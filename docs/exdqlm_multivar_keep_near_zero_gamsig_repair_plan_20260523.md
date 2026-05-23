# exDQLM Multivariate Keep Near-Zero Gamma/Sigma Repair Plan

Date: 2026-05-23

Status: post-launch repair plan. Do not relaunch broad production until this plan's targeted gates pass.

## Purpose

The 2026-05-22 all-cutoff full-history promotion launch partially succeeded, but three cutoff rows failed before
post because one quantile lane in each row stopped at the gamma/sigma terminal update-count guard. This plan defines
the smallest rigorous fix path: repair the near-zero gamma handling, test it as a first-class algorithmic regime, run
targeted reproductions, and only then resume cutoff-level production.

This document supersedes the launch-readiness conclusion in
[exdqlm_multivar_keep_allcutoffs_fullhistory_promotion_readiness_20260522.md](/data/muscat_data/jaguir26/project1_ucsc_phd/docs/exdqlm_multivar_keep_allcutoffs_fullhistory_promotion_readiness_20260522.md)
until the repair gates below pass.

## Evidence Lock

Current branch at investigation time:

- `feature/export_posterior_tables`
- clean against `origin/feature/export_posterior_tables`

Current all-cutoff launch root:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_all_cutoffs_fullhistory_promotion_20260522`

Current monitor report:

`/data/muscat_data/jaguir26/project1_ucsc_phd/reports/he2_exdqlm_multivar_keep_allcutoffs_fullhistory_promotion_live_20260522/LIVE_STATUS.md`

Protected operation rule: this repair plan must not stop, modify, delete, or relaunch protected older production
runs. New tests and reproductions must use isolated roots.

## What Failed

The launch did not fail from pseudo-data guard breaches, latent caps, or a Kalman/state explosion. It failed because
three lanes repeatedly entered the near-zero gamma split path for forecast source `j=3`, failed to find an interior
split-branch candidate, refroze gamma/sigma, and then hit the hard terminal rule:

`gamsig_update_iters < DISC_GAMSIG_MIN_UPDATE_ITERS`.

| cutoff | failed lane | terminal iter | gamma/sigma updates | terminal error |
| --- | ---: | ---: | ---: | --- |
| `20210123` | `q35` | 100 | 16 / 50 | `stopped before required gamma/sigma updates` |
| `20211221` | `q20` | 100 | 21 / 50 | `stopped before required gamma/sigma updates` |
| `20220511` | `q20` | 100 | 17 / 50 | `stopped before required gamma/sigma updates` |

Direct evidence:

- `20210123 q35`: repeated `reason=near_zero` no-candidate events at
  [fit.log:287](/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_all_cutoffs_fullhistory_promotion_20260522/runs/multimodel_20210123_v8_he2pubgdpc1r1_exdqlm_multivar_keep/fit/exdqlm_multivar/keep/q=35/logs/fit.log:287),
  then terminal stop at
  [fit.log:699](/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_all_cutoffs_fullhistory_promotion_20260522/runs/multimodel_20210123_v8_he2pubgdpc1r1_exdqlm_multivar_keep/fit/exdqlm_multivar/keep/q=35/logs/fit.log:699).
- `20211221 q20`: repeated `reason=near_zero` no-candidate events at
  [fit.log:386](/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_all_cutoffs_fullhistory_promotion_20260522/runs/multimodel_20211221_v8_he2pubgdpc1r1_exdqlm_multivar_keep/fit/exdqlm_multivar/keep/q=20/logs/fit.log:386),
  then terminal stop at
  [fit.log:701](/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_all_cutoffs_fullhistory_promotion_20260522/runs/multimodel_20211221_v8_he2pubgdpc1r1_exdqlm_multivar_keep/fit/exdqlm_multivar/keep/q=20/logs/fit.log:701).
- `20220511 q20`: repeated `reason=near_zero` no-candidate events at
  [fit.log:295](/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_all_cutoffs_fullhistory_promotion_20260522/runs/multimodel_20220511_v8_he2pubgdpc1r1_exdqlm_multivar_keep/fit/exdqlm_multivar/keep/q=20/logs/fit.log:295),
  then terminal stop at
  [fit.log:690](/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_all_cutoffs_fullhistory_promotion_20260522/runs/multimodel_20220511_v8_he2pubgdpc1r1_exdqlm_multivar_keep/fit/exdqlm_multivar/keep/q=20/logs/fit.log:690).
- Live monitor shows `pseudo=0` for all lanes and finite state norms scaled by history length at
  [LIVE_STATUS.md:8](/data/muscat_data/jaguir26/project1_ucsc_phd/reports/he2_exdqlm_multivar_keep_allcutoffs_fullhistory_promotion_live_20260522/LIVE_STATUS.md:8).

Successful context:

- 32 of 35 quantile fits wrote usable `.RData` outputs.
- Two full cutoff rows, `20211112` and `20221225`, completed post/report and then cleaned `.RData` as expected.
- The three failed cutoff rows retained `.RData` only for the six lanes that passed before the cutoff-level abort.

## Active Code Path

The relevant active path is narrow:

1. Near-zero split decision:
   [R/disc_w/10_gamsig_laplace.R:58](/data/muscat_data/jaguir26/project1_ucsc_phd/R/disc_w/10_gamsig_laplace.R:58)
   returns `reason="near_zero"` when `abs(gamma_hat)` is below the configured threshold.
2. The promotion config sets the near-zero threshold to `abs_gamma_threshold=0.05` and
   `rel_support_threshold=0.02`; see generated config around
   [multimodel_20210123...yaml:245](/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_all_cutoffs_fullhistory_promotion_20260522/control/generated_configs/multimodel_20210123_v8_he2pubgdpc1r1_exdqlm_multivar_keep.yaml:245).
3. `update_gamma_sigma(...)` runs full and split candidates in
   [DISC_Optimal...r:2519](/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:2519)
   and rejects branch candidates that are not interior in
   [DISC_Optimal...r:2547](/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:2547).
4. If no split candidate is accepted, the current code logs a guard, attempts the median-only sigma fallback, and
   otherwise returns a guard fallback at
   [DISC_Optimal...r:2612](/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:2612).
   That fallback is not available to `q20` or `q35` because it is restricted to the median lane at
   [DISC_Optimal...r:2162](/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:2162).
5. A guard fallback triggers refreeze in the fit loop at
   [DISC_Optimal...r:4399](/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:4399).
6. `gamsig_update_iters` increments only when the gamma/sigma pass is not frozen at
   [DISC_Optimal...r:4437](/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:4437).
7. The hard terminal stop fires before posterior sampling at
   [DISC_Optimal...r:4708](/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:4708).

## Root-Cause Interpretation

The problem is not that near-zero gamma is inherently invalid. The problem is that the current implementation treats
one valid near-zero regime as a guard failure when the split-branch approximation cannot produce an interior
candidate.

In these failed lanes, the split search is doing what it was designed to do: it avoids placing a Laplace covariance
across the nondifferentiable `abs(gamma)` cusp. But when both sign-branch optima sit effectively on the zero
boundary, there is no accepted branch. The code then falls back to a guard path rather than a mathematically explicit
near-zero approximation. This freezes updates and starves the terminal update counter.

This is consistent with the log1p transformation history. The `log1p_cms` scale is larger than the old
`log(log1p(cms))` scale, and it can shift the fitted source-specific transfer/discrepancy balance enough that some
forecast-source gamma modes now land near zero. The repair target remains `log1p_cms`; reverting to the old
`loglog1p` scale is not the plan because near-zero retrospective values make that scale fragile.

## Non-Fixes To Avoid

Do not treat any of these as the primary repair:

1. Lowering `DISC_GAMSIG_MIN_UPDATE_ITERS` globally.
2. Increasing `DISC_GAMSIG_MAX_ITER` globally.
3. Disabling pseudo-data guards or latent caps.
4. Disabling the near-zero split check without replacing it with a tested near-zero approximation.
5. Deleting current `.RData` evidence before the failure report and targeted repair runs are complete.
6. Relaunching all 35 lanes before the three failed lanes pass isolated smokes.

Increasing `max_iter` alone is especially unlikely to help: the failed lanes repeatedly refroze after the same
near-zero no-candidate event and stayed below the minimum update count.

## Repair Design

### R1. Add First-Class Near-Zero Fallback

Implement a general, non-median fallback for `split_decision$reason == "near_zero"` when the full candidate is finite
but no split branch is acceptable.

Preferred implementation:

1. Add explicit config/env controls:
   - `DISC_GAMSIG_NEAR_ZERO_FALLBACK_ENABLED`, default `TRUE`;
   - `DISC_GAMSIG_NEAR_ZERO_FALLBACK_MODE`, default `sigma_only`;
   - `DISC_GAMSIG_NEAR_ZERO_GAMMA_ANCHOR`, default `full_candidate`, with allowed values `full_candidate`, `zero`,
     and `previous`.
2. Refactor the current median-only `run_sigma_only_fallback(...)` into a general helper:
   - optimize `theta_s` with a fixed `theta_g_anchor`;
   - return `build_mode_result(..., guard=FALSE, laplace_status="near_zero_sigma_only_fallback")`;
   - log `laplace_mode_search="near_zero_sigma_only:<anchor>"`.
3. Use that helper only when all of these gates hold:
   - split reason is exactly `near_zero`;
   - the full candidate is finite;
   - the full candidate's `abs(gamma_hat)` is below the configured near-zero threshold;
   - the objective at the fallback point is finite;
   - resulting point moments are finite and inside pseudo-data guard caps.
4. Keep the current guard fallback for:
   - nonfinite objective;
   - invalid Hessian unrelated to near-zero;
   - state guard events;
   - pseudo-data guard failures;
   - any near-zero fallback that cannot produce finite moments.

Why this is a root fix: near-zero gamma becomes a valid approximation branch with explicit moment semantics rather
than a guard/refreeze failure.

### R2. Add Explicit Counters And Logs

Add structured fields to logs and saved objects where feasible:

- `near_zero_fallback_count`;
- `near_zero_fallback_iters`;
- `last_near_zero_fallback_reason`;
- `laplace_status` and `laplace_mode_search` already exist and should carry the new labels;
- terminal preflight should report `near_zero_fallback_count` alongside `gamsig_update_iters`.

Acceptance rule: a lane may enter sampling with fewer split-Laplace updates only if it has enough finite
near-zero fallback updates and no pseudo-data/state guard failures. If the fallback is implemented as a non-frozen
gamma/sigma update, the existing `gamsig_update_iters >= min_update_iters` rule can remain the main terminal gate.

### R3. Keep Terminal Guard Strict For Real Failures

Do not weaken the terminal guard generally. Instead, make the near-zero fallback count as a real finite update only
after the checks in R1 pass. Terminal failures should still occur for:

- pseudo-data guard rows in `fail` mode;
- latent cap breaches that exceed policy;
- state guard/refreeze active at terminal sampling preflight;
- nonfinite sigma/gamma moments;
- non-near-zero optimizer/Hessian failures.

### R4. Preserve Existing Promotion Controls

Do not remove these currently useful guards:

- latent cap `mode: cap_e_inv_u`, `e_inv_u_cap=5000`;
- pseudo-data guard `mode: fail`;
- terminal sampling guard `mode: fail_fast`;
- post-save objective disabled by default;
- per-process thread caps;
- `.RData` cleanup after successful post.

## Tests To Add Or Extend

### Unit Tests

1. Extend [tests/testthat/test_disc_w_gamsig_laplace.R](/data/muscat_data/jaguir26/project1_ucsc_phd/tests/testthat/test_disc_w_gamsig_laplace.R)
   to cover:
   - near-zero threshold computation;
   - branch-bound construction around zero;
   - candidate rejection due to zero-boundary margin;
   - explicit expected decision when `reason="near_zero"`.
2. Add a small helper test for the new fallback policy function:
   - enabled/disabled behavior;
   - accepted `sigma_only` near-zero fallback when objective and moments are finite;
   - hard failure when finite gates are not met.
3. Add a source-level regression test proving the active runner contains:
   - `DISC_GAMSIG_NEAR_ZERO_FALLBACK_ENABLED`;
   - `laplace_status="near_zero_sigma_only_fallback"`;
   - terminal preflight logging of near-zero fallback count.

### Config And Bridge Tests

1. Extend [R/unified/config.R](/data/muscat_data/jaguir26/project1_ucsc_phd/R/unified/config.R) validation tests for
   new near-zero fallback fields.
2. Extend [R/unified/stages/stage_fit.R](/data/muscat_data/jaguir26/project1_ucsc_phd/R/unified/stages/stage_fit.R)
   bridge tests to prove generated YAML values become worker env vars.
3. Add generated-config tests for the all-cutoff promotion package so the near-zero fallback policy is frozen in
   generated configs.

### Log Parser And Monitor Tests

1. Extend [scripts/monitor_he2_exdqlm_multivar_keep_allcutoffs.py](/data/muscat_data/jaguir26/project1_ucsc_phd/scripts/monitor_he2_exdqlm_multivar_keep_allcutoffs.py)
   to parse:
   - `near_zero_fallback_count`;
   - `laplace_status` counts if available;
   - terminal stop reason.
2. Extend [tests/python/test_he2_exdqlm_keep_allcutoff_monitor.py](/data/muscat_data/jaguir26/project1_ucsc_phd/tests/python/test_he2_exdqlm_keep_allcutoff_monitor.py)
   with fixtures for:
   - near-zero fallback pass;
   - terminal update-count failure;
   - pseudo-data guard failure.

### Runtime Tests

All runtime tests must be isolated from existing production roots.

Required targeted fit-only smokes after implementation:

| smoke | purpose |
| --- | --- |
| `20210123 q35` | reproduces the worst current q35 near-zero no-candidate failure |
| `20211221 q20` | reproduces the first q20 near-zero no-candidate failure |
| `20220511 q20` | reproduces the second q20 near-zero no-candidate failure |
| `20221225 q20` | healthy q20 control |
| `20211112 q35` | healthy q35 control with gamma already near zero |

Smoke pass criteria:

1. fit reaches posterior sampling and writes `.RData`;
2. no pseudo-data guard rows in `fail` mode;
3. no latent cap exceedance beyond explicit policy;
4. no terminal state guard;
5. `gamsig_update_iters >= 50` or equivalent explicit near-zero finite-update terminal rule;
6. `laplace_status` shows the near-zero fallback only in the intended source/iterations;
7. ELBO/state/T/sigma/gamma remain in the same rough magnitude class as neighboring successful lanes.

## Runtime Rollout Sequence

### Phase A. Freeze Failure Evidence

Produce one untracked report under:

`reports/exdqlm_multivar_keep_near_zero_gamsig_failure_20260523/`

Required files:

- `lane_failure_summary.csv`;
- `near_zero_event_table.csv`;
- `terminal_preflight_table.csv`;
- `README.md` with the failure interpretation and links to the three failed logs.

No model fitting in this phase.

### Phase B. Implement Near-Zero Fallback

Tracked code changes:

1. `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r`
   - add config/env parsing;
   - generalize sigma-only fallback;
   - implement near-zero fallback branch;
   - add structured logs/counters.
2. `R/disc_w/10_gamsig_laplace.R`
   - add small pure helper(s) for near-zero fallback policy if practical;
   - keep branch-bound helpers unit-testable.
3. `R/unified/config.R`
   - add defaults and validation.
4. `R/unified/stages/stage_fit.R`
   - pass new policy into worker env.
5. `scripts/monitor_he2_exdqlm_multivar_keep_allcutoffs.py`
   - parse new fallback counters/status fields.

### Phase C. Run Deterministic Tests

Minimum validation commands:

```bash
Rscript --vanilla -e "invisible(parse('DISC_Optimal_Synth_Ranges_W_transfer_forecast.r')); cat('parse ok\\n')"
Rscript --vanilla -e "testthat::test_file('tests/testthat/test_disc_w_gamsig_laplace.R')"
Rscript --vanilla -e "testthat::test_file('tests/testthat/test_unified_gamma_sigma_state_refresh_schedule_config.R')"
python3 -m unittest tests.python.test_stage_fit_quantile_gamma_sigma_overrides -v
python3 -m unittest tests.python.test_he2_exdqlm_keep_allcutoff_monitor -v
python3 -m unittest tests.python.test_he2_publication_relaunch_builder_selection.HE2PublicationRelaunchBuilderSelectionTests.test_exdqlm_allcutoffs_fullhistory_promotion_batch_builds_guarded_configs -v
```

Add narrower commands if new tests are placed elsewhere.

### Phase D. Targeted Fit Smokes

Run only the five lane smokes listed above, in a new isolated root. Do not reuse or mutate the 2026-05-22 all-cutoff
root.

Required report:

`reports/exdqlm_multivar_keep_near_zero_gamsig_smoke_20260523/`

Required checks:

- lane-level health table;
- near-zero fallback event table;
- ELBO and gamma/sigma traces;
- pseudo-data guard summary;
- `.RData` presence table.

### Phase E. Failed-Cutoff Repair Rerun

Only after Phase D passes, rerun the three failed cutoff rows in a clean repair root:

- `20210123`
- `20211221`
- `20220511`

Use all seven quantiles per cutoff so the post stage has coherent quantile objects. Do not splice targeted single-lane
outputs into the existing failed cutoff roots.

Required pass criteria:

1. all seven quantile fits write `.RData` for each failed cutoff;
2. post/validate/report completes for each failed cutoff;
3. post cleanup removes `.RData` only after post success;
4. CRPS tables and held-out USGS forecast-window plots are produced;
5. monitor shows zero pseudo-data failures and no terminal fit errors.

### Phase F. Campaign-Level Decision

After Phase E:

1. If the three failed cutoffs pass and match the two already successful cutoffs, produce a campaign repair report
   and decide whether to publish the mixed evidence set or run one clean homogeneous all-five-cutoff relaunch.
2. If any targeted lane still fails, do not broaden. Inspect whether the failure is:
   - nonfinite objective;
   - true pseudo-data/latent guard;
   - state/Kalman failure;
   - identifiability/scientific calibration issue.

## Promotion Acceptance Criteria

The near-zero repair can be promoted only when all are true:

1. The three previously failed lanes pass isolated smokes.
2. Healthy controls remain healthy.
3. The three failed cutoffs pass full fit/post/validate/report in a new repair root.
4. No pseudo-data guard failures occur in promotion mode.
5. New near-zero fallback events are present only where expected and are documented.
6. ELBO, sigma/gamma, state/T, and selected state coordinates show no new divergence.
7. The final report lists all fallback counts by cutoff, quantile, source, and iteration.
8. All tracked docs/tests/scripts are committed; generated `reports/` remain untracked unless explicitly justified.

## Prioritized Fix List

| priority | fix | reason | gate |
| ---: | --- | --- | --- |
| 1 | Add tested near-zero gamma fallback for non-median lanes | Direct root cause of all three failures | unit tests plus three failed-lane smokes |
| 2 | Add fallback counters/status to logs and monitor | Prevent silent approximation drift | monitor fixture tests and runtime report |
| 3 | Keep terminal guard strict for real failures | Avoid hiding pseudo-data/state/Kalman failures | negative tests for pseudo/state failure |
| 4 | Rerun only failed lanes/cutoffs first | Avoid wasting 35 cores before root fix is proven | isolated targeted report |
| 5 | Decide mixed repair vs clean all-five relaunch | Publication/reproducibility decision after evidence | final campaign repair report |

## Open Questions

1. Should the default gamma anchor be `full_candidate` or exact `zero`?

   Initial recommendation: start with `full_candidate` for continuity, but include a deterministic diagnostic comparing
   `full_candidate` vs `zero` on the three failed lanes before broad promotion.

2. Should near-zero fallback update count toward `gamsig_update_iters`?

   Initial recommendation: yes, if and only if it returns finite point moments with `guard=FALSE`. This makes it a
   real finite approximation update, not a terminal-guard bypass.

3. Does this solve all scientific calibration concerns?

   No. It solves the observed operational failure mode. Tail-lane calibration and trend/transfer/discrepancy
   identifiability still require post-repair visual and CRPS review.

