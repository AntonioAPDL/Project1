ndlm_theory_state_draws <- function(sm, sC, n_draws, seed) {
  set.seed(seed)
  d <- nrow(sm)
  Tn <- ncol(sm)
  out <- array(0, dim = c(d, Tn, n_draws))
  for (t in seq_len(Tn)) {
    Sigma <- as.matrix(sC[, , t])
    if (!all(is.finite(Sigma))) {
      stop(sprintf("[NDLM_COV_NONFINITE] smooth covariance slice t=%d contains non-finite values", as.integer(t)), call. = FALSE)
    }
    L <- ndlm_theory_safe_chol(Sigma)
    Z <- matrix(stats::rnorm(d * n_draws), nrow = d, ncol = n_draws)
    out[, t, ] <- sm[, t] + L %*% Z
  }
  out
}

ndlm_theory_standardize <- function(x) {
  x <- as.numeric(x)
  x[!is.finite(x)] <- NA_real_
  mu <- mean(x, na.rm = TRUE)
  sdv <- stats::sd(x, na.rm = TRUE)
  if (!is.finite(mu)) mu <- 0
  if (!is.finite(sdv) || sdv < 1e-8) {
    return(rep(0, length(x)))
  }
  z <- (x - mu) / sdv
  z[!is.finite(z)] <- 0
  z
}

ndlm_theory_build_ragged_horizon <- function(forecast) {
  k_nws <- suppressWarnings(as.integer(forecast$K_vec[["nws"]]))
  k_glofas <- suppressWarnings(as.integer(forecast$K_vec[["glofas"]]))
  if (!is.finite(k_nws) || k_nws < 1L || !is.finite(k_glofas) || k_glofas < 1L) {
    stop("ndlm theory ragged horizon requires positive K_vec entries for nws and glofas", call. = FALSE)
  }

  k_overlap <- min(k_nws, k_glofas)
  k_max <- max(k_nws, k_glofas)
  k_tail <- max(k_max - k_overlap, 0L)
  extension_source <- if (k_nws >= k_glofas) "nws" else "glofas"
  bridge_source <- if (identical(extension_source, "nws")) "glofas" else "nws"

  active_sources <- lapply(seq_len(k_max), function(k) {
    out <- character(0)
    if (k <= k_nws) out <- c(out, "nws")
    if (k <= k_glofas) out <- c(out, "glofas")
    out
  })

  list(
    K_overlap = as.integer(k_overlap),
    K_max = as.integer(k_max),
    K_tail = as.integer(k_tail),
    K_vec = c(nws = as.integer(k_nws), glofas = as.integer(k_glofas)),
    extension_source = extension_source,
    bridge_source = bridge_source,
    segment_lengths = c(overlap = as.integer(k_overlap), extension = as.integer(k_tail)),
    active_sources = active_sources
  )
}

ndlm_theory_make_df_mat <- function(df, dim_df, n, power = 1L) {
  if (sum(dim_df) != n) {
    stop("sum(dim_df) must equal n for ndlm discount matrix construction", call. = FALSE)
  }
  if (length(df) != length(dim_df)) {
    stop("length(df) must match length(dim_df) for ndlm discount matrix construction", call. = FALSE)
  }
  pwr <- suppressWarnings(as.numeric(power))
  if (!is.finite(pwr) || pwr < 1) pwr <- 1
  dfs <- rep(as.numeric(df), as.integer(dim_df))
  dfs <- pmin(pmax(dfs, 1e-8), 1 - 1e-8)
  idx <- c(0L, cumsum(as.integer(dim_df)))
  out <- matrix(0, nrow = n, ncol = n)
  for (j in seq_len(length(dim_df))) {
    cur <- dfs[idx[j + 1L]]
    scale <- (1 - cur^pwr) / (cur^pwr)
    out[(idx[j] + 1L):idx[j + 1L], (idx[j] + 1L):idx[j + 1L]] <- scale
  }
  out
}

ndlm_theory_df_components <- function(constants, mode = c("hist", "fore"), k = 1L) {
  mode <- match.arg(mode)
  k <- suppressWarnings(as.integer(k[[1L]]))
  if (!is.finite(k) || k < 1L) k <- 1L
  df_hist <- c(constants$df_t, constants$df_s1, constants$df_s2, constants$df_s67)
  if (identical(mode, "hist")) {
    return(df_hist)
  }
  trend_df <- constants$df_t * constants$df_discrep * (constants$lambda ^ max(k - 1L, 0L))
  trend_df <- pmin(pmax(trend_df, 1e-8), 1 - 1e-8)
  c(trend_df, constants$df_s1, constants$df_s2, constants$df_s67)
}

ndlm_theory_q_diag_from_discount <- function(constants, state_dim) {
  state_dim <- suppressWarnings(as.integer(state_dim[[1L]]))
  if (!is.finite(state_dim) || state_dim < 14L) {
    stop("state_dim must be >= 14 for ndlm discount-based q_diag construction", call. = FALSE)
  }
  hist_diag <- rep(1e-8, 7L)
  fore_diag <- rep(1e-8, 7L)
  extra_len <- state_dim - 14L
  extra_diag <- numeric(0)
  if (extra_len > 0L) {
    extra_diag <- rep(1e-8, extra_len)
  }
  q_diag <- c(hist_diag, fore_diag, extra_diag)
  pmax(as.numeric(q_diag), 1e-8)
}

