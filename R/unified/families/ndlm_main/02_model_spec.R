ndlm_theory_kalman_backend_normalize <- function(backend = "r") {
  backend <- tolower(trimws(as.character(backend[[1L]])))
  if (!nzchar(backend)) backend <- "r"
  if (!(backend %in% c("r", "cpp"))) {
    stop(sprintf("ndlm kalman backend must be one of: r, cpp; got '%s'", backend), call. = FALSE)
  }
  backend
}

ndlm_theory_kalman_load_cpp <- function() {
  if (exists("ndlm_kalman_smoother_cpp", mode = "function", inherits = TRUE)) {
    return(invisible(TRUE))
  }
  if (!requireNamespace("Rcpp", quietly = TRUE)) {
    stop("NDLM cpp backend requires package 'Rcpp'", call. = FALSE)
  }

  env_cpp <- Sys.getenv("NDLM_KALMAN_CPP_PATH", "")
  candidates <- c(
    env_cpp,
    file.path(getwd(), "R", "unified", "families", "ndlm_main", "ndlm_kalman_backend.cpp"),
    file.path(getwd(), "..", "R", "unified", "families", "ndlm_main", "ndlm_kalman_backend.cpp"),
    file.path(getwd(), "..", "..", "R", "unified", "families", "ndlm_main", "ndlm_kalman_backend.cpp")
  )
  candidates <- unique(candidates[nzchar(candidates)])
  cpp_path <- ""
  for (cand in candidates) {
    cand_norm <- normalizePath(cand, mustWork = FALSE)
    if (file.exists(cand_norm)) {
      cpp_path <- cand_norm
      break
    }
  }
  if (!nzchar(cpp_path)) {
    stop(
      sprintf(
        "NDLM cpp backend source not found in any candidate path: %s",
        paste(candidates, collapse = " | ")
      ),
      call. = FALSE
    )
  }
  Rcpp::sourceCpp(cpp_path)
  if (!exists("ndlm_kalman_smoother_cpp", mode = "function", inherits = TRUE)) {
    stop("NDLM cpp backend compiled but exported symbol 'ndlm_kalman_smoother_cpp' was not found", call. = FALSE)
  }
  invisible(TRUE)
}

ndlm_theory_cov_stabilization_defaults <- function(stabilization = NULL) {
  if (!is.list(stabilization)) stabilization <- list()
  read_num <- function(x, default, min_val = -Inf, max_val = Inf) {
    out <- suppressWarnings(if (is.null(x) || length(x) < 1L) NA_real_ else as.numeric(x[[1L]]))
    if (!is.finite(out)) out <- suppressWarnings(as.numeric(default))
    if (!is.finite(out)) out <- 0
    out <- max(out, as.numeric(min_val))
    out <- min(out, as.numeric(max_val))
    out
  }
  cov_eig_floor <- read_num(stabilization$cov_eig_floor, 1e-8, min_val = 1e-12)
  cov_eig_cap <- read_num(stabilization$cov_eig_cap, 1e8, min_val = cov_eig_floor * 10)
  cov_diag_jitter <- read_num(stabilization$cov_diag_jitter, 1e-10, min_val = 0)
  list(
    cov_eig_floor = cov_eig_floor,
    cov_eig_cap = cov_eig_cap,
    cov_diag_jitter = cov_diag_jitter
  )
}

