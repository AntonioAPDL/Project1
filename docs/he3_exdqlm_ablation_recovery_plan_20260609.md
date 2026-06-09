# HE3 exDQLM Ablation Recovery Plan

Timestamp: 2026-06-09 UTC.

This note freezes the health check and recovery plan for the authoritative HE3
exDQLM multivariate ablation campaign rooted at:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he3_exdqlm_ablation_authoritative_winners_20260608`

The goal is to complete the HE3 ablation table using the selected exDQLM
multivariate keep winner specifications, with run-scoped post output, CRPS
summaries, audit outputs, and synchronized revised-article/corrections tables.

## Current Health Check

The active process check found no live HE3 queue, fit, post, or finish-gate
processes. Disk is healthy: `/data` has about `446G` free and is `49%` used.

Git state at the project repo was clean:

`feature/export_posterior_tables...origin/feature/export_posterior_tables [ahead 9]`

The static markdown status file is stale because the queue controller aborted
after detecting one failed row. The stale file reports:

| source | pass | pending | fail | not started |
|---|---:|---:|---:|---:|
| `matrix_status.md` | 17 | 3 | 1 | 9 |

Rebuilding the status frame from `matrix_plan.csv`, `matrix_metadata.yaml`, and
run manifests gives the current on-disk state:

| current computed state | rows |
|---|---:|
| pass | 20 |
| fail | 1 |
| not started | 9 |
| pending | 0 |

The three rows still listed as pending in the stale markdown are now pass by
manifest/output evidence:

| cutoff | variant | current phase | current status |
|---|---|---|---|
| 20210123 | `noH3` | report | pass |
| 20210123 | `noTrend` | report | pass |
| 20211221 | `noTrend` | report | pass |

Therefore we are no longer waiting on live work. The matrix is blocked by one
failed row and nine not-started rows.

## Blocked Rows

Current incomplete rows:

| cutoff | variant | run id | phase | status |
|---|---|---|---|---|
| 20210123 | `noTF` | `multimodel_20210123_v8_c04_eps365_exdqlm_multivar_keep_he3_noTF` | fit | fail |
| 20211221 | `noH1` | `multimodel_20211221_v8_c03_eps030_exdqlm_multivar_keep_he3_noH1` | not_started | not_started |
| 20211221 | `noH2` | `multimodel_20211221_v8_c03_eps030_exdqlm_multivar_keep_he3_noH2` | not_started | not_started |
| 20211221 | `noH3` | `multimodel_20211221_v8_c03_eps030_exdqlm_multivar_keep_he3_noH3` | not_started | not_started |
| 20211221 | `noTF` | `multimodel_20211221_v8_c03_eps030_exdqlm_multivar_keep_he3_noTF` | not_started | not_started |
| 20220511 | `noH1` | `multimodel_20220511_v8_c02_eps060_exdqlm_multivar_keep_he3_noH1` | not_started | not_started |
| 20220511 | `noH2` | `multimodel_20220511_v8_c02_eps060_exdqlm_multivar_keep_he3_noH2` | not_started | not_started |
| 20220511 | `noH3` | `multimodel_20220511_v8_c02_eps060_exdqlm_multivar_keep_he3_noH3` | not_started | not_started |
| 20220511 | `noTF` | `multimodel_20220511_v8_c02_eps060_exdqlm_multivar_keep_he3_noTF` | not_started | not_started |
| 20220511 | `noTrend` | `multimodel_20220511_v8_c02_eps060_exdqlm_multivar_keep_he3_noTrend` | not_started | not_started |

The queue stopped with:

`RuntimeError: HE3 queue aborting because rows failed: ['multimodel_20210123_v8_c04_eps365_exdqlm_multivar_keep_he3_noTF']`

## Completed-Row CRPS Evidence

The final HE3 summary builder should not be treated as complete until all 30
rows pass. Still, the completed row-local CRPS summaries are internally
available and useful for diagnosing whether the campaign is scientifically
behaving as expected.

Current completed rows with valid target-model CRPS:

| cutoff | variant | target model | mean CRPS | median CRPS |
|---|---|---|---:|---:|
| 20210123 | `full` | `exdqlm_multivar_synth_keep` | 0.139709 | 0.083939 |
| 20210123 | `noH1` | `exdqlm_multivar_synth_keep` | 1.278609 | 1.072538 |
| 20210123 | `noH2` | `exdqlm_multivar_synth_keep` | 0.726896 | 0.530998 |
| 20210123 | `noH3` | `exdqlm_multivar_synth_keep` | 1.082814 | 0.826174 |
| 20210123 | `noTrend` | `exdqlm_multivar_synth_keep` | 1.051592 | 0.796339 |
| 20211112 | `full` | `exdqlm_multivar_synth_keep` | 0.047236 | 0.044288 |
| 20211112 | `noH1` | `exdqlm_multivar_synth_keep` | 1.601420 | 1.598778 |
| 20211112 | `noH2` | `exdqlm_multivar_synth_keep` | 1.047240 | 1.047060 |
| 20211112 | `noH3` | `exdqlm_multivar_synth_keep` | 1.035625 | 1.022196 |
| 20211112 | `noTF` | `exdqlm_multivar_synth_drop` | 1.912852 | 1.925870 |
| 20211112 | `noTrend` | `exdqlm_multivar_synth_keep` | 0.723427 | 0.711027 |
| 20211221 | `full` | `exdqlm_multivar_synth_keep` | 0.265372 | 0.137032 |
| 20211221 | `noTrend` | `exdqlm_multivar_synth_keep` | 2.520427 | 2.386068 |
| 20220511 | `full` | `exdqlm_multivar_synth_keep` | 0.032325 | 0.026597 |
| 20221225 | `full` | `exdqlm_multivar_synth_keep` | 0.665460 | 0.576694 |
| 20221225 | `noH1` | `exdqlm_multivar_synth_keep` | 4.812205 | 4.754373 |
| 20221225 | `noH2` | `exdqlm_multivar_synth_keep` | 4.450271 | 4.404399 |
| 20221225 | `noH3` | `exdqlm_multivar_synth_keep` | 4.144780 | 4.080836 |
| 20221225 | `noTF` | `exdqlm_multivar_synth_drop` | 2.367420 | 2.309404 |
| 20221225 | `noTrend` | `exdqlm_multivar_synth_keep` | 3.866177 | 3.802873 |

Partial interpretation:

1. All completed ablation rows are worse than their cutoff's selected full
   exDQLM multivariate keep winner. This supports the intended HE3 scientific
   narrative, but it is still incomplete until the failed and not-started rows
   finish.
2. The completed `20210123` ablations already show large degradation without
   individual harmonics or trend. The missing `20210123/noTF` row is therefore
   important: it is the remaining transfer-function ablation for that cutoff.
3. The completed `20221225` ablations show very large degradation for every
   removed component. Transfer removal is less damaging than harmonic/trend
   removal for this cutoff, but still far worse than the full winner.
4. The `20211221` and `20220511` ablation evidence is too incomplete to rank
   components; those rows should not be interpreted yet.

## Failed Row Evidence

Failed row directory:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he3_exdqlm_ablation_authoritative_winners_20260608/runs/multimodel_20210123_v8_c04_eps365_exdqlm_multivar_keep_he3_noTF`

