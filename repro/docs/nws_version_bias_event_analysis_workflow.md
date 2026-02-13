# NWS Versioned Bias Event Analysis Workflow

This workflow is NWS/NWM-only and does not change the unified pipeline behavior.

## Goal

1. Audit NWS retrospective sources and date coverage.
2. Plot retrospective sources together with version-boundary annotations.
3. Compute NWS-only bias time series and event-focused summaries by version window.

Bias definitions:

- `Bias_retro(t) = USGS(t) - Retro(t)`
- `Bias_forecast(t, h) = USGS(t) - mean_ensemble(issue=t-h, target=t)`
- `Delta(t, h) = Bias_forecast(t, h) - Bias_retro(t)`

All values are in `cms` (same domain as existing bias scripts).

## Config

Template:

- `config/nws_version_bias_event_analysis.template.yaml`

## Run

```bash
python3 repro/tools/nws_version_bias_event_analysis.py \
  --config config/nws_version_bias_event_analysis.template.yaml
```

The command prints the output run directory.

## Outputs

Under `repro/bias_version_runs/<RUN_ID>/`:

- `tables/source_audit.csv`
- `tables/version_coverage.csv`
- `tables/cutoff_run_map.csv`
- `tables/bias_forecast_nws.csv`
- `tables/bias_compare_nws_by_version.csv`
- `tables/event_version_summary.csv`
- `tables/focus_date_notes.csv`
- `plots/retros_sources_overlay.png`
- `plots/version_timeline.png`
- `plots/event_YYYY-MM-DD/panels_<version>_h01.png` and `_h07.png`
- `event_report.md`
- `summary.json`
- `resolved_config.yaml`
- `logs/nws_version_bias_event_analysis.log`

## Notes

- By default, this config runs **two NWS retrospective cases** only:
  - `NWS2.1` from `11160500_nws_retro_old.csv`
  - `NWS3.0` from `11160500_nws_retro.csv`
- Case windows can overlap (`analysis.allow_overlapping_versions: true`), which allows direct per-case comparison when both are available.
- The `source_key` field in each version window controls which retrospective source file is used for `Bias_retro` in that window.
- If a focus date is outside a version window (or data is absent), the report marks it explicitly.
