import csv
import re
import unicodedata

import geopandas as gpd
import pandas as pd
import shapely

from .checks import Checks, PipelineError, utc_now
from .config import ROOT, project_path
from .files import sha256_file


def norm_code(value):
    text = str(value).strip()
    return text.removesuffix(".0")


def norm_name(text):
    text = unicodedata.normalize("NFKD", str(text))
    text = "".join(ch for ch in text if not unicodedata.combining(ch)).lower()
    text = re.sub(r"[-–—]", " ", text)
    return " ".join(text.split())


def areas_dir(cfg):
    return project_path(cfg, "local") / "uzemia"


def reference_points(geometries):
    points = geometries.centroid
    outside = ~points.within(geometries)
    points[outside] = geometries[outside].representative_point()
    return points


def read_settlements(cfg):
    settings = cfg["hranice"]["sidla"]
    path = ROOT / settings["subor"]
    if not path.exists():
        raise PipelineError(f"Chýba súbor sídiel ZBGIS {settings['subor']} (docs/runbook.md, Prvé nastavenie).")
    frame = gpd.read_file(path, layer=settings["vrstva"] or None)
    frame = frame[~frame[settings["stlpec_kategoria"]].isin(settings["vynechat_kategorie"])].copy()
    frame["obec_kod"] = frame[settings["stlpec_kod"]].map(norm_code)
    return path, frame[["obec_kod", "geometry"]]


def settlement_points(obce, settlements):
    points = settlements.to_crs(obce.crs).drop_duplicates("obec_kod").set_index("obec_kod").geometry
    centers = reference_points(obce.geometry)
    chosen, sources = [], []
    for kod, area, center in zip(obce["obec_kod"], obce.geometry, centers):
        point = points.get(kod)
        if point is not None and area.covers(point):
            chosen.append(point)
            sources.append("sidlo")
        else:
            chosen.append(center)
            sources.append("stred")
    return gpd.GeoSeries(chosen, index=obce.index, crs=obce.crs), pd.Series(sources, index=obce.index)


def read_boundaries(cfg, checks):
    settings = cfg["hranice"]
    path = ROOT / settings["subor"]
    frame = gpd.read_file(path, layer=settings["vrstva"] or None)
    epsg = frame.crs.to_epsg(min_confidence=20) if frame.crs else None
    checks.check("V1.5", epsg == settings["epsg"], f"hranice sú v EPSG:{settings['epsg']}",
                 f"EPSG:{epsg}" if epsg else (frame.crs.name if frame.crs else "bez CRS"))
    checks.done()
    columns = settings["stlpce"]
    checks.check("V1.5", all(c in frame.columns for c in columns.values()), "hranice majú očakávané atribúty",
                 detail=f"dostupné: {[c for c in frame.columns if c != 'geometry']}")
    checks.done()
    frame = frame.rename(columns={v: k for k, v in columns.items()})[[*columns.keys(), "geometry"]]
    for col in ("obec_kod", "okres_kod", "kraj_kod"):
        frame[col] = frame[col].map(norm_code)
    frame["geometry"] = shapely.force_2d(frame.geometry.values)
    invalid = ~frame.geometry.is_valid
    if invalid.any():
        frame.loc[invalid, "geometry"] = shapely.make_valid(
            frame.geometry[invalid].values, method="structure", keep_collapsed=False
        )
    return path, frame


def parse_number(text):
    text = text.replace("\xa0", "").replace(" ", "").replace(",", ".").strip()
    return float(text) if text else None


def read_statdata(path, rok):
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = [next(csv.reader([r[0]])) if len(r) == 1 else r for r in csv.reader(f) if r]
    if rok not in rows[0]:
        raise PipelineError(f"V súbore {path.name} chýba stĺpec za rok {rok}.")
    col = rows[0].index(rok)
    sr, obce = None, []
    for row in rows[1:]:
        if len(row) <= col:
            continue
        parent, name, value = row[0].strip(), row[1].strip(), parse_number(row[col])
        if parent == name == "Slovenská republika":
            sr = value
        elif parent.startswith("Okres "):
            obce.append((parent, name, value))
    return sr, obce


