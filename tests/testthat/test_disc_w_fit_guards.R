source(testthat::test_path("..", "..", "R", "disc_w", "09_fit_guards.R"))

test_that("finite guard fires before delayed state-growth guard", {
  out <- disc_w_iteration_guard_decision(
    elbo = NA_real_,
    state_norm_sq = 10,
    sigma_exp = 1,
    gamma_exp = 0,
    theta_update = TRUE,
    gamsig_frozen_now = FALSE,
    state_guard_enabled = TRUE,
    iter = 46,
    state_guard_start_iter = 1000,
    prev_state_norm_sq = 9,
    state_norm_abs_cap = 1e8,
    state_norm_max_ratio = 10
  )

  expect_match(out$reason, "non-finite elbo")
  expect_true(out$finite_guard)
  expect_false(out$state_guard_active)
  expect_true(is.na(out$state_growth_ratio))
})

test_that("finite guard is not bypassed during gamma-sigma freeze", {
  out <- disc_w_iteration_guard_decision(
    elbo = -1,
    state_norm_sq = NA_real_,
    sigma_exp = 1,
    gamma_exp = 0,
    theta_update = TRUE,
    gamsig_frozen_now = TRUE,
    state_guard_enabled = TRUE,
    iter = 20,
    state_guard_start_iter = 1000,
    prev_state_norm_sq = 9,
    state_norm_abs_cap = 1e8,
    state_norm_max_ratio = 10
  )

  expect_match(out$reason, "non-finite state_norm_sq")
  expect_true(out$finite_guard)
  expect_false(out$state_guard_active)
})

test_that("state-growth checks remain gated by the configured start iteration", {
  before <- disc_w_iteration_guard_decision(
    elbo = -1,
    state_norm_sq = 1000,
    sigma_exp = 1,
    gamma_exp = 0,
    theta_update = TRUE,
    gamsig_frozen_now = FALSE,
    state_guard_enabled = TRUE,
    iter = 20,
    state_guard_start_iter = 100,
    prev_state_norm_sq = 10,
    state_norm_abs_cap = 1e8,
    state_norm_max_ratio = 10
  )
  after <- disc_w_iteration_guard_decision(
    elbo = -1,
    state_norm_sq = 1000,
    sigma_exp = 1,
    gamma_exp = 0,
    theta_update = TRUE,
    gamsig_frozen_now = FALSE,
    state_guard_enabled = TRUE,
    iter = 100,
    state_guard_start_iter = 100,
    prev_state_norm_sq = 10,
    state_norm_abs_cap = 1e8,
    state_norm_max_ratio = 10
  )

  expect_null(before$reason)
  expect_false(before$state_guard_active)
  expect_true(after$state_guard_active)
  expect_match(after$reason, "state_growth_ratio")
  expect_false(after$finite_guard)
})

test_that("absolute state norm cap is a hard safety guard", {
  out <- disc_w_iteration_guard_decision(
    elbo = -175,
    state_norm_sq = 1.38e14,
    sigma_exp = 1,
    gamma_exp = 0,
    theta_update = TRUE,
    gamsig_frozen_now = TRUE,
    state_guard_enabled = TRUE,
    iter = 12,
    state_guard_start_iter = 1000,
    prev_state_norm_sq = 1e5,
    state_norm_abs_cap = 1e6,
    state_norm_max_ratio = 25
  )

  expect_match(out$reason, "state_norm_sq=.*exceeds abs_cap")
  expect_false(out$finite_guard)
  expect_false(out$state_guard_active)
})

