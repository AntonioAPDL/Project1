# NDLM Parity Audit Phase 1 Inventory and Provenance

Date: 2026-04-20
Phase: 1 of 8
Status: complete

## Purpose

This note records the current source-of-truth surfaces for the NDLM models before any fairness or performance analysis. The goal of Phase 1 is not to diagnose the CRPS gap yet, but to identify the exact code, configs, runtime artifacts, exports, and theory notes that define the current Normal-likelihood models and their comparison context.

## Main Phase 1 Findings

1. The current unified NDLM execution path is modular and theory-oriented:
   - [run_ndlm_main.R](/data/muscat_data/jaguir26/project1_ucsc_phd/scripts/run_ndlm_main.R)
   - [run_ndlm_univar.R](/data/muscat_data/jaguir26/project1_ucsc_phd/scripts/run_ndlm_univar.R)
   - [R/unified/families/ndlm_main](/data/muscat_data/jaguir26/project1_ucsc_phd/R/unified/families/ndlm_main)
   - [R/unified/families/ndlm_univar](/data/muscat_data/jaguir26/project1_ucsc_phd/R/unified/families/ndlm_univar)

2. The final manuscript-facing best9 export manifest currently packages NDLM rows from the older baseline-TT run tree:
   - [selection_manifest.csv](/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_20260402/exports/best9_cutoff_png_package_20260406/selection_manifest.csv)

3. A separate dedicated NDLM relaunch campaign exists, with its own configs, reports, and contract diagnostics:
   - [multimodel_v8_ndlm_20260411](/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_ndlm_20260411)

4. The current featurecov cf1 config surface for NDLM explicitly includes deterministic climate, blended forecast covariates, transfer-function features, and a forecast covariance prior block:
   - [multimodel_20221225_v8_eps360cf1_ndlm_main_keep_featurecov_cf1.yaml](/data/muscat_data/jaguir26/project1_ucsc_phd/config/unified_runs_featurecov_cf1_eps_20260416/multimodel_20221225_v8_eps360cf1_ndlm_main_keep_featurecov_cf1.yaml)

5. There are already internal theory and parity audit notes that must be incorporated into the later phases:
   - [NDLM_EXDQLM_COMPARISON_AUDIT_20260226.md](/data/muscat_data/jaguir26/project1_ucsc_phd/repro/NDLM_EXDQLM_COMPARISON_AUDIT_20260226.md)
   - [P4_NDLM_CONTRACTS_SMOKE_20260211_095407.md](/data/muscat_data/jaguir26/project1_ucsc_phd/repro/P4_NDLM_CONTRACTS_SMOKE_20260211_095407.md)
   - [theory_spec_checklist.md](/data/muscat_data/jaguir26/project1_ucsc_phd/theory_spec_checklist.md)

## Authoritative Code Surfaces

### Unified NDLM main family

Primary execution path:

- [run_ndlm_main.R](/data/muscat_data/jaguir26/project1_ucsc_phd/scripts/run_ndlm_main.R)
- [zz_run.R](/data/muscat_data/jaguir26/project1_ucsc_phd/R/unified/families/ndlm_main/zz_run.R)

Module files:

- [00_constants.R](/data/muscat_data/jaguir26/project1_ucsc_phd/R/unified/families/ndlm_main/00_constants.R)
- [01_inputs.R](/data/muscat_data/jaguir26/project1_ucsc_phd/R/unified/families/ndlm_main/01_inputs.R)
- [02_model_spec.R](/data/muscat_data/jaguir26/project1_ucsc_phd/R/unified/families/ndlm_main/02_model_spec.R)
- [03_vb_updates.R](/data/muscat_data/jaguir26/project1_ucsc_phd/R/unified/families/ndlm_main/03_vb_updates.R)
- [04_elbo.R](/data/muscat_data/jaguir26/project1_ucsc_phd/R/unified/families/ndlm_main/04_elbo.R)
- [05_fitloop.R](/data/muscat_data/jaguir26/project1_ucsc_phd/R/unified/families/ndlm_main/05_fitloop.R)
- [06_save_state.R](/data/muscat_data/jaguir26/project1_ucsc_phd/R/unified/families/ndlm_main/06_save_state.R)
- [07_state_registry.R](/data/muscat_data/jaguir26/project1_ucsc_phd/R/unified/families/ndlm_main/07_state_registry.R)
- [08_vb_cavi_exact.R](/data/muscat_data/jaguir26/project1_ucsc_phd/R/unified/families/ndlm_main/08_vb_cavi_exact.R)
- [ndlm_kalman_backend.cpp](/data/muscat_data/jaguir26/project1_ucsc_phd/R/unified/families/ndlm_main/ndlm_kalman_backend.cpp)

Phase 1 interpretation:

- The current main NDLM path is not a legacy monolith. It is a modular unified-family implementation with explicit theory logs and contract surfaces.

### Unified NDLM univariate family

Primary execution path:

- [run_ndlm_univar.R](/data/muscat_data/jaguir26/project1_ucsc_phd/scripts/run_ndlm_univar.R)
- [zz_run.R](/data/muscat_data/jaguir26/project1_ucsc_phd/R/unified/families/ndlm_univar/zz_run.R)

Module files:

- [00_constants.R](/data/muscat_data/jaguir26/project1_ucsc_phd/R/unified/families/ndlm_univar/00_constants.R)
- [01_inputs.R](/data/muscat_data/jaguir26/project1_ucsc_phd/R/unified/families/ndlm_univar/01_inputs.R)
- [02_model_spec.R](/data/muscat_data/jaguir26/project1_ucsc_phd/R/unified/families/ndlm_univar/02_model_spec.R)
- [03_filter_forecast_fit.R](/data/muscat_data/jaguir26/project1_ucsc_phd/R/unified/families/ndlm_univar/03_filter_forecast_fit.R)
- [04_save_state.R](/data/muscat_data/jaguir26/project1_ucsc_phd/R/unified/families/ndlm_univar/04_save_state.R)
- [05_fitloop.R](/data/muscat_data/jaguir26/project1_ucsc_phd/R/unified/families/ndlm_univar/05_fitloop.R)
- [ndlm_univar_kalman_backend.cpp](/data/muscat_data/jaguir26/project1_ucsc_phd/R/unified/families/ndlm_univar/ndlm_univar_kalman_backend.cpp)

Phase 1 interpretation:

- The current univariate NDLM path is also modular and separate from the legacy root-level NDLM scripts.

## Current Config Surfaces

### Featurecov cf1 sweep configs

Key NDLM config example:

- [multimodel_20221225_v8_eps360cf1_ndlm_main_keep_featurecov_cf1.yaml](/data/muscat_data/jaguir26/project1_ucsc_phd/config/unified_runs_featurecov_cf1_eps_20260416/multimodel_20221225_v8_eps360cf1_ndlm_main_keep_featurecov_cf1.yaml)

Why it matters:

- it is the clearest current config surface for checking:
  - `implementation_mode`
  - `forecast_transfer_mode`
  - deterministic climate on/off
  - transfer covariates and engineered terms
  - forecast covariance prior fields
  - state-evolution discount factors

Observed config fields to carry into later audits:

- `models.ndlm_main.implementation_mode: theory_aligned`
- `models.ndlm_main.kalman_backend: cpp`
- `models.ndlm_main.forecast_transfer_mode: keep`
- `models.ndlm_main.prior.forecast_cov.*`
- `transfer_function_covariates.base_covariates`
- `transfer_function_covariates.engineered_terms`
- `inputs.deterministic_climate.*`

Quantile-model comparison config used to anchor parity later:

- [multimodel_20221225_v8_eps360cf1_exdqlm_multivar_keep_featurecov_cf1.yaml](/data/muscat_data/jaguir26/project1_ucsc_phd/config/unified_runs_featurecov_cf1_eps_20260416/multimodel_20221225_v8_eps360cf1_exdqlm_multivar_keep_featurecov_cf1.yaml)

Why it matters:

- this gives us the current multivariate exDQLM spec that NDLM should match as closely as possible outside the likelihood family.

### Dedicated NDLM campaign template

- [multimodel_v8_ndlm_campaign.template.yaml](/data/muscat_data/jaguir26/project1_ucsc_phd/config/multimodel_v8_ndlm_campaign.template.yaml)

Why it matters:

- this is the dedicated relaunch campaign contract for NDLM-only tuning and compares current-v8 vs retuned NDLM settings
- it records family-to-lane mappings:
  - `ndlm_main_keep -> l1`
  - `ndlm_main_drop -> l2`
  - `ndlm_univar_keep -> l1`

## Runtime And Diagnostic Surfaces

### Baseline-TT run tree feeding current best9 export

- [multimodel_v8_20260402](/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_20260402)
- [selection_manifest.csv](/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_20260402/exports/best9_cutoff_png_package_20260406/selection_manifest.csv)

Observed provenance fact:

- NDLM rows in the packaged best9 export currently point to baseline-TT source runs such as:
  - `multimodel_20210123_v8_epsTT_l1`
  - `multimodel_20210123_v8_epsTT_l2`
  - `multimodel_20221225_v8_epsTT_l1`
  - `multimodel_20221225_v8_epsTT_l2`

This is a provenance observation only for now. Later phases must determine whether that is intended or whether a newer NDLM relaunch should have replaced them.

### Dedicated NDLM relaunch runtime root

- [multimodel_v8_ndlm_20260411](/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_ndlm_20260411)

Important runtime artifacts present there:

- per-cutoff compare reports
- `source_provenance.csv`
- `model_coverage.csv`
- fit logs
- theory logs
- contract checks
- saved diagnostics under `diagnostics/ndlm`

Representative files:

- [summary.md](/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_ndlm_20260411/reports/multimodel_20211112_v8_ndlm_tune_20260411_v1_compare/summary.md)
- [source_provenance.csv](/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_ndlm_20260411/reports/multimodel_20211112_v8_ndlm_tune_20260411_v1_compare/source_provenance.csv)
- [crps_forecast_summary_all_models.csv](/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_ndlm_20260411/reports/multimodel_20211112_v8_ndlm_tune_20260411_v1_compare/crps_forecast_summary_all_models.csv)
- [ndlm_horizon_contract.md](/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_ndlm_20260411/runs/multimodel_20211221_v8_ndlm_tune_20260411_v1_ndlm_main_keep/diagnostics/ndlm/ndlm_horizon_contract.md)

Phase 1 interpretation:

- there is already a dedicated NDLM runtime lineage separate from the baseline-TT export lineage
- reconciling those two lineages is a required later step

## Theory, Contract, And Audit Documents Already Present

### Internal repo docs

- [NDLM_EXDQLM_COMPARISON_AUDIT_20260226.md](/data/muscat_data/jaguir26/project1_ucsc_phd/repro/NDLM_EXDQLM_COMPARISON_AUDIT_20260226.md)
- [P4_NDLM_CONTRACTS_SMOKE_20260211_095407.md](/data/muscat_data/jaguir26/project1_ucsc_phd/repro/P4_NDLM_CONTRACTS_SMOKE_20260211_095407.md)
- [P4_NDLM_THEORY_SMOKE_20260210_235222.md](/data/muscat_data/jaguir26/project1_ucsc_phd/repro/P4_NDLM_THEORY_SMOKE_20260210_235222.md)
- [P3_UNIVAR_THEORY_SMOKE_20260210_234304.md](/data/muscat_data/jaguir26/project1_ucsc_phd/repro/P3_UNIVAR_THEORY_SMOKE_20260210_234304.md)
- [theory_spec_checklist.md](/data/muscat_data/jaguir26/project1_ucsc_phd/theory_spec_checklist.md)

