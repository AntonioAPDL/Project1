# exDQLM Multivariate Keep State-Space Contract Audit

Date: 2026-05-20

## Scope

This document derives the active multivariate `exdqlm keep` state-space
contract from the canonical theory and maps it to the current implementation.
It covers the historical observation/state equations, retrospective discrepancy
equations, transfer-retained forecast equations, stacked state definitions,
block dimensions, and measurement loading semantics.

Supporting tables:

- [exdqlm_multivar_keep_dimension_contract.csv](/data/muscat_data/jaguir26/project1_ucsc_phd/docs/exdqlm_multivar_keep_dimension_contract.csv)
- [exdqlm_multivar_keep_symbol_map.csv](/data/muscat_data/jaguir26/project1_ucsc_phd/docs/exdqlm_multivar_keep_symbol_map.csv)

## Source Lock

The canonical theory is `main.tex`. The active executed implementation is the
inline setup in
[DISC_Optimal_Synth_Ranges_W_transfer_forecast.r](/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_Optimal_Synth_Ranges_W_transfer_forecast.r),
with the C++ state update in
[DISC_kalman_synth_transfer_forecast.cpp](/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_kalman_synth_transfer_forecast.cpp).

The reusable `R/environmetrics/20_model_setup.R` file is a close keep/drop
analogue, but it is not sourced by the active transfer runner. The active runner
builds a transfer-retained forecast state whenever `ppx > 0` at
`DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:1568-1618`.

## Historical Model A Contract

Theory:

\[
y_t^o \mid \theta_t,\zeta_t,\sigma^o,\gamma^o
\sim \operatorname{exAL}_{p_0}(F_t^\top\theta_t+\zeta_t,\sigma^o,\gamma^o)
\]

\[
\theta_t \mid \theta_{t-1}\sim N(G_t\theta_{t-1},W_t^\theta),
\quad
\zeta_t \mid \zeta_{t-1},\psi_t
\sim N(\lambda\zeta_{t-1}+x_t^\top\psi_t,w_t^\zeta),
\quad
\psi_t \mid \psi_{t-1}\sim N(\psi_{t-1},W_t^\psi).
\]

Canonical anchors: `main.tex:63-70`.

Stacked theory state:

\[
\alpha_t =
\begin{bmatrix}
\theta_t\\ \zeta_t\\ \psi_t
\end{bmatrix},
\qquad
\tilde F_t =
\begin{bmatrix}
F_t\\ 1\\ 0
\end{bmatrix},
\qquad
G_t^{trans} =
\begin{bmatrix}
\lambda & x_t^\top\\
0 & I
\end{bmatrix}.
\]

Canonical anchors: `main.tex:73-99`.

Implementation:

- The runner builds the baseline structure and dimension `p` at
  `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:1342-1365`.
- It forms baseline plus discrepancy block-diagonal `GG`/`FF` at
  `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:1458-1467`.
- If covariates are enabled, it appends `ppx = px + 1` transfer coordinates at
  `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:1473-1506`.
- The historical transfer loading is `[1, 0, ..., 0]` for every historical
  measurement column because `Fx <- rbind(rep(1, J + 1), matrix(0, nrow = px,
  ncol = J + 1))` is assigned into `FFx` at
  `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:1484-1485`.
- The historical transfer transition block is `bdiag(lambda, diag(px))`, with
  future/current covariates inserted into the first transfer row at
  `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:1487-1490`.

Conclusion: the historical transfer block matches the Model A stacked form:
`zeta_t` loads directly in measurement, while `psi_t` drives `zeta_t` through
the transition.

## Retrospective Model B Contract

Theory:

\[
z_t^j \mid \alpha_t,\delta_t^j,\sigma^j,\gamma^j
\sim
\operatorname{exAL}_{p_0}(\tilde F_t^\top\alpha_t + F_t^\top\delta_t^j,\sigma^j,\gamma^j),
\]

\[
\delta_t^j \mid \delta_{t-1}^j
\sim N(G_t\delta_{t-1}^j,W_t^{\delta^j}).
\]

Canonical anchors: `main.tex:103-112`.

Implementation:

- The runner initializes `m0 <- c(model$m0, rep(0, p*J))` and appends
  discrepancy covariance at
  `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:1388-1389`.
- It repeats the baseline `G` and `F` blocks with
  `exdqlm_multivar_create_block_diag` at
  `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:1455-1467`.
- The first `p` rows of `result_FF` are overwritten with the baseline
  measurement `model$FF` replicated across `J+1` columns at
  `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:1463-1466`.

Measurement interpretation:

- Column 1 of historical `FF` loads the target row.
- Columns 2 through `J+1` load retrospective source rows.
- Each retrospective source column includes the shared baseline block plus that
  source's discrepancy block, and, when covariates are enabled, the shared
  transfer `zeta_t` coordinate.

The shape is validated before the C++ call:
`FF` must be `[p*(J+1)+ppx] x [J+1] x TT_sub`, and `y` must be
`[J+1] x TT_sub` at
`DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:2941-2949`.

## Forecast Keep Contract

Theory Model C-T keeps the transfer block during forecast:

\[
\beta_t^{(s)} =
\begin{bmatrix}
\theta_t\\
\delta_t^{1:a_s}\\
\tau_t
\end{bmatrix},
\qquad
\tau_t =
\begin{bmatrix}
\zeta_t\\
\psi_t
\end{bmatrix},
\qquad
\dim(\beta_t^{(s)})=q(1+a_s)+r.
\]

Canonical anchors: `main.tex:161-186`.

For active source `j` and member `i`,

\[
y_T^{j,i}(k)\mid \beta_{T+k}^{(s)},\sigma^j,\gamma^j
\sim
\operatorname{exAL}_{p_0}((h_{T+k,j}^{(s)})^\top\beta_{T+k}^{(s)},\sigma^j,\gamma^j).
\]

The theory says the loading includes baseline, discrepancy, and transfer
contribution (`main.tex:189-196`). The transfer transition is
`G_t^{trans}` with future covariates in the first row (`main.tex:198-217`).
Boundary maps preserve transfer coordinates while dropping only inactive
discrepancy blocks (`main.tex:219-239`).

Implementation:

- `ranges_per_local`, `r_vec_local`, and `seg_start_local` define ragged
  horizon segments at
  `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:1571-1573`.
- For R list segment `seg`, the active source count is
  `a_seg = J - seg + 1`; the core baseline/discrepancy dimension is
  `p*(a_seg+1)` at
  `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:1575-1579`.
- If `ppx > 0`, `state_dim = core_dim + ppx`, and `GG_list[[seg]]` is a
  time-varying array whose transfer block is `bdiag(lambda, diag(px))` with
  `X_f` inserted into the `zeta` row at
  `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:1581-1610`.
- The forecast loading appends
  `[1, 0, ..., 0]^\top` for each active source at
  `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:1612-1613`.

Thus the active implementation realizes transfer-retained loading as direct
measurement loading of `zeta_t` plus transition-mediated effects from `psi_t`.
It does not directly measurement-load the `psi_t` coordinates.

## R-to-C++ Shape Contract

The R validator defines the expected shapes at
`DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:2908-2990`.

For history:

- `total_state = p*(J+1)+ppx`
- `GG`: `total_state x total_state x TT_sub`
- `FF`: `total_state x (J+1) x TT_sub`
- `y`: `(J+1) x TT_sub`
- `FFF`: `(J+1) x TT_sub`
- `QQQ`: `(J+1) x (J+1) x TT_sub`

For forecast segment `seg`:

- `expected_state = p*(J - seg + 2) + ppx`
- `expected_series = J - seg + 1`
- `expected_h = rev(ranges - c(ranges[2:J], 0))[seg]`
- `expected_obs = sum(num_mem[1:expected_series])`
- `GG_list[[seg]]`: `expected_state x expected_state x expected_h`
- `FF_list[[seg]]`: `expected_state x expected_series`
- `FFF_forecast[[seg]]`: `expected_obs x expected_h`
- `QQQ_forecast[[seg]]`: `expected_obs x expected_obs x expected_h`
- `cur.covs_list[[seg]]`: `expected_state x expected_state x expected_h`

The compiled entrypoint repeats these checks and allocates forecast state arrays
with `+ ppx` at `DISC_kalman_synth_transfer_forecast.cpp:1031-1135`.

## Measurement Loading Semantics in C++

The compiled historical filter uses:

\[
f_t = FF_t^\top a_t + FFF_t,
\qquad
q_t = FF_t^\top R_t FF_t + QQQ_t.
\]

Code anchors:

- historical: `DISC_kalman_synth_transfer_forecast.cpp:1155-1200`
- forecast: `DISC_kalman_synth_transfer_forecast.cpp:1212-1350`

So `FFF`/`FFF_forecast` are not state loadings. They are additive
pseudo-observation offsets. Since the innovation is `y - f`, passing offset
`d_n` is equivalent to using pseudo-observation `y_n - d_n` with variance
`QQQ_n`.

## Confirmed Correct at Contract Level

1. The active runner uses the transfer-specialized compiled core, not the older
   non-transfer C++ file (`DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:45-47`).
2. The active historical state includes baseline, discrepancy, and transfer
   coordinates when covariates are enabled (`DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:1458-1506`).
3. The active forecast state retains transfer coordinates whenever `ppx > 0`
   (`DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:1568-1618`).
4. Direct measurement loading of transfer is only through `zeta_t`; `psi_t`
   affects observations through the transition (`DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:1484-1490`,
   `1612-1613`).
5. The R validator and C++ entrypoint agree on `+ppx` forecast state dimensions
   (`DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:2961-2984`,
   `DISC_kalman_synth_transfer_forecast.cpp:1085-1135`).

## Open Risks Carried Forward

1. State-space algebra being dimensionally coherent does not prove numerical
   stability. The latent and pseudo-data audit must determine whether `FFF` and
   `QQQ` can become extreme enough to destabilize an otherwise valid Kalman
   layer.
2. The active keep runner is specialized and inline. Any future edits to
   `20_model_setup.R` do not automatically repair this runner unless they are
   ported or the runner is refactored to source the shared setup.
3. Trend, discrepancy, and retained transfer are all persistent blocks. The
   contract permits them to compete for the same low-frequency signal; runtime
   identifiability evidence is required before clearing H4.
