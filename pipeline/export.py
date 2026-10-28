import json
import subprocess
from datetime import date

import pandas as pd

from . import __version__
from .areas import areas_dir
from .checks import Checks, utc_now
from .compute import DENOMINATOR, FAR_COLUMNS, load_ambulances
from .config import ROOT, project_path, published_types
from .files import write_csv_rows, write_json
from .site import build_site

TYPE_NAMES = {"VLD": "Všeobecný lekár pre dospelých", "VLDD": "Pediater prvého kontaktu"}
DENOMINATOR_NAMES = {"VLD": "dospelých (18+)", "VLDD": "detí (0 – 17)"}
AMBULANCE_KEYS = {"nazov", "typ", "adresa", "lat", "lon", "presnost"}
ALLOWED_EXTENSIONS = {".html", ".css", ".js", ".json", ".geojson", ".csv", ".png", ".svg", ".txt"}
SK_BOUNDS = {"lat": (47.7, 49.7), "lon": (16.8, 22.6)}
FIRST_LOAD = ["index.html", "static/css/style.css", "data/meta.json", "data/okresy.geojson"]
OKRES_CSV = ["okres_kod", "okres", "kraj", "typ", "pocet_ambulancii", "pocet_pracovisk", "na_10k", "menovatel", "poradie",
             *FAR_COLUMNS, "na_10k_okolie", "poradie_okolie", "stav_registra", "stav_obyvatelstva", "verzia_pipeline"]
OBEC_CSV = ["obec_kod", "obec", "okres", "typ", "najblizsia_km", "pocet_v_obci", "pocet_do_10km", "pocet_do_20km",
            "na_10k_okolie", "stav_registra", "verzia_pipeline"]


def pipeline_version():
    def git(*args):
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    try:
        sha = git("rev-parse", "--short", "HEAD")
        dirty = git("status", "--porcelain")
    except (OSError, subprocess.CalledProcessError):
        return f"{__version__}+bez-commitu"
    return f"{__version__}+{sha}" + ("-dirty" if dirty else "")


def round_coords(value, digits):
    if isinstance(value, float):
        return round(value, digits)
    if isinstance(value, (list, tuple)):
        return [round_coords(v, digits) for v in value]
    return value


def format_date(iso):
    if not iso:
        return ""
    d = date.fromisoformat(iso)
    return f"{d.day}. {d.month}. {d.year}"


def format_address(ulica, psc, obec):
    psc_text = f"{psc[:3]} {psc[3:]}" if len(psc or "") == 5 else (psc or "")
    town = " ".join(part for part in (psc_text, obec or "") if part)
    return ", ".join(part for part in (ulica or "", town) if part)


def in_slovakia(lat, lon):
    return SK_BOUNDS["lat"][0] <= lat <= SK_BOUNDS["lat"][1] and SK_BOUNDS["lon"][0] <= lon <= SK_BOUNDS["lon"][1]


def export_okresy(cfg, okresy, indicators, types, meta):
    web = json.loads((areas_dir(cfg) / "okresy_web.geojson").read_text(encoding="utf-8"))
    by_key = indicators.set_index(["okres_kod", "typ"])
    features = []
    for feature in sorted(web["features"], key=lambda f: f["properties"]["okres_kod"]):
        kod = feature["properties"]["okres_kod"]
        props = {"kod": kod, "nazov": okresy.at[kod, "nazov"], "kraj": okresy.at[kod, "kraj_nazov"]}
        for typ in types:
            row = by_key.loc[(kod, typ)]
            prefix = typ.lower()
            props[f"{prefix}_pocet"] = int(row["pocet"])
            props[f"{prefix}_pracoviska"] = int(row["pocet_pracovisk"])
            props[f"{prefix}_na10k"] = float(row["na_10k"])
            props[f"{prefix}_poradie"] = int(row["poradie"])
            for name, km in zip(FAR_COLUMNS, cfg["vypocty"]["podiel_nad_km"]):
                props[f"{prefix}_nad{km}"] = float(row[name])
            props[f"{prefix}_okolie"] = float(row["na_10k_okolie"])
            props[f"{prefix}_poradie_okolie"] = int(row["poradie_okolie"])
        geometry = feature["geometry"]
        features.append({
            "type": "Feature",
            "properties": props,
            "geometry": {"type": geometry["type"],
                         "coordinates": round_coords(geometry["coordinates"], cfg["hranice"]["desatinne_miesta_okresy"])},
        })
    return {"type": "FeatureCollection", "meta": meta, "features": features}