ndlm_theory_discount_matrix_full <- function(constants, state_dim, k = 1L) {
  state_dim <- suppressWarnings(as.integer(state_dim[[1L]]))
  if (!is.finite(state_dim) || state_dim < 14L) {
    stop("state_dim must be >= 14 for ndlm discount matrix construction", call. = FALSE)
  }
  hist_df <- ndlm_theory_df_components(constants, mode = "hist", k = k)
  discrep_df <- pmin(pmax(constants$df_discrep * hist_df, 1e-8), 1 - 1e-8)
  df_hist <- ndlm_theory_make_df_mat(hist_df, dim_df = c(1L, 2L, 2L, 2L), n = 7L, power = 1L)
  df_discrep <- ndlm_theory_make_df_mat(discrep_df, dim_df = c(1L, 2L, 2L, 2L), n = 7L, power = 1L)
  out <- matrix(0, nrow = state_dim, ncol = state_dim)
  out[1:7, 1:7] <- df_hist
  out[8:14, 8:14] <- df_discrep
  if (state_dim > 14L) {
    extra_n <- state_dim - 14L
    extra_df <- rep(constants$df_covs, extra_n)
    extra_df[[1L]] <- constants$df_trans
    extra_df <- pmin(pmax(extra_df, 1e-8), 1 - 1e-8)
    out[15:state_dim, 15:state_dim] <- diag((1 - extra_df) / extra_df, extra_n)
  }
  out
}

ndlm_theory_safe_chol <- function(Sigma) {
  try_chol <- function(M, jitters) {
    for (j in jitters) {
      out <- tryCatch(chol(M + diag(j, nrow(M))), error = function(e) NULL)
      if (!is.null(out)) return(out)
    }
    NULL
  }

  Sigma <- as.matrix(Sigma)
  if (!all(is.finite(Sigma))) {
    stop("[NDLM_COV_NONFINITE] covariance contains non-finite values", call. = FALSE)
  }
  if (!is.numeric(Sigma) || nrow(Sigma) != ncol(Sigma)) {
    stop("[NDLM_COV_SHAPE] covariance must be a finite square numeric matrix", call. = FALSE)
  }
  Sigma <- (Sigma + t(Sigma)) / 2
  jitters <- c(0, 1e-12, 1e-10, 1e-8, 1e-6, 1e-4, 1e-2)

  out <- try_chol(Sigma, jitters)
  if (!is.null(out)) return(out)

  eig <- eigen(Sigma, symmetric = TRUE)
  vals <- pmax(as.numeric(eig$values), 1e-8)
  Sigma_psd <- eig$vectors %*% diag(vals, length(vals)) %*% t(eig$vectors)
  Sigma_psd <- (Sigma_psd + t(Sigma_psd)) / 2
  if (all(is.finite(Sigma_psd))) {
    out <- try_chol(Sigma_psd, jitters)
    if (!is.null(out)) return(out)
  }

  # Last-resort SPD projection with nearPD for extreme numerical instability.
  if (requireNamespace("Matrix", quietly = TRUE)) {
    np <- tryCatch(
      Matrix::nearPD(
        Sigma,
        corr = FALSE,
        keepDiag = FALSE,
        do2eigen = TRUE,
        doSym = TRUE,
        base.matrix = TRUE
      ),
      error = function(e) NULL
    )
    if (!is.null(np) && !is.null(np$mat)) {
      S_np <- as.matrix(np$mat)
      if (all(is.finite(S_np))) {
        S_np <- (S_np + t(S_np)) / 2
        out <- try_chol(S_np, c(0, jitters, 1e-1))
        if (!is.null(out)) return(out)
      }
    }
  }

  min_eig <- suppressWarnings(min(eigen(Sigma, symmetric = TRUE, only.values = TRUE)$values))
  stop(
    sprintf(
      "[NDLM_COV_NOT_SPD] unable to obtain SPD covariance for Cholesky (n=%d, min_eig=%s)",
      as.integer(nrow(Sigma)),
      as.character(signif(min_eig, 6))
    ),
    call. = FALSE
  )
}

