# unified/stages/stage_validate.R

unified_write_sha_for_dir <- function(dir_path, out_path) {
  dir.create(dirname(out_path), recursive = TRUE, showWarnings = FALSE)
  if (!dir.exists(dir_path)) {
    writeLines(character(0), out_path, useBytes = TRUE)
    return(invisible(out_path))
  }
  files <- sort(list.files(dir_path, full.names = TRUE))
  files <- files[file.info(files)$isdir %in% FALSE]
  lines <- vapply(files, function(p) sprintf("%s  %s", unified_sha256(p), basename(p)), character(1))
  writeLines(lines, out_path, useBytes = TRUE)
  invisible(out_path)
}

unified_parse_compare_report_txt <- function(path) {
  if (!file.exists(path)) {
    return(list(matched = NA_integer_, missing = NA_integer_, extra = NA_integer_, mismatched = NA_integer_))
  }
  lines <- readLines(path, warn = FALSE)
  parse_count <- function(key) {
    line <- grep(paste0("^", key, ":"), lines, value = TRUE)
    if (length(line) == 0) return(NA_integer_)
    suppressWarnings(as.integer(sub("^.*:\\s*", "", line[[1]])))
  }
  list(
    matched = parse_count("Matched"),
    missing = parse_count("Missing"),
    extra = parse_count("Extra"),
    mismatched = parse_count("Mismatched")
  )
}

unified_stage_validate <- function(cfg, run_root, repo_root, manifest) {
  validate_root <- file.path(run_root, "validate")
  dir.create(validate_root, recursive = TRUE, showWarnings = FALSE)

  run_id <- cfg$run$run_id
  current_dir <- file.path(run_root, "post", "outputs", run_id)

  canonical_run_id <- cfg$validation$canonical_run_id
  if (!is.null(canonical_run_id) && nzchar(canonical_run_id) &&
      identical(toupper(canonical_run_id), "__SELF__")) {
    canonical_run_id <- run_id
  }
  if (!is.null(canonical_run_id) && nzchar(canonical_run_id)) {
    canonical_dir <- file.path(cfg$run$run_root, canonical_run_id, "post", "outputs", canonical_run_id)
  } else {
    canonical_dir <- file.path(repo_root, "Environmetrics_reproduce")
  }

  canonical_sha <- file.path(validate_root, "canonical.sha256")
  current_sha <- file.path(validate_root, "current.sha256")
  report_txt <- file.path(validate_root, "compare_report.txt")
  report_json <- file.path(validate_root, "compare_report.json")
  diff_dir <- file.path(validate_root, "diff")

  unified_write_sha_for_dir(canonical_dir, canonical_sha)
  unified_write_sha_for_dir(current_dir, current_sha)

  compare_script <- file.path(repo_root, "repro", "compare_to_canonical.py")
  cmd_status <- 0L
  cmd_out <- character(0)
  if (file.exists(compare_script)) {
    args <- c(
      compare_script,
      "--manifest", file.path(run_root, "run_manifest.yaml"),
      "--canonical-dir", canonical_dir,
      "--current-dir", current_dir,
      "--canonical-sha", canonical_sha,
      "--current-sha", current_sha,
      "--report", report_txt,
      "--diff-dir", diff_dir,
      "--mode", cfg$validation$compare$mode
    )
    cmd_out <- system2("python3", args, stdout = TRUE, stderr = TRUE)
    status_attr <- attr(cmd_out, "status")
    if (!is.null(status_attr)) cmd_status <- as.integer(status_attr)
  } else {
    cmd_status <- 1L
    cmd_out <- sprintf("compare tool missing: %s", compare_script)
  }

  metrics <- unified_parse_compare_report_txt(report_txt)
  status <- if (!is.na(metrics$mismatched) && !is.na(metrics$missing) && !is.na(metrics$extra) &&
                metrics$mismatched == 0 && metrics$missing == 0 && metrics$extra == 0 && cmd_status == 0) {
    "pass"
  } else {
    "fail"
  }

  report <- list(
    status = status,
    run_id = run_id,
    canonical_run_id = canonical_run_id,
    canonical_dir = canonical_dir,
    current_dir = current_dir,
    mode = cfg$validation$compare$mode,
    metrics = metrics,
    command_status = cmd_status,
    command_output_tail = utils::tail(cmd_out, 20)
  )

  env_drift_path <- file.path(validate_root, "env_drift_report.json")
  if (!is.null(canonical_run_id) && nzchar(canonical_run_id)) {
    current_env_dir <- file.path(run_root, "env")
    canonical_env_dir <- file.path(cfg$run$run_root, canonical_run_id, "env")
    env_report <- unified_env_drift_report(current_env_dir, canonical_env_dir, out_json_path = env_drift_path)
    report$env_drift <- env_report
    if (identical(env_report$status, "fail")) {
      status <- "fail"
      report$status <- "fail"
    }
  }

  if (requireNamespace("jsonlite", quietly = TRUE)) {
    jsonlite::write_json(report, path = report_json, auto_unbox = TRUE, pretty = TRUE)
  } else {
    writeLines(c("{", sprintf("  \"status\": \"%s\"", status), "}"), report_json, useBytes = TRUE)
  }

  manifest$validation$status <- status
  manifest$validation$compare_report_path <- report_json
  list(manifest = manifest)
}
