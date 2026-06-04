#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from build_he2_dqlm_multivar_al_drop_from_exal_drop import (  # noqa: E402
    SOURCE_ARTIFACT_ROOT,
    TARGET_FAMILY,
    TARGET_LABEL,
    TARGET_MODEL_ID,
    TARGET_MODEL_KEY,
    clone_config,
    source_config_path,
    source_run_id,
)


DEFAULT_ARTIFACT_ROOT = (
    ROOT.parent / "project1_ucsc_phd_runtime" / "multimodel_v8_he2_dqlm_multivar_al_drop_diagnostics_20260603"
)

DEFAULT_DIAGNOSTIC_LANES: list[dict[str, str]] = [
    {
        "cutoff": "20210123",
        "q": "35",
        "tier": "extended",
        "failure_signature": "forecast_health_max_E_sigma_119",
    },
    {
        "cutoff": "20210123",
        "q": "65",
        "tier": "extended",
        "failure_signature": "forecast_health_max_E_sigma_999",
    },
    {
        "cutoff": "20211112",
        "q": "35",
        "tier": "representative",
        "failure_signature": "post_save_chol_G_non_pd",
    },
    {
        "cutoff": "20211221",
        "q": "35",
        "tier": "extended",
        "failure_signature": "forecast_health_max_E_sigma_201",
    },
    {
        "cutoff": "20211221",
        "q": "80",
        "tier": "representative",
        "failure_signature": "huge_state_forecast_and_max_E_sigma_999",
    },
    {
        "cutoff": "20220511",
        "q": "65",
        "tier": "representative",
        "failure_signature": "forecast_health_max_E_sigma_450",
    },
    {
        "cutoff": "20221225",
        "q": "20",
        "tier": "extended",
        "failure_signature": "post_save_chol_G_non_pd",
    },
    {
        "cutoff": "20221225",
        "q": "35",
        "tier": "extended",
        "failure_signature": "forecast_health_max_E_sigma_891",
    },
    {
        "cutoff": "20221225",
        "q": "65",
        "tier": "extended",
        "failure_signature": "forecast_health_max_E_sigma_999",
    },
    {
        "cutoff": "20221225",
        "q": "80",
        "tier": "representative",
        "failure_signature": "forecast_mvrnorm_sigma_non_pd",
    },
]

DEFAULT_TRANSFER_BASE_FEATURES = ["PPT", "SOIL", "PCA"]
DEFAULT_TRANSFER_ENGINEERED_FEATURES = [
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

TRANSFER_EXPERIMENTS: list[dict[str, Any]] = [
    {
        "experiment_id": "a0_full_sd",
        "label": "A0",
        "description": "Current high-discount AL-M-T0 full transfer design with historical SD-only scaling.",
        "mode": "full",
        "scaling": "sd",
        "base_covariates": DEFAULT_TRANSFER_BASE_FEATURES,
        "engineered_terms": DEFAULT_TRANSFER_ENGINEERED_FEATURES,
    },
    {
        "experiment_id": "a1_transfer_level_only",
        "label": "A1",
        "description": "Transfer level only; no covariate driver rows.",
        "mode": "none",
        "scaling": "sd",
        "base_covariates": [],
        "engineered_terms": [],
    },
    {
        "experiment_id": "a2_full_zscore",
        "label": "A2",
        "description": "Full transfer design with history-fitted mean-zero unit-SD scaling.",
        "mode": "full",
        "scaling": "zscore",
        "base_covariates": DEFAULT_TRANSFER_BASE_FEATURES,
        "engineered_terms": DEFAULT_TRANSFER_ENGINEERED_FEATURES,
    },
    {
        "experiment_id": "a3_base_sd",
        "label": "A3",
        "description": "Base transfer covariates only with historical SD-only scaling.",
        "mode": "base_only",
        "scaling": "sd",
        "base_covariates": DEFAULT_TRANSFER_BASE_FEATURES,
        "engineered_terms": [],
    },
    {
        "experiment_id": "a4_base_zscore",
        "label": "A4",
        "description": "Base transfer covariates only with history-fitted mean-zero unit-SD scaling.",
        "mode": "base_only",
        "scaling": "zscore",
        "base_covariates": DEFAULT_TRANSFER_BASE_FEATURES,
        "engineered_terms": [],
    },
]


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def git_head() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return "unknown"


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"YAML root must be a mapping: {path}")
    return payload


