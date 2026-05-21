# exDQLM Multivariate Keep Repair And Transform Regression Plan

Date: 2026-05-21

## Purpose

This document is the repair plan that follows the full multivariate `exdqlm keep` audit. It is deliberately
implementation-focused: every proposed fix or test below is tied to the canonical theory, the active code path, or
runtime evidence produced by the audit.

The live step-by-step execution tracker for this plan is:

[exdqlm_multivar_keep_repair_tracker.md](/data/muscat_data/jaguir26/project1_ucsc_phd/docs/exdqlm_multivar_keep_repair_tracker.md)

The tracker is the place to update phase status, evidence paths, validation commands, and promotion readiness after
each work item.

The new hypothesis added on 2026-05-21 is important:

> The model reportedly behaved acceptably before the output/input analysis transform was changed from
> `log_log1p_cms` to `log1p_cms`. The current instability may therefore be a scale-regression problem: the active
> exAL latent updates, `sigma/gamma` approximation, pseudo-data construction, and state-space update are mostly
> algebraically coherent, but they may no longer be numerically calibrated for the larger `log1p` dynamic range.

This is not yet a proven root cause. The plan below is designed to prove or falsify it with small, reproducible
checks before any broad production relaunch.

Important clarification added on 2026-05-21: the repair target is the current `log1p_cms` contract. The old
`log_log1p_cms` behavior is useful only as a diagnostic comparator, not as the preferred fix. One reason is practical
and legitimate: retrospective series can contain raw zeros or values whose `log1p(cms)` values are zero or very close
to zero, and `log(log1p(cms))` is then undefined or very large negative. A future `log1p(log1p(cms))` transform could
be evaluated as a separate modeling choice, but this plan is scoped to making `log1p_cms` robust.

## Current Diagnosis

The completed audit found an interactional failure, not a single isolated layer that explains everything.

Confirmed from [exdqlm_multivar_keep_final_findings.md](/data/muscat_data/jaguir26/project1_ucsc_phd/docs/exdqlm_multivar_keep_final_findings.md):

1. The active state-space, ensemble/member, latent conditional, pseudo-data, and historical Kalman contracts are
   mostly coherent against the canonical theory and current implementation.
2. One concrete production-code bug was found and patched: forecast-member `update_uts` now indexes forecast
   expectation columns using `TT_sub` instead of bare `T` at
   `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:4001-4002` and
   `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:4694-4695`.
3. The `s_t` entropy calculation was wrong for a positive-truncated normal and used base-2 logs. It is now fixed
   in commit `4bbb643`: active `disc_w_pos_truncnorm_moments` uses the natural-log positive-truncated-normal
   entropy at `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:1821-1839`, and `update_sts` sums that entropy at
   `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:1853-1860`.
4. Runtime failures show extreme latent moments and pseudo-data before the Kalman layer can be blamed alone.

Key runtime evidence from
[exdqlm_multivar_keep_runtime_stability_audit.md](/data/muscat_data/jaguir26/project1_ucsc_phd/docs/exdqlm_multivar_keep_runtime_stability_audit.md):

| lane | target max E[s] | target max E[s^2] | target max E[1/u] | FFF range | QQQ diag max | total state norm sq |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| q05 | 0.666 | 0.636 | 158.8 | [15.01, 20.54] | 0.145 | 5.403e5 |
| q35 | 42.35 | 1793.10 | 2098.77 | [-166.25, 232.88] | 3187.14 | 1.137e8 |
| q50 | 6.13 | 37.54 | 7057.22 | [-3245.82, 67.07] | 859.39 | 1.125e10 |
| q95 | 23.60 | 556.75 | 9480.96 | [-789.36, 99.51] | 1435.99 | 1.447e8 |

The q50 lane is the most diagnostic: the pseudo-data offset reaches `-3245.82`, `E[1/u]` reaches `7057.22`, and
the state norm reaches `1.125e10`. These values are from the untracked report directory:

`reports/exdqlm_multivar_keep_runtime_stability_2017_ready_q05_q35_q50_q95_20260520/`

## Implementation Checkpoint 2026-05-21

This section records what has now moved from plan to implementation and the first guarded runtime result.

Implemented and committed:

1. `eb22e6e`: forecast-member `update_uts` indexing fix (`TT_sub` instead of bare `T`).
2. `be5cf55`: transform-regression forensics and `log1p_cms` scale-contract tests.
3. `4bbb643`: stable `s_t` moments/entropy, closed-form half-order `u_t` moments, and pre-Kalman pseudo-data guards.
4. `5a83162`: guarded repro launcher, corrected runtime `E[log u]` summaries, and an env switch for the expensive
   post-save objective diagnostic.
5. `869c9c2`: guarded keep run monitor.
6. `docs/exdqlm_multivar_keep_guarded_repro_20260521.md`: tracked evidence summary for the isolated guarded
   q05/q35/q50/q95 reproduction.

Active code anchors after implementation:

1. Positive-truncated-normal `s_t` moments and entropy:
   `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:1821-1860`.
