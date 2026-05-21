# exDQLM Multivariate Keep Final Findings

Date: 2026-05-20

## Executive Finding

The current instability is interactional, not a single-layer failure.

The state-space contract, ensemble/member contract, latent conditional formulas, pseudo-data algebra, and a
historical Kalman fixture are mostly coherent against the canonical theory and active implementation. However,
the VB loop can drive latent moments and pseudo-data into destructive regimes, and one concrete forecast-member
indexing bug was found and patched during this audit.

The strongest runtime signature is:

1. `sigma/gamma` and latent moment updates produce extreme `E[1/u_t]`, `E[s_t]`, and `E[s_t^2]` in bad lanes.
2. Those moments directly generate large `FFF` offsets and `QQQ` variances.
3. The Kalman layer consumes those pseudo-data inputs according to its contract and propagates them into large
   state norms.
4. Retained transfer, trend, and discrepancy blocks remain weakly identified under those extreme inputs.

The tracked mismatch matrix is:

`docs/exdqlm_multivar_keep_final_mismatch_matrix.csv`

## Confirmed Correct

- Active path: `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r` is the runner. It sources DISC helpers and the
  structure helper at lines `22-24`, compiles `DISC_kalman_synth_transfer_forecast.cpp` at line `47`, builds
  ensembles at lines `1314-1319`, and constructs the transfer-retained forecast state at lines `1565-1618`.
- Keep state contract: canonical Model C-T keeps the transfer block (`main.tex:161-239`), and the active R/C++
  dimensions preserve `ppx` in historical and forecast states (`DISC_kalman_synth_transfer_forecast.cpp:1066-1130`).
- Ensemble/member contract: source arrays are lead/time by member in `R/disc_w/06_ensemble_spec.R:55-81,107-130`;
  bookkeeping preserves `num_mem`, `ranges`, and `mean_forecast` in `R/disc_w/04_ensemble_bookkeeping.R:24-37`.
- `s_t` moments: `update_sts` implements the positive-truncated normal parameters from `main.tex:344-360` and
  passes deterministic moment tests.
- `u_t` moments: `update_uts` implements the GIG family from `main.tex:323-342` and passes deterministic moment
  tests against Bessel identities and numerical integration.
- Pseudo-data algebra: active `FFF`/`QQQ` construction at `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:3539-3587`
  matches the information-form pseudo-data derivation at `main.tex:947-967`.
- Historical Kalman filter fixture: `reports/exdqlm_multivar_keep_kalman_fixture_20260520/kalman_fixture_checks.csv`
  shows filtered mean/covariance max absolute differences of `6.26e-11` and `7.37e-11` against an R reference.

## Found Wrong

1. Forecast-member `update_uts` used bare `T` for forecast column indexing at audit time.

   This was wrong because `update_sts` used `(TT_sub+1):(TT_sub+k_forecast)`, while `update_uts` used
   `(T+1):(T+k_forecast)`. In R, bare `T` is unsafe and can mean `TRUE` unless assigned in scope. The active
   file is now patched so the fit-stage forecast `update_uts` uses `TT_sub` at
   `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:4001-4002`, and the sampling-stage forecast `update_uts`
   uses `TT_sub` at `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:4694-4695`.

   Regression coverage: `tests/testthat/test_exdqlm_multivar_keep_latent_pseudodata_audit.R` asserts there are
   no remaining `new.theta.out$exps[j,(T+1):(T+k_forecast)]` or `exps2` forecast-member references.

2. Active `s_t` entropy is not the canonical positive-truncated normal entropy.

   The moment formulas are correct, but `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:1812-1814` uses
   `0.5*log2(2*pi*exp(1)*s.sig2) - 1`, which is not the canonical truncated-normal entropy and uses base-2 logs.
   This is probably an ELBO/convergence accounting defect rather than the direct source of state explosion.

## Questionable

