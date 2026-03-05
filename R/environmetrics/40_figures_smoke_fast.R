###############################################################################
# Smoke-only figures module
# Purpose:
#   - Produce a minimal figure set quickly for run-scoped post smoke validation.
#   - Reuse in-memory objects from earlier modules without touching model logic.
###############################################################################

as_trace_vector <- function(x) {
  if (is.null(x)) {
    return(numeric(0))
  }
  if (is.atomic(x)) {
    return(as.numeric(x))
  }
  numeric(0)
}

fetch_numeric_object <- function(name) {
  as_trace_vector(get0(name, ifnotfound = NULL, inherits = TRUE))
}

fetch_first_numeric <- function(candidates) {
  for (nm in candidates) {
    vals <- fetch_numeric_object(nm)
    if (length(vals) > 0L) {
      return(vals)
    }
  }
  numeric(0)
}

plot_trace <- function(values, title_txt, ylab_txt) {
  vals <- as.numeric(values)
  if (length(vals) == 0L || all(!is.finite(vals))) {
    plot.new()
    title(main = paste0(title_txt, " (missing)"))
    return(invisible(NULL))
  }
  plot.ts(vals, main = title_txt, xlab = "Iteration", ylab = ylab_txt, lwd = 1.5)
  invisible(NULL)
}

safe_obj_list <- function(name) {
  obj <- get0(name, ifnotfound = NULL, inherits = TRUE)
  if (!is.list(obj)) {
    return(NULL)
  }
  obj
}

matrix_sample_time <- function(x, horizon = NA_integer_) {
  mat <- as.matrix(x)
  nr <- nrow(mat)
  nc <- ncol(mat)
  if (is.finite(horizon)) {
    hz <- as.integer(horizon[[1L]])
    if (nr == hz && nc != hz) return(t(mat))
    if (nc == hz) return(mat)
  }
  if (nr >= nc) mat else t(mat)
}

col_quantiles <- function(mat, probs = c(0.025, 0.5, 0.975)) {
  m <- matrix_sample_time(mat)
  if (!is.matrix(m) || ncol(m) == 0L) {
    return(matrix(NA_real_, nrow = length(probs), ncol = 0L))
  }
  out <- apply(m, 2, quantile, probs = probs, na.rm = TRUE, type = 8, names = FALSE)
  matrix(out, nrow = length(probs), byrow = FALSE)
}

pad_to_horizon <- function(x, horizon) {
  out <- rep(NA_real_, horizon)
  vals <- as.numeric(x)
  n <- min(length(vals), horizon)
  if (n > 0L) {
    out[seq_len(n)] <- vals[seq_len(n)]
  }
  out
}

