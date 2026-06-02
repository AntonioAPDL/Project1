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

from build_he2_dqlm_multivar_al_keep_from_exal_winners import (  # noqa: E402
    DEFAULT_ARTIFACT_ROOT,
    MAX_ACTIVE_QUANTILE_WORKERS,
    QUANTILE_WORKERS_PER_RUN,
    RUN_ROWS_AT_ONCE,
    SOURCE_FAMILY,
    SOURCE_LABEL,
    SOURCE_MODEL_ID,
    TARGET_FAMILY,
    TARGET_LABEL,
    TARGET_MODEL_ID,
    TARGET_MODEL_KEY,
    target_run_id,
)
from he2_exdqlm_keep_authoritative import (  # noqa: E402
    EXPECTED_CUTOFFS,
    EXPECTED_QUANTILE_LABELS,
    EXPECTED_QUANTILES,
    load_authoritative_spec,
)
from validate_he2_exdqlm_multivar_keep_grid_prelaunch import (  # noqa: E402
    EXPECTED_HARMONICS,
    EXPECTED_TRANSFER_BASE,
    EXPECTED_TRANSFER_ENGINEERED,
    nested,
)


FLOAT_FIELDS = ["df_t", "df_s1", "df_s2", "df_s67", "df_discrep", "lambda", "df_trans", "df_covs"]
PRESERVED_TOP_LEVEL_KEYS = ["inputs", "dates", "scale_contract", "stages"]
PRESERVED_MODEL_KEYS = ["implementation_mode", "forecast_transfer_mode", "state_evolution", "structure"]
PRESERVED_FIT_KEYS = ["quantiles", "parallel", "warm_start", "exdqlm_multivar", "contract_checks", "diagnostics"]


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


def same_float(left: Any, right: Any, tol: float = 1e-12) -> bool:
    try:
        return abs(float(left) - float(right)) <= tol
    except Exception:
        return False


