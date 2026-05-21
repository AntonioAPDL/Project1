# exDQLM Multivariate Keep Latent `s_t` / `u_t` Audit

Date: 2026-05-20

## Scope

This document re-derives the active latent updates used by the multivariate
`exdqlm keep` workflow and maps them to current code. It covers:

- the positive-truncated normal update for `s_t`,
- the GIG update for `u_t`/`v_t`,
- moment formulas consumed downstream,
- entropy formulas,
- historical and forecast-member update loops,
- focused executable tests.

The deterministic audit helper is
[R/disc_w/11_latent_pseudodata_audit_helpers.R](/data/muscat_data/jaguir26/project1_ucsc_phd/R/disc_w/11_latent_pseudodata_audit_helpers.R).
It is not sourced by the production runner.

Focused tests are in
[tests/testthat/test_exdqlm_multivar_keep_latent_pseudodata_audit.R](/data/muscat_data/jaguir26/project1_ucsc_phd/tests/testthat/test_exdqlm_multivar_keep_latent_pseudodata_audit.R).

Verification run:

```text
Rscript --vanilla -e "testthat::test_file('tests/testthat/test_exdqlm_multivar_keep_latent_pseudodata_audit.R')"
PASS: 27 expectations, 0 failures
```

## Theory: Augmented Observation

For a scalar observation with linear predictor `eta_n`, the manuscript
augmentation is:

\[
y_n \mid \eta_n,\sigma,\gamma,v_n,s_n
\sim
N(\eta_n + C\sigma|\gamma|s_n + A v_n,\sigma B v_n),
\]

\[
v_n\mid\sigma\sim \operatorname{Exp}(1/\sigma),
\qquad
s_n\sim N^+(0,1).
\]

Canonical anchors: `main.tex:241-253`.

## `s_t` Conditional Derivation

Define:

\[
y^\circ = y-\eta-Av,\qquad d=C\sigma|\gamma|,\qquad R=\sigma Bv.
\]

The terms in `s` are:

\[
-\frac{1}{2R}(y^\circ-ds)^2-\frac{1}{2}s^2.
\]

Completing the square:

\[
V_s=\left(1+\frac{d^2}{R}\right)^{-1}
=\left(1+\frac{C^2\sigma\gamma^2}{Bv}\right)^{-1},
\]

\[
m_s=V_s\frac{d y^\circ}{R}
=V_s\frac{C|\gamma|}{Bv}(y-\eta-Av).
\]

Thus:

\[
s\mid\text{rest}\sim N^+(m_s,V_s).
\]

Canonical anchors: `main.tex:344-360`.

## `s_t` Implementation Map

Active function:
`DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:1795-1815`.

Code-to-theory map:

| Theory quantity | Active code | Lines |
|---|---|---:|
| \(1/v\) | `inv.uts` | `1802` |
| \(V_s\) | `s.sig2 <- 1 / (1 + c2.invb.absgam2.sigma * inv.uts)` | `1803-1804` |
| \(m_s\) | `s.mu <- s.sig2*(c.invb.absgam*(y-exps)*inv.uts-c.a.invb.absgam)` | `1805` |
| \(E[s]\) | `truncnorm::etruncnorm(...)` | `1807` |
| \(E[s^2]\) | explicit second moment formula | `1808-1811` |
| entropy | `sum(0.5*log2(2*pi*exp(1)*s.sig2) - 1)` | `1812-1814` |

Why the `m_s` expression matches theory:

\[
\frac{C|\gamma|}{Bv}(y-\eta-Av)
=
\frac{C|\gamma|}{B}(y-\eta)\frac{1}{v}
-
\frac{AC|\gamma|}{B}.
\]

The code stores those expected coefficient terms as
`c.invb.absgam` and `c.a.invb.absgam`.

## `s_t` Moment Verification

For `S ~ N(mu, sig2)` truncated to `S > 0`, let `z = mu/sig` and
\[
\lambda_z=\phi(z)/\Phi(z).
\]

Then:

\[
E[S]=\mu+\sigma\lambda_z,
\]

\[
\operatorname{Var}(S)=\sigma^2(1-z\lambda_z-\lambda_z^2),
\]

