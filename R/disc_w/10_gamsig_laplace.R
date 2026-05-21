disc_w_clamp_prob <- function(prob, eps = 1e-12) {
  prob <- suppressWarnings(as.numeric(prob)[1L])
  eps <- suppressWarnings(as.numeric(eps)[1L])
  if (!is.finite(eps) || eps <= 0 || eps >= 0.5) {
    eps <- 1e-12
  }
  if (!is.finite(prob)) {
    prob <- 0.5
  }
  pmin(pmax(prob, eps), 1 - eps)
}

disc_w_gamma_zero_probability <- function(L, U, eps = 1e-12) {
  L <- suppressWarnings(as.numeric(L)[1L])
  U <- suppressWarnings(as.numeric(U)[1L])
  if (!is.finite(L) || !is.finite(U) || L >= U) {
    stop("L and U must be finite with L < U", call. = FALSE)
  }
  disc_w_clamp_prob((-L) / (U - L), eps = eps)
}

disc_w_theta_to_gamma <- function(theta_g, L, U, eps = 1e-12) {
  pi <- disc_w_clamp_prob(stats::plogis(theta_g), eps = eps)
  L + (U - L) * pi
}

disc_w_gamma_to_theta <- function(gamma, L, U, eps = 1e-12) {
  L <- suppressWarnings(as.numeric(L)[1L])
  U <- suppressWarnings(as.numeric(U)[1L])
  gamma <- suppressWarnings(as.numeric(gamma)[1L])
  if (!is.finite(L) || !is.finite(U) || L >= U) {
    stop("L and U must be finite with L < U", call. = FALSE)
  }
  if (!is.finite(gamma)) {
    stop("gamma must be finite", call. = FALSE)
  }
  pi <- disc_w_clamp_prob((gamma - L) / (U - L), eps = eps)
  stats::qlogis(pi)
}

disc_w_gamma_split_threshold <- function(
  L,
  U,
  abs_gamma_threshold = 0.05,
  rel_support_threshold = 0.02
) {
  abs_gamma_threshold <- suppressWarnings(as.numeric(abs_gamma_threshold)[1L])
  rel_support_threshold <- suppressWarnings(as.numeric(rel_support_threshold)[1L])
  if (!is.finite(abs_gamma_threshold) || abs_gamma_threshold <= 0) {
    abs_gamma_threshold <- 0.05
  }
  if (!is.finite(rel_support_threshold) || rel_support_threshold <= 0) {
    rel_support_threshold <- 0.02
  }
  max(abs_gamma_threshold, rel_support_threshold * abs(U - L))
}

disc_w_should_split_gamma_mode <- function(
  gamma_hat,
  L,
  U,
  enabled = TRUE,
  abs_gamma_threshold = 0.05,
  rel_support_threshold = 0.02,
  guard_triggered = FALSE,
  split_on_guard = TRUE
) {
  threshold <- disc_w_gamma_split_threshold(
    L = L,
    U = U,
    abs_gamma_threshold = abs_gamma_threshold,
    rel_support_threshold = rel_support_threshold
  )
  gamma_hat <- suppressWarnings(as.numeric(gamma_hat)[1L])
  reason <- "disabled"
  should_split <- FALSE
  if (!isTRUE(enabled)) {
    reason <- "disabled"
  } else if (isTRUE(split_on_guard) && isTRUE(guard_triggered)) {
    should_split <- TRUE
    reason <- "guard_triggered"
  } else if (is.finite(gamma_hat) && abs(gamma_hat) <= threshold) {
    should_split <- TRUE
    reason <- "near_zero"
  } else {
    reason <- "far_from_zero"
  }
  list(
    should_split = should_split,
    reason = reason,
    threshold = threshold,
    gamma_hat = gamma_hat
  )
}

