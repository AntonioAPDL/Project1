# exAL-M-T1 Discount Probe Comparison

This report compares the current HE2 `exAL-M-T1` row against the completed discount-factor probe reruns for `exdqlm_multivar_keep` across all five cutoffs.

Important scope note:
- The authoritative CRPS values for the probe runs are taken from each run-local post table: `post/outputs/<run_id>/tables/crps_forecast_summary.csv`.
- I did **not** use the reused compare-bundle summaries as the source of truth for the probe rows because those bundles are named after preserved source compare directories and can retain inherited source metadata that does not uniquely identify the newly probed exAL row.

Completed probe profiles included:
- Featurecov custom discount probe, Featurecov NDLM-tight discount probe

Scaffolded but not completed, so excluded from the result comparison:
- Featurecov hybrid discount probe, Older baseline discount probe

## Discount Profiles

| Profile | State | df_t | df_s1 | df_s2 | df_s67 | df_discrep | lambda | df_trans | df_covs |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Current HE2 baseline | completed_reference | 0.99999999 | 0.9999 | 0.9999 | 0.9999 | 0.999 | 0.97 | 0.9999999 | 0.99999 |
| Featurecov custom discount probe | completed | 0.99999 | 0.9995 | 0.9995 | 0.9999 | 0.997 | 0.97 | 0.9999999 | 0.9999 |
| Featurecov NDLM-tight discount probe | completed | 0.99999999 | 0.99999999 | 0.99999999 | 0.99999999 | 0.99999999 | 0.97 | 0.9999999 | 0.99999999 |
| Featurecov hybrid discount probe | missing_run_output |  | 0.99999 | 0.99999 | 0.99999 | 0.99999 |  |  | 0.999999 |
| Older baseline discount probe | missing_run_output | 0.99999999 | 0.99999999 | 0.99999999 | 0.99999999 | 0.99999999 | 0.97 | 0.9999999 | 0.99999999 |

## Cutoff Comparison

| Cutoff | HE2 baseline | Custom CRPS | Custom delta | NDLM-tight CRPS | NDLM-tight delta | Winner |
| --- | --- | --- | --- | --- | --- | --- |
| 20210123 | 0.156860 | 0.175880 | 0.019020 | 0.436682 | 0.279822 | Current HE2 baseline |
| 20211112 | 0.028384 | 0.032097 | 0.003713 | 0.095942 | 0.067558 | Current HE2 baseline |
| 20211221 | 0.236937 | 1.079838e+303 | 1.079838e+303 | 0.282697 | 0.045759 | Current HE2 baseline |
| 20220511 | 0.020966 | 2.795935e+17 | 2.795935e+17 | 0.044304 | 0.023338 | Current HE2 baseline |
| 20221225 | 0.614397 | 0.731801 | 0.117404 | 0.920275 | 0.305878 | Current HE2 baseline |

## Main Takeaways

- The current HE2 `exAL-M-T1` baseline remains the best completed profile in **5 / 5** cutoffs.
- The completed NDLM-tight discount probe is worse than the HE2 baseline in **5 / 5** cutoffs.
- The completed custom discount probe is also worse than the HE2 baseline in **5 / 5** cutoffs, and it is catastrophically unstable at `20211221` and `20220511`.
- Based on the completed discount probes, there is **no evidence** that the new discount-factor launches improved `exAL-M-T1` relative to the current HE2 row.
