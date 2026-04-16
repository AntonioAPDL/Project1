# All-9 Feature-Covariate Prelaunch Validation (2026-04-16)

## Purpose

This note records the reproducible prelaunch validation for the corrected all-9 relaunch workflow based on:

- engineered covariates from `PPT`, `SOIL`, and `PCA`
- nonlinear terms `PPT^2`, `SOIL^2`, `PPT * SOIL`
- lag terms `PPT_lag1..3`, `SOIL_lag1..3`
- blended forecast-window `PPT` and `SOIL` built from the configured deterministic-climate blend

This validation is intentionally **prelaunch only**. It does **not** start the full 45-run campaign.

## Command

```bash
python3 scripts/validate_all9_featurecov_prelaunch.py \
  --config config/multimodel_v8_all9_featurecov.template.yaml
```

## What The Validator Checks

1. deterministic-climate config sanity
   - handoff root exists
   - `PPT` source is `GEFS APCP`
   - `SOIL` source is `GEFS SOILW 0-0.1 m`
   - precipitation blend parameters match the active corrected-model spec
   - soil blend parameters match the active corrected-model spec
2. forecast-overlay review artifacts
   - review summary exists
   - plot index exists
   - climate-series status exists
   - all `5 x 2 = 10` review plots are present
3. builder regeneration
   - rebuilds the corrected all-9 config surface
   - verifies `45` generated configs and `45` plan rows
4. generated config integrity
   - each config uses exactly `PPT`, `SOIL`, `PCA` as fit covariates
   - each covariate path exists
   - each config carries the expected `handoff_root`
5. unit tests
   - Python forecast-overlay / handoff / forecast-download tests
   - R deterministic-climate blend and covariate-feature-engineering tests
6. family smoke checks
   - runs `data_prep_shared` once for each of the `9` model families
   - verifies `covariate_features.csv`
   - verifies `deterministic_climate_summary.txt`

## Current Successful Validation

Validation output directory:

- `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_all9_featurecov_20260415/control/prelaunch_validation_20260416T024348Z`

Summary artifacts:

- [prelaunch_validation_summary.md](/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_all9_featurecov_20260415/control/prelaunch_validation_20260416T024348Z/prelaunch_validation_summary.md)
- [prelaunch_validation_summary.json](/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_all9_featurecov_20260415/control/prelaunch_validation_20260416T024348Z/prelaunch_validation_summary.json)

Headline result:

- status: `passed`
- launch state during validation: `not launched by this validation`
- generated configs: `45`
- overlay review plots verified: `10`
- family smoke runs: `9`

## Important Operational Note

A real batch launch was started briefly during earlier debugging and then intentionally stopped so this validation could be run on a stable prelaunch state.

The intended operational sequence is now:

1. keep the corrected all-9 workflow in prelaunch mode
2. rerun the validator if the blend spec or builder changes
3. only after a passing validation, start the full campaign
