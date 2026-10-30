import pandas as pd

from pipeline.export import kraj_rows
from pipeline.nczi import to_number


def test_kraj_capacity_on_hand_computed_example():
    okresy = pd.DataFrame({
        "okres_kod": ["101", "102", "201"],
        "kraj_kod": ["1", "1", "2"],
        "kraj_nazov": ["Prvý", "Prvý", "Druhý"],
        "obyv_dospeli": [10000.0, 30000.0, 10000.0],
        "obyv_deti": [2000.0, 6000.0, 2000.0],
    }).set_index("okres_kod", drop=False)
    okres_ind = pd.DataFrame({"okres_kod": ["101", "102", "201"], "typ": "VLD", "pocet": [5, 15, 4]})
    nczi = [
        {"typ": "VLD", "kraj_kod": "SR", "nczi": 20, "uvazky": 18.0},
        {"typ": "VLD", "kraj_kod": "1", "nczi": 16, "uvazky": 14.0},
        {"typ": "VLD", "kraj_kod": "2", "nczi": 4, "uvazky": 4.0},
    ]
    rows = {r["kraj_kod"]: r for r in kraj_rows(okresy, okres_ind, nczi, ["VLD"])["VLD"]}
    assert list(rows) == ["SR", "1", "2"]
    assert rows["SR"]["pocet"] == 24 and rows["SR"]["menovatel"] == 50000
    assert rows["SR"]["na_10k"] == 4.8
    assert rows["SR"]["uvazky_na_10k"] == 3.6
    assert rows["1"]["na_10k"] == 5.0
    assert rows["1"]["uvazky_na_10k"] == 3.5
    assert rows["1"]["uvazky_na_utvar"] == 0.88
    assert rows["2"]["uvazky_na_utvar"] == 1.0


def test_kraj_without_nczi_values_stays_empty():
    okresy = pd.DataFrame({"okres_kod": ["101"], "kraj_kod": ["1"], "kraj_nazov": ["Prvý"],
                           "obyv_dospeli": [10000.0], "obyv_deti": [2000.0]}).set_index("okres_kod", drop=False)
    okres_ind = pd.DataFrame({"okres_kod": ["101"], "typ": "VLD", "pocet": [3]})
    row = kraj_rows(okresy, okres_ind, [], ["VLD"])["VLD"][1]
    assert row["uvazky"] is None and row["uvazky_na_10k"] is None and row["uvazky_na_utvar"] is None


def test_empty_nczi_cell_is_zero():
    assert to_number("–") == 0.0
    assert to_number(None) == 0.0
    assert to_number("812.72") == 812.72