2. Half-order GIG `u_t` moments:
   `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:1863-1911`.
3. Pseudo-data guard policy:
   `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:3456-3484`.
4. Post-save objective switch:
   `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:649-663` and
   `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:5189-5196`.
5. Isolated guarded reproduction generator:
   `repro/audits/prepare_exdqlm_keep_guarded_repro.py:42-155`.
6. Runtime audit normalization for stored summed `E[log u]` terms:
   `repro/audits/exdqlm_keep_runtime_stability_audit.R:168-216` and `:343-394`.
7. Guarded run monitor:
   `repro/audits/summarize_exdqlm_keep_guarded_run.py:55-116` and `:140-198`.

Tests run after implementation:

1. `Rscript --vanilla -e "invisible(parse('DISC_Optimal_Synth_Ranges_W_transfer_forecast.r')); cat('parse ok\n')"`
   passed.
2. `Rscript --vanilla -e "testthat::test_file('tests/testthat/test_exdqlm_multivar_keep_latent_pseudodata_audit.R')"`
   passed with 45 expectations.
3. `Rscript --vanilla -e "testthat::test_file('tests/testthat/test_exdqlm_transform_scale_sensitivity.R')"` passed
   with 10 expectations.
4. `Rscript --vanilla -e "testthat::test_file('tests/testthat/test_scale_contract_adapters.R')"` passed with
   13 expectations.
5. `Rscript --vanilla -e "testthat::test_file('tests/testthat/test_exdqlm_runtime_stability_audit.R')"` passed
   with 8 expectations.
6. `python3 -m unittest tests.python.test_log1p_transform_policy -v` passed with 6 tests.
7. `python3 -m py_compile repro/audits/prepare_exdqlm_keep_guarded_repro.py` passed.
8. `python3 -m py_compile repro/audits/summarize_exdqlm_keep_guarded_run.py` passed.

Smoke evidence:

1. Isolated smoke root:
   `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/exdqlm_keep_smoke_guarded_log1p_phase_cd_20260521/`.
2. Smoke report:
   `reports/exdqlm_keep_guarded_repro_smoke_guarded_log1p_phase_cd_20260521/`.
3. q05 and q50 both wrote `.RData` outputs and the read-only runtime report was generated at
   `reports/exdqlm_keep_guarded_repro_smoke_guarded_log1p_phase_cd_20260521/runtime_stability/`.
4. No pseudo-data guard event CSV was written in the smoke report directory, which means the configured guard
   thresholds were not crossed in that short run.
5. The q05 smoke process was manually terminated after the `.RData` output and runtime report were written because
   it was spending CPU in the old post-save 3D KDE/JSD diagnostic. Commit `5a83162` adds
   `DISC_W_POST_SAVE_OBJECTIVE_ENABLED=0` for isolated repros so this does not block the overnight q-lane run.

Completed guarded q-lane reproduction:

1. Prepared by:
   `python3 repro/audits/prepare_exdqlm_keep_guarded_repro.py --tag guarded_log1p_q05_q35_q50_q95_20260521 --max-iter 3000 --workers 4 --quantiles 0.05,0.35,0.5,0.95 --guard-mode warn`.
2. Runtime root:
   `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/exdqlm_keep_guarded_log1p_q05_q35_q50_q95_20260521/`.
3. Report root:
   `reports/exdqlm_keep_guarded_repro_guarded_log1p_q05_q35_q50_q95_20260521/`.
4. Launch policy: pseudo-data guards are enabled in warn mode, and post-save objective diagnostics are disabled.
5. Final live monitor evidence:
   `reports/exdqlm_keep_guarded_repro_guarded_log1p_q05_q35_q50_q95_20260521/live_monitor/LIVE_STATUS.md`.
6. Runtime stability report:
   `reports/exdqlm_keep_guarded_repro_guarded_log1p_q05_q35_q50_q95_20260521/runtime_stability/`.
7. Tracked summary:
   [exdqlm_multivar_keep_guarded_repro_20260521.md](/data/muscat_data/jaguir26/project1_ucsc_phd/docs/exdqlm_multivar_keep_guarded_repro_20260521.md).

Fit outcome:

| lane | iter | terminal state norm sq | sigma exp | gamma exp | output bytes |
| --- | ---: | ---: | ---: | ---: | ---: |
| q05 | 3000 | 1521.116 | 0.04159479 | 0.8357179 | 614403137 |
| q35 | 3000 | 2233.589 | 0.1136433 | 0.1103588 | 615356651 |
| q50 | 1079 | 2547.352 | 0.1227996 | -0.01111135 | 614988494 |
| q95 | 3000 | 5082.421 | 0.07100852 | -1.762717 | 615690228 |

The prior q50 failure had state norm squared `1.125e10`; this guarded q50 run ended at `2547.352`. That is a
material stabilization, but not a single-cause proof because multiple fixes were active together.

Guard outcome:

1. 18 guard rows were written.
2. All rows were q05 historical `E_inv_uts`, iterations 1001-1018.
3. The peak was `14397.595` at iteration 1005 with cap `5000`.
4. No rows were written for `FFF`, `QQQ_diag`, forecast pseudo-data, `E[s]`, `E[s^2]`, or `E[u]`.

