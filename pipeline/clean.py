import re

from .areas import norm_name
from .checks import Checks, PipelineError
from .config import ROOT, project_path
from .files import read_csv_rows
from .validate import clean_frame, load_register, parse_date

EMPTY_VALUES = {"null", "none", "-"}


def norm_psc(text):
    text = re.sub(r"\.0$", "", text.strip())
    digits = re.sub(r"\D", "", text)
    if len(digits) == 4:
        digits = "0" + digits
    return digits if len(digits) == 5 else ""


def address_key(ulica, obec, psc):
    return "|".join(" ".join(part.lower().split()) for part in (ulica, obec, psc))


def is_valid(od, do, stav_k):
    return (not od or od <= stav_k) and (not do or do >= stav_k)


def load_blocklist(cfg):
    rows = read_csv_rows(project_path(cfg, "local") / "blocklist.csv")
    return {r["pzs_kod"].strip().upper() for r in rows if r.get("pzs_kod", "").strip()}


def load_obec_mapping(cfg):
    rows = read_csv_rows(project_path(cfg, "manual") / "obec_mapping.csv")
    return {(norm_name(r["obec_text"]), r.get("psc", "").strip()): r["obec_kod"].strip() for r in rows if r.get("obec_text")}


def register_obce(cfg, con, addresses):
    obce = con.execute("SELECT obec_kod, nazov, kraj_kod FROM obec").fetchall()
    if not obce:
        raise PipelineError("Tabuľka obcí je prázdna. Najprv spusti: python -m pipeline areas")
    by_name, by_city = {}, {}
    for r in obce:
        by_name.setdefault(norm_name(r["nazov"]), []).append(r["obec_kod"])
        if "-" in r["nazov"]:
            by_city.setdefault(norm_name(r["nazov"].split("-")[0]), []).append(r["obec_kod"])
    kraj_of = {r["obec_kod"]: r["kraj_kod"] for r in obce}
    mapping = load_obec_mapping(cfg)
    rows, missing, several_kraje = [], [], 0
    for kluc, obec_text, psc in addresses:
        target = norm_name(obec_text)
        mapped = mapping.get((target, psc)) or mapping.get((target, ""))
        if mapped:
            rows.append((kluc, mapped, "rucne"))
            continue
        codes, source = by_name.get(target, []), "nazov"
        if not codes:
            codes, source = by_city.get(target, []), "mesto"
        if not codes:
            missing.append(f"{obec_text} ({psc})")
            continue
        rows.extend((kluc, kod, source) for kod in codes)
        several_kraje += len({kraj_of[kod] for kod in codes}) > 1
    return rows, missing, several_kraje


