# Discrepancy Resolution Notes (D1/D2/D3–D5)

This file records what was changed (and why) to resolve the audit discrepancies in
`discrepancy_report.md` without running the full pipeline.

---

## D2 — `sample_truncnorm` exported-name collision (resolved)

### What was happening (pre-fix)

The runner compiles two translation units in sequence:
- `DISC_Optimal_Synth_Ranges_W.r:52` → `Rcpp::sourceCpp("sampling_exal.cpp")`
- `DISC_Optimal_Synth_Ranges_W.r:53` → `Rcpp::sourceCpp("sampling_truncnorm.cpp")`

Both previously exported **the same R name** `sample_truncnorm(...)`. Evidence from the generated
`sourceCpp` wrapper files shows the last compilation overwrote the R wrapper:

- After `sampling_exal.cpp`, the wrapper bound:
  - `sample_truncnorm <- ... 'sourceCpp_1_sample_truncnorm'`
- After `sampling_truncnorm.cpp`, the wrapper bound:
  - `sample_truncnorm <- ... 'sourceCpp_3_sample_truncnorm'`

(These strings appear in the temporary `*.cpp.R` wrapper files produced by `Rcpp::sourceCpp`.)

### Differences between implementations

- `sampling_exal.cpp` (rejection sampler):
  - Algorithm: Normal rejection sampling until `x >= 0` (lower truncation at 0).
  - RNG: Boost `mt19937`; previously **re-seeded inside the inner loop** using `omp_get_thread_num()`,
    which is fragile and can produce degenerate/repeated draws.
- `sampling_truncnorm.cpp` (inverse-CDF sampler):
  - Algorithm: draw `U ~ Unif(Phi(alpha), 1)`, return `mu + sd * Phi^{-1}(U)` with `alpha=(0-mu)/sd`.
  - RNG: Boost `mt19937`; previously seeded from wall-clock time + thread id (not reproducible under `set.seed()`).

Both interpret inputs as `(mean = sts_mu[t], variance = sts_sig2[t])` and truncate at 0.

### Fix applied

- Removed the collision by renaming the rejection sampler export:
  - `sampling_exal.cpp`: `sample_truncnorm(...)` → `sample_truncnorm_reject(...)`.
- Made the inverse-CDF sampler the explicit call target:
  - `sampling_truncnorm.cpp`: exported `sample_truncnorm_icdf(...)` (canonical),
    plus a backward-compatible alias `sample_truncnorm(...)` that calls `sample_truncnorm_icdf(...)`.
  - `DISC_Optimal_Synth_Ranges_W.r`: updated call sites to `sample_truncnorm_icdf(...)`.
- Improved reproducibility for *both* samplers:
  - Seed Boost RNGs from R’s RNG (`set.seed()` now controls results), using one seed per OpenMP thread.
  - Use `schedule(static)` to reduce scheduling-dependent variability.

### Micro-test evidence

Added: `repro/test_truncnorm_equivalence.R` (targeted; no model runs). It:
- compiles both samplers,
- checks reproducibility under `set.seed()` (with `OMP_NUM_THREADS=1`),
- compares sample mean/variance to truncated-normal theory on a small `(mu, sig2)` grid,
- reports rough runtime.

In a representative run (n=20,000 draws per grid point, `OMP_NUM_THREADS=1`):
- both samplers were reproducible under `set.seed()`,
- both matched theoretical moments within Monte Carlo error,
- `icdf` was substantially faster than `reject`.

Decision: **keep `sample_truncnorm_icdf` as the canonical implementation** for the runner.

---

## D1 — \u03b3 transform mismatch vs LaTeX (resolved)

### What was happening (pre-fix)

The LaTeX document parameterizes the Laplace approximation on \((u,\u03be)\in\mathbb{R}^2\) with
\[
u=\log\sigma,\qquad \gamma=L+(U-L)\,\pi(\u03be),\quad \pi(\u03be)=\frac{1}{1+e^{-\u03be}},
\]
and log-Jacobian \(\log|J| = u + \log(U-L) + \log \pi(\u03be) + \log(1-\pi(\u03be))\)
(`main.tex:eq:transform_u_xi`, `eq:jacobian_u_xi`).

In contrast, `update_gamma_sigma` in the runner used:
- \(\gamma = LL + (UU-LL)\exp(-\exp(\theta_g))\) with `LL=L+0.001`, `UU=U-0.001`,
- log-Jacobian contribution `theta_s + theta_g - exp(theta_g)` (plus constants),
which did not match the LaTeX mapping.

### Fix applied

In `DISC_Optimal_Synth_Ranges_W.r:update_gamma_sigma`:
- Replaced the \(\exp(-\exp)\) mapping with the LaTeX logistic mapping:
  \[
  \gamma = L+(U-L)\,\pi(\theta_g),\quad \pi=\mathrm{plogis}(\theta_g).
  \]
- Updated the log-Jacobian term in the transformed objective accordingly:
  \[
  u + \log(U-L) + \log \pi + \log(1-\pi).
  \]
  Implemented using `log(pi) + log1p(-pi)` for numerical stability.
- Removed `LL`/`UU` tightening; instead, clip \(\pi\) to \([10^{-12},1-10^{-12}]\) to ensure \(\gamma\in(L,U)\)
  strictly (avoids evaluating \(A,B,C\) at boundary values where they blow up).
- Updated the inverse transform used for initialization:
  `theta_g_init <- qlogis((g_init - L)/(U - L))` (with the same \(\pi\) clipping).
- Updated the \(\gamma\) transform used for Laplace draws (`samp.gamma <- ...`) to the new mapping.
