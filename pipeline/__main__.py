import argparse
import functools
import http.server
import sys
from typing import ClassVar

from . import db, fixtures
from .areas import build_areas
from .backup import backup
from .checks import PipelineError
from .clean import clean
from .compute import compute
from .config import load_config, project_path
from .deploy import deploy
from .download import check_for_update, download
from .export import export
from .geocode import geocode
from .nczi import nczi
from .validate import validate

COMMANDS = ["download", "validate", "clean", "areas", "nczi", "geocode", "compute", "export", "all", "report", "serve",
            "deploy", "skontroluj", "zaloha"]
NEW_REGISTER_EXIT = 10


class StaticHandler(http.server.SimpleHTTPRequestHandler):
    extensions_map: ClassVar[dict] = {
        **http.server.SimpleHTTPRequestHandler.extensions_map,
        ".js": "text/javascript",
        ".json": "application/json",
        ".geojson": "application/geo+json",
        ".csv": "text/csv",
    }


def serve(cfg, port):
    site = project_path(cfg, "site")
    handler = functools.partial(StaticHandler, directory=str(site))
    with http.server.ThreadingHTTPServer(("127.0.0.1", port), handler) as server:
        print(f"Náhľad: http://127.0.0.1:{port}/  (ukončenie: Ctrl+C)")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


def write_report(cfg, con, snapshot):
    rows = con.execute(
        "SELECT * FROM validacia WHERE snapshot_id = ? OR snapshot_id IS NULL ORDER BY krok, kod", (snapshot["snapshot_id"],)
    ).fetchall()
    lines = [f"# Validácia – register k {snapshot['stav_k']}", "", "| Krok | Kód | Výsledok | Kontrola | Hodnota | Detail |",
             "|---|---|---|---|---|---|"]
    for r in rows:
        cells = [r["krok"], r["kod"], r["vysledok"], r["popis"], r["hodnota"] or "", (r["detail"] or "")[:200]]
        lines.append("| " + " | ".join(str(c).replace("|", "/") for c in cells) + " |")
    path = project_path(cfg, "local") / "reports" / f"validacia_{snapshot['stav_k']}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    counts = {}
    for r in rows:
        counts[r["vysledok"]] = counts.get(r["vysledok"], 0) + 1
    print(f"Report: {path}  ({', '.join(f'{k}: {v}' for k, v in sorted(counts.items()))})")


def run(args):
    cfg = load_config()
    if args.fixtures:
        fixtures.apply(cfg)
    if args.prikaz == "serve":
        return serve(cfg, args.port)
    if args.prikaz == "deploy":
        return deploy(cfg)
    if args.prikaz == "zaloha":
        backup(cfg)
        return 0

    stav_k, subor = args.stav_k, args.subor
    offline = args.fixtures or not args.nominatim
    if args.fixtures and args.prikaz in ("download", "all"):
        subor = subor or fixtures.prepare()
        stav_k = stav_k or fixtures.STAV_K

    con = db.connect(cfg)
    try:
        if args.prikaz == "skontroluj":
            return NEW_REGISTER_EXIT if check_for_update(cfg, con) else 0
        if args.prikaz in ("download", "all"):
            stav_k = download(cfg, con, stav_k, url=args.url, subor=subor, force=args.force)
        if args.prikaz in ("areas", "all"):
            build_areas(cfg, con)
        if args.prikaz == "download":
            return 0
        snapshot = db.get_snapshot(con, stav_k)
        if args.prikaz in ("validate", "all"):
            validate(cfg, con, snapshot)
        if args.prikaz in ("clean", "all"):
            clean(cfg, con, snapshot)
        if args.prikaz in ("nczi", "all"):
            nczi(cfg, con, snapshot, force=args.force and args.prikaz == "nczi")
        if args.prikaz in ("geocode", "all"):
            geocode(cfg, con, snapshot, offline=offline, max_new=args.max_dotazov)
        if args.prikaz in ("compute", "all"):
            compute(cfg, con, snapshot, confirmed=args.potvrdit_zmeny)
        if args.prikaz in ("export", "all"):
            export(cfg, con, snapshot)
        if args.prikaz in ("report", "all", "export"):
            write_report(cfg, con, snapshot)
    finally:
        con.close()
    return 0


def main(argv=None):
    sys.stdout.reconfigure(errors="replace")
    parser = argparse.ArgumentParser(prog="python -m pipeline", description="Dátová pipeline: dostupnosť lekárov prvého kontaktu.")
    parser.add_argument("prikaz", choices=COMMANDS)
    parser.add_argument("--stav-k", help="dátum stavu registra RRRR-MM-DD (inak z názvu súboru)")
    parser.add_argument("--url", help="URL súboru registra (inak sa nájde na stránke ÚDZS)")
    parser.add_argument("--subor", help="lokálny súbor registra namiesto stiahnutia")
    parser.add_argument("--fixtures", action="store_true", help="beh na umelých dátach v build/fixtures")
    parser.add_argument("--nominatim", action="store_true", help="geokódovať nové adresy cez Nominatim (inak iba z cache)")
    parser.add_argument("--max-dotazov", type=int, help="najviac N nových dotazov na Nominatim v tomto behu")
    parser.add_argument("--force", action="store_true", help="nahradiť snapshot s rovnakým dátumom; pri nczi znovu stiahnuť súbor")
    parser.add_argument("--potvrdit-zmeny", action="store_true", help="pokračovať aj pri veľkej zmene počtov")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args(argv)
    try:
        return run(args) or 0
    except PipelineError as error:
        print(f"\nCHYBA: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
