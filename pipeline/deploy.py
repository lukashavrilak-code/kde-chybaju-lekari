import json
import shutil
import subprocess
import tarfile

from .checks import PipelineError
from .config import ROOT, project_path
from .export import pipeline_version

RELEASE = "web-balik"
WORKFLOW = "nasadenie.yml"
ARCHIVE_NAME = "site.tar.gz"


def pushed_to_origin():
    def rev(ref):
        return subprocess.run(["git", "rev-parse", ref], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    try:
        return rev("HEAD") == rev("origin/main")
    except (OSError, subprocess.CalledProcessError):
        return False


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
    if not pushed_to_origin():
        problems.append("aktuálny commit nie je odoslaný do origin/main (verzia na webe by neodkazovala na verejný kód)")
    projekt = cfg["projekt"]
    if not projekt["prevadzkovatel"].strip() or not projekt["kontakt_email"].strip():
        problems.append("chýba prevádzkovateľ (config.toml) alebo kontaktný e-mail (config.local.toml)")
    if not projekt["web_url"].strip():
        problems.append("chýba [projekt] web_url v config.toml (stránka 404 ho potrebuje pre odkazy na vnorených adresách)")
    if not all(p["url"] for p in cfg["web"]["poistovne"]):
        problems.append("v config.toml chýbajú odkazy na vyhľadávanie lekárov poisťovní")
    for page in site.glob("*.html"):
        if "[DOPLŇ" in page.read_text(encoding="utf-8"):
            problems.append(f"{page.name} obsahuje nevyplnený text [DOPLŇ …]")
    ambulancie = site / "data" / "ambulancie.json"
    if not cfg["zverejnit"].get("nazvy") and ambulancie.exists():
        items = json.loads(ambulancie.read_text(encoding="utf-8"))["ambulancie"]
        if any("nazov" in item for item in items):
            problems.append("ambulancie.json obsahuje názvy poskytovateľov, hoci sú vypnuté ([zverejnit] nazvy)")
    return problems


def normalized_member(member):
    member.mode = 0o755 if member.isdir() else 0o644
    member.uid = member.gid = 0
    member.uname = member.gname = ""
    return member


def build_archive(site, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(target, "w:gz") as archive:
        archive.add(site, arcname=".", filter=normalized_member)
    return target


def deploy(cfg):
    site = project_path(cfg, "site")
    problems = deploy_problems(cfg, site)
    if problems:
        raise PipelineError("Nasadenie zastavené:\n  - " + "\n  - ".join(problems))
    gh = shutil.which("gh")
    if not gh:
        raise PipelineError("Chýba GitHub CLI. Nainštaluj ho (winget install GitHub.cli) a prihlás sa (gh auth login).")
    meta = json.loads((site / "data" / "meta.json").read_text(encoding="utf-8"))
    archive = build_archive(site, ROOT / "build" / ARCHIVE_NAME)
    release = subprocess.run([gh, "release", "view", RELEASE, "--json", "isDraft"], cwd=ROOT, capture_output=True, text=True, check=False)
    if release.returncode != 0:
        notes = "Neverejný balík pre workflow Nasadenie webu. Nepublikovať."
        subprocess.run([gh, "release", "create", RELEASE, "--draft", "--title", RELEASE, "--notes", notes], cwd=ROOT, check=True)
    elif not json.loads(release.stdout)["isDraft"]:
        raise PipelineError(f"Vydanie {RELEASE} nie je draft, balík by bol verejný. Nasadenie zastavené.")
    subprocess.run([gh, "release", "upload", RELEASE, str(archive), "--clobber"], cwd=ROOT, check=True)
    subprocess.run([gh, "workflow", "run", WORKFLOW], cwd=ROOT, check=True)
    print(f"Nasadenie spustené: register k {meta['stav_registra']}, pipeline {meta['verzia_pipeline']}. Priebeh: gh run watch")
