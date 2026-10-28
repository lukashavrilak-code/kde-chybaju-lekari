import pandas as pd

from pipeline.compute import obec_indicators, okres_indicators


def test_okres_rate_and_rank_on_hand_computed_example():
    okresy = pd.DataFrame({
        "okres_kod": ["A", "B", "C"],
        "obyv_dospeli": [20000, 10000, 5000],
        "obyv_deti": [4000, 2000, 1000],
    })
    amb = pd.DataFrame({
        "typ": ["VLD"] * 7,
        "okres_kod": ["A"] * 4 + ["B"] * 2 + ["C"],
        "ico": ["1", "1", "1", "2", "3", "4", "5"],
        "adresa_kluc": ["x", "x", "y", "x", "z", "z", "w"],
    })
    result = okres_indicators(amb, okresy, "VLD").set_index("okres_kod")
    assert result.loc["A", "na_10k"] == 2.0
    assert result.loc["B", "na_10k"] == 2.0
    assert result.loc["C", "na_10k"] == 2.0
    assert set(result["poradie"]) == {1}
    assert result["pocet_pracovisk"].to_dict() == {"A": 3, "B": 2, "C": 1}

    amb = pd.DataFrame({"typ": ["VLD"] * 3, "okres_kod": ["A", "A", "B"], "ico": ["1", "2", "3"], "adresa_kluc": ["x", "x", "y"]})
    result = okres_indicators(amb, okresy, "VLD").set_index("okres_kod")
    assert result.loc["C", "pocet"] == 0
    assert result.loc["C", "poradie"] == 1
    assert result.loc["A", "poradie"] == 2
    assert result.loc["B", "poradie"] == 2


def test_obec_distances_and_counts():
    obce = pd.DataFrame({"obec_kod": ["1", "2"], "ref_lat": [48.0, 49.0], "ref_lon": [19.0, 19.0]})
    amb = pd.DataFrame({
        "typ": ["VLD", "VLD", "VLD"],
        "obec_kod": ["1", "1", "2"],
        "lat": [48.0, 48.05, 48.9],
        "lon": [19.0, 19.0, 19.0],
    })
    result = obec_indicators(amb, obce, "VLD", [10, 20]).set_index("obec_kod")
    assert result.loc["1", "najblizsia_km"] == 0
    assert result.loc["1", "pocet_10km"] == 2
    assert result.loc["1", "pocet_v_obci"] == 2
    assert round(result.loc["2", "najblizsia_km"], 1) == 11.1
    assert result.loc["2", "pocet_10km"] == 0
    assert result.loc["2", "pocet_20km"] == 1
