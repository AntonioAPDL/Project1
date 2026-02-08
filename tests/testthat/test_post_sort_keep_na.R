source(testthat::test_path("..", "..", "R", "environmetrics", "02_helpers_core.R"))

test_that('sort_keep_na preserves all-NA vector length by default', {
  x <- rep(NA_real_, 8)
  y <- sort_keep_na(x)
  expect_length(y, length(x))
  expect_true(all(is.na(y)))
})

test_that('sort_keep_na supports legacy NA-drop behavior when disabled', {
  x <- c(NA_real_, 3, 1, NA_real_)
  y <- sort_keep_na(x, keep_na = FALSE)
  expect_equal(y, c(1, 3))
})

test_that('array-slice assignment does not error for all-NA slices', {
  xbs <- array(NA_real_, c(1, 1, 5))
  expect_no_error({
    xbs[1, 1, ] <- sort_keep_na(xbs[1, 1, ])
  })
  expect_length(xbs[1, 1, ], 5)
  expect_true(all(is.na(xbs[1, 1, ])))
})
