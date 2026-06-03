# HE2 Bayesian Publication Manifest

This report freezes the **current manuscript-facing HE2 Bayesian table** at the run level for all `9 x 5 = 45` cells.

Headline checks:
- published Bayesian HE2 cells documented: `45`
- cutoffs documented: `5`
- canonical-bundle promoted cells: `15`
- remaining transition cells: `30`
- required shared-input artifacts checked within each cutoff: `10`
- fit covariate contract observed: `PPT|SOIL|PCA`
- deterministic-climate enabled flags observed: `True`
- covariate-features enabled flags observed: `True`
- lag orders observed: `1|2|3`
- square terms observed: `True`
- interaction term observed: `True`
- likelihood modes observed: `al, exal, normal`
- full within-cutoff shared-input alignment checks passing: `35 / 50`

Special publication update:
- `exAL-M-T1`, `AL-M-T1`, and `exAL-M-T0` now resolve to canonical-bundle promoted roots.
- Transition gate: the remaining six HE2 Bayesian comparison families still need rerun/promotion onto the same canonical 20260510 input-bundle contract before the full benchmark table should be treated as final.

## Canonical-Bundle Promoted Rows

| Cutoff | Label | Mean CRPS | Run ID |
|---|---|---|---|
| 01/23/2021 | AL-M-T1 | 0.1459 | multimodel_20210123_v8_he2grid_c04_eps365_dqlm_multivar_al_keep |
| 01/23/2021 | exAL-M-T0 | 1.2215 | multimodel_20210123_v8_he2pubgdpc1r1_exdqlm_multivar_drop |
| 01/23/2021 | exAL-M-T1 | 0.1397 | multimodel_20210123_v8_he2grid_c04_eps365_exdqlm_multivar_keep |
| 11/12/2021 | AL-M-T1 | 0.0555 | multimodel_20211112_v8_he2grid_c04_eps365_dqlm_multivar_al_keep |
| 11/12/2021 | exAL-M-T0 | 1.7987 | multimodel_20211112_v8_he2pubgdpc1r1_exdqlm_multivar_drop |
| 11/12/2021 | exAL-M-T1 | 0.0472 | multimodel_20211112_v8_he2grid_c04_eps365_exdqlm_multivar_keep |
| 12/21/2021 | AL-M-T1 | 0.2778 | multimodel_20211221_v8_he2grid_c03_eps030_dqlm_multivar_al_keep |
| 12/21/2021 | exAL-M-T0 | 1.0850 | multimodel_20211221_v8_he2pubgdpc1r1_exdqlm_multivar_drop |
| 12/21/2021 | exAL-M-T1 | 0.2654 | multimodel_20211221_v8_he2grid_c03_eps030_exdqlm_multivar_keep |
| 05/11/2022 | AL-M-T1 | 0.0572 | multimodel_20220511_v8_he2grid_c02_eps060_dqlm_multivar_al_keep |
| 05/11/2022 | exAL-M-T0 | 2.1310 | multimodel_20220511_v8_he2pubgdpc1r1_exdqlm_multivar_drop |
| 05/11/2022 | exAL-M-T1 | 0.0323 | multimodel_20220511_v8_he2grid_c02_eps060_exdqlm_multivar_keep |
| 12/25/2022 | AL-M-T1 | 0.6276 | multimodel_20221225_v8_he2grid_c05_eps030_dqlm_multivar_al_keep |
| 12/25/2022 | exAL-M-T0 | 1.2113 | multimodel_20221225_v8_he2pubgdpc1r1_exdqlm_multivar_drop |
| 12/25/2022 | exAL-M-T1 | 0.6655 | multimodel_20221225_v8_he2grid_c05_eps030_exdqlm_multivar_keep |

## Within-Cutoff Input Congruence

| Cutoff | Artifact Checks Passing | Result |
|---|---|---|
| 01/23/2021 | 7 / 10 | Transition mismatch |
| 11/12/2021 | 7 / 10 | Transition mismatch |
| 12/21/2021 | 7 / 10 | Transition mismatch |
| 05/11/2022 | 7 / 10 | Transition mismatch |
| 12/25/2022 | 7 / 10 | Transition mismatch |

