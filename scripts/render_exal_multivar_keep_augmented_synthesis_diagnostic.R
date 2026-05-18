#!/usr/bin/env Rscript

args <- commandArgs(trailingOnly = TRUE)

get_arg <- function(flag, default = NULL) {
  hit <- which(args == flag)
  if (length(hit) == 0L) return(default)
  idx <- hit[[1L]] + 1L
  if (idx > length(args)) {
    stop(sprintf("Missing value for %s", flag), call. = FALSE)
  }
  args[[idx]]
}

`%||%` <- function(x, y) if (is.null(x) || identical(x, "")) y else x

project_root <- normalizePath(get_arg("--project-root", getwd()), mustWork = FALSE)
run_root <- normalizePath(
  get_arg(
    "--run-root",
    "/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_20221225_reference_relaunch_20260518/runs/multimodel_20221225_v8_he2pubgdpc1r1_exdqlm_multivar_keep"
  ),
  mustWork = FALSE
)
report_dir <- normalizePath(
  get_arg(
    "--report-dir",
    file.path(project_root, "reports", "he2_exal_m_t1_augmented_synthesis_diagnostic_20221225_20260518")
  ),
  mustWork = FALSE
)
dir.create(report_dir, recursive = TRUE, showWarnings = FALSE)
sample_cap <- suppressWarnings(as.integer(get_arg("--sample-cap", "512")))
if (!is.finite(sample_cap) || sample_cap <= 1L) {
  sample_cap <- 512L
}
skip_history_model <- tolower(as.character(get_arg("--skip-history-model", "true"))) %in% c("true", "1", "yes")

resolved_config_path <- file.path(run_root, "resolved_config.yaml")
if (!file.exists(resolved_config_path)) {
  stop(sprintf("Resolved config missing: %s", resolved_config_path), call. = FALSE)
}
if (!requireNamespace("yaml", quietly = TRUE)) {
  stop("yaml package is required.", call. = FALSE)
}
cfg <- yaml::read_yaml(resolved_config_path)

analysis_scale <- as.character(cfg$scale_contract$analysis_scale_post_internal %||% "log1p_cms")
cutoff_date <- as.Date(cfg$dates$cutoff_date %||% "2022-12-25")
plot_start <- as.Date(cfg$dates$plot_start %||% as.character(cutoff_date - 18L))
plot_end <- as.Date(cfg$dates$plot_end %||% as.character(cutoff_date + 28L))
forecast_start <- cutoff_date + 1L
run_id <- basename(run_root)
cache_dir <- file.path(run_root, "post", "cache")
outputs_dir <- file.path(run_root, "post", "outputs", run_id)

Sys.setenv(
  ENV_PROJECT_ROOT = project_root,
  UNIFIED_RUN_ROOT = run_root,
  UNIFIED_RUN_ID = run_id,
  UNIFIED_POST_CACHE_DIR = cache_dir,
  UNIFIED_ANALYSIS_SCALE_POST_INTERNAL = analysis_scale
)
options(unified.analysis_scale_post_internal = analysis_scale)

source(file.path(project_root, "R", "unified", "utils_scale.R"))
source(file.path(project_root, "R", "environmetrics", "02_helpers_core.R"))
source(file.path(project_root, "R", "unified", "post_publication_figures.R"))

if (!requireNamespace("ggplot2", quietly = TRUE)) {
  stop("ggplot2 is required.", call. = FALSE)
}

write_csv_det <- function(df, path) {
  dir.create(dirname(path), recursive = TRUE, showWarnings = FALSE)
  utils::write.csv(df, path, row.names = FALSE)
  invisible(path)
}

matrix_quantiles_type8 <- function(mat, probs) {
  out <- apply(mat, 2L, stats::quantile, probs = probs, na.rm = TRUE, type = 8, names = FALSE)
  matrix(out, nrow = length(probs), byrow = FALSE)
}

