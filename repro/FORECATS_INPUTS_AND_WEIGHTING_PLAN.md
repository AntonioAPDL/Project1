# `forecats.png` Inputs + Ensemble Weighting (Current State + Repro Plan)

Last updated: 2026-02-06

## 0) Why this document exists

You have a working (but currently hard-coded) pipeline that:

1) assembles observed + retrospective daily river flow (USGS + GloFAS retro + NWS/NWM retro),
2) assembles **post-processed** forecast ensembles (GloFAS + NWS/NWM),
3) produces the figure:
   - `Environmetrics_reproduce/forecats.png`
   - titled: **"Observed and Retrospective River Flow with GloFAS and NWS Forecast Ensembles"**

Your goal is to have **full control** over this figure (and later, model inputs) by:

- picking a **cutoff/target date** (the last date with “known” observations/retros),
- rebuilding the exact figure inputs deterministically,
- storing them in a clean, queryable folder layout,
- (later) using that same bundle to fit any model automatically.

For now, this doc focuses on the **minimum data needed to reproduce `forecats.png`** and documents the current ensemble post-processing/weighting logic used to build those forecast inputs.

## 1) Terms (make the date logic explicit)

These four dates show up repeatedly; we should standardize language:

- **cutoff_date**: last date included in retrospective/observed history used for “fit” window (e.g. `2022-12-25`).
- **forecast_start_date**: first forecast *target* date shown “after” the cutoff (typically `cutoff_date + 1 day`, e.g. `2022-12-26`).
- **issue_date** (a.k.a. start_forecast): the date/time a forecast is initialized.
- **target_date**: the date the forecast is *valid for* (what you plot on the x-axis).

For GloFAS (per current notebook logic), `target_date` is derived from `(issue_date, lead_time)` with a **-1 day shift**:

```text
target_date = issue_date + lead_time - 1 day
```

This shift is used to align “discharge in the last 24 hours” (valid at 00:00) to the *previous* calendar day. It is a critical convention to keep consistent across the whole pipeline.

## 2) Where `forecats.png` is created (current truth)

The plot is constructed in:

- `R/environmetrics/40_figures.R`

The file is saved here:

- `Environmetrics_reproduce/forecats.png`

Code reference (exact save call):

- `R/environmetrics/40_figures.R:4960` (near the `ggsave(... forecats.png ...)` block)

Runner (recommended way to reproduce without overwriting canonical outputs):

- `scripts/run_environmetrics_figures.R`
  - runs the modular pipeline in order
  - redirects `ggsave/png/pdf/...` output into `Environmetrics_reproduce_script_runs/<RUN_ID>/`

## 3) What data `forecats.png` uses (as implemented today)

### 3.1 High-level: the figure is assembled from 3 sources

Within `R/environmetrics/40_figures.R`, the figure combines:

1) **USGS observed daily flow** (before + after the cutoff)  
2) **Retrospective daily flows** for GloFAS and NWS (before the cutoff)  
3) **Forecast ensemble members** (after the cutoff) for:
   - GloFAS (51 members)
   - NWS (7 members)

### 3.2 Concrete objects the plot depends on (in the R session)

The plot block expects these objects to exist (created upstream by `R/environmetrics/10_data_inputs.R`):

- `San_Lorenzo_Daily_USGS_R` (USGS daily time series; includes `time` and `X_00060_00003`)
- `Y` and `timestamps` (the retrospective “response” matrix and its dates)
- `ensembles` (list of 2 forecast matrices: GloFAS and NWS)
- `ranges` (forecast horizon lengths for each forecast matrix)

In the current pipeline, these are built by:

- `R/environmetrics/00_paths.R`
- `R/environmetrics/10_data_inputs.R`

### 3.3 Concrete input files currently used by the pipeline

Paths are centralized in:

- `R/environmetrics/00_paths.R`

The key inputs for `forecats.png` are:

- GloFAS weighted forecast (wide members):
  - `weighted_time_series.csv` (path: `GLOFAS_FORECAST_PATH`)
- NWS weighted forecast (wide members):
  - `nws_forecast.csv` (path: `NWS_FORECAST_PATH`)
