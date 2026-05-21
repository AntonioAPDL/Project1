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

## Found Wrong And Patched

1. Forecast-member `update_uts` used bare `T` for forecast column indexing at audit time.

   This was wrong because `update_sts` used `(TT_sub+1):(TT_sub+k_forecast)`, while `update_uts` used
   `(T+1):(T+k_forecast)`. In R, bare `T` is unsafe and can mean `TRUE` unless assigned in scope. The active
   file is now patched so the fit-stage forecast `update_uts` uses `TT_sub` at
   `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:4001-4002`, and the sampling-stage forecast `update_uts`
   uses `TT_sub` at `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:4694-4695`.

   Regression coverage: `tests/testthat/test_exdqlm_multivar_keep_latent_pseudodata_audit.R` asserts there are
   no remaining `new.theta.out$exps[j,(T+1):(T+k_forecast)]` or `exps2` forecast-member references.

2. Active `s_t` entropy was not the canonical positive-truncated normal entropy.

   This was patched in commit `4bbb643`. The active runner now computes positive-truncated-normal moments and
   natural-log entropy in `disc_w_pos_truncnorm_moments` at
   `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:1821-1839`, and `update_sts` uses those moments at
   `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:1853-1860`. Regression coverage is in
   `tests/testthat/test_exdqlm_multivar_keep_latent_pseudodata_audit.R`.

3. The post-save objective diagnostic can dominate runtime after outputs are already saved.

   The active runner historically computed a 3D KDE/JSD diagnostic after writing `.RData`. In the guarded smoke
   run, q05 had already saved its output and generated audit evidence, then continued spending CPU in this
   post-save block. Commit `5a83162` keeps default behavior unchanged but adds
   `DISC_W_POST_SAVE_OBJECTIVE_ENABLED` at `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:649-663` and the early
   return at `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:5189-5196`. The isolated guarded repro launcher now
   exports this switch off by default for targeted audit runs.

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

## Implementation Status 2026-05-21

The first repair sequence is now implemented in local commits:

- `eb22e6e`: forecast `update_uts` indexing fix.
- `be5cf55`: log1p transform forensics and scale-contract tests.
- `4bbb643`: stable latent moments and pseudo-data guards.
- `5a83162`: guarded reproduction launcher, runtime audit normalization for summed `E[log u]`, and post-save
  objective control.

Smoke evidence is under
`reports/exdqlm_keep_guarded_repro_smoke_guarded_log1p_phase_cd_20260521/`. q05 and q50 wrote `.RData` outputs,
the runtime stability report was generated, and no pseudo-data guard event CSV was written under the smoke guard
report directory. The q05 smoke wrapper was terminated only after output save because it was in the old post-save
JSD diagnostic; the full guarded run uses the new objective-disable switch.

A full isolated guarded q05/q35/q50/q95 reproduction is currently running under:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/exdqlm_keep_guarded_log1p_q05_q35_q50_q95_20260521/`

and writes audit artifacts under:

`reports/exdqlm_keep_guarded_repro_guarded_log1p_q05_q35_q50_q95_20260521/`

Initial live monitor snapshot at `2026-05-21T01:20:39-0700`: q35/q50 remained near state-norm squared
`2.1e3`/`2.4e3`, q05/q95 had decreased from early `~0.8e6-1.1e6` plateaus to about `3.5e5`/`4.1e5`, and no
pseudo-data guard events had been written. This is not a final root-cause verdict; it is the first live evidence
that the hardened path is no longer immediately reproducing the previous `1e10` state-norm failure.

## Prioritized Fix List

The implementation and testing roadmap for these fixes is now tracked in
`docs/exdqlm_multivar_keep_repair_and_transform_regression_plan.md`. That plan also adds the transform-regression
hypothesis: the workflow reportedly behaved better before commit `44e2d60` changed the internal analysis contract
from `log_log1p_cms` to `log1p_cms`, so the next repair cycle must explicitly test scale sensitivity rather than
assuming the current instability is unrelated to the transform rewrite.

P0. Validate the forecast `update_uts` indexing fix with narrow q05/q35/q50/q95 reproductions. Do not launch broad
production. Save iteration snapshots for forecast `E[u]`, `E[1/u]`, `FFF_forecast`, `QQQ_forecast`, and state norm.

P0. Add a pre-Kalman pseudo-data guard for nonfinite or extreme `FFF` and `QQQ_diag`, with clear logs and optional
fail-fast behavior before the state update consumes them.

P1. Continue the guarded q05/q35/q50/q95 reproduction to completion, then regenerate the runtime stability report
from the resulting `.RData` outputs and compare against the pre-repair `1e10` q50 failure.

P1. Confirm whether the patched `s_t` entropy and `u_t` numerical changes alter ELBO convergence behavior across
the full refresh schedule, not only in short smoke runs.

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
