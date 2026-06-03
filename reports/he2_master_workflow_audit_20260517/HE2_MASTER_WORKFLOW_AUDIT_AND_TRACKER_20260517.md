# HE2 Master Workflow Audit And Tracker

Date: 2026-06-03T06:59:49Z

## Current Decision

`exAL-M-T1`, `AL-M-T1`, and `exAL-M-T0` are now promoted onto canonical-bundle roots.
The full 9-model HE2 benchmark table is still transitional: the remaining six Bayesian comparison families
must be rerun or promoted onto the same 20260510 canonical input bundle before the paper can make final
all-model CRPS claims.

## Canonical Contract

- source manifest: `/data/muscat_data/jaguir26/project1_ucsc_phd/docs/exdqlm_multivar_keep_authoritative_specs_20260601.yaml`
- runtime root: `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_epsilon_discount_grid_20260524`
- shared bundle root: `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510`
- shared bundle run id: `20260510_publication_shared_r01`
- retrospective start: `1987-05-29`
- scale: `log1p_cms`, scored as `log_cms_plus1`
- covariates: `PPT`, `SOIL`, `PCA(alias=GDPC1)` with lags `1,2,3`, squares, and interaction

## Publication Gate

- promoted rows: `15`
- pending rows: `30`
- pending families: `6`
- pending submodels: `120`
- within-cutoff input-alignment checks passing now: `35 / 50`
- final 9-model benchmark ready: `False`

## Family State

| Label | Family | Rows | State | Required Action |
|---|---|---:|---|---|
| `AL-M-T0` | `dqlm_multivar_al_drop` | 5 | `pending_same_bundle_promotion` | `rerun_or_promote_on_20260510_canonical_bundle` |
| `AL-M-T1` | `dqlm_multivar_al_keep` | 5 | `authoritative_current_bundle_promoted` | `none` |
| `AL-U-T1` | `dqlm_univar_al` | 5 | `pending_same_bundle_promotion` | `rerun_or_promote_on_20260510_canonical_bundle` |
| `N-M-T0` | `ndlm_main_drop` | 5 | `pending_same_bundle_promotion` | `rerun_or_promote_on_20260510_canonical_bundle` |
| `N-M-T1` | `ndlm_main_keep` | 5 | `pending_same_bundle_promotion` | `rerun_or_promote_on_20260510_canonical_bundle` |
| `N-U-T1` | `ndlm_univar_keep` | 5 | `pending_same_bundle_promotion` | `rerun_or_promote_on_20260510_canonical_bundle` |
| `exAL-M-T0` | `exdqlm_multivar_drop` | 5 | `authoritative_current_bundle_promoted` | `none` |
| `exAL-M-T1` | `exdqlm_multivar_keep` | 5 | `authoritative_current_bundle_promoted` | `none` |
| `exAL-U-T1` | `exdqlm_univar` | 5 | `pending_same_bundle_promotion` | `rerun_or_promote_on_20260510_canonical_bundle` |

## Next Work

1. Build or select same-bundle rerun packages for the six pending families.
2. Run fit/post/validate/report with post-success heavy `.RData/.rda` cleanup enabled.
3. Rebuild the HE2 publication manifest; the alignment gate should move from `35 / 50` to `50 / 50`.
4. Refresh article assets and tables from the manifest only after the parity gate passes.
5. Then update manuscript prose and benchmark interpretation from the final 45-row source.

## Outputs

- family tracker: `/data/muscat_data/jaguir26/project1_ucsc_phd/reports/he2_master_workflow_audit_20260517/family_tracker.csv`
- cell tracker: `/data/muscat_data/jaguir26/project1_ucsc_phd/reports/he2_master_workflow_audit_20260517/cutoff_tracker.csv`
- summary: `/data/muscat_data/jaguir26/project1_ucsc_phd/reports/he2_master_workflow_audit_20260517/summary.json`
