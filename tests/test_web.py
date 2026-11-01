import functools
import http.server
import json
import math
import os
import sys
import threading

import pytest

from pipeline.__main__ import StaticHandler, main
from pipeline.config import ROOT

sync_api = pytest.importorskip("playwright.sync_api")

SITE = ROOT / "build" / "fixtures" / "site"
CHANNEL = "msedge" if sys.platform == "win32" else "chrome"
PAGES = ["index.html", "rebricky.html", "data.html", "metodika.html", "sukromie.html"]
PNG_1X1 = bytes.fromhex(
    "89504E470D0A1A0A0000000D4948445200000001000000010806000000"
    "1F15C4890000000D49444154789C6360606060000000050001A5F645400000000049454E44AE426082"
)
WATCH = """
window.__csp = [];
window.__chyby = [];
document.addEventListener('securitypolicyviolation', (e) => window.__csp.push(e.violatedDirective));
window.addEventListener('unhandledrejection', (e) => window.__chyby.push(String(e.reason)));
"""
MOBILE = {"viewport": {"width": 390, "height": 700}, "is_mobile": True, "has_touch": True}


class QuietHandler(StaticHandler):
    def log_message(self, *args):
        pass


def slow_fetch(name, ms=800):
    return ("(() => { const f = window.fetch; window.fetch = (u, o) => String(u).includes('" + name + "') ? "
            f"new Promise((r) => setTimeout(r, {ms})).then(() => f(u, o)) : f(u, o); }})();")


@pytest.fixture(scope="module")
def base_url():
    assert main(["all", "--fixtures"]) == 0
    handler = functools.partial(QuietHandler, directory=str(SITE))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}/"
    server.shutdown()


@pytest.fixture(scope="module")
def browser():
    with sync_api.sync_playwright() as playwright:
        try:
            instance = playwright.chromium.launch(channel=CHANNEL, headless=True)
        except sync_api.Error:
            if os.environ.get("CI"):
                raise
            pytest.skip(f"Prehliadač {CHANNEL} nie je dostupný.")
        yield instance
        instance.close()


def expose_map(route):
    response = route.fetch()
    body = response.text().replace("zobrazSlovensko(mapa);\n  L.tileLayer", "window.__mapa = mapa; zobrazSlovensko(mapa);\n  L.tileLayer")
    route.fulfill(response=response, body=body)


