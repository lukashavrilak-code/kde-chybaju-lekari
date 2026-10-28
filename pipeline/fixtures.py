import csv
import io
import shutil
from datetime import datetime

import geopandas as gpd
import openpyxl
from pyproj import Transformer
from shapely.geometry import box

from .config import ROOT
from .files import write_csv_rows
from .geocode import CACHE_COLUMNS, city_query, query_key, structured_query

BASE = "build/fixtures"
STAV_K = "2026-10-01"
CELL_M = 8000
ORIGIN_WGS = (19.50, 48.70)

OBCE = [
    ("900001", "Horná Testovka", "901", "Testovka", "91", "Testovací kraj", 0, 0, "90101"),
    ("900002", "Dolná Testovka", "901", "Testovka", "91", "Testovací kraj", 0, 1, "90102"),
    ("900003", "Pokusné Mesto", "902", "Pokusy", "91", "Testovací kraj", 1, 0, "90201"),
    ("900004", "Lúčka", "902", "Pokusy", "91", "Testovací kraj", 1, 1, "90203"),
    ("900005", "Vzorkovce", "903", "Vzorkovce", "92", "Vzorový kraj", 2, 0, "04001"),
    ("900006", "Lúčka", "903", "Vzorkovce", "92", "Vzorový kraj", 2, 1, "04003"),
]

AMBULANCIE = [
    ("P00001020201", "11111111", "Ambulancia Horná s.r.o.", 0, "Hlavná 1", None, "2015-01-01", "", "presne"),
    ("P00002020201", "22222222", "MUDr. Fiktívna Testerová", 0, "Hlavná 1", None, "2016-03-01", "", "presne"),
    ("P00003020201", "33333333", "Všeobecná ambulancia Dolná", 1, "Školská 5", None, "2018-01-01", "", "ulica"),
    ("P00004020201", "44444444", "<img src=x onerror=alert(1)>", 2, "Nová 10", None, "2019-01-01", "", "presne"),
    ("P00005020201", "55555555", "Ambulancia Pokusy", 2, "Nová 12", None, datetime(2010, 5, 1), "", "presne"),
    ("P00006020201", "66666666", "Lekár Lúčka", 3, "Lúčka 77", None, "2014-01-01", "", "chyba"),
    ("P00007020201", "77777777", "Vzorková ambulancia", 4, "Dlhá 3", 4001, "2017-01-01", "", "hranica"),
    ("P00008020201", "88888888", "Ukončená ambulancia", 4, "Dlhá 9", None, "2010-01-01", "2025-12-31", "presne"),
    ("P00009020201", "99999999", "Budúca ambulancia", 5, "Lúčka 9", None, "2027-01-01", "", "presne"),
    ("P00010020201", "10101010", "Ambulancia Vzor", 5, "Lúčka 1", "040 03", "01.02.2011", "31.12.9999", "presne"),
    ("P00011020201", "12121212", "Stará verzia záznamu", 1, "Poľná 2", None, "2012-01-01", "", "presne"),
    ("P00011020201", "12121212", "Nová verzia záznamu", 1, "Poľná 2", None, "2020-01-01", "", "presne"),
    ("P00012020201", "13131313", "Zablokovaná ambulancia", 2, "Nová 14", None, "2015-01-01", "", "presne"),
    ("P00013020201", "14141414", "Ambulancia bez adresy", None, "", None, "2015-01-01", "", "override"),
    ("P00014020201", "15151515", "Ambulancia s chybnou polohou", 1, "Lesná 8", None, "2015-01-01", "", "mimo"),
    ("P00015020601", "24242424", "Denný stacionár Pokusy", 2, "Nová 16", None, "2015-01-01", "", "presne"),
    ("P00016020202", "11111111", "Ambulancia Horná s.r.o. – druhý kód", 0, "Hlavná 1", None, "2016-01-01", "", "presne"),
    ("P00020008201", "16161616", "Detská ambulancia Horná", 0, "Hlavná 3", None, "2015-01-01", "", "presne"),
    ("P00021008201", "17171717", "Pediatria Pokusy s.r.o.", 2, "Nová 10", None, "2015-01-01", "", "presne"),
    ("P00022008201", "18181818", "Detský lekár Vzorkovce", 4, "Dlhá 5", None, "2015-01-01", "", "vedla"),
    ("P00023008201", "19191919", "Pediatria Lúčka", 5, "Lúčka 3", None, "2015-01-01", "", "presne"),
    ("P00030001201", "20202020", "Interná ambulancia", 0, "Hlavná 1", None, "2015-01-01", "", "presne"),
    ("P00031017201", "21212121", "Chirurgická ambulancia", 2, "Nová 12", None, "2015-01-01", "", "presne"),
    ("ZLYKOD", "23232323", "Záznam s chybným kódom", 0, "Hlavná 1", None, "2015-01-01", "", "presne"),
]

