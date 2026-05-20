# exDQLM Laplace-Delta Audit

Date: 2026-05-20

## Purpose

This document is the Stage 5 audit for the Laplace / curvature / Delta-method layer of the current
`q(sigma, gamma)` implementation.

Stages 1-4 already established:

1. source precedence,
2. the active theory contract,
3. `keep` vs `drop`,
4. the current joint objective for `(sigma, gamma)`.

This stage focuses on what happens **after** the transformed objective is defined:

1. how the mode is found,
2. how the Hessian is turned into a covariance,
3. how expectations are computed from the Laplace approximation,
4. where the current implementation is faithful, approximate, or numerically defensive.

## Sources checked directly

Primary theory:
- `/data/muscat_data/jaguir26/exDQLM---Ensemble/main.tex`
  - transform and Jacobian: lines 1125-1148
  - near-zero smoothness note: lines 1151-1157
  - Laplace covariance: lines 1159-1172
  - Delta method and required functions: lines 1175-1208

Current active implementation:
- `/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_Optimal_Synth_Ranges_W_transfer_forecast.r`
  - seed handling and transform setup: lines 1900-2123
  - optimization: lines 2220-2313
  - Hessian/covariance: lines 2165-2195 and 2314-2324
  - Delta expectations: lines 2343-2466
  - return object: lines 2468-2478

Current runtime-use anchor:
- `/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:1874`

Historical comparison only:
- `/data/muscat_data/jaguir26/project1_ucsc_phd/R/environmetrics/20_model_setup.R`
- `/data/muscat_data/jaguir26/project1_ucsc_phd/docs/DERIVATION_AUDIT.md`

## 1. Manuscript Laplace-Delta contract

The canonical manuscript specifies:

\[
u = \log \sigma, \qquad
\gamma = L + (U-L)\pi(\xi), \qquad
\pi(\xi) = \frac{1}{1+e^{-\xi}}.
\]

with transformed objective

\[
\tilde f_s(u,\xi) = f_s(e^u, \gamma(\xi)) + \log|J(u,\xi)|.
\]

The Laplace approximation is then defined by:

\[
(\hat u, \hat \xi) = \arg\max \tilde f_s(u,\xi),
\qquad
\hat \Sigma = \left(-\nabla^2 \tilde f_s(\hat u,\hat \xi)\right)^{-1}.
\]

Theory anchors:
- `main.tex` lines 1125-1165

The manuscript also makes an important note:

- because `|gamma|` and the sign-dependent maps inside `p`, `A`, `B`, `C` can introduce
  nonsmoothness at `gamma = 0`,
- the optimization should be split across `gamma < 0` and `gamma > 0` if the mode is near zero.

Theory anchor:
- `main.tex` lines 1151-1157

The Delta-method layer then requires:

\[
\mathbb E_q[h(\sigma,\gamma)]
\approx
g(\hat \mu) + \frac12 \operatorname{tr}\left(\nabla^2 g(\hat \mu)\hat \Sigma\right),
\]

with exact closed-form exceptions for pure `u` exponentials such as:

\[
\mathbb E[e^{a u}] = \exp\left(a\hat u + \frac12 a^2 \Sigma_{uu}\right).
\]

Theory anchors:
- `main.tex` lines 1177-1208

## 2. Current mode-finding path

### 2.1 Seed handling

The active code:

1. sanitizes `s_init` into `s_seed`,
2. sanitizes `g_init` into `g_seed`,
3. clips `g_seed` into `(L,U)`,
4. maps the seed into transformed coordinates with
   - `theta_s_init = log(s_seed)`
   - `theta_g_init = qlogis((g_seed - L)/(U-L))`

Code anchors:
- `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r` lines 1900-1911
- `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r` lines 2119-2123

Status: `confirmed`

### 2.2 Optimization objective

The current code defines:

```r
objective_neg <- function(x) -dq_transf(x[1], x[2])
```

and then runs:

```r
optim(
  par = initial_values,
  fn = objective_neg,
  method = "L-BFGS-B",
  lower = c(theta_sigma_lower, theta_gamma_lower),
  upper = c(theta_sigma_upper, theta_gamma_upper),
  hessian = TRUE
)
```

Code anchors:
- `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r` lines 2232-2273

This is mathematically correct for maximizing the transformed log objective by minimizing its
negative.

Status: `confirmed`

### 2.3 Effective search domain

The manuscript parameterization uses unconstrained `(u, xi) in R^2`.

The current code instead uses bounded transformed coordinates:
- `theta_sigma_lower`, `theta_sigma_upper`
- `theta_gamma_lower`, `theta_gamma_upper`

with the current gamma bounds tied to clipped logistic probabilities.

Evidence:
- `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r` lines 1957-1966
- global defaults printed by `rg` at lines 243-244

