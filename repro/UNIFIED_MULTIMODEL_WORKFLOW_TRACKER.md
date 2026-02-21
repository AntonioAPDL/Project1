# Unified Multi-Model Workflow Tracker (Living)

Date: 2026-02-10  
Last verified: 2026-02-20 (canonical one-core-per-model parallel end-to-end run closed PASS; post-quality diagnosis checklist opened for NDLM/univar quality and multivar synthesis-horizon/aggregated-discrepancy figure integrity)  
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
- Current `fit` stage orchestrates multivariate exDQLM (DISC-W) and can optionally run univariate exDQLM + NDLM via per-family toggles and `implementation_mode` dispatch (`theory_aligned` default; `legacy_bridge` fallback).
- Current `post` stage runs `scripts/run_environmetrics_figures.R`.

Repo references:

- `scripts/unified_run.R`
- `R/unified/stages/stage_fit.R`
- `R/unified/stages/stage_post.R`

## 2.2 What remains incomplete in first-class unified model orchestration

- Theory-aligned univariate and NDLM runners are wired in unified `fit` and selected by `models.<family>.implementation_mode`.
- Legacy scripts (`OptimalModelSLexAL.r`, `DISC_Optimal_Synth_Ranges_NDLM.r`) remain supported as explicit fallback paths when `implementation_mode=legacy_bridge`.
- Remaining open work is parity/completeness follow-up (not orchestration presence), focused on NDLM convergence-quality review and full post synthesis replay artifacts under figures/tables-enabled post mode.

Repo references:

- `scripts/run_exdqlm_univar.R`
- `scripts/run_ndlm_main.R`
- `R/unified/families/exdqlm_univar/*`
- `R/unified/families/ndlm_main/*`
- `run_scripts_SL.py`
- `DISC_Optimal_Synth_Ranges_NDLM.r`
- `OptimalModelSLexAL.r`

## 2.3 Current hidden dependency risk in post-processing

Strict post mode now resolves model-state artifacts from run-scoped manifest paths; legacy root fallback remains a controlled non-strict compatibility path.

Repo references:

- `R/environmetrics/00_paths.R`
- `R/environmetrics/30_univariate_and_misc.R`

Implication:

- In strict repro mode, post requires run-scoped model-state artifacts.
- In non-strict mode, legacy root fallback remains possible only when explicitly enabled for compatibility.

## 2.4 Last Verified Evidence Pointers (2026-02-18)

- P9 closure proof runs (q=0.01, 0.50, 0.99):
  - `repro/runs/debug_extreme_mv_q010599_parallel_max800_20260216_222144/run_manifest.yaml`
  - `repro/runs/debug_extreme_uv_q010599_parallel_max800_20260216_222436/run_manifest.yaml`
- Multivariate proof outputs:
  - `repro/runs/debug_extreme_mv_q010599_parallel_max800_20260216_222144/fit/q=01/outputs/DISC_variables_1_exAL_synth_DISC.RData`
  - `repro/runs/debug_extreme_mv_q010599_parallel_max800_20260216_222144/fit/q=50/outputs/DISC_variables_50_exAL_synth_DISC.RData`
  - `repro/runs/debug_extreme_mv_q010599_parallel_max800_20260216_222144/fit/q=99/outputs/DISC_variables_99_exAL_synth_DISC.RData`
- Univariate proof outputs:
  - `repro/runs/debug_extreme_uv_q010599_parallel_max800_20260216_222436/fit/exdqlm_univar/q=01/outputs/variables_01_exAL_synth_DISC_uni.RData`
  - `repro/runs/debug_extreme_uv_q010599_parallel_max800_20260216_222436/fit/exdqlm_univar/q=50/outputs/variables_50_exAL_synth_DISC_uni.RData`
  - `repro/runs/debug_extreme_uv_q010599_parallel_max800_20260216_222436/fit/exdqlm_univar/q=99/outputs/variables_99_exAL_synth_DISC_uni.RData`
- Latest trace summaries:
  - `repro/reports/figures/debug_extreme_mv_q010599_parallel_max800_20260216_222144_trace_summary_latest.png`
  - `repro/reports/figures/debug_extreme_uv_q010599_parallel_max800_20260216_222436_trace_summary_latest.png`
- Canonical production closure run:
  - `repro/runs/prod_canonical_p8c_parallel_20260216_220751/run_manifest.yaml`
  - `repro/runs/prod_canonical_parallel_allmodels_20260218_040416/run_manifest.yaml`
  - `repro/runs/prod_canonical_parallel_allmodels_20260218_040416/report/summary.md`
  - `repro/runs/prod_canonical_parallel_allmodels_20260218_040416/validate/compare_report.json`
  - `repro/runs/prod_canonical_parallel_allmodels_20260218_040416/validate/env_drift_report.json`
  - `repro/runs/prod_canonical_parallel_allmodels_20260218_040416/post/outputs/prod_canonical_parallel_allmodels_20260218_040416/post_smoke_marker.txt`
- Full-figures post replay (contract-report closure evidence):
  - `repro/runs/post_replay_canonical_fullprod_fix2_20260219_002249/run_manifest.yaml`
  - `repro/runs/post_replay_canonical_fullprod_fix2_20260219_002249/post/outputs/post_replay_canonical_fullprod_fix2_20260219_002249/post_artifacts_manifest.csv`
  - `repro/runs/post_replay_canonical_fullprod_fix2_20260219_002249/post/outputs/post_replay_canonical_fullprod_fix2_20260219_002249/post_artifacts_summary.json`
  - `repro/runs/post_replay_canonical_fullprod_fix2_20260219_002249/post/cache/y_reps_f.rds`
  - `repro/runs/post_replay_canonical_fullprod_fix2_20260219_002249/post/cache/y_reps.rds`
  - `repro/runs/post_replay_canonical_fullprod_fix2_20260219_002249/post/outputs/post_replay_canonical_fullprod_fix2_20260219_002249/tables/posterior_table_exports_manifest.csv`
- Canonical trace summaries (all enabled families):
  - `repro/reports/figures/prod_canonical_p8c_parallel_20260216_220751_univar_trace_summary_latest.png`
  - `repro/reports/figures/prod_canonical_p8c_parallel_20260216_220751_multivar_trace_summary_latest.png`
  - `repro/reports/figures/prod_canonical_p8c_parallel_20260216_220751_ndlm_trace_summary_latest.png`
- Trace plotting utility:
  - `repro/tools/plot_unified_trace_summaries.py`
- Stage graph + status wiring: `scripts/unified_run.R`
- Fit family dispatch + implementation modes: `R/unified/stages/stage_fit.R`
- Default config + implementation modes: `config/unified_run.template.yaml`, `R/unified/config.R`
- Canonical production family config: `config/unified_runs/production_canonical_family.yaml`
- Extreme-q debug configs:
  - `config/unified_runs/debug_q01_multivar_extreme.yaml`
  - `config/unified_runs/debug_q01_multivar_extreme_states.yaml`
- Validator profile resolution (`production|production_proof|smoke|auto`): `repro/tools/validate_run.sh`

## 2.5 Canonical P8C Health Snapshot (2026-02-17)

Run-level closure:

| run_id | finished_at_utc | validation.status | stage statuses |
|---|---|---|---|
| `prod_canonical_p8c_parallel_20260216_220751` | `2026-02-17T13:40:00Z` | `pass` | `forecats=pass`, `data_prep_shared=pass`, `fit=pass`, `post=pass`, `validate=pass`, `report=pass` |
| `prod_canonical_parallel_allmodels_20260218_040416` | `2026-02-18T10:43:26Z` | `pass` | `forecats=pass`, `data_prep_shared=pass`, `fit=pass`, `post=pass`, `validate=pass`, `report=pass` |

Post-mode note for latest run (`prod_canonical_parallel_allmodels_20260218_040416`):

1. `post.smoke_fast=true`, `post.figures=false`, `post.export_tables=false`.
2. Expected post output is smoke marker + logs (not full synthesis figure/table bundle).

Family/quantile fit snapshot from latest `gamsig_progress` lines:

| family | q | final_iter | final_elbo | final_sigma_exp | final_gamma_exp |
|---|---|---:|---:|---:|---:|
| `exdqlm_multivar` | `0.01` | 800 | -44.83422 | 0.01179619 | 1.953162 |
| `exdqlm_multivar` | `0.05` | 466 | -44.65134 | 0.03011774 | 0.9584789 |
| `exdqlm_multivar` | `0.10` | 800 | -44.60489 | 0.04203167 | 0.5289511 |
| `exdqlm_multivar` | `0.50` | 134 | -44.28300 | 0.07889116 | -0.04823061 |
| `exdqlm_multivar` | `0.90` | 800 | -44.15141 | 0.05367939 | -1.139010 |
| `exdqlm_multivar` | `0.95` | 800 | -44.14914 | 0.04167215 | -1.826992 |
| `exdqlm_multivar` | `0.99` | 800 | -44.44925 | 0.02117679 | -3.882173 |
| `exdqlm_univar` | `0.01` | 800 | -1929.086 | 0.3812341 | 61.47403 |
| `exdqlm_univar` | `0.05` | 769 | 113901.1 | 0.0002493927 | 7.852744 |
| `exdqlm_univar` | `0.10` | 215 | 113904.6 | 0.0002494134 | 3.750303 |
| `exdqlm_univar` | `0.50` | 70 | 113909.9 | 0.0002493727 | -0.0000005375816 |
| `exdqlm_univar` | `0.90` | 211 | 113904.6 | 0.0002494129 | -3.750300 |
| `exdqlm_univar` | `0.95` | 700 | 113901.1 | 0.0002493898 | -7.852662 |
| `exdqlm_univar` | `0.99` | 800 | -1927.464 | 0.3812506 | -61.46849 |
| `ndlm_main` | `0.50` | 16 | -13660.61 | 0.7382676 | NA |

## 2.6 Automatic Cutoff Retrospective Policy (Forecats Batch/Render)

Scope:

1. Implemented in `scripts/forecats_batch.R` render path.
2. Configured via `inputs.retros.automatic_cutoff_policy` (defaulted in `config/forecats_batch.site=11160500.default.yaml`).
3. Used by unified workflow through forecats bundle snapshots consumed by `data_prep_shared`, therefore shared by multivariate exDQLM, univariate exDQLM, and NDLM downstream.

Version mapping logic (by cutoff `c`):

1. Forecast-origin bounds enforced from local shared cache snapshot: `2019-11-05` to `2023-01-31`.
2. GloFAS historical source selection:
   - `2.x` family cutoffs -> `version_2_1` (`glofas_hist_v21_htessel_cons`)
   - `3.x` family cutoffs -> `version_3_1` (`glofas_hist_v31_lisflood_cons`)
   - `4.x` family cutoffs -> `version_4_0` (`glofas_hist_v40_lisflood_cons`)
3. NWS primary retrospective source: synthetic one-step series (`nws_synth_retro_ens_mean`).
4. Optional NWS hybrid diagnostic (audit-only): same-version retrospective, then next-version gap fill, then synthetic fallback.
5. NWS synthetic-gap fill rule (enabled by default):
   - for missing synthetic value at day `t`, use latest available NWS forecast-cache issue that predicts `t` (equivalent to trying day+1 from `t-1`, then day+2 from `t-2`, then day+3 from `t-3`, etc.).
   - fail fast if unresolved synthetic gaps remain after this lead fallback (indicates outage longer than available lead horizon).

Shared retrospective window rule:

1. For each cutoff, selected NWS primary and selected GloFAS historical are loaded through `date <= cutoff`.
2. Compute:
   - `shared_start = max(min_date_nws_selected, min_date_glofas_selected)`
3. Retrospective preparation tables are built on `[shared_start, cutoff]` inclusive.
4. Plot input `retros_daily.csv` remains windowed to `[plot_start, plot_end]` for rendering compatibility/performance, but sourced from the shared-window-trimmed selected series.

Per-cutoff outputs (bundle `inputs/`):

1. `retros_daily.csv` (plot-consumed long schema).
2. `retrospective_preparation.csv` with:
   - `date`
   - `selected_glofas_retrospective_value`
   - `selected_nws_synthetic_value`
   - `shared_window_flag`
   - selected source/version labels used for the cutoff.
3. `retrospective_nws_hybrid_diagnostic.csv` (optional audit diagnostic when enabled).
4. `meta.yaml` now records `retrospective_policy` selection fields and preparation artifact paths.
5. `retrospective_preparation.csv` includes synthetic-fill diagnostics (`selected_nws_synthetic_fill_*`, filled/unresolved flags).

Fallback/error behavior:

1. If cutoff is outside local shared origin span, render fails fast with explicit bounds error.
2. If cutoff is a known missing-origin date (`2020-03-12..2020-03-16`, `2020-07-29`, `2020-11-14`, `2022-07-14`), render fails fast with explicit date list.
3. If required selected retrospective source is missing from cache, render fails fast with actionable source-id inventory.
4. If automatic policy is explicitly disabled, legacy/manual selection policy is used and a fallback preparation table is still emitted.

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
| D-005 | In unified config, NDLM should be mandatory when `models.run_ndlm_main=true`; default intended as enabled in production mode. | Locked | No silent NDLM skip in full production runs. |
| D-006 | Post outputs/reports should remain separated by model family; do not merge posterior outputs into a single blended block. | Locked | Shared inputs are allowed; outputs remain clearly separated. |
| D-007 | Sequencing is hybrid: wire legacy scripts into unified runner early for operational continuity, while replacing them module-by-module with theory-aligned implementations. | Locked | This is now the active and accepted execution strategy. |
| D-008 | Preserve `post/outputs/<RUN_ID>/` nesting until validate contract is explicitly versioned. | Locked | `stage_validate` currently compares against `run_root/post/outputs/<RUN_ID>`; do not break this path contract before validate v2. |
| D-009 | Preserve current DISC-W fit output contract `fit/q=<QQ>/outputs/...` until family-path cutover. | Locked | Existing fit/post tooling and run artifacts rely on this structure; migration to `fit/exdqlm_multivar/...` is a versioned cutover item. |
| D-010 | P5 closure is accepted via strict run-scoped figures-on smoke using smoke-fast path; full heavy figure hardening is a separate follow-up item. | Locked | Requires non-null manifest closure, run-scoped load proof, and PNG outputs under run root. |
| D-011 | P9 closure is accepted as operationally robust (“good enough”) when isolated extreme-quantile proof runs close with run-scoped artifacts and no hard runtime failures, even if some tails terminate at max-iter. | Locked | Residual strict-tail convergence tightening is tracked as follow-up optimization, not a blocker for forward workflow implementation. |
| D-012 | Legacy post root fallback remains deprecated compatibility-only and must be disabled for `production` and `production_proof` validation profiles. | Locked | `post.allow_legacy_root_fallback=true` now triggers explicit policy FAIL in external validator for non-smoke profiles. |

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
| P4 | [x] | NDLM modularization (theory-aligned VB) | P2 done | New modular NDLM stage with forecast-window stochastic `W` policy implemented per NDLM theory, plus ELBO/VB parity regression and contract evidence |
| P5 | [x] | Post decoupling from root artifacts | P2 done | Post loads only manifest-declared run-scoped artifacts and strict figures-on smoke closes with non-null `finished_at_utc` |
| P6 | [x] | Parallel orchestration hardening | P5 done | exDQLM multivar + univar parallel; NDLM isolated; no cross-stage clobbering |
| P7 | [x] | Validation/report family-aware automation | P6 done | PASS criteria include per-family artifact checks + write-audit + manifest closure, with family-summary report regression coverage |
| P8 | [x] | Cutover + deprecation plan | P7 done | Theory-aligned stages become default; legacy stages optional fallback |
| P9 | [x] | Extreme-quantile stabilization (q=0.01 first) | P8C failure evidence captured | Isolated extreme-quantile proof runs (`q=0.01,0.50,0.99`) close for exDQLM multivar + univar under adaptive defaults, with run-scoped outputs and no hard runtime failures (operational closure accepted under D-011) |

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
- [x] `T-P4-02`: Replace forecast-window discount-factor-only path with theory-aligned stochastic `W` treatment (VB only).
- [x] `T-P4-03`: Update ELBO and VB covariance distribution updates per NDLM derivations.
- [x] `T-P4-04`: Emit neutral NDLM artifacts (`ndlm_main`) with stable schema.
- [x] `T-P4-05`: Add NDLM structural compatibility contract checks against post-consumed aliases.
- [x] `T-P4-06`: Add theory-mode diagnostics (finite/shape/symmetry/PSD sampled checks + summary-log invariants) and equation-to-code audit notes for NDLM modules.

## 7.6 P5 Tasks (Post Decoupling)

- Note: P5 phase closure was accepted under D-010 via strict run-scoped figures-on smoke-fast proof; the items below remain full-hardening follow-ups where compatibility fallback behavior still exists in non-strict mode.
- `T-P5-01`: Remove hardcoded root `.RData` loads in `R/environmetrics/30_univariate_and_misc.R`.
- `T-P5-02`: Load all family artifacts from manifest paths.
- `T-P5-03`: Keep family-specific outputs separated in post output tree.

## 7.7 P6-P8 Tasks (Orchestration, Validation, Cutover)

- [x] `T-P6-01`: Add explicit model-family toggles under unified config.
- [x] `T-P6-02`: Add scheduling policy for parallel exDQLM stages + NDLM isolation.
- [x] `T-P7-01`: Extend validator to enforce per-family required outputs.
- [x] `T-P7-02`: Extend report to summarize each family separately.
- [x] `T-P8-01`: Change defaults to theory-aligned stages; keep legacy as opt-in fallback.
- [x] `T-P8-02`: Add end-to-end unified-run smoke integration coverage for post table exports and post artifact allowlist capture.
- [x] `T-P8-03`: Add canonical production family config (canonical 7 quantiles) plus validator UX/docs regression coverage.
- [x] `T-P8-04`: Complete canonical production evidence run (P8C) with production validator PASS and closed manifest.

