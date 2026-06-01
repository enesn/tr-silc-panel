"""
05-deploy.py
Runs the full ingest/join/clean pipeline, saves the result directly to
the publication folder (no interim/ output):

  /silc0624.parquet    — data with embedded column metadata
  /manifest.yaml       — dataset / provenance / quality manifest
"""


from pandas import read_parquet
import datetime
import hashlib
import importlib.metadata as _ilm
import io
import json
import platform
import subprocess

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import yaml

from config import DEPLOY_DIR, VERSION, PREV_VERSION, CODEBOOK_PATH


# ── 1. Run pipeline ──────────────────────────────────────────────────────────

exec(open("01-ingest.py").read())  # → PANELS, _DTYPE_MAP, load_panel, panels
exec(open("02-join.py").read())    # → silc0624 (joined)
exec(open("03-clean.py").read())   # → silc0624 (dtypes cast, columns renamed, dup flag)
exec(open("04-validation.py").read())   # → validation checks (not used directly below but good to run before deployment)

NOW = datetime.datetime.utcnow()
NOW_ISO = NOW.isoformat() + "Z"
DATE_STR = NOW.strftime("%Y-%m-%d")


# ── 2. Helpers ────────────────────────────────────────────────────────────────

def _git(cmd: str) -> str:
    try:
        return subprocess.check_output(
            ["git"] + cmd.split(), stderr=subprocess.DEVNULL
        ).decode().strip()
    except Exception:
        return "unknown"


def _pkg(name: str) -> str:
    try:
        return _ilm.version(name)
    except Exception:
        return "unknown"


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    try:
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()
    except FileNotFoundError:
        return "file-not-found"


def _s(val) -> str | None:
    """Coerce cell to stripped string; return None for NaN/empty."""
    try:
        if pd.isna(val):
            return None
    except (TypeError, ValueError):
        pass
    s = str(val).strip()
    return s or None


def _parse_vl(raw) -> dict | None:
    """'1 = Male | 2 = Female' → {'1': 'Male', '2': 'Female'}"""
    if not isinstance(raw, str) or "=" not in raw:
        return None
    out = {}
    for part in raw.split("|"):
        if "=" in part:
            k, _, v = part.partition("=")
            try:
                out[str(int(k.strip()))] = v.strip()
            except ValueError:
                pass
    return out or None


# ── 3. Load codebook for parquet field annotations ────────────────────────────

print("loading codebook...")
VAR_SHEET = pd.read_excel(
    CODEBOOK_PATH, sheet_name="Variable labels by wave"
)

# variable_name → {source_code, label, topic, value_labels}
var_meta: dict[str, dict] = {}
for _, row in VAR_SHEET.iterrows():
    vname = _s(row.get("Variable name"))
    if not vname:
        continue
    var_meta[vname] = {
        "source_code":  _s(row.get("Variable code")),
        "label":        _s(row.get("Variable label (EN)")),
        "topic":        _s(row.get("Topic")),
        "value_labels": _parse_vl(row.get("Value labels — current scheme (EN, last wave)")),
    }

# source_code → variable_name (reverse lookup for unrenamed columns)
code_to_name: dict[str, str] = {
    v["source_code"]: k for k, v in var_meta.items() if v.get("source_code")
}


# ── 4. Save parquet with embedded metadata ────────────────────────────────────

print("converting to Arrow + embedding metadata...")
tbl = pa.Table.from_pandas(silc0624, preserve_index=False)

# Field-level: attach compact codebook JSON to each column
new_fields = []
for field in tbl.schema:
    col = field.name
    meta = var_meta.get(col) or var_meta.get(code_to_name.get(col, ""), {})
    payload: dict = {}
    for key in ("label", "topic", "source_code", "value_labels"):
        if meta.get(key):
            payload[key] = meta[key]
    if payload:
        field = field.with_metadata(
            {b"codebook": json.dumps(payload, ensure_ascii=False).encode()}
        )
    new_fields.append(field)

