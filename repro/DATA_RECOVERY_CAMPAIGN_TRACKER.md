# Data Recovery Campaign Tracker

Last updated: 2026-04-06  
Status owner: this document is the operational source of truth for the post-cleanup recovery campaign at site `11160500`.

## 1) Scope Lock

Target location:

- USGS site: `11160500`
- Lat/Lon: `37.0443931`, `-122.072464`
- Site label: San Lorenzo / Big Trees

Requested source families:

1. NWS/NWM/NOAA retrospective analysis at `11160500`
2. GLOFAS/ECMWF historical analysis at `11160500`
3. ERA5 and PRISM climate covariates at the same location
4. GEFS forecasts for precipitation and soil moisture
5. USGS daily flow

Authoritative context documents:

- `repro/NWS_NWM_GLOFAS_DATA_AUDIT_PLAN.md`
- `repro/FORECATS_INPUTS_AND_WEIGHTING_PLAN.md`
- `repro/NWM_RETROSPECTIVE_EXTRACTION_WORKSTREAM_TRACKER.md`
- `repro/GLOFAS_OPERATIONAL_MEDIUMRANGE_WORKFLOW_RUNBOOK.md`
- `repro/GEFS_NWM_FORECAST_AUDIT_TRACKER.md`
- `repro/LEGACY_GLOFAS_REANALYSIS_DOWNLOAD_PLAN.md`
- `repro/PROVENANCE_AND_RECOVERY_PLAN.md`

## 2) Recovery Rules

- Do not write new large restored datasets under the repo root by default.
- Use external runtime storage rooted at `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime`.
- Keep every recovery step run-scoped, resumable, and ledger-backed.
- Prefer small wrappers around existing scripts over deep refactors.
- Treat surviving external artifacts as either:
  - `authoritative_surviving`: safe bootstrap/reuse candidate, or
  - `reference_only`: helpful comparison input but not authoritative for versioned rebuild.

## 3) Runtime Layout

Canonical runtime layout:

```text
/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/
  data_recovery/
    site=11160500/
      recovery_run=<RUN_ID>/
        commands/
          paths.sh
        logs/
        manifests/
          run_manifest.json
        provenance/
          bootstrap_artifacts_inventory.csv
        status/
          README.txt
        family=nwm_retrospective/
          manifests/
          logs/
          outputs/
          smoke/
          health_checks/
          audits/
          provenance/
        family=glofas_historical/
          manifests/
          logs/
          outputs/
          smoke/
          health_checks/
          audits/
          provenance/
        family=climate_covariates/
          manifests/
          logs/
          outputs/
          smoke/
          health_checks/
          audits/
          provenance/
        family=gefs_forecasts/
          manifests/
          logs/
          outputs/
          smoke/
          health_checks/
          audits/
          provenance/
        family=usgs_daily_flow/
          manifests/
          logs/
          outputs/
          smoke/
          health_checks/
          audits/
          provenance/
```

Initialization command:

```bash
python3 scripts/recovery_init_run.py --config config/recovery_site11160500.yaml
```

This writes:

- `commands/paths.sh`
- `manifests/run_manifest.json`
- `provenance/bootstrap_artifacts_inventory.csv`

Current initialized run:

- `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/data_recovery/site=11160500/recovery_run=site11160500_recovery_20260406T185022Z`
- status: layout initialized, bootstrap artifacts inventoried, no heavy backfills launched yet

## 4) Inventory

Legend:

- `ready_now`: current scripts can rebuild now with external-root wrappers
- `partial`: some implementation exists, but a cache, lineage decision, or wrapper is still missing
- `blocked`: known unresolved dependency or source ambiguity

