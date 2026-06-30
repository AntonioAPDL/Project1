# HE2 Univariate AL/exAL Scale-Repair Promotion Plan

Date: 2026-06-30

## Purpose

This plan defines the clean promotion path for the repaired univariate
`AL-U-T1` and `exAL-U-T1` HE2 benchmark rows after the legacy univariate
scale-contamination fix. It is intentionally limited to promotion, generated
artifact refresh, and validation. It does not call for new model launches.

The immediate objective is to replace the stale univariate AL/exAL publication
rows with the repaired runs, then regenerate all dependent tables, figures,
poster data, and corrections-repo fragments through the existing reproducible
generators rather than hand editing any numeric artifact.

## Source of Truth

### Repaired runtime authority

Runtime root:

```text
/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_univar_al_exal_scale_repair_20260629
```

Final health evidence:

```text
reports/he2_univar_al_exal_scale_repair_final_health_20260630/
```

Key evidence files:

- `summary.json`
- `repaired_crps_28day_summary.csv`
- `repaired_vs_current_article_crps_comparison.csv`

All 70 quantile logs in the repaired campaign record the intended scale
contract:

```text
UNIV legacy scale contract: fit_input=log1p_cms; fit_internal=log1p_cms; transform_policy=log1p_only
```

The repaired campaign produced all ten cutoff-family rows:

- 5 cutoffs x `AL-U-T1`
- 5 cutoffs x `exAL-U-T1`

It also passed fit, post, validate, and report stages for the campaign matrix.

### Current stale publication authority

The workflow manifest builder still has the old univariate baseline root in
`scripts/build_he2_bayesian_publication_manifest.py`:

```python
PROMOTED_UNIVAR_AL_EXAL_ROOT = RUNTIME_ROOT / "multimodel_v8_he2_univar_al_exal_publication_relaunch_20260603"
```

The active replacement overlay is:

```text
config/he2_publication_manifest_replacement_overlay_current_authority_20260623.yaml
```

That overlay currently replaces `AL-U-T1` using the 2026-06-12 targeted repair
root and leaves `exAL-U-T1` on the 2026-06-03 root. Therefore the revised
article, corrections response, HE4 check-loss artifact, and poster derived data
still contain stale univariate values.

## Evidence Summary

The repaired 28-day CRPS values are:

| cutoff | AL-U-T1 | exAL-U-T1 |
| --- | ---: | ---: |
| 2021-01-23 | 0.231069 | 0.216222 |
| 2021-11-12 | 0.077948 | 0.101942 |
| 2021-12-21 | 0.870493 | 0.833366 |
| 2022-05-11 | 0.105058 | 0.124522 |
| 2022-12-25 | 1.733757 | 1.705479 |

The repaired common eight-day CRPS values are:

| cutoff | AL-U-T1 | exAL-U-T1 |
| --- | ---: | ---: |
| 2021-01-23 | 0.188354 | 0.189994 |
| 2021-11-12 | 0.103669 | 0.113125 |
| 2021-12-21 | 0.756253 | 0.779391 |
| 2022-05-11 | 0.035991 | 0.044895 |
| 2022-12-25 | 0.620016 | 0.629815 |

The current article/corrections values are much larger because they resolve to
the old source roots. For example, the current 28-day publication rows include:

- `AL-U-T1`, 2022-12-25: `3.665288` from
  `multimodel_v8_he2_table1_targeted_repair_20260612`
- `exAL-U-T1`, 2022-12-25: `3.595278` from
  `multimodel_v8_he2_univar_al_exal_publication_relaunch_20260603`

The repaired rows are not merely better by CRPS. They are the first rows that
enforce the intended univariate `log1p` scale contract consistently in the
legacy univariate bridge. That makes promotion a correctness repair, not just a
model-selection change.

## Critical Design Decision

### Recommended: selective overlay promotion

Promote the repaired rows through the replacement overlay instead of changing
the global `PROMOTED_UNIVAR_AL_EXAL_ROOT` constant.

Rationale:

1. The overlay is already the publication mechanism for selective row
   supersession.
2. It preserves provenance for each promoted row: old run, new run, reason,
   lineage, and publication note.
3. It avoids unintended changes to any unrelated family.
4. It supports mixed authority, which is already needed because the same overlay
   contains Table 1 targeted repairs and exAL-M-T1 partial-screen replacements.

