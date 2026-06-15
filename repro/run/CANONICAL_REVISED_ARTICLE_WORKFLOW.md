# Canonical Revised Article Workflow

Date: 2026-05-07

Current path update: 2026-06-14

## Scope

This runbook defines the canonical reproduction and refresh workflow for the current revised article:

- article repo: `/data/muscat_data/jaguir26/project1_ucsc_phd/Evironmetrics---REVISED-DOC-Corrected-2`
- workflow repo: `/data/muscat_data/jaguir26/project1_ucsc_phd`

The goal is to keep one clear operational path from now on.

For the software availability and archival-release contract, use:

- `repro/run/REVISION_SOFTWARE_REPRODUCIBILITY_CONTRACT_20260615.md`

The legacy `repro/REPRODUCE_PAPER.md` is retained as historical context only
and is not the current revised-article reproduction contract.

As of the 2026-06-14 publication freeze, the article-side `generated/` and
`DISC/` naming layers are retired. The current manuscript-local freeze surface
is:

- `artifacts/`
- `figures/`
- `tables/generated_tex/`
- `reports/manuscript_asset_review/`
- `MANUSCRIPT_ASSET_MANIFEST.json`

Older references to `generated/` or `DISC/` in historical planning notes should
be translated through the article repo's `docs/article_repository_structure.md`
and `docs/article_repository_path_crosswalk.csv`.

## Canonical scripts to use

### 1. Model reruns and post-processing

Use:
- `scripts/unified_run.R`
- `R/unified/stages/stage_post.R`

These are the canonical orchestration and post-stage entrypoints.

### 2. Publication-lineage planning and verification

Use:
- `scripts/build_publication_replay_matrix.py`
- `scripts/build_publication_replay_representative_bundle.py`
- `scripts/launch_publication_replay_representatives.py`
- `scripts/refresh_publication_replay_representative_status.py`
- `scripts/validate_publication_replay_representatives.py`

These define and verify the publication replay contract.

### 3. Sensitive authoritative replay path

Use when needed for publication-equivalent exAL replay stability:
- `scripts/run_authoritative_r440_replay.sh`

This is the authoritative `R 4.4.0` replay path used for the sensitive publication rows.

### 4. Figure generation

Use two canonical figure paths:

#### 4A. General publication figures

- `R/environmetrics/40_figures.R`
- `scripts/run_environmetrics_figures.R`
- `R/unified/stages/stage_post.R`

This path covers the workflow-linked publication figures driven by the unified post stage.

#### 4B. Cutoff-specific setup/support figures

- `config/exal_m_t1_setup_support_by_cutoff_v2_20260507.json`
- `scripts/render_exal_m_t1_setup_support_by_cutoff_v2.py`
- `scripts/render_setup_support_bundle_v2.R`
- `scripts/setup_support_bundle_v2_helpers.R`
- `scripts/forecats_plot_bundle.R`
- `scripts/build_exal_m_t1_setup_support_v2_review.py`
- `scripts/validate_exal_m_t1_setup_support_v2.py`
- `repro/run/EXAL_M_T1_SETUP_SUPPORT_BY_CUTOFF_V2_WORKFLOW.md`

This path covers the cutoff-dependent setup/input/support figures for:
- `usgs.png`
- `precip_soilmoisture_climatePC1_faceted_labeled.png`
- `retrospective_log_discharge_plot_faceted.png`
- `forecats.png`

The current canonical `v2` contract is:
- `usgs.png` and the raw covariate figure use the full `1987-05-29 -> cutoff` daily history available in the selected-run shared inputs
- `retrospective_log_discharge_plot_faceted.png` uses the retrospective support actually available for the cutoff-specific bundle, with that availability surfaced explicitly in the review metadata
- `forecats.png` uses a strict `cutoff - 28 days` to `cutoff + 28 days` display window
- the support-flow figures are displayed on `log1p_cms`
- the current workflow now fixes retros, observations, forecast ensembles, fit internals, and post internals to `log1p_cms`

### 5. Article-side provenance freezing

