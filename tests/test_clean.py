import sqlite3

from pipeline.clean import address_key, is_valid, norm_psc, register_obce
from pipeline.validate import cell_text, clean_text, parse_date


def test_norm_psc_handles_numbers_spaces_and_lost_leading_zero():
    assert norm_psc("811 01") == "81101"
    assert norm_psc("81101.0") == "81101"
    assert norm_psc("4001") == "04001"
    assert norm_psc("") == ""
    assert norm_psc("123") == ""


def test_parse_date_formats():
    assert parse_date("2026-10-01") == "2026-10-01"
    assert parse_date("1.10.2026") == "2026-10-01"
    assert parse_date("2026-10-01 00:00:00") == "2026-10-01"
    assert parse_date("31.12.9999") == "9999-12-31"
    assert parse_date("45931") == "2025-10-01"
    assert parse_date("") == ""
    assert parse_date("nikdy") is None


def test_validity_at_date():
    assert is_valid("2015-01-01", "", "2026-10-01")
    assert is_valid("2026-10-01", "2026-10-01", "2026-10-01")
    assert not is_valid("2027-01-01", "", "2026-10-01")
    assert not is_valid("2010-01-01", "2025-12-31", "2026-10-01")


def test_clean_text_removes_control_characters_and_extra_spaces():
    assert clean_text("  MUDr.\x00 Test\n\tTestová  ") == "MUDr. Test Testová"


def test_cell_text_converts_excel_numbers():
    assert cell_text(81101.0) == "81101"
    assert cell_text(None) == ""


def test_address_key_ignores_case_and_spaces():
    assert address_key("Hlavná  1", "Senec", "90301") == address_key("hlavná 1", "SENEC", "90301")


def test_register_obce_matches_names_and_city_parts_only(tmp_path):
    con = sqlite3.connect(":memory:")
    con.row_factory = sqlite3.Row
    con.execute("CREATE TABLE obec (obec_kod TEXT, nazov TEXT, kraj_kod TEXT)")
    con.executemany("INSERT INTO obec VALUES (?, ?, ?)", [
        ("1", "Bratislava-Staré Mesto", "1"), ("2", "Bratislava-Ružinov", "1"),
        ("3", "Matejovce nad Hornádom", "8"), ("4", "Nedožery-Brezany", "5"), ("5", "Senec", "1"),
    ])
    cfg = {"cesty": {"manual": str(tmp_path)}}
    addresses = [("a", "Senec", "90301"), ("b", "Bratislava", "81101"), ("c", "Bratislava - Ružinov", "82101"),
                 ("d", "Matejovce", "05951"), ("e", "Nedožery", "97212")]
    rows, missing, several_kraje = register_obce(cfg, con, addresses)
    assert sorted(rows) == [("a", "5", "nazov"), ("b", "1", "mesto"), ("b", "2", "mesto"), ("c", "2", "nazov"),
                            ("e", "4", "mesto")]
    assert missing == ["Matejovce (05951)"]
    assert several_kraje == 0
