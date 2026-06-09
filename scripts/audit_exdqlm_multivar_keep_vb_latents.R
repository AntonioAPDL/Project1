#!/usr/bin/env Rscript

suppressWarnings(options(stringsAsFactors = FALSE))

parse_args <- function(args) {
  out <- list(
    run_roots = character(0),
    out_dir = file.path("reports", paste0("exdqlm_multivar_keep_vb_latent_audit_", format(Sys.time(), "%Y%m%d_%H%M%S"))),
    window_days = 90L
  )
  i <- 1L
  while (i <= length(args)) {
    key <- args[[i]]
    if (identical(key, "--run-root")) {
      i <- i + 1L
      out$run_roots <- c(out$run_roots, args[[i]])
    } else if (identical(key, "--out-dir")) {
      i <- i + 1L
      out$out_dir <- args[[i]]
    } else if (identical(key, "--window-days")) {
      i <- i + 1L
      out$window_days <- as.integer(args[[i]])
    } else if (key %in% c("-h", "--help")) {
      cat(
        "Usage: Rscript scripts/audit_exdqlm_multivar_keep_vb_latents.R",
        " --run-root <run_dir> [--run-root <run_dir> ...]",
        " --out-dir <report_dir> [--window-days 90]\n"
      )
      quit(status = 0L)
    } else {
      stop(sprintf("Unknown argument: %s", key), call. = FALSE)
    }
    i <- i + 1L
  }
  if (!length(out$run_roots)) {
    stop("At least one --run-root is required.", call. = FALSE)
  }
  out
}

num <- function(x) suppressWarnings(as.numeric(x))

finite_summary <- function(x) {
  v <- num(x)
  finite <- is.finite(v)
  vf <- v[finite]
  if (!length(vf)) {
    return(data.frame(
      n = length(v), finite_n = 0L, nonfinite_n = length(v),
      min = NA_real_, q01 = NA_real_, q05 = NA_real_, q50 = NA_real_,
      q95 = NA_real_, q99 = NA_real_, max = NA_real_, mean = NA_real_,
      sd = NA_real_, max_abs = NA_real_
    ))
  }
  qs <- stats::quantile(vf, probs = c(0.01, 0.05, 0.50, 0.95, 0.99), names = FALSE, na.rm = TRUE)
  data.frame(
    n = length(v),
    finite_n = length(vf),
    nonfinite_n = length(v) - length(vf),
    min = min(vf),
    q01 = qs[[1L]],
    q05 = qs[[2L]],
    q50 = qs[[3L]],
    q95 = qs[[4L]],
    q99 = qs[[5L]],
    max = max(vf),
    mean = mean(vf),
    sd = stats::sd(vf),
    max_abs = max(abs(vf))
  )
}

bind_rows <- function(x) {
  x <- Filter(Negate(is.null), x)
  if (!length(x)) return(data.frame())
  all_cols <- unique(unlist(lapply(x, names), use.names = FALSE))
  x <- lapply(x, function(df) {
    missing <- setdiff(all_cols, names(df))
    for (col in missing) df[[col]] <- rep(NA, nrow(df))
    df[, all_cols, drop = FALSE]
  })
  do.call(rbind, x)
}

safe_read_csv <- function(path) {
  if (!file.exists(path)) return(NULL)
  tryCatch(utils::read.csv(path, check.names = FALSE), error = function(e) NULL)
}

run_id_from_path <- function(path) {
  parts <- strsplit(normalizePath(path, mustWork = FALSE), .Platform$file.sep, fixed = TRUE)[[1L]]
  idx <- match("runs", parts)
  if (!is.na(idx) && idx + 1L <= length(parts)) return(parts[[idx + 1L]])
  NA_character_
}

q_from_path <- function(path) {
  m <- regexpr("q=[0-9]+", path)
  if (m[[1L]] < 0L) return(NA_integer_)
  as.integer(sub("q=", "", regmatches(path, m)))
}

spec_from_run_id <- function(run_id) {
  patterns <- c(
    "_he2grid_([^_]+_[^_]+)_",
    "_v8_([^_]+_[^_]+)_exdqlm"
  )
  for (pattern in patterns) {
    m <- regexec(pattern, run_id)
    got <- regmatches(run_id, m)[[1L]]
    if (length(got) >= 2L) return(got[[2L]])
  }
  NA_character_
}

cutoff_from_run_id <- function(run_id) {
  m <- regexec("multimodel_([0-9]{8})_", run_id)
  got <- regmatches(run_id, m)[[1L]]
  if (length(got) >= 2L) got[[2L]] else NA_character_
}

run_root_from_rdata <- function(path) {
  parts <- strsplit(normalizePath(path, mustWork = FALSE), .Platform$file.sep, fixed = TRUE)[[1L]]
  idx <- match("runs", parts)
  if (!is.na(idx) && idx + 1L <= length(parts)) {
    return(paste(parts[seq_len(idx + 1L)], collapse = .Platform$file.sep))
  }
  dirname(dirname(dirname(dirname(path))))
}

read_history_dates <- function(run_root) {
  retros <- safe_read_csv(file.path(run_root, "inputs", "shared", "retros", "retros.csv"))
  if (is.null(retros)) return(as.Date(character(0)))
  date_col <- intersect(c("Date", "date", "time", "timestamp"), names(retros))
  if (!length(date_col)) return(as.Date(character(0)))
  suppressWarnings(as.Date(retros[[date_col[[1L]]]]))
}

read_forecast_dates <- function(run_root, source_label) {
  fname <- switch(
    source_label,
    "GloFAS" = "glofas_forecast.csv",
    "NWS3.0" = "nws_forecast.csv",
    "nws_forecast.csv"
  )
  df <- safe_read_csv(file.path(run_root, "inputs", "shared", "forecasts", fname))
  if (is.null(df)) return(as.Date(character(0)))
  date_col <- intersect(c("target_date", "Date", "date", "time", "timestamp"), names(df))
  if (!length(date_col)) return(as.Date(character(0)))
  suppressWarnings(as.Date(df[[date_col[[1L]]]]))
}

first_date_chr <- function(dates) {
  if (!length(dates)) return(NA_character_)
  as.character(dates[[1L]])
}

last_date_chr <- function(dates, n = length(dates)) {
  if (!length(dates) || !is.finite(n) || n <= 0L) return(NA_character_)
  as.character(dates[[min(length(dates), as.integer(n))]])
}

object_by_prefix <- function(env, prefix) {
  nms <- ls(env, all.names = TRUE)
  hit <- nms[startsWith(nms, prefix)]
  if (!length(hit)) return(NULL)
  get(hit[[1L]], envir = env)
}

object_name_by_prefix <- function(env, prefix) {
  nms <- ls(env, all.names = TRUE)
  hit <- nms[startsWith(nms, prefix)]
  if (!length(hit)) return(NA_character_)
  hit[[1L]]
}

source_labels <- c("USGS", "GloFAS", "NWS3.0")

matrix_rows_summary <- function(mat, quantity, block, meta, dates = NULL) {
  if (is.null(mat)) return(data.frame())
  mat <- as.matrix(mat)
  rows <- vector("list", nrow(mat))
  for (j in seq_len(nrow(mat))) {
    s <- finite_summary(mat[j, ])
    rows[[j]] <- cbind(
      meta,
      data.frame(
        block = block,
        source_index = j,
        source = if (j <= length(source_labels)) source_labels[[j]] else paste0("source_", j),
        quantity = quantity,
        first_date = first_date_chr(dates),
        last_date = last_date_chr(dates, ncol(mat))
      ),
      s
    )
  }
  bind_rows(rows)
}

matrix_top_cells <- function(mat, quantity, block, meta, dates = NULL, n_top = 12L) {
  if (is.null(mat)) return(data.frame())
  mat <- as.matrix(mat)
  vals <- num(mat)
  finite <- is.finite(vals)
  if (!any(finite)) return(data.frame())
  ord <- order(abs(vals[finite]), decreasing = TRUE)
  finite_idx <- which(finite)[ord[seq_len(min(n_top, length(ord)))]]
  rc <- arrayInd(finite_idx, dim(mat))
  data.frame(
    meta,
    block = block,
    source_index = rc[, 1L],
    source = source_labels[pmin(rc[, 1L], length(source_labels))],
    quantity = quantity,
    time_index = rc[, 2L],
    date = if (length(dates)) as.character(dates[pmin(rc[, 2L], length(dates))]) else NA_character_,
    value = vals[finite_idx],
    abs_value = abs(vals[finite_idx])
  )
}

list_matrix_summary <- function(x, quantity, block, meta, run_root) {
  if (is.null(x) || !is.list(x)) return(data.frame())
  rows <- list()
  for (i in seq_along(x)) {
    if (is.null(x[[i]])) next
    source_index <- i + 1L
    source <- if (source_index <= length(source_labels)) source_labels[[source_index]] else paste0("source_", source_index)
    dates <- read_forecast_dates(run_root, source)
    s <- finite_summary(x[[i]])
    rows[[i]] <- cbind(
      meta,
      data.frame(
        block = block,
        source_index = source_index,
        source = source,
        quantity = quantity,
        first_date = first_date_chr(dates),
        last_date = last_date_chr(dates, length(num(x[[i]])))
      ),
      s
    )
  }
  bind_rows(rows)
}

list_matrix_top_cells <- function(x, quantity, block, meta, run_root, n_top = 12L) {
  if (is.null(x) || !is.list(x)) return(data.frame())
  rows <- list()
  for (i in seq_along(x)) {
    if (is.null(x[[i]])) next
    mat <- as.matrix(x[[i]])
    vals <- num(mat)
    finite <- is.finite(vals)
    if (!any(finite)) next
    dims <- dim(mat)
    ord <- order(abs(vals[finite]), decreasing = TRUE)
    finite_idx <- which(finite)[ord[seq_len(min(n_top, length(ord)))]]
    rc <- arrayInd(finite_idx, dims)
    source_index <- i + 1L
    source <- if (source_index <= length(source_labels)) source_labels[[source_index]] else paste0("source_", source_index)
    dates <- read_forecast_dates(run_root, source)
    rows[[length(rows) + 1L]] <- data.frame(
      meta,
      block = block,
      source_index = source_index,
      source = source,
      quantity = quantity,
      time_index = rc[, 1L],
      member_index = rc[, 2L],
      date = if (length(dates)) as.character(dates[pmin(rc[, 1L], length(dates))]) else NA_character_,
      value = vals[finite_idx],
      abs_value = abs(vals[finite_idx])
    )
  }
  bind_rows(rows)
}

diag_array_by_time <- function(arr) {
  if (is.null(arr)) return(NULL)
  d <- dim(arr)
  if (length(d) != 3L) return(NULL)
  out <- matrix(NA_real_, nrow = min(d[1L], d[2L]), ncol = d[3L])
  for (k in seq_len(d[3L])) out[, k] <- diag(arr[, , k, drop = FALSE][, , 1L])
  out
}

gamsig_summary <- function(gs, meta) {
  if (is.null(gs) || !is.list(gs)) return(data.frame())
  fields <- intersect(
    c(
      "E.gam", "V.gam", "E.sigma", "V.sig", "E.inv.sigma",
      "E.c2.invb.absgam2.sigma", "E.c.invb.absgam",
      "E.c.a.invb.absgam", "E.a2.invb.inv.sigma",
      "E.invb.inv.sigma", "E.a.invb.inv.sigma",
      "E.log.sig.b", "E.log.sig", "entrop"
    ),
    names(gs)
  )
  rows <- list()
  for (field in fields) {
    v <- num(gs[[field]])
    for (j in seq_along(v)) {
      rows[[length(rows) + 1L]] <- data.frame(
        meta,
        source_index = j,
        source = if (j <= length(source_labels)) source_labels[[j]] else paste0("source_", j),
        quantity = field,
        value = v[[j]]
      )
    }
  }
  extra <- c("near_zero_fallback_count", "near_zero_fallback_iters", "last_near_zero_fallback_reason", "last_near_zero_fallback_iter")
  for (field in intersect(extra, names(gs))) {
    rows[[length(rows) + 1L]] <- data.frame(
      meta,
      source_index = NA_integer_,
      source = NA_character_,
      quantity = field,
      value = paste(gs[[field]], collapse = ";")
    )
  }
  bind_rows(rows)
}

