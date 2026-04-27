# HE2 Bayesian Publication Manifest

This report freezes the **current manuscript-facing HE2 Bayesian table** at the run level for all `9 x 5 = 45` cells.

Headline checks:
- published Bayesian HE2 cells documented: `45`
- cutoffs documented: `5`
- required shared-input artifacts checked within each cutoff: `10`
- fit covariate contract observed: `PPT|SOIL|PCA`
- deterministic-climate enabled flags observed: `True`
- covariate-features enabled flags observed: `True`
- lag orders observed: `1|2|3`
- square terms observed: `True`
- interaction term observed: `True`
- likelihood modes observed: `al, exal, normal`

Special publication update:
- `12/25/2022 / exAL-M-T1` now resolves to `multimodel_20221225_v8_exalm_t1_discount_grid_exact_v1_set09_exdqlm_multivar_keep` with mean CRPS `0.4375`, replacing the earlier cf1-sweep source row for that single HE2 cell.

## Within-Cutoff Input Congruence

| Cutoff | Artifact Checks Passing | Result |
|---|---|---|
| 01/23/2021 | 10 / 10 | Aligned |
| 11/12/2021 | 10 / 10 | Aligned |
| 12/21/2021 | 10 / 10 | Aligned |
| 05/11/2022 | 10 / 10 | Aligned |
| 12/25/2022 | 10 / 10 | Aligned |

Archival caveat:
- `usgs_daily.csv` was not preserved inside some older multivariate quantile run roots, so the strict within-cutoff congruence gate is evaluated on the **10 fit/forecast/blended-covariate artifacts** rather than on the auxiliary USGS cache file.

## Publication Rows

