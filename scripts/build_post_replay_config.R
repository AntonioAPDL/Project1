#!/usr/bin/env Rscript

args <- commandArgs(trailingOnly = TRUE)

usage <- function() {
  cat(
    paste(
      "Usage:",
      "Rscript --vanilla scripts/build_post_replay_config.R",
      "--base-config <yaml>",
      "--source-run-id <run_id>",
      "--out-config <yaml>",
      "--run-id <run_id>",
      "[--source-run-root <dir>]",
      sep = " "
    ),
    "\n"
  )
}

parse_args <- function(args) {
  opts <- list(
    base_config = NULL,
    source_run_id = NULL,
    source_run_root = NULL,
    out_config = NULL,
    run_id = NULL
  )
  i <- 1L
  while (i <= length(args)) {
    arg <- args[[i]]
    if (identical(arg, "--base-config")) {
      opts$base_config <- args[[i + 1L]]
      i <- i + 2L
      next
    }
    if (identical(arg, "--source-run-id")) {
      opts$source_run_id <- args[[i + 1L]]
      i <- i + 2L
      next
    }
    if (identical(arg, "--source-run-root")) {
      opts$source_run_root <- args[[i + 1L]]
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
    stop(sprintf("Unknown argument: %s", arg), call. = FALSE)
  }

  required <- c("base_config", "source_run_id", "out_config", "run_id")
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

base_config <- path.expand(as.character(opts$base_config))
out_config <- path.expand(as.character(opts$out_config))
dir.create(dirname(out_config), recursive = TRUE, showWarnings = FALSE)

cfg <- yaml::read_yaml(base_config)
source_run_root <- opts$source_run_root
if (is.null(source_run_root) || !nzchar(as.character(source_run_root))) {
  source_run_root <- cfg$run$run_root
}
source_run_root <- normalizePath(path.expand(as.character(source_run_root)), mustWork = TRUE)
if (identical(basename(source_run_root), as.character(opts$source_run_id))) {
  source_run_root <- dirname(source_run_root)
}

cfg$run$run_id <- as.character(opts$run_id)
cfg$run$overwrite <- TRUE
cfg$run$auto_suffix_on_collision <- FALSE

cfg$stages$forecats <- FALSE
cfg$stages$data_prep_shared <- FALSE
cfg$stages$fit <- FALSE
cfg$stages$post <- TRUE
cfg$stages$validate <- FALSE
cfg$stages$report <- FALSE

cfg$inputs$post$use_fit_outputs_from_run <- TRUE
cfg$inputs$post$source_run_id <- as.character(opts$source_run_id)
cfg$inputs$post$source_run_root <- source_run_root

cfg$debug_post_replay <- list(
  source_run_id = as.character(opts$source_run_id),
  source_run_root = source_run_root
)

yaml_txt <- yaml::as.yaml(cfg, indent.mapping.sequence = TRUE)
writeLines(yaml_txt, con = out_config, useBytes = TRUE)

cat(sprintf("Wrote %s\n", normalizePath(out_config, mustWork = FALSE)))
