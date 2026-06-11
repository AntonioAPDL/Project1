# Authoritative Output Lineage Sync Audit And Plan

Date: 2026-06-09

## Executive Decision

The revised article must not mix posterior-output figures from different selected-model runs. The authoritative
posterior-output source is the same selected-model bundle currently used for the synthesis figure:

- cutoff: `2022-12-25`
- model label: `exAL-M-T1`
- family: `exdqlm_multivar_keep`
- winning spec: `c05_eps030`
- run id: `multimodel_20221225_v8_he2grid_c05_eps030_exdqlm_multivar_keep`
- runtime root:
  `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_epsilon_discount_grid_20260524/runs/multimodel_20221225_v8_he2grid_c05_eps030_exdqlm_multivar_keep`
- article bundle:
  `Evironmetrics---REVISED-DOC-2/artifacts/representative_selected_model_2022_12_25/`

This means the q05, q50, and q95 quantile-dynamic figures and the associated component figures must resolve to the
same authoritative posterior source as `fig:synth1`, not to a separate historical-support replay.

Scope correction after the 2026-06-09 review:

- `artifacts/historical_support_from_current_models/` is no longer an acceptable source for the main representative
  posterior-output figures.
- The representative HE2 posterior-output figures and tables must all be sourced from the same selected-output authority
  as the synthesis illustration.
- Setup/input figures may still come from setup-support bundles, and comparison-model tables may still come from their
  own model-specific authoritative roots, but every object that is presented as the representative `exAL-M-T1`
  posterior output must pass a same-cutoff, same-run, same-source-class lineage check.
- Future model-output changes should be made by switching a single authority manifest and rerunning refresh/validation
  scripts, not by manually copying individual figures.

## Current Audit Finding

The new strict validator in the revised article repo reports `FAIL`:

- validator:
  `Evironmetrics---REVISED-DOC-2/scripts/validate_authoritative_output_lineage.py`
- report:
  `Evironmetrics---REVISED-DOC-2/reports/manuscript_asset_review/authoritative_output_lineage/AUTHORITATIVE_OUTPUT_LINEAGE_VALIDATION.md`

Current status:

| Object | Current source | Status |
|---|---|---|
| `fig:synth1` | `2022-12-25`, `multimodel_20221225_v8_he2grid_c05_eps030_exdqlm_multivar_keep` | pass |
| `tab:components_23_31` | `2022-12-25`, same selected-model bundle | pass |
| `tab:gamma_sigma_intervals1` | `2022-12-25`, same selected-model bundle | pass |
| `tab:gamma_sigma_intervals2` | `2022-12-25`, same selected-model bundle | pass |
| `fig:dry_quantile` | `2022-05-11`, `multimodel_20220511_v8_he2grid_c02_eps060_exdqlm_multivar_keep` | fail |
| `fig:rainy_quantile` | `2022-05-11`, `multimodel_20220511_v8_he2grid_c02_eps060_exdqlm_multivar_keep` | fail |
| `fig:80_components` | `2022-05-11`, `multimodel_20220511_v8_he2grid_c02_eps060_exdqlm_multivar_keep` | fail |

The corrections repo also still contains prose that says the historical regime and long-cycle figures are descriptive
historical summaries. That prose is now stale under the new synchronization rule.

## Source-Of-Truth Architecture

The long-term wiring should use two manifests with different responsibilities:

1. Workflow-side selected-output authority manifest
   - owned by this repo;
   - records the selected cutoff, run id, runtime root, input bundle hash/path, model family, likelihood mode, quantiles,
     discount factors, epsilon, `c_factor`, scale contract, seed contract, post artifact hashes, and cleanup policy;
   - is written or refreshed when we promote a new selected model.
2. Article-side asset manifest
   - owned by the revised article repo;
   - records manuscript labels and copied artifact paths;
   - must derive representative posterior-output source paths from the workflow authority manifest or from an imported
     bundle metadata file copied from it.

