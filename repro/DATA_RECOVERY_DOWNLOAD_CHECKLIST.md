# Data Recovery Download Checklist

Last updated: 2026-04-06 (tranche-1 active; auxiliary GLOFAS operational parallel full download launch active)  
Primary tracker: `repro/DATA_RECOVERY_CAMPAIGN_TRACKER.md`  
Current recovery run root: `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/data_recovery/site=11160500/recovery_run=site11160500_recovery_20260406T185022Z`

Purpose:

- This is the short operational checklist for the exact datasets we still need to materialize or intentionally reuse.
- Detailed lineage, commands, smoke evidence, and blockers live in `repro/DATA_RECOVERY_CAMPAIGN_TRACKER.md`.

## 1) Phase Gate

- [x] External runtime layout initialized
- [x] Bootstrap artifacts inventoried
- [x] Metadata-only manifests/plans written
- [x] One bounded smoke test run for each requested family
- [x] Smoke outputs reviewed for location, variable, product/version, schema, and coverage framing
- [x] Full backfills launched for tranche `source_native_tranche1_20260406T194500Z`
- [x] GEFS targeted retry and reconciled health pass completed
- [x] Muscat backup bootstrap artifacts recovered for NWS operational archive (`results.pkl`, `saved_data.pkl`, `NWM_v3_hydrofabric.gdb`)
- [x] Auxiliary GLOFAS operational forecast smoke suite passed
- [x] Auxiliary `forecast_download.py` smoke suite passed
- [ ] Remaining family full backfill health checks completed
- [ ] Final recovered family outputs consolidated

## 2) Main Download Queue

