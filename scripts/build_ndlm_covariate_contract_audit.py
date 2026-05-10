#!/usr/bin/env python3

from __future__ import annotations

import csv
from collections import Counter
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path("/data/muscat_data/jaguir26/project1_ucsc_phd")
SPEC_PARITY_CSV = REPO_ROOT / "reports" / "ndlm_parity_audit" / "spec_parity_matrix.csv"
REFERENCE_CONFIG_DIR = REPO_ROOT / "config" / "unified_runs_all9_featurecov_20260415"
OUTPUT_DIR = REPO_ROOT / "reports" / "ndlm_parity_audit"
CSV_OUT = OUTPUT_DIR / "covariate_contract_audit.csv"
MD_OUT = OUTPUT_DIR / "blend_contract_audit.md"
REFERENCE_WORKFLOW_DOC = REPO_ROOT / "repro" / "MULTIMODEL_V8_ALL9_FEATURECOV_20260415.md"

MODEL_SPECS = {
    "ndlm_univar_keep": {"family_key": "ndlm_univar", "fit_key": ""},
    "exdqlm_univar": {"family_key": "exdqlm_univar", "fit_key": "exdqlm_univar"},
    "dqlm_univar_al": {"family_key": "exdqlm_univar", "fit_key": "exdqlm_univar"},
    "ndlm_main_drop": {"family_key": "ndlm_main", "fit_key": "ndlm_main"},
    "exdqlm_multivar_drop": {"family_key": "exdqlm_multivar", "fit_key": "exdqlm_multivar"},
    "dqlm_multivar_al_drop": {"family_key": "exdqlm_multivar", "fit_key": "exdqlm_multivar"},
    "ndlm_main_keep": {"family_key": "ndlm_main", "fit_key": "ndlm_main"},
    "exdqlm_multivar_keep": {"family_key": "exdqlm_multivar", "fit_key": "exdqlm_multivar"},
    "dqlm_multivar_al_keep": {"family_key": "exdqlm_multivar", "fit_key": "exdqlm_multivar"},
}

