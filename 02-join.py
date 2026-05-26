import pandas as pd


# Left joins to combine the four files for each wave into one DataFrame per wave.
def join_panel(dfs: dict[str, pd.DataFrame]) -> pd.DataFrame:
    f  = dfs["f"]
    fk = dfs["fk"].rename(columns={"FK010": "FB010"})
    h  = dfs["h"].rename(columns={"HB010": "FB010"})
    hk = dfs["hk"].rename(columns={"HK010": "FB010"})

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
            how="right"
        )
)

frames = []
for label, dfs in panels.items():
    print(f"joining {label}...")
    df = join_panel(dfs)
    df["wave"] = label
    # max_panel_length: longest sub-panel the individual belongs to in this wave.
    # Based on which FK060_* weight is non-null in the final-year record.
    df["max_panel_length"] = (
        df["FK060_4"].notna().map({True: 4, False: None})
        .fillna(df["FK060_3"].notna().map({True: 3, False: None}))
        .fillna(df["FK060_2"].notna().map({True: 2, False: None}))
    )
    frames.append(df)
    print(f"  {label}: {len(df)} rows, {len(df.columns)} cols")
    del df, dfs
    panels[label] = None  # release raw DataFrames immediately

# Report columns that differ across waves before concatenating.

silc0624 = pd.concat(frames, ignore_index=True)

silc0624["max_panel_length"] = (
    silc0624.groupby(["wave", "FKIMLIK"])["max_panel_length"]
            .transform(lambda x: x.ffill().bfill())
)