disc_w_gamma_branch_bounds <- function(
  L,
  U,
  theta_gamma_lower,
  theta_gamma_upper,
  zero_margin_abs_gamma = 1e-6,
  eps = 1e-12
) {
  L <- suppressWarnings(as.numeric(L)[1L])
  U <- suppressWarnings(as.numeric(U)[1L])
  theta_gamma_lower <- suppressWarnings(as.numeric(theta_gamma_lower)[1L])
  theta_gamma_upper <- suppressWarnings(as.numeric(theta_gamma_upper)[1L])
  zero_margin_abs_gamma <- suppressWarnings(as.numeric(zero_margin_abs_gamma)[1L])
  if (!is.finite(zero_margin_abs_gamma) || zero_margin_abs_gamma <= 0) {
    zero_margin_abs_gamma <- 1e-6
  }
  max_margin <- 0.5 * min(abs(L), abs(U))
  if (!is.finite(max_margin) || max_margin <= 0) {
    max_margin <- zero_margin_abs_gamma
  }
  eff_margin <- min(zero_margin_abs_gamma, max_margin)
  eff_margin <- max(eff_margin, eps)
  theta_zero <- disc_w_gamma_to_theta(0, L = L, U = U, eps = eps)
  neg_upper_theta <- disc_w_gamma_to_theta(-eff_margin, L = L, U = U, eps = eps)
  pos_lower_theta <- disc_w_gamma_to_theta(eff_margin, L = L, U = U, eps = eps)
  negative <- c(theta_gamma_lower, min(theta_gamma_upper, neg_upper_theta))
  positive <- c(max(theta_gamma_lower, pos_lower_theta), theta_gamma_upper)
  list(
    theta_zero = theta_zero,
    zero_margin_abs_gamma = eff_margin,
    negative = negative,
    positive = positive,
    negative_valid = all(is.finite(negative)) && negative[1L] < negative[2L],
    positive_valid = all(is.finite(positive)) && positive[1L] < positive[2L]
  )
}

disc_w_seed_theta_pair_for_branch <- function(theta_pair, lower, upper) {
  theta_pair <- suppressWarnings(as.numeric(theta_pair))
  lower <- suppressWarnings(as.numeric(lower))
  upper <- suppressWarnings(as.numeric(upper))
  if (length(theta_pair) != 2L || length(lower) != 2L || length(upper) != 2L) {
    stop("theta_pair, lower, and upper must all have length 2", call. = FALSE)
  }
  out <- theta_pair
  out[1L] <- pmin(pmax(out[1L], lower[1L]), upper[1L])
  if (!is.finite(out[2L]) || out[2L] < lower[2L] || out[2L] > upper[2L]) {
    out[2L] <- mean(c(lower[2L], upper[2L]))
  }
  out[2L] <- pmin(pmax(out[2L], lower[2L]), upper[2L])
  out
}

disc_w_optimize_theta_candidate <- function(
  initial_values,
  objective_neg,
  lower,
  upper,
  label = "candidate"
) {
  lower <- suppressWarnings(as.numeric(lower))
  upper <- suppressWarnings(as.numeric(upper))
  if (length(lower) != 2L || length(upper) != 2L || any(!is.finite(lower)) || any(!is.finite(upper))) {
    stop("lower and upper must be finite vectors of length 2", call. = FALSE)
  }
  if (any(lower >= upper)) {
    return(list(
      ok = FALSE,
      label = label,
      par = NA_real_,
      obj_value = NA_real_,
      optim = NULL,
      message = "invalid_bounds"
    ))
  }
  par0 <- disc_w_seed_theta_pair_for_branch(initial_values, lower = lower, upper = upper)
  optim_res <- tryCatch(
    stats::optim(
      par = par0,
      fn = objective_neg,
      method = "L-BFGS-B",
      lower = lower,
      upper = upper,
      hessian = TRUE
    ),
    error = function(e) e
  )
  if (inherits(optim_res, "error")) {
    return(list(
      ok = FALSE,
      label = label,
      par = par0,
      obj_value = NA_real_,
      optim = NULL,
      message = conditionMessage(optim_res)
    ))
  }
  par <- pmin(pmax(optim_res$par, lower), upper)
  obj_value <- tryCatch(-objective_neg(par), error = function(e) NA_real_)
  list(
    ok = is.finite(obj_value),
    label = label,
    par = par,
    obj_value = obj_value,
    optim = optim_res,
    message = if (is.finite(obj_value)) "ok" else "non_finite_objective"
  )
}

disc_w_pick_best_theta_candidate <- function(candidates) {
  if (!is.list(candidates) || length(candidates) < 1L) {
    return(NULL)
  }
  keep <- Filter(function(x) {
    is.list(x) && isTRUE(x$ok) && is.finite(x$obj_value) && length(x$par) == 2L && all(is.finite(x$par))
  }, candidates)
  if (length(keep) < 1L) {
    return(NULL)
  }
  scores <- vapply(keep, function(x) x$obj_value, numeric(1))
  keep[[which.max(scores)]]
}