resolve_future_truth <- function(horizon) {
  h <- as.integer(horizon[[1L]])
  truth <- rep(NA_real_, h)

  infer_start_from_forecasts <- function() {
    fallback_start <- if (exists("FORECAST_START_DATE", inherits = TRUE)) {
      suppressWarnings(as.Date(get("FORECAST_START_DATE", inherits = TRUE)))
    } else {
      as.Date("2022-12-26")
    }
    if (is.na(fallback_start)) fallback_start <- as.Date("2022-12-26")

    starts <- as.Date(character(0))
    if (exists("glofas_forecast", inherits = TRUE) && is.data.frame(glofas_forecast) && "target_date" %in% names(glofas_forecast)) {
      d <- suppressWarnings(as.Date(glofas_forecast$target_date))
      d <- d[!is.na(d)]
      if (length(d) > 0L) starts <- c(starts, min(d))
    }
    if (exists("nws_forecast", inherits = TRUE) && is.data.frame(nws_forecast) && "Date" %in% names(nws_forecast)) {
      d <- suppressWarnings(as.Date(nws_forecast$Date))
      d <- d[!is.na(d)]
      if (length(d) > 0L) starts <- c(starts, min(d))
    }
    starts <- starts[!is.na(starts)]
    if (length(starts) > 0L) min(starts) else fallback_start
  }

  start_date <- infer_start_from_forecasts()
  target_dates <- seq.Date(start_date, by = "day", length.out = h)

  # Match NDLM forecast-window diagnostics: USGS realized future on log(log1p(cms)).
  if (exists("San_Lorenzo_Daily_USGS_R", inherits = TRUE) &&
      is.data.frame(San_Lorenzo_Daily_USGS_R) &&
      "data0" %in% names(San_Lorenzo_Daily_USGS_R)) {
    sl <- San_Lorenzo_Daily_USGS_R
    date_col <- if ("Date" %in% names(sl)) {
      suppressWarnings(as.Date(sl$Date))
    } else if ("timestamp" %in% names(sl)) {
      suppressWarnings(as.Date(sl$timestamp))
    } else if ("time" %in% names(sl)) {
      suppressWarnings(as.Date(sl$time))
    } else {
      as.Date(rep(NA_character_, nrow(sl)))
    }
    flow_log1p <- suppressWarnings(as.numeric(sl$data0))
    ok <- !is.na(date_col) & is.finite(flow_log1p) & (flow_log1p > 0)
    if (sum(ok) > 0L) {
      idx_map <- match(target_dates, date_col[ok])
      valid <- !is.na(idx_map)
      if (any(valid)) {
        truth[valid] <- log(flow_log1p[ok][idx_map[valid]])
      }
    }
  }

  if (all(!is.finite(truth))) {
    idx_tt <- suppressWarnings(as.integer(get0("TT", ifnotfound = NA_integer_, inherits = TRUE)))
    if (is.finite(idx_tt) && exists("Y", inherits = TRUE) && is.matrix(Y) && nrow(Y) >= 1L) {
      obs <- as.numeric(Y[1, ])
      idx <- idx_tt + seq_len(h)
      valid <- idx >= 1L & idx <= length(obs)
      if (any(valid)) {
        truth[valid] <- obs[idx[valid]]
      }
    }
  }

  truth
}

quantile_tag <- function(label) {
  as.character(as.integer(to_quantile_label(label)))
}

load_univar_bundle_with_alias_smoke <- function(path, target_label, source_label = target_label, assign_env = parent.frame()) {
  path <- as.character(path)
  if (!nzchar(path) || !file.exists(path)) {
    return(FALSE)
  }

  source_tag <- quantile_tag(if (is.null(source_label) || !nzchar(as.character(source_label))) target_label else source_label)
  target_tag <- quantile_tag(target_label)

  tmp <- new.env(parent = emptyenv())
  load(path, envir = tmp)
  obj_names <- ls(tmp, all.names = TRUE)
  src_token <- paste0("_", source_tag, "_exAL_synth_DISC_uni")
  tgt_token <- paste0("_", target_tag, "_exAL_synth_DISC_uni")

  for (nm in obj_names) {
    value <- get(nm, envir = tmp, inherits = FALSE)
    assign(nm, value, envir = assign_env)
    if (!identical(source_tag, target_tag)) {
      alias_name <- sub(src_token, tgt_token, nm, fixed = TRUE)
      if (!identical(alias_name, nm)) {
        assign(alias_name, value, envir = assign_env)
      }
    }
  }
  TRUE
}

ensure_univar_bundles_loaded <- function() {
  run_univar <- isTRUE(get0("MODEL_RUN_EXDQLM_UNIVAR", ifnotfound = FALSE, inherits = TRUE))
  if (!run_univar) {
    return(FALSE)
  }
  if (length(fetch_numeric_object("seq.elbo_50_exAL_synth_DISC_uni")) > 0L &&
      !is.null(safe_obj_list("new.theta.out_50_exAL_synth_DISC_uni"))) {
    return(TRUE)
  }

  q_labels <- c("05", "20", "35", "50", "65", "80", "95")
  assign_env <- parent.frame()
  loaded_any <- FALSE
  for (q in q_labels) {
    path <- get0(paste0("UNI_VAR_", q), ifnotfound = "", inherits = TRUE)
    src <- get0(paste0("UNI_VAR_SRC_", q), ifnotfound = q, inherits = TRUE)
    loaded_any <- load_univar_bundle_with_alias_smoke(
      path,
      target_label = q,
      source_label = src,
      assign_env = assign_env
    ) || loaded_any
  }
  loaded_any
}

