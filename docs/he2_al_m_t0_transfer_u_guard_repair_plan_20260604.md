# HE2 AL-M-T0 Transfer/u_t Guard Repair Plan - 2026-06-04

## Purpose

This document is the execution plan for repairing and validating the HE2 AL-M-T0 workflow after the deep diagnostic audit found invalid saved fits in representative quantile lanes.

The immediate target is the AL multivariate transfer family, but the plan is written so the repairs can protect the broader publication workflow: exDQLM multivariate keep/drop, AL analogues, univariate analogues, CRPS tables, diagnostic figures, and revised article outputs.

The verified evidence bundle is:

`reports/he2_al_m_t0_representative_diagnostic_deep_audit_20260604/`

The key conclusion is:

The invalid `20211112_q35` and `20220511_q65` AL-M-T0 fits are not a plotting problem and not primarily an `s_t` bug. They are invalid saved fits caused by transfer-level runaway coupled with AL `u_t` / pseudo-data instability. Before the 2026-06-04 repair, the AL guard and health checks did not reliably intercept this failure before outputs could be promoted.

This plan is deliberately conservative. We first make failures detectable and reproducible. Then we stabilize the latent/pseudo-data and transfer-design layers. Only after those gates pass do we relaunch publication workflows.

## Implementation Status - 2026-06-04

Implemented in commit-ready local changes after the plan was written:

| Area | Status | Tracked implementation |
|---|---|---|
| AL state guard bypass | fixed | `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r` now lets `state_guard_enabled` apply to AL and exAL; the policy log includes `likelihood_mode`, `state_guard`, `state_guard_configured`, `state_guard_effective_policy`, and `state_guard_disabled_reason` |
| Terminal saved-state health | fixed | `R/unified/stages/stage_fit.R` extends `unified_multivar_fit_health_check(...)` to check historical `theta.out$exps`, `theta.out$sm`, `state_norm_sq/T`, transfer row 22, and transfer coefficients |
| Terminal health artifacts | fixed | future fits write `multivar_terminal_state_health.txt` and `multivar_terminal_state_health.csv` next to `multivar_forecast_health.txt` |
| AL `E[1/u_t]` floor saturation | fixed as detection/gate | `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r` and `R/disc_w/11_latent_pseudodata_audit_helpers.R` now classify excessive floor mass as `floor_saturated` |
| Runtime config propagation | fixed | `R/unified/config.R` and `R/unified/stages/stage_fit.R` carry `e_inv_u_floor`, `e_inv_u_floor_frac_cap`, historical location/state limits, and transfer limits |
| Transfer design diagnostics | implemented | `R/unified/families/shared_input_helpers.R` adds `family_shared_transfer_design_diagnostics(...)`; `R/disc_w/03_covariates_standardize.R` writes transfer design summary/condition/metadata when the fit stage provides a diagnostic directory |
| Deterministic tests | implemented | added/extended `test_exdqlm_multivar_terminal_health.R`, `test_exdqlm_multivar_keep_latent_pseudodata_audit.R`, `test_config_mode_resolution.R`, and `test_covariate_feature_engineering.R` |
| Retained-output replay helper | implemented | `scripts/replay_he2_al_m_t0_terminal_health.R` regenerates the terminal-health replay report from retained representative `.RData` files |

Real retained-output replay was run without modifying the retained runs:

`reports/he2_al_m_t0_terminal_health_replay_20260604/terminal_health_replay_summary.csv`

| lane | new violation count | max historical exps abs | state norm sq / T | transfer row 22 max abs | result |
|---|---:|---:|---:|---:|---|
| `20211112_q35` | 3 | 964.608 | 434474.403 | 964.431 | fail, as expected |
| `20211221_q80` | 0 | 8.274 | 9.223 | 4.913 | pass, as expected |
| `20220511_q65` | 3 | 560.034 | 205100.754 | 552.359 | fail, as expected |
| `20221225_q80` | 0 | 8.386 | 12.029 | 4.730 | pass, as expected |

The replay confirms that Phases 1-3 now catch the two verified bad saved fits while preserving the q80 controls. No broad relaunch was started. The next launchable step is the targeted Phase 5 experiment ladder, using the new gates and transfer diagnostics.

Validation run on 2026-06-04:

```bash
Rscript --vanilla -e "invisible(parse('DISC_Optimal_Synth_Ranges_W_transfer_forecast.r')); invisible(parse('R/unified/stages/stage_fit.R')); invisible(parse('R/unified/config.R')); invisible(parse('R/disc_w/03_covariates_standardize.R')); invisible(parse('R/unified/families/shared_input_helpers.R')); invisible(parse('R/disc_w/11_latent_pseudodata_audit_helpers.R')); cat('parse_ok\n')"
Rscript --vanilla -e "library(testthat); test_file('tests/testthat/test_exdqlm_multivar_terminal_health.R'); test_file('tests/testthat/test_exdqlm_multivar_keep_latent_pseudodata_audit.R')"
Rscript --vanilla -e "library(testthat); test_file('tests/testthat/test_config_mode_resolution.R'); test_file('tests/testthat/test_covariate_feature_engineering.R')"
python3 -m unittest tests.python.test_stage_fit_quantile_gamma_sigma_overrides tests.python.test_he2_al_m_t0_diagnostic_plan tests.python.test_he2_remaining_quantile_al_exal_relaunch
Rscript --vanilla -e "library(testthat); test_dir('tests/testthat', filter='exdqlm|config|post|visual|latent|pseudodata|covariate_feature')"
Rscript --vanilla -e "invisible(parse('scripts/replay_he2_al_m_t0_terminal_health.R')); cat('replay_script_parse_ok\n')"
```