def export_obce(obce, indicators, types, meta):
    by_key = indicators.set_index(["obec_kod", "typ"])
    items = []
    for obec in obce.itertuples():
        item = {"kod": obec.obec_kod, "nazov": obec.nazov, "okres_kod": obec.okres_kod,
                "lat": round(obec.ref_lat, 5), "lon": round(obec.ref_lon, 5)}
        for typ in types:
            row = by_key.loc[(obec.obec_kod, typ)]
            prefix = typ.lower()
            item[f"{prefix}_km"] = None if pd.isna(row["najblizsia_km"]) else round(float(row["najblizsia_km"]), 2)
            item[f"{prefix}_v_obci"] = int(row["pocet_v_obci"])
            item[f"{prefix}_10"] = int(row["pocet_10km"])
            item[f"{prefix}_20"] = int(row["pocet_20km"])
        items.append(item)
    return {**meta, "obce": items}


def export_ambulancie(amb, types, meta):
    subset = amb[amb["typ"].isin(types)].copy()
    subset["adresa"] = [format_address(u, p, o) for u, p, o in zip(subset["ulica"], subset["psc"], subset["obec_text"])]
    subset = subset.sort_values(["typ", "obec_text", "adresa", "nazov"])
    items = [
        {"nazov": r.nazov, "typ": r.typ, "adresa": r.adresa, "lat": round(r.lat, 5), "lon": round(r.lon, 5),
         "presnost": r.presnost}
        for r in subset.itertuples()
    ]
    return {**meta, "atribucia": "Údaje: ÚDZS. Poloha: © OpenStreetMap contributors, ODbL.", "ambulancie": items}


def csv_rows(okresy, obce, okres_ind, obec_ind, types, meta):
    okres_rows = []
    for r in okres_ind[okres_ind["typ"].isin(types)].sort_values(["typ", "okres_kod"]).itertuples():
        okres_rows.append({
            "okres_kod": r.okres_kod, "okres": okresy.at[r.okres_kod, "nazov"], "kraj": okresy.at[r.okres_kod, "kraj_nazov"],
            "typ": r.typ, "pocet_ambulancii": r.pocet, "pocet_pracovisk": r.pocet_pracovisk, "na_10k": f"{r.na_10k:.2f}",
            "menovatel": DENOMINATOR_NAMES[r.typ],
            "poradie": r.poradie, "podiel_nad_5km": f"{r.podiel_nad_5km:.4f}", "podiel_nad_10km": f"{r.podiel_nad_10km:.4f}",
            "na_10k_okolie": f"{r.na_10k_okolie:.2f}", "poradie_okolie": r.poradie_okolie,
            "stav_registra": meta["stav_registra"], "stav_obyvatelstva": meta["stav_obyvatelstva"],
            "verzia_pipeline": meta["verzia_pipeline"],
        })
    names = obce.set_index("obec_kod")
    obec_rows = []
    for r in obec_ind[obec_ind["typ"].isin(types)].sort_values(["typ", "obec_kod"]).itertuples():
        okres_kod = names.at[r.obec_kod, "okres_kod"]
        obec_rows.append({
            "obec_kod": r.obec_kod, "obec": names.at[r.obec_kod, "nazov"], "okres": okresy.at[okres_kod, "nazov"],
            "typ": r.typ, "najblizsia_km": "" if pd.isna(r.najblizsia_km) else f"{r.najblizsia_km:.2f}",
            "pocet_v_obci": r.pocet_v_obci, "pocet_do_10km": r.pocet_10km, "pocet_do_20km": r.pocet_20km,
            "na_10k_okolie": f"{r.na_10k_okolie:.2f}",
            "stav_registra": meta["stav_registra"], "verzia_pipeline": meta["verzia_pipeline"],
        })
    return okres_rows, obec_rows