ndlm_theory_covariance_diagnostics_one <- function(object_name, cov_arr) {
  dims <- dim(cov_arr)
  if (is.null(dims) || length(dims) != 3L || dims[1] != dims[2]) {
    stop(sprintf("[NDLM_COV_SHAPE] %s must be a square 3D covariance array", object_name), call. = FALSE)
  }
  n_slices <- as.integer(dims[3])
  min_eigs <- rep(NA_real_, n_slices)
  min_diags <- rep(NA_real_, n_slices)
  max_asym <- rep(NA_real_, n_slices)
  nonfinite <- rep(FALSE, n_slices)
  base_chol_fail <- rep(FALSE, n_slices)

  for (k in seq_len(n_slices)) {
    S <- as.matrix(cov_arr[, , k, drop = TRUE])
    if (!all(is.finite(S))) {
      nonfinite[k] <- TRUE
      next
    }
    S <- (S + t(S)) / 2
    max_asym[k] <- max(abs(S - t(S)))
    min_diags[k] <- min(diag(S))
    min_eigs[k] <- min(eigen(S, symmetric = TRUE, only.values = TRUE)$values)
    base_try <- tryCatch(chol(S + diag(1e-8, nrow(S))), error = function(e) NULL)
    base_chol_fail[k] <- is.null(base_try)
  }

  data.frame(
    object = object_name,
    n_slices = n_slices,
    matrix_dim = as.integer(dims[1]),
    nonfinite_slices = as.integer(sum(nonfinite)),
    asymmetry_max = if (all(is.na(max_asym))) NA_real_ else max(max_asym, na.rm = TRUE),
    min_diag_min = if (all(is.na(min_diags))) NA_real_ else min(min_diags, na.rm = TRUE),
    min_eig_min = if (all(is.na(min_eigs))) NA_real_ else min(min_eigs, na.rm = TRUE),
    min_eig_p01 = if (all(is.na(min_eigs))) NA_real_ else as.numeric(stats::quantile(min_eigs, probs = 0.01, na.rm = TRUE, names = FALSE)),
    base_chol_fail_slices = as.integer(sum(base_chol_fail, na.rm = TRUE)),
    base_chol_fail_rate = mean(base_chol_fail, na.rm = TRUE),
    stringsAsFactors = FALSE
  )
}

ndlm_theory_collect_covariance_diagnostics <- function(fit_sC, sC_ens_1, sC_ens_2) {
  rows <- list(
    ndlm_theory_covariance_diagnostics_one("smooth_cov", fit_sC),
    ndlm_theory_covariance_diagnostics_one("forecast_cov_segment_1", sC_ens_1),
    ndlm_theory_covariance_diagnostics_one("forecast_cov_segment_2", sC_ens_2)
  )
  out <- do.call(rbind, rows)
  rownames(out) <- NULL
  out
}

ndlm_theory_alloc_segment_cov <- function(k_len, constants, base_cov, inactive_row = integer(0), start_k = 1L) {
  k_len <- suppressWarnings(as.integer(k_len[[1L]]))
  if (!is.finite(k_len) || k_len < 0L) k_len <- 0L
  start_k <- suppressWarnings(as.integer(start_k[[1L]]))
  if (!is.finite(start_k) || start_k < 1L) start_k <- 1L
  out <- array(0, dim = c(7L, 7L, k_len))
  if (k_len == 0L) return(out)
  base_cov <- as.matrix(base_cov)
  if (!all(dim(base_cov) == c(7L, 7L))) {
    stop("base_cov must be 7x7 for ndlm forecast segment covariance construction", call. = FALSE)
  }
  P_prev <- (base_cov + t(base_cov)) / 2 + diag(1e-8, 7L)
  inactive_row <- suppressWarnings(as.integer(inactive_row))
  for (k in seq_len(k_len)) {
    k_abs <- as.integer(start_k + k - 1L)
    df_fore_k <- ndlm_theory_df_components(constants, mode = "fore", k = k_abs)
    d <- ndlm_theory_make_df_mat(
      df = df_fore_k,
      dim_df = c(1L, 2L, 2L, 2L),
      n = 7L,
      power = 1L
    )
    Wk <- d * P_prev
    d <- (P_prev + Wk)
    d <- (d + t(d)) / 2
    if (length(inactive_row) > 0L) {
      keep <- inactive_row[inactive_row >= 1L & inactive_row <= 7L]
      if (length(keep) > 0L) {
        d[keep, ] <- 0
        d[, keep] <- 0
        d[cbind(keep, keep)] <- 1e-8
      }
    }
    d <- (d + t(d)) / 2 + diag(1e-8, 7L)
    out[, , k] <- d
    P_prev <- d
  }
  out
}

