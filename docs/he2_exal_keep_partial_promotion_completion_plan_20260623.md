# HE2 exAL-M-T1 Partial-Screen Promotion Completion Plan

Date: 2026-06-23

## Purpose

This plan completes the interrupted promotion of improved HE2
`exAL-M-T1` / `exdqlm_multivar_keep` screening specifications into the
publication-authoritative workflow, revised article, corrections response, and
poster materials.

The plan is intentionally conservative. The current local state contains a
valid partial-screen overlay, but it is not yet a finished publication freeze:
the overnight screening campaign is still running, the clean authority replay
has not completed, the corrections response tables are stale, and poster inputs
still reference older benchmark values.

## Current Evidence

### Workflow Repository

Repository:

`/data/muscat_data/jaguir26/project1_ucsc_phd`

Current branch is `main`, tracking `origin/main`. Local uncommitted files
include the partial promotion overlay, helper scripts, validators, manifest
builder changes, and tests.

Important local files:

- `config/he2_publication_manifest_replacement_overlay_current_authority_20260623.yaml`
- `config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_partial_authority_refresh_20260623.template.yaml`
- `scripts/manage_he2_exal_keep_partial_promotion.py`
- `scripts/validate_he2_exal_keep_partial_screen_promotion.py`
- `scripts/host_finish_he2_exal_keep_partial_promotion.sh`
- `docs/exdqlm_multivar_keep_partial_screen_promotion_20260623.md`

The dedicated partial-screen validator passes:

```text
checks=24 failed=0
```

### Screening Runtime

Screening root:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_overnight_screen_20260619`

Current matrix status at audit time:

| status | count |
|---|---:|
| pass | 215 |
| fail | 73 |
| pending | 4 |
| not_started | 23 |
| total | 315 |

The screening campaign remains active, so it is not a final full-grid
authority. A partial promotion is still valid only if explicitly documented as
best-so-far evidence from completed rows.

The screening root currently retains no heavy `.RData`/`.rda` files.

### Promoted Partial-Screen Rows

The current local overlay promotes exactly three improved rows:

| cutoff | previous authoritative run | promoted screening run | old CRPS | new CRPS |
|---|---|---|---:|---:|
| `20211221` | `multimodel_20211221_v8_he2grid_c03_eps030_exdqlm_multivar_keep` | `multimodel_20211221_v8_he2grid_s02_eps030_exdqlm_multivar_keep` | 0.26537 | 0.26045 |
| `20220511` | `multimodel_20220511_v8_he2grid_c02_eps060_exdqlm_multivar_keep` | `multimodel_20220511_v8_he2grid_s06_eps001_exdqlm_multivar_keep` | 0.03233 | 0.02273 |
| `20221225` | `multimodel_20221225_v8_he2grid_c05_eps030_exdqlm_multivar_keep` | `multimodel_20221225_v8_he2grid_s01_eps001_exdqlm_multivar_keep` | 0.66546 | 0.53806 |

The `20210123` and `20211112` cutoffs remain on the previous authority because
their best completed screening rows were worse at the checkpoint.

### Revised Article

Repository:

`/data/muscat_data/jaguir26/project1_ucsc_phd/Evironmetrics---REVISED-DOC-Corrected-2`

The revised article has local uncommitted HE2 freeze/table changes. Its current
generated article tables already show the promoted `exAL-M-T1` CRPS values:

```text
exAL-M-T1 & 0.13971 & 0.04724 & 0.26045 & 0.02273 & 0.53806
```

This is locally consistent with the partial overlay, but not yet committed or
pushed.

### Corrections Response

Repository:

`/data/muscat_data/jaguir26/Corrections---Project-1`

The corrections repo is clean but stale. It still contains older HE2 table
values:

```text
exAL-M-T1 & 0.13971 & 0.04724 & 0.26537 & 0.03233 & 0.66546
```

Therefore cross-repo validation is expected to fail until corrections generated
tables are synchronized from the revised article outputs.

### Poster

Poster root:

`/data/muscat_data/jaguir26/project1_ucsc_phd/Evironmetrics---REVISED-DOC-Corrected-2/isba2026_poster`

Poster derived CRPS inputs still contain the older `exAL-M-T1` values for the
improved cutoffs, for example:

```text
20211221,0.26537
20220511,0.03233
20221225,0.66546
```

The poster must therefore be refreshed after the publication manifest is
rebuilt.

### Clean Authority Replay

Clean replay root:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_partial_authority_refresh_20260623`

