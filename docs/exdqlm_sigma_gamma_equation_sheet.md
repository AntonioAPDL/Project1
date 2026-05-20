# exDQLM Equation Sheet

Date: 2026-05-20

## Scope

This document is the Stage 2 mathematical contract for the current exAL / exDQLM workflow in this
repository. It is deliberately narrow:

- base exAL observation model
- historical multivariate discrepancy model
- forecast `drop` and `keep` variants
- latent augmentation used for conditional Gaussian updates
- VB pseudo-data construction
- joint variational update for `(sigma, gamma)`
- Laplace-Delta transform, Jacobian, mode covariance, and expectation formulas

This sheet does **not** assume that older project notes are correct. Every expression here is grounded
in:

1. the canonical manuscript source:
   - [main.tex](/data/muscat_data/jaguir26/exDQLM---Ensemble/main.tex)
2. the current implementation path:
   - [R/environmetrics/02_helpers_core.R](/data/muscat_data/jaguir26/project1_ucsc_phd/R/environmetrics/02_helpers_core.R:1508)
   - [R/environmetrics/20_model_setup.R](/data/muscat_data/jaguir26/project1_ucsc_phd/R/environmetrics/20_model_setup.R:207)
   - [DISC_Optimal_Synth_Ranges_W_transfer_forecast.r](/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:1874)

## 1. exAL support bounds and coefficient maps

For a target quantile `p0`, define:

\[
g(\gamma)=2\Phi(-|\gamma|)\exp(\gamma^2/2),
\]
\[
L = \text{negative root of } g(\gamma)=1-p_0,
\qquad
U = \text{positive root of } g(\gamma)=p_0.
\]

Then define:

\[
p(p_0,\gamma)=\mathbf{1}(\gamma<0)+\frac{p_0-\mathbf{1}(\gamma<0)}{g(\gamma)},
\]
\[
A(\gamma;p_0)=\frac{1-2p}{p(1-p)},
\qquad
B(\gamma;p_0)=\frac{2}{p(1-p)},
\qquad
C(\gamma;p_0)=\big(\mathbf{1}(\gamma>0)-p\big)^{-1}.
\]

Canonical manuscript anchors:
- [main.tex:148](/data/muscat_data/jaguir26/exDQLM---Ensemble/main.tex:148)
- [main.tex:150](/data/muscat_data/jaguir26/exDQLM---Ensemble/main.tex:150)

Current implementation anchors:
- support bounds:
  - [R/environmetrics/02_helpers_core.R:1508](/data/muscat_data/jaguir26/project1_ucsc_phd/R/environmetrics/02_helpers_core.R:1508)
  - [R/environmetrics/02_helpers_core.R:1512](/data/muscat_data/jaguir26/project1_ucsc_phd/R/environmetrics/02_helpers_core.R:1512)
- `p`, `A`, `B`, `C`:
  - [R/environmetrics/02_helpers_core.R:1516](/data/muscat_data/jaguir26/project1_ucsc_phd/R/environmetrics/02_helpers_core.R:1516)
  - [R/environmetrics/02_helpers_core.R:1520](/data/muscat_data/jaguir26/project1_ucsc_phd/R/environmetrics/02_helpers_core.R:1520)
  - [R/environmetrics/02_helpers_core.R:1525](/data/muscat_data/jaguir26/project1_ucsc_phd/R/environmetrics/02_helpers_core.R:1525)
  - [R/environmetrics/02_helpers_core.R:1530](/data/muscat_data/jaguir26/project1_ucsc_phd/R/environmetrics/02_helpers_core.R:1530)

Status: `confirmed`

## 2. Historical baseline + transfer model (Model A)

For historical times `t = 1, ..., T`:

\[
y_t^o \mid \theta_t,\zeta_t,\sigma^o,\gamma^o
\sim \mathrm{exAL}_{p_0}\big(F_t^\top \theta_t+\zeta_t,\sigma^o,\gamma^o\big),
\]
\[
\theta_t \mid \theta_{t-1}
\sim \mathcal{N}(G_t\theta_{t-1},W_t^\theta),
\]
\[
\zeta_t \mid \zeta_{t-1},\psi_t
\sim \mathcal{N}(\lambda\zeta_{t-1}+x_t^\top\psi_t,w_t^\zeta),
\]
\[
\psi_t \mid \psi_{t-1}
\sim \mathcal{N}(\psi_{t-1},W_t^\psi).
\]

Stacked state:

\[
\alpha_t =
\begin{bmatrix}
\theta_t\\
\zeta_t\\
\psi_t
\end{bmatrix},
\qquad
\tilde F_t=
\begin{bmatrix}
F_t\\
1\\
0
\end{bmatrix},
\]
so that
\[
y_t^o \mid \alpha_t,\sigma^o,\gamma^o
\sim \mathrm{exAL}_{p_0}\big(\tilde F_t^\top \alpha_t,\sigma^o,\gamma^o\big).
\]

Canonical manuscript anchors:
- [main.tex:63](/data/muscat_data/jaguir26/exDQLM---Ensemble/main.tex:63)
- [main.tex:67](/data/muscat_data/jaguir26/exDQLM---Ensemble/main.tex:67)
- [main.tex:95](/data/muscat_data/jaguir26/exDQLM---Ensemble/main.tex:95)

Status: `confirmed as intended theory`

## 3. Historical discrepancy model (Model B)

For retrospective source `j = 1, ..., J`:

\[
z_t^j \mid \alpha_t,\delta_t^j,\sigma^j,\gamma^j
\sim
\mathrm{exAL}_{p_0}\big(\tilde F_t^\top\alpha_t + F_t^\top\delta_t^j,\sigma^j,\gamma^j\big),
\]
\[
\delta_t^j \mid \delta_{t-1}^j
\sim \mathcal{N}(G_t\delta_{t-1}^j,W_t^{\delta^j}).
\]

Canonical manuscript anchors:
- [main.tex:107](/data/muscat_data/jaguir26/exDQLM---Ensemble/main.tex:107)
- [main.tex:109](/data/muscat_data/jaguir26/exDQLM---Ensemble/main.tex:109)

Status: `confirmed as intended theory`

## 4. Forecast model with transfer dropped (Model C)

Forecast-period state:

\[
\beta_t=
\begin{bmatrix}
\theta_t\\
\delta_t^f
\end{bmatrix},
\qquad
\delta_t^f=
\begin{bmatrix}
\delta_t^1\\
\vdots\\
\delta_t^{J_f}
\end{bmatrix}.
\]

Observation model:

\[
y_T^{j,i}(k)\mid \beta_{T+k},\sigma^j,\gamma^j
\sim
\mathrm{exAL}_{p_0}\big(e_{T+k,j+1}^\top\beta_{T+k},\sigma^j,\gamma^j\big).
\]

Transition:

\[
\beta_t \mid \beta_{t-1},W_t
\sim \mathcal{N}(M_t\beta_{t-1},W_t).
\]

Canonical manuscript anchors:
- [main.tex:139](/data/muscat_data/jaguir26/exDQLM---Ensemble/main.tex:139)
- [main.tex:141](/data/muscat_data/jaguir26/exDQLM---Ensemble/main.tex:141)

Current implementation interpretation:
- when `forecast_transfer_mode = "drop"`, forecast FF/GG omit the transfer coordinates
- code anchor:
  - [R/environmetrics/20_model_setup.R:271](/data/muscat_data/jaguir26/project1_ucsc_phd/R/environmetrics/20_model_setup.R:271)

Status: `confirmed`

## 5. Forecast model with transfer retained (Model C-T / keep mode)

Forecast segment state:

\[
\beta_t^{(s)}=
\begin{bmatrix}
\theta_t\\
\delta_t^{1:a_s}\\
\tau_t
\end{bmatrix},
\qquad
\tau_t=
\begin{bmatrix}
\zeta_t\\
\psi_t
\end{bmatrix}.
\]

Observation model:

\[
y_T^{j,i}(k)\mid \beta_{T+k}^{(s)},\sigma^j,\gamma^j
\sim
\mathrm{exAL}_{p_0}\big((h_{T+k,j}^{(s)})^\top \beta_{T+k}^{(s)},\sigma^j,\gamma^j\big),
\]

where the loading includes:
- baseline state contribution
- discrepancy-state contribution
- retained transfer contribution

Transition:

\[
\beta_t^{(s)}\mid\beta_{t-1}^{(s)}
\sim \mathcal{N}(M_t^{(s)}\beta_{t-1}^{(s)},W_t^{(s)}),
\]

with transfer block

\[
G_t^{\mathrm{trans}}=
\begin{bmatrix}
\lambda & x_t^\top\\
0 & I
\end{bmatrix}.
\]

