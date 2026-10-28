from pipeline.areas import norm_name, parse_number, read_statdata, statdata_key
from pipeline.config import load_config

DOUBLE_QUOTED = (
    '",,""2025"",,""2024"","\n'
    '"Slovenská republika,Slovenská republika,""1 020 767"",,""1 028 343"","\n'
    '"Okres Lučenec,""Mikušovce, okes Lučenec"",""50"",,""51,5"","\n'
    '"Okres Poltár,Pinciná,,,""26"","\n'
)
PLAIN = (
    '"","","2025","","2024",""\n'
    '"Slovenská republika","Slovenská republika","4\xa0393\xa0662","","4 393 726",""\n'
    '"Okres Bratislava I","Bratislava - mestská časť Staré Mesto","39 322,5","","39 062",""\n'
)


def test_parse_number():
    assert parse_number("1 020 767") == 1020767
    assert parse_number("4\xa0393\xa0662") == 4393662
    assert parse_number("171,5") == 171.5
    assert parse_number("") is None


def test_read_statdata_double_quoted_lines(tmp_path):
    path = tmp_path / "deti.csv"
    path.write_text(DOUBLE_QUOTED, encoding="utf-8")
    sr, rows = read_statdata(path, "2025")
    assert sr == 1020767
    assert rows == [("Okres Lučenec", "Mikušovce, okes Lučenec", 50.0), ("Okres Poltár", "Pinciná", None)]
    _, older = read_statdata(path, "2024")
    assert older[0][2] == 51.5


def test_read_statdata_plain_csv(tmp_path):
    path = tmp_path / "dospeli.csv"
    path.write_text(PLAIN, encoding="utf-8-sig")
    sr, rows = read_statdata(path, "2025")
    assert sr == 4393662
    assert rows == [("Okres Bratislava I", "Bratislava - mestská časť Staré Mesto", 39322.5)]


def test_statdata_key_matches_zbgis_names():
    assert statdata_key("Okres Bratislava I", "Bratislava - mestská časť Staré Mesto") == (
        norm_name("Bratislava I"), norm_name("Bratislava-Staré Mesto"))
    assert statdata_key("Okres Bánovce nad Bebravou", "Čierna Lehota, okres Bánovce nad Bebravou") == (
        norm_name("Bánovce nad Bebravou"), norm_name("Čierna Lehota"))
    assert statdata_key("Okres Lučenec", "Mikušovce, okes Lučenec") == (norm_name("Lučenec"), norm_name("Mikušovce"))


def test_local_config_overrides_only_given_keys(tmp_path):
    local = tmp_path / "config.local.toml"
    local.write_text('[projekt]\nkontakt_email = "test@example.org"\n', encoding="utf-8")
    cfg = load_config(local_path=local)
    assert cfg["projekt"]["kontakt_email"] == "test@example.org"
    assert cfg["projekt"]["nazov"]
    assert cfg["register"]["povolene_domeny"]
