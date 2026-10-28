import sqlite3

from .checks import PipelineError
from .config import ROOT, project_path

SCHEMA_VERSION = 3
SCHEMA = """
CREATE TABLE IF NOT EXISTS snapshot (
    snapshot_id     INTEGER PRIMARY KEY,
    stav_k          TEXT NOT NULL UNIQUE,
    stiahnute_utc   TEXT NOT NULL,
    url             TEXT NOT NULL,
    subor           TEXT NOT NULL,
    sha256          TEXT NOT NULL UNIQUE,
    velkost_b       INTEGER NOT NULL,
    pocet_riadkov   INTEGER,
    pipeline_verzia TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS odbornost_pocet (
    snapshot_id   INTEGER NOT NULL REFERENCES snapshot(snapshot_id) ON DELETE CASCADE,
    odbornost_kod TEXT NOT NULL,
    pocet         INTEGER NOT NULL,
    PRIMARY KEY (snapshot_id, odbornost_kod)
);

CREATE TABLE IF NOT EXISTS ambulancia (
    snapshot_id   INTEGER NOT NULL REFERENCES snapshot(snapshot_id) ON DELETE CASCADE,
    pzs_kod       TEXT NOT NULL,
    ico           TEXT,
    nazov         TEXT NOT NULL,
    typ           TEXT NOT NULL CHECK (typ IN ('VLD', 'VLDD')),
    odbornost_kod TEXT NOT NULL,
    ulica         TEXT,
    obec_text     TEXT,
    psc           TEXT,
    adresa_kluc   TEXT NOT NULL,
    platnost_od   TEXT,
    platnost_do   TEXT,
    PRIMARY KEY (snapshot_id, pzs_kod)
);

CREATE TABLE IF NOT EXISTS geokod (
    adresa_kluc TEXT PRIMARY KEY,
    dotaz       TEXT,
    lat         REAL NOT NULL,
    lon         REAL NOT NULL,
    presnost    TEXT NOT NULL CHECK (presnost IN ('adresa', 'ulica', 'obec', 'rucne')),
    zdroj       TEXT NOT NULL,
    obec_kod    TEXT NOT NULL,
    problem     TEXT
);

CREATE TABLE IF NOT EXISTS adresa_obec (
    adresa_kluc TEXT NOT NULL,
    obec_kod    TEXT NOT NULL,
    zdroj       TEXT NOT NULL CHECK (zdroj IN ('rucne', 'nazov', 'mesto')),
    PRIMARY KEY (adresa_kluc, obec_kod)
);

CREATE TABLE IF NOT EXISTS obec (
    obec_kod     TEXT PRIMARY KEY,
    nazov        TEXT NOT NULL,
    okres_kod    TEXT NOT NULL,
    kraj_kod     TEXT NOT NULL,
    ref_lat      REAL NOT NULL,
    ref_lon      REAL NOT NULL,
    obyv_spolu   REAL NOT NULL,
    obyv_deti    REAL NOT NULL,
    obyv_dospeli REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS okres (
    okres_kod    TEXT PRIMARY KEY,
    nazov        TEXT NOT NULL,
    kraj_kod     TEXT NOT NULL,
    kraj_nazov   TEXT NOT NULL,
    obyv_spolu   REAL NOT NULL,
    obyv_deti    REAL NOT NULL,
    obyv_dospeli REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS nczi_porovnanie (
    snapshot_id INTEGER NOT NULL REFERENCES snapshot(snapshot_id) ON DELETE CASCADE,
    rok         TEXT NOT NULL,
    typ         TEXT NOT NULL,
    kraj_kod    TEXT NOT NULL,
    register    INTEGER NOT NULL,
    nczi        INTEGER NOT NULL,
    PRIMARY KEY (snapshot_id, typ, kraj_kod)
);

CREATE TABLE IF NOT EXISTS ukazovatel_okres (
    snapshot_id INTEGER NOT NULL REFERENCES snapshot(snapshot_id) ON DELETE CASCADE,
    okres_kod   TEXT NOT NULL,
    typ         TEXT NOT NULL,
    pocet       INTEGER NOT NULL,
    pocet_pracovisk INTEGER NOT NULL,
    na_10k      REAL NOT NULL,
    poradie     INTEGER NOT NULL,
    PRIMARY KEY (snapshot_id, okres_kod, typ)
);

CREATE TABLE IF NOT EXISTS ukazovatel_obec (
    snapshot_id   INTEGER NOT NULL REFERENCES snapshot(snapshot_id) ON DELETE CASCADE,
    obec_kod      TEXT NOT NULL,
    typ           TEXT NOT NULL,
    najblizsia_km REAL,
    pocet_v_obci  INTEGER NOT NULL,
    pocet_10km    INTEGER NOT NULL,
    pocet_20km    INTEGER NOT NULL,
    PRIMARY KEY (snapshot_id, obec_kod, typ)
);

CREATE TABLE IF NOT EXISTS zdroj (
    zdroj_id      TEXT PRIMARY KEY,
    subor         TEXT NOT NULL,
    sha256        TEXT NOT NULL,
    stav_k        TEXT,
    nacitane_utc  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS validacia (
    snapshot_id INTEGER,
    krok        TEXT NOT NULL,
    kod         TEXT NOT NULL,
    vysledok    TEXT NOT NULL CHECK (vysledok IN ('OK', 'INFO', 'WARN', 'FAIL')),
    popis       TEXT NOT NULL,
    hodnota     TEXT,
    detail      TEXT,
    cas_utc     TEXT NOT NULL
);

CREATE VIEW IF NOT EXISTS v_ambulancia AS
SELECT a.*, g.lat, g.lon, g.presnost, g.zdroj AS zdroj_polohy, g.obec_kod,
       o.nazov AS obec_nazov, o.okres_kod, o.kraj_kod
FROM ambulancia a
LEFT JOIN geokod g ON g.adresa_kluc = a.adresa_kluc
LEFT JOIN obec o ON o.obec_kod = g.obec_kod;
"""


