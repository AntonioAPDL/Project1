# HE2 AL-M-T0 Scale/State Diagnostic Plan Revision - 2026-06-04

## Purpose

This note supersedes the next-step portion of
`docs/he2_al_m_t0_transfer_u_guard_repair_plan_20260604.md`.

The prior plan correctly moved the workflow away from broad relaunches and toward
representative diagnostics, but the second-pass investigation found two important
corrections:

1. The active AL-drop entrypoint still bypasses the state guard in AL mode.
2. The transfer ladder falsifies a purely transfer-covariate explanation for the
   q35/q65 failures.

The immediate goal is now narrower and more rigorous: prove whether the remaining
AL-M-T0 failures are caused by an AL scale/latent-`u_t`/state-update feedback loop,
by disabled or asymmetric stabilization policy, or by a true non-promotable model
geometry for the suspect cutoffs and quantiles.

No broad publication relaunch should start until the gates in this document pass.

## Evidence From The Second-Pass Investigation

| Finding | Evidence | Consequence |
|---|---|---|
| The transfer ladder has a stable control pattern: q80 controls pass and q35/q65 suspect lanes fail across valid A0-A4 rows | `docs/he2_al_m_t0_transfer_ladder_terminal_findings_20260604.md`; `reports/he2_al_m_t0_transfer_ladder_live_20260604/diagnostic_ladder_live_status.csv` | This is lane-specific, not a generic runner failure |
| `a1_transfer_level_only` still fails q35/q65 even with no transfer covariate driver rows | `a1_transfer_level_only` terminal health: q35 `max_abs_history_exps` about 13131 and `state_norm_sq_per_T` about `1.07e8`, while `transfer_level_max_abs` is about 2.41 | Transfer covariate rows are not sufficient to explain the failure |
| q80 controls under the same A1 no-driver experiment pass | q80 terminal health: `max_abs_history_exps` about 3.68 and `state_norm_sq_per_T` about 4.49 | The no-driver design itself is not inherently broken |
| Failed q35/q65 logs show a two-cycle in the last iterations | A1 q35 alternates between `sigma_exp=0.2486072`, `state_norm_sq=58725.97` and `sigma_exp=999.956`, `state_norm_sq=1.3493644e12`; A1 q65 shows the same high/low alternation | Terminal state can be determined by iteration parity; this is update-cycle instability, not smooth convergence |
| The active AL-drop entrypoint still bypasses state guards | `DISC_Optimal_Synth_Ranges_W.r:3770-3771` has `state_guard_active <- (!isTRUE(DISC_W_AL_MODE) && isTRUE(state_guard_enabled))` | Any AL-drop diagnostic that relies on state guard protection is currently under-protected |
| The transfer-forecast entrypoint has the intended guard condition | `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:5868-5869` has `state_guard_active <- (isTRUE(state_guard_enabled) && iter >= DISC_GAMSIG_STATE_GUARD_START_ITER)` | The two legacy entrypoints are inconsistent and must be reconciled |
| Quantile overrides are real and propagated | `R/unified/stages/stage_fit.R:441-456` resolves `quantile_overrides`; env export happens around `R/unified/stages/stage_fit.R:1318-1510` | Policy experiments must record the resolved per-quantile policy, not only the base config |
| Terminal sampling guard was off in the failed A1 rows | failed logs show `mode=off`, `guard_count=0`, `blocked=false` | Terminal invalidity is detected after the fact, not prevented before sampling/post |

## Current Interpretation

The best current explanation is an interaction defect or model-geometry failure in
the AL sigma/latent-`u_t`/pseudo-data/state layer.

This is more precise than saying "the transfer function is unstable." In AL mode,
`gamma` and `s_t` are intentionally fixed at zero, so the dangerous channel is the
AL scale and `u_t` moments feeding pseudo-data and then the Kalman state update.
The transfer block can amplify the problem in some runs, but A1 proves it is not
the only driver. The active drop path also disables exactly the guard intended to
stop impossible state growth, so algorithmic protection must be repaired before
we interpret further launch outcomes as scientific evidence.

## Non-Negotiable Gates

A result is not promotable unless all of these are true:

1. Both legacy multivariate entrypoints have the same AL state-guard semantics.
2. Logs report both configured and effective guard policy, including likelihood
   mode and any disabled reason.
