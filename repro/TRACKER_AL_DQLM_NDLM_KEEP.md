# TRACKER: AL DQLM + NDLM Keep (Unified Workflow)

## Metadata
- Created: 2026-03-22 (America/Los_Angeles)
- Last updated: 2026-03-31 05:55 (America/Los_Angeles)
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

## Focused Repair Program (2026-03-25 Refresh)
Goal:
- Pause full 9-model benchmark interpretation until the remaining suspect families are repaired under a narrower, auditable workflow.
- Primary repair targets:
  - `ndlm_main_synth_drop`
  - `ndlm_main_synth_keep` (propagate after `drop`)
  - `exdqlm_univar_synth`
  - `dqlm_univar_al_synth` (propagate after `exAL`)

Confirmed implementation facts:
- Current focused `ndlm_main` repair runs are using `implementation_mode: theory_aligned`, not `legacy_bridge`.
- Legacy NDLM bridge remains available through:
  - `scripts/run_DISC_Optimal_Synth_Ranges_NDLM.R`
  - `DISC_Optimal_Synth_Ranges_NDLM.r`
- Current focused `exdqlm_univar` repair runs use:
  - `implementation_mode: legacy_bridge` for the fit path;
  - the repaired dedicated univariate-only post module for synthesis, diagnostics, figures, and CRPS.

Confirmed theory/implementation facts to anchor the next repair:
- NDLM derivations explicitly allow two distinct covariance regimes:
  - learned covariance blocks with inverse-Wishart updates;
  - discount-fixed covariance blocks, in which case no full conditional exists for `W_t`.
- The exDQLM derivation notes document that current `project1` forecast-period covariance updates use a shrinkage-stabilized plug-in update rather than the inverse-Wishart CAVI update.
- Therefore, any theory-vs-legacy NDLM comparison must treat:
  - historical discount-fixed evolution;
  - forecast-period plug-in covariance updates;
  as separate implementation choices, not as an automatic mismatch or proof of error.
- Local external-reference availability:
  - `/data/muscat_data/jaguir26/exDQLM---Ensemble` is still documentation/theory oriented and does not provide the requested package branch.
  - `/data/muscat_data/jaguir26/exdqlm` is the full source repo and does expose:
    - local branch `cransub/0.4.0`
    - source file `R/exdqlm_synthesize_from_draws.R`
    - C++/R implementations backing `rexal`, `simulate_ts_mc_quantiles`, and related helpers.
  - focused univariate repair tests now use this local `exdqlm` source repo as the direct package-reference anchor.

Focused hypotheses:
1. `ndlm_main drop` failure is now narrowed to forecast-state / forecast-covariance propagation and export, not the basic run wrapper.
2. If `ndlm_main drop` is repaired at the forecast-state level, `ndlm_main keep` should inherit the same fix modulo transfer-coordinate inclusion.
3. `exdqlm_univar` no longer has the original isolated-post contract bug; the remaining failure is quantile coherence / crossing.
4. If `exdqlm_univar` forecast quantile coherence is fixed, the same repair pattern should carry to `dqlm_univar_al`.

Execution strategy:
1. Run one-cutoff, short-history repair loops only:
- cutoff: `2021-01-23`
- history start: `2010-01-01` by default; optionally `2018-01-01` for ultra-fast structural tests
- keep `.RData` and caches; do not use cleanup wrapper during repair

2. `ndlm_main drop`: legacy-vs-theory parity audit before further patching:
- compare on the same cutoff/history/discount settings:
  - active-set-by-lead structure
  - exported `sm_ens` / `sC_ens` dimensions
  - `sigma` / `sigma_mean`
  - forecast identity summaries
  - covariance spectra / PSD diagnostics
  - latent forecast draw ranges
- determine whether the theory-aligned path should match:
  - legacy plug-in forecast covariance update, or
  - a separately justified IW-driven forecast block

3. `exdqlm_univar`: reference-and-contract audit:
- reuse the repaired univariate-only post route
- run only `q = {0.05, 0.50, 0.95}` until quantile coherence is fixed
- validate:
  - CRPS finite and reasonable
  - zero/controlled crossing on median curves
  - sample-path crossing diagnostics materially reduced
  - forecast-window raw quantile and synthesis plots/tables look coherent

4. Propagation rules:
- only propagate `ndlm_main drop` fix to `keep` after the root cause is understood and tested
- only propagate `exdqlm_univar` fix to `dqlm_univar_al` after the exAL reference path is stable

Repair checklist:
- [ ] NDLM legacy-vs-theory parity run prepared on one cutoff / short history
- [ ] NDLM covariance-regime decision documented (`discount-fixed` vs `IW` vs `legacy plug-in`)
- [ ] NDLM `drop` root-cause fix implemented and tested
- [ ] NDLM `keep` propagated and validated
- [x] exAL univariate quantile-coherence defect isolated
- [x] exAL univariate synthesis/diagnostic repair harness implemented
- [x] exAL univariate root-cause fix implemented and tested on `q={0.05,0.50,0.95}`

## NDLM Exact VB/CAVI Rebuild (2026-03-26)
Status: **IMPLEMENTED ON TARGETED HARNESS; NOT YET RUN THROUGH FULL PRODUCTION MATRIX**

What changed:
- Replaced the active `ndlm_main` theory-aligned fit entrypoint with a new exact multivariate NDLM path:
  - true `drop` reduced forecast state
  - true `keep` augmented forecast state
  - one lead-specific forecast covariance factor per forecast lead
  - deterministic historical discount-induced covariances
  - fixed `lambda`
- Added a new transdimensional Kalman filter/smoother backend in R and C++ for the Gaussian state factor.
- Added a state-registry layer so all forecast means/discrepancies are extracted by projection vectors rather than hard-coded row arithmetic.
- Extended saved fit state to include:
  - `forecast_cov_factors`
  - `state_registry`
  - cleaned `forecast_identity` tables
  - lead-wise `state_dim_by_lead`

Files added / introduced into the active path:
- `R/unified/families/ndlm_main/07_state_registry.R`
- `R/unified/families/ndlm_main/08_vb_cavi_exact.R`
- `R/unified/families/ndlm_main/ndlm_kalman_backend.cpp` (new TV smoother export)

Files updated to wire the new path:
- `R/unified/families/ndlm_main/00_constants.R`
- `R/unified/families/ndlm_main/02_model_spec.R`
- `R/unified/families/ndlm_main/05_fitloop.R`
- `R/unified/families/ndlm_main/06_save_state.R`
- `scripts/run_ndlm_main.R`

Validation completed:
- Focused NDLM tests pass:
  - `test_ndlm_kalman_backend.R`
  - `test_ndlm_tv_backend.R`
  - `test_ndlm_exact_registry.R`
  - `test_ndlm_fitloop_contract.R`
  - `test_ndlm_exact_fit_contract.R`
  - `test_ndlm_save_state.R`
- Synthetic exact-fit harness passes for both modes:
  - `drop`: lead-1 state dim `21`, tail state dim `14`
  - `keep`: lead-1 state dim `27`, tail state dim `20`
  - forecast identity errors are numerically zero (`~1e-16`)
- Real script entrypoint validation passes for both modes using synthetic CSV inputs:
  - `scripts/run_ndlm_main.R`
  - `.RData` outputs saved successfully
  - summary logs emitted successfully
  - covariance diagnostics remained finite and SPD on the synthetic entrypoint run

Current limitations / next required step:
- The new path is validated on unit tests, toy exact-fit harnesses, and synthetic CLI entrypoint runs.
- It has **not yet** been run on the real targeted `2021-01-23` NDLM repair fixture after the full derivation-aligned rebuild.
- `seq_elbo` in the new exact path is currently a convergence objective trace, not a fully expanded closed-form ELBO proof object; keep this explicit until the full state-entropy block is implemented.

Execution checklist after this rebuild:
- [x] exact transdimensional state registry implemented
- [x] exact `drop` / `keep` forecast-state handling implemented
- [x] transdimensional Kalman backend implemented in C++
- [x] active `ndlm_main` fit path rerouted to exact VB/CAVI engine
- [x] saved-state contract extended for forecast covariance/state registry diagnostics
- [x] targeted synthetic end-to-end script validation completed
- [ ] run real targeted NDLM `drop` repair case on `2021-01-23`
- [ ] inspect real forecast-window CRPS / identity / figure outputs for `drop`
- [ ] propagate / validate on real targeted NDLM `keep`
- [ ] reintegrate into suspect-only unified repair batch
- [x] exAL univariate full-7 repair run validated
- [x] AL univariate propagated and validated on `q={0.05,0.50,0.95}`
- [x] AL univariate full-7 repair run validated
- [ ] suspect-only integrated run (`ndlm_main drop/keep`, `exdqlm_univar`, `dqlm_univar_al`, optional `ndlm_univar` verification)
- [ ] only then resume full 9-model benchmark reruns

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
- [x] Phase J0 preflight baseline lock
- [x] Phase J1 strict full-slice PSD audit + contracts
- [x] Phase J2 CRPS input-health diagnostics + replay closure
- [x] Phase J3 mini-matrix validation (3 cutoffs + replay gate checks)
- [ ] Phase J4 production matrix launch (full cutoff set)
- [x] Phase J5 tracker closeout for J0-J3 evidence

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

## Benchmark Integrity Repair Program (Post-Production Hold)
### Status
- **Production benchmark expansion is paused here.**
- Reason:
  - completed production runs exposed benchmark-integrity issues that must be fixed before the 9-model benchmark can be trusted.
- Scope of this repair program:
  - isolate the suspect families
  - validate fit vs post responsibilities separately
  - add model-specific forecast-window diagnostics
  - re-enable full 9-model production only after targeted revalidation passes

### Current Findings (as of 2026-03-26)
#### Model-family integrity snapshot
| Family / output | Current assessment | Main issue class | Current evidence |
| --- | --- | --- | --- |
| `dqlm_multivar_al_synth_drop` | Plausible | no primary post-contract failure found yet | CRPS magnitudes plausible; multivar state projection consistent with theory |
| `dqlm_multivar_al_synth_keep` | Plausible | no primary post-contract failure found yet | CRPS magnitudes plausible; `keep` transfer projection matches intended semantics |
| `exdqlm_multivar_synth_drop` | Plausible | no primary post-contract failure found yet | CRPS magnitudes plausible; sample-level crossing exists but lead-wise medians remain broadly ordered |
| `exdqlm_multivar_synth_keep` | Plausible | no primary post-contract failure found yet | same as above |
| `ndlm_main_synth_drop` | **suspect / untrusted** | fit/projection scale + forecast covariance blow-up | repaired fit lowers `sigma` materially, but forecast latent draws still explode to `[-3.6e4, 3.9e4]` and isolated NDLM post overflows |
| `ndlm_main_synth_keep` | **suspect / untrusted** | fit/projection scale + post/CRPS contract | CRPS ~4044 across cutoffs; health medians around -121 with huge spread |
| `exdqlm_univar_synth` | accepted comparison workflow = `legacy_bridge` | theory-aligned tails remain experimental; accepted comparison mode is closed | corrected `l2` reintegration closure uses `implementation_mode=legacy_bridge`; mixed post/CRPS are healthy under the accepted comparison lane |
| `dqlm_univar_al_synth` | accepted comparison workflow = `legacy_bridge` | theory-aligned + `al` predictive contract remains experimental | isolated lineage-aligned validations now pass on five cutoffs and remove the prior inflated-tail CRPS pathology |
| `ndlm_univar_synth_keep` | plausible but must be verified | verification gap | CRPS scale is reasonable, but not yet checked with the same dedicated forecast-window diagnostics |

