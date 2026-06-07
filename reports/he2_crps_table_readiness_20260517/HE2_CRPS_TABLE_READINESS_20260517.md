# HE2 CRPS Table Readiness Audit (2026-05-17)

## Decision

The revised-doc CRPS benchmark table may use the current manifest snapshot as a transitional source, but it is **not paper-final** yet.

The full 9-model benchmark should not be interpreted as final until the three NDLM families are promoted onto the canonical workflow.

## Why

- The three NDLM families are not yet aligned to the current `20260510` canonical shared-input bundle contract.
- Six Bayesian families are now canonical-bundle promoted in the manifest: `exAL-M-T1`, `AL-M-T1`, `exAL-M-T0`, `AL-M-T0`, `AL-U-T1`, and `exAL-U-T1`.

## Current Benchmark Source

- Bayesian source: `artifacts/he2_publication_freeze/he2_bayesian_publication_manifest.csv`
- Note: Generated from the frozen HE2 publication manifest plus the raw-baseline rows in the five authoritative exAL-M-T1 CRPS summaries. The exAL-M-T1, AL-M-T1, exAL-M-T0, AL-M-T0, AL-U-T1, and exAL-U-T1 families are promoted onto canonical input bundles; this remains transitional until the three NDLM families are promoted onto the same canonical input bundle.

## Family Gates

| Label | Family | Current status | CRPS table gate | Blocking reason |
|---|---|---|---|---|
| `AL-M-T0` | `dqlm_multivar_al_drop` | `authoritative_current_bundle_promoted` | `ready_transitional_snapshot` | `canonical_bundle_promoted_current_manifest_row` |
| `AL-M-T1` | `dqlm_multivar_al_keep` | `authoritative_current_bundle_promoted` | `ready_transitional_snapshot` | `canonical_bundle_promoted_current_manifest_row` |
| `AL-U-T1` | `dqlm_univar_al` | `authoritative_current_bundle_promoted` | `ready_transitional_snapshot` | `canonical_bundle_promoted_current_manifest_row` |
| `N-M-T0` | `ndlm_main_drop` | `pending_same_bundle_promotion` | `blocked` | `ndlm_not_current_canonical_bundle_aligned` |
| `N-M-T1` | `ndlm_main_keep` | `pending_same_bundle_promotion` | `blocked` | `ndlm_not_current_canonical_bundle_aligned` |
| `N-U-T1` | `ndlm_univar_keep` | `pending_same_bundle_promotion` | `blocked` | `ndlm_not_current_canonical_bundle_aligned` |
| `exAL-M-T0` | `exdqlm_multivar_drop` | `authoritative_current_bundle_promoted` | `ready_transitional_snapshot` | `canonical_bundle_promoted_current_manifest_row` |
| `exAL-M-T1` | `exdqlm_multivar_keep` | `authoritative_current_bundle_promoted` | `ready_transitional_snapshot` | `canonical_bundle_promoted_current_manifest_row` |
| `exAL-U-T1` | `exdqlm_univar` | `authoritative_current_bundle_promoted` | `ready_transitional_snapshot` | `canonical_bundle_promoted_current_manifest_row` |

## Conclusion

The revised-doc benchmark CRPS table should remain labeled transitional until we have:
1. NDLM relaunched or promoted on the canonical shared bundle,
2. a rebuilt publication manifest and parity gate with no pending families, and
3. refreshed article assets and generated tables from that final manifest.

