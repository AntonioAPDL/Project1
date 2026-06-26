# exDQLM Univariate vs Selected-Support Rebuild Plan

Date: 2026-06-26

## Purpose

This note records the decision plan for whether to relaunch `exdqlm_univar`
with retained `.RData` while the current HE3 ablation campaign is running, and
how that relates to fixing selected article figures.

The immediate goal is not to launch anything. The goal is to separate three
different needs that can otherwise look similar:

1. rebuilding the selected `2022-12-25 exAL-M-T1` component and quantile-dynamic
   diagnostic figures,
2. refreshing the univariate reference synthesis figure family, and
3. refreshing full CRPS/table evidence for the univariate model row.

These are not the same workflow target.

## Current Evidence

### Repository and runtime state

- Workflow repo:
  `/data/muscat_data/jaguir26/project1_ucsc_phd`
- Active branch at this audit point: `main`
- Local git status at this audit point:
  `main...origin/main [ahead 2]`
- Recent local commits:
  - `d71cb6b Clarify HE3 follow-on figure contract`
  - `20260c1 Prepare current-authority HE3 ablation relaunch`

Disk and active-runtime state checked during this audit:

- `/data`: approximately `414G` free.
- Active HE3 root:
  `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he3_exdqlm_ablation_current_authority_20260625`
- Active HE3 root size: approximately `45G`.
- Active HE3 `.RData` at this audit point: `7` files, approximately `43.63 GiB`.
- Existing univariate root:
  `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_univar_all_cutoffs_sharedspec_20260516`
- Existing univariate root size: approximately `246M`.
- Existing univariate retained `.RData`: `0` files.

### Selected-output authority

The current representative selected-output authority is:

`docs/authoritative_selected_outputs/he2_exal_m_t1_representative_20221225.yaml`

Key contract fields:

- model family: `exdqlm_multivar_keep`
- manuscript label: `exAL-M-T1`
- selected cutoff: `2022-12-25`
- selected run:
  `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_partial_authority_refresh_20260623/runs/multimodel_20221225_v8_he2partial20260623_exdqlm_multivar_keep`
- selected spec: `s01_eps001`
- selected score mean CRPS: `0.5380554847458453`
- cleanup policy: cleanup after post is expected, long-term `.RData`
  retention is not expected.

