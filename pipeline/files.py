import csv
import hashlib
import json
from pathlib import Path


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv_rows(path):
    path = Path(path)
    if not path.exists():
        return []
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv_rows(path, rows, columns, bom=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8-sig" if bom else "utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col, "") for col in columns})


def replace_csv_rows(path, new_rows, columns, match_col, match_value, sort_cols):
    rows = [r for r in read_csv_rows(path) if r.get(match_col) != match_value]
    rows += [{col: str(row.get(col, "")) for col in columns} for row in new_rows]
    rows.sort(key=lambda r: tuple(r.get(col, "") for col in sort_cols))
    write_csv_rows(path, rows, columns)


def write_json(path, data, indent=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    separators = None if indent else (",", ":")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, sort_keys=True, indent=indent, separators=separators)
        f.write("\n")
