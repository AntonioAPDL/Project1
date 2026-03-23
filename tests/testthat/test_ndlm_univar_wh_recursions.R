source(testthat::test_path("..", "..", "R", "unified", "families", "ndlm_univar", "00_constants.R"))
source(testthat::test_path("..", "..", "R", "unified", "families", "ndlm_univar", "02_model_spec.R"))
source(testthat::test_path("..", "..", "R", "unified", "families", "ndlm_univar", "03_filter_forecast_fit.R"))

test_that("ndlm_univar filter step matches West-Harrison scalar recursion", {
  out <- ndlm_univar_filter_step(
    F_t = 1,
    G_t = matrix(1, 1, 1),
    W_star_t = matrix(0.2, 1, 1),
    y_t = 1.2,
    m_prev = 0.5,
    C_prev_star = matrix(0.4, 1, 1),
    n_prev = 10,
    S_prev = 2,
    backend = "r"
  )

  expect_equal(as.numeric(out$a), 0.5, tolerance = 1e-8)
  expect_equal(as.numeric(out$R_star), 0.6, tolerance = 1e-8)
  expect_equal(as.numeric(out$f), 0.5, tolerance = 1e-8)
  expect_equal(as.numeric(out$Q_star), 1.6, tolerance = 1e-8)
  expect_equal(as.numeric(out$e), 0.7, tolerance = 1e-8)
  expect_equal(as.numeric(out$A), 0.375, tolerance = 1e-8)
  expect_equal(as.numeric(out$m), 0.7625, tolerance = 1e-8)
  expect_equal(as.numeric(out$C_star), 0.375, tolerance = 1e-8)
  expect_equal(as.numeric(out$n), 11, tolerance = 1e-8)
  expect_equal(as.numeric(out$S), (10 * 2 + (0.7^2) / 1.6) / 11, tolerance = 1e-8)
})

test_that("ndlm_univar h-step forecast recursion matches closed-form scalar propagation", {
  out <- ndlm_univar_forecast_h(
    F_future = matrix(c(1, 1, 1), ncol = 1),
    G_future = array(rep(1.1, 3), dim = c(1, 1, 3)),
    W_star_future = array(rep(0.05, 3), dim = c(1, 1, 3)),
    m_t = 0.2,
    C_t_star = matrix(0.3, 1, 1),
    n_t = 15,
    S_t = 1.7,
    backend = "r"
  )

  a1 <- 1.1 * 0.2
  a2 <- 1.1 * a1
  a3 <- 1.1 * a2
  R1 <- 1.1^2 * 0.3 + 0.05
  R2 <- 1.1^2 * R1 + 0.05
  R3 <- 1.1^2 * R2 + 0.05

  expect_equal(as.numeric(out$a[, 2]), a1, tolerance = 1e-8)
  expect_equal(as.numeric(out$a[, 3]), a2, tolerance = 1e-8)
  expect_equal(as.numeric(out$a[, 4]), a3, tolerance = 1e-8)
  expect_equal(as.numeric(out$R_star[, , 2]), R1, tolerance = 1e-8)
  expect_equal(as.numeric(out$R_star[, , 3]), R2, tolerance = 1e-8)
  expect_equal(as.numeric(out$R_star[, , 4]), R3, tolerance = 1e-8)
  expect_equal(as.numeric(out$f[1]), a1, tolerance = 1e-8)
  expect_equal(as.numeric(out$Q_star[1]), 1 + R1, tolerance = 1e-8)
  expect_equal(as.numeric(out$Q_scale[1]), 1.7 * (1 + R1), tolerance = 1e-8)
})

