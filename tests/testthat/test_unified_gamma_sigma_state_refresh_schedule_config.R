source(testthat::test_path("..", "..", "R", "unified", "config.R"))

test_that("unified_validate_config accepts valid state refresh schedule", {
  cfg <- unified_config_defaults()
  cfg$fit$exdqlm_multivar$gamma_sigma$state_refresh_schedule <- list(
    enabled = TRUE,
    start_iter = 11L,
    end_iter = 200L,
    hold_iters = 10L,
    refresh_iters = 1L
  )

  errs <- unified_validate_config(cfg)
  schedule_errs <- errs[grepl("state_refresh_schedule", errs, fixed = TRUE)]
  expect_length(schedule_errs, 0L)
})

test_that("unified_validate_config rejects invalid state refresh schedule", {
  cfg <- unified_config_defaults()
  cfg$fit$exdqlm_multivar$gamma_sigma$state_refresh_schedule <- list(
    enabled = TRUE,
    start_iter = 5L,
    end_iter = 4L,
    hold_iters = 0L,
    refresh_iters = 0L
  )

  errs <- unified_validate_config(cfg)
  expect_true(any(grepl("state_refresh_schedule.start_iter", errs, fixed = TRUE)))
  expect_true(any(grepl("state_refresh_schedule.end_iter", errs, fixed = TRUE)))
  expect_true(any(grepl("state_refresh_schedule.hold_iters", errs, fixed = TRUE)))
  expect_true(any(grepl("state_refresh_schedule.refresh_iters", errs, fixed = TRUE)))
})

test_that("unified_validate_config accepts valid laplace split controls", {
  cfg <- unified_config_defaults()
  cfg$fit$exdqlm_multivar$gamma_sigma$laplace_split_near_zero <- list(
    enabled = TRUE,
    abs_gamma_threshold = 0.05,
    rel_support_threshold = 0.02,
    zero_margin_abs_gamma = 1e-6,
    split_on_guard = TRUE
  )

  errs <- unified_validate_config(cfg)
  split_errs <- errs[grepl("laplace_split_near_zero", errs, fixed = TRUE)]
  expect_length(split_errs, 0L)
})

test_that("unified_validate_config rejects invalid laplace split controls", {
  cfg <- unified_config_defaults()
  cfg$fit$exdqlm_multivar$gamma_sigma$laplace_split_near_zero <- list(
    enabled = TRUE,
    abs_gamma_threshold = 0,
    rel_support_threshold = -1,
    zero_margin_abs_gamma = 0,
    split_on_guard = NA
  )

  errs <- unified_validate_config(cfg)
  expect_true(any(grepl("laplace_split_near_zero.abs_gamma_threshold", errs, fixed = TRUE)))
  expect_true(any(grepl("laplace_split_near_zero.rel_support_threshold", errs, fixed = TRUE)))
  expect_true(any(grepl("laplace_split_near_zero.zero_margin_abs_gamma", errs, fixed = TRUE)))
  expect_true(any(grepl("laplace_split_near_zero.split_on_guard", errs, fixed = TRUE)))
})

test_that("unified_validate_config accepts valid near-zero fallback controls", {
  cfg <- unified_config_defaults()
  cfg$fit$exdqlm_multivar$gamma_sigma$near_zero_fallback <- list(
    enabled = TRUE,
    mode = "sigma_only",
    gamma_anchor = "full_candidate"
  )

  errs <- unified_validate_config(cfg)
  fallback_errs <- errs[grepl("near_zero_fallback", errs, fixed = TRUE)]
  expect_length(fallback_errs, 0L)
})

test_that("unified_validate_config rejects invalid near-zero fallback controls", {
  cfg <- unified_config_defaults()
  cfg$fit$exdqlm_multivar$gamma_sigma$near_zero_fallback <- list(
    enabled = NA,
    mode = "bad",
    gamma_anchor = "bad"
  )

  errs <- unified_validate_config(cfg)
  expect_true(any(grepl("near_zero_fallback.enabled", errs, fixed = TRUE)))
  expect_true(any(grepl("near_zero_fallback.mode", errs, fixed = TRUE)))
  expect_true(any(grepl("near_zero_fallback.gamma_anchor", errs, fixed = TRUE)))
})
