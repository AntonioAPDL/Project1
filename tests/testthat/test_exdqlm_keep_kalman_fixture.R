`%||%` <- function(x, y) if (is.null(x)) y else x

testthat::test_that("ragged keep Kalman fixture validates compiled and reference paths", {
  repo_root <- normalizePath(testthat::test_path("..", ".."), mustWork = TRUE)
  script <- testthat::test_path(
    "..",
    "..",
    "repro",
    "audits",
    "run_exdqlm_keep_kalman_fixture.R"
  )
  testthat::skip_if_not(file.exists(script))
  testthat::skip_if_not(requireNamespace("Rcpp", quietly = TRUE))
  script_abs <- normalizePath(script, mustWork = TRUE)

  out_dir <- file.path(tempdir(), "kalman_fixture")
  oldwd <- getwd()
  setwd(repo_root)
  on.exit(setwd(oldwd), add = TRUE)
  result <- system2(
    "Rscript",
    c("--vanilla", script_abs, out_dir),
    stdout = TRUE,
    stderr = TRUE
  )
  testthat::expect_equal(attr(result, "status") %||% 0L, 0L)

  checks <- read.csv(file.path(out_dir, "kalman_fixture_checks.csv"))
  testthat::expect_true(all(checks$pass))
  testthat::expect_true(any(checks$check == "forecast_smoothed_mean_max_abs_diff"))
  testthat::expect_equal(
    checks$value[checks$check == "retained_transfer_dim"],
    1
  )

  segments <- read.csv(file.path(out_dir, "kalman_fixture_segments.csv"))
  testthat::expect_equal(segments$active_sources, c(2L, 1L))
  testthat::expect_equal(segments$state_dim, c(4L, 3L))
  testthat::expect_equal(segments$horizon, c(2L, 3L))
})
