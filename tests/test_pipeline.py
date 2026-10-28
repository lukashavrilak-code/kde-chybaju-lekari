import json
import sqlite3

from pipeline.__main__ import main
from pipeline.config import ROOT
from pipeline.export import AMBULANCE_KEYS
from pipeline.files import read_csv_rows, sha256_file

BASE = ROOT / "build" / "fixtures"
SITE = BASE / "site"


def data_hashes():
    return {p.name: sha256_file(p) for p in sorted((SITE / "data").iterdir()) if p.name != "meta.json"}


def test_full_pipeline_on_fixtures_is_valid_and_deterministic():
    assert main(["all", "--fixtures"]) == 0
    meta = json.loads((SITE / "data" / "meta.json").read_text(encoding="utf-8"))
    assert meta["validacia"]["FAIL"] == 0
    assert meta["fixtures"] is True
    assert meta["pocty"] == {"VLD": 12, "VLDD": 4, "vylucene_na_ziadost": 1}
    assert meta["pracoviska"] == {"VLD": 11, "VLDD": 4}
    statdata = next(z for z in meta["zdroje"] if z["id"] == "statdata")
    assert statdata["atribucia"] == "Zdroj: Štatistický úrad SR, CC BY 4.0, www.statistics.sk"
    assert set(meta["vzdialenost_sr"]) == {"VLD", "VLDD"} and set(meta["vzdialenost_sr"]["VLD"]) == {"5", "10"}
    assert meta["mestske_okresy"] == ["902"] and meta["spadova_oblast_km"] == 10

    snapshot = BASE / "snapshots" / "udzs" / "2026-10-01.xlsx"
    assert (BASE / "snapshots" / "udzs" / "2026-10-01.xlsx.sha256").read_text(encoding="utf-8").split()[0] == sha256_file(snapshot)

    con = sqlite3.connect(BASE / "local" / "lekari.sqlite")
    try:
        assert con.execute("SELECT COUNT(*) FROM adresa_obec").fetchone()[0] > 0
        assert con.execute("SELECT COUNT(*) FROM nczi_porovnanie").fetchone()[0] == 6
        nczi_results = {r[0] for r in con.execute("SELECT vysledok FROM validacia WHERE kod = 'V3.7'")}
        assert "WARN" in nczi_results and "FAIL" not in nczi_results
        assert sum(r[0] for r in con.execute("SELECT obyv_deti FROM obec")) == 1156.5
        assert not con.execute("SELECT * FROM validacia WHERE kod = 'V4.3' AND vysledok = 'WARN'").fetchall()
        assert con.execute("SELECT obec_kod, zdroj FROM geokod WHERE adresa_kluc = 'dlhá 3|vzorkovce|04001'").fetchone() == (
            "900005", "nominatim")
        assert con.execute("SELECT presnost, zdroj FROM geokod WHERE adresa_kluc = 'dlhá 5|vzorkovce|04001'").fetchone() == (
            "obec", "stred_obce")
        assert con.execute("SELECT SUM(pocet), SUM(pocet_pracovisk) FROM ukazovatel_okres WHERE typ = 'VLD'").fetchone() == (12, 11)
        assert con.execute("SELECT obec_kod, ref_zdroj FROM obec ORDER BY obec_kod").fetchall() == [
            ("900001", "sidlo"), ("900002", "sidlo"), ("900003", "sidlo"), ("900004", "stred"), ("900005", "stred"),
            ("900006", "sidlo")]
        assert con.execute("SELECT vysledok, hodnota FROM validacia WHERE kod = 'V3.9'").fetchall() == [("WARN", "4 z 6")]
        assert con.execute("SELECT COUNT(*) FROM validacia WHERE kod = 'V5.6' AND vysledok = 'INFO'").fetchone()[0] == 2
        assert con.execute("SELECT COUNT(*) FROM validacia WHERE kod = 'V5.7' AND vysledok = 'OK'").fetchone()[0] == 2
    finally:
        con.close()
    mismatches = read_csv_rows(BASE / "local" / "reports" / "geokod_mimo_obce_2026-10-01.csv")
    assert [(m["obec_v_registri"], m["obec_podla_bodu"], m["riesenie"]) for m in mismatches] == [
        ("Vzorkovce", "Lúčka", "stred obce"),
        ("Vzorkovce", "Lúčka", "tolerancia pri hranici obce"),
    ]
    okresy = json.loads((SITE / "data" / "okresy.geojson").read_text(encoding="utf-8"))["features"]
    assert sum(f["properties"]["vld_pracoviska"] for f in okresy) == 11
    assert all({"vld_nad5", "vld_nad10", "vldd_nad5", "vldd_nad10"} <= set(f["properties"]) for f in okresy)
    assert all({"vld_okolie", "vld_poradie_okolie", "vldd_okolie", "vldd_poradie_okolie"} <= set(f["properties"]) for f in okresy)
    okres_csv = read_csv_rows(next((SITE / "downloads").glob("ukazovatele_okresy_*.csv")))
    assert "pocet_pracovisk" in okres_csv[0] and "podiel_nad_10km" in okres_csv[0] and "na_10k_okolie" in okres_csv[0]
    rebricky = (SITE / "rebricky.html").read_text(encoding="utf-8")
    assert 'id="mestske-okresy"' in rebricky and 'href="#mestske-okresy"' in rebricky
    assert "stredný stav 2025" in (SITE / "metodika.html").read_text(encoding="utf-8")

    ambulancie = json.loads((SITE / "data" / "ambulancie.json").read_text(encoding="utf-8"))["ambulancie"]
    assert all(set(a) == AMBULANCE_KEYS for a in ambulancie)
    names = {a["nazov"] for a in ambulancie}
    assert "Zablokovaná ambulancia" not in names
    assert "Ukončená ambulancia" not in names
    assert "Denný stacionár Pokusy" not in names
    assert "Nová verzia záznamu" in names and "Stará verzia záznamu" not in names

    for page in SITE.glob("*.html"):
        html = page.read_text(encoding="utf-8")
        assert "<img src=x" not in html
        assert "Content-Security-Policy" in html

    first = data_hashes()
    assert main(["export", "--fixtures"]) == 0
    assert data_hashes() == first

    register = str(BASE / "raw" / "input" / "register.xlsx")
    assert main(["download", "--fixtures", "--subor", register]) == 0
    con = sqlite3.connect(BASE / "local" / "lekari.sqlite")
    try:
        assert con.execute("SELECT COUNT(*) FROM snapshot").fetchone()[0] == 1
        con.execute("DELETE FROM snapshot")
        con.commit()
        assert main(["download", "--fixtures", "--subor", register]) == 0
        assert con.execute("SELECT subor FROM snapshot").fetchall() == [("build/fixtures/snapshots/udzs/2026-10-01.xlsx",)]
    finally:
        con.close()
    assert sorted(p.name for p in (BASE / "snapshots" / "udzs").iterdir()) == ["2026-10-01.xlsx", "2026-10-01.xlsx.sha256"]
