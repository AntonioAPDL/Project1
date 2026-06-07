# HE2 AL-M-T0 P5 Production Closeout - 2026-06-06

## Decision

`AL-M-T0` / `dqlm_multivar_al_drop` is now publication-promoted through the P5 production root:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_dqlm_multivar_al_drop_p5_production_20260606`

This closes the earlier P5 workflow gate. All five canonical cutoffs reached `report/pass`, produced CRPS summaries and publication figure manifests, and completed post-success heavy-artifact cleanup.

## Evidence Lock

Primary tracked helper:

- `scripts/build_he2_al_m_t0_p5_closeout_report.py`

Primary generated evidence:

- closeout report: `reports/he2_al_m_t0_p5_production_closeout_20260606/P5_PRODUCTION_CLOSEOUT.md`
- closeout summary: `reports/he2_al_m_t0_p5_production_closeout_20260606/p5_closeout_summary.csv`
- CRPS aggregate: `reports/he2_al_m_t0_p5_production_closeout_20260606/p5_crps_forecast_summary_all_cutoffs.csv`
- validation status: `reports/he2_al_m_t0_p5_production_closeout_20260606/p5_closeout_validation_status.txt`
- production matrix: `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_dqlm_multivar_al_drop_p5_production_20260606/control/publication_relaunch_matrix/matrix_status.csv`

Publication-manifest promotion helper:

- `scripts/build_he2_bayesian_publication_manifest.py`

Regenerated publication-manifest evidence:

- `reports/he2_publication_manifest/he2_bayesian_publication_manifest.csv`
- `reports/he2_publication_manifest/he2_bayesian_publication_manifest.md`
- `reports/he2_publication_manifest/he2_bayesian_publication_inputs.csv`
- `reports/he2_publication_manifest/he2_bayesian_publication_alignment.csv`

## Final P5 Cutoff Summary

| cutoff | matrix status | terminal q files | max state norm sq/T | synth CRPS | GLOFAS CRPS | NWS CRPS | figure manifest rows | retained RData |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `20210123` | `pass` | 7 | 9.23279504284 | 0.46797777375195321 | 0.40365981766818693 | 0.83036605178260892 | 2 | 0 |
| `20211112` | `pass` | 7 | 3.84619083137 | 0.19990057157767774 | 0.16957475641561054 | 1.3719166338517021 | 2 | 0 |
| `20211221` | `pass` | 7 | 11.4760833569 | 0.58668486044003065 | 0.68246362689335660 | 0.28117590724791863 | 2 | 0 |
| `20220511` | `pass` | 7 | 7.6690451241 | 0.21553150232042961 | 0.27226751146296652 | 0.28365909559653485 | 2 | 0 |
| `20221225` | `pass` | 7 | 12.6386808322 | 1.4026020148001415 | 1.5600635885630343 | 0.55680206834701040 | 2 | 0 |

CRPS values are on `log_cms_plus1` with `quantile_check_loss_sum` and the `k_over_m_plus_1` tau rule, as recorded in the P5 post-stage `tables/crps_forecast_summary.csv` files.

## Publication Manifest Impact

`scripts/build_he2_bayesian_publication_manifest.py` now resolves `dqlm_multivar_al_drop` rows from the P5 production root rather than from the older April feature-covariance sweep.

The regenerated manifest reports:

- total Bayesian HE2 table cells: `45`
- canonical-bundle promoted cells: `30`
- remaining transition cells: `15`
- promoted families: `exAL-M-T1`, `AL-M-T1`, `exAL-M-T0`, `AL-M-T0`, `AL-U-T1`, `exAL-U-T1`
- remaining transition families: `N-U-T1`, `N-M-T0`, `N-M-T1`

The manifest builder validated the P5 rows through the promoted-row gates: fit/post/validate/report pass in `run_manifest.yaml`, local CRPS table exists, publication figure manifest exists, required canonical artifacts are materialized and aligned with the promoted bundle contract, and no retained `.RData`, `.rda`, or `.Rda` files remain under the run roots.

## Reproduction Commands

```bash
python3 -m py_compile \
  scripts/build_he2_al_m_t0_p5_closeout_report.py \
  scripts/build_he2_bayesian_publication_manifest.py

python3 scripts/build_he2_al_m_t0_p5_closeout_report.py

python3 scripts/build_he2_bayesian_publication_manifest.py
```

## Remaining Work

The AL-M-T0 blocker is closed. The remaining benchmark-table promotion work is now the three NDLM families:

- `N-U-T1` / `ndlm_univar_keep`
- `N-M-T0` / `ndlm_main_drop`
- `N-M-T1` / `ndlm_main_keep`

Those rows are still documented in the publication manifest as transition rows from the older `ndlm_featurecov_rerun_postfix_20260421` lineage and should be rerun or promoted onto the same canonical 20260510 input-bundle contract before the full 9-model HE2 Bayesian benchmark is treated as final.
