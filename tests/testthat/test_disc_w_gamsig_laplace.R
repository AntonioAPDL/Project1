source(testthat::test_path("..", "..", "R", "disc_w", "10_gamsig_laplace.R"))

test_that("disc_w_should_split_gamma_mode detects near-zero and guard cases", {
  near_zero <- disc_w_should_split_gamma_mode(
    gamma_hat = 0.01,
    L = -1,
    U = 1,
    enabled = TRUE,
    abs_gamma_threshold = 0.05,
    rel_support_threshold = 0.02,
    guard_triggered = FALSE,
    split_on_guard = TRUE
  )
  expect_true(near_zero$should_split)
  expect_identical(near_zero$reason, "near_zero")

  far_from_zero <- disc_w_should_split_gamma_mode(
    gamma_hat = 0.25,
    L = -1,
    U = 1,
    enabled = TRUE,
    abs_gamma_threshold = 0.05,
    rel_support_threshold = 0.02,
    guard_triggered = FALSE,
    split_on_guard = TRUE
  )
  expect_false(far_from_zero$should_split)
  expect_identical(far_from_zero$reason, "far_from_zero")

  guard_case <- disc_w_should_split_gamma_mode(
    gamma_hat = 0.25,
    L = -1,
    U = 1,
    enabled = TRUE,
    abs_gamma_threshold = 0.05,
    rel_support_threshold = 0.02,
    guard_triggered = TRUE,
    split_on_guard = TRUE
  )
  expect_true(guard_case$should_split)
  expect_identical(guard_case$reason, "guard_triggered")
})

test_that("disc_w_gamma_branch_bounds split the transformed space around gamma zero", {
  bounds <- disc_w_gamma_branch_bounds(
    L = -1,
    U = 1,
    theta_gamma_lower = qlogis(1e-6),
    theta_gamma_upper = qlogis(1 - 1e-6),
    zero_margin_abs_gamma = 1e-4
  )

  expect_true(bounds$negative_valid)
  expect_true(bounds$positive_valid)
  expect_lt(bounds$negative[[2]], bounds$theta_zero)
  expect_gt(bounds$positive[[1]], bounds$theta_zero)
})

test_that("disc_w_optimize_theta_candidate and picker prefer the higher-objective branch", {
  objective_neg <- function(x) {
    (x[[1]] - 0.1)^2 + (x[[2]] + 2)^2
  }

  negative <- disc_w_optimize_theta_candidate(
    initial_values = c(0, 0),
    objective_neg = objective_neg,
    lower = c(-5, -5),
    upper = c(5, -0.1),
    label = "negative"
  )
  positive <- disc_w_optimize_theta_candidate(
    initial_values = c(0, 0),
    objective_neg = objective_neg,
    lower = c(-5, 0.1),
    upper = c(5, 5),
    label = "positive"
  )

  expect_true(negative$ok)
  expect_true(positive$ok)
  best <- disc_w_pick_best_theta_candidate(list(negative, positive))
  expect_identical(best$label, "negative")
  expect_gt(best$obj_value, positive$obj_value)
})

test_that("disc_w_exact_sigma_moments returns closed-form lognormal moments", {
  theta_mean <- c(1.2, -0.4)
  theta_cov <- matrix(c(0.3, 0.05, 0.05, 0.8), nrow = 2)

  out <- disc_w_exact_sigma_moments(theta_mean, theta_cov)

  expect_equal(out$E_sigma, exp(1.2 + 0.5 * 0.3))
  expect_equal(out$E_inv_sigma, exp(-1.2 + 0.5 * 0.3))
  expect_equal(out$E_log_sigma, 1.2)
})

test_that("disc_w_exact_sigma_moments rejects invalid theta_s covariance inputs", {
  expect_error(
    disc_w_exact_sigma_moments(c(1, 2), matrix(c(-0.1, 0, 0, 1), nrow = 2)),
    "Var\\(theta_s\\) must be finite and >= 0"
  )
  expect_error(
    disc_w_exact_sigma_moments(c(NA_real_, 2), diag(2)),
    "theta_mean must contain a finite theta_s entry"
  )
})

test_that("disc_w_try_exact_sigma_moments reports invalid covariance without stopping", {
  out <- disc_w_try_exact_sigma_moments(c(1, 2), matrix(c(-0.1, 0, 0, 1), nrow = 2))

  expect_false(out$ok)
  expect_null(out$moments)
  expect_match(out$error_message, "Var\\(theta_s\\) must be finite and >= 0")
})

test_that("disc_w_build_laplace_covariance returns the exact inverse when possible", {
  log_hessian <- -diag(c(4, 9), nrow = 2)

  out <- disc_w_build_laplace_covariance(
    log_hessian = log_hessian,
    ridge_init = 1e-6,
    ridge_multiplier = 10,
    max_tries = 3
  )

  expect_true(out$ok)
  expect_identical(out$covariance_type, "laplace_precision_inverse")
  expect_false(out$ridge_regularized)
  expect_equal(out$ridge_used, 0)
  expect_equal(out$covariance, diag(c(1 / 4, 1 / 9), nrow = 2))
})

test_that("disc_w_build_laplace_covariance rejects indefinite exact inverses and repairs with ridge", {
  log_hessian <- -matrix(c(1, 2, 2, 1), nrow = 2)

  out <- disc_w_build_laplace_covariance(
    log_hessian = log_hessian,
    ridge_init = 1e-6,
    ridge_multiplier = 10,
    max_tries = 8
  )

  expect_true(out$ok)
  expect_true(out$ridge_regularized)
  expect_identical(out$covariance_type, "ridge_regularized_precision_inverse")
  expect_true(all(diag(out$covariance) >= 0))
  eig <- eigen(out$covariance, symmetric = TRUE, only.values = TRUE)$values
  expect_true(min(eig) >= -1e-10)
  expect_true(is.finite(out$min_diag))
  expect_true(is.finite(out$min_eigen))
})

