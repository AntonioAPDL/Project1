#!/usr/bin/env Rscript

args <- commandArgs(trailingOnly = TRUE)

if (length(args) < 2L) {
  stop("Usage: Rscript scripts/audit_exal_multivar_keep_negative_forecast_support.R <run_root> <out_dir>", call. = FALSE)
}

run_root <- normalizePath(args[[1L]], mustWork = TRUE)
out_dir <- args[[2L]]
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
out_dir <- normalizePath(out_dir, mustWork = FALSE)

quant_csv <- file.path(
  run_root, "post", "outputs", basename(run_root),
  "exdqlm_multivar_synth_keep_cutoff_window_quantiles.csv"
)
draws_rds <- file.path(
  run_root, "post", "cache",
  "exdqlm_multivar_synth_keep__mode-keep__y_reps_f_new_smoke.rds"
)
synth_rds <- file.path(
  run_root, "post", "cache",
  "exdqlm_multivar_synth_keep__mode-keep__synth_multivar_forecast_log1p.rds"
)
guard_txt <- file.path(
  run_root, "post", "cache",
  "exdqlm_multivar_synth_keep__mode-keep__synth_multivar_forecast_exp_guard.txt"
)
cfg_yaml <- file.path(run_root, "resolved_config.yaml")

for (p in c(quant_csv, draws_rds, synth_rds, guard_txt, cfg_yaml)) {
  if (!file.exists(p)) {
    stop(sprintf("Missing required path: %s", p), call. = FALSE)
  }
}

if (!requireNamespace("yaml", quietly = TRUE)) stop("Package 'yaml' is required", call. = FALSE)
if (!requireNamespace("jsonlite", quietly = TRUE)) stop("Package 'jsonlite' is required", call. = FALSE)

`%||%` <- function(x, y) {
  if (is.null(x) || length(x) == 0L) y else x
}

cfg <- yaml::read_yaml(cfg_yaml, eval.expr = FALSE)
quant_df <- utils::read.csv(quant_csv, stringsAsFactors = FALSE, check.names = FALSE)
draws <- readRDS(draws_rds)
synth <- readRDS(synth_rds)
guard_lines <- readLines(guard_txt, warn = FALSE)

forecast_df <- quant_df[quant_df$segment == "forecast", , drop = FALSE]
forecast_dates <- as.Date(forecast_df$date)

q_probs <- c(0.05, 0.20, 0.35, 0.50, 0.65, 0.80, 0.95)
q_cols <- c("q05", "q20", "q35", "q50", "q65", "q80", "q95")
stopifnot(length(q_cols) == dim(draws)[1L], ncol(synth) == nrow(forecast_df), dim(draws)[3L] == nrow(forecast_df))

fast_quant <- function(x, prob) as.numeric(stats::quantile(x, probs = prob, type = 8, names = FALSE, na.rm = TRUE))

row_summary <- do.call(rbind, lapply(seq_along(q_probs), function(i) {
  vals <- as.numeric(draws[i, , ])
  data.frame(
    quantile_row = q_cols[[i]],
    target_prob = q_probs[[i]],
    min = min(vals, na.rm = TRUE),
    max = max(vals, na.rm = TRUE),
    mean = mean(vals, na.rm = TRUE),
    median = fast_quant(vals, 0.5),
    own_quantile = fast_quant(vals, q_probs[[i]]),
    frac_negative = mean(vals < 0, na.rm = TRUE),
    stringsAsFactors = FALSE
  )
}))

row_day <- do.call(rbind, lapply(seq_along(q_probs), function(i) {
  do.call(rbind, lapply(seq_len(dim(draws)[3L]), function(t_idx) {
    vals <- draws[i, , t_idx]
    data.frame(
      date = as.character(forecast_dates[[t_idx]]),
      quantile_row = q_cols[[i]],
      target_prob = q_probs[[i]],
      min = min(vals, na.rm = TRUE),
      max = max(vals, na.rm = TRUE),
      median = fast_quant(vals, 0.5),
      own_quantile = fast_quant(vals, q_probs[[i]]),
      frac_negative = mean(vals < 0, na.rm = TRUE),
      stringsAsFactors = FALSE
    )
  }))
}))

synth_day <- do.call(rbind, lapply(seq_len(ncol(synth)), function(t_idx) {
  vals <- synth[, t_idx]
  data.frame(
    date = as.character(forecast_dates[[t_idx]]),
    min = min(vals, na.rm = TRUE),
    max = max(vals, na.rm = TRUE),
    mean = mean(vals, na.rm = TRUE),
    median = fast_quant(vals, 0.5),
    q05 = fast_quant(vals, 0.05),
    q20 = fast_quant(vals, 0.20),
    q35 = fast_quant(vals, 0.35),
    q50 = fast_quant(vals, 0.50),
    q65 = fast_quant(vals, 0.65),
    q80 = fast_quant(vals, 0.80),
    q95 = fast_quant(vals, 0.95),
    frac_negative = mean(vals < 0, na.rm = TRUE),
    stringsAsFactors = FALSE
  )
}))