- Retrospective daily series (USGS + NWS + GloFAS):
  - `retros_2022-12-25.csv` (path: `RETROS_PATH`)
- Live USGS observations are pulled at runtime via NWIS:
  - `readNWISdv(...)` inside `R/environmetrics/10_data_inputs.R`

## 4) Data transformations (the “double log” gotcha)

Today, the CSV inputs for retros/forecasts appear to already be on a **log1p** scale (values ~0–3.5 are consistent with `log(cms + 1)`).

Then, `R/environmetrics/10_data_inputs.R` applies **another log()**:

- NWS forecast:
  - `nws_forecast[,-1] <- log(nws_forecast[,-1])`
- GloFAS forecast:
  - `glofas_forecast[,-1] <- log(glofas_forecast[,-1])`
- Retrospective Y:
  - `Y <- log(Y)  # log-log, since already logged`
- USGS plotted values (inside `40_figures.R`) are computed as:
  - `log(log(cms + 1))`

So the figure is explicitly on a **log-log scale**:

```text
value_plotted = log( log( discharge_cms + 1 ) )
```

This can be totally valid, but it must be **explicitly documented and consistent**. The main risk is silently mixing:

- raw cms
- log1p(cms)
- log(log1p(cms))

### Recommendation (for reproducibility)

Pick one canonical storage scale for your “bundle”:

- Option A (recommended): store **raw cms** in all bundle CSVs, and apply transforms in plotting/model code.
- Option B: store **log1p(cms)**, but then never apply `log()` again unless you *explicitly* want log-log.

Right now, your stored inputs look like Option B, but your R pipeline applies the extra log() to force log-log.

## 5) Forecast post-processing (weighting) — what you described + what code does

You described (correctly) the key idea:

For a fixed **cutoff_date** D, and a fixed **forecast target date** T (e.g. T = D+1), you have *multiple forecasts* that verify at T:

- 1-step ahead forecast issued at D
- 2-step ahead forecast issued at D-1
- ...

Instead of taking only the most recent issue date, you compute a **weighted average** over all those available forecasts for the same target date (per ensemble member).

That is exactly what your notebooks implement, with different weight functions for GloFAS vs NWS.

### 5.1 GloFAS weighting (from `glofas_forecasts.ipynb`)

Code reference (search anchors):

- `glofas_forecasts.ipynb` contains:
  - `consolidated_df['target_date'] = ... - timedelta(days=1)`
  - `def weighted_avg(group, power): ... weights = lead_times ** power`

Core logic (as written in the notebook):

1) Compute `target_date` with the -1 day shift:

```python
target_date = start_forecast + to_timedelta(lead_time_hours) - 1 day
```

2) Transform:

```python
log_discharge = log(discharge + 1)
```

3) For each `(target_date, ensemble_member)` group, compute:

```text
weights_i = (lead_time_i) ** power
weights_i = weights_i / sum(weights_i)
weighted_average_log_discharge = sum_i weights_i * log_discharge_i
```

Where:

- `lead_time` is in hours (e.g. 24, 48, ..., 720)
- `power` is negative (e.g. `-1.001`), so **shorter lead times get more weight** (more recent issue dates).

4) Pivot to wide:

- index: `target_date`
- columns: `ensemble_member` (0..50)
- values: `weighted_average_log_discharge`

The resulting wide table is the conceptual parent of `weighted_time_series.csv`.

### 5.2 NWS weighting (from `Retro-Analysis.ipynb`)

Code reference (search anchors):

- `Retro-Analysis.ipynb` contains:
  - `def calculate_weight(ensemble_number, lead_time):`
  - `def process_nws_forecast(pkl_file_path, cutoff_date):`
  - `Target_Time = Date + to_timedelta(Lead_Time, unit='h')`

Core logic (as written in the notebook):

Inputs:

- A pickle `results.pkl` is parsed into a long table with columns:
  - `Date` (issue date)
  - `Ensemble_Number` (1..7)
  - `Lead_Time` (hours)
  - `Value` (flow in some base unit)

Steps:

1) Filter by cutoff:

```python
forecast_df = forecast_df[forecast_df["Date"] <= cutoff_date]
```

