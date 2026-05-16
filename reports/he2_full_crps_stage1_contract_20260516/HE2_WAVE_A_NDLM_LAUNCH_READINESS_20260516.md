# HE2 Wave A NDLM Launch Readiness

Date: 2026-05-16

## Decision

- status: `GO`
- approved launcher: manifest-driven publication relaunch builder + validator only
- scope: 15 NDLM rows across 5 cutoffs

## Approved launcher

- `selection_source`: `reports/he2_publication_manifest/he2_bayesian_publication_manifest.csv`
- `builder`: `scripts/build_he2_bayesian_publication_relaunch_configs.py`
- `validator`: `scripts/validate_he2_bayesian_publication_relaunch_prelaunch.py`
- `template`: `config/he2_bayesian_publication_relaunch_20260510.template.yaml`

Quarantined builders:

- `scripts/build_multimodel_v8_featurecov_cf1_eps_matrix_configs.py`
- `scripts/build_multimodel_v8_all9_feature_matrix_configs.py`
- `scripts/build_multimodel_v8_ndlm_featurecov_rerun_matrix_configs.py`

## Wave A scope

- rows: `15`
- families: `ndlm_main_drop, ndlm_main_keep, ndlm_univar_keep`
- cutoffs: `20210123, 20211112, 20211221, 20220511, 20221225`

## Input-bundle contract

| Cutoff | Bundle Root | Retros | USGS | Deterministic Futures | GDPC Alias |
|---|---|---|---|---|---|
| `20210123` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/stable_inputs/site=11160500/cutoff_date=2021-01-23/run_id=20260510_publication_shared_r01` | `1987-05-29 -> 2021-01-23` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/data_recovery/site=11160500/recovery_run=site11160500_recovery_20260406T185022Z/family=usgs_daily_flow/full_runs/source_native_tranche1_20260406T194500Z/outputs/usgs_daily_flow_11160500.csv` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/data_recovery/site=11160500/recovery_run=site11160500_recovery_20260406T185022Z/family=gefs_forecasts/full_runs/source_native_tranche1_20260406T194500Z/gefs_nwm_forecast_manifest_source_native_tranche1_20260406T194500Z/handoff_forecasts/site=11160500/run_id=gefs_nwm_forecast_manifest_source_native_tranche1_20260406T194500Z` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/supporting_inputs/covariates/cov_05_PCA.csv` |
| `20211112` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/stable_inputs/site=11160500/cutoff_date=2021-11-12/run_id=20260510_publication_shared_r01` | `1987-05-29 -> 2021-11-12` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/data_recovery/site=11160500/recovery_run=site11160500_recovery_20260406T185022Z/family=usgs_daily_flow/full_runs/source_native_tranche1_20260406T194500Z/outputs/usgs_daily_flow_11160500.csv` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/data_recovery/site=11160500/recovery_run=site11160500_recovery_20260406T185022Z/family=gefs_forecasts/full_runs/source_native_tranche1_20260406T194500Z/gefs_nwm_forecast_manifest_source_native_tranche1_20260406T194500Z/handoff_forecasts/site=11160500/run_id=gefs_nwm_forecast_manifest_source_native_tranche1_20260406T194500Z` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/supporting_inputs/covariates/cov_05_PCA.csv` |
| `20211221` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/stable_inputs/site=11160500/cutoff_date=2021-12-21/run_id=20260510_publication_shared_r01` | `1987-05-29 -> 2021-12-21` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/data_recovery/site=11160500/recovery_run=site11160500_recovery_20260406T185022Z/family=usgs_daily_flow/full_runs/source_native_tranche1_20260406T194500Z/outputs/usgs_daily_flow_11160500.csv` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/data_recovery/site=11160500/recovery_run=site11160500_recovery_20260406T185022Z/family=gefs_forecasts/full_runs/source_native_tranche1_20260406T194500Z/gefs_nwm_forecast_manifest_source_native_tranche1_20260406T194500Z/handoff_forecasts/site=11160500/run_id=gefs_nwm_forecast_manifest_source_native_tranche1_20260406T194500Z` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/supporting_inputs/covariates/cov_05_PCA.csv` |
| `20220511` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/stable_inputs/site=11160500/cutoff_date=2022-05-11/run_id=20260510_publication_shared_r01` | `1987-05-29 -> 2022-05-11` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/data_recovery/site=11160500/recovery_run=site11160500_recovery_20260406T185022Z/family=usgs_daily_flow/full_runs/source_native_tranche1_20260406T194500Z/outputs/usgs_daily_flow_11160500.csv` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/data_recovery/site=11160500/recovery_run=site11160500_recovery_20260406T185022Z/family=gefs_forecasts/full_runs/source_native_tranche1_20260406T194500Z/gefs_nwm_forecast_manifest_source_native_tranche1_20260406T194500Z/handoff_forecasts/site=11160500/run_id=gefs_nwm_forecast_manifest_source_native_tranche1_20260406T194500Z` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/supporting_inputs/covariates/cov_05_PCA.csv` |
| `20221225` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/stable_inputs/site=11160500/cutoff_date=2022-12-25/run_id=20260510_publication_shared_r01` | `1987-05-29 -> 2022-12-25` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/data_recovery/site=11160500/recovery_run=site11160500_recovery_20260406T185022Z/family=usgs_daily_flow/full_runs/source_native_tranche1_20260406T194500Z/outputs/usgs_daily_flow_11160500.csv` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/data_recovery/site=11160500/recovery_run=site11160500_recovery_20260406T185022Z/family=gefs_forecasts/full_runs/source_native_tranche1_20260406T194500Z/gefs_nwm_forecast_manifest_source_native_tranche1_20260406T194500Z/handoff_forecasts/site=11160500/run_id=gefs_nwm_forecast_manifest_source_native_tranche1_20260406T194500Z` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/supporting_inputs/covariates/cov_05_PCA.csv` |

## Validation result

- bundle build: `passed`
- within-cutoff bundle alignment: `passed`
- smoke runs: `10` passed, `4` skipped, `14` total
- quantile smoke scopes skipped only because Wave A intentionally selects NDLM rows

## Launch gate

- full-history retros: `1987-05-29 -> cutoff` verified
- within-cutoff shared bundles: verified
- canonical covariate contract: `PPT`, `SOIL`, `PCA(alias=GDPC1)` verified
- deterministic blended futures: verified
- Wave A NDLM fit + pipeline smokes: passed

Wave A is ready for real launch on the approved path.
