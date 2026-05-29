# exDQLM Multivar Keep 20260524 Latent Stability Diagnostic Plan

Date: 2026-05-28

Status: plan for the next targeted diagnostic cycle. This document does not authorize a full grid relaunch.

## Purpose

The 20260524 epsilon/discount-factor grid is mostly healthy, but three grid rows failed. Two failures look like the
old latent-instability family, while one is a terminal sampling walltime issue. The next work should be a small,
instrumented diagnostic cycle that identifies the first unstable quantity and tests one stabilization mechanism at a
time.

The goal is not to rescue every aggressive grid row. The goal is to decide whether there is still a real algorithmic
defect in the active `exdqlm_multivar_keep` workflow, and, if so, fix it without masking bad model specifications.

## Locked Evidence

Runtime root:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_epsilon_discount_grid_20260524`

Deep audit report:

`reports/he2_exdqlm_multivar_keep_epsilon_discount_grid_live_20260524/latent_stability_deep_audit_20260528_181606/README.md`

Key audit tables:

| table | purpose |
| --- | --- |
| `run_level_audit.csv` | row-level pass/fail, CRPS, guard totals, max state/gamma/sigma summaries |
| `quantile_log_audit.csv` | q-lane iteration summaries, guard counts, sampling details, log paths |
| `pseudodata_guard_events.csv` | exact pseudodata guard quantities, blocks, caps, and exceedance counts |
| `sampling_walltime_events.csv` | terminal sampling walltime failures |
| `gamsig_guard_events.csv` | gamma/sigma guard and near-zero objective events |
| `spec_failure_summary.csv` | spec-level pass/fail and guard totals |

Current final matrix state from the audit:

| status | count |
| --- | ---: |
| pass | 147 |
| fail | 3 |
| planned rows | 150 |

Failed rows:

| cutoff | spec | failure class | failing q-lanes | first conclusion |
| --- | --- | --- | --- | --- |
| `20220511` | `c02_eps090` | fit-stage pseudodata guard | `q20` | `E[u_t]` and historical `FFF` exceed caps at iter 32 |
| `20221225` | `c03_eps060` | fit-stage pseudodata guard | `q20` | `E[u_t]`, historical `FFF`, forecast `FFF`, and forecast `E[u_t]` exceed caps at iter 47 |
| `20210123` | `c06_eps365` | terminal sampling walltime | `q05`, `q35`, `q80` | fit reaches terminal sampling; failure is not the same pseudodata path |

## Active Code Contract To Diagnose

The active implementation path is:

| layer | active code anchor | why it matters |
| --- | --- | --- |
| `s_t` moments | `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:1848-1888` | computes positive-truncated-normal `E[s_t]`, `E[s_t^2]`, and entropy |
| `u_t` moments | `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:1917-1944` | computes GIG `E[u_t]`, `E[1/u_t]`, `E[log u_t]`, and entropy |
| latent cap | `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:1946-2029` | current promoted mode caps only `E[1/u_t]`, not `E[u_t]` |
| pseudodata guard caps | `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:3751-3763` | guard caps are `FFF=1000`, `QQQ=10000`, `E[s]=1000`, `E[s^2]=1e6`, `E[u]=1e6`, `E[1/u]=5000` |
| historical pseudodata | `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:4060-4066` | constructs `FFF` and `QQQ` passed to the Kalman layer |
| forecast pseudodata | `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:4073-4089` | constructs forecast-member `FFF_forecast` and `QQQ_forecast` |
| latent update loop | `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:4432-4568` | updates historical and forecast `s_t/u_t`, then applies latent ablation before gamma/sigma update |
| config validation | `R/unified/config.R:2153-2214` | validates delayed state guard, latent ablation, and pseudodata guard fields |
| fit environment wiring | `R/unified/stages/stage_fit.R:909-1083` | turns YAML policy into `DISC_LATENT_*` and `DISC_PSEUDODATA_*` environment variables |

Important interpretation:

`E[u_t]` does not enter the `FFF` formula directly. Historical `FFF` is:

```text
FFF = (E[c / b * |gamma|] * E[s_t] + E[a / b / sigma] / E[1/u_t]) / E[1 / b / sigma]
```

However, `E[u_t]` enters the gamma/sigma update objective and is a symptom of the same GIG moment regime that can make
`E[1/u_t]` small. A large `FFF` can come from at least four mechanisms:

1. large `E[s_t]`;
2. small `E[1/u_t]`, because `1 / E[1/u_t]` appears in the numerator;
3. small `E[1 / b / sigma]`, because it is the denominator;
4. unstable gamma/sigma moments after near-zero or guarded updates.

The diagnostic must identify which term moves first.

## What Is Already Known

The current grid is not running the free latent path. Generated configs use:

| control | current value |
| --- | --- |
| `latent_ablation.mode` | `cap_e_inv_u` |
| `latent_ablation.e_inv_u_cap` | `5000` |
| `pseudodata_guard.enabled` | `true` |
| `pseudodata_guard.mode` | `fail` |
| `pseudodata_guard.caps.e_u_abs_cap` | `1e6` |
| `pseudodata_guard.caps.e_inv_u_abs_cap` | `5000` |
| `gamma_sigma.max_iter` | `100` |
| `gamma_sigma.stabilization.state_guard_start_iter` | `1000` |

That last line is a crucial wiring fact: with `max_iter=100`, the delayed state guard never activates. The grid is
therefore protected by pseudodata and gamma/sigma guards, but not by an active state-norm refreeze guard.

The two q20 failures also show that the explicit `E[1/u_t]` cap is not enough to classify all remaining failures. The
hard stop is on `E[u_t]` and `FFF`, not on an uncapped `E[1/u_t]` explosion.

## Hypotheses And Discriminating Evidence

The diagnostic should not assume which layer is guilty. Each hypothesis below has a concrete signal that can prove or
disprove it.

| id | hypothesis | evidence that supports it | evidence that rejects it |
| --- | --- | --- | --- |
| H1 | GIG `u_t` moment degeneracy is the first event | `psi`, `chi`, `E[u_t]`, or `E[1/u_t]` leaves healthy range before `FFF`/state/gamma changes | `E[u_t]` only rises after gamma/sigma or state drift |
| H2 | `s_t` truncation amplifies the mean equation | `E[s_t]` or `E[s_t^2]` spikes before `FFF`; top cells align with large `s.mu`/tiny `s.sig2` | `E[s_t]` remains normal while `FFF` spikes through denominator terms |
| H3 | gamma/sigma approximation drives the bad pseudo-observation | `E[1/b/sigma]`, `E[a/b/sigma]`, `E[c/b|gamma|]`, sigma, or gamma jumps immediately before `FFF` | stable gamma/sigma moments with bad latents only |
| H4 | Kalman/state feedback creates the bad residual | `state_norm_sq`, `exps`, `exps2`, or top state coordinates drift before latent/gamma changes | state moments remain stable until after pseudodata spike |
| H5 | log1p-scale transform or near-zero transformed values create edge-case latents | offending cells align with near-zero transformed `y`, retro, or forecast-member values; `chi` becomes tiny or residual terms are scale-inconsistent | offending cells are large residuals or denominator effects unrelated to near-zero transformed inputs |
| H6 | forecast-member bookkeeping contributes to the failure | forecast-only top cells are concentrated in one source/member/lead segment, with valid historical quantities | history and forecast fail together from shared gamma/sigma/latent terms |
| H7 | `c06_eps365` is a sampling-only runtime issue | fit diagnostics are healthy and only posterior sampling GIG/truncated-normal calls exceed walltime | fit-stage pseudodata or state guards fire before sampling |

## Instrumentation Plan

Add diagnostics before changing the algorithm. The instrumentation should be low-overhead and enabled only when a new
diagnostic flag is set.

### 1. Pre-pseudodata iteration summary

Write one CSV row per iteration, quantile, and block:

`logs/pseudodata_guard/pseudodata_iteration_summary.csv`

Minimum columns:

| column | description |
| --- | --- |
| `p0`, `iter`, `context`, `block` | q-lane, iteration, live/seed, history/forecast |
| `source_index`, `source_name` | source block when available; otherwise integer index |
| `n`, `finite_n`, `nonfinite_n` | shape and finite checks |
| `max_abs_FFF`, `p99_abs_FFF`, `median_abs_FFF` | pseudo-observation mean scale |
| `min_QQQ_diag`, `max_QQQ_diag`, `p99_QQQ_diag` | pseudo-observation variance scale |
| `max_E_s`, `max_E_s2` | `s_t` moment scale |
| `max_E_u`, `max_E_inv_u`, `min_E_inv_u` | `u_t` moment scale |
| `max_psi`, `min_psi`, `max_chi`, `min_chi` | GIG parameter scale |
| `max_gamma`, `max_sigma`, `min_E_invb_inv_sigma` | gamma/sigma denominator diagnostics |
| `state_norm_sq`, `state_norm_sq_per_t` | state feedback scale |

This table answers whether the failure was sudden or slowly growing, and whether the first abnormal term is latent,
gamma/sigma, pseudodata denominator, or state feedback.

### 2. Top-k offending cells

When any soft threshold is exceeded, write:

`logs/pseudodata_guard/pseudodata_top_cells.csv`

For each quantity (`FFF`, `QQQ_diag`, `E_u`, `E_inv_u`, `E_s`, `E_s2`, `chi`, `psi`), store the top 20 cells by
absolute value or extremeness. Required columns:

| column | description |
| --- | --- |
| `quantity`, `rank`, `value`, `threshold` | what was selected |
| `block`, `source_index`, `source_name`, `time_index`, `date` | where it happened |
| `member_index`, `lead_index` | forecast-specific position, blank for history |
| `y`, `exps`, `exps2`, `resid`, `resid_sq` | residual context |
| `E_s`, `E_s2`, `E_u`, `E_inv_u`, `psi`, `chi` | latent context |
| `E_c_invb_absgam`, `E_a_invb_inv_sigma`, `E_invb_inv_sigma` | exact `FFF` ingredients |
| `gamma`, `sigma` | human-readable gamma/sigma moments |

This is the most important diagnostic artifact. Without it, we know that `FFF` failed but not which source/time/member
caused the failure.

### 3. Optional compact snapshots

Do not save full `.RData` by default. Instead, if a guard is about to fail, save compact RDS/CSV diagnostics only:

| artifact | reason |
| --- | --- |
| `latent_guard_snapshot_iter_<iter>.rds` | small list of offending cells and per-source summaries |
| `latent_guard_snapshot_iter_<iter>.csv` | portable top-cell version for quick review |
| `gamsig_source_summary_iter_<iter>.csv` | gamma/sigma source-block summary |

Full `.RData` is only justified if the compact top-cell diagnostics cannot identify the bad path.

### 4. Sampling-stage timer details

For `20210123 c06_eps365`, add or reuse sampling diagnostics to write per-call timings for:

| sampling step | required fields |
| --- | --- |
| retro `s_t/u_t` sampling | q, source, time count, elapsed, min/max `psi`, min/max `chi` |
| forecast-member GIG sampling | q, source, member, lead count, elapsed, min/max `psi`, min/max `chi` |
| posterior predictive synthesis | q, sample count, elapsed, memory check |

The purpose is to distinguish bad mathematics from an inefficient sampler path for finite but difficult GIG parameters.

## Implementation Tasks

These are ordered so every step produces useful evidence even if the next step is paused.

| step | task | output | tests |
| --- | --- | --- | --- |
| 1 | Add diagnostic flag parsing for latent/pseudodata iteration summaries | config/env fields, disabled by default | R config validation test |
| 2 | Implement reusable summary helpers for matrices/lists/forecast segments | tested helper functions | deterministic R unit tests |
| 3 | Add pre-guard iteration summary writer before `disc_w_check_pseudodata_guard(...)` | `pseudodata_iteration_summary.csv` | source-contract test confirms call location |
| 4 | Add top-k cell writer triggered by soft thresholds or hard guard pre-failure | `pseudodata_top_cells.csv` | fixture verifies correct top rows and indices |
| 5 | Expose `state_guard_start_iter` override in the diagnostic config generator | generated YAML with start iter <= 20 | Python config-builder test |
| 6 | Add a named experimental latent mode for `E[u_t]` sensitivity only if diagnostics confirm H1/H3 | e.g. `cap_e_u_and_e_inv_u`, not default | R moment-cap tests and config validation |
| 7 | Add sampling timer extraction/reporting for the c06 walltime issue | sampling walltime table | parser test with synthetic log |
| 8 | Build one parser/report script for the targeted diagnostic roots | `reports/.../README.md` plus CSVs/plots | Python unit test on fixture logs |

Step 6 should not be implemented first. Capping `E[u_t]` changes the VB update behavior and can hide the root cause.
It is a sensitivity experiment, not a first-line diagnosis.

## Targeted Relaunch Design

Use a new isolated runtime root, for example:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/exdqlm_keep_latent_diag_20260529`

