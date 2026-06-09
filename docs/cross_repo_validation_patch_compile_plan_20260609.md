# Cross-Repo Validation, Text Patch, and Compile Plan

Date: 2026-06-09

Related audit:

- `docs/revision_cross_repo_progress_audit_20260609.md`

Repos:

- workflow/code: `/data/muscat_data/jaguir26/project1_ucsc_phd`
- revised article: `/data/muscat_data/jaguir26/project1_ucsc_phd/Evironmetrics---REVISED-DOC-2`
- corrections article: `/data/muscat_data/jaguir26/Corrections---Project-1`

## Goal

Implement a robust cross-repo validation pass that compares:

1. source CSV/JSON/runtime artifacts,
2. generated revised-article TeX tables,
3. corrections/rebuttal TeX tables,
4. manuscript asset manifest entries,
5. table-derived prose claims,
6. and final PDF compile logs.

Then patch the known stale HE2/HE4/revised-article text, compile both
documents, and produce a final validation report.

The output should make the revised article, corrections article, and workflow
repo mutually consistent, traceable, and reproducible for the final paper
revision.

## Non-Goals

- Do not relaunch model fits.
- Do not alter production/runtime campaigns.
- Do not silently replace model values without a source-table audit.
- Do not push until the final validation report and compile checks pass.
- Do not make either LaTeX document depend on absolute runtime paths at compile
  time. Any generated table fragment used by a document must be copied into that
  document repo.

## Current Evidence

### Existing Strong Infrastructure

Workflow-side:

- `scripts/build_he2_bayesian_publication_manifest.py`
- `scripts/build_he2_publication_parity_gate.py`
- `scripts/build_he2_crps_table_readiness_audit.py`
- `scripts/build_he4_quantile_check_loss_tables.py`
- `scripts/audit_he3_exdqlm_ablation.py`
- `scripts/finalize_he3_exdqlm_ablation.py`
- `scripts/sync_he3_ablation_article_tables.py`
- `tests/python/test_he2_bayesian_publication_manifest.py`
- `tests/python/test_he2_publication_parity_gate.py`
- `tests/python/test_he4_quantile_check_loss_tables.py`
- `tests/python/test_he3_exdqlm_ablation_tooling.py`

Revised-article side:

- `MANUSCRIPT_ASSET_MANIFEST.json`
- `scripts/build_generated_table_includes.py`
- `scripts/build_article_asset_review_report.py`
- `scripts/refresh_all_generated_assets.py`
- `scripts/validate_manuscript_figure_paths.py`
- `tables/generated_tex/`
- `artifacts/he2_publication_freeze/`
- `artifacts/he3_exdqlm_ablation_authoritative/`
- `artifacts/representative_selected_model_2022_12_25/`

Corrections side:

- `main.tex`
- `Makefile`
- currently no generated-table infrastructure.

### Confirmed Stale Items

The cross-repo audit found these known stale claims:

| repo | location | issue |
|---|---|---|
| revised article | `wileyNJD-APA.tex` conclusion | says `exAL-M-T1` has lowest CRPS "in every case" |
| corrections | `main.tex` HE2 table | still uses older HE2 values |
| corrections | `main.tex` HE2 prose | says `exAL-M-T1` is best in all five cutoffs and beats raw baselines across the panel |
| corrections | `main.tex` HE7 prose | repeats latest-forecast-only conclusion as best in all five cutoffs |
| corrections | `main.tex` internal TODO block | unresolved submission-facing TODOs remain |
| HE4 workflow | `scripts/build_he4_quantile_check_loss_tables.py` | defaults to old April CF1 sweep, not current June HE2 publication manifest |
| revised article manifest | `MANUSCRIPT_ASSET_MANIFEST.json` | no HE4 table entry |

## Source of Truth Policy

### HE2 CRPS Benchmark

Primary publication source:

- revised article artifact freeze:
  `Evironmetrics---REVISED-DOC-2/artifacts/he2_publication_freeze/he2_bayesian_publication_manifest.csv`
- raw-reference source:
  `Evironmetrics---REVISED-DOC-2/artifacts/five_cutoff_crps_validation_sources/*/crps_forecast_summary.csv`

Validation cross-check:

- workflow-side `reports/he2_publication_manifest/he2_bayesian_publication_manifest.csv`
- workflow-side `reports/he2_publication_manifest/he2_publication_parity_gate_summary.json`

Expected interpretation:

- `exAL-M-T1` wins the first four cutoffs.
- `RAW-NWS` wins the final `2022-12-25` cutoff.
- `AL-M-T1` is the best corrected Bayesian row at `2022-12-25`.
- corrected Bayesian models do not uniformly dominate the raw operational
  baseline.