disc_w_theta_margin_to_bounds <- function(theta_pair, lower, upper) {
  theta_pair <- suppressWarnings(as.numeric(theta_pair))
  lower <- suppressWarnings(as.numeric(lower))
  upper <- suppressWarnings(as.numeric(upper))
  if (length(theta_pair) != 2L || length(lower) != 2L || length(upper) != 2L) {
    stop("theta_pair, lower, and upper must all have length 2", call. = FALSE)
  }
  lower_margin <- theta_pair - lower
  upper_margin <- upper - theta_pair
  pmin(lower_margin, upper_margin)
}

disc_w_candidate_is_interior <- function(
  theta_pair,
  lower,
  upper,
  abs_margin = c(1e-4, 1e-3),
  rel_margin = c(1e-6, 1e-4)
) {
  theta_pair <- suppressWarnings(as.numeric(theta_pair))
  lower <- suppressWarnings(as.numeric(lower))
  upper <- suppressWarnings(as.numeric(upper))
  abs_margin <- suppressWarnings(as.numeric(abs_margin))
  rel_margin <- suppressWarnings(as.numeric(rel_margin))
  if (length(theta_pair) != 2L || length(lower) != 2L || length(upper) != 2L) {
    stop("theta_pair, lower, and upper must all have length 2", call. = FALSE)
  }
  if (length(abs_margin) != 2L || any(!is.finite(abs_margin)) || any(abs_margin < 0)) {
    abs_margin <- c(1e-4, 1e-3)
  }
  if (length(rel_margin) != 2L || any(!is.finite(rel_margin)) || any(rel_margin < 0)) {
    rel_margin <- c(1e-6, 1e-4)
  }
  span <- pmax(upper - lower, 0)
  threshold <- pmax(abs_margin, rel_margin * span)
  margin <- disc_w_theta_margin_to_bounds(theta_pair, lower, upper)
  list(
    all_interior = all(is.finite(margin)) && all(is.finite(threshold)) && all(margin > threshold),
    margin = margin,
    threshold = threshold
  )
}

disc_w_gamma_margin_to_support <- function(gamma_hat, L, U) {
  gamma_hat <- suppressWarnings(as.numeric(gamma_hat)[1L])
  L <- suppressWarnings(as.numeric(L)[1L])
  U <- suppressWarnings(as.numeric(U)[1L])
  if (!is.finite(gamma_hat) || !is.finite(L) || !is.finite(U) || L >= U) {
    return(NA_real_)
  }
  min(gamma_hat - L, U - gamma_hat)
}

disc_w_candidate_has_gamma_margin <- function(
  theta_pair,
  L,
  U,
  abs_margin = 1e-4,
  rel_margin = 1e-4
) {
  theta_pair <- suppressWarnings(as.numeric(theta_pair))
  abs_margin <- suppressWarnings(as.numeric(abs_margin)[1L])
  rel_margin <- suppressWarnings(as.numeric(rel_margin)[1L])
  if (length(theta_pair) != 2L) {
    stop("theta_pair must have length 2", call. = FALSE)
  }
  if (!is.finite(abs_margin) || abs_margin < 0) {
    abs_margin <- 1e-4
  }
  if (!is.finite(rel_margin) || rel_margin < 0) {
    rel_margin <- 1e-4
  }
  gamma_hat <- disc_w_theta_to_gamma(theta_pair[[2L]], L = L, U = U)
  support_span <- pmax(U - L, 0)
  threshold <- max(abs_margin, rel_margin * support_span)
  margin <- disc_w_gamma_margin_to_support(gamma_hat, L = L, U = U)
  list(
    all_interior = is.finite(margin) && is.finite(threshold) && margin > threshold,
    gamma_hat = gamma_hat,
    margin = margin,
    threshold = threshold
  )
}