build_univar_location_forecast_summary <- function() {
  if (!exists("FF", inherits = TRUE) ||
      !exists("GG", inherits = TRUE) ||
      !exists("X_f", inherits = TRUE) ||
      !exists("ranges", inherits = TRUE) ||
      !exists("TT", inherits = TRUE)) {
    return(NULL)
  }

  tt <- suppressWarnings(as.integer(TT[[1L]]))
  horizon <- suppressWarnings(as.integer(ranges[[1L]]))
  if (!is.finite(tt) || !is.finite(horizon) || tt <= 0L || horizon <= 0L) {
    return(NULL)
  }

  p_core <- suppressWarnings(as.integer(get0("p", ifnotfound = 7L, inherits = TRUE)))
  if (!is.finite(p_core) || p_core <= 0L) {
    p_core <- 7L
  }

  x_future <- as.matrix(X_f)
  if (!is.matrix(x_future) || nrow(x_future) == 0L || ncol(x_future) == 0L) {
    return(NULL)
  }
  horizon <- min(horizon, nrow(x_future))
  if (horizon <= 0L) {
    return(NULL)
  }

  px <- ncol(x_future)
  state_dim <- p_core + 1L + px
  if (nrow(FF) < state_dim) {
    state_dim <- nrow(FF)
    px <- max(0L, state_dim - p_core - 1L)
  }
  if (px <= 0L) {
    return(NULL)
  }

  x_future <- x_future[seq_len(horizon), seq_len(px), drop = FALSE]
  if (dim(GG)[1] < p_core || dim(GG)[2] < p_core || dim(GG)[3] < tt) {
    return(NULL)
  }

  delta_vals <- as.numeric(get0("initial_delta", ifnotfound = NA_real_, inherits = TRUE))
  lambda2 <- if (length(delta_vals) >= 6L && is.finite(delta_vals[[6L]])) delta_vals[[6L]] else as.numeric(get0("lam2", ifnotfound = 0.8995, inherits = TRUE))
  if (!is.finite(lambda2)) {
    lambda2 <- 0.8995
  }

  gx_base <- as.matrix(bdiag(GG[1:p_core, 1:p_core, tt], lambda2, diag(px)))
  gx_arr <- array(rep(gx_base, horizon), dim = c(state_dim, state_dim, horizon))
  cov_cols <- (p_core + 2L):(p_core + 1L + px)
  gx_arr[p_core + 1L, cov_cols, ] <- t(x_future)

  ff_vec <- matrix(FF[seq_len(state_dim), 1, 1], ncol = 1)
  ff_vec[p_core + 1L] <- 1

  forecast_mu_path <- function(state_vec) {
    sm <- matrix(as.numeric(state_vec), ncol = 1)
    out <- rep(NA_real_, horizon)
    out[1L] <- sum(ff_vec * sm)
    if (horizon > 1L) {
      for (k in 2:horizon) {
        sm <- gx_arr[, , k] %*% sm
        out[k] <- sum(ff_vec * sm)
      }
    }
    out
  }

  deterministic_mu <- function(q_tag) {
    obj <- safe_obj_list(sprintf("new.theta.out_%s_exAL_synth_DISC_uni", q_tag))
    if (is.null(obj) || is.null(obj$sm) || !is.matrix(obj$sm) || nrow(obj$sm) < state_dim || ncol(obj$sm) < tt) {
      return(numeric(0))
    }
    forecast_mu_path(obj$sm[seq_len(state_dim), tt])
  }

  mu_50 <- deterministic_mu("50")
  if (length(mu_50) == 0L) {
    return(NULL)
  }
  mu_05 <- deterministic_mu("5")
  if (length(mu_05) == 0L) mu_05 <- mu_50
  mu_95 <- deterministic_mu("95")
  if (length(mu_95) == 0L) mu_95 <- mu_50

  q50_samples <- NULL
  samp_50 <- get0("samp.theta_50_exAL_synth_DISC_uni", ifnotfound = NULL, inherits = TRUE)
  if (!is.null(samp_50) && is.array(samp_50) && length(dim(samp_50)) == 3L &&
      dim(samp_50)[1] >= state_dim && dim(samp_50)[2] >= tt && dim(samp_50)[3] >= 1L) {
    n_keep <- min(400L, as.integer(dim(samp_50)[3]))
    q50_samples <- matrix(NA_real_, nrow = n_keep, ncol = horizon)
    for (i in seq_len(n_keep)) {
      q50_samples[i, ] <- forecast_mu_path(samp_50[seq_len(state_dim), tt, i])
    }
  }

  loc_q05 <- rbind(mu_05, mu_05, mu_05)
  loc_q50 <- rbind(mu_50, mu_50, mu_50)
  if (!is.null(q50_samples)) {
    loc_q50 <- col_quantiles(q50_samples, probs = c(0.025, 0.5, 0.975))
  }
  loc_q95 <- rbind(mu_95, mu_95, mu_95)

  list(
    horizon = horizon,
    loc_q05 = loc_q05,
    loc_q50 = loc_q50,
    loc_q95 = loc_q95,
    q50_samples = q50_samples
  )
}

