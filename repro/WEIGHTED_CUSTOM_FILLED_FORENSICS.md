# `weighted_time_series_custom_filled.csv` Forensics Report

Date: 2026-02-07  
Repo: `/data/muscat_data/jaguir26/project1_ucsc_phd`

## Objective

Use the old ChatGPT transcript as a clue source and verify, with repo evidence, whether we can identify how `weighted_time_series_custom_filled.csv` was produced.

## Clues from the old transcript

The historical workflow indicates:

1. `consolidated_glofas_data.csv` was extracted from GRIB files.
2. A weighted-by-lead-time ensemble table was computed and pivoted into:
   - `weighted_time_series_custom.csv`
3. A missing combination was found (`target_date=2022-10-25`, `ensemble_member=0`).
4. A fill step was applied and saved as:
   - `weighted_time_series_custom_filled.csv`

## What exists in this repo today

1. `glofas_forecasts.ipynb` contains code to:
   - build `consolidated_glofas_data.csv`
   - compute weighted custom series
   - write `weighted_time_series_custom.csv`
2. No script/notebook cell in the repo writes `weighted_time_series_custom_filled.csv`.
3. Both CSV files are present on disk but ignored by git (`.gitignore` includes `*.csv`), so git history cannot identify origin commit.

## Hard evidence from artifact comparison

Using `weighted_time_series_custom.csv` vs `weighted_time_series_custom_filled.csv`:

1. Shapes differ:
   - custom: `(151, 52)`
   - filled: `(242, 52)`
2. Date range differs:
   - custom: `2022-08-25` to `2023-01-22`
   - filled: `2022-08-25` to `2023-04-23`
3. Common-date overlap: `151` dates.
4. Cell-level differences on overlap:
   - `na->value`: `1`
   - `value->na`: `0`
   - non-NaN value changes: `7469`

Conclusion: the `filled` file is **not** a simple one-cell NaN patch; it includes broader undocumented transformations plus an extended horizon.

## Root-cause assessment

`weighted_time_series_custom_filled.csv` is a legacy artifact with missing provenance in the current repo:

1. We can reproduce `weighted_time_series_custom.csv` from notebook logic.
2. We cannot reconstruct the exact generation path for `*_filled.csv` from tracked code.
3. The old transcript explains one symptom (single missing pair) but does not explain the full transformed artifact we have today.

## Decision (recommended and consistent with current pipeline docs)

1. Keep treating `weighted_time_series_custom_filled.csv` as legacy parity-only input.
2. Use raw-data reproducible pipeline as canonical:
   - `scripts/forecats_build_glofas_weighted.py`
   - `scripts/forecats_pipeline.R`
   - `scripts/forecats_plot_bundle.R`

## New reproducible tool added

To make this forensic check rerunnable:

- `scripts/forensics_weighted_custom_filled.py`

Example:

```bash
python3 scripts/forensics_weighted_custom_filled.py \
  --custom weighted_time_series_custom.csv \
  --filled weighted_time_series_custom_filled.csv \
  --out-json repro/reports/weighted_custom_filled_forensics.json
```

The JSON report captures shapes, date coverage, overlap deltas, and top changed dates.
