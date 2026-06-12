# HE2 Full CRPS Table Relaunch Plan

Date: 2026-05-16
Last updated: 2026-05-16
Status: Revised planning contract for the remaining full-table relaunch

## Purpose

This document defines the stage-by-stage plan to finish the **full HE2 CRPS-table relaunch** under the corrected shared-input and revised-article workflow.

This plan is intentionally broader than the completed `exdqlm_multivar_keep` relaunch. Its purpose is to take the lessons, tooling, and proof-quality recovery work from that family and apply them cleanly to the rest of the CRPS table.

The plan is designed to be:

- well documented
- reviewer-shareable
- flexible in rollout order
- strict about provenance and reproducibility
- wired to the revised article workflow
- explicit about what is frozen from publication state versus what is being corrected in the new relaunch lineage

## Executive Summary

### What is already complete

The `he2pubgdpc1r1` relaunch has now completed successfully for the full `exdqlm_multivar_keep` family across all 5 HE2 cutoffs.

That completed family is now our **reference implementation** for:

- canonical shared-input bundle wiring
- full-history `1987-05-29 -> cutoff` retrospective contract
- `log1p_cms` end-to-end transform contract
- deterministic-climate handoff usage
- blended PPT and soil forecast covariates
- canonical GDPC-backed climate covariate wiring
- queue/recovery/reset operations
- post/validate/report completion under the revised workflow

### What is not complete yet

The full CRPS table is **not yet fully refreshed** under this corrected lineage.

The compare tables currently contain all expected model IDs, but only the `exdqlm_multivar_keep` rows are sourced from the new relaunch lineage. The remaining model rows are still being carried from older `baseline_tt` publication-state runs.

So the next task is **not** to redesign the workflow again. The next task is to use the now-proven relaunch stack to refresh the rest of the CRPS-table rows under the same corrected shared-input contract.

## Core Goal

Produce a corrected, reproducible, article-wired CRPS-table relaunch in which:

1. every rerunnable Bayesian model family uses the same scientific/model specification that produced the current publication row,
2. every rerun uses the corrected shared-input bundle for its cutoff,
3. all models within the same cutoff use the exact same shared-input lineage,
4. all retros and USGS support honor the `1987-05-29 -> cutoff` full-history contract,
5. all runs use the updated deterministic-climate blended covariates for PPT and soil moisture,
6. all runs use the updated canonical GDPC-backed climate factor input,
7. all refreshed outputs wire cleanly into the revised article provenance workflow,
8. and the final compare bundles no longer mix corrected relaunch rows with stale baseline rows for rerunnable models.

## Current Audit Read

### 1. The completed relaunch family is only `exdqlm_multivar_keep`

The completed all-cutoff relaunch template was explicitly scoped to:

- `families: [exdqlm_multivar_keep]`

Source:
- `config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_all_cutoffs_20260512.template.yaml`

So the recent work successfully closed one family, not the entire CRPS table.

### 2. The compare bundles still mix corrected and publication-state rows

Current compare bundles include the full CRPS-table shape per cutoff, but they are mixed-source:

- `featurecov_relaunch` rows now exist for `exdqlm_multivar_keep`
- the other model rows still come from `baseline_tt` source runs

That means the compare bundles are structurally useful, but they are **not yet a fully corrected same-lineage table**.

### 3. The publication manifest is still the right source-of-truth for model specification

The current publication manifest contains 45 Bayesian rows:

- 9 model families
- 5 cutoffs each

Families:

- `ndlm_univar_keep`
- `ndlm_main_drop`
- `ndlm_main_keep`
- `dqlm_univar_al`
- `dqlm_multivar_al_drop`
- `dqlm_multivar_al_keep`
- `exdqlm_univar`
- `exdqlm_multivar_drop`
- `exdqlm_multivar_keep`

The manifest also records, for all 45 rows:

- `within_cutoff_shared_inputs_aligned = True`
- `deterministic_climate_enabled = True`
- `fit_covariate_names = PPT|SOIL|PCA`
- `score_scale = log_cms_plus1`

That makes the manifest the correct publication-state source-of-truth for the remaining-family relaunch plan.

### 4. The current authoritative publication rows are already aligned within cutoff, but alignment is not the same as correction

A fresh workflow-side sanity audit now confirms that the current authoritative 45 Bayesian publication rows already agree, within each cutoff, on:

- parameters
- retros
- NWS forecast
- GloFAS forecast
- `PPT`
- `SOIL`
- `PCA`
- `covariate_features.csv`
- deterministic-climate future precip
- deterministic-climate future soil

Current audit result:

- `50 / 50` artifact-alignment checks passed across the 5 cutoffs

However, that is **not** enough to declare the current publication rows ready for corrected reuse.

Why:

- `20210123`
- `20211112`
- `20221225`

still carry short effective retrospective support windows in the authoritative publication lineage even though the requested `data_start` is `1987-05-29`.

So the correct interpretation is:

- current publication rows are already **internally aligned within cutoff**
- but three cutoffs are still **not yet on the corrected full-history relaunch contract**

### 5. The remaining launch risk is using the wrong launcher family

There are still older family-specific matrix builders in the repo that materialize runs by copying inputs from older source snapshots.

Those builders remain useful as audit history and for reading publication-era selection logic, but they should **not** be treated as the corrected launch authority for the remaining CRPS-table relaunch:

- `scripts/build_multimodel_v8_featurecov_cf1_eps_matrix_configs.py`
- `scripts/build_multimodel_v8_all9_feature_matrix_configs.py`
- `scripts/build_multimodel_v8_ndlm_featurecov_rerun_matrix_configs.py`

The corrected relaunch path should instead be driven by:

- the publication manifest
- `scripts/build_he2_bayesian_publication_relaunch_configs.py`
- `scripts/validate_he2_bayesian_publication_relaunch_prelaunch.py`

This matters because the remaining-family relaunch must use:

- the most recent publication-winning row specs
- the corrected shared-input bundle lineage
- explicit row-level provenance and frozen spec tracking

and not an older launcher that happens to reproduce a similar family shape with the wrong bundle roots.

### 6. The main-model bundle/figure lineage must be qualified before broader relaunch

The revised-article workflow already has a canonical five-cutoff setup/support bundle path for the main model lineage:

- `repro/run/EXAL_M_T1_SETUP_SUPPORT_BY_CUTOFF_V2_WORKFLOW.md`
- `repro/run/EXAL_M_T1_SETUP_SUPPORT_V2_SOURCE_MANIFEST.md`

That corrected workflow already locks:

- full-history `usgs.png` / raw covariate figures where applicable
- cutoff-specific retrospective support reporting
- bundle-native `forecats.png`
- `log1p_cms` display scale

It also already preserves the forecast-context figures for all five cutoffs in the revised article repo.

What remains open is the cutoff-wide curation/promotion of the synthesis families tied to the main model:

- Figure 7 multivariate synthesis family
- Figure A2 historical-only synthesis family

So the figure/input-bundle audit for the main model should be treated as an explicit early stage of the full-table relaunch plan, not as a trailing cosmetic task.

## Locked Contracts

These rules should be treated as frozen unless we intentionally revise them in a new planning pass.

### A. Shared-input contract

For all corrected relaunch rows:

- `data_start = 1987-05-29`
- `retros.csv` must begin at `1987-05-29`
- `retros.csv` must end at the row cutoff date
- shared-input artifacts must be identical across all rerun families within a cutoff

The relaunch validator already knows how to enforce within-cutoff identity for:

- `parameters_path`
- `retros_path`
- `nws_forecast_path`
- `glofas_forecast_path`
- `bundle_meta`
- `handoff_root`
- covariate-feature settings
- individual covariate file paths

### B. Transform contract

The active relaunch path stays on the `log1p_cms` contract.

Required:

- retrospective observations: `log1p_cms`
- forecast ensemble fit/post usage: `log1p_cms`
- fit internals: `log1p_cms`
- post internals: `log1p_cms`
- support-flow figures displayed on `log1p_cms`

`log_log1p_cms` is not allowed in the active corrected relaunch workflow.

### C. Covariate contract

Every corrected rerun must consume the same three publication covariate slots:

- `PPT`
- `SOIL`
- `PCA`

Where:

- `PPT` is fed by the corrected blended deterministic precipitation forecast path
- `SOIL` is fed by the corrected blended deterministic soil-moisture forecast path
- `PCA` is the workflow-facing compatibility alias for the canonical GDPC-backed climate factor

### D. GDPC contract

The climate-factor contract is now the canonical GDPC lineage.

Locked design:

- method: `gdpc()`
- fixed lag: `k = 2`
- retained component: `GDPC1`
- master fitting window: `1987-05-29 -> 2023-01-22`
- all cutoffs reuse the same master factor by date slicing
- workflow-facing compatibility alias remains the `PCA` slot

