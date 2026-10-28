import json
import shutil
import subprocess
import sys
from pathlib import Path

from .checks import PipelineError
from .config import ROOT, project_path
from .export import pipeline_version


def deploy_problems(cfg, site):
    problems = []
    meta_path = site / "data" / "meta.json"
    if not meta_path.exists():
        return ["chýba site/data/meta.json, najprv spusti export"]
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    if meta.get("fixtures"):
        problems.append("site/ obsahuje umelé (fixture) dáta")
    if meta.get("validacia", {}).get("FAIL", 0):
        problems.append("posledný beh pipeline obsahuje FAIL")
    current = pipeline_version()
    if current.endswith("-dirty") or "bez-commitu" in current:
        problems.append("v Gite sú neuložené zmeny alebo chýba commit")
    if meta.get("verzia_pipeline") != current:
        problems.append(f"web bol vygenerovaný inou verziou ({meta.get('verzia_pipeline')}), aktuálna je {current}")
    projekt = cfg["projekt"]
    if not projekt["prevadzkovatel"].strip() or not projekt["kontakt_email"].strip():
        problems.append("chýba prevádzkovateľ (config.toml) alebo kontaktný e-mail (config.local.toml)")
    if not all(p["url"] for p in cfg["web"]["poistovne"]):
        problems.append("v config.toml chýbajú odkazy na vyhľadávanie lekárov poisťovní")
    for page in site.glob("*.html"):
        if "[DOPLŇ" in page.read_text(encoding="utf-8"):
            problems.append(f"{page.name} obsahuje nevyplnený text [DOPLŇ …]")
    return problems


def deploy(cfg):
    site = project_path(cfg, "site")
    problems = deploy_problems(cfg, site)
    if problems:
        raise PipelineError("Nasadenie zastavené:\n  - " + "\n  - ".join(problems))
    executable = shutil.which("ghp-import") or str(Path(sys.executable).parent / "ghp-import")
    meta = json.loads((site / "data" / "meta.json").read_text(encoding="utf-8"))
    message = f"Web: register k {meta['stav_registra']}, pipeline {meta['verzia_pipeline']}"
    subprocess.run(
        [executable, "--no-history", "--no-jekyll", "--push", "--force", "-m", message, str(site)],
        cwd=ROOT, check=True,
    )
    print("Nasadené do vetvy gh-pages.")
