#!/usr/bin/env Rscript

args <- commandArgs(trailingOnly = TRUE)

usage <- function() {
  cat(
    paste(
      "Usage:",
      "Rscript --vanilla scripts/build_unified_fullhist_rerun_config.R",
      "--base-config <yaml>",
      "--out-config <yaml>",
      "--out-forecats-config <yaml>",
      "--data-start YYYY-MM-DD",
      sep = " "
    ),
    "\n"
  )
}

parse_args <- function(args) {
  opts <- list(
    base_config = NULL,
    out_config = NULL,
    out_forecats_config = NULL,
    data_start = NULL
  )
  i <- 1L
  while (i <= length(args)) {
    arg <- args[[i]]
    if (identical(arg, "--base-config")) {
      opts$base_config <- args[[i + 1L]]
      i <- i + 2L
      next
    }
    if (identical(arg, "--out-config")) {
      opts$out_config <- args[[i + 1L]]
      i <- i + 2L
      next
    }
    if (identical(arg, "--out-forecats-config")) {
      opts$out_forecats_config <- args[[i + 1L]]
      i <- i + 2L
      next
    }
    if (identical(arg, "--data-start")) {
      opts$data_start <- args[[i + 1L]]
      i <- i + 2L
      next
    }
    stop(sprintf("Unknown argument: %s", arg), call. = FALSE)
  }

  required <- c("base_config", "out_config", "out_forecats_config", "data_start")
  missing <- required[vapply(required, function(x) {
    is.null(opts[[x]]) || !nzchar(as.character(opts[[x]]))
  }, logical(1))]
  if (length(missing) > 0L) {
    usage()
    stop(sprintf("Missing required arguments: %s", paste(missing, collapse = ", ")), call. = FALSE)
  }
  opts
}

opts <- parse_args(args)

if (!requireNamespace("yaml", quietly = TRUE)) {
  stop("Package 'yaml' is required", call. = FALSE)
}

`%||%` <- function(x, y) {
  if (is.null(x)) y else x
}

data_start <- suppressWarnings(as.Date(as.character(opts$data_start)))
if (is.na(data_start)) {
  stop("--data-start must be a valid YYYY-MM-DD date", call. = FALSE)
}

base_config <- normalizePath(path.expand(as.character(opts$base_config)), mustWork = TRUE)
out_config <- path.expand(as.character(opts$out_config))
out_forecats_config <- path.expand(as.character(opts$out_forecats_config))
dir.create(dirname(out_config), recursive = TRUE, showWarnings = FALSE)
dir.create(dirname(out_forecats_config), recursive = TRUE, showWarnings = FALSE)

cfg <- yaml::read_yaml(base_config)
forecats_template_path <- cfg$inputs$forecats$pipeline_config_path
if (is.null(forecats_template_path) || !nzchar(as.character(forecats_template_path))) {
  stop("inputs.forecats.pipeline_config_path is missing in base config", call. = FALSE)
}
forecats_template_path <- normalizePath(path.expand(as.character(forecats_template_path)), mustWork = TRUE)
forecats_cfg <- yaml::read_yaml(forecats_template_path)

run_id <- as.character(cfg$run$run_id %||% "")
cutoff_date <- as.character(cfg$dates$cutoff_date %||% "")
plot_start <- as.character(cfg$dates$plot_start %||% "")
plot_end <- as.character(cfg$dates$plot_end %||% "")
if (!nzchar(run_id) || !nzchar(cutoff_date) || !nzchar(plot_start) || !nzchar(plot_end)) {
  stop("Base config must define run.run_id and dates.cutoff_date/plot_start/plot_end", call. = FALSE)
}

cfg$run$overwrite <- TRUE
cfg$run$auto_suffix_on_collision <- FALSE
cfg$run$git_require_clean <- FALSE
cfg$run$dry_run <- FALSE

cfg$dates$data_start <- format(data_start, "%Y-%m-%d")

cfg$stages$forecats <- TRUE
cfg$stages$data_prep_shared <- TRUE
cfg$stages$fit <- TRUE
cfg$stages$post <- TRUE
cfg$stages$validate <- TRUE
cfg$stages$report <- TRUE

cfg$models$run_exdqlm_multivar <- TRUE
cfg$models$run_exdqlm_univar <- TRUE
cfg$models$run_ndlm_main <- TRUE
cfg$models$exdqlm_multivar$forecast_transfer_mode <- "drop"
cfg$models$exdqlm_multivar$forecast_transfer_modes <- list("drop", "keep")

cfg$inputs$forecats$mode <- "build"
cfg$inputs$forecats$pipeline_config_path <- normalizePath(out_forecats_config, mustWork = FALSE)
cfg$inputs$forecats$existing_bundle_path <- NULL
cfg$inputs$forecats$snapshot$enabled <- TRUE

if (is.null(cfg$inputs$post)) cfg$inputs$post <- list()
cfg$inputs$post$use_fit_outputs_from_run <- TRUE
cfg$inputs$post$source_run_id <- NULL
cfg$inputs$post$source_run_root <- cfg$run$run_root

if (is.null(forecats_cfg$run)) forecats_cfg$run <- list()
if (is.null(forecats_cfg$site)) forecats_cfg$site <- list()
if (is.null(forecats_cfg$dates)) forecats_cfg$dates <- list()
if (is.null(forecats_cfg$inputs)) forecats_cfg$inputs <- list()
if (is.null(forecats_cfg$inputs$retros)) forecats_cfg$inputs$retros <- list()

forecats_cfg$run$run_id <- sprintf("%s_fullhist_19870529", run_id)
forecats_cfg$run$out_root <- "repro/forecats_inputs_fullhist_19870529"
forecats_cfg$run$overwrite <- TRUE

forecats_cfg$site$usgs_site <- cfg$site$usgs_site
forecats_cfg$site$lat <- cfg$site$lat
forecats_cfg$site$lon <- cfg$site$lon

forecats_cfg$dates$cutoff_date <- cutoff_date
forecats_cfg$dates$plot_start <- plot_start
forecats_cfg$dates$plot_end <- plot_end

forecats_cfg$inputs$retros$path <- cfg$inputs$fit$retros_path
forecats_cfg$inputs$retros$scale <- cfg$inputs$fit$retros_storage_scale

yaml_txt <- yaml::as.yaml(cfg, indent.mapping.sequence = TRUE)
writeLines(yaml_txt, con = out_config, useBytes = TRUE)
fore_txt <- yaml::as.yaml(forecats_cfg, indent.mapping.sequence = TRUE)
writeLines(fore_txt, con = out_forecats_config, useBytes = TRUE)

cat(sprintf("Wrote unified config %s\n", normalizePath(out_config, mustWork = FALSE)))
cat(sprintf("Wrote forecats config %s\n", normalizePath(out_forecats_config, mustWork = FALSE)))
