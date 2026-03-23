source(testthat::test_path("..", "..", "R", "unified", "families", "ndlm_main", "00_constants.R"))
source(testthat::test_path("..", "..", "R", "unified", "families", "ndlm_main", "03_vb_updates.R"))

test_that("NDLM ragged horizon metadata is derived correctly for glofas extension", {
  meta <- ndlm_theory_build_ragged_horizon(
    list(K_vec = c(nws = 10L, glofas = 28L))
  )

  expect_equal(meta$K_overlap, 10L)
  expect_equal(meta$K_max, 28L)
  expect_equal(meta$K_tail, 18L)
  expect_equal(meta$extension_source, "glofas")
  expect_equal(meta$bridge_source, "nws")
  expect_equal(meta$segment_lengths[["overlap"]], 10L)
  expect_equal(meta$segment_lengths[["extension"]], 18L)
  expect_equal(length(meta$active_sources), 28L)
  expect_equal(length(meta$active_sources[[1L]]), 2L)
  expect_equal(length(meta$active_sources[[28L]]), 1L)
})

test_that("NDLM ragged horizon metadata is derived correctly for nws extension", {
  meta <- ndlm_theory_build_ragged_horizon(
    list(K_vec = c(nws = 21L, glofas = 12L))
  )

  expect_equal(meta$K_overlap, 12L)
  expect_equal(meta$K_max, 21L)
  expect_equal(meta$K_tail, 9L)
  expect_equal(meta$extension_source, "nws")
  expect_equal(meta$bridge_source, "glofas")
})

test_that("NDLM ragged horizon rejects invalid K_vec", {
  expect_error(
    ndlm_theory_build_ragged_horizon(list(K_vec = c(nws = 0L, glofas = 10L))),
    "requires positive K_vec"
  )
  expect_error(
    ndlm_theory_build_ragged_horizon(list(K_vec = c(nws = NA_integer_, glofas = 10L))),
    "requires positive K_vec"
  )
})

test_that("NDLM segment covariance supports inactive rows", {
  constants <- list(
    df_t = 0.95,
    df_s1 = 0.98,
    df_s2 = 0.98,
    df_s67 = 0.98,
    df_discrep = 0.98,
    lambda = 0.99
  )
  cov_arr <- ndlm_theory_alloc_segment_cov(
    k_len = 4L,
    constants = constants,
    base_cov = diag(0.2, 7L),
    inactive_row = 2L,
    start_k = 1L
  )
  expect_equal(dim(cov_arr), c(7L, 7L, 4L))
  expect_true(all(cov_arr[2, 2, ] < 1e-6))
  expect_true(all(cov_arr[1, 1, ] >= cov_arr[2, 2, ]))
})

test_that("NDLM safe chol repairs indefinite covariance matrices", {
  S <- matrix(c(
    2.0, 3.2, 0.5,
    3.2, 2.0, 0.1,
    0.5, 0.1, 0.2
  ), nrow = 3, byrow = TRUE)
  expect_error(chol(S + diag(1e-8, 3)))
  L <- ndlm_theory_safe_chol(S)
  expect_equal(dim(L), c(3L, 3L))
  expect_true(all(is.finite(L)))
})

test_that("NDLM covariance diagnostics summarize slice validity", {
  good <- array(0, dim = c(4, 4, 2))
  good[, , 1] <- diag(c(0.2, 0.3, 0.25, 0.4))
  good[, , 2] <- diag(c(0.1, 0.2, 0.15, 0.35))
  bad <- array(0, dim = c(4, 4, 1))
  bad[, , 1] <- matrix(c(
    1.0, 2.0, 0.0, 0.0,
    2.0, 1.0, 0.0, 0.0,
    0.0, 0.0, 0.5, 0.0,
    0.0, 0.0, 0.0, 0.5
  ), nrow = 4, byrow = TRUE)

  out <- ndlm_theory_collect_covariance_diagnostics(good, bad, good)
  expect_true(is.data.frame(out))
  expect_equal(nrow(out), 3L)
  expect_true(all(c("object", "min_eig_min", "base_chol_fail_slices") %in% names(out)))
  row_bad <- out[out$object == "forecast_cov_segment_1", , drop = FALSE]
  expect_true(nrow(row_bad) == 1L)
  expect_true(row_bad$base_chol_fail_slices[[1L]] >= 1L)
})

test_that("NDLM constants normalize forecast transfer mode", {
  old_mode <- Sys.getenv("NDLM_FORECAST_TRANSFER_MODE", unset = "")
  on.exit(Sys.setenv(NDLM_FORECAST_TRANSFER_MODE = old_mode), add = TRUE)

  Sys.setenv(NDLM_FORECAST_TRANSFER_MODE = "drop")
  constants <- ndlm_theory_constants(seed = 123L)
  expect_equal(constants$forecast_transfer_mode, "drop")

  Sys.setenv(NDLM_FORECAST_TRANSFER_MODE = "BAD")
  constants_bad <- ndlm_theory_constants(seed = 123L)
  expect_equal(constants_bad$forecast_transfer_mode, "keep")
})

test_that("NDLM local covariance stabilization enforces eigen floor/cap", {
  constants <- ndlm_theory_constants(seed = 777L)
  constants$stabilization$cov_eig_floor <- 1e-5
  constants$stabilization$cov_eig_cap <- 5
  constants$stabilization$cov_diag_jitter <- 0

  S <- matrix(c(
    9, 7, 0,
    7, 2, 0,
    0, 0, 100
  ), nrow = 3, byrow = TRUE)
  out <- ndlm_theory_stabilize_covariance_local(S, constants = constants)
  eigs <- eigen(out$cov, symmetric = TRUE, only.values = TRUE)$values

  expect_true(is.list(out$stats))
  expect_true(as.integer(out$stats$cov_projected) >= 1L)
  expect_true(min(eigs) >= 1e-5 - 1e-9)
  expect_true(max(eigs) <= 5 + 1e-6)
})

test_that("NDLM segment covariance reports stabilization stats", {
  constants <- ndlm_theory_constants(seed = 777L)
  constants$stabilization$cov_eig_floor <- 1e-6
  constants$stabilization$cov_eig_cap <- 1
  constants$stabilization$cov_diag_jitter <- 1e-10

  cov_arr <- ndlm_theory_alloc_segment_cov(
    k_len = 3L,
    constants = constants,
    base_cov = diag(c(10, 9, 8, 7, 6, 5, 4), 7L),
    inactive_row = integer(0),
    start_k = 1L
  )
  stats <- attr(cov_arr, "stabilization_stats")
  expect_true(is.list(stats))
  expect_true(as.integer(stats$calls) >= 1L)
  expect_true(as.integer(stats$cov_cap_clipped) >= 1L)
})
