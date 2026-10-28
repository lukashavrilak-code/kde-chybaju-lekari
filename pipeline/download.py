import re
import shutil
import zipfile
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse

import requests

from . import __version__
from .checks import Checks, PipelineError, utc_now
from .config import ROOT, project_path
from .files import replace_csv_rows, sha256_file

SNAPSHOT_COLUMNS = ["stav_k", "url", "sha256", "velkost_b", "pocet_riadkov", "stiahnute_utc"]
HEADERS = {"User-Agent": f"kde-chybaju-lekari/{__version__}"}


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        href = dict(attrs).get("href") if tag == "a" else None
        if href:
            self.links.append(href.strip())


def xlsx_problems(path, cfg):
    reg = cfg["register"]
    if not zipfile.is_zipfile(path):
        return ["súbor nie je XLSX (ZIP)"]
    problems = []
    with zipfile.ZipFile(path) as z:
        infos = z.infolist()
        names = [i.filename.lower() for i in infos]
        if len(infos) > reg["max_poloziek_zip"]:
            problems.append(f"priveľa položiek v archíve ({len(infos)})")
        if sum(i.file_size for i in infos) > reg["max_rozbalene_mb"] * 1024 * 1024:
            problems.append("po rozbalení je súbor priveľký")
        if "xl/workbook.xml" not in names:
            problems.append("chýba xl/workbook.xml")
        if any(n.endswith("vbaproject.bin") for n in names):
            problems.append("súbor obsahuje makrá")
    return problems


def allowed_url(url, domains):
    host = urlparse(url).hostname or ""
    return url.startswith("https://") and host in domains


def stream_to_file(url, target, domains, max_mb):
    if not allowed_url(url, domains):
        raise PipelineError(f"URL nemá HTTPS alebo povolenú doménu: {url or '(URL nie je zadaná)'}")
    limit = max_mb * 1024 * 1024
    try:
        with requests.get(url, headers=HEADERS, stream=True, timeout=60) as response:
            response.raise_for_status()
            if not allowed_url(response.url, domains):
                raise PipelineError(f"Presmerovanie na nepovolenú doménu: {response.url}")
            size = 0
            with open(target, "wb") as f:
                for chunk in response.iter_content(chunk_size=1 << 16):
                    size += len(chunk)
                    if size > limit:
                        raise PipelineError("Súbor je väčší ako povolený limit, sťahovanie prerušené.")
                    f.write(chunk)
    except requests.RequestException as error:
        raise PipelineError(f"Sťahovanie zlyhalo: {error}") from error


def fetch(url, target, cfg, checks):
    domains = cfg["register"]["povolene_domeny"]
    checks.check("V1.1", allowed_url(url, domains), "HTTPS a povolená doména", url or "(URL nie je zadaná)")
    checks.done()
    stream_to_file(url, target, domains, cfg["register"]["max_mb"])


def read_page(url, domains, max_mb):
    if not allowed_url(url, domains):
        raise PipelineError(f"Stránka nemá HTTPS alebo povolenú doménu: {url}")
    limit = max_mb * 1024 * 1024
    try:
        with requests.get(url, headers=HEADERS, stream=True, timeout=60) as response:
            response.raise_for_status()
            if not allowed_url(response.url, domains):
                raise PipelineError(f"Stránka presmerovala na nepovolenú doménu: {response.url}")
            content = b""
            for chunk in response.iter_content(chunk_size=1 << 16):
                content += chunk
                if len(content) > limit:
                    raise PipelineError("Stránka je väčšia ako povolený limit.")
            return content.decode(response.encoding or "utf-8", errors="replace"), response.url
    except requests.RequestException as error:
        raise PipelineError(f"Stránka nie je dostupná: {error}") from error


def link_date(url, cfg):
    name = Path(unquote(urlparse(url).path)).name
    match = re.search(cfg["register"]["vzor_odkazu"], name)
    if not match:
        return None
    day, month, year = (int(g) for g in match.groups())
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return None


def find_register_link(html, base_url, cfg):
    parser = LinkParser()
    parser.feed(html)
    found = []
    for href in parser.links:
        url = urljoin(base_url, href)
        stav_k = link_date(url, cfg)
        if stav_k and allowed_url(url, cfg["register"]["povolene_domeny"]):
            found.append((stav_k, url))
    if not found:
        return None
    stav_k, url = max(found)
    return url, stav_k


def discover(cfg):
    reg = cfg["register"]
    html, page_url = read_page(reg["stranka"], reg["povolene_domeny"], reg["max_stranka_mb"])
    return find_register_link(html, page_url, cfg)


def resolve_source(cfg, checks):
    try:
        found = discover(cfg)
        reason = "na stránke nie je odkaz zodpovedajúci vzoru"
    except PipelineError as error:
        found, reason = None, str(error)
    if found:
        checks.info("V1.0", "odkaz na register nájdený na stránke ÚDZS", found[0])
        return found
    url = cfg["register"]["url"]
    checks.check("V1.0", False, "odkaz sa nenašiel, použitá záložná URL z config.toml", url, "WARN", detail=reason)
    return url, link_date(url, cfg)


def snapshot_dir(cfg):
    return project_path(cfg, "snapshots") / "udzs"


def sidecar(path):
    return path.with_name(path.name + ".sha256")


