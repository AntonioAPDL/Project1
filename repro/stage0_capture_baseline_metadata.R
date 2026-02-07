#!/usr/bin/env Rscript

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 1) {
  stop("Usage: Rscript --vanilla repro/stage0_capture_baseline_metadata.R <baseline_run_dir>")
}

run_dir <- normalizePath(args[[1]], mustWork = FALSE)
if (!dir.exists(run_dir)) {
  stop(sprintf("Run directory does not exist: %s", run_dir))
}

repo_root <- normalizePath(file.path(dirname(run_dir), "..", ".."), mustWork = TRUE)
run_id <- basename(run_dir)
env_dir <- file.path(run_dir, "env")
meta_dir <- file.path(run_dir, "meta")
if (!dir.exists(meta_dir)) dir.create(meta_dir, recursive = TRUE, showWarnings = FALSE)
dir.create(env_dir, recursive = TRUE, showWarnings = FALSE)

write_lines <- function(path, lines) {
  con <- file(path, open = "wt")
  on.exit(close(con), add = TRUE)
  writeLines(lines, con = con, useBytes = TRUE)
}

# env snapshots per spec
session_info_path <- file.path(env_dir, "R_sessionInfo.txt")
write_lines(session_info_path, capture.output({
  cat("Timestamp:", format(Sys.time(), "%Y-%m-%dT%H:%M:%SZ", tz = "UTC"), "\n")
  cat("R.version.string:", R.version.string, "\n\n")
  print(sessionInfo())
}))

installed_packages_path <- file.path(env_dir, "R_installed_packages.csv")
ip <- as.data.frame(installed.packages(), stringsAsFactors = FALSE)
keep_cols <- c("Package", "Version", "LibPath", "Priority", "Built")
keep_cols <- keep_cols[keep_cols %in% colnames(ip)]
utils::write.csv(ip[, keep_cols, drop = FALSE], installed_packages_path, row.names = FALSE)

pip_freeze_path <- file.path(env_dir, "python_pip_freeze.txt")
python_bin <- Sys.which("python3")
if (python_bin == "") python_bin <- Sys.which("python")
if (python_bin != "") {
  out <- tryCatch(
    system2(python_bin, c("-m", "pip", "freeze"), stdout = TRUE, stderr = TRUE),
    error = function(e) c(sprintf("ERROR: %s", conditionMessage(e)))
  )
  write_lines(pip_freeze_path, out)
} else {
  write_lines(pip_freeze_path, "python3/python not found in PATH")
}

thread_keys <- c(
  "OMP_NUM_THREADS",
  "OPENBLAS_NUM_THREADS",
  "MKL_NUM_THREADS",
  "VECLIB_MAXIMUM_THREADS",
  "NUMEXPR_NUM_THREADS"
)
thread_vals <- Sys.getenv(thread_keys, unset = "")
threads_snapshot_path <- file.path(env_dir, "threads_snapshot.txt")
write_lines(
  threads_snapshot_path,
  c(
    sprintf("captured_at_utc=%s", format(Sys.time(), "%Y-%m-%dT%H:%M:%SZ", tz = "UTC")),
    sprintf("%s=%s", thread_keys, unname(thread_vals))
  )
)

renviron_snapshot_path <- file.path(env_dir, "renviron_snapshot.txt")
renv_keys <- unique(c(thread_keys, "PKG_CXXFLAGS", "PKG_LIBS", "LD_LIBRARY_PATH"))
renv_vals <- Sys.getenv(renv_keys, unset = "")
renviron_lines <- c(
  sprintf("captured_at_utc=%s", format(Sys.time(), "%Y-%m-%dT%H:%M:%SZ", tz = "UTC")),
  sprintf("%s=%s", renv_keys, unname(renv_vals))
)
repo_renviron <- file.path(repo_root, ".Renviron")
if (file.exists(repo_renviron)) {
  renviron_lines <- c(
    renviron_lines,
    "",
    "# .Renviron content (repo root)",
    readLines(repo_renviron, warn = FALSE)
  )
}
write_lines(renviron_snapshot_path, renviron_lines)

# artifact hashes for baseline inputs/outputs/meta
sha_output <- file.path(meta_dir, "artifacts.sha256")
subdirs <- c("inputs", "run1", "run2", "meta")
files <- unlist(lapply(subdirs, function(sd) {
  d <- file.path(run_dir, sd)
  if (!dir.exists(d)) return(character(0))
  list.files(d, recursive = TRUE, full.names = TRUE, all.files = FALSE)
}), use.names = FALSE)
files <- files[file.info(files)$isdir %in% FALSE]
files <- sort(unique(files))

sha_lines <- character(0)
if (length(files) > 0) {
  cmd <- sprintf("sha256sum %s", paste(shQuote(files), collapse = " "))
  sha_lines <- tryCatch(
    system(cmd, intern = TRUE),
    error = function(e) c(sprintf("ERROR: failed to hash files: %s", conditionMessage(e)))
  )
}
if (length(sha_lines) == 0) sha_lines <- "NO_FILES_FOUND"
write_lines(sha_output, sha_lines)

# minimal manifest skeleton (pending approvals allowed)
manifest_path <- file.path(run_dir, "run_manifest.yaml")
manifest_lines <- c(
  "manifest_version: 1",
  "config_version: 1",
  sprintf("run_id: \"%s\"", run_id),
  sprintf("run_root: \"%s\"", run_dir),
  "repro:",
  "  mode: \"strict\"",
  "  seed: null",
  "  thread_env:",
  sprintf("    %s: \"%s\"", thread_keys, unname(thread_vals)),
  "git:",
  sprintf("  commit: \"%s\"", tryCatch(system("git rev-parse HEAD", intern = TRUE), error = function(e) "unknown")),
  sprintf("  branch: \"%s\"", tryCatch(system("git rev-parse --abbrev-ref HEAD", intern = TRUE), error = function(e) "unknown")),
  "  dirty: true",
  "inputs:",
  "  - path: \"inputs/inputs.sha256\"",
  "    sha256: null",
  "    storage_scale: \"mixed\"",
  "artifacts:",
  "  - path: \"meta/artifacts.sha256\"",
  "    sha256: null",
  "    storage_scale: \"hash_manifest\"",
  "change_approval:",
  "  required: true",
  "  status: \"pending\"",
  "  approver: null",
  "  approved_at_utc: null",
  "  rationale: null",
  "  expected_diffs:",
  "    allowed_path_patterns: []",
  "    disallowed_path_patterns: []",
  "  metric_thresholds:",
  "    numeric_abs_max: 0.0",
  "    numeric_rel_max: 0.0",
  "    pixel_max_abs: 0.0",
  "  evidence_paths:",
  "    compare_report: null",
  "    diff_summary: null",
  "validation:",
  "  compare_report_path: null",
  "  write_audit_diff_path: null",
  "  status: \"pending\"",
  "schema_migration:",
  "  previous_manifest_version: null",
  "  migration_notes: \"stage0 baseline metadata capture\""
)
write_lines(manifest_path, manifest_lines)

cat(sprintf("Wrote Stage 0 metadata artifacts in: %s\n", run_dir))
cat(sprintf("- %s\n", session_info_path))
cat(sprintf("- %s\n", installed_packages_path))
cat(sprintf("- %s\n", pip_freeze_path))
cat(sprintf("- %s\n", renviron_snapshot_path))
cat(sprintf("- %s\n", threads_snapshot_path))
cat(sprintf("- %s\n", sha_output))
cat(sprintf("- %s\n", manifest_path))