### HE3 Ablation

Primary publication source:

- `Evironmetrics---REVISED-DOC-2/artifacts/he3_exdqlm_ablation_authoritative/he3_ablation_long.csv`
- `Evironmetrics---REVISED-DOC-2/artifacts/he3_exdqlm_ablation_authoritative/audit__he3_ablation_audit.csv`
- `Evironmetrics---REVISED-DOC-2/artifacts/he3_exdqlm_ablation_authoritative/audit__he3_ablation_runtime_input_detail.csv`

Runtime cross-check:

- `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he3_exdqlm_ablation_authoritative_winners_20260608/control/he3_exdqlm_ablation_authoritative_winners_v1/finalize_status_20260609T165219Z.json`

Expected interpretation:

- all `30/30` rows pass;
- all launched ablation rows preserve inherited inputs/hyperparameters except
  the intended component toggle;
- full `exAL-M-T1` is the best ablation-row value at every cutoff;
- `RAW-NWS` remains better than full `exAL-M-T1` at `2022-12-25` as a reference
  raw-row exception.

### HE4 Quantile Check Loss

Current status:

- runtime evidence exists under the old April CF1 sweep;
- corrections article uses a hard-coded HE4 table;
- revised article does not yet manifest an HE4 table.

Target policy:

Regenerate HE4 from the current HE2 publication manifest. Do not silently reuse
the April CF1 sweep values unless a validator proves they match the current
manifest rows.

Model mapping:

| manuscript label | HE2 family | model id | quantile CSV |
|---|---|---|---|
| `exAL-M-T1` | `exdqlm_multivar_keep` | `exdqlm_multivar_synth_keep` | `exdqlm_multivar_synth_keep_cutoff_window_quantiles.csv` |
| `AL-M-T1` | `dqlm_multivar_al_keep` | `dqlm_multivar_al_synth_keep` | `dqlm_multivar_al_synth_keep_cutoff_window_quantiles.csv` |
| `exAL-U-T1` | `exdqlm_univar` | `exdqlm_univar_synth` | `exdqlm_univar_synth_cutoff_window_quantiles.csv` |
| `AL-U-T1` | `dqlm_univar_al` | `dqlm_univar_al_synth` | `dqlm_univar_al_synth_cutoff_window_quantiles.csv` |

Validation requirements:

- resolve each run from the current HE2 publication manifest, not from
  `best_by_cutoff_long.csv`;
- load forecast-only quantile rows;
- confirm quantile monotonicity;
- confirm `resolved_mean_crps` matches the HE2 row `crps_exact` within
  tolerance;
- write current-publication HE4 CSV/Markdown/TeX outputs;
- decide whether to include HE4 in the revised article manifest or keep it
  corrections-only with explicit provenance.

### Representative Tables

Primary publication source:

- `artifacts/representative_selected_model_2022_12_25/covariate_effects_summary.csv`
- `artifacts/representative_selected_model_2022_12_25/gamma_summary.csv`
- `artifacts/representative_selected_model_2022_12_25/sigma_summary.csv`

Expected validation:

- generated TeX values match CSV values after display rounding;
- table captions/notes correctly mark these as representative and interpretive,
  not primary forecast-validation evidence.

## Implementation Design

### New Workflow-Side Script

Add:

`scripts/validate_revision_cross_repo_wiring.py`

Primary outputs:

`reports/revision_cross_repo_validation_20260609/`

Files:

- `cross_repo_validation_summary.json`
- `cross_repo_validation_summary.md`
- `source_inventory.csv`
- `manifest_path_audit.csv`
- `table_value_audit.csv`
- `table_render_audit.csv`
- `prose_claim_audit.csv`
- `compile_log_audit.csv`

The script should support two modes:

- `--check-only`: fail on stale values/claims without editing files.
- `--after-patch`: run the same checks after text/table patches and compilation.

It should also accept explicit repo paths:

```bash
python3 scripts/validate_revision_cross_repo_wiring.py \
  --workflow-root /data/muscat_data/jaguir26/project1_ucsc_phd \
  --article-root /data/muscat_data/jaguir26/project1_ucsc_phd/Evironmetrics---REVISED-DOC-2 \
  --corrections-root /data/muscat_data/jaguir26/Corrections---Project-1 \
  --output-dir reports/revision_cross_repo_validation_20260609 \
  --check-only
```

### New HE4 Current-Publication Builder Mode

Extend:

`scripts/build_he4_quantile_check_loss_tables.py`

Add a current-manifest mode:

```bash
python3 scripts/build_he4_quantile_check_loss_tables.py \
  --source-mode he2-publication-manifest \
  --he2-publication-manifest Evironmetrics---REVISED-DOC-2/artifacts/he2_publication_freeze/he2_bayesian_publication_manifest.csv \
  --runtime-root /data/muscat_data/jaguir26/project1_ucsc_phd_runtime \
  --output-dir reports/he4_quantile_check_loss_current_publication_20260609
```

Expected outputs:

- `he4_selection_audit.csv`
- `he4_quantile_check_loss_per_day.csv`
- `he4_quantile_check_loss_long.csv`
- `he4_quantile_check_loss_wide.csv`
- `he4_quantile_check_loss_summary.md`
- `he4_table_rows.tex`
- `he4_main_table.tex`

### Corrections Table Strategy

Preferred robust strategy:

1. Add generated-table fragments to the corrections repo:
   - `tables/generated_tex/he2_benchmark_crps_main_table.tex`
   - `tables/generated_tex/he3_ablation_crps_main_table.tex`
   - `tables/generated_tex/he4_quantile_check_loss_main_table.tex`
2. Replace hard-coded HE2, HE3, and HE4 table blocks in `Corrections---Project-1/main.tex`
   with `\input{tables/generated_tex/...}`.
3. Keep the corrections repo standalone by copying generated TeX fragments into
   the corrections repo. Do not require absolute paths during LaTeX compile.
4. The validator compares the corrections generated fragments against the same
   source tables used by the revised article.

Fallback strategy:

- If we want to avoid changing corrections repo structure, patch `main.tex`
  hard-coded tables directly and validate them by parsing the hard-coded TeX.

The preferred strategy is better because it prevents future silent drift.

## Validator Details

### Table Parsing

The validator should implement small deterministic parsers rather than relying
on fragile text greps only.

Required parser behaviors:

- remove display wrappers such as `\textbf{...}`;
- ignore `\midrule`, `\bottomrule`, `\addlinespace`, `\multicolumn`, captions,
  and notes;
- parse row label plus numeric cells;
- round expected source values to the display precision used by each table;
- compare rendered display values, not raw full precision, unless checking
  source CSV equality.

Display tolerances:

| table | display digits | tolerance |
|---|---:|---:|
| HE2 CRPS | 4 | `5e-5` after rounding |
| HE3 CRPS | 4 | `5e-5` after rounding |
| HE4 check loss | 4 | `5e-5` after rounding |
| covariate effects | 3 | `5e-4` after rounding |
| gamma | 3 | `5e-4` after rounding |
| sigma | 5 | `5e-6` after rounding |

### Manifest Path Checks

The validator should verify:

- every `MANUSCRIPT_ASSET_MANIFEST.json` table path exists;
- every table source path in the manifest exists;
- every figure `manuscript_path` exists;
- every figure `source_path` exists;
- every `\input{...}` in `wileyNJD-APA.tex` resolves;
- every `\includegraphics{...}` in `wileyNJD-APA.tex` resolves through the
  known figure search paths;
- every generated table in `tables/generated_tex/manifest.csv` has a
  corresponding manifest table or documented exception;
- HE4 is either present in the revised article manifest or explicitly recorded
  as corrections-only.

### Prose Claim Checks

The validator should compute winners from source tables and check manuscript
claims against those computed facts.

Computed facts:

- HE2 overall winner by cutoff;
- HE2 best corrected Bayesian winner by cutoff;
- whether corrected Bayesian models beat both raw baselines at each cutoff;
- HE3 best ablation row by cutoff;
- HE4 best model by cutoff and quantile cell, if regenerated.

Hard fail forbidden claims:

- `exAL-M-T1` "wins all five" HE2 cutoffs;
- `exAL-M-T1` has lowest CRPS "in every case";
- "best corrected model outperforms the best raw forecast baseline across the
  panel";
- "substantive conclusions unchanged ... best-performing model in all five
  cutoffs";
- any unresolved `% TODO[` line in the corrections article, unless an explicit
  allow-list marks it as intentionally internal and non-submission-facing.

Required claims:

- revised article benchmark/conclusion must mention the final-cutoff raw-NWS
  exception;
- corrections HE2/HE7 must mention the final-cutoff raw-NWS exception or avoid
  all-five overclaims;
- HE3 text must mention that raw rows are references and that raw NWS beats the
  full model at the final cutoff;
- HE4 text must state whether values come from the current HE2 publication
  manifest or are corrections-only legacy evidence.

### Compile Log Checks

Compile revised article:

```bash
cd /data/muscat_data/jaguir26/project1_ucsc_phd/Evironmetrics---REVISED-DOC-2
pdflatex -interaction=nonstopmode -halt-on-error -jobname=output wileyNJD-APA.tex
bibtex output
pdflatex -interaction=nonstopmode -halt-on-error -jobname=output wileyNJD-APA.tex
pdflatex -interaction=nonstopmode -halt-on-error -jobname=output wileyNJD-APA.tex
```

Compile corrections:

```bash
cd /data/muscat_data/jaguir26/Corrections---Project-1
make
```

If `make` fails because `latexmk` is unavailable, the Makefile already falls
back to two `pdflatex` runs.

Fail compile validation on:

- missing file;
- undefined reference;
- undefined citation;
- LaTeX fatal error;
- missing bibliography;
- `?` references in final aux/log.

Report but do not automatically fail on:

- mild overfull/underfull boxes;
- rerun warnings after final pass, unless references remain unresolved.

## Work Plan

### Phase 0. Scope Freeze

1. Confirm all three repos are clean or record local changes.
2. Confirm no model/runtime campaigns are modified.
3. Record current commits and ahead counts.
4. Create `reports/revision_cross_repo_validation_20260609/` for validation
   evidence.

Acceptance gate:

- repo state recorded;
- no runtime modifications made;
- output directory created.

### Phase 1. Build Check-Only Validator

Implement `scripts/validate_revision_cross_repo_wiring.py` with:

- source inventory builder;
- HE2 expected table builder;
- HE3 expected table builder;
- representative expected table builders;
- article generated TeX parser;
- corrections TeX parser;
- manifest path auditor;
- prose claim auditor;
- Markdown/JSON summary writer.

At this phase, the validator is expected to fail because known stale claims are
present.

Acceptance gate:

- validator produces structured evidence;
- known stale HE2/corrections/revised-article conclusion items are detected;
- no false failure on current HE3 table.

### Phase 2. Regenerate HE4 From Current HE2 Manifest

Extend `scripts/build_he4_quantile_check_loss_tables.py` with
`--source-mode he2-publication-manifest`.

Run the current-publication HE4 builder and compare against the existing April
CF1 HE4 values:

```bash
python3 scripts/build_he4_quantile_check_loss_tables.py \
  --source-mode he2-publication-manifest \
  --he2-publication-manifest Evironmetrics---REVISED-DOC-2/artifacts/he2_publication_freeze/he2_bayesian_publication_manifest.csv \
  --runtime-root /data/muscat_data/jaguir26/project1_ucsc_phd_runtime \
  --output-dir reports/he4_quantile_check_loss_current_publication_20260609
```

Acceptance gate:

- all `5 cutoffs x 4 models` resolve;
- every quantile artifact exists;
- every forecast horizon is valid;
- quantile rows are monotone;
- `resolved_mean_crps` matches HE2 `crps_exact`;
- comparison to old HE4 is documented.

### Phase 3. Decide HE4 Article Placement

Decision options:

1. **Preferred**: add HE4 to revised article generated-table manifest, likely in
   the forecast-validation section or appendix, and keep the corrections HE4
   table synchronized from the same fragment.
2. **Acceptable**: keep HE4 corrections-only, but explicitly say the revised
   article reports CRPS while the response letter adds quantile-level detail,
   and store the current-publication HE4 output in article/corrections artifact
   bundles.

Acceptance gate:

- one option is chosen and documented in the validation summary;
- no text claims HE4 is in the revised article if it is not.

### Phase 4. Patch Generated Tables and Text

Patch revised article:

- conclusion paragraph: replace "lowest CRPS in every case" with the exact
  HE2-qualified interpretation;
- if HE4 is promoted, add HE4 generated table and manifest entry;
- otherwise ensure HE4 is not promised as an in-manuscript table.

Patch corrections article:

- update HE2 table from current HE2 publication freeze;
- update HE2 prose to state the final-cutoff raw-NWS exception;
- update HE7 prose to avoid all-five overclaim;
- update HE4 table from current-publication HE4 if generated;
- remove or resolve internal `% TODO[` lines;
- preferably convert HE2/HE3/HE4 tables to generated includes under
  `Corrections---Project-1/tables/generated_tex/`.

Acceptance gate:

- check-only validator passes table and prose checks;
- `git diff` is reviewable and limited to planned docs/scripts/tables/text.

### Phase 5. Manifest and Asset Review

Run article-side asset refresh/validation as appropriate:

```bash
cd /data/muscat_data/jaguir26/project1_ucsc_phd/Evironmetrics---REVISED-DOC-2
python3 scripts/build_generated_table_includes.py --article-root .
python3 scripts/build_article_asset_review_report.py --article-root .
python3 scripts/validate_manuscript_figure_paths.py --article-root .
```

