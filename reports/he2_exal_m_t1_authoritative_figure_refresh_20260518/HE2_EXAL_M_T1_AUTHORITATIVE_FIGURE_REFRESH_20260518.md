# HE2 exAL-M-T1 Authoritative Figure Refresh 2026-05-18

## Decision

The authoritative representative review figure set for `exAL-M-T1` cutoff `2022-12-25` is now the bundle rendered from:

- run root: `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_20221225_reference_relaunch_20260518/runs/multimodel_20221225_v8_he2pubgdpc1r1_exdqlm_multivar_keep_postbridgefix_20260518`

This run root used the patched `log1p_cms -> log1p_cms` bridge contract in `R/environmetrics/10_data_inputs.R` and the promoted scale-contract env plumbing in the shared unified stage entrypoints.

## Why this bundle is authoritative

1. `post`, `validate`, and `report` completed for the patched replay root.
2. The replay run log records:
   - `UNIFIED_LEGACY_FIT_INPUT_SCALE=log1p_cms`
   - `UNIFIED_ANALYSIS_SCALE_FIT_INTERNAL=log1p_cms`
   - `UNIFIED_LEGACY_POST_INPUT_SCALE=log1p_cms`
   - `UNIFIED_ANALYSIS_SCALE_POST_INTERNAL=log1p_cms`
3. The replay output matrix `data_cbind_tY_X.csv` now matches the post adapters exactly for:
   - `USGS`
   - `GloFAS`
   - `NWS3.0`
   across `12995` historical rows.
4. The refreshed review bundles below were rendered directly from this corrected run root.

## Authoritative review bundles

Forecast-window review:
- `/data/muscat_data/jaguir26/project1_ucsc_phd/reports/he2_exal_m_t1_forecast_window_review_20221225_authoritative_postbridgefix_20260518`

Location-dynamics review:
- `/data/muscat_data/jaguir26/project1_ucsc_phd/reports/he2_exal_m_t1_usgs_location_dynamics_review_20221225_authoritative_postbridgefix_20260518`

Most useful forecast-window figures:
- `/data/muscat_data/jaguir26/project1_ucsc_phd/reports/he2_exal_m_t1_forecast_window_review_20221225_authoritative_postbridgefix_20260518/cutoff_window_focus_with_raw_ensembles_log1p.png`
- `/data/muscat_data/jaguir26/project1_ucsc_phd/reports/he2_exal_m_t1_forecast_window_review_20221225_authoritative_postbridgefix_20260518/forecast_window_quantile_fan_log1p.png`
- `/data/muscat_data/jaguir26/project1_ucsc_phd/reports/he2_exal_m_t1_forecast_window_review_20221225_authoritative_postbridgefix_20260518/forecast_window_central_reasonableness_log1p.png`

Most useful mean-location figures:
- `/data/muscat_data/jaguir26/project1_ucsc_phd/reports/he2_exal_m_t1_usgs_location_dynamics_review_20221225_authoritative_postbridgefix_20260518/cutoff_window_usgs_location_mean_dynamics_log1p.png`
- `/data/muscat_data/jaguir26/project1_ucsc_phd/reports/he2_exal_m_t1_usgs_location_dynamics_review_20221225_authoritative_postbridgefix_20260518/cutoff_window_usgs_location_mean_dynamics_central_log1p.png`
- `/data/muscat_data/jaguir26/project1_ucsc_phd/reports/he2_exal_m_t1_usgs_location_dynamics_review_20221225_authoritative_postbridgefix_20260518/forecast_window_usgs_location_mean_dynamics_log1p.png`

## Authoritative script path

Patched bridge and promotion entrypoints:
- `R/environmetrics/10_data_inputs.R`
- `R/unified/stages/stage_fit.R`
- `R/unified/stages/stage_post.R`
- `scripts/run_environmetrics_figures.R`

Authoritative review refresh wrapper:
- `scripts/render_exal_m_t1_authoritative_review_bundle.sh`

Underlying review renderers:
- `scripts/render_exal_m_t1_forecast_window_review.R`
- `scripts/render_exal_m_t1_usgs_location_dynamics_review.R`

## Validation

Passed:
- `pytest -q tests/python/test_environmetrics_scale_contract_bridges.py tests/python/test_environmetrics_scale_contract_source_contract.py`
- result: `6 passed`

Run-manifest stage status for the patched replay root:
- `post: pass`
- `validate: pass`
- `report: pass`

Caveat:
- `report/summary.json` still records `validation_status = fail` for known deterministic-climate/report bookkeeping checks in this post-only replay configuration.
- That does not change the scale-contract confirmation or the authority of the refreshed review figures for this representative diagnostic lane.