seq_summary <- function(seq_mat, quantity, meta) {
  if (is.null(seq_mat)) return(data.frame())
  mat <- as.matrix(seq_mat)
  rows <- list()
  for (j in seq_len(nrow(mat))) {
    v <- num(mat[j, ])
    finite <- is.finite(v)
    last_val <- if (any(finite)) tail(v[finite], 1L) else NA_real_
    first_val <- if (any(finite)) v[which(finite)[[1L]]] else NA_real_
    rows[[j]] <- cbind(
      meta,
      data.frame(
        quantity = quantity,
        source_index = if (nrow(mat) == 1L) NA_integer_ else j,
        source = if (nrow(mat) == 1L) NA_character_ else source_labels[pmin(j, length(source_labels))],
        first = first_val,
        last = last_val,
        delta = last_val - first_val
      ),
      finite_summary(v)
    )
  }
  bind_rows(rows)
}

seq_long <- function(elbo, gamma, sigma, eigen, meta) {
  n_iter <- max(
    c(ncol(as.matrix(elbo)), ncol(as.matrix(gamma)), ncol(as.matrix(sigma)), ncol(as.matrix(eigen))),
    na.rm = TRUE
  )
  if (!is.finite(n_iter) || n_iter <= 0L) return(data.frame())
  rows <- list()
  if (!is.null(elbo)) {
    rows[[length(rows) + 1L]] <- data.frame(meta, iter = seq_len(ncol(as.matrix(elbo))) - 1L, source_index = NA_integer_, source = NA_character_, quantity = "elbo", value = num(as.matrix(elbo)[1L, ]))
  }
  for (payload in list(gamma = gamma, sigma = sigma)) {
    nm <- names(payload)
  }
  add_mat <- function(mat, quantity) {
    if (is.null(mat)) return(NULL)
    mat <- as.matrix(mat)
    out <- vector("list", nrow(mat))
    for (j in seq_len(nrow(mat))) {
      out[[j]] <- data.frame(
        meta,
        iter = seq_len(ncol(mat)) - 1L,
        source_index = j,
        source = source_labels[pmin(j, length(source_labels))],
        quantity = quantity,
        value = num(mat[j, ])
      )
    }
    bind_rows(out)
  }
  rows[[length(rows) + 1L]] <- add_mat(gamma, "gamma")
  rows[[length(rows) + 1L]] <- add_mat(sigma, "sigma")
  if (!is.null(eigen)) {
    rows[[length(rows) + 1L]] <- data.frame(meta, iter = seq_len(ncol(as.matrix(eigen))) - 1L, source_index = NA_integer_, source = NA_character_, quantity = "min_abs_eigen", value = num(as.matrix(eigen)[1L, ]))
  }
  bind_rows(rows)
}

theta_summary <- function(theta, meta, history_dates, cutoff_date) {
  if (is.null(theta) || !is.list(theta)) return(list(summary = data.frame(), window = data.frame()))
  rows <- list()
  if (!is.null(theta$exps)) {
    rows[[length(rows) + 1L]] <- matrix_rows_summary(theta$exps, "theta.exps", "history_plus_forecast", meta)
  }
  if (!is.null(theta$exps2)) {
    rows[[length(rows) + 1L]] <- matrix_rows_summary(theta$exps2, "theta.exps2", "history_plus_forecast", meta)
  }
  if (!is.null(theta$sm)) {
    sm <- as.matrix(theta$sm)
    state_norm <- sqrt(colSums(sm^2, na.rm = TRUE) / pmax(nrow(sm), 1L))
    rows[[length(rows) + 1L]] <- cbind(meta, data.frame(block = "history", source_index = NA_integer_, source = NA_character_, quantity = "theta.sm_rms_state_norm", first_date = NA_character_, last_date = NA_character_), finite_summary(state_norm))
  }
  window_rows <- list()
  if (!is.null(theta$exps) && length(history_dates)) {
    exps <- as.matrix(theta$exps)
    all_dates <- history_dates
    if (ncol(exps) > length(all_dates)) {
      fc_n <- ncol(exps) - length(all_dates)
      all_dates <- c(all_dates, cutoff_date + seq_len(fc_n))
    }
    keep <- which(all_dates >= cutoff_date - as.integer(get("window_days_global", envir = .GlobalEnv)) & all_dates <= cutoff_date + as.integer(get("window_days_global", envir = .GlobalEnv)))
    keep <- keep[keep <= ncol(exps)]
    if (length(keep)) {
      for (j in seq_len(nrow(exps))) {
        window_rows[[length(window_rows) + 1L]] <- data.frame(
          meta,
          date = as.character(all_dates[keep]),
          day_rel = as.integer(all_dates[keep] - cutoff_date),
          source_index = j,
          source = source_labels[pmin(j, length(source_labels))],
          quantity = "theta.exps",
          value = num(exps[j, keep])
        )
      }
    }
  }
  if (!is.null(theta$sm) && length(history_dates)) {
    sm <- as.matrix(theta$sm)
    state_norm <- sqrt(colSums(sm^2, na.rm = TRUE) / pmax(nrow(sm), 1L))
    keep <- which(history_dates >= cutoff_date - as.integer(get("window_days_global", envir = .GlobalEnv)) & history_dates <= cutoff_date)
    keep <- keep[keep <= length(state_norm)]
    if (length(keep)) {
      window_rows[[length(window_rows) + 1L]] <- data.frame(
        meta,
        date = as.character(history_dates[keep]),
        day_rel = as.integer(history_dates[keep] - cutoff_date),
        source_index = NA_integer_,
        source = NA_character_,
        quantity = "theta.sm_rms_state_norm",
        value = num(state_norm[keep])
      )
    }
  }
  list(summary = bind_rows(rows), window = bind_rows(window_rows))
}

latent_window <- function(sts, uts, ext_f, ext_q, meta, history_dates, cutoff_date) {
  if (!length(history_dates)) return(data.frame())
  keep <- which(history_dates >= cutoff_date - as.integer(get("window_days_global", envir = .GlobalEnv)) & history_dates <= cutoff_date)
  rows <- list()
  add_matrix <- function(mat, quantity) {
    if (is.null(mat) || !length(keep)) return()
    mat <- as.matrix(mat)
    kk <- keep[keep <= ncol(mat)]
    for (j in seq_len(nrow(mat))) {
      rows[[length(rows) + 1L]] <<- data.frame(
        meta,
        block = "history",
        date = as.character(history_dates[kk]),
        day_rel = as.integer(history_dates[kk] - cutoff_date),
        source_index = j,
        source = source_labels[pmin(j, length(source_labels))],
        quantity = quantity,
        value = num(mat[j, kk])
      )
    }
  }
  add_matrix(sts$E.sts, "E_s")
  add_matrix(sts$E.sts2, "E_s2")
  add_matrix(uts$E.uts, "E_u")
  add_matrix(uts$E.inv.uts, "E_inv_u")
  add_matrix(ext_f, "FFF")
  add_matrix(diag_array_by_time(ext_q), "QQQ_diag")
  bind_rows(rows)
}

forecast_window <- function(sts_f, uts_f, ext_f_f, ext_q_f, meta, run_root, cutoff_date) {
  rows <- list()
  add_list <- function(x, quantity) {
    if (is.null(x) || !is.list(x)) return()
    for (i in seq_along(x)) {
      if (is.null(x[[i]])) next
      mat <- as.matrix(x[[i]])
      if (!length(mat) || is.null(dim(mat))) next
      source_index <- i + 1L
      source <- if (source_index <= length(source_labels)) source_labels[[source_index]] else paste0("source_", source_index)
      dates <- read_forecast_dates(run_root, source)
      if (!length(dates)) dates <- cutoff_date + seq_len(nrow(mat))
      keep <- which(dates >= cutoff_date + 1L & dates <= cutoff_date + as.integer(get("window_days_global", envir = .GlobalEnv)))
      keep <- keep[keep <= nrow(mat)]
      if (!length(keep)) next
      for (tt in keep) {
        rows[[length(rows) + 1L]] <<- data.frame(
          meta,
          block = "forecast",
          date = as.character(dates[[tt]]),
          day_rel = as.integer(dates[[tt]] - cutoff_date),
          source_index = source_index,
          source = source,
          quantity = quantity,
          member_index = seq_len(ncol(mat)),
          value = num(mat[tt, ])
        )
      }
    }
  }
  add_list(sts_f$E.sts, "E_s")
  add_list(sts_f$E.sts2, "E_s2")
  add_list(uts_f$E.uts, "E_u")
  add_list(uts_f$E.inv.uts, "E_inv_u")
  add_list(ext_f_f, "FFF")
  add_list(ext_q_f, "QQQ_diag")
  bind_rows(rows)
}

parse_progress_log <- function(log_path, meta, tt) {
  if (!file.exists(log_path)) return(data.frame())
  lines <- readLines(log_path, warn = FALSE)
  lines <- lines[grepl("\\[gamsig_progress\\]", lines, fixed = FALSE)]
  if (!length(lines)) return(data.frame())
  rows <- vector("list", length(lines))
  grab <- function(pattern, x) {
    m <- regexec(pattern, x, perl = TRUE)
    got <- regmatches(x, m)[[1L]]
    if (length(got) >= 2L) got[[2L]] else NA_character_
  }
  parse_vec <- function(x) {
    raw <- grab("\\[([^\\]]+)\\]", x)
    if (is.na(raw)) return(numeric(0))
    num(strsplit(raw, ",", fixed = TRUE)[[1L]])
  }
  for (i in seq_along(lines)) {
    line <- lines[[i]]
    rows[[i]] <- data.frame(
      meta,
      iter = as.integer(grab("iter=([0-9]+)", line)),
      elbo = num(grab("elbo=([-+0-9.eE]+)", line)),
      sigma_exp = num(grab("sigma_exp=([-+0-9.eE]+)", line)),
      gamma_exp = num(grab("gamma_exp=([-+0-9.eE]+)", line)),
      state_norm_sq = num(grab("state_norm_sq=([-+0-9.eE]+)", line)),
      state_norm_sq_per_T = num(grab("state_norm_sq=([-+0-9.eE]+)", line)) / tt,
      crit_state_norm_sq = num(grab("crit_state_norm_sq=([-+0-9.eE]+)", line)),
      frozen = grab("frozen=([^ ]+)", line)
    )
  }
  bind_rows(rows)
}

read_iteration_health <- function(rdata_path, meta) {
  diag_path <- file.path(dirname(rdata_path), "diagnostics", "vb_iteration", "fit_iteration_health_summary.csv")
  health <- safe_read_csv(diag_path)
  if (is.null(health) || !nrow(health)) return(data.frame())
  meta_cols <- names(meta)
  health <- health[, setdiff(names(health), meta_cols), drop = FALSE]
  cbind(meta, diagnostic_path = diag_path, health)
}

write_csv <- function(x, path) {
  if (is.null(x) || !is.data.frame(x) || !nrow(x)) {
    utils::write.csv(data.frame(), path, row.names = FALSE)
  } else {
    utils::write.csv(x, path, row.names = FALSE)
  }
}

fill_missing_group_values <- function(df, group_cols, missing_label = "__missing__") {
  if (is.null(df) || !is.data.frame(df) || !nrow(df) || !length(group_cols)) return(df)
  for (nm in intersect(group_cols, names(df))) {
    vals <- df[[nm]]
    missing <- is.na(vals)
    if (!any(missing)) next
    if (is.character(vals) || is.factor(vals)) {
      vals <- as.character(vals)
      vals[missing] <- missing_label
      df[[nm]] <- vals
    }
  }
  df
}