ndlm_theory_build_hist_pseudo_obs <- function(
  source_obs,
  sigma_by_source,
  source_names = c("usgs", "nws", "glofas"),
  fallback_y = NULL,
  fallback_var = 1e12
) {
  if (!is.list(source_obs)) {
    stop("source_obs must be a named list of source vectors", call. = FALSE)
  }
  source_names <- unique(as.character(source_names))
  source_names <- source_names[nzchar(source_names)]
  if (length(source_names) < 1L) {
    stop("source_names must include at least one source label", call. = FALSE)
  }

  lengths <- vapply(source_names, function(nm) length(as.numeric(source_obs[[nm]])), integer(1))
  Tn <- suppressWarnings(as.integer(max(lengths)))
  if (!is.finite(Tn) || Tn < 1L) {
    stop("source_obs must include at least one non-empty source vector", call. = FALSE)
  }

  fallback_y <- as.numeric(fallback_y)
  if (length(fallback_y) < Tn) {
    fallback_y <- c(fallback_y, rep(NA_real_, Tn - length(fallback_y)))
  }
  fallback_y <- fallback_y[seq_len(Tn)]

  fallback_var <- suppressWarnings(as.numeric(fallback_var[[1L]]))
  if (!is.finite(fallback_var) || fallback_var <= 0) {
    fallback_var <- 1e12
  }

  y_pseudo <- rep(0, Tn)
  R_vec <- rep(fallback_var, Tn)
  n_sources <- integer(Tn)

  for (t in seq_len(Tn)) {
    obs_vals <- numeric(0)
    prec_vals <- numeric(0)
    for (nm in source_names) {
      obs_nm <- as.numeric(source_obs[[nm]])
      if (length(obs_nm) < t) next
      y_nt <- obs_nm[[t]]
      sigma_nt <- suppressWarnings(as.numeric(sigma_by_source[[nm]]))
      if (!is.finite(y_nt) || !is.finite(sigma_nt) || sigma_nt <= 0) next
      obs_vals <- c(obs_vals, y_nt)
      prec_vals <- c(prec_vals, 1 / max(sigma_nt, 1e-10))
    }

    if (length(obs_vals) > 0L) {
      prec_sum <- sum(prec_vals)
      if (!is.finite(prec_sum) || prec_sum <= 0) {
        prec_sum <- 1e-12
      }
      y_pseudo[[t]] <- sum(obs_vals * prec_vals) / prec_sum
      R_vec[[t]] <- 1 / prec_sum
      n_sources[[t]] <- as.integer(length(obs_vals))
    } else {
      y_fallback <- fallback_y[[t]]
      if (!is.finite(y_fallback)) {
        y_fallback <- 0
      }
      y_pseudo[[t]] <- y_fallback
      R_vec[[t]] <- fallback_var
      n_sources[[t]] <- 0L
    }
  }

  list(
    y = as.numeric(y_pseudo),
    R_vec = pmax(as.numeric(R_vec), 1e-10),
    n_sources = as.integer(n_sources)
  )
}

ndlm_theory_has_converged <- function(
  iter,
  min_total_iters,
  crit_elbo,
  crit_elbo_rel,
  elbo_tol,
  elbo_rel_tol
) {
  if (!is.finite(iter) || !is.finite(min_total_iters) || as.integer(iter) < as.integer(min_total_iters)) {
    return(FALSE)
  }
  if (!is.finite(crit_elbo) || !is.finite(crit_elbo_rel)) {
    return(FALSE)
  }
  (crit_elbo <= elbo_tol) && (crit_elbo_rel <= elbo_rel_tol)
}