def write_outputs(matrix_dir: Path, rec: Recorder, summary: dict[str, Any]) -> None:
    matrix_dir.mkdir(parents=True, exist_ok=True)
    with (matrix_dir / "al_keep_from_exal_winners_prelaunch_checks.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=["scope", "check", "status", "detail"], lineterminator="\n")
        writer.writeheader()
        writer.writerows(rec.rows)
    (matrix_dir / "al_keep_from_exal_winners_prelaunch_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    status = "pass" if summary["failures"] == 0 else "fail"
    lines = [
        "# HE2 AL-M-T1 From exAL-M-T1 Winners Prelaunch Validation",
        "",
        f"- status: `{status}`",
        f"- checks: `{summary['checks']}`",
        f"- failures: `{summary['failures']}`",
        f"- run rows: `{summary['run_rows']}`",
        f"- quantile fits represented: `{summary['quantile_fits']}`",
        f"- artifact_root: `{summary['artifact_root']}`",
        f"- matrix_dir: `{summary['matrix_dir']}`",
        "",
        "Validated contract: clone the five authoritative `exAL-M-T1` winner configs and switch only the active multivariate likelihood to `al`, preserving the current input bundles and winner specs.",
    ]
    if rec.failures:
        lines.extend(["", "## Failures", ""])
        for row in rec.failures[:100]:
            lines.append(f"- `{row['scope']}` `{row['check']}`: {row['detail']}")
    (matrix_dir / "AL_KEEP_FROM_EXAL_WINNERS_PRELAUNCH_VALIDATION.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def validate(manifest_path: Path, artifact_root: Path) -> tuple[Recorder, dict[str, Any]]:
    spec = load_authoritative_spec(manifest_path)
    artifact_root = artifact_root.resolve()
    matrix_dir = artifact_root / "control" / "publication_relaunch_matrix"
    config_output_dir = artifact_root / "control" / "generated_configs"
    rec = Recorder()

    matrix_path = matrix_dir / "matrix_plan.csv"
    metadata_path = matrix_dir / "matrix_metadata.yaml"
    clone_path = matrix_dir / "source_clone_manifest.csv"
    bundle_path = matrix_dir / "cutoff_bundle_audit.csv"
    frozen_path = matrix_dir / "frozen_spec_manifest.csv"
    for path in [matrix_path, metadata_path, clone_path, bundle_path, frozen_path]:
        rec.check("matrix", f"exists:{path.name}", path.exists(), str(path))

    metadata = load_yaml(metadata_path) if metadata_path.exists() else {}
    plan = read_csv(matrix_path) if matrix_path.exists() else []
    rec.check("matrix", "run_rows_5", len(plan) == 5, f"observed={len(plan)}")
    rec.check("matrix", "cutoff_order", [row.get("cutoff") for row in plan] == EXPECTED_CUTOFFS, str([row.get("cutoff") for row in plan]))
    rec.check("matrix", "target_family", {row.get("family_id") for row in plan} == {TARGET_FAMILY}, str(sorted({row.get("family_id") for row in plan})))
    rec.check("matrix", "target_label", {row.get("manuscript_label") for row in plan} == {TARGET_LABEL}, str(sorted({row.get("manuscript_label") for row in plan})))
    rec.check("matrix", "target_model_id", {row.get("model_id") for row in plan} == {TARGET_MODEL_ID}, str(sorted({row.get("model_id") for row in plan})))
    rec.check("matrix", "likelihood_al", {row.get("likelihood_mode") for row in plan} == {"al"}, str(sorted({row.get("likelihood_mode") for row in plan})))
    rec.check("matrix", "transfer_keep", {row.get("transfer_mode") for row in plan} == {"keep"}, str(sorted({row.get("transfer_mode") for row in plan})))
    rec.check("matrix", "active_quantiles", {row.get("active_quantiles") for row in plan} == {EXPECTED_QUANTILE_LABELS}, str(sorted({row.get("active_quantiles") for row in plan})))
    rec.check("matrix", "quantile_fits_35", len(plan) * len(EXPECTED_QUANTILES) == 35, "")
    rec.check("matrix", "metadata_status_prepared", metadata.get("status") == "prepared_not_launched", str(metadata.get("status")))
    rec.check("matrix", "metadata_cleanup_after_post", bool(metadata.get("cleanup_rdata_after_post")) is True, str(metadata.get("cleanup_rdata_after_post")))
    rec.check("matrix", "metadata_skip_compares", bool(metadata.get("skip_compare_bundles")) is True, str(metadata.get("skip_compare_bundles")))
    rec.check("matrix", "metadata_continue_on_fail", bool(metadata.get("continue_on_fail")) is True, str(metadata.get("continue_on_fail")))
    rec.check("matrix", "queue_run_rows_at_once_2", int(nested(metadata, ["queue", "ordinary_max_concurrent"], 0)) == RUN_ROWS_AT_ONCE, str(nested(metadata, ["queue", "ordinary_max_concurrent"], "")))
    rec.check("matrix", "queue_heavy_rows_at_once_2", int(nested(metadata, ["queue", "heavy_cutoff_max_concurrent"], 0)) == RUN_ROWS_AT_ONCE, str(nested(metadata, ["queue", "heavy_cutoff_max_concurrent"], "")))
    rec.check("matrix", "queue_heavy_does_not_block_ordinary", bool(nested(metadata, ["queue", "heavy_cutoff_blocks_ordinary"], True)) is False, str(nested(metadata, ["queue", "heavy_cutoff_blocks_ordinary"], "")))
    rec.check("matrix", "resources_quantile_workers_7", int(nested(metadata, ["resources", "fit_parallel_workers"], 0)) == QUANTILE_WORKERS_PER_RUN, str(nested(metadata, ["resources", "fit_parallel_workers"], "")))
    rec.check("matrix", "resources_mc_cores_7", int(nested(metadata, ["resources", "mc_cores"], 0)) == QUANTILE_WORKERS_PER_RUN, str(nested(metadata, ["resources", "mc_cores"], "")))
    rec.check("matrix", "metadata_max_active_quantile_workers_14", int(metadata.get("max_active_quantile_workers", 0)) == MAX_ACTIVE_QUANTILE_WORKERS, str(metadata.get("max_active_quantile_workers", "")))
    rec.check("matrix", "matrix_status_exists", (matrix_dir / "matrix_status.csv").exists(), str(matrix_dir / "matrix_status.csv"))
    rec.check("matrix", "queue_log_exists", (matrix_dir / "queue.log").exists(), str(matrix_dir / "queue.log"))

    source_by_cutoff = spec.winner_by_cutoff()
    for row in plan:
        cutoff = str(row.get("cutoff", "")).zfill(8)
        winner = source_by_cutoff.get(cutoff)
        scope = f"{cutoff}:{row.get('grid_spec_id')}"
        rec.check(scope, "cutoff_in_authoritative_manifest", winner is not None, cutoff)
        if winner is None:
            continue

        source_config_path = spec.generated_config_path(winner)
        target_config_path = Path(str(row.get("config_path", "")))
        rec.check(scope, "source_config_exists", source_config_path.exists(), str(source_config_path))
        rec.check(scope, "target_config_exists", target_config_path.exists(), str(target_config_path))
        rec.check(scope, "target_config_under_output_dir", target_config_path.parent == config_output_dir, str(target_config_path))
        rec.check(scope, "run_id_matches_target_rule", row.get("run_id") == target_run_id(cutoff, winner.grid_spec_id), str(row.get("run_id")))
        if not source_config_path.exists() or not target_config_path.exists():
            continue

        source_cfg = load_yaml(source_config_path)
        target_cfg = load_yaml(target_config_path)
        rec.check(scope, "source_likelihood_exal", nested(source_cfg, ["models", "exdqlm_multivar", "likelihood_mode"]) == "exal", str(nested(source_cfg, ["models", "exdqlm_multivar", "likelihood_mode"])))
        rec.check(scope, "target_likelihood_al", nested(target_cfg, ["models", "exdqlm_multivar", "likelihood_mode"]) == "al", str(nested(target_cfg, ["models", "exdqlm_multivar", "likelihood_mode"])))
        rec.check(scope, "target_model_multivar_only", bool(nested(target_cfg, ["models", "run_exdqlm_multivar"])) is True, "")
        rec.check(scope, "target_univar_disabled", bool(nested(target_cfg, ["models", "run_exdqlm_univar"])) is False, "")
        rec.check(scope, "target_ndlm_main_disabled", bool(nested(target_cfg, ["models", "run_ndlm_main"])) is False, "")
        rec.check(scope, "target_ndlm_univar_disabled", bool(nested(target_cfg, ["models", "run_ndlm_univar"])) is False, "")
        rec.check(scope, "run_root_new_artifact", nested(target_cfg, ["run", "run_root"]) == str(artifact_root / "runs"), str(nested(target_cfg, ["run", "run_root"])))
        rec.check(scope, "resolved_run_root_new_artifact", nested(target_cfg, ["run", "resolved_run_root"]) == str(artifact_root / "runs" / row["run_id"]), str(nested(target_cfg, ["run", "resolved_run_root"])))
        rec.check(scope, "resolved_config_path_matches", nested(target_cfg, ["run", "resolved_config_path"]) == str(target_config_path), str(nested(target_cfg, ["run", "resolved_config_path"])))
        rec.check(scope, "run_overwrite_false", bool(nested(target_cfg, ["run", "overwrite"])) is False, str(nested(target_cfg, ["run", "overwrite"])))
        rec.check(scope, "run_autosuffix_false", bool(nested(target_cfg, ["run", "auto_suffix_on_collision"])) is False, str(nested(target_cfg, ["run", "auto_suffix_on_collision"])))

        for key in PRESERVED_TOP_LEVEL_KEYS:
            rec.check(scope, f"preserve_top_level_{key}", target_cfg.get(key) == source_cfg.get(key), key)
        for key in PRESERVED_MODEL_KEYS:
            rec.check(
                scope,
                f"preserve_model_{key}",
                nested(target_cfg, ["models", "exdqlm_multivar", key]) == nested(source_cfg, ["models", "exdqlm_multivar", key]),
                key,
            )
        for key in PRESERVED_FIT_KEYS:
            rec.check(scope, f"preserve_fit_{key}", nested(target_cfg, ["fit", key]) == nested(source_cfg, ["fit", key]), key)

        rec.check(scope, "harmonics_123", nested(target_cfg, ["models", "exdqlm_multivar", "structure", "enabled_harmonic_indices"], []) == EXPECTED_HARMONICS, str(nested(target_cfg, ["models", "exdqlm_multivar", "structure", "enabled_harmonic_indices"], [])))
        rec.check(scope, "transfer_base_covariates", nested(target_cfg, ["inputs", "transfer_function_covariates", "base_covariates"], []) == EXPECTED_TRANSFER_BASE, str(nested(target_cfg, ["inputs", "transfer_function_covariates", "base_covariates"], [])))
        rec.check(scope, "transfer_engineered_covariates", nested(target_cfg, ["inputs", "transfer_function_covariates", "engineered_terms"], []) == EXPECTED_TRANSFER_ENGINEERED, str(nested(target_cfg, ["inputs", "transfer_function_covariates", "engineered_terms"], [])))
        feature_cfg = nested(target_cfg, ["inputs", "covariate_features"], {})
        rec.check(scope, "covariate_lags_123", nested(feature_cfg, ["lag_orders"], []) == [1, 2, 3] if isinstance(feature_cfg, dict) else False, str(feature_cfg))
        rec.check(scope, "covariate_squares", bool(nested(feature_cfg, ["include_squares"])) is True if isinstance(feature_cfg, dict) else False, str(feature_cfg))
        rec.check(scope, "covariate_interaction", bool(nested(feature_cfg, ["include_interaction"])) is True if isinstance(feature_cfg, dict) else False, str(feature_cfg))
        rec.check(scope, "quantiles", [float(x) for x in nested(target_cfg, ["fit", "quantiles"], [])] == EXPECTED_QUANTILES, str(nested(target_cfg, ["fit", "quantiles"], [])))
        rec.check(scope, "max_iter_100", int(nested(target_cfg, ["fit", "exdqlm_multivar", "gamma_sigma", "max_iter"], 0)) == 100, str(nested(target_cfg, ["fit", "exdqlm_multivar", "gamma_sigma", "max_iter"], "")))
        rec.check(scope, "data_start", nested(target_cfg, ["dates", "data_start"]) == "1987-05-29", str(nested(target_cfg, ["dates", "data_start"])))
        rec.check(scope, "scale_fit_log1p", nested(target_cfg, ["scale_contract", "analysis_scale_fit_internal"]) == "log1p_cms", str(nested(target_cfg, ["scale_contract", "analysis_scale_fit_internal"])))
        rec.check(scope, "scale_post_log1p", nested(target_cfg, ["scale_contract", "analysis_scale_post_internal"]) == "log1p_cms", str(nested(target_cfg, ["scale_contract", "analysis_scale_post_internal"])))
        rec.check(scope, "transform_policy_log1p", nested(target_cfg, ["scale_contract", "transform_policy"]) == "log1p_only", str(nested(target_cfg, ["scale_contract", "transform_policy"])))
        rec.check(scope, "forecast_cov_epsilon", same_float(nested(target_cfg, ["fit", "exdqlm_multivar", "legacy", "forecast_cov", "epsilon"]), winner.epsilon_value), str(nested(target_cfg, ["fit", "exdqlm_multivar", "legacy", "forecast_cov", "epsilon"])))
        rec.check(scope, "forecast_cov_c_factor", same_float(nested(target_cfg, ["fit", "exdqlm_multivar", "legacy", "forecast_cov", "c_factor"]), winner.c_factor), str(nested(target_cfg, ["fit", "exdqlm_multivar", "legacy", "forecast_cov", "c_factor"])))
        expected_state = {
            "df_t": winner.df_t,
            "df_s1": winner.df_s1,
            "df_s2": winner.df_s2,
            "df_s67": winner.df_s67,
            "df_discrep": winner.df_discrep,
            "lambda": winner.lambda_value,
            "df_trans": winner.df_trans,
            "df_covs": winner.df_covs,
        }
        for field in FLOAT_FIELDS:
            rec.check(
                scope,
                f"state_{field}",
                same_float(nested(target_cfg, ["models", "exdqlm_multivar", "state_evolution", field]), expected_state[field]),
                str(nested(target_cfg, ["models", "exdqlm_multivar", "state_evolution", field])),
            )

        forecast_meta = Path(str(nested(target_cfg, ["inputs", "forecats", "existing_bundle_path"], "")))
        rec.check(scope, "bundle_meta_exists", forecast_meta.exists(), str(forecast_meta))
        rec.check(scope, "bundle_cutoff_matches", f"cutoff_date={nested(target_cfg, ['dates', 'cutoff_date'])}" in str(forecast_meta), str(forecast_meta))
        rec.check(scope, "bundle_run_id_matches", "run_id=20260510_publication_shared_r01" in str(forecast_meta), str(forecast_meta))
        debug = nested(target_cfg, ["debug_he2_dqlm_al_keep_from_exal_winners"], {})
        rec.check(scope, "debug_block_exists", isinstance(debug, dict), str(type(debug)))
        rec.check(scope, "debug_source_run", isinstance(debug, dict) and debug.get("source_run_id") == winner.run_id, str(debug))
        rec.check(scope, "debug_no_launch", isinstance(debug, dict) and bool(debug.get("no_launch")) is True, str(debug))
        rec.check(scope, "debug_gamma_contract", isinstance(debug, dict) and "gamma" in str(debug.get("expected_gamma_contract", "")).lower(), str(debug))
        rec.check(scope, "debug_st_contract", isinstance(debug, dict) and "update_sts" in str(debug.get("expected_st_contract", "")), str(debug))

    summary = {
        "validated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "manifest_path": str(spec.manifest_path),
        "artifact_root": str(artifact_root),
        "matrix_dir": str(matrix_dir),
        "target_family": TARGET_FAMILY,
        "target_label": TARGET_LABEL,
        "target_model_id": TARGET_MODEL_ID,
        "source_family": SOURCE_FAMILY,
        "source_label": SOURCE_LABEL,
        "source_model_id": SOURCE_MODEL_ID,
        "checks": len(rec.rows),
        "failures": len(rec.failures),
        "run_rows": len(plan),
        "quantile_fits": len(plan) * len(EXPECTED_QUANTILES),
    }
    return rec, summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate AL-M-T1 clone configs prepared from exAL-M-T1 winners.")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "docs" / "exdqlm_multivar_keep_authoritative_specs_20260601.yaml",
    )
    parser.add_argument("--artifact-root", type=Path, default=DEFAULT_ARTIFACT_ROOT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rec, summary = validate(args.manifest.resolve(), args.artifact_root.resolve())
    write_outputs(Path(summary["matrix_dir"]), rec, summary)
    print(json.dumps(summary, indent=2))
    return 0 if summary["failures"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
