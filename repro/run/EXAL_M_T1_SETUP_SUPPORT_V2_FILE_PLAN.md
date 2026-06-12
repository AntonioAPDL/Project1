# exAL-M-T1 Setup/Support v2 File-by-File Plan

Date: 2026-05-07

## Purpose

This document defines the **exact file-level implementation plan** for replacing the current cutoff-specific setup/support figure workflow with a corrected `v2` workflow.

The goal is to:

- keep the published `exAL-M-T1` run lineage fixed,
- switch the figure generation over to the correct authoritative bundle sources,
- avoid the merged model-matrix shortcut,
- and mirror the new figure family into the revised article repo automatically.

## Summary of the architectural change

The current `v1` workflow should be treated as an experiment:

- it correctly targeted the five verified `exAL-M-T1` cutoffs,
- but it rendered from `10_data_inputs.R` / `40_figures_setup_support.R`,
- which is not the right source layer for these figures.

The `v2` workflow should instead be:

1. **bundle-native**
2. **cutoff-explicit**
3. **version-policy-aware**
4. **self-describing**

That means:
- `forecats.png` should be built on top of `scripts/forecats_plot_bundle.R`
- the other three figures should read raw bundle/run files directly, not model matrices
- the workflow must carry both:
  - selected model run provenance,
  - and figure-bundle provenance
  - and an explicit display-scale contract so the figure surface does not silently drift from the stored fit-input scale

## Files to create

### 1. Canonical config / manifest inputs

Create:
- `config/exal_m_t1_setup_support_by_cutoff_v2_20260507.json`

Purpose:
- explicit machine-readable config for the corrected `v2` figure workflow
- one row per cutoff, using the canonical source manifest in:
  - `repro/run/EXAL_M_T1_SETUP_SUPPORT_V2_SOURCE_MANIFEST.md`

Must include per cutoff:
- cutoff slug
- cutoff date
- published CRPS
- selected model run root
- figure bundle root
- bundle class
- NWS policy summary
- GloFAS policy summary
- support-start mode
- forecast plot window mode

### 2. Runtime-side orchestrator

Create:
- `scripts/render_exal_m_t1_setup_support_by_cutoff_v2.py`

Purpose:
- orchestrate the corrected cutoff-by-cutoff rendering
- read `v2` config
- prepare per-cutoff output dirs
- call the new R renderer
- build runtime review manifests

This should replace:
- the operational role of `scripts/render_exal_m_t1_setup_support_by_cutoff.py`

but the old script should remain in the repo as historical `v1` scaffolding, not be deleted immediately.

### 3. Bundle-native R renderer

Create:
- `scripts/render_setup_support_bundle_v2.R`

Purpose:
- render all four figures for one cutoff using only:
  - canonical bundle files,
  - canonical selected-run shared files,
  - and structured metadata passed by the orchestrator

This should be the main rendering engine for:
- `usgs.png`
- `precip_soilmoisture_climatePC1_faceted_labeled.png`
- `retrospective_log_discharge_plot_faceted.png`
- `forecats.png`

It should **not** source:
- `R/environmetrics/10_data_inputs.R`
- `R/environmetrics/40_figures_setup_support.R`

### 4. Shared helper module for bundle-native support plots

Create:
- `scripts/setup_support_bundle_v2_helpers.R`

Purpose:
- keep the renderer clean and explicit
- centralize:
  - bundle metadata parsing
  - support-start detection
  - retrospective source resolution
  - covariate slicing
  - scale transforms
  - dynamic y-limit helpers
  - QA summaries for manifests

Recommended helper responsibilities:
- `read_bundle_meta()`
- `resolve_support_start()`
- `load_retros_lineage_for_cutoff()`
- `load_covariate_history_for_cutoff()`
- `load_usgs_history_for_cutoff()`
- `load_forecast_window_inputs_for_cutoff()`
- `compute_dynamic_ylim()`

### 5. Review/QA builder

Create:
- `scripts/build_exal_m_t1_setup_support_v2_review.py`

Purpose:
- build the runtime-side:
  - `review/REVIEW.md`
  - `review/gallery.html`
  - `review/figure_manifest.csv`
  - cutoff policy summary table

This should replace the review role currently embedded in the `v1` Python orchestrator.

### 6. Article-side mirror helper

Create:
- `Evironmetrics---REVISED-DOC-Corrected/scripts/refresh_setup_support_by_cutoff_v2.py`

Purpose:
- mirror the corrected runtime family into:
  - `generated/setup_support_by_cutoff_v2/`

### 7. Article-side review builder

Create:
- `Evironmetrics---REVISED-DOC-Corrected/scripts/build_setup_support_by_cutoff_v2_review.py`

Purpose:
- build:
  - `generated/setup_support_by_cutoff_v2_review/SETUP_SUPPORT_BY_CUTOFF_V2_REVIEW.md`
  - `generated/setup_support_by_cutoff_v2_review/gallery.html`
  - `generated/setup_support_by_cutoff_v2_review/figure_manifest.csv`

## Files to modify

### 1. `scripts/forecats_plot_bundle.R`