row_match <- do.call(rbind, lapply(seq_along(q_probs), function(i) {
  own_series <- vapply(seq_len(dim(draws)[3L]), function(t_idx) fast_quant(draws[i, , t_idx], q_probs[[i]]), numeric(1))
  final_series <- forecast_df[[q_cols[[i]]]]
  data.frame(
    quantile = q_cols[[i]],
    corr = suppressWarnings(stats::cor(final_series, own_series, use = "complete.obs")),
    mae = mean(abs(final_series - own_series), na.rm = TRUE),
    stringsAsFactors = FALSE
  )
}))

guard_kv <- stats::setNames(
  vapply(strsplit(guard_lines, "=", fixed = TRUE), function(x) if (length(x) >= 2L) paste(x[-1L], collapse = "=") else "", character(1)),
  vapply(strsplit(guard_lines, "=", fixed = TRUE), `[`, character(1), 1L)
)

summary_list <- list(
  run_root = run_root,
  analysis_scale_post_internal = cfg$scale_contract$analysis_scale_post_internal %||% NA_character_,
  guard_from_scale = unname(guard_kv[["from_scale"]]),
  guard_to_scale = unname(guard_kv[["to_scale"]]),
  guard_transform = unname(guard_kv[["transform"]]),
  forecast_days = nrow(forecast_df),
  final_synth_frac_negative = mean(as.numeric(synth) < 0, na.rm = TRUE),
  final_q05_negative_days = sum(synth_day$q05 < 0, na.rm = TRUE),
  final_q20_negative_days = sum(synth_day$q20 < 0, na.rm = TRUE),
  final_q35_negative_days = sum(synth_day$q35 < 0, na.rm = TRUE),
  row_q05_frac_negative = row_summary$frac_negative[row_summary$quantile_row == "q05"],
  row_q05_median = row_summary$median[row_summary$quantile_row == "q05"],
  row_q05_own_quantile = row_summary$own_quantile[row_summary$quantile_row == "q05"],
  row_q95_frac_negative = row_summary$frac_negative[row_summary$quantile_row == "q95"],
  row_q95_own_quantile = row_summary$own_quantile[row_summary$quantile_row == "q95"],
  final_vs_row_q05_corr = row_match$corr[row_match$quantile == "q05"],
  final_vs_row_q05_mae = row_match$mae[row_match$quantile == "q05"],
  final_vs_row_q95_corr = row_match$corr[row_match$quantile == "q95"],
  final_vs_row_q95_mae = row_match$mae[row_match$quantile == "q95"],
  issue_confirmed = isTRUE(
    identical(unname(guard_kv[["transform"]]), "identity") &&
      mean(as.numeric(synth) < 0, na.rm = TRUE) > 0.05 &&
      row_summary$own_quantile[row_summary$quantile_row == "q05"] < 0 &&
      row_match$corr[row_match$quantile == "q05"] > 0.95
  )
)

utils::write.csv(row_summary, file.path(out_dir, "row_predictive_support_summary.csv"), row.names = FALSE)
utils::write.csv(row_day, file.path(out_dir, "row_predictive_support_by_day.csv"), row.names = FALSE)
utils::write.csv(synth_day, file.path(out_dir, "synth_support_by_day.csv"), row.names = FALSE)
utils::write.csv(row_match, file.path(out_dir, "final_vs_row_target_quantiles.csv"), row.names = FALSE)
jsonlite::write_json(summary_list, file.path(out_dir, "summary.json"), auto_unbox = TRUE, pretty = TRUE)

md_path <- file.path(out_dir, "HE2_EXAL_M_T1_NEGATIVE_FORECAST_SUPPORT_AUDIT_20221225_20260518.md")
lines <- c(
  "# exAL-M-T1 Negative Forecast Support Audit",
  "",
  sprintf("- run_root: `%s`", run_root),
  sprintf("- analysis_scale_post_internal: `%s`", summary_list$analysis_scale_post_internal),
  sprintf("- transform guard: `%s` (`%s -> %s`)", summary_list$guard_transform, summary_list$guard_from_scale, summary_list$guard_to_scale),
  "",
  "## Main result",
  "",
  sprintf("- issue_confirmed: `%s`", summary_list$issue_confirmed),
  sprintf("- final synthesized forecast negative mass: `%.4f`", summary_list$final_synth_frac_negative),
  sprintf("- forecast days with final q05 < 0: `%d / %d`", summary_list$final_q05_negative_days, summary_list$forecast_days),
  sprintf("- forecast days with final q20 < 0: `%d / %d`", summary_list$final_q20_negative_days, summary_list$forecast_days),
  sprintf("- forecast days with final q35 < 0: `%d / %d`", summary_list$final_q35_negative_days, summary_list$forecast_days),
  "",
  "## Interpretation",
  "",
  "- The active canonical post path is no longer applying an extra exponentiation; the guard is identity on `log1p_cms`.",
  "- The negative support remains after that fix.",
  "- The negativity is already present in the row-specific predictive draws before the final synthesis step.",
  "- The final q05 and q95 curves track the corresponding tail-row predictive objects closely, so the synthesis step is mostly inheriting the tail pathology rather than creating it from scratch.",
  "",
  "## Key files",
  "",
  "- `row_predictive_support_summary.csv`",
  "- `row_predictive_support_by_day.csv`",
  "- `synth_support_by_day.csv`",
  "- `final_vs_row_target_quantiles.csv`",
  "- `summary.json`"
)
writeLines(lines, md_path)
cat(md_path, "\n")