Archival caveat:
- `usgs_daily.csv` was not preserved inside some older multivariate quantile run roots, so the strict within-cutoff congruence table is evaluated on the **10 fit/forecast/blended-covariate artifacts** rather than on the auxiliary USGS cache file.
- Input congruence is now a diagnostic gate, not a final-pass claim, because three families have been promoted and the other six comparison families still require matching canonical-input promotion.

## Publication Rows

| Cutoff | Label | CRPS | Run ID | Campaign | Note |
|---|---|---|---|---|---|
| 01/23/2021 | N-U-T1 | 0.3520 | multimodel_20210123_v8_ndlm_featurecov_v1_postfix_ndlm_univar_keep | ndlm_featurecov_rerun_postfix_20260421 |  |
| 01/23/2021 | N-M-T0 | 0.5311 | multimodel_20210123_v8_ndlm_featurecov_v1_postfix_ndlm_main_drop | ndlm_featurecov_rerun_postfix_20260421 |  |
| 01/23/2021 | N-M-T1 | 0.5275 | multimodel_20210123_v8_ndlm_featurecov_v1_postfix_ndlm_main_keep | ndlm_featurecov_rerun_postfix_20260421 |  |
| 01/23/2021 | AL-U-T1 | 0.2449 | multimodel_20210123_v8_univar_featurecov_he2_v1_dqlm_univar_al | univar_featurecov_he2_rerun_20260422 |  |
| 01/23/2021 | AL-M-T0 | 0.3267 | multimodel_20210123_v8_eps30cf1_dqlm_multivar_al_drop_featurecov_cf1 | featurecov_cf1_eps_sweep_20260416 |  |
| 01/23/2021 | AL-M-T1 | 0.1459 | multimodel_20210123_v8_he2grid_c04_eps365_dqlm_multivar_al_keep | dqlm_multivar_al_keep_from_exal_winners_20260602:canonical_bundle_promoted | canonical-bundle promoted |
| 01/23/2021 | exAL-U-T1 | 0.2229 | multimodel_20210123_v8_univar_featurecov_he2_v1_exdqlm_univar | univar_featurecov_he2_rerun_20260422 |  |
| 01/23/2021 | exAL-M-T0 | 1.2215 | multimodel_20210123_v8_he2pubgdpc1r1_exdqlm_multivar_drop | exdqlm_multivar_drop_current_relaunch_q50repair_20260602:canonical_bundle_promoted | canonical-bundle promoted |
| 01/23/2021 | exAL-M-T1 | 0.1397 | multimodel_20210123_v8_he2grid_c04_eps365_exdqlm_multivar_keep | exdqlm_multivar_keep_canonical_grid_20260524:authoritative_winner | canonical-bundle promoted |
| 11/12/2021 | N-U-T1 | 0.2486 | multimodel_20211112_v8_ndlm_featurecov_v1_postfix_ndlm_univar_keep | ndlm_featurecov_rerun_postfix_20260421 |  |
| 11/12/2021 | N-M-T0 | 0.0565 | multimodel_20211112_v8_ndlm_featurecov_v1_postfix_ndlm_main_drop | ndlm_featurecov_rerun_postfix_20260421 |  |
| 11/12/2021 | N-M-T1 | 0.0722 | multimodel_20211112_v8_ndlm_featurecov_v1_postfix_ndlm_main_keep | ndlm_featurecov_rerun_postfix_20260421 |  |
| 11/12/2021 | AL-U-T1 | 0.1493 | multimodel_20211112_v8_univar_featurecov_he2_v1_dqlm_univar_al | univar_featurecov_he2_rerun_20260422 |  |
| 11/12/2021 | AL-M-T0 | 2.2435 | multimodel_20211112_v8_eps30cf1_dqlm_multivar_al_drop_featurecov_cf1 | featurecov_cf1_eps_sweep_20260416 |  |
| 11/12/2021 | AL-M-T1 | 0.0555 | multimodel_20211112_v8_he2grid_c04_eps365_dqlm_multivar_al_keep | dqlm_multivar_al_keep_from_exal_winners_20260602:canonical_bundle_promoted | canonical-bundle promoted |
| 11/12/2021 | exAL-U-T1 | 0.1506 | multimodel_20211112_v8_univar_featurecov_he2_v1_exdqlm_univar | univar_featurecov_he2_rerun_20260422 |  |
| 11/12/2021 | exAL-M-T0 | 1.7987 | multimodel_20211112_v8_he2pubgdpc1r1_exdqlm_multivar_drop | exdqlm_multivar_drop_current_relaunch_q50repair_20260602:canonical_bundle_promoted | canonical-bundle promoted |
| 11/12/2021 | exAL-M-T1 | 0.0472 | multimodel_20211112_v8_he2grid_c04_eps365_exdqlm_multivar_keep | exdqlm_multivar_keep_canonical_grid_20260524:authoritative_winner | canonical-bundle promoted |
| 12/21/2021 | N-U-T1 | 1.1768 | multimodel_20211221_v8_ndlm_featurecov_v1_postfix_ndlm_univar_keep | ndlm_featurecov_rerun_postfix_20260421 |  |
| 12/21/2021 | N-M-T0 | 1.5616 | multimodel_20211221_v8_ndlm_featurecov_v1_postfix_ndlm_main_drop | ndlm_featurecov_rerun_postfix_20260421 |  |
| 12/21/2021 | N-M-T1 | 0.6071 | multimodel_20211221_v8_ndlm_featurecov_v1_postfix_ndlm_main_keep | ndlm_featurecov_rerun_postfix_20260421 |  |
| 12/21/2021 | AL-U-T1 | 1.2283 | multimodel_20211221_v8_univar_featurecov_he2_v1_dqlm_univar_al | univar_featurecov_he2_rerun_20260422 |  |
| 12/21/2021 | AL-M-T0 | 0.6511 | multimodel_20211221_v8_eps360cf1_dqlm_multivar_al_drop_featurecov_cf1 | featurecov_cf1_eps_sweep_20260416 |  |
| 12/21/2021 | AL-M-T1 | 0.2778 | multimodel_20211221_v8_he2grid_c03_eps030_dqlm_multivar_al_keep | dqlm_multivar_al_keep_from_exal_winners_20260602:canonical_bundle_promoted | canonical-bundle promoted |
| 12/21/2021 | exAL-U-T1 | 1.2691 | multimodel_20211221_v8_univar_featurecov_he2_v1_exdqlm_univar | univar_featurecov_he2_rerun_20260422 |  |
| 12/21/2021 | exAL-M-T0 | 1.0850 | multimodel_20211221_v8_he2pubgdpc1r1_exdqlm_multivar_drop | exdqlm_multivar_drop_current_relaunch_q50repair_20260602:canonical_bundle_promoted | canonical-bundle promoted |
| 12/21/2021 | exAL-M-T1 | 0.2654 | multimodel_20211221_v8_he2grid_c03_eps030_exdqlm_multivar_keep | exdqlm_multivar_keep_canonical_grid_20260524:authoritative_winner | canonical-bundle promoted |
| 05/11/2022 | N-U-T1 | 0.1572 | multimodel_20220511_v8_ndlm_featurecov_v1_postfix_ndlm_univar_keep | ndlm_featurecov_rerun_postfix_20260421 |  |
| 05/11/2022 | N-M-T0 | 0.0241 | multimodel_20220511_v8_ndlm_featurecov_v1_postfix_ndlm_main_drop | ndlm_featurecov_rerun_postfix_20260421 |  |
| 05/11/2022 | N-M-T1 | 0.0416 | multimodel_20220511_v8_ndlm_featurecov_v1_postfix_ndlm_main_keep | ndlm_featurecov_rerun_postfix_20260421 |  |
| 05/11/2022 | AL-U-T1 | 0.0551 | multimodel_20220511_v8_univar_featurecov_he2_v1_dqlm_univar_al | univar_featurecov_he2_rerun_20260422 |  |
| 05/11/2022 | AL-M-T0 | 0.0433 | multimodel_20220511_v8_eps30cf1_dqlm_multivar_al_drop_featurecov_cf1 | featurecov_cf1_eps_sweep_20260416 |  |
| 05/11/2022 | AL-M-T1 | 0.0572 | multimodel_20220511_v8_he2grid_c02_eps060_dqlm_multivar_al_keep | dqlm_multivar_al_keep_from_exal_winners_20260602:canonical_bundle_promoted | canonical-bundle promoted |
| 05/11/2022 | exAL-U-T1 | 0.0541 | multimodel_20220511_v8_univar_featurecov_he2_v1_exdqlm_univar | univar_featurecov_he2_rerun_20260422 |  |
| 05/11/2022 | exAL-M-T0 | 2.1310 | multimodel_20220511_v8_he2pubgdpc1r1_exdqlm_multivar_drop | exdqlm_multivar_drop_current_relaunch_q50repair_20260602:canonical_bundle_promoted | canonical-bundle promoted |
| 05/11/2022 | exAL-M-T1 | 0.0323 | multimodel_20220511_v8_he2grid_c02_eps060_exdqlm_multivar_keep | exdqlm_multivar_keep_canonical_grid_20260524:authoritative_winner | canonical-bundle promoted |
| 12/25/2022 | N-U-T1 | 2.1451 | multimodel_20221225_v8_ndlm_featurecov_v1_postfix_ndlm_univar_keep | ndlm_featurecov_rerun_postfix_20260421 |  |
| 12/25/2022 | N-M-T0 | 2.3485 | multimodel_20221225_v8_ndlm_featurecov_v1_postfix_ndlm_main_drop | ndlm_featurecov_rerun_postfix_20260421 |  |
| 12/25/2022 | N-M-T1 | 0.5363 | multimodel_20221225_v8_ndlm_featurecov_v1_postfix_ndlm_main_keep | ndlm_featurecov_rerun_postfix_20260421 |  |
| 12/25/2022 | AL-U-T1 | 1.1038 | multimodel_20221225_v8_univar_featurecov_he2_v1_dqlm_univar_al | univar_featurecov_he2_rerun_20260422 |  |
| 12/25/2022 | AL-M-T0 | 2.2601 | multimodel_20221225_v8_eps1cf1_dqlm_multivar_al_drop_featurecov_cf1 | featurecov_cf1_eps_sweep_20260416 |  |
| 12/25/2022 | AL-M-T1 | 0.6276 | multimodel_20221225_v8_he2grid_c05_eps030_dqlm_multivar_al_keep | dqlm_multivar_al_keep_from_exal_winners_20260602:canonical_bundle_promoted | canonical-bundle promoted |
| 12/25/2022 | exAL-U-T1 | 1.1189 | multimodel_20221225_v8_univar_featurecov_he2_v1_exdqlm_univar | univar_featurecov_he2_rerun_20260422 |  |
| 12/25/2022 | exAL-M-T0 | 1.2113 | multimodel_20221225_v8_he2pubgdpc1r1_exdqlm_multivar_drop | exdqlm_multivar_drop_current_relaunch_q50repair_20260602:canonical_bundle_promoted | canonical-bundle promoted |
| 12/25/2022 | exAL-M-T1 | 0.6655 | multimodel_20221225_v8_he2grid_c05_eps030_exdqlm_multivar_keep | exdqlm_multivar_keep_canonical_grid_20260524:authoritative_winner | canonical-bundle promoted |

## Outputs

- manifest: `/data/muscat_data/jaguir26/project1_ucsc_phd/reports/he2_publication_manifest/he2_bayesian_publication_manifest.csv`
- inputs: `/data/muscat_data/jaguir26/project1_ucsc_phd/reports/he2_publication_manifest/he2_bayesian_publication_inputs.csv`
- alignment: `/data/muscat_data/jaguir26/project1_ucsc_phd/reports/he2_publication_manifest/he2_bayesian_publication_alignment.csv`

