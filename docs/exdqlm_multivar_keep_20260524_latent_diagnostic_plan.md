# exDQLM Multivar Keep 20260524 Latent Stability Diagnostic Plan

Date: 2026-05-28

Status: revised diagnostic plan after a second pass through the failed q-lane logs, generated configs, and active
implementation. This document does not authorize a full grid relaunch.

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

Additional second-pass sources:

| source | evidence used |
| --- | --- |
| failed `q20` `fit.log` files | exact iteration timeline, gamma/sigma vectors, refreeze events, pseudodata guard stop |
| failed `q20` `logs/pseudodata_guard/pseudodata_guard_events.csv` files | guard quantities, cap counts, finite/nonfinite status |
| generated YAML configs under `control/generated_configs/` | discount/epsilon profile, input bundle, transform, guard policy, state guard start |
| `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r` | exact pseudo-data construction, guard function, latent updates, gamma/sigma objective, ELBO accounting |

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

## Corrections From The First Draft

The first version of this plan was directionally right but not evidence-sharp enough. The corrected investigation is:

1. The current guard CSVs are aggregate summaries only. They prove which quantity and block failed, but they do not
   identify source, date, lead, or member. Any source-level claim must therefore come from fit-log gamma/sigma events,
   not from the pseudodata guard CSV itself.
2. The two q20 failures do not show `E[1/u_t]` cap activity. In both failed q20 logs,
   `[latent_ablation] mode=cap_e_inv_u ... capped_history=0 capped_forecast=0` immediately before the failure.
   Therefore these failures are not simply "the old uncapped `E[1/u_t]` explosion".
3. The failing q20 guard stop is on `E[u_t]` and `FFF`, while `E[1/u_t]` is not reported as exceeding its cap. Since
   `E[u_t]` is not a direct term in `FFF`, the likely mechanism is indirect: `E[u_t]` affects gamma/sigma objective
   terms, and the resulting gamma/sigma/latent state creates bad pseudo-data.
4. State norm alone is not a sufficient explanation. Some passing q20 controls have state norms similar to or larger
   than the failing lanes. The inactive state guard is still a real wiring issue, but the evidence does not yet prove
   that state growth is the first cause.
5. The `20210123 c06_eps365` row is a separate sampling-stage runtime issue. It should not be mixed with the q20
   pseudodata failures when testing latent/gamma/sigma fixes.

## Second-Pass Failure Timelines

The q20 failures share a stronger pattern than the first draft stated: source-3 gamma moves from a near-zero value to a
large positive value in the iteration before the hard pseudodata stop, then the split-gamma guard cannot find an
acceptable interior candidate for source block `j=3`.

### `20220511 c02_eps090 q20`

| iter | ELBO | gamma mean | gamma vector | state norm sq | event |
| ---: | ---: | ---: | --- | ---: | --- |
| 30 | `-52.81148` | `0.1639871` | `[0.120449, 0.3604348, 0.01107759]` | `21302.59` | stable near-zero source-3 gamma |
| 31 | `-52.81176` | `0.2943224` | `[0.1174336, 0.3531277, 0.412406]` | `21377.72` | source-3 gamma jump after split-positive selection |
| 32 | `-210249.3` | `0.2965318` | `[0.1278294, 0.3493601, 0.412406]` | `20117.77` | source-3 guard/refreeze; pseudodata guard fails |

Guard details at iter 32:

| quantity | block | max abs | cap | exceed count |
| --- | --- | ---: | ---: | ---: |
| `FFF` | history | `22417.859` | `1000` | `2099` |
| `E_uts` | history | `1009613.467` | `1e6` | `12767` |
| `E_uts` | forecast | `1000001` | `1e6` | `56` |

### `20221225 c03_eps060 q20`

| iter | ELBO | gamma mean | gamma vector | state norm sq | event |
| ---: | ---: | ---: | --- | ---: | --- |
| 45 | `-7.168543` | `0.1299293` | `[0.1184119, 0.2598715, 0.01150441]` | `18683.05` | stable near-zero source-3 gamma |
| 46 | `-7.168171` | `0.23501` | `[0.1181079, 0.2591283, 0.3277937]` | `18687.49` | source-3 gamma jump after split-positive selection |
| 47 | `-216120.4` | `0.2384521` | `[0.1265825, 0.2609802, 0.3277937]` | `20376.18` | source-3 guard/refreeze; pseudodata guard fails |

