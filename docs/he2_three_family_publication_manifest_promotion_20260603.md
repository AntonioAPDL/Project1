# HE2 Six-Family Publication Manifest Promotion

Date: 2026-06-03

## Decision

The HE2 publication-facing manifest now promotes six canonical-bundle families:

| label | family | promoted root | status |
|---|---|---|---|
| `exAL-M-T1` | `exdqlm_multivar_keep` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_epsilon_discount_grid_20260524` | authoritative canonical-grid winners |
| `AL-M-T1` | `dqlm_multivar_al_keep` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_dqlm_multivar_al_keep_from_exal_winners_20260602` | fit/post/validate/report pass for 5 cutoffs |
| `exAL-M-T0` | `exdqlm_multivar_drop` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_drop_current_relaunch_q50repair_20260602` | fit/post/validate/report pass for 5 cutoffs |
| `AL-M-T0` | `dqlm_multivar_al_drop` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_dqlm_multivar_al_drop_p5_production_20260606` | fit/post/validate/report pass for 5 cutoffs |
| `AL-U-T1` | `dqlm_univar_al` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_univar_al_exal_publication_relaunch_20260603` | fit/post/validate/report pass for 5 cutoffs |
| `exAL-U-T1` | `exdqlm_univar` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_univar_al_exal_publication_relaunch_20260603` | fit/post/validate/report pass for 5 cutoffs |

The manifest gate now reports `30` promoted rows, `15` pending rows, and `3` pending families. `AL-M-T0` is no longer
publication-pending after the 2026-06-06 P5 production closeout.

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

## Remaining Families

The remaining same-bundle promotion work is:

| label | family | submodels |
|---|---|---:|
| `N-U-T1` | `ndlm_univar_keep` | 5 |
| `N-M-T0` | `ndlm_main_drop` | 5 |
| `N-M-T1` | `ndlm_main_keep` | 5 |

`AL-M-T0` raw-clone failures from 2026-06-03 remain useful diagnostic evidence, but the promoted production path is the
P5 policy documented in `docs/he2_al_m_t0_p5_postsave_objective_repair_plan_20260606.md` and closed out in
`docs/he2_al_m_t0_p5_production_closeout_20260606.md`.
