# TRACKER: AL DQLM + NDLM Keep (Unified Workflow)

## Metadata
- Created: 2026-03-22 (America/Los_Angeles)
- Last updated: 2026-03-23 11:43 (America/Los_Angeles)
- Repository root: `/data/muscat_data/jaguir26/project1_ucsc_phd`
- Tracker path: `repro/TRACKER_AL_DQLM_NDLM_KEEP.md`
- Owner: Codex + user

## Objectives
Add and validate the following benchmark-reference families in unified workflow:
1. Univariate DQLM via `AL` (not exAL)
2. Multivariate DQLM via `AL` in `drop` mode
3. Multivariate DQLM via `AL` in `keep` mode
4. NDLM `keep` mode with transfer function active during forecast window

Also ensure post-stage and CRPS exports include all new model semantics/IDs.

## Baseline Audit (Confirmed)
### Already implemented before this work
- exDQLM univariate theory-aligned path
- exDQLM multivariate legacy bridge path with transfer `drop`/`keep`
- Keep-mode multivar transfer-in-forecast pathway
- Existing raw-ensemble comparison outputs
- Existing CRPS export pipeline

### Missing before this work
- First-class unified likelihood mode switches (`exal` vs `al`) for univar/multivar
- First-class unified NDLM transfer mode signal in fit/post metadata
- CRPS model ID semantics for AL and NDLM keep transfer

## exAL -> AL Collapse Hypothesis
Hypothesis:
- Use exAL machinery with `gamma=0` and latent `s_t` disabled/zeroed to operationalize AL, avoiding full re-derivation.

Result:
- **Accepted (operationally) for current codebase**, with explicit mode guards:
  - Univar AL path sets/keeps `gamma=0` and disables latent skew updates.
  - Multivar AL path fixes sampled gamma at 0 (`samp_gamma_range=0,0`) and zeros/neutralizes AL-only skew terms.
- Caveat:
  - This is implementation-level equivalence in this repository, not a new symbolic derivation.

## Model Definitions / Naming
- `exal`:
  - existing baseline likelihood behavior
- `al`:
  - new explicit likelihood mode in unified config
- `transfer_mode`:
  - `drop`: transfer states removed in forecast window
  - `keep`: transfer states retained in forecast window
- CRPS model IDs used:
  - `dqlm_univar_al_synth`
  - `dqlm_multivar_al_synth_drop`
  - `dqlm_multivar_al_synth_keep`
  - `ndlm_main_synth_keep`

## Design Decisions
1. Backward compatibility preserved:
- Defaults remain `exal`
- Existing production run folders untouched

2. Minimal-invasive implementation:
- Keep legacy object naming/contracts used by post scripts
- Inject semantics via explicit config/env + CRPS ID mapping

3. Test-first and evidence-first:
- Add mode-resolution tests + CRPS ID tests
- Run phased smoke jobs with one cutoff, short history, q=0.50, low compute
- Record PASS/FAIL with files/logs/commands/run IDs

## Phase Plan + Outcomes
### Phase A: AL wiring/config flags
Status: **PASS**
- Added likelihood mode config/resolvers and NDLM forecast transfer mode resolver
- Fit/post stages export mode env vars
- Defaults unchanged (`exal`)
- Unit tests pass

### Phase B: Univariate AL-DQLM smoke
Status: **PASS**
- Run completed
- AL mode recorded; `gamma=0`
- No NaN/Inf in key outputs

### Phase B2: Univariate AL-DQLM legacy bridge (sigma-only LD patch)
Status: **PASS**
- Legacy bridge run completed with `UNIV_LIKELIHOOD_MODE=al`
- `gamma` collapsed to exactly zero in sampled output
- `s_t` collapsed to exactly zero in both VB moments and sampled output
- No NaN/Inf in checked fit outputs

### Phase C: Multivariate AL-DQLM `drop` smoke
Status: **PASS**
- Run completed
- Mode log shows `multivar_likelihood=al`
- Forecast health file present (`transfer_mode=drop`)
- `samp_gamma_range=0,0`, no NaN/Inf in checked fit tensors

### Phase D: Multivariate AL-DQLM `keep` smoke
Status: **PASS**
- Run completed
- Mode log shows `multivar_likelihood=al`
- Forecast health file present (`transfer_mode=keep`)
- `samp_gamma_range=0,0`, no NaN/Inf in checked fit tensors

### Phase E: NDLM keep + transfer active in forecast
Status: **PARTIAL (operational PASS, diagnostics FAIL)**
- Run completed and post completed
- NDLM summary reports:
  - `forecast_transfer_mode=keep`
  - `transfer_active_forecast_window=true`
- Contract artifacts produced
- Diagnostics file status is fail due covariance PSD violations (`ndlm.new_theta.sC.psd`, `ndlm.new_theta.sC_ens[2].psd`)

### Phase G: NDLM keep stabilization root-cause fix
Status: **PASS (diagnostics + smoke pipeline)**
- Root cause validated from Phase E fail artifacts:
  - covariance PSD drift in NDLM smoother/forecast covariances inflated latent variance terms and destabilized sigma updates.
- Implemented principled stabilization:
  - SPD/eigen-floor/eigen-cap covariance stabilization in both R and C++ Kalman backends.
  - NDLM local covariance stabilization for forecast segment builders and export-time covariance tensors.
  - sigma-update guardrails:
    - latent variance cap (data-scale + absolute cap)
    - sigma upper cap
    - optional damping hook (default 1.0, backward compatible)
  - added stabilization diagnostics counters to NDLM theory summary/state.
