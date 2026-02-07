# unified/stages/stage_validate.R

unified_stage_validate <- function(cfg, run_root, repo_root, manifest) {
  validate_root <- file.path(run_root, "validate")
  dir.create(validate_root, recursive = TRUE, showWarnings = FALSE)

  report <- list(
    status = "pending",
    run_id = cfg$run$run_id,
    canonical_run_id = cfg$validation$canonical_run_id,
    notes = c("Stage 7 will expand compare automation; this stage currently writes a manifest-aligned placeholder.")
  )

  if (!requireNamespace("jsonlite", quietly = TRUE)) {
    writeLines(c("{", "  \"status\": \"pending\"", "}"), file.path(validate_root, "compare_report.json"), useBytes = TRUE)
  } else {
    jsonlite::write_json(report, path = file.path(validate_root, "compare_report.json"), auto_unbox = TRUE, pretty = TRUE)
  }

  manifest$validation$status <- "pending"
  manifest$validation$compare_report_path <- file.path(validate_root, "compare_report.json")
  list(manifest = manifest)
}
