# HE2 exdqlm_multivar_keep All-Cutoff Rerun Contract

Date: 2026-05-16

## Decision

- status: `VALIDATE_ONLY`
- family: `exdqlm_multivar_keep`
- scope: all 5 HE2 cutoffs
- launcher: manifest-driven relaunch builder + prelaunch validator only
- launch posture: do not start the queue until this rerun package is explicitly reapproved

## Approved launcher

- `selection_source`: `reports/he2_publication_manifest/he2_bayesian_publication_manifest.csv`
- `builder`: `scripts/build_he2_bayesian_publication_relaunch_configs.py`
- `validator`: `scripts/validate_he2_bayesian_publication_relaunch_prelaunch.py`
- `template`: `config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_all_cutoffs_rerun_20260516.template.yaml`
- `batch`: `config/he2_relaunch_batches/exdqlm_multivar_keep_all_cutoffs_rerun_20260516.yaml`

Quarantined builders:

- `scripts/build_multimodel_v8_featurecov_cf1_eps_matrix_configs.py`
- `scripts/build_multimodel_v8_all9_feature_matrix_configs.py`
- `scripts/build_multimodel_v8_ndlm_featurecov_rerun_matrix_configs.py`

## Publication-winning rerun spec freeze

| Cutoff | Winning Run | Campaign | CRPS | epsilon | c_factor | Discount Set | df_s1 | df_s2 | df_s67 | df_discrep | df_covs | lambda | Note |
|---|---|---|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|---|
| `20210123` | `multimodel_20210123_v8_eps360cf1_exdqlm_multivar_keep_featurecov_cf1` | `featurecov_cf1_eps_sweep_20260416` | `0.1569` | `360.0` | `1.0` | `-` | `0.9999` | `0.9999` | `0.9999` | `0.999` | `0.99999` | `0.97` | debug_v8_matrix epsilon label/value differ from effective exdqlm fit epsilon; trust fit.exdqlm_multivar.legacy.forecast_cov.epsilon |
| `20211112` | `multimodel_20211112_v8_eps180cf1_exdqlm_multivar_keep_featurecov_cf1` | `featurecov_cf1_eps_sweep_20260416` | `0.0284` | `180.0` | `1.0` | `-` | `0.9999` | `0.9999` | `0.9999` | `0.999` | `0.99999` | `0.97` | - |
| `20211221` | `multimodel_20211221_v8_eps1cf1_exdqlm_multivar_keep_featurecov_cf1` | `featurecov_cf1_eps_sweep_20260416` | `0.2369` | `1.0` | `1.0` | `-` | `0.9999` | `0.9999` | `0.9999` | `0.999` | `0.99999` | `0.97` | debug_v8_matrix epsilon label/value differ from effective exdqlm fit epsilon; trust fit.exdqlm_multivar.legacy.forecast_cov.epsilon |
| `20220511` | `multimodel_20220511_v8_eps180cf1_exdqlm_multivar_keep_featurecov_cf1` | `featurecov_cf1_eps_sweep_20260416` | `0.0210` | `180.0` | `1.0` | `-` | `0.9999` | `0.9999` | `0.9999` | `0.999` | `0.99999` | `0.97` | - |
| `20221225` | `multimodel_20221225_v8_exalm_t1_discount_grid_exact_v1_set09_exdqlm_multivar_keep` | `exalm_t1_discount_grid_exact_20260424:set09_override` | `0.4375` | `360.0` | `1.0` | `set09` | `0.9998` | `0.9998` | `0.9999` | `0.998` | `0.9999999` | `0.97` | debug_v8_matrix epsilon label/value differ from effective exdqlm fit epsilon; trust fit.exdqlm_multivar.legacy.forecast_cov.epsilon |

## 20221225 nuance

- the winning publication row is the exact-input discount-grid override run
- effective exdqlm fit epsilon remains `360.0`
- `debug_v8_matrix.epsilon_label=eps90cf1` is descriptive/debug provenance only and must not override the effective fit spec
- the rerun contract therefore freezes `epsilon=360.0`, `c_factor=1.0`, and discount-set `set09` state evolution values explicitly

## Canonical input-bundle contract