3. Terminal health fails q35/q65 retained bad fits and passes q80 retained controls.
4. A two-cycle detector reports no terminal high/low alternation in accepted fits.
5. `E[u_t]`, `E[1/u_t]`, `FFF`, `QQQ`, and state norms are finite and within
   documented diagnostic caps.
6. Failed lanes produce explicit failure rows and cannot enter CRPS winner
   selection or article tables silently.
7. Runtime `.RData` is retained only for diagnostics and cleaned after post/report
   in production-style launches.

## Phase 0: Freeze Evidence

Do this before any more launches.

1. Preserve the A1 q35/q65/q80 `.RData` files until one-at-a-time decomposition is
   complete.
2. Preserve the final ladder status CSV and Markdown under `reports/`.
3. Confirm `git status` is clean except intentional doc/code changes.
4. Do not clean these diagnostic `.RData` files yet:
   - `20211112 q35` A1 no-driver failure;
   - `20220511 q65` A1 no-driver failure;
   - `20211221 q80` and `20221225 q80` controls.

Exit gate: a manifest names every retained artifact used by the next phases.

## Phase 1: Repair And Prove Code-Path Parity

Goal: remove the current inconsistency between AL-drop and transfer-forecast paths.

Implementation:

1. Patch `DISC_Optimal_Synth_Ranges_W.r` so AL mode no longer disables
   `state_guard_active`.
2. Match the transfer-forecast condition:
   `state_guard_enabled && iter >= DISC_GAMSIG_STATE_GUARD_START_ITER`.
3. Add or extend logging so both entrypoints print:
   - `likelihood_mode`;
   - `state_guard_configured`;
   - `state_guard_effective`;
   - `state_guard_disabled_reason`;
   - `state_guard_start_iter`;
   - `freeze_target`;
   - terminal sampling guard mode.
4. Add deterministic tests or static assertions that both entrypoints have no
   AL-mode state-guard bypass.
5. Re-run targeted parse and test checks for both entrypoints.

Exit gate: a small AL synthetic or static test proves an AL fit can trigger state
guard protection in both legacy scripts.

## Phase 2: Add A Log-Level Two-Cycle Detector

Goal: catch the observed high/low oscillation without loading multi-GB `.RData`.

Implementation:

1. Build a parser for `[gamsig_progress]` rows that emits:
   - final iteration;
   - final `ELBO`;
   - final `sigma_exp`;
   - final `gamma_exp`;
   - final `state_norm_sq`;
   - last-10 min/max ratios for sigma and state norm;
   - parity alternation count;
   - `guard_count`;
   - terminal sampling guard mode.
2. Classify a run as `two_cycle_suspect` when the last 6-10 iterations alternate
   between two separated sigma/state regimes.
3. Add this to the diagnostic monitor and write CSV plus Markdown under `reports/`.

Exit gate: A1 q35/q65 are classified as two-cycle suspect; A1 q80 controls are not.

## Phase 3: One-At-A-Time Saved-State Decomposition

Goal: identify what block drives A1 q35/q65 when transfer covariate rows are absent.

Implementation:

1. Load one retained `.RData` at a time.
2. Immediately extract and save compact summaries, then `rm(...)` and `gc()`.
3. Report:
   - `theta.out$exps` max locations by source/time;
   - state block norms;
   - top state coordinates by absolute value;
   - historical versus forecast split;
   - transfer level and coefficient blocks, where present;
   - `new.gamsig.out` terminal summaries;
   - `new.uts.out` summaries if objects are available;
   - reconstructed location checks from state loadings.
4. Produce comparison tables for A1 q35/q65 failures versus q80 controls.

Exit gate: we know whether A1 q35/q65 failures are driven by shared trend/seasonal
coordinates, discrepancy coordinates, transfer level, or another block.

## Phase 4: Latent `u_t` And Pseudo-Data Audit

Goal: determine whether AL `u_t` moments are the direct source of bad pseudo-data.

Implementation:

1. Recompute or summarize:
   - `E[u_t]`;
   - `E[1/u_t]`;
   - `E[log u_t]`, where available;
   - floor/saturation fractions;
   - `FFF` ranges;
   - `QQQ` ranges.
