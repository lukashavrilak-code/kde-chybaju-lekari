import numpy as np
import pandas as pd

from .checks import Checks
from .config import project_path
from .files import read_csv_rows, replace_csv_rows

R_EARTH_KM = 6371.0
TYPES = ("VLD", "VLDD")
DENOMINATOR = {"VLD": "obyv_dospeli", "VLDD": "obyv_deti"}
HISTORY_COLUMNS = ["stav_k", "okres_kod", "typ", "pocet", "pocet_pracovisk"]
WORKPLACE = ["ico", "adresa_kluc"]
FAR_COLUMNS = ["podiel_nad_5km", "podiel_nad_10km"]


def haversine_km(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = (np.radians(np.asarray(v, dtype=float)) for v in (lat1, lon1, lat2, lon2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 2 * R_EARTH_KM * np.arcsin(np.sqrt(a))


def load_ambulances(con, snapshot_id):
    return pd.read_sql("SELECT * FROM v_ambulancia WHERE snapshot_id = ?", con, params=(snapshot_id,))


def okres_indicators(amb, okresy, typ):
    subset = amb[amb["typ"] == typ]
    counts = subset.groupby("okres_kod").size().reindex(okresy["okres_kod"], fill_value=0)
    workplaces = subset.drop_duplicates(WORKPLACE).groupby("okres_kod").size().reindex(okresy["okres_kod"], fill_value=0)
    denominator = okresy.set_index("okres_kod")[DENOMINATOR[typ]]
    rate = (counts / denominator * 10000).round(2)
    return pd.DataFrame({
        "okres_kod": counts.index,
        "typ": typ,
        "pocet": counts.values.astype(int),
        "pocet_pracovisk": workplaces.values.astype(int),
        "na_10k": rate.values,
        "poradie": rate.rank(method="min").astype(int).values,
    })


def obec_indicators(amb, obce, typ, radii):
    subset = amb[amb["typ"] == typ]
    result = pd.DataFrame({"obec_kod": obce["obec_kod"].values, "typ": typ})
    result["pocet_v_obci"] = subset.groupby("obec_kod").size().reindex(obce["obec_kod"], fill_value=0).values
    if subset.empty:
        result["najblizsia_km"] = np.nan
        result["pocet_10km"] = 0
        result["pocet_20km"] = 0
        return result
    distances = haversine_km(
        obce["ref_lat"].values[:, None], obce["ref_lon"].values[:, None],
        subset["lat"].values[None, :], subset["lon"].values[None, :],
    )
    result["najblizsia_km"] = distances.min(axis=1)
    result["pocet_10km"] = (distances <= radii[0]).sum(axis=1)
    result["pocet_20km"] = (distances <= radii[1]).sum(axis=1)
    return result


def catchment_access(amb, obce, typ, radius_km):
    subset = amb[amb["typ"] == typ]
    population = obce[DENOMINATOR[typ]].to_numpy(dtype=float)
    if subset.empty:
        return np.zeros(len(obce)), 0
    distances = haversine_km(
        obce["ref_lat"].values[:, None], obce["ref_lon"].values[:, None],
        subset["lat"].values[None, :], subset["lon"].values[None, :],
    )
    within = (distances <= radius_km).astype(float)
    demand = within.T @ population
    shares = np.divide(1.0, demand, out=np.zeros_like(demand), where=demand > 0)
    return within @ shares * 10000, int((demand > 0).sum())


def catchment_by_okres(obec_rows, obce, typ):
    column = DENOMINATOR[typ]
    rows = obec_rows.merge(obce[["obec_kod", "okres_kod", column]], on="obec_kod")
    weighted = (rows["na_10k_okolie"] * rows[column]).groupby(rows["okres_kod"]).sum()
    rate = (weighted / rows.groupby("okres_kod")[column].sum()).round(2)
    return pd.DataFrame({
        "okres_kod": rate.index,
        "typ": typ,
        "na_10k_okolie": rate.values,
        "poradie_okolie": rate.rank(method="min").astype(int).values,
    })


def distance_shares(obec_rows, obce, typ, limits):
    column = DENOMINATOR[typ]
    rows = obec_rows.merge(obce[["obec_kod", "okres_kod", column]], on="obec_kod")
    distance = rows["najblizsia_km"].fillna(np.inf)
    population = rows.groupby("okres_kod")[column].sum()
    result = pd.DataFrame({"okres_kod": population.index, "typ": typ})
    for name, km in zip(FAR_COLUMNS, limits):
        far = rows[column].where(distance > km, 0).groupby(rows["okres_kod"]).sum()
        result[name] = (far / population).round(4).values
    return result


def check_history(cfg, checks, stav_k, current, confirmed):
    rules = cfg["validacia"]
    rows = read_csv_rows(project_path(cfg, "history") / "pocty_okresy.csv")
    earlier = sorted({r["stav_k"] for r in rows if r["stav_k"] < stav_k})
    if not earlier:
        checks.info("V5.4", "prvý snapshot v histórii, zmeny sa neporovnávajú")
        return
    previous = {(r["okres_kod"], r["typ"]): int(r["pocet"]) for r in rows if r["stav_k"] == earlier[-1]}
    for typ in TYPES:
        now = current[current["typ"] == typ]
        before_total = sum(v for (_, t), v in previous.items() if t == typ)
        if not before_total:
            continue
        change = (now["pocet"].sum() - before_total) / before_total
        level = "WARN" if abs(change) <= rules["zmena_sr_fail"] or confirmed else "FAIL"
        checks.check("V5.4", abs(change) <= rules["zmena_sr_warn"], f"zmena počtu {typ} za SR oproti {earlier[-1]}",
                     f"{change:+.1%}", level)
        jumps = []
        for row in now.itertuples():
            old = previous.get((row.okres_kod, typ), 0)
            if abs(row.pocet - old) >= max(rules["zmena_okres_min"], rules["zmena_okres_podiel"] * old):
                jumps.append(f"{row.okres_kod}: {old}→{row.pocet}")
        checks.check("V5.4", not jumps, f"žiadny okres nemá skokovú zmenu {typ}", f"{len(jumps)} okresov", "WARN",
                     detail=", ".join(jumps))


def compute(cfg, con, snapshot, confirmed=False):
    sid = snapshot["snapshot_id"]
    stav_k = snapshot["stav_k"]
    checks = Checks(con, "5-compute", sid)
    rules = cfg["validacia"]
    amb = load_ambulances(con, sid)
    okresy = pd.read_sql("SELECT * FROM okres ORDER BY okres_kod", con)
    obce = pd.read_sql("SELECT * FROM obec ORDER BY obec_kod", con)
    radii = cfg["vypocty"]["polomery_km"]

    checks.check("V5.1", bool(amb["okres_kod"].notna().all()), "každá ambulancia má okres", f"{int(amb['okres_kod'].isna().sum())} bez okresu")
    for typ in TYPES:
        column = DENOMINATOR[typ]
        checks.check("V5.2", bool((okresy[column] > 0).all()), f"menovateľ {column} je kladný vo všetkých okresoch")
    checks.done()

    by_okres = pd.concat([okres_indicators(amb, okresy, typ) for typ in TYPES], ignore_index=True)
    catchment_km = cfg["vypocty"]["spadova_oblast_km"]
    obec_parts, served = [], {}
    for typ in TYPES:
        part = obec_indicators(amb, obce, typ, radii)
        part["na_10k_okolie"], served[typ] = catchment_access(amb, obce, typ, catchment_km)
        obec_parts.append(part)
    by_obec = pd.concat(obec_parts, ignore_index=True)
    limits = cfg["vypocty"]["podiel_nad_km"]
    shares = pd.concat([distance_shares(by_obec[by_obec["typ"] == typ], obce, typ, limits) for typ in TYPES], ignore_index=True)
    catchment = pd.concat([catchment_by_okres(by_obec[by_obec["typ"] == typ], obce, typ) for typ in TYPES], ignore_index=True)
    by_okres = by_okres.merge(shares, on=["okres_kod", "typ"], how="left").merge(catchment, on=["okres_kod", "typ"], how="left")
    names = obce.set_index("obec_kod")["nazov"]

    for typ in TYPES:
        part = by_okres[by_okres["typ"] == typ]
        checks.check("V5.1", int(part["pocet"].sum()) == int((amb["typ"] == typ).sum()),
                     f"súčet okresov sa rovná počtu ambulancií {typ}", int(part["pocet"].sum()))
        checks.check("V5.1", bool((part["pocet_pracovisk"] <= part["pocet"]).all()),
                     f"počet pracovísk {typ} nie je v žiadnom okrese vyšší ako počet ambulancií")
        checks.info("V5.1", f"pracoviská {typ} za SR (rovnaké IČO a adresa)", int(part["pocet_pracovisk"].sum()))
        median = part["na_10k"].median()
        outliers = part[part["na_10k"] > rules["odlahla_hodnota_nasobok"] * median]
        checks.check("V5.2", outliers.empty, f"bez odľahlých hodnôt {typ} na 10 000 (nad {rules['odlahla_hodnota_nasobok']}× medián)",
                     f"{len(outliers)} okresov", "WARN", detail=", ".join(outliers["okres_kod"]))
        rows = by_obec[by_obec["typ"] == typ]
        inconsistent = ((rows["najblizsia_km"] <= radii[0]) != (rows["pocet_10km"] >= 1)).sum()
        checks.check("V5.5", inconsistent == 0, f"najbližšia ambulancia a počet do {radii[0]} km sú konzistentné ({typ})",
                     f"{int(inconsistent)} obcí")
        limit_km = rules["vzdialenost_v_obci_km"]
        own = rows[(rows["pocet_v_obci"] > 0) & (rows["najblizsia_km"] > limit_km)]
        checks.info("V5.6", f"obce s ambulanciou {typ} v obci, ale referenčný bod je od najbližšej ďalej ako {limit_km:g} km",
                    len(own), detail=", ".join(names[own["obec_kod"]].head(40)))
        population = obce.set_index("obec_kod").loc[rows["obec_kod"], DENOMINATOR[typ]].to_numpy()
        distributed = float((rows["na_10k_okolie"].to_numpy() * population).sum() / 10000)
        checks.check("V5.7", abs(distributed - served[typ]) < 1e-6 * max(served[typ], 1),
                     f"U8 rozdelí medzi obyvateľov presne všetky ambulancie {typ}, ktoré majú obyvateľov do {catchment_km} km",
                     f"{distributed:.3f} / {served[typ]}")
        checks.info("V5.7", f"ambulancie {typ} bez obyvateľov do {catchment_km} km (v U8 sa nepočítajú)",
                    int((amb["typ"] == typ).sum()) - served[typ])

    check_history(cfg, checks, stav_k, by_okres, confirmed)

    con.execute("DELETE FROM ukazovatel_okres WHERE snapshot_id = ?", (sid,))
    con.executemany(
        "INSERT INTO ukazovatel_okres (snapshot_id, okres_kod, typ, pocet, pocet_pracovisk, na_10k, poradie, podiel_nad_5km, "
        "podiel_nad_10km, na_10k_okolie, poradie_okolie) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [(sid, r.okres_kod, r.typ, int(r.pocet), int(r.pocet_pracovisk), float(r.na_10k), int(r.poradie),
          float(r.podiel_nad_5km), float(r.podiel_nad_10km), float(r.na_10k_okolie), int(r.poradie_okolie))
         for r in by_okres.itertuples()],
    )
    con.execute("DELETE FROM ukazovatel_obec WHERE snapshot_id = ?", (sid,))
    con.executemany(
        "INSERT INTO ukazovatel_obec (snapshot_id, obec_kod, typ, najblizsia_km, pocet_v_obci, pocet_10km, pocet_20km, "
        "na_10k_okolie) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (sid, r.obec_kod, r.typ, None if pd.isna(r.najblizsia_km) else float(r.najblizsia_km),
             int(r.pocet_v_obci), int(r.pocet_10km), int(r.pocet_20km), float(r.na_10k_okolie))
            for r in by_obec.itertuples()
        ],
    )
    history = [
        {"stav_k": stav_k, "okres_kod": r.okres_kod, "typ": r.typ, "pocet": int(r.pocet), "pocet_pracovisk": int(r.pocet_pracovisk)}
        for r in by_okres.itertuples()
    ]
    replace_csv_rows(project_path(cfg, "history") / "pocty_okresy.csv", history, HISTORY_COLUMNS, "stav_k", stav_k,
                     ["stav_k", "okres_kod", "typ"])
    checks.done()
