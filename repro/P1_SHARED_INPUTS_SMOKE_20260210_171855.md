# P1 Shared Inputs Smoke Report

Date: 2026-02-11  
Config: `config/unified_runs/smoke_p1_shared_inputs.yaml`  
Run ID: `20260210_171855`  
Run root: `repro/runs/20260210_171855`

## Closure Evidence

- Manifest: `repro/runs/20260210_171855/run_manifest.yaml`
- `finished_at_utc`: `2026-02-11T01:18:57Z`
- Stage executed: `data_prep_shared` only

## Shared Input Tree (short)

- `inputs/shared/parameters/parameters.txt`
- `inputs/shared/retros/retros.csv`
- `inputs/shared/forecasts/nws_forecast.csv`
- `inputs/shared/forecasts/glofas_forecast.csv`
- `inputs/shared/covariates/cov_1_ELI.csv`
- `inputs/shared/covariates/cov_2_ONI.csv`

## Manifest Reference Proof

The manifest includes these run-scoped shared-input paths in `inputs[]` and `artifacts[]`:

- `inputs/shared/parameters/parameters.txt`
- `inputs/shared/retros/retros.csv`
- `inputs/shared/forecasts/nws_forecast.csv`
- `inputs/shared/forecasts/glofas_forecast.csv`
- `inputs/shared/covariates/cov_1_ELI.csv`
- `inputs/shared/covariates/cov_2_ONI.csv`