profile_section("figures_smoke_fast.univar_load_inputs", {
  ensure_univar_bundles_loaded()
})

profile_section("figures_smoke_fast.elbo_traces", {
  out_file <- file.path(OUT_DIR, "All_ELBOS_DISC.png")
  png(out_file, width = 2400, height = 1200, res = 300)
  on.exit(dev.off(), add = TRUE)

  traces <- list(
    NDLM = fetch_numeric_object("seq.elbo_50_NDLM_synth_DISC"),
    exAL_multiv_50 = fetch_numeric_object("seq.elbo_50_exAL_synth_DISC"),
    exAL_multiv_95 = fetch_numeric_object("seq.elbo_95_exAL_synth_DISC"),
    exAL_univar_50 = fetch_numeric_object("seq.elbo_50_exAL_synth_DISC_uni")
  )
  show_names <- names(traces)[vapply(traces, function(x) length(x) > 0L, logical(1))]
  if (length(show_names) == 0L) {
    show_names <- names(traces)
  }
  n <- length(show_names)
  ncol <- min(2L, n)
  nrow <- ceiling(n / ncol)
  par(mfrow = c(nrow, ncol), mar = c(3, 3, 2, 1))

  for (nm in show_names) {
    vals <- traces[[nm]]
    if (length(vals) > 0L) {
      vals[1] <- NA_real_
    }
    plot_trace(vals, nm, "ELBO")
  }
  mtext("Smoke Figure Set", side = 3, outer = TRUE, line = -2, cex = 0.9)
})

profile_section("figures_smoke_fast.observed_series", {
  out_file <- file.path(OUT_DIR, "SMOKE_OBSERVED_SERIES_DISC.png")
  png(out_file, width = 2400, height = 1200, res = 300)
  on.exit(dev.off(), add = TRUE)

  if (exists("Y", inherits = TRUE) && is.matrix(Y) && nrow(Y) >= 1L) {
    yy <- as.numeric(Y[1, ])
    idx <- which(is.finite(yy))
    if (length(idx) > 0L) {
      plot(idx, yy[idx], type = "l", col = "black", lwd = 1.5,
           xlab = "Time index", ylab = "log-flow", main = "Observed series (row 1)")
    } else {
      plot.new()
      title(main = "Observed series unavailable (no finite values)")
    }
  } else {
    plot.new()
    title(main = "Observed series unavailable (Y missing)")
  }
})