| family | source | product | version(s) | variable(s) | spatial logic | temporal coverage | current script(s) | current status | fully rebuildable now | depends on missing local cache | important gaps / unknowns |
|---|---|---|---|---|---|---|---|---|---|---|---|
| NWM retrospective | NOAA NWM retrospective | channel point streamflow | `1.2` | `streamflow` | fixed `feature_id=17682474` for full run; target lat/lon only for pilot lookup | `1993-01-01` to `2017-12-31` | `scripts/nwm_retrospective_extract_point_v12_comp.py`, `scripts/run_nwm_v12_full_point_extraction.sh`, `scripts/nwm_retrospective_audit_point_series.py` | `partial` | `yes`, with year sharding | `no` | full run is expensive; wrapper now supports external run-base override, but no surviving authoritative full `v1.2` CSV was found |
| NWM retrospective | NOAA NWM retrospective | channel point streamflow | `2.0` | `streamflow` | nearest valid feature from Zarr; prior full run selected `feature_id=17682474` | `1993-01-01` to `2018-12-31` | `scripts/nwm_retrospective_extract_point_zarr.py`, `scripts/nwm_retrospective_audit_point_series.py`, `scripts/nwm_retrospective_build_unified_table.py` | `ready_now` | `yes` | `no` | point-series outputs were lost from repo-local cache and need rerun under external root |
| NWM retrospective | NOAA NWM retrospective | channel point streamflow | `2.1` | `streamflow` | nearest valid feature from Zarr; prior full run selected `feature_id=17682474` | `1979-02-01` to `2020-12-31` | `scripts/nwm_retrospective_extract_point_zarr.py`, `scripts/nwm_retrospective_audit_point_series.py`, `scripts/nwm_retrospective_build_unified_table.py` | `ready_now` | `yes` | `no` | external surviving hourly CSV backup exists and can be reused instead of redownload if desired |
| NWM retrospective | NOAA NWM retrospective | channel point streamflow | `3.0` | `streamflow` | nearest valid feature from Zarr; prior full run selected `feature_id=17682474` | `1979-02-01` to `2023-01-31` | `scripts/nwm_retrospective_extract_point_zarr.py`, `scripts/nwm_retrospective_audit_point_series.py`, `scripts/nwm_retrospective_build_unified_table.py` | `ready_now` | `yes` | `no` | external surviving hourly CSV backup exists; backup has trailing `2023-02-01 00:00` timestamp and should be trimmed explicitly |
| NWM retrospective (auxiliary) | local `results.pkl` archive | synthetic daily retrospective from operational forecasts | forecast-era synthetic | daily `discharge_cms` | parsed from archived forecast keys, not source-native retrospective grid/feature mapping | depends on `results.pkl` coverage | `scripts/nwm_build_synthetic_retrospective_from_results.py` | `blocked` | `no` | `yes` | `results.pkl` is not present in current workspace or nearby external paths inspected so far |
| NWM retrospective (auxiliary) | lost `forecast_cache/nws` | strict day+1 synthetic retrospective | forecast-cache synthetic | daily `discharge_cms` | derived from `forecast_cache/nws/cutoff_date=.../nws_members.csv` | depends on surviving cache horizon | `scripts/nwm_build_synthetic_retrospective_from_nws_daily_cache.py` | `blocked` | `no` | `yes` | repo-local `data/forecats_cache/.../forecast_cache/nws` is gone |
| GLOFAS historical | EWDS historical | consolidated historical point campaign | `version_2_1 + htessel_lisflood + consolidated` | `river_discharge_in_the_last_24_hours` | small bbox download plus nearest valid cell point extraction | audit-confirmed `1979-01-01` to `2022-07-31` | `scripts/forecats_download_glofas_historical_consolidated.py`, `scripts/forecats_validate_glofas_historical_boundaries.py`, `scripts/forecats_extract_glofas_historical_point.py` | `ready_now` | `yes` | `no` | output zips and extracted point CSVs were lost and must be rebuilt under external root |
| GLOFAS historical | EWDS historical | consolidated historical point campaign | `version_3_1 + lisflood + consolidated` | `river_discharge_in_the_last_24_hours` | small bbox download plus nearest valid cell point extraction | audit-confirmed `1979-01-01` to `2024-06-30` | `scripts/forecats_download_glofas_historical_consolidated.py`, `scripts/forecats_validate_glofas_historical_boundaries.py`, `scripts/forecats_extract_glofas_historical_point.py` | `ready_now` | `yes` | `no` | run under external root; do not assume parity with legacy `v3.0` |
| GLOFAS historical | EWDS historical | consolidated historical point campaign | `version_4_0 + lisflood + consolidated` | `river_discharge_in_the_last_24_hours` | small bbox download plus nearest valid cell point extraction | audit-confirmed `1979-01-01` to `2025-11-30` | `scripts/forecats_download_glofas_historical_consolidated.py`, `scripts/forecats_validate_glofas_historical_boundaries.py`, `scripts/forecats_extract_glofas_historical_point.py` | `ready_now` | `yes` | `no` | use explicit `version_4_0` label; do not silently substitute legacy v4 naming |
| GLOFAS historical | JRC legacy archive | legacy reanalysis point series | `legacy v3.0` | legacy discharge variable (`dis24`/equivalent) | global NetCDF direct download plus nearest valid point extraction | `1980-01-01` to `2018-12-31` | `scripts/run_legacy_glofas_downloads.sh`, `scripts/forecats_extract_legacy_glofas_point.py` | `ready_now` | `yes` | `no` | direct URL is confirmed; should be relocated to external runtime storage before use |
| GLOFAS historical | JRC legacy archive / unresolved direct URL | legacy reanalysis point series | `legacy v4.0` | legacy discharge variable | direct-file workflow unresolved; fallback may require EWDS/service path | target metadata says `1980-01-01` to `2022-07-31` | `scripts/run_legacy_glofas_downloads.sh`, `scripts/forecats_extract_legacy_glofas_point.py` | `blocked` | `no` | `no` | direct URL unresolved; parity vs EWDS `version_4_0` remains open |
| GLOFAS historical (reference-only) | old local project artifacts | unversioned local historical series | unclear | discharge | prior local point series / yearly GRIBs | unclear lineage | external paths listed in `config/recovery_site11160500.yaml` | `partial` | `not_as_authoritative_source` | `no` | useful bootstrap/comparison only until lineage is proven |
| Climate covariates | PRISM | daily precipitation point series | resolution `4km` by current script default | `PRCP_mm` | raster extract at target lat/lon | current surviving CSV `1987-01-01` to `2023-12-31`; script can request broader window until data unavailability | `scripts/build_prism_ppt_point_series.R` | `ready_now` | `yes` | `no` | current script deletes downloads unless `--keep-downloads`; needs external-root wrapper |
| Climate covariates | ERA5-Land | daily soil-moisture point series | `volumetric_soil_water_layer_1` | daily mean soil moisture | nearest ERA5 grid point within small bbox | current surviving CSV `1987-01-01` to `2023-12-31`; script supports later end dates | `scripts/build_era5_soil_moisture_point_series.py`, `scripts/update_soil_incremental.sh` | `ready_now` | `yes` | `no` | script deletes monthly NetCDF by default and prints failures without a persistent ledger |
| Climate covariates (auxiliary) | NWM retrospective LDAS | daily soil point series | v3.0 retrospective LDAS | `SOIL_M`, `SOIL_W` | NWM Lambert grid projection plus nearest valid cell | `1987-01-01` to present dataset end | `scripts/build_nwm_retro_soil_point_series.py`, `scripts/update_nwm_soil_retro_full.sh` | `ready_now` | `yes` | `no` | not one of the two requested canonical climate covariates, but useful for same-unit soil comparisons |
| GEFS forecasts | NOAA GEFS archive | point forecast extraction | `00z` cycle across requested five init dates | `APCP`, all available `SOILW` layers | GRIB nearest valid cell; byte-range message extraction via `.idx` | init dates `2021-01-23`, `2021-11-12`, `2021-12-21`, `2022-05-11`, `2022-12-25` | `scripts/build_gefs_nwm_forecast_manifest.py`, `scripts/gefs_nwm_point_smoke_extract.py`, `scripts/extract_gefs_nwm_forecast_points.py`, `scripts/check_gefs_nwm_forecast_extract_health.py`, `scripts/consolidate_gefs_nwm_forecast_handoff.py` | `ready_now` | `yes` | `no` | previous repro run directory is gone, but manifests and extracts can be rebuilt from public cloud without local cache |
| USGS daily flow | USGS NWIS daily values | daily observed streamflow | NWIS `00060/00003` | `discharge_cfs`, `discharge_cms` | site-code query, no spatial lookup | `1979-01-01` to requested end date | `R/environmetrics/10_data_inputs.R`, `scripts/forecats_pipeline.R`, `scripts/forecats_batch.R`, `scripts/fetch_usgs_daily_flow.py` | `ready_now` | `yes` | `no` | the repo previously relied on implicit runtime fetches; `scripts/fetch_usgs_daily_flow.py` now provides explicit materialization |

