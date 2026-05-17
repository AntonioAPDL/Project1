# HE2 CRPS Table Readiness Audit (2026-05-17)

## Decision

Do **not** rebuild or promote the revised-doc CRPS benchmark table yet.

The table should remain frozen on the current manuscript benchmark source until the full family set is ready under the canonical workflow.

## Why

- The three NDLM families are not yet aligned to the current `20260510` canonical shared-input bundle contract.
- `AL-M-T1` and `AL-M-T0` are not launched and are currently blocked by the late `20221225 q65` diagnostic failures.
- The completed shared-spec exAL rerun-local benchmark scores do not reconcile to the frozen exAL manuscript benchmark rows (`15/15` mismatches in the exAL audit).

## Current Benchmark Source

- Bayesian source: `artifacts/he2_publication_freeze/he2_bayesian_publication_manifest.csv`
- Note: Generated from the frozen HE2 publication manifest plus the raw-baseline rows in the five exAL-M-T1 CRPS summaries. This remains the manuscript benchmark source pending reconciliation with the completed shared-spec exAL rerun-local synthesis CRPS outputs.

## Family Gates

| Label | Family | Current status | CRPS table gate | Blocking reason |
|---|---|---|---|---|
| `exAL-M-T1` | `exdqlm_multivar_keep` | `authoritative_complete` | `blocked` | `exal_benchmark_rows_not_reconciled_to_completed_sharedspec_reruns` |
| `exAL-M-T0` | `exdqlm_multivar_drop` | `authoritative_complete` | `blocked` | `exal_benchmark_rows_not_reconciled_to_completed_sharedspec_reruns` |
| `exAL-U-T1` | `exdqlm_univar` | `authoritative_complete` | `blocked` | `exal_benchmark_rows_not_reconciled_to_completed_sharedspec_reruns` |
| `AL-M-T1` | `dqlm_multivar_al_keep` | `diagnostic_failed` | `blocked` | `al_multivar_not_launched_and_q65_diagnostics_failed` |
| `AL-M-T0` | `dqlm_multivar_al_drop` | `diagnostic_failed` | `blocked` | `al_multivar_not_launched_and_q65_diagnostics_failed` |
| `AL-U-T1` | `dqlm_univar_al` | `authoritative_complete` | `pending_family_set` | `al_univar_complete_but_al_multivar_family_set_not_ready` |
| `N-M-T1` | `ndlm_main_keep` | `completed_but_not_current_bundle_aligned` | `blocked` | `ndlm_not_current_canonical_bundle_aligned` |
| `N-M-T0` | `ndlm_main_drop` | `completed_but_not_current_bundle_aligned` | `blocked` | `ndlm_not_current_canonical_bundle_aligned` |
| `N-U-T1` | `ndlm_univar_keep` | `completed_but_not_current_bundle_aligned` | `blocked` | `ndlm_not_current_canonical_bundle_aligned` |

## Conclusion

The revised-doc benchmark CRPS table should stay frozen until we have:
1. NDLM relaunched on the canonical shared bundle,
2. AL multivariate keep/drop launched successfully, and
3. a deliberate benchmark-table reconciliation policy for the completed exAL shared-spec reruns.

