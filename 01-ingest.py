
import pandas as pd

# One entry per 4-year rolling panel wave released by TÜİK.
# Tuple fields: (label, folder, unused, sep)
# The separator changed across releases: early waves used ";" , later ones ",".
PANELS = [
    ("06070809", "raw-data/GYKA_Panel_2006-2009/Data_CSV/",             None, ","),
    ("08091011", "raw-data/GYKA_Panel_2008-2011/turkce/downloads",      None, ","),
    ("10111213", "raw-data/GYKA_Panel_2010-2013/downloads",             None, ";"),
    ("12131415", "raw-data/GYKA_Panel_2012-2015/downloads",             None, ";"),
    ("14151617", "raw-data/GYKA_Panel_2014-2017/turkce",                None, ";"),
    ("15161718", "raw-data/GYKA_Panel_2015-2018/turkce",                None, ";"),
    ("16171819", "raw-data/GYKA_Panel_2016-2019/Turkce",                None, ","),
    ("17181920", "raw-data/GYKA_Panel_2017-2020/veri_seti/csv",         None, ","),
    ("18192021", "raw-data/GYKA_Panel_2018-2021",                       None, ","),
    ("19202122", "raw-data/GYKA_Panel_2019-2022/csv",                   None, ","),
    ("20212223", "raw-data/GYKA_Panel_2020-2023/TURKÇE/csv",            None, ","),
    ("21222324", "raw-data/GYKA_Panel_2021-2024/csv_TURKÇE",            None, ","),
]


def load_panel(label: str, folder: str, sep: str) -> dict[str, pd.DataFrame]:
    # The 2008-2011 wave uses uppercase GYK; all others use lowercase gyk.
    prefix = "GYK" if label == "08091011" else "gyk"
    # f  = individual (fert) file
    # fk = individual characteristics (fert kayit)
    # h  = household (hane) file
    # hk = household characteristics (hane kayit)
    return {
        "f":  pd.read_csv(f"{folder}/{prefix}{label}_f.csv",  sep=sep, dtype=str),
        "fk": pd.read_csv(f"{folder}/{prefix}{label}_fk.csv", sep=sep, dtype=str),
        "h":  pd.read_csv(f"{folder}/{prefix}{label}_h.csv",  sep=sep, dtype=str),
        "hk": pd.read_csv(f"{folder}/{prefix}{label}_hk.csv", sep=sep, dtype=str),
    }


# Load all waves; result is {label: {"f": df, "fk": df, "h": df, "hk": df}}
panels = {label: load_panel(label, folder, sep) for label, folder, _, sep in PANELS}


