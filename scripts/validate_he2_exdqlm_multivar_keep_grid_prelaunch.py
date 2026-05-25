#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_MATRIX_DIR = Path(
    "/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/"
    "multimodel_v8_he2_exdqlm_multivar_keep_epsilon_discount_grid_20260524/"
    "control/publication_relaunch_matrix"
)

EXPECTED_CUTOFFS = {"20210123", "20211112", "20211221", "20220511", "20221225"}
EXPECTED_QUANTILES = [0.05, 0.20, 0.35, 0.50, 0.65, 0.80, 0.95]
EXPECTED_QUANTILE_LABELS = "05|20|35|50|65|80|95"
EXPECTED_HARMONICS = [1, 2, 3]
EXPECTED_TRANSFER_BASE = ["PPT", "SOIL", "PCA"]
EXPECTED_TRANSFER_ENGINEERED = [
    "PPT_sq",
    "SOIL_sq",
    "PPT_x_SOIL",
    "PPT_lag1",
    "PPT_lag2",
    "PPT_lag3",
    "SOIL_lag1",
    "SOIL_lag2",
    "SOIL_lag3",
]
FLOAT_FIELDS = ["df_t", "df_s1", "df_s2", "df_s67", "df_discrep", "lambda", "df_trans", "df_covs"]


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"YAML root is not a mapping: {path}")
    return payload


def nested(payload: dict[str, Any], keys: list[str], default: Any = None) -> Any:
    cur: Any = payload
    for key in keys:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


def as_float(value: Any) -> float:
    return float(value)


def same_float(left: Any, right: Any, tol: float = 1e-12) -> bool:
    return abs(float(left) - float(right)) <= tol


def cutoff_dash(cutoff: str) -> str:
    cutoff = str(cutoff).zfill(8)
    return f"{cutoff[:4]}-{cutoff[4:6]}-{cutoff[6:8]}"


class Recorder:
    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []

    def check(self, scope: str, check: str, ok: bool, detail: str = "") -> None:
        self.rows.append({"scope": scope, "check": check, "status": "pass" if ok else "fail", "detail": detail})

    @property
    def failures(self) -> list[dict[str, Any]]:
        return [row for row in self.rows if row["status"] == "fail"]