synthesize_samples <- function(y_reps, q_s, k = 1L) {
  n.q     <- dim(y_reps)[1]
  n.samp  <- dim(y_reps)[2]
  n.times <- dim(y_reps)[3]
  stopifnot(length(q_s) == n.q, !is.unsorted(q_s))
  total_samp <- as.integer(k) * n.samp
  out <- matrix(NA_real_, nrow = total_samp, ncol = n.times)
  for (t_idx in seq_len(n.times)) {
    for (i in seq_len(total_samp)) {
      u <- stats::runif(1L)
      idx <- findInterval(u, q_s)
      if ((idx != 0L) && (idx != n.q)) {
        q_lo <- q_s[idx]
        q_hi <- q_s[idx + 1L]
        w <- (u - q_lo) / (q_hi - q_lo)
        y_lower <- stats::quantile(y_reps[idx, , t_idx], probs = u, type = 7L, names = FALSE, na.rm = TRUE)
        y_upper <- stats::quantile(y_reps[idx + 1L, , t_idx], probs = u, type = 7L, names = FALSE, na.rm = TRUE)
        out[i, t_idx] <- (1 - w) * y_lower + w * y_upper
      } else if (idx == 0L) {
        out[i, t_idx] <- stats::quantile(y_reps[idx + 1L, , t_idx], probs = u, type = 7L, names = FALSE, na.rm = TRUE)
      } else {
        out[i, t_idx] <- stats::quantile(y_reps[idx, , t_idx], probs = u, type = 7L, names = FALSE, na.rm = TRUE)
      }
    }
  }
  out
}

smoke_inverse_cdf_al <- function(U, mu, sigma, p) {
  ifelse(
    U < p,
    mu + (sigma / (1 - p)) * log(U / p),
    mu - (sigma / p) * log((1 - U) / (1 - p))
  )
}

next_idx_block <- function(prev_idx, block_len) {
  block_len <- suppressWarnings(as.integer(block_len[[1L]]))
  start <- if (length(prev_idx) == 0L) 0L else as.integer(prev_idx[[length(prev_idx)]])
  if (!is.finite(block_len) || block_len <= 0L) return(integer(0))
  seq_len(block_len) + start
}

forecast_core_dim <- function(seg_id, p, J) {
  as.integer(p * (J - as.integer(seg_id) + 2L))
}

build_usgs_projection_weights <- function(ff_seg, state_len, seg_id, p, J, use_covariates, transfer_mode, ppx) {
  ff_n <- nrow(ff_seg)
  weights <- rep(0, state_len)
  base_len <- min(p, ff_n, state_len)
  if (base_len > 0L) {
    base_vals <- as.numeric(ff_seg[seq_len(base_len), 1, drop = TRUE])
    base_vals[!is.finite(base_vals)] <- 0
    weights[seq_len(base_len)] <- base_vals
  }
  use_transfer_forecast_projection <- isTRUE(use_covariates) &&
    identical(transfer_mode, "keep") &&
    is.finite(ppx) &&
    ppx > 0L
  if (isTRUE(use_transfer_forecast_projection)) {
    core_dim <- forecast_core_dim(seg_id, p = p, J = J)
    zeta_idx <- core_dim + 1L
    if (zeta_idx <= ff_n && zeta_idx <= state_len) {
      zeta_w <- as.numeric(ff_seg[zeta_idx, 1, drop = TRUE])
      if (!is.finite(zeta_w)) zeta_w <- 0
      weights[zeta_idx] <- zeta_w
    }
  }
  weights
}

project_state_gaussian <- function(Mu, Sigma, ff_seg, seg_id, p, J, use_covariates, transfer_mode, ppx) {
  w <- build_usgs_projection_weights(
    ff_seg = ff_seg,
    state_len = length(Mu),
    seg_id = seg_id,
    p = p,
    J = J,
    use_covariates = use_covariates,
    transfer_mode = transfer_mode,
    ppx = ppx
  )
  idx_use <- which(abs(w) > 0)
  if (length(idx_use) == 0L) {
    return(c(mean = NA_real_, sd = NA_real_))
  }
  Mu_use <- as.numeric(Mu[idx_use])
  Mu_use[!is.finite(Mu_use)] <- 0
  S_use <- as.matrix(Sigma[idx_use, idx_use, drop = FALSE])
  S_use[!is.finite(S_use)] <- 0
  w_use <- as.numeric(w[idx_use])
  mean_use <- sum(w_use * Mu_use)
  var_use <- as.numeric(crossprod(w_use, S_use %*% w_use))
  if (!is.finite(var_use) || var_use < 0) var_use <- 0
  c(mean = mean_use, sd = sqrt(var_use))
}