disc_w_exact_sigma_moments <- function(theta_mean, theta_cov) {
  theta_mean <- suppressWarnings(as.numeric(theta_mean))
  theta_cov <- as.matrix(theta_cov)
  if (length(theta_mean) < 1L || !is.finite(theta_mean[[1L]])) {
    stop("theta_mean must contain a finite theta_s entry", call. = FALSE)
  }
  if (nrow(theta_cov) < 1L || ncol(theta_cov) < 1L || !is.finite(theta_cov[[1L, 1L]])) {
    stop("theta_cov must contain a finite Var(theta_s) entry", call. = FALSE)
  }
  var_u <- suppressWarnings(as.numeric(theta_cov[[1L, 1L]]))
  if (!is.finite(var_u) || var_u < 0) {
    stop("Var(theta_s) must be finite and >= 0", call. = FALSE)
  }
  mu_u <- suppressWarnings(as.numeric(theta_mean[[1L]]))
  list(
    E_sigma = exp(mu_u + 0.5 * var_u),
    E_inv_sigma = exp(-mu_u + 0.5 * var_u),
    E_log_sigma = mu_u
  )
}

disc_w_try_exact_sigma_moments <- function(theta_mean, theta_cov) {
  tryCatch(
    list(
      ok = TRUE,
      moments = disc_w_exact_sigma_moments(theta_mean, theta_cov),
      error_message = ""
    ),
    error = function(e) {
      list(
        ok = FALSE,
        moments = NULL,
        error_message = conditionMessage(e)
      )
    }
  )
}

disc_w_try_expected_value <- function(f, theta_mean, theta_cov) {
  tryCatch(
    {
      hess <- numDeriv::hessian(func = f, x = theta_mean)
      if (any(!is.finite(hess))) {
        stop("non-finite Hessian", call. = FALSE)
      }
      prod <- hess %*% theta_cov
      value <- f(theta_mean) + 0.5 * sum(diag(prod))
      if (!is.finite(value)) {
        stop("non-finite expected value", call. = FALSE)
      }
      list(ok = TRUE, value = value, error_message = "")
    },
    error = function(e) {
      list(ok = FALSE, value = NA_real_, error_message = conditionMessage(e))
    }
  )
}

disc_w_validate_covariance_matrix <- function(
  covariance,
  symmetry_tol = 1e-8,
  eigen_tol = 1e-10
) {
  cov <- as.matrix(covariance)
  if (nrow(cov) != ncol(cov) || any(!is.finite(cov))) {
    return(list(
      ok = FALSE,
      covariance = NULL,
      reason = "invalid_entries",
      min_diag = NA_real_,
      min_eigen = NA_real_,
      symmetry_error = NA_real_
    ))
  }
  cov <- 0.5 * (cov + t(cov))
  scale_ref <- max(1, max(abs(cov)))
  symmetry_error <- max(abs(cov - t(cov)))
  if (!is.finite(symmetry_error) || symmetry_error > symmetry_tol * scale_ref) {
    return(list(
      ok = FALSE,
      covariance = cov,
      reason = "non_symmetric",
      min_diag = NA_real_,
      min_eigen = NA_real_,
      symmetry_error = symmetry_error
    ))
  }
  diag_vals <- diag(cov)
  min_diag <- suppressWarnings(min(diag_vals))
  if (any(!is.finite(diag_vals)) || !is.finite(min_diag)) {
    return(list(
      ok = FALSE,
      covariance = cov,
      reason = "invalid_diagonal",
      min_diag = min_diag,
      min_eigen = NA_real_,
      symmetry_error = symmetry_error
    ))
  }
  eig_vals <- tryCatch(
    eigen(cov, symmetric = TRUE, only.values = TRUE)$values,
    error = function(e) NULL
  )
  if (is.null(eig_vals) || any(!is.finite(eig_vals))) {
    return(list(
      ok = FALSE,
      covariance = cov,
      reason = "eigen_failure",
      min_diag = min_diag,
      min_eigen = NA_real_,
      symmetry_error = symmetry_error
    ))
  }
  min_eigen <- suppressWarnings(min(eig_vals))
  eig_floor <- -eigen_tol * max(1, max(abs(eig_vals)))
  if (min_diag < eig_floor) {
    return(list(
      ok = FALSE,
      covariance = cov,
      reason = "negative_diagonal",
      min_diag = min_diag,
      min_eigen = min_eigen,
      symmetry_error = symmetry_error
    ))
  }
  if (min_eigen < eig_floor) {
    return(list(
      ok = FALSE,
      covariance = cov,
      reason = "not_psd",
      min_diag = min_diag,
      min_eigen = min_eigen,
      symmetry_error = symmetry_error
    ))
  }
  list(
    ok = TRUE,
    covariance = cov,
    reason = "ok",
    min_diag = min_diag,
    min_eigen = min_eigen,
    symmetry_error = symmetry_error
  )
}

