# Reproduce Paper Figures and Results

## Environment assumptions
- R 4.3.x (a source tree exists at `R-4.3.1/`, but no install script is present).
- R packages listed in `install_packages.R` (run `Rscript install_packages.R`).
- C++ toolchain + headers/libs for Rcpp builds (the model script sets `PKG_CXXFLAGS` and `PKG_LIBS` to `/data/muscat_data/jaguir26/libs/...`).
- Python 3.x with `pandas`, `numpy`, `matplotlib`, `xarray`, `cdsapi`, `pygrib`, etc for the Python notebooks.
- `tmux` installed if you use the tmux launcher.

## Required inputs (must exist before model runs)
Local files:
- `nws_forecast.csv`
- `weighted_time_series.csv`
- `prism_precipitation_santa_cruz_1987_2023.csv`
- `soil_moisture_data/soil_moisture_big_trees_daily_avg_1987_2023.csv`
- `pca.csv`

External files (outside repo):
- `/data/muscat_data/jaguir26/projects/Project/Input/exAL/covariates/cov_1_ELI.csv`
- `/data/muscat_data/jaguir26/projects/Project/Input/exAL/covariates/cov_2_ONI.csv`

Quick check:
```bash
ls -lh \
  nws_forecast.csv \
  weighted_time_series.csv \
  prism_precipitation_santa_cruz_1987_2023.csv \
  soil_moisture_data/soil_moisture_big_trees_daily_avg_1987_2023.csv \
  pca.csv

ls -lh /data/muscat_data/jaguir26/projects/Project/Input/exAL/covariates/cov_1_ELI.csv \
       /data/muscat_data/jaguir26/projects/Project/Input/exAL/covariates/cov_2_ONI.csv
```

If any of these are missing:
- `prism_precipitation_santa_cruz_1987_2023.csv`: run `Rscript download_prism_data.R` (downloads 1987-2023 PRISM data to `prism_data/`).
- `soil_moisture_data/soil_moisture_big_trees_daily_avg_1987_2023.csv`: run `download_era5_soilmoisture.py` (ERA5 download) then `soil.ipynb` to aggregate to daily averages.
- `pca.csv`: run `gdpc_fit.ipynb`.
- `nws_forecast.csv`: generated in `Paper_Forecast_Synthesis_DQLM.ipynb`.
- `weighted_time_series.csv`: derived in `glofas_forecasts.ipynb` (output lines are mostly commented; may need to enable).
- `cov_1_ELI.csv` and `cov_2_ONI.csv`: currently outside repo and required by `DISC_Optimal_Synth_Ranges_W.r`.

## Step 1: Confirm existing model outputs (fast path)
```bash
ls -lh DISC_variables_*_exAL_synth_DISC.RData
ls -lh DISC_variables_50_NDLM_synth_DISC.RData
```
If these exist and are recent, you can skip to figure generation.

## Step 2: Regenerate model outputs (slow path)
Option A: run via tmux launcher (spawns sessions):
```bash
python run_scripts_synth_DISC_W.py
```
Option B: run sequentially in the foreground:
```bash
for p in 0.05 0.2 0.35 0.5 0.65 0.8 0.95; do
  Rscript DISC_Optimal_Synth_Ranges_W.r "$p"
done
```
NDLM baseline (if needed by figures):
```bash
Rscript DISC_Optimal_Synth_Ranges_NDLM.r 0.5
```

Expected outputs:
- `DISC_variables_05_exAL_synth_DISC.RData`
- `DISC_variables_20_exAL_synth_DISC.RData`
- `DISC_variables_35_exAL_synth_DISC.RData`
- `DISC_variables_50_exAL_synth_DISC.RData`
- `DISC_variables_65_exAL_synth_DISC.RData`
- `DISC_variables_80_exAL_synth_DISC.RData`
- `DISC_variables_95_exAL_synth_DISC.RData`
- `DISC_variables_50_NDLM_synth_DISC.RData`

## Step 3: Derived quantities
The figure notebook expects several intermediate RDS/RData objects (some saves are commented):
- `y_reps*.rds` (e.g., `y_reps_f.rds`, `y_reps_new.rds`) appear in `Environmetrics_Figures.ipynb`.

If these are missing and the notebook fails, either:
- un-comment the `saveRDS` lines in `Environmetrics_Figures.ipynb`, or
- rerun the notebook cells that generate these arrays.

## Step 4: Regenerate figures in `Environmetrics/`
1) Open and run `Environmetrics_Figures.ipynb` with an R kernel.
2) Many `ggsave()` lines are commented; you may need to un-comment them to write files into `Environmetrics/`.

Expected outputs (from `article.txt`):
- `Environmetrics/usgs.png`
- `Environmetrics/precip_soilmoisture_climatePC1_faceted_labeled.png`
- `Environmetrics/retrospective_log_discharge_plot_faceted.png`
- `Environmetrics/forecats.png`
- `Environmetrics/80_component_1991_2022.png`
- `Environmetrics/All_exal_2012-2016_DISC.png`
- `Environmetrics/All_exal_2017-2019_DISC.png`
- `Environmetrics/posterior_samples_valid.png`
- `Environmetrics/posterior_samples_counter_valid.png`

Note: `article.txt` references figures under `DISC/`. Either update the LaTeX paths or create `DISC/` and copy/symlink from `Environmetrics/`.

Optional: run `Retro-Analysis.ipynb` (Python kernel) to regenerate `plot_*.png` outputs and any retrospective plots referenced by the paper.

## Step 5: Validate outputs
```bash
ls -lh Environmetrics/*.png | wc -l
ls -lh Environmetrics/usgs.png \
      Environmetrics/precip_soilmoisture_climatePC1_faceted_labeled.png \
      Environmetrics/retrospective_log_discharge_plot_faceted.png \
      Environmetrics/forecats.png \
      Environmetrics/80_component_1991_2022.png \
      Environmetrics/All_exal_2012-2016_DISC.png \
      Environmetrics/All_exal_2017-2019_DISC.png \
      Environmetrics/posterior_samples_valid.png \
      Environmetrics/posterior_samples_counter_valid.png
```
Optional hashes for reproducibility:
```bash
sha256sum Environmetrics/*.png > repro/figure_hashes.sha256
```

## Known missing or fragile inputs
- `cov_1_ELI.csv` and `cov_2_ONI.csv` are outside this repo and required by the model script.
- Several notebook save steps are commented out; reproduction requires manual un-commenting or refactoring to scripts.
