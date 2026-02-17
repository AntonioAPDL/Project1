# Legacy GloFAS Reanalysis Download and Point-Extraction Plan

Last updated: 2026-02-17

## 1) Objective

Prepare robust, resumable workflows for two large legacy global reanalysis assets and a fixed-cell point extraction pipeline for Big Trees (`lat=37.0443931`, `lon=-122.072464`).

## 2) Source Status

### 2.1 v3.0 legacy global NetCDF (confirmed direct URL)

- URL: `https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/CEMS-GLOFAS-RA/streamflow_analysis/LATEST/dis_1980_2018.nc`
- HEAD check: HTTP 200 and `content-length: 73345627590` bytes (~68.3 GiB).

### 2.2 v4.0 legacy global asset (direct URL unresolved)

- JRC dataset page metadata indicates distribution type `WEB_SERVICE` with access URL to EWDS dataset page, not a direct `.nc` file.
- Current status: no stable direct `.nc` URL confirmed from primary JRC/JEODPP evidence.
- Evidence bundle:
  - `repro/glofas_probe_runs/legacy_url_resolution_20260217T020444Z/summary.txt`
  - `repro/glofas_probe_runs/legacy_url_resolution_20260217T020444Z/jrc_v4_rdf_distribution_lines.txt`
  - `repro/glofas_probe_runs/legacy_url_resolution_20260217T020444Z/jeodpp_ra_latest_index.html`

## 3) Preflight Capacity Snapshot

- `/data` free space: ~314 GB available (captured during preflight).
- This is sufficient for one ~68 GB file + working scratch for extraction.
- If both v3 and v4 large global files are stored simultaneously, still feasible but monitor headroom.

## 4) Download Strategy

### 4.1 v3 direct file

- Use resumable `curl -C -` with retry/backoff.
- Run in background (`nohup`) and monitor logs.
- Command template: `scripts/run_legacy_glofas_downloads.sh`.

### 4.2 v4 fallback path

Because direct `.nc` link is unresolved, use one of:
1. Resolve direct URL through data provider support and then run same resumable flow as v3.
2. Use EWDS API campaign fallback (global area, chunked temporal requests) and assemble equivalent archive locally.
3. Keep this as an explicit service-path workflow in provenance metadata (do not label as direct-file parity unless a true direct URL is later confirmed).

## 5) Integrity and Validation

After download completion:

```bash
sha256sum data/glofas_legacy_global/dis_1980_2018_v3_legacy.nc > data/glofas_legacy_global/dis_1980_2018_v3_legacy.nc.sha256
ncdump -h data/glofas_legacy_global/dis_1980_2018_v3_legacy.nc | head -n 80
```

For resumed downloads, verify file size stability after completion and confirm checksum generated once.

## 6) Point Extraction Protocol

Script: `scripts/forecats_extract_legacy_glofas_point.py`

Behavior:
1. Opens legacy NetCDF.
2. Resolves coordinate and discharge variable names.
3. Finds nearest non-NaN grid cell to target location.
4. Fixes that cell and exports full time series to CSV.
5. Writes cell metadata JSON (indices, coordinates, distance, date range).

Example:

```bash
python3 scripts/forecats_extract_legacy_glofas_point.py \
  --input-nc data/glofas_legacy_global/dis_1980_2018_v3_legacy.nc \
  --out-csv repro/glofas_probe_runs/legacy_point_v3_1980_2018.csv \
  --out-meta repro/glofas_probe_runs/legacy_point_v3_1980_2018.meta.json \
  --lat 37.0443931 --lon -122.072464
```

## 7) Output Schema (for harmonization)

Recommended extracted CSV fields:
- `date`
- `discharge_cms`

Recommended metadata JSON fields:
- `input_nc`, `variable`
- `lat_coord_name`, `lon_coord_name`
- `target_lat`, `target_lon`
- `cell_lat_index`, `cell_lon_index`
- `cell_lat`, `cell_lon_raw`, `cell_lon_m180_180`
- `distance_km`
- `n_rows`, `start_date`, `end_date`

## 8) Operational Notes

- Keep a single fixed cell per legacy product once selected.
- Store extraction metadata and checksum files next to outputs.
- Do not delete partial `.nc` during interrupted downloads; resume from existing file.
