# Post Publication Figures Workflow

## Purpose

The post stage now keeps the existing figure contracts and automatically rewrites the canonical cutoff-window figures into a publication-grade style using the saved CSV sidecars.

This keeps the workflow reproducible and low-risk:

- model fitting and post contracts stay unchanged
- the canonical `*_cutoff_window_posterior_samples.png` and `*_cutoff_window_predictive_bands.png` files are regenerated from the saved CSV contracts
- companion PNGs are emitted beside the canonical figure for both posterior and NDLM predictive families using the saved post-adapter ensemble references on the `log1p` scale
- matching PDF exports are emitted beside the PNGs
- `publication_figure_manifest.csv` and `publication_style_used.yaml` record what was rendered

## Style Control

Default style config:

- `config/post_publication_figures.yaml`

Current defaults:

- rewrite canonical PNGs: `TRUE`
- emit PDF sidecars: `TRUE`
- fail fast on render errors: `TRUE`
- shared y-limits are enforced per cutoff from `config/post_publication_figures.yaml`

These settings are passed through `stage_post.R` into `scripts/run_environmetrics_figures.R` and then handled by `R/unified/post_publication_figures.R`.

## Backfill Existing Runs

To regenerate the publication figures for an existing run tree without rerunning models:

```bash
cd /data/muscat_data/jaguir26/project1_ucsc_phd
Rscript scripts/render_publication_post_figures.R \
  --runs-root /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_20260402/runs
```

To target a single run:

```bash
cd /data/muscat_data/jaguir26/project1_ucsc_phd
Rscript scripts/render_publication_post_figures.R \
  --run-dir /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_20260402/runs/multimodel_20210123_v8_epsTT_l1/post/outputs/multimodel_20210123_v8_epsTT_l1
```

## Inputs Required Per Figure

Posterior-sample plots require:

- `*_cutoff_window_quantiles.csv`
- `*_cutoff_window_sample_subset.csv`
- matching `figure_manifest.csv` row
- matching post caches for the exact `95%` interval and synth. mean
- `post/inputs/nws_post_adapter.csv` and `post/inputs/glofas_post_adapter.csv` for the companion ensemble-reference overlay

Predictive-band plots require:

- `*_cutoff_window_quantiles.csv`
- matching `figure_manifest.csv` row
- `post/inputs/nws_post_adapter.csv` and `post/inputs/glofas_post_adapter.csv` for the companion ensemble-reference overlay

## Output Artifacts

Per run output directory:

- canonical rewritten PNGs
- companion overlay PNGs (`*_with_raw_ensembles.png` file names retained for backward compatibility)
- matching PDF sidecars
- `publication_figure_manifest.csv`
- `publication_style_used.yaml`

The main `figure_manifest.csv` is also updated with:

- `style=publication_focus_v2` on rewritten canonical PNG rows
- new companion rows such as `*_with_raw_ensembles`, documented as adapter-scale ensemble-reference overlays
- new `*_pdf` rows for both canonical and companion exports