2) Define verification timestamp:

```python
Target_Time = Date + Lead_Time(hours)
```

3) Define weights (ensemble-dependent exponents):

```text
weight = 1 / (lead_time ** exponent_dict[member])
```

with:

```python
exponent_dict = {1:0, 2:0.3, 3:0.6, 4:0.9, 5:1.2, 6:1.5, 7:1.8}
```

4) Normalize weights within `(Target_Time, Ensemble_Number)` and compute:

```text
Transformed_Value = log1p(Value)
Weighted_Avg_Transformed_Value = sum_i Normalized_Weight_i * Transformed_Value_i
```

5) Downsample to daily:

- Convert `Target_Time` to calendar date, then daily mean per member.

The resulting wide daily table is the conceptual parent of `nws_forecast.csv`.

## 6) Minimum “data contract” to reproduce `forecats.png` for any cutoff_date

To make this reproducible, we want a bundle that is *explicitly parameterized* by:

- `site_code` (e.g. `11160500`)
- `cutoff_date` (e.g. `2022-12-25`)
- (optional) forecast horizon (e.g. 30 days for GloFAS medium-range)

### 6.1 Bundle contents (proposed)

For each `(site_code, cutoff_date)` create a folder (optionally nested by `run_id` so multiple runs can coexist):

```text
data/forecats_inputs/
  site=11160500/
    cutoff_date=2022-12-25/
      run_id=<RUN_ID>/
        meta.yaml
        inputs/
          usgs_daily.csv
          retros_daily.csv
          glofas_weighted_daily.csv
          nws_weighted_daily.csv
        figures/
          forecats.png
        logs/
          pipeline.log
```

Where:

- `meta.yaml` records:
  - site_code, lat/lon, units
  - cutoff_date, forecast_start_date
  - transformations (what scale is stored)
  - weighting method + parameters (power/exponents)
  - provenance pointers (file paths, commit hash, timestamps)

### 6.2 CSV schemas (keep them boring + explicit)

All CSVs written into a bundle are stored as **raw cms**.

`inputs/usgs_daily.csv`

- columns:
  - `date` (YYYY-MM-DD)
  - `discharge_cfs` (raw USGS daily mean discharge; what NWIS returns)
  - `discharge_cms` (converted to cms using `0.0283168466`)
- date range: covers what you need for plotting (pipeline fetches from `site.usgs.start_date` through `plot_end`)

`inputs/retros_daily.csv`

- columns:
  - `date`
  - `usgs_cms`
  - `glofas_cms`
  - `nws_cms`
- date range: continuous daily, ending exactly on `cutoff_date`

`inputs/glofas_weighted_daily.csv`

- columns: `target_date, member_00, member_01, ..., member_50`
- date range: `forecast_start_date..plot_end` (inclusive)

`inputs/nws_weighted_daily.csv`

- columns: `target_date, member_01, ..., member_07`
- date range: `forecast_start_date..plot_end` (inclusive); values may be NA beyond NWS maximum lead time

`inputs/glofas_cell.json`

- metadata about the chosen nearest valid river cell for GloFAS extraction (lat/lon indices, distance, reference issue date)

## 6.3 Implemented Bundle + YAML-Driven Pipeline (now in repo)

The repo now contains a *fully controlled* (YAML-driven) bundle pipeline that builds inputs
and produces the `forecats.png`-style figure without relying on hard-coded dates in
`R/environmetrics/*`.

### Quickstart (recommended workflow)

1) Copy the template config:

```bash
cp config/forecats_pipeline.template.yaml config/forecats_pipeline.yaml
```

2) Edit `config/forecats_pipeline.yaml`:

- set `dates.cutoff_date`, `dates.plot_start`, `dates.plot_end`
- set `site.usgs_site`, `site.lat`, `site.lon`
- decide whether NWS comes from `inputs.nws.source: csv` (fast, limited) or `pickle` (general)
- ensure `inputs.glofas.grib.grib_root` points to your downloaded operational GRIB directory

3) Run the pipeline:

```bash
Rscript scripts/forecats_pipeline.R --config config/forecats_pipeline.yaml
```