| Cutoff | Retros Window | Bundle Root | USGS | NWS Forecast | GloFAS Forecast | PPT | SOIL | PCA(alias=GDPC1) |
|---|---|---|---|---|---|---|---|---|
| `20210123` | `1987-05-29 -> 2021-01-23` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/stable_inputs/site=11160500/cutoff_date=2021-01-23/run_id=20260510_publication_shared_r01` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/data_recovery/site=11160500/recovery_run=site11160500_recovery_20260406T185022Z/family=usgs_daily_flow/full_runs/source_native_tranche1_20260406T194500Z/outputs/usgs_daily_flow_11160500.csv` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/stable_inputs/site=11160500/cutoff_date=2021-01-23/run_id=20260510_publication_shared_r01/nws_forecast.csv` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/stable_inputs/site=11160500/cutoff_date=2021-01-23/run_id=20260510_publication_shared_r01/glofas_forecast.csv` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/supporting_inputs/covariates/cov_03_PPT.csv` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/supporting_inputs/covariates/cov_04_SOIL.csv` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/supporting_inputs/covariates/cov_05_PCA.csv` |
| `20211112` | `1987-05-29 -> 2021-11-12` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/stable_inputs/site=11160500/cutoff_date=2021-11-12/run_id=20260510_publication_shared_r01` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/data_recovery/site=11160500/recovery_run=site11160500_recovery_20260406T185022Z/family=usgs_daily_flow/full_runs/source_native_tranche1_20260406T194500Z/outputs/usgs_daily_flow_11160500.csv` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/stable_inputs/site=11160500/cutoff_date=2021-11-12/run_id=20260510_publication_shared_r01/nws_forecast.csv` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/stable_inputs/site=11160500/cutoff_date=2021-11-12/run_id=20260510_publication_shared_r01/glofas_forecast.csv` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/supporting_inputs/covariates/cov_03_PPT.csv` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/supporting_inputs/covariates/cov_04_SOIL.csv` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/supporting_inputs/covariates/cov_05_PCA.csv` |
| `20211221` | `1987-05-29 -> 2021-12-21` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/stable_inputs/site=11160500/cutoff_date=2021-12-21/run_id=20260510_publication_shared_r01` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/data_recovery/site=11160500/recovery_run=site11160500_recovery_20260406T185022Z/family=usgs_daily_flow/full_runs/source_native_tranche1_20260406T194500Z/outputs/usgs_daily_flow_11160500.csv` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/stable_inputs/site=11160500/cutoff_date=2021-12-21/run_id=20260510_publication_shared_r01/nws_forecast.csv` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/stable_inputs/site=11160500/cutoff_date=2021-12-21/run_id=20260510_publication_shared_r01/glofas_forecast.csv` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/supporting_inputs/covariates/cov_03_PPT.csv` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/supporting_inputs/covariates/cov_04_SOIL.csv` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/supporting_inputs/covariates/cov_05_PCA.csv` |
| `20220511` | `1987-05-29 -> 2022-05-11` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/stable_inputs/site=11160500/cutoff_date=2022-05-11/run_id=20260510_publication_shared_r01` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/data_recovery/site=11160500/recovery_run=site11160500_recovery_20260406T185022Z/family=usgs_daily_flow/full_runs/source_native_tranche1_20260406T194500Z/outputs/usgs_daily_flow_11160500.csv` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/stable_inputs/site=11160500/cutoff_date=2022-05-11/run_id=20260510_publication_shared_r01/nws_forecast.csv` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/stable_inputs/site=11160500/cutoff_date=2022-05-11/run_id=20260510_publication_shared_r01/glofas_forecast.csv` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/supporting_inputs/covariates/cov_03_PPT.csv` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/supporting_inputs/covariates/cov_04_SOIL.csv` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/supporting_inputs/covariates/cov_05_PCA.csv` |
| `20221225` | `1987-05-29 -> 2022-12-25` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/stable_inputs/site=11160500/cutoff_date=2022-12-25/run_id=20260510_publication_shared_r01` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/data_recovery/site=11160500/recovery_run=site11160500_recovery_20260406T185022Z/family=usgs_daily_flow/full_runs/source_native_tranche1_20260406T194500Z/outputs/usgs_daily_flow_11160500.csv` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/stable_inputs/site=11160500/cutoff_date=2022-12-25/run_id=20260510_publication_shared_r01/nws_forecast.csv` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/stable_inputs/site=11160500/cutoff_date=2022-12-25/run_id=20260510_publication_shared_r01/glofas_forecast.csv` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/supporting_inputs/covariates/cov_03_PPT.csv` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/supporting_inputs/covariates/cov_04_SOIL.csv` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/supporting_inputs/covariates/cov_05_PCA.csv` |

This rerun contract is intentionally tied to the corrected shared bundle lineage:
- bundle artifact root: `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510`
- bundle run id: `20260510_publication_shared_r01`
- data start: `1987-05-29`

## Outputs

- template: `/data/muscat_data/jaguir26/project1_ucsc_phd/config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_all_cutoffs_rerun_20260516.template.yaml`
- batch: `/data/muscat_data/jaguir26/project1_ucsc_phd/config/he2_relaunch_batches/exdqlm_multivar_keep_all_cutoffs_rerun_20260516.yaml`
- runbook: `/data/muscat_data/jaguir26/project1_ucsc_phd/repro/run/HE2_EXDQLM_MULTIVAR_KEEP_ALL_CUTOFFS_RERUN_RUNBOOK_20260516.md`
- spec freeze CSV/JSON and frozen source configs are written beside this note

