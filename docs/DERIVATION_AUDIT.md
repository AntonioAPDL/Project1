# QDESN / exDQLM Derivation Audit

Date: 2026-02-07

## Scope and interpretation
- No literal `QDESN` symbol/string appears in this repository.
- The active math/code stack is the exAL-based exDQLM/NDLM workflow in `article.txt` and `R/environmetrics/20_model_setup.R`.
- This audit treats that stack as the requested QDESN target and checks univariate and multivariate consistency, including the dimension-1 reduction property.

## Source map used in this audit
- Derivation source: `article.txt`
- Core distribution helpers: `R/environmetrics/02_helpers_core.R`
- VB-Laplace-Delta update code: `R/environmetrics/20_model_setup.R`
- Audit math helpers: `R/environmetrics/qdesn_validation_math.R`
- Automated checks:
  - `tests/testthat/test_qdesn_derivation_consistency.R`
  - `scripts/validate/run_qdesn_checks.R`

## Symbol and shape dictionary

### Indexing and horizons
| Symbol | Meaning | Domain | Univariate | Multivariate |
|---|---|---|---|---|
| `t` | Time index | `1..T` (history), `T+1..T+K_(1)` (forecast) | scalar index | scalar index |
| `j` | Source index (`0`=USGS, `1..J` retros/forecasters) | `0..J` | scalar index | scalar index |
| `i` | Ensemble member index | `1..I_j` | scalar index | scalar index |
| `k` | Forecast lead index | `1..K_(j)` | scalar index | scalar index |

### State-space objects
| Symbol | Meaning | Domain/support | Univariate shape | Multivariate shape | Where introduced |
|---|---|---|---|---|---|
| `y_t^o` | Observed flow | `R` | scalar | scalar | `article.txt:116` |
| `z_t^j` | Retrospective signal for source `j` | `R` | scalar | scalar | `article.txt:133` |
| `F_t` | Observation vector for trend/seasonal state | `R^p` | `p x 1` | `p x 1` | `article.txt:121` |
| `G_t` | State evolution matrix | `R^{p x p}` | `p x p` | `p x p` | `article.txt:117` |
| `theta_t` | Trend/seasonal latent state | `R^p` | `p x 1` | `p x 1` | `article.txt:117` |
| `delta_t^j` | Discrepancy state (source `j`) | `R^p` | `p x 1` | `p x 1` per `j` | `article.txt:133`, `article.txt:147` |
| `alpha_t` | Model-A stacked state `[theta_t; zeta_t; psi_t]` | `R^{p+1+m}` | `(p+1+m) x 1` | same | `article.txt:127` |
| `mu_t` | Model-B stacked state `[theta_t; delta_t; zeta_t; psi_t]` | `R^{p + pJ + 1 + m}` | `(p+pJ+1+m) x 1` | same | `article.txt:146` |
| `beta_t` | Forecast-period stacked state `[theta_t; delta_t^f]` | `R^{p + d_t}` | `(p+d_t) x 1` | same | `article.txt:170` |

### exAL/non-conjugate parameters and augmentations
| Symbol | Meaning | Support | Univariate shape | Multivariate shape | Code alignment |
|---|---|---|---|---|---|
| `sigma^j` | Scale parameter for source `j` | `sigma^j > 0` | scalar | length `J+1` vector | `R/environmetrics/20_model_setup.R:612` |
| `gamma^j` | Skewness parameter for source `j` | `gamma^j in (L, U)` | scalar | length `J+1` vector | `R/environmetrics/20_model_setup.R:612` |
| `v_t^j` (`u_t` in code) | GIG latent variable | `v_t^j > 0` | scalar per `(j,t)` | vector over `j` at fixed `t` | `R/environmetrics/20_model_setup.R:374` |
| `s_t^j` | Truncated-normal latent variable | `s_t^j > 0` | scalar per `(j,t)` | vector over `j` at fixed `t` | `R/environmetrics/20_model_setup.R:346` |
| `A(gamma), B(gamma), C(gamma)` | exAL coefficient transforms | deterministic in `gamma,p0` | scalar | elementwise vector | `R/environmetrics/02_helpers_core.R:62` |