Canonical manuscript anchors:
- [main.tex:161](/data/muscat_data/jaguir26/exDQLM---Ensemble/main.tex:161)
- [main.tex:192](/data/muscat_data/jaguir26/exDQLM---Ensemble/main.tex:192)
- [main.tex:200](/data/muscat_data/jaguir26/exDQLM---Ensemble/main.tex:200)
- [main.tex:223](/data/muscat_data/jaguir26/exDQLM---Ensemble/main.tex:223)

Current implementation anchors:
- switch:
  - [R/environmetrics/20_model_setup.R:208](/data/muscat_data/jaguir26/project1_ucsc_phd/R/environmetrics/20_model_setup.R:208)
- retained transfer GG block:
  - [R/environmetrics/20_model_setup.R:226](/data/muscat_data/jaguir26/project1_ucsc_phd/R/environmetrics/20_model_setup.R:226)
  - [R/environmetrics/20_model_setup.R:262](/data/muscat_data/jaguir26/project1_ucsc_phd/R/environmetrics/20_model_setup.R:262)
- retained transfer FF load:
  - [R/environmetrics/20_model_setup.R:269](/data/muscat_data/jaguir26/project1_ucsc_phd/R/environmetrics/20_model_setup.R:269)

Status: `confirmed as a distinct current forecast-mode specialization`

## 6. exAL latent augmentation

For a scalar datum with predictor `eta_n`:

\[
y_n \mid \eta_n,\sigma,\gamma,v_n,s_n
\sim
\mathcal{N}\big(
\eta_n + C(p,\gamma)\sigma|\gamma|s_n + A(p)v_n,\;
\sigma B(p)v_n
\big),
\]
\[
v_n \mid \sigma \sim \mathrm{Exp}(\text{rate}=1/\sigma),
\qquad
s_n \sim \mathcal{N}^+(0,1).
\]

Canonical manuscript anchors:
- [main.tex:153](/data/muscat_data/jaguir26/exDQLM---Ensemble/main.tex:153)
- [main.tex:159](/data/muscat_data/jaguir26/exDQLM---Ensemble/main.tex:159)

Status: `confirmed`

## 7. Conditional of `v_t`

Let

\[
r_t = y_t - \eta_t - C(p,\gamma)\sigma|\gamma|s_t.
\]

Then

\[
v_t \mid \text{rest}
\sim
\mathrm{GIG}\left(
\lambda=\tfrac12,\;
\chi=\frac{r_t^2}{\sigma B},\;
\psi=\frac{A^2}{\sigma B}+\frac{2}{\sigma}
\right),
\]

under density

\[
f(v)\propto v^{\lambda-1}\exp\left\{-\tfrac12(\chi/v+\psi v)\right\}\mathbf{1}(v>0).
\]

Canonical manuscript anchors:
- [main.tex:331](/data/muscat_data/jaguir26/exDQLM---Ensemble/main.tex:331)
- [main.tex:337](/data/muscat_data/jaguir26/exDQLM---Ensemble/main.tex:337)

Status: `confirmed as intended theory`

## 8. Conditional of `s_t`

Let

\[
y_t^\circ = y_t - \eta_t - A v_t,
\qquad
d = C(p,\gamma)\sigma|\gamma|,
\qquad
R_t = \sigma B v_t.
\]

Then

\[
s_t \mid \text{rest} \sim \mathcal{N}^+(m_{s,t},V_{s,t}),
\]

with

\[
V_{s,t} =
\left(1 + \frac{d^2}{R_t}\right)^{-1}
=
\left(1+\frac{C(p,\gamma)^2 \sigma \gamma^2}{B v_t}\right)^{-1},
\]
\[
m_{s,t}
=
V_{s,t}\left(\frac{d y_t^\circ}{R_t}\right)
=
V_{s,t}\left(\frac{C(p,\gamma)|\gamma|}{B v_t} y_t^\circ\right).
\]

Canonical manuscript anchors:
- [main.tex:356](/data/muscat_data/jaguir26/exDQLM---Ensemble/main.tex:356)
- [main.tex:359](/data/muscat_data/jaguir26/exDQLM---Ensemble/main.tex:359)

Status: `confirmed as intended theory`

## 9. VB pseudo-data for the Gaussian state update

For each scalar observation `n`, define:

\[
w_n = \mathbb{E}_q\left[\frac{1}{R_n}\right]
=
\mathbb{E}_q\left[\frac{1}{\sigma^s B^s}\right]
\mathbb{E}_q\left[\frac{1}{v_n}\right],
\]

