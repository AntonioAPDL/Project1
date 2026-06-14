# Current Publication Authority, Cleanup, And Corrections Audit Plan

Date: 2026-06-14

## Decision

The current outputs are the authoritative publication baseline for the present
revision cycle. This is a practical freeze, not a claim that every individual
cutoff/model cell is globally optimal. Future per-cell or per-cutoff calibration
is allowed, but only through a versioned manifest/overlay, regenerated article
artifacts, synchronized corrections tables, and the validation gates listed
below.

No current numerical table, figure, or manifest value is changed by this note.
It records the authority contract and the cleanup/cross-reference plan needed
before the next corrections-article audit.

## Active Source Of Truth

### Workflow Repo

Root:

`/data/muscat_data/jaguir26/project1_ucsc_phd`

Branch:

`feature/export_posterior_tables`

Core authority files:

- `docs/exdqlm_multivar_keep_authoritative_specs_20260601.yaml`
  - current five-cutoff `exAL-M-T1` winner manifest;
  - points to the canonical grid runtime root;
  - records the canonical 20260510 input-bundle contract, `log1p` scale, seven
    quantile lanes, and winner hyperparameters.
- `config/he2_publication_manifest_replacement_overlay_table1_targeted_repair_20260612.yaml`
  - current selective HE2 Table 1 repair overlay;
  - promotes only repair rows that improved or tied the previous authoritative
    CRPS and passed fit/post/validate/report plus heavy-artifact cleanup.
- `scripts/build_he2_bayesian_publication_manifest.py`
  - workflow-side builder for the 45-cell HE2 Bayesian publication manifest;
  - checks canonical input congruence, model lineage, score values, stage
    status, and absence of retained heavy `.RData`/`.rda` artifacts.
- `scripts/validate_publication_freeze.py`
  - strict publication-freeze gate for HE2, HE3, HE4, selected figures, and
    repo cleanliness.
- `scripts/validate_revision_cross_repo_wiring.py`
  - strict cross-repo table/prose/source-path validator.

### Revised Article Repo

Root:

`/data/muscat_data/jaguir26/project1_ucsc_phd/Evironmetrics---REVISED-DOC-Corrected-2`

Branch:

`main`

Current manuscript-local freeze surface:

- `MANUSCRIPT_ASSET_MANIFEST.json`;
- `config/runtime_bindings.json`;
- `artifacts/`;
- `figures/`;
- `tables/generated_tex/`;
- `reports/manuscript_asset_review/`;
- `docs/figure_table_provenance.md`;
- `docs/manuscript_revision_checklist.md`.

The old article-side `generated/` and `DISC/` trees are retired and should
remain absent. The preferred article refresh command is:

```bash
python3 scripts/refresh_all_generated_assets.py
```

### Corrections Repo

Root:

`/data/muscat_data/jaguir26/Corrections---Project-1`

Branch:

`main`

Current corrections source-of-truth files:

- `WORKFLOW.md`;
- `main.tex`;
- `tables/generated_tex/`.

Generated response tables should be synced from the revised article repo by:

```bash
python3 Evironmetrics---REVISED-DOC-Corrected-2/scripts/sync_corrections_generated_table_includes.py \
  --article-root /data/muscat_data/jaguir26/project1_ucsc_phd/Evironmetrics---REVISED-DOC-Corrected-2 \
  --corrections-root /data/muscat_data/jaguir26/Corrections---Project-1
```

## Current Authoritative Assets

| Asset family | Current authority | Flexible future replacement path |
|---|---|---|
| HE2 28-day CRPS table | `artifacts/he2_publication_freeze/he2_bayesian_publication_manifest.csv` plus `tables/generated_tex/benchmark_crps_main_table.tex` | Replace by a new HE2 manifest or replacement overlay, then refresh article tables and sync corrections. |
| HE2 8-day NWS-horizon CRPS table | `tables/generated_tex/benchmark_crps_nws_horizon_table.tex` and `benchmark_crps_horizon_summary.csv` | Same manifest refresh, with per-lead CRPS recomputation for leads 1--8. |
| `exAL-M-T1` five-cutoff winners | `docs/exdqlm_multivar_keep_authoritative_specs_20260601.yaml` | Create a new versioned authority YAML; do not overwrite old run roots or generated TeX directly. |
| HE3 ablation tables | `artifacts/he3_exdqlm_ablation_authoritative/` and `tables/generated_tex/he3_ablation_crps*_table.tex` | Rerun ablation matrix anchored to the new winner manifest, regenerate both 28-day and 8-day tables, then sync corrections. |
| HE4 quantile check-loss table | `artifacts/he4_quantile_check_loss_current_publication/` and `tables/generated_tex/he4_quantile_check_loss_main_table.tex` | Recompute from the current HE2 manifest rows for `exAL-M-T1`, `AL-M-T1`, `exAL-U-T1`, and `AL-U-T1`. |
| Representative selected-model figures/tables | `artifacts/representative_selected_model_2022_12_25/` | Update `config/runtime_bindings.json:exal_m_t1.selected_support_output_root`, refresh article assets, and rerun lineage validation. |
| Setup/support figures | `artifacts/five_cutoff_setup_support/` and `figures/manuscript/` | Refresh through the validated setup-support `v2` path, then promote through manifest-driven scripts. |

## Future Calibration Protocol

When a future calibration produces better fits or better CRPS for a specific
model/cutoff, use this order:

1. Preserve the old runtime root and create a new isolated runtime root.
2. Run fit, post, validate, and report stages.
3. Confirm CRPS and diagnostic improvement against the current authoritative
   row.
