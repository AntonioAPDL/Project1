univar_theory_read_csv <- function(path, label) {
  if (is.null(path) || !nzchar(path)) {
    stop(sprintf("univar theory input %s path is empty", label), call. = FALSE)
  }
  if (!file.exists(path)) {
    stop(sprintf("univar theory input %s missing: %s", label, path), call. = FALSE)
  }
  out <- tryCatch(
    utils::read.csv(path, stringsAsFactors = FALSE, check.names = FALSE),
    error = function(e) e
  )
  if (inherits(out, "error") || !is.data.frame(out)) {
    stop(sprintf("univar theory input %s unreadable CSV: %s", label, path), call. = FALSE)
  }
  if (nrow(out) < 1L || ncol(out) < 1L) {
    stop(sprintf("univar theory input %s is empty: %s", label, path), call. = FALSE)
  }
  out
}

univar_theory_pick_numeric_column <- function(df, preferred = character(0)) {
  if (length(preferred) > 0L) {
    for (nm in preferred) {
      if (nm %in% names(df) && is.numeric(df[[nm]])) {
        return(df[[nm]])
      }
    }
  }
  numeric_cols <- names(df)[vapply(df, is.numeric, logical(1))]
  if (length(numeric_cols) == 0L) {
    return(NULL)
  }
  df[[numeric_cols[[1L]]]]
}

univar_theory_align_series <- function(x, target_len, fill = 0) {
  x <- as.numeric(x)
  x <- x[is.finite(x)]
  if (target_len <= 0L) return(numeric(0))
  if (length(x) == 0L) {
    return(rep(as.numeric(fill), target_len))
  }
  if (length(x) >= target_len) {
    return(tail(x, target_len))
  }
  c(rep(as.numeric(fill), target_len - length(x)), x)
}

univar_theory_load_inputs <- function() {
  retros_path <- Sys.getenv("UNIV_RETROS_CSV", "")
  if (!nzchar(retros_path)) {
    shared_root <- Sys.getenv("UNIV_SHARED_INPUT_ROOT", "")
    if (nzchar(shared_root)) {
      retros_path <- file.path(shared_root, "retros", "retros.csv")
    }
  }
  retros_df <- univar_theory_read_csv(retros_path, "retros")
  y <- univar_theory_pick_numeric_column(
    retros_df,
    preferred = c("USGS", "y", "obs", "flow", "value")
  )
  if (is.null(y)) {
    stop(
      sprintf("univar theory retros has no numeric target column: %s", retros_path),
      call. = FALSE
    )
  }
  y <- as.numeric(y)
  y <- y[is.finite(y)]
  if (length(y) < 30L) {
    stop("univar theory requires at least 30 finite observations in retros", call. = FALSE)
  }
  Tn <- length(y)

  cov_keys <- c(
    "UNIV_COV1_ELI_CSV",
    "UNIV_COV2_ONI_CSV",
    "UNIV_PPT_CSV",
    "UNIV_SOIL_CSV",
    "UNIV_PCA_CSV"
  )
  cov_series <- vector("list", length(cov_keys))
  for (i in seq_along(cov_keys)) {
    pth <- Sys.getenv(cov_keys[[i]], "")
    if (!nzchar(pth) || !file.exists(pth)) {
      cov_series[[i]] <- rep(0, Tn)
      next
    }
    cdf <- univar_theory_read_csv(pth, cov_keys[[i]])
    col <- univar_theory_pick_numeric_column(cdf)
    if (is.null(col)) {
      cov_series[[i]] <- rep(0, Tn)
      next
    }
    cov_series[[i]] <- univar_theory_align_series(col, Tn, fill = 0)
  }
  X <- do.call(cbind, cov_series)
  colnames(X) <- c("ELI", "ONI", "PPT", "SOIL", "PCA")

  list(
    y = y,
    X = X,
    T = Tn,
    input_paths = list(
      retros = retros_path,
      parameters = Sys.getenv("UNIV_PARAMETERS_TXT", ""),
      nws = Sys.getenv("UNIV_NWS_FORECAST_CSV", ""),
      glofas = Sys.getenv("UNIV_GLOFAS_FORECAST_CSV", "")
    )
  )
}
