# NDLM Reaudit Anomaly Digest

Generated from the corrected 15-row NDLM rerun.

| Run | Mean CRPS | Median CRPS | Max CRPS | Max q80 | Max q95 | Ensemble max q95 | Quantile max q95 |
|---|---:|---:|---:|---:|---:|---:|---:|
| multimodel_20211221_v8_ndlm_featurecov_v1_ndlm_main_keep | 13.926882 | 2.875417 | 205.620105 | 16.036433 | 1406.190757 | 1.537233 | 5.610840 |
| multimodel_20221225_v8_ndlm_featurecov_v1_ndlm_main_keep | 8.974282 | 2.420286 | 104.556740 | 30.338708 | 959.238068 | 1.601519 | 7.807540 |
| multimodel_20221225_v8_ndlm_featurecov_v1_ndlm_main_drop | 4.223333 | 2.378465 | 37.004435 | 5.883947 | 224.435235 | 1.601519 | 2.083724 |
| multimodel_20211221_v8_ndlm_featurecov_v1_ndlm_main_drop | 3.547419 | 1.661402 | 37.839398 | 3.851449 | 193.614553 | 1.537233 | 6.211220 |
| multimodel_20220511_v8_ndlm_featurecov_v1_ndlm_main_keep | 2.288016 | 0.576934 | 33.249603 | 2.829716 | 181.225888 | -0.150334 | 0.632577 |

Key read:
- The worst rows are concentrated in the multivariate NDLM path (`ndlm_main_keep`, `ndlm_main_drop`).
- Their forecast-window medians are far smaller than their maxima, which indicates a small number of catastrophic forecast days dominate the score.
- The multivariate NDLM upper forecast quantiles are far larger than both the raw driver ensembles and the matched multivariate quantile-model outputs.
- The univariate NDLM rows do not carry multivariate ensemble-summary diagnostics, so those cells are intentionally `n/a` in the CSV.