If HE4 is promoted into the article, update the manifest/table generator before
these commands.

Acceptance gate:

- manifest paths exist;
- generated table manifest is current;
- no missing figure path.

### Phase 6. Compile Both Documents

Compile revised article and corrections article with the commands above.

Then run:

```bash
python3 scripts/validate_revision_cross_repo_wiring.py \
  --workflow-root /data/muscat_data/jaguir26/project1_ucsc_phd \
  --article-root /data/muscat_data/jaguir26/project1_ucsc_phd/Evironmetrics---REVISED-DOC-2 \
  --corrections-root /data/muscat_data/jaguir26/Corrections---Project-1 \
  --output-dir reports/revision_cross_repo_validation_20260609 \
  --after-patch
```

Acceptance gate:

- article PDF builds;
- corrections PDF builds;
- compile log audit passes;
- cross-repo validator passes.

### Phase 7. Tests and Final Commit Hygiene

Run focused tests:

```bash
python3 -m unittest \
  tests.python.test_he2_bayesian_publication_manifest \
  tests.python.test_he2_publication_parity_gate \
  tests.python.test_he3_exdqlm_ablation_tooling \
  tests.python.test_he4_quantile_check_loss_tables \
  tests.python.test_revised_article_stage1_refresh_contract \
  -v
```

Add new tests:

- `tests/python/test_revision_cross_repo_validation.py`

Minimum new test coverage:

- TeX numeric parser removes `\textbf{}` and parses rows correctly;
- HE2 expected winner logic detects raw-NWS final-cutoff exception;
- forbidden prose claim detector catches "lowest CRPS in every case";
- manifest checker catches missing table source;
- corrections generated-table include path resolves in fixture;
- HE4 current-manifest source mode resolves fixture rows.

Acceptance gate:

- focused test suite passes;
- `git diff --check` passes in all modified repos;
- final `git status` is clean after intentional commits;
- no push until explicitly approved.

## Expected Deliverables

Workflow repo:

- `scripts/validate_revision_cross_repo_wiring.py`
- updated `scripts/build_he4_quantile_check_loss_tables.py`
- `tests/python/test_revision_cross_repo_validation.py`
- updated HE4 tests if needed
- `reports/revision_cross_repo_validation_20260609/` untracked runtime evidence
- this plan and final closeout doc under `docs/`

Revised article repo:

- patched `wileyNJD-APA.tex`
- optional HE4 generated table and manifest entry
- refreshed generated table includes
- refreshed article asset review reports
- successful compiled PDF/log

Corrections repo:

- patched `main.tex`
- preferably new `tables/generated_tex/` fragments for HE2/HE3/HE4
- successful compiled `main.pdf`

## Success Criteria

The work is complete only when all of these are true:

1. HE2 source CSV values, revised article TeX values, and corrections TeX values
   agree after display rounding.
2. HE3 source CSV values, revised article TeX values, and corrections TeX values
   agree after display rounding.
3. HE4 values are either regenerated from the current HE2 publication manifest
   and synchronized, or explicitly documented as omitted from the revised
   article and corrections-only.
4. No prose claim contradicts computed HE2/HE3/HE4 facts.
5. No unresolved corrections TODO remains.
6. Revised article manifest paths and manuscript figure/table includes resolve.
7. Revised article compiles.
8. Corrections article compiles.
9. Focused regression tests pass.
10. All three repos have intentional, reviewable commits and no accidental
    runtime/report clutter staged.

## Main Risk and Mitigation

| risk | mitigation |
|---|---|
| HE4 current-publication rows cannot resolve quantile CSVs from current HE2 manifest | fail with explicit row-level path evidence; either repair manifest run-root fields or mark HE4 as temporarily blocked |
| corrections generated includes complicate Overleaf upload | keep fragments small, tracked, and relative; document required files in corrections README |
| TeX parsing false positives | unit-test parser with fixtures and compare rounded displays only |
| prose checker misses a new overclaim | use both forbidden phrases and source-derived required-claim checks |
| article compile creates noisy aux/log changes | commit only intended source/table/manifest changes; leave generated aux/log untracked or ignored as appropriate |
| HE2 raw-baseline exception is forgotten again | encode raw-NWS final-cutoff exception as a validator assertion |

## Recommended Immediate Next Move

Implement Phase 1 first and deliberately run it against the current stale state.
That gives us a failing baseline with exact row/line evidence. Then patch text
and tables until the same validator passes. This avoids optimistic manual
editing and gives us a reproducible gate for future article updates.
