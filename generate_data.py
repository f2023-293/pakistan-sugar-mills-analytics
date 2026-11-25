"""
Pakistan Sugar Mills: simulated big-data generator
==================================================

Creates a large, realistic but SIMULATED dataset of sugar mill operations in Pakistan
for 10 crushing seasons (2015-16 to 2024-25). Season-level volumes, province shares,
recovery levels and cane prices are calibrated to the real figures stored in data/real/
(PBS, PSMA, Crop Reporting Service Punjab, Economic Survey, USDA GAIN).

Mill names are anonymised codes. District names and cane variety codes are real,
but all mill-level, grower-level and receipt-level values are generated.

Outputs (in --out, default data/synthetic):
  districts.csv                  district -> province lookup
  mills.csv                      85 mills (dimension)
  varieties.csv                  sugarcane varieties (dimension)
  growers.csv.gz                 ~85,000 cane growers (dimension)
  daily_crushing.csv.gz          one row per mill per crushing day (~90,000 rows)
  cane_procurement/procurement_<season>.csv.gz
                                 weighbridge receipts (~1 million rows at the default --scale 0.4)

Usage:
  python src/generate_data.py                 # default, ~1M receipts
  python src/generate_data.py --scale 1       # ~2.5M receipts
  python src/generate_data.py --scale 4       # ~10M receipts (stress-test Spark)
"""
import argparse
import os
from datetime import date, timedelta

import numpy as np
import pandas as pd

SEASONS = ["2015-16", "2016-17", "2017-18", "2018-19", "2019-20",
           "2020-21", "2021-22", "2022-23", "2023-24", "2024-25"]
PROVINCES = ["Punjab", "Sindh", "KPK"]

# --- Real calibration data (see data/real/SOURCES.md) -----------------------
# National sugarcane production, '000 tonnes (PBS / Economic Survey)
NATIONAL_CANE = {"2015-16": 65482, "2016-17": 75482, "2017-18": 83333, "2018-19": 67174,
                 "2019-20": 66380, "2020-21": 81009, "2021-22": 88651, "2022-23": 87981,
                 "2023-24": 87600, "2024-25": 84240}
# Share of cane crushed by mills (2015-16..2018-19 from Sugar Inquiry Commission; others assumed)
CRUSH_RATIO = {"2015-16": 0.764, "2016-17": 0.944, "2017-18": 0.788, "2018-19": 0.741,
               "2019-20": 0.74, "2020-21": 0.80, "2021-22": 0.91, "2022-23": 0.80,
               "2023-24": 0.80, "2024-25": 0.80}
# Province sugarcane production, '000 tonnes (Crop Reporting Service Punjab)
PROV_CANE = {
    "2015-16": (41968, 17984, 5498), "2016-17": (49613, 20209, 5629),
    "2017-18": (55068, 20612, 7610), "2018-19": (44906, 16691, 5532),
    "2019-20": (43347, 17234, 5754), "2020-21": (57001, 18336, 5628),
    "2021-22": (64245, 19333, 5624), "2022-23": (66932, 14637, 4844),
}
PROV_CANE["2023-24"] = PROV_CANE["2022-23"]
PROV_CANE["2024-25"] = PROV_CANE["2022-23"]
# Cane flows: Sindh mills also buy cane from south Punjab; KPK uses much cane for gur
PROV_CRUSH_FACTOR = {"Punjab": 0.95, "Sindh": 1.15, "KPK": 0.55}
# Minimum support price, Rs per 40 kg (USDA GAIN). 2024-25 and KPK 2023-24 assumed.
MSP = {
    "2015-16": (180, 172, 180), "2016-17": (180, 182, 180), "2017-18": (180, 182, 180),
    "2018-19": (180, 182, 180), "2019-20": (190, 192, 190), "2020-21": (200, 202, 200),
    "2021-22": (225, 227, 225), "2022-23": (300, 302, 300), "2023-24": (400, 425, 400),
    "2024-25": (400, 425, 400),
}
# Market premium over MSP in cane-shortage seasons (assumption)
PRICE_PREMIUM = {"2019-20": 1.08, "2020-21": 1.30, "2021-22": 1.10, "2024-25": 1.05}
# Seasons with sugar surplus -> slower grower payments (assumption)
SURPLUS_SEASONS = {"2017-18", "2018-19", "2022-23", "2023-24", "2024-25"}
# Season effect on recovery, tuned so simulated national sugar output tracks the
# real figures in sugar_national_crushing_2015_2020.csv (2022-23 = flood year)
SEASON_REC_EFFECT = {"2015-16": 0.84, "2016-17": 0.72, "2017-18": -0.66, "2018-19": 1.16,
                     "2019-20": 0.30, "2020-21": 0.35, "2021-22": 0.35, "2022-23": 0.10,
                     "2023-24": 0.40, "2024-25": 0.35}