plot_trace <- function(trace, quantity, out_file, ylab = quantity) {
  dat <- trace[trace$quantity == quantity & is.finite(trace$value), , drop = FALSE]
  if (!nrow(dat)) return(invisible(FALSE))
  png(out_file, width = 3200, height = 1800, res = 260)
  on.exit(dev.off(), add = TRUE)
  qvals <- sort(unique(dat$q))
  cols <- grDevices::hcl.colors(max(length(qvals), 2L), "Dark 3")
  names(cols) <- qvals
  ylim <- range(dat$value, na.rm = TRUE)
  plot(dat$iter, dat$value, type = "n", xlab = "Iteration", ylab = ylab, main = paste(quantity, "trace by run / quantile"))
  for (rid in unique(dat$run_id)) {
    for (qv in qvals) {
      sub <- dat[dat$run_id == rid & dat$q == qv, , drop = FALSE]
      if (!nrow(sub)) next
      if ("source" %in% names(sub) && any(!is.na(sub$source))) {
        for (src in unique(sub$source[!is.na(sub$source)])) {
          ss <- sub[sub$source == src, , drop = FALSE]
          lines(ss$iter, ss$value, col = cols[[as.character(qv)]], lwd = 1.4, lty = match(src, unique(sub$source[!is.na(sub$source)])))
        }
      } else {
        lines(sub$iter, sub$value, col = cols[[as.character(qv)]], lwd = 1.6)
      }
    }
  }
  legend("topright", legend = paste0("q", qvals), col = cols, lwd = 2, bty = "n", cex = 0.8)
  invisible(TRUE)
}

plot_progress_metric <- function(progress, metric, out_file, ylab = metric) {
  dat <- progress[is.finite(progress[[metric]]), , drop = FALSE]
  if (!nrow(dat)) return(invisible(FALSE))
  png(out_file, width = 3200, height = 1800, res = 260)
  on.exit(dev.off(), add = TRUE)
  qvals <- sort(unique(dat$q))
  cols <- grDevices::hcl.colors(max(length(qvals), 2L), "Dark 3")
  names(cols) <- qvals
  plot(dat$iter, dat[[metric]], type = "n", xlab = "Iteration", ylab = ylab, main = paste(metric, "from fit logs"))
  for (rid in unique(dat$run_id)) {
    for (qv in qvals) {
      sub <- dat[dat$run_id == rid & dat$q == qv, , drop = FALSE]
      if (!nrow(sub)) next
      lines(sub$iter, sub[[metric]], col = cols[[as.character(qv)]], lwd = 1.5, lty = match(rid, unique(dat$run_id)))
    }
  }
  legend("topright", legend = paste0("q", qvals), col = cols, lwd = 2, bty = "n", cex = 0.8)
  invisible(TRUE)
}

plot_health_metric <- function(health, metric, out_file, ylab = metric) {
  if (is.null(health) || !is.data.frame(health) || !nrow(health) || !metric %in% names(health)) {
    return(invisible(FALSE))
  }
  dat <- health[is.finite(num(health[[metric]])), , drop = FALSE]
  if (!nrow(dat)) return(invisible(FALSE))
  dat[[metric]] <- num(dat[[metric]])
  png(out_file, width = 3200, height = 1800, res = 260)
  on.exit(dev.off(), add = TRUE)
  qvals <- sort(unique(dat$q))
  cols <- grDevices::hcl.colors(max(length(qvals), 2L), "Dark 3")
  names(cols) <- qvals
  plot(dat$iter, dat[[metric]], type = "n", xlab = "Iteration", ylab = ylab, main = paste(metric, "from fit iteration health CSV"))
  for (rid in unique(dat$run_id)) {
    for (qv in qvals) {
      sub <- dat[dat$run_id == rid & dat$q == qv, , drop = FALSE]
      if (!nrow(sub)) next
      lines(sub$iter, sub[[metric]], col = cols[[as.character(qv)]], lwd = 1.5, lty = match(rid, unique(dat$run_id)))
    }
  }
  legend("topright", legend = paste0("q", qvals), col = cols, lwd = 2, bty = "n", cex = 0.8)
  invisible(TRUE)
}

plot_window_quantity <- function(window_df, run_id, quantity, out_file) {
  dat <- window_df[window_df$run_id == run_id & window_df$quantity == quantity & is.finite(window_df$value), , drop = FALSE]
  if (!nrow(dat)) return(invisible(FALSE))
  png(out_file, width = 3200, height = 1800, res = 260)
  on.exit(dev.off(), add = TRUE)
  qvals <- sort(unique(dat$q))
  cols <- grDevices::hcl.colors(max(length(qvals), 2L), "Dark 3")
  names(cols) <- qvals
  ylim <- range(dat$value, na.rm = TRUE)
  plot(dat$day_rel, dat$value, type = "n", xlab = "Day relative to cutoff", ylab = quantity, main = paste(quantity, "around cutoff:", run_id), ylim = ylim)
  abline(v = 0, lty = 3, col = "gray45")
  for (src in unique(dat$source[!is.na(dat$source)])) {
    for (qv in qvals) {
      sub <- dat[dat$source == src & dat$q == qv, , drop = FALSE]
      if (!nrow(sub)) next
      lines(sub$day_rel, sub$value, col = cols[[as.character(qv)]], lwd = ifelse(qv %in% c(5L, 50L, 95L), 1.8, 1.0), lty = match(src, unique(dat$source[!is.na(dat$source)])))
    }
  }
  legend("topright", legend = paste0("q", qvals), col = cols, lwd = 2, bty = "n", cex = 0.75)
  invisible(TRUE)
}

plot_forecast_window_quantity <- function(window_df, run_id, quantity, out_file) {
  dat <- window_df[window_df$run_id == run_id & window_df$quantity == quantity & is.finite(window_df$value), , drop = FALSE]
  if (!nrow(dat)) return(invisible(FALSE))
  dat <- fill_missing_group_values(dat, c("run_id", "q", "source", "day_rel"))
  agg <- stats::aggregate(
    value ~ run_id + q + source + day_rel,
    data = dat,
    FUN = function(x) stats::median(x, na.rm = TRUE)
  )
  if (!nrow(agg)) return(invisible(FALSE))
  png(out_file, width = 3200, height = 1800, res = 260)
  on.exit(dev.off(), add = TRUE)
  qvals <- sort(unique(agg$q))
  cols <- grDevices::hcl.colors(max(length(qvals), 2L), "Dark 3")
  names(cols) <- qvals
  ylim <- range(agg$value, na.rm = TRUE)
  plot(agg$day_rel, agg$value, type = "n", xlab = "Forecast day relative to cutoff", ylab = paste(quantity, "member median"), main = paste(quantity, "forecast member median:", run_id), ylim = ylim)
  for (src in unique(agg$source[!is.na(agg$source)])) {
    for (qv in qvals) {
      sub <- agg[agg$source == src & agg$q == qv, , drop = FALSE]
      if (!nrow(sub)) next
      lines(sub$day_rel, sub$value, col = cols[[as.character(qv)]], lwd = ifelse(qv %in% c(5L, 50L, 95L), 1.8, 1.0), lty = match(src, unique(agg$source[!is.na(agg$source)])))
    }
  }
  legend("topright", legend = paste0("q", qvals), col = cols, lwd = 2, bty = "n", cex = 0.75)
  invisible(TRUE)
}

read_fit_usgs_series <- function(run_root) {
  df <- safe_read_csv(file.path(run_root, "fit", "inputs", "retros_fit_adapter.csv"))
  if (is.null(df)) df <- safe_read_csv(file.path(run_root, "inputs", "shared", "retros", "retros.csv"))
  if (is.null(df)) return(data.frame(date = as.Date(character(0)), usgs_log1p = numeric(0)))
  date_col <- intersect(c("Date", "date", "time", "timestamp"), names(df))
  val_col <- intersect(c("USGS", "usgs", "usgs_log1p", "value"), names(df))
  if (!length(date_col) || !length(val_col)) return(data.frame(date = as.Date(character(0)), usgs_log1p = numeric(0)))
  data.frame(
    date = suppressWarnings(as.Date(df[[date_col[[1L]]]])),
    usgs_log1p = num(df[[val_col[[1L]]]]),
    stringsAsFactors = FALSE
  )
}

read_usgs_log1p_series <- function(run_root) {
  hist <- read_fit_usgs_series(run_root)
  raw <- safe_read_csv(file.path(run_root, "inputs", "shared", "usgs", "usgs_daily.csv"))
  if (is.null(raw)) return(hist)
  date_col <- intersect(c("date", "Date", "time", "timestamp"), names(raw))
  if (!length(date_col)) return(hist)
  val_col <- intersect(c("discharge_cms", "cms", "USGS", "usgs_log1p", "discharge_cfs"), names(raw))
  if (!length(val_col)) return(hist)
  vals <- num(raw[[val_col[[1L]]]])
  if (identical(val_col[[1L]], "discharge_cfs")) {
    vals <- vals * 0.028316846592
  }
  if (!grepl("log1p|USGS", val_col[[1L]], ignore.case = TRUE)) {
    vals <- log1p(pmax(vals, 0))
  }
  out <- data.frame(
    date = suppressWarnings(as.Date(raw[[date_col[[1L]]]])),
    usgs_log1p = vals,
    stringsAsFactors = FALSE
  )
  if (!nrow(hist)) return(out)
  out <- out[!is.na(out$date), , drop = FALSE]
  hist <- hist[!is.na(hist$date), , drop = FALSE]
  combined <- rbind(hist, out[!out$date %in% hist$date, , drop = FALSE])
  combined[order(combined$date), , drop = FALSE]
}

lookup_usgs_log1p <- function(series, dates) {
  if (is.null(series) || !nrow(series) || !length(dates)) return(rep(NA_real_, length(dates)))
  idx <- match(as.Date(dates), as.Date(series$date))
  out <- rep(NA_real_, length(dates))
  ok <- !is.na(idx)
  out[ok] <- num(series$usgs_log1p[idx[ok]])
  out
}

read_harmonic_count <- function(run_root, p = NA_integer_) {
  candidates <- c(
    file.path(run_root, "inputs", "shared", "parameters", "parameters.txt"),
    file.path(run_root, "fit", "inputs", "parameters.txt"),
    file.path(run_root, "resolved_config.yaml")
  )
  candidates <- candidates[file.exists(candidates)]
  for (path in candidates) {
    txt <- tryCatch(readLines(path, warn = FALSE), error = function(e) character(0))
    hit <- grep("harmonics", txt, ignore.case = TRUE, value = TRUE)
    if (!length(hit)) next
    line <- hit[[1L]]
    inside <- sub(".*c\\(([^)]*)\\).*", "\\1", line)
    if (identical(inside, line)) next
    vals <- trimws(strsplit(inside, ",", fixed = TRUE)[[1L]])
    vals <- vals[nzchar(vals)]
    return(length(vals))
  }
  p_use <- suppressWarnings(as.integer(p))
  if (is.finite(p_use) && p_use > 1L) {
    return(as.integer(floor((p_use - 1L) / 2L)))
  }
  NA_integer_
}

