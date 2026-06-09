# Cross-Repo Validation Patch and Compile Closeout

Date: 2026-06-09

Related plan:

- `docs/cross_repo_validation_patch_compile_plan_20260609.md`
- `docs/revision_cross_repo_progress_audit_20260609.md`

Repos validated:

- workflow/code: `/data/muscat_data/jaguir26/project1_ucsc_phd`
- revised article: `/data/muscat_data/jaguir26/project1_ucsc_phd/Evironmetrics---REVISED-DOC-2`
- corrections article: `/data/muscat_data/jaguir26/Corrections---Project-1`

## Implemented Changes

### HE4 Current-Publication Source Contract

`scripts/build_he4_quantile_check_loss_tables.py` now supports:

```bash
python3 scripts/build_he4_quantile_check_loss_tables.py \
  --source-mode he2-publication-manifest \
  --he2-publication-manifest Evironmetrics---REVISED-DOC-2/artifacts/he2_publication_freeze/he2_bayesian_publication_manifest.csv \
  --runtime-root /data/muscat_data/jaguir26/project1_ucsc_phd_runtime \
  --output-dir reports/he4_quantile_check_loss_current_publication_20260609
```

The new mode resolves HE4 rows directly from the frozen HE2 publication
manifest. For each of the five cutoffs and four synthesis competitors, it checks
that:

- `run_root/run_id` exists and is internally consistent;
- the quantile artifact is present;
- forecast rows have the expected horizon length;
- quantile columns are monotone;
- the run CRPS row matches HE2 `crps_exact`;
- the output provenance is recorded as `he2-publication-manifest`.

The generated HE4 artifact was frozen into the revised article repo at:

- `Evironmetrics---REVISED-DOC-2/artifacts/he4_quantile_check_loss_current_publication/`

### Revised Article Wiring

The revised article now includes HE4 in the generated-table manifest:

- manifest label: `tab:he4_quantile_check_loss`
- generated table: `tables/generated_tex/he4_quantile_check_loss_main_table.tex`
- source artifact: `artifacts/he4_quantile_check_loss_current_publication/he4_quantile_check_loss_wide.csv`

The forecast-validation text now reports:

- exAL-M-T1 is lowest CRPS in the first four cutoffs;
- AL-M-T1 is the best corrected Bayesian row at 12/25/2022;
- raw NWS is the overall CRPS winner at 12/25/2022;
- corrected models do not uniformly dominate the raw operational baseline.

### Corrections Article Wiring

Hard-coded HE2, HE3, and HE4 response tables were replaced by tracked generated
fragments:

- `tables/generated_tex/he2_benchmark_crps_response_table.tex`
- `tables/generated_tex/he3_ablation_crps_response_table.tex`
- `tables/generated_tex/he4_quantile_check_loss_response_table.tex`

The corrections prose now uses the same final HE2 interpretation as the revised
article and removes the stale all-five-win claims.

### Cross-Repo Validator

Added:

- `scripts/validate_revision_cross_repo_wiring.py`

The validator checks:

- revised-article manifest paths;
- article `\input{}` paths;
- corrections `\input{}` paths;
- HE2, HE3, and HE4 rendered table values against source CSVs;
- HE4 selection provenance and CRPS agreement;
- stale/forbidden prose claims;
- required final-cutoff raw-NWS exception claims;
- compile logs in `--after-patch` mode;
- SHA-256 manifests and git metadata for reproducibility.

Final report directory, intentionally untracked:

- `reports/revision_cross_repo_validation_20260609/`

Final result:

- `cross_repo_validation_summary.md`: pass
- failed checks: `0`

## Verification Commands

```bash
python3 scripts/build_he4_quantile_check_loss_tables.py \
  --source-mode he2-publication-manifest \
  --he2-publication-manifest Evironmetrics---REVISED-DOC-2/artifacts/he2_publication_freeze/he2_bayesian_publication_manifest.csv \
  --runtime-root /data/muscat_data/jaguir26/project1_ucsc_phd_runtime \
  --output-dir reports/he4_quantile_check_loss_current_publication_20260609

python3 Evironmetrics---REVISED-DOC-2/scripts/build_generated_table_includes.py \
  --article-root Evironmetrics---REVISED-DOC-2

python3 Evironmetrics---REVISED-DOC-2/scripts/build_article_asset_review_report.py \
  --article-root Evironmetrics---REVISED-DOC-2

python3 Evironmetrics---REVISED-DOC-2/scripts/validate_manuscript_figure_paths.py \
  --article-root Evironmetrics---REVISED-DOC-2

python3 -m pytest tests/python/test_he4_quantile_check_loss_tables.py -q

python3 -m py_compile \
  scripts/build_he4_quantile_check_loss_tables.py \
  scripts/validate_revision_cross_repo_wiring.py \
  Evironmetrics---REVISED-DOC-2/scripts/build_generated_table_includes.py \
  Evironmetrics---REVISED-DOC-2/scripts/article_repo_layout.py
```

PDF builds:

```bash
cd Evironmetrics---REVISED-DOC-2
pdflatex -interaction=nonstopmode -halt-on-error -jobname=output wileyNJD-APA.tex
bibtex output
pdflatex -interaction=nonstopmode -halt-on-error -jobname=output wileyNJD-APA.tex
pdflatex -interaction=nonstopmode -halt-on-error -jobname=output wileyNJD-APA.tex

cd /data/muscat_data/jaguir26/Corrections---Project-1
make
```

Final gate:

```bash
python3 scripts/validate_revision_cross_repo_wiring.py \
  --workflow-root /data/muscat_data/jaguir26/project1_ucsc_phd \
  --article-root /data/muscat_data/jaguir26/project1_ucsc_phd/Evironmetrics---REVISED-DOC-2 \
  --corrections-root /data/muscat_data/jaguir26/Corrections---Project-1 \
  --output-dir reports/revision_cross_repo_validation_20260609 \
  --after-patch
```

## Known Residual Notes

- The revised article compile emits layout warnings, including overfull/underfull
  boxes, but no fatal errors or unresolved references after the final pass.
- The corrections compile emits an `mdframed` page-break warning. It does not
  prevent compilation and does not indicate a table/provenance mismatch.
- The validator report and HE4 builder report under `reports/` are runtime
  evidence and are intentionally not tracked by default.