# District -> (province, number of mills, temperature offset C)
DISTRICTS = {
    "Rahim Yar Khan": ("Punjab", 7, 1.5), "Sargodha": ("Punjab", 4, 0.0),
    "Jhang": ("Punjab", 3, 0.5), "Muzaffargarh": ("Punjab", 3, 1.5),
    "Bahawalpur": ("Punjab", 1, 1.5), "Pakpattan": ("Punjab", 1, 0.5),
    "Dera Ghazi Khan": ("Punjab", 1, 1.5), "Kasur": ("Punjab", 1, 0.0),
    "Rajanpur": ("Punjab", 2, 1.5), "Layyah": ("Punjab", 2, 1.0),
    "Bhakkar": ("Punjab", 2, 1.0), "Toba Tek Singh": ("Punjab", 2, 0.5),
    "Faisalabad": ("Punjab", 2, 0.5), "Mandi Bahauddin": ("Punjab", 2, -0.5),
    "Chiniot": ("Punjab", 2, 0.5), "Sheikhupura": ("Punjab", 2, 0.0),
    "Okara": ("Punjab", 2, 0.5), "Vehari": ("Punjab", 2, 1.0),
    "Lodhran": ("Punjab", 2, 1.5), "Khanewal": ("Punjab", 2, 1.0),
    "Ghotki": ("Sindh", 3, 3.0), "Sukkur": ("Sindh", 2, 3.0), "Khairpur": ("Sindh", 3, 3.0),
    "Naushahro Feroze": ("Sindh", 2, 3.5), "Shaheed Benazirabad": ("Sindh", 4, 3.5),
    "Sanghar": ("Sindh", 3, 4.0), "Matiari": ("Sindh", 3, 4.0), "Hyderabad": ("Sindh", 2, 4.5),
    "Tando Allahyar": ("Sindh", 3, 4.5), "Tando Muhammad Khan": ("Sindh", 2, 4.5),
    "Badin": ("Sindh", 3, 5.0), "Thatta": ("Sindh", 2, 5.0),
    "Charsadda": ("KPK", 2, -1.5), "Mardan": ("KPK", 2, -1.5), "Peshawar": ("KPK", 1, -1.0),
    "Dera Ismail Khan": ("KPK", 3, 1.0),
}

# Variety -> (simulated sucrose effect, maturity group, first season available, provinces)
VARIETIES = {
    "CPF-246":   (0.30, "Early", 0, ("Punjab", "KPK")),
    "CPF-247":   (0.35, "Mid", 0, ("Punjab",)),
    "CPF-248":   (0.20, "Mid", 0, ("Punjab",)),
    "CPF-249":   (0.55, "Early", 3, ("Punjab", "Sindh")),
    "CPF-250":   (0.45, "Mid", 5, ("Punjab",)),
    "HSF-240":   (0.20, "Mid", 0, ("Punjab", "Sindh")),
    "HSF-242":   (0.00, "Late", 0, ("Punjab",)),
    "SPF-213":   (-0.20, "Late", 0, ("Punjab", "KPK")),
    "SPF-234":   (-0.10, "Mid", 0, ("Punjab", "Sindh", "KPK")),
    "CP-77-400": (-0.35, "Late", 0, ("Punjab", "Sindh", "KPK")),
    "Thatta-10": (0.15, "Mid", 0, ("Sindh",)),
}
NEW_VARIETIES = {"CPF-249", "CPF-250"}
OLD_VARIETIES = {"CP-77-400", "SPF-213", "HSF-242"}