test_that("absolute state norm cap can be scaled by observation length", {
  healthy_extreme <- disc_w_iteration_guard_decision(
    elbo = -2,
    state_norm_sq = 33799896,
    sigma_exp = 1,
    gamma_exp = 0,
    theta_update = TRUE,
    gamsig_frozen_now = TRUE,
    state_guard_enabled = TRUE,
    iter = 1,
    state_guard_start_iter = 1000,
    prev_state_norm_sq = NA_real_,
    state_norm_abs_cap = 1e6,
    state_norm_max_ratio = 25,
    state_norm_length = 12294,
    state_norm_abs_cap_scale = "per_time"
  )
  explosive_median <- disc_w_iteration_guard_decision(
    elbo = -175,
    state_norm_sq = 1.38e14,
    sigma_exp = 1,
    gamma_exp = 0,
    theta_update = TRUE,
    gamsig_frozen_now = TRUE,
    state_guard_enabled = TRUE,
    iter = 12,
    state_guard_start_iter = 1000,
    prev_state_norm_sq = NA_real_,
    state_norm_abs_cap = 1e6,
    state_norm_max_ratio = 25,
    state_norm_length = 12294,
    state_norm_abs_cap_scale = "per_time"
  )
  total_scale <- disc_w_iteration_guard_decision(
    elbo = -2,
    state_norm_sq = 33799896,
    sigma_exp = 1,
    gamma_exp = 0,
    theta_update = TRUE,
    gamsig_frozen_now = TRUE,
    state_guard_enabled = TRUE,
    iter = 1,
    state_guard_start_iter = 1000,
    prev_state_norm_sq = NA_real_,
    state_norm_abs_cap = 1e6,
    state_norm_max_ratio = 25,
    state_norm_length = 12294,
    state_norm_abs_cap_scale = "total"
  )

  expect_null(healthy_extreme$reason)
  expect_match(explosive_median$reason, "state_norm_sq_per_T=.*exceeds abs_cap")
  expect_match(total_scale$reason, "state_norm_sq=.*exceeds abs_cap")
})

test_that("state-growth ratio guard uses scale-aware reference floor when configured", {
  q35_like <- disc_w_iteration_guard_decision(
    elbo = -100,
    state_norm_sq = 22702.47,
    sigma_exp = 0.05693132,
    gamma_exp = 0,
    theta_update = TRUE,
    gamsig_frozen_now = FALSE,
    state_guard_enabled = TRUE,
    iter = 160,
    state_guard_start_iter = 50,
    prev_state_norm_sq = 37.19796,
    state_norm_abs_cap = 1e6,
    state_norm_max_ratio = 25,
    state_norm_length = 12767,
    state_norm_abs_cap_scale = "per_time",
    state_norm_ratio_ref_floor = 0.1
  )
  no_floor <- disc_w_iteration_guard_decision(
    elbo = -100,
    state_norm_sq = 22702.47,
    sigma_exp = 0.05693132,
    gamma_exp = 0,
    theta_update = TRUE,
    gamsig_frozen_now = FALSE,
    state_guard_enabled = TRUE,
    iter = 160,
    state_guard_start_iter = 50,
    prev_state_norm_sq = 37.19796,
    state_norm_abs_cap = 1e6,
    state_norm_max_ratio = 25,
    state_norm_length = 12767,
    state_norm_abs_cap_scale = "per_time"
  )

  expect_match(no_floor$reason, "state_growth_ratio")
  expect_null(q35_like$reason)
  expect_equal(q35_like$state_growth_ref_floor_total, 1276.7)
  expect_gt(q35_like$state_growth_ratio, 600)
  expect_lt(q35_like$state_growth_effective_ratio, 25)
})

test_that("state-growth reference floor does not hide material effective jumps", {
  out <- disc_w_iteration_guard_decision(
    elbo = -100,
    state_norm_sq = 40000,
    sigma_exp = 0.05,
    gamma_exp = 0,
    theta_update = TRUE,
    gamsig_frozen_now = FALSE,
    state_guard_enabled = TRUE,
    iter = 160,
    state_guard_start_iter = 50,
    prev_state_norm_sq = 37.19796,
    state_norm_abs_cap = 1e6,
    state_norm_max_ratio = 25,
    state_norm_length = 12767,
    state_norm_abs_cap_scale = "per_time",
    state_norm_ratio_ref_floor = 0.1
  )

  expect_match(out$reason, "state_growth_effective_ratio")
  expect_match(out$reason, "raw_state_growth_ratio")
  expect_gt(out$state_growth_effective_ratio, 25)
})

