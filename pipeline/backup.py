import shutil
from pathlib import Path

from .checks import PipelineError
from .config import ROOT


def is_current(source, target):
    if not target.exists():
        return False
    a, b = source.stat(), target.stat()
    return a.st_size == b.st_size and int(a.st_mtime) <= int(b.st_mtime)


def copy_new(source, target):
    files = [source] if source.is_file() else sorted(p for p in source.rglob("*") if p.is_file())
    copied = 0
    for path in files:
        dest = target if source.is_file() else target / path.relative_to(source)
        if is_current(path, dest):
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)
        copied += 1
    return copied, len(files)


def backup(cfg, root=ROOT):
    settings = cfg.get("zaloha", {})
    target = Path(settings.get("ciel", "").strip())
    if not target.is_absolute():
        raise PipelineError("Nie je nastavený cieľ zálohy (úplná cesta). Doplň do config.local.toml: [zaloha] ciel = '...'")
    if not Path(target.anchor).exists():
        raise PipelineError(f"Cieľ zálohy nie je dostupný (je pripojený disk?): {target}")
    copied = total = 0
    for item in settings["polozky"]:
        source = root / item
        if not source.exists():
            print(f"  preskočené (neexistuje): {item}")
            continue
        new, count = copy_new(source, target / item)
        copied, total = copied + new, total + count
        print(f"  {item}: {new} nových alebo zmenených z {count}")
    print(f"Záloha do {target}: skopírovaných {copied} z {total} súborov. V cieli sa nič nemaže.")
    return copied