The wrapper exited nonzero after fit outputs were written because the isolated post-stage figure path had no USGS
truth rows available at/after `2022-12-26`. This is a post-stage gating problem to fix separately, not evidence that
the exDQLM fit failed.

## Active Theory And Code Anchors

Canonical theory source:

1. `/data/muscat_data/jaguir26/exDQLM---Ensemble/main.tex:323-342` gives the GIG conditional for `v_t`/`u_t`.
2. `/data/muscat_data/jaguir26/exDQLM---Ensemble/main.tex:344-360` gives the positive-truncated normal conditional
   for `s_t`.
3. `/data/muscat_data/jaguir26/exDQLM---Ensemble/main.tex:947-967` gives the information-form pseudo-data rule
   `bar y = b / w`, `bar R = 1 / w`.

Active implementation anchors:

1. `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:1296-1314` reads forecast adapters and now keeps them on
   `log1p(cms)`.
2. `R/disc_w/03_covariates_standardize.R:138-147` reads retrospective `USGS`, `GloFAS`, and `NWS3.0`, then keeps the
   matrix `Y` on `log1p(cms)` without a second log.
3. `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:1795-1815` implements `update_sts`.
4. `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:1833-1879` implements `update_uts`.
5. `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:3539-3587` constructs historical and forecast `FFF`/`QQQ`.
6. `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:3670-3679` calls the compiled Kalman path.

Scale-contract implementation anchors:

1. `R/unified/utils_scale.R:3-43` defines the allowed scale conversions.
2. `R/unified/utils_scale.R:55-79` implements `unified_adapt_csv_scale`.
3. `R/unified/config.R:490-495` currently sets all fit/post internal scales to `log1p_cms`.
4. `R/unified/config.R:1593-1607` rejects `log_log*` internal scales in the current workflow.
5. `R/unified/stages/stage_fit.R:420-450` adapts retrospectives and forecasts to the fit legacy scale.
6. `R/unified/stages/stage_post.R:175-202` adapts retrospectives and forecasts to the post legacy scale.

## Transform Regression Evidence

The key git-history commit is:

`44e2d60cd41ba29468563668b87b0a32270dde42 Enforce log1p-only transform policy`

This commit made four changes that are directly relevant to the current instability investigation:

1. In `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r`, it removed:
   - `nws_forecast[,-1] <- log(nws_forecast[,-1])`
   - `glofas_forecast[,-1] <- log(glofas_forecast[,-1])`

   The current code instead states that forecast adapters already provide `log1p(cms)` and should remain on that
   scale (`DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:1296-1310`).

2. In `R/disc_w/03_covariates_standardize.R`, it removed:
   - `Y <- log(Y) # log-log, since already logged`

   The current code instead keeps retrospective `USGS`, `GloFAS`, and `NWS3.0` on `log1p(cms)` and explicitly says
   not to apply a second log (`R/disc_w/03_covariates_standardize.R:138-147`).

3. In `R/unified/config.R`, it changed:
   - `analysis_scale_fit_internal = "log_log1p_cms"`
   - `analysis_scale_post_internal = "log_log1p_cms"`

   to:
   - `analysis_scale_fit_internal = "log1p_cms"`
   - `analysis_scale_post_internal = "log1p_cms"`

   Historical check: `git grep` at `44e2d60^` shows the old defaults at `R/unified/config.R:405-406`. The current
   defaults are at `R/unified/config.R:490-495`.

4. In `R/unified/stages/stage_fit.R` and `R/unified/stages/stage_post.R`, it changed the scale-adapter
   `positive_required` flag from `TRUE` to `FALSE` for retrospectives, NWS, and GloFAS. Current fit anchors are
   `R/unified/stages/stage_fit.R:430-450`; current post anchors are `R/unified/stages/stage_post.R:182-202`.

The scale change is mathematically large. For raw flow `x`, the old internal analysis scale was approximately
`log(log1p(x))`, while the current scale is `log1p(x)`.

| raw cms x | log1p(x) | log(log1p(x)) | scale ratio log1p / loglog1p |
| ---: | ---: | ---: | ---: |
| 10 | 2.398 | 0.875 | 2.74 |
| 100 | 4.615 | 1.529 | 3.02 |
| 1000 | 6.909 | 1.933 | 3.57 |
| 10000 | 9.210 | 2.220 | 4.15 |

The old scale is also fragile near zero:

| raw cms x | log1p(x) | log(log1p(x)) | interpretation |
| ---: | ---: | ---: | --- |
| 0 | 0 | `-Inf` | impossible without flooring or special handling |
| 1e-6 | 1.000e-6 | -13.816 | finite but extremely negative |
| 0.001 | 9.995e-4 | -6.908 | finite but highly compressed and negative |
| 0.1 | 0.0953 | -2.350 | finite but still negative |

This near-zero behavior is why the plan should not quietly revert to `log_log1p_cms`. The current target is to make
`log1p_cms` stable by repairing numerical conditioning, guards, and calibration.