Results:

- parse check: pass.
- targeted terminal/latent/config/covariate R tests: pass.
- targeted Python launch/config tests: 12 tests pass.
- broader filtered R `testthat` pass: 572 pass, 0 fail, 3 expected warning assertions.
- retained-output replay helper parse check: pass.

## Targeted Transfer Ladder Implementation - 2026-06-04

The Phase 5 A0-A4 ladder is now implemented in tracked code and launched in isolated diagnostic roots.

Tracked implementation:

| Surface | Status | Notes |
|---|---|---|
| Transfer feature modes | implemented | `inputs.transfer_function_covariates.mode` supports `full`, `base_only`, `custom`, and `none`; publication default remains `full` |
| Transfer feature scaling | implemented | `inputs.transfer_function_covariates.scaling` supports historical `sd` and diagnostic `zscore` |
| Transfer-level-only state setup | implemented | both `DISC_Optimal_Synth_Ranges_W.r` and `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r` now skip `2:ppx` assignments when `ppx == 1` |
| Zero-sized discount blocks | implemented | legacy `make_df_mat(...)` and `make_df_mat_k(...)` skip zero-dimensional covariate blocks instead of indexing `2:1` |
| Diagnostic package builder | implemented | `scripts/build_he2_dqlm_multivar_al_drop_diagnostic_plan.py` can prepare `a0`, `a1`, `a2`, `a3`, `a4`, or full `ladder` scopes |
| Diagnostic launcher | implemented | `scripts/launch_he2_al_m_t0_representative_diagnostics.py` validates the requested experiment scope before launch |
| Live monitor | implemented | `scripts/monitor_he2_al_m_t0_diagnostic_ladder.py` writes compact CSV/Markdown status across one or more diagnostic roots |

Experiment definitions:

| Experiment | Transfer design | Scaling | Purpose |
|---|---|---|---|
| `a0_full_sd` | full feature set | SD-only | current high-discount control with new guards/checks |
| `a1_transfer_level_only` | transfer level only, no covariate rows | SD-only placeholder | tests whether covariate driver rows cause runaway |
| `a2_full_zscore` | full feature set | history-fitted z-score | tests scale-driven instability |
| `a3_base_sd` | `PPT`, `SOIL`, `PCA` only | SD-only | tests reduced identifiability |
| `a4_base_zscore` | `PPT`, `SOIL`, `PCA` only | history-fitted z-score | candidate low-complexity stable specification |

Validation commands added/run:

```bash
python3 -m unittest tests.python.test_he2_al_m_t0_diagnostic_plan -v
Rscript --vanilla -e "library(testthat); test_file('tests/testthat/test_config_mode_resolution.R'); test_file('tests/testthat/test_covariate_feature_engineering.R'); test_file('tests/testthat/test_exdqlm_multivar_transfer_level_only_helpers.R')"
Rscript --vanilla -e "invisible(parse('DISC_Optimal_Synth_Ranges_W.r')); invisible(parse('DISC_Optimal_Synth_Ranges_W_transfer_forecast.r')); invisible(parse('R/environmetrics/02_helpers_core.R')); cat('parse_ok\n')"
```

Observed validation status:

- Python diagnostic-plan tests: 7 pass, 0 fail.
- R config/covariate/transfer-level-only helper tests: pass, 0 fail.
- Legacy DISC entrypoint parse check: pass.

Runtime roots:

| Root | Role | Status |
|---|---|---|
| `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_dqlm_multivar_al_drop_transfer_ladder_highdf_eps365_cf1_20260604` | first 20-lane A0-A4 launch | A0/A2/A3/A4 active; its A1 rows failed before the actual drop entrypoint was patched |
| `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_dqlm_multivar_al_drop_a1_transfer_level_only_retry_highdf_eps365_cf1_20260604` | first A1 retry | failed for the same reason: `DISC_Optimal_Synth_Ranges_W.r` still had the zero-column `2:ppx` bug |
| `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_dqlm_multivar_al_drop_a1_transfer_level_only_retry2_highdf_eps365_cf1_20260604` | patched A1 retry | active after patching the actual drop entrypoint |

The failed A1 roots are retained as useful implementation evidence: they show that `transfer_level_only` exposed a real code-path gap in the drop entrypoint. They should not be interpreted as scientific model failures.

Live status report:

`reports/he2_al_m_t0_transfer_ladder_live_20260604/DIAGNOSTIC_LADDER_LIVE_STATUS.md`

This report is intentionally untracked under `reports/`.

## Evidence Lock

The plan is grounded in these verified facts:

| Finding | Evidence |
|---|---|
| `20211112_q35` and `20220511_q65` are invalid saved fits | `terminal_gamsig_summary.csv`, `theta_exps_summary.csv`, `state_block_summary.csv` |
| Direct `.RData` recomputation validates the audit tables | `final_verification_crosscheck.csv`; 56/56 rows pass |
| The dominant state failure is transfer row 22 | `state_block_summary.csv`, `state_top_coordinates.csv` |
| `20211112_q35` terminal `E[sigma]` is about 41.76 and `state_norm_sq/T` is about 434474 | `terminal_gamsig_summary.csv`, `state_block_summary.csv` |
| `20220511_q65` terminal `E[sigma]` is about 90.27 and `state_norm_sq/T` is about 205101 | `terminal_gamsig_summary.csv`, `state_block_summary.csv` |
| AL mode zeroes `gamma` and `s_t` moments | `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:739-740`, `1638-1644`, `1919-1924` |
| `u_t` and pseudo-data are central in AL mode | `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:1967-2004`, `5061-5080` |
| AL state guard is currently bypassed | `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:5774-5776`, `gamsig_policy_summary.csv`, `fit_log_event_summary.csv` |
| Existing health checks can miss impossible historical fitted locations | `forecast_health_summary.csv`, `theta_exps_summary.csv` |
| q80 controls can recover from transient large early values | representative q80 retained outputs and final terminal summaries |

Do not delete the retained diagnostic `.RData` files until the replay checks in this plan are implemented and have produced replacement evidence.

## Current Machinery To Reuse

The repair should reuse existing code instead of creating a parallel workflow:

| Area | Existing surface |
|---|---|
| Unified fit health | `R/unified/stages/stage_fit.R`, especially `unified_multivar_fit_health_check(...)` |
| Runtime guard env/config propagation | `R/unified/stages/stage_fit.R` and `R/unified/config.R` |
| Main active model path | `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r` |
| Pseudo-data audit helpers | `R/disc_w/11_latent_pseudodata_audit_helpers.R` |
| Existing pseudodata guard hooks | `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r` around guard summaries, guard checks, and `disc_w_diag_health_stats(...)` |
| Ensemble/input bookkeeping | `R/disc_w/04_ensemble_bookkeeping.R`, `R/disc_w/06_ensemble_spec.R`, shared input helpers |
| Config validation | `R/unified/config.R` |
| Existing tests | `tests/testthat/test_exdqlm_multivar_keep_latent_pseudodata_audit.R`, `tests/testthat/test_config_mode_resolution.R`, `tests/python/test_stage_fit_quantile_gamma_sigma_overrides.py`, `tests/python/test_he2_al_m_t0_diagnostic_plan.py`, `tests/python/test_he2_remaining_quantile_al_exal_relaunch.py` |

Any new code should be small, shared, and callable by both the diagnostic runner and production stage. We should not create one-off logic that only works for the current audit reports.

## Planning Principles

1. Detection before tuning: impossible states must be caught before we try new discount factors, priors, caps, or transfer designs.
2. Terminal health is separate from transient health: a run can have early spikes and recover. The saved posterior state and historical fitted locations must be checked directly.
3. AL and exAL need explicit policies: `gamma=0` and `s_t=0` in AL mode are intentional, but that does not justify disabling state or pseudo-data guards.
4. Transfer identifiability is a model-design problem: if row 22 dominates the state norm, numerical guards alone are not a sufficient scientific fix.
5. Every relaunch needs a manifest: cutoff, quantile, likelihood, transfer design, input bundle hash/path, discount factors, `lambda`, epsilon, `c_factor`, max iterations, cleanup policy, and post outputs.
6. Publication tables must distinguish valid fits from failed fits: a failure is useful evidence, but it cannot silently become a CRPS candidate.

## Implementation Order and Rationale

| Order | Workstream | Why it comes here |
|---|---|---|
| 0 | Freeze evidence and scope | Protects the retained bad and healthy controls used to prove the fix |
| 1 | Make AL guards real and truthful | Removes the known contradiction between configured policy and active code |
| 2 | Add terminal saved-state health | Prevents invalid `.RData` from reaching post, figures, or CRPS |
| 3 | Add latent/pseudo-data health | Detects the AL `u_t` mechanism before it contaminates the Kalman update |
| 4 | Diagnose and stabilize transfer design | Addresses the row-22 runaway root model issue |
| 5 | Run targeted repair experiments | Tests only the lanes needed to decide the repair path |
| 6 | Promote to publication workflow | Reconnects successful fixes to the full model-family pipeline |
| 7 | Commit tests/docs and freeze run contracts | Makes the repair reproducible and reviewable |

## Success Definition

We are done only when all of the following are true:

1. Deterministic tests prove AL state guards activate when `state_norm_sq`, `state_norm_sq / T`, transfer row 22, or historical `theta.out$exps` exceeds configured limits.
2. Deterministic tests prove AL latent/pseudo-data health checks detect collapsed `E[1/u_t]`, floor saturation, extreme `FFF`, extreme `QQQ`, and non-finite pseudo-data values.
3. Replaying retained bad diagnostics marks `20211112_q35` and `20220511_q65` unhealthy.
4. Replaying healthy q80 controls does not falsely fail because of transient early iteration spikes once final saved-state checks are used.
5. Targeted q35/q65 repair experiments identify either a stable AL-M-T0 specification worth promoting or a justified conclusion that AL-M-T0 with this transfer design is not promotable.
6. Production/post cannot advance a failed quantile into CRPS summaries, article tables, or winner selection without an explicit failure status.
7. The plan, code, tests, and reports are cross-linked so another reader can reproduce the decision.

## Definition Of Done By Phase

