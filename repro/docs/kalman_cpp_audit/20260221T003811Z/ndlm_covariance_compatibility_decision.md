# NDLM Forecast Covariance Compatibility Decision

Date: 2026-02-21

## Question
Should NDLM synth-path covariance in `DISC_kalman_synth_NDLM.cpp` remain fixed `D/D_ens` or support expected time-varying `V_t` from Wishart/IW VB updates?

## Observed implementation state
1. `DISC_kalman_synth_NDLM.cpp` currently uses fixed `D` and fixed-per-segment `D_ens` for `q` in forecast blocks.
2. `kalman_NDLM.cpp:update_theta_cpp_ndlm_exactV(...)` already implements expected covariance updates via `nu0,S0 -> nu_t,S_t -> V_obs`.

## Decision
Adopt dual-mode NDLM covariance handling in synth C++ path:
1. Preserve current fixed `D/D_ens` path as backward-compatible default.
2. Add optional time-varying expected covariance inputs (`D_t`, `D_ens_t`) and enforce shape contracts.
3. If optional inputs are present, use them deterministically in place of fixed covariance at corresponding time/slice.

## Rationale
1. Keeps legacy behavior stable.
2. Enables theory-compatible expected-covariance mode without forcing old scripts to change immediately.
3. Eliminates ambiguity: covariance source is explicit and fail-fast validated.

## Required code implications
1. Add optional covariance arguments to NDLM synth C++ entrypoint.
2. Add helper selectors for historical and segment-level covariance extraction with dimension/slice checks.
3. Add explicit contract errors for malformed covariance inputs.
