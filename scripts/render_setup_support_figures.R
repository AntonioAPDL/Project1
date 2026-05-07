#!/usr/bin/env Rscript

parse_args <- function(args) {
  out <- list()
  i <- 1L
  while (i <= length(args)) {
    key <- args[[i]]
    if (!startsWith(key, "--")) stop(sprintf("Unexpected argument: %s", key), call. = FALSE)
    if (i == length(args)) stop(sprintf("Missing value for %s", key), call. = FALSE)
    out[[sub("^--", "", key)]] <- args[[i + 1L]]
    i <- i + 2L
  }
  out
}

args <- parse_args(commandArgs(trailingOnly = TRUE))
required <- c("project-root", "run-root", "output-dir")
missing <- required[!vapply(required, function(k) !is.null(args[[k]]) && nzchar(args[[k]]), logical(1))]
if (length(missing) > 0L) {
  stop(sprintf("Missing required args: %s", paste(missing, collapse = ", ")), call. = FALSE)
}

project_root <- normalizePath(args[["project-root"]], mustWork = TRUE)
run_root <- normalizePath(args[["run-root"]], mustWork = TRUE)
output_dir <- normalizePath(args[["output-dir"]], mustWork = FALSE)
dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

shared_root <- file.path(run_root, "inputs", "shared")
required_paths <- c(
  retros = file.path(shared_root, "retros", "retros.csv"),
  nws = file.path(shared_root, "forecasts", "nws_forecast.csv"),
  glofas = file.path(shared_root, "forecasts", "glofas_forecast.csv"),
  usgs = file.path(shared_root, "usgs", "usgs_daily.csv"),
  ppt = file.path(shared_root, "covariates", "cov_01_PPT.csv"),
  soil = file.path(shared_root, "covariates", "cov_02_SOIL.csv"),
  pca = file.path(shared_root, "covariates", "cov_03_PCA.csv"),
  features = file.path(shared_root, "covariates", "covariate_features.csv")
)
missing_inputs <- names(required_paths)[!file.exists(required_paths)]
if (length(missing_inputs) > 0L) {
  stop(sprintf("Missing required run-scoped shared inputs: %s", paste(missing_inputs, collapse = ", ")), call. = FALSE)
}

Sys.setenv(
  ENV_PROJECT_ROOT = project_root,
  ENV_RETROS_PATH = required_paths[["retros"]],
  ENV_NWS_FORECAST_PATH = required_paths[["nws"]],
  ENV_GLOFAS_FORECAST_PATH = required_paths[["glofas"]],
  ENV_USGS_DAILY_PATH = required_paths[["usgs"]],
  ENV_PPT_PATH = required_paths[["ppt"]],
  ENV_SOIL_PATH = required_paths[["soil"]],
  ENV_PCA_PATH = required_paths[["pca"]],
  ENV_COVARIATE_FEATURES_PATH = required_paths[["features"]],
  UNIFIED_COVARIATE_FEATURES_CSV = required_paths[["features"]],
  UNIFIED_CUTOFF_DATE = if (!is.null(args[["cutoff-date"]])) args[["cutoff-date"]] else "",
  UNIFIED_FORECAST_START_DATE = if (!is.null(args[["forecast-start-date"]])) args[["forecast-start-date"]] else "",
  UNIFIED_PLOT_START = if (!is.null(args[["plot-start"]])) args[["plot-start"]] else "",
  UNIFIED_PLOT_END = if (!is.null(args[["plot-end"]])) args[["plot-end"]] else "",
  UNIFIED_FORECAST_EVENT_DATE = if (!is.null(args[["event-date"]])) args[["event-date"]] else "",
  UNIFIED_FORECAST_EVENT_LABEL = if (!is.null(args[["event-label"]])) args[["event-label"]] else ""
)

modules_dir <- file.path(project_root, "R", "environmetrics")
module_paths <- c(
  file.path(modules_dir, "00_paths.R"),
  file.path(modules_dir, "00_setup.R"),
  file.path(modules_dir, "00_constants.R"),
  file.path(modules_dir, "01_config.R"),
  file.path(modules_dir, "02_helpers_core.R"),
  file.path(modules_dir, "utils_data.R"),
  file.path(modules_dir, "utils_plot.R")
)
missing_modules <- module_paths[!file.exists(module_paths)]
if (length(missing_modules) > 0L) {
  stop(sprintf("Missing required module files: %s", paste(missing_modules, collapse = ", ")), call. = FALSE)
}

for (mod in module_paths) {
  source(mod, local = .GlobalEnv)
}

DATA_CBIND_RDS <- file.path(output_dir, "data_cbind_tY_X.rds")
DATA_CBIND_CSV <- file.path(output_dir, "data_cbind_tY_X.csv")
OUT_DIR <- output_dir

source(file.path(modules_dir, "10_data_inputs.R"), local = .GlobalEnv)
source(file.path(modules_dir, "40_figures_setup_support.R"), local = .GlobalEnv)

cat(sprintf("Rendered setup/support figures into %s\n", output_dir))
