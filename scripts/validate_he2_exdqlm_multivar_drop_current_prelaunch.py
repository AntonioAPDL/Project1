#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from build_he2_exdqlm_multivar_drop_current_relaunch import (  # noqa: E402
    DEFAULT_ARTIFACT_ROOT,
    MAX_ACTIVE_QUANTILE_WORKERS,
    QUANTILE_WORKERS_PER_RUN,
    RUN_ROWS_AT_ONCE,
    TARGET_FAMILY,
    TARGET_LABEL,
    TARGET_MODEL_ID,
    TARGET_MODEL_KEY,
)
from he2_publication_relaunch_lib import (  # noqa: E402
    DEFAULT_BUNDLE_ARTIFACT_ROOT,
    DEFAULT_BUNDLE_RUN_ID,
    EXPECTED_CUTOFFS,
    canonical_shared_paths,
)


EXPECTED_QUANTILES = [0.05, 0.20, 0.35, 0.50, 0.65, 0.80, 0.95]
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
EXPECTED_STATE = {
    "df_t": 0.99999999,
    "df_s1": 0.99999,
    "df_s2": 0.99999,
    "df_s67": 0.99999,
    "df_discrep": 0.99999,
    "lambda": 0.97,
    "df_trans": 0.9999999,
    "df_covs": 0.9999999,
}


class Recorder:
    def __init__(self) -> None:
        self.rows: list[dict[str, str]] = []

    def check(self, scope: str, check: str, ok: bool, detail: str = "") -> None:
        self.rows.append({"scope": scope, "check": check, "status": "pass" if ok else "fail", "detail": detail})

    @property
    def failures(self) -> list[dict[str, str]]:
        return [row for row in self.rows if row["status"] == "fail"]


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"YAML root must be a mapping: {path}")
    return payload


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def nested(payload: dict[str, Any], keys: list[str], default: Any = None) -> Any:
    cur: Any = payload
    for key in keys:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


def same_float(left: Any, right: Any, tol: float = 1e-10) -> bool:
    try:
        return abs(float(left) - float(right)) <= tol
    except Exception:
        return False


def expected_run_id(cutoff: str) -> str:
    return f"multimodel_{cutoff}_v8_he2pubgdpc1r1_{TARGET_FAMILY}"


def check_path(rec: Recorder, scope: str, name: str, observed: Any, expected: Path) -> None:
    rec.check(scope, name, str(observed) == str(expected), f"observed={observed} expected={expected}")