test_that("disc_w_build_laplace_covariance falls back to ridge regularization when needed", {
  log_hessian <- matrix(0, nrow = 2, ncol = 2)

  out <- disc_w_build_laplace_covariance(
    log_hessian = log_hessian,
    ridge_init = 1e-3,
    ridge_multiplier = 10,
    max_tries = 2
  )

  expect_true(out$ok)
  expect_identical(out$covariance_type, "ridge_regularized_precision_inverse")
  expect_true(out$ridge_regularized)
  expect_equal(out$ridge_used, 1e-3)
  expect_equal(out$covariance, diag(1000, nrow = 2))
})

test_that("disc_w_candidate_is_interior detects near-boundary branch candidates", {
  interior <- disc_w_candidate_is_interior(
    theta_pair = c(0, 0),
    lower = c(-1, -10),
    upper = c(1, 10)
  )
  expect_true(interior$all_interior)

  boundary <- disc_w_candidate_is_interior(
    theta_pair = c(0, 9.9999),
    lower = c(-1, -10),
    upper = c(1, 10)
  )
  expect_false(boundary$all_interior)
})

test_that("disc_w_candidate_has_gamma_margin rejects support-boundary gamma candidates", {
  interior <- disc_w_candidate_has_gamma_margin(
    theta_pair = c(0, 0),
    L = -1,
    U = 1
  )
  expect_true(interior$all_interior)

  near_upper <- disc_w_candidate_has_gamma_margin(
    theta_pair = c(0, qlogis(1 - 1e-12)),
    L = -1,
    U = 1
  )
  expect_false(near_upper$all_interior)
  expect_true(near_upper$margin <= near_upper$threshold)
})

test_that("disc_w_try_expected_value reports non-finite expectations without stopping", {
  out <- disc_w_try_expected_value(
    f = function(theta) if (theta[[2]] > 0) NA_real_ else 0,
    theta_mean = c(0, 1),
    theta_cov = diag(2)
  )

  expect_false(out$ok)
  expect_true(is.na(out$value))
  expect_match(out$error_message, "non-finite")
})

test_that("near-zero fallback policy normalizes invalid options conservatively", {
  policy <- disc_w_normalize_near_zero_fallback_policy(
    enabled = TRUE,
    mode = "bad",
    gamma_anchor = "bad"
  )

  expect_true(policy$enabled)
  expect_identical(policy$mode, "sigma_only")
  expect_identical(policy$gamma_anchor, "full_candidate")

  off_policy <- disc_w_normalize_near_zero_fallback_policy(
    enabled = TRUE,
    mode = "off",
    gamma_anchor = "zero"
  )
  expect_false(off_policy$enabled)
  expect_identical(off_policy$gamma_anchor, "zero")
})

test_that("near-zero fallback eligibility is limited to finite near-zero full candidates", {
  split_decision <- disc_w_should_split_gamma_mode(
    gamma_hat = 0.01,
    L = -1,
    U = 1,
    enabled = TRUE,
    abs_gamma_threshold = 0.05,
    rel_support_threshold = 0.02
  )
  full_candidate <- list(
    ok = TRUE,
    par = c(log(0.7), disc_w_gamma_to_theta(0.01, L = -1, U = 1)),
    obj_value = 12.5
  )

  eligible <- disc_w_near_zero_fallback_eligible(
    split_decision = split_decision,
    full_candidate = full_candidate,
    L = -1,
    U = 1,
    enabled = TRUE,
    mode = "sigma_only"
  )
  expect_true(eligible$eligible)
  expect_identical(eligible$reason, "near_zero_full_candidate_finite")
  expect_equal(eligible$gamma_hat, 0.01, tolerance = 1e-8)

  disabled <- disc_w_near_zero_fallback_eligible(
    split_decision = split_decision,
    full_candidate = full_candidate,
    L = -1,
    U = 1,
    enabled = FALSE,
    mode = "sigma_only"
  )
  expect_false(disabled$eligible)
  expect_identical(disabled$reason, "disabled")

  bad_objective <- full_candidate
  bad_objective$obj_value <- Inf
  rejected <- disc_w_near_zero_fallback_eligible(
    split_decision = split_decision,
    full_candidate = bad_objective,
    L = -1,
    U = 1,
    enabled = TRUE,
    mode = "sigma_only"
  )
  expect_false(rejected$eligible)
  expect_identical(rejected$reason, "full_candidate_invalid_objective")
})

test_that("active multivariate runner exposes near-zero fallback policy and diagnostics", {
  runner <- testthat::test_path("..", "..", "DISC_Optimal_Synth_Ranges_W_transfer_forecast.r")
  text <- paste(readLines(runner, warn = FALSE), collapse = "\n")

  expect_true(grepl("DISC_GAMSIG_NEAR_ZERO_FALLBACK_ENABLED", text, fixed = TRUE))
  expect_true(grepl("DISC_GAMSIG_NEAR_ZERO_FALLBACK_MODE", text, fixed = TRUE))
  expect_true(grepl("DISC_GAMSIG_NEAR_ZERO_GAMMA_ANCHOR", text, fixed = TRUE))
  expect_true(grepl("near_zero_sigma_only_fallback", text, fixed = TRUE))
  expect_true(grepl("[gamsig_near_zero_fallback]", text, fixed = TRUE))
  expect_true(grepl("near_zero_fallback_count", text, fixed = TRUE))
})