## 7.8 P9 Tasks (Extreme-Quantile Stabilization)

- [x] `T-P9-01`: Stop active failing canonical run cleanly and preserve failure forensics (manifest, runner log, q=01 fit log) before cleanup.
- [x] `T-P9-02`: Quarantine/remove failed run artifacts with evidence trail (before/after space + retained key logs) using safe cleanup policy.
- [x] `T-P9-03`: Run theory-first audit for failing path at q=0.01 (`objective_deltas` / `update_gamma_sigma`), mapping equations to code and finite-domain requirements.
- [x] `T-P9-04`: Build isolated reproducer (`fit.quantiles=[0.01]`, multivar-only, post/validate/report OFF) and reproduce deterministically.
- [x] `T-P9-05`: Implement diagnostics-first guardrails (finite/domain checks + precise error context) and shared policy controls.
- [x] `T-P9-06`: Promote adaptive `gamma/sigma` stabilization to default for exDQLM multivar + univar (`warmup_freeze_iters=20`, `guard_refreeze_iters=10`, `init.mode=robust`, `objective_guard.enabled=true`, `objective_guard.mode=adaptive_freeze`), with per-family override controls.
- [x] `T-P9-07`: Validate fixes with isolated extreme-quantile proofs (`q=0.01,0.50,0.99`) for exDQLM multivar + univar, plus targeted regression tests and trace monitoring artifacts.

## 8) Risk Register (Live)

| Risk ID | Severity | Description | Mitigation | Owner | Status |
|---|---|---|---|---|---|
| R-001 | Critical | NDLM forecast-window covariance mismatch vs theory can invalidate inference. | Prioritize P4 equation-to-code audit + tests before making NDLM default authoritative. | TBD | Mitigated (P4 closed with theory-aligned NDLM mode, stochastic `W` smoke closure, and NDLM VB regression test coverage) |
| R-002 | High | Post currently consumes root pre-generated NDLM/univariate artifacts. | Execute P5 decoupling before declaring full autonomy. | TBD | Mitigated (strict run-scoped smoke passed; non-smoke validator now enforces disabled legacy root fallback) |
| R-003 | High | Legacy scripts contain duplicated core functions and fragile patterns. | Modularize with strict tests and narrow wrappers. | TBD | Open |
| R-004 | Medium | Parallel orchestration may induce file collisions without strict run-scope contracts. | Enforce per-family/per-quantile isolated output roots + write-audit. | TBD | Mitigating (P2B fit-stage write-audit pass with empty outside-run-root diff) |
| R-005 | Medium | Ambiguity on sequencing can delay implementation. | Lock D-007 or replace with alternate sequence immediately after P0. | Maintainer | Mitigated (D-007 locked) |
| R-006 | High | DISC-W warm-start can load root `DISC_variables_*` paths, violating run-scoped reproducibility if enabled. | Keep warm-start disabled by default; if enabled, require run-scoped warm-start source path recorded in manifest before stage execution. | TBD | Mitigating (legacy bridge env routing now run-scoped; warm-start remains disabled by default) |
| R-007 | Medium | Post reads `y_reps*.rds` via relative paths, creating working-directory-sensitive behavior. | In P5, enforce absolute/manifest-declared paths for these intermediates and fail fast on unresolved relative reads. | TBD | Mitigating (run-scoped cache path enforced) |
| R-008 | Medium | Extreme quantile (`q=0.01`) multivar fit can enter non-finite objective regions without adaptive safeguards. | Keep adaptive gamma/sigma guardrails defaulted across exDQLM families; maintain extreme-quantile regression proofs and trace monitoring for drift. | TBD | Mitigated for current scope (P9 closure accepted under D-011; residual strict-tail convergence tightening tracked as follow-up optimization) |
| R-009 | High | Post synthesis horizon may be truncated before full forecast lead window (expected up to GloFAS 30-day support) in multivar and NDLM figure outputs. | Execute isolated post diagnostics that compare each plotted time index against available `NWS/GloFAS` member horizons and model-state forecast arrays; enforce explicit horizon-contract checks before plotting. | TBD | Open (diagnosis checklist queued) |
| R-010 | High | Aggregated discrepancy figures (`Agg_disc_*`) currently render observed discrepancies only, without fitted aggregated discrepancy overlays. | Audit aggregated discrepancy plotting path and model-fit object wiring; add contract checks requiring both observed and fitted aggregated discrepancy series in figure payloads. | TBD | Open (diagnosis checklist queued) |
| R-011 | Medium | Univariate exDQLM and NDLM outputs may be numerically complete but visually/structurally inconsistent with expected model behavior in synthesis windows. | Run isolated single-family lanes (NDLM-only and univar median-only) with dedicated convergence + posterior trace diagnostics and post-only replay checks before changing model logic. | TBD | Open (diagnosis checklist queued) |

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

### Progress Update 2026-02-19 02:20 UTC
- Phase: P8C/P7 follow-up hardening
- Change type: implementation+validation
- Summary: implemented run-scoped post artifact contract helpers, wired contract report generation/fail-fast into post runner, extended validator with post artifact contract gates, and fixed validator `--profile auto` SIGPIPE/exit-141 failure path under `pipefail`. Verified against real full-figures replay artifacts and updated regression coverage.
- Files touched:
  - `R/unified/post_artifact_contract.R`
  - `scripts/run_environmetrics_figures.R`
  - `R/unified/stages/stage_post.R`
  - `repro/tools/validate_run.sh`
  - `tests/testthat/test_post_artifact_contract.R`
  - `repro/tests/test_validate_run.py`
  - `repro/UNIFIED_MULTIMODEL_WORKFLOW_TRACKER.md`
- Evidence paths:
  - `repro/runs/post_replay_canonical_fullprod_fix2_20260219_002249/post/outputs/post_replay_canonical_fullprod_fix2_20260219_002249/post_artifacts_manifest.csv`
  - `repro/runs/post_replay_canonical_fullprod_fix2_20260219_002249/post/outputs/post_replay_canonical_fullprod_fix2_20260219_002249/post_artifacts_summary.json`
  - `/tmp/post_replay_fix2_validate_auto_v2.txt`
  - `/tmp/post_replay_fix2_validate_prod.txt`
- Validation notes:
  - `python3 -m pytest -q repro/tests/test_validate_run.py` -> `29 passed`
  - `python3 -m pytest -q repro/tests/test_post_tables_manifest_integration.py` -> `2 passed`
  - `Rscript --vanilla -e "testthat::test_file('tests/testthat/test_post_artifact_contract.R')"` -> pass
  - `Rscript --vanilla -e "testthat::test_file('tests/testthat/test_post_forecast_horizon.R')"` -> pass (expected warning only)
  - `Rscript --vanilla -e "testthat::test_file('tests/testthat/test_ndlm_post_jsd.R')"` -> pass (expected warning only)
- New risks:
  - None added; this closes validator output robustness bug and post artifact-contract coverage gap.
- Next action:
  - Keep NDLM convergence-quality review as the primary remaining quality task; post artifact contract and validator hardening are now in place.

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

### Progress Update 2026-02-14 00:05 UTC
- Phase: P8A
- Change type: config-policy+tests+docs
- Summary: completed first P8 cutover step by switching univariate/NDLM implementation-mode defaults to `theory_aligned` while keeping both families disabled by default; retained explicit `legacy_bridge` fallback and added one-time non-fatal deprecation warnings when legacy bridge is selected for an enabled univariate/NDLM family.
- Files touched:
  - `R/unified/config.R`
  - `config/unified_run.template.yaml`
  - `R/unified/manifest.R`
  - `R/unified/stages/stage_fit.R`
  - `repro/tests/test_config_implementation_mode_defaults.py`
  - `repro/UNIFIED_WORKFLOW_README.md`
  - `repro/UNIFIED_MULTIMODEL_WORKFLOW_TRACKER.md`
- Evidence paths:
  - `config/unified_run.template.yaml`
  - `repro/tests/test_config_implementation_mode_defaults.py`
- Validation commands run:
  - `python3 -m unittest discover -s repro/tests -p 'test_*.py'`
  - `Rscript -e "testthat::test_dir('tests/testthat', reporter='summary')"`
  - `Rscript -e "parse(file='scripts/unified_run.R'); cat('R_PARSE_OK\n')"`
- Validation notes:
  - Defaults remain `models.run_exdqlm_univar=false` and `models.run_ndlm_main=false`.
  - `legacy_bridge` remains accepted as explicit per-family override.
  - No model/fit/post semantics changed in this chunk.

### Progress Update 2026-02-13 23:35 UTC
- Phase: P8B
- Change type: config+tests+docs
- Summary: added canonical production family config (`production_canonical_family.yaml`) with all families enabled, theory-aligned univariate/NDLM modes, canonical quantiles `[0.01,0.05,0.10,0.50,0.90,0.95,0.99]`, strict `validation.profile=production`, and explicit `write_audit.enforce_from_stage=4`; added lightweight regression test coverage for canonical config contract and explicit-production auto-profile resolution; updated README to clarify canonical production vs production-proof usage and validator expectations.
- Files touched:
  - `config/unified_runs/production_canonical_family.yaml`
  - `repro/tests/test_production_canonical_family_config.py`
  - `repro/tests/test_validate_run.py`
  - `repro/UNIFIED_WORKFLOW_README.md`
  - `repro/UNIFIED_MULTIMODEL_WORKFLOW_TRACKER.md`
- Evidence paths:
  - `config/unified_runs/production_canonical_family.yaml`
  - `repro/tests/test_production_canonical_family_config.py`
  - `repro/tests/test_validate_run.py`
- Validation commands run:
  - `python3 -m unittest discover -s repro/tests -p 'test_*.py'`
  - `Rscript -e "testthat::test_dir('tests/testthat', reporter='summary')"`
  - `Rscript -e "parse(file='scripts/unified_run.R'); cat('R_PARSE_OK\n')"`
- Validation notes:
  - `validate_run.sh` logic already matched canonical-vs-proof auto-resolution policy, so no tooling patch was required in this chunk.
  - Template defaults remain unchanged for family run toggles (`models.run_exdqlm_univar=false`, `models.run_ndlm_main=false`).
  - Canonical production evidence run was deferred in this chunk (resource-gated; no runtime risk escalation).

### Progress Update 2026-02-14 00:01 UTC
- Phase: P8C
- Change type: operations+validation
- Summary: executed one canonical production run attempt using `config/unified_runs/production_canonical_family.yaml` (`run_id=prod_canonical_p8b_template`) and collected runtime evidence; run did not close in this interactive cycle (fit remained in early quantile iterations and was interrupted), so P8C remains deferred pending a dedicated long-budget execution window.
- Files touched:
  - `repro/UNIFIED_MULTIMODEL_WORKFLOW_TRACKER.md`
- Run id:
  - `prod_canonical_p8b_template`
- Evidence paths:
  - `repro/runs/prod_canonical_p8b_template/resolved_config.yaml`
  - `repro/runs/prod_canonical_p8b_template/run_manifest.yaml`
  - `repro/runs/prod_canonical_p8b_template/fit/q=01/logs/fit.log`
  - `repro/runs/prod_canonical_p8b_template/fit/q=05/logs/fit.log`
  - `repro/runs/prod_canonical_p8b_template/fit/q=10/logs/fit.log`
  - `repro/runs/prod_canonical_p8b_template/fit/inputs/parameters.txt`
  - `repro/runs/prod_canonical_p8b_template/fit/inputs/retros_fit_adapter.csv`
  - `repro/runs/prod_canonical_p8b_template/fit/inputs/nws_fit_adapter.csv`
  - `repro/runs/prod_canonical_p8b_template/fit/inputs/glofas_fit_adapter.csv`
  - `repro/runs/prod_canonical_p8b_template/inputs/shared/source_map.txt`
  - `repro/runs/prod_canonical_p8b_template/inputs/shared/forecats_bundle/snapshot_source_map.txt`
  - `repro/reports/validator/prod_canonical_p8b_template_auto.txt`
  - `repro/reports/validator/prod_canonical_p8b_template_production.txt`
- Validation commands run:
  - `python3 -m unittest discover -s repro/tests -p 'test_*.py'`
  - `Rscript -e "testthat::test_dir('tests/testthat', reporter='summary')"`
  - `Rscript -e "parse(file='scripts/unified_run.R'); cat('R_PARSE_OK\\n')"`
  - `df -h /data`
  - `df -i /data`
  - `bash repro/tools/validate_run.sh prod_canonical_p8b_template --profile auto --exit-nonzero`
  - `bash repro/tools/validate_run.sh prod_canonical_p8b_template --profile production --exit-nonzero`
- Validation notes:
  - Preconditions passed and canonical config contract matched expected values (all families enabled, theory-aligned univar/NDLM modes, canonical quantiles, `validation.profile=production`, `write_audit.enforce_from_stage=4`).
  - `run_manifest.yaml` remained open (`timestamps.finished_at_utc: null`, `validation.status: pending`, `stages.fit.status: pending`) because execution was interrupted before fit completion.
  - Validator outputs for both `--profile auto` and `--profile production` are `RESULT=FAIL` with `profile_effective=production` and `quantile_outputs=0/7`, consistent with the incomplete run state.
  - No model/fit/post semantics changes were made and no storage-policy code changes were made in this step.
  - Next action: execute one dedicated uninterrupted canonical run window, then run `validate_run.sh` with `--profile auto` and `--profile production` and attach validator outputs under `repro/reports/validator/`.

### Progress Update 2026-02-14 01:09 UTC
- Phase: P8C (ops rerun request)
- Change type: operations
- Summary: stopped active canonical run attempt `prod_canonical_p8c_20260213_162304` on maintainer request and launched a fresh full workflow run constrained to quantiles `[0.05, 0.50, 0.95]`.
- Files touched:
  - `repro/UNIFIED_MULTIMODEL_WORKFLOW_TRACKER.md`
- Configs used:
  - First attempt (blocked by preflight): `/tmp/prod_proof_q3_20260214_010854.yaml`
  - Active rerun (in progress): `/tmp/prod_proof_q3_20260214_010911.yaml`
- Run ids:
  - stopped: `prod_canonical_p8c_20260213_162304`
  - active: `prod_proof_q3_20260214_010911`
- Validation notes:
  - First rerun attempt failed at run-start storage preflight (`free_gb=71.60`, threshold `min_free_gb_start=90`).
  - Ops-only remediation applied via temp config threshold alignment (`min_free_gb_start=70`, `min_free_gb_continue=60`) with no model/fit/post semantics changes.
  - Second rerun attempt passed run-start preflight and is currently running in persistent session.
- Next action:
  - Monitor active run to completion, then execute validator checks (`--profile auto` and `--profile production_proof`) and record evidence paths.

### Progress Update 2026-02-14 00:21 UTC
- Phase: P8C
- Change type: operations
- Summary: completed diagnose-first gate and launched one fresh canonical production run in background with a unique run id to avoid partial-state ambiguity from deferred run `prod_canonical_p8b_template`; no code changes applied because diagnosis indicated interruption/partial-run state rather than a proven deterministic model bug.
- Files touched:
  - `repro/UNIFIED_MULTIMODEL_WORKFLOW_TRACKER.md`
- Run id:
  - `prod_canonical_p8c_20260213_162140`
- Operational evidence paths:
  - `/tmp/prod_canonical_p8c_20260213_162140.yaml` (runtime overlay config with pinned `run.run_id`)
  - `repro/reports/validator/prod_canonical_p8c_20260213_162140_runner.log`
  - `repro/reports/validator/prod_canonical_p8c_20260213_162140.pid`
  - `repro/runs/prod_canonical_p8c_20260213_162140/run_manifest.yaml` (in-progress while run is active)
- Validation/diagnosis checks run:
  - `git status -sb`
  - `git rev-parse --abbrev-ref HEAD`
  - `git log -n 12 --oneline`
  - `python3 -m unittest discover -s repro/tests -p 'test_*.py'`
  - `Rscript -e "testthat::test_dir('tests/testthat', reporter='summary')"`
  - `Rscript -e "parse(file='scripts/unified_run.R'); cat('R_PARSE_OK\\n')"`
  - deferred-run inspection over `run_manifest.yaml`, `resolved_config.yaml`, `fit/q=*/logs/fit.log`, and `fit/q=*/outputs/*.RData`
  - process checks via `ps`/`pgrep`
  - `df -h /data`
  - `df -i /data`
- Diagnosis summary:
  - Deferred run remained open (`finished_at_utc: null`) with zero completed quantile output files recorded at diagnosis time.
  - Validator fail (`quantile_outputs=0/7`) was consistent with incomplete run state.
  - Headroom at launch: `/data` `72G` free, inode usage `4%`.
- Next action:
  - Keep run active; perform health checks (`ps -p $(cat <pidfile>)`, tail runner log, inspect `run_manifest.yaml` stage status), then run validator `--profile auto` and `--profile production` once run closes.

### Progress Update 2026-02-14 00:23 UTC
- Phase: P8C
- Change type: operations
- Summary: relaunched canonical production run in a persistent PTY session (instead of `nohup` background) because this execution environment reaps detached background jobs at command return; run now advanced through `forecats` and `data_prep_shared` and entered `fit`.
- Files touched:
  - `repro/UNIFIED_MULTIMODEL_WORKFLOW_TRACKER.md`
- Run id:
  - `prod_canonical_p8c_20260213_162304`
