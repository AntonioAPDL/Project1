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

from he2_exdqlm_keep_authoritative import (  # noqa: E402
    EXPECTED_CUTOFFS,
    EXPECTED_QUANTILE_LABELS,
    EXPECTED_QUANTILES,
    assert_close,
    iter_runtime_checks,
    load_authoritative_spec,
)
from validate_he2_exdqlm_multivar_keep_grid_prelaunch import (  # noqa: E402
    EXPECTED_HARMONICS,
    EXPECTED_TRANSFER_BASE,
    EXPECTED_TRANSFER_ENGINEERED,
    nested,
)


FLOAT_FIELDS = ["df_t", "df_s1", "df_s2", "df_s67", "df_discrep", "lambda", "df_trans", "df_covs"]


class Recorder:
    def __init__(self) -> None:
        self.rows: list[dict[str, str]] = []

    def check(self, scope: str, check: str, ok: bool, detail: str = "") -> None:
        self.rows.append({"scope": scope, "check": check, "status": "pass" if ok else "fail", "detail": detail})

    @property
    def failures(self) -> list[dict[str, str]]:
        return [row for row in self.rows if row["status"] == "fail"]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"YAML root must be a mapping: {path}")
    return payload


def same_float(left: Any, right: Any, tol: float = 1e-12) -> bool:
    return abs(float(left) - float(right)) <= tol


