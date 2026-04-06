#!/usr/bin/env Rscript

args <- commandArgs(trailingOnly = TRUE)

usage <- function() {
  cat(
    paste(
      "Usage:",
      "Rscript --vanilla scripts/build_detclim_ab_config.R",
      "--base-config <yaml>",
      "--source-run-root <run_root>",
      "--scenario <observed|precip_only|soil_only|both>",
      "--out-config <yaml>",
      "--run-id <run_id>",
      "[--precip-reduction <mean|median>]",
      "[--precip-dry-threshold-mm <number>]",
      "[--precip-tail-blend-target <climatology_mean|climatology_median|zero>]",
      "[--precip-tail-blend-start-day <integer>]",
      "[--precip-tail-blend-end-day <integer>]",
      "[--soil-reduction <mean|median>]",
      "[--post]",
      sep = " "
    ),
    "\n"
  )
}

parse_args <- function(args) {
  opts <- list(
    base_config = NULL,
    source_run_root = NULL,
    scenario = NULL,
    out_config = NULL,
    run_id = NULL,
    precip_reduction = NULL,
    precip_dry_threshold_mm = NULL,
    precip_tail_blend_target = NULL,
    precip_tail_blend_start_day = NULL,
    precip_tail_blend_end_day = NULL,
    soil_reduction = NULL,
    enable_post = FALSE
  )

  i <- 1L
  while (i <= length(args)) {
    arg <- args[[i]]
    if (identical(arg, "--base-config")) {
      opts$base_config <- args[[i + 1L]]
      i <- i + 2L
      next
    }
    if (identical(arg, "--source-run-root")) {
      opts$source_run_root <- args[[i + 1L]]
      i <- i + 2L
      next
    }
    if (identical(arg, "--scenario")) {
      opts$scenario <- args[[i + 1L]]
      i <- i + 2L
      next
    }
    if (identical(arg, "--out-config")) {
      opts$out_config <- args[[i + 1L]]
      i <- i + 2L
      next
    }
    if (identical(arg, "--run-id")) {
      opts$run_id <- args[[i + 1L]]
      i <- i + 2L
      next
    }
    if (identical(arg, "--precip-reduction")) {
      opts$precip_reduction <- args[[i + 1L]]
      i <- i + 2L
      next
    }
    if (identical(arg, "--precip-dry-threshold-mm")) {
      opts$precip_dry_threshold_mm <- args[[i + 1L]]
      i <- i + 2L
      next
    }
    if (identical(arg, "--precip-tail-blend-target")) {
      opts$precip_tail_blend_target <- args[[i + 1L]]
      i <- i + 2L
      next
    }
    if (identical(arg, "--precip-tail-blend-start-day")) {
      opts$precip_tail_blend_start_day <- args[[i + 1L]]
      i <- i + 2L
      next
    }
    if (identical(arg, "--precip-tail-blend-end-day")) {
      opts$precip_tail_blend_end_day <- args[[i + 1L]]
      i <- i + 2L
      next
    }
    if (identical(arg, "--soil-reduction")) {
      opts$soil_reduction <- args[[i + 1L]]
      i <- i + 2L
      next
    }
    if (identical(arg, "--post")) {
      opts$enable_post <- TRUE
      i <- i + 1L
      next
    }
    stop(sprintf("Unknown argument: %s", arg), call. = FALSE)
  }

  required <- c("base_config", "source_run_root", "scenario", "out_config", "run_id")
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

scenario <- tolower(trimws(as.character(opts$scenario)))
if (!(scenario %in% c("observed", "precip_only", "soil_only", "both"))) {
  stop("scenario must be one of: observed, precip_only, soil_only, both", call. = FALSE)
}
normalize_reduction <- function(x, label) {
  if (is.null(x) || !nzchar(as.character(x))) return(NULL)
  value <- tolower(trimws(as.character(x)))
  if (!(value %in% c("mean", "median"))) {
    stop(sprintf("%s must be one of: mean, median", label), call. = FALSE)
  }
  value
}
precip_reduction <- normalize_reduction(opts$precip_reduction, "--precip-reduction")
soil_reduction <- normalize_reduction(opts$soil_reduction, "--soil-reduction")
precip_dry_threshold_mm <- NULL
if (!is.null(opts$precip_dry_threshold_mm) && nzchar(as.character(opts$precip_dry_threshold_mm))) {
  precip_dry_threshold_mm <- suppressWarnings(as.numeric(opts$precip_dry_threshold_mm))
  if (!is.finite(precip_dry_threshold_mm) || precip_dry_threshold_mm < 0) {
    stop("--precip-dry-threshold-mm must be numeric >= 0", call. = FALSE)
  }
}
precip_tail_blend_target <- NULL
if (!is.null(opts$precip_tail_blend_target) && nzchar(as.character(opts$precip_tail_blend_target))) {
  precip_tail_blend_target <- tolower(trimws(as.character(opts$precip_tail_blend_target)))
  if (!(precip_tail_blend_target %in% c("climatology_mean", "climatology_median", "zero"))) {
    stop(
      "--precip-tail-blend-target must be one of: climatology_mean, climatology_median, zero",
      call. = FALSE
    )
  }
}
precip_tail_blend_start_day <- NULL
if (!is.null(opts$precip_tail_blend_start_day) && nzchar(as.character(opts$precip_tail_blend_start_day))) {
  precip_tail_blend_start_day <- suppressWarnings(as.integer(opts$precip_tail_blend_start_day))
  if (!is.finite(precip_tail_blend_start_day) || precip_tail_blend_start_day < 1L) {
    stop("--precip-tail-blend-start-day must be an integer >= 1", call. = FALSE)
  }
}
precip_tail_blend_end_day <- NULL
if (!is.null(opts$precip_tail_blend_end_day) && nzchar(as.character(opts$precip_tail_blend_end_day))) {
  precip_tail_blend_end_day <- suppressWarnings(as.integer(opts$precip_tail_blend_end_day))
  if (!is.finite(precip_tail_blend_end_day) || precip_tail_blend_end_day < 1L) {
    stop("--precip-tail-blend-end-day must be an integer >= 1", call. = FALSE)
  }
}
if (!is.null(precip_tail_blend_start_day) && !is.null(precip_tail_blend_end_day) &&
    precip_tail_blend_end_day < precip_tail_blend_start_day) {
  stop("--precip-tail-blend-end-day must be >= --precip-tail-blend-start-day", call. = FALSE)
}

base_config <- path.expand(as.character(opts$base_config))
source_run_root <- normalizePath(path.expand(as.character(opts$source_run_root)), mustWork = TRUE)
out_config <- path.expand(as.character(opts$out_config))
dir.create(dirname(out_config), recursive = TRUE, showWarnings = FALSE)

cfg <- yaml::read_yaml(base_config)

shared_root <- file.path(source_run_root, "inputs", "shared")
must_files <- c(
  parameters = file.path(shared_root, "parameters", "parameters.txt"),
  retros = file.path(shared_root, "retros", "retros.csv"),
  nws = file.path(shared_root, "forecasts", "nws_forecast.csv"),
  glofas = file.path(shared_root, "forecasts", "glofas_forecast.csv")
)
missing_files <- must_files[!file.exists(must_files)]
if (length(missing_files) > 0L) {
  stop(
    sprintf(
      "source_run_root is missing required shared inputs: %s",
      paste(names(missing_files), collapse = ", ")
    ),
    call. = FALSE
  )
}

cfg$run$run_id <- as.character(opts$run_id)
cfg$run$overwrite <- TRUE
cfg$run$auto_suffix_on_collision <- FALSE

cfg$stages$forecats <- FALSE
cfg$stages$data_prep_shared <- TRUE
cfg$stages$fit <- TRUE
cfg$stages$post <- isTRUE(opts$enable_post)
cfg$stages$validate <- FALSE
cfg$stages$report <- FALSE

cfg$models$run_exdqlm_multivar <- TRUE
cfg$models$run_exdqlm_univar <- FALSE
cfg$models$run_ndlm_main <- FALSE
cfg$models$exdqlm_multivar$forecast_transfer_mode <- "keep"
cfg$models$exdqlm_multivar$forecast_transfer_modes <- list("keep")

cfg$fit$quantiles <- list(0.95)
cfg$fit$parallel$mode <- "one_core_per_model"
cfg$fit$parallel$workers <- 1L

cfg$inputs$shared$prefer_forecats_snapshot <- FALSE
cfg$inputs$fit$parameters_path <- must_files[["parameters"]]
cfg$inputs$fit$retros_path <- must_files[["retros"]]
cfg$inputs$fit$nws_forecast_path <- must_files[["nws"]]
cfg$inputs$fit$glofas_forecast_path <- must_files[["glofas"]]

cfg$inputs$deterministic_climate$enabled <- !identical(scenario, "observed")
cfg$inputs$deterministic_climate$precip$enabled <- scenario %in% c("precip_only", "both")
cfg$inputs$deterministic_climate$soil$enabled <- scenario %in% c("soil_only", "both")
if (!is.null(precip_reduction)) {
  cfg$inputs$deterministic_climate$precip$reduction <- precip_reduction
}
if (!is.null(precip_dry_threshold_mm)) {
  cfg$inputs$deterministic_climate$precip$dry_day_threshold_mm <- precip_dry_threshold_mm
}
if (!is.null(precip_tail_blend_target) || !is.null(precip_tail_blend_start_day) || !is.null(precip_tail_blend_end_day)) {
  cfg$inputs$deterministic_climate$precip$tail_blend$enabled <- TRUE
}
if (!is.null(precip_tail_blend_target)) {
  cfg$inputs$deterministic_climate$precip$tail_blend$target <- precip_tail_blend_target
}
if (!is.null(precip_tail_blend_start_day)) {
  cfg$inputs$deterministic_climate$precip$tail_blend$start_day <- precip_tail_blend_start_day
}
if (!is.null(precip_tail_blend_end_day)) {
  cfg$inputs$deterministic_climate$precip$tail_blend$end_day <- precip_tail_blend_end_day
}
if (!is.null(soil_reduction)) {
  cfg$inputs$deterministic_climate$soil$reduction <- soil_reduction
}

meta_block <- list(
  scenario = scenario,
  precip_reduction = cfg$inputs$deterministic_climate$precip$reduction,
  precip_dry_threshold_mm = cfg$inputs$deterministic_climate$precip$dry_day_threshold_mm,
  precip_tail_blend = cfg$inputs$deterministic_climate$precip$tail_blend,
  soil_reduction = cfg$inputs$deterministic_climate$soil$reduction,
  source_run_root = normalizePath(source_run_root, mustWork = FALSE),
  source_shared_root = normalizePath(shared_root, mustWork = FALSE),
  post_enabled = isTRUE(opts$enable_post)
)
cfg$debug_detclim_ab <- meta_block

yaml_txt <- yaml::as.yaml(cfg, indent.mapping.sequence = TRUE)
writeLines(yaml_txt, con = out_config, useBytes = TRUE)

cat(sprintf("Wrote %s\n", normalizePath(out_config, mustWork = FALSE)))