- Operational evidence paths:
  - `/tmp/prod_canonical_p8c_20260213_162304.yaml`
  - `repro/runs/prod_canonical_p8c_20260213_162304/resolved_config.yaml`
  - `repro/runs/prod_canonical_p8c_20260213_162304/run_manifest.yaml`
- Session tracking:
  - PTY session id: `87547`
- Next action:
  - Keep session alive and monitor fit progress via session polling and run-root logs, then execute validator `--profile auto` and `--profile production` after run closure.

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
     - explicit `validation.profile` in `{production,production_proof,smoke}` wins,
     - explicit `validation.profile=auto` falls through to inference,
     - otherwise infer by normalized `fit.quantiles`: canonical set -> `production`, non-canonical -> `production_proof`,
     - missing/invalid `fit.quantiles` in auto mode is a validator FAIL.
   - Canonical quantile set for `production`/canonical-auto resolution is `[0.01,0.05,0.10,0.50,0.90,0.95,0.99]`.
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
8. Post legacy fallback policy is locked:
   - `post.allow_legacy_root_fallback` defaults to `false`.
   - For `production` and `production_proof`, validator enforces `post.allow_legacy_root_fallback=false`.
   - Any `true` setting is treated as deprecated compatibility mode and must remain smoke-only.
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
10. P8A implementation-mode defaults are locked:
   - `models.exdqlm_univar.implementation_mode` defaults to `theory_aligned`.
   - `models.ndlm_main.implementation_mode` defaults to `theory_aligned`.
   - `models.run_exdqlm_univar` and `models.run_ndlm_main` remain default `false`; no behavior change unless families are enabled.
   - `legacy_bridge` remains supported as explicit fallback and now emits a non-fatal deprecation warning when selected for an enabled family.
11. P9 exDQLM gamma/sigma stabilization defaults are locked for both multivar + univar:
   - `warmup_freeze_iters: 20`
   - `freeze_target: gamma_sigma`
   - `guard_refreeze_iters: 10`
   - `init.mode: robust` with `gamma=0.0`, `sigma_floor=1e-3`, `sigma_scale=1.0`
   - `objective_guard.enabled: true`, `objective_guard.mode: adaptive_freeze`, `fail_fast: false`, `log_failures: true`, `penalty: 1e12`
   - Per-family config overrides remain supported under `fit.exdqlm_multivar.gamma_sigma.*` and `fit.exdqlm_univar.gamma_sigma.*`.
12. P9 closure acceptance rule is locked under D-011:
   - Operational closure requires completed isolated extreme-quantile proofs with run-scoped artifacts and no hard runtime failures.
   - Hitting max-iter in extreme tails is acceptable for this closure gate when traces remain stable and outputs are produced.
   - Additional strict-tail convergence tightening is tracked as non-blocking follow-up work.

## 12) Immediate Next Actions (Post-Quality Isolation Checklist)

Scope note:
1. Canonical workflow execution is now confirmed end-to-end PASS under one-core-per-model parallel mode.
2. The active blocker is output-quality correctness (NDLM/univar behavior and multivar synthesis/aggregated-discrepancy figure integrity), not orchestration stability.

Checklist (execute in order, one lane at a time):

- [x] `Q-00` Baseline freeze + diagnostics contract
  - Lock baseline run for diagnosis: `prod_canonical_full_e2e_parallel_onecore_20260220_002642`.
  - Snapshot current problematic artifacts and map each to producing code path:
    - NDLM quality figure: `All3_ndlm_DISC.png`
    - Univar quality figures (median-focused)
    - Multivar horizon and aggregated discrepancy figures:
      - `All3_exal_DISC.png`
      - `Agg_disc_1991_2022_1.png` (and sibling `Agg_disc_*`)
  - Define expected horizon contract explicitly for all synthesis figures:
    - Plot domain end must match the maximum valid forecast horizon across available model inputs used in that plot (NWS/GloFAS/member availability aware).

- [x] `Q-01` NDLM-only isolated fit + post diagnosis lane
  - Run NDLM-only fit and NDLM-only post replay from run-scoped artifacts.
  - Add NDLM diagnostics outputs:
    - ELBO trace
    - state norm trace
    - sigma (and any NDLM-specific dynamic variance/weight traces already available)
    - forecast-window coverage trace (time index actually plotted vs available)
  - Acceptance gate:
    - NDLM figures use full intended forecast window for the selected plot definition.
    - No silent truncation from index-shape mismatch.
  - Current sub-status:
    - `Q-01A` run closure and diagnostics bundle are complete.
    - `Q-01B` root-cause matrix is complete with a single supported cause for the original NDLM-only post crash.
    - `Q-01C` horizon-contract closure has been upgraded to theory-aligned ragged-horizon invariants (`K_j`, `A_k`, `K_overlap`, `K_max`, segment profile) with passing NDLM-only diagnostics.

### 12.1) `Q-00` + `Q-01` Root-Cause Debug Checklist (Execution Contract)

Use this checklist as mandatory execution contract for `Q-00` and `Q-01`. Do not patch code until phases A-D are complete and evidence is written.

Phase A: Baseline freeze (`Q-00A`)
1. Lock diagnosis baseline run id and path:
   - `RUN_BASE=prod_canonical_full_e2e_parallel_onecore_20260220_002642`
   - `repro/runs/${RUN_BASE}`
2. Record immutable baseline snapshot in:
   - `repro/runs/${RUN_BASE}/diagnostics/q00_baseline/`
3. Write `baseline_manifest.md` containing:
   - run id, stage statuses, finished timestamp, active git commit hash,
   - exact list of target artifacts under diagnosis (`All3_ndlm_DISC.png`, `All3_exal_DISC.png`, all `Agg_disc_*`, univar median synthesis figures),
   - producer code map (`file`, `function/block`, `line hint`).
4. Write `baseline_symptom_table.csv` with one row per symptom:
   - `symptom_id`, `artifact_path`, `observed_behavior`, `expected_behavior`, `severity`, `suspected_layer` (`fit`, `post`, `plot_contract`, `time_index`).

Phase B: Contract audit (`Q-00B`)
1. Write `horizon_contract.md` for each affected figure family:
   - expected x-range definition,
   - required source time vectors,
   - max valid horizon rule and truncation rule.
2. Write `shape_contract_table.csv` for NDLM objects used in post:
   - object name,
   - expected rank/dims/type,
   - observed rank/dims/type from baseline run artifacts,
   - status (`match`, `mismatch`, `ambiguous`).
3. Parse post logs and emit `contract_warnings_summary.csv`:
   - warning/error key,
   - count,
   - first/last occurrence,
   - affected script.
4. `Q-00` completion gate:
   - all four baseline contract files exist and are linked in progress log.

Phase C: NDLM isolation lane (`Q-01A`)
1. Run isolated NDLM lane only (fit + post) with deterministic seed and run-scoped output directory:
   - no univar/multivar families enabled in this lane.
2. Persist NDLM diagnostics bundle at:
   - `repro/runs/<Q01_RUN_ID>/diagnostics/ndlm/`
3. Required diagnostics files:
   - `ndlm_iter_trace.csv`: `iter, elbo, elbo_diff, state_norm_sq, sigma_expectation`.
   - `ndlm_time_coverage.csv`: `source_series, t_min, t_max, n_points, missing_count`.
   - `ndlm_plot_contract_check.csv`: figure-level expected vs actual x-range coverage.
   - `ndlm_object_shapes.csv`: NDLM post-input object shapes read at render time.

Phase D: Root-cause isolation (`Q-01B`)
1. Build `ndlm_hypothesis_matrix.md` with three root classes and explicit falsification checks:
   - H1 time-index contract mismatch,
   - H2 tensor orientation/rank mismatch,
   - H3 upstream forecast-horizon truncation propagated into plotting.
2. For each hypothesis, run one minimal discriminating check and record outcome with artifact path.
3. Declare root cause only when one hypothesis is supported and alternatives are falsified.
4. No code fix is allowed unless `ndlm_hypothesis_matrix.md` has a single supported root-cause conclusion.

Phase E: Fix-readiness gate (`Q-01C`)
1. Before edits, write `ndlm_fix_spec.md`:
   - invariant(s) to enforce,
   - exact interfaces/files to change,
   - why fix preserves model/post semantics.
2. Define acceptance criteria:
   - NDLM synthesis figures cover contract horizon,
   - no index/dimension warning promoted to error in NDLM lane,
   - post artifacts generated with non-empty fitted series where required.
3. Only after this gate: implement code changes and proceed to `Q-04/Q-05`.

- [ ] `Q-02` Univariate exDQLM median-only isolated lane (`q=0.50`)
  - Run univar-only (`q=0.50`) fit + post replay.
  - Produce compact diagnostics pack:
    - ELBO trace
    - gamma/sigma traces
    - state norm trace
    - synthesis horizon coverage trace
  - Acceptance gate:
    - Median univar synthesis aligns with expected horizon and does not show premature plot cutoff.

- [ ] `Q-03` Multivariate post-only figure integrity lane
  - Reuse existing multivar fit artifacts; run post-only replay focused on multivar figures.
  - Diagnose and fix two issues:
    - `Q-03A`: synthesis horizon truncation in `All3_exal_DISC.png` and related multivar synthesis plots.
    - `Q-03B`: aggregated discrepancy figures (`Agg_disc_*`) must include fitted aggregated discrepancy series, not only observed discrepancy.
  - Add explicit plot-data contract checks before rendering:
    - observed series length
    - fitted series length
    - plotted x-range
    - missing-value handling policy
  - Acceptance gate:
    - Fitted aggregated discrepancy overlay is present and non-empty in every `Agg_disc_*` figure.
    - Synthesis x-range matches the expected forecast horizon contract.

- [ ] `Q-04` Root-cause closure + regression guardrails
  - For every corrected issue, record:
    - exact root cause (object/dimension/time-index mismatch, wrong variable selection, or path-level contract mismatch),
    - exact file/line fixes,
    - why the fix is theory-consistent (no cosmetic patching).
  - Add targeted tests for:
    - horizon coverage contract,
    - aggregated discrepancy fit presence contract,
    - NDLM/univar median post-figure data-shape checks.

- [ ] `Q-05` Recompose final quality pack
  - Re-run post (full figures + tables) from corrected artifacts.
  - Register final evidence paths for:
    - NDLM corrected figures and traces
    - univar median corrected figures and traces
    - multivar corrected synthesis + `Agg_disc_*` figures
  - Update risk register statuses for `R-009`, `R-010`, `R-011` and close checklist items.

### 12.2) Context-Switch Resume Reminder (Current State)

If work is paused for a tangent, resume from this exact state:

1. `Q-00` is complete (`Q-00A` + `Q-00B`) with baseline artifacts under:
   - `repro/runs/prod_canonical_full_e2e_parallel_onecore_20260220_002642/diagnostics/q00_baseline/`
2. `Q-01A` is complete on rerun:
   - `run_id=diag_q01a_ndlm_only_sharedseed_fitpost_resume_sharedfix_20260220_215704`
   - stages: `forecats=pass`, `data_prep_shared=pass`, `fit=pass`, `post=pass`
3. `Q-01B` is complete:
   - single supported root cause for the original NDLM-only post crash is family-unaware post initialization wiring.
4. Active remaining NDLM issue after `Q-01A/B`:
   - resolved: NDLM horizon-contract mismatch was closed in rerun `diag_q01a_ndlm_only_horizonfix_20260220_223605` with passing `ndlm_plot_contract_check.csv`.
5. Resume evidence anchors:
   - `repro/runs/diag_q01a_ndlm_only_sharedseed_fitpost_resume_sharedfix_20260220_215704/run_manifest.yaml`
   - `repro/runs/diag_q01a_ndlm_only_sharedseed_fitpost_resume_sharedfix_20260220_215704/post/logs/post_runner.log`
   - `repro/runs/diag_q01a_ndlm_only_sharedseed_fitpost_resume_sharedfix_20260220_215704/diagnostics/ndlm/ndlm_iter_trace.csv`
   - `repro/runs/diag_q01a_ndlm_only_sharedseed_fitpost_resume_sharedfix_20260220_215704/diagnostics/ndlm/ndlm_plot_contract_check.csv`
   - `repro/runs/diag_q01a_ndlm_only_sharedseed_fitpost_resume_sharedfix_20260220_215704/diagnostics/ndlm/ndlm_hypothesis_matrix.md`
   - `repro/runs/diag_q01a_ndlm_only_horizonfix_20260220_223605/run_manifest.yaml`
   - `repro/runs/diag_q01a_ndlm_only_horizonfix_20260220_223605/diagnostics/ndlm/ndlm_horizon_contract.md`
   - `repro/runs/diag_q01a_ndlm_only_horizonfix_20260220_223605/diagnostics/ndlm/ndlm_plot_contract_check.csv`

## 13) Notes

- Current multivariate exDQLM path (`DISC_Optimal_Synth_Ranges_W.r` + modular DISC-W runner chain) is treated as correct baseline.
- Univariate and NDLM legacy scripts are treated as candidates for theory-aligned replacement and cleanup.
- NDLM quantile argument is not semantically meaningful for current intended NDLM path; NDLM is tracked as a single neutral model artifact family.

## 14) Appendix: Contracts (Repo-grounded)

### 14.1 Discovery Report (2026-02-10)

This subsection is a historical discovery snapshot captured on 2026-02-10. Current authoritative behavior is defined by §§2, 11, and subsequent progress updates.

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
| 2 | `data_prep_shared` | `unified_stage_data_prep_shared(cfg, run_root, repo_root, manifest)` | `cfg$inputs$fit.*`, `cfg$inputs$forecats.*`, `cfg$inputs$shared.*` | `run_root/inputs/shared/...` canonical run-scoped shared bundle + source-map/hashes |
| 3 | `fit` | `unified_stage_fit(cfg, run_root, repo_root, manifest)` | `cfg$fit$quantiles`, `cfg$models.*`, `cfg$inputs$fit.*`, `cfg$run$seed`, `cfg$run$threads$mc_cores`, `cfg$scale_contract$legacy_fit_input_scale` | multivar: `run_root/fit/q=<QQ>/outputs/DISC_variables_<q>_exAL_synth_DISC.RData`; univar (if enabled): `run_root/fit/exdqlm_univar/q=<QQ>/outputs/variables_<QQ>_exAL_synth_DISC_uni.RData`; NDLM (if enabled): `run_root/fit/ndlm_main/outputs/DISC_variables_50_NDLM_synth_DISC.RData` |
| 4 | `post` | `unified_stage_post(cfg, run_root, repo_root, manifest)` | `cfg$post$profile`, `cfg$post$profile_detail`, `cfg$post$sort_keep_na`, `cfg$post$export_tables`, run-scoped artifact/env resolution | `run_root/post/outputs/<RUN_ID>/...` (images/csv/rds/txt/json/yaml/tsv/pdf by allowlist) |
| 5 | `validate` | `unified_stage_validate(cfg, run_root, repo_root, manifest)` | `cfg$validation$canonical_run_id`, `cfg$validation$compare$mode` | `run_root/validate/compare_report.txt`, `run_root/validate/compare_report.json`, `run_root/validate/diff/*` |
| 6 | `report` | `unified_stage_report(cfg, run_root, repo_root, manifest)` | `manifest$validation`, `cfg$post$profile`, compare report json | `run_root/report/summary.md`, `run_root/report/summary.json` (+ optional `profile_summary.md`) |

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
| `stages.forecats|data_prep_shared|fit|post|validate|report` | template defaults: `forecats,fit,post,validate,report=true`, `data_prep_shared=false` | stage loop gate + stage status writes (`scripts/unified_run.R`) |
| `run.repro_mode` | `strict` | deterministic policy (`R/unified/determinism.R:39-57`) |
| `run.seed` | `777` | `unified_apply_seed` and fit wrapper seed env (`scripts/unified_run.R:82`, `R/unified/stages/stage_fit.R:79-93`) |
| `run.threads.mc_cores` | `1` | quantile parallelism (`R/unified/stages/stage_fit.R:108-116`) |
| `fit.quantiles` | `[0.05,...,0.95]` | per-quantile execution (`R/unified/stages/stage_fit.R:67-76`) |
| `models.exdqlm_univar.implementation_mode`, `models.ndlm_main.implementation_mode` | `theory_aligned` | family runner dispatch (`R/unified/stages/stage_fit.R`) |
| `fit.warm_start.enabled` | `false` | forwarded as `DISC_USE_PREV` env (`R/unified/stages/stage_fit.R:80`) |
| `inputs.fit.*_path` | `null` | validated in `R/unified/config.R:210-215`; consumed in fit/post adapters |
| `inputs.fit.*_storage_scale` | `log1p_cms` | adapter conversion in fit/post (`R/unified/stages/stage_fit.R:18-61`, `R/unified/stages/stage_post.R:16-59`) |
| `post.profile`, `post.profile_detail` | `false` | post runner env vars (`R/unified/stages/stage_post.R:73-74`) |
| `post.sort_keep_na`, `post.export_tables` | `true` | post runner env vars (`R/unified/stages/stage_post.R:66-77`) |
| `validation.profile` | `production` | validator policy intent stored in manifest metadata (`R/unified/manifest.R`) and consumed by external validator |
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

### 14.4 Artifact Contracts by Model Family (current unified behavior; legacy standalone defaults noted)

#### 14.4.1 Multivariate exDQLM (DISC-W, current unified fit family)