\[
E[S^2]=\operatorname{Var}(S)+E[S]^2
=\mu^2+\sigma^2+\mu\sigma\lambda_z.
\]

The focused test numerically integrates the truncated normal density and checks
`E.sts` and `E.sts2` from the active formula against the integrals. This test
passes.

Status:

- `sts.mu`: confirmed.
- `sts.sig2`: confirmed.
- `E[s_t]`: confirmed by deterministic test.
- `E[s_t^2]`: confirmed by deterministic test.
- positivity/truncation: confirmed at moment level because `E[s_t] >= 0` is
  tested and the active formula uses lower truncation at 0.

## `s_t` Entropy Finding

Canonical entropy for `N(mu, sig2)` truncated to `S > 0` is:

\[
h(S)=\frac12\log(2\pi e\sigma^2)+\log\Phi(z)-\frac12 z\frac{\phi(z)}{\Phi(z)}.
\]

The active code instead uses:

\[
\sum_t \left(\frac12\log_2(2\pi e\,V_{s,t}) - 1\right).
\]

Active anchor: `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:1812-1814`.

This differs from the canonical entropy in three ways:

1. it uses base-2 logs while the ELBO uses natural logs elsewhere,
2. it omits the truncation normalization term `log Phi(z)`,
3. it omits the truncation correction `-0.5 z phi(z)/Phi(z)`.

The focused test asserts that the active entropy formula is numerically different
from the canonical truncated-normal entropy for a nontrivial deterministic
fixture. This is a confirmed mismatch, but its likely effect is ELBO accounting
rather than direct state instability because `tot.entrop` is not used in the
state update itself.

Status: `wrong for canonical entropy; likely secondary for state dynamics`.

## `u_t` / `v_t` Conditional Derivation

Using:

\[
r = y-\eta-C\sigma|\gamma|s,
\]

the manuscript gives:

\[
v\mid\text{rest}\sim
\operatorname{GIG}
\left(
\lambda=\frac12,
\chi=\frac{r^2}{\sigma B},
\psi=\frac{A^2}{\sigma B}+\frac{2}{\sigma}
\right),
\]

with density:

\[
f(v)\propto v^{\lambda-1}\exp\left[-\frac12(\chi/v+\psi v)\right]\mathbf 1(v>0).
\]

Canonical anchors: `main.tex:323-342`.

In the VB update, the residual-square expectation expands as:

\[
\chi =
E\left[\frac{(y-\eta)^2}{\sigma B}\right]
-2E\left[\frac{C|\gamma|}{B}\right]E[s](y-E[\eta])
+E\left[\frac{\sigma C^2\gamma^2}{B}\right]E[s^2].
\]

The implementation uses `exps = E[eta]` and `exps2 = E[eta^2]`.

## `u_t` Implementation Map

Active function:
`DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:1833-1879`.

| Theory quantity | Active code | Lines |
|---|---|---:|
| \(\lambda\) | `u.lambda = 0.5` | `1834` |
| \(\psi\) | `a2.invb.inv.sigma + 2*inv.sigma` | `1835` |
| \(\chi\) | expanded expected residual square | `1836` |
| positivity guard | replace nonfinite/nonpositive `psi`/`chi` with `1e-6` | `1838-1839` |
| \(E[u]\) | `sqrt(chi/psi) * K_{lambda+1}/K_lambda` | `1853-1857` |
| \(E[1/u]\) | recurrence from `K_{lambda+1}/K_lambda` | `1856-1857` |
| \(E[\log u]\) | derivative of log Bessel term plus `0.5 log(chi/psi)` | `1863-1870` |
| entropy | `gig_entrop(u.psi,u.chi)` | `1871-1878` |

Moment identities used by the test:

\[
E[V^r]=
\left(\frac{\chi}{\psi}\right)^{r/2}
\frac{K_{\lambda+r}(\sqrt{\chi\psi})}{K_\lambda(\sqrt{\chi\psi})}.
\]

The focused test checks `E.uts` and `E.inv.uts` against this identity and checks
the summed `E.log.uts` against numerical integration. This test passes.

Status:

- family and parameterization: confirmed.
- `lambda`, `psi`, `chi`: confirmed structurally.
- `E[u_t]`: confirmed by deterministic test.
- `E[1/u_t]`: confirmed by deterministic test.
- `E[log u_t]`: confirmed by deterministic test for the active summed output.
- entropy: formula is structurally consistent with the active GIG parameterization,
  but a separate entropy integration fixture remains desirable.