def validate_matrix(matrix_dir: Path, artifact_root: Path | None) -> tuple[Recorder, dict[str, Any]]:
    rec = Recorder()
    matrix_dir = matrix_dir.resolve()
    metadata_path = matrix_dir / "matrix_metadata.yaml"
    metadata = load_yaml(metadata_path) if metadata_path.exists() else {}
    if artifact_root is None:
        artifact_root_raw = metadata.get("artifact_root")
        artifact_root = Path(str(artifact_root_raw)).resolve() if artifact_root_raw else matrix_dir.parents[1].resolve()
    else:
        artifact_root = artifact_root.resolve()

    plan_path = matrix_dir / "matrix_plan.csv"
    specs_path = matrix_dir / "grid_spec_manifest_resolved.csv"
    registry_path = matrix_dir / "grid_run_registry.csv"
    frozen_path = matrix_dir / "frozen_spec_manifest.csv"
    for path in [plan_path, specs_path, registry_path, frozen_path, metadata_path]:
        rec.check("matrix", f"exists:{path.name}", path.exists(), str(path))

    plan = pd.read_csv(plan_path, dtype=str)
    specs = pd.read_csv(specs_path, dtype=str)
    registry = pd.read_csv(registry_path, dtype=str)
    frozen = pd.read_csv(frozen_path, dtype=str)

    expected_rows = len(specs) * len(EXPECTED_CUTOFFS)
    rec.check("matrix", "spec_count_30", len(specs) == 30, f"observed={len(specs)}")
    rec.check("matrix", "run_rows_150", len(plan) == expected_rows == 150, f"observed={len(plan)} expected={expected_rows}")
    rec.check("matrix", "registry_rows_match_plan", len(registry) == len(plan), f"registry={len(registry)} plan={len(plan)}")
    rec.check("matrix", "frozen_rows_match_plan", len(frozen) == len(plan), f"frozen={len(frozen)} plan={len(plan)}")
    rec.check("matrix", "run_ids_unique", plan["run_id"].is_unique, "")
    rec.check("matrix", "cutoff_set", set(plan["cutoff"].astype(str)) == EXPECTED_CUTOFFS, str(sorted(plan["cutoff"].unique())))
    rec.check("matrix", "all_specs_cover_all_cutoffs", plan.groupby("grid_spec_id").size().min() == 5 and plan.groupby("grid_spec_id").size().max() == 5, "")
    rec.check("matrix", "all_cutoffs_cover_all_specs", plan.groupby("cutoff").size().min() == 30 and plan.groupby("cutoff").size().max() == 30, "")
    rec.check("matrix", "active_quantiles", set(plan["active_quantiles"].astype(str)) == {EXPECTED_QUANTILE_LABELS}, str(sorted(plan["active_quantiles"].unique())))
    rec.check("matrix", "allow_failures", bool(metadata.get("allow_run_failures")) is True, str(metadata.get("allow_run_failures")))
    rec.check("matrix", "skip_compare_bundles", bool(metadata.get("skip_compare_bundles")) is True, str(metadata.get("skip_compare_bundles")))
    rec.check("matrix", "queue_rows_at_once_4", int(nested(metadata, ["queue", "ordinary_max_concurrent"], 0)) == 4, str(nested(metadata, ["queue", "ordinary_max_concurrent"], "")))
    rec.check("matrix", "queue_pause_mem_gb_120", float(nested(metadata, ["queue", "pause_mem_gb"], 0)) == 120.0, str(nested(metadata, ["queue", "pause_mem_gb"], "")))
    rec.check("matrix", "queue_launch_mem_gb_170", float(nested(metadata, ["queue", "launch_mem_gb"], 0)) == 170.0, str(nested(metadata, ["queue", "launch_mem_gb"], "")))
    rec.check("matrix", "queue_heavy_mem_gb_190", float(nested(metadata, ["queue", "heavy_mem_gb"], 0)) == 190.0, str(nested(metadata, ["queue", "heavy_mem_gb"], "")))
    rec.check("matrix", "fit_parallel_workers_7", int(nested(metadata, ["resources", "fit_parallel_workers"], 0)) == 7, str(nested(metadata, ["resources", "fit_parallel_workers"], "")))
    rec.check("matrix", "mc_cores_7", int(nested(metadata, ["resources", "mc_cores"], 0)) == 7, str(nested(metadata, ["resources", "mc_cores"], "")))

    wrapper_path = ROOT / "scripts" / "run_unified_with_cleanup.sh"
    wrapper_text = wrapper_path.read_text(encoding="utf-8") if wrapper_path.exists() else ""
    rec.check("cleanup", "cleanup_wrapper_exports_env", "CLEANUP_RDATA_AFTER_POST=1" in wrapper_text, str(wrapper_path))

    specs_by_id = specs.set_index("grid_spec_id", drop=False)
    registry_by_run = registry.set_index("run_id", drop=False)
    for _, row in plan.iterrows():
        run_id = str(row["run_id"])
        scope = f"{row['grid_spec_id']}:{row['cutoff']}"
        rec.check(scope, "registry_row", run_id in registry_by_run.index, run_id)
        rec.check(scope, "spec_row", str(row["grid_spec_id"]) in specs_by_id.index, str(row["grid_spec_id"]))
        config_path = Path(str(row["config_path"]))
        rec.check(scope, "config_exists", config_path.exists(), str(config_path))
        if not config_path.exists():
            continue
        cfg = load_yaml(config_path)
        spec = specs_by_id.loc[str(row["grid_spec_id"])]
        reg = registry_by_run.loc[run_id] if run_id in registry_by_run.index else row

        rec.check(scope, "run_id_matches", nested(cfg, ["run", "run_id"]) == run_id, str(nested(cfg, ["run", "run_id"])))
        rec.check(scope, "run_root_matches_artifact", nested(cfg, ["run", "run_root"]) == str(artifact_root / "runs"), str(nested(cfg, ["run", "run_root"])))
        rec.check(scope, "resolved_run_root_matches", nested(cfg, ["run", "resolved_run_root"]) == str(artifact_root / "runs" / run_id), str(nested(cfg, ["run", "resolved_run_root"])))
        rec.check(scope, "model_family_multivar_only", bool(nested(cfg, ["models", "run_exdqlm_multivar"])) is True, "")
        rec.check(scope, "univar_disabled", bool(nested(cfg, ["models", "run_exdqlm_univar"])) is False, "")
        rec.check(scope, "ndlm_main_disabled", bool(nested(cfg, ["models", "run_ndlm_main"])) is False, "")
        rec.check(scope, "ndlm_univar_disabled", bool(nested(cfg, ["models", "run_ndlm_univar"])) is False, "")
        rec.check(scope, "transfer_keep", nested(cfg, ["models", "exdqlm_multivar", "forecast_transfer_mode"]) == "keep", "")
        rec.check(scope, "harmonics_123", nested(cfg, ["models", "exdqlm_multivar", "structure", "enabled_harmonic_indices"], []) == EXPECTED_HARMONICS, str(nested(cfg, ["models", "exdqlm_multivar", "structure", "enabled_harmonic_indices"], [])))
        for field in FLOAT_FIELDS:
            rec.check(
                scope,
                f"state_{field}",
                same_float(nested(cfg, ["models", "exdqlm_multivar", "state_evolution", field]), reg[field]),
                f"cfg={nested(cfg, ['models', 'exdqlm_multivar', 'state_evolution', field])} registry={reg[field]}",
            )
            rec.check(scope, f"spec_{field}", same_float(reg[field], spec[field]), f"registry={reg[field]} spec={spec[field]}")
        rec.check(scope, "forecast_cov_epsilon", same_float(nested(cfg, ["fit", "exdqlm_multivar", "legacy", "forecast_cov", "epsilon"]), spec["epsilon"]), str(spec["epsilon"]))
        rec.check(scope, "forecast_cov_c_factor", same_float(nested(cfg, ["fit", "exdqlm_multivar", "legacy", "forecast_cov", "c_factor"]), spec["c_factor"]), str(spec["c_factor"]))
        rec.check(scope, "quantiles", [float(x) for x in nested(cfg, ["fit", "quantiles"], [])] == EXPECTED_QUANTILES, str(nested(cfg, ["fit", "quantiles"], [])))
        rec.check(scope, "workers_7", int(nested(cfg, ["fit", "parallel", "workers"], 0)) == 7, str(nested(cfg, ["fit", "parallel", "workers"], "")))
        rec.check(scope, "mc_cores_7", int(nested(cfg, ["run", "threads", "mc_cores"], 0)) == 7, str(nested(cfg, ["run", "threads", "mc_cores"], "")))
        rec.check(scope, "data_start", nested(cfg, ["dates", "data_start"]) == "1987-05-29", str(nested(cfg, ["dates", "data_start"])))
        rec.check(scope, "scale_fit_log1p", nested(cfg, ["scale_contract", "analysis_scale_fit_internal"]) == "log1p_cms", str(nested(cfg, ["scale_contract", "analysis_scale_fit_internal"])))
        rec.check(scope, "scale_post_log1p", nested(cfg, ["scale_contract", "analysis_scale_post_internal"]) == "log1p_cms", str(nested(cfg, ["scale_contract", "analysis_scale_post_internal"])))
        rec.check(scope, "transform_policy_log1p", nested(cfg, ["scale_contract", "transform_policy"]) == "log1p_only", str(nested(cfg, ["scale_contract", "transform_policy"])))
        rec.check(scope, "post_smoke_fast", bool(nested(cfg, ["post", "smoke_fast"])) is True, "")
        rec.check(scope, "post_force_isolation_smoke_fast", bool(nested(cfg, ["post", "force_isolation_smoke_fast"])) is True, "")
        rec.check(scope, "component_diag_enabled", bool(nested(cfg, ["post", "multivar_component_diagnostics", "enabled"])) is True, "")
        rec.check(scope, "component_diag_fail_fast", bool(nested(cfg, ["post", "multivar_component_diagnostics", "fail_fast"])) is True, "")
        rec.check(scope, "component_diag_q50", same_float(nested(cfg, ["post", "multivar_component_diagnostics", "quantile"]), 0.50), str(nested(cfg, ["post", "multivar_component_diagnostics", "quantile"])))
        rec.check(scope, "component_diag_pre_days_30", int(nested(cfg, ["post", "multivar_component_diagnostics", "pre_days"], 0)) == 30, str(nested(cfg, ["post", "multivar_component_diagnostics", "pre_days"], "")))
        rec.check(scope, "stages_forecats_reuse_existing", bool(nested(cfg, ["stages", "forecats"])) is False, "")
        for stage in ["data_prep_shared", "fit", "post", "validate", "report"]:
            rec.check(scope, f"stage_{stage}", bool(nested(cfg, ["stages", stage])) is True, "")
        rec.check(scope, "transfer_base_covariates", nested(cfg, ["inputs", "transfer_function_covariates", "base_covariates"], []) == EXPECTED_TRANSFER_BASE, str(nested(cfg, ["inputs", "transfer_function_covariates", "base_covariates"], [])))
        rec.check(scope, "transfer_engineered_covariates", nested(cfg, ["inputs", "transfer_function_covariates", "engineered_terms"], []) == EXPECTED_TRANSFER_ENGINEERED, str(nested(cfg, ["inputs", "transfer_function_covariates", "engineered_terms"], [])))
        feature_cfg = nested(cfg, ["inputs", "covariate_features"], {})
        rec.check(scope, "covariate_lags_123", nested(feature_cfg, ["lag_orders"], []) == [1, 2, 3] if isinstance(feature_cfg, dict) else False, str(feature_cfg))
        rec.check(scope, "covariate_squares", bool(nested(feature_cfg, ["include_squares"])) is True if isinstance(feature_cfg, dict) else False, str(feature_cfg))
        rec.check(scope, "covariate_interaction", bool(nested(feature_cfg, ["include_interaction"])) is True if isinstance(feature_cfg, dict) else False, str(feature_cfg))
        forecast_meta = Path(str(nested(cfg, ["inputs", "forecats", "existing_bundle_path"], "")))
        rec.check(scope, "bundle_meta_exists", forecast_meta.exists(), str(forecast_meta))
        rec.check(scope, "bundle_cutoff_matches", f"cutoff_date={cutoff_dash(str(row['cutoff']))}" in str(forecast_meta), str(forecast_meta))
        rec.check(scope, "bundle_run_id_matches", "run_id=20260510_publication_shared_r01" in str(forecast_meta), str(forecast_meta))
        debug_grid = nested(cfg, ["debug_he2_exdqlm_keep_grid"], {})
        rec.check(scope, "debug_grid_spec_id", isinstance(debug_grid, dict) and debug_grid.get("grid_spec_id") == row["grid_spec_id"], str(debug_grid))

    summary = {
        "validated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "matrix_dir": str(matrix_dir),
        "artifact_root": str(artifact_root),
        "checks": len(rec.rows),
        "failures": len(rec.failures),
        "plan_rows": int(len(plan)),
        "specs": int(len(specs)),
        "cutoffs": sorted(plan["cutoff"].astype(str).unique().tolist()),
        "quantile_fits": int(len(plan) * len(EXPECTED_QUANTILES)),
    }
    return rec, summary


