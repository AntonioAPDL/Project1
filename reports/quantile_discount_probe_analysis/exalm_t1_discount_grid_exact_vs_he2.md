# exAL-M-T1 Exact-Input Discount Grid Comparison

This report compares the current HE-table `exAL-M-T1` baseline against the **exact-input** discount-grid reruns under `multimodel_v8_exalm_t1_discount_grid_exact_20260424`.

Comparison contract:
- baseline rows are the current HE `exAL-M-T1` source runs selected in the completed featurecov cf1 epsilon sweep
- probe rows are read from the exact-input discount-grid reruns
- both sides use the same run-local `crps_forecast_summary.csv` metric for `model_variant=exdqlm_multivar_keep`
- the exact-input campaign is considered apples-to-apples when:
  - `shared_snapshot.mode == exact_copy`
  - the preserved `shared_snapshot.source_root` matches the selected HE source `inputs/shared` root

Contract check:
- rows in grid: **45**
- started rows already verified as exact-copy apples-to-apples: **45 / 45**

Current campaign status:
| Status | Rows | Percent |
|---|---|---|
| pass | 45 | 100.000000 |
| running | 0 | 0.000000 |
| failed | 0 | 0.000000 |
| not_started | 0 | 0.000000 |

Current best completed challenger by cutoff:
| Cutoff | HE baseline CRPS | Best completed set | Best completed probe CRPS | Delta vs HE |
|---|---|---|---|---|
| 20210123 | 0.156860 | set08 | 0.158157 | 0.001297 (No) |
| 20211112 | 0.028384 | set05 | 0.025092 | -0.003292 (Yes) |
| 20211221 | 0.236937 | set06 | 0.172690 | -0.064248 (Yes) |
| 20220511 | 0.020966 | set03 | 0.021719 | 0.000753 (No) |
| 20221225 | 0.614397 | set09 | 0.437525 | -0.176872 (Yes) |