Do not modify the completed grid root. Do not touch older protected live roots.

### Phase A: exact reproductions with better visibility

Run only the failing q-lanes with the same model/data/spec and diagnostic logging enabled:

| target | cutoff | spec | q | guard policy | expected result |
| --- | --- | --- | ---: | --- | --- |
| A1 | `20220511` | `c02_eps090` | `0.20` | fail | should reproduce iter 32 guard and now write top cells |
| A2 | `20221225` | `c03_eps060` | `0.20` | fail | should reproduce iter 47 guard and now write top cells |

Acceptance:

- reproducible failure within +/- 2 iterations, or a documented reason for nondeterminism;
- top-cell diagnostics identify the source, time/date, block, and exact bad formula term;
- no large `.RData` retained unless explicitly required.

### Phase B: matched controls

Run a minimal control set to avoid overfitting the diagnosis to one lane:

| control | cutoff | spec | q | reason |
| --- | --- | --- | ---: | --- |
| B1 | `20220511` | `c02_eps180` | `0.20` | same cutoff/case family, larger epsilon, passed |
| B2 | `20220511` | `c02_eps060` | `0.20` | same cutoff/case family, smaller epsilon, expected contrast |
| B3 | `20221225` | `c03_eps090` | `0.20` | same cutoff/case family, larger epsilon, passed but high latent cap count |
| B4 | `20221225` | `c03_eps030` | `0.20` | same cutoff/case family, smaller epsilon, contrast |
| B5 | `20211112` | `c02_eps090` | `0.20` | same failed spec as A1, different cutoff, passed |
| B6 | `20211112` | `c03_eps060` | `0.20` | same failed spec as A2, different cutoff, passed |