## 5) Readiness Summary

Already redownloadable automatically now:

- NWM retrospective `v1.2`, `v2.0`, `v2.1`, `v3.0`
- GLOFAS historical `version_2_1`, `version_3_1`, `version_4_0`
- Legacy GLOFAS `v3.0`
- PRISM precipitation
- ERA5 soil moisture
- GEFS precipitation and soil-moisture forecasts
- USGS daily flow

Rebuildable from surviving local artifacts now:

- NWM retrospective `v2.1` and `v3.0` from surviving backup hourly point CSVs
- PRISM, ERA5, and NWM retrospective soil from surviving external CSVs
- shared bundle reference tables outside repo root

Only partially supported:

- legacy local GLOFAS point/GRIB artifacts with unclear version lineage
- NWM auxiliary synthetic retrospectives that require missing cache products
- PRISM and ERA5 scripts need safer external-root wrappers and persistent run ledgers

Blocked:

- legacy GLOFAS `v4.0` direct-file parity workflow
- NWM synthetic retrospective from missing `results.pkl`
- NWM synthetic retrospective from missing repo-local `forecast_cache/nws`

## 6) Commands

Initialize the run-scoped runtime layout:

```bash
python3 scripts/recovery_init_run.py --config config/recovery_site11160500.yaml
source /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/data_recovery/site=11160500/recovery_run=<RUN_ID>/commands/paths.sh
```