| queue item | family | source/product | version or selector | requested coverage | smoke status | planned canonical output | current action |
|---|---|---|---|---|---|---|---|
| `NWM-RETRO-12` | NWM retrospective | NOAA retrospective `.comp` | `1.2` | `1993-01-01` to `2017-12-31` | `pass` | `family=nwm_retrospective/full_runs/source_native_tranche1_20260406T194500Z/nwm_v12_campaign_source_native_tranche1_20260406T194500Z/` | launched and in progress |
| `NWM-RETRO-20` | NWM retrospective | NOAA retrospective Zarr | `2.0` | `1993-01-01` to `2018-12-31` | `pass` | `family=nwm_retrospective/full_runs/source_native_tranche1_20260406T194500Z/nwm_v20_campaign_source_native_tranche1_20260406T194500Z/` | complete and audited |
| `NWM-RETRO-21` | NWM retrospective | NOAA retrospective Zarr | `2.1` | `1979-02-01` to `2020-12-31` | `pass` | `family=nwm_retrospective/outputs/v21_full_daily.csv` | choose reuse of surviving backup or rebuild from source |
| `NWM-RETRO-30` | NWM retrospective | NOAA retrospective Zarr | `3.0` | `1979-02-01` to `2023-01-31` | `pass` | `family=nwm_retrospective/outputs/v30_full_daily.csv` | choose reuse of surviving backup or rebuild from source |
| `GLOFAS-HIST-21` | GLOFAS historical | EWDS historical consolidated | `version_2_1 + htessel_lisflood + consolidated` | `1987-05-29` to `2022-07-31` within project focus | `pass` | `family=glofas_historical/full_runs/source_native_tranche1_20260406T194500Z/outputs/historical_zips/hist_v21_htessel_cons/` plus extracted point CSV | launched and in progress |
| `GLOFAS-HIST-31` | GLOFAS historical | EWDS historical consolidated | `version_3_1 + lisflood + consolidated` | `1987-05-29` to `2023-05-01` within project focus | `pass` | `family=glofas_historical/full_runs/source_native_tranche1_20260406T194500Z/outputs/historical_zips/hist_v31_lisflood_cons/` plus extracted point CSV | launched and in progress |
| `GLOFAS-HIST-40` | GLOFAS historical | EWDS historical consolidated | `version_4_0 + lisflood + consolidated` | `1987-05-29` to `2023-05-01` within project focus | `pass` | `family=glofas_historical/full_runs/source_native_tranche1_20260406T194500Z/outputs/historical_zips/hist_v40_lisflood_cons/` plus extracted point CSV | launched and in progress |
| `GLOFAS-OPS-AUX` | GLOFAS operational forecasts | ECMWF/CEMS operational medium-range | `operational`, interpreted by issue date | prior cache window `2019-11-05` to `2023-01-31` | `pass` | `family=glofas_operational_forecasts/full_runs/glofas_operational_parallel_20260407T023100Z/outputs/download_root/` plus staged follow-on extraction command | launched in six equal parallel splits; download sessions active |
| `CLIMATE-PRISM` | Climate covariates | PRISM daily precipitation | `4km` | `1987-01-01` to `2023-12-31` | `pass` | `family=climate_covariates/outputs/prism_precipitation_santa_cruz_1987_2023.csv` | choose reuse of surviving CSV or rebuild from source |
| `CLIMATE-ERA5` | Climate covariates | ERA5-Land soil moisture | `swvl1` daily mean | `1987-01-01` to `2023-12-31` | `pass` | `family=climate_covariates/outputs/soil_moisture_big_trees_daily_avg_1987_2023.csv` | choose reuse of surviving CSV or rebuild from source |
| `GEFS-FORECASTS` | GEFS forecasts | NOAA GEFS archive point extraction | `00z`, 5 init dates | `2021-01-23`, `2021-11-12`, `2021-12-21`, `2022-05-11`, `2022-12-25` | `pass` | `family=gefs_forecasts/full_runs/source_native_tranche1_20260406T194500Z/gefs_nwm_forecast_manifest_source_native_tranche1_20260406T194500Z/extract_gefs_full_reconciled_gefs_retry_20260406T224500Z/` | complete via targeted retry + non-destructive reconciliation |
| `NWS-RESULTSPKL-AUX` | NWS operational archive | bounded `results.pkl` rebuild workflow | operational medium-range archive | audit-referenced `2018-09-17` to `2024-02-20` | `pass` | `family=nws_operational_results_archive/outputs/` | recovered bootstrap + smoke-validated; defer full archive regeneration until after main five-family recovery |
| `USGS-DAILY` | USGS daily flow | NWIS daily values | `00060/00003` | `1979-01-01` to chosen end date | `pass` | `family=usgs_daily_flow/full_runs/source_native_tranche1_20260406T194500Z/outputs/usgs_daily_flow_11160500.csv` | complete |
| `GLOFAS-LEGACY-V3` | GLOFAS historical | JRC legacy archive | `legacy v3.0` | `1980-01-01` to `2018-12-31` | not rerun in this cycle | `family=glofas_historical/outputs/glofas_legacy_global/` plus extracted point CSV | optional parity/reference lane; not part of minimum five-family queue |

## 3) Explicitly Blocked Or Deferred From Main Launch

| item | reason | status |
|---|---|---|
| `GLOFAS-LEGACY-V4` | direct-file URL/parity workflow still unresolved | blocked |
| `NWM-SYNTH-NWS-CACHE` | repo-local `forecast_cache/nws` missing | blocked |
| `GLOFAS-OPS-AUX-EXTRACT` | six-way download campaign is active; wide cache extraction should run after the split download sessions finish via staged `commands/run_extract_all.sh` | pending after downloads |
| `NWS-RESULTSPKL-FULL` | bounded rerun is validated, but a full archive regeneration is intentionally deferred until after the primary five-family recovery | deferred |
| `NWM-RETRO-SOIL-AUX` | useful auxiliary comparison series, but not part of the required five-family recovery minimum | optional |

## 4) Smoke Evidence Pointers