Guard details at iter 47:

| quantity | block | max abs | cap | exceed count |
| --- | --- | ---: | ---: | ---: |
| `FFF` | history | `22518.780` | `1000` | `2313` |
| `FFF_forecast` | forecast | `14700.713` | `1000` | `54` |
| `E_uts` | history | `1008735.025` | `1e6` | `12995` |
| `E_uts` | forecast | `1005275.987` | `1e6` | `56` |

### Matched Control Signals

These controls are not a formal proof, but they are enough to prioritize the next diagnostics.

| lane | status | last iter | last ELBO | state norm sq | gamsig guards | latent cap events | pseudodata bad rows |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `20220511 c02_eps090 q20` | fail | 32 | `-210249.3` | `20117.77` | `41` | `0` | `3` |
| `20220511 c02_eps180 q20` | pass | 100 | `-52.81225` | `21416.50` | `31` | `0` | `0` |
| `20221225 c03_eps060 q20` | fail | 47 | `-216120.4` | `20376.18` | `51` | `0` | `4` |
| `20221225 c03_eps090 q20` | pass | 100 | `-7.171472` | `18371.44` | `80` | `12795` | `0` |
| `20211112 c02_eps090 q20` | pass | 100 | `-53.52599` | `21837.23` | `30` | `0` | `0` |
| `20211112 c03_eps060 q20` | pass | 100 | `-7.278374` | `21218.94` | `30` | `0` | `0` |

Interpretation:

- source-3 gamma behavior is more suspicious than raw state norm;
- latent cap count alone is not sufficient, because `20221225 c03_eps090 q20` passes with many `E[1/u_t]` cap events;
- the failed q20 lanes need source/time/member top-cell diagnostics before any algorithmic change.

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
| gamma/sigma objective | `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:2045-3025` | consumes `E[u_t]`, `E[1/u_t]`, `E[s_t]`, `E[s_t^2]` and produces the expectations used in `FFF` |
| gamma/sigma forecast update | `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:4570-4608` | source blocks `j=2:(J+1)` include forecast-member latent moments in the gamma/sigma update |
| ELBO accounting | `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:4669-4718` | useful diagnostic, but not the safest primary failure signal until the forecast terms are rechecked |
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

Iteration semantics matter. The live pseudodata guard is called after `FFF`/`QQQ` are built at the top of the loop, and
it is checking the latent and gamma/sigma objects produced by the previous completed update cycle with the same printed
iteration number. For the q20 failures, the relevant diagnostic window is therefore:

1. after `update_uts(...)`, while `psi` and `chi` are still available in `uts.dummy`;
2. after `disc_w_apply_latent_ablation(...)`, to see whether any cap/freeze changed the latent moments;
3. after `update_gamma_sigma(...)`, especially for source block `j=3`;
4. before `disc_w_check_pseudodata_guard(...)`, to decompose `FFF`/`QQQ`.

The current production objects do not retain `psi` and `chi` after the local `uts.dummy` update. Any top-cell diagnostic
that needs GIG parameters must either write them inside the latent update loops or store a diagnostic-only copy.

## Newly Found Code Discrepancy To Verify Separately

The deeper code pass also found a likely ELBO-accounting discrepancy in the forecast terms:

```text
DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:4693
new.uts.out_f$E.sts2[[j-1]] * new.uts.out_f$E.uts[[j-1]]

DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:4698
new.uts.out_f$E.sts[[j-1]]
```

The forecast `s_t` moments live in `new.sts.out_f`, not `new.uts.out_f`. In R, multiplying by `NULL` silently produces
length-zero terms whose sum is zero, so these forecast ELBO terms can be omitted without throwing an error. Also, the
quadratic `s_t^2` term appears to need `E[1/u_t]`, as in the historical term and the gamma/sigma objective, not
`E[u_t]`.

This likely affects ELBO accounting and convergence interpretation more than the direct pseudodata failure, because the
state/latent/gamma-sigma updates use their own paths. Still, it must be verified with a focused test before trusting
ELBO differences as a primary diagnostic signal.

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
hard stop is on `E[u_t]` and `FFF`, not on an uncapped `E[1/u_t]` explosion. However, the current evidence does not yet
prove that `E[u_t]` itself is the root cause, because it could be a symptom of a gamma/sigma source-block jump or a
near-zero transform/residual regime.

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

