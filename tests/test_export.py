import pandas as pd

from pipeline.export import AMBULANCE_KEYS, export_ambulancie, names_in_site

META = {"stav_registra": "2026-10-01", "verzia_pipeline": "test"}


def ambulance(typ, kluc, nazov, ulica):
    return {"typ": typ, "adresa_kluc": kluc, "nazov": nazov, "ulica": ulica, "psc": "90101", "obec_text": "Testovce",
            "lat": 48.123456, "lon": 19.1, "presnost": "adresa"}


def ambulances():
    return pd.DataFrame([
        ambulance("VLD", "a", "Ambulancia Prvá", "Hlavná 1"),
        ambulance("VLD", "a", "Ambulancia Druhá", "Hlavná 1"),
        ambulance("VLDD", "a", "Ambulancia Prvá", "Hlavná 1"),
        ambulance("VLD", "b", "Ambulancia Tretia", "Dlhá 2"),
    ])


def test_without_names_groups_by_type_and_address():
    items = export_ambulancie(ambulances(), ["VLD", "VLDD"], META)["ambulancie"]
    assert all(set(item) == AMBULANCE_KEYS for item in items)
    assert sorted((i["typ"], i["adresa"], i["pocet"]) for i in items) == [
        ("VLD", "Dlhá 2, 901 01 Testovce", 1),
        ("VLD", "Hlavná 1, 901 01 Testovce", 2),
        ("VLDD", "Hlavná 1, 901 01 Testovce", 1),
    ]
    assert {i["lat"] for i in items} == {48.12346}


def test_without_names_removes_own_name_from_street():
    frame = pd.DataFrame([ambulance("VLD", "a", "Ambulancia Prvá", "Ambulancia Prvá, Hlavná 1")])
    assert export_ambulancie(frame, ["VLD"], META)["ambulancie"][0]["adresa"] == "Hlavná 1, 901 01 Testovce"
    assert export_ambulancie(frame, ["VLD"], META, with_names=True)["ambulancie"][0]["adresa"].startswith("Ambulancia Prvá,")


def test_with_names_keeps_each_provider():
    items = export_ambulancie(ambulances(), ["VLD"], META, with_names=True)["ambulancie"]
    assert all(set(item) == AMBULANCE_KEYS | {"nazov"} for item in items)
    assert sorted(i["nazov"] for i in items) == ["Ambulancia Druhá", "Ambulancia Prvá", "Ambulancia Tretia"]
    assert sum(i["pocet"] for i in items) == 3


def test_names_in_site_finds_leak_and_ignores_short_names(tmp_path):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "a.json").write_text('{"x": "Ambulancia Prvá"}', encoding="utf-8")
    (tmp_path / "index.html").write_text("Bez mien, iba Rad", encoding="utf-8")
    assert names_in_site(["Ambulancia Prvá", "Rad"], tmp_path) == ["data/a.json"]
    assert names_in_site(["Rad"], tmp_path) == []