| family | smoke artifact root |
|---|---|
| NWM retrospective | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/data_recovery/site=11160500/recovery_run=site11160500_recovery_20260406T185022Z/family=nwm_retrospective/smoke/site11160500_nwm_retro_smoke_20260406T191500Z` |
| GLOFAS historical | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/data_recovery/site=11160500/recovery_run=site11160500_recovery_20260406T185022Z/family=glofas_historical/smoke/site11160500_glofas_historical_smoke_20260406T191700Z` |
| Climate covariates | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/data_recovery/site=11160500/recovery_run=site11160500_recovery_20260406T185022Z/family=climate_covariates/smoke/site11160500_climate_smoke_20260406T191900Z` |
| GEFS forecasts | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/data_recovery/site=11160500/recovery_run=site11160500_recovery_20260406T185022Z/family=gefs_forecasts/gefs_nwm_forecast_manifest_20260406T190344Z/smoke` |
| GLOFAS operational forecasts (auxiliary) | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/data_recovery/site=11160500/recovery_run=site11160500_recovery_20260406T185022Z/family=glofas_operational_forecasts/smoke/site11160500_glofas_operational_forecast_smoke_20260407T012316Z` |
| GLOFAS operational forecasts (auxiliary, six-split smoke) | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/data_recovery/site=11160500/recovery_run=site11160500_recovery_20260406T185022Z/family=glofas_operational_forecasts/smoke/site11160500_glofas_operational_parallel_smoke_20260407T022231Z` |
| NWS operational archive (auxiliary) | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/data_recovery/site=11160500/recovery_run=site11160500_recovery_20260406T185022Z/family=nws_operational_results_archive/smoke/site11160500_forecast_download_smoke_20260407T013413Z` |
| USGS daily flow | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/data_recovery/site=11160500/recovery_run=site11160500_recovery_20260406T185022Z/family=usgs_daily_flow/smoke/site11160500_usgs_daily_smoke_20260406T192100Z` |

## 5) Operator Notes

- Keep `NWM-RETRO-12` pinned to `feature_id=17682474`.
- Keep the NWS operational archive pinned to the same site lat/lon, but note that its operational bootstrap feature is `17684066` while the retrospective rebuild feature remains `17682474`.
- Active tranche-1 launch bundle:
  - `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/data_recovery/site=11160500/recovery_run=site11160500_recovery_20260406T185022Z/backfill_groups/source_native_tranche1_20260406T194500Z`
- Active GLOFAS operational six-split download campaign:
  - `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/data_recovery/site=11160500/recovery_run=site11160500_recovery_20260406T185022Z/family=glofas_operational_forecasts/full_runs/glofas_operational_parallel_20260407T023100Z`
- Active concurrent GLOFAS historical `v4.0` session:
  - `glofas_hist_v40_parallel_20260407T023100Z`
- GEFS canonical recovered output is now the reconciled directory:
  - `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/data_recovery/site=11160500/recovery_run=site11160500_recovery_20260406T185022Z/family=gefs_forecasts/full_runs/source_native_tranche1_20260406T194500Z/gefs_nwm_forecast_manifest_source_native_tranche1_20260406T194500Z/extract_gefs_full_reconciled_gefs_retry_20260406T224500Z`
- The original GEFS base extract is still preserved for audit:
  - `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/data_recovery/site=11160500/recovery_run=site11160500_recovery_20260406T185022Z/family=gefs_forecasts/full_runs/source_native_tranche1_20260406T194500Z/gefs_nwm_forecast_manifest_source_native_tranche1_20260406T194500Z/extract_gefs_full`
- Recovered NWS bootstrap artifacts now available:
  - `/data/muscat_data/jaguir26/project1_ucsc_phd/data/recovery_bootstrap/muscat_backup_20260406/results.pkl`
  - `/data/muscat_data/jaguir26/project1_ucsc_phd/data/recovery_bootstrap/muscat_backup_20260406/Project/Input/NWS-Coordinates/saved_data.pkl`
  - `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/data_recovery/bootstrap_recovered/muscat_backup_20260406/Project/Input/NWS-Coordinates/NWM_v3_hydrofabric.gdb`
- If we reuse surviving authoritative CSVs for `NWM-RETRO-21`, `NWM-RETRO-30`, `CLIMATE-PRISM`, or `CLIMATE-ERA5`, record that decision in the main tracker before launching other full backfills.
- Do not let blocked synthetic/legacy lanes delay the main five-family recovery objective.
