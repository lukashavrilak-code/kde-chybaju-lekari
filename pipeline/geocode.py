import re
import time
from collections import Counter
from datetime import UTC, datetime

import geopandas as gpd
import requests
import shapely
from pyproj import Transformer

from . import __version__
from .areas import areas_dir, norm_name
from .checks import Checks, PipelineError
from .config import project_path
from .files import read_csv_rows, write_csv_rows

CACHE_COLUMNS = ["dotaz", "lat", "lon", "place_rank", "osm_typ", "osm_id", "addresstype", "datum"]
REVIEW_COLUMNS = ["adresa_kluc", "ulica", "obec_text", "psc", "ambulancii", "zdroj", "presnost", "lat", "lon",
                  "obec_kod", "obec_nazov", "problem"]
MISMATCH_COLUMNS = ["adresa_kluc", "ulica", "obec_text", "psc", "ambulancii", "obec_v_registri", "obec_podla_bodu",
                    "vzdialenost_km", "riesenie", "zdroj", "presnost", "lat", "lon"]
PRECISION_RANK = {"obec": 0, "ulica": 1, "adresa": 2, "rucne": 3}
MANUAL_CHECK = "bod je mimo obce z registra – na ručnú kontrolu"
CENTER_AFTER_MISMATCH = "bod z Nominatimu bol mimo obce z registra, použitý stred obce"
RESOLUTION = {
    "tolerancia": "tolerancia pri hranici obce",
    "kandidat": "iný kandidát v obci",
    "stred": "stred obce",
    "rucne": "na ručnú kontrolu",
}
NUMBER = r"\d+[^\W\d_]?(?:/\d+[^\W\d_]?)?"


def query_key(params):
    return "&".join(f"{key}={params[key]}" for key in sorted(params))


def structured_query(ulica, obec, psc):
    params = {"street": ulica, "city": obec}
    if psc:
        params["postalcode"] = psc
    return params


def city_query(obec, psc):
    params = {"city": obec}
    if psc:
        params["postalcode"] = psc
    return params


def precision(place_rank):
    rank = int(float(place_rank or 0))
    if rank >= 30:
        return "adresa"
    if rank >= 26:
        return "ulica"
    return "obec"


def clean_street(text, prefixes):
    text = " ".join(text.split())
    changed = True
    while changed:
        changed = False
        for prefix in prefixes:
            rest = text[len(prefix):]
            if text.lower().startswith(prefix.lower()) and (prefix.endswith(".") or rest[:1] in (" ", "")):
                text, changed = rest.strip(), True
    text = re.sub(r"\bč\.\s*(?=\d)", "", text)
    return " ".join(text.split())


def swap_number(text):
    match = re.fullmatch(r"(.*\S)\s+(\d+[^\W\d_]?)/(\d+[^\W\d_]?)", text)
    return f"{match.group(1)} {match.group(3)}/{match.group(2)}" if match else text


def village_query(text, obec, psc):
    match = re.fullmatch(rf"(?:(.*\S)\s+)?({NUMBER})", text)
    if not match or (match.group(1) and norm_name(match.group(1)) != norm_name(obec)):
        return None
    return {"q": ", ".join(part for part in (match.group(2), obec, psc) if part)}


def street_variants(ulica, obec, psc, prefixes):
    cleaned = clean_street(ulica, prefixes)
    variants = [structured_query(cleaned, obec, psc), structured_query(swap_number(cleaned), obec, psc)]
    village = village_query(cleaned, obec, psc)
    if village:
        variants.append(village)
    original = query_key(structured_query(ulica, obec, psc))
    unique = {}
    for params in variants:
        key = query_key(params)
        if key != original:
            unique.setdefault(key, params)
    return list(unique.values())


class Nominatim:
    def __init__(self, cfg):
        email = cfg["projekt"]["kontakt_email"].strip()
        if not email:
            raise PipelineError(
                "Pred geokódovaním cez Nominatim doplň kontaktný e-mail do config.local.toml ([projekt] kontakt_email)."
            )
        settings = cfg["nominatim"]
        self.url = settings["url"]
        self.interval = settings["interval_s"]
        self.timeout = settings["timeout_s"]
        self.retries = settings["pokusy"]
        self.retry_wait_s = settings["cakanie_po_chybe_s"]
        self.session = requests.Session()
        self.session.headers["User-Agent"] = f"kde-chybaju-lekari/{__version__} ({email})"
        self.last = 0.0
        self.count = 0

    def request(self, params):
        wait = self.interval - (time.monotonic() - self.last)
        if wait > 0:
            time.sleep(wait)
        try:
            return self.session.get(
                self.url,
                params={**params, "countrycodes": "sk", "format": "jsonv2", "limit": 1},
                timeout=self.timeout,
            )
        finally:
            self.last = time.monotonic()

    def search(self, params):
        for attempt in range(1, self.retries + 1):
            try:
                response = self.request(params)
                problem = f"HTTP {response.status_code}" if response.status_code >= 500 else None
            except (requests.ConnectionError, requests.Timeout) as error:
                response, problem = None, type(error).__name__
            if problem is None:
                break
            if attempt == self.retries:
                raise PipelineError(f"V4.1 Nominatim je nedostupný ({problem}), geokódovanie je zastavené. "
                                    "Cache je uložená, spusti príkaz znova neskôr.")
            print(f"  Nominatim: {problem}, ďalší pokus o {self.retry_wait_s * attempt} s")
            time.sleep(self.retry_wait_s * attempt)
        if response.status_code in (403, 429):
            raise PipelineError(f"V4.1 Nominatim vrátil HTTP {response.status_code}, geokódovanie je zastavené. Skús to neskôr.")
        response.raise_for_status()
        self.count += 1
        items = response.json()
        return items[0] if items else None