#### High-confidence discoveries
1. Multivariate NDLM is still a fit-side forecast-state problem, but it is now much narrower.
- The ensemble-member forecast-likelihood fix was necessary and improved the `drop` fit materially:
  - `sigma` fell from the old implausible range (`~285`) to `23.84804930` in `repair_r1_ndlm_main_drop_20210123_20260324_rerun_20260324_232509`.
- However, the repaired fit still exports exploding forecast latent draws:
  - `forecast_mean_draws_loglog1p` range `[-36035.3, 38917.1]`
  - `sC_ens` blocks still hit the stabilization cap (`~1e8`) with large negative off-diagonals.
- The isolated NDLM post now fails immediately on overflow:
  - `[EXP_OVERFLOW_RISK] ndlm.only.predictive.loglog1p max latent value 38912.135805 exceeds safe exp limit`
- Therefore the remaining defect is **not** the closed-form univariate NDLM family and **not** just the post wrapper; it is the multivariate NDLM forecast covariance / state-propagation path.

2. Univariate exDQLM / DQLM-AL repair is now closed on the isolated harness.
- The original univariate failures were a combination of:
  - a broken univariate-only post artifact contract; and
  - an incorrect isolated synthesis/forecast reconstruction path.
- Those are now repaired:
  - dedicated univariate-only post module
  - dedicated univariate-only artifact contract
  - run-scoped univariate synthesis caches and CRPS exports
  - direct synthesis parity against the local `exdqlm` source repo
- Evidence:
  - `repair_p5_univar_exal_triage_20210123_20260325_post_replay_fix3` -> `OVERALL=pass`
  - `repair_p6_univar_exal_full7_20210123_20260325` -> `OVERALL=pass`
  - `repair_p7_univar_al_triage_20210123_20260325` -> `OVERALL=pass`
  - `repair_p7_univar_al_full7_20210123_20260325` -> `OVERALL=pass`
- Current interpretation:
  - synthesized univariate curves are now monotone and benchmark-ready on the isolated harness
  - residual raw-model crossing in `AL full7` is documented (`raw_crossing_share = 0.107143`) but is not a benchmark blocker because CRPS and the benchmark contract are defined on synthesized outputs
  - the remaining work for univariate families is reintegration, not root-cause repair

3. Multivariate exDQLM / DQLM post logic is broadly aligned with theory.
- `drop` vs `keep` semantics are implemented correctly in forecast `FF/GG` handling.
- The multivariate USGS reconstruction is implemented through the state projection, which is equivalent to subtracting discrepancy from source so long as the state identity holds.
- A dedicated q50 transfer-state identity audit exists, but **it is not part of full production runs** because full runs source `40_figures.R`, not `40_figures_multivar_only.R`.

4. Univariate NDLM looks numerically plausible, but this must be elevated from "looks okay" to "verified okay" after `ndlm_main` is repaired.

### Immediate Decision
#### Do not continue full 9-model production until the targeted repair cycle passes.
Reason:
- rerunning all 9 families and all 7 quantiles while known benchmark-integrity defects remain is computationally expensive and analytically misleading.

### Isolation Strategy
#### Global debug profile
- Single cutoff only:
  - `2021-01-23`
- Shortened history:
  - `dates.data_start: "2010-01-01"`
- Targeted families only:
  - run only the suspect families under investigation in each phase
- Fit and post separated:
  - run `fit` for the suspect families
  - keep outputs
  - replay `post` from fit outputs as needed while debugging post logic
- Cleanup disabled during repair:
  - do **not** auto-delete `.RData` until the repair phase for that family is closed
- Strict run-scoped replay:
  - use `inputs.post.use_fit_outputs_from_run: true`
  - use `inputs.post.source_run_id` for post-only replays

#### Efficiency refinements (worth adopting)
1. **Use existing completed `2021-01-23` production artifacts as frozen post-replay fixtures before launching any new fit.**
- Reason:
  - many of the currently suspected failures can be diagnosed from cached fit outputs and post replay alone
  - this is faster than immediately launching new fits
- Initial frozen fixtures to reuse:
  - `prod_phaseK3_batchA_20210123_l1_fix1_20260324`
  - `prod_phaseK3_batchA_20210123_l2_20260324`

2. **For broken quantile-model families, use a triage quantile set first, then promote to the full 7 quantiles only after the path is repaired.**
- Triage set:
  - `0.05`, `0.50`, `0.95`
- Promotion set:
  - `0.05`, `0.20`, `0.35`, `0.50`, `0.65`, `0.80`, `0.95`
- Reason:
  - the current univariate failure is already obvious without all 7 quantiles
  - this cuts repair-cycle cost substantially while preserving tail/center diagnostics

3. **Do not use the cleanup wrapper during repair-mode runs.**
- Use `scripts/unified_run.R` directly with `CLEANUP_RDATA_AFTER_POST=0`.
- Reason:
  - repair-mode post replay depends on keeping the fit artifacts available

#### Important current workflow limitation
- Multivariate-only targeted post runs already have a dedicated path via `40_figures_multivar_only.R`.
- NDLM-only targeted runs already have an isolated post path via `40_figures_ndlm_only.R`.
- Univariate-only targeted runs now have a dedicated full repair path:
  - `40_figures_smoke_fast.R` for lightweight diagnostics
  - `40_figures_univar_only.R` for univariate-only forecast-window figures, caches, CRPS exports, and artifact contract closure
- Remaining limitation:
  - multivariate identity audits are still not embedded in the main production-compatible path
  - NDLM-only path still needs a deeper fix for forecast covariance explosion

### Repair Phases
#### R0. Freeze and baseline capture
Goal:
- stop interpreting current benchmark CRPS as final evidence
- capture the exact defect inventory in tracker and logs

Exit criteria:
- tracker updated
- suspect model list frozen
- no new full-production launches until repair closure

#### R1. Normalize validation contracts across model families
Goal:
- define a common validation surface so every family is checked coherently

Required checks:
1. Fit health
- no NaN/Inf in saved fit outputs
- expected dimensions / contract objects present

2. Forecast sample health
- finite share
- range diagnostics
- per-time summaries
- explicit scale-contract label

3. Forecast-window reconstruction audit
- multivariate quantile models:
  - USGS/source/discrepancy identity checks
- multivariate NDLM:
  - mean reconstruction identity checks
- univariate models:
  - direct forecast contract checks (no discrepancy-subtraction path)

4. Quantile-order diagnostics
- for quantile-model families:
  - sample-level monotonicity share
  - lead-wise median monotonicity

5. CRPS input-health checks
- model-specific CRPS inputs only
- fail-fast thresholds configurable

6. Forecast-window figures
- simple forecast-window-only visualization per model family:
  - true withheld USGS
  - 7 model quantile curves or 7 NDLM-derived Gaussian quantiles
  - synthesis quantiles
  - empirical synthesis quantiles

Exit criteria:
- unified checklist defined
- gaps by family documented
- tests planned for each contract

#### R2. Multivariate NDLM repair (`drop` + `keep`)
Priority: **highest**

Hypotheses to test:
1. forecast draws are on the wrong scale for CRPS/post
2. mean projection into USGS space is incorrect or incomplete
3. fit variance / sigma update is unstable or mis-scaled

Required work:
- inspect NDLM fit output objects end-to-end
- explicitly trace:
  - projected USGS mean
  - source means
  - discrepancy means
  - forecast predictive variance
- add dedicated multivariate NDLM mean-identity audit
- add explicit scale-contract diagnostics
- add forecast-window NDLM plot with:
  - true withheld USGS
  - 7 Gaussian quantiles implied by NDLM mean/variance
- recompute targeted CRPS only after the scale contract is verified

Runs:
0. frozen-fixture post replay first on existing `2021-01-23` outputs
1. `drop` only first
2. then `keep`
3. single cutoff `2021-01-23`
4. `dates.data_start: "2010-01-01"`

Fit rerun policy:
- do **not** rerun fit until the post-side scale contract and mean-identity diagnostics are implemented and exercised on the frozen fixture
- only rerun fit if the evidence shows the fit objects themselves are wrong, or if a fit-side patch is required

Exit criteria:
- NDLM forecast draws are on the intended scale
- NDLM mean reconstruction identity passes
- CRPS magnitudes become plausible
- `drop` and `keep` both pass targeted health tables

#### R3. Univariate exDQLM / DQLM-AL repair
Priority: **highest**

Hypothesis:
- current post/forecast generation still assumes the old univariate legacy state layout and is incompatible with the theory-aligned fit outputs.

Required work:
- create a proper univariate-only diagnostic post route
- stop relying on legacy `p=7/Gx/state_idx` assumptions where incompatible
- rebuild univariate forecast generation from the actual fitted theory-aligned objects
- verify:
  - state forecast moments
  - posterior predictive generation
  - synthesis inputs
  - quantile monotonicity diagnostics

Runs:
0. frozen-fixture post replay first on existing `2021-01-23` outputs
1. exAL first with triage quantiles `0.05/0.50/0.95`
2. AL second with triage quantiles `0.05/0.50/0.95`
3. once corrected, promote each to the full 7-quantile grid
4. single cutoff `2021-01-23`
5. `dates.data_start: "2010-01-01"`

Exit criteria:
- forecast sample ranges become plausible
- sample-level quantile-order failures are no longer pathological
- CRPS drops from astronomical values to plausible scale
- exAL and AL both pass the same univariate diagnostic contract

#### R4. Univariate NDLM verification
Priority: **medium**

Goal:
- upgrade `ndlm_univar_synth_keep` from plausible to verified

Required work:
- add the same forecast-window diagnostic figure style
- check Gaussian-quantile reconstruction from mean/variance
- check scale contract and CRPS input-health explicitly

Runs:
- `keep`
- single cutoff `2021-01-23`
- `dates.data_start: "2010-01-01"`

Exit criteria:
- no scale anomalies
- forecast-window figure and CRPS inputs look coherent

#### R5. Multivariate quantile-model verification hardening
Priority: **medium**

Goal:
- convert current informal confidence into explicit audited confidence

Required work:
- bring q50 transfer-state identity audit into the main production-compatible path or a targeted replay path
- add simple forecast-window plots for multivariate AL/exAL `drop`/`keep`
- check raw model quantiles, synthesis quantiles, and empirical synthesis quantiles together

Exit criteria:
- multivariate AL/exAL identity checks pass in targeted replays
- plot outputs exist and are reviewed

#### R6. Reintegration into main 9-model workflow
Priority: **only after R2-R5 pass**

Goal:
- fold corrected fit/post logic back into the main unified workflow

Required work:
- re-enable cleanup only after targeted repair runs are closed
- rerun a single-cutoff all-suspect-family integration check
- rerun a single-cutoff all-9-model integration check
- only then resume full multi-cutoff benchmark production

Exit criteria:
- single-cutoff all-9-model run passes
- CRPS values are credible across all model families
- figure outputs and health tables are coherent

