import json
import tarfile

import pytest

from pipeline import db, deploy, fixtures
from pipeline.__main__ import main
from pipeline.checks import PipelineError
from pipeline.config import load_config, project_path
from pipeline.export import export

VERSION = "0.1.0+abc1234"


def config():
    return {
        "projekt": {"prevadzkovatel": "Testovací prevádzkovateľ", "kontakt_email": "test@example.org", "web_url": "https://example.org/"},
        "web": {"poistovne": [{"nazov": "Test", "url": "https://example.org/"}]},
        "zverejnit": {"nazvy": False},
    }


@pytest.fixture
def site(tmp_path, monkeypatch):
    monkeypatch.setattr(deploy, "pipeline_version", lambda: VERSION)
    monkeypatch.setattr(deploy, "pushed_to_origin", lambda: True)
    (tmp_path / "data").mkdir()
    write_meta(tmp_path)
    (tmp_path / "data" / "ambulancie.json").write_text('{"ambulancie": [{"adresa": "Hlavná 1"}]}', encoding="utf-8")
    (tmp_path / "index.html").write_text("<p>web</p>", encoding="utf-8")
    return tmp_path


def write_meta(site, **changes):
    meta = {"fixtures": False, "validacia": {"FAIL": 0}, "verzia_pipeline": VERSION, **changes}
    (site / "data" / "meta.json").write_text(json.dumps(meta), encoding="utf-8")


def test_complete_site_has_no_problems(site):
    assert deploy.deploy_problems(config(), site) == []


def test_missing_meta_stops_deploy(site):
    (site / "data" / "meta.json").unlink()
    assert "chýba site/data/meta.json" in deploy.deploy_problems(config(), site)[0]


@pytest.mark.parametrize(("changes", "expected"), [
    ({"fixtures": True}, "umelé"),
    ({"validacia": {"FAIL": 1}}, "FAIL"),
    ({"verzia_pipeline": "0.1.0+stara"}, "inou verziou"),
])
def test_bad_meta_stops_deploy(site, changes, expected):
    write_meta(site, **changes)
    assert expected in " ".join(deploy.deploy_problems(config(), site))


@pytest.mark.parametrize("version", ["0.1.0+abc1234-dirty", "0.1.0+bez-commitu"])
def test_uncommitted_changes_stop_deploy(site, monkeypatch, version):
    monkeypatch.setattr(deploy, "pipeline_version", lambda: version)
    write_meta(site, verzia_pipeline=version)
    assert "neuložené zmeny" in " ".join(deploy.deploy_problems(config(), site))


def test_unpushed_commit_stops_deploy(site, monkeypatch):
    monkeypatch.setattr(deploy, "pushed_to_origin", lambda: False)
    assert "origin/main" in " ".join(deploy.deploy_problems(config(), site))


@pytest.mark.parametrize(("section", "key", "value", "expected"), [
    ("projekt", "prevadzkovatel", " ", "prevádzkovateľ"),
    ("projekt", "kontakt_email", "", "e-mail"),
    ("projekt", "web_url", "", "web_url"),
    ("web", "poistovne", [{"url": ""}], "poisťovní"),
])
def test_incomplete_config_stops_deploy(site, section, key, value, expected):
    cfg = config()
    cfg[section][key] = value
    assert expected in " ".join(deploy.deploy_problems(cfg, site))


def test_placeholder_text_stops_deploy(site):
    (site / "sukromie.html").write_text("[DOPLŇ MENO]", encoding="utf-8")
    assert "sukromie.html" in " ".join(deploy.deploy_problems(config(), site))


def test_names_stop_deploy_unless_enabled(site):
    (site / "data" / "ambulancie.json").write_text('{"ambulancie": [{"nazov": "Ambulancia Prvá"}]}', encoding="utf-8")
    assert "názvy" in " ".join(deploy.deploy_problems(config(), site))
    cfg = config()
    cfg["zverejnit"]["nazvy"] = True
    assert deploy.deploy_problems(cfg, site) == []


def test_archive_contains_site_with_plain_permissions(site, tmp_path):
    target = tmp_path / "balik" / "site.tar.gz"
    deploy.build_archive(site, target)
    with tarfile.open(target) as archive:
        members = {m.name: m for m in archive.getmembers()}
    assert "./index.html" in members and "./data/meta.json" in members
    assert members["./index.html"].mode == 0o644 and members["./data"].mode == 0o755


def test_failed_size_check_blocks_deploy():
    assert main(["all", "--fixtures"]) == 0
    cfg = load_config()
    fixtures.apply(cfg)
    cfg["limity_kb"]["data/meta.json"] = 0
    con = db.connect(cfg)
    try:
        with pytest.raises(PipelineError, match="V6.2"):
            export(cfg, con, db.get_snapshot(con))
    finally:
        con.close()
    site = project_path(cfg, "site")
    assert json.loads((site / "data" / "meta.json").read_text(encoding="utf-8"))["validacia"]["FAIL"] >= 1
    assert "FAIL" in " ".join(deploy.deploy_problems(cfg, site))
    assert main(["export", "--fixtures"]) == 0