### E. Article-side contract

The revised article repo remains the canonical freeze point for generated assets and review bundles.

Canonical article refresh entrypoint:

- `Evironmetrics---REVISED-DOC-Corrected/scripts/refresh_all_generated_assets.py`

Canonical setup/support path:

- `repro/run/EXAL_M_T1_SETUP_SUPPORT_BY_CUTOFF_V2_WORKFLOW.md`

Canonical article workflow contract:

- `repro/run/CANONICAL_REVISED_ARTICLE_WORKFLOW.md`

### F. Launcher contract

The corrected remaining-family relaunch must use one approved launch path:

- publication rows selected from the current publication manifest
- source specs loaded from each row’s current `resolved_config.yaml`
- corrected configs built by `scripts/build_he2_bayesian_publication_relaunch_configs.py`
- prelaunch validation enforced by `scripts/validate_he2_bayesian_publication_relaunch_prelaunch.py`

The older family-specific matrix builders may still be used as audit references, but they are not the corrected launch authority for the remaining full-table relaunch.

### G. Main-model figure contract

Before the remaining-family relaunch becomes operationally authoritative, the main-model figure lineage must be re-qualified under the corrected bundle contract.

That stage must include:

- the canonical five-cutoff setup/support bundle family
- the five-cutoff forecast-context `forecats.png` family
- the cutoff-wide synthesis-family plan for Figure 7 and Figure A2

The purpose is to keep the revised article and the corrected workflow lineage synchronized from the start instead of trying to bolt figure provenance on at the end.

## Planning Principle

We must preserve two distinct but linked states:

1. **publication-state freeze**
2. **corrected relaunch lineage**

We do not overwrite the frozen publication-state evidence in place.
We build the corrected lineage beside it, validate it, and only then refresh article-side generated bundles intentionally.

## Scope For The Remaining Relaunch

### In scope now

The remaining Bayesian model families:

- `ndlm_univar_keep`
- `ndlm_main_drop`
- `ndlm_main_keep`
- `dqlm_univar_al`
- `dqlm_multivar_al_drop`
- `dqlm_multivar_al_keep`
- `exdqlm_univar`
- `exdqlm_multivar_drop`

Already completed and frozen as reference:

- `exdqlm_multivar_keep`

### In scope after Bayesian relaunch waves

Direct CRPS-table baseline rows should also be refreshed under the corrected shared-input contract as a final table-integrity step:

- `nws_nwm_ensemble`
- `glofas_ensemble`

### Out of scope for this stage

- scientific redesign of model specs beyond documented relaunch fixes
- cosmetic figure redesign
- manuscript wording changes before corrected evidence is fully assembled
- replacing the `PCA` slot name everywhere with `GDPC`

## Model-Spec Policy

This is one of the most important decisions in the plan.

### Default rule for remaining families

For the remaining 8 Bayesian families, use the **same model specifications that produced the current publication rows**.

That means:

- start from each row’s current `resolved_config.yaml`
- preserve the family-specific statistical specification
- preserve the publication-row likelihood choice
- preserve the publication-row transfer-mode choice
- preserve family-specific prior/state/seasonality behavior
- update only the shared-input lineage and relaunch scaffolding needed to run on the corrected bundles

### Preserve the winning epsilon / discount / postfix choice per row

This rule is critical.

The remaining-family relaunch is **not** the stage where we rerun model-selection sweeps.

Instead, every remaining row should inherit the current publication-winning specification token from the publication manifest lineage:

- current selected epsilon winner where the row came from the feature-covariate epsilon sweep lineage
- current selected postfix NDLM lineage where the row came from the NDLM rerun-postfix lineage
- current univariate rerun lineage where the row came from the univariate relaunch lineage
- current exact-input override where a documented publication replacement already exists

Operational meaning:

- preserve the winning row-level scientific spec
- correct the shared-input lineage beneath it
- do not silently downgrade to an older builder’s default epsilon / discount setting

### Controlled exception path

If a future row needs a relaunch-only corrective override, that override must be:

- row-scoped
- documented in the batch request
- recorded in the generated `frozen_spec_manifest.csv`
- justified as a corrective relaunch action rather than a silent spec drift

### Exception: `exdqlm_multivar_keep`

Do **not** revert this family back to the old publication-state configs.