ndlm_theory_cov_stabilize_one <- function(Sigma, stabilization = NULL) {
  params <- ndlm_theory_cov_stabilization_defaults(stabilization)
  stats <- list(
    calls = 1L,
    cov_projected = 0L,
    cov_floor_clipped = 0L,
    cov_cap_clipped = 0L,
    cov_nonfinite_inputs = 0L
  )
  Sigma <- as.matrix(Sigma)
  if (!is.numeric(Sigma) || nrow(Sigma) != ncol(Sigma)) {
    stop("NDLM covariance stabilization requires a numeric square matrix", call. = FALSE)
  }
  d <- nrow(Sigma)
  if (!all(is.finite(Sigma))) {
    Sigma[!is.finite(Sigma)] <- 0
    stats$cov_nonfinite_inputs <- 1L
  }
  Sigma <- (Sigma + t(Sigma)) / 2

  eig_vals <- tryCatch(
    suppressWarnings(eigen(Sigma, symmetric = TRUE, only.values = TRUE)$values),
    error = function(e) rep(NA_real_, d)
  )
  has_nonfinite_eigs <- any(!is.finite(eig_vals))
  floor_hit <- has_nonfinite_eigs || min(eig_vals, na.rm = TRUE) < params$cov_eig_floor
  cap_hit <- has_nonfinite_eigs || max(eig_vals, na.rm = TRUE) > params$cov_eig_cap
  if (isTRUE(floor_hit) || isTRUE(cap_hit)) {
    stats$cov_projected <- 1L
    stats$cov_floor_clipped <- as.integer(isTRUE(floor_hit))
    stats$cov_cap_clipped <- as.integer(isTRUE(cap_hit))
    eig <- tryCatch(
      suppressWarnings(eigen(Sigma, symmetric = TRUE)),
      error = function(e) NULL
    )
    if (is.null(eig) || any(!is.finite(eig$values)) || any(!is.finite(eig$vectors))) {
      Sigma <- diag(params$cov_eig_floor, d)
    } else {
      vals <- as.numeric(eig$values)
      vals <- pmin(pmax(vals, params$cov_eig_floor), params$cov_eig_cap)
      Sigma <- eig$vectors %*% diag(vals, length(vals)) %*% t(eig$vectors)
    }
  }
  Sigma <- (Sigma + t(Sigma)) / 2
  if (isTRUE(params$cov_diag_jitter > 0)) {
    Sigma <- Sigma + diag(params$cov_diag_jitter, d)
  }
  for (ii in seq_len(3L)) {
    final_min <- tryCatch(
      suppressWarnings(min(eigen(Sigma, symmetric = TRUE, only.values = TRUE)$values)),
      error = function(e) NA_real_
    )
    if (is.finite(final_min) && final_min >= params$cov_eig_floor) {
      break
    }
    shift <- if (!is.finite(final_min)) params$cov_eig_floor else (params$cov_eig_floor - final_min)
    shift <- max(shift + params$cov_diag_jitter, params$cov_diag_jitter)
    Sigma <- Sigma + diag(shift, d)
    stats$cov_projected <- max(stats$cov_projected, 1L)
    stats$cov_floor_clipped <- max(stats$cov_floor_clipped, 1L)
  }
  list(cov = Sigma, stats = stats)
}

ndlm_theory_kalman_smoother_r <- function(y, H_mat, R_vec, q_diag, m0, C0, df_mat = NULL, stabilization = NULL) {
  y <- as.numeric(y)
  H_mat <- as.matrix(H_mat)
  Tn <- length(y)
  d <- ncol(H_mat)
  if (nrow(H_mat) != Tn) {
    stop("H_mat row count must match y length", call. = FALSE)
  }

  R_vec <- pmax(as.numeric(R_vec), 1e-10)
  Q <- diag(pmax(as.numeric(q_diag), 1e-10), d)
  use_discount <- !is.null(df_mat)
  if (use_discount) {
    df_mat <- as.matrix(df_mat)
    if (!all(dim(df_mat) == c(d, d))) {
      stop("df_mat must have shape d x d", call. = FALSE)
    }
    if (any(!is.finite(df_mat))) {
      stop("df_mat must contain finite numeric values", call. = FALSE)
    }
    df_mat <- (df_mat + t(df_mat)) / 2
    df_mat[df_mat < 0] <- 0
  }
  m0 <- as.numeric(m0)
  C0 <- as.matrix(C0)
  stab <- ndlm_theory_cov_stabilization_defaults(stabilization)
  stab_stats <- list(
    calls = 0L,
    cov_projected = 0L,
    cov_floor_clipped = 0L,
    cov_cap_clipped = 0L,
    cov_nonfinite_inputs = 0L
  )
  accumulate_stats <- function(piece) {
    for (nm in names(stab_stats)) {
      cur <- suppressWarnings(as.integer(piece[[nm]]))
      if (!is.finite(cur)) cur <- 0L
      stab_stats[[nm]] <<- stab_stats[[nm]] + cur
    }
  }
  stabilize_cov <- function(S) {
    out <- ndlm_theory_cov_stabilize_one(S, stabilization = stab)
    accumulate_stats(out$stats)
    out$cov
  }

  a <- matrix(0, nrow = d, ncol = Tn)
  m <- matrix(0, nrow = d, ncol = Tn)
  Rpred <- array(0, dim = c(d, d, Tn))
  C <- array(0, dim = c(d, d, Tn))
  pred_mean <- rep(NA_real_, Tn)
  pred_var <- rep(NA_real_, Tn)
  filter_mean <- rep(NA_real_, Tn)
  filter_var <- rep(NA_real_, Tn)

  m_prev <- m0
  C_prev <- stabilize_cov(C0)

  for (t in seq_len(Tn)) {
    H_t <- matrix(H_mat[t, ], ncol = 1)
    a_t <- m_prev
    P_t <- stabilize_cov(C_prev)
    if (use_discount) {
      W_t <- df_mat * P_t
      R_t <- stabilize_cov(P_t + W_t + Q)
    } else {
      R_t <- stabilize_cov(C_prev + Q)
    }
    Qy <- as.numeric(crossprod(H_t, R_t %*% H_t)) + R_vec[t]
    Qy <- max(Qy, 1e-10)
    K <- as.vector((R_t %*% H_t) / Qy)
    innov <- y[t] - as.numeric(crossprod(H_t, a_t))
    m_t <- a_t + K * innov
    C_t <- stabilize_cov(R_t - (R_t %*% (H_t %*% t(H_t)) %*% R_t) / Qy)
    pred_mean[t] <- as.numeric(crossprod(H_t, a_t))
    pred_var[t] <- max(as.numeric(crossprod(H_t, R_t %*% H_t)) + R_vec[t], 1e-10)
    filter_mean[t] <- as.numeric(crossprod(H_t, m_t))
    filter_var[t] <- max(as.numeric(crossprod(H_t, C_t %*% H_t)) + R_vec[t], 1e-10)

    a[, t] <- a_t
    m[, t] <- m_t
    Rpred[, , t] <- R_t
    C[, , t] <- C_t
    m_prev <- m_t
    C_prev <- C_t
  }

  ms <- m
  Cs <- C
  if (Tn >= 2) {
    for (t in (Tn - 1):1) {
      R_next <- stabilize_cov(Rpred[, , t + 1])
      R_next_inv <- tryCatch(
        solve(R_next),
        error = function(e) solve(R_next + diag(max(stab$cov_diag_jitter, 1e-8), d))
      )
      J_t <- C[, , t] %*% R_next_inv
      ms[, t] <- m[, t] + as.vector(J_t %*% (ms[, t + 1] - a[, t + 1]))
      Cs_t <- C[, , t] + J_t %*% (Cs[, , t + 1] - R_next) %*% t(J_t)
      Cs[, , t] <- stabilize_cov(Cs_t)
    }
  }

  smooth_obs_mean <- rowSums(H_mat * t(ms))
  smooth_obs_var <- vapply(
    seq_len(Tn),
    function(t) as.numeric(crossprod(H_mat[t, ], Cs[, , t] %*% H_mat[t, ])) + R_vec[t],
    numeric(1)
  )

  list(
    smooth_mean = ms,
    smooth_cov = Cs,
    predicted_mean = as.numeric(pred_mean),
    predicted_var = pmax(as.numeric(pred_var), 1e-10),
    filtered_mean = as.numeric(filter_mean),
    filtered_var = pmax(as.numeric(filter_var), 1e-10),
    smoothed_mean = as.numeric(smooth_obs_mean),
    smoothed_var = pmax(as.numeric(smooth_obs_var), 1e-10),
    fitted_mean = as.numeric(smooth_obs_mean),
    fitted_var = pmax(as.numeric(smooth_obs_var), 1e-10),
    stabilization = stab_stats
  )
}