def validate(artifact_root: Path = DEFAULT_ARTIFACT_ROOT) -> tuple[Recorder, dict[str, Any]]:
    artifact_root = artifact_root.resolve()
    matrix_dir = artifact_root / "control" / "publication_relaunch_matrix"
    rec = Recorder()

    matrix_path = matrix_dir / "matrix_plan.csv"
    metadata_path = matrix_dir / "matrix_metadata.yaml"
    status_path = matrix_dir / "matrix_status.csv"
    batch_path = matrix_dir / "batch_request_snapshot.yaml"
    for path in [matrix_path, metadata_path, status_path, batch_path]:
        rec.check("matrix", f"exists:{path.name}", path.exists(), str(path))

    plan = read_csv(matrix_path) if matrix_path.exists() else []
    metadata = load_yaml(metadata_path) if metadata_path.exists() else {}
    batch = load_yaml(batch_path) if batch_path.exists() else {}

    rec.check("matrix", "run_rows_5", len(plan) == len(EXPECTED_CUTOFFS), f"observed={len(plan)}")
    rec.check("matrix", "cutoff_order", [row.get("cutoff") for row in plan] == EXPECTED_CUTOFFS, str([row.get("cutoff") for row in plan]))
    rec.check("matrix", "family", {row.get("family_id") for row in plan} == {TARGET_FAMILY}, str(sorted({row.get("family_id") for row in plan})))
    rec.check("matrix", "label", {row.get("manuscript_label") for row in plan} == {TARGET_LABEL}, str(sorted({row.get("manuscript_label") for row in plan})))
    rec.check("matrix", "model_id", {row.get("model_id") for row in plan} == {TARGET_MODEL_ID}, str(sorted({row.get("model_id") for row in plan})))
    rec.check("matrix", "model_key", {row.get("model_key") for row in plan} == {TARGET_MODEL_KEY}, str(sorted({row.get("model_key") for row in plan})))
    rec.check("matrix", "likelihood_exal", {row.get("likelihood_mode") for row in plan} == {"exal"}, str(sorted({row.get("likelihood_mode") for row in plan})))
    rec.check("matrix", "transfer_drop", {row.get("transfer_mode") for row in plan} == {"drop"}, str(sorted({row.get("transfer_mode") for row in plan})))
    rec.check("matrix", "quantile_fit_count_35", len(plan) * QUANTILE_WORKERS_PER_RUN == 35, "")
    rec.check("matrix", "metadata_target_family", metadata.get("target_family") == TARGET_FAMILY, str(metadata.get("target_family")))
    rec.check("matrix", "metadata_max_workers_14", int(metadata.get("max_active_quantile_workers", 0)) == MAX_ACTIVE_QUANTILE_WORKERS, str(metadata.get("max_active_quantile_workers", "")))
    rec.check("matrix", "metadata_cleanup_after_post", bool(metadata.get("cleanup_rdata_after_post")) is True, str(metadata.get("cleanup_rdata_after_post")))
    rec.check("matrix", "queue_ordinary_rows_2", int(nested(metadata, ["queue", "ordinary_max_concurrent"], 0)) == RUN_ROWS_AT_ONCE, str(nested(metadata, ["queue", "ordinary_max_concurrent"], "")))
    rec.check("matrix", "queue_heavy_rows_2", int(nested(metadata, ["queue", "heavy_cutoff_max_concurrent"], 0)) == RUN_ROWS_AT_ONCE, str(nested(metadata, ["queue", "heavy_cutoff_max_concurrent"], "")))
    rec.check("matrix", "queue_heavy_does_not_block", bool(nested(metadata, ["queue", "heavy_cutoff_blocks_ordinary"], True)) is False, str(nested(metadata, ["queue", "heavy_cutoff_blocks_ordinary"], "")))
    rec.check("matrix", "batch_selection_family", nested(batch, ["selection", "families"], []) == [TARGET_FAMILY], str(nested(batch, ["selection", "families"], [])))
    rec.check("matrix", "batch_resources_workers_7", int(nested(batch, ["resources", "fit_parallel_workers"], 0)) == QUANTILE_WORKERS_PER_RUN, str(nested(batch, ["resources", "fit_parallel_workers"], "")))

    wrapper_text = (ROOT / "scripts" / "run_unified_with_cleanup.sh").read_text(encoding="utf-8")
    rec.check("cleanup", "wrapper_cleanup_enabled", "CLEANUP_RDATA_AFTER_POST=1" in wrapper_text, "")
    rec.check("cleanup", "wrapper_boost_ld_path", "/data/muscat_data/jaguir26/libs/boost/lib" in wrapper_text and "LD_LIBRARY_PATH" in wrapper_text, "")

    for row in plan:
        cutoff = str(row.get("cutoff", ""))
        scope = f"{cutoff}:{TARGET_FAMILY}"
        cfg_path = Path(str(row.get("config_path", "")))
        rec.check(scope, "run_id", row.get("run_id") == expected_run_id(cutoff), str(row.get("run_id")))
        rec.check(scope, "config_exists", cfg_path.exists(), str(cfg_path))
        if not cfg_path.exists():
            continue
        cfg = load_yaml(cfg_path)
        shared = canonical_shared_paths(DEFAULT_BUNDLE_ARTIFACT_ROOT, cutoff, DEFAULT_BUNDLE_RUN_ID)

        rec.check(scope, "run_root_new_artifact", nested(cfg, ["run", "run_root"]) == str(artifact_root / "runs"), str(nested(cfg, ["run", "run_root"])))
        rec.check(scope, "run_overwrite_false", bool(nested(cfg, ["run", "overwrite"])) is False, str(nested(cfg, ["run", "overwrite"])))
        rec.check(scope, "run_autosuffix_false", bool(nested(cfg, ["run", "auto_suffix_on_collision"])) is False, str(nested(cfg, ["run", "auto_suffix_on_collision"])))
        rec.check(scope, "run_mc_cores_7", int(nested(cfg, ["run", "threads", "mc_cores"], 0)) == QUANTILE_WORKERS_PER_RUN, str(nested(cfg, ["run", "threads", "mc_cores"], "")))
        rec.check(scope, "fit_workers_7", int(nested(cfg, ["fit", "parallel", "workers"], 0)) == QUANTILE_WORKERS_PER_RUN, str(nested(cfg, ["fit", "parallel", "workers"], "")))

        rec.check(scope, "run_multivar_only", bool(nested(cfg, ["models", "run_exdqlm_multivar"])) is True, "")
        rec.check(scope, "likelihood_exal", nested(cfg, ["models", TARGET_MODEL_KEY, "likelihood_mode"]) == "exal", str(nested(cfg, ["models", TARGET_MODEL_KEY, "likelihood_mode"])))
        rec.check(scope, "transfer_drop", nested(cfg, ["models", TARGET_MODEL_KEY, "forecast_transfer_mode"]) == "drop", str(nested(cfg, ["models", TARGET_MODEL_KEY, "forecast_transfer_mode"])))
        rec.check(scope, "structure_trend", bool(nested(cfg, ["models", TARGET_MODEL_KEY, "structure", "include_trend"])) is True, str(nested(cfg, ["models", TARGET_MODEL_KEY, "structure"], {})))
        rec.check(scope, "structure_harmonics_123", nested(cfg, ["models", TARGET_MODEL_KEY, "structure", "enabled_harmonic_indices"], []) == [1, 2, 3], str(nested(cfg, ["models", TARGET_MODEL_KEY, "structure", "enabled_harmonic_indices"], [])))
        for key, value in EXPECTED_STATE.items():
            rec.check(scope, f"state_{key}", same_float(nested(cfg, ["models", TARGET_MODEL_KEY, "state_evolution", key]), value), str(nested(cfg, ["models", TARGET_MODEL_KEY, "state_evolution", key])))

        rec.check(scope, "max_iter_100", int(nested(cfg, ["fit", TARGET_MODEL_KEY, "gamma_sigma", "max_iter"], 0)) == 100, str(nested(cfg, ["fit", TARGET_MODEL_KEY, "gamma_sigma", "max_iter"], "")))
        rec.check(scope, "forecast_cov_epsilon_30", same_float(nested(cfg, ["fit", TARGET_MODEL_KEY, "legacy", "forecast_cov", "epsilon"]), 30.0), str(nested(cfg, ["fit", TARGET_MODEL_KEY, "legacy", "forecast_cov", "epsilon"])))
        rec.check(scope, "forecast_cov_c_factor_1", same_float(nested(cfg, ["fit", TARGET_MODEL_KEY, "legacy", "forecast_cov", "c_factor"]), 1.0), str(nested(cfg, ["fit", TARGET_MODEL_KEY, "legacy", "forecast_cov", "c_factor"])))
        rec.check(scope, "quantiles", [float(q) for q in nested(cfg, ["fit", "quantiles"], [])] == EXPECTED_QUANTILES, str(nested(cfg, ["fit", "quantiles"], [])))

        rec.check(scope, "data_start", nested(cfg, ["dates", "data_start"]) == "1987-05-29", str(nested(cfg, ["dates", "data_start"])))
        rec.check(scope, "scale_fit_log1p", nested(cfg, ["scale_contract", "analysis_scale_fit_internal"]) == "log1p_cms", str(nested(cfg, ["scale_contract", "analysis_scale_fit_internal"])))
        rec.check(scope, "scale_post_log1p", nested(cfg, ["scale_contract", "analysis_scale_post_internal"]) == "log1p_cms", str(nested(cfg, ["scale_contract", "analysis_scale_post_internal"])))
        rec.check(scope, "transform_policy_log1p", nested(cfg, ["scale_contract", "transform_policy"]) == "log1p_only", str(nested(cfg, ["scale_contract", "transform_policy"])))

        check_path(rec, scope, "bundle_meta", nested(cfg, ["inputs", "forecats", "existing_bundle_path"]), shared["bundle_meta"])
        check_path(rec, scope, "parameters_path", nested(cfg, ["inputs", "fit", "parameters_path"]), shared["parameters"])
        check_path(rec, scope, "retros_path", nested(cfg, ["inputs", "fit", "retros_path"]), shared["retros"])
        check_path(rec, scope, "nws_path", nested(cfg, ["inputs", "fit", "nws_forecast_path"]), shared["nws_forecast"])
        check_path(rec, scope, "glofas_path", nested(cfg, ["inputs", "fit", "glofas_forecast_path"]), shared["glofas_forecast"])
        covs = nested(cfg, ["inputs", "fit", "covariates"], [])
        cov_map = {cov.get("name"): cov.get("path") for cov in covs if isinstance(cov, dict)}
        check_path(rec, scope, "cov_ppt", cov_map.get("PPT"), shared["cov_ppt"])
        check_path(rec, scope, "cov_soil", cov_map.get("SOIL"), shared["cov_soil"])
        check_path(rec, scope, "cov_pca", cov_map.get("PCA"), shared["cov_pca"])
        rec.check(scope, "transfer_base_covariates", nested(cfg, ["inputs", "transfer_function_covariates", "base_covariates"], []) == EXPECTED_TRANSFER_BASE, str(nested(cfg, ["inputs", "transfer_function_covariates", "base_covariates"], [])))
        rec.check(scope, "transfer_engineered_covariates", nested(cfg, ["inputs", "transfer_function_covariates", "engineered_terms"], []) == EXPECTED_TRANSFER_ENGINEERED, str(nested(cfg, ["inputs", "transfer_function_covariates", "engineered_terms"], [])))
        rec.check(scope, "covariate_lags_123", nested(cfg, ["inputs", "covariate_features", "lag_orders"], []) == [1, 2, 3], str(nested(cfg, ["inputs", "covariate_features", "lag_orders"], [])))
        rec.check(scope, "covariate_squares", bool(nested(cfg, ["inputs", "covariate_features", "include_squares"])) is True, str(nested(cfg, ["inputs", "covariate_features", "include_squares"])))
        rec.check(scope, "covariate_interaction", bool(nested(cfg, ["inputs", "covariate_features", "include_interaction"])) is True, str(nested(cfg, ["inputs", "covariate_features", "include_interaction"])))
        rec.check(scope, "deterministic_climate_enabled", bool(nested(cfg, ["inputs", "deterministic_climate", "enabled"])) is True, str(nested(cfg, ["inputs", "deterministic_climate", "enabled"])))

    summary = {
        "validated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "artifact_root": str(artifact_root),
        "matrix_dir": str(matrix_dir),
        "target_family": TARGET_FAMILY,
        "target_label": TARGET_LABEL,
        "target_model_id": TARGET_MODEL_ID,
        "checks": len(rec.rows),
        "failures": len(rec.failures),
        "run_rows": len(plan),
        "quantile_fits": len(plan) * QUANTILE_WORKERS_PER_RUN,
    }
    return rec, summary