Acceptance:

- controls produce the same diagnostic columns;
- first abnormal term in failed lanes is absent or much smaller in controls;
- any stabilization candidate does not damage controls.

### Phase C: active state-guard sensitivity

Repeat A1/A2 with only the state guard start changed:

| target | changed setting | unchanged settings |
| --- | --- | --- |
| C1/C2 | `state_guard_start_iter=20` | same q/spec/cutoff, same latent cap, same pseudodata guard |

This tests whether the existing state guard is simply wired outside the 100-iteration budget.

Acceptance:

- if state guard fires before the pseudodata failure and stabilizes the lane, the production fix is likely a config
  policy fix;
- if pseudodata still fails with active state guard, the root is more likely latent/gamma/sigma or pseudo-data
  formula sensitivity.

### Phase D: `E[u_t]` sensitivity, only if justified

Only run this phase if A/B show that `E[u_t]` or its direct ingredients move first.

Candidate diagnostic modes:

| mode | behavior | purpose |
| --- | --- | --- |
| `cap_e_inv_u` | current promoted behavior | baseline |
| `cap_e_u_and_e_inv_u` | cap both `E[u_t]` and `E[1/u_t]` after update | tests whether the remaining path is the uncapped `E[u_t]` side |
| `freeze_on_e_u_guard` | reuse previous latents if `E[u_t]` exceeds a soft cap | tests if a one-iteration latent shock drives the failure |

