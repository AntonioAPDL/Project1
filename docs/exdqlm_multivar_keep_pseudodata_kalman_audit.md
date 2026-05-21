# exDQLM Multivariate Keep Pseudo-Data and Kalman Audit

Date: 2026-05-20

## Scope

This document audits the pseudo-data construction (`FFF`, `QQQ`,
`FFF_forecast`, `QQQ_forecast`) and the compiled Kalman/RTS state-update
contract used by the active multivariate `exdqlm keep` workflow.

Focused test evidence:

- [tests/testthat/test_exdqlm_multivar_keep_latent_pseudodata_audit.R](/data/muscat_data/jaguir26/project1_ucsc_phd/tests/testthat/test_exdqlm_multivar_keep_latent_pseudodata_audit.R)
- test command passed with 27 expectations and 0 failures.

Fixture evidence:

- script:
  [repro/audits/run_exdqlm_keep_kalman_fixture.R](/data/muscat_data/jaguir26/project1_ucsc_phd/repro/audits/run_exdqlm_keep_kalman_fixture.R)
- untracked report:
  [reports/exdqlm_multivar_keep_kalman_fixture_20260520/kalman_fixture_checks.csv](/data/muscat_data/jaguir26/project1_ucsc_phd/reports/exdqlm_multivar_keep_kalman_fixture_20260520/kalman_fixture_checks.csv)

## Theory: Information-Form Pseudo-Data

For scalar observation `n`, the manuscript defines:

\[
w_n = E_q\left[\frac{1}{R_n}\right]
=E_q\left[\frac{1}{\sigma^s B^s}\right]E_q\left[\frac{1}{v_n}\right],
\]

\[
b_n = E_q\left[\frac{\tilde y_n}{R_n}\right]
=y_nw_n
-E_q\left[\frac{C^s|\gamma^s|}{B^s}\right]E_q[s_n]E_q\left[\frac{1}{v_n}\right]
-E_q\left[\frac{A^s}{\sigma^sB^s}\right].
\]

Equivalent Gaussian pseudo-data:

\[
\bar y_n=b_n/w_n,\qquad \bar R_n=1/w_n.
\]

Canonical anchors:

- `main.tex:707-729`
- `main.tex:947-967`

## Active Offset/Covariance Representation

The C++ core does not receive `bar_y` directly. It receives the raw observation
`y` and an additive offset `ex_f`:

\[
f_n = h_n^\top a_t + ex\_f_n,
\qquad
\text{innovation}=y_n-f_n.
\]

Therefore the active `FFF` offset must satisfy:

\[
y_n-FFF_n=\bar y_n.
\]

From the theory:

\[
FFF_n
=
\frac{
E[C|\gamma|/B]E[s_n]E[1/v_n]+E[A/(\sigma B)]
}{
E[1/(\sigma B)]E[1/v_n]
}
=
\frac{
E[C|\gamma|/B]E[s_n]+E[A/(\sigma B)]/E[1/v_n]
}{
E[1/(\sigma B)]
}.
\]

The active covariance is:

\[
QQQ_n=\bar R_n=\frac{1}{E[1/(\sigma B)]E[1/v_n]}.
\]

This exactly matches the live historical construction:

- `FFF <- (...)` at
  `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:3539`
- `QQQ <- 1/(...)` at
  `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:3540`
- diagonal cube construction at
  `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:3541-3545`

The seed/materialization path uses the same formulas at
`DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:3343-3374`.

## Forecast Pseudo-Data

For each source `j`, forecast member pseudo-data use the same algebra with
forecast member latent arrays:

- `FFF_j` construction:
  `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:3552-3556`
- `QQQ_j` construction:
  `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:3558-3559`
- ragged horizon concatenation:
  `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:3564-3568`
- diagonal member covariance cubes:
  `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:3569-3587`

The same construction is used in the seed/materialization path at
`DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:3352-3374`.

The R validator checks that:

- `FFF_forecast[[seg]]` is `obs_dim x expected_h`,
- `QQQ_forecast[[seg]]` is `obs_dim x obs_dim x expected_h`,
- all values are finite.

Code anchors: `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:2975-2988`.

## Executable Pseudo-Data Test

The deterministic test in
`tests/testthat/test_exdqlm_multivar_keep_latent_pseudodata_audit.R` checks that:

\[
y - FFF = b/w,
\qquad
QQQ = 1/w,
\]

for a numeric fixture. It also checks finite offsets and positive variances.
This test passes.

Status: pseudo-data algebra is confirmed against the theory and active C++
offset convention.

## How Instability Propagates Through Pseudo-Data

Let:

\[
g_1=E[1/(\sigma B)],
\qquad
g_2=E[C|\gamma|/B],
\qquad
g_3=E[A/(\sigma B)],
\qquad
r_v=E[1/v].
\]

Then:

\[
QQQ=\frac{1}{g_1r_v},
\qquad
FFF=\frac{g_2E[s]+g_3/r_v}{g_1}.
\]

Propagation signatures:

1. If `sigma` explodes, `g_1` and `g_3` can shrink, inflating `QQQ` and making
   observations weak while also amplifying `FFF` through division by `g_1`.
2. If `gamma` approaches a support/pathological region, `A`, `B`, and `C`
   expectations can move together, changing both `FFF` and `QQQ`.
