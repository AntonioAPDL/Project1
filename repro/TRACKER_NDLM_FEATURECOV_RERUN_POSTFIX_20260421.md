# NDLM Featurecov Postfix Rerun Tracker

Date opened: 2026-04-21  
Status: active

## Purpose

This tracker records the full clean NDLM rerun launched after the post-correction reaudit identified a multivariate post predictive-sampling bug in the earlier corrected rerun.

The bug fix is in:

- [R/environmetrics/02_helpers_core.R](/data/muscat_data/jaguir26/project1_ucsc_phd/R/environmetrics/02_helpers_core.R)

This rerun is intended to regenerate the manuscript-facing NDLM values from the fixed code path under the same shared featurecov and deterministic-climate contract.

## Why This Rerun Exists

The post-correction reaudit concluded that:

- the NDLM Kalman core is numerically sound
- the scoring tables are internally consistent
- the multivariate NDLM predictive draws were contaminated by a sigma-row mixing bug

So the previous corrected NDLM rerun is not trustworthy for final manuscript values, even though it completed successfully as a campaign.

## Campaign Identity

- campaign id:
  `multimodel_v8_ndlm_featurecov_rerun_postfix_20260421`
- spec id:
  `ndlm_featurecov_v1_postfix`
- runtime root:
  [/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_ndlm_featurecov_rerun_postfix_20260421](/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_ndlm_featurecov_rerun_postfix_20260421)

## Scope

- `15` rows total
- families:
  - `ndlm_main_keep`
  - `ndlm_main_drop`
  - `ndlm_univar_keep`
- cutoffs:
  - `20210123`
  - `20211112`
  - `20211221`
  - `20220511`
  - `20221225`

## Validation Status

- prelaunch validation: passed
  - [prelaunch_validation_summary.json](/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_ndlm_featurecov_rerun_postfix_20260421/control/prelaunch_validation_20260421T222408Z/prelaunch_validation_summary.json)
- unit/regression tests used in the gate:
  - `tests.python.test_ndlm_wishart_prior_audit`
  - `tests.python.test_ndlm_featurecov_rerun_builder`
  - `tests/testthat/test_ndlm_fitloop_contract.R`
  - `tests/testthat/test_ndlm_save_state.R`

## Live State

- controller PID:
  [controller.pid](/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_ndlm_featurecov_rerun_postfix_20260421/control/ndlm_featurecov_v1/controller_state/controller.pid)
- last launch metadata:
  [last_launch.json](/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_ndlm_featurecov_rerun_postfix_20260421/control/ndlm_featurecov_v1/controller_state/last_launch.json)
- matrix state:
  [matrix_status.csv](/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_ndlm_featurecov_rerun_postfix_20260421/control/ndlm_featurecov_v1/matrix_status.csv)
- queue log:
  [queue.log](/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_ndlm_featurecov_rerun_postfix_20260421/control/ndlm_featurecov_v1/queue.log)

## Current Read

At the latest check:

- `20210123` is fully closed
- `20211112` is fully closed
- `20211221` multivariate rows are active
- controller is running in the background
- no active blocker has been observed in the postfix campaign so far

## Checklist

### Setup

- [x] Create postfix rerun template
- [x] Build new 15-row matrix
- [x] Run prelaunch validation
- [x] Confirm smoke runs through `post`
- [x] Launch detached queue controller

### Runtime

- [x] Confirm first cutoff closes cleanly
- [x] Confirm second cutoff closes cleanly
- [ ] Monitor remaining cutoffs to completion
- [ ] Verify final controller shutdown is clean

### Downstream

- [ ] Refresh NDLM manuscript-facing CRPS values from postfix rerun
- [ ] Update HE2 NDLM rows in `Corrections---Project-1`
- [ ] Update any explanatory prose if the NDLM ranking changes materially