This creates a bundle under:

```text
data/forecats_inputs/site=<USGS_SITE>/cutoff_date=<YYYY-MM-DD>/run_id=<RUN_ID>/
```

and writes the figure:

```text
.../figures/forecats.png
```

### Example run (validated)

This was executed successfully on jerez (user `jaguir26`) for a December cutoff date:

- cutoff_date: `2020-12-20`
- plot window: `2020-12-01 .. 2021-01-04`
- config:
  - `config/forecats_pipeline.example_dec2020.yaml`
- output bundle:
  - `data/forecats_inputs/site=11160500/cutoff_date=2020-12-20/run_id=20260204_225904/`
- produced figure:
  - `data/forecats_inputs/site=11160500/cutoff_date=2020-12-20/run_id=20260204_225904/figures/forecats.png`

Notes:

- This run used `inputs.nws.source: pickle` (from `results.pkl`), so it generalizes to arbitrary cutoff dates.
- It is normal for some ensemble member/time combinations to be NA (upstream forecast availability); ggplot will drop missing segments.

### Example run (validated): paper-mode vs notebook-mode comparison (Dec 2022)

To compare the weighting scheme described in the paper vs the current notebook-derived weighting,
two bundles were built for the same cutoff date:

- cutoff_date: `2022-12-25`
- plot window: `2022-12-07 .. 2023-01-22`
- both use:
  - GloFAS source: operational medium-range GRIBs (`inputs.glofas.source: grib`)
  - NWS source: `results.pkl` (`inputs.nws.source: pickle`)

Notebook-mode run:

- config:
  - `config/forecats_pipeline.dec2022_grib_nws_pkl.notebook_compare.yaml`
- output bundle:
  - `data/forecats_inputs/site=11160500/cutoff_date=2022-12-25/run_id=20260205_144220_dec2022_notebook_compare/`
- figure:
  - `.../figures/forecats.png`

Paper-mode run:

- config:
  - `config/forecats_pipeline.dec2022_grib_nws_pkl.paper_compare.yaml`
- output bundle:
  - `data/forecats_inputs/site=11160500/cutoff_date=2022-12-25/run_id=20260205_144220_dec2022_paper_compare/`
- figure:
  - `.../figures/forecats.png`

### Config (YAML)

- Template: `config/forecats_pipeline.template.yaml`

This YAML explicitly defines:

- site: USGS gage + target lat/lon
- cutoff date + plot window
- data sources:
  - retros: existing combined CSV (truncated to cutoff)
  - GloFAS: from GRIB (raw, recommended) **or** from existing CSV (fast/debug)
  - NWS: from results.pkl (raw) **or** from existing CSV (fast/debug)
- weighting parameters (power / per-member exponents)
- plot markers (vertical lines + labels)
- plot scale (current workflow: `log1p_cms`)

### Runner scripts

- Build bundle + plot (entrypoint):
  - `scripts/forecats_pipeline.R`
  - Usage:
    - `Rscript scripts/forecats_pipeline.R --config config/forecats_pipeline.yaml`
- Plot from an existing bundle:
  - `scripts/forecats_plot_bundle.R`
  - Usage:
    - `Rscript scripts/forecats_plot_bundle.R --bundle-dir <bundle_dir>`

### Raw -> weighted forecast builders (Python)

- GloFAS GRIB -> weighted daily ensemble:
  - `scripts/forecats_build_glofas_weighted.py`
  - Uses `xarray+cfgrib+eccodes` (already present in this environment)
  - Picks a nearest non-NaN river cell (stored in `inputs/glofas_cell.json`)
- NWS results.pkl -> weighted daily ensemble:
  - `scripts/forecats_build_nws_weighted.py`
  - Supports a compatibility mode that ignores run-cycle hour (t00z/t12z), and an option to parse it.

### Output bundle layout

For each run, outputs land at:

```text
data/forecats_inputs/site=<USGS_SITE>/cutoff_date=<YYYY-MM-DD>/run_id=<RUN_ID>/
  meta.yaml
  inputs/
    usgs_daily.csv
    retros_daily.csv
    glofas_weighted_daily.csv
    nws_weighted_daily.csv
    glofas_cell.json
  figures/
    forecats.png
  logs/
    pipeline.log
  cache/
    glofas/   (per-issue_date caches; run-scoped)
```