Use:
- `Evironmetrics---REVISED-DOC-Corrected-2/scripts/refresh_exal_m_t1_generated_assets.py`
- `Evironmetrics---REVISED-DOC-Corrected-2/scripts/refresh_he2_manifest_snapshot.py`
- `Evironmetrics---REVISED-DOC-Corrected-2/scripts/refresh_setup_support_by_cutoff_v2.py`
- `Evironmetrics---REVISED-DOC-Corrected-2/scripts/build_setup_support_by_cutoff_v2_review.py`
- `Evironmetrics---REVISED-DOC-Corrected-2/scripts/build_setup_support_by_cutoff_v2_appendix.py`
- `Evironmetrics---REVISED-DOC-Corrected-2/scripts/promote_setup_support_v2_to_disc.py`
- `Evironmetrics---REVISED-DOC-Corrected-2/scripts/build_generated_asset_index.py`
- `Evironmetrics---REVISED-DOC-Corrected-2/scripts/refresh_all_generated_assets.py`

These are the canonical article-side refresh helpers.

- `refresh_all_generated_assets.py` is the preferred top-level entrypoint.
- The narrower helpers remain available when only one bundle family needs refresh.
- The generated-asset inventory is refreshed automatically and written to:
  - `Evironmetrics---REVISED-DOC-Corrected-2/artifacts/README.md`
  - `Evironmetrics---REVISED-DOC-Corrected-2/artifacts/artifact_inventory.csv`

## Non-canonical / legacy items to avoid

Do not treat these as the operational contract:
- `scripts/make_environmetrics_figures.R`
- direct notebook reruns from `Environmetrics_Figures.ipynb`
- manual article-side copying without manifest/hash refresh
- older free-form audit notes as substitutes for the current replay matrix or local bundles

Why:
- `scripts/make_environmetrics_figures.R` still depends on notebook-linearized state and legacy hard-coded external paths
- direct notebook reruns are too easy to drift from the current unified/run-scoped contract
- manual copying breaks provenance discipline

## Current article asset model

### A. Selected-model assets

Canonical source:
- verified `exAL-M-T1` publication reruns
- article-side bundles:
  - `artifacts/five_cutoff_crps_validation_sources/`
  - `artifacts/five_cutoff_main_model_synthesis/`
  - `artifacts/representative_selected_model_2022_12_25/`

### B. Historical-summary support assets

Canonical source:
- workflow-linked historical figure path
- article-side bundle:
  - `artifacts/historical_support_from_current_models/`

### C. Workflow-linked support assets

Canonical source:
- corrected `v2` cutoff-specific setup/support workflow:
  - `repro/run/EXAL_M_T1_SETUP_SUPPORT_BY_CUTOFF_V2_WORKFLOW.md`
  - `repro/run/EXAL_M_T1_SETUP_SUPPORT_V2_SOURCE_MANIFEST.md`
  - `repro/run/EXAL_M_T1_SETUP_SUPPORT_V2_FILE_PLAN.md`
  - `repro/run/EXAL_M_T1_SETUP_SUPPORT_V2_ACCEPTANCE_CHECKLIST.md`
- article-side bundle:
  - `artifacts/five_cutoff_setup_support/`
- article-side review:
  - `reports/five_cutoff_setup_support_review/`
- article-side appendix-ready composites:
  - `figures/appendix_cutoff_panels/`

These are the canonical per-cutoff setup/input/support figures for:
- `usgs.png`
- `precip_soilmoisture_climatePC1_faceted_labeled.png`
- `retrospective_log_discharge_plot_faceted.png`
- `forecats.png`

Article-facing promotion:
- the current revised manuscript promotes the representative cutoff
  - `20221225_exal_m_t1`
  into `figures/manuscript/` through:
  - `Evironmetrics---REVISED-DOC-Corrected-2/scripts/promote_setup_support_v2_to_disc.py`

Archival note:
- the older `generated/setup_support_by_cutoff/` family is superseded and
  should not be recreated as a canonical provenance path.