3. If `E[1/u]` becomes very large, `QQQ` collapses and the Kalman update becomes
   overconfident.
4. If `E[1/u]` becomes very small, `QQQ` inflates and the state update becomes
   weakly anchored.
5. If `E[s]` becomes large, `FFF` shifts the innovation even if `QQQ` remains
   numerically reasonable.

Thus H1 and H2 can destabilize H3 through a single iteration of pseudo-data.

## Compiled Kalman Contract

The active runner compiles:

```r
Rcpp::sourceCpp("DISC_kalman_synth_transfer_forecast.cpp")
```

Implementation anchor:
`DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:45-47`.

The exported C++ entrypoint is:

```cpp
DISC_update_theta_synth_cpp_W(...)
```

Implementation anchor:
`DISC_kalman_synth_transfer_forecast.cpp:1031-1043`.

Historical filter equations in C++:

\[
a_t=G_t m_{t-1},
\qquad
P_t=G_t C_{t-1}G_t^\top,
\]

\[
R_t=P_t + ex.df.mat\circ P_t,
\qquad
f_t=FF_t^\top a_t+FFF_t,
\qquad
q_t=FF_t^\top R_tFF_t+QQQ_t,
\]

\[
m_t=a_t+R_tFF_tq_t^{-1}(y_t-f_t),
\qquad
C_t=R_t-R_tFF_tq_t^{-1}FF_t^\top R_t^\top.
\]

Code anchors:
`DISC_kalman_synth_transfer_forecast.cpp:1147-1200`.

Forecast filter equations use the same pattern but:

- transition and state dimension are segment-specific,
- source loading columns are expanded by `num_mem`,
- `W_list_ens` is added directly to forecast process covariance,
- `ex_f_list_ens` and `ex_q_list_ens` are member-expanded.

Code anchors:
`DISC_kalman_synth_transfer_forecast.cpp:1212-1350`.

## Kalman Fixture Evidence

The script
`repro/audits/run_exdqlm_keep_kalman_fixture.R` compiles the transfer C++ core
and runs a deterministic `p=1`, `J=1`, `ppx=0`, `TT=2`, one-member forecast
fixture. It compares the historical filtered mean/covariance against an R
reference implementation of the same equations and checks covariance symmetry.

Result:

| Check | Value | Tolerance | Status |
|---|---:|---:|---|
| historical filtered mean max abs diff | `6.26023677341436e-11` | `1e-10` | pass |
| historical filtered covariance max abs diff | `7.3717032478271e-11` | `1e-10` | pass |
| historical filtered covariance symmetry | `0` | `1e-12` | pass |
| historical smoothed covariance symmetry | `0` | `1e-12` | pass |
| forecast filtered covariance symmetry | `0` | `1e-12` | pass |
| forecast smoothed covariance symmetry | `0` | `1e-12` | pass |

Evidence file:
`reports/exdqlm_multivar_keep_kalman_fixture_20260520/kalman_fixture_checks.csv`.

Status: the basic historical filtering algebra and covariance symmetry are
cleared for a small deterministic fixture. This does not clear the full
transfer-retained ragged forecast smoother under production dimensions.

## Current Kalman-Layer Risks

1. Robust inverses and SPD repairs are used in C++:
   `DISC_kalman_synth_transfer_forecast.cpp:96-132`,
   `DISC_kalman_synth_transfer_forecast.cpp:134-158`.
   These are good defensive numerics, but they can hide severe pseudo-data
   conditioning.
2. R-side forecast covariance updates force SPD through jitter/eigenvalue
   flooring at `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:3071-3112`.
   Runtime evidence should quantify whether this is rare hygiene or frequent
   repair.
3. The smoothing equations for ragged forecast segments are more complex than
   the small fixture, especially at segment transitions and with `ppx > 0`.
   The fixture verifies a lower-level contract, not the full production path.

## Verdict

| Component | Status | Evidence |
|---|---|---|
| historical pseudo-data algebra | confirmed | theory derivation, active code lines `3539-3545`, unit test |
| forecast pseudo-data algebra | confirmed structurally | active code lines `3552-3587`; shape validator |
| C++ offset convention | confirmed | C++ uses `f=FF'a+ex_f` at `1155-1200` and `1265-1274` |
| historical Kalman filter | confirmed on fixture | fixture max diff `< 1e-10` |
| covariance symmetry | confirmed on fixture | fixture symmetry checks pass |
| full ragged transfer smoother | inconclusive | needs production-dimension fixture/runtime evidence |
| pseudo-data as instability channel | confirmed plausible | formulas show direct dependence on `sigma/gamma/s/u` |

## Fix / Evidence Priorities

1. `P0`: add runtime extraction for `FFF`, `QQQ`, state norms, and covariance
   eigenvalues from saved objects and logs.
2. `P1`: add a production-shaped but tiny `ppx > 0`, `J = 2`, ragged-horizon
   Kalman fixture if debugging points toward segment transitions.
3. `P1`: instrument or post-process counts of SPD projection/flooring in R-side
   covariance updates and C++ robust inverse fallbacks.
4. `P2`: if pseudo-data ranges are healthy but states still drift, prioritize a
   deeper RTS segment-transition audit.