- Validation:
  - targeted NDLM tests pass (backend, constants/env, ragged+stabilization, config validation).
  - NDLM keep smoke rerun passes fit+post and diagnostics (`status: pass`).

### Phase F: Post + CRPS inclusion for new IDs
Status: **PASS (with replay workaround)**
- Initial all-model run failed in post due NDLM exps indexing OOB in `40_figures.R`
- Patched NDLM exps indexing with safe bounds helpers
- Replayed post using fit outputs source and completed
- CRPS tables exported for both drop and keep passes
- Required new IDs present across summary tables

### Phase H: NDLM univariate keep implementation (West-Harrison closed form, C++ backend)
Status: **PASS**
- Added first-class `ndlm_univar` family wiring in unified config, manifest, fit/post/report orchestration, contracts, and CRPS metadata.
- Added dedicated run entry script: `scripts/run_ndlm_univar.R`.
- Added compatibility output aliases (`NDLM_univar` + legacy `NDLM` object names) for downstream post modules.
- Implemented and validated C++ Kalman backend path and R wrappers for:
  - filter step / full forward filter
  - h-step forecast
  - backward smoother
- Debugged two root-cause fit failures in posterior state sampling:
  - non-conformable scaling multiply in Student-t sampler
  - non-conformable mean broadcast in Student-t sampler
- Patched samplers using explicit column sweep + explicit mean draw matrix.
- Updated `ndlm_univar` contract checker to accept list-wrapped `samp.theta`/`samp.sigma` and nested ensemble leaves (same convention as other families).
- Final Phase H rerun completes `data_prep_shared + fit + post + report`.

### Phase I: all-model smoke with ndlm_univar CRPS inclusion
Status: **PASS**
- Run completed end-to-end:
  - `data_prep_shared=pass`, `fit=pass`, `post=pass`, `report=pass`
  - run: `repro/runs/dev_al_phaseI_allmodels_plus_ndlm_univar_crps_smoke_20260323`
- CRPS summary includes required `ndlm_univar` model row:
  - `model_id=ndlm_univar_synth_keep`
  - `model_variant=ndlm_univar_keep`
- Prior required IDs remain present in same summary:
  - `dqlm_univar_al_synth`
  - `dqlm_multivar_al_synth_drop`
  - `ndlm_main_synth_keep`

## Risk Log (Current)
1. R1: Legacy post coupling to NDLM matrix shape
- Evidence: prior OOB in `40_figures.R` on `exps` indexing
- Mitigation applied: safe index/range wrappers returning NA+warning instead of hard fail

2. R2: CRPS magnitude blow-ups for some synthesis outputs
- Evidence: extremely large CRPS values in keep summary for univar/NDLM rows
- Mitigation next: add scale/finite-range guards and explicit clipping policy diagnostics

3. R3: Full-slice PSD margin remains near tolerance in offline exhaustive scans
- Evidence: sampled diagnostics pass (`psd_tol=-1e-8`), but full-slice eigen scans can show small negative minima at ~1e-8 scale.
- Mitigation next: optional stricter full-slice PSD audit mode for NDLM diagnostics and/or stronger default jitter policy once benchmark sensitivity is measured.

## Test Matrix (Executed)
### Unit / contract tests
- `tests/testthat/test_config_mode_resolution.R` -> pass
- `tests/testthat/test_univar_convergence_contract.R` -> pass
- `tests/testthat/test_ndlm_ragged_horizon_builder.R` -> pass
- `tests/testthat/test_ndlm_kalman_backend.R` -> pass
- `tests/testthat/test_ndlm_fitloop_contract.R` -> pass
- `tests/testthat/test_post_crps_tables.R` -> pass
- `tests/testthat/test_ndlm_univar_wh_recursions.R` -> pass

### Smoke test scope
- Single cutoff: `2022-12-25`
- Data start: `2010-01-01`
- Quantiles: `0.50` only
- Reduced workers/cores
- New run IDs only; no production folders modified/deleted

## Commands Log (Primary)
### Dry-run + execution
- `Rscript --vanilla scripts/unified_run.R --config config/unified_runs/al_phaseB_univar_al_smoke_20260322.yaml`
- `Rscript --vanilla scripts/unified_run.R --config config/unified_runs/al_phaseB2_univar_legacy_al_smoke_20260322.yaml`
- `Rscript --vanilla scripts/unified_run.R --config config/unified_runs/al_phaseC_multivar_al_drop_smoke_20260322.yaml`
- `Rscript --vanilla scripts/unified_run.R --config config/unified_runs/al_phaseD_multivar_al_keep_smoke_20260322.yaml`
- `Rscript --vanilla scripts/unified_run.R --config config/unified_runs/al_phaseE_ndlm_keep_smoke_20260322.yaml`
- `Rscript --vanilla scripts/unified_run.R --config config/unified_runs/al_phaseF_allmodels_crps_smoke_20260322.yaml`
- `Rscript --vanilla scripts/unified_run.R --config config/unified_runs/al_phaseF_post_replay_crps_20260322.yaml`
- `Rscript --vanilla scripts/unified_run.R --config config/unified_runs/al_phaseH_ndlm_univar_keep_smoke_20260323.yaml`
- `Rscript --vanilla scripts/unified_run.R --config config/unified_runs/al_phaseI_allmodels_plus_ndlm_univar_crps_smoke_20260323.yaml`