### Standardized Repair Checklist
- [x] R0 tracker + freeze state complete
- [x] R1 common validation contract defined
- [x] R1 scale-contract checks implemented where missing
- [x] R1 forecast-window diagnostic plot spec implemented
- [x] R2 NDLM main `drop` isolated fit run completed
- [ ] R2 NDLM main `drop` post replay completed
- [ ] R2 NDLM main `drop` mean-identity checks pass
- [ ] R2 NDLM main `drop` CRPS input-health passes
- [ ] R2 NDLM main `keep` isolated fit run completed
- [ ] R2 NDLM main `keep` post replay completed
- [ ] R2 NDLM main `keep` mean-identity checks pass
- [ ] R2 NDLM main `keep` CRPS input-health passes
- [x] R3 univariate exAL isolated fit run completed
- [x] R3 univariate exAL corrected post route completed
- [x] R3 univariate exAL quantile-order checks pass at the synthesized-output level
- [x] R3 univariate exAL CRPS input-health passes
- [x] R3 univariate AL isolated fit run completed
- [x] R3 univariate AL corrected post route completed
- [x] R3 univariate AL quantile-order checks pass at the synthesized-output level
- [x] R3 univariate AL CRPS input-health passes
- [ ] R4 univariate NDLM verification run completed
- [ ] R4 univariate NDLM verification checks pass
- [ ] R5 multivariate AL/exAL identity audits integrated and passing
- [ ] R6 single-cutoff all-suspect-family integration run passes
- [ ] R6 single-cutoff all-9-model integration run passes
- [ ] full production benchmark resume authorized

### Recommended Execution Order
1. `R1` common validation contract on frozen `2021-01-23` fixtures
2. `ndlm_main drop` frozen-fixture replay, then fit rerun only if needed
3. `ndlm_main keep` frozen-fixture replay, then fit rerun only if needed
4. `ndlm_univar keep` verification
5. multivariate AL/exAL verification hardening
6. all-suspect integration
7. all-9-model reintegration

Reason:
- this addresses the only remaining untrusted benchmark rows first
- the univariate repair scope is already closed on the isolated harness
- it avoids wasting compute on families that currently look plausible

### NDLM Next-Step Program (Post-P5/P6/P7)
#### Active scope
- Active blocker family:
  - `ndlm_main drop`
  - `ndlm_main keep` only after `drop`
- Deferred until after `ndlm_main` closure:
  - `ndlm_univar` verification
  - suspect-only reintegration
  - all-9-model reintegration

#### What is already known
1. The current blocker is **not** `ndlm_univar`.
- `ndlm_univar` is the closed-form West-Harrison path and is not the source of the current overflow / CRPS blow-up investigation.

2. The current blocker is **not** primarily the NDLM post wrapper.
- isolated NDLM post replay is failing because the fit outputs already contain exploding latent forecast draws and covariance blocks

3. The remaining `ndlm_main` issue is now narrow.
- forecast latent draws still explode in `drop` after the ensemble-member forecast-likelihood repair
- the likely root region is:
  - forecast-state propagation
  - forecast covariance recursion/export
  - mean/variance reconstruction into USGS space

#### NDLM execution principles
1. Do not restart full 9-model production while `ndlm_main` remains untrusted.
2. Use a single cutoff and short history until the root cause is identified:
- cutoff: `2021-01-23`
- history start: `2010-01-01`
3. Keep artifacts during NDLM repair:
- `CLEANUP_RDATA_AFTER_POST=0`
4. Use frozen fixtures first, then rerun fit only when a fit-side patch is justified.
5. Use production-like discount settings for parity and repair validation.
6. Use near-1 discount factors only for micro structural tests, not as the main proof harness.

#### NDLM phase program
##### N0. Freeze the NDLM target and evidence surface
Objective:
- make the `drop` root cause explicit before any new algorithmic patching

Checklist:
- [ ] select canonical frozen fixture for `drop`
- [ ] select canonical frozen fixture for `keep`
- [ ] list the exact output objects that define the NDLM debug surface
- [ ] define the pass/fail thresholds for latent-range, PSD, and identity checks

Evidence surface to freeze:
- `sigma`, `sigma_mean`
- `sm_ens`, `sC_ens`
- `forecast_mean_draws_loglog1p`
- `mu_usgs_post`, `var_usgs_post`
- forecast member counts by lead
- NDLM-only post replay logs

##### N1. Legacy-vs-theory parity audit for `ndlm_main drop`
Objective:
- determine whether the theory-aligned path is diverging from legacy because of:
  - observation construction
  - forecast covariance regime
  - state export slicing
  - USGS mean/variance reconstruction

Checklist:
- [ ] run one `legacy_bridge` `drop` fit on `2021-01-23`
- [ ] run one `theory_aligned` `drop` fit on the same data window
- [ ] diff both outputs on:
  - `sigma`, `sigma_mean`
  - active-set-by-lead
  - forecast member counts by lead
  - `sm_ens` / `sC_ens` dimensions
  - latent forecast range
  - covariance eigen ranges
- [ ] record the first stage where parity breaks

Decision gate:
- if parity breaks before forecast export, patch fit-side logic first
- if parity holds through fit export but breaks in post replay, patch NDLM post reconstruction first

##### N2. Covariance-regime decision
Objective:
- decide the exact forecast covariance regime that `ndlm_main` should implement in this project

Options to evaluate:
1. discount-fixed historical covariance + forecast extension / plug-in update
2. learned covariance block with inverse-Wishart treatment
3. strict legacy parity target for benchmark comparability

Checklist:
- [ ] compare current theory notes with current `project1` benchmark intent
- [ ] document the chosen regime in the tracker before patching
- [ ] reject any patch that mixes regimes implicitly

Constraint:
- no partial or hybrid patch without documenting the intended covariance regime

##### N3. Instrument the NDLM fit/export boundary
Objective:
- expose the exact place where `drop` becomes numerically implausible

Required instrumentation:
- [ ] lead-wise latent mean range
- [ ] lead-wise latent variance range
- [ ] PSD / eigen minima for every exported covariance slice
- [ ] mean-reconstruction audit for USGS space
- [ ] explicit scale-contract label for each saved output object

Required mean/variance identities:
- [ ] verify the saved USGS mean reconstruction matches the intended discrepancy decomposition
- [ ] verify Gaussian quantiles used in NDLM-only post are derived from the same mean/variance objects
- [ ] verify the CRPS path scores the intended scale, not the latent scale

Exit gate:
- a single report must identify whether the failure first appears in:
  - state recursion
  - covariance recursion
  - export assembly
  - post transformation / scoring

##### N4. Frozen-fixture post replay with the new diagnostics
Objective:
- test the new diagnostics on preserved `drop` fit outputs before launching a new fit

Checklist:
- [ ] replay NDLM-only post on the frozen `drop` fixture
- [ ] emit the new mean/variance identity outputs
- [ ] emit forecast-window NDLM plot:
  - withheld USGS
  - NDLM mean
  - 7 Gaussian quantiles implied by the saved mean/variance
- [ ] emit targeted CRPS input-health table for NDLM only

Success criteria:
- scale contract is explicit
- mean-reconstruction audit is explicit
- the replay either passes or isolates the exact failing object and lead window

##### N5. Patch `ndlm_main drop`, rerun, and gate
Objective:
- make one principled fix to the root-cause region, then rerun only `drop`

Checklist:
- [ ] implement one root-cause patch
- [ ] add regression tests for that patch
- [ ] run targeted `drop` fit
- [ ] run NDLM-only post replay on the new fit outputs
- [ ] confirm:
  - latent forecast range is plausible
  - covariance slices remain PSD within tolerance
  - mean identity passes
  - CRPS input-health passes
  - CRPS magnitude is plausible

Stop condition:
- if the rerun still fails, do not patch `keep`; return to N1/N3 evidence and isolate the next discrepancy

##### N6. Propagate to `ndlm_main keep`
Objective:
- verify that the `drop` fix carries to `keep` when transfer is active during the forecast window

Checklist:
- [ ] run isolated `keep` fit on the same cutoff/history
- [ ] run isolated NDLM-only `keep` post replay
- [ ] compare `drop` vs `keep` on:
  - mean identity
  - covariance ranges
  - CRPS input-health
  - forecast-window quantiles
- [ ] confirm the only intended differences are transfer-related

Exit gate:
- `drop` and `keep` both pass the NDLM contract

#### NDLM contract checklist
##### Fit-side contract
- [ ] no NaN/Inf in saved NDLM fit outputs
- [ ] exported covariance arrays have the expected dimensions
- [ ] PSD diagnostics pass for every exported slice
- [ ] latent ranges are finite and bounded to plausible magnitude

##### Reconstruction contract
- [ ] USGS mean reconstruction identity passes
- [ ] USGS variance construction is explicit and consistent with the chosen covariance regime
- [ ] saved Gaussian quantiles are derived from the saved mean/variance, not from an incompatible latent object

##### Post / scoring contract
- [ ] NDLM-only replay completes
- [ ] CRPS input-health has `fail_rows = 0`
- [ ] CRPS magnitude is in the same rough order as the plausible families, not `1e3+` while observations are on the usual scale
- [ ] forecast-window plot is visually coherent

#### What not to do
1. Do not use near-1 discount factors as the main correctness proof.
2. Do not patch `keep` first.
3. Do not resume batch production before `drop` and `keep` both pass the NDLM contract.
4. Do not delete repair artifacts during NDLM debugging.

### Command Blocks (repair-mode templates)
#### Fit-only targeted run template
```bash
export CLEANUP_RDATA_AFTER_POST=0
Rscript --vanilla scripts/unified_run.R --config <repair_fit_config.yaml>
```

Target config requirements:
```yaml
run:
  run_id: "<new_repair_run_id>"
  run_root: "repro/runs"
  repro_mode: "strict"

stages:
  forecats: true
  data_prep_shared: true
  fit: true
  post: false
  validate: true
  report: true

models:
  run_exdqlm_multivar: <true_or_false>
  run_exdqlm_univar: <true_or_false>
  run_ndlm_main: <true_or_false>
  run_ndlm_univar: <true_or_false>

dates:
  cutoff_date: "2021-01-23"
  data_start: "2010-01-01"

fit:
  quantiles: [0.05, 0.50, 0.95]   # triage set for broken quantile families
```

#### Post-only replay template
```bash
export CLEANUP_RDATA_AFTER_POST=0
Rscript --vanilla scripts/unified_run.R --config <repair_post_config.yaml>
```

Target config requirements:
```yaml
stages:
  forecats: false
  data_prep_shared: false
  fit: false
  post: true
  validate: true
  report: true

inputs:
  post:
    use_fit_outputs_from_run: true
    source_run_id: "<repair_fit_run_id>"
```

#### Keep artifacts during repair
```bash
export CLEANUP_RDATA_AFTER_POST=0
```

#### Delete repair artifacts only after closure
```bash
find repro/runs/<repair_run_id> -name '*.RData' -print
```

### Practical next move
#### Start with `R1 + R2(drop)` on the frozen `2021-01-23` fixture
Reason:
- multivariate NDLM `drop` is the cleanest first isolation target:
  - no transfer in forecast window
  - one of the clearly broken CRPS rows
  - easier mean-identity contract than `keep`
- and using the frozen completed artifact first avoids unnecessary refits during diagnosis

Then proceed immediately to:
- `R2(keep)`
- `R3(exdqlm_univar)`
- `R3(dqlm_univar_al)`

### Notes for reintegration
- do not resume automated batch production until targeted repair closure is documented here with exact run IDs and evidence
- keep all repair runs out of the previous production batch lineage
- once the suspect families pass, the main workflow should be rerun first on one cutoff only before any multi-cutoff restart
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

Status: **PASS (after one targeted rerun on 20221225)**

Checklist:
- [x] Generate per-cutoff configs from known-good Phase I template.
- [x] Run sequentially to isolate failures.
- [x] Verify all hard gates per run.

