# DISC Wishart/Ensemble Workflow — Runbook

This document is the operational runbook for the **Wishart + ensemble** multivariate exDQLM workflow anchored at:
- Entrypoint orchestrator: `DISC_Optimal_Synth_Ranges_W.r`
- Helper modules: `R/disc_w/*`
- Compiled deps (loaded via `Rcpp::sourceCpp()` in the orchestrator): `sampling_exal.cpp`, `sampling_truncnorm.cpp`, `DISC_kalman_synth.cpp`

## Scope + hard exclusions

In scope:
- Only the Wishart/ensemble workflow anchored at `DISC_Optimal_Synth_Ranges_W.r`.

Hard exclusions (do not edit):
- `DISC_Optimal_Synth_Ranges_NDLM.r`
- `DISC_Optimal_Synth_Ranges.r`

## Canonical run commands (deterministic)

Single run (wrapper sets seed and forces single-threaded BLAS/OpenMP):

```bash
cd /data/muscat_data/jaguir26/project1_ucsc_phd
Rscript --vanilla scripts/run_DISC_Optimal_Synth_Ranges_W.R 0.5 777
```

Locked baseline equivalence check (restores mutable `.RData` state, then runs twice):

```bash
cd /data/muscat_data/jaguir26/project1_ucsc_phd
cp --reflink=auto repro/baseline_runs/20260204_174008_p0_0.5_seed_777/inputs/DISC_variables_50_exAL_synth_DISC.RData \
  DISC_variables_50_exAL_synth_DISC.RData
bash repro/run_stage0_baseline.sh 0.5 777
```

Latest canonical validation artifact:
- `repro/baseline_runs/20260206_124259_p0_0.5_seed_777/`
- Status: `PASS: outputs.sha256 identical`
- Primary output hash:
  - `88dd2101b08f452b054ca191965802ce4b24d09bab407970c9f32d3657cdd56c`

## Inputs / outputs inventory

The workflow reads multiple external and repo-local inputs and writes an updated VB state back to disk.

Authoritative inventory lives in:
- `repro/OPTIMIZATION_TRACKER.md` → **“Inputs / outputs (static inventory; Wishart workflow)”**

## Dataflow overview (the “contract” between pieces)

High-level execution path:

1. `DISC_Optimal_Synth_Ranges_W.r` (script orchestrator)
   - sources `R/disc_w/_init.R` (which sources all `R/disc_w/*.R` helpers)
   - loads inputs (covariates, forecasts, precipitation/soil/PCA, retrospective streamflow)
   - builds ensembles + covariates
   - runs the VB/Kalman update loop
   - saves updated state into `DISC_variables_<...>.RData`

2. `R/disc_w/*` (helpers, extracted for modularity with no semantic changes)
   - paths + I/O loaders
   - covariate construction/standardization
   - ensemble bookkeeping and normalization helpers
   - save-state helper (dynamic naming + `assign()` + `save()`)

3. Compiled code (loaded at runtime via `Rcpp::sourceCpp()` from the orchestrator)
   - `sampling_exal.cpp`: GIG sampler + multivariate normal sampling utilities used by the workflow
   - `sampling_truncnorm.cpp`: truncated-normal sampler used by the workflow
   - `DISC_kalman_synth.cpp`: Kalman/RTS core used by the workflow (export `DISC_update_theta_synth_cpp_W`)

For a static “what is actually called” inventory, see:
- `audit_used_code.md`

## Canonical ensemble contract (Stage 2 normalization)

The canonical ensemble object `E` is created by:
- `disc_w_as_ensemble(...)` in `R/disc_w/06_ensemble_spec.R`

Contract:
- `E$type == "disc_w_ensemble"`
- `E$data` is a list of **matrix-like** objects; for each source `j`:
  - `E$data[[j]]` has **rows = time/lead index**, **cols = member index**
  - element type: matrix or numeric `data.frame`
- `E$J` is the number of ensemble sources (length of `E$data`)
- `E$num_mem[j] == ncol(E$data[[j]])`
- `E$ranges[j] == nrow(E$data[[j]])`

Why “matrix-like” is allowed:
- In this workflow, forecast inputs are commonly read via `read.csv(...)` and are therefore `data.frame`s.
- Downstream operations used here (`rowMeans`, `dim`, `nrow`, `ncol`, `^`, `-`, `*`, and `sum`) operate consistently on numeric data frames, so the canonical representation preserves the existing type and avoids incidental coercions.

## Mutability warning (very important for equivalence checks)

`DISC_variables_<...>.RData` is **updated in-place** by the workflow.

If you run the workflow twice without restoring the initial `.RData`, you will not be comparing like-for-like states.

For equivalence checks, always restore the locked initial state first (see the “Locked baseline equivalence check” command above).

## Debugging knobs and expectations

`DISC_DEBUG`:
- Defined near the top of `DISC_Optimal_Synth_Ranges_W.r`.
- Default is `FALSE`.
- When enabled, helpers can perform extra assertions (e.g., ensemble shape checks via `disc_w_validate_ensemble(..., strict=TRUE)`).

`disc_assert(...)`:
- Defined in `R/disc_w/00_debug.R`.
- No-op unless `DISC_DEBUG` is `TRUE`.

Typical failure modes caught by strict checks:
- non-numeric ensemble columns (e.g., factors/characters)
- inconsistent `ranges/num_mem` vs `dim()` of the underlying forecast matrices
