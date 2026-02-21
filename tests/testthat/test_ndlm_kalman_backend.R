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
  expect_equal(length(out_r$fitted_mean), length(out_cpp$fitted_mean))
  expect_equal(length(out_r$fitted_var), length(out_cpp$fitted_var))

  expect_equal(as.numeric(out_cpp$fitted_mean), as.numeric(out_r$fitted_mean), tolerance = 1e-7)
  expect_equal(as.numeric(out_cpp$fitted_var), as.numeric(out_r$fitted_var), tolerance = 1e-7)
  expect_equal(as.numeric(out_cpp$smooth_mean), as.numeric(out_r$smooth_mean), tolerance = 1e-6)
})