PROV_IDX = {"Punjab": 0, "Sindh": 1, "KPK": 2}
PROV_CODE = {"Punjab": "PB", "Sindh": "SD", "KPK": "KP"}


# Read the command-line options (--scale, --out, --seed)
def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--scale", type=float, default=0.4,
                   help="receipt sampling multiplier (0.4 = ~1M rows, 1 = ~2.5M rows)")
    p.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "..", "data", "synthetic"))
    p.add_argument("--seed", type=int, default=42)
    return p.parse_args()


# Daily temperature model: a cosine wave over the year (coldest mid-January),
# shifted by the district offset (Sindh is warmer, KPK colder) plus random day-to-day noise.
def temperature(day: date, offset: float, rng) -> float:
    """Mean daily temperature: coldest around 15 January."""
    t = (day - date(day.year if day.month < 7 else day.year + 1, 1, 15)).days
    return 22.0 - 9.0 * np.cos(2 * np.pi * t / 365.0) + offset + rng.normal(0, 1.6)


# Sucrose in cane rises through the winter and peaks in early February (a bell curve),
# then cane "stales" and loses sugar after mid-March. Returns a +/- adjustment to recovery %.
def maturity_effect(day: date) -> float:
    """Cane sucrose builds up to a peak in early February, then stales."""
    dn = (day - date(day.year if day.month >= 7 else day.year - 1, 11, 1)).days
    eff = 0.55 * np.exp(-((dn - 95) / 50.0) ** 2) - 0.28
    if dn > 140:
        eff -= 0.012 * (dn - 140)
    return eff


# Probability of each cane variety in a province for a given season.
# New varieties (CPF-249, CPF-250) gain share every year; old ones are gradually replaced.
def variety_weights(province: str, s_idx: int):
    names, w = [], []
    for v, (eff, grp, first, provs) in VARIETIES.items():
        if province not in provs or s_idx < first:
            continue
        base = 1.0
        if v in NEW_VARIETIES:
            base = 0.6 + 0.45 * (s_idx - first)          # adoption grows each season
        elif v in OLD_VARIETIES:
            base = max(0.25, 1.4 - 0.11 * s_idx)         # gradually replaced
        if province == "Sindh" and v == "Thatta-10":
            base *= 1.8
        names.append(v)
        w.append(base)
    w = np.array(w)
    return names, w / w.sum()


# Create the 85 mills (number per district comes from DISTRICTS).
# Bigger mills are more likely to be "Modern"; technology level drives efficiency, breakdowns and cogeneration.
# Columns starting with "_" are hidden simulation settings and are NOT written to mills.csv.
def build_mills(rng):
    rows = []
    n = 0
    for district, (prov, k, _) in DISTRICTS.items():
        for _ in range(k):
            n += 1
            cap = float(np.clip(rng.lognormal(np.log(9000), 0.38), 3000, 24000))
            p_modern = 0.15 + 0.5 * (cap > 11000) + 0.1 * (prov == "Sindh")
            r = rng.random()
            tech = "Modern" if r < p_modern else ("Standard" if r < p_modern + 0.47 else "Old")
            est = int({"Modern": rng.integers(1995, 2016), "Standard": rng.integers(1975, 2005),
                       "Old": rng.integers(1950, 1990)}[tech])
            cogen = rng.random() < {"Modern": 0.75, "Standard": 0.25, "Old": 0.05}[tech]
            distil = rng.random() < 0.30 + 0.15 * (tech == "Modern")
            listed = rng.random() < 0.40 + 0.2 * (cap > 12000)
            # hidden "financial health" score: listed companies and mills with a distillery pay growers faster
            fin = rng.normal(0, 1) + 0.4 * listed + 0.3 * distil - 0.3 * (tech == "Old")
            rows.append(dict(
                mill_id=f"M{n:03d}", mill_name=f"{PROV_CODE[prov]}-Sugar-Mill-{n:03d}",
                province=prov, district=district, capacity_tcd=int(round(cap, -2)),
                technology_level=tech, established_year=est,
                has_cogeneration=int(cogen), has_distillery=int(distil),
                ownership="PSX Listed" if listed else "Private",
                _fin_health=fin,
                _base_util={"Modern": 0.90, "Standard": 0.84, "Old": 0.75}[tech] + rng.normal(0, 0.03),
                _rec_offset=rng.normal(0, 0.22),
                _queue_hrs={"Modern": 4, "Standard": 8, "Old": 14}[tech],
            ))
    return pd.DataFrame(rows)