sample_subset_df <- function(model_id, sample_mat, dates, segment, cap = 128L) {
  if (!is.matrix(sample_mat) || nrow(sample_mat) <= 0L || ncol(sample_mat) <= 0L) {
    return(data.frame(
      model_id = character(0),
      draw_id = character(0),
      sample_index = integer(0),
      date = character(0),
      segment = character(0),
      value = numeric(0),
      stringsAsFactors = FALSE
    ))
  }
  idx <- unique(round(seq(1, nrow(sample_mat), length.out = min(as.integer(cap), nrow(sample_mat)))))
  sub_mat <- sample_mat[idx, , drop = FALSE]
  data.frame(
    model_id = as.character(model_id),
    draw_id = rep(sprintf("draw_%03d", seq_along(idx)), each = ncol(sub_mat)),
    sample_index = rep(idx, each = ncol(sub_mat)),
    date = rep(as.character(as.Date(dates)), times = nrow(sub_mat)),
    segment = as.character(segment),
    value = as.numeric(t(sub_mat)),
    stringsAsFactors = FALSE
  )
}

quantile_df <- function(model_id, dates, observed, quantile_mat, probs, segment, interval_low, interval_high, model_mean) {
  out <- data.frame(
    model_id = as.character(model_id),
    date = as.character(as.Date(dates)),
    segment = as.character(segment),
    observed = as.numeric(observed),
    interval_low = as.numeric(interval_low),
    interval_high = as.numeric(interval_high),
    model_mean = as.numeric(model_mean),
    stringsAsFactors = FALSE
  )
  for (i in seq_along(probs)) {
    out[[sprintf("q%02d", as.integer(round(100 * probs[[i]])))]] <- as.numeric(quantile_mat[i, ])
  }
  out
}

read_quantile_contract <- function(path) {
  df <- utils::read.csv(path, stringsAsFactors = FALSE, check.names = FALSE)
  df$date <- as.Date(df$date)
  df
}

contract_path <- file.path(outputs_dir, "exdqlm_multivar_synth_keep_cutoff_window_quantiles.csv")
if (!file.exists(contract_path)) {
  stop(sprintf("Current cutoff-window quantile contract missing: %s", contract_path), call. = FALSE)
}
current_contract <- read_quantile_contract(contract_path)
hist_contract <- current_contract[current_contract$segment == "history", , drop = FALSE]
fc_contract <- current_contract[current_contract$segment == "forecast", , drop = FALSE]

hist_dates <- hist_contract$date
fc_dates <- fc_contract$date
hist_obs <- hist_contract$observed
fc_obs <- fc_contract$observed

q_probs <- c(0.05, 0.20, 0.35, 0.50, 0.65, 0.80, 0.95)
q_tags <- c("5", "20", "35", "50", "65", "80", "95")
model_id <- "exdqlm_multivar_synth_keep"