def write_yaml(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(payload, handle, sort_keys=False, default_flow_style=False)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"no rows to write: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def deep_merge_dict(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    out = deepcopy(base)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = deep_merge_dict(out[key], value)
        else:
            out[key] = deepcopy(value)
    return out


def matrix_row_from_diagnostic_row(row: dict[str, Any]) -> dict[str, Any]:
    epsilon_value = row.get("forecast_cov_epsilon", "")
    try:
        epsilon_label = f"eps{int(float(epsilon_value))}"
    except Exception:
        epsilon_label = str(epsilon_value or "eps_unknown")
    q_float_value = q_float(str(row["q"]))
    return {
        "order_index": row["order_index"],
        "cutoff": row["cutoff"],
        "epsilon": epsilon_label,
        "epsilon_value": epsilon_value,
        "lane": f"q{row['q']}",
        "run_scope": "diagnostic_single_quantile_fit_only",
        "run_id": row["run_id"],
        "config_path": row["config_path"],
        "compare_outdir": "",
        "priority_group": "al_m_t0_representative_diagnostic" if row["tier"] == "representative" else "al_m_t0_extended_diagnostic",
        "max_concurrent_class": "ordinary",
        "family_id": row["family_id"],
        "model_id": row["model_id"],
        "model_key": row["model_key"],
        "model_class": "dqlm",
        "likelihood_mode": row["likelihood_mode"],
        "transfer_mode": row["transfer_mode"],
        "manuscript_label": row["manuscript_label"],
        "row_kind": "diagnostic_fit_only",
        "quantile_submodels": f"{q_float_value:.2f}",
        "active_quantiles": f"{q_float_value:.2f}",
        "spec_id": row["spec_id"],
        "experiment_id": row["experiment_id"],
        "transfer_feature_mode": row["transfer_feature_mode"],
        "transfer_feature_scaling": row["transfer_feature_scaling"],
        "transfer_feature_columns": row["transfer_feature_columns"],
        "failure_signature": row["failure_signature"],
        "no_launch_guarded": row["no_launch"],
        "fit_only": row["fit_only"],
    }


def q_float(q_label: str) -> float:
    return int(q_label) / 100.0


def nested(payload: dict[str, Any], keys: list[str], default: Any = None) -> Any:
    cur: Any = payload
    for key in keys:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


def diagnostic_run_id(cutoff: str, q: str, spec_id: str, experiment_id: str = "a0_full_sd") -> str:
    safe_spec = "".join(ch if ch.isalnum() else "_" for ch in spec_id).strip("_").lower()
    safe_experiment = "".join(ch if ch.isalnum() else "_" for ch in experiment_id).strip("_").lower()
    return f"diagnostic_{cutoff}_{TARGET_FAMILY}_q{q}_{safe_spec}_{safe_experiment}"


def load_discount_spec(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {
            "spec_id": "source_clone_failed_spec",
            "description": (
                "No override supplied. Diagnostics preserve the failed AL-M-T0 clone specs so a future run can "
                "separate algorithmic failure from a later discount/epsilon retune."
            ),
            "requires_user_discount_decision": True,
            "state_evolution": {},
            "forecast_cov": {},
            "gamma_sigma": {},
            "legacy": {},
        }
    spec = load_yaml(path)
    spec.setdefault("spec_id", path.stem)
    spec.setdefault("description", "")
    spec.setdefault("requires_user_discount_decision", False)
    spec.setdefault("state_evolution", {})
    spec.setdefault("forecast_cov", {})
    spec.setdefault("gamma_sigma", {})
    spec.setdefault("legacy", {})
    return spec


def apply_discount_spec(cfg: dict[str, Any], spec: dict[str, Any]) -> None:
    state_patch = spec.get("state_evolution") or {}
    if state_patch:
        cfg.setdefault("models", {}).setdefault(TARGET_MODEL_KEY, {}).setdefault("state_evolution", {}).update(
            deepcopy(state_patch)
        )

    fit_model = cfg.setdefault("fit", {}).setdefault(TARGET_MODEL_KEY, {})
    gamma_sigma_patch = spec.get("gamma_sigma") or {}
    if gamma_sigma_patch:
        fit_model["gamma_sigma"] = deep_merge_dict(fit_model.get("gamma_sigma", {}), gamma_sigma_patch)

    legacy_patch = spec.get("legacy") or {}
    if legacy_patch:
        fit_model["legacy"] = deep_merge_dict(fit_model.get("legacy", {}), legacy_patch)

    forecast_cov_patch = spec.get("forecast_cov") or {}
    if forecast_cov_patch:
        legacy = fit_model.setdefault("legacy", {})
        legacy["forecast_cov"] = deep_merge_dict(legacy.get("forecast_cov", {}), forecast_cov_patch)


def apply_transfer_experiment(cfg: dict[str, Any], experiment: dict[str, Any]) -> None:
    cfg.setdefault("inputs", {})["transfer_function_covariates"] = {
        "mode": experiment["mode"],
        "scaling": experiment["scaling"],
        "base_covariates": list(experiment["base_covariates"]),
        "engineered_terms": list(experiment["engineered_terms"]),
    }
    cfg["debug_he2_al_m_t0_transfer_experiment"] = {
        "experiment_id": experiment["experiment_id"],
        "label": experiment["label"],
        "description": experiment["description"],
        "mode": experiment["mode"],
        "scaling": experiment["scaling"],
        "base_covariates": list(experiment["base_covariates"]),
        "engineered_terms": list(experiment["engineered_terms"]),
    }


def prepare_config(
    *,
    source_root: Path,
    artifact_root: Path,
    config_dir: Path,
    cutoff: str,
    q: str,
    spec: dict[str, Any],
    experiment: dict[str, Any],
    code_commit: str,
) -> tuple[dict[str, Any], Path, str]:
    src_path = source_config_path(source_root, cutoff)
    if not src_path.exists():
        raise FileNotFoundError(f"missing source exAL-M-T0 config: {src_path}")
    source_cfg = load_yaml(src_path)
    spec_id = str(spec["spec_id"])
    run_id = diagnostic_run_id(cutoff, q, spec_id, str(experiment["experiment_id"]))
    target_cfg_path = config_dir / f"{run_id}.yaml"
    cfg = clone_config(
        source_cfg,
        cutoff=cutoff,
        source_cfg_path=src_path,
        target_cfg_path=target_cfg_path,
        source_root=source_root,
        artifact_root=artifact_root,
        code_commit=code_commit,
    )
    cfg.setdefault("run", {})
    cfg["run"]["run_id"] = run_id
    cfg["run"]["run_root"] = str(artifact_root / "runs")
    cfg["run"]["resolved_run_root"] = str(artifact_root / "runs" / run_id)
    cfg["run"]["resolved_config_path"] = str(target_cfg_path)
    cfg["run"]["overwrite"] = False
    cfg["run"]["auto_suffix_on_collision"] = False
    cfg["run"].setdefault("threads", {})
    cfg["run"]["threads"]["mc_cores"] = 1

    cfg.setdefault("fit", {})
    cfg["fit"]["quantiles"] = [q_float(q)]
    cfg["fit"].setdefault("parallel", {})
    cfg["fit"]["parallel"]["workers"] = 1

    # Diagnostics are intentionally fit-only and no-cleanup so the failed object can be inspected later.
    stages = cfg.setdefault("stages", {})
    for stage in ["forecats", "post", "validate", "report"]:
        stages[stage] = False
    stages["data_prep_shared"] = True
    stages["fit"] = True

    apply_discount_spec(cfg, spec)
    apply_transfer_experiment(cfg, experiment)

    cfg["debug_he2_al_m_t0_diagnostic"] = {
        "status": "prepared_not_launched",
        "no_launch": True,
        "diagnostic_scope": "single_quantile_fit_only_no_cleanup",
        "cutoff": cutoff,
        "q": q,
        "spec_id": spec_id,
        "experiment_id": experiment["experiment_id"],
        "source_run_id": source_run_id(cutoff),
        "source_artifact_root": str(source_root),
        "target_artifact_root": str(artifact_root),
        "run_id": run_id,
        "config_path": str(target_cfg_path),
        "discount_spec": spec,
        "transfer_experiment": experiment,
        "retain_rdata_if_launched": True,
        "launch_status": "blocked_until_user_confirms_discount_spec_and_launch",
    }
    return cfg, target_cfg_path, run_id


def select_lanes(scope: str) -> list[dict[str, str]]:
    if scope == "all_failed":
        return list(DEFAULT_DIAGNOSTIC_LANES)
    if scope == "representative":
        return [row for row in DEFAULT_DIAGNOSTIC_LANES if row["tier"] == "representative"]
    raise ValueError(f"unknown lane scope: {scope}")


def select_experiments(scope: str) -> list[dict[str, Any]]:
    if scope == "a0":
        return [deepcopy(TRANSFER_EXPERIMENTS[0])]
    for experiment in TRANSFER_EXPERIMENTS:
        if scope == str(experiment["label"]).lower():
            return [deepcopy(experiment)]
    if scope == "ladder":
        return [deepcopy(row) for row in TRANSFER_EXPERIMENTS]
    raise ValueError(f"unknown experiment scope: {scope}")


def build_package(
    artifact_root: Path,
    *,
    source_artifact_root: Path = SOURCE_ARTIFACT_ROOT,
    discount_spec_path: Path | None = None,
    lane_scope: str = "representative",
    experiment_scope: str = "a0",
) -> dict[str, Any]:
    artifact_root = artifact_root.resolve()
    source_artifact_root = source_artifact_root.resolve()
    matrix_dir = artifact_root / "control" / "diagnostic_matrix"
    config_dir = artifact_root / "control" / "generated_configs"
    matrix_dir.mkdir(parents=True, exist_ok=True)
    config_dir.mkdir(parents=True, exist_ok=True)

    spec = load_discount_spec(discount_spec_path)
    lanes = select_lanes(lane_scope)
    experiments = select_experiments(experiment_scope)
    code_commit = git_head()
    rows: list[dict[str, Any]] = []
    idx = 0
    for experiment in experiments:
        for lane in lanes:
            idx += 1
            cfg, cfg_path, run_id = prepare_config(
                source_root=source_artifact_root,
                artifact_root=artifact_root,
                config_dir=config_dir,
                cutoff=lane["cutoff"],
                q=lane["q"],
                spec=spec,
                experiment=experiment,
                code_commit=code_commit,
            )
            write_yaml(cfg_path, cfg)
            state = nested(cfg, ["models", TARGET_MODEL_KEY, "state_evolution"], {}) or {}
            forecast_cov = nested(cfg, ["fit", TARGET_MODEL_KEY, "legacy", "forecast_cov"], {}) or {}
            feature_columns = list(experiment["base_covariates"]) + list(experiment["engineered_terms"])
            rows.append(
                {
                    "order_index": idx,
                    "cutoff": lane["cutoff"],
                    "q": lane["q"],
                    "tier": lane["tier"],
                    "failure_signature": lane["failure_signature"],
                    "family_id": TARGET_FAMILY,
                    "manuscript_label": TARGET_LABEL,
                    "model_id": TARGET_MODEL_ID,
                    "model_key": TARGET_MODEL_KEY,
                    "likelihood_mode": "al",
                    "transfer_mode": "drop",
                    "spec_id": spec["spec_id"],
                    "experiment_id": experiment["experiment_id"],
                    "experiment_label": experiment["label"],
                    "experiment_description": experiment["description"],
                    "transfer_feature_mode": experiment["mode"],
                    "transfer_feature_scaling": experiment["scaling"],
                    "transfer_feature_columns": ",".join(feature_columns),
                    "requires_user_discount_decision": str(bool(spec.get("requires_user_discount_decision", False))),
                    "run_id": run_id,
                    "config_path": str(cfg_path),
                    "source_run_id": source_run_id(lane["cutoff"]),
                    "source_config_path": str(source_config_path(source_artifact_root, lane["cutoff"])),
                    "df_t": state.get("df_t", ""),
                    "df_s1": state.get("df_s1", ""),
                    "df_s2": state.get("df_s2", ""),
                    "df_s67": state.get("df_s67", ""),
                    "df_discrep": state.get("df_discrep", ""),
                    "lambda": state.get("lambda", ""),
                    "df_trans": state.get("df_trans", ""),
                    "df_covs": state.get("df_covs", ""),
                    "forecast_cov_epsilon": forecast_cov.get("epsilon", ""),
                    "c_factor": forecast_cov.get("c_factor", ""),
                    "max_iter": nested(cfg, ["fit", TARGET_MODEL_KEY, "gamma_sigma", "max_iter"], ""),
                    "no_launch": "True",
                    "fit_only": "True",
                    "cleanup_disabled_for_diagnostic": "True",
                }
            )

    queue_rows = [matrix_row_from_diagnostic_row(row) for row in rows]
    write_csv(matrix_dir / "diagnostic_matrix_plan.csv", rows)
    write_csv(matrix_dir / "diagnostic_config_manifest.csv", rows)
    write_csv(matrix_dir / "matrix_plan.csv", queue_rows)
    metadata = {
        "generated_at_utc": utc_now(),
        "status": "prepared_not_launched",
        "no_launch": True,
        "launch_files_written": False,
        "campaign_id": "he2_dqlm_multivar_al_drop_diagnostics_20260603",
        "artifact_root": str(artifact_root),
        "source_artifact_root": str(source_artifact_root),
        "matrix_dir": str(matrix_dir),
        "config_dir": str(config_dir),
        "lane_scope": lane_scope,
        "experiment_scope": experiment_scope,
        "n_lanes": len(rows),
        "n_lane_templates": len(lanes),
        "n_experiments": len(experiments),
        "experiments": experiments,
        "discount_spec_path": str(discount_spec_path) if discount_spec_path else "",
        "discount_spec": spec,
        "requires_user_discount_decision": bool(spec.get("requires_user_discount_decision", False)),
        "code_commit": code_commit,
    }
    write_yaml(matrix_dir / "diagnostic_matrix_metadata.yaml", metadata)
    (matrix_dir / "NO_LAUNCH_GUARD.txt").write_text(
        "\n".join(
            [
                "This diagnostic package is prepared_not_launched.",
                "Do not run these configs until the AL-M-T0 discount/epsilon spec is confirmed.",
                "The package intentionally does not write a launch shell script.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    readme = [
        "# HE2 AL-M-T0 Diagnostic Matrix",
        "",
        "- status: `prepared_not_launched`",
        "- launch files written: `false`",
        f"- target family: `{TARGET_LABEL}` / `{TARGET_FAMILY}`",
        f"- source root: `{source_artifact_root}`",
        f"- artifact root: `{artifact_root}`",
        f"- lane scope: `{lane_scope}`",
        f"- experiment scope: `{experiment_scope}`",
        f"- lanes: `{len(rows)}`",
        f"- discount spec id: `{spec['spec_id']}`",
        f"- requires user discount decision: `{bool(spec.get('requires_user_discount_decision', False))}`",
        "",
        "The configs are single-quantile, fit-only diagnostics. They preserve outputs if eventually launched so that",
        "`E[s_t]`, `E[u_t]`, sigma, state norms, forecast covariance, and post-save Cholesky failures can be inspected.",
        "",
        "## Files",
        "",
        "- `diagnostic_matrix_plan.csv`",
        "- `diagnostic_config_manifest.csv`",
        "- `matrix_plan.csv`",
        "- `diagnostic_matrix_metadata.yaml`",
        "- `NO_LAUNCH_GUARD.txt`",
    ]
    (matrix_dir / "README.md").write_text("\n".join(readme) + "\n", encoding="utf-8")
    return metadata


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare AL-M-T0 targeted diagnostic configs without launching.")
    parser.add_argument("--artifact-root", type=Path, default=DEFAULT_ARTIFACT_ROOT)
    parser.add_argument("--source-artifact-root", type=Path, default=SOURCE_ARTIFACT_ROOT)
    parser.add_argument("--discount-spec-yaml", type=Path)
    parser.add_argument("--lane-scope", choices=["representative", "all_failed"], default="representative")
    parser.add_argument("--experiment-scope", choices=["a0", "a1", "a2", "a3", "a4", "ladder"], default="a0")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    metadata = build_package(
        args.artifact_root,
        source_artifact_root=args.source_artifact_root,
        discount_spec_path=args.discount_spec_yaml,
        lane_scope=args.lane_scope,
        experiment_scope=args.experiment_scope,
    )
    print(json.dumps(metadata, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
