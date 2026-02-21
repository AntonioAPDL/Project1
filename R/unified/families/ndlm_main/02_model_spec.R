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

ndlm_theory_kalman_smoother_r <- function(y, H_mat, R_vec, q_diag, m0, C0) {
  y <- as.numeric(y)
  H_mat <- as.matrix(H_mat)
  Tn <- length(y)
  d <- ncol(H_mat)
  if (nrow(H_mat) != Tn) {
    stop("H_mat row count must match y length", call. = FALSE)
  }

  R_vec <- pmax(as.numeric(R_vec), 1e-10)
  Q <- diag(pmax(as.numeric(q_diag), 1e-10), d)
  m0 <- as.numeric(m0)
  C0 <- as.matrix(C0)

  a <- matrix(0, nrow = d, ncol = Tn)
  m <- matrix(0, nrow = d, ncol = Tn)
  Rpred <- array(0, dim = c(d, d, Tn))
  C <- array(0, dim = c(d, d, Tn))

  m_prev <- m0
  C_prev <- C0

  for (t in seq_len(Tn)) {
    H_t <- matrix(H_mat[t, ], ncol = 1)
    a_t <- m_prev
    R_t <- C_prev + Q
    Qy <- as.numeric(crossprod(H_t, R_t %*% H_t)) + R_vec[t]
    Qy <- max(Qy, 1e-10)
    K <- as.vector((R_t %*% H_t) / Qy)
    innov <- y[t] - as.numeric(crossprod(H_t, a_t))
    m_t <- a_t + K * innov
    C_t <- R_t - (R_t %*% (H_t %*% t(H_t)) %*% R_t) / Qy
    C_t <- (C_t + t(C_t)) / 2

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

  fitted_mean <- rowSums(H_mat * t(ms))
  fitted_var <- vapply(
    seq_len(Tn),
    function(t) as.numeric(crossprod(H_mat[t, ], Cs[, , t] %*% H_mat[t, ])),
    numeric(1)
  )

  list(
    smooth_mean = ms,
    smooth_cov = Cs,
    fitted_mean = fitted_mean,
    fitted_var = pmax(fitted_var, 1e-10)
  )
}

ndlm_theory_kalman_smoother <- function(y, H_mat, R_vec, q_diag, m0, C0, backend = "r") {
  backend <- ndlm_theory_kalman_backend_normalize(backend)
  if (identical(backend, "cpp")) {
    ndlm_theory_kalman_load_cpp()
    out <- ndlm_kalman_smoother_cpp(
      y = as.numeric(y),
      H_mat = as.matrix(H_mat),
      R_vec_in = as.numeric(R_vec),
      q_diag_in = as.numeric(q_diag),
      m0 = as.numeric(m0),
      C0 = as.matrix(C0)
    )
    out$fitted_mean <- as.numeric(out$fitted_mean)
    out$fitted_var <- pmax(as.numeric(out$fitted_var), 1e-10)
    return(out)
  }
  ndlm_theory_kalman_smoother_r(y = y, H_mat = H_mat, R_vec = R_vec, q_diag = q_diag, m0 = m0, C0 = C0)
}
