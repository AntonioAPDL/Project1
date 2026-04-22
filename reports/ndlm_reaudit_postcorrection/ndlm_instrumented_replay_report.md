# NDLM Post-Correction Reaudit: Instrumented Replay Report

Date: 2026-04-21  
Status: complete

## Priority Rows Replayed

- `20211221 / ndlm_main_keep`
- `20221225 / ndlm_main_keep`
- `20211221 / ndlm_main_drop`

## What Was Replayed

The replay focused on the forecast-side predictive construction, using:

- saved predictive caches from the corrected rerun
- the preserved prelaunch smoke fit artifact for `ndlm_main_keep`
- the current fixed implementation of [post_ndlm_predictive_draws](/data/muscat_data/jaguir26/project1_ucsc_phd/R/environmetrics/02_helpers_core.R:189)

## Replay Findings

### 1. The anomaly is concentrated on a subset of forecast days

Worst daily CRPS values:

| Run | Worst lead | Worst daily CRPS |
|---|---:|---:|
| `20211221 / ndlm_main_keep` | `17` | `205.620105` |
| `20221225 / ndlm_main_keep` | `17` | `104.556740` |
| `20211221 / ndlm_main_drop` | `13` | `37.839398` |

So the issue is not an even forecast-window degradation; it is a catastrophic tail problem on selected forecast days.

### 2. The raw forecast ensembles are not exploding

From the multivariate NDLM ensemble summaries:

- `20211221` ensemble max q95 is about `1.537233`
- `20221225` ensemble max q95 is about `1.601519`

This is incompatible with the NDLM forecast q95 values of:

- `1406.190757` for `20211221 / ndlm_main_keep`
- `959.238068` for `20221225 / ndlm_main_keep`

### 3. The post-stage predictive sampler can reproduce the explosion under the old bug

Using the preserved smoke fit artifact:

- bug-path replay q99.9 = `2067.945949`
- bug-path replay max = `7365.636641`

Using the corrected USGS-only sigma stream:

- fixed replay q99.9 = `1.031747`
- fixed replay max = `1.100605`

This is the most direct causal evidence in the entire reaudit.

## Conclusion

The instrumented replay supports a concrete causal story:

1. the NDLM fit and covariance objects remain numerically coherent
2. the raw forecast drivers are not themselves explosive
3. the catastrophic multivariate NDLM tails arise when the post predictor mixes `nws` and `glofas` sigma draws into the USGS predictive sampler

So the replay evidence is consistent with the predictive-generation audit and inconsistent with a pure “Normal likelihood is weak” explanation.
