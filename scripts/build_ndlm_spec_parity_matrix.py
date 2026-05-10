#!/usr/bin/env python3

from __future__ import annotations

import csv
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path("/data/muscat_data/jaguir26/project1_ucsc_phd")
FEATURECOV_ROOT = Path(
    "/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/"
    "multimodel_v8_featurecov_cf1_eps_sweep_20260416"
)
PHASE2_LABEL_MAPPING_CSV = REPO_ROOT / "reports" / "ndlm_parity_audit" / "label_mapping_check.csv"
OUTPUT_DIR = REPO_ROOT / "reports" / "ndlm_parity_audit"
CSV_OUT = OUTPUT_DIR / "spec_parity_matrix.csv"
MD_OUT = OUTPUT_DIR / "spec_parity_summary.md"

RUN_ROOT_CANDIDATES = [
    (
        "baseline_20260402",
        Path("/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_20260402/runs"),
    ),
    (
        "ndlm_relaunch_20260411",
        Path("/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_ndlm_20260411/runs"),
    ),
    (
        "featurecov_cf1_eps_sweep",
        FEATURECOV_ROOT / "runs",
    ),
]

CUTOFFS = ["20210123", "20211112", "20211221", "20220511", "20221225"]

MODEL_SPECS = {
    "ndlm_univar_keep": {
        "model_id": "ndlm_univar_synth_keep",
        "family_key": "ndlm_univar",
        "comparison_group": "univar_keep",
        "transfer_mode": "keep",
        "likelihood_family": "normal",
        "manuscript_label": "N-U-T1",
    },
    "exdqlm_univar": {
        "model_id": "exdqlm_univar_synth",
        "family_key": "exdqlm_univar",
        "comparison_group": "univar_keep",
        "transfer_mode": "",
        "likelihood_family": "exal",
        "manuscript_label": "",
    },
    "dqlm_univar_al": {
        "model_id": "dqlm_univar_al_synth",
        "family_key": "exdqlm_univar",
        "comparison_group": "univar_keep",
        "transfer_mode": "",
        "likelihood_family": "al",
        "manuscript_label": "",
    },
    "ndlm_main_drop": {
        "model_id": "ndlm_main_synth_drop",
        "family_key": "ndlm_main",
        "comparison_group": "multivar_drop",
        "transfer_mode": "drop",
        "likelihood_family": "normal",
        "manuscript_label": "N-M-T0",
    },
    "exdqlm_multivar_drop": {
        "model_id": "exdqlm_multivar_synth_drop",
        "family_key": "exdqlm_multivar",
        "comparison_group": "multivar_drop",
        "transfer_mode": "drop",
        "likelihood_family": "exal",
        "manuscript_label": "",
    },
    "dqlm_multivar_al_drop": {
        "model_id": "dqlm_multivar_al_synth_drop",
        "family_key": "exdqlm_multivar",
        "comparison_group": "multivar_drop",
        "transfer_mode": "drop",
        "likelihood_family": "al",
        "manuscript_label": "",
    },
    "ndlm_main_keep": {
        "model_id": "ndlm_main_synth_keep",
        "family_key": "ndlm_main",
        "comparison_group": "multivar_keep",
        "transfer_mode": "keep",
        "likelihood_family": "normal",
        "manuscript_label": "N-M-T1",
    },
    "exdqlm_multivar_keep": {
        "model_id": "exdqlm_multivar_synth_keep",
        "family_key": "exdqlm_multivar",
        "comparison_group": "multivar_keep",
        "transfer_mode": "keep",
        "likelihood_family": "exal",
        "manuscript_label": "",
    },
    "dqlm_multivar_al_keep": {
        "model_id": "dqlm_multivar_al_synth_keep",
        "family_key": "exdqlm_multivar",
        "comparison_group": "multivar_keep",
        "transfer_mode": "keep",
        "likelihood_family": "al",
        "manuscript_label": "",
    },
}

