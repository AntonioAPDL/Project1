# HE2 exAL-M-T1 Bridge Contract Confirmation (2026-05-18)

## Scope
Representative rerun audit for `exAL-M-T1` at cutoff `2022-12-25`.

## Main findings
- The active `disc_w` fit helper path already preserves the adapted retrospective response on the declared `log1p_cms` contract.
- The shared `R/environmetrics/10_data_inputs.R` bridge was still applying an unconditional second transform to retrospective and forecast inputs.
- The bug therefore affected the common post/diagnostic data assembly path directly, and did **not** require us to assume that the main fit runner was still double-logging the response.

## Patch
Patched:
- `R/environmetrics/10_data_inputs.R`

Behavior now:
- resolves `legacy_*_input_scale` and `analysis_scale_*_internal`
- converts from legacy input scale to analysis internal scale via `unified_convert_scale(...)`
- stays identity for the current representative `log1p_cms -> log1p_cms` contract
- still supports older `log1p_cms -> log_log1p_cms` behavior when explicitly requested by config

## Validation
Focused regression tests:
- `tests/python/test_environmetrics_scale_contract_bridges.py`
- result: `2 passed`

Direct representative replay against actual post adapters:
- `USGS max_abs_diff_vs_post_adapter = 0.0`
- `GloFAS max_abs_diff_vs_post_adapter = 0.0`
- `NWS3.0 max_abs_diff_vs_post_adapter = 0.0`

This confirms that the patched bridge is identity on the representative run's declared `log1p_cms` contract.

## Representative rerun
Fresh config:
- `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_20221225_reference_relaunch_20260518/control/generated_configs/multimodel_20221225_v8_he2pubgdpc1r1_exdqlm_multivar_keep_bridgefix_20260518.yaml`

Fresh run root:
- `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_20221225_reference_relaunch_20260518/runs/multimodel_20221225_v8_he2pubgdpc1r1_exdqlm_multivar_keep_bridgefix_20260518`

Current known stage at launch check:
- `data_prep_shared`
