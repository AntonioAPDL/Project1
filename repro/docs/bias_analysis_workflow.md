# Bias Analysis Workflow (Read-Only to Existing Pipeline)

This workflow computes bias time series from existing forecats bundles and retros data, without modifying unified stage behavior.

## Purpose

For each climate center (`NWS/NWM`, `GloFAS`) and target date `t`:

1. `Bias_retro(t) = USGS(t) - Retro(t)`
2. `Bias_forecast(t, h) = USGS(t) - mean_ensemble(issue=t-h, target=t)` for horizons `h in {1, 7}`
3. `Delta(t, h) = Bias_forecast(t, h) - Bias_retro(t)`

All values are in `cms`.

## Inputs

Default config: `config/bias_analysis.template.yaml`

Expected artifacts:

- Forecats bundles under `data/forecats_inputs/site=11160500/cutoff_date=*/run_id=*/inputs/`
  - `nws_weighted_daily.csv`
  - `glofas_weighted_daily.csv`
- Retros source: `retros_2023-06-01.csv` (default, `log1p_cms`)

## Run

```bash
python3 repro/tools/bias_analysis.py --config config/bias_analysis.template.yaml
```

The command prints the output run directory.

## Outputs

Under `repro/bias_runs/<RUN_ID>/`:

- `tables/bias_retro.csv`
- `tables/bias_forecast.csv`
- `tables/bias_compare.csv`
- `tables/coverage.csv`
- `tables/cutoff_run_map.csv`
- `plots/<window_id>/ts_all_all_metrics_h01.png`
- `plots/<window_id>/ts_all_all_metrics_h07.png`
- `plots/<window_id>/ts_nws_nwm_retro_h01.png`, `ts_nws_nwm_forecast_h01.png`, `ts_nws_nwm_delta_h01.png` (and `h07`)
- `plots/<window_id>/ts_glofas_retro_h01.png`, `ts_glofas_forecast_h01.png`, `ts_glofas_delta_h01.png` (and `h07`)
- `plots/<window_id>/scatter_all_h01.png`, `scatter_nws_nwm_h01.png`, `scatter_glofas_h01.png` (and `h07`)
- Backward-compatible aliases remain:
  - `plots/<window_id>/bias_overlay_h01.png`, `bias_overlay_h07.png`
  - `plots/<window_id>/bias_scatter_h01.png`, `bias_scatter_h07.png`
- `summary.json`
- `resolved_config.yaml`
- `logs/bias_analysis.log`

## Notes

- The tool is read-only on source inputs.
- Boundary gaps are preserved explicitly (no imputation), especially at interval starts and horizon transitions.
- By default, if multiple `run_id=*` exist for a cutoff, the latest by mtime is selected (`run_id_selector: latest_mtime`).
- Visualization defaults prioritize readability:
  - thinner lines
  - metric markers
  - fixed bias range (`plots.y_limits_cms`, default `[-30, 30]`)
  - fixed scatter range (`plots.scatter_limits_cms`, default `[-30, 30]`)
