###############################################################################
# Helper functions (core)
# Inputs:
#   - Data/matrix objects passed from later modules
# Outputs:
#   - Utility functions for model computations and checks
# Dependencies:
#   - Base R + Matrix + dlm-related functions
###############################################################################

# Function to check if a matrix is positive definite
is_positive_definite <- function(x) {
  eigenvalues <- eigen(x)$values
  return(all(eigenvalues > 0))
}

# Function to compute inverse or square root of inverse using Cholesky Decomposition
compute_cholesky <- function(q, compute_sqrt_inverse = FALSE) {
  if (!is_positive_definite(q)) {
    stop("The matrix is not positive definite.")
  }
  
  # Compute Cholesky decomposition
  chol_decomp <- chol(as.matrix(q))
  
  # Convert to Matrix class to use with chol2inv
  U <- Matrix(chol_decomp, sparse = TRUE)
  
  # Compute inverse using Cholesky decomposition
  inv_q <- chol2inv(U)
  
  if (!compute_sqrt_inverse) {
    return(list(inverse = inv_q))
  } else {
    # Compute square root of the inverse
    # The square root of the inverse in this context is the inverse of the upper triangular matrix U
    sqrt_inv_q <- solve(U)
    
    # Check if the square root of the inverse times itself results in the inverse
    sqrt_inv_q_product <- sqrt_inv_q %*% t(sqrt_inv_q)
    is_correct <- all.equal(sqrt_inv_q_product, inv_q, tolerance = 1e-12)
    
    return(list(inverse = inv_q, sqrt_inverse = sqrt_inv_q, check = is_correct))
  }
}

# Stable sort policy for forecast sample slices.
# Default keeps NA values to preserve vector length during array-slice assignment.
sort_keep_na <- function(x, keep_na = NULL) {
  if (is.null(keep_na)) {
    keep_na_env <- Sys.getenv("ENV_SORT_KEEP_NA", "TRUE")
    keep_na <- isTRUE(as.logical(keep_na_env))
  }
  if (isTRUE(keep_na)) {
    return(sort(x, na.last = TRUE))
  }
  sort(x)
}

# Sort a vector while guaranteeing exact output length for safe array-slice writes.
sort_to_len <- function(x, target_len, keep_na = NULL, fill = NA_real_, context = NULL) {
  if (length(target_len) != 1L || is.na(target_len) || target_len < 0) {
    stop(sprintf("sort_to_len target_len must be a single non-negative integer; got: %s", paste(target_len, collapse = ",")))
  }

  target_len <- as.integer(target_len)
  sorted <- sort_keep_na(as.vector(x), keep_na = keep_na)
  cur_len <- length(sorted)

  if (cur_len == target_len) {
    return(sorted)
  }

  if (cur_len == 0L && target_len > 0L) {
    if (!is.null(context) && nzchar(context)) {
      warning(sprintf("sort_to_len received empty input for %s; padding to target length %d", context, target_len), call. = FALSE)
    }
    return(rep(fill, target_len))
  }

  if (cur_len < target_len) {
    return(c(sorted, rep(fill, target_len - cur_len)))
  }

  sorted[seq_len(target_len)]
}

build_agg_discrep_quantile_df <- function(
  q_array,
  idx,
  dates,
  quantile_rows = c(1L, 4L, 7L),
  quantile_labels = c("5th", "50th", "95th"),
  context = "agg_discrep"
) {
  if (!is.numeric(q_array) || is.null(dim(q_array)) || length(dim(q_array)) != 3L) {
    stop(sprintf("[%s_SHAPE] q_array must be numeric 3D [quantile_row x time x summary].", context))
  }
  if (dim(q_array)[3] < 3L) {
    stop(sprintf("[%s_SUMMARY_DIM] q_array third dimension must contain at least 3 summary slots.", context))
  }

  idx <- as.integer(idx)
  if (length(idx) == 0L || any(!is.finite(idx)) || any(idx < 1L)) {
    stop(sprintf("[%s_INDEX] idx must contain positive finite indices.", context))
  }
  if (max(idx) > dim(q_array)[2]) {
    stop(
      sprintf(
        "[%s_INDEX_OOB] idx max=%d exceeds q_array time dimension=%d.",
        context,
        as.integer(max(idx)),
        as.integer(dim(q_array)[2])
      )
    )
  }

  quantile_rows <- as.integer(quantile_rows)
  if (length(quantile_rows) != length(quantile_labels)) {
    stop(sprintf("[%s_LABEL_MAP] quantile_rows and quantile_labels must have the same length.", context))
  }
  if (any(!is.finite(quantile_rows)) || any(quantile_rows < 1L) || any(quantile_rows > dim(q_array)[1])) {
    stop(
      sprintf(
        "[%s_ROW_OOB] quantile_rows must be within [1, %d].",
        context,
        as.integer(dim(q_array)[1])
      )
    )
  }

  dates <- as.Date(dates)
  if (length(dates) != length(idx)) {
    stop(
      sprintf(
        "[%s_DATE_LEN] dates length=%d must equal idx length=%d.",
        context,
        as.integer(length(dates)),
        as.integer(length(idx))
      )
    )
  }

  rows <- lapply(seq_along(quantile_rows), function(i) {
    row_id <- quantile_rows[[i]]
    lower_raw <- q_array[row_id, idx, 1]
    upper_raw <- q_array[row_id, idx, 3]
    data.frame(
      Date = dates,
      Quantile = as.character(quantile_labels[[i]]),
      Lower = pmin(lower_raw, upper_raw),
      Median = q_array[row_id, idx, 2],
      Upper = pmax(lower_raw, upper_raw),
      stringsAsFactors = FALSE
    )
  })
  dplyr::bind_rows(rows)
}

resolve_agg_discrep_ylim <- function(
  obs,
  fitted_df,
  preferred_ylim = NULL,
  min_inrange_share = 0.15,
  pad_frac = 0.05,
  min_span = 0.1,
  context = "agg_discrep"
) {
  obs <- as.numeric(obs)
  if (!is.data.frame(fitted_df) ||
      !all(c("Lower", "Median", "Upper") %in% names(fitted_df))) {
    stop(sprintf("[%s_FITTED_SCHEMA] fitted_df must contain Lower/Median/Upper columns.", context))
  }

  fitted_vals <- c(
    as.numeric(fitted_df$Lower),
    as.numeric(fitted_df$Median),
    as.numeric(fitted_df$Upper)
  )
  obs_finite <- obs[is.finite(obs)]
  fitted_finite <- fitted_vals[is.finite(fitted_vals)]
  combined <- c(obs_finite, fitted_finite)
  if (length(combined) == 0L) {
    stop(sprintf("[%s_EMPTY_SERIES] no finite observed/fitted values available to resolve ylim.", context))
  }

  pref_valid <- FALSE
  pref <- c(NA_real_, NA_real_)
  if (!is.null(preferred_ylim)) {
    pref <- as.numeric(preferred_ylim)
    pref_valid <- length(pref) == 2L && all(is.finite(pref)) && pref[1] < pref[2]
  }

  inrange_share <- NA_real_
  use_preferred <- FALSE
  if (pref_valid && length(fitted_finite) > 0L) {
    inrange_share <- mean(fitted_finite >= pref[1] & fitted_finite <= pref[2])
    use_preferred <- is.finite(inrange_share) && inrange_share >= as.numeric(min_inrange_share)
  } else if (pref_valid && length(fitted_finite) == 0L) {
    use_preferred <- TRUE
  }

  if (use_preferred) {
    return(list(
      ylim = pref,
      mode = "preferred",
      preferred_inrange_share = inrange_share,
      fitted_finite_n = as.integer(length(fitted_finite)),
      obs_finite_n = as.integer(length(obs_finite)),
      combined_min = min(combined),
      combined_max = max(combined),
      preferred_min = pref[1],
      preferred_max = pref[2]
    ))
  }

  y_min <- min(combined)
  y_max <- max(combined)
  span <- y_max - y_min
  if (!is.finite(span) || span < as.numeric(min_span)) {
    mid <- mean(c(y_min, y_max))
    span <- as.numeric(min_span)
    y_min <- mid - 0.5 * span
    y_max <- mid + 0.5 * span
  }
  pad <- max(as.numeric(pad_frac) * span, 1e-6)
  dyn <- c(y_min - pad, y_max + pad)

  list(
    ylim = dyn,
    mode = if (pref_valid) "expanded" else "expanded_no_preferred",
    preferred_inrange_share = inrange_share,
    fitted_finite_n = as.integer(length(fitted_finite)),
    obs_finite_n = as.integer(length(obs_finite)),
    combined_min = min(combined),
    combined_max = max(combined),
    preferred_min = if (pref_valid) pref[1] else NA_real_,
    preferred_max = if (pref_valid) pref[2] else NA_real_
  )
}

