#!/usr/bin/env Rscript

parse_args <- function(argv) {
  out <- list()
  i <- 1L
  while (i <= length(argv)) {
    key <- argv[[i]]
    if (!startsWith(key, "--")) {
      i <- i + 1L
      next
    }
    key <- sub("^--", "", key)
    key <- gsub("-", "_", key, fixed = TRUE)
    if (i == length(argv) || startsWith(argv[[i + 1L]], "--")) {
      out[[key]] <- TRUE
      i <- i + 1L
    } else {
      out[[key]] <- argv[[i + 1L]]
      i <- i + 2L
    }
  }
  out
}

`%||%` <- function(x, y) {
  if (is.null(x) || identical(x, "") || (length(x) == 1L && is.na(x))) y else x
}

require_pkg <- function(pkg) {
  if (!requireNamespace(pkg, quietly = TRUE)) {
    stop(sprintf("Package '%s' is required.", pkg), call. = FALSE)
  }
}

write_csv_det <- function(df, path) {
  dir.create(dirname(path), recursive = TRUE, showWarnings = FALSE)
  if (exists("post_write_csv_deterministic", inherits = TRUE)) {
    post_write_csv_deterministic(df, path, numeric_digits = 15L)
  } else {
    utils::write.csv(df, path, row.names = FALSE)
  }
}

read_history_observed_from_retros <- function(run_root, hist_dates) {
  retros_path <- file.path(run_root, "post", "inputs", "retros_post_adapter.csv")
  if (!file.exists(retros_path)) {
    stop(sprintf("Missing retros_post_adapter.csv at %s", retros_path), call. = FALSE)
  }
  retros_df <- utils::read.csv(retros_path, stringsAsFactors = FALSE, check.names = FALSE)
  if (!all(c("Date", "USGS") %in% names(retros_df))) {
    stop(sprintf("retros_post_adapter.csv missing Date/USGS columns: %s", retros_path), call. = FALSE)
  }
  retros_df$Date <- as.Date(retros_df$Date)
  idx <- match(as.Date(hist_dates), retros_df$Date)
  if (any(is.na(idx))) {
    stop("Unable to align all historical dates to retros_post_adapter.csv", call. = FALSE)
  }
  as.numeric(retros_df$USGS[idx])
}

quantile_prob_label_local <- function(p) sprintf("q%02d", as.integer(round(100 * p)))

smoke_next_idx_block_local <- function(prev_idx, block_len) {
  block_len <- suppressWarnings(as.integer(block_len[[1L]]))
  start <- if (length(prev_idx) == 0L) 0L else as.integer(prev_idx[[length(prev_idx)]])
  if (!is.finite(block_len) || block_len <= 0L) return(integer(0))
  seq_len(block_len) + start
}

smoke_forecast_core_dim_local <- function(seg_id, p_core, j_total) {
  as.integer(p_core * (j_total - as.integer(seg_id) + 2L))
}

smoke_build_usgs_projection_weights_local <- function(ff_seg, state_len, seg_id, p_core, j_total, use_covariates, ppx_val, transfer_mode) {
  ff_n <- nrow(ff_seg)
  weights <- rep(0, state_len)
  base_len <- min(p_core, ff_n, state_len)
  if (base_len > 0L) {
    base_vals <- as.numeric(ff_seg[seq_len(base_len), 1, drop = TRUE])
    base_vals[!is.finite(base_vals)] <- 0
    weights[seq_len(base_len)] <- base_vals
  }

  use_transfer_forecast_projection <- isTRUE(use_covariates) &&
    identical(transfer_mode, "keep") &&
    is.finite(ppx_val) &&
    ppx_val > 0L

  if (isTRUE(use_transfer_forecast_projection)) {
    core_dim <- smoke_forecast_core_dim_local(seg_id, p_core, j_total)
    zeta_idx <- core_dim + 1L
    if (zeta_idx <= ff_n && zeta_idx <= state_len) {
      zeta_w <- as.numeric(ff_seg[zeta_idx, 1, drop = TRUE])
      if (!is.finite(zeta_w)) zeta_w <- 0
      weights[zeta_idx] <- zeta_w
    }
  }
  weights
}