COMPARISON_GROUPS = {
    "univar_keep": ["ndlm_univar_keep", "exdqlm_univar", "dqlm_univar_al"],
    "multivar_drop": ["ndlm_main_drop", "exdqlm_multivar_drop", "dqlm_multivar_al_drop"],
    "multivar_keep": ["ndlm_main_keep", "exdqlm_multivar_keep", "dqlm_multivar_al_keep"],
}

FIELDNAMES = [
    "comparison_group",
    "cutoff",
    "model_variant",
    "manuscript_label",
    "model_id",
    "expected_transfer_mode",
    "likelihood_family_expected",
    "selection_class",
    "selection_basis",
    "forecast_window_crps",
    "best_epsilon_label",
    "best_epsilon_value",
    "compare_dir",
    "compare_value",
    "source_type",
    "selected_source_run",
    "selected_source_lineage",
    "selected_source_run_root",
    "resolved_config_path",
    "run_scope",
    "template_source",
    "active_family_key",
    "active_family_enabled",
    "resolved_active_transfer_mode",
    "config_family_default_transfer_mode",
    "config_family_available_transfer_modes",
    "config_supports_expected_transfer_mode",
    "implementation_mode",
    "likelihood_mode_from_config",
    "kalman_backend",
    "horizon_cap",
    "posterior_draws",
    "fit_covariate_names",
    "fit_covariate_count",
    "shared_covariates",
    "transfer_covariate_base",
    "transfer_covariate_engineered_terms",
    "covariate_lag_orders",
    "covariate_include_squares",
    "covariate_include_interaction",
    "deterministic_climate_enabled",
    "det_climate_precip_enabled",
    "det_climate_precip_source",
    "det_climate_precip_reduction",
    "det_climate_precip_noisy_blend_enabled",
    "det_climate_precip_observed_blend_enabled",
    "det_climate_soil_enabled",
    "det_climate_soil_source",
    "det_climate_soil_reduction",
    "det_climate_soil_noisy_blend_enabled",
    "det_climate_soil_observed_blend_enabled",
    "prefer_forecats_snapshot",
    "retros_path",
    "nws_forecast_path",
    "glofas_forecast_path",
    "usgs_mode",
    "state_df_t",
    "state_df_s1",
    "state_df_s2",
    "state_df_s67",
    "state_df_discrep",
    "state_lambda",
    "state_df_trans",
    "state_df_covs",
    "fit_legacy_lam1",
    "fit_legacy_lam2",
    "fit_legacy_use_covariates",
    "fit_legacy_n_samp",
    "fit_legacy_sims_enabled",
    "fit_legacy_forecast_cov_c_factor",
    "fit_legacy_forecast_cov_epsilon",
    "prior_forecast_cov_c_factor",
    "prior_forecast_cov_epsilon",
    "prior_forecast_cov_dof_offset",
    "prior_forecast_cov_scale_mult",
    "prior_forecast_cov_jitter",
    "prior_n0",
    "prior_S0",
    "stabilization_cov_eig_floor",
    "stabilization_cov_eig_cap",
    "stabilization_cov_diag_jitter",
    "stabilization_sigma_upper_cap",
    "stabilization_sigma_update_damping",
    "stabilization_latent_var_cap_mult",
    "stabilization_latent_var_cap_abs",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


@lru_cache(maxsize=None)
def load_yaml(path: str) -> dict[str, Any]:
    with Path(path).open() as handle:
        return yaml.safe_load(handle)


def nested_get(obj: Any, *keys: str, default: Any = "") -> Any:
    cur = obj
    for key in keys:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


def join_list(value: Any) -> str:
    if value in ("", None):
        return ""
    if isinstance(value, list):
        return "|".join(str(item) for item in value)
    return str(value)


def bool_text(value: Any) -> str:
    if value is True:
        return "True"
    if value is False:
        return "False"
    if value in ("yes", "Yes", "no", "No"):
        return "True" if str(value).lower() == "yes" else "False"
    return "" if value in ("", None) else str(value)


def source_lineage_from_run(run_id: str) -> str:
    if not run_id:
        return ""
    for lineage, root in RUN_ROOT_CANDIDATES:
        if (root / run_id / "resolved_config.yaml").exists():
            return lineage
    if "ndlm_tune_20260411" in run_id:
        return "ndlm_relaunch_20260411"
    if "featurecov" in run_id:
        return "featurecov_cf1_eps_sweep"
    return "unknown"


def resolve_source_run(run_id: str) -> tuple[str, str, str]:
    if not run_id:
        return "", "", ""
    for lineage, root in RUN_ROOT_CANDIDATES:
        run_root = root / run_id
        resolved = run_root / "resolved_config.yaml"
        if resolved.exists():
            return lineage, str(run_root), str(resolved)
    return source_lineage_from_run(run_id), "", ""


def compare_report_records() -> dict[tuple[str, str], list[dict[str, Any]]]:
    records: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    wanted_model_ids = {spec["model_id"] for spec in MODEL_SPECS.values()}
    model_variant_by_id = {spec["model_id"]: model_variant for model_variant, spec in MODEL_SPECS.items()}
    for prov_path in sorted(FEATURECOV_ROOT.glob("reports/multimodel_*_compare/source_provenance.csv")):
        compare_dir = prov_path.parent
        parts = compare_dir.name.split("_")
        cutoff = parts[1]
        epsilon_label = parts[3]
        prov_rows = {row["model_id"]: row for row in read_csv(prov_path)}
        crps_rows = {
            row["model_id"]: row
            for row in read_csv(compare_dir / "crps_forecast_summary_all_models.csv")
            if row["model_id"] in wanted_model_ids
        }
        for model_id, crps_row in crps_rows.items():
            prov_row = prov_rows[model_id]
            model_variant = model_variant_by_id[model_id]
            selected_source_run = prov_row.get("selected_source_run", "") or prov_row.get("source_run", "")
            lineage, run_root, resolved_config = resolve_source_run(selected_source_run)
            records[(model_variant, cutoff)].append(
                {
                    "compare_dir": str(compare_dir),
                    "epsilon_label": epsilon_label,
                    "mean_crps": float(crps_row["mean_crps"]),
                    "source_run": prov_row.get("source_run", ""),
                    "source_type": prov_row.get("source_type", ""),
                    "selected_source_run": selected_source_run,
                    "selected_source_lineage": lineage,
                    "selected_source_run_root": run_root,
                    "selected_source_resolved_config": resolved_config,
                }
            )
    return records


def choose_current_record(
    model_variant: str,
    cutoff: str,
    selection_class: str,
    records: dict[tuple[str, str], list[dict[str, Any]]],
) -> dict[str, Any]:
    candidates = records[(model_variant, cutoff)]
    if not candidates:
        raise RuntimeError(f"Missing compare provenance for {model_variant} @ {cutoff}")
    if selection_class == "fixed_baseline":
        return sorted(candidates, key=lambda row: (str(row["compare_dir"]), str(row["selected_source_run"])))[0]
    return min(candidates, key=lambda row: float(row["mean_crps"]))


def active_family_enabled(config: dict[str, Any], family_key: str) -> str:
    flag = nested_get(config, "models", f"run_{family_key}", default="")
    return bool_text(flag)


def config_transfer_support(family_cfg: dict[str, Any], expected_transfer_mode: str) -> str:
    if not expected_transfer_mode:
        return "n/a"
    available = family_cfg.get("forecast_transfer_modes")
    default = family_cfg.get("forecast_transfer_mode")
    if isinstance(available, list):
        return bool_text(expected_transfer_mode in available)
    return bool_text(default == expected_transfer_mode)


def extract_row_fields(base_row: dict[str, Any]) -> dict[str, Any]:
    config = load_yaml(base_row["resolved_config_path"])
    spec = MODEL_SPECS[base_row["model_variant"]]
    family_key = spec["family_key"]
    family_cfg = nested_get(config, "models", family_key, default={}) or {}
    fit_family_cfg = nested_get(config, "fit", family_key, default={}) or {}
    fit_legacy = fit_family_cfg.get("legacy", {}) if isinstance(fit_family_cfg, dict) else {}
    inputs = config.get("inputs", {}) or {}
    deterministic = inputs.get("deterministic_climate", {}) or {}
    transfer_cov = inputs.get("transfer_function_covariates", {}) or {}
    cov_features = inputs.get("covariate_features", {}) or {}
    shared = inputs.get("shared", {}) or {}
    fit_inputs = inputs.get("fit", {}) or {}
    fit_covariates = fit_inputs.get("covariates", []) or []
    prior_forecast_cov = nested_get(family_cfg, "prior", "forecast_cov", default={}) or {}
    stabilization = family_cfg.get("stabilization", {}) or {}
    state = family_cfg.get("state_evolution", {}) or {}
    debug_v8 = config.get("debug_v8_matrix", {}) or {}
    debug_ndlm = config.get("debug_ndlm_campaign", {}) or {}

    row = dict(base_row)
    row.update(
        {
            "run_scope": debug_v8.get("run_scope", ""),
            "template_source": debug_ndlm.get("template_config", "") or debug_v8.get("template_source", ""),
            "active_family_key": family_key,
            "active_family_enabled": active_family_enabled(config, family_key),
            "resolved_active_transfer_mode": debug_ndlm.get("transfer_mode", "") or spec["transfer_mode"],
            "config_family_default_transfer_mode": family_cfg.get("forecast_transfer_mode", ""),
            "config_family_available_transfer_modes": join_list(family_cfg.get("forecast_transfer_modes", "")),
            "config_supports_expected_transfer_mode": config_transfer_support(
                family_cfg, spec["transfer_mode"]
            ),
            "implementation_mode": family_cfg.get("implementation_mode", ""),
            "likelihood_mode_from_config": family_cfg.get("likelihood_mode", "") or spec["likelihood_family"],
            "kalman_backend": family_cfg.get("kalman_backend", ""),
            "horizon_cap": family_cfg.get("horizon_cap", ""),
            "posterior_draws": family_cfg.get("posterior_draws", ""),
            "fit_covariate_names": join_list([item["name"] for item in fit_covariates]),
            "fit_covariate_count": len(fit_covariates),
            "shared_covariates": join_list(inputs.get("shared_covariates", "")),
            "transfer_covariate_base": join_list(transfer_cov.get("base_covariates", "")),
            "transfer_covariate_engineered_terms": join_list(transfer_cov.get("engineered_terms", "")),
            "covariate_lag_orders": join_list(cov_features.get("lag_orders", "")),
            "covariate_include_squares": bool_text(cov_features.get("include_squares", "")),
            "covariate_include_interaction": bool_text(cov_features.get("include_interaction", "")),
            "deterministic_climate_enabled": bool_text(deterministic.get("enabled", "")),
            "det_climate_precip_enabled": bool_text(nested_get(deterministic, "precip", "enabled", default="")),
            "det_climate_precip_source": nested_get(deterministic, "precip", "source", default=""),
            "det_climate_precip_reduction": nested_get(deterministic, "precip", "reduction", default=""),
            "det_climate_precip_noisy_blend_enabled": bool_text(
                nested_get(deterministic, "precip", "noisy_blend", "enabled", default="")
            ),
            "det_climate_precip_observed_blend_enabled": bool_text(
                nested_get(deterministic, "precip", "observed_blend", "enabled", default="")
            ),
            "det_climate_soil_enabled": bool_text(nested_get(deterministic, "soil", "enabled", default="")),
            "det_climate_soil_source": nested_get(deterministic, "soil", "source", default=""),
            "det_climate_soil_reduction": nested_get(deterministic, "soil", "reduction", default=""),
            "det_climate_soil_noisy_blend_enabled": bool_text(
                nested_get(deterministic, "soil", "noisy_blend", "enabled", default="")
            ),
            "det_climate_soil_observed_blend_enabled": bool_text(
                nested_get(deterministic, "soil", "observed_blend", "enabled", default="")
            ),
            "prefer_forecats_snapshot": bool_text(shared.get("prefer_forecats_snapshot", "")),
            "retros_path": fit_inputs.get("retros_path", ""),
            "nws_forecast_path": fit_inputs.get("nws_forecast_path", ""),
            "glofas_forecast_path": fit_inputs.get("glofas_forecast_path", ""),
            "usgs_mode": fit_inputs.get("usgs_mode", ""),
            "state_df_t": state.get("df_t", ""),
            "state_df_s1": state.get("df_s1", ""),
            "state_df_s2": state.get("df_s2", ""),
            "state_df_s67": state.get("df_s67", ""),
            "state_df_discrep": state.get("df_discrep", ""),
            "state_lambda": state.get("lambda", ""),
            "state_df_trans": state.get("df_trans", ""),
            "state_df_covs": state.get("df_covs", ""),
            "fit_legacy_lam1": fit_legacy.get("lam1", ""),
            "fit_legacy_lam2": fit_legacy.get("lam2", ""),
            "fit_legacy_use_covariates": bool_text(fit_legacy.get("use_covariates", "")),
            "fit_legacy_n_samp": fit_legacy.get("n_samp", ""),
            "fit_legacy_sims_enabled": bool_text(fit_legacy.get("sims_enabled", "")),
            "fit_legacy_forecast_cov_c_factor": nested_get(
                fit_legacy, "forecast_cov", "c_factor", default=""
            ),
            "fit_legacy_forecast_cov_epsilon": nested_get(
                fit_legacy, "forecast_cov", "epsilon", default=""
            ),
            "prior_forecast_cov_c_factor": prior_forecast_cov.get("c_factor", ""),
            "prior_forecast_cov_epsilon": prior_forecast_cov.get("epsilon", ""),
            "prior_forecast_cov_dof_offset": prior_forecast_cov.get("dof_offset", ""),
            "prior_forecast_cov_scale_mult": prior_forecast_cov.get("scale_mult", ""),
            "prior_forecast_cov_jitter": prior_forecast_cov.get("jitter", ""),
            "prior_n0": nested_get(family_cfg, "prior", "n0", default=""),
            "prior_S0": nested_get(family_cfg, "prior", "S0", default=""),
            "stabilization_cov_eig_floor": stabilization.get("cov_eig_floor", ""),
            "stabilization_cov_eig_cap": stabilization.get("cov_eig_cap", ""),
            "stabilization_cov_diag_jitter": stabilization.get("cov_diag_jitter", ""),
            "stabilization_sigma_upper_cap": stabilization.get("sigma_upper_cap", ""),
            "stabilization_sigma_update_damping": stabilization.get("sigma_update_damping", ""),
            "stabilization_latent_var_cap_mult": stabilization.get("latent_var_cap_mult", ""),
            "stabilization_latent_var_cap_abs": stabilization.get("latent_var_cap_abs", ""),
        }
    )
    return row


def build_rows() -> list[dict[str, Any]]:
    best_long = {
        (row["model_variant"], row["cutoff"]): row
        for row in read_csv(
            FEATURECOV_ROOT / "reports" / "final_featurecov_cf1_eps_analysis" / "best_by_cutoff_long.csv"
        )
        if row["model_variant"] in MODEL_SPECS
    }
    records = compare_report_records()

    rows: list[dict[str, Any]] = []
    for comparison_group, variants in COMPARISON_GROUPS.items():
        for cutoff in CUTOFFS:
            for model_variant in variants:
                spec = MODEL_SPECS[model_variant]
                summary_row = best_long[(model_variant, cutoff)]
                chosen_record = choose_current_record(model_variant, cutoff, summary_row["class"], records)
                base_row = {
                    "comparison_group": comparison_group,
                    "cutoff": cutoff,
                    "model_variant": model_variant,
                    "manuscript_label": spec["manuscript_label"],
                    "model_id": spec["model_id"],
                    "expected_transfer_mode": spec["transfer_mode"],
                    "likelihood_family_expected": spec["likelihood_family"],
                    "selection_class": summary_row["class"],
                    "selection_basis": summary_row["selection_basis"],
                    "forecast_window_crps": float(summary_row["forecast_window_crps"]),
                    "best_epsilon_label": summary_row["best_epsilon_label"],
                    "best_epsilon_value": summary_row["best_epsilon_value"],
                    "compare_dir": chosen_record["compare_dir"],
                    "compare_value": float(chosen_record["mean_crps"]),
                    "source_type": chosen_record["source_type"],
                    "selected_source_run": chosen_record["selected_source_run"],
                    "selected_source_lineage": chosen_record["selected_source_lineage"],
                    "selected_source_run_root": chosen_record["selected_source_run_root"],
                    "resolved_config_path": chosen_record["selected_source_resolved_config"],
                }
                rows.append(extract_row_fields(base_row))

    rows.sort(key=lambda row: (row["cutoff"], row["comparison_group"], row["model_variant"]))
    return rows


def write_csv(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def write_summary(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    lineage_counts = Counter(row["selected_source_lineage"] for row in rows)
    det_climate_counts = Counter(row["deterministic_climate_enabled"] for row in rows)
    fit_covariate_sets = sorted({row["fit_covariate_names"] for row in rows})
    featurecov_blocks_present = sum(1 for row in rows if row["transfer_covariate_base"])
    prefer_snapshot_counts = Counter(row["prefer_forecats_snapshot"] for row in rows)

    ndlm_main_rows = [row for row in rows if row["model_variant"].startswith("ndlm_main")]
    ndlm_univar_rows = [row for row in rows if row["model_variant"] == "ndlm_univar_keep"]
    multivar_quantile_rows = [
        row for row in rows if row["model_variant"] in {"exdqlm_multivar_keep", "exdqlm_multivar_drop", "dqlm_multivar_al_keep", "dqlm_multivar_al_drop"}
    ]

    ndlm_df_covs = sorted({str(row["state_df_covs"]) for row in ndlm_main_rows})
    quantile_df_covs = sorted({str(row["state_df_covs"]) for row in multivar_quantile_rows})
    ndlm_main_lam_pairs = sorted(
        {(str(row["fit_legacy_lam1"]), str(row["fit_legacy_lam2"])) for row in ndlm_main_rows}
    )
    quantile_lam_pairs = sorted(
        {(str(row["fit_legacy_lam1"]), str(row["fit_legacy_lam2"])) for row in rows if row["model_variant"].startswith(("exdqlm_", "dqlm_"))}
    )
    ndlm_relaunch_rows = [
        row for row in rows if row["selected_source_lineage"] == "ndlm_relaunch_20260411"
    ]

    lines: list[str] = []
    lines.append("# Phase 3 NDLM Specification Parity Summary")
    lines.append("")
    lines.append("Status: complete")
    lines.append("")
    lines.append("## Audit Scope")
    lines.append("")
    lines.append(
        f"- Built a 45-row spec matrix covering `{len(CUTOFFS)}` cutoffs x `3` comparison groups x `3` model variants."
    )
    lines.append(
        "- Comparison groups: `univar_keep`, `multivar_drop`, `multivar_keep`."
    )
    lines.append(
        "- Each row is traced to the authoritative current HE2 source run and its `resolved_config.yaml`."
    )
    lines.append("")
    lines.append("## Headline Findings")
    lines.append("")
    lines.append(
        f"- Source-run lineage is still dominated by the older `multimodel_v8_20260402` tree: `{lineage_counts.get('baseline_20260402', 0)}` of `{len(rows)}` rows. "
        f"Only `{lineage_counts.get('ndlm_relaunch_20260411', 0)}` row comes from the dedicated NDLM relaunch lineage."
    )
    lines.append(
        f"- Deterministic climate is disabled in all authoritative Phase 3 rows (`{det_climate_counts.get('True', 0)}` enabled, `{det_climate_counts.get('False', 0)}` disabled)."
    )
    lines.append(
        f"- All rows share the same fit-covariate set: `{fit_covariate_sets[0]}`."
        if len(fit_covariate_sets) == 1
        else f"- Fit covariate sets are not uniform across rows: {fit_covariate_sets}."
    )
    lines.append(
        f"- The newer featurecov transfer-function blocks (`PPT/SOIL/GDPC-compatibility` with lags and interactions) are absent from all authoritative Phase 3 source configs: `{featurecov_blocks_present}` of `{len(rows)}` rows expose `inputs.transfer_function_covariates`."
    )
    lines.append(
        f"- Snapshot preference differs by lineage: `{prefer_snapshot_counts.get('True', 0)}` rows prefer the older `forecats` snapshot path, while `{prefer_snapshot_counts.get('False', 0)}` rows do not."
    )
    lines.append("")
    lines.append("## NDLM-vs-Quantile Specification Notes")
    lines.append("")
    lines.append(
        f"- NDLM main rows use `state_df_covs` values {', '.join(ndlm_df_covs)}, versus {', '.join(quantile_df_covs)} for the multivariate quantile rows."
    )
    lines.append(
        f"- NDLM main legacy fit damping pairs are {', '.join(f'({a}, {b})' for a, b in ndlm_main_lam_pairs)}, while the quantile rows use {', '.join(f'({a}, {b})' for a, b in quantile_lam_pairs)}. "
        f"The NDLM univariate rows expose no analogous `lam1/lam2` fields in the resolved configs."
    )
    lines.append(
        "- Multivariate exDQLM / DQLM source runs expose both `drop` and `keep` through `forecast_transfer_modes`, whereas NDLM baseline rows separate `keep` and `drop` into distinct source runs."
    )
    lines.append(
        "- In the older multivariate quantile configs, the family-level default `forecast_transfer_mode` is often still `drop` even for HE2 cells that resolve to `keep`; the active `keep` interpretation comes from the compare-layer provenance plus the supported transfer-mode list, not from a keep-only config file."
    )
    if ndlm_relaunch_rows:
        row = ndlm_relaunch_rows[0]
        lines.append(
            "- The one relaunch-backed NDLM row is "
            f"`{row['model_variant']}` at cutoff `{row['cutoff']}`; it carries the stricter relaunch prior fields "
            f"`dof_offset={row['prior_forecast_cov_dof_offset']}`, "
            f"`scale_mult={row['prior_forecast_cov_scale_mult']}`, and "
            f"`jitter={row['prior_forecast_cov_jitter']}`."
        )
    lines.append("")
    lines.append("## Implication For Later Phases")
    lines.append("")
    lines.append(
        "- Phase 4 must compare file-level inputs across these authoritative older source runs before we interpret the NDLM CRPS gap as a modeling result."
    )
    lines.append(
        "- Phase 5 must trace the NDLM main forecast-window covariance prior carefully, because the current HE2 rows mix baseline-TT NDLM runs with one relaunch-tuned NDLM row."
    )
    lines.append("")
    lines.append("## Outputs")
    lines.append("")
    lines.append(f"- CSV: [{CSV_OUT.name}]({CSV_OUT})")
    lines.append("")

    path.write_text("\n".join(lines))


def main() -> None:
    rows = build_rows()
    write_csv(rows, CSV_OUT)
    write_summary(rows, MD_OUT)
    print(f"Wrote {len(rows)} rows to {CSV_OUT}")
    print(f"Wrote summary to {MD_OUT}")


if __name__ == "__main__":
    main()
