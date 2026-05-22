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
   extends the gamma/sigma refreeze/hold window. Promotion candidates can delay activation with
   `DISC_GAMSIG_STATE_GUARD_START_ITER`; this prevents the guard from trapping q05/q95 during the early recovery
   phase before the latent-cap path settles.

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

Latent-freeze v3:

- evidence roots:
  `reports/exdqlm_keep_guarded_repro_ablation_log1p_q05_q35_q50_q95_v3_20260521_latent_freeze/`,
  `reports/exdqlm_keep_runtime_stability_ablation_log1p_q05_q35_q50_q95_v3_20260521_latent_freeze/`,
  `reports/exdqlm_keep_decomposition_ablation_log1p_q05_q35_q50_q95_v3_20260521_latent_freeze/`;
- all four lanes wrote `.RData` and post/validate/report completed under the missing-truth gate;
- no pseudo-data guard rows were written;
- q05 and q95 remained scientifically unstable-looking despite fixed latent moments:
  terminal state norm squared was `8011171` for q05 and `8190166` for q95;
- q05/q95 gamma/sigma drifted to large asymmetric values:
  q05 `sigma_exp=3.065681`, `gamma_exp=6.756436`; q95 `sigma_exp=3.075551`, `gamma_exp=-6.76794`.

This is inconsistent with a simple "latent formulas alone explain everything" story. It supports treating
`sigma/gamma` dynamics and `sigma/gamma`-state interaction as a decisive remaining risk.

Latent-cap v3:

- evidence roots:
  `reports/exdqlm_keep_guarded_repro_ablation_log1p_q05_q35_q50_q95_v3_20260521_latent_cap_e_inv_u/`,
  `reports/exdqlm_keep_runtime_stability_ablation_log1p_q05_q35_q50_q95_v3_20260521_latent_cap_e_inv_u/`,
  `reports/exdqlm_keep_decomposition_ablation_log1p_q05_q35_q50_q95_v3_20260521_latent_cap_e_inv_u/`;
- all four lanes wrote `.RData` and the wrapper completed post/validate/report;
- no pseudo-data guard rows were written;
- terminal state norm squared was `1521.127` for q05, `2233.589` for q35, `2547.352` for q50, and `5082.421`
  for q95;
- saved-output historical pseudo-data were finite and small relative to current caps; q05 target `E[1/u]` max was
  `764.468` and q95 target `E[1/u]` max was `110.045`.

This is enough evidence to test a capped candidate explicitly. It is not enough evidence to make silent latent
clipping the default, because the cap changes pseudo-observation precision and therefore the fitted state update.

Promotion v1:

- evidence root:
  `reports/exdqlm_keep_guarded_repro_promotion_log1p_q05_q35_q50_q95_v1_20260521_latent_cap_e_inv_u/`;
- guard profile used fail-fast pseudo-data guards plus state guard active from the beginning;
- no pseudo-data guard rows were written;
- q05 and q95 failed at iter `3000` after repeated state-guard/refreeze events, with terminal state norm squared
  around `1.50e6` and `1.56e6`;
- interpretation: this was a guard-policy failure, not evidence that latent capping cannot stabilize the lane.

Promotion v2:

- evidence roots:
  `reports/exdqlm_keep_guarded_repro_promotion_log1p_q05_q35_q50_q95_v2_20260521_latent_cap_e_inv_u/`,
  `reports/exdqlm_keep_runtime_stability_promotion_log1p_q05_q35_q50_q95_v2_20260521_latent_cap_e_inv_u/`,
  `reports/exdqlm_keep_curated_evidence_promotion_log1p_q05_q35_q50_q95_v2_20260521_latent_cap_e_inv_u/`,
  `reports/exdqlm_keep_decomposition_promotion_log1p_q05_q35_q50_q95_v2_20260521_latent_cap_e_inv_u/`;
- state guard delayed to iter `1000`;
- all q05/q35/q50/q95 lanes wrote `.RData`, and fit/post/validate/report completed;
- no pseudo-data guard rows were written;
- terminal state norm squared was q05 `1521.127`, q35 `2233.589`, q50 `2547.352`, q95 `5082.421`.

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
- enable state-norm guard/refreeze controls and terminal sampling guard for all q05/q35/q50/q95 promotion lanes;
- delay state-norm guard activation until iter `1000` for this reduced-spec `log1p_cms` profile unless a new
  warmup-specific diagnostic shows an earlier threshold is safe;
- treat any q05-like `E[1/u]` cap breach as a failed promotion run until the latent-cap ablation proves that
  capping is scientifically harmless.
- use `repro/audits/prepare_exdqlm_keep_guarded_repro.py --guard-profile promotion` for isolated candidates. That
  profile exports fail-fast pseudo-data guards, `DISC_GAMSIG_STATE_GUARD_ENABLED=1`, state norm cap/ratio controls,
  delayed guard start, refreeze/hold windows, and `DISC_GAMSIG_TERMINAL_SAMPLING_GUARD_MODE=fail_fast`.

## What Not To Do Yet

Do not promote latent `E[1/u]` capping as an unlabeled default production fix. It is now a runtime-clean explicit
candidate, but capping changes the pseudo-observation precision directly. Any production relaunch using it should be
named as the capped/guarded promotion-v2 profile and retain the fail-fast monitoring.

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

1. Review the promotion-v2 evidence bundle and decide whether to relaunch production with that named profile.
2. Add a damped/refrozen `sigma/gamma` candidate before broadening beyond q05/q35/q50/q95, because q05/q95 terminal
   gamma values remain asymmetric even though the state and pseudo-data paths are stable.
3. Keep runtime stability, guard CSV, and decomposition bundles mandatory for any production-scale relaunch.