test_that("ndlm_univar backward smoother matches scalar RTS / WH recursion", {
  m_mat <- matrix(c(0.4, 0.9), nrow = 1)
  a_mat <- matrix(c(0.3, 0.8), nrow = 1)
  C_star_cube <- array(c(0.5, 0.2), dim = c(1, 1, 2))
  R_star_cube <- array(c(0.8, 0.3), dim = c(1, 1, 2))
  G_array <- array(c(1.0, 0.9), dim = c(1, 1, 2))

  out <- ndlm_univar_backward_smoother(
    m_mat = m_mat,
    C_star_cube = C_star_cube,
    a_mat = a_mat,
    R_star_cube = R_star_cube,
    G_array = G_array,
    n_T = 30,
    S_T = 1.2,
    backend = "r"
  )

  B1 <- 0.5 * 0.9 / 0.3
  a1_s <- 0.4 + B1 * (0.9 - 0.8)
  R1_s <- 0.5 + B1 * (0.2 - 0.3) * B1

  expect_equal(as.numeric(out$a_smooth[, 2]), 0.9, tolerance = 1e-8)
  expect_equal(as.numeric(out$R_smooth_star[, , 2]), 0.2, tolerance = 1e-8)
  expect_equal(as.numeric(out$a_smooth[, 1]), a1_s, tolerance = 1e-8)
  expect_equal(as.numeric(out$R_smooth_star[, , 1]), R1_s, tolerance = 1e-8)
  expect_equal(as.numeric(out$R_smooth_scale[, , 1]), 1.2 * R1_s, tolerance = 1e-8)
})

test_that("ndlm_univar r and cpp backends agree on forward/forecast/smoother outputs", {
  set.seed(8123)
  Tn <- 64L
  p <- 5L
  H <- 12L

  y <- rnorm(Tn)
  F_mat <- matrix(rnorm(Tn * p), nrow = Tn, ncol = p)
  F_future <- matrix(rnorm(H * p), nrow = H, ncol = p)
  G_array <- array(0, dim = c(p, p, Tn))
  G_future <- array(0, dim = c(p, p, H))
  for (tt in seq_len(Tn)) G_array[, , tt] <- diag(p) + matrix(rnorm(p * p, sd = 0.02), p, p)
  for (hh in seq_len(H)) G_future[, , hh] <- diag(p) + matrix(rnorm(p * p, sd = 0.02), p, p)

  discount_mat <- diag(seq(0.01, 0.03, length.out = p), p)
  m0 <- rep(0, p)
  C0_star <- diag(0.5, p)
  n0 <- 25
  S0 <- 0.8
  stab <- list(cov_eig_floor = 1e-8, cov_eig_cap = 1e6, cov_diag_jitter = 1e-10)

  fr <- ndlm_univar_filter_forward(
    y = y,
    F_mat = F_mat,
    G_array = G_array,
    W_star_array = NULL,
    discount_mat = discount_mat,
    m0 = m0,
    C0_star = C0_star,
    n0 = n0,
    S0 = S0,
    backend = "r",
    stabilization = stab
  )
  fc <- ndlm_univar_filter_forward(
    y = y,
    F_mat = F_mat,
    G_array = G_array,
    W_star_array = NULL,
    discount_mat = discount_mat,
    m0 = m0,
    C0_star = C0_star,
    n0 = n0,
    S0 = S0,
    backend = "cpp",
    stabilization = stab
  )

  expect_equal(as.numeric(fc$f), as.numeric(fr$f), tolerance = 1e-6)
  expect_equal(as.numeric(fc$Q_star), as.numeric(fr$Q_star), tolerance = 1e-6)
  expect_equal(as.numeric(fc$e), as.numeric(fr$e), tolerance = 1e-6)
  expect_equal(as.numeric(fc$m), as.numeric(fr$m), tolerance = 1e-5)
  expect_equal(as.numeric(fc$C_star), as.numeric(fr$C_star), tolerance = 1e-5)

  for_r <- ndlm_univar_forecast_h(
    F_future = F_future,
    G_future = G_future,
    W_star_future = NULL,
    discount_mat = discount_mat,
    m_t = fr$m[, Tn],
    C_t_star = fr$C_star[, , Tn],
    n_t = fr$n[Tn],
    S_t = fr$S[Tn],
    backend = "r",
    stabilization = stab
  )
  for_c <- ndlm_univar_forecast_h(
    F_future = F_future,
    G_future = G_future,
    W_star_future = NULL,
    discount_mat = discount_mat,
    m_t = fc$m[, Tn],
    C_t_star = fc$C_star[, , Tn],
    n_t = fc$n[Tn],
    S_t = fc$S[Tn],
    backend = "cpp",
    stabilization = stab
  )

  expect_equal(as.numeric(for_c$f), as.numeric(for_r$f), tolerance = 1e-5)
  expect_equal(as.numeric(for_c$Q_star), as.numeric(for_r$Q_star), tolerance = 1e-5)
  expect_equal(as.numeric(for_c$R_star), as.numeric(for_r$R_star), tolerance = 1e-5)

  sm_r <- ndlm_univar_backward_smoother(
    m_mat = fr$m,
    C_star_cube = fr$C_star,
    a_mat = fr$a,
    R_star_cube = fr$R_star,
    G_array = G_array,
    n_T = fr$n[Tn],
    S_T = fr$S[Tn],
    backend = "r",
    stabilization = stab
  )
  sm_c <- ndlm_univar_backward_smoother(
    m_mat = fc$m,
    C_star_cube = fc$C_star,
    a_mat = fc$a,
    R_star_cube = fc$R_star,
    G_array = G_array,
    n_T = fc$n[Tn],
    S_T = fc$S[Tn],
    backend = "cpp",
    stabilization = stab
  )

  expect_equal(as.numeric(sm_c$a_smooth), as.numeric(sm_r$a_smooth), tolerance = 1e-5)
  expect_equal(as.numeric(sm_c$R_smooth_star), as.numeric(sm_r$R_smooth_star), tolerance = 1e-5)
})

