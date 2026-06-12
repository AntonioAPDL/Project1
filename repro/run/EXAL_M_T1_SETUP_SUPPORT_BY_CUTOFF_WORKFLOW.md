# exAL-M-T1 Setup/Support Figures by Cutoff Workflow

Status: provisional `v1` workflow; retained for audit history only.

Do not treat this document as the final article-facing contract.

The corrected planning documents are now:
- `repro/run/EXAL_M_T1_SETUP_SUPPORT_V2_SOURCE_MANIFEST.md`
- `repro/run/EXAL_M_T1_SETUP_SUPPORT_V2_FILE_PLAN.md`
- `repro/run/EXAL_M_T1_SETUP_SUPPORT_V2_ACCEPTANCE_CHECKLIST.md`

Why this matters:
- the `v1` workflow correctly targeted the five verified `exAL-M-T1` cutoffs,
- but it rendered several figures from merged model matrices and incomplete replay-side metadata,
- so it is no longer considered faithful enough for the final revised-article freeze.

Date: 2026-05-06

## Scope

This workflow derives the cutoff-specific setup/input/support figures for the five verified `exAL-M-T1` publication replay runs.

Figures produced for each cutoff:
- `usgs.png`
- `precip_soilmoisture_climatePC1_faceted_labeled.png`
- `retrospective_log_discharge_plot_faceted.png`
- `forecats.png`

These figures are treated as:
- cutoff-dependent reproducibility artifacts,
- derived from the verified run-scoped shared input bundles,
- separate from the smoke-fast replay post outputs used for CRPS and posterior summaries.

## Canonical source set

Source config:
- `config/exal_m_t1_setup_support_by_cutoff_20260506.json`

Verified replay root:
- `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_publication_replay_representatives_20260506`

Derived runtime root:
- `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/exal_m_t1_setup_support_by_cutoff_20260506`

## Canonical scripts

Runtime-side render path:
- `scripts/render_exal_m_t1_setup_support_by_cutoff.py`
- `scripts/render_setup_support_figures.R`
- `R/environmetrics/40_figures_setup_support.R`

Article-side mirror path:
- `Evironmetrics---REVISED-DOC-Corrected-2/scripts/refresh_setup_support_by_cutoff.py`
- `Evironmetrics---REVISED-DOC-Corrected-2/scripts/build_setup_support_by_cutoff_review.py`

Top-level article refresh:
- `Evironmetrics---REVISED-DOC-Corrected-2/scripts/refresh_all_generated_assets.py`

## Why this workflow exists

The verified publication replay runs intentionally used:
- `post.smoke_fast: yes`

That was the correct choice for:
- CRPS tables,
- posterior summary tables,
- representative predictive synthesis outputs.

But it does not emit the four setup/input/support figures above.

This workflow fills that gap by:
- reusing the verified run-scoped `inputs/shared/*` bundles,
- rendering only the four setup/support figures,
- and preserving a separate derived artifact family with manifests, hashes, and review outputs.

## Inputs used per cutoff

Each cutoff render reads only the materialized run-scoped inputs from the verified replay run:
- `inputs/shared/usgs/usgs_daily.csv`
- `inputs/shared/retros/retros.csv`
- `inputs/shared/forecasts/nws_forecast.csv`
- `inputs/shared/forecasts/glofas_forecast.csv`
- `inputs/shared/covariates/cov_01_PPT.csv`
- `inputs/shared/covariates/cov_02_SOIL.csv`
- `inputs/shared/covariates/cov_03_PCA.csv`
- `inputs/shared/covariates/covariate_features.csv`
- `inputs/shared/source_map.txt`

This avoids the older notebook/manual path and keeps the derivation local to the verified run bundles.

## Output contract

For each cutoff slug, the derived runtime bundle contains:
- `figures/`
- `inputs/`
- `logs/`
- `review/`

Representative files:
- `figures/usgs.png`
- `figures/precip_soilmoisture_climatePC1_faceted_labeled.png`
- `figures/retrospective_log_discharge_plot_faceted.png`
- `figures/forecats.png`
- `inputs/source_run_root.txt`
- `inputs/source_map.txt`
- `inputs/resolved_config.yaml`
- `inputs/summary.json`
- `inputs/compare_report.json`
- `inputs/cutoff_metadata.json`
- `inputs/shared_input_hashes.csv`
- `logs/render.log`
- `review/figure_manifest.csv`
- `review/review_notes.md`

The top-level derived runtime bundle also contains:
- `review/REVIEW.md`
- `review/gallery.html`
- `review/figure_manifest.csv`

## Canonical commands

Render the workflow bundle:

```bash
python3 /data/muscat_data/jaguir26/project1_ucsc_phd/scripts/render_exal_m_t1_setup_support_by_cutoff.py --clean
```

Mirror it into the revised article repo:

```bash
python3 /data/muscat_data/jaguir26/project1_ucsc_phd/Evironmetrics---REVISED-DOC-Corrected-2/scripts/refresh_setup_support_by_cutoff.py
python3 /data/muscat_data/jaguir26/project1_ucsc_phd/Evironmetrics---REVISED-DOC-Corrected-2/scripts/build_setup_support_by_cutoff_review.py
```

Or run the full article refresh:

```bash
python3 /data/muscat_data/jaguir26/project1_ucsc_phd/Evironmetrics---REVISED-DOC-Corrected-2/scripts/refresh_all_generated_assets.py
```

## Review paths

Workflow-side review:
- `.../exal_m_t1_setup_support_by_cutoff_20260506/review/gallery.html`
- `.../exal_m_t1_setup_support_by_cutoff_20260506/review/REVIEW.md`

Article-side review:
- `Evironmetrics---REVISED-DOC-Corrected-2/generated/setup_support_by_cutoff_review/gallery.html`
- `Evironmetrics---REVISED-DOC-Corrected-2/generated/setup_support_by_cutoff_review/SETUP_SUPPORT_BY_CUTOFF_REVIEW.md`

## Operational rules

1. Do not regenerate these figures from the old notebook path.
2. Do not treat the article's current single-copy setup figures as universal.
3. Treat the five verified `exAL-M-T1` replay runs as the only source of truth.
4. Refresh the article-side mirror only from the derived runtime bundle.
5. Keep the current manuscript figure references unchanged until the visual review is complete.
