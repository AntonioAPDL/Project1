source(testthat::test_path('..', '..', 'R', 'unified', 'families', 'ndlm_main', '02_model_spec.R'))

test_that('ndlm time-varying Kalman smoother r and cpp backends agree', {
  set.seed(101)
  y_list <- list(rnorm(2), rnorm(1), numeric(0), rnorm(3))
  H_list <- list(
    matrix(rnorm(6), nrow = 2, ncol = 3),
    matrix(rnorm(4), nrow = 1, ncol = 4),
    matrix(numeric(0), nrow = 0, ncol = 2),
    matrix(rnorm(9), nrow = 3, ncol = 3)
  )
  R_list <- list(c(0.4, 0.6), 0.5, numeric(0), c(0.3, 0.5, 0.7))
  G_list <- list(
    NULL,
    matrix(rnorm(12), nrow = 4, ncol = 3),
    matrix(rnorm(8), nrow = 2, ncol = 4),
    matrix(rnorm(6), nrow = 3, ncol = 2)
  )
  Q_list <- list(
    NULL,
    diag(c(0.2, 0.3, 0.4, 0.5)),
    diag(c(0.25, 0.35)),
    diag(c(0.15, 0.25, 0.45))
  )
  m0 <- c(0, 0, 0)
  C0 <- diag(3)

  out_r <- ndlm_theory_tv_kalman_smoother(
    y_list = y_list,
    H_list = H_list,
    R_list = R_list,
    G_list = G_list,
    Q_list = Q_list,
    m0 = m0,
    C0 = C0,
    backend = 'r'
  )
  out_cpp <- ndlm_theory_tv_kalman_smoother(
    y_list = y_list,
    H_list = H_list,
    R_list = R_list,
    G_list = G_list,
    Q_list = Q_list,
    m0 = m0,
    C0 = C0,
    backend = 'cpp'
  )

  expect_equal(as.integer(out_r$state_dim), as.integer(out_cpp$state_dim))
  expect_equal(length(out_r$smooth_mean), length(out_cpp$smooth_mean))
  expect_equal(length(out_r$lag_cov_next), length(out_cpp$lag_cov_next))

  for (tt in seq_along(out_r$smooth_mean)) {
    expect_equal(as.numeric(out_cpp$pred_mean[[tt]]), as.numeric(out_r$pred_mean[[tt]]), tolerance = 1e-6)
    expect_equal(as.numeric(out_cpp$filter_mean[[tt]]), as.numeric(out_r$filter_mean[[tt]]), tolerance = 1e-6)
    expect_equal(as.numeric(out_cpp$smooth_mean[[tt]]), as.numeric(out_r$smooth_mean[[tt]]), tolerance = 1e-6)
    expect_equal(as.numeric(out_cpp$pred_cov[[tt]]), as.numeric(out_r$pred_cov[[tt]]), tolerance = 1e-6)
    expect_equal(as.numeric(out_cpp$filter_cov[[tt]]), as.numeric(out_r$filter_cov[[tt]]), tolerance = 1e-6)
    expect_equal(as.numeric(out_cpp$smooth_cov[[tt]]), as.numeric(out_r$smooth_cov[[tt]]), tolerance = 1e-6)
    if (tt < length(out_r$lag_cov_next)) {
      expect_equal(as.numeric(out_cpp$lag_cov_next[[tt]]), as.numeric(out_r$lag_cov_next[[tt]]), tolerance = 1e-6)
    }
  }
})