The failed row directory is small, about `8.2M`, and is not the source of the
disk pressure. Six quantile fits saved `.RData`; the failure is localized to
`q=50`.

Failed q50 log:

`fit/q=50/logs/fit.log`

Observed failure signature:

| item | evidence |
|---|---|
| first instability phase | repeated `[gamsig_guard] non-finite dq_transf` |
| fallback behavior | repeated `[gamsig_stabilization] sigma-only fallback accepted` |
| iteration range with bad state | iter 39 onward, visible through iter 46 |
| sigma | `sigma_exp=999.9447`, pinned at the effective upper boundary |
| gamma | `gamma_exp=-0.910777` |
| ELBO | `elbo=NA`, `crit_elbo=NA` |
| state norm | `state_norm_sq=NA`, `crit_state_norm_sq=NA` |
| freeze state | `frozen=false` |
| terminal error | `ww[j=1,t=1] eigen decomposition failed during SPD projection` |

The final observed progress line is:

`iter=46 elbo=NA sigma_exp=999.9447 gamma_exp=-0.910777 state_norm_sq=NA ... frozen=false`

Then the fit stops with:

`Error: ww[j=1,t=1] eigen decomposition failed during SPD projection`

## Implementation Path Analysis

The active legacy fit code reads the gamma/sigma max-iteration policy from
`DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:141-147`. For this run the
config sets `max_iter: 100`.

The same code reads `DISC_GAMSIG_STATE_GUARD_START_ITER` at
`DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:372-375`. The failed run config
sets `state_guard_start_iter: 1000`, while `max_iter: 100`.

The main state guard is activated only when:

`iter >= DISC_GAMSIG_STATE_GUARD_START_ITER`

See `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:5979-5980`.

The code already has the right rollback/refreeze behavior once the guard fires:

- non-finite state norm becomes a guard reason at
  `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:5991-5994`;
- rollback restores previous theta, latent state moments, gamma/sigma, and
  covariance objects at `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:6010-6057`;
- progress diagnostics are recorded at
  `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:6088-6111`;
- convergence checks require finite ELBO/state/sigma/gamma criteria at
  `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:6143-6150`.

However, because `state_guard_start_iter=1000` and `max_iter=100`, the guard
cannot fire during this run. That explains why the log can show
`state_norm_sq=NA` and `elbo=NA` while `frozen=false`, and why the bad state can
continue into the next covariance/SPD construction.

The terminal crash occurs in the SPD helper:

`DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:4719-4755`

That helper currently replaces non-finite matrix entries with zero before
symmetrization, then attempts Cholesky/eigen projection. This can mask the first
invalid value source and turn an upstream non-finite state into a later, less
informative eigen failure.

The Laplace gamma/sigma helper layer has moment and covariance validators in
`R/disc_w/10_gamsig_laplace.R:450-654` and robust covariance construction in
`R/disc_w/10_gamsig_laplace.R:660-781`. Those guards are useful, but they do not
by themselves guarantee that the later state-space covariance update remains
finite after a sigma-only fallback has been accepted.

## Root-Cause Assessment

This does not look like an input-bundle, article-sync, or post-stage problem. It
is a numerical robustness failure in the active exDQLM multivariate fit loop.

The strongest current root-cause hypothesis is:

1. The q50/noTF fit reaches a boundary gamma/sigma regime.
2. The guarded objective detects non-finite `dq_transf`.
3. The sigma-only fallback is accepted and keeps gamma/sigma deltas at zero.
4. The downstream state update produces non-finite ELBO/state norm.
5. The configured state guard is effectively disabled for 100-iteration runs
   because it starts at iter 1000.
6. The invalid state/covariance reaches `ww[j=1,t=1]` SPD projection and the fit
   dies with an eigen failure.

This is an interaction failure across layers, not a standalone post-processing
issue:

- gamma/sigma approximation hits boundary/non-finite objective evaluations;
- latent/state update produces `NA` state norm;
- covariance/SPD projection receives invalid state-space quantities;
- guard scheduling lets the invalid state continue instead of rolling back.

## Recovery Plan

