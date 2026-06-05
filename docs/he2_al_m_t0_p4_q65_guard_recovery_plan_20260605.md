# HE2 AL-M-T0 P4 q65 Guard-Recovery Plan - 2026-06-05

## Purpose

This plan supersedes direct AL-M-T0 production promotion after the P3
full-design smoke.

P3 fixed the stale q50 states-freeze inheritance and showed no terminal
two-cycle. It still failed the promotion gate because the 20220511 q65 lane
entered a deterministic state-guard lockout: every attempted state update was
rejected by the state-growth guard, the fit was rolled back to the previous
state/gamma/sigma values, and `gamsig_update_iters` stayed at zero until the
terminal sampling preflight failed.

The P4 hypothesis is therefore precise:

1. the active algorithmic guard is doing the right safety check;
2. the P3 q65 recovery policy is too coarse because it retries full state steps
   after long refreeze/hold intervals;
3. q65 should be repaired by damping the state/covariance update before the
   guard check, not by weakening the terminal health gate.

## Evidence Lock

Primary P3 smoke artifacts:

| Evidence | Path |
|---|---|
| P3 overlay | `config/he2_relaunch_batches/al_m_t0_p3_production_overlay_20260605.yaml` |
| P3 fit summary | `reports/he2_al_m_t0_p3_production_smoke_20260605/fit_log_summary/P3_SMOKE_FIT_LOG_SUMMARY.md` |
| P3 cycle audit | `reports/he2_al_m_t0_p3_production_smoke_20260605/cycles/GAMSIG_CYCLE_AUDIT.md` |
| failing q65 fit log | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_dqlm_multivar_al_drop_p3_smoke_20260605/runs/multimodel_20220511_v8_he2pubgdpc1r1_dqlm_multivar_al_drop/fit/q=65/logs/fit.log` |
| failing q65 sampling diagnostics | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_dqlm_multivar_al_drop_p3_smoke_20260605/runs/multimodel_20220511_v8_he2pubgdpc1r1_dqlm_multivar_al_drop/fit/q=65/logs/sampling_diagnostics.log` |

Observed P3 terminal table:

| cutoff | q | iter | updates | sigma | state norm sq | guards | frozen | error |
|---|---:|---:|---:|---:|---:|---:|---|---|
| 20220511 | 65 | 160 | 0 | 0.1813254 | 42047.93 | 15 | true | yes |

The key failure line in the failing sampling diagnostics is the terminal
preflight blocking condition: `update_iters=0 min_update_iters=50`. The cycle
audit reports `two_cycle=False`, so this is not the old sigma/state two-cycle
failure.

## Source Contract

The active code path already supports the intended repair.

| Contract | Active source |
|---|---|
| quantile-specific gamma/sigma policy merge | `R/unified/stages/stage_fit.R`, `unified_resolve_gamma_sigma_policy(...)` |
| q-specific `max_iter` export | `R/unified/stages/stage_fit.R`, `DISC_GAMSIG_MAX_ITER` setup |
| q-specific state/cov blend export | `R/unified/stages/stage_fit.R`, `DISC_GAMSIG_STATE_BLEND_ALPHA` and `DISC_GAMSIG_COV_BLEND_ALPHA` setup |
| state/cov blending before guard check | `DISC_Optimal_Synth_Ranges_W.r`, `disc_blend_numeric_like(...)` and `disc_blend_numeric_list(...)` |
| state-growth guard rollback and terminal fail-fast | `DISC_Optimal_Synth_Ranges_W.r`, `[gamsig_state_guard]` and `[sampling_preflight]` blocks |

Because blending is applied before the guard evaluates `state_growth_ratio`, P4
can test a smaller accepted q65 state step without changing the mathematical
likelihood, input bundle, or post-processing contract.

## P4 Overlay

Tracked overlay:

`config/he2_relaunch_batches/al_m_t0_p4_q65_guard_recovery_overlay_20260605.yaml`

The overlay preserves P3:

- AL likelihood for the target family;
- transfer drop;
- canonical 20260510 input bundle;
- data start `1987-05-29`;
- full transfer design;
- covariates `PPT`, `SOIL`, `PCA`;
- lags `1,2,3`;
- squares and PPT-SOIL interaction;
- harmonic indices `[1,2,3]`;
- log1p-only scale contract;
- `df_* = 0.99999999`;
- `lambda = 0.97`;
- `epsilon = 365`;
- `c_factor = 1`;
- q35 P3 policy;
- terminal sampling fail-fast;
- q50 stale source override drop.

P4 changes only q65:

| Field | P3 | P4 |
|---|---:|---:|
| `max_iter` | 160 inherited | 220 q65-only |
| `state_guard_refreeze_iters` | 10 | 2 |
| `state_hold_after_guard_iters` | 10 | 0 |
| `state_blend_alpha` | 1.0 | 0.15 |
| `cov_blend_alpha` | 1.0 | 0.5 |
| `state_norm_max_ratio` | 25 | 25 |
| terminal sampling guard | fail-fast | fail-fast |

## Implementation And Launch Plan

1. Add P4 overlay and documentation.
2. Add/extend builder and validator tests so generated configs prove:
   - q65 carries the P4 recovery policy;
   - q35 remains on P3;
   - q50 is still dropped;
   - no quantile-level `freeze_target=states` override remains.
3. Run focused Python/R source tests and prelaunch validation without smoke.
4. Launch an isolated 20220511 q65 fit-only diagnostic:
   - one quantile only;
   - no post/validate/report;
   - retain `.RData` only long enough for terminal health and cycle audit;
   - use the P4 overlay-generated config as the source of truth.
5. Monitor q65 until terminal:
   - `gamsig_update_iters >= 50`;
   - no terminal two-cycle;
   - finite sigma and state norm;
   - terminal sampling preflight does not block;
   - state guard, if present, no longer locks updates at zero.
6. If isolated q65 passes, rebuild and launch the full two-cutoff P4 smoke:
   - cutoffs `20211112` and `20220511`;
   - all seven quantiles;
   - full post/validate/report;
   - cleanup after post enabled.
7. Promote AL-M-T0 only if the full smoke passes:
   - fit/post/validate/report pass for both rows;
   - CRPS tables and publication figure manifests exist;
   - no retained `.RData/.rda/.Rda` under successful run roots;
   - failure rows remain explicit and block promotion.

## Decision Rules

P4 is considered successful only if it converts the P3 q65 failure from
`updates=0` into a terminal healthy fit with at least 50 gamma/sigma updates.

P4 is not considered successful if it merely hides the failure by:

- disabling the state guard;
- increasing `state_norm_max_ratio`;
- disabling terminal fail-fast;
- lowering `min_update_iters`;
- using a different input bundle or transfer design.

If P4 still fails, the next diagnostic should compare a small grid of q65
`state_blend_alpha` values (`0.05`, `0.10`, `0.25`) against the same fixed
terminal gates before any broader production rerun.

## Isolated q65 Result

The first isolated q65 diagnostic exposed a dormant implementation defect in the
duplicated state-blend helper inside `DISC_Optimal_Synth_Ranges_W.r`: the helper
did not tolerate optional `NULL` theta payloads when `state_blend_alpha < 1`.
The tested helper in `R/disc_w/09_state_blend.R` already had the correct
semantics. The live entrypoint copy was brought into parity and the source
contract now checks for these `NULL` guards.

Post-fix isolated diagnostic:

| Item | Value |
|---|---|
| run root | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_dqlm_multivar_al_drop_p4_q65_guard_recovery_20260605/runs/multimodel_20220511_v8_he2pubgdpc1r1_dqlm_multivar_al_drop_p4q65fitonly_blendfix_20260605` |
| final summary | `reports/he2_al_m_t0_p4_q65_guard_recovery_20260605/q65_fitonly_blendfix_final/Q65_FITONLY_BLENDFIX_FINAL_SUMMARY.md` |
| cycle audit | `reports/he2_al_m_t0_p4_q65_guard_recovery_20260605/q65_fitonly_blendfix_cycles/GAMSIG_CYCLE_AUDIT.md` |
| fit stage | pass |
| final iteration | 220 |
| gamma/sigma update iterations | 215 |
| state guards | 0 |
| two-cycle suspect | false |
| final `E[sigma]` mean | 0.05764058 |
| final `E[gamma]` mean | 0 |
| final state norm sq | 21059.15 |
| state norm sq per T | 1.64949875793094 |
| terminal health violations | 0 |

The 7.1 GB isolated diagnostic `.RData` was removed after preserving the compact
log, cycle, forecast-health, and terminal-health evidence. This keeps the P4
root usable without accumulating avoidable disk pressure.

This result satisfies the isolated q65 gate and authorizes a full two-cutoff P4
smoke, not full production promotion. Production remains gated on the all-seven
quantile, full-post smoke for `20211112` and `20220511`.

## Full Two-Cutoff P4 Smoke Result

The full P4 smoke passed on commit
`a354b7894d13fd3d5e76d137ec27b258d7e3e89f`.

| Item | Evidence |
|---|---|
| smoke root | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_dqlm_multivar_al_drop_p4_smoke_20260605` |
| matrix status | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_dqlm_multivar_al_drop_p4_smoke_20260605/control/publication_relaunch_matrix/matrix_status.csv` |
| final fit-log summary | `reports/he2_al_m_t0_p4_smoke_20260605/final_fit_logs/P4_SMOKE_FINAL_FIT_LOG_SUMMARY.md` |
| final cycle audit | `reports/he2_al_m_t0_p4_smoke_20260605/final_cycles/GAMSIG_CYCLE_AUDIT.md` |
| final runtime report | `reports/he2_al_m_t0_p4_smoke_20260605/P4_SMOKE_FINAL_REPORT.md` |

Both smoke rows closed with `phase=report`, `status=pass`:

| cutoff | final phase | status | finished UTC |
|---|---|---|---|
| `20211112` | report | pass | 2026-06-05T10:03:12Z |
| `20220511` | report | pass | 2026-06-05T10:07:04Z |

The q65 recovery gate passed for both cutoffs:

| cutoff | q | final iter | updates | sigma | gamma | state norm sq/T | guards | two-cycle | terminal fail |
|---|---:|---:|---:|---:|---:|---:|---:|---|---:|
| `20211112` | 0.65 | 220 | 215 | 0.05754201 | 0 | 3.84727109785607 | 0 | false | 0 |
| `20220511` | 0.65 | 220 | 215 | 0.05764058 | 0 | 1.64949875793094 | 0 | false | 0 |

The final cycle audit reports `two-cycle=False` for all 14 quantile fits. The
post artifact contracts passed for both cutoffs, including synthesis cache
shape checks, figure presence, and table-export presence.

CRPS smoke outputs were produced with finite truth availability:

| cutoff | model | horizon | mean CRPS | median CRPS |
|---|---|---:|---:|---:|
| `20211112` | `dqlm_multivar_al_synth_drop` | 28 | 0.19741118135136021 | 0.20144921851044836 |
| `20211112` | `glofas_ensemble` | 28 | 0.16957475641561054 | 0.17538905902916158 |
| `20211112` | `nws_nwm_ensemble` | 8 | 1.3719166338517021 | 1.3605649135592990 |
| `20220511` | `dqlm_multivar_al_synth_drop` | 28 | 0.21550211143045339 | 0.21906773159992321 |
| `20220511` | `glofas_ensemble` | 28 | 0.27226751146296652 | 0.26428106570693211 |
| `20220511` | `nws_nwm_ensemble` | 8 | 0.28365909559653485 | 0.28612739832195971 |

Successful-run `.RData` cleanup also passed: there are zero retained fit
`.RData` files under the P4 smoke run roots after post/report completion, and
disk recovered to 138 GB free on `/data`.

This result satisfies the P4 two-cutoff smoke gate. The next promotion step is
to prepare the five-cutoff AL-M-T0 production matrix using the P4 q65 policy and
the same scientific/input contract, then run the usual no-launch validation
before starting production.