def open_page(browser, url, *scripts, **options):
    context = browser.new_context(locale="sk-SK", **options)
    context.add_init_script(WATCH)
    for script in scripts:
        context.add_init_script(script)
    context.route("**/static/js/map.js", expose_map)
    context.route("https://tile.openstreetmap.org/**", lambda route: route.fulfill(status=200, content_type="image/png", body=PNG_1X1))
    page = context.new_page()
    page.errors = []
    page.on("console", lambda m: page.errors.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.goto(url, wait_until="load")
    return page


def wait_for_map(page):
    page.wait_for_selector("#legenda .titulok")
    page.wait_for_function("() => document.querySelector('#panel h2') || document.querySelector('#panel p')")


def panel_title(page):
    return page.evaluate("() => document.querySelector('#panel h2')?.textContent")


def circles(page):
    return page.evaluate("() => Object.values(window.__mapa._layers).filter((l) => l instanceof L.CircleMarker).length")


def municipality(name):
    obce = json.loads((SITE / "data" / "obce.json").read_text(encoding="utf-8"))["obce"]
    return next(o for o in obce if o["nazov"] == name)


def farthest_practice(obec):
    items = json.loads((SITE / "data" / "ambulancie.json").read_text(encoding="utf-8"))["ambulancie"]
    return max((a for a in items if a["typ"] == "VLD"), key=lambda a: math.hypot(a["lat"] - obec["lat"], a["lon"] - obec["lon"]))


def screen_point(page, lat, lon):
    return page.evaluate(
        """([lat, lon]) => {
            const p = window.__mapa.latLngToContainerPoint([lat, lon]);
            const r = document.getElementById('mapa').getBoundingClientRect();
            return [r.left + p.x, r.top + p.y];
        }""",
        [lat, lon],
    )


@pytest.mark.parametrize("options", [{"viewport": {"width": 1366, "height": 768}}, MOBILE], ids=["pocitac", "mobil"])
def test_pages_have_no_errors_and_no_overflow(browser, base_url, options):
    for name in PAGES:
        page = open_page(browser, base_url + name, **options)
        page.wait_for_timeout(200)
        assert page.errors == [], name
        assert page.evaluate("window.__csp") == [], name
        assert page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth") <= 0, name
        page.context.close()


def test_search_prefers_exact_name(browser, base_url):
    page = open_page(browser, base_url)
    wait_for_map(page)
    result = page.evaluate(
        """async () => {
            const { zoradNavrhy } = await import('./static/js/search.js');
            const obce = ['Turčiansky Martin', 'Martinček', 'Martin nad Žitavou', 'Martin'].map((nazov) => ({ nazov, kluc: nazov.toLowerCase() }));
            return zoradNavrhy(obce, 'martin').map((obec) => obec.nazov);
        }"""
    )
    assert result[0] == "Martin"
    assert result[-1] == "Turčiansky Martin"
    page.context.close()


def test_search_selection_on_phone_closes_keyboard_and_shows_summary(browser, base_url):
    page = open_page(browser, base_url, **MOBILE)
    wait_for_map(page)
    page.tap("#hladat")
    page.type("#hladat", "pokusne")
    page.wait_for_selector("#navrhy li[role=option]")
    page.tap("#navrhy li[role=option]")
    page.wait_for_selector(".karta")
    assert panel_title(page) == "Pokusné Mesto"
    assert page.evaluate("document.activeElement.id") != "hladat"
    assert page.inner_text("#lista strong") == "Pokusné Mesto"
    page.context.close()


def test_slow_layer_does_not_overwrite_newer_choice(browser, base_url):
    page = open_page(browser, base_url, slow_fetch("obce.json"))
    wait_for_map(page)
    page.check('input[name="vrstva"][value="obce"]', force=True)
    page.wait_for_timeout(100)
    page.check('input[name="vrstva"][value="okresy"]', force=True)
    page.wait_for_timeout(1200)
    assert circles(page) == 0
    assert page.inner_text("#legenda .titulok").startswith("Ambulancie")
    page.context.close()


def test_slow_practices_do_not_overwrite_newer_choice(browser, base_url):
    obec = municipality("Lúčka")
    okres = obec["okres_kod"]
    page = open_page(browser, f"{base_url}#obec={obec['kod']}", slow_fetch("ambulancie.json"))
    page.wait_for_selector("#legenda .titulok")
    page.wait_for_function("() => document.querySelector('#panel').getAttribute('aria-busy') === 'true'")
    page.evaluate(f"location.hash = '#okres={okres}'")
    page.wait_for_timeout(1200)
    assert (panel_title(page) or "").startswith("Okres")
    assert page.evaluate("document.querySelector('#panel').getAttribute('aria-busy')") is None
    assert page.locator(".karta").count() == 0
    page.context.close()


def test_failed_municipality_list_shows_message(browser, base_url):
    page = open_page(browser, "about:blank")
    page.route("**/data/obce.json", lambda route: route.fulfill(status=500, body="chyba"))
    page.goto(base_url, wait_until="load")
    wait_for_map(page)
    page.click("#hladat")
    page.type("#hladat", "lu")
    page.wait_for_selector("#navrhy li")
    assert "nepodarilo" in page.inner_text("#navrhy")
    assert page.evaluate("window.__chyby") == []
    page.context.close()


def test_reset_returns_to_whole_country(browser, base_url):
    obec = municipality("Lúčka")
    page = open_page(browser, base_url)
    wait_for_map(page)
    start_zoom = page.evaluate("window.__mapa.getZoom()")
    page.evaluate(f"location.hash = '#typ=VLDD&obec={obec['kod']}'")
    page.wait_for_selector(".karta, #panel dl.suhrn")
    assert page.input_value("#hladat") == "Lúčka"
    assert page.evaluate("window.__mapa.getZoom()") > start_zoom
    page.wait_for_timeout(400)
    page.click(".mapa-slovensko")
    page.wait_for_function("() => document.querySelector('#panel h2')?.textContent === 'Ako čítať mapu'")
    assert page.input_value("#hladat") == ""
    assert page.evaluate("location.hash") == "#typ=VLDD"
    page.wait_for_function(f"() => window.__mapa.getZoom() === {start_zoom}")
    page.context.close()


def test_tap_on_point_keeps_map_and_bar_navigates(browser, base_url):
    obec = municipality("Pokusné Mesto")
    target = farthest_practice(obec)
    page = open_page(browser, f"{base_url}#obec={obec['kod']}", **MOBILE)
    page.wait_for_selector(".karta")
    page.wait_for_timeout(300)
    page.touchscreen.tap(*screen_point(page, target["lat"], target["lon"]))
    page.wait_for_selector(".karta.aktivna", state="attached")
    assert page.evaluate("window.scrollY") == 0
    assert page.inner_text("#lista strong") == target["adresa"]
    assert page.inner_text("#lista button").startswith("Detail")
    page.tap("#lista button")
    page.wait_for_function("() => window.scrollY > 0")
    assert page.evaluate("document.querySelector('.karta.aktivna').getBoundingClientRect().top < innerHeight")
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    page.wait_for_function("() => document.querySelector('#lista button').textContent.includes('Mapa')")
    page.tap("#lista button")
    page.wait_for_function("() => document.getElementById('mapa').getBoundingClientRect().top < innerHeight")
    page.context.close()


def test_html_in_address_stays_text(browser, base_url):
    obec = municipality("Pokusné Mesto")
    data = json.loads((SITE / "data" / "ambulancie.json").read_text(encoding="utf-8"))
    for item in data["ambulancie"]:
        item["adresa"] = "<img src=x onerror=window.__xss=1>"
    page = open_page(browser, "about:blank")
    page.route("**/data/ambulancie.json", lambda route: route.fulfill(status=200, content_type="application/json", body=json.dumps(data)))
    page.goto(f"{base_url}#obec={obec['kod']}", wait_until="load")
    page.wait_for_selector(".karta")
    assert page.locator("#panel img").count() == 0
    assert "<img src=x" in page.inner_text(".karta h3")
    assert page.evaluate("window.__xss") is None
    page.context.close()
