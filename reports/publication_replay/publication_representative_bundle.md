# Publication Representative Replay Bundle

This bundle stages one representative replay row for each publication lineage
tracked in the current Bayesian HE2 table.

| Slug | Cutoff | Label | Lineage | Family | Source R | Runtime profile | Expected CRPS | Notes |
|---|---|---|---|---|---|---|---:|---|
| `20210123_n_m_t1` | 01/23/2021 | `N-M-T1` | `ndlm_featurecov_rerun_postfix_20260421` | `ndlm_main_keep` | `4.4.0 (2024-04-24)` | `authoritative_r440` | 0.5275 | Representative publication row. |
| `20210123_exal_u_t1` | 01/23/2021 | `exAL-U-T1` | `univar_featurecov_he2_rerun_20260422` | `exdqlm_univar` | `4.4.0 (2024-04-24)` | `authoritative_r440` | 0.2229 | Representative publication row. |
| `20210123_exal_m_t1` | 01/23/2021 | `exAL-M-T1` | `featurecov_cf1_eps_sweep_20260416` | `exdqlm_multivar_keep` | `4.4.0 (2024-04-24)` | `authoritative_r440` | 0.1569 | Representative cf1-sweep row; selected epsilon `eps360cf1`. |
| `20221225_exal_m_t1` | 12/25/2022 | `exAL-M-T1` | `exalm_t1_discount_grid_exact_20260424:set09_override` | `exdqlm_multivar_keep` | `4.4.0 (2024-04-24)` | `authoritative_r440` | 0.4375 | Publication override row; exact-input set09 representative. |

## Generated templates

- directory: `/data/muscat_data/jaguir26/project1_ucsc_phd/config/publication_replay_representatives_20260506`

## Launch expectation

- each row uses its own isolated artifact root under
  `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_publication_replay_representatives_20260506`
- runtime selection is source-run aware and reuses the recorded
  publication `R 4.4.0` stack when required
- cutoff and family scope are restricted to one publication row per lineage
- cf1 replay is restricted to the selected publication epsilon
- exact-grid replay is restricted to the publication `set09` profile
