# Shared Kalman/FFBS Contract (NDLM vs multiv exDQLM)

Date: 2026-02-21

## Scope
This note defines the common state-update contract that must be identical between NDLM and multivariate exDQLM C++ paths. Only likelihood/covariance blocks may differ.

## Common contract (must match)
1. Linear-Gaussian state propagation structure for latent states within VB/CAVI state-update step.
2. Forward filtering equations for `(a_t, R_t)` and posterior update `(m_t, C_t)`.
3. Backward smoothing equations with smoothing gain `B_t` and covariance correction for `sC_t`.
4. Forecast-segment smoothing with transdimensional mapping when active forecaster set changes by lead (`k_ens` segmentation).
5. ELBO state-block terms: log-det and quadratic-form contributions from filtered/smoothed covariance transitions.

## Model-specific differences (allowed)
1. Observation likelihood:
   - multiv exDQLM: exAL-driven observation moments injected through `ex_f` and `ex_q` (and ensemble variants).
   - NDLM: Gaussian observation covariance injected through `D` (or expected `V_t` if using exactV-compatible mode).
2. Auxiliary latent updates for exAL-specific parameters (`gamma`, `sigma`, truncation moments) are exDQLM-only.

## Ragged horizon requirement
1. Both models must support lead-dependent active forecaster sets (`A_k`).
2. Transition from dimension `d_k` to `d_{k+1}` must preserve cross-covariances through rectangular smoother gain blocks.
3. No silent truncation to min-horizon in forecast segments.

## Evidence pointers
- multiv cpp: `DISC_kalman_synth.cpp`
- ndlm cpp: `DISC_kalman_synth_NDLM.cpp`
- ndlm exactV reference: `kalman_NDLM.cpp:update_theta_cpp_ndlm_exactV`
- unified ndlm active path: `R/unified/families/ndlm_main/02_model_spec.R`