forecast_cube_effective_horizon <- function(cube, context = "forecast_cube") {
  if (!is.numeric(cube)) {
    stop(sprintf("[FORECAST_CUBE_TYPE] %s must be a numeric 3D array.", context))
  }
  d <- dim(cube)
  if (is.null(d) || length(d) != 3L) {
    stop(sprintf("[FORECAST_CUBE_DIM] %s must be a 3D array [quantile x sample x time].", context))
  }
  n_t <- as.integer(d[[3L]])
  if (!is.finite(n_t) || n_t <= 0L) {
    stop(sprintf("[FORECAST_CUBE_EMPTY] %s has no forecast time dimension.", context))
  }

  finite_by_t <- vapply(
    seq_len(n_t),
    function(t) all(is.finite(cube[, , t])),
    logical(1)
  )

  if (!any(finite_by_t)) {
    stop(sprintf("[FORECAST_CUBE_EMPTY] %s has no fully finite forecast slices.", context))
  }

  last_finite <- max(which(finite_by_t))
  interior_missing <- which(!finite_by_t[seq_len(last_finite)])
  if (length(interior_missing) > 0L) {
    stop(
      sprintf(
        "[FORECAST_CUBE_GAP] %s has non-finite interior forecast slices before horizon end at t=%d (first bad t=%d).",
        context,
        as.integer(last_finite),
        as.integer(interior_missing[[1L]])
      )
    )
  }

  trailing_missing <- which(!finite_by_t & seq_len(n_t) > last_finite)
  if (length(trailing_missing) > 0L) {
    warning(
      sprintf(
        "[FORECAST_CUBE_TRUNCATE] %s contains trailing non-finite slices; effective horizon reduced from %d to %d.",
        context,
        as.integer(n_t),
        as.integer(last_finite)
      ),
      call. = FALSE
    )
  }

  list(
    horizon = as.integer(last_finite),
    finite_mask = finite_by_t,
    trailing_missing = as.integer(length(trailing_missing))
  )
}

trim_forecast_cube_to_effective_horizon <- function(cube, context = "forecast_cube") {
  info <- forecast_cube_effective_horizon(cube, context = context)
  n_t <- dim(cube)[3]
  if (info$horizon >= n_t) {
    return(list(cube = cube, info = info))
  }
  list(
    cube = cube[, , seq_len(info$horizon), drop = FALSE],
    info = info
  )
}

post_export_tables_enabled <- function(default = TRUE) {
  if (exists("EXPORT_TABLES", inherits = TRUE)) {
    return(isTRUE(get("EXPORT_TABLES", inherits = TRUE)))
  }
  isTRUE(as.logical(Sys.getenv("EXPORT_TABLES", if (isTRUE(default)) "TRUE" else "FALSE")))
}

post_quantile_label_to_int <- function(x) {
  x <- as.character(x)
  x <- gsub("[^0-9]", "", x)
  out <- suppressWarnings(as.integer(x))
  out
}

post_ci_string <- function(lower, upper, digits = 3L) {
  lower <- as.numeric(lower)
  upper <- as.numeric(upper)
  fmt <- paste0("%.", as.integer(digits), "f")
  out <- rep(NA_character_, length(lower))
  ok <- is.finite(lower) & is.finite(upper)
  out[ok] <- sprintf(paste0(fmt, ", ", fmt), lower[ok], upper[ok])
  out
}

post_write_csv <- function(df, path) {
  dir.create(dirname(path), recursive = TRUE, showWarnings = FALSE)
  write.csv(df, file = path, row.names = FALSE)
  invisible(path)
}

post_table_formats <- function(default = c("csv")) {
  raw <- Sys.getenv("EXPORT_TABLE_FORMATS", "")
  if (!nzchar(raw)) {
    return(unique(tolower(as.character(default))))
  }
  vals <- trimws(unlist(strsplit(raw, ",", fixed = TRUE), use.names = FALSE))
  vals <- vals[nzchar(vals)]
  if (length(vals) == 0L) {
    return(unique(tolower(as.character(default))))
  }
  unique(tolower(vals))
}

post_table_row_order <- function(df, sort_keys = NULL) {
  n <- nrow(df)
  if (n <= 1L) return(seq_len(n))

  if (!is.null(sort_keys) && length(sort_keys) > 0L) {
    keys <- intersect(as.character(sort_keys), names(df))
  } else {
    keys <- character(0)
  }
  # Preserve caller-provided row order unless explicit valid sort keys are provided.
  if (length(keys) == 0L) {
    return(seq_len(n))
  }

  key_cols <- lapply(keys, function(k) {
    v <- df[[k]]
    if (inherits(v, "factor")) {
      as.character(v)
    } else {
      v
    }
  })
  do.call(order, c(key_cols, list(na.last = TRUE, method = "radix")))
}

post_drop_na_rows <- function(df, keep_na = TRUE) {
  if (isTRUE(keep_na) || nrow(df) == 0L) return(df)
  df[stats::complete.cases(df), , drop = FALSE]
}

post_format_numeric_columns <- function(df, digits = 10L) {
  out <- df
  for (nm in names(out)) {
    col <- out[[nm]]
    if (is.numeric(col) && !is.integer(col)) {
      vals <- as.numeric(col)
      out[[nm]] <- ifelse(
        is.na(vals),
        NA_character_,
        formatC(vals, digits = as.integer(digits), format = "fg", flag = "#")
      )
    } else if (inherits(col, "factor")) {
      out[[nm]] <- as.character(col)
    }
  }
  out
}

post_write_csv_deterministic <- function(df, path, numeric_digits = 10L) {
  dir.create(dirname(path), recursive = TRUE, showWarnings = FALSE)
  out <- post_format_numeric_columns(df, digits = numeric_digits)
  utils::write.table(
    out,
    file = path,
    sep = ",",
    row.names = FALSE,
    col.names = TRUE,
    quote = TRUE,
    na = "NA",
    qmethod = "double",
    eol = "\n"
  )
  invisible(path)
}

post_path_relative_to_dir <- function(path, output_dir) {
  dir_abs <- normalizePath(output_dir, mustWork = TRUE)
  path_abs <- normalizePath(path, mustWork = FALSE)
  prefix <- paste0(dir_abs, .Platform$file.sep)
  if (startsWith(path_abs, prefix)) {
    return(substr(path_abs, nchar(prefix) + 1L, nchar(path_abs)))
  }
  basename(path_abs)
}

post_sha256_file <- function(path) {
  stopifnot(file.exists(path))

  if (requireNamespace("digest", quietly = TRUE)) {
    return(digest::digest(file = path, algo = "sha256"))
  }

  cmd <- Sys.which("sha256sum")
  if (nzchar(cmd)) {
    out <- tryCatch(system2(cmd, shQuote(path), stdout = TRUE, stderr = FALSE), error = function(e) character(0))
    if (length(out) >= 1L) {
      token <- strsplit(out[[1L]], "[[:space:]]+")[[1L]][1L]
      if (nzchar(token)) return(token)
    }
  }

  stop("Unable to compute sha256 (digest package or sha256sum command required).", call. = FALSE)
}