### Storage scale choice (current implementation)

To keep the bundle easy to reason about:

- All bundle CSVs store **raw cms**.
- Forecast weighting is performed on **log1p(cms)** (as in notebooks), then inverted back to cms.
- Plot scale is controlled by YAML (`transforms.plot_scale`) and current workflow fixes it to `log1p_cms`.

### Plot contract (legend, flood thresholds, and unit consistency)

This is the explicit plotting contract enforced by `scripts/forecats_plot_bundle.R` so the
bundle-driven figure stays comparable to the legacy notebook figure in `R/environmetrics/40_figures.R`.

- **Units**:
  - All bundle inputs are stored as **raw cms** (m^3/s).
  - The plot applies a single transform (configured by `transforms.plot_scale`) to *all* series.
  - No bias correction or scale correction is applied anywhere in the canonical pipeline.
- **Legend** (matches the old notebook semantics):
  - Legend entries: **USGS**, **GloFAS**, **NWS** (the *before-cutoff* USGS and retrospective series).
  - USGS observations **after** the cutoff are plotted as **dashed red** and intentionally excluded from the legend.
  - Forecast ensembles are plotted as thin member lines and excluded from the legend.
- **Flood thresholds** (horizontal dashed lines):
  - Configure in YAML under `plot.flood_levels` with explicit `value` + `unit` (`cfs` or `cms`).
  - Values are converted to cms, then transformed to the plotting scale before drawing.
  - Backwards-compatibility: if `plot.flood_levels` is missing and `site.usgs_site=11160500`,
    the plotter defaults to:
    - Major Flooding: 15000 cfs
    - Minor Flooding: 6750 cfs

### Weighting + alignment details (the "contract" the pipeline enforces)

This section is meant to make it crystal-clear how raw files become the forecast matrices used
for plotting (and later model fitting). If anything here ever changes, update this document and
the corresponding scripts together.

#### GloFAS (operational medium-range GRIB -> weighted daily ensemble)

Input: GRIBs under:

```text
data/glofas_operational_medium_range/grib/issue_date=YYYY-MM-DD/*.grib
```

Extraction:

- variable: `shortName=dis24` (river discharge in the last 24 hours)
- control forecast: `dataType=cf` -> member `member_00`
- perturbed forecast: `dataType=pf` -> members `member_01..member_50`
- location:
  - we select the **nearest non-NaN** river cell once, using a reference GRIB at/just before `cutoff_date`
  - that selection is written to `inputs/glofas_cell.json` with the chosen lat/lon indices and distance

Alignment:

- GRIB provides `time` (issue time) and `step` (lead time as timedelta)
- lead time in hours: `lead_time_h = step / 1h`
- **target_date convention (important):**

```text
target_date = issue_date + lead_time_h/24 - shift_days
```

where `shift_days` defaults to `1` to match the historical notebook behavior. (This is the
"valid for the previous calendar day" convention for `dis24`.)

Issue-date window:

To build forecasts for the window `[forecast_start_date, forecast_end_date]` given a cutoff `D`,
we include only issue_dates `<= D` and compute the earliest necessary issue_date automatically:

```text
issue_start = forecast_start_date - (max_lead_days - shift_days)
issue_dates = issue_start .. cutoff_date  (inclusive)
```

This guarantees we include *all* issue dates that could contribute to the first forecast target day.

Weighting (per target_date, per ensemble member):

