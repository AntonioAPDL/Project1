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
  cols <- c("iter", "elbo", "crit_elbo", "sigma_exp", "gamma_exp", "state_norm_sq", "w_hist", "w_fore")
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
      w_fore = unified_ndlm_diag_num(extract_token("w_fore"))
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

unified_ndlm_diag_build_horizon_contract <- function(ndlm_obj, state_obj, retros_n, nws_n, glofas_n) {
  state_k <- NA_integer_
  state_k_cap <- NA_integer_
  state_nws <- NA_integer_
  state_glofas <- NA_integer_
  if (is.list(state_obj)) {
    state_k <- unified_ndlm_diag_int(state_obj$K)
    state_k_cap <- unified_ndlm_diag_int(state_obj$K_cap)
    state_nws <- unified_ndlm_diag_int(state_obj$nws_len)
    state_glofas <- unified_ndlm_diag_int(state_obj$glofas_len)
  }

  if (!is.finite(state_k_cap) || state_k_cap <= 0L) state_k_cap <- 14L
  if (!is.finite(state_nws) || state_nws <= 0L) state_nws <- nws_n
  if (!is.finite(state_glofas) || state_glofas <= 0L) state_glofas <- glofas_n

  expected_k <- suppressWarnings(as.integer(min(state_nws, state_glofas, state_k_cap)))
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

  rows <- list(
    data.frame(
      figure_or_series = "ndlm_shared_forecast_horizon",
      expected_horizon = expected_k,
      actual_horizon = standard_k,
      status = if (is.finite(expected_k) && is.finite(standard_k) && expected_k == standard_k) "pass" else "mismatch",
      contract_rule = "K = min(nws_len, glofas_len, K_cap)",
      notes = sprintf("state.K=%s state.nws_len=%s state.glofas_len=%s K_cap=%s", as.character(state_k), as.character(state_nws), as.character(state_glofas), as.character(state_k_cap)),
      stringsAsFactors = FALSE
    ),
    data.frame(
      figure_or_series = "ndlm_sm_ens_segment_horizon",
      expected_horizon = expected_k,
      actual_horizon = if (length(sm_k) == 0L) NA_integer_ else min(sm_k),
      status = if (length(sm_k) > 0L && all(is.finite(sm_k)) && all(sm_k == expected_k)) "pass" else "mismatch",
      contract_rule = "Each sm_ens segment must use shared K",
      notes = if (length(sm_k) == 0L) "no sm_ens segments" else sprintf("segment_K=[%s]", paste(sm_k, collapse = ",")),
      stringsAsFactors = FALSE
    ),
    data.frame(
      figure_or_series = "ndlm_sC_ens_segment_horizon",
      expected_horizon = expected_k,
      actual_horizon = if (length(sc_k) == 0L) NA_integer_ else min(sc_k),
      status = if (length(sc_k) > 0L && all(is.finite(sc_k)) && all(sc_k == expected_k)) "pass" else "mismatch",
      contract_rule = "Each sC_ens segment must use shared K",
      notes = if (length(sc_k) == 0L) "no sC_ens segments" else sprintf("segment_K=[%s]", paste(sc_k, collapse = ",")),
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

  obs_series <- unified_ndlm_diag_pick_numeric_column(retros_df, preferred = c("USGS", "y", "obs", "flow", "value"))
  fit_series <- if (is.numeric(exps) && !is.null(dim(exps)) && length(dim(exps)) == 2L && dim(exps)[1] >= 2L) {
    as.numeric(exps[2, ])
  } else {
    numeric(0)
  }
  n_overlap <- min(length(obs_series), length(fit_series))
  obs_use <- if (n_overlap > 0L) obs_series[seq_len(n_overlap)] else numeric(0)
  fit_use <- if (n_overlap > 0L) fit_series[seq_len(n_overlap)] else numeric(0)
  ok <- is.finite(obs_use) & is.finite(fit_use)
  fit_summary <- data.frame(
    metric = c(
      "retros_points", "exps_points", "overlap_points", "finite_overlap_points",
      "coverage_rate", "rmse", "mae", "corr"
    ),
    value = c(
      as.numeric(length(obs_series)),
      as.numeric(length(fit_series)),
      as.numeric(n_overlap),
      as.numeric(sum(ok)),
      if (n_overlap > 0L) as.numeric(sum(ok) / n_overlap) else NA_real_,
      if (any(ok)) sqrt(mean((fit_use[ok] - obs_use[ok])^2)) else NA_real_,
      if (any(ok)) mean(abs(fit_use[ok] - obs_use[ok])) else NA_real_,
      if (sum(ok) >= 2L) suppressWarnings(stats::cor(fit_use[ok], obs_use[ok])) else NA_real_
    ),
    stringsAsFactors = FALSE
  )

  horizon_note <- c(
    "# NDLM Horizon Contract",
    "",
    "Theory alignment:",
    "1. NDLM Model C defines a shared forecast index `k=1..K` for active forecast sources.",
    "2. In this implementation, `K` is derived as `min(nws_len, glofas_len, K_cap)`.",
    "3. `exps` is retrospective-only (`T` columns). Forecast discrepancy dynamics are represented by `sm_ens/sC_ens` and `standard_forecast_errors` over `K`.",
    "",
    sprintf("Observed lengths: retros=%d, nws=%d, glofas=%d", as.integer(nrow(retros_df)), as.integer(nrow(nws_df)), as.integer(nrow(glofas_df))),
    sprintf("Contract result: %s", if (all(horizon_contract$status == "pass")) "pass" else "mismatch")
  )

  paths <- list(
    ndlm_iter_trace = file.path(output_dir, "ndlm_iter_trace.csv"),
    ndlm_time_coverage = file.path(output_dir, "ndlm_time_coverage.csv"),
    ndlm_plot_contract_check = file.path(output_dir, "ndlm_plot_contract_check.csv"),
    ndlm_object_shapes = file.path(output_dir, "ndlm_object_shapes.csv"),
    ndlm_fit_vs_observed_coverage = file.path(output_dir, "ndlm_fit_vs_observed_coverage.csv"),
    ndlm_horizon_contract = file.path(output_dir, "ndlm_horizon_contract.md")
  )

  utils::write.csv(iter_trace, paths$ndlm_iter_trace, row.names = FALSE)
  utils::write.csv(time_coverage, paths$ndlm_time_coverage, row.names = FALSE)
  utils::write.csv(horizon_contract, paths$ndlm_plot_contract_check, row.names = FALSE)
  utils::write.csv(shape_rows, paths$ndlm_object_shapes, row.names = FALSE)
  utils::write.csv(fit_summary, paths$ndlm_fit_vs_observed_coverage, row.names = FALSE)
  writeLines(horizon_note, con = paths$ndlm_horizon_contract)

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
