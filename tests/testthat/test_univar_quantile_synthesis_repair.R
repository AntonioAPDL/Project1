source(testthat::test_path("..", "..", "R", "environmetrics", "utils_data.R"))
source(testthat::test_path("..", "..", "R", "environmetrics", "02_helpers_core.R"))

test_that("quantile curve helper extracts row-specific target quantiles", {
  cube <- array(NA_real_, dim = c(3L, 4L, 2L))
  cube[1, , 1] <- c(1, 2, 3, 4)
  cube[2, , 1] <- c(3, 4, 5, 6)
  cube[3, , 1] <- c(5, 6, 7, 8)
  cube[1, , 2] <- c(2, 3, 4, 5)
  cube[2, , 2] <- c(4, 5, 6, 7)
  cube[3, , 2] <- c(6, 7, 8, 9)

  q_probs <- c(0.1, 0.5, 0.9)
  out <- post_quantile_curve_from_sample_cube(cube, q_probs, context = "ut.curve")

  expect_equal(dim(out), c(3L, 2L))
  expect_true(all(is.finite(out)))
  expect_true(all(out[1, ] <= out[2, ]))
  expect_true(all(out[2, ] <= out[3, ]))
})

test_that("curve-level crossing summary flags genuine curve crossing", {
  q_curve <- rbind(
    c(0, 0, 0),
    c(-1, 1, 2),
    c(2, 2, 3)
  )
  out <- post_quantile_curve_crossing_summary(
    q_curve = q_curve,
    q_probs = c(0.05, 0.5, 0.95),
    context = "ut.curve.cross"
  )

  expect_equal(out$per_time$has_crossing[[1]], 1L)
  expect_equal(out$per_time$has_crossing[[2]], 0L)
  expect_equal(out$summary$n_times_with_crossing[[1]], 1L)
})

test_that("long-value helper preserves lead-major quantile ordering", {
  q_curve <- rbind(
    c(1, 2),
    c(10, 20),
    c(100, 200)
  )
  vals <- post_quantile_curve_long_values(
    q_curve,
    q_probs = c(0.05, 0.5, 0.95),
    context = "ut.curve.long"
  )
  expect_equal(vals, c(1, 10, 100, 2, 20, 200))
})

test_that("exdqlm synthesis repair enforces monotone anchor and empirical quantiles", {
  skip_if_not_installed("exdqlm")

  set.seed(42)
  cube <- array(NA_real_, dim = c(3L, 400L, 6L))
  for (h in seq_len(dim(cube)[3])) {
    cube[1, , h] <- seq(0.0, 0.6, length.out = 400L) + 0.05 * h
    cube[2, , h] <- seq(0.8, 1.4, length.out = 400L) + 0.05 * h
    cube[3, , h] <- seq(1.8, 2.4, length.out = 400L) + 0.05 * h
  }
  cube[2, , 3] <- seq(3.0, 3.2, length.out = 400L)
  cube[3, , 3] <- seq(2.0, 2.1, length.out = 400L)

  raw_curve <- post_quantile_curve_from_sample_cube(
    cube,
    q_probs = c(0.05, 0.5, 0.95),
    context = "ut.raw"
  )
  expect_true(any(apply(raw_curve, 2L, function(x) any(diff(x) < 0))))

  syn <- post_exdqlm_synthesize_from_sample_cube(
    sample_cube = cube,
    q_probs = c(0.05, 0.5, 0.95),
    n_samp = 300L,
    seed = 99L,
    context = "ut.synth"
  )

  expect_equal(dim(syn$draws), c(300L, 6L))
  expect_equal(dim(syn$anchor_quantiles), c(3L, 6L))
  expect_equal(dim(syn$empirical_quantiles), c(3L, 6L))
  expect_true(all(is.finite(syn$draws)))
  expect_true(all(apply(syn$anchor_quantiles, 2L, function(x) all(diff(x) >= -1e-10))))
  expect_true(all(apply(syn$empirical_quantiles, 2L, function(x) all(diff(x) >= -1e-10))))
})

test_that("local exdqlm repo synthesis matches installed package output", {
  skip_if_not_installed("exdqlm")
  repo_fun_path <- "/data/muscat_data/jaguir26/exdqlm/R/exdqlm_synthesize_from_draws.R"
  skip_if_not(file.exists(repo_fun_path), "local exdqlm repo source is unavailable")

  repo_env <- new.env(parent = globalenv())
  source(repo_fun_path, local = repo_env)
  expect_true(exists("exdqlm_synthesize_from_draws", envir = repo_env, inherits = FALSE))

  set.seed(20260325)
  draws_list <- list(
    matrix(rnorm(60L * 80L, mean = 0.0, sd = 0.3), nrow = 60L, ncol = 80L),
    matrix(rnorm(60L * 90L, mean = 0.2, sd = 0.25), nrow = 60L, ncol = 90L),
    matrix(rnorm(60L * 70L, mean = 0.5, sd = 0.2), nrow = 60L, ncol = 70L)
  )
  probs <- c(0.05, 0.5, 0.95)

  set.seed(314159)
  pkg_out <- exdqlm::exdqlm_synthesize_from_draws(
    draws_list,
    p = probs,
    enforce_isotonic = TRUE,
    rearrange = TRUE,
    grid_M = 201L,
    n_samp = 120L,
    seed = 2718L,
    T_expected = 60L
  )

  set.seed(314159)
  repo_out <- repo_env$exdqlm_synthesize_from_draws(
    draws_list,
    p = probs,
    enforce_isotonic = TRUE,
    rearrange = TRUE,
    grid_M = 201L,
    n_samp = 120L,
    seed = 2718L,
    T_expected = 60L
  )

  expect_equal(repo_out$levels, pkg_out$levels)
  expect_equal(repo_out$quantiles, pkg_out$quantiles, tolerance = 1e-12)
  expect_equal(repo_out$draws, pkg_out$draws, tolerance = 1e-12)
})