## Consistency findings

### F1 (fixed): discrepancy-state dimension typo in manuscript
- Issue: text stated `delta_t^j in R^J` while equations use `F_t' delta_t^j`, requiring `delta_t^j in R^p`.
- Evidence: `article.txt:133` and matrix definition around `article.txt:147`.
- Resolution: corrected to `R^p` in `article.txt`.

### F2 (no code mismatch): VB-LD transformed objective and Jacobian are internally consistent
- Evidence: transformed variables and Jacobian term in `R/environmetrics/20_model_setup.R:420` and `R/environmetrics/20_model_setup.R:437`.
- Check added: finite-difference stability test on the same transformed objective.

### F3 (no code mismatch): univariate and multivariate expressions agree at dimension 1
- Evidence: dimension-1 reduction checks added for observation mean and scale diagonal, plus latent-`chi` update term.

## Computable implementation forms

### 1. Observation location block
Implementation form (vectorized over sources at fixed time `t`):

```text
Inputs:
- H_t: n_state x (J+1)
- alpha_t: n_state x 1
- sigma, gamma, s_t, v_t: length (J+1)

A <- A_fn(p0, gamma)          # elementwise
C <- C_fn(p0, gamma)          # elementwise
mu_t <- H_t' alpha_t + C * sigma * abs(gamma) * s_t + A * v_t
```

Numerical notes:
- Keep `gamma` away from boundaries via transformed parameterization used in code.
- Use elementwise vector operations; avoid per-source loops.

Complexity:
- `O(n_state * (J+1))` for `H_t' alpha_t`; `O(J)` for elementwise terms.

### 2. Latent `u_t` (`v_t`) update core (`chi` term)
Implementation form:

```text
Inputs (length n vectors): y, exps, exps2, sts, sts2,
invb_inv_sigma, c_invb_absgam, c2_invb_absgam2_sigma

chi <- invb_inv_sigma * (y^2 - 2*y*exps + exps2)
     - 2 * c_invb_absgam * sts * (y - exps)
     + c2_invb_absgam2_sigma * sts2
chi[chi <= 0] <- 1e-6
```

Numerical notes:
- The positive clamp (`1e-6`) is required before Bessel-ratio calls.
- Keep this clamp in place to prevent invalid `sqrt`/division operations.

Complexity:
- `O(n)`.

### 3. Non-conjugate `(sigma, gamma)` VB-LD block
Implementation form:

```text
(theta_s, theta_g) -> (sigma, gamma)
sigma = exp(theta_s)
gamma = LL + (UU - LL) * exp(-exp(theta_g))

maximize transformed objective dq_transf(theta_s, theta_g)
via L-BFGS-B on unconstrained theta-space

Laplace covariance:
S = - (Hessian dq_transf at mode)^(-1)

Delta expectations:
E[g(theta)] ~= g(theta_hat) + 0.5 * tr(H_g(theta_hat) * S)
```

Numerical notes:
- The double-exponential map keeps `gamma` strictly interior to `(L,U)`.
- Use stable linear solves for Hessian inversion; fail fast on non-invertible Hessian.

Complexity:
- Dominated by objective/Hessian evaluations inside optimization.

## Automated check results (this branch)
- `testthat`: `tests/testthat/test_qdesn_derivation_consistency.R` -> PASS
- Scripted validator: `scripts/validate/run_qdesn_checks.R` -> PASS
- Machine-readable summary: `logs/validation/qdesn_checks.tsv`

## Notes on model-definition preservation
- No model assumptions or likelihood definitions were changed.
- Audit fixes are documentation-level consistency corrections and new validation checks only.
