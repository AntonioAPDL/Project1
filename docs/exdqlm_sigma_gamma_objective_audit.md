# exDQLM Sigma/Gamma Objective Audit

Date: 2026-05-20

## Purpose

This document is the Stage 4 audit for the joint variational update of `(sigma, gamma)` in the
current exDQLM workflow.

This is not a restatement of old notes. The objective here is to:

1. extract the current intended mathematical contract from the canonical manuscript,
2. derive the exact transformed objective used by the active implementation,
3. compare them term by term,
4. record what is confirmed and what remains unresolved.

## Sources checked directly

Primary theory:
- `/data/muscat_data/jaguir26/exDQLM---Ensemble/main.tex`
  - joint kernel: lines 735-778
  - transform and Jacobian: lines 1125-1148
  - Laplace covariance and Delta method: lines 1162-1205

Current implementation:
- `/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_Optimal_Synth_Ranges_W_transfer_forecast.r`
  - `PriorGammaDens`: lines 1863-1870
  - `update_gamma_sigma`: lines 1874 onward
  - non-forecast `dq_transf`: lines 2031-2065
  - forecast-augmented `dq_transf`: lines 2075-2115
  - mode / Hessian / covariance: lines 2233-2317
  - Delta expectations: lines 2333-2471

Current helper definitions:
- `/data/muscat_data/jaguir26/project1_ucsc_phd/R/environmetrics/02_helpers_core.R`
  - `L_fn`, `U_fn`, `p_fn`, `A_fn`, `B_fn`, `C_fn`

Historical comparison only:
- `Optimal_DQLM.r`
- `opt_delta.r`
- `opt_delta_3.r`
- `docs/DERIVATION_AUDIT.md`

## 1. Current symbol mapping

The manuscript writes the source-specific objective over observations `n in I_s`.
The current implementation uses the following objects:

| Theory quantity | Current code object | Meaning |
|---|---|---|
| `y_n` | `y` or `ensembles_j` | observed response |
| `E_q[eta_n]` | `exps` | posterior mean of linear predictor |
| `E_q[eta_n^2]` | `exps2` | posterior second moment of linear predictor |
| `E_q[s_n]` | `sts` or `sts_f` | posterior mean of positive latent |
| `E_q[s_n^2]` | `sts2` or `sts2_f` | posterior second moment of positive latent |
| `E_q[v_n]` | `uts` or `uts_f` | posterior mean of exponential/GIG latent |
| `E_q[1 / v_n]` | `inv.uts` or `inv.uts_f` | posterior inverse moment |
| `N_s` | `nn` or `nn + k_forecast * num_mem_j` | number of observations contributing to the source objective |

The forecast-augmented branch uses the same source-specific `(sigma, gamma)` for both:
- historical observations
- forecast ensemble-member observations

That is a current implementation specialization of the generic manuscript index set `I_s`.

## 2. Manuscript joint kernel

The manuscript gives

\[
q^*(\sigma^s,\gamma^s) \propto
\mathbf 1(L < \gamma^s < U)\,
\mathrm{IG}(\sigma^s \mid a_\sigma, b_\sigma)\,
t_{(L,U)}(\gamma^s \mid m_\gamma, s_\gamma; \nu_\gamma)
\times
(\sigma^s)^{-N_s}
\exp\!\left(-\frac{\sum_n E_q[v_n]}{\sigma^s}\right)
\prod_n (\sigma^s B^s)^{-1/2}
\exp\!\left(
-\frac12 E_q\!\left[
\frac{(y_n - \eta_n - A^s v_n - C^s \sigma^s |\gamma^s| s_n)^2}{\sigma^s B^s v_n}
\right]
\right).
\]

Theory anchors:
- `main.tex` lines 748-762

Expanding the quadratic expectation yields

\[
E_q\!\left[
\frac{(y_n-\eta_n-A^s v_n-C^s \sigma^s |\gamma^s| s_n)^2}{\sigma^s B^s v_n}
\right]
 =
\frac{1}{\sigma^s B^s}
\left(
E_q[(y_n-\eta_n)^2] E_q[1/v_n]
- 2 A^s E_q[y_n-\eta_n]
+ (A^s)^2 E_q[v_n]
\right)
- \frac{2 C^s |\gamma^s|}{B^s}
\left(
E_q[s_n] E_q[y_n-\eta_n] E_q[1/v_n]
- A^s E_q[s_n]
\right)
+ \frac{\sigma^s (C^s)^2 (\gamma^s)^2}{B^s}
E_q[s_n^2] E_q[1/v_n].
\]

