# exDQLM Multivariate Keep Repair Tracker

Last updated: 2026-05-21

## Scope

This is the living execution tracker for the repaired `log1p_cms` multivariate `exdqlm keep` workflow. It tracks the
remaining work after the full audit, first repair sequence, and isolated guarded q05/q35/q50/q95 reproduction.

The current goal is not to produce every possible diagnostic artifact. The goal is to finish the remaining work in a
high-quality sequence:

1. preserve the successful guarded-run evidence,
2. add only the curated PNG/evidence bundle needed for review and communication,
3. isolate which repair mattered through targeted ablations,
4. make q05-like latent-tail behavior production-safe,
5. verify scientific component behavior and remaining Kalman contracts,
6. fix operational post-stage failure modes,
7. decide whether the repaired `log1p_cms` path is ready for broader production.

## Operating Rules

1. Do not stop, relaunch, or modify existing production campaigns unless explicitly requested.
2. Keep new runtime outputs under `reports/` and untracked by default.
3. Commit tracked docs, tests, scripts, and small reproducibility helpers intentionally.
4. After every phase, update this tracker with:
   - commands run,
   - evidence paths,
   - pass/fail status,
   - remaining risk,
   - next action.
5. Do not promote a broad production relaunch until the promotion gate at the end of this tracker is explicitly
   satisfied.

## Current Baseline

Tracked summary docs:

- [final findings](/data/muscat_data/jaguir26/project1_ucsc_phd/docs/exdqlm_multivar_keep_final_findings.md)
- [repair and transform regression plan](/data/muscat_data/jaguir26/project1_ucsc_phd/docs/exdqlm_multivar_keep_repair_and_transform_regression_plan.md)
- [guarded reproduction evidence](/data/muscat_data/jaguir26/project1_ucsc_phd/docs/exdqlm_multivar_keep_guarded_repro_20260521.md)

Completed first repair sequence:

| item | status | evidence |
| --- | --- | --- |
| Forecast `update_uts` `TT_sub` indexing fix | done | commit `eb22e6e` |
| Transform forensics and scale-contract tests | done | commit `be5cf55` |
| Stable `s_t` moments/entropy | done | commit `4bbb643` |
| Closed-form half-order `u_t` moments | done | commit `4bbb643` |
| Pseudo-data guards in warning mode | done | commit `4bbb643` |
| Guarded repro launcher and post-save objective switch | done | commit `5a83162` |
| Guarded run monitor | done | commit `869c9c2` |
| Guarded q05/q35/q50/q95 reproduction | done | `docs/exdqlm_multivar_keep_guarded_repro_20260521.md` |

Guarded reproduction result:

| lane | iter | terminal state norm sq | fit output |
| --- | ---: | ---: | --- |
| q05 | 3000 | 1521.116 | written |
| q35 | 3000 | 2233.589 | written |
| q50 | 1079 | 2547.352 | written |
| q95 | 3000 | 5082.421 | written |

Residual concern:

| issue | status | evidence | next action |
| --- | --- | --- | --- |
| q05 transient historical `E[1/u_t]` burst | open | 18 guard rows, iterations 1001-1018, peak `14397.595` | tune/decide guard response |
| Single causal layer not isolated | open | guarded run used multiple fixes together | run ablations |
| Post-stage no-truth failure | open | no USGS truth rows at/after `2022-12-26` | gate/fix post-stage figure path |

## Execution Checklist

### T0. Curated Evidence Bundle From Existing Guarded Outputs

Status: pending

Purpose: create a compact review bundle, not a plot dump. This should help us inspect and communicate the repaired
run before spending time on causal ablations.

Inputs:

- existing guarded q05/q35/q50/q95 `.RData` outputs under the isolated guarded run root,
- existing runtime audit output under
  `reports/exdqlm_keep_guarded_repro_guarded_log1p_q05_q35_q50_q95_20260521/runtime_stability/`.

Required outputs under a new or existing `reports/` subdirectory:

1. q05/q35/q50/q95 state norm panel.
2. `E[1/u_t]` panel, with q05 iterations 1001-1018 called out when possible.
3. `FFF` and `QQQ_diag` panels.
4. sigma/gamma trace or terminal-lane summary, depending on what is available without re-fitting.
5. selected state-coordinate panel.
6. short `README.md` explaining what the plots show and what they do not prove.

Acceptance criteria:

1. No new model fitting.
2. Bundle is small enough for review.
3. The q05 `E[1/u_t]` transient is visible or explicitly linked to the guard CSV.
4. The bundle supports, but does not replace, the ablation plan.

### T1. Ablation Harness Design

Status: pending

Purpose: design the smallest safe harness for causal isolation.

Required design decisions:

1. How to freeze or replay `sigma/gamma`.
2. How to freeze or replay latent moments.
3. Which q-lanes are required for each ablation: default q05/q35/q50/q95, with permission to reduce only if justified.
4. Which existing guarded run values are used as seeds or reference values.
5. Which environment variables or config flags are added.

Acceptance criteria:

1. The harness is isolated from production roots.
2. It has explicit output/report paths.
3. It records all freeze/replay values in manifests.
4. It has at least smoke-level parse/test coverage before runtime use.

### T2. Fixed/Free `sigma/gamma` Ablations

Status: pending

Purpose: determine whether the `sigma/gamma` approximation or calibration is the decisive instability source under
the current `log1p_cms` scale.

Run matrix:

| condition | lanes | expected evidence |
| --- | --- | --- |
| free `sigma/gamma`, repaired latent path | q05/q35/q50/q95 | control against guarded run |
| fixed `sigma/gamma`, free latent path | q05/q35/q50/q95 | isolates gamsig dynamics |
| damped/refrozen `sigma/gamma`, free latent path | q05/q35/q50/q95 if needed | tests production control |

Required outputs:

1. `sigma_exp_vec`, `gamma_exp_vec`, objective values, optimizer convergence flags.
2. `E[s]`, `E[s^2]`, `E[u]`, `E[1/u]`, `E[log u]`.
3. `FFF`, `QQQ_diag`, `FFF_forecast`, `QQQ_forecast_diag`.
4. state norms and guard events.
5. runtime summary README.

Acceptance criteria:

1. If fixed `sigma/gamma` removes q05 `E[1/u]` bursts or materially changes stability, prioritize gamsig
   recalibration/damping.
2. If fixed `sigma/gamma` does not materially change the q05 burst, prioritize latent guard response and
   identifiability/decomposition.
3. Do not infer from terminal state norm alone; inspect latent and pseudo-data trajectories.

### T3. Fixed/Free Latent Moment Ablations

Status: pending

Purpose: determine whether the `s_t/u_t` updates remain the dominant source of instability after numerical
hardening.

Run matrix:

| condition | lanes | expected evidence |
| --- | --- | --- |
| free latent moments, free `sigma/gamma` | q05/q35/q50/q95 | repaired control |
| fixed/replayed latent moments, free `sigma/gamma` | q05/q35/q50/q95 | isolates latent dynamics |
| capped/damped `E[1/u]`, free `sigma/gamma` | q05 first, then q35/q50/q95 if promising | tests production guard policy |

Acceptance criteria:

1. If replayed/capped latent moments stabilize q05 without harming q50/q95, define a production policy.
2. If latent replay does not change behavior, shift emphasis to `sigma/gamma` and decomposition.
3. All latent interventions must be documented as diagnostics unless explicitly promoted later.

### T4. q05 Guard-Response Policy

Status: pending

Purpose: turn the warning-mode q05 `E[1/u_t]` evidence into a production decision.

Candidate policies:

1. warn-only with documented thresholds,
2. fail-fast on cap exceedance,
3. temporary `sigma/gamma` refreeze after guard,
4. damp/cap `E[1/u_t]` before pseudo-data construction,
5. trigger snapshotting only.

Acceptance criteria:

1. The chosen policy prevents silent destructive pseudo-data.
2. The policy does not mask scientifically important tail behavior without reporting it.
3. The policy is tested with deterministic fixtures and at least one targeted q05 runtime check.