Use the newly completed `he2pubgdpc1r1` relaunch outputs as the corrected authoritative lineage for this family.

That family has already gone through the necessary q50/q65 recovery and should now be treated as the corrected reference implementation.

## Stage-By-Stage Plan

### Stage 0. Freeze the current reference state

Purpose:
- make the successful `exdqlm_multivar_keep` relaunch the reusable template for the remaining work
- avoid accidental drift while expanding to the rest of the table

Actions:
1. treat `multimodel_v8_he2_exdqlm_multivar_keep_all_cutoffs_20260512` as the reference corrected-family root
2. freeze the completed proof and recovery notes as evidence
3. keep the publication manifest snapshot unchanged until the broader corrected reruns are complete

Deliverables:
- stable reference family root
- stable reference runbooks and recovery notes
- stable reviewer-facing evidence path for the completed family

### Stage 1. Qualify the launcher, spec, input-bundle, and main-model figure contract

Purpose:
- prove that the remaining relaunch will launch the **right rows with the right specs**
- prove that the corrected workflow is wired to the right bundle lineage and revised-article figure lineage before we widen scope

Actions:
1. refresh the authoritative HE2 Bayesian input sanity audit
2. refresh the historical-support audit snapshot so we explicitly separate:
   - already aligned publication rows
   - cutoffs that still need corrected full-history reruns
3. freeze the approved launch path:
   - publication manifest
   - `build_he2_bayesian_publication_relaunch_configs.py`
   - `validate_he2_bayesian_publication_relaunch_prelaunch.py`
4. explicitly quarantine the older family-specific builders from corrected production use
5. build a launcher qualification note that maps every remaining family to:
   - current publication campaign lineage
   - current publication run ID
   - current resolved-config path
   - current selected spec token
6. refresh and validate the main-model five-cutoff setup/support bundle family
7. refresh and validate the five-cutoff forecast-context `forecats.png` family in the revised article repo
8. define the cutoff-wide synthesis-family promotion plan for:
   - Figure 7 multivariate synthesis
   - Figure A2 historical-only synthesis

Stage 1 implementation files:
- contract builder: `scripts/build_he2_full_crps_stage1_contract.py`
- Stage 1 output root: `reports/he2_full_crps_stage1_contract_20260516/`
- revised-article refresh entrypoint: `Evironmetrics---REVISED-DOC-Corrected/scripts/refresh_all_generated_assets.py`
- five-cutoff setup/support refresh: `Evironmetrics---REVISED-DOC-Corrected/scripts/refresh_exal_m_t1_generated_assets.py`
- current-model support refresh: `Evironmetrics---REVISED-DOC-Corrected/scripts/refresh_current_model_output_support_figures.py`
- cutoff synthesis-family refresh: `Evironmetrics---REVISED-DOC-Corrected/scripts/refresh_cutoff_synthesis_families.py`

Stage 1 article-refresh gate:
- `refresh_all_generated_assets.py` is the approved entrypoint
- corrected setup/support, forecast-context, and cutoff synthesis families are required
- current-model historical-support refresh is separately gated behind `--strict-current-model-support`
- if corrected fit caches are absent, the refresh writes:
  - `Evironmetrics---REVISED-DOC-Corrected/artifacts/historical_support_from_current_models/refresh_status.json`
  and preserves the prior frozen bundle instead of failing the entire Stage 1 refresh

Deliverables:
- refreshed input sanity audit
- refreshed historical-support audit snapshot
- approved-launcher qualification note
- main-model bundle/figure lineage note
- explicit synthesis-family promotion plan for all cutoffs
- remaining-family relaunch matrix:
  - `reports/he2_full_crps_stage1_contract_20260516/remaining_family_relaunch_matrix.csv`
  - `reports/he2_full_crps_stage1_contract_20260516/remaining_family_spec_freeze.csv`
- Wave A row selection:
  - `reports/he2_full_crps_stage1_contract_20260516/wave_a_ndlm_rows.csv`

Acceptance gate:
- one and only one launcher path is approved for corrected relaunch use
- every remaining family is tied to its current publication-winning spec token
- the main-model revised-doc figure lineage is verified against the corrected bundle contract

### Stage 2. Build the remaining-family relaunch matrix

Purpose:
- convert the publication manifest into an explicit relaunch plan for the remaining CRPS-table rows

Actions:
1. inventory the remaining 8 Bayesian families across all 5 cutoffs
2. map each family to:
   - current publication run lineage
   - implementation class
   - likelihood mode
   - transfer mode
   - current resolved config path