# Create about 1,000 cane growers per mill in each district.
# 72% are small farmers (<12.5 acres), 22% medium, 6% large; each has a distance to the mill.
def build_growers(rng, mills):
    rows = []
    gid = 0
    for district, (prov, k, _) in DISTRICTS.items():
        n = int(k * 1000 * rng.uniform(0.85, 1.15))
        types = rng.choice(["Small", "Medium", "Large"], size=n, p=[0.72, 0.22, 0.06])
        acres = np.where(types == "Small", rng.uniform(1, 12.5, n),
                         np.where(types == "Medium", rng.uniform(12.5, 50, n),
                                  rng.lognormal(np.log(110), 0.6, n)))
        dist = np.clip(rng.gamma(2.2, 9, n), 1, 140)
        for i in range(n):
            gid += 1
            rows.append((f"G{gid:06d}", district, prov, types[i], round(float(acres[i]), 1),
                         round(float(dist[i]), 1)))
    return pd.DataFrame(rows, columns=["grower_id", "district", "province", "grower_type",
                                       "farm_size_acres", "distance_to_mill_km"])


# Deliberately add realistic data errors so the notebook has something to clean.
def add_real_world_noise(df, rng):
    """Inject the kind of dirt found in real weighbridge data, so the cleaning step has work to do:
    missing trash readings, unrecorded varieties, lab typos in pol and duplicated receipts."""
    n = len(df)
    df.loc[rng.random(n) < 0.003, "trash_pct"] = np.nan
    df.loc[rng.random(n) < 0.002, "variety_code"] = np.nan
    bad = rng.random(n) < 0.0008
    df.loc[bad, "cane_pol_pct"] = rng.choice([0.0, 99.9, -1.0], size=int(bad.sum()))
    dup = df.sample(frac=0.0015, random_state=int(rng.integers(1e9)))
    return pd.concat([df, dup], ignore_index=True).sort_values(["receipt_date", "receipt_id"])


