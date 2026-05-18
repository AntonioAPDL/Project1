# HE2 exAL-M-T1 Scale Contract Audit

- run root: `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_20221225_reference_relaunch_20260518/runs/multimodel_20221225_v8_he2pubgdpc1r1_exdqlm_multivar_keep`
- object inventory: `/data/muscat_data/jaguir26/project1_ucsc_phd/reports/he2_exal_m_t1_end_to_end_audit_20221225_20260518/scale_contract_inventory.csv`

## Main Conclusions

- The representative run advertises `analysis_scale_fit_internal = log1p_cms`.
- The representative run advertises `analysis_scale_post_internal = log1p_cms`.
- The representative run advertises `legacy_fit_input_scale = log1p_cms` and `legacy_post_input_scale = log1p_cms`.
- Raw USGS and raw shared forecast files remain on physical/raw flow scales.
- Retros adapters, post adapters, fit ingress exports, and active synthesis caches are on `log1p_cms` for this representative run.
- The `*_exp_guard.txt` report remains the main proof that the stale `log_log1p -> exp()` path was removed from the active representative post route.

## Status Counts

- `verified_by_codepath_and_filename`: 7
- `verified_by_codepath_and_plot_contract`: 1
- `verified_by_config`: 1
- `verified_by_config_and_codepath`: 1
- `verified_by_guard_report`: 1
- `verified_by_value_comparison`: 4
- `verified_by_values`: 3
- `verified_by_values_and_config`: 3

## Notes

- This audit is about scale contracts, not yet about whether the semantically correct model-side object is being plotted.
- Location-summary caches and synthesized predictive caches are intentionally separated because they may be on the same numeric scale while representing different mathematical objects.
