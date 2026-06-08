# HE2 CRPS Table Readiness Audit (2026-06-08)

## Decision

The revised-doc CRPS benchmark table should now be refreshed from the current workflow manifest and treated as **paper-final for the current publication snapshot**.

## Why

- All 45 Bayesian table cells are canonical-bundle promoted.
- The three NDLM families now resolve to the June 7 promotion root and the same `20260510` shared-input bundle contract.
- The publication parity gate reports 45 promoted rows, 0 pending rows, and `final_9_model_benchmark_ready = true`.

## Current Benchmark Source

- Bayesian source: `artifacts/he2_publication_freeze/he2_bayesian_publication_manifest.csv`
- Note: Generated from the frozen HE2 publication manifest plus the raw-baseline rows in the five authoritative exAL-M-T1 CRPS summaries. All nine Bayesian benchmark families are promoted onto the canonical 20260510 input-bundle contract; this is the final CRPS table source for the current publication snapshot.

## Family Gates

| Label | Family | Current status | CRPS table gate | Blocking reason |
|---|---|---|---|---|
| `AL-M-T0` | `dqlm_multivar_al_drop` | `promoted` | `ready_final_snapshot` | `none` |
| `AL-M-T0` | `dqlm_multivar_al_drop` | `promoted` | `ready_final_snapshot` | `none` |
| `AL-M-T0` | `dqlm_multivar_al_drop` | `promoted` | `ready_final_snapshot` | `none` |
| `AL-M-T0` | `dqlm_multivar_al_drop` | `promoted` | `ready_final_snapshot` | `none` |
| `AL-M-T0` | `dqlm_multivar_al_drop` | `promoted` | `ready_final_snapshot` | `none` |
| `AL-M-T1` | `dqlm_multivar_al_keep` | `promoted` | `ready_final_snapshot` | `none` |
| `AL-M-T1` | `dqlm_multivar_al_keep` | `promoted` | `ready_final_snapshot` | `none` |
| `AL-M-T1` | `dqlm_multivar_al_keep` | `promoted` | `ready_final_snapshot` | `none` |
| `AL-M-T1` | `dqlm_multivar_al_keep` | `promoted` | `ready_final_snapshot` | `none` |
| `AL-M-T1` | `dqlm_multivar_al_keep` | `promoted` | `ready_final_snapshot` | `none` |
| `AL-U-T1` | `dqlm_univar_al` | `promoted` | `ready_final_snapshot` | `none` |
| `AL-U-T1` | `dqlm_univar_al` | `promoted` | `ready_final_snapshot` | `none` |
| `AL-U-T1` | `dqlm_univar_al` | `promoted` | `ready_final_snapshot` | `none` |
| `AL-U-T1` | `dqlm_univar_al` | `promoted` | `ready_final_snapshot` | `none` |
| `AL-U-T1` | `dqlm_univar_al` | `promoted` | `ready_final_snapshot` | `none` |
| `N-M-T0` | `ndlm_main_drop` | `promoted` | `ready_final_snapshot` | `none` |
| `N-M-T0` | `ndlm_main_drop` | `promoted` | `ready_final_snapshot` | `none` |
| `N-M-T0` | `ndlm_main_drop` | `promoted` | `ready_final_snapshot` | `none` |
| `N-M-T0` | `ndlm_main_drop` | `promoted` | `ready_final_snapshot` | `none` |
| `N-M-T0` | `ndlm_main_drop` | `promoted` | `ready_final_snapshot` | `none` |
| `N-M-T1` | `ndlm_main_keep` | `promoted` | `ready_final_snapshot` | `none` |
| `N-M-T1` | `ndlm_main_keep` | `promoted` | `ready_final_snapshot` | `none` |
| `N-M-T1` | `ndlm_main_keep` | `promoted` | `ready_final_snapshot` | `none` |
| `N-M-T1` | `ndlm_main_keep` | `promoted` | `ready_final_snapshot` | `none` |
| `N-M-T1` | `ndlm_main_keep` | `promoted` | `ready_final_snapshot` | `none` |
| `N-U-T1` | `ndlm_univar_keep` | `promoted` | `ready_final_snapshot` | `none` |
| `N-U-T1` | `ndlm_univar_keep` | `promoted` | `ready_final_snapshot` | `none` |
| `N-U-T1` | `ndlm_univar_keep` | `promoted` | `ready_final_snapshot` | `none` |
| `N-U-T1` | `ndlm_univar_keep` | `promoted` | `ready_final_snapshot` | `none` |
| `N-U-T1` | `ndlm_univar_keep` | `promoted` | `ready_final_snapshot` | `none` |
| `exAL-M-T0` | `exdqlm_multivar_drop` | `promoted` | `ready_final_snapshot` | `none` |
| `exAL-M-T0` | `exdqlm_multivar_drop` | `promoted` | `ready_final_snapshot` | `none` |
| `exAL-M-T0` | `exdqlm_multivar_drop` | `promoted` | `ready_final_snapshot` | `none` |
| `exAL-M-T0` | `exdqlm_multivar_drop` | `promoted` | `ready_final_snapshot` | `none` |
| `exAL-M-T0` | `exdqlm_multivar_drop` | `promoted` | `ready_final_snapshot` | `none` |
| `exAL-M-T1` | `exdqlm_multivar_keep` | `promoted` | `ready_final_snapshot` | `none` |
| `exAL-M-T1` | `exdqlm_multivar_keep` | `promoted` | `ready_final_snapshot` | `none` |
| `exAL-M-T1` | `exdqlm_multivar_keep` | `promoted` | `ready_final_snapshot` | `none` |
| `exAL-M-T1` | `exdqlm_multivar_keep` | `promoted` | `ready_final_snapshot` | `none` |
| `exAL-M-T1` | `exdqlm_multivar_keep` | `promoted` | `ready_final_snapshot` | `none` |
| `exAL-U-T1` | `exdqlm_univar` | `promoted` | `ready_final_snapshot` | `none` |
| `exAL-U-T1` | `exdqlm_univar` | `promoted` | `ready_final_snapshot` | `none` |
| `exAL-U-T1` | `exdqlm_univar` | `promoted` | `ready_final_snapshot` | `none` |
| `exAL-U-T1` | `exdqlm_univar` | `promoted` | `ready_final_snapshot` | `none` |
| `exAL-U-T1` | `exdqlm_univar` | `promoted` | `ready_final_snapshot` | `none` |

## Conclusion

Refresh the article-side manifest snapshot and regenerated TeX table includes from the current workflow manifest.

