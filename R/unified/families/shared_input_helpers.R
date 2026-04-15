family_shared_read_csv <- function(path, label) {
  if (is.null(path) || !nzchar(path)) {
    stop(sprintf("input %s path is empty", label), call. = FALSE)
  }
  if (!file.exists(path)) {
    stop(sprintf("input %s missing: %s", label, path), call. = FALSE)
  }
  out <- tryCatch(
    utils::read.csv(path, stringsAsFactors = FALSE, check.names = FALSE),
    error = function(e) e
  )
  if (inherits(out, "error") || !is.data.frame(out)) {
    stop(sprintf("input %s unreadable CSV: %s", label, path), call. = FALSE)
  }
  if (nrow(out) < 1L || ncol(out) < 1L) {
    stop(sprintf("input %s is empty: %s", label, path), call. = FALSE)
  }
  out
}

family_shared_normalize_name <- function(x) {
  gsub("[^a-z0-9]+", "", tolower(as.character(x)))
}

family_shared_pick_numeric_column <- function(df, preferred = character(0), exclude_time_like = TRUE) {
  nm_norm <- family_shared_normalize_name(names(df))
  if (length(preferred) > 0L) {
    pref_norm <- unique(family_shared_normalize_name(preferred))
    for (cand in pref_norm) {
      idx <- which(nm_norm == cand)
      if (length(idx) < 1L) next
      col <- suppressWarnings(as.numeric(df[[idx[[1L]]]]))
      if (any(is.finite(col))) {
        return(col)
      }
    }
  }

  num_idx <- which(vapply(df, is.numeric, logical(1)))
  if (length(num_idx) < 1L) {
    return(NULL)
  }
  if (isTRUE(exclude_time_like)) {
    drop_pat <- "^(date|time|timestamp|index|idx|year|month|day|julian)$"
    keep <- !grepl(drop_pat, nm_norm[num_idx])
    if (any(keep)) {
      num_idx <- num_idx[keep]
    }
  }
  if (length(num_idx) < 1L) {
    return(NULL)
  }
  col <- suppressWarnings(as.numeric(df[[num_idx[[1L]]]]))
  if (!any(is.finite(col))) {
    return(NULL)
  }
  col
}

family_shared_shift_date_years <- function(x, years_back) {
  if (!length(x)) return(as.Date(character(0)))
  if (requireNamespace("lubridate", quietly = TRUE)) {
    return(as.Date(x - lubridate::years(as.integer(years_back))))
  }
  as.Date(as.numeric(x) - round(as.numeric(years_back) * 365.2425), origin = "1970-01-01")
}

family_shared_pick_date_column <- function(df, cov_name = NULL) {
  nms <- names(df)
  if (!length(nms)) return(rep(as.Date(NA), nrow(df)))
  candidates <- unique(c(
    nms[grepl("date|time|timestamp", tolower(nms))],
    nms[[1L]]
  ))
  cov_key <- toupper(trimws(as.character(cov_name[[1L]])))
  min_good <- max(1L, min(10L, floor(0.7 * nrow(df))))

  parse_one <- function(v, shift_eli = FALSE) {
    if (inherits(v, "Date")) {
      return(as.Date(v))
    }
    if (is.numeric(v)) {
      d <- suppressWarnings(as.Date(v, origin = "1970-01-01"))
      if (shift_eli) {
        d <- family_shared_shift_date_years(d, 170L)
      }
      return(d)
    }
    suppressWarnings(as.Date(v))
  }

  for (nm in candidates) {
    vals <- df[[nm]]
    d <- parse_one(vals, shift_eli = FALSE)
    if (sum(!is.na(d)) >= min_good) {
      return(d)
    }
    if (identical(cov_key, "ELI")) {
      d_eli <- parse_one(vals, shift_eli = TRUE)
      if (sum(!is.na(d_eli)) >= min_good) {
        return(d_eli)
      }
    }
  }
  rep(as.Date(NA), nrow(df))
}

family_shared_feature_columns <- function(df) {
  if (!is.data.frame(df) || ncol(df) < 1L) return(character(0))
  nm <- names(df)
  nm_norm <- family_shared_normalize_name(nm)
  num_idx <- which(vapply(df, is.numeric, logical(1)))
  if (length(num_idx) < 1L) return(character(0))
  drop_pat <- "^(date|time|timestamp|index|idx|year|month|day|julian)$"
  keep <- !grepl(drop_pat, nm_norm[num_idx])
  if (any(keep)) {
    num_idx <- num_idx[keep]
  }
  nm[num_idx]
}