The article-side manifest is not allowed to become an independent source of truth for posterior-output lineage. It is a
rendering/promotion manifest only. The workflow authority manifest decides what the selected output is; article refresh
scripts copy/render from that selected output; validators confirm the article and corrections repos did not drift.

Recommended workflow authority file:

`docs/authoritative_selected_outputs/he2_exal_m_t1_representative_20221225.yaml`

Implemented initial authority file:

`docs/authoritative_selected_outputs/he2_exal_m_t1_representative_20221225.yaml`

Minimum keys:

| Key | Required value for current authority |
|---|---|
| `article_object_family` | `he2_representative_exal_m_t1` |
| `cutoff` | `2022-12-25` |
| `model_label` | `exAL-M-T1` |
| `model_family` | `exdqlm_multivar_keep` |
| `spec_id` | `c05_eps030` |
| `run_id` | `multimodel_20221225_v8_he2grid_c05_eps030_exdqlm_multivar_keep` |
| `runtime_run_root` | current synthesis run root |
| `scale_contract` | `log1p_cms` |
| `quantiles` | `05,20,35,50,65,80,95` |
| `representative_quantiles_for_article` | `05,50,95` |
| `cleanup_policy` | `.RData` removed after post only after durable compact exports validate |

The existing five-cutoff winner YAML remains the CRPS/winner-selection source. The selected-output authority file is the
article-facing promotion lock for the representative figures/tables.

2026-06-10 Figure A1/table display addendum:

`docs/figure_a1_component_and_table_precision_contract_20260610.md`

This addendum locks the Figure A1 internal rendering contract to the samplewise
`component_6_plus_trend_component_1_samplewise` construction, keeps the
article-facing wording as the 80-month seasonal component, restores the dry/wet
period overlays, and standardizes publication-facing generated TeX tables to
fixed five-decimal display.

Implemented workflow-side validation gate:

`scripts/validate_he2_selected_output_authority.py`

This gate checks the selected-output authority file against:

- `docs/exdqlm_multivar_keep_authoritative_specs_20260601.yaml`;
- the selected runtime post outputs;
- the revised-article representative bundle metadata.

Current result:

`python3 scripts/validate_he2_selected_output_authority.py` exits `0`.

Focused test:

`python3 -m unittest tests.python.test_he2_selected_output_authority -v`

Current result: 2 tests pass, including a deliberate run-id drift rejection.

Implemented post-stage durable export switch:

- config key: `post.authoritative_selected_model_support.enabled`;
- environment flag: `UNIFIED_POST_AUTHORITATIVE_SELECTED_SUPPORT`;
- exporter location: `R/environmetrics/40_figures_multivar_only.R`;
- required post artifacts when enabled:
  - `authoritative_usgs_quantile_dynamics_summary.csv`;
  - `authoritative_usgs_quantile_dynamics_summary.rds`;
  - `authoritative_component_summary.csv`;
  - `authoritative_component_summary.rds`;
  - `authoritative_selected_support_lineage.csv`;
  - `authoritative_selected_support_manifest.json`.

The post artifact contract now fails before cleanup if these files are requested but missing. The focused contract test is:

`python3 -m unittest tests.python.test_authoritative_selected_support_contract -v`

Implemented article-side import/render path:

- `Evironmetrics---REVISED-DOC-2/scripts/refresh_authoritative_selected_model_support_figures.py`;
- `Evironmetrics---REVISED-DOC-2/scripts/render_authoritative_selected_model_support_figures.R`.

These scripts import compact workflow support artifacts into:

`Evironmetrics---REVISED-DOC-2/artifacts/representative_selected_model_2022_12_25/authoritative_support/`

and then update only `fig:dry_quantile`, `fig:rainy_quantile`, and `fig:80_components` to point at the representative
selected-model bundle.

Implemented isolated replay config builder:

`scripts/build_he2_selected_output_support_replay_config.py`

Generated replay config:

`config/unified_runs_selected_output_support_20260609/multimodel_20221225_v8_he2grid_c05_eps030_exdqlm_multivar_keep_authoritative_support_20260609.yaml`

Corrected clean retry replay config:

`config/unified_runs_selected_output_support_20260609/multimodel_20221225_v8_he2grid_c05_eps030_exdqlm_multivar_keep_authoritative_support_r2_20260609.yaml`

Final clean launch replay config after the r2 dry-run envelope was consumed:

`config/unified_runs_selected_output_support_20260609/multimodel_20221225_v8_he2grid_c05_eps030_exdqlm_multivar_keep_authoritative_support_r3_20260609.yaml`

Post-failure correction after the r3 replay:

- r3 was launched from clean commit `3730667` and all seven quantile fits reached the intended 100-iteration contract;
- r3 post generated ordinary synthesis/table artifacts, then failed inside
  `R/environmetrics/40_figures_multivar_only.R:authoritative_support_project_theta()` with
  `t(Ft) %*% Sigma : non-conformable arguments`;
- the root cause was a covariance-slice shape bug: `theta_obj$sC[, , t, drop = FALSE]` can remain a 3D `p x p x 1`
  object and is not a valid matrix operand for the `F_t' C_t F_t` projection;
- the implementation now materializes each smoother covariance slice as an explicit `p_use x p_use` matrix before
  projection;
- because r3 used the default cleanup-on-failure behavior inherited from `CLEANUP_RDATA_AFTER_POST=1`, the failed post
  removed all seven large `.RData` files and cannot be replayed without refitting;
- this exposed an operational contract bug for authoritative support replays: success should clean `.RData`, but failure
  must retain `.RData` for post-stage debugging and retry;
- the launch/builder contract now sets `CLEANUP_RDATA_ON_FAILURE=0` for selected-output support replays while keeping
  successful post cleanup enabled.

Replacement clean replay config:

`config/unified_runs_selected_output_support_20260609/multimodel_20221225_v8_he2grid_c05_eps030_exdqlm_multivar_keep_authoritative_support_r4_20260609.yaml`

