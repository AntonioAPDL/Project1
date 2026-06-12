# exAL-M-T1 Setup/Support Figures by Cutoff v2 Workflow

Date: 2026-05-07

## Scope

This runbook documents the corrected `v2` workflow for the four cutoff-dependent setup/input/support figures tied to the published `exAL-M-T1` CRPS lineage:

- `usgs.png`
- `precip_soilmoisture_climatePC1_faceted_labeled.png`
- `retrospective_log_discharge_plot_faceted.png`
- `forecats.png`

The `v2` workflow replaces the older `20260506` `v1` family as the canonical article-facing provenance path.

Current corrected `v2` plotting contract:

- `usgs.png` and the raw covariate figure use the full `1987-05-29 -> cutoff` daily history available in the selected-run shared inputs
- `retrospective_log_discharge_plot_faceted.png` uses the retrospective support actually available for the cutoff-specific bundle, and the review metadata explicitly records whether that support reaches back to `1987-05-29`
- `forecats.png` uses a strict `cutoff - 28 days` to `cutoff + 28 days` display window so the post-cutoff span matches the maximum GloFAS horizon
- flow-support figures are displayed on `log1p_cms`, not the harsher internal `log_log1p_cms` model-analysis scale
- the runtime metadata now records both:
  - the display-scale contract used by the figures
  - the selected-run internal analysis scale used by the fitted model lineage

## Canonical source contract

Each cutoff now has two linked roots:

1. the CRPS-linked selected `exAL-M-T1` run root
2. the authoritative figure-input bundle root

Those pairings are frozen in:

- `repro/run/EXAL_M_T1_SETUP_SUPPORT_V2_SOURCE_MANIFEST.md`
- `config/exal_m_t1_setup_support_by_cutoff_v2_20260507.json`

## Bundle classes

### Short-window synthetic-retrospective cutoffs

- `2021-01-23`
- `2021-11-12`

These use:

- NWS synthetic retrospective keep-source policy centered on `nws_synth_retro_ens_mean`
- cutoff-era GloFAS retrospective source selection

### Histfix long-history cutoffs

- `2021-12-21`
- `2022-05-11`
- `2022-12-25`

These use:

- `nws_retro_v21` with `nws_retro_v30` tail fill
- `glofas_hist_v31_lisflood_cons`

## Canonical scripts

### Workflow-side build

- `scripts/render_exal_m_t1_setup_support_by_cutoff_v2.py`
- `scripts/render_setup_support_bundle_v2.R`
- `scripts/setup_support_bundle_v2_helpers.R`
- `scripts/forecats_plot_bundle.R`
- `scripts/build_exal_m_t1_setup_support_v2_review.py`
- `scripts/validate_exal_m_t1_setup_support_v2.py`

### Article-side mirror and promotion

- `Evironmetrics---REVISED-DOC-Corrected-2/scripts/refresh_setup_support_by_cutoff_v2.py`
- `Evironmetrics---REVISED-DOC-Corrected-2/scripts/build_setup_support_by_cutoff_v2_review.py`
- `Evironmetrics---REVISED-DOC-Corrected-2/scripts/promote_setup_support_v2_to_disc.py`
- `Evironmetrics---REVISED-DOC-Corrected-2/scripts/refresh_all_generated_assets.py`

## Output roots

Workflow runtime family:

- `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/exal_m_t1_setup_support_by_cutoff_v2_20260507/`

Article-side mirror:

- `Evironmetrics---REVISED-DOC-Corrected-2/generated/setup_support_by_cutoff_v2/`

Article-side review:

- `Evironmetrics---REVISED-DOC-Corrected-2/generated/setup_support_by_cutoff_v2_review/`

Representative manuscript promotion:

- `Evironmetrics---REVISED-DOC-Corrected-2/DISC/`
- selected by `generated/setup_support_by_cutoff_v2_article_selection/selection_manifest.json`

## Source-layer rules

The corrected `v2` renderer does not use merged model matrices for these four figures.

It uses:

- `usgs.png` from the selected-run `inputs/shared/usgs/usgs_daily.csv`
- the covariate figure from raw cutoff-specific `cov_01_PPT.csv`, `cov_02_SOIL.csv`, and `cov_03_PCA.csv`
- the retrospective figure from authoritative bundle-native retrospective lineage
- `forecats.png` from bundle-native forecast inputs staged through `forecats_plot_bundle.R`

The metadata beside each cutoff now distinguishes:

- requested historical window
- actual retrospective available window
- missing-day counts within the requested and available windows

## Canonical commands

Build the full five-cutoff runtime family:

```bash
python3 /data/muscat_data/jaguir26/project1_ucsc_phd/scripts/render_exal_m_t1_setup_support_by_cutoff_v2.py --clean
```

Refresh the article-side mirror and representative `DISC/` figures:

```bash
python3 /data/muscat_data/jaguir26/project1_ucsc_phd/Evironmetrics---REVISED-DOC-Corrected-2/scripts/refresh_all_generated_assets.py
```

## Validation gate

The `v2` family is only trusted if it passes:

- `repro/run/EXAL_M_T1_SETUP_SUPPORT_V2_ACCEPTANCE_CHECKLIST.md`

The machine validation entrypoint is:

```bash
python3 /data/muscat_data/jaguir26/project1_ucsc_phd/scripts/validate_exal_m_t1_setup_support_v2.py
```

## Review outputs

Workflow-side review:

- `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/exal_m_t1_setup_support_by_cutoff_v2_20260507/review/REVIEW.md`
- `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/exal_m_t1_setup_support_by_cutoff_v2_20260507/review/gallery.html`
- `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/exal_m_t1_setup_support_by_cutoff_v2_20260507/review/figure_manifest.csv`

Article-side review:

- `Evironmetrics---REVISED-DOC-Corrected-2/generated/setup_support_by_cutoff_v2_review/SETUP_SUPPORT_BY_CUTOFF_V2_REVIEW.md`
- `Evironmetrics---REVISED-DOC-Corrected-2/generated/setup_support_by_cutoff_v2_review/gallery.html`
- `Evironmetrics---REVISED-DOC-Corrected-2/generated/setup_support_by_cutoff_v2_review/figure_manifest.csv`

## Current representative article choice

The revised article currently promotes the representative cutoff:

- `20221225_exal_m_t1`

into `DISC/` for:

- `usgs.png`
- `precip_soilmoisture_climatePC1_faceted_labeled.png`
- `retrospective_log_discharge_plot_faceted.png`
- `forecats.png`

This is an editorial choice. The underlying reproducibility family contains all five cutoffs.

## Archival note

The older workflow documented in:

- `repro/run/EXAL_M_T1_SETUP_SUPPORT_BY_CUTOFF_WORKFLOW.md`

remains useful as audit history only. It should not be used for future article refreshes.