| Contract item | Current repo-grounded behavior |
|---|---|
| Producer | `R/unified/stages/stage_fit.R` calls `Rscript --vanilla scripts/run_DISC_Optimal_Synth_Ranges_W.R <q> <seed>` (`R/unified/stages/stage_fit.R:90-93`) |
| Run-scoped output file | `repro/runs/<RUN_ID>/fit/q=<QQ>/outputs/DISC_variables_<q>_exAL_synth_DISC.RData` (`R/unified/stages/stage_fit.R:72-100`) |
| RData object naming pattern | Dynamic names created in `disc_w_save_state`: `samp.gamma_<q>_exAL_synth_DISC`, `samp.sigma_<q>_exAL_synth_DISC`, `new.theta.out_<q>_exAL_synth_DISC`, etc. (`R/disc_w/05_save_state.R:22-110`) |
| Manifest reference style | `artifacts[]` entries with `storage_scale: model_state` and `flow_domain: cfg$scale_contract$analysis_scale_fit_internal` (`R/unified/stages/stage_fit.R:123-128`) |
| Post dependency today | Post receives run-scoped DISC-W paths from manifest via `stage_post`; legacy root fallback is compatibility-only in non-strict mode (`R/unified/stages/stage_post.R`, `R/environmetrics/00_paths.R`) |

#### 14.4.2 Univariate exDQLM (unified family under `fit` with mode dispatch)

| Contract item | Current repo-grounded behavior |
|---|---|
| Producer | `R/unified/stages/stage_fit.R` dispatches by `models.exdqlm_univar.implementation_mode`: theory runner `scripts/run_exdqlm_univar.R` (default) or legacy script `OptimalModelSLexAL.r` |
| Run-scoped output path | `repro/runs/<RUN_ID>/fit/exdqlm_univar/q=<QQ>/outputs/variables_<QQ>_exAL_synth_DISC_uni.RData` |
| Expected object names consumed by post | `new.theta.out_<q>_exAL_synth_DISC_uni`, `samp.theta_<q>_exAL_synth_DISC_uni` and related objects (`R/environmetrics/30_univariate_and_misc.R`) |
| Manifest reference today | Run-scoped model-state artifact is recorded in manifest `artifacts[]` |
| Legacy standalone default | If `OptimalModelSLexAL.r` is run outside unified wrappers, default output remains root-scoped unless env override is provided |

#### 14.4.3 NDLM (unified family under `fit` with mode dispatch)

| Contract item | Current repo-grounded behavior |
|---|---|
| Producer | `R/unified/stages/stage_fit.R` dispatches by `models.ndlm_main.implementation_mode`: theory runner `scripts/run_ndlm_main.R` (default) or legacy script `DISC_Optimal_Synth_Ranges_NDLM.r` |
| Run-scoped output path | `repro/runs/<RUN_ID>/fit/ndlm_main/outputs/DISC_variables_50_NDLM_synth_DISC.RData` (validator also accepts neutral aliases such as `ndlm_main_state.RData` / `ndlm_main_*.RData`) |
| Expected object names consumed by post | `new.theta.out_50_NDLM_synth_DISC`, `samp.theta_50_NDLM_synth_DISC`, `samp.sigma_50_NDLM_synth_DISC` (compat aliases still provided for current post contracts) |
| Manifest reference today | Run-scoped model-state artifact is recorded in manifest `artifacts[]` |
| Legacy standalone default | If `DISC_Optimal_Synth_Ranges_NDLM.r` is run outside unified wrappers, default output remains root-scoped unless env override is provided |

#### 14.4.4 Manifest mapping proposal constrained to current schema

Current manifest schema does not have a `family` field in `artifacts[]` (`R/unified/manifest.R:115-126`).  
Implementation-safe mapping for multi-model migration should therefore be path-prefix based:

1. `fit/exdqlm_multivar/q=<QQ>/outputs/*.RData`
2. `fit/exdqlm_univar/q=<QQ>/outputs/*.RData`
3. `fit/ndlm_main/outputs/*.RData`

Open question: whether to add explicit `family` field in manifest v2 vs retain path-prefix inference.

### 14.5 Post-Processing Dependency Map (legacy fallback surfaces; strict mode uses run-scoped env paths)

| File:line | Load/read pattern | Expected artifacts/objects | Run-scoping risk |
|---|---|---|---|
| `R/environmetrics/00_paths.R` | Resolves run-scoped env paths first; root fallback only if strict mode is off and fallback is allowed | univar/NDLM/DISC-W `.RData` | Conditional legacy fallback |
| `R/environmetrics/30_univariate_and_misc.R` | `load(UNI_VAR_*)` and related model-state loads after path resolution in `00_paths.R` | post-consumed posterior objects | Conditional legacy fallback (non-strict compatibility path) |
| `R/environmetrics/40_figures.R:4151` | `readRDS("y_reps_f.rds")` | intermediate posterior arrays | Relative path dependency |
| `R/environmetrics/40_figures.R:4316` | `readRDS("y_reps_f_new.rds")` | intermediate posterior arrays | Relative path dependency |
| `R/environmetrics/40_figures.R:4483` | `readRDS("y_reps_new.rds")` | intermediate posterior arrays | Relative path dependency |

Recommendation for continuing hardening:

1. Keep strict run-scoped mode as default for production runs.
2. Continue reducing compatibility fallback surface in non-strict paths.
3. Keep family-separated output folders as already decided in D-006.

### 14.6 Legacy Bridge Execution Semantics (current reality)

1. DISC-W bridge (already unified): `stage_fit` runs wrapper `scripts/run_DISC_Optimal_Synth_Ranges_W.R`, which sources legacy script (`source("DISC_Optimal_Synth_Ranges_W.r", chdir=TRUE)`), injecting run-scoped input/output paths through `DISC_W_*` env vars (`R/unified/stages/stage_fit.R:78-96`, `scripts/run_DISC_Optimal_Synth_Ranges_W.R:32-39`, `R/disc_w/01_paths_inputs.R:16-27`).
2. Post bridge (already unified): `stage_post` runs `scripts/run_environmetrics_figures.R` with env overrides for run root + adapted CSV paths (`R/unified/stages/stage_post.R:70-91`, `scripts/run_environmetrics_figures.R:11-27`).
3. Univariate execution in unified runs: `stage_fit` dispatches to `scripts/run_exdqlm_univar.R` (`theory_aligned`) or `OptimalModelSLexAL.r` (`legacy_bridge`) with run-scoped env-overridden inputs/outputs.
4. NDLM execution in unified runs: `stage_fit` dispatches to `scripts/run_ndlm_main.R` (`theory_aligned`) or `DISC_Optimal_Synth_Ranges_NDLM.r` (`legacy_bridge`) with run-scoped env-overridden inputs/outputs.
5. Standalone legacy launchers (`run_scripts_SL.py`, direct legacy Rscript usage) remain outside unified-run reproducibility guarantees unless explicitly routed to run-scoped paths.

### 14.7 Run-Scoping + Collision Audit (current state)

#### 14.7.1 Hardcoded/root write points

1. Legacy univariate/NDLM scripts still have root-default output behavior when run standalone.
2. Unified `stage_fit` overrides legacy script IO paths to run-scoped outputs under `repro/runs/<RUN_ID>/fit/...`.
3. DISC-W warm-start can still pull root `DISC_variables_*` if warm-start is enabled without run-scoped source control.
4. Post legacy root fallback remains available only in non-strict mode when explicitly allowed.
5. Forecats build mode still uses external forecats outputs as source-of-copy, then snapshots required artifacts into run root.

#### 14.7.2 Current run tree convention to preserve

Current unified outputs use:

- `repro/runs/<RUN_ID>/fit/q=<QQ>/outputs/...`
- `repro/runs/<RUN_ID>/fit/exdqlm_univar/q=<QQ>/outputs/...` (when univar family enabled)
- `repro/runs/<RUN_ID>/fit/ndlm_main/outputs/...` (when NDLM family enabled)
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

### Progress Update 2026-02-14 01:08 UTC
- Phase: P8C
- Change type: operations
- Summary: executed active-run-safe storage cleanup audit + dry-run policy assessment; applied only one high-confidence deletion (stale temp `.tmp` artifact outside active run root) with before/after evidence capture.
- Commands run:
  - `git status -sb`
  - `git rev-parse --abbrev-ref HEAD`
  - `df -h /data && df -i /data`
  - `pgrep -fa "prod_canonical_p8c_20260213_162304|/tmp/prod_canonical_p8c_20260213_162304.yaml|run_DISC_Optimal_Synth_Ranges_W.R"`
  - `repro/tools/cleanup_runs.sh --inventory-only ...`
  - `repro/tools/cleanup_runs.sh --dry-run --thin-failed --inventory-root-rdata ...`
  - `repro/tools/cleanup_runs.sh --dry-run --thin-failed --include-baseline --thin-baseline --inventory-root-rdata ...`
  - `rm repro/runs/prod_canonical_p8b_template/fit/q=10/outputs/DISC_variables_10_exAL_synth_DISC.RData.tmp.2161922`
- Evidence paths:
  - `repro/reports/cleanup_runs/20260213_170344_p8c_safe_cleanup/00_preflight.txt`
  - `repro/reports/cleanup_runs/20260213_170344_p8c_safe_cleanup/01_files_ge_1GiB.tsv`
  - `repro/reports/cleanup_runs/20260213_170344_p8c_safe_cleanup/02_top_dirs_by_size.tsv`
  - `repro/reports/cleanup_runs/20260213_170344_p8c_safe_cleanup/05_baseline_disc_q50_hash_groups.tsv`
  - `repro/reports/cleanup_runs/20260213_170344_p8c_safe_cleanup/policy_dryrun_main/20260214_010627_dryrun.json`
  - `repro/reports/cleanup_runs/20260213_170344_p8c_safe_cleanup/policy_dryrun_with_baseline/20260214_010627_dryrun.json`
  - `repro/reports/cleanup_runs/20260213_170344_p8c_safe_cleanup/09_apply_high_confidence_cleanup.txt`
  - `repro/reports/cleanup_runs/20260213_170344_p8c_safe_cleanup/10_cleanup_summary.md`
- Reclaimed space:
  - Exact removed bytes: `1812216257` (`1.687758 GiB`)
  - Disk snapshot: `/data` moved from `800G used / 70G avail` to `798G used / 72G avail`.
- Intentionally not touched:
  - Active run root `repro/runs/prod_canonical_p8c_20260213_162304` (in-progress process confirmed before/after).
  - Protected runs in `repro/protected_runs.yaml`.
  - Baseline duplicates and root-level legacy `.RData` families (classified `REVIEW_FIRST`).
- New risks:
  - None introduced; no model/fit/post/validator code or semantics changed.
- Next action:
  - If additional reclaim is needed, execute an explicitly approved baseline dedupe-by-hash plan with rollback safeguards.

### Progress Update 2026-02-14 01:31 UTC
- Phase: P8C
- Change type: operations
- Summary: executed aggressive run-artifact cleanup in `repro/` + `repro/baseline_runs` for storage control; deleted heavy generated run products while explicitly excluding active canonical/proof run roots.
- Scope deleted:
  - `repro/baseline_runs/*/inputs/DISC_variables_50_exAL_synth_DISC.RData`
  - `repro/runs|repro/quarantine fit/*/outputs/*.RData|*.rds` (non-excluded runs)
  - `repro/runs/*/inputs/shared/forecats_bundle` (non-excluded runs)
- Exclusions:
  - `repro/runs/prod_canonical_p8c_20260213_162304`
  - `repro/runs/prod_proof_q3_20260214_010911`
- Reclaimed space:
  - `332314584807` bytes (`309.492075 GiB`)
  - `/data`: `798G used / 72G avail` -> `489G used / 381G avail`
- Evidence paths:
  - `repro/reports/cleanup_runs/20260213_172450_aggressive_repro_cleanup/apply_cleanup.log`
  - `repro/reports/cleanup_runs/20260213_172450_aggressive_repro_cleanup/deleted_paths.tsv`
  - `repro/reports/cleanup_runs/20260213_172450_aggressive_repro_cleanup/apply_deleted_summary.txt`
  - `repro/reports/cleanup_runs/20260213_172450_aggressive_repro_cleanup/CLEANUP_REFERENCE_REPORT_2026-02-13.md` (kept untracked by request)
- New risks:
  - deleted run-generated heavy artifacts are not locally recoverable unless regenerated.
- Next action:
  - keep active run protections; if needed, perform a smaller second-pass prune of low-value run logs/caches only.

### Progress Update 2026-02-14 06:53 UTC
- Phase: P8C
- Change type: operations+validation
- Summary: salvaged `prod_proof_q3_20260214_010911` without refit by re-running only `post+validate+report` from the run-scoped resolved config via temporary overlay (`fit/forecats/data_prep_shared` disabled); manifest is now closed with `validation.status: pass`. Performed failed-run cleanup tooling dry-run+apply (`--thin-failed`) and confirmed no remaining reclaimable heavy failed-run fit outputs under current `repro/runs` scan.
- Files touched:
  - `/tmp/salvage_prod_proof_q3_20260214_010911.yaml` (temp runtime config; not committed)
  - `repro/UNIFIED_MULTIMODEL_WORKFLOW_TRACKER.md`
  - run-scoped artifacts under `repro/runs/prod_proof_q3_20260214_010911/**`
  - cleanup reports under `repro/reports/cleanup_runs/**`
  - validator reports under `repro/reports/validator/**`
- Evidence paths:
  - `repro/runs/prod_proof_q3_20260214_010911/run_manifest.yaml`
  - `repro/runs/prod_proof_q3_20260214_010911/post/logs/post_runner.log`
  - `repro/runs/prod_proof_q3_20260214_010911/validate/compare_report.json`
  - `repro/runs/prod_proof_q3_20260214_010911/report/summary.md`
  - `repro/runs/prod_proof_q3_20260214_010911/report/summary.json`
  - `repro/runs/prod_proof_q3_20260214_010911/validate/write_audit/post/fs_diff.patch`
  - `repro/runs/prod_proof_q3_20260214_010911/validate/write_audit/validate/fs_diff.patch`
  - `repro/runs/prod_proof_q3_20260214_010911/validate/write_audit/report/fs_diff.patch`
  - `repro/reports/validator/prod_proof_q3_20260214_010911_auto.txt`
  - `repro/reports/validator/prod_proof_q3_20260214_010911_production_proof.txt`
  - `repro/reports/cleanup_runs/thin_failed_dryrun_stdout.txt`
  - `repro/reports/cleanup_runs/thin_failed_apply_stdout.txt`
  - `repro/reports/cleanup_runs/20260214_065206_dryrun.log`
  - `repro/reports/cleanup_runs/20260214_065244_apply.log`
- Validation notes:
  - Salvage run closure: `timestamps.finished_at_utc: 2026-02-14T06:51:43Z`.
  - Manifest validation status: `pass`.
  - `validate_run.sh` PASS for both `--profile auto` and `--profile production_proof`.
  - Write-audit patches for post/validate/report are all `0` bytes; historical fit diff remains non-empty from the original interrupted fit window.
  - `find repro/runs -type f -size +1G` now shows only the retained proof-run multivariate artifacts (`q=05,50,95`).
- Next action:
  - Keep canonical run closure as separate workstream; this salvage/proof run is now operationally complete and validated under `production_proof`.

### Progress Update 2026-02-14 07:08 UTC
- Phase: P8C
- Change type: operations
- Summary: on maintainer request, canceled active canonical run (`prod_canonical_p8c_20260214_070148`) to speed iteration, deleted its partial run root outputs, and relaunched a fresh 3-quantile full workflow proof run with quantiles `[0.05, 0.50, 0.95]` under `validation.profile=production_proof`.
- Files touched:
  - `repro/UNIFIED_MULTIMODEL_WORKFLOW_TRACKER.md`
  - deleted run root: `repro/runs/prod_canonical_p8c_20260214_070148/`
  - new run root: `repro/runs/prod_proof_q3_20260214_070801/`
  - temp runtime config/log (outside repo): `/tmp/prod_proof_q3_20260214_070801.yaml`, `/tmp/prod_proof_q3_20260214_070801_unified_run.log`
- Evidence paths:
  - deleted previous run root confirmation: `repro/runs/prod_canonical_p8c_20260214_070148/` (removed)
  - new run manifest: `repro/runs/prod_proof_q3_20260214_070801/run_manifest.yaml`
  - new resolved config: `repro/runs/prod_proof_q3_20260214_070801/resolved_config.yaml`
  - new fit q05 log: `repro/runs/prod_proof_q3_20260214_070801/fit/q=05/logs/fit.log`
  - new fit q50 log: `repro/runs/prod_proof_q3_20260214_070801/fit/q=50/logs/fit.log`
  - new fit q95 log: `repro/runs/prod_proof_q3_20260214_070801/fit/q=95/logs/fit.log`
- Validation notes:
  - Relaunch executed in tmux session `q3_run_20260214_070801`.
  - New run is active and currently in `fit`; no stop condition triggered at launch.
  - Target quantiles are explicitly limited to `0.05, 0.50, 0.95` for this rerun.
- Next action:
  - Continue health checks until run closure, then execute `validate_run.sh` with `--profile auto` and `--profile production_proof`.

### Progress Update 2026-02-14 21:48 UTC
- Phase: P8C
- Change type: decision+operations
- Summary: executed read-only P8C gate and selected Path A (fresh canonical closure run) because blocker thresholds were not met; prepared untracked canonical overlay with unique run id and canonical invariants preserved.
- Files touched:
  - `repro/UNIFIED_MULTIMODEL_WORKFLOW_TRACKER.md`
- Run id:
  - `prod_canonical_p8c_20260214_214849_r01`
- Evidence paths:
  - `repro/runs/prod_proof_q3_20260214_070801/run_manifest.yaml`
  - `repro/runs/prod_canonical_p8b_template/run_manifest.yaml`
  - `repro/runs/prod_canonical_p8c_20260213_162304/run_manifest.yaml`
  - `config/unified_runs/production_canonical_family.yaml`
  - `/tmp/prod_canonical_p8c_20260214_214849_r01.yaml`
