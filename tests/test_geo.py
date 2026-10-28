import math

import geopandas as gpd
from shapely.geometry import Point, box

from pipeline.areas import norm_name, settlement_points
from pipeline.compute import haversine_km
from pipeline.geocode import (
    Geocoder,
    Locator,
    clean_street,
    precision,
    query_key,
    street_variants,
    structured_query,
    swap_number,
    village_query,
)

PREFIXES = ["ul.", "ZS", "Zdravotné stredisko"]


def test_haversine_one_degree_latitude():
    assert math.isclose(haversine_km(48.0, 19.0, 49.0, 19.0), 6371.0 * math.pi / 180, rel_tol=1e-9)
    assert haversine_km(48.5, 19.5, 48.5, 19.5) == 0


def test_norm_name_ignores_diacritics_and_dashes():
    assert norm_name("Bratislava - Petržalka") == norm_name("Bratislava-Petržalka") == "bratislava petrzalka"


def test_settlement_point_must_lie_in_own_obec_else_center():
    obce = gpd.GeoDataFrame({"obec_kod": ["1", "2", "3"]}, geometry=[box(0, 0, 10, 10), box(10, 0, 20, 10), box(20, 0, 30, 10)],
                            crs=5514)
    sidla = gpd.GeoDataFrame({"obec_kod": ["1", "2", "9"]}, geometry=[Point(2, 3), Point(5, 5), Point(25, 5)], crs=5514)
    points, sources = settlement_points(obce, sidla)
    assert list(sources) == ["sidlo", "stred", "stred"]
    assert [(p.x, p.y) for p in points] == [(2, 3), (15, 5), (25, 5)]


def test_precision_from_place_rank():
    assert precision("30") == "adresa"
    assert precision(26) == "ulica"
    assert precision("16") == "obec"
    assert precision("") == "obec"


def test_query_key_is_stable():
    assert query_key(structured_query("Hlavná 1", "Senec", "90301")) == "city=Senec&postalcode=90301&street=Hlavná 1"


def test_locator_finds_point_and_rejects_point_outside():
    obce = gpd.GeoDataFrame(
        {"obec_kod": ["1", "2"], "obec_nazov": ["Bratislava - Petržalka", "Senec"]},
        geometry=[box(-500000, -1250000, -499000, -1249000), box(-499000, -1250000, -498000, -1249000)],
        crs=5514,
    )
    locator = Locator(obce)
    inside = gpd.GeoSeries.from_xy([-499500], [-1249500], crs=5514).to_crs(4326)[0]
    index = locator.find(inside.y, inside.x)
    assert obce.iloc[index]["obec_kod"] == "1"
    assert locator.find(inside.y + 1, inside.x) is None
    assert locator.distance_km(inside.y, inside.x, ["1"]) == 0
    assert math.isclose(locator.distance_km(inside.y, inside.x, ["2"]), 0.5, rel_tol=0.01)
    assert locator.nearest(inside.y, inside.x, ["2", "1"]) == ("1", 0)
    assert locator.names(["2", "1"]) == "Senec, Bratislava - Petržalka"
    minlon, maxlat, maxlon, minlat = (float(v) for v in locator.viewbox(["1", "2"]).split(","))
    assert minlon < inside.x < maxlon and minlat < inside.y < maxlat


def test_clean_street_and_number_variants():
    assert clean_street("ul. Daniela Dlabača 770/23", PREFIXES) == "Daniela Dlabača 770/23"
    assert clean_street("ul.Hlavná 5", PREFIXES) == "Hlavná 5"
    assert clean_street("Dolná č. 49/21", PREFIXES) == "Dolná 49/21"
    assert clean_street("ZS Oravský Podzámok 34", PREFIXES) == "Oravský Podzámok 34"
    assert clean_street("ZSNP 2", PREFIXES) == "ZSNP 2"
    assert clean_street("Ulica mieru 1390", PREFIXES) == "Ulica mieru 1390"
    assert swap_number("Levočská 59/1808") == "Levočská 1808/59"
    assert swap_number("Daxnerova 906/III") == "Daxnerova 906/III"


def test_village_query_only_for_addresses_without_street():
    assert village_query("Bzenov 37", "Bzenov", "08241") == {"q": "37, Bzenov, 08241"}
    assert village_query("37", "Bzenov", "") == {"q": "37, Bzenov"}
    assert village_query("Oravský Podzámok 34", "Oravský Podzámok", "02741") == {"q": "34, Oravský Podzámok, 02741"}
    assert village_query("Hlavná 1", "Bzenov", "08241") is None


def test_street_variants_skip_original_and_duplicates():
    variants = street_variants("Bzenov 37", "Bzenov", "08241", PREFIXES)
    assert variants == [{"q": "37, Bzenov, 08241"}]
    variants = street_variants("ul. Levočská 59/1808", "Poprad", "05801", PREFIXES)
    assert [v["street"] for v in variants] == ["Levočská 59/1808", "Levočská 1808/59"]


class FakeNominatim:
    def search(self, params):
        return {"lat": "48.1", "lon": "17.1", "place_rank": 30}


def test_geocoder_stops_after_query_limit(tmp_path):
    cfg = {"cesty": {"cache": str(tmp_path)}}
    geocoder = Geocoder(cfg, offline=False, max_new=1)
    geocoder.client = FakeNominatim()
    assert geocoder.lookup({"city": "A"})["lat"] == "48.1"
    assert geocoder.lookup({"city": "B"}) is None
    assert geocoder.limit_reached
    assert geocoder.lookup({"city": "A"})["lat"] == "48.1"
