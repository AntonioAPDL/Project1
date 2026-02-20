ndlm_theory_read_csv <- function(path, label) {
  if (is.null(path) || !nzchar(path)) {
    stop(sprintf("ndlm theory input %s path is empty", label), call. = FALSE)
  }
  if (!file.exists(path)) {
    stop(sprintf("ndlm theory input %s missing: %s", label, path), call. = FALSE)
  }
  out <- tryCatch(
    utils::read.csv(path, stringsAsFactors = FALSE, check.names = FALSE),
    error = function(e) e
  )
  if (inherits(out, "error") || !is.data.frame(out)) {
    stop(sprintf("ndlm theory input %s unreadable CSV: %s", label, path), call. = FALSE)
  }
  if (nrow(out) < 1L || ncol(out) < 1L) {
    stop(sprintf("ndlm theory input %s is empty: %s", label, path), call. = FALSE)
  }
  out
}

ndlm_theory_pick_numeric_column <- function(df, preferred = character(0)) {
  if (length(preferred) > 0L) {
    for (nm in preferred) {
      if (nm %in% names(df) && is.numeric(df[[nm]])) {
        return(df[[nm]])
      }
    }
  }
  num_cols <- names(df)[vapply(df, is.numeric, logical(1))]
  if (length(num_cols) == 0L) return(NULL)
  df[[num_cols[[1L]]]]
}

ndlm_theory_align_series <- function(x, target_len, fill = 0) {
  x <- as.numeric(x)
  x <- x[is.finite(x)]
  if (target_len <= 0L) return(numeric(0))
  if (length(x) == 0L) return(rep(as.numeric(fill), target_len))
  if (length(x) >= target_len) return(tail(x, target_len))
  c(rep(as.numeric(fill), target_len - length(x)), x)
}

ndlm_theory_find_input <- function(env_key, shared_root, rel_path) {
  p <- Sys.getenv(env_key, "")
  if (nzchar(p)) {
    return(normalizePath(p, mustWork = FALSE))
  }
  if (!nzchar(shared_root)) return("")
  normalizePath(file.path(shared_root, rel_path), mustWork = FALSE)
}

ndlm_theory_load_inputs <- function(horizon_cap = 14L) {
  shared_root <- Sys.getenv("NDLM_SHARED_INPUT_ROOT", "")
  if (nzchar(shared_root)) shared_root <- normalizePath(shared_root, mustWork = FALSE)

  retros_path <- ndlm_theory_find_input("NDLM_RETROS_CSV", shared_root, file.path("retros", "retros.csv"))
  nws_path <- ndlm_theory_find_input("NDLM_NWS_FORECAST_CSV", shared_root, file.path("forecasts", "nws_forecast.csv"))
  glofas_path <- ndlm_theory_find_input("NDLM_GLOFAS_FORECAST_CSV", shared_root, file.path("forecasts", "glofas_forecast.csv"))

  retros_df <- ndlm_theory_read_csv(retros_path, "retros")
  nws_df <- ndlm_theory_read_csv(nws_path, "nws_forecast")
  glofas_df <- ndlm_theory_read_csv(glofas_path, "glofas_forecast")

  y <- ndlm_theory_pick_numeric_column(retros_df, preferred = c("USGS", "y", "obs", "flow", "value"))
  if (is.null(y)) {
    stop(sprintf("ndlm theory retros has no numeric target column: %s", retros_path), call. = FALSE)
  }
  y <- as.numeric(y)
  y <- y[is.finite(y)]
  if (length(y) < 30L) {
    stop("ndlm theory requires at least 30 finite observations in retros", call. = FALSE)
  }
  Tn <- length(y)

  cov_keys <- c(
    "NDLM_COV1_ELI_CSV",
    "NDLM_COV2_ONI_CSV",
    "NDLM_PPT_CSV",
    "NDLM_SOIL_CSV",
    "NDLM_PCA_CSV"
  )
  cov_series <- vector("list", length(cov_keys))
  for (i in seq_along(cov_keys)) {
    pth <- Sys.getenv(cov_keys[[i]], "")
    if (!nzchar(pth) || !file.exists(pth)) {
      cov_series[[i]] <- rep(0, Tn)
      next
    }
    cdf <- ndlm_theory_read_csv(pth, cov_keys[[i]])
    col <- ndlm_theory_pick_numeric_column(cdf)
    if (is.null(col)) {
      cov_series[[i]] <- rep(0, Tn)
      next
    }
    cov_series[[i]] <- ndlm_theory_align_series(col, Tn, fill = 0)
  }
  X <- do.call(cbind, cov_series)
  colnames(X) <- c("ELI", "ONI", "PPT", "SOIL", "PCA")

  nws_vec <- ndlm_theory_pick_numeric_column(nws_df, preferred = c("nws", "forecast", "value", "flow"))
  glofas_vec <- ndlm_theory_pick_numeric_column(glofas_df, preferred = c("glofas", "forecast", "value", "flow", "member_value"))
  if (is.null(nws_vec) || is.null(glofas_vec)) {
    stop("ndlm theory forecast inputs require numeric forecast columns", call. = FALSE)
  }
  nws_vec <- as.numeric(nws_vec)
  nws_vec <- nws_vec[is.finite(nws_vec)]
  glofas_vec <- as.numeric(glofas_vec)
  glofas_vec <- glofas_vec[is.finite(glofas_vec)]

  horizon_cap <- suppressWarnings(as.integer(horizon_cap[[1L]]))
  if (!is.finite(horizon_cap) || horizon_cap <= 0L) {
    stop(sprintf("ndlm theory forecast horizon cap must be a positive integer; got '%s'", as.character(horizon_cap)), call. = FALSE)
  }

  nws_len_raw <- length(nws_vec)
  glofas_len_raw <- length(glofas_vec)
  nws_len <- min(nws_len_raw, horizon_cap)
  glofas_len <- min(glofas_len_raw, horizon_cap)
  K_overlap <- min(nws_len, glofas_len)
  K_max <- max(nws_len, glofas_len)
  if (K_overlap < 3L) {
    stop("ndlm theory requires at least 3 overlapping finite forecast leads across sources", call. = FALSE)
  }
  if (K_max < 3L) {
    stop("ndlm theory requires forecast vectors with at least 3 finite rows after horizon capping", call. = FALSE)
  }

  list(
    y = y,
    X = X,
    T = Tn,
    forecast = list(
      nws = nws_vec[seq_len(nws_len)],
      glofas = glofas_vec[seq_len(glofas_len)],
      K = K_max,
      K_overlap = K_overlap,
      K_max = K_max,
      K_vec = c(nws = nws_len, glofas = glofas_len),
      K_cap = horizon_cap,
      nws_len = nws_len,
      glofas_len = glofas_len,
      nws_len_raw = nws_len_raw,
      glofas_len_raw = glofas_len_raw
    ),
    input_paths = list(
      retros = retros_path,
      nws = nws_path,
      glofas = glofas_path,
      parameters = Sys.getenv("NDLM_PARAMETERS_TXT", "")
    )
  )
}