profile_section("figures_smoke_fast.univar_traces", {
  run_univar <- isTRUE(get0("MODEL_RUN_EXDQLM_UNIVAR", ifnotfound = FALSE, inherits = TRUE))
  has_univar_objs <- length(fetch_numeric_object("seq.elbo_50_exAL_synth_DISC_uni")) > 0L
  if (!(run_univar || has_univar_objs)) {
    return(invisible(NULL))
  }

  q_tags <- c("5", "20", "35", "50", "65", "80", "95")

  collect_metric <- function(metric_name) {
    out <- list()
    for (q in q_tags) {
      vals <- fetch_first_numeric(c(
        sprintf("seq.%s_%s_exAL_synth_DISC_uni", metric_name, q),
        sprintf("samp.%s_%s_exAL_synth_DISC_uni", metric_name, q)
      ))
      if (length(vals) > 0L) {
        out[[q]] <- vals
      }
    }
    out
  }

  draw_metric_grid <- function(metric_key, ylab_txt, file_name) {
    traces <- collect_metric(metric_key)
    if (length(traces) == 0L) {
      return(invisible(NULL))
    }
    out_file <- file.path(OUT_DIR, file_name)
    png(out_file, width = 2800, height = 1600, res = 300)
    on.exit(dev.off(), add = TRUE)
    n <- length(traces)
    ncol <- min(3L, n)
    nrow <- ceiling(n / ncol)
    par(mfrow = c(nrow, ncol), mar = c(3, 3, 2, 1))
    for (nm in names(traces)) {
      plot_trace(traces[[nm]], paste0(metric_key, " q=", nm), ylab_txt)
    }
    invisible(NULL)
  }

  draw_metric_grid("elbo", "ELBO", "univar_elbo_traces.png")
  draw_metric_grid("sigma", "sigma", "univar_sigma_traces.png")
  draw_metric_grid("gamma", "gamma", "univar_gamma_traces.png")
})