post_export_tables <- function(
  tables,
  output_dir,
  file_stems = NULL,
  formats = c("csv"),
  keep_na = TRUE,
  sort_keys = NULL,
  numeric_digits = 10L
) {
  if (is.null(tables) || length(tables) == 0L) {
    return(data.frame(
      table_name = character(0),
      file_path = character(0),
      nrow = integer(0),
      ncol = integer(0),
      sha256 = character(0),
      stringsAsFactors = FALSE
    ))
  }
  if (is.null(names(tables)) || any(!nzchar(names(tables)))) {
    stop("post_export_tables requires a named list of tables.", call. = FALSE)
  }

  formats <- unique(tolower(as.character(formats)))
  formats <- formats[formats %in% c("csv", "rds")]
  if (length(formats) == 0L) formats <- "csv"

  manifest_rows <- list()

  for (nm in names(tables)) {
    df <- as.data.frame(tables[[nm]], stringsAsFactors = FALSE)
    df <- post_drop_na_rows(df, keep_na = keep_na)

    keys <- NULL
    if (!is.null(sort_keys) && !is.null(sort_keys[[nm]])) {
      keys <- sort_keys[[nm]]
    }
    ord <- post_table_row_order(df, sort_keys = keys)
    if (length(ord) > 0L) {
      df <- df[ord, , drop = FALSE]
    }
    rownames(df) <- NULL

    stem <- nm
    if (!is.null(file_stems) && !is.null(file_stems[[nm]]) && nzchar(file_stems[[nm]])) {
      stem <- as.character(file_stems[[nm]])
    }

    for (fmt in formats) {
      path <- file.path(output_dir, sprintf("%s.%s", stem, fmt))
      if (identical(fmt, "csv")) {
        post_write_csv_deterministic(df, path, numeric_digits = numeric_digits)
      } else if (identical(fmt, "rds")) {
        dir.create(dirname(path), recursive = TRUE, showWarnings = FALSE)
        saveRDS(df, path)
      }

      manifest_rows[[length(manifest_rows) + 1L]] <- data.frame(
        table_name = nm,
        file_path = post_path_relative_to_dir(path, output_dir),
        nrow = nrow(df),
        ncol = ncol(df),
        sha256 = post_sha256_file(path),
        stringsAsFactors = FALSE
      )
    }
  }

  do.call(rbind, manifest_rows)
}

post_write_lines <- function(lines, path) {
  dir.create(dirname(path), recursive = TRUE, showWarnings = FALSE)
  writeLines(lines, con = path, useBytes = TRUE)
  invisible(path)
}

post_source_levels <- c("USGS", "GLOFAS", "NWS")
post_quantile_levels <- c(5L, 20L, 35L, 50L, 65L, 80L, 95L)
post_covariate_levels <- c("Precipitation", "Soil Moisture", "PC1", "Intercept", "Lag1", "Lag2", "Lag3", "Lag4", "Lag5")

post_component_to_covariate <- function(component) {
  component <- as.integer(component)
  mapping <- c(
    "23" = "Precipitation",
    "24" = "Soil Moisture",
    "25" = "PC1",
    "26" = "Intercept",
    "27" = "Lag1",
    "28" = "Lag2",
    "29" = "Lag3",
    "30" = "Lag4",
    "31" = "Lag5"
  )
  out <- unname(mapping[as.character(component)])
  fallback <- paste0("Component_", component)
  out[is.na(out)] <- fallback[is.na(out)]
  out
}

post_export_gamma_sigma_tables <- function(
  all_quantiles,
  output_dir,
  ci_digits = 3L,
  write_tex = TRUE,
  table_formats = c("csv"),
  keep_na = TRUE,
  numeric_digits = 10L
) {
  req_cols <- c("variable", "source", "quantile", "quantile_025", "median", "quantile_975")
  missing_cols <- setdiff(req_cols, names(all_quantiles))
  if (length(missing_cols) > 0L) {
    stop(sprintf("post_export_gamma_sigma_tables missing columns: %s", paste(missing_cols, collapse = ", ")))
  }

  vars <- tolower(as.character(all_quantiles$variable))
  keep <- vars %in% c("gamma", "sigma")
  work <- all_quantiles[keep, req_cols, drop = FALSE]
  if (nrow(work) == 0L) {
    empty <- data.frame(
      quantile = integer(0),
      source = character(0),
      stat = character(0),
      center = numeric(0),
      q2_5 = numeric(0),
      q97_5 = numeric(0),
      ci_str = character(0),
      stringsAsFactors = FALSE
    )
    manifest <- post_export_tables(
      tables = list(gamma = empty, sigma = empty),
      output_dir = output_dir,
      file_stems = list(gamma = "gamma_summary", sigma = "sigma_summary"),
      formats = table_formats,
      keep_na = keep_na,
      sort_keys = list(gamma = c("quantile", "source", "stat"), sigma = c("quantile", "source", "stat")),
      numeric_digits = numeric_digits
    )
    return(list(gamma = empty, sigma = empty, manifest = manifest))
  }

  out <- data.frame(
    quantile = post_quantile_label_to_int(work$quantile),
    source = toupper(as.character(work$source)),
    stat = tolower(as.character(work$variable)),
    center = as.numeric(work$median),
    q2_5 = as.numeric(work$quantile_025),
    q97_5 = as.numeric(work$quantile_975),
    stringsAsFactors = FALSE
  )
  out$ci_str <- post_ci_string(out$q2_5, out$q97_5, digits = ci_digits)

  out$source <- factor(out$source, levels = post_source_levels, ordered = TRUE)
  out$quantile <- as.integer(out$quantile)
  out <- out[order(out$quantile, out$source, out$stat), c("quantile", "source", "stat", "center", "q2_5", "q97_5", "ci_str")]
  rownames(out) <- NULL
  out$source <- as.character(out$source)

  gamma_df <- out[out$stat == "gamma", , drop = FALSE]
  sigma_df <- out[out$stat == "sigma", , drop = FALSE]
  manifest <- post_export_tables(
    tables = list(gamma = gamma_df, sigma = sigma_df),
    output_dir = output_dir,
    file_stems = list(gamma = "gamma_summary", sigma = "sigma_summary"),
    formats = table_formats,
    keep_na = keep_na,
    sort_keys = list(gamma = c("quantile", "source", "stat"), sigma = c("quantile", "source", "stat")),
    numeric_digits = numeric_digits
  )

  if (isTRUE(write_tex)) {
    gamma_lines <- c(
      "% quantile & source & center & [q2.5, q97.5] \\\\",
      if (nrow(gamma_df) == 0L) "% <empty>" else sprintf(
        "%d & %s & %.6f & [%.6f, %.6f] \\\\",
        gamma_df$quantile, gamma_df$source, gamma_df$center, gamma_df$q2_5, gamma_df$q97_5
      )
    )
    sigma_lines <- c(
      "% quantile & source & center & [q2.5, q97.5] \\\\",
      if (nrow(sigma_df) == 0L) "% <empty>" else sprintf(
        "%d & %s & %.6f & [%.6f, %.6f] \\\\",
        sigma_df$quantile, sigma_df$source, sigma_df$center, sigma_df$q2_5, sigma_df$q97_5
      )
    )
    post_write_lines(gamma_lines, file.path(output_dir, "gamma_summary.tex"))
    post_write_lines(sigma_lines, file.path(output_dir, "sigma_summary.tex"))
  }

  list(gamma = gamma_df, sigma = sigma_df, manifest = manifest)
}

post_export_covariate_effects_table <- function(
  summary_df,
  output_dir,
  time_index = NA_integer_,
  ci_digits = 3L,
  write_tex = TRUE,
  table_formats = c("csv"),
  keep_na = TRUE,
  numeric_digits = 10L
) {
  req_cols <- c("Component", "Quantile", "Lower", "Mean", "Upper")
  missing_cols <- setdiff(req_cols, names(summary_df))
  if (length(missing_cols) > 0L) {
    stop(sprintf("post_export_covariate_effects_table missing columns: %s", paste(missing_cols, collapse = ", ")))
  }

  out <- data.frame(
    covariate = post_component_to_covariate(summary_df$Component),
    quantile = post_quantile_label_to_int(summary_df$Quantile),
    center = as.numeric(summary_df$Mean),
    q2_5 = as.numeric(summary_df$Lower),
    q97_5 = as.numeric(summary_df$Upper),
    ci_str = NA_character_,
    time_index = as.integer(time_index),
    notes = "",
    stringsAsFactors = FALSE
  )
  out$ci_str <- post_ci_string(out$q2_5, out$q97_5, digits = ci_digits)

  out$covariate <- factor(out$covariate, levels = post_covariate_levels, ordered = TRUE)
  out$quantile <- as.integer(out$quantile)
  out <- out[order(out$covariate, out$quantile), c("covariate", "quantile", "center", "q2_5", "q97_5", "ci_str", "time_index", "notes")]
  rownames(out) <- NULL
  out$covariate <- as.character(out$covariate)

  manifest <- post_export_tables(
    tables = list(covariate_effects = out),
    output_dir = output_dir,
    file_stems = list(covariate_effects = "covariate_effects_summary"),
    formats = table_formats,
    keep_na = keep_na,
    sort_keys = list(covariate_effects = c("covariate", "quantile")),
    numeric_digits = numeric_digits
  )

  if (isTRUE(write_tex)) {
    lines <- c(
      "% covariate & quantile & center & [q2.5, q97.5] \\\\",
      if (nrow(out) == 0L) "% <empty>" else sprintf(
        "%s & %d & %.6f & [%.6f, %.6f] \\\\",
        out$covariate, out$quantile, out$center, out$q2_5, out$q97_5
      )
    )
    post_write_lines(lines, file.path(output_dir, "covariate_effects_summary.tex"))
  }

  list(table = out, manifest = manifest)
}