The root did not exist before this audit. A dry-run/prelaunch inspection created
matrix/config control files but was interrupted before any full clean queue was
launched. No clean authority runs are currently active.

The generated clean replay matrix targets exactly three run IDs:

| cutoff | clean replay run id | source selected run |
|---|---|---|
| `20211221` | `multimodel_20211221_v8_he2partial20260623_exdqlm_multivar_keep` | `multimodel_20211221_v8_he2grid_s02_eps030_exdqlm_multivar_keep` |
| `20220511` | `multimodel_20220511_v8_he2partial20260623_exdqlm_multivar_keep` | `multimodel_20220511_v8_he2grid_s06_eps001_exdqlm_multivar_keep` |
| `20221225` | `multimodel_20221225_v8_he2partial20260623_exdqlm_multivar_keep` | `multimodel_20221225_v8_he2grid_s01_eps001_exdqlm_multivar_keep` |

The frozen specs inherit the canonical `20260510_publication_shared_r01` input
bundle, full seven quantile lanes, `log1p_cms` scale, full transfer features,
and cleanup-after-post behavior.

## Critical Correction to the Existing Helper Plan

The current host helper correctly includes preflight, pause, clean launch,
article sync, validation, and commit steps. However, its usage note says that
the publication overlay remains a partial-screen overlay until a later explicit
clean-rerun overlay promotion.

For a publication-grade finish, that is not enough. The optimal workflow is:

1. use the partial-screen overlay as the source for the clean replay,
2. run and validate the clean replay,
3. create a new final overlay that points to the clean replay run roots,
4. rebuild all manifests/tables/figures from that clean overlay,
5. then commit and push.

This avoids publishing article/poster/corrections artifacts whose authority
points back to an exploratory screening campaign.

## Recommended Completion Workflow

### Phase 1: Freeze Current State and Pause Screening

Goal: preserve evidence before stopping the active exploratory campaign.

Actions:

1. Run `scripts/manage_he2_exal_keep_partial_promotion.py status`.
2. Copy `matrix_status.csv`, `matrix_plan.csv`, queue logs, and promotion
   summaries into `reports/he2_exal_keep_partial_screen_promotion_20260623/`.
3. Dry-run the pause process and inspect matched processes.
4. Send `SIGTERM` only to processes containing `overnight_screen_20260619`.
5. Confirm that unrelated production monitors/runs, especially
   `dqlm_multivar_al_drop_p5_production_20260606`, remain untouched.

Why this is optimal:

- The current screening is exploratory and incomplete, so pausing it is lower
  risk than continuing to spend cores while the publication authority is being
  rebuilt.
- Checkpointing first preserves the exact best-so-far decision boundary.
- Matching only the screening token avoids interfering with older or unrelated
  production campaigns.

Validation gates:

- `screen_processes_before_pause.csv` exists.
- `matrix_status.csv` checkpoint exists.
- no active process contains `overnight_screen_20260619`.
- unrelated production process tokens are still present if they were present
  before the pause.

### Phase 2: Clean the Prelaunch Side Effects and Rebuild Matrix

Goal: ensure the clean replay starts from a known state.

Actions:

1. Remove or archive the interrupted prelaunch validation directory under the
   clean replay root if it contains only smoke-test residue.
2. Run the relaunch config builder explicitly.
3. Validate the matrix/control files without launching the queue.
4. Inspect `matrix_plan.csv` and `frozen_spec_manifest.csv`.