- transform: `x = log1p(discharge_cms)`
- choose a weighting scheme:
  - **notebook-mode** (lead-time weights; matches `glofas_forecasts.ipynb`):
    - unnormalized weights: `w_raw = lead_time_h ** power` (power < 0 favors shorter leads)
  - **paper-mode** (age weights; matches the paper's description):
    - define: `r_days = cutoff_date - issue_date` (integer days, `r_days >= 0`)
    - unnormalized weights: `w_raw = 1 / (r_days + 1) ** alpha`
      - we use `(r_days + 1)` so `r_days=0` is well-defined (weight 1 before normalization)

- normalize within each group `(target_date, member)`:
  - `w = w_raw / sum(w_raw)`
- weighted mean on the log1p scale:

```text
x_weighted(target_date, member) = sum_i w_i * log1p(value_i)
```

- invert for storage: `discharge_weighted_cms = expm1(x_weighted)`

Output:

- `inputs/glofas_weighted_daily.csv` with:
  - `target_date` + `member_00..member_50`
  - values stored as **raw cms**

#### NWS/NWM (`results.pkl` -> weighted daily ensemble)

Input: `results.pkl` (dict mapping a path-like key -> a float value at the point).

Parsing:

From each key we derive:

- `issue_date` from `nwm.YYYYMMDD/...`
- `ensemble_number` from the folder name containing `mem` (e.g. `mem3` -> 3)
- `lead_time_h` from filename token `.fNNN.`
- optional `issue_hour` from `.t00z.` / `.t12z.` (configurable)

Alignment:

- `issue_datetime = issue_date + issue_hour`
- `target_datetime = issue_datetime + lead_time_h hours`
- `target_date = date(target_datetime)`
- `target_hour = hour(target_datetime)`

Filtering:

- `issue_date <= cutoff_date` (represents information available at cutoff time)
- `forecast_start_date <= target_date <= forecast_end_date`
- optional speed optimization: ignore issue_dates older than `cutoff_date - issue_lookback_days`

Weighting:

For each `(target_date, target_hour, ensemble)` group:

- transform: `x = log1p(value_cms)`
- choose a weighting scheme:
  - **notebook-mode** (lead-time weights; matches `Retro-Analysis.ipynb`):

    ```text
    w_raw = 1 / (lead_time_h ** exponent[ensemble])
    ```

  - **paper-mode** (age weights; matches the paper's description):

    ```text
    r_days = cutoff_date - issue_date
    w_raw  = 1 / (r_days + 1) ** alpha
    ```

- normalize within group and compute weighted average on log1p scale
- then compute **daily mean** across hours (simple/unweighted):

```text
x_daily(target_date, ensemble) = mean_over_target_hour( x_weighted(target_date, target_hour, ensemble) )
```

- invert for storage: `cms = expm1(x_daily)`

Output:

- `inputs/nws_weighted_daily.csv` with:
  - `target_date` + `member_01..member_07`
  - values stored as **raw cms**

#### A subtle but important constraint: how far after cutoff can we forecast?

Because we enforce `issue_date <= cutoff_date`, there is a hard limit to how far after cutoff
we can produce non-NaN targets given a maximum lead time.

For GloFAS with max lead of 30 days and `shift_days=1`, target dates later than:

```text
cutoff_date + (max_lead_days - shift_days)
```

will be NaN (no contributing issue dates exist). In practice this means:

- with max lead 30 and shift 1, the last valid target_date is cutoff + 29 days

If you set `dates.plot_end` beyond this, the bundle is still produced, but the extra days will be NA.

### YAML config reference (what you can/should change)

The pipeline is designed so that changing only YAML is enough to re-run for a new cutoff date.
The template is the best source of truth; this section documents the intent.

- `run.run_id`: optional; default auto timestamp (lets you keep multiple runs)
- `run.out_root`: output root (default `data/forecats_inputs`)
- `run.overwrite`: if true, overwrite existing bundle outputs for same run_id

- `site.usgs_site`: USGS gage (e.g. `11160500`)
- `site.lat`/`site.lon`: target location for forecast extraction (degrees)
- `site.usgs.*`: NWIS params; usually keep defaults unless changing station/metric

- `dates.cutoff_date`: last day included in retros/history window (YYYY-MM-DD)
- `dates.plot_start`/`dates.plot_end`: plotting window; also defines forecast target window

- `transforms.plot_scale`:
  - `raw_cms` (linear)
  - `log1p_cms`
  - `log1p_cms` (current workflow standard)

- `inputs.retros.path`: combined retros CSV to truncate (covers 1979..2022 in current file)
- `inputs.retros.scale`: scale of that file (`log1p_cms` for legacy)

- `inputs.glofas.source`: `grib` (preferred) or `csv` (debug)
- `inputs.glofas.grib.grib_root`: root containing `issue_date=...` folders
- `inputs.glofas.weighting.scheme`:
  - `latest` (no weighting; pick most recent issue_date per target_date/member) **[default if omitted]**
  - `paper` (age-based)
  - `notebook` (lead-time)
- `inputs.glofas.weighting.power`: notebook-mode lead-time weighting power (negative favors shorter leads)
- `inputs.glofas.weighting.alpha`: paper-mode exponent (weights ~ (r_days+1)^-alpha)
- `inputs.glofas.weighting.shift_days`: target-date shift; keep at 1 unless you re-derive conventions

- `inputs.nws.source`: `pickle` (preferred general) or `csv` (debug)
- `inputs.nws.pickle.path`: path to `results.pkl`
- `inputs.nws.pickle.issue_lookback_days`: speed knob; increase if you suspect longer required lookback
- `inputs.nws.pickle.parse_issue_hour`: if true, use t00z/t12z cycles; if false, treat as 00Z (compat)
- `inputs.nws.weighting.scheme`:
  - `latest` (no weighting; pick most recent issue_datetime per target_date/ensemble) **[default if omitted]**
  - `paper` (age-based)
  - `notebook` (lead-time)
- `inputs.nws.weighting.exponents`: notebook-mode per-member exponent map
- `inputs.nws.weighting.alpha`: paper-mode exponent (weights ~ (r_days+1)^-alpha)

### Validation checklist (fast sanity checks)

After a run completes, the bundle should contain:

- `inputs/usgs_daily.csv`: non-empty; includes dates through `plot_end`
- `inputs/retros_daily.csv`: ends exactly on `cutoff_date`
- `inputs/glofas_weighted_daily.csv`: has `member_00..member_50` (51 members)
- `inputs/nws_weighted_daily.csv`: has `member_01..member_07` (7 members)
- `figures/forecats.png`: renders without errors

Quick checks:

```bash
python3 - <<'PY'\nfrom __future__ import annotations\n\nfrom pathlib import Path\n\nimport pandas as pd\n\nBUNDLE = Path('data/forecats_inputs/site=11160500/cutoff_date=2022-12-25/run_id=<RUN_ID>')\ninputs = BUNDLE / 'inputs'\n\nusgs = pd.read_csv(inputs / 'usgs_daily.csv', parse_dates=['date'])\nretros = pd.read_csv(inputs / 'retros_daily.csv', parse_dates=['date'])\nglo = pd.read_csv(inputs / 'glofas_weighted_daily.csv', parse_dates=['target_date'])\nnws = pd.read_csv(inputs / 'nws_weighted_daily.csv', parse_dates=['target_date'])\n\nprint('usgs rows', len(usgs), 'range', usgs['date'].min().date(), usgs['date'].max().date())\nprint('retros rows', len(retros), 'range', retros['date'].min().date(), retros['date'].max().date())\nprint('glofas rows', len(glo), 'cols', len(glo.columns) - 1)\nprint('nws rows', len(nws), 'cols', len(nws.columns) - 1)\n\nassert len([c for c in glo.columns if c.startswith('member_')]) == 51\nassert len([c for c in nws.columns if c.startswith('member_')]) == 7\n\nprint('glofas NA fraction', float(glo.drop(columns=['target_date']).isna().mean().mean()))\nprint('nws NA fraction', float(nws.drop(columns=['target_date']).isna().mean().mean()))\nPY\n+```

### Troubleshooting (common failures)

- All-NaN GloFAS outputs:
  - likely your chosen bbox / cell has NaNs everywhere; check `inputs/glofas_cell.json` and consider a larger bbox upstream (download side)
  - or `dates.plot_end` is beyond `cutoff + 29d` (see constraint above)
- NWS builder produces "No rows matched":
  - confirm `results.pkl` contains the year you requested
  - increase `inputs.nws.pickle.issue_lookback_days`
  - set `inputs.nws.pickle.parse_issue_hour: false` if key parsing differs from expected

## 7) Current Implementation Status + Next Steps

As of 2026-02-05, the bundle workflow described above is **already implemented** in this repo:

- DONE: YAML-driven pipeline runner:
  - `scripts/forecats_pipeline.R`
- DONE: raw -> weighted forecast builders:
  - `scripts/forecats_build_glofas_weighted.py`
  - `scripts/forecats_build_nws_weighted.py`
- DONE: bundle-driven plotter:
  - `scripts/forecats_plot_bundle.R`

What remains (next improvements, not required for correctness):

- Decide default for NWS issue-cycle handling:
  - keep `parse_issue_hour: false` for strict compatibility with parts of the old notebook logic, or
  - switch to `true` for more faithful time alignment
- Add a batch runner to generate bundles/figures for a list of cutoff_dates (once GloFAS downloads are complete)
- Add persistent caching (especially for NWS parsing) to accelerate large-scale batch generation
- Later: wire bundle input into model-fitting code so "fit any cutoff_date" becomes a pure config change

## 8) How this supports the “many dates” plan after full GloFAS download

Once the GloFAS archive is complete for your target issue-date windows, you can:

1) enumerate all cutoff_dates for which you have complete retros + forecast coverage,
2) build one bundle per cutoff_date,
3) batch-generate `forecats.png` for each cutoff_date (or only for select events),
4) later batch-run model fits using the same bundles.