Evidence:
- Initial sequential runs:
  - `dev_al_phaseJ3_mini_20210123` -> pass
  - `dev_al_phaseJ3_mini_20211112` -> pass
  - `dev_al_phaseJ3_mini_20221225` -> **fit fail** (`ndlm_univar.new_theta.sC.psd`, sampled slice `2599`, min eig `-3.4024558e-10`)
- Root-cause fix for 20221225 fail:
  - Added explicit covariance-array hardening in `ndlm_univar` export path before sampling/serialization:
    - `R/unified/families/ndlm_univar/03_filter_forecast_fit.R`
  - Added unit regression for hardening:
    - `tests/testthat/test_ndlm_univar_wh_recursions.R`
  - Targeted tests pass:
    - `test_ndlm_univar_wh_recursions.R`
    - `test_fit_diagnostics_psd_scan.R`
- Rerun after fix:
  - `dev_al_phaseJ3_mini_20221225_v2` -> pass
  - diagnostics pass:
    - `repro/runs/dev_al_phaseJ3_mini_20221225_v2/fit/diagnostics/ndlm_univar/ndlm_univar_diagnostics.yaml`
    - `repro/runs/dev_al_phaseJ3_mini_20221225_v2/fit/diagnostics/ndlm_main/ndlm_main_diagnostics.yaml`
- Full post replay for CRPS/input-health gates:
  - `dev_al_phaseJ3_post_replay_20210123` -> pass
  - `dev_al_phaseJ3_post_replay_20211112` -> pass
  - `dev_al_phaseJ3_post_replay_20221225` -> pass
- Consolidated gate log:
  - `repro/hardening_logs/J3_gate_matrix_final_20260323T224036Z.log`
  - For all 3 cutoffs: `G1`, `G2`, `G3`, `G4` pass.

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
  fit_run="dev_al_phaseJ3_mini_${cut}"
  if [ "$cut" = "20221225" ]; then fit_run="dev_al_phaseJ3_mini_20221225_v2"; fi
  post_run="dev_al_phaseJ3_post_replay_${cut}"
  fit_root="repro/runs/${fit_run}"
  post_root="repro/runs/${post_run}"
  echo "=== cutoff ${cut} ==="
  sed -n '24,54p' "${fit_root}/run_manifest.yaml"
  sed -n '24,54p' "${post_root}/run_manifest.yaml"
  rg -n "status: fail" "${fit_root}/run_manifest.yaml" && echo "FAIL: fit stage status"
  rg -n "status: fail" "${post_root}/run_manifest.yaml" && echo "FAIL: post replay stage status"
  crps="${post_root}/post/outputs/${post_run}/tables/crps_forecast_summary.csv"
  rg -n "ndlm_univar_synth_keep|ndlm_main_synth_keep|dqlm_univar_al_synth|dqlm_multivar_al_synth_drop" "$crps"
done
```

### Phase J4 — Production Matrix Launch (After J3 PASS)
Status: **PENDING (J3 gates cleared; launch deferred until user authorizes full production batch)**

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
Status: **PASS (J0-J3 closure documented with exact run/log evidence)**

Checklist:
- [x] Record PASS/FAIL for each J-phase.
- [x] Record exact run IDs, commands, artifact paths.
- [x] Add unresolved risks and production recommendation.

Command block:
```bash
cd /data/muscat_data/jaguir26/project1_ucsc_phd
git rev-parse --short HEAD
date -u
```

## Operations Addendum (2026-03-23): `.RData` Cleanup + Gap #2 Closure Plan
### Cleanup execution evidence (completed)
Objective:
- reclaim disk by deleting recent run-scoped `.RData` artifacts and enforce auto-cleanup on future runs.

Execution:
- Deleted `.RData` files under `repro/runs/` modified in the last 48 hours.
- Cleanup summary log:
  - `repro/hardening_logs/rdata_recent_cleanup_20260323T230301Z.log`
  - `count_before=64`
  - `bytes_before=16700693700`
  - `count_after=0`
  - `bytes_after=0`
- Detailed path lists:
  - deleted candidates: `repro/hardening_logs/rdata_recent_candidates_20260323T230301Z.txt`
  - deleted records: `repro/hardening_logs/rdata_recent_deleted_20260323T230301Z.txt`
  - post-cleanup residual check: `repro/hardening_logs/rdata_recent_remaining_20260323T230301Z.txt`

Auto-cleanup policy for all next runs:
- set `CLEANUP_RDATA_AFTER_POST=1` when invoking `scripts/unified_run.R`.
- keep this enabled for smoke, hardening, and production batches.
- note: post replay from a fit run requires fit `.RData`; if replay is needed, use a no-cleanup fit run or replay immediately before cleanup.

### Remaining validation gap (#2) closure plan
Gap:
- #2 multivariate NDLM `drop` (transfer inactive in forecast window) lacks explicit hardening-proof run evidence in this campaign.

#### Phase K1 — Single-cutoff hardening smoke for NDLM main `drop`
Status: **PASS**

Checklist:
- [x] Clone known-good hardening smoke config (`al_phaseJ2_hardening_smoke_20260323_v6.yaml`).
- [x] Set `models.ndlm_main.forecast_transfer_mode: drop`.
- [x] Keep strict diagnostics (`full_slice_psd: true`, fail-fast enabled).
- [x] Run with auto `.RData` cleanup enabled.
- [x] Verify evidence:
  - `ndlm_theory_summary.log` has `forecast_transfer_mode=drop` and `transfer_active_forecast_window=false`.
  - `fit/diagnostics/ndlm_main/ndlm_main_diagnostics.yaml` status pass.
  - CRPS summary includes `ndlm_main_synth_drop`.

Execution notes:
- Initial run:
  - config: `config/unified_runs/al_phaseK1_ndlm_drop_smoke_20260323.yaml`
  - run: `repro/runs/dev_al_phaseK1_ndlm_drop_smoke_20260323`
  - result: `fit/post/report` pass, `.RData` cleanup pass, but `post.smoke_fast=yes` so CRPS tables were intentionally absent.
- Full-post closure rerun:
  - config: `config/unified_runs/al_phaseK1_ndlm_drop_smoke_20260323_v2.yaml`
  - run: `repro/runs/dev_al_phaseK1_ndlm_drop_smoke_20260323_v2`
  - result: `data_prep_shared=pass`, `fit=pass`, `post=pass`, `report=pass` in `run_manifest.yaml`.

Evidence:
- Stage status:
  - `repro/runs/dev_al_phaseK1_ndlm_drop_smoke_20260323_v2/run_manifest.yaml`
- NDLM drop markers:
  - `repro/runs/dev_al_phaseK1_ndlm_drop_smoke_20260323_v2/fit/ndlm_main/logs/ndlm_theory_summary.log`
  - contains:
    - `forecast_transfer_mode=drop`
    - `transfer_active_forecast_window=false`
- Strict diagnostics:
  - `repro/runs/dev_al_phaseK1_ndlm_drop_smoke_20260323_v2/fit/diagnostics/ndlm_main/ndlm_main_diagnostics.yaml`
  - `status: pass`
- CRPS table proof:
  - `repro/runs/dev_al_phaseK1_ndlm_drop_smoke_20260323_v2/post/outputs/dev_al_phaseK1_ndlm_drop_smoke_20260323_v2/tables/crps_forecast_summary.csv`
  - includes `ndlm_main_synth_drop`
- CRPS input-health proof:
  - `repro/runs/dev_al_phaseK1_ndlm_drop_smoke_20260323_v2/post/outputs/dev_al_phaseK1_ndlm_drop_smoke_20260323_v2/tables/crps_input_health.csv`
  - `fail_rows=0`
- Auto `.RData` cleanup proof:
  - `repro/runs/dev_al_phaseK1_ndlm_drop_smoke_20260323_v2` contains `0` `.RData` files after completion.

Command block:
```bash
cd /data/muscat_data/jaguir26/project1_ucsc_phd
Rscript --vanilla - <<'RS'
library(yaml)
src <- "config/unified_runs/al_phaseJ2_hardening_smoke_20260323_v6.yaml"
dst <- "config/unified_runs/al_phaseK1_ndlm_drop_smoke_20260323.yaml"
cfg <- read_yaml(src)
cfg$run$run_id <- "dev_al_phaseK1_ndlm_drop_smoke_20260323"
cfg$models$ndlm_main$forecast_transfer_mode <- "drop"
write_yaml(cfg, dst)
RS

CLEANUP_RDATA_AFTER_POST=1 \
Rscript --vanilla scripts/unified_run.R \
  --config config/unified_runs/al_phaseK1_ndlm_drop_smoke_20260323.yaml
```

Command block (full-post closure rerun):
```bash
cd /data/muscat_data/jaguir26/project1_ucsc_phd
Rscript --vanilla - <<'RS'
library(yaml)
src <- "config/unified_runs/al_phaseK1_ndlm_drop_smoke_20260323.yaml"
dst <- "config/unified_runs/al_phaseK1_ndlm_drop_smoke_20260323_v2.yaml"
cfg <- read_yaml(src)
cfg$run$run_id <- "dev_al_phaseK1_ndlm_drop_smoke_20260323_v2"
cfg$post$smoke_fast <- FALSE
write_yaml(cfg, dst)
RS

scripts/run_unified_with_cleanup.sh \
  --config config/unified_runs/al_phaseK1_ndlm_drop_smoke_20260323_v2.yaml
```

#### Phase K2 — Mini-matrix hardening proof for #2 (3 cutoffs, sequential)
Cutoffs:
- `20210123`, `20211112`, `20221225`

Checklist:
- [x] Generate one K2 config per cutoff from K1 config.
- [x] Sequential execution only for fresh runs (`20210123`, `20211112`); reuse the already validated full-post `20221225` lane only after explicit config-equivalence check.
- [x] Gate each run:
  - [x] G1: NDLM diagnostics pass (full-slice PSD policy).
  - [x] G2: no `status=fail` rows in CRPS input-health exports.
  - [x] G3: `ndlm_main_synth_drop` present in CRPS summary.
  - [x] G4: manifest `fit/post/report` stage pass.
- [x] Consolidate results in `repro/hardening_logs/K2_gate_matrix_<timestamp>.log`.

Status:
- PASS

Run IDs:
- `20210123`: `dev_al_phaseK2_mini_20210123`
- `20211112`: `dev_al_phaseK2_mini_20211112`
- `20221225`: reused `dev_al_phaseK1_ndlm_drop_smoke_20260323_v2`

Command block (fresh runs):
```bash
cd /data/muscat_data/jaguir26/project1_ucsc_phd
scripts/run_unified_with_cleanup.sh \
  --config config/unified_runs/al_phaseK2_mini_20210123.yaml

scripts/run_unified_with_cleanup.sh \
  --config config/unified_runs/al_phaseK2_mini_20211112.yaml
