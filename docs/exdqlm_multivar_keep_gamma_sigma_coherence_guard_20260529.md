# exDQLM Multivar Keep Gamma/Sigma Coherence Guard - 2026-05-29

## Scope

This document records the follow-up implementation from the 2026-05-29 latent diagnostic ladder. It closes the
immediate q20 fit-failure mechanism identified in
[`exdqlm_multivar_keep_latent_diag_overnight_results_20260529.md`](exdqlm_multivar_keep_latent_diag_overnight_results_20260529.md)
without changing, stopping, or relaunching production campaigns.

The patch targets the active multivariate `exdqlm keep` path:

- [`DISC_Optimal_Synth_Ranges_W_transfer_forecast.r`](/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_Optimal_Synth_Ranges_W_transfer_forecast.r)
- [`R/disc_w/10_gamsig_laplace.R`](/data/muscat_data/jaguir26/project1_ucsc_phd/R/disc_w/10_gamsig_laplace.R)
- [`R/unified/config.R`](/data/muscat_data/jaguir26/project1_ucsc_phd/R/unified/config.R)
- [`R/unified/stages/stage_fit.R`](/data/muscat_data/jaguir26/project1_ucsc_phd/R/unified/stages/stage_fit.R)

## Root Evidence

The diagnostic ladder showed two repeated q20 fit-stage failures:

| cutoff/spec | failure iteration | immediate failure |
| --- | ---: | --- |
| `20220511 c02_eps090 q20` | 32 | historical `FFF` max about `22417.9`; historical `E[u_t]` about `1.0096e6` |
| `20221225 c03_eps060 q20` | 47 | historical `FFF` about `22518.8`; forecast `FFF` about `14700.7`; `E[u_t]` about `1.0e6` |

The decisive additional evidence is that the accepted gamma/sigma source-block update immediately before each failure
contained impossible second-order moments. For example:

| row | accepted `E[gamma]` | accepted `E[sigma]` | accepted `E[a^2/(b sigma)]` | accepted `E[1/sigma]` | implied `u.psi` floor |
| --- | ---: | ---: | ---: | ---: | ---: |
| `20220511 c02_eps090 q20` | `0.4124059451` | `0.0591065683` | `-148.186240` | `16.99359` | `-114.19906` |
| `20221225 c03_eps060 q20` | `0.32779368` | `0.05965007` | `-108.90929` | `16.82423` | `-75.26083` |

The theory contract rules this out:

- `a(gamma)^2 / (b(gamma) sigma)` is non-negative pointwise when `sigma > 0` and `b(gamma) > 0`.
- `c(gamma)^2 |gamma|^2 sigma / b(gamma)` is also non-negative pointwise.
- the GIG latent update uses `u.psi = E[a^2/(b sigma)] + 2 E[1/sigma]`, so accepting a negative value large enough to
  make this non-positive forces the later latent update into the clamp-to-floor branch.

So the immediate root is not simply that `update_uts()` needed stronger clipping. The latent explosion is downstream of
an incoherent gamma/sigma moment package being committed.

## Implemented Guard

### Reusable Moment Validator

[`R/disc_w/10_gamsig_laplace.R`](/data/muscat_data/jaguir26/project1_ucsc_phd/R/disc_w/10_gamsig_laplace.R)
now provides:

- `disc_w_validate_gamsig_moments(...)`
- `disc_w_gamsig_moments_are_coherent(...)`

The validator checks:

| check | reason |
| --- | --- |
| required moment fields exist and are finite | avoids partially populated commits |
| `E[sigma]`, `E[1/sigma]`, and `E[1/(b sigma)]` are positive | required by the pseudo-data and latent formulas |
| `E[a^2/(b sigma)]` and `E[c^2 |gamma|^2 sigma / b]` are not materially negative | pointwise non-negative theory moments |
| `E[a^2/(b sigma)] + 2 E[1/sigma] > min_uts_psi` | prevents an accepted source update from guaranteeing invalid `u.psi` |
| `E[gamma]` is inside the open support when support bounds are supplied | keeps transformed gamma away from impossible boundary states |
| `Sigma.LD` is symmetric positive semidefinite when present | keeps the Laplace covariance contract explicit |

Zeros are still allowed for non-negative theory moments. This matters for median-like cases where `a(gamma)` or
`gamma` can make a squared term exactly zero.

### Transactional Source Commit

[`DISC_Optimal_Synth_Ranges_W_transfer_forecast.r`](/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_Optimal_Synth_Ranges_W_transfer_forecast.r)
now treats gamma/sigma source-block updates transactionally:

1. build a candidate with `update_gamma_sigma(...)`;
2. validate the full moment package;
3. reject candidates that are incoherent or already guard-triggered;
4. roll back to the previous source-block gamma/sigma state;
5. repair the rollback moments from the previous point `gamma/sigma` values if the stored previous moment package is
   itself incoherent;
6. commit all gamma/sigma fields through one helper rather than scattered manual assignments.

New helper functions in the active runner:

- `disc_w_gamsig_source_snapshot(...)`
- `disc_w_prepare_gamsig_for_commit(...)`
- `disc_w_assign_gamsig_source(...)`

The VB fit loop and the sampling-stage gamma/sigma updates both use the transactional path.

### Latent Guard Logging

`update_uts(...)` still clamps non-positive or non-finite `psi/chi` to the historical numerical floor, but it now logs
`[latent_parameter_guard]` before doing so. That makes a future invalid latent update observable instead of silently
absorbing it.

### Config Knobs

The unified config now exposes the guard under:

```yaml
fit:
  exdqlm_multivar:
    gamma_sigma:
      coherence_guard:
        enabled: true
        rollback_on_guard: true
        min_uts_psi: 1.0e-8
        nonnegative_tol: 1.0e-10
```

The same default block is available for the univariate exDQLM family for config consistency. `stage_fit` exports these
values as:

- `DISC_GAMSIG_COHERENCE_GUARD_ENABLED`
- `DISC_GAMSIG_COHERENCE_ROLLBACK_ON_GUARD`
- `DISC_GAMSIG_COHERENCE_MIN_UTS_PSI`
- `DISC_GAMSIG_COHERENCE_NONNEGATIVE_TOL`

The active runner logs the selected policy with `[gamsig_coherence_policy]`.

### ELBO Accounting Correction

The ELBO contribution now reads the actual returned fields:

- `new.sts.out$tot.entrop`
- `new.gamsig.out$entrop`

The old names, `new.sts.out$E.tot.entrop` and `new.gamsig.out$E.sig.gam.entrop`, were not valid fields in the active
objects. This is a diagnostic/accounting fix, not the primary q20 pseudo-data root cause.

## Why This Is A Root-Cause Patch

The bad failure chain was:

1. gamma/sigma approximation produced a moment package with an impossible negative squared-term expectation;
2. the fit loop committed it because the previous finiteness guard did not check theory coherence;
3. the next `u_t` update saw non-positive `u.psi`;
4. `update_uts()` clamped `u.psi` to the numerical floor;
5. `E[u_t]` jumped to about `1e6`;
6. gamma/sigma and pseudo-data terms propagated the instability into `FFF`;
7. the pseudo-data guard stopped the fit.

This patch prevents step 2. It does not merely raise caps or hide the pseudo-data guard.

## Tests Added Or Extended

| test file | coverage |
| --- | --- |
| [`tests/testthat/test_disc_w_gamsig_laplace.R`](/data/muscat_data/jaguir26/project1_ucsc_phd/tests/testthat/test_disc_w_gamsig_laplace.R) | rejects the exact impossible negative moment pattern from the failed q20 lane; rejects invalid implied `u.psi`; permits valid zero squared moments; confirms active runner exposes rollback policy |
| [`tests/testthat/test_config_mode_resolution.R`](/data/muscat_data/jaguir26/project1_ucsc_phd/tests/testthat/test_config_mode_resolution.R) | checks default coherence guard config and validation errors for invalid guard values |
| [`tests/testthat/test_exdqlm_multivar_keep_latent_pseudodata_audit.R`](/data/muscat_data/jaguir26/project1_ucsc_phd/tests/testthat/test_exdqlm_multivar_keep_latent_pseudodata_audit.R) | confirms the stale ELBO field names are absent and the active names are present |

Commands run:

```bash
git diff --check
Rscript --vanilla -e 'invisible(parse("R/disc_w/10_gamsig_laplace.R")); invisible(parse("DISC_Optimal_Synth_Ranges_W_transfer_forecast.r")); invisible(parse("R/unified/config.R")); invisible(parse("R/unified/stages/stage_fit.R")); cat("parse_ok\n")'
Rscript --vanilla -e 'library(testthat); test_file("tests/testthat/test_disc_w_gamsig_laplace.R")'
Rscript --vanilla -e 'library(testthat); test_file("tests/testthat/test_config_mode_resolution.R")'
Rscript --vanilla -e 'library(testthat); test_file("tests/testthat/test_exdqlm_multivar_keep_latent_pseudodata_audit.R")'
```

Results:

| check | result |
| --- | --- |
| diff whitespace | pass |
| R parse | pass |
| gamma/sigma validator tests | pass, 73 expectations |
| unified config tests | pass, 82 expectations |
| latent/pseudo-data audit tests | pass, 75 expectations |

## Required Runtime Validation Before Relaunch

This patch is theory-grounded and unit-tested, but it still needs a minimal runtime ladder before any new full grid or
production relaunch:

| stage | rows | expected result |
| --- | --- | --- |
| smoke parse/config | no model fit | all active configs parse and export coherence guard env vars |
| failed-lane reproduction | `20220511 c02_eps090 q20`, `20221225 c03_eps060 q20` | no committed negative theory moment; no `u.psi` floor cascade; either pass or fail with a different explicit reason |
| matched controls | `20211112 c02_eps090 q20`, `20211112 c03_eps060 q20` | remain healthy; CRPS/trace behavior not degraded materially |
| focused multi-quantile row | one affected cutoff/spec with all seven quantiles | post-stage synthesis and diagnostics still complete |
| only then | selected grid/production launch | proceed using normal monitor/report cleanup |

Failure of an aggressive discount/epsilon row after this patch is acceptable if the new failure is a transparent model
specification failure. What should not recur is an accepted negative squared-term gamma/sigma moment followed by silent
latent-floor amplification.

## Remaining Work

| priority | item | reason |
| ---: | --- | --- |
| 1 | run the minimal q20 ladder under this patch | proves the root failure no longer reproduces |
| 2 | inspect `[gamsig_rollback]` and `[latent_parameter_guard]` counts in the ladder | distinguishes healthy rollback from frequent instability |
| 3 | compare CRPS and trace summaries for matched controls | ensures the guard is not over-constraining healthy lanes |
| 4 | keep pseudo-data guards active in hard-fail or report mode during validation | prevents masked failures |
| 5 | revisit Laplace/delta moment calculation if rollback fires too often | high rollback frequency would mean the approximation itself still needs stronger local treatment |