infer_transfer_layout <- function(theta_obj, p_hint = NA_integer_) {
  out <- list(
    valid = FALSE,
    reason = "unavailable",
    J = NA_integer_,
    p = NA_integer_,
    ppx = NA_integer_,
    TT_hist = NA_integer_,
    core_hist_dim = NA_integer_,
    seg_contract = data.frame()
  )

  if (!is.list(theta_obj) || !is.matrix(theta_obj$sm) || !is.list(theta_obj$sm_ens)) {
    out$reason <- "missing_state_objects"
    return(out)
  }

  j_total <- length(theta_obj$sm_ens)
  if (!is.finite(j_total) || j_total < 1L) {
    out$reason <- "no_forecast_segments"
    return(out)
  }
  j_total <- as.integer(j_total)

  p_val <- suppressWarnings(as.integer(p_hint))
  if (!is.finite(p_val) || p_val <= 0L) {
    if (j_total >= 2L) {
      d1 <- nrow(as.matrix(theta_obj$sm_ens[[1L]]))
      d2 <- nrow(as.matrix(theta_obj$sm_ens[[2L]]))
      p_val <- suppressWarnings(as.integer(abs(d1 - d2)))
    }
  }
  if (!is.finite(p_val) || p_val <= 0L) {
    out$reason <- "cannot_infer_p"
    return(out)
  }

  full_hist_dim <- nrow(theta_obj$sm)
  core_hist_dim <- as.integer(p_val * (j_total + 1L))
  ppx_val <- as.integer(full_hist_dim - core_hist_dim)
  if (!is.finite(ppx_val) || ppx_val <= 0L) {
    out$reason <- "no_transfer_block_detected"
    return(out)
  }

  seg_rows <- vapply(theta_obj$sm_ens, function(x) nrow(as.matrix(x)), integer(1))
  seg_cols <- vapply(theta_obj$sm_ens, function(x) ncol(as.matrix(x)), integer(1))
  seg_idx <- seq_len(j_total)
  active_source_count <- as.integer(j_total - seg_idx + 1L)
  expected_core <- as.integer(p_val * (active_source_count + 1L))
  expected_with_transfer <- expected_core + ppx_val
  transfer_retained <- seg_rows >= expected_with_transfer
  active_sources <- vapply(active_source_count, function(n) paste(source_labels[seq.int(2L, n + 1L)], collapse = "+"), character(1))

  seg_contract <- data.frame(
    segment = seg_idx,
    active_source_count = active_source_count,
    active_sources = active_sources,
    day_start = cumsum(c(1L, head(seg_cols, -1L))),
    day_end = cumsum(seg_cols),
    segment_horizon = seg_cols,
    segment_state_dim = seg_rows,
    expected_core_state_dim = expected_core,
    expected_transfer_state_dim = expected_with_transfer,
    transfer_retained = transfer_retained,
    stringsAsFactors = FALSE
  )

  out$valid <- TRUE
  out$reason <- "ok"
  out$J <- j_total
  out$p <- p_val
  out$ppx <- ppx_val
  out$TT_hist <- ncol(theta_obj$sm)
  out$core_hist_dim <- core_hist_dim
  out$seg_contract <- seg_contract
  out
}

safe_diag_sd <- function(cube_arr, idx, n_time) {
  out <- rep(NA_real_, n_time)
  if (!is.array(cube_arr) || length(dim(cube_arr)) != 3L || n_time <= 0L) return(out)
  if (idx < 1L || idx > dim(cube_arr)[1L] || idx > dim(cube_arr)[2L]) return(out)
  t_use <- min(n_time, dim(cube_arr)[3L])
  if (t_use <= 0L) return(out)
  vv <- as.numeric(cube_arr[idx, idx, seq_len(t_use)])
  out[seq_len(t_use)] <- sqrt(pmax(vv, 0))
  out
}

safe_linear_sd <- function(cube_arr, w, t_idx) {
  if (!is.array(cube_arr) || length(dim(cube_arr)) != 3L) return(NA_real_)
  if (!is.numeric(w) || length(w) != dim(cube_arr)[1L] || dim(cube_arr)[1L] != dim(cube_arr)[2L]) return(NA_real_)
  tt <- suppressWarnings(as.integer(t_idx))
  if (!is.finite(tt) || tt < 1L || tt > dim(cube_arr)[3L]) return(NA_real_)
  s <- matrix(
    as.numeric(cube_arr[, , tt, drop = TRUE]),
    nrow = dim(cube_arr)[1L],
    ncol = dim(cube_arr)[2L]
  )
  v <- suppressWarnings(as.numeric(t(w) %*% s %*% w))
  if (!is.finite(v)) return(NA_real_)
  sqrt(max(v, 0))
}

infer_structure_indices <- function(p, harmonic_count) {
  p_use <- suppressWarnings(as.integer(p))
  n_harm <- suppressWarnings(as.integer(harmonic_count))
  if (!is.finite(p_use) || p_use <= 0L) {
    return(list(trend_idx = integer(0), season_idx = integer(0), ff_base = numeric(0), harmonic_count = NA_integer_))
  }
  if (!is.finite(n_harm) || n_harm < 0L || 2L * n_harm > p_use) {
    n_harm <- if (p_use %% 2L == 1L) as.integer((p_use - 1L) / 2L) else as.integer(p_use / 2L)
  }
  trend_dim <- p_use - 2L * n_harm
  if (!is.finite(trend_dim) || trend_dim < 0L) trend_dim <- 0L
  trend_idx <- if (trend_dim > 0L) seq_len(trend_dim) else integer(0)
  season_idx <- if (trend_dim < p_use) seq.int(trend_dim + 1L, p_use) else integer(0)
  ff_base <- rep(0, p_use)
  if (trend_dim > 0L) ff_base[1L] <- 1
  if (length(season_idx)) {
    pair_starts <- season_idx[seq.int(1L, length(season_idx), by = 2L)]
    ff_base[pair_starts] <- 1
  }
  list(
    trend_idx = trend_idx,
    season_idx = season_idx,
    ff_base = ff_base,
    harmonic_count = n_harm
  )
}

forecast_state_dates <- function(run_root, cutoff_date, horizon) {
  h <- suppressWarnings(as.integer(horizon))
  if (!is.finite(h) || h <= 0L) return(as.Date(character(0)))
  dates <- read_forecast_dates(run_root, "GloFAS")
  if (length(dates) >= h) return(as.Date(dates[seq_len(h)]))
  as.Date(cutoff_date) + seq_len(h)
}

component_empty <- function(meta, reason) {
  list(
    wide = data.frame(),
    long = data.frame(),
    layout = data.frame(meta, valid = FALSE, reason = reason),
    diagnostics = data.frame(meta, reason = reason)
  )
}