profile_section("figures_smoke_fast.univar_fit_mu_vs_obs", {
  run_univar <- isTRUE(get0("MODEL_RUN_EXDQLM_UNIVAR", ifnotfound = FALSE, inherits = TRUE))
  if (!run_univar || !exists("Y", inherits = TRUE) || !is.matrix(Y) || nrow(Y) < 1L) {
    return(invisible(NULL))
  }

  q_tags <- c("5", "20", "35", "50", "65", "80", "95")
  q_cols <- c(
    "5" = "#b2182b",
    "20" = "#d6604d",
    "35" = "#f4a582",
    "50" = "#1b7837",
    "65" = "#92c5de",
    "80" = "#4393c3",
    "95" = "#2166ac"
  )

  exps_by_q <- list()
  for (q in q_tags) {
    obj <- safe_obj_list(sprintf("new.theta.out_%s_exAL_synth_DISC_uni", q))
    if (is.null(obj) || is.null(obj$exps) || !is.matrix(obj$exps) || nrow(obj$exps) < 1L) {
      next
    }
    exps_by_q[[q]] <- as.numeric(obj$exps[1, ])
  }
  if (length(exps_by_q) == 0L) {
    return(invisible(NULL))
  }

  obs <- as.numeric(Y[1, ])
  fit_len <- min(length(obs), max(vapply(exps_by_q, length, integer(1))))
  if (!is.finite(fit_len) || fit_len <= 0L) {
    return(invisible(NULL))
  }
  idx <- seq_len(fit_len)

  out_file <- file.path(OUT_DIR, "univar_fit_mu_vs_observed_loglog.png")
  png(out_file, width = 2800, height = 1400, res = 300)
  on.exit(dev.off(), add = TRUE)
  y_min <- min(obs[idx], unlist(lapply(exps_by_q, function(v) v[idx])), na.rm = TRUE)
  y_max <- max(obs[idx], unlist(lapply(exps_by_q, function(v) v[idx])), na.rm = TRUE)
  plot(idx, obs[idx], type = "p", pch = 16, cex = 0.35, col = "gray20",
       xlab = "Time index", ylab = "log(log(flow + 1))",
       main = "Univariate exDQLM expected location vs observed (in-sample)",
       ylim = c(y_min, y_max))
  for (q in names(exps_by_q)) {
    lines(idx, exps_by_q[[q]][idx], col = q_cols[[q]], lwd = if (q == "50") 2 else 1.3)
  }
  legend("topright",
         legend = c("Observed", paste0("mu_t q=", names(exps_by_q))),
         col = c("gray20", unname(q_cols[names(exps_by_q)])),
         lwd = c(NA, rep(2, length(exps_by_q))),
         pch = c(16, rep(NA, length(exps_by_q))),
         pt.cex = 0.7,
         bty = "n")

  recent_n <- min(900L, fit_len)
  idx_recent <- seq.int(fit_len - recent_n + 1L, fit_len)
  out_file_recent <- file.path(OUT_DIR, "univar_fit_mu_vs_observed_recent_loglog.png")
  png(out_file_recent, width = 2800, height = 1400, res = 300)
  on.exit(dev.off(), add = TRUE)
  y_min_r <- min(obs[idx_recent], unlist(lapply(exps_by_q, function(v) v[idx_recent])), na.rm = TRUE)
  y_max_r <- max(obs[idx_recent], unlist(lapply(exps_by_q, function(v) v[idx_recent])), na.rm = TRUE)
  plot(idx_recent, obs[idx_recent], type = "p", pch = 16, cex = 0.55, col = "gray20",
       xlab = "Time index", ylab = "log(log(flow + 1))",
       main = sprintf("Univariate exDQLM expected location vs observed (recent %d points)", recent_n),
       ylim = c(y_min_r, y_max_r))
  for (q in names(exps_by_q)) {
    lines(idx_recent, exps_by_q[[q]][idx_recent], col = q_cols[[q]], lwd = if (q == "50") 2.2 else 1.5)
  }
  legend("topright",
         legend = c("Observed", paste0("mu_t q=", names(exps_by_q))),
         col = c("gray20", unname(q_cols[names(exps_by_q)])),
         lwd = c(NA, rep(2, length(exps_by_q))),
         pch = c(16, rep(NA, length(exps_by_q))),
         pt.cex = 0.7,
         bty = "n")
})