family_shared_build_feature_matrices <- function(path, history_dates, forecast_dates = NULL, fill_value = 0, scale_with_history = TRUE) {
  history_dates <- as.Date(history_dates)
  forecast_dates <- as.Date(forecast_dates)
  if (is.null(path) || !nzchar(path) || !file.exists(path)) {
    return(list(
      history = matrix(numeric(0), nrow = length(history_dates), ncol = 0L),
      forecast = matrix(numeric(0), nrow = length(forecast_dates), ncol = 0L),
      feature_names = character(0),
      scales = numeric(0)
    ))
  }

  df <- family_shared_read_csv(path, "covariate_features")
  feature_cols <- family_shared_feature_columns(df)
  if (length(feature_cols) < 1L) {
    stop(sprintf("covariate feature table has no numeric feature columns: %s", path), call. = FALSE)
  }
  src_dates <- family_shared_pick_date_column(df, cov_name = "FEATURES")
  if (all(is.na(src_dates))) {
    stop(sprintf("covariate feature table has no parseable date column: %s", path), call. = FALSE)
  }

  hist_cols <- vector("list", length(feature_cols))
  fore_cols <- vector("list", length(feature_cols))
  scales <- rep(NA_real_, length(feature_cols))
  for (i in seq_along(feature_cols)) {
    vals <- suppressWarnings(as.numeric(df[[feature_cols[[i]]]]))
    hist_vals_raw <- family_shared_align_by_dates(src_dates, vals, history_dates, fill_value = NA_real_)
    fore_vals_raw <- family_shared_align_by_dates(src_dates, vals, forecast_dates, fill_value = NA_real_)
    if (isTRUE(scale_with_history)) {
      scaled <- family_shared_sd_scale_history_future(hist_vals_raw, fore_vals_raw)
      fill_scaled <- as.numeric(fill_value) / scaled$sd
      hist_vals <- scaled$history
      fore_vals <- scaled$future
      hist_vals[!is.finite(hist_vals_raw)] <- fill_scaled
      fore_vals[!is.finite(fore_vals_raw)] <- fill_scaled
      hist_cols[[i]] <- hist_vals
      fore_cols[[i]] <- fore_vals
      scales[[i]] <- scaled$sd
    } else {
      hist_vals <- hist_vals_raw
      fore_vals <- fore_vals_raw
      hist_vals[!is.finite(hist_vals)] <- as.numeric(fill_value)
      fore_vals[!is.finite(fore_vals)] <- as.numeric(fill_value)
      hist_cols[[i]] <- hist_vals
      fore_cols[[i]] <- fore_vals
    }
  }

  history_mat <- if (length(hist_cols) > 0L) do.call(cbind, hist_cols) else matrix(numeric(0), nrow = length(history_dates), ncol = 0L)
  forecast_mat <- if (length(fore_cols) > 0L) do.call(cbind, fore_cols) else matrix(numeric(0), nrow = length(forecast_dates), ncol = 0L)
  if (!is.matrix(history_mat)) history_mat <- matrix(history_mat, ncol = length(feature_cols))
  if (!is.matrix(forecast_mat)) forecast_mat <- matrix(forecast_mat, ncol = length(feature_cols))
  colnames(history_mat) <- feature_cols
  colnames(forecast_mat) <- feature_cols

  list(
    history = history_mat,
    forecast = forecast_mat,
    feature_names = feature_cols,
    scales = setNames(scales, feature_cols)
  )
}

family_shared_tail_align_series <- function(x, target_len, fill = 0) {
  x <- as.numeric(x)
  x <- x[is.finite(x)]
  target_len <- suppressWarnings(as.integer(target_len[[1L]]))
  if (!is.finite(target_len) || target_len <= 0L) return(numeric(0))
  if (length(x) == 0L) return(rep(as.numeric(fill), target_len))
  if (length(x) >= target_len) return(tail(x, target_len))
  c(rep(as.numeric(fill), target_len - length(x)), x)
}

