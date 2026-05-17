# HE2 exdqlm_univar Shared Relaunch Plan

Date: 2026-05-16

## Decision

- family: `exdqlm_univar`
- launch posture: `PREPARE_ONLY`
- shared discount set: `set10_manual_20260516`
- selection basis: `manual_projection_from_multivar_sharedspec_20260516`
- forecast-covariance knobs (`epsilon`, `c_factor`) remain absent by design for univariate EXDQLM
- `df_discrep` remains absent because it is not part of the univariate state block
- q50 gamma/sigma stabilization knobs from the multivariate relaunch are not operative under the published `legacy_bridge` univariate runner

## Shared science contract

| Parameter | Value | Applicability |
|---|---|---|
| `df_t` | `0.99999999` | shared projected state-evolution knob |
| `df_s1` | `0.99999` | shared projected state-evolution knob |
| `df_s2` | `0.99999` | shared projected state-evolution knob |
| `df_s67` | `0.99999` | shared projected state-evolution knob |
| `lambda` | `0.97` | shared projected state-evolution knob |
| `df_trans` | `0.9999999` | shared projected state-evolution knob |
| `df_covs` | `0.9999999` | shared projected state-evolution knob |
| `epsilon` | `not applied` | univariate forecast-cov block remains absent by design |
| `c_factor` | `not applied` | univariate forecast-cov block remains absent by design |
| `df_discrep` | `absent` | not part of `models.exdqlm_univar.state_evolution` |

## q50 gamma/sigma mapping under `legacy_bridge`

| Item | Value | Notes |
|---|---|---|
| `init.*` | `not_operative_under_legacy_bridge` | `run_OptimalModelSLexAL.R` does not read the univariate init env knobs |
| `freeze_target` | `not_operative_under_legacy_bridge` | not read by the published legacy runner |
| `objective_guard.fail_fast` | `not_operative_under_legacy_bridge` | not read by the published legacy runner |
| `terminal_sampling_guard` | `not_supported_by_univar_runner` | no univariate terminal-sampling guard path exists in the legacy runner |
| `median_blend_and_step_caps` | `not_applicable_to_univar_runner` | multivariate-only |
| operative controls | `shared_state_projection_and_validator_smoke_iter_caps_only` | the real no-launch gates are state projection plus validator smoke evidence |

## Current source scope

| Cutoff | Current run id | Current bundle root | Full history today | Current df_s1 | Target df_s1 | Forecast-cov present today |
|---|---|---|---|---:|---:|---|
| `20210123` | `multimodel_20210123_v8_univar_featurecov_he2_v1_exdqlm_univar` | `` | `False` | `0.9999` | `0.99999` | `False` |
| `20211112` | `multimodel_20211112_v8_univar_featurecov_he2_v1_exdqlm_univar` | `` | `False` | `0.9999` | `0.99999` | `False` |
| `20211221` | `multimodel_20211221_v8_univar_featurecov_he2_v1_exdqlm_univar` | `` | `True` | `0.9999` | `0.99999` | `False` |
| `20220511` | `multimodel_20220511_v8_univar_featurecov_he2_v1_exdqlm_univar` | `` | `True` | `0.9999` | `0.99999` | `False` |
| `20221225` | `multimodel_20221225_v8_univar_featurecov_he2_v1_exdqlm_univar` | `` | `False` | `0.9999` | `0.99999` | `False` |

## Canonical shared-input contract