This can turn a stable old-scale residual into a much larger current-scale residual. Because the exAL latent updates
depend on residuals and residual squares, the effect can be amplified:

1. `update_sts` uses `(y - exps)` in `s.mu`
   (`DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:1802-1809`).
2. `update_uts` uses `y^2 - 2*y*exps + exps2` and `sts*(y-exps)` in `u.chi`
   (`DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:1833-1839`).
3. `FFF` combines `E[s]`, `E[1/u]`, and `sigma/gamma` expectations
   (`DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:3539-3558`).
4. `QQQ` is inversely proportional to `E[1/u]` times `E[1/(b sigma)]`
   (`DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:3540-3558`).

So the most likely transform-regression mechanism is:

`log1p` larger residuals -> more aggressive `s_t` and `u_t` moments -> distorted `FFF`/`QQQ` pseudo-data -> Kalman
state update follows the pseudo-data -> weakly identified trend/transfer/discrepancy blocks absorb unstable signal.

The competing explanation is also plausible:

The log1p scale may be statistically correct and the old log-log scale may simply have hidden a latent numerical
fragility by over-compressing the data. In that case the fix is not to revert the transform, but to make the latent
moments, pseudo-data guardrails, priors, and `sigma/gamma` approximation robust on the intended `log1p` scale.

## Target Scale Decision

The implementation target is:

1. historical `USGS`, retrospective GloFAS, and retrospective NWS on `log1p_cms`,
2. NWS and GloFAS forecast members on `log1p_cms`,
3. model fit internals on `log1p_cms`,
4. post and plotting outputs explicitly labeled as `log1p_cms` unless converted for display.

Non-goals for this repair cycle:

1. do not restore `log_log1p_cms` as the active internal scale,
2. do not introduce `log1p(log1p(cms))` until the `log1p_cms` path has been tested and repaired,
3. do not use flooring around `log(log1p(cms))` as a hidden production workaround,
4. do not tune plots or posterior display code as a substitute for fixing fit-stage instability.

The old log-log path remains useful only for controlled comparison:

1. to quantify how much compression changed the latent moments,
2. to test whether previous stability came from scale compression,
3. to identify which layer first becomes unstable when moving back to `log1p_cms`.

## Implementation Readiness

The first implementation sequence is complete. We are ready for targeted ablations and promotion-hardening work, but
not for a broad production relaunch.

The recommended next step is a small curated evidence bundle from the already-written guarded `.RData` outputs,
followed immediately by causal ablations. We should not generate every possible summary PNG unless a specific report
or presentation needs it.

Completed:

1. Phase A transform forensics and static scale-contract tests.
2. Phase B deterministic scale-sensitivity fixtures, including near-zero retrospective cases.
3. Phase C latent moment robustification for `s_t` entropy and `u_t` numerical stability.
4. Phase D pre-Kalman `FFF`/`QQQ` guards in warning mode first.
5. A guarded q05/q35/q50/q95 `log1p` reproduction with all four fit outputs written.

Not ready yet:

1. broad production relaunches,
2. final `sigma/gamma` retuning,
3. switching to a new transform such as `log1p(log1p(cms))`,
4. claiming a single root cause before fixed/free `sigma/gamma` and latent ablations are run,
5. promoting warning-mode guard thresholds to production without a decision on q05-like `E[1/u]` bursts.

The safest remaining execution order is:

1. create the curated evidence bundle from existing guarded outputs,
2. design the ablation harness,
3. run fixed/free `sigma/gamma` ablations,
4. run fixed/free latent moment ablations,
5. tune or harden the `E[1/u]` guard response,
6. add component decomposition traces,
7. extend the Kalman fixture to ragged forecast `keep`,
8. gate the post-stage truth-window failure,
9. only then decide whether `sigma/gamma` priors, damping, or refresh schedules need recalibration for production.

## Repair Principles

1. Do not relaunch or modify existing production campaigns during this repair sequence.
2. Do not use old documentation as proof unless it matches both canonical theory and active implementation.
3. Use deterministic fixtures before runtime reproductions.
4. Keep large runtime outputs under `reports/` and out of commits by default.
5. Prefer narrow q-lane reproductions over broad campaign relaunches.
6. Every promoted fix must have:
   - a theory/code citation,
   - a unit or fixture test where feasible,
   - a runtime acceptance criterion,
   - a rollback story if behavior worsens.

## Phase A: Transform Forensics And Scale Contract Lock

Goal: prove exactly what changed at the transform boundary and prevent accidental double-transform or missing-transform
regressions.

Implementation tasks:

1. Add a reproducible transform-history extractor under `repro/audits/`.
   - Input: commit pair `44e2d60^..44e2d60`.
   - Output: untracked `reports/exdqlm_transform_regression_forensics_<date>/`.
   - Required files:
     - `transform_diff_manifest.csv`
     - `active_scale_contract.csv`
     - `retros_forecast_transform_sites.csv`
     - `README.md`
