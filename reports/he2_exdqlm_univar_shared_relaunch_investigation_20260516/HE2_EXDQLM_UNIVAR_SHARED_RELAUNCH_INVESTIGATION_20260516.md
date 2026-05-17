# HE2 exdqlm_univar Shared Relaunch Investigation

Date: 2026-05-16

## Decision boundary

- posture: `INVESTIGATION_ONLY`
- launch status: `DO NOT LAUNCH`
- target family: `exdqlm_univar` (`exAL-U-T1`)
- reference multivariate contracts: live `exdqlm_multivar_keep` and live `exdqlm_multivar_drop` shared-spec relaunches

## Phase A: current multivariate reference contract

| Contract Area | Approved Value | Evidence |
|---|---|---|
| builder | `scripts/build_he2_bayesian_publication_relaunch_configs.py` | current approved publication relaunch path |
| validator | `scripts/validate_he2_bayesian_publication_relaunch_prelaunch.py` | current approved publication relaunch path |
| launcher | `scripts/launch_he2_bayesian_publication_relaunch.py` | current approved publication relaunch path |
| queue/controller | `scripts/run_multimodel_v8_queue.py` | current root-scoped queue path |
| shared bundle root | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510` | current keep/drop sharedspec templates and live runs |
| shared bundle run id | `20260510_publication_shared_r01` | current keep/drop sharedspec templates and live runs |
| data_start | `1987-05-29` | current approved builder contract |
| covariates | `PPT, SOIL, PCA` | manifest + canonical shared bundle paths |
| climate factor alias | `PCA(alias=GDPC1)` | deterministic climate / PCA passthrough contract |
| fit_parallel_workers | `7` | sharedspec batch resource block |
| mc_cores | `7` | sharedspec batch resource block |
| queue ordinary_max_concurrent | `1` | sharedspec templates |

### Shared multivariate science spec

| Item | Value |
|---|---|
| `epsilon` | `30.0` |
| `c_factor` | `1.0` |
| `df_t` | `0.99999999` |
| `df_s1` | `0.99999` |
| `df_s2` | `0.99999` |
| `df_s67` | `0.99999` |
| `df_discrep` | `0.99999` |
| `lambda` | `0.97` |
| `df_trans` | `0.9999999` |
| `df_covs` | `0.9999999` |
| `q50.freeze_target` | `states` |
| `q50.terminal_sampling_guard.mode` | `fail_fast` |
| `q50.median_state_blend_alpha` | `0.5` |
| `q50.median_cov_blend_alpha` | `0.5` |

## Phase B: exact univariate target scope

| Cutoff | Label | Family | Current Run ID | Current Campaign | Implementation | Likelihood | Full History Today | Risk Summary |
|---|---|---|---|---|---|---|---|---|
| `20210123` | `exAL-U-T1` | `exdqlm_univar` | `multimodel_20210123_v8_univar_featurecov_he2_v1_exdqlm_univar` | `univar_featurecov_he2_rerun_20260422` | `legacy_bridge` | `exal` | `False` | historical support starts at 2018-02-08; forecast_cov prior block absent in current univariate source config; legacy univar launcher still points at all9 feature builder unless quarantined |
| `20211112` | `exAL-U-T1` | `exdqlm_univar` | `multimodel_20211112_v8_univar_featurecov_he2_v1_exdqlm_univar` | `univar_featurecov_he2_rerun_20260422` | `legacy_bridge` | `exal` | `False` | historical support starts at 2018-11-28; forecast_cov prior block absent in current univariate source config; legacy univar launcher still points at all9 feature builder unless quarantined |
| `20211221` | `exAL-U-T1` | `exdqlm_univar` | `multimodel_20211221_v8_univar_featurecov_he2_v1_exdqlm_univar` | `univar_featurecov_he2_rerun_20260422` | `legacy_bridge` | `exal` | `True` | forecast_cov prior block absent in current univariate source config; legacy univar launcher still points at all9 feature builder unless quarantined |
| `20220511` | `exAL-U-T1` | `exdqlm_univar` | `multimodel_20220511_v8_univar_featurecov_he2_v1_exdqlm_univar` | `univar_featurecov_he2_rerun_20260422` | `legacy_bridge` | `exal` | `True` | forecast_cov prior block absent in current univariate source config; legacy univar launcher still points at all9 feature builder unless quarantined |
| `20221225` | `exAL-U-T1` | `exdqlm_univar` | `multimodel_20221225_v8_univar_featurecov_he2_v1_exdqlm_univar` | `univar_featurecov_he2_rerun_20260422` | `legacy_bridge` | `exal` | `False` | historical support starts at 2020-01-10; forecast_cov prior block absent in current univariate source config; legacy univar launcher still points at all9 feature builder unless quarantined |

Scope conclusion: the correct target is exactly `exdqlm_univar`, one row per HE2 cutoff, manuscript label `exAL-U-T1`.

## Phase C: bundle parity audit

| Cutoff | Full History Today | Current Effective Start | Retros Matches Target | NWS Matches Target | GloFAS Matches Target | PPT Matches Target | SOIL Matches Target | PCA Matches Target | Parity Status |
|---|---|---|---|---|---|---|---|---|---|
| `20210123` | `False` | `2018-02-08` | `False` | `False` | `False` | `False` | `False` | `False` | `requires_adaptation` |
| `20211112` | `False` | `2018-11-28` | `False` | `False` | `False` | `False` | `False` | `False` | `requires_adaptation` |
| `20211221` | `True` | `1987-05-29` | `False` | `False` | `False` | `False` | `False` | `False` | `requires_adaptation` |
| `20220511` | `True` | `1987-05-29` | `False` | `False` | `False` | `False` | `False` | `False` | `requires_adaptation` |
| `20221225` | `False` | `2020-01-10` | `False` | `False` | `False` | `False` | `False` | `False` | `requires_adaptation` |

Bundle conclusion: the univariate family can and should use the exact same corrected 20260510 shared bundle lineage as multivariate keep/drop, but every current publication-source row still needs an explicit bundle path swap under the approved builder path.

## Phase C: spec parity audit

| Item | Current | Target Sharedspec | Status | Notes |
|---|---|---|---|---|
| `models.exdqlm_univar.state_evolution.df_t` | `0.99999999` | `0.99999999` | `direct_reuse` | same numeric value already present in published univariate rows |
| `models.exdqlm_univar.state_evolution.df_s1` | `0.9999` | `0.99999` | `requires_adaptation` | published univariate winner uses 0.9999; shared multivariate contract uses 0.99999 |
| `models.exdqlm_univar.state_evolution.df_s2` | `0.9999` | `0.99999` | `requires_adaptation` | published univariate winner uses 0.9999; shared multivariate contract uses 0.99999 |
| `models.exdqlm_univar.state_evolution.df_s67` | `0.9999` | `0.99999` | `requires_adaptation` | published univariate winner uses 0.9999; shared multivariate contract uses 0.99999 |
| `models.exdqlm_univar.state_evolution.df_discrep` | `<absent>` | `0.99999` | `not_applicable` | repo validation explicitly asserts univariate EXDQLM should not gain df_discrep and stage_fit does not read it |
| `models.exdqlm_univar.state_evolution.lambda` | `0.97` | `0.97` | `direct_reuse` | same numeric value already present in published univariate rows |
| `models.exdqlm_univar.state_evolution.df_trans` | `0.9999999` | `0.9999999` | `direct_reuse` | same numeric value already present in published univariate rows |
| `models.exdqlm_univar.state_evolution.df_covs` | `0.99999` | `0.9999999` | `requires_adaptation` | published univariate winner uses 0.99999; shared multivariate contract uses 0.9999999 |
| `models.exdqlm_univar.prior.forecast_cov.c_factor` | `` | `1.0` | `requires_code_or_policy_decision` | current univariate source config has no forecast_cov prior block and the fit-stage path does not consume c_factor for exdqlm_univar |
| `models.exdqlm_univar.prior.forecast_cov.epsilon` | `` | `30.0` | `requires_code_or_policy_decision` | current univariate source config has no forecast_cov prior block and the fit-stage path does not consume epsilon for exdqlm_univar |
| `fit.exdqlm_univar.gamma_sigma.freeze_target` | `gamma_sigma` | `states` | `partial_equivalent` | univariate runner supports freeze_target and can map states/gamma_sigma directly |
| `fit.exdqlm_univar.gamma_sigma.objective_guard.fail_fast` | `false` | `true` | `partial_equivalent` | univariate runner supports objective_guard.fail_fast but does not expose multivariate terminal_sampling_guard |
| `fit.exdqlm_univar.gamma_sigma.stabilization.median_state_blend_alpha` | `<unsupported>` | `0.5` | `not_applicable` | no equivalent knob exists in run_exdqlm_univar.R or exdqlm_univar gamma-sigma resolver |
| `fit.exdqlm_univar.gamma_sigma.stabilization.median_cov_blend_alpha` | `<unsupported>` | `0.5` | `not_applicable` | no equivalent knob exists in run_exdqlm_univar.R or exdqlm_univar gamma-sigma resolver |
| `fit.exdqlm_univar.gamma_sigma.stabilization.median_max_abs_gamma_step` | `<unsupported>` | `0.15` | `not_applicable` | no equivalent step-cap knob exists for univariate EXDQLM today |
| `fit.exdqlm_univar.gamma_sigma.stabilization.median_max_abs_log_sigma_step` | `<unsupported>` | `0.25` | `not_applicable` | no equivalent step-cap knob exists for univariate EXDQLM today |

Spec conclusion:

- `df_t`, `lambda`, and `df_trans` already match the multivariate sharedspec numerically.
- `df_s1`, `df_s2`, `df_s67`, and `df_covs` require explicit univariate value overrides if we want numeric parity with the multivariate sharedspec.
- `df_discrep` is not applicable to `exdqlm_univar` in the current code path and should not be forced into the univariate state block.
- `epsilon` and `c_factor` do not currently have an operative univariate home: the published univariate source config does not define `models.exdqlm_univar.prior.forecast_cov`, and the fit-stage path does not consume those knobs for `exdqlm_univar`.

## Phase C: directly reusable vs adaptation mapping

| Component | Status | Reuse Strategy | Notes |
|---|---|---|---|
| `approved_builder` | `direct_reuse` | reuse exactly | builder already supports family selection and quantile_univariate model class |
| `approved_validator` | `direct_reuse` | reuse exactly | validator already supports univar fit/full-pipeline smokes through quantile_univariate selection |
| `queue_controller` | `direct_reuse` | reuse exactly | root-scoped active-process fix already allows parallel family controllers under separate artifact roots |
| `bundle_contract` | `direct_reuse` | reuse exactly | same canonical 20260510 shared-input bundle root should be used per cutoff |
| `data_start` | `direct_reuse` | reuse exactly | full retrospective history start is already enforced in the approved builder path |
| `deterministic_climate_contract` | `direct_reuse` | reuse exactly | univariate publication rows already use the same covariate names and deterministic climate support assets |
| `runtime_posture` | `direct_reuse` | reuse exactly | published univariate rerun already used one core per quantile and should keep that posture for parity |
| `artifact_root_naming` | `requires_adaptation` | new univar-specific artifact root with sharedspec naming | needs a dedicated exdqlm_univar sharedspec root so it can queue in parallel without colliding with keep/drop |
| `template_and_batch` | `requires_adaptation` | create univar twin template and batch using approved publication relaunch style | selection/family/model_class must target exdqlm_univar / quantile_univariate |
| `shared_discount_bundle` | `partial_equivalent` | project applicable state-evolution fields into univar state block | df_discrep has no univar state slot and must remain excluded to preserve current univar family contract |
| `shared_epsilon_c_factor` | `requires_code_or_policy_decision` | decide whether to keep as metadata only or extend fit-stage to consume them | current exdqlm_univar fit path does not read forecast_cov prior knobs and the published univariate source config does not currently define that block |
| `q50_stabilization` | `partial_equivalent` | reuse freeze_target/init/objective_guard subset; validate separately | multivariate median-specific stabilization knobs do not exist for univariate EXDQLM today |
| `legacy_univar_launcher` | `requires_adaptation` | quarantine and do not reuse | points to legacy all9-feature builder/validator path rather than the approved publication relaunch workflow |

## Phase D: launcher / builder / template adaptation plan

Recommended new files:

- `config/he2_bayesian_publication_relaunch_exdqlm_univar_all_cutoffs_sharedspec_20260516.template.yaml`
- `config/he2_relaunch_batches/exdqlm_univar_all_cutoffs_sharedspec_20260516.yaml`
- `repro/run/HE2_EXDQLM_UNIVAR_SHARED_RELAUNCH_PLAN_20260516.md`
- `reports/he2_exdqlm_univar_shared_relaunch_plan_20260516/` (future no-launch package outputs)
- `tests/python/test_he2_exdqlm_univar_sharedspec_package.py`

Recommended edits:

- `scripts/build_he2_bayesian_publication_relaunch_configs.py`: likely no family-support changes needed; only use it through a new univariate sharedspec template/batch.
- `scripts/validate_he2_bayesian_publication_relaunch_prelaunch.py`: likely no code changes needed, but the new univariate template should set `cutoff_smoke_family`, `univar_quantile_fit_smoke_family`, and `full_pipeline_univar_quantile_family` explicitly to `exdqlm_univar`.
- `scripts/run_multimodel_v8_queue.py`: no code change expected; reuse current root-scoped behavior under a separate univariate artifact root.

## Phase E: no-launch validation plan

1. Build the univariate sharedspec configs with the approved builder.
2. Inspect generated configs for:
   - canonical 20260510 bundle paths
   - `data_start = 1987-05-29`
   - `fit_parallel_workers = 7`, `mc_cores = 7`, thread caps = 1
   - `models.run_exdqlm_univar = true` and no stray family flags
3. Run the approved prelaunch validator on the final exact batch.
4. Add targeted univariate quantile smokes, at minimum:
   - `20210123 q50`
   - `20211221 q50`
   - `20221225 q50`
   - one full-pipeline univariate smoke row
5. Add a queue/controller dry check proving a third family artifact root can coexist with live keep/drop without cross-root blocking.

## Phase F: staged implementation plan

| Stage | Objective | Files / Scripts | Success Criteria | Launch Boundary |
|---|---|---|---|---|
| `Stage 0` | Freeze the univariate investigation contract. | `build_he2_exdqlm_univar_shared_relaunch_investigation.py`, scope/parity CSVs, this report | scope and parity artifacts rebuild deterministically | `do not launch` |
| `Stage 1` | Create the univariate sharedspec template and batch on the approved publication relaunch path. | new template/batch + `/data/muscat_data/jaguir26/project1_ucsc_phd/repro/run/HE2_EXDQLM_UNIVAR_SHARED_RELAUNCH_PLAN_20260516.md` | builder selects exactly 5 `exdqlm_univar` rows | `do not launch` |
| `Stage 2` | Encode the univariate sharedspec projection. | batch row patch + tests | state-evolution overrides are explicit, `df_discrep` remains absent, epsilon/c_factor decision is documented | `do not launch` |
| `Stage 3` | Run no-launch validation. | `scripts/validate_he2_bayesian_publication_relaunch_prelaunch.py` + focused tests | builder dry-run, bundle audit, univariate q50/full-pipeline smokes all pass | `do not launch` |
| `Stage 4` | Parallel-launch readiness review. | queue compatibility note + validation status report | explicit conclusion that a third family can run beside live keep/drop | `ready for launch after validation` |

## Risks / blockers / open questions

1. `df_discrep` is a multivariate-only part of the shared discount bundle today. Forcing it into univariate would contradict existing repo validation expectations.
2. `epsilon` and `c_factor` are present in the univariate source config but are not read by the current univariate fit-stage path. We need an explicit choice between preserving model identity and extending the code.
3. The multivariate q50 stabilization layer has only a partial univariate equivalent. Univariate needs its own smoke-confirmed q50 policy rather than a blind copy.
4. The legacy univariate launcher is intentionally out of contract for this corrected relaunch and must stay quarantined.

## Readiness conclusion

- readiness status: `INVESTIGATED_ONLY`
- ready_for_no_launch_packaging: `False`
- ready_for_launch_after_validation: `False`

Current conclusion: we are ready to implement the univariate sharedspec package cleanly, but we are **not** ready to claim launch readiness until we codify the univariate-specific spec projection and validate a partial q50 stabilization strategy under the approved no-launch path.

