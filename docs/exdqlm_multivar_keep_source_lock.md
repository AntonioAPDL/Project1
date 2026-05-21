# exDQLM Multivariate Keep Source Lock

Date: 2026-05-20

## Purpose

This file freezes the source set for the active multivariate `exdqlm keep`
implementation audit. It is a source lock, not a verdict: later audit files
must cite both the canonical theory source and the active implementation path
before treating a claim as confirmed.

## Primary Theory

The canonical mathematical source is
`/data/muscat_data/jaguir26/exDQLM---Ensemble/main.tex`.

Primary theory anchors used by this audit:

| Component | Theory lines | Meaning |
|---|---:|---|
| Model A observation/transfer | `main.tex:63-70` | historical target observation, baseline state, transfer state |
| Model A stacked form | `main.tex:73-99` | `alpha_t = (theta_t, zeta_t, psi_t)` and transfer transition |
| Model B discrepancy | `main.tex:103-112` | retrospective source discrepancy state |
| Model C drop forecast | `main.tex:114-145` | forecast without transfer state |
| Model C-T keep forecast | `main.tex:161-239` | forecast state retaining transfer coordinates |
| exAL augmentation | `main.tex:241-253` | Gaussian augmentation with `v_t` and `s_t` |
| `v_t` conditional | `main.tex:323-342` | GIG conditional and parameterization |
| `s_t` conditional | `main.tex:344-360` | positive-truncated normal conditional |
| pseudo-data | `main.tex:707-729`, `main.tex:947-967` | information-form pseudo-data for Gaussian state update |
| joint sigma/gamma kernel | `main.tex:735-765` | variational factor for `(sigma, gamma)` |

The project-local `article.txt` is useful corroborating manuscript text, but
`main.tex` remains stronger when the two differ.

## Active Implementation Path

The active runner for this audit is:

- [DISC_Optimal_Synth_Ranges_W_transfer_forecast.r](/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_Optimal_Synth_Ranges_W_transfer_forecast.r)

Current active implementation anchors:

| Component | Implementation lines | Meaning |
|---|---:|---|
| helper and structure sources | `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:22-24` | sources `R/disc_w/_init.R`, state blending, multivar structure helper |
| compiled code | `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:45-47` | compiles `sampling_exal.cpp`, `sampling_truncnorm.cpp`, and `DISC_kalman_synth_transfer_forecast.cpp` |
| ensemble construction | `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:1314-1319` | builds `ensembles`, `J`, `num_mem`, `ranges`, `mean_forecast` |
| structure construction | `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:1342-1365` | builds baseline structure and state dimension `p` |
| historical stacked state | `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:1458-1506` | builds baseline/discrepancy plus historical transfer block |
| forecast keep state | `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:1565-1618` | builds transfer-retained forecast `GG_list` and `FF_list` |
| shape contract | `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:2908-2990` | validates R-to-C++ shapes for history and forecast |
| `s_t` update | `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:1795-1815` | active positive-truncated normal moment update |
| `u_t` update | `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:1833-1879` | active GIG moment update |
| pseudo-data | `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:3343-3374`, `3539-3587` | seed and live `FFF`/`QQQ` construction |
| Kalman call | `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:3401-3412`, `3670-3679` | seed and live C++ state update calls |
| saved state surface | `R/disc_w/05_save_state.R:31-119` | saved latent, state, sigma/gamma, and pseudo-data objects |

The compiled active state update is:

- [DISC_kalman_synth_transfer_forecast.cpp](/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_kalman_synth_transfer_forecast.cpp)

Key compiled anchors:

| Component | C++ lines | Meaning |
|---|---:|---|
| exported entrypoint | `DISC_kalman_synth_transfer_forecast.cpp:1031-1043` | `DISC_update_theta_synth_cpp_W(...)` signature |
| historical shape checks | `DISC_kalman_synth_transfer_forecast.cpp:1066-1084` | state, observation, and member dimensions |
| transfer forecast dimensions | `DISC_kalman_synth_transfer_forecast.cpp:1085-1135` | forecast state/member allocation includes `ppx` |
| historical filter pseudo-data use | `DISC_kalman_synth_transfer_forecast.cpp:1155-1200` | `f = FF'a + ex_f`, `q = FF'RFF + ex_q` |
| forecast filter pseudo-data use | `DISC_kalman_synth_transfer_forecast.cpp:1212-1350` | expanded member loading plus `ex_f_list_ens`/`ex_q_list_ens` |
| returned state objects | `DISC_kalman_synth_transfer_forecast.cpp:1894-1906` | filtered, smoothed, forecast, and covariance outputs |

## Keep/Drop Scope Clarification

`R/environmetrics/20_model_setup.R` remains a useful implementation analogue:
it contains an explicit keep/drop switch at
`R/environmetrics/20_model_setup.R:208-214`, keeps transfer at
`R/environmetrics/20_model_setup.R:226-270`, and drops transfer at
`R/environmetrics/20_model_setup.R:271-273`.

However, the active transfer runner audited here does not source
`R/environmetrics/20_model_setup.R`; it constructs the model inline. In the
active runner, forecast transfer is retained whenever `ppx > 0` by the block at
`DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:1568-1618`. Therefore this
audit treats `20_model_setup.R` as a corroborating reusable setup path, not as
the direct executed code for the active keep runner.

## Non-Authoritative / Historical Inputs

The older static inventory [audit_used_code.md](/data/muscat_data/jaguir26/project1_ucsc_phd/audit_used_code.md)
is useful for audit style, but it targets `DISC_Optimal_Synth_Ranges_W.r`.
For the current keep audit, any claim from that file must be rechecked against
`DISC_Optimal_Synth_Ranges_W_transfer_forecast.r` and
`DISC_kalman_synth_transfer_forecast.cpp`.

## Runtime Scope Guard

This audit may inspect existing logs and saved outputs from current or prior
runs, but it must not stop, relaunch, or modify the named live production
campaigns. Large runtime evidence belongs under `reports/` and is not committed
by default.
