# unified/ndlm_post_diagnostics.R

unified_ndlm_diag_num <- function(x) {
  out <- suppressWarnings(as.numeric(x))
  if (length(out) == 0L) return(NA_real_)
  out[[1L]]
}

unified_ndlm_diag_int <- function(x) {
  out <- suppressWarnings(as.integer(x))
  if (length(out) == 0L) return(NA_integer_)
  out[[1L]]
}

unified_ndlm_diag_read_csv <- function(path, label) {
  if (is.null(path) || !nzchar(path)) {
    stop(sprintf("[NDLM_DIAG_INPUT_PATH] Missing %s CSV path.", label), call. = FALSE)
  }
  if (!file.exists(path)) {
    stop(sprintf("[NDLM_DIAG_INPUT_PATH] %s CSV does not exist: %s", label, path), call. = FALSE)
  }
  out <- tryCatch(
    utils::read.csv(path, stringsAsFactors = FALSE, check.names = FALSE),
    error = function(e) e
  )
  if (inherits(out, "error") || !is.data.frame(out) || nrow(out) < 1L) {
    stop(sprintf("[NDLM_DIAG_INPUT_READ] Unable to read non-empty %s CSV: %s", label, path), call. = FALSE)
  }
  out
}

unified_ndlm_diag_extract_date_column <- function(df) {
  cand <- c("Date", "date", "target_date", "timestamp", "Timestamp")
  for (nm in cand) {
    if (!nm %in% names(df)) next
    vals <- suppressWarnings(as.Date(df[[nm]]))
    if (length(vals) == nrow(df) && sum(is.na(vals)) < length(vals)) {
      return(vals)
    }
  }
  as.Date(rep(NA_character_, nrow(df)))
}

unified_ndlm_diag_pick_numeric_column <- function(df, preferred = character(0)) {
  if (length(preferred) > 0L) {
    for (nm in preferred) {
      if (nm %in% names(df) && is.numeric(df[[nm]])) {
        return(as.numeric(df[[nm]]))
      }
    }
  }
  num_cols <- names(df)[vapply(df, is.numeric, logical(1))]
  if (length(num_cols) == 0L) return(numeric(0))
  as.numeric(df[[num_cols[[1L]]]])
}

unified_ndlm_diag_parse_progress_log <- function(log_path) {
  cols <- c(
    "iter", "elbo", "crit_elbo", "sigma_exp", "gamma_exp", "state_norm_sq",
    "w_hist", "w_fore", "df_t", "df_s1", "df_s2", "df_s67", "df_discrep", "lambda"
  )
  empty <- stats::setNames(data.frame(matrix(ncol = length(cols), nrow = 0L)), cols)
  if (is.null(log_path) || !nzchar(log_path) || !file.exists(log_path)) {
    return(empty)
  }

  lines <- readLines(log_path, warn = FALSE)
  rows <- vector("list", length(lines))
  row_i <- 0L
  for (ln in lines) {
    if (!grepl("\\[gamsig_progress\\]", ln)) next

    extract_token <- function(key) {
      pat <- sprintf(".*%s=([^ ]+).*", key)
      if (!grepl(sprintf("%s=", key), ln, fixed = TRUE)) return(NA_character_)
      sub(pat, "\\1", ln)
    }

    row_i <- row_i + 1L
    rows[[row_i]] <- list(
      iter = unified_ndlm_diag_int(extract_token("iter")),
      elbo = unified_ndlm_diag_num(extract_token("elbo")),
      crit_elbo = unified_ndlm_diag_num(extract_token("crit_elbo")),
      sigma_exp = unified_ndlm_diag_num(extract_token("sigma_exp")),
      gamma_exp = unified_ndlm_diag_num(extract_token("gamma_exp")),
      state_norm_sq = unified_ndlm_diag_num(extract_token("state_norm_sq")),
      w_hist = unified_ndlm_diag_num(extract_token("w_hist")),
      w_fore = unified_ndlm_diag_num(extract_token("w_fore")),
      df_t = unified_ndlm_diag_num(extract_token("df_t")),
      df_s1 = unified_ndlm_diag_num(extract_token("df_s1")),
      df_s2 = unified_ndlm_diag_num(extract_token("df_s2")),
      df_s67 = unified_ndlm_diag_num(extract_token("df_s67")),
      df_discrep = unified_ndlm_diag_num(extract_token("df_discrep")),
      lambda = unified_ndlm_diag_num(extract_token("lambda"))
    )
  }

  if (row_i == 0L) {
    return(empty)
  }

  rows <- rows[seq_len(row_i)]
  out <- as.data.frame(do.call(rbind, lapply(rows, as.data.frame)), stringsAsFactors = FALSE)
  out$iter <- as.integer(out$iter)
  out
}

unified_ndlm_diag_shape_row <- function(object_name, value) {
  obj_type <- paste(class(value), collapse = "|")
  obj_rank <- if (is.null(dim(value))) {
    if (is.list(value)) NA_integer_ else 1L
  } else {
    length(dim(value))
  }
  dims_txt <- if (is.list(value)) {
    if (length(value) == 0L) {
      ""
    } else {
      paste(vapply(value, function(x) {
        d <- dim(x)
        if (is.null(d)) {
          as.character(length(x))
        } else {
          paste(as.integer(d), collapse = "x")
        }
      }, character(1)), collapse = ";")
    }
  } else {
    d <- dim(value)
    if (is.null(d)) as.character(length(value)) else paste(as.integer(d), collapse = "x")
  }

  data.frame(
    object = object_name,
    type = obj_type,
    rank = obj_rank,
    dims = dims_txt,
    stringsAsFactors = FALSE
  )
}

unified_ndlm_diag_date_span <- function(dates) {
  if (length(dates) == 0L) return(c(t_min = "", t_max = ""))
  ok <- !is.na(dates)
  if (!any(ok)) return(c(t_min = "", t_max = ""))
  c(t_min = as.character(min(dates[ok])), t_max = as.character(max(dates[ok])))
}

unified_ndlm_diag_named_int <- function(x, name, fallback = NA_integer_) {
  if (is.null(x)) return(as.integer(fallback))
  if (!is.null(names(x)) && (name %in% names(x))) {
    return(unified_ndlm_diag_int(x[[name]]))
  }
  unified_ndlm_diag_int(x[[1L]])
}

unified_ndlm_diag_cov_row <- function(object_name, cov_arr) {
  dims <- dim(cov_arr)
  if (is.null(dims) || length(dims) != 3L || dims[1] != dims[2]) {
    return(data.frame(
      object = object_name,
      n_slices = NA_integer_,
      matrix_dim = NA_integer_,
      nonfinite_slices = NA_integer_,
      asymmetry_max = NA_real_,
      min_diag_min = NA_real_,
      min_eig_min = NA_real_,
      min_eig_p01 = NA_real_,
      base_chol_fail_slices = NA_integer_,
      base_chol_fail_rate = NA_real_,
      stringsAsFactors = FALSE
    ))
  }

  n_slices <- as.integer(dims[3])
  min_eigs <- rep(NA_real_, n_slices)
  min_diags <- rep(NA_real_, n_slices)
  asym <- rep(NA_real_, n_slices)
  nonfinite <- rep(FALSE, n_slices)
  base_fail <- rep(FALSE, n_slices)
  for (k in seq_len(n_slices)) {
    S <- as.matrix(cov_arr[, , k, drop = TRUE])
    if (!all(is.finite(S))) {
      nonfinite[k] <- TRUE
      next
    }
    S <- (S + t(S)) / 2
    asym[k] <- max(abs(S - t(S)))
    min_diags[k] <- min(diag(S))
    min_eigs[k] <- min(eigen(S, symmetric = TRUE, only.values = TRUE)$values)
    base_fail[k] <- is.null(tryCatch(chol(S + diag(1e-8, nrow(S))), error = function(e) NULL))
  }

  data.frame(
    object = object_name,
    n_slices = n_slices,
    matrix_dim = as.integer(dims[1]),
    nonfinite_slices = as.integer(sum(nonfinite)),
    asymmetry_max = if (all(is.na(asym))) NA_real_ else max(asym, na.rm = TRUE),
    min_diag_min = if (all(is.na(min_diags))) NA_real_ else min(min_diags, na.rm = TRUE),
    min_eig_min = if (all(is.na(min_eigs))) NA_real_ else min(min_eigs, na.rm = TRUE),
    min_eig_p01 = if (all(is.na(min_eigs))) NA_real_ else as.numeric(stats::quantile(min_eigs, probs = 0.01, na.rm = TRUE, names = FALSE)),
    base_chol_fail_slices = as.integer(sum(base_fail, na.rm = TRUE)),
    base_chol_fail_rate = mean(base_fail, na.rm = TRUE),
    stringsAsFactors = FALSE
  )
}

