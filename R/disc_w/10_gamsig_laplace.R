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