2. Record all active transform boundaries:
   - shared retrospectives,
   - USGS observations,
   - retrospective GloFAS/NWS,
   - NWS forecasts,
   - GloFAS forecasts,
   - post-stage outputs and plotted outputs.
3. Compare active code to pre-`44e2d60` behavior without running old production, while marking old log-log behavior
   as diagnostic-only.
4. Add static tests that fail if the active runner silently reintroduces:
   - `Y <- log(Y)` in `R/disc_w/03_covariates_standardize.R`,
   - `log(nws_forecast[,-1])` or `log(glofas_forecast[,-1])` in the active runner,
   - inconsistent `analysis_scale_*` and `legacy_*_input_scale` defaults.
5. Add explicit near-zero retrospective checks so the report records why `log_log1p_cms` is not a safe active target.

Tests to add or extend:

1. Extend `tests/python/test_log1p_transform_policy.py` to assert the active runner and retrospective builder have
   exactly one intended scale conversion boundary.
2. Add an R fixture test for `unified_convert_scale` round trips:
   - `raw_cms -> log1p_cms -> raw_cms`,
   - `raw_cms -> log_log1p_cms -> raw_cms`,
   - `log_log1p_cms -> log1p_cms`.
3. Add a manifest test that ensures fit/post adapters record `from_scale`, `to_scale`, and artifact name for retros,
   NWS, and GloFAS.
4. Add a near-zero test showing that `raw_cms = 0` is valid on `log1p_cms` but invalid on `log_log1p_cms` without
   artificial flooring.

Acceptance criteria:

1. The transform-forensics report identifies every code-level transform site affected by `44e2d60`.
2. Static tests prove that active `keep` fit/post inputs are all on one declared scale.
3. The report explicitly distinguishes the intended current `log1p` contract from the old log-log contract.

## Phase B: Deterministic Scale-Sensitivity Fixtures

Goal: quantify how much the transform change alone moves `s_t`, `u_t`, `FFF`, and `QQQ`.

Implementation tasks:

1. Build a deterministic fixture with raw flow values spanning low, medium, high, and tail ranges.
   - Include exact zero and near-zero retrospective-like values.
2. Evaluate the same synthetic residual structure under:
   - old `log_log1p_cms` scale,
   - current `log1p_cms` scale.
3. Feed both into the standalone latent/pseudo-data helpers in
   `R/disc_w/11_latent_pseudodata_audit_helpers.R`.
4. Emit a table comparing:
   - residual magnitude,
   - residual square magnitude,
   - `sts.mu`,
   - `E[s_t]`,
   - `u.chi`,
   - `E[u_t]`,
   - `E[1/u_t]`,
   - `FFF`,
   - `QQQ`.

Tests to add:

1. `tests/testthat/test_exdqlm_transform_scale_sensitivity.R`
2. Fixture expectations should not assert that log1p is "better" or "worse"; they should assert known mathematical
   relationships and finite outputs.
3. Include at least one fixture where old-scale values are benign and current-scale values approach guard thresholds.

Acceptance criteria:

1. We can reproduce, in a small fixture, whether the larger log1p residuals are sufficient to push latent moments or
   pseudo-data toward the bad runtime range.
2. The fixture is deterministic and runs without external campaign outputs.
3. The fixture demonstrates that old log-log compression is not a valid active workaround for zero or near-zero
   retrospectives.

## Phase C: Latent Moment Robustification

Goal: make `s_t` and `u_t` numerically stable on the intended `log1p` scale.

Implementation tasks for `s_t`:

1. Replace the active entropy calculation with the canonical positive-truncated normal entropy in natural logs.
2. Compute the Mills-ratio terms in log space.
3. Define explicit finite-value behavior for extreme `s.mu / s.sig`:
   - no silent `NA`,
   - no negative `E[s_t^2]`,
   - no base-2 entropy.
4. Preserve the existing exAL-disabled shortcut in `DISC_W_AL_MODE`.

Implementation tasks for `u_t`:

1. Stabilize Bessel-ratio evaluation for small `sqrt(psi * chi)` and large `sqrt(psi * chi)`.
2. Audit whether `HyperbolicDist::besselRatio(val, nu, 1, Inf)` is the right ratio for all moments.
3. Add asymptotic or log-Bessel fallbacks for `E[u_t]`, `E[1/u_t]`, `E[log u_t]`, and entropy.
4. Replace scalar `E.log.uts <- sum(...)` with an explicit contract:
   - either document that it is intentionally total entropy/log expectation, or return both per-time and total values.
5. Add warnings or fail-fast guards when `u.chi` or `u.psi` are repaired by flooring.

Tests to add or extend:

1. Extend `tests/testthat/test_exdqlm_multivar_keep_latent_pseudodata_audit.R`.
2. Add numerical-integration checks for `s_t` entropy and moments over benign and extreme parameter values.
3. Add GIG moment checks for:
   - small `chi`,
   - large `chi`,
   - small `psi`,
   - large `psi`,
   - runtime-like q50 parameters if extractable.
4. Add transform-scale paired tests from Phase B.

