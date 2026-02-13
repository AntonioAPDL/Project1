# Unified Multi-Model Workflow Tracker (Living)

Date: 2026-02-10  
Repo root: `/data/muscat_data/jaguir26/project1_ucsc_phd`  
Status: Active planning + execution tracker  
Primary audience: project maintainer + Codex

## 1) Purpose

This document tracks the step-by-step migration to one unified workflow that produces, in a single run graph:

1. Multivariate exDQLM outputs (current DISC-W path).
2. Univariate exDQLM outputs (currently from legacy `OptimalModelSLexAL.r`).
3. Multivariate NDLM outputs (currently from legacy `DISC_Optimal_Synth_Ranges_NDLM.r`).
4. Post-processing outputs, validations, and reports with explicit model-family separation.

This is a living document and must be updated when:

1. A decision changes.
2. A phase is started/closed.
3. A risk appears/resolves.
4. A major implementation deviation is accepted.

## 2) Current Repo Reality Snapshot

## 2.1 What is currently orchestrated by the unified runner

- Unified runner calls stages: `forecats`, `fit`, `post`, `validate`, `report`.
- Unified runner now also supports `data_prep_shared` stage between `forecats` and `fit`.
- Current `fit` stage always supports multivariate exDQLM (DISC-W) and can optionally run legacy univariate + legacy NDLM bridges via model toggles.
- Current `post` stage runs `scripts/run_environmetrics_figures.R`.

Repo references:

- `scripts/unified_run.R`
- `R/unified/stages/stage_fit.R`
- `R/unified/stages/stage_post.R`

## 2.2 What is not yet orchestrated as first-class unified model stages

- `OptimalModelSLexAL.r` (univariate exDQLM) and `DISC_Optimal_Synth_Ranges_NDLM.r` (NDLM) are orchestrated as legacy bridge calls inside unified `fit`, but they are not yet modular first-class theory-aligned stages.

Repo references:

- `run_scripts_SL.py`
- `DISC_Optimal_Synth_Ranges_NDLM.r`
- `OptimalModelSLexAL.r`

## 2.3 Current hidden dependency risk in post-processing

Strict post mode now resolves model-state artifacts from run-scoped manifest paths; legacy root fallback remains a controlled non-strict compatibility path.

Repo references:

- `R/environmetrics/00_paths.R`
- `R/environmetrics/30_univariate_and_misc.R`

Implication:

- A unified run can still depend on stale/non-run-scoped NDLM/univariate artifacts unless decoupled.

## 3) Theory Source-of-Truth Policy (Locked)

All new or corrected model logic must follow these theory repos:

1. NDLM: `/data/muscat_data/jaguir26/NDLM---Ensemble`
2. Multivariate exDQLM: `/data/muscat_data/jaguir26/exDQLM---Ensemble`
3. Univariate exDQLM: `/data/muscat_data/jaguir26/univ-exDQLM---Ensemble`

Relevant main theory files:

- `/data/muscat_data/jaguir26/NDLM---Ensemble/docs/derivations/main.tex`
- `/data/muscat_data/jaguir26/exDQLM---Ensemble/main.tex`
- `/data/muscat_data/jaguir26/univ-exDQLM---Ensemble/main.tex`

Precedence rule:

1. Theory repo equations/specification.
2. Unified workflow contracts (config, manifest, stage interfaces).
3. Legacy script behavior (legacy is reference material, not authority, when conflicting with theory).

## 4) Locked Decisions (from maintainer)

| ID | Decision | Status | Notes |
|---|---|---|---|
| D-001 | Default behavior for NDLM/univariate modernization is theory-first from external repos, not legacy-discount parity-first. | Locked | Legacy NDLM/univariate may be wrong in parts; multivariate exDQLM path in this repo is currently considered correct. |
| D-002 | NDLM implementation scope is VB only (no MCMC parity hooks required now). | Locked | MCMC can be future work item. |
| D-003 | NDLM output naming will be neutral (`ndlm_main` style), not quantile-labeled `50` compatibility naming. | Locked | Avoid semantic confusion. |
| D-004 | Univariate modernization must be structurally compatible with current downstream expectations (not byte-identical `.RData`). | Locked | Keep object contracts and shape compatibility. |
| D-005 | In unified config, NDLM should be mandatory when `models.run_ndlm=true`; default intended as enabled in production mode. | Locked | No silent NDLM skip in full production runs. |
| D-006 | Post outputs/reports should remain separated by model family; do not merge posterior outputs into a single blended block. | Locked | Shared inputs are allowed; outputs remain clearly separated. |
| D-007 | Sequencing is hybrid: wire legacy scripts into unified runner early for operational continuity, while replacing them module-by-module with theory-aligned implementations. | Locked | This is now the active and accepted execution strategy. |
| D-008 | Preserve `post/outputs/<RUN_ID>/` nesting until validate contract is explicitly versioned. | Locked | `stage_validate` currently compares against `run_root/post/outputs/<RUN_ID>`; do not break this path contract before validate v2. |
| D-009 | Preserve current DISC-W fit output contract `fit/q=<QQ>/outputs/...` until family-path cutover. | Locked | Existing fit/post tooling and run artifacts rely on this structure; migration to `fit/exdqlm_multivar/...` is a versioned cutover item. |
| D-010 | P5 closure is accepted via strict run-scoped figures-on smoke using smoke-fast path; full heavy figure hardening is a separate follow-up item. | Locked | Requires non-null manifest closure, run-scoped load proof, and PNG outputs under run root. |

## 5) Target End-State Architecture

## 5.1 High-level stage graph

`unified_run -> data_prep_shared -> fit_exdqlm_multivar -> fit_exdqlm_univar -> fit_ndlm_main -> post -> validate -> report`

## 5.2 Output organization (family-separated)

Under `repro/runs/<RUN_ID>/`:

- Manifest v1 compatibility path (current, keep through cutover):
  - `fit/q=<QQ>/outputs/...` (DISC-W)
  - `post/outputs/<RUN_ID>/...` (required nested run id)
  - `validate/...`
  - `report/...`
- Manifest v2 target path (after versioned cutover):
  - `fit/exdqlm_multivar/q=<QQ>/...`
  - `fit/exdqlm_univar/q=<QQ>/...`
  - `fit/ndlm_main/...`
  - `post/outputs/<RUN_ID>/exdqlm_multivar/...`
  - `post/outputs/<RUN_ID>/exdqlm_univar/...`
  - `post/outputs/<RUN_ID>/ndlm_main/...`
- `validate/...`
- `report/...`

## 5.3 Manifest requirements

Manifest must explicitly label:

1. Which families executed.
2. Which families were theory-aligned vs legacy-reference mode.
3. Artifact paths per family.
4. Version tags for model interfaces.

## 6) Phase Plan and Gates

Status legend:

- `[ ]` not started
- `[~]` in progress
- `[x]` completed
- `[!]` blocked

| Phase | Status | Goal | Entry Criteria | Exit Gate |
|---|---|---|---|---|
| P0 | [x] | Governance + contract freeze | Tracker approved | Contracts document + decision log initialized and D-007 locked |
| P1 | [x] | Shared input contract + adapters | P0 done | Single run-scoped input bundle consumable by all three families with forecats snapshot integration and per-family fast-fail gating |
| P2 | [x] | Legacy orchestration bridge in unified runner | P0 done | Unified runner can launch current legacy univariate + NDLM as controlled sub-stages |
| P3 | [~] | Univariate modularization (theory-aligned) | P2 done | New modular univariate stage passes structural compatibility checks |
| P4 | [~] | NDLM modularization (theory-aligned VB) | P2 done | New modular NDLM stage with forecast-window stochastic `W` policy implemented per NDLM theory |
| P5 | [x] | Post decoupling from root artifacts | P2 done | Post loads only manifest-declared run-scoped artifacts and strict figures-on smoke closes with non-null `finished_at_utc` |
| P6 | [~] | Parallel orchestration hardening | P5 done | exDQLM multivar + univar parallel; NDLM isolated; no cross-stage clobbering |
| P7 | [~] | Validation/report family-aware automation | P6 done | PASS criteria include per-family artifact checks + write-audit + manifest closure |
| P8 | [~] | Cutover + deprecation plan | P7 done | Theory-aligned stages become default; legacy stages optional fallback |

## 7) Detailed Task Backlog

## 7.1 P0 Tasks

- [x] `T-P0-01`: Create model-family interface contract doc (inputs/outputs/object names).
- [x] `T-P0-02`: Define acceptance criteria per family (minimal required artifacts + shape checks).
- [x] `T-P0-03`: Confirm D-007 (hybrid sequencing) as locked or replace it.

## 7.2 P1 Tasks (Shared Inputs)

- [x] `T-P1-01`: Build shared data-prep adapter module that writes run-scoped canonical inputs.
- [x] `T-P1-02`: Add input manifest entries per source file with hashes/scales.
- [x] `T-P1-03`: Add fast-fail checks for required per-family inputs.
- [x] `T-P1-04`: Freeze shared input bundle layout under `repro/runs/<RUN_ID>/inputs/shared/...`; when forecats build mode is enabled, snapshot/copy required forecats outputs into this shared input tree and record hashes in manifest.

## 7.3 P2 Tasks (Legacy Bridge)

- [x] `T-P2-01`: Add unified stage wrapper for legacy univariate script execution.
- [x] `T-P2-02`: Add unified stage wrapper for legacy NDLM script execution.
- [x] `T-P2-03`: Ensure run-scoped output capture and explicit legacy-mode labeling in manifest.

## 7.4 P3 Tasks (Univariate Modular, Theory-Aligned)

- [x] `T-P3-01`: Split `OptimalModelSLexAL.r` into modular files (setup/inputs/model/update/save).
- [x] `T-P3-02`: Reconcile equations with `univ-exDQLM---Ensemble/main.tex`.
- [x] `T-P3-03`: Add structural compatibility tests against expected post interfaces.
- [x] `T-P3-04`: Add theory-mode diagnostics (finite/shape/symmetry/PSD sampled checks) and equation-to-code audit notes for univariate modules.

## 7.5 P4 Tasks (NDLM Modular, Theory-Aligned VB)

- [x] `T-P4-01`: Split `DISC_Optimal_Synth_Ranges_NDLM.r` into modular files.
- [~] `T-P4-02`: Replace forecast-window discount-factor-only path with theory-aligned stochastic `W` treatment (VB only).
- [~] `T-P4-03`: Update ELBO and VB covariance distribution updates per NDLM derivations.
- [x] `T-P4-04`: Emit neutral NDLM artifacts (`ndlm_main`) with stable schema.
- [x] `T-P4-05`: Add NDLM structural compatibility contract checks against post-consumed aliases.
- [x] `T-P4-06`: Add theory-mode diagnostics (finite/shape/symmetry/PSD sampled checks + summary-log invariants) and equation-to-code audit notes for NDLM modules.

## 7.6 P5 Tasks (Post Decoupling)

- `T-P5-01`: Remove hardcoded root `.RData` loads in `R/environmetrics/30_univariate_and_misc.R`.
- `T-P5-02`: Load all family artifacts from manifest paths.
- `T-P5-03`: Keep family-specific outputs separated in post output tree.

## 7.7 P6-P8 Tasks (Orchestration, Validation, Cutover)

- `T-P6-01`: Add explicit model-family toggles under unified config.
- `T-P6-02`: Add scheduling policy for parallel exDQLM stages + NDLM isolation.
- `T-P7-01`: Extend validator to enforce per-family required outputs.
- `T-P7-02`: Extend report to summarize each family separately.
- `T-P8-01`: Change defaults to theory-aligned stages; keep legacy as opt-in fallback.
- [x] `T-P8-02`: Add end-to-end unified-run smoke integration coverage for post table exports and post artifact allowlist capture.

## 8) Risk Register (Live)

| Risk ID | Severity | Description | Mitigation | Owner | Status |
|---|---|---|---|---|---|
| R-001 | Critical | NDLM forecast-window covariance mismatch vs theory can invalidate inference. | Prioritize P4 equation-to-code audit + tests before making NDLM default authoritative. | TBD | Mitigating (theory-aligned NDLM mode + stochastic `W` smoke path now wired and exercised) |
| R-002 | High | Post currently consumes root pre-generated NDLM/univariate artifacts. | Execute P5 decoupling before declaring full autonomy. | TBD | Mitigating (strict run-scoped smoke passed) |
| R-003 | High | Legacy scripts contain duplicated core functions and fragile patterns. | Modularize with strict tests and narrow wrappers. | TBD | Open |
| R-004 | Medium | Parallel orchestration may induce file collisions without strict run-scope contracts. | Enforce per-family/per-quantile isolated output roots + write-audit. | TBD | Mitigating (P2B fit-stage write-audit pass with empty outside-run-root diff) |
| R-005 | Medium | Ambiguity on sequencing can delay implementation. | Lock D-007 or replace with alternate sequence immediately after P0. | Maintainer | Mitigated (D-007 locked) |
| R-006 | High | DISC-W warm-start can load root `DISC_variables_*` paths, violating run-scoped reproducibility if enabled. | Keep warm-start disabled by default; if enabled, require run-scoped warm-start source path recorded in manifest before stage execution. | TBD | Mitigating (legacy bridge env routing now run-scoped; warm-start remains disabled by default) |
| R-007 | Medium | Post reads `y_reps*.rds` via relative paths, creating working-directory-sensitive behavior. | In P5, enforce absolute/manifest-declared paths for these intermediates and fail fast on unresolved relative reads. | TBD | Mitigating (run-scoped cache path enforced) |

## 9) Validation and Done Criteria

A run is "full PASS" only if all hold:

1. Manifest has non-null `timestamps.finished_at_utc`.
2. Manifest `validation.status == pass`.
3. Required artifacts exist for each enabled family.
4. Post outputs exist in family-separated locations.
5. Compare report + write-audit artifacts exist and pass gate policies.
6. Completion report exists and references all family outputs.

## 10) Update Protocol (How to Maintain This Tracker)

At each planning/execution checkpoint:

1. Update phase status table.
2. Add decision entries if scope/behavior changes.
3. Add a progress log entry.
4. Mark completed tasks with evidence paths.
5. Update risk statuses.

## 10.1 Progress Log Template

```markdown
### Progress Update YYYY-MM-DD HH:MM UTC
- Phase: P?
- Change type: decision|implementation|validation|rollback
- Summary:
- Files touched:
- Evidence paths:
- New risks:
- Next action:
```

## 10.2 Decision Log Template

```markdown
| Decision ID | Date | Decision | Why | Impacted phases | Status |
|---|---|---|---|---|---|
| D-XYZ | YYYY-MM-DD | ... | ... | P? | Proposed/Locked/Superseded |
```

## 10.3 Progress Log Entries

### Progress Update 2026-02-10 02:24 UTC
- Phase: P2
- Change type: implementation
- Summary: wired optional legacy bridges in unified `fit` stage for univariate exDQLM and NDLM with run-scoped outputs; added config toggles (default OFF) and fit-only smoke config.
- Files touched:
  - `R/unified/config.R`
  - `config/unified_run.template.yaml`
  - `R/unified/stages/stage_fit.R`
  - `OptimalModelSLexAL.r`
  - `DISC_Optimal_Synth_Ranges_NDLM.r`
  - `config/unified_runs/smoke_p2_legacy_bridge.yaml`
  - `repro/UNIFIED_MULTIMODEL_WORKFLOW_TRACKER.md`
