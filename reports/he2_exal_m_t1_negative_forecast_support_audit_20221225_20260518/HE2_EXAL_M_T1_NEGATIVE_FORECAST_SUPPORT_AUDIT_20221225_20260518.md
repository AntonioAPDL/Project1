# exAL-M-T1 Negative Forecast Support Audit

- run_root: `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_20221225_reference_relaunch_20260518/runs/multimodel_20221225_v8_he2pubgdpc1r1_exdqlm_multivar_keep`
- analysis_scale_post_internal: `log1p_cms`
- transform guard: `identity` (`log1p_cms -> log1p_cms`)

## Main result

- issue_confirmed: `TRUE`
- final synthesized forecast negative mass: `0.3709`
- forecast days with final q05 < 0: `28 / 28`
- forecast days with final q20 < 0: `28 / 28`
- forecast days with final q35 < 0: `24 / 28`

## Interpretation

- The active canonical post path is no longer applying an extra exponentiation; the guard is identity on `log1p_cms`.
- The negative support remains after that fix.
- The negativity is already present in the row-specific predictive draws before the final synthesis step.
- The final q05 and q95 curves track the corresponding tail-row predictive objects closely, so the synthesis step is mostly inheriting the tail pathology rather than creating it from scratch.

## Key files

- `row_predictive_support_summary.csv`
- `row_predictive_support_by_day.csv`
- `synth_support_by_day.csv`
- `final_vs_row_target_quantiles.csv`
- `summary.json`
