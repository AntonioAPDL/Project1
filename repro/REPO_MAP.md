# Repo Executive Map

## Scope and current focus
- Old PhD Project 1 workspace with mixed research, data, and tooling.
- Immediate goal is to reproduce the current paper figures in `Environmetrics/` and track how they were produced.

## Major directories
- `Environmetrics/`: final paper figures (PNG) referenced by `article.txt`.
- `plots/`, `Plots_Model_DISC/`, `Plots_Model_GDPCA/`, `Plots_Model_PCA/`, `quantile_plots/`, `gdpc_plots/`, `figures_for_river_ecmwf_nwm/`: derived plots from experiments (likely legacy or side analyses).
- `prism_data/`: raw PRISM precipitation downloads (large).
- `soil_moisture_data/`: ERA5 soil moisture downloads + aggregated CSVs.
- `climate_indices/`: climate index data (usage unclear).
- `task_medium/`: R package scaffold with `R/` and `src/` (Rcpp) code.
- `Project/`: separate workspace for download scripts (outside repo structure; used by `forecast_download.py`/`glofas_download.py`).
- Tooling/SDK directories: `boost_1_81_0/`, `boost_1_82_0/`, `cmake-3.22.1/`, `eccodes-2.26.0-Source/`, `google-cloud-sdk/`, `julia-1.9.3/`, `R-4.3.1/`, `lapack/`, `fftw-3.3.10/`, `nlopt-2.7.0/`, `icu/`, `rclone-v1.67.0-linux-amd64/`, `aws/`.

## Active pipeline (paper reproduction)
1. Model runs (exAL, weighted forecasts): `run_scripts_synth_DISC_W.py` -> `DISC_Optimal_Synth_Ranges_W.r` -> `DISC_variables_*_exAL_synth_DISC.RData`.
2. NDLM baseline (observed in outputs): `DISC_Optimal_Synth_Ranges_NDLM.r` -> `DISC_variables_50_NDLM_synth_DISC.RData`.
3. Figure assembly: `Environmetrics_Figures.ipynb` reads the RData outputs + local covariate CSVs and writes figures into `Environmetrics/` (many save calls are commented).
4. Retrospective ensemble comparisons: `Retro-Analysis.ipynb` produces `plot_*.png` outputs; some appear to have been copied into `Environmetrics/`.

## Legacy/experimental pipelines (not clearly tied to current paper)
- Alternate model drivers: `run_scripts_synth.py`, `run_scripts_synth_DISC.py`, `run_scripts.py`, `run_scripts_SL.py`, `run_scripts_SLwoPPT.py`, `run_scripts_AV.py`, `run_scripts_sim_test.py`.
- Model variants: `Optimal_Synth_Ranges.r`, `Optimal_Synth_Ranges_NDLM.r`, `OptimalModelSLexAL.r`, `OptimalModelAVexAL.r`, `Optimal_DQLM.r`, `DQLM_SIM_test.r`, `LD_vs_IS*.r`, `gdpc_*`, `dpca_*`, `fnets_*`, `fnet_analysis.R`, `fda_usc_fpca_analysis.R`.
- Notebooks for earlier analyses: `Paper_Forecast_Synthesis_DQLM.ipynb`, `Opt_CRPS_Synth.ipynb`, `Emp_Synthesys.ipynb`, `DISC_TEST.ipynb`, `Test_*.ipynb`, etc.

## Key entrypoints and what they generate
- `run_scripts_synth_DISC_W.py`: tmux launcher; runs `Rscript DISC_Optimal_Synth_Ranges_W.r <p0>` for p0 in {0.05, 0.2, 0.35, 0.5, 0.65, 0.8, 0.95}.
- `DISC_Optimal_Synth_Ranges_W.r`: main model; reads local CSVs + external covariates; compiles C++ via Rcpp; saves `DISC_variables_<p0*100>_exAL_synth_DISC.RData`.
- `DISC_Optimal_Synth_Ranges_NDLM.r`: NDLM baseline; saves `DISC_variables_<p0*100>_NDLM_synth_DISC.RData`.
- `Environmetrics_Figures.ipynb`: loads model outputs + covariates; saves PNGs into `Environmetrics/` (save calls mostly commented).
- `Retro-Analysis.ipynb`: loads `weighted_time_series.csv` + `nws_*` + USGS data; produces `plot_*.png` in repo root.
- `download_prism_data.R`: downloads PRISM precipitation; outputs `prism_precipitation_santa_cruz_1987_2023.csv` and populates `prism_data/`.
- `download_era5_soilmoisture.py`: downloads ERA5 soil moisture (netCDF) into `soil_moisture_data/`.
- `soil.ipynb`: aggregates soil moisture to daily average CSVs.
- `gdpc_fit.ipynb`: writes `pca.csv`.
- `Paper_Forecast_Synthesis_DQLM.ipynb`: writes `nws_forecast.csv`.
- `glofas_forecasts.ipynb`: generates `weighted_time_series.csv` or `weighted_time_series_custom.csv` (outputs mostly commented).
- `forecast_download.py`/`glofas_download.py`: heavy data ingestion for NWS/GloFAS; writes into `/home/jaguir26/projects/Project` (outside repo).