| Cutoff | Label | CRPS | Run ID | Campaign | Note |
|---|---|---|---|---|---|
| 01/23/2021 | N-U-T1 | 0.3520 | multimodel_20210123_v8_ndlm_featurecov_v1_postfix_ndlm_univar_keep | ndlm_featurecov_rerun_postfix_20260421 |  |
| 01/23/2021 | N-M-T0 | 0.5311 | multimodel_20210123_v8_ndlm_featurecov_v1_postfix_ndlm_main_drop | ndlm_featurecov_rerun_postfix_20260421 |  |
| 01/23/2021 | N-M-T1 | 0.5275 | multimodel_20210123_v8_ndlm_featurecov_v1_postfix_ndlm_main_keep | ndlm_featurecov_rerun_postfix_20260421 |  |
| 01/23/2021 | AL-U-T1 | 0.2449 | multimodel_20210123_v8_univar_featurecov_he2_v1_dqlm_univar_al | univar_featurecov_he2_rerun_20260422 |  |
| 01/23/2021 | AL-M-T0 | 0.3267 | multimodel_20210123_v8_eps30cf1_dqlm_multivar_al_drop_featurecov_cf1 | featurecov_cf1_eps_sweep_20260416 |  |
| 01/23/2021 | AL-M-T1 | 0.1604 | multimodel_20210123_v8_eps180cf1_dqlm_multivar_al_keep_featurecov_cf1 | featurecov_cf1_eps_sweep_20260416 |  |
| 01/23/2021 | exAL-U-T1 | 0.2229 | multimodel_20210123_v8_univar_featurecov_he2_v1_exdqlm_univar | univar_featurecov_he2_rerun_20260422 |  |
| 01/23/2021 | exAL-M-T0 | 0.3292 | multimodel_20210123_v8_eps30cf1_exdqlm_multivar_drop_featurecov_cf1 | featurecov_cf1_eps_sweep_20260416 |  |
| 01/23/2021 | exAL-M-T1 | 0.1569 | multimodel_20210123_v8_eps360cf1_exdqlm_multivar_keep_featurecov_cf1 | featurecov_cf1_eps_sweep_20260416 |  |
| 11/12/2021 | N-U-T1 | 0.2486 | multimodel_20211112_v8_ndlm_featurecov_v1_postfix_ndlm_univar_keep | ndlm_featurecov_rerun_postfix_20260421 |  |
| 11/12/2021 | N-M-T0 | 0.0565 | multimodel_20211112_v8_ndlm_featurecov_v1_postfix_ndlm_main_drop | ndlm_featurecov_rerun_postfix_20260421 |  |
| 11/12/2021 | N-M-T1 | 0.0722 | multimodel_20211112_v8_ndlm_featurecov_v1_postfix_ndlm_main_keep | ndlm_featurecov_rerun_postfix_20260421 |  |
| 11/12/2021 | AL-U-T1 | 0.1493 | multimodel_20211112_v8_univar_featurecov_he2_v1_dqlm_univar_al | univar_featurecov_he2_rerun_20260422 |  |
| 11/12/2021 | AL-M-T0 | 2.2435 | multimodel_20211112_v8_eps30cf1_dqlm_multivar_al_drop_featurecov_cf1 | featurecov_cf1_eps_sweep_20260416 |  |
| 11/12/2021 | AL-M-T1 | 0.0391 | multimodel_20211112_v8_eps180cf1_dqlm_multivar_al_keep_featurecov_cf1 | featurecov_cf1_eps_sweep_20260416 |  |
| 11/12/2021 | exAL-U-T1 | 0.1506 | multimodel_20211112_v8_univar_featurecov_he2_v1_exdqlm_univar | univar_featurecov_he2_rerun_20260422 |  |
| 11/12/2021 | exAL-M-T0 | 1.2744 | multimodel_20211112_v8_eps30cf1_exdqlm_multivar_drop_featurecov_cf1 | featurecov_cf1_eps_sweep_20260416 |  |
| 11/12/2021 | exAL-M-T1 | 0.0284 | multimodel_20211112_v8_eps180cf1_exdqlm_multivar_keep_featurecov_cf1 | featurecov_cf1_eps_sweep_20260416 |  |
| 12/21/2021 | N-U-T1 | 1.1768 | multimodel_20211221_v8_ndlm_featurecov_v1_postfix_ndlm_univar_keep | ndlm_featurecov_rerun_postfix_20260421 |  |
| 12/21/2021 | N-M-T0 | 1.5616 | multimodel_20211221_v8_ndlm_featurecov_v1_postfix_ndlm_main_drop | ndlm_featurecov_rerun_postfix_20260421 |  |
| 12/21/2021 | N-M-T1 | 0.6071 | multimodel_20211221_v8_ndlm_featurecov_v1_postfix_ndlm_main_keep | ndlm_featurecov_rerun_postfix_20260421 |  |
| 12/21/2021 | AL-U-T1 | 1.2283 | multimodel_20211221_v8_univar_featurecov_he2_v1_dqlm_univar_al | univar_featurecov_he2_rerun_20260422 |  |
| 12/21/2021 | AL-M-T0 | 0.6511 | multimodel_20211221_v8_eps360cf1_dqlm_multivar_al_drop_featurecov_cf1 | featurecov_cf1_eps_sweep_20260416 |  |
| 12/21/2021 | AL-M-T1 | 0.3482 | multimodel_20211221_v8_eps1cf1_dqlm_multivar_al_keep_featurecov_cf1 | featurecov_cf1_eps_sweep_20260416 |  |
| 12/21/2021 | exAL-U-T1 | 1.2691 | multimodel_20211221_v8_univar_featurecov_he2_v1_exdqlm_univar | univar_featurecov_he2_rerun_20260422 |  |
| 12/21/2021 | exAL-M-T0 | 0.4720 | multimodel_20211221_v8_eps1cf1_exdqlm_multivar_drop_featurecov_cf1 | featurecov_cf1_eps_sweep_20260416 |  |
| 12/21/2021 | exAL-M-T1 | 0.2369 | multimodel_20211221_v8_eps1cf1_exdqlm_multivar_keep_featurecov_cf1 | featurecov_cf1_eps_sweep_20260416 |  |
| 05/11/2022 | N-U-T1 | 0.1572 | multimodel_20220511_v8_ndlm_featurecov_v1_postfix_ndlm_univar_keep | ndlm_featurecov_rerun_postfix_20260421 |  |
| 05/11/2022 | N-M-T0 | 0.0241 | multimodel_20220511_v8_ndlm_featurecov_v1_postfix_ndlm_main_drop | ndlm_featurecov_rerun_postfix_20260421 |  |
| 05/11/2022 | N-M-T1 | 0.0416 | multimodel_20220511_v8_ndlm_featurecov_v1_postfix_ndlm_main_keep | ndlm_featurecov_rerun_postfix_20260421 |  |
| 05/11/2022 | AL-U-T1 | 0.0551 | multimodel_20220511_v8_univar_featurecov_he2_v1_dqlm_univar_al | univar_featurecov_he2_rerun_20260422 |  |
| 05/11/2022 | AL-M-T0 | 0.0433 | multimodel_20220511_v8_eps30cf1_dqlm_multivar_al_drop_featurecov_cf1 | featurecov_cf1_eps_sweep_20260416 |  |
| 05/11/2022 | AL-M-T1 | 0.0214 | multimodel_20220511_v8_eps90cf1_dqlm_multivar_al_keep_featurecov_cf1 | featurecov_cf1_eps_sweep_20260416 |  |
| 05/11/2022 | exAL-U-T1 | 0.0541 | multimodel_20220511_v8_univar_featurecov_he2_v1_exdqlm_univar | univar_featurecov_he2_rerun_20260422 |  |
| 05/11/2022 | exAL-M-T0 | 0.0694 | multimodel_20220511_v8_eps30cf1_exdqlm_multivar_drop_featurecov_cf1 | featurecov_cf1_eps_sweep_20260416 |  |
| 05/11/2022 | exAL-M-T1 | 0.0210 | multimodel_20220511_v8_eps180cf1_exdqlm_multivar_keep_featurecov_cf1 | featurecov_cf1_eps_sweep_20260416 |  |
| 12/25/2022 | N-U-T1 | 2.1451 | multimodel_20221225_v8_ndlm_featurecov_v1_postfix_ndlm_univar_keep | ndlm_featurecov_rerun_postfix_20260421 |  |
| 12/25/2022 | N-M-T0 | 2.3485 | multimodel_20221225_v8_ndlm_featurecov_v1_postfix_ndlm_main_drop | ndlm_featurecov_rerun_postfix_20260421 |  |
| 12/25/2022 | N-M-T1 | 0.5363 | multimodel_20221225_v8_ndlm_featurecov_v1_postfix_ndlm_main_keep | ndlm_featurecov_rerun_postfix_20260421 |  |
| 12/25/2022 | AL-U-T1 | 1.1038 | multimodel_20221225_v8_univar_featurecov_he2_v1_dqlm_univar_al | univar_featurecov_he2_rerun_20260422 |  |
| 12/25/2022 | AL-M-T0 | 2.2601 | multimodel_20221225_v8_eps1cf1_dqlm_multivar_al_drop_featurecov_cf1 | featurecov_cf1_eps_sweep_20260416 |  |
| 12/25/2022 | AL-M-T1 | 0.6186 | multimodel_20221225_v8_eps360cf1_dqlm_multivar_al_keep_featurecov_cf1 | featurecov_cf1_eps_sweep_20260416 |  |
| 12/25/2022 | exAL-U-T1 | 1.1189 | multimodel_20221225_v8_univar_featurecov_he2_v1_exdqlm_univar | univar_featurecov_he2_rerun_20260422 |  |
| 12/25/2022 | exAL-M-T0 | 2.3365 | multimodel_20221225_v8_eps1cf1_exdqlm_multivar_drop_featurecov_cf1 | featurecov_cf1_eps_sweep_20260416 |  |
| 12/25/2022 | exAL-M-T1 | 0.4375 | multimodel_20221225_v8_exalm_t1_discount_grid_exact_v1_set09_exdqlm_multivar_keep | exalm_t1_discount_grid_exact_20260424:set09_override | updated winner |

## Outputs

- manifest: `/data/muscat_data/jaguir26/project1_ucsc_phd/reports/he2_publication_manifest/he2_bayesian_publication_manifest.csv`
- inputs: `/data/muscat_data/jaguir26/project1_ucsc_phd/reports/he2_publication_manifest/he2_bayesian_publication_inputs.csv`
- alignment: `/data/muscat_data/jaguir26/project1_ucsc_phd/reports/he2_publication_manifest/he2_bayesian_publication_alignment.csv`

