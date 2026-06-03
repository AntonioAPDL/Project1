# HE2 Five-Family Publication Manifest Promotion

Date: 2026-06-03

## Decision

The HE2 publication-facing manifest now promotes five canonical-bundle families:

| label | family | promoted root | status |
|---|---|---|---|
| `exAL-M-T1` | `exdqlm_multivar_keep` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_epsilon_discount_grid_20260524` | authoritative canonical-grid winners |
| `AL-M-T1` | `dqlm_multivar_al_keep` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_dqlm_multivar_al_keep_from_exal_winners_20260602` | fit/post/validate/report pass for 5 cutoffs |
| `exAL-M-T0` | `exdqlm_multivar_drop` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_drop_current_relaunch_q50repair_20260602` | fit/post/validate/report pass for 5 cutoffs |
| `AL-U-T1` | `dqlm_univar_al` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_univar_al_exal_publication_relaunch_20260603` | fit/post/validate/report pass for 5 cutoffs |
| `exAL-U-T1` | `exdqlm_univar` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_univar_al_exal_publication_relaunch_20260603` | fit/post/validate/report pass for 5 cutoffs |

The manifest/parity gate now reports `25` promoted rows, `20` pending/blocked rows, `4` pending/blocked families, and
`50` pending/blocked submodels.

## Evidence Gates

The promotion is guarded in `scripts/build_he2_bayesian_publication_manifest.py`.

For every promoted row, the builder now requires:

- `fit`, `post`, `validate`, and `report` stages are `pass` in `run_manifest.yaml`;
- local `tables/crps_forecast_summary.csv` exists and supplies the publication CRPS row;
- `publication_figure_manifest.csv` exists in the post output directory;
- no retained `.RData`, `.rda`, or `.Rda` files remain under the run root;
- materialized fit inputs are identical across the three promoted families within each cutoff;
- source configs point at the canonical 20260510 bundle for parameters, retros, forecasts, and covariates;
- copied retrospective CSVs are semantically equal to the canonical bundle, allowing harmless floating text serialization differences.

## Generated Outputs

Main project outputs:

- `reports/he2_publication_manifest/he2_bayesian_publication_manifest.csv`
- `reports/he2_publication_manifest/he2_bayesian_publication_manifest.md`
- `reports/he2_publication_manifest/he2_publication_parity_gate.csv`
- `reports/he2_publication_manifest/he2_publication_parity_gate.md`
- `reports/he2_publication_manifest/he2_publication_parity_gate_summary.json`
- `reports/he2_master_workflow_audit_20260517/HE2_MASTER_WORKFLOW_AUDIT_AND_TRACKER_20260517.md`

## Remaining Or Blocked Families

The remaining same-bundle promotion work is:

| label | family | submodels |
|---|---|---:|
| `AL-M-T0` | `dqlm_multivar_al_drop` | 35 |
| `N-U-T1` | `ndlm_univar_keep` | 5 |
| `N-M-T0` | `ndlm_main_drop` | 5 |
| `N-M-T1` | `ndlm_main_keep` | 5 |

`AL-M-T0` is blocked by the 2026-06-03 fit-stage sigma/PSD failures. The next implementation target is the no-launch
targeted diagnostic package and a confirmed AL-specific discount/epsilon/c_factor spec, not a broad production launch.