- Evidence paths (expected after smoke run):
  - `repro/runs/<RUN_ID>/resolved_config.yaml`
  - `repro/runs/<RUN_ID>/run_manifest.yaml`
  - `repro/runs/<RUN_ID>/fit/q=50/outputs/DISC_variables_50_exAL_synth_DISC.RData`
  - `repro/runs/<RUN_ID>/fit/exdqlm_univar/q=50/outputs/variables_50_exAL_synth_DISC_uni.RData`
  - `repro/runs/<RUN_ID>/fit/ndlm_main/outputs/DISC_variables_50_NDLM_synth_DISC.RData`
- New risks: none (no model semantics changed in this chunk).
- Next action: run smoke config, verify artifact existence + manifest artifact entries for `fit/exdqlm_univar/...` and `fit/ndlm_main/...`, then scope P2 follow-up.

### Progress Update 2026-02-10 03:05 UTC
- Phase: P2
- Change type: validation
- Summary: hardened P2 bridge wiring and passed fit-only smoke gate with run-scoped univariate and NDLM legacy outputs recorded in manifest v1.
- Files touched:
  - `R/unified/config.R`
  - `config/unified_run.template.yaml`
  - `config/unified_runs/smoke_p2_legacy_bridge.yaml`
  - `R/unified/stages/stage_fit.R`
  - `repro/UNIFIED_MULTIMODEL_WORKFLOW_TRACKER.md`
- Evidence paths:
  - `repro/runs/20260209_183637/resolved_config.yaml`
  - `repro/runs/20260209_183637/run_manifest.yaml`
  - `repro/runs/20260209_183637/fit/exdqlm_univar/q=50/outputs/variables_50_exAL_synth_DISC_uni.RData`
  - `repro/runs/20260209_183637/fit/exdqlm_univar/q=50/logs/univar_legacy.log`
  - `repro/runs/20260209_183637/fit/ndlm_main/outputs/DISC_variables_50_NDLM_synth_DISC.RData`
  - `repro/runs/20260209_183637/fit/ndlm_main/logs/ndlm_legacy.log`
  - `repro/runs/20260209_183637/run_manifest.yaml` artifact entries include both paths above
- New risks: none introduced; default behavior remains unchanged unless model toggles are enabled.
- Next action: start next chunk after maintainer review/smoke confirmation.

### Progress Update 2026-02-10 05:30 UTC
- Phase: P5
- Change type: implementation+validation
- Summary: post stage now resolves run-scoped model-state artifacts from manifest and passes those paths via env vars; post modules now read run-scoped paths/cache in strict mode and no longer rely on repo-root hardcoded loads in this smoke path.
- Files touched:
  - `R/unified/utils_artifact_locator.R`
  - `scripts/unified_run.R`
  - `R/unified/stages/stage_post.R`
  - `scripts/run_environmetrics_figures.R`
  - `R/environmetrics/00_paths.R`
  - `R/environmetrics/30_univariate_and_misc.R`
  - `R/environmetrics/40_figures.R`
  - `config/unified_runs/smoke_p5_post_runscoped.yaml`
  - `repro/UNIFIED_MULTIMODEL_WORKFLOW_TRACKER.md`
- Evidence paths:
  - `/tmp/project1_ucsc_phd/repro/runs/20260209_210504/resolved_config.yaml`
  - `/tmp/project1_ucsc_phd/repro/runs/20260209_210504/run_manifest.yaml`
  - `/tmp/project1_ucsc_phd/repro/runs/20260209_210504/post/logs/post_runner.log`
  - `/tmp/project1_ucsc_phd/repro/runs/20260209_210504/post/outputs/20260209_210504/post_smoke_marker.txt`
  - `/tmp/project1_ucsc_phd/repro/runs/20260209_210504/fit/exdqlm_univar/q=50/outputs/variables_50_exAL_synth_DISC_uni.RData`
  - `/tmp/project1_ucsc_phd/repro/runs/20260209_210504/fit/ndlm_main/outputs/DISC_variables_50_NDLM_synth_DISC.RData`
- Validation notes:
  - `run_manifest.yaml` has non-null `timestamps.finished_at_utc`.
  - Strict mode was active (`UNIFIED_REQUIRE_RUNSCOPED_POST=TRUE`) with legacy fallback disabled.
  - Post log shows resolved run-scoped artifact paths and no repo-root `variables_*/DISC_variables_*` loads.
- New risks:
  - None added; this chunk mitigates run-scope path coupling risks (R-002, R-007).
- Next action:
  - Continue P5 by extending run-scoped manifest-driven inputs to full figure mode and then validate/report stages.

### Progress Update 2026-02-10 11:20 UTC
- Phase: P2 + P5
- Change type: governance+hygiene reconciliation
- Summary: reconciled tracker-vs-history mismatch by committing outstanding P2 bridge files (model toggles + legacy bridge wiring + run-scoped legacy output env overrides) and removed machine-specific `/tmp` default from P5 smoke config.
- Files touched:
  - `DISC_Optimal_Synth_Ranges_NDLM.r`
  - `OptimalModelSLexAL.r`
  - `R/unified/config.R`
  - `R/unified/stages/stage_fit.R`
  - `config/unified_run.template.yaml`
  - `config/unified_runs/smoke_p2_legacy_bridge.yaml`
  - `config/unified_runs/smoke_p5_post_runscoped.yaml`
  - `config/unified_runs/local_overrides.example.yaml`
  - `.gitignore`
  - `repro/REPO_REALITY_2026-02-09.md`
  - `repro/UNIFIED_MULTIMODEL_WORKFLOW_TRACKER.md`
- Evidence paths:
  - `repro/runs/20260209_183637/run_manifest.yaml` (P2 smoke evidence, non-null finished timestamp, univar+NDLM artifacts)
  - `/tmp/project1_ucsc_phd/repro/runs/20260209_210504/run_manifest.yaml` (P5 strict run-scoped smoke evidence, figures disabled)
- Validation notes:
  - No new heavy runs executed in this chunk.
  - Portability default restored to repo-relative `run_root: "repro/runs"` for P5 smoke config.
  - Local machine overrides are now documented via `config/unified_runs/local_overrides.example.yaml` with untracked `config/unified_runs/local_overrides.yaml`.
- Next action:
  - Run one strict smoke with `post.figures=true` and then one validate/report smoke from run-scoped artifacts (no code changes unless failure evidence requires it).

### Progress Update 2026-02-11 01:05 UTC
- Phase: P5
- Change type: implementation+validation
- Summary: closed strict run-scoped figures-on smoke by adding a smoke-fast figures module path (`UNIFIED_POST_SMOKE_FAST=TRUE`) while preserving default post behavior; post completed and unified manifest closed with non-null `finished_at_utc`.
- Files touched:
  - `R/unified/stages/stage_post.R`
  - `scripts/run_environmetrics_figures.R`
  - `R/environmetrics/40_figures.R`
  - `R/environmetrics/40_figures_smoke_fast.R`
  - `config/unified_runs/smoke_p5_post_runscoped_figures.yaml`
  - `repro/UNIFIED_MULTIMODEL_WORKFLOW_TRACKER.md`
- Smoke config used:
  - `config/unified_runs/smoke_p5_post_runscoped_figures.yaml` (run-specific overlay set `run_id: p5_figures_smoke_20260210_v13` for evidence capture)
- Evidence paths:
  - `repro/runs/p5_figures_smoke_20260210_v13/run_manifest.yaml`
  - `repro/runs/p5_figures_smoke_20260210_v13/post/logs/post_runner.log`
  - `repro/runs/p5_figures_smoke_20260210_v13/post/outputs/p5_figures_smoke_20260210_v13/All_ELBOS_DISC.png`
  - `repro/runs/p5_figures_smoke_20260210_v13/post/outputs/p5_figures_smoke_20260210_v13/SMOKE_OBSERVED_SERIES_DISC.png`
- Validation notes:
  - `run_manifest.yaml` has `timestamps.finished_at_utc: 2026-02-11T01:01:34Z`.
  - Root-load grep returned no matches for `"/project1_ucsc_phd/(variables_|DISC_variables_)"` under post logs.
  - Post log shows strict run-scoped env and resolved model-state paths under `repro/runs/p5_figures_smoke_20260210_v13/fit/...`.
- Next action:
  - Move to P0 contract freeze (lock D-007 explicitly and finalize family acceptance criteria), then start P1 shared input bundle.

### Progress Update 2026-02-11 01:20 UTC
- Phase: P0 + P1
- Change type: decision+implementation+validation
- Summary: closed P0 with explicit contract freeze artifacts and started P1 by implementing `data_prep_shared` stage that materializes run-scoped shared inputs and records them in manifest v1-compatible fields.
- Files touched:
  - `repro/contracts/UNIFIED_FAMILY_CONTRACTS_v1.md`
  - `repro/P0_CONTRACT_FREEZE_2026-02-11.md`
  - `R/unified/stages/stage_data_prep_shared.R`
  - `scripts/unified_run.R`
  - `R/unified/config.R`
  - `config/unified_run.template.yaml`
  - `config/unified_runs/smoke_p1_shared_inputs.yaml`
  - `repro/P1_SHARED_INPUTS_SMOKE_20260210_171855.md`
  - `repro/UNIFIED_MULTIMODEL_WORKFLOW_TRACKER.md`
- Smoke config used:
  - `config/unified_runs/smoke_p1_shared_inputs.yaml`
- Evidence paths:
  - `repro/runs/20260210_171855/resolved_config.yaml`
  - `repro/runs/20260210_171855/run_manifest.yaml`
  - `repro/runs/20260210_171855/inputs/shared/parameters/parameters.txt`
  - `repro/runs/20260210_171855/inputs/shared/retros/retros.csv`
  - `repro/runs/20260210_171855/inputs/shared/forecasts/nws_forecast.csv`
  - `repro/runs/20260210_171855/inputs/shared/forecasts/glofas_forecast.csv`
  - `repro/runs/20260210_171855/inputs/shared/covariates/cov_1_ELI.csv`
  - `repro/runs/20260210_171855/inputs/shared/covariates/cov_2_ONI.csv`
- Validation notes:
  - `run_manifest.yaml` has non-null `timestamps.finished_at_utc` (`2026-02-11T01:18:57Z`).
  - Manifest includes shared-input references under both `inputs[]` and `artifacts[]`.
- Next action:
  - Complete remaining P1 tasks (forecats snapshot integration + stricter per-family input gating) before beginning P3/P4 modular model replacements.

### Progress Update 2026-02-11 01:40 UTC
- Phase: P1
- Change type: implementation+validation
- Summary: completed remaining P1 scope by adding strict per-family shared-input fast-fail validation, forecats snapshot integration (`inputs/shared/forecats_bundle`), manifest hashing for snapshot + canonical shared inputs, and shared-input consumption preference from snapshot aliases.
- Files touched:
  - `R/unified/inputs_shared_validate.R`
  - `R/unified/stages/stage_data_prep_shared.R`
  - `R/unified/stages/stage_forecats.R`
  - `R/unified/stages/stage_fit.R`
  - `R/unified/stages/stage_post.R`
  - `R/unified/config.R`
  - `R/unified/manifest.R`
  - `R/unified/utils_hash.R`
  - `scripts/unified_run.R`
  - `config/unified_run.template.yaml`
  - `config/unified_runs/smoke_p1_forecats_snapshot.yaml`
  - `repro/P1_FORECATS_SNAPSHOT_SMOKE_20260210_173759.md`
  - `repro/UNIFIED_MULTIMODEL_WORKFLOW_TRACKER.md`
- Smoke config used:
  - `config/unified_runs/smoke_p1_forecats_snapshot.yaml`
- Evidence paths:
  - `repro/runs/20260210_173759/resolved_config.yaml`
  - `repro/runs/20260210_173759/run_manifest.yaml`
  - `repro/runs/20260210_173759/inputs/shared/parameters/parameters.txt`
  - `repro/runs/20260210_173759/inputs/shared/retros/retros.csv`
  - `repro/runs/20260210_173759/inputs/shared/forecasts/nws_forecast.csv`
  - `repro/runs/20260210_173759/inputs/shared/forecasts/glofas_forecast.csv`
  - `repro/runs/20260210_173759/inputs/shared/covariates/cov_01_ELI.csv`
  - `repro/runs/20260210_173759/inputs/shared/covariates/cov_02_ONI.csv`
  - `repro/runs/20260210_173759/inputs/shared/forecats_bundle/meta.yaml`
  - `repro/runs/20260210_173759/inputs/shared/forecats_bundle/inputs/retros_daily.csv`
  - `repro/runs/20260210_173759/inputs/shared/forecats_bundle/inputs/nws_weighted_daily.csv`
  - `repro/runs/20260210_173759/inputs/shared/forecats_bundle/inputs/glofas_weighted_daily.csv`
  - `repro/P1_FORECATS_SNAPSHOT_SMOKE_20260210_173759.md`
- Validation notes:
  - `run_manifest.yaml` has non-null `timestamps.finished_at_utc` (`2026-02-11T01:38:04Z`).
  - Manifest includes `role: input_snapshot` entries for snapshot copies and `role: shared_input` entries for canonical shared inputs, each with SHA256.
  - Fast-fail checks now execute at end of `data_prep_shared` and at start of `fit`/`post` when shared inputs are enabled/present.
- Next action:
  - Begin P3 and P4 modernization tracks using frozen P0/P1 contracts and keep P2/P5 bridges stable until cutover.

### Progress Update 2026-02-11 05:58 UTC
- Phase: P2B
- Change type: implementation+validation
- Summary: removed uncontrolled legacy bridge root IO by wiring univariate and NDLM scripts to run-scoped shared input env paths and run-scoped output/log paths under `fit/exdqlm_univar/...` and `fit/ndlm_main/...`; validated with strict fit-stage write-audit (`enforce_from_stage=2`, empty allowlist).
- Files touched:
  - `R/unified/stages/stage_fit.R`
  - `OptimalModelSLexAL.r`
  - `DISC_Optimal_Synth_Ranges_NDLM.r`
  - `config/unified_runs/smoke_p2b_no_root_writes.yaml`
  - `repro/P2B_NO_ROOT_WRITES_SMOKE_20260210_212458.md`
  - `repro/UNIFIED_MULTIMODEL_WORKFLOW_TRACKER.md`
- Smoke config used:
  - `config/unified_runs/smoke_p2b_no_root_writes.yaml`
- Evidence paths:
  - `repro/runs/20260210_212458/run_manifest.yaml`
  - `repro/runs/20260210_212458/fit/exdqlm_univar/q=50/outputs/variables_50_exAL_synth_DISC_uni.RData`
  - `repro/runs/20260210_212458/fit/ndlm_main/outputs/DISC_variables_50_NDLM_synth_DISC.RData`
  - `repro/runs/20260210_212458/fit/exdqlm_univar/q=50/logs/univar_legacy.log`
  - `repro/runs/20260210_212458/fit/ndlm_main/logs/ndlm_legacy.log`
  - `repro/runs/20260210_212458/validate/write_audit/fit/fs_diff.patch`
  - `repro/P2B_NO_ROOT_WRITES_SMOKE_20260210_212458.md`
- Validation notes:
  - `run_manifest.yaml` has non-null `timestamps.finished_at_utc` (`2026-02-11T05:56:49Z`).
  - Fit-stage write audit passed with `fs_diff.patch` size `0` bytes.
  - Legacy bridge artifacts are produced and hashed under run root; no new writes outside run root were detected for fit stage.
- Next action:
  - Start P3/P4 theory-aligned modularization while preserving P2/P5 run-scoped bridge contracts.