disc_w_build_laplace_covariance <- function(
  log_hessian,
  ridge_init = 1e-6,
  ridge_multiplier = 10,
  max_tries = 8L
) {
  if (is.null(log_hessian)) {
    return(list(
      ok = FALSE,
      covariance = NULL,
      covariance_type = "invalid_log_hessian",
      ridge_used = NA_real_,
      ridge_regularized = NA,
      attempts = 0L
    ))
  }

  log_hessian <- as.matrix(log_hessian)
  if (nrow(log_hessian) != ncol(log_hessian) || any(!is.finite(log_hessian))) {
    return(list(
      ok = FALSE,
      covariance = NULL,
      covariance_type = "invalid_log_hessian",
      ridge_used = NA_real_,
      ridge_regularized = NA,
      attempts = 0L
    ))
  }

  ridge_init <- suppressWarnings(as.numeric(ridge_init)[1L])
  ridge_multiplier <- suppressWarnings(as.numeric(ridge_multiplier)[1L])
  max_tries <- suppressWarnings(as.integer(max_tries)[1L])
  if (!is.finite(ridge_init) || ridge_init <= 0) {
    ridge_init <- 1e-6
  }
  if (!is.finite(ridge_multiplier) || ridge_multiplier <= 1) {
    ridge_multiplier <- 10
  }
  if (!is.finite(max_tries) || max_tries < 0L) {
    max_tries <- 8L
  }

  precision <- -(0.5 * (log_hessian + t(log_hessian)))
  if (any(!is.finite(precision))) {
    return(list(
      ok = FALSE,
      covariance = NULL,
      covariance_type = "invalid_precision",
      ridge_used = NA_real_,
      ridge_regularized = NA,
      attempts = 0L
    ))
  }

  last_validation <- list(
    reason = "not_attempted",
    min_diag = NA_real_,
    min_eigen = NA_real_,
    symmetry_error = NA_real_
  )
  exact_covariance <- tryCatch(solve(precision), error = function(e) NULL)
  if (!is.null(exact_covariance) && all(is.finite(exact_covariance))) {
    validation <- disc_w_validate_covariance_matrix(exact_covariance)
    last_validation <- validation
  } else {
    validation <- list(ok = FALSE)
  }
  if (isTRUE(validation$ok)) {
    return(list(
      ok = TRUE,
      covariance = validation$covariance,
      covariance_type = "laplace_precision_inverse",
      ridge_used = 0,
      ridge_regularized = FALSE,
      attempts = 1L,
      covariance_reason = validation$reason,
      min_diag = validation$min_diag,
      min_eigen = validation$min_eigen,
      symmetry_error = validation$symmetry_error
    ))
  }

  ridge <- ridge_init
  for (attempt in seq_len(max_tries + 1L)) {
    precision_reg <- precision + diag(ridge, nrow = nrow(precision))
    cov_candidate <- tryCatch(solve(precision_reg), error = function(e) NULL)
    if (!is.null(cov_candidate) && all(is.finite(cov_candidate))) {
      validation <- disc_w_validate_covariance_matrix(cov_candidate)
      last_validation <- validation
    } else {
      validation <- list(ok = FALSE)
    }
    if (isTRUE(validation$ok)) {
      return(list(
        ok = TRUE,
        covariance = validation$covariance,
        covariance_type = "ridge_regularized_precision_inverse",
        ridge_used = ridge,
        ridge_regularized = TRUE,
        attempts = attempt + 1L,
        covariance_reason = validation$reason,
        min_diag = validation$min_diag,
        min_eigen = validation$min_eigen,
        symmetry_error = validation$symmetry_error
      ))
    }
    ridge <- ridge * ridge_multiplier
  }

  list(
    ok = FALSE,
    covariance = NULL,
    covariance_type = "covariance_build_failed",
    ridge_used = ridge / ridge_multiplier,
    ridge_regularized = TRUE,
    attempts = max_tries + 2L,
    covariance_reason = last_validation$reason,
    min_diag = last_validation$min_diag,
    min_eigen = last_validation$min_eigen,
    symmetry_error = last_validation$symmetry_error
  )
}