## Model implementations
- C++ (Rcpp sources): `sampling_exal.cpp`, `sampling_truncnorm.cpp`, `DISC_kalman_synth.cpp`, `DISC_kalman_synth_NDLM.cpp`, plus other `kalman_*.cpp`.
- R modeling scripts: `DISC_Optimal_Synth_Ranges_W.r`, `DISC_Optimal_Synth_Ranges.r`, `DISC_Optimal_Synth_Ranges_NDLM.r`, `OptimalModelSLexAL.r`, `OptimalModelAVexAL.r`, `Optimal_Synth_Ranges*.r`, `Optimal_DQLM.r`.
- R package scaffold: `task_medium/` with `task_medium/R/exal.r` and `task_medium/src/exAL.cpp`.

## Analysis/plotting locations
- Primary figure notebook: `Environmetrics_Figures.ipynb` (R).
- Retrospective/ensemble notebook: `Retro-Analysis.ipynb` (Python).
- Additional plotting outputs: `plots/`, `Plots_Model_DISC/`, `Plots_Model_GDPCA/`, `Plots_Model_PCA/`, `quantile_plots/`, `gdpc_plots/`.

## Data sources and how created
Local (in repo):
- `nws_forecast.csv` (generated in `Paper_Forecast_Synthesis_DQLM.ipynb`).
- `weighted_time_series.csv` (from `glofas_forecasts.ipynb` or manual export).
- `prism_precipitation_santa_cruz_1987_2023.csv` (from `download_prism_data.R`).
- `soil_moisture_data/soil_moisture_big_trees_daily_avg_1987_2023.csv` (from `soil.ipynb`).
- `pca.csv` (from `gdpc_fit.ipynb`).
- USGS/forecast intermediate CSVs in repo root (e.g., `usgs_*`, `glofas_*`, `nws_*`).

External (outside repo or network):
- `/data/muscat_data/jaguir26/projects/Project/Input/exAL/covariates/cov_1_ELI.csv`
- `/data/muscat_data/jaguir26/projects/Project/Input/exAL/covariates/cov_2_ONI.csv`
- USGS NWIS daily flow via `dataRetrieval::readNWISdv` (R) or `dataretrieval.nwis` (Python).
- ERA5 land soil moisture via `cdsapi`.
- GloFAS forecasts via `cdsapi` + `pygrib`.
- NWS forecast data via `forecast_download.py` (AWS/GCP).

## Outputs and provenance
Model outputs:
- `DISC_variables_{5,20,35,50,65,80,95}_exAL_synth_DISC.RData` -> produced by `DISC_Optimal_Synth_Ranges_W.r` (or `DISC_Optimal_Synth_Ranges.r`).
- `DISC_variables_50_NDLM_synth_DISC.RData` -> produced by `DISC_Optimal_Synth_Ranges_NDLM.r`.
- `variables_{5,20,35,50,65,80,95}_exAL_synth_DISC_uni.RData` -> produced by `OptimalModelSLexAL.r` (run via `run_scripts_SL.py`).
- `PCA_variables_{5,20,35,50,65,80,95}_exAL_synth_PCA.RData` -> produced by `Optimal_Synth_Ranges.r`.

Paper figures (per `article.txt`):
- `Environmetrics/usgs.png` -> `Environmetrics_Figures.ipynb` (ggsave call commented).
- `Environmetrics/precip_soilmoisture_climatePC1_faceted_labeled.png` -> `Environmetrics_Figures.ipynb`.
- `Environmetrics/retrospective_log_discharge_plot_faceted.png` -> referenced in `Environmetrics_Figures.ipynb` (source unclear).
- `Environmetrics/forecats.png` -> `Environmetrics_Figures.ipynb`.
- `Environmetrics/80_component_1991_2022.png` -> `Environmetrics_Figures.ipynb` (filename referenced, save commented).
- `Environmetrics/All_exal_2012-2016_DISC.png` -> `Environmetrics_Figures.ipynb`.
- `Environmetrics/All_exal_2017-2019_DISC.png` -> `Environmetrics_Figures.ipynb`.
- `Environmetrics/posterior_samples_valid.png` -> `Environmetrics_Figures.ipynb`.
- `Environmetrics/posterior_samples_counter_valid.png` -> `Environmetrics_Figures.ipynb`.
- `article.txt` uses `DISC/*.png` paths; these currently map to `Environmetrics/*.png`.