family_shared_align_by_dates <- function(dates_src, values_src, target_dates, fill_value = 0) {
  values_src <- as.numeric(values_src)
  target_dates <- as.Date(target_dates)
  if (length(target_dates) == 0L) return(numeric(0))
  if (length(values_src) < length(dates_src)) {
    values_src <- c(values_src, rep(NA_real_, length(dates_src) - length(values_src)))
  }
  if (all(is.na(dates_src))) {
    return(family_shared_tail_align_series(values_src, length(target_dates), fill = fill_value))
  }

  ord <- order(dates_src)
  dates_ord <- as.Date(dates_src[ord])
  vals_ord <- values_src[ord]
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

family_shared_sd_scale_history_future <- function(history, future = NULL) {
  history <- as.numeric(history)
  future <- as.numeric(future)
  hist_finite <- history[is.finite(history)]
  sd_hist <- suppressWarnings(stats::sd(hist_finite, na.rm = TRUE))
  if (!is.finite(sd_hist) || sd_hist <= 1e-8) {
    sd_hist <- 1
  }
  history_scaled <- history / sd_hist
  history_scaled[!is.finite(history_scaled)] <- 0
  future_scaled <- future / sd_hist
  future_scaled[!is.finite(future_scaled)] <- 0
  list(
    history = history_scaled,
    future = future_scaled,
    sd = sd_hist
  )
}

family_shared_covariate_preferences <- function(cov_name) {
  cov_key <- toupper(trimws(as.character(cov_name[[1L]])))
  switch(
    cov_key,
    ELI = c("ELI_lon", "ELI", "eli_lon", "eli", "value"),
    ONI = c("nino34", "oni", "ONI", "nino3.4", "nino_34", "value"),
    PPT = c("PRCP_mm", "ppt", "precip", "prcp", "precipitation", "value"),
    SOIL = c("Daily_Avg_Soil_Moisture", "soil", "soil_moisture", "daily_avg_soil_moisture", "value"),
    PCA = c("Static_PCA", "PCA", "static_pca", "pca", "value"),
    c(as.character(cov_name), "value", "x", "data")
  )
}

family_shared_build_covariate_series <- function(path, cov_name, history_dates, forecast_dates = NULL, fill_value = 0, scale_with_history = TRUE) {
  history_dates <- as.Date(history_dates)
  forecast_dates <- as.Date(forecast_dates)
  if (is.null(path) || !nzchar(path) || !file.exists(path)) {
    hist <- rep(as.numeric(fill_value), length(history_dates))
    fore <- rep(as.numeric(fill_value), length(forecast_dates))
    if (isTRUE(scale_with_history)) {
      scaled <- family_shared_sd_scale_history_future(hist, fore)
      return(list(history = scaled$history, forecast = scaled$future, sd = scaled$sd))
    }
    return(list(history = hist, forecast = fore, sd = NA_real_))
  }

  df <- family_shared_read_csv(path, sprintf("covariate_%s", cov_name))
  val <- family_shared_pick_numeric_column(
    df,
    preferred = family_shared_covariate_preferences(cov_name),
    exclude_time_like = TRUE
  )
  if (is.null(val)) {
    hist <- rep(as.numeric(fill_value), length(history_dates))
    fore <- rep(as.numeric(fill_value), length(forecast_dates))
    if (isTRUE(scale_with_history)) {
      scaled <- family_shared_sd_scale_history_future(hist, fore)
      return(list(history = scaled$history, forecast = scaled$future, sd = scaled$sd))
    }
    return(list(history = hist, forecast = fore, sd = NA_real_))
  }

  dt <- family_shared_pick_date_column(df, cov_name = cov_name)
  hist_vals <- family_shared_align_by_dates(dt, val, history_dates, fill_value = fill_value)
  finite_vals <- as.numeric(val[is.finite(val)])
  fore_fill <- if (length(finite_vals) > 0L) tail(finite_vals, 1L) else fill_value
  fore_vals <- family_shared_align_by_dates(dt, val, forecast_dates, fill_value = fore_fill)
  if (isTRUE(scale_with_history)) {
    scaled <- family_shared_sd_scale_history_future(hist_vals, fore_vals)
    return(list(history = scaled$history, forecast = scaled$future, sd = scaled$sd))
  }
  list(history = hist_vals, forecast = fore_vals, sd = NA_real_)
}

family_shared_extract_forecast_mean <- function(df, label, transform = c("none", "log1p", "log")) {
  transform <- match.arg(transform)
  if (!is.data.frame(df) || nrow(df) < 1L) {
    stop(sprintf("%s must be a non-empty data.frame", label), call. = FALSE)
  }
  nm_norm <- family_shared_normalize_name(names(df))
  num_idx <- which(vapply(df, is.numeric, logical(1)))
  if (length(num_idx) < 1L) {
    stop(sprintf("%s has no numeric forecast columns", label), call. = FALSE)
  }
  keep <- !grepl("^(date|time|timestamp|index|idx|year|month|day)$", nm_norm[num_idx])
  if (any(keep)) {
    num_idx <- num_idx[keep]
  }
  if (length(num_idx) < 1L) {
    stop(sprintf("%s has no usable ensemble member columns after excluding date/time fields", label), call. = FALSE)
  }
  mat <- data.matrix(df[, num_idx, drop = FALSE])
  if (!all(is.finite(mat))) {
    mat[!is.finite(mat)] <- NA_real_
  }
  if (identical(transform, "log1p")) {
    if (any(mat < 0, na.rm = TRUE)) {
      stop(sprintf("%s contains negative values; cannot apply log1p transform safely", label), call. = FALSE)
    }
    mat <- log1p(mat)
  } else if (identical(transform, "log")) {
    if (any(mat <= 0, na.rm = TRUE)) {
      stop(sprintf("%s contains non-positive values; cannot apply log transform safely", label), call. = FALSE)
    }
    mat <- log(mat)
  }
  out <- rowMeans(mat, na.rm = TRUE)
  out[!is.finite(out)] <- NA_real_
  out
}

family_shared_extract_forecast_ensemble <- function(
  df,
  label,
  transform = c("none", "log1p", "log"),
  target_dates = NULL
) {
  transform <- match.arg(transform)
  if (!is.data.frame(df) || nrow(df) < 1L) {
    stop(sprintf("%s must be a non-empty data.frame", label), call. = FALSE)
  }

  nm_norm <- family_shared_normalize_name(names(df))
  num_idx <- which(vapply(df, is.numeric, logical(1)))
  if (length(num_idx) < 1L) {
    stop(sprintf("%s has no numeric forecast columns", label), call. = FALSE)
  }
  keep <- !grepl("^(date|time|timestamp|index|idx|year|month|day)$", nm_norm[num_idx])
  if (any(keep)) {
    num_idx <- num_idx[keep]
  }
  if (length(num_idx) < 1L) {
    stop(sprintf("%s has no usable ensemble member columns after excluding date/time fields", label), call. = FALSE)
  }

  mat <- data.matrix(df[, num_idx, drop = FALSE])
  if (!all(is.finite(mat))) {
    mat[!is.finite(mat)] <- NA_real_
  }
  if (identical(transform, "log1p")) {
    if (any(mat < 0, na.rm = TRUE)) {
      stop(sprintf("%s contains negative values; cannot apply log1p transform safely", label), call. = FALSE)
    }
    mat <- log1p(mat)
  } else if (identical(transform, "log")) {
    if (any(mat <= 0, na.rm = TRUE)) {
      stop(sprintf("%s contains non-positive values; cannot apply log transform safely", label), call. = FALSE)
    }
    mat <- log(mat)
  }

  src_dates <- family_shared_pick_date_column(df)
  target_dates <- as.Date(target_dates)
  if (length(target_dates) > 0L) {
    aligned <- matrix(NA_real_, nrow = length(target_dates), ncol = ncol(mat))
    if (!all(is.na(src_dates))) {
      ord <- order(src_dates)
      src_dates_ord <- as.Date(src_dates[ord])
      mat_ord <- mat[ord, , drop = FALSE]
      keep_last <- !duplicated(src_dates_ord, fromLast = TRUE)
      src_dates_ord <- src_dates_ord[keep_last]
      mat_ord <- mat_ord[keep_last, , drop = FALSE]
      mt <- match(target_dates, src_dates_ord)
      hit <- which(!is.na(mt))
      if (length(hit) > 0L) {
        aligned[hit, ] <- mat_ord[mt[hit], , drop = FALSE]
      }
    } else {
      take <- seq_len(min(nrow(mat), length(target_dates)))
      aligned[take, ] <- mat[take, , drop = FALSE]
    }
    mat <- aligned
    src_dates <- target_dates
  }

  row_means <- rowMeans(mat, na.rm = TRUE)
  row_means[!is.finite(row_means)] <- NA_real_
  list(
    members = mat,
    row_means = as.numeric(row_means),
    dates = as.Date(src_dates),
    member_cols = names(df)[num_idx]
  )
}
