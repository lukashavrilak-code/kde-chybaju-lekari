from pathlib import Path
from urllib.parse import unquote, urlparse

import openpyxl
import pandas as pd

from .areas import norm_name
from .checks import Checks, PipelineError
from .config import project_path
from .download import stream_to_file, xlsx_problems

TYPES = ("VLD", "VLDD")
SR = "SR"


def nczi_path(cfg):
    name = Path(unquote(urlparse(cfg["nczi"]["url"]).path)).name
    return project_path(cfg, "raw") / "nczi" / name


def ensure_file(cfg, force=False):
    path = nczi_path(cfg)
    if path.exists() and not force:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    try:
        stream_to_file(cfg["nczi"]["url"], tmp, cfg["nczi"]["povolene_domeny"], cfg["register"]["max_mb"])
        problems = xlsx_problems(tmp, cfg)
        if problems:
            raise PipelineError("Súbor NCZI nie je v poriadku: " + "; ".join(problems))
        tmp.replace(path)
    finally:
        tmp.unlink(missing_ok=True)
    return path


def to_number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def read_nczi(path, cfg):
    settings = cfg["nczi"]
    codes = {code: typ for typ, code in cfg["odbornosti"].items()}
    counts, fte, areas = {}, {}, {}
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True, keep_links=False)
    try:
        for sheet, kraj in settings["harky"].items():
            if sheet not in wb.sheetnames:
                continue
            column = fte_column = None
            for row in wb[sheet].iter_rows(values_only=True):
                cells = ["" if c is None else str(c).strip() for c in row]
                if column is None:
                    title = next((c for c in cells if c.startswith("Územie")), "")
                    if title:
                        areas[kraj] = title.split(":", 1)[-1].strip()
                    if settings["stlpec"] in cells:
                        column = cells.index(settings["stlpec"])
                        if settings["stlpec_uvazky"] in cells:
                            fte_column = cells.index(settings["stlpec_uvazky"])
                    continue
                if len(cells) > column and cells[0] == settings["riadok"]:
                    code = cells[1].removesuffix(".0").zfill(3)
                    if code in codes:
                        counts[(codes[code], kraj)] = int(float(row[column]))
                        if fte_column is not None and len(row) > fte_column:
                            fte[(codes[code], kraj)] = round(to_number(row[fte_column]), 2)
    finally:
        wb.close()
    return counts, fte, areas


def load_register(con, sid):
    amb = pd.read_sql("SELECT * FROM ambulancia WHERE snapshot_id = ?", con, params=(sid,))
    kraje = pd.read_sql(
        "SELECT ao.adresa_kluc, MIN(o.kraj_kod) AS kraj_kod, COUNT(DISTINCT o.kraj_kod) AS krajov "
        "FROM adresa_obec ao JOIN obec o ON o.obec_kod = ao.obec_kod GROUP BY ao.adresa_kluc",
        con,
    )
    amb = amb.merge(kraje, on="adresa_kluc", how="left")
    amb.loc[amb["krajov"] != 1, "kraj_kod"] = None
    return amb


def ratio(register, nczi):
    return register / nczi if nczi else None


def fmt_ratio(value):
    return "–" if value is None else f"{value:.2f}".replace(".", ",")


def fmt_int(value):
    return f"{int(value):,}".replace(",", " ")


def register_counts(amb, kraje):
    result = {}
    for typ in TYPES:
        part = amb[amb["typ"] == typ]
        result[(typ, SR)] = len(part)
        by_kraj = part.groupby("kraj_kod").size()
        for kraj in kraje:
            result[(typ, kraj)] = int(by_kraj.get(kraj, 0))
    return result


def check_file(cfg, checks, counts, fte, areas, kraj_names):
    settings = cfg["nczi"]
    sr_ok = all(counts.get((typ, SR)) == settings["kontrola_sr"][typ] for typ in TYPES)
    found = ", ".join(f"{typ} {counts.get((typ, SR))}" for typ in TYPES)
    checks.check("V3.7", sr_ok, "súbor NCZI sa prečítal správne (počty za SR sa rovnajú overeným hodnotám)", found, "WARN")
    if not sr_ok:
        return False
    kraje = [k for k in settings["harky"].values() if k != SR]
    tolerance = settings["tolerancia_uvazky"]
    for typ in TYPES:
        total = sum(counts.get((typ, k), 0) for k in kraje)
        checks.check("V3.7", total == counts[(typ, SR)], f"NCZI {typ}: súčet krajov sa rovná SR", f"{total} / {counts[(typ, SR)]}", "WARN")
        sr_fte = fte.get((typ, SR))
        expected = settings["kontrola_uvazky_sr"][typ]
        checks.check("V3.7", sr_fte is not None and abs(sr_fte - expected) <= tolerance,
                     f"NCZI {typ}: úväzky lekárov za SR sa rovnajú overenej hodnote", f"{sr_fte} / {expected}", "WARN")
        fte_total = round(sum(fte.get((typ, k), 0.0) for k in kraje), 2)
        checks.check("V3.7", sr_fte is not None and abs(fte_total - sr_fte) <= tolerance,
                     f"NCZI {typ}: súčet úväzkov krajov sa rovná SR", f"{fte_total} / {sr_fte}", "WARN")
    wrong = [f"{k}: {areas.get(k)}" for k in kraje
             if not norm_name(areas.get(k, "")).startswith(norm_name(kraj_names.get(k, "?")))]
    checks.check("V3.7", not wrong, "poradie hárkov NCZI zodpovedá kódom krajov", f"{len(wrong)} nezhôd", "WARN",
                 detail=", ".join(wrong))
    return True