ndlm_theory_kalman_smoother <- function(y, H_mat, R_vec, q_diag, m0, C0, df_mat = NULL, backend = "r", stabilization = NULL) {
  backend <- ndlm_theory_kalman_backend_normalize(backend)
  stab <- ndlm_theory_cov_stabilization_defaults(stabilization)
  if (identical(backend, "cpp")) {
    ndlm_theory_kalman_load_cpp()
    out <- ndlm_kalman_smoother_cpp(
      y = as.numeric(y),
      H_mat = as.matrix(H_mat),
      R_vec_in = as.numeric(R_vec),
      q_diag_in = as.numeric(q_diag),
      df_mat_in = if (is.null(df_mat)) NULL else as.matrix(df_mat),
      m0 = as.numeric(m0),
      C0 = as.matrix(C0),
      cov_eig_floor = as.numeric(stab$cov_eig_floor),
      cov_eig_cap = as.numeric(stab$cov_eig_cap),
      cov_diag_jitter = as.numeric(stab$cov_diag_jitter)
    )
    out$predicted_mean <- as.numeric(out$predicted_mean)
    out$predicted_var <- pmax(as.numeric(out$predicted_var), 1e-10)
    out$filtered_mean <- as.numeric(out$filtered_mean)
    out$filtered_var <- pmax(as.numeric(out$filtered_var), 1e-10)
    out$smoothed_mean <- as.numeric(out$smoothed_mean)
    out$smoothed_var <- pmax(as.numeric(out$smoothed_var), 1e-10)
    out$fitted_mean <- as.numeric(out$fitted_mean)
    out$fitted_var <- pmax(as.numeric(out$fitted_var), 1e-10)
    if (is.null(out$stabilization) || !is.list(out$stabilization)) {
      out$stabilization <- list(
        calls = 0L,
        cov_projected = 0L,
        cov_floor_clipped = 0L,
        cov_cap_clipped = 0L,
        cov_nonfinite_inputs = 0L
      )
    }
    return(out)
  }
  ndlm_theory_kalman_smoother_r(
    y = y,
    H_mat = H_mat,
    R_vec = R_vec,
    q_diag = q_diag,
    m0 = m0,
    C0 = C0,
    df_mat = df_mat,
    stabilization = stab
  )
}
