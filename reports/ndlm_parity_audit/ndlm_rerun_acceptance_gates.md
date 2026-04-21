# NDLM Featurecov Rerun Acceptance Gates

Date: 2026-04-21  
Status: passed, strengthened, and validated by the completed rerun

## Launch Gates

The corrected NDLM rerun is allowed to launch only if all of the following gates pass.

## Gate 1. Matrix Surface

- Builder completes successfully.
- Generated config count is `15`.
- Matrix plan count is `15`.
- Selection summary count is `15`.
- Families are exactly:
  - `ndlm_main_keep`
  - `ndlm_main_drop`
  - `ndlm_univar_keep`
- Cutoff coverage is exactly five cutoffs with three NDLM rows per cutoff.

## Gate 2. Corrected Featurecov Contract

Every generated config must:

- use fit covariates exactly `PPT`, `SOIL`, `PCA`
- enable `inputs.covariate_features`
- enable deterministic-climate blending
- point to an existing GEFS/NWM handoff root

## Gate 3. Corrected NDLM Main Prior Contract

Every `ndlm_main_*` config must carry:

- `dof_offset = 4`
- `scale_mult = 1.0`
- `df_covs = 0.99999999`

## Gate 4. Corrected NDLM Univariate Contract

Every `ndlm_univar_keep` config must carry:

- `n0 = 20`
- `S0 = 1`
- `df_covs = 0.99999999`

## Gate 5. Regression Coverage

The following test commands must pass:

```bash
python3 -m unittest \
  tests.python.test_ndlm_wishart_prior_audit \
  tests.python.test_ndlm_featurecov_rerun_builder

Rscript -e 'testthat::test_file("tests/testthat/test_ndlm_fitloop_contract.R"); \
            testthat::test_file("tests/testthat/test_ndlm_save_state.R")'
```

## Gate 6. Runtime Smoke Contract

For each NDLM family, a smoke run through `data_prep_shared`, `fit`, and `post` must produce:

- `inputs/shared/covariates/covariate_features.csv`
- `inputs/shared/deterministic_climate/deterministic_climate_summary.txt`
- `post/logs/post_runner.log`
- successful `post` stage completion under the corrected NDLM-only contract

## Gate 7. Reproducibility Artifacts

The matrix directory must contain:

- `matrix_plan.csv`
- `selection_summary.csv`
- `dependency_preservation.csv`
- `spec_parameter_table.csv`
- `campaign_snapshot.yaml`
- `launch_settings.env`

## Current Result

All seven gates passed in the strengthened validator run:

- [prelaunch_validation_summary.json](/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_ndlm_featurecov_rerun_20260420/control/prelaunch_validation_20260421T045415Z/prelaunch_validation_summary.json)

Those gate results were then validated by the completed live rerun:

- [matrix_status.csv](/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_ndlm_featurecov_rerun_20260420/control/ndlm_featurecov_v1/matrix_status.csv)
- [queue.log](/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_ndlm_featurecov_rerun_20260420/control/ndlm_featurecov_v1/queue.log)

Final live confirmation:

- `15 / 15` target rows passed
- `0` failed
- queue controller exited cleanly with `exit_code=0`