4. Confirm canonical input-bundle congruence.
5. Confirm no retained heavy `.RData`, `.rda`, or `.Rda` artifacts remain in
   promoted runtime roots unless an explicit short-term exception is documented.
6. Promote by manifest:
   - for selected `exAL-M-T1` winners, create a new
     `docs/exdqlm_multivar_keep_authoritative_specs_YYYYMMDD.yaml`;
   - for HE2 family repair rows, create or update a replacement overlay and set
     `HE2_PUBLICATION_MANIFEST_REPLACEMENT_OVERLAY` if the default overlay is
     not the intended one.
7. Rebuild the workflow HE2 manifest.
8. Refresh the article-side bundles.
9. Sync corrections generated tables.
10. Run all validation gates and compile both documents.
11. Only then revise manuscript/corrections prose.

## Validation Gates

Run from the workflow repo:

```bash
python3 scripts/build_he2_bayesian_publication_manifest.py
```

Run from the article repo:

```bash
python3 scripts/refresh_he2_manifest_snapshot.py \
  --article-root /data/muscat_data/jaguir26/project1_ucsc_phd/Evironmetrics---REVISED-DOC-Corrected-2 \
  --workflow-root /data/muscat_data/jaguir26/project1_ucsc_phd

python3 scripts/build_generated_table_includes.py \
  --article-root /data/muscat_data/jaguir26/project1_ucsc_phd/Evironmetrics---REVISED-DOC-Corrected-2

python3 scripts/sync_corrections_generated_table_includes.py \
  --article-root /data/muscat_data/jaguir26/project1_ucsc_phd/Evironmetrics---REVISED-DOC-Corrected-2 \
  --corrections-root /data/muscat_data/jaguir26/Corrections---Project-1

python3 -m unittest discover -s tests
```

Run from the workflow repo after all tracked edits are committed:

```bash
python3 scripts/validate_revision_cross_repo_wiring.py \
  --workflow-root /data/muscat_data/jaguir26/project1_ucsc_phd \
  --article-root /data/muscat_data/jaguir26/project1_ucsc_phd/Evironmetrics---REVISED-DOC-Corrected-2 \
  --corrections-root /data/muscat_data/jaguir26/Corrections---Project-1 \
  --output-dir reports/revision_cross_repo_wiring_check_CURRENT \
  --check-only --strict

python3 scripts/validate_publication_freeze.py \
  --workflow-root /data/muscat_data/jaguir26/project1_ucsc_phd \
  --article-root /data/muscat_data/jaguir26/project1_ucsc_phd/Evironmetrics---REVISED-DOC-Corrected-2 \
  --corrections-root /data/muscat_data/jaguir26/Corrections---Project-1 \
  --require-clean
```

Compile from the article repo:

```bash
pdflatex -interaction=nonstopmode -halt-on-error -jobname=output wileyNJD-APA.tex
bibtex output
pdflatex -interaction=nonstopmode -halt-on-error -jobname=output wileyNJD-APA.tex
pdflatex -interaction=nonstopmode -halt-on-error -jobname=output wileyNJD-APA.tex
```

Compile from the corrections repo:

```bash
pdflatex -interaction=nonstopmode -halt-on-error main.tex
```

## Cleanup Rules

1. Keep generated runtime evidence under `reports/` untracked unless it is a
   small, intentional publication-freeze artifact.
2. Do not commit large runtime `.RData`, `.rda`, `.Rda`, or scratch output.
3. Do not edit `tables/generated_tex/*.tex` by hand except for emergency
   rollback documentation; regenerate from source CSVs/manifests.
4. Keep the article repo focused on manuscript-facing figures, generated table
   TeX, small provenance CSV/JSON/MD files, and compact frozen artifacts.
5. Keep full runtime data in `project1_ucsc_phd_runtime`, not in the article or
   corrections repos.
6. When space is tight, clean only non-authoritative old runtime heavy
   artifacts after confirming the post-stage CSV/PNG/PDF evidence has been
   generated and frozen where needed.

## Corrections-Article Audit Plan

The next audit should be a response-letter/manuscript crosswalk, not another
model-relaunch pass unless new evidence identifies a specific scientific issue.

Checklist:

- [ ] Build a table of every editor/reviewer item in
  `Corrections---Project-1/tracker_master.csv`.
- [ ] For each item, map:
  - response location in `Corrections---Project-1/main.tex`;
  - revised manuscript location in `wileyNJD-APA.tex`;
  - evidence table/figure/artifact path;
  - whether the response claim is already present in the manuscript.
- [ ] Check all model labels (`N`, `AL`, `exAL`, `U`, `M`, `T0`, `T1`) against
  the manifest labels.
- [ ] Check all CRPS/check-loss values against generated TeX and source CSVs.
- [ ] Check all horizon language:
  - 28-day tables exclude `RAW-NWS`;
  - 8-day NWS-horizon tables include `RAW-NWS`.
- [ ] Check forecast-input timing language:
  - post-cutoff USGS is verification only;
  - post-cutoff forecast precipitation and soil moisture are forecast inputs;
  - GDPC/PCA is not forecast the same way as PPT/SOIL.
- [ ] Check the five-cutoff selection justification once the final wording is
  available.
- [ ] Compile both documents and run cross-repo validators.

## Current Takeaway

The current results are coherent enough to serve as the authoritative revision
baseline. The remaining high-value work is not to keep chasing model cells
blindly; it is to make the revised article and corrections article fully
cross-referenced, numerically synchronized, and explicit about which evidence
supports each reviewer response. Future calibration remains possible, but it
must replace the current baseline through manifests and validators rather than
manual edits.
