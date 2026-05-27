
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

# Codebook-informed dtype map (original variable codes → pandas dtype).
# Format notation x.y: x = integer digits, y = decimal places.
# Sources: "Length / format (last wave)" and "Type" columns in codebook.
# Applied per-file during ingest so each small DataFrame is cast before joining.
_DTYPE_MAP: dict = {
    # --- identifiers (kept as string — some older waves use space-formatted IDs) ---
    # HKIMLIK, FKIMLIK, FK220, FK230, FK240 stay as str (default from dtype=str)

    # survey year appears under four codes across files; all become FB010 after join
    "FB010":   pd.Int16Dtype(),
    "FK010":   pd.Int16Dtype(),
    "HB010":   pd.Int16Dtype(),
    "HK010":   pd.Int16Dtype(),

    # --- panel weights ---
    "FK060":   pd.Float64Dtype(), # panel weight              (format 4.7)
    "FK060_2": pd.Float64Dtype(), # 2-year panel weight
    "FK060_3": pd.Float64Dtype(), # 3-year panel weight
    "FK060_4": pd.Float64Dtype(), # 4-year panel weight
    "FK250":   pd.Float32Dtype(), # OECD equivalent weight    (values: 0.3 / 0.5 / 1)

    # --- panel tracking & individual characteristics ---
    "ALTORN":  pd.Int8Dtype(),    # sub_sample                (format 1.0, values 5-22)
    "HK110":   pd.Int8Dtype(),    # household_status          (format 2.0, max 11)
    "HK120":   pd.Int8Dtype(),    # address_status            (format 2.0, values 11/21/22/23)
    "HK130":   pd.Int8Dtype(),    # interview_status          (format 2.0, max 24)
    "FK070":   pd.Int8Dtype(),    # age                       (format 2.0, 0–110)
    "FK075":   pd.Int8Dtype(),    # birth_month               (1–12)
    "FK080":   pd.Int16Dtype(),   # birth_year                (format 4.0)
    "FK090":   pd.Int8Dtype(),    # sex                       (1/2)
    "FK095":   pd.Int8Dtype(),    # relationship_to_ref       (1–11)
    "FK100":   pd.Int8Dtype(),    # sample_person             (1/2)
    "FK110":   pd.Int8Dtype(),    # membership_status         (1–8)
    "FK120":   pd.Int8Dtype(),    # leaver_destination        (1–4)
    "FK140":   pd.Int8Dtype(),    # leave_month               (1–12)
    "FK150":   pd.Int16Dtype(),   # leave_year                (format 4.0)
    "FK160":   pd.Int8Dtype(),    # months_in_hh_leaver       (1–12)
    "FK170":   pd.Int8Dtype(),    # leaver_activity           (1–4)
    "FK180":   pd.Int8Dtype(),    # join_month                (1–12)
    "FK190":   pd.Int16Dtype(),   # join_year                 (format 4.0)
    "FK210":   pd.Int8Dtype(),    # activity_in_ref_period    (1–4)

    # --- household characteristics ---
    "HB020":   pd.Int8Dtype(),    # urban_rural               (1-digit)
    "HB050":   pd.Int8Dtype(),    # household_type            (max 23)

    # --- dwelling & amenities ---
    "HH010":   pd.Int8Dtype(),    # hh_dwelling_type          (1–5)
    "HH020":   pd.Int8Dtype(),    # hh_tenure_status          (1–4)
    "HH030":   pd.Int16Dtype(),   # hh_year_acquired          (4-digit year)
    "HH040":   pd.Float64Dtype(), # hh_monthly_rent           (format 6.0, float in some waves)
    "HH050":   pd.Float64Dtype(), # hh_monthly_housing_cost   (format 6.0, float in some waves)
    "HH060":   pd.Int8Dtype(),    # hh_number_of_rooms        (1–10)
    "HH070":   pd.Int16Dtype(),   # hh_floor_area_m2          (format 3.0)
    "HH080":   pd.Int8Dtype(),    # hh_heating_system         (1–5)
    "HH090":   pd.Int8Dtype(),    # hh_heating_fuel           (1–8)
    "HH100":   pd.Int8Dtype(),    # hh_has_bath_shower        (1–3)
    "HH110":   pd.Int8Dtype(),    # hh_has_indoor_toilet      (1–3)
    "HH120":   pd.Int8Dtype(),    # hh_has_kitchen            (1/2)
    "HH130":   pd.Int8Dtype(),    # hh_has_piped_water        (1/2)
    "HH140":   pd.Int8Dtype(),    # hh_has_hot_water          (1/2)
    "HH150":   pd.Int8Dtype(),    # hh_has_landline           (1–3)
    "HH160":   pd.Int8Dtype(),    # hh_has_mobile_phone       (1–3)
    "HH170":   pd.Int8Dtype(),    # hh_has_colour_tv          (1–3)
    "HH180":   pd.Int8Dtype(),    # hh_has_computer           (1–3)
    "HH190":   pd.Int8Dtype(),    # hh_has_internet           (1–3)
    "HH200":   pd.Int8Dtype(),    # hh_has_washing_machine    (1–3)
    "HH210":   pd.Int8Dtype(),    # hh_has_refrigerator       (1–3)
    "HH220":   pd.Int8Dtype(),    # hh_has_dishwasher         (1–3)
    "HH230":   pd.Int8Dtype(),    # hh_has_air_conditioner    (1–3)
    "HH240":   pd.Int8Dtype(),    # hh_has_car                (1–3)
    "HS010":   pd.Int8Dtype(),    # damp_leak_problems        (1/2)
    "HS020":   pd.Int8Dtype(),    # insulation_problems       (1/2)

    # --- economic situation / deprivation ---
    "HE010":   pd.Int8Dtype(),    # hh_arrears_housing_loan   (1–4)
    "HE020":   pd.Int8Dtype(),    # hh_arrears_utilities      (1–4)
    "HE030":   pd.Int8Dtype(),    # hh_arrears_other_debt     (1–4)
    "HE040":   pd.Int8Dtype(),    # hh_make_ends_meet         (1–6)
    "HE050":   pd.Float64Dtype(), # hh_min_income_needed      (format 7.0, float in some waves)
    "HE060":   pd.Int8Dtype(),    # hh_housing_cost_burden    (1–3)
    "HE070":   pd.Int8Dtype(),    # hh_debt_burden            (1–4)
    "HE080":   pd.Int8Dtype(),    # hh_afford_holiday         (1/2)
    "HE090":   pd.Int8Dtype(),    # hh_afford_protein_meal    (1/2)
    "HE100":   pd.Int8Dtype(),    # hh_unexpected_expenses    (1/2)
    "HE110":   pd.Int8Dtype(),    # hh_keep_home_warm         (1/2)
    "HE120":   pd.Int8Dtype(),    # hh_replace_furniture      (1–3)
    "HE130":   pd.Int8Dtype(),    # hh_afford_new_clothes_hh  (1/2)

    # --- household income (format 9.2 → Float64 for precision in aggregation) ---
    "HG010":   pd.Float64Dtype(), "HG020":   pd.Float64Dtype(),
    "HG030A":  pd.Float64Dtype(), "HG030N":  pd.Float64Dtype(),
    "HG040":   pd.Float64Dtype(), "HG050A":  pd.Float64Dtype(),
    "HG050N":  pd.Float64Dtype(), "HG060A":  pd.Float64Dtype(),
    "HG060N":  pd.Float64Dtype(), "HG065":   pd.Float64Dtype(),
    "HG065N":  pd.Float64Dtype(), "HG070":   pd.Float64Dtype(),
    "HG080":   pd.Float64Dtype(), "HG085":   pd.Float64Dtype(),
    "HG090A":  pd.Float64Dtype(), "HG090N":  pd.Float64Dtype(),
    "HG095":   pd.Float64Dtype(), "HG095N":  pd.Float64Dtype(),
    "HG100":   pd.Float64Dtype(), "HG103":   pd.Float64Dtype(),
    "HG105":   pd.Float64Dtype(), "HG110":   pd.Float64Dtype(),
    "HG120":   pd.Float64Dtype(), "HG130":   pd.Float64Dtype(),

    # --- demographics ---
    "FB100":   pd.Int8Dtype(),    # marital_status            (1–5)
    "FB110":   pd.Int8Dtype(),    # legally_married           (1–3)

    # --- education ---
    "FE030":   pd.Int8Dtype(),    # education_level           (0–6)

    # --- individual income (format 9.2 → Float64) ---
    "FG010":   pd.Float64Dtype(), "FG020":   pd.Float64Dtype(),
    "FG030":   pd.Float64Dtype(), "FG040":   pd.Float64Dtype(),
    "FG070":   pd.Float64Dtype(), "FG080":   pd.Float64Dtype(),
    "FG085":   pd.Float64Dtype(), "FG090":   pd.Float64Dtype(),
    "FG100":   pd.Float64Dtype(), "FG110":   pd.Float64Dtype(),
    "FG120":   pd.Float64Dtype(), "FG125":   pd.Float64Dtype(),
    "FG130":   pd.Float64Dtype(), "FG140":   pd.Float64Dtype(),

    # --- employment status ---
    "FI010":   pd.Int8Dtype(),    # self_def_activity         (1–10)
    "FI020":   pd.Int8Dtype(),    # worked_last_week          (1/2)
    "FI030":   pd.Int8Dtype(),    # ever_worked               (1/2)
    "FI040":   pd.Int8Dtype(),    # job_search_4wk            (1/2)
    "FI050":   pd.Int8Dtype(),    # available_2wk             (1/2)

    # --- last job ---
    "FI070":   pd.Int8Dtype(),    # last_job_status           (1–5)
    "FI080":   pd.Int8Dtype(),    # last_job_isco             (1–9)
    "FI085":   pd.Int8Dtype(),    # last_job_permanence       (1–4)
    "FI100":   pd.Int8Dtype(),    # last_job_months           (1–12)
    "FI110":   pd.Float64Dtype(), # last_job_income           (format 6.0)

    # --- main job ---
    "FI120":   pd.Int8Dtype(),    # main_job_status           (1–5)
    "FI130":   pd.Int8Dtype(),    # main_job_isco             (1–9)
    "FI140":   pd.Int8Dtype(),    # main_job_nace             (2-digit, 1–18+)
    "FI145":   pd.Int8Dtype(),    # (extra column, values 1/2)
    "FI150":   pd.Int8Dtype(),    # main_job_hours            (max ~84, fits Int8)
    "FI180":   pd.Int8Dtype(),    # main_job_firm_size        (1–6)
    "FI190":   pd.Int8Dtype(),    # main_job_ssc_registered   (1/2)
    "FI210":   pd.Int8Dtype(),    # main_job_permanence       (1–4)
    "FI240":   pd.Int8Dtype(),    # main_job_months           (0–12)
    "FI250":   pd.Float64Dtype(), # main_job_annual_income    (format 6.0)
    "FI255":   pd.Int8Dtype(),    # changed_job               (1/2)
    "FI256":   pd.Int8Dtype(),    # job_change_reason         (1–7)

    # --- work history / activity calendar ---
    "FI320":   pd.Int8Dtype(),    # age_at_first_job          (format 2.0)
    "FI330":   pd.Int8Dtype(),    # years_worked              (format 2.0, max ~50)
    "FI340A":  pd.Int8Dtype(),    "FI340B":  pd.Int8Dtype(),
    "FI340C":  pd.Int8Dtype(),    "FI340D":  pd.Int8Dtype(),
    "FI340E":  pd.Int8Dtype(),    "FI340F":  pd.Int8Dtype(),
    "FI340G":  pd.Int8Dtype(),    "FI340H":  pd.Int8Dtype(),
    "FI340I":  pd.Int8Dtype(),    "FI340J":  pd.Int8Dtype(),
    "FI340K":  pd.Int8Dtype(),    "FI340L":  pd.Int8Dtype(),

    # --- material deprivation / health ---
    "FM010":   pd.Int8Dtype(),    # afford_new_clothes        (1–3)
    "FS010":   pd.Int8Dtype(),    # self_rated_health         (1–5)
    "FS020":   pd.Int8Dtype(),    # chronic_illness           (1/2)
    "FS030":   pd.Int8Dtype(),    # activity_limitation       (1–3)
}


def _apply_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    for col, dtype in _DTYPE_MAP.items():
        if col in df.columns:
            df[col] = df[col].astype(dtype)
    return df


def load_panel(label: str, folder: str, sep: str) -> dict[str, pd.DataFrame]:
    # The 2008-2011 wave uses uppercase GYK; all others use lowercase gyk.
    prefix = "GYK" if label == "08091011" else "gyk"
    # f  = individual (fert) file
    # fk = individual characteristics (fert kayit)
    # h  = household (hane) file
    # hk = household characteristics (hane kayit)
    return {
        key: _apply_dtypes(pd.read_csv(f"{folder}/{prefix}{label}_{key}.csv", sep=sep, dtype=str, na_values=["."]))
        for key in ("f", "fk", "h", "hk")
    }


# Load all waves; result is {label: {"f": df, "fk": df, "h": df, "hk": df}}
panels = {label: load_panel(label, folder, sep) for label, folder, _, sep in PANELS}
