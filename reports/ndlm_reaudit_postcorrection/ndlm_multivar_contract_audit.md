# NDLM Post-Correction Reaudit: Multivariate Contract Audit

Date: 2026-04-21  
Status: complete

## Scope

This note checks whether the multivariate NDLM anomaly is more likely to come from a broken state/measurement/transfer contract than from the predictive-sampling bug identified in the post stage.

## Runtime Evidence

Representative worst rows:

- [20211221 ndlm_main_keep diagnostics](</data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_ndlm_featurecov_rerun_20260420/runs/multimodel_20211221_v8_ndlm_featurecov_v1_ndlm_main_keep/diagnostics/ndlm>)
- [20221225 ndlm_main_keep diagnostics](</data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_ndlm_featurecov_rerun_20260420/runs/multimodel_20221225_v8_ndlm_featurecov_v1_ndlm_main_keep/diagnostics/ndlm>)
- [20211221 ndlm_main_drop diagnostics](</data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_ndlm_featurecov_rerun_20260420/runs/multimodel_20211221_v8_ndlm_featurecov_v1_ndlm_main_drop/diagnostics/ndlm>)

## Multivariate State/Lead Structure

The multivariate NDLM state dimensions are internally consistent across the forecast horizon:

| Run | Lead-wise state dimension |
|---|---:|
| `20211221 / ndlm_main_keep` | `34` for leads `1..28` |
| `20221225 / ndlm_main_keep` | `34` for leads `1..28` |
| `20211221 / ndlm_main_drop` | `21` for leads `1..28` |

The active-set diagnostics are also stable across leads:

| Run | Active NWS | Active GloFAS | Active count |
|---|---:|---:|---:|
| `20211221 / ndlm_main_keep` | `1` | `1` | `2` |
| `20221225 / ndlm_main_keep` | `1` | `1` | `2` |
| `20211221 / ndlm_main_drop` | `1` | `1` | `2` |

So there is no evidence here of a lead-indexing collapse or a disappearing forecast-family support set.

## Gaussian Smoother Congruence

The NDLM Kalman smoother core was checked against two references:

1. the NDLM C++ backend
2. the Gaussian smoother backbone used by the univariate exDQLM theory path

Results from [ndlm_kalman_congruence_checks.csv](/data/muscat_data/jaguir26/project1_ucsc_phd/reports/ndlm_reaudit_postcorrection/ndlm_kalman_congruence_checks.csv):

- `ndlm_r_vs_cpp_smooth_cov_max_abs_diff = 1.38777878078145e-17`
- `ndlm_r_vs_cpp_fitted_var_max_abs_diff = 2.77555756156289e-17`
- `ndlm_r_vs_univar_smooth_cov_max_abs_diff = 9.82612435862507e-10`
- `ndlm_r_vs_univar_fitted_mean_max_abs_diff = 1.07174602526072e-10`

The only material offset is that NDLM fitted variance is reported on the observation scale, so it includes `R_vec`, while the univariate Gaussian backbone report uses state-only fitted variance. After subtracting `R_vec`, the fitted-variance quantities align numerically.

## Theory Sources Used

- NDLM theory source of truth:
  [/data/muscat_data/jaguir26/NDLM---Ensemble/docs/derivations/main.tex](/data/muscat_data/jaguir26/NDLM---Ensemble/docs/derivations/main.tex)
- Existing theory-to-code audit:
  [P4_NDLM_THEORY_EQ_TO_CODE_v1.md](/data/muscat_data/jaguir26/project1_ucsc_phd/repro/audits/P4_NDLM_THEORY_EQ_TO_CODE_v1.md)
- Corresponding Gaussian backbone for the quantile family:
  [/data/muscat_data/jaguir26/univ-exDQLM---Ensemble/main.tex](/data/muscat_data/jaguir26/univ-exDQLM---Ensemble/main.tex)
- Existing quantile-family theory-to-code audit:
  [P3_UNIVAR_THEORY_EQ_TO_CODE_v1.md](/data/muscat_data/jaguir26/project1_ucsc_phd/repro/audits/P3_UNIVAR_THEORY_EQ_TO_CODE_v1.md)

## Conclusion

The multivariate NDLM state/measurement contract does not show an obvious structural failure in the forecast horizon:

- state dimensions are stable
- active-set behavior is stable
- the NDLM Kalman smoother core agrees with both the C++ backend and the Gaussian smoother backbone when like-for-like quantities are compared

This makes the forecast-side predictive-sampling bug a much stronger explanation for the catastrophic multivariate NDLM scores than a hidden Kalman-filter or smoother failure.