def rankings(okresy, okres_ind, types, mestske):
    result = {}
    for typ in types:
        part = okres_ind[okres_ind["typ"] == typ].sort_values(["poradie", "okres_kod"])
        rows = [
            {"kod": r.okres_kod, "poradie": int(r.poradie), "nazov": okresy.at[r.okres_kod, "nazov"],
             "kraj": okresy.at[r.okres_kod, "kraj_nazov"], "pocet": int(r.pocet), "pracoviska": int(r.pocet_pracovisk),
             "na_10k": float(r.na_10k), "okolie": float(r.na_10k_okolie), "poradie_okolie": int(r.poradie_okolie),
             "mestsky": r.okres_kod in mestske}
            for r in part.itertuples()
        ]
        by_catchment = sorted(rows, key=lambda r: (r["poradie_okolie"], r["kod"]))
        okolie = [{**r, "poradie": r["poradie_okolie"], "na_10k": r["okolie"]} for r in by_catchment[:10]]
        result[typ] = {"vsetky": rows, "najhorsie": rows[:10], "najlepsie": list(reversed(rows[-10:])), "najhorsie_okolie": okolie}
    return result


def distance_shares_sr(obce, obec_ind, types, limits):
    result = {}
    for typ in types:
        rows = obec_ind[obec_ind["typ"] == typ].merge(obce, on="obec_kod")
        population = rows[DENOMINATOR[typ]]
        distance = rows["najblizsia_km"].fillna(float("inf"))
        result[typ] = {str(km): round(float(population[distance > km].sum() / population.sum()), 4) for km in limits}
    return result


def validation_summary(con, sid):
    rows = con.execute(
        "SELECT vysledok, COUNT(*) AS n FROM validacia WHERE snapshot_id = ? OR snapshot_id IS NULL GROUP BY vysledok", (sid,)
    ).fetchall()
    summary = {"OK": 0, "INFO": 0, "WARN": 0, "FAIL": 0}
    summary.update({r["vysledok"]: r["n"] for r in rows})
    return summary


def excluded_count(con, sid):
    row = con.execute(
        "SELECT hodnota FROM validacia WHERE snapshot_id = ? AND kod = 'V3.1' AND vysledok = 'INFO'", (sid,)
    ).fetchone()
    return int(row["hodnota"]) if row else 0


def precision_shares(amb, types):
    subset = amb[amb["typ"].isin(types)]
    if subset.empty:
        return {}
    return {k: round(v, 4) for k, v in subset["presnost"].value_counts(normalize=True).sort_index().items()}


def nczi_rows(con, sid, okresy, types):
    names = okresy.drop_duplicates("kraj_kod").set_index("kraj_kod")["kraj_nazov"]
    rows = con.execute(
        "SELECT * FROM nczi_porovnanie WHERE snapshot_id = ? ORDER BY typ, kraj_kod != 'SR', kraj_kod", (sid,)
    ).fetchall()
    return [
        {"typ": r["typ"], "kraj": "Slovensko" if r["kraj_kod"] == "SR" else names.get(r["kraj_kod"], r["kraj_kod"]),
         "register": r["register"], "nczi": r["nczi"], "rok": r["rok"],
         "pomer": round(r["register"] / r["nczi"], 2) if r["nczi"] else None}
        for r in rows if r["typ"] in types
    ]


def sources(cfg, con, snapshot):
    rows = {r["zdroj_id"]: r for r in con.execute("SELECT * FROM zdroj")}
    zbgis, sidla = rows.get("zbgis"), rows.get("zbgis_sidla")
    deti, dospeli = rows.get("statdata_deti"), rows.get("statdata_dospeli")
    obyvatelia = cfg["obyvatelia"]
    return [
        {"id": "udzs", "nazov": "ÚDZS – Kódy poskytovateľov zdravotnej starostlivosti", "url": snapshot["url"],
         "stav_k": snapshot["stav_k"], "sha256": snapshot["sha256"]},
        {"id": "statdata", "nazov": obyvatelia["zdroj"], "licencia": "CC BY 4.0", "atribucia": obyvatelia["atribucia"],
         "stav_k": obyvatelia["stav_k"] or None,
         "sha256": {"0-17": deti["sha256"] if deti else None, "18+": dospeli["sha256"] if dospeli else None}},
        {"id": "zbgis", "nazov": "ÚGKK SR – ZBGIS, hranice obcí", "licencia": "CC BY 4.0",
         "sha256": zbgis["sha256"] if zbgis else None},
        {"id": "zbgis_sidla", "nazov": "ÚGKK SR – ZBGIS, geografické názvy obcí (body sídiel)", "licencia": "CC BY 4.0",
         "sha256": sidla["sha256"] if sidla else None},
        {"id": "osm", "nazov": "OpenStreetMap (mapa, geokódovanie cez Nominatim)", "licencia": "ODbL",
         "atribucia": "© OpenStreetMap contributors"},
    ]


