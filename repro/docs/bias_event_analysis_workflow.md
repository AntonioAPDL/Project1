# Bias Event Analysis Workflow

Event-focused bias analysis around selected dates using precomputed bias tables from `repro/bias_runs/<RUN_ID>/tables/bias_compare.csv`.

## Purpose

For each event date and horizon (`h=1`, `h=7`), inspect:

- `Bias_retro = USGS - Retro`
- `Bias_forecast = USGS - ForecastMean`
- `Delta = Bias_forecast - Bias_retro`

with focused windows around each event date, for:

- all centers,
- NWS/NWM only,
- GloFAS only.

## Run

```bash
python3 repro/tools/bias_event_analysis.py --config config/bias_event_analysis.template.yaml
```

## Outputs

Under `repro/bias_event_runs/<RUN_ID>/`:

- `plots/event_<YYYY-MM-DD>/panels_all_h01.png`
- `plots/event_<YYYY-MM-DD>/panels_nws_nwm_h01.png`
- `plots/event_<YYYY-MM-DD>/panels_glofas_h01.png`
- `plots/event_<YYYY-MM-DD>/scatter_all_h01.png`
- same set for `h07`
- `tables/event_summary.json`
- `tables/event_summary.md`
- `tables/event_date_notes.json`
- `event_report.md`
- `summary.json`
- `resolved_config.yaml`
- `logs/bias_event_analysis.log`

## Notes

- If a date token includes extra characters (for example `c2021-11-12`), the script sanitizes it to `2021-11-12` and records this in `event_date_notes.json`.
- Plots use fixed y-range by default (`[-30, 30]` cms) for comparability across events.