3. define which rows will be corrected by Bayesian reruns and which rows are direct baseline rows to refresh later

Deliverables:
- one machine-readable remaining-family relaunch matrix
- one reviewer-friendly markdown summary of the remaining scope

Acceptance gate:
- every non-`exdqlm_multivar_keep` Bayesian family is explicitly accounted for
- direct baseline rows are tracked separately instead of disappearing implicitly into compare bundles

### Stage 3. Build the shared-input and config promotion contract for remaining families

Purpose:
- make the remaining-family relaunch use the corrected shared-input lineage without accidentally changing the scientific model specification

Actions:
1. build family-specific corrected relaunch configs by starting from publication `resolved_config.yaml`
2. replace only the input-layer surfaces with canonical shared paths:
   - parameters
   - retros
   - NWS forecast
   - GloFAS forecast
   - deterministic-climate handoff
   - `PPT`, `SOIL`, `PCA` covariate paths
3. pin `data_start = 1987-05-29`
4. pin `log1p_cms` transform contract
5. preserve family-specific statistical structure unless a documented family-specific relaunch fix is already frozen

Deliverables:
- remaining-family relaunch template(s)
- batch files for staged execution
- frozen generated-config provenance contract

Acceptance gate:
- the relaunch builder can produce corrected configs for all remaining families
- config patches are limited to shared-input / workflow contract rewiring unless explicitly documented otherwise

### Stage 4. Add a cross-family validator gate

Purpose:
- promote the current within-cutoff alignment check from a single-family guarantee to a full-table guarantee

Actions:
1. extend the existing relaunch validator usage to run across the selected remaining families
2. require within-cutoff identity across families for:
   - `parameters_path`
   - `retros_path`
   - `nws_forecast_path`
   - `glofas_forecast_path`
   - `existing_bundle_path`
   - deterministic-climate `handoff_root`
   - `covariate_features` settings
   - covariate paths for `PPT`, `SOIL`, `PCA`
3. require `covariate_features.csv` presence in all smoke outputs
4. require `data_start_filter_summary.txt` to show `1987-05-29`
5. require legacy-log-ready retros checks where the workflow expects them

Deliverables:
- updated validation summary
- cutoff bundle audit covering the whole remaining relaunch scope

Acceptance gate:
- no family within the same cutoff is allowed to drift onto a different shared-input root

### Stage 5. Prelaunch smoke validation by implementation class

Purpose:
- reduce launch risk by proving the remaining-family configs actually run under the corrected contract before full rollout

Recommended smoke grouping:

#### Wave A: theory-aligned normal families
- `ndlm_univar_keep`
- `ndlm_main_drop`
- `ndlm_main_keep`

#### Wave B: univariate legacy-bridge families
- `dqlm_univar_al`
- `exdqlm_univar`

#### Wave C: multivariate legacy-bridge families
- `dqlm_multivar_al_drop`
- `dqlm_multivar_al_keep`
- `exdqlm_multivar_drop`

Actions:
1. run data-prep shared-input smokes per cutoff
2. run fit-only smokes per family class
3. run representative full-pipeline smokes for each wave
4. confirm post-stage cleanup still behaves correctly

Deliverables:
- smoke run logs
- smoke validation summary
- evidence that each implementation class can run under the corrected bundle contract

Acceptance gate:
- no family wave proceeds to production launch until its smoke passes

### Stage 6. Relaunch the remaining Bayesian families in controlled waves

Purpose:
- finish the CRPS-table Bayesian rows under the corrected lineage without turning the rollout into one unmanageable batch

Recommended rollout order:

1. Wave A: NDLM families
2. Wave B: univariate AL / exAL families
3. Wave C: multivariate AL / exAL drop families

Why this order:
- theory-aligned NDLM families are generally the simplest operationally
- univariate legacy-bridge families have lower dimensionality than multivariate legacy-bridge families
- multivariate legacy-bridge families are the highest-risk remaining wave after `exdqlm_multivar_keep`

Actions for each wave:
1. launch the selected family wave across all 5 cutoffs
2. use the corrected shared bundles and canonical deterministic-climate/GDPC contract
3. keep run roots and compare bundles separated by wave and lineage
4. stop and diagnose family-specific regressions before widening further

Deliverables:
- completed corrected run roots for the wave
- completed `post`, `validate`, and `report` outputs
- refreshed wave compare bundles

