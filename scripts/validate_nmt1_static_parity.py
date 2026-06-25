#!/usr/bin/env python3
"""Static parity audit for N-M-T1 versus exAL-M-T1.

This validator intentionally performs no launches, no monitoring, and no
sensitivity experiments.  It inspects the current manuscript-facing provenance,
the frozen run-local input bundles, and the resolved configuration files.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path("/data/muscat_data/jaguir26/project1_ucsc_phd")
ARTICLE_ROOT = REPO_ROOT / "Evironmetrics---REVISED-DOC-Corrected-2"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "reports" / "nmt1_static_parity_audit_20260625"
BENCHMARK_CSV = ARTICLE_ROOT / "tables" / "generated_tex" / "benchmark_crps_horizon_summary.csv"
RETAINED_EXDQLM_ROOT = Path(
    "/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/"
    "multimodel_v8_he2_exdqlm_multivar_keep_authoritative_rdata_retention_current_20260623/runs"
)
CUTOFFS = ["20210123", "20211112", "20211221", "20220511", "20221225"]
CANONICAL_HARMONICS = [1.0, 2.0, 1.0 / 6.8068493]
NUMERIC_FORMAT_TOLERANCE = 1e-12

INPUT_ARTIFACTS = [
    ("parameters", "inputs/shared/parameters/parameters.txt"),
    ("retros", "inputs/shared/retros/retros.csv"),
    ("usgs_daily", "inputs/shared/usgs/usgs_daily.csv"),
    ("nws_forecast", "inputs/shared/forecasts/nws_forecast.csv"),
    ("glofas_forecast", "inputs/shared/forecasts/glofas_forecast.csv"),
    ("cov_01_PPT", "inputs/shared/covariates/cov_01_PPT.csv"),
    ("cov_02_SOIL", "inputs/shared/covariates/cov_02_SOIL.csv"),
    ("cov_03_PCA", "inputs/shared/covariates/cov_03_PCA.csv"),
    ("covariate_features", "inputs/shared/covariates/covariate_features.csv"),
    (
        "deterministic_precip_future",
        "inputs/shared/deterministic_climate/deterministic_precip_future.csv",
    ),
    (
        "deterministic_soil_future",
        "inputs/shared/deterministic_climate/deterministic_soil_future.csv",
    ),
]

SOURCE_MAP = [
    {
        "contract_area": "fit dispatch",
        "file": "R/unified/stages/stage_fit.R",
        "line_refs": "2091-2225",
        "claim": (
            "NDLM main uses run-scoped shared inputs and passes transfer mode, "
            "discounts, harmonics, Kalman backend, and forecast IW prior through "
            "environment variables."
        ),
    },
    {
        "contract_area": "NDLM runner",
        "file": "scripts/run_ndlm_main.R",
        "line_refs": "7-53",
        "claim": (
            "The theory-aligned runner sources only the NDLM family modules and "
            "calls unified_run_ndlm_main_theory."
        ),
    },
    {
        "contract_area": "input loader",
        "file": "R/unified/families/ndlm_main/01_inputs.R",
        "line_refs": "64-183",
        "claim": (
            "NDLM reads retros, forecast products, and engineered covariate "
            "features from shared run-local inputs on the log1p internal scale."
        ),
    },
    {
        "contract_area": "state registry",
        "file": "R/unified/families/ndlm_main/07_state_registry.R",
        "line_refs": "26-242",
        "claim": (
            "The multivariate keep state contains shared theta, retained transfer "
            "block, and source discrepancy blocks, with ragged forecast lead "
            "state dimensions derived from active NWS/GloFAS sources."
        ),
    },
    {
        "contract_area": "Gaussian/Kalman fit",
        "file": "R/unified/families/ndlm_main/08_vb_cavi_exact.R",
        "line_refs": "73-155",
        "claim": (
            "Historical updates are Gaussian sequential Kalman updates with no "
            "exAL s_t/u_t/gamma layer."
        ),
    },
    {
        "contract_area": "forecast IW anchor",
        "file": "R/unified/families/ndlm_main/08_vb_cavi_exact.R",
        "line_refs": "157-220",
        "claim": (
            "Forecast covariance priors are anchored to the terminal historical "
            "discount recursion through epsilon/c_factor-style IW settings."
        ),
    },
]

STATE_SPACE_ROWS = [
    {
        "block": "theta",
        "meaning": "shared latent river state: level/trend plus seasonal harmonics",
        "historical_presence": "yes",
        "forecast_keep_presence": "yes",
        "dimension_rule": "q = 1 + 2 * number_of_harmonics",
        "loading": "F_base",
    },
    {
        "block": "transfer",
        "meaning": "retained transfer block: intercept zeta plus engineered covariate effects psi",
        "historical_presence": "yes",
        "forecast_keep_presence": "yes in keep mode",
        "dimension_rule": "1 + number_of_engineered_covariates",
        "loading": "1 on zeta in observation; transfer evolves with covariate row",
    },
    {
        "block": "delta_glofas",
        "meaning": "GloFAS discrepancy state relative to shared USGS location",
        "historical_presence": "yes",
        "forecast_keep_presence": "only active forecast leads with GloFAS",
        "dimension_rule": "q",
        "loading": "F_base added to USGS loading for GloFAS observation",
    },
    {
        "block": "delta_nws",
        "meaning": "NWS discrepancy state relative to shared USGS location",
        "historical_presence": "yes",
        "forecast_keep_presence": "only active forecast leads with NWS",
        "dimension_rule": "q",
        "loading": "F_base added to USGS loading for NWS observation",
    },
]

NOT_COMPARABLE_FIELDS = [
    ("quantile_lanes", "NDLM is one Gaussian model; exDQLM is quantile-indexed."),
    ("s_t", "NDLM has no exAL latent s_t update."),
    ("u_t", "NDLM has no exAL latent u_t/v_t update."),
    ("gamma", "NDLM has no exAL asymmetry gamma parameter."),
    ("sigma_gamma_laplace", "NDLM does not use the exAL sigma/gamma approximation."),
    ("cross_quantile_synthesis", "NDLM table row is not built from quantile-lane synthesis internals."),
]


@dataclass(frozen=True)
class CsvProfile:
    rows: int
    cols: int
    header: list[str]
    min_date: str
    max_date: str
    numeric_columns: int
    active_rows: int


def read_csv_dicts(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(rows: list[dict[str, Any]], path: Path, fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        keys: list[str] = []
        for row in rows:
            for key in row:
                if key not in keys:
                    keys.append(key)
        fieldnames = keys
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_json(obj: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open() as handle:
        loaded = yaml.safe_load(handle)
    return loaded if isinstance(loaded, dict) else {}


def nested_get(obj: Any, keys: list[str], default: Any = "") -> Any:
    cur = obj
    for key in keys:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


def scalar_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return f"{value:.15g}"
    if isinstance(value, list):
        return "|".join(scalar_text(x) for x in value)
    if isinstance(value, dict):
        return json.dumps(value, sort_keys=True)
    return str(value)


def normalize_transfer_covariates(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {
        "base_covariates": list(value.get("base_covariates", []) or []),
        "engineered_terms": list(value.get("engineered_terms", []) or []),
    }


def normalized_config_value(field_name: str, value: Any) -> str:
    if field_name == "inputs.transfer_function_covariates":
        return scalar_text(normalize_transfer_covariates(value))
    return scalar_text(value)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_float(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if text == "" or text.lower() in {"na", "nan", "null", "none"}:
        return None
    try:
        out = float(text)
    except ValueError:
        return None
    return out if math.isfinite(out) else None


def is_date_like_column(name: str) -> bool:
    lname = name.lower()
    return "date" in lname or lname in {"time", "timestamp"}


def csv_profile(path: Path) -> CsvProfile:
    rows = read_csv_dicts(path)
    header: list[str] = []
    with path.open(newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader, [])

    date_cols = [col for col in header if is_date_like_column(col)]
    dates: list[str] = []
    if date_cols:
        col = date_cols[0]
        dates = [row.get(col, "") for row in rows if row.get(col, "")]

    numeric_cols = 0
    active_rows = 0
    for col in header:
        if is_date_like_column(col):
            continue
        vals = [parse_float(row.get(col, "")) for row in rows]
        finite = [x for x in vals if x is not None]
        if finite:
            numeric_cols += 1
    for row in rows:
        has_num = False
        for col in header:
            if is_date_like_column(col):
                continue
            if parse_float(row.get(col, "")) is not None:
                has_num = True
                break
        if has_num:
            active_rows += 1

    return CsvProfile(
        rows=len(rows),
        cols=len(header),
        header=header,
        min_date=min(dates) if dates else "",
        max_date=max(dates) if dates else "",
        numeric_columns=numeric_cols,
        active_rows=active_rows,
    )


def compare_csv_numeric_equivalence(path_a: Path, path_b: Path, tol: float = NUMERIC_FORMAT_TOLERANCE) -> dict[str, Any]:
    rows_a = read_csv_dicts(path_a)
    rows_b = read_csv_dicts(path_b)
    prof_a = csv_profile(path_a)
    prof_b = csv_profile(path_b)
    text_diff_rows = 0
    non_numeric_diff_rows = 0
    max_abs = 0.0
    max_rel = 0.0
    compared_numeric = 0
    common_header = [col for col in prof_a.header if col in prof_b.header]

    for row_a, row_b in zip(rows_a, rows_b):
        if row_a != row_b:
            text_diff_rows += 1
        non_numeric_diff_this_row = False
        for col in common_header:
            aval = row_a.get(col, "")
            bval = row_b.get(col, "")
            af = parse_float(aval)
            bf = parse_float(bval)
            if af is not None and bf is not None:
                compared_numeric += 1
                diff = abs(af - bf)
                max_abs = max(max_abs, diff)
                denom = max(abs(af), abs(bf), 1e-300)
                max_rel = max(max_rel, diff / denom)
            elif aval != bval:
                non_numeric_diff_this_row = True
        if non_numeric_diff_this_row:
            non_numeric_diff_rows += 1

    numeric_equivalent = (
        prof_a.rows == prof_b.rows
        and prof_a.header == prof_b.header
        and prof_a.min_date == prof_b.min_date
        and prof_a.max_date == prof_b.max_date
        and non_numeric_diff_rows == 0
        and max_abs <= tol
    )
    return {
        "rows_a": prof_a.rows,
        "rows_b": prof_b.rows,
        "cols_a": prof_a.cols,
        "cols_b": prof_b.cols,
        "header_equal": prof_a.header == prof_b.header,
        "min_date_a": prof_a.min_date,
        "min_date_b": prof_b.min_date,
        "max_date_a": prof_a.max_date,
        "max_date_b": prof_b.max_date,
        "text_diff_rows": text_diff_rows,
        "non_numeric_diff_rows": non_numeric_diff_rows,
        "compared_numeric_cells": compared_numeric,
        "max_abs_numeric_diff": max_abs,
        "max_rel_numeric_diff": max_rel,
        "numeric_equivalent": numeric_equivalent,
    }


def classify_input_pair(
    path_a: Path,
    path_b: Path,
    tol: float = NUMERIC_FORMAT_TOLERANCE,
) -> tuple[str, dict[str, Any]]:
    if not path_a.exists() or not path_b.exists():
        return "fail_missing", {}
    hash_a = sha256_file(path_a)
    hash_b = sha256_file(path_b)
    if hash_a == hash_b:
        prof_a = csv_profile(path_a) if path_a.suffix.lower() == ".csv" else None
        return "pass_exact", {
            "sha256_a": hash_a,
            "sha256_b": hash_b,
            "rows_a": prof_a.rows if prof_a else "",
            "rows_b": prof_a.rows if prof_a else "",
            "cols_a": prof_a.cols if prof_a else "",
            "cols_b": prof_a.cols if prof_a else "",
            "header_equal": "true" if prof_a else "",
            "max_abs_numeric_diff": 0.0,
            "max_rel_numeric_diff": 0.0,
            "text_diff_rows": 0,
            "non_numeric_diff_rows": 0,
        }
    if path_a.suffix.lower() != ".csv" or path_b.suffix.lower() != ".csv":
        return "fail_hash", {"sha256_a": hash_a, "sha256_b": hash_b}
    cmp = compare_csv_numeric_equivalence(path_a, path_b, tol=tol)
    status = "pass_numeric_equivalent" if cmp["numeric_equivalent"] else "fail_numeric_or_schema"
    cmp["sha256_a"] = hash_a
    cmp["sha256_b"] = hash_b
    return status, cmp


def run_root_from_score_path(source_path: str | Path, article_root: Path = ARTICLE_ROOT) -> Path:
    path = Path(source_path)
    if not path.is_absolute():
        path = article_root / path
    # Expected shape: run/post/outputs/<run-id>/tables/crps_forecast_per_time.csv
    if len(path.parents) >= 5 and path.name.endswith(".csv"):
        return path.parents[4]
    return path.parent


def first_output_root(run_root: Path) -> Path:
    outputs = sorted((run_root / "post" / "outputs").glob("*"))
    return outputs[0] if outputs else run_root / "post" / "outputs"


def find_retained_exdqlm_run(cutoff: str, retained_root: Path = RETAINED_EXDQLM_ROOT) -> Path | None:
    matches = sorted(
        retained_root.glob(
            f"multimodel_{cutoff}_*_exdqlm_multivar_keep_authoritative_rdata_retained_current_20260623"
        )
    )
    return matches[0] if matches else None


def benchmark_rows(benchmark_csv: Path) -> list[dict[str, str]]:
    return [
        row
        for row in read_csv_dicts(benchmark_csv)
        if row.get("table_label") == "tab:benchmark_crps_models"
        and row.get("row_label") in {"N-M-T1", "exAL-M-T1"}
    ]


def build_authority_rows(benchmark_csv: Path = BENCHMARK_CSV, article_root: Path = ARTICLE_ROOT) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in benchmark_rows(benchmark_csv):
        source_path = row["source_path"]
        run_root = run_root_from_score_path(source_path, article_root=article_root)
        rows.append(
            {
                "authority_class": "article_crps_table",
                "cutoff": row["cutoff"],
                "row_label": row["row_label"],
                "source_class": row["source_class"],
                "mean_crps": row["mean_crps"],
                "source_path": source_path,
                "run_root": str(run_root),
                "output_root": str(first_output_root(run_root)),
                "resolved_config": str(run_root / "resolved_config.yaml"),
                "run_manifest": str(run_root / "run_manifest.yaml"),
                "model_selector": row["model_selector"],
                "horizon_days": row["horizon_days"],
                "run_id": run_root.name,
                "exists_run_root": run_root.exists(),
                "exists_resolved_config": (run_root / "resolved_config.yaml").exists(),
            }
        )
    for cutoff in CUTOFFS:
        run_root = find_retained_exdqlm_run(cutoff)
        if run_root is None:
            rows.append(
                {
                    "authority_class": "current_retained_exdqlm_figures",
                    "cutoff": cutoff,
                    "row_label": "exAL-M-T1-retained-current",
                    "source_class": "exdqlm_multivar_keep",
                    "mean_crps": "",
                    "source_path": "",
                    "run_root": "",
                    "output_root": "",
                    "resolved_config": "",
                    "run_manifest": "",
                    "model_selector": "retained_current",
                    "horizon_days": "28",
                    "run_id": "",
                    "exists_run_root": False,
                    "exists_resolved_config": False,
                }
            )
            continue
        rows.append(
            {
                "authority_class": "current_retained_exdqlm_figures",
                "cutoff": cutoff,
                "row_label": "exAL-M-T1-retained-current",
                "source_class": "exdqlm_multivar_keep",
                "mean_crps": "",
                "source_path": "",
                "run_root": str(run_root),
                "output_root": str(first_output_root(run_root)),
                "resolved_config": str(run_root / "resolved_config.yaml"),
                "run_manifest": str(run_root / "run_manifest.yaml"),
                "model_selector": "retained_current",
                "horizon_days": "28",
                "run_id": run_root.name,
                "exists_run_root": run_root.exists(),
                "exists_resolved_config": (run_root / "resolved_config.yaml").exists(),
            }
        )
    return sorted(rows, key=lambda r: (r["cutoff"], r["row_label"], r["authority_class"]))


def authority_lookup(rows: list[dict[str, Any]]) -> dict[tuple[str, str, str], dict[str, Any]]:
    return {(r["cutoff"], r["row_label"], r["authority_class"]): r for r in rows}


def artifact_path(run_root: str | Path, rel_path: str) -> Path:
    return Path(run_root) / rel_path


def build_input_inventory(authority_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in authority_rows:
        run_root = Path(row["run_root"]) if row["run_root"] else Path("")
        for artifact, rel_path in INPUT_ARTIFACTS:
            path = run_root / rel_path if row["run_root"] else Path("")
            prof: CsvProfile | None = None
            if path.exists() and path.suffix.lower() == ".csv":
                prof = csv_profile(path)
            out.append(
                {
                    "authority_class": row["authority_class"],
                    "cutoff": row["cutoff"],
                    "row_label": row["row_label"],
                    "artifact": artifact,
                    "relative_path": rel_path,
                    "path": str(path) if row["run_root"] else "",
                    "exists": path.exists() if row["run_root"] else False,
                    "sha256": sha256_file(path) if path.exists() and path.is_file() else "",
                    "size_bytes": path.stat().st_size if path.exists() and path.is_file() else "",
                    "rows": prof.rows if prof else "",
                    "cols": prof.cols if prof else "",
                    "min_date": prof.min_date if prof else "",
                    "max_date": prof.max_date if prof else "",
                    "numeric_columns": prof.numeric_columns if prof else "",
                    "active_rows": prof.active_rows if prof else "",
                }
            )
    return out


def build_input_comparisons(
    authority_rows: list[dict[str, Any]],
    tol: float = NUMERIC_FORMAT_TOLERANCE,
) -> list[dict[str, Any]]:
    lookup = authority_lookup(authority_rows)
    out: list[dict[str, Any]] = []
    for cutoff in CUTOFFS:
        base = lookup.get((cutoff, "N-M-T1", "article_crps_table"))
        targets = [
            lookup.get((cutoff, "exAL-M-T1", "article_crps_table")),
            lookup.get((cutoff, "exAL-M-T1-retained-current", "current_retained_exdqlm_figures")),
        ]
        for target in [t for t in targets if t]:
            for artifact, rel_path in INPUT_ARTIFACTS:
                path_a = artifact_path(base["run_root"], rel_path) if base and base["run_root"] else Path("")
                path_b = artifact_path(target["run_root"], rel_path) if target["run_root"] else Path("")
                status, details = classify_input_pair(path_a, path_b, tol=tol)
                out.append(
                    {
                        "cutoff": cutoff,
                        "left_label": "N-M-T1",
                        "right_label": target["row_label"],
                        "right_authority_class": target["authority_class"],
                        "artifact": artifact,
                        "relative_path": rel_path,
                        "status": status,
                        "path_left": str(path_a),
                        "path_right": str(path_b),
                        "sha256_left": details.get("sha256_a", ""),
                        "sha256_right": details.get("sha256_b", ""),
                        "rows_left": details.get("rows_a", ""),
                        "rows_right": details.get("rows_b", ""),
                        "cols_left": details.get("cols_a", ""),
                        "cols_right": details.get("cols_b", ""),
                        "header_equal": details.get("header_equal", ""),
                        "text_diff_rows": details.get("text_diff_rows", ""),
                        "non_numeric_diff_rows": details.get("non_numeric_diff_rows", ""),
                        "max_abs_numeric_diff": details.get("max_abs_numeric_diff", ""),
                        "max_rel_numeric_diff": details.get("max_rel_numeric_diff", ""),
                    }
                )
    return out


def normalize_harmonics_from_config(config: dict[str, Any], family_key: str) -> list[float]:
    family = nested_get(config, ["models", family_key], default={})
    if not isinstance(family, dict):
        return []
    harmonics = nested_get(family, ["seasonality", "harmonics"], default=None)
    if harmonics not in (None, ""):
        return [float(x) for x in harmonics]
    indices = nested_get(family, ["structure", "enabled_harmonic_indices"], default=None)
    if indices in (None, ""):
        return []
    out: list[float] = []
    for item in indices:
        idx = int(item)
        if idx < 1 or idx > len(CANONICAL_HARMONICS):
            raise ValueError(f"enabled harmonic index {idx} outside canonical vector")
        out.append(CANONICAL_HARMONICS[idx - 1])
    return out


def harmonics_equal(left: list[float], right: list[float], tol: float = 1e-12) -> bool:
    return len(left) == len(right) and all(abs(a - b) <= tol for a, b in zip(left, right))


def config_field_rows(authority_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    fields = [
        ("site.usgs_site", ["site", "usgs_site"], "hard"),
        ("dates.cutoff_date", ["dates", "cutoff_date"], "hard"),
        ("dates.data_start", ["dates", "data_start"], "hard"),
        ("scale_contract.internal_scale", ["scale_contract", "internal_scale"], "hard"),
        ("fit.retros_storage_scale", ["inputs", "fit", "retros_storage_scale"], "hard"),
        ("fit.nws_storage_scale", ["inputs", "fit", "nws_storage_scale"], "hard"),
        ("fit.glofas_storage_scale", ["inputs", "fit", "glofas_storage_scale"], "hard"),
        ("forecast_transfer_mode", ["__family__", "forecast_transfer_mode"], "semantic"),
        ("implementation_mode", ["__family__", "implementation_mode"], "documented_difference"),
        ("likelihood_mode", ["__family__", "likelihood_mode"], "documented_difference"),
        ("kalman_backend", ["__family__", "kalman_backend"], "documented_difference"),
        ("state.df_t", ["__family__", "state_evolution", "df_t"], "documented_difference"),
        ("state.df_s1", ["__family__", "state_evolution", "df_s1"], "documented_difference"),
        ("state.df_s2", ["__family__", "state_evolution", "df_s2"], "documented_difference"),
        ("state.df_s67", ["__family__", "state_evolution", "df_s67"], "documented_difference"),
        ("state.df_discrep", ["__family__", "state_evolution", "df_discrep"], "documented_difference"),
        ("state.lambda", ["__family__", "state_evolution", "lambda"], "documented_difference"),
        ("state.df_trans", ["__family__", "state_evolution", "df_trans"], "documented_difference"),
        ("state.df_covs", ["__family__", "state_evolution", "df_covs"], "documented_difference"),
        ("prior.forecast_cov.c_factor", ["__family__", "prior", "forecast_cov", "c_factor"], "documented_difference"),
        ("prior.forecast_cov.epsilon", ["__family__", "prior", "forecast_cov", "epsilon"], "documented_difference"),
        ("inputs.shared_covariates", ["inputs", "shared_covariates"], "semantic"),
        (
            "inputs.transfer_function_covariates",
            ["inputs", "transfer_function_covariates"],
            "semantic",
        ),
        ("inputs.covariate_features", ["inputs", "covariate_features"], "semantic"),
    ]
    out: list[dict[str, Any]] = []
    for row in authority_rows:
        if not row["resolved_config"] or not Path(row["resolved_config"]).exists():
            continue
        config = load_yaml(Path(row["resolved_config"]))
        family_key = "ndlm_main" if row["source_class"] == "ndlm_main_keep" else "exdqlm_multivar"
        family = nested_get(config, ["models", family_key], default={})
        for field_name, keys, parity_class in fields:
            source_obj = config
            actual_keys = keys
            if keys and keys[0] == "__family__":
                source_obj = family
                actual_keys = keys[1:]
            out.append(
                {
                    "cutoff": row["cutoff"],
                    "row_label": row["row_label"],
                    "authority_class": row["authority_class"],
                    "source_class": row["source_class"],
                    "field": field_name,
                    "parity_class": parity_class,
                    "value": normalized_config_value(
                        field_name,
                        nested_get(source_obj, actual_keys, default=""),
                    ),
                }
            )
        out.append(
            {
                "cutoff": row["cutoff"],
                "row_label": row["row_label"],
                "authority_class": row["authority_class"],
                "source_class": row["source_class"],
                "field": "normalized_harmonics",
                "parity_class": "semantic",
                "value": scalar_text([f"{x:.15g}" for x in normalize_harmonics_from_config(config, family_key)]),
            }
        )
        out.append(
            {
                "cutoff": row["cutoff"],
                "row_label": row["row_label"],
                "authority_class": row["authority_class"],
                "source_class": row["source_class"],
                "field": "trend_included",
                "parity_class": "semantic",
                "value": scalar_text(
                    True
                    if family_key == "ndlm_main"
                    else nested_get(family, ["structure", "include_trend"], default="")
                ),
            }
        )
    return out


def compare_specs(field_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key: dict[tuple[str, str, str, str], str] = {}
    class_by_field: dict[str, str] = {}
    for row in field_rows:
        by_key[(row["cutoff"], row["row_label"], row["authority_class"], row["field"])] = row["value"]
        class_by_field[row["field"]] = row["parity_class"]
    out: list[dict[str, Any]] = []
    for cutoff in CUTOFFS:
        for target_label, authority in [
            ("exAL-M-T1", "article_crps_table"),
            ("exAL-M-T1-retained-current", "current_retained_exdqlm_figures"),
        ]:
            fields = sorted(class_by_field)
            for field in fields:
                left = by_key.get((cutoff, "N-M-T1", "article_crps_table", field), "")
                right = by_key.get((cutoff, target_label, authority, field), "")
                parity_class = class_by_field[field]
                equal = left == right
                if field == "normalized_harmonics":
                    l_vals = [float(x) for x in left.split("|") if x]
                    r_vals = [float(x) for x in right.split("|") if x]
                    equal = harmonics_equal(l_vals, r_vals)
                if parity_class == "hard":
                    status = "pass" if equal else "fail_hard"
                elif parity_class == "semantic":
                    status = "pass" if equal else "fail_semantic"
                elif parity_class == "documented_difference":
                    status = "documented_difference" if not equal else "same"
                else:
                    status = "not_comparable"
                out.append(
                    {
                        "cutoff": cutoff,
                        "left_label": "N-M-T1",
                        "right_label": target_label,
                        "right_authority_class": authority,
                        "field": field,
                        "parity_class": parity_class,
                        "left_value": left,
                        "right_value": right,
                        "status": status,
                    }
                )
    return out


def build_harmonic_rows(authority_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in authority_rows:
        if not row["resolved_config"] or not Path(row["resolved_config"]).exists():
            continue
        family_key = "ndlm_main" if row["source_class"] == "ndlm_main_keep" else "exdqlm_multivar"
        config = load_yaml(Path(row["resolved_config"]))
        family = nested_get(config, ["models", family_key], default={})
        indices = nested_get(family, ["structure", "enabled_harmonic_indices"], default="")
        raw_harmonics = nested_get(family, ["seasonality", "harmonics"], default="")
        normalized = normalize_harmonics_from_config(config, family_key)
        out.append(
            {
                "cutoff": row["cutoff"],
                "row_label": row["row_label"],
                "authority_class": row["authority_class"],
                "family_key": family_key,
                "raw_harmonics": scalar_text(raw_harmonics),
                "enabled_harmonic_indices": scalar_text(indices),
                "canonical_vector": scalar_text([f"{x:.15g}" for x in CANONICAL_HARMONICS]),
                "normalized_harmonics": scalar_text([f"{x:.15g}" for x in normalized]),
                "note": (
                    "indices map to canonical vector"
                    if indices not in ("", None)
                    else "actual harmonic values stored"
                ),
            }
        )
    return out


def build_covariate_forecast_contract(authority_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in authority_rows:
        run_root = row["run_root"]
        if not run_root:
            continue
        for artifact in ["covariate_features", "nws_forecast", "glofas_forecast"]:
            rel = dict(INPUT_ARTIFACTS)[artifact]
            path = Path(run_root) / rel
            if path.exists() and path.suffix.lower() == ".csv":
                prof = csv_profile(path)
                out.append(
                    {
                        "cutoff": row["cutoff"],
                        "row_label": row["row_label"],
                        "authority_class": row["authority_class"],
                        "artifact": artifact,
                        "path": str(path),
                        "sha256": sha256_file(path),
                        "rows": prof.rows,
                        "cols": prof.cols,
                        "min_date": prof.min_date,
                        "max_date": prof.max_date,
                        "numeric_columns": prof.numeric_columns,
                        "active_rows": prof.active_rows,
                        "header": "|".join(prof.header),
                    }
                )
    return out


def parse_selector(selector: str) -> tuple[str, str]:
    if "=" not in selector:
        return "", ""
    key, value = selector.split("=", 1)
    return key.strip(), value.strip()


def recompute_crps_mean(source_path: str, article_root: Path, selector: str, horizon_days: str) -> float | None:
    path = Path(source_path)
    if not path.is_absolute():
        path = article_root / path
    if not path.exists():
        return None
    key, expected = parse_selector(selector)
    horizon = int(float(horizon_days))
    vals: list[float] = []
    for row in read_csv_dicts(path):
        lead = parse_float(row.get("lead_day", ""))
        if lead is None or lead > horizon:
            continue
        if key and expected and row.get(key) != expected:
            continue
        val = parse_float(row.get("crps", ""))
        if val is not None:
            vals.append(val)
    if not vals:
        return None
    return sum(vals) / len(vals)


def build_article_table_checks(
    authority_rows: list[dict[str, Any]],
    article_root: Path = ARTICLE_ROOT,
    tol: float = 1e-10,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in authority_rows:
        if row["authority_class"] != "article_crps_table":
            continue
        recomputed = recompute_crps_mean(
            row["source_path"],
            article_root=article_root,
            selector=row["model_selector"],
            horizon_days=row["horizon_days"],
        )
        recorded = parse_float(row["mean_crps"])
        diff = None if recorded is None or recomputed is None else abs(recorded - recomputed)
        out.append(
            {
                "cutoff": row["cutoff"],
                "row_label": row["row_label"],
                "source_class": row["source_class"],
                "source_path": row["source_path"],
                "model_selector": row["model_selector"],
                "horizon_days": row["horizon_days"],
                "recorded_mean_crps": row["mean_crps"],
                "recomputed_mean_crps": "" if recomputed is None else f"{recomputed:.17g}",
                "abs_diff": "" if diff is None else f"{diff:.17g}",
                "status": "pass" if diff is not None and diff <= tol else "fail",
            }
        )
    return out


def build_source_map_rows() -> list[dict[str, str]]:
    return SOURCE_MAP


def build_state_space_rows() -> list[dict[str, str]]:
    return STATE_SPACE_ROWS


def build_not_comparable_rows() -> list[dict[str, str]]:
    return [{"field": field, "reason": reason} for field, reason in NOT_COMPARABLE_FIELDS]


def count_status(rows: list[dict[str, Any]], key: str = "status") -> dict[str, int]:
    out: dict[str, int] = {}
    for row in rows:
        val = str(row.get(key, ""))
        out[val] = out.get(val, 0) + 1
    return out


def compact_table(rows: list[list[str]]) -> str:
    widths = [max(len(str(row[i])) for row in rows) for i in range(len(rows[0]))]
    out = []
    for idx, row in enumerate(rows):
        out.append("| " + " | ".join(str(v).ljust(widths[i]) for i, v in enumerate(row)) + " |")
        if idx == 0:
            out.append("| " + " | ".join("-" * widths[i] for i in range(len(row))) + " |")
    return "\n".join(out)


def write_markdown_outputs(
    output_dir: Path,
    authority_rows: list[dict[str, Any]],
    input_comparisons: list[dict[str, Any]],
    spec_comparisons: list[dict[str, Any]],
    article_checks: list[dict[str, Any]],
    summary: dict[str, Any],
) -> None:
    authority_table = compact_table(
        [["cutoff", "row", "authority", "run id"]]
        + [
            [r["cutoff"], r["row_label"], r["authority_class"], r["run_id"]]
            for r in authority_rows
            if r["row_label"] in {"N-M-T1", "exAL-M-T1", "exAL-M-T1-retained-current"}
        ]
    )
    input_status = count_status(input_comparisons)
    spec_status = count_status(spec_comparisons)
    table_status = count_status(article_checks)

    pair_summary: dict[tuple[str, str, str], list[str]] = {}
    for row in input_comparisons:
        key = (row["cutoff"], row["right_label"], row["right_authority_class"])
        pair_summary.setdefault(key, []).append(row["status"])
    pair_rows = [["cutoff", "comparison", "authority", "exact", "numeric-eq", "failed"]]
    for key, statuses in sorted(pair_summary.items()):
        exact = statuses.count("pass_exact")
        neq = statuses.count("pass_numeric_equivalent")
        failed = len([s for s in statuses if not s.startswith("pass_")])
        pair_rows.append([key[0], key[1], key[2], str(exact), str(neq), str(failed)])

    lines = [
        "# N-M-T1 Static Parity Audit",
        "",
        "Generated by `scripts/validate_nmt1_static_parity.py`.",
        "",
        "## Scope",
        "",
        "This is a static audit only. It inspects existing manuscript-facing provenance, resolved configuration files, and frozen run-local input bundles. It does not launch, stop, monitor, tune, or promote any model run.",
        "",
        "## Summary",
        "",
        f"- Hard failures: `{summary['hard_failures']}`.",
        f"- Semantic failures: `{summary['semantic_failures']}`.",
        f"- Input status counts: `{input_status}`.",
        f"- Specification status counts: `{spec_status}`.",
        f"- Article table CRPS wiring status counts: `{table_status}`.",
        "",
        "## Authority Rows",
        "",
        authority_table,
        "",
        "## Input-Bundle Pair Summary",
        "",
        compact_table(pair_rows),
        "",
        "Interpretation: `pass_numeric_equivalent` means the file hashes differ but CSV schema/date range match and all numeric differences are within tolerance. This is expected for decimal-format-only copied retrospective files.",
        "",
        "## Specification Interpretation",
        "",
        "- `N-M-T1` is a normal/Gaussian multivariate dynamic linear model; it is not quantile-specific.",
        "- `exAL-M-T1` is an extended asymmetric-Laplace quantile model with quantile lanes and synthesis.",
        "- Transfer mode, harmonics after normalization, and input bundle content are the comparable contract.",
        "- Discount and forecast prior settings are documented differences unless a later manuscript claim requires strict hyperparameter parity.",
        "- `s_t`, `u_t`, `gamma`, sigma/gamma Laplace approximation, and cross-quantile synthesis internals are not comparable for `N-M-T1`.",
        "",
        "## Outputs",
        "",
        "- `authority_rows.csv`",
        "- `input_bundle_inventory.csv`",
        "- `input_bundle_pairwise_comparison.csv`",
        "- `input_bundle_parity_summary.json`",
        "- `spec_field_matrix.csv`",
        "- `spec_pairwise_comparison.csv`",
        "- `spec_noncomparable_fields.csv`",
        "- `harmonic_normalization.csv`",
        "- `covariate_forecast_contract.csv`",
        "- `article_table_wiring_check.csv`",
        "- `ndlm_algorithm_source_map.csv`",
        "- `ndlm_state_space_contract.csv`",
        "",
    ]
    (output_dir / "README.md").write_text("\n".join(lines))

    input_md = [
        "# Input Bundle Parity",
        "",
        compact_table(pair_rows),
        "",
        "Required artifacts are parameters, retros, USGS, NWS, GloFAS, PPT, SOIL, GDPC/PCA, engineered covariate features, and deterministic precipitation/soil futures.",
        "",
    ]
    (output_dir / "input_bundle_parity.md").write_text("\n".join(input_md))

    spec_md = [
        "# Specification Summary",
        "",
        "The validator separates hard equality, semantic equality, documented specification differences, and non-comparable fields.",
        "",
        f"Status counts: `{spec_status}`.",
        "",
        "The key expected documented differences are likelihood family, quantile structure, latent layer, state-evolution discounts, and forecast covariance prior fields.",
        "For transfer-covariate YAML, the validator compares the substantive base covariates and engineered terms; copied decorator fields such as scaling/mode are reported through the frozen feature table profile rather than treated as a semantic mismatch.",
        "",
    ]
    (output_dir / "spec_summary.md").write_text("\n".join(spec_md))

    cov_md = [
        "# Covariate And Forecast Contract",
        "",
        "This table records the static profile of the engineered covariate feature table and NWS/GloFAS forecast products used by the inspected run-local bundles.",
        "",
        "See `covariate_forecast_contract.csv` for hashes, row counts, date ranges, numeric-column counts, and headers.",
        "",
    ]
    (output_dir / "covariate_forecast_contract.md").write_text("\n".join(cov_md))

    article_md = [
        "# Article Table Wiring Check",
        "",
        f"Status counts: `{table_status}`.",
        "",
        "The check recomputes mean CRPS from each manuscript-facing source `crps_forecast_per_time.csv` using the recorded selector and horizon.",
        "",
    ]
    (output_dir / "article_table_wiring_summary.md").write_text("\n".join(article_md))


def run_audit(repo_root: Path, article_root: Path, output_dir: Path, tol: float) -> dict[str, Any]:
    benchmark_csv = article_root / "tables" / "generated_tex" / "benchmark_crps_horizon_summary.csv"
    authority_rows = build_authority_rows(benchmark_csv=benchmark_csv, article_root=article_root)
    input_inventory = build_input_inventory(authority_rows)
    input_comparisons = build_input_comparisons(authority_rows, tol=tol)
    spec_fields = config_field_rows(authority_rows)
    spec_comparisons = compare_specs(spec_fields)
    harmonic_rows = build_harmonic_rows(authority_rows)
    cov_forecast_rows = build_covariate_forecast_contract(authority_rows)
    article_checks = build_article_table_checks(authority_rows, article_root=article_root)
    not_comparable = build_not_comparable_rows()
    source_map = build_source_map_rows()
    state_space = build_state_space_rows()

    hard_failures = sum(
        1
        for row in input_comparisons
        if str(row["status"]).startswith("fail_")
    ) + sum(1 for row in spec_comparisons if row["status"] == "fail_hard") + sum(
        1 for row in article_checks if row["status"] != "pass"
    )
    semantic_failures = sum(1 for row in spec_comparisons if row["status"] == "fail_semantic")
    warnings = sum(1 for row in input_comparisons if row["status"] == "pass_numeric_equivalent")
    summary = {
        "hard_failures": hard_failures,
        "semantic_failures": semantic_failures,
        "numeric_equivalence_warnings": warnings,
        "authority_rows": len(authority_rows),
        "input_comparisons": len(input_comparisons),
        "spec_comparisons": len(spec_comparisons),
        "article_table_checks": len(article_checks),
        "input_status_counts": count_status(input_comparisons),
        "spec_status_counts": count_status(spec_comparisons),
        "article_table_status_counts": count_status(article_checks),
        "repo_root": str(repo_root),
        "article_root": str(article_root),
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(authority_rows, output_dir / "authority_rows.csv")
    write_csv(input_inventory, output_dir / "input_bundle_inventory.csv")
    write_csv(input_comparisons, output_dir / "input_bundle_pairwise_comparison.csv")
    write_json(summary, output_dir / "input_bundle_parity_summary.json")
    write_csv(spec_fields, output_dir / "spec_field_matrix.csv")
    write_csv(spec_comparisons, output_dir / "spec_pairwise_comparison.csv")
    write_csv(not_comparable, output_dir / "spec_noncomparable_fields.csv")
    write_csv(harmonic_rows, output_dir / "harmonic_normalization.csv")
    write_csv(cov_forecast_rows, output_dir / "covariate_forecast_contract.csv")
    write_csv(article_checks, output_dir / "article_table_wiring_check.csv")
    write_csv(source_map, output_dir / "ndlm_algorithm_source_map.csv")
    write_csv(state_space, output_dir / "ndlm_state_space_contract.csv")
    write_markdown_outputs(
        output_dir=output_dir,
        authority_rows=authority_rows,
        input_comparisons=input_comparisons,
        spec_comparisons=spec_comparisons,
        article_checks=article_checks,
        summary=summary,
    )
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--article-root", type=Path, default=ARTICLE_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--numeric-tolerance", type=float, default=NUMERIC_FORMAT_TOLERANCE)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = run_audit(
        repo_root=args.repo_root,
        article_root=args.article_root,
        output_dir=args.output_dir,
        tol=args.numeric_tolerance,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 1 if summary["hard_failures"] or summary["semantic_failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
