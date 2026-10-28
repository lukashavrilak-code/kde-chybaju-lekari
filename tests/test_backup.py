import os

import pytest

from pipeline.backup import backup
from pipeline.checks import PipelineError


def test_backup_copies_only_new_files_and_never_deletes(tmp_path):
    root, target = tmp_path / "projekt", tmp_path / "zaloha"
    (root / "data" / "cache").mkdir(parents=True)
    (root / "data" / "cache" / "geocode_cache.csv").write_text("dotaz,lat\n", encoding="utf-8")
    (root / "config.local.toml").write_text("[projekt]\n", encoding="utf-8")
    cfg = {"zaloha": {"ciel": str(target), "polozky": ["data/cache", "data/snapshots", "config.local.toml"]}}

    assert backup(cfg, root) == 2
    assert (target / "data" / "cache" / "geocode_cache.csv").read_text(encoding="utf-8") == "dotaz,lat\n"
    assert backup(cfg, root) == 0

    (target / "stary_subor.txt").write_text("x", encoding="utf-8")
    cache = root / "data" / "cache" / "geocode_cache.csv"
    cache.write_text("dotaz,lat\nnovy,1\n", encoding="utf-8")
    os.utime(cache, (cache.stat().st_atime, cache.stat().st_mtime + 10))
    assert backup(cfg, root) == 1
    assert (target / "stary_subor.txt").exists()


def test_backup_requires_absolute_target(tmp_path):
    with pytest.raises(PipelineError):
        backup({"zaloha": {"ciel": "", "polozky": []}}, tmp_path)
