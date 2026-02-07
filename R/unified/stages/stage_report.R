# unified/stages/stage_report.R

unified_stage_report <- function(cfg, run_root, repo_root, manifest) {
  report_root <- file.path(run_root, "report")
  dir.create(report_root, recursive = TRUE, showWarnings = FALSE)

  summary_lines <- c(
    sprintf("# Unified Run Summary (%s)", cfg$run$run_id),
    "",
    sprintf("- run_root: `%s`", run_root),
    sprintf("- repro_mode: `%s`", cfg$run$repro_mode),
    sprintf("- seed: `%s`", cfg$run$seed),
    sprintf("- git_commit: `%s`", manifest$git$commit),
    sprintf("- stages_enabled: `%s`", paste(names(cfg$stages)[vapply(cfg$stages, isTRUE, logical(1))], collapse = ", ")),
    sprintf("- artifacts_recorded: `%d`", length(manifest$artifacts))
  )
  writeLines(summary_lines, file.path(report_root, "summary.md"), useBytes = TRUE)

  if (requireNamespace("jsonlite", quietly = TRUE)) {
    jsonlite::write_json(list(
      run_id = cfg$run$run_id,
      run_root = run_root,
      repro_mode = cfg$run$repro_mode,
      seed = cfg$run$seed,
      git_commit = manifest$git$commit,
      stages_enabled = names(cfg$stages)[vapply(cfg$stages, isTRUE, logical(1))],
      artifacts_recorded = length(manifest$artifacts),
      validation_status = manifest$validation$status
    ), path = file.path(report_root, "summary.json"), auto_unbox = TRUE, pretty = TRUE)
  }

  list(manifest = manifest)
}
