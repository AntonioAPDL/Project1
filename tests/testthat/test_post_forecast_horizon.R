source(testthat::test_path("..", "..", "R", "environmetrics", "02_helpers_core.R"))

test_that("forecast_cube_effective_horizon returns full horizon for finite cube", {
  set.seed(1)
  cube <- array(rnorm(7 * 32 * 12), dim = c(7, 32, 12))
  info <- forecast_cube_effective_horizon(cube, context = "test.full")
  expect_equal(info$horizon, 12L)
  expect_equal(info$trailing_missing, 0L)
  expect_true(all(info$finite_mask))
})

test_that("forecast cube trailing non-finite slices are truncated with explicit warning", {
  set.seed(2)
  cube <- array(rnorm(7 * 16 * 10), dim = c(7, 16, 10))
  cube[, , 8:10] <- NA_real_

  expect_warning(
    info <- forecast_cube_effective_horizon(cube, context = "test.trailing"),
    "\\[FORECAST_CUBE_TRUNCATE\\]"
  )
  expect_equal(info$horizon, 7L)
  trimmed <- trim_forecast_cube_to_effective_horizon(cube, context = "test.trailing")
  expect_equal(dim(trimmed$cube), c(7, 16, 7))
})

test_that("forecast cube fails fast on interior non-finite gaps", {
  set.seed(3)
  cube <- array(rnorm(7 * 12 * 9), dim = c(7, 12, 9))
  cube[, , 5] <- NA_real_
  expect_error(
    forecast_cube_effective_horizon(cube, context = "test.gap"),
    "\\[FORECAST_CUBE_GAP\\]"
  )
})

test_that("forecast cube fails fast when no finite forecast slices exist", {
  cube <- array(NA_real_, dim = c(7, 20, 6))
  expect_error(
    forecast_cube_effective_horizon(cube, context = "test.empty"),
    "\\[FORECAST_CUBE_EMPTY\\]"
  )
})
