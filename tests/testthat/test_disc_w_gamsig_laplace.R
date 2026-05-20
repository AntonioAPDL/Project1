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
