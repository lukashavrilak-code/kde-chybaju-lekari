import re
import sqlite3
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FORBIDDEN_PATHS = ("data/raw/", "data/local/", "data/snapshots/", "data/cache/", "site/", "build/")
FORBIDDEN_FILES = ("config.local.toml",)
FORBIDDEN_JS = re.compile(r"innerHTML|outerHTML|insertAdjacentHTML|document\.write|\beval\(|new Function")
MAX_BYTES = 1024 * 1024
MIN_NAME_LENGTH = 8


def git_files(staged):
    args = ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"] if staged else ["git", "ls-files"]
    output = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, check=True).stdout
    return [line for line in output.splitlines() if line]


def local_email():
    path = ROOT / "config.local.toml"
    if not path.exists():
        return ""
    with open(path, "rb") as f:
        return tomllib.load(f).get("projekt", {}).get("kontakt_email", "").strip()


def provider_names():
    path = ROOT / "data" / "local" / "lekari.sqlite"
    if not path.exists():
        return []
    con = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    try:
        return [row[0].encode("utf-8") for row in con.execute("SELECT DISTINCT nazov FROM ambulancia") if len(row[0]) >= MIN_NAME_LENGTH]
    except sqlite3.OperationalError:
        return []
    finally:
        con.close()


def problems(files):
    found = []
    email = local_email()
    names = provider_names()
    for name in files:
        path = ROOT / name
        content = path.read_bytes() if path.is_file() else b""
        if any(provider in content for provider in names):
            found.append(f"{name}: obsahuje názov poskytovateľa z lokálnej databázy")
        if name.startswith(FORBIDDEN_PATHS) or name in FORBIDDEN_FILES:
            found.append(f"{name}: súbor s dátami, lokálnym nastavením alebo buildom nepatrí do Gitu")
        if path.exists() and path.stat().st_size > MAX_BYTES:
            found.append(f"{name}: súbor je väčší ako 1 MB")
        if email and email.encode("utf-8") in content:
            found.append(f"{name}: obsahuje projektový e-mail z config.local.toml")
    for path in (ROOT / "web" / "static" / "js").glob("*.js"):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if FORBIDDEN_JS.search(line):
                found.append(f"{path.relative_to(ROOT).as_posix()}:{number}: zakázaný vzor (riziko XSS)")
    return found


def main():
    found = problems(git_files("--staged" in sys.argv))
    for problem in found:
        print(problem)
    if found:
        sys.exit(1)
    print("Kontrola repozitára: OK")


if __name__ == "__main__":
    main()
