# HE2 AL-M-T0 P5 Post-Save Objective Repair Plan - 2026-06-06

## Decision

Promote a P5 candidate for the remaining AL-M-T0 q80 failure:

- keep the scientific/input contract from P4;
- set q65/q80 `warmup_freeze_iters` to `40`;
- keep q65 damping and q80 robust initialization;
- harden only the post-save objective diagnostic path after
  `disc_w_save_state(...)`.

## Evidence

The warmup-20 diagnostic showed:

| Lane | Result | Interpretation |
|---|---|---|
| `20210123 q80` | failed after sampling and RData save with `dmvnorm.deriv.unique -> chol` | remaining defect is post-save diagnostic covariance handling, not VB warm-up |
| `20211221 q65` | completed fit stage | q65 guard/damping path is valid under the isolated diagnostic |

Runtime summary:

`reports/he2_al_m_t0_p4_warmup20_repair_q65q80_20260606/WARMUP20_REPAIR_Q65Q80_SUMMARY.md`

## Source Fix

The robust fix is deliberately scoped after the saved-state boundary:

1. fit, VB updates, terminal sampling, and `disc_w_save_state(...)` remain
   fatal if they fail;
2. after the RData is saved, standard forecast error diagnostics are summarized;
3. post-save KL/JSD metric failures are logged with
   `[post_save_objective_metric_error]`;
4. if the KDE/KNN KL metric is non-finite, a moment-based empirical Gaussian KL
   fallback is computed and logged with `[post_save_objective_fallback]`;
5. the already saved fit is allowed to complete.

Patched source files:

- `DISC_Optimal_Synth_Ranges_W.r`;
- `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r`.

## P5 Overlay

Tracked overlay:

`config/he2_relaunch_batches/al_m_t0_p5_q65_q80_warmup40_postsave_overlay_20260606.yaml`

Spec id:

`al_m_t0_p5_q65_q80_warmup40_postsave_highdf_eps365_cf1_20260606`

## Validation Gate

Before promotion:

1. parse both patched DISC scripts;
2. run focused Python builder/validator tests;
3. prelaunch-validate generated P5 configs for `20210123`;
4. relaunch only `20210123 q80`;
5. require the q80 log to show:
   - `warmup_freeze_iters=40`;
   - at least 50 gamma/sigma updates;
   - `Sampling finished`;
   - `Variables saved`;
   - no `Execution halted`;
   - if the old KL path is still non-PD, a non-fatal
     `[post_save_objective_metric_error]` plus fallback log.

Only after q80 passes should we rebuild the relevant AL-M-T0 rows.