Modify carefully.

Why:
- this is the best existing bundle-native plotting foundation
- it already understands:
  - bundle `meta.yaml`
  - `retros_daily.csv`
  - weighted forecast files
  - retrospective-source labeling

Required changes:
- factor reusable data-loading helpers so `render_setup_support_bundle_v2.R` can call them cleanly
- allow a caller to inject a USGS path when the bundle itself lacks `inputs/usgs_daily.csv`
- preserve current `forecats.png` behavior for existing consumers

Important:
- do not turn this into a mixed model-matrix script
- keep it bundle-native

### 2. `repro/run/CANONICAL_REVISED_ARTICLE_WORKFLOW.md`

Modify to:
- demote the current `setup_support_by_cutoff_20260506` family from “canonical”
- point to the new `v2` workflow once implemented

### 3. `repro/run/EXAL_M_T1_SETUP_SUPPORT_BY_CUTOFF_WORKFLOW.md`

Modify to:
- label it as `v1`
- keep it as historical audit context
- explicitly say it should not be used for the final article freeze

### 4. `Evironmetrics---REVISED-DOC-Corrected/FIGURE_TABLE_PROVENANCE.md`

Modify to:
- mark `generated/setup_support_by_cutoff/` as provisional `v1`
- point setup/support figure provenance to `setup_support_by_cutoff_v2/` after implementation

### 5. `Evironmetrics---REVISED-DOC-Corrected/EXAL_M_T1_ARTIFACT_RUN_MAP.md`

Modify to:
- split setup/support provenance into:
  - `v1` debugging artifact
  - `v2` canonical article-side family

### 6. `Evironmetrics---REVISED-DOC-Corrected/MANUSCRIPT_REVISION_CHECKLIST.md`

Modify to:
- track the `v2` rollout explicitly
- prevent the old `v1` cutoff figure family from being treated as done

### 7. `Evironmetrics---REVISED-DOC-Corrected/scripts/refresh_all_generated_assets.py`

Modify to:
- call the new `v2` article-side refresh helper and review builder
- keep `v1` refresh optional or remove it from the default path after the new family is validated

## Files to demote from canonical status

These should remain in the repo, but be explicitly demoted from canonical use:

- `scripts/render_exal_m_t1_setup_support_by_cutoff.py`
- `scripts/render_setup_support_figures.R`
- `R/environmetrics/40_figures_setup_support.R`
- `generated/setup_support_by_cutoff/`
- `generated/setup_support_by_cutoff_review/`

Reason:
- they are useful for audit comparison,
- but they should no longer be the article-facing contract after `v2` is implemented.

## Figure-specific implementation rules

### `usgs.png`

Implementation rule:
- use `selected_run_root/inputs/shared/usgs/usgs_daily.csv`

Window rule:
- start = historical support start for the cutoff
- end = `cutoff_date`

Do not:
- use `Y[1, ]`
- use `timestamps`
- merge with covariates before plotting

### `precip_soilmoisture_climatePC1_faceted_labeled.png`

Implementation rule:
- read the three raw covariate files directly from the selected model run root

Window rule:
- same historical support start as the retrospective support for that cutoff
- end = `cutoff_date`

Do not:
- use `X`
- use model-matrix row count as the primary authority

### `retrospective_log_discharge_plot_faceted.png`

Implementation rule:
- for histfix cutoffs:
  - use `retros_source_lineage.csv`
- for short-window cutoffs:
  - use `inputs/retros_daily.csv` + policy extracted from bundle `meta.yaml`

Window rule:
- full retrospective fit-support window

Do not:
- use hard-coded y-limits
- use replay-packaged `source_map.txt` fallback as the primary provenance path

### `forecats.png`

Implementation rule:
- render from bundle-native files using the `forecats_plot_bundle.R` logic

Window rule:
- use the bundle metadata plot window

Do not:
- rebuild from model matrices
- infer the “before cutoff” retrospective lines from replay-wide `retros.csv` when richer bundle lineage exists

## Output family to create

Create a new runtime family:

- `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/exal_m_t1_setup_support_by_cutoff_v2_20260507/`

Per cutoff:
- `figures/`
- `metadata/`
- `logs/`
- `review/`

Required metadata files per cutoff:
- `metadata/source_model_run.txt`
- `metadata/source_figure_bundle.txt`
- `metadata/policy_summary.yaml`
- `metadata/support_window.yaml`
- `metadata/input_hashes.csv`

Mirror into article repo:
- `Evironmetrics---REVISED-DOC-Corrected/generated/setup_support_by_cutoff_v2/`
- `Evironmetrics---REVISED-DOC-Corrected/generated/setup_support_by_cutoff_v2_review/`

## Implementation order

1. create the `v2` config and manifest wiring
2. create the bundle-native helper and renderer
3. extend `forecats_plot_bundle.R` only where needed
4. render one short-window canary:
   - `2022-12-25`
5. render one histfix canary:
   - `2021-12-21`
6. validate against the acceptance checklist
7. only then scale to all five cutoffs
8. mirror into the article repo
9. update manuscript figure references only after visual QA is complete
