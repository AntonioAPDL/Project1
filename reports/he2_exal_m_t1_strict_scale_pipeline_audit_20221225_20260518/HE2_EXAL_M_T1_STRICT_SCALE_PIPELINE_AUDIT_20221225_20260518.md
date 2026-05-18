# HE2 exAL-M-T1 Strict Scale Pipeline Audit 2026-05-18

- fit run root: `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_20221225_reference_relaunch_20260518/runs/multimodel_20221225_v8_he2pubgdpc1r1_exdqlm_multivar_keep_bridgefix_20260518`
- post run root: `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_20221225_reference_relaunch_20260518/runs/multimodel_20221225_v8_he2pubgdpc1r1_exdqlm_multivar_keep_postbridgefix_20260518`
- authoritative forecast review dir: `/data/muscat_data/jaguir26/project1_ucsc_phd/reports/he2_exal_m_t1_forecast_window_review_20221225_authoritative_postbridgefix_20260518`
- authoritative location review dir: `/data/muscat_data/jaguir26/project1_ucsc_phd/reports/he2_exal_m_t1_usgs_location_dynamics_review_20221225_authoritative_postbridgefix_20260518`

## Summary

- checks total: `55`
- checks failed: `0`
- exp guard identity on log1p contract: `true`
- data_cbind first three response columns match post adapters: `true`
- canonical quantile exports match cache quantiles: `true`
- canonical sample-subset export matches cache samples: `true`
- authoritative review exports match canonical objects: `true`

## Main outputs

- checks csv: `/data/muscat_data/jaguir26/project1_ucsc_phd/reports/he2_exal_m_t1_strict_scale_pipeline_audit_20221225_20260518/strict_scale_pipeline_checks.csv`
- artifact inventory: `/data/muscat_data/jaguir26/project1_ucsc_phd/reports/he2_exal_m_t1_strict_scale_pipeline_audit_20221225_20260518/artifact_inventory.csv`
- summary json: `/data/muscat_data/jaguir26/project1_ucsc_phd/reports/he2_exal_m_t1_strict_scale_pipeline_audit_20221225_20260518/summary.json`