### 6.1 NWM Retrospective

Metadata-first manifest with external backup inventory:

```bash
python3 scripts/nwm_retrospective_build_manifest.py \
  --run-root "${RECOVERY_FAMILY_NWM_RETROSPECTIVE_ROOT}" \
  --run-id "nwm_retrospective_manifest" \
  --local-known "2.1=/data/muscat_data/jaguir26/project1_ucsc_phd_BACKUP_20260121_010041/11160500_nws_retro_old.csv" \
  --local-known "3.0=/data/muscat_data/jaguir26/project1_ucsc_phd_BACKUP_20260121_010041/11160500_nws_retro.csv"
```

Zarr versions:

```bash
python3 scripts/nwm_retrospective_extract_point_zarr.py \
  --zarr-url "s3://noaa-nwm-retrospective-3-0-pds/CONUS/zarr/chrtout.zarr" \
  --version "3.0" \
  --lat 37.0443931 \
  --lon -122.072464 \
  --start-date 1979-02-01 \
  --end-date 2023-01-31 \
  --aggregate daily \
  --aggregation-scale log_log1p_cms \
  --out-csv "${RECOVERY_FAMILY_NWM_RETROSPECTIVE_ROOT}/outputs/v30_full_daily.csv" \
  --out-meta "${RECOVERY_FAMILY_NWM_RETROSPECTIVE_ROOT}/logs/v30_full_meta.json"
```

Use the same pattern for:

- `v2.1`: `s3://noaa-nwm-retrospective-2-1-zarr-pds/chrtout.zarr`, `1979-02-01` to `2020-12-31`
- `v2.0`: `s3://noaa-nwm-retro-v2-zarr-pds`, `1993-01-01` to `2018-12-31`

`v1.2` yearly shards:

```bash
for Y in $(seq 1993 2017); do
  python3 scripts/nwm_retrospective_extract_point_v12_comp.py \
    --bucket nwm-archive \
    --version 1.2 \
    --lat 37.0443931 \
    --lon -122.072464 \
    --feature-id 17682474 \
    --start-date "${Y}-01-01" \
    --end-date "${Y}-12-31" \
    --aggregate daily \
    --aggregation-scale log_log1p_cms \
    --out-csv "${RECOVERY_FAMILY_NWM_RETROSPECTIVE_ROOT}/outputs/v12_yearly/v12_${Y}_daily.csv" \
    --out-meta "${RECOVERY_FAMILY_NWM_RETROSPECTIVE_ROOT}/logs/v12_yearly/v12_${Y}_meta.json" \
    --missing-hours-csv "${RECOVERY_FAMILY_NWM_RETROSPECTIVE_ROOT}/logs/v12_yearly/v12_${Y}_missing_hours.csv"
done
```

Audit and unify:

```bash
python3 scripts/nwm_retrospective_audit_point_series.py \
  --inputs "${RECOVERY_FAMILY_NWM_RETROSPECTIVE_ROOT}/outputs/v20_full_daily.csv" \
  --labels "v20_full" \
  --expected-start 1993-01-01 \
  --expected-end 2018-12-31 \
  --out-summary-csv "${RECOVERY_FAMILY_NWM_RETROSPECTIVE_ROOT}/audits/v20_full_audit_summary.csv" \
  --out-missing-dir "${RECOVERY_FAMILY_NWM_RETROSPECTIVE_ROOT}/audits/v20_missing" \
  --out-summary-json "${RECOVERY_FAMILY_NWM_RETROSPECTIVE_ROOT}/audits/v20_full_audit_summary.json"

python3 scripts/nwm_retrospective_build_unified_table.py \
  --v12 "${RECOVERY_FAMILY_NWM_RETROSPECTIVE_ROOT}/outputs/v12_full_daily.csv" \
  --v20 "${RECOVERY_FAMILY_NWM_RETROSPECTIVE_ROOT}/outputs/v20_full_daily.csv" \
  --v21 "${RECOVERY_FAMILY_NWM_RETROSPECTIVE_ROOT}/outputs/v21_full_daily.csv" \
  --v30 "${RECOVERY_FAMILY_NWM_RETROSPECTIVE_ROOT}/outputs/v30_full_daily.csv" \
  --out-csv "${RECOVERY_FAMILY_NWM_RETROSPECTIVE_ROOT}/outputs/nwm_unified_daily.csv"
```

### 6.2 GLOFAS Historical

Plan only:

```bash
python3 scripts/forecats_download_glofas_historical_consolidated.py \
  --out-root "${RECOVERY_FAMILY_GLOFAS_HISTORICAL_ROOT}/outputs/historical_zips" \
  --plan-root "${RECOVERY_FAMILY_GLOFAS_HISTORICAL_ROOT}/manifests" \
  --focus-start 1987-05-29 \
  --focus-end 2023-05-01
```

Boundary validation:

```bash
python3 scripts/forecats_validate_glofas_historical_boundaries.py \
  --out-root "${RECOVERY_FAMILY_GLOFAS_HISTORICAL_ROOT}/manifests/boundary_checks" \
  --run
```

Download selected/full shards only after smoke approval:

```bash
python3 scripts/forecats_download_glofas_historical_consolidated.py \
  --out-root "${RECOVERY_FAMILY_GLOFAS_HISTORICAL_ROOT}/outputs/historical_zips" \
  --plan-root "${RECOVERY_FAMILY_GLOFAS_HISTORICAL_ROOT}/manifests" \
  --focus-start 1987-05-29 \
  --focus-end 2023-05-01 \
  --run
```

Extract point series from completed campaign:

```bash
python3 scripts/forecats_extract_glofas_historical_point.py \
  --campaign-root "${RECOVERY_FAMILY_GLOFAS_HISTORICAL_ROOT}/outputs/historical_zips/hist_v31_lisflood_cons" \
  --out-csv "${RECOVERY_FAMILY_GLOFAS_HISTORICAL_ROOT}/outputs/hist_v31_lisflood_cons_point.csv" \
  --out-meta "${RECOVERY_FAMILY_GLOFAS_HISTORICAL_ROOT}/logs/hist_v31_lisflood_cons_point_meta.json" \
  --lat 37.0443931 \
  --lon -122.072464 \
  --cell-policy nearest_valid
```