Generated runtime manifest:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_selected_output_support_20260609/control/selected_output_support_replay_manifest.json`

This replay uses the same selected-output authority and input bundle but writes to an isolated runtime root. It enables
the compact support export and keeps production cleanup behavior on success, so large `.RData` files are removed only
after the post artifact contract passes. If post fails, `.RData` files are intentionally retained for diagnosis.

Execution correction from the 2026-06-09 implementation pass:

- the first `authoritative_support_20260609` attempt only created the run envelope and did not enter the unified stage
  loop; its manifest records an older dirty code state and must not be used as article evidence;
- the `authoritative_support_r2_20260609` retry was used for dry-run validation and is not the final launch target;
- the clean `authoritative_support_r3_20260609` retry proved the fit was healthy but exposed the post projection bug and
  cleanup-on-failure gap;
- the clean `authoritative_support_r4_20260609` retry is the current support-replay target;
- launch/status entrypoints:
  - `scripts/launch_he2_selected_output_support_replay.py`;
  - `scripts/check_he2_selected_output_support_replay.py`;
- revised-article binding:
  `Evironmetrics---REVISED-DOC-2/config/runtime_bindings.json:exal_m_t1.selected_support_output_root`.

## Why This Cannot Be Fixed By Renaming Alone

The current authoritative `2022-12-25` post output contains the synthesis artifacts and median-only component diagnostics,
but not the retained q05/q50/q95 posterior state objects required to regenerate the three-quantile dynamic/component
figures from the exact same posterior source. The heavy `.RData` files were cleaned after post, as intended by the
production cleanup policy.

Observed available `2022-12-25` post outputs include:

- synthesis figures and sample/quantile exports,
- CRPS summaries,
- posterior table exports,
- q50 trace/component diagnostics,
- compact synthesis caches.

Observed missing durable artifacts:

- q05/q50/q95 retained state-summary cache for article dynamic/component figures,
- q05/q95 component diagnostic outputs,
- seven quantile `.RData` files under the authoritative run root.

Therefore, copying the current 2022-05-11 historical support figures into a different path would be wrong. Generating
new 2022-12-25 dynamics from a fresh sibling replay while leaving the old 2022-12-25 synthesis in place would also be
wrong unless the replay is proven to reproduce the exact same posterior objects. The robust fix is to produce one
authoritative selected-model support bundle and promote all representative posterior figures and tables from that bundle
together.

## Implementation Plan

### Phase 1: Make The Gate Permanent

1. Keep `Evironmetrics---REVISED-DOC-2/scripts/validate_authoritative_output_lineage.py` as the strict article gate.
2. After the rewire is complete, add it to the article full-refresh pipeline after:
   - `promote_generated_figures_to_disc.py`,
   - `sync_legacy_uppercase_figures.py`,
   - `build_article_asset_review_report.py`.
3. The gate must fail if any representative posterior-output figure or table is sourced from a cutoff/run different from
   `fig:synth1`.
4. The gate must also scan the corrections repo for stale prose that contradicts the current selected-output lineage.

Acceptance:

- the validator exits `0`,
- all figure/table rows in the generated report are `PASS`,
- the corrections prose gate is `PASS`.

Additional gate behavior:

- fail if any representative posterior-output label points at `historical_support_from_current_models`;
- fail if a representative posterior-output object is missing a source hash;
- fail if copied article artifacts differ from their bundle source hashes;
- fail if corrections hard-coded table values disagree with the generated revised-article table sources;
- fail if stale phrases such as "historical summaries" are used for the representative posterior-output figures.

### Phase 2: Add Durable Compact Posterior-Support Exports In The Workflow Repo

Add a compact support export to the post stage before `.RData` cleanup. This export should be small enough to retain
permanently and rich enough to regenerate article-side q05/q50/q95 dynamic and component figures without keeping large
fit-state files.

Required durable artifacts:

1. `authoritative_usgs_quantile_dynamics_summary.rds`
   - q05, q50, q95 posterior predictive/location summaries,
   - 2.5%, 50%, 97.5% bands,
   - historical window and forecast-window dates,
   - source run id, cutoff, scale contract, quantile levels.
2. `authoritative_component_summary.rds`
   - q05, q50, q95 component summaries,
   - exact summary probability ordering,
   - component labels and state-coordinate map,
   - trend-shift or decomposition contract,
   - source run id, cutoff, scale contract.
3. CSV mirrors for review:
   - `authoritative_usgs_quantile_dynamics_summary.csv`,
   - `authoritative_component_summary.csv`,
   - `authoritative_output_lineage_manifest.csv`.
4. Figure outputs generated from the compact summaries:
   - q05/q50/q95 selected-model dynamics around the chosen windows,
   - q05/q50/q95 selected-model component figures,
   - optional q05/q50/q95 around-cutoff deterministic location figure.

The compact export should be the only durable dependency needed to redraw the article-side q05/q50/q95 dynamics and
components. It must not require retained `.RData` after post.

Contract changes:

- extend `R/unified/post_artifact_contract.R` so the authoritative support export is required when
  `post.authoritative_selected_model_support.enabled = true`;
- update `R/unified/stages/stage_post.R` to set the required environment/config flags;
- preserve `.RData` cleanup only after the compact support export and post artifact contract pass.

Tests:

- unit fixture: compact support export exists, has q05/q50/q95, and source run id equals the run id in `resolved_config.yaml`;
- unit fixture: component summary bands use the direct 2.5/50/97.5 columns and do not re-quantile already summarized values;
- cleanup fixture: `.RData` is removed after post only if the compact support export exists and validates.

Runtime validation:

- compare compact-export q50 summaries against the existing q50 post diagnostics for the same run;
- compare compact-export synthesis/dynamic dates against the synthesis cutoff-window CSV;
- verify all exported article windows contain observed USGS truth where it exists and explicit `NA` where truth is not
  available;
- verify no q05/q50/q95 representative article figure can be rendered from a different cutoff unless the authority
  manifest itself changes.

### Phase 3: Recover Or Recreate A Single Authoritative Bundle

First try to recover the original selected-run `.RData` files or equivalent compact state summaries for:

`multimodel_20221225_v8_he2grid_c05_eps030_exdqlm_multivar_keep`

If they are not recoverable, run an isolated authoritative support replay with:

- same cutoff: `2022-12-25`,
- same input bundle contract,
- same winning spec: `c05_eps030`,
- same active quantiles: `05|20|35|50|65|80|95`,
- same max iter: `100`,
- same scale contract: `log1p_cms`,
- same seed contract if available,
- cleanup enabled only after compact support export passes.

Promotion rule:

- If the replay reproduces the old synthesis outputs exactly or within a documented deterministic tolerance, it can be used
  to generate only the missing dynamics/components while preserving `fig:synth1`.
- If it does not reproduce the old synthesis exactly, promote the replay as a new single authoritative selected-model
  bundle and regenerate `fig:synth1`, q05/q50/q95 dynamics, component figures, posterior tables, CRPS summaries, and
  article manifests together from that replay. Do not mix old synthesis with new dynamics.

### Phase 4: Rewire The Revised Article Repo

Replace the old historical-support figure source path with an authoritative selected-model support source.

Recommended structure:

`Evironmetrics---REVISED-DOC-2/artifacts/representative_selected_model_2022_12_25/authoritative_dynamics/`

Required article updates:

1. `MANUSCRIPT_ASSET_MANIFEST.json`
   - change `fig:dry_quantile`, `fig:rainy_quantile`, and `fig:80_components` to `source_class =
     current_selected_model_representative`;
   - source paths must point into the representative selected-model bundle.
2. Replace or retire:
   - `artifacts/historical_support_from_current_models/` as a source for representative posterior-output figures.
3. Update scripts:
   - replace the hard-coded `20220511` default in `refresh_current_model_output_support_figures.py`,
   - or replace the script with `refresh_authoritative_selected_model_support_figures.py`.
4. Update article prose:
   - remove language saying these are separate historical-support figures,
   - describe them as selected-model q05/q50/q95 posterior dynamics/components from the same `2022-12-25` selected model
     used in the synthesis illustration.
5. Rebuild:
   - manuscript figures,
   - uppercase mirror,
   - asset review reports,
   - generated asset inventory,
   - article PDF.

Article manifest target state:

| Label | Required source family | Required cutoff/run |
|---|---|---|
| `fig:synth1` | representative selected-model bundle | `2022-12-25` / `c05_eps030` selected run |
| `fig:dry_quantile` | representative selected-model bundle | same as `fig:synth1` |
| `fig:rainy_quantile` | representative selected-model bundle | same as `fig:synth1` |
| `fig:80_components` | representative selected-model bundle | same as `fig:synth1` |
| `tab:components_23_31` | representative selected-model bundle | same as `fig:synth1` |
| `tab:gamma_sigma_intervals1` | representative selected-model bundle | same as `fig:synth1` |
| `tab:gamma_sigma_intervals2` | representative selected-model bundle | same as `fig:synth1` |

Any additional representative posterior-output figure/table added later must be included in the validator's default label
set or in a checked manifest field such as `requires_authoritative_selected_model_lineage = true`.

Article acceptance gates:

- `python3 scripts/validate_authoritative_output_lineage.py --article-root . --corrections-root /data/muscat_data/jaguir26/Corrections---Project-1`
- `python3 scripts/validate_manuscript_figure_paths.py --article-root .`
- `pdflatex/bibtex/pdflatex/pdflatex` succeeds.

### Phase 5: Rewire The Corrections Repo

Patch the corrections letter so it no longer says the q05/q50/q95 dynamic and long-cycle figures are a separate
historical-support family. The corrections text should say that the selected-model posterior-output figures and tables
are sourced from the same authoritative selected-model output bundle as the synthesis figure.

Corrections acceptance gates:

- generated HE2/HE3/HE4 tables remain byte-for-byte synced with revised article sources unless deliberately refreshed;
- stale historical-support prose scan passes;
- corrections PDF compiles.

### Phase 6: Future-Proof The Authority Switch

For future model-output changes, the source of truth should be a single selected-model authority manifest, not hand-edited
figure paths.

Authority manifest requirements:

- selected cutoff,
- run id,
- runtime root,
- input-bundle id/hash,
- scale contract,
- quantiles,
- spec id,
- random seed,
- post artifact hashes,
- figure/table artifact hashes.

Refresh scripts should read that manifest and derive all representative figure/table source paths from it. If the selected
model changes later, updating the authority manifest plus rerunning the refresh should be enough. The strict lineage gate
then confirms every representative posterior-output object follows the new authority.

Future authority-switch procedure:

1. Promote the new workflow run into a compact selected-output support bundle.
2. Update only the workflow selected-output authority manifest.
3. Run the workflow authority validator: specs, input bundle, scale, quantiles, post hashes, cleanup state.
4. Import/promote the selected-output bundle into the revised article repo.
5. Regenerate all representative posterior-output figures and tables from that bundle.
6. Run the article lineage validator and manuscript path/hash validators.
7. Sync generated tables/prose references into the corrections repo.
8. Compile the revised article and corrections article.
9. Commit all repos with the authority switch documented in the commit messages.

If any step fails, the authority switch is incomplete and the previous published bundle remains the only valid authority.

## Cross-Repo Validation Matrix

| Layer | Repository | Gate | Failure caught |
|---|---|---|---|
| Winner/source lock | workflow | `scripts/validate_he2_selected_output_authority.py` | wrong cutoff, wrong run id, stale spec, stale selected bundle metadata |
| Post durability | workflow | post artifact contract | compact support missing before `.RData` cleanup |
| Article assets | revised article | source hash/path validator | copied figure/table differs from selected bundle |
| Article lineage | revised article | `scripts/validate_authoritative_output_lineage.py` | mixed 2022-05-11 and 2022-12-25 posterior outputs |
| Article prose | revised article | stale-phrase/prose claim scan | text still says historical support when source is selected output |
| Corrections tables | corrections | generated-table parity check | hard-coded values drift from revised article tables |
| Corrections prose | corrections | stale-phrase/prose claim scan | correction letter contradicts current lineage |
| Build reproducibility | revised + corrections | LaTeX compile | broken references, missing figures, stale labels |

Current cross-repo gate status:

| Gate | Status | Interpretation |
|---|---|---|
| workflow selected-output authority | pass | the synthesis authority is coherent and matches the CRPS-selected winner |
| revised-article authoritative lineage | fail | expected until q05/q50/q95 dynamics/components are regenerated from the selected-output authority |
| corrections stale historical-support prose scan | fail | expected until corrections prose is patched after the selected-output article rewire |

## Immediate Next Actions

1. Keep the strict validator and current failing report as evidence of the bug.
2. Run the isolated `2022-12-25 c05_eps030` authoritative support replay from the generated config.
3. Import the replay support artifacts into the revised article repo with
   `scripts/refresh_authoritative_selected_model_support_figures.py`.
4. Promote manuscript figures and rebuild article asset review reports.
5. Patch corrections prose.
6. Run cross-repo validation and compile both documents.

The current expected validation state is `FAIL`. That is correct until the representative q05/q50/q95 dynamic/component
figures are regenerated from the same selected-output authority as the synthesis figure and the corrections prose is
patched.

## Non-Negotiable Guardrails

- Do not relabel 2022-05-11 historical-support figures as 2022-12-25 selected-model figures.
- Do not mix synthesis from one run with components/dynamics from a different run.
- Do not keep large `.RData` files as the long-term solution.
- Do not update the corrections article without rerunning the lineage validator.
- Do not call the final article synced until the validator exits `0`.