FIELDNAMES = [
    "comparison_group",
    "cutoff",
    "model_variant",
    "manuscript_label",
    "selected_source_run",
    "selected_source_lineage",
    "selected_source_run_root",
    "resolved_config_path",
    "reference_featurecov_config_path",
    "reference_contract_source_doc",
    "authoritative_contract_class",
    "reference_contract_class",
    "authoritative_fit_covariate_names",
    "reference_fit_covariate_names",
    "fit_covariates_match_reference",
    "authoritative_covariate_features_enabled_config",
    "authoritative_covariate_features_output",
    "authoritative_covariate_lag_orders",
    "authoritative_covariate_include_squares",
    "authoritative_covariate_include_interaction",
    "authoritative_covariate_features_runtime_present",
    "authoritative_covariate_features_path",
    "authoritative_covariate_features_summary_present",
    "reference_covariate_features_enabled",
    "reference_covariate_features_output",
    "reference_covariate_lag_orders",
    "reference_covariate_include_squares",
    "reference_covariate_include_interaction",
    "covariate_feature_contract_match",
    "authoritative_deterministic_climate_enabled_config",
    "authoritative_deterministic_climate_runtime_present",
    "authoritative_deterministic_climate_summary_path",
    "authoritative_deterministic_precip_future_present",
    "authoritative_deterministic_soil_future_present",
    "authoritative_det_climate_precip_source",
    "authoritative_det_climate_precip_reduction",
    "authoritative_det_climate_precip_noisy_blend_enabled",
    "authoritative_det_climate_precip_observed_blend_enabled",
    "authoritative_det_climate_soil_source",
    "authoritative_det_climate_soil_reduction",
    "authoritative_det_climate_soil_noisy_blend_enabled",
    "authoritative_det_climate_soil_observed_blend_enabled",
    "reference_deterministic_climate_enabled",
    "reference_deterministic_climate_handoff_root_set",
    "reference_det_climate_precip_source",
    "reference_det_climate_precip_reduction",
    "reference_det_climate_precip_noisy_blend_enabled",
    "reference_det_climate_precip_observed_blend_enabled",
    "reference_det_climate_soil_source",
    "reference_det_climate_soil_reduction",
    "reference_det_climate_soil_noisy_blend_enabled",
    "reference_det_climate_soil_observed_blend_enabled",
    "deterministic_climate_contract_match",
    "blend_rule_contract_match",
    "authoritative_transfer_mode",
    "reference_transfer_mode",
    "transfer_mode_match_reference",
    "authoritative_legacy_use_covariates",
    "reference_legacy_use_covariates",
    "use_covariates_match_reference",
    "overall_featurecov_contract_match",
    "mismatch_notes",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


@lru_cache(maxsize=None)
def load_yaml(path: str) -> dict[str, Any]:
    with Path(path).open() as handle:
        return yaml.safe_load(handle)


def bool_text(value: bool) -> str:
    return "True" if value else "False"


def normalize_list(values: list[Any] | None) -> str:
    if not values:
        return ""
    return "|".join(str(value) for value in values)


def normalize_fit_covariates(config: dict[str, Any]) -> str:
    covariates = config.get("inputs", {}).get("fit", {}).get("covariates", []) or []
    return "|".join(cov["name"] for cov in covariates if cov.get("name"))


def covariate_feature_block(config: dict[str, Any]) -> dict[str, str]:
    block = config.get("inputs", {}).get("covariate_features", {}) or {}
    return {
        "enabled": bool_text(bool(block.get("enabled", False))),
        "output_filename": str(block.get("output_filename", "")),
        "lag_orders": normalize_list(block.get("lag_orders", []) or []),
        "include_squares": bool_text(bool(block.get("include_squares", False))),
        "include_interaction": bool_text(bool(block.get("include_interaction", False))),
    }


def deterministic_climate_block(config: dict[str, Any]) -> dict[str, str]:
    block = config.get("inputs", {}).get("deterministic_climate", {}) or {}
    precip = block.get("precip", {}) or {}
    soil = block.get("soil", {}) or {}
    return {
        "enabled": bool_text(bool(block.get("enabled", False))),
        "handoff_root_set": bool_text(bool(block.get("handoff_root"))),
        "precip_source": str(precip.get("source", "")),
        "precip_reduction": str(precip.get("reduction", "")),
        "precip_noisy_blend_enabled": bool_text(
            bool((precip.get("noisy_blend", {}) or {}).get("enabled", False))
        ),
        "precip_observed_blend_enabled": bool_text(
            bool((precip.get("observed_blend", {}) or {}).get("enabled", False))
        ),
        "soil_source": str(soil.get("source", "")),
        "soil_reduction": str(soil.get("reduction", "")),
        "soil_noisy_blend_enabled": bool_text(
            bool((soil.get("noisy_blend", {}) or {}).get("enabled", False))
        ),
        "soil_observed_blend_enabled": bool_text(
            bool((soil.get("observed_blend", {}) or {}).get("enabled", False))
        ),
    }


def reference_config_path(cutoff: str, model_variant: str) -> Path:
    return REFERENCE_CONFIG_DIR / f"multimodel_{cutoff}_v8_featurecov_v1_{model_variant}.yaml"


def transfer_mode_from_config(config: dict[str, Any], family_key: str) -> str:
    return str((config.get("models", {}).get(family_key, {}) or {}).get("forecast_transfer_mode", ""))


def legacy_use_covariates_from_config(config: dict[str, Any], fit_key: str) -> str:
    if not fit_key:
        return ""
    block = config.get("fit", {}).get(fit_key, {}) or {}
    legacy = block.get("legacy", {}) or {}
    if "use_covariates" not in legacy:
        return ""
    return bool_text(bool(legacy.get("use_covariates")))


def runtime_artifacts(run_root: Path) -> dict[str, str]:
    shared = run_root / "inputs" / "shared"
    cov_dir = shared / "covariates"
    det_dir = shared / "deterministic_climate"
    cov_features = cov_dir / "covariate_features.csv"
    cov_summary = cov_dir / "covariate_features_summary.txt"
    det_summary = det_dir / "deterministic_climate_summary.txt"
    det_precip = det_dir / "deterministic_precip_future.csv"
    det_soil = det_dir / "deterministic_soil_future.csv"
    return {
        "covariate_features_present": bool_text(cov_features.exists()),
        "covariate_features_path": str(cov_features) if cov_features.exists() else "",
        "covariate_features_summary_present": bool_text(cov_summary.exists()),
        "det_summary_present": bool_text(det_summary.exists()),
        "det_summary_path": str(det_summary) if det_summary.exists() else "",
        "det_precip_future_present": bool_text(det_precip.exists()),
        "det_soil_future_present": bool_text(det_soil.exists()),
    }


def classify_contract(
    fit_covariates: str,
    covariate_features_enabled: str,
    deterministic_climate_enabled: str,
) -> str:
    if (
        fit_covariates == "PPT|SOIL|PCA"
        and covariate_features_enabled == "True"
        and deterministic_climate_enabled == "True"
    ):
        return "featurecov_engineered_blended"
    if (
        fit_covariates == "ELI|ONI|PPT|SOIL|PCA"
        and covariate_features_enabled == "False"
        and deterministic_climate_enabled == "False"
    ):
        return "legacy_base_covariates"
    return "mixed_or_partial"


def build_rows() -> list[dict[str, str]]:
    spec_rows = read_csv(SPEC_PARITY_CSV)
    rows: list[dict[str, str]] = []

    for spec_row in spec_rows:
        model_variant = spec_row["model_variant"]
        model_spec = MODEL_SPECS[model_variant]

        authoritative_config = load_yaml(spec_row["resolved_config_path"])
        authoritative_fit_covariates = normalize_fit_covariates(authoritative_config)
        authoritative_cov_features = covariate_feature_block(authoritative_config)
        authoritative_det = deterministic_climate_block(authoritative_config)

        ref_path = reference_config_path(spec_row["cutoff"], model_variant)
        reference_config = load_yaml(str(ref_path))
        reference_fit_covariates = normalize_fit_covariates(reference_config)
        reference_cov_features = covariate_feature_block(reference_config)
        reference_det = deterministic_climate_block(reference_config)

        run_root = Path(spec_row["selected_source_run_root"])
        runtime = runtime_artifacts(run_root)

        authoritative_transfer_mode = spec_row["resolved_active_transfer_mode"]
        reference_transfer_mode = transfer_mode_from_config(reference_config, model_spec["family_key"])
        transfer_mode_match_reference = (
            authoritative_transfer_mode == reference_transfer_mode
            if reference_transfer_mode or authoritative_transfer_mode
            else True
        )

        authoritative_use_covariates = spec_row["fit_legacy_use_covariates"]
        reference_use_covariates = legacy_use_covariates_from_config(reference_config, model_spec["fit_key"])
        use_covariates_match_reference = (
            authoritative_use_covariates == reference_use_covariates
            if reference_use_covariates or authoritative_use_covariates
            else True
        )

        fit_covariates_match_reference = authoritative_fit_covariates == reference_fit_covariates
        covariate_feature_contract_match = (
            authoritative_cov_features["enabled"] == reference_cov_features["enabled"]
            and authoritative_cov_features["output_filename"] == reference_cov_features["output_filename"]
            and authoritative_cov_features["lag_orders"] == reference_cov_features["lag_orders"]
            and authoritative_cov_features["include_squares"] == reference_cov_features["include_squares"]
            and authoritative_cov_features["include_interaction"] == reference_cov_features["include_interaction"]
            and (
                reference_cov_features["enabled"] != "True"
                or runtime["covariate_features_present"] == "True"
            )
        )

        blend_rule_contract_match = (
            authoritative_det["precip_source"] == reference_det["precip_source"]
            and authoritative_det["precip_reduction"] == reference_det["precip_reduction"]
            and authoritative_det["precip_noisy_blend_enabled"]
            == reference_det["precip_noisy_blend_enabled"]
            and authoritative_det["precip_observed_blend_enabled"]
            == reference_det["precip_observed_blend_enabled"]
            and authoritative_det["soil_source"] == reference_det["soil_source"]
            and authoritative_det["soil_reduction"] == reference_det["soil_reduction"]
            and authoritative_det["soil_noisy_blend_enabled"]
            == reference_det["soil_noisy_blend_enabled"]
            and authoritative_det["soil_observed_blend_enabled"]
            == reference_det["soil_observed_blend_enabled"]
        )

        deterministic_climate_contract_match = (
            authoritative_det["enabled"] == reference_det["enabled"]
            and blend_rule_contract_match
            and (
                reference_det["enabled"] != "True"
                or (
                    runtime["det_summary_present"] == "True"
                    and runtime["det_precip_future_present"] == "True"
                    and runtime["det_soil_future_present"] == "True"
                )
            )
        )

        authoritative_contract_class = classify_contract(
            authoritative_fit_covariates,
            authoritative_cov_features["enabled"],
            authoritative_det["enabled"],
        )
        reference_contract_class = classify_contract(
            reference_fit_covariates,
            reference_cov_features["enabled"],
            reference_det["enabled"],
        )

        overall_match = (
            fit_covariates_match_reference
            and covariate_feature_contract_match
            and deterministic_climate_contract_match
            and transfer_mode_match_reference
            and use_covariates_match_reference
        )

        mismatch_notes: list[str] = []
        if not fit_covariates_match_reference:
            mismatch_notes.append(
                f"fit_covariates:{authoritative_fit_covariates}->{reference_fit_covariates}"
            )
        if authoritative_cov_features["enabled"] != reference_cov_features["enabled"]:
            mismatch_notes.append(
                f"covariate_features_enabled:{authoritative_cov_features['enabled']}->{reference_cov_features['enabled']}"
            )
        if runtime["covariate_features_present"] != "True":
            mismatch_notes.append("runtime_missing:covariate_features.csv")
        if authoritative_cov_features["lag_orders"] != reference_cov_features["lag_orders"]:
            mismatch_notes.append(
                f"lag_orders:{authoritative_cov_features['lag_orders']}->{reference_cov_features['lag_orders']}"
            )
        if authoritative_cov_features["include_squares"] != reference_cov_features["include_squares"]:
            mismatch_notes.append(
                f"include_squares:{authoritative_cov_features['include_squares']}->{reference_cov_features['include_squares']}"
            )
        if authoritative_cov_features["include_interaction"] != reference_cov_features["include_interaction"]:
            mismatch_notes.append(
                "include_interaction:"
                f"{authoritative_cov_features['include_interaction']}->{reference_cov_features['include_interaction']}"
            )
        if authoritative_det["enabled"] != reference_det["enabled"]:
            mismatch_notes.append(
                f"deterministic_climate_enabled:{authoritative_det['enabled']}->{reference_det['enabled']}"
            )
        if runtime["det_summary_present"] != "True":
            mismatch_notes.append("runtime_missing:deterministic_climate_summary.txt")
        if authoritative_det["precip_source"] != reference_det["precip_source"]:
            mismatch_notes.append(
                f"precip_source:{authoritative_det['precip_source']}->{reference_det['precip_source']}"
            )
        if authoritative_det["soil_source"] != reference_det["soil_source"]:
            mismatch_notes.append(
                f"soil_source:{authoritative_det['soil_source']}->{reference_det['soil_source']}"
            )
        if not transfer_mode_match_reference:
            mismatch_notes.append(
                f"transfer_mode:{authoritative_transfer_mode}->{reference_transfer_mode}"
            )
        if not use_covariates_match_reference:
            mismatch_notes.append(
                f"use_covariates:{authoritative_use_covariates}->{reference_use_covariates}"
            )

        rows.append(
            {
                "comparison_group": spec_row["comparison_group"],
                "cutoff": spec_row["cutoff"],
                "model_variant": model_variant,
                "manuscript_label": spec_row["manuscript_label"],
                "selected_source_run": spec_row["selected_source_run"],
                "selected_source_lineage": spec_row["selected_source_lineage"],
                "selected_source_run_root": spec_row["selected_source_run_root"],
                "resolved_config_path": spec_row["resolved_config_path"],
                "reference_featurecov_config_path": str(ref_path),
                "reference_contract_source_doc": str(REFERENCE_WORKFLOW_DOC),
                "authoritative_contract_class": authoritative_contract_class,
                "reference_contract_class": reference_contract_class,
                "authoritative_fit_covariate_names": authoritative_fit_covariates,
                "reference_fit_covariate_names": reference_fit_covariates,
                "fit_covariates_match_reference": bool_text(fit_covariates_match_reference),
                "authoritative_covariate_features_enabled_config": authoritative_cov_features["enabled"],
                "authoritative_covariate_features_output": authoritative_cov_features["output_filename"],
                "authoritative_covariate_lag_orders": authoritative_cov_features["lag_orders"],
                "authoritative_covariate_include_squares": authoritative_cov_features["include_squares"],
                "authoritative_covariate_include_interaction": authoritative_cov_features["include_interaction"],
                "authoritative_covariate_features_runtime_present": runtime["covariate_features_present"],
                "authoritative_covariate_features_path": runtime["covariate_features_path"],
                "authoritative_covariate_features_summary_present": runtime[
                    "covariate_features_summary_present"
                ],
                "reference_covariate_features_enabled": reference_cov_features["enabled"],
                "reference_covariate_features_output": reference_cov_features["output_filename"],
                "reference_covariate_lag_orders": reference_cov_features["lag_orders"],
                "reference_covariate_include_squares": reference_cov_features["include_squares"],
                "reference_covariate_include_interaction": reference_cov_features[
                    "include_interaction"
                ],
                "covariate_feature_contract_match": bool_text(covariate_feature_contract_match),
                "authoritative_deterministic_climate_enabled_config": authoritative_det["enabled"],
                "authoritative_deterministic_climate_runtime_present": runtime["det_summary_present"],
                "authoritative_deterministic_climate_summary_path": runtime["det_summary_path"],
                "authoritative_deterministic_precip_future_present": runtime[
                    "det_precip_future_present"
                ],
                "authoritative_deterministic_soil_future_present": runtime["det_soil_future_present"],
                "authoritative_det_climate_precip_source": authoritative_det["precip_source"],
                "authoritative_det_climate_precip_reduction": authoritative_det[
                    "precip_reduction"
                ],
                "authoritative_det_climate_precip_noisy_blend_enabled": authoritative_det[
                    "precip_noisy_blend_enabled"
                ],
                "authoritative_det_climate_precip_observed_blend_enabled": authoritative_det[
                    "precip_observed_blend_enabled"
                ],
                "authoritative_det_climate_soil_source": authoritative_det["soil_source"],
                "authoritative_det_climate_soil_reduction": authoritative_det["soil_reduction"],
                "authoritative_det_climate_soil_noisy_blend_enabled": authoritative_det[
                    "soil_noisy_blend_enabled"
                ],
                "authoritative_det_climate_soil_observed_blend_enabled": authoritative_det[
                    "soil_observed_blend_enabled"
                ],
                "reference_deterministic_climate_enabled": reference_det["enabled"],
                "reference_deterministic_climate_handoff_root_set": reference_det[
                    "handoff_root_set"
                ],
                "reference_det_climate_precip_source": reference_det["precip_source"],
                "reference_det_climate_precip_reduction": reference_det["precip_reduction"],
                "reference_det_climate_precip_noisy_blend_enabled": reference_det[
                    "precip_noisy_blend_enabled"
                ],
                "reference_det_climate_precip_observed_blend_enabled": reference_det[
                    "precip_observed_blend_enabled"
                ],
                "reference_det_climate_soil_source": reference_det["soil_source"],
                "reference_det_climate_soil_reduction": reference_det["soil_reduction"],
                "reference_det_climate_soil_noisy_blend_enabled": reference_det[
                    "soil_noisy_blend_enabled"
                ],
                "reference_det_climate_soil_observed_blend_enabled": reference_det[
                    "soil_observed_blend_enabled"
                ],
                "deterministic_climate_contract_match": bool_text(
                    deterministic_climate_contract_match
                ),
                "blend_rule_contract_match": bool_text(blend_rule_contract_match),
                "authoritative_transfer_mode": authoritative_transfer_mode,
                "reference_transfer_mode": reference_transfer_mode,
                "transfer_mode_match_reference": bool_text(transfer_mode_match_reference),
                "authoritative_legacy_use_covariates": authoritative_use_covariates,
                "reference_legacy_use_covariates": reference_use_covariates,
                "use_covariates_match_reference": bool_text(use_covariates_match_reference),
                "overall_featurecov_contract_match": bool_text(overall_match),
                "mismatch_notes": "; ".join(mismatch_notes),
            }
        )

    rows.sort(
        key=lambda row: (
            row["cutoff"],
            row["comparison_group"],
            row["model_variant"],
        )
    )
    return rows


def write_csv(rows: list[dict[str, str]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def write_summary(rows: list[dict[str, str]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    overall_matches = sum(1 for row in rows if row["overall_featurecov_contract_match"] == "True")
    fit_cov_matches = sum(1 for row in rows if row["fit_covariates_match_reference"] == "True")
    cov_feature_matches = sum(
        1 for row in rows if row["covariate_feature_contract_match"] == "True"
    )
    det_matches = sum(
        1 for row in rows if row["deterministic_climate_contract_match"] == "True"
    )
    transfer_matches = sum(
        1 for row in rows if row["transfer_mode_match_reference"] == "True"
    )
    use_cov_matches = sum(
        1 for row in rows if row["use_covariates_match_reference"] == "True"
    )
    runtime_cov_features = sum(
        1 for row in rows if row["authoritative_covariate_features_runtime_present"] == "True"
    )
    runtime_det = sum(
        1 for row in rows if row["authoritative_deterministic_climate_runtime_present"] == "True"
    )
    authoritative_contract_counts = Counter(
        row["authoritative_contract_class"] for row in rows
    )
    reference_contract_counts = Counter(row["reference_contract_class"] for row in rows)
    fit_cov_sets = Counter(row["authoritative_fit_covariate_names"] for row in rows)
    reference_fit_cov_sets = Counter(row["reference_fit_covariate_names"] for row in rows)
    by_variant = Counter(
        row["model_variant"] for row in rows if row["overall_featurecov_contract_match"] == "True"
    )

    lines: list[str] = []
    lines.append("# Phase 6 NDLM Transfer / Blend Contract Audit")
    lines.append("")
    lines.append("Status: complete")
    lines.append("")
    lines.append("## Audit Scope")
    lines.append("")
    lines.append(
        f"- Audited `{len(rows)}` authoritative HE2 comparison rows against the intended all-9 featurecov contract."
    )
    lines.append(
        f"- Reference contract documented in [{REFERENCE_WORKFLOW_DOC.name}]({REFERENCE_WORKFLOW_DOC})."
    )
    lines.append(
        "- This phase compares the current manuscript-facing rows against the intended shared featurecov design, not just against each other."
    )
    lines.append("")
    lines.append("## Headline Findings")
    lines.append("")
    lines.append(
        f"- End-to-end featurecov contract matches: `{overall_matches} / {len(rows)}`."
    )
    lines.append(
        f"- Fit-covariate list matches: `{fit_cov_matches} / {len(rows)}`."
    )
    lines.append(
        f"- Engineered covariate-feature contract matches: `{cov_feature_matches} / {len(rows)}`."
    )
    lines.append(
        f"- Deterministic-climate / blend contract matches: `{det_matches} / {len(rows)}`."
    )
    lines.append(
        f"- Transfer-mode semantics still match: `{transfer_matches} / {len(rows)}`."
    )
    lines.append(
        f"- Legacy `use_covariates` semantics still match where exposed: `{use_cov_matches} / {len(rows)}`."
    )
    lines.append(
        f"- Authoritative runtime rows carrying `covariate_features.csv`: `{runtime_cov_features} / {len(rows)}`."
    )
    lines.append(
        f"- Authoritative runtime rows carrying `deterministic_climate_summary.txt`: `{runtime_det} / {len(rows)}`."
    )
    lines.append("")
    lines.append("## Contract Classification")
    lines.append("")
    lines.append("Authoritative manuscript-facing rows:")
    for contract_class, count in sorted(authoritative_contract_counts.items()):
        lines.append(f"- `{contract_class}`: `{count}` rows")
    lines.append("")
    lines.append("Reference all-9 featurecov rows:")
    for contract_class, count in sorted(reference_contract_counts.items()):
        lines.append(f"- `{contract_class}`: `{count}` rows")
    lines.append("")
    lines.append("## Specific Interpretation")
    lines.append("")
    lines.append(
        "- The current authoritative HE2 rows are internally aligned to an older simpler covariate contract, not the newer featurecov contract."
    )
    lines.append(
        f"- Authoritative fit covariates are `{', '.join(sorted(fit_cov_sets))}`."
    )
    lines.append(
        f"- Intended featurecov fit covariates are `{', '.join(sorted(reference_fit_cov_sets))}`."
    )
    lines.append(
        "- In the intended featurecov workflow, the reduced `PPT/SOIL/GDPC-compatibility` inputs are expanded through `covariate_features.csv` and deterministic-climate forecast substitution."
    )
    lines.append(
        "- The generated all-9 featurecov configs express that contract through reduced fit covariates, `inputs.covariate_features`, and `inputs.deterministic_climate`; they do not need a separate `transfer_function_covariates` key to enforce it."
    )
    lines.append(
        "- The authoritative manuscript-facing rows do not carry those runtime artifacts, so they are not using the lagged, squared, interaction-based feature matrix or the GEFS q85 blend contract now documented for the all-9 relaunch."
    )
    lines.append(
        "- This means the current NDLM-versus-quantile comparison is not yet a comparison under the newer shared featurecov specification."
    )
    lines.append(
        "- The main discrepancy in this phase is therefore not transfer-mode wiring. Keep/drop activation and `use_covariates` semantics remain aligned. The discrepancy is the broader covariate and forecast-blend contract."
    )
    lines.append("")
    lines.append("## Bottom Line")
    lines.append("")
    lines.append(
        "- Phase 6 supports a narrower diagnosis: the poor NDLM CRPS values are not explained by mislabeled transfer modes, but the current manuscript-facing rows are still anchored in a pre-featurecov covariate regime."
    )
    lines.append(
        "- To claim a true likelihood-only comparison under the new article specification, later phases must either reproduce all families under the shared featurecov/blended-forecast contract or formally constrain the claims to the older contract."
    )
    if by_variant:
        lines.append("")
        lines.append("Rows already matching the intended featurecov contract by variant:")
        for model_variant, count in sorted(by_variant.items()):
            lines.append(f"- `{model_variant}`: `{count}`")

    path.write_text("\n".join(lines) + "\n")


def main() -> None:
    rows = build_rows()
    write_csv(rows, CSV_OUT)
    write_summary(rows, MD_OUT)
    print(f"Wrote {len(rows)} rows to {CSV_OUT}")
    print(f"Wrote summary to {MD_OUT}")


if __name__ == "__main__":
    main()
