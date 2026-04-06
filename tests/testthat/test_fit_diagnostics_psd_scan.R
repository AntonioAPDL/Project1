source(testthat::test_path("..", "..", "R", "unified", "diagnostics.R"))

test_that("diag_check_psd_3d full scan catches unsampled bad slices", {
  arr <- array(0, dim = c(2, 2, 3))
  arr[, , 1] <- diag(c(1, 1))
  arr[, , 2] <- matrix(c(2, 0.1, 0.1, 1), nrow = 2, byrow = TRUE)
  arr[, , 3] <- matrix(c(1, 0, 0, -1e-6), nrow = 2, byrow = TRUE)

  sampled <- diag_check_psd_3d(
    A = arr,
    sample_idx = c(1L, 2L),
    name = "ut.psd",
    psd_tol = -1e-8,
    full_scan = FALSE,
    id_suffix = "psd"
  )
  expect_equal(sampled$status, "pass")
  expect_equal(sampled$metrics$scan_mode, "sampled")
  expect_equal(sampled$metrics$checked_slices_count, 2L)

  full <- diag_check_psd_3d(
    A = arr,
    sample_idx = c(1L, 2L),
    name = "ut.psd",
    psd_tol = -1e-8,
    full_scan = TRUE,
    id_suffix = "psd"
  )
  expect_equal(full$status, "fail")
  expect_equal(full$metrics$scan_mode, "full")
  expect_equal(full$metrics$checked_slices_count, 3L)
  expect_true(length(full$metrics$violating_slices) >= 1L)
})