Why this is optimal:

- The `--dry-run` relaunch command is not fully side-effect-free; it can run
  prelaunch smoke validation. The implementation should avoid treating
  `--dry-run` as a harmless print-only command.
- Rebuilding matrix/control files after cleanup prevents ambiguous evidence
  from the interrupted smoke attempt.

Validation gates:

- matrix has exactly three rows;
- all rows are `exdqlm_multivar_keep` / `exAL-M-T1`;
- active quantiles are `05|20|35|50|65|80|95`;
- selected source runs are exactly `s02_eps030`, `s06_eps001`, and `s01_eps001`;
- `cleanup_rdata_after_post` is enabled in generated configs;
- canonical bundle metadata points to `20260510_publication_shared_r01`.

### Phase 3: Launch and Monitor Clean Authority Replay

Goal: produce clean publication-authority runs independent of the exploratory
screening root.

Actions:

1. Launch the three-row clean replay with `--reset-state --start-monitor`.
2. Monitor until all three rows are terminal.
3. Require all three rows to pass; do not accept failed clean replay rows as
   authority.

Why this is optimal:

- The publication authority becomes reproducible from a small dedicated root.
- The three-row scope minimizes runtime and disk pressure while preserving all
  seven quantile models per cutoff.
- Running these as clean replays separates the publication freeze from the
  unfinished screening experiment.

Validation gates:

- `matrix_status.csv` has exactly three `pass` rows.
- each run manifest has `fit`, `post`, `validate`, and `report` status `pass`;
- each run has the required post outputs:
  - `publication_figure_manifest.csv`;
  - synthesis plots with and without raw ensembles;
  - `tables/crps_forecast_summary.csv`;
  - `tables/crps_forecast_per_time.csv`;
  - `tables/covariate_effects_summary.csv`;
  - gamma/sigma summaries;
- no `.RData`/`.rda` files remain after post-stage cleanup.

### Phase 4: Promote Clean Replay as Authority

Goal: replace the temporary partial-screen overlay with a clean-authority
overlay.

Actions:

1. Promote with the guarded helper:

   ```bash
   python3 scripts/promote_he2_exal_keep_clean_authority.py \
     --out-dir reports/he2_exal_keep_clean_authority_promotion_20260623 \
     --apply
   ```

   The helper validates the clean replay before writing the overlay. It fails
   if any selected run is missing, still pending, missing required post outputs,
   worse than the 2026-06-01 authority, or retaining heavy `.RData`/`.rda`
   files.

2. Update this overlay in place:

   `config/he2_publication_manifest_replacement_overlay_current_authority_20260623.yaml`

   updated in place, plus an archived copy of the partial-screen overlay if
   needed for audit context.

3. For the three `exAL-M-T1` rows, set:
   - `run_id` to the clean replay run ID;
   - `run_root` to the clean replay root;
   - `campaign_lineage` to a clean replay lineage, for example
     `exdqlm_multivar_keep_partial_authority_refresh_20260623:clean_replay`;
   - `replaced_source_run_id` to the previous 2026-06-01 authority;
   - a note that the clean replay reproduces the selected partial-screen specs.

4. Validate the selected overlay against the clean root:

   ```bash
   python3 scripts/validate_he2_exal_keep_partial_screen_promotion.py \
     --screen-root /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_partial_authority_refresh_20260623 \
     --out-dir reports/he2_exal_keep_clean_authority_promotion_20260623/selected_overlay_validation
   ```

5. Keep the helper script
   `scripts/host_finish_he2_exal_keep_partial_promotion.sh` synchronized with
   this order: `wait-clean`, `promote-clean`, `sync-articles`, `validate`,
   `commit`.

Why this is optimal:

- The manifest no longer depends on unfinished exploratory screening outputs.
- The partial-screen decision remains documented, but the publication freeze
  points to a compact clean replay.
