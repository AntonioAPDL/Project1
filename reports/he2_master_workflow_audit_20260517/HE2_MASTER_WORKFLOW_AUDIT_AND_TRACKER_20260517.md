# HE2 Master Workflow Audit And Tracker

Date: 2026-06-08T10:02:34Z

## Current Decision

All nine HE2 Bayesian benchmark families are now promoted onto canonical-bundle roots.
The full 9-model HE2 benchmark table is ready for the current paper snapshot after the June 7 NDLM promotion.

## Canonical Contract

- source manifest: `/data/muscat_data/jaguir26/project1_ucsc_phd/docs/exdqlm_multivar_keep_authoritative_specs_20260601.yaml`
- runtime root: `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_epsilon_discount_grid_20260524`
- shared bundle root: `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510`
- shared bundle run id: `20260510_publication_shared_r01`
- retrospective start: `1987-05-29`
- scale: `log1p_cms`, scored as `log_cms_plus1`
- covariates: `PPT`, `SOIL`, `PCA(alias=GDPC1)` with lags `1,2,3`, squares, and interaction

## Publication Gate

- promoted rows: `45`
- pending rows: `0`
- pending families: `0`
- pending submodels: `0`
- within-cutoff input-alignment checks passing now: `50 / 50`
- final 9-model benchmark ready: `True`

## Family State

| Label | Family | Rows | State | Required Action |
|---|---|---:|---|---|
| `AL-M-T0` | `dqlm_multivar_al_drop` | 5 | `authoritative_current_bundle_promoted` | `none` |
| `AL-M-T1` | `dqlm_multivar_al_keep` | 5 | `authoritative_current_bundle_promoted` | `none` |
| `AL-U-T1` | `dqlm_univar_al` | 5 | `authoritative_current_bundle_promoted` | `none` |
| `N-M-T0` | `ndlm_main_drop` | 5 | `authoritative_current_bundle_promoted` | `none` |
| `N-M-T1` | `ndlm_main_keep` | 5 | `authoritative_current_bundle_promoted` | `none` |
| `N-U-T1` | `ndlm_univar_keep` | 5 | `authoritative_current_bundle_promoted` | `none` |
| `exAL-M-T0` | `exdqlm_multivar_drop` | 5 | `authoritative_current_bundle_promoted` | `none` |
| `exAL-M-T1` | `exdqlm_multivar_keep` | 5 | `authoritative_current_bundle_promoted` | `none` |
| `exAL-U-T1` | `exdqlm_univar` | 5 | `authoritative_current_bundle_promoted` | `none` |

## Next Work

1. Keep the workflow manifest and parity gate as the source of truth for the manuscript CRPS table.
2. Refresh the article-side HE2 publication freeze from the workflow manifest.
3. Regenerate the article TeX table includes and asset-review reports.
4. Treat any future model-spec exploration as a new comparison grid, not as a modification of this frozen publication snapshot.

## Outputs

- family tracker: `/data/muscat_data/jaguir26/project1_ucsc_phd/reports/he2_master_workflow_audit_20260517/family_tracker.csv`
- cell tracker: `/data/muscat_data/jaguir26/project1_ucsc_phd/reports/he2_master_workflow_audit_20260517/cutoff_tracker.csv`
- summary: `/data/muscat_data/jaguir26/project1_ucsc_phd/reports/he2_master_workflow_audit_20260517/summary.json`