test_that("state-growth reference floor follows total-scale semantics", {
  out <- disc_w_iteration_guard_decision(
    elbo = -100,
    state_norm_sq = 2400,
    sigma_exp = 0.05,
    gamma_exp = 0,
    theta_update = TRUE,
    gamsig_frozen_now = FALSE,
    state_guard_enabled = TRUE,
    iter = 160,
    state_guard_start_iter = 50,
    prev_state_norm_sq = 12,
    state_norm_abs_cap = 1e6,
    state_norm_max_ratio = 25,
    state_norm_length = 1000,
    state_norm_abs_cap_scale = "total",
    state_norm_ratio_ref_floor = 100
  )

  expect_null(out$reason)
  expect_equal(out$state_growth_ref_floor_total, 100)
  expect_equal(out$state_growth_effective_ratio, 24)
})

test_that("summary helpers reject partial non-finite payloads", {
  expect_true(is.na(disc_w_numeric_mean_all_finite(c(1, NA_real_))))
  expect_true(is.na(disc_w_numeric_mean_all_finite(c(1, Inf))))
  expect_true(is.na(disc_w_numeric_mean_all_finite(c(1, 0), positive_required = TRUE)))
  expect_equal(disc_w_numeric_mean_all_finite(c(1, 2, 3)), 2)

  expect_true(is.na(disc_w_state_norm_sq_all_finite(c(1, NA_real_))))
  expect_true(is.na(disc_w_state_norm_sq_all_finite(c(1, Inf))))
  expect_equal(disc_w_state_norm_sq_all_finite(c(1, 2, 3)), 14)
})

test_that("scalar helper protects first-iteration rollback ELBO bookkeeping", {
  expect_equal(disc_w_scalar_finite_or_default(0, default = 99), 0)
  expect_equal(disc_w_scalar_finite_or_default(numeric(0), default = 99), 99)
  expect_equal(disc_w_scalar_finite_or_default(NULL, default = 99), 99)
  expect_equal(disc_w_scalar_finite_or_default(Inf, default = 99), 99)
  expect_equal(disc_w_scalar_finite_or_default(c(1, 2), default = 99), 99)
})

test_that("finite square matrix assertion fails before SPD projection", {
  expect_equal(disc_w_assert_finite_square_matrix(diag(2), label = "ok"), diag(2))
  expect_error(
    disc_w_assert_finite_square_matrix(matrix(c(1, NaN, 0, 1), nrow = 2), label = "ww[j=1,t=1]"),
    "ww\\[j=1,t=1\\] contains non-finite entries before SPD projection \\(n=1 dim=2x2\\)"
  )
  expect_error(
    disc_w_assert_finite_square_matrix(matrix(1:6, nrow = 2), label = "bad"),
    "bad must be a non-empty square matrix"
  )
})

test_that("state guard step backoff is bounded and deterministic", {
  expect_equal(
    disc_w_guard_backoff_step_scale(
      current_scale = 1,
      backoff_factor = 0.2,
      min_scale = 0.05
    ),
    0.2
  )
  expect_equal(
    disc_w_guard_backoff_step_scale(
      current_scale = 0.2,
      backoff_factor = 0.2,
      min_scale = 0.05
    ),
    0.05
  )
  expect_equal(
    disc_w_guard_backoff_step_scale(
      current_scale = 0.2,
      backoff_factor = 0.2,
      min_scale = 0.05,
      enabled = FALSE
    ),
    0.2
  )
  expect_equal(disc_w_effective_step_cap(0.5, 0.2), 0.1)
  expect_equal(disc_w_effective_step_cap(0.25, 0.2), 0.05)
})

test_that("state guard retry windows scale with the damped proposal", {
  expect_equal(
    disc_w_guard_scaled_hold_iters(
      base_iters = 20L,
      step_scale = 0.2,
      min_iters = 1L
    ),
    4L
  )
  expect_equal(
    disc_w_guard_scaled_hold_iters(
      base_iters = 20L,
      step_scale = 0.05,
      min_iters = 1L
    ),
    1L
  )
  expect_equal(
    disc_w_guard_scaled_hold_iters(
      base_iters = 20L,
      step_scale = 0.005,
      min_iters = 1L
    ),
    1L
  )
  expect_equal(
    disc_w_guard_scaled_hold_iters(
      base_iters = 20L,
      step_scale = 0.05,
      min_iters = 2L
    ),
    2L
  )
  expect_equal(
    disc_w_guard_scaled_hold_iters(
      base_iters = 20L,
      step_scale = 0.05,
      enabled = FALSE
    ),
    20L
  )
  expect_equal(disc_w_guard_scaled_hold_iters(0L, 0.05), 0L)
})