### Phase 1: Freeze Evidence

Preserve the failed run directory and q50 logs. Do not delete this failed row
until the repaired row has passed and the matrix audit is complete.

Refresh status only after the repair path is ready, so the stale/pending rows are
not confused with the true failure.

### Phase 2: Patch the Fit Guard

Patch the active fit loop so non-finite core quantities are guarded
unconditionally, independent of delayed state-growth scheduling:

1. If `elbo`, `state_norm_sq`, `sigma_exp`, `gamma_exp`, or newly computed
   covariance/state moments are non-finite after an iteration, trigger
   rollback/refreeze immediately.
2. Keep ratio/absolute-cap state growth checks behind
   `DISC_GAMSIG_STATE_GUARD_START_ITER`, but never delay non-finite checks.
3. Ensure the rollback restores the previous coherent `theta.out`, `sts`, `uts`,
   gamma/sigma, and covariance lists before the next pseudo-data/state-space
   update.
4. Emit a clear `[gamsig_state_guard]` or `[gamsig_finite_guard]` reason, e.g.
   `non-finite elbo` or `non-finite state_norm_sq`.
5. Do not allow `prev_state_norm_sq <- NA` to poison later convergence criteria
   after a rollback.

### Phase 3: Harden SPD Diagnostics

Patch `disc_w_force_spd()` so non-finite input matrices fail fast with the label,
dimension, and non-finite count, instead of silently replacing non-finite values
with zero.

This is not the primary fix; it is a diagnostic hardening change. The primary
fix is to prevent invalid state/covariance from reaching SPD projection.

### Phase 4: Tests

Add focused deterministic tests:

| test | expected result |
|---|---|
| non-finite state norm in a 100-iteration policy with `state_guard_start_iter=1000` | rollback/refreeze still fires |
| non-finite ELBO after gamsig fallback | rollback/refreeze fires before convergence/update bookkeeping accepts the iteration |
| `disc_w_force_spd()` receives `NaN`/`Inf` input | fails with explicit non-finite diagnostic, not ambiguous eigen failure |
| HE3 generated configs | either set `state_guard_start_iter < max_iter` or rely on unconditional finite guard |

### Phase 5: Targeted Reproduction

Before resuming the full queue, run only the failed quantile:

| target | value |
|---|---|
| cutoff | 20210123 |
| variant | `noTF` |
| quantile | q50 |
| max iter | 100 |
| input bundle | existing HE3 authoritative bundle |
| cleanup | disabled until evidence is reviewed |

Pass criteria:

- no `NA` ELBO/state norm accepted as a live iteration;
- no `ww[j=1,t=1]` SPD eigen failure;
- q50 saves expected `.RData`;
- terminal health is finite and not obviously explosive.

### Phase 6: Relaunch Failed Row Only

After q50 passes, relaunch only:

`multimodel_20210123_v8_c04_eps365_exdqlm_multivar_keep_he3_noTF`

Then run row post-stage and validate/report for that row.

### Phase 7: Resume Matrix Queue

After the repaired `20210123/noTF` row passes, resume the queue for the nine
not-started rows. Do not rerun rows that already pass.

Expected remaining rows:

- `20211221`: `noH1`, `noH2`, `noH3`, `noTF`
- `20220511`: `noH1`, `noH2`, `noH3`, `noTF`, `noTrend`

### Phase 8: Finalize HE3 Table

When all 30 rows pass:

1. refresh `matrix_status.csv` and `matrix_status.md`;
2. run `scripts/build_he3_exdqlm_ablation_summary.py`;
3. run `scripts/audit_he3_exdqlm_ablation.py`;
4. run `scripts/sync_he3_ablation_article_tables.py`;
5. verify revised-article outputs under
   `Evironmetrics---REVISED-DOC-2/tables/generated_tex/` and
   `Evironmetrics---REVISED-DOC-2/artifacts/he3_exdqlm_ablation_authoritative/`;
6. verify corrections-repo table/text sync under
   `/data/muscat_data/jaguir26/Corrections---Project-1`;
7. clean large `.RData` only after summary, audit, and article sync are verified.

## Recommendation

Do not wait and do not blindly relaunch the whole matrix. The correct next move
is to patch the finite-state guard and SPD diagnostics, test those patches, and
then run a targeted q50 reproduction for the failed `20210123/noTF` row. Only
after that should the failed row and the nine not-started rows be launched.

## Repair Implemented on 2026-06-09

The repair is now implemented in the active legacy multivariate entrypoints and
the shared DISC-W helper loader. The first patch fixed the visible failure mode:
non-finite core iteration quantities were being accepted because the
state-growth guard was delayed beyond `max_iter`. The later diagnostic replays
showed a deeper interaction: the first finite q50 full-gamma move could remain
state-compatible at the end of its own iteration, but the following state update
exploded before a later gamma/sigma proposal could repair it. Therefore the
rollback payload itself had to be re-anchored, not merely the next proposal.

Tracked code changes:

| file | repair |
|---|---|
| `R/disc_w/09_fit_guards.R` | Adds shared finite-summary helpers, the iteration guard decision helper, a finite square-matrix assertion for SPD inputs, and `disc_w_reanchor_gamsig_to_gamma(...)` for coherent gamma-zero recovery. |
| `R/disc_w/_init.R` | Sources `09_fit_guards.R` before the Laplace gamma/sigma helpers. |
| `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r` | Uses the shared iteration guard in the active multivariate `keep` path; records finite-guard versus state-growth guard reasons; restores coherent ELBO/state/gamma/sigma payloads on rollback; re-anchors median q50/noTF state-compatible gamma/sigma payloads to gamma zero when the state guard proves the last full-gamma payload is incompatible; rejects non-finite SPD inputs before projection. |
| `DISC_Optimal_Synth_Ranges_W.r` | Applies the same finite-guard, recovery, and SPD input contract to the sibling multivariate DISC-W entrypoint so the two legacy paths do not diverge. |
| `R/unified/config.R` | Exposes the promoted gamma/sigma stabilization defaults and median-specific overrides used by the unified stage bridge. |
| `R/unified/stages/stage_fit.R` | Exports the guard, damping, median override, and recovery environment variables into the legacy fit process. |
| `tests/testthat/test_disc_w_fit_guards.R` | Adds deterministic tests for delayed-guard non-finite rollback, frozen-phase finite rollback, state-growth warmup gating, no-`na.rm` summary masking, finite SPD input diagnostics, and coherent pseudo-data moment recomputation under gamma-zero re-anchoring. |
| `tests/testthat/test_config_mode_resolution.R` | Locks the unified default/override configuration contract. |
| `tests/python/test_disc_sampling_diagnostics_source_contract.py` | Updates the source contract so both legacy entrypoints must use the shared finite guard, must expose gamma-zero re-anchoring, must not mask non-finite summaries with `na.rm`, and must not replace non-finite covariance entries with zero before SPD projection. |
| `tests/python/test_stage_fit_quantile_gamma_sigma_overrides.py` | Locks the stage-fit environment export contract for quantile-specific gamma/sigma and state-guard overrides. |

Important semantic choices:

1. Finite guards are unconditional once `theta_update` is true. They do not wait
   for `DISC_GAMSIG_STATE_GUARD_START_ITER`, and they are not bypassed during a
   gamma/sigma freeze window.
2. The absolute state-norm cap is now a hard safety guard. It does not wait for
   `DISC_GAMSIG_STATE_GUARD_START_ITER`, because a configured absolute cap should
   never allow a finite but explosive state payload to become the accepted
   iteration.
3. The state-growth ratio check remains gated by
   `DISC_GAMSIG_STATE_GUARD_START_ITER`, preserving the intended warmup policy
   for noisy but finite early relative jumps below the hard cap.
4. After a median q50 state-guard failure in a `noTF`/drop lane, the compatible
   rollback payload can be coherently re-anchored to `gamma=0`. This recomputes
   all downstream pseudo-data moments used by the Gaussian state update, not only
   `E.gam`.
5. Sigma-only fallback is damped after median state-guard recovery, so the
   recovery path cannot immediately jump sigma to the numerical boundary.
6. `disc_w_force_spd()` now fails fast on non-finite input matrices with the
   matrix label, dimension, and non-finite count. This is diagnostic hardening,
   not a substitute for the finite iteration rollback.
7. The ELBO trace rollback restores the previous coherent ELBO value rather
   than preserving the newly computed `NA` iteration. This prevents a rejected
   iteration from poisoning convergence criteria and progress summaries.

Diagnostic replay sequence:

| replay | key evidence |
|---|---|
| `r02` | Same HE3 input bundle and q50/noTF lane reached iter 12 with finite `elbo=-175.8278` but explosive `state_norm_sq=1.3803749e14`; proved the absolute cap must be hard, not delayed. |
| `r04`/`r05` | The SPD crash was prevented, but the run still stopped with `got=1 required=50`; rollback alone was not enough. |
| `r06`/`r07` | Adaptive hold/backoff exposed that the stored state-compatible snapshot could itself become the wrong baseline after the first q50 full-gamma move. |
| `r08` | Median state-guard sigma-only fallback activated, but without sigma damping it still jumped too aggressively. |
| `r09` | Sigma damping worked, but the next state update still reused the stale full-gamma rollback payload. This isolated the need to re-anchor the rollback payload itself. |
| `r10` | Gamma-zero re-anchoring of the state-compatible payload succeeded: q50 saved `.RData`, terminal health was `ok`, `state_norm_sq_per_T=1.7577689`, and the fit did not reach the previous `ww[j=1,t=1]` SPD failure. |

Validation completed:

| check | command | result |
|---|---|---|
| R parse | `Rscript --vanilla -e 'parse(file="R/disc_w/09_fit_guards.R"); parse(file="DISC_Optimal_Synth_Ranges_W_transfer_forecast.r"); parse(file="DISC_Optimal_Synth_Ranges_W.r"); parse(file="R/unified/stages/stage_fit.R"); parse(file="R/unified/config.R")'` | pass |
| focused R guard tests | `Rscript --vanilla -e 'testthat::test_file("tests/testthat/test_disc_w_fit_guards.R")'` | pass, 54 assertions |
| unified config tests | `Rscript --vanilla -e 'testthat::test_file("tests/testthat/test_config_mode_resolution.R")'` | pass, 116 assertions |
| source contract | `python3 -m unittest tests.python.test_disc_sampling_diagnostics_source_contract -v` | pass, 7 tests |
| stage-fit override contract | `python3 -m unittest tests.python.test_stage_fit_quantile_gamma_sigma_overrides -v` | pass, 3 tests |
| HE3 tooling parser gate | `python3 -m py_compile scripts/build_he3_exdqlm_ablation_matrix.py scripts/run_he3_exdqlm_ablation_queue.py scripts/finalize_he3_exdqlm_ablation.py scripts/build_he3_exdqlm_ablation_summary.py scripts/audit_he3_exdqlm_ablation.py scripts/sync_he3_ablation_article_tables.py scripts/he3_exdqlm_ablation_lib.py` | pass |