\[
b_n =
\mathbb{E}_q\left[\frac{\tilde y_n}{R_n}\right]
=
y_n w_n
- \mathbb{E}_q\left[\frac{C^s|\gamma^s|}{B^s}\right]\mathbb{E}_q[s_n]\mathbb{E}_q\left[\frac{1}{v_n}\right]
- \mathbb{E}_q\left[\frac{A^s}{\sigma^s B^s}\right].
\]

Equivalent pseudo-data:

\[
\bar y_n = \frac{b_n}{w_n},
\qquad
\bar R_n = \frac{1}{w_n}.
\]

Canonical manuscript anchors:
- [main.tex:711](/data/muscat_data/jaguir26/exDQLM---Ensemble/main.tex:711)
- [main.tex:716](/data/muscat_data/jaguir26/exDQLM---Ensemble/main.tex:716)
- [main.tex:956](/data/muscat_data/jaguir26/exDQLM---Ensemble/main.tex:956)

Status: `confirmed as intended theory`

## 10. Joint VB factor for `(sigma^s, gamma^s)`

The optimal joint factor satisfies:

\[
q^*(\sigma^s,\gamma^s)
\propto
\exp\left(
\mathbb{E}_{q(\text{others})}[\log p(\text{augmented joint})]
\right),
\qquad
\sigma^s > 0,\;
\gamma^s \in (L,U).
\]

Expanded kernel:

\[
q^*(\sigma^s,\gamma^s)
\propto
\mathbf{1}(L<\gamma^s<U)\;
\mathrm{IG}(\sigma^s\mid a_\sigma,b_\sigma)\;
t_{(L,U)}(\gamma^s\mid m_\gamma,s_\gamma;\nu_\gamma)
\]
\[
\times
(\sigma^s)^{-N_s}
\exp\left(
-\frac{\sum_{n\in\mathcal{I}_s}\mathbb{E}_q[v_n]}{\sigma^s}
\right)
\prod_{n\in\mathcal{I}_s}
(\sigma^s B^s)^{-1/2}
\exp\left(
-\frac12
\mathbb{E}_q
\left[
\frac{(y_n-\eta_n-A^s v_n-C^s\sigma^s|\gamma^s|s_n)^2}{\sigma^s B^s v_n}
\right]
\right).
\]

Canonical manuscript anchors:
- [main.tex:735](/data/muscat_data/jaguir26/exDQLM---Ensemble/main.tex:735)
- [main.tex:748](/data/muscat_data/jaguir26/exDQLM---Ensemble/main.tex:748)
- [main.tex:760](/data/muscat_data/jaguir26/exDQLM---Ensemble/main.tex:760)

Current implementation structure:
- prior term:
  - [DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:2044](/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:2044)
- historical likelihood term:
  - [DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:2052](/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:2052)
- forecast-augmented likelihood term:
  - [DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:2096](/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:2096)

Status: `confirmed at the structural level; detailed term-by-term comparison is the next audit stage`

## 11. Laplace-Delta transform for `(sigma, gamma)`

The current intended transform is:

\[
u = \log \sigma \in \mathbb{R},
\qquad
\gamma = L + (U-L)\pi(\xi),
\qquad
\pi(\xi)=\frac{1}{1+e^{-\xi}},
\]

with Jacobian

\[
\left|
\frac{\partial(\sigma,\gamma)}{\partial(u,\xi)}
\right|
=
\sigma (U-L)\pi(\xi)(1-\pi(\xi)),
\]

\[
\log |J(u,\xi)|
=
u + \log(U-L) + \log \pi(\xi) + \log(1-\pi(\xi)).
\]

Transformed objective:

\[
\tilde f(u,\xi) = f(e^u,\gamma(\xi)) + \log |J(u,\xi)|.
\]

Canonical manuscript anchors:
- [main.tex:1125](/data/muscat_data/jaguir26/exDQLM---Ensemble/main.tex:1125)
- [main.tex:1139](/data/muscat_data/jaguir26/exDQLM---Ensemble/main.tex:1139)
- [main.tex:1147](/data/muscat_data/jaguir26/exDQLM---Ensemble/main.tex:1147)

Current implementation anchors:
- map:
  - [DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:2032](/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:2032)
  - [DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:2036](/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:2036)
- Jacobian term:
  - [DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:2060](/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:2060)
  - [DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:2110](/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:2110)
- clipped interior safeguard:
  - [DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:2034](/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:2034)

Status: `confirmed`

## 12. Laplace mode, covariance, and Delta expectations

Mode and covariance:

\[
(\hat u,\hat \xi) = \arg\max_{(u,\xi)\in\mathbb{R}^2} \tilde f(u,\xi),
\qquad
\hat\Sigma = \left(-\nabla^2 \tilde f(\hat u,\hat \xi)\right)^{-1}.
\]