## Historical and Forecast Update Loops

Historical latent updates:

- `s_t`: `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:3901-3909`
- `u_t`: `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:3911-3924`

Forecast-member latent updates inside the fit loop:

- `s_t`: `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:3986-3996`
- `u_t`: `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:3999-4009`

Forecast-member latent updates in the later sampling/pre-finalization block:

- `s_t`: `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:4660-4677`
- `u_t`: `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:4688-4709`

The same `update_sts(...)` and `update_uts(...)` functions are used for
history and forecast members. The intended difference is indexing:

- history uses `y[j, 1:TT_sub]` and `new.theta.out$exps[j, 1:TT_sub]`;
- forecast uses `ensembles[[j-1]][, i]` and the forecast slice of
  `new.theta.out$exps[j, ...]`.

Audit finding: at audit time, the forecast-member `u_t` update used bare `T`
instead of `TT_sub` in two forecast-slice expressions. This was inconsistent
with the adjacent `s_t` update and unsafe because `T` is a predefined alias for
`TRUE` in R unless explicitly assigned in scope. The active runner is now
patched so the fit-stage `u_t` forecast update uses `TT_sub` at
`DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:4001-4002`, and the
sampling-stage update uses `TT_sub` at
`DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:4694-4695`.

The focused test suite now includes a static regression check that no
forecast-member `new.theta.out$exps[j,(T+1):(T+k_forecast)]` or `exps2`
references remain.

Status: same update functions are used in both stages; the confirmed
fit/sampling forecast-index bug is fixed locally, but existing saved runtime
outputs still reflect the pre-fix code.

## Stability Propagation

The latent updates feed pseudo-data as:

\[
QQQ_n = \frac{1}{E[1/(\sigma B)]E[1/u_n]},
\]

\[
FFF_n =
\frac{E[C|\gamma|/B]E[s_n] + E[A/(\sigma B)]/E[1/u_n]}
{E[1/(\sigma B)]}.
\]

Therefore:

- very small `E[1/u]` inflates `QQQ` and can create weak observations;
- very large `E[1/u]` shrinks `QQQ` and can create overconfident pseudo-data;
- large `E[s]` or unstable `gamma` expectations move `FFF`, changing the
  innovation `y - (H a + FFF)`;
- bad `sigma/gamma` expectations can affect both latent updates and pseudo-data
  in the same iteration.

This is the main interaction channel between H1/H2 and H3.

## Verdict

| Component | Status | Evidence |
|---|---|---|
| `s_t` conditional parameters | confirmed | theory derivation plus active code lines `1795-1805` |
| `s_t` first/second moments | confirmed | deterministic integration test passes |
| `s_t` entropy | wrong vs canonical | active code lines `1812-1814`; deterministic mismatch test |
| `u_t` GIG family | confirmed | `main.tex:323-342`; active code lines `1833-1839` |
| `u_t` moments | confirmed | Bessel identity and numerical integration tests pass |
| forecast `u_t` indexing | wrong at audit time; fixed locally | active code now uses `TT_sub` at lines `4001-4002` and `4694-4695`; static regression test |
| history vs forecast formula consistency | confirmed after index fix | shared functions in both loops |
| latent update as primary state-instability source | interactional | runtime traces show latent and pseudo-data extremes in suspect lanes |

## Fix Priority From This Phase

1. `P0`: run narrow post-fix q05/q35/q50/q95 reproductions to measure how much
   the forecast `u_t` index correction changes `E[u]`, `E[1/u]`, forecast
   pseudo-data, and state norms.
2. `P1`: correct the `s_t` entropy contribution or remove it from any decision
   logic that assumes a canonical ELBO. This is a confirmed formula mismatch.
3. `P1`: add runtime logging/extraction for `E[s]`, `E[s^2]`, `E[u]`,
   `E[1/u]`, and `E[log u]` by source and lane; this is necessary to decide
   whether the latent layer is dynamically unstable.
4. `P2`: add an entropy integration test for the GIG helper if entropy is used
   for model comparison or convergence interpretation.
