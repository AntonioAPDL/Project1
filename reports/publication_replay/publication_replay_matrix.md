# Publication Replay Matrix

This matrix locks the current manuscript-facing HE2 Bayesian publication lineage
to explicit run roots, compare bundles, score files, and output contracts.

- rows: `45`
- representative lineage rows: `4`

## Source of truth

- `reports/he2_publication_manifest/he2_bayesian_publication_manifest.csv`
- `reports/he2_publication_manifest/he2_bayesian_publication_manifest.md`

## Campaign counts

| Campaign lineage | Rows |
|---|---:|
| `exalm_t1_discount_grid_exact_20260424:set09_override` | 1 |
| `featurecov_cf1_eps_sweep_20260416` | 19 |
| `ndlm_featurecov_rerun_postfix_20260421` | 15 |
| `univar_featurecov_he2_rerun_20260422` | 10 |

## Representative rows

| Cutoff | Label | Campaign lineage | Replay environment recommendation |
|---|---|---|---|
| 01/23/2021 | `N-M-T1` | `ndlm_featurecov_rerun_postfix_20260421` | Use publication campaign artifacts first; recreate native campaign runtime before fresh reruns |
| 01/23/2021 | `exAL-U-T1` | `univar_featurecov_he2_rerun_20260422` | Use publication campaign artifacts first; recreate native campaign runtime before fresh reruns |
| 01/23/2021 | `exAL-M-T1` | `featurecov_cf1_eps_sweep_20260416` | Use publication campaign artifacts first; recreate native campaign runtime before fresh reruns |
| 12/25/2022 | `exAL-M-T1` | `exalm_t1_discount_grid_exact_20260424:set09_override` | Use exact-input lineage plus authoritative R 4.4 replay for fit-sensitive checks |

## Important note

The `12/25/2022 / exAL-M-T1` row is treated as a publication override. It
no longer points to the earlier `featurecov_cf1` run; it points to the
exact-input discount-grid winner under `set09`.

Full matrix: `/data/muscat_data/jaguir26/project1_ucsc_phd/reports/publication_replay/publication_replay_matrix.csv`