unified_ndlm_diag_write_trace_plot <- function(df, x_col, y_col, path, main, ylab) {
  if (!is.data.frame(df) || !(x_col %in% names(df)) || !(y_col %in% names(df))) return(FALSE)
  x <- suppressWarnings(as.numeric(df[[x_col]]))
  y <- suppressWarnings(as.numeric(df[[y_col]]))
  ok <- is.finite(x) & is.finite(y)
  if (sum(ok) < 2L) return(FALSE)

  grDevices::png(filename = path, width = 1400, height = 800, res = 140)
  on.exit(grDevices::dev.off(), add = TRUE)
  graphics::par(mar = c(4.2, 4.6, 3.4, 1.2))
  graphics::plot(
    x[ok], y[ok],
    type = "l",
    col = "#004C6D",
    lwd = 2.4,
    xlab = "Iteration",
    ylab = ylab,
    main = main
  )
  graphics::grid(col = "#D6DCE5", lty = "dotted")
  TRUE
}

unified_ndlm_diag_safe_filename <- function(x) {
  x <- tolower(as.character(x))
  x <- gsub("[^a-z0-9]+", "_", x)
  x <- gsub("^_+|_+$", "", x)
  if (!nzchar(x)) x <- "scale"
  x
}

unified_ndlm_diag_extract_sigma_long <- function(iter_trace, env) {
  # Prefer explicit sigma sequence object if present; fallback to parsed progress log.
  sigma_obj <- if (exists("seq.sigma_50_NDLM_synth_DISC", envir = env, inherits = FALSE)) {
    get("seq.sigma_50_NDLM_synth_DISC", envir = env, inherits = FALSE)
  } else {
    NULL
  }

  iter_n <- if (is.data.frame(iter_trace) && nrow(iter_trace) > 0L && "iter" %in% names(iter_trace)) {
    max(suppressWarnings(as.integer(iter_trace$iter)), na.rm = TRUE)
  } else {
    NA_integer_
  }
  if (!is.finite(iter_n) || iter_n < 1L) iter_n <- NA_integer_

  rows <- list()

  if (!is.null(sigma_obj) && is.numeric(sigma_obj)) {
    if (is.null(dim(sigma_obj))) {
      v <- as.numeric(sigma_obj)
      if (length(v) > 0L) {
        rows[[length(rows) + 1L]] <- data.frame(
          iter = seq_along(v),
          scale_key = "scale_01",
          scale_label = "scale_01",
          sigma = v,
          stringsAsFactors = FALSE
        )
      }
    } else if (length(dim(sigma_obj)) == 2L) {
      mat <- as.matrix(sigma_obj)
      nr <- nrow(mat)
      nc <- ncol(mat)
      if (is.finite(iter_n)) {
        if (nr == iter_n) {
          # as-is
        } else if (nc == iter_n) {
          mat <- t(mat)
          nr <- nrow(mat)
          nc <- ncol(mat)
        } else if (nc > nr) {
          mat <- t(mat)
          nr <- nrow(mat)
          nc <- ncol(mat)
        }
      } else if (nc > nr) {
        mat <- t(mat)
        nr <- nrow(mat)
        nc <- ncol(mat)
      }
      scale_names <- colnames(mat)
      if (is.null(scale_names) || length(scale_names) != nc) {
        scale_names <- sprintf("scale_%02d", seq_len(nc))
      } else {
        scale_names <- ifelse(nzchar(scale_names), scale_names, sprintf("scale_%02d", seq_len(nc)))
      }
      for (j in seq_len(nc)) {
        rows[[length(rows) + 1L]] <- data.frame(
          iter = seq_len(nr),
          scale_key = sprintf("scale_%02d", j),
          scale_label = as.character(scale_names[[j]]),
          sigma = as.numeric(mat[, j]),
          stringsAsFactors = FALSE
        )
      }
    }
  }

  if (length(rows) == 0L && is.data.frame(iter_trace) && nrow(iter_trace) > 0L && "sigma_exp" %in% names(iter_trace)) {
    rows[[1L]] <- data.frame(
      iter = suppressWarnings(as.integer(iter_trace$iter)),
      scale_key = "scale_01",
      scale_label = "sigma_exp",
      sigma = suppressWarnings(as.numeric(iter_trace$sigma_exp)),
      stringsAsFactors = FALSE
    )
  }

  if (length(rows) == 0L) {
    return(data.frame(iter = integer(0), scale_key = character(0), scale_label = character(0), sigma = numeric(0), stringsAsFactors = FALSE))
  }

  out <- do.call(rbind, rows)
  out <- out[is.finite(out$iter) & is.finite(out$sigma), , drop = FALSE]
  out$iter <- as.integer(out$iter)
  rownames(out) <- NULL
  out
}

unified_ndlm_diag_write_sigma_traces <- function(sigma_long, output_dir, primary_path) {
  if (!is.data.frame(sigma_long) || nrow(sigma_long) < 2L) {
    return(character(0))
  }
  paths <- character(0)
  scales <- unique(as.character(sigma_long$scale_key))
  scales <- scales[nzchar(scales)]
  if (length(scales) < 1L) return(paths)

  for (k in seq_along(scales)) {
    sk <- scales[[k]]
    sub <- sigma_long[sigma_long$scale_key == sk, , drop = FALSE]
    lbl <- if (nrow(sub) > 0L) as.character(sub$scale_label[[1L]]) else sk
    if (!nzchar(lbl)) lbl <- sk
    out_path <- if (k == 1L) {
      primary_path
    } else {
      file.path(output_dir, sprintf("ndlm_sigma_trace_%s.png", unified_ndlm_diag_safe_filename(sk)))
    }
    ok <- unified_ndlm_diag_write_trace_plot(
      df = sub,
      x_col = "iter",
      y_col = "sigma",
      path = out_path,
      main = sprintf("NDLM Sigma Trace (%s)", lbl),
      ylab = "Sigma"
    )
    if (isTRUE(ok)) paths <- c(paths, out_path)
  }
  paths
}

unified_ndlm_diag_write_fit_plot <- function(
  dates,
  obs,
  fit,
  path,
  title,
  x_as_date = TRUE
) {
  obs <- suppressWarnings(as.numeric(obs))
  fit <- suppressWarnings(as.numeric(fit))
  n <- min(length(obs), length(fit), length(dates))
  if (n < 2L) return(FALSE)
  obs <- obs[seq_len(n)]
  fit <- fit[seq_len(n)]
  d <- dates[seq_len(n)]
  ok <- is.finite(obs) & is.finite(fit)
  if (x_as_date) {
    ok <- ok & !is.na(d)
    x <- d
    xlab <- "Date"
  } else {
    x <- seq_len(n)
    xlab <- "Index"
  }
  if (sum(ok) < 2L) return(FALSE)

  y_rng <- range(c(obs[ok], fit[ok]), finite = TRUE)
  if (!all(is.finite(y_rng))) return(FALSE)
  pad <- 0.05 * max(diff(y_rng), 1e-8)
  y_lim <- c(y_rng[1] - pad, y_rng[2] + pad)

  grDevices::png(filename = path, width = 1600, height = 900, res = 140)
  on.exit(grDevices::dev.off(), add = TRUE)
  graphics::par(mar = c(4.2, 4.8, 3.4, 1.4))
  graphics::plot(
    x[ok], obs[ok],
    type = "o",
    pch = 16,
    cex = 0.35,
    lwd = 1.2,
    col = "#171A1F",
    xlab = xlab,
    ylab = "log1p(cms)",
    ylim = y_lim,
    main = title
  )
  graphics::lines(x[ok], fit[ok], col = "#D1495B", lwd = 2.2)
  graphics::grid(col = "#D6DCE5", lty = "dotted")
  graphics::legend(
    "topright",
    legend = c("Observed (USGS)", "NDLM dynamic location fit"),
    col = c("#171A1F", "#D1495B"),
    lwd = c(1.2, 2.2),
    pch = c(16, NA),
    pt.cex = c(0.6, NA),
    bty = "n"
  )
  TRUE
}

