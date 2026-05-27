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