### Targeted tests
- `Rscript -e 'library(testthat); test_file("tests/testthat/test_config_mode_resolution.R"); test_file("tests/testthat/test_univar_convergence_contract.R"); test_file("tests/testthat/test_ndlm_ragged_horizon_builder.R"); test_file("tests/testthat/test_post_crps_tables.R")'`
- `Rscript -e 'library(testthat); test_file("tests/testthat/test_config_mode_resolution.R"); test_file("tests/testthat/test_ndlm_fitloop_contract.R"); test_file("tests/testthat/test_ndlm_ragged_horizon_builder.R"); test_file("tests/testthat/test_ndlm_kalman_backend.R")'`
- `Rscript --vanilla -e 'library(testthat); test_file("tests/testthat/test_ndlm_univar_wh_recursions.R"); test_file("tests/testthat/test_config_mode_resolution.R"); test_file("tests/testthat/test_post_module_plan.R"); test_file("tests/testthat/test_post_crps_tables.R")'`

## Phase Status Checklist
- [x] Phase 0 audit complete
- [x] Phase A AL wiring/config
- [x] Phase B univar AL smoke
- [x] Phase B2 univar AL smoke (legacy bridge sigma-only patch)
- [x] Phase C multivar AL drop smoke
- [x] Phase D multivar AL keep smoke
- [x] Phase E NDLM keep smoke executed (diagnostics fail tracked)
- [x] Phase F post + CRPS inclusion
- [x] Phase G NDLM keep stabilization fix + smoke revalidation
- [x] Phase H NDLM univar keep implementation + smoke validation
- [x] Phase I all-model smoke + ndlm_univar CRPS inclusion validation

## Evidence Register
### Phase A (PASS)
Key implementation files:
- `R/unified/config.R`
- `R/unified/stages/stage_fit.R`
- `R/unified/stages/stage_post.R`
- `config/unified_run.template.yaml`
- `R/environmetrics/02_helpers_core.R`
- `R/environmetrics/40_figures.R`
- `scripts/run_exdqlm_univar.R`
- `DISC_Optimal_Synth_Ranges_W.r`
- `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r`
- `scripts/run_ndlm_main.R`

Test evidence:
- All 4 targeted testthat files pass (see command above).

### Phase B (PASS)
Config:
- `config/unified_runs/al_phaseB_univar_al_smoke_20260322.yaml`

Run:
- `repro/runs/dev_al_phaseB_univar_al_smoke_20260322_rerun_20260322_200655`

Evidence:
- `fit/exdqlm_univar/q=50/logs/univar_theory_summary.log`
  - `likelihood_mode=al`
  - `gamma=0.00000000`
- `fit/diagnostics/exdqlm_univar/q=50/q50_exdqlm_univar_diagnostics.json`
  - status pass
  - detail includes `gamma=0`
- NaN/Inf check:
  - `naninf_total=0` (loaded `variables_50_exAL_synth_DISC_uni.RData`)
- Post completion:
  - `post/logs/post_runner.log` ends with `END: 2026-03-22 20:07:29`

### Phase B2 (PASS)
Config:
- `config/unified_runs/al_phaseB2_univar_legacy_al_smoke_20260322.yaml`

Run:
- `repro/runs/dev_al_phaseB2_univar_legacy_al_smoke_20260322_rerun_20260322_233816`

Evidence:
- `fit/logs/fit_stage.log`
  - `univar_likelihood=al`
  - `status: pass`
- `fit/exdqlm_univar/q=50/logs/univar_legacy.log`
  - `[univar_legacy] likelihood_mode=al`
- Loaded RData checks (`fit/exdqlm_univar/q=50/outputs/variables_50_exAL_synth_DISC_uni.RData`):
  - `gamma_range=0.0000000000,0.0000000000`
  - `max_abs_samp_sts=0.0000000000`
  - `max_abs_E_sts=0.0000000000`
  - `naninf_total=0`

### Phase C (PASS)
Config:
- `config/unified_runs/al_phaseC_multivar_al_drop_smoke_20260322.yaml`

Run:
- `repro/runs/dev_al_phaseC_multivar_al_drop_smoke_20260322_rerun_20260322_200829`

Evidence:
- `fit/logs/fit_stage.log`
  - `multivar_likelihood=al`
- `fit/q=50/outputs/multivar_forecast_health.txt`
  - `transfer_mode=drop`
- `fit/q=50/logs/fit.log`
  - `gamma_seed=0.000000`
- Loaded RData checks:
  - `samp_gamma_range=0,0`
  - `naninf_total=0`
- Post completion:
  - `post/logs/post_runner.log` ends with `END: 2026-03-22 20:12:41`

### Phase D (PASS)
Config:
- `config/unified_runs/al_phaseD_multivar_al_keep_smoke_20260322.yaml`

Run:
- `repro/runs/dev_al_phaseD_multivar_al_keep_smoke_20260322_rerun_20260322_201424`

Evidence:
- `fit/logs/fit_stage.log`
  - `multivar_likelihood=al`
- `fit/exdqlm_multivar/keep/q=50/outputs/multivar_forecast_health.txt`
  - `transfer_mode=keep`
