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
