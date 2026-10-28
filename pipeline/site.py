import base64
import hashlib
import shutil

import markdown
from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

from .checks import PipelineError
from .config import ROOT

CSP = (
    "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data: https://tile.openstreetmap.org; "
    "connect-src 'self'; base-uri 'none'; form-action 'none'"
)
PAGES = ["index.html", "rebricky.html", "data.html", "metodika.html", "sukromie.html", "404.html"]
LEAFLET = ROOT / "web" / "static" / "vendor" / "leaflet-1.9.4"


def sk_number(value, digits=0):
    return f"{value:,.{digits}f}".replace(",", " ").replace(".", ",")


def sk_percent(value, digits=1):
    return sk_number(value * 100, digits) + " %"


def sri(path):
    return "sha384-" + base64.b64encode(hashlib.sha384(path.read_bytes()).digest()).decode()


def verified_leaflet_hashes():
    expected = {}
    for line in (LEAFLET / "SHA384SUMS").read_text(encoding="utf-8").splitlines():
        if line.strip():
            digest, name = line.split()
            expected[name] = digest
    for name, digest in expected.items():
        if sri(LEAFLET / name) != digest:
            raise PipelineError(f"Súbor {name} v priečinku vendor nezodpovedá overenému hashu SHA-384.")
    return expected


def render_markdown(name):
    text = (ROOT / "docs" / name).read_text(encoding="utf-8")
    return markdown.markdown(text, extensions=["tables", "sane_lists"], output_format="html")


def build_site(cfg, context, site_dir):
    env = Environment(
        loader=FileSystemLoader(ROOT / "web" / "templates"),
        autoescape=select_autoescape(["html"]),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["cislo"] = sk_number
    env.filters["percento"] = sk_percent
    hashes = verified_leaflet_hashes()
    context = {
        **context,
        "csp": CSP,
        "leaflet_js_sri": hashes["leaflet.js"],
        "leaflet_css_sri": hashes["leaflet.css"],
        "metodika_html": render_markdown("metodika.md"),
        "sukromie_html": render_markdown("sukromie.md"),
    }
    site_dir.mkdir(parents=True, exist_ok=True)
    static_target = site_dir / "static"
    if static_target.exists():
        shutil.rmtree(static_target)
    shutil.copytree(ROOT / "web" / "static", static_target, ignore=shutil.ignore_patterns("SHA384SUMS", "LICENSE"))
    shutil.copyfile(LEAFLET / "LICENSE", static_target / "vendor" / "leaflet-1.9.4" / "LICENSE.txt")
    pages = []
    for page in PAGES:
        html = env.get_template(page).render(**context, stranka=page)
        path = site_dir / page
        path.write_text(html, encoding="utf-8", newline="\n")
        pages.append(path)
    return pages