The revised-article runtime binding currently points selected support to:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_selected_output_support_20260625_seasonal_only_current_components/runs/multimodel_20221225_v8_he2partial20260623_exdqlm_multivar_keep_authoritative_support_seasonal_only_20260625/post/outputs/multimodel_20221225_v8_he2partial20260623_exdqlm_multivar_keep_authoritative_support_seasonal_only_20260625`

This binding lives in:

`Evironmetrics---REVISED-DOC-Corrected-2/config/runtime_bindings.json`

## Critical Lineage Correction

The figure-repair question should not default to an `exdqlm_univar` rerun.

### Figure A1 / `fig:80_components`

Figure A1 is currently the selected-model 80-month seasonal-component diagnostic,
not a univariate-model diagnostic.

Evidence:

- `docs/figure_a1_component_and_table_precision_contract_20260610.md`
  defines the manuscript Figure A1 contract as:
  - `raw_state_component`
  - `component = 6`
  - dry period: `2012-01-01` to `2016-12-31`
  - wet period: `2017-01-01` to `2019-12-31`
- `Evironmetrics---REVISED-DOC-Corrected-2/docs/figure_table_provenance.md`
  maps `fig:80_components` to
  `figures/manuscript/historical_component_80month.png`, sourced from the
  `2022-12-25 exAL-M-T1` selected-output support bundle.
- `Evironmetrics---REVISED-DOC-Corrected-2/scripts/render_authoritative_selected_model_support_figures.R`
  hard-codes:
  - `FIGURE_A1_COMPONENT <- 6L`
  - `FIGURE_A1_COMPONENT_CONTRACT <- "raw_state_component"`
- `Evironmetrics---REVISED-DOC-Corrected-2/scripts/refresh_authoritative_selected_model_support_figures.py`
  maps `fig:80_components` to
  `selected_model_component_80month.png` and states that plus/minus-trend
  variants are analysis-only diagnostics.

Therefore, if the target is Figure A1 or the selected dry/wet quantile-dynamic
figures, the optimal rebuild path is the selected `exdqlm_multivar_keep`
support-replay path, not `exdqlm_univar`.

### Figure A2 / `fig:synth2` and univariate reference synthesis

The univariate model is used by the reference synthesis figure family, not by
Figure A1.

Evidence:

- `Evironmetrics---REVISED-DOC-Corrected-2/docs/figure_table_provenance.md`
  maps `fig:synth2` to
  `figures/manuscript/reference_synthesis_univariate.png`, sourced from the
  current `2022-12-25 exdqlm_univar` output bundle.
- `Evironmetrics---REVISED-DOC-Corrected-2/scripts/refresh_current_model_output_support_figures.py`
  defines `UNIVAR_SPEC` as:
  - cutoff: `2022-12-25`
  - run id: `multimodel_20221225_v8_he2pubgdpc1r1_exdqlm_univar`
  - source figure:
    `exdqlm_univar_synth_cutoff_window_posterior_samples.png`
- `Evironmetrics---REVISED-DOC-Corrected-2/scripts/refresh_cutoff_synthesis_families.py`
  uses the univariate runtime root for cutoff-by-cutoff reference synthesis
  support.

Therefore, if the target is the reference univariate synthesis figure or a full
univariate table row refresh, an `exdqlm_univar` rerun is valid. It is not the
right mechanism for fixing selected multivariate component diagnostics.

## Recommended Decision Tree

### Target A: Fix or polish Figure A1 / dry-wet selected diagnostics

Recommended action:

1. Use the selected multivariate support replay workflow for the representative
   `2022-12-25 exAL-M-T1` selected run.
2. Prefer compact support export plus automatic cleanup.
3. Retain `.RData` only for a short, explicit debugging window if compact support
   is not sufficient to regenerate the desired figure.

Why this is optimal:

- It is the figure's actual lineage.
- It preserves consistency with the current authoritative synthesis figure.
- It avoids rerunning unrelated univariate models.
- It keeps the article repo lightweight by promoting compact support CSV/RDS and
  rendered figures, not full posterior objects.

Relevant tooling:

- `scripts/build_he2_selected_output_support_replay_config.py`
- `scripts/launch_he2_selected_output_support_replay.py`
- `scripts/run_unified_with_cleanup.sh`
- `Evironmetrics---REVISED-DOC-Corrected-2/scripts/refresh_authoritative_selected_model_support_figures.py`
- `Evironmetrics---REVISED-DOC-Corrected-2/scripts/render_authoritative_selected_model_support_figures.R`

Validation gate before any launch:

- Build a replay config with a new tag.
- Run the selected-support launcher with `--dry-run`.
- Confirm the resolved output root is isolated.
- Confirm the resulting config has:
  - `post.figures = TRUE`
  - `post.export_tables = TRUE`
  - `post.authoritative_selected_model_support.enabled = TRUE`
  - `post.multivar_component_diagnostics.enabled = TRUE`
  - cleanup wrapper set to `scripts/run_unified_with_cleanup.sh`.

Validation gate after completion:

- Confirm required compact support artifacts exist:
  - `authoritative_usgs_quantile_dynamics_summary.csv`
  - `authoritative_component_summary.csv`
  - `authoritative_selected_support_manifest.json`
- Refresh article assets.
- Validate:
  - `python3 scripts/validate_authoritative_output_lineage.py --article-root . --corrections-root /data/muscat_data/jaguir26/Corrections---Project-1`
  - `python3 scripts/validate_manuscript_figure_paths.py --article-root .`
  - `python3 -m unittest tests.test_article_a1_and_table_contracts -v`

### Target B: Refresh only the representative univariate reference synthesis

Recommended action:

1. Relaunch only the `2022-12-25 exdqlm_univar` case.
2. Retain `.RData` only until the needed figure edits are confirmed.
3. Promote the resulting figure through the existing article refresh scripts.
4. Clean `.RData` after the figure is frozen and hash-recorded.

Why this is optimal:

- It gives access to posterior objects for figure refinement.
- It avoids unnecessary all-cutoff reruns if the current goal is just the
  representative appendix/reference synthesis figure.
- It keeps disk risk controlled while HE3 continues.

Relevant tooling and config:

- `config/he2_bayesian_publication_relaunch_exdqlm_univar_all_cutoffs_sharedspec_20260516.template.yaml`
- `config/he2_relaunch_batches/exdqlm_univar_all_cutoffs_sharedspec_20260516.yaml`
- `scripts/build_he2_exdqlm_univar_shared_relaunch_validation_status.py`
- `Evironmetrics---REVISED-DOC-Corrected-2/scripts/refresh_current_model_output_support_figures.py`

The current univariate shared spec is:

- `df_t = 0.99999999`
- `df_s1 = 0.99999`
- `df_s2 = 0.99999`
- `df_s67 = 0.99999`
- `lambda = 0.97`
- `df_trans = 0.9999999`
- `df_covs = 0.9999999`

The univariate model has no multivariate discrepancy block and does not use the
forecast inverse-Wishart prior in the same way as the multivariate keep model.

Validation gate before any launch:

- Generate a one-cutoff config or matrix subset for `2022-12-25` only.
- Dry-run the launcher.
- Confirm the input bundle root remains:
  `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510`
- Confirm data start remains `1987-05-29`.
- Confirm output root is isolated from the previous `20260516` publication root
  unless this is an intentional replacement.

Validation gate after completion:

- Confirm all seven quantile fits completed.
- Confirm the post output includes:
  `exdqlm_univar_synth_cutoff_window_posterior_samples.png`.
- Refresh article support through
  `refresh_current_model_output_support_figures.py`.
- Validate figure paths and article lineage.

### Target C: Refresh all five univariate cutoffs for table/CRPS authority

Recommended action:

Run all five cutoffs only if the goal is a full univariate Table 1 / CRPS row
refresh, not merely a figure repair.

Why this is not the first move for the current figure question:

- The existing univariate runtime root has no retained `.RData` and is only
  about `246M`, so it is not currently a disk problem.
- The all-five retained rerun would create large posterior objects without
  helping Figure A1.
- If Table 1 does not need a univariate refresh right now, this is avoidable
  compute.

If this target becomes necessary:

1. Use cleanup by default.
2. Retain `.RData` only for failed or figure-critical cases.
3. Run serially or with conservative concurrency while HE3 is active.
4. Promote only compact metrics, figures, generated TeX, manifests, and hashes.

## Resource Plan

Current disk state is sufficient for a narrow retained run, but not a reason to
run broad retained jobs casually.

Recommended resource policy:

1. Do not run all-five-cutoff retained multivariate jobs while HE3 is active.
2. A one-cutoff selected-support replay is safe.
3. A one-cutoff retained univariate diagnostic run is safe if needed.
4. If HE3 is still active, use conservative concurrency and keep cleanup enabled
   by default.
5. Use disk thresholds before launch:
   - pause if free space drops below `180G`,
   - do not launch new heavy jobs below `220G`,
   - prefer cleanup before any new retained posterior-object run.

## Documentation and Wiring Requirements

Any future implementation should update or verify:

Workflow repo:

- `docs/authoritative_selected_outputs/he2_exal_m_t1_representative_20221225.yaml`
- this plan file, with an implementation log section
- any generated replay manifest under the runtime control directory
- validation reports under `reports/` as untracked evidence

Revised article repo:

- `Evironmetrics---REVISED-DOC-Corrected-2/config/runtime_bindings.json`
- `Evironmetrics---REVISED-DOC-Corrected-2/docs/figure_table_provenance.md`
- `Evironmetrics---REVISED-DOC-Corrected-2/artifacts/.../manifest.csv`
- `Evironmetrics---REVISED-DOC-Corrected-2/artifacts/.../SHA256SUMS.txt`
- manuscript figure copies under `figures/manuscript/`

Corrections repo:

- only update if the figure/table being refreshed is referenced in the
  corrections response or generated table/figure crosswalk.

## Implementation-Ready Sequence

When implementation is requested, the recommended sequence is:

1. Re-check live HE3 status and disk.
2. Confirm the user target:
   - selected multivariate component/quantile dynamics,
   - univariate reference synthesis,
   - full univariate CRPS/table refresh.
3. Build the narrowest isolated config for that target.
4. Run dry-run validation and inspect resolved roots.
5. Launch only after dry-run passes.
6. Monitor until post stage finishes.
7. Promote compact artifacts and figures.
8. Run cross-repo validators and article compile checks as applicable.
9. Clean retained `.RData` unless the user explicitly wants to keep them for the
   next figure-polish cycle.
10. Commit only source/docs/manifests/figure/table changes; keep large runtime
    outputs and validation reports untracked unless explicitly justified.

## Current Recommendation

The best immediate move is not to relaunch `exdqlm_univar` unless the next figure
to polish is the univariate reference synthesis.

For Figure A1 or the selected dry/wet quantile-dynamic figures, use the
`2022-12-25 exAL-M-T1` selected multivariate support replay. If compact support
is already sufficient, avoid retaining `.RData`. If not, run one isolated
selected-support replay with temporary `.RData` retention, extract the compact
support needed for plotting, then clean the posterior objects.

For the univariate reference synthesis, run only the `2022-12-25 exdqlm_univar`
case first. Expand to all five cutoffs only if the table/CRPS authority requires
it.

## Implementation Log

### 2026-06-26 univariate synthesis style refresh

The univariate `exdqlm_univar` synthesis figures are a reference-synthesis
family and should use the same publication-focus visual contract as the
multivariate `exdqlm_multivar_keep` synthesis figures.

This refresh does not require a model relaunch. The current publication
univariate outputs already exist for all five cutoffs under:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_univar_al_exal_publication_relaunch_20260603`

