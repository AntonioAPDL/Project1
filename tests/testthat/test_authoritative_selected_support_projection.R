test_that("authoritative selected-support projection uses 2D covariance slices", {
  helper_path <- file.path("R", "environmetrics", "40_figures_multivar_only.R")
  if (!file.exists(helper_path)) {
    helper_path <- file.path("..", "..", helper_path)
  }
  lines <- readLines(helper_path, warn = FALSE)
  start <- grep("^authoritative_support_Ft <-", lines)
  end <- grep("^authoritative_support_observed_usgs <-", lines) - 1L
  testthat::expect_equal(length(start), 1L)
  testthat::expect_equal(length(end), 1L)
  env <- new.env(parent = globalenv())
  env$safe_get <- function(name, default = NULL) {
    if (exists(name, envir = env, inherits = FALSE)) get(name, envir = env, inherits = FALSE) else default
  }
  eval(parse(text = paste(lines[start:end], collapse = "\n")), envir = env)

  n_time <- 3L
  p <- 2L
  env$FF <- array(c(
    1, 0.5,
    1, 1.0,
    1, 1.5
  ), dim = c(p, 1L, n_time))
  theta_obj <- list(
    sm = matrix(c(
      1.0, 1.2, 1.4,
      0.1, 0.2, 0.3
    ), nrow = p, byrow = TRUE),
    sC = array(0, dim = c(p, p, n_time))
  )
  for (tt in seq_len(n_time)) {
    theta_obj$sC[, , tt] <- matrix(c(0.04, 0.01, 0.01, 0.09), nrow = p)
  }

  projected <- env$authoritative_support_project_theta(theta_obj)

  testthat::expect_s3_class(projected, "data.frame")
  testthat::expect_equal(nrow(projected), n_time)
  testthat::expect_true(all(is.finite(projected$mu_usgs)))
  testthat::expect_true(all(is.finite(projected$sd_usgs)))
  testthat::expect_equal(projected$mu_usgs, c(1.05, 1.4, 1.85), tolerance = 1e-12)
})