fit_dir <- file.path(run_root, "fit", "exdqlm_multivar", "keep")
if (isTRUE(skip_history_model)) {
  hist_samples <- matrix(numeric(0), nrow = 0L, ncol = length(hist_dates))
  hist_q <- matrix(NA_real_, nrow = length(q_probs), ncol = length(hist_dates))
  hist_interval <- matrix(NA_real_, nrow = 2L, ncol = length(hist_dates))
  hist_mean <- rep(NA_real_, length(hist_dates))
} else {
  load_env <- new.env(parent = .GlobalEnv)
  for (q in q_tags) {
    fp <- file.path(fit_dir, sprintf("q=%02d", as.integer(q)), "outputs", sprintf("DISC_variables_%s_exAL_synth_DISC.RData", as.integer(q)))
    if (!file.exists(fp)) {
      stop(sprintf("Missing retained fit object for q=%s: %s", q, fp), call. = FALSE)
    }
    load(fp, envir = load_env)
  }

  timestamps_all <- get0("timestamps", envir = load_env, inherits = TRUE, ifnotfound = NULL)
  if (is.null(timestamps_all)) {
    timestamps_all <- get0("timestamps_keep", envir = load_env, inherits = TRUE, ifnotfound = NULL)
  }
  timestamps_all <- as.Date(timestamps_all)
  hist_idx <- match(hist_dates, timestamps_all)
  if (any(is.na(hist_idx))) {
    stop("Unable to align historical dates to retained timestamps.", call. = FALSE)
  }

  FF_use <- get("FF", envir = load_env, inherits = TRUE)
  n_samp_hist <- min(vapply(q_tags, function(q) {
    theta_obj <- get(sprintf("samp.theta_%s_exAL_synth_DISC", q), envir = load_env, inherits = TRUE)
    dim(theta_obj$samp_theta)[3]
  }, integer(1)))
  n_samp_hist <- min(n_samp_hist, sample_cap)

  y_hist_cube <- array(NA_real_, c(length(q_tags), n_samp_hist, length(hist_idx)))
  for (i in seq_along(q_tags)) {
    q_tag <- q_tags[[i]]
    p0 <- q_probs[[i]]
    theta_obj <- get(sprintf("samp.theta_%s_exAL_synth_DISC", q_tag), envir = load_env, inherits = TRUE)
    th <- theta_obj$samp_theta[, , seq_len(n_samp_hist), drop = FALSE]
    sts_arr <- get(sprintf("samp.sts_%s_exAL_synth_DISC", q_tag), envir = load_env, inherits = TRUE)[1L, hist_idx, seq_len(n_samp_hist), drop = FALSE]
    stj <- matrix(sts_arr, nrow = length(hist_idx), ncol = n_samp_hist)
    gamj <- as.numeric(get(sprintf("samp.gamma_%s_exAL_synth_DISC", q_tag), envir = load_env, inherits = TRUE)[1L, seq_len(n_samp_hist)])
    sigj <- as.numeric(get(sprintf("samp.sigma_%s_exAL_synth_DISC", q_tag), envir = load_env, inherits = TRUE)[1L, seq_len(n_samp_hist)])
    p_exAL <- p_fn(p0, gamj)

    xb <- matrix(NA_real_, nrow = length(hist_idx), ncol = n_samp_hist)
    for (k in seq_along(hist_idx)) {
      t_idx <- hist_idx[[k]]
      th_t <- matrix(th[, t_idx, ], nrow = dim(th)[1], ncol = n_samp_hist)
      p_use <- min(nrow(FF_use), nrow(th_t))
      xb[k, ] <- as.vector(t(FF_use[seq_len(p_use), 1L, t_idx, drop = FALSE][, 1L, 1L]) %*% th_t[seq_len(p_use), , drop = FALSE])
    }

    set.seed(770L + i)
    u_values <- matrix(stats::runif(length(hist_idx) * n_samp_hist), nrow = length(hist_idx), ncol = n_samp_hist)
    mu <- xb + sweep(stj, 2L, sigj * abs(gamj) * C_fn(p0, gamj), `*`)
    y_hist <- t(smoke_inverse_cdf_al(u_values, mu, sigj, p_exAL))
    for (k in seq_len(ncol(y_hist))) {
      y_hist[, k] <- sort_keep_na(y_hist[, k])
    }
    y_hist_cube[i, , ] <- post_transform_internal_to_log1p_mat(
      y_hist,
      from_scale = analysis_scale,
      context = sprintf("%s.corrected.multivar.hist.q%s", model_id, q_tag)
    )
  }

  set.seed(20260518L)
  hist_samples <- synthesize_samples(y_hist_cube, q_probs)
  hist_q <- matrix_quantiles_type8(hist_samples, probs = q_probs)
  hist_interval <- matrix_quantiles_type8(hist_samples, probs = c(0.025, 0.975))
  hist_mean <- colMeans(hist_samples, na.rm = TRUE)
}

fc_draws_path <- file.path(cache_dir, sprintf("%s__mode-keep__y_reps_f_new_smoke.rds", model_id))
if (!file.exists(fc_draws_path)) {
  stop(sprintf("Forecast draw cache missing: %s", fc_draws_path), call. = FALSE)
}
fc_raw_cube <- readRDS(fc_draws_path)
if (dim(fc_raw_cube)[2] > sample_cap) {
  fc_raw_cube <- fc_raw_cube[, seq_len(sample_cap), , drop = FALSE]
}
fc_log1p_cube <- post_transform_internal_array_to_log1p(
  fc_raw_cube,
  from_scale = analysis_scale,
  context = sprintf("%s.corrected.multivar.forecast", model_id),
  report_path = file.path(report_dir, "forecast_scale_transform_report.txt")
)$values
set.seed(20260518L)
fc_samples <- synthesize_samples(fc_log1p_cube, q_probs)
fc_q <- matrix_quantiles_type8(fc_samples, probs = q_probs)
fc_interval <- matrix_quantiles_type8(fc_samples, probs = c(0.025, 0.975))
fc_mean <- colMeans(fc_samples, na.rm = TRUE)