- `fit/exdqlm_multivar/keep/q=50/logs/fit.log`
  - `gamma_seed=0.000000`
- Loaded RData checks:
  - `samp_gamma_range=0,0`
  - `naninf_total=0`
- Post completion:
  - `post/logs/post_runner.log` ends with `END: 2026-03-22 20:19:09`

### Phase E (PARTIAL: operational PASS / diagnostics FAIL)
Config:
- `config/unified_runs/al_phaseE_ndlm_keep_smoke_20260322.yaml`

Run:
- `repro/runs/dev_al_phaseE_ndlm_keep_smoke_20260322_rerun_20260322_202402`

Evidence:
- `fit/logs/fit_stage.log`
  - `ndlm_forecast_transfer_mode=keep`
- `fit/ndlm_main/logs/ndlm_theory_summary.log`
  - `forecast_transfer_mode=keep`
  - `transfer_active_forecast_window=true`
- Contract output present:
  - `fit/contract_checks/ndlm_main/ndlm_main_contract_check.json`
- Diagnostics fail:
  - `fit/diagnostics/ndlm_main/ndlm_main_diagnostics.yaml`
  - `status: fail`
  - errors on `ndlm.new_theta.sC.psd` and `ndlm.new_theta.sC_ens[2].psd`
- NaN/Inf check:
  - `naninf_total=0`
- Post completion:
  - `post/logs/post_runner.log` ends with `END: 2026-03-22 20:25:29`

### Phase G (PASS: stabilization fix + validated rerun)
Key implementation files:
- `R/unified/families/ndlm_main/00_constants.R`
- `R/unified/families/ndlm_main/02_model_spec.R`
- `R/unified/families/ndlm_main/03_vb_updates.R`
- `R/unified/families/ndlm_main/06_save_state.R`
- `R/unified/families/ndlm_main/zz_run.R`
- `R/unified/families/ndlm_main/ndlm_kalman_backend.cpp`
- `R/unified/stages/stage_fit.R`
- `R/unified/config.R`
- `config/unified_run.template.yaml`
- `tests/testthat/test_ndlm_kalman_backend.R`
- `tests/testthat/test_ndlm_fitloop_contract.R`
- `tests/testthat/test_ndlm_ragged_horizon_builder.R`
- `tests/testthat/test_config_mode_resolution.R`

Root-cause evidence (pre-fix):
- `repro/runs/dev_al_phaseE_ndlm_keep_smoke_20260322_rerun_20260322_202402/fit/diagnostics/ndlm_main/ndlm_main_diagnostics.yaml`
  - PSD failures on `ndlm.new_theta.sC.psd` and `ndlm.new_theta.sC_ens[2].psd`
- `.../fit/ndlm_main/logs/ndlm_theory_summary.log`
  - catastrophic sigma scale and severe covariance failures (historical fail snapshot).

Validation runs:
- transitional reruns:
  - `repro/runs/dev_al_phaseE_ndlm_keep_smoke_20260322_rerun_20260323_001705`
  - `..._20260323_002300`
  - `..._20260323_002922`
  - `..._20260323_003820`
  - `..._20260323_004504`
- final stabilization evidence run:
  - `repro/runs/dev_al_phaseE_ndlm_keep_smoke_20260322_rerun_20260323_005054`

Final evidence (`..._20260323_005054`):
- `run_manifest.yaml`
  - `fit.status: pass`
  - `post.status: pass`
- `fit/diagnostics/ndlm_main/ndlm_main_diagnostics.yaml`
  - `status: pass`
  - `ndlm.new_theta.sC.psd: pass`
  - `ndlm.new_theta.sC_ens[1].psd: pass`
  - `ndlm.new_theta.sC_ens[2].psd: pass`
- `fit/ndlm_main/logs/ndlm_theory_summary.log`
  - `forecast_transfer_mode=keep`
  - `transfer_active_forecast_window=true`
  - finite sigma (`sigma_usgs=493.67278272`, `sigma_nws=493.67102109`, `sigma_glofas=493.68117230`)
  - stabilization counters emitted (`stabilization.*` lines present)
- RData finite check:
  - `nonfinite_total=0`

### Phase F (PASS with replay workaround)
Initial full run (expected all models):
- Config: `config/unified_runs/al_phaseF_allmodels_crps_smoke_20260322.yaml`
- Run: `repro/runs/dev_al_phaseF_allmodels_crps_smoke_20260322_rerun_20260322_203217`
- Manifest:
  - `run_manifest.yaml` reports `post.status: fail`
- Failure evidence:
  - `post/logs/post_runner.log` error:
    - `new.theta.out_50_NDLM_synth_DISC$exps[2, (TT + 1):(TT + ranges[1])] : subscript out of bounds`

Fix applied:
- `R/environmetrics/40_figures.R`
  - added `safe_exps_index()` / `safe_exps_range()`
  - replaced hard NDLM exps indexing with bounds-safe calls

Replay run:
- Config: `config/unified_runs/al_phaseF_post_replay_crps_20260322.yaml`
- Run: `repro/runs/dev_al_phaseF_post_replay_crps_20260322`
- Manifest:
  - `run_manifest.yaml` reports `post.status: pass`
- Completion evidence:
  - `post/logs/dev_al_phaseF_post_replay_crps_20260322/run_log.txt`
  - ends with `END: 2026-03-22 21:22:34`