post_write_table_exports_manifest <- function(manifest_df, output_dir) {
  if (is.null(manifest_df) || nrow(manifest_df) == 0L) return(invisible(NULL))
  out_path <- file.path(output_dir, "posterior_table_exports_manifest.csv")
  post_write_csv_deterministic(manifest_df, out_path, numeric_digits = 15L)
  invisible(out_path)
}

post_write_table_exports_readme <- function(output_dir, ci_digits = 3L, table_formats = c("csv")) {
  lines <- c(
    "# Posterior Table Exports",
    "",
    "This folder contains machine-readable posterior summary tables generated during post-processing.",
    "",
    "Files:",
    "- gamma_summary.csv: gamma by source x quantile with center=posterior median and 95% CI",
    "- sigma_summary.csv: sigma by source x quantile with center=posterior median and 95% CI",
    "- covariate_effects_summary.csv: transfer-function covariate effects with center=posterior mean and 95% CI at final time index",
    "",
    "Optional LaTeX snippets:",
    "- gamma_summary.tex",
    "- sigma_summary.tex",
    "- covariate_effects_summary.tex",
    "",
    sprintf("CI string precision: %d decimal places.", as.integer(ci_digits)),
    sprintf("Table formats: %s", paste(unique(table_formats), collapse = ", ")),
    "The numeric columns are the source of truth for downstream table generation."
  )
  post_write_lines(lines, file.path(output_dir, "posterior_table_exports_README.md"))
}

log_g <- function(gam) {
  log(2) + stats::pnorm(-abs(gam), log = TRUE) + 0.5 * gam^2
}

L_fn <- function(p0) {
  stats::uniroot(function(gam) exp(log_g(gam)) - (1 - p0), c(-1000, 0))$root
}

U_fn <- function(p0) {
  stats::uniroot(function(gam) exp(log_g(gam)) - p0, c(0, 1000))$root
}

p_fn <- function(p0, gam) {
  (p0 - as.numeric(gam < 0)) / exp(log_g(gam)) + as.numeric(gam < 0)
}

A_fn <- function(p0, gam) {
  temp_p <- p_fn(p0, gam)
  (1 - 2 * temp_p) / (temp_p * (1 - temp_p))
}

B_fn <- function(p0, gam) {
  temp_p <- p_fn(p0, gam)
  2 / (temp_p * (1 - temp_p))
}

C_fn <- function(p0, gam) {
  temp_p <- p_fn(p0, gam)
  (as.numeric(gam > 0) - temp_p)^(-1)
}