### Progress Update 2026-02-11 06:55 UTC
- Phase: P2C (P1/P2 schema hardening follow-up)
- Change type: implementation+validation
- Summary: hardened shared-input schema routing to prevent legacy bridge failures from malformed forecast files by (1) enforcing member-level GloFAS schema checks, (2) adding early NWS non-finite schema checks, and (3) canonicalizing snapshot alias selection so `glofas_forecast.csv` is always member-level while retros stays legacy-compatible.
- Files touched:
  - `R/unified/inputs_shared_validate.R`
  - `R/unified/stages/stage_forecats.R`
  - `R/unified/stages/stage_data_prep_shared.R`
  - `config/unified_runs/smoke_p2c_shared_inputs_schema.yaml`
  - `repro/P2C_SHARED_INPUTS_SCHEMA_SMOKE_20260210_222054.md`
  - `repro/UNIFIED_MULTIMODEL_WORKFLOW_TRACKER.md`
- Smoke config used:
  - `config/unified_runs/smoke_p2c_shared_inputs_schema.yaml`
- Evidence paths:
  - `repro/runs/20260210_222054/run_manifest.yaml`
  - `repro/runs/20260210_222054/inputs/shared/source_map.txt`
  - `repro/runs/20260210_222054/inputs/shared/forecats_bundle/snapshot_source_map.txt`
  - `repro/runs/20260210_222054/fit/exdqlm_univar/q=50/outputs/variables_50_exAL_synth_DISC_uni.RData`
  - `repro/runs/20260210_222054/fit/ndlm_main/outputs/DISC_variables_50_NDLM_synth_DISC.RData`
  - `repro/runs/20260210_222054/validate/write_audit/fit/fs_diff.patch`
  - `repro/P2C_SHARED_INPUTS_SCHEMA_SMOKE_20260210_222054.md`
- Validation notes:
  - `run_manifest.yaml` has non-null `timestamps.finished_at_utc` (`2026-02-11T06:53:15Z`).
  - Fit-stage write-audit diff is empty (`fs_diff.patch` size `0` bytes) with `enforce_from_stage=2` and empty allowlist.
  - Canonical shared GloFAS input is sourced from snapshot member-level file and passes schema validation before fit.
  - Legacy bridges complete without root writes using run-scoped shared inputs and run-scoped outputs.
- Next action:
  - Begin P3/P4 theory-aligned modularization using P1 canonical shared-input and P2B/P2C run-scoped bridge guarantees as baseline.

### Progress Update 2026-02-11 07:45 UTC
- Phase: P3
- Change type: implementation+validation
- Summary: introduced first theory-aligned univariate family modules and runner behind `models.exdqlm_univar.implementation_mode=theory_aligned`; wired `stage_fit` to dispatch by implementation mode while preserving legacy defaults and run-scoped artifact hashing.
- Files touched:
  - `R/unified/families/exdqlm_univar/00_constants.R`
  - `R/unified/families/exdqlm_univar/01_inputs.R`
  - `R/unified/families/exdqlm_univar/02_model_spec.R`
  - `R/unified/families/exdqlm_univar/03_updates_vb_or_fitloop.R`
  - `R/unified/families/exdqlm_univar/04_elbo_optional.R`
  - `R/unified/families/exdqlm_univar/05_save_state.R`
  - `R/unified/families/exdqlm_univar/zz_run.R`
  - `scripts/run_exdqlm_univar.R`
  - `R/unified/stages/stage_fit.R`
  - `R/unified/config.R`
  - `R/unified/manifest.R`
  - `config/unified_run.template.yaml`
  - `config/unified_runs/smoke_p3_univar_theory.yaml`
  - `repro/P3_UNIVAR_THEORY_SMOKE_20260210_234304.md`
  - `repro/UNIFIED_MULTIMODEL_WORKFLOW_TRACKER.md`
- Smoke config used:
  - `config/unified_runs/smoke_p3_univar_theory.yaml`
- Evidence paths:
  - `repro/runs/20260210_234304/run_manifest.yaml`
  - `repro/runs/20260210_234304/fit/exdqlm_univar/q=50/outputs/variables_50_exAL_synth_DISC_uni.RData`
  - `repro/runs/20260210_234304/fit/exdqlm_univar/q=50/logs/univar_theory.log`
  - `repro/runs/20260210_234304/fit/exdqlm_univar/q=50/logs/univar_theory_summary.log`
  - `repro/runs/20260210_234304/validate/write_audit/fit/fs_diff.patch`
  - `repro/P3_UNIVAR_THEORY_SMOKE_20260210_234304.md`
- Validation notes:
  - `run_manifest.yaml` has non-null `timestamps.finished_at_utc` (`2026-02-11T07:44:59Z`).
  - Fit write-audit diff is empty (`fs_diff.patch` size `0` bytes) with `enforce_from_stage=2`.
  - Legacy behavior remains default unless `implementation_mode=theory_aligned` is explicitly enabled.
- Next action:
  - Implement P4 theory-aligned NDLM VB family with forecast-window stochastic `W` handling behind `models.ndlm_main.implementation_mode=theory_aligned`.

### Progress Update 2026-02-11 07:58 UTC
- Phase: P4
- Change type: implementation+validation
- Summary: introduced theory-aligned NDLM family modules and runner behind `models.ndlm_main.implementation_mode=theory_aligned`; extended `stage_fit` NDLM dispatch by implementation mode while preserving legacy defaults and run-scoped artifact hashing.
- Files touched:
  - `R/unified/families/ndlm_main/00_constants.R`
  - `R/unified/families/ndlm_main/01_inputs.R`
  - `R/unified/families/ndlm_main/02_model_spec.R`
  - `R/unified/families/ndlm_main/03_vb_updates.R`
  - `R/unified/families/ndlm_main/04_elbo.R`
  - `R/unified/families/ndlm_main/05_fitloop.R`
  - `R/unified/families/ndlm_main/06_save_state.R`
  - `R/unified/families/ndlm_main/zz_run.R`
  - `scripts/run_ndlm_main.R`
  - `R/unified/stages/stage_fit.R`
  - `R/unified/config.R`
  - `config/unified_run.template.yaml`
  - `config/unified_runs/smoke_p4_ndlm_theory.yaml`
  - `repro/P4_NDLM_THEORY_SMOKE_20260210_235222.md`
  - `repro/UNIFIED_MULTIMODEL_WORKFLOW_TRACKER.md`
- Smoke config used:
  - `config/unified_runs/smoke_p4_ndlm_theory.yaml`
- Evidence paths:
  - `repro/runs/20260210_235222/run_manifest.yaml`
  - `repro/runs/20260210_235222/fit/ndlm_main/outputs/DISC_variables_50_NDLM_synth_DISC.RData`
  - `repro/runs/20260210_235222/fit/ndlm_main/logs/ndlm_theory.log`
  - `repro/runs/20260210_235222/fit/ndlm_main/logs/ndlm_theory_summary.log`
  - `repro/runs/20260210_235222/validate/write_audit/fit/fs_diff.patch`
  - `repro/P4_NDLM_THEORY_SMOKE_20260210_235222.md`
- Validation notes:
  - `run_manifest.yaml` has non-null `timestamps.finished_at_utc` (`2026-02-11T07:55:22Z`).
  - Fit write-audit diff is empty (`fs_diff.patch` size `0` bytes) with `enforce_from_stage=2`.
  - NDLM theory output includes legacy-compatible alias objects required by current post contracts.
  - Legacy behavior remains default unless `implementation_mode=theory_aligned` is explicitly enabled.
- Next action:
  - Close remaining P3/P4 validation gaps with post-compat structural tests and equation-to-code parity checks before default cutover.

### Progress Update 2026-02-11 17:58 UTC
- Phase: P3 + P4 validation
- Change type: implementation+validation
- Summary: added fit-stage contract checks (default OFF) for theory-aligned univariate and NDLM outputs, with machine-readable reports and manifest artifact recording; validated with dedicated P3/P4 contract-check smokes under strict fit write-audit.
- Files touched:
  - `R/unified/contract_checks.R`
  - `R/unified/stages/stage_fit.R`
  - `R/unified/config.R`
  - `scripts/unified_run.R`
  - `config/unified_run.template.yaml`
  - `config/unified_runs/smoke_p3_univar_theory_contracts.yaml`
  - `config/unified_runs/smoke_p4_ndlm_theory_contracts.yaml`
  - `repro/contracts/FAMILY_POST_OBJECT_CONTRACT_MAP_v1.md`
  - `repro/P3_UNIVAR_CONTRACTS_SMOKE_20260211_094533.md`
  - `repro/P4_NDLM_CONTRACTS_SMOKE_20260211_095407.md`
  - `repro/UNIFIED_MULTIMODEL_WORKFLOW_TRACKER.md`
- Smoke configs used:
  - `config/unified_runs/smoke_p3_univar_theory_contracts.yaml`
  - `config/unified_runs/smoke_p4_ndlm_theory_contracts.yaml`
- Evidence paths:
  - `repro/runs/20260211_094533/run_manifest.yaml`
  - `repro/runs/20260211_094533/fit/exdqlm_univar/q=50/outputs/variables_50_exAL_synth_DISC_uni.RData`
  - `repro/runs/20260211_094533/fit/contract_checks/exdqlm_univar/q=50/q50_exdqlm_univar_contract_check.json`
  - `repro/runs/20260211_094533/validate/write_audit/fit/fs_diff.patch`
  - `repro/runs/20260211_095407/run_manifest.yaml`
  - `repro/runs/20260211_095407/fit/ndlm_main/outputs/DISC_variables_50_NDLM_synth_DISC.RData`
  - `repro/runs/20260211_095407/fit/contract_checks/ndlm_main/ndlm_main_contract_check.json`
  - `repro/runs/20260211_095407/validate/write_audit/fit/fs_diff.patch`
  - `repro/P3_UNIVAR_CONTRACTS_SMOKE_20260211_094533.md`
  - `repro/P4_NDLM_CONTRACTS_SMOKE_20260211_095407.md`
- Validation notes:
  - Both smokes closed with non-null `timestamps.finished_at_utc`.
  - Contract-check reports are pass for both families and are recorded in manifest artifacts with role `contract_check`.
  - Fit write-audit diffs are empty (`0` bytes) for both smokes with `enforce_from_stage=2` and empty allowlist.
  - Default behavior is unchanged unless `fit.contract_checks.enabled=true`.
- Next action:
  - Implement equation-to-code parity audit notes plus optional runtime diagnostics invariants (shape/PSD/finite) behind diagnostics toggles before default cutover.

### Progress Update 2026-02-11 18:18 UTC
- Phase: P3 + P4 validation hardening (Commit D)
- Change type: implementation+validation
- Summary: added opt-in fit diagnostics framework (default OFF) for theory-aligned univariate and NDLM runners, including deterministic sampled PSD/symmetry/finite checks, diagnostics report artifacts, and equation-to-code audit notes; validated with a single combined theory diagnostics smoke.
- Files touched:
  - `R/unified/diagnostics.R`
  - `R/unified/stages/stage_fit.R`
  - `R/unified/config.R`
  - `scripts/unified_run.R`
  - `config/unified_run.template.yaml`
  - `config/unified_runs/smoke_pD_theory_diagnostics.yaml`
  - `repro/audits/P3_UNIVAR_THEORY_EQ_TO_CODE_v1.md`
  - `repro/audits/P4_NDLM_THEORY_EQ_TO_CODE_v1.md`
  - `repro/PD_THEORY_DIAGNOSTICS_SMOKE_20260211_101249.md`
  - `repro/UNIFIED_MULTIMODEL_WORKFLOW_TRACKER.md`
- Smoke config used:
  - `config/unified_runs/smoke_pD_theory_diagnostics.yaml`
- Evidence paths:
  - `repro/runs/20260211_101249/run_manifest.yaml`
  - `repro/runs/20260211_101249/fit/exdqlm_univar/q=50/outputs/variables_50_exAL_synth_DISC_uni.RData`
  - `repro/runs/20260211_101249/fit/ndlm_main/outputs/DISC_variables_50_NDLM_synth_DISC.RData`
  - `repro/runs/20260211_101249/fit/diagnostics/exdqlm_univar/q=50/q50_exdqlm_univar_diagnostics.json`
  - `repro/runs/20260211_101249/fit/diagnostics/ndlm_main/ndlm_main_diagnostics.json`
  - `repro/runs/20260211_101249/fit/contract_checks/exdqlm_univar/q=50/q50_exdqlm_univar_contract_check.json`
  - `repro/runs/20260211_101249/fit/contract_checks/ndlm_main/ndlm_main_contract_check.json`
  - `repro/runs/20260211_101249/validate/write_audit/fit/fs_diff.patch`
  - `repro/PD_THEORY_DIAGNOSTICS_SMOKE_20260211_101249.md`
- Validation notes:
  - `run_manifest.yaml` has non-null `timestamps.finished_at_utc` (`2026-02-11T18:16:50Z`).
  - Univariate and NDLM diagnostics reports both return `status: pass`.
  - Fit write-audit diff remains empty (`0` bytes) with `enforce_from_stage=2` and empty allowlist.
  - Defaults remain unchanged unless `fit.diagnostics.enabled=true`.
- Next action:
  - Define/execute combined P6 orchestration smoke criteria with multivariate DISC-W + theory univariate + theory NDLM under strict write-audit.

### Progress Update 2026-02-11 20:40 UTC
- Phase: P6
- Change type: validation+hardening
- Summary: executed combined strict orchestration smoke with all three families enabled (DISC-W multivar + theory univar + theory NDLM), strict run-scoped post, contract checks, diagnostics, and write-audit from fit; fixed validate false-negative by honoring explicit `--current-dir` in `compare_to_canonical.py` and re-ran validate/report on the same run manifest.
- Files touched:
  - `config/unified_runs/smoke_p6_combined_theory_orchestration.yaml`
  - `scripts/run_environmetrics_figures.R`
  - `R/environmetrics/40_figures_smoke_fast.R`
  - `R/unified/stages/stage_validate.R`
  - `repro/compare_to_canonical.py`
  - `repro/P6_COMBINED_ORCHESTRATION_SMOKE_20260211_120855.md`
  - `repro/UNIFIED_MULTIMODEL_WORKFLOW_TRACKER.md`
- Smoke config used:
  - `config/unified_runs/smoke_p6_combined_theory_orchestration.yaml`
- Evidence paths:
  - `repro/runs/20260211_120855/run_manifest.yaml`
  - `repro/runs/20260211_120855/fit/q=50/outputs/DISC_variables_50_exAL_synth_DISC.RData`
  - `repro/runs/20260211_120855/fit/exdqlm_univar/q=50/outputs/variables_50_exAL_synth_DISC_uni.RData`
  - `repro/runs/20260211_120855/fit/ndlm_main/outputs/DISC_variables_50_NDLM_synth_DISC.RData`
  - `repro/runs/20260211_120855/fit/contract_checks/exdqlm_univar/q=50/q50_exdqlm_univar_contract_check.json`
  - `repro/runs/20260211_120855/fit/contract_checks/ndlm_main/ndlm_main_contract_check.json`
  - `repro/runs/20260211_120855/fit/diagnostics/exdqlm_univar/q=50/q50_exdqlm_univar_diagnostics.json`
  - `repro/runs/20260211_120855/fit/diagnostics/ndlm_main/ndlm_main_diagnostics.json`
  - `repro/runs/20260211_120855/post/logs/post_runner.log`
  - `repro/runs/20260211_120855/post/outputs/20260211_120855/All_ELBOS_DISC.png`
  - `repro/runs/20260211_120855/post/outputs/20260211_120855/SMOKE_OBSERVED_SERIES_DISC.png`
  - `repro/runs/20260211_120855/validate/compare_report.json`
  - `repro/runs/20260211_120855/validate/write_audit/fit/fs_diff.patch`
  - `repro/runs/20260211_120855/validate/write_audit/post/fs_diff.patch`
  - `repro/runs/20260211_120855/validate/write_audit/validate/fs_diff.patch`
  - `repro/runs/20260211_120855/validate/write_audit/report/fs_diff.patch`
  - `repro/runs/20260211_120855/report/summary.md`
  - `repro/runs/20260211_120855/report/summary.json`
  - `repro/P6_COMBINED_ORCHESTRATION_SMOKE_20260211_120855.md`
