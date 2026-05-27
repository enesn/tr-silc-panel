from dask.dataframe import read_parquet
import pandas as pd
import pyarrow.parquet as pq

_ns: dict = {}
exec(open("01-ingest.py").read(), _ns)
exec(open("02-join.py").read(), _ns)

silc0624: pd.DataFrame = _ns["silc0624"]

# Cast the two pipeline-derived columns not present in raw files.
silc0624["max_panel_length"] = silc0624["max_panel_length"].astype(pd.Int8Dtype())
silc0624["wave"] = silc0624["wave"].astype("category")

# Build rename map from codebook (code → snake_name).
codebook = pd.read_excel(
    "metadata/codebook-052026.xlsx",
    sheet_name="Value labels by wave",
    usecols=["Variable code", "Variable name"],
).dropna(subset=["Variable code"]).drop_duplicates(subset="Variable code")

code_to_snake: dict[str, str] = dict(
    zip(codebook["Variable code"], codebook["Variable name"])
)

silc0624 = silc0624.rename(columns=code_to_snake)