check_loss_fn <- function(p0, diff) {
  diff * p0 - diff * as.numeric(diff < 0)
}
dlm_df = function(y, model, df, dim.df, s.priors = list(l0=1,S0=10), just.lik=FALSE){
  ### Gets the     Time Series Length / Replicate number
  y = check_ts(y)
  TT = nrow(y)
  ### Gets the State Parameter dimension and Prior Distribution Parameters
  m0 = model$m0
  C0 = model$C0
  l0 = s.priors$l0
  S0 = s.priors$S0
  n = length(m0)
  ### Constructs F and G
  FF = model$FF
  GG = model$GG
  ### Variable Saving
  ### Posterior Distribution
  m = matrix(0,TT,n)
  C = array(0,c(TT,n,n))
  ### Predictive State Distribution
  a = matrix(0,TT,n)
  R = array(0,dim = c(TT,n,n))
  P = array(0,dim = c(TT,n,n))
  W = array(0,dim = c(TT,n,n))
  ### One-Step Ahead Forecast
  f = matrix(0,TT,1)
  Q = array(0,c(TT,1,1))
  inv.Q = array(0,c(TT,1,1))
  ### Regression Variables
  e = matrix(0,TT,1)
  A = array(0,c(TT,n,1))
  ### Sample Variance
  S = vector("numeric",TT)
  l = vector("numeric",TT)

  # Prior Dim Check
  m0 = matrix(m0,n,1)
  C0 = matrix(C0,n,n)
  ### Discount Factor Blocking
  df.mat = make_df_mat(df,dim.df,n)

  ### First Update
  ### One-step state forecast
  a[1,]  = GG[,,1] %*% m0
  P[1,,] = GG[,,1] %*% C0 %*% t(GG[,,1])
  W[1,,] = df.mat * P[1,,]
  R[1,,] = P[1,,] + W[1,,]
  ### One-step ahead forecast
  f[1,] = t(FF[,1]) %*% a[1,]
  Q[1,,] = as.matrix(1 + t(FF[,1]) %*% R[1,,] %*% FF[,1],1,1)
  inv.Q[1,,] = chol2inv(chol(Q[1,,]))
  ### Auxilary Variables
  e[1,]  = as.matrix(y[1,] - f[1,],1,1)
  A[1,,] = R[1,,] %*% FF[,1] %*% inv.Q[1,,]
  ### Variance update
  l[1] = l0 + 1
  S[1] = l0 * S0 / l[1] + (t(e[1,]) %*% inv.Q[1,,] %*% e[1,] / l[1])
  ### Posterior Distribution
  m[1,]  = a[1,] + as.matrix(A[1,,],n,1) %*% e[1,]
  C[1,,] = R[1,,] - as.matrix(A[1,,],n,1) %*% Q[1,,] %*% t(A[1,,])
  C[1,,] = (C[1,,] + t(C[1,,]))/2

  for(i in 2:TT){
    ### One-step state forecast
    a[i,]  = GG[,,i] %*% m[i-1,]
    P[i,,] = GG[,,i] %*% C[i-1,,] %*% t(GG[,,i])
    W[i,,] = df.mat * P[i,,]
    R[i,,] = P[i,,] + W[i,,]
    ### One-step ahead forecast
    f[i,] = t(FF[,i]) %*% a[i,]
    Q[i,,] = matrix(1 + t(FF[,i])%*% R[i,,]%*% FF[,i],1,1)
    inv.Q[i,,] = chol2inv(chol(Q[i,,]))
    ### Auxilary Variables
    e[i,]  = as.matrix(y[i,] - f[i,],1,1)
    A[i,,] = as.matrix(R[i,,] %*% FF[,i] %*% inv.Q[i,,],n,1)
    ### Variance update
    l[i] = l[i-1] + 1
    S[i] = l[i-1] * S[i-1] / l[i] + (t(e[i,]) %*% inv.Q[i,,] %*% e[i,] / l[i])
    ### Posterior Distribution
    m[i,]  = a[i,] + as.matrix(A[i,,],n,1) %*% e[i,]
    C[i,,] = R[i,,] - as.matrix(A[i,,],n,1) %*% Q[i,,] %*% t(as.matrix(A[i,,],n,1))
    C[i,,] = (C[i,,] + t(C[i,,]))/2
  }

  ### Adjust By Variance
  R[1,,] = S0 * R[1,,]
  Q[1,,]   = S0 * Q[1,,]
  C[1,,]   = S[1] * C[1,,]
  for(i in 2:TT){
    R[i,,] = S[i-1] * R[i,,]
    Q[i,,]   = S[i-1] * Q[i,,]
    C[i,,]   = S[i] * C[i,,]
  }

  # Calculate Log-Likelihood
  det.Q = log(abs(Q[1,,])) ; llik = lgamma((l0+1)/2)-lgamma(l0/2)-log(pi*l0)/2-det.Q/2-(l0+1)*log(1+t(e[1,])%*%inv.Q[1,,]%*%e[1,]/l0)/2
  for(t in 2:TT){
    det.Q = log(abs(Q[t,,]))
    llik = llik + lgamma((l[t-1]+1)/2)-lgamma(l[t-1]/2)-log(pi*l[t-1])/2-det.Q/2-(l[t-1]+1)*log(1+t(e[t,])%*%inv.Q[t,,]%*%e[t,]/l[t-1])/2
  }
  if(just.lik){
    return(list(llik = llik))
  }

  ## SMOOTHING
  ### Initializes recursive relations
  sa = matrix(0,TT,n)
  sR = array(0, dim = c(TT,n,n))
  ### Runs the recursive equations
  sa[TT,]  = m[TT,]
  sR[TT,,] = C[TT,,]
  for(k in 1:(TT-1)){
  ### Computes the Auxilary recursion Variable B
    B = C[TT-k,,] %*% t(GG[,,TT-k+1]) %*% solve(R[TT-k+1,,])
    sa[TT-k,] = m[TT-k,] + B %*% (sa[TT-k+1,] - a[TT-k+1,])
    sR[TT-k,,] = C[TT-k,,] + B %*% (sR[TT-k+1,,] - R[TT-k+1,,]) %*% t(B)
  }
  ### Adjusts the variance update
  for(k in 1:TT){
    sR[TT-k,,] = S[TT] * sR[TT-k,,] / S[TT-k]
  }
  return(list(fm = m, fC = C, m = sa, C = sR,model = model, s = S, n = l))
}
#
make_df_mat = function(df,dim.df,n){
  if(sum(dim.df)!=n){ stop("sum of component dimensions given in dim.df does not match m0") }
  if(length(df)!=length(dim.df)){ stop("length of component discount factors does not match length of component dimensions") }
  dfs = rep(df,dim.df)
  n.dfs = length(dim.df)
  ind.dfs = c(0,sapply(1:length(dim.df),function(x){sum(dim.df[1:x])}),n)
  df.mat = matrix(0,n,n)
  for(j in 1:n.dfs){
    df.mat[(ind.dfs[j]+1):ind.dfs[(j+1)],(ind.dfs[j]+1):ind.dfs[(j+1)]] = (1-dfs[ind.dfs[(j+1)]])/dfs[ind.dfs[(j+1)]]
  }
  return(df.mat)
}
#
check_mod = function(model){
  if(dlm::is.dlm(model)){
    model = dlmMod(model)
  }
  if(!is.vector(model$m0)){
    if(ncol(model$m0) != 1){
      stop("m0 must be a vector or a matrix with 1 column")
      }
    }
  p = length(model$m0)
  model$C0 = as.matrix(model$C0)
  if(p != dim(model$C0)[1] & p != dim(model$C0)[2]){
    stop("C0 must be a square matrix matching the dimension of m0")
    }
  if(!all.equal(model$C0, t(model$C0)) | !all(eigen(model$C0)$values >= 0)){
    stop("C0 must be a covariance matrix")
  }
  if(!is.vector(model$FF)){
    if(nrow(model$FF) != p){
      stop("FF must be a vector of length matching the dimension of m0, or a matrix with number of rows matching the dimension of m0")
    }
  }else{
    if(length(model$FF) != p){
      stop("FF must be a vector of length matching the dimension of m0, or a matrix with number of rows matching the dimension of m0")
    }
  }
  if(is.null(dim(model$GG)[3])){
    model$GG = as.matrix(model$GG)
  }else{
    if(is.na(dim(model$GG)[3])){
      model$GG = as.matrix(model$GG)
    }else{
      model$GG = as.array(model$GG)
    }
  }
  if(p != dim(model$GG)[1] & p != dim(model$GG)[2]){
    stop("GG must be a square matrix matching the dimension of m0, or an array with first two dimensions matching the dimension of m0")
  }
  model$m0 = as.matrix(model$m0)
  model$FF = as.matrix(model$FF)
  return(model)
}
#
check_logics = function(gam.init,sig.init,fix.gamma,fix.sigma,dqlm.ind){
  retval <- NULL
  retval$gam.init = gam.init
  retval$fix.gamma = fix.gamma
  retval$dqlm.ind = dqlm.ind
  if(dqlm.ind){
    if(gam.init!=0 | !fix.gamma){
      retval$gam.init <- gam.init <- 0
      retval$fix.gamma <- fix.gamma <- TRUE
    }
  }else{
    if(gam.init==0 && fix.gamma==TRUE){
      retval$dqlm.ind = TRUE
    }
  }
  if(fix.gamma & is.na(gam.init)){ stop("when fix.gamma = TRUE, gam.init must be specified") }
  if(fix.sigma & is.na(sig.init)){ stop("when fix.sigma = TRUE, sig.init must be specified") }
  return(retval)
}
#
check_ts = function(dat){
  dat = as.matrix(dat)
  if(all(dim(dat)>1)){
    stop("data must be univariate time-series")
  }
  if(dim(dat)[1]<dim(dat)[2]){
    dat = t(dat)
  }
  return(invisible(dat))
}
#
is.exdqlm = function(m){ return(inherits(m,"exdqlm")) }

parameters_path <- "/data/muscat_data/jaguir26/projects/Project/Input/exAL/parameters/parameters.txt"

# Check if the file exists
if (!file.exists(parameters_path)) {
  stop("The parameters file does not exist at the specified path: ", parameters_path)
}

lines <- readLines(parameters_path)

# Check if the lines variable is empty or not as expected
if (length(lines) == 0) {
  stop("No content found in the parameters file: ", parameters_path)
}