def statdata_key(okres, nazov):
    okres = okres.removeprefix("Okres ")
    nazov = nazov.split(",")[0].replace(" - mestská časť ", "-")
    return norm_name(okres), norm_name(nazov)


def join_statdata(path, rok, obce, keys, checks):
    sr, rows = read_statdata(path, rok)
    values, duplicates, unmatched, empty = {}, [], [], []
    for okres, nazov, value in rows:
        kod = keys.get(statdata_key(okres, nazov))
        if kod is None:
            (empty if value is None else unmatched).append(f"{okres}: {nazov}")
        elif kod in values:
            duplicates.append(f"{okres}: {nazov}")
        else:
            values[kod] = value
    missing = [kod for kod in obce["obec_kod"] if values.get(kod) is None]
    name = path.name
    checks.check("V3.5", not missing, f"{name}: každá obec ZBGIS má počet obyvateľov",
                 f"{len(obce) - len(missing)} z {len(obce)}", detail=", ".join(missing[:20]))
    checks.check("V3.5", not duplicates, f"{name}: žiadna obec nie je v súbore dvakrát", f"{len(duplicates)} duplicít",
                 detail=", ".join(duplicates[:20]))
    checks.check("V3.5", not unmatched, f"{name}: každý riadok s hodnotou sa spojil s obcou ZBGIS",
                 f"{len(unmatched)} nespojených", detail=", ".join(unmatched[:20]))
    if empty:
        checks.info("V3.5", f"{name}: riadky bez hodnoty za {rok} (zaniknuté územia), nepoužité", ", ".join(empty))
    total = sum(v for v in values.values() if v is not None)
    checks.check("V3.5", sr is not None and abs(total - sr) < 0.01, f"{name}: súčet obcí sa rovná riadku Slovenská republika",
                 f"{total:.1f} / {sr}")
    return pd.Series(values, dtype=float)


def read_population(cfg, obce, checks):
    settings = cfg["obyvatelia"]
    keys = {
        (norm_name(okres), norm_name(nazov)): kod
        for kod, okres, nazov in zip(obce["obec_kod"], obce["okres_nazov"], obce["obec_nazov"])
    }
    paths = {"obyv_deti": ROOT / settings["subor_deti"], "obyv_dospeli": ROOT / settings["subor_dospeli"]}
    result = pd.DataFrame(index=obce["obec_kod"])
    for column, path in paths.items():
        result[column] = join_statdata(path, settings["rok"], obce, keys, checks)
    result = result.fillna(0.0)
    result["obyv_spolu"] = result["obyv_deti"] + result["obyv_dospeli"]
    deti, spolu = result["obyv_deti"].sum(), result["obyv_spolu"].sum()
    checks.check("V3.5", abs(deti - settings["kontrola_deti_sr"]) < 0.01, "obyvatelia 0 – 17 za SR sa rovnajú kontrolnej hodnote",
                 f"{deti:.1f} (očakávané {settings['kontrola_deti_sr']})")
    checks.check("V3.5", abs(spolu - settings["kontrola_spolu_sr"]) < 0.01, "obyvatelia spolu za SR sa rovnajú kontrolnej hodnote",
                 f"{spolu:.1f} (očakávané {settings['kontrola_spolu_sr']})")
    checks.info("V3.5", f"obyvatelia SR {settings['rok']}: 0 – 17 / 18+ / spolu",
                f"{deti:.1f} / {result['obyv_dospeli'].sum():.1f} / {spolu:.1f}")
    return paths, result


def save_source(con, zdroj_id, path, stav_k=None):
    con.execute(
        "INSERT OR REPLACE INTO zdroj (zdroj_id, subor, sha256, stav_k, nacitane_utc) VALUES (?, ?, ?, ?, ?)",
        (zdroj_id, path.name, sha256_file(path), stav_k, utc_now()),
    )