git_hash_long = _git("rev-parse HEAD")
file_meta_raw = {
    "dataset":          "Turkish SILC (GYKA) Longitudinal Panel",
    "source_org":       "TUIK",
    "waves":            " | ".join(label for label, *_ in PANELS),
    "created_at":       NOW_ISO,
    "git_commit":       git_hash_long,
    "codebook_ref":     f"/{CODEBOOK_PATH.name}",
    "manifest_sidecar": "/manifest.yaml",
}
existing_meta = tbl.schema.metadata or {}
merged_meta = {
    **existing_meta,
    **{k.encode(): v.encode() for k, v in file_meta_raw.items()},
}
new_schema = pa.schema(new_fields, metadata=merged_meta)
tbl_ann = pa.Table.from_batches(tbl.to_batches(), schema=new_schema)
_parquet_buf = io.BytesIO()
pq.write_table(tbl_ann, _parquet_buf, compression="snappy")
parquet_bytes = _parquet_buf.getvalue()
print(f"  buffered silc0624.parquet in memory  "
      f"({len(silc0624):,} rows × {len(silc0624.columns)} cols)")



# ── 5. Quality stats ──────────────────────────────────────────────────────────

print("computing quality stats...")
KEY_COLS = ["wave", "max_panel_length", "survey_year", "individual_id"]
null_stats = {col: int(silc0624[col].isna().sum()) for col in KEY_COLS}

dup_mask = silc0624.duplicated(subset=KEY_COLS, keep=False)
n_dup_rows = int(dup_mask.sum())
n_dup_ids = int(silc0624.loc[dup_mask, "individual_id"].nunique()) if n_dup_rows else 0

wave_range_fails: list[str] = []
for label, grp in silc0624.groupby("wave", observed=True):
    lo, hi = 2000 + int(label[:2]), 2000 + int(label[6:])
    n_bad = int((~grp["survey_year"].between(lo, hi)).sum())
    if n_bad:
        wave_range_fails.append(f"{label}: {n_bad} rows outside [{lo}, {hi}]")

# §2c — reconcile against published TÜİK sample sizes
_PUBLISHED = {
    "19202122": {4: 19_669, 3: 40_040, 2: 61_313},
    "20212223": {4: 18_478, 3: 37_402, 2: 57_705},
    "21222324": {4: 17_839, 3: 36_680, 2: 56_612},
}
_uniq = (
    silc0624
    .groupby(["wave", "max_panel_length"], observed=True)["individual_id"]
    .nunique()
    .unstack("max_panel_length")
)
_uniq.columns = [f"len={int(c)}" if pd.notna(c) else "len=NA" for c in _uniq.columns]
_uniq["total"] = _uniq.sum(axis=1)

pub_mismatches: list[str] = []
for _wave, _pub in _PUBLISHED.items():
    _wc = _uniq.loc[_wave]
    _obs = {
        4: int(_wc.get("len=4", 0)),
        3: int(_wc.get("len=3", 0) + _wc.get("len=4", 0)),
        2: int(_wc["total"]),
    }
    for _pl, _expected in _pub.items():
        _got = _obs[_pl]
        if _got != _expected:
            pub_mismatches.append(
                f"{_wave} pl={_pl}: got {_got:,}, expected {_expected:,} "
                f"(delta {_got - _expected:+,})"
            )

# §5b — panel composition drift
_CATEGORICAL_AGE_WAVES = {"06070809"}
_snapshot = silc0624[
    silc0624["survey_year"]
    == silc0624.groupby("wave", observed=True)["survey_year"].transform("max")
]
_wave_order = (
    silc0624["wave"].cat.categories.tolist()
    if hasattr(silc0624["wave"], "cat")
    else sorted(silc0624["wave"].unique())
)
_wave_rows = []
for _w, _grp in _snapshot.groupby("wave", observed=True):
    _r: dict = {"wave": _w}
    if "sex" in _grp.columns:
        _r["pct_female"] = (_grp["sex"] == 2).mean() * 100
    if "age" in _grp.columns and _w not in _CATEGORICAL_AGE_WAVES:
        _r["mean_age"] = _grp["age"].mean()
    if "urban_rural" in _grp.columns:
        _r["pct_urban"] = (_grp["urban_rural"] == 1).mean() * 100
    _wave_rows.append(_r)