def write_outputs(matrix_dir: Path, rec: Recorder, summary: dict[str, Any]) -> None:
    matrix_dir.mkdir(parents=True, exist_ok=True)
    with (matrix_dir / "exdqlm_multivar_drop_current_prelaunch_checks.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=["scope", "check", "status", "detail"], lineterminator="\n")
        writer.writeheader()
        writer.writerows(rec.rows)
    (matrix_dir / "exdqlm_multivar_drop_current_prelaunch_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    status = "pass" if summary["failures"] == 0 else "fail"
    lines = [
        "# HE2 exAL-M-T0 Current-Code Prelaunch Validation",
        "",
        f"- status: `{status}`",
        f"- checks: `{summary['checks']}`",
        f"- failures: `{summary['failures']}`",
        f"- run rows: `{summary['run_rows']}`",
        f"- quantile fits represented: `{summary['quantile_fits']}`",
        f"- artifact_root: `{summary['artifact_root']}`",
        f"- matrix_dir: `{summary['matrix_dir']}`",
        "",
        "Validated contract: current-code multivariate exDQLM drop on the 20260510 canonical input bundle, with two cutoff rows at a time and post-success heavy-artifact cleanup.",
    ]
    if rec.failures:
        lines.extend(["", "## Failures", ""])
        for row in rec.failures[:100]:
            lines.append(f"- `{row['scope']}` `{row['check']}`: {row['detail']}")
    (matrix_dir / "EXDQLM_MULTIVAR_DROP_CURRENT_PRELAUNCH_VALIDATION.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate current-code exAL-M-T0 prelaunch package.")
    parser.add_argument("--artifact-root", type=Path, default=DEFAULT_ARTIFACT_ROOT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rec, summary = validate(args.artifact_root)
    write_outputs(Path(summary["matrix_dir"]), rec, summary)
    print(json.dumps(summary, indent=2))
    return 0 if summary["failures"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