Legacy `v3.0` direct file:

```bash
bash scripts/run_legacy_glofas_downloads.sh \
  "${RECOVERY_FAMILY_GLOFAS_HISTORICAL_ROOT}/outputs/glofas_legacy_global" \
  "${RECOVERY_FAMILY_GLOFAS_HISTORICAL_ROOT}/logs/glofas_legacy_global"
python3 scripts/forecats_extract_legacy_glofas_point.py \
  --input-nc "${RECOVERY_FAMILY_GLOFAS_HISTORICAL_ROOT}/outputs/glofas_legacy_global/dis_1980_2018_v3_legacy.nc" \
  --out-csv "${RECOVERY_FAMILY_GLOFAS_HISTORICAL_ROOT}/outputs/dis_1980_2018_v3_legacy_bigtrees.csv" \
  --out-meta "${RECOVERY_FAMILY_GLOFAS_HISTORICAL_ROOT}/logs/dis_1980_2018_v3_legacy_bigtrees_meta.json" \
  --lat 37.0443931 \
  --lon -122.072464
```

### 6.3 Climate Covariates

PRISM dry run:

```bash
Rscript --vanilla scripts/build_prism_ppt_point_series.R \
  --start-date 1987-01-01 \
  --end-date 2023-12-31 \
  --lat 37.0443931 \
  --lon -122.072464 \
  --download-dir "${RECOVERY_FAMILY_CLIMATE_COVARIATES_ROOT}/outputs/prism_work" \
  --output-csv "${RECOVERY_FAMILY_CLIMATE_COVARIATES_ROOT}/outputs/prism_precipitation_santa_cruz_1987_2023.csv" \
  --dry-run
```

ERA5 dry run:

```bash
python3 scripts/build_era5_soil_moisture_point_series.py \
  --start-date 1987-01-01 \
  --end-date 2023-12-31 \
  --lat 37.0443931 \
  --lon -122.072464 \
  --tmp-dir "${RECOVERY_FAMILY_CLIMATE_COVARIATES_ROOT}/outputs/era5_tmp" \
  --daily-csv "${RECOVERY_FAMILY_CLIMATE_COVARIATES_ROOT}/outputs/soil_moisture_big_trees_daily_avg_1987_2023.csv" \
  --keep-monthly \
  --dry-run
```

NWM retrospective soil:

```bash
python3 scripts/build_nwm_retro_soil_point_series.py \
  --lat 37.0443931 \
  --lon -122.072464 \
  --start-date 1987-01-01 \
  --end-date 2023-12-31 \
  --soil-layer-index 0 \
  --out-csv "${RECOVERY_FAMILY_CLIMATE_COVARIATES_ROOT}/outputs/nwm_soil_moisture_big_trees_daily_1987_present.csv" \
  --out-meta "${RECOVERY_FAMILY_CLIMATE_COVARIATES_ROOT}/logs/nwm_soil_moisture_big_trees_daily_1987_present.meta.json"
```

Status summary:

```bash
python3 scripts/write_climate_series_status.py \
  --root-dir "${RECOVERY_FAMILY_CLIMATE_COVARIATES_ROOT}/outputs" \
  --target-date 2023-12-31 \
  --output-csv "${RECOVERY_FAMILY_CLIMATE_COVARIATES_ROOT}/health_checks/climate_series_status.csv"
```

### 6.4 GEFS Forecasts

Manifest only:

```bash
python3 scripts/build_gefs_nwm_forecast_manifest.py \
  --run-root "${RECOVERY_FAMILY_GEFS_FORECASTS_ROOT}" \
  --site-config config/forecats_pipeline.template.yaml \
  --dates "2021-01-23,2021-11-12,2021-12-21,2022-05-11,2022-12-25" \
  --gefs-cycle 00 \
  --nwm-cycle 00
```

