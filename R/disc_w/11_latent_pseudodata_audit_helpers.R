# Audit-only helpers for the multivariate exDQLM keep workflow.
#
# These functions intentionally mirror the active formulas in
# DISC_Optimal_Synth_Ranges_W_transfer_forecast.r without being sourced by the
# production runner. They give deterministic unit tests and report scripts a
# small surface for checking latent moments, pseudo-data, and keep dimensions.

disc_w_audit_truncnorm_pos_moments <- function(mu, sig2) {
  mu <- as.numeric(mu)
  sig2 <- as.numeric(sig2)
  sig <- sqrt(pmax(sig2, 1e-300))
  z <- mu / sig
  mills <- exp(stats::dnorm(z, log = TRUE) - stats::pnorm(z, log.p = TRUE))
  mean <- mu + sig * mills
  variance <- sig2 * (1 - z * mills - mills^2)
  second <- variance + mean^2
  entropy <- 0.5 * log(2 * pi * exp(1) * sig2) +
    stats::pnorm(z, log.p = TRUE) -
    0.5 * z * mills
  list(mean = mean, variance = variance, second = second, entropy = entropy)
}

disc_w_audit_update_sts <- function(
  y,
  exps,
  inv_uts,
  c2_invb_absgam2_sigma,
  c_invb_absgam,
  c_a_invb_absgam,
  al_mode = FALSE
) {
  n <- length(y)
  if (isTRUE(al_mode)) {
    z <- rep(0, n)
    return(list(
      sts.sig2 = rep(1, n),
      sts.mu = z,
      E.sts = z,
      E.sts2 = z,
      active_tot.entrop = 0,
      canonical_tot.entrop = 0
    ))
  }

  inv_uts <- pmax(as.numeric(inv_uts), 1e-10)
  denom <- pmax(1 + c2_invb_absgam2_sigma * inv_uts, 1e-10)
  s.sig2 <- 1 / denom
  s.sig <- sqrt(pmax(s.sig2, 1e-10))
  s.mu <- s.sig2 * (c_invb_absgam * (y - exps) * inv_uts - c_a_invb_absgam)

  moments <- disc_w_audit_truncnorm_pos_moments(s.mu, s.sig2)
  active_entropy <- 0.5 * log2(2 * pi * exp(1) * s.sig2) - 1

  list(
    sts.sig2 = s.sig2,
    sts.mu = s.mu,
    E.sts = moments$mean,
    E.sts2 = moments$second,
    active_tot.entrop = sum(active_entropy),
    canonical_tot.entrop = sum(moments$entropy),
    active_entropy = active_entropy,
    canonical_entropy = moments$entropy
  )
}

disc_w_audit_Kprime_half <- function(x) {
  sqrt(pi / (2 * x)) * expint::expint_E1(2 * x) * exp(x)
}

disc_w_audit_gig_entropy_active <- function(psi, chi) {
  nu <- 0.5
  s.ab <- sqrt(psi * chi)
  K1 <- besselK(s.ab, nu)
  K2 <- besselK(s.ab, nu + 1)
  K3 <- besselK(s.ab, nu - 1)
  0.5 * log(chi / psi) + log(2 * K1) -
    (nu - 1) * disc_w_audit_Kprime_half(s.ab) / K1 +
    s.ab / (2 * K1) * (K2 + K3)
}

