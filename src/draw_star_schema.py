"""Draws the data warehouse star schema to docs/star_schema.png"""
import os
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

OUT = os.path.join(os.path.dirname(__file__), "..", "docs", "star_schema.png")

TABLES = {
    "fact_cane_procurement": ((5.0, 6.2), "#F4B942", [
        "receipt_id (PK)", "date_key (FK)", "mill_key (FK)", "grower_key (FK)", "variety_key (FK)",
        "gross_weight_t", "deduction_t", "net_weight_t", "trash_pct", "cane_pol_pct",
        "harvest_to_crush_hrs", "distance_km", "price_rs_per_40kg", "amount_rs",
        "payment_delay_days", "is_late_payment"]),
    "fact_daily_crushing": ((5.0, 1.2), "#F4B942", [
        "date_key (FK)", "mill_key (FK)", "cane_crushed_t", "sugar_produced_t", "recovery_pct",
        "molasses_t", "bagasse_t", "power_exported_mwh", "capacity_utilization_pct",
        "breakdown_hrs", "avg_temp_c", "rainfall_mm"]),
    "dim_date": ((0.3, 4.4), "#7EB6D9", [
        "date_key (PK)", "full_date", "day", "month", "month_name", "quarter", "year",
        "season", "week_of_season", "crushing_phase"]),
    "dim_mill": ((9.7, 4.4), "#7EB6D9", [
        "mill_key (PK)", "mill_id", "mill_name", "district", "province", "capacity_tcd",
        "capacity_class", "technology_level", "established_year", "has_cogeneration",
        "has_distillery", "ownership"]),
    "dim_grower": ((0.3, 8.6), "#7EB6D9", [
        "grower_key (PK)", "grower_id", "district", "province", "grower_type",
        "farm_size_acres", "distance_to_mill_km"]),
    "dim_variety": ((9.7, 8.6), "#7EB6D9", [
        "variety_key (PK)", "variety_code", "maturity_group", "grown_in"]),
}
W, LH = 3.4, 0.27


def box(ax, name, xy, color, cols):
    x, y = xy
    h = LH * (len(cols) + 1.4)
    ax.add_patch(FancyBboxPatch((x, y), W, h, boxstyle="round,pad=0.04", fc="white", ec="#333", lw=1.2))
    ax.add_patch(FancyBboxPatch((x, y + h - LH * 1.3), W, LH * 1.3, boxstyle="round,pad=0.04",
                                fc=color, ec="#333", lw=1.2))
    ax.text(x + W / 2, y + h - LH * 0.65, name, ha="center", va="center", fontsize=10, weight="bold")
    for i, c in enumerate(cols):
        ax.text(x + 0.12, y + h - LH * (1.9 + i), c, fontsize=8, va="center",
                weight="bold" if "(PK)" in c else "normal", color="#B03030" if "(FK)" in c else "#222")
    return (x, y, W, h)


fig, ax = plt.subplots(figsize=(14, 12))
pos = {n: box(ax, n, *v) for n, v in TABLES.items()}


def link(a, b):
    xa, ya, wa, ha = pos[a]
    xb, yb, wb, hb = pos[b]
    ax.annotate("", xy=(xb + wb / 2, yb + hb / 2), xytext=(xa + wa / 2, ya + ha / 2),
                arrowprops=dict(arrowstyle="-", color="#777", lw=1.4, ls="--"), zorder=0)


for f, ds in [("fact_cane_procurement", ["dim_date", "dim_mill", "dim_grower", "dim_variety"]),
              ("fact_daily_crushing", ["dim_date", "dim_mill"])]:
    for d in ds:
        link(f, d)
ax.set_xlim(0, 13.4)
ax.set_ylim(0.8, 11.4)
ax.axis("off")
ax.set_title("Pakistan Sugar Mills Data Warehouse: Galaxy (fact constellation) schema", fontsize=14, weight="bold")
plt.tight_layout()
os.makedirs(os.path.dirname(OUT), exist_ok=True)
plt.savefig(OUT, dpi=130)
print("saved", os.path.abspath(OUT))
