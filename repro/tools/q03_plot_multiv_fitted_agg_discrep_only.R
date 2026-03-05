#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(ggplot2)
})

args <- commandArgs(trailingOnly = TRUE)

get_arg <- function(flag, default = NULL) {
  hit <- grep(paste0("^", flag, "="), args, value = TRUE)
  if (length(hit) == 0L) {
    return(default)
  }
  sub(paste0("^", flag, "="), "", hit[[1L]])
}

source_run_id <- get_arg("--source-run-id", "prod_canonical_full_e2e_parallel_onecore_refresh_20260221")
out_dir <- get_arg("--out-dir", file.path("repro", "docs", sprintf("q03_post_direct_%s", format(Sys.time(), "%Y%m%dT%H%M%SZ"))))

dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

quantiles <- c(1L, 5L, 10L, 50L, 90L, 95L, 99L)
quantile_labels <- sprintf("q%02d", quantiles)
F_constant_disc <- c(1, 1, 0, 1, 0, 1, 0)

retros_csv <- file.path("repro", "runs", source_run_id, "post", "inputs", "retros_post_adapter.csv")
dates_all <- NULL
retros_df <- NULL
if (file.exists(retros_csv)) {
  retros_df <- read.csv(retros_csv, stringsAsFactors = FALSE)
  if ("Date" %in% names(retros_df)) {
    dates_all <- as.Date(retros_df$Date)
  }
}

rows <- list()
n_t_ref <- NA_integer_

for (i in seq_along(quantiles)) {
  q <- quantiles[[i]]
  q_label <- quantile_labels[[i]]
  cat(sprintf("[q03-direct] loading %s\n", q_label))
  flush.console()
  rdata_path <- file.path(
    "repro", "runs", source_run_id, "fit",
    sprintf("q=%02d", q),
    "outputs",
    sprintf("DISC_variables_%d_exAL_synth_DISC.RData", q)
  )
  if (!file.exists(rdata_path)) {
    stop(sprintf("[Q03_DIRECT_MISSING_RDATA] Missing fit artifact for %s at %s", q_label, rdata_path), call. = FALSE)
  }

  e <- new.env(parent = emptyenv())
  load(rdata_path, envir = e)
  obj_name <- sprintf("new.theta.out_%d_exAL_synth_DISC", q)
  if (!exists(obj_name, envir = e, inherits = FALSE)) {
    stop(sprintf("[Q03_DIRECT_MISSING_OBJECT] %s not found in %s", obj_name, rdata_path), call. = FALSE)
  }
  obj <- get(obj_name, envir = e, inherits = FALSE)
  sm <- obj$sm

  if (!is.numeric(sm) || is.null(dim(sm)) || length(dim(sm)) != 2L) {
    stop(sprintf("[Q03_DIRECT_SM_SHAPE] %s$sm must be a numeric matrix.", obj_name), call. = FALSE)
  }
  if (nrow(sm) < 21L) {
    stop(sprintf("[Q03_DIRECT_SM_ROWS] %s$sm has %d rows; need at least 21 for discrepancy blocks.", obj_name, as.integer(nrow(sm))), call. = FALSE)
  }

  d1 <- as.numeric(crossprod(F_constant_disc, sm[8:14, , drop = FALSE]))
  d2 <- as.numeric(crossprod(F_constant_disc, sm[15:21, , drop = FALSE]))
  n_t <- length(d1)
  if (!identical(length(d2), n_t)) {
    stop(sprintf("[Q03_DIRECT_DISCREP_LEN] discrepancy length mismatch for %s.", q_label), call. = FALSE)
  }
  if (is.na(n_t_ref)) {
    n_t_ref <- as.integer(n_t)
  } else if (!identical(as.integer(n_t), n_t_ref)) {
    stop(sprintf("[Q03_DIRECT_TIME_MISMATCH] %s length=%d differs from reference length=%d.", q_label, as.integer(n_t), n_t_ref), call. = FALSE)
  }

  if (!is.null(dates_all) && length(dates_all) >= n_t) {
    use_dates <- tail(dates_all, n_t)
  } else {
    use_dates <- as.Date("1970-01-01") + seq_len(n_t) - 1L
  }

  rows[[length(rows) + 1L]] <- data.frame(
    date = use_dates,
    time_index = seq_len(n_t),
    quantile = q_label,
    discrepancy_type = "GloFAS-USGS",
    fitted_discrepancy = d1,
    stringsAsFactors = FALSE
  )
  rows[[length(rows) + 1L]] <- data.frame(
    date = use_dates,
    time_index = seq_len(n_t),
    quantile = q_label,
    discrepancy_type = "NWS-USGS",
    fitted_discrepancy = d2,
    stringsAsFactors = FALSE
  )
  cat(sprintf("[q03-direct] computed fitted discrepancies for %s (n_time=%d)\n", q_label, n_t))
  flush.console()
}

df <- do.call(rbind, rows)
df$quantile <- factor(df$quantile, levels = quantile_labels)
df$discrepancy_type <- factor(df$discrepancy_type, levels = c("GloFAS-USGS", "NWS-USGS"))

csv_path <- file.path(out_dir, "multiv_agg_discrep_fitted_only_timeseries.csv")
write.csv(df, csv_path, row.names = FALSE)

