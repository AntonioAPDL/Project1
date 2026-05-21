# exDQLM Multivariate Keep Guard-Response Policy

Date: 2026-05-21

## Purpose

This document closes the policy part of tracker item `T4`. It defines how to treat q05-like latent-tail and
pseudo-data events while the remaining ablations finish. It is intentionally conservative: the current evidence
supports guardrails and gamma/sigma damping/refreeze controls, but it does not yet justify silently clipping latent
moments in production.

## Active Guard Surfaces

The active runner has three relevant guard surfaces.

1. Pseudo-data/latent magnitude guard.

   Active code: `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:3137-3260`.

   It checks historical and forecast `FFF`, `QQQ` diagonals, `E[s]`, `E[s^2]`, `E[u]`, and `E[1/u]`.
   Bad rows are written to `pseudodata_guard_events.csv` when `DISC_PSEUDODATA_GUARD_REPORT_DIR` is set.
   `DISC_PSEUDODATA_GUARD_MODE=warn` reports and continues; `DISC_PSEUDODATA_GUARD_MODE=fail` stops before the
   next Kalman update consumes bad pseudo-data.

2. State-norm gamma/sigma guard.

   Active code: `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:4530-4624`.

   When enabled, it detects nonfinite state norms, absolute state-norm cap breaches, or sudden state-norm growth.
   On trigger, it reverts the proposed state/latent/gamma-sigma/covariance update to the previous iterate and
   extends the gamma/sigma refreeze/hold window.

3. Terminal sampling guard.

   Active code: `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:4733-4793`.

   This prevents entering posterior sampling after a recent or still-frozen state guard, depending on the configured
   terminal guard mode.

The isolated repro preparer exposes these controls without touching production roots:
`repro/audits/prepare_exdqlm_keep_guarded_repro.py:84-99,143-149,159-166`.

## Evidence So Far

Guarded repaired control:

- evidence root:
  `reports/exdqlm_keep_guarded_repro_guarded_log1p_q05_q35_q50_q95_20260521/`
- q05 wrote 18 historical `E_inv_uts` guard rows at iterations `1001-1018`, peak `14397.595`;
- no `FFF`, `QQQ_diag`, forecast pseudo-data, `E[s]`, `E[s^2]`, or `E[u]` guard rows were written.

Fixed-gamsig v3:

- evidence roots:
  `reports/exdqlm_keep_guarded_repro_ablation_log1p_q05_q35_q50_q95_v3_20260521_fixed_gamsig/`,
  `reports/exdqlm_keep_runtime_stability_ablation_log1p_q05_q35_q50_q95_v3_20260521_fixed_gamsig/`,
  `reports/exdqlm_keep_decomposition_ablation_log1p_q05_q35_q50_q95_v3_20260521_fixed_gamsig/`;
- all four lanes wrote `.RData` with `gamsig_update_iters=0` and `frozen=true`;
- no pseudo-data guard rows were written;
- saved-output historical `E[1/u]` maxima remained below the current `5000` cap, although q95/source1 and
  q05/source1 were close enough to require monitoring (`4818.429` and `4401.679` respectively).

Latent-freeze v3 is still running at this tracker point. Mid-fit logs show q05/q95 state norm squared near `8e6`
with very large gamma magnitudes and no pseudo-data guard CSV yet. That is not a final result, but it is already
inconsistent with a simple "latent formulas alone explain everything" story.

## Policy Decision

For diagnostic ablations:

- keep `DISC_PSEUDODATA_GUARD_MODE=warn`;
- always write `pseudodata_guard_events.csv`;
- never silently clip `E[1/u]` unless the run is explicitly labeled `latent-cap-e-inv-u` or
  `fixed-gamsig-latent-cap`.

For promotion candidates and broad production relaunches:

- switch pseudo-data guard mode to `fail`;
- retain the current caps as initial promotion thresholds:
  `FFF=1000`, `QQQ_diag=10000`, `E[s]=1000`, `E[s^2]=1e6`, `E[u]=1e6`, `E[1/u]=5000`;
- enable state-norm guard/refreeze controls and terminal sampling guard for any lane whose state norm has shown
  growth bursts in diagnostics;
- treat any q05-like `E[1/u]` cap breach as a failed promotion run until the latent-cap ablation proves that
  capping is scientifically harmless.

## What Not To Do Yet

Do not promote latent `E[1/u]` capping as the default production fix yet. It is useful as a diagnostic ablation,
but capping changes the pseudo-observation precision directly. Until the latent-cap run and decomposition checks
show no material distortion, fail-fast is the defensible production behavior.

Do not infer stability from terminal state norm alone. The fixed-gamsig v3 outputs are finite, but saved-output
latent tails can still be close to the cap and q95 component magnitudes remain large.

## Tests And Reproducibility

Current focused tests:

- `tests/testthat/test_exdqlm_multivar_keep_latent_pseudodata_audit.R` validates latent formulas, pseudo-data
  algebra, guard classification, and active-runner wiring for guard/ablation controls.
- `tests/python/test_exdqlm_keep_ablation_tooling.py` validates generated isolated launchers, including
  guard-mode exports and latent-cap exports.
- `tests/testthat/test_exdqlm_keep_decomposition_audit.R` validates that the decomposition audit reconstructs
  historical and ragged forecast `new.theta.out$exps` rows exactly on a deterministic fixture.

Recommended next runtime check:

1. Finish latent-freeze and latent-cap v3 ablations.
2. Run runtime stability and decomposition audits on both.
3. If latent-cap suppresses q05/q95 state and `E[1/u]` excursions without changing reconstruction/component
   behavior materially, promote a separate capped candidate. Otherwise keep fail-fast and prioritize gamma/sigma
   damping/refreeze.
