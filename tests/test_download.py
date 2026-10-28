from pipeline.config import load_config
from pipeline.download import find_register_link, link_date

CFG = load_config()
PAGE = "https://www.udzs-sk.sk/urad/kody-poskytovatelov-zdravotnej-starostlivosti-a-zdravotnickych-pracovnikov/"
HTML = """
<a href="/wp-content/uploads/2026/09/VyberKpWeb_1.9.2026.xlsx">september</a>
<a href="https://www.udzs-sk.sk/wp-content/uploads/2026/10/VyberKpWeb_1.10.2026.xlsx">október</a>
<a href="https://example.org/VyberKpWeb_1.12.2026.xlsx">cudzia doména</a>
<a href="http://www.udzs-sk.sk/VyberKpWeb_1.11.2026.xlsx">bez HTTPS</a>
<a href="/wp-content/uploads/2026/10/Iny_subor_1.11.2026.xlsx">iný súbor</a>
<a>bez odkazu</a>
"""


def test_find_register_link_picks_newest_allowed_file():
    url, stav_k = find_register_link(HTML, PAGE, CFG)
    assert url == "https://www.udzs-sk.sk/wp-content/uploads/2026/10/VyberKpWeb_1.10.2026.xlsx"
    assert stav_k == "2026-10-01"


def test_find_register_link_resolves_relative_href():
    url, stav_k = find_register_link('<a href="../subory/VyberKpWeb_15.1.2027.xlsx">x</a>', PAGE, CFG)
    assert url == "https://www.udzs-sk.sk/urad/subory/VyberKpWeb_15.1.2027.xlsx"
    assert stav_k == "2027-01-15"


def test_find_register_link_without_match():
    assert find_register_link("<p>nič</p>", PAGE, CFG) is None


def test_link_date():
    assert link_date("https://www.udzs-sk.sk/x/VyberKpWeb_1.10.2026.xlsx", CFG) == "2026-10-01"
    assert link_date("register.xlsx", CFG) is None
    assert link_date("VyberKpWeb_31.2.2026.xlsx", CFG) is None
