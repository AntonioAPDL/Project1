#!/usr/bin/env python3
"""Export a clean public reproducibility repository for the Environmetrics paper.

This script is intentionally allowlist-based. It creates a reader-facing repo
with compact staged inputs, manuscript-facing outputs, provenance, and selected
workflow code without copying raw climate archives, active runtime campaigns, or
large local research artifacts.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import subprocess
import textwrap
from dataclasses import dataclass
from pathlib import Path

import yaml


REPO_NAME = "san-lorenzo-exdqlm-reproducibility"
PUBLIC_URL = f"https://github.com/AntonioAPDL/{REPO_NAME}"
ARTICLE_DIR_NAME = "Evironmetrics---REVISED-DOC-Corrected-2"
SHARED_INPUT_BUNDLE = "multimodel_v8_he2_publication_shared_inputs_20260510"

FORBIDDEN_SUFFIXES = {
    ".RData",
    ".rda",
    ".rdata",
    ".nc",
    ".grib",
    ".grib2",
    ".zarr",
    ".pkl",
    ".pickle",
    ".parquet",
    ".feather",
    ".h5",
    ".hdf5",
}

TEXT_SUFFIXES = {
    ".R",
    ".Rmd",
    ".bib",
    ".bst",
    ".cff",
    ".cls",
    ".csv",
    ".html",
    ".htm",
    ".json",
    ".md",
    ".py",
    ".sh",
    ".sty",
    ".tex",
    ".txt",
    ".yaml",
    ".yml",
}
TEXT_FILENAMES = {"Makefile", "LICENSE", ".gitignore"}

WORKFLOW_DOCS = [
    "README.md",
    "CITATION.cff",
    "docs/software_reproducibility_release_plan_20260615.md",
    "docs/workflow_archive_readiness_20260615.md",
    "docs/he6_out_of_sample_forecast_design_contract_20260615.md",
    "docs/he7_latest_forecast_issue_contract_20260615.md",
    "docs/publication_freeze_validation_20260614.md",
    "repro/run/REVISION_SOFTWARE_REPRODUCIBILITY_CONTRACT_20260615.md",
]

ARTICLE_DOCS = [
    "README.md",
    "MANUSCRIPT_ASSET_MANIFEST.json",
    "artifacts/artifact_inventory.csv",
    "docs/figure_table_provenance.md",
    "docs/forecast_design_contract.md",
    "docs/latest_forecast_issue_contract.md",
    "docs/software_availability_contract.md",
    "docs/exal_m_t1_artifact_run_map.md",
]

CONFIG_FILES = [
    "config/post_publication_figures.yaml",
]

SCRIPT_FILES = [
    "scripts/unified_run.R",
    "scripts/run_environmetrics_figures.R",
    "scripts/make_environmetrics_figures.R",
]

TEST_FILES = [
    "tests/testthat/test_post_crps_tables.R",
    "tests/testthat/test_post_posterior_table_exports.R",
    "tests/testthat/test_post_quantile_synthesis_rearrangement.R",
]

ARTICLE_ARTIFACT_DIRS = [
    "artifacts/five_cutoff_crps_validation_sources",
    "artifacts/five_cutoff_main_model_synthesis",
    "artifacts/five_cutoff_reference_synthesis",
    "artifacts/five_cutoff_setup_support",
    "artifacts/forecast_design",
    "artifacts/he2_publication_freeze",
    "artifacts/he3_exdqlm_ablation_authoritative",
    "artifacts/he4_quantile_check_loss_current_publication",
    "artifacts/historical_support_from_current_models",
    "artifacts/latest_forecast_issue",
    "artifacts/representative_selected_model_2022_12_25",
    "artifacts/runtime_benchmark",
    "artifacts/software_availability",
]

FORECAST_COVARIATE_PUBLIC_NOTE = {
    "public_scope": (
        "Forecast-window precipitation and shallow soil-water covariates are "
        "included as deterministic, model-ready summaries derived from "
        "post-processed GEFS forecast products. Raw GEFS retrieval, recovery, "
        "and intermediate covariate-construction details are not bundled in "
        "this public reproducibility repository."
    )
}

REDACTED_JSON_KEYS = {
    "handoff_root",
    "summary_path",
    "summary_sha256",
    "manifest_summary_sha256",
    "manifest_summary_sha_match",
    "current",
    "summary",
    "canonical",
    "validation",
    "compare_report_path",
}

REDACTED_JSON_KEY_FRAGMENTS = (
    "noisy_blend",
    "observed_blend",
    "tail_blend",
    "noise_seed",
    "noise_sd",
    "noise_distribution",
    "observed_weight",
    "observed_zero_stay",
)

PUBLIC_TEXT_NORMALIZATIONS = (
    ("histfix", "long_history_support"),
    ("Histfix", "Long-history support"),
    ("HISTFIX", "LONG_HISTORY_SUPPORT"),
    ("legacy_log_ready_repairs", "log_scale_support_checks"),
    ("selected_window_splice", "selected_window_alignment"),
    ("best_epsilon_label", "forecast_covariance_prior_label"),
    ("best_epsilon_value", "forecast_covariance_prior_weight"),
    ("selected_epsilon_label", "forecast_covariance_prior_label"),
    ("selected_epsilon", "forecast_covariance_prior_weight"),
    ("provenance_selected_epsilon", "provenance_forecast_covariance_prior_weight"),
    ("source_epsilon_label", "source_forecast_covariance_prior_label"),
    ("matrix_epsilon", "source_forecast_covariance_prior_setting"),
    ("runner_up_grid_spec_id", "comparison_profile_id"),
    ("runner_up_mean_crps", "comparison_mean_crps"),
    ("winner_runner_abs_diff", "comparison_abs_diff"),
    ("epsilon/discount screening checkpoint", "selected-output refresh"),
    ("epsilon_discount_grid", "selected_specifications"),
    ("discount_grid", "selected_specifications"),
    ("canonical-grid", "selected-output"),
    ("canonical_grid", "selected_output"),
    ("partial-screen", "selected-output"),
    ("partial_screen", "selected_output"),
    ("clean_screen_replay", "selected_output_replay"),
    ("clean screen replay", "selected-output replay"),
    ("screening checkpoint", "selected-output checkpoint"),
    ("screening", "internal exploratory"),
    ("generated screening/audit outputs", "internal exploratory outputs"),
    ("blended-covariate", "forecast-covariate"),
    ("blended covariate", "forecast-covariate"),
    ("blended_covariate", "forecast_covariate"),
    ("blending internals", "forecast-covariate internals"),
    ("blending", "forecast-covariate construction"),
)

PUBLIC_CSV_FIELD_RENAMES = {
    "grid_spec_id": "selected_profile_id",
    "synthesis_grid_spec_id": "synthesis_selected_profile_id",
    "discount_case_id": "state_evolution_profile_id",
    "epsilon_label": "forecast_covariance_prior_label",
    "epsilon_value": "forecast_covariance_prior_weight",
    "best_epsilon_label": "forecast_covariance_prior_label",
    "best_epsilon_value": "forecast_covariance_prior_weight",
    "selected_epsilon": "forecast_covariance_prior_weight",
    "selected_epsilon_label": "forecast_covariance_prior_label",
    "provenance_selected_epsilon": "provenance_forecast_covariance_prior_weight",
    "provenance_selected_source_run": "provenance_selected_output",
    "provenance_selected_source_run_id": "provenance_selected_output_id",
    "source_epsilon_label": "source_forecast_covariance_prior_label",
    "matrix_epsilon": "source_forecast_covariance_prior_setting",
    "runner_up_grid_spec_id": "comparison_profile_id",
    "runner_up_mean_crps": "comparison_mean_crps",
    "winner_runner_abs_diff": "comparison_abs_diff",
}

PUBLIC_METADATA_PREFIXES_FOR_EXPORT = (
    "README.md",
    "CITATION.cff",
    "LICENSE",
    "Makefile",
    "config/",
    "data/",
    "manuscript/",
    "outputs/",
    "provenance/",
    "tables/",
)


@dataclass(frozen=True)
class Roots:
    workflow: Path
    article: Path
    runtime: Path
    destination: Path


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text).lstrip(), encoding="utf-8")


def local_path_replacements(roots: Roots) -> tuple[tuple[str, str], ...]:
    return (
        ("https://github.com/AntonioAPDL/" + "Project1", PUBLIC_URL),
        ((roots.runtime / SHARED_INPUT_BUNDLE).as_posix(), "STAGED_INPUT_BUNDLE_ROOT"),
        (roots.article.as_posix(), "SOURCE_ARTICLE_ROOT"),
        (roots.runtime.as_posix(), "SOURCE_RUNTIME_ROOT"),
        (roots.workflow.as_posix(), "SOURCE_WORKFLOW_ROOT"),
        (roots.destination.as_posix(), "PUBLIC_REPRO_ROOT"),
        ("/data/muscat_data/jaguir26/Corrections---Project-1", "SOURCE_CORRECTIONS_ROOT"),
        ("/data/muscat_data/jaguir26/projects/Project/Input/exAL", "LEGACY_EXAL_INPUT_ROOT"),
        ("/data/muscat_data/jaguir26/projects/Project", "LEGACY_PROJECT_ROOT"),
        ("/data/muscat_data/jaguir26/libs", "LOCAL_RCPP_LIB_ROOT"),
        ("/data/jaguir26/local/src", "EXTERNAL_RUNTIME_SOURCE_ROOT"),
        ("Owner: Codex + Antonio", "Owner: Antonio"),
    )


def is_text_like(path: Path) -> bool:
    return path.suffix in TEXT_SUFFIXES or path.name in TEXT_FILENAMES


def sanitize_public_text_file(path: Path, replacements: tuple[tuple[str, str], ...]) -> None:
    if not is_text_like(path):
        return
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return
    original = text
    for old, new in replacements:
        text = text.replace(old, new)
    if text != original:
        path.write_text(text, encoding="utf-8")


def apply_replacements(text: str, replacements: tuple[tuple[str, str], ...]) -> str:
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def sanitize_public_field_name(name: str) -> str:
    return PUBLIC_CSV_FIELD_RENAMES.get(
        apply_replacements(name, PUBLIC_TEXT_NORMALIZATIONS),
        apply_replacements(name, PUBLIC_TEXT_NORMALIZATIONS),
    )


def sanitize_public_lineage_text(text: str) -> str:
    """Neutralize private campaign labels while preserving scientific values."""

    text = apply_replacements(text, PUBLIC_TEXT_NORMALIZATIONS)
    regex_replacements = (
        (
            r"multimodel_(\d{8})_v8_he2grid_c\d{2}_eps\d{3}_([A-Za-z0-9_]+)",
            r"selected_model_\1_\2",
        ),
        (
            r"multimodel_(\d{8})_v8_c\d{2}_eps\d{3}_([A-Za-z0-9_]+)",
            r"selected_model_\1_\2",
        ),
        (
            r"multimodel_(\d{8})_v8_exalm_t1_discount_grid_exact_v1_set\d+_([A-Za-z0-9_]+)",
            r"selected_model_\1_\2",
        ),
        (
            r"multimodel_(\d{8})_v8_eps\d+(?:cf\d+)?_([A-Za-z0-9_]+)",
            r"selected_model_\1_\2",
        ),
        (
            r"multimodel_(\d{8})_v8_he2partial20260623_([A-Za-z0-9_]+)",
            r"selected_model_\1_\2",
        ),
        (r"\bc\d{2}_eps\d{3}\b", "selected_profile"),
        (r"\beps\d+(?:cf\d+)?\b", "forecast_covariance_prior"),
        (
            r"\bexalm_t1_discount_grid_exact_20260424:set09_override\b",
            "exal_m_t1_selected_output_reference",
        ),
        (
            r"\bfeaturecov_cf1_eps_sweep_20260416\b",
            "featurecov_selected_output_reference",
        ),
    )
    for pattern, replacement in regex_replacements:
        text = re.sub(pattern, replacement, text)
    return text


def compact_placeholder_paths(text: str) -> str:
    """Remove machine/run-specific path tails after public placeholders."""

    patterns = (
        (r"SOURCE_RUNTIME_ROOT/[^\s,\"'\]\)]+", "SOURCE_RUNTIME_REFERENCE"),
        (r"SOURCE_WORKFLOW_ROOT/[^\s,\"'\]\)]+", "SOURCE_WORKFLOW_REFERENCE"),
        (r"SOURCE_ARTICLE_ROOT/[^\s,\"'\]\)]+", "SOURCE_ARTICLE_REFERENCE"),
        (r"SOURCE_CORRECTIONS_ROOT/[^\s,\"'\]\)]+", "SOURCE_CORRECTIONS_REFERENCE"),
        (r"STAGED_INPUT_BUNDLE_ROOT/[^\s,\"'\]\)]+", "STAGED_INPUT_REFERENCE"),
        (r"LEGACY_EXAL_INPUT_ROOT/[^\s,\"'\]\)]+", "LEGACY_EXAL_INPUT_REFERENCE"),
        (r"LEGACY_PROJECT_ROOT/[^\s,\"'\]\)]+", "LEGACY_PROJECT_REFERENCE"),
        (r"LOCAL_RCPP_LIB_ROOT/[^\s,\"'\]\)]+", "LOCAL_RCPP_LIB_REFERENCE"),
        (r"EXTERNAL_RUNTIME_SOURCE_ROOT/[^\s,\"'\]\)]+", "EXTERNAL_RUNTIME_SOURCE_REFERENCE"),
    )
    for pattern, replacement in patterns:
        text = re.sub(pattern, replacement, text)
    return text


def redact_json_for_public(obj):
    if isinstance(obj, dict):
        redacted = {}
        for key, value in obj.items():
            lower_key = key.lower()
            public_key = sanitize_public_field_name(key)
            if lower_key == "deterministic_climate":
                redacted[public_key] = FORECAST_COVARIATE_PUBLIC_NOTE
                continue
            if key in REDACTED_JSON_KEYS:
                continue
            if any(fragment in lower_key for fragment in REDACTED_JSON_KEY_FRAGMENTS):
                continue
            redacted[public_key] = redact_json_for_public(value)
        return redacted
    if isinstance(obj, list):
        return [redact_json_for_public(value) for value in obj]
    if isinstance(obj, str):
        return sanitize_public_lineage_text(
            apply_replacements(compact_placeholder_paths(obj), PUBLIC_TEXT_NORMALIZATIONS)
        )
    return obj


def redact_csv_for_public(path: Path) -> bool:
    try:
        with path.open(newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            if reader.fieldnames is None:
                return False
            rows = list(reader)
    except (csv.Error, UnicodeDecodeError):
        return False

    changed = False
    fieldnames = [sanitize_public_field_name(name) for name in reader.fieldnames]
    note_json = json.dumps(FORECAST_COVARIATE_PUBLIC_NOTE, sort_keys=True)
    sanitized_rows = []
    for row in rows:
        sanitized_row = {}
        for key, value in list(row.items()):
            public_key = sanitize_public_field_name(key)
            if value is None:
                sanitized_row[public_key] = value
                continue
            lower_key = key.lower()
            lower_value = value.lower()
            new_value = value
            if lower_key == "deterministic_climate_json":
                new_value = note_json
            elif lower_key == "source_zip":
                new_value = "SOURCE_ARCHIVE_SHARD_REFERENCE"
            elif "handoff_forecasts" in lower_value or "source_native_tranche" in lower_value:
                new_value = "SOURCE_ARCHIVE_REFERENCE"
            else:
                new_value = compact_placeholder_paths(value)
            new_value = sanitize_public_lineage_text(new_value)
            if new_value != value:
                changed = True
            sanitized_row[public_key] = new_value
            if public_key != key:
                changed = True
        sanitized_rows.append(sanitized_row)

    if changed:
        with path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames, lineterminator="\n")
            writer.writeheader()
            writer.writerows(sanitized_rows)
    return changed


def curate_public_metadata(roots: Roots, replacements: tuple[tuple[str, str], ...]) -> None:
    for path in sorted(roots.destination.rglob("*")):
        if not path.is_file() or ".git" in path.parts:
            continue
        relpath = path.relative_to(roots.destination).as_posix()
        if path.suffix == ".json":
            try:
                obj = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                obj = None
            if obj is not None:
                redacted = redact_json_for_public(obj)
                path.write_text(json.dumps(redacted, indent=2, sort_keys=True) + "\n", encoding="utf-8")
                continue
        if path.suffix == ".csv":
            redact_csv_for_public(path)
        if is_text_like(path):
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            updated = compact_placeholder_paths(apply_replacements(text, replacements))
            if relpath.startswith(PUBLIC_METADATA_PREFIXES_FOR_EXPORT):
                updated = sanitize_public_lineage_text(updated)
            else:
                updated = apply_replacements(updated, PUBLIC_TEXT_NORMALIZATIONS)
            if updated != text:
                path.write_text(updated, encoding="utf-8")


def count_csv_rows_and_columns(path: Path) -> tuple[int, int, str | None, str | None]:
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        header = next(reader)
        first = None
        last = None
        rows = 0
        for row in reader:
            if not row:
                continue
            rows += 1
            if first is None:
                first = row[0]
            last = row[0]
    return rows, len(header), first, last


def write_compact_origin_metadata(roots: Roots) -> None:
    origins = roots.destination / "data/staged/forecast_origins"
    for origin_dir in sorted(origins.glob("cutoff_*")):
        if not origin_dir.is_dir():
            continue
        cutoff = origin_dir.name.removeprefix("cutoff_")
        cutoff_date = cutoff.replace("_", "-")
        retros_rows, retros_cols, retros_start, retros_end = count_csv_rows_and_columns(
            origin_dir / "retrospective_products_daily.csv"
        )
        glofas_rows, glofas_cols, _, _ = count_csv_rows_and_columns(origin_dir / "glofas_ensemble_forecast_daily.csv")
        nws_rows, nws_cols, _, _ = count_csv_rows_and_columns(origin_dir / "nws_ensemble_forecast_daily.csv")
        glofas_members = max(glofas_cols - 1, 0)
        nws_members = max(nws_cols - 1, 0)

        write_text(
            origin_dir / "origin_metadata.yaml",
            f"""
            schema_version: public_forecast_origin_bundle_v1
            cutoff: "{cutoff.replace("_", "")}"
            cutoff_date: "{cutoff_date}"
            site:
              usgs_site: "11160500"
              river: "San Lorenzo River"
              gauge: "Big Trees"
              latitude: 37.0443931
              longitude: -122.072464
            files:
              retrospective_products_daily: "retrospective_products_daily.csv"
              retrospective_source_lineage: "retrospective_source_lineage.csv"
              glofas_ensemble_forecast_daily: "glofas_ensemble_forecast_daily.csv"
              nws_ensemble_forecast_daily: "nws_ensemble_forecast_daily.csv"
              bundle_health: "bundle_health.json"
            retrospective_products:
              role: "pre-cutoff observations and aligned hydrologic product inputs"
              rows: {retros_rows}
              start_date: "{retros_start}"
              end_date: "{retros_end}"
              product_families:
                glofas_ecmwf: "ECMWF/GloFAS retrospective hydrologic product input"
                noaa_nws_nwm: "NOAA/NWS/National Water Model retrospective hydrologic product input"
            forecast_products:
              role: "issued ensemble forecasts available at the cutoff"
              glofas_ecmwf:
                members: {glofas_members}
                forecast_rows: {glofas_rows}
                issue_policy: "forecast issued at the cutoff; daily member matrix"
              noaa_nws_nwm:
                members: {nws_members}
                forecast_rows: {nws_rows}
                issue_policy: "latest available forecast issue at the cutoff; daily member matrix"
            exogenous_covariates:
              historical_inputs:
                - "local precipitation"
                - "local shallow soil-water"
                - "GDPC climate-index summary"
              forecast_window_inputs: "deterministic model-ready summaries derived from post-processed GEFS forecast products"
            public_scope_note: "This public bundle starts from model-ready inputs and compact versioning metadata; raw archive retrieval, recovery, and covariate-construction workflows are not bundled."
            """,
        )

        health = {
            "schema_version": "public_forecast_origin_health_v1",
            "status": "model_ready_public_bundle",
            "cutoff": cutoff.replace("_", ""),
            "cutoff_date": cutoff_date,
            "retrospective_window": {
                "start_date": retros_start,
                "end_date": retros_end,
                "rows": retros_rows,
            },
            "forecast_rows": {
                "glofas_ecmwf": glofas_rows,
                "noaa_nws_nwm": nws_rows,
            },
            "forecast_member_counts": {
                "glofas_ecmwf": glofas_members,
                "noaa_nws_nwm": nws_members,
            },
            "storage_scales": {
                "retrospective_products_daily": "log1p_cms",
                "glofas_ensemble_forecast_daily": "raw_cms",
                "nws_ensemble_forecast_daily": "raw_cms",
            },
            "public_scope_note": (
                "Numerical model inputs are included. Raw retrieval, recovery, "
                "and intermediate covariate-construction metadata are excluded "
                "from the public release."
            ),
        }
        (origin_dir / "bundle_health.json").write_text(
            json.dumps(health, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


def refresh_row_hashes(roots: Roots, rows: list[dict[str, str]], replacements: tuple[tuple[str, str], ...]) -> None:
    refreshed = []
    for row in rows:
        updated = dict(row)
        public_path = Path(updated["public_path"])
        if public_path.exists():
            updated["bytes"] = str(public_path.stat().st_size)
            updated["sha256"] = sha256(public_path)
        updated["source_path"] = compact_placeholder_paths(apply_replacements(updated["source_path"], replacements))
        refreshed.append(updated)
    rows[:] = refreshed


def copy_file(
    src: Path,
    dst: Path,
    role: str,
    rows: list[dict[str, str]],
    replacements: tuple[tuple[str, str], ...] | None = None,
) -> None:
    if not src.exists():
        return
    if src.suffix in FORBIDDEN_SUFFIXES:
        raise RuntimeError(f"Refusing to copy forbidden file type: {src}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    if replacements is not None:
        sanitize_public_text_file(dst, replacements)
    rows.append(
        {
            "role": role,
            "public_path": dst.as_posix(),
            "source_path": src.as_posix(),
            "bytes": str(dst.stat().st_size),
            "sha256": sha256(dst),
        }
    )


def copy_tree(
    src: Path,
    dst: Path,
    role: str,
    rows: list[dict[str, str]],
    replacements: tuple[tuple[str, str], ...] | None = None,
) -> None:
    if not src.exists():
        return
    for path in sorted(src.rglob("*")):
        if not path.is_file():
            continue
        if "__pycache__" in path.parts or ".git" in path.parts:
            continue
        target = dst / path.relative_to(src)
        copy_file(path, target, role, rows, replacements)


def remove_exported_file(roots: Roots, rows: list[dict[str, str]], relpath: str) -> None:
    path = roots.destination / relpath
    if path.exists():
        path.unlink()
    rows[:] = [
        row
        for row in rows
        if Path(row["public_path"]).resolve() != path.resolve()
    ]


def write_public_deterministic_covariate_stub(roots: Roots) -> None:
    write_text(
        roots.destination / "R/unified/deterministic_climate_covariates.R",
        """
        # Public reproducibility stub.
        #
        # The public repository starts from model-ready staged covariates. Raw
        # GEFS/NWM retrieval and intermediate forecast-covariate construction
        # are intentionally outside this release.

        unified_materialize_deterministic_climate_covariates <- function(cfg, shared_paths, cov_path_map, repo_root) {
          stop(
            paste(
              "Raw forecast-covariate materialization is not bundled in the public reproducibility release.",
              "Use the model-ready staged covariates under data/staged/covariates and the cutoff-specific",
              "forecast-origin bundles under data/staged/forecast_origins."
            ),
            call. = FALSE
          )
        }
        """,
    )


def write_public_selected_model_specs(roots: Roots) -> None:
    """Write neutral selected-model specifications for public inspection."""

    authority_path = roots.workflow / "docs/exdqlm_multivar_keep_authoritative_specs_20260601.yaml"
    authority = yaml.safe_load(authority_path.read_text(encoding="utf-8"))
    by_cutoff = {str(row["cutoff"]): dict(row) for row in authority.get("winners", [])}

    partial_root = (
        roots.runtime
        / "multimodel_v8_he2_exdqlm_multivar_keep_partial_authority_refresh_20260623"
        / "runs"
    )
    for cutoff in ("20211221", "20220511", "20221225"):
        resolved = partial_root / f"multimodel_{cutoff}_v8_he2partial20260623_exdqlm_multivar_keep" / "resolved_config.yaml"
        if not resolved.exists() or cutoff not in by_cutoff:
            continue
        cfg = yaml.safe_load(resolved.read_text(encoding="utf-8"))
        state = cfg.get("models", {}).get("exdqlm_multivar", {}).get("state_evolution", {})
        forecast_cov = (
            cfg.get("fit", {})
            .get("exdqlm_multivar", {})
            .get("legacy", {})
            .get("forecast_cov", {})
        )
        by_cutoff[cutoff].update(
            {
                "forecast_covariance_prior_weight": forecast_cov.get("epsilon"),
                "c_factor": forecast_cov.get("c_factor", by_cutoff[cutoff].get("c_factor")),
                "df_t": state.get("df_t", by_cutoff[cutoff].get("df_t")),
                "df_s1": state.get("df_s1", by_cutoff[cutoff].get("df_s1")),
                "df_s2": state.get("df_s2", by_cutoff[cutoff].get("df_s2")),
                "df_s67": state.get("df_s67", by_cutoff[cutoff].get("df_s67")),
                "df_discrep": state.get("df_discrep", by_cutoff[cutoff].get("df_discrep")),
                "lambda": state.get("lambda", by_cutoff[cutoff].get("lambda")),
                "df_trans": state.get("df_trans", by_cutoff[cutoff].get("df_trans")),
                "df_covs": state.get("df_covs", by_cutoff[cutoff].get("df_covs")),
            }
        )

    manifest_path = roots.article / "artifacts/five_cutoff_crps_validation_sources/manifest.csv"
    crps_by_cutoff: dict[str, dict[str, str]] = {}
    if manifest_path.exists():
        with manifest_path.open(newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                crps_by_cutoff[row["cutoff"].replace("-", "")] = row

    selected_cutoffs = []
    for cutoff in ("20210123", "20211112", "20211221", "20220511", "20221225"):
        row = by_cutoff.get(cutoff, {})
        crps_row = crps_by_cutoff.get(cutoff, {})
        selected_cutoffs.append(
            {
                "cutoff": cutoff,
                "cutoff_date": f"{cutoff[:4]}-{cutoff[4:6]}-{cutoff[6:]}",
                "selected_output_id": f"selected_exdqlm_multivariate_keep_{cutoff}",
                "model_family": "exdqlm_multivar_keep",
                "manuscript_label": "exAL-M-T1",
                "forecast_covariance_prior": {
                    "c_factor": row.get("c_factor", 1.0),
                    "prior_weight": row.get(
                        "forecast_covariance_prior_weight",
                        row.get("epsilon_value"),
                    ),
                },
                "state_evolution": {
                    "df_t": row.get("df_t"),
                    "df_s1": row.get("df_s1"),
                    "df_s2": row.get("df_s2"),
                    "df_s67": row.get("df_s67"),
                    "df_discrep": row.get("df_discrep"),
                    "lambda": row.get("lambda", 0.97),
                    "df_trans": row.get("df_trans"),
                    "df_covs": row.get("df_covs"),
                },
                "forecast_window_mean_crps": crps_row.get("replay_mean_crps", row.get("mean_crps")),
                "score_scale": "log_cms_plus1",
            }
        )

    spec = {
        "schema_version": "public_selected_model_specifications_v1",
        "scope": "selected manuscript-facing exDQLM multivariate keep outputs",
        "note": (
            "This public file records the selected settings needed to interpret "
            "and rerun the reported exAL-M-T1 case-study outputs from staged "
            "inputs. Internal exploratory campaign labels are not part of the "
            "public release."
        ),
        "shared_inputs": {
            "site": "USGS 11160500 San Lorenzo River at Big Trees",
            "data_start": authority.get("metadata", {}).get("data_start", "1987-05-29"),
            "active_quantiles": ["0.05", "0.20", "0.35", "0.50", "0.65", "0.80", "0.95"],
            "input_bundle_contract": "PPT|SOIL|GDPC1",
        },
        "selected_cutoffs": selected_cutoffs,
    }

    out_dir = roots.destination / "config/selected_model_specifications"
    write_text(
        out_dir / "README.md",
        """
        # Selected Model Specifications

        These files describe the selected manuscript-facing model
        specifications in public, readable terms. They intentionally omit
        private exploratory campaign names and run-root labels. Numerical
        scores, cutoffs, prior weights, discount factors, staged inputs, and
        expected manuscript outputs remain available for verification.
        """,
    )
    (out_dir / "exdqlm_multivariate_keep_selected_outputs.yaml").write_text(
        yaml.safe_dump(spec, sort_keys=False, allow_unicode=False),
        encoding="utf-8",
    )


def reset_destination(path: Path, replace: bool) -> None:
    if path.exists() and not replace:
        raise SystemExit(f"Destination exists. Re-run with --replace to refresh: {path}")
    path.mkdir(parents=True, exist_ok=True)
    for child in path.iterdir():
        if child.name == ".git":
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def git_commit(root: Path) -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    except Exception:
        return "unknown"


def git_remote(root: Path) -> str:
    try:
        return subprocess.check_output(["git", "remote", "get-url", "origin"], cwd=root, text=True).strip()
    except Exception:
        return "unknown"


def export_data_bundle(roots: Roots, rows: list[dict[str, str]], replacements: tuple[tuple[str, str], ...]) -> None:
    bundle = roots.runtime / SHARED_INPUT_BUNDLE
    if not bundle.exists():
        raise RuntimeError(f"Missing shared input bundle: {bundle}")

    source_map = {
        "glofas_hist_v31_lisflood_cons_point.csv": "glofas_lisflood_retrospective_daily.csv",
        "glofas_hist_v31_lisflood_cons_point.meta.json": "glofas_lisflood_retrospective_daily.meta.json",
        "hist_v21_htessel_cons_point.csv": "glofas_htessel_retrospective_daily.csv",
        "hist_v21_htessel_cons_point.meta.json": "glofas_htessel_retrospective_daily.meta.json",
        "hist_v31_lisflood_cons_point.csv": "glofas_lisflood_historical_daily.csv",
        "hist_v31_lisflood_cons_point.meta.json": "glofas_lisflood_historical_daily.meta.json",
        "nws_retro_v21_daily.csv": "nws_nwm_retrospective_v21_daily.csv",
        "nws_retro_v30_daily.csv": "nws_nwm_retrospective_v30_daily.csv",
    }
    for old, new in source_map.items():
        copy_file(
            bundle / "source_series" / old,
            roots.destination / "data/staged/source_series" / new,
            "staged_source_series",
            rows,
            replacements,
        )

    cov_map = {
        "cov_01_ELI.csv": "eli_climate_index_daily.csv",
        "cov_02_ONI.csv": "oni_climate_index_daily.csv",
        "cov_03_PPT.csv": "local_precipitation_daily.csv",
        "cov_04_SOIL.csv": "local_shallow_soil_water_daily.csv",
        "cov_05_PCA.csv": "gdpc_climate_index_pc1_daily.csv",
    }
    for old, new in cov_map.items():
        copy_file(
            bundle / "supporting_inputs/covariates" / old,
            roots.destination / "data/staged/covariates" / new,
            "staged_covariates",
            rows,
            replacements,
        )

    copy_file(
        bundle / "supporting_inputs/parameters/parameters.txt",
        roots.destination / "data/staged/model_parameters/parameters.txt",
        "staged_parameters",
        rows,
        replacements,
    )
    copy_file(
        bundle / "supporting_inputs/support_manifest.json",
        roots.destination / "data/staged/support_manifest.json",
        "staged_support_manifest",
        rows,
        replacements,
    )
    copy_file(
        bundle / "stable_inputs/histfix_bundle_summary.csv",
        roots.destination / "data/staged/forecast_origins/forecast_origin_bundle_summary.csv",
        "staged_forecast_origin_summary",
        rows,
        replacements,
    )

    for origin in sorted((bundle / "stable_inputs/site=11160500").glob("cutoff_date=*/run_id=*")):
        if not origin.is_dir():
            continue
        cutoff = origin.parent.name.split("=", 1)[1]
        public_cutoff = "cutoff_" + cutoff.replace("-", "_")
        origin_dst = roots.destination / "data/staged/forecast_origins" / public_cutoff
        file_map = {
            "retros.csv": "retrospective_products_daily.csv",
            "retros_source_lineage.csv": "retrospective_source_lineage.csv",
            "glofas_forecast.csv": "glofas_ensemble_forecast_daily.csv",
            "nws_forecast.csv": "nws_ensemble_forecast_daily.csv",
            "meta.yaml": "origin_metadata.yaml",
            "bundle_health.json": "bundle_health.json",
        }
        for old, new in file_map.items():
            copy_file(origin / old, origin_dst / new, "staged_forecast_origin_bundle", rows, replacements)


def generate_public_docs(roots: Roots) -> None:
    write_text(
        roots.destination / "README.md",
        f"""
        # San Lorenzo exDQLM Reproducibility

        This repository contains the clean reproducibility bundle for the
        Environmetrics manuscript *Bayesian Quantile-Based Correction and
        Synthesis of Hydrologic Products*.

        The repository is intentionally narrower than the live research
        workspace. It contains compact staged inputs, current manuscript-facing
        outputs, provenance, and the selected workflow code needed to inspect
        or rerun the reported case-study analysis from model-ready inputs. It
        does not contain raw climate-center archives, raw covariate-retrieval
        workflows, active runtime campaigns, local notebooks, poster drafts, or
        internal exploratory outputs.

        ## Quick Validation

        ```bash
        make validate
        ```

        This checks required files, manifests, hashes, file sizes, and the
        absence of forbidden heavy runtime formats.

        ## Reproducibility Levels

        1. **Fast artifact verification.** Regenerate or verify
           manuscript-facing tables, figures, hashes, and provenance from the
           compact staged outputs in `outputs/expected/`.
        2. **Selected-model rerun support.** Use the selected R workflow,
           configuration files, and model-ready staged input bundles in
           `data/staged/` to rerun the reported exDQLM/DQLM case-study fits.
           This requires the public CRAN package `exdqlm` and sufficient local
           compute.
        3. **Raw archive reconstruction.** Not bundled. Reconstructing a new
           retrospective validation archive requires agency-specific historical
           products, version matching, spatial extraction, forecast-window
           covariate staging, and source-specific horizon handling.

        ## Main Directories

        - `R/`: selected model, post-processing, and figure-generation code.
        - `scripts/`: orchestration, manifest, and validation scripts.
        - `config/`: selected public model-specification files.
        - `data/staged/`: compact model-ready inputs used by the five cutoff cases.
        - `outputs/expected/`: current manuscript-facing expected outputs and
          compact artifact bundles.
        - `figures/`: frozen manuscript figure files.
        - `tables/`: generated manuscript table fragments and summaries.
        - `provenance/`: source crosswalks, data/version notes, and hashes.
        - `manuscript/`: article-side manifest and source pointers.

        ## Software

        The reusable estimation routines are provided by the CRAN package
        `exdqlm`, version 1.1.0:

        - <https://CRAN.R-project.org/package=exdqlm>
        - <https://doi.org/10.32614/CRAN.package.exdqlm>

        The accompanying software paper is:

        - <https://arxiv.org/abs/2607.22760>
        - <https://doi.org/10.48550/arXiv.2607.22760>

        ## Repository URL

        {PUBLIC_URL}

        ## Source-Path Placeholders

        Copied text artifacts replace local machine paths with stable
        placeholders so the public tree can be read outside the original
        workspace:

        - `SOURCE_WORKFLOW_ROOT`: private live workflow repository used for export.
        - `SOURCE_ARTICLE_ROOT`: private revised manuscript repository used for export.
        - `SOURCE_CORRECTIONS_ROOT`: private response-letter repository used
          for cross-repo validation.
        - `SOURCE_RUNTIME_ROOT`: private runtime root used for staged artifacts.
        - `STAGED_INPUT_BUNDLE_ROOT`: private staged-input bundle used for export.
        - `PUBLIC_REPRO_ROOT`: local checkout of this public reproducibility repo.
        - `LEGACY_EXAL_INPUT_ROOT`: legacy local input root referenced by older
          workflow scripts.
        - `LEGACY_PROJECT_ROOT`: legacy local project root referenced by older
          workflow scripts.
        - `LOCAL_RCPP_LIB_ROOT`: local compiled-library root referenced by
          commented Rcpp setup notes.
        - `EXTERNAL_RUNTIME_SOURCE_ROOT`: external local runtime source tree used
          in legacy provenance notes.

        Export-time commits and source roles are preserved in
        `provenance/source_file_crosswalk.csv` and
        `provenance/runtime_source_crosswalk.csv`; machine-specific paths are
        replaced by public placeholders.

        ## License Status

        The final reuse license must be confirmed by the authors before
        archival release. See `LICENSE` for the current review-stage notice.
        """,
    )

    write_text(
        roots.destination / ".gitignore",
        """
        # Local runtime/build products
        __pycache__/
        .pytest_cache/
        *.pyc
        *.aux
        *.log
        *.out
        *.toc
        *.fdb_latexmk
        *.fls
        *.synctex.gz

        # Heavy or raw runtime formats not allowed in the public repo
        *.RData
        *.rda
        *.rdata
        *.nc
        *.grib
        *.grib2
        *.zarr
        *.pkl
        *.pickle
        *.parquet
        *.feather
        *.h5
        *.hdf5

        # Local rerun outputs
        local_outputs/
        runtime/
        scratch/
        """,
    )

    write_text(
        roots.destination / "LICENSE",
        """
        Copyright (c) 2026 Antonio Aguirre, Raquel Prado, and Bruno Sanso.

        This repository is shared as a review-stage reproducibility artifact
        for the associated Environmetrics manuscript. The final reuse license
        will be confirmed by the authors before archival release. Until that
        license is added, no permission is granted beyond inspection and
        evaluation for manuscript review and reproducibility assessment.
        """,
    )

    write_text(
        roots.destination / "CITATION.cff",
        f"""
        cff-version: 1.2.0
        message: "If you use this reproducibility bundle, cite the associated article and the final archived release once available."
        title: "San Lorenzo exDQLM reproducibility bundle"
        type: dataset
        authors:
          - family-names: Aguirre
            given-names: Antonio
          - family-names: Prado
            given-names: Raquel
          - family-names: Sanso
            given-names: Bruno
        repository-code: "{PUBLIC_URL}"
        url: "{PUBLIC_URL}"
        version: "pending-final-archive"
        keywords:
          - dynamic quantile linear model
          - exDQLM
          - hydrologic forecasting
          - probabilistic forecasting
          - reproducibility
        """,
    )

    write_text(
        roots.destination / "Makefile",
        """
        .PHONY: validate hashes list

        validate:
        \tpython3 scripts/validate_public_repository.py

        hashes:
        \tpython3 scripts/write_sha256_manifest.py

        list:
        \tfind . -maxdepth 3 -type f | sort
        """,
    )

    write_text(
        roots.destination / "data/README.md",
        """
        # Staged Data

        `data/staged/` contains compact, cutoff-specific inputs used by the
        publication workflow. These are model-ready inputs, not raw
        climate-center retrieval archives. Filenames are intentionally
        descriptive; source roles and hashes are recorded in
        `provenance/source_file_crosswalk.csv`.

        The five forecast-origin folders are:

        - `cutoff_2021_01_23`
        - `cutoff_2021_11_12`
        - `cutoff_2021_12_21`
        - `cutoff_2022_05_11`
        - `cutoff_2022_12_25`

        Each contains retrospective products, issued GloFAS and NWS ensemble
        forecast matrices, source-lineage metadata, and bundle health metadata.
        """,
    )

    write_text(
        roots.destination / "provenance/model_inputs_by_cutoff.md",
        """
        # Model Inputs by Forecast Origin

        The public data bundle starts from model-ready inputs for the five
        forecast origins used in the manuscript:

        - `cutoff_2021_01_23`
        - `cutoff_2021_11_12`
        - `cutoff_2021_12_21`
        - `cutoff_2022_05_11`
        - `cutoff_2022_12_25`

        Each folder under `data/staged/forecast_origins/` contains:

        - `retrospective_products_daily.csv`: USGS observations and aligned
          retrospective hydrologic product inputs available before the cutoff.
        - `glofas_ensemble_forecast_daily.csv`: GloFAS ensemble forecast matrix
          issued at the cutoff.
        - `nws_ensemble_forecast_daily.csv`: NWS/NWM ensemble forecast matrix
          issued at the cutoff.
        - `retrospective_source_lineage.csv`: compact source labels for the
          retrospective products.
        - `origin_metadata.yaml` and `bundle_health.json`: compact checks and
          metadata for the staged origin bundle.

        Shared covariates live under `data/staged/covariates/`:

        - `local_precipitation_daily.csv`
        - `local_shallow_soil_water_daily.csv`
        - `gdpc_climate_index_pc1_daily.csv`

        The forecast-window precipitation and shallow soil-water covariates are
        included as deterministic, model-ready summaries derived from
        post-processed GEFS forecast products. The public repository does not
        bundle raw GEFS retrievals or intermediate covariate-construction
        workflows. The GDPC series is a climate-index summary covariate, not an
        operational forecast product.
        """,
    )

    write_text(
        roots.destination / "provenance/climate_product_versioning.md",
        """
        # Climate Product Versioning and Public Scope

        The validation study uses forecast-origin bundles that align four
        information streams at each cutoff:

        - USGS observed daily river flow for the San Lorenzo River at Big Trees.
        - ECMWF/GloFAS retrospective hydrologic products before the cutoff and
          issued GloFAS ensemble forecasts after the cutoff.
        - NOAA/NWS/National Water Model retrospective hydrologic products before
          the cutoff and issued NWS ensemble forecasts after the cutoff.
        - Exogenous covariates: local precipitation, local shallow soil-water,
          and a GDPC climate-index summary.

        The public repository includes the staged inputs used by the manuscript.
        It does not attempt to reproduce the raw historical archive recovery.
        That reconstruction requires product-version matching, spatial
        extraction rules, source-specific forecast horizons, and cutoff-specific
        issued forecast bundles for each climate-center product family.

        This versioning detail is most important for the hydrologic product
        families. GloFAS/ECMWF and NWS/NWM each contribute retrospective
        information and issued forecast information, and those products differ
        in version history, spatial support, ensemble structure, update cycle,
        and forecast horizon. The model inputs exported here are the aligned
        result of that recovery and harmonization step.
        """,
    )

    write_text(
        roots.destination / "provenance/public_release_hygiene.md",
        """
        # Public Release Hygiene

        This export is allowlist-based. It excludes raw archives, active
        runtime outputs, local planning notes, poster materials, large binary
        model objects, and internal recovery trackers. It also redacts
        machine-specific path tails and low-level covariate-construction
        metadata that are not required for reproducing the reported model fits
        from the staged inputs.

        The validation gate is:

        ```bash
        make validate
        ```

        The gate checks required files, hashes, forbidden heavy formats, stale
        repository URLs, local absolute paths, internal drafting/tooling
        markers, excluded workflow trackers, and low-level public metadata
        fields that should not appear in the release.
        """,
    )

    write_text(
        roots.destination / "provenance/reproducibility_levels.md",
        """
        # Reproducibility Levels

        ## Level 1: Fast Verification

        Verify current manuscript-facing assets, tables, hashes, and provenance
        using the compact expected outputs included in this repository.

        ## Level 2: Selected Reruns

        Rerun selected model configurations using the staged inputs and workflow
        code included here. This requires installing the public `exdqlm` package
        and matching R/Python dependencies locally.

        ## Level 3: Historical Archive Reconstruction

        The raw agency archives are not bundled. Reconstructing additional
        forecast origins or another basin requires separate data recovery and
        version matching for USGS observations, retrospective products, issued
        forecasts, forecast-window covariates, spatial extraction rules, and
        source-specific horizons.
        """,
    )

    write_text(
        roots.destination / "outputs/README.md",
        """
        # Expected Outputs

        This directory contains the compact manuscript-facing outputs exported
        from the revised article repository. These are the reference artifacts
        used by fast validation and by the article figure/table provenance
        records.
        """,
    )

    write_text(
        roots.destination / "figures/README.md",
        """
        # Figures

        Frozen manuscript figures are copied from the revised article
        repository. Use the provenance crosswalks and article-side figure/table
        provenance notes to trace each figure back to the workflow artifacts.
        """,
    )

    write_text(
        roots.destination / "tables/README.md",
        """
        # Tables

        Generated TeX table fragments and CSV summaries are copied from the
        revised article repository. These should not be hand-edited; regenerate
        them from the workflow when the authoritative model outputs change.
        """,
    )

    write_text(
        roots.destination / "config/README.md",
        """
        # Configuration

        This directory contains selected public model-specification files and
        manuscript support configuration. Internal exploratory campaign
        configs are not exported.
        """,
    )

    write_text(
        roots.destination / "R/README.md",
        """
        # R Code

        Selected workflow R code is copied from the live research repository.
        The exported code is intended for reproducibility and inspection; the
        live research repository remains the source for exploratory campaign
        management.
        """,
    )

    write_text(
        roots.destination / "scripts/README.md",
        """
        # Scripts

        Selected orchestration, manifest, and validation scripts are copied from
        the live workflow repository. Use `make validate` for the public-bundle
        integrity check.
        """,
    )

    write_text(
        roots.destination / "manuscript/README.md",
        """
        # Manuscript Pointers

        The journal-facing manuscript source lives in the revised article
        repository, not here. This directory stores article-side manifests and
        source pointers needed to connect the clean reproducibility bundle to
        the manuscript figures and tables.
        """,
    )


def generate_validation_scripts(root: Path) -> None:
    write_text(
        root / "scripts/validate_public_repository.py",
        r"""
        #!/usr/bin/env python3
        from __future__ import annotations

        import csv
        import hashlib
        import sys
        from pathlib import Path

        ROOT = Path(__file__).resolve().parents[1]
        FORBIDDEN_SUFFIXES = {
            ".RData",
            ".rda",
            ".rdata",
            ".nc",
            ".grib",
            ".grib2",
            ".zarr",
            ".pkl",
            ".pickle",
            ".parquet",
            ".feather",
            ".h5",
            ".hdf5",
        }
        REQUIRED = [
            "README.md",
            "CITATION.cff",
            "LICENSE",
            "Makefile",
            "data/staged/source_series/glofas_lisflood_retrospective_daily.csv",
            "data/staged/source_series/nws_nwm_retrospective_v30_daily.csv",
            "data/staged/covariates/local_precipitation_daily.csv",
            "data/staged/covariates/local_shallow_soil_water_daily.csv",
            "data/staged/covariates/gdpc_climate_index_pc1_daily.csv",
            "config/selected_model_specifications/exdqlm_multivariate_keep_selected_outputs.yaml",
            "tables/generated_tex/benchmark_crps_main_table.tex",
            "figures/manuscript_context/site_context_usgs.png",
            "outputs/expected/artifacts/he2_publication_freeze/he2_bayesian_publication_manifest.csv",
            "provenance/model_inputs_by_cutoff.md",
            "provenance/climate_product_versioning.md",
            "provenance/public_release_hygiene.md",
            "provenance/source_file_crosswalk.csv",
            "provenance/runtime_source_crosswalk.csv",
            "data/SHA256SUMS.txt",
        ]
        TEXT_SUFFIXES = {
            ".R",
            ".Rmd",
            ".bib",
            ".bst",
            ".cff",
            ".cls",
            ".csv",
            ".html",
            ".htm",
            ".json",
            ".md",
            ".py",
            ".sh",
            ".sty",
            ".tex",
            ".txt",
            ".yaml",
            ".yml",
        }
        TEXT_FILENAMES = {"Makefile", "LICENSE", ".gitignore"}
        LOCAL_PATH_MARKERS = ("/" + "data/muscat_data/", "/" + "data/jaguir26/")
        STALE_TEXT_MARKERS = (
            "https://github.com/AntonioAPDL/" + "Project1",
            "PROJECT1" + "_URL",
            "chat" + "gpt",
            "co" + "dex",
            "open" + "ai",
            "cl" + "aude",
            "gem" + "ini",
            "co" + "pilot",
            "large " + "language " + "model",
            "language " + "model",
            "l" + "lm",
            "ai" + "-generated",
            "ai" + " generated",
            "ai " + "wording",
            "prompt " + "for",
        )
        FORBIDDEN_PUBLIC_PATHS = {
            "config/publication/unified_run.template.yaml",
            "config/publication/he2_bayesian_publication_relaunch_20260510.template.yaml",
            "config/publication/he2_bayesian_publication_relaunch_table1_targeted_repair_20260612.template.yaml",
            "config/publication/he2_bayesian_publication_relaunch_univar_al_exal_scale_repair_20260629.template.yaml",
            "config/publication/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_partial_authority_refresh_20260623.template.yaml",
            "config/publication/he2_publication_manifest_replacement_overlay_current_authority_20260623.yaml",
            "config/publication/he2_publication_manifest_replacement_overlay_table1_targeted_repair_20260612.yaml",
            "config/authority/exdqlm_multivar_keep_authoritative_specs_20260601.yaml",
            "config/authority/he2_exal_m_t1_representative_20221225.yaml",
            "config/publication/exdqlm_multivar_keep_epsilon_discount_grid_20260524.csv",
            "outputs/expected/artifacts/he2_historical_support_audit",
            "provenance/workflow/docs/current_authority_refresh_runbook.md",
            "provenance/workflow/docs/canonical_gdpc_subset6_noi_soi_espi_pna_whwp_amo_20260527.md",
            "provenance/workflow/repro/GLOFAS_HARMONIZATION_QA_SPEC.md",
            "provenance/workflow/repro/GLOFAS_OPERATIONAL_MEDIUMRANGE_WORKFLOW_RUNBOOK.md",
            "provenance/workflow/repro/NWS_NWM_GLOFAS_DATA_AUDIT_PLAN.md",
            "provenance/workflow/repro/NWM_RETROSPECTIVE_EXTRACTION_WORKSTREAM_TRACKER.md",
            "provenance/workflow/repro/GEFS_NWM_FORECAST_AUDIT_TRACKER.md",
            "provenance/workflow/repro/run/CANONICAL_GDPC_IMPLEMENTATION_TRACKER_20260509.md",
            "provenance/workflow/repro/run/CANONICAL_GDPC_MASTER_COVARIATE_REPORT_20260509.md",
            "provenance/workflow/repro/run/CANONICAL_GDPC_MASTER_PIPELINE_RUNBOOK_20260509.md",
        }
        PUBLIC_METADATA_PREFIXES = (
            "README.md",
            "CITATION.cff",
            "LICENSE",
            "Makefile",
            "config/",
            "data/",
            "manuscript/",
            "outputs/",
            "provenance/",
            "tables/",
        )
        INTERNAL_COVARIATE_MARKERS = (
            "noisy" + "_blend",
            "observed" + "_blend",
            "tail" + "_blend",
            "handoff" + "_forecasts",
            "source" + "_native_tranche",
            "deterministic" + "_climate_blend",
            "GEFS" + "_NWM_FORECAST_AUDIT_TRACKER",
            "CANONICAL" + "_GDPC_MASTER_PIPELINE",
            "hist" + "fix",
            "legacy" + "_log_ready",
            "selected" + "_window_splice",
        )
        INTERNAL_SELECTION_MARKERS = (
            "he2" + "grid",
            "eps" + "001",
            "eps" + "030",
            "eps" + "060",
            "eps" + "090",
            "eps" + "180",
            "eps" + "360",
            "eps" + "365",
            "discount" + "_grid",
            "epsilon" + "_discount",
            "canonical" + "_grid",
            "canonical-" + "grid",
            "partial" + "_screen",
            "partial-" + "screen",
            "best" + "_epsilon",
            "selected" + "_epsilon",
            "source" + "_epsilon",
            "matrix" + "_epsilon",
            "runner" + "_up",
            "screen" + "ing",
        )


        def sha256(path: Path) -> str:
            h = hashlib.sha256()
            with path.open("rb") as fh:
                for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                    h.update(chunk)
            return h.hexdigest()


        def is_text_like(path: Path) -> bool:
            return path.suffix in TEXT_SUFFIXES or path.name in TEXT_FILENAMES


        def main() -> int:
            errors = []
            for rel in REQUIRED:
                if not (ROOT / rel).exists():
                    errors.append(f"missing required file: {rel}")
            for rel in FORBIDDEN_PUBLIC_PATHS:
                if (ROOT / rel).exists():
                    errors.append(f"forbidden internal export file: {rel}")

            for path in ROOT.rglob("*"):
                if not path.is_file() or ".git" in path.parts:
                    continue
                rel = path.relative_to(ROOT).as_posix()
                if path.suffix in FORBIDDEN_SUFFIXES:
                    errors.append(f"forbidden heavy/runtime file type: {rel}")
                if path.stat().st_size > 100 * 1024 * 1024:
                    errors.append(f"oversized file >100MB: {rel}")
                if is_text_like(path):
                    try:
                        text = path.read_text(encoding="utf-8")
                    except UnicodeDecodeError:
                        continue
                    lower_text = text.lower()
                    if any(marker in text for marker in LOCAL_PATH_MARKERS):
                        errors.append(f"local absolute path outside provenance crosswalk: {rel}")
                    for marker in STALE_TEXT_MARKERS:
                        if marker.lower() in lower_text:
                            errors.append(f"stale/internal marker {marker!r} in {rel}")
                    if rel.startswith(PUBLIC_METADATA_PREFIXES):
                        for marker in INTERNAL_COVARIATE_MARKERS:
                            if marker.lower() in lower_text:
                                errors.append(f"internal covariate-construction marker {marker!r} in {rel}")
                        for marker in INTERNAL_SELECTION_MARKERS:
                            if marker.lower() in lower_text:
                                errors.append(f"internal model-selection lineage marker {marker!r} in {rel}")

            manifest = ROOT / "data/SHA256SUMS.txt"
            if manifest.exists():
                for line in manifest.read_text(encoding="utf-8").splitlines():
                    if not line.strip():
                        continue
                    expected, relpath = line.split("  ", 1)
                    path = ROOT / relpath
                    if not path.exists():
                        errors.append(f"hash manifest missing file: {relpath}")
                    elif sha256(path) != expected:
                        errors.append(f"hash mismatch: {relpath}")

            crosswalk = ROOT / "provenance/source_file_crosswalk.csv"
            if crosswalk.exists():
                with crosswalk.open(newline="", encoding="utf-8") as fh:
                    rows = list(csv.DictReader(fh))
                if len(rows) < 50:
                    errors.append("source_file_crosswalk.csv has unexpectedly few rows")

            if errors:
                print("Public repository validation failed:")
                for item in errors:
                    print(f"- {item}")
                return 1

            print("Public repository validation passed.")
            return 0


        if __name__ == "__main__":
            sys.exit(main())
        """,
    )

    write_text(
        root / "scripts/write_sha256_manifest.py",
        r"""
        #!/usr/bin/env python3
        from __future__ import annotations

        import hashlib
        from pathlib import Path

        ROOT = Path(__file__).resolve().parents[1]
        OUT = ROOT / "data/SHA256SUMS.txt"


        def sha256(path: Path) -> str:
            h = hashlib.sha256()
            with path.open("rb") as fh:
                for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                    h.update(chunk)
            return h.hexdigest()


        rows = []
        for path in sorted((ROOT / "data").rglob("*")):
            if path.is_file() and path != OUT:
                rows.append(f"{sha256(path)}  {path.relative_to(ROOT).as_posix()}")
        OUT.write_text("\n".join(rows) + "\n", encoding="utf-8")
        print(f"Wrote {OUT.relative_to(ROOT)} with {len(rows)} entries")
        """,
    )


def write_crosswalks(roots: Roots, rows: list[dict[str, str]]) -> None:
    replacements = local_path_replacements(roots)
    crosswalk = roots.destination / "provenance/source_file_crosswalk.csv"
    crosswalk.parent.mkdir(parents=True, exist_ok=True)
    normalized_rows = []
    for row in rows:
        normalized = dict(row)
        public_path = Path(normalized["public_path"])
        try:
            normalized["public_path"] = public_path.relative_to(roots.destination).as_posix()
        except ValueError:
            normalized["public_path"] = public_path.as_posix()
        normalized["public_path"] = sanitize_public_lineage_text(normalized["public_path"])
        normalized["source_path"] = sanitize_public_lineage_text(
            compact_placeholder_paths(apply_replacements(normalized["source_path"], replacements))
        )
        normalized_rows.append(normalized)
    with crosswalk.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["role", "public_path", "source_path", "bytes", "sha256"],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(normalized_rows)

    runtime_crosswalk = roots.destination / "provenance/runtime_source_crosswalk.csv"
    with runtime_crosswalk.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["role", "path", "git_head", "remote"], lineterminator="\n")
        writer.writeheader()
        writer.writerow(
            {
                "role": "workflow_source",
                "path": "SOURCE_WORKFLOW_ROOT",
                "git_head": git_commit(roots.workflow),
                "remote": git_remote(roots.workflow),
            }
        )
        writer.writerow(
            {
                "role": "article_source",
                "path": "SOURCE_ARTICLE_ROOT",
                "git_head": git_commit(roots.article),
                "remote": git_remote(roots.article),
            }
        )
        writer.writerow(
            {
                "role": "runtime_shared_input_bundle",
                "path": "STAGED_INPUT_BUNDLE_ROOT",
                "git_head": "not_a_git_repository",
                "remote": "local_runtime_bundle",
            }
        )

    data_hashes = []
    for path in sorted((roots.destination / "data").rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.txt":
            data_hashes.append(f"{sha256(path)}  {rel(path, roots.destination)}")
    write_text(roots.destination / "data/SHA256SUMS.txt", "\n".join(data_hashes) + "\n")


def export_public_repo(roots: Roots) -> None:
    rows: list[dict[str, str]] = []
    reset_destination(roots.destination, replace=True)
    generate_public_docs(roots)
    generate_validation_scripts(roots.destination)
    replacements = local_path_replacements(roots)

    copy_tree(roots.workflow / "R/environmetrics", roots.destination / "R/environmetrics", "workflow_r_code", rows, replacements)
    copy_tree(roots.workflow / "R/unified", roots.destination / "R/unified", "workflow_r_code", rows, replacements)
    copy_file(roots.workflow / "R/environmetrics_utils.R", roots.destination / "R/environmetrics_utils.R", "workflow_r_code", rows, replacements)
    remove_exported_file(roots, rows, "R/unified/deterministic_climate_blend.R")
    write_public_deterministic_covariate_stub(roots)

    for item in CONFIG_FILES:
        src = roots.workflow / item
        if item.startswith("config/"):
            dst = roots.destination / "config/publication" / Path(item).name
        else:
            dst = roots.destination / "config/authority" / Path(item).name
        copy_file(src, dst, "workflow_config", rows, replacements)
    write_public_selected_model_specs(roots)

    for item in SCRIPT_FILES:
        copy_file(roots.workflow / item, roots.destination / item, "workflow_script", rows, replacements)

    for item in TEST_FILES:
        copy_file(roots.workflow / item, roots.destination / item, "workflow_test", rows, replacements)

    for item in WORKFLOW_DOCS:
        copy_file(roots.workflow / item, roots.destination / "provenance/workflow" / item, "workflow_provenance", rows, replacements)

    for item in ARTICLE_DOCS:
        target_dir = "manuscript" if item in {"README.md", "MANUSCRIPT_ASSET_MANIFEST.json"} else "provenance/article"
        copy_file(roots.article / item, roots.destination / target_dir / item, "article_provenance", rows, replacements)

    copy_tree(roots.article / "Figures/manuscript", roots.destination / "figures/manuscript_context", "article_figure", rows, replacements)
    copy_tree(roots.article / "Figures/multivariate_synthesis_by_cutoff", roots.destination / "figures/multivariate_synthesis_by_cutoff", "article_figure", rows, replacements)
    copy_tree(roots.article / "Figures/reference_synthesis_by_cutoff", roots.destination / "figures/reference_synthesis_by_cutoff", "article_figure", rows, replacements)
    copy_tree(roots.article / "Figures/appendix_cutoff_panels", roots.destination / "figures/appendix_cutoff_panels", "article_figure", rows, replacements)
    copy_tree(roots.article / "tables/generated_tex", roots.destination / "tables/generated_tex", "article_table", rows, replacements)

    for item in ARTICLE_ARTIFACT_DIRS:
        copy_tree(roots.article / item, roots.destination / "outputs/expected" / item, "article_expected_output", rows, replacements)

    export_data_bundle(roots, rows, replacements)
    curate_public_metadata(roots, replacements)
    write_compact_origin_metadata(roots)
    refresh_row_hashes(roots, rows, replacements)
    write_crosswalks(roots, rows)


def parse_args() -> argparse.Namespace:
    default_workflow = Path(__file__).resolve().parents[1]
    return argparse.ArgumentParser(description=__doc__).parse_args()


def main() -> int:
    workflow = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workflow-root", type=Path, default=workflow)
    parser.add_argument("--article-root", type=Path, default=workflow / ARTICLE_DIR_NAME)
    parser.add_argument("--runtime-root", type=Path, default=workflow.parent / "project1_ucsc_phd_runtime")
    parser.add_argument("--destination", type=Path, default=workflow.parent / REPO_NAME)
    args = parser.parse_args()

    roots = Roots(
        workflow=args.workflow_root.resolve(),
        article=args.article_root.resolve(),
        runtime=args.runtime_root.resolve(),
        destination=args.destination.resolve(),
    )
    export_public_repo(roots)
    print(f"Exported clean reproducibility repository to {roots.destination}")
    print(f"Recommended public URL: {PUBLIC_URL}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