Theory anchors:
- `main.tex` lines 766-779

## 3. Current code objective: non-forecast branch

The active non-forecast branch is:

```r
yy <- log(prior_gamma_dens) - (prior_s[1] + 1) * log(sig) - prior_s[2]/sig
yy <- yy - (1.5*nn)*log(sig) - (0.5*nn)*log(b) - sum(uts)/sig
yy <- yy - 0.5*sum(
  inv.uts*(y^2 - 2*y*exps + exps2)/sig
  - (y-exps)*2*(inv.uts*c*abs(gam)*sts + a/sig)
  + sig*inv.uts*(c^2)*(abs(gam)^2)*sts2
  + 2*c*abs(gam)*sts*a
  + (uts*a^2)/sig
)/b
yy <- yy + theta_s + log(U - L) + log(pi) + log1p(-pi)
```

Code anchors:
- `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r` lines 2044-2061

Here:
- `sig = exp(theta_s)`
- `gam = L + (U-L) * plogis(theta_g)`
- `a = A.fn(p0, gam)`
- `b = B.fn(p0, gam)`
- `c = C.fn(p0, gam)`

## 4. Why the code has `-1.5 * N * log(sig)`

This can look suspicious if read too quickly, but it matches the manuscript kernel.

From the manuscript:

1. the latent-variable prior contributes
   \[
   (\sigma^s)^{-N_s} \exp\!\left(-\frac{\sum_n E_q[v_n]}{\sigma^s}\right),
   \]
2. the Gaussian observation part contributes
   \[
   \prod_n (\sigma^s B^s)^{-1/2}.
   \]

Combining those terms gives

\[
-N_s \log \sigma^s - \frac{N_s}{2}\log \sigma^s - \frac{N_s}{2}\log B^s
= -\frac{3 N_s}{2}\log \sigma^s - \frac{N_s}{2}\log B^s.
\]

That matches the code term:

```r
-(1.5*nn)*log(sig) - (0.5*nn)*log(b)
```

Status: `confirmed`

## 5. Term-by-term manuscript-to-code match

The table below compares the manuscript kernel to the current active implementation.

| Component | Manuscript expression | Current code | Status |
|---|---|---|---|
| gamma prior | `log t_(L,U)(gamma)` | `log(prior_gamma_dens)` | confirmed |
| sigma prior | `log IG(sigma)` | `-(prior_s[1]+1) log(sig) - prior_s[2] / sig` | confirmed |
| latent `v` prior normalization | `-N_s log sigma` | included in `-(1.5*N_s) log(sig)` | confirmed |
| Gaussian normalization | `-(N_s/2) log(sigma B)` | `-(0.5*N_s) log(b)` plus the extra `-0.5*N_s log(sig)` inside `-1.5*N_s log(sig)` | confirmed |
| latent `v` exponential rate term | `- sum E[v_n] / sigma` | `-sum(uts) / sig` | confirmed |
| `E[(y-eta)^2] E[1/v] / (sigma B)` | first term of quadratic expansion | `inv.uts*(y^2 - 2*y*exps + exps2) / sig / b` | confirmed |
| `-2 A E[y-eta] / (sigma B)` | quadratic expansion | `-(y-exps) * 2 * (a / sig) / b` | confirmed |
| `-(2 C |gamma| / B) E[s] E[y-eta] E[1/v]` | quadratic expansion | `-(y-exps) * 2 * (inv.uts * c * abs(gam) * sts) / b` | confirmed |
| `A^2 E[v] / (sigma B)` | quadratic expansion | `(uts * a^2) / sig / b` | confirmed |
| `+ 2 A C |gamma| E[s] / B` | quadratic expansion | `2 * c * abs(gam) * sts * a / b` | confirmed |
| `sigma C^2 gamma^2 E[s^2] E[1/v] / B` | quadratic expansion | `sig * inv.uts * c^2 * abs(gam)^2 * sts2 / b` | confirmed |
| transform `u = log sigma` | manuscript transform | `sig <- exp(theta_s)` | confirmed |
| transform `gamma = L + (U-L) logistic(xi)` | manuscript transform | `gam <- L + (U-L) * plogis(theta_g)` | confirmed |
| Jacobian | `u + log(U-L) + log(pi) + log(1-pi)` | `theta_s + log(U-L) + log(pi) + log1p(-pi)` | confirmed |

