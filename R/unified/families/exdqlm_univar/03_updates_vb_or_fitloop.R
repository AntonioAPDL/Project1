univar_theory_log_joint_sigma_gamma <- function(
  sigma,
  gamma,
  y,
  eta,
  Ev,
  Es,
  p0,
  constants
) {
  if (!is.finite(sigma) || sigma <= 0 || !is.finite(gamma)) return(-Inf)

  bounds <- univar_theory_gamma_bounds(p0)
  if (gamma <= bounds["L"] || gamma >= bounds["U"]) return(-Inf)

  map <- tryCatch(univar_theory_exal_map(p0, gamma), error = function(e) NULL)
  if (is.null(map)) return(-Inf)

  v <- pmax(Ev, 1e-10)
  s <- pmax(Es, 0)
  resid <- y - eta - map$A * v - map$C * sigma * abs(gamma) * s

  ll <- -0.5 * sum(log(sigma * map$B * v) + resid^2 / (sigma * map$B * v))

  a_sigma <- constants$a_sigma
  b_sigma <- constants$b_sigma
  lp_sigma <- a_sigma * log(b_sigma) - lgamma(a_sigma) - (a_sigma + 1) * log(sigma) - b_sigma / sigma

  m_gamma <- constants$m_gamma
  s_gamma <- constants$s_gamma
  nu_gamma <- constants$nu_gamma
  z <- (gamma - m_gamma) / s_gamma
  Z <- stats::pt((bounds["U"] - m_gamma) / s_gamma, df = nu_gamma) -
    stats::pt((bounds["L"] - m_gamma) / s_gamma, df = nu_gamma)
  lp_gamma <- stats::dt(z, df = nu_gamma, log = TRUE) - log(s_gamma) - log(max(Z, 1e-12))

  ll + lp_sigma + lp_gamma
}

univar_theory_run_cavi <- function(inputs, constants) {
  set.seed(constants$seed)

  y <- as.numeric(inputs$y)
  X <- as.matrix(inputs$X)
  if (!all(is.finite(y))) {
    stop("univar theory run received non-finite y", call. = FALSE)
  }
  if (nrow(X) != length(y)) {
    stop("univar theory covariate rows must match y length", call. = FALSE)
  }

  p0 <- constants$p0
  bounds <- univar_theory_gamma_bounds(p0)
  gamma <- max(min(0, bounds["U"] - 1e-4), bounds["L"] + 1e-4)
  sigma <- max(stats::sd(y), 0.1)

  Tn <- length(y)
  d_act <- constants$active_dim
  F_mat <- cbind(1, X[, seq_len(d_act - 1), drop = FALSE])
  m0 <- rep(0, d_act)
  C0 <- diag(c(5, rep(1, d_act - 1)), d_act)
  q_diag <- c(0.05, rep(0.01, d_act - 1))

  Ev <- rep(1, Tn)
  E1v <- rep(1, Tn)
  Es <- rep(sqrt(2 / pi), Tn)
  elbo <- rep(NA_real_, constants$n_iter)

  smoother <- NULL
  for (iter in seq_len(constants$n_iter)) {
    map <- univar_theory_exal_map(p0, gamma)
    y_tilde <- y - map$C * sigma * abs(gamma) * Es - map$A * Ev
    R_vec <- pmax(sigma * map$B * Ev, 1e-8)
    smoother <- univar_theory_kalman_smoother(y_tilde, F_mat, R_vec, q_diag, m0, C0)
    eta <- smoother$fitted_mean

    r <- y - eta - map$C * sigma * abs(gamma) * Es
    chi <- pmax(r^2 / (sigma * map$B), 1e-10)
    psi <- pmax((map$A^2) / (sigma * map$B) + 2 / sigma, 1e-10)

    Ev_new <- univar_theory_gig_moment(lambda = 0.5, chi = chi, psi = psi, r = 1)
    E1v_new <- univar_theory_gig_moment(lambda = 0.5, chi = chi, psi = psi, r = -1)
    Ev_new[!is.finite(Ev_new)] <- Ev[!is.finite(Ev_new)]
    E1v_new[!is.finite(E1v_new)] <- E1v[!is.finite(E1v_new)]
    Ev <- pmax(Ev_new, 1e-8)
    E1v <- pmax(E1v_new, 1e-8)

    y_circ <- y - eta - map$A * Ev
    Vs <- 1 / (1 + (map$C^2) * sigma * gamma^2 / (map$B * Ev))
    ms <- Vs * (map$C * abs(gamma) / (map$B * Ev)) * y_circ
    tm <- univar_theory_truncnorm_pos_moments(ms, Vs)
    Es <- pmax(tm$mean, 1e-8)

    gamma_obj <- function(g) {
      -univar_theory_log_joint_sigma_gamma(
        sigma = sigma,
        gamma = g,
        y = y,
        eta = eta,
        Ev = Ev,
        Es = Es,
        p0 = p0,
        constants = constants
      )
    }
    gamma_opt <- stats::optimize(gamma_obj, interval = c(bounds["L"] + 1e-5, bounds["U"] - 1e-5))
    gamma <- max(min(gamma_opt$minimum, bounds["U"] - 1e-6), bounds["L"] + 1e-6)

    sigma_obj <- function(log_sigma) {
      -univar_theory_log_joint_sigma_gamma(
        sigma = exp(log_sigma),
        gamma = gamma,
        y = y,
        eta = eta,
        Ev = Ev,
        Es = Es,
        p0 = p0,
        constants = constants
      )
    }
    sigma_opt <- stats::optimize(sigma_obj, interval = log(c(1e-5, 1e3)))
    sigma <- max(exp(sigma_opt$minimum), 1e-8)

    elbo[iter] <- univar_theory_log_joint_sigma_gamma(
      sigma = sigma,
      gamma = gamma,
      y = y,
      eta = eta,
      Ev = Ev,
      Es = Es,
      p0 = p0,
      constants = constants
    )
  }

  if (is.null(smoother)) {
    stop("univar theory smoother failed to initialize", call. = FALSE)
  }

  list(
    smooth_mean = smoother$smooth_mean,
    smooth_cov = smoother$smooth_cov,
    fitted_mean = smoother$fitted_mean,
    fitted_var = smoother$fitted_var,
    sigma = sigma,
    gamma = gamma,
    Ev = Ev,
    E1v = E1v,
    Es = Es,
    elbo = elbo,
    p0 = p0,
    bounds = bounds
  )
}