Implementation contract:

- Re-render the five `exdqlm_univar` cutoff-window synthesis figures from the
  existing post-stage caches.
- Use the shared `publication_focus_v2` renderer so the univariate figures share
  the multivariate synthesis conventions: fixed y limits, held-out USGS
  labeling, dashed cutoff marker at the first forecast date, flood-stage
  reference lines, compact bottom legend, and no forecast-window shading.
- Use the common model-center label `exDQLM - Synthesis`.
- Rewire the revised article's `univar_runtime_root` binding from the stale
  May 2026 root to the June 3 publication relaunch root before refreshing
  article-side figure copies.

Required validation after rendering:

- Confirm all five runtime output roots have refreshed PNG/PDF synthesis
  figures and updated `publication_figure_manifest.csv` files.
- Refresh the revised article's cutoff reference-synthesis family and the
  representative `reference_synthesis_univariate.png`.
- Validate article figure paths and cross-repo lineage before committing.

### 2026-06-26 selected-support refresh

The selected multivariate support path was implemented without launching a new
model run.

Reason:

- The revised article binding already pointed to a compact selected-support root
  with all required support files.
- The compact root contained no retained `.RData`, so a new retained replay was
  unnecessary for the Figure A1 / dry-wet selected-diagnostic refresh.

Source support used:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_selected_output_support_20260625_seasonal_only_current_components/runs/multimodel_20221225_v8_he2partial20260623_exdqlm_multivar_keep_authoritative_support_seasonal_only_20260625/post/outputs/multimodel_20221225_v8_he2partial20260623_exdqlm_multivar_keep_authoritative_support_seasonal_only_20260625`

Support evidence:

- `authoritative_usgs_quantile_dynamics_summary.csv` present.
- `authoritative_component_summary.csv` present.
- `authoritative_selected_support_manifest.json` present.
- `authoritative_selected_support_lineage.csv` present.
- selected-support retained `.RData`: `0` files.

Article-side implementation:

- `Evironmetrics---REVISED-DOC-Corrected-2/scripts/refresh_authoritative_selected_model_support_figures.py`
  refreshed the selected-model support artifacts.
- `Evironmetrics---REVISED-DOC-Corrected-2/scripts/render_authoritative_selected_model_support_figures.R`
  was hardened so render metadata no longer records temporary staging paths or
  per-render timestamps.
- `Evironmetrics---REVISED-DOC-Corrected-2/tests/test_article_a1_and_table_contracts.py`
  now checks the deterministic metadata contract.

Determinism check:

- The selected-support refresh was run twice.
- The full `git diff` SHA-256 before and after the second refresh was identical:
  `c49eec1e5f98679fd7774006bd43de0dc0a7914965b5a41fc3d97cc588ae1797`.

Validation:

- `python3 -m py_compile scripts/build_he2_selected_output_support_replay_config.py scripts/launch_he2_selected_output_support_replay.py scripts/validate_revision_cross_repo_wiring.py`
- `python3 -m py_compile scripts/validate_publication_freeze.py scripts/validate_revision_cross_repo_wiring.py`
- `python3 -m py_compile scripts/build_he2_exdqlm_univar_shared_relaunch_validation_status.py`
- revised article:
  `python3 -m unittest discover -s tests -v`
- revised article:
  `python3 scripts/validate_authoritative_output_lineage.py --article-root . --corrections-root /data/muscat_data/jaguir26/Corrections---Project-1`
- revised article:
  `python3 scripts/validate_manuscript_figure_paths.py --article-root .`
- workflow cross-repo:
  `python3 scripts/validate_revision_cross_repo_wiring.py --workflow-root /data/muscat_data/jaguir26/project1_ucsc_phd --article-root /data/muscat_data/jaguir26/project1_ucsc_phd/Evironmetrics---REVISED-DOC-Corrected-2 --corrections-root /data/muscat_data/jaguir26/Corrections---Project-1 --after-patch --strict --output-dir reports/revision_cross_repo_validation_20260626_selected_support_refresh_final`
- corrections response:
  `make`
- revised article compile:
  `pdflatex`, `bibtex`, `pdflatex`, `pdflatex` on `wileyNJD-APA.tex`.

Compile result:

- `output.pdf` built successfully with 28 pages.
- Only ordinary LaTeX warnings/overfull boxes were observed; no fatal compile
  errors occurred.