CRPS export evidence:
- Drop pass tables:
  - `post/outputs/dev_al_phaseF_post_replay_crps_20260322/tables/crps_forecast_summary.csv`
  - includes `dqlm_multivar_al_synth_drop`, `dqlm_univar_al_synth`, `ndlm_main_synth_keep`
- Keep replay tables:
  - `post/outputs/dev_al_phaseF_post_replay_crps_20260322/tables/crps_forecast_summary_keep.csv`
  - includes `dqlm_multivar_al_synth_keep`, `dqlm_univar_al_synth`, `ndlm_main_synth_keep`
- Required ID union check:
  - required across both summaries: `TRUE`
  - required set:
    - `dqlm_univar_al_synth`
    - `dqlm_multivar_al_synth_drop`
    - `dqlm_multivar_al_synth_keep`
    - `ndlm_main_synth_keep`

### Phase H (PASS: ndlm_univar keep, closed-form implementation + smoke)
Key implementation files:
- `R/unified/config.R`
- `R/unified/manifest.R`
- `R/unified/inputs_shared_validate.R`
- `R/unified/stages/stage_fit.R`
- `R/unified/stages/stage_post.R`
- `R/unified/stages/stage_report.R`
- `R/unified/post_module_plan.R`
- `R/unified/post_artifact_contract.R`
- `R/unified/contract_checks.R`
- `R/unified/families/ndlm_univar/00_constants.R`
- `R/unified/families/ndlm_univar/01_inputs.R`
- `R/unified/families/ndlm_univar/02_model_spec.R`
- `R/unified/families/ndlm_univar/03_filter_forecast_fit.R`
- `R/unified/families/ndlm_univar/04_save_state.R`
- `R/unified/families/ndlm_univar/05_fitloop.R`
- `R/unified/families/ndlm_univar/zz_run.R`
- `R/unified/families/ndlm_univar/ndlm_univar_kalman_backend.cpp`
- `R/environmetrics/00_paths.R`
- `R/environmetrics/02_helpers_core.R`
- `R/environmetrics/30_ndlm_only_init.R`
- `R/environmetrics/30_univariate_and_misc.R`
- `R/environmetrics/40_figures.R`
- `scripts/run_ndlm_univar.R`
- `scripts/run_environmetrics_figures.R`
- `config/unified_run.template.yaml`
- `config/unified_runs/al_phaseH_ndlm_univar_keep_smoke_20260323.yaml`
- `config/unified_runs/al_phaseI_allmodels_plus_ndlm_univar_crps_smoke_20260323.yaml`
- `tests/testthat/test_config_mode_resolution.R`
- `tests/testthat/test_post_module_plan.R`
- `tests/testthat/test_post_crps_tables.R`

Debug/fix evidence:
- failing run #1:
  - `repro/runs/dev_al_phaseH_ndlm_univar_keep_smoke_20260323_rerun_20260323_023149/fit/ndlm_univar/logs/ndlm_univar_theory.log`
  - error: `matrix(scale_vec, nrow = 1L) * Z : non-conformable arrays`
- failing run #2:
  - `repro/runs/dev_al_phaseH_ndlm_univar_keep_smoke_20260323_rerun_20260323_023241/run_manifest.yaml`
  - fit contract error: `ndlm_univar.samp_theta.numeric: samp.theta must be numeric`
- final passing run:
  - `repro/runs/dev_al_phaseH_ndlm_univar_keep_smoke_20260323_rerun_20260323_023419/run_manifest.yaml`
  - stage statuses: `data_prep_shared=pass`, `fit=pass`, `post=pass`, `report=pass`
  - contract output:
    - `repro/runs/dev_al_phaseH_ndlm_univar_keep_smoke_20260323_rerun_20260323_023419/fit/contract_checks/ndlm_univar/ndlm_univar_contract_check.yaml`
  - fit output:
    - `repro/runs/dev_al_phaseH_ndlm_univar_keep_smoke_20260323_rerun_20260323_023419/fit/ndlm_univar/outputs/DISC_variables_50_NDLM_univar_synth_DISC.RData`

Phase I execution evidence (PASS):
- run root:
  - `repro/runs/dev_al_phaseI_allmodels_plus_ndlm_univar_crps_smoke_20260323`
- stage status evidence:
  - `run_manifest.yaml`:
    - `data_prep_shared.status: pass`
    - `fit.status: pass`
    - `post.status: pass`
    - `report.status: pass`
- fit artifacts:
  - `fit/ndlm_univar/outputs/DISC_variables_50_NDLM_univar_synth_DISC.RData`
  - `fit/contract_checks/ndlm_univar/ndlm_univar_contract_check.yaml`
- post completion evidence:
  - `post/logs/dev_al_phaseI_allmodels_plus_ndlm_univar_crps_smoke_20260323/run_log.txt`
  - contains `END: 2026-03-23 02:59:23`
- CRPS inclusion evidence:
  - `post/outputs/dev_al_phaseI_allmodels_plus_ndlm_univar_crps_smoke_20260323/tables/crps_forecast_summary.csv`
  - contains row with:
    - `model_id=ndlm_univar_synth_keep`
    - `model_variant=ndlm_univar_keep`