- Validation notes:
  - Gate outputs: `/data` free `337G`, inode usage `4%`, no active unified run workers found.
  - Canonical config invariants confirmed in overlay: `fit.quantiles=[0.01,0.05,0.10,0.50,0.90,0.95,0.99]`, `validation.profile=production`, all families enabled, `write_audit.enforce_from_stage=4`.
  - Existing proof run remains closed/pass under `production_proof`; prior canonical attempts remain open/pending.
- Next action:
  - Launch canonical run in tmux from `/tmp/prod_canonical_p8c_20260214_214849_r01.yaml`, then run external validator checks (`--profile auto` and `--profile production`) after closure.

### Progress Update 2026-02-14 22:06 UTC
- Phase: P8C
- Change type: operations
- Summary: executed the planned Path A launch after the 21:48 decision gate; canonical run is active in tmux and currently in fit. Clarified runtime overlay location as untracked `/tmp` path.
- Files touched:
  - `repro/UNIFIED_MULTIMODEL_WORKFLOW_TRACKER.md`
- Run id:
  - `prod_canonical_p8c_20260214_214849_r01`
- Evidence paths:
  - `/tmp/prod_canonical_p8c_20260214_214849_r01.yaml`
  - `/tmp/prod_canonical_p8c_20260214_214849_r01_unified_run.log`
  - `repro/runs/prod_canonical_p8c_20260214_214849_r01/run_manifest.yaml`
  - `repro/runs/prod_canonical_p8c_20260214_214849_r01/resolved_config.yaml`
  - `repro/runs/prod_canonical_p8c_20260214_214849_r01/fit/q=01/logs/fit.log`
- Validation notes:
  - Overlay config is not tracked and is outside repo root (`/tmp/...yaml`).
  - Manifest stage status at check time: `forecats=pass`, `data_prep_shared=pass`, `fit=pending/running`, `post/validate/report=pending`.
- Next action:
  - Continue health checks to closure, then run external validator checks (`--profile auto`, `--profile production`) and capture reports under `repro/reports/validator/`.

### Progress Update 2026-02-14 22:37 UTC
- Phase: P9
- Change type: decision+planning
- Summary: added dedicated P9 extreme-quantile stabilization phase after q=0.01 multivar failure evidence (`L-BFGS-B needs finite values of 'fn'` in q=01 fit log). Locked P9 execution order as theory-first -> isolated reproducer -> diagnostics-first mitigation, with default model semantics preserved unless explicit opt-in flags are enabled.
- Files touched:
  - `repro/UNIFIED_MULTIMODEL_WORKFLOW_TRACKER.md`
- Evidence paths:
  - `repro/runs/prod_canonical_p8c_20260214_214849_r01/run_manifest.yaml`
  - `repro/runs/prod_canonical_p8c_20260214_214849_r01/fit/q=01/logs/fit.log`
  - `/tmp/prod_canonical_p8c_20260214_214849_r01_unified_run.log`
- Validation notes:
  - No model/fit/post code semantics were changed in this update.
  - P9 tasks were added to enforce clean stop, safe cleanup, and single-quantile isolation before attempting mitigations.
- Next action:
  - Begin P9-T01 by stopping only run-id-scoped processes for `prod_canonical_p8c_20260214_214849_r01`, then preserve forensic artifacts before cleanup and isolation reruns.

### Progress Update 2026-02-14 23:00 UTC
- Phase: P9
- Change type: implementation+validation+operations
- Summary: implemented opt-in extreme-quantile stabilization controls for DISC-W multivar gamma/sigma updates (default semantics unchanged), including config-schema support, fit-stage env wiring, objective finite/domain guardrails, and warmup freeze iterations; added isolated q=0.01 debug config and regression tests; launched deterministic isolated reproducer run with canonicalized shared inputs.
- Files touched:
  - `R/unified/config.R`
  - `R/unified/stages/stage_fit.R`
  - `DISC_Optimal_Synth_Ranges_W.r`
  - `config/unified_run.template.yaml`
  - `config/unified_runs/debug_q01_multivar_extreme.yaml`
  - `repro/tests/test_config_extreme_quantile_stabilization.py`
  - `repro/UNIFIED_MULTIMODEL_WORKFLOW_TRACKER.md`
- Evidence paths:
  - `repro/reports/failures/prod_canonical_p8c_20260214_214849_r01_20260214T224804Z/fit_q01.log`
  - `repro/quarantine/failed_runs/prod_canonical_p8c_20260214_214849_r01_20260214T224824Z/QUARANTINE_INDEX.md`
  - `/tmp/debug_q01_extreme_20260214_225450.yaml`
  - `repro/runs/debug_q01_extreme_20260214_225450/run_manifest.yaml`
  - `/tmp/debug_q01_extreme_20260214_225559_r02.yaml`
  - `repro/runs/debug_q01_extreme_20260214_225559_r02/run_manifest.yaml`
  - `repro/runs/debug_q01_extreme_20260214_225559_r02/fit/q=01/logs/fit.log`
- Validation notes:
  - Targeted regression tests passed:
    - `python3 -m unittest repro.tests.test_config_extreme_quantile_stabilization repro.tests.test_config_implementation_mode_defaults repro.tests.test_stage_fit_parallel_guard repro.tests.test_production_canonical_family_config -v`
  - R parse checks passed for modified files:
    - `R/unified/config.R`
    - `R/unified/stages/stage_fit.R`
    - `DISC_Optimal_Synth_Ranges_W.r`
  - First isolated attempt (`debug_q01_extreme_20260214_225450`) failed pre-fit due input adapter non-finite GloFAS values; second attempt (`debug_q01_extreme_20260214_225559_r02`) launched with `forecats + data_prep_shared` and reached fit execution for q=0.01.
- Next action:
  - Let isolated run `debug_q01_extreme_20260214_225559_r02` finish, then inspect q=0.01 fit outcome, run validator/report where applicable, and decide whether freeze iteration count can be reduced while keeping q=0.01 stable.

### Progress Update 2026-02-15 00:35 UTC
- Phase: P9
- Change type: implementation+operations
- Summary: canceled active isolated q=0.01 reproducer and moved its run roots to quarantine for clean restart; upgraded extreme-quantile stabilization from fixed-penalty/fixed-freeze to adaptive policy controls (guard-trigger refreeze windows, selectable freeze target `gamma_sigma|states`, and robust gamma/sigma initialization mode) while keeping default semantics unchanged unless opt-in config keys are enabled.
- Files touched:
  - `R/unified/config.R`
  - `R/unified/stages/stage_fit.R`
  - `DISC_Optimal_Synth_Ranges_W.r`
  - `config/unified_run.template.yaml`
  - `config/unified_runs/debug_q01_multivar_extreme.yaml`
  - `config/unified_runs/debug_q01_multivar_extreme_states.yaml`
  - `repro/tests/test_config_extreme_quantile_stabilization.py`
  - `repro/UNIFIED_WORKFLOW_README.md`
  - `repro/UNIFIED_MULTIMODEL_WORKFLOW_TRACKER.md`
- Evidence paths:
  - `repro/quarantine/cleanup_runs/20260215T002430Z/debug_q01_extreme_20260214_225450/`
  - `repro/quarantine/cleanup_runs/20260215T002430Z/debug_q01_extreme_20260214_225559_r02/`
  - `repro/quarantine/cleanup_runs/20260215T002430Z/debug_q01_extreme_20260214_225559_r02/fit/q=01/logs/fit.log`
- Validation notes:
  - Prior fixed warmup path showed guard hit immediately after thaw (`iter=121`), motivating adaptive refreeze controls.
  - New controls are opt-in and default-safe:
    - `freeze_target` default `gamma_sigma`
    - `guard_refreeze_iters` default `0`
    - `objective_guard.mode` default `penalty`
    - `init.mode` default `legacy`
- Next action:
  - Commit + push this P9 adaptive policy batch, then execute tests and run two isolated q=0.01 proofs (`gamma_sigma` freeze target vs `states` freeze target) to compare stability outcomes.

### Progress Update 2026-02-15 22:52 UTC
- Phase: P9
- Change type: implementation+validation
- Summary: promoted adaptive gamma/sigma stabilization to default for both exDQLM multivariate and exDQLM univariate paths; aligned unified config defaults, fit-stage env wiring/fallbacks, univariate theory-runner policy ingestion, and docs/tests. Multivar fallback defaults were also aligned in `DISC_Optimal_Synth_Ranges_W.r` for standalone execution consistency.
- Files touched:
  - `R/unified/config.R`
  - `config/unified_run.template.yaml`
  - `R/unified/stages/stage_fit.R`
  - `scripts/run_exdqlm_univar.R`
  - `R/unified/families/exdqlm_univar/00_constants.R`
  - `R/unified/families/exdqlm_univar/03_updates_vb_or_fitloop.R`
  - `R/unified/families/exdqlm_univar/zz_run.R`
  - `DISC_Optimal_Synth_Ranges_W.r`
  - `repro/tests/test_config_extreme_quantile_stabilization.py`
  - `repro/UNIFIED_WORKFLOW_README.md`
  - `repro/UNIFIED_MULTIMODEL_WORKFLOW_TRACKER.md`
- Validation checks run:
  - `python3 -m unittest repro.tests.test_config_extreme_quantile_stabilization repro.tests.test_config_implementation_mode_defaults repro.tests.test_production_canonical_family_config repro.tests.test_stage_fit_parallel_guard -v`
  - `python3 -m unittest discover -s repro/tests -p 'test_*.py'`
  - `Rscript -e "testthat::test_dir('tests/testthat', reporter='summary')"`
  - `Rscript -e "parse(file='R/unified/config.R'); parse(file='R/unified/stages/stage_fit.R'); parse(file='scripts/run_exdqlm_univar.R'); parse(file='R/unified/families/exdqlm_univar/00_constants.R'); parse(file='R/unified/families/exdqlm_univar/03_updates_vb_or_fitloop.R'); parse(file='R/unified/families/exdqlm_univar/zz_run.R'); parse(file='DISC_Optimal_Synth_Ranges_W.r'); cat('R_PARSE_OK\\n')"`
- Validation notes:
  - Targeted and full Python test suites passed.
  - `tests/testthat` suite passed.
  - No model-family toggles changed (`models.run_exdqlm_univar` remains default `false`); defaults apply when each family is enabled.
- Next action:
  - Continue P9 closure via isolated q=0.01 convergence evidence under the new defaults, then run q=0.05 sanity before broader proof runs.

### Progress Update 2026-02-16 19:56 UTC
- Phase: P9
- Change type: validation+monitoring
- Summary: refreshed live trace visualizations for current extreme-quantile monitoring runs (univariate and multivariate) using the latest `gamsig_progress` logs, and captured current run-state evidence. Multivariate `q=50` and `q=99` reached completion with saved outputs; multivariate `q=01` halted with a matrix-dimension error in `DISC_update_theta_synth_cpp_W`.
- Files touched:
  - `repro/UNIFIED_MULTIMODEL_WORKFLOW_TRACKER.md`
- Evidence paths:
  - `repro/reports/figures/univar_trace_matrix_q010599_live_enhanced_20260216_195533Z.png`
  - `repro/reports/figures/multivar_trace_matrix_q010599_live_enhanced_20260216_195533Z.png`
  - `repro/runs/debug_extreme_mv_q010599_parallel_20260216_034312/fit/q=01/logs/fit.log`
  - `repro/runs/debug_extreme_mv_q010599_parallel_20260216_034312/fit/q=50/logs/fit.log`
  - `repro/runs/debug_extreme_mv_q010599_parallel_20260216_034312/fit/q=99/logs/fit.log`
- Validation notes:
  - Univariate latest run remains completed (`q=01` iter 75, `q=50` iter 70, `q=99` iter 75).
  - Multivariate latest run status at capture time:
    - `q=99`: iter `1000` (max-iter cap reached), output saved.
    - `q=50`: iter `145`, output saved.
    - `q=01`: halted at iter `739` with `matrix multiplication: incompatible matrix dimensions: 0x0 and 31x31`.
  - No active run was interrupted for this update.
- Next action:
  - Isolate and debug the `q=01` multivariate matrix-dimension failure path while preserving successful `q=50` and `q=99` artifacts as control references.

### Progress Update 2026-02-17 05:35 UTC
- Phase: P9
- Change type: validation+closure
- Summary: completed final isolated extreme-quantile proof runs for exDQLM multivar + univar using `fit.quantiles=[0.01,0.50,0.99]`, `mc_cores=3`, and `gamma_sigma.max_iter=800`. All six quantile jobs closed with run-scoped outputs and no hard runtime failures. Maintainer accepted operational “good enough” closure for P9.
- Files touched:
  - `repro/UNIFIED_MULTIMODEL_WORKFLOW_TRACKER.md`
- Evidence paths:
  - `repro/runs/debug_extreme_mv_q010599_parallel_max800_20260216_222144/run_manifest.yaml`
  - `repro/runs/debug_extreme_uv_q010599_parallel_max800_20260216_222436/run_manifest.yaml`
  - `repro/runs/debug_extreme_mv_q010599_parallel_max800_20260216_222144/fit/q=01/outputs/DISC_variables_1_exAL_synth_DISC.RData`
  - `repro/runs/debug_extreme_mv_q010599_parallel_max800_20260216_222144/fit/q=50/outputs/DISC_variables_50_exAL_synth_DISC.RData`
  - `repro/runs/debug_extreme_mv_q010599_parallel_max800_20260216_222144/fit/q=99/outputs/DISC_variables_99_exAL_synth_DISC.RData`
  - `repro/runs/debug_extreme_uv_q010599_parallel_max800_20260216_222436/fit/exdqlm_univar/q=01/outputs/variables_01_exAL_synth_DISC_uni.RData`
  - `repro/runs/debug_extreme_uv_q010599_parallel_max800_20260216_222436/fit/exdqlm_univar/q=50/outputs/variables_50_exAL_synth_DISC_uni.RData`
  - `repro/runs/debug_extreme_uv_q010599_parallel_max800_20260216_222436/fit/exdqlm_univar/q=99/outputs/variables_99_exAL_synth_DISC_uni.RData`
  - `repro/reports/figures/debug_extreme_mv_q010599_parallel_max800_20260216_222144_trace_summary_latest.png`
  - `repro/reports/figures/debug_extreme_uv_q010599_parallel_max800_20260216_222436_trace_summary_latest.png`
- Validation notes:
  - Multivar run finished with stage status `fit=pass`, `timestamps.finished_at_utc: 2026-02-17T04:40:00Z`.
  - Univar run finished with stage status `fit=pass`, `timestamps.finished_at_utc: 2026-02-16T23:15:17Z`.
  - Extremes (`q=0.01`, `q=0.99`) closed at `iter=800` under adaptive guardrails with output artifacts present; no `Execution halted` markers in final proof logs.
- Next action:
  - Move focus to remaining unified-workflow closure items (P8 canonical production evidence, P4 NDLM theory completeness, and P7 validator/report hardening).

### Progress Update 2026-02-17 05:56 UTC
- Phase: C1 baseline gate
- Change type: validation
- Summary: pre-execution baseline verified against current tracker claims. Confirmed P9 closure evidence exists and resolves, and confirmed remaining closure scope is still P8C + P4 + P7 + P5 follow-up + P8 packaging.
- Files touched:
  - `repro/UNIFIED_MULTIMODEL_WORKFLOW_TRACKER.md`
- Evidence paths:
  - `repro/runs/debug_extreme_mv_q010599_parallel_max800_20260216_222144/run_manifest.yaml`
  - `repro/runs/debug_extreme_uv_q010599_parallel_max800_20260216_222436/run_manifest.yaml`
  - `repro/reports/figures/debug_extreme_mv_q010599_parallel_max800_20260216_222144_trace_summary_latest.png`
  - `repro/reports/figures/debug_extreme_uv_q010599_parallel_max800_20260216_222436_trace_summary_latest.png`
  - `config/unified_runs/production_canonical_family.yaml`
- Validation notes:
  - Multivar proof manifest: `fit=pass`, `finished_at_utc=2026-02-17T04:40:00Z`.
  - Univar proof manifest: `fit=pass`, `finished_at_utc=2026-02-16T23:15:17Z`.
  - P9 proof outputs exist for all three tracked quantiles in both model families.
- Next action:
  - Execute C2 canonical P8C production closure run and run validator with `--profile auto` and `--profile production`.

### Progress Update 2026-02-17 06:58 UTC
- Phase: C3 (P4 closure)
- Change type: implementation+validation
- Summary: closed remaining P4 tasks by locking NDLM theory-mode regression coverage and fresh NDLM closure smoke evidence under unified runner. Marked `T-P4-02` and `T-P4-03` complete and promoted P4 to closed.
- Files touched:
  - `repro/tests/test_ndlm_theory_vb_regression.py`
  - `repro/UNIFIED_MULTIMODEL_WORKFLOW_TRACKER.md`
- Evidence paths:
  - `repro/runs/smoke_p4_ndlm_closure_20260217_065448/run_manifest.yaml`
  - `repro/runs/smoke_p4_ndlm_closure_20260217_065448/fit/ndlm_main/outputs/DISC_variables_50_NDLM_synth_DISC.RData`
  - `repro/runs/smoke_p4_ndlm_closure_20260217_065448/fit/ndlm_main/logs/ndlm_theory_summary.log`
  - `repro/runs/smoke_p4_ndlm_closure_20260217_065448/fit/contract_checks/ndlm_main/ndlm_main_contract_check.json`
- Validation notes:
  - `python3 -m unittest repro.tests.test_ndlm_theory_vb_regression -v` passed.
  - NDLM closure smoke completed with `forecats=pass`, `data_prep_shared=pass`, `fit=pass`, and non-null `finished_at_utc`.
