# NDLM Post-Correction Reaudit: Covariance and Dynamics Audit

Date: 2026-04-21  
Status: complete

## Scope

This note checks whether the worst multivariate NDLM rows are showing obvious covariance blow-up or PSD/stability failure in the forecast horizon.

## Runtime Evidence

- [20211221 ndlm_main_keep covariance diagnostics](</data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_ndlm_featurecov_rerun_20260420/runs/multimodel_20211221_v8_ndlm_featurecov_v1_ndlm_main_keep/diagnostics/ndlm/ndlm_covariance_diagnostics.csv>)
- [20221225 ndlm_main_keep covariance diagnostics](</data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_ndlm_featurecov_rerun_20260420/runs/multimodel_20221225_v8_ndlm_featurecov_v1_ndlm_main_keep/diagnostics/ndlm/ndlm_covariance_diagnostics.csv>)
- [20211221 ndlm_main_drop covariance diagnostics](</data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_ndlm_featurecov_rerun_20260420/runs/multimodel_20211221_v8_ndlm_featurecov_v1_ndlm_main_drop/diagnostics/ndlm/ndlm_covariance_diagnostics.csv>)

## Diagnostic Summary

The covariance diagnostics do not show the kind of instability that would explain forecast quantiles in the hundreds or thousands on the `log(1+Q)` scale.

Representative worst-row summaries:

| Run | Min diag minimum | Min eigenvalue minimum | Cholesky fail rate |
|---|---:|---:|---:|
| `20211221 / ndlm_main_keep` | `8.7382e-07` | `3.5276e-08` | `0` |
| `20221225 / ndlm_main_keep` | `1.1119e-06` | `3.7688e-08` | `0` |
| `20211221 / ndlm_main_drop` | `8.7314e-07` | `3.5251e-08` | `0` |

Across the diagnostic slices:

- `nonfinite_slices = 0`
- `asymmetry_max = 0`
- `base_chol_fail_slices = 0`

So the saved multivariate covariance objects are:

- finite
- symmetric
- positive semidefinite to tolerance
- numerically stable enough for the hardening checks

## Interpretation

This does **not** prove the forecast covariance dynamics are optimal. It does, however, rule out the simplest “the covariance matrix exploded” explanation for the catastrophic multivariate NDLM CRPS values.

Instead, the evidence points to a narrower issue:

- the covariance/state path is numerically coherent
- but the predictive sampler was applying the wrong sigma stream to the USGS target series

That is exactly the pattern seen in the numeric replay:

- stable covariance diagnostics
- raw forecast drivers with upper quantiles near `~1`
- scored NDLM predictive quantiles in the hundreds or thousands

## Relation to Prior Audit

The earlier parity audit had already shown that the forecast-window covariance prior path in `ndlm_main` is theory-aligned but partially parameterized through the exposed contract. That matters for fairness and tuning, but it does not explain the extreme forecast-tail explosion observed here.

Relevant earlier note:

- [wishart_prior_audit.md](/data/muscat_data/jaguir26/project1_ucsc_phd/reports/ndlm_parity_audit/wishart_prior_audit.md)

## Conclusion

The current evidence does not support a covariance blow-up diagnosis.

The multivariate NDLM covariance/state path appears numerically stable enough that the main remaining problem is better explained by the post-stage predictive-sampling bug than by PSD failure, Cholesky collapse, or a gross forecast-covariance explosion.
