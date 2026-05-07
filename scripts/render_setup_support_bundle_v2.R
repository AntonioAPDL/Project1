#!/usr/bin/env Rscript

parse_args <- function(argv) {
  out <- list()
  i <- 1L
  while (i <= length(argv)) {
    key <- argv[[i]]
    if (!startsWith(key, "--")) stop(sprintf("Unexpected argument: %s", key), call. = FALSE)
    if (i == length(argv)) stop(sprintf("Missing value for %s", key), call. = FALSE)
    out[[sub("^--", "", key)]] <- argv[[i + 1L]]
    i <- i + 2L
  }
  out
}

args <- parse_args(commandArgs(trailingOnly = TRUE))
required <- c("project-root", "selected-run-root", "figure-bundle-root", "bundle-class", "output-dir", "support-start", "cutoff-date")
missing <- required[!vapply(required, function(k) !is.null(args[[k]]) && nzchar(args[[k]]), logical(1))]
if (length(missing) > 0L) {
  stop(sprintf("Missing required args: %s", paste(missing, collapse = ", ")), call. = FALSE)
}

project_root <- normalizePath(args[["project-root"]], mustWork = TRUE)
selected_run_root <- normalizePath(args[["selected-run-root"]], mustWork = TRUE)
figure_bundle_root <- normalizePath(args[["figure-bundle-root"]], mustWork = TRUE)
out_dir <- normalizePath(args[["output-dir"]], mustWork = FALSE)
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

support_start <- as.Date(args[["support-start"]])
cutoff_date <- as.Date(args[["cutoff-date"]])
bundle_class <- args[["bundle-class"]]

helper_path <- file.path(project_root, "scripts", "setup_support_bundle_v2_helpers.R")
source(helper_path, local = .GlobalEnv)
source(file.path(project_root, "scripts", "forecats_plot_bundle.R"), local = .GlobalEnv)

selected_usgs_path <- require_existing_path(file.path(selected_run_root, "inputs", "shared", "usgs", "usgs_daily.csv"), "selected-run USGS")
ppt_path <- require_existing_path(file.path(selected_run_root, "inputs", "shared", "covariates", "cov_01_PPT.csv"), "selected-run PPT covariate")
soil_path <- require_existing_path(file.path(selected_run_root, "inputs", "shared", "covariates", "cov_02_SOIL.csv"), "selected-run SOIL covariate")
pca_path <- require_existing_path(file.path(selected_run_root, "inputs", "shared", "covariates", "cov_03_PCA.csv"), "selected-run PCA covariate")

meta <- read_bundle_meta(figure_bundle_root)
plot_scale <- as.character(meta$transforms$plot_scale %||% "log_log1p_cms")
plot_start <- safe_date(meta$dates$plot_start %||% support_start)
plot_end <- safe_date(meta$dates$plot_end %||% cutoff_date)

usgs_df <- read_usgs_history(selected_usgs_path, support_start = support_start, cutoff_date = cutoff_date)
if (nrow(usgs_df) == 0L) {
  stop("USGS history resolved to zero rows for the requested support window.", call. = FALSE)
}

covariate_df <- bind_rows(
  read_covariate_series(ppt_path, support_start, cutoff_date, "Precipitation", c("PRCP_mm", "ppt", "PPT")),
  read_covariate_series(soil_path, support_start, cutoff_date, "Soil_Moisture", c("Daily_Avg_Soil_Moisture", "soil", "SOIL")),
  read_covariate_series(pca_path, support_start, cutoff_date, "Climate_PC1", c("Static_PCA", "PCA"))
) %>%
  mutate(Variable = factor(Variable, levels = c("Precipitation", "Soil_Moisture", "Climate_PC1")))

retros_long <- build_retros_long_selected(
  bundle_root = figure_bundle_root,
  bundle_class = bundle_class,
  support_start = support_start,
  plot_end = plot_end,
  cutoff_date = cutoff_date
)
retros_wide <- build_retros_wide_for_history(retros_long, cutoff_date = cutoff_date)
if (nrow(retros_wide) == 0L) {
  stop("Retrospective history resolved to zero rows for the requested support window.", call. = FALSE)
}

plot_usgs_png(
  out_path = file.path(out_dir, "usgs.png"),
  usgs_df = usgs_df,
  cutoff_date = cutoff_date,
  support_start = support_start,
  plot_scale = plot_scale
)
plot_covariates_png(
  out_path = file.path(out_dir, "precip_soilmoisture_climatePC1_faceted_labeled.png"),
  covariate_df = covariate_df,
  cutoff_date = cutoff_date,
  support_start = support_start
)
plot_retrospective_png(
  out_path = file.path(out_dir, "retrospective_log_discharge_plot_faceted.png"),
  retros_wide = retros_wide,
  cutoff_date = cutoff_date,
  support_start = support_start,
  plot_scale = plot_scale
)

stage_dir <- file.path(tempdir(check = TRUE), paste0("setup_support_stage_", format(cutoff_date, "%Y%m%d")))
unlink(stage_dir, recursive = TRUE, force = TRUE)
stage_forecats_bundle(
  bundle_root = figure_bundle_root,
  selected_usgs_path = selected_usgs_path,
  retros_long = retros_long,
  stage_dir = stage_dir
)
plot_forecats_bundle(stage_dir)
file.copy(file.path(stage_dir, "figures", "forecats.png"), file.path(out_dir, "forecats.png"), overwrite = TRUE)

cat(sprintf("Rendered v2 setup/support figures for cutoff %s into %s\n", format(cutoff_date, "%Y-%m-%d"), out_dir))
