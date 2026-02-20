ndlm_theory_state_draws <- function(sm, sC, n_draws, seed) {
  set.seed(seed)
  d <- nrow(sm)
  Tn <- ncol(sm)
  out <- array(0, dim = c(d, Tn, n_draws))
  for (t in seq_len(Tn)) {
    Sigma <- as.matrix(sC[, , t])
    Sigma <- (Sigma + t(Sigma)) / 2 + diag(1e-8, d)
    L <- tryCatch(chol(Sigma), error = function(e) chol(Sigma + diag(1e-6, d)))
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
  K <- inputs$forecast$K

  H_mat <- matrix(0, nrow = Tn, ncol = d)
  H_mat[, 1] <- 1
  H_mat[, 2:6] <- inputs$X[, 1:5, drop = FALSE]
  if (Tn >= 2) {
    H_mat[-1, 7] <- diff(inputs$y)
  }
  H_mat[, 8:12] <- inputs$X[, 1:5, drop = FALSE]

  m0 <- rep(0, d)
  C0 <- diag(c(5, rep(1, d - 1)), d)

  sigma <- max(stats::sd(inputs$y), 0.1)
  w_hist <- 0.05
  w_fore <- 0.05

  seq_sigma <- rep(NA_real_, constants$n_iter)
  seq_elbo <- rep(NA_real_, constants$n_iter)
  prev_elbo <- NA_real_
  crit_elbo <- Inf
  fit <- NULL

  for (iter in seq_len(constants$n_iter)) {
    q_diag <- c(rep(w_hist, 7L), rep(w_fore, 7L), rep(1e-4, d - 14L))
    R_vec <- rep(sigma, Tn)

    fit <- ndlm_theory_kalman_smoother(
      y = inputs$y,
      H_mat = H_mat,
      R_vec = R_vec,
      q_diag = q_diag,
      m0 = m0,
      C0 = C0
    )

    resid <- inputs$y - fit$fitted_mean
    sigma_shape <- constants$a_sigma + Tn / 2
    sigma_rate <- constants$b_sigma + 0.5 * sum(resid^2 + fit$fitted_var)
    sigma <- sigma_rate / max(sigma_shape - 1, 1.01)
    sigma <- max(sigma, 1e-6)

    hist_diff <- diff(t(fit$smooth_mean[1:7, , drop = FALSE]))
    fore_diff <- diff(t(fit$smooth_mean[8:14, , drop = FALSE]))

    hist_shape <- constants$a_w_hist + length(hist_diff) / 2
    hist_rate <- constants$b_w_hist + 0.5 * sum(hist_diff^2)
    fore_shape <- constants$a_w_fore + length(fore_diff) / 2
    fore_rate <- constants$b_w_fore + 0.5 * sum(fore_diff^2)

    w_hist <- hist_rate / max(hist_shape - 1, 1.01)
    w_fore <- fore_rate / max(fore_shape - 1, 1.01)
    w_hist <- max(w_hist, 1e-6)
    w_fore <- max(w_fore, 1e-6)

    seq_sigma[iter] <- sigma
    seq_elbo[iter] <- -0.5 * sum(log(2 * pi * sigma) + resid^2 / sigma)
    if (is.finite(prev_elbo) && is.finite(seq_elbo[iter])) {
      crit_elbo <- abs(seq_elbo[iter] - prev_elbo)
    } else {
      crit_elbo <- Inf
    }
    prev_elbo <- seq_elbo[iter]

    state_norm_sq <- suppressWarnings(as.numeric(sum(fit$smooth_mean^2, na.rm = TRUE)))
    if (!is.finite(state_norm_sq)) {
      state_norm_sq <- NA_real_
    }
    cat(
      sprintf(
        "[gamsig_progress] family=ndlm_main p0=NA iter=%d elbo=%s crit_elbo=%s sigma_exp=%s gamma_exp=NA state_norm_sq=%s w_hist=%s w_fore=%s\n",
        as.integer(iter),
        fmt_iter_num(seq_elbo[iter]),
        fmt_iter_num(crit_elbo),
        fmt_iter_num(sigma),
        fmt_iter_num(state_norm_sq),
        fmt_iter_num(w_hist),
        fmt_iter_num(w_fore)
      )
    )
  }

  if (is.null(fit)) {
    stop("ndlm theory VB failed to initialize", call. = FALSE)
  }

  exps <- rbind(fit$fitted_mean, fit$fitted_mean)
  rownames(exps) <- c("median", "mean")
  vars <- rbind(fit$fitted_var, fit$fitted_var)
  exps2 <- exps^2 + vars

  base_hist <- fit$smooth_mean[8:14, Tn]
  sm_ens_1 <- matrix(0, nrow = 7, ncol = K)
  sm_ens_2 <- matrix(0, nrow = 7, ncol = K)
  sm_ens_1[1, ] <- ndlm_theory_standardize(inputs$forecast$nws[, drop = TRUE])
  sm_ens_1[2, ] <- ndlm_theory_standardize(inputs$forecast$glofas[, drop = TRUE])
  sm_ens_1[3:7, ] <- matrix(base_hist[3:7], nrow = 5, ncol = K)

  sm_ens_2[1, ] <- ndlm_theory_standardize(inputs$forecast$glofas[, drop = TRUE])
  sm_ens_2[2, ] <- ndlm_theory_standardize(inputs$forecast$nws[, drop = TRUE])
  sm_ens_2[3:7, ] <- matrix(base_hist[3:7], nrow = 5, ncol = K)

  sC_ens_1 <- array(0, dim = c(7, 7, K))
  sC_ens_2 <- array(0, dim = c(7, 7, K))
  for (k in seq_len(K)) {
    sC_ens_1[, , k] <- diag(w_fore * k + 1e-4, 7)
    sC_ens_2[, , k] <- diag(w_fore * k + 1e-4, 7)
  }

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
    arr <- array(0, dim = c(7, K, constants$n_draws))
    for (k in seq_len(K)) {
      L <- chol(Sig[, , k] + diag(1e-8, 7))
      Z <- matrix(stats::rnorm(7 * constants$n_draws), nrow = 7)
      arr[, k, ] <- mu[, k] + L %*% Z
    }
    samp_theta_ens[[j]] <- list(samp_theta = arr)
  }

  set.seed(constants$seed + 33L)
  samp_sigma <- matrix(1 / stats::rgamma(constants$n_draws, shape = constants$a_sigma + Tn / 2, rate = constants$b_sigma + Tn / 2), nrow = 1)

  standard_forecast_errors <- matrix(
    inputs$forecast$nws - inputs$forecast$glofas,
    nrow = 1
  )

  new_theta <- list(
    sm = fit$smooth_mean,
    sC = fit$smooth_cov,
    exps = exps,
    exps2 = exps2,
    vars = vars,
    sm_ens = list(sm_ens_1, sm_ens_2),
    sC_ens = list(sC_ens_1, sC_ens_2),
    standard_forecast_errors = standard_forecast_errors
  )

  list(
    new_theta = new_theta,
    samp_theta = list(samp_theta = samp_theta_retro),
    samp_theta_ens = samp_theta_ens,
    samp_sigma = samp_sigma,
    seq_sigma = seq_sigma,
    seq_elbo = seq_elbo,
    delta = c(diff(seq_elbo), 0),
    sigma = sigma,
    w_hist = w_hist,
    w_fore = w_fore,
    K = K,
    K_cap = inputs$forecast$K_cap,
    nws_len = inputs$forecast$nws_len,
    glofas_len = inputs$forecast$glofas_len,
    T = Tn
  )
}
