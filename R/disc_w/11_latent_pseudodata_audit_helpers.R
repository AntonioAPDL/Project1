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
  left_tail <- is.finite(z) & z < -37
  mills[left_tail] <- -z[left_tail] + 1 / pmax(-z[left_tail], 1e-12)
  right_tail <- is.finite(z) & z > 37
  mills[right_tail] <- 0
  mills[!is.finite(mills)] <- 0
  mean <- mu + sig * mills
  mean[!is.finite(mean)] <- 0
  mean <- pmax(mean, 0)
  variance <- sig2 * (1 - z * mills - mills^2)
  variance[!is.finite(variance) | variance < 0] <- 0
  second <- variance + mean^2
  entropy <- 0.5 * log(2 * pi * exp(1) * sig2) +
    stats::pnorm(z, log.p = TRUE) -
    0.5 * z * mills
  bad_entropy <- !is.finite(entropy)
  entropy[bad_entropy] <- 0.5 * log(2 * pi * exp(1) * sig2[bad_entropy])
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
  active_entropy <- moments$entropy

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

disc_w_audit_Kprime_over_K_half <- function(x) {
  x <- as.numeric(x)
  x[!is.finite(x) | x <= 0] <- 1e-12
  out <- rep(NA_real_, length(x))
  large <- x > 50
  out[large] <- 1 / (2 * x[large])
  if (any(!large)) {
    z <- x[!large]
    out[!large] <- expint::expint_E1(2 * z) * exp(2 * z)
  }
  out[!is.finite(out)] <- 0
  out
}