```

Command block (20221225 reuse-equivalence check):
```bash
cd /data/muscat_data/jaguir26/project1_ucsc_phd
Rscript --vanilla - <<'RS'
library(yaml)
k1 <- read_yaml("config/unified_runs/al_phaseK1_ndlm_drop_smoke_20260323_v2.yaml")
k2 <- read_yaml("config/unified_runs/al_phaseK2_mini_20221225.yaml")
vals <- c(
  identical(k1$dates$cutoff_date, k2$dates$cutoff_date),
  identical(k1$models$exdqlm_multivar$likelihood_mode, k2$models$exdqlm_multivar$likelihood_mode),
  identical(k1$models$exdqlm_multivar$forecast_transfer_mode, k2$models$exdqlm_multivar$forecast_transfer_mode),
  identical(k1$models$exdqlm_univar$likelihood_mode, k2$models$exdqlm_univar$likelihood_mode),
  identical(k1$models$ndlm_main$forecast_transfer_mode, k2$models$ndlm_main$forecast_transfer_mode),
  identical(k1$models$ndlm_univar$forecast_transfer_mode, k2$models$ndlm_univar$forecast_transfer_mode),
  identical(k1$post$smoke_fast, k2$post$smoke_fast),
  identical(k1$post$export_tables, k2$post$export_tables),
  identical(k1$post$crps_input_health$enabled, k2$post$crps_input_health$enabled),
  identical(k1$post$crps_input_health$fail_fast, k2$post$crps_input_health$fail_fast),
  identical(k1$fit$diagnostics$enabled, k2$fit$diagnostics$enabled),
  identical(k1$fit$diagnostics$fail_fast, k2$fit$diagnostics$fail_fast),
  identical(k1$fit$diagnostics$full_slice_psd, k2$fit$diagnostics$full_slice_psd)
)
stopifnot(all(vals))
RS
```

Evidence:
- Consolidated gate log: `repro/hardening_logs/K2_gate_matrix_20260324T004716Z.log`
- `20210123` manifest PASS: `repro/runs/dev_al_phaseK2_mini_20210123/run_manifest.yaml`
- `20210123` NDLM drop proof: `repro/runs/dev_al_phaseK2_mini_20210123/fit/ndlm_main/logs/ndlm_theory_summary.log`
- `20210123` diagnostics PASS: `repro/runs/dev_al_phaseK2_mini_20210123/fit/diagnostics/ndlm_main/ndlm_main_diagnostics.yaml`
- `20210123` CRPS summary: `repro/runs/dev_al_phaseK2_mini_20210123/post/outputs/dev_al_phaseK2_mini_20210123/tables/crps_forecast_summary.csv`
- `20210123` CRPS input-health: `repro/runs/dev_al_phaseK2_mini_20210123/post/outputs/dev_al_phaseK2_mini_20210123/tables/crps_input_health.csv`
- `20211112` manifest PASS: `repro/runs/dev_al_phaseK2_mini_20211112/run_manifest.yaml`
- `20211112` NDLM drop proof: `repro/runs/dev_al_phaseK2_mini_20211112/fit/ndlm_main/logs/ndlm_theory_summary.log`
- `20211112` diagnostics PASS: `repro/runs/dev_al_phaseK2_mini_20211112/fit/diagnostics/ndlm_main/ndlm_main_diagnostics.yaml`
- `20211112` CRPS summary: `repro/runs/dev_al_phaseK2_mini_20211112/post/outputs/dev_al_phaseK2_mini_20211112/tables/crps_forecast_summary.csv`
- `20211112` CRPS input-health: `repro/runs/dev_al_phaseK2_mini_20211112/post/outputs/dev_al_phaseK2_mini_20211112/tables/crps_input_health.csv`
- `20221225` reused manifest PASS: `repro/runs/dev_al_phaseK1_ndlm_drop_smoke_20260323_v2/run_manifest.yaml`
- `20221225` reused NDLM drop proof: `repro/runs/dev_al_phaseK1_ndlm_drop_smoke_20260323_v2/fit/ndlm_main/logs/ndlm_theory_summary.log`
- `20221225` reused diagnostics PASS: `repro/runs/dev_al_phaseK1_ndlm_drop_smoke_20260323_v2/fit/diagnostics/ndlm_main/ndlm_main_diagnostics.yaml`
- `20221225` reused CRPS summary: `repro/runs/dev_al_phaseK1_ndlm_drop_smoke_20260323_v2/post/outputs/dev_al_phaseK1_ndlm_drop_smoke_20260323_v2/tables/crps_forecast_summary.csv`
- `20221225` reused CRPS input-health: `repro/runs/dev_al_phaseK1_ndlm_drop_smoke_20260323_v2/post/outputs/dev_al_phaseK1_ndlm_drop_smoke_20260323_v2/tables/crps_input_health.csv`

#### Phase K3 — Production cutoff batches (controlled launch)
Batching strategy:
- Batch A: `20210123`, `20211112`
- Batch B: `20211221`, `20220511`
- Batch C: `20221225`

Per-cutoff run lanes to cover all 9 benchmark models with minimal redundancy:
- Lane L1 (`AL + NDLM keep`):
  - univar DQLM AL
  - multivar DQLM AL drop/keep
  - NDLM main keep
  - NDLM univar keep
- Lane L2 (`exAL + NDLM drop`):
  - univar exDQLM
  - multivar exDQLM drop/keep
  - NDLM main drop

Operational rules:
- [x] `fit.parallel.mode=one_core_per_model`
- [x] strict diagnostics + CRPS input-health fail-fast
- [x] `CLEANUP_RDATA_AFTER_POST=1`
- [x] run cutoff-by-cutoff within each batch, lane-by-lane
- [x] gate check immediately after each run
- [x] append gate outcomes to `repro/hardening_logs/J4_batch_monitor_<timestamp>.log`

Batch A blocker identified after first production lane:
- `prod_phaseK3_batchA_20210123_l1_20260324` completed `fit/post/report`, but gate `G3_required_model_ids` failed because canonical `crps_forecast_summary.csv` omitted `dqlm_multivar_al_synth_keep` even though the keep replay artifacts existed in suffixed exports.
- Root cause: dual-mode post wrote valid `*_keep.csv` CRPS tables, but did not merge them back into the canonical unsuffixed CRPS tables that Batch A gates read.

Stabilization / forward path:
- Root fix implemented in `R/unified/stages/stage_post.R`:
  - source post table helpers,
  - preserve mode-specific `*_keep.csv` exports,
  - merge `drop` + `keep` CRPS / CRPS-input-health tables into canonical unsuffixed exports,
  - refresh `posterior_table_exports_manifest.csv` so canonical and mode-specific files are both represented.
- Validation smoke:
  - config: `config/unified_runs/dev_phaseK3_dualmode_post_merge_smoke_20210123_20260324.yaml`
  - run: `repro/runs/dev_phaseK3_dualmode_post_merge_smoke_20210123_20260324`
  - result: PASS
  - canonical `crps_forecast_summary.csv` now includes:
    - `dqlm_multivar_al_synth_drop`
    - `dqlm_multivar_al_synth_keep`
    - `dqlm_univar_al_synth`
    - `ndlm_main_synth_keep`
    - `ndlm_univar_synth_keep`
  - `crps_input_health.csv` includes both multivar AL modes with `FAIL_ROWS=0`
  - manifest now includes both canonical and suffixed keep table files.
- Production rerun prepared:
  - fresh config: `config/unified_runs/prod_phaseK3_batchA_20210123_l1_fix1_20260324.yaml`
  - resume runner: `scripts/run_k3_batchA_resume_fix1_20260324.sh`

Immediate forward plan from current state:
- Objective: resume controlled production without reintroducing the original dual-mode post contract gap.
- Principle:
  - do not relaunch the whole batch blindly,
  - finish the live fixed `20210123 L1` rerun,
  - gate it against the canonical unsuffixed CRPS contract,
  - only then continue the remaining Batch A lanes under the same monitor log.
- Shared control utilities:
  - `scripts/gate_batch_run.R`
    - single source of truth for Batch A gate evaluation,
    - validates stage pass, diagnostics pass, required model IDs, CRPS input-health, NDLM mode contract, and `.RData` cleanup.
  - `scripts/run_k3_batchA_wait_fix1_then_continue_20260324.sh`
    - waits for `prod_phaseK3_batchA_20210123_l1_fix1_20260324`,
    - gates it with `scripts/gate_batch_run.R`,
    - on PASS, invokes `scripts/run_k3_batchA_continue_after_fix1_20260324.sh` using the same `BATCH_LOG`.
  - `scripts/run_k3_batchA_continue_after_fix1_20260324.sh`
    - sequentially runs:
      - `prod_phaseK3_batchA_20210123_l2_20260324`
      - `prod_phaseK3_batchA_20211112_l1_20260324`
      - `prod_phaseK3_batchA_20211112_l2_20260324`
    - appends a gate block after each completed run.

Execution checklist:
- [x] Implement shared gate helper `scripts/gate_batch_run.R`.
- [x] Refactor Batch A continuation runners to call the shared helper.
- [x] Validate the gate helper against the known failed original `20210123 L1` run and confirm expected `G3_required_model_ids=fail`.
- [x] Let `prod_phaseK3_batchA_20210123_l1_fix1_20260324` finish.
- [x] Gate `prod_phaseK3_batchA_20210123_l1_fix1_20260324` with the shared helper.
- [x] On PASS, continue remaining Batch A lanes automatically.
- [x] Review the consolidated Batch A monitor log.

Command block (automated handoff from live fix1 run to remaining Batch A lanes):
```bash
cd /data/muscat_data/jaguir26/project1_ucsc_phd
nohup scripts/run_k3_batchA_wait_fix1_then_continue_20260324.sh \
  > repro/hardening_logs/run_k3_batchA_wait_fix1_then_continue_20260324.launcher.log 2>&1 &
```

Command block (manual gate check for any completed Batch A run):
```bash
cd /data/muscat_data/jaguir26/project1_ucsc_phd
Rscript --vanilla scripts/gate_batch_run.R \
  /data/muscat_data/jaguir26/project1_ucsc_phd \
  config/unified_runs/prod_phaseK3_batchA_20210123_l1_fix1_20260324.yaml \
  repro/hardening_logs/prod_phaseK3_batchA_20210123_l1_fix1_20260324.launcher.log \
  repro/hardening_logs/manual_gate_check.log
