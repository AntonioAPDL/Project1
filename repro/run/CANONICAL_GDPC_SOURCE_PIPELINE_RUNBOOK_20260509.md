# Canonical GDPC Source Pipeline Runbook

Date: 2026-05-09
Scope: source acquisition and daily post-processing only. This runbook does not fit GDPC yet.

## Purpose

This runbook documents the new canonical climate-index source pipeline that prepares the daily standardized climate matrix later used to fit the master `GDPC1` covariate.

The pipeline now has a clean, reproducible shape:
1. download the canonical 17 monthly climate-index source files,
2. parse and preserve them as normalized monthly CSVs,
3. build the canonical daily interpolated matrix on `1987-05-29 -> 2023-01-22`,
4. standardize the daily matrix,
5. audit the standardized matrix for trend/stationarity compatibility,
6. write metadata, validation, and review outputs.

## Canonical config

- `config/canonical_gdpc_master_covariate.yaml`

This config freezes:
- the 17-index source set,
- the canonical daily window,
- the monthly source window,
- the interpolation contract,
- and the standardization contract.

## Entry points

Downloader:
- `scripts/download_canonical_climate_indices.py`

Post-processor:
- `scripts/build_canonical_climate_daily_matrices.py`

One-shot wrapper:
- `scripts/run_canonical_climate_index_pipeline.py`

Pre-GDPC stationarity audit:
- `scripts/build_canonical_climate_stationarity_audit.R`

## Canonical output root

- `data/canonical_gdpc_master/v20260509/`

Key outputs:
- `inputs/raw_psl_text/`
- `inputs/monthly_csv/`
- `intermediate/combined_climate_indices_daily_19870529_20230122.csv`
- `intermediate/combined_climate_indices_daily_standardized_19870529_20230122.csv`
- `metadata/source_manifest.csv`
- `metadata/validation_summary.json`
- `review/CANONICAL_CLIMATE_INDEX_DOWNLOAD_REVIEW.md`
- `review/CANONICAL_CLIMATE_INDEX_POSTPROCESS_REVIEW.md`
- `review/stationarity/CANONICAL_GDPC_STATIONARITY_AUDIT.md`
- `review/stationarity/stationarity_audit.csv`

## Recommended command

```bash
python3 scripts/run_canonical_climate_index_pipeline.py \
  --config config/canonical_gdpc_master_covariate.yaml
```

To force redownload of the raw monthly source files:

```bash
python3 scripts/run_canonical_climate_index_pipeline.py \
  --config config/canonical_gdpc_master_covariate.yaml \
  --force-download
```

To rerun the pre-GDPC stationarity audit explicitly:

```bash
Rscript scripts/build_canonical_climate_stationarity_audit.R \
  --input-csv data/canonical_gdpc_master/v20260509/intermediate/combined_climate_indices_daily_standardized_19870529_20230122.csv \
  --output-dir data/canonical_gdpc_master/v20260509/review/stationarity \
  --window-label "1987-05-29 -> 2023-01-22"
```

## Validation expectation

After a successful run:
- all 17 monthly source files should exist,
- `metadata/source_manifest.csv` should list all 17 indices,
- the raw and standardized daily matrices should cover `1987-05-29 -> 2023-01-22`,
- the stationarity audit should confirm the full 17-series block is retained in levels for GDPC,
- and the review markdown files should summarize coverage and standardization behavior clearly.

## Important boundary

This pipeline does not fit `gdpc()` yet.
It prepares the exact source and post-processed daily matrix that the later GDPC phase will consume.