Interpretation:
- this is not the pure unconstrained manuscript optimizer
- it is a numerically truncated version of that search
- because the logistic map is clipped anyway, this is a numerical stabilizer rather than a change
  to the intended target density

Status: `confirmed as a numerical stabilization`

### 2.4 Near-zero `gamma` handling

The manuscript recommends sign-split optimization when the mode is near `gamma = 0`.

The current code does **not** implement that split search directly.

What it does instead:
- clips `gamma` away from the boundaries,
- optionally damps the step for median quantiles,
- optionally falls back to sigma-only optimization for median quantiles,
- has a separate `DISC_W_AL_MODE` sigma-only branch.

Code anchors:
- step damping: lines 1978-2028
- sigma-only fallback: lines 2125-2163
- AL special case: lines 2197-2218

This is a real difference from the manuscript recommendation.

Status: `confirmed discrepancy at the optimization-policy level`

Impact:
- not a mismatch in the target objective,
- but a mismatch in how the mode search behaves near nondifferentiable `gamma = 0`.

## 3. Hessian and covariance construction

### 3.1 Current implementation

The current code first attempts:

```r
log_hessian_at_optimal <- numDeriv::hessian(
  func = function(theta_vec) dq_transf(theta_vec[[1L]], theta_vec[[2L]]),
  x = optim_results$par
)
```

and if that fails, it falls back to:

```r
log_hessian_at_optimal <- -optim_results$hessian
```

Code anchors:
- `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r` lines 2314-2323

This is consistent, because:
- `optim_results$hessian` is the Hessian of the minimized negative objective
- so `-optim_results$hessian` is the Hessian of the maximized transformed log objective

Status: `confirmed`

### 3.2 Covariance formula

The manuscript requires:

\[
\hat \Sigma = \left(-\nabla^2 \tilde f(\hat u,\hat \xi)\right)^{-1}.
\]

The current code computes:

```r
precision <- -(0.5 * (log_hessian + t(log_hessian)))
cov_candidate <- solve(precision + ridge * I)
```

Code anchors:
- `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r` lines 2165-2194

Interpretation:
- the Hessian is symmetrized before inversion
- the precision matrix is `-H`
- ridge regularization is added when necessary

So in the no-ridge case this matches the manuscript exactly.

Status: `confirmed`

### 3.3 Ridge regularization

The ridge loop:

```r
precision_reg <- precision + diag(ridge, nrow = nrow(precision))
```

is not part of the pure Laplace formula. It changes the covariance to:

\[
(\,-H + \lambda I\,)^{-1}.
\]

This is a deliberate numerical regularization.

Status: `confirmed as implementation-only stabilization`

Impact:
- improves invertibility and supervisor robustness,
- but shrinks the resulting covariance relative to the exact Laplace covariance,
- therefore can bias Delta expectations and downstream entropy terms slightly.

### 3.4 `Hess.LD` is misnamed

The returned object uses the field:

```r
Hess.LD = LD_S
```

Code anchor:
- `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r` lines 2472 and 4293/4508

But `LD_S` is the covariance matrix, not the Hessian.

This is confirmed again later because downstream code samples with:

```r
rmvnorm(..., sigma = gamsig.dummy$Hess.LD)
```

Code anchors:
- `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r` lines 4293-4299
- `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r` lines 4508-4514

Status: `confirmed naming mismatch`

Impact:
- not a mathematical error by itself,
- but a real clarity hazard in future audits and maintenance.

### 3.5 Guard fallback path is not a true Laplace object

When optimization fails or the Hessian is unusable, `build_mode_result()` returns:
- point estimates from the seed or fallback,
- a diagonal matrix built from `var.sig` and `var.gam`,
- `entrop = 0`.

Code anchors:
- `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r` lines 1913-1951

This is not a Laplace approximation in the manuscript sense.

Status: `confirmed implementation fallback`

Impact:
- good for robustness,
- but it should not be interpreted as a theoretically faithful Laplace posterior block.

## 4. Delta-method expectation audit

### 4.1 Current helper

The current code uses:

```r
Expected_f <- function(f, theta_s, theta_g){
  x <- hessian(func = f, x = LD_mu) %*% LD_S
  e <- f(LD_mu) + 0.5 * sum(diag(x))
  return(e)
}
```

Code anchor:
- `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r` lines 2343-2346

This is exactly the second-order Delta method:

\[
g(\hat \mu) + \frac12 \operatorname{tr}(H_g(\hat \mu)\Sigma).
\]

Status: `confirmed`

### 4.2 Returned functions

The returned expectations match the manuscript-required function family:

- `1 / sigma`
- `1 / (sigma B)`
- `A / (sigma B)`
- `A^2 / (sigma B)`
- `C |gamma| / B`
- `A C |gamma| / B`
- `sigma C^2 gamma^2 / B`
- `log(sigma B)`
- `log(sigma)`