def validate(manifest_path: Path, matrix_dir: Path | None = None) -> tuple[Recorder, dict[str, Any]]:
    spec = load_authoritative_spec(manifest_path)
    matrix_dir = (matrix_dir or (spec.runtime_root / "control" / "authoritative_winner_matrix")).resolve()
    rec = Recorder()

    matrix_path = matrix_dir / "matrix_plan.csv"
    metadata_path = matrix_dir / "matrix_metadata.yaml"
    rec.check("matrix", "matrix_plan_exists", matrix_path.exists(), str(matrix_path))
    rec.check("matrix", "matrix_metadata_exists", metadata_path.exists(), str(metadata_path))

    plan = read_csv(matrix_path) if matrix_path.exists() else []
    rec.check("matrix", "winner_rows_5", len(plan) == 5, f"observed={len(plan)}")
    rec.check("matrix", "cutoff_order", [row.get("cutoff") for row in plan] == EXPECTED_CUTOFFS, str([row.get("cutoff") for row in plan]))
    rec.check("matrix", "active_quantiles", {row.get("active_quantiles") for row in plan} == {EXPECTED_QUANTILE_LABELS}, str(sorted({row.get("active_quantiles") for row in plan})))
    rec.check("matrix", "family_exdqlm_keep", {row.get("family") for row in plan} == {"exdqlm_multivar_keep"}, str(sorted({row.get("family") for row in plan})))
    rec.check("matrix", "label_exal_m_t1", {row.get("manuscript_label") for row in plan} == {"exAL-M-T1"}, str(sorted({row.get("manuscript_label") for row in plan})))

    by_cutoff = spec.winner_by_cutoff()
    for row in plan:
        cutoff = row.get("cutoff", "")
        winner = by_cutoff.get(cutoff)
        scope = f"{cutoff}:{row.get('grid_spec_id')}"
        rec.check(scope, "winner_cutoff_in_manifest", winner is not None, cutoff)
        if winner is None:
            continue
        rec.check(scope, "run_id_matches_manifest", row.get("run_id") == winner.run_id, row.get("run_id", ""))
        rec.check(scope, "grid_spec_matches_manifest", row.get("grid_spec_id") == winner.grid_spec_id, row.get("grid_spec_id", ""))
        rec.check(scope, "mean_crps_matches_manifest", same_float(row.get("mean_crps"), winner.mean_crps), str(row.get("mean_crps")))

    for runtime_row in iter_runtime_checks(spec):
        rec.check(
            f"{runtime_row['cutoff']}:{runtime_row['run_id']}",
            runtime_row["check"],
            runtime_row["status"] == "pass",
            runtime_row["detail"],
        )

    for winner in spec.winners:
        cfg_path = spec.generated_config_path(winner)
        scope = f"{winner.cutoff}:{winner.grid_spec_id}:config"
        if not cfg_path.exists():
            continue
        cfg = load_yaml(cfg_path)
        rec.check(scope, "run_id", nested(cfg, ["run", "run_id"]) == winner.run_id, str(nested(cfg, ["run", "run_id"])))
        rec.check(scope, "resolved_run_root", nested(cfg, ["run", "resolved_run_root"]) == str(spec.run_root(winner)), str(nested(cfg, ["run", "resolved_run_root"])))
        rec.check(scope, "model_family_multivar_only", bool(nested(cfg, ["models", "run_exdqlm_multivar"])) is True, "")
        rec.check(scope, "univar_disabled", bool(nested(cfg, ["models", "run_exdqlm_univar"])) is False, "")
        rec.check(scope, "ndlm_main_disabled", bool(nested(cfg, ["models", "run_ndlm_main"])) is False, "")
        rec.check(scope, "ndlm_univar_disabled", bool(nested(cfg, ["models", "run_ndlm_univar"])) is False, "")
        rec.check(scope, "transfer_keep", nested(cfg, ["models", "exdqlm_multivar", "forecast_transfer_mode"]) == "keep", "")
        rec.check(scope, "harmonics_123", nested(cfg, ["models", "exdqlm_multivar", "structure", "enabled_harmonic_indices"], []) == EXPECTED_HARMONICS, str(nested(cfg, ["models", "exdqlm_multivar", "structure", "enabled_harmonic_indices"], [])))
        rec.check(scope, "quantiles", [float(x) for x in nested(cfg, ["fit", "quantiles"], [])] == EXPECTED_QUANTILES, str(nested(cfg, ["fit", "quantiles"], [])))
        rec.check(scope, "max_iter_100", int(nested(cfg, ["fit", "exdqlm_multivar", "gamma_sigma", "max_iter"], 0)) == 100, str(nested(cfg, ["fit", "exdqlm_multivar", "gamma_sigma", "max_iter"], "")))
        rec.check(scope, "forecast_cov_epsilon", same_float(nested(cfg, ["fit", "exdqlm_multivar", "legacy", "forecast_cov", "epsilon"]), winner.epsilon_value), str(nested(cfg, ["fit", "exdqlm_multivar", "legacy", "forecast_cov", "epsilon"])))
        rec.check(scope, "forecast_cov_c_factor", same_float(nested(cfg, ["fit", "exdqlm_multivar", "legacy", "forecast_cov", "c_factor"]), winner.c_factor), str(nested(cfg, ["fit", "exdqlm_multivar", "legacy", "forecast_cov", "c_factor"])))
        state = {
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
            rec.check(scope, f"state_{field}", same_float(nested(cfg, ["models", "exdqlm_multivar", "state_evolution", field]), state[field]), str(nested(cfg, ["models", "exdqlm_multivar", "state_evolution", field])))
        rec.check(scope, "data_start", nested(cfg, ["dates", "data_start"]) == "1987-05-29", str(nested(cfg, ["dates", "data_start"])))
        rec.check(scope, "scale_fit_log1p", nested(cfg, ["scale_contract", "analysis_scale_fit_internal"]) == "log1p_cms", str(nested(cfg, ["scale_contract", "analysis_scale_fit_internal"])))
        rec.check(scope, "scale_post_log1p", nested(cfg, ["scale_contract", "analysis_scale_post_internal"]) == "log1p_cms", str(nested(cfg, ["scale_contract", "analysis_scale_post_internal"])))
        rec.check(scope, "transform_policy_log1p", nested(cfg, ["scale_contract", "transform_policy"]) == "log1p_only", str(nested(cfg, ["scale_contract", "transform_policy"])))
        rec.check(scope, "post_smoke_fast", bool(nested(cfg, ["post", "smoke_fast"])) is True, "")
        rec.check(scope, "post_export_tables", bool(nested(cfg, ["post", "export_tables"])) is True, "")
        rec.check(scope, "component_diag_enabled", bool(nested(cfg, ["post", "multivar_component_diagnostics", "enabled"])) is True, "")
        rec.check(scope, "transfer_base_covariates", nested(cfg, ["inputs", "transfer_function_covariates", "base_covariates"], []) == EXPECTED_TRANSFER_BASE, str(nested(cfg, ["inputs", "transfer_function_covariates", "base_covariates"], [])))
        rec.check(scope, "transfer_engineered_covariates", nested(cfg, ["inputs", "transfer_function_covariates", "engineered_terms"], []) == EXPECTED_TRANSFER_ENGINEERED, str(nested(cfg, ["inputs", "transfer_function_covariates", "engineered_terms"], [])))
        feature_cfg = nested(cfg, ["inputs", "covariate_features"], {})
        rec.check(scope, "covariate_lags_123", nested(feature_cfg, ["lag_orders"], []) == [1, 2, 3] if isinstance(feature_cfg, dict) else False, str(feature_cfg))
        rec.check(scope, "covariate_squares", bool(nested(feature_cfg, ["include_squares"])) is True if isinstance(feature_cfg, dict) else False, str(feature_cfg))
        rec.check(scope, "covariate_interaction", bool(nested(feature_cfg, ["include_interaction"])) is True if isinstance(feature_cfg, dict) else False, str(feature_cfg))
        crps_row = spec.selected_crps_row(winner)
        rec.check(scope, "crps_table_mean", assert_close(float(crps_row["mean_crps"]), winner.mean_crps), f"manifest={winner.mean_crps} table={crps_row['mean_crps']}")

    summary = {
        "validated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "manifest_path": str(spec.manifest_path),
        "matrix_dir": str(matrix_dir),
        "runtime_root": str(spec.runtime_root),
        "checks": len(rec.rows),
        "failures": len(rec.failures),
        "winner_rows": len(plan),
        "remaining_model_input_parity_required": True,
        "remaining_8_model_input_parity_required": False,
    }
    return rec, summary


def write_outputs(matrix_dir: Path, rec: Recorder, summary: dict[str, Any]) -> None:
    matrix_dir.mkdir(parents=True, exist_ok=True)
    with (matrix_dir / "authoritative_prelaunch_validation_checks.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["scope", "check", "status", "detail"], lineterminator="\n")
        writer.writeheader()
        writer.writerows(rec.rows)
    (matrix_dir / "authoritative_prelaunch_validation_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    status = "pass" if summary["failures"] == 0 else "fail"
    lines = [
        "# HE2 exDQLM Multivar Keep Authoritative Prelaunch Validation",
        "",
        f"- status: `{status}`",
        f"- checks: `{summary['checks']}`",
        f"- failures: `{summary['failures']}`",
        f"- winner rows: `{summary['winner_rows']}`",
        f"- runtime_root: `{summary['runtime_root']}`",
        "",
        "This validates the five selected `exAL-M-T1` winner rows, their source configs, post outputs, CRPS values, and cleanup state.",
        "",
        "Publication gate: all nine HE2 Bayesian comparison families now resolve to canonical-bundle promoted roots after the 2026-06-07 NDLM promotion.",
    ]
    if rec.failures:
        lines.extend(["", "## Failures", ""])
        for row in rec.failures[:80]:
            lines.append(f"- `{row['scope']}` `{row['check']}`: {row['detail']}")
    (matrix_dir / "AUTHORITATIVE_PRELAUNCH_VALIDATION.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate the five-row authoritative exDQLM multivar keep winner matrix.")
    parser.add_argument("--manifest", type=Path, default=ROOT / "docs" / "exdqlm_multivar_keep_authoritative_specs_20260601.yaml")
    parser.add_argument("--matrix-dir", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rec, summary = validate(args.manifest.resolve(), args.matrix_dir.resolve() if args.matrix_dir else None)
    write_outputs(Path(summary["matrix_dir"]), rec, summary)
    print(json.dumps(summary, indent=2))
    return 0 if summary["failures"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