unified_ndlm_diag_write_fit_modes_plot <- function(df, path, title) {
  req <- c("date", "observed", "one_step_predicted", "filtered_fit", "smoothed_fit")
  if (!is.data.frame(df) || !all(req %in% names(df)) || nrow(df) < 2L) return(FALSE)

  obs <- suppressWarnings(as.numeric(df$observed))
  one_step <- suppressWarnings(as.numeric(df$one_step_predicted))
  filt <- suppressWarnings(as.numeric(df$filtered_fit))
  smooth <- suppressWarnings(as.numeric(df$smoothed_fit))
  d <- suppressWarnings(as.Date(df$date))
  use_date <- any(!is.na(d))
  x <- if (use_date) d else seq_len(nrow(df))
  ok_obs <- is.finite(obs) & if (use_date) !is.na(x) else TRUE
  if (sum(ok_obs) < 2L) return(FALSE)

  y_stack <- c(obs[ok_obs], one_step[is.finite(one_step)], filt[is.finite(filt)], smooth[is.finite(smooth)])
  y_rng <- range(y_stack, finite = TRUE)
  if (!all(is.finite(y_rng))) return(FALSE)
  pad <- 0.05 * max(diff(y_rng), 1e-8)
  y_lim <- c(y_rng[1] - pad, y_rng[2] + pad)

  grDevices::png(filename = path, width = 1800, height = 1000, res = 140)
  on.exit(grDevices::dev.off(), add = TRUE)
  graphics::par(mar = c(4.2, 4.8, 3.4, 1.4))
  graphics::plot(
    x[ok_obs], obs[ok_obs],
    type = "o",
    pch = 16,
    cex = 0.32,
    lwd = 1.0,
    col = "#171A1F",
    xlab = if (use_date) "Date" else "Index",
    ylab = "log1p(cms)",
    ylim = y_lim,
    main = title
  )
  ok_one <- is.finite(one_step) & if (use_date) !is.na(x) else TRUE
  if (sum(ok_one) >= 2L) graphics::lines(x[ok_one], one_step[ok_one], col = "#1E88E5", lwd = 1.8, lty = 2)
  ok_filt <- is.finite(filt) & if (use_date) !is.na(x) else TRUE
  if (sum(ok_filt) >= 2L) graphics::lines(x[ok_filt], filt[ok_filt], col = "#00897B", lwd = 1.8, lty = 3)
  ok_smooth <- is.finite(smooth) & if (use_date) !is.na(x) else TRUE
  if (sum(ok_smooth) >= 2L) graphics::lines(x[ok_smooth], smooth[ok_smooth], col = "#D1495B", lwd = 2.2, lty = 1)
  graphics::grid(col = "#D6DCE5", lty = "dotted")
  graphics::legend(
    "topright",
    legend = c("Observed", "One-step predicted", "Filtered fit", "Smoothed fit"),
    col = c("#171A1F", "#1E88E5", "#00897B", "#D1495B"),
    lwd = c(1.0, 1.8, 1.8, 2.2),
    lty = c(1, 2, 3, 1),
    pch = c(16, NA, NA, NA),
    pt.cex = c(0.55, NA, NA, NA),
    bty = "n"
  )
  TRUE
}

unified_ndlm_diag_component_label <- function(component_id) {
  component_id <- suppressWarnings(as.integer(component_id[[1L]]))
  if (!is.finite(component_id) || component_id < 1L) {
    return("theta_unknown")
  }
  if (component_id <= 7L) {
    return(sprintf("hist_%02d (theta_%02d)", component_id, component_id))
  }
  if (component_id <= 14L) {
    return(sprintf("discrep_%02d (theta_%02d)", component_id - 7L, component_id))
  }
  sprintf("transfer_%02d (theta_%02d)", component_id - 14L, component_id)
}

unified_ndlm_diag_extract_theta_draws <- function(env) {
  if (!exists("samp.theta_50_NDLM_synth_DISC", envir = env, inherits = FALSE)) {
    return(NULL)
  }
  raw_obj <- get("samp.theta_50_NDLM_synth_DISC", envir = env, inherits = FALSE)
  arr <- if (is.list(raw_obj) && !is.null(raw_obj$samp_theta)) raw_obj$samp_theta else raw_obj
  if (!is.numeric(arr)) return(NULL)
  d <- dim(arr)
  if (is.null(d) || length(d) != 3L) return(NULL)
  arr
}

unified_ndlm_diag_summarize_state_draws <- function(theta_draws, dates = as.Date(character(0))) {
  d <- dim(theta_draws)
  if (is.null(d) || length(d) != 3L) {
    stop("[NDLM_STATE_DRAWS_SHAPE] theta_draws must be a numeric 3D array [state, time, draw]", call. = FALSE)
  }
  n_state <- as.integer(d[1])
  n_time <- as.integer(d[2])
  n_draw <- as.integer(d[3])
  if (!is.finite(n_state) || !is.finite(n_time) || !is.finite(n_draw) ||
      n_state < 1L || n_time < 1L || n_draw < 1L) {
    stop("[NDLM_STATE_DRAWS_SHAPE] theta_draws dimensions must be positive", call. = FALSE)
  }

  if (length(dates) < n_time) {
    dates_use <- as.Date(rep(NA_character_, n_time))
  } else {
    dates_use <- suppressWarnings(as.Date(dates[seq_len(n_time)]))
  }
  idx <- seq_len(n_time)

  summary_rows <- vector("list", n_state)
  coverage_rows <- vector("list", n_state)
  for (j in seq_len(n_state)) {
    mat_j <- theta_draws[j, , , drop = TRUE]
    if (is.null(dim(mat_j))) {
      mat_j <- matrix(as.numeric(mat_j), nrow = n_time, ncol = 1L)
    } else if (length(dim(mat_j)) != 2L) {
      mat_j <- matrix(as.numeric(mat_j), nrow = n_time, ncol = n_draw)
    }
    q025 <- apply(mat_j, 1L, stats::quantile, probs = 0.025, na.rm = TRUE, type = 7L, names = FALSE)
    q500 <- apply(mat_j, 1L, stats::quantile, probs = 0.500, na.rm = TRUE, type = 7L, names = FALSE)
    q975 <- apply(mat_j, 1L, stats::quantile, probs = 0.975, na.rm = TRUE, type = 7L, names = FALSE)
    mn <- rowMeans(mat_j, na.rm = TRUE)
    band <- q975 - q025
    ok <- is.finite(q025) & is.finite(q500) & is.finite(q975) & is.finite(mn)

    label_j <- unified_ndlm_diag_component_label(j)
    summary_rows[[j]] <- data.frame(
      component_id = as.integer(j),
      component_label = label_j,
      t_index = as.integer(idx),
      date = dates_use,
      q025 = as.numeric(q025),
      q500 = as.numeric(q500),
      q975 = as.numeric(q975),
      mean = as.numeric(mn),
      band_width = as.numeric(band),
      stringsAsFactors = FALSE
    )
    coverage_rows[[j]] <- data.frame(
      component_id = as.integer(j),
      component_label = label_j,
      n_time = as.integer(n_time),
      finite_points = as.integer(sum(ok)),
      finite_rate = as.numeric(sum(ok) / n_time),
      mean_band_width = if (any(ok)) mean(band[ok]) else NA_real_,
      median_band_width = if (any(ok)) stats::median(band[ok]) else NA_real_,
      q95_band_width = if (any(ok)) as.numeric(stats::quantile(band[ok], probs = 0.95, names = FALSE, na.rm = TRUE)) else NA_real_,
      stringsAsFactors = FALSE
    )
  }

  list(
    summary = do.call(rbind, summary_rows),
    coverage = do.call(rbind, coverage_rows)
  )
}

