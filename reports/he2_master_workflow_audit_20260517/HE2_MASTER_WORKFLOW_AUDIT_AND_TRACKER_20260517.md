# HE2 Master Workflow Audit And Tracker

Date: 2026-06-07T00:39:15Z

## Current Decision

`exAL-M-T1`, `AL-M-T1`, `exAL-M-T0`, `AL-M-T0`, `AL-U-T1`, and `exAL-U-T1` are now promoted onto canonical-bundle roots.
The full 9-model HE2 benchmark table is still transitional because the three NDLM comparison families must be
rerun or promoted onto the same 20260510 canonical input bundle before the paper can make final all-model CRPS claims.

## Canonical Contract

- source manifest: `/data/muscat_data/jaguir26/project1_ucsc_phd/docs/exdqlm_multivar_keep_authoritative_specs_20260601.yaml`
- runtime root: `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_epsilon_discount_grid_20260524`
- shared bundle root: `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510`
- shared bundle run id: `20260510_publication_shared_r01`
- retrospective start: `1987-05-29`
- scale: `log1p_cms`, scored as `log_cms_plus1`
- covariates: `PPT`, `SOIL`, `PCA(alias=GDPC1)` with lags `1,2,3`, squares, and interaction

## Publication Gate

- promoted rows: `30`
- pending rows: `15`
- pending families: `3`
- pending submodels: `15`
- within-cutoff input-alignment checks passing now: `35 / 50`
- final 9-model benchmark ready: `False`

## Family State

| Label | Family | Rows | State | Required Action |
|---|---|---:|---|---|
| `AL-M-T0` | `dqlm_multivar_al_drop` | 5 | `authoritative_current_bundle_promoted` | `none` |
| `AL-M-T1` | `dqlm_multivar_al_keep` | 5 | `authoritative_current_bundle_promoted` | `none` |
| `AL-U-T1` | `dqlm_univar_al` | 5 | `authoritative_current_bundle_promoted` | `none` |
| `N-M-T0` | `ndlm_main_drop` | 5 | `pending_same_bundle_promotion` | `rerun_or_promote_on_20260510_canonical_bundle` |
| `N-M-T1` | `ndlm_main_keep` | 5 | `pending_same_bundle_promotion` | `rerun_or_promote_on_20260510_canonical_bundle` |
| `N-U-T1` | `ndlm_univar_keep` | 5 | `pending_same_bundle_promotion` | `rerun_or_promote_on_20260510_canonical_bundle` |
| `exAL-M-T0` | `exdqlm_multivar_drop` | 5 | `authoritative_current_bundle_promoted` | `none` |
| `exAL-M-T1` | `exdqlm_multivar_keep` | 5 | `authoritative_current_bundle_promoted` | `none` |
| `exAL-U-T1` | `exdqlm_univar` | 5 | `authoritative_current_bundle_promoted` | `none` |

## Next Work

1. Build or select same-bundle rerun packages for the three NDLM pending families.
2. Run the NDLM promotion/validation workflow on the canonical 20260510 bundle.
3. Rebuild the HE2 publication manifest and parity gate; the alignment gate should move to full pass only after NDLM is resolved.
4. Refresh article assets and tables from the manifest only after the parity gate passes.

## Outputs

- family tracker: `/data/muscat_data/jaguir26/project1_ucsc_phd/reports/he2_master_workflow_audit_20260517/family_tracker.csv`
- cell tracker: `/data/muscat_data/jaguir26/project1_ucsc_phd/reports/he2_master_workflow_audit_20260517/cutoff_tracker.csv`
- summary: `/data/muscat_data/jaguir26/project1_ucsc_phd/reports/he2_master_workflow_audit_20260517/summary.json`
