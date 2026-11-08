library(testthat)

# Extract only this pure helper. Sourcing the figure module would execute plots.
module_candidates <- c(file.path("R", "environmetrics", "40_figures_multivar_only.R"),
                       file.path("..", "..", "R", "environmetrics", "40_figures_multivar_only.R"))
module_path <- module_candidates[file.exists(module_candidates)][1L]
stopifnot(!is.na(module_path))
expressions <- parse(module_path)
helper_expression <- Filter(function(expr) {
  is.call(expr) && identical(expr[[1L]], as.name("<-")) &&
    identical(expr[[2L]], as.name("safe_diag_sd"))
}, as.list(expressions))
stopifnot(length(helper_expression) == 1L)
helper_env <- new.env(parent = baseenv())
eval(helper_expression[[1L]], envir = helper_env)
extract_sd <- helper_env$safe_diag_sd

test_that("historical covariance follows actual late time indices", {
  cube <- array(0, c(2L, 2L, 70L))
  cube[1L, 1L, ] <- seq_len(70L)^2
  cube[2L, 2L, ] <- (2 * seq_len(70L))^2
  expect_equal(extract_sd(cube, 1L, 31L, 40:70), as.numeric(40:70))
  expect_false(identical(extract_sd(cube, 1L, 31L, 40:70), extract_sd(cube, 1L, 31L)))
  expect_equal(extract_sd(cube, 2L, 3L, c(69L, 2L, 70L)), c(138, 4, 140))
  expect_equal(extract_sd(cube, 1L, 1L, 70L), 70)
})

test_that("legacy forecast prefix and short-array padding remain compatible", {
  cube <- array(0, c(1L, 1L, 3L))
  cube[1L, 1L, ] <- c(1, 4, 9)
  expect_equal(extract_sd(cube, 1L, 3L), c(1, 2, 3))
  expect_equal(extract_sd(cube, 1L, 5L), c(1, 2, 3, NA_real_, NA_real_))
  expect_equal(extract_sd(cube, 2L, 2L), rep(NA_real_, 2L))
  expect_equal(extract_sd(cube, 1L, 0L), numeric(0))
})

test_that("explicit historical indices fail on invalid indices or lengths", {
  cube <- array(1, c(1L, 1L, 3L))
  for (bad in list(c(1L, 4L), c(0L, 2L), c(NA_real_, 2), c(1.5, 2), 1L)) {
    expect_error(extract_sd(cube, 1L, 2L, bad), "valid covariance time indices")
  }
})

test_that("the historical caller supplies its actual display indices", {
  module <- paste(readLines(module_path, warn = FALSE), collapse = "\n")
  expect_match(module, "safe_diag_sd\\(sC_hist, psi_hist_idx\\[k\\], n_hist, time_indices = hist_idx\\)")
  expect_match(module, "safe_diag_sd\\(sC_seg, psi_k_idx, t_use\\)")
})
