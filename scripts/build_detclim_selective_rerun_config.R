#!/usr/bin/env Rscript

args <- commandArgs(trailingOnly = TRUE)

usage <- function() {
  cat(
    paste(
      "Usage:",
      "Rscript --vanilla scripts/build_detclim_selective_rerun_config.R",
      "--base-config <yaml>",
      "--out-config <yaml>",
      "--phase <data_prep|fit_keep_univar|post_all>",
      "--phase <data_prep|fit_keep_univar|fit_multivar_dual_univar|fit_multivar_dual_only|post_all|post_multivar_only>",
      sep = " "
    ),
    "\n"
  )
}

parse_args <- function(args) {
  opts <- list(
    base_config = NULL,
    out_config = NULL,
    phase = NULL
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
    if (identical(arg, "--phase")) {
      opts$phase <- args[[i + 1L]]
      i <- i + 2L
      next
    }
    stop(sprintf("Unknown argument: %s", arg), call. = FALSE)
  }
  required <- c("base_config", "out_config", "phase")
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

phase <- tolower(trimws(as.character(opts$phase)))
if (!(phase %in% c("data_prep", "fit_keep_univar", "fit_multivar_dual_univar", "fit_multivar_dual_only", "post_all", "post_multivar_only"))) {
  stop("--phase must be one of: data_prep, fit_keep_univar, fit_multivar_dual_univar, fit_multivar_dual_only, post_all, post_multivar_only", call. = FALSE)
}

base_config <- normalizePath(path.expand(as.character(opts$base_config)), mustWork = TRUE)
out_config <- path.expand(as.character(opts$out_config))
dir.create(dirname(out_config), recursive = TRUE, showWarnings = FALSE)

cfg <- yaml::read_yaml(base_config)

cfg$run$overwrite <- TRUE
cfg$run$auto_suffix_on_collision <- FALSE

# Force the new deterministic-climate policy used by the latest comparison plots.
cfg$inputs$deterministic_climate$enabled <- TRUE
cfg$inputs$deterministic_climate$precip$enabled <- TRUE
cfg$inputs$deterministic_climate$soil$enabled <- TRUE
cfg$inputs$deterministic_climate$precip$reduction <- "q70"
cfg$inputs$deterministic_climate$soil$reduction <- "q70"
cfg$inputs$deterministic_climate$precip$noisy_blend$enabled <- TRUE
cfg$inputs$deterministic_climate$precip$noisy_blend$lambda_mode <- "dynamic"
cfg$inputs$deterministic_climate$precip$noisy_blend$lambda_start <- 0.8
cfg$inputs$deterministic_climate$precip$noisy_blend$lambda_end <- 0.2
cfg$inputs$deterministic_climate$precip$noisy_blend$noise_sd_multiplier <- 1.0
cfg$inputs$deterministic_climate$precip$noisy_blend$noise_seed <- 20260309L
cfg$inputs$deterministic_climate$precip$noisy_blend$floor_at_zero <- TRUE
cfg$inputs$deterministic_climate$precip$noisy_blend$zero_zero_force_prob <- 0.9
cfg$inputs$deterministic_climate$soil$noisy_blend$enabled <- TRUE
cfg$inputs$deterministic_climate$soil$noisy_blend$lambda_mode <- "dynamic"
cfg$inputs$deterministic_climate$soil$noisy_blend$lambda_start <- 0.8
cfg$inputs$deterministic_climate$soil$noisy_blend$lambda_end <- 0.2
cfg$inputs$deterministic_climate$soil$noisy_blend$noise_sd_multiplier <- 1.0
cfg$inputs$deterministic_climate$soil$noisy_blend$noise_seed <- 20260309L
cfg$inputs$deterministic_climate$soil$noisy_blend$floor_at_zero <- FALSE

if (identical(phase, "data_prep")) {
  cfg$stages$forecats <- FALSE
  cfg$stages$data_prep_shared <- TRUE
  cfg$stages$fit <- FALSE
  cfg$stages$post <- FALSE
  cfg$stages$validate <- FALSE
  cfg$stages$report <- FALSE
} else if (identical(phase, "fit_keep_univar")) {
  cfg$stages$forecats <- FALSE
  cfg$stages$data_prep_shared <- TRUE
  cfg$stages$fit <- TRUE
  cfg$stages$post <- FALSE
  cfg$stages$validate <- FALSE
  cfg$stages$report <- FALSE

  cfg$models$run_exdqlm_multivar <- TRUE
  cfg$models$run_exdqlm_univar <- TRUE
  cfg$models$run_ndlm_main <- FALSE
  cfg$models$exdqlm_multivar$forecast_transfer_mode <- "keep"
  cfg$models$exdqlm_multivar$forecast_transfer_modes <- list("keep")
} else if (identical(phase, "fit_multivar_dual_univar")) {
  cfg$stages$forecats <- FALSE
  cfg$stages$data_prep_shared <- TRUE
  cfg$stages$fit <- TRUE
  cfg$stages$post <- FALSE
  cfg$stages$validate <- FALSE
  cfg$stages$report <- FALSE

  cfg$models$run_exdqlm_multivar <- TRUE
  cfg$models$run_exdqlm_univar <- TRUE
  cfg$models$run_ndlm_main <- FALSE
  cfg$models$exdqlm_multivar$forecast_transfer_mode <- "drop"
  cfg$models$exdqlm_multivar$forecast_transfer_modes <- list("drop", "keep")
} else if (identical(phase, "fit_multivar_dual_only")) {
  cfg$stages$forecats <- FALSE
  cfg$stages$data_prep_shared <- FALSE
  cfg$stages$fit <- TRUE
  cfg$stages$post <- FALSE
  cfg$stages$validate <- FALSE
  cfg$stages$report <- FALSE

  cfg$models$run_exdqlm_multivar <- TRUE
  cfg$models$run_exdqlm_univar <- FALSE
  cfg$models$run_ndlm_main <- FALSE
  cfg$models$exdqlm_multivar$forecast_transfer_mode <- "drop"
  cfg$models$exdqlm_multivar$forecast_transfer_modes <- list("drop", "keep")
} else if (identical(phase, "post_all")) {
  cfg$stages$forecats <- FALSE
  cfg$stages$data_prep_shared <- FALSE
  cfg$stages$fit <- FALSE
  cfg$stages$post <- TRUE
  cfg$stages$validate <- FALSE
  cfg$stages$report <- FALSE

  cfg$models$run_exdqlm_multivar <- TRUE
  cfg$models$run_exdqlm_univar <- TRUE
  cfg$models$run_ndlm_main <- TRUE
  cfg$models$exdqlm_multivar$forecast_transfer_mode <- "drop"
  cfg$models$exdqlm_multivar$forecast_transfer_modes <- list("drop", "keep")
  cfg$inputs$post$use_fit_outputs_from_run <- TRUE
  cfg$inputs$post$source_run_id <- NULL
  cfg$inputs$post$source_run_root <- cfg$run$run_root
} else if (identical(phase, "post_multivar_only")) {
  cfg$stages$forecats <- FALSE
  cfg$stages$data_prep_shared <- FALSE
  cfg$stages$fit <- FALSE
  cfg$stages$post <- TRUE
  cfg$stages$validate <- FALSE
  cfg$stages$report <- FALSE

  cfg$models$run_exdqlm_multivar <- TRUE
  cfg$models$run_exdqlm_univar <- FALSE
  cfg$models$run_ndlm_main <- FALSE
  cfg$models$exdqlm_multivar$forecast_transfer_mode <- "drop"
  cfg$models$exdqlm_multivar$forecast_transfer_modes <- list("drop", "keep")
  cfg$inputs$post$use_fit_outputs_from_run <- TRUE
  cfg$inputs$post$source_run_id <- NULL
  cfg$inputs$post$source_run_root <- cfg$run$run_root
}

cfg$debug_detclim_selective_rerun <- list(
  phase = phase,
  precip_reduction = cfg$inputs$deterministic_climate$precip$reduction,
  soil_reduction = cfg$inputs$deterministic_climate$soil$reduction,
  precip_noisy_blend = cfg$inputs$deterministic_climate$precip$noisy_blend,
  soil_noisy_blend = cfg$inputs$deterministic_climate$soil$noisy_blend
)

yaml_txt <- yaml::as.yaml(cfg, indent.mapping.sequence = TRUE)
writeLines(yaml_txt, con = out_config, useBytes = TRUE)
cat(sprintf("Wrote %s\n", normalizePath(out_config, mustWork = FALSE)))
