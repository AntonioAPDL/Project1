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