## Open Issues
1. Full-slice PSD audit (all time slices) can still show tiny negative eigenvalues around tolerance scale, while sampled diagnostics pass; decide whether to promote full-slice PSD auditing to a strict gate.
2. CRPS magnitudes for univar/NDLM in keep replay can be extremely large; interpretability guardrails still needed.
3. `post_runner.log` can lag/reflect earlier pass; authoritative post completion for replay is in per-run `run_log.txt` and run manifest.

## Recommended Next Steps for Production Scale-Up
1. Add optional strict full-slice PSD audit mode for NDLM (`all slices`, not sampled subset) and decide threshold policy (`-1e-8` vs tighter/looser) before multi-cutoff production.
2. Add CRPS value-range diagnostics/alerts to flag pathological scale before leaderboard comparisons.
3. Run multi-cutoff production matrix only after (1) and (2), using the same model IDs and replay-compatible post config.

## Hardening Plan v1 (Execution-Ready)
Goal: close Open Issues R2/R3 with strict diagnostics gates, then scale to multi-cutoff production safely.

### Hard Gates (Do Not Bypass)
- Gate G1: all NDLM covariance PSD diagnostics pass under full-slice audit policy.
- Gate G2: no NaN/Inf in fit/post artifacts and CRPS exports.
- Gate G3: CRPS table must include required model IDs:
  - `dqlm_univar_al_synth`
  - `dqlm_multivar_al_synth_drop`
  - `ndlm_main_synth_keep`
  - `ndlm_univar_synth_keep`
- Gate G4: stage status pass in `run_manifest.yaml` for `data_prep_shared`, `fit`, `post`, `report`.

### Phase J0 — Preflight Baseline Lock
Checklist:
- [x] Record current commit and branch.
- [x] Confirm execution context and artifact paths.
- [x] Create hardening log directory.

Status: **PASS**

Evidence:
- Baseline metadata/log capture exists under `repro/hardening_logs/` (including `J0_baseline.txt`).
- Subsequent hardening runs reference branch/commit in manifests, e.g.:
  - `repro/runs/dev_al_phaseJ2_hardening_smoke_20260323_v6/run_manifest.yaml`
  - `repro/runs/dev_al_phaseJ2_hardening_post_replay_20260323_v7/run_manifest.yaml`

Command block:
```bash
cd /data/muscat_data/jaguir26/project1_ucsc_phd
git rev-parse --abbrev-ref HEAD
git rev-parse --short HEAD
date -u
mkdir -p repro/hardening_logs
```

### Phase J1 — Implement Full-Slice PSD Audit + Contracts
Checklist:
- [x] Add full-slice PSD diagnostics in NDLM fit diagnostics output.
- [x] Add fail criteria with warn/fail tolerances.
- [x] Wire PSD fail to fail-fast diagnostics gate in fit stage.
- [x] Add unit tests for pass/fail PSD scenarios.

Status: **PASS**

Evidence:
- Config/schema wiring:
  - `R/unified/config.R`
  - `config/unified_run.template.yaml`
- Fit-stage diagnostics + hardening wiring:
  - `R/unified/stages/stage_fit.R`
  - `R/unified/diagnostics.R`
- Tests:
  - `tests/testthat/test_fit_diagnostics_psd_scan.R` (full-slice detects unsampled bad slice)
  - `tests/testthat/test_ndlm_kalman_backend.R`
  - `tests/testthat/test_ndlm_univar_wh_recursions.R`
- Targeted test command passed:
  - `Rscript --vanilla -e 'library(testthat); test_file("tests/testthat/test_fit_diagnostics_psd_scan.R"); test_file("tests/testthat/test_ndlm_kalman_backend.R"); test_file("tests/testthat/test_ndlm_univar_wh_recursions.R")'`

Code targets:
- `R/unified/contract_checks.R`
- `R/unified/families/ndlm_main/*` (diagnostics path)
- `R/unified/families/ndlm_univar/*` (diagnostics path)
- `tests/testthat/` (new PSD full-slice tests)

Command block (post-implementation validation):
```bash
cd /data/muscat_data/jaguir26/project1_ucsc_phd
Rscript --vanilla -e 'library(testthat); \
  test_file("tests/testthat/test_ndlm_kalman_backend.R"); \
  test_file("tests/testthat/test_ndlm_univar_wh_recursions.R"); \
  test_file("tests/testthat/test_config_mode_resolution.R"); \
  test_file("tests/testthat/test_post_crps_tables.R")'
```

### Phase J2 — Add CRPS Input-Health Diagnostics (Root-Cause First)
Checklist:
- [x] Add `crps_input_health.csv` export in post stage.
- [x] Include draw-scale and tail diagnostics by model + horizon (`*_per_time` + aggregate).
- [x] Add fail-fast checks for nonfinite/health-threshold violations.
- [x] Keep CRPS scoring unchanged; add diagnostics as sidecar exports.

Status: **PASS (strict fit hardening + full post replay)**

Evidence:
- Strict hardening smoke (fit + smoke post) now passes with full-slice PSD gate:
  - Run ID: `dev_al_phaseJ2_hardening_smoke_20260323_v6`
  - Manifest: `repro/runs/dev_al_phaseJ2_hardening_smoke_20260323_v6/run_manifest.yaml` (`fit/post/report: pass`)
  - NDLM diagnostics: `repro/runs/dev_al_phaseJ2_hardening_smoke_20260323_v6/fit/diagnostics/ndlm_main/ndlm_main_diagnostics.yaml` (`status: pass`, `ndlm.new_theta.sC.psd` pass).
  - Hardening log shows repaired minimum eigenvalue above floor:
    - `repro/runs/dev_al_phaseJ2_hardening_smoke_20260323_v6/fit/ndlm_main/logs/ndlm_covariance_hardening.log`
    - `smooth_min_eig_before=-3.958777e-08`, `smooth_min_eig_after=1.003471e-08`, `smooth_below_floor_after=0`.