- Next action:
  - Continue C2 canonical P8C closure monitoring and then close C4/C5/C6/C7 checklist items.

### Progress Update 2026-02-17 07:06 UTC
- Phase: C4 (P7 closure)
- Change type: validation+tests
- Summary: closed P7 validator/report hardening by adding explicit report family-summary regression coverage and re-validating production-proof gate behavior under current validator contracts.
- Files touched:
  - `repro/tests/test_stage_report_family_summary.py`
  - `repro/UNIFIED_MULTIMODEL_WORKFLOW_TRACKER.md`
- Evidence paths:
  - `repro/tests/test_stage_report_family_summary.py`
  - `repro/runs/prod_proof_p7b_20260212_225100/FAILURE_REPORT.md`
  - `/tmp/c4_validate_prodproof_20260217.log`
- Validation notes:
  - `python3 -m unittest repro.tests.test_stage_report_family_summary repro.tests.test_validate_run -v` passed.
  - External validator intentionally failed `prod_proof_p7b_20260212_225100` under current policies when family outputs were missing, confirming active family-aware gate enforcement.
- Next action:
  - Continue C2 canonical P8C closure run; apply C5 follow-up legacy-fallback policy hardening commit.

### Progress Update 2026-02-17 07:14 UTC
- Phase: C5 (P5 follow-up policy)
- Change type: implementation+validation
- Summary: resolved the non-strict legacy post fallback decision by locking an explicit deprecated compatibility switch (`post.allow_legacy_root_fallback`) and enforcing policy rejection in `production` and `production_proof` validator profiles.
- Files touched:
  - `R/unified/config.R`
  - `R/unified/stages/stage_post.R`
  - `config/unified_run.template.yaml`
  - `config/unified_runs/production_canonical_family.yaml`
  - `repro/tools/validate_run.sh`
  - `repro/tests/test_validate_run.py`
  - `repro/UNIFIED_WORKFLOW_README.md`
  - `repro/UNIFIED_MULTIMODEL_WORKFLOW_TRACKER.md`
- Evidence paths:
  - `repro/tests/test_validate_run.py`
  - `/tmp/c4_validate_prodproof_20260217.log`
  - `config/unified_run.template.yaml`
  - `config/unified_runs/production_canonical_family.yaml`
- Validation notes:
  - `python3 -m unittest repro.tests.test_stage_report_family_summary repro.tests.test_validate_run -v` passed.
  - Added explicit validator policy gate: `policy_check.legacy_post_fallback`.
- Next action:
  - Continue C2 canonical production closure monitoring and then close P8 cutover packaging/checklist finalization.

### Progress Update 2026-02-17 07:18 UTC
- Phase: C2 (P8C canonical production closure run)
- Change type: run-monitoring
- Summary: canonical production closure run remains active with strict convergence defaults (`max_iter=800`, per-component tolerances at `1e-6`) and canonical 7-quantile multivariate fit workload. No hard runtime errors observed; stages `forecats` and `data_prep_shared` are pass and `fit` is still pending.
- Files touched:
  - `repro/UNIFIED_MULTIMODEL_WORKFLOW_TRACKER.md`
- Evidence paths:
  - `repro/runs/prod_canonical_p8c_parallel_20260216_220751/run_manifest.yaml`
  - `/tmp/prod_canonical_p8c_parallel_20260216_220751_unified.log`
  - `repro/runs/prod_canonical_p8c_parallel_20260216_220751/fit/q=01/logs/fit.log`
  - `repro/runs/prod_canonical_p8c_parallel_20260216_220751/fit/q=50/logs/fit.log`
  - `repro/runs/prod_canonical_p8c_parallel_20260216_220751/fit/q=99/logs/fit.log`
- Validation notes:
  - Stage statuses at capture: `forecats=pass`, `data_prep_shared=pass`, `fit=pending`, `post=pending`, `validate=pending`, `report=pending`.
  - Iterations observed during this window: approximately `q01=113`, `q50=118`, `q99=113` with no `Execution halted`.
- Next action:
  - Continue to closure gate (`finished_at_utc` non-null), then run external validator with `--profile auto` and `--profile production`.

### Progress Update 2026-02-17 07:20 UTC
- Phase: C6 (P8 cutover packaging)
- Change type: validation+documentation
- Summary: finalized cutover packaging consistency around theory-aligned defaults and deprecated fallback controls, and captured a release-readiness smoke run with full stage closure plus external validator PASS on `auto` and `production` profiles.
- Files touched:
  - `repro/UNIFIED_MULTIMODEL_WORKFLOW_TRACKER.md`
- Evidence paths:
  - `repro/runs/smoke_c6_packaging_20260217_070653/run_manifest.yaml`
  - `repro/runs/smoke_c6_packaging_20260217_070653/validate/compare_report.json`
  - `repro/runs/smoke_c6_packaging_20260217_070653/report/summary.json`
  - `/tmp/c6_validate_auto_20260217.log`
  - `/tmp/c6_validate_production_20260217.log`
- Validation notes:
  - Smoke run closed with `forecats=pass`, `data_prep_shared=pass`, `fit=pass`, `post=pass`, `validate=pass`, `report=pass`, and non-null `finished_at_utc`.
  - External validator PASS confirmed for both `--profile auto` and `--profile production` on this release-readiness smoke run.
- Next action:
  - Complete C2 canonical production closure and run C7 final self-consistency pass.

### Progress Update 2026-02-17 07:23 UTC
- Phase: C7 (final closure pass, interim)
- Change type: tracker-audit
- Summary: performed a self-consistency pass across phase table, backlog checkboxes, risk/decision register, evidence pointers, and immediate next actions. Internal consistency is restored for completed items (C1/C3/C4/C5/C6); only C2 remains open and blocks full terminal closure state.
- Files touched:
  - `repro/UNIFIED_MULTIMODEL_WORKFLOW_TRACKER.md`
- Evidence paths:
  - `repro/UNIFIED_MULTIMODEL_WORKFLOW_TRACKER.md`
  - `repro/runs/prod_canonical_p8c_parallel_20260216_220751/run_manifest.yaml`
- Validation notes:
  - P4, P7 task rows and detailed checklist items now agree (`[x]`) with committed evidence/tests.
  - P8 remains `[~]` because canonical closure evidence run (`T-P8-04`) is still in progress.
  - Immediate-next-actions now focus exclusively on C2 closure and final post-C2 audit.
- Next action:
  - Finalize C2 closure and then perform the terminal C7 pass to mark full tracker closure state.

### Progress Update 2026-02-17 19:26 UTC
- Phase: C2/P8C monitoring follow-up
- Change type: validation+documentation
- Summary: added a compact canonical-run health snapshot table to close the live-checkpoint documentation gap and refreshed all-family trace figures for the canonical production run (univariate, multivariate, NDLM) from latest logs.
- Files touched:
  - `repro/UNIFIED_MULTIMODEL_WORKFLOW_TRACKER.md`
  - `repro/tools/plot_unified_trace_summaries.py`
- Evidence paths:
  - `repro/runs/prod_canonical_p8c_parallel_20260216_220751/run_manifest.yaml`
  - `repro/reports/figures/prod_canonical_p8c_parallel_20260216_220751_univar_trace_summary_latest.png`
  - `repro/reports/figures/prod_canonical_p8c_parallel_20260216_220751_multivar_trace_summary_latest.png`
  - `repro/reports/figures/prod_canonical_p8c_parallel_20260216_220751_ndlm_trace_summary_latest.png`
  - `repro/tools/plot_unified_trace_summaries.py`
- Validation notes:
  - Manifest confirms canonical run closure with `finished_at_utc=2026-02-17T13:40:00Z` and `validation.status=pass`.
  - All enabled families have trace data captured in refreshed figures.
- Next action:
  - Continue remaining unified-workflow closure workstream items using this canonical health snapshot as baseline.

### Progress Update 2026-02-17 21:46 UTC
- Phase: Post-replay NDLM blocker triage
- Change type: validation+planning
- Summary: documented current post-only replay failure state for full-figures runs and locked an isolated NDLM-first debug lane. Latest replay progressed deep into `40_figures.R` and now fails in NDLM JSD computation (`array(..., dim=dim_p)` with empty `dim_p`), indicating a downstream shape/contract issue beyond previously fixed NDLM forecast-window indexing mismatches.
- Files touched:
  - `repro/UNIFIED_MULTIMODEL_WORKFLOW_TRACKER.md`
- Evidence paths:
  - `repro/runs/post_replay_p8c_fullfig_20260217_120550/post/logs/post_runner.log` (original NDLM subscript OOB failure)
  - `repro/runs/post_replay_p8c_fullfig_fix_20260217_203611_r01/post/logs/post_runner.log` (intermediate non-conformable projection failure)
  - `repro/runs/post_replay_p8c_fullfig_fix_20260217_205632_r02/post/logs/post_runner.log` (current NDLM JSD failure: `dims cannot be of length 0`)
  - `repro/runs/post_replay_p8c_fullfig_fix_20260217_205632_r02/run_manifest.yaml` (post status fail; deep artifact generation completed before terminal error)
- Validation notes:
  - No active post replay process remained at capture time.
  - Latest failed run produced substantial post artifacts, confirming the blocker is localized in later `40_figures.R` NDLM/JSD path, not early figure wiring.
- Next action:
  - Execute isolated NDLM post-debug plan with strict invariants (shape contracts, theory-consistent transformations, no superficial patches) and close replay with post stage PASS.

## 15) Audit Report (2026-02-14)

### 15.1 Inconsistencies Found and Fixed

- Tracker stated univariate/NDLM were only legacy bridge calls and not first-class unified stages; corrected to reflect current `implementation_mode` dispatch with theory-aligned defaults and legacy fallback.
- Decision D-005 used stale key `models.run_ndlm`; corrected to `models.run_ndlm_main`.
- Validation `auto` profile rules in §11.2 were stale (`validation.smoke=true` inference); corrected to match current validator logic (explicit profile wins, else quantile-based inference, missing quantiles fail).
- Appendix stage-contract table omitted `data_prep_shared` and underreported fit outputs; corrected to include current stage order and family-specific output paths.
- Appendix artifact and bridge sections labeled legacy-only behaviors as current unified behavior; corrected to distinguish unified run-scoped behavior vs standalone legacy defaults.
- Post-dependency section implied unconditional root dependence; corrected to conditional non-strict fallback with strict-mode run-scoped enforcement.
- Immediate-next-actions section was stale relative to active P8C run; updated to current closure and validator gate steps.

### 15.2 Remaining Ambiguities Requiring Explicit Maintainer Decision

- Final canonical production evidence closure (`T-P8-04`) remains in progress.

### Progress Update 2026-02-18 00:14 UTC
- Phase: NDLM post-replay blocker closure lane (D1-D8)
- Change type: implementation+validation
- Summary: completed root-cause-first NDLM post hardening for the full-figures replay failure chain. Baseline failures were re-verified from prior replay logs (subscript OOB, projection non-conformable, and JSD `dim` failure), NDLM shape contracts were audited against canonical artifacts, and the JSD path was replaced with dimension-safe, contract-checked helpers that support valid `d=1/2/3` error spaces with explicit keyed diagnostics.
- Files touched:
  - `R/environmetrics/02_helpers_core.R`
  - `R/environmetrics/40_figures.R`
  - `tests/testthat/test_ndlm_post_jsd.R`
  - `repro/UNIFIED_MULTIMODEL_WORKFLOW_TRACKER.md`
- Evidence paths:
  - Baseline failures:
    - `repro/runs/post_replay_p8c_fullfig_20260217_120550/post/logs/post_runner.log`
    - `repro/runs/post_replay_p8c_fullfig_fix_20260217_203611_r01/post/logs/post_runner.log`
    - `repro/runs/post_replay_p8c_fullfig_fix_20260217_205632_r02/post/logs/post_runner.log`
  - Contract/theory audit bundle:
    - `repro/runs/ndlm_post_debug_20260217T234137Z/ndlm_shape_contract_audit.md`
    - `repro/runs/ndlm_post_debug_20260217T234137Z/ndlm_observed_shapes.json`
    - `repro/runs/ndlm_post_debug_20260217T234137Z/ndlm_post_root_cause_audit.md`
    - `repro/runs/ndlm_post_debug_20260217T234137Z/baseline_jsd_dim_repro.json`
    - `repro/runs/ndlm_post_debug_20260217T234137Z/ndlm_only_jsd_replay.json`
  - Isolated NDLM replay PASS:
    - `repro/runs/post_replay_ndlm_only_smoke_20260217_234449/run_manifest.yaml`
    - `repro/runs/post_replay_ndlm_only_smoke_20260217_234449/post/logs/post_runner.log`
    - `repro/runs/post_replay_ndlm_only_smoke_20260217_234449/post/outputs/post_replay_ndlm_only_smoke_20260217_234449/All_ELBOS_DISC.png`
  - Targeted regression tests:
    - `tests/testthat/test_ndlm_post_jsd.R`
- Validation notes:
  - `Rscript --vanilla -e "testthat::test_file('tests/testthat/test_ndlm_post_jsd.R', reporter='summary')"` passed.
  - Isolated NDLM-only post replay closed with `post=pass` and non-null `finished_at_utc`.
  - Full all-family full-figures replay is running in strict post-only lane for final closure evidence:
    - `repro/runs/post_replay_fullfig_ndlmfix_20260217_234449/run_manifest.yaml` (`post=pending` at this checkpoint).
- Next action:
  - Let `post_replay_fullfig_ndlmfix_20260217_234449` close, then record terminal pass/fail evidence and finalize D7/D8 closure status.

### Progress Update 2026-02-18 01:26 UTC
- Phase: C2 (definitive canonical closure rerun)
- Change type: execution+tracking
- Summary: launched a fresh canonical production full-workflow run from `production_canonical_family.yaml` with a unique run id and confirmed live progression into fit stage. This run is now the active definitive closure lane for C2 evidence collection.
- Files touched:
  - `repro/UNIFIED_MULTIMODEL_WORKFLOW_TRACKER.md`
- Evidence paths:
  - Active run config overlay:
    - `/tmp/prod_canonical_definitive_20260217_172457_diag.yaml`
  - Active run manifest:
    - `repro/runs/prod_canonical_definitive_20260217_172457_diag/run_manifest.yaml`
  - Active run stage logs:
    - `repro/runs/prod_canonical_definitive_20260217_172457_diag/fit/q=01/logs/fit.log`
- Validation notes:
  - Current stage snapshot at capture:
    - `forecats=pass`
    - `data_prep_shared=pass`
    - `fit=pending` (active)
    - `post/validate/report=pending`
  - Process-level evidence shows active multivariate fit worker for `q=0.01`.
- Next action:
  - Continue periodic health checks until terminal closure, then run:
    - `bash repro/tools/validate_run.sh prod_canonical_definitive_20260217_172457_diag --profile auto --exit-nonzero`
    - `bash repro/tools/validate_run.sh prod_canonical_definitive_20260217_172457_diag --profile production --exit-nonzero`

### Progress Update 2026-02-18 03:50 UTC
- Phase: C2 (canonical closure rerun policy update)
- Change type: execution-policy adjustment
- Summary: deprecated interrupted serial-worker canonical attempt `prod_canonical_definitive_20260217_172457_diag` for closure purposes due excessive wall-time under `mc_cores=1` with canonical 7-quantile + 3-family workload, and relaunched the same canonical plan with safe parallel fit workers (`mc_cores=3`) to accelerate time-to-closure while preserving model semantics and stage contract behavior.
- Files touched:
  - `repro/UNIFIED_MULTIMODEL_WORKFLOW_TRACKER.md`
- Evidence paths:
  - Deprecated serial attempt:
    - `repro/runs/prod_canonical_definitive_20260217_172457_diag/run_manifest.yaml`
    - `repro/runs/prod_canonical_definitive_20260217_172457_diag/fit/q=01/logs/fit.log`
    - `/tmp/prod_canonical_definitive_20260217_172457_diag.yaml`
  - Active parallel canonical run:
    - `repro/runs/prod_canonical_parallel_mc3_diag_20260217_194948/run_manifest.yaml`
    - `repro/runs/prod_canonical_parallel_mc3_diag_20260217_194948/fit/q=01/logs/fit.log`
    - `repro/runs/prod_canonical_parallel_mc3_diag_20260217_194948/fit/q=05/logs/fit.log`
    - `repro/runs/prod_canonical_parallel_mc3_diag_20260217_194948/fit/q=10/logs/fit.log`
    - `/tmp/prod_canonical_parallel_mc3_diag_20260217_194948.yaml`
- Validation notes:
  - Parallel run shows concurrent multivariate workers for `q=01`, `q=05`, `q=10` with `fit=pending` and no hard runtime errors at capture.
  - Stage status at capture:
    - `forecats=pass`
    - `data_prep_shared=pass`
    - `fit=pending`
    - `post/validate/report=pending`
- Next action:
  - Continue periodic health checks on `prod_canonical_parallel_mc3_diag_20260217_194948`, then execute validator `--profile auto` and `--profile production` after terminal closure.

### Progress Update 2026-02-18 19:25 UTC
- Phase: C2/P8C closure update (canonical all-family parallel lane)
- Change type: evidence + status closure
- Summary: canonical all-family closure lane `prod_canonical_parallel_allmodels_20260218_040416` completed end-to-end with all stages `pass` and closed manifest timestamp (`finished_at_utc=2026-02-18T10:43:26Z`). Fit executed with `fit.parallel.mode=global_models` and `fit.parallel.workers=15` (7 multivar quantiles + 7 univar quantiles + NDLM in parallel). Validation and report both closed `pass`.
- Files touched:
  - `repro/UNIFIED_MULTIMODEL_WORKFLOW_TRACKER.md`