Current evidence ranking before new diagnostics:

| rank | hypothesis | current status |
| ---: | --- | --- |
| 1 | H3 gamma/sigma approximation/source-3 near-zero split behavior | strongest q20 signal; source-3 gamma jumps immediately before both failures |
| 2 | H1 GIG `u_t` moment degeneracy | supported by `E[u_t]` hard guard, but missing `psi/chi` top cells prevents root-cause claim |
| 3 | H5 log1p/near-zero transformed value edge case | plausible because gamma split repeatedly operates near zero; no top-cell values yet |
| 4 | H4 state feedback | possible, but state norms in passing controls are similar or higher |
| 5 | H6 forecast bookkeeping | plausible for `20221225 c03_eps060` because forecast `FFF` also fails, weaker for `20220511` |
| 6 | H2 `s_t` truncation | not currently supported or rejected because aggregate guard did not flag `E[s]`/`E[s^2]` |
| separate | H7 sampling-only runtime | confirmed separate for `20210123 c06_eps365`; do not use q20 fixes to treat it |

## Instrumentation Plan

Add diagnostics before changing the algorithm. The instrumentation should be low-overhead, disabled by default, and
enabled only when a new diagnostic flag is set.

The instrumentation must answer two different questions:

1. Which quantity first leaves the healthy range?
2. Which source/time/member cell is responsible for the aggregate guard failure?

The current guard answers neither question completely because it only writes aggregate rows once a hard guard is
violated.

### 1. Post-latent update trace

Write a diagnostic row immediately after each `update_uts(...)` call, before `uts.dummy$psi` and `uts.dummy$chi` are
discarded.

Suggested files:

| file | contents |
| --- | --- |
| `latent_update_summary.csv` | one row per iteration/source/block, with min/max/p99 of `E[s]`, `E[s^2]`, `E[u]`, `E[1/u]`, `psi`, `chi` |
| `latent_update_top_cells.csv` | top cells for `E[u]`, `E[1/u]`, `chi`, and `psi`, including source, time/date, lead/member where available |

Minimum columns:

| column | description |
| --- | --- |
| `p0`, `iter`, `block`, `source_index`, `source_name` | q-lane and source |
| `member_index`, `lead_index`, `time_index`, `date` | cell location, blank where not applicable |
| `y`, `exps`, `exps2`, `resid` | residual context |
| `E_s`, `E_s2`, `E_u`, `E_inv_u`, `psi`, `chi` | latent/GIG context |
| `gamma`, `sigma` | current gamma/sigma moments used to compute the update |
| `transform_scale`, `raw_value_if_available` | log1p-specific context |

This is the only reliable place to diagnose `psi`/`chi` without changing persistent model objects.

### 2. Post-gamma/sigma source trace

Write a source-level row after each `update_gamma_sigma(...)` call and after any guard/refreeze decision.

Suggested file:

`gamsig_source_iteration_summary.csv`

Minimum columns:

| column | description |
| --- | --- |
| `p0`, `iter`, `source_index`, `source_name`, `climate_center` | source block |
| `E_gamma`, `E_sigma`, `V_gamma`, `V_sigma` | primary moments |
| `E_c_invb_absgam`, `E_a_invb_inv_sigma`, `E_invb_inv_sigma` | exact `FFF` ingredients |
| `E_a2_invb_inv_sigma`, `E_c2_invb_absgam2_sigma` | exact `u_t/s_t` objective ingredients |
| `guard_triggered`, `guard_message`, `refreeze_until` | stabilization outcome |
| `selected_candidate_label`, `split_reason`, `hessian_ridge` | near-zero/split behavior |

This directly tests the source-3 gamma-jump hypothesis.

### 3. Pre-pseudodata iteration summary

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

### 4. Top-k pseudodata cells

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

### 5. Optional compact snapshots

Do not save full `.RData` by default. Instead, if a guard is about to fail, save compact RDS/CSV diagnostics only:

| artifact | reason |
| --- | --- |
| `latent_guard_snapshot_iter_<iter>.rds` | small list of offending cells and per-source summaries |
| `latent_guard_snapshot_iter_<iter>.csv` | portable top-cell version for quick review |
| `gamsig_source_summary_iter_<iter>.csv` | gamma/sigma source-block summary |