Approximate transformed factor:

\[
q(u,\xi)\approx \mathcal{N}_2\big((\hat u,\hat \xi)^\top,\hat\Sigma\big).
\]

Second-order Delta method for any `g(u, xi)`:

\[
\mathbb{E}[g(u,\xi)]
\approx
g(\hat\mu) + \frac12 \operatorname{tr}\left(\nabla^2 g(\hat\mu)\hat\Sigma\right),
\qquad
\hat\mu = (\hat u,\hat \xi)^\top.
\]

Exact normal moment for `u`-only exponential terms:

\[
\mathbb{E}[e^{a u}] = \exp\left(a\hat u + \tfrac12 a^2 \hat\Sigma_{uu}\right).
\]

Canonical manuscript anchors:
- [main.tex:1162](/data/muscat_data/jaguir26/exDQLM---Ensemble/main.tex:1162)
- [main.tex:1169](/data/muscat_data/jaguir26/exDQLM---Ensemble/main.tex:1169)
- [main.tex:1181](/data/muscat_data/jaguir26/exDQLM---Ensemble/main.tex:1181)
- [main.tex:1189](/data/muscat_data/jaguir26/exDQLM---Ensemble/main.tex:1189)

Current implementation anchors:
- optimization:
  - [DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:2265](/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:2265)
- curvature estimation:
  - [DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:2314](/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:2314)
  - [DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:2165](/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:2165)
- generic expectation helper:
  - [DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:2343](/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:2343)

Status: `confirmed at the structural level`

## 13. Functions explicitly needed by the VB updates

The manuscript already lists the core functions whose expectations are needed:

\[
g_{1/(\sigma B)}(u,\xi)=\frac{e^{-u}}{B(\gamma(\xi))},
\qquad
g_{A/(\sigma B)}(u,\xi)=\frac{A(\gamma(\xi))e^{-u}}{B(\gamma(\xi))},
\]
\[
g_{A^2/(\sigma B)}(u,\xi)=\frac{A(\gamma(\xi))^2 e^{-u}}{B(\gamma(\xi))},
\qquad
g_{1/\sigma}(u)=e^{-u},
\]
\[
g_{C|\gamma|/B}(\xi)=\frac{C(\gamma(\xi))|\gamma(\xi)|}{B(\gamma(\xi))},
\qquad
g_{AC|\gamma|/B}(\xi)=\frac{A(\gamma(\xi))C(\gamma(\xi))|\gamma(\xi)|}{B(\gamma(\xi))},
\]
\[
g_{\sigma C^2\gamma^2/B}(u,\xi)=
e^u \frac{C(\gamma(\xi))^2 \gamma(\xi)^2}{B(\gamma(\xi))},
\qquad
g_{\log B}(\xi)=\log B(\gamma(\xi)).
\]

Canonical manuscript anchors:
- [main.tex:1199](/data/muscat_data/jaguir26/exDQLM---Ensemble/main.tex:1199)
- [main.tex:1205](/data/muscat_data/jaguir26/exDQLM---Ensemble/main.tex:1205)

Current implementation realizations:
- stored output fields:
  - [DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:1936](/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:1936)
  - [DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:1943](/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:1943)

Status: `confirmed conceptually; exact expectation-quality audit remains to be done`

## 14. What is confirmed now versus still pending

### Confirmed now
- the active repository has a canonical theory source
- the active implementation uses the logistic `gamma` transform, not the older double-exponential map
- `keep` vs `drop` is a real forecast-stage model distinction in both manuscript and current code
- the current implementation structure for `q(sigma, gamma)` matches the manuscript at a high level

### Still pending in the next audit stage
- term-by-term verification of the exact joint log-kernel used in `dq_transf`
- check of every expected quantity used in the sigma/gamma update
- sign convention and curvature quality of the Hessian / covariance step
- comparison of the current implementation with historical duplicates in:
  - [Optimal_DQLM.r](/data/muscat_data/jaguir26/project1_ucsc_phd/Optimal_DQLM.r)
  - [LD_vs_IS_synth.R](/data/muscat_data/jaguir26/project1_ucsc_phd/LD_vs_IS_synth.R)
  - [opt_delta.r](/data/muscat_data/jaguir26/project1_ucsc_phd/opt_delta.r)
  - [opt_delta_3.r](/data/muscat_data/jaguir26/project1_ucsc_phd/opt_delta_3.r)