unified_ndlm_diag_write_state_components_ci_plot <- function(summary_df, path, title, component_ids = NULL) {
  req <- c("component_id", "component_label", "t_index", "q025", "q500", "q975")
  if (!is.data.frame(summary_df) || !all(req %in% names(summary_df)) || nrow(summary_df) < 2L) return(FALSE)
  work <- summary_df
  if (!is.null(component_ids)) {
    keep <- suppressWarnings(as.integer(component_ids))
    keep <- keep[is.finite(keep)]
    work <- work[work$component_id %in% keep, , drop = FALSE]
  }
  comps <- sort(unique(suppressWarnings(as.integer(work$component_id))))
  comps <- comps[is.finite(comps)]
  if (length(comps) < 1L) return(FALSE)

  n_panels <- length(comps)
  n_col <- min(4L, max(1L, ceiling(sqrt(n_panels))))
  n_row <- max(1L, ceiling(n_panels / n_col))
  width_px <- max(1400L, 520L * n_col)
  height_px <- max(900L, 320L * n_row)

  grDevices::png(filename = path, width = width_px, height = height_px, res = 140)
  on.exit(grDevices::dev.off(), add = TRUE)
  graphics::par(mfrow = c(n_row, n_col), mar = c(2.9, 3.4, 2.2, 1.1), oma = c(0.5, 0.5, 2.0, 0))

  for (cid in comps) {
    sub <- work[work$component_id == cid, , drop = FALSE]
    x <- suppressWarnings(as.numeric(sub$t_index))
    lo <- suppressWarnings(as.numeric(sub$q025))
    md <- suppressWarnings(as.numeric(sub$q500))
    hi <- suppressWarnings(as.numeric(sub$q975))
    ok <- is.finite(x) & is.finite(lo) & is.finite(md) & is.finite(hi)
    panel_title <- as.character(sub$component_label[[1L]])
    if (sum(ok) < 2L) {
      graphics::plot.new()
      graphics::title(main = panel_title)
      next
    }
    y_rng <- range(c(lo[ok], hi[ok]), finite = TRUE)
    if (!all(is.finite(y_rng))) {
      graphics::plot.new()
      graphics::title(main = panel_title)
      next
    }
    pad <- 0.05 * max(diff(y_rng), 1e-8)
    y_lim <- c(y_rng[1] - pad, y_rng[2] + pad)

    graphics::plot(
      x[ok], md[ok],
      type = "n",
      xlab = "Time index",
      ylab = "State value",
      ylim = y_lim,
      main = panel_title
    )
    graphics::polygon(
      x = c(x[ok], rev(x[ok])),
      y = c(lo[ok], rev(hi[ok])),
      col = grDevices::adjustcolor("#80B1D3", alpha.f = 0.30),
      border = NA
    )
    graphics::lines(x[ok], md[ok], col = "#0B3C5D", lwd = 1.7)
    graphics::grid(col = "#D6DCE5", lty = "dotted")
  }

  graphics::mtext(title, outer = TRUE, line = 0.2, cex = 1.0)
  TRUE
}

unified_ndlm_diag_build_horizon_contract <- function(ndlm_obj, state_obj, retros_n, nws_n, glofas_n) {
  state_k <- NA_integer_
  state_k_overlap <- NA_integer_
  state_k_max <- NA_integer_
  state_k_cap <- NA_integer_
  state_nws <- NA_integer_
  state_glofas <- NA_integer_
  state_k_vec_nws <- NA_integer_
  state_k_vec_glofas <- NA_integer_
  state_seg_overlap <- NA_integer_
  state_seg_extension <- NA_integer_
  if (is.list(state_obj)) {
    state_k <- unified_ndlm_diag_int(state_obj$K)
    state_k_overlap <- unified_ndlm_diag_int(state_obj$K_overlap)
    state_k_max <- unified_ndlm_diag_int(state_obj$K_max)
    state_k_cap <- unified_ndlm_diag_int(state_obj$K_cap)
    state_nws <- unified_ndlm_diag_int(state_obj$nws_len)
    state_glofas <- unified_ndlm_diag_int(state_obj$glofas_len)
    state_k_vec_nws <- unified_ndlm_diag_named_int(state_obj$K_vec, "nws")
    state_k_vec_glofas <- unified_ndlm_diag_named_int(state_obj$K_vec, "glofas")
    state_seg_overlap <- unified_ndlm_diag_named_int(state_obj$segment_lengths, "overlap")
    state_seg_extension <- unified_ndlm_diag_named_int(state_obj$segment_lengths, "extension")
  }

  if (!is.finite(state_k_cap) || state_k_cap <= 0L) state_k_cap <- 14L
  if (!is.finite(state_nws) || state_nws <= 0L) state_nws <- nws_n
  if (!is.finite(state_glofas) || state_glofas <= 0L) state_glofas <- glofas_n

  expected_k_nws <- suppressWarnings(as.integer(min(state_nws, state_k_cap)))
  expected_k_glofas <- suppressWarnings(as.integer(min(state_glofas, state_k_cap)))
  expected_k_overlap <- suppressWarnings(as.integer(min(expected_k_nws, expected_k_glofas)))
  expected_k_max <- suppressWarnings(as.integer(max(expected_k_nws, expected_k_glofas)))
  expected_seg <- c(expected_k_overlap, max(expected_k_max - expected_k_overlap, 0L))
  standard_k <- if (is.list(ndlm_obj) && is.numeric(ndlm_obj$standard_forecast_errors)) {
    d <- dim(ndlm_obj$standard_forecast_errors)
    if (!is.null(d) && length(d) == 2L) as.integer(d[2]) else NA_integer_
  } else {
    NA_integer_
  }

  sm_k <- if (is.list(ndlm_obj) && is.list(ndlm_obj$sm_ens) && length(ndlm_obj$sm_ens) > 0L) {
    vapply(ndlm_obj$sm_ens, function(x) {
      d <- dim(x)
      if (is.null(d) || length(d) != 2L) return(NA_integer_)
      as.integer(d[2])
    }, integer(1))
  } else {
    integer(0)
  }

  sc_k <- if (is.list(ndlm_obj) && is.list(ndlm_obj$sC_ens) && length(ndlm_obj$sC_ens) > 0L) {
    vapply(ndlm_obj$sC_ens, function(x) {
      d <- dim(x)
      if (is.null(d) || length(d) != 3L) return(NA_integer_)
      as.integer(d[3])
    }, integer(1))
  } else {
    integer(0)
  }

  exps_k <- if (is.list(ndlm_obj) && is.numeric(ndlm_obj$exps)) {
    d <- dim(ndlm_obj$exps)
    if (!is.null(d) && length(d) == 2L) max(as.integer(d[2]) - as.integer(retros_n), 0L) else NA_integer_
  } else {
    NA_integer_
  }

  actual_seg <- if (length(sm_k) > 0L) sm_k else integer(0)
  actual_seg_txt <- if (length(actual_seg) == 0L) "[]" else sprintf("[%s]", paste(actual_seg, collapse = ","))
  expected_seg_txt <- sprintf("[%s]", paste(expected_seg, collapse = ","))
  sc_seg_txt <- if (length(sc_k) == 0L) "[]" else sprintf("[%s]", paste(sc_k, collapse = ","))

  rows <- list(
    data.frame(
      figure_or_series = "ndlm_total_forecast_horizon",
      expected_horizon = expected_k_max,
      actual_horizon = standard_k,
      status = if (is.finite(expected_k_max) && is.finite(standard_k) && expected_k_max == standard_k) "pass" else "mismatch",
      contract_rule = "K_max = max(min(nws_len,K_cap), min(glofas_len,K_cap))",
      notes = sprintf("state.K=%s state.K_max=%s state.K_overlap=%s K_cap=%s state.K_vec=(nws=%s,glofas=%s)", as.character(state_k), as.character(state_k_max), as.character(state_k_overlap), as.character(state_k_cap), as.character(state_k_vec_nws), as.character(state_k_vec_glofas)),
      stringsAsFactors = FALSE
    ),
    data.frame(
      figure_or_series = "ndlm_segment_profile_sm_ens",
      expected_horizon = expected_k_overlap,
      actual_horizon = if (length(sm_k) == 0L) NA_integer_ else sum(sm_k),
      status = if (length(sm_k) > 0L && all(is.finite(sm_k)) && all(sm_k >= 0L) && identical(as.integer(sm_k), as.integer(expected_seg))) "pass" else "mismatch",
      contract_rule = "sm_ens segment lengths must match [K_overlap, K_max-K_overlap]",
      notes = sprintf("expected=%s actual=%s", expected_seg_txt, actual_seg_txt),
      stringsAsFactors = FALSE
    ),
    data.frame(
      figure_or_series = "ndlm_segment_profile_sC_ens",
      expected_horizon = expected_k_overlap,
      actual_horizon = if (length(sc_k) == 0L) NA_integer_ else sum(sc_k),
      status = if (length(sc_k) > 0L && all(is.finite(sc_k)) && all(sc_k >= 0L) && identical(as.integer(sc_k), as.integer(expected_seg))) "pass" else "mismatch",
      contract_rule = "sC_ens segment lengths must match [K_overlap, K_max-K_overlap]",
      notes = sprintf("expected=%s actual=%s", expected_seg_txt, sc_seg_txt),
      stringsAsFactors = FALSE
    ),
    data.frame(
      figure_or_series = "ndlm_segment_profile_state_consistency",
      expected_horizon = expected_k_max,
      actual_horizon = if (length(sm_k) == 0L) NA_integer_ else sum(sm_k),
      status = if (length(sm_k) > 0L && length(sc_k) > 0L && all(is.finite(sm_k)) && all(is.finite(sc_k)) && length(sm_k) == length(sc_k) && all(sm_k == sc_k) && sum(sm_k) == standard_k) "pass" else "mismatch",
      contract_rule = "sm_ens and sC_ens segment profiles must match and sum to standard_forecast_errors horizon",
      notes = sprintf("sm_ens=%s sC_ens=%s standard.K=%s", actual_seg_txt, sc_seg_txt, as.character(standard_k)),
      stringsAsFactors = FALSE
    ),
    data.frame(
      figure_or_series = "ndlm_state_metadata_consistency",
      expected_horizon = expected_k_max,
      actual_horizon = state_k_max,
      status = if (is.finite(state_k_max) && is.finite(state_k_overlap) && is.finite(state_seg_overlap) && is.finite(state_seg_extension) &&
                    state_k_max == expected_k_max &&
                    state_k_overlap == expected_k_overlap &&
                    state_seg_overlap == state_k_overlap &&
                    (state_seg_overlap + state_seg_extension) == state_k_max &&
                    state_k_vec_nws == expected_k_nws &&
                    state_k_vec_glofas == expected_k_glofas &&
                    state_k == state_k_max) "pass" else "mismatch",
      contract_rule = "state metadata (K_vec/K_overlap/K_max/segment_lengths) must match expected ragged horizon",
      notes = sprintf("state.seg=[%s,%s] state.K=%s expected.Kmax=%s expected.Koverlap=%s", as.character(state_seg_overlap), as.character(state_seg_extension), as.character(state_k), as.character(expected_k_max), as.character(expected_k_overlap)),
      stringsAsFactors = FALSE
    ),
    data.frame(
      figure_or_series = "ndlm_exps_forecast_extension",
      expected_horizon = 0L,
      actual_horizon = exps_k,
      status = if (is.finite(exps_k) && exps_k == 0L) "pass" else "mismatch",
      contract_rule = "Theory-aligned NDLM stores retrospective exps over T only; forecast component is represented via sm_ens/sC_ens",
      notes = sprintf("retros_n=%d", as.integer(retros_n)),
      stringsAsFactors = FALSE
    )
  )

  do.call(rbind, rows)
}