def compare(cfg, con, checks, sid, amb, counts, fte, kraj_names):
    settings = cfg["nczi"]
    kraje = [k for k in settings["harky"].values() if k != SR]
    ours = register_counts(amb, kraje)
    rows = []
    for typ in TYPES:
        for kraj in [SR, *kraje]:
            reference = counts.get((typ, kraj), 0)
            mine = ours[(typ, kraj)]
            value = ratio(mine, reference)
            name = "Slovensko" if kraj == SR else kraj_names.get(kraj, kraj)
            checks.check(
                "V3.7", value is not None and settings["pomer_min"] <= value <= settings["pomer_max"],
                f"{typ} {name}: register / NCZI {settings['rok']} v rozsahu "
                f"{fmt_ratio(settings['pomer_min'])} – {fmt_ratio(settings['pomer_max'])}",
                f"register {mine} / NCZI {reference} = {fmt_ratio(value)}", "WARN",
            )
            rows.append((sid, settings["rok"], typ, kraj, mine, reference, fte.get((typ, kraj))))
        unknown = int(((amb["typ"] == typ) & amb["kraj_kod"].isna()).sum())
        checks.info("V3.7", f"{typ}: ambulancie bez jednoznačného kraja z adresy v registri", unknown)
    con.execute("DELETE FROM nczi_porovnanie WHERE snapshot_id = ?", (sid,))
    con.executemany(
        "INSERT INTO nczi_porovnanie (snapshot_id, rok, typ, kraj_kod, register, nczi, uvazky) VALUES (?, ?, ?, ?, ?, ?, ?)", rows
    )


def year_bucket(value):
    if not value:
        return "neuvedené"
    year = int(value[:4])
    if year <= 2000:
        return "≤ 2000"
    if year <= 2010:
        return "2001 – 2010"
    if year <= 2020:
        return "2011 – 2020"
    return str(year)


def scenario_table(typ, scenarios, counts, kraje, kraj_names):
    ours = [register_counts(frame, kraje) for _, frame in scenarios]
    lines = [f"### {typ}", "", "| Kraj | NCZI | " + " | ".join(name for name, _ in scenarios) + " |",
             "|---|---:|" + "---:|" * len(scenarios)]
    for kraj in [SR, *kraje]:
        label = "Slovensko" if kraj == SR else kraj_names.get(kraj, kraj)
        reference = counts.get((typ, kraj), 0)
        cells = [f"{fmt_int(o[(typ, kraj)])} ({fmt_ratio(ratio(o[(typ, kraj)], reference))})" for o in ours]
        lines.append(f"| {label} | {fmt_int(reference)} | " + " | ".join(cells) + " |")
    return lines + [""]


