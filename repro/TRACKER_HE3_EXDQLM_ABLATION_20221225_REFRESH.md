# HE3 `20221225` Refresh Tracker

## Goal

Refresh the HE3 ablation slice for cutoff `20221225` so it is anchored to the
current published HE2 `exAL-M-T1` winner:

- published full reference:
  `multimodel_20221225_v8_exalm_t1_discount_grid_exact_v1_set09_exdqlm_multivar_keep`
- published mean CRPS:
  `0.4375250570387207`

The relaunch must remain structurally identical to the original HE3 study aside
from the updated full-model discount block inherited from the new published
winner.

## Investigation Status

- [x] Confirm the current manuscript-facing discrepancy is isolated to HE3 at `20221225`
- [x] Compare original HE3 full reference against the new published HE2 winner
- [x] Confirm covariates, blended forecasts, deterministic-climate futures, and engineered features are unchanged
- [x] Confirm the scientific difference is confined to the state-evolution discount block
- [x] Decide the minimal relaunch scope
- [x] Prepare focused builder / validator support for a cutoff-filtered refresh
- [x] Freeze a dedicated refresh template using the new published source run
- [x] Add regression coverage for the focused refresh path
- [x] Validate the focused refresh path locally
- [x] Launch the focused refresh campaign
- [x] Rebuild HE3 summary / audit outputs from the refreshed slice
- [x] Update the corrections repo if HE3 table values change materially

## Scope Decision

The refresh scope is:

- cutoff: `20221225` only
- reused full row: `1`
- launched ablation rows: `5`
  - `noTrend`
  - `noTF`
  - `noH1`
  - `noH2`
  - `noH3`

This is sufficient because the other four HE3 full references still match the
current published HE2 `exAL-M-T1` rows exactly.

## Runtime Contract

- baseline family: `exdqlm_multivar_keep`
- likelihood: `exal`
- transfer mode:
  - full / `noTrend` / `noH1` / `noH2` / `noH3` -> `keep`
  - `noTF` -> `drop`
- fit covariates: `PPT|SOIL|PCA`
- deterministic climate: enabled
- engineered features:
  - lags `1|2|3`
  - squares enabled
  - interaction enabled
- launched quantile models:
  - `fit.parallel.workers = 1`
  - `run.threads.mc_cores = 1`
- queue concurrency:
  - up to `4` launched rows at once

## Source of Truth

- refresh template:
  [config/multimodel_v8_he3_exdqlm_ablation_20221225_refresh.template.yaml](/data/muscat_data/jaguir26/project1_ucsc_phd/config/multimodel_v8_he3_exdqlm_ablation_20221225_refresh.template.yaml)
- investigation note:
  [he3_ablation_refresh_investigation.md](/data/muscat_data/jaguir26/project1_ucsc_phd/reports/he3_ablation_refresh_20221225/he3_ablation_refresh_investigation.md)
- workflow:
  [HE3_EXDQLM_ABLATION_20221225_REFRESH_WORKFLOW.md](/data/muscat_data/jaguir26/project1_ucsc_phd/repro/run/HE3_EXDQLM_ABLATION_20221225_REFRESH_WORKFLOW.md)
- refresh summary:
  [/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he3_exdqlm_ablation_20221225_refresh_20260426/reports/he3_exdqlm_ablation/he3_ablation_summary.md](/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he3_exdqlm_ablation_20221225_refresh_20260426/reports/he3_exdqlm_ablation/he3_ablation_summary.md)
- refresh audit:
  [/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he3_exdqlm_ablation_20221225_refresh_20260426/reports/he3_exdqlm_ablation/audit/he3_ablation_audit.md](/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he3_exdqlm_ablation_20221225_refresh_20260426/reports/he3_exdqlm_ablation/audit/he3_ablation_audit.md)