disc_w_audit_gig_entropy_active <- function(psi, chi) {
  psi <- pmax(as.numeric(psi), 1e-300)
  chi <- pmax(as.numeric(chi), 1e-300)
  s.ab <- sqrt(psi * chi)
  log_k_half <- 0.5 * (log(pi) - log(2 * s.ab)) - s.ab
  out <- 0.5 * log(chi / psi) + log(2) + log_k_half +
    0.5 * disc_w_audit_Kprime_over_K_half(s.ab) + s.ab + 0.5
  out[!is.finite(out)] <- 0
  out
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

  E.uts <- sqrt(u.chi / u.psi) + 1 / u.psi
  E.inv.uts <- sqrt(u.psi / u.chi)
  E.uts[!is.finite(E.uts)] <- 1e-10
  E.inv.uts[!is.finite(E.inv.uts)] <- 1e-10
  E.uts <- pmax(E.uts, 1e-10)
  E.inv.uts <- pmax(E.inv.uts, 1e-10)

  E.log.uts <- sum(disc_w_audit_Kprime_over_K_half(s.ab) - 0.5 * log(u.psi / u.chi))
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

disc_w_audit_transform_raw_cms <- function(x, scale) {
  x <- as.numeric(x)
  if (identical(scale, "raw_cms")) return(x)
  if (identical(scale, "log1p_cms")) return(log1p(x))
  if (identical(scale, "log_log1p_cms")) return(log(log1p(x)))
  stop(sprintf("Unsupported audit scale: %s", scale), call. = FALSE)
}

disc_w_audit_scale_sensitivity_fixture <- function(
  raw_y = c(0, 1e-6, 0.001, 0.1, 1, 10, 100, 1000),
  raw_exps = NULL,
  scales = c("log1p_cms", "log_log1p_cms"),
  exps2_variance = 0.05
) {
  raw_y <- as.numeric(raw_y)
  if (is.null(raw_exps)) {
    raw_exps <- pmax(raw_y * 0.92 + 0.02, 0)
  }
  raw_exps <- as.numeric(raw_exps)
  if (length(raw_exps) != length(raw_y)) {
    stop("raw_exps must have the same length as raw_y", call. = FALSE)
  }

  rows <- list()
  for (scale in scales) {
    y_scaled <- suppressWarnings(disc_w_audit_transform_raw_cms(raw_y, scale))
    exps_scaled <- suppressWarnings(disc_w_audit_transform_raw_cms(raw_exps, scale))
    finite_pair <- is.finite(y_scaled) & is.finite(exps_scaled)

    base <- data.frame(
      scale = scale,
      raw_y = raw_y,
      raw_exps = raw_exps,
      y_scaled = y_scaled,
      exps_scaled = exps_scaled,
      residual = y_scaled - exps_scaled,
      residual2 = (y_scaled - exps_scaled)^2,
      valid_scaled = finite_pair
    )

    base$sts_mu <- NA_real_
    base$E_sts <- NA_real_
    base$E_sts2 <- NA_real_
    base$u_chi <- NA_real_
    base$E_uts <- NA_real_
    base$E_inv_uts <- NA_real_
    base$pseudo_offset <- NA_real_
    base$pseudo_variance <- NA_real_

    if (any(finite_pair)) {
      idx <- which(finite_pair)
      n <- length(idx)
      sts <- disc_w_audit_update_sts(
        y = y_scaled[idx],
        exps = exps_scaled[idx],
        inv_uts = rep(1, n),
        c2_invb_absgam2_sigma = rep(0.55, n),
        c_invb_absgam = rep(0.25, n),
        c_a_invb_absgam = rep(0.05, n)
      )
      uts <- disc_w_audit_update_uts(
        y = y_scaled[idx],
        exps = exps_scaled[idx],
        exps2 = exps_scaled[idx]^2 + exps2_variance,
        sts = sts$E.sts,
        sts2 = sts$E.sts2,
        inv_sigma = rep(1, n),
        a2_invb_inv_sigma = rep(0.35, n),
        invb_inv_sigma = rep(1, n),
        c_invb_absgam = rep(0.25, n),
        c2_invb_absgam2_sigma = rep(0.55, n)
      )
      pseudo <- disc_w_audit_pseudodata(
        E_c_invb_absgam = rep(0.25, n),
        E_a_invb_inv_sigma = rep(0.35, n),
        E_invb_inv_sigma = rep(1, n),
        E_sts = sts$E.sts,
        E_inv_uts = uts$E.inv.uts
      )

      base$sts_mu[idx] <- sts$sts.mu
      base$E_sts[idx] <- sts$E.sts
      base$E_sts2[idx] <- sts$E.sts2
      base$u_chi[idx] <- uts$uts.chi
      base$E_uts[idx] <- uts$E.uts
      base$E_inv_uts[idx] <- uts$E.inv.uts
      base$pseudo_offset[idx] <- pseudo$offset
      base$pseudo_variance[idx] <- pseudo$variance
    }
    rows[[length(rows) + 1L]] <- base
  }

  do.call(rbind, rows)
}

disc_w_audit_extract_diag_values <- function(x) {
  if (is.list(x) && !is.data.frame(x)) {
    return(unlist(lapply(x, disc_w_audit_extract_diag_values), use.names = FALSE))
  }
  d <- dim(x)
  if (!is.null(d) && length(d) == 3L && d[[1L]] == d[[2L]]) {
    return(unlist(lapply(seq_len(d[[3L]]), function(i) diag(x[, , i, drop = TRUE])), use.names = FALSE))
  }
  as.numeric(x)
}

disc_w_audit_guard_summary <- function(values, quantity, block, iter = NA_integer_, abs_cap = Inf, positive_required = FALSE) {
  raw <- as.numeric(values)
  finite <- raw[is.finite(raw)]
  cap_exceed <- if (is.finite(abs_cap)) sum(abs(finite) > abs_cap) else 0L
  nonpositive <- if (isTRUE(positive_required)) sum(finite <= 0) else 0L
  status <- "ok"
  if (length(finite) < length(raw)) {
    status <- "nonfinite"
  } else if (nonpositive > 0L) {
    status <- "nonpositive"
  } else if (cap_exceed > 0L) {
    status <- "cap_exceeded"
  }
  data.frame(
    iter = as.integer(iter),
    quantity = quantity,
    block = block,
    n = length(raw),
    finite_n = length(finite),
    nonfinite_n = length(raw) - length(finite),
    positive_required = isTRUE(positive_required),
    nonpositive_n = as.integer(nonpositive),
    min = if (length(finite)) min(finite) else NA_real_,
    max = if (length(finite)) max(finite) else NA_real_,
    max_abs = if (length(finite)) max(abs(finite)) else NA_real_,
    abs_cap = as.numeric(abs_cap),
    cap_exceed_n = as.integer(cap_exceed),
    status = status
  )
}

disc_w_audit_pseudodata_guard <- function(
  iter = NA_integer_,
  FFF,
  QQQ,
  FFF_forecast = NULL,
  QQQ_forecast = NULL,
  E_sts = NULL,
  E_sts2 = NULL,
  E_uts = NULL,
  E_inv_uts = NULL,
  E_sts_forecast = NULL,
  E_sts2_forecast = NULL,
  E_uts_forecast = NULL,
  E_inv_uts_forecast = NULL,
  fff_abs_cap = 1000,
  qqq_diag_abs_cap = 10000,
  e_s_abs_cap = 1000,
  e_s2_abs_cap = 1e6,
  e_u_abs_cap = 1e6,
  e_inv_u_abs_cap = 5000,
  allow_zero_sts = FALSE
) {
  rows <- list()
  add <- function(values, quantity, block, cap, positive = FALSE, diag_values = FALSE) {
    if (is.null(values)) return(invisible(NULL))
    vals <- if (isTRUE(diag_values)) disc_w_audit_extract_diag_values(values) else as.numeric(unlist(values, use.names = FALSE))
    rows[[length(rows) + 1L]] <<- disc_w_audit_guard_summary(
      vals,
      quantity = quantity,
      block = block,
      iter = iter,
      abs_cap = cap,
      positive_required = positive
    )
    invisible(NULL)
  }

  add(FFF, "FFF", "history", fff_abs_cap)
  add(QQQ, "QQQ_diag", "history", qqq_diag_abs_cap, positive = TRUE, diag_values = TRUE)
  add(FFF_forecast, "FFF_forecast", "forecast", fff_abs_cap)
  add(QQQ_forecast, "QQQ_forecast_diag", "forecast", qqq_diag_abs_cap, positive = TRUE, diag_values = TRUE)
  sts_positive_required <- !isTRUE(allow_zero_sts)
  add(E_sts, "E_sts", "history", e_s_abs_cap, positive = sts_positive_required)
  add(E_sts2, "E_sts2", "history", e_s2_abs_cap, positive = sts_positive_required)
  add(E_uts, "E_uts", "history", e_u_abs_cap, positive = TRUE)
  add(E_inv_uts, "E_inv_uts", "history", e_inv_u_abs_cap, positive = TRUE)
  add(E_sts_forecast, "E_sts", "forecast", e_s_abs_cap, positive = sts_positive_required)
  add(E_sts2_forecast, "E_sts2", "forecast", e_s2_abs_cap, positive = sts_positive_required)
  add(E_uts_forecast, "E_uts", "forecast", e_u_abs_cap, positive = TRUE)
  add(E_inv_uts_forecast, "E_inv_uts", "forecast", e_inv_u_abs_cap, positive = TRUE)

  do.call(rbind, rows)
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
