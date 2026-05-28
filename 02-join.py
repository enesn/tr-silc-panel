import pandas as pd


# Left joins to combine the four files for each wave into one DataFrame per wave.
def join_panel(dfs: dict[str, pd.DataFrame]) -> pd.DataFrame:
    f  = dfs["f"]
    fk = dfs["fk"].rename(columns={"FK010": "FB010"})
    h  = dfs["h"].rename(columns={"HB010": "FB010"})
    hk = dfs["hk"].rename(columns={"HK010": "FB010"})

    # fk is the authoritative individual roster; f/h/hk are joined in
    # where available. RIGHT JOIN fk keeps panel-tracked individuals even
    # if they have no survey record in f (e.g. attrition year). LEFT JOIN
    # hk avoids phantom rows from the ~3,900 hk-only households that carry
    # no individuals.
    return (
        f.merge(
            fk,
            on=["FKIMLIK", "HKIMLIK", "FB010"],
            how="right"
        )
        .merge(
            h,
            on=["HKIMLIK", "FB010"],
            how="left"
        )
        .merge(
            hk,
            on=["HKIMLIK", "FB010"],
            how="left"
        )
)

print(f"joining {len(panels)} waves...")
frames = []
for label, dfs in panels.items():
    df = join_panel(dfs)
    df["wave"] = label
    df["max_panel_length"] = (
        df["FK060_4"].notna().map({True: 4, False: None})
        .fillna(df["FK060_3"].notna().map({True: 3, False: None}))
        .fillna(df["FK060_2"].notna().map({True: 2, False: None}))
    )
    frames.append(df)
    print(f"  {label}: {len(df):,} rows, {len(df.columns)} cols")
    del df, dfs
    panels[label] = None

silc0624 = pd.concat(frames, ignore_index=True)
print(f"concatenated: {len(silc0624):,} rows total")

print("computing max_panel_length per individual...")
silc0624["max_panel_length"] = (
    silc0624.groupby(["wave", "FKIMLIK"], sort=False, observed=True)
            ["max_panel_length"]
            .transform("max")
)
print("done.")