Suggested caps for diagnostics, not production:

| cap | reason |
| ---: | --- |
| `1e6` | current pseudodata hard guard threshold |
| `2e5` | earlier soft intervention |
| `1e5` | stronger sensitivity check |

Promotion bar:

- the mode must be explicitly named in config and logs;
- tests must prove both moments are capped as intended;
- controls must not show degraded CRPS, broken quantile synthesis, or worse component diagnostics;
- final docs must state that this changes the variational update.

### Phase E: sampling walltime isolation

Handle `20210123 c06_eps365` separately:

| target | cutoff | spec | q | diagnosis |
| --- | --- | --- | ---: | --- |
| E1 | `20210123` | `c06_eps365` | `0.05` | retro posterior sampling walltime |
| E2 | `20210123` | `c06_eps365` | `0.35` | forecast-member GIG walltime |
| E3 | `20210123` | `c06_eps365` | `0.80` | retro posterior sampling walltime |

Acceptance:

- determine whether fit-stage diagnostics are healthy;
- identify exact sampling call and parameter regime;
- choose between sampler fallback, timeout policy, or leaving this as a failed aggressive spec.

## Transform-Specific Audit Addendum

Because the instability appeared after moving from `loglog1p` back to `log1p`, the targeted diagnostics must include
raw and transformed values for top offending cells.