combined_quant <- rbind(
  quantile_df(model_id, hist_dates, hist_obs, hist_q, q_probs, "history", hist_interval[1, ], hist_interval[2, ], hist_mean),
  quantile_df(model_id, fc_dates, fc_obs, fc_q, q_probs, "forecast", fc_interval[1, ], fc_interval[2, ], fc_mean)
)
combined_samples <- rbind(
  sample_subset_df(model_id, hist_samples, hist_dates, "history", cap = 96L),
  sample_subset_df(model_id, fc_samples, fc_dates, "forecast", cap = 96L)
)

corrected_quant_path <- file.path(report_dir, "corrected_cutoff_window_quantiles_log1p.csv")
corrected_sample_subset_path <- file.path(report_dir, "corrected_cutoff_window_sample_subset_log1p.csv")
current_vs_corrected_path <- file.path(report_dir, "current_vs_corrected_forecast_quantiles.csv")
hist_samples_rds <- file.path(report_dir, "corrected_history_samples_log1p.rds")
fc_samples_rds <- file.path(report_dir, "corrected_forecast_samples_log1p.rds")
saveRDS(hist_samples, hist_samples_rds)
saveRDS(fc_samples, fc_samples_rds)
write_csv_det(combined_quant, corrected_quant_path)
write_csv_det(combined_samples, corrected_sample_subset_path)

current_fc <- fc_contract[, c("date", "observed", "q05", "q20", "q35", "q50", "q65", "q80", "q95"), drop = FALSE]
current_fc$date <- as.Date(current_fc$date)
corrected_fc <- combined_quant[combined_quant$segment == "forecast", c("date", "observed", "interval_low", "interval_high", "model_mean", "q05", "q20", "q35", "q50", "q65", "q80", "q95"), drop = FALSE]
comparison_df <- merge(
  current_fc,
  corrected_fc,
  by = c("date", "observed"),
  suffixes = c("_current", "_corrected"),
  sort = TRUE
)
write_csv_det(comparison_df, current_vs_corrected_path)

style <- post_publication_default_style()
style$posterior$sample_path_cap <- 10L

quant_plot <- combined_quant
quant_plot$date <- as.Date(quant_plot$date)
sample_plot <- combined_samples
sample_plot$date <- as.Date(sample_plot$date)

forecast_quant_cols <- grep("^q\\d{2}$", names(quant_plot), value = TRUE)
forecast_long <- do.call(rbind, lapply(forecast_quant_cols, function(col) {
  data.frame(
    date = quant_plot$date[quant_plot$segment == "forecast"],
    value = quant_plot[quant_plot$segment == "forecast", col],
    quantile = col,
    stringsAsFactors = FALSE
  )
}))
forecast_long$quantile_label <- factor(
  forecast_long$quantile,
  levels = forecast_quant_cols,
  labels = c("q05", "q20", "q35", "q50", "q65", "q80", "q95")
)

sample_plot <- post_publication_sample_subset(sample_plot, cap = 10L)

quant_colors <- c(
  q05 = "#B2182B",
  q20 = "#D6604D",
  q35 = "#F4A582",
  q50 = "#1B7837",
  q65 = "#92C5DE",
  q80 = "#4393C3",
  q95 = "#2166AC"
)

title_text <- "Multivariate exDQLM via exAL Forecast Synthesis"
subtitle_text <- sprintf(
  "Corrected forecast-window diagnostic for cutoff %s | internal scale %s | synthesis sample cap %d",
  as.character(cutoff_date),
  analysis_scale,
  as.integer(sample_cap)
)
caption_text <- paste(
  "Corrected diagnostic bundle rebuilt from retained fit objects and cached predictive draws.",
  "Forecast-window quantile lines are derived from synthesized USGS predictive draws on log1p(cms) scale.",
  "No exp() back-transform is applied when the run contract is already log1p_cms.",
  if (isTRUE(skip_history_model)) "History-side model ribbons were intentionally omitted in this quick diagnostic rerender." else "",
  sprintf("The diagnostic synthesis uses a deterministic cap of %d posterior draws for turnaround.", as.integer(sample_cap))
)