This is exactly why a bundle-based contract is worth doing now: it makes the whole workflow composable and safe (no accidental mixing of dates/scales).

## Appendix A — Current canonical inputs (as of now)

- `weighted_time_series.csv` (GloFAS weighted forecasts; `target_date` + 51 members)
- `nws_forecast.csv` (NWS weighted forecasts; `Date` + 7 members)
- `retros_2022-12-25.csv` (retros daily; `Date, USGS, NWS3.0, GloFAS`)

Consumed by:

- `R/environmetrics/10_data_inputs.R`
- `R/environmetrics/40_figures.R`

Produced (conceptually) by:

- `glofas_forecasts.ipynb` (GloFAS weighting)
- `Retro-Analysis.ipynb` (NWS weighting + retros assembly)

## Appendix B — Legacy artifact + provenance gap: `weighted_time_series_custom_filled.csv`

There is an important reproducibility gap around one legacy input that explains why some
older notebook figures can be reproduced **only** if we reuse an existing CSV artifact.

### What we observed

- A legacy file exists in the repo root:
  - `weighted_time_series_custom_filled.csv`
- When this file is used as the GloFAS forecast source, we can reproduce the corresponding
  legacy Dec 2022 figure **exactly** (because we are literally using the same precomputed
  numbers).

### What is *not* in this repo (as of 2026-02-05)

