import pandas as pd

exec(open("01-ingest.py").read())
exec(open("02-join.py").read())
exec(open("03-clean.py").read())

KEY_COLS = ["wave", "max_panel_length", "survey_year", "individual_id"]


# ── 1. Survey year within wave range ──────────────────────────────────────

print("\n=== 1. Survey year within wave range ===")

def wave_years(label: str) -> tuple[int, int]:
    return 2000 + int(label[:2]), 2000 + int(label[6:])

issues = []
for label, grp in silc0624.groupby("wave", observed=True):
    lo, hi = wave_years(label)
    n_bad = (~grp["survey_year"].between(lo, hi)).sum()
    if n_bad:
        issues.append((label, lo, hi, n_bad))

if issues:
    for label, lo, hi, n in issues:
        print(f"  FAIL  {label}: {n:,} rows outside [{lo}, {hi}]")
else:
    print("  PASSED:  all survey years within wave range")


# ── 2. Unique individual IDs per year: silc0624 vs raw fk files ───────────

print("\n=== 2. Unique individual_ids per (wave, survey_year): silc0624 vs raw ===")

silc_counts = (
    silc0624
    .groupby(["wave", "survey_year"], observed=True)["individual_id"]
    .nunique()
    .reset_index(name="n_pooled_silc")
)

raw_rows = []
for label, folder, _, sep in PANELS:
    prefix = "GYK" if label == "08091011" else "gyk"
    fk_raw = pd.read_csv(
        f"{folder}/{prefix}{label}_fk.csv",
        sep=sep, dtype=str, na_values=["."],
        usecols=["FKIMLIK", "FK010"],
    )
    fk_raw["FK010"] = pd.to_numeric(fk_raw["FK010"], errors="coerce")
    for year, grp in fk_raw.groupby("FK010", dropna=True):
        raw_rows.append({"wave": label, "survey_year": int(year), "n_raw": grp["FKIMLIK"].nunique()})

raw_counts = pd.DataFrame(raw_rows)
cmp = silc_counts.merge(raw_counts, on=["wave", "survey_year"], how="outer")
cmp["delta"] = cmp["n_pooled_silc"] - cmp["n_raw"]
print(cmp.to_string(index=False))
n_mismatch = (cmp["delta"] != 0).sum()
print(f"\n  {'PASSED:' if n_mismatch == 0 else 'FAILED'}  {n_mismatch} (wave, year) combos with mismatched counts")


# ── 2b. Unique individuals by wave × max_panel_length ────────────────────

print("\n=== 2b. Unique individuals by wave × max_panel_length ===")

uniq = (
    silc0624
    .groupby(["wave", "max_panel_length"], observed=True)["individual_id"]
    .nunique()
    .unstack("max_panel_length")
)
uniq.columns = [f"len={int(c)}" if pd.notna(c) else "len=NA" for c in uniq.columns]
uniq["total"] = uniq.sum(axis=1)
print(uniq.to_string())
print(f"\n  total unique individuals across all waves: {silc0624['individual_id'].nunique():,}")


# ── 2c. Reconcile selected waves against published TÜİK sample sizes ─────
# Published figures are CUMULATIVE (≥ x years), while max_panel_length is
# EXCLUSIVE.  Mapping: 4-yr = len=4; 3-yr = len≥3; 2-yr = total (all).
# Sources:
#   19202122 — "sırasıyla 61 313, 40 040 ve 19 669 ferttir"
#   20212223 — "sırasıyla 57 705, 37 402 ve 18 478 ferttir"
#   21222324 — "56 612 … two-year; 36 680 … three-year; 17 839 … four-year"

print("\n=== 2c. Reconcile against published sample sizes ===")

PUBLISHED = {
    "19202122": {4: 19_669, 3: 40_040, 2: 61_313},
    "20212223": {4: 18_478, 3: 37_402, 2: 57_705},
    "21222324": {4: 17_839, 3: 36_680, 2: 56_612},
}

all_rows = []
for wave, pub in PUBLISHED.items():
    w_counts = uniq.loc[wave]
    observed = {
        4: int(w_counts.get("len=4", 0)),
        3: int(w_counts.get("len=3", 0) + w_counts.get("len=4", 0)),
        2: int(w_counts["total"]),
    }
    for pl, published in pub.items():
        got = observed[pl]
        all_rows.append({"wave": wave, "panel_length": pl, "published": published, "data": got, "delta": got - published})

rec = pd.DataFrame(all_rows).set_index(["wave", "panel_length"])
print(rec.to_string())
n_fail = (rec["delta"] != 0).sum()
if n_fail == 0:
    print("\n  PASSED  all counts match published figures")
else:
    print(f"\n  FLAG  {n_fail} mismatches above")


# ── 3. Null key identifiers ───────────────────────────────────────────────

print("\n=== 3. Null key identifiers in pooled data ===")
for col in KEY_COLS:
    n = silc0624[col].isna().sum()
    print(f"  {'PASSED' if n == 0 else 'FLAG'}  {col}: {n:,} nulls")


# ── 4. Duplicates: wave × max_panel_length × survey_year × individual_id ──

print("\n=== 4. Total duplicates in pooled: wave × max_panel_length × survey_year × individual_id ===")

dup_mask = silc0624.duplicated(subset=KEY_COLS, keep=False)
n_dup_rows = dup_mask.sum()

if n_dup_rows == 0:
    print("  PASSED  no duplicates")