disc_w_audit_update_uts <- function(
  y,
  exps,
  exps2,
  sts,
  sts2,
  inv_sigma,
  a2_invb_inv_sigma,
  invb_inv_sigma,
  c_invb_absgam,
  c2_invb_absgam2_sigma
) {
  u.lambda <- 0.5
  u.psi <- as.numeric(a2_invb_inv_sigma + 2 * inv_sigma)
  u.chi <- as.numeric(
    invb_inv_sigma * (y^2 - 2 * y * exps + exps2) -
      2 * c_invb_absgam * sts * (y - exps) +
      c2_invb_absgam2_sigma * sts2
  )

  u.psi[!is.finite(u.psi) | u.psi <= 0] <- 1e-6
  u.chi[!is.finite(u.chi) | u.chi <= 0] <- 1e-6

  s.ab <- sqrt(pmax(u.psi * u.chi, 1e-12))
  K0 <- besselK(s.ab, u.lambda)
  K1 <- besselK(s.ab, u.lambda + 1)
  ratio <- K1 / K0
  ratio[!is.finite(ratio)] <- 1

  E.uts <- sqrt(u.chi / u.psi) * ratio
  E.inv.uts <- sqrt(u.psi / u.chi) * ratio - 2 * u.lambda / u.chi
  E.uts[!is.finite(E.uts)] <- 1e-10
  E.inv.uts[!is.finite(E.inv.uts)] <- 1e-10
  E.uts <- pmax(E.uts, 1e-10)
  E.inv.uts <- pmax(E.inv.uts, 1e-10)

  K_lambda <- besselK(s.ab, u.lambda)
  K_lambda[!is.finite(K_lambda) | K_lambda <= 0] <- 1e-12
  kp <- disc_w_audit_Kprime_half(s.ab)
  kp[!is.finite(kp)] <- 0

  E.log.uts <- sum(kp / K_lambda - 0.5 * log(u.psi / u.chi))
  if (!is.finite(E.log.uts)) E.log.uts <- 0
  tot.ent <- sum(disc_w_audit_gig_entropy_active(u.psi, u.chi))
  if (!is.finite(tot.ent)) tot.ent <- 0

  list(
    uts.lambda = u.lambda,
    uts.psi = u.psi,
    uts.chi = u.chi,
    E.uts = E.uts,
    E.inv.uts = E.inv.uts,
    E.log.uts = E.log.uts,
    tot.entrop = tot.ent
  )
}

disc_w_audit_gig_moment <- function(lambda, chi, psi, r) {
  z <- sqrt(chi * psi)
  (chi / psi)^(r / 2) * besselK(z, lambda + r) / besselK(z, lambda)
}

disc_w_audit_pseudodata <- function(
  E_c_invb_absgam,
  E_a_invb_inv_sigma,
  E_invb_inv_sigma,
  E_sts,
  E_inv_uts
) {
  E_inv_uts <- pmax(as.numeric(E_inv_uts), 1e-300)
  E_invb_inv_sigma <- pmax(as.numeric(E_invb_inv_sigma), 1e-300)
  offset <- (
    as.numeric(E_c_invb_absgam) * as.numeric(E_sts) +
      as.numeric(E_a_invb_inv_sigma) / E_inv_uts
  ) / E_invb_inv_sigma
  variance <- 1 / (E_invb_inv_sigma * E_inv_uts)
  weight <- 1 / variance
  list(offset = offset, variance = variance, weight = weight)
}

disc_w_audit_keep_dimension_table <- function(p, J, ppx, ranges, num_mem = NULL) {
  if (is.null(num_mem)) {
    num_mem <- rep(NA_integer_, J)
  }
  ranges_per_local <- if (J > 1) ranges - c(ranges[2:J], 0) else ranges
  r_vec_local <- rev(ranges_per_local)
  seg_start_local <- cumsum(c(1, head(r_vec_local, -1)))
  out <- lapply(seq_len(J), function(seg) {
    active_sources <- J - seg + 1L
    core_dim <- p * (active_sources + 1L)
    state_dim <- core_dim + ppx
    obs_dim <- if (all(is.finite(num_mem))) sum(num_mem[seq_len(active_sources)]) else NA_real_
    data.frame(
      segment_index = seg,
      active_sources = active_sources,
      segment_horizon = r_vec_local[seg],
      segment_start = seg_start_local[seg],
      core_state_dim = core_dim,
      transfer_dim = ppx,
      keep_state_dim = state_dim,
      forecast_series = active_sources,
      forecast_member_obs_dim = obs_dim
    )
  })
  do.call(rbind, out)
}