def build_areas(cfg, con):
    checks = Checks(con, "3-areas")
    expected = cfg["ocakavane"]
    boundaries_path, obce = read_boundaries(cfg, checks)

    geometry_ok = obce.geometry.notna() & ~obce.geometry.is_empty & obce.geometry.is_valid
    checks.check("V3.4", bool(geometry_ok.all()), "geometrie obcí sú platné a neprázdne", f"{int((~geometry_ok).sum())} chybných")
    checks.check("V3.4", obce["obec_kod"].is_unique, "kód obce je jedinečný", f"{len(obce)} obcí")
    okres_count = obce["okres_kod"].nunique()
    kraj_count = obce["kraj_kod"].nunique()
    checks.check("V3.4", okres_count == expected["okresy"], "počet okresov", okres_count)
    checks.check("V3.4", kraj_count == expected["kraje"], "počet krajov", kraj_count)
    per_okres = obce.groupby("okres_kod")["kraj_kod"].nunique()
    checks.check("V3.4", bool((per_okres == 1).all()), "každý okres patrí do práve jedného kraja")

    population_paths, population = read_population(cfg, obce, checks)
    checks.done()

    obce = obce.merge(population, left_on="obec_kod", right_index=True, how="left")
    settlements_path, settlements = read_settlements(cfg)
    points, sources = settlement_points(obce, settlements)
    fallback = obce.loc[sources == "stred", "obec_nazov"]
    checks.check("V3.9", fallback.empty, "každá obec má bod sídla zo ZBGIS vo svojom území (inak sa použije geometrický stred)",
                 f"{len(obce) - len(fallback)} z {len(obce)}", "WARN", detail=", ".join(fallback.head(40)))
    reference = points.to_crs(4326)
    obce["ref_lat"] = reference.y.round(5)
    obce["ref_lon"] = reference.x.round(5)
    obce["ref_zdroj"] = sources

    okresy = obce.dissolve(
        by="okres_kod",
        aggfunc={"okres_nazov": "first", "kraj_kod": "first", "kraj_nazov": "first",
                 "obyv_spolu": "sum", "obyv_deti": "sum", "obyv_dospeli": "sum"},
    ).reset_index()
    simplified = shapely.coverage_simplify(okresy.geometry.values, cfg["hranice"]["zjednodusenie_okresy_m"])
    area_change = (abs(shapely.area(simplified) - okresy.geometry.area) / okresy.geometry.area).max()
    checks.check("V3.6", area_change <= cfg["validacia"]["max_zmena_plochy"], "zjednodušenie hraníc mení plochu okresu najviac o limit",
                 f"{area_change:.2%}", "WARN")

    folder = areas_dir(cfg)
    folder.mkdir(parents=True, exist_ok=True)
    for name in ("obce.gpkg", "okresy_web.geojson"):
        (folder / name).unlink(missing_ok=True)
    obce[["obec_kod", "obec_nazov", "okres_kod", "kraj_kod", "geometry"]].to_file(folder / "obce.gpkg", driver="GPKG")
    web = gpd.GeoDataFrame(okresy[["okres_kod"]], geometry=simplified, crs=okresy.crs).to_crs(4326)
    web.to_file(folder / "okresy_web.geojson", driver="GeoJSON")

    con.execute("DELETE FROM obec")
    con.executemany(
        "INSERT INTO obec (obec_kod, nazov, okres_kod, kraj_kod, ref_lat, ref_lon, ref_zdroj, obyv_spolu, obyv_deti, obyv_dospeli) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (r.obec_kod, r.obec_nazov, r.okres_kod, r.kraj_kod, r.ref_lat, r.ref_lon, r.ref_zdroj,
             float(r.obyv_spolu), float(r.obyv_deti), float(r.obyv_dospeli))
            for r in obce.itertuples()
        ],
    )
    con.execute("DELETE FROM okres")
    con.executemany(
        "INSERT INTO okres (okres_kod, nazov, kraj_kod, kraj_nazov, obyv_spolu, obyv_deti, obyv_dospeli) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            (r.okres_kod, r.okres_nazov, r.kraj_kod, r.kraj_nazov,
             float(r.obyv_spolu), float(r.obyv_deti), float(r.obyv_dospeli))
            for r in okresy.itertuples()
        ],
    )
    save_source(con, "zbgis", boundaries_path)
    save_source(con, "zbgis_sidla", settlements_path)
    stav_k = cfg["obyvatelia"]["stav_k"] or None
    save_source(con, "statdata_deti", population_paths["obyv_deti"], stav_k)
    save_source(con, "statdata_dospeli", population_paths["obyv_dospeli"], stav_k)
    checks.done()