# Process each line and assign variables
for (line in lines) {
  # Remove leading and trailing whitespaces
  line <- trimws(line)
  
  # Skip empty lines and comments
  if (nchar(line) == 0 || grepl("^#", line)) next
  
  # Evaluate and assign
  eval(parse(text = line))
}
#
dlm_df = function(y, model, df, dim.df, s.priors = list(l0=1,S0=10), just.lik=FALSE){
  
  ### Gets the Time Series Length / Replicate number
  TT = length(y)
  ### Gets the State Parameter dimension and Prior Distribution Parameters
  m0 = model$m0
  C0 = model$C0
  l0 = s.priors$l0
  S0 = s.priors$S0
  n = length(m0)
  ### Constructs F and G
  FF = model$FF
  GG = model$GG
  ### Variable Saving
  ### Posterior Distribution
  m = matrix(0,TT,n)
  C = array(0,c(TT,n,n))
  ### Predictive State Distribution
  a = matrix(0,TT,n)
  R = array(0,dim = c(TT,n,n))
  P = array(0,dim = c(TT,n,n))
  W = array(0,dim = c(TT,n,n))
  ### One-Step Ahead Forecast
  f = matrix(0,TT,1)
  Q = array(0,c(TT,1,1))
  inv.Q = array(0,c(TT,1,1))
  ### Regression Variables
  e = matrix(0,TT,1)
  A = array(0,c(TT,n,1))
  ### Sample Variance
  S = vector("numeric",TT)
  l = vector("numeric",TT)
  
  # Prior Dim Check
  m0 = matrix(m0,n,1)
  C0 = matrix(C0,n,n)
  ### Discount Factor Blocking
  df.mat = make_df_mat(df,dim.df,n)
  
  ### First Update
  ### One-step state forecast
  a[1,]  = GG[,,1] %*% m0
  P[1,,] = GG[,,1] %*% C0 %*% t(GG[,,1])
  W[1,,] = df.mat * P[1,,]
  R[1,,] = P[1,,] + W[1,,]
  ### One-step ahead forecast
  f[1,] = t(FF[,,1]) %*% a[1,]
  Q[1,,] = as.matrix(1 + t(FF[,,1]) %*% R[1,,] %*% FF[,,1],1,1)
  inv.Q[1,,] = chol2inv(chol(Q[1,,]))
  ### Auxilary Variables
  e[1,]  = as.matrix(y[1] - f[1,],1,1)
  A[1,,] = R[1,,] %*% FF[,,1] %*% inv.Q[1,,]
  ### Variance update
  l[1] = l0 + 1
  S[1] = l0 * S0 / l[1] + (t(e[1,]) %*% inv.Q[1,,] %*% e[1,] / l[1])
  ### Posterior Distribution
  m[1,]  = a[1,] + as.matrix(A[1,,],n,1) %*% e[1,]
  C[1,,] = R[1,,] - as.matrix(A[1,,],n,1) %*% Q[1,,] %*% t(A[1,,])
  C[1,,] = (C[1,,] + t(C[1,,]))/2
  
  for(i in 2:TT){
    ### One-step state forecast
    a[i,]  = GG[,,i] %*% m[i-1,]
    P[i,,] = GG[,,i] %*% C[i-1,,] %*% t(GG[,,i])
    W[i,,] = df.mat * P[i,,]
    R[i,,] = P[i,,] + W[i,,]
    ### One-step ahead forecast
    f[i,] = t(FF[,,i]) %*% a[i,]
    Q[i,,] = matrix(1 + t(FF[,,i])%*% R[i,,]%*% FF[,,i],1,1)
    inv.Q[i,,] = chol2inv(chol(Q[i,,]))
    ### Auxilary Variables
    e[i,]  = as.matrix(y[i] - f[i,],1,1)
    A[i,,] = as.matrix(R[i,,] %*% FF[,,i] %*% inv.Q[i,,],n,1)
    ### Variance update
    l[i] = l[i-1] + 1
    S[i] = l[i-1] * S[i-1] / l[i] + (t(e[i,]) %*% inv.Q[i,,] %*% e[i,] / l[i])
    ### Posterior Distribution
    m[i,]  = a[i,] + as.matrix(A[i,,],n,1) %*% e[i,]
    C[i,,] = R[i,,] - as.matrix(A[i,,],n,1) %*% Q[i,,] %*% t(as.matrix(A[i,,],n,1))
    C[i,,] = (C[i,,] + t(C[i,,]))/2
  }
  
  ### Adjust By Variance
  R[1,,] = S0 * R[1,,]
  Q[1,,]   = S0 * Q[1,,]
  C[1,,]   = S[1] * C[1,,]
  for(i in 2:TT){
    R[i,,] = S[i-1] * R[i,,]
    Q[i,,]   = S[i-1] * Q[i,,]
    C[i,,]   = S[i] * C[i,,]
  }
  
  # Calculate Log-Likelihood
  det.Q = log(abs(Q[1,,])) ; llik = lgamma((l0+1)/2)-lgamma(l0/2)-log(pi*l0)/2-det.Q/2-(l0+1)*log(1+t(e[1,])%*%inv.Q[1,,]%*%e[1,]/l0)/2
  for(t in 2:TT){
    det.Q = log(abs(Q[t,,]))
    llik = llik + lgamma((l[t-1]+1)/2)-lgamma(l[t-1]/2)-log(pi*l[t-1])/2-det.Q/2-(l[t-1]+1)*log(1+t(e[t,])%*%inv.Q[t,,]%*%e[t,]/l[t-1])/2
  }
  if(just.lik){
    return(list(llik = llik))
  }
  
  ## SMOOTHING
  ### Initializes recursive relations
  sa = matrix(0,TT,n)
  sR = array(0, dim = c(TT,n,n))
  ### Runs the recursive equations
  sa[TT,]  = m[TT,]
  sR[TT,,] = C[TT,,]
  for(k in 1:(TT-1)){
    ### Computes the Auxilary recursion Variable B
    B = C[TT-k,,] %*% t(GG[,,TT-k+1]) %*% solve(R[TT-k+1,,])
    sa[TT-k,] = m[TT-k,] + B %*% (sa[TT-k+1,] - a[TT-k+1,])
    sR[TT-k,,] = C[TT-k,,] + B %*% (sR[TT-k+1,,] - R[TT-k+1,,]) %*% t(B)
  }
  ### Adjusts the variance update
  for(k in 1:TT){
    sR[TT-k,,] = S[TT] * sR[TT-k,,] / S[TT-k]
  }
  return(list(fm = m, fC = C, m = sa, C = sR,model = model, s = S, n = l))
}
#
make_df_mat = function(df,dim.df,n){
  if(sum(dim.df)!=n){ stop("sum of component dimensions given in dim.df does not match m0") }
  if(length(df)!=length(dim.df)){ stop("length of component discount factors does not match length of component dimensions") }
  dfs = rep(df,dim.df)
  n.dfs = length(dim.df)
  ind.dfs = c(0,sapply(1:length(dim.df),function(x){sum(dim.df[1:x])}),n)
  df.mat = matrix(0,n,n)
  for(j in 1:n.dfs){
    df.mat[(ind.dfs[j]+1):ind.dfs[(j+1)],(ind.dfs[j]+1):ind.dfs[(j+1)]] = (1-dfs[ind.dfs[(j+1)]])/dfs[ind.dfs[(j+1)]]
  }
  return(df.mat)
}
#
make_df_mat_k = function(df,dim.df,n,k){
  if(sum(dim.df)!=n){ stop("sum of component dimensions given in dim.df does not match m0") }
  if(length(df)!=length(dim.df)){ stop("length of component discount factors does not match length of component dimensions") }
  dfs = rep(df,dim.df)
  n.dfs = length(dim.df)
  ind.dfs = c(0,sapply(1:length(dim.df),function(x){sum(dim.df[1:x])}),n)
  df.mat = matrix(0,n,n)
  for(j in 1:n.dfs){
    df.mat[(ind.dfs[j]+1):ind.dfs[(j+1)],(ind.dfs[j]+1):ind.dfs[(j+1)]] = (1-dfs[ind.dfs[(j+1)]]^k)/dfs[ind.dfs[(j+1)]]^k
  }
  return(df.mat)
}
#
H_t_k_r <- function(GG, t, k, r){
  n <- dim(GG)[1]
  I <- diag(n)
  for (s in (t+k-r):(t+k)) {
    I <- GG[,,s] %*% I   
  }
  return(I)
}
#
# Function to estimate log density using KDE for univariate data
estimate_log_density_kde_univariate <- function(data, points) {
  kde_result <- kde(data)
  density_estimates <- predict(kde_result, x = points)
  log_density <- log(density_estimates + .Machine$double.eps*100)  # Add small value to avoid log(0)
  return(log_density)
}
#
# Function to estimate the expectation term for univariate data
estimate_expectation_term_univariate <- function(sample_from_p, sample_size) {
  # Generate a sample from the standard normal distribution
  sample_from_normal <- rnorm(sample_size)
  
  # Estimate log density of p at points sampled from the standard normal distribution
  log_density_estimates <- estimate_log_density_kde_univariate(sample_from_p, sample_from_normal)
  
  # Compute the Monte Carlo estimate of the expectation
  expectation_estimate <- mean(log_density_estimates)
  
  return(expectation_estimate)
}
#
# Function to estimate the KL divergence D_KL(N(0, 1) || p) for univariate data
estimate_kl_divergence_univariate_normal_to_p <- function(sample_from_p, sample_size) {
  # Estimate the expectation term
  expectation_term <- estimate_expectation_term_univariate(sample_from_p, sample_size)
  
  # Compute the KL divergence
  kl_divergence <- -0.5 * log(2 * pi) - 0.5 - expectation_term
  
  return(kl_divergence)
}
#
# Function to estimate KL divergence using k-NN with entropy package for multivariate data
estimate_kl_divergence_knn_entropy <- function(sample_from_p, sample_size, k = 5) {
  # Generate a sample from the multivariate standard normal distribution
  sample_from_normal <- matrix(rnorm(sample_size * ncol(sample_from_p)), ncol = ncol(sample_from_p))
  
  # Estimate KL divergence using entropy package's KL.div function
  kl_divergence <- KL.divergence(sample_from_p, sample_from_normal, k = k)
  
  # Return only the final estimate
  return(tail(kl_divergence, n = 1))
}
#
# Unified function to estimate KL divergence based on the input sample
estimate_kl_divergence <- function(sample, sample_size = 10000) {
  # Check if the sample is univariate or multivariate
  if (is.vector(sample) || ncol(sample) == 1) {
    # Univariate case
    if (is.vector(sample)) {
      sample_from_p <- sample
    } else {
      sample_from_p <- sample[, 1]
    }
    
    # Estimate the KL divergence using the KDE-based method
    estimated_kl_divergence <- estimate_kl_divergence_univariate_normal_to_p(sample_from_p, sample_size)
    
  } else {
    # Multivariate case
    sample_from_p <- sample
    
    # Estimate the KL divergence using the k-NN based method with entropy package
    estimated_kl_divergence <- estimate_kl_divergence_knn_entropy(sample_from_p, sample_size, k = 5)
  }
  
  # Return the estimate
  return(estimated_kl_divergence)
}
#
# Function to estimate differential entropy using KDE for univariate data
estimate_differential_entropy_kde_univariate <- function(data) {
  kde_result <- kde(data)
  estimates <- kde_result$estimate
  estimates[estimates <= 0] <- .Machine$double.eps*100 # Prevent log(0) issues
  log_estimates <- log(estimates)
  log_estimates[!is.finite(log_estimates)] <- 0 # Handle non-finite values
  entropy_estimate <- -sum(estimates * log_estimates) * diff(kde_result$eval.points)[1]
  return(entropy_estimate)
}
#
# Function to estimate differential entropy using KDE for multivariate data
estimate_differential_entropy_kde_multivariate <- function(data) {
  kde_result <- kde(data)
  estimates <- kde_result$estimate
  estimates[estimates <= 0] <- .Machine$double.eps*100 # Prevent log(0) issues
  log_estimates <- log(estimates)
  log_estimates[!is.finite(log_estimates)] <- 0 # Handle non-finite values
  entropy_estimate <- -sum(estimates * log_estimates) * prod(diff(kde_result$eval.points[[1]]))
  return(entropy_estimate)
}
#
# Function to estimate the KL divergence D_KL(p || N(0, I)) for univariate data
estimate_kl_divergence_univariate <- function(data) {
  # Estimate the differential entropy H(p)
  H_p <- estimate_differential_entropy_kde_univariate(data)
  
  # Compute the expected value of the squared norm of the vectors
  E_p_x2 <- mean(data^2)
  
  # Dimensionality is 1 for univariate data
  k <- 1
  
  # Compute the KL divergence
  kl_divergence <- -H_p + (k / 2) * log(2 * pi) + (1 / 2) * E_p_x2
  
  return(kl_divergence)
}
#
# Function to estimate the KL divergence D_KL(p || N(0, I)) for multivariate data
estimate_kl_divergence_multivariate <- function(data) {
  # Estimate the differential entropy H(p)
  H_p <- estimate_differential_entropy_kde_multivariate(data)
  
  # Dimensionality of the vectors
  k <- ncol(data)
  
  # Compute the expected value of the squared norm of the vectors
  E_p_xTx <- mean(rowSums(data^2))
  
  # Compute the KL divergence
  kl_divergence <- -H_p + (k / 2) * log(2 * pi) + (1 / 2) * E_p_xTx
  
  return(kl_divergence)
}
#
# Wrapper function for any sample
compute_kl_divergence <- function(sample) {
  # Ensure the input sample is a matrix
  sample <- as.matrix(sample)
  
  # Determine if the sample is univariate or multivariate
  if (ncol(sample) == 1) {
    kl_divergence <- estimate_kl_divergence_univariate(sample)
  } else {
    kl_divergence <- estimate_kl_divergence_multivariate(sample)
  }
  
  return(kl_divergence)
}
#
concatenate_matrix_columns <- function(matrix_input) {
  # Concatenate the columns of the matrix
  concatenated_vector <- c(matrix_input)
  return(concatenated_vector)
}
#
preallocate_matrix_list <- function(column_counts, num_rows) {
  # Initialize an empty list
  matrix_list <- vector("list", length(column_counts))
  
  # Loop through the column counts and create matrices
  for (i in seq_along(column_counts)) {
    num_cols <- column_counts[i]
    matrix_list[[i]] <- matrix(NA, nrow = num_rows, ncol = num_cols)
  }
  
  return(matrix_list)
}

