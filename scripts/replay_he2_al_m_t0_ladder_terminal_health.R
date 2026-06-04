#!/usr/bin/env Rscript

args <- commandArgs(trailingOnly = TRUE)

`%||%` <- function(x, y) if (is.null(x)) y else x

arg_value <- function(flag, default = "") {
  idx <- which(args == flag)
  if (!length(idx) || idx[[1L]] >= length(args)) return(default)
  args[[idx[[1L]] + 1L]]
}

arg_flag <- function(flag) {
  any(args == flag)
}

script_file <- tryCatch(sys.frame(1)$ofile, error = function(e) NULL) %||%
  file.path("scripts", "replay_he2_al_m_t0_ladder_terminal_health.R")
repo_root <- normalizePath(file.path(dirname(script_file), ".."), mustWork = FALSE)
if (!dir.exists(file.path(repo_root, "R"))) {
  repo_root <- normalizePath(getwd(), mustWork = TRUE)
}
setwd(repo_root)

source(file.path("R", "unified", "stages", "stage_fit.R"))

status_csv <- arg_value(
  "--status-csv",
  file.path("reports", "he2_al_m_t0_transfer_ladder_live_20260604", "diagnostic_ladder_live_status.csv")
)
out_dir <- arg_value(
  "--out-dir",
  file.path("reports", "he2_al_m_t0_transfer_ladder_live_20260604", "terminal_health_replay")
)
include_active <- arg_flag("--include-active")
overwrite <- arg_flag("--overwrite")

if (!file.exists(status_csv)) {
  stop(sprintf("status CSV not found: %s", status_csv), call. = FALSE)
}

status <- utils::read.csv(status_csv, stringsAsFactors = FALSE)
required_cols <- c(
  "root",
  "experiment_id",
  "cutoff",
  "lane",
  "pid",
  "rdata_exists",
  "rdata_path",
  "terminal_health_exists"
)
missing_cols <- setdiff(required_cols, names(status))
if (length(missing_cols) > 0L) {
  stop(sprintf("status CSV missing columns: %s", paste(missing_cols, collapse = ", ")), call. = FALSE)
}

status$rdata_exists <- tolower(as.character(status$rdata_exists))
status$terminal_health_exists <- tolower(as.character(status$terminal_health_exists))
status$pid <- as.character(status$pid)
status$pid[is.na(status$pid)] <- ""

candidates <- status[
  status$rdata_exists == "true" &
    nzchar(status$rdata_path) &
    file.exists(status$rdata_path),
  ,
  drop = FALSE
]
if (!include_active) {
  candidates <- candidates[!nzchar(candidates$pid), , drop = FALSE]
}
if (!overwrite) {
  candidates <- candidates[candidates$terminal_health_exists != "true", , drop = FALSE]
}

dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

rows <- list()
for (i in seq_len(nrow(candidates))) {
  row <- candidates[i, , drop = FALSE]
  q_label <- sub("^q", "", as.character(row$lane[[1L]]))
  quantile <- suppressWarnings(as.numeric(q_label) / 100)
  if (!is.finite(quantile)) {
    warning(sprintf("skipping row with invalid quantile label: %s", row$lane[[1L]]), call. = FALSE)
    next
  }
  rdata_path <- as.character(row$rdata_path[[1L]])
  output_dir <- dirname(rdata_path)
  tmp_files <- list.files(output_dir, pattern = "\\.tmp\\.", full.names = TRUE)
  if (!include_active && length(tmp_files) > 0L) {
    message(sprintf(
      "skip active save root=%s experiment=%s cutoff=%s lane=%s tmp_files=%d",
      row$root[[1L]],
      row$experiment_id[[1L]],
      row$cutoff[[1L]],
      row$lane[[1L]],
      length(tmp_files)
    ))
    next
  }
  terminal_txt <- file.path(output_dir, "multivar_terminal_state_health.txt")
  terminal_csv <- file.path(output_dir, "multivar_terminal_state_health.csv")
  forecast_txt <- file.path(output_dir, "multivar_forecast_health.txt")

  message(sprintf(
    "replay root=%s experiment=%s cutoff=%s lane=%s",
    row$root[[1L]],
    row$experiment_id[[1L]],
    row$cutoff[[1L]],
    row$lane[[1L]]
  ))

  res <- unified_multivar_fit_health_check(
    rdata_path = rdata_path,
    quantile = quantile,
    transfer_mode = "drop",
    report_path = forecast_txt,
    terminal_report_path = terminal_txt,
    terminal_csv_path = terminal_csv,
    history_latent_limit = 25,
    state_norm_sq_per_T_limit = 1e4,
    transfer_level_limit = 25,
    transfer_coef_limit = 100
  )

  rows[[length(rows) + 1L]] <- data.frame(
    root = row$root[[1L]],
    experiment_id = row$experiment_id[[1L]],
    cutoff = row$cutoff[[1L]],
    lane = row$lane[[1L]],
    violation_n = length(res$violations),
    violations = paste(res$violations, collapse = " | "),
    max_abs_history_exps = res$max_abs_history_exps,
    state_norm_sq_per_T = res$state_norm_sq_per_T,
    transfer_level_max_abs = res$transfer_level_max_abs,
    max_E_sigma = res$max_E_sigma,
    terminal_csv = terminal_csv,
    rdata_path = rdata_path,
    stringsAsFactors = FALSE
  )
  rm(res)
  invisible(gc(verbose = FALSE))
}

summary <- if (length(rows)) {
  do.call(rbind, rows)
} else {
  data.frame(
    root = character(0),
    experiment_id = character(0),
    cutoff = character(0),
    lane = character(0),
    violation_n = integer(0),
    violations = character(0),
    max_abs_history_exps = numeric(0),
    state_norm_sq_per_T = numeric(0),
    transfer_level_max_abs = numeric(0),
    max_E_sigma = numeric(0),
    terminal_csv = character(0),
    rdata_path = character(0),
    stringsAsFactors = FALSE
  )
}

utils::write.csv(summary, file.path(out_dir, "terminal_health_replay_summary.csv"), row.names = FALSE)
writeLines(
  c(
    "# HE2 AL-M-T0 Ladder Terminal Health Replay",
    "",
    "This report replays terminal saved-state health for diagnostic ladder outputs that have saved RData artifacts but missing terminal-health CSVs.",
    "",
    sprintf("- status_csv: `%s`", normalizePath(status_csv, mustWork = FALSE)),
    sprintf("- output_dir: `%s`", normalizePath(out_dir, mustWork = FALSE)),
    sprintf("- include_active: `%s`", include_active),
    sprintf("- overwrite: `%s`", overwrite),
    sprintf("- replayed_rows: `%d`", nrow(summary)),
    "",
    "```",
    capture.output(print(summary[, c(
      "root",
      "experiment_id",
      "cutoff",
      "lane",
      "violation_n",
      "max_abs_history_exps",
      "state_norm_sq_per_T",
      "transfer_level_max_abs",
      "max_E_sigma"
    )], row.names = FALSE)),
    "```"
  ),
  con = file.path(out_dir, "README.md")
)

print(summary[, c(
  "root",
  "experiment_id",
  "cutoff",
  "lane",
  "violation_n",
  "max_abs_history_exps",
  "state_norm_sq_per_T",
  "transfer_level_max_abs",
  "max_E_sigma"
)], row.names = FALSE)
