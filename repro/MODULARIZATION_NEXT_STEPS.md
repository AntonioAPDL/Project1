# Modularization Status & Next Steps

## Current modular layout (implemented)
The notebook `repro/recovery/Environmetrics_Figures__OLDEST.ipynb` is represented by the linearized script:
- `Environmetrics_Figures__OLDEST_linearized.R`

That linearized script is split into ordered modules under `R/environmetrics/`:
1. `00_setup.R` — library paths + package imports
2. `01_config.R` — global constants/flags (n.samp, p0, harmonics, deltas, etc.)
3. `02_helpers_core.R` — helper functions (positive-definite checks, KL/entropy helpers, utility functions)
4. `10_data_inputs.R` — data ingestion + covariate assembly (ELI/ONI, USGS, forecasts, PPT/soil/PCA, merge, standardization)
5. `20_model_setup.R` — model setup + matrices (df mats, model objects, priors, etc.)
6. `30_univariate_and_misc.R` — synthesis helpers + univariate block (always executed)
7. `40_figures.R` — all plotting/figure generation

The runner script `scripts/run_environmetrics_figures.R` sources the modules in this exact order and writes outputs to:
- `Environmetrics_reproduce_script_runs/YYYYMMDD_HHMMSS/`

## Invariants (do not change without re-validation)
- Preserve execution order exactly as above.
- Do not change object names or intermediate variables unless proven safe.
- Univariate block is always executed (no skip flag).
- Output directory is always the runner’s timestamped folder; never write into `Environmetrics_reproduce/`.

## Immediate next steps (high-quality cleanup, no semantics changes)
1. Add section headers/comments inside each module to make boundaries explicit.
2. Replace repeated path strings with a single shared config file (future step; not yet).
3. Isolate plotting parameters (width/height/dpi) in one module (`40_figures.R`) without changing values.
4. Introduce a lightweight `R/environmetrics/00_constants.R` if constants grow, but only after confirming unchanged outputs.

## Regenerating modules from the notebook
If the notebook changes:
1. Recreate the linearized script with:
   `scripts/extract_ipynb_to_R.sh`
2. Re-split into the 7 modules above (no semantic edits).
3. Keep the same execution order in the runner.

## Files to inspect when troubleshooting
- `scripts/run_environmetrics_figures.R` (runner + output redirection)
- `R/environmetrics/40_figures.R` (figure saves and file names)
- `repro/logs/script_runs/<RUN_ID>/run_log.txt` (progress timeline)