## 6. Current code objective: forecast-augmented branch

When `Climate_Center = TRUE`, the current code extends the same source-specific objective by adding
forecast ensemble-member observations:

```r
yy <- yy - 1.5*(nn + k_forecast*num_mem_j)*log(sig)
yy <- yy - 0.5*(nn + k_forecast*num_mem_j)*log(b)
yy <- yy - (sum(uts) + sum(uts_f)) / sig
yy <- yy - 0.5 * [historical quadratic sum] / b
yy <- yy - 0.5 * [forecast quadratic sum] / b
```

Code anchors:
- `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r` lines 2096-2109

Interpretation:
- the same `(sigma^s, gamma^s)` block is shared across the source's historical and forecast-member
  observations
- the forecast branch is not a different objective family; it is the same kernel applied to an
  enlarged effective index set

Status: `confirmed as the current implementation contract`

## 7. Transform and Jacobian audit

The manuscript requires:

\[
u = \log \sigma,
\qquad
\gamma = L + (U-L)\,\pi(\xi),
\qquad
\pi(\xi) = \frac{1}{1+e^{-\xi}},
\]

with

\[
\log |J(u,\xi)| =
u + \log(U-L) + \log \pi(\xi) + \log(1-\pi(\xi)).
\]

Theory anchors:
- `main.tex` lines 1125-1148

The current code does exactly that:

```r
pi <- plogis(theta_g)
pi <- pmin(pmax(pi, 1e-12), 1 - 1e-12)
gam <- L + (U - L) * pi
yy <- yy + theta_s + log(U - L) + log(pi) + log1p(-pi)
```

Code anchors:
- `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r` lines 2033-2061
- `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r` lines 2077-2111

This also matches the manuscript's numerical note about clipping the logistic probability away from
exact `0` and `1`.

Status: `confirmed`

## 8. Historical mismatch: older scripts are stale here

The historical scripts and the older derivation note still use:

\[
\gamma = LL + (UU-LL)\exp(-\exp(\theta_g)),
\qquad
\log|J| = \theta_s + \theta_g - \exp(\theta_g)
\]

Evidence:
- `Optimal_DQLM.r` lines 1014-1026
- `opt_delta.r` lines 1163-1175 and 2042-2054
- `opt_delta_3.r` lines 1163-1175 and 2042-2054
- `docs/DERIVATION_AUDIT.md` lines 112-127

That is not the current active implementation and not the canonical manuscript transform.

Status: `confirmed stale for the current workflow`

## 9. What is confirmed

### Confirmed O1
The current active `dq_transf` matches the manuscript joint kernel structurally and term by term.

### Confirmed O2
The current active `dq_transf` uses the logistic `gamma` transform and the correct Jacobian from the
canonical manuscript.

### Confirmed O3
The forecast-augmented branch is the same objective family, extended over a larger source-specific
observation set.

## 10. What is not taken for granted

The following were explicitly checked rather than assumed:

1. the `-1.5 * N * log(sig)` term
2. the placement of `/ b` inside the observation sum
3. the exact Jacobian sign and constants
4. whether the current code still used the old double-exponential interior map

Each of those is now tied to source lines in both the manuscript and the active implementation.

## 11. What remains unresolved for the next audit stage

These are not objective mismatches, but they are important implementation questions for the next
stage:

1. The manuscript recommends split optimization across `gamma < 0` and `gamma > 0` when the mode is
   near zero because of nonsmoothness from `|gamma|`. The current code does not implement that split
   optimization directly.
2. The manuscript notes that some `u`-only moments are available exactly under the Gaussian
   Laplace approximation. The current code uses the generic second-order Delta-method helper for all
   returned expectations instead.
3. The current code adds robustification layers:
   - objective guards
   - Hessian regularization
   - fallback modes
   These are implementation stabilizers and must be audited separately from the mathematical kernel.

## 12. Stage 4 conclusion

For the current active implementation path:

- the joint `(sigma, gamma)` objective matches the canonical manuscript kernel
- the transformed objective uses the correct logistic map and Jacobian
- older documentation and historical scripts that still show the double-exponential map are not
  authoritative for the current workflow

So the next meaningful step is no longer "find the formula." We now have the formula locked.

The next meaningful step is:
- audit the Laplace mode/Hessian/covariance step,
- then audit the returned Delta expectations,
- and only after that compare any remaining differences in behavior to the current implementation.