- Future users can reproduce exactly the promoted rows without replaying the
  entire screening grid.

Validation gates:

- manifest builder accepts only documented replacement lineages;
- final overlay has no `exdqlm_multivar_keep_partial_screen_20260623:*`
  publication-authority rows except in archived provenance fields;
- CRPS values from clean replay are tied to or numerically consistent with the
  selected screening values within a documented tolerance;
- canonical input bundle checks pass.

### Phase 5: Rebuild Workflow Publication Manifest

Goal: make the workflow repo the source of truth for the new authority.

Actions:

1. Run `scripts/build_he2_bayesian_publication_manifest.py`.
2. Run `scripts/build_he2_publication_parity_gate.py`.
3. Inspect the resulting manifest rows for all five `exAL-M-T1` cutoffs.

Why this is optimal:

- Downstream article, corrections, and poster artifacts should consume generated
  manifest outputs, not hand-edited table values.
- The manifest builder already enforces input bundle, covariate, forecast, and
  heavy-file cleanup contracts.

Validation gates:

- `reports/he2_publication_manifest/he2_bayesian_publication_manifest.csv`
  includes clean replay run IDs for the three promoted cutoffs;
- 20210123 and 20211112 remain unchanged;
- main HE2 table values match the clean manifest;
- no heavy `.RData` files are referenced or retained.

### Phase 6: Refresh Revised Article

Goal: update Overleaf-facing article artifacts from the workflow manifest.

Actions:

1. Refresh HE2 manifest snapshot into the revised article repo.
2. Rebuild generated TeX table includes.
3. Promote generated figures to manuscript aliases.
4. Rebuild/compile the revised article.

Why this is optimal:

- The revised article remains lightweight and generated from compact manifests.
- Tables and figures are updated through the same path used by validation,
  reducing the chance of hand-edited inconsistencies.

Validation gates:

- article table rows contain clean-authority values:
  `0.13971`, `0.04724`, `0.26045`, `0.02273`, `0.53806`;
- article tests pass;
- `pdflatex -> bibtex -> pdflatex -> pdflatex` succeeds;
- no oversized support CSVs or runtime objects are added.

### Phase 7: Refresh Corrections Response

Goal: synchronize the response document with the revised article.

Actions:

1. Run the article-provided corrections table sync script.
2. Rebuild the corrections response.
3. Inspect HE2/HE3 generated table fragments.

Why this is optimal:

- The corrections repo should not independently hand-code stale benchmark
  values.
- Syncing from article-generated includes keeps the response and revised
  manuscript aligned.

Validation gates:

- corrections HE2 28-day and NWS-horizon tables match revised article values;
- corrections HE3 ablation full-reference rows are either intentionally
  unchanged or explicitly regenerated from the same authority;
- `make` succeeds.

### Phase 8: Refresh Poster Inputs and Figures

Goal: make ISBA poster figures consume the same authority as the article.

Actions:

1. Identify the poster data build step that writes:
   - `isba2026_poster/data/derived/benchmark_crps_28d_long.csv`;
   - `isba2026_poster/data/derived/benchmark_crps_8d_long.csv`.
2. Rebuild those derived poster CSVs from the article/workflow generated
   tables, not by manual edits.
3. Run the poster figure builder.
4. Compile or smoke-test the poster if the poster source changed.

Why this is optimal:

- The poster is currently stale even though the article tables are locally
  updated.
- Rebuilding poster data from the article/workflow artifacts prevents the
  poster from becoming a separate fork of the benchmark results.

Validation gates:

- poster derived data uses:
  - `20211221 = 0.26045` in the 28-day selected exDQLM row;
  - `20220511 = 0.02273`;
  - `20221225 = 0.53806`;
- poster figures are regenerated after the data refresh;
- no poster claim says the old authority is current.

### Phase 9: Full Cross-Repo Validation

Goal: catch remaining inconsistencies before committing.

Workflow repo:

```bash
python3 -m py_compile \
  scripts/manage_he2_exal_keep_partial_promotion.py \
  scripts/promote_he2_exal_keep_clean_authority.py \
  scripts/validate_he2_exal_keep_partial_screen_promotion.py \
  scripts/build_he2_bayesian_publication_manifest.py \
  scripts/validate_publication_freeze.py \
  scripts/forecast_design_contract.py

python3 -m unittest \
  tests.python.test_he2_exal_keep_partial_screen_promotion \
  tests.python.test_he2_bayesian_publication_manifest -v

python3 scripts/validate_publication_freeze.py \
  --report-dir reports/publication_freeze_validation_20260623_clean_exal_keep_authority

python3 scripts/validate_revision_cross_repo_wiring.py \
  --after-patch \
  --output-dir reports/revision_cross_repo_validation_20260623_clean_exal_keep_authority
```

Revised article:

```bash
python3 -m unittest discover -s tests -v
pdflatex -interaction=nonstopmode -halt-on-error -jobname=output wileyNJD-APA.tex
bibtex output
pdflatex -interaction=nonstopmode -halt-on-error -jobname=output wileyNJD-APA.tex
pdflatex -interaction=nonstopmode -halt-on-error -jobname=output wileyNJD-APA.tex
```

Corrections:

```bash
make
```

Poster:

Run the poster figure builder and poster compile/smoke-test path identified in
Phase 8.

### Phase 10: Commit and Push

Goal: leave all repos clean and pullable from Overleaf/GitHub.

Recommended commit grouping:

1. workflow repo:
   - clean authority overlay and validators;
   - manifest builder updates;
   - documentation and tests.
2. revised article repo:
   - refreshed HE2 freeze artifacts;
   - generated tables;
   - promoted manuscript figures;
   - refreshed poster data/figures if stored there.
3. corrections repo:
   - synchronized generated response tables;
   - any tracker updates needed to document the new authority.

Before push:

- verify no `.RData`, `.rda`, large support CSVs, or runtime report directories
  are staged;
- verify article repo remains Overleaf-safe and lightweight;
- run `git status --short --branch` in all three repos.

After push:

- confirm all repos are clean and at `main...origin/main`;
- note any expected untracked runtime reports.

### Phase 11: Resume Remaining Screening

Goal: continue the exploratory grid after the publication authority is stable.

Actions:

1. Resume only the unfinished rows from the checkpointed screening matrix.
2. Preserve previous `pass`/`fail` statuses.
3. Continue using cleanup-after-post.
4. Treat future improvements as a separate authority proposal, not as an
   automatic overwrite.

Why this is optimal:

- The publication freeze is no longer blocked by exploratory tail rows.
- Future screening discoveries can be evaluated with the same promotion gates.

## Implementation Readiness Checklist

- [ ] Checkpoint active screening matrix and logs.
- [ ] Pause only `overnight_screen_20260619` processes.
- [ ] Clean interrupted dry-run/prelaunch residue from the clean replay root.
- [ ] Rebuild and inspect clean replay matrix.
- [ ] Launch clean replay.
- [ ] Confirm clean replay passes all three rows.
- [ ] Repoint authority overlay from screening roots to clean replay roots.
- [ ] Update validators for clean replay lineage.
- [ ] Rebuild workflow manifest and parity gate.
- [ ] Refresh revised article artifacts and compile.
- [ ] Sync corrections generated tables and compile.
- [ ] Refresh poster derived data and figures.
- [ ] Run full cross-repo validation.
- [ ] Clean heavy runtime objects from clean replay root.
- [ ] Commit and push all three repos.
- [ ] Resume unfinished screening rows.

## Recommendation

Do not publish or push the current partial local state as final. It is useful
and internally validated as a best-so-far partial-screen overlay, but the
publication-grade authority should be the clean replay root. The clean replay
adds little runtime cost relative to the full screening grid and gives a much
stronger provenance story for the revised manuscript, corrections response, and
poster.
