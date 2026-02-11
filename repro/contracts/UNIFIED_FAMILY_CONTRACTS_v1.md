# Unified Family Contracts v1

Date: 2026-02-11  
Scope: `project1_ucsc_phd` unified multi-model workflow  
Schema baseline: manifest v1 (no schema-breaking fields added)

## 1) Stage Graph Contracts

Current stage graph v1 (implemented):

`forecats -> data_prep_shared -> fit -> post -> validate -> report`

Target stage graph (planned):

`forecats -> data_prep_shared -> fit_exdqlm_multivar -> fit_exdqlm_univar -> fit_ndlm_main -> post -> validate -> report`

Notes:

- `data_prep_shared` is introduced as an independent stage in P1 and can run by itself.
- `fit` is still the compatibility bridge stage in v1 and can execute one or more families based on model toggles.

## 2) Family Contracts (v1, compatibility-first)

### 2.1 exdqlm_multivar (DISC-W)

- Required config inputs:
  - `inputs.fit.parameters_path`
  - `inputs.fit.retros_path`
  - `inputs.fit.nws_forecast_path`
  - `inputs.fit.glofas_forecast_path`
  - `fit.quantiles`
- Required output paths when enabled (`models.run_exdqlm_multivar=true`):
  - `repro/runs/<RUN_ID>/fit/q=<QQ>/outputs/DISC_variables_<QNUM>_exAL_synth_DISC.RData`
- Manifest recording:
  - `artifacts[]` entries with `storage_scale: model_state`
  - `flow_domain: cfg$scale_contract$analysis_scale_fit_internal`
- Scale contract:
  - storage adapters use `scale_contract.legacy_fit_input_scale`
  - internal analysis domain follows `scale_contract.analysis_scale_fit_internal`

### 2.2 exdqlm_univar (legacy bridge)

- Required output paths when enabled (`models.run_exdqlm_univar=true`):
  - `repro/runs/<RUN_ID>/fit/exdqlm_univar/q=<QQ>/outputs/variables_<QQ>_exAL_synth_DISC_uni.RData`
- Manifest recording:
  - `artifacts[]` path-prefix under `fit/exdqlm_univar/...` (manifest v1 compatibility approach)
- Authority semantics (doc-level in v1):
  - treat as `non_authoritative` until theory-aligned P3 implementation is complete.

### 2.3 ndlm_main (legacy bridge)

- Required output path when enabled (`models.run_ndlm_main=true`):
  - `repro/runs/<RUN_ID>/fit/ndlm_main/outputs/DISC_variables_50_NDLM_synth_DISC.RData`
- Manifest recording:
  - `artifacts[]` path-prefix under `fit/ndlm_main/...` (manifest v1 compatibility approach)
- Naming semantics:
  - family name is neutral (`ndlm_main`); `50` in the legacy filename is treated as a compatibility detail, not quantile meaning.
- Authority semantics (doc-level in v1):
  - treat as `non_authoritative` until theory-aligned P4 implementation is complete.

## 3) Acceptance Criteria Checklists (v1)

### 3.1 Family-level acceptance (enabled family must satisfy all)

1. Required artifact files exist under run scope (`repro/runs/<RUN_ID>/...`).
2. Manifest contains `artifacts[]` entries for produced files.
3. Files are readable in post-stage consumers (no root fallback in strict mode).

### 3.2 Stage-level acceptance

- PASS:
  - stage function returns without `stop(...)`
  - stage-specific outputs exist (if stage enabled)
  - manifest is written after stage completion
- FAIL:
  - stage function throws/`stop(...)`
  - unified run exits non-zero
  - `timestamps.finished_at_utc` remains null
- SKIP:
  - `cfg$stages.<stage> == false`

Required evidence files by stage:

1. `data_prep_shared`: `repro/runs/<RUN_ID>/inputs/shared/...` plus `run_manifest.yaml` entries.
2. `fit`: `repro/runs/<RUN_ID>/fit/...` logs + model-state outputs.
3. `post`: `repro/runs/<RUN_ID>/post/logs/post_runner.log` + `post/outputs/<RUN_ID>/...`.
4. `validate`: `repro/runs/<RUN_ID>/validate/compare_report.json` (when enabled).
5. `report`: `repro/runs/<RUN_ID>/report/summary.md` and `summary.json` (when enabled).

## 4) Locked Decisions Snapshot (P0 freeze)

- D-007 (LOCKED): Hybrid sequencing is the execution strategy.
  - Legacy bridge stays operational while theory-aligned modules are introduced incrementally.
  - This reflects current repo execution history and minimizes workflow downtime.
- D-010 (LOCKED): P5 closure acceptance in v1.
  - P5 is considered closed with strict run-scoped figures-on smoke using the smoke-fast path, provided:
    - manifest closure (`finished_at_utc` non-null),
    - run-scoped artifact resolution evidence in post logs,
    - no repo-root model-state loads,
    - figure outputs produced under `post/outputs/<RUN_ID>/...`.
  - Full heavy figure-path hardening remains a separate follow-up track.
