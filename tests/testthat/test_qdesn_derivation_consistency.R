source(file.path("..", "..", "R", "environmetrics", "qdesn_validation_math.R"))

test_that("multivariate mean and scale reduce to univariate at dimension 1", {
  set.seed(123)
  p0 <- 0.35

  for (rep_idx in 1:25) {
    h_t <- rnorm(1)
    alpha_t <- rnorm(1)
    sigma <- runif(1, min = 0.2, max = 2.0)

    # Keep gamma away from 0 and the boundaries to avoid degenerate checks.
    L <- qdesn_L_fn(p0)
    U <- qdesn_U_fn(p0)
    gamma <- runif(1, min = L * 0.75, max = U * 0.75)
    if (abs(gamma) < 0.05) {
      gamma <- sign(gamma + 1e-8) * 0.05
    }

    s_t <- runif(1, min = 0.01, max = 4.0)
    v_t <- runif(1, min = 0.01, max = 4.0)

    mu_uni <- qdesn_mu_univariate(h_t, alpha_t, sigma, gamma, s_t, v_t, p0)
    mu_multi <- qdesn_mu_multivariate(
      H_t = matrix(h_t, nrow = 1, ncol = 1),
      alpha_t = matrix(alpha_t, nrow = 1, ncol = 1),
      sigma = sigma,
      gamma = gamma,
      s_t = s_t,
      v_t = v_t,
      p0 = p0
    )

    O_uni <- as.numeric((sigma^2) * qdesn_B_fn(p0, gamma) * v_t)
    O_multi <- qdesn_obs_scale_diag(
      sigma = sigma,
      gamma = gamma,
      v_t = v_t,
      p0 = p0
    )

    expect_equal(mu_multi, mu_uni, tolerance = 1e-12)
    expect_equal(as.numeric(O_multi[1, 1]), O_uni, tolerance = 1e-12)
  }
})

test_that("chi update term is finite and strictly positive after clamp", {
  set.seed(456)
  d <- 20

  y <- rnorm(d)
  exps <- rnorm(d)
  exps2 <- exps^2 + rexp(d, rate = 2)
  sts <- rexp(d, rate = 1) + 0.01
  sts2 <- sts^2 + runif(d, min = 0, max = 0.2)

  invb_inv_sigma <- runif(d, min = 0.05, max = 2.0)
  c_invb_absgam <- runif(d, min = -1.0, max = 1.0)
  c2_invb_absgam2_sigma <- runif(d, min = 0.01, max = 2.0)

  chi <- qdesn_update_uts_chi(
    y = y,
    exps = exps,
    exps2 = exps2,
    sts = sts,
    sts2 = sts2,
    invb_inv_sigma = invb_inv_sigma,
    c_invb_absgam = c_invb_absgam,
    c2_invb_absgam2_sigma = c2_invb_absgam2_sigma
  )

  expect_true(all(is.finite(chi)))
  expect_true(all(chi > 0))

  # Dimension-1 reduction check on chi expression.
  chi_scalar <- qdesn_update_uts_chi(
    y = y[1],
    exps = exps[1],
    exps2 = exps2[1],
    sts = sts[1],
    sts2 = sts2[1],
    invb_inv_sigma = invb_inv_sigma[1],
    c_invb_absgam = c_invb_absgam[1],
    c2_invb_absgam2_sigma = c2_invb_absgam2_sigma[1]
  )
  expect_equal(chi[1], chi_scalar, tolerance = 1e-12)
})

test_that("finite-difference gradient for non-conjugate block is numerically stable", {
  set.seed(789)
  p0 <- 0.50

  n <- 12
  y <- rnorm(n)
  exps <- rnorm(n)
  exps2 <- exps^2 + rexp(n, rate = 2)
  sts <- rexp(n, rate = 1) + 0.01
  sts2 <- sts^2 + runif(n, min = 0, max = 0.15)
  uts <- rexp(n, rate = 1) + 0.05
  inv_uts <- 1 / (uts + runif(n, min = 0.1, max = 0.5))

  prior_g <- c(0, 1, 5)
  prior_s <- c(2, 1)

  f <- function(theta) {
    qdesn_dq_transf_no_climate(
      theta_s = theta[1],
      theta_g = theta[2],
      y = y,
      exps = exps,
      exps2 = exps2,
      sts = sts,
      sts2 = sts2,
      uts = uts,
      inv_uts = inv_uts,
      prior_g = prior_g,
      prior_s = prior_s,
      p0 = p0
    )
  }

  # Interior point in transformed space.
  theta <- c(log(1.2), -0.35)

  g_h <- qdesn_central_diff(f, theta, h = 1e-5)
  g_h2 <- qdesn_central_diff(f, theta, h = 5e-6)

  expect_true(all(is.finite(g_h)))
  expect_true(all(is.finite(g_h2)))
  expect_lt(max(abs(g_h - g_h2)), 1e-4)
})