For each top offending history or forecast cell, capture:

| field | purpose |
| --- | --- |
| raw USGS/retro/forecast value if available | confirms physical-scale magnitude |
| transformed `log1p` value used by fit | checks near-zero and scale consistency |
| `y - exps` and residual-square components | identifies whether the issue is near-zero, large residual, or denominator-driven |
| source/member/lead/date | determines whether one input family causes the issue |

Decision rule:

- If failures align with near-zero transformed inputs and tiny `chi`, revisit `u_t`/`E[1/u_t]` stability.
- If failures align with huge residuals or small `E[1/b/sigma]`, focus on gamma/sigma and state feedback.
- If failures align with one forecast source/member segment, audit forecast-member bookkeeping and transfer-retained
  construction before changing latent formulas.

## Reporting Contract

Each diagnostic cycle should produce an untracked report directory under:

`reports/he2_exdqlm_multivar_keep_epsilon_discount_grid_live_20260524/`

Required files:

| file | required contents |
| --- | --- |
| `README.md` | executive conclusion, exact run roots, pass/fail, recommended next action |
| `diagnostic_run_matrix.csv` | all targeted q-lanes, config deltas, status |
| `pseudodata_iteration_summary.csv` | concatenated iteration summaries |
| `pseudodata_top_cells.csv` | offending cells with formula ingredients |
| `control_comparison.csv` | failed vs control lanes by first abnormal quantity |
| `state_guard_sensitivity.csv` | baseline vs active-state-guard result |
| `sampling_walltime_diagnostics.csv` | c06 sampling-only analysis |
| `recommended_fix_decision.md` | one of: config fix, code fix, sampling fallback, or no change |

Recommended plots:

| plot | reason |
| --- | --- |
| `max_FFF_by_iter.png` | shows sudden vs gradual pseudo-data failure |
| `max_Eu_EinvU_by_iter.png` | separates `E[u_t]` and `E[1/u_t]` regimes |
| `gamsig_by_iter_source.png` | shows source-specific gamma/sigma jumps |
| `state_norm_per_t_by_iter.png` | tests state feedback hypothesis |
| `top_cell_residual_decomposition.png` | explains formula-level failure |

## Fix Decision Tree

Use the diagnostic evidence to choose the smallest correct intervention.

| evidence | next fix |
| --- | --- |
| active state guard prevents A1/A2 without hurting controls | change grid/promotion config so `state_guard_start_iter` is inside the iteration budget |
| `E[u_t]` moves first and capping/freezing that moment fixes A1/A2 while preserving controls | promote a named `E[u_t]` stabilization profile with tests and docs |
| gamma/sigma denominator terms move first | improve gamma/sigma guard/damping/refreeze, especially around source block that first moves |
| `s_t` moments move first | revisit truncated-normal moment bounds and `s_t` update stabilization |
| transformed near-zero values create tiny `chi` or pathological residual terms | add transform-scale specific guard or input preprocessing check; do not change transform blindly |
| only forecast-member top cells fail | audit forecast segment assembly and member bookkeeping before changing latents |
| only sampling walltime fails with finite fit diagnostics | add sampler fallback/timing guard or classify that spec as failed for runtime reasons |

## What Not To Do

- Do not relaunch the full 150-row grid before the targeted diagnostic cycle.
- Do not silently change the production algorithm to cap `E[u_t]` without a named config mode and tests.
- Do not replace failed grid rows in the CRPS ranking without labeling them as diagnostic reruns.
- Do not retain large `.RData` files by default.
- Do not touch older protected production roots.

## Ready Criteria For Implementation

The plan is ready to implement when these are all true:

1. a new isolated diagnostic root is chosen;
2. instrumentation is disabled by default and enabled only in diagnostic configs;
3. source-contract and helper tests pass;
4. A/B/C diagnostic matrix is generated and statically validated;
5. disk cleanup policy is explicit and compact diagnostics are preserved;
6. the final report template exists before the diagnostic runs start.

The first implementation step should be diagnostic instrumentation, not algorithmic stabilization.