# Prepare a numeric sample matrix for JSD/KDE diagnostics with strict shape checks.
prepare_jsd_sample_matrix <- function(sample, context = "jsd_sample", min_rows = 5L) {
  if (is.null(sample)) {
    stop(sprintf("[JSD_INPUT_NULL] %s is NULL; expected numeric vector/matrix.", context))
  }
  if (is.vector(sample)) {
    sample <- matrix(as.numeric(sample), ncol = 1L)
  } else {
    sample <- as.matrix(sample)
  }
  if (!is.numeric(sample)) {
    stop(sprintf("[JSD_INPUT_TYPE] %s is non-numeric; expected numeric sample matrix.", context))
  }
  if (is.null(dim(sample)) || length(dim(sample)) != 2L || ncol(sample) < 1L) {
    stop(sprintf("[JSD_INPUT_SHAPE] %s has invalid shape; expected an n x d matrix with d >= 1.", context))
  }

  keep <- apply(sample, 1L, function(row) all(is.finite(row)))
  n_drop <- sum(!keep)
  if (n_drop > 0L) {
    warning(
      sprintf("[JSD_INPUT_NONFINITE] %s dropped %d non-finite sample rows before KDE.", context, as.integer(n_drop)),
      call. = FALSE
    )
  }
  sample <- sample[keep, , drop = FALSE]

  if (nrow(sample) < as.integer(min_rows)) {
    stop(
      sprintf(
        "[JSD_INPUT_ROWS] %s has %d finite rows after filtering; need at least %d for stable KDE.",
        context,
        as.integer(nrow(sample)),
        as.integer(min_rows)
      )
    )
  }
  sample
}

normalize_jsd_gridsize <- function(gridsize, d) {
  d <- as.integer(d)
  gs <- as.integer(gridsize)
  if (length(gs) == 0L || any(!is.finite(gs))) {
    stop("[JSD_GRID_INVALID] JSD gridsize must contain at least one finite integer.")
  }
  if (length(gs) == 1L) {
    gs <- rep(gs, d)
  } else if (length(gs) < d) {
    gs <- c(gs, rep(tail(gs, 1L), d - length(gs)))
  } else if (length(gs) > d) {
    gs <- gs[seq_len(d)]
  }
  if (any(gs < 2L)) {
    stop("[JSD_GRID_RANGE] JSD gridsize entries must be >= 2.")
  }
  gs
}

extract_kde_eval_points <- function(kde_obj, d, context = "jsd_kde") {
  gp <- kde_obj$eval.points
  d <- as.integer(d)

  if (d == 1L) {
    if (is.numeric(gp)) {
      return(list(as.numeric(gp)))
    }
    if (is.list(gp) && length(gp) == 1L && is.numeric(gp[[1L]])) {
      return(list(as.numeric(gp[[1L]])))
    }
    if (is.list(gp) && length(gp) > 1L &&
        all(vapply(gp, function(v) is.numeric(v) && length(v) == 1L, logical(1)))) {
      return(list(as.numeric(unlist(gp, use.names = FALSE))))
    }
    stop(sprintf("[JSD_KDE_AXIS_1D] %s has unsupported 1D eval.points structure.", context))
  }

  if (!is.list(gp) || length(gp) != d) {
    stop(sprintf("[JSD_KDE_AXES] %s expected %d KDE eval-point axes; found %d.", context, d, length(gp)))
  }
  out <- lapply(gp, as.numeric)
  axis_lengths <- vapply(out, length, integer(1))
  if (any(axis_lengths < 2L)) {
    stop(sprintf("[JSD_KDE_AXIS_RANGE] %s contains degenerate KDE axis lengths: %s.", context, paste(axis_lengths, collapse = ",")))
  }
  out
}