The successful q50 replay is:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he3_exdqlm_ablation_finiteguard_diagnostic_20260609/runs/multimodel_20210123_v8_c04_eps365_exdqlm_multivar_keep_he3_noTF_reanchor_q50_fitonly_20260609_r10`

Key runtime evidence:

| evidence file | result |
|---|---|
| `fit/q=50/logs/fit.log` | Logs `[gamsig_state_guard_recovery] ... recovery=median_zero_gamma_anchor sigma_exp=0.6576243 gamma_exp=0` at iter 12, later reaches `gamsig_update_iters=80`, completes sampling, and saves `DISC_variables_50_exAL_synth_simp.RData`. |
| `fit/q=50/outputs/multivar_terminal_state_health.txt` | `terminal_status=ok`, `violations=`. |
| `fit/q=50/outputs/multivar_forecast_health.txt` | `state_norm_sq=21610.01086`, `state_norm_sq_per_T=1.7577689`, `nonfinite_sm=0`, `max_abs_history_exps=3.511901363`, `max_abs_forecast_exps=3.007974874`, `max_E_sigma=0.8614459336`. |

Current matrix state after recomputing from manifests:

| status | rows |
|---|---:|
| pass | 20 |
| fail | 1 |
| not_started | 9 |

The failed row remains:

`multimodel_20210123_v8_c04_eps365_exdqlm_multivar_keep_he3_noTF`

The nine not-started rows are:

- `20211221`: `noH1`, `noH2`, `noH3`, `noTF`
- `20220511`: `noH1`, `noH2`, `noH3`, `noTF`, `noTrend`

## Promotion Plan After r10

1. Preserve the original failed `20210123/noTF` row until the repaired row has
   passed and the HE3 summary/audit outputs have been refreshed.
2. Reset only the failed `20210123/noTF` run directory and status, after moving
   the failed evidence into an explicit timestamped evidence folder.
3. Relaunch only `multimodel_20210123_v8_c04_eps365_exdqlm_multivar_keep_he3_noTF`
   under the existing authoritative HE3 config so all quantiles, post, validate,
   and report stages run with the promoted guard/reanchor code.
4. If that row passes, refresh `matrix_status.csv` and resume the HE3 queue for
   the nine not-started rows. Do not rerun the 20 rows that already pass.
5. After all 30 rows pass, run `scripts/finalize_he3_exdqlm_ablation.py` with
   article sync enabled. Use `--cleanup-rdata` only after summary, audit,
   revised-article assets, and corrections-repo outputs are verified.
6. Optionally delete the isolated r10 q50 `.RData` after the promoted row has
   passed; it is about `4.5G` and is diagnostic evidence, not a publication row.

Residual risk:

- The recovered q50/noTF lane is bounded and finite, but it still relies on the
  median gamma-zero recovery path after a state-guard event. That is acceptable
  for the no-transfer ablation because q50 has zero AL skew at the recovery
  anchor, but the full promoted row should still be inspected for repeated guard
  cycling before the nine remaining rows are resumed.

## Promotion Attempt 1 and Additional Root-Cause Fix

After commit `b7d3860`, the failed row was archived to:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he3_exdqlm_ablation_authoritative_winners_20260608/failed_evidence/reanchor_prepatch_failed_20260609T115625Z/multimodel_20210123_v8_c04_eps365_exdqlm_multivar_keep_he3_noTF`

The promoted row was then relaunched manually from:

`config/unified_runs_he3_exdqlm_ablation_authoritative_20260608/multimodel_20210123_v8_c04_eps365_exdqlm_multivar_keep_he3_noTF.yaml`

The row-level relaunch exposed a second first-iteration rollback bug. Extreme
lanes `q05`, `q20`, `q80`, and `q95` hit the hard absolute state cap at iter 1.
The guard correctly rolled the state back and activated a short latent hold, but
the next iteration attempted ELBO bookkeeping while the restored
`theta.out$elbo.part` baseline was zero-length. The failure signature was:

`Error in if (is.finite(prev_ELBO_iter) && is.finite(elbo)) : missing value where TRUE/FALSE needed`

This was not the original q50/gamma instability; it was an incomplete rollback
baseline for the newly generalized first-iteration hard-cap path. The robust
fix is:

1. add `disc_w_scalar_finite_or_default(...)` in `R/disc_w/09_fit_guards.R`;
2. treat a missing `new.theta.out$elbo.part` as zero during ELBO reconstruction;
3. coerce `ELBO`, `prev_ELBO_iter`, and reconstructed `elbo` to scalar finite
   values before convergence arithmetic;
4. during rollback, use a scalar fallback ELBO instead of preserving a
   zero-length baseline;
5. recompute rollback `state_norm_sq` from the restored `new.theta.out$sm`
   whenever possible, instead of forcing the previous `NA` placeholder through
   progress bookkeeping.

Validation for this incremental fix:

| check | command | result |
|---|---|---|
| R parse | `Rscript --vanilla -e 'parse(file="R/disc_w/09_fit_guards.R"); parse(file="DISC_Optimal_Synth_Ranges_W_transfer_forecast.r"); parse(file="DISC_Optimal_Synth_Ranges_W.r")'` | pass |
| focused R guard tests | `Rscript --vanilla -e 'testthat::test_file("tests/testthat/test_disc_w_fit_guards.R")'` | pass, 59 assertions |
| source contract | `python3 -m unittest tests.python.test_disc_sampling_diagnostics_source_contract -v` | pass, 7 tests |

The failed manual relaunch directory should be archived before the next relaunch,
then the same row should be rerun once more from the authoritative config.

## Promotion Attempt 2 and State-Norm Cap Scaling

After commit `655da41`, the row-level relaunch advanced past the
first-iteration rollback bug but exposed a third issue in the promoted hard-cap
policy. The hard cap was being applied to the total `state_norm_sq`, even though
all operational health checks and user-facing monitoring interpret state energy
as `state_norm_sq / T`, where `T` is the history length up to the cutoff.

