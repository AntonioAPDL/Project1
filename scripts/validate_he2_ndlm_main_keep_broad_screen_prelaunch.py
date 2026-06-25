#!/usr/bin/env python3
"""Prelaunch validation for the HE2 N-M-T1 broad screen."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

DEFAULT_ARTIFACT_ROOT = Path(
    "/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/"
    "multimodel_v8_he2_ndlm_main_keep_broad_screen_20260625"
)
DEFAULT_MATRIX_DIR = DEFAULT_ARTIFACT_ROOT / "control" / "ndlm_main_keep_broad_screen"
EXPECTED_CUTOFFS = {"20210123", "20211112", "20211221", "20220511", "20221225"}
EXPECTED_RUN_ROWS = 1440
EXPECTED_SPECS = 288
EXPECTED_DISCOUNT_CASES = 48
EXPECTED_EPSILONS = {1.0, 30.0, 60.0, 90.0, 180.0, 365.0}
FLOAT_FIELDS = ["df_t", "df_s1", "df_s2", "df_s67", "df_discrep", "lambda", "df_trans", "df_covs"]
TARGET_LANE = "ndlm_main_keep"
DATE_COLUMNS = ["target_date", "date", "Date", "timestamp", "time"]
USGS_FLOW_COLUMNS = ["discharge_cms", "discharge_cfs", "X_00060_00003", "USGS", "usgs", "flow", "data0"]


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return data if isinstance(data, dict) else {}


def nested(cfg: dict[str, Any], path: list[str], default: Any = None) -> Any:
    cur: Any = cfg
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


def same_float(left: Any, right: Any, tol: float = 1e-12) -> bool:
    try:
        return abs(float(left) - float(right)) <= tol
    except Exception:
        return False


def sha256_file(path: Path, cache: dict[str, str]) -> str:
    key = str(path)
    if key in cache:
        return cache[key]
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    cache[key] = h.hexdigest()
    return cache[key]


def read_csv_cached(path: Path, cache: dict[str, pd.DataFrame]) -> pd.DataFrame:
    key = str(path)
    if key not in cache:
        cache[key] = pd.read_csv(path)
    return cache[key]


def detect_date_series(df: pd.DataFrame) -> pd.Series:
    for col in DATE_COLUMNS:
        if col in df.columns:
            return pd.to_datetime(df[col], errors="coerce")
    for col in df.columns:
        if "date" in str(col).lower():
            return pd.to_datetime(df[col], errors="coerce")
    return pd.Series(pd.NaT, index=df.index)


def finite_usgs_flow_mask(df: pd.DataFrame) -> pd.Series:
    for col in USGS_FLOW_COLUMNS:
        if col in df.columns:
            vals = pd.to_numeric(df[col], errors="coerce")
            if vals.notna().sum() >= 5:
                return vals.notna()
    numeric_cols = []
    for col in df.columns:
        if col in DATE_COLUMNS or "date" in str(col).lower():
            continue
        vals = pd.to_numeric(df[col], errors="coerce")
        if vals.notna().sum() >= 5:
            numeric_cols.append(col)
    if numeric_cols:
        return pd.to_numeric(df[numeric_cols[0]], errors="coerce").notna()
    return pd.Series(False, index=df.index)


def date_window_info(path: Path, start: pd.Timestamp, cache: dict[str, pd.DataFrame]) -> dict[str, Any]:
    df = read_csv_cached(path, cache)
    dates = detect_date_series(df)
    ok = dates.notna() & (dates >= start)
    return {
        "rows_at_or_after_start": int(ok.sum()),
        "min_date": str(dates.min().date()) if dates.notna().any() else "",
        "max_date": str(dates.max().date()) if dates.notna().any() else "",
        "max_timestamp": dates.max() if dates.notna().any() else pd.NaT,
    }


def usgs_truth_window_info(path: Path, start: pd.Timestamp, end: pd.Timestamp, cache: dict[str, pd.DataFrame]) -> dict[str, Any]:
    df = read_csv_cached(path, cache)
    dates = detect_date_series(df)
    finite_flow = finite_usgs_flow_mask(df)
    in_window = dates.notna() & finite_flow & (dates >= start) & (dates <= end)
    after_start = dates.notna() & finite_flow & (dates >= start)
    return {
        "finite_rows_in_forecast_window": int(in_window.sum()),
        "finite_rows_at_or_after_start": int(after_start.sum()),
        "min_date": str(dates.min().date()) if dates.notna().any() else "",
        "max_date": str(dates.max().date()) if dates.notna().any() else "",
        "max_timestamp": dates.max() if dates.notna().any() else pd.NaT,
    }


class Recorder:
    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []

    def check(self, scope: str, check: str, ok: bool, detail: Any = "") -> None:
        self.rows.append({"scope": scope, "check": check, "status": "pass" if ok else "fail", "detail": str(detail)})

    @property
    def failures(self) -> list[dict[str, Any]]:
        return [row for row in self.rows if row["status"] == "fail"]


def validate(matrix_dir: Path, artifact_root: Path, *, allow_existing_runs: bool = False) -> tuple[Recorder, dict[str, Any]]:
    rec = Recorder()
    metadata_path = matrix_dir / "matrix_metadata.yaml"
    plan_path = matrix_dir / "matrix_plan.csv"
    specs_path = matrix_dir / "grid_spec_manifest_resolved.csv"
    registry_path = matrix_dir / "grid_run_registry.csv"
    inputs_path = matrix_dir / "source_input_manifest.csv"
    launch_ready_path = matrix_dir / "LAUNCH_READY.md"
    for path in [metadata_path, plan_path, specs_path, registry_path, inputs_path, launch_ready_path]:
        rec.check("matrix", f"exists:{path.name}", path.exists(), path)

    metadata = load_yaml(metadata_path) if metadata_path.exists() else {}
    plan = pd.read_csv(plan_path, dtype=str) if plan_path.exists() else pd.DataFrame()
    specs = pd.read_csv(specs_path, dtype=str) if specs_path.exists() else pd.DataFrame()
    registry = pd.read_csv(registry_path, dtype=str) if registry_path.exists() else pd.DataFrame()
    input_manifest = pd.read_csv(inputs_path, dtype=str) if inputs_path.exists() else pd.DataFrame()

    rec.check("matrix", "run_rows_1440", len(plan) == EXPECTED_RUN_ROWS, f"observed={len(plan)}")
    rec.check("matrix", "spec_rows_288", len(specs) == EXPECTED_SPECS, f"observed={len(specs)}")
    rec.check("matrix", "discount_cases_48", specs.get("discount_case_id", pd.Series(dtype=str)).nunique() == EXPECTED_DISCOUNT_CASES, "")
    if not specs.empty:
        rec.check("matrix", "epsilon_grid", set(pd.to_numeric(specs["epsilon"], errors="coerce").dropna()) == EXPECTED_EPSILONS, "")
        rec.check("matrix", "max_iter_100", set(pd.to_numeric(specs["max_iter"], errors="coerce").dropna()) == {100}, "")
        rec.check("matrix", "grid_spec_unique", specs["grid_spec_id"].is_unique, "")
    if not plan.empty:
        rec.check("matrix", "run_ids_unique", plan["run_id"].is_unique, "")
        rec.check("matrix", "cutoffs", set(plan["cutoff"].astype(str)) == EXPECTED_CUTOFFS, sorted(plan["cutoff"].astype(str).unique()))
        rec.check("matrix", "one_lane", set(plan["lane"].astype(str)) == {TARGET_LANE}, sorted(plan["lane"].astype(str).unique()))
        rec.check("matrix", "one_model_per_row", set(pd.to_numeric(plan["quantile_submodels"], errors="coerce").dropna()) == {1}, "")
        rec.check("matrix", "registry_rows_match", len(registry) == len(plan), f"registry={len(registry)} plan={len(plan)}")
        rec.check(
            "matrix",
            "all_specs_cover_all_cutoffs",
            plan.groupby("grid_spec_id").size().min() == len(EXPECTED_CUTOFFS)
            and plan.groupby("grid_spec_id").size().max() == len(EXPECTED_CUTOFFS),
            "",
        )

    queue = metadata.get("queue", {}) if isinstance(metadata.get("queue"), dict) else {}
    rec.check("queue", "ordinary_max_concurrent_3", int(queue.get("ordinary_max_concurrent", -1)) == 3, queue.get("ordinary_max_concurrent"))
    rec.check("queue", "heavy_cutoff_max_concurrent_1", int(queue.get("heavy_cutoff_max_concurrent", -1)) == 1, queue.get("heavy_cutoff_max_concurrent"))
    rec.check("queue", "continue_on_fail", bool(queue.get("continue_on_fail")) is True, queue.get("continue_on_fail"))
    rec.check("queue", "skip_compares", bool(queue.get("skip_compares")) is True, queue.get("skip_compares"))
    rec.check("queue", "cleanup_after_post", bool(queue.get("cleanup_rdata_after_post")) is True, queue.get("cleanup_rdata_after_post"))
    rec.check("queue", "one_core_per_run", bool(metadata.get("one_core_per_run")) is True, metadata.get("one_core_per_run"))

    specs_by_id = specs.set_index("grid_spec_id", drop=False) if "grid_spec_id" in specs else pd.DataFrame()
    hash_cache: dict[str, str] = {}
    csv_cache: dict[str, pd.DataFrame] = {}
    input_hash_by_path = {
        str(row["path"]): str(row["sha256"])
        for _, row in input_manifest.iterrows()
        if "path" in row and "sha256" in row
    }
    for _, row in plan.iterrows():
        scope = f"{row['grid_spec_id']}:{row['cutoff']}"
        config_path = Path(str(row["config_path"]))
        rec.check(scope, "config_exists", config_path.exists(), config_path)
        run_root = artifact_root / "runs" / str(row["run_id"])
        rec.check(scope, "run_not_started", allow_existing_runs or not run_root.exists(), run_root)
        if not config_path.exists() or str(row["grid_spec_id"]) not in specs_by_id.index:
            continue
        cfg = load_yaml(config_path)
        spec = specs_by_id.loc[str(row["grid_spec_id"])]
        rec.check(scope, "run_id", nested(cfg, ["run", "run_id"]) == row["run_id"], nested(cfg, ["run", "run_id"]))
        rec.check(scope, "run_root", nested(cfg, ["run", "run_root"]) == str(artifact_root / "runs"), nested(cfg, ["run", "run_root"]))
        rec.check(scope, "resolved_run_root", nested(cfg, ["run", "resolved_run_root"]) == str(run_root), nested(cfg, ["run", "resolved_run_root"]))
        for thread_key in ["omp", "openblas", "mkl", "veclib", "numexpr", "mc_cores"]:
            rec.check(scope, f"thread_{thread_key}_1", int(nested(cfg, ["run", "threads", thread_key], 0)) == 1, nested(cfg, ["run", "threads", thread_key]))
        rec.check(scope, "ndlm_main_only", bool(nested(cfg, ["models", "run_ndlm_main"])) is True, "")
        rec.check(scope, "exdqlm_multivar_disabled", bool(nested(cfg, ["models", "run_exdqlm_multivar"])) is False, "")
        rec.check(scope, "exdqlm_univar_disabled", bool(nested(cfg, ["models", "run_exdqlm_univar"])) is False, "")
        rec.check(scope, "ndlm_univar_disabled", bool(nested(cfg, ["models", "run_ndlm_univar"])) is False, "")
        rec.check(scope, "transfer_keep", nested(cfg, ["models", "ndlm_main", "forecast_transfer_mode"]) == "keep", nested(cfg, ["models", "ndlm_main", "forecast_transfer_mode"]))
        rec.check(scope, "implementation_theory_aligned", nested(cfg, ["models", "ndlm_main", "implementation_mode"]) == "theory_aligned", nested(cfg, ["models", "ndlm_main", "implementation_mode"]))
        rec.check(scope, "kalman_cpp", nested(cfg, ["models", "ndlm_main", "kalman_backend"]) == "cpp", nested(cfg, ["models", "ndlm_main", "kalman_backend"]))
        rec.check(scope, "harmonics_canonical", [round(float(x), 14) for x in nested(cfg, ["models", "ndlm_main", "seasonality", "harmonics"], [])] == [round(1.0, 14), round(2.0, 14), round(1.0 / 6.8068493, 14)], nested(cfg, ["models", "ndlm_main", "seasonality", "harmonics"]))
        for field in FLOAT_FIELDS:
            rec.check(scope, f"state_{field}", same_float(nested(cfg, ["models", "ndlm_main", "state_evolution", field]), spec[field]), f"cfg={nested(cfg, ['models', 'ndlm_main', 'state_evolution', field])} spec={spec[field]}")
        rec.check(scope, "prior_epsilon", same_float(nested(cfg, ["models", "ndlm_main", "prior", "forecast_cov", "epsilon"]), spec["epsilon"]), nested(cfg, ["models", "ndlm_main", "prior", "forecast_cov", "epsilon"]))
        rec.check(scope, "prior_c_factor", same_float(nested(cfg, ["models", "ndlm_main", "prior", "forecast_cov", "c_factor"]), spec["c_factor"]), nested(cfg, ["models", "ndlm_main", "prior", "forecast_cov", "c_factor"]))
        rec.check(scope, "max_iter_100", int(nested(cfg, ["fit", "ndlm_main", "gamma_sigma", "max_iter"], 0)) == 100, nested(cfg, ["fit", "ndlm_main", "gamma_sigma", "max_iter"]))
        rec.check(scope, "fit_workers_1", int(nested(cfg, ["fit", "parallel", "workers"], 0)) == 1, nested(cfg, ["fit", "parallel", "workers"]))
        rec.check(scope, "data_start_19870529", nested(cfg, ["dates", "data_start"]) == "1987-05-29", nested(cfg, ["dates", "data_start"]))
        rec.check(scope, "scale_fit_log1p", nested(cfg, ["scale_contract", "analysis_scale_fit_internal"]) == "log1p_cms", nested(cfg, ["scale_contract", "analysis_scale_fit_internal"]))
        rec.check(scope, "stages_forecats_false", bool(nested(cfg, ["stages", "forecats"])) is False, nested(cfg, ["stages", "forecats"]))
        for stage in ["data_prep_shared", "fit", "post", "validate", "report"]:
            rec.check(scope, f"stage_{stage}", bool(nested(cfg, ["stages", stage])) is True, nested(cfg, ["stages", stage]))
        for cfg_path in [
            nested(cfg, ["inputs", "fit", "parameters_path"]),
            nested(cfg, ["inputs", "fit", "retros_path"]),
            nested(cfg, ["inputs", "fit", "nws_forecast_path"]),
            nested(cfg, ["inputs", "fit", "glofas_forecast_path"]),
            nested(cfg, ["inputs", "fit", "usgs_cache_path"]),
        ] + [cov.get("path") for cov in nested(cfg, ["inputs", "fit", "covariates"], []) if isinstance(cov, dict)]:
            path = Path(str(cfg_path))
            rec.check(scope, f"input_exists:{path.name}", path.exists(), path)
            if path.exists() and str(path) in input_hash_by_path:
                rec.check(scope, f"input_hash:{path.name}", sha256_file(path, hash_cache) == input_hash_by_path[str(path)], path)

        cutoff_date = pd.to_datetime(nested(cfg, ["dates", "cutoff_date"], ""), errors="coerce")
        forecast_start = cutoff_date + pd.Timedelta(days=1) if not pd.isna(cutoff_date) else pd.NaT
        usgs_path = Path(str(nested(cfg, ["inputs", "fit", "usgs_cache_path"], "")))
        glofas_path = Path(str(nested(cfg, ["inputs", "fit", "glofas_forecast_path"], "")))
        if not pd.isna(forecast_start) and usgs_path.exists() and glofas_path.exists():
            try:
                fc_info = date_window_info(glofas_path, forecast_start, csv_cache)
                forecast_rows = int(fc_info["rows_at_or_after_start"])
                forecast_end = fc_info["max_timestamp"]
                rec.check(scope, "glofas_forecast_window_nonempty", forecast_rows > 0, fc_info)
                if forecast_rows > 0 and not pd.isna(forecast_end):
                    truth_info = usgs_truth_window_info(usgs_path, forecast_start, forecast_end, csv_cache)
                    rec.check(
                        scope,
                        "usgs_truth_extends_through_forecast_window",
                        truth_info["max_timestamp"] >= forecast_end,
                        f"truth={truth_info} forecast={fc_info}",
                    )
                    rec.check(
                        scope,
                        "usgs_truth_rows_cover_glofas_horizon",
                        int(truth_info["finite_rows_in_forecast_window"]) >= forecast_rows,
                        f"truth={truth_info} forecast_rows={forecast_rows}",
                    )
            except Exception as exc:
                rec.check(scope, "post_truth_window_check_readable", False, repr(exc))

    summary = {
        "validated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "artifact_root": str(artifact_root),
        "matrix_dir": str(matrix_dir),
        "checks": len(rec.rows),
        "failures": len(rec.failures),
        "run_rows": int(len(plan)),
        "specs": int(len(specs)),
        "status": "pass" if not rec.failures else "fail",
    }
    return rec, summary


def write_outputs(matrix_dir: Path, rec: Recorder, summary: dict[str, Any]) -> None:
    pd.DataFrame(rec.rows).to_csv(matrix_dir / "prelaunch_validation_checks.csv", index=False)
    (matrix_dir / "prelaunch_validation_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# HE2 N-M-T1 Broad Screen Prelaunch Validation",
        "",
        f"- status: `{summary['status']}`",
        f"- validated_at_utc: `{summary['validated_at_utc']}`",
        f"- matrix_dir: `{summary['matrix_dir']}`",
        f"- artifact_root: `{summary['artifact_root']}`",
        f"- run rows: `{summary['run_rows']}`",
        f"- specs: `{summary['specs']}`",
        f"- checks: `{summary['checks']}`",
        f"- failures: `{summary['failures']}`",
        "",
    ]
    if rec.failures:
        lines.extend(["## Failures", ""])
        for row in rec.failures[:100]:
            lines.append(f"- `{row['scope']}` `{row['check']}`: {row['detail']}")
    else:
        lines.append("All launch-blocking static checks passed. No model run was launched by this validator.")
    (matrix_dir / "PRELAUNCH_VALIDATION.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Validate HE2 N-M-T1 broad screen matrix before launch.")
    ap.add_argument("--artifact-root", default=str(DEFAULT_ARTIFACT_ROOT))
    ap.add_argument("--matrix-dir", default=str(DEFAULT_MATRIX_DIR))
    ap.add_argument("--allow-existing-runs", action="store_true")
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    matrix_dir = Path(args.matrix_dir).expanduser().resolve()
    artifact_root = Path(args.artifact_root).expanduser().resolve()
    rec, summary = validate(matrix_dir, artifact_root, allow_existing_runs=bool(args.allow_existing_runs))
    write_outputs(matrix_dir, rec, summary)
    print(json.dumps(summary, indent=2))
    return 0 if summary["failures"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
