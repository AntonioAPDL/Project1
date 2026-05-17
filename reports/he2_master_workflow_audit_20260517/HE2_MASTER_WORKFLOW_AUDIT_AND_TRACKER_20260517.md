# HE2 Master Workflow Audit And Tracker

Date: 2026-05-17

## Purpose

This document centralizes the current HE2 manuscript-rebuild state so we can clearly distinguish authoritative reruns, validation-only work, diagnostic failures, and article-repair lanes.

## Your Ultimate Goal

- Rebuild the full CRPS table from authoritative rerun outputs.
- Rebuild the other manuscript tables, including ablation-style comparisons, from the same authoritative run roots.
- Refresh every manuscript figure from authoritative outputs and corrected input bundles.
- Keep the whole workflow reproducible, centralized, documented, and flexible enough to tune individual quantiles without losing provenance.
- Clean heavy fit artifacts after post when they are no longer needed, while preserving the retained artifacts required for manuscript reproduction.

## Canonical Contract We Are Trying To Enforce

- Scale: `log(x+1)`.
- Shared retrospective history: `1987-05-29 -> cutoff`.
- Forecast alignment: NWS + GloFAS versions must match within cutoff.
- Covariates: `PPT`, `SOIL`, `PCA(alias=GDPC1)`.
- Engineered covariate features: lags `1,2,3`, squares on, interactions on.
- Deterministic climate: blended forecast contract where applicable.
- Quantile debugging policy: warm-up/stabilization first; only then consider `epsilon` / `c_factor`, and only with explicit approval.

## Current Authoritative Family State

| Label | Family | Mode | Current state | Notes |
|---|---|---|---|---|
| `exAL-M-T1` | `exdqlm_multivar_keep` | `exAL` | `authoritative_complete` | Corrected shared-spec rerun complete. |
| `exAL-M-T0` | `exdqlm_multivar_drop` | `exAL` | `authoritative_complete` | Corrected shared-spec rerun complete. |
| `exAL-U-T1` | `exdqlm_univar` | `exAL` | `authoritative_complete` | Corrected shared-spec rerun complete. |
| `AL-M-T1` | `dqlm_multivar_al_keep` | `AL` | `diagnostic_failed` | - global_models exdqlm_multivar_keep q=65: [FIT_FORECAST_HEALTH_FAIL] multivar keep q=65 violated forecast-health limits: max_abs_sm_ens=10017306363.541973 > 1000.000000 | max_abs_forecast_exps=16557925554.469927 > 650.000000 | max_E_sigma=596.181551 > 100.000000. See /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_dqlm_multivar_al_keep_20221225_q65_prodclone_diagnostic_20260517/control/prelaunch_validation_prodclone_20221225_q65_20260517/smoke_runs/fit_quantile/dqlm_multivar_al_keep/20221225/fit_smoke_dqlm_multivar_al_keep_20221225_qsubset/fit/exdqlm_multivar/keep/q=65/outputs/multivar_forecast_health.txt |
| `AL-M-T0` | `dqlm_multivar_al_drop` | `AL` | `diagnostic_failed` | - global_models exdqlm_multivar_drop q=65: [FIT_FORECAST_HEALTH_FAIL] multivar drop q=65 violated forecast-health limits: max_E_sigma=131.529506 > 100.000000. See /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_dqlm_multivar_al_drop_20221225_q65_prodclone_diagnostic_20260517/control/prelaunch_validation_prodclone_20221225_q65_20260517/smoke_runs/fit_quantile/dqlm_multivar_al_drop/20221225/fit_smoke_dqlm_multivar_al_drop_20221225_qsubset/fit/q=65/outputs/multivar_forecast_health.txt |
| `AL-U-T1` | `dqlm_univar_al` | `AL` | `authoritative_complete` | Canonical AL univar shared-spec rerun complete across all five cutoffs. |
| `N-M-T1` | `ndlm_main_keep` | `normal` | `completed_but_not_current_bundle_aligned` | Corrected NDLM featurecov rerun complete, but source_map still points to older input lineages. |
| `N-M-T0` | `ndlm_main_drop` | `normal` | `completed_but_not_current_bundle_aligned` | Corrected NDLM featurecov rerun complete, but source_map still points to older input lineages. |
| `N-U-T1` | `ndlm_univar_keep` | `normal` | `completed_but_not_current_bundle_aligned` | Corrected NDLM featurecov rerun complete, but source_map still points to older input lineages. |

## What Is Done

- `exdqlm_multivar_keep`, `exdqlm_multivar_drop`, and `exdqlm_univar` corrected shared-spec reruns are complete across all `5` cutoffs.
- `ndlm_main_keep`, `ndlm_main_drop`, and `ndlm_univar_keep` corrected featurecov reruns are complete across all `5` cutoffs, but they are **not yet** on the current `20260510` canonical shared bundle lineage.
- `dqlm_univar_al` canonical shared-spec rerun is complete across all `5` cutoffs.

## What Is Not Done

- `dqlm_multivar_al_keep` has **not** been launched as a production family.
- `dqlm_multivar_al_drop` has **not** been launched as a production family.
- The current manuscript-facing publication manifest still points to older pre-relaunch AL/exAL lineage for many table rows and should not yet be treated as the rebuilt final table source.
- The keep-side historical-support/current-model revised-doc figures are repaired and promoted through the retained-support replay contract.
- The benchmark CRPS table should remain frozen until NDLM is canonical, AL multivariate keep/drop are complete, and the exAL benchmark rows are reconciled.