| Cutoff | Retros window | Bundle root | PPT | SOIL | PCA(alias=GDPC1) |
|---|---|---|---|---|---|
| `20210123` | `1987-05-29 -> 2021-01-23` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/stable_inputs/site=11160500/cutoff_date=2021-01-23/run_id=20260510_publication_shared_r01` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/supporting_inputs/covariates/cov_03_PPT.csv` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/supporting_inputs/covariates/cov_04_SOIL.csv` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/supporting_inputs/covariates/cov_05_PCA.csv` |
| `20211112` | `1987-05-29 -> 2021-11-12` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/stable_inputs/site=11160500/cutoff_date=2021-11-12/run_id=20260510_publication_shared_r01` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/supporting_inputs/covariates/cov_03_PPT.csv` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/supporting_inputs/covariates/cov_04_SOIL.csv` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/supporting_inputs/covariates/cov_05_PCA.csv` |
| `20211221` | `1987-05-29 -> 2021-12-21` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/stable_inputs/site=11160500/cutoff_date=2021-12-21/run_id=20260510_publication_shared_r01` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/supporting_inputs/covariates/cov_03_PPT.csv` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/supporting_inputs/covariates/cov_04_SOIL.csv` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/supporting_inputs/covariates/cov_05_PCA.csv` |
| `20220511` | `1987-05-29 -> 2022-05-11` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/stable_inputs/site=11160500/cutoff_date=2022-05-11/run_id=20260510_publication_shared_r01` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/supporting_inputs/covariates/cov_03_PPT.csv` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/supporting_inputs/covariates/cov_04_SOIL.csv` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/supporting_inputs/covariates/cov_05_PCA.csv` |
| `20221225` | `1987-05-29 -> 2022-12-25` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/stable_inputs/site=11160500/cutoff_date=2022-12-25/run_id=20260510_publication_shared_r01` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/supporting_inputs/covariates/cov_03_PPT.csv` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/supporting_inputs/covariates/cov_04_SOIL.csv` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/supporting_inputs/covariates/cov_05_PCA.csv` |

## No-launch validation schedule

| Stage | Goal | Deliverables | Gate |
|---|---|---|---|
| `Stage 0` | Freeze the no-launch univariate shared-spec package under the approved publication relaunch workflow. | template, batch, runbook, report bundle, source-config freeze | package files exist and focused unit tests pass |
| `Stage 1` | Run builder dry-run and inspect the generated univariate configs for exact bundle/spec projection. | generated configs, matrix plan, config inspection notes | 5 exdqlm_univar rows generated with canonical 20260510 shared bundles and shared state projection |
| `Stage 2` | Run the no-launch validator on the final exact batch with targeted q50 fit and full-pipeline smokes. | prelaunch_validation_summary.json, smoke logs, validation status report | 20210123 q50 fit smoke passes and representative 20210123 q35/q50/q65 full-pipeline smoke clears post/validate/report without queue launch |
| `Stage 3` | Review launch readiness for later parallel execution alongside the live multivariate keep/drop campaigns. | explicit ready/not-ready conclusion and future launch schedule | all no-launch validation gates are green |

## Future workflow refresh points

| Artifact family | Role | Refresh timing |
|---|---|---|
| `five_cutoff_crps_validation_sources` | refresh the exdqlm_univar row lineage in the five-cutoff CRPS validation source freeze | `Stage 3 (after real relaunch completes)` |
| `he2_publication_compare_bundle_refresh` | refresh compare bundles so the exdqlm_univar rows move from legacy lineage to the corrected shared-spec lineage | `Stage 3 (after real relaunch completes)` |
| `article_crps_table_provenance` | document the updated exdqlm_univar provenance if revised-article tables or supplements surface those rows | `Stage 3 (only if article outputs consume the refreshed univariate rows)` |

## No-launch output paths

- template: `/data/muscat_data/jaguir26/project1_ucsc_phd/config/he2_bayesian_publication_relaunch_exdqlm_univar_all_cutoffs_sharedspec_20260516.template.yaml`
- batch: `/data/muscat_data/jaguir26/project1_ucsc_phd/config/he2_relaunch_batches/exdqlm_univar_all_cutoffs_sharedspec_20260516.yaml`
- runbook: `/data/muscat_data/jaguir26/project1_ucsc_phd/repro/run/HE2_EXDQLM_UNIVAR_SHARED_RELAUNCH_PLAN_20260516.md`
- validator outdir: `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_univar_all_cutoffs_sharedspec_20260516/control/prelaunch_validation_exact_final_batch_20260516`

