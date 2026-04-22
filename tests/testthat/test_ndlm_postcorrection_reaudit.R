source(testthat::test_path("..", "..", "R", "environmetrics", "02_helpers_core.R"))
source(testthat::test_path("..", "..", "R", "unified", "families", "ndlm_main", "02_model_spec.R"))
source(testthat::test_path("..", "..", "R", "unified", "families", "exdqlm_univar", "02_model_spec.R"))

test_that("post_ndlm_predictive_draws uses USGS sigma row for multivariate NDLM sigma matrices", {
  ndlm_raw <- matrix(
    c(
      0.5, 0.7, 0.6,
      0.4, 0.6, 0.5,
      0.3, 0.5, 0.4,
      0.2, 0.4, 0.3
    ),
    nrow = 4,
    byrow = TRUE
  )
  sigma_draws <- rbind(
    usgs = c(0.01, 0.02, 0.03, 0.04),
    nws = c(1.0, 1.1, 1.2, 1.3),
    glofas = c(8.0, 8.1, 8.2, 8.3)
  )

  out <- post_ndlm_predictive_draws(
    ndlm_raw = ndlm_raw,
    sigma_draws = sigma_draws,
    context = "test.ndlm.post",
    seed = 777L
  )

  expect_identical(out$sigma_source_used, "matrix_row_usgs")
  expect_equal(out$sigma_sd, sqrt(as.numeric(sigma_draws["usgs", ])))
  expect_true(max(out$predictive_log1p) < 5)
})

test_that("NDLM Gaussian smoother matches univariate Gaussian backbone when discounting is disabled", {
  y <- c(0.3, 0.5, 0.2, 0.6, 0.4)
  F_mat <- cbind(1, c(-0.2, 0.0, 0.1, 0.2, 0.3))
  R_vec <- rep(0.15, length(y))
  q_diag <- c(0.05, 0.02)
  m0 <- c(0.1, -0.1)
  C0 <- diag(c(0.5, 0.3), 2L)

  ndlm_out <- ndlm_theory_kalman_smoother_r(
    y = y,
    H_mat = F_mat,
    R_vec = R_vec,
    q_diag = q_diag,
    m0 = m0,
    C0 = C0,
    df_mat = NULL
  )
  univar_out <- univar_theory_kalman_smoother(
    y = y,
    F_mat = F_mat,
    R_vec = R_vec,
    q_diag = q_diag,
    m0 = m0,
    C0 = C0
  )

  expect_equal(ndlm_out$fitted_mean, univar_out$fitted_mean, tolerance = 1e-8)
  expect_equal(ndlm_out$smooth_mean, univar_out$smooth_mean, tolerance = 1e-8)
  expect_equal(ndlm_out$smooth_cov, univar_out$smooth_cov, tolerance = 1e-8)
  # NDLM fitted variance is an observation-scale quantity, so it includes R_vec.
  expect_equal(ndlm_out$fitted_var - R_vec, univar_out$fitted_var, tolerance = 1e-8)
})