## What Failed

- The AL multivariate late-cutoff diagnostic lane failed specifically at `20221225 q65`.
- `AL-M-T1`: - global_models exdqlm_multivar_keep q=65: [FIT_FORECAST_HEALTH_FAIL] multivar keep q=65 violated forecast-health limits: max_abs_sm_ens=10017306363.541973 > 1000.000000 | max_abs_forecast_exps=16557925554.469927 > 650.000000 | max_E_sigma=596.181551 > 100.000000. See /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_dqlm_multivar_al_keep_20221225_q65_prodclone_diagnostic_20260517/control/prelaunch_validation_prodclone_20221225_q65_20260517/smoke_runs/fit_quantile/dqlm_multivar_al_keep/20221225/fit_smoke_dqlm_multivar_al_keep_20221225_qsubset/fit/exdqlm_multivar/keep/q=65/outputs/multivar_forecast_health.txt
- `AL-M-T0`: - global_models exdqlm_multivar_drop q=65: [FIT_FORECAST_HEALTH_FAIL] multivar drop q=65 violated forecast-health limits: max_E_sigma=131.529506 > 100.000000. See /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_dqlm_multivar_al_drop_20221225_q65_prodclone_diagnostic_20260517/control/prelaunch_validation_prodclone_20221225_q65_20260517/smoke_runs/fit_quantile/dqlm_multivar_al_drop/20221225/fit_smoke_dqlm_multivar_al_drop_20221225_qsubset/fit/q=65/outputs/multivar_forecast_health.txt
- These were diagnostic failures, not completed production reruns.

## AL q65 Diagnostic State

- There are no active AL q65 prodclone processes now.
- The keep/drop q65 lanes should be treated as stopped failed diagnostics, not as live work.

## NDLM Provenance Correction

- The NDLM rerun is **not** on the current `20260510` canonical shared-input bundle lineage.
- Unique NDLM retrospective source-root groups observed: `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_20260402/runs, /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_histfix_20260407/runs, /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_ndlm_20260411/runs`.
- So NDLM should currently be classified as `completed older corrected rerun`, not `current canonical-bundle authoritative`.

## What Is Running Right Now

- No exAL/AL/NDLM q65 diagnostic processes are active now.
- No historical-support replay is still pending; that article-side repair is complete.

## Why The State Felt Messy

- Production reruns, no-launch validators, prodclone diagnostics, and article-repair replays ended up coexisting in the same time window.
- Some status reports are stale or validation-centric and do not distinguish clearly between `running`, `failed diagnostic`, and `authoritative production complete`.
- The publication manifest is a frozen manuscript-source report, not yet the final rebuilt authoritative-table tracker.
- The article figure tree is authoritative for the repaired exAL keep-side figures, but the benchmark table still depends on the frozen publication manifest.

## Policy Correction Going Forward

- Do **not** change `epsilon` / `c_factor` in active remediation without explicit approval.
- Treat warm-up / stabilization / initialization as the first-line quantile remediation path.
- Keep one central tracker for each family with four separate states: `authoritative production`, `validation-only`, `diagnostic`, `article integration`.
- Do not treat older publication-manifest rows as final once a corrected rerun exists.

## Article Integration State

- Figure lineage summary currently reports: `{'unchanged_intentionally': 8, 'updated_now': 39}`.
- Setup/support/context and synthesis families are already updated from corrected runtimes.
- Historical-support repair status: `repaired_via_retained_support_contract`.
- exAL benchmark reconciliation status: `blocked_on_benchmark_table_reconciliation`.
- CRPS benchmark-table readiness decision: `keep_frozen_current_benchmark_table`.

## Immediate Next Actions

1. Keep the benchmark CRPS table frozen until the NDLM family set is relaunched on the canonical shared bundle.
2. Re-open the AL multivariate lane as an explicit warm-up/stabilization investigation, not as a silent epsilon retuning exercise.
3. Freeze this tracker as the central status spine instead of relying on the older publication manifest or chat memory.
4. Build the final authoritative CRPS/table export layer only after NDLM is canonical, AL multivariate keep/drop are complete, and the exAL benchmark reconciliation policy is explicit.
5. Add explicit heavy-artifact retention/cleanup policy by stage so the post-required objects are preserved and the rest can be deleted safely.

## Outputs

- [family_tracker.csv](/data/muscat_data/jaguir26/project1_ucsc_phd/reports/he2_master_workflow_audit_20260517/family_tracker.csv)
- [cutoff_tracker.csv](/data/muscat_data/jaguir26/project1_ucsc_phd/reports/he2_master_workflow_audit_20260517/cutoff_tracker.csv)
- [ndlm_lineage_tracker.csv](/data/muscat_data/jaguir26/project1_ucsc_phd/reports/he2_master_workflow_audit_20260517/ndlm_lineage_tracker.csv)
- [summary.json](/data/muscat_data/jaguir26/project1_ucsc_phd/reports/he2_master_workflow_audit_20260517/summary.json)