def archived_files(folder):
    result = {}
    for side in folder.glob("*.xlsx.sha256"):
        parts = side.read_text(encoding="utf-8").split()
        if parts:
            result[parts[0]] = side.with_name(side.name.removesuffix(".sha256"))
    return result


def write_snapshot_history(cfg, con, stav_k):
    row = con.execute("SELECT * FROM snapshot WHERE stav_k = ?", (stav_k,)).fetchone()
    data = {col: row[col] if row[col] is not None else "" for col in SNAPSHOT_COLUMNS}
    data["stiahnute_utc"] = row["stiahnute_utc"]
    path = project_path(cfg, "history") / "snapshoty.csv"
    replace_csv_rows(path, [data], SNAPSHOT_COLUMNS, "stav_k", stav_k, ["stav_k"])


def insert_snapshot(con, stav_k, url, path, sha):
    con.execute(
        "INSERT INTO snapshot (stav_k, stiahnute_utc, url, subor, sha256, velkost_b, pipeline_verzia) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (stav_k, utc_now(), url, path.relative_to(ROOT).as_posix(), sha, path.stat().st_size, __version__),
    )


def download(cfg, con, stav_k=None, url=None, subor=None, force=False):
    target_dir = snapshot_dir(cfg)
    target_dir.mkdir(parents=True, exist_ok=True)
    tmp = target_dir / "_stahovanie.tmp"
    checks = Checks(con, "1-download")
    try:
        if subor:
            source = Path(subor)
            url = f"subor:{source.name}"
            name_date = link_date(source.name, cfg)
            shutil.copyfile(source, tmp)
        else:
            if url:
                name_date = link_date(url, cfg)
            else:
                url, name_date = resolve_source(cfg, checks)
            fetch(url, tmp, cfg, checks)

        if stav_k and name_date and stav_k != name_date:
            checks.check("V1.0", False, "dátum --stav-k sa líši od dátumu v názve súboru", f"{stav_k} / {name_date}", "WARN")
        stav_k = stav_k or name_date
        if not stav_k:
            raise PipelineError("Dátum stavu registra sa nedá určiť z názvu súboru. Zadaj --stav-k RRRR-MM-DD")

        size = tmp.stat().st_size
        reg = cfg["register"]
        checks.check(
            "V1.2", reg["min_kb"] * 1024 <= size <= reg["max_mb"] * 1024 * 1024,
            "veľkosť súboru v povolenom rozsahu", f"{size / 1024:.0f} KB",
        )
        problems = xlsx_problems(tmp, cfg)
        checks.check("V1.3", not problems, "súbor je XLSX bez makier a bez podozrivej štruktúry", "; ".join(problems) or "OK")
        checks.done()

        sha = sha256_file(tmp)
        same_file = con.execute("SELECT stav_k FROM snapshot WHERE sha256 = ?", (sha,)).fetchone()
        if same_file:
            checks.info("V1.4", "súbor je rovnaký ako už uložený snapshot, nový snapshot sa nevytvára", same_file["stav_k"])
            checks.done()
            return same_file["stav_k"]
        archived = archived_files(target_dir).get(sha)
        if archived and archived.exists():
            archived_stav_k = archived.name.removesuffix(".xlsx")
            insert_snapshot(con, archived_stav_k, url, archived, sha)
            checks.info("V1.4", "súbor už je v archíve snapshotov, iba sa zapísal do databázy", archived.name)
            checks.done()
            write_snapshot_history(cfg, con, archived_stav_k)
            return archived_stav_k

        final = target_dir / f"{stav_k}.xlsx"
        existing = con.execute("SELECT * FROM snapshot WHERE stav_k = ?", (stav_k,)).fetchone()
        if (existing or final.exists()) and not force:
            checks.check("V1.4", False, "pre tento dátum už existuje iný súbor (použi --force na nahradenie)", stav_k)
            checks.done()
        if existing:
            (ROOT / existing["subor"]).unlink(missing_ok=True)
            sidecar(ROOT / existing["subor"]).unlink(missing_ok=True)
            con.execute("DELETE FROM snapshot WHERE snapshot_id = ?", (existing["snapshot_id"],))

        tmp.replace(final)
        sidecar(final).write_text(f"{sha}  {final.name}\n", encoding="utf-8", newline="\n")
        insert_snapshot(con, stav_k, url, final, sha)
        checks.info("V1.4", "nový snapshot uložený", final.name)
        checks.done()
        write_snapshot_history(cfg, con, stav_k)
        return stav_k
    finally:
        tmp.unlink(missing_ok=True)


def check_for_update(cfg, con):
    found = discover(cfg)
    if not found:
        raise PipelineError("Na stránke ÚDZS sa nenašiel odkaz zodpovedajúci vzoru VyberKpWeb_*.xlsx.")
    url, stav_k = found
    latest = con.execute("SELECT stav_k, url FROM snapshot ORDER BY stav_k DESC LIMIT 1").fetchone()
    if latest and (latest["stav_k"] >= stav_k or latest["url"] == url):
        print(f"Bez zmeny: posledný snapshot je k {latest['stav_k']}, na stránke ÚDZS je {Path(urlparse(url).path).name}.")
        return False
    print(f"Nový register k {stav_k} je dostupný: {url}")
    print("Spusti: python -m pipeline download")
    return True
