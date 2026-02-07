# UNIFIED WORKFLOW IMPLEMENTATION CHECKLIST

Date: 2026-02-07
Spec source: `repro/UNIFIED_WORKFLOW_MASTER_2026-02-07.md`
Repo root: `/data/muscat_data/jaguir26/project1_ucsc_phd`

## 1) Pre-implementation audit complete

- Master spec read fully: `repro/UNIFIED_WORKFLOW_MASTER_2026-02-07.md`.
- Facts F-001..F-036 rechecked using `rg` against referenced files.
- Notes:
  - Exact pattern strings for some facts differ slightly from the master table but the behavior is confirmed.
  - Confirmed key examples:
    - `R/environmetrics/02_helpers_core.R` has smoother loop using `GG[,,i]` inside `for(k in 1:(TT-1))` and returns `s = i`.
    - `scripts/forecats_plot_bundle.R` documents raw cms contract and transform scale handling.
    - `DISC_Optimal_Synth_Ranges_W.r` currently sources C++ files via absolute paths.

## 2) Stage execution order (must not reorder)

1. Stage 0: Baseline freeze support
2. Stage 1: Correctness blockers
3. Stage 2: Determinism
4. Stage 3: Config + manifest foundation
5. Stage 4: Output isolation + write audit
6. Stage 5: Scale contract + adapters
7. Stage 6: Unified orchestrator + parallel quantiles
8. Stage 7: Validation/report automation
9. Stage 8: Environment lock hardening

## 3) Planned file additions/modifications by stage

### Stage 0

- Add: `repro/stage0_capture_baseline_metadata.R`
- Add: `repro/run_unified_demo.sh`

### Stage 1

- Modify: `R/environmetrics/02_helpers_core.R`
- Modify: `DISC_Optimal_Synth_Ranges_W.r` (if analogous smoother bug present)
- Add: `tests/testthat/test_smoother_indexing.R`
- Add: `tests/testthat/test_helper_contract_s.R`
- Add: `tests/testthat/helper_unified_test_models.R`
- Add: `tests/testthat.R`

### Stage 2

- Modify: `sampling_exal.cpp`
- Modify: `sampling_truncnorm.cpp`
- Modify: `DISC_Optimal_Synth_Ranges_W.r` (seed pass-through where needed)
- Add: `R/unified/determinism.R`
- Add: `tests/testthat/test_determinism_sampling.R`

### Stage 3

- Add: `config/unified_run.template.yaml`
- Add: `R/unified/config.R`
- Add: `R/unified/manifest.R`
- Add: `R/unified/utils_hash.R`
- Add: `scripts/unified_run.R` (dry-run capable baseline)

### Stage 4

- Add: `R/unified/utils_write_audit.R`
- Add: `R/unified/stages/stage_fit.R`
- Add: `R/unified/stages/stage_post.R`
- Modify: `R/environmetrics/00_paths.R` and/or post modules to support run-root path injection (minimal, backward-compatible)

### Stage 5

- Add: `R/unified/utils_scale.R`
- Modify: stage adapters (`R/unified/stages/stage_fit.R`, `R/unified/stages/stage_post.R`)

### Stage 6

- Extend: `scripts/unified_run.R`
- Add: `R/unified/stages/stage_forecats.R`
- Add: `R/unified/stages/stage_validate.R`
- Add: `R/unified/stages/stage_report.R`

### Stage 7

- Modify: `repro/compare_to_canonical.py` (manifest/path support) or call contract from unified runner
- Add: report writers under `R/unified/stages/stage_report.R`

### Stage 8

- Add: `R/unified/utils_env_capture.R`
- Add: `repro/ENV_LOCK_STRATEGY.md`
- Update: `repro/SCRIPT_RUNNER_STATUS.md`
- Add: `repro/UNIFIED_WORKFLOW_README.md`

## 4) Tests to add and run

- `tests/testthat/test_smoother_indexing.R`
- `tests/testthat/test_helper_contract_s.R`
- `tests/testthat/test_determinism_sampling.R`

Run command:

```bash
Rscript --vanilla tests/testthat.R
```

## 5) Acceptance evidence paths (per run_id)

Under `repro/runs/<RUN_ID>/`:

- `resolved_config.yaml`
- `run_manifest.yaml`
- `validate/write_audit/fs_before.tsv`
- `validate/write_audit/fs_after.tsv`
- `validate/write_audit/fs_diff.patch`
- `validate/compare_report.json`
- `report/summary.md`
- `report/summary.json`
- `env/R_sessionInfo.txt`
- `env/R_installed_packages.csv`
- `env/python_pip_freeze.txt`
- `env/renviron_snapshot.txt`
- `env/threads_snapshot.txt`

Stage closure docs:

- `repro/STAGE_CLOSURE_STAGE0.md`
- `repro/STAGE_CLOSURE_STAGE1.md`
- `repro/STAGE_CLOSURE_STAGE2.md`
- `repro/STAGE_CLOSURE_STAGE3.md`
- `repro/STAGE_CLOSURE_STAGE4.md`
- `repro/STAGE_CLOSURE_STAGE5.md`
- `repro/STAGE_CLOSURE_STAGE6.md`
- `repro/STAGE_CLOSURE_STAGE7.md`
- `repro/STAGE_CLOSURE_STAGE8.md`

## 6) Commit discipline

- Minimum one commit per stage in order.
- No stage can start before prior stage closure artifact exists.
- Preserve legacy entrypoints and maintain backward compatibility.