- Evidence paths:
  - Canonical run closure:
    - `repro/runs/prod_canonical_parallel_allmodels_20260218_040416/run_manifest.yaml`
    - `repro/runs/prod_canonical_parallel_allmodels_20260218_040416/resolved_config.yaml`
    - `repro/runs/prod_canonical_parallel_allmodels_20260218_040416/report/summary.md`
    - `repro/runs/prod_canonical_parallel_allmodels_20260218_040416/validate/compare_report.json`
    - `repro/runs/prod_canonical_parallel_allmodels_20260218_040416/validate/env_drift_report.json`
  - Fit completion evidence:
    - `repro/runs/prod_canonical_parallel_allmodels_20260218_040416/fit/q=01/logs/fit.log`
    - `repro/runs/prod_canonical_parallel_allmodels_20260218_040416/fit/q=99/logs/fit.log`
    - `repro/runs/prod_canonical_parallel_allmodels_20260218_040416/fit/exdqlm_univar/q=01/logs/univar_theory.log`
    - `repro/runs/prod_canonical_parallel_allmodels_20260218_040416/fit/exdqlm_univar/q=99/logs/univar_theory.log`
    - `repro/runs/prod_canonical_parallel_allmodels_20260218_040416/fit/ndlm_main/logs/ndlm_theory.log`
  - Post-mode clarification:
    - `repro/runs/prod_canonical_parallel_allmodels_20260218_040416/post/outputs/prod_canonical_parallel_allmodels_20260218_040416/post_smoke_marker.txt`
    - `repro/runs/prod_canonical_parallel_allmodels_20260218_040416/post/logs/post_runner.log`
- Validation notes:
  - Stage statuses are all `pass`: `forecats`, `data_prep_shared`, `fit`, `post`, `validate`, `report`.
  - No hard runtime failures in fit logs (`Error in`/`Execution halted` absent in family logs used for closure check).
  - Synthesis figure/table bundles were intentionally not produced in this canonical run because resolved post config used smoke mode:
    - `post.smoke_fast=true`
    - `post.figures=false`
    - `post.export_tables=false`
- Next action:
  - Launch a dedicated post replay from this canonical fit run with synthesis outputs enabled (`smoke_fast=false`, `figures=true`, `export_tables=true`) and then register generated multivar/univar/NDLM synthesis artifact paths.

### Progress Update 2026-02-18 20:23 UTC

- Phase: Post-synthesis completion + restartability verification (no-refit path)
- Summary:
  - Launched full post replay from canonical fit artifacts with synthesis outputs enabled and no refit:
    - `run_id=post_replay_canonical_fullprod_20260218_115313`
    - stages enabled: `post`, `validate`, `report`
    - `inputs.post.source_run_id=prod_canonical_parallel_allmodels_20260218_040416`
    - `post.smoke_fast=false`, `post.figures=true`, `post.export_tables=true`, `post.table_formats=[csv,rds]`
  - Replay is currently in `post` (long-running full-fig path, CPU-active) and already producing synthesis artifacts under run-scoped outputs.
  - Per maintainer cleanup request, quarantined previous debug/proof/replay run roots to reduce workspace clutter while preserving canonical evidence lanes.
  - Started automated restartability helper that waits for replay closure, clears only run-scoped post outputs, reruns same run id with `overwrite=true`, and writes a restartability summary JSON.
- Evidence:
  - Active replay config:
    - `/tmp/post_replay_canonical_fullprod_20260218_115313.yaml`
  - Active replay run root:
    - `repro/runs/post_replay_canonical_fullprod_20260218_115313/run_manifest.yaml`
    - `repro/runs/post_replay_canonical_fullprod_20260218_115313/post/logs/post_replay_canonical_fullprod_20260218_115313/run_log.txt`
    - `repro/runs/post_replay_canonical_fullprod_20260218_115313/post/outputs/post_replay_canonical_fullprod_20260218_115313/`
  - Cleanup quarantine batch:
    - `repro/quarantine/cleanup_runs/20260218T201412Z/CLEANUP_INDEX.md`
    - `repro/quarantine/cleanup_runs/20260218T201412Z/cleanup_summary.json`
  - Restartability helper:
    - `/tmp/post_replay_canonical_fullprod_20260218_115313_restart_helper.sh`
    - `repro/runs/post_replay_canonical_fullprod_20260218_115313/post/restartability_helper.log`
- Next action:
  - Wait for `post_replay_canonical_fullprod_20260218_115313` to close, then confirm helper-produced restartability rerun closure and register final artifact counts/paths.

### Progress Update 2026-02-20 19:57 UTC

- Phase: Post-quality diagnosis planning (NDLM + univar median + multivar synthesis/agg-discrepancy)
- Change type: validation+planning
- Summary:
  - Verified definitive canonical one-core-per-model full run closure:
    - `run_id=prod_canonical_full_e2e_parallel_onecore_20260220_002642`
    - all stages `pass` with non-null `finished_at_utc`.
  - Confirmed synthesis/figure artifacts exist under run-scoped post outputs.
  - Maintainer-raised quality issues were captured as new diagnosis scope:
    - NDLM fit/plot quality concerns.
    - Univariate exDQLM quality concerns.
    - Multivariate synthesis horizon truncation suspicion (expected vs plotted horizon mismatch).
    - Aggregated discrepancy figures (`Agg_disc_*`) showing observed discrepancy but missing fitted aggregated discrepancy overlay.
  - Opened explicit isolation-first checklist in Section 12 (`Q-00` to `Q-05`) and corresponding live risks (`R-009`, `R-010`, `R-011`).
- Files touched:
  - `repro/UNIFIED_MULTIMODEL_WORKFLOW_TRACKER.md`
- Evidence:
  - Canonical run closure:
    - `repro/runs/prod_canonical_full_e2e_parallel_onecore_20260220_002642/run_manifest.yaml`
    - `repro/runs/prod_canonical_full_e2e_parallel_onecore_20260220_002642/post/logs/post_runner.log`
    - `repro/runs/prod_canonical_full_e2e_parallel_onecore_20260220_002642/report/summary.md`
  - Quality-issue example artifacts:
    - `repro/runs/prod_canonical_full_e2e_parallel_onecore_20260220_002642/post/outputs/prod_canonical_full_e2e_parallel_onecore_20260220_002642/All3_ndlm_DISC.png`
    - `repro/runs/prod_canonical_full_e2e_parallel_onecore_20260220_002642/post/outputs/prod_canonical_full_e2e_parallel_onecore_20260220_002642/All3_exal_DISC.png`
    - `repro/runs/prod_canonical_full_e2e_parallel_onecore_20260220_002642/post/outputs/prod_canonical_full_e2e_parallel_onecore_20260220_002642/Agg_disc_1991_2022_1.png`
    - `repro/runs/prod_canonical_full_e2e_parallel_onecore_20260220_002642/post/outputs/prod_canonical_full_e2e_parallel_onecore_20260220_002642/post_artifacts_manifest.csv`
- Validation notes:
  - No hard runtime failures are currently blocking workflow completion.
  - Current blocker class is output-quality correctness and plot-data contract integrity.
- Next action:
  - Execute `Q-00` baseline freeze and then start `Q-01` NDLM-only isolated diagnosis lane before any model-logic edits.

### Progress Update 2026-02-20 20:17 UTC

- Phase: `Q-00A` baseline freeze artifactization (diagnostics contract bootstrap)
- Change type: evidence capture (no model/post logic edits)
- Summary:
  - Executed `Q-00A` and froze the canonical diagnosis baseline for:
    - `run_id=prod_canonical_full_e2e_parallel_onecore_20260220_002642`
  - Added run-scoped baseline diagnostics bundle with:
    - immutable run/status snapshot,
    - explicit target artifact list under diagnosis,
    - producer code-path map with file/line hints,
    - symptom table for NDLM, univar median, multivar horizon, and `Agg_disc_*`.
  - No code-path behavior changes were made in fit/post/validate/report.
- Files touched:
  - `repro/UNIFIED_MULTIMODEL_WORKFLOW_TRACKER.md`
  - `repro/runs/prod_canonical_full_e2e_parallel_onecore_20260220_002642/diagnostics/q00_baseline/baseline_manifest.md`
  - `repro/runs/prod_canonical_full_e2e_parallel_onecore_20260220_002642/diagnostics/q00_baseline/baseline_symptom_table.csv`
- Evidence:
  - Baseline bundle root:
    - `repro/runs/prod_canonical_full_e2e_parallel_onecore_20260220_002642/diagnostics/q00_baseline/`
  - Baseline manifest:
    - `repro/runs/prod_canonical_full_e2e_parallel_onecore_20260220_002642/diagnostics/q00_baseline/baseline_manifest.md`
  - Baseline symptoms:
    - `repro/runs/prod_canonical_full_e2e_parallel_onecore_20260220_002642/diagnostics/q00_baseline/baseline_symptom_table.csv`
- Validation notes:
  - Target diagnosis artifacts referenced in the baseline manifest are present in post outputs.
  - `Q-00A` is complete; `Q-00B` contract audit files (`horizon_contract.md`, `shape_contract_table.csv`, `contract_warnings_summary.csv`) remain pending.
- Next action:
  - Execute `Q-00B` contract audit and then launch `Q-01A` NDLM-only isolated lane.

### Progress Update 2026-02-20 20:44 UTC

- Phase: `Q-00B` contract audit completion
- Change type: diagnostics evidence capture (no model/post logic edits)
- Summary:
  - Completed `Q-00B` and generated all required contract-audit artifacts for baseline run:
    - horizon contract with requested vs available vs effective horizons,
    - NDLM post-input shape contract table (expected vs observed),
    - keyed warning/error summary parsed from baseline post logs.
  - Baseline highlights captured for root-cause isolation:
    - forecast availability mismatch (`NWS=10`, `GloFAS=28`, requested `k_step_ahead=30`),
    - effective synthesis cache horizon (`y_reps_f`) at `18`,
    - NDLM forecast-window objects (`sm_ens`, `standard_forecast_errors`) at horizon `10`.
- Files touched:
  - `repro/UNIFIED_MULTIMODEL_WORKFLOW_TRACKER.md`
  - `repro/runs/prod_canonical_full_e2e_parallel_onecore_20260220_002642/diagnostics/q00_baseline/horizon_contract.md`
  - `repro/runs/prod_canonical_full_e2e_parallel_onecore_20260220_002642/diagnostics/q00_baseline/shape_contract_table.csv`
  - `repro/runs/prod_canonical_full_e2e_parallel_onecore_20260220_002642/diagnostics/q00_baseline/contract_warnings_summary.csv`
  - `repro/runs/prod_canonical_full_e2e_parallel_onecore_20260220_002642/diagnostics/q00_baseline/horizon_metrics.csv`
- Evidence:
  - `repro/runs/prod_canonical_full_e2e_parallel_onecore_20260220_002642/diagnostics/q00_baseline/horizon_contract.md`
  - `repro/runs/prod_canonical_full_e2e_parallel_onecore_20260220_002642/diagnostics/q00_baseline/shape_contract_table.csv`
  - `repro/runs/prod_canonical_full_e2e_parallel_onecore_20260220_002642/diagnostics/q00_baseline/contract_warnings_summary.csv`
  - `repro/runs/prod_canonical_full_e2e_parallel_onecore_20260220_002642/diagnostics/q00_baseline/horizon_metrics.csv`
- Validation notes:
  - `Q-00` completion gate is satisfied (`baseline_manifest.md`, `baseline_symptom_table.csv`, `horizon_contract.md`, `shape_contract_table.csv`, `contract_warnings_summary.csv` all present).
  - No stage reruns were executed in this update.
- Next action:
  - Launch `Q-01A` NDLM-only isolated fit+post lane and start periodic health checks on that lane.

### Progress Update 2026-02-20 20:47 UTC

- Phase: `Q-01A` NDLM-only lane launch + isolation wiring validation
- Change type: execution diagnostics
- Summary:
  - Attempted NDLM-only isolated lane with minimal stages and captured two hard preconditions:
    1. `fit+post` without shared inputs fails in fit adapter conversion with non-finite source rows.
    2. NDLM fit bridge enforces run-scoped shared inputs (`inputs/shared/...`) and fails fast when absent.
  - Started active NDLM-only isolated run with pre-seeded run-scoped shared bundle:
    - `run_id=diag_q01a_ndlm_only_sharedseed_fitpost_20260220_124726`
    - stages: `fit, post`
    - models: `run_ndlm_main=true`, `run_exdqlm_multivar=false`, `run_exdqlm_univar=false`
  - Live process evidence confirms NDLM theory runner is executing under the isolated run root.
- Files touched:
  - `repro/UNIFIED_MULTIMODEL_WORKFLOW_TRACKER.md`
- Evidence:
  - Failed attempt (raw-input non-finite conversion):
    - `/tmp/diag_q01a_ndlm_only_fitpost_20260220_124453.yaml`
    - `repro/runs/diag_q01a_ndlm_only_fitpost_20260220_124453/run_manifest.yaml`
    - foreground error capture: `glofas_fit_adapter.csv:0 has non-finite values after conversion`
  - Failed attempt (shared-input precondition):
    - `/tmp/diag_q01a_ndlm_only_fitpost_from_adapters_20260220_124637.yaml`
    - `repro/runs/diag_q01a_ndlm_only_fitpost_from_adapters_20260220_124637/run_manifest.yaml`
    - foreground error capture: `legacy NDLM bridge requires run-scoped shared inputs`
  - Active isolated run:
    - `/tmp/diag_q01a_ndlm_only_sharedseed_fitpost_20260220_124726.yaml`
    - `repro/runs/diag_q01a_ndlm_only_sharedseed_fitpost_20260220_124726/run_manifest.yaml`
    - process traces observed for:
      - `scripts/unified_run.R --config /tmp/diag_q01a_ndlm_only_sharedseed_fitpost_20260220_124726.yaml`
      - `scripts/run_ndlm_main.R` with NDLM run-scoped env bindings.
- Validation notes:
  - `Q-01A` is in progress (fit active; post not started yet).
  - No model-logic edits were applied in this step.
- Next action:
  - Continue periodic health checks on `diag_q01a_ndlm_only_sharedseed_fitpost_20260220_124726` and register NDLM diagnostics bundle outputs once fit/post close.

### Progress Update 2026-02-20 22:01 UTC

- Phase: `Q-01A/Q-01B` NDLM-only resume closure with updated retrospective policy context
- Change type: root-cause fix + targeted tests + isolated rerun evidence
- Summary:
  - Re-verified updated cutoff retrospective preparation for `cutoff=2022-12-25`:
    - source: `data/forecats_inputs/site=11160500/cutoff_date=2022-12-25/run_id=auto_cutoff_policy_fillcheck_minicache_20260220/inputs/retrospective_preparation.csv`
    - continuity: daily index continuous from `2019-11-06` to `2022-12-25`
    - `selected_nws_synthetic_value` missing count: `0`
  - Confirmed original `Q-01A` fail locus in NDLM-only mode:
    - `fit=pass`, `post=fail` due empty-path univar bundle load in `30_univariate_and_misc.R`.
  - Implemented family-aware NDLM-only post initialization path:
    - new module planner helper and NDLM-only init module.
    - NDLM-only path now skips exDQLM bundle loads and fail-fasts only on NDLM-required artifact/object contract.
  - Added/ran targeted regression tests covering:
    - NDLM-only module planning,
    - non-NDLM-only planning unchanged,
    - NDLM-only init success/fail-fast behavior,
    - smoke-fast post artifact contract relaxation path.
  - Relaunched NDLM-only isolated lane with shared-input prep and achieved closure:
    - `run_id=diag_q01a_ndlm_only_sharedseed_fitpost_resume_sharedfix_20260220_215704`
    - stages: `forecats=pass`, `data_prep_shared=pass`, `fit=pass`, `post=pass`
  - Generated required `Q-01A` diagnostics bundle and `Q-01B` hypothesis matrix.
- Files touched:
  - `R/unified/post_module_plan.R`
  - `R/environmetrics/30_ndlm_only_init.R`
  - `R/unified/post_artifact_contract.R`
  - `scripts/run_environmetrics_figures.R`
  - `repro/tests/test_post_module_plan.py`
  - `repro/UNIFIED_MULTIMODEL_WORKFLOW_TRACKER.md`
  - `repro/runs/diag_q01a_ndlm_only_sharedseed_fitpost_resume_sharedfix_20260220_215704/diagnostics/ndlm/*`
- Evidence:
  - Baseline failed run:
    - `repro/runs/diag_q01a_ndlm_only_sharedseed_fitpost_20260220_124726/run_manifest.yaml`
    - `repro/runs/diag_q01a_ndlm_only_sharedseed_fitpost_20260220_124726/post/logs/post_runner.log`
  - Passing rerun:
    - `repro/runs/diag_q01a_ndlm_only_sharedseed_fitpost_resume_sharedfix_20260220_215704/run_manifest.yaml`
    - `repro/runs/diag_q01a_ndlm_only_sharedseed_fitpost_resume_sharedfix_20260220_215704/post/logs/post_runner.log`
    - `repro/runs/diag_q01a_ndlm_only_sharedseed_fitpost_resume_sharedfix_20260220_215704/post/outputs/diag_q01a_ndlm_only_sharedseed_fitpost_resume_sharedfix_20260220_215704/post_artifacts_manifest.csv`
  - Q-01A diagnostics bundle:
    - `repro/runs/diag_q01a_ndlm_only_sharedseed_fitpost_resume_sharedfix_20260220_215704/diagnostics/ndlm/ndlm_iter_trace.csv`
    - `repro/runs/diag_q01a_ndlm_only_sharedseed_fitpost_resume_sharedfix_20260220_215704/diagnostics/ndlm/ndlm_time_coverage.csv`
    - `repro/runs/diag_q01a_ndlm_only_sharedseed_fitpost_resume_sharedfix_20260220_215704/diagnostics/ndlm/ndlm_plot_contract_check.csv`
    - `repro/runs/diag_q01a_ndlm_only_sharedseed_fitpost_resume_sharedfix_20260220_215704/diagnostics/ndlm/ndlm_object_shapes.csv`
  - Q-01B matrix:
    - `repro/runs/diag_q01a_ndlm_only_sharedseed_fitpost_resume_sharedfix_20260220_215704/diagnostics/ndlm/ndlm_hypothesis_matrix.md`