test_that("ndlm_univar Student-t samplers return expected shapes and finite values", {
  set.seed(444)
  p <- 4L
  Tn <- 20L
  n_draws <- 32L
  means <- matrix(rnorm(p * Tn), nrow = p, ncol = Tn)
  cov_arr <- array(0, dim = c(p, p, Tn))
  for (tt in seq_len(Tn)) {
    M <- matrix(rnorm(p * p), p, p)
    cov_arr[, , tt] <- crossprod(M) + diag(0.1, p)
  }

  draws <- ndlm_univar_draw_state_t(
    mean_mat = means,
    scale_cov_arr = cov_arr,
    df = 20,
    n_draws = n_draws,
    seed = 701
  )
  expect_equal(dim(draws), c(p, Tn, n_draws))
  expect_true(all(is.finite(draws)))

  seg <- ndlm_univar_draw_segment_t(
    mean_mat = means[, 1:7, drop = FALSE],
    scale_cov_arr = cov_arr[, , 1:7, drop = FALSE],
    df = 20,
    n_draws = n_draws,
    seed = 702
  )
  expect_equal(dim(seg), c(p, 7L, n_draws))
  expect_true(all(is.finite(seg)))
})

test_that("ndlm_univar covariance array hardening enforces PSD floor", {
  p <- 3L
  arr <- array(0, dim = c(p, p, 2L))
  arr[, , 1] <- matrix(c(1, 0.2, 0.1, 0.2, 0.8, -0.1, 0.1, -0.1, 0.6), nrow = p, byrow = TRUE)
  arr[, , 2] <- matrix(c(1, 0.9999999999, 0, 0.9999999999, 1, 0, 0, 0, -1e-12), nrow = p, byrow = TRUE)
  arr[, , 2] <- (arr[, , 2] + t(arr[, , 2])) / 2

  stab <- list(cov_eig_floor = 1e-8, cov_eig_cap = 1e8, cov_diag_jitter = 1e-10)
  out <- ndlm_univar_cov_stabilize_array(arr, stabilization = stab)

  mins <- vapply(seq_len(dim(out)[3]), function(k) {
    min(eigen(out[, , k], symmetric = TRUE, only.values = TRUE)$values)
  }, numeric(1))
  expect_true(all(is.finite(mins)))
  expect_true(all(mins >= 1e-8 - 1e-12))
})