Smoke extraction:

```bash
python3 scripts/gefs_nwm_point_smoke_extract.py \
  --manifest-run-dir "${RECOVERY_FAMILY_GEFS_FORECASTS_ROOT}/manifests/<MANIFEST_RUN_ID>" \
  --site-config config/forecats_pipeline.template.yaml \
  --gefs-init-date 2021-01-23 \
  --nwm-init-date 2021-11-12 \
  --gefs-cycle 0 \
  --nwm-cycle 0
```

Full GEFS extraction after smoke approval:

```bash
python3 scripts/extract_gefs_nwm_forecast_points.py \
  --manifest-run-dir "${RECOVERY_FAMILY_GEFS_FORECASTS_ROOT}/manifests/<MANIFEST_RUN_ID>" \
  --out-subdir extract_gefs_full \
  --sources gefs \
  --gefs-workers 16 \
  --batch-size 512 \
  --gefs-file-retries 3
```

Health check:

```bash
python3 scripts/check_gefs_nwm_forecast_extract_health.py \
  --manifest-run-dir "${RECOVERY_FAMILY_GEFS_FORECASTS_ROOT}/manifests/<MANIFEST_RUN_ID>" \
  --gefs-out-subdir extract_gefs_full
```

### 6.5 USGS Daily Flow

Dry run:

```bash
python3 scripts/fetch_usgs_daily_flow.py \
  --site-id 11160500 \
  --start-date 1979-01-01 \
  --end-date 2026-04-06 \
  --out-csv "${RECOVERY_FAMILY_USGS_DAILY_FLOW_ROOT}/outputs/usgs_daily_flow_11160500.csv" \
  --out-meta "${RECOVERY_FAMILY_USGS_DAILY_FLOW_ROOT}/logs/usgs_daily_flow_11160500.meta.json" \
  --dry-run
```

Materialize:

```bash
python3 scripts/fetch_usgs_daily_flow.py \
  --site-id 11160500 \
  --start-date 1979-01-01 \
  --end-date 2026-04-06 \
  --out-csv "${RECOVERY_FAMILY_USGS_DAILY_FLOW_ROOT}/outputs/usgs_daily_flow_11160500.csv" \
  --out-meta "${RECOVERY_FAMILY_USGS_DAILY_FLOW_ROOT}/logs/usgs_daily_flow_11160500.meta.json"
```

## 7) Smoke / Full / Health Checklist

| family | smoke test | smoke status | full run status | health status | blocking note |
|---|---|---|---|---|---|
| NWM retrospective | one short-range Zarr pilot per version + `v1.2` two-day pilot | existing historical evidence only; rerun pending under external root | not started in new runtime root | not started in new runtime root | `v1.2` full sharded run remains the longest lane |
| GLOFAS historical | one day or one month per product; use existing probe zips where possible | existing historical evidence only; rerun pending under external root | not started in new runtime root | not started in new runtime root | legacy `v4.0` direct file blocked |
| Climate covariates | PRISM dry-run, ERA5 dry-run, NWM soil short extraction | pending | not started in new runtime root | not started in new runtime root | need external-root wrappers and ledgers |
| GEFS forecasts | manifest build + one-date smoke extraction | prior repo-local evidence exists; rerun pending under external root | not started in new runtime root | not started in new runtime root | previous run directory missing |
| USGS daily flow | explicit dry-run URL and one real fetch into runtime root | pending | not started in new runtime root | schema/date-range check pending | standalone materializer added, not yet executed |

## 8) Immediate Next Steps

1. Initialize the runtime run root and record the bootstrap artifact inventory.
2. Rebuild metadata-only manifests first:
   - NWM retrospective manifest
   - GLOFAS historical plan
   - GEFS manifest
3. Run one smoke test per family under the external runtime root.
4. Review smoke outputs for:
   - location/cell/feature identity
   - version/product label correctness
   - schema and units
   - coverage framing
5. Only then approve full backfills.
