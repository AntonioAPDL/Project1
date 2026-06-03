# HE2 exdqlm_multivar_drop Shared Relaunch Plan

Date: 2026-05-16

## Decision

- family: `exdqlm_multivar_drop`
- launch posture: `PREPARE_ONLY`
- shared forecast-covariance spec: `epsilon=30.0`, `c_factor=1.0`
- shared discount set: `set10_manual_20260516`
- selection basis: `manual_override_20260516`
- shared q50 stabilization layer: promoted from the successful 2026-06-02 20211112 repair path

## Why this shared spec

- selected shared relaunch spec is a manual override recorded on `2026-05-16`; it is not required to equal the historical cf1 or discount-grid winner
- historical cf1 family-wide best reference remains `eps30cf1` with mean CRPS `0.986870` across 5 cutoffs
- historical exact-input discount-grid best-by-mean reference remains `set08`
- this twin package intentionally mirrors the approved shared exdqlm relaunch contract so the drop family uses the same corrected bundles, prior scale, discount block, and q50 stabilization posture as the keep family

## Shared science spec

| Parameter | Value | Evidence |
|---|---|---|
| `epsilon` | `30.0` | manual shared override (`2026-05-16`) |
| `c_factor` | `1.0` | manual shared override (`2026-05-16`) |
| `df_t` | `0.99999999` | manual shared override (`2026-05-16`) |
| `df_s1` | `0.99999` | manual shared override (`2026-05-16`) |
| `df_s2` | `0.99999` | manual shared override (`2026-05-16`) |
| `df_s67` | `0.99999` | manual shared override (`2026-05-16`) |
| `df_discrep` | `0.99999` | manual shared override (`2026-05-16`) |
| `lambda` | `0.97` | manual shared override (`2026-05-16`) |
| `df_trans` | `0.9999999` | manual shared override (`2026-05-16`) |
| `df_covs` | `0.9999999` | manual shared override (`2026-05-16`) |

## Shared execution stabilization layer

- `freeze_target`: `states`
- `terminal_sampling_guard.mode`: `fail_fast`
- `terminal_sampling_guard.min_guard_count`: `1`
- `terminal_sampling_guard.max_guard_lag_iters`: `0`
- `terminal_sampling_guard.require_frozen`: `True`
- `median_state_hold_after_guard_iters`: `10`
- `median_state_blend_alpha`: `1.0`
- `median_cov_blend_alpha`: `1.0`
- `median_max_abs_gamma_step`: `0.075`
- `median_max_abs_log_sigma_step`: `0.15`

## Historical discount-set ranking across all 5 cutoffs

This table is retained as historical reference only. The selected shared relaunch set above is a manual override and does not need to match the historical ranking winner.

| Set | Mean Probe CRPS | Mean Delta vs HE | Median Delta | Wins | df_s1 | df_discrep | lambda | df_covs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `set08` | `0.210545` | `-0.000964` | `0.000752` | `2` | `0.9999` | `0.999` | `0.975` | `0.99999` |
| `set07` | `0.218278` | `0.006769` | `0.004465` | `0` | `0.9999` | `0.999` | `0.98` | `0.99999` |
| `set06` | `0.229896` | `0.018388` | `0.001414` | `2` | `0.9999` | `0.999` | `0.97` | `0.9999` |
| `set05` | `0.244019` | `0.032510` | `0.004121` | `1` | `0.9995` | `0.999` | `0.97` | `0.99995` |
| `set09` | `0.255512` | `0.044003` | `0.007841` | `1` | `0.9998` | `0.998` | `0.97` | `0.9999999` |
| `set01` | `0.266405` | `0.054896` | `0.043602` | `0` | `0.9999` | `0.9999` | `0.97` | `0.99995` |
| `set04` | `0.271598` | `0.060090` | `0.072597` | `0` | `0.9999` | `0.99999` | `0.97` | `0.99999` |
| `set03` | `0.284927` | `0.073419` | `0.071811` | `0` | `0.9995` | `0.9999` | `0.97` | `0.99999` |
| `set02` | `0.317206` | `0.105697` | `0.008775` | `1` | `0.9995` | `0.998` | `0.97` | `0.99999` |

## Shared-input bundle contract