### D. Workflow-linked appendix reference assets

Canonical source:
- unified post -> figure-runner -> `40_figures.R`
- article-side bundle:
  - `artifacts/five_cutoff_reference_synthesis/`

This bundle is now mainly archival/supporting for workflow-linked appendix assets such as:
- `posterior_samples_counter_valid.png`

### E. HE2 benchmark table freeze

Canonical source:
- `reports/he2_publication_manifest/he2_bayesian_publication_manifest.md`
- article-side snapshot:
  - `artifacts/he2_publication_freeze/`

### F. Historical-support contract audit

Canonical source:
- `reports/he2_publication_manifest/historical_support_audit_20260507/historical_support_audit.md`
- article-side snapshot:
  - `artifacts/he2_historical_support_audit/`

Forward repair planning source:
- `repro/run/HE2_FULL_HISTORY_REPAIR_FORWARD_PLAN.md`

## Forward order of operations

### Step 1. Start from the canonical publication source of truth

Check:
- `reports/he2_publication_manifest/he2_bayesian_publication_manifest.md`
- `reports/publication_replay/publication_replay_matrix.md`
- `reports/publication_replay/representative_replay_verification.md`
- article-side provenance docs in `Evironmetrics---REVISED-DOC-Corrected-2/`

### Step 2. If a selected-model refresh is needed, rerun only through the canonical replay path

Use:
- publication replay configs under `config/publication_replay_representatives_20260506/`
- `scripts/unified_run.R`
- `scripts/run_authoritative_r440_replay.sh` when the sensitive authoritative path is required

### Step 3. Validate outputs before touching the article

Require:
- `summary.json`
- `compare_report.json`
- `crps_forecast_summary.csv`
- selected figure outputs
- table exports when applicable

### Step 4. Refresh article-side local bundles through the helper script

Use:
- `Evironmetrics---REVISED-DOC-Corrected-2/scripts/refresh_all_generated_assets.py`

That refreshes:
- workflow-linked support bundles,
- cutoff-specific setup/support figure bundles and review outputs,
- historical-summary bundles,
- the representative `exAL-M-T1` generated bundle,
- the five-run `exAL-M-T1` source freeze,
- the HE2 publication-manifest snapshot,
- and the article asset review report.

Generated review outputs:
- `reports/five_cutoff_setup_support_review/SETUP_SUPPORT_BY_CUTOFF_V2_REVIEW.md`
- `reports/five_cutoff_setup_support_review/gallery.html`
- `reports/five_cutoff_setup_support_review/figure_manifest.csv`
- `reports/manuscript_asset_review/ARTICLE_ASSET_REVIEW.md`
- `reports/manuscript_asset_review/figure_gallery.html`
- `reports/manuscript_asset_review/figure_manifest.csv`
- `reports/manuscript_asset_review/table_manifest.csv`
- `artifacts/README.md`
- `artifacts/artifact_inventory.csv`

### Step 5. Only then update manuscript assets or wording

After provenance is refreshed:
- update figure/table references if needed
- recompile the article
- re-run the article/corrections crosswalk if the scientific content changed

## Practical rules from now on

1. Treat `unified_run.R` as the canonical run entrypoint.
2. Treat `stage_post.R -> run_environmetrics_figures.R -> 40_figures.R` as the canonical figure pipeline for the workflow-linked publication figures.
3. Treat the `setup_support_by_cutoff_v2` workflow as the canonical figure pipeline for the four cutoff-specific setup/support figures.
4. Treat `refresh_all_generated_assets.py` as the canonical article-side refresh entrypoint.
5. Use the narrower helper scripts only when intentionally refreshing one bundle family in isolation.
6. Keep legacy notebook-style figure paths only as historical reference.
7. Do not update article assets without updating the matching provenance bundle and review report.

## Why this runbook exists

The project accumulated multiple historical reproduction paths. This runbook narrows them to one operational workflow so future work stays:
- documented,
- reproducible,
- consistent with the current publication lineage,
- and less dependent on institutional memory.
