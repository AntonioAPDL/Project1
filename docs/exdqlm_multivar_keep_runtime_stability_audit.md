# exDQLM Multivariate Keep Runtime Stability Audit

Date: 2026-05-20

## Scope

This document records read-only runtime evidence for the active multivariate `exdqlm keep`
workflow. It uses saved `.RData` outputs and fit logs from the isolated 2017 ready run:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_20221225_reducedspec_defaultvb_iter3000_dfall999999_datastart2017_ready_20260520/runs/multimodel_20221225_v8_he2pubgdpc1r1_defaultvb_schedhold20refresh1_iter3000_dfall999999_datastart2017_ready_exdqlm_multivar_keep_rerun_20260520_160916`

No production process was stopped, relaunched, or modified. The runtime extractor is tracked at
`repro/audits/exdqlm_keep_runtime_stability_audit.R`; its outputs are intentionally untracked under:

`reports/exdqlm_multivar_keep_runtime_stability_2017_ready_q05_q35_q50_q95_20260520/`

Important interpretation note: these saved runtime outputs were produced before the local audit patch that
replaced bare `T` forecast indexing with `TT_sub` in forecast-member `update_uts`. They remain valid evidence for
the observed production instability, but post-fix reproductions are required before claiming the same magnitudes
will occur in future runs.

## Theory And Code Anchors

The latent-variable and pseudo-data contract comes from the canonical exDQLM theory:

- `main.tex:323-342` gives the GIG conditional for `v_t`/`u_t`.
- `main.tex:344-360` gives the positive-truncated normal conditional for `s_t`.
- `main.tex:947-967` gives the pseudo-data rule `bar y=b/w`, `bar R=1/w`.

The active implementation path is:

- `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:1795-1815` for `update_sts`.
- `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:1833-1879` for `update_uts`.
- `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:3539-3587` for live historical and forecast `FFF`/`QQQ`.
- `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:3670-3679` for the call into the compiled Kalman path.
- `DISC_kalman_synth_transfer_forecast.cpp:1157-1196` and `DISC_kalman_synth_transfer_forecast.cpp:1265-1348` for historical and forecast filtering.

## Evidence Files

The report directory contains:

- `manifest.csv`: exact `.RData` paths loaded.
- `object_summaries.csv`: finite/positive fractions and quantiles for latent, `sigma/gamma`, and pseudo-data objects.
- `runtime_key_findings.csv`: compact high-signal subset used below.
- `state_norms.csv`: per-time state norm squared.
- `state_norm_totals.csv`: total state norm squared across each saved state matrix, matching the `state_norm_sq` scale printed in fit logs.
- `q*_E.sts_history.png`, `q*_E.sts2_history.png`, `q*_E.uts_history.png`, `q*_E.inv.uts_history.png`, `q*_FFF_history.png`, and `q*_QQQ_diag_history.png`.

The extractor summarizes `QQQ_diag` separately because active `QQQ` is stored as a diagonal covariance cube
(`DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:3540-3545`), so off-diagonal zeros are structural rather than
zero variances.

## Runtime Findings

The healthy control lane, `q05`, has bounded target latent moments and pseudo-data:

| lane | target max E[s] | target max E[s^2] | target max E[1/u] | FFF range | QQQ diag max | total state norm sq |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| q05 | 0.666 | 0.636 | 158.8 | [15.01, 20.54] | 0.145 | 5.403e5 |

Pathological lanes have large latent and pseudo-data excursions before the Kalman layer can be isolated as the
sole cause:

| lane | target max E[s] | target max E[s^2] | target max E[1/u] | FFF range | QQQ diag max | total state norm sq |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| q35 | 42.35 | 1793.10 | 2098.77 | [-166.25, 232.88] | 3187.14 | 1.137e8 |
| q50 | 6.13 | 37.54 | 7057.22 | [-3245.82, 67.07] | 859.39 | 1.125e10 |
| q95 | 23.60 | 556.75 | 9480.96 | [-789.36, 99.51] | 1435.99 | 1.447e8 |

These values are from `runtime_key_findings.csv` and `state_norm_totals.csv` in the report directory.

The saved total state norms agree with the fit-log `state_norm_sq` scale:

- `q05`: fit log line `9167` reports `state_norm_sq=540329.9`; report total is `5.403299e5`.
- `q35`: fit log line `9167` reports `state_norm_sq=113678700`; report total is `1.136787e8`.
- `q50`: fit log line `15472` reports `state_norm_sq=11253274000`; report total is `1.125327e10`.
- `q95`: fit log line `9167` reports `state_norm_sq=144683240`; report total is `1.446832e8`.

The per-time maxima in `state_norm_totals.csv` are a different diagnostic: `247.3` for `q05`, `200773.5` for
`q35`, `5160824.1` for `q50`, and `224541.3` for `q95`.

## Log Evidence

The `q50` lane records repeated state guards near the end of VB:

- `q50/logs/fit.log:15423`: `gamsig_state_guard` at iteration 2992 because `state_norm_sq=11252388000`
  exceeds `abs_cap=100000000`.
- `q50/logs/fit.log:15472`: iteration 3000 still has `state_norm_sq=11253274000`, `sigma_exp_vec`
  `[0.000592705,0.1307873,0.0170561]`, and `gamma_exp_vec` `[1.084075,1.083863,1.071936]`.
- `q50/logs/fit.log:15476`: terminal guard reports `mode=fail_fast`, `guard_count=179`, and the same
  abs-cap reason.

The q35 and q95 lanes did not use the same terminal guard mode, but their final norms are still very large:

- `q35/logs/fit.log:9167`: `state_norm_sq=113678700`, `sigma_exp=0.5790909`, `gamma_exp=-0.6135736`.
- `q95/logs/fit.log:9167`: `state_norm_sq=144683240`, `sigma_exp=0.3522215`, `gamma_exp=0.06463079`.

## Interpretation

The runtime evidence does not support "Kalman layer alone" as the primary explanation, because `FFF` and
`QQQ_diag` are already extreme in pathological lanes. The Kalman layer then consumes these objects as additive
observation offsets and variances (`DISC_kalman_synth_transfer_forecast.cpp:1157-1158`,
`DISC_kalman_synth_transfer_forecast.cpp:1187-1188`, `DISC_kalman_synth_transfer_forecast.cpp:1265-1273`).

The evidence also does not support a single isolated `s_t` or `u_t` formula bug. Focused tests verify the
moment identities for the formulas implemented in `update_sts` and `update_uts`; however, the VB loop can drive
the moments into numerically destructive regimes. The strongest signature is interactional:

1. `sigma/gamma` values and latent moments determine the information weights and offsets.
2. Small `E[u_t]` and large `E[1/u_t]` inflate pseudo-data weights.
3. `FFF` offsets can become large and sign-changing.
4. The Kalman update faithfully follows the supplied pseudo-data and propagates the instability into state norms.
5. Trend, transfer, and discrepancy blocks remain structurally able to absorb similar signal, so the large
   pseudo-data perturbations are not well identified.

## Remaining Runtime Gaps

This audit did not launch new targeted lanes. The saved q05/q35/q50/q95 outputs were sufficient to establish the
interaction signature without touching live campaigns. Remaining runtime work should be small and explicit:

1. Add a decomposed component extractor for trend, transfer, and each discrepancy block using the active state
   index map.
2. Add iteration-level saved snapshots of `FFF`, `QQQ_diag`, `E[s]`, `E[1/u]`, and `state_norm_sq`, because the
   current `.RData` objects expose the terminal state while the logs expose iteration traces.
3. Run a targeted q50 fixed-latent or fixed-`sigma/gamma` ablation only after the next code-side guard/fix is
   chosen.
