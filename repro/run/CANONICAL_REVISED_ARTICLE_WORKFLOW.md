# Canonical Revised Article Workflow

Date: 2026-05-06

## Scope

This runbook defines the canonical reproduction and refresh workflow for the current revised article:

- article repo: `/data/muscat_data/jaguir26/project1_ucsc_phd/Evironmetrics---REVISED-DOC-2`
- workflow repo: `/data/muscat_data/jaguir26/project1_ucsc_phd`

The goal is to keep one clear operational path from now on.

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

Use:
- `R/environmetrics/40_figures.R`
- `scripts/run_environmetrics_figures.R`
- `R/unified/stages/stage_post.R`

The intended current path is:
- `stage_post.R` wires run-scoped shared inputs into the environment
- `run_environmetrics_figures.R` runs the figure stack headlessly
- `40_figures.R` generates the publication-facing figures

### 5. Article-side provenance freezing

Use:
- `Evironmetrics---REVISED-DOC-2/scripts/refresh_local_provenance_bundles.py`

This is the canonical article-side helper for rebuilding the local support bundles from the current `DISC/` assets and workflow gold manifest.

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
  - `generated/exal_m_t1_five_run_sources/`
  - `generated/exal_m_t1_20221225/`

### B. Historical-summary support assets

Canonical source:
- workflow-linked historical figure path
- article-side bundle:
  - `generated/historical_summary_sources/`

### C. Workflow-linked support assets

Canonical source:
- unified post -> figure-runner -> `40_figures.R`
- article-side bundle:
  - `generated/workflow_linked_support_sources/`

### D. HE2 benchmark table freeze

Canonical source:
- `reports/he2_publication_manifest/he2_bayesian_publication_manifest.md`
- article-side snapshot:
  - `generated/he2_publication_manifest_snapshot/`

## Forward order of operations

### Step 1. Start from the canonical publication source of truth

Check:
- `reports/he2_publication_manifest/he2_bayesian_publication_manifest.md`
- `reports/publication_replay/publication_replay_matrix.md`
- `reports/publication_replay/representative_replay_verification.md`
- article-side provenance docs in `Evironmetrics---REVISED-DOC-2/`

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
- `Evironmetrics---REVISED-DOC-2/scripts/refresh_local_provenance_bundles.py`

That keeps article-side copies, manifests, and hashes synchronized.

### Step 5. Only then update manuscript assets or wording

After provenance is refreshed:
- update figure/table references if needed
- recompile the article
- re-run the article/corrections crosswalk if the scientific content changed

## Practical rules from now on

1. Treat `unified_run.R` as the canonical run entrypoint.
2. Treat `stage_post.R -> run_environmetrics_figures.R -> 40_figures.R` as the canonical figure pipeline.
3. Treat `refresh_local_provenance_bundles.py` as the canonical article-side bundle refresher.
4. Keep legacy notebook-style figure paths only as historical reference.
5. Do not update article assets without updating the matching provenance bundle.

## Why this runbook exists

The project accumulated multiple historical reproduction paths. This runbook narrows them to one operational workflow so future work stays:
- documented,
- reproducible,
- consistent with the current publication lineage,
- and less dependent on institutional memory.