def file_kb(path):
    return path.stat().st_size / 1024


def export(cfg, con, snapshot):
    sid = snapshot["snapshot_id"]
    checks = Checks(con, "6-export", sid)
    site = project_path(cfg, "site")
    data_dir = site / "data"
    downloads = site / "downloads"
    for folder in (data_dir, downloads):
        if folder.exists():
            for old in folder.iterdir():
                old.unlink()
    types = published_types(cfg)
    stav_obyvatelstva = cfg["obyvatelia"]["stav_k"] or ""
    base = {"stav_registra": snapshot["stav_k"], "verzia_pipeline": pipeline_version()}

    okresy = pd.read_sql("SELECT * FROM okres ORDER BY okres_kod", con).set_index("okres_kod", drop=False)
    obce = pd.read_sql("SELECT * FROM obec ORDER BY obec_kod", con)
    okres_ind = pd.read_sql("SELECT * FROM ukazovatel_okres WHERE snapshot_id = ?", con, params=(sid,))
    obec_ind = pd.read_sql("SELECT * FROM ukazovatel_obec WHERE snapshot_id = ?", con, params=(sid,))
    amb = load_ambulances(con, sid)

    write_json(data_dir / "okresy.geojson", export_okresy(cfg, okresy, okres_ind, types, base))
    write_json(data_dir / "obce.json", export_obce(obce, obec_ind, types, base))
    ambulancie = export_ambulancie(amb, types, base)
    write_json(data_dir / "ambulancie.json", ambulancie)

    okres_rows, obec_rows = csv_rows(okresy, obce, okres_ind, obec_ind, types, {**base, "stav_obyvatelstva": stav_obyvatelstva})
    csv_files = {
        f"ukazovatele_okresy_{snapshot['stav_k']}.csv": (okres_rows, OKRES_CSV),
        f"ukazovatele_obce_{snapshot['stav_k']}.csv": (obec_rows, OBEC_CSV),
    }
    for name, (rows, columns) in csv_files.items():
        write_csv_rows(downloads / name, rows, columns, bom=True)

    keys_ok = all(set(item) == AMBULANCE_KEYS for item in ambulancie["ambulancie"])
    checks.check("V6.1", keys_ok, "ambulancie.json obsahuje iba povolené kľúče", ", ".join(sorted(AMBULANCE_KEYS)))
    coords_ok = all(in_slovakia(a["lat"], a["lon"]) for a in ambulancie["ambulancie"])
    checks.check("V6.3", coords_ok, "všetky súradnice ambulancií ležia v rozsahu SR")
    for path in sorted(data_dir.iterdir()):
        content = json.loads(path.read_text(encoding="utf-8"))
        meta = content.get("meta", content)
        checks.check("V6.3", bool(meta.get("stav_registra") and meta.get("verzia_pipeline")),
                     f"{path.name} sa dá načítať a nesie dátum a verziu")
    text_columns = ["okres", "kraj", "obec"]
    values = [str(r.get(c, "")) for rows, _ in csv_files.values() for r in rows for c in text_columns]
    risky = [v for v in values if v[:1] in ("=", "+", "-", "@")]
    checks.check("V6.6", not risky, "CSV neobsahuje bunky začínajúce =, +, - alebo @", f"{len(risky)} buniek")

    context = {
        "projekt": cfg["projekt"],
        "typy": types,
        "nazvy_typov": TYPE_NAMES,
        "menovatele": DENOMINATOR_NAMES,
        "stav_registra": snapshot["stav_k"],
        "stav_registra_text": format_date(snapshot["stav_k"]),
        "verzia": base["verzia_pipeline"],
        "rebricky": rankings(okresy, okres_ind, types, cfg["web"]["mestske_okresy"]),
        "pocty": {typ: int((amb["typ"] == typ).sum()) for typ in types},
        "pracoviska": {typ: int(okres_ind.loc[okres_ind["typ"] == typ, "pocet_pracovisk"].sum()) for typ in types},
        "popis_obyvatelstva": cfg["obyvatelia"]["popis"],
        "presnost": precision_shares(amb, types),
        "nczi": nczi_rows(con, sid, okresy, types),
        "atribucia_obyvatelia": cfg["obyvatelia"]["atribucia"],
        "validacia": validation_summary(con, sid),
        "subory_csv": [{"nazov": name, "kb": round(file_kb(downloads / name), 1)} for name in csv_files],
        "polomery": cfg["vypocty"]["polomery_km"],
        "podiel_nad_km": cfg["vypocty"]["podiel_nad_km"],
        "vzdialenost_sr": distance_shares_sr(obce, obec_ind, types, cfg["vypocty"]["podiel_nad_km"]),
        "spadova_oblast_km": cfg["vypocty"]["spadova_oblast_km"],
        "vylucene": excluded_count(con, sid),
    }
    pages = build_site(cfg, context, site)
    for page in pages:
        html = page.read_text(encoding="utf-8")
        checks.check("V6.4", 'data-upozornenie' in html and context["stav_registra_text"] in html and 'data-atribucie' in html,
                     f"{page.name} má upozornenie s dátumom a atribúcie")
    bad_files = [p.relative_to(site).as_posix() for p in site.rglob("*") if p.is_file() and p.suffix.lower() not in ALLOWED_EXTENSIONS]
    checks.check("V6.5", not bad_files, "v site/ sú iba povolené typy súborov", f"{len(bad_files)} nepovolených", detail=", ".join(bad_files[:20]))

    meta = {
        **base,
        "vygenerovane_utc": utc_now(),
        "stav_obyvatelstva": stav_obyvatelstva,
        "fixtures": bool(cfg.get("_fixtures")),
        "typy": types,
        "nazvy_typov": {t: TYPE_NAMES[t] for t in types},
        "menovatele": {t: DENOMINATOR_NAMES[t] for t in types},
        "stlpec_menovatela": {t: DENOMINATOR[t] for t in types},
        "legenda": {**{t: cfg["legenda"][t] for t in types}, "vzdialenost_km": cfg["legenda"]["vzdialenost_km"]},
        "polomery_km": cfg["vypocty"]["polomery_km"],
        "podiel_nad_km": context["podiel_nad_km"],
        "vzdialenost_sr": context["vzdialenost_sr"],
        "spadova_oblast_km": context["spadova_oblast_km"],
        "mestske_okresy": cfg["web"]["mestske_okresy"],
        "max_zoznam_km": cfg["vypocty"]["max_zoznam_km"],
        "poistovne": [p for p in cfg["web"]["poistovne"] if p["url"]],
        "kontakt_email": cfg["projekt"]["kontakt_email"],
        "zastarane_po_dnoch": cfg["web"]["zastarane_po_dnoch"],
        "tile_url": cfg["web"]["tile_url"],
        "zdroje": sources(cfg, con, snapshot),
        "pocty": {**context["pocty"], "vylucene_na_ziadost": context["vylucene"]},
        "pracoviska": context["pracoviska"],
        "popis_obyvatelstva": cfg["obyvatelia"]["popis"],
        "presnost_polohy": context["presnost"],
        "validacia": validation_summary(con, sid),
    }
    write_json(data_dir / "meta.json", meta, indent=2)

    limits = cfg["limity_kb"]
    for name, limit in limits.items():
        if name == "prve_nacitanie":
            continue
        size = file_kb(site / name)
        checks.check("V6.2", size <= limit, f"{name} v limite {limit} KB", f"{size:.0f} KB")
    first = sum(file_kb(site / name) for name in FIRST_LOAD)
    first += sum(file_kb(p) for p in (site / "static" / "js").glob("*.js"))
    first += sum(file_kb(p) for p in (site / "static" / "vendor").rglob("*") if p.suffix in (".js", ".css"))
    checks.check("V6.2", first <= limits["prve_nacitanie"], f"prvé načítanie bez dlaždíc v limite {limits['prve_nacitanie']} KB", f"{first:.0f} KB")
    checks.done()