- Validation notes:
  - `Q-01A` run closure criteria (stage pass + diagnostics bundle) are satisfied.
  - `Q-01B` root-cause isolation for original NDLM-only post crash is satisfied with one supported cause.
  - NDLM horizon acceptance remains open (`ndlm_plot_contract_check.csv` mismatches), to be handled in downstream quality-fix tasks (`Q-03/Q-04` scope).
- Next action:
  - Continue with NDLM horizon/quality correction work using the new passing NDLM-only lane and diagnostics artifacts as baseline.

### Progress Update 2026-02-20 22:39 UTC

- Phase: `Q-01C` NDLM horizon/data-flow contract closure (NDLM-only scope)
- Change type: root-cause fix + diagnostics hardening + targeted regression + isolated rerun evidence
- Summary:
  - Root-cause confirmed for remaining NDLM mismatch: diagnostics contract incorrectly assumed max forecast horizon (`28`) instead of NDLM shared forecast horizon.
  - Implemented theory-aligned NDLM horizon invariants:
    - NDLM shared horizon is now explicitly tracked as `K=min(nws_len,glofas_len,K_cap)`.
    - `ndlm_main_theory_state` now stores `K`, `K_cap`, `nws_len`, `glofas_len`.
    - NDLM fit contract checks and diagnostics now enforce horizon consistency across `standard_forecast_errors`, `sm_ens`, and `sC_ens`.
  - Added automated NDLM diagnostics bundle generation in post stage (NDLM-enabled runs; strict fail-fast in NDLM-only lane):
    - `ndlm_iter_trace.csv` (ELBO, crit_elbo, sigma, state-norm, weights),
    - `ndlm_time_coverage.csv`,
    - `ndlm_plot_contract_check.csv`,
    - `ndlm_object_shapes.csv`,
    - `ndlm_fit_vs_observed_coverage.csv`,
    - `ndlm_horizon_contract.md`.
  - Reran NDLM-only lane and closed `Q-01C` acceptance:
    - `run_id=diag_q01a_ndlm_only_horizonfix_20260220_223605`
    - stages: `forecats=pass`, `data_prep_shared=pass`, `fit=pass`, `post=pass`
    - horizon contract check now fully passes (`expected K=10`, `actual K=10`).
- Files touched:
  - `R/unified/families/ndlm_main/00_constants.R`
  - `R/unified/families/ndlm_main/01_inputs.R`
  - `R/unified/families/ndlm_main/03_vb_updates.R`
  - `R/unified/families/ndlm_main/06_save_state.R`
  - `R/unified/families/ndlm_main/zz_run.R`
  - `R/unified/contract_checks.R`
  - `R/unified/diagnostics.R`
  - `R/unified/ndlm_post_diagnostics.R`
  - `R/unified/stages/stage_post.R`
  - `tests/testthat/test_ndlm_horizon_contract.R`
  - `repro/UNIFIED_MULTIMODEL_WORKFLOW_TRACKER.md`
- Evidence:
  - Updated retrospective continuity recheck (unchanged data-prep policy result):
    - `data/forecats_inputs/site=11160500/cutoff_date=2022-12-25/run_id=auto_cutoff_policy_fillcheck_minicache_20260220/inputs/retrospective_preparation.csv`
  - NDLM-only rerun closure:
    - `repro/runs/diag_q01a_ndlm_only_horizonfix_20260220_223605/run_manifest.yaml`
    - `repro/runs/diag_q01a_ndlm_only_horizonfix_20260220_223605/post/logs/post_runner.log`
  - NDLM diagnostics bundle (auto-generated by post stage):
    - `repro/runs/diag_q01a_ndlm_only_horizonfix_20260220_223605/diagnostics/ndlm/ndlm_iter_trace.csv`
    - `repro/runs/diag_q01a_ndlm_only_horizonfix_20260220_223605/diagnostics/ndlm/ndlm_time_coverage.csv`
    - `repro/runs/diag_q01a_ndlm_only_horizonfix_20260220_223605/diagnostics/ndlm/ndlm_plot_contract_check.csv`
    - `repro/runs/diag_q01a_ndlm_only_horizonfix_20260220_223605/diagnostics/ndlm/ndlm_object_shapes.csv`
    - `repro/runs/diag_q01a_ndlm_only_horizonfix_20260220_223605/diagnostics/ndlm/ndlm_fit_vs_observed_coverage.csv`
    - `repro/runs/diag_q01a_ndlm_only_horizonfix_20260220_223605/diagnostics/ndlm/ndlm_horizon_contract.md`
- Validation notes:
  - Targeted tests passed:
    - `tests/testthat/test_ndlm_horizon_contract.R`
    - `tests/testthat/test_ndlm_post_jsd.R`
    - `repro/tests/test_post_module_plan.py`
    - `repro/tests/test_ndlm_theory_vb_regression.py`
  - `Q-01` is now closed for NDLM-only crash + horizon-contract mismatch.
  - NDLM model-quality interpretation (fit quality vs scientific adequacy) remains a separate downstream task and is not changed by this wiring/contract fix.
- Next action:
  - Continue with non-NDLM checklist items (`Q-02` onward) without changing this NDLM contract baseline.

### Progress Update 2026-02-20 22:47 UTC

- Phase: NDLM-only re-verification pass (post-fix stability check)
- Change type: verification rerun + theory/notebook alignment evidence update (no new NDLM logic change)
- Summary:
  - Re-ran the NDLM-only isolated lane from the horizon-fixed configuration with a fresh run id:
    - `run_id=diag_q01a_ndlm_only_horizonfix_verify_20260220_224430`
    - stages: `forecats=pass`, `data_prep_shared=pass`, `fit=pass`, `post=pass`
  - Re-validated retrospective continuity for cutoff `2022-12-25` under the updated automatic policy:
    - daily index continuity holds (`date_gap_count=0`)
    - `selected_nws_synthetic_value` has no missing values after lead-fallback fill (`missing=0`)
  - Re-checked NDLM horizon-contract diagnostics:
    - all checks pass at shared horizon `K=10`
    - confirms consistent `K` across `standard_forecast_errors`, `sm_ens`, and `sC_ens`
  - Theory/notebook alignment note:
    - NDLM derivations define one shared forecast index `k=1..K` for active forecasters.
    - Historical notebook cells often use `ranges[1]` for plotting scaffolds, but NDLM forecast discrepancy state blocks are expected to follow the shared `K` contract.
- Evidence:
  - NDLM-only verify run:
    - `repro/runs/diag_q01a_ndlm_only_horizonfix_verify_20260220_224430/run_manifest.yaml`
    - `repro/runs/diag_q01a_ndlm_only_horizonfix_verify_20260220_224430/post/logs/post_runner.log`
  - NDLM diagnostics (verify run):
    - `repro/runs/diag_q01a_ndlm_only_horizonfix_verify_20260220_224430/diagnostics/ndlm/ndlm_iter_trace.csv`
    - `repro/runs/diag_q01a_ndlm_only_horizonfix_verify_20260220_224430/diagnostics/ndlm/ndlm_time_coverage.csv`
    - `repro/runs/diag_q01a_ndlm_only_horizonfix_verify_20260220_224430/diagnostics/ndlm/ndlm_plot_contract_check.csv`
    - `repro/runs/diag_q01a_ndlm_only_horizonfix_verify_20260220_224430/diagnostics/ndlm/ndlm_object_shapes.csv`
    - `repro/runs/diag_q01a_ndlm_only_horizonfix_verify_20260220_224430/diagnostics/ndlm/ndlm_fit_vs_observed_coverage.csv`
    - `repro/runs/diag_q01a_ndlm_only_horizonfix_verify_20260220_224430/diagnostics/ndlm/ndlm_horizon_contract.md`
  - Retrospective continuity check source:
    - `data/forecats_inputs/site=11160500/cutoff_date=2022-12-25/run_id=auto_cutoff_policy_fillcheck_minicache_20260220/inputs/retrospective_preparation.csv`
  - Theory references:
    - `/data/muscat_data/jaguir26/NDLM---Ensemble/docs/derivations/sections/01_notation_and_model.tex`
    - `/data/muscat_data/jaguir26/NDLM---Ensemble/docs/derivations/sections/08_computational_notes.tex`
- Validation notes:
  - Targeted NDLM regressions continue to pass:
    - `tests/testthat/test_ndlm_horizon_contract.R`
    - `tests/testthat/test_ndlm_post_jsd.R`
    - `repro/tests/test_post_module_plan.py`
    - `repro/tests/test_ndlm_theory_vb_regression.py`
  - No additional NDLM horizon/data-flow code change was required after this re-verification.
- Next action:
  - Keep NDLM horizon/data-flow contract frozen and move remaining NDLM work to model-quality diagnostics (fit behavior) only.

### Progress Update 2026-02-20 23:40 UTC

- Phase: NDLM ragged-horizon contract correction (`Q-01` scope refinement)
- Change type: root-cause fix (shared-K truncation removal) + theory alignment + regression hardening + isolated rerun
- Summary:
  - Reopened NDLM horizon contract because shared-`K` assumptions were mathematically inconsistent with target Model C ragged horizons.
  - Implemented NDLM ragged-horizon forecast contract:
    - per-source effective horizon `K_j=min(source_len_j, K_cap)`,
    - `K_overlap=min_j K_j`, `K_max=max_j K_j`,
    - active set by lead `A_k={j: k<=K_j}`,
    - segmented forecast state outputs `sm_ens/sC_ens` with profile `[K_overlap, K_max-K_overlap]` (for two-source case).
  - Added run-time NDLM metadata for contract tracing:
    - `K_vec`, `K_overlap`, `K_max`, `segment_lengths`, `extension_source`, `bridge_source`,
    - `active_set_by_lead`, `state_dim_by_lead`.
  - Updated fit/post contract checks to validate ragged profile consistency instead of shared-`K` equality.
  - Added NDLM ragged diagnostics outputs in post:
    - `active_set_by_lead.csv`,
    - `state_dim_by_lead.csv`,
    - `horizon_contract_check.csv`,
    - `ragged_coverage_summary.csv`.
- Theory updates:
  - NDLM derivation sections now state ragged-horizon Model C contract (`K_j`, `A_k`, transdimensional/equivalent fixed-dim projection).
- Verification rerun:
  - `run_id=20260220_153713`
  - stages: `forecats=pass`, `data_prep_shared=pass`, `fit=pass`, `post=pass`
  - ragged contract result: full pass (`k_nws=10`, `k_glofas=28`, `segment=[10,18]`, `standard_forecast_errors.K=28`).
- Evidence:
  - Run closure:
    - `repro/runs/20260220_153713/run_manifest.yaml`
    - `repro/runs/20260220_153713/fit/ndlm_main/logs/ndlm_theory.log`
    - `repro/runs/20260220_153713/post/logs/post_runner.log`
  - NDLM diagnostics bundle:
    - `repro/runs/20260220_153713/diagnostics/ndlm/ndlm_iter_trace.csv`
    - `repro/runs/20260220_153713/diagnostics/ndlm/ndlm_time_coverage.csv`
    - `repro/runs/20260220_153713/diagnostics/ndlm/horizon_contract_check.csv`
    - `repro/runs/20260220_153713/diagnostics/ndlm/ndlm_plot_contract_check.csv`
    - `repro/runs/20260220_153713/diagnostics/ndlm/active_set_by_lead.csv`
    - `repro/runs/20260220_153713/diagnostics/ndlm/state_dim_by_lead.csv`
    - `repro/runs/20260220_153713/diagnostics/ndlm/ragged_coverage_summary.csv`
    - `repro/runs/20260220_153713/diagnostics/ndlm/ndlm_hypothesis_matrix.md`
- Validation notes:
  - Targeted tests passed:
    - `tests/testthat/test_ndlm_ragged_horizon_builder.R`
    - `tests/testthat/test_ndlm_horizon_contract.R`
  - NDLM fit contract check passed:
    - `repro/runs/20260220_153713/fit/contract_checks/ndlm_main/ndlm_main_contract_check.yaml`
- Next action:
  - Keep ragged-horizon contract frozen and proceed to NDLM model-quality diagnosis (fit behavior/parameter dynamics), without changing non-NDLM families.

### Progress Update 2026-02-21 01:21 UTC

- Phase: Kalman C++ congruence + NDLM backend wiring (`A0`-`A8` execution thread, NDLM/exDQLM scope only)
- Change type: contract audit + C++ fail-fast hardening + NDLM unified backend integration + targeted tests + verification runs
- Summary:
  - Completed baseline and theory-to-code contract artifacts for NDLM/exDQLM Kalman paths:
    - `A0` baseline inventory matrix with callsite evidence.
    - `A1` shared Kalman contract note (common FFBS structure + model-specific likelihood/covariance split).
    - `A2` NDLM covariance compatibility decision (fixed `D` default with optional expected-covariance inputs in synth C++ path).
    - `A3` mismatch table and severity/fix mapping.
  - Implemented root-fix hardening in C++ paths:
    - NDLM synth C++ now has strict shape/slice guards, optional covariance selectors (`D_t`, `D_ens_t`), and explicit non-finite ELBO fail-fast.
    - multiv synth C++ now has explicit non-finite ELBO fail-fast checks.
  - Wired NDLM C++ Kalman backend into unified workflow:
    - Added backend selector `models.ndlm_main.kalman_backend: r|cpp`.
    - Added `R/unified/families/ndlm_main/ndlm_kalman_backend.cpp` and dispatch path in `02_model_spec.R`.
    - Set default NDLM backend to `cpp` in unified defaults + production canonical config.
    - Preserved R backend as fallback.
  - Added targeted deterministic tests:
    - C++ compile/load smoke (both DISC files + NDLM backend C++).
    - NDLM backend config validation.
    - R-vs-C++ NDLM smoother consistency test.
  - Verification status:
    - Targeted tests: pass.
    - NDLM-only fit+post smoke: pass.
    - multiv exDQLM median-only smoke (`q=0.50`) launched and running; no continuous polling by policy.
- Files touched (this phase):
  - `DISC_kalman_synth.cpp`
  - `DISC_kalman_synth_NDLM.cpp`
  - `R/unified/families/ndlm_main/ndlm_kalman_backend.cpp`
  - `R/unified/families/ndlm_main/02_model_spec.R`
  - `R/unified/families/ndlm_main/00_constants.R`
  - `R/unified/families/ndlm_main/03_vb_updates.R`
  - `R/unified/families/ndlm_main/zz_run.R`
  - `R/unified/config.R`
  - `R/unified/stages/stage_fit.R`
  - `R/unified/manifest.R`
  - `scripts/run_ndlm_main.R`
  - `config/unified_runs/production_canonical_family.yaml`
  - `tests/testthat/test_ndlm_kalman_backend.R`
  - `repro/tests/test_kalman_cpp_compile_smoke.py`
  - `repro/tests/test_ndlm_kalman_backend_config.py`
  - `repro/docs/kalman_cpp_audit/20260221T003811Z/baseline_inventory_matrix.md`
  - `repro/docs/kalman_cpp_audit/20260221T003811Z/shared_kalman_contract.md`
  - `repro/docs/kalman_cpp_audit/20260221T003811Z/ndlm_covariance_compatibility_decision.md`
  - `repro/docs/kalman_cpp_audit/20260221T003811Z/cpp_congruence_mismatch_table.md`
  - `config/unified_runs/ndlm_cpp_only_smoke_shared_20260221.yaml`
  - `config/unified_runs/multiv_cpp_ultrafast_smoke_shared_20260221.yaml`
- Evidence:
  - Contract/audit artifacts:
    - `repro/docs/kalman_cpp_audit/20260221T003811Z/baseline_inventory_matrix.md`
    - `repro/docs/kalman_cpp_audit/20260221T003811Z/shared_kalman_contract.md`
    - `repro/docs/kalman_cpp_audit/20260221T003811Z/ndlm_covariance_compatibility_decision.md`
    - `repro/docs/kalman_cpp_audit/20260221T003811Z/cpp_congruence_mismatch_table.md`
  - Targeted tests:
    - `tests/testthat/test_ndlm_kalman_backend.R`
    - `repro/tests/test_kalman_cpp_compile_smoke.py`
    - `repro/tests/test_ndlm_kalman_backend_config.py`
  - NDLM-only closure run:
    - `repro/runs/diag_ndlm_cpp_only_smoke_shared_20260221/run_manifest.yaml`
    - `repro/runs/diag_ndlm_cpp_only_smoke_shared_20260221/post/logs/post_runner.log`
  - Active multiv median-only smoke run:
    - `repro/runs/diag_multiv_cpp_ultrafast_smoke_shared_20260221/run_manifest.yaml`
    - `repro/runs/diag_multiv_cpp_ultrafast_smoke_shared_20260221/fit/q=50/logs/fit.log`
- Validation notes:
  - `A0`-`A6` complete.
  - `A7`: NDLM smoke complete; multiv smoke is in-progress (median-only lane, one job).
  - `A8`: tracker updated with current state and evidence paths.
- Next action:
  - Wait for `diag_multiv_cpp_ultrafast_smoke_shared_20260221` fit/post closure, then append final verification status and close the remaining `A7` gate.