build_component_decomposition <- function(theta, meta, run_root, history_dates, cutoff_date, window_days) {
  if (is.null(theta) || !is.list(theta)) return(component_empty(meta, "missing_theta"))
  layout <- infer_transfer_layout(theta)
  if (!isTRUE(layout$valid)) return(component_empty(meta, layout$reason))

  j_total <- layout$J
  p <- layout$p
  ppx <- layout$ppx
  tt_hist <- layout$TT_hist
  core_hist_dim <- layout$core_hist_dim
  seg_contract <- layout$seg_contract
  h_seg <- seg_contract$segment_horizon
  h_fore <- sum(h_seg)
  harm_n <- read_harmonic_count(run_root, p)
  idx_split <- infer_structure_indices(p, harm_n)
  ff_base <- idx_split$ff_base
  trend_idx <- idx_split$trend_idx
  season_idx <- idx_split$season_idx

  hist_dates <- as.Date(history_dates)
  if (length(hist_dates) >= tt_hist) hist_dates <- hist_dates[seq_len(tt_hist)]
  if (length(hist_dates) < tt_hist) hist_dates <- c(hist_dates, rep(as.Date(NA), tt_hist - length(hist_dates)))
  keep_hist <- which(hist_dates >= as.Date(cutoff_date) - as.integer(window_days) & hist_dates <= as.Date(cutoff_date))
  keep_hist <- keep_hist[keep_hist <= tt_hist]
  fore_dates <- forecast_state_dates(run_root, cutoff_date, h_fore)
  usgs_series <- read_usgs_log1p_series(run_root)

  sm_hist <- as.matrix(theta$sm)
  sC_hist <- theta$sC
  exps <- if (!is.null(theta$exps)) as.matrix(theta$exps) else matrix(NA_real_, nrow = 3L, ncol = tt_hist + h_fore)
  exps2 <- if (!is.null(theta$exps2)) as.matrix(theta$exps2) else matrix(NA_real_, nrow = 3L, ncol = tt_hist + h_fore)

  row_template <- function(n) {
    data.frame(
      phase = rep(NA_character_, n),
      date = rep(NA_character_, n),
      day_rel = rep(NA_integer_, n),
      time_index = rep(NA_integer_, n),
      segment = rep(NA_integer_, n),
      active_sources = rep(NA_character_, n),
      p = rep(p, n),
      ppx = rep(ppx, n),
      harmonic_count = rep(idx_split$harmonic_count, n),
      trend_state_dim = rep(length(trend_idx), n),
      season_state_dim = rep(length(season_idx), n),
      mu_usgs_state = rep(NA_real_, n),
      mu_usgs_lower_95 = rep(NA_real_, n),
      mu_usgs_upper_95 = rep(NA_real_, n),
      theta_exps_usgs = rep(NA_real_, n),
      theta_exps2_usgs = rep(NA_real_, n),
      mu_glofas_state = rep(NA_real_, n),
      mu_glofas_lower_95 = rep(NA_real_, n),
      mu_glofas_upper_95 = rep(NA_real_, n),
      theta_exps_glofas = rep(NA_real_, n),
      theta_exps2_glofas = rep(NA_real_, n),
      mu_nws_state = rep(NA_real_, n),
      mu_nws_lower_95 = rep(NA_real_, n),
      mu_nws_upper_95 = rep(NA_real_, n),
      theta_exps_nws = rep(NA_real_, n),
      theta_exps2_nws = rep(NA_real_, n),
      agg_discrep_glofas = rep(NA_real_, n),
      agg_discrep_glofas_lower_95 = rep(NA_real_, n),
      agg_discrep_glofas_upper_95 = rep(NA_real_, n),
      agg_discrep_nws = rep(NA_real_, n),
      agg_discrep_nws_lower_95 = rep(NA_real_, n),
      agg_discrep_nws_upper_95 = rep(NA_real_, n),
      zeta = rep(NA_real_, n),
      zeta_lower_95 = rep(NA_real_, n),
      zeta_upper_95 = rep(NA_real_, n),
      trend = rep(NA_real_, n),
      trend_lower_95 = rep(NA_real_, n),
      trend_upper_95 = rep(NA_real_, n),
      season = rep(NA_real_, n),
      season_lower_95 = rep(NA_real_, n),
      season_upper_95 = rep(NA_real_, n),
      mu_without_transfer = rep(NA_real_, n),
      mu_without_transfer_lower_95 = rep(NA_real_, n),
      mu_without_transfer_upper_95 = rep(NA_real_, n),
      usgs_observed = rep(NA_real_, n),
      state_rms_norm = rep(NA_real_, n),
      identity_err_glofas = rep(NA_real_, n),
      identity_err_nws = rep(NA_real_, n),
      exps_state_err_usgs = rep(NA_real_, n),
      exps_state_err_glofas = rep(NA_real_, n),
      exps_state_err_nws = rep(NA_real_, n),
      stringsAsFactors = FALSE
    )
  }

  fill_row <- function(out, ii, mt, sC_obj, sC_t, phase, date, day_rel, time_index, segment, active_sources, core_dim_current, active_count) {
    theta_idx <- seq_len(p)
    delta_g_idx <- if (active_count >= 1L) seq.int(p + 1L, 2L * p) else integer(0)
    delta_n_idx <- if (active_count >= 2L) seq.int(2L * p + 1L, 3L * p) else integer(0)
    zeta_idx <- core_dim_current + 1L
    has_transfer <- zeta_idx <= length(mt)

    base_no_transfer <- sum(ff_base * mt[theta_idx])
    trend_mean <- if (length(trend_idx)) sum(ff_base[trend_idx] * mt[trend_idx]) else NA_real_
    season_mean <- if (length(season_idx)) sum(ff_base[season_idx] * mt[season_idx]) else 0
    zeta_mean <- if (has_transfer) mt[zeta_idx] else 0
    disc_g_mean <- if (length(delta_g_idx) == p && max(delta_g_idx) <= length(mt)) sum(ff_base * mt[delta_g_idx]) else NA_real_
    disc_n_mean <- if (length(delta_n_idx) == p && max(delta_n_idx) <= length(mt)) sum(ff_base * mt[delta_n_idx]) else NA_real_
    mu_usgs <- base_no_transfer + zeta_mean
    mu_g <- if (is.finite(disc_g_mean)) mu_usgs + disc_g_mean else NA_real_
    mu_n <- if (is.finite(disc_n_mean)) mu_usgs + disc_n_mean else NA_real_

    w_usgs <- rep(0, length(mt)); w_usgs[theta_idx] <- ff_base; if (has_transfer) w_usgs[zeta_idx] <- 1
    w_base <- rep(0, length(mt)); w_base[theta_idx] <- ff_base
    w_trend <- rep(0, length(mt)); if (length(trend_idx)) w_trend[trend_idx] <- ff_base[trend_idx]
    w_season <- rep(0, length(mt)); if (length(season_idx)) w_season[season_idx] <- ff_base[season_idx]
    sd_usgs <- safe_linear_sd(sC_obj, w_usgs, sC_t)
    sd_base <- safe_linear_sd(sC_obj, w_base, sC_t)
    sd_trend <- safe_linear_sd(sC_obj, w_trend, sC_t)
    sd_season <- safe_linear_sd(sC_obj, w_season, sC_t)
    z_sd <- if (has_transfer) safe_diag_sd(sC_obj, zeta_idx, sC_t)[sC_t] else 0

    d_g_sd <- NA_real_; d_n_sd <- NA_real_; mu_g_sd <- NA_real_; mu_n_sd <- NA_real_
    if (length(delta_g_idx) == p && max(delta_g_idx) <= length(mt)) {
      w_disc_g <- rep(0, length(mt)); w_disc_g[delta_g_idx] <- ff_base
      d_g_sd <- safe_linear_sd(sC_obj, w_disc_g, sC_t)
      mu_g_sd <- safe_linear_sd(sC_obj, w_usgs + w_disc_g, sC_t)
    }
    if (length(delta_n_idx) == p && max(delta_n_idx) <= length(mt)) {
      w_disc_n <- rep(0, length(mt)); w_disc_n[delta_n_idx] <- ff_base
      d_n_sd <- safe_linear_sd(sC_obj, w_disc_n, sC_t)
      mu_n_sd <- safe_linear_sd(sC_obj, w_usgs + w_disc_n, sC_t)
    }

    col_idx <- time_index
    out$phase[ii] <- phase
    out$date[ii] <- as.character(date)
    out$day_rel[ii] <- as.integer(day_rel)
    out$time_index[ii] <- as.integer(time_index)
    out$segment[ii] <- as.integer(segment)
    out$active_sources[ii] <- active_sources
    out$mu_usgs_state[ii] <- mu_usgs
    out$mu_usgs_lower_95[ii] <- mu_usgs - 1.96 * sd_usgs
    out$mu_usgs_upper_95[ii] <- mu_usgs + 1.96 * sd_usgs
    out$mu_glofas_state[ii] <- mu_g
    out$mu_glofas_lower_95[ii] <- if (is.finite(mu_g_sd)) mu_g - 1.96 * mu_g_sd else NA_real_
    out$mu_glofas_upper_95[ii] <- if (is.finite(mu_g_sd)) mu_g + 1.96 * mu_g_sd else NA_real_
    out$mu_nws_state[ii] <- mu_n
    out$mu_nws_lower_95[ii] <- if (is.finite(mu_n_sd)) mu_n - 1.96 * mu_n_sd else NA_real_
    out$mu_nws_upper_95[ii] <- if (is.finite(mu_n_sd)) mu_n + 1.96 * mu_n_sd else NA_real_
    out$agg_discrep_glofas[ii] <- disc_g_mean
    out$agg_discrep_glofas_lower_95[ii] <- if (is.finite(d_g_sd)) disc_g_mean - 1.96 * d_g_sd else NA_real_
    out$agg_discrep_glofas_upper_95[ii] <- if (is.finite(d_g_sd)) disc_g_mean + 1.96 * d_g_sd else NA_real_
    out$agg_discrep_nws[ii] <- disc_n_mean
    out$agg_discrep_nws_lower_95[ii] <- if (is.finite(d_n_sd)) disc_n_mean - 1.96 * d_n_sd else NA_real_
    out$agg_discrep_nws_upper_95[ii] <- if (is.finite(d_n_sd)) disc_n_mean + 1.96 * d_n_sd else NA_real_
    out$zeta[ii] <- zeta_mean
    out$zeta_lower_95[ii] <- zeta_mean - 1.96 * z_sd
    out$zeta_upper_95[ii] <- zeta_mean + 1.96 * z_sd
    out$trend[ii] <- trend_mean
    out$trend_lower_95[ii] <- if (is.finite(sd_trend)) trend_mean - 1.96 * sd_trend else NA_real_
    out$trend_upper_95[ii] <- if (is.finite(sd_trend)) trend_mean + 1.96 * sd_trend else NA_real_
    out$season[ii] <- season_mean
    out$season_lower_95[ii] <- if (is.finite(sd_season)) season_mean - 1.96 * sd_season else NA_real_
    out$season_upper_95[ii] <- if (is.finite(sd_season)) season_mean + 1.96 * sd_season else NA_real_
    out$mu_without_transfer[ii] <- base_no_transfer
    out$mu_without_transfer_lower_95[ii] <- base_no_transfer - 1.96 * sd_base
    out$mu_without_transfer_upper_95[ii] <- base_no_transfer + 1.96 * sd_base
    out$state_rms_norm[ii] <- sqrt(sum(mt^2, na.rm = TRUE) / max(length(mt), 1L))
    out$identity_err_glofas[ii] <- mu_g - mu_usgs - disc_g_mean
    out$identity_err_nws[ii] <- mu_n - mu_usgs - disc_n_mean
    if (!is.null(exps) && nrow(exps) >= 1L && col_idx <= ncol(exps)) out$theta_exps_usgs[ii] <- num(exps[1L, col_idx])
    if (!is.null(exps) && nrow(exps) >= 2L && col_idx <= ncol(exps)) out$theta_exps_glofas[ii] <- num(exps[2L, col_idx])
    if (!is.null(exps) && nrow(exps) >= 3L && col_idx <= ncol(exps)) out$theta_exps_nws[ii] <- num(exps[3L, col_idx])
    if (!is.null(exps2) && nrow(exps2) >= 1L && col_idx <= ncol(exps2)) out$theta_exps2_usgs[ii] <- num(exps2[1L, col_idx])
    if (!is.null(exps2) && nrow(exps2) >= 2L && col_idx <= ncol(exps2)) out$theta_exps2_glofas[ii] <- num(exps2[2L, col_idx])
    if (!is.null(exps2) && nrow(exps2) >= 3L && col_idx <= ncol(exps2)) out$theta_exps2_nws[ii] <- num(exps2[3L, col_idx])
    out$exps_state_err_usgs[ii] <- out$theta_exps_usgs[ii] - out$mu_usgs_state[ii]
    out$exps_state_err_glofas[ii] <- out$theta_exps_glofas[ii] - out$mu_glofas_state[ii]
    out$exps_state_err_nws[ii] <- out$theta_exps_nws[ii] - out$mu_nws_state[ii]
    out$usgs_observed[ii] <- lookup_usgs_log1p(usgs_series, as.Date(date))
    out
  }

  hist_out <- row_template(length(keep_hist))
  if (length(keep_hist)) {
    for (ii in seq_along(keep_hist)) {
      tt <- keep_hist[[ii]]
      hist_out <- fill_row(
        hist_out, ii, as.numeric(sm_hist[, tt]), sC_hist, tt,
        "history", hist_dates[[tt]], as.integer(hist_dates[[tt]] - as.Date(cutoff_date)),
        tt, 0L, "USGS+GloFAS+NWS3.0", core_hist_dim, j_total
      )
    }
  }

  fore_out <- row_template(h_fore)
  cursor <- 0L
  if (h_fore > 0L) {
    for (j in seq_len(j_total)) {
      seg_len <- h_seg[[j]]
      if (!is.finite(seg_len) || seg_len <= 0L) next
      sm_seg <- as.matrix(theta$sm_ens[[j]])
      sC_seg <- theta$sC_ens[[j]]
      active_count <- as.integer(j_total - j + 1L)
      core_dim_j <- as.integer(p * (active_count + 1L))
      active_sources <- paste(source_labels[seq.int(2L, active_count + 1L)], collapse = "+")
      for (tt in seq_len(seg_len)) {
        g_idx <- cursor + tt
        fore_out <- fill_row(
          fore_out, g_idx, as.numeric(sm_seg[, tt]), sC_seg, tt,
          "forecast", fore_dates[[g_idx]], as.integer(fore_dates[[g_idx]] - as.Date(cutoff_date)),
          tt_hist + g_idx, j, active_sources, core_dim_j, active_count
        )
      }
      cursor <- cursor + seg_len
    }
  }

  wide <- cbind(meta, rbind(hist_out, fore_out))
  component_cols <- c(
    "mu_usgs_state", "theta_exps_usgs", "mu_glofas_state", "theta_exps_glofas",
    "mu_nws_state", "theta_exps_nws", "agg_discrep_glofas", "agg_discrep_nws",
    "zeta", "trend", "season", "mu_without_transfer", "usgs_observed", "state_rms_norm"
  )
  long_rows <- list()
  for (nm in component_cols) {
    if (!nm %in% names(wide)) next
    lo <- paste0(nm, "_lower_95")
    hi <- paste0(nm, "_upper_95")
    long_rows[[length(long_rows) + 1L]] <- data.frame(
      wide[, intersect(c(names(meta), "phase", "date", "day_rel", "time_index", "segment", "active_sources"), names(wide)), drop = FALSE],
      quantity = nm,
      value = num(wide[[nm]]),
      lower_95 = if (lo %in% names(wide)) num(wide[[lo]]) else NA_real_,
      upper_95 = if (hi %in% names(wide)) num(wide[[hi]]) else NA_real_,
      stringsAsFactors = FALSE
    )
  }
  long <- bind_rows(long_rows)

  seg_layout <- cbind(
    meta,
    data.frame(
      valid = TRUE,
      reason = "ok",
      J = j_total,
      p = p,
      ppx = ppx,
      TT_hist = tt_hist,
      harmonic_count = idx_split$harmonic_count,
      trend_idx = paste(trend_idx, collapse = ","),
      season_idx = paste(season_idx, collapse = ","),
      ff_base = paste(ff_base, collapse = ","),
      stringsAsFactors = FALSE
    ),
    seg_contract
  )

  fin_abs_max <- function(x) {
    v <- abs(num(x))
    v <- v[is.finite(v)]
    if (!length(v)) NA_real_ else max(v)
  }
  day_last <- wide[wide$phase == "forecast" & wide$day_rel == max(wide$day_rel[wide$phase == "forecast"], na.rm = TRUE), , drop = FALSE]
  diagnostics <- data.frame(
    meta,
    reason = "ok",
    p = p,
    ppx = ppx,
    harmonic_count = idx_split$harmonic_count,
    max_abs_identity_err_glofas = fin_abs_max(wide$identity_err_glofas),
    max_abs_identity_err_nws = fin_abs_max(wide$identity_err_nws),
    max_abs_exps_state_err_usgs = fin_abs_max(wide$exps_state_err_usgs),
    max_abs_exps_state_err_glofas = fin_abs_max(wide$exps_state_err_glofas),
    max_abs_exps_state_err_nws = fin_abs_max(wide$exps_state_err_nws),
    forecast_negative_mu_usgs_n = sum(wide$phase == "forecast" & is.finite(wide$mu_usgs_state) & wide$mu_usgs_state < 0),
    forecast_min_mu_usgs = suppressWarnings(min(wide$mu_usgs_state[wide$phase == "forecast"], na.rm = TRUE)),
    forecast_max_state_rms_norm = suppressWarnings(max(wide$state_rms_norm[wide$phase == "forecast"], na.rm = TRUE)),
    last_forecast_day_rel = if (nrow(day_last)) day_last$day_rel[[1L]] else NA_integer_,
    last_forecast_mu_usgs = if (nrow(day_last)) day_last$mu_usgs_state[[1L]] else NA_real_,
    last_forecast_mu_glofas = if (nrow(day_last)) day_last$mu_glofas_state[[1L]] else NA_real_,
    last_forecast_disc_glofas = if (nrow(day_last)) day_last$agg_discrep_glofas[[1L]] else NA_real_,
    last_forecast_trend = if (nrow(day_last)) day_last$trend[[1L]] else NA_real_,
    last_forecast_season = if (nrow(day_last)) day_last$season[[1L]] else NA_real_,
    last_forecast_zeta = if (nrow(day_last)) day_last$zeta[[1L]] else NA_real_,
    last_forecast_usgs_observed = if (nrow(day_last)) day_last$usgs_observed[[1L]] else NA_real_,
    stringsAsFactors = FALSE
  )

  list(wide = wide, long = long, layout = seg_layout, diagnostics = diagnostics)
}