```

Batch A final status:
- PASS
- consolidated monitor log:
  - `repro/hardening_logs/J4_batch_monitor_wait_fix1_then_continue_20260324T055944Z.log`
- final run/gate closure:
  - `20210123 L1 fix1`: `OVERALL=pass`
  - `20210123 L2`: `OVERALL=pass`
  - `20211112 L1`: `OVERALL=pass`
  - `20211112 L2`: `OVERALL=pass`

Phase K3 forward production automation:
- Batch B configs:
  - `config/unified_runs/prod_phaseK3_batchB_20211221_l1_20260324.yaml`
  - `config/unified_runs/prod_phaseK3_batchB_20211221_l2_20260324.yaml`
  - `config/unified_runs/prod_phaseK3_batchB_20220511_l1_20260324.yaml`
  - `config/unified_runs/prod_phaseK3_batchB_20220511_l2_20260324.yaml`
- Batch C configs:
  - `config/unified_runs/prod_phaseK3_batchC_20221225_l1_20260324.yaml`
  - `config/unified_runs/prod_phaseK3_batchC_20221225_l2_20260324.yaml`
- batch config builder:
  - `scripts/build_k3_batch_bc_configs.R`
- generic batch runner:
  - `scripts/run_k3_batch_sequence.sh`
- batch launchers:
  - `scripts/run_k3_batchB_20260324.sh`
  - `scripts/run_k3_batchC_20260324.sh`
  - `scripts/run_k3_batchB_then_C_20260324.sh`
- K4 merge launcher:
  - `scripts/run_k4_merge_after_production_20260324.sh`

Batch B execution plan:
- cutoff order:
  - `20211221 L1`
  - `20211221 L2`
  - `20220511 L1`
  - `20220511 L2`
- all runs inherit:
  - `one_core_per_model`
  - strict diagnostics
  - CRPS input-health fail-fast
  - `.RData` cleanup after `post`
  - shared gate contract via `scripts/gate_batch_run.R`

Batch C execution plan:
- cutoff order:
  - `20221225 L1`
  - `20221225 L2`
- Batch C auto-starts only if Batch B completes with all `OVERALL=pass`.
- K4 merge auto-starts only if Batch C completes with all `OVERALL=pass`.

Live execution status:
- Batch B -> Batch C -> K4 chain launched.
- shared monitor log:
  - `repro/hardening_logs/J4_batch_monitor_batchB_then_C_20260324T202506Z.log`
- live controller:
  - `scripts/run_k3_batchB_then_C_20260324.sh`
- current first active production run:
  - `prod_phaseK3_batchB_20211221_l1_20260324`
- current manifest snapshot at launch verification:
  - `repro/runs/prod_phaseK3_batchB_20211221_l1_20260324/run_manifest.yaml`
  - `data_prep_shared: pass`
  - `fit: pending`
  - `post: pending`
  - `report: pending`

Batch B incident note (`20220511 L1`):
- original failing run:
  - `prod_phaseK3_batchB_20220511_l1_20260324`
- failure class:
  - `post` stage failure in `R/environmetrics/40_figures.R`
  - failing diagnostic callsite: JSD computation for `new.theta.out_50_NDLM_synth$standard_forecast_errors`
- exact error:
  - `Error in dpik(x = x, level = nstage, gridsize = bgridsize) : scale estimate is zero for input data`
- root-cause finding:
  - the NDLM standardized forecast-error sample was finite and non-constant (`sd > 0`) but heavily tied, with `IQR = 0` and `MAD = 0`;
  - `ks::kde()` default bandwidth path (`hpi` -> `dpik`) failed on this tied sample even though the sample itself was valid;
  - this is a brittle post-diagnostic bandwidth-selection failure, not an NDLM fit instability.
- robust fix implemented:
  - `R/environmetrics/02_helpers_core.R`
  - `compute_jsd_to_standard_normal()` now uses explicit stable bandwidth selection:
    - univariate: deterministic `bw.nrd0`-based `h` with positive floor
    - multivariate: `ks::Hpi()` when valid, otherwise diagonal positive-definite fallback built from per-axis stable bandwidths
    - explicit PD repair / ridge on bandwidth matrices when needed
- regression coverage added:
  - `tests/testthat/test_ndlm_post_jsd.R`
  - new cases:
    - tied univariate sample with `IQR = 0`
    - exact constant univariate sample
    - multivariate sample with a degenerate axis
- validation in progress:
  - post-only replay run:
    - `prod_phaseK3_batchB_20220511_l1_post_replay_fix1_20260324`
  - resume controller waiting on replay pass, then auto-reruns remaining production:
    - `scripts/run_k3_batchB_resume_after_replay_fix1_20260325.sh`
    - queued production rerun config:
      - `config/unified_runs/prod_phaseK3_batchB_20220511_l1_fix1_20260325.yaml`
    - on replay pass, controller runs:
      - `20220511 L1 fix1`
      - `20220511 L2`
      - then `Batch C`
      - then `K4 merge`
  - shared batch log remains:
    - `repro/hardening_logs/J4_batch_monitor_batchB_then_C_20260324T202506Z.log`

Command block (auto-run Batch B, then Batch C on pass):
```bash
cd /data/muscat_data/jaguir26/project1_ucsc_phd
Rscript --vanilla scripts/build_k3_batch_bc_configs.R
nohup scripts/run_k3_batchB_then_C_20260324.sh \
  > repro/hardening_logs/run_k3_batchB_then_C_20260324.launcher.log 2>&1 &
