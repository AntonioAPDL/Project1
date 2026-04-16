# Forecast Overlay Review

## Purpose

Before implementing blended forecast inputs for the corrected all-9 relaunch, we need a clean review layer that compares:

- retrospective PRISM precipitation vs forecast precipitation families
- retrospective ERA5 soil moisture vs forecast soil families

for the first 30 days after each cutoff.

This review step is the evidence-gathering layer for deciding the blend design, and it now also overlays the currently configured blended input that would be fed into the corrected-model relaunch.

## Why this is the right step

The current forecast handoff is complete and healthy:

- GEFS extraction complete
- NWM extraction complete
- combined health check passed
- handoff cache built for all 5 cutoffs

The current gap is not forecast availability. The current gap is scientific:

- the live model-input helper is still deterministic forecast substitution
- the repo contains blend-oriented config knobs, but the actual helper path does not yet use them

So the correct next step is to review forecast vs retrospective behavior first, then define the blend.

## Review inputs

Forecast inputs:

- handoff root under the completed GEFS/NWM manifest run
- GEFS `APCP`
- GEFS `SOILW` layers
- NWM `SOILSAT_TOP`
- NWM `SOIL_M`
- NWM `RAINRATE`

Retrospective overlays:

- `prism_precipitation_santa_cruz_1987_2023.csv`
- `soil_moisture_data/soil_moisture_big_trees_daily_avg_1987_2023.csv`

If those canonical project-root files are missing, the workflow can restore them from validated surviving CSVs.

## Exact workflow

Config:

- [forecast_overlay_review.site11160500.yaml](/data/muscat_data/jaguir26/project1_ucsc_phd/config/forecast_overlay_review.site11160500.yaml)

Runner:

- [prepare_forecast_overlay_review.py](/data/muscat_data/jaguir26/project1_ucsc_phd/scripts/prepare_forecast_overlay_review.py)

Plot script:

- [plot_gefs_nwm_forecast_cutoff.R](/data/muscat_data/jaguir26/project1_ucsc_phd/scripts/plot_gefs_nwm_forecast_cutoff.R)

The workflow does:

1. validate the handoff cache is healthy
2. validate or restore retrospective PRISM and ERA5 overlay CSVs
3. write a climate-series status CSV
4. render exact 30-day plots for all 5 cutoffs in two styles:
   - `mean_only_same_units`
   - `mean_only_same_units_bias_quantiles`
   - with the configured blended input added as a gold line when `review.detclim_config_path` is set
5. write a summary JSON and plot index CSV

## Outputs

Per cutoff, the plot script writes outputs under:

- `.../plots/cutoff_date=YYYY-MM-DD/`

The review workflow writes:

- `review_prep/forecast_overlay_review_20260415/forecast_overlay_review_summary.json`
- `review_prep/forecast_overlay_review_20260415/plot_index.csv`
- `review_prep/forecast_overlay_review_20260415/climate_series_status.csv`

## Intended use

These plots are not the blend itself.

They are the decision layer used to answer:

- which precipitation forecast family is most defensible to feed the blend
- which soil forecast family is most defensible to feed the blend
- whether soil should be bias-adjusted before blending
- how fast the blend should trust the forecast after the cutoff

The current configured blend used in the review is read from:

- [multimodel_v8_all9_featurecov.template.yaml](/data/muscat_data/jaguir26/project1_ucsc_phd/config/multimodel_v8_all9_featurecov.template.yaml)

and currently means:

- precipitation source: `GEFS APCP`
- soil source: `GEFS SOILW 0-0.1 m below ground`
- ensemble reduction: `q85` for both series
- noisy forecast step:
  - precipitation `N(0, 20)`, floored at zero
  - soil `|N(0, 0.05)|`
- observed/forecast convex blend:
  - `0.5 * observed + 0.5 * noisy_forecast`
- additional precipitation zero-stay rule:
  - if retrospective precipitation is `0`, keep the final precipitation input at `0` with probability `0.9`
  - otherwise use the blended value above