class Locator:
    def __init__(self, obce):
        self.obce = obce.reset_index(drop=True)
        self.tree = shapely.STRtree(self.obce.geometry.values)
        self.to_local = Transformer.from_crs(4326, obce.crs, always_xy=True)
        self.index_of = {kod: i for i, kod in enumerate(self.obce["obec_kod"])}
        self.bounds_wgs = self.obce.to_crs(4326).bounds

    def point(self, lat, lon):
        x, y = self.to_local.transform(lon, lat)
        return shapely.Point(x, y)

    def find(self, lat, lon):
        hits = self.tree.query(self.point(lat, lon), predicate="intersects")
        return int(min(hits)) if len(hits) else None

    def nearest(self, lat, lon, codes):
        point = self.point(lat, lon)
        return min((self.obce.geometry[self.index_of[kod]].distance(point) / 1000, kod) for kod in codes)[::-1]

    def distance_km(self, lat, lon, codes):
        return self.nearest(lat, lon, codes)[1]

    def names(self, codes):
        return ", ".join(self.obce.at[self.index_of[kod], "obec_nazov"] for kod in codes)

    def viewbox(self, codes):
        box = self.bounds_wgs.iloc[[self.index_of[kod] for kod in codes]]
        return f"{box['minx'].min():.4f},{box['maxy'].max():.4f},{box['maxx'].max():.4f},{box['miny'].min():.4f}"


class Geocoder:
    def __init__(self, cfg, offline, max_new=None):
        self.cfg = cfg
        self.offline = offline
        self.max_new = max_new
        self.limit_reached = False
        self.client = None
        self.cache_path = project_path(cfg, "cache") / "geocode_cache.csv"
        self.cache = {r["dotaz"]: r for r in read_csv_rows(self.cache_path)}
        self.new_queries = 0

    def lookup(self, params):
        key = query_key(params)
        if key in self.cache:
            return self.cache[key]
        if self.offline:
            return None
        if self.max_new is not None and self.new_queries >= self.max_new:
            self.limit_reached = True
            return None
        if self.client is None:
            self.client = Nominatim(self.cfg)
        item = self.client.search(params) or {}
        row = {
            "dotaz": key,
            "lat": item.get("lat", ""),
            "lon": item.get("lon", ""),
            "place_rank": item.get("place_rank", ""),
            "osm_typ": item.get("osm_type", ""),
            "osm_id": item.get("osm_id", ""),
            "addresstype": item.get("addresstype", ""),
            "datum": datetime.now(UTC).date().isoformat(),
        }
        self.cache[key] = row
        self.new_queries += 1
        if self.new_queries % 25 == 0:
            print(f"  ... {self.new_queries} nových dotazov")
            self.save()
        return row

    def save(self):
        rows = [self.cache[k] for k in sorted(self.cache)]
        write_csv_rows(self.cache_path, rows, CACHE_COLUMNS)


def load_overrides(cfg):
    rows = read_csv_rows(project_path(cfg, "manual") / "geocode_overrides.csv")
    return {r["adresa_kluc"]: (float(r["lat"]), float(r["lon"])) for r in rows if r.get("adresa_kluc")}


def load_register_obce(con):
    result = {}
    for r in con.execute("SELECT adresa_kluc, obec_kod FROM adresa_obec ORDER BY adresa_kluc, obec_kod"):
        result.setdefault(r["adresa_kluc"], []).append(r["obec_kod"])
    return result


def found(row, prec=None):
    return "nominatim", row["dotaz"], float(row["lat"]), float(row["lon"]), prec or precision(row["place_rank"])