This distinction matters for long history windows. In the archived prepatch row,
the extreme quantile lanes had large total state norms but ordinary normalized
state energy by the end of the successful lanes:

| lane | final `state_norm_sq` | final `state_norm_sq_per_T` |
|---|---:|---:|
| q05 | 5144190.653 | 418.430995 |
| q20 | 65278.37 | 5.31 |
| q35 | 60623.45 | 4.93 |
| q65 | 176477.05 | 14.35 |
| q80 | 226398.88 | 18.42 |
| q95 | 5957058.078 | 484.55 |

The promoted relaunch was therefore falsely guarding legitimate early extreme
lanes:

| lane | relaunch guard value | normalized by `T=12294` | interpretation |
|---|---:|---:|---|
| q05 | `state_norm_sq=33799896` | 2749.30 | large warmup state, not explosive |
| q20 | `state_norm_sq=1190504` | 96.84 | ordinary warmup state |
| q80 | `state_norm_sq=1606932` | 130.71 | ordinary warmup state |
| q95 | `state_norm_sq=35886283` | 2919.01 | large warmup state, not explosive |

By contrast, the original pathological q50 replay reached
`state_norm_sq=1.3803749e14`, which is about `1.1228e10` after division by
`T=12294`. That remains many orders of magnitude above a per-time cap of
`1e6`, so the corrected policy still catches the real instability.

The robust fix is to make the absolute cap scale explicit:

1. `R/disc_w/09_fit_guards.R` now accepts `state_norm_length` and
   `state_norm_abs_cap_scale`.
2. The default scale is `per_time`, so the hard cap compares
   `state_norm_sq / TT_sub` to the configured cap.
3. The old total-norm behavior remains reproducible by setting
   `DISC_GAMSIG_STATE_NORM_ABS_CAP_SCALE=total`.
4. Both multivariate legacy entrypoints pass `TT_sub` into the guard and log
   `state_norm_abs_cap_scale`.
5. `R/unified/config.R` exposes and validates
   `fit.exdqlm_multivar.gamma_sigma.stabilization.state_norm_abs_cap_scale`.
6. `R/unified/stages/stage_fit.R` exports
   `DISC_GAMSIG_STATE_NORM_ABS_CAP_SCALE` to the legacy fit worker.

This is a root-cause fix rather than a loosening patch: it keeps the hard cap on
the diagnostic scale used everywhere else in the workflow, separates legitimate
long-history warmup energy from true state explosion, and preserves an explicit
switch for old total-scale diagnostics.

Validation for this incremental fix:

| check | command | result |
|---|---|---|
| diff hygiene | `git diff --check` | pass |
| R parse | `Rscript --vanilla -e 'parse(file="R/disc_w/09_fit_guards.R"); parse(file="DISC_Optimal_Synth_Ranges_W_transfer_forecast.r"); parse(file="DISC_Optimal_Synth_Ranges_W.r"); parse(file="R/unified/stages/stage_fit.R"); parse(file="R/unified/config.R")'` | pass |
| focused R guard tests | `Rscript --vanilla -e 'testthat::test_file("tests/testthat/test_disc_w_fit_guards.R")'` | pass, 62 assertions |
| unified config tests | `Rscript --vanilla -e 'testthat::test_file("tests/testthat/test_config_mode_resolution.R")'` | pass, 118 assertions |
| source and stage-fit contracts | `python3 -m unittest tests.python.test_disc_sampling_diagnostics_source_contract tests.python.test_stage_fit_quantile_gamma_sigma_overrides -v` | pass, 10 tests |

The interrupted relaunch attempt that exposed this cap-scale issue had orphaned
workers in process groups `938748` and `945307`. They were stopped because they
were two partial writers to the same row directory, not a valid production run.
The directory should be archived as cap-scale evidence before the next clean
row-level relaunch.

## Promotion Attempt 3 Result and Health-Semantics Repair

After commit `5dc2c79`, the failed `20210123/noTF` row was relaunched from the
authoritative config:

`config/unified_runs_he3_exdqlm_ablation_authoritative_20260608/multimodel_20210123_v8_c04_eps365_exdqlm_multivar_keep_he3_noTF.yaml`

The run completed all required stages:

| stage | result |
|---|---|
| `data_prep_shared` | pass |
| `fit` | pass |
| `post` | pass |
| `validate` | pass |
| `report` | pass |