smoke_project_state_gaussian_local <- function(Mu, Sigma, ff_seg, seg_id, p_core, j_total, use_covariates, ppx_val, transfer_mode) {
  w <- smoke_build_usgs_projection_weights_local(
    ff_seg = ff_seg,
    state_len = length(Mu),
    seg_id = seg_id,
    p_core = p_core,
    j_total = j_total,
    use_covariates = use_covariates,
    ppx_val = ppx_val,
    transfer_mode = transfer_mode
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

load_fit_env <- function(path) {
  e <- new.env(parent = baseenv())
  load(path, envir = e)
  e
}

resolve_scale <- function(run_root) {
  Sys.setenv(UNIFIED_RUN_ROOT = run_root)
  post_resolve_analysis_scale_post_internal()
}

transform_samples_to_log1p <- function(mat, from_scale, context) {
  out <- post_transform_internal_to_log1p_mat(mat, from_scale = from_scale, context = context)
  as.matrix(out)
}

transform_vec_to_log1p <- function(x, from_scale, context) {
  mat <- matrix(as.numeric(x), nrow = 1L)
  as.numeric(transform_samples_to_log1p(mat, from_scale = from_scale, context = context))
}

col_quantiles_local <- function(mat, probs = c(0.025, 0.5, 0.975)) {
  out <- apply(mat, 2L, stats::quantile, probs = probs, na.rm = TRUE, type = 8, names = FALSE)
  matrix(out, nrow = length(probs), byrow = FALSE)
}

gaussian_band_to_log1p <- function(mean_vec, sd_vec, probs = c(0.025, 0.5, 0.975), from_scale = "log1p_cms", context = "forecast.location.band") {
  sd_vec <- pmax(as.numeric(sd_vec), 0)
  z <- stats::qnorm(probs)
  latent <- matrix(mean_vec, nrow = length(probs), ncol = length(mean_vec), byrow = TRUE) +
    outer(z, sd_vec)
  transform_samples_to_log1p(latent, from_scale = from_scale, context = context)
}

compute_history_location_summary <- function(env, q_tag, p0, hist_idx, from_scale) {
  theta_obj <- get(sprintf("samp.theta_%s_exAL_synth_DISC", q_tag), envir = env, inherits = FALSE)
  sts_arr <- get(sprintf("samp.sts_%s_exAL_synth_DISC", q_tag), envir = env, inherits = FALSE)
  gamma_mat <- get(sprintf("samp.gamma_%s_exAL_synth_DISC", q_tag), envir = env, inherits = FALSE)
  sigma_mat <- get(sprintf("samp.sigma_%s_exAL_synth_DISC", q_tag), envir = env, inherits = FALSE)

  n_samp <- min(
    dim(theta_obj$samp_theta)[3],
    dim(sts_arr)[3],
    ncol(gamma_mat),
    ncol(sigma_mat)
  )
  th <- theta_obj$samp_theta[, , seq_len(n_samp), drop = FALSE]
  stj <- matrix(sts_arr[1L, hist_idx, seq_len(n_samp), drop = FALSE], nrow = length(hist_idx), ncol = n_samp)
  gamj <- as.numeric(gamma_mat[1L, seq_len(n_samp)])
  sigj <- as.numeric(sigma_mat[1L, seq_len(n_samp)])
  ff_use <- get("FF", envir = env, inherits = FALSE)

  xb <- matrix(NA_real_, nrow = length(hist_idx), ncol = n_samp)
  for (k in seq_along(hist_idx)) {
    t_idx <- hist_idx[[k]]
    th_t <- matrix(th[, t_idx, ], nrow = dim(th)[1], ncol = n_samp)
    p_use <- min(nrow(ff_use), nrow(th_t))
    xb[k, ] <- as.vector(t(ff_use[seq_len(p_use), 1L, t_idx, drop = FALSE][, 1L, 1L]) %*% th_t[seq_len(p_use), , drop = FALSE])
  }

  mu <- xb + sweep(stj, 2L, sigj * abs(gamj) * C_fn(p0, gamj), `*`)
  mu_t <- t(mu)
  mu_log1p <- transform_samples_to_log1p(mu_t, from_scale = from_scale, context = sprintf("hist.location.q%s", q_tag))
  q_mat <- col_quantiles_local(mu_log1p, probs = c(0.025, 0.5, 0.975))
  list(
    mean = colMeans(mu_log1p, na.rm = TRUE),
    q025 = q_mat[1L, ],
    q500 = q_mat[2L, ],
    q975 = q_mat[3L, ]
  )
}

compute_forecast_location_summary <- function(env, q_tag, p0, from_scale, p_core, transfer_mode) {
  obj <- get(sprintf("new.theta.out_%s_exAL_synth_DISC", q_tag), envir = env, inherits = FALSE)
  ranges <- get("ranges", envir = env, inherits = FALSE)
  ff_list <- get("FF_list", envir = env, inherits = FALSE)
  horizon <- as.integer(ranges[[1L]])
  j_total <- as.integer(get("J", envir = env, inherits = FALSE))
  ppx_val <- if (exists("ppx", envir = env, inherits = FALSE)) suppressWarnings(as.integer(get("ppx", envir = env, inherits = FALSE))) else 0L
  use_covariates <- isTRUE(get0("use_covariates", envir = env, inherits = FALSE, ifnotfound = FALSE))

  ks <- -diff(c(as.integer(ranges), 0L))
  j_use <- min(j_total, length(ff_list), length(obj$sm_ens), length(obj$sC_ens))
  idx <- c(0L)
  mean_vec <- rep(NA_real_, horizon)
  sd_vec <- rep(NA_real_, horizon)

  for (j in seq_len(j_use)) {
    idx <- smoke_next_idx_block_local(idx, ks[j_use - j + 1L])
    if (length(idx) == 0L) next
    sm_j <- obj$sm_ens[[j]]
    sc_j <- obj$sC_ens[[j]]
    seg_cap <- min(length(idx), ncol(sm_j), dim(sc_j)[3])
    if (!is.finite(seg_cap) || seg_cap <= 0L) next
    tt <- 1L
    for (t_idx in idx[seq_len(seg_cap)]) {
      proj <- smoke_project_state_gaussian_local(
        Mu = sm_j[, tt],
        Sigma = sc_j[, , tt],
        ff_seg = ff_list[[j]],
        seg_id = j,
        p_core = p_core,
        j_total = j_total,
        use_covariates = use_covariates,
        ppx_val = ppx_val,
        transfer_mode = transfer_mode
      )
      mean_vec[t_idx] <- as.numeric(proj[["mean"]])
      sd_vec[t_idx] <- as.numeric(proj[["sd"]])
      tt <- tt + 1L
    }
  }

  mean_log1p <- transform_vec_to_log1p(mean_vec, from_scale = from_scale, context = sprintf("forecast.location.mean.q%s", q_tag))
  loc_band <- gaussian_band_to_log1p(
    mean_vec = mean_vec,
    sd_vec = sd_vec,
    probs = c(0.025, 0.5, 0.975),
    from_scale = from_scale,
    context = sprintf("forecast.location.band.q%s", q_tag)
  )
  list(
    mean = mean_log1p,
    q025 = loc_band[1L, ],
    q500 = loc_band[2L, ],
    q975 = loc_band[3L, ]
  )
}

location_lines_long <- function(df, cols_map) {
  rows <- lapply(names(cols_map), function(label) {
    data.frame(
      date = df$date,
      segment = df$segment,
      quantile = label,
      value = df[[cols_map[[label]]]],
      stringsAsFactors = FALSE
    )
  })
  out <- do.call(rbind, rows)
  out$quantile <- factor(out$quantile, levels = names(cols_map))
  out
}

adaptive_date_scale <- function(date_vec) {
  date_vec <- as.Date(date_vec)
  date_vec <- date_vec[!is.na(date_vec)]
  if (length(date_vec) == 0L) {
    return(list(breaks = "1 month", labels = "%Y-%m", angle = 45))
  }
  span_days <- as.numeric(max(date_vec) - min(date_vec))
  if (!is.finite(span_days)) span_days <- 0
  if (span_days > 2500) {
    list(breaks = "6 months", labels = "%Y-%m", angle = 45)
  } else if (span_days > 900) {
    list(breaks = "3 months", labels = "%Y-%m", angle = 45)
  } else if (span_days > 240) {
    list(breaks = "1 month", labels = "%Y-%m", angle = 45)
  } else if (span_days > 120) {
    list(breaks = "2 weeks", labels = "%b %d", angle = 45)
  } else {
    list(breaks = "1 week", labels = "%b %d", angle = 45)
  }
}

render_location_plot <- function(main_df, ensemble_df, style, png_path, pdf_path, forecast_only = FALSE, show_q50_band = TRUE, history_only = FALSE, quantile_subset = NULL) {
  require_pkg("ggplot2")
  palette <- c(q05 = "#9B1D20", q20 = "#C45D38", q35 = "#E38D2C", q50 = "#6A3D9A", q65 = "#2E86AB", q80 = "#1F9E89", q95 = "#006D2C")
  ltypes <- if (isTRUE(show_q50_band)) {
    c(q05 = "22", q20 = "solid", q35 = "solid", q50 = "solid", q65 = "solid", q80 = "solid", q95 = "22")
  } else {
    c(q05 = "solid", q20 = "solid", q35 = "solid", q50 = "solid", q65 = "solid", q80 = "solid", q95 = "solid")
  }
  widths <- c(q05 = 0.70, q20 = 0.78, q35 = 0.86, q50 = 1.15, q65 = 0.86, q80 = 0.78, q95 = 0.70)
  cols_map <- c(q05 = "loc_q05_mean", q20 = "loc_q20_mean", q35 = "loc_q35_mean", q50 = "loc_q50_mean", q65 = "loc_q65_mean", q80 = "loc_q80_mean", q95 = "loc_q95_mean")
  if (!is.null(quantile_subset)) {
    keep <- intersect(quantile_subset, names(cols_map))
    cols_map <- cols_map[keep]
    palette <- palette[keep]
    ltypes <- ltypes[keep]
    widths <- widths[keep]
  }
  line_df <- location_lines_long(main_df, cols_map)

  plot_df <- if (forecast_only) main_df[main_df$segment == "forecast", , drop = FALSE] else main_df
  line_df <- line_df[line_df$segment %in% unique(plot_df$segment), , drop = FALSE]
  date_scale <- adaptive_date_scale(plot_df$date)

  hist_obs <- plot_df[plot_df$segment == "history", c("date", "observed"), drop = FALSE]
  fc_obs <- plot_df[plot_df$segment == "forecast", c("date", "observed"), drop = FALSE]
  if (!is.null(ensemble_df) && nrow(ensemble_df) > 0L) {
    ensemble_df <- ensemble_df[ensemble_df$date %in% plot_df$date, , drop = FALSE]
    ensemble_df$legend_label <- ifelse(ensemble_df$provider == "GloFAS", "GloFAS ensembles", "NWS ensembles")
  }

  cutoff_date <- max(main_df$date[main_df$segment == "history"])
  forecast_start <- min(main_df$date[main_df$segment == "forecast"])
  forecast_end <- max(main_df$date[main_df$segment == "forecast"])

  title_text <- if (isTRUE(history_only)) {
    if (isTRUE(show_q50_band)) "USGS Historical Location Dynamics Used Before exAL Sampling" else "USGS Historical Mean Location Curves Used Before exAL Sampling"
  } else if (forecast_only) {
    if (isTRUE(show_q50_band)) "USGS Location Dynamics Used Before exAL Sampling" else "USGS Mean Location Curves Used Before exAL Sampling"
  } else {
    if (isTRUE(show_q50_band)) "USGS Location Dynamics Used to Generate exAL Predictive Samples" else "USGS Mean Location Curves Used to Generate exAL Predictive Samples"
  }
  subtitle_text <- if (isTRUE(history_only)) {
    if (isTRUE(show_q50_band)) {
      "Historical window only; row-level location means before synthesis"
    } else {
      if (length(cols_map) < 7L) {
        "Historical window only; mean-only central quantile-row locations"
      } else {
        "Historical window only; no credible bands, each colored line is one quantile-row mean location"
      }
    }
  } else if (forecast_only) {
    if (isTRUE(show_q50_band)) {
      "Forecast window only; row-level location means before synthesis"
    } else {
      "Forecast window only; no credible bands, each colored line is one quantile-row mean location"
    }
  } else {
    if (isTRUE(show_q50_band)) {
      "Full cutoff window; row-level locations before rexal() and before synthesis"
    } else {
      "Full cutoff window; no credible bands, each colored line is one quantile-row mean location"
    }
  }

  p <- ggplot2::ggplot(plot_df, ggplot2::aes(x = date))

  if (!forecast_only && !isTRUE(history_only)) {
    p <- p + ggplot2::geom_rect(
      data = data.frame(xmin = forecast_start, xmax = forecast_end, ymin = -Inf, ymax = Inf),
      mapping = ggplot2::aes(xmin = xmin, xmax = xmax, ymin = ymin, ymax = ymax),
      inherit.aes = FALSE,
      fill = style$theme$forecast_window_fill,
      alpha = style$theme$forecast_window_alpha
    )
  }

  if (isTRUE(show_q50_band)) {
    p <- p + ggplot2::geom_ribbon(
      ggplot2::aes(ymin = loc_q50_q025, ymax = loc_q50_q975, fill = "q50 location 95% band"),
      alpha = 0.22,
      color = NA
    )
  }

  if (!is.null(ensemble_df) && nrow(ensemble_df) > 0L) {
    p <- p + ggplot2::geom_line(
      data = ensemble_df,
      mapping = ggplot2::aes(y = value, group = interaction(provider, member), color = legend_label),
      linewidth = 0.55,
      alpha = 0.20,
      lineend = "round"
    )
  }

  p <- p +
    ggplot2::geom_line(
      data = line_df,
      mapping = ggplot2::aes(y = value, color = quantile, linetype = quantile, linewidth = quantile, group = quantile),
      alpha = 0.94,
      lineend = "round"
    )

  if (nrow(hist_obs) > 0L) {
    p <- p +
      ggplot2::geom_line(
        data = hist_obs,
        mapping = ggplot2::aes(y = observed, color = "USGS observations"),
        linewidth = 0.95,
        lineend = "round"
      ) +
      ggplot2::geom_point(
        data = hist_obs,
        mapping = ggplot2::aes(y = observed),
        color = "#238B45",
        fill = "#238B45",
        shape = 16,
        size = 1.5,
        alpha = 0.95,
        show.legend = FALSE
      )
  }

  if (nrow(fc_obs) > 0L) {
    p <- p +
      ggplot2::geom_line(
        data = fc_obs,
        mapping = ggplot2::aes(y = observed, color = "Held-out USGS"),
        linewidth = 0.98,
        lineend = "round"
      ) +
      ggplot2::geom_point(
        data = fc_obs,
        mapping = ggplot2::aes(y = observed),
        color = "#B22222",
        fill = "white",
        shape = 21,
        stroke = 0.55,
        size = 1.75,
        show.legend = FALSE
      )
  }

  if (!forecast_only && !isTRUE(history_only)) {
    p <- p + ggplot2::geom_segment(
      data = data.frame(date = cutoff_date),
      mapping = ggplot2::aes(x = date, xend = date, y = -Inf, yend = Inf),
      inherit.aes = FALSE,
      color = style$colors$cutoff,
      linewidth = 0.55,
      linetype = "22"
    )
  }

  color_values <- c(
    "USGS observations" = "#238B45",
    "Held-out USGS" = "#B22222",
    "GloFAS ensembles" = "#E67E22",
    "NWS ensembles" = "#756BB1",
    palette
  )

  color_breaks <- c(
    if (nrow(hist_obs) > 0L) "USGS observations",
    if (nrow(fc_obs) > 0L) "Held-out USGS",
    if (!is.null(ensemble_df) && any(ensemble_df$provider == "GloFAS")) "GloFAS ensembles",
    if (!is.null(ensemble_df) && any(ensemble_df$provider == "NWS")) "NWS ensembles",
    names(cols_map)
  )

  p <- p +
    ggplot2::scale_color_manual(values = color_values, breaks = color_breaks) +
    ggplot2::scale_linetype_manual(values = ltypes, breaks = names(cols_map), labels = names(cols_map)) +
    ggplot2::scale_linewidth_manual(values = widths, breaks = names(cols_map), labels = names(cols_map)) +
    ggplot2::scale_x_date(date_breaks = date_scale$breaks, date_labels = date_scale$labels) +
    ggplot2::labs(
      title = title_text,
      subtitle = subtitle_text,
      x = if (forecast_only) "Forecast date" else "Date",
      y = post_publication_y_label(style)
    ) +
    post_publication_base_theme(style) +
    ggplot2::theme(
      legend.position = "bottom",
      legend.direction = "horizontal",
      legend.box = "vertical",
      legend.text = ggplot2::element_text(size = 10.2),
      axis.text.x = ggplot2::element_text(angle = date_scale$angle, hjust = 1),
      plot.margin = ggplot2::margin(10, 10, 8, 10)
    )

  if (isTRUE(show_q50_band)) {
    p <- p +
      ggplot2::scale_fill_manual(values = c("q50 location 95% band" = "#D97AA5"), breaks = "q50 location 95% band") +
      ggplot2::guides(
        color = ggplot2::guide_legend(order = 1, nrow = 3, byrow = TRUE, override.aes = list(alpha = 1)),
        linetype = "none",
        linewidth = "none",
        fill = ggplot2::guide_legend(order = 2, nrow = 1)
      )
  } else {
    p <- p +
      ggplot2::guides(
        color = ggplot2::guide_legend(order = 1, nrow = 3, byrow = TRUE, override.aes = list(alpha = 1)),
        linetype = "none",
        linewidth = "none"
      )
  }

  post_publication_save_plot(p, png_path = png_path, pdf_path = pdf_path, style = style)
}

main <- function() {
  require_pkg("ggplot2")
  args <- parse_args(commandArgs(trailingOnly = TRUE))
  project_root <- normalizePath(getwd(), mustWork = TRUE)
  run_root <- normalizePath(args$run_root %||% "", mustWork = TRUE)
  quant_source_run_root <- normalizePath(args$quant_source_run_root %||% run_root, mustWork = TRUE)
  report_dir <- normalizePath(args$report_dir %||% "", mustWork = FALSE)
  mean_only <- isTRUE(args$mean_only)
  if (!nzchar(report_dir)) {
    stop("Provide --report-dir", call. = FALSE)
  }
  dir.create(report_dir, recursive = TRUE, showWarnings = FALSE)

  source(file.path(project_root, "R", "environmetrics", "02_helpers_core.R"))
  source(file.path(project_root, "R", "unified", "post_publication_figures.R"))

  from_scale <- resolve_scale(run_root)
  transfer_mode <- tolower(trimws(Sys.getenv("UNIFIED_MULTIVAR_FORECAST_TRANSFER_MODE", "keep")))
  if (!transfer_mode %in% c("drop", "keep")) transfer_mode <- "keep"
  cache_dir <- file.path(run_root, "post", "cache")
  outputs_dir <- file.path(quant_source_run_root, "post", "outputs", basename(quant_source_run_root))
  quant_matches <- if (dir.exists(outputs_dir)) Sys.glob(file.path(outputs_dir, "*_cutoff_window_quantiles.csv")) else character(0)
  quant_df <- NULL
  model_id <- NULL
  if (length(quant_matches) > 0L) {
    quant_path <- quant_matches[[1L]]
    quant_df <- post_publication_read_contract_csv(
      quant_path,
      required_cols = c("model_id", "date", "segment", "observed"),
      context = "location-dynamics review quantiles"
    )
    quant_df$date <- as.Date(quant_df$date)
    quant_df <- quant_df[order(quant_df$date, quant_df$segment, method = "radix"), , drop = FALSE]
    model_id <- unique(quant_df$model_id)[[1L]]
    hist_cache <- file.path(cache_dir, sprintf("%s__mode-%s__multivar_hist_usgs_location_summary_log1p.rds", model_id, transfer_mode))
    fc_cache <- file.path(cache_dir, sprintf("%s__mode-%s__multivar_forecast_usgs_location_summary_log1p.rds", model_id, transfer_mode))
  } else {
    hist_candidates <- Sys.glob(file.path(cache_dir, sprintf("*__mode-%s__multivar_hist_usgs_location_summary_log1p.rds", transfer_mode)))
    fc_candidates <- Sys.glob(file.path(cache_dir, sprintf("*__mode-%s__multivar_forecast_usgs_location_summary_log1p.rds", transfer_mode)))
    hist_cache <- if (length(hist_candidates) > 0L) hist_candidates[[1L]] else ""
    fc_cache <- if (length(fc_candidates) > 0L) fc_candidates[[1L]] else ""
  }
  if (!nzchar(hist_cache) || !file.exists(hist_cache) || !nzchar(fc_cache) || !file.exists(fc_cache)) {
    stop(sprintf("location summary cache missing; hist=%s forecast=%s", hist_cache, fc_cache), call. = FALSE)
  }
  hist_summary <- readRDS(hist_cache)
  if (is.null(model_id) || !nzchar(model_id)) {
    model_id <- hist_summary$model_id %||% basename(run_root)
  }
  fc_summary <- if (file.exists(fc_cache)) readRDS(fc_cache) else NULL
  labels <- as.character(hist_summary$q_labels)
  hist_dates <- as.Date(hist_summary$dates)
  if (is.null(quant_df)) {
    hist_obs <- read_history_observed_from_retros(run_root, hist_dates)
    forecast_quant_df <- data.frame()
  } else {
    hist_obs <- quant_df$observed[quant_df$segment == "history"]
    forecast_quant_df <- quant_df[quant_df$segment == "forecast" & !is.na(quant_df$date), , drop = FALSE]
    if (length(hist_obs) != length(hist_dates)) {
      hist_obs <- read_history_observed_from_retros(run_root, hist_dates)
      forecast_quant_df <- data.frame()
    }
  }
  has_forecast_rows <- nrow(forecast_quant_df) > 0L
  fc_obs <- forecast_quant_df$observed

  hist_df <- data.frame(
    date = hist_dates,
    segment = "history",
    observed = hist_obs,
    stringsAsFactors = FALSE
  )
  for (nm in labels) {
    row_idx_hist <- match(nm, hist_summary$q_labels)
    hist_df[[sprintf("loc_%s_mean", nm)]] <- hist_summary$mean_mat[row_idx_hist, ]
  }
  q50_hist_idx <- match("q50", hist_summary$q_labels)
  hist_df$loc_q50_q025 <- hist_summary$q025_mat[q50_hist_idx, ]
  hist_df$loc_q50_q500 <- hist_summary$q500_mat[q50_hist_idx, ]
  hist_df$loc_q50_q975 <- hist_summary$q975_mat[q50_hist_idx, ]

  if (isTRUE(has_forecast_rows)) {
    fc_dates <- as.Date(fc_summary$dates)
    fc_df <- data.frame(
      date = fc_dates,
      segment = "forecast",
      observed = fc_obs,
      stringsAsFactors = FALSE
    )
    for (nm in labels) {
      row_idx_fc <- match(nm, fc_summary$q_labels)
      fc_df[[sprintf("loc_%s_mean", nm)]] <- fc_summary$mean_mat[row_idx_fc, ]
    }
    q50_fc_idx <- match("q50", fc_summary$q_labels)
    fc_df$loc_q50_q025 <- fc_summary$q025_mat[q50_fc_idx, ]
    fc_df$loc_q50_q500 <- fc_summary$q500_mat[q50_fc_idx, ]
    fc_df$loc_q50_q975 <- fc_summary$q975_mat[q50_fc_idx, ]
    main_df <- rbind(hist_df, fc_df)
    rownames(main_df) <- NULL
  } else {
    main_df <- hist_df
  }

  ensemble_paths <- post_publication_resolve_ensemble_input_paths(file.path(run_root, "post"))
  ensemble_frames <- list()
  if (isTRUE(has_forecast_rows) && !is.null(ensemble_paths$glofas_path) && file.exists(ensemble_paths$glofas_path)) {
    ensemble_frames[[length(ensemble_frames) + 1L]] <- post_publication_read_member_forecasts(ensemble_paths$glofas_path, "GloFAS")
  }
  if (isTRUE(has_forecast_rows) && !is.null(ensemble_paths$nws_path) && file.exists(ensemble_paths$nws_path)) {
    ensemble_frames[[length(ensemble_frames) + 1L]] <- post_publication_read_member_forecasts(ensemble_paths$nws_path, "NWS")
  }
  ensemble_df <- if (length(ensemble_frames) > 0L) do.call(rbind, ensemble_frames) else NULL

  style <- post_publication_load_style(project_root, file.path(project_root, "config", "post_publication_figures.yaml"))
  style$theme$legend_position <- "bottom"

  history_only <- !isTRUE(has_forecast_rows)
  full_png <- file.path(report_dir, if (history_only) {
    if (mean_only) "history_window_usgs_location_mean_dynamics_log1p.png" else "history_window_usgs_location_dynamics_log1p.png"
  } else if (mean_only) "cutoff_window_usgs_location_mean_dynamics_log1p.png" else "cutoff_window_usgs_location_dynamics_log1p.png")
  full_pdf <- sub("\\.png$", ".pdf", full_png)
  fc_png <- file.path(report_dir, if (mean_only) "forecast_window_usgs_location_mean_dynamics_log1p.png" else "forecast_window_usgs_location_dynamics_log1p.png")
  fc_pdf <- sub("\\.png$", ".pdf", fc_png)
  central_png <- file.path(report_dir, if (history_only) {
    if (mean_only) "history_window_usgs_location_mean_dynamics_central_log1p.png" else "history_window_usgs_location_dynamics_central_log1p.png"
  } else if (mean_only) "cutoff_window_usgs_location_mean_dynamics_central_log1p.png" else "cutoff_window_usgs_location_dynamics_central_log1p.png")
  central_pdf <- sub("\\.png$", ".pdf", central_png)

  render_location_plot(main_df, ensemble_df, style, full_png, full_pdf, forecast_only = FALSE, show_q50_band = !mean_only, history_only = history_only)
  render_location_plot(
    main_df,
    ensemble_df,
    style,
    central_png,
    central_pdf,
    forecast_only = FALSE,
    show_q50_band = FALSE,
    history_only = history_only,
    quantile_subset = c("q20", "q35", "q50", "q65", "q80")
  )
  if (!history_only) {
    render_location_plot(main_df, ensemble_df, style, fc_png, fc_pdf, forecast_only = TRUE, show_q50_band = !mean_only, history_only = FALSE)
  }

  write_csv_det(main_df, file.path(report_dir, "usgs_location_dynamics_log1p.csv"))

  checks <- data.frame(
    metric = c(
      "scale",
      "history_days",
      "forecast_days",
      "forecast_q50_location_mean_min",
      "forecast_q50_location_mean_max",
      "forecast_q05_location_mean_min",
      "forecast_q95_location_mean_max"
    ),
    value = c(
      from_scale,
      as.character(nrow(hist_df)),
      if (history_only) "0" else as.character(nrow(fc_df)),
      if (history_only) NA_character_ else sprintf("%.6f", min(fc_df$loc_q50_mean, na.rm = TRUE)),
      if (history_only) NA_character_ else sprintf("%.6f", max(fc_df$loc_q50_mean, na.rm = TRUE)),
      if (history_only) NA_character_ else sprintf("%.6f", min(fc_df$loc_q05_mean, na.rm = TRUE)),
      if (history_only) NA_character_ else sprintf("%.6f", max(fc_df$loc_q95_mean, na.rm = TRUE))
    ),
    stringsAsFactors = FALSE
  )
  write_csv_det(checks, file.path(report_dir, "location_dynamics_summary.csv"))

  md <- c(
    "# exAL-M-T1 USGS Location Dynamics Review",
    "",
    sprintf("- run root: `%s`", run_root),
    sprintf("- quantile source run root: `%s`", quant_source_run_root),
    sprintf("- model id: `%s`", model_id),
    sprintf("- internal/post scale: `%s`", from_scale),
    "- these lines are the row-level USGS locations used before `rexal()` sampling, not the synthesized predictive output",
    sprintf("- mean-only mode: `%s`", if (mean_only) "true" else "false"),
    "",
    "## Generated figures",
    "",
    sprintf("- full cutoff-window location dynamics: `%s`", full_png),
    sprintf("- central quantile location dynamics: `%s`", central_png),
    if (!history_only) sprintf("- forecast-window location dynamics: `%s`", fc_png),
    "",
    "## Supporting files",
    "",
    sprintf("- location dynamics csv: `%s`", file.path(report_dir, "usgs_location_dynamics_log1p.csv")),
    sprintf("- summary checks: `%s`", file.path(report_dir, "location_dynamics_summary.csv"))
  )
  writeLines(md, con = file.path(report_dir, "README.md"))

  cat(sprintf("WROTE %s\n", full_png))
  cat(sprintf("WROTE %s\n", central_png))
  if (!history_only) {
    cat(sprintf("WROTE %s\n", fc_png))
  }
}

main()