# ----------------------------------------------------------------------------
# MAIN: builds all tables season by season, mill by mill, day by day
# ----------------------------------------------------------------------------
def main():
    a = parse_args()
    rng = np.random.default_rng(a.seed)        # fixed seed -> the same dataset every time
    out = os.path.abspath(a.out)
    os.makedirs(os.path.join(out, "cane_procurement"), exist_ok=True)

    # ---------------- dimensions ----------------
    pd.DataFrame([(d, p) for d, (p, _, _) in DISTRICTS.items()],
                 columns=["district", "province"]).to_csv(os.path.join(out, "districts.csv"), index=False)
    pd.DataFrame([(v, g, ", ".join(pv)) for v, (_, g, _, pv) in VARIETIES.items()],
                 columns=["variety_code", "maturity_group", "grown_in"]).to_csv(
        os.path.join(out, "varieties.csv"), index=False)

    mills = build_mills(rng)
    mills[[c for c in mills.columns if not c.startswith("_")]].to_csv(
        os.path.join(out, "mills.csv"), index=False)
    growers = build_growers(rng, mills)
    growers.to_csv(os.path.join(out, "growers.csv.gz"), index=False, compression="gzip")
    print(f"mills={len(mills)} growers={len(growers)}")

    # grower pools per district (sampling weight grows with farm size)
    # -> large farmers appear on more receipts than small farmers
    pools = {}
    for d, g in growers.groupby("district"):
        w = g["farm_size_acres"].values ** 0.8
        pools[d] = (g["grower_id"].values, g["grower_type"].values,
                    g["distance_to_mill_km"].values, w / w.sum())

    daily_rows = []
    receipt_rate = 0.05 * a.scale              # share of all weighbridge receipts we keep (0.05 x scale)
    rid = 0

    for s_idx, season in enumerate(SEASONS):
        y = int(season[:4])
        # province crushing targets (tonnes): REAL national cane production x share crushed by mills,
        # split between provinces using REAL province production. This is the calibration step.
        nat_crushed = NATIONAL_CANE[season] * 1000 * CRUSH_RATIO[season]
        weighted = np.array([PROV_CANE[season][i] * PROV_CRUSH_FACTOR[p] for i, p in enumerate(PROVINCES)])
        prov_target = dict(zip(PROVINCES, nat_crushed * weighted / weighted.sum()))

        # which mills operate this season (old mills are more likely to stay closed in a season)
        op = mills[rng.random(len(mills)) < np.where(mills["technology_level"] == "Old", 0.86, 0.96)].copy()
        op["_w"] = op["capacity_tcd"] * op["technology_level"].map({"Modern": 1.1, "Standard": 1.0, "Old": 0.85})
        # each mill gets a share of its province target in proportion to its size and efficiency
        op["_target"] = op.apply(lambda r: prov_target[r.province] * r._w /
                                 op.loc[op.province == r.province, "_w"].sum(), axis=1)
        season_receipts = []

        for _, m in op.iterrows():
            prov = m.province
            temp_off = DISTRICTS[m.district][2]
            # crushing starts in late November (Sindh and KPK a little earlier), +/- a few days per mill
            start = {"Punjab": date(y, 11, 25), "Sindh": date(y, 11, 18), "KPK": date(y, 11, 10)}[prov]
            start += timedelta(days=int(rng.integers(-4, 9)))
            util = float(np.clip(m._base_util, 0.6, 0.97))
            # season length = cane to crush / (daily capacity x utilisation), kept between 45 and 150 days
            n_days = int(np.clip(round(m._target / (m.capacity_tcd * util * 0.93)), 45, 150))
            vnames, vw = variety_weights(prov, s_idx)
            # better variety mix in the catchment -> slightly higher recovery
            var_eff = float(sum(VARIETIES[v][0] * w for v, w in zip(vnames, vw))) * 0.6
            # daily chance of a machinery breakdown (old mills break down far more often)
            p_bd = {"Modern": 0.04, "Standard": 0.08, "Old": 0.15}[m.technology_level]

            # ---------------- daily crushing simulation ----------------
            days, crushed = [], []
            for i in range(n_days):
                d = start + timedelta(days=i)
                T = temperature(d, temp_off, rng)
                rain = float(rng.exponential(7)) if rng.random() < (0.08 if d.month in (12, 1, 2) else 0.03) else 0.0
                bd = float(rng.uniform(1, 12)) if rng.random() < p_bd else 0.0
                # slow start in the first week and slow-down in the last 8 days of the season
                ramp = min(1.0, 0.5 + i * 0.09) * (1.0 if i < n_days - 8 else 0.6 + 0.05 * (n_days - 1 - i))
                # utilisation today: reduced by breakdown hours and by heavy rain (cane cannot reach the mill)
                u = util * ramp * (1 - bd / 24) * (0.8 if rain > 8 else 1.0) * rng.normal(1, 0.045)
                # RECOVERY % model = province base + technology + season + mill effect + variety mix
                #   + cane maturity (date) - temperature effect - breakdown effect + random noise
                rec = (9.25 if prov == "Punjab" else 9.75 if prov == "Sindh" else 8.6) \
                    + {"Modern": 0.35, "Standard": 0.0, "Old": -0.45}[m.technology_level] \
                    + SEASON_REC_EFFECT[season] + m._rec_offset + var_eff + maturity_effect(d) \
                    - 0.06 * (T - 15) - 0.04 * bd + rng.normal(0, 0.12)
                rec = float(np.clip(rec, 7.0, 12.5))
                days.append([d, i + 1, T, rain, bd, rec])
                crushed.append(max(u, 0.05) * m.capacity_tcd)
            crushed = np.array(crushed) * (m._target / np.sum(crushed))   # match calibrated total
            crushed = np.minimum(crushed, 1.12 * m.capacity_tcd)           # physical limit

            # derive the other daily measures: sugar = cane x recovery, molasses ~4.5%, bagasse from fibre,
            # electricity exported only by mills with a cogeneration plant
            for (d, dn, T, rain, bd, rec), c in zip(days, crushed):
                fiber = rng.normal(14.5, 0.6) + (0.3 if m.technology_level == "Old" else 0)
                pol = rec / rng.normal(0.745, 0.008)
                sugar = c * rec / 100
                bag = c * fiber / 100 * 2.0
                daily_rows.append((
                    season, d.isoformat(), m.mill_id, dn, round(c, 1), round(sugar, 1), round(rec, 2),
                    round(pol, 2), round(fiber, 2), round(c * rng.normal(0.045, 0.002), 1), round(bag, 1),
                    round(bag * rng.normal(0.10, 0.01), 1) if m.has_cogeneration else 0.0,
                    round(c / m.capacity_tcd * 100, 1), round(bd, 1),
                    round(24 - bd - (2 if c / m.capacity_tcd < 0.5 else 0), 1),
                    round(T, 1), round(rain, 1)))

            # ---------------- procurement receipts ----------------
            g_ids, g_type, g_dist, g_w = pools[m.district]
            # number of receipts per day is proportional to the cane crushed that day (Poisson = random count)
            n_per_day = rng.poisson(crushed * receipt_rate / 13.0)
            n = int(n_per_day.sum())
            if n == 0:
                continue
            day_idx = np.repeat(np.arange(n_days), n_per_day)
            gi = rng.choice(len(g_ids), size=n, p=g_w)   # pick which grower delivered each receipt
            gtype = g_type[gi]
            gdist = g_dist[gi]
            r = rng.random(n)
            # transport mode depends on farm size: large farmers use trucks, small farmers trolleys or bullock carts
            mode = np.where(gtype == "Large", np.where(r < 0.62, "Truck", "Tractor-Trolley"),
                    np.where(gtype == "Medium", np.where(r < 0.30, "Truck", np.where(r < 0.95, "Tractor-Trolley", "Bullock Cart")),
                             np.where(r < 0.13, "Truck", np.where(r < 0.72, "Tractor-Trolley", "Bullock Cart"))))
            mode = np.where((mode == "Bullock Cart") & (gdist > 15), "Tractor-Trolley", mode)
            dist_km = np.where(mode == "Bullock Cart", np.minimum(gdist, 15),
                               np.where(mode == "Truck", gdist + rng.uniform(5, 40, n), gdist))
            # load weight depends on the vehicle (cart 1.5-4 t, trolley ~12 t, truck ~25 t)
            gross = np.where(mode == "Bullock Cart", rng.uniform(1.5, 4, n),
                             np.where(mode == "Truck", np.clip(rng.normal(25, 4, n), 15, 40),
                                      np.clip(rng.normal(12, 2.5, n), 5, 20)))
            dates = np.array([days[k][0] for k in day_idx])
            temps = np.array([days[k][2] for k in day_idx])
            month = np.array([d.month for d in dates])
            mat = np.array([maturity_effect(d) for d in dates])
            frac = day_idx / max(n_days - 1, 1)
            # hours from harvest to crushing = travel time + waiting at the farm + queue at the mill gate
            hrs = (dist_km / np.where(mode == "Bullock Cart", 5, np.where(mode == "Truck", 35, 18))
                   + rng.gamma(2.0, 7.0, n) + m._queue_hrs * (0.6 + 0.8 * np.sin(np.pi * frac)) * rng.uniform(0.5, 1.5, n))
            # trash % (leaves, tops, mud) is higher early in the season and on bullock carts
            trash = np.clip(rng.normal(4.0, 1.4, n) + 1.0 * (month == 11) + 0.6 * (mode == "Bullock Cart"), 1, 12)
            vnames_arr = np.array(vnames)
            var = vnames_arr[rng.choice(len(vnames), size=n, p=vw)]
            var_e = np.array([VARIETIES[v][0] for v in var])
            # cane pol % (sucrose) = province base + variety + maturity + season - staleness - trash - temperature + noise
            pol = ({"Punjab": 12.4, "Sindh": 13.0, "KPK": 11.6}[prov] + var_e + 1.3 * mat
                   + 1.2 * SEASON_REC_EFFECT[season]
                   - 0.015 * (hrs - 24) - 0.10 * (trash - 4) - 0.05 * (temps - 15)
                   + {"Modern": 0.15, "Standard": 0.0, "Old": -0.15}[m.technology_level]
                   + rng.normal(0, 0.45, n))
            deduct = gross * trash / 100 * 0.8           # weight deducted by the mill for trash
            net = gross - deduct
            # price paid = official support price (x market premium in shortage seasons) +/- 2%
            price = MSP[season][PROV_IDX[prov]] * PRICE_PREMIUM.get(season, 1.0) * rng.normal(1, 0.02, n)
            if season not in PRICE_PREMIUM:
                price = np.maximum(price, MSP[season][PROV_IDX[prov]])
            # PAYMENT DELAY (days) is higher for financially weak mills, surplus seasons, late-season deliveries,
            # small growers, old mills and Sindh; this is the pattern the classification model has to learn
            delay = (2 - 5.5 * m._fin_health + 9 * (season in SURPLUS_SEASONS)
                     + 5 * (month >= 3) + 3 * (gtype == "Small") - 3 * (gtype == "Large")
                     + 3 * (m.technology_level == "Old") + 4 * (prov == "Sindh")
                     + rng.exponential(5, n) + rng.normal(0, 3, n))
            delay = np.clip(np.round(delay), 1, 180).astype(int)
            pay_mode = np.where(rng.random(n) < np.where(gtype == "Small", 0.18, 0.05), "Cash",
                                np.where(rng.random(n) < 0.6, "Bank Transfer", "Cheque"))
            ids = np.arange(rid + 1, rid + n + 1)
            rid += n
            season_receipts.append(pd.DataFrame({
                "receipt_id": [f"R{x:09d}" for x in ids],
                "season": season,
                "receipt_date": [d.isoformat() for d in dates],
                "receipt_hour": rng.integers(0, 24, n),
                "mill_id": m.mill_id,
                "grower_id": g_ids[gi],
                "variety_code": var,
                "transport_mode": mode,
                "distance_km": np.round(dist_km, 1),
                "harvest_to_crush_hrs": np.round(hrs, 1),
                "gross_weight_t": np.round(gross, 3),
                "trash_pct": np.round(trash, 2),
                "deduction_t": np.round(deduct, 3),
                "net_weight_t": np.round(net, 3),
                "cane_pol_pct": np.round(pol, 2),
                "price_rs_per_40kg": np.round(price, 0),
                "amount_rs": np.round(net * 25 * np.round(price, 0), 0),
                "payment_delay_days": delay,
                "payment_mode": pay_mode,
            }))

        # combine all mills of this season, add data errors, and save one compressed file per season
        rec_df = pd.concat(season_receipts, ignore_index=True)
        rec_df = add_real_world_noise(rec_df, rng)
        f = os.path.join(out, "cane_procurement", f"procurement_{season.replace('-', '_')}.csv.gz")
        rec_df.to_csv(f, index=False, compression="gzip")
        print(f"{season}: mills={len(op)} receipts={len(rec_df):,}  file={os.path.getsize(f)/1e6:.1f} MB")

    # save the mill-day table and print season totals so they can be compared with the real figures
    daily = pd.DataFrame(daily_rows, columns=[
        "season", "date", "mill_id", "crushing_day", "cane_crushed_t", "sugar_produced_t",
        "recovery_pct", "pol_pct_cane", "fiber_pct", "molasses_t", "bagasse_t",
        "power_exported_mwh", "capacity_utilization_pct", "breakdown_hrs", "operating_hrs",
        "avg_temp_c", "rainfall_mm"])
    miss = rng.random(len(daily)) < 0.004                      # sensor gaps
    daily.loc[miss, "avg_temp_c"] = np.nan
    daily.to_csv(os.path.join(out, "daily_crushing.csv.gz"), index=False, compression="gzip")
    print(f"daily_crushing rows={len(daily):,}")
    print(daily.groupby("season").agg(crushed_mt=("cane_crushed_t", lambda x: x.sum() / 1e6),
                                      sugar_mt=("sugar_produced_t", lambda x: x.sum() / 1e6)).round(2))


if __name__ == "__main__":
    main()