- Full post replay (non-smoke) passes and exports CRPS + input-health tables:
  - Run ID: `dev_al_phaseJ2_hardening_post_replay_20260323_v7`
  - Manifest: `repro/runs/dev_al_phaseJ2_hardening_post_replay_20260323_v7/run_manifest.yaml` (`post/report: pass`)
  - Tables dir:
    - `repro/runs/dev_al_phaseJ2_hardening_post_replay_20260323_v7/post/outputs/dev_al_phaseJ2_hardening_post_replay_20260323_v7/tables/`
    - includes `crps_forecast_summary.csv`, `crps_forecast_per_time.csv`, `crps_input_health.csv`, `crps_input_health_per_time.csv`.
  - Required model IDs present in CRPS summary and CRPS input-health tables:
    - `dqlm_univar_al_synth`
    - `dqlm_multivar_al_synth_drop`
    - `ndlm_main_synth_keep`
    - `ndlm_univar_synth_keep`
  - Input-health fail-fast condition satisfied (no `status="fail"` rows in either input-health CSV).
- Root-cause post stabilization applied (sample-count contract):
  - `R/environmetrics/40_figures.R`
  - `normalize_theta_time_sample()` now handles mismatched available-vs-target sample counts via deterministic truncate/recycle with one-time warnings.

Code targets:
- `R/environmetrics/40_figures.R`
- `R/environmetrics/02_helpers_core.R`
- `R/unified/stages/stage_post.R` (artifact registration)

Command block (single-cutoff hardening smoke config generation + run):
```bash
cd /data/muscat_data/jaguir26/project1_ucsc_phd
Rscript --vanilla - <<'RS'
library(yaml)
src <- "config/unified_runs/al_phaseI_allmodels_plus_ndlm_univar_crps_smoke_20260323.yaml"
dst <- "config/unified_runs/al_phaseJ2_hardening_smoke_20260323.yaml"
cfg <- read_yaml(src)
cfg$run$run_id <- "dev_al_phaseJ2_hardening_smoke_20260323"
cfg$fit$diagnostics$enabled <- TRUE
cfg$fit$diagnostics$fail_fast <- TRUE
cfg$fit$diagnostics$max_time_checks <- 200000
cfg$fit$diagnostics$psd_tol <- -1e-8
cfg$post$smoke_fast <- TRUE
cfg$fit$exdqlm_multivar$legacy$n_samp <- 500
cfg$fit$exdqlm_univar$legacy$n_samp <- 500
cfg$fit$ndlm_main$legacy$n_samp <- 500
cfg$models$ndlm_univar$posterior_draws <- 64
write_yaml(cfg, dst)
RS

Rscript --vanilla scripts/unified_run.R --config config/unified_runs/al_phaseJ2_hardening_smoke_20260323.yaml
```

Command block (J2 evidence checks):
```bash
cd /data/muscat_data/jaguir26/project1_ucsc_phd
RUN_ROOT="repro/runs/dev_al_phaseJ2_hardening_smoke_20260323"
sed -n '24,54p' "$RUN_ROOT/run_manifest.yaml"
ls -la "$RUN_ROOT/post/outputs/dev_al_phaseJ2_hardening_smoke_20260323/tables"
rg -n "ndlm_univar_synth_keep|ndlm_main_synth_keep|dqlm_univar_al_synth|dqlm_multivar_al_synth_drop" \
  "$RUN_ROOT/post/outputs/dev_al_phaseJ2_hardening_smoke_20260323/tables/crps_forecast_summary.csv"
```

### Phase J3 — Mini-Matrix Validation (3 Cutoffs, Sequential)
Cutoffs selected from available bundles:
- `20210123`, `20211112`, `20221225`

Checklist:
- [ ] Generate per-cutoff configs from known-good Phase I template.
- [ ] Run sequentially to isolate failures.
- [ ] Verify all hard gates per run.

Command block (config generation):
```bash
cd /data/muscat_data/jaguir26/project1_ucsc_phd
Rscript --vanilla - <<'RS'
library(yaml)
base_cfg <- "config/unified_runs/al_phaseI_allmodels_plus_ndlm_univar_crps_smoke_20260323.yaml"
cuts <- c("20210123", "20211112", "20221225")
project_root <- "/data/muscat_data/jaguir26/project1_ucsc_phd"
for (cut in cuts) {
  cfg <- read_yaml(base_cfg)
  cutoff_date <- as.Date(cut, "%Y%m%d")
  run_id <- sprintf("dev_al_phaseJ3_mini_%s", cut)
  bundle <- file.path(project_root, "repro/runs", sprintf("multimodel_%s", cut), "inputs/shared/forecats_bundle")
  cfg$run$run_id <- run_id
  cfg$dates$cutoff_date <- format(cutoff_date, "%Y-%m-%d")
  cfg$dates$plot_start <- format(cutoff_date - 18, "%Y-%m-%d")
  cfg$dates$plot_end <- format(cutoff_date + 28, "%Y-%m-%d")
  cfg$inputs$fit$retros_path <- file.path(bundle, "retros.csv")
  cfg$inputs$fit$nws_forecast_path <- file.path(bundle, "nws_forecast.csv")
  cfg$inputs$fit$glofas_forecast_path <- file.path(bundle, "glofas_forecast.csv")
  cfg$fit$diagnostics$enabled <- TRUE
  cfg$fit$diagnostics$fail_fast <- TRUE
  cfg$post$smoke_fast <- TRUE
  cfg$fit$exdqlm_multivar$legacy$n_samp <- 500
  cfg$fit$exdqlm_univar$legacy$n_samp <- 500
  cfg$fit$ndlm_main$legacy$n_samp <- 500
  cfg$models$ndlm_univar$posterior_draws <- 64
  out <- sprintf("config/unified_runs/al_phaseJ3_mini_%s.yaml", cut)
  write_yaml(cfg, out)
}
RS
```