REGISTER_HEADER = ["ico", "pzs_kod", "nazov_pzs", "Obec", "PSC", "Ulica cislo OU", "Obec OU", "PSC OU",
                   "Platnost_od", "Platnost_do"]

NCZI = {"T2": ("Slovenská republika", 9, 3), "T2_1": ("Testovací kraj", 7, 2), "T2_2": ("Vzorový kraj", 2, 1)}
NCZI_HEADER = ["Druh odborného útvaru - výstup", "Kód odborného zamerania útvaru", "Odborné zameranie útvaru",
               "Počet útvarov", "Počet pracovných miest - Lekári"]


def path(*parts):
    return ROOT / BASE / "/".join(parts)


def population():
    return {kod: (100 + index * 37 + 0.5 * (index % 2), 500 + index * 111 + 0.5 * (index % 2))
            for index, (kod, *_rest) in enumerate(OBCE)}


def apply(cfg):
    cfg["_fixtures"] = True
    cfg["cesty"] = {key: f"{BASE}/{key}" for key in ("raw", "local", "manual", "cache", "history", "snapshots", "site")}
    cfg["register"]["min_kb"] = 0
    cfg["hranice"]["subor"] = f"{BASE}/raw/zbgis/obce.gpkg"
    cfg["hranice"]["vrstva"] = ""
    values = population().values()
    cfg["obyvatelia"].update({
        "subor_deti": f"{BASE}/raw/statdata/om7006rr_0-17.csv",
        "subor_dospeli": f"{BASE}/raw/statdata/om7006rr_18plus.csv",
        "stav_k": "2025-06-30",
        "kontrola_deti_sr": sum(d for d, _ in values),
        "kontrola_spolu_sr": sum(d + a for d, a in values),
    })
    cfg["nczi"]["povolene_domeny"] = []
    cfg["nczi"]["harky"] = {"T2": "SR", "T2_1": "91", "T2_2": "92"}
    cfg["nczi"]["kontrola_sr"] = {"VLD": NCZI["T2"][1], "VLDD": NCZI["T2"][2]}
    cfg["ocakavane"] = {"okresy": 3, "kraje": 2}
    cfg["validacia"]["ocakavane_pocty"] = {"VLD": 16, "VLDD": 4}
    cfg["validacia"]["max_zlych_kodov"] = 0.05
    cfg["zverejnit"]["VLDD"] = True
    cfg["projekt"]["prevadzkovatel"] = "Testovací prevádzkovateľ"
    cfg["projekt"]["kontakt_email"] = "test@example.org"
    for insurer in cfg["web"]["poistovne"]:
        insurer["url"] = "https://example.org/vyhladavanie-lekarov"
    cfg["legenda"]["VLD"] = [10.0, 15.0, 20.0, 25.0]
    cfg["legenda"]["VLDD"] = [40.0, 60.0, 80.0, 100.0]
    return cfg