def candidates(addr, geocoder, overrides, codes, reference, locator, settings):
    key = addr["adresa_kluc"]
    if key in overrides:
        lat, lon = overrides[key]
        yield "manual", None, lat, lon, "rucne"
    if addr["ulica"] and addr["obec_text"]:
        params = structured_query(addr["ulica"], addr["obec_text"], addr["psc"])
        row = geocoder.lookup(params)
        if row and row["lat"]:
            yield found(row)
            if codes:
                row = geocoder.lookup({**params, "viewbox": locator.viewbox(codes), "bounded": "1"})
                if row and row["lat"]:
                    yield found(row)
        elif settings["varianty"]:
            for variant in street_variants(addr["ulica"], addr["obec_text"], addr["psc"], settings["odstranit_predpony"]):
                row = geocoder.lookup(variant)
                if row and row["lat"]:
                    yield found(row)
    if addr["obec_text"]:
        row = geocoder.lookup(city_query(addr["obec_text"], addr["psc"]))
        if row and row["lat"]:
            yield found(row, "obec")
    if len(codes) == 1:
        lat, lon = reference[codes[0]]
        yield "stred_obce", None, lat, lon, "obec"


def choose(addr, geocoder, overrides, codes, reference, locator, settings):
    first, outside = None, 0
    for source, query, lat, lon, prec in candidates(addr, geocoder, overrides, codes, reference, locator, settings):
        index = locator.find(lat, lon)
        if index is None:
            outside += 1
            continue
        point_obec = locator.obce.at[index, "obec_kod"]
        if source == "nominatim" and first is None:
            first = (source, query, lat, lon, prec, point_obec)
        if source == "manual" or not codes or point_obec in codes:
            return (source, query, lat, lon, prec, point_obec), first, None, outside
        nearest_obec, distance = locator.nearest(lat, lon, codes)
        if distance <= settings["tolerancia_obce_km"]:
            return (source, query, lat, lon, prec, nearest_obec), first, "tolerancia", outside
    return first, first, "rucne", outside


def resolution_of(accepted, first, kind):
    if kind:
        return kind
    if accepted[0] == "stred_obce":
        return "stred"
    return None if accepted == first else "kandidat"


