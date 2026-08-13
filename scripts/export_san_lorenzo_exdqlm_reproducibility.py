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
import shutil
import subprocess
import textwrap
from dataclasses import dataclass
from pathlib import Path


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
    "docs/current_authority_refresh_runbook.md",
    "docs/software_reproducibility_release_plan_20260615.md",
    "docs/workflow_archive_readiness_20260615.md",
    "docs/he6_out_of_sample_forecast_design_contract_20260615.md",
    "docs/he7_latest_forecast_issue_contract_20260615.md",
    "docs/canonical_gdpc_subset6_noi_soi_espi_pna_whwp_amo_20260527.md",
    "docs/publication_freeze_validation_20260614.md",
    "repro/GLOFAS_HARMONIZATION_QA_SPEC.md",
    "repro/GLOFAS_OPERATIONAL_MEDIUMRANGE_WORKFLOW_RUNBOOK.md",
    "repro/NWS_NWM_GLOFAS_DATA_AUDIT_PLAN.md",
    "repro/NWM_RETROSPECTIVE_EXTRACTION_WORKSTREAM_TRACKER.md",
    "repro/GEFS_NWM_FORECAST_AUDIT_TRACKER.md",
    "repro/run/CANONICAL_GDPC_IMPLEMENTATION_TRACKER_20260509.md",
    "repro/run/CANONICAL_GDPC_MASTER_COVARIATE_REPORT_20260509.md",
    "repro/run/CANONICAL_GDPC_MASTER_PIPELINE_RUNBOOK_20260509.md",
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
    "config/unified_run.template.yaml",
    "config/post_publication_figures.yaml",
    "config/he2_bayesian_publication_relaunch_20260510.template.yaml",
    "config/he2_bayesian_publication_relaunch_table1_targeted_repair_20260612.template.yaml",
    "config/he2_bayesian_publication_relaunch_univar_al_exal_scale_repair_20260629.template.yaml",
    "config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_partial_authority_refresh_20260623.template.yaml",
    "config/he2_publication_manifest_replacement_overlay_current_authority_20260623.yaml",
    "config/he2_publication_manifest_replacement_overlay_table1_targeted_repair_20260612.yaml",
    "config/he2_grid_specs/exdqlm_multivar_keep_epsilon_discount_grid_20260524.csv",
    "docs/exdqlm_multivar_keep_authoritative_specs_20260601.yaml",
    "docs/authoritative_selected_outputs/he2_exal_m_t1_representative_20221225.yaml",
]

SCRIPT_FILES = [
    "scripts/unified_run.R",
    "scripts/run_environmetrics_figures.R",
    "scripts/make_environmetrics_figures.R",
    "scripts/build_he2_bayesian_publication_manifest.py",
    "scripts/build_he2_publication_parity_gate.py",
    "scripts/build_he4_quantile_check_loss_tables.py",
    "scripts/he2_exdqlm_keep_authoritative.py",
    "scripts/he2_publication_relaunch_lib.py",
    "scripts/validate_current_authority_sync.sh",
    "scripts/validate_publication_freeze.py",
    "scripts/validate_revision_cross_repo_wiring.py",
    "scripts/validate_he2_selected_output_authority.py",
]

