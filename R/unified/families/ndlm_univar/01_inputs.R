ndlm_univar_read_csv <- function(path, label) {
  if (is.null(path) || !nzchar(path)) {
    stop(sprintf("ndlm_univar input %s path is empty", label), call. = FALSE)
  }
  if (!file.exists(path)) {
    stop(sprintf("ndlm_univar input %s missing: %s", label, path), call. = FALSE)
  }
  out <- tryCatch(
    utils::read.csv(path, stringsAsFactors = FALSE, check.names = FALSE),
    error = function(e) e
  )
  if (inherits(out, "error") || !is.data.frame(out)) {
    stop(sprintf("ndlm_univar input %s unreadable CSV: %s", label, path), call. = FALSE)
  }
  if (nrow(out) < 1L || ncol(out) < 1L) {
    stop(sprintf("ndlm_univar input %s is empty: %s", label, path), call. = FALSE)
  }
  out
}

ndlm_univar_pick_numeric_column <- function(df, preferred = character(0)) {
  if (length(preferred) > 0L) {
    nm_norm <- gsub("[^a-z0-9]+", "", tolower(names(df)))
    for (cand in preferred) {
      key <- gsub("[^a-z0-9]+", "", tolower(as.character(cand)))
      if (!nzchar(key)) next
      idx <- which(nm_norm == key)
      if (length(idx) < 1L) next
      col <- suppressWarnings(as.numeric(df[[idx[[1L]]]]))
      if (any(is.finite(col))) {
        return(col)
      }
    }
  }
  num_cols <- names(df)[vapply(df, is.numeric, logical(1))]
  if (length(num_cols) == 0L) return(NULL)
  col <- suppressWarnings(as.numeric(df[[num_cols[[1L]]]]))
  if (!any(is.finite(col))) return(NULL)
  col
}

ndlm_univar_pick_date_column <- function(df) {
  nms <- names(df)
  if (!length(nms)) return(rep(as.Date(NA), nrow(df)))
  candidates <- c(
    nms[grepl("date|time", tolower(nms))],
    nms[[1L]]
  )
  candidates <- unique(candidates)
  for (nm in candidates) {
    vals <- suppressWarnings(as.Date(df[[nm]]))
    if (sum(!is.na(vals)) >= max(10L, floor(0.7 * nrow(df)))) {
      return(vals)
    }
  }
  rep(as.Date(NA), nrow(df))
}

ndlm_univar_align_cov_by_dates <- function(dates_src, values_src, target_dates, fill_value = 0) {
  values_src <- as.numeric(values_src)
  if (length(values_src) < length(dates_src)) {
    values_src <- c(values_src, rep(NA_real_, length(dates_src) - length(values_src)))
  }
  if (length(target_dates) == 0L) return(numeric(0))

  if (all(is.na(dates_src))) {
    fin <- values_src[is.finite(values_src)]
    if (length(fin) == 0L) {
      return(rep(as.numeric(fill_value), length(target_dates)))
    }
    if (length(fin) >= length(target_dates)) {
      return(tail(fin, length(target_dates)))
    }
    return(c(rep(fin[[1L]], length(target_dates) - length(fin)), fin))
  }

  ord <- order(dates_src)
  dates_ord <- as.Date(dates_src[ord])
  vals_ord <- values_src[ord]

  # keep latest duplicate per date
  keep <- !duplicated(dates_ord, fromLast = TRUE)
  dates_ord <- dates_ord[keep]
  vals_ord <- vals_ord[keep]

  out <- rep(as.numeric(fill_value), length(target_dates))
  mt <- match(as.Date(target_dates), dates_ord)
  matched <- which(is.finite(mt))
  if (length(matched) > 0L) {
    out[matched] <- vals_ord[mt[matched]]
  }
  out[!is.finite(out)] <- as.numeric(fill_value)
  out
}

ndlm_univar_build_covariate_series <- function(path, cov_name, history_dates, forecast_dates) {
  if (is.null(path) || !nzchar(path) || !file.exists(path)) {
    return(list(
      history = rep(0, length(history_dates)),
      forecast = rep(0, length(forecast_dates))
    ))
  }

  df <- ndlm_univar_read_csv(path, sprintf("covariate_%s", cov_name))
  val <- ndlm_univar_pick_numeric_column(
    df,
    preferred = c(cov_name, paste0(cov_name, "_value"), "value", "x", "data")
  )
  if (is.null(val)) {
    return(list(
      history = rep(0, length(history_dates)),
      forecast = rep(0, length(forecast_dates))
    ))
  }

  dt <- ndlm_univar_pick_date_column(df)
  hist_vals <- ndlm_univar_align_cov_by_dates(dt, val, history_dates, fill_value = 0)
  fore_vals <- ndlm_univar_align_cov_by_dates(dt, val, forecast_dates, fill_value = if (length(hist_vals) > 0L) tail(hist_vals, 1L) else 0)
  list(history = hist_vals, forecast = fore_vals)
}

ndlm_univar_find_input <- function(env_key, shared_root, rel_path) {
  p <- Sys.getenv(env_key, "")
  if (nzchar(p)) {
    return(normalizePath(p, mustWork = FALSE))
  }
  if (!nzchar(shared_root)) return("")
  normalizePath(file.path(shared_root, rel_path), mustWork = FALSE)
}

