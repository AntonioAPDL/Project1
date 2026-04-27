# NDLM Discount-Spec CRPS Comparison

This report compares the distinct NDLM discount-factor regimes we have actually run historically against the current postfix NDLM rows that are now in Table HE2-A.

## Main Takeaways

- N-M-T1: current postfix beats baseline at 5/5 cutoffs.
- N-M-T0: current postfix beats baseline at 3/5 cutoffs.
- N-U-T1: current postfix beats baseline at 3/5 cutoffs.
- The only meaningful distinct NDLM discount regimes we currently have are the old baseline TT regime and the tuned/postfix regime now used in the HE table.
- The intermediate `ndlm_tune_20260411` and `featurecov_rerun_20260420` campaigns reuse the tuned discount regime; they are included in the audit CSVs, but not used as separate discount-spec competitors.
- This is not a pure discount-only experiment, because the baseline TT campaign also differs in inputs/protocol from the current postfix featurecov rerun.

## Distinct Discount Regimes

| Campaign | Model | Regime | df_t | df_s1 | df_s2 | df_s67 | df_discrep | lambda | df_trans | df_covs |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Baseline TT regime | ndlm_main_drop | baseline_tt_regime | 0.99999999 | 0.99990000 | 0.99990000 | 0.99990000 | 0.99900000 | 0.97000000 | 0.99999990 | 0.99990000 |
| Current postfix HE row | ndlm_main_drop | tuned_postfix_regime | 0.99999999 | 0.99999999 | 0.99999999 | 0.99999999 | 0.99999999 | 0.97000000 | 0.99999990 | 0.99999999 |
| Baseline TT regime | ndlm_main_keep | baseline_tt_regime | 0.99999999 | 0.99990000 | 0.99990000 | 0.99990000 | 0.99900000 | 0.97000000 | 0.99999990 | 0.99990000 |
| Current postfix HE row | ndlm_main_keep | tuned_postfix_regime | 0.99999999 | 0.99999999 | 0.99999999 | 0.99999999 | 0.99999999 | 0.97000000 | 0.99999990 | 0.99999999 |
| Baseline TT regime | ndlm_univar_keep | baseline_tt_regime | 0.99999999 | 0.99990000 | 0.99990000 | 0.99990000 | n/a | 0.97000000 | 0.99999990 | 0.99999000 |
| Current postfix HE row | ndlm_univar_keep | tuned_postfix_regime | 0.99999999 | 0.99999999 | 0.99999999 | 0.99999999 | n/a | 0.97000000 | 0.99999990 | 0.99999999 |

## Current HE Winner By Cutoff

| Cutoff | Current HE Winner | Mean CRPS |
|---|---|---:|
| 2021-01-23 | exAL-M-T1 | 0.1569 |
| 2021-11-12 | exAL-M-T1 | 0.0284 |
| 2021-12-21 | exAL-M-T1 | 0.2369 |
| 2022-05-11 | exAL-M-T1 | 0.0210 |
| 2022-12-25 | N-M-T1 | 0.5363 |

## N-M-T1

| Cutoff | Baseline TT CRPS | Current Postfix CRPS | Delta (postfix-baseline) | Current HE Winner | Winner CRPS | Gap To HE Winner |
|---|---:|---:|---:|---|---:|---:|
| 2021-01-23 | 4.4601 | 0.5275 | -3.9325 | exAL-M-T1 | 0.1569 | 0.3706 |
| 2021-11-12 | 0.3557 | 0.0722 | -0.2835 | exAL-M-T1 | 0.0284 | 0.0438 |
| 2021-12-21 | 1.4099 | 0.6071 | -0.8027 | exAL-M-T1 | 0.2369 | 0.3702 |
| 2022-05-11 | 0.6278 | 0.0416 | -0.5862 | exAL-M-T1 | 0.0210 | 0.0206 |
| 2022-12-25 | 2.8785 | 0.5363 | -2.3422 | N-M-T1 | 0.5363 | -0.0000 |

## N-M-T0

| Cutoff | Baseline TT CRPS | Current Postfix CRPS | Delta (postfix-baseline) | Current HE Winner | Winner CRPS | Gap To HE Winner |
|---|---:|---:|---:|---|---:|---:|
| 2021-01-23 | 0.3599 | 0.5311 | 0.1712 | exAL-M-T1 | 0.1569 | 0.3742 |
| 2021-11-12 | 0.3226 | 0.0565 | -0.2661 | exAL-M-T1 | 0.0284 | 0.0281 |
| 2021-12-21 | 1.4536 | 1.5616 | 0.1081 | exAL-M-T1 | 0.2369 | 1.3247 |
| 2022-05-11 | 0.5689 | 0.0241 | -0.5448 | exAL-M-T1 | 0.0210 | 0.0031 |
| 2022-12-25 | 3.2322 | 2.3485 | -0.8837 | N-M-T1 | 0.5363 | 1.8122 |

## N-U-T1

| Cutoff | Baseline TT CRPS | Current Postfix CRPS | Delta (postfix-baseline) | Current HE Winner | Winner CRPS | Gap To HE Winner |
|---|---:|---:|---:|---|---:|---:|
| 2021-01-23 | 0.5851 | 0.3520 | -0.2331 | exAL-M-T1 | 0.1569 | 0.1951 |
| 2021-11-12 | 0.9105 | 0.2486 | -0.6619 | exAL-M-T1 | 0.0284 | 0.2202 |
| 2021-12-21 | 0.6926 | 1.1768 | 0.4842 | exAL-M-T1 | 0.2369 | 0.9399 |
| 2022-05-11 | 0.9125 | 0.1572 | -0.7552 | exAL-M-T1 | 0.0210 | 0.1362 |
| 2022-12-25 | 1.1617 | 2.1451 | 0.9833 | N-M-T1 | 0.5363 | 1.6088 |

## Interpretation

The current postfix HE rows are the right manuscript-facing reference, because they use the corrected post predictive-generation path. Empirically, the tuned/postfix NDLM main keep regime (`N-M-T1`) is better than the historical baseline TT regime at all five cutoffs, while `N-M-T0` and `N-U-T1` improve at three of five cutoffs.

Because the baseline TT campaign and the current postfix campaign also differ in input contract and protocol, this comparison should be read as a historical empirical benchmark rather than a pure controlled discount-factor sweep. A strict discount-only answer would still require rerunning the old baseline discount regime under the same current postfix featurecov contract.