aggregate_quantity_long <- function(df, phase_value = NULL) {
  if (is.null(df) || !nrow(df)) return(data.frame())
  id_cols <- intersect(c("run_id", "cutoff", "cutoff_date", "spec", "q", "block", "source", "day_rel"), names(df))
  work <- df[is.finite(df$value), c(id_cols, "quantity", "value"), drop = FALSE]
  if (!nrow(work)) return(data.frame())
  work <- fill_missing_group_values(work, id_cols)
  agg <- stats::aggregate(value ~ ., data = work, FUN = function(x) stats::median(x, na.rm = TRUE))
  if (!nrow(agg)) return(data.frame())
  wide <- stats::reshape(agg, idvar = id_cols, timevar = "quantity", direction = "wide")
  names(wide) <- sub("^value\\.", "", names(wide))
  if ("block" %in% names(wide)) {
    names(wide)[names(wide) == "block"] <- "phase"
  } else {
    wide$phase <- phase_value
  }
  wide
}

source_component_rows <- function(component_wide) {
  if (is.null(component_wide) || !nrow(component_wide)) return(data.frame())
  base_cols <- intersect(
    c(names(component_wide)[names(component_wide) %in% c("run_id", "run_root", "cutoff", "cutoff_date", "spec", "q", "rdata_path")],
      "phase", "date", "day_rel", "segment", "active_sources", "mu_usgs_state",
      "theta_exps_usgs", "mu_without_transfer", "trend", "season", "zeta", "usgs_observed", "state_rms_norm"),
    names(component_wide)
  )
  make_one <- function(src, state_col, exps_col, disc_col) {
    out <- component_wide[, base_cols, drop = FALSE]
    out$source <- src
    out$source_location_state <- num(component_wide[[state_col]])
    out$source_location_exps <- num(component_wide[[exps_col]])
    out$agg_discrep <- num(component_wide[[disc_col]])
    out
  }
  bind_rows(list(
    make_one("GloFAS", "mu_glofas_state", "theta_exps_glofas", "agg_discrep_glofas"),
    make_one("NWS3.0", "mu_nws_state", "theta_exps_nws", "agg_discrep_nws")
  ))
}

build_component_latent_overlay <- function(component_wide, latent_win, forecast_win) {
  if (is.null(component_wide) || !nrow(component_wide)) return(data.frame())
  comp_src <- source_component_rows(component_wide)
  latent_hist <- aggregate_quantity_long(latent_win)
  latent_fore <- aggregate_quantity_long(forecast_win)
  latents <- bind_rows(list(latent_hist, latent_fore))
  if (!nrow(latents)) return(comp_src)
  key <- intersect(c("run_id", "cutoff", "cutoff_date", "spec", "q", "phase", "source", "day_rel"), names(latents))
  merge(comp_src, latents, by = key, all.x = TRUE, sort = FALSE)
}

component_quantile_order_summary <- function(component_wide) {
  if (is.null(component_wide) || !nrow(component_wide)) return(data.frame())
  quantities <- intersect(c("mu_usgs_state", "theta_exps_usgs", "mu_glofas_state", "mu_nws_state"), names(component_wide))
  rows <- list()
  for (rid in unique(component_wide$run_id)) {
    run_df <- component_wide[component_wide$run_id == rid, , drop = FALSE]
    for (phase in unique(run_df$phase)) {
      phase_df <- run_df[run_df$phase == phase, , drop = FALSE]
      for (qty in quantities) {
        day_rows <- list()
        for (dd in sort(unique(phase_df$day_rel))) {
          sub <- phase_df[phase_df$day_rel == dd & is.finite(phase_df[[qty]]), , drop = FALSE]
          sub <- sub[order(sub$q), , drop = FALSE]
          if (nrow(sub) < 2L) next
          dif <- diff(num(sub[[qty]]))
          day_rows[[length(day_rows) + 1L]] <- data.frame(
            run_id = rid,
            cutoff = sub$cutoff[[1L]],
            spec = sub$spec[[1L]],
            phase = phase,
            quantity = qty,
            day_rel = dd,
            finite_q_n = nrow(sub),
            violation_n = sum(is.finite(dif) & dif < -1e-8),
            worst_diff = if (any(is.finite(dif))) min(dif[is.finite(dif)]) else NA_real_
          )
        }
        day_df <- bind_rows(day_rows)
        if (!nrow(day_df)) next
        rows[[length(rows) + 1L]] <- data.frame(
          run_id = rid,
          cutoff = day_df$cutoff[[1L]],
          spec = day_df$spec[[1L]],
          phase = phase,
          quantity = qty,
          checked_days = nrow(day_df),
          violation_days = sum(day_df$violation_n > 0L, na.rm = TRUE),
          total_violations = sum(day_df$violation_n, na.rm = TRUE),
          worst_diff = suppressWarnings(min(day_df$worst_diff, na.rm = TRUE)),
          stringsAsFactors = FALSE
        )
      }
    }
  }
  bind_rows(rows)
}

component_overlay_summary <- function(overlay) {
  if (is.null(overlay) || !nrow(overlay)) return(data.frame())
  fields <- intersect(c("source_location_state", "agg_discrep", "mu_usgs_state", "E_u", "E_inv_u", "E_s", "E_s2", "FFF", "QQQ_diag", "state_rms_norm"), names(overlay))
  rows <- list()
  groups <- unique(overlay[, intersect(c("run_id", "cutoff", "spec", "q", "phase", "source"), names(overlay)), drop = FALSE])
  for (ii in seq_len(nrow(groups))) {
    idx <- rep(TRUE, nrow(overlay))
    for (nm in names(groups)) idx <- idx & overlay[[nm]] == groups[[nm]][ii]
    sub <- overlay[idx, , drop = FALSE]
    for (field in fields) {
      rows[[length(rows) + 1L]] <- cbind(groups[ii, , drop = FALSE], data.frame(quantity = field), finite_summary(sub[[field]]))
    }
    if (all(c("source_location_state", "E_inv_u") %in% names(sub))) {
      ok <- is.finite(sub$source_location_state) & is.finite(sub$E_inv_u)
      rows[[length(rows) + 1L]] <- cbind(groups[ii, , drop = FALSE], data.frame(quantity = "cor_source_location_E_inv_u"), finite_summary(if (sum(ok) >= 3L) stats::cor(sub$source_location_state[ok], sub$E_inv_u[ok]) else NA_real_))
    }
    if (all(c("agg_discrep", "E_inv_u") %in% names(sub))) {
      ok <- is.finite(sub$agg_discrep) & is.finite(sub$E_inv_u)
      rows[[length(rows) + 1L]] <- cbind(groups[ii, , drop = FALSE], data.frame(quantity = "cor_discrep_E_inv_u"), finite_summary(if (sum(ok) >= 3L) stats::cor(sub$agg_discrep[ok], sub$E_inv_u[ok]) else NA_real_))
    }
  }
  bind_rows(rows)
}

plot_component_lines <- function(component_wide, run_id, y_col, out_file, title = y_col, ylab = y_col) {
  dat <- component_wide[component_wide$run_id == run_id & is.finite(component_wide[[y_col]]), , drop = FALSE]
  if (!nrow(dat)) return(invisible(FALSE))
  obs <- component_wide[component_wide$run_id == run_id & is.finite(component_wide$usgs_observed), c("day_rel", "usgs_observed"), drop = FALSE]
  obs <- obs[!duplicated(obs$day_rel), , drop = FALSE]
  ylim <- range(c(dat[[y_col]], obs$usgs_observed), na.rm = TRUE)
  png(out_file, width = 3200, height = 1800, res = 260)
  on.exit(dev.off(), add = TRUE)
  qvals <- sort(unique(dat$q))
  cols <- grDevices::hcl.colors(max(length(qvals), 2L), "Dark 3")
  names(cols) <- qvals
  plot(dat$day_rel, dat[[y_col]], type = "n", xlab = "Day relative to cutoff", ylab = ylab, main = title, ylim = ylim)
  abline(v = 0, lty = 3, col = "gray45")
  if (nrow(obs)) lines(obs$day_rel, obs$usgs_observed, col = "black", lwd = 2.2)
  for (qv in qvals) {
    sub <- dat[dat$q == qv, , drop = FALSE]
    sub <- sub[order(sub$day_rel), , drop = FALSE]
    lines(sub$day_rel, sub[[y_col]], col = cols[[as.character(qv)]], lwd = ifelse(qv %in% c(5L, 50L, 95L), 1.9, 1.1))
  }
  legend("topleft", legend = c("USGS obs", paste0("q", qvals)), col = c("black", cols), lwd = c(2.2, rep(2, length(qvals))), bty = "n", cex = 0.75)
  invisible(TRUE)
}

plot_component_facet_grid <- function(component_wide, run_id, y_cols, labels, out_file, title) {
  dat <- component_wide[component_wide$run_id == run_id, , drop = FALSE]
  if (!nrow(dat)) return(invisible(FALSE))
  png(out_file, width = 3400, height = 2200, res = 260)
  on.exit(dev.off(), add = TRUE)
  old <- par(no.readonly = TRUE)
  on.exit(par(old), add = TRUE)
  par(mfrow = c(ceiling(length(y_cols) / 2), 2), mar = c(3.5, 4, 2.5, 1))
  qvals <- sort(unique(dat$q))
  cols <- grDevices::hcl.colors(max(length(qvals), 2L), "Dark 3")
  names(cols) <- qvals
  for (i in seq_along(y_cols)) {
    y_col <- y_cols[[i]]
    sub0 <- dat[is.finite(dat[[y_col]]), , drop = FALSE]
    if (!nrow(sub0)) {
      plot.new(); title(labels[[i]])
      next
    }
    plot(sub0$day_rel, sub0[[y_col]], type = "n", xlab = "Day relative to cutoff", ylab = labels[[i]], main = labels[[i]])
    abline(v = 0, lty = 3, col = "gray45")
    for (qv in qvals) {
      sub <- sub0[sub0$q == qv, , drop = FALSE]
      sub <- sub[order(sub$day_rel), , drop = FALSE]
      lines(sub$day_rel, sub[[y_col]], col = cols[[as.character(qv)]], lwd = ifelse(qv %in% c(5L, 50L, 95L), 1.8, 1.0))
    }
  }
  mtext(title, outer = TRUE, line = -1, cex = 1.1)
  invisible(TRUE)
}