else:
    n_dup_keys = silc0624.loc[dup_mask, KEY_COLS].drop_duplicates().shape[0]
    print(f"  FLAG:  {n_dup_rows:,} rows ({n_dup_keys:,} distinct key combos)")

    sample_ids = (
        silc0624.loc[dup_mask, "individual_id"]
        .drop_duplicates()
        .sample(min(30, dup_mask.sum()), random_state=42)
        .tolist()
    )
    print("Most duplicates are expected to be due to the same individual_id appearing in multiple households.To eyeball:")
    print("\n  30 random example individual_ids to eyeball:")
    print(
        silc0624.loc[silc0624["individual_id"].isin(sample_ids) & dup_mask, KEY_COLS]
        .drop_duplicates("individual_id")
        .sort_values(KEY_COLS)
        .to_string(index=False)
    )


# ── 5. Panel composition drift ────────────────────────────────────────────

print("\n=== 5. Panel composition drift by wave ===")
print("  Checks whether the sample's structural makeup shifts suspiciously across waves.")
print("  Expected: gradual demographic change. Suspect: abrupt jumps that suggest a")
print("  sampling-frame change, boundary redefinition, or attrition bias taking hold.")

# 5a. max_panel_length share — attrition shifts the balance toward shorter spells
panel_len_dist = (
    silc0624
    .groupby(["wave", "max_panel_length"], observed=True)
    .size()
    .unstack("max_panel_length", fill_value=0)
)
panel_len_pct = panel_len_dist.div(panel_len_dist.sum(axis=1), axis=0).mul(100).round(1)
print("\n  max_panel_length share (%) by wave:")
print(panel_len_pct.to_string())

wave_order = list(panel_len_pct.index)
for i in range(1, len(wave_order)):
    for pl in panel_len_pct.columns:
        if pl not in panel_len_pct.columns:
            continue
        delta = panel_len_pct.loc[wave_order[i], pl] - panel_len_pct.loc[wave_order[i - 1], pl]
        if abs(delta) > 10:
            print(f"  FLAG  panel_length={pl}: {wave_order[i-1]}→{wave_order[i]}: {delta:+.1f}pp")

# 5b. Sex ratio, mean age, urban share, mean household income — last year of each wave,
#     broken down by max_panel_length to expose attrition-linked selection.
#     Restricted to last year to avoid overlap bias from multi-wave individuals.
#     Age suppressed for 06070809: FK070 was coded as age groups (1–14) in that wave,
#     not completed years; computing a mean would be meaningless.
#     Income (hh_total_disposable_income) is nominal TL — expect inflation-driven growth;
#     it is shown for context but not flagged with a fixed threshold.

CATEGORICAL_AGE_WAVES = {"06070809"}

snapshot = silc0624[
    silc0624["survey_year"]
    == silc0624.groupby("wave", observed=True)["survey_year"].transform("max")
]

detail_rows = []
for (wave, pl), grp in snapshot.groupby(["wave", "max_panel_length"], observed=True):
    row: dict = {"wave": wave, "max_panel_length": pl, "n": len(grp)}
    if "sex" in grp.columns:
        row["pct_female"] = (grp["sex"] == 2).mean() * 100
    if "age" in grp.columns and wave not in CATEGORICAL_AGE_WAVES:
        row["mean_age"] = grp["age"].mean()
    if "urban_rural" in grp.columns:
        row["pct_urban"] = (grp["urban_rural"] == 1).mean() * 100
    if "hh_total_disposable_income" in grp.columns:
        row["median_hh_income"] = grp["hh_total_disposable_income"].median()
    detail_rows.append(row)

detail = pd.DataFrame(detail_rows).set_index(["wave", "max_panel_length"])
print("\n  Demographic & income snapshot by (wave, max_panel_length):")
print(detail.round(1).to_string())

# Collapse to wave level for drift flagging (mean_age weighted by n)
wave_rows = []
for wave, grp in snapshot.groupby("wave", observed=True):
    row2: dict = {"wave": wave}
    if "sex" in grp.columns:
        row2["pct_female"] = (grp["sex"] == 2).mean() * 100
    if "age" in grp.columns and wave not in CATEGORICAL_AGE_WAVES:
        row2["mean_age"] = grp["age"].mean()
    if "urban_rural" in grp.columns:
        row2["pct_urban"] = (grp["urban_rural"] == 1).mean() * 100
    wave_rows.append(row2)

wave_summary = pd.DataFrame(wave_rows).set_index("wave")

DRIFT_THRESHOLDS = {"pct_female": 2.0, "mean_age": 1.0, "pct_urban": 3.0}
drift_flags = []
for i in range(1, len(wave_order)):
    w0, w1 = wave_order[i - 1], wave_order[i]
    for metric, thr in DRIFT_THRESHOLDS.items():
        if metric not in wave_summary.columns:
            continue
        if w0 not in wave_summary.index or w1 not in wave_summary.index:
            continue
        v0, v1 = wave_summary.loc[w0, metric], wave_summary.loc[w1, metric]
        if pd.notna(v0) and pd.notna(v1) and abs(v1 - v0) > thr:
            drift_flags.append(f"  FLAG  {metric}: {w0}→{w1}: {v1 - v0:+.2f}")

if drift_flags:
    print()
    for f in drift_flags:
        print(f)
else:
    print("\n  PASSED  no demographic drift above thresholds (wave-level aggregates)")


# ── 6. Weight Smoothness (soon) ─────────────────────
