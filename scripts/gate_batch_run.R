#!/usr/bin/env Rscript

args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 4L) {
  stop("usage: scripts/gate_batch_run.R <repo_root> <config_yaml> <launcher_log> <batch_log>", call. = FALSE)
}

repo_root <- normalizePath(args[[1]], mustWork = TRUE)
cfg_path <- normalizePath(args[[2]], mustWork = TRUE)
launcher_log <- args[[3]]
batch_log <- args[[4]]

suppressPackageStartupMessages(library(yaml))

require_file <- function(path, label) {
  if (!file.exists(path)) {
    stop(sprintf("missing %s: %s", label, path), call. = FALSE)
  }
  path
}

cfg <- read_yaml(cfg_path)
run_id <- cfg$run$run_id
cutoff <- gsub("-", "", cfg$dates$cutoff_date)
cfg_base <- tools::file_path_sans_ext(basename(cfg_path))
lane <- if (grepl("_l1_", cfg_base, fixed = TRUE)) {
  "l1"
} else if (grepl("_l2_", cfg_base, fixed = TRUE)) {
  "l2"
} else {
  stop(sprintf("could not infer lane from config path: %s", cfg_path), call. = FALSE)
}
expected_ndlm_mode <- cfg$models$ndlm_main$forecast_transfer_mode

run_root <- file.path(repo_root, "repro", "runs", run_id)
manifest_path <- require_file(file.path(run_root, "run_manifest.yaml"), "manifest")
crps_sum_path <- require_file(
  file.path(run_root, "post", "outputs", run_id, "tables", "crps_forecast_summary.csv"),
  "crps summary"
)
crps_health_path <- require_file(
  file.path(run_root, "post", "outputs", run_id, "tables", "crps_input_health.csv"),
  "crps input health"
)
crps_health_pt_path <- require_file(
  file.path(run_root, "post", "outputs", run_id, "tables", "crps_input_health_per_time.csv"),
  "crps input health per time"
)
theory_path <- require_file(
  file.path(run_root, "fit", "ndlm_main", "logs", "ndlm_theory_summary.log"),
  "ndlm main theory summary"
)

required_ids <- switch(
  lane,
  l1 = c(
    "dqlm_univar_al_synth",
    "dqlm_multivar_al_synth_drop",
    "dqlm_multivar_al_synth_keep",
    "ndlm_main_synth_keep",
    "ndlm_univar_synth_keep"
  ),
  l2 = c(
    "exdqlm_univar_synth",
    "exdqlm_multivar_synth_drop",
    "exdqlm_multivar_synth_keep",
    "ndlm_main_synth_drop"
  ),
  stop(sprintf("unknown lane: %s", lane), call. = FALSE)
)

manifest <- read_yaml(manifest_path)
stage_pass <- all(vapply(
  c("fit", "post", "report"),
  function(stage_name) identical(manifest$stages[[stage_name]]$status, "pass"),
  logical(1)
))

diag_dir <- file.path(run_root, "fit", "diagnostics")
diag_paths <- sort(list.files(
  diag_dir,
  pattern = "_diagnostics\\.yaml$",
  recursive = TRUE,
  full.names = TRUE
))
diag_statuses <- if (length(diag_paths)) {
  vapply(diag_paths, function(path) {
    x <- tryCatch(read_yaml(path), error = function(e) NULL)
    if (is.null(x) || is.null(x$status)) {
      return(NA_character_)
    }
    as.character(x$status)
  }, character(1))
} else {
  character(0)
}
diag_pass <- length(diag_paths) > 0L && all(diag_statuses == "pass")

crps_sum <- read.csv(crps_sum_path, stringsAsFactors = FALSE)
present_ids <- sort(unique(crps_sum$model_id))
missing_ids <- setdiff(required_ids, present_ids)
id_pass <- length(missing_ids) == 0L

crps_health <- read.csv(crps_health_path, stringsAsFactors = FALSE)
crps_health_pt <- read.csv(crps_health_pt_path, stringsAsFactors = FALSE)
health_fail_rows <- sum(tolower(trimws(crps_health$status)) == "fail")
health_fail_rows_pt <- sum(tolower(trimws(crps_health_pt$status)) == "fail")
health_pass <- health_fail_rows == 0L && health_fail_rows_pt == 0L

theory_lines <- readLines(theory_path, warn = FALSE)
mode_line <- sprintf("forecast_transfer_mode=%s", expected_ndlm_mode)
active_line <- if (identical(expected_ndlm_mode, "keep")) {
  "transfer_active_forecast_window=true"
} else {
  "transfer_active_forecast_window=false"
}
ndlm_mode_pass <- any(trimws(theory_lines) == mode_line) &&
  any(trimws(theory_lines) == active_line)

rdata_count <- length(list.files(run_root, pattern = "\\.RData$", recursive = TRUE, full.names = TRUE))
cleanup_pass <- identical(rdata_count, 0L)

overall_pass <- stage_pass && diag_pass && id_pass && health_pass && ndlm_mode_pass && cleanup_pass

lines <- c(
  sprintf("=== run_id %s ===", run_id),
  sprintf("cutoff=%s", cutoff),
  sprintf("lane=%s", lane),
  sprintf("config=%s", cfg_path),
  sprintf("launcher_log=%s", launcher_log),
  sprintf("G1_stage_pass=%s", if (stage_pass) "pass" else "fail"),
  sprintf("G2_diag_pass=%s (n=%d)", if (diag_pass) "pass" else "fail", length(diag_paths)),
  sprintf(
    "G3_required_model_ids=%s (missing=%s)",
    if (id_pass) "pass" else "fail",
    if (length(missing_ids)) paste(missing_ids, collapse = ",") else "<none>"
  ),
  sprintf(
    "G4_input_health=%s (fail_rows=%d, fail_rows_per_time=%d)",
    if (health_pass) "pass" else "fail",
    health_fail_rows,
    health_fail_rows_pt
  ),
  sprintf("G5_ndlm_mode=%s (expected=%s)", if (ndlm_mode_pass) "pass" else "fail", expected_ndlm_mode),
  sprintf("G6_cleanup=%s (rdata_count=%d)", if (cleanup_pass) "pass" else "fail", rdata_count),
  sprintf("OVERALL=%s", if (overall_pass) "pass" else "fail"),
  sprintf("evidence_manifest=%s", manifest_path),
  sprintf("evidence_diag_dir=%s", diag_dir),
  sprintf("evidence_theory=%s", theory_path),
  sprintf("evidence_crps_summary=%s", crps_sum_path),
  sprintf("evidence_crps_health=%s", crps_health_path),
  sprintf("evidence_crps_health_per_time=%s", crps_health_pt_path)
)

write(lines, file = batch_log, append = TRUE)
if (!overall_pass) {
  quit(status = 1L)
}