- `sigma/gamma` approximation stability remains a high-risk block. The q50 runtime lane has terminal
  `sigma_exp_vec=[0.000592705,0.1307873,0.0170561]` and
  `gamma_exp_vec=[1.084075,1.083863,1.071936]` in `q50/logs/fit.log:15472`, while the state norm is already
  `1.125e10`.
- Wishart/covariance approximation remains only partially checked. C++ inverse-Wishart precision/logdet helpers
  are at `DISC_kalman_synth_transfer_forecast.cpp:52-80`; forecast covariance enters filtering at
  `DISC_kalman_synth_transfer_forecast.cpp:1220-1244`.
- Full ragged forecast smoothing with `J>1` and `ppx>0` is not yet reference-checked. The fixture checks a
  small forecast case for symmetry, not the complete ragged transfer-retained smoother.
- Trend/transfer/discrepancy identifiability remains plausible as an amplifier. The state contract is coherent,
  but the runtime evidence shows very large pseudo-data forcing terms in lanes where multiple retained blocks can
  absorb similar signal.

## Runtime Evidence

The runtime audit report is untracked by design:

`reports/exdqlm_multivar_keep_runtime_stability_2017_ready_q05_q35_q50_q95_20260520/`

Key terminal evidence from `runtime_key_findings.csv` and `state_norm_totals.csv`:

| lane | target max E[s] | target max E[s^2] | target max E[1/u] | FFF range | QQQ diag max | total state norm sq |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| q05 | 0.666 | 0.636 | 158.8 | [15.01, 20.54] | 0.145 | 5.403e5 |
| q35 | 42.35 | 1793.10 | 2098.77 | [-166.25, 232.88] | 3187.14 | 1.137e8 |
| q50 | 6.13 | 37.54 | 7057.22 | [-3245.82, 67.07] | 859.39 | 1.125e10 |
| q95 | 23.60 | 556.75 | 9480.96 | [-789.36, 99.51] | 1435.99 | 1.447e8 |

The q50 log records a terminal guard condition:

- `q50/logs/fit.log:15423`: `state_norm_sq=11252388000` exceeds `abs_cap=100000000`.
- `q50/logs/fit.log:15476`: terminal preflight reports `mode=fail_fast`, `guard_count=179`.

## Prioritized Fix List

P0. Validate the forecast `update_uts` indexing fix with narrow q05/q35/q50/q95 reproductions. Do not launch broad
production. Save iteration snapshots for forecast `E[u]`, `E[1/u]`, `FFF_forecast`, `QQQ_forecast`, and state norm.

P0. Add a pre-Kalman pseudo-data guard for nonfinite or extreme `FFF` and `QQQ_diag`, with clear logs and optional
fail-fast behavior before the state update consumes them.

P1. Replace `s_t` entropy with the canonical natural-log positive-truncated normal entropy, then confirm whether
ELBO convergence behavior changes.

P1. Add eigenvalue/SPD diagnostics for `W_list_ens`, `QQQ`, `QQQ_forecast`, and Kalman `q` matrices in suspect
lanes.

P1. Add component decomposition traces for trend, transfer, and discrepancy blocks using the active state index
map. This is necessary to separate numerical explosion from identifiability.

P2. Extend the Kalman fixture to `J=2`, `ppx>0`, and a true ragged forecast segment transition.

P2. Revisit the inverse-Wishart precision/logdet approximation after the above fixes; it is suspicious but not yet
the first proven failure.

## Verification Completed

- `Rscript --vanilla -e "testthat::test_file('tests/testthat/test_exdqlm_multivar_keep_latent_pseudodata_audit.R')"`
  passed with 27 expectations.
- `Rscript --vanilla repro/audits/run_exdqlm_keep_kalman_fixture.R reports/exdqlm_multivar_keep_kalman_fixture_20260520`
  passed.
- `Rscript --vanilla repro/audits/exdqlm_keep_runtime_stability_audit.R --out reports/exdqlm_multivar_keep_runtime_stability_2017_ready_q05_q35_q50_q95_20260520 ...`
  regenerated the q05/q35/q50/q95 read-only runtime report.
