# HE2 Full CRPS Stage 1 Launcher Qualification

Date: 2026-05-16

## Decision

The remaining full-table Bayesian relaunch is approved to proceed only through the manifest-driven relaunch stack.

Approved launch authority:
- selection source: `reports/he2_publication_manifest/he2_bayesian_publication_manifest.csv`
- builder: `scripts/build_he2_bayesian_publication_relaunch_configs.py`
- validator: `scripts/validate_he2_bayesian_publication_relaunch_prelaunch.py`
- baseline template: `config/he2_bayesian_publication_relaunch_20260510.template.yaml`

Quarantined legacy builders:
- `scripts/build_multimodel_v8_featurecov_cf1_eps_matrix_configs.py`
- `scripts/build_multimodel_v8_all9_feature_matrix_configs.py`
- `scripts/build_multimodel_v8_ndlm_featurecov_rerun_matrix_configs.py`

## Why this launcher is the approved path

- It selects rows from the authoritative 45-row publication manifest.
- It starts from each publication-winning `resolved_config.yaml` instead of an older family sweep default.
- It freezes row-level winning spec tokens, config patches, and cutoff bundle audits.
- It already supports the corrected shared-input contract and prelaunch validation gates.

## Current audit read

- remaining Bayesian rows to relaunch: `40`
- remaining Bayesian families: `8`
- input-alignment audit checks passed: `50 / 50`
- cutoffs still lacking corrected full-history support in the current publication lineage: `20210123, 20211112, 20221225`
- completed reference family: `exdqlm_multivar_keep`
- completed reference root: `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_all_cutoffs_20260512`

## Wave grouping

| Wave | Families | Row count |
|---|---|---:|
| `wave_a_ndlm` | `ndlm_main_drop, ndlm_main_keep, ndlm_univar_keep` | 15 |
| `wave_b_univariate_bridge` | `dqlm_univar_al, exdqlm_univar` | 10 |
| `wave_c_multivariate_bridge` | `dqlm_multivar_al_drop, dqlm_multivar_al_keep, exdqlm_multivar_drop` | 15 |

## Wave A launch path

Wave A is the approved first relaunch wave:
- `ndlm_main_drop`
- `ndlm_main_keep`
- `ndlm_univar_keep`

Wave A row count by cutoff:
- `20210123`: `3` rows
- `20211112`: `3` rows
- `20211221`: `3` rows
- `20220511`: `3` rows
- `20221225`: `3` rows

## Frozen remaining-family spec source

Every remaining row now has a frozen local copy of its publication-winning `resolved_config.yaml` under:

- `source_config_freeze/`

Those frozen configs are the reviewer-facing proof that the remaining relaunch preserves the exact publication-winning row specs while changing only the shared-input lineage and relaunch scaffolding.

