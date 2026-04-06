#!/usr/bin/env Rscript

suppressPackageStartupMessages(library(yaml))

repo_root <- normalizePath(
  Sys.getenv("REPO_ROOT", "/data/muscat_data/jaguir26/project1_ucsc_phd"),
  mustWork = TRUE
)
cfg_dir <- file.path(repo_root, "config", "unified_runs")

read_yaml_rel <- function(path) {
  read_yaml(file.path(repo_root, path))
}

write_yaml_rel <- function(x, path) {
  write_yaml(x, file.path(repo_root, path))
}

template_l1 <- read_yaml_rel("config/unified_runs/prod_phaseK3_batchA_20210123_l1_20260324.yaml")
template_l2 <- read_yaml_rel("config/unified_runs/prod_phaseK3_batchA_20210123_l2_20260324.yaml")

cutoff_specs <- list(
  list(
    cutoff_compact = "20211221",
    cutoff_date = "2021-12-21",
    plot_start = "2021-12-03",
    plot_end = "2022-01-18",
    batch = "batchB",
    multimodel_run = "multimodel_20211221"
  ),
  list(
    cutoff_compact = "20220511",
    cutoff_date = "2022-05-11",
    plot_start = "2022-04-23",
    plot_end = "2022-06-08",
    batch = "batchB",
    multimodel_run = "multimodel_20220511"
  ),
  list(
    cutoff_compact = "20221225",
    cutoff_date = "2022-12-25",
    plot_start = "2022-12-07",
    plot_end = "2023-01-22",
    batch = "batchC",
    multimodel_run = "multimodel_20221225"
  )
)

bundle_path <- function(multimodel_run, rel_path) {
  file.path(repo_root, "repro", "runs", multimodel_run, "inputs", "shared", "forecats_bundle", rel_path)
}

set_cutoff_paths <- function(cfg, spec, lane) {
  cfg$run$run_id <- sprintf("prod_phaseK3_%s_%s_%s_20260324", spec$batch, spec$cutoff_compact, lane)
  cfg$dates$cutoff_date <- spec$cutoff_date
  cfg$dates$plot_start <- spec$plot_start
  cfg$dates$plot_end <- spec$plot_end
  cfg$inputs$fit$retros_path <- bundle_path(spec$multimodel_run, "retros.csv")
  cfg$inputs$fit$nws_forecast_path <- bundle_path(spec$multimodel_run, "nws_forecast.csv")
  cfg$inputs$fit$glofas_forecast_path <- bundle_path(spec$multimodel_run, "glofas_forecast.csv")
  cfg
}

generated <- character(0)

for (spec in cutoff_specs) {
  cfg_l1 <- set_cutoff_paths(template_l1, spec, "l1")
  cfg_l2 <- set_cutoff_paths(template_l2, spec, "l2")

  out_l1 <- file.path("config", "unified_runs", sprintf("prod_phaseK3_%s_%s_l1_20260324.yaml", spec$batch, spec$cutoff_compact))
  out_l2 <- file.path("config", "unified_runs", sprintf("prod_phaseK3_%s_%s_l2_20260324.yaml", spec$batch, spec$cutoff_compact))

  write_yaml_rel(cfg_l1, out_l1)
  write_yaml_rel(cfg_l2, out_l2)
  generated <- c(generated, out_l1, out_l2)
}

cat(paste(generated, collapse = "\n"))
cat("\n")
