# Phase 2 NDLM Label Mapping and Provenance Summary

Status: complete

## Headline Findings

- This phase established the pre-rerun provenance chain behind the older NDLM manuscript rows: they aligned with the final featurecov summary in [best_by_cutoff_long.csv](/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_featurecov_cf1_eps_sweep_20260416/reports/final_featurecov_cf1_eps_analysis/best_by_cutoff_long.csv), not with the older packaged [selection_manifest.csv](/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_20260402/exports/best9_cutoff_png_package_20260406/selection_manifest.csv).
- The current HE2 NDLM rows in the manuscript have since been replaced by the corrected NDLM featurecov rerun values; the provenance columns below are retained as historical context for why that rerun was needed.
- Across the 15 NDLM HE2 cells, the current selected source lineage is `baseline_tt` in 14 cells and `ndlm_relaunch_20260411` in 1 cell.
- The older packaged best9 manifest is stale for 12 of the 15 NDLM HE2 cells.

## Label Mapping

| Manuscript label | Unified family | Model ID | Transfer mode | Current provenance role |
| --- | --- | --- | --- | --- |
| `N-U-T1` | `ndlm_univar_keep` | `ndlm_univar_synth_keep` | `keep` | fixed baseline carried forward in current featurecov summary |
| `N-M-T0` | `ndlm_main_drop` | `ndlm_main_synth_drop` | `drop` | tuned current cf1 selection from current featurecov summary |
| `N-M-T1` | `ndlm_main_keep` | `ndlm_main_synth_keep` | `keep` | tuned current cf1 selection from current featurecov summary |

## Historical Provenance By Cutoff

| Label | Cutoff | Current HE2 value | Historical source lineage | Historical selected source run | Historical compare dir |
| --- | --- | ---: | --- | --- | --- |
| `N-U-T1` | `20210123` | `0.3520` | `baseline_tt` | `multimodel_20210123_v8_epsTT_l1` | `multimodel_20210123_v8_eps180cf1_compare` |
| `N-U-T1` | `20211112` | `0.2486` | `baseline_tt` | `multimodel_20211112_v8_epsTT_l1` | `multimodel_20211112_v8_eps180cf1_compare` |
| `N-U-T1` | `20211221` | `1.1768` | `baseline_tt` | `multimodel_20211221_v8_epsTT_l1` | `multimodel_20211221_v8_eps180cf1_compare` |
| `N-U-T1` | `20220511` | `0.1572` | `baseline_tt` | `multimodel_20220511_v8_epsTT_l1` | `multimodel_20220511_v8_eps180cf1_compare` |
| `N-U-T1` | `20221225` | `2.1451` | `baseline_tt` | `multimodel_20221225_v8_epsTT_l1` | `multimodel_20221225_v8_eps180cf1_compare` |
| `N-M-T0` | `20210123` | `0.5257` | `baseline_tt` | `multimodel_20210123_v8_epsTT_l2` | `multimodel_20210123_v8_eps30cf1_compare` |
| `N-M-T0` | `20211112` | `0.7126` | `baseline_tt` | `multimodel_20211112_v8_epsTT_l2` | `multimodel_20211112_v8_eps1cf1_compare` |
| `N-M-T0` | `20211221` | `3.5474` | `baseline_tt` | `multimodel_20211221_v8_epsTT_l2` | `multimodel_20211221_v8_eps1cf1_compare` |
| `N-M-T0` | `20220511` | `2.0727` | `baseline_tt` | `multimodel_20220511_v8_epsTT_l2` | `multimodel_20220511_v8_eps360cf1_compare` |
| `N-M-T0` | `20221225` | `4.2233` | `baseline_tt` | `multimodel_20221225_v8_epsTT_l2` | `multimodel_20221225_v8_eps360cf1_compare` |
| `N-M-T1` | `20210123` | `0.5930` | `ndlm_relaunch_20260411` | `multimodel_20210123_v8_ndlm_tune_20260411_v1_ndlm_main_keep` | `multimodel_20210123_v8_eps1cf1_compare` |
| `N-M-T1` | `20211112` | `0.8524` | `baseline_tt` | `multimodel_20211112_v8_epsTT_l1` | `multimodel_20211112_v8_eps360cf1_compare` |
| `N-M-T1` | `20211221` | `13.9269` | `baseline_tt` | `multimodel_20211221_v8_epsTT_l1` | `multimodel_20211221_v8_eps360cf1_compare` |
| `N-M-T1` | `20220511` | `2.2880` | `baseline_tt` | `multimodel_20220511_v8_epsTT_l1` | `multimodel_20220511_v8_eps30cf1_compare` |
| `N-M-T1` | `20221225` | `8.9743` | `baseline_tt` | `multimodel_20221225_v8_epsTT_l1` | `multimodel_20221225_v8_eps360cf1_compare` |

## Important Provenance Interpretation

- Historically, `N-U-T1` did not come from the dedicated NDLM relaunch tree. It was a carried-forward baseline row, and that older value was validated against the current featurecov compare reports rather than the older packaged best9 manifest.
- Historically, `N-M-T0` resolved to featurecov summary selections whose underlying selected source run remained in the baseline TT lineage for all five cutoffs.
- Historically, `N-M-T1` resolved mostly to baseline TT lineage, except for cutoff `20210123`, where the selected underlying source run came from the dedicated `ndlm_tune_20260411_v1` relaunch.

## Old Packaged Best9 Manifest Status

- The older packaged best9 export manifest should not be treated as the authoritative current source for the NDLM HE2 rows.
- It still matches some current cells, but it diverges materially for the multivariate NDLM rows and also diverges for `N-U-T1` at cutoffs `20211221` and `20220511`.

## Historical Role In The Audit

- This phase provided the provenance baseline that justified the later corrected rerun. The current manuscript-facing NDLM rows should now be interpreted through the completed rerun documented in `ndlm_final_audit_summary.md`, not through the historical featurecov compare lineage captured here.