standardize_for_overlay <- function(x) {
  v <- num(x)
  ok <- is.finite(v)
  out <- rep(NA_real_, length(v))
  if (sum(ok) < 2L) return(out)
  center <- stats::median(v[ok], na.rm = TRUE)
  scale <- stats::IQR(v[ok], na.rm = TRUE)
  if (!is.finite(scale) || scale <= 0) scale <- stats::sd(v[ok], na.rm = TRUE)
  if (!is.finite(scale) || scale <= 0) return(out)
  out[ok] <- (v[ok] - center) / scale
  out
}

plot_overlay_scaled <- function(overlay, run_id, q_value, source_name, out_file) {
  dat <- overlay[overlay$run_id == run_id & overlay$q == q_value & overlay$source == source_name, , drop = FALSE]
  if (!nrow(dat)) return(invisible(FALSE))
  fields <- intersect(c("mu_usgs_state", "source_location_state", "agg_discrep", "E_inv_u", "E_u", "E_s", "E_s2", "FFF", "QQQ_diag", "state_rms_norm"), names(dat))
  if (!length(fields)) return(invisible(FALSE))
  dat <- dat[order(dat$day_rel), , drop = FALSE]
  z <- lapply(fields, function(f) standardize_for_overlay(dat[[f]]))
  names(z) <- fields
  keep <- vapply(z, function(x) any(is.finite(x)), logical(1))
  z <- z[keep]
  if (!length(z)) return(invisible(FALSE))
  ylim <- range(unlist(z, use.names = FALSE), na.rm = TRUE)
  png(out_file, width = 3200, height = 1800, res = 260)
  on.exit(dev.off(), add = TRUE)
  cols <- grDevices::hcl.colors(max(length(z), 2L), "Dark 3")
  plot(dat$day_rel, z[[1L]], type = "n", xlab = "Day relative to cutoff", ylab = "Robust z-score within series", main = paste("q", q_value, source_name, "component/latent overlay:", run_id), ylim = ylim)
  abline(v = 0, lty = 3, col = "gray45")
  for (i in seq_along(z)) lines(dat$day_rel, z[[i]], col = cols[[i]], lwd = 1.5)
  legend("topright", legend = names(z), col = cols[seq_along(z)], lwd = 2, bty = "n", cex = 0.7)
  invisible(TRUE)
}