Acceptance gate:
- each wave must complete before the next wave becomes authoritative

### Stage 7. Refresh direct baseline rows

Purpose:
- make the final CRPS table completely coherent, not half-corrected Bayesian rows plus stale direct-forecast rows

Rows:
- `nws_nwm_ensemble`
- `glofas_ensemble`

Actions:
1. define the corrected-refresh method for the direct ensemble rows from the same canonical shared bundles
2. regenerate the baseline-table rows for each cutoff
3. verify the resulting compare tables no longer rely on stale `baseline_tt` rows for table publication

Deliverables:
- refreshed direct baseline CRPS entries
- updated compare bundles with the full corrected table composition

Acceptance gate:
- final compare bundles use only corrected relaunch sources or explicitly refreshed direct-baseline sources

### Stage 8. Rebuild the final whole-table compare bundles

Purpose:
- produce the actual corrected CRPS-table outputs we can show, audit, and pass downstream to the revised article

Actions:
1. rebuild cutoff compare bundles after all rerunnable model rows and direct baselines are refreshed
2. require the final `crps_forecast_summary_all_models.csv` per cutoff to contain no stale baseline-family substitutions for rerunnable models
3. record source provenance per row in the final compare bundle outputs

Deliverables:
- final corrected compare bundles for all 5 cutoffs
- whole-table provenance summary

Acceptance gate:
- the final compare bundles are fully lineage-clean for the intended corrected table state

### Stage 9. Refresh article-side generated bundles

Purpose:
- wire the corrected rerun outputs into the revised article repo through the canonical refresh path, not manual copying

Actions:
1. refresh publication-manifest snapshots
2. refresh setup/support bundles if any selected-run sources changed
3. refresh review reports and generated asset inventory
4. preserve the publication-state snapshots alongside the corrected-state outputs

Use:
- `Evironmetrics---REVISED-DOC-Corrected/scripts/refresh_all_generated_assets.py`
- narrower article-side helpers only when intentionally refreshing one bundle family in isolation

Deliverables:
- refreshed article-side generated bundles
- refreshed generated asset inventory
- refreshed article-side review reports

Acceptance gate:
- every manuscript-facing refreshed asset is traceable to a corrected workflow-side lineage

### Stage 10. Reviewer-facing evidence packaging

Purpose:
- make the corrected rerun phase easy to explain and defend to reviewers

Actions:
1. prepare a corrected-lineage summary note
2. include:
   - exact bundle root
   - exact `data_start`
   - deterministic-climate policy summary
   - GDPC lineage summary
   - transform contract summary
   - family rollout order
   - validation gates passed
   - final row source provenance summary
3. mirror the relevant provenance snapshots into the revised article repo if needed

Deliverables:
- reviewer-shareable methodology addendum or appendix note
- corrected-lineage provenance packet

## Testing And Verification Plan

### A. Config / builder tests

Must pass before launch:

- builder selection tests
- publication relaunch template tests
- bundle-path construction tests
- canonical GDPC compatibility-alias tests

### B. Prelaunch validator tests

Must pass for the selected remaining-family wave:

- bundle existence checks
- retros start/end checks
- within-cutoff alignment checks across families
- covariate-feature presence checks
- representative full-pipeline smokes

### C. Runtime verification

Must pass during rollout:

- row-level `fit`, `post`, `validate`, `report` completion
- expected cleanup behavior after `post`
- compare bundle generation
- no silent failures in family-specific legacy-bridge paths

### D. Final table integrity checks

Must pass before article refresh:

- all corrected rerunnable rows appear in final compare bundles
- no stale `baseline_tt` source rows remain for rerunnable model families
- direct baseline rows are refreshed or explicitly frozen with documented rationale
- all final rows carry reviewer-auditable source provenance

## Decision Rules

### Decision 1. What stays frozen from publication state?

Frozen:
- the current publication manifest as a publication-state artifact
- the current publication CRPS values as publication-state evidence
- article-side frozen snapshots of publication state

Not frozen:
- the next corrected rerun lineage
- the refreshed corrected CRPS table built from that lineage

### Decision 2. What model specifications may change?

Default answer:
- none, except the already proven `exdqlm_multivar_keep` relaunch path

Interpretation:
- for remaining families, preserve publication model specs
- change only shared-input wiring and relaunch scaffolding unless a family-specific correction is explicitly documented and justified

