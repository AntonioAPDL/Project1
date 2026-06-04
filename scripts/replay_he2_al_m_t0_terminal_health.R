#!/usr/bin/env Rscript

args <- commandArgs(trailingOnly = TRUE)

`%||%` <- function(x, y) if (is.null(x)) y else x

arg_value <- function(flag, default = "") {
  idx <- which(args == flag)
  if (!length(idx) || idx[[1L]] >= length(args)) return(default)
  args[[idx[[1L]] + 1L]]
}

script_file <- sys.frame(1)$ofile %||% file.path("scripts", "replay_he2_al_m_t0_terminal_health.R")
repo_root <- normalizePath(file.path(dirname(script_file), ".."), mustWork = FALSE)
if (!dir.exists(file.path(repo_root, "R"))) {
  repo_root <- normalizePath(getwd(), mustWork = TRUE)
}
setwd(repo_root)

source(file.path("R", "unified", "stages", "stage_fit.R"))

default_runtime_root <- file.path(
  "/data/muscat_data/jaguir26/project1_ucsc_phd_runtime",
  "multimodel_v8_he2_dqlm_multivar_al_drop_diagnostics_highdf_eps365_cf1_representative_20260603"
)
runtime_root <- arg_value("--runtime-root", default_runtime_root)
out_dir <- arg_value(
  "--out-dir",
  file.path("reports", "he2_al_m_t0_terminal_health_replay_20260604")
)

lane_paths <- data.frame(
  label = c("20211112_q35", "20211221_q80", "20220511_q65", "20221225_q80"),
  q = c(0.35, 0.80, 0.65, 0.80),
  rel = c(
    "runs/diagnostic_20211112_dqlm_multivar_al_drop_q35_highdf_eps365_cf1_al_m_t0_20260603/fit/q=35/outputs/DISC_variables_35_exAL_synth_DISC.RData",
    "runs/diagnostic_20211221_dqlm_multivar_al_drop_q80_highdf_eps365_cf1_al_m_t0_20260603/fit/q=80/outputs/DISC_variables_80_exAL_synth_DISC.RData",
    "runs/diagnostic_20220511_dqlm_multivar_al_drop_q65_highdf_eps365_cf1_al_m_t0_20260603/fit/q=65/outputs/DISC_variables_65_exAL_synth_DISC.RData",
    "runs/diagnostic_20221225_dqlm_multivar_al_drop_q80_highdf_eps365_cf1_al_m_t0_20260603/fit/q=80/outputs/DISC_variables_80_exAL_synth_DISC.RData"
  ),
  stringsAsFactors = FALSE
)
lane_paths$rdata <- file.path(runtime_root, lane_paths$rel)

missing <- lane_paths$rdata[!file.exists(lane_paths$rdata)]
if (length(missing) > 0L) {
  stop(
    sprintf("missing retained diagnostic RData files:\n%s", paste(missing, collapse = "\n")),
    call. = FALSE
  )
}

dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
rows <- list()
for (i in seq_len(nrow(lane_paths))) {
  label <- lane_paths$label[[i]]
  message("replay ", label)
  txt <- file.path(out_dir, paste0(label, "_forecast_health.txt"))
  terminal_txt <- file.path(out_dir, paste0(label, "_terminal_state_health.txt"))
  terminal_csv <- file.path(out_dir, paste0(label, "_terminal_state_health.csv"))
  res <- unified_multivar_fit_health_check(
    rdata_path = lane_paths$rdata[[i]],
    quantile = lane_paths$q[[i]],
    transfer_mode = "drop",
    report_path = txt,
    terminal_report_path = terminal_txt,
    terminal_csv_path = terminal_csv,
    history_latent_limit = 25,
    state_norm_sq_per_T_limit = 1e4,
    transfer_level_limit = 25,
    transfer_coef_limit = 100
  )
  rows[[length(rows) + 1L]] <- data.frame(
    label = label,
    violation_n = length(res$violations),
    violations = paste(res$violations, collapse = " | "),
    max_abs_history_exps = res$max_abs_history_exps,
    state_norm_sq_per_T = res$state_norm_sq_per_T,
    transfer_level_max_abs = res$transfer_level_max_abs,
    max_E_sigma = res$max_E_sigma,
    terminal_csv = terminal_csv,
    stringsAsFactors = FALSE
  )
  rm(res)
  invisible(gc(verbose = FALSE))
}

summary <- do.call(rbind, rows)
utils::write.csv(summary, file.path(out_dir, "terminal_health_replay_summary.csv"), row.names = FALSE)
writeLines(
  c(
    "# HE2 AL-M-T0 Terminal Health Replay",
    "",
    "This report replays the terminal saved-state health gate against retained representative diagnostics.",
    "",
    sprintf("- runtime root: `%s`", normalizePath(runtime_root, mustWork = FALSE)),
    sprintf("- output dir: `%s`", normalizePath(out_dir, mustWork = FALSE)),
    "",
    "```",
    capture.output(print(summary[, c(
      "label",
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
  "label",
  "violation_n",
  "max_abs_history_exps",
  "state_norm_sq_per_T",
  "transfer_level_max_abs",
  "max_E_sigma"
)], row.names = FALSE)