def clean(cfg, con, snapshot):
    sid = snapshot["snapshot_id"]
    stav_k = snapshot["stav_k"]
    checks = Checks(con, "3-clean", sid)
    _, raw = load_register(ROOT / snapshot["subor"], cfg)
    frame = clean_frame(raw)

    blocklist = load_blocklist(cfg)
    blocked = frame["pzs_kod"].isin(blocklist)
    not_found = blocklist - set(frame["pzs_kod"])
    checks.check("V3.1", not not_found, "všetky položky blocklistu sa našli v registri", f"{len(not_found)} nenájdených", "WARN")
    checks.info("V3.1", "záznamy vylúčené na žiadosť", int(blocked.sum()))
    frame = frame[~blocked].copy()

    types = {code: typ for typ, code in cfg["odbornosti"].items()}
    frame["odbornost_kod"] = frame["pzs_kod"].str[6:9]
    frame["typ"] = frame["odbornost_kod"].map(types)
    frame = frame[frame["typ"].notna()].copy()
    allowed_kind = frame["pzs_kod"].str[9].isin(cfg["druh_cinnosti"]["pozicia_10"])
    checks.info("V3.0", "vylúčené iné druhy činnosti ako ambulancia (napr. stacionár)", int((~allowed_kind).sum()))
    frame = frame[allowed_kind].copy()

    frame["platnost_od"] = frame["platnost_od"].map(parse_date).fillna("")
    frame["platnost_do"] = frame["platnost_do"].map(parse_date).fillna("")
    valid = [is_valid(o, d, stav_k) for o, d in zip(frame["platnost_od"], frame["platnost_do"])]
    checks.info("V3.0", "záznamy mimo platnosti k dátumu stavu", len(frame) - sum(valid))
    frame = frame[valid].copy()

    before = len(frame)
    frame = frame.sort_values(["pzs_kod", "platnost_od"]).drop_duplicates("pzs_kod", keep="last")
    checks.info("V3.0", "odstránené duplicitné pzs_kod (ponechaný najnovší)", before - len(frame))

    frame["psc"] = frame["psc"].map(norm_psc)
    frame["ico"] = frame["ico"].map(lambda x: x.zfill(8) if x.isdigit() else x)
    placeholder = frame["ulica"].str.strip().str.lower().isin(EMPTY_VALUES)
    checks.info("V3.2", "ulica v registri je zástupný text (null, none, -), použije sa prázdna", int(placeholder.sum()))
    frame.loc[placeholder, "ulica"] = ""
    missing_address = frame["obec"] == ""
    frame["adresa_kluc"] = [
        address_key(u, o, p) if o else f"chyba|{k}"
        for u, o, p, k in zip(frame["ulica"], frame["obec"], frame["psc"], frame["pzs_kod"])
    ]
    checks.check("V3.2", not missing_address.any(), "každá ambulancia má adresu prevádzky (OU)",
                 f"{int(missing_address.sum())} bez adresy", "WARN",
                 detail=", ".join(frame.loc[missing_address, "pzs_kod"].head(20)))

    group = ["ico", "typ", "adresa_kluc"]
    duplicated = frame[frame.duplicated(group, keep=False)]
    checks.check("V3.3", duplicated.empty, "žiadne možné duplicity (rovnaké IČO, typ a adresa)",
                 f"{duplicated.groupby(group).ngroups} skupín", "WARN")
    per_address = frame.groupby("adresa_kluc").size()
    checks.info("V3.3", "adresy s viac ako 10 ambulanciami", int((per_address > 10).sum()))
    for typ in ("VLD", "VLDD"):
        checks.info("V3.0", f"platné ambulancie {typ}", int((frame["typ"] == typ).sum()))

    addresses = frame.loc[frame["obec"] != "", ["adresa_kluc", "obec", "psc"]].drop_duplicates("adresa_kluc")
    links, missing, several_kraje = register_obce(cfg, con, addresses.itertuples(index=False))
    checks.check("V3.8", not missing, "obec z adresy v registri sa našla v hraniciach ZBGIS (inak doplň data/manual/obec_mapping.csv)",
                 f"{len(missing)} adries bez obce", "WARN", detail=", ".join(sorted(set(missing))[:40]))
    checks.info("V3.8", "adresy, pri ktorých názov obce zodpovedá obciam vo viacerých krajoch", several_kraje)
    con.execute("DELETE FROM adresa_obec")
    con.executemany("INSERT INTO adresa_obec (adresa_kluc, obec_kod, zdroj) VALUES (?, ?, ?)", links)

    con.execute("DELETE FROM ambulancia WHERE snapshot_id = ?", (sid,))
    con.executemany(
        "INSERT INTO ambulancia (snapshot_id, pzs_kod, ico, nazov, typ, odbornost_kod, ulica, obec_text, psc, "
        "adresa_kluc, platnost_od, platnost_do) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (sid, r.pzs_kod, r.ico, r.nazov, r.typ, r.odbornost_kod, r.ulica, r.obec, r.psc,
             r.adresa_kluc, r.platnost_od, r.platnost_do)
            for r in frame.itertuples()
        ],
    )
    checks.done()