Why they matter:

- these already encode prior reconciliation work between NDLM theory, NDLM implementation, and exDQLM implementation
- later phases should reuse them rather than rebuilding everything from scratch

### External/local theory repos and folders

- [NDLM---Ensemble](/data/muscat_data/jaguir26/NDLM---Ensemble)
- [DQLM-and-BQR---Theory](/data/muscat_data/jaguir26/DQLM-and-BQR---Theory)

Phase 1 interpretation:

- there is a separate local NDLM theory repository available for checking mathematical intent
- there is also a local DQLM/BQR theory repository that may help when comparing what is supposed to differ by likelihood only

## Legacy NDLM Surfaces Still Present

Legacy NDLM code still in the repo root:

- [Optimal_Synth_Ranges_NDLM.r](/data/muscat_data/jaguir26/project1_ucsc_phd/Optimal_Synth_Ranges_NDLM.r)
- [DISC_Optimal_Synth_Ranges_NDLM.r](/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_Optimal_Synth_Ranges_NDLM.r)
- [NDLM_Model1.r](/data/muscat_data/jaguir26/project1_ucsc_phd/NDLM_Model1.r)
- [Optimal_Model_Retro_NDLM.r](/data/muscat_data/jaguir26/project1_ucsc_phd/Optimal_Model_Retro_NDLM.r)
- [kalman_NDLM.cpp](/data/muscat_data/jaguir26/project1_ucsc_phd/kalman_NDLM.cpp)
- [kalman_synth_NDLM.cpp](/data/muscat_data/jaguir26/project1_ucsc_phd/kalman_synth_NDLM.cpp)
- [DISC_kalman_synth_NDLM.cpp](/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_kalman_synth_NDLM.cpp)

Phase 1 interpretation:

- these are historical/legacy reference points, not obviously the primary current unified path
- however, they may still matter for:
  - theory provenance
  - old baseline TT run lineage
  - understanding how current NDLM differs from older NDLM behavior

## Provenance Questions Uncovered By Phase 1

These are not yet answers. They are the questions that Phase 1 surfaced for the later audit.

1. Why do the manuscript-facing best9 export rows still point to baseline-TT NDLM runs while a dedicated NDLM relaunch runtime also exists?
2. Which NDLM run lineage should be treated as authoritative for the article tables?
3. Are the current featurecov cf1 configs actually the source of manuscript NDLM numbers, or only the quantile-model side?
4. Are the baseline-TT NDLM runs and dedicated NDLM relaunch runs using the same transfer/covariate contract?
5. Is the forecast-window covariance prior in `ndlm_main` traceable from config into the actual runtime diagnostics the way we expect?

## Phase 1 Deliverables Completed

- persistent tracker created:
  - [TRACKER_NDLM_PARITY_AUDIT.md](/data/muscat_data/jaguir26/project1_ucsc_phd/repro/TRACKER_NDLM_PARITY_AUDIT.md)
- workflow doc created:
  - [NDLM_PARITY_AUDIT_WORKFLOW.md](/data/muscat_data/jaguir26/project1_ucsc_phd/repro/run/NDLM_PARITY_AUDIT_WORKFLOW.md)
- this inventory/provenance report created:
  - [NDLM_PARITY_AUDIT_PHASE1_INVENTORY_20260420.md](/data/muscat_data/jaguir26/project1_ucsc_phd/repro/NDLM_PARITY_AUDIT_PHASE1_INVENTORY_20260420.md)

## Recommended Next Step

Proceed to Phase 2:

- build a strict label-to-family and manuscript/export provenance map for:
  - `N-U-T1`
  - `N-M-T0`
  - `N-M-T1`

That phase should settle which NDLM lineage is actually driving the current tables before we compare specifications or performance.
