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

test_that("authoritative component support includes samplewise trend plus 80-month contract", {
  helper_path <- file.path("R", "environmetrics", "40_figures_multivar_only.R")
  if (!file.exists(helper_path)) {
    helper_path <- file.path("..", "..", helper_path)
  }
  lines <- readLines(helper_path, warn = FALSE)
  q_start <- grep("^safe_row_quantiles <-", lines)
  q_end <- grep("^resolve_future_truth_multivar <-", lines) - 1L
  c_start <- grep("^authoritative_support_samp_theta <-", lines)
  c_end <- grep("^build_authoritative_component_summary <-", lines) - 1L
  testthat::expect_equal(length(q_start), 1L)
  testthat::expect_equal(length(q_end), 1L)
  testthat::expect_equal(length(c_start), 1L)
  testthat::expect_equal(length(c_end), 1L)

  env <- new.env(parent = globalenv())
  env$safe_get <- function(name, default = NULL) {
    if (exists(name, envir = env, inherits = FALSE)) get(name, envir = env, inherits = FALSE) else default
  }
  eval(parse(text = paste(lines[q_start:q_end], collapse = "\n")), envir = env)
  eval(parse(text = paste(lines[c_start:c_end], collapse = "\n")), envir = env)

  arr <- array(0, dim = c(7L, 2L, 4L))
  arr[1L, 1L, ] <- c(1, 2, 3, 4)
  arr[6L, 1L, ] <- c(4, 3, 2, 1)
  arr[1L, 2L, ] <- c(10, 20, 30, 40)
  arr[6L, 2L, ] <- c(-5, 0, 5, 10)
  env$p <- 7L
  env$TT <- 2L
  env$dates_ts_usgs <- as.Date(c("2020-01-01", "2020-01-02"))
  assign("samp.theta_5_exAL_synth_DISC", list(samp_theta = arr), envir = env)

  out <- env$authoritative_support_component_summary_for_quantile(
    suffix = "5",
    label = "q05",
    probability = 0.05,
    probs = c(0.25, 0.5, 0.75)
  )

  samplewise <- out[out$component_contract == "component_6_plus_trend_component_1_samplewise", , drop = FALSE]
  legacy <- out[out$component_contract == "component_6_shifted_by_posterior_mean_trend_component_1", , drop = FALSE]
  testthat::expect_equal(nrow(samplewise), 2L)
  testthat::expect_equal(nrow(legacy), 2L)

  expected_t1 <- as.numeric(stats::quantile(arr[1L, 1L, ] + arr[6L, 1L, ], probs = c(0.25, 0.5, 0.75), type = 8, names = FALSE))
  expected_t2 <- as.numeric(stats::quantile(arr[1L, 2L, ] + arr[6L, 2L, ], probs = c(0.25, 0.5, 0.75), type = 8, names = FALSE))
  testthat::expect_equal(samplewise$lower_025, c(expected_t1[[1L]], expected_t2[[1L]]), tolerance = 1e-12)
  testthat::expect_equal(samplewise$median_500, c(expected_t1[[2L]], expected_t2[[2L]]), tolerance = 1e-12)
  testthat::expect_equal(samplewise$upper_975, c(expected_t1[[3L]], expected_t2[[3L]]), tolerance = 1e-12)
  testthat::expect_false(isTRUE(all.equal(samplewise$lower_025[[1L]], legacy$lower_025[[1L]], tolerance = 1e-12)))
})
