# Figure A1 Component And Table Precision Contract

Date: 2026-06-10

## Scope

This note freezes the implementation contract for the revised-article Figure A1
refresh and the publication-facing numeric display precision used by generated
tables.

The active revised-article repository for this wiring pass is:

`/data/muscat_data/jaguir26/project1_ucsc_phd/Evironmetrics---REVISED-DOC-2`

The selected-output authority is:

`docs/authoritative_selected_outputs/he2_exal_m_t1_representative_20221225.yaml`

The compact selected-support source is:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_selected_output_support_20260610/runs/multimodel_20221225_v8_he2grid_c05_eps030_exdqlm_multivar_keep_authoritative_support_samplewise_a1_20260610/post/outputs/multimodel_20221225_v8_he2grid_c05_eps030_exdqlm_multivar_keep_authoritative_support_samplewise_a1_20260610`

It was rebuilt from the prior compact support bundle plus the retained
2022-12-25 q05/q50/q95 `.RData` files using:

`scripts/rebuild_authoritative_selected_support_samplewise_component.R`

## Figure A1 Display Contract

The article-facing caption and prose describe Figure A1 as the 80-month seasonal
component. The internal rendering metadata records the exact plotted contract so
the figure remains reproducible and auditable.

Required internal contract:

`component_6_plus_trend_component_1_samplewise`

This means posterior samples are combined as:

`theta[1, t, sample] + theta[6, t, sample]`

and only then summarized into the displayed posterior median and 95% interval.
This replaces the weaker legacy display helper:

`component_6_shifted_by_posterior_mean_trend_component_1`

which shifted the component-6 posterior interval by the posterior mean trend.
The legacy row family may remain in compact support files for diagnostic
comparison, but Figure A1 must use the samplewise composite contract.

## Dry/Wet Overlay Contract

Figure A1 must mark the two hydrologic regimes used in the article text:

| Period | Start | End |
|---|---:|---:|
| Dry | 2012-01-01 | 2016-12-31 |
| Wet | 2017-01-01 | 2019-12-31 |

The article renderer writes these periods to:

`artifacts/representative_selected_model_2022_12_25/authoritative_support/figures/render_metadata.json`

The metadata is part of the validation surface. Future Figure A1 refreshes should
fail validation if the samplewise component contract or dry/wet period metadata
is missing.

## Table Display Precision Contract

Publication-facing generated TeX tables use fixed five-decimal display. This
applies to CRPS, quantile check-loss, transfer-function coefficient, gamma, and
sigma tables in the revised article.

Machine-readable CSV and RDS artifacts may retain higher precision. The
five-decimal policy is a display contract for article-facing TeX fragments, not a
lossy source-data policy.

Primary generators:

- workflow post table helpers:
  `R/environmetrics/02_helpers_core.R`
- revised article TeX fragments:
  `Evironmetrics---REVISED-DOC-2/scripts/build_generated_table_includes.py`
- HE3 ablation article/corrections table sync:
  `scripts/sync_he3_ablation_article_tables.py`
- corrections response-table sync from revised-article generated bodies:
  `Evironmetrics---REVISED-DOC-2/scripts/sync_corrections_generated_table_includes.py`

The corrections repository consumes response-specific wrappers under:

`/data/muscat_data/jaguir26/Corrections---Project-1/tables/generated_tex`

Those fragments must be regenerated from the revised-article generated table
bodies rather than hand-edited.

## Validation Gates

Workflow-side tests:

- `Rscript -e 'testthat::test_file("tests/testthat/test_authoritative_selected_support_projection.R")'`
- `Rscript -e 'testthat::test_file("tests/testthat/test_post_posterior_table_exports.R")'`

Article-side tests:

- `python3 -m unittest tests.test_article_a1_and_table_contracts tests.test_corrections_generated_table_sync -v`

HE3 sync regression:

- `python3 -m unittest tests.python.test_he3_exdqlm_ablation_tooling.He3ToolingTests.test_sync_ablation_tables_updates_article_and_corrections_outputs -v`

Article refresh/validation:

- `python3 scripts/refresh_authoritative_selected_model_support_figures.py`
- `python3 scripts/build_generated_table_includes.py`
- `python3 scripts/sync_corrections_generated_table_includes.py --article-root . --corrections-root /data/muscat_data/jaguir26/Corrections---Project-1`
- `python3 scripts/validate_authoritative_output_lineage.py --article-root . --corrections-root /data/muscat_data/jaguir26/Corrections---Project-1`
- `python3 scripts/validate_manuscript_figure_paths.py --article-root .`
- `python3 scripts/validate_revision_cross_repo_wiring.py --workflow-root /data/muscat_data/jaguir26/project1_ucsc_phd --article-root /data/muscat_data/jaguir26/project1_ucsc_phd/Evironmetrics---REVISED-DOC-2 --corrections-root /data/muscat_data/jaguir26/Corrections---Project-1 --after-patch --strict`

Compile checks:

- revised article:
  `pdflatex -interaction=nonstopmode -halt-on-error -jobname=output wileyNJD-APA.tex`
  after the documented BibTeX pass sequence in the article README.
- corrections response:
  `make -B`

The 2026-06-10 implementation pass produced a passing compile-aware
cross-repo validation report at:

`reports/revision_cross_repo_validation_20260609/cross_repo_validation_summary.md`