2. Compare the same summaries across:
   - A1 q35 failure;
   - A1 q65 failure;
   - A1 q80 controls.
3. Flag whether the two-cycle correlates with:
   - `sigma_exp` hitting the upper bound;
   - collapsed or explosive `E[1/u_t]`;
   - near-zero `QQQ`;
   - extreme pseudo-observation location `FFF`.

Exit gate: we can say whether `u_t`/pseudo-data is a primary mechanism or only a
downstream symptom of sigma/state oscillation.

## Phase 5: Minimal Controlled Relaunch Matrix

Only launch after Phases 1-4 have produced their artifacts.

Run fit-only diagnostics first, one core per quantile, no post, retain `.RData`
only until decomposition is complete.

| Experiment | q35/q65 suspect lanes | q80 controls | Purpose |
|---|---:|---:|---|
| P0 patched baseline | yes | yes | Tests whether fixing AL-drop guard parity is sufficient |
| P1 patched baseline plus terminal guard `fail_fast` | yes | yes | Prevents invalid terminal state from sampling/post |
| P2 force `freeze_target=gamma_sigma` for q35/q65 | yes | yes | Tests whether q35 state-freeze policy contributes |
| P3 force `freeze_target=states` for q80 controls | optional | yes | Negative control for policy asymmetry |
| P4 tighter sigma upper bound | yes | yes | Tests whether the two-cycle is scale-bound driven |
| P5 detection-only `u_t`/pseudo-data guard | yes | yes | Confirms if latent moments become unhealthy before state blow-up |

Do not run a broad cutoff grid in this phase. The minimum scientifically useful
set is `20211112 q35`, `20220511 q65`, `20211221 q80`, and `20221225 q80`.

Exit gate: at least one candidate passes q35/q65 and q80 controls without terminal
two-cycle, impossible state norms, or latent/pseudo-data violations. If none pass,
AL-M-T0 should be excluded or reported as failed for this article table rather
than tuned indefinitely.

## Phase 6: Promotion Rules

Promote only after the candidate passes Phase 5.

1. Update canonical builders with the selected policy and guard settings.
2. Require terminal health before post.
3. Require two-cycle-free logs before CRPS winner selection.
4. Require CRPS tables to include explicit failure rows for failed candidates.
5. Keep production cleanup enabled so `.RData` is removed after post/report unless
   a diagnostic retain flag is explicitly set.
6. Cross-link output manifests to the revised article figure/table generation.

## Phase 7: Documentation And Tests

Required tracked updates:

1. This revision doc.
2. A short correction note in the older repair plan pointing here.
3. Tests for AL guard parity across both legacy entrypoints.
4. Tests for the two-cycle parser.
5. Tests or fixtures for retained q35/q65 fail and q80 pass terminal status.
6. Launcher/monitor docs showing that `reports/` remains untracked.

Suggested validation commands:

```bash
Rscript --vanilla -e "invisible(parse('DISC_Optimal_Synth_Ranges_W.r')); invisible(parse('DISC_Optimal_Synth_Ranges_W_transfer_forecast.r')); invisible(parse('R/unified/stages/stage_fit.R')); cat('parse_ok\n')"
Rscript --vanilla -e "library(testthat); test_file('tests/testthat/test_exdqlm_multivar_terminal_health.R'); test_file('tests/testthat/test_exdqlm_multivar_keep_latent_pseudodata_audit.R')"
python3 -m unittest tests.python.test_stage_fit_quantile_gamma_sigma_overrides tests.python.test_he2_al_m_t0_diagnostic_plan
```

## Immediate Next Actions

1. Patch AL-drop guard parity in `DISC_Optimal_Synth_Ranges_W.r`.
2. Add a deterministic/static test that prevents AL state-guard bypass from
   reappearing in either legacy entrypoint.
3. Add the log-level two-cycle parser and classify the retained A1 rows.
4. Run one-at-a-time RData decomposition for A1 q35/q65/q80.
5. Decide whether Phase 5 should start with P0/P1 only or the full P0-P5 matrix.

The plan is intentionally front-loaded with non-invasive evidence extraction.
That is the fastest way to avoid confusing a real AL update-cycle defect with a
model-spec tuning problem.