def cell_box(transformer, column, row):
    x0, y0 = transformer.transform(*ORIGIN_WGS)
    return box(x0 + column * CELL_M, y0 + row * CELL_M, x0 + (column + 1) * CELL_M, y0 + (row + 1) * CELL_M)


def point_in_cell(transformer_back, cell, index):
    minx, miny, _, _ = cell.bounds
    lon, lat = transformer_back.transform(minx + 1000 + (index % 6) * 1000, miny + 1500 + (index % 4) * 1200)
    return round(lat, 5), round(lon, 5)


def write_boundaries(to_local):
    rows = []
    for kod, nazov, okres, okres_nazov, kraj, kraj_nazov, column, row, _ in OBCE:
        rows.append({"IDN4": kod, "NM4": nazov, "IDN3": okres, "NM3": okres_nazov, "IDN2": kraj, "NM2": kraj_nazov,
                     "geometry": cell_box(to_local, column, row)})
    target = path("raw", "zbgis", "obce.gpkg")
    target.parent.mkdir(parents=True, exist_ok=True)
    gpd.GeoDataFrame(rows, crs=5514).to_file(target, driver="GPKG")


def sk_number(value, separator):
    text = f"{value:,.1f}".replace(",", separator).replace(".", ",")
    return text.removesuffix(",0")


def statdata_rows(column, separator):
    values = {kod: pair[column] for kod, pair in population().items()}
    names = [o[1] for o in OBCE]
    rows = [["", "", "2025", "", "2024", ""],
            ["Slovenská republika", "Slovenská republika", sk_number(sum(values.values()), separator), "", "1", ""]]
    for kod, nazov, _okres, okres_nazov, *_rest in OBCE:
        label = f"{nazov}, okres {okres_nazov}" if names.count(nazov) > 1 else nazov
        rows.append([f"Okres {okres_nazov}", label, sk_number(values[kod], separator), "", "1", ""])
    rows.append(["Okres Pokusy", "Zaniknutá obec", "", "", "12", ""])
    return rows