TEST_FILES = [
    "tests/python/test_software_availability_contract.py",
    "tests/python/test_he2_bayesian_publication_manifest.py",
    "tests/python/test_he2_publication_parity_gate.py",
    "tests/python/test_he2_selected_output_authority.py",
    "tests/python/test_he4_quantile_check_loss_tables.py",
    "tests/python/test_publication_freeze_validation.py",
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
    "artifacts/he2_historical_support_audit",
    "artifacts/he2_publication_freeze",
    "artifacts/he3_exdqlm_ablation_authoritative",
    "artifacts/he4_quantile_check_loss_current_publication",
    "artifacts/historical_support_from_current_models",
    "artifacts/latest_forecast_issue",
    "artifacts/representative_selected_model_2022_12_25",
    "artifacts/runtime_benchmark",
    "artifacts/software_availability",
]


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
        or rerun the reported case-study analysis. It does not contain raw
        climate-center archives, active runtime campaigns, local notebooks,
        poster drafts, or generated screening/audit outputs.

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
           configuration files, and staged input bundles in `data/staged/` to
           rerun the reported exDQLM/DQLM case-study fits. This requires the
           public CRAN package `exdqlm` and sufficient local compute.
        3. **Raw archive reconstruction.** Not bundled. Reconstructing a new
           retrospective validation archive requires agency-specific historical
           products, version matching, spatial extraction, forecast-window
           covariate staging, and source-specific horizon handling.

        ## Main Directories

        - `R/`: selected model, post-processing, and figure-generation code.
        - `scripts/`: orchestration, manifest, and validation scripts.
        - `config/`: selected publication and authority configuration files.
        - `data/staged/`: compact staged inputs used by the five cutoff cases.
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

        Exact source paths and export-time commits are preserved only in
        `provenance/source_file_crosswalk.csv` and
        `provenance/runtime_source_crosswalk.csv`.

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
        publication workflow. Filenames are intentionally descriptive; original
        source paths and hashes are recorded in
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

        This directory contains selected publication-authority configuration
        files and manifests. Legacy exploratory grids and screening configs are
        not exported.
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
            "tables/generated_tex/benchmark_crps_main_table.tex",
            "figures/manuscript_context/site_context_usgs.png",
            "outputs/expected/artifacts/he2_publication_freeze/he2_bayesian_publication_manifest.csv",
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
        ALLOWED_LOCAL_PATH_FILES = {
            "provenance/source_file_crosswalk.csv",
            "provenance/runtime_source_crosswalk.csv",
        }
        LOCAL_PATH_MARKERS = ("/" + "data/muscat_data/", "/" + "data/jaguir26/")
        STALE_TEXT_MARKERS = (
            "https://github.com/AntonioAPDL/" + "Project1",
            "PROJECT1" + "_URL",
            "chat" + "gpt",
            "co" + "dex",
            "ai" + "-generated",
            "ai " + "wording",
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
                    if rel not in ALLOWED_LOCAL_PATH_FILES and any(marker in text for marker in LOCAL_PATH_MARKERS):
                        errors.append(f"local absolute path outside provenance crosswalk: {rel}")
                    for marker in STALE_TEXT_MARKERS:
                        if marker.lower() in lower_text:
                            errors.append(f"stale/internal marker {marker!r} in {rel}")

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
        normalized_rows.append(normalized)
    with crosswalk.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["role", "public_path", "source_path", "bytes", "sha256"])
        writer.writeheader()
        writer.writerows(normalized_rows)

    runtime_crosswalk = roots.destination / "provenance/runtime_source_crosswalk.csv"
    with runtime_crosswalk.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["role", "path", "git_head", "remote"])
        writer.writeheader()
        writer.writerow(
            {
                "role": "workflow_source",
                "path": roots.workflow.as_posix(),
                "git_head": git_commit(roots.workflow),
                "remote": git_remote(roots.workflow),
            }
        )
        writer.writerow(
            {
                "role": "article_source",
                "path": roots.article.as_posix(),
                "git_head": git_commit(roots.article),
                "remote": git_remote(roots.article),
            }
        )
        writer.writerow(
            {
                "role": "runtime_shared_input_bundle",
                "path": (roots.runtime / SHARED_INPUT_BUNDLE).as_posix(),
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

    for item in CONFIG_FILES:
        src = roots.workflow / item
        if item.startswith("config/"):
            dst = roots.destination / "config/publication" / Path(item).name
        else:
            dst = roots.destination / "config/authority" / Path(item).name
        copy_file(src, dst, "workflow_config", rows, replacements)

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
