
import pandas as pd


print("casting dtypes...")
silc0624["max_panel_length"] = silc0624["max_panel_length"].astype(pd.Int8Dtype())
silc0624["wave"] = silc0624["wave"].astype("category")

print("reading codebook and renaming columns...")
codebook = pd.read_excel(
    "metadata/codebook-202605.xlsx",
    sheet_name="Value labels by wave",
    usecols=["Variable code", "Variable name"],
).dropna(subset=["Variable code"]).drop_duplicates(subset="Variable code")

code_to_snake: dict[str, str] = dict(
    zip(codebook["Variable code"], codebook["Variable name"])
)

silc0624 = silc0624.rename(columns=code_to_snake)
print(f"  renamed {len(code_to_snake)} columns")

print("flagging duplicate individuals...")
_key_cols = ["wave", "max_panel_length", "survey_year", "individual_id"]
_dup_ids = silc0624.loc[
    silc0624.duplicated(subset=_key_cols, keep=False), "individual_id"
].unique()
silc0624["is_duplicate"] = silc0624["individual_id"].isin(_dup_ids)
print(f"  {len(_dup_ids):,} individuals flagged as duplicates")
print("done.")

