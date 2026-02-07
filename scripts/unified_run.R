#!/usr/bin/env Rscript

args <- commandArgs(trailingOnly = TRUE)

usage <- function() {
  cat("Usage: Rscript --vanilla scripts/unified_run.R --config <yaml> [--dry-run]\n")
}

parse_args <- function(args) {
  config_path <- NULL
  dry_run <- FALSE

  i <- 1L
  while (i <= length(args)) {
    arg <- args[[i]]
    if (identical(arg, "--config")) {
      if (i == length(args)) stop("--config requires a value", call. = FALSE)
      config_path <- args[[i + 1L]]
      i <- i + 2L
      next
    }
    if (identical(arg, "--dry-run")) {
      dry_run <- TRUE
      i <- i + 1L
      next
    }
    stop(sprintf("Unknown argument: %s", arg), call. = FALSE)
  }

  if (is.null(config_path)) {
    usage()
    stop("--config is required", call. = FALSE)
  }

  list(config_path = config_path, dry_run = dry_run)
}

opts <- parse_args(args)
repo_root <- normalizePath(getwd(), mustWork = TRUE)

source(file.path(repo_root, "R", "unified", "utils_hash.R"))
source(file.path(repo_root, "R", "unified", "config.R"))
source(file.path(repo_root, "R", "unified", "determinism.R"))
source(file.path(repo_root, "R", "unified", "manifest.R"))

cfg <- unified_load_config(opts$config_path, repo_root = repo_root)

run_id <- cfg$run$run_id
if (is.null(run_id) || !nzchar(run_id)) {
  run_id <- format(Sys.time(), "%Y%m%d_%H%M%S")
}
run_root <- file.path(cfg$run$run_root, run_id)

if (dir.exists(run_root) && !isTRUE(cfg$run$overwrite)) {
  stop(sprintf("Run root exists and overwrite=false: %s", run_root), call. = FALSE)
}

dir.create(run_root, recursive = TRUE, showWarnings = FALSE)
dir.create(file.path(run_root, "validate"), recursive = TRUE, showWarnings = FALSE)
dir.create(file.path(run_root, "report"), recursive = TRUE, showWarnings = FALSE)
dir.create(file.path(run_root, "env"), recursive = TRUE, showWarnings = FALSE)

cfg$run$run_id <- run_id
cfg$run$resolved_run_root <- run_root
cfg$run$resolved_config_path <- normalizePath(opts$config_path, mustWork = FALSE)

if (!requireNamespace("yaml", quietly = TRUE)) {
  stop("Package 'yaml' is required", call. = FALSE)
}

resolved_config_path <- file.path(run_root, "resolved_config.yaml")
writeLines(yaml::as.yaml(cfg, indent.mapping.sequence = TRUE), con = resolved_config_path, useBytes = TRUE)

repro_record <- unified_apply_seed(seed = cfg$run$seed, mode = cfg$run$repro_mode)
manifest <- unified_manifest_init(cfg, run_id = run_id, run_root = run_root, repo_root = repo_root, repro_record = repro_record)
manifest_path <- file.path(run_root, "run_manifest.yaml")
unified_manifest_write(manifest, manifest_path)

enabled_stages <- names(cfg$stages)[vapply(cfg$stages, isTRUE, logical(1))]

cat("Unified run plan\n")
cat(sprintf("- config: %s\n", normalizePath(opts$config_path, mustWork = FALSE)))
cat(sprintf("- run_id: %s\n", run_id))
cat(sprintf("- run_root: %s\n", run_root))
cat(sprintf("- repro_mode: %s\n", cfg$run$repro_mode))
cat(sprintf("- seed: %s\n", cfg$run$seed))
cat(sprintf("- stages: %s\n", paste(enabled_stages, collapse = ", ")))
cat(sprintf("- resolved_config: %s\n", resolved_config_path))
cat(sprintf("- manifest: %s\n", manifest_path))

if (isTRUE(opts$dry_run) || isTRUE(cfg$run$dry_run)) {
  cat("Dry-run complete.\n")
  quit(save = "no", status = 0)
}

cat("Stage execution scaffold initialized. Full stage execution is implemented in subsequent stages.\n")
quit(save = "no", status = 0)