| Phase | Done means |
|---|---|
| 0 | Evidence is preserved, the plan is tracked, and no broad relaunch has been started |
| 1 | AL guard policy is effective, logged, tested, and no longer contradicts the printed policy |
| 2 | Terminal saved-state health exists, emits CSV/text, and catches retained bad fits |
| 3 | AL latent/pseudo-data checks exist, emit summaries, and catch `u_t` floor/collapse mechanisms |
| 4 | Transfer design diagnostics and optional standardization/reduction modes are available and tested |
| 5 | Targeted q35/q65/control experiments produce a clear promote/reduce/exclude decision |
| 6 | Publication relaunch manifests and post-stage outputs use the selected valid spec only |
| 7 | Tests pass, docs are updated, commits are reviewable, and runtime evidence remains under `reports/` |

## Phase 0: Freeze Scope And Preserve Evidence

Goal: avoid losing the evidence that makes the root cause reproducible.

Investigation tasks:

1. Confirm retained diagnostic `.RData` paths for:
   - `20211112_q35`;
   - `20220511_q65`;
   - q80 healthy controls.
2. Confirm `final_verification_crosscheck.csv` still exists and has no review/fail rows.
3. Confirm no current live production campaign is being stopped or modified.
4. Confirm `reports/` artifacts remain untracked unless explicitly promoted.

Implementation tasks:

1. Add this plan under `docs/`.
2. Add a small manifest, if missing, that records the retained diagnostic paths and report files needed for replay.
3. Do not clean diagnostic `.RData` until replay tests are implemented.

Acceptance gate:

- `reports/he2_al_m_t0_representative_diagnostic_deep_audit_20260604/final_verification_crosscheck.csv` remains available or is reproducibly regenerated.
- `git status` shows no accidental `reports/` additions.

## Phase 1: Make AL State Guards Real

Goal: remove the implementation contradiction where the policy prints or configures a state guard, but AL mode bypasses it.

Primary code:

- `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r`
- `R/unified/stages/stage_fit.R`
- `R/unified/config.R`
- existing guard/config tests under `tests/python/` and `tests/testthat/`

Pre-repair defect:

```r
state_guard_active <- (!isTRUE(DISC_W_AL_MODE) &&
  isTRUE(state_guard_enabled) &&
  as.integer(iter) >= as.integer(DISC_GAMSIG_STATE_GUARD_START_ITER))
```

This disabled the state guard for AL mode, even though AL is exactly where the retained failure occurs. The 2026-06-04 repair removes the AL exclusion and adds explicit effective-policy logging.

Investigation tasks:

1. Trace every config/env variable that controls:
   - `state_guard_enabled`;
   - `DISC_GAMSIG_STATE_GUARD_START_ITER`;
   - `DISC_GAMSIG_STATE_NORM_ABS_CAP`;
   - `DISC_GAMSIG_STATE_NORM_PER_T_CAP`;
   - transfer-specific caps, if present.
2. Compare the configured policy printed in logs with the effective conditional used in the model loop.
3. Identify what state is available at the guard decision point:
   - proposed `theta`;
   - previous accepted `theta`;
   - gamma/sigma state;
   - `u_t`, `s_t`;
   - Kalman covariance outputs.
4. Confirm whether guard rejection currently reverts all coupled quantities or only a subset.

Implementation tasks:

1. Replace the unconditional AL bypass with explicit likelihood-aware policy:
   - `state_guard_enabled` means active for both AL and exAL unless a separate config key disables it;
   - if separate defaults are needed, use explicit keys such as `al_state_guard_enabled` and `exal_state_guard_enabled`;
   - never let the printed policy disagree with the actual condition.
2. Log both configured and effective guard state:
   - `state_guard_configured`;
   - `state_guard_effective`;
   - `likelihood_mode`;
   - `disabled_reason`, if disabled.
3. Keep guard semantics conservative:
   - if a proposed update exceeds an absolute cap, reject that coupled update;
   - revert to previous accepted `theta`, `u_t`, `s_t`, gamma/sigma, and covariances where applicable;
   - refreeze or hold state updates for configured iterations after repeated guard events;
   - do not let a guard-triggered rejection count as clean convergence.
4. Add a terminal guard gate for saved states:
   - if the last saved state is impossible, mark the fit unhealthy before post;
   - production mode should fail or stop before post sampling;
   - diagnostic mode may continue only with `status=unhealthy`.

Tests:

1. AL-mode synthetic state with `state_norm_sq/T` above cap must trigger the effective guard.
2. AL-mode synthetic transfer row 22 above cap must trigger the effective guard.
3. exAL behavior must remain guarded under the same policy.
4. Config test: when policy reports `state_guard=true`, effective guard cannot be false unless a log field names the exact override reason.
5. Regression test: current bad retained lanes would be marked unhealthy by replay.

Acceptance gate:

- A synthetic AL failure is rejected.
- The verified q35/q65 retained failures are marked unhealthy by replay health checks.
- q80 control retained outputs remain passable by final saved-state checks.

## Phase 2: Add Terminal Fit-Health Checks For Saved `theta.out`

Goal: prevent invalid saved fits from reaching post or publication tables.

Primary code:

- `R/unified/stages/stage_fit.R`
- `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r`
- optionally `R/disc_w/11_latent_pseudodata_audit_helpers.R`

Current gap:

The existing forecast health check can pass when `max_E_sigma < 100`, even if historical `theta.out$exps` is hundreds of units on the log1p scale. That is exactly the kind of saved-state failure seen in the retained diagnostics.

Investigation tasks:

1. Confirm the 34-state layout used by the current AL-M-T0 diagnostic:
   - rows 1-7: shared quantile state;
   - rows 8-14: GloFAS discrepancy;
   - rows 15-21: NWS discrepancy;
   - row 22: transfer level;
   - rows 23-34: transfer coefficient block for the current full transfer design.