# Jensen-Shannon divergence between sample KDE and standard Normal in matching dimension.
compute_jsd_to_standard_normal <- function(sample, gridsize = 100L, context = "jsd") {
  if (!requireNamespace("ks", quietly = TRUE)) {
    stop("[JSD_DEP_KS] compute_jsd_to_standard_normal requires package 'ks'.")
  }
  if (!requireNamespace("mvtnorm", quietly = TRUE)) {
    stop("[JSD_DEP_MVTNORM] compute_jsd_to_standard_normal requires package 'mvtnorm'.")
  }

  sample_m <- prepare_jsd_sample_matrix(sample, context = context)
  d <- ncol(sample_m)
  if (d > 3L) {
    stop(sprintf("[JSD_DIMENSION] %s has dimension %d; JSD KDE grid diagnostics support d <= 3.", context, as.integer(d)))
  }

  gs <- normalize_jsd_gridsize(gridsize, d)
  kde_obj <- ks::kde(sample_m, gridsize = gs)

  pdf_p <- kde_obj$estimate
  dim_p <- dim(pdf_p)
  if (is.null(dim_p)) {
    dim_p <- length(pdf_p)
  }
  dim_p <- as.integer(dim_p)
  if (length(dim_p) != d) {
    stop(
      sprintf(
        "[JSD_KDE_DIM_MISMATCH] %s KDE estimate dimension mismatch: sample d=%d but estimate dim length=%d.",
        context,
        as.integer(d),
        as.integer(length(dim_p))
      )
    )
  }
  if (any(dim_p < 2L)) {
    stop(sprintf("[JSD_KDE_DIM_RANGE] %s KDE estimate has degenerate dimensions: %s.", context, paste(dim_p, collapse = "x")))
  }

  grid_points <- extract_kde_eval_points(kde_obj, d, context = context)
  grid_df <- do.call(expand.grid, c(grid_points, KEEP.OUT.ATTRS = FALSE, stringsAsFactors = FALSE))
  grid_matrix <- as.matrix(grid_df)
  if (!is.numeric(grid_matrix) || ncol(grid_matrix) != d) {
    stop(sprintf("[JSD_GRID_SHAPE] %s generated invalid KDE grid matrix shape.", context))
  }

  mean_q <- rep(0, d)
  cov_q <- diag(d)
  pdf_q_vec <- mvtnorm::dmvnorm(grid_matrix, mean = mean_q, sigma = cov_q)
  if (length(pdf_q_vec) != prod(dim_p)) {
    stop(
      sprintf(
        "[JSD_DENSITY_GRID_MISMATCH] %s density-grid mismatch: q length=%d vs p grid size=%d.",
        context,
        as.integer(length(pdf_q_vec)),
        as.integer(prod(dim_p))
      )
    )
  }
  pdf_q <- array(pdf_q_vec, dim = dim_p)

  sum_p <- sum(pdf_p)
  sum_q <- sum(pdf_q)
  if (!is.finite(sum_p) || sum_p <= 0 || !is.finite(sum_q) || sum_q <= 0) {
    stop(sprintf("[JSD_DENSITY_NORMALIZATION] %s invalid KDE or reference density normalization constants.", context))
  }
  pdf_p <- pdf_p / sum_p
  pdf_q <- pdf_q / sum_q

  epsilon <- 1e-10
  kl_divergence <- function(p, q) {
    p <- p + epsilon
    q <- q + epsilon
    sum(p * log(p / q))
  }
  m <- 0.5 * (pdf_p + pdf_q)
  as.numeric(0.5 * kl_divergence(pdf_p, m) + 0.5 * kl_divergence(pdf_q, m))
}

resolve_time_cuts <- function(
  timestamps,
  cutoff_date = if (exists("CUTOFF_DATE", inherits = TRUE)) get("CUTOFF_DATE", inherits = TRUE) else NA,
  anchor_dates = c("2012-08-01", "2016-05-01", "2016-09-15", "2019-08-01"),
  anchor_tolerance_days = 3L,
  context = "time_cuts"
) {
  dates <- as.Date(timestamps)
  n <- length(dates)
  if (n < 8L) {
    stop(sprintf("[%s] need at least 8 timestamps to build stable plotting windows.", context), call. = FALSE)
  }

  sanitize_cuts <- function(idx) {
    idx <- as.integer(round(idx))
    if (length(idx) != 4L || any(!is.finite(idx))) return(NULL)
    idx <- pmin(pmax(idx, 1L), n)
    for (i in 2:4) {
      if (idx[[i]] <= idx[[i - 1L]]) idx[[i]] <- idx[[i - 1L]] + 1L
    }
    if (idx[[4L]] > n) {
      shift <- idx[[4L]] - n
      idx <- idx - shift
      if (idx[[1L]] < 1L) idx <- idx + (1L - idx[[1L]])
      for (i in 2:4) {
        if (idx[[i]] <= idx[[i - 1L]]) idx[[i]] <- idx[[i - 1L]] + 1L
      }
    }
    if (idx[[1L]] < 1L || idx[[4L]] > n || any(diff(idx) <= 0L)) return(NULL)
    idx
  }

  anchors <- as.Date(anchor_dates)
  anchor_idx_exact <- match(anchors, dates)
  if (all(!is.na(anchor_idx_exact))) {
    anchor_cuts <- sanitize_cuts(anchor_idx_exact)
    if (!is.null(anchor_cuts)) return(anchor_cuts)
  }

  nearest_index <- function(target) {
    target <- as.Date(target)
    if (is.na(target)) return(NA_integer_)
    as.integer(which.min(abs(as.numeric(dates - target))))
  }

  tol_days <- suppressWarnings(as.numeric(anchor_tolerance_days))
  if (!is.finite(tol_days) || tol_days < 0) tol_days <- 0
  anchor_idx_near <- vapply(anchors, nearest_index, integer(1))
  if (!anyNA(anchor_idx_near)) {
    anchor_dist <- abs(as.numeric(dates[anchor_idx_near] - anchors))
    if (all(is.finite(anchor_dist)) && all(anchor_dist <= tol_days)) {
      anchor_cuts <- sanitize_cuts(anchor_idx_near)
      if (!is.null(anchor_cuts)) return(anchor_cuts)
    }
  }

  cutoff_date <- suppressWarnings(as.Date(cutoff_date))
  hist_end <- if (!is.na(cutoff_date)) {
    idx <- which(dates <= cutoff_date)
    if (length(idx) > 0L) max(idx) else n
  } else {
    n
  }
  hist_end <- min(max(8L, hist_end), n)

  w2_end <- max(4L, hist_end)
  w2_start <- max(3L, w2_end - 365L * 3L)
  w1_end <- max(2L, w2_start - 1L)
  w1_start <- max(1L, w1_end - 365L * 4L)
  fallback_cuts <- sanitize_cuts(c(w1_start, w1_end, w2_start, w2_end))
  if (!is.null(fallback_cuts)) return(fallback_cuts)

  idx_grid <- unique(as.integer(round(c(0.10, 0.45, 0.55, 0.90) * (hist_end - 1L) + 1L)))
  if (length(idx_grid) < 4L) {
    idx_grid <- as.integer(round(seq(1L, hist_end, length.out = 4L)))
  } else if (length(idx_grid) > 4L) {
    idx_grid <- idx_grid[c(1L, 2L, length(idx_grid) - 1L, length(idx_grid))]
  }
  final_cuts <- sanitize_cuts(idx_grid)
  if (is.null(final_cuts)) {
    stop(sprintf("[%s] unable to derive valid time_cuts.", context), call. = FALSE)
  }
  final_cuts
}

safe_time_index <- function(start_idx, end_idx, n, context = "time_index", prefer_tail = TRUE) {
  n <- as.integer(n)
  if (!is.finite(n) || n < 1L) {
    stop(sprintf("[%s] n must be a positive integer; got: %s", context, paste(n, collapse = ",")), call. = FALSE)
  }

  s <- suppressWarnings(as.integer(round(start_idx)))
  e <- suppressWarnings(as.integer(round(end_idx)))
  if (!is.finite(s)) s <- 1L
  if (!is.finite(e)) e <- n

  s <- max(1L, min(n, s))
  e <- max(1L, min(n, e))

  if (s > e) {
    if (isTRUE(prefer_tail)) {
      width_raw <- suppressWarnings(as.integer(round(end_idx - start_idx + 1L)))
      if (!is.finite(width_raw) || width_raw < 1L) width_raw <- 1L
      width <- min(n, width_raw)
      e <- n
      s <- max(1L, e - width + 1L)
    } else {
      s <- 1L
      e <- 1L
    }
  }

  seq.int(s, e)
}