def write_gap_report(cfg, snapshot, amb, counts, kraj_names):
    settings = cfg["nczi"]
    reference_date = settings["referencny_datum"]
    kraje = [k for k in settings["harky"].values() if k != SR]
    group = ["ico", "typ", "adresa_kluc"]
    before = amb[(amb["platnost_od"] == "") | (amb["platnost_od"] <= reference_date)]
    scenarios = [
        ("S0", amb),
        ("S1", before),
        ("S2", amb.drop_duplicates(group)),
        ("S3", before.drop_duplicates(group)),
    ]
    lines = [
        f"# Rozdiel register ÚDZS vs. NCZI – register k {snapshot['stav_k']}, NCZI {settings['rok']}",
        "",
        f"Iba agregované počty. NCZI: „{settings['stlpec']}“, riadky „{settings['riadok']}“, stav k {reference_date}.",
        "Kraj ambulancie je určený z adresy v registri (Obec OU), nie z geokódovania.",
        "",
        "## a) Pomer register / NCZI po krajoch",
        "",
        "| Kraj | " + " | ".join(f"{typ} register | {typ} NCZI | {typ} pomer" for typ in TYPES) + " |",
        "|---|" + "---:|" * 3 * len(TYPES),
    ]
    ours = register_counts(amb, kraje)
    for kraj in [SR, *kraje]:
        label = "Slovensko" if kraj == SR else kraj_names.get(kraj, kraj)
        cells = []
        for typ in TYPES:
            mine, reference = ours[(typ, kraj)], counts.get((typ, kraj), 0)
            cells += [fmt_int(mine), fmt_int(reference), fmt_ratio(ratio(mine, reference))]
        lines.append(f"| {label} | " + " | ".join(cells) + " |")
    unknown = amb[amb["kraj_kod"].isna()].groupby("typ").size()
    lines += ["", "Bez jednoznačného kraja (započítané iba do Slovenska): "
              + ", ".join(f"{typ} {fmt_int(unknown.get(typ, 0))}" for typ in TYPES) + ".", ""]

    lines += ["## b) Viac kódov na rovnakom IČO a adrese", "",
              "| Typ | Kódov | Skupín IČO+typ+adresa s viac kódmi | Nadbytočných kódov (n − 1) | IČO s viac kódmi daného typu (ľubovoľná adresa) | Kódy s poradím 02+ |",
              "|---|---:|---:|---:|---:|---:|"]
    for typ in TYPES:
        part = amb[amb["typ"] == typ]
        sizes = part.groupby(["ico", "adresa_kluc"]).size()
        multi = sizes[sizes > 1]
        per_ico = part.groupby("ico").size()
        later = int((part["pzs_kod"].str[10:12] != "01").sum())
        lines.append(f"| {typ} | {fmt_int(len(part))} | {fmt_int(len(multi))} | {fmt_int((multi - 1).sum())} | "
                     f"{fmt_int((per_ico > 1).sum())} | {fmt_int(later)} |")
    both = amb.groupby(["ico", "adresa_kluc"])["typ"].nunique()
    lines += ["", f"Adresy s rovnakým IČO, na ktorých sú kódy VLD aj VLDD: {fmt_int((both > 1).sum())}.", ""]

    lines += ["## c) Rozdelenie podľa Platnost_od", "", "| Začiatok platnosti | VLD | VLDD |", "|---|---:|---:|"]
    buckets = amb.assign(kos=amb["platnost_od"].map(year_bucket)).groupby(["kos", "typ"]).size()
    order = ["≤ 2000", "2001 – 2010", "2011 – 2020", *sorted({b for b, _ in buckets.index if b[:1].isdigit() and len(b) == 4}),
             "neuvedené"]
    for bucket in dict.fromkeys(order):
        if any((bucket, typ) in buckets.index for typ in TYPES):
            lines.append(f"| {bucket} | " + " | ".join(fmt_int(buckets.get((bucket, typ), 0)) for typ in TYPES) + " |")
    after = amb[amb["platnost_od"] > reference_date].groupby("typ").size()
    lines += ["", f"Kódy so začiatkom platnosti po {reference_date}: "
              + ", ".join(f"{typ} {fmt_int(after.get(typ, 0))}" for typ in TYPES) + ".",
              ("Register neobsahuje ukončené záznamy, preto počet kódov so začiatkom do referenčného dátumu je iba dolný odhad "
               "stavu registra k tomuto dátumu."), ""]

    lines += ["## d) Scenáre (iba informatívne, nič sa nefiltruje)", "",
              (f"S0 = všetky kódy, S1 = bez kódov so začiatkom platnosti po {reference_date}, "
               "S2 = kódy s rovnakým IČO, typom a adresou zlúčené na jeden, S3 = S1 + S2. "
               "V bunke je počet v registri a v zátvorke pomer k NCZI."), ""]
    for typ in TYPES:
        lines += scenario_table(typ, scenarios, counts, kraje, kraj_names)

    path = project_path(cfg, "local") / "reports" / f"nczi_rozdiel_{snapshot['stav_k']}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def nczi(cfg, con, snapshot, force=False):
    sid = snapshot["snapshot_id"]
    checks = Checks(con, "3-nczi", sid)
    try:
        path = ensure_file(cfg, force)
        counts, fte, areas = read_nczi(path, cfg)
    except (PipelineError, OSError, ValueError) as error:
        checks.check("V3.7", False, "súbor NCZI je dostupný (kontrola sa preskočila)", "", "WARN", detail=str(error))
        checks.done()
        return
    kraj_names = {r["kraj_kod"]: r["kraj_nazov"] for r in con.execute("SELECT DISTINCT kraj_kod, kraj_nazov FROM okres")}
    if check_file(cfg, checks, counts, fte, areas, kraj_names):
        amb = load_register(con, sid)
        compare(cfg, con, checks, sid, amb, counts, fte, kraj_names)
        report = write_gap_report(cfg, snapshot, amb, counts, kraj_names)
        checks.info("V3.7", "report rozdielu register vs. NCZI", report.name)
    checks.done()