- Validation notes:
  - `run_manifest.yaml` has non-null `timestamps.finished_at_utc` (`2026-02-11T20:36:55Z`).
  - `run_manifest.yaml` has `validation.status: pass`.
  - Compare metrics show `matched=4, missing=0, extra=0, mismatched=0`.
  - Fit/post/validate/report write-audit diffs are all empty (`0` bytes) with `enforce_from_stage=2` and empty allowlist.
  - Root-load grep over post logs for `/data/muscat_data/jaguir26/project1_ucsc_phd/(variables_|DISC_variables_)` returned no matches.
- Next action:
  - Continue P6 hardening with scheduler/isolation policy checks across repeated runs, then move to P7 family-aware validator/report contracts.

### Progress Update 2026-02-11 21:48 UTC
- Phase: P7A
- Change type: implementation+validation
- Summary: added smoke-aware validation profile support while preserving production strict defaults, hardened `compare_to_canonical.py` path precedence for explicit CLI dirs, and added regression tests for run_id underscore/path resolution bugs; validated with one end-to-end smoke run including fit+post+validate+report.
- Files touched:
  - `R/unified/config.R`
  - `R/unified/stages/stage_validate.R`
  - `config/unified_run.template.yaml`
  - `config/unified_runs/smoke_p7_family_validate.yaml`
  - `repro/compare_to_canonical.py`
  - `repro/tools/validate_run.sh`
  - `repro/tests/test_compare_to_canonical.py`
  - `repro/P7A_FAMILY_VALIDATE_SMOKE_20260211_131304.md`
  - `repro/UNIFIED_MULTIMODEL_WORKFLOW_TRACKER.md`
- Smoke config used:
  - `config/unified_runs/smoke_p7_family_validate.yaml`
- Evidence paths:
  - `repro/runs/20260211_131304/run_manifest.yaml`
  - `repro/runs/20260211_131304/validate/compare_report.json`
  - `repro/runs/20260211_131304/validate/write_audit/fit/fs_diff.patch`
  - `repro/runs/20260211_131304/validate/write_audit/post/fs_diff.patch`
  - `repro/runs/20260211_131304/validate/write_audit/validate/fs_diff.patch`
  - `repro/runs/20260211_131304/validate/write_audit/report/fs_diff.patch`
  - `repro/runs/20260211_131304/post/logs/post_runner.log`
  - `repro/runs/20260211_131304/post/outputs/20260211_131304/All_ELBOS_DISC.png`
  - `repro/runs/20260211_131304/post/outputs/20260211_131304/SMOKE_OBSERVED_SERIES_DISC.png`
  - `repro/P7A_FAMILY_VALIDATE_SMOKE_20260211_131304.md`
- Validation notes:
  - `run_manifest.yaml` has non-null `timestamps.finished_at_utc` (`2026-02-11T21:40:35Z`).
  - `validation.status` is `pass` and compare metrics are `matched=4, missing=0, extra=0, mismatched=0`.
  - `bash repro/tools/validate_run.sh 20260211_131304 --profile smoke` returns `RESULT=PASS`.
  - All write-audit `fs_diff.patch` files for fit/post/validate/report are `0` bytes.
  - Post root-load grep for `/data/muscat_data/jaguir26/project1_ucsc_phd/(variables_|DISC_variables_)` returned no matches.
- Next action:
  - Move to P7B: extend validator/report contracts with per-family required-artifact assertions in production profile while keeping smoke profile lightweight and explicit.

### Progress Update 2026-02-11 23:20 UTC
- Phase: P7B
- Change type: implementation+validation
- Summary: made production validator family-aware from `resolved_config.yaml` (per-family fit artifacts + optional contract/diagnostics report enforcement), added deterministic `validate_run.sh` regression tests with `--exit-nonzero`, and added additive `report.families` metadata in `summary.json`.
- Files touched:
  - `repro/tools/validate_run.sh`
  - `repro/tests/test_validate_run.py`
  - `R/unified/stages/stage_report.R`
  - `config/unified_runs/smoke_p7b_production_validate.yaml`
  - `repro/P7B_PRODUCTION_VALIDATE_SMOKE_20260211_151207.md`
  - `repro/UNIFIED_MULTIMODEL_WORKFLOW_TRACKER.md`
- Smoke config used:
  - `config/unified_runs/smoke_p7b_production_validate.yaml`
- Evidence paths:
  - `repro/runs/20260211_151207/run_manifest.yaml`
  - `repro/runs/20260211_151207/resolved_config.yaml`
  - `repro/runs/20260211_151207/validate/compare_report.json`
  - `repro/runs/20260211_151207/validate/write_audit/fit/fs_diff.patch`
  - `repro/runs/20260211_151207/validate/write_audit/post/fs_diff.patch`
  - `repro/runs/20260211_151207/validate/write_audit/validate/fs_diff.patch`
  - `repro/runs/20260211_151207/validate/write_audit/report/fs_diff.patch`
  - `repro/runs/20260211_151207/report/summary.json`
  - `repro/runs/20260211_151207/post/outputs/20260211_151207/post_smoke_marker.txt`
  - `repro/P7B_PRODUCTION_VALIDATE_SMOKE_20260211_151207.md`
- Validation notes:
  - `run_manifest.yaml` has non-null `timestamps.finished_at_utc` (`2026-02-11T23:16:03Z`) and `validation.status: pass`.
  - `compare_report.json` metrics are `matched=1, missing=0, extra=0, mismatched=0`.
  - `validate_run.sh` passes in production profile with and without `--exit-nonzero`.
  - All write-audit `fs_diff.patch` files under `validate/write_audit/{fit,post,validate,report}` are `0` bytes.
  - `report/summary.json` now contains additive `report.families` metadata for multivar/univar/ndlm.
- Next action:
  - Run a production-profile family-enabled validation pass once runtime budget is allocated (7-quantile multivar and optional univar/ndlm), reusing P7B validator gates now enforced by config-driven family toggles.

### Progress Update 2026-02-12 00:09 UTC
- Phase: P7B
- Change type: hardening+tests
- Summary: hardened validator/report robustness without changing model semantics by (1) making stage-report univar quantile extraction robust to `variables_5_...` naming with integer-scaled quantile outputs, (2) extending NDLM validator detection to accept legacy and neutral filenames, and (3) improving resolved-config YAML parse failures with explicit PyYAML/import guidance.
- Files touched:
  - `R/unified/stages/stage_report.R`
  - `repro/tools/validate_run.sh`
  - `repro/tests/test_validate_run.py`
  - `repro/UNIFIED_MULTIMODEL_WORKFLOW_TRACKER.md`
- Validation checks run:
  - `python3 -m unittest discover -s repro/tests -p 'test_*.py'`
  - `bash -n repro/tools/validate_run.sh`
  - `Rscript -e "parse(file='R/unified/stages/stage_report.R'); cat('R_PARSE_OK\\n')"`
- Validation notes:
  - Added regression coverage for NDLM neutral output name acceptance (`ndlm_main_state.RData`).
  - Added regression coverage for stage-report univar quantile parsing (`q=05` with `variables_5_...`, directory quantile preferred).
  - Production-vs-smoke quantile rule is now explicitly surfaced in validator output (`quantile_rule=*`).
- Next action:
  - Execute the deferred long-budget production-profile family-enabled run to collect full runtime P7B evidence against the hardened validator.

### Progress Update 2026-02-12 07:20 UTC
- Phase: P7B (ops hardening follow-up)
- Change type: implementation+validation
- Summary: added storage/I/O guardrails to fail fast before long fits, introduced atomic model-state save for DISC-W artifact writes to prevent 0-byte outputs on failure, and added a fast debug-small workflow + safe cleanup tooling.
- Files touched:
  - `R/unified/preflight.R`
  - `scripts/unified_run.R`
  - `R/unified/config.R`
  - `R/unified/stages/stage_fit.R`
  - `R/disc_w/05_save_state.R`
  - `scripts/run_DISC_Optimal_Synth_Ranges_W.R`
  - `R/unified/stages/stage_data_prep_shared.R`
  - `config/unified_run.template.yaml`
  - `config/unified_runs/debug_p7b_small.yaml`
  - `repro/tests/test_preflight_io.py`
  - `repro/tools/cleanup_runs.sh`
  - `repro/docs/storage_root_cause.md`
  - `repro/docs/debug_small_workflow.md`
  - `repro/UNIFIED_MULTIMODEL_WORKFLOW_TRACKER.md`
- Evidence paths:
  - `repro/docs/storage_root_cause.md`
  - `repro/runs/20260211_231702/run_manifest.yaml`
  - `repro/runs/20260211_231702/inputs/shared/data_start_filter_summary.txt`
  - `config/unified_runs/debug_p7b_small.yaml`
  - `repro/docs/debug_small_workflow.md`
- Validation checks run:
  - `python3 -m unittest discover -s repro/tests -p 'test_*.py'`
  - `bash -n repro/tools/cleanup_runs.sh`
  - `bash -n repro/tools/validate_run.sh`
  - `Rscript -e "parse(file='R/unified/preflight.R'); parse(file='R/unified/stages/stage_data_prep_shared.R'); parse(file='R/unified/stages/stage_fit.R'); parse(file='R/disc_w/05_save_state.R'); parse(file='scripts/unified_run.R'); parse(file='scripts/run_DISC_Optimal_Synth_Ranges_W.R'); cat('R_PARSE_OK\\n')"`
  - `Rscript --vanilla scripts/unified_run.R --config config/unified_runs/debug_p7b_small.yaml` (run_id `20260211_231702`)
- Validation notes:
  - Debug-small run closed successfully with non-null `timestamps.finished_at_utc` (`2026-02-12T07:18:11Z`).
  - New storage preflight checks are config-gated (`run.io.enabled` default `false`) to avoid changing default behavior.
  - Atomic save wrapper now enforces non-empty final artifacts and cleans up temp files on failure.
- Next action:
  - Allocate disk headroom via safe cleanup workflow, then execute one production-profile family-enabled proof run using the hardened preflight and atomic save guardrails.

### Progress Update 2026-02-12 20:20 UTC
- Phase: P7B (production proof run)
- Change type: operations+validation
- Summary: added production-proof run config plus storage operations playbook, reclaimed `/data` headroom using policy-driven cleanup reports, and executed exactly one production-profile proof run; run failed at univariate fit preflight after multivar q=05/50/95 completed because free space dropped below configured `run.io.min_free_gb=100`.
- Files touched:
  - `repro/tools/cleanup_runs.sh`
  - `config/unified_runs/production_proof_p7b_family.yaml`
  - `repro/docs/storage_ops_playbook.md`
  - `repro/P7B_PRODUCTION_PROOF_RUN_20260212_112137.md`
  - `repro/UNIFIED_MULTIMODEL_WORKFLOW_TRACKER.md`
- Config used:
  - `config/unified_runs/production_proof_p7b_family.yaml`
- Evidence paths:
  - `repro/reports/cleanup_runs/cleanup_20260212_201240.log` (dry-run)
  - `repro/reports/cleanup_runs/cleanup_20260212_201249.log` (apply)
  - `repro/runs/20260212_112137/resolved_config.yaml`
  - `repro/runs/20260212_112137/run_manifest.yaml`
  - `repro/runs/20260212_112137/fit/q=05/outputs/DISC_variables_5_exAL_synth_DISC.RData`
  - `repro/runs/20260212_112137/fit/q=50/outputs/DISC_variables_50_exAL_synth_DISC.RData`
  - `repro/runs/20260212_112137/fit/q=95/outputs/DISC_variables_95_exAL_synth_DISC.RData`
  - `repro/P7B_PRODUCTION_PROOF_RUN_20260212_112137.md`
- Validation notes:
  - Single proof run command executed: `Rscript --vanilla scripts/unified_run.R --config config/unified_runs/production_proof_p7b_family.yaml`.
  - Run did not close: `timestamps.finished_at_utc: null`, `validation.status: pending`.
  - Failure was fail-fast I/O preflight (not model semantics): univar q=05 launch blocked at `free_gb: 94.10` vs threshold `100.00`.
  - `/data` headroom improved before run via cleanup apply (`~98G -> ~104G`), but full multivar footprint still dropped free space below threshold before theory families launched.
- Next action:
  - For the next proof attempt, either reclaim additional `/data` headroom to sustain `>=100 GB` throughout fit, or lower proof-config `run.io.min_free_gb` to a measured-safe threshold and rerun once with a new `RUN_ID`.

### Progress Update 2026-02-12 21:59 UTC
- Phase: P7B (ops resilience follow-up)
- Change type: implementation+tests+docs
- Summary: added backward-compatible scoped I/O preflight policy (`legacy` / `fit_start_and_continue` / `fit_start_only`) with run-scoped preflight JSON evidence + fit-stage preflight log summaries; updated production-proof config to use split start/continue thresholds; extended cleanup policy tooling with `--thin-failed`, root `.RData` inventory/prune flags, and optional baseline thinning hook, all dry-run-first.
- Files touched:
  - `R/unified/preflight.R`
  - `R/unified/config.R`
  - `R/unified/stages/stage_fit.R`
  - `scripts/unified_run.R`
  - `config/unified_run.template.yaml`
  - `config/unified_runs/production_proof_p7b_family.yaml`
  - `repro/tools/cleanup_policy.py`
  - `repro/tests/test_preflight_io.py`
  - `repro/tests/test_cleanup_policy.py`
  - `repro/docs/storage_root_cause.md`
  - `repro/docs/storage_ops_playbook.md`
  - `repro/docs/STATUS_SNAPSHOT_FOR_CLEANUP_AND_FORWARD.md`
  - `repro/UNIFIED_MULTIMODEL_WORKFLOW_TRACKER.md`
- Validation checks run:
  - `Rscript -e "parse(file='R/unified/preflight.R'); parse(file='R/unified/config.R'); parse(file='R/unified/stages/stage_fit.R'); parse(file='scripts/unified_run.R'); cat('R_PARSE_OK\\n')"`
  - `python3 -m py_compile repro/tools/cleanup_policy.py repro/tests/test_cleanup_policy.py repro/tests/test_preflight_io.py`
  - `python3 -m unittest repro.tests.test_preflight_io repro.tests.test_cleanup_policy`
- Validation notes:
  - Existing configs remain backward compatible under `run.io.preflight_scope: legacy` (default).
  - Preflight evidence now lands under `repro/runs/<RUN_ID>/preflight/*.json` and `repro/runs/<RUN_ID>/fit/logs/preflight.log`.
  - Cleanup dry-run plans now include per-target sizes and blocked thin-failed candidates for protected runs.
- Next action:
  - Execute dry-run cleanup planning with `--thin-failed` and inventory flags, then rerun one production-proof attempt after confirmed headroom.