ndlm_univar_load_inputs <- function(constants) {
  shared_root <- Sys.getenv("NDLM_SHARED_INPUT_ROOT", "")
  if (nzchar(shared_root)) shared_root <- normalizePath(shared_root, mustWork = FALSE)

  retros_path <- ndlm_univar_find_input("NDLM_RETROS_CSV", shared_root, file.path("retros", "retros.csv"))
  nws_path <- ndlm_univar_find_input("NDLM_NWS_FORECAST_CSV", shared_root, file.path("forecasts", "nws_forecast.csv"))
  glofas_path <- ndlm_univar_find_input("NDLM_GLOFAS_FORECAST_CSV", shared_root, file.path("forecasts", "glofas_forecast.csv"))

  retros_df <- ndlm_univar_read_csv(retros_path, "retros")
  nws_df <- ndlm_univar_read_csv(nws_path, "nws_forecast")
  glofas_df <- ndlm_univar_read_csv(glofas_path, "glofas_forecast")

  y_raw <- ndlm_univar_pick_numeric_column(
    retros_df,
    preferred = c("USGS", "usgs", "y", "obs", "flow", "value")
  )
  if (is.null(y_raw)) {
    stop(sprintf("ndlm_univar retros has no usable numeric target column: %s", retros_path), call. = FALSE)
  }

  retros_dates <- ndlm_univar_pick_date_column(retros_df)
  cutoff_raw <- Sys.getenv("UNIFIED_CUTOFF_DATE", "")
  cutoff_date <- suppressWarnings(as.Date(cutoff_raw))
  if (is.na(cutoff_date)) {
    finite_dates <- retros_dates[!is.na(retros_dates)]
    cutoff_date <- if (length(finite_dates) > 0L) max(finite_dates, na.rm = TRUE) else as.Date("2022-12-25")
  }
  forecast_start_date <- cutoff_date + 1L

  keep_idx <- is.finite(y_raw)
  if (any(!is.na(retros_dates))) {
    keep_idx <- keep_idx & !is.na(retros_dates) & retros_dates <= cutoff_date
  }
  y_hist <- as.numeric(y_raw[keep_idx])
  if (length(y_hist) < 30L) {
    stop("ndlm_univar requires at least 30 finite historical observations", call. = FALSE)
  }

  dates_hist <- retros_dates[keep_idx]
  if (all(is.na(dates_hist))) {
    dates_hist <- seq(cutoff_date - (length(y_hist) - 1L), cutoff_date, by = "1 day")
  }

  nws_vec <- ndlm_univar_pick_numeric_column(nws_df, preferred = c("nws", "forecast", "value", "flow"))
  glofas_vec <- ndlm_univar_pick_numeric_column(glofas_df, preferred = c("glofas", "forecast", "value", "flow", "member_value"))
  if (is.null(nws_vec) || is.null(glofas_vec)) {
    stop("ndlm_univar forecast CSVs require numeric forecast columns", call. = FALSE)
  }
  nws_vec <- as.numeric(nws_vec)
  glofas_vec <- as.numeric(glofas_vec)
  nws_vec <- nws_vec[is.finite(nws_vec)]
  glofas_vec <- glofas_vec[is.finite(glofas_vec)]

  k_nws <- min(length(nws_vec), constants$horizon_cap)
  k_glofas <- min(length(glofas_vec), constants$horizon_cap)
  if (k_nws < 3L || k_glofas < 3L) {
    stop("ndlm_univar requires at least 3 finite forecast leads for both nws and glofas", call. = FALSE)
  }

  K_overlap <- min(k_nws, k_glofas)
  K_max <- max(k_nws, k_glofas)
  forecast_dates <- seq(forecast_start_date, by = "1 day", length.out = K_max)

  cov_paths <- c(
    ELI = Sys.getenv("NDLM_COV1_ELI_CSV", ""),
    ONI = Sys.getenv("NDLM_COV2_ONI_CSV", ""),
    PPT = Sys.getenv("NDLM_PPT_CSV", ""),
    SOIL = Sys.getenv("NDLM_SOIL_CSV", ""),
    PCA = Sys.getenv("NDLM_PCA_CSV", "")
  )

  cov_hist <- matrix(0, nrow = length(y_hist), ncol = length(cov_paths))
  cov_future <- matrix(0, nrow = K_max, ncol = length(cov_paths))
  colnames(cov_hist) <- names(cov_paths)
  colnames(cov_future) <- names(cov_paths)

  for (j in seq_along(cov_paths)) {
    ser <- ndlm_univar_build_covariate_series(
      path = cov_paths[[j]],
      cov_name = names(cov_paths)[[j]],
      history_dates = dates_hist,
      forecast_dates = forecast_dates
    )
    cov_hist[, j] <- as.numeric(ser$history)
    cov_future[, j] <- as.numeric(ser$forecast)
  }

  list(
    y = as.numeric(y_hist),
    dates_hist = as.Date(dates_hist),
    cutoff_date = as.Date(cutoff_date),
    forecast_start_date = as.Date(forecast_start_date),
    forecast_dates = as.Date(forecast_dates),
    X_hist = cov_hist,
    X_future = cov_future,
    forecast = list(
      nws = as.numeric(nws_vec[seq_len(k_nws)]),
      glofas = as.numeric(glofas_vec[seq_len(k_glofas)]),
      K_overlap = as.integer(K_overlap),
      K_max = as.integer(K_max),
      K_vec = c(nws = as.integer(k_nws), glofas = as.integer(k_glofas)),
      K_cap = as.integer(constants$horizon_cap)
    ),
    input_paths = list(
      retros = retros_path,
      nws = nws_path,
      glofas = glofas_path,
      covariates = as.list(cov_paths)
    )
  )
}
