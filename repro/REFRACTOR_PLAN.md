# Refactor Blueprint (Reproducible + Clean)

## Recommendation
Use an R `targets` pipeline because the core modeling and figure generation are R-first and already parameterized by quantile. Python pieces can be called from `targets` using system targets or `tar_target()` with `format = "file"`.

## Proposed clean structure
```
project1_ucsc_phd/
  R/                      # core R functions (model + plotting)
  src/                    # Rcpp sources (sampling, kalman) for package-style builds
  scripts/                # thin entrypoints (Rscript, python)
  notebooks/              # archived notebooks (read-only)
  data_raw/               # raw downloads (PRISM, ERA5, GloFAS, NWS)
  data_curated/           # cleaned CSVs used by the model
  outputs/model/          # large RData outputs by model/quantile
  outputs/derived/        # intermediate RDS objects (y_reps, etc)
  figures/                # final paper figures (Environmetrics)
  repro/                  # documentation (this folder)
  config.yml              # paths + parameters (p0 list, forecast dates)
  _targets.R              # pipeline definition
  renv.lock               # R package lockfile
  requirements.txt        # Python env for notebooks/scripts
```

## Migration strategy (do not break reproduction)
### Stage 0: Wrap existing scripts and notebooks
- Create `scripts/run_disc_exal.R` to call `DISC_Optimal_Synth_Ranges_W.r` with a p0 list.
- Create `scripts/run_ndlm.R` to call `DISC_Optimal_Synth_Ranges_NDLM.r`.
- Create `scripts/make_figures.R` to run the figure logic from `Environmetrics_Figures.ipynb`.
- Create `scripts/retro_analysis.py` to run the required cells from `Retro-Analysis.ipynb`.
- Keep original notebooks/scripts untouched; wrappers only.

### Stage 1: Extract reusable functions
- Move model setup, data loading, and save routines from `DISC_Optimal_Synth_Ranges_W.r` into `R/model_disc_exal.R`.
- Extract covariate loaders (PRISM, soil moisture, PCA) into `R/data_inputs.R`.
- Put plotting helpers from `Environmetrics_Figures.ipynb` into `R/plots_environmetrics.R`.
- Add `testthat` tests for helper functions (date alignment, file presence checks, output naming).

### Stage 2: Replace notebooks with scripts
- Convert `Environmetrics_Figures.ipynb` into `scripts/make_figures.R` that writes to `figures/`.
- Convert `Retro-Analysis.ipynb` into `scripts/retro_analysis.py` with explicit CLI arguments.
- Ensure scripts can be run headless (no manual un-commenting of `ggsave`).

### Stage 3: Add pipeline + smoke tests
- Create `_targets.R` with targets for:
  - `data_raw` downloads (PRISM, ERA5, GloFAS/NWS)
  - `data_curated` CSVs (pca.csv, soil moisture, etc)
  - model outputs for each p0
  - figure generation
- Add a small smoke configuration (subset of dates, fewer samples) to validate without large runtimes.
- Add CI or local `make check` that runs smoke targets only.

## Notes for smooth migration
- Keep old file names for outputs during the transition; add a copy step to the new `outputs/` layout.
- Use `config.yml` for all hard-coded paths (especially `/data/muscat_data/...` and `/home/jaguir26/...`).
- Consider packaging the Rcpp sources in an R package (e.g., `exalmodel`) to avoid manual `sourceCpp` calls.
- Add `renv` and Python requirements to lock versions once the pipeline is stable.