- We do **not** have code in this repo that produces the `*_custom_filled.csv` artifact.
- Repo-wide search only found references in our new debugging config/report artifacts, not
  in the original notebook/scripts that generated the legacy data:
  - no `to_csv(...custom_filled...)`, no `custom_filled` string, no explicit fill step.
- We *do* have notebook code that writes the non-filled variant:
  - `glofas_forecasts.ipynb` writes `weighted_time_series_custom.csv`
  - but it does not write `weighted_time_series_custom_filled.csv`, and the “filled”
    procedure is currently undocumented.

### Decision (recommended)

- Treat `weighted_time_series_custom_filled.csv` as a **legacy snapshot** that is useful
  for comparisons, but **not** as a canonical, reproducible input going forward.
- Canonicalize the GRIB-based pipeline:
  - `scripts/forecats_build_glofas_weighted.py` (GRIB -> weighted daily ensemble)
  - bundle runner: `scripts/forecats_pipeline.R`
  - plotter: `scripts/forecats_plot_bundle.R`

This makes the workflow fully parameterized (by YAML), auditable (bundle meta + logs), and
regeneratable for any cutoff_date once the GRIB archive is complete.

### If you still need legacy parity for a specific case (debug only)

- Use the dedicated config that explicitly declares the legacy artifact as the source of
  truth:
  - `config/forecats_pipeline.example_dec2022_legacy_custom_filled.yaml`
- This is intentionally *not* the default mode, because it hides upstream assumptions and
  depends on an untracked transformation/filling step.
