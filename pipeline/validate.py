import re
import unicodedata
from datetime import date, datetime, timedelta

import openpyxl
import pandas as pd

from .checks import Checks, PipelineError
from .config import ROOT
from .db import previous_snapshot

CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f-\x9f]")
CODE_PATTERN = r"[0-9A-Z]{12}"
DATE_FORMATS = ["%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%d.%m.%Y", "%d.%m.%Y %H:%M:%S", "%d. %m. %Y"]


def cell_text(value):
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def clean_text(text):
    text = unicodedata.normalize("NFC", text)
    text = CONTROL_CHARS.sub(" ", text)
    return " ".join(text.split())


def parse_date(text):
    text = text.strip()
    if not text:
        return ""
    if re.fullmatch(r"\d{5}", text):
        return (date(1899, 12, 30) + timedelta(days=int(text))).isoformat()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            pass
    return None


def read_register(path, cfg):
    key_column = cfg["register"]["stlpce"]["pzs_kod"]
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True, keep_links=False)
    try:
        rows = [[cell_text(v) for v in row] for row in wb.worksheets[0].iter_rows(values_only=True)]
    finally:
        wb.close()
    header_index = 0
    for i, row in enumerate(rows[:20]):
        if key_column in [clean_text(v) for v in row]:
            header_index = i
            break
    header = [clean_text(v) for v in rows[header_index]]
    data = [row for row in rows[header_index + 1:] if any(v.strip() for v in row)]
    width = len(header)
    data = [(row + [""] * width)[:width] for row in data]
    return header, data


def load_register(path, cfg):
    header, data = read_register(path, cfg)
    columns = cfg["register"]["stlpce"]
    missing = [name for name in columns.values() if name not in header]
    if missing:
        return header, None
    frame = pd.DataFrame(data, columns=header)
    frame = frame[list(columns.values())].copy()
    frame.columns = list(columns.keys())
    return header, frame.fillna("").astype(str)


def clean_frame(frame):
    frame = frame.copy()
    for col in frame.columns:
        frame[col] = frame[col].map(clean_text)
    frame["pzs_kod"] = frame["pzs_kod"].str.upper()
    return frame


def validate(cfg, con, snapshot):
    sid = snapshot["snapshot_id"]
    checks = Checks(con, "2-validate", sid)
    rules = cfg["validacia"]
    header, raw = load_register(ROOT / snapshot["subor"], cfg)

    expected = list(cfg["register"]["stlpce"].values())
    missing = [c for c in expected if c not in header]
    extra = [c for c in header if c and c not in expected]
    checks.check("V2.1", not missing and not extra, "stĺpce zodpovedajú očakávaniu", detail=f"chýba: {missing}; navyše: {extra}")
    checks.done()
    if raw is None:
        raise PipelineError("Register nemá očakávané stĺpce.")

    count = len(raw)
    con.execute("UPDATE snapshot SET pocet_riadkov = ? WHERE snapshot_id = ?", (count, sid))
    previous = previous_snapshot(con, snapshot["stav_k"])
    if previous and previous["pocet_riadkov"]:
        change = abs(count - previous["pocet_riadkov"]) / previous["pocet_riadkov"]
        checks.check("V2.2", change <= rules["zmena_riadkov"], "zmena počtu riadkov oproti minulému snapshotu",
                     f"{count} (predtým {previous['pocet_riadkov']})", "WARN")
    else:
        checks.info("V2.2", "počet riadkov (prvý snapshot)", count)

    long_or_control = sum(
        1 for col in raw.columns for v in raw[col]
        if len(v) > cfg["register"]["max_dlzka_textu"] or CONTROL_CHARS.search(v)
    )
    checks.check("V2.7", long_or_control == 0, "texty bez riadiacich znakov a primeranej dĺžky", f"{long_or_control} buniek", "WARN")

    frame = clean_frame(raw)
    bad_code = ~frame["pzs_kod"].str.fullmatch(CODE_PATTERN)
    checks.check("V2.3", bad_code.mean() <= rules["max_zlych_kodov"], "formát pzs_kod (12 znakov)",
                 f"{int(bad_code.sum())} zlých z {count}", detail=", ".join(frame.loc[bad_code, "pzs_kod"].head(10)))

    specialty = frame.loc[~bad_code, "pzs_kod"].str[6:9]
    counts = specialty.value_counts()
    con.execute("DELETE FROM odbornost_pocet WHERE snapshot_id = ?", (sid,))
    con.executemany(
        "INSERT INTO odbornost_pocet (snapshot_id, odbornost_kod, pocet) VALUES (?, ?, ?)",
        [(sid, code, int(n)) for code, n in counts.items()],
    )
    for typ, code in cfg["odbornosti"].items():
        found = int(counts.get(code, 0))
        expected_count = rules["ocakavane_pocty"][typ]
        checks.check("V2.4", abs(found - expected_count) <= expected_count * rules["rozsah_odbornosti"],
                     f"počet záznamov s kódom {code} ({typ}) v očakávanom rozsahu", f"{found} (očakávané ~{expected_count})")

    od = frame["platnost_od"].map(parse_date)
    do = frame["platnost_do"].map(parse_date)
    unparsed = int(od.isna().sum() + do.isna().sum())
    checks.check("V2.5", unparsed <= count * rules["max_zlych_datumov"], "dátumy platnosti sa dajú prečítať",
                 f"{unparsed} neprečítaných", "WARN")
    reversed_dates = int(((od.fillna("") != "") & (do.fillna("") != "") & (od.fillna("") > do.fillna(""))).sum())
    checks.check("V2.5", reversed_dates == 0, "Platnost_od nie je po Platnost_do", f"{reversed_dates} záznamov", "WARN")

    stav_k = snapshot["stav_k"]
    valid = [(not o or o <= stav_k) and (not d or d >= stav_k) for o, d in zip(od.fillna(""), do.fillna(""))]
    duplicates = frame.loc[valid, "pzs_kod"].duplicated().sum()
    checks.check("V2.6", duplicates == 0, "pzs_kod je medzi platnými záznamami jedinečný", f"{int(duplicates)} duplicít", "WARN")
    checks.done()