profile_section("figures_smoke_fast.univar_forecast_window", {
  run_univar <- isTRUE(get0("MODEL_RUN_EXDQLM_UNIVAR", ifnotfound = FALSE, inherits = TRUE))
  if (!run_univar) {
    return(invisible(NULL))
  }

  loc_q05 <- NULL
  loc_q50 <- NULL
  loc_q95 <- NULL
  pred_q50 <- NULL
  horizon <- NA_integer_

  if (exists("xb_forecast", inherits = TRUE) && !is.null(dim(xb_forecast)) && length(dim(xb_forecast)) == 3L) {
    horizon <- dim(xb_forecast)[3]
    loc_q05 <- col_quantiles(xb_forecast[1, , ], probs = c(0.025, 0.5, 0.975))
    loc_q50 <- col_quantiles(xb_forecast[4, , ], probs = c(0.025, 0.5, 0.975))
    loc_q95 <- col_quantiles(xb_forecast[7, , ], probs = c(0.025, 0.5, 0.975))

    if (exists("y_forecast", inherits = TRUE) && is.array(y_forecast) && length(dim(y_forecast)) == 3L && dim(y_forecast)[1] >= 4L) {
      pred_q50 <- col_quantiles(y_forecast[4, , ], probs = c(0.025, 0.5, 0.975))
    }
  } else {
    fallback_fc <- build_univar_location_forecast_summary()
    if (!is.null(fallback_fc)) {
      horizon <- fallback_fc$horizon
      loc_q05 <- fallback_fc$loc_q05
      loc_q50 <- fallback_fc$loc_q50
      loc_q95 <- fallback_fc$loc_q95
      if (!is.null(fallback_fc$q50_samples)) {
        pred_q50 <- col_quantiles(fallback_fc$q50_samples, probs = c(0.025, 0.5, 0.975))
      }
    }
  }

  if (!is.finite(horizon) || horizon <= 0L || is.null(loc_q50)) {
    return(invisible(NULL))
  }

  x_idx <- seq_len(horizon)
  truth <- resolve_future_truth(horizon)

  out_file <- file.path(OUT_DIR, "univar_forecast_window_mu_vs_future_usgs.png")
  png(out_file, width = 2800, height = 1400, res = 300)
  on.exit(dev.off(), add = TRUE)
  y_min <- min(c(loc_q05, loc_q50, loc_q95, truth), na.rm = TRUE)
  y_max <- max(c(loc_q05, loc_q50, loc_q95, truth), na.rm = TRUE)
  plot(x_idx, loc_q50[2, ], type = "l", lwd = 2.2, col = "#1b7837",
       xlab = "Forecast day", ylab = "log(log(flow + 1))",
       main = "Univariate exDQLM forecast-window location vs future USGS",
       ylim = c(y_min, y_max))
  lines(x_idx, loc_q50[1, ], lty = 2, lwd = 1.2, col = "#1b7837")
  lines(x_idx, loc_q50[3, ], lty = 2, lwd = 1.2, col = "#1b7837")
  lines(x_idx, loc_q05[2, ], lwd = 1.5, col = "#b2182b")
  lines(x_idx, loc_q95[2, ], lwd = 1.5, col = "#2166ac")
  points(x_idx, truth, pch = 16, cex = 0.8, col = "black")
  lines(x_idx, truth, lwd = 1.1, col = "black")
  legend("topleft",
         legend = c("mu_t q=50 (median)", "mu_t q=50 95% interval", "mu_t q=05", "mu_t q=95", "Future USGS (withheld)"),
         col = c("#1b7837", "#1b7837", "#b2182b", "#2166ac", "black"),
         lty = c(1, 2, 1, 1, 1),
         lwd = c(2.2, 1.2, 1.5, 1.5, 1.1),
         pch = c(NA, NA, NA, NA, 16),
         bty = "n")

  if (!is.null(pred_q50) && ncol(pred_q50) == horizon) {
    out_file2 <- file.path(OUT_DIR, "univar_forecast_window_predictive_q50_vs_future_usgs.png")
    png(out_file2, width = 2800, height = 1400, res = 300)
    on.exit(dev.off(), add = TRUE)
    y_min2 <- min(c(pred_q50, truth), na.rm = TRUE)
    y_max2 <- max(c(pred_q50, truth), na.rm = TRUE)
    plot(x_idx, pred_q50[2, ], type = "l", lwd = 2.1, col = "#1b7837",
         xlab = "Forecast day", ylab = "log(log(flow + 1))",
         main = "Univariate exDQLM predictive q=50 vs future USGS",
         ylim = c(y_min2, y_max2))
    lines(x_idx, pred_q50[1, ], lty = 2, lwd = 1.2, col = "#1b7837")
    lines(x_idx, pred_q50[3, ], lty = 2, lwd = 1.2, col = "#1b7837")
    points(x_idx, truth, pch = 16, cex = 0.8, col = "black")
    lines(x_idx, truth, lwd = 1.1, col = "black")
    legend("topleft",
           legend = c("Predictive q=50 median", "Predictive q=50 95% interval", "Future USGS (withheld)"),
           col = c("#1b7837", "#1b7837", "black"),
           lty = c(1, 2, 1),
           lwd = c(2.1, 1.2, 1.1),
           pch = c(NA, NA, 16),
           bty = "n")
  }

  if (exists("ensembles", inherits = TRUE) && is.list(ensembles) && length(ensembles) >= 2L) {
    glofas <- as.matrix(ensembles[[1]])
    nws <- as.matrix(ensembles[[2]])
    glofas_mean <- pad_to_horizon(rowMeans(glofas, na.rm = TRUE), horizon)
    nws_mean <- pad_to_horizon(rowMeans(nws, na.rm = TRUE), horizon)

    out_file3 <- file.path(OUT_DIR, "univar_forecast_window_univar_vs_ensembles.png")
    png(out_file3, width = 2800, height = 1400, res = 300)
    on.exit(dev.off(), add = TRUE)
    y_min3 <- min(c(loc_q50, glofas_mean, nws_mean, truth), na.rm = TRUE)
    y_max3 <- max(c(loc_q50, glofas_mean, nws_mean, truth), na.rm = TRUE)
    plot(x_idx, loc_q50[2, ], type = "l", lwd = 2.4, col = "#1b7837",
         xlab = "Forecast day", ylab = "log(log(flow + 1))",
         main = "Forecast window: univariate exDQLM vs ensemble means",
         ylim = c(y_min3, y_max3))
    lines(x_idx, loc_q50[1, ], lty = 2, lwd = 1.1, col = "#1b7837")
    lines(x_idx, loc_q50[3, ], lty = 2, lwd = 1.1, col = "#1b7837")
    lines(x_idx, glofas_mean, col = "#2166ac", lwd = 1.7)
    lines(x_idx, nws_mean, col = "#762a83", lwd = 1.7)
    points(x_idx, truth, pch = 16, cex = 0.8, col = "black")
    lines(x_idx, truth, lwd = 1.1, col = "black")
    legend("topleft",
           legend = c("Univar mu_t q=50 median", "Univar mu_t q=50 95% interval", "GLOFAS ensemble mean", "NWS ensemble mean", "Future USGS (withheld)"),
           col = c("#1b7837", "#1b7837", "#2166ac", "#762a83", "black"),
           lty = c(1, 2, 1, 1, 1),
           lwd = c(2.4, 1.1, 1.7, 1.7, 1.1),
           pch = c(NA, NA, NA, NA, 16),
           bty = "n")

    out_file4 <- file.path(OUT_DIR, "univar_forecast_window_ensemble_members.png")
    png(out_file4, width = 2800, height = 1400, res = 300)
    on.exit(dev.off(), add = TRUE)
    y_min4 <- min(c(glofas, nws, loc_q50[2, ], truth), na.rm = TRUE)
    y_max4 <- max(c(glofas, nws, loc_q50[2, ], truth), na.rm = TRUE)
    plot(x_idx, loc_q50[2, ], type = "l", lwd = 2.6, col = "#1b7837",
         xlab = "Forecast day", ylab = "log(log(flow + 1))",
         main = "Forecast window: ensemble members + univariate median + future USGS",
         ylim = c(y_min4, y_max4))
    if (ncol(glofas) > 0L) {
      matlines(seq_len(nrow(glofas)), glofas, lty = 1, lwd = 0.5, col = adjustcolor("#2166ac", alpha.f = 0.28))
    }
    if (ncol(nws) > 0L) {
      matlines(seq_len(nrow(nws)), nws, lty = 1, lwd = 0.5, col = adjustcolor("#762a83", alpha.f = 0.28))
    }
    lines(x_idx, loc_q50[2, ], lwd = 2.6, col = "#1b7837")
    points(x_idx, truth, pch = 16, cex = 0.85, col = "black")
    lines(x_idx, truth, lwd = 1.1, col = "black")
    legend("topleft",
           legend = c("Univar mu_t q=50 median", "GLOFAS members", "NWS members", "Future USGS (withheld)"),
           col = c("#1b7837", "#2166ac", "#762a83", "black"),
           lty = c(1, 1, 1, 1),
           lwd = c(2.6, 1.0, 1.0, 1.1),
           pch = c(NA, NA, NA, 16),
           bty = "n")
  }
})
