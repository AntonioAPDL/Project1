# DISC_W Final Status (Closeout)

Date: 2026-02-06
Project root: `/data/muscat_data/jaguir26/project1_ucsc_phd`
Scope: DISC multivariate exDQLM Wishart/ensemble workflow only.

## What Was Changed

The DISC_W workflow was completed through four controlled stages with hash-safe validation after each stage.

1. Stage 1 - Modularization (no semantic changes)
- Extracted helper modules under `R/disc_w/`:
  - `00_debug.R`
  - `01_paths_inputs.R`
  - `02_io_loaders.R`
  - `03_covariates_standardize.R`
  - `04_ensemble_bookkeeping.R`
  - `05_save_state.R`
  - `06_ensemble_spec.R`
- Kept `DISC_Optimal_Synth_Ranges_W.r` as orchestrator and delegated blocks to helpers.

2. Stage 2 - Ensemble normalization
- Introduced canonical ensemble contract (`E`) and validation.
- Removed duplicate ensemble bookkeeping paths.
- Established single source of truth for ranges/member structure.

3. Stage 3 - Documentation
- Added and updated runbook documentation:
  - `docs/DISC_W_WORKFLOW.md`
  - `repro/OPTIMIZATION_TRACKER.md`

4. Stage 4 - Safe performance optimization
- Added deterministic timing harness and optional R profiling.
- Applied two hash-safe micro-optimizations:
  - Reduced allocation overhead in mean forecast assembly.
  - Removed repeated forecast-index lookups.
- Observed speed-up: about `8.3%` (`17:17.46` to `15:51.39`).
- Dominant remaining hotspot: `save()` (expected due to byte-identical `.RData` requirement).

## Final Reproducibility Validation

Canonical final closeout run:
- `repro/baseline_runs/20260206_124259_p0_0.5_seed_777/`

Validation status:
- `run1/outputs.sha256` equals `run2/outputs.sha256`
- `meta/outputs_diff.txt` is empty
- Both runs match locked output hash:
  - `88dd2101b08f452b054ca191965802ce4b24d09bab407970c9f32d3657cdd56c`

Superseded run:
- `repro/baseline_runs/20260206_120030_p0_0.5_seed_777/` is incomplete and superseded by the validated run above.

## Canonical Commands

Single deterministic run:
```bash
cd /data/muscat_data/jaguir26/project1_ucsc_phd
Rscript --vanilla scripts/run_DISC_Optimal_Synth_Ranges_W.R 0.5 777
```

Two-run reproducibility validation:
```bash
cd /data/muscat_data/jaguir26/project1_ucsc_phd
cp --reflink=auto repro/baseline_runs/20260204_174008_p0_0.5_seed_777/inputs/DISC_variables_50_exAL_synth_DISC.RData \
  DISC_variables_50_exAL_synth_DISC.RData
bash repro/run_stage0_baseline.sh 0.5 777
```

## Scope Boundary

In scope:
- `DISC_Optimal_Synth_Ranges_W.r`
- `R/disc_w/*`
- `scripts/run_DISC_Optimal_Synth_Ranges_W.R`
- `repro/*` and `docs/DISC_W_WORKFLOW.md` related to DISC_W stages

Out of scope:
- `DISC_Optimal_Synth_Ranges.r`
- `DISC_Optimal_Synth_Ranges_NDLM.r`
- unrelated `forecats` / GloFAS work

## Known Warnings (Non-Blocking)

Observed warnings in baseline logs (present before and after refactor):
- `matrix_list[[i]][] <- value : number of items to replace is not a multiple of replacement length`
- `sprintf(...): arguments not used by format 'Sampling Started'`

These did not affect output hash equivalence in the canonical baseline checks.