The completed run is:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he3_exdqlm_ablation_authoritative_winners_20260608/runs/multimodel_20210123_v8_c04_eps365_exdqlm_multivar_keep_he3_noTF`

Runtime evidence:

| evidence | result |
|---|---|
| Main relaunch log | `Unified run complete.` |
| Fit outputs | all seven quantiles saved final `.RData` before post |
| Cleanup | `Post-stage .RData cleanup: before=7 removed=7 remaining=0` |
| Manifest | `forecats=skip`, `data_prep_shared=pass`, `fit=pass`, `post=pass`, `validate=pass`, `report=pass` |
| q50 recovery | reached iter 100, sampled, saved, and post-processed after two median gamma-zero recovery events |
| post figures | cutoff-window synthesis PNG/PDF, raw-ensemble synthesis PNG/PDF, ELBO traces, gamma/sigma traces, transfer diagnostics, VB latent/pseudodata diagnostics |
| CRPS | `exdqlm_multivar_synth_drop` mean forecast CRPS `1.7360957277723663` for 28 valid forecast days |
| matrix state | `21 pass`, `9 not_started`, `0 fail` |

The repaired q50 lane is no longer the blocker. Its final health sidecar reports
`state_norm_sq_per_T=1.7577689`, `max_abs_history_exps=3.511901363`, and
`max_E_sigma=0.8614459336`.

The row-level post stage also revealed a separate reporting ambiguity. For the
`noTF` ablation, q05 and q95 have finite but large extreme-tail historical
`theta.out$exps` values:

| lane | `max_abs_history_exps` | `state_norm_sq_per_T` | old terminal label |
|---|---:|---:|---|
| q05 | 26.8492706941193 | 418.43099500521 | `fail` |
| q95 | 27.8503102245771 | 484.550030714071 | `fail` |

This pattern is not the q50 state explosion. It is also not a non-finite latent,
state, or pseudo-data failure: both lanes have `nonfinite_history_exps=0`,
`nonfinite_sm=0`, and state energy far below the `1e4` per-time cap. The same
pattern appears in other completed `noTF` rows, where q05/q95 exceed the older
history-latent diagnostic cap while the normalized state checks remain finite
and coherent.

The root issue is therefore terminology: `multivar_terminal_state_health.txt`
used `terminal_status=fail` for both hard numerical failures and soft
extreme-tail magnitude warnings. That made healthy-but-wide no-transfer extreme
quantile lanes look like broken fits in monitoring output.

The repair is to split terminal health severity:

1. `multivar_terminal_state_health.csv` now includes a `severity` column.
2. Hard numerical checks keep `severity=hard` and failed rows keep
   `status=fail`.
3. The historical `theta.out$exps` magnitude cap is retained as a warning
   diagnostic with `severity=warning` and `status=warn`.
4. `multivar_terminal_state_health.txt` now reports:
   - `terminal_status=fail` only when at least one hard check fails;
   - `terminal_status=warn` when only warning checks are exceeded;
   - explicit `hard_violations=...` and `warnings=...` fields.
5. Stage-fit log messages now distinguish `[FIT_FORECAST_HEALTH_WARN]` from
   `[FIT_FORECAST_HEALTH_FAIL]` when `forecast_health.fail_fast=false`.

This does not hide the q05/q95 behavior. It preserves the warning, keeps the
full value in the CSV, and prevents future HE3 monitoring from confusing a
soft noTF extreme-tail magnitude warning with the original q50 algorithmic
failure.

## Queue Resume Root Cause and Controller Fix

After the repaired `20210123/noTF` row passed, the matrix recomputed to:

| status | rows |
|---|---:|
| pass | 21 |
| not_started | 9 |
| fail | 0 |

The next intended step was to resume only the remaining nine rows. A detached
resume attempt created a PID file and zero-byte stdout log, but did not append a
new startup heartbeat to `queue.log` and left the same `21 pass` / `9
not_started` matrix state.

A foreground diagnostic run isolated the controller lifecycle problem. The
queue runner installed a custom `SIGHUP` handler, which defeated the launch
contract used for background/nohup controllers. The handler also used
`signum in signal.Signals`, which raises a Python 3.9 `TypeError` when a real
signal is delivered:

`TypeError: unsupported operand type(s) for 'in': 'int' and 'EnumMeta'`

This explains why a background resume could die without launching rows even
though the matrix itself was healthy. It was not a fit-stage failure and not a
new HE3 model instability.

The robust controller fix is:

1. introduce `signal_name(...)`, which maps a numeric signal to a name with
   `signal.Signals(signum)` and falls back to `SIG<signum>`;
2. treat `SIGTERM` and `SIGINT` as explicit terminating signals and log
   `action=terminate`;
3. treat `SIGHUP` as a logged non-terminal detach signal and log
   `action=ignored`;
4. test the behavior with real signal delivery in
   `tests/python/test_he3_exdqlm_ablation_tooling.py`.

This keeps intentional operator stops working while making detached queue
launches reliable. It also preserves the expected audit trail in `queue.log`.

## Live Resume Checkpoint After Controller Fix

Timestamp: 2026-06-09 15:36 UTC.

After commit `bdf6df9`, the HE3 queue was resumed from the existing matrix
without relaunching completed rows. The live controller is:

`python3 scripts/run_he3_exdqlm_ablation_queue.py --matrix-dir .../he3_exdqlm_ablation_authoritative_winners_v1 --artifact-root .../multimodel_v8_he3_exdqlm_ablation_authoritative_winners_20260608 --ordinary-max-concurrent 4 --heavy-cutoff-max-concurrent 1 --pause-free-gb 180 --launch-free-gb 220 --heavy-free-gb 240 --poll-seconds 60`

Process evidence at this checkpoint:

| item | evidence |
|---|---|
| controller | PID `970722`, session leader, alive for more than two hours |
| queue log | heartbeats append normally after the detached resume |
| disk gate | `/data` has about `301G` free, safely above launch and pause thresholds |
| matrix counts | `25 pass`, `4 pending`, `1 not_started`, `0 fail` |

Remaining rows are all in the final `20220511` cutoff group:

| cutoff | variant | phase | status | interpretation |
|---|---|---|---|---|
| 20220511 | `noH1` | validate | pending | fit/post completed; row-level validation still unwinding |
| 20220511 | `noH2` | fit | pending | all seven quantile fits reached iter 100 and all seven `.RData` files are finalized |
| 20220511 | `noH3` | not_started | not_started | waiting for the controller to free an active slot |
| 20220511 | `noTF` | post | pending | all seven `.RData` files saved; post diagnostics running |
| 20220511 | `noTrend` | post | pending | all seven `.RData` files saved; post diagnostics running |

The only suspicious symptom in the live check was `20220511/noH2`: for a period
the quantile logs had already reached `Sampling finished`, while the status
frame still showed zero expected `.RData` markers. A file-system pass resolved
that ambiguity. Six quantiles had already atomically moved final `.RData` files,
and q65 was still present as:

`DISC_variables_65_exAL_synth_DISC.RData.tmp.1023299`

with size about `6.2G`. A follow-up check found seven final `.RData` files and
zero temp files. Therefore this was a long atomic save/rename interval, not a
latent-variable, Kalman, gamma/sigma, or pseudo-data failure.

Operational conclusion: no additional model-code patch is justified by the live
resume evidence. The robust move is to let the controller finish the remaining
post/validate work, then let it launch `20220511/noH3`. If a later row becomes
`fail`, diagnose that row from logs and sidecars before relaunching anything.

## VB Latent Audit Robustness Fix

Timestamp: 2026-06-09 15:50 UTC.

The live `20220511/noH1` post stage exposed a reporting-only defect in the
optional VB latent/component audit:

`Error in aggregate.data.frame(lhs, mf[-1L], FUN = FUN, ...) : no rows to aggregate`

Evidence:

| file | evidence |
|---|---|
| `post/logs/post_runner.log` | post stage completed and wrote post artifact manifests, but emitted `multivar VB latent audit failed with status 1` |
| `vb_latent_component_audit/audit_rscript.log` | audit loaded q05 through q95 and failed after q95 |
| `vb_latent_component_audit/audit_rscript.err` | aggregation error: `no rows to aggregate` |
| `multivar_vb_latent_audit_status.csv` | `ok=FALSE`, `exit_status=1` |

This is not a fit instability and not a CRPS/post-output failure. The root cause
is in `scripts/audit_exdqlm_multivar_keep_vb_latents.R`: `spec_from_run_id(...)`
only parsed older `_he2grid_<case>_<epsilon>_` run IDs. HE3 ablation run IDs
such as `multimodel_20220511_v8_c02_eps060_exdqlm_multivar_keep_he3_noH1`
therefore received `spec=NA`. Downstream `aggregate(value ~ .)` calls used
`spec` as a grouping column, and base R dropped all rows with missing grouping
values before aggregation.

The robust fix is:

1. parse HE3 run IDs with `_v8_<case>_<epsilon>_exdqlm` as well as legacy
   `_he2grid_<case>_<epsilon>_`;
2. normalize missing character/factor grouping fields to an explicit
   `__missing__` label before diagnostic aggregation;
3. return an empty diagnostic table instead of throwing if an aggregation is
   genuinely empty after filtering;
4. allow the audit helper script to be sourced in tests without executing
   `main()`;
5. add a focused test in `tests/testthat/test_vb_latent_audit_helpers.R`.

This prevents intentionally absent ablation components or unrecognized spec
labels from crashing a diagnostic report. It does not alter the model fit, post
CRPS, synthesis figures, or publication tables.

## Final Matrix Completion And Runtime Input Contract Fix

Timestamp: 2026-06-09 16:50 UTC.

The resumed HE3 controller completed all rows:

| status | rows |
|---|---:|
| pass | 30 |
| pending/not started/fail | 0 |

The final `20220511/noH3` row behaved as expected:

1. all seven quantiles reached iteration 100 with no finite/state guard
   failures;
2. all seven `.RData.tmp.*` files atomically resolved into final `.RData`
   outputs;
3. post generated CRPS tables, synthesis figures, q50 traces, transfer
   diagnostics, and the VB latent/component audit;
4. the VB latent audit loaded q05 through q95 and completed with zero-byte
   stderr;
5. row-local `.RData` files were removed by the workflow cleanup path after
   post/report completion.

The controller then ran the completion hooks:

1. `scripts/build_he3_exdqlm_ablation_summary.py`;
2. `scripts/audit_he3_exdqlm_ablation.py`;
3. `scripts/sync_he3_ablation_article_tables.py`.

The explicit finalizer gate initially refused to complete because
`scripts/audit_he3_exdqlm_ablation.py` compared all runtime inputs with raw
SHA-256 hashes. Fifteen launched ablation rows were marked non-ok only for:

`inputs:hash:fit/inputs/retros_fit_adapter.csv`

The affected cutoffs were `20210123`, `20211112`, and `20221225`, all five
launched variants per cutoff. A parsed CSV comparison showed:

| check | result |
|---|---|
| shape | identical |
| column names | identical |
| `Date` values | identical |
| missingness | identical |
| numeric values | identical after parsing, max absolute difference `0` |
| raw bytes | different because numeric writer precision dropped trailing digits |

Example byte-level difference:

| source full run | HE3 ablation run |
|---|---|
| `0.00995033063186363` | `0.0099503306318636` |

Therefore the finalizer failure was a reproducibility-audit contract bug, not
an input-bundle, model, post, or CRPS failure.

The robust fix is:

1. keep strict SHA-256 equality as the first check for every runtime input;
2. allow generated numeric adapter CSVs
   (`retros_fit_adapter.csv`, `nws_fit_adapter.csv`, `glofas_fit_adapter.csv`)
   to pass by canonical parsed-CSV equality when raw hashes differ;
3. require matching schema, row count, missingness, text/date fields, and
   numeric values within absolute tolerance `1e-12`;
4. write `audit/he3_ablation_runtime_input_detail.csv` and `.md` so every
   raw-hash or canonical-equivalence decision is visible;
5. make the finalizer require that runtime-detail table;
6. copy the runtime-detail table into the article-side HE3 artifact bundle when
   synchronizing tables.

The focused regression test is:

`tests/python/test_he3_exdqlm_ablation_tooling.py::He3ToolingTests::test_runtime_input_audit_accepts_canonical_numeric_adapter_precision_only`

It verifies that writer-precision drift passes canonically, while a real
numeric value change still fails the runtime input contract.