_wave_summary = pd.DataFrame(_wave_rows).set_index("wave")

_DRIFT_THR = {"pct_female": 2.0, "mean_age": 1.0, "pct_urban": 3.0}
drift_flags: list[str] = []
for _i in range(1, len(_wave_order)):
    _w0, _w1 = _wave_order[_i - 1], _wave_order[_i]
    for _metric, _thr in _DRIFT_THR.items():
        if _metric not in _wave_summary.columns:
            continue
        if _w0 not in _wave_summary.index or _w1 not in _wave_summary.index:
            continue
        _v0, _v1 = _wave_summary.loc[_w0, _metric], _wave_summary.loc[_w1, _metric]
        if pd.notna(_v0) and pd.notna(_v1) and abs(_v1 - _v0) > _thr:
            drift_flags.append(f"{_metric}: {_w0}→{_w1}: {_v1 - _v0:+.2f}")


# ── 6. Hash raw source files ──────────────────────────────────────────────────

print("hashing raw source files (this may take a moment)...")
raw_sources = []
for label, folder, _, sep in PANELS:
    prefix = "GYK" if label == "08091011" else "gyk"
    file_hashes = {}
    for key in ("f", "fk", "h", "hk"):
        path = f"{folder}/{prefix}{label}_{key}.csv"
        file_hashes[f"{prefix}{label}_{key}.csv"] = _sha256(path)
    raw_sources.append({
        "name": f"GYKA_Panel_{label}",
        "folder": folder,
        "separator": sep,
        "files_sha256": file_hashes,
    })


# ── 7. Write interim/manifest.yaml ───────────────────────────────────────────

print("writing /manifest.yaml...")

git_branch = _git("rev-parse --abbrev-ref HEAD")
git_short = _git("rev-parse --short HEAD")
output_sha = hashlib.sha256(parquet_bytes).hexdigest()

WAVE_LIST = [
    f"{label} ({2000+int(label[:2])}–{2000+int(label[6:])})"
    for label, *_ in PANELS
]