### Progress Update 2026-02-12 22:26 UTC
- Phase: P7B (storage operations)
- Change type: operations+validation
- Summary: completed dry-run-first cleanup planning and apply passes using `repro/tools/cleanup_runs.sh` with logs under `repro/reports/cleanup_runs`; no deletions were applied because all current `repro/runs/*` candidates are protected by YAML/safety guards. Added explicit storage retention policy doc and captured disk inventory + before/after stats.
- Files touched:
  - `repro/reports/disk_inventory/disk_inventory_20260212_222348.md`
  - `repro/reports/cleanup_runs/before_after_20260212_222348.txt`
  - `repro/reports/cleanup_runs/summary_20260212_222348.md`
  - `repro/reports/cleanup_runs/20260212_222510_dryrun.log`
  - `repro/reports/cleanup_runs/20260212_222510_dryrun.json`
  - `repro/reports/cleanup_runs/20260212_222513_dryrun.log`
  - `repro/reports/cleanup_runs/20260212_222513_dryrun.json`
  - `repro/reports/cleanup_runs/20260212_222519_dryrun.log`
  - `repro/reports/cleanup_runs/20260212_222519_dryrun.json`
  - `repro/reports/cleanup_runs/20260212_222526_dryrun.log`
  - `repro/reports/cleanup_runs/20260212_222526_dryrun.json`
  - `repro/reports/cleanup_runs/20260212_222534_apply.log`
  - `repro/reports/cleanup_runs/20260212_222534_apply.json`
  - `repro/reports/cleanup_runs/20260212_222539_apply.log`
  - `repro/reports/cleanup_runs/20260212_222539_apply.json`
  - `repro/reports/cleanup_runs/20260212_222543_apply.log`
  - `repro/reports/cleanup_runs/20260212_222543_apply.json`
  - `repro/reports/cleanup_runs/validate_run_20260211_151207_20260212_222348.txt`
  - `repro/docs/storage_retention_policy.md`
  - `repro/UNIFIED_MULTIMODEL_WORKFLOW_TRACKER.md`
- Evidence paths:
  - `repro/reports/disk_inventory/disk_inventory_20260212_222348.md`
  - `repro/reports/cleanup_runs/summary_20260212_222348.md`
  - `repro/reports/cleanup_runs/before_after_20260212_222348.txt`
  - `repro/reports/cleanup_runs/validate_run_20260211_151207_20260212_222348.txt`
- Validation notes:
  - `/data` before cleanup: `95G` free (`90%` used); after cleanup: `95G` free (`90%` used).
  - Thin-failed blocked candidate remained protected: `repro/runs/20260212_112137` (`~21.28GB`) with reasons `protected_runs_yaml`, `modified_within_safety_window`, `in_progress_manifest`.
  - Root `.RData` inventory found 15 candidates; no prune executed in this pass.
  - Baseline archive (`repro/baseline_runs`) remained untouched (no baseline flags enabled).
  - Lightweight integrity check passed: `bash repro/tools/validate_run.sh 20260211_151207 --profile smoke` -> `RESULT=PASS`.
  - Protected reference runs currently present under `repro/runs`: `20260211_120855`, `20260211_131304`, `20260211_151207`, `20260212_112137`.
- Next action:
  - To reclaim substantial space, approve either (1) targeted unprotect/thinning of specific failed runs, or (2) baseline thinning allowlist usage, and optionally (3) explicit root `.RData` prune under strict run-scoped post policy.

### Progress Update 2026-02-13 00:39 UTC
- Phase: P7B (production proof run recovery)
- Change type: operations+validation
- Summary: quarantined and safely removed failed run `20260212_112137` after manifest closure-to-fail + unprotect, reclaimed `~21.37GB`, then executed exactly one new production-proof family-enabled run `prod_proof_p7b_20260212_225100` to completion with non-null manifest closure and `validation.status: pass`; added new successful proof run to protected set.
- Files touched:
  - `repro/protected_runs.yaml`
  - `repro/UNIFIED_MULTIMODEL_WORKFLOW_TRACKER.md`
  - run-scoped operational artifacts only under `repro/quarantine/**`, `repro/reports/cleanup_runs/**`, and `repro/runs/prod_proof_p7b_20260212_225100/**`
- Evidence paths:
  - `repro/quarantine/failed_runs/20260212_112137/QUARANTINE_INDEX.md`
  - `repro/reports/cleanup_runs/before_after_20260212_224902.txt`
  - `repro/reports/cleanup_runs/20260212_225013_dryrun.log`
  - `repro/reports/cleanup_runs/20260212_225013_dryrun.json`
  - `repro/reports/cleanup_runs/20260212_225025_apply.log`
  - `repro/reports/cleanup_runs/20260212_225025_apply.json`
  - `repro/reports/cleanup_runs/summary_20260212_224902_failed_run_cleanup.md`
  - `repro/runs/prod_proof_p7b_20260212_225100/run_manifest.yaml`
  - `repro/runs/prod_proof_p7b_20260212_225100/validate/compare_report.json`
  - `repro/runs/prod_proof_p7b_20260212_225100/report/summary.md`
  - `repro/runs/prod_proof_p7b_20260212_225100/report/summary.json`
  - `repro/runs/prod_proof_p7b_20260212_225100/validate/write_audit/fit/fs_diff.patch`
  - `repro/runs/prod_proof_p7b_20260212_225100/validate/write_audit/post/fs_diff.patch`
  - `repro/runs/prod_proof_p7b_20260212_225100/validate/write_audit/validate/fs_diff.patch`
  - `repro/runs/prod_proof_p7b_20260212_225100/validate/write_audit/report/fs_diff.patch`
- Validation notes:
  - Space reclaim gate met: `/data` free increased from `73G` to `95G` (`+22G` approx) during failed-run cleanup apply.
  - Exactly one new production-proof run command executed for this attempt:
    - `Rscript --vanilla scripts/unified_run.R --config config/unified_runs/production_proof_p7b_family.yaml`
  - New proof run closed successfully:
    - `timestamps.finished_at_utc: 2026-02-13T00:38:11Z`
    - `validation.status: pass`
  - Write-audit diffs for `fit/post/validate/report` are all `0` bytes.
  - `bash repro/tools/validate_run.sh prod_proof_p7b_20260212_225100 --profile production --exit-nonzero` currently returns FAIL because the validator production profile enforces canonical 7 quantiles while this proof config intentionally runs quantiles `5,50,95`; run-manifest validation still passes.
- Next action:
  - Decide whether production proof should continue using representative quantile subset `[0.05,0.50,0.95]` (and adjust validator profile gate), or move proof config to canonical 7-quantile production expectations before next run.

### Progress Update 2026-02-13 01:05 UTC
- Phase: P7B (validator policy alignment)
- Change type: tooling+tests
- Summary: resolved production-vs-proof validator mismatch by adding `production_proof` profile to `repro/tools/validate_run.sh`; `production` remains canonical 7-quantile strict and unchanged, while `production_proof` enforces quantiles declared in run `resolved_config.yaml` with all other production-like gates preserved.
- Files touched:
  - `repro/tools/validate_run.sh`
  - `repro/tests/test_validate_run.py`
  - `repro/UNIFIED_MULTIMODEL_WORKFLOW_TRACKER.md`
- Validation notes:
  - `production_proof` is intended for bounded proof runs (e.g., q=`[0.05,0.50,0.95]`) and uses `quantile_rule=config_declared_quantiles_enforced`.
  - `production` still reports `quantile_rule=canonical_7_quantiles_enforced` and fails when only 3 quantiles are present.
- Next action:
  - Keep `production` for full canonical runs; use `production_proof` only for storage/time-bounded proof runs.

### Progress Update 2026-02-13 01:20 UTC
- Phase: P7B (validator auto-selection hardening)
- Change type: tooling+tests
- Summary: added deterministic `--profile auto` resolution in `repro/tools/validate_run.sh` with precedence `run_manifest.validation.validator_profile` -> `resolved_config.validation.profile` -> `production` fallback; production strictness remains unchanged.
- Files touched:
  - `repro/tools/validate_run.sh`
  - `repro/tests/test_validate_run.py`
  - `R/unified/stages/stage_validate.R`
  - `repro/UNIFIED_MULTIMODEL_WORKFLOW_TRACKER.md`
- Validation notes:
  - `--profile auto` now emits `profile_resolved=<...>` and `profile_source=manifest|resolved_config|default` for auditability.
  - Canonical command for run-scoped validation is now:
    - `bash repro/tools/validate_run.sh <RUN_ID> --profile auto --exit-nonzero`
  - For historical proof run `prod_proof_p7b_20260212_225100`, `run_manifest.yaml` was backfilled with `validation.validator_profile: production_proof` so `auto` resolves deterministically to proof profile.

### Progress Update 2026-02-13 02:05 UTC
- Phase: P7B (validator metadata autopopulation)
- Change type: tooling+tests
- Summary: removed forward need for manual manifest backfill by emitting `validation.validator_profile` at manifest initialization (`unified_manifest_init`) from `cfg$validation$profile`; this is metadata-only and preserves existing validation gates/semantics.
- Files touched:
  - `R/unified/manifest.R`
  - `repro/tests/test_validate_run.py`
  - `repro/UNIFIED_MULTIMODEL_WORKFLOW_TRACKER.md`
- Validation notes:
  - New runs now carry `validation.validator_profile` before stage execution begins, so `bash repro/tools/validate_run.sh <RUN_ID> --profile auto --exit-nonzero` resolves deterministically without post-hoc manifest edits.
  - Backward compatibility remains: old runs lacking this field still resolve via `resolved_config.validation.profile` then default `production`.

### Progress Update 2026-02-13 02:35 UTC
- Phase: P7C (validator policy/evidence closure)
- Change type: tooling+docs+validation
- Summary: closed profile-policy ambiguity for proof vs canonical validation by documenting canonical validator commands, making proof config explicitly `validation.profile: production_proof`, and adding a regression test that `--profile auto` prefers manifest metadata over conflicting resolved-config profile.
- Files touched:
  - `config/unified_runs/production_proof_p7b_family.yaml`
  - `repro/tests/test_validate_run.py`
  - `repro/UNIFIED_WORKFLOW_README.md`
  - `repro/UNIFIED_MULTIMODEL_WORKFLOW_TRACKER.md`
- Evidence paths:
  - `repro/reports/validator/prod_proof_p7b_20260212_225100_auto.txt`
  - `repro/reports/validator/prod_proof_p7b_20260212_225100_production.txt`
  - `repro/reports/validator/prod_proof_p7b_20260212_225100_production_proof.txt`
- Validation notes:
  - `--profile auto` on proof run resolves from manifest and passes (`profile_source=manifest`, `RESULT=PASS`).
  - `--profile production` on the same proof run fails by design (`quantile_rule=canonical_7_quantiles_enforced`, `RESULT=FAIL`).
  - `--profile production_proof` on the same proof run passes (`quantile_rule=config_declared_quantiles_enforced`, `RESULT=PASS`).

### Progress Update 2026-02-13 07:56 UTC
- Phase: P7 (family contract metadata hardening)
- Change type: tooling+tests
- Summary: closed Open Q11.1 #1 by hardening manifest family metadata defaults: multivar remains authoritative by default, univar/NDLM default to non-authoritative unless explicitly set in config, and implementation modes are now emitted for all families from config with safe fallback.
- Files touched:
  - `R/unified/manifest.R`
  - `repro/tests/test_manifest_metadata.py`
  - `repro/UNIFIED_MULTIMODEL_WORKFLOW_TRACKER.md`
- Validation checks run:
  - `bash -n repro/tools/validate_run.sh`
  - `python3 -m unittest discover -s repro/tests -p 'test_*.py'`
  - `Rscript -e "parse(file='scripts/unified_run.R'); cat('R_PARSE_OK\n')"`
- Validation notes:
  - Added deterministic unit coverage for family authoritative defaults and explicit override behavior at manifest init.
  - Existing manifests remain backward compatible because `families` remains additive metadata.
- Next action:
  - Close Open Q11.1 #2 by codifying NDLM minimal artifact schema in contract docs and validator tests.

### Progress Update 2026-02-13 07:58 UTC
- Phase: P7 (NDLM artifact contract closure)
- Change type: tooling+tests+contracts
- Summary: closed Open Q11.1 #2 by documenting validator-minimal NDLM artifact schema in contract docs and hardening validator tests for required NDLM pass/fail behavior when `models.run_ndlm_main=true`.
- Files touched:
  - `repro/contracts/FAMILY_POST_OBJECT_CONTRACT_MAP_v1.md`
  - `repro/tools/validate_run.sh`
  - `repro/tests/test_validate_run.py`
  - `repro/UNIFIED_MULTIMODEL_WORKFLOW_TRACKER.md`
- Validation notes:
  - NDLM accepted output names remain centralized in `validate_run.sh` and are now used as the sole finder expression source.
  - Added deterministic tests for:
    - `production_proof` PASS with accepted `ndlm_main_*.RData`.
    - `production_proof` FAIL when NDLM is required but no accepted output exists.
- Next action:
  - Close Open Q11.1 #3 by adding additive per-stage status metadata in manifest v1-compatible shape.

### Progress Update 2026-02-13 08:02 UTC
- Phase: P7 (manifest stage status closure)
- Change type: tooling+tests
- Summary: closed Open Q11.1 #3 by adding additive per-stage status metadata under `manifest.stages` (`status`, `started_at_utc`, `finished_at_utc`, `log_path`) and wiring unified runner to mark `skip/pass/fail` with best-effort manifest write on stage errors.
- Files touched:
  - `R/unified/manifest.R`
  - `scripts/unified_run.R`
  - `repro/tests/test_manifest_stage_status.py`
  - `repro/UNIFIED_MULTIMODEL_WORKFLOW_TRACKER.md`
- Validation notes:
  - Stage status metadata is v1-compatible and additive; existing consumers continue using legacy fields unchanged.
  - New unit coverage validates stage helper transitions for `skip`, `pass`, and `fail` semantics.
- Next action:
  - Close Open Q11.1 #4 with explicit write-audit policy guidance (default unchanged, migration profile documented).

### Progress Update 2026-02-13 08:04 UTC
- Phase: P7 (write-audit policy closure)
- Change type: docs+config-policy
- Summary: closed Open Q11.1 #4 without changing defaults by documenting explicit write-audit policy (`enforce_from_stage=4` production default, `=2` migration/proof recommendation) and adding a minimal overlay config for fit-stage audit enforcement.
- Files touched:
  - `config/unified_run.template.yaml`
  - `config/unified_runs/migration_write_audit_from_fit.yaml`
  - `repro/UNIFIED_WORKFLOW_README.md`
  - `repro/UNIFIED_MULTIMODEL_WORKFLOW_TRACKER.md`
- Validation notes:
  - No runtime behavior changed; defaults remain production-stable.
  - Migration/proof audit profile is now explicitly reproducible via committed overlay config.
- Next action:
  - Close Open Q11.1 #5 by hardening run-scoped forecats snapshot usage evidence across fit/post/validator outputs.

### Progress Update 2026-02-13 08:08 UTC
- Phase: P7 (forecats snapshot contract closure)
- Change type: tooling+tests
- Summary: closed Open Q11.1 #5 by hardening snapshot usage evidence for fit/post and validator outputs: shared input validation now logs source-map provenance into stage logs, validator output now reports shared/snapshot source-map paths, and regression coverage simulates `forecats` snapshot flow with manifest `input_snapshot` artifacts and snapshot-origin routing in shared source maps.
- Files touched:
  - `R/unified/inputs_shared_validate.R`
  - `repro/tools/validate_run.sh`
  - `repro/tests/test_validate_run.py`
  - `repro/tests/test_forecats_snapshot_contract.py`
  - `repro/UNIFIED_MULTIMODEL_WORKFLOW_TRACKER.md`
