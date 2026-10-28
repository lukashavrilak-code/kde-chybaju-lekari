import numpy as np
import pandas as pd

from pipeline.compute import catchment_access, catchment_by_okres, distance_shares, obec_indicators, okres_indicators


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


def test_catchment_access_shares_ambulances_with_everyone_nearby():
    obce = pd.DataFrame({
        "obec_kod": ["A", "B", "C"],
        "okres_kod": ["X", "X", "Y"],
        "ref_lat": [48.00, 48.05, 48.30],
        "ref_lon": [19.0, 19.0, 19.0],
        "obyv_dospeli": [1000, 3000, 1000],
    })
    amb = pd.DataFrame({"typ": ["VLD"] * 3, "lat": [48.00, 48.15, 48.30], "lon": [19.0] * 3})
    rates, served = catchment_access(amb, obce, "VLD", 10)
    assert np.allclose(rates, [2.5, 2.5, 10.0])
    assert served == 2
    rows = pd.DataFrame({"obec_kod": obce["obec_kod"], "typ": "VLD", "na_10k_okolie": rates})
    result = catchment_by_okres(rows, obce, "VLD").set_index("okres_kod")
    assert result["na_10k_okolie"].to_dict() == {"X": 2.5, "Y": 10.0}
    assert result["poradie_okolie"].to_dict() == {"X": 1, "Y": 2}


def test_distance_shares_weighted_by_population():
    obce = pd.DataFrame({
        "obec_kod": ["1", "2", "3", "4"],
        "okres_kod": ["A", "A", "A", "B"],
        "obyv_dospeli": [100, 300, 600, 50],
    })
    rows = pd.DataFrame({"obec_kod": ["1", "2", "3", "4"], "typ": "VLD", "najblizsia_km": [3.0, 6.0, 12.0, np.nan]})
    result = distance_shares(rows, obce, "VLD", [5, 10]).set_index("okres_kod")
    assert result.loc["A", "podiel_nad_5km"] == 0.9
    assert result.loc["A", "podiel_nad_10km"] == 0.6
    assert result.loc["B", "podiel_nad_10km"] == 1.0