Acceptance criteria:

1. Latent moments remain finite and positive where theory requires positivity.
2. Moment identities pass against numerical integration or Bessel identities.
3. Entropy is mathematically correct and uses natural logs.
4. Runtime-like extreme fixtures either pass with finite bounded values or fail early with a meaningful diagnostic.

## Phase D: Pre-Kalman Pseudo-Data Guards

Goal: stop destructive `FFF`/`QQQ` inputs before they enter the Kalman update.

Implementation tasks:

1. Add a helper near the pseudo-data construction path:
   - validate finite `FFF`,
   - validate finite positive `QQQ_diag`,
   - validate finite `E[s]`, `E[s^2]`, `E[u]`, `E[1/u]`, and core `sigma/gamma` expectations,
   - compute lane/time/source maxima and quantiles,
   - optionally fail-fast before the compiled Kalman call.
2. Use explicit threshold names and log them:
   - `fff_abs_cap`,
   - `qqq_diag_abs_cap`,
   - `e_inv_u_abs_cap`,
   - `e_s_abs_cap`,
   - `state_norm_abs_cap`.
3. Make thresholds configurable from environment variables or config, with conservative defaults.
4. Add a diagnostic CSV per iteration when a guard fires.

Tests to add:

1. Healthy deterministic pseudo-data passes.
2. Non-finite `FFF` fails.
3. Non-positive or non-finite `QQQ_diag` fails.
4. Runtime-like q50 `FFF=-3245.82` triggers the configured warning/fail threshold when the threshold is below that
   value.
5. Forecast `FFF_forecast` and `QQQ_forecast` are checked as well as historical `FFF` and `QQQ`.

Acceptance criteria:

1. The Kalman layer never receives non-finite or structurally invalid pseudo-data.
2. Extreme but finite pseudo-data are recorded with enough context to debug source, lead, time, and member.
3. The guard can run in warning mode for diagnostics and fail-fast mode for production protection.

## Phase E: Sigma/Gamma Recalibration Under Log1p

Goal: determine whether the `sigma/gamma` approximation was tuned for the old compressed scale.

Status: not completed. This is now the most important causal-isolation phase because the guarded reproduction proves
the repaired stack is much more stable, but it does not say whether `sigma/gamma`, `s_t/u_t`, pseudo-data guards, or
their interaction was the decisive change.

Implementation tasks:

1. Audit initialization and priors used by `new.gamsig.out` and the Laplace/Delta helpers in
   `R/disc_w/10_gamsig_laplace.R`.
2. Compare expected residual scales under old and current transforms from Phase B.
3. Test whether prior scales, initial `sigma`, `gamma` bounds, damping, and refresh schedules assume old log-log
   residual magnitudes.
4. Add an ablation that freezes `sigma/gamma` at stable values while allowing latent and Kalman updates to proceed.
5. Add an ablation that freezes latent moments while allowing `sigma/gamma` to update.

Tests and runtime checks:

1. Deterministic objective tests for finite objective, gradient-free optimizer output, and valid covariance output.
2. Runtime q-lane ablations:
   - q05 as a healthy control,
   - q35 and q50 as suspect lanes,
   - q95 as upper-tail stress.
3. Output required:
   - `sigma_exp_vec`,
   - `gamma_exp_vec`,
   - objective value,
   - optimizer convergence status,
   - latent moments,
   - pseudo-data summaries,
   - state norms.

Acceptance criteria:

1. If fixed `sigma/gamma` stabilizes q50, prioritize the `sigma/gamma` objective or prior calibration.
2. If free `sigma/gamma` is stable after latent/pseudo-data guards, prioritize guard and latent hardening.
3. If both fail, continue to Phase F and Phase G before changing priors broadly.

## Phase F: Kalman And Identifiability Stress Checks

Goal: separate a faithful Kalman propagation of bad pseudo-data from a Kalman or state-identifiability defect.

Status: not completed beyond the earlier historical fixture. The guarded reproduction did not produce pseudo-data
guard failures, so the next value is decomposition and ragged-forecast fixture coverage rather than blaming Kalman
without controlled evidence.

Implementation tasks:

1. Extend the existing Kalman fixture to `J=2`, `ppx>0`, and true ragged forecast segment transitions.
2. Compare the compiled update against an R reference for:
   - filtered means,
   - filtered covariances,
   - smoothed means,
   - smoothed covariances,
   - forecast segment transitions.
3. Add component decomposition traces from the active state index map:
   - trend block,
   - transfer-retained block,
   - discrepancy block by source and lead.
4. Add SPD and symmetry checks for:
   - `W_list_ens`,
   - historical `QQQ`,
   - forecast `QQQ_forecast`,
   - Kalman predictive covariance,
   - Kalman filtered covariance,
   - smoothed covariance.

Tests to add:

1. A compiled-vs-R fixture for ragged forecast keep with transfer retained.
2. A decomposition fixture where known synthetic components reconstruct the fitted mean.
3. A covariance fixture that catches asymmetric or non-PSD matrices before smoothing.

Acceptance criteria:

1. If compiled and R references agree under controlled pseudo-data, do not blame Kalman for runtime explosions until
   pseudo-data are controlled.
2. If component decomposition shows trend/transfer/discrepancy non-identifiability under healthy pseudo-data, then
   add identifiability constraints or stronger priors before production.
3. If decomposition is only unstable under extreme pseudo-data, prioritize Phases C-E first.

## Phase G: Targeted Runtime Reproductions

Goal: run the smallest possible reproductions needed to identify the actual failing layer.

Status: the first guarded q05/q35/q50/q95 reproduction is complete and documented. The remaining Phase G work is the
ablation matrix, not another identical guarded run.

Operational constraints:

1. Do not stop, relaunch, or modify existing live production campaigns.
2. New reproductions must be isolated under a clearly named run root.
3. Use q-lane subsets only unless evidence demands more.
4. Save large outputs under `reports/`, not tracked docs.

Recommended lanes:

1. q05: stable control.
2. q35: mid-lane pathology with large `E[s]` and `QQQ`.
3. q50: strongest state explosion and extreme negative `FFF`.
4. q95: upper-tail pathology with very large `E[1/u]`.

Run matrix:

| condition | purpose | expected conclusion if stable | expected conclusion if unstable |
| --- | --- | --- | --- |
| current `log1p` plus `TT_sub` fix | confirms impact of already-patched bug | bug was a major contributor | continue |
| current `log1p` plus latent robustification | tests `s_t/u_t` numerical fragility | latent moments were primary | continue |
| current `log1p` plus pseudo-data guard warning mode | measures guard rate without stopping | thresholds mostly diagnostic | thresholds identify true bad iterations |
| current `log1p` plus pseudo-data guard fail-fast mode | protects Kalman from invalid inputs | production can fail safely | need root-cause upstream fix |
| current `log1p` plus fixed `sigma/gamma` | isolates `sigma/gamma` approximation | `sigma/gamma` is primary | continue |
| current `log1p` plus fixed latent moments | isolates latent updates | latent updates are primary | continue |
| old-scale compatibility probe | tests transform-regression hypothesis only | scale change is a major trigger, but not a revert target | instability is not only scale |

The old-scale compatibility probe must not become a silent production revert. It is a controlled diagnostic to
answer: "Does old log-log compression stabilize the same lane under otherwise comparable code?" Because zero and
near-zero retrospectives are unsafe under `log(log1p(cms))`, this probe must be isolated and clearly labeled as
diagnostic-only.

Required runtime outputs:

1. `E[s_t]`, `E[s_t^2]`, `E[u_t]`, `E[1/u_t]`, `E[log u_t]`.
2. `FFF`, `QQQ_diag`, `FFF_forecast`, `QQQ_forecast_diag`.
3. `sigma_exp_vec`, `gamma_exp_vec`, objective values, optimizer convergence flags.
4. State norm by iteration and by time.
5. Selected state coordinates.
6. Trend/transfer/discrepancy decomposition.
7. Guard events with source, lead, time, member, and threshold.

Acceptance criteria:

1. A q50 run that stays below `state_norm_sq=1e8` is materially improved relative to saved evidence.
2. A q50 run that still reaches `state_norm_sq=1e10` after latent and pseudo-data guards means the state-space or
   identifiability layer must be investigated next.
3. A run that becomes stable only on old log-log scale means the current log1p workflow needs recalibration, not a
   transform revert.

## Phase H: Documentation, Reproducibility, And Promotion

Goal: make every fix reviewable, reproducible, and reversible.

Tracked docs to update after each phase:

1. This plan.
2. [exdqlm_multivar_keep_final_findings.md](/data/muscat_data/jaguir26/project1_ucsc_phd/docs/exdqlm_multivar_keep_final_findings.md)
3. [exdqlm_multivar_keep_final_mismatch_matrix.csv](/data/muscat_data/jaguir26/project1_ucsc_phd/docs/exdqlm_multivar_keep_final_mismatch_matrix.csv)
4. The relevant phase-specific audit doc.

Tracked code/tests likely needed:

1. `R/disc_w/11_latent_pseudodata_audit_helpers.R`
2. `tests/testthat/test_exdqlm_multivar_keep_latent_pseudodata_audit.R`
3. `tests/testthat/test_exdqlm_transform_scale_sensitivity.R`
4. `tests/python/test_log1p_transform_policy.py`
5. `repro/audits/exdqlm_keep_runtime_stability_audit.R`
6. A new `repro/audits/exdqlm_transform_regression_forensics.R`
7. A new `repro/audits/exdqlm_keep_component_decomposition.R`

Untracked reports to produce:

1. `reports/exdqlm_transform_regression_forensics_<date>/`
2. `reports/exdqlm_transform_scale_sensitivity_<date>/`
3. `reports/exdqlm_keep_latent_extreme_fixture_<date>/`
4. `reports/exdqlm_keep_guarded_q05_q35_q50_q95_<date>/`
5. `reports/exdqlm_keep_ablation_q05_q35_q50_q95_<date>/`