Changing the global root would be less explicit and would blur whether a row was
base-promoted or repaired after a diagnosed scale defect. The overlay is the
more auditable path.

### Required companion update

The manifest builder only accepts a fixed set of replacement lineage prefixes.
Before adding the new repaired replacements, extend
`ALLOWED_REPLACEMENT_LINEAGE_PREFIXES` in
`scripts/build_he2_bayesian_publication_manifest.py` with a new prefix such as:

```text
he2_univar_al_exal_scale_repair_20260629:
```

Do not add this to `ALLOWED_EXAL_KEEP_REPLACEMENT_LINEAGE_PREFIXES`, because the
scale repair affects only `AL-U-T1` and `exAL-U-T1`, not `exAL-M-T1`.

## Implementation Phases

### Phase 0 - Freeze the current source repair package

Before promotion, make sure the source-side repair is reviewable:

- Keep the source changes that define the univariate scale contract.
- Keep the tests that enforce the contract.
- Keep the relaunch config and plan docs.
- Do not commit the runtime `reports/` health bundle unless a compact evidence
  snapshot is explicitly desired.
- Do not commit `temp_exdqlm_univar_authoritative_figures_20260629/`.

Current untracked/modified repair files should be reviewed as a unit before the
promotion overlay is committed.

### Phase 1 - Promote repaired rows in the HE2 manifest overlay

Update:

```text
config/he2_publication_manifest_replacement_overlay_current_authority_20260623.yaml
```

Add explicit replacements for all ten repaired rows:

- `20210123`, `20211112`, `20211221`, `20220511`, `20221225`
- families `dqlm_univar_al` and `exdqlm_univar`
- labels `AL-U-T1` and `exAL-U-T1`

Each replacement should specify:

- `cutoff`
- `family`
- `manuscript_label`
- `run_id`
- `run_root`
- `campaign_lineage`
- `replacement_reason`
- `publication_note`
- `replaced_source_run_id`

Use per-row `run_root` fields. Do not change the overlay-level `artifact_root`
to the repaired root, because existing unrelated overlay rows still rely on the
2026-06-12 targeted-repair root.

Recommended lineage:

```text
he2_univar_al_exal_scale_repair_20260629:log1p_scale_repair
```

Recommended replacement reason:

```text
legacy_univariate_loglog_scale_contamination_repaired
```

The publication note should say, compactly, that the legacy univariate bridge now
uses `log1p_cms` as both fit input and internal fit scale, all stages passed, the
canonical input bundle was retained, and no heavy `.RData`/`.rda` objects are
publication artifacts.

### Phase 2 - Rebuild the workflow-side HE2 publication manifest

Run the manifest builder from the workflow repo:

```bash
python3 scripts/build_he2_bayesian_publication_manifest.py
```

Expected outputs:

```text
reports/he2_publication_manifest/he2_bayesian_publication_manifest.csv
reports/he2_publication_manifest/he2_bayesian_publication_manifest.md
reports/he2_publication_manifest/he2_publication_parity_gate.csv
reports/he2_publication_manifest/he2_publication_parity_gate.md
reports/he2_publication_manifest/he2_publication_parity_gate_summary.json
```

Gate checks:

- exactly 45 HE2 Bayesian rows
- all five `AL-U-T1` rows point to the 2026-06-29 scale-repair root
- all five `exAL-U-T1` rows point to the 2026-06-29 scale-repair root
- all ten repaired rows have `campaign_lineage` beginning with
  `he2_univar_al_exal_scale_repair_20260629:`
- all ten repaired rows have the expected canonical input-bundle id
- all ten repaired rows pass fit, post, validate, and report
- all ten repaired rows retain the intended `log_cms_plus1` score scale
- no unrelated family changes unexpectedly

### Phase 3 - Refresh the revised-article HE2 publication freeze

Copy the rebuilt workflow manifest into the revised article publication freeze:

```bash
python3 Evironmetrics---REVISED-DOC-Corrected-2/scripts/refresh_he2_manifest_snapshot.py \
  --article-root Evironmetrics---REVISED-DOC-Corrected-2 \
  --workflow-root .
```

Expected article-side outputs:

```text
Evironmetrics---REVISED-DOC-Corrected-2/artifacts/he2_publication_freeze/he2_bayesian_publication_manifest.csv
Evironmetrics---REVISED-DOC-Corrected-2/artifacts/he2_publication_freeze/he2_bayesian_publication_manifest.md
```

This must be done before regenerating article tables or HE4 check-loss tables,
because those generators are manifest-driven.

### Phase 4 - Update revised-article runtime bindings for univariate reference figures

Update:

```text
Evironmetrics---REVISED-DOC-Corrected-2/config/runtime_bindings.json
```

Set:

```json
"univar_runtime_root": "/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_univar_al_exal_scale_repair_20260629"
```

This is necessary because
`Evironmetrics---REVISED-DOC-Corrected-2/scripts/refresh_cutoff_synthesis_families.py`
uses the runtime binding plus the canonical univariate run IDs to refresh the
reference synthesis artifacts. Without this, tables could be repaired while the
appendix/poster univariate figures still point at stale 2026-06-03 outputs.

Optional robustness improvement:

- Update the fallback default in
  `Evironmetrics---REVISED-DOC-Corrected-2/scripts/article_runtime_bindings.py`
  only if the project wants the repaired root to be the default when
  `runtime_bindings.json` is absent. This is useful but not required while the
  config file is tracked and validated.

### Phase 5 - Regenerate HE4 check-loss artifacts

HE4 is not independent of the HE2 manifest. It resolves the four synthesis
competitors from the frozen HE2 publication manifest and cross-checks CRPS
against each run-local summary.

Run from the workflow repo:

```bash
python3 scripts/build_he4_quantile_check_loss_tables.py \
  --source-mode he2-publication-manifest \
  --he2-publication-manifest Evironmetrics---REVISED-DOC-Corrected-2/artifacts/he2_publication_freeze/he2_bayesian_publication_manifest.csv \
  --output-dir Evironmetrics---REVISED-DOC-Corrected-2/artifacts/he4_quantile_check_loss_current_publication
```

Expected checks inside the generator:

- exactly one HE4 row for each cutoff and each model label:
  `exAL-M-T1`, `AL-M-T1`, `exAL-U-T1`, `AL-U-T1`
- run-root/run-id consistency
- manifest CRPS matches run-local CRPS within tolerance
- required quantile CSV exists
- forecast horizon length matches the manifest horizon
- quantile columns are monotone

This phase must happen before rebuilding revised-article table includes,
because `tab:he4_quantile_check_loss` reads the generated wide CSV from this
artifact directory.

### Phase 6 - Regenerate revised-article generated table includes

Run:

```bash
python3 Evironmetrics---REVISED-DOC-Corrected-2/scripts/build_generated_table_includes.py \
  --article-root Evironmetrics---REVISED-DOC-Corrected-2
```

Expected refreshed files include:

```text
Evironmetrics---REVISED-DOC-Corrected-2/tables/generated_tex/benchmark_crps_horizon_summary.csv
Evironmetrics---REVISED-DOC-Corrected-2/tables/generated_tex/benchmark_crps_body.tex
Evironmetrics---REVISED-DOC-Corrected-2/tables/generated_tex/benchmark_crps_nws_horizon_body.tex
Evironmetrics---REVISED-DOC-Corrected-2/tables/generated_tex/he4_quantile_check_loss_rows.tex
```

The article generator already uses fixed five-decimal rendering for
publication-facing numeric cells. Do not hand edit these files.

### Phase 7 - Refresh univariate reference synthesis figures

Run the cutoff synthesis refresh after updating `runtime_bindings.json`:

```bash
python3 Evironmetrics---REVISED-DOC-Corrected-2/scripts/refresh_cutoff_synthesis_families.py \
  --article-root Evironmetrics---REVISED-DOC-Corrected-2
```

Expected refreshed roots:

```text
Evironmetrics---REVISED-DOC-Corrected-2/artifacts/five_cutoff_reference_synthesis/
Evironmetrics---REVISED-DOC-Corrected-2/figures/reference_synthesis_by_cutoff/
Evironmetrics---REVISED-DOC-Corrected-2/Figures/reference_synthesis_by_cutoff/
```

The 2022-12-25 reference synthesis manuscript figure should also refresh through
the existing copy pathway if the script updates the representative target:

```text
Evironmetrics---REVISED-DOC-Corrected-2/figures/manuscript/reference_synthesis_univariate.png
```

If the targeted refresh does not update every manuscript-facing copy, use the
standard full asset refresh only after reviewing expected churn:

```bash
python3 Evironmetrics---REVISED-DOC-Corrected-2/scripts/refresh_all_generated_assets.py \
  --article-root Evironmetrics---REVISED-DOC-Corrected-2
```

Recommended order:

1. targeted refresh first
2. inspect changed files
3. full refresh only if a validation gate still identifies stale lineage

### Phase 8 - Regenerate poster derived data and frozen figures

The ISBA 2026 poster has derived CRPS CSVs and frozen figures that are generated
from article-side artifacts. Current derived files still contain stale
`AL-U-T1` and `exAL-U-T1` values.

Run:

```bash
cd Evironmetrics---REVISED-DOC-Corrected-2
Rscript --vanilla isba2026_poster/scripts/build_poster_figures.R
```

Then rebuild palette previews only if the active poster workflow requires them:

```bash
python3 isba2026_poster/scripts/render_palette_variants.py
```

Validation checks:

- `isba2026_poster/data/derived/benchmark_crps_28d_long.csv` contains repaired
  univariate values.
- `isba2026_poster/data/derived/benchmark_crps_8d_long.csv` contains repaired
  univariate values.
- no poster derived CSV retains the 2026-06-03 or 2026-06-12 univariate
  stale source values for `AL-U-T1`/`exAL-U-T1`.

### Phase 9 - Sync corrections response tables from the revised article

Run:

```bash
python3 Evironmetrics---REVISED-DOC-Corrected-2/scripts/sync_corrections_generated_table_includes.py \
  --article-root Evironmetrics---REVISED-DOC-Corrected-2 \
  --corrections-root /data/muscat_data/jaguir26/Corrections---Project-1
```

This updates the corrections-side generated fragments:

```text
/data/muscat_data/jaguir26/Corrections---Project-1/tables/generated_tex/he2_benchmark_crps_response_table.tex
/data/muscat_data/jaguir26/Corrections---Project-1/tables/generated_tex/he2_benchmark_crps_nws_horizon_response_table.tex
/data/muscat_data/jaguir26/Corrections---Project-1/tables/generated_tex/he4_quantile_check_loss_response_table.tex
```

The sync script asserts fixed five-decimal precision. Do not hand edit these
response table fragments.

### Phase 10 - Validation gates

Run workflow-side checks:

```bash
python3 -m py_compile \
  scripts/build_he2_bayesian_publication_manifest.py \
  scripts/build_he4_quantile_check_loss_tables.py \
  scripts/validate_publication_freeze.py \
  scripts/validate_revision_cross_repo_wiring.py

python3 -m unittest \
  tests.python.test_log1p_transform_policy \
  tests.python.test_environmetrics_scale_contract_source_contract \
  tests.python.test_he2_univar_scale_repair_relaunch \
  -v

Rscript --vanilla -e "testthat::test_file('tests/testthat/test_univar_legacy_scale_contract.R'); testthat::test_file('tests/testthat/test_post_artifact_contract.R')"

python3 scripts/validate_publication_freeze.py \
  --require-clean \
  --report-dir reports/publication_freeze_validation_20260630_univar_scale_promotion

python3 scripts/validate_revision_cross_repo_wiring.py \
  --after-patch \
  --output-dir reports/revision_cross_repo_validation_20260630_univar_scale_promotion
```

Run revised-article checks:

```bash
cd Evironmetrics---REVISED-DOC-Corrected-2
python3 -m unittest discover -s tests -v
python3 scripts/validate_authoritative_output_lineage.py \
  --article-root . \
  --corrections-root /data/muscat_data/jaguir26/Corrections---Project-1
python3 scripts/validate_manuscript_figure_paths.py --article-root .
pdflatex -interaction=nonstopmode -halt-on-error -jobname=output wileyNJD-APA.tex
bibtex output
pdflatex -interaction=nonstopmode -halt-on-error -jobname=output wileyNJD-APA.tex
pdflatex -interaction=nonstopmode -halt-on-error -jobname=output wileyNJD-APA.tex
```

Run corrections-repo checks:

```bash
cd /data/muscat_data/jaguir26/Corrections---Project-1
make
```

Additional targeted stale-value checks:

```bash
rg -n "univar_al_exal_publication_relaunch_20260603|he2tbl1fix20260612_.*(dqlm_univar_al|exdqlm_univar)" \
  Evironmetrics---REVISED-DOC-Corrected-2 \
  /data/muscat_data/jaguir26/Corrections---Project-1
```

Interpretation:

- Stale `exdqlm_univar` references to the 2026-06-03 root should be gone from
  publication-facing manifests, tables, HE4 artifacts, and poster derived data.
- Stale `dqlm_univar_al` references to the 2026-06-12 targeted-repair root
  should be gone from the same places.
- References to the 2026-06-12 targeted-repair root may remain for unrelated
  families such as NDLM or multivariate drop rows.

## Risk Register

| risk | why it matters | mitigation |
| --- | --- | --- |
| New lineage rejected by manifest builder | The builder restricts replacement lineage prefixes | Add only `he2_univar_al_exal_scale_repair_20260629:` to `ALLOWED_REPLACEMENT_LINEAGE_PREFIXES` |
| Overlay-level root changed accidentally | Existing unrelated replacements would resolve against the wrong root | Use per-row `run_root` for all ten repaired rows |
| Tables fixed but figures stale | Reference synthesis uses `runtime_bindings.json`, not only the HE2 manifest | Update `univar_runtime_root` and refresh figure families |
| HE4 stale after HE2 promotion | HE4 stores resolved run roots and check-loss values | Regenerate HE4 after refreshing the article HE2 manifest |
| Poster stale after article update | Poster has its own derived CSVs and frozen figures | Rebuild poster figures from article-side generated tables |
| Large artifacts committed | Overleaf/GitHub sync can fail on oversized blobs | Keep runtime reports, `.RData`, `.rda`, large caches, and temp folders untracked |
| Full asset refresh causes unrelated churn | The article repo has many generated assets | Prefer targeted refresh first, then run full refresh only if validation requires it |

## Commit Strategy

Use small commits by repository and purpose:

1. Workflow source repair contract, tests, and relaunch docs.
2. Workflow HE2 promotion overlay and manifest-builder lineage gate.
3. Revised article manifest snapshot, generated tables, HE4 artifacts, runtime
   binding, and refreshed univariate reference figures.
4. Poster derived data and frozen figure refresh if changed separately.
5. Corrections generated table sync.

Do not commit:

- runtime `reports/` validation output unless explicitly selected as compact
  evidence
- `.RData`
- `.rda`
- large runtime caches
- temporary figure-inspection directories

Push only after all validation gates for the affected repositories pass.

## Readiness Checklist

- [x] Repaired univariate AL/exAL runtime completed.
- [x] Final health evidence exists under `reports/`.
- [x] Repaired CRPS values are materially better than stale publication rows.
- [x] The stale publication roots have been identified in article, corrections,
  HE4, and poster artifacts.
- [ ] Source repair files reviewed and committed.
- [ ] Manifest builder accepts the new scale-repair lineage prefix.
- [ ] Overlay contains all ten repaired `AL-U-T1`/`exAL-U-T1` replacements.
- [ ] Workflow HE2 manifest rebuilt and checked.
- [ ] Revised article HE2 freeze refreshed.
- [ ] HE4 check-loss artifact rebuilt from the refreshed HE2 manifest.
- [ ] Revised article generated table includes rebuilt.
- [ ] Univariate reference synthesis figures refreshed from the repaired root.
- [ ] Poster derived data rebuilt from refreshed table artifacts.
- [ ] Corrections generated tables synced from revised article.
- [ ] Cross-repo validators pass.
- [ ] Revised article compiles.
- [ ] Corrections response compiles.

## Recommendation

This is the optimal next move because it treats the repaired univariate outputs
as a correctness fix, promotes them through the existing selective-authority
mechanism, and forces every publication-facing artifact to be regenerated from
machine-readable provenance. The plan avoids relaunching models, avoids hand
editing numeric tables, and adds validation at the exact points where stale
lineage previously survived: the HE2 manifest snapshot, HE4 check-loss artifact,
reference synthesis figures, poster derived data, and corrections table
fragments.
