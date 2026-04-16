# Multimodel v8 Featurecov CF1 Epsilon Sweep (2026-04-16)

## Purpose

Relaunch the forecast-window covariance-sensitive families across all `5` cutoffs under the current blended-forecast + engineered-covariate featurecov pipeline while fixing:

- `c_factor = 1.0`
- `epsilon in {1, 30, 60, 90, 180, 360}`

This campaign is build-first and launch-later by design.

## Sweep Scope

Swept families only:

- `exdqlm_multivar_keep`
- `exdqlm_multivar_drop`
- `dqlm_multivar_al_keep`
- `dqlm_multivar_al_drop`
- `ndlm_main_keep`
- `ndlm_main_drop`

Preserved from authoritative compare bundles:

- `exdqlm_univar`
- `dqlm_univar_al`
- `ndlm_univar_keep`
- raw forecast ensemble rows

## Campaign Layout

Primary campaign config:

- [multimodel_v8_featurecov_cf1_eps_sweep.template.yaml](/data/muscat_data/jaguir26/project1_ucsc_phd/config/multimodel_v8_featurecov_cf1_eps_sweep.template.yaml)

Builder and wrapper:

- [build_multimodel_v8_featurecov_cf1_eps_matrix_configs.py](/data/muscat_data/jaguir26/project1_ucsc_phd/scripts/build_multimodel_v8_featurecov_cf1_eps_matrix_configs.py)
- [build_multimodel_v8_featurecov_cf1_eps_compare_bundle.py](/data/muscat_data/jaguir26/project1_ucsc_phd/scripts/build_multimodel_v8_featurecov_cf1_eps_compare_bundle.py)
- [run_multimodel_v8_featurecov_cf1_eps_campaign.sh](/data/muscat_data/jaguir26/project1_ucsc_phd/scripts/run_multimodel_v8_featurecov_cf1_eps_campaign.sh)
- [validate_featurecov_cf1_eps_prelaunch.py](/data/muscat_data/jaguir26/project1_ucsc_phd/scripts/validate_featurecov_cf1_eps_prelaunch.py)

Runtime root:

- `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_featurecov_cf1_eps_sweep_20260416`

Generated config directory:

- `config/unified_runs_featurecov_cf1_eps_20260416`

## Transfer-Function Covariates

Run-scoped base covariates passed through the featurecov pipeline:

- `PPT`
- `SOIL`
- `PCA`

Engineered transfer-function covariates:

- `PPT_sq`
- `SOIL_sq`
- `PPT_x_SOIL`
- `PPT_lag1`
- `PPT_lag2`
- `PPT_lag3`
- `SOIL_lag1`
- `SOIL_lag2`
- `SOIL_lag3`

Operationally, this means:

- `PCA` is passed through as-is
- `PPT` and `SOIL` are retained as base covariates
- squares are built only for `PPT` and `SOIL`
- interaction is built only as `PPT_x_SOIL`
- lags are built only for `PPT` and `SOIL`, for orders `1`, `2`, and `3`

## Deterministic-Climate Policy

The sweep keeps the current `featurecov_v1` deterministic-climate setup:

- precipitation source: `GEFS APCP`
- soil source: `GEFS SOILW 0-0.1m`
- reduction: `q85`
- precipitation noisy blend: `sd = 30`, `normal`, floor at `0`
- soil noisy blend: `sd = 0.05`, `abs_normal`
- observed blend weight: `0.5`
- precipitation zero-stay probability: `0.9`

## Scheduling Policy

Each individual swept family gets its own config and its own core:

- one active model family per generated config
- `run.threads.mc_cores = 1`
- `fit.parallel.mode = global_models`
- `fit.parallel.workers = 1`

Queue defaults in the campaign template:

- ordinary concurrency: `12`
- heavy cutoff policy retained for `20221225`

## Resume / Skip Policy

The sweep is resumable in two ways:

1. local resume
- passed runs in the sweep artifact root are skipped automatically by the shared queue controller

2. compatible prior-run reuse
- exact compatible completed runs from the prior all-9 featurecov campaign are detected and marked as synthetic `pass`
- this only applies when the new generated config matches the prior completed run on:
  - active family scope
  - `c_factor`
  - `epsilon`
  - deterministic-climate settings
  - covariate-feature settings
  - input snapshot paths

This avoids wasting compute on scientifically identical already-completed cells.

## Expected Size

- cutoffs: `5`
- epsilons: `6`
- swept families: `6`
- total planned run configs: `180`
- compare bundles: `30`

## Build Only

```bash
bash scripts/run_multimodel_v8_featurecov_cf1_eps_campaign.sh \
  --config config/multimodel_v8_featurecov_cf1_eps_sweep.template.yaml
```

This builds the matrix and does not launch anything.

## Prelaunch Validation

```bash
python3 scripts/validate_featurecov_cf1_eps_prelaunch.py \
  --config config/multimodel_v8_featurecov_cf1_eps_sweep.template.yaml
```

Validation checks:

- deterministic-climate wiring
- transfer-function covariate contract
- `180` generated configs and matrix rows
- one-core-per-run settings
- family-specific `c_factor` / `epsilon` wiring
- synthetic reuse manifest creation when applicable
- targeted Python and R tests
- one `data_prep_shared` smoke run per swept family
- actual engineered feature columns in `covariate_features.csv`

## Launch Later

```bash
bash scripts/run_multimodel_v8_featurecov_cf1_eps_campaign.sh \
  --config config/multimodel_v8_featurecov_cf1_eps_sweep.template.yaml \
  --launch
```

This launch step is intentionally opt-in and should only happen after validation passes and the user confirms.