- Validation notes:
  - `fit/logs/shared_input_source_map.log` and `post/logs/shared_input_source_map.log` now capture source-map paths when shared inputs are validated.
  - Validator output now prints `shared_source_map_path`, `snapshot_source_map_path`, and corresponding existence flags for auditability.
  - Snapshot regression test confirms manifest `role=input_snapshot` entries and `inputs/shared/source_map.txt` origin flags (`source.glofas_origin=snapshot`, `source.nws_origin=snapshot`).
- Next action:
  - With Open Q11.1 items closed, continue P7 family-aware validator/report hardening toward P8 cutover planning.

### Progress Update 2026-02-13 08:24 UTC
- Phase: P7 (validator robustness bugfix)
- Change type: tooling+tests
- Summary: fixed validator robustness around NDLM artifact discovery and failure reporting by guarding NDLM output-dir lookup and preventing early termination when `fit/` is absent; missing NDLM outputs now fail cleanly with `RESULT=FAIL` diagnostics instead of blank output.
- Files touched:
  - `repro/tools/validate_run.sh`
  - `repro/tests/test_validate_run.py`
  - `repro/UNIFIED_MULTIMODEL_WORKFLOW_TRACKER.md`
- Validation notes:
  - NDLM accepted-name finder now runs only when `fit/ndlm_main/outputs` exists.
  - Added deterministic regression test for missing NDLM outputs directory under `production_proof`.
- Next action:
  - Apply runner-level skip-status bugfix to ensure disabled stages always record `stages.<name>.status=skip` in manifest.

### Progress Update 2026-02-13 08:25 UTC
- Phase: P7 (runner skip-status bugfix)
- Change type: tooling+tests
- Summary: hardened unified runner stage loop to use a single `enabled_flag` branch for disabled stages and added a runner-level regression test that executes a no-stage run and verifies all stage statuses are written as `skip` in `run_manifest.yaml`.
- Files touched:
  - `scripts/unified_run.R`
  - `repro/tests/test_unified_run_stage_skip.py`
  - `repro/UNIFIED_MULTIMODEL_WORKFLOW_TRACKER.md`
- Validation notes:
  - Disabled stages now deterministically emit `manifest.stages.<name>.status=skip` with manifest writes in-loop.
  - Regression test verifies skip-status persistence on real runner execution path (no model stages enabled).
- Next action:
  - Implement build-mode snapshot parity evidence + validator enforcement without heavy runs.

### Progress Update 2026-02-13 08:43 UTC
- Phase: P7 (forecats build-snapshot parity enforcement)
- Change type: tooling+tests
- Summary: hardened validator-side snapshot parity enforcement for production/production_proof profiles when `inputs.forecats.mode=build`, `inputs.forecats.snapshot.enabled=true`, and `inputs.shared.prefer_forecats_snapshot=true`; added deterministic tests for both fail/pass evidence paths and a build-mode snapshot regression that stubs the forecats pipeline command while exercising real stage snapshot + shared-input resolution logic.
- Files touched:
  - `repro/tools/validate_run.sh`
  - `repro/tests/test_validate_run.py`
  - `repro/tests/test_forecats_snapshot_contract.py`
  - `repro/UNIFIED_MULTIMODEL_WORKFLOW_TRACKER.md`
- Validation notes:
  - Validator now emits and gates on snapshot provenance evidence lines (`require_snapshot_evidence`, `snapshot_check.*`, `shared_source_*`, `snapshot_source_mode`) in production/proof profiles when build-mode parity is required by config.
  - New regression coverage verifies:
    - production_proof FAIL when build-mode snapshot evidence is required but absent,
    - production_proof PASS when `source_map.txt` + `snapshot_source_map.txt` prove snapshot routing,
    - build-mode forecats snapshot flow records `mode=build`, snapshot aliases, and snapshot-origin shared source map entries without running heavy/network forecats pipeline work.
- Next action:
  - Clean tracker duplication and keep a single authoritative Open/Resolved section.

### Progress Update 2026-02-13 08:55 UTC
- Phase: P7 (tracker hygiene)
- Change type: docs
- Summary: cleaned tracker state to keep a single authoritative Open/Resolved block in §11, clarified that appendix discovery ambiguities are historical context (not active open questions), and updated forecats snapshot resolved-default language to match enforced validator gates.
- Files touched:
  - `repro/UNIFIED_MULTIMODEL_WORKFLOW_TRACKER.md`
- Validation notes:
  - Tracker now has one authoritative `## 11) Open Questions / Resolved Defaults` section with `11.1 Open = None currently tracked`.
  - Forecats snapshot policy text now reflects production/proof enforcement conditions introduced in validator tooling.
- Next action:
  - Continue P7 family-aware validator/report hardening toward P8 cutover planning.

### Progress Update 2026-02-13 09:18 UTC
- Phase: P7B (validator auto-selection hardening)
- Change type: tooling+tests
- Summary: hardened `validate_run.sh --profile auto` to use conservative resolved-config-driven profile selection with explicit diagnostics (`profile_requested`, `profile_effective`, `profile_reason`) and canonical quantile set comparison after normalization. Auto now fails cleanly with `RESULT=FAIL` for malformed `resolved_config.yaml` or unknown `validation.profile` values while preserving strict production gates.
- Files touched:
  - `repro/tools/validate_run.sh`
  - `repro/tests/test_validate_run.py`
  - `repro/UNIFIED_MULTIMODEL_WORKFLOW_TRACKER.md`
- Validation checks run:
  - `bash -n repro/tools/validate_run.sh`
  - `Rscript -e "parse(file='scripts/unified_run.R'); cat('R_PARSE_OK\n')"`
  - `python3 -m unittest discover -s repro/tests -p 'test_*.py'`
- Validation notes:
  - `auto` selects `production_proof` when quantile set is non-canonical and no explicit validation profile is declared.
  - `auto` selects `production` for canonical 7 quantiles and honors explicit `validation.profile` when declared.
  - Unknown `validation.profile` under `auto` now emits deterministic fail output with allowed-profile guidance.

### Progress Update 2026-02-13 21:21 UTC
- Phase: P7B (validator auto-selection hardening)
- Change type: tooling+tests
- Summary: closed remaining `--profile auto` gaps in `validate_run.sh` by removing smoke-flag inference, accepting explicit `validation.profile: auto` as infer-continue, requiring `fit.quantiles` for auto inference, and switching canonical auto inference to normalized quantiles `[0.01,0.05,0.10,0.50,0.90,0.95,0.99]` using single-pass Python parsing. Added regression coverage for canonical mixed-type quantiles, no-smoke inference behavior, and missing-quantiles fail path.
- Files touched:
  - `repro/tools/validate_run.sh`
  - `repro/tests/test_validate_run.py`
  - `repro/UNIFIED_MULTIMODEL_WORKFLOW_TRACKER.md`
- Validation checks run:
  - `bash -n repro/tools/validate_run.sh`
  - `python3 -m unittest discover -s repro/tests -p 'test_*.py'`
  - `Rscript -e "parse(file='scripts/unified_run.R'); cat('R_PARSE_OK\n')"`
- Validation notes:
  - Auto now uses explicit `validation.profile` only when in `{production,production_proof,smoke}`; explicit `auto` falls through to quantile inference.
  - Auto no longer infers smoke from `validation.smoke`; smoke remains explicit-profile only.
  - Missing/empty parseable `fit.quantiles` now fails cleanly under auto.

### Progress Update 2026-02-13 21:55 UTC
- Phase: P7B (validator auto-selection hardening)
- Change type: tests
- Summary: completed gap-only follow-up verification against current `af1a416` baseline; implementation already matched auto-selection contract, so only residual test coverage gaps were patched. Added explicit regression for `validation.profile: auto` infer-continue path and strengthened malformed-config assertions to ensure no traceback-like output.
- Files touched:
  - `repro/tests/test_validate_run.py`
  - `repro/UNIFIED_MULTIMODEL_WORKFLOW_TRACKER.md`
- Validation checks run:
  - `bash -n repro/tools/validate_run.sh`
  - `python3 -m unittest discover -s repro/tests -p 'test_*.py'`
  - `Rscript -e "parse(file='scripts/unified_run.R'); cat('R_PARSE_OK\n')"`
- Validation notes:
  - Unknown-profile error assertion now matches allowed values including `auto`.
  - Malformed YAML auto-fail test now asserts absence of `Traceback` and `File "` tokens in stdout.
  - Total test suite passed with the new coverage additions.

### Progress Update 2026-02-13 22:55 UTC
- Phase: P7 (post deterministic table export bugfix + guardrails)
- Change type: implementation+tests
- Summary: applied gap-only hardening to deterministic post table exports by fixing `ENV_SORT_KEEP_NA` parsing in post figures, removing empty-path exporter inconsistency, enforcing row-order preservation unless explicit `sort_keys` are provided, emitting table-export manifest file paths relative to the tables output dir, and adding recursive post artifact filtering to a safe extension allowlist.
- Files touched:
  - `R/environmetrics/40_figures.R`
  - `R/environmetrics/02_helpers_core.R`
  - `R/unified/stages/stage_post.R`
  - `tests/testthat/test_post_posterior_table_exports.R`
  - `repro/UNIFIED_MULTIMODEL_WORKFLOW_TRACKER.md`
- Validation checks run:
  - `Rscript -e "testthat::test_dir('tests/testthat', reporter='summary')"`
  - `python3 -m unittest discover -s repro/tests -p 'test_*.py'`
  - `Rscript -e "parse(file='scripts/unified_run.R'); cat('R_PARSE_OK\n')"`
- Validation notes:
  - No model/fit/posterior semantics were changed.
  - Deterministic sorting is now explicit-only (`sort_keys` provided); otherwise row order is preserved as supplied.

### Progress Update 2026-02-13 23:20 UTC
- Phase: P7 (post deterministic table export residual hardening)
- Change type: implementation+tests
- Summary: completed residual gap-only hardening by making table-export relative-path derivation robust for non-existent candidate paths (`normalizePath(..., mustWork=FALSE)` on file path with basename fallback), and by making `stage_post` run-root artifact prefix checks path-separator safe.
- Files touched:
  - `R/environmetrics/02_helpers_core.R`
  - `R/unified/stages/stage_post.R`
  - `tests/testthat/test_post_posterior_table_exports.R`
  - `repro/UNIFIED_MULTIMODEL_WORKFLOW_TRACKER.md`
- Validation checks run:
  - `Rscript -e "testthat::test_dir('tests/testthat', reporter='summary')"`
  - `python3 -m unittest discover -s repro/tests -p 'test_*.py'`
  - `Rscript -e "parse(file='scripts/unified_run.R'); cat('R_PARSE_OK\n')"`
- Validation notes:
  - No model/fit/posterior semantics changed.
  - Sorting behavior is unchanged: explicit valid `sort_keys` sorts, otherwise caller row order is preserved.
  - Post artifact capture remains extension-allowlist bounded.

### Progress Update 2026-02-13 23:45 UTC
- Phase: P7 (post deterministic table export integration closure)
- Change type: tests
- Summary: added lightweight integration coverage for deterministic post table exports by exercising on-disk table + manifest generation through `post_export_tables()`/`post_write_table_exports_manifest()` and asserting relative manifest file paths, resolved artifact existence, and byte-stable manifest content across reruns; also added guard assertions that `stage_post` artifact scanning remains allowlist-only and branch-consistent.
- Files touched:
  - `repro/tests/test_post_tables_manifest_integration.py`
  - `repro/UNIFIED_MULTIMODEL_WORKFLOW_TRACKER.md`
- Validation checks run:
  - `Rscript -e "testthat::test_dir('tests/testthat', reporter='summary')"`
  - `python3 -m unittest discover -s repro/tests -p 'test_*.py'`
  - `Rscript -e "parse(file='scripts/unified_run.R'); cat('R_PARSE_OK\n')"`
- Validation notes:
  - Coverage is lightweight and avoids heavy fit/post runtime while still validating the table-export integration boundary (filesystem outputs + manifest semantics).
  - No model/fit/posterior semantics were changed.

### Progress Update 2026-02-13 22:15 UTC
- Phase: P7 (post deterministic table export hardening)
- Change type: implementation+tests
- Summary: hardened post-stage table exports for deterministic and reliable output generation without model-semantic changes by adding deterministic table-export utilities (stable row/column handling, explicit NA policy, deterministic numeric CSV formatting, per-file sha256 manifest), routing exports to run-scoped `post/outputs/<RUN_ID>/tables/`, wiring configurable table formats (`csv` default, optional `rds`) through post env plumbing, and extending testthat coverage for byte-stable CSV output, NA policy, and checksum-manifest stability.
- Files touched:
  - `R/environmetrics/02_helpers_core.R`
  - `R/environmetrics/40_figures.R`
  - `R/unified/stages/stage_post.R`
  - `config/unified_run.template.yaml`
  - `tests/testthat/test_post_posterior_table_exports.R`
  - `repro/UNIFIED_MULTIMODEL_WORKFLOW_TRACKER.md`
- Validation checks run:
  - `Rscript -e "testthat::test_dir('tests/testthat', reporter='summary')"`
  - `python3 -m unittest discover -s repro/tests -p 'test_*.py'`
  - `Rscript -e "parse(file='scripts/unified_run.R'); cat('R_PARSE_OK\n')"`
- Validation notes:
  - `post.export_tables` behavior remains config-gated and backward-compatible; default still enabled.
  - Table artifacts are now emitted under `post/outputs/<RUN_ID>/tables/` and are captured by recursive post artifact manifest scanning.
  - Deterministic test coverage now includes CSV byte identity under reordered inputs and explicit NA-retain/NA-drop behavior.

### Progress Update 2026-02-13 23:59 UTC
- Phase: P8 (end-to-end unified-run smoke closure for post tables)
- Change type: tests
- Summary: added a true unified-run integration smoke test that executes `scripts/unified_run.R` through `stage_post` and validates table-export wiring plus run-manifest post artifact allowlist behavior using a lightweight post-runner stub in test scope for deterministic runtime.
- Files touched:
  - `repro/tests/test_unified_run_post_tables_smoke.py`
  - `repro/UNIFIED_MULTIMODEL_WORKFLOW_TRACKER.md`
- Evidence paths:
  - test-scoped run root pattern: `repro/_tmp_unittest/post_tables_e2e/<case>/runs/ut_post_tables_smoke/`
  - expected key files during test execution:
    - `repro/_tmp_unittest/post_tables_e2e/<case>/runs/ut_post_tables_smoke/run_manifest.yaml`
    - `repro/_tmp_unittest/post_tables_e2e/<case>/runs/ut_post_tables_smoke/post/outputs/ut_post_tables_smoke/tables/posterior_table_exports_manifest.csv`
- Validation checks run:
  - `python3 -m unittest repro.tests.test_unified_run_post_tables_smoke -v`
  - `python3 -m unittest discover -s repro/tests -p 'test_*.py'`
  - `Rscript -e "testthat::test_dir('tests/testthat', reporter='summary')"`
  - `Rscript -e "parse(file='scripts/unified_run.R'); cat('R_PARSE_OK\\n')"`