2. Confirm how `theta.out$exps` is reconstructed from state blocks historically.
3. Confirm whether the post stage reads `theta.out$exps`, `theta.out$sm`, or both.
4. Calibrate thresholds using retained bad and healthy controls:
   - bad q35/q65 should fail;
   - q80 controls should pass on final saved state;
   - transient early spikes should be separate warnings, not terminal failures.

Implementation tasks:

1. Extend `unified_multivar_fit_health_check(...)` or add a shared sibling check for saved multivariate state:
   - historical `theta.out$exps` max absolute value by source;
   - historical `theta.out$exps` quantiles by source;
   - full `theta.out$sm` norm and `state_norm_sq/T`;
   - per-block state norms;
   - transfer row 22 max abs and median abs;
   - transfer coefficient max abs;
   - reconstruction check between state block locations and `theta.out$exps`.
2. Make thresholds config-driven and likelihood-aware. Initial hard-fail diagnostic caps:
   - `max_abs_history_exps <= 25` on log1p scale for routine production;
   - `transfer_level_max_abs <= 25`;
   - `state_norm_sq_per_T <= 1e4` as a generous diagnostic cap.
3. Emit compact health artifacts for each quantile:
   - `multivar_terminal_state_health.txt`;
   - `multivar_terminal_state_health.csv`;
   - optional `multivar_terminal_state_health.json` if stage orchestration benefits from machine-readable status.
4. Wire fail behavior:
   - diagnostics may continue with `status=unhealthy`;
   - production/post should stop before posterior sampling or publication metrics.

Tests:

1. Fixture with `theta.out$exps` max abs of 500 must fail.
2. Fixture with only an early transient log spike but healthy final saved `theta.out` must pass terminal health.
3. Fixture where transfer row 22 dominates state norm must flag `transfer_level_runaway`.
4. Replay retained q35/q65/q80 summaries using lightweight CSV fixtures where possible.

Acceptance gate:

- Retained `20211112_q35` and `20220511_q65` outputs fail terminal-state replay.
- Retained q80 controls pass terminal-state replay.
- The post stage cannot produce CRPS rows for a failed fit without marking the row as failed.

## Phase 3: Add AL Latent And Pseudo-Data Health Checks

Goal: detect the `u_t`/pseudo-data mechanism before it corrupts the state update.

Primary code:

- `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r`
- `R/disc_w/11_latent_pseudodata_audit_helpers.R`
- `R/unified/stages/stage_fit.R`

Current mechanism:

In AL mode, `gamma=0` and `E[s_t]=0`, so the pseudo-data approximately reduces to:

```text
FFF ~= A(p0) / E[1/u_t]
QQQ ~= B(p0) * sigma / E[1/u_t]
```

When `E[1/u_t]` hits the small-value floor, `FFF` and `QQQ` become numerically absurd even if the implied precision is tiny. Existing pseudodata guards emphasize large `E[1/u_t]` caps, but the retained failures also require checking small or floored `E[1/u_t]` and its effect on pseudo-data scale.

Investigation tasks:

1. Confirm exact AL parameterization in `update_uts(...)`:
   - `lambda`;
   - `psi`;
   - `chi`;
   - formulas for `E[u_t]`, `E[1/u_t]`, `E[log u_t]`, and entropy.
2. Confirm fit-stage and sampling-stage use the same AL `u_t` semantics.
3. Confirm the historical and forecast pseudo-data construction:
   - `FFF`;
   - `QQQ`;
   - `FFF_forecast`;
   - `QQQ_forecast`.
4. Compare retained bad and healthy lanes for:
   - min, median, max `E[u_t]`;
   - min, median, max `E[1/u_t]`;
   - floor fraction for `E[1/u_t]`;
   - `FFF` and `QQQ` quantiles.

Implementation tasks:

1. Track and summarize for history and forecast members:
   - `E[u_t]`;
   - `E[1/u_t]`;
   - `E[log u_t]`;
   - floor counts for `E[u_t]` and `E[1/u_t]`;
   - `u.psi`, `u.chi`, and `u.lambda` ranges when available;
   - `FFF` and diagonal `QQQ` ranges.
2. Add AL-specific failure rules:
   - fail if `E[1/u_t]` floor saturation exceeds a configurable fraction, initially `> 0.25` in any source;
   - fail if median `E[u_t]` is implausibly large relative to healthy controls;
   - fail if `FFF` or `QQQ` exceeds caps;
   - fail if pseudo-data has non-finite or nonpositive variance.
3. Add a pseudo-data representation warning:
   - if both `FFF` and `QQQ` are enormous because precision is tiny, flag `information_form_recommended`.
4. Keep first implementation as detection-only:
   - do not cap values until targeted tests show the cap improves q35/q65 and preserves q80 controls;
   - if capping is later added, log cap counts and mark the fit as guarded.

Tests:

1. Fixture with `E[1/u_t]=1e-10` for most times must fail.
2. Fixture with healthy q80-like `E[1/u_t]` must pass.
3. Fixture with enormous finite `FFF`/`QQQ` must fail.
4. Test AL `s_t` zero semantics remains intact.
5. Test forecast pseudo-data summaries are emitted and use the same thresholds.

Acceptance gate:

- q35 retained output fails because `E[1/u_t]` floor saturation and pseudo-data are extreme.
- q65 retained output fails because `E[u_t]`, `E[1/u_t]`, and `QQQ` are unhealthy, even if `E[1/u_t]` is not fully floored.
- q80 controls pass or produce only documented warnings for transient forecast-member floor values.

