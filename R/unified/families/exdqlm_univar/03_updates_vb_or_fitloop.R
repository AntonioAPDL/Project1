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
  policy <- constants$gamma_sigma_policy
  if (!is.list(policy)) {
    policy <- univar_theory_default_gamma_sigma_policy()
  }

  if (identical(policy$init$mode, "robust")) {
    robust_spread <- suppressWarnings(stats::mad(y, center = stats::median(y), constant = 1.4826, na.rm = TRUE))
    if (!is.finite(robust_spread) || robust_spread <= 0) {
      robust_spread <- suppressWarnings(stats::sd(y))
    }
    if (!is.finite(robust_spread) || robust_spread <= 0) {
      robust_spread <- 0.1
    }
    sigma <- max(policy$init$sigma_floor, policy$init$sigma_scale * robust_spread)
    gamma <- min(max(policy$init$gamma, bounds["L"] + 1e-6), bounds["U"] - 1e-6)
    if (isTRUE(policy$objective_guard$log_failures)) {
      cat(
        sprintf(
          "[gamsig_init] p0=%s mode=robust gamma_seed=%0.6f sigma_seed=%0.6f\n",
          as.character(p0),
          as.numeric(gamma),
          as.numeric(sigma)
        )
      )
    }
  } else {
    gamma <- max(min(0, bounds["U"] - 1e-4), bounds["L"] + 1e-4)
    sigma <- max(stats::sd(y), 0.1)
  }

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

  gamsig_dynamic_freeze_until_iter <- as.integer(policy$warmup_freeze_iters)
  if (!is.finite(gamsig_dynamic_freeze_until_iter) || gamsig_dynamic_freeze_until_iter < 0L) {
    gamsig_dynamic_freeze_until_iter <- 0L
  }
  if (isTRUE(policy$objective_guard$log_failures)) {
    cat(
      sprintf(
        "[gamsig_policy] p0=%s freeze_target=%s warmup_freeze_iters=%d guard_mode=%s guard_refreeze_iters=%d\n",
        as.character(p0),
        policy$freeze_target,
        as.integer(policy$warmup_freeze_iters),
        policy$objective_guard$mode,
        as.integer(policy$guard_refreeze_iters)
      )
    )
  }

  smoother <- NULL
  eta <- rep(0, Tn)
  for (iter in seq_len(constants$n_iter)) {
    iter_int <- as.integer(iter)
    state_frozen_now <- identical(policy$freeze_target, "states") &&
      (gamsig_dynamic_freeze_until_iter > 0L) &&
      (iter_int <= gamsig_dynamic_freeze_until_iter) &&
      (iter_int > 1L)
    if (state_frozen_now && isTRUE(policy$objective_guard$log_failures)) {
      cat(
        sprintf(
          "[gamsig_freeze] p0=%s iter=%d freeze_until_iter=%d target=states\n",
          as.character(p0),
          iter_int,
          as.integer(gamsig_dynamic_freeze_until_iter)
        )
      )
    }

    if (!state_frozen_now) {
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
    }

    gamsig_frozen_now <- identical(policy$freeze_target, "gamma_sigma") &&
      (gamsig_dynamic_freeze_until_iter > 0L) &&
      (iter_int <= gamsig_dynamic_freeze_until_iter)
    if (gamsig_frozen_now && isTRUE(policy$objective_guard$log_failures)) {
      cat(
        sprintf(
          "[gamsig_freeze] p0=%s iter=%d freeze_until_iter=%d target=gamma_sigma\n",
          as.character(p0),
          iter_int,
          as.integer(gamsig_dynamic_freeze_until_iter)
        )
      )
    }

    guard_triggered <- FALSE
    guard_message <- NULL
    guard_eval <- function(obj_raw, context_label, theta_s = NA_real_, theta_g = NA_real_) {
      if (is.finite(obj_raw)) return(obj_raw)

      msg <- sprintf(
        "non-finite dq_transf at p0=%s context=%s iter=%d theta_s=%s theta_g=%s",
        as.character(p0),
        context_label,
        iter_int,
        as.character(theta_s),
        as.character(theta_g)
      )
      if (isTRUE(policy$objective_guard$log_failures)) {
        cat(sprintf("[gamsig_guard] %s\n", msg))
      }
      if (isTRUE(policy$objective_guard$enabled)) {
        guard_triggered <<- TRUE
        guard_message <<- msg
        if (isTRUE(policy$objective_guard$fail_fast)) {
          stop(msg, call. = FALSE)
        }
        return(as.numeric(policy$objective_guard$penalty))
      }
      if (isTRUE(policy$objective_guard$fail_fast)) {
        stop(msg, call. = FALSE)
      }
      Inf
    }

    if (!gamsig_frozen_now) {
      gamma_obj <- function(g) {
        raw <- -univar_theory_log_joint_sigma_gamma(
          sigma = sigma,
          gamma = g,
          y = y,
          eta = eta,
          Ev = Ev,
          Es = Es,
          p0 = p0,
          constants = constants
        )
        guard_eval(raw, context_label = "univar_gamma_opt", theta_s = sigma, theta_g = g)
      }
      gamma_opt <- tryCatch(
        stats::optimize(gamma_obj, interval = c(bounds["L"] + 1e-5, bounds["U"] - 1e-5)),
        error = function(e) e
      )
      if (inherits(gamma_opt, "error")) {
        msg <- sprintf("gamma optimize failed at iter=%d: %s", iter_int, conditionMessage(gamma_opt))
        if (isTRUE(policy$objective_guard$log_failures)) cat(sprintf("[gamsig_guard] %s\n", msg))
        if (isTRUE(policy$objective_guard$enabled)) {
          guard_triggered <- TRUE
          guard_message <- msg
          if (isTRUE(policy$objective_guard$fail_fast)) stop(msg, call. = FALSE)
        } else if (isTRUE(policy$objective_guard$fail_fast)) {
          stop(msg, call. = FALSE)
        }
      } else {
        gamma <- max(min(gamma_opt$minimum, bounds["U"] - 1e-6), bounds["L"] + 1e-6)
      }

      sigma_obj <- function(log_sigma) {
        sigma_candidate <- exp(log_sigma)
        raw <- -univar_theory_log_joint_sigma_gamma(
          sigma = sigma_candidate,
          gamma = gamma,
          y = y,
          eta = eta,
          Ev = Ev,
          Es = Es,
          p0 = p0,
          constants = constants
        )
        guard_eval(raw, context_label = "univar_sigma_opt", theta_s = sigma_candidate, theta_g = gamma)
      }
      sigma_opt <- tryCatch(
        stats::optimize(sigma_obj, interval = log(c(1e-5, 1e3))),
        error = function(e) e
      )
      if (inherits(sigma_opt, "error")) {
        msg <- sprintf("sigma optimize failed at iter=%d: %s", iter_int, conditionMessage(sigma_opt))
        if (isTRUE(policy$objective_guard$log_failures)) cat(sprintf("[gamsig_guard] %s\n", msg))
        if (isTRUE(policy$objective_guard$enabled)) {
          guard_triggered <- TRUE
          guard_message <- msg
          if (isTRUE(policy$objective_guard$fail_fast)) stop(msg, call. = FALSE)
        } else if (isTRUE(policy$objective_guard$fail_fast)) {
          stop(msg, call. = FALSE)
        }
      } else {
        sigma <- max(exp(sigma_opt$minimum), 1e-8)
      }
    }

    if (isTRUE(guard_triggered) &&
        identical(policy$objective_guard$mode, "adaptive_freeze") &&
        as.integer(policy$guard_refreeze_iters) > 0L) {
      old_freeze_until <- as.integer(gamsig_dynamic_freeze_until_iter)
      gamsig_dynamic_freeze_until_iter <- max(
        as.integer(gamsig_dynamic_freeze_until_iter),
        as.integer(iter + as.integer(policy$guard_refreeze_iters))
      )
      if (isTRUE(policy$objective_guard$log_failures)) {
        cat(
          sprintf(
            "[gamsig_refreeze] p0=%s iter=%d old_until=%d new_until=%d reason=%s\n",
            as.character(p0),
            iter_int,
            old_freeze_until,
            as.integer(gamsig_dynamic_freeze_until_iter),
            ifelse(is.null(guard_message), "", as.character(guard_message))
          )
        )
      }
    }

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