Full `.RData` is only justified if the compact top-cell diagnostics cannot identify the bad path.

### 6. Sampling-stage timer details

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
| 3 | Add latent update summary/top-cell writer inside historical and forecast update loops | `latent_update_summary.csv`, `latent_update_top_cells.csv` | fixture verifies retained `psi/chi` and indices |
| 4 | Add gamma/sigma source summary writer after each source update | `gamsig_source_iteration_summary.csv` | fixture verifies source-3 jump is capturable |
| 5 | Add pre-guard pseudodata summary before `disc_w_check_pseudodata_guard(...)` | `pseudodata_iteration_summary.csv` | source-contract test confirms call location |
| 6 | Add top-k pseudodata cell writer triggered by soft thresholds or hard guard pre-failure | `pseudodata_top_cells.csv` | fixture verifies correct top rows and indices |
| 7 | Add an ELBO-accounting source-contract test for forecast `s_t` terms | failing test first if current code is wrong | R or Python source test |
| 8 | Expose `state_guard_start_iter` override in the diagnostic config generator | generated YAML with start iter <= 20 | Python config-builder test |
| 9 | Add a named experimental latent mode for `E[u_t]` sensitivity only if diagnostics confirm H1/H3 | e.g. `cap_e_u_and_e_inv_u`, not default | R moment-cap tests and config validation |
| 10 | Add sampling timer extraction/reporting for the c06 walltime issue | sampling walltime table | parser test with synthetic log |
| 11 | Build one parser/report script for the targeted diagnostic roots | `reports/.../README.md` plus CSVs/plots | Python unit test on fixture logs |

Step 9 should not be implemented first. Capping `E[u_t]` changes the VB update behavior and can hide the root cause.
It is a sensitivity experiment, not a first-line diagnosis.

## Targeted Relaunch Design

