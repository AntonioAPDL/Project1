# unified/stages/stage_report.R

unified_stage_report <- function(cfg, run_root, repo_root, manifest) {
  report_root <- file.path(run_root, "report")
  dir.create(report_root, recursive = TRUE, showWarnings = FALSE)

  compare_report_path <- manifest$validation$compare_report_path
  compare_metrics <- list(matched = NA_integer_, missing = NA_integer_, extra = NA_integer_, mismatched = NA_integer_)
  if (!is.null(compare_report_path) && file.exists(compare_report_path) && requireNamespace("jsonlite", quietly = TRUE)) {
    cmp <- tryCatch(jsonlite::read_json(compare_report_path, simplifyVector = TRUE), error = function(e) NULL)
    if (!is.null(cmp) && !is.null(cmp$metrics)) {
      compare_metrics <- as.list(cmp$metrics)
    }
  }

  diff_files <- list.files(file.path(run_root, "validate", "write_audit"), pattern = "fs_diff.patch", recursive = TRUE, full.names = TRUE)
  write_audit_clean <- if (length(diff_files) == 0) TRUE else all(vapply(diff_files, function(p) !file.exists(p) || file.info(p)$size == 0, logical(1)))

  profile_summary_path <- NULL
  if (isTRUE(cfg$post$profile)) {
    profile_dir <- file.path(run_root, "post", "profile", cfg$run$run_id)
    run_log_path <- file.path(run_root, "post", "logs", cfg$run$run_id, "run_log.txt")
    profile_summary_path <- file.path(report_root, "profile_summary.md")
    summarize_script <- file.path(repo_root, "scripts", "summarize_profile_run.py")
    if (file.exists(summarize_script) && dir.exists(profile_dir)) {
      cmd_out <- system2(
        "python3",
        c(
          summarize_script,
          "--project-root", repo_root,
          "--run-id", cfg$run$run_id,
          "--profile-dir", profile_dir,
          "--run-log-path", run_log_path,
          "--out", profile_summary_path
        ),
        stdout = TRUE,
        stderr = TRUE
      )
      status <- attr(cmd_out, "status")
      if (!is.null(status) && status != 0) {
        profile_summary_path <- NULL
      }
    } else {
      profile_summary_path <- NULL
    }
  }

  input_hashes <- lapply(manifest$inputs, function(x) list(path = x$path, sha256 = x$sha256, storage_scale = x$storage_scale))

  summary_json <- list(
    run_id = cfg$run$run_id,
    run_root = run_root,
    git_commit = manifest$git$commit,
    repro_mode = cfg$run$repro_mode,
    seed = cfg$run$seed,
    stages_enabled = names(cfg$stages)[vapply(cfg$stages, isTRUE, logical(1))],
    input_hashes = input_hashes,
    drift_metrics = compare_metrics,
    validation_status = manifest$validation$status,
    change_approval_status = manifest$change_approval$status,
    write_audit_clean = write_audit_clean,
    compare_report_path = compare_report_path,
    profile_summary_path = profile_summary_path,
    artifacts_recorded = length(manifest$artifacts)
  )

  if (requireNamespace("jsonlite", quietly = TRUE)) {
    jsonlite::write_json(summary_json, path = file.path(report_root, "summary.json"), auto_unbox = TRUE, pretty = TRUE)
  }

  summary_lines <- c(
    sprintf("# Unified Run Summary (%s)", cfg$run$run_id),
    "",
    "## Run",
    sprintf("- run_root: `%s`", run_root),
    sprintf("- git_commit: `%s`", manifest$git$commit),
    sprintf("- repro_mode: `%s`", cfg$run$repro_mode),
    sprintf("- seed: `%s`", cfg$run$seed),
    sprintf("- stages_enabled: `%s`", paste(summary_json$stages_enabled, collapse = ", ")),
    "",
    "## Validation",
    sprintf("- validation_status: `%s`", manifest$validation$status),
    sprintf("- compare_report: `%s`", compare_report_path),
    sprintf("- drift metrics: matched=%s missing=%s extra=%s mismatched=%s",
            compare_metrics$matched, compare_metrics$missing, compare_metrics$extra, compare_metrics$mismatched),
    sprintf("- write_audit_clean: `%s`", write_audit_clean),
    sprintf("- change_approval.status: `%s`", manifest$change_approval$status),
    "",
    "## Inputs",
    sprintf("- input artifacts hashed: `%d`", length(input_hashes)),
    "",
    "## Outputs",
    sprintf("- artifacts_recorded: `%d`", length(manifest$artifacts)),
    sprintf("- summary_json: `%s`", file.path(report_root, "summary.json"))
  )

  if (!is.null(profile_summary_path)) {
    summary_lines <- c(summary_lines, sprintf("- profile_summary: `%s`", profile_summary_path))
  }

  writeLines(summary_lines, file.path(report_root, "summary.md"), useBytes = TRUE)

  list(manifest = manifest)
}
