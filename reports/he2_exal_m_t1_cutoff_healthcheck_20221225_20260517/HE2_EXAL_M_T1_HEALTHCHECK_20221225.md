# exAL-M-T1 Single-Cutoff Health Check

Cutoff: `2022-12-25`  
Run id: `multimodel_20221225_v8_he2pubgdpc1r1_exdqlm_multivar_keep`  
Run root: `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_all_cutoffs_sharedspec_20260516/runs/multimodel_20221225_v8_he2pubgdpc1r1_exdqlm_multivar_keep`  
Health-check bundle: `/data/muscat_data/jaguir26/project1_ucsc_phd/reports/he2_exal_m_t1_cutoff_healthcheck_20221225_20260517`

## Executive Read

- family: `exAL-M-T1`
- stages: `data_prep_shared, fit, post, validate, report`
- validation status: `pass`
- post contract status: `True`
- synthesis mean CRPS: `162225957192096.50`
- synthesis input-health status: `pass`
- note: `No dedicated per-quantile trace PNGs are emitted; use All_ELBOS_DISC plus per-quantile fit/sampling logs.`

Heavy per-quantile fit-state `.RData` files are no longer present in the run root. That is consistent with post-cleanup and means this health check relies on logs, forecast-health summaries, post tables, and figures rather than retained fit-state blobs.

## What To Inspect First

- ELBO/trend figure: [`links/post/All_ELBOS_DISC.png`](./links/post/All_ELBOS_DISC.png)
- observed smoke figure: [`links/post/SMOKE_OBSERVED_SERIES_DISC.png`](./links/post/SMOKE_OBSERVED_SERIES_DISC.png)
- main synthesis figure: [`links/post/exdqlm_multivar_synth_keep_cutoff_window_posterior_samples.png`](./links/post/exdqlm_multivar_synth_keep_cutoff_window_posterior_samples.png)
- synthesis figure with raw ensembles: [`links/post/exdqlm_multivar_synth_keep_cutoff_window_posterior_samples_with_raw_ensembles.png`](./links/post/exdqlm_multivar_synth_keep_cutoff_window_posterior_samples_with_raw_ensembles.png)
- synthesis quantiles CSV: [`links/post/exdqlm_multivar_synth_keep_cutoff_window_quantiles.csv`](./links/post/exdqlm_multivar_synth_keep_cutoff_window_quantiles.csv)
- CRPS summary: [`links/post/tables/crps_forecast_summary.csv`](./links/post/tables/crps_forecast_summary.csv)
- gamma summary: [`links/post/tables/gamma_summary.csv`](./links/post/tables/gamma_summary.csv)
- sigma summary: [`links/post/tables/sigma_summary.csv`](./links/post/tables/sigma_summary.csv)
- covariate effects summary: [`links/post/tables/covariate_effects_summary.csv`](./links/post/tables/covariate_effects_summary.csv)
- compare report: [`links/validate/compare_report.json`](./links/validate/compare_report.json)
- report summary: [`links/report/summary.md`](./links/report/summary.md)

## Quantile Matrix

| q | freeze_target | warmup | state_guard | sampling_sec | n_samp | max_abs_sm_ens | max_abs_forecast_exps | nonfinite_forecast_exps | max_E_sigma |
|---|---|---:|---|---:|---:|---:|---:|---:|---:|
| `05` | `gamma_sigma` | `5` | `false` | `112.787` | `2000` | `41.55997654` | `32.67376444` | `48` | `0.1641896884` |
| `20` | `gamma_sigma` | `5` | `false` | `114.084` | `2000` | `2.20025557` | `3.748804161` | `48` | `0.02232366106` |
| `35` | `states` | `8` | `true` | `115.588` | `2000` | `5.910614049` | `8.945416789` | `48` | `0.05952037685` |
| `50` | `states` | `5` | `true` | `116.531` | `2000` | `1.799707236` | `3.712256706` | `48` | `0.01136618918` |
| `65` | `gamma_sigma` | `5` | `false` | `115.852` | `2000` | `1.584240954` | `3.36881387` | `48` | `0.01286283876` |
| `80` | `gamma_sigma` | `5` | `false` | `110.594` | `2000` | `2.842958276` | `3.669669832` | `48` | `0.0179517702` |
| `95` | `gamma_sigma` | `5` | `false` | `109.174` | `2000` | `42.40533925` | `33.62445837` | `48` | `0.1635069044` |