Use a new isolated runtime root, for example:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/exdqlm_keep_latent_diag_20260529`

Do not modify the completed grid root. Do not touch older protected live roots.

### Phase 0: no-run code/test preparation

Before launching any diagnostic q-lane:

1. add the diagnostic writers behind disabled-by-default config flags;
2. add source-contract tests proving the writers are called at the intended locations;
3. add or extend a test that checks forecast ELBO terms reference `new.sts.out_f`, not `new.uts.out_f`;
4. statically generate the diagnostic configs and verify they differ from the grid configs only by diagnostics and
   declared sensitivity settings.

Acceptance:

- no live or grid root is modified;
- all diagnostics are disabled by default;
- generated diagnostic YAMLs preserve cutoff, bundle, transform, discount factors, epsilon, quantiles, and cleanup
  policy unless the phase explicitly changes one setting.

### Phase A: exact reproductions with better visibility

Run only the failing q-lanes with the same model/data/spec and diagnostic logging enabled:

| target | cutoff | spec | q | guard policy | expected result |
| --- | --- | --- | ---: | --- | --- |
| A1 | `20220511` | `c02_eps090` | `0.20` | fail | should reproduce iter 32 guard and now write top cells |
| A2 | `20221225` | `c03_eps060` | `0.20` | fail | should reproduce iter 47 guard and now write top cells |

Acceptance:

- reproducible failure within +/- 2 iterations, or a documented reason for nondeterminism;
- latent/gamsig/pseudodata top-cell diagnostics identify the source, time/date, block, and exact bad formula term;
- source-3 gamma jump is either confirmed as the first abnormal event or rejected by earlier latent/top-cell evidence;
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

Repeat A1/A2 with only the state guard start changed after Phase A/B have established the baseline trace:

| target | changed setting | unchanged settings |
| --- | --- | --- |
| C1/C2 | `state_guard_start_iter=20` | same q/spec/cutoff, same latent cap, same pseudodata guard |

This tests whether the existing state guard is simply wired outside the 100-iteration budget.

Acceptance:

- if state guard fires before the pseudodata failure and stabilizes the lane, the production fix may include a config
  policy change;
- if state guard does not fire, or fires after source-3 gamma/latent quantities have already gone bad, state guard is
  not the root fix;
- if pseudodata still fails with active state guard, the root is more likely latent/gamma/sigma or pseudo-data formula
  sensitivity.

### Phase D: `E[u_t]` sensitivity, only if justified

Only run this phase if A/B show that `E[u_t]`, `psi`, `chi`, or a direct `u_t` ingredient moves before source-3
gamma/sigma or state feedback.

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

### Phase D2: gamma/sigma near-zero sensitivity, if H3 remains strongest

Only run this phase if A/B confirm that source-3 gamma/sigma moves first.

Candidate sensitivity tests:

| mode | behavior | purpose |
| --- | --- | --- |
| stronger split-interior margin | reject source-3 split candidates closer to support boundaries | tests whether the accepted split-positive candidate is too aggressive |
| source-specific gamma step damping | limit one-iteration gamma movement for source blocks | tests whether the source-3 jump itself drives `FFF` |
| refreeze-before-commit on no-acceptable-split | reuse previous gamma/sigma before the bad state reaches pseudodata | tests whether current refreeze happens too late |
| sigma-only fallback for guard-triggered source block | update sigma but hold gamma near previous/anchor | tests whether gamma movement, not sigma, causes the failure |

Promotion bar:

- the candidate must explain both q20 failures and leave matched controls unchanged or improved;
- the candidate must be named in config and logs;
- the report must distinguish "stabilizes numerical failure" from "improves CRPS".

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
| `latent_update_summary.csv` | per-iteration source/member summaries of `s_t/u_t`, including `psi/chi` |
| `latent_update_top_cells.csv` | top offending latent/GIG cells |
| `gamsig_source_iteration_summary.csv` | source-level gamma/sigma and `FFF` ingredient trajectory |
| `pseudodata_iteration_summary.csv` | concatenated iteration summaries |
| `pseudodata_top_cells.csv` | offending cells with formula ingredients |
| `control_comparison.csv` | failed vs control lanes by first abnormal quantity |
| `state_guard_sensitivity.csv` | baseline vs active-state-guard result |
| `elbo_accounting_check.md` | result of forecast `s_t` ELBO source-contract test and any fix status |
| `sampling_walltime_diagnostics.csv` | c06 sampling-only analysis |
| `recommended_fix_decision.md` | one of: config fix, code fix, sampling fallback, or no change |

Recommended plots:

| plot | reason |
| --- | --- |
| `max_FFF_by_iter.png` | shows sudden vs gradual pseudo-data failure |
| `max_Eu_EinvU_by_iter.png` | separates `E[u_t]` and `E[1/u_t]` regimes |
| `psi_chi_by_iter.png` | shows whether GIG parameters move before `E[u_t]` |
| `gamsig_by_iter_source.png` | shows source-specific gamma/sigma jumps |
| `fff_ingredient_by_iter_source.png` | decomposes `FFF` into numerator and denominator ingredients |
| `state_norm_per_t_by_iter.png` | tests state feedback hypothesis |
| `top_cell_residual_decomposition.png` | explains formula-level failure |

## Fix Decision Tree

Use the diagnostic evidence to choose the smallest correct intervention.

| evidence | next fix |
| --- | --- |
| active state guard prevents A1/A2 without hurting controls | change grid/promotion config so `state_guard_start_iter` is inside the iteration budget |
| `E[u_t]` moves first and capping/freezing that moment fixes A1/A2 while preserving controls | promote a named `E[u_t]` stabilization profile with tests and docs |
| source-3 gamma/sigma terms move first | improve gamma/sigma guard/damping/refreeze, especially around source block `j=3` |
| `E_invb_inv_sigma` denominator collapses first | stabilize gamma/sigma expectation calculation or denominator floor with explicit sensitivity labeling |
| `s_t` moments move first | revisit truncated-normal moment bounds and `s_t` update stabilization |
| transformed near-zero values create tiny `chi` or pathological residual terms | add transform-scale specific guard or input preprocessing check; do not change transform blindly |
| only forecast-member top cells fail | audit forecast segment assembly and member bookkeeping before changing latents |
| only sampling walltime fails with finite fit diagnostics | add sampler fallback/timing guard or classify that spec as failed for runtime reasons |
| only ELBO accounting is wrong and hard guards stay healthy | fix ELBO accounting, but do not relabel it as the q20 pseudodata root cause |

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
4. the ELBO forecast `s_t` source-contract test has either passed or produced a documented code fix;
5. A/B/C diagnostic matrix is generated and statically validated;
6. disk cleanup policy is explicit and compact diagnostics are preserved;
7. the final report template exists before the diagnostic runs start.

The first implementation step should be diagnostic instrumentation, not algorithmic stabilization.