## Phase 4: Stabilize Transfer Identifiability

Goal: address the model-side cause of transfer row 22 runaway.

Primary code:

- `R/disc_w/03_covariates_standardize.R`
- `R/unified/families/shared_input_helpers.R`
- `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r`
- config builders for AL-M-T0 diagnostics and publication relaunches

Observed risk:

The transfer state evolves as:

```text
h_t = lambda * h_{t-1} + X_t beta_t
```

with `lambda=0.97`, near-frozen `df_trans/df_covs`, and transfer features on very different scales. The active feature set includes precipitation, soil, GDPC/PCA, squares, interactions, and lags. Some features are not comparable in scale. Prior evidence showed `PPT_sq` can be orders of magnitude larger than soil terms.

Investigation tasks:

1. Confirm the exact transfer feature names and ordering in the active input bundles.
2. Confirm feature scaling for every cutoff:
   - 1987-to-cutoff historical window;
   - forecast window;
   - missing/fill behavior.
3. Compute design diagnostics:
   - min, median, max, mean, sd;
   - singular values or condition number;
   - pairwise correlations for high-risk columns;
   - max absolute `X beta` driver if beta is available.
4. Confirm the transfer coefficient rows map one-to-one to feature columns.
5. Confirm whether all alternative model families use the same input bundles and transfer covariate definitions.

Implementation tasks:

1. Add explicit transfer-design diagnostics before fit:
   - write `transfer_design_summary.csv`;
   - write `transfer_design_condition.csv`;
   - write `transfer_feature_metadata.csv`.
2. Add an optional standardized-transfer-feature mode:
   - standardize non-binary transfer covariates using history-only mean/sd;
   - apply the same transform to forecast covariates;
   - write scaling metadata into the input bundle and manifest;
   - fail if forecast uses missing scaling metadata.
3. Add optional transfer-block constraints for diagnostics:
   - smaller initial prior variance for row 22 and beta rows;
   - configurable `transfer_level_abs_cap`;
   - optional damped transfer update after guard events.
4. Add reduced-design diagnostic modes:
   - base covariates only: `PPT`, `SOIL`, `PCA/GDPC`;
   - no squares/interactions/lags;
   - soil-only and ppt-only stress tests if needed.

Tests:

1. Feature standardization produces history mean approximately 0 and sd approximately 1 for selected columns.
2. Forecast uses saved history scaling metadata.
3. Input bundle hash or metadata changes when standardized mode is enabled.
4. State layout remains consistent for the full design and is explicitly remapped for reduced designs.
5. Transfer feature order in metadata matches transfer coefficient order in state outputs.

Acceptance gate:

- We can run targeted diagnostics that differ only in transfer design and can compare them cleanly.
- No broad relaunch uses a transfer bundle without recorded feature-scaling metadata.

## Phase 5: Targeted Repair Experiments

Goal: determine whether AL-M-T0 is salvageable for the problem lanes without wasting a full grid.

Run only after Phases 1-4 pass.

Target lanes:

- `20211112_q35`;
- `20220511_q65`;
- `20211221_q80` as a healthy control;
- `20221225_q80` as a second healthy control if resources allow.

Run all with `max_iter=100` first. Retain `.RData` only for diagnostics, then clean after report generation.

Experiment ladder:

| Experiment | Change | Purpose |
|---|---|---|
| A0 | Current high-discount AL-M-T0 with new guards/checks | Prove old bad lanes now fail loudly |
| A1 | No transfer covariates, transfer level only | Test whether covariate driver causes row 22 runaway |
| A2 | Standardized full transfer features | Test scale-driven instability |
| A3 | Base features only: `PPT`, `SOIL`, `PCA/GDPC` | Test reduced identifiability |
| A4 | Standardized base features only | Candidate low-complexity stable specification |
| A5 | Lower `lambda` values, for example `0.90`, `0.95`, `0.97` | Test transfer persistence |
| A6 | Tighter transfer/covariate priors or lower `df_covs` | Test regularization/evolution effect |
| A7 | Pseudo-data information-form or cap diagnostic | Test numerical representation if model spec otherwise looks viable |

Experiment controls:

1. Same input bundle path/hash unless the experiment explicitly changes transfer design.
2. Same likelihood mode, cutoff, quantile, max iteration count, and cleanup policy.
3. One core per quantile model.
4. Runtime roots must include date, cutoff, likelihood, experiment id, and cleanup policy.
5. No broad launch and no article table update until this ladder produces a decision.

Evaluation metrics:

- pass/fail of new terminal health checks;
- terminal `E[sigma]`;
- `state_norm_sq/T`;
- transfer row 22 max abs and median abs;
- historical USGS `theta.out$exps` range;
- `E[u_t]`, `E[1/u_t]`, and floor fractions;
- `FFF`/`QQQ` ranges;
- CRPS only after the fit passes health gates;
- diagnostic figures around cutoff using fixed y-limits where needed.

Decision rule:

1. If A1 is healthy and A0 is not, transfer covariates are the root model-side driver.
2. If A2 is healthy, promote standardized transfer features as the leading fix.
3. If A3/A4 are healthy but A2 is not, full feature design is too weakly identified for AL-M-T0.
4. If all transfer-enabled variants fail but no-transfer passes, AL-M-T0 should be reported without transfer or excluded from that ablation family.
5. If all variants fail, AL-M-T0 multivariate drop/analogues are not currently promotable under the article workflow.