manifest = {
    "dataset": {
        "name": "tr-silc-panel",
        "version": VERSION,
        "previous_version": PREV_VERSION,
        "release_date": DATE_STR,
        "created_by": "enesn",
    },

    "provenance": {
        "raw_sources": raw_sources,
        "pipeline": {
            "repo": "github.com/enesn/tr-silc-panel",
            "branch": git_branch,
            "commit": git_hash_long,
            "output_sha256": output_sha,
            "entry_point": "05-deploy.py",
            "scripts_executed": [
                "01-ingest.py", "02-join.py", "03-clean.py", "05-deploy.py"
            ],
            "runtime": {
                "Python": platform.python_version(),
                "packages": {
                    "pandas":   _pkg("pandas"),
                    "pyarrow":  _pkg("pyarrow"),
                    "openpyxl": _pkg("openpyxl"),
                    "PyYAML":   _pkg("PyYAML"),
                },
            },
            "environment": {
                "image": "enesn/python3.12-slim:v1",
                "run_args": "--memory=32g --memory-swap=32g",
            },
        },
    },

    "schema": {
        "codebook_ref":        f"/{CODEBOOK_PATH.name}",
        "n_rows":              int(len(silc0624)),
        "n_cols":              int(len(silc0624.columns)),
        "unit_of_observation": "Individual × survey_year (person-year)",
        "panel_waves":         WAVE_LIST,
        "key_variables": {
            "wave":             "4-year panel wave label (e.g. '21222324')",
            "max_panel_length": "Longest balanced panel the individual belongs to (2/3/4 — exclusive)",
            "survey_year":      "Calendar year of the interview",
            "individual_id":    "Individual identifier (FKIMLIK)",
        },
        "weight_variables": {
            "panel_weight_2y": "FK060_2 — 2-wave balanced panel expansion weight",
            "panel_weight_3y": "FK060_3 — 3-wave balanced panel expansion weight",
            "panel_weight_4y": "FK060_4 — 4-wave balanced panel expansion weight",
        },
        "derived_variables": {
            "max_panel_length": "Exclusive: 4 if in FK060_4; 3 if FK060_3 but not FK060_4; 2 if FK060_2 only",
            "is_duplicate":     "True if individual_id appears in multiple households in the same wave-year",
        },
    },

    "changelog": [
        {
            "type": "initial",
            "description": (
                "Initial pooled release — 12 GYKA waves (2006–2024) joined, cleaned, "
                "column-renamed from TÜİK source codes, and validated."
            ),
            "variables_affected": "all",
            "rationale": "First version of the harmonised longitudinal dataset.",
        }
    ],

    "quality": {
        "completeness": {
            col: ("OK (0 nulls)" if v == 0 else f"FLAG — {v:,} nulls")
            for col, v in null_stats.items()
        },
        "known_issues": {
            "hk_phantom_rows": (
                "RIGHT JOIN on hk introduces ~3,917 rows with null individual_id "
                "(hk-only households). Exclude where individual_id IS NULL for any "
                "person-level analysis."
            ),
            "age_coding_06070809": (
                "FK070 was coded as age groups (1–14) not completed years in wave "
                "06070809. Do not compute mean age for this wave."
            ),
        },
        "validation": {
            "within_wave_range": (
                "passed"
                if not wave_range_fails
                else f"FAILED — {'; '.join(wave_range_fails)}"
            ),
            "individual_duplicates": (
                f"{n_dup_rows:,} duplicate rows across {n_dup_ids:,} individual_ids "
                "(expected: same individual in multiple households)"
            ),
            "sample_size_against_published_numbers": (
                "passed — 19202122, 20212223, 21222324 all match TÜİK published figures"
                if not pub_mismatches
                else "FAILED — " + "; ".join(pub_mismatches)
            ),
            "null_key_identifiers": (
                "passed"
                if all(v == 0 for v in null_stats.values())
                else (
                    "FLAG — " +
                    ", ".join(f"{col}: {v}" for col, v in null_stats.items() if v)
                )
            ),
            "panel_composition_drift": (
                "passed — no wave-to-wave shifts above thresholds "
                "(pct_female >2pp, mean_age >1yr, pct_urban >3pp)"
                if not drift_flags
                else "FLAG — " + "; ".join(drift_flags)
            ),
        },
    },
}

manifest_bytes = yaml.dump(
    manifest, allow_unicode=True, sort_keys=False, default_flow_style=False
).encode("utf-8")

# ── 8. Write to Dropbox folder ───────────────────────────────────────────────

print(f"writing to {DEPLOY_DIR}...")
DEPLOY_DIR.mkdir(parents=True, exist_ok=True)
(DEPLOY_DIR / "silc0624.parquet").write_bytes(parquet_bytes)
print(f"  wrote silc0624.parquet  ({len(parquet_bytes):,} bytes)")
(DEPLOY_DIR / "manifest.yaml").write_bytes(manifest_bytes)
print(f"  wrote manifest.yaml  ({len(manifest_bytes):,} bytes)")
_cb_src = CODEBOOK_PATH
_cb_dst = DEPLOY_DIR / _cb_src.name
_cb_dst.write_bytes(_cb_src.read_bytes())
print(f"  wrote {_cb_src.name}  ({_cb_dst.stat().st_size:,} bytes)")

# ── 9. Smoke-test ────────────────────────────────────────────────────────────

del parquet_bytes, manifest_bytes

_parquet_path = DEPLOY_DIR / "silc0624.parquet"
_pf = pq.ParquetFile(_parquet_path)

print("\nsmoke-test — schema:")
print(_pf.schema_arrow)

print("\nsmoke-test — file-level metadata:")
for k, v in (_pf.schema_arrow.metadata or {}).items():
    if not k.startswith(b"pandas"):
        try:
            v_display = json.dumps(json.loads(v), ensure_ascii=False)
        except (json.JSONDecodeError, UnicodeDecodeError):
            v_display = v.decode(errors="replace")
        print(f"  {k.decode()}: {v_display}")

