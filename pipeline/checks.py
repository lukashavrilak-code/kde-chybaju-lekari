from datetime import UTC, datetime


class PipelineError(Exception):
    pass


def utc_now():
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


class Checks:
    def __init__(self, con, krok, snapshot_id=None):
        self.con = con
        self.krok = krok
        self.snapshot_id = snapshot_id
        self.failed = []
        con.execute("DELETE FROM validacia WHERE krok = ? AND snapshot_id IS ?", (krok, snapshot_id))
        print(f"== {krok}")

    def check(self, kod, ok, popis, hodnota=None, uroven="FAIL", detail=None):
        vysledok = "OK" if ok else uroven
        self._save(kod, vysledok, popis, hodnota, detail)
        if vysledok == "FAIL":
            self.failed.append(f"{kod} {popis}")
        return ok

    def info(self, kod, popis, hodnota=None, detail=None):
        self._save(kod, "INFO", popis, hodnota, detail)

    def _save(self, kod, vysledok, popis, hodnota, detail):
        hodnota = None if hodnota is None else str(hodnota)
        self.con.execute(
            "INSERT INTO validacia (snapshot_id, krok, kod, vysledok, popis, hodnota, detail, cas_utc) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (self.snapshot_id, self.krok, kod, vysledok, popis, hodnota, detail, utc_now()),
        )
        line = f"  [{vysledok:<4}] {kod} {popis}"
        if hodnota is not None:
            line += f": {hodnota}"
        print(line)
        if detail and vysledok in ("WARN", "FAIL"):
            print(f"         {detail[:300]}")

    def done(self):
        self.con.commit()
        if self.failed:
            raise PipelineError(f"Krok {self.krok} zastavený: " + "; ".join(self.failed))