- Validation notes:
  - No model/fit/posterior semantics changed.
  - No storage-policy changes.
  - Test enforces relative table-export manifest file paths and excludes disallowed `.tex`/`.md` post artifact captures from `run_manifest.yaml`.

## 11) Open Questions / Resolved Defaults

### 11.1 Open

None currently tracked.

### 11.2 Resolved Defaults

1. D-007 is locked as hybrid sequencing (legacy bridge operational continuity + incremental theory-aligned replacement).
2. Config v1 includes model toggles:
   - `models.run_exdqlm_multivar` (default `true`)
   - `models.run_exdqlm_univar` (default `false`)
   - `models.run_ndlm_main` (default `false`)
3. P5 closure is accepted under D-010 with strict run-scoped figures-on smoke-fast proof.
4. Validation profile semantics are locked:
   - `production`: canonical 7-quantile enforcement with strict production gates.
   - `production_proof`: config-declared quantile enforcement with production-like non-quantile gates.
   - `smoke`: lightweight smoke-oriented validation contract.
   - `auto`: deterministic conservative resolution from `resolved_config.yaml`:
     - explicit `validation.profile` (`production|production_proof|smoke`) wins,
     - else `validation.smoke=true` implies `smoke`,
     - else canonical quantile set implies `production`,
     - else `production_proof`.
5. Manifest family authority defaults are locked for v1 metadata:
   - `families.exdqlm_multivar.authoritative` defaults to `true`.
   - `families.exdqlm_univar.authoritative` defaults to `false` unless explicitly set.
   - `families.ndlm_main.authoritative` defaults to `false` unless explicitly set.
6. NDLM validator-minimal artifact schema is locked when `models.run_ndlm_main=true`:
   - Accepted model-state outputs include `DISC_variables_50_NDLM_synth_DISC.RData`, `ndlm_main_state.RData`, or `ndlm_main_*.RData`.
   - If `fit.contract_checks.enabled=true`, require NDLM contract-check JSON under `fit/contract_checks/ndlm_main/`.
   - If `fit.diagnostics.enabled=true`, require NDLM diagnostics JSON under `fit/diagnostics/ndlm_main/`.
7. Manifest v1 now includes additive stage-status metadata:
   - `stages.<name>.status` uses `pass|fail|skip` (with `pending` only transiently during execution).
   - `stages.<name>.started_at_utc` and `stages.<name>.finished_at_utc` are populated on execution path.
   - `stages.<name>.log_path` records stage-log intent without changing run pass/fail semantics.
8. Write-audit policy defaults are locked:
   - Keep `write_audit.enforce_from_stage: 4` as production default.
   - Use `write_audit.enforce_from_stage: 2` for migration/proof runs that need fit/post write isolation evidence.
   - Reference overlay config: `config/unified_runs/migration_write_audit_from_fit.yaml`.
9. Forecats run-scoped snapshot policy is locked:
   - When snapshot bundle exists, shared-input resolution remains run-scoped and provenance is logged in `inputs/shared/source_map.txt`.
   - Fit/post shared-input validation logs source-map evidence under `fit/logs/shared_input_source_map.log` and `post/logs/shared_input_source_map.log`.
   - For `production` / `production_proof`, validator now enforces snapshot evidence when config declares `inputs.forecats.mode=build`, `inputs.forecats.snapshot.enabled=true`, and `inputs.shared.prefer_forecats_snapshot=true` (`snapshot_check.*` + `shared_source_*` / `snapshot_source_mode` lines).
   - Validator output reports shared/snapshot source-map paths and provenance fields for auditability.

## 12) Immediate Next Actions (Proposed)

1. Complete P3/P4 parity validation: add structural compatibility tests for post-consumed object contracts and equation-to-code audit notes versus theory repos.
2. Keep P2/P5 bridges stable while migrating family implementations behind the same unified contracts.
3. Define P6 orchestration smoke criteria for combined multivar + theory univar + theory NDLM execution under strict write-audit.

## 13) Notes

- Current multivariate exDQLM path (`DISC_Optimal_Synth_Ranges_W.r` + modular DISC-W runner chain) is treated as correct baseline.
- Univariate and NDLM legacy scripts are treated as candidates for theory-aligned replacement and cleanup.
- NDLM quantile argument is not semantically meaningful for current intended NDLM path; NDLM is tracked as a single neutral model artifact family.

## 14) Appendix: Contracts (Repo-grounded)

### 14.1 Discovery Report (2026-02-10)

Files inspected (read-only):

- Unified orchestration: `scripts/unified_run.R`, `R/unified/config.R`, `R/unified/manifest.R`, `R/unified/determinism.R`, `R/unified/utils_write_audit.R`
- Unified stages: `R/unified/stages/stage_forecats.R`, `R/unified/stages/stage_fit.R`, `R/unified/stages/stage_post.R`, `R/unified/stages/stage_validate.R`, `R/unified/stages/stage_report.R`
- DISC-W fit chain: `scripts/run_DISC_Optimal_Synth_Ranges_W.R`, `DISC_Optimal_Synth_Ranges_W.r`, `R/disc_w/01_paths_inputs.R`, `R/disc_w/05_save_state.R`
- Post chain: `scripts/run_environmetrics_figures.R`, `R/environmetrics/00_paths.R`, `R/environmetrics/10_data_inputs.R`, `R/environmetrics/30_univariate_and_misc.R`, `R/environmetrics/40_figures.R`
- Legacy scripts: `OptimalModelSLexAL.r`, `DISC_Optimal_Synth_Ranges_NDLM.r`, `run_scripts_SL.py`
- Validation/tools/config docs: `repro/compare_to_canonical.py`, `repro/tools/validate_run.sh`, `config/unified_run.template.yaml`, `config/unified_runs/heavy_site11160500_cutoff20221225.yaml`, `repro/UNIFIED_WORKFLOW_README.md`
- Run artifacts (small text only): `repro/runs/heavy_20260207_211120/*`, `repro/runs/heavy_20260208_040646/*`, `repro/runs/heavy_20260208_183742_postexports/*`, `repro/runs/heavy_20260209_010522/*`

Key findings:

1. Unified stage order is fixed and explicit: `forecats -> fit -> post -> validate -> report` (`scripts/unified_run.R:108-149`).
2. Current unified `fit` stage orchestrates DISC-W only; univariate and NDLM are not first-class unified stages (`R/unified/stages/stage_fit.R:3-133`).
3. Legacy univariate and NDLM outputs are still loaded from repo root by post modules (`R/environmetrics/30_univariate_and_misc.R:895-1035`).
4. Manifest schema is stable (`manifest_version=1`) but has no per-stage status block; skip/fail are inferred from control flow and `validation.status` (`R/unified/manifest.R:51-113`, `scripts/unified_run.R:126-152`).
5. Post uses relative `readRDS(...)` calls for intermediate files (`R/environmetrics/40_figures.R:4151`, `R/environmetrics/40_figures.R:4316`, `R/environmetrics/40_figures.R:4483`), which is a run-scoping risk unless paths are fully controlled.
6. NDLM legacy script currently hard-codes `p0 <- 0.5` and writes `DISC_variables_50_NDLM_synth_DISC.RData` to repo root (`DISC_Optimal_Synth_Ranges_NDLM.r:44`, `DISC_Optimal_Synth_Ranges_NDLM.r:2186`).
7. Univariate legacy script consumes command-line quantile and writes `variables_<q>_exAL_synth_DISC_uni.RData` to repo root (`OptimalModelSLexAL.r:45-46`, `OptimalModelSLexAL.r:2040`).

Historical ambiguities remaining after 2026-02-10 discovery (superseded by §11 authoritative state):

1. Exact canonical schema for future `ndlm_main` manifest family labeling is not implemented in current manifest v1.
2. Current post code consumes root model-state artifacts; run-scoped manifest-driven loading contract is not implemented yet.
3. Current default write-audit threshold (`enforce_from_stage=4`) does not audit fit/post by default.

### 14.2 Unified Runner Contracts (current implementation)

#### 14.2.1 Stage ordering + signatures

| Order | Stage | Function signature | Inputs (config/env) | Required outputs |
|---|---|---|---|---|
| 1 | `forecats` | `unified_stage_forecats(cfg, run_root, repo_root, manifest)` | `cfg$inputs$forecats$mode`, `pipeline_config_path`, `existing_bundle_path` (`R/unified/stages/stage_forecats.R:3-18`) | If `use_existing`, optional bundle artifact recorded in manifest; if `build`, log at `run_root/forecats/forecats_pipeline.log` |
| 2 | `fit` | `unified_stage_fit(cfg, run_root, repo_root, manifest)` | `cfg$fit$quantiles`, `cfg$inputs$fit.*`, `cfg$run$seed`, `cfg$run$threads$mc_cores`, `cfg$scale_contract$legacy_fit_input_scale` (`R/unified/stages/stage_fit.R:8-116`) | `run_root/fit/q=<QQ>/outputs/DISC_variables_<q>_exAL_synth_DISC.RData` |
| 3 | `post` | `unified_stage_post(cfg, run_root, repo_root, manifest)` | `cfg$post$profile`, `cfg$post$profile_detail`, `cfg$post$sort_keep_na`, `cfg$post$export_tables`, adapted CSV inputs (`R/unified/stages/stage_post.R:65-91`) | `run_root/post/outputs/<RUN_ID>/...` (images/csv/rds/tex/md) |
| 4 | `validate` | `unified_stage_validate(cfg, run_root, repo_root, manifest)` | `cfg$validation$canonical_run_id`, `cfg$validation$compare$mode` (`R/unified/stages/stage_validate.R:41-71`) | `run_root/validate/compare_report.txt`, `run_root/validate/compare_report.json`, `run_root/validate/diff/*` |
| 5 | `report` | `unified_stage_report(cfg, run_root, repo_root, manifest)` | `manifest$validation`, `cfg$post$profile`, compare report json (`R/unified/stages/stage_report.R:7-70`) | `run_root/report/summary.md`, `run_root/report/summary.json` (+ optional `profile_summary.md`) |

#### 14.2.2 PASS / FAIL / SKIP representation

1. Stage PASS: stage function returns `list(manifest = manifest)` and does not call `stop(...)`.
2. Stage FAIL: stage function calls `stop(...)` (or throws), `scripts/unified_run.R` exits non-zero before setting `finished_at_utc`.
3. Stage SKIP: stage is disabled by config (`cfg$stages[[stage]] == FALSE`) and not executed (`scripts/unified_run.R:126-127`).
4. Global run PASS: script reaches end, sets `manifest$timestamps$finished_at_utc`, writes manifest, exits status 0 (`scripts/unified_run.R:151-155`).
5. Global run FAIL: no final timestamp update; manifest often remains with `finished_at_utc: null`.

#### 14.2.3 Config load/validation + manifest lifecycle

1. Config load/merge/validate: `cfg <- unified_load_config(...)` (`scripts/unified_run.R:54`), implemented in `R/unified/config.R:252-269`.
2. Manifest init and early write: `unified_manifest_init(...)` then `unified_manifest_write(...)` before stage loop (`scripts/unified_run.R:83-89`).
3. Manifest update cadence: after each stage (`scripts/unified_run.R:140-143`) and once at final closure (`scripts/unified_run.R:151-152`).

Manifest v1 snippet (current, `R/unified/manifest.R:55-112`):

```yaml
manifest_version: 1
config_version: 1
run_id: "<RUN_ID>"
run_root: "<ABS_RUN_ROOT>"
timestamps:
  started_at_utc: "YYYY-MM-DDTHH:MM:SSZ"
  finished_at_utc: null
validation:
  compare_report_path: "<run_root>/validate/compare_report.json"
  write_audit_diff_path: "<run_root>/validate/write_audit/fs_diff.patch"
  status: "pending"
```

#### 14.2.4 Manifest v2 minimal freeze (target, doc contract)

```yaml
manifest_version: 2
run_id: "<RUN_ID>"
run_root: "<ABS_RUN_ROOT>"

stages:
  fit:
    status: "pass"                # enum: pass|fail|skip
    started_at_utc: "YYYY-MM-DDTHH:MM:SSZ"
    finished_at_utc: "YYYY-MM-DDTHH:MM:SSZ"
    log_paths:
      console: "<run_root>/fit/runner_console.txt"
  post:
    status: "pass"
    started_at_utc: "YYYY-MM-DDTHH:MM:SSZ"
    finished_at_utc: "YYYY-MM-DDTHH:MM:SSZ"
    log_paths:
      console: "<run_root>/post/runner_console.txt"
  validate:
    status: "pass"
    started_at_utc: "YYYY-MM-DDTHH:MM:SSZ"
    finished_at_utc: "YYYY-MM-DDTHH:MM:SSZ"
    log_paths:
      console: "<run_root>/validate/runner_console.txt"
  report:
    status: "pass"
    started_at_utc: "YYYY-MM-DDTHH:MM:SSZ"
    finished_at_utc: "YYYY-MM-DDTHH:MM:SSZ"
    log_paths:
      console: "<run_root>/report/runner_console.txt"

families:
  exdqlm_multivar:
    enabled: true
    implementation_mode: "legacy_bridge"   # enum: legacy_bridge|theory_aligned
    authoritative: true
  exdqlm_univar:
    enabled: true
    implementation_mode: "legacy_bridge"
    authoritative: false
  ndlm_main:
    enabled: true
    implementation_mode: "legacy_bridge"
    authoritative: false

artifacts:
  - family: "exdqlm_multivar"
    role: "model_state"           # e.g., model_state|table|figure|input_snapshot|log|report
    format: "rdata"               # e.g., rdata|rds|csv|png|json|yaml|txt|md|tex
    path: "<ABS_OR_RUN_REL_PATH>"
    sha256: "<HEX_SHA256>"
```

### 14.3 Config Schema Contracts (repo-grounded)

#### 14.3.1 Config files in use

1. Unified default template: `config/unified_run.template.yaml`
2. Operational heavy harness template: `config/unified_runs/heavy_site11160500_cutoff20221225.yaml`
3. Per-run resolved config (generated): `repro/runs/<RUN_ID>/resolved_config.yaml`
4. Forecats stage delegated config (when used): `config/forecats_pipeline.template.yaml` passed to `scripts/forecats_pipeline.R`

#### 14.3.2 Key controls + where consumed

| Key | Default | Consumed in |
|---|---|---|
| `stages.forecats|fit|post|validate|report` | all `true` in template | stage loop gate (`scripts/unified_run.R:126-127`) |
| `run.repro_mode` | `strict` | deterministic policy (`R/unified/determinism.R:39-57`) |
| `run.seed` | `777` | `unified_apply_seed` and fit wrapper seed env (`scripts/unified_run.R:82`, `R/unified/stages/stage_fit.R:79-93`) |
| `run.threads.mc_cores` | `1` | quantile parallelism (`R/unified/stages/stage_fit.R:108-116`) |
| `fit.quantiles` | `[0.05,...,0.95]` | per-quantile execution (`R/unified/stages/stage_fit.R:67-76`) |
| `fit.warm_start.enabled` | `false` | forwarded as `DISC_USE_PREV` env (`R/unified/stages/stage_fit.R:80`) |
| `inputs.fit.*_path` | `null` | validated in `R/unified/config.R:210-215`; consumed in fit/post adapters |
| `inputs.fit.*_storage_scale` | `log1p_cms` | adapter conversion in fit/post (`R/unified/stages/stage_fit.R:18-61`, `R/unified/stages/stage_post.R:16-59`) |
| `post.profile`, `post.profile_detail` | `false` | post runner env vars (`R/unified/stages/stage_post.R:73-74`) |
| `post.sort_keep_na`, `post.export_tables` | `true` | post runner env vars (`R/unified/stages/stage_post.R:66-77`) |
| `validation.canonical_run_id` | `null` | compare target selection (`R/unified/stages/stage_validate.R:41-46`) |
| `validation.compare.mode` | `both` | compare tool arg (`R/unified/stages/stage_validate.R:70`) |
| `write_audit.enabled`, `write_audit.enforce_from_stage`, `write_audit.allowlist_outside_run_root` | `true`, `4`, `[]` | stage-gated snapshots/enforcement (`scripts/unified_run.R:122-148`) |