unified_generate_ndlm_post_diagnostics <- function(
  run_root,
  ndlm_rdata_path,
  retros_csv_path,
  nws_csv_path,
  glofas_csv_path,
  fit_log_path = "",
  output_dir = NULL,
  strict_contract = FALSE
) {
  if (is.null(output_dir) || !nzchar(output_dir)) {
    output_dir <- file.path(run_root, "diagnostics", "ndlm")
  }
  dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

  retros_df <- unified_ndlm_diag_read_csv(retros_csv_path, "retros")
  nws_df <- unified_ndlm_diag_read_csv(nws_csv_path, "nws_forecast")
  glofas_df <- unified_ndlm_diag_read_csv(glofas_csv_path, "glofas_forecast")

  env <- new.env(parent = emptyenv())
  load(ndlm_rdata_path, envir = env)
  if (!exists("new.theta.out_50_NDLM_synth_DISC", envir = env, inherits = FALSE)) {
    stop("[NDLM_DIAG_OBJECT_MISSING] Missing new.theta.out_50_NDLM_synth_DISC in NDLM bundle.", call. = FALSE)
  }

  ndlm_obj <- get("new.theta.out_50_NDLM_synth_DISC", envir = env, inherits = FALSE)
  state_obj <- if (exists("ndlm_main_theory_state", envir = env, inherits = FALSE)) {
    get("ndlm_main_theory_state", envir = env, inherits = FALSE)
  } else {
    NULL
  }
  covariance_diagnostics <- if (
    is.list(state_obj) &&
      is.data.frame(state_obj$covariance_diagnostics) &&
      nrow(state_obj$covariance_diagnostics) > 0L
  ) {
    state_obj$covariance_diagnostics
  } else {
    do.call(rbind, list(
      unified_ndlm_diag_cov_row("smooth_cov", ndlm_obj$sC),
      if (is.list(ndlm_obj$sC_ens) && length(ndlm_obj$sC_ens) >= 1L) unified_ndlm_diag_cov_row("forecast_cov_segment_1", ndlm_obj$sC_ens[[1L]]) else NULL,
      if (is.list(ndlm_obj$sC_ens) && length(ndlm_obj$sC_ens) >= 2L) unified_ndlm_diag_cov_row("forecast_cov_segment_2", ndlm_obj$sC_ens[[2L]]) else NULL
    ))
  }

  iter_trace <- unified_ndlm_diag_parse_progress_log(fit_log_path)
  if (nrow(iter_trace) == 0L && exists("seq.elbo_50_NDLM_synth_DISC", envir = env, inherits = FALSE)) {
    elbo <- as.numeric(get("seq.elbo_50_NDLM_synth_DISC", envir = env, inherits = FALSE))
    sigma <- if (exists("seq.sigma_50_NDLM_synth_DISC", envir = env, inherits = FALSE)) {
      as.numeric(get("seq.sigma_50_NDLM_synth_DISC", envir = env, inherits = FALSE))
    } else {
      rep(NA_real_, length(elbo))
    }
    iter_trace <- data.frame(
      iter = seq_along(elbo),
      elbo = elbo,
      crit_elbo = c(NA_real_, abs(diff(elbo))),
      sigma_exp = sigma,
      gamma_exp = NA_real_,
      state_norm_sq = NA_real_,
      w_hist = NA_real_,
      w_fore = NA_real_,
      stringsAsFactors = FALSE
    )
  }

  retros_dates <- unified_ndlm_diag_extract_date_column(retros_df)
  nws_dates <- unified_ndlm_diag_extract_date_column(nws_df)
  glofas_dates <- unified_ndlm_diag_extract_date_column(glofas_df)

  exps <- ndlm_obj$exps
  sfe <- ndlm_obj$standard_forecast_errors
  sm_ens <- ndlm_obj$sm_ens

  time_rows <- list(
    {
      span <- unified_ndlm_diag_date_span(retros_dates)
      data.frame(source_series = "retros", t_min = span[["t_min"]], t_max = span[["t_max"]], n_points = as.integer(nrow(retros_df)), missing_count = as.integer(sum(!is.finite(unified_ndlm_diag_pick_numeric_column(retros_df, preferred = c("USGS", "y", "obs", "flow", "value")))), na.rm = TRUE), stringsAsFactors = FALSE)
    },
    {
      span <- unified_ndlm_diag_date_span(nws_dates)
      data.frame(source_series = "nws_forecast", t_min = span[["t_min"]], t_max = span[["t_max"]], n_points = as.integer(nrow(nws_df)), missing_count = 0L, stringsAsFactors = FALSE)
    },
    {
      span <- unified_ndlm_diag_date_span(glofas_dates)
      data.frame(source_series = "glofas_forecast", t_min = span[["t_min"]], t_max = span[["t_max"]], n_points = as.integer(nrow(glofas_df)), missing_count = 0L, stringsAsFactors = FALSE)
    },
    {
      exps_dim <- dim(exps)
      n_exps <- if (!is.null(exps_dim) && length(exps_dim) == 2L) as.integer(exps_dim[2]) else 0L
      data.frame(source_series = "ndlm_exps", t_min = if (n_exps > 0L) "1" else "", t_max = as.character(n_exps), n_points = n_exps, missing_count = as.integer(if (is.numeric(exps)) sum(!is.finite(exps)) else NA_integer_), stringsAsFactors = FALSE)
    },
    {
      sfe_dim <- dim(sfe)
      n_sfe <- if (!is.null(sfe_dim) && length(sfe_dim) == 2L) as.integer(sfe_dim[2]) else 0L
      data.frame(source_series = "ndlm_standard_forecast_errors", t_min = if (n_sfe > 0L) "1" else "", t_max = as.character(n_sfe), n_points = n_sfe, missing_count = as.integer(if (is.numeric(sfe)) sum(!is.finite(sfe)) else NA_integer_), stringsAsFactors = FALSE)
    }
  )

  if (is.list(sm_ens) && length(sm_ens) > 0L) {
    for (i in seq_along(sm_ens)) {
      d <- dim(sm_ens[[i]])
      n_seg <- if (!is.null(d) && length(d) == 2L) as.integer(d[2]) else 0L
      time_rows[[length(time_rows) + 1L]] <- data.frame(
        source_series = sprintf("ndlm_sm_ens_seg_%d", as.integer(i)),
        t_min = if (n_seg > 0L) "1" else "",
        t_max = as.character(n_seg),
        n_points = n_seg,
        missing_count = as.integer(if (is.numeric(sm_ens[[i]])) sum(!is.finite(sm_ens[[i]])) else NA_integer_),
        stringsAsFactors = FALSE
      )
    }
  }

  time_coverage <- do.call(rbind, time_rows)

  shape_rows <- do.call(rbind, list(
    unified_ndlm_diag_shape_row("new.theta.out_50_NDLM_synth_DISC$sm", ndlm_obj$sm),
    unified_ndlm_diag_shape_row("new.theta.out_50_NDLM_synth_DISC$sC", ndlm_obj$sC),
    unified_ndlm_diag_shape_row("new.theta.out_50_NDLM_synth_DISC$exps", ndlm_obj$exps),
    unified_ndlm_diag_shape_row("new.theta.out_50_NDLM_synth_DISC$standard_forecast_errors", ndlm_obj$standard_forecast_errors),
    unified_ndlm_diag_shape_row("new.theta.out_50_NDLM_synth_DISC$sm_ens", ndlm_obj$sm_ens),
    unified_ndlm_diag_shape_row("new.theta.out_50_NDLM_synth_DISC$sC_ens", ndlm_obj$sC_ens),
    if (!is.null(state_obj)) unified_ndlm_diag_shape_row("ndlm_main_theory_state", state_obj) else NULL
  ))

  horizon_contract <- unified_ndlm_diag_build_horizon_contract(
    ndlm_obj = ndlm_obj,
    state_obj = state_obj,
    retros_n = as.integer(nrow(retros_df)),
    nws_n = as.integer(nrow(nws_df)),
    glofas_n = as.integer(nrow(glofas_df))
  )

  derive_active_set <- function() {
    if (is.list(state_obj) && is.data.frame(state_obj$active_set_by_lead)) {
      out <- state_obj$active_set_by_lead
      req <- c("lead", "active_nws", "active_glofas", "active_count")
      if (all(req %in% names(out))) {
        return(out[, req, drop = FALSE])
      }
    }
    cap <- if (is.list(state_obj)) unified_ndlm_diag_int(state_obj$K_cap) else NA_integer_
    if (!is.finite(cap) || cap <= 0L) cap <- 14L
    k_nws <- min(as.integer(nrow(nws_df)), cap)
    k_glofas <- min(as.integer(nrow(glofas_df)), cap)
    k_max <- max(k_nws, k_glofas)
    data.frame(
      lead = seq_len(k_max),
      active_nws = as.integer(seq_len(k_max) <= k_nws),
      active_glofas = as.integer(seq_len(k_max) <= k_glofas),
      active_count = as.integer((seq_len(k_max) <= k_nws) + (seq_len(k_max) <= k_glofas)),
      stringsAsFactors = FALSE
    )
  }
  active_set_by_lead <- derive_active_set()

  state_dim_by_lead <- if (is.list(state_obj) && is.data.frame(state_obj$state_dim_by_lead) &&
                           all(c("lead", "state_dim") %in% names(state_obj$state_dim_by_lead))) {
    state_obj$state_dim_by_lead[, c("lead", "state_dim"), drop = FALSE]
  } else {
    data.frame(
      lead = active_set_by_lead$lead,
      state_dim = as.integer(7L * active_set_by_lead$active_count),
      stringsAsFactors = FALSE
    )
  }

  parse_seg_profile <- function(x) {
    out <- gsub("^\\[|\\]$", "", as.character(x))
    if (!nzchar(out)) return(integer(0))
    vals <- strsplit(out, ",", fixed = TRUE)[[1L]]
    suppressWarnings(as.integer(trimws(vals)))
  }
  row_sm <- horizon_contract[horizon_contract$figure_or_series == "ndlm_segment_profile_sm_ens", , drop = FALSE]
  row_total <- horizon_contract[horizon_contract$figure_or_series == "ndlm_total_forecast_horizon", , drop = FALSE]
  sm_profile <- if (nrow(row_sm) == 1L) parse_seg_profile(sub(".*actual=\\[([^]]*)\\].*", "[\\1]", row_sm$notes[[1L]])) else integer(0)
  ragged_coverage_summary <- data.frame(
    metric = c(
      "k_nws_effective", "k_glofas_effective", "k_overlap", "k_max",
      "segment_overlap", "segment_extension", "segment_sum", "standard_forecast_errors_k", "contract_status"
    ),
    value = c(
      as.character(sum(active_set_by_lead$active_nws)),
      as.character(sum(active_set_by_lead$active_glofas)),
      as.character(sum(active_set_by_lead$active_count == 2L)),
      as.character(nrow(active_set_by_lead)),
      as.character(if (length(sm_profile) >= 1L) sm_profile[[1L]] else NA_integer_),
      as.character(if (length(sm_profile) >= 2L) sm_profile[[2L]] else NA_integer_),
      as.character(if (length(sm_profile) > 0L) sum(sm_profile, na.rm = TRUE) else NA_integer_),
      as.character(if (nrow(row_total) == 1L) row_total$actual_horizon[[1L]] else NA_integer_),
      if (all(horizon_contract$status == "pass")) "pass" else "mismatch"
    ),
    stringsAsFactors = FALSE
  )

  obs_series <- unified_ndlm_diag_pick_numeric_column(retros_df, preferred = c("USGS", "y", "obs", "flow", "value"))
  smooth_series <- if (is.numeric(exps) && !is.null(dim(exps)) && length(dim(exps)) == 2L && dim(exps)[1] >= 2L) {
    as.numeric(exps[2, ])
  } else {
    numeric(0)
  }

  fit_diag_state <- if (is.list(state_obj) && is.list(state_obj$fit_diagnostics)) state_obj$fit_diagnostics else NULL
  get_diag_vec <- function(name, fallback, n_target) {
    val <- if (!is.null(fit_diag_state)) fit_diag_state[[name]] else NULL
    out <- suppressWarnings(as.numeric(val))
    if (length(out) != n_target) out <- fallback
    if (length(out) != n_target) out <- rep(NA_real_, n_target)
    out
  }

  n_overlap <- max(
    min(length(obs_series), length(smooth_series)),
    if (!is.null(fit_diag_state)) suppressWarnings(as.integer(length(fit_diag_state$y_observed))) else 0L
  )
  if (!is.finite(n_overlap) || n_overlap < 0L) n_overlap <- 0L
  if (n_overlap > 0L) {
    n_overlap <- min(
      n_overlap,
      length(obs_series),
      max(length(smooth_series), if (!is.null(fit_diag_state)) suppressWarnings(as.integer(length(fit_diag_state$y_smoothed))) else 0L)
    )
  }

  obs_use <- if (n_overlap > 0L) as.numeric(obs_series[seq_len(n_overlap)]) else numeric(0)
  smooth_use <- if (n_overlap > 0L) get_diag_vec("y_smoothed", smooth_series[seq_len(min(length(smooth_series), n_overlap))], n_overlap) else numeric(0)
  pred_use <- if (n_overlap > 0L) get_diag_vec("y_predicted_one_step", rep(NA_real_, n_overlap), n_overlap) else numeric(0)
  filt_use <- if (n_overlap > 0L) get_diag_vec("y_filtered", rep(NA_real_, n_overlap), n_overlap) else numeric(0)
  date_use <- if (n_overlap > 0L && length(retros_dates) >= n_overlap) retros_dates[seq_len(n_overlap)] else as.Date(rep(NA_character_, n_overlap))

  mode_series <- data.frame(
    date = date_use,
    observed = obs_use,
    one_step_predicted = pred_use,
    filtered_fit = filt_use,
    smoothed_fit = smooth_use,
    residual_one_step = if (n_overlap > 0L) pred_use - obs_use else numeric(0),
    residual_filtered = if (n_overlap > 0L) filt_use - obs_use else numeric(0),
    residual_smoothed = if (n_overlap > 0L) smooth_use - obs_use else numeric(0),
    stringsAsFactors = FALSE
  )

  summarize_mode <- function(mode_name, fitted_vals, observed_vals) {
    fitted_vals <- suppressWarnings(as.numeric(fitted_vals))
    observed_vals <- suppressWarnings(as.numeric(observed_vals))
    n <- min(length(fitted_vals), length(observed_vals))
    if (n <= 0L) {
      return(data.frame(
        mode = mode_name, n_points = 0L, finite_points = 0L, coverage_rate = NA_real_,
        rmse = NA_real_, mae = NA_real_, corr = NA_real_, mean_residual = NA_real_,
        stringsAsFactors = FALSE
      ))
    }
    f <- fitted_vals[seq_len(n)]
    o <- observed_vals[seq_len(n)]
    ok <- is.finite(f) & is.finite(o)
    err <- f - o
    data.frame(
      mode = mode_name,
      n_points = as.integer(n),
      finite_points = as.integer(sum(ok)),
      coverage_rate = if (n > 0L) as.numeric(sum(ok) / n) else NA_real_,
      rmse = if (any(ok)) sqrt(mean(err[ok]^2)) else NA_real_,
      mae = if (any(ok)) mean(abs(err[ok])) else NA_real_,
      corr = if (sum(ok) >= 2L) suppressWarnings(stats::cor(f[ok], o[ok])) else NA_real_,
      mean_residual = if (any(ok)) mean(err[ok]) else NA_real_,
      stringsAsFactors = FALSE
    )
  }

  mode_coverage <- do.call(rbind, list(
    summarize_mode("one_step_predicted", mode_series$one_step_predicted, mode_series$observed),
    summarize_mode("filtered_fit", mode_series$filtered_fit, mode_series$observed),
    summarize_mode("smoothed_fit", mode_series$smoothed_fit, mode_series$observed)
  ))
  row_sm <- mode_coverage[mode_coverage$mode == "smoothed_fit", , drop = FALSE]
  fit_summary <- data.frame(
    metric = c(
      "retros_points", "exps_points", "overlap_points", "finite_overlap_points",
      "coverage_rate", "rmse", "mae", "corr"
    ),
    value = c(
      as.numeric(length(obs_series)),
      as.numeric(length(smooth_series)),
      as.numeric(n_overlap),
      if (nrow(row_sm) == 1L) as.numeric(row_sm$finite_points[[1L]]) else NA_real_,
      if (nrow(row_sm) == 1L) as.numeric(row_sm$coverage_rate[[1L]]) else NA_real_,
      if (nrow(row_sm) == 1L) as.numeric(row_sm$rmse[[1L]]) else NA_real_,
      if (nrow(row_sm) == 1L) as.numeric(row_sm$mae[[1L]]) else NA_real_,
      if (nrow(row_sm) == 1L) as.numeric(row_sm$corr[[1L]]) else NA_real_
    ),
    stringsAsFactors = FALSE
  )

  fit_series <- data.frame(
    date = mode_series$date,
    observed = mode_series$observed,
    ndlm_fit = mode_series$smoothed_fit,
    residual = mode_series$residual_smoothed,
    stringsAsFactors = FALSE
  )

  sigma_long <- unified_ndlm_diag_extract_sigma_long(iter_trace = iter_trace, env = env)

  theta_draws <- unified_ndlm_diag_extract_theta_draws(env)
  state_ci <- NULL
  if (!is.null(theta_draws)) {
    state_ci <- unified_ndlm_diag_summarize_state_draws(theta_draws = theta_draws, dates = retros_dates)
  }

  horizon_note <- c(
    "# NDLM Horizon Contract",
    "",
    "Theory alignment:",
    "1. NDLM Model C uses ragged forecast horizons with active set A_k = {j: k <= K_j}.",
    "2. In this implementation, K_j = min(source_len_j, K_cap), K_overlap=min(K_j), K_max=max(K_j).",
    "3. `exps` is retrospective-only (`T` columns). Forecast discrepancy dynamics are represented by segmented `sm_ens/sC_ens` and `standard_forecast_errors` over K_max.",
    "",
    sprintf("Observed lengths: retros=%d, nws=%d, glofas=%d", as.integer(nrow(retros_df)), as.integer(nrow(nws_df)), as.integer(nrow(glofas_df))),
    sprintf("Contract result: %s", if (all(horizon_contract$status == "pass")) "pass" else "mismatch")
  )

  paths <- list(
    ndlm_iter_trace = file.path(output_dir, "ndlm_iter_trace.csv"),
    ndlm_time_coverage = file.path(output_dir, "ndlm_time_coverage.csv"),
    active_set_by_lead = file.path(output_dir, "active_set_by_lead.csv"),
    state_dim_by_lead = file.path(output_dir, "state_dim_by_lead.csv"),
    horizon_contract_check = file.path(output_dir, "horizon_contract_check.csv"),
    ndlm_plot_contract_check = file.path(output_dir, "ndlm_plot_contract_check.csv"),
    ndlm_object_shapes = file.path(output_dir, "ndlm_object_shapes.csv"),
    ndlm_fit_vs_observed_coverage = file.path(output_dir, "ndlm_fit_vs_observed_coverage.csv"),
    ndlm_fit_series = file.path(output_dir, "ndlm_fit_series.csv"),
    ndlm_fit_modes_coverage = file.path(output_dir, "ndlm_fit_modes_coverage.csv"),
    ndlm_fit_modes_series = file.path(output_dir, "ndlm_fit_modes_series.csv"),
    ndlm_sigma_trace_long = file.path(output_dir, "ndlm_sigma_trace_long.csv"),
    ndlm_state_components_ci_summary = file.path(output_dir, "ndlm_state_components_ci_summary.csv"),
    ndlm_state_components_ci_coverage = file.path(output_dir, "ndlm_state_components_ci_coverage.csv"),
    ndlm_covariance_diagnostics = file.path(output_dir, "ndlm_covariance_diagnostics.csv"),
    ragged_coverage_summary = file.path(output_dir, "ragged_coverage_summary.csv"),
    ndlm_horizon_contract = file.path(output_dir, "ndlm_horizon_contract.md"),
    ndlm_elbo_trace = file.path(output_dir, "ndlm_elbo_trace.png"),
    ndlm_sigma_trace = file.path(output_dir, "ndlm_sigma_trace.png"),
    ndlm_state_norm_trace = file.path(output_dir, "ndlm_state_norm_trace.png"),
    ndlm_dynamic_fit_full = file.path(output_dir, "ndlm_dynamic_fit_full.png"),
    ndlm_dynamic_fit_modes_full = file.path(output_dir, "ndlm_dynamic_fit_modes_full.png"),
    ndlm_state_components_ci_all = file.path(output_dir, "ndlm_state_components_ci_all.png"),
    ndlm_state_components_ci_hist = file.path(output_dir, "ndlm_state_components_ci_hist.png"),
    ndlm_state_components_ci_discrep = file.path(output_dir, "ndlm_state_components_ci_discrep.png"),
    ndlm_state_components_ci_transfer = file.path(output_dir, "ndlm_state_components_ci_transfer.png"),
    ndlm_dynamic_fit_2012_2016 = file.path(output_dir, "ndlm_dynamic_fit_2012_2016.png"),
    ndlm_dynamic_fit_2017_2019 = file.path(output_dir, "ndlm_dynamic_fit_2017_2019.png"),
    ndlm_dynamic_fit_2018_2020 = file.path(output_dir, "ndlm_dynamic_fit_2018_2020.png")
  )

  utils::write.csv(iter_trace, paths$ndlm_iter_trace, row.names = FALSE)
  utils::write.csv(time_coverage, paths$ndlm_time_coverage, row.names = FALSE)
  utils::write.csv(active_set_by_lead, paths$active_set_by_lead, row.names = FALSE)
  utils::write.csv(state_dim_by_lead, paths$state_dim_by_lead, row.names = FALSE)
  utils::write.csv(horizon_contract, paths$horizon_contract_check, row.names = FALSE)
  utils::write.csv(horizon_contract, paths$ndlm_plot_contract_check, row.names = FALSE)
  utils::write.csv(shape_rows, paths$ndlm_object_shapes, row.names = FALSE)
  utils::write.csv(fit_summary, paths$ndlm_fit_vs_observed_coverage, row.names = FALSE)
  utils::write.csv(fit_series, paths$ndlm_fit_series, row.names = FALSE)
  utils::write.csv(mode_coverage, paths$ndlm_fit_modes_coverage, row.names = FALSE)
  utils::write.csv(mode_series, paths$ndlm_fit_modes_series, row.names = FALSE)
  if (is.data.frame(sigma_long) && nrow(sigma_long) > 0L) {
    utils::write.csv(sigma_long, paths$ndlm_sigma_trace_long, row.names = FALSE)
  }
  if (!is.null(state_ci) && is.list(state_ci) && is.data.frame(state_ci$summary) && nrow(state_ci$summary) > 0L) {
    utils::write.csv(state_ci$summary, paths$ndlm_state_components_ci_summary, row.names = FALSE)
    utils::write.csv(state_ci$coverage, paths$ndlm_state_components_ci_coverage, row.names = FALSE)
  }
  utils::write.csv(covariance_diagnostics, paths$ndlm_covariance_diagnostics, row.names = FALSE)
  utils::write.csv(ragged_coverage_summary, paths$ragged_coverage_summary, row.names = FALSE)
  writeLines(horizon_note, con = paths$ndlm_horizon_contract)

  invisible(unified_ndlm_diag_write_trace_plot(
    df = iter_trace,
    x_col = "iter",
    y_col = "elbo",
    path = paths$ndlm_elbo_trace,
    main = "NDLM ELBO Trace",
    ylab = "ELBO"
  ))
  sigma_trace_paths <- unified_ndlm_diag_write_sigma_traces(
    sigma_long = sigma_long,
    output_dir = output_dir,
    primary_path = paths$ndlm_sigma_trace
  )
  if (length(sigma_trace_paths) == 0L) {
    invisible(unified_ndlm_diag_write_trace_plot(
      df = iter_trace,
      x_col = "iter",
      y_col = "sigma_exp",
      path = paths$ndlm_sigma_trace,
      main = "NDLM Sigma Trace",
      ylab = "Sigma"
    ))
  }
  invisible(unified_ndlm_diag_write_trace_plot(
    df = iter_trace,
    x_col = "iter",
    y_col = "state_norm_sq",
    path = paths$ndlm_state_norm_trace,
    main = "NDLM State-Norm Trace",
    ylab = "State Norm Sq"
  ))

  if (n_overlap > 1L) {
    invisible(unified_ndlm_diag_write_fit_modes_plot(
      df = mode_series,
      path = paths$ndlm_dynamic_fit_modes_full,
      title = "NDLM Fit Comparison: One-step vs Filtered vs Smoothed"
    ))

    # Full retrospective fit view.
    invisible(unified_ndlm_diag_write_fit_plot(
      dates = fit_series$date,
      obs = fit_series$observed,
      fit = fit_series$ndlm_fit,
      path = paths$ndlm_dynamic_fit_full,
      title = "NDLM Dynamic Location Fit vs Observed (Full Retrospective)",
      x_as_date = any(!is.na(fit_series$date))
    ))

    # Standard post windows for quick parity checks.
    win_specs <- list(
      list(path = paths$ndlm_dynamic_fit_2012_2016, start = as.Date("2012-01-01"), end = as.Date("2016-12-31"), label = "2012-2016"),
      list(path = paths$ndlm_dynamic_fit_2017_2019, start = as.Date("2017-01-01"), end = as.Date("2019-12-31"), label = "2017-2019"),
      list(path = paths$ndlm_dynamic_fit_2018_2020, start = as.Date("2018-01-01"), end = as.Date("2020-12-31"), label = "2018-2020")
    )
    for (spec in win_specs) {
      idx <- if (any(!is.na(fit_series$date))) {
        which(!is.na(fit_series$date) & fit_series$date >= spec$start & fit_series$date <= spec$end)
      } else {
        integer(0)
      }
      if (length(idx) < 2L) next
      invisible(unified_ndlm_diag_write_fit_plot(
        dates = fit_series$date[idx],
        obs = fit_series$observed[idx],
        fit = fit_series$ndlm_fit[idx],
        path = spec$path,
        title = sprintf("NDLM Dynamic Location Fit vs Observed (%s)", spec$label),
        x_as_date = TRUE
      ))
    }
  }

  if (!is.null(state_ci) && is.list(state_ci) && is.data.frame(state_ci$summary) && nrow(state_ci$summary) > 0L) {
    invisible(unified_ndlm_diag_write_state_components_ci_plot(
      summary_df = state_ci$summary,
      path = paths$ndlm_state_components_ci_all,
      title = "NDLM State Components (Posterior Median + 95% Credible Interval)"
    ))
    invisible(unified_ndlm_diag_write_state_components_ci_plot(
      summary_df = state_ci$summary,
      path = paths$ndlm_state_components_ci_hist,
      title = "NDLM Historical Block States (1-7): Median + 95% CI",
      component_ids = 1:7
    ))
    invisible(unified_ndlm_diag_write_state_components_ci_plot(
      summary_df = state_ci$summary,
      path = paths$ndlm_state_components_ci_discrep,
      title = "NDLM Discrepancy Block States (8-14): Median + 95% CI",
      component_ids = 8:14
    ))
    invisible(unified_ndlm_diag_write_state_components_ci_plot(
      summary_df = state_ci$summary,
      path = paths$ndlm_state_components_ci_transfer,
      title = "NDLM Transfer Block States (15+): Median + 95% CI",
      component_ids = which(sort(unique(as.integer(state_ci$summary$component_id))) >= 15L)
    ))
  }

  if (isTRUE(strict_contract)) {
    mismatches <- horizon_contract$figure_or_series[horizon_contract$status != "pass"]
    if (length(mismatches) > 0L) {
      stop(
        sprintf(
          "[NDLM_HORIZON_CONTRACT] NDLM horizon contract mismatch for: %s",
          paste(mismatches, collapse = ", ")
        ),
        call. = FALSE
      )
    }
  }

  list(
    status = if (all(horizon_contract$status == "pass")) "pass" else "mismatch",
    output_dir = normalizePath(output_dir, mustWork = FALSE),
    paths = unname(vapply(paths, normalizePath, character(1), mustWork = FALSE))
  )
}