def write_population():
    folder = path("raw", "statdata")
    folder.mkdir(parents=True, exist_ok=True)
    with open(folder / "om7006rr_0-17.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL, lineterminator="\n")
        for row in statdata_rows(0, " "):
            line = io.StringIO()
            csv.writer(line, lineterminator="").writerow(row)
            writer.writerow([line.getvalue()])
    with open(folder / "om7006rr_18plus.csv", "w", encoding="utf-8", newline="") as f:
        csv.writer(f, quoting=csv.QUOTE_ALL, lineterminator="\n").writerows(statdata_rows(1, "\xa0"))


def write_nczi():
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for sheet, (area, vld, vldd) in NCZI.items():
        ws = wb.create_sheet(sheet)
        ws.append(["Výstup o sieti poskytovateľov zdravotnej starostlivosti – umelé testovacie dáta"])
        ws.append([f"{sheet} Prehľad siete"])
        ws.append([f"Územie činnosti odborných útvarov: {area}"])
        ws.append([])
        ws.append(NCZI_HEADER)
        ws.append(["Spolu", None, None, vld + vldd + 5])
        ws.append(["ambulancia_výstup", "001", "vnútorné lekárstvo", 5, 4.5])
        ws.append(["ambulancia_výstup", "008", "všeobecná starostlivosť o deti a dorast", vldd, 1.0])
        ws.append(["ambulancia_výstup", "020", "všeobecné lekárstvo", vld, 1.0])
        ws.append(["pracovisko_výstup", "020", "všeobecné lekárstvo", 99, 0.0])
    target = path("raw", "nczi", "vystup_S01_2024_T2.xlsx")
    target.parent.mkdir(parents=True, exist_ok=True)
    wb.save(target)


def write_register():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Kódy poskytovateľov zdravotnej starostlivosti – umelé testovacie dáta"])
    ws.append(REGISTER_HEADER)
    for kod, ico, nazov, obec, ulica, psc, od, do, _ in AMBULANCIE:
        town = OBCE[obec][1] if obec is not None else ""
        psc_value = psc if psc is not None else (OBCE[obec][8] if obec is not None else "")
        ws.append([ico, kod, nazov, town, psc_value, ulica, town, psc_value, od, do])
    target = path("raw", "input", "register.xlsx")
    target.parent.mkdir(parents=True, exist_ok=True)
    wb.save(target)
    return target


def write_geocoding(to_local, to_wgs):
    cache, overrides = [], []
    for index, (kod, _ico, _nazov, obec, ulica, psc, _od, _do, kind) in enumerate(AMBULANCIE):
        if obec is None:
            cell = cell_box(to_local, OBCE[1][6], OBCE[1][7])
            lat, lon = point_in_cell(to_wgs, cell, index)
            overrides.append({"adresa_kluc": f"chyba|{kod}", "lat": lat, "lon": lon, "poznamka": "umelá ručná oprava", "datum": STAV_K})
            continue
        town, psc_default = OBCE[obec][1], OBCE[obec][8]
        psc_text = str(psc).replace(" ", "").zfill(5) if psc is not None else psc_default
        cell = cell_box(to_local, OBCE[obec][6], OBCE[obec][7])
        lat, lon = point_in_cell(to_wgs, cell, index)
        structured = query_key(structured_query(ulica, town, psc_text))
        if kind == "vedla":
            neighbour = cell_box(to_local, OBCE[obec + 1][6], OBCE[obec + 1][7])
            lat, lon = point_in_cell(to_wgs, neighbour, index)
        if kind == "hranica":
            minx, _, maxx, maxy = cell.bounds
            lon, lat = (round(v, 5) for v in to_wgs.transform((minx + maxx) / 2, maxy + 100))
        if kind in ("presne", "ulica", "vedla", "hranica"):
            rank = 26 if kind == "ulica" else 30
            cache.append({"dotaz": structured, "lat": lat, "lon": lon, "place_rank": rank, "osm_typ": "node",
                          "osm_id": 1000 + index, "addresstype": "house", "datum": STAV_K})
        elif kind == "mimo":
            cache.append({"dotaz": structured, "lat": 50.5, "lon": 19.5, "place_rank": 30, "osm_typ": "node",
                          "osm_id": 1000 + index, "addresstype": "house", "datum": STAV_K})
            cache.append({"dotaz": query_key(city_query(town, psc_text)), "lat": lat, "lon": lon, "place_rank": 16,
                          "osm_typ": "relation", "osm_id": 2000 + index, "addresstype": "village", "datum": STAV_K})
    unique = {row["dotaz"]: row for row in cache}
    write_csv_rows(path("cache", "geocode_cache.csv"), [unique[k] for k in sorted(unique)], CACHE_COLUMNS)
    write_csv_rows(path("manual", "geocode_overrides.csv"), overrides, ["adresa_kluc", "lat", "lon", "poznamka", "datum"])
    write_csv_rows(path("manual", "obec_mapping.csv"),
                   [{"obec_text": "Lúčka", "psc": "90203", "obec_kod": "900004", "poznamka": "dve obce s rovnakým názvom"}],
                   ["obec_text", "psc", "obec_kod", "poznamka"])


def write_manual():
    write_csv_rows(path("local", "blocklist.csv"),
                   [{"pzs_kod": "P00012020201", "datum": STAV_K, "typ_ziadosti": "odstranenie"},
                    {"pzs_kod": "P99999020201", "datum": STAV_K, "typ_ziadosti": "odstranenie"}],
                   ["pzs_kod", "datum", "typ_ziadosti"])


def prepare():
    shutil.rmtree(ROOT / BASE, ignore_errors=True)
    to_local = Transformer.from_crs(4326, 5514, always_xy=True)
    to_wgs = Transformer.from_crs(5514, 4326, always_xy=True)
    write_boundaries(to_local)
    write_population()
    write_nczi()
    write_geocoding(to_local, to_wgs)
    write_manual()
    return write_register()
