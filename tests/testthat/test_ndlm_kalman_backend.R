source(testthat::test_path("..", "..", "R", "unified", "families", "ndlm_main", "02_model_spec.R"))

test_that("ndlm kalman backend normalize enforces allowed values", {
  expect_equal(ndlm_theory_kalman_backend_normalize("r"), "r")
  expect_equal(ndlm_theory_kalman_backend_normalize("cpp"), "cpp")
  expect_error(
    ndlm_theory_kalman_backend_normalize("bad"),
    "must be one of: r, cpp"
  )
})

test_that("ndlm kalman smoother r and cpp backends are numerically consistent", {
  set.seed(777)
  Tn <- 80L
  d <- 6L
  H <- matrix(rnorm(Tn * d), nrow = Tn, ncol = d)
  y <- rnorm(Tn)
  R_vec <- rep(0.5, Tn)
  q_diag <- rep(0.1, d)
  m0 <- rep(0, d)
  C0 <- diag(d)

  out_r <- ndlm_theory_kalman_smoother(
    y = y,
    H_mat = H,
    R_vec = R_vec,
    q_diag = q_diag,
    m0 = m0,
    C0 = C0,
    backend = "r"
  )
  out_cpp <- ndlm_theory_kalman_smoother(
    y = y,
    H_mat = H,
    R_vec = R_vec,
    q_diag = q_diag,
    m0 = m0,
    C0 = C0,
    backend = "cpp"
  )

  expect_equal(dim(out_r$smooth_mean), dim(out_cpp$smooth_mean))
  expect_equal(dim(out_r$smooth_cov), dim(out_cpp$smooth_cov))
  expect_equal(length(out_r$predicted_mean), length(out_cpp$predicted_mean))
  expect_equal(length(out_r$predicted_var), length(out_cpp$predicted_var))
  expect_equal(length(out_r$filtered_mean), length(out_cpp$filtered_mean))
  expect_equal(length(out_r$filtered_var), length(out_cpp$filtered_var))
  expect_equal(length(out_r$smoothed_mean), length(out_cpp$smoothed_mean))
  expect_equal(length(out_r$smoothed_var), length(out_cpp$smoothed_var))
  expect_equal(length(out_r$fitted_mean), length(out_cpp$fitted_mean))
  expect_equal(length(out_r$fitted_var), length(out_cpp$fitted_var))

  expect_equal(as.numeric(out_cpp$predicted_mean), as.numeric(out_r$predicted_mean), tolerance = 1e-7)
  expect_equal(as.numeric(out_cpp$predicted_var), as.numeric(out_r$predicted_var), tolerance = 1e-7)
  expect_equal(as.numeric(out_cpp$filtered_mean), as.numeric(out_r$filtered_mean), tolerance = 1e-7)
  expect_equal(as.numeric(out_cpp$filtered_var), as.numeric(out_r$filtered_var), tolerance = 1e-7)
  expect_equal(as.numeric(out_cpp$smoothed_mean), as.numeric(out_r$smoothed_mean), tolerance = 1e-7)
  expect_equal(as.numeric(out_cpp$smoothed_var), as.numeric(out_r$smoothed_var), tolerance = 1e-7)
  expect_equal(as.numeric(out_cpp$fitted_mean), as.numeric(out_r$fitted_mean), tolerance = 1e-7)
  expect_equal(as.numeric(out_cpp$fitted_var), as.numeric(out_r$fitted_var), tolerance = 1e-7)
  expect_equal(as.numeric(out_cpp$smooth_mean), as.numeric(out_r$smooth_mean), tolerance = 1e-6)
})

test_that("ndlm kalman smoother discount path matches between r and cpp", {
  set.seed(778)
  Tn <- 60L
  d <- 8L
  H <- matrix(rnorm(Tn * d), nrow = Tn, ncol = d)
  y <- rnorm(Tn)
  R_vec <- rep(0.7, Tn)
  q_diag <- rep(1e-8, d)
  m0 <- rep(0, d)
  C0 <- diag(d)
  df_mat <- matrix(0, d, d)
  df_mat[1:4, 1:4] <- 0.03
  df_mat[5:8, 5:8] <- 0.02
  diag(df_mat) <- c(rep(0.05, 4), rep(0.03, 4))

  out_r <- ndlm_theory_kalman_smoother(
    y = y,
    H_mat = H,
    R_vec = R_vec,
    q_diag = q_diag,
    df_mat = df_mat,
    m0 = m0,
    C0 = C0,
    backend = "r"
  )
  out_cpp <- ndlm_theory_kalman_smoother(
    y = y,
    H_mat = H,
    R_vec = R_vec,
    q_diag = q_diag,
    df_mat = df_mat,
    m0 = m0,
    C0 = C0,
    backend = "cpp"
  )

  expect_equal(as.numeric(out_cpp$fitted_mean), as.numeric(out_r$fitted_mean), tolerance = 1e-7)
  expect_equal(as.numeric(out_cpp$fitted_var), as.numeric(out_r$fitted_var), tolerance = 1e-7)
  expect_equal(as.numeric(out_cpp$predicted_mean), as.numeric(out_r$predicted_mean), tolerance = 1e-7)
  expect_equal(as.numeric(out_cpp$filtered_mean), as.numeric(out_r$filtered_mean), tolerance = 1e-7)
  expect_equal(as.numeric(out_cpp$smoothed_mean), as.numeric(out_r$smoothed_mean), tolerance = 1e-7)
  expect_equal(as.numeric(out_cpp$smooth_mean), as.numeric(out_r$smooth_mean), tolerance = 1e-6)
})

test_that("ndlm kalman smoother exposes stabilization metadata and repairs covariance", {
  set.seed(779)
  Tn <- 40L
  d <- 4L
  H <- matrix(rnorm(Tn * d), nrow = Tn, ncol = d)
  y <- rnorm(Tn)
  R_vec <- rep(0.25, Tn)
  q_diag <- rep(0.05, d)
  m0 <- rep(0, d)
  C0 <- matrix(c(
    2.0, 5.0, 0.0, 0.0,
    5.0, 1.0, 0.0, 0.0,
    0.0, 0.0, 50.0, 0.0,
    0.0, 0.0, 0.0, 30.0
  ), nrow = d, byrow = TRUE)

  out <- ndlm_theory_kalman_smoother(
    y = y,
    H_mat = H,
    R_vec = R_vec,
    q_diag = q_diag,
    m0 = m0,
    C0 = C0,
    backend = "r",
    stabilization = list(
      cov_eig_floor = 1e-6,
      cov_eig_cap = 10,
      cov_diag_jitter = 1e-10
    )
  )

  expect_true(is.list(out$stabilization))
  expect_true(as.integer(out$stabilization$calls) > 0L)
  expect_true(as.integer(out$stabilization$cov_projected) > 0L)
  mins <- vapply(
    seq_len(dim(out$smooth_cov)[3]),
    function(k) min(eigen(out$smooth_cov[, , k], symmetric = TRUE, only.values = TRUE)$values),
    numeric(1)
  )
  expect_true(all(is.finite(mins)))
  expect_true(min(mins) >= -1e-8)
})