| Cutoff | Retros Window | Bundle Root | PPT | SOIL | PCA(alias=GDPC1) |
|---|---|---|---|---|---|
| `20210123` | `1987-05-29 -> 2021-01-23` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/stable_inputs/site=11160500/cutoff_date=2021-01-23/run_id=20260510_publication_shared_r01` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/supporting_inputs/covariates/cov_03_PPT.csv` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/supporting_inputs/covariates/cov_04_SOIL.csv` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/supporting_inputs/covariates/cov_05_PCA.csv` |
| `20211112` | `1987-05-29 -> 2021-11-12` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/stable_inputs/site=11160500/cutoff_date=2021-11-12/run_id=20260510_publication_shared_r01` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/supporting_inputs/covariates/cov_03_PPT.csv` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/supporting_inputs/covariates/cov_04_SOIL.csv` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/supporting_inputs/covariates/cov_05_PCA.csv` |
| `20211221` | `1987-05-29 -> 2021-12-21` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/stable_inputs/site=11160500/cutoff_date=2021-12-21/run_id=20260510_publication_shared_r01` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/supporting_inputs/covariates/cov_03_PPT.csv` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/supporting_inputs/covariates/cov_04_SOIL.csv` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/supporting_inputs/covariates/cov_05_PCA.csv` |
| `20220511` | `1987-05-29 -> 2022-05-11` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/stable_inputs/site=11160500/cutoff_date=2022-05-11/run_id=20260510_publication_shared_r01` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/supporting_inputs/covariates/cov_03_PPT.csv` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/supporting_inputs/covariates/cov_04_SOIL.csv` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/supporting_inputs/covariates/cov_05_PCA.csv` |
| `20221225` | `1987-05-29 -> 2022-12-25` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/stable_inputs/site=11160500/cutoff_date=2022-12-25/run_id=20260510_publication_shared_r01` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/supporting_inputs/covariates/cov_03_PPT.csv` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/supporting_inputs/covariates/cov_04_SOIL.csv` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/supporting_inputs/covariates/cov_05_PCA.csv` |

## Staged relaunch schedule

| Stage | Goal | Deliverables | Gate |
|---|---|---|---|
| `Stage 0` | Freeze the shared relaunch contract before any queue launch. | shared spec report, no-launch template/batch, validator runbook | builder and focused unit tests pass; bundle contract unchanged |
| `Stage 1` | Run no-launch prelaunch validation on representative q50/q65 smokes under the shared spec. | prelaunch_validation_summary.json and smoke-run evidence logs | 20210123 q50, 20211221 q50, and 20221225 q50/q65 all clear the validator contract |
| `Stage 2` | Run a staged relaunch: first canary rows, then all five cutoffs. | five row manifests, fit/post/validate/report status, CRPS compare bundle refresh | all five rows pass report and compare status under the shared spec |
| `Stage 3` | Refresh the revised article figures/tables from the new relaunch outputs. | five-cutoff validation bundle, representative selected-model bundle, cutoff setup/support, forecast-context and synthesis families | article review manifests refreshed and committed in the revised-doc repo |

## Article refresh schedule

| Asset family | Role | Refresh timing |
|---|---|---|
| `five_cutoff_crps_validation_sources` | Table 1 CRPS source freeze | `Stage 2` |
| `representative_selected_model_2022_12_25` | Section 5 representative outputs and posterior tables | `Stage 2` |
| `five_cutoff_setup_support` | input/setup/support bundle by cutoff | `Stage 3` |
| `forecast_context_by_cutoff` | forecast window context figures for all cutoffs | `Stage 3` |
| `multivariate_synthesis_by_cutoff` | main-model synthesis family for all cutoffs | `Stage 3` |
| `reference_synthesis_by_cutoff` | reference synthesis family for all cutoffs | `Stage 3` |
| `historical_support_from_current_models` | historical support figures; refresh only if corrected retained-artifact contract is satisfied | `Stage 3 (gated)` |

## No-launch output paths

- template: `/data/muscat_data/jaguir26/project1_ucsc_phd/config/he2_bayesian_publication_relaunch_exdqlm_multivar_drop_all_cutoffs_sharedspec_20260516.template.yaml`
- batch: `/data/muscat_data/jaguir26/project1_ucsc_phd/config/he2_relaunch_batches/exdqlm_multivar_drop_all_cutoffs_sharedspec_20260516.yaml`
- runbook: `/data/muscat_data/jaguir26/project1_ucsc_phd/repro/run/HE2_EXDQLM_MULTIVAR_DROP_SHARED_RELAUNCH_PLAN_20260516.md`