### Decision 2A. Which launcher is allowed?

Allowed:
- the publication-manifest-driven relaunch builder and validator stack

Not allowed as corrected launch authority:
- older family-specific featurecov / all9 / NDLM matrix builders that rewrite from older source snapshots

Interpretation:
- legacy builders may still inform audits and historical traceability
- they should not be the mechanism that launches the corrected remaining-family relaunch

### Decision 2B. How do we treat epsilon and discount experiments?

Default answer:
- publication-winning choices are frozen per row and reused

Interpretation:
- we do not reopen epsilon or discount search during the relaunch stage
- we relaunch the current publication-selected winner on corrected bundles
- any corrective row-level override must be explicit, auditable, and preserved in `frozen_spec_manifest.csv`

### Decision 3. What counts as “whole table ready”?

Not enough:
- compare bundles exist
- rows have all expected model IDs

Required:
- all rerunnable Bayesian rows have been recomputed on the corrected lineage
- direct baseline rows are refreshed or explicitly accounted for
- article-side refresh completed
- final compare bundles are lineage-clean
- main-model five-cutoff support/forecast/synthesis figure families are wired to the corrected lineage

## Recommended First Execution Slice

The best first execution slice after this plan is approved is:

1. refresh the launcher/spec/input sanity and historical-support audits
2. freeze the approved launcher path and explicitly retire the legacy launchers from corrected production use
3. refresh and validate the main-model five-cutoff setup/support and forecast-context figure families
4. define the cutoff-wide Figure 7 / A2 synthesis-family promotion plan
5. build the remaining-family relaunch matrix
6. build the multi-family corrected relaunch template(s)
7. add the cross-family validation gate
8. run a Wave A prelaunch validation and smoke pass for:
   - `ndlm_univar_keep`
   - `ndlm_main_drop`
   - `ndlm_main_keep`

Concrete Stage 1 execution artifacts:
- launcher qualification bundle:
  - `reports/he2_full_crps_stage1_contract_20260516/HE2_FULL_CRPS_STAGE1_LAUNCHER_QUALIFICATION_20260516.md`
  - `reports/he2_full_crps_stage1_contract_20260516/launcher_qualification.json`
- revised-article synthesis review:
  - `Evironmetrics---REVISED-DOC-Corrected/reports/five_cutoff_synthesis_review/FIVE_CUTOFF_SYNTHESIS_REVIEW.md`
- Wave A NDLM template:
  - `config/he2_bayesian_publication_relaunch_wave_a_ndlm_20260516.template.yaml`
- Wave A NDLM batch:
  - `config/he2_relaunch_batches/he2_wave_a_ndlm_remaining_families_20260516.yaml`
- Wave A validator runbook:
  - `repro/run/HE2_WAVE_A_NDLM_VALIDATOR_RUNBOOK_20260516.md`

Why this is optimal:
- it removes launcher ambiguity before we spend time on the wrong runs
- it makes the revised article bundle lineage part of the relaunch contract from the beginning
- it still exercises the corrected full-history/shared-input contract across multiple families immediately
- it uses simpler theory-aligned families first
- it keeps the scope large enough to be meaningful but small enough to debug cleanly

## Final Exit Criteria

This broader relaunch phase is complete only when:

1. all 9 Bayesian families across all 5 cutoffs have a corrected relaunch lineage,
2. the two direct ensemble rows are refreshed or deliberately frozen with explicit rationale,
3. every corrected rerun uses the same within-cutoff shared-input bundle lineage,
4. all reruns use the full-history `1987-05-29 -> cutoff` support contract,
5. all reruns use the updated deterministic-climate blended PPT and soil inputs,
6. all reruns use the canonical GDPC-backed climate covariate contract,
7. all final compare bundles are rebuilt and lineage-clean,
8. article-side generated bundles are refreshed through the canonical revised-article workflow,
9. the main-model cutoff-wide support / forecast-context / synthesis figure families are refreshed and reviewer-auditable,
10. and the final provenance packet is strong enough to share with reviewers.

## Bottom Line

The completed `exdqlm_multivar_keep` relaunch was the pilot and the workflow-hardening pass.

The next correct move is **not** another family-specific rescue cycle.
The next correct move is to turn that success into a **whole-table corrected relaunch program** under the same bundle, transform, deterministic-climate, GDPC, and article-refresh contracts.

That is the path that is most reproducible, most reviewer-defensible, and least dependent on memory.