main <- function() {
  args <- parse_args(commandArgs(trailingOnly = TRUE))
  assign("window_days_global", args$window_days, envir = .GlobalEnv)
  out_dir <- normalizePath(args$out_dir, mustWork = FALSE)
  dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
  dir.create(file.path(out_dir, "plots"), recursive = TRUE, showWarnings = FALSE)

  rdata_paths <- sort(unique(unlist(lapply(args$run_roots, function(root) {
    list.files(
      root,
      pattern = "^DISC_variables_.*_exAL_synth_[A-Za-z0-9._-]+\\.RData$",
      recursive = TRUE,
      full.names = TRUE
    )
  }))))
  if (!length(rdata_paths)) stop("No DISC_variables RData files found.", call. = FALSE)

  all_latent_summary <- list()
  all_latent_top <- list()
  all_pseudo_summary <- list()
  all_pseudo_top <- list()
  all_gamsig <- list()
  all_seq_summary <- list()
  all_seq_long <- list()
  all_theta_summary <- list()
  all_theta_window <- list()
  all_latent_window <- list()
  all_forecast_window <- list()
  all_component_wide <- list()
  all_component_long <- list()
  all_component_layout <- list()
  all_component_diag <- list()
  all_progress <- list()
  all_iteration_health <- list()
  manifest <- list()

  for (path in rdata_paths) {
    run_id <- run_id_from_path(path)
    run_root <- run_root_from_rdata(path)
    cutoff_raw <- cutoff_from_run_id(run_id)
    cutoff_date <- as.Date(cutoff_raw, format = "%Y%m%d")
    q <- q_from_path(path)
    spec <- spec_from_run_id(run_id)
    meta <- data.frame(
      run_id = run_id,
      run_root = run_root,
      cutoff = cutoff_raw,
      cutoff_date = as.character(cutoff_date),
      spec = spec,
      q = q,
      rdata_path = path
    )
    cat(sprintf("[audit] loading q=%s run=%s\n", q, run_id))
    e <- new.env(parent = emptyenv())
    loaded <- load(path, envir = e)
    history_dates <- read_history_dates(run_root)

    sts <- object_by_prefix(e, "new.sts.out_")
    uts <- object_by_prefix(e, "new.uts.out_")
    sts_f <- object_by_prefix(e, "new.sts_ens.out_")
    uts_f <- object_by_prefix(e, "new.uts_ens.out_")
    gs <- object_by_prefix(e, "new.gamsig.out_")
    theta <- object_by_prefix(e, "new.theta.out_")
    ext_f <- object_by_prefix(e, "ext.f_")
    ext_q <- object_by_prefix(e, "ext.q_")
    ext_f_f <- object_by_prefix(e, "ext.f_f_")
    ext_q_f <- object_by_prefix(e, "ext.q_f_")
    seq_elbo <- object_by_prefix(e, "seq.elbo_")
    seq_gamma <- object_by_prefix(e, "seq.gamma_")
    seq_sigma <- object_by_prefix(e, "seq.sigma_")
    seq_eigen <- object_by_prefix(e, "seq.eigen")

    manifest[[length(manifest) + 1L]] <- data.frame(
      meta,
      loaded_objects = paste(loaded, collapse = ";"),
      sts_object = object_name_by_prefix(e, "new.sts.out_"),
      uts_object = object_name_by_prefix(e, "new.uts.out_"),
      theta_object = object_name_by_prefix(e, "new.theta.out_"),
      gamsig_object = object_name_by_prefix(e, "new.gamsig.out_"),
      rdata_size_gb = file.info(path)$size / (1024^3)
    )

    all_latent_summary[[length(all_latent_summary) + 1L]] <- bind_rows(list(
      matrix_rows_summary(sts$E.sts, "E_s", "history", meta, history_dates),
      matrix_rows_summary(sts$E.sts2, "E_s2", "history", meta, history_dates),
      matrix_rows_summary(uts$E.uts, "E_u", "history", meta, history_dates),
      matrix_rows_summary(uts$E.inv.uts, "E_inv_u", "history", meta, history_dates),
      matrix_rows_summary(uts$E.log.uts, "E_log_u", "history_source_total", meta),
      matrix_rows_summary(uts$tot.entrop, "entropy_u", "history_source_total", meta),
      matrix_rows_summary(sts$tot.entrop, "entropy_s", "history_source_total", meta),
      list_matrix_summary(sts_f$E.sts, "E_s", "forecast", meta, run_root),
      list_matrix_summary(sts_f$E.sts2, "E_s2", "forecast", meta, run_root),
      list_matrix_summary(uts_f$E.uts, "E_u", "forecast", meta, run_root),
      list_matrix_summary(uts_f$E.inv.uts, "E_inv_u", "forecast", meta, run_root),
      list_matrix_summary(uts_f$E.log.uts, "E_log_u", "forecast_source_total", meta, run_root),
      list_matrix_summary(uts_f$tot.entrop, "entropy_u", "forecast_source_total", meta, run_root),
      list_matrix_summary(sts_f$tot.entrop, "entropy_s", "forecast_source_total", meta, run_root)
    ))
    all_latent_top[[length(all_latent_top) + 1L]] <- bind_rows(list(
      matrix_top_cells(sts$E.sts, "E_s", "history", meta, history_dates),
      matrix_top_cells(sts$E.sts2, "E_s2", "history", meta, history_dates),
      matrix_top_cells(uts$E.uts, "E_u", "history", meta, history_dates),
      matrix_top_cells(uts$E.inv.uts, "E_inv_u", "history", meta, history_dates),
      list_matrix_top_cells(sts_f$E.sts, "E_s", "forecast", meta, run_root),
      list_matrix_top_cells(sts_f$E.sts2, "E_s2", "forecast", meta, run_root),
      list_matrix_top_cells(uts_f$E.uts, "E_u", "forecast", meta, run_root),
      list_matrix_top_cells(uts_f$E.inv.uts, "E_inv_u", "forecast", meta, run_root)
    ))
    all_pseudo_summary[[length(all_pseudo_summary) + 1L]] <- bind_rows(list(
      matrix_rows_summary(ext_f, "FFF", "history", meta, history_dates),
      matrix_rows_summary(diag_array_by_time(ext_q), "QQQ_diag", "history", meta, history_dates),
      list_matrix_summary(ext_f_f, "FFF", "forecast", meta, run_root),
      list_matrix_summary(ext_q_f, "QQQ_diag", "forecast", meta, run_root)
    ))
    all_pseudo_top[[length(all_pseudo_top) + 1L]] <- bind_rows(list(
      matrix_top_cells(ext_f, "FFF", "history", meta, history_dates),
      matrix_top_cells(diag_array_by_time(ext_q), "QQQ_diag", "history", meta, history_dates),
      list_matrix_top_cells(ext_f_f, "FFF", "forecast", meta, run_root),
      list_matrix_top_cells(ext_q_f, "QQQ_diag", "forecast", meta, run_root)
    ))
    all_gamsig[[length(all_gamsig) + 1L]] <- gamsig_summary(gs, meta)
    all_seq_summary[[length(all_seq_summary) + 1L]] <- bind_rows(list(
      seq_summary(seq_elbo, "elbo", meta),
      seq_summary(seq_gamma, "gamma", meta),
      seq_summary(seq_sigma, "sigma", meta),
      seq_summary(seq_eigen, "min_abs_eigen", meta)
    ))
    all_seq_long[[length(all_seq_long) + 1L]] <- seq_long(seq_elbo, seq_gamma, seq_sigma, seq_eigen, meta)
    th <- theta_summary(theta, meta, history_dates, cutoff_date)
    all_theta_summary[[length(all_theta_summary) + 1L]] <- th$summary
    all_theta_window[[length(all_theta_window) + 1L]] <- th$window
    all_latent_window[[length(all_latent_window) + 1L]] <- latent_window(sts, uts, ext_f, ext_q, meta, history_dates, cutoff_date)
    all_forecast_window[[length(all_forecast_window) + 1L]] <- forecast_window(sts_f, uts_f, ext_f_f, ext_q_f, meta, run_root, cutoff_date)
    comp <- build_component_decomposition(theta, meta, run_root, history_dates, cutoff_date, args$window_days)
    all_component_wide[[length(all_component_wide) + 1L]] <- comp$wide
    all_component_long[[length(all_component_long) + 1L]] <- comp$long
    all_component_layout[[length(all_component_layout) + 1L]] <- comp$layout
    all_component_diag[[length(all_component_diag) + 1L]] <- comp$diagnostics

    tt <- if (length(history_dates)) length(history_dates) else if (!is.null(sts$E.sts)) ncol(as.matrix(sts$E.sts)) else NA_real_
    q_dir <- dirname(dirname(path))
    all_progress[[length(all_progress) + 1L]] <- parse_progress_log(file.path(q_dir, "logs", "fit.log"), meta, tt)
    all_iteration_health[[length(all_iteration_health) + 1L]] <- read_iteration_health(path, meta)

    rm(e, sts, uts, sts_f, uts_f, gs, theta, ext_f, ext_q, ext_f_f, ext_q_f, seq_elbo, seq_gamma, seq_sigma, seq_eigen, comp)
    gc(verbose = FALSE)
  }

  latent_summary <- bind_rows(all_latent_summary)
  latent_top <- bind_rows(all_latent_top)
  pseudo_summary <- bind_rows(all_pseudo_summary)
  pseudo_top <- bind_rows(all_pseudo_top)
  gamsig <- bind_rows(all_gamsig)
  trace_summary <- bind_rows(all_seq_summary)
  trace_long <- bind_rows(all_seq_long)
  theta_summ <- bind_rows(all_theta_summary)
  theta_win <- bind_rows(all_theta_window)
  latent_win <- bind_rows(all_latent_window)
  forecast_win <- bind_rows(all_forecast_window)
  component_wide <- bind_rows(all_component_wide)
  component_long <- bind_rows(all_component_long)
  component_layout <- bind_rows(all_component_layout)
  component_diag <- bind_rows(all_component_diag)
  component_overlay <- build_component_latent_overlay(component_wide, latent_win, forecast_win)
  component_overlay_summ <- component_overlay_summary(component_overlay)
  component_qorder <- component_quantile_order_summary(component_wide)
  progress <- bind_rows(all_progress)
  iteration_health <- bind_rows(all_iteration_health)
  manifest_df <- bind_rows(manifest)

  write_csv(manifest_df, file.path(out_dir, "vb_latent_audit_manifest.csv"))
  write_csv(latent_summary, file.path(out_dir, "vb_latent_field_summary.csv"))
  write_csv(latent_top, file.path(out_dir, "vb_latent_top_cells.csv"))
  write_csv(pseudo_summary, file.path(out_dir, "vb_pseudodata_field_summary.csv"))
  write_csv(pseudo_top, file.path(out_dir, "vb_pseudodata_top_cells.csv"))
  write_csv(gamsig, file.path(out_dir, "vb_gamsig_final_values.csv"))
  write_csv(trace_summary, file.path(out_dir, "vb_trace_summary.csv"))
  write_csv(trace_long, file.path(out_dir, "vb_trace_long.csv"))
  write_csv(progress, file.path(out_dir, "vb_fit_progress_from_logs.csv"))
  write_csv(iteration_health, file.path(out_dir, "vb_fit_iteration_health_summary.csv"))
  write_csv(theta_summ, file.path(out_dir, "vb_theta_field_summary.csv"))
  write_csv(theta_win, file.path(out_dir, "vb_theta_cutoff_window.csv"))
  write_csv(latent_win, file.path(out_dir, "vb_latent_pseudodata_cutoff_window.csv"))
  write_csv(forecast_win, file.path(out_dir, "vb_forecast_latent_pseudodata_window.csv"))
  write_csv(component_wide, file.path(out_dir, "vb_component_decomposition_window.csv"))
  write_csv(component_long, file.path(out_dir, "vb_component_decomposition_long.csv"))
  write_csv(component_layout, file.path(out_dir, "vb_component_layout_contract.csv"))
  write_csv(component_diag, file.path(out_dir, "vb_component_diagnostic_summary.csv"))
  write_csv(component_qorder, file.path(out_dir, "vb_component_quantile_order_summary.csv"))
  write_csv(component_overlay, file.path(out_dir, "vb_component_latent_overlay.csv"))
  write_csv(component_overlay_summ, file.path(out_dir, "vb_component_latent_overlay_summary.csv"))

  plot_trace(trace_long, "elbo", file.path(out_dir, "plots", "elbo_trace_by_run_quantile.png"), "ELBO")
  plot_trace(trace_long, "gamma", file.path(out_dir, "plots", "gamma_trace_by_run_quantile_source.png"), "E[gamma]")
  plot_trace(trace_long, "sigma", file.path(out_dir, "plots", "sigma_trace_by_run_quantile_source.png"), "E[sigma]")
  plot_progress_metric(progress, "state_norm_sq_per_T", file.path(out_dir, "plots", "state_norm_sq_per_T_from_logs.png"), "state norm sq / T")
  plot_health_metric(iteration_health, "state_norm_sq_per_T", file.path(out_dir, "plots", "iter_health_state_norm_sq_per_T.png"), "state norm sq / T")
  plot_health_metric(iteration_health, "max_E_inv_u", file.path(out_dir, "plots", "iter_health_max_E_inv_u.png"), "max E[1/u]")
  plot_health_metric(iteration_health, "min_E_u", file.path(out_dir, "plots", "iter_health_min_E_u.png"), "min E[u]")
  plot_health_metric(iteration_health, "max_QQQ_diag_abs", file.path(out_dir, "plots", "iter_health_max_QQQ_diag_abs.png"), "max |diag(QQQ)|")
  plot_health_metric(iteration_health, "health_flag_n", file.path(out_dir, "plots", "iter_health_flag_count.png"), "health flag count")
  for (rid in unique(latent_win$run_id)) {
    safe_id <- gsub("[^A-Za-z0-9_=-]+", "_", rid)
    for (quantity in c("E_u", "E_inv_u", "E_s", "E_s2", "FFF", "QQQ_diag")) {
      plot_window_quantity(latent_win, rid, quantity, file.path(out_dir, "plots", paste0("cutoff_window_", quantity, "_", safe_id, ".png")))
    }
  }
  for (rid in unique(theta_win$run_id)) {
    safe_id <- gsub("[^A-Za-z0-9_=-]+", "_", rid)
    plot_window_quantity(theta_win, rid, "theta.exps", file.path(out_dir, "plots", paste0("cutoff_window_theta_exps_", safe_id, ".png")))
    plot_window_quantity(theta_win, rid, "theta.sm_rms_state_norm", file.path(out_dir, "plots", paste0("cutoff_window_theta_state_norm_", safe_id, ".png")))
  }
  for (rid in unique(forecast_win$run_id)) {
    safe_id <- gsub("[^A-Za-z0-9_=-]+", "_", rid)
    for (quantity in c("E_u", "E_inv_u", "FFF", "QQQ_diag")) {
      plot_forecast_window_quantity(forecast_win, rid, quantity, file.path(out_dir, "plots", paste0("forecast_window_", quantity, "_", safe_id, ".png")))
    }
  }
  for (rid in unique(component_wide$run_id)) {
    safe_id <- gsub("[^A-Za-z0-9_=-]+", "_", rid)
    plot_component_lines(
      component_wide, rid, "mu_usgs_state",
      file.path(out_dir, "plots", paste0("components_mu_usgs_all_quantiles_", safe_id, ".png")),
      paste("USGS VB location state mean around cutoff:", rid),
      "USGS location mean (log1p cms)"
    )
    plot_component_lines(
      component_wide, rid, "theta_exps_usgs",
      file.path(out_dir, "plots", paste0("components_theta_exps_usgs_all_quantiles_", safe_id, ".png")),
      paste("USGS theta.out exps around cutoff:", rid),
      "theta.out exps USGS (log1p cms)"
    )
    plot_component_facet_grid(
      component_wide, rid,
      c("mu_without_transfer", "trend", "season", "zeta", "agg_discrep_glofas", "agg_discrep_nws"),
      c("baseline without transfer", "trend", "seasonal aggregate", "transfer zeta", "GloFAS discrepancy", "NWS discrepancy"),
      file.path(out_dir, "plots", paste0("components_decomposition_facets_", safe_id, ".png")),
      paste("State decomposition around cutoff:", rid)
    )
    plot_component_facet_grid(
      component_wide, rid,
      c("mu_usgs_state", "mu_glofas_state", "mu_nws_state", "state_rms_norm"),
      c("USGS location", "GloFAS source location", "NWS source location", "state RMS norm"),
      file.path(out_dir, "plots", paste0("components_source_locations_and_norm_", safe_id, ".png")),
      paste("Source locations and state norm:", rid)
    )
    for (src in c("GloFAS", "NWS3.0")) {
      plot_overlay_scaled(
        component_overlay, rid, 5L, src,
        file.path(out_dir, "plots", paste0("overlay_q05_", gsub("[^A-Za-z0-9]+", "_", src), "_components_latents_", safe_id, ".png"))
      )
      plot_overlay_scaled(
        component_overlay, rid, 95L, src,
        file.path(out_dir, "plots", paste0("overlay_q95_", gsub("[^A-Za-z0-9]+", "_", src), "_components_latents_", safe_id, ".png"))
      )
    }
  }

  lines <- c(
    "# exDQLM Multivar Keep VB Latent Audit",
    "",
    sprintf("- generated_at: `%s`", format(Sys.time(), "%Y-%m-%d %H:%M:%S %Z")),
    sprintf("- window_days: `%d`", args$window_days),
    "",
    "This report audits final variational-parameter objects saved by the fit stage. It does not use posterior predictive samples except that the `.RData` files must be loaded as saved.",
    "",
    "## Inputs",
    "",
    paste0("- `", normalizePath(args$run_roots, mustWork = FALSE), "`"),
    "",
    "## Tables",
    "",
    "- `vb_latent_field_summary.csv`: final `s_t` and `u_t` variational moments by source/block/quantile.",
    "- `vb_latent_top_cells.csv`: largest final latent-moment cells by source/date.",
    "- `vb_pseudodata_field_summary.csv`: final pseudo-data `FFF` and diagonal `QQQ` ranges.",
    "- `vb_pseudodata_top_cells.csv`: largest final pseudo-data cells by source/date.",
    "- `vb_gamsig_final_values.csv`: final gamma/sigma/Laplace moment values.",
    "- `vb_trace_summary.csv` and `vb_trace_long.csv`: ELBO/gamma/sigma/eigen traces from saved sequences.",
    "- `vb_fit_progress_from_logs.csv`: fit log progress including `state_norm_sq_per_T`.",
    "- `vb_fit_iteration_health_summary.csv`: optional per-iteration fit-stage health CSVs emitted by the active fit workflow, including latent moment, pseudo-data, and state-norm flags.",
    "- `vb_theta_field_summary.csv` and `vb_theta_cutoff_window.csv`: state-space VB means/state norms.",
    "- `vb_latent_pseudodata_cutoff_window.csv`: cutoff-window latent and pseudo-data values.",
    "- `vb_forecast_latent_pseudodata_window.csv`: forecast-window latent and pseudo-data values by lead/member.",
    "- `vb_component_decomposition_window.csv`: deterministic state-component decomposition from `theta.out` for all quantiles.",
    "- `vb_component_decomposition_long.csv`: long-form component values for plotting and QA.",
    "- `vb_component_layout_contract.csv`: inferred `keep` state dimensions, retained-transfer segments, harmonic split, and measurement loading.",
    "- `vb_component_diagnostic_summary.csv`: identity checks, exps-vs-state checks, negative forecast counts, and last-lead component values.",
    "- `vb_component_quantile_order_summary.csv`: cross-quantile monotonicity checks for state and `theta.out` locations.",
    "- `vb_component_latent_overlay.csv`: source-level component rows joined to `s_t/u_t/FFF/QQQ` moments by lead/source.",
    "- `vb_component_latent_overlay_summary.csv`: summaries and correlations for the component-latent overlay.",
    "",
    "## Plots",
    "",
    paste0("- `plots/", basename(list.files(file.path(out_dir, "plots"), full.names = FALSE)), "`"),
    "",
    "## Source-Code Contract Checked",
    "",
    "- Saved object names and contents come from `R/disc_w/05_save_state.R`.",
    "- Latent update formulas are in `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r` at `update_sts(...)` and `update_uts(...)`.",
    "- Pseudo-data construction is `FFF = (E.c.invb.absgam * E.sts + E.a.invb.inv.sigma / E.inv.uts) / E.invb.inv.sigma` and `QQQ = 1 / (E.invb.inv.sigma * E.inv.uts)` in the active fit script.",
    "- Historical source order is `USGS`, `GloFAS`, `NWS3.0` from `R/disc_w/03_covariates_standardize.R`; forecast ensemble order is GloFAS then NWS from `R/disc_w/04_ensemble_bookkeeping.R`.",
    "- Forecast latent/pseudo-data objects are source-level lists, while `theta.out$sm_ens` is a keep-mode availability-segment list. The component overlay maps both contracts onto actual forecast lead days before joining."
  )
  writeLines(lines, file.path(out_dir, "README.md"))
  cat(sprintf("out_dir=%s\n", out_dir))
}

if (!identical(toupper(Sys.getenv("EXDQLM_VB_LATENT_AUDIT_NO_MAIN", "FALSE")), "TRUE")) {
  main()
}