Acceptance gate:

- A recommendation exists for AL-M-T0: promote a stable spec, reduce the transfer design, or exclude/flag the family.

## Phase 6: Promotion And Relaunch Readiness

Goal: reconnect the repaired workflow to the publication/revised article pipeline.

Only begin after a targeted stable spec is found.

Investigation tasks:

1. Identify every model family that must use the same corrected input/wiring assumptions:
   - exDQLM multivariate keep;
   - exDQLM multivariate drop;
   - AL multivariate keep/drop analogues;
   - univariate exDQLM;
   - univariate AL analogue;
   - remaining ablation or correction-table families.
2. Confirm the revised article output contract:
   - CRPS table inputs;
   - ablation table inputs;
   - forecast-window synthesis figures;
   - trace and state diagnostics;
   - transfer coefficient summaries.
3. Confirm all publication runs use:
   - correct cutoff-specific input bundles;
   - correct GDPC/PCA covariate choice;
   - blended forecasts for precipitation and soil where required;
   - correct harmonics and transfer covariates;
   - no retained `.RData` unless diagnostic override is enabled.

Implementation tasks:

1. Update canonical config builders with:
   - selected transfer design;
   - selected discount factors, epsilon, `lambda`, and `c_factor`;
   - health gates enabled;
   - manifest writing;
   - cleanup policy after post.
2. Ensure post-stage generation includes:
   - CRPS tables and raw forecast baselines;
   - fixed-scale forecast-window synthesis plots;
   - deterministic location-parameter quantile plots;
   - ELBO, sigma/gamma, `u_t`, `s_t`, and state-norm traces;
   - transfer coefficient summaries;
   - terminal health summaries.
3. Run staged smoke tests:
   - one cutoff, two quantiles;
   - one formerly bad lane and one known healthy control;
   - then one full seven-quantile cutoff;
   - only then all cutoffs.
4. Make failed lanes first-class:
   - write failure status;
   - include reason in summary CSV;
   - do not let failed lanes enter winner selection.

Acceptance gate:

- Production run cannot advance to post if terminal fit health fails.
- CRPS tables include only valid models or explicit failure rows.
- The revised article workflow can find figures/tables from the run manifests without manual path guessing.

## Phase 7: Tests And Documentation Required Before Commit

Minimum existing tests to run:

```bash
python3 -m unittest \
  tests.python.test_stage_fit_quantile_gamma_sigma_overrides \
  tests.python.test_he2_al_m_t0_diagnostic_plan \
  tests.python.test_he2_remaining_quantile_al_exal_relaunch
```

R tests:

```bash
Rscript -e "testthat::test_dir('tests/testthat', filter='exdqlm|config|post|visual|latent|pseudodata')"
```

New or expanded tests required:

| Test area | Expected coverage |
|---|---|
| AL guard effective behavior | AL and exAL guard activation, disabled reason logging, cap rejection |
| Terminal multivar state health | `theta.out$exps`, `theta.out$sm`, state blocks, transfer row 22 |
| AL latent/pseudo-data health | `E[u_t]`, `E[1/u_t]`, floor fractions, `FFF`, `QQQ` |
| Transfer standardization | history-only scaling, forecast reuse, metadata/hash changes |
| Post-stage failure handling | failed fit cannot enter CRPS winner selection |
| Replay fixtures | retained q35/q65 fail, q80 controls pass |

Documentation updates:

1. This plan after each major decision.
2. `docs/he2_al_m_t0_blocked_diagnostic_plan_20260603.md`.
3. `docs/he2_remaining_quantile_al_exal_publication_relaunch_20260603.md`.
4. Publication/relaunch manifest docs once the stable spec is selected.
5. Any revised article integration notes that explain how valid outputs populate CRPS and ablation tables.

Commit policy:

1. Commit tracked docs/tests/code in small reviewable chunks.
2. Do not commit `reports/` unless a specific small evidence file is explicitly promoted.
3. Push only after the branch has passing targeted tests and a clean intentional status.

## Risk Register

| Risk | Why it matters | Mitigation |
|---|---|---|
| False failing q80 controls | q80 had transient large early values but healthy final saved states | Separate transient warnings from terminal saved-state failures |
| Thresholds too strict | Could reject valid high-flow event behavior on log1p scale | Calibrate with retained controls and expose config thresholds |
| Thresholds too loose | Could allow q35/q65-style invalid fits into CRPS | Replay bad lanes must fail before promotion |
| `.RData` memory/disk pressure | Diagnostics need retained files, production should clean them | Keep only representative diagnostics; clean after reports/post |
| Pseudo-data capping changes the model | Caps may hide a deeper issue | Start with detection-only; cap only after targeted experiments |
| Standardizing transfer features changes comparability | CRPS grid may mix raw and standardized bundles | Record bundle hashes and scaling metadata; compare within manifest groups |
| Reduced transfer design changes scientific claim | Ablation meaning changes if features are dropped | Document as a separate model spec, not a silent repair |
| Failed lanes disappear from tables | Missing rows can look like success | Write explicit failure rows and reasons |

## Decision Tree

Use this tree after targeted experiments:

1. If new guards flag old bad fits and q80 controls pass, proceed to transfer repair experiments.
2. If guards do not flag old bad fits, stop and fix detection.
3. If standardized full transfer passes bad lanes and controls, promote standardized full transfer for AL-M-T0 diagnostics.
4. If standardized full transfer fails but standardized base transfer passes, promote the reduced design only if the scientific interpretation is acceptable.
5. If only no-transfer passes, AL-M-T0 with transfer is not promotable for the article. Keep it as a failed ablation or report no-transfer separately.
6. If no AL-M-T0 variant passes, exclude/flag that family and do not spend compute on broad relaunches.
7. If a promoted AL-M-T0 spec passes, run smoke tests, one full cutoff, and then all cutoffs with cleanup enabled.

## Immediate Implementation Checklist

Implement in this exact order:

1. Add/finish replay manifest for retained q35/q65/q80 diagnostics.
2. Make AL state guard effective and truthful in logs.
3. Add terminal saved-state health checks and artifacts.
4. Add latent/pseudo-data health checks and artifacts.
5. Add deterministic tests for the above.
6. Re-run replay checks on retained diagnostics.
7. Add transfer design diagnostics and optional standardization metadata.
8. Run targeted A0-A4 experiments first.
9. Decide whether A5-A7 are needed.
10. Promote only the stable, documented spec into publication relaunch manifests.

## What Not To Do

Do not:

1. Relaunch the full AL-M-T0 grid before guards and terminal checks are implemented.
2. Tune discount factors until impossible saved states are caught automatically.
3. Treat q80 controls as proof the family is safe; they show the workflow can recover in some lanes, not that q35/q65 are acceptable.
4. Promote outputs where historical `theta.out$exps` or transfer row 22 are impossible.
5. Delete retained diagnostic `.RData` files until replay checks and replacement reports are complete.
6. Mix raw-transfer and standardized-transfer outputs in winner selection without manifest labels.
7. Let failed lanes silently disappear from CRPS or ablation tables.

## Immediate Next Step

Implement Phase 1 and Phase 2 together:

1. make AL state guards effective and truthful in logs;
2. add terminal saved-state health checks for `theta.out$exps`, `theta.out$sm`, state blocks, and transfer row 22;
3. add deterministic tests proving q35/q65-style failures are rejected;
4. replay retained q35/q65/q80 outputs through the new health code.

This is the highest leverage first move because it prevents future silent promotion while preserving the ability to diagnose and tune the model scientifically.

## Drop Runner Post-Save Gate Fix - 2026-06-04

The A0-A4 diagnostic ladder exposed an implementation asymmetry between the two legacy multivariate
entrypoints. `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r` already honored
`DISC_W_POST_SAVE_OBJECTIVE_ENABLED` and `DISC_W_POST_SAVE_JSD_ENABLED`, but the active AL-M-T0 drop
entrypoint, `DISC_Optimal_Synth_Ranges_W.r`, still ran the old post-save JSD/objective block
unconditionally after saving `DISC_variables_*_exAL_synth_DISC.RData`.

Observed evidence:

- `diagnostic_20211221_dqlm_multivar_al_drop_q80_highdf_eps365_cf1_al_m_t0_20260603_a4_base_zscore`
  saved its RData successfully and then failed in
  `dmvnorm.deriv.unique -> chol2inv -> chol` because the optional post-save objective path received
  a non-positive-definite matrix.
- This is not a VB fit failure by itself; it is an optional legacy diagnostic failure occurring after
  the fit artifact is written.

Repair:

- `DISC_Optimal_Synth_Ranges_W.r` now defines the same post-save objective/JSD environment switches
  as the keep runner.
- Its post-save objective block now emits `[post_save_objective] disabled ...` and skips the old
  `objective_deltas(...)` call when `DISC_W_POST_SAVE_OBJECTIVE_ENABLED=FALSE`.
- Its post-save JSD block now emits `[post_save_jsd] disabled ...` and skips the KDE/JSD computation
  when `DISC_W_POST_SAVE_JSD_ENABLED=FALSE`.
- `tests/testthat/test_exdqlm_multivar_keep_latent_pseudodata_audit.R` now asserts that both the keep
  and drop legacy entrypoints expose the post-save switches and disabled log markers.

Validation:

- `Rscript --vanilla -e "invisible(parse('DISC_Optimal_Synth_Ranges_W.r')); invisible(parse('DISC_Optimal_Synth_Ranges_W_transfer_forecast.r')); cat('parse_ok\n')"`
- `Rscript --vanilla -e "library(testthat); test_file('tests/testthat/test_exdqlm_multivar_keep_latent_pseudodata_audit.R')"`

Operational consequence:

- Already-launched diagnostic lanes can still exit nonzero after saving because they started before this
  patch. For those lanes, terminal health should be replayed from the saved RData artifact rather than
  treating the post-save objective crash as a model failure.
- Future AL-M-T0 drop diagnostic launches should finish the fit stage cleanly when post-save objective
  and JSD are disabled in the unified config.

## Terminal Ladder Findings - 2026-06-04

The A0-A4 ladder completed with zero active processes and a complete terminal-health classification.
The full findings are recorded in
`docs/he2_al_m_t0_transfer_ladder_terminal_findings_20260604.md`.

Main conclusion:

- all q80 control lanes passed terminal health across the valid ladder;
- all q35/q65 suspect lanes failed terminal health across the valid ladder;
- `a1_transfer_level_only` still failed q35/q65, so the remaining instability is not solely caused by
  transfer covariate driver rows;
- the next diagnostic target should be the AL sigma/latent/state interaction, especially q35/q65 lanes.
