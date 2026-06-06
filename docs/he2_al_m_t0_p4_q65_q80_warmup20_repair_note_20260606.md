# HE2 AL-M-T0 P4 q65/q80 Warmup-20 Repair Note - 2026-06-06

## Purpose

This note records the targeted source-policy repair requested after the
five-cutoff AL-M-T0 P4 production matrix. The production evidence is preserved
in place; this change updates the tracked overlay used to regenerate future
repair/prelaunch configs.

## Evidence

The completed P4 production matrix is:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_dqlm_multivar_al_drop_p4_production_20260605/control/publication_relaunch_matrix/matrix_status.csv`

It closed with three passing report rows and two fit-fail rows:

| Cutoff | Status | Failed lane |
|---|---|---|
| `20210123` | `fit/fail` | `q80` |
| `20211112` | `report/pass` | none |
| `20211221` | `fit/fail` | `q65` |
| `20220511` | `report/pass` | none |
| `20221225` | `report/pass` | none |

Both failed lanes reached the end of fitting/sampling and then failed in the
post-save derivative/objective path with:

`Error in chol.default(G) : the leading minor of order 3 is not positive`

The observed active policies in the failed logs were:

| Lane | Previous `warmup_freeze_iters` | Other relevant policy |
|---|---:|---|
| `20210123 q80` | 5 | robust q80 initialization; no state guard |
| `20211221 q65` | 5 | q65 P4 state/covariance damping and fail-fast terminal guard |

## Implemented Source-Policy Change

Tracked overlay:

`config/he2_relaunch_batches/al_m_t0_p4_q65_guard_recovery_overlay_20260605.yaml`

The new overlay `spec_id` is:

`al_m_t0_p4_q65_q80_warmup20_highdf_eps365_cf1_20260606`

Only the problematic quantiles are changed:

| Quantile | Change |
|---|---|
| `q65` | set `warmup_freeze_iters: 20`; retain P4 `max_iter: 220`, `freeze_target: gamma_sigma`, state/covariance damping, and terminal fail-fast guard |
| `q80` | add explicit `freeze_target: gamma_sigma` and `warmup_freeze_iters: 20`; retain source robust initialization; do not add q65 damping or terminal guard |

The scientific/input contract is unchanged:

- target family: `dqlm_multivar_al_drop` / `AL-M-T0`;
- source family: promoted `exdqlm_multivar_drop` / `exAL-M-T0`;
- AL likelihood and transfer-drop post contract;
- data start `1987-05-29`;
- cutoffs `20210123`, `20211112`, `20211221`, `20220511`, `20221225`;
- quantiles `05`, `20`, `35`, `50`, `65`, `80`, `95`;
- all state discount factors `0.99999999`;
- `lambda = 0.97`;
- `epsilon = 365`;
- `c_factor = 1`.

## Validation Gate

Future repair/prelaunch generation must prove:

1. generated configs carry the new policy spec id;
2. `q65.warmup_freeze_iters == 20`;
3. `q80.warmup_freeze_iters == 20`;
4. q80 robust initialization is still present;
5. stale source `q50.freeze_target=states` is still removed;
6. no quantile-level `freeze_target=states` override remains.

The failed production configs should not be edited retroactively.