ndlm_theory_run_vb <- function(inputs, constants) {
  fmt_iter_num <- function(x, digits = 8L) {
    if (!is.finite(x)) {
      return("NA")
    }
    format(signif(as.numeric(x), digits = as.integer(digits)), trim = TRUE, scientific = FALSE)
  }

  set.seed(constants$seed)
  Tn <- inputs$T
  d <- constants$state_dim
  ragged <- ndlm_theory_build_ragged_horizon(inputs$forecast)
  K_overlap <- ragged$K_overlap
  K_tail <- ragged$K_tail
  K_max <- ragged$K_max

  H_mat <- matrix(0, nrow = Tn, ncol = d)
  H_mat[, 1] <- 1
  H_mat[, 2:6] <- inputs$X[, 1:5, drop = FALSE]
  if (Tn >= 2) {
    H_mat[-1, 7] <- diff(inputs$y)
  }
  H_mat[, 8:12] <- inputs$X[, 1:5, drop = FALSE]

  m0 <- rep(0, d)
  C0 <- diag(c(5, rep(1, d - 1)), d)

  source_names <- c("usgs", "nws", "glofas")
  retros <- inputs$retros
  if (!is.list(retros)) {
    retros <- list()
  }
  source_obs <- list(
    usgs = as.numeric(if (!is.null(retros$usgs)) retros$usgs else inputs$y),
    nws = as.numeric(if (!is.null(retros$nws)) retros$nws else rep(NA_real_, Tn)),
    glofas = as.numeric(if (!is.null(retros$glofas)) retros$glofas else rep(NA_real_, Tn))
  )
  for (nm in source_names) {
    cur <- source_obs[[nm]]
    if (length(cur) < Tn) {
      cur <- c(cur, rep(NA_real_, Tn - length(cur)))
    }
    source_obs[[nm]] <- as.numeric(cur[seq_len(Tn)])
  }

  sigma_init <- vapply(source_names, function(nm) {
    x <- source_obs[[nm]]
    sdv <- suppressWarnings(stats::sd(x, na.rm = TRUE))
    if (!is.finite(sdv) || sdv < 0.1) sdv <- 0.1
    as.numeric(sdv)
  }, numeric(1))
  names(sigma_init) <- source_names
  sigma_by_source <- pmax(sigma_init, 1e-6)

  hist_df_components <- ndlm_theory_df_components(constants, mode = "hist", k = 1L)
  fore_df_components <- ndlm_theory_df_components(constants, mode = "fore", k = 1L)
  w_hist <- mean((1 - hist_df_components) / hist_df_components)
  w_fore <- mean((1 - fore_df_components) / fore_df_components)

  max_iter <- suppressWarnings(as.integer(constants$max_iter))
  if (!is.finite(max_iter) || max_iter < 1L) {
    max_iter <- 100L
  }
  min_total_iters <- suppressWarnings(as.integer(constants$min_total_iters))
  if (!is.finite(min_total_iters) || min_total_iters < 1L) {
    min_total_iters <- min(50L, max_iter)
  }
  min_total_iters <- min(min_total_iters, max_iter)
  conv <- constants$convergence
  elbo_tol <- suppressWarnings(as.numeric(conv$elbo_tol))
  elbo_rel_tol <- suppressWarnings(as.numeric(conv$elbo_rel_tol))
  if (!is.finite(elbo_tol) || elbo_tol <= 0) elbo_tol <- 1e-6
  if (!is.finite(elbo_rel_tol) || elbo_rel_tol <= 0) elbo_rel_tol <- 2.5e-4

  seq_sigma <- matrix(NA_real_, nrow = max_iter, ncol = length(source_names))
  colnames(seq_sigma) <- sprintf("sigma_%s_exp", source_names)
  seq_elbo <- rep(NA_real_, max_iter)
  scale_colnames <- c(
    "sigma_exp",
    "sigma_usgs_exp",
    "sigma_nws_exp",
    "sigma_glofas_exp",
    "w_hist",
    "w_fore",
    "df_t",
    "df_s1",
    "df_s2",
    "df_s67",
    "df_discrep",
    "lambda",
    "df_trans",
    "df_covs"
  )
  seq_scale <- matrix(NA_real_, nrow = max_iter, ncol = length(scale_colnames))
  colnames(seq_scale) <- scale_colnames
  prev_elbo <- NA_real_
  crit_elbo <- Inf
  crit_elbo_rel <- Inf
  sigma_shape_final <- rep(constants$a_sigma, length(source_names))
  sigma_rate_final <- rep(constants$b_sigma, length(source_names))
  names(sigma_shape_final) <- source_names
  names(sigma_rate_final) <- source_names
  fit <- NULL
  converged <- FALSE
  convergence_reason <- "max_iter_reached"
  iterations_completed <- 0L
  df_mat_full <- ndlm_theory_discount_matrix_full(constants, state_dim = d, k = 1L)
  q_diag <- ndlm_theory_q_diag_from_discount(constants, state_dim = d)
  hist_assim <- ndlm_theory_build_hist_pseudo_obs(
    source_obs = source_obs,
    sigma_by_source = sigma_by_source,
    source_names = source_names,
    fallback_y = inputs$y,
    fallback_var = max(as.numeric(sigma_by_source[["usgs"]]), 1e6, na.rm = TRUE)
  )

  for (iter in seq_len(max_iter)) {
    hist_assim <- ndlm_theory_build_hist_pseudo_obs(
      source_obs = source_obs,
      sigma_by_source = sigma_by_source,
      source_names = source_names,
      fallback_y = inputs$y,
      fallback_var = max(as.numeric(sigma_by_source[["usgs"]]), 1e6, na.rm = TRUE)
    )

    fit <- ndlm_theory_kalman_smoother(
      y = hist_assim$y,
      H_mat = H_mat,
      R_vec = hist_assim$R_vec,
      q_diag = q_diag,
      df_mat = df_mat_full,
      m0 = m0,
      C0 = C0,
      backend = constants$kalman_backend
    )

    fitted_mean <- as.numeric(fit$fitted_mean)
    fitted_latent_var <- pmax(vapply(
      seq_len(Tn),
      function(tt) as.numeric(crossprod(H_mat[tt, ], fit$smooth_cov[, , tt] %*% H_mat[tt, ])),
      numeric(1)
    ), 1e-10)

    source_elbo <- rep(0, length(source_names))
    names(source_elbo) <- source_names
    sigma_next <- sigma_by_source
    for (nm in source_names) {
      obs <- as.numeric(source_obs[[nm]])
      ok <- is.finite(obs) & is.finite(fitted_mean) & is.finite(fitted_latent_var)
      n_obs <- sum(ok)

      sigma_shape <- constants$a_sigma + n_obs / 2
      sigma_rate <- constants$b_sigma
      if (n_obs > 0L) {
        resid <- obs[ok] - fitted_mean[ok]
        sigma_rate <- sigma_rate + 0.5 * sum(resid^2 + fitted_latent_var[ok])
      }
      sigma_new <- sigma_rate / max(sigma_shape - 1, 1.01)
      sigma_new <- max(sigma_new, 1e-6)
      sigma_next[[nm]] <- sigma_new
      sigma_shape_final[[nm]] <- sigma_shape
      sigma_rate_final[[nm]] <- sigma_rate

      prior_term <- constants$a_sigma * log(constants$b_sigma) -
        lgamma(constants$a_sigma) -
        (constants$a_sigma + 1) * log(sigma_new) -
        constants$b_sigma / sigma_new
      ll_term <- 0
      if (n_obs > 0L) {
        resid <- obs[ok] - fitted_mean[ok]
        ll_term <- -0.5 * sum(log(2 * pi * sigma_new) + (resid^2 + fitted_latent_var[ok]) / sigma_new)
      }
      source_elbo[[nm]] <- ll_term + prior_term
    }
    sigma_by_source <- sigma_next

    seq_sigma[iter, ] <- as.numeric(sigma_by_source[source_names])
    seq_elbo[iter] <- sum(as.numeric(source_elbo))
    seq_scale[iter, ] <- c(
      sigma_by_source[["usgs"]],
      sigma_by_source[["usgs"]],
      sigma_by_source[["nws"]],
      sigma_by_source[["glofas"]],
      w_hist,
      w_fore,
      constants$df_t,
      constants$df_s1,
      constants$df_s2,
      constants$df_s67,
      constants$df_discrep,
      constants$lambda,
      constants$df_trans,
      constants$df_covs
    )
    if (is.finite(prev_elbo) && is.finite(seq_elbo[iter])) {
      crit_elbo <- abs(seq_elbo[iter] - prev_elbo)
      denom <- max(abs(prev_elbo), 1e-12)
      crit_elbo_rel <- crit_elbo / denom
    } else {
      crit_elbo <- Inf
      crit_elbo_rel <- Inf
    }
    prev_elbo <- seq_elbo[iter]
    iterations_completed <- as.integer(iter)

    state_norm_sq <- suppressWarnings(as.numeric(sum(fit$smooth_mean^2, na.rm = TRUE)))
    if (!is.finite(state_norm_sq)) {
      state_norm_sq <- NA_real_
    }
    cat(
      sprintf(
        "[gamsig_progress] family=ndlm_main p0=NA iter=%d elbo=%s crit_elbo=%s crit_elbo_rel=%s sigma_exp=%s sigma_usgs_exp=%s sigma_nws_exp=%s sigma_glofas_exp=%s gamma_exp=NA state_norm_sq=%s w_hist=%s w_fore=%s df_t=%s df_s1=%s df_s2=%s df_s67=%s df_discrep=%s lambda=%s\n",
        as.integer(iter),
        fmt_iter_num(seq_elbo[iter]),
        fmt_iter_num(crit_elbo),
        fmt_iter_num(crit_elbo_rel),
        fmt_iter_num(sigma_by_source[["usgs"]]),
        fmt_iter_num(sigma_by_source[["usgs"]]),
        fmt_iter_num(sigma_by_source[["nws"]]),
        fmt_iter_num(sigma_by_source[["glofas"]]),
        fmt_iter_num(state_norm_sq),
        fmt_iter_num(w_hist),
        fmt_iter_num(w_fore),
        fmt_iter_num(constants$df_t),
        fmt_iter_num(constants$df_s1),
        fmt_iter_num(constants$df_s2),
        fmt_iter_num(constants$df_s67),
        fmt_iter_num(constants$df_discrep),
        fmt_iter_num(constants$lambda)
      )
    )

    if (ndlm_theory_has_converged(
      iter = iter,
      min_total_iters = min_total_iters,
      crit_elbo = crit_elbo,
      crit_elbo_rel = crit_elbo_rel,
      elbo_tol = elbo_tol,
      elbo_rel_tol = elbo_rel_tol
    )) {
      converged <- TRUE
      convergence_reason <- "all_convergence_criteria_met"
      break
    }
  }

  if (is.null(fit)) {
    stop("ndlm theory VB failed to initialize", call. = FALSE)
  }
  if (iterations_completed < 1L) {
    iterations_completed <- max_iter
  }
  seq_sigma <- seq_sigma[seq_len(iterations_completed), , drop = FALSE]
  seq_elbo <- seq_elbo[seq_len(iterations_completed)]
  seq_scale <- seq_scale[seq_len(iterations_completed), , drop = FALSE]

  exps <- rbind(fit$fitted_mean, fit$fitted_mean)
  rownames(exps) <- c("median", "mean")
  vars <- rbind(fit$fitted_var, fit$fitted_var)
  exps2 <- exps^2 + vars

  pick_fit_vec <- function(name, fallback) {
    val <- fit[[name]]
    if (is.null(val)) {
      return(as.numeric(fallback))
    }
    out <- as.numeric(val)
    if (length(out) != length(fallback)) {
      return(as.numeric(fallback))
    }
    out
  }
  y_obs <- as.numeric(inputs$y)
  y_pred <- pick_fit_vec("predicted_mean", fit$fitted_mean)
  y_filt <- pick_fit_vec("filtered_mean", fit$fitted_mean)
  y_smooth <- pick_fit_vec("smoothed_mean", fit$fitted_mean)
  v_pred <- pmax(pick_fit_vec("predicted_var", fit$fitted_var), 1e-10)
  v_filt <- pmax(pick_fit_vec("filtered_var", fit$fitted_var), 1e-10)
  v_smooth <- pmax(pick_fit_vec("smoothed_var", fit$fitted_var), 1e-10)
  fit_diagnostics <- list(
    y_observed = y_obs,
    y_assim_hist_pseudo = hist_assim$y,
    R_assim_hist_pseudo = hist_assim$R_vec,
    n_sources_assim_hist = hist_assim$n_sources,
    n_sources_assim_hist_mean = mean(hist_assim$n_sources),
    y_predicted_one_step = y_pred,
    y_filtered = y_filt,
    y_smoothed = y_smooth,
    var_predicted_one_step = v_pred,
    var_filtered = v_filt,
    var_smoothed = v_smooth,
    residual_one_step = y_obs - y_pred,
    residual_filtered = y_obs - y_filt,
    residual_smoothed = y_obs - y_smooth,
    residual_source_usgs = as.numeric(source_obs$usgs) - y_smooth,
    residual_source_nws = as.numeric(source_obs$nws) - y_smooth,
    residual_source_glofas = as.numeric(source_obs$glofas) - y_smooth
  )

  nws_std <- ndlm_theory_standardize(inputs$forecast$nws)
  glofas_std <- ndlm_theory_standardize(inputs$forecast$glofas)

  base_hist <- fit$smooth_mean[8:14, Tn]
  sm_ens_1 <- matrix(0, nrow = 7L, ncol = K_overlap)
  sm_ens_1[1, ] <- nws_std[seq_len(K_overlap)]
  sm_ens_1[2, ] <- glofas_std[seq_len(K_overlap)]
  if (K_overlap > 0L) {
    decay_1 <- matrix(constants$lambda ^ (seq_len(K_overlap) - 1L), nrow = 1L, ncol = K_overlap)
    sm_ens_1[3:7, ] <- matrix(base_hist[3:7], nrow = 5L, ncol = K_overlap) * matrix(rep(decay_1, 5L), nrow = 5L)
  }

  sm_ens_2 <- matrix(0, nrow = 7L, ncol = K_tail)
  bridge_value <- 0
  inactive_row <- integer(0)
  if (K_tail > 0L) {
    if (identical(ragged$extension_source, "nws")) {
      tail_idx <- seq.int(K_overlap + 1L, ragged$K_vec[["nws"]])
      sm_ens_2[1, ] <- nws_std[tail_idx]
      bridge_value <- as.numeric(glofas_std[K_overlap])
      inactive_row <- 2L
    } else {
      tail_idx <- seq.int(K_overlap + 1L, ragged$K_vec[["glofas"]])
      sm_ens_2[1, ] <- glofas_std[tail_idx]
      bridge_value <- as.numeric(nws_std[K_overlap])
      inactive_row <- 2L
    }
    if (!is.finite(bridge_value)) bridge_value <- 0
    sm_ens_2[2, ] <- rep(bridge_value, K_tail)
    decay_2 <- matrix(constants$lambda ^ (seq.int(K_overlap + 1L, K_max) - 1L), nrow = 1L, ncol = K_tail)
    sm_ens_2[3:7, ] <- matrix(base_hist[3:7], nrow = 5L, ncol = K_tail) * matrix(rep(decay_2, 5L), nrow = 5L)
  }

  base_fore_cov <- fit$smooth_cov[8:14, 8:14, Tn, drop = TRUE]
  sC_ens_1 <- ndlm_theory_alloc_segment_cov(
    k_len = K_overlap,
    constants = constants,
    base_cov = base_fore_cov,
    inactive_row = integer(0),
    start_k = 1L
  )
  sC_ens_2 <- ndlm_theory_alloc_segment_cov(
    k_len = K_tail,
    constants = constants,
    base_cov = if (K_overlap > 0L) sC_ens_1[, , K_overlap, drop = TRUE] else base_fore_cov,
    inactive_row = inactive_row,
    start_k = K_overlap + 1L
  )
  cov_diag <- ndlm_theory_collect_covariance_diagnostics(
    fit_sC = fit$smooth_cov,
    sC_ens_1 = sC_ens_1,
    sC_ens_2 = sC_ens_2
  )

  samp_theta_retro <- ndlm_theory_state_draws(
    sm = fit$smooth_mean,
    sC = fit$smooth_cov,
    n_draws = constants$n_draws,
    seed = constants$seed + 11L
  )

  set.seed(constants$seed + 22L)
  samp_theta_ens <- vector("list", 2)
  for (j in 1:2) {
    mu <- if (j == 1) sm_ens_1 else sm_ens_2
    Sig <- if (j == 1) sC_ens_1 else sC_ens_2
    k_j <- suppressWarnings(as.integer(ncol(mu)))
    if (!is.finite(k_j) || k_j < 0L) k_j <- 0L
    arr <- array(0, dim = c(7L, k_j, constants$n_draws))
    for (k in seq_len(k_j)) {
      L <- ndlm_theory_safe_chol(Sig[, , k])
      Z <- matrix(stats::rnorm(7 * constants$n_draws), nrow = 7)
      arr[, k, ] <- mu[, k] + L %*% Z
    }
    samp_theta_ens[[j]] <- list(samp_theta = arr)
  }

  set.seed(constants$seed + 33L)
  samp_sigma <- matrix(NA_real_, nrow = length(source_names), ncol = constants$n_draws)
  rownames(samp_sigma) <- source_names
  for (j in seq_along(source_names)) {
    nm <- source_names[[j]]
    shp <- sigma_shape_final[[nm]]
    rte <- sigma_rate_final[[nm]]
    if (!is.finite(shp) || shp <= 0) shp <- constants$a_sigma
    if (!is.finite(rte) || rte <= 0) rte <- constants$b_sigma
    samp_sigma[j, ] <- 1 / stats::rgamma(constants$n_draws, shape = shp, rate = rte)
  }

  standard_forecast_errors <- rep(NA_real_, K_max)
  standard_forecast_errors[seq_len(K_overlap)] <- inputs$forecast$nws[seq_len(K_overlap)] - inputs$forecast$glofas[seq_len(K_overlap)]
  if (K_tail > 0L) {
    if (identical(ragged$extension_source, "nws")) {
      tail_idx <- seq.int(K_overlap + 1L, ragged$K_vec[["nws"]])
      bridge_raw <- as.numeric(inputs$forecast$glofas[K_overlap])
      if (!is.finite(bridge_raw)) bridge_raw <- 0
      standard_forecast_errors[seq.int(K_overlap + 1L, K_max)] <- inputs$forecast$nws[tail_idx] - bridge_raw
    } else {
      tail_idx <- seq.int(K_overlap + 1L, ragged$K_vec[["glofas"]])
      bridge_raw <- as.numeric(inputs$forecast$nws[K_overlap])
      if (!is.finite(bridge_raw)) bridge_raw <- 0
      standard_forecast_errors[seq.int(K_overlap + 1L, K_max)] <- bridge_raw - inputs$forecast$glofas[tail_idx]
    }
  }
  standard_forecast_errors[!is.finite(standard_forecast_errors)] <- 0
  standard_forecast_errors <- matrix(standard_forecast_errors, nrow = 1L)

  active_set_by_lead <- data.frame(
    lead = seq_len(K_max),
    active_nws = as.integer(seq_len(K_max) <= ragged$K_vec[["nws"]]),
    active_glofas = as.integer(seq_len(K_max) <= ragged$K_vec[["glofas"]]),
    active_count = as.integer(vapply(ragged$active_sources, length, integer(1))),
    stringsAsFactors = FALSE
  )
  state_dim_by_lead <- data.frame(
    lead = seq_len(K_max),
    state_dim = as.integer(7L * active_set_by_lead$active_count),
    stringsAsFactors = FALSE
  )

  new_theta <- list(
    sm = fit$smooth_mean,
    sC = fit$smooth_cov,
    exps = exps,
    exps2 = exps2,
    vars = vars,
    sm_ens = list(sm_ens_1, sm_ens_2),
    sC_ens = list(sC_ens_1, sC_ens_2),
    standard_forecast_errors = standard_forecast_errors,
    forecast_horizon = list(
      K_vec = ragged$K_vec,
      K_overlap = ragged$K_overlap,
      K_max = ragged$K_max,
      segment_lengths = ragged$segment_lengths,
      extension_source = ragged$extension_source,
      bridge_source = ragged$bridge_source
    )
  )

  list(
    new_theta = new_theta,
    samp_theta = list(samp_theta = samp_theta_retro),
    samp_theta_ens = samp_theta_ens,
    samp_sigma = samp_sigma,
    seq_sigma = seq_sigma,
    seq_scale = seq_scale,
    seq_elbo = seq_elbo,
    delta = c(diff(seq_elbo), 0),
    iterations_completed = iterations_completed,
    max_iter = max_iter,
    converged = converged,
    convergence_reason = convergence_reason,
    convergence_metrics = c(
      crit_elbo = suppressWarnings(as.numeric(crit_elbo)),
      crit_elbo_rel = suppressWarnings(as.numeric(crit_elbo_rel)),
      elbo_tol = elbo_tol,
      elbo_rel_tol = elbo_rel_tol
    ),
    sigma = as.numeric(sigma_by_source[["usgs"]]),
    sigma_by_source = sigma_by_source[source_names],
    sigma_mean = mean(as.numeric(sigma_by_source[source_names])),
    w_hist = w_hist,
    w_fore = w_fore,
    discount_factors = c(
      df_t = constants$df_t,
      df_s1 = constants$df_s1,
      df_s2 = constants$df_s2,
      df_s67 = constants$df_s67,
      df_discrep = constants$df_discrep,
      lambda = constants$lambda,
      df_trans = constants$df_trans,
      df_covs = constants$df_covs
    ),
    K = K_max,
    K_overlap = K_overlap,
    K_max = K_max,
    K_vec = ragged$K_vec,
    segment_lengths = ragged$segment_lengths,
    extension_source = ragged$extension_source,
    bridge_source = ragged$bridge_source,
    active_set_by_lead = active_set_by_lead,
    state_dim_by_lead = state_dim_by_lead,
    covariance_diagnostics = cov_diag,
    fit_diagnostics = fit_diagnostics,
    K_cap = inputs$forecast$K_cap,
    nws_len = inputs$forecast$nws_len,
    glofas_len = inputs$forecast$glofas_len,
    T = Tn
  )
}