#### 14.3.3 Defaults and override precedence

1. Base defaults from `unified_config_defaults()` (`R/unified/config.R:5-100`).
2. User YAML deep-merged onto defaults (`R/unified/config.R:102-122`, `R/unified/config.R:261`).
3. Paths normalized against repo root (`R/unified/config.R:160-179`, `R/unified/config.R:262`).
4. Validation fast-fails on missing files / invalid enums (`R/unified/config.R:181-249`, `R/unified/config.R:264-267`).
5. Operational harness overrides (heavy runs) are applied by writing a run-specific YAML before invoking unified runner (`repro/run_unified_heavy.sh:59-114`, `repro/run_unified_heavy.sh:230-236`).

#### 14.3.4 Shared input bundle contract (target for P1)

Run-scoped shared input root (all enabled families read from here):

- `repro/runs/<RUN_ID>/inputs/shared/parameters/parameters.txt`
- `repro/runs/<RUN_ID>/inputs/shared/retros/retros.csv`
- `repro/runs/<RUN_ID>/inputs/shared/forecasts/nws_forecast.csv`
- `repro/runs/<RUN_ID>/inputs/shared/forecasts/glofas_forecast.csv`
- `repro/runs/<RUN_ID>/inputs/shared/covariates/cov_1_ELI.csv`
- `repro/runs/<RUN_ID>/inputs/shared/covariates/cov_2_ONI.csv`

Config/manifest linkage (repo-grounded):

1. Current config v1 keys that already exist and are consumed:
   - `inputs.fit.parameters_path`
   - `inputs.fit.retros_path`
   - `inputs.fit.nws_forecast_path`
   - `inputs.fit.glofas_forecast_path`
2. Current manifest v1 fields that record these source files:
   - `inputs[]` entries (`R/unified/manifest.R:19-49`, `R/unified/manifest.R:80`)
   - adapted run-local copies under `fit/inputs` and `post/inputs` are recorded in `artifacts[]` (`R/unified/stages/stage_fit.R:63-65`, `R/unified/stages/stage_post.R:61-63`).
3. Covariate files are currently hardcoded in post paths (`R/environmetrics/00_paths.R:22-23`) and are not yet represented by unified config keys; adding explicit config/manifest linkage is part of P1/P5 cutover work.

Forecats build-mode snapshot contract:

1. If `stages.forecats=true` and mode is `build`, copy/snapshot the produced bundle artifacts from forecats outputs into `repro/runs/<RUN_ID>/inputs/shared/forecats_bundle/`.
2. Record each copied/snapshotted forecats input artifact hash in manifest `artifacts[]` with role `input_snapshot`.
3. Downstream fit/post stages read forecats-derived inputs from `inputs/shared/forecats_bundle/...`, not from mutable global paths.

### 14.4 Artifact Contracts by Model Family

#### 14.4.1 Multivariate exDQLM (DISC-W, current unified fit family)

| Contract item | Current repo-grounded behavior |
|---|---|
| Producer | `R/unified/stages/stage_fit.R` calls `Rscript --vanilla scripts/run_DISC_Optimal_Synth_Ranges_W.R <q> <seed>` (`R/unified/stages/stage_fit.R:90-93`) |
| Run-scoped output file | `repro/runs/<RUN_ID>/fit/q=<QQ>/outputs/DISC_variables_<q>_exAL_synth_DISC.RData` (`R/unified/stages/stage_fit.R:72-100`) |
| RData object naming pattern | Dynamic names created in `disc_w_save_state`: `samp.gamma_<q>_exAL_synth_DISC`, `samp.sigma_<q>_exAL_synth_DISC`, `new.theta.out_<q>_exAL_synth_DISC`, etc. (`R/disc_w/05_save_state.R:22-110`) |
| Manifest reference style | `artifacts[]` entries with `storage_scale: model_state` and `flow_domain: cfg$scale_contract$analysis_scale_fit_internal` (`R/unified/stages/stage_fit.R:123-128`) |
| Post dependency today | Post still loads DISC-W root `.RData` files directly (not run-scoped) in `R/environmetrics/30_univariate_and_misc.R:999-1030` |

#### 14.4.2 Univariate exDQLM (legacy family, not yet unified stage)

| Contract item | Current repo-grounded behavior |
|---|---|
| Producer | Legacy script `OptimalModelSLexAL.r` (launched by `run_scripts_SL.py`) with CLI quantile argument (`run_scripts_SL.py:22-29`, `OptimalModelSLexAL.r:45-46`) |
| Output file path | Root write: `/data/muscat_data/jaguir26/project1_ucsc_phd/variables_<q>_exAL_synth_DISC_uni.RData` (`OptimalModelSLexAL.r:2040`) |
| Expected object names consumed by post | `new.theta.out_<q>_exAL_synth_DISC_uni`, `samp.theta_<q>_exAL_synth_DISC_uni` and related objects (`R/environmetrics/30_univariate_and_misc.R:154-736`) |
| Manifest reference today | None (no unified stage writes these artifacts into manifest) |

#### 14.4.3 NDLM (legacy family, not yet unified stage)

| Contract item | Current repo-grounded behavior |
|---|---|
| Producer | Legacy script `DISC_Optimal_Synth_Ranges_NDLM.r` with hardcoded `p0 <- 0.5` (`DISC_Optimal_Synth_Ranges_NDLM.r:44`) |
| Output file path | Root write: `/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_variables_50_NDLM_synth_DISC.RData` (`DISC_Optimal_Synth_Ranges_NDLM.r:2186`) |
| Expected object names consumed by post | `new.theta.out_50_NDLM_synth_DISC`, `samp.theta_50_NDLM_synth_DISC`, `samp.sigma_50_NDLM_synth_DISC` (`R/environmetrics/40_figures.R:220-221`, `R/environmetrics/40_figures.R:1235`, `R/environmetrics/40_figures.R:1992`) |
| Manifest reference today | None (no unified stage writes NDLM artifacts into manifest) |

#### 14.4.4 Manifest mapping proposal constrained to current schema

Current manifest schema does not have a `family` field in `artifacts[]` (`R/unified/manifest.R:115-126`).  
Implementation-safe mapping for multi-model migration should therefore be path-prefix based:

1. `fit/exdqlm_multivar/q=<QQ>/outputs/*.RData`
2. `fit/exdqlm_univar/q=<QQ>/outputs/*.RData`
3. `fit/ndlm_main/outputs/*.RData`

Open question: whether to add explicit `family` field in manifest v2 vs retain path-prefix inference.

### 14.5 Post-Processing Dependency Map (non-run-scoped loads)

| File:line | Load/read pattern | Expected artifacts/objects | Run-scoping risk |
|---|---|---|---|
| `R/environmetrics/00_paths.R:39-45` | Defines `UNI_VAR_*` root paths | `variables_<q>_exAL_synth_DISC_uni.RData` | Root dependency |
| `R/environmetrics/30_univariate_and_misc.R:100-149` | `load(UNI_VAR_05..95)` via `load_rdata_with_retry()` | `new.theta.out_<q>_exAL_synth_DISC_uni`, `samp.theta_<q>_exAL_synth_DISC_uni`, etc. | Root dependency |
| `R/environmetrics/30_univariate_and_misc.R:895-897` | `load("/.../DISC_variables_50_NDLM_synth_DISC.RData")` | `new.theta.out_50_NDLM_synth_DISC` | Root dependency |
| `R/environmetrics/30_univariate_and_misc.R:999-1035` | `load("/.../DISC_variables_<q>_exAL_synth_DISC.RData")` | `new.theta.out_<q>_exAL_synth_DISC`, `samp.theta_<q>_exAL_synth_DISC` | Root dependency |
| `R/environmetrics/40_figures.R:4151` | `readRDS("y_reps_f.rds")` | intermediate posterior arrays | Relative path dependency |
| `R/environmetrics/40_figures.R:4316` | `readRDS("y_reps_f_new.rds")` | intermediate posterior arrays | Relative path dependency |
| `R/environmetrics/40_figures.R:4483` | `readRDS("y_reps_new.rds")` | intermediate posterior arrays | Relative path dependency |

Recommendation for P5 contract:

1. Replace root/relative loads with manifest-declared absolute paths.
2. Stage post should fail fast if required family artifacts are missing from manifest.
3. Keep family-separated output folders as already decided in D-006.

### 14.6 Legacy Bridge Execution Semantics (current reality)

1. DISC-W bridge (already unified): `stage_fit` runs wrapper `scripts/run_DISC_Optimal_Synth_Ranges_W.R`, which sources legacy script (`source("DISC_Optimal_Synth_Ranges_W.r", chdir=TRUE)`), injecting run-scoped input/output paths through `DISC_W_*` env vars (`R/unified/stages/stage_fit.R:78-96`, `scripts/run_DISC_Optimal_Synth_Ranges_W.R:32-39`, `R/disc_w/01_paths_inputs.R:16-27`).
2. Post bridge (already unified): `stage_post` runs `scripts/run_environmetrics_figures.R` with env overrides for run root + adapted CSV paths (`R/unified/stages/stage_post.R:70-91`, `scripts/run_environmetrics_figures.R:11-27`).
3. Univariate legacy execution today: tmux-per-quantile launcher `run_scripts_SL.py` invokes `Rscript /.../OptimalModelSLexAL.r <q>` (`run_scripts_SL.py:12-29`); outputs go to repo root (`OptimalModelSLexAL.r:2040`).
4. NDLM legacy execution today: no unified wrapper stage exists; script writes to repo root (`DISC_Optimal_Synth_Ranges_NDLM.r:2186`) and assumes root-level input/output paths.

### 14.7 Run-Scoping + Collision Audit (current state)

#### 14.7.1 Hardcoded/root write points

1. Univariate outputs to repo root (`OptimalModelSLexAL.r:2040`).
2. NDLM outputs to repo root (`DISC_Optimal_Synth_Ranges_NDLM.r:2186`).
3. DISC-W warm-start loads from root `DISC_variables_*` when enabled (`DISC_Optimal_Synth_Ranges_W.r:1417-1480`).
4. Post loads model-state `.RData` from root (`R/environmetrics/30_univariate_and_misc.R:895-1035`).
5. Forecats build mode writes outside run root via delegated script behavior (`R/unified/stages/stage_forecats.R:16-29`).

#### 14.7.2 Current run tree convention to preserve

Current unified outputs use:

- `repro/runs/<RUN_ID>/fit/q=<QQ>/outputs/...`
- `repro/runs/<RUN_ID>/post/outputs/<RUN_ID>/...`  (nested `<RUN_ID>` is current convention and is consumed by validate stage)
- `repro/runs/<RUN_ID>/validate/...`
- `repro/runs/<RUN_ID>/report/...`

`stage_validate` explicitly compares `run_root/post/outputs/<RUN_ID>` (`R/unified/stages/stage_validate.R:38-40`), so this nesting should remain until compare contracts are versioned.

#### 14.7.3 Current vs Target Run Tree (Versioned)

| Current manifest v1 paths (produced today) | Target manifest v2 paths (proposed; phase + backward compatibility) |
|---|---|
| **Fit (DISC-W current)**: `repro/runs/<RUN_ID>/fit/q=<QQ>/outputs/DISC_variables_<q>_exAL_synth_DISC.RData` (+ logs at `fit/q=<QQ>/logs/fit.log`) | **Fit families**: `repro/runs/<RUN_ID>/fit/exdqlm_multivar/q=<QQ>/...`, `repro/runs/<RUN_ID>/fit/exdqlm_univar/q=<QQ>/...`, `repro/runs/<RUN_ID>/fit/ndlm_main/...` (introduced P2-P4; compatibility: keep current `fit/q=<QQ>/outputs` + `fit/q=<QQ>/logs` through D-009 cutover) |
| **Post outputs**: `repro/runs/<RUN_ID>/post/outputs/<RUN_ID>/...` | **Post family separation under required nesting**: `repro/runs/<RUN_ID>/post/outputs/<RUN_ID>/exdqlm_multivar/...`, `.../exdqlm_univar/...`, `.../ndlm_main/...` (introduced P5; compatibility: preserve `post/outputs/<RUN_ID>/` nesting per D-008 until validate v2) |
| **Validate**: `repro/runs/<RUN_ID>/validate/compare_report.json`, `repro/runs/<RUN_ID>/validate/write_audit/.../fs_diff.patch` | **Validate v2**: same root plus stage-scoped logs/status in manifest `stages.validate.*` (introduced P5-P6; compatibility: keep current file names to avoid breaking `repro/tools/validate_run.sh` and existing reports) |
| **Report**: `repro/runs/<RUN_ID>/report/summary.md`, `repro/runs/<RUN_ID>/report/summary.json` | **Report v2**: same root paths + family-aware report sections and manifest `stages.report.*` status/log linkage (introduced P6; compatibility: preserve `summary.md/json` filenames) |
| **Inputs (current mixed)**: stage-local adapters in `fit/inputs/` and `post/inputs/`, plus some external/root dependencies | **Shared run inputs**: `repro/runs/<RUN_ID>/inputs/shared/...` as single source for enabled families (introduced P1 via T-P1-04; compatibility: allow staged adapters to read from shared path while preserving current stage-local filenames during bridge period) |
| **Forecats build outputs (current)**: external trees under `data/forecats_inputs/...` and `data/forecats_cache/...` | **Forecats snapshot in run root**: copy/snapshot required forecats artifacts into `repro/runs/<RUN_ID>/inputs/shared/forecats_bundle/...` and hash in manifest (introduced P1/P2; compatibility: keep external forecats outputs as source-of-copy until forecats stage is fully run-scoped) |

### 14.8 Parallel Orchestration Policy (current implementation)

1. Quantile parallelism is implemented only in unified fit stage via `parallel::mclapply` over `cfg$fit$quantiles` with `cfg$run$threads$mc_cores` (`R/unified/stages/stage_fit.R:108-116`).
2. Post/validate/report stages run serially in `scripts/unified_run.R` stage loop (`scripts/unified_run.R:126-149`).
3. RNG/thread determinism policy is centralized in `R/unified/determinism.R`; strict mode forces single-thread defaults and fixed RNG kind (`R/unified/determinism.R:3-57`).
4. C++ samplers use derived per-thread seeds from a base seed set by `set_sampling_exal_seed`/`set_sampling_truncnorm_seed` (`sampling_exal.cpp:20-44`, `sampling_truncnorm.cpp:35-59`).
5. Policy recording in manifest:
   - `repro.mode`, `repro.seed`, `repro.thread_env`, `repro.r_rng` (`R/unified/manifest.R:65-79`).

Concurrency rule for migration phases:

1. exDQLM multivariate quantiles may stay parallel per current fit stage.
2. NDLM should remain isolated as a single stage/job (no quantile fanout) until NDLM-v2 contracts are finalized.
3. Post/validate/report remain serialized and manifest-driven.
