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
source(file.path(repo_root, "R", "unified", "utils_scale.R"))
source(file.path(repo_root, "R", "unified", "utils_env_capture.R"))
source(file.path(repo_root, "R", "unified", "utils_artifact_locator.R"))
source(file.path(repo_root, "R", "unified", "inputs_shared_validate.R"))
source(file.path(repo_root, "R", "unified", "contract_checks.R"))
source(file.path(repo_root, "R", "unified", "config.R"))
source(file.path(repo_root, "R", "unified", "determinism.R"))
source(file.path(repo_root, "R", "unified", "manifest.R"))
source(file.path(repo_root, "R", "unified", "utils_write_audit.R"))
source(file.path(repo_root, "R", "unified", "stages", "stage_forecats.R"))
source(file.path(repo_root, "R", "unified", "stages", "stage_data_prep_shared.R"))
source(file.path(repo_root, "R", "unified", "stages", "stage_fit.R"))
source(file.path(repo_root, "R", "unified", "stages", "stage_post.R"))
source(file.path(repo_root, "R", "unified", "stages", "stage_validate.R"))
source(file.path(repo_root, "R", "unified", "stages", "stage_report.R"))

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
env_artifacts <- unified_capture_env_artifacts(run_root)
for (nm in names(env_artifacts)) {
  manifest <- unified_manifest_add_artifact(manifest, env_artifacts[[nm]], storage_scale = "text")
}
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

stage_order <- c("forecats", "data_prep_shared", "fit", "post", "validate", "report")
stage_index <- c(
  forecats = 1L,
  data_prep_shared = 1L,
  fit = 2L,
  post = 3L,
  validate = 4L,
  report = 5L
)

run_stage <- function(stage, manifest) {
  switch(stage,
    forecats = unified_stage_forecats(cfg, run_root, repo_root, manifest),
    data_prep_shared = unified_stage_data_prep_shared(cfg, run_root, repo_root, manifest),
    fit = unified_stage_fit(cfg, run_root, repo_root, manifest),
    post = unified_stage_post(cfg, run_root, repo_root, manifest),
    validate = unified_stage_validate(cfg, run_root, repo_root, manifest),
    report = unified_stage_report(cfg, run_root, repo_root, manifest),
    stop(sprintf("Unknown stage: %s", stage), call. = FALSE)
  )
}

audit_enabled <- isTRUE(cfg$write_audit$enabled)
audit_threshold <- as.integer(cfg$write_audit$enforce_from_stage)
allowlist <- unlist(cfg$write_audit$allowlist_outside_run_root, use.names = FALSE)

for (stage in stage_order) {
  if (!isTRUE(cfg$stages[[stage]])) next

  cat(sprintf("== Running stage: %s ==\n", stage))
  enforce_audit <- audit_enabled && (stage_index[[stage]] >= audit_threshold)
  stage_audit_dir <- file.path(run_root, "validate", "write_audit", stage)
  before_path <- file.path(stage_audit_dir, "fs_before.tsv")
  after_path <- file.path(stage_audit_dir, "fs_after.tsv")
  diff_path <- file.path(stage_audit_dir, "fs_diff.patch")

  if (enforce_audit) {
    unified_write_audit_snapshot(repo_root, run_root, before_path)
  }

  result <- run_stage(stage, manifest)
  manifest <- result$manifest
  unified_manifest_write(manifest, manifest_path)

  if (enforce_audit) {
    unified_write_audit_snapshot(repo_root, run_root, after_path)
    unified_write_audit_diff(before_path, after_path, diff_path)
    unified_write_audit_enforce(diff_path, allowlist = allowlist)
  }
}

manifest$timestamps$finished_at_utc <- format(Sys.time(), "%Y-%m-%dT%H:%M:%SZ", tz = "UTC")
unified_manifest_write(manifest, manifest_path)

cat("Unified run complete.\n")
quit(save = "no", status = 0)