```

Command block (Batch B only):
```bash
cd /data/muscat_data/jaguir26/project1_ucsc_phd
Rscript --vanilla scripts/build_k3_batch_bc_configs.R
scripts/run_k3_batchB_20260324.sh
```

Command block (Batch C only):
```bash
cd /data/muscat_data/jaguir26/project1_ucsc_phd
Rscript --vanilla scripts/build_k3_batch_bc_configs.R
scripts/run_k3_batchC_20260324.sh
```

#### Phase K4 — CRPS export merge for final benchmark table
Inputs:
- each run’s `post/outputs/<run_id>/tables/crps_forecast_summary*.csv`
- each run’s `post/outputs/<run_id>/tables/crps_forecast_per_time*.csv`

Checklist:
- [ ] stack summaries with metadata columns `run_id`, `cutoff`, `lane`.
- [ ] validate required model-id coverage across merged union:
  - `dqlm_univar_al_synth`
  - `dqlm_multivar_al_synth_drop`
  - `dqlm_multivar_al_synth_keep`
  - `ndlm_main_synth_drop`
  - `ndlm_main_synth_keep`
  - `ndlm_univar_synth_keep`
  - `exdqlm_univar_synth`
  - `exdqlm_multivar_synth_drop`
  - `exdqlm_multivar_synth_keep`
- [ ] export merged files to:
  - `exports/benchmark_crps/crps_summary_merged_<timestamp>.csv`
  - `exports/benchmark_crps/crps_per_time_merged_<timestamp>.csv`
- [ ] write merge manifest + coverage report in same folder.

Prepared merge utility:
- `scripts/merge_k4_benchmark_crps.R`
- automatic launcher:
  - `scripts/run_k4_merge_after_production_20260324.sh`
- intended use: auto-runs after Batch C passes so the full 5-cutoff production matrix is available.
- outputs:
  - merged summary
  - merged per-time
  - merged CRPS health
  - merged CRPS health per-time
  - coverage report
  - merge manifest

Command block (K4 merge after all production batches pass):
```bash
cd /data/muscat_data/jaguir26/project1_ucsc_phd
Rscript --vanilla scripts/merge_k4_benchmark_crps.R
```

## Changelog
- 2026-03-22: Created tracker with baseline audit, assumptions, risks, and phased plan.
- 2026-03-22: Updated tracker with completed implementation evidence for Phases A-D, partial Phase E, and Phase F replay-based PASS.
- 2026-03-22: Patched `OptimalModelSLexAL.r` to support AL collapse in legacy bridge with sigma-only Laplace-Delta optimization when `UNIV_LIKELIHOOD_MODE=al` (`gamma=0`, `s_t=0`), and validated via Phase B2 smoke run.
- 2026-03-23: Added NDLM stabilization controls and root-cause fix across R/C++ Kalman paths, sigma update safeguards, diagnostics counters, new NDLM tests, and validated Phase G NDLM keep smoke rerun PASS (`..._20260323_005054`).
- 2026-03-23: Added Phase H `ndlm_univar` family wiring, C++/R West-Harrison closed-form implementation integration, sampler/contract bug fixes, and validated smoke rerun PASS (`..._20260323_023419`).
- 2026-03-23: Added `tests/testthat/test_ndlm_univar_wh_recursions.R` for scalar WH recursion checks, backend parity checks, and sampler dimension/finite checks; test passes.
- 2026-03-23: Completed Phase I all-model smoke including `ndlm_univar` CRPS export validation (`dev_al_phaseI_allmodels_plus_ndlm_univar_crps_smoke_20260323`).
- 2026-03-24: Completed Phase K2 for model #2 (`ndlm_main` drop) using fresh full-post runs `dev_al_phaseK2_mini_20210123` and `dev_al_phaseK2_mini_20211112`, plus config-equivalent reuse of `dev_al_phaseK1_ndlm_drop_smoke_20260323_v2` for `20221225`; consolidated proof log `repro/hardening_logs/K2_gate_matrix_20260324T004716Z.log`, all gates pass, and `.RData` cleanup verified.
- 2026-03-23: Completed J1/J2 hardening closure:
  - strengthened NDLM fit-stage covariance hardening (strict floor enforcement + diagnostic before/after logging),
  - cleared strict full-slice PSD gate in `dev_al_phaseJ2_hardening_smoke_20260323_v6`,
  - fixed full-post replay failure in `normalize_theta_time_sample()` for reduced draw counts,
  - validated full post replay pass with CRPS + CRPS input-health exports in `dev_al_phaseJ2_hardening_post_replay_20260323_v7`.
- 2026-03-23: Completed Phase J3 mini-matrix hard-gate closure:
  - ran `dev_al_phaseJ3_mini_20210123` and `dev_al_phaseJ3_mini_20211112` PASS;
  - isolated `dev_al_phaseJ3_mini_20221225` fail (`ndlm_univar.new_theta.sC.psd`, min eig `-3.4024558e-10`);
  - implemented `ndlm_univar` export covariance-array hardening in `R/unified/families/ndlm_univar/03_filter_forecast_fit.R` and added regression test in `tests/testthat/test_ndlm_univar_wh_recursions.R`;
  - reran `dev_al_phaseJ3_mini_20221225_v2` PASS, then full post replays (`dev_al_phaseJ3_post_replay_20210123`, `..._20211112`, `..._20221225`) PASS with CRPS/input-health exports;
  - consolidated gates (`G1/G2/G3/G4`) pass across all three cutoffs in `repro/hardening_logs/J3_gate_matrix_final_20260323T224036Z.log`.
- 2026-03-23: Performed recent `.RData` cleanup for disk hygiene (`last 48h`) with audit logs:
  - `repro/hardening_logs/rdata_recent_cleanup_20260323T230301Z.log`
  - deleted `64` files (`16.70 GB`) and verified `count_after=0`.
- 2026-03-23: Added execution helper `scripts/run_unified_with_cleanup.sh` to enforce `CLEANUP_RDATA_AFTER_POST=1` for future runs.
- 2026-03-23: Completed K1 gap-closure proof for model #2 (`ndlm_main drop`):
  - initial smoke run `dev_al_phaseK1_ndlm_drop_smoke_20260323` passed fit/post/report and `.RData` cleanup,
  - full-post rerun `dev_al_phaseK1_ndlm_drop_smoke_20260323_v2` passed all stages, exported CRPS tables with `ndlm_main_synth_drop`, recorded `fail_rows=0` in `crps_input_health.csv`, and finished with `0` residual `.RData` files.
- 2026-03-24: Fixed Batch A root-cause post contract bug for dual-mode multivariate synthesis:
  - implemented canonical CRPS/health merge in `R/unified/stages/stage_post.R` so dual-mode runs retain `*_keep.csv` provenance files while also rewriting unsuffixed canonical CRPS tables with the union of `drop` + `keep`,
  - validated in `dev_phaseK3_dualmode_post_merge_smoke_20210123_20260324` (`fit/post/report` PASS),
  - canonical CRPS summary now includes `dqlm_multivar_al_synth_keep`,
  - CRPS input-health remains clean (`FAIL_ROWS=0`),
  - table manifest now lists both canonical and suffixed keep exports,
  - prepared fresh production rerun config `prod_phaseK3_batchA_20210123_l1_fix1_20260324` and resume runner `scripts/run_k3_batchA_resume_fix1_20260324.sh`.
- 2026-03-24: Added shared Batch A gate/control utilities:
  - `scripts/gate_batch_run.R` is now the reusable gate evaluator for production lane completion,
  - `scripts/run_k3_batchA_wait_fix1_then_continue_20260324.sh` now waits on the live `20210123 L1 fix1` rerun, gates it, and hands off to the remaining Batch A lanes,
  - `scripts/run_k3_batchA_resume_fix1_20260324.sh` and `scripts/run_k3_batchA_continue_after_fix1_20260324.sh` now use the shared gate helper and preserve a shared `BATCH_LOG_OVERRIDE` log instead of clobbering it.
- 2026-03-24: Closed Batch A production:
  - consolidated log `repro/hardening_logs/J4_batch_monitor_wait_fix1_then_continue_20260324T055944Z.log`,
  - `20210123 L1 fix1`, `20210123 L2`, `20211112 L1`, and `20211112 L2` all completed `fit/post/report` and gated `OVERALL=pass`,
  - dual-mode canonical CRPS export contract now holds in production.
- 2026-03-24: Added Batch B/C production automation:
  - generated six production configs for `20211221`, `20220511`, and `20221225` via `scripts/build_k3_batch_bc_configs.R`,
  - added generic runner `scripts/run_k3_batch_sequence.sh`,
  - added `scripts/run_k3_batchB_20260324.sh`, `scripts/run_k3_batchC_20260324.sh`, and chained launcher `scripts/run_k3_batchB_then_C_20260324.sh`,
  - added K4 merge utility `scripts/merge_k4_benchmark_crps.R` and launcher `scripts/run_k4_merge_after_production_20260324.sh` for final benchmark export once all production batches pass.
- 2026-03-24: Launched the chained production controller:
  - Batch B -> Batch C -> K4 merge now runs through a single handoff path,
  - shared monitor log: `repro/hardening_logs/J4_batch_monitor_batchB_then_C_20260324T202506Z.log`,
  - first live run: `prod_phaseK3_batchB_20211221_l1_20260324`,
  - manifest at launch verification showed `data_prep_shared: pass` and `fit/post/report` pending as expected for an active Batch B start.
- 2026-03-24: Investigated and fixed the `20220511 L1` Batch B post failure:
  - isolated failure to JSD/KDE diagnostics in `R/environmetrics/40_figures.R` for `new.theta.out_50_NDLM_synth$standard_forecast_errors`,
  - confirmed the NDLM sample was valid but heavily tied (`sd > 0`, `IQR = 0`, `MAD = 0`), so the crash originated in `ks::kde()` default bandwidth selection rather than fit instability,
  - hardened `compute_jsd_to_standard_normal()` in `R/environmetrics/02_helpers_core.R` with explicit bandwidth selection and multivariate positive-definite fallback,
  - added regression coverage in `tests/testthat/test_ndlm_post_jsd.R`,
  - created post replay validation run `prod_phaseK3_batchB_20220511_l1_post_replay_fix1_20260324`,
  - prepared and launched the auto-resume controller `scripts/run_k3_batchB_resume_after_replay_fix1_20260325.sh` so Batch B resumes from `20220511 L1 fix1` and then hands off to Batch C and K4 once replay validation passes.
- 2026-03-25: Began focused benchmark-integrity repair runs on frozen `2021-01-23` fixtures:
  - implemented NDLM forecast-member extraction in `R/unified/families/shared_input_helpers.R` and `R/unified/families/ndlm_main/01_inputs.R`,
  - updated `R/unified/families/ndlm_main/03_vb_updates.R` so future observation sequences use all active forecast ensemble members and export member-count diagnostics,
  - added/extended targeted tests:
    - `tests/testthat/test_ndlm_main_inputs.R`
    - `tests/testthat/test_ndlm_ragged_horizon_builder.R`
  - reran `repair_r1_ndlm_main_drop_20210123_20260324_rerun_20260324_232509`:
    - `fit=pass`, `post=fail`
    - fit improvement evidence: `sigma=23.84804930`
    - remaining failure: `forecast_mean_draws_loglog1p` range `[-36035.3, 38917.1]` and NDLM-only post overflow on `38912.135805`.
- 2026-03-25: Completed the univariate exAL isolated post-route repair:
  - added dedicated univariate-only post module `R/environmetrics/40_figures_univar_only.R`,
  - updated `R/unified/post_module_plan.R` and `R/unified/post_artifact_contract.R` for univariate-only full repair-mode post,
  - added run-scoped univariate synthesis cache exports in `R/environmetrics/30_univariate_and_misc.R`,
  - extended tests:
    - `tests/testthat/test_post_module_plan.R`
    - `tests/testthat/test_post_artifact_contract.R`
  - reran `repair_r1_univar_exal_triage_20210123_20260324_rerun_20260324_233729`:
    - `fit=pass`, `post=pass`, `report=pass`
    - `crps_forecast_summary.csv`: `mean_crps = 0.18037037280820534`
    - `crps_input_health.csv`: `status = pass`
    - remaining defect: quantile-order pathology persists (`56000 / 56000` sample-path crossings; median-curve crossings at all `28` forecast leads).
- 2026-03-25: Narrowed the remaining repair program:
  - confirmed current `ndlm_main` focused repair runs use `implementation_mode: theory_aligned`, while legacy bridge remains available through `scripts/run_DISC_Optimal_Synth_Ranges_NDLM.R`,
  - confirmed NDLM derivations allow either inverse-Wishart-updated covariance blocks or discount-fixed covariance blocks,
  - confirmed exDQLM derivation notes that current `project1` forecast-period covariance updates use a shrinkage plug-in rather than the inverse-Wishart CAVI update,
  - set the next investigation focus to:
    - `ndlm_main drop` legacy-vs-theory covariance parity,
    - `exdqlm_univar` quantile-coherence repair,
  - recorded that the theory/docs clone `/data/muscat_data/jaguir26/exDQLM---Ensemble` is not the right source reference for package implementation parity.
- 2026-03-25: Implemented P5/P6/P7 univariate repair harness:
  - added repo-anchored univariate synthesis helpers in `R/environmetrics/02_helpers_core.R`:
    - `post_quantile_curve_from_sample_cube()`
    - `post_quantile_curve_crossing_summary()`
    - `post_exdqlm_synthesize_from_sample_cube()`
  - refactored `R/environmetrics/30_univariate_and_misc.R` to rebuild isolated legacy univariate forecast/historical cubes from only the actually fitted quantiles and synthesize them through `exdqlm::exdqlm_synthesize_from_draws()`,
  - replaced `R/environmetrics/40_figures_univar_only.R` with a dedicated univariate repair post module that exports:
    - forecast-window quantile table
    - forecast-window quantile plot
    - curve-level crossing summaries
    - CRPS + CRPS input-health tables,
  - added focused regression coverage:
    - `tests/testthat/test_univar_quantile_synthesis_repair.R`
      - helper extraction
      - curve-crossing detection
      - monotone synthesis repair
      - direct equivalence to the local source repo `/data/muscat_data/jaguir26/exdqlm/R/exdqlm_synthesize_from_draws.R`,
    - reran:
      - `tests/testthat/test_univar_quantile_synthesis_repair.R` -> pass
      - `tests/testthat/test_post_artifact_contract.R` -> pass
      - `tests/testthat/test_post_module_plan.R` -> pass
  - added focused univariate repair tooling:
    - `scripts/build_univar_repair_configs.R`
    - `scripts/gate_univar_repair_run.R`
    - `scripts/run_univar_repair_p5_p7_20260325.sh`
  - confirmed local source repo availability:
    - `/data/muscat_data/jaguir26/exdqlm`
    - local branch `cransub/0.4.0`
  - launched focused run sequence without cleanup:
    - `repair_p5_univar_exal_triage_20210123_20260325`
    - `repair_p6_univar_exal_full7_20210123_20260325`
    - `repair_p7_univar_al_triage_20210123_20260325`
    - `repair_p7_univar_al_full7_20210123_20260325`
    - shared log: `repro/hardening_logs/univar_repair_p5_p7_20260325T194215Z.log`
  - current live state at tracker update:
    - `repair_p5_univar_exal_triage_20210123_20260325`
    - `data_prep_shared=pass`
    - `fit` active on `q=0.95`
    - no `.RData` cleanup enabled by design.
- 2026-03-25: Completed P5/P6/P7 univariate repair execution and validation:
  - fixed the remaining univariate-only artifact/gate defects:
    - `R/unified/post_artifact_contract.R`
      - isolated univariate repair outputs now satisfy the post contract without requiring legacy fit/trace figures,
    - `scripts/gate_univar_repair_run.R`
      - post-only replay runs now accept `data_prep_shared/fit/report = skip` with `post = pass`,
    - `R/environmetrics/40_figures_univar_only.R`
      - corrected `[quantile x horizon]` table flattening order for `univar_forecast_window_quantiles.csv`,
    - `R/environmetrics/02_helpers_core.R`
      - added `post_quantile_curve_long_values()` and regression coverage for table ordering,
  - reran targeted regression tests after the final fixes:
    - `tests/testthat/test_univar_quantile_synthesis_repair.R` -> pass
    - `tests/testthat/test_post_artifact_contract.R` -> pass
    - `tests/testthat/test_post_module_plan.R` -> pass
  - final P5 evidence (`exAL` triage replay, post-only on preserved fit outputs):
    - run: `repair_p5_univar_exal_triage_20210123_20260325_post_replay_fix3`
    - gate: `OVERALL=pass`
    - CRPS: `mean_crps = 0.1864799257`, `median_crps = 0.0967645875`, `n_valid = 28`
    - monotonicity: `synth_anchor_crossings = 0`, `synth_empirical_crossings = 0`, `raw_crossing_share = 0`
  - final P6 evidence (`exAL` full7):
    - run: `repair_p6_univar_exal_full7_20210123_20260325`
    - gate: `OVERALL=pass`
    - stages: `data_prep_shared=pass`, `fit=pass`, `post=pass`, `report=pass`
    - CRPS: `mean_crps = 0.1921359219`, `median_crps = 0.0979350108`, `n_valid = 28`
    - monotonicity: `synth_anchor_crossings = 0`, `synth_empirical_crossings = 0`, `raw_crossing_share = 0`
  - final P7 evidence (`AL` triage):
    - run: `repair_p7_univar_al_triage_20210123_20260325`
    - gate: `OVERALL=pass`
    - CRPS: `mean_crps = 0.1524967519`, `median_crps = 0.0811790647`, `n_valid = 28`
    - monotonicity: `synth_anchor_crossings = 0`, `synth_empirical_crossings = 0`, `raw_crossing_share = 0`
  - final P7 evidence (`AL` full7):
    - run: `repair_p7_univar_al_full7_20210123_20260325`
    - gate: `OVERALL=pass`
    - stages: `data_prep_shared=pass`, `fit=pass`, `post=pass`, `report=pass`
    - CRPS: `mean_crps = 0.1728766418`, `median_crps = 0.0922789608`, `n_valid = 28`
    - monotonicity: `synth_anchor_crossings = 0`, `synth_empirical_crossings = 0`, `raw_crossing_share = 0.107143`
  - interpretation:
    - the univariate repair scope is now closed for both `exAL` and `AL` on the isolated single-cutoff harness,
    - synthesized curves are now monotone and CRPS is back to a plausible scale for both likelihood modes,
    - residual raw-model crossing in `AL` full7 is no longer a blocker because the benchmark contract is on synthesized outputs; it should still be documented and visualized in the next suspect-only integration step.
- 2026-03-26: Rebased the repair tracker around the true remaining blocker:
  - updated the model-family integrity snapshot to mark:
    - `exdqlm_univar_synth` as repaired on the isolated harness and pending reintegration,
    - `dqlm_univar_al_synth` as repaired on the isolated harness and pending reintegration,
    - `ndlm_main drop/keep` as the only remaining untrusted benchmark rows,
  - updated the standardized repair checklist to close the `R3` univariate items at the synthesized-output benchmark level,
  - rewrote the recommended execution order so it now starts with NDLM-only work:
    - `ndlm_main drop`
    - `ndlm_main keep`
    - `ndlm_univar` verification
    - multivariate identity hardening
    - suspect-only reintegration
    - all-9-model reintegration,
  - added a dedicated `NDLM Next-Step Program (Post-P5/P6/P7)` section with:
    - explicit scope,
    - execution principles,
    - phases `N0` through `N6`,
    - NDLM-specific fit/reconstruction/post contracts,
    - stop conditions and anti-patterns,
  - recorded the key operational clarification:
    - the active NDLM blocker is `ndlm_main`, not the closed-form `ndlm_univar` family.

### 2026-03-26 real-data proof step
- Launched real targeted NDLM repair run on actual `2021-01-23` inputs using the new exact VB/CAVI engine:
  - `config/unified_runs/repair_r1_ndlm_main_drop_20210123_20260324.yaml`
  - resolved run id: `repair_r1_ndlm_main_drop_20210123_20260324_rerun_20260326_083229`
  - monitor log: `repro/hardening_logs/repair_r1_ndlm_main_drop_20210123_20260324.repair.log`
- Current live state at launch checkpoint:
  - `data_prep_shared=pass`
  - `fit=pending`
  - worker process `scripts/run_ndlm_main.R` active on CPU under the unified run
- Purpose of this step:
  - move beyond synthetic harness validation
  - verify the exact multivariate NDLM `drop` path on real repair inputs before running `keep`

## 2026-03-29 Reintegration Update

### Run-area cleanup
Status: **PASS**

- Preserved all protected canonical multimodel lineage roots in `repro/runs/`:
  - `multimodel_20210123*`
  - `multimodel_20211112*`
  - `multimodel_20211221*`
  - `multimodel_20220511*`
  - `multimodel_20221225*`
- Created archive root:
  - `repro/runs_archive_20260329/`
- Moved stale one-off debug / repair / control clutter out of the main run surface:
  - `90` runs archived
- Retained accepted evidence runs in place:
  - `control_exdqlm_multivar_drop_c1_epsTT_df1_20210123_2018_20260327`
  - `control_exdqlm_multivar_keep_c1_epsTT_df1_20210123_2018_20260327`
  - `control_ndlm_main_drop_c1_epsTT_df1_20210123_2018_20260327`
  - `decision_ndlm_main_drop_fullhist_bounded_20210123_19870529_20260327`
  - `decision_ndlm_main_keep_fullhist_bounded_20210123_19870529_20260327_rerun_20260328_054731`
- Inventory evidence:
  - `repro/reports/run_cleanup_20260329/run_inventory_classification_20260329.csv`

### Accepted NDLM bounded full-history references
Status: **PASS**

- `drop` accepted reference:
  - run: `decision_ndlm_main_drop_fullhist_bounded_20210123_19870529_20260327`
  - `fit=pass`, `post=pass`, `converged=true`, `iterations_completed=14`
  - `w_fore=0.00000317`
  - `cov_cap_clipped=0`
  - forecast scale sane (`max_abs_mean_draw_loglog1p=0.616358`)
- `keep` accepted reference:
  - run: `decision_ndlm_main_keep_fullhist_bounded_20210123_19870529_20260327_rerun_20260328_054731`
  - `fit=pass`, `post=pass`, `converged=true`, `iterations_completed=15`
  - `w_fore=0.00000285`
  - `cov_cap_clipped=0`
  - forecast scale sane (`max_abs_mean_draw_loglog1p=2.97908`)

Interpretation:
- The revised full-history exact NDLM specification is accepted for bounded reintegration proof on both `drop` and `keep`.

### Unified multimodel proof batch
Status: **PARTIAL**

Proof configs:
- `config/unified_runs/proof_mm9_20210123_l1_20260329.yaml`
- `config/unified_runs/proof_mm9_20210123_l2_20260329.yaml`

`l1` result:
- run: `proof_mm9_20210123_l1_20260329`
- `data_prep_shared=pass`, `fit=pass`, `post=pass`, `validate=pass`, `report=pass`
- validated under `production_proof`
- successful model-ID coverage in CRPS exports:
  - `dqlm_univar_al_synth`
  - `dqlm_multivar_al_synth_drop`
  - `dqlm_multivar_al_synth_keep`
  - `ndlm_main_synth_keep`
  - `ndlm_univar_synth_keep`

`l2` result:
- run: `proof_mm9_20210123_l2_20260329`
- `data_prep_shared=pass`, `fit=pass`, `post=fail`
- failure localized to mixed post univariate synthesis:
  - `repro/runs/proof_mm9_20210123_l2_20260329/post/logs/post_runner.log`
  - `R/environmetrics/30_univariate_and_misc.R`
- exact failure:
  - `rexal()` rejected out-of-bounds `gamma`
  - logged example: `Invalid gamma: -11.7161, Allowed range: (-3.75165, 0.298837)`

Fit-side evidence for the failing `exdqlm_univar` lane:
- `q=05`: `gamma=11.48552162`, `converged=false`, `max_iter_reached`
- `q=50`: `gamma=-1.07686870`, `converged=false`, `max_iter_reached`
- `q=95`: `gamma=-11.71607908`, `converged=false`, `max_iter_reached`
- source:
  - `repro/runs/proof_mm9_20210123_l2_20260329/fit/exdqlm_univar/q=*/logs/univar_theory_summary.log`

Interpretation:
- The reintegration blocker is no longer NDLM.
- The active blocker is now the theory-aligned `exdqlm_univar` extreme-tail fit/post contract in the mixed multimodel path.

### Current readiness decision
Status: **NOT READY for heavier canonical all-model workflow**

Single smallest blocker:
- Repair or guard the theory-aligned `exdqlm_univar` extreme-tail `gamma` path so mixed post no longer passes invalid `gamma` values into `rexal()` for `q=0.05/0.95`.

Residual, non-blocking note:
- `ndlm_univar_synth_keep` remains operationally integrated, but its bounded-proof CRPS scale in `l1` is still poor and should be tracked as a model-quality follow-up after the exDQLM-univar blocker is cleared.

### 2026-03-29 comparison-ready `v7` closure for cutoff `2021-01-23`
Status: **PASS**

Accepted lane configs:
- `config/unified_runs/multimodel_20210123_v7_l1.yaml`
- `config/unified_runs/multimodel_20210123_v7_l2.yaml`

Operational closeout runs:
- Lane 1 accepted comparison source:
  - run: `multimodel_20210123_v7_l1_postreplay_fix1_20260329_rerun_20260329_150051`
  - source fit root: `multimodel_20210123_v7_l1`
  - `post=pass`, `validate=pass`, `report=pass`
- Lane 2 accepted comparison source:
  - run: `multimodel_20210123_v7_l2`
  - `fit=pass`, `post=pass`, `validate=pass`, `report=pass`

Aggregate comparison bundle:
- `repro/reports/multimodel_20210123_v7_compare/crps_forecast_summary_all_models.csv`
- `repro/reports/multimodel_20210123_v7_compare/crps_input_health_all_models.csv`
- `repro/reports/multimodel_20210123_v7_compare/model_coverage.csv`
- `repro/reports/multimodel_20210123_v7_compare/summary.md`

Coverage result:
- exported target models: `9/9`
- target IDs now covered in the aggregate bundle:
  - `exdqlm_univar_synth`
  - `dqlm_univar_al_synth`
  - `exdqlm_multivar_synth_drop`
  - `exdqlm_multivar_synth_keep`
  - `dqlm_multivar_al_synth_drop`
  - `dqlm_multivar_al_synth_keep`
  - `ndlm_main_synth_drop`
  - `ndlm_main_synth_keep`
  - `ndlm_univar_synth_keep`

Interpretation:
- `20210123` is now comparison-ready under the supported tables-first mixed post route.
- The active accepted exAL-univariate policy in the comparison lane remains:
  - `implementation_mode=legacy_bridge`
- The active default-policy basis remains the protected canonical lineage, not the stale old NDLM template defaults.

Residual caveats:
- `dqlm_univar_al_synth` is operationally valid, but its input-health magnitude remains much larger than the exDQLM / NDLM synthesis rows.
- `ndlm_main_synth_keep` is healthy and fully exported, but its predictive scale remains larger than `ndlm_main_synth_drop`.
- These are comparison-quality caveats, not workflow-closure blockers for `20210123`.

Readiness decision:
- `20210123` is ready to serve as the comparison-ready reference cutoff.
- Next rollout should reuse the same two-lane `v7` structure and tables-first mixed post policy for the remaining protected cutoffs, without reopening NDLM main or multivariate exDQLM calibration unless a new cutoff-specific regression appears.

### 2026-03-31 `dqlm_univar_al_synth` comparison-policy closure
Status: **PASS**

Accepted current policy:
- `dqlm_univar_al_synth` should use:
  - `likelihood_mode=al`
  - `implementation_mode=legacy_bridge`
- `theory_aligned + al` remains available for research, but it is **not** the accepted comparison/canonical workflow at this time.

Reason:
- The large CRPS gap versus `exdqlm_univar_synth` was traced to the old `theory_aligned + al` predictive/post contract, not to the AL likelihood by itself.
- The repaired `legacy_bridge + al` path restores sane forecast scale and CRPS.

Code/policy changes now in place:
- `R/unified/config.R`
- `config/unified_run.template.yaml`
- `R/unified/manifest.R`
- `R/unified/stages/stage_fit.R`
- `R/unified/stages/stage_post.R`
- `tests/testthat/test_config_mode_resolution.R`
- active `v7_l1` configs for all protected cutoffs now pin `models.exdqlm_univar.implementation_mode=legacy_bridge`

Cross-cutoff isolated validation runs:
- `repair_p8_univar_al_lineage_legacy_20210123_19870529_20260331`
- `repair_p8_univar_al_lineage_legacy_20211112_20260331`
- `repair_p8_univar_al_lineage_legacy_20211221_20260331`
- `repair_p8_univar_al_lineage_legacy_20220511_20260331`
- `repair_p8_univar_al_lineage_legacy_20221225_20260331`

Summary report:
- `repro/reports/dqlm_univar_al_legacy_bridge_validation_20260331/summary.md`
- `repro/reports/dqlm_univar_al_legacy_bridge_validation_20260331/cross_cutoff_validation.csv`

Key evidence:
- repaired AL mean CRPS is now close to exAL on every cutoff with an existing comparison bundle:
  - `20210123`: `0.2955` vs `0.2969` (old bad `6.5113`)
  - `20211112`: `0.1340` vs `0.1350` (old bad `3.8349`)
  - `20211221`: `1.0965` vs `1.1526` (old bad `3.4983`)
  - `20220511`: `0.0697` vs `0.0738` (old bad `11.7865`)
- `20221225` isolated repaired AL validation also closes cleanly:
  - `fit=pass`, `post=pass`, `validate=pass`, `report=pass`
  - `mean_crps=1.5653`
  - `max_abs_observed=16.7555`
  - `status=pass`

Reintegration evidence:
- corrected `20210123` lane-1 replay:
  - `multimodel_20210123_v7_l1_alfix_postreplay_20260331`
- corrected aggregate comparison bundle:
  - `repro/reports/multimodel_20210123_v7_compare_alfix_20260331`

Decision:
- `dqlm_univar_al_synth` model repair is now closed for current comparison workflows.
- The remaining work is later multimodel relaunch/replay to ingest the accepted AL policy into aggregate bundles, not further root-cause repair of the AL likelihood path.