def write_outputs(matrix_dir: Path, rec: Recorder, summary: dict[str, Any]) -> None:
    pd.DataFrame(rec.rows).to_csv(matrix_dir / "prelaunch_validation_checks.csv", index=False)
    (matrix_dir / "prelaunch_validation_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# HE2 exDQLM Multivar Keep Grid Prelaunch Validation",
        "",
        f"- validated_at_utc: `{summary['validated_at_utc']}`",
        f"- matrix_dir: `{summary['matrix_dir']}`",
        f"- artifact_root: `{summary['artifact_root']}`",
        f"- status: `{'pass' if summary['failures'] == 0 else 'fail'}`",
        f"- checks: `{summary['checks']}`",
        f"- failures: `{summary['failures']}`",
        f"- run rows: `{summary['plan_rows']}`",
        f"- specs: `{summary['specs']}`",
        f"- quantile fits: `{summary['quantile_fits']}`",
        "",
    ]
    if rec.failures:
        lines.extend(["## Failures", ""])
        for row in rec.failures[:50]:
            lines.append(f"- `{row['scope']}` `{row['check']}`: {row['detail']}")
    else:
        lines.extend([
            "All static prelaunch gates passed.",
            "",
            "This validates matrix/config wiring only; it does not launch or fit models.",
        ])
    (matrix_dir / "PRELAUNCH_VALIDATION.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Validate prepared HE2 exDQLM multivar keep epsilon/discount grid wiring.")
    ap.add_argument("--matrix-dir", default=str(DEFAULT_MATRIX_DIR))
    ap.add_argument("--artifact-root", default="")
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    matrix_dir = Path(args.matrix_dir).expanduser().resolve()
    artifact_root = Path(args.artifact_root).expanduser().resolve() if args.artifact_root else None
    rec, summary = validate_matrix(matrix_dir, artifact_root)
    write_outputs(matrix_dir, rec, summary)
    print(json.dumps(summary, indent=2))
    return 0 if summary["failures"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