Detailed row-level comparison:
| Cutoff | Set | Status | Exact-copy | HE baseline | Probe CRPS | Delta | Better than HE | df_t | df_discrep | df_covs |
|---|---|---|---|---|---|---|---|---|---|---|
| 20210123 | set01 | pass | True | 0.156860 | 0.225540 | 0.068680 | False | 0.99999 | 0.9999 | 0.99995 |
| 20210123 | set02 | pass | True | 0.156860 | 0.163522 | 0.006662 | False | 0.99999999 | 0.998 | 0.99999 |
| 20210123 | set03 | pass | True | 0.156860 | 0.228671 | 0.071811 | False | 0.99999999 | 0.9999 | 0.99999 |
| 20210123 | set04 | pass | True | 0.156860 | 0.229457 | 0.072597 | False | 0.99999999 | 0.99999 | 0.99999 |
| 20210123 | set05 | pass | True | 0.156860 | 0.163711 | 0.006851 | False | 0.99999999 | 0.999 | 0.99995 |
| 20210123 | set06 | pass | True | 0.156860 | 0.158273 | 0.001414 | False | 0.99999999 | 0.999 | 0.9999 |
| 20210123 | set07 | pass | True | 0.156860 | 0.159436 | 0.002576 | False | 0.99999999 | 0.999 | 0.99999 |
| 20210123 | set08 | pass | True | 0.156860 | 0.158157 | 0.001297 | False | 0.99999999 | 0.999 | 0.99999 |
| 20210123 | set09 | pass | True | 0.156860 | 0.160985 | 0.004125 | False | 0.99999999 | 0.998 | 0.9999999 |
| 20211112 | set01 | pass | True | 0.028384 | 0.055218 | 0.026834 | False | 0.99999 | 0.9999 | 0.99995 |
| 20211112 | set02 | pass | True | 0.028384 | 0.037224 | 0.008840 | False | 0.99999999 | 0.998 | 0.99999 |
| 20211112 | set03 | pass | True | 0.028384 | 0.048926 | 0.020542 | False | 0.99999999 | 0.9999 | 0.99999 |
| 20211112 | set04 | pass | True | 0.028384 | 0.055716 | 0.027333 | False | 0.99999999 | 0.99999 | 0.99999 |
| 20211112 | set05 | pass | True | 0.028384 | 0.025092 | -0.003292 | True | 0.99999999 | 0.999 | 0.99995 |
| 20211112 | set06 | pass | True | 0.028384 | 0.027242 | -0.001141 | True | 0.99999999 | 0.999 | 0.9999 |
| 20211112 | set07 | pass | True | 0.028384 | 0.030924 | 0.002541 | False | 0.99999999 | 0.999 | 0.99999 |
| 20211112 | set08 | pass | True | 0.028384 | 0.029135 | 0.000752 | False | 0.99999999 | 0.999 | 0.99999 |
| 20211112 | set09 | pass | True | 0.028384 | 0.036225 | 0.007841 | False | 0.99999999 | 0.998 | 0.9999999 |
| 20211221 | set01 | pass | True | 0.236937 | 0.280539 | 0.043602 | False | 0.99999 | 0.9999 | 0.99995 |
| 20211221 | set02 | pass | True | 0.236937 | 0.905024 | 0.668087 | False | 0.99999999 | 0.998 | 0.99999 |
| 20211221 | set03 | pass | True | 0.236937 | 0.344581 | 0.107644 | False | 0.99999999 | 0.9999 | 0.99999 |
| 20211221 | set04 | pass | True | 0.236937 | 0.328981 | 0.092044 | False | 0.99999999 | 0.99999 | 0.99999 |
| 20211221 | set05 | pass | True | 0.236937 | 0.240659 | 0.003722 | False | 0.99999999 | 0.999 | 0.99995 |
| 20211221 | set06 | pass | True | 0.236937 | 0.172690 | -0.064248 | True | 0.99999999 | 0.999 | 0.9999 |
| 20211221 | set07 | pass | True | 0.236937 | 0.241593 | 0.004656 | False | 0.99999999 | 0.999 | 0.99999 |
| 20211221 | set08 | pass | True | 0.236937 | 0.232576 | -0.004362 | True | 0.99999999 | 0.999 | 0.99999 |
| 20211221 | set09 | pass | True | 0.236937 | 0.607554 | 0.370616 | False | 0.99999999 | 0.998 | 0.9999999 |
| 20220511 | set01 | pass | True | 0.020966 | 0.029378 | 0.008412 | False | 0.99999 | 0.9999 | 0.99995 |
| 20220511 | set02 | pass | True | 0.020966 | 0.029741 | 0.008775 | False | 0.99999999 | 0.998 | 0.99999 |
| 20220511 | set03 | pass | True | 0.020966 | 0.021719 | 0.000753 | False | 0.99999999 | 0.9999 | 0.99999 |
| 20220511 | set04 | pass | True | 0.020966 | 0.033604 | 0.012638 | False | 0.99999999 | 0.99999 | 0.99999 |
| 20220511 | set05 | pass | True | 0.020966 | 0.025087 | 0.004121 | False | 0.99999999 | 0.999 | 0.99995 |
| 20220511 | set06 | pass | True | 0.020966 | 0.022389 | 0.001423 | False | 0.99999999 | 0.999 | 0.9999 |
| 20220511 | set07 | pass | True | 0.020966 | 0.025431 | 0.004465 | False | 0.99999999 | 0.999 | 0.99999 |
| 20220511 | set08 | pass | True | 0.020966 | 0.022281 | 0.001315 | False | 0.99999999 | 0.999 | 0.99999 |
| 20220511 | set09 | pass | True | 0.020966 | 0.035269 | 0.014303 | False | 0.99999999 | 0.998 | 0.9999999 |
| 20221225 | set01 | pass | True | 0.614397 | 0.741350 | 0.126953 | False | 0.99999 | 0.9999 | 0.99995 |
| 20221225 | set02 | pass | True | 0.614397 | 0.450518 | -0.163879 | True | 0.99999999 | 0.998 | 0.99999 |
| 20221225 | set03 | pass | True | 0.614397 | 0.780740 | 0.166343 | False | 0.99999999 | 0.9999 | 0.99999 |
| 20221225 | set04 | pass | True | 0.614397 | 0.710234 | 0.095836 | False | 0.99999999 | 0.99999 | 0.99999 |
| 20221225 | set05 | pass | True | 0.614397 | 0.765545 | 0.151148 | False | 0.99999999 | 0.999 | 0.99995 |
| 20221225 | set06 | pass | True | 0.614397 | 0.768888 | 0.154490 | False | 0.99999999 | 0.999 | 0.9999 |
| 20221225 | set07 | pass | True | 0.614397 | 0.634006 | 0.019608 | False | 0.99999999 | 0.999 | 0.99999 |
| 20221225 | set08 | pass | True | 0.614397 | 0.610574 | -0.003824 | True | 0.99999999 | 0.999 | 0.99999 |
| 20221225 | set09 | pass | True | 0.614397 | 0.437525 | -0.176872 | True | 0.99999999 | 0.998 | 0.9999999 |