pick_col <- function(candidates, cols, label) {
  for (pat in candidates) {
    hit <- grep(pat, cols, ignore.case = TRUE, value = TRUE)
    if (length(hit) > 0L) return(hit[[1L]])
  }
  stop(sprintf("[Q03_DIRECT_MISSING_COL] Could not find %s column in retros_post_adapter.csv", label), call. = FALSE)
}

obs_df <- NULL
obs_csv_path <- file.path(out_dir, "multiv_agg_discrep_observed_timeseries.csv")
if (!is.null(retros_df)) {
  if (nrow(retros_df) < n_t_ref) {
    stop(
      sprintf(
        "[Q03_DIRECT_RETRO_SHORT] retros_post_adapter has %d rows but fitted discrepancy uses %d time steps.",
        as.integer(nrow(retros_df)),
        as.integer(n_t_ref)
      ),
      call. = FALSE
    )
  }

  usgs_col <- pick_col(c("^USGS$", "^USGS"), names(retros_df), "USGS")
  glofas_col <- pick_col(c("^GloFAS$", "GloFAS"), names(retros_df), "GloFAS")
  nws_col <- pick_col(c("^NWS3\\.0$", "^NWS", "NWS"), names(retros_df), "NWS")

  retro_use <- tail(retros_df, n_t_ref)
  dates_obs <- as.Date(retro_use$Date)
  obs_df <- rbind(
    data.frame(
      date = dates_obs,
      time_index = seq_len(n_t_ref),
      discrepancy_type = "GloFAS-USGS",
      observed_discrepancy = as.numeric(retro_use[[glofas_col]]) - as.numeric(retro_use[[usgs_col]]),
      stringsAsFactors = FALSE
    ),
    data.frame(
      date = dates_obs,
      time_index = seq_len(n_t_ref),
      discrepancy_type = "NWS-USGS",
      observed_discrepancy = as.numeric(retro_use[[nws_col]]) - as.numeric(retro_use[[usgs_col]]),
      stringsAsFactors = FALSE
    )
  )
  obs_df$discrepancy_type <- factor(obs_df$discrepancy_type, levels = c("GloFAS-USGS", "NWS-USGS"))
  write.csv(obs_df, obs_csv_path, row.names = FALSE)
}

meta_path <- file.path(out_dir, "multiv_agg_discrep_fitted_only_meta.txt")
meta_lines <- c(
  sprintf("source_run_id=%s", source_run_id),
  sprintf("n_quantiles=%d", length(quantiles)),
  sprintf("quantiles=%s", paste(quantile_labels, collapse = ",")),
  sprintf("n_time=%d", n_t_ref),
  sprintf("date_start=%s", as.character(min(df$date))),
  sprintf("date_end=%s", as.character(max(df$date))),
  sprintf("observed_overlay_present=%s", ifelse(is.null(obs_df), "no", "yes")),
  sprintf("n_finite=%d", sum(is.finite(df$fitted_discrepancy))),
  sprintf("n_total=%d", nrow(df))
)
writeLines(meta_lines, con = meta_path)

plot_path <- file.path(out_dir, "multiv_agg_discrep_fitted_only.png")
q_colors <- c(
  q01 = "#8c510a",
  q05 = "#d8b365",
  q10 = "#f6e8c3",
  q50 = "#1b7837",
  q90 = "#7fbf7b",
  q95 = "#5e3c99",
  q99 = "#2d004b"
)

p <- ggplot() +
  {
    if (!is.null(obs_df)) geom_line(
      data = obs_df,
      aes(x = date, y = observed_discrepancy),
      inherit.aes = FALSE,
      color = "#4d4d4d",
      linewidth = 0.20,
      alpha = 0.75
    )
  } +
  {
    if (!is.null(obs_df)) geom_point(
      data = obs_df,
      aes(x = date, y = observed_discrepancy),
      inherit.aes = FALSE,
      color = "#1f1f1f",
      size = 0.15,
      alpha = 0.60
    )
  } +
  geom_line(data = df, aes(x = date, y = fitted_discrepancy, color = quantile), linewidth = 0.35, alpha = 0.92) +
  facet_wrap(~ discrepancy_type, ncol = 1, scales = "free_y") +
  scale_color_manual(values = q_colors) +
  labs(
    title = "Multiv exDQLM Aggregated Discrepancy",
    subtitle = sprintf("Source run: %s", source_run_id),
    x = NULL,
    y = "Discrepancy (observed in gray/black, fitted quantiles in color)",
    color = "Fitted quantile"
  ) +
  theme_minimal(base_size = 11) +
  theme(
    legend.position = "bottom",
    legend.key.width = unit(1.6, "lines"),
    axis.text.x = element_text(angle = 30, hjust = 1),
    strip.text = element_text(face = "bold"),
    panel.grid.minor = element_blank()
  )
ggsave(plot_path, p, width = 13, height = 8, units = "in", dpi = 220)

cat(sprintf("WROTE %s\n", normalizePath(plot_path)))
cat(sprintf("WROTE %s\n", normalizePath(csv_path)))
if (!is.null(obs_df)) {
  cat(sprintf("WROTE %s\n", normalizePath(obs_csv_path)))
}
cat(sprintf("WROTE %s\n", normalizePath(meta_path)))