### T5. Trend/Transfer/Discrepancy Decomposition

Status: pending

Purpose: verify the stable outputs are scientifically interpretable, not merely finite.

Required outputs:

1. trend contribution traces,
2. retained transfer contribution traces,
3. discrepancy contribution traces by source/lead where available,
4. reconstruction checks against fitted means,
5. q-lane comparison table.

Acceptance criteria:

1. Contributions reconstruct fitted means within numerical tolerance.
2. No single weakly identified component silently absorbs implausible signal under the repaired run.
3. If identifiability is questionable, document whether it appears only under unstable inputs or also under healthy
   pseudo-data.

### T6. Ragged Forecast Kalman Fixture

Status: pending

Purpose: close the remaining compiled Kalman/RTS contract gap for the active `keep` structure.

Fixture requirements:

1. `J=2`,
2. retained transfer block `ppx>0`,
3. true ragged forecast segment transition,
4. compiled-vs-reference checks for filtered and smoothed means/covariances,
5. symmetry and PSD/coherence checks.

Acceptance criteria:

1. Compiled and reference outputs agree within defined tolerance.
2. Forecast segment transition logic is explicitly exercised.
3. Failures are localized to a minimal fixture before any production run.

### T7. Post-Stage Truth-Window Gate

Status: pending

Purpose: prevent successful isolated fits from being reported as failed whole-workflow runs when post-stage figures
need truth rows that are unavailable after the cutoff.

Required behavior:

1. detect missing truth rows before CRPS/figure code errors,
2. write a clear skipped/partial diagnostic artifact,
3. preserve successful fit-stage status,
4. keep default behavior unchanged where truth is available.

Acceptance criteria:

1. Post-stage no-truth cases exit cleanly or with an explicitly classified partial status.
2. Existing successful post workflows are not regressed.

### T8. Promotion Decision

Status: blocked on T1-T7

Promotion requires:

1. curated evidence bundle complete,
2. ablations identify the most likely decisive repair or show that the stability gain is interactional,
3. q05 guard-response policy chosen and tested,
4. decomposition traces pass or identify an accepted limitation,
5. ragged forecast Kalman fixture passes or has a documented blocker,
6. post-stage truth-window handling is fixed or explicitly waived,
7. final findings and this tracker are updated with exact evidence paths.

Decision outcomes:

| outcome | meaning |
| --- | --- |
| promote repaired `log1p_cms` path | ready for broader but still monitored production |
| targeted additional ablations | one layer remains ambiguous |
| hold production | instability or scientific interpretability remains unresolved |

## Validation Log

| date | command/evidence | outcome |
| --- | --- | --- |
| 2026-05-21 | `Rscript --vanilla -e "testthat::test_file('tests/testthat/test_exdqlm_multivar_keep_latent_pseudodata_audit.R')"` | pass, 45 expectations |
| 2026-05-21 | `Rscript --vanilla -e "testthat::test_file('tests/testthat/test_exdqlm_transform_scale_sensitivity.R')"` | pass, 10 expectations |
| 2026-05-21 | `Rscript --vanilla -e "testthat::test_file('tests/testthat/test_scale_contract_adapters.R')"` | pass, 13 expectations |
| 2026-05-21 | `Rscript --vanilla -e "testthat::test_file('tests/testthat/test_exdqlm_runtime_stability_audit.R')"` | pass, 8 expectations |
| 2026-05-21 | `python3 -m unittest tests.python.test_log1p_transform_policy -v` | pass, 6 tests |
| 2026-05-21 | guarded q05/q35/q50/q95 reproduction | fit outputs written; post-stage no-truth failure after fit |
| 2026-05-21 | guarded runtime stability audit | pass; report written under `reports/exdqlm_keep_guarded_repro_guarded_log1p_q05_q35_q50_q95_20260521/runtime_stability/` |

## Change Log

| date | change | status |
| --- | --- | --- |
| 2026-05-21 | Created living repair tracker with curated evidence, ablation, guard-policy, decomposition, Kalman, post-stage, and promotion gates | done |
