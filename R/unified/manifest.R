# unified/manifest.R

unified_git_info <- function(repo_root) {
  read_cmd <- function(...) {
    out <- tryCatch(system2("git", c("-C", repo_root, ...), stdout = TRUE, stderr = FALSE), error = function(e) character(0))
    if (length(out) == 0) return("unknown")
    out[[1]]
  }

  dirty_lines <- tryCatch(system2("git", c("-C", repo_root, "status", "--porcelain"), stdout = TRUE, stderr = FALSE), error = function(e) character(0))

  list(
    commit = read_cmd("rev-parse", "HEAD"),
    branch = read_cmd("rev-parse", "--abbrev-ref", "HEAD"),
    dirty = length(dirty_lines) > 0
  )
}

unified_collect_input_records <- function(cfg) {
  records <- list()

  add_record <- function(path, storage_scale) {
    if (is.null(path) || !nzchar(path)) return()
    records[[length(records) + 1]] <<- list(
      path = path,
      sha256 = unified_sha256(path),
      storage_scale = storage_scale
    )
  }

  if (isTRUE(cfg$stages$fit)) {
    add_record(cfg$inputs$fit$parameters_path, "parameters_text")
    add_record(cfg$inputs$fit$retros_path, cfg$inputs$fit$retros_storage_scale)
    add_record(cfg$inputs$fit$nws_forecast_path, cfg$inputs$fit$nws_storage_scale)
    add_record(cfg$inputs$fit$glofas_forecast_path, cfg$inputs$fit$glofas_storage_scale)
  }

  if (isTRUE(cfg$stages$forecats)) {
    mode <- cfg$inputs$forecats$mode
    if (identical(mode, "build")) {
      add_record(cfg$inputs$forecats$pipeline_config_path, "yaml_config")
    }
    if (identical(mode, "use_existing")) {
      add_record(cfg$inputs$forecats$existing_bundle_path, "bundle")
    }
  }

  records
}

unified_manifest_init <- function(cfg, run_id, run_root, repo_root, repro_record) {
  git <- unified_git_info(repo_root)
  inputs <- unified_collect_input_records(cfg)

  list(
    manifest_version = 1L,
    config_version = cfg$config_version,
    run_id = run_id,
    run_root = run_root,
    timestamps = list(
      started_at_utc = format(Sys.time(), "%Y-%m-%dT%H:%M:%SZ", tz = "UTC"),
      finished_at_utc = NULL
    ),
    git = git,
    repro = list(
      mode = cfg$run$repro_mode,
      seed = as.integer(cfg$run$seed),
      thread_env = list(
        OMP_NUM_THREADS = Sys.getenv("OMP_NUM_THREADS", ""),
        OPENBLAS_NUM_THREADS = Sys.getenv("OPENBLAS_NUM_THREADS", ""),
        MKL_NUM_THREADS = Sys.getenv("MKL_NUM_THREADS", ""),
        VECLIB_MAXIMUM_THREADS = Sys.getenv("VECLIB_MAXIMUM_THREADS", ""),
        NUMEXPR_NUM_THREADS = Sys.getenv("NUMEXPR_NUM_THREADS", "")
      ),
      r_rng = list(
        fit = paste(repro_record$fit_rng, collapse = "/"),
        post = paste(repro_record$post_rng, collapse = "/")
      )
    ),
    inputs = inputs,
    artifacts = list(),
    scale_history = list(),
    change_approval = list(
      required = TRUE,
      status = "pending",
      approver = NULL,
      approved_at_utc = NULL,
      rationale = NULL,
      expected_diffs = list(
        allowed_path_patterns = list(),
        disallowed_path_patterns = list()
      ),
      metric_thresholds = list(
        numeric_abs_max = 0,
        numeric_rel_max = 0,
        pixel_max_abs = 0
      ),
      evidence_paths = list(
        compare_report = NULL,
        diff_summary = NULL
      )
    ),
    validation = list(
      compare_report_path = file.path(run_root, "validate", "compare_report.json"),
      write_audit_diff_path = file.path(run_root, "validate", "write_audit", "fs_diff.patch"),
      status = "pending"
    ),
    schema_migration = list(
      previous_manifest_version = NULL,
      migration_notes = NULL
    )
  )
}

unified_manifest_add_artifact <- function(manifest, path, storage_scale, analysis_scale = NULL, flow_domain = NULL) {
  artifact <- list(
    path = path,
    sha256 = if (file.exists(path)) unified_sha256(path) else NA_character_,
    storage_scale = storage_scale
  )
  if (!is.null(analysis_scale)) artifact$analysis_scale <- analysis_scale
  if (!is.null(flow_domain)) artifact$flow_domain <- flow_domain

  manifest$artifacts[[length(manifest$artifacts) + 1]] <- artifact
  manifest
}

unified_manifest_add_scale_history <- function(manifest, artifact, from_scale, to_scale, transform) {
  manifest$scale_history[[length(manifest$scale_history) + 1]] <- list(
    artifact = artifact,
    from_scale = from_scale,
    to_scale = to_scale,
    transform = transform
  )
  manifest
}

unified_manifest_write <- function(manifest, out_path) {
  if (!requireNamespace("yaml", quietly = TRUE)) {
    stop("Package 'yaml' is required to write unified manifest")
  }
  dir.create(dirname(out_path), recursive = TRUE, showWarnings = FALSE)
  yaml_text <- yaml::as.yaml(manifest, indent.mapping.sequence = TRUE)
  writeLines(yaml_text, con = out_path, useBytes = TRUE)
  invisible(out_path)
}