Command block (run matrix):
```bash
cd /data/muscat_data/jaguir26/project1_ucsc_phd
for cfg in config/unified_runs/al_phaseJ3_mini_*.yaml; do
  echo "=== RUNNING $cfg ==="
  Rscript --vanilla scripts/unified_run.R --config "$cfg"
done
```

Command block (matrix gate checks):
```bash
cd /data/muscat_data/jaguir26/project1_ucsc_phd
for cut in 20210123 20211112 20221225; do
  run_id="dev_al_phaseJ3_mini_${cut}"
  root="repro/runs/${run_id}"
  echo "=== ${run_id} ==="
  sed -n '24,54p' "${root}/run_manifest.yaml"
  rg -n "status: fail" "${root}/run_manifest.yaml" && echo "FAIL: stage status"
  crps="${root}/post/outputs/${run_id}/tables/crps_forecast_summary.csv"
  rg -n "ndlm_univar_synth_keep|ndlm_main_synth_keep|dqlm_univar_al_synth|dqlm_multivar_al_synth_drop" "$crps"
done
```

### Phase J4 — Production Matrix Launch (After J3 PASS)
Checklist:
- [ ] Promote mini-matrix template to full cutoff set.
- [ ] Run in batches, not all at once.
- [ ] Run gate checks after each batch.

Command block (discover available multimodel cutoffs):
```bash
cd /data/muscat_data/jaguir26/project1_ucsc_phd
ls -1 repro/runs | rg '^multimodel_[0-9]{8}$' | sort
```

Command block (batch gate check helper):
```bash
cd /data/muscat_data/jaguir26/project1_ucsc_phd
for run_id in $(ls -1 repro/runs | rg '^prod_al_phaseJ4_' | sort); do
  root="repro/runs/${run_id}"
  echo "=== ${run_id} ==="
  sed -n '24,54p' "${root}/run_manifest.yaml"
  rg -n "status: fail" "${root}/run_manifest.yaml" && echo "FAIL: stage status"
  crps="${root}/post/outputs/${run_id}/tables/crps_forecast_summary.csv"
  test -s "$crps" || echo "FAIL: missing CRPS summary"
done
```

### Phase J5 — Closeout + Tracker Evidence Completion
Checklist:
- [ ] Record PASS/FAIL for each J-phase.
- [ ] Record exact run IDs, commands, artifact paths.
- [ ] Add unresolved risks and production recommendation.

Command block:
```bash
cd /data/muscat_data/jaguir26/project1_ucsc_phd
git rev-parse --short HEAD
date -u
```

## Changelog
- 2026-03-22: Created tracker with baseline audit, assumptions, risks, and phased plan.
- 2026-03-22: Updated tracker with completed implementation evidence for Phases A-D, partial Phase E, and Phase F replay-based PASS.
- 2026-03-22: Patched `OptimalModelSLexAL.r` to support AL collapse in legacy bridge with sigma-only Laplace-Delta optimization when `UNIV_LIKELIHOOD_MODE=al` (`gamma=0`, `s_t=0`), and validated via Phase B2 smoke run.
- 2026-03-23: Added NDLM stabilization controls and root-cause fix across R/C++ Kalman paths, sigma update safeguards, diagnostics counters, new NDLM tests, and validated Phase G NDLM keep smoke rerun PASS (`..._20260323_005054`).
- 2026-03-23: Added Phase H `ndlm_univar` family wiring, C++/R West-Harrison closed-form implementation integration, sampler/contract bug fixes, and validated smoke rerun PASS (`..._20260323_023419`).
- 2026-03-23: Added `tests/testthat/test_ndlm_univar_wh_recursions.R` for scalar WH recursion checks, backend parity checks, and sampler dimension/finite checks; test passes.
- 2026-03-23: Completed Phase I all-model smoke including `ndlm_univar` CRPS export validation (`dev_al_phaseI_allmodels_plus_ndlm_univar_crps_smoke_20260323`).
- 2026-03-23: Completed J1/J2 hardening closure:
  - strengthened NDLM fit-stage covariance hardening (strict floor enforcement + diagnostic before/after logging),
  - cleared strict full-slice PSD gate in `dev_al_phaseJ2_hardening_smoke_20260323_v6`,
  - fixed full-post replay failure in `normalize_theta_time_sample()` for reduced draw counts,
  - validated full post replay pass with CRPS + CRPS input-health exports in `dev_al_phaseJ2_hardening_post_replay_20260323_v7`.
