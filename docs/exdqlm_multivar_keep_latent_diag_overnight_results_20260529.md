# exDQLM Multivar Keep Latent Diagnostic Ladder Results - 2026-05-29

## Scope

This documents the completed A/B/C latent diagnostic ladder launched from
`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/exdqlm_keep_latent_diag_20260529_prepared`
using:

- matrix plan: `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/exdqlm_keep_latent_diag_20260529_prepared/control/latent_diag_matrix/latent_diag_matrix_plan.csv`
- controller status: `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/exdqlm_keep_latent_diag_20260529_prepared/control/overnight_ladder/phase_status.csv`
- final live status: `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/exdqlm_keep_latent_diag_20260529_prepared/control/overnight_ladder/LIVE_STATUS.md`
- final report: `reports/he2_exdqlm_multivar_keep_latent_diag_overnight_20260529/all_phases_final/`

The run completed at `2026-05-29T10:29:51Z`. No `.RData`, `.rdata`, `.Rda`, `.rda`, or
`.RData.tmp.*` files remained under the diagnostic runtime root at completion.

## Controller Outcome

| phase | purpose | rows | outcome |
| --- | --- | ---: | --- |
| A | exact reproductions of the two failed q20 lanes | 2 | both failed in fit |
| B | matched controls / epsilon-spec perturbations | 6 | two passed end-to-end; four had completed fit but failed post before the single-q post guard patch |
| C | guarded sensitivity rows for the two Phase A failures | 2 | both failed in fit with the same instability signature |

Final controller count: 2 pass, 8 fail. The four Phase B post failures should not be interpreted as
fit instability; they were q20-only post-stage synthesis failures from before
`bbcd7a6 Skip multivar synthesis for single-quantile diagnostics`.

## Confirmed Fit Failure Signature

The repeated failure is upstream of the Kalman/state-space layer. In the failing rows, source_2 gamma moves down a
near-zero split-positive path, then a regularized Hessian/fallback step jumps gamma upward and immediately makes the
latent `E[u_t]` and pseudo-data unstable.

Confirmed examples:

| row | failure iter | gamma/sigma evidence | pseudo-data evidence |
| --- | ---: | --- | --- |
| A `20220511 c02_eps090 q20` | 32 | source_2 guard fallback after near-zero path | `FFF/history` max_abs about 22417.9; `E_uts/history` about 1.0096e6 |
| A `20221225 c03_eps060 q20` | 47 | source_2 guard fallback after near-zero path | `FFF/history` about 22518.8; `FFF_forecast` about 14700.7; `E_uts` about 1.0e6 |
| C `20220511 c02_eps090 q20` | 32 | same source_2 fallback/refreeze as Phase A | same top bad cells, including `2008-01-04` source_2 |
| C `20221225 c03_eps060 q20` | 47 | same source_2 fallback/refreeze as Phase A | same historical and forecast pseudo-data cap breaches |

Key files:

- `reports/he2_exdqlm_multivar_keep_latent_diag_overnight_20260529/all_phases_final/pseudodata_guard_events.csv`
- `reports/he2_exdqlm_multivar_keep_latent_diag_overnight_20260529/all_phases_final/first_bad_pseudodata_by_lane.csv`
- `reports/he2_exdqlm_multivar_keep_latent_diag_overnight_20260529/all_phases_final/pseudodata_top_cells.csv`
- `reports/he2_exdqlm_multivar_keep_latent_diag_overnight_20260529/all_phases_final/gamsig_source_iteration_summary.csv`

## What Phase B Adds

The two completed 20211112 controls passed fit, post, validate, and report:

- `20211112 c02_eps090 q20`
- `20211112 c03_eps060 q20`

During late fit these controls also approached a small source_2 gamma regime, but they did not hit the destructive
fallback/pseudo-data cap breach. This supports a spec/cutoff-sensitive interaction rather than a universal Kalman or
state-space implementation failure.

The q20-only post guard added in `bbcd7a6` is confirmed operational by these two end-to-end passes. The formal
multi-quantile synthesis helper still rejects single-quantile synthesis; the smoke-fast post caller now skips products
that are mathematically unavailable for q20-only diagnostics.

## Interpretation

Most likely root layer:

1. gamma/sigma approximation and candidate acceptance/refreeze behavior,
2. interacting with the latent `u_t` update,
3. propagating into `FFF`/`QQQ` pseudo-data.

Less likely as primary root cause from this ladder:

- compiled Kalman/RTS layer, because the hard failures occur before state update completion at the pseudo-data guard;
- transfer/trend/discrepancy identifiability alone, because the immediate trigger is localized source_2 gamma fallback
  and latent `E[u_t]` explosion;
- forecast bookkeeping alone, because 20220511 fails in historical `FFF/history` first, while 20221225 fails in both
  history and forecast after the same source_2 gamma event.

## Prioritized Fix Plan

1. Change gamma/sigma candidate acceptance from local-only acceptance to downstream-safe acceptance: a candidate should
   not be committed if it produces non-finite objective values, guard-triggered split rejection, or downstream
   pseudo-data/latent caps on a cheap trial update.
2. On source-level guard failure, roll back to the last stable gamma/sigma state before constructing pseudo-data. The
   current behavior can refreeze after committing a destructive fallback value, which is too late.
3. Add and test a diagnostic mode that caps or freezes both `E[u_t]` and `E[1/u_t]`, not only `E[1/u_t]`; the observed
   breaches are driven directly by `E[u_t]` reaching about `1e6`.
4. Promote pseudo-data guard checks to a pre-commit rollback path in the VB loop, while retaining hard-fail mode for
   diagnostics.
5. Rerun a minimal ladder after each fix: the two Phase A controls, the two 20211112 healthy controls, then the two
   Phase C-style guarded rows.
6. Only after those pass, relaunch the selected all-quantile/cutoff production experiments.