aug_png <- file.path(report_dir, "exdqlm_multivar_synth_keep_cutoff_window_augmented_quantiles_log1p.png")
aug_pdf <- file.path(report_dir, "exdqlm_multivar_synth_keep_cutoff_window_augmented_quantiles_log1p.pdf")

p <- ggplot2::ggplot(quant_plot, ggplot2::aes(x = date)) +
  ggplot2::geom_rect(
    data = data.frame(xmin = forecast_start, xmax = max(fc_dates), ymin = -Inf, ymax = Inf),
    mapping = ggplot2::aes(xmin = xmin, xmax = xmax, ymin = ymin, ymax = ymax),
    inherit.aes = FALSE,
    fill = style$theme$forecast_window_fill,
    alpha = style$theme$forecast_window_alpha
  ) +
  ggplot2::geom_ribbon(
    data = subset(quant_plot, segment == "forecast"),
    ggplot2::aes(ymin = interval_low, ymax = interval_high, fill = "USGS predictive 95% credible band"),
    alpha = 0.35,
    color = NA
  ) +
  ggplot2::geom_line(
    data = sample_plot,
    ggplot2::aes(y = value, group = interaction(segment, sample_index), color = "Posterior draws"),
    linewidth = style$posterior$sample_line_width,
    alpha = style$posterior$sample_line_alpha,
    lineend = "round"
  ) +
  ggplot2::geom_line(
    data = quant_plot,
    ggplot2::aes(y = observed, color = "Observed USGS"),
    linewidth = 0.9,
    lineend = "round"
  ) +
  ggplot2::geom_line(
    data = quant_plot,
    ggplot2::aes(y = model_mean, color = "Predictive mean"),
    linewidth = 0.9,
    lineend = "round"
  ) +
  ggplot2::geom_line(
    data = forecast_long,
    ggplot2::aes(y = value, color = quantile_label),
    linewidth = 0.8,
    lineend = "round"
  ) +
  ggplot2::geom_segment(
    data = data.frame(date = cutoff_date),
    mapping = ggplot2::aes(x = date, xend = date, y = -Inf, yend = Inf),
    inherit.aes = FALSE,
    color = style$colors$cutoff,
    linewidth = 0.55,
    linetype = "22"
  ) +
  ggplot2::scale_color_manual(
    values = c(
      "Observed USGS" = style$colors$observed,
      "Predictive mean" = style$colors$median,
      "Posterior draws" = style$colors$sample_paths,
      q05 = quant_colors[["q05"]],
      q20 = quant_colors[["q20"]],
      q35 = quant_colors[["q35"]],
      q50 = quant_colors[["q50"]],
      q65 = quant_colors[["q65"]],
      q80 = quant_colors[["q80"]],
      q95 = quant_colors[["q95"]]
    ),
    breaks = c("Observed USGS", "Predictive mean", "Posterior draws", "q05", "q20", "q35", "q50", "q65", "q80", "q95")
  ) +
  ggplot2::scale_fill_manual(values = c("USGS predictive 95% credible band" = style$colors$interval_outer)) +
  ggplot2::scale_x_date(date_breaks = "1 week", date_labels = "%b %d") +
  ggplot2::labs(
    title = title_text,
    subtitle = subtitle_text,
    x = NULL,
    y = post_publication_y_label(style),
    caption = caption_text
  ) +
  post_publication_base_theme(style)

post_publication_save_plot(p, png_path = aug_png, pdf_path = aug_pdf, style = style)

summary_json_path <- file.path(report_dir, "summary.json")
summary_obj <- list(
  run_root = run_root,
  outputs_dir = outputs_dir,
  report_dir = report_dir,
  analysis_scale_post_internal = analysis_scale,
  diagnostic_sample_cap = as.integer(sample_cap),
  skip_history_model = isTRUE(skip_history_model),
  corrected_quantiles_csv = corrected_quant_path,
  corrected_sample_subset_csv = corrected_sample_subset_path,
  corrected_history_samples_rds = hist_samples_rds,
  corrected_forecast_samples_rds = fc_samples_rds,
  current_vs_corrected_forecast_quantiles_csv = current_vs_corrected_path,
  augmented_png = aug_png,
  augmented_pdf = aug_pdf
)
writeLines(jsonlite::toJSON(summary_obj, auto_unbox = TRUE, pretty = TRUE), con = summary_json_path, useBytes = TRUE)

cat(sprintf("Wrote diagnostic bundle to %s\n", report_dir))
