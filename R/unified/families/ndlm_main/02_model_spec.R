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

ndlm_theory_kalman_smoother_r <- function(y, H_mat, R_vec, q_diag, m0, C0, df_mat = NULL) {
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

  a <- matrix(0, nrow = d, ncol = Tn)
  m <- matrix(0, nrow = d, ncol = Tn)
  Rpred <- array(0, dim = c(d, d, Tn))
  C <- array(0, dim = c(d, d, Tn))
  pred_mean <- rep(NA_real_, Tn)
  pred_var <- rep(NA_real_, Tn)
  filter_mean <- rep(NA_real_, Tn)
  filter_var <- rep(NA_real_, Tn)

  m_prev <- m0
  C_prev <- C0

  for (t in seq_len(Tn)) {
    H_t <- matrix(H_mat[t, ], ncol = 1)
    a_t <- m_prev
    P_t <- C_prev
    if (use_discount) {
      W_t <- df_mat * P_t
      R_t <- P_t + W_t + Q
    } else {
      R_t <- C_prev + Q
    }
    R_t <- (R_t + t(R_t)) / 2
    Qy <- as.numeric(crossprod(H_t, R_t %*% H_t)) + R_vec[t]
    Qy <- max(Qy, 1e-10)
    K <- as.vector((R_t %*% H_t) / Qy)
    innov <- y[t] - as.numeric(crossprod(H_t, a_t))
    m_t <- a_t + K * innov
    C_t <- R_t - (R_t %*% (H_t %*% t(H_t)) %*% R_t) / Qy
    C_t <- (C_t + t(C_t)) / 2
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
      R_next <- Rpred[, , t + 1]
      R_next_inv <- tryCatch(
        solve(R_next),
        error = function(e) solve(R_next + diag(1e-8, d))
      )
      J_t <- C[, , t] %*% R_next_inv
      ms[, t] <- m[, t] + as.vector(J_t %*% (ms[, t + 1] - a[, t + 1]))
      Cs_t <- C[, , t] + J_t %*% (Cs[, , t + 1] - R_next) %*% t(J_t)
      Cs[, , t] <- (Cs_t + t(Cs_t)) / 2
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
    fitted_var = pmax(as.numeric(smooth_obs_var), 1e-10)
  )
}

ndlm_theory_kalman_smoother <- function(y, H_mat, R_vec, q_diag, m0, C0, df_mat = NULL, backend = "r") {
  backend <- ndlm_theory_kalman_backend_normalize(backend)
  if (identical(backend, "cpp")) {
    ndlm_theory_kalman_load_cpp()
    out <- ndlm_kalman_smoother_cpp(
      y = as.numeric(y),
      H_mat = as.matrix(H_mat),
      R_vec_in = as.numeric(R_vec),
      q_diag_in = as.numeric(q_diag),
      df_mat_in = if (is.null(df_mat)) NULL else as.matrix(df_mat),
      m0 = as.numeric(m0),
      C0 = as.matrix(C0)
    )
    out$predicted_mean <- as.numeric(out$predicted_mean)
    out$predicted_var <- pmax(as.numeric(out$predicted_var), 1e-10)
    out$filtered_mean <- as.numeric(out$filtered_mean)
    out$filtered_var <- pmax(as.numeric(out$filtered_var), 1e-10)
    out$smoothed_mean <- as.numeric(out$smoothed_mean)
    out$smoothed_var <- pmax(as.numeric(out$smoothed_var), 1e-10)
    out$fitted_mean <- as.numeric(out$fitted_mean)
    out$fitted_var <- pmax(as.numeric(out$fitted_var), 1e-10)
    return(out)
  }
  ndlm_theory_kalman_smoother_r(y = y, H_mat = H_mat, R_vec = R_vec, q_diag = q_diag, m0 = m0, C0 = C0, df_mat = df_mat)
}