def migrate(cfg, con):
    version = con.execute("PRAGMA user_version").fetchone()[0]
    has_tables = con.execute("SELECT COUNT(*) FROM sqlite_master WHERE name = 'snapshot'").fetchone()[0]
    if version < 2 and has_tables:
        snapshots = (project_path(cfg, "snapshots") / "udzs").relative_to(ROOT).as_posix()
        con.execute("UPDATE snapshot SET subor = ? || '/' || stav_k || '.xlsx' WHERE subor NOT LIKE ? || '/%'",
                    (snapshots, snapshots))
        con.execute("DELETE FROM zdroj WHERE zdroj_id = 'datacube'")
        con.executescript("DROP VIEW IF EXISTS v_ambulancia; DROP TABLE IF EXISTS obec; DROP TABLE IF EXISTS okres;")
        print("Databáza prevedená na verziu 2 (obec a okres treba znovu naplniť príkazom areas).")
    if version < 3 and has_tables:
        con.execute("DROP TABLE IF EXISTS ukazovatel_okres")
        print("Databáza prevedená na verziu 3 (ukazovatele okresov treba znovu vypočítať príkazom compute).")
    con.executescript(SCHEMA)
    con.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    con.commit()


def connect(cfg):
    path = project_path(cfg, "local") / "lekari.sqlite"
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    migrate(cfg, con)
    return con


def get_snapshot(con, stav_k=None):
    if stav_k:
        row = con.execute("SELECT * FROM snapshot WHERE stav_k = ?", (stav_k,)).fetchone()
    else:
        row = con.execute("SELECT * FROM snapshot ORDER BY stav_k DESC LIMIT 1").fetchone()
    if row is None:
        raise PipelineError("Nenašiel sa snapshot registra. Najprv spusti: python -m pipeline download")
    return row


def previous_snapshot(con, stav_k):
    return con.execute(
        "SELECT * FROM snapshot WHERE stav_k < ? ORDER BY stav_k DESC LIMIT 1", (stav_k,)
    ).fetchone()