test_that("state guard step backoff can shrink below the old 0.05 floor", {
  expect_equal(
    disc_w_guard_backoff_step_scale(
      current_scale = 0.05,
      backoff_factor = 0.2,
      min_scale = 0.005
    ),
    0.01
  )
  expect_equal(
    disc_w_guard_backoff_step_scale(
      current_scale = 0.01,
      backoff_factor = 0.2,
      min_scale = 0.005
    ),
    0.005
  )
})

test_that("gamma/sigma recovery re-anchors every pseudo-data moment coherently", {
  log_g <- function(gam) log(2) + stats::pnorm(-abs(gam), log.p = TRUE) + 0.5 * gam^2
  p_fn <- function(p0, gam) {
    (p0 - as.numeric(gam < 0)) / exp(log_g(gam)) + as.numeric(gam < 0)
  }
  A_fn <- function(p0, gam) {
    temp_p <- p_fn(p0, gam)
    (1 - 2 * temp_p) / (temp_p * (1 - temp_p))
  }
  B_fn <- function(p0, gam) {
    temp_p <- p_fn(p0, gam)
    2 / (temp_p * (1 - temp_p))
  }
  C_fn <- function(p0, gam) {
    temp_p <- p_fn(p0, gam)
    (as.numeric(gam > 0) - temp_p)^(-1)
  }

  sigma <- matrix(c(0.6, 0.5, 0.8), ncol = 1)
  payload <- list(
    E.gam = matrix(rep(-0.25, 3), ncol = 1),
    E.sigma = sigma,
    E.inv.sigma = 1 / sigma,
    E.c2.invb.absgam2.sigma = matrix(99, nrow = 3, ncol = 1),
    E.c.invb.absgam = matrix(99, nrow = 3, ncol = 1),
    E.c.a.invb.absgam = matrix(99, nrow = 3, ncol = 1),
    E.a2.invb.inv.sigma = matrix(99, nrow = 3, ncol = 1),
    E.invb.inv.sigma = matrix(99, nrow = 3, ncol = 1),
    E.a.invb.inv.sigma = matrix(99, nrow = 3, ncol = 1),
    E.log.sig.b = matrix(99, nrow = 3, ncol = 1),
    E.log.sig = matrix(99, nrow = 3, ncol = 1),
    E.prior.sig.gam = matrix(99, nrow = 3, ncol = 1),
    entrop = matrix(99, nrow = 3, ncol = 1)
  )

  out <- disc_w_reanchor_gamsig_to_gamma(
    payload,
    gamma = 0,
    p0 = 0.5,
    L = -1,
    U = 1,
    A_fn = A_fn,
    B_fn = B_fn,
    C_fn = C_fn,
    status = "test_zero_anchor"
  )

  expect_equal(as.numeric(out$E.gam), c(0, 0, 0))
  expect_equal(as.numeric(out$E.sigma), as.numeric(sigma))
  expect_equal(as.numeric(out$E.inv.sigma), as.numeric(1 / sigma))
  expect_equal(as.numeric(out$E.c2.invb.absgam2.sigma), c(0, 0, 0))
  expect_equal(as.numeric(out$E.c.invb.absgam), c(0, 0, 0))
  expect_equal(as.numeric(out$E.c.a.invb.absgam), c(0, 0, 0))
  expect_equal(as.numeric(out$E.a2.invb.inv.sigma), c(0, 0, 0))
  expect_equal(as.numeric(out$E.a.invb.inv.sigma), c(0, 0, 0))
  expect_equal(as.numeric(out$E.invb.inv.sigma), as.numeric(1 / (sigma * 8)))
  expect_equal(as.numeric(out$E.log.sig.b), as.numeric(log(sigma * 8)))
  expect_equal(as.numeric(out$E.log.sig), as.numeric(log(sigma)))
  expect_equal(as.numeric(out$E.prior.sig.gam), c(0, 0, 0))
  expect_equal(as.numeric(out$entrop), c(0, 0, 0))
  expect_true(out$state_guard_reanchored)
  expect_equal(out$state_guard_reanchor_status, "test_zero_anchor")
  expect_equal(out$state_guard_reanchor_gamma, 0)
})
