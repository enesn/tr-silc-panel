# tr-silc-panel

Harmonised longitudinal panel dataset built from 12 rolling waves of the Turkish Statistics Institute (TÜİK) Income and Living Conditions Survey (**GYKA / SILC**), covering survey years 2006–2024. 

**Current release:** `tr-silc-panel202605`  
**Produced by:** `05-deploy.py`  
**Output artefacts:** `silc0624.parquet` · `manifest.yaml` 

---

## Getting started

The `raw-data/` folder is **not distributed** with this repository — it contains proprietary TÜİK microdata that cannot be shared publicly. You must obtain the raw panel files directly from TÜİK and place them in the expected folder structure before running anything.

**Steps:**

1. **Obtain the raw data.** Download the GYKA panel releases from TÜİK. Each wave ships as four CSV files (`_f`, `_fk`, `_h`, `_hk`).

2. **Place files under `raw-data/`.** Match the folder paths listed in the [Panel waves](#panel-waves) table below — for example:
   ```
   raw-data/GYKA_Panel_2021-2024/csv_TURKÇE/gyk21222324_f.csv
   raw-data/GYKA_Panel_2021-2024/csv_TURKÇE/gyk21222324_fk.csv
   ...
   ```
   The exact subfolder names are defined in `01-ingest.py` (`PANELS` list).

3. **Edit `config.py`** to set your output directory and version:
   ```python
   DEPLOY_DIR    = Path("/your/output/path")
   VERSION       = "tr-silc-panel202606"
   CODEBOOK_PATH = Path("metadata/codebook-202605.xlsx")
   ```

4. **Run the pipeline:**
   ```bash
   python 05-deploy.py
   ```

---

## What this is

TÜİK releases GYKA as overlapping 4-year rotating panels. This pipeline ingests all 12 panel waves, joins the four per-wave files (individual survey `f`, panel tracking `fk`, household `h`, household panel `hk`), harmonises variable names from raw TÜİK codes to English snake-case labels, and writes a single Parquet file with codebook metadata embedded directly in the column schema.

The result is a person-year file: one row per individual per survey year, with a `wave` column identifying the 4-year panel the row belongs to.

---

## Output files

### `silc0624.parquet`

| Property | Value |
|---|---|
| Unit of observation | Individual × survey year (person-year) |
| Compression | Snappy |
| Column metadata | Codebook JSON per field (label, topic, source code, value labels) |
| File metadata | Dataset name, source org, waves, git commit, codebook ref, manifest ref |

Column-level metadata is embedded in the Arrow schema under the `codebook` key as a compact JSON object with up to four fields:

```json
{
  "label": "Sex",
  "topic": "Demographics",
  "source_code": "FK090",
  "value_labels": {"1": "Male", "2": "Female"}
}
```


### `manifest.yaml`

Machine-readable provenance sidecar. Sections:

- **`dataset`** — name, version, release date, author
- **`provenance`** — raw source files with SHA-256 hashes, pipeline repo/branch/commit, runtime environment
- **`schema`** — row count, column count, unit of observation, panel waves, key/weight/derived variable descriptions
- **`changelog`** — per-release change log
- **`quality`** — null counts, known issues, validation results

### `codebook-202605.xlsx`

TÜİK codebook manually edited alongside the parquet. Two sheets are consumed by the pipeline:

| Sheet | Used for |
|---|---|
| `Variable labels by wave` | Column metadata embedded in the Parquet schema |
| `Value labels by wave` | Column rename map (source code → English snake-case name) |

---

## Key variables

| Variable | Type | Description |
|---|---|---|
| `wave` | category | 4-year panel label, e.g. `"21222324"` (2021–2024) |
| `max_panel_length` | Int8 | Longest balanced panel the individual belongs to — **exclusive**: 4 if in FK060_4; 3 if FK060_3 only; 2 if FK060_2 only |
| `survey_year` | Int16 | Calendar year of the interview |
| `individual_id` | str | Individual identifier (FKIMLIK) |
| `is_duplicate` | bool | True if `individual_id` appears in more than one household in the same wave-year |

### Panel weights

| Variable | Description |
|---|---|
| `panel_weight_2y` | FK060_2 — 2-wave balanced panel expansion weight |
| `panel_weight_3y` | FK060_3 — 3-wave balanced panel expansion weight |
| `panel_weight_4y` | FK060_4 — 4-wave balanced panel expansion weight |

---

## Panel waves

| Wave label | Survey years | Files |
|---|---|---|
| `06070809` | 2006–2009 | `gyk06070809_{f,fk,h,hk}.csv` |
| `08091011` | 2008–2011 | `GYK08091011_{f,fk,h,hk}.csv` |
| `10111213` | 2010–2013 | `gyk10111213_{f,fk,h,hk}.csv` |
| `12131415` | 2012–2015 | `gyk12131415_{f,fk,h,hk}.csv` |
| `14151617` | 2014–2017 | `gyk14151617_{f,fk,h,hk}.csv` |
| `15161718` | 2015–2018 | `gyk15161718_{f,fk,h,hk}.csv` |
| `16171819` | 2016–2019 | `gyk16171819_{f,fk,h,hk}.csv` |
| `17181920` | 2017–2020 | `gyk17181920_{f,fk,h,hk}.csv` |
| `18192021` | 2018–2021 | `gyk18192021_{f,fk,h,hk}.csv` |
| `19202122` | 2019–2022 | `gyk19202122_{f,fk,h,hk}.csv` |
| `20212223` | 2020–2023 | `gyk20212223_{f,fk,h,hk}.csv` |
| `21222324` | 2021–2024 | `gyk21222324_{f,fk,h,hk}.csv` |

---

## Known issues

**`hk_phantom_rows`** — The RIGHT JOIN on `hk` introduces ~3,917 rows where `individual_id` is null (hk-only households that carry no tracked individuals). Filter `WHERE individual_id IS NOT NULL` for any person-level analysis.

**`age_coding_06070809`** — `FK070` was coded as age groups (1–14) rather than completed years in wave `06070809`. Do not compute mean age for this wave.

---

## Validation

`04-validation.py` runs these checks before each deploy:

| Check | Method |
|---|---|
| Survey year within wave range | Each row's `survey_year` must fall in `[2000+label[:2], 2000+label[6:]]` |
| Individual counts vs raw `fk` | `nunique(individual_id)` per (wave, year) must match the raw fk CSV |
| Sample sizes vs published TÜİK figures | 19202122, 20212223, 21222324 reconciled against official release notes |
| Null key identifiers | Zero nulls in `wave`, `max_panel_length`, `survey_year`, `individual_id` |
| Panel composition drift | Wave-to-wave shifts flagged if `pct_female > 2pp`, `mean_age > 1yr`, or `pct_urban > 3pp` |

---

## Pipeline

```
01-ingest.py   — load each wave's four CSVs; apply codebook-informed dtypes
02-join.py     — RIGHT JOIN fk → merge f, h, hk; derive max_panel_length
03-clean.py    — cast final dtypes; rename columns from TÜİK codes; flag duplicates
04-validation.py — run quality checks (recommended before deploy)
05-deploy.py   — embed codebook metadata in Arrow schema; write parquet + manifest
```

Run with:

```bash
python 05-deploy.py
```

Requires Python 3.12, `pandas`, `pyarrow`, `openpyxl`, `PyYAML`. Raw source CSVs must be present under `raw-data/`. Output is written to `DEPLOY_DIR` (default: `/mnt/dropbox-out`), configurable in [config.py](config.py).

---

## Repo

`github.com/enesn/tr-silc-panel` — maintained by [@enesn](https://github.com/enesn)
