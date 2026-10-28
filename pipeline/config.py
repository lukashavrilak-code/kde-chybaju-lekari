import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCAL_CONFIG = ROOT / "config.local.toml"


def merge(base, extra):
    for key, value in extra.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            merge(base[key], value)
        else:
            base[key] = value
    return base


def load_config(path=None, local_path=None):
    with open(path or ROOT / "config.toml", "rb") as f:
        cfg = tomllib.load(f)
    local_path = local_path or (LOCAL_CONFIG if path is None else None)
    if local_path and Path(local_path).exists():
        with open(local_path, "rb") as f:
            merge(cfg, tomllib.load(f))
    return cfg


def project_path(cfg, key):
    return ROOT / cfg["cesty"][key]


def published_types(cfg):
    return [typ for typ in ("VLD", "VLDD") if cfg["zverejnit"].get(typ)]