def geocode(cfg, con, snapshot, offline=False, max_new=None):
    sid = snapshot["snapshot_id"]
    checks = Checks(con, "4-geocode", sid)
    rules = cfg["validacia"]
    settings = cfg["nominatim"]
    addresses = con.execute(
        "SELECT adresa_kluc, MIN(ulica) AS ulica, MIN(obec_text) AS obec_text, MIN(psc) AS psc, COUNT(*) AS n "
        "FROM ambulancia WHERE snapshot_id = ? GROUP BY adresa_kluc ORDER BY adresa_kluc",
        (sid,),
    ).fetchall()
    obce = gpd.read_file(areas_dir(cfg) / "obce.gpkg")
    locator = Locator(obce)
    reference = {r["obec_kod"]: (r["ref_lat"], r["ref_lon"]) for r in con.execute("SELECT * FROM obec")}
    previous = {r["adresa_kluc"]: r["presnost"] for r in con.execute("SELECT adresa_kluc, presnost FROM geokod")}
    geocoder = Geocoder(cfg, offline, max_new)
    overrides = load_overrides(cfg)
    register_obce = load_register_obce(con)

    results, review, unresolved, mismatches, unknown_obec = [], [], [], [], []
    touched, improved, worse = set(), set(), set()
    outside = 0
    try:
        for addr in addresses:
            key = addr["adresa_kluc"]
            codes = register_obce.get(key, [])
            queries_before = geocoder.new_queries
            accepted, first, kind, skipped = choose(addr, geocoder, overrides, codes, reference, locator, settings)
            outside += skipped
            if geocoder.new_queries > queries_before:
                touched.add(key)
            if accepted is None:
                unresolved.append(key)
                review.append({**dict(addr), "ambulancii": addr["n"], "problem": "poloha sa nenašla"})
                continue
            source, query, lat, lon, prec, obec_kod = accepted
            resolution = resolution_of(accepted, first, kind) if codes and first and first[5] not in codes else kind
            problem = ""
            if resolution == "rucne":
                problem = MANUAL_CHECK
            elif resolution == "stred":
                problem = CENTER_AFTER_MISMATCH
            elif source == "stred_obce":
                problem = "iba stred obce"
            if not codes and addr["obec_text"]:
                unknown_obec.append(f"{addr['obec_text']} ({addr['psc']})")
            if resolution:
                mismatches.append({
                    **dict(addr), "ambulancii": addr["n"], "obec_v_registri": locator.names(codes),
                    "obec_podla_bodu": locator.names([first[5]]),
                    "vzdialenost_km": round(locator.distance_km(first[2], first[3], codes), 2),
                    "riesenie": RESOLUTION[resolution], "zdroj": source, "presnost": prec,
                    "lat": round(lat, 5), "lon": round(lon, 5),
                })
            if key in previous and prec != previous[key]:
                (improved if PRECISION_RANK[prec] > PRECISION_RANK[previous[key]] else worse).add(key)
            obec_nazov = locator.names([obec_kod])
            result = {
                "adresa_kluc": key, "dotaz": query, "lat": round(lat, 5), "lon": round(lon, 5),
                "presnost": prec, "zdroj": source, "obec_kod": obec_kod, "problem": problem or None,
            }
            results.append((result, addr["n"]))
            if problem or prec == "obec":
                review.append({**dict(addr), "ambulancii": addr["n"], "zdroj": source, "presnost": prec,
                               "lat": result["lat"], "lon": result["lon"], "obec_kod": obec_kod,
                               "obec_nazov": obec_nazov, "problem": problem or "presnosť iba na obec"})
    finally:
        geocoder.save()

    checks.info("V4.1", "nové dotazy na Nominatim v tomto behu", geocoder.new_queries)
    if geocoder.limit_reached:
        checks.info("V4.1", "dosiahnutý limit nových dotazov (--max-dotazov), ďalšie adresy iba z cache", max_new)
    checks.info("V4.2", "body mimo územia SR, ktoré sa nepoužili", outside)
    mismatches.sort(key=lambda m: -m["vzdialenost_km"])
    by_resolution = Counter(m["riesenie"] for m in mismatches)
    manual = [m for m in mismatches if m["riesenie"] == RESOLUTION["rucne"]]
    checks.info("V4.3", "prvý bod z Nominatimu bol mimo obce z registra", len(mismatches),
                detail=", ".join(f"{k}: {v}" for k, v in sorted(by_resolution.items())))
    for name, label in RESOLUTION.items():
        if name != "rucne":
            checks.info("V4.3", f"vyriešené: {label}", by_resolution.get(label, 0))
    checks.check("V4.3", not manual, "každý bod leží v obci z adresy v registri (alebo do tolerancie)",
                 f"{len(manual)} adries na ručnú kontrolu", "WARN")
    for m in manual[:50]:
        print(f"         {m['obec_text']} ({m['psc']}): bod v obci {m['obec_podla_bodu']}, "
              f"{m['vzdialenost_km']} km od obce z registra, {m['zdroj']}/{m['presnost']}")
    checks.check("V4.3", not unknown_obec, "adresa z registra má obec v ZBGIS (tabuľka adresa_obec)",
                 f"{len(unknown_obec)} adries bez obce", "WARN", detail=", ".join(sorted(set(unknown_obec))[:40]))
    mismatch_report = project_path(cfg, "local") / "reports" / f"geokod_mimo_obce_{snapshot['stav_k']}.csv"
    write_csv_rows(mismatch_report, mismatches, MISMATCH_COLUMNS)
    checks.check("V4.4", not unresolved, "každá ambulancia má polohu a obec", f"{len(unresolved)} adries bez polohy",
                 detail=", ".join(unresolved[:20]))
    if previous:
        checks.info("V4.5", "presnosť oproti minulému behu: zlepšená / zhoršená", f"{len(improved)} / {len(worse)}")
        checks.info("V4.5", "adresy s novými dotazmi: počet / z toho so zlepšenou presnosťou",
                    f"{len(touched)} / {len(touched & improved)}")

    total = sum(n for _, n in results) or 1
    shares = Counter()
    for r, n in results:
        shares[r["presnost"]] += n
    exact = shares["adresa"] / total
    checks.check("V4.5", exact >= rules["min_podiel_presnych"], "podiel polôh s presnosťou na adresu", f"{exact:.1%}", "WARN")
    checks.info("V4.5", "presnosť polôh", ", ".join(f"{k}: {v / total:.1%}" for k, v in sorted(shares.items())))

    points = Counter((r["lat"], r["lon"]) for r, _ in results if r["zdroj"] == "nominatim")
    clusters = [p for p, n in points.items() if n > rules["max_adries_na_bode"]]
    checks.check("V4.6", not clusters, "na rovnakom bode nie je priveľa rôznych adries", f"{len(clusters)} zhlukov", "WARN")

    con.execute("DELETE FROM geokod")
    con.executemany(
        "INSERT INTO geokod (adresa_kluc, dotaz, lat, lon, presnost, zdroj, obec_kod, problem) "
        "VALUES (:adresa_kluc, :dotaz, :lat, :lon, :presnost, :zdroj, :obec_kod, :problem)",
        [r for r, _ in results],
    )
    report = project_path(cfg, "local") / "reports" / f"geokod_kontrola_{snapshot['stav_k']}.csv"
    write_csv_rows(report, review, REVIEW_COLUMNS)
    checks.info("V4.0", "reporty na ručnú kontrolu", f"{report.name}, {mismatch_report.name}")
    checks.done()