## Key Diagnostics

- run manifest: [`links/run_manifest.yaml`](./links/run_manifest.yaml)
- resolved config: [`links/resolved_config.yaml`](./links/resolved_config.yaml)
- source map: [`links/inputs/shared/source_map.txt`](./links/inputs/shared/source_map.txt)
- deterministic climate summary: [`links/inputs/shared/deterministic_climate/deterministic_climate_summary.txt`](./links/inputs/shared/deterministic_climate/deterministic_climate_summary.txt)
- fit stage log: [`links/fit/logs/fit_stage.log`](./links/fit/logs/fit_stage.log)
- post runner log: [`links/post/logs/post_runner.log`](./links/post/logs/post_runner.log)
- q=05: [`fit.log`](./links/fit/exdqlm_multivar/keep/q=05/logs/fit.log), [`sampling_diagnostics.log`](./links/fit/exdqlm_multivar/keep/q=05/logs/sampling_diagnostics.log), [`multivar_forecast_health.txt`](./links/fit/exdqlm_multivar/keep/q=05/outputs/multivar_forecast_health.txt)
- q=20: [`fit.log`](./links/fit/exdqlm_multivar/keep/q=20/logs/fit.log), [`sampling_diagnostics.log`](./links/fit/exdqlm_multivar/keep/q=20/logs/sampling_diagnostics.log), [`multivar_forecast_health.txt`](./links/fit/exdqlm_multivar/keep/q=20/outputs/multivar_forecast_health.txt)
- q=35: [`fit.log`](./links/fit/exdqlm_multivar/keep/q=35/logs/fit.log), [`sampling_diagnostics.log`](./links/fit/exdqlm_multivar/keep/q=35/logs/sampling_diagnostics.log), [`multivar_forecast_health.txt`](./links/fit/exdqlm_multivar/keep/q=35/outputs/multivar_forecast_health.txt)
- q=50: [`fit.log`](./links/fit/exdqlm_multivar/keep/q=50/logs/fit.log), [`sampling_diagnostics.log`](./links/fit/exdqlm_multivar/keep/q=50/logs/sampling_diagnostics.log), [`multivar_forecast_health.txt`](./links/fit/exdqlm_multivar/keep/q=50/outputs/multivar_forecast_health.txt)
- q=65: [`fit.log`](./links/fit/exdqlm_multivar/keep/q=65/logs/fit.log), [`sampling_diagnostics.log`](./links/fit/exdqlm_multivar/keep/q=65/logs/sampling_diagnostics.log), [`multivar_forecast_health.txt`](./links/fit/exdqlm_multivar/keep/q=65/outputs/multivar_forecast_health.txt)
- q=80: [`fit.log`](./links/fit/exdqlm_multivar/keep/q=80/logs/fit.log), [`sampling_diagnostics.log`](./links/fit/exdqlm_multivar/keep/q=80/logs/sampling_diagnostics.log), [`multivar_forecast_health.txt`](./links/fit/exdqlm_multivar/keep/q=80/outputs/multivar_forecast_health.txt)
- q=95: [`fit.log`](./links/fit/exdqlm_multivar/keep/q=95/logs/fit.log), [`sampling_diagnostics.log`](./links/fit/exdqlm_multivar/keep/q=95/logs/sampling_diagnostics.log), [`multivar_forecast_health.txt`](./links/fit/exdqlm_multivar/keep/q=95/outputs/multivar_forecast_health.txt)

## Notes

- This bundle is a focused reference check for a single cutoff only.
- It is meant to help us inspect fit behavior, posterior summaries, and synthesis behavior without mixing in cross-cutoff state.
- The workflow emits one aggregate ELBO figure plus per-quantile logs; it does not emit separate per-quantile trace PNGs in this run family.
- The representative synthesis figure is current, so any bad-looking forecast-window behavior here should be treated as a real output-quality concern, not an article-sync concern.