Promotion criteria before any broad production run:

1. Unit and fixture tests pass.
2. q05/q35/q50/q95 targeted reproductions are run or explicitly waived with rationale.
3. Guard thresholds are documented and visible in logs.
4. Runtime reports compare old evidence to new evidence.
5. The final findings doc is updated with:
   - confirmed correct,
   - fixed,
   - still questionable,
   - still inconclusive,
   - next prioritized actions.

## Prioritized Fix List

P0 done. Validate the already-applied `TT_sub` forecast `update_uts` fix and first latent/pseudo-data hardening with
narrow q05/q35/q50/q95 reproductions.

Evidence: `docs/exdqlm_multivar_keep_guarded_repro_20260521.md`. All four lanes wrote fit outputs; q50 ended with
state norm squared `2547.352` instead of reproducing the prior `1.125e10` failure.

P0 done. Build the transform-regression forensic report for `44e2d60^..44e2d60`, explicitly documenting zero and near-zero
retrospective behavior.

Why: the user-observed "worked before log-log to log1p" clue is strong and must be turned into concrete evidence, but
the old log-log scale is not a valid active target when `log1p(cms)` can be zero or near zero.

P0 done. Add deterministic scale-sensitivity fixtures comparing `log_log1p_cms` and `log1p_cms`, including zero and
near-zero retrospective values.

Why: this tells us whether the transform change alone can plausibly move latent moments into the pathological range.

P0 partly done. Add pre-Kalman `FFF`/`QQQ` guards in warning mode first, then fail-fast mode.

Why: regardless of root cause, the Kalman layer should not consume destructive pseudo-data silently. Warning-mode
instrumentation exists and produced the q05 `E[1/u]` guard evidence; production fail-fast/damping policy remains to
be chosen.

P0 done for the half-order formula; P1 remains for runtime policy. Harden `u_t` moment calculations under extreme
`psi/chi`.

Why: runtime evidence still shows a transient q05 `E[1/u_t]` burst, so the numerical formula is improved but guard
response/tuning remains important.

P1 done. Replace `s_t` entropy with the canonical positive-truncated normal entropy.

Why: likely not the direct state-explosion cause, but it contaminates ELBO/convergence diagnostics.

P0 next. Recalibrate or damp `sigma/gamma` updates for the `log1p` scale if ablations show that fixed `sigma/gamma`
stabilizes suspect lanes.

Why: the old compressed scale may have tuned priors and optimizers implicitly.

P1 next. Add trend/transfer/discrepancy decomposition traces.

Why: identifiability may amplify instability even if it does not originate it.

P2. Extend the compiled Kalman fixture to ragged forecast keep with `J=2` and `ppx>0`.

Why: current Kalman evidence is encouraging but incomplete for the full active keep workflow.

P2. Fix or gate the post-stage truth-window figure path.

Why: the guarded fit outputs completed, but the wrapper exited nonzero because post-stage CRPS/figure code had no
USGS truth rows available at/after `2022-12-26`.

## Decision Tree

1. If old-scale compatibility is stable and current `log1p` is unstable with the same code, the transform change is a
   major trigger, but the fix remains `log1p` stabilization.
2. If current `log1p` becomes stable after latent robustification, the primary repair is `s_t/u_t` numerical
   stability.
3. If current `log1p` becomes stable after fixed `sigma/gamma`, the primary repair is `sigma/gamma` objective,
   priors, damping, or initialization.
4. If current `log1p` becomes stable only after pseudo-data guards, the root remains upstream but the production
   safety mechanism is effective.
5. If instability persists with fixed latent moments and fixed `sigma/gamma`, prioritize Kalman ragged-forecast and
   identifiability work.
6. If all controlled layers pass but runtime still fails, the remaining suspect is an interaction across layers that
   only appears in the full VB schedule. At that point the next step is iteration-level snapshotting, not guessing.

## Current Bottom Line

It is still not proven that the transform change was the sole reason the algorithm failed. The first guarded
post-repair reproduction shows that the current `log1p_cms` path can be made dramatically more stable, but it does
not isolate which repair was decisive because several changes were active together.

The transform-regression hypothesis remains important because:

1. the reported behavior changed after the transform rewrite,
2. git history shows a precise policy flip in `44e2d60`,
3. `log1p` materially expands residual magnitude relative to `log(log1p)`,
4. the active latent and pseudo-data formulas are directly residual-sensitive,
5. saved runtime evidence shows the bad lanes failing through exactly those residual-sensitive objects.
6. the old log-log path has a real near-zero defect for retrospectives, so it should not be restored as the fix.
7. the guarded run still had a q05 latent-tail warning burst, which is exactly the kind of scale-sensitive issue that
   could be hidden by the old compressed transform.

The repair strategy should therefore not start with broad production reruns or a blind transform revert. It should
continue with fixed/free `sigma/gamma` and latent ablations, q05 guard-response tuning, component decomposition, and
ragged-forecast Kalman fixture coverage. Only after those pass should the repaired `log1p` workflow be promoted to
broader production campaigns.