Code anchors:
- `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r` lines 2349-2464

These line up with:
- `main.tex` lines 1194-1208

Status: `confirmed`

### 4.3 Exact moments that are not used exactly

The manuscript explicitly notes that for `u`-only exponentials:

\[
\mathbb E[e^{a u}] = \exp(a\hat u + \tfrac12 a^2 \Sigma_{uu})
\]

exactly under the Gaussian marginal of `u`.

Theory anchor:
- `main.tex` lines 1187-1191

The current code does **not** exploit that exact formula for:
- `E.sigma = E[e^u]`
- `E.inv.sigma = E[e^{-u}]`

Instead it applies the generic second-order Delta method.

Code anchors:
- `f.sig`: lines 2429-2433
- `f.inv.sig`: lines 2383-2387
- evaluations: lines 2445 and 2449

Status: `confirmed approximation gap`

Impact:
- this is not catastrophic,
- but it is a real avoidable approximation because exact formulas are available here.

### 4.4 Expectations that are exact under the current helper

Some functions are linear in `u`, so the second-order Delta helper is exact automatically:

- `E.log.sig`

because `log(sig) = u` and the Hessian of that map is zero.

Code anchors:
- `f.log.sig`: lines 2357-2363
- evaluation: line 2457

Status: `confirmed`

### 4.5 Entropy accounting

The manuscript implies:

\[
H(q_{u,\xi}) = \frac12 \log\!\big((2\pi e)^2 \det \Sigma\big)
= \log(2\pi e) + \frac12 \log \det \Sigma
\]

for the 2D Gaussian approximation, and the induced entropy in `(sigma, gamma)` coordinates adds
`E[log J]`.

The current code computes:

```r
entrop <- log(2*pi*exp(1)) +
  0.5 * log(det(LD_S)) +
  E.log.jac
```

implemented as:

```r
log(2*pi*exp(1)) + 0.5*determinant(as.matrix(LD_S), logarithm = TRUE)$modulus[1] + E.log.jac
```

Code anchor:
- `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r` line 2466

This is mathematically correct for the transformed density.

Status: `confirmed`

### 4.6 Namespace fragility in `Expected_f`

The current code explicitly uses `numDeriv::hessian` for the log objective Hessian at the mode, but
inside `Expected_f` it uses bare `hessian(...)` without the namespace.

Code anchors:
- explicit: line 2315
- bare call: line 2344

The package list includes `numDeriv`, so this works when the package is attached, but it is still a
namespace fragility.

Status: `confirmed implementation fragility`

Impact:
- not a mathematical mismatch,
- but a real robustness risk if the calling environment changes.

## 5. Active-path versus stale duplicate-path note

The active implementation in `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r` now uses:
- logistic gamma transform
- corrected Jacobian
- corrected entropy sign

But the legacy duplicate in:
- `R/environmetrics/20_model_setup.R`

still shows:
- the old double-exponential map,
- the old Jacobian form,
- the old entropy formula.

This duplicate path is not the active current launch path, but it should not be treated as current
theory-compatible code.

Status: `confirmed stale duplicate path`

## 6. Confirmed items

### Confirmed L1
The active mode-finding step is maximizing the correct transformed objective.

### Confirmed L2
The active covariance formula is correct in the no-ridge case:

\[
\Sigma = (-H)^{-1}.
\]

### Confirmed L3
The active Delta helper implements the manuscript second-order Delta method.

### Confirmed L4
The active entropy formula is correct for the transformed density.

## 7. Confirmed discrepancies or caveats

### Caveat C1
The manuscript recommends split optimization across `gamma < 0` and `gamma > 0` near zero; the
current code does not do that.

### Caveat C2
Exact `u`-only moments are available from the manuscript but are not used exactly in code.

### Caveat C3
Ridge regularization modifies the pure Laplace covariance.

### Caveat C4
`Hess.LD` is actually a covariance matrix, not a Hessian.

### Caveat C5
Fallback returns are robustness objects, not true Laplace posterior blocks.

### Caveat C6
`Expected_f` relies on an attached `hessian()` function rather than `numDeriv::hessian`.

## 8. Stage 5 conclusion

The best overall read is:

- the active transformed objective is mathematically correct,
- the active Hessian-to-covariance step is mathematically aligned with the manuscript,
- the active Delta-method layer is broadly correct,
- the main remaining risks are not the formula itself but:
  - near-zero `gamma` optimization policy,
  - exact-vs-approximate moment handling for `u`-only functions,
  - numerical regularization and fallback behavior,
  - stale duplicate code paths.

So the next optimal step is not another broad theory search.

The next optimal step is:

1. audit the exact returned expectation list one by one for avoidable approximation,
2. decide whether to implement manuscript-consistent split optimization near `gamma = 0`,
3. then compare those conclusions against run behavior.
