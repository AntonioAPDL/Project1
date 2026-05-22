source(testthat::test_path("..", "..", "R", "disc_w", "11_latent_pseudodata_audit_helpers.R"))

testthat::test_that("s_t audit helper matches positive-truncated normal moments", {
  y <- c(1.2, -0.4, 2.1)
  exps <- c(0.3, -0.7, 1.5)
  inv_uts <- c(0.8, 1.4, 0.5)
  out <- disc_w_audit_update_sts(
    y = y,
    exps = exps,
    inv_uts = inv_uts,
    c2_invb_absgam2_sigma = c(0.7, 0.2, 1.1),
    c_invb_absgam = c(0.6, -0.1, 0.9),
    c_a_invb_absgam = c(0.05, -0.02, 0.1)
  )

  for (i in seq_along(y)) {
    dens <- function(x) stats::dnorm(x, mean = out$sts.mu[i], sd = sqrt(out$sts.sig2[i]))
    z <- stats::pnorm(out$sts.mu[i] / sqrt(out$sts.sig2[i]))
    ref_mean <- stats::integrate(function(x) x * dens(x), 0, Inf, rel.tol = 1e-10)$value / z
    ref_second <- stats::integrate(function(x) x^2 * dens(x), 0, Inf, rel.tol = 1e-10)$value / z
    testthat::expect_equal(out$E.sts[i], ref_mean, tolerance = 1e-9)
    testthat::expect_equal(out$E.sts2[i], ref_second, tolerance = 1e-8)
  }

  testthat::expect_true(all(out$E.sts >= 0))
  testthat::expect_true(all(out$E.sts2 >= out$E.sts^2))
})

testthat::test_that("s_t entropy uses the canonical truncated-normal entropy", {
  out <- disc_w_audit_update_sts(
    y = c(1.2, -0.4, 2.1),
    exps = c(0.3, -0.7, 1.5),
    inv_uts = c(0.8, 1.4, 0.5),
    c2_invb_absgam2_sigma = c(0.7, 0.2, 1.1),
    c_invb_absgam = c(0.6, -0.1, 0.9),
    c_a_invb_absgam = c(0.05, -0.02, 0.1)
  )

  testthat::expect_true(is.finite(out$active_tot.entrop))
  testthat::expect_true(is.finite(out$canonical_tot.entrop))
  testthat::expect_equal(out$active_tot.entrop, out$canonical_tot.entrop, tolerance = 1e-12)
})

testthat::test_that("u_t audit helper matches GIG moment identities", {
  out <- disc_w_audit_update_uts(
    y = c(1.4, -0.2),
    exps = c(0.4, -0.5),
    exps2 = c(0.5, 0.4),
    sts = c(0.8, 0.2),
    sts2 = c(0.9, 0.3),
    inv_sigma = c(0.7, 1.3),
    a2_invb_inv_sigma = c(0.4, 0.9),
    invb_inv_sigma = c(0.8, 1.1),
    c_invb_absgam = c(0.25, -0.15),
    c2_invb_absgam2_sigma = c(0.55, 0.35)
  )

  ref_E <- disc_w_audit_gig_moment(out$uts.lambda, out$uts.chi, out$uts.psi, 1)
  ref_E_inv <- disc_w_audit_gig_moment(out$uts.lambda, out$uts.chi, out$uts.psi, -1)
  testthat::expect_equal(out$E.uts, ref_E, tolerance = 1e-10)
  testthat::expect_equal(out$E.inv.uts, ref_E_inv, tolerance = 1e-10)

  ref_log <- vapply(seq_along(out$uts.chi), function(i) {
    lambda <- out$uts.lambda
    chi <- out$uts.chi[i]
    psi <- out$uts.psi[i]
    norm_const <- 2 * (chi / psi)^(lambda / 2) * besselK(sqrt(chi * psi), lambda)
    stats::integrate(
      function(x) log(x) * x^(lambda - 1) * exp(-0.5 * (chi / x + psi * x)) / norm_const,
      0,
      Inf,
      rel.tol = 1e-8
    )$value
  }, numeric(1))
  testthat::expect_equal(out$E.log.uts, sum(ref_log), tolerance = 1e-6)
})

testthat::test_that("u_t half-order GIG moments stay finite at extreme chi values", {
  out_small <- disc_w_audit_update_uts(
    y = c(0, 1000),
    exps = c(0, 0),
    exps2 = c(0, 1),
    sts = c(0, 0.1),
    sts2 = c(0, 0.2),
    inv_sigma = c(1, 1),
    a2_invb_inv_sigma = c(0.35, 0.35),
    invb_inv_sigma = c(1, 1),
    c_invb_absgam = c(0.25, 0.25),
    c2_invb_absgam2_sigma = c(0.55, 0.55)
  )

  testthat::expect_true(all(is.finite(out_small$E.uts)))
  testthat::expect_true(all(is.finite(out_small$E.inv.uts)))
  testthat::expect_true(all(out_small$E.uts > 0))
  testthat::expect_true(all(out_small$E.inv.uts > 0))
  testthat::expect_equal(out_small$E.uts, sqrt(out_small$uts.chi / out_small$uts.psi) + 1 / out_small$uts.psi)
  testthat::expect_equal(out_small$E.inv.uts, sqrt(out_small$uts.psi / out_small$uts.chi))
})

testthat::test_that("active runner uses stable latent formulas", {
  runner <- testthat::test_path("..", "..", "DISC_Optimal_Synth_Ranges_W_transfer_forecast.r")
  src <- readLines(runner, warn = FALSE)
  text <- paste(src, collapse = "\n")

  testthat::expect_false(grepl("log2\\(2\\*pi\\*exp\\(1\\)\\*s\\.sig2\\)", text))
  testthat::expect_false(grepl("HyperbolicDist::besselRatio", text, fixed = TRUE))
  testthat::expect_true(grepl("disc_w_pos_truncnorm_moments", text, fixed = TRUE))
  testthat::expect_true(grepl("E.inv.uts = sqrt\\(u.psi/u.chi\\)", text))
  testthat::expect_true(grepl("disc_w_check_pseudodata_guard", text, fixed = TRUE))
  testthat::expect_true(grepl("DISC_PSEUDODATA_GUARD_MODE", text, fixed = TRUE))
  testthat::expect_true(grepl("DISC_W_POST_SAVE_OBJECTIVE_ENABLED", text, fixed = TRUE))
  testthat::expect_true(grepl("\\[post_save_objective\\] disabled", text))
  testthat::expect_true(grepl("DISC_GAMSIG_STATE_GUARD_START_ITER", text, fixed = TRUE))
  testthat::expect_true(grepl("state_guard_start_iter", text, fixed = TRUE))

  stage_fit <- testthat::test_path("..", "..", "R", "unified", "stages", "stage_fit.R")
  stage_text <- paste(readLines(stage_fit, warn = FALSE), collapse = "\n")
  testthat::expect_true(grepl("DISC_W_POST_SAVE_OBJECTIVE_ENABLED", stage_text, fixed = TRUE))
  testthat::expect_true(grepl("post_save_objective_enabled", stage_text, fixed = TRUE))
  testthat::expect_true(grepl("DISC_W_POST_SAVE_JSD_ENABLED", stage_text, fixed = TRUE))
  testthat::expect_true(grepl("post_save_jsd_enabled", stage_text, fixed = TRUE))
})

testthat::test_that("active runner exposes diagnostic latent ablation controls", {
  runner <- testthat::test_path("..", "..", "DISC_Optimal_Synth_Ranges_W_transfer_forecast.r")
  text <- paste(readLines(runner, warn = FALSE), collapse = "\n")

  testthat::expect_true(grepl("DISC_LATENT_ABLATION_MODE", text, fixed = TRUE))
  testthat::expect_true(grepl("choices = c(\"free\", \"freeze\", \"cap_e_inv_u\")", text, fixed = TRUE))
  testthat::expect_true(grepl("DISC_LATENT_E_INV_U_CAP", text, fixed = TRUE))
  testthat::expect_true(grepl("disc_w_apply_latent_ablation", text, fixed = TRUE))
  testthat::expect_true(grepl("mode=cap_e_inv_u", text, fixed = TRUE))
  testthat::expect_true(grepl("context_label = \"fit_pre_gamsig\"", text, fixed = TRUE))
  testthat::expect_true(grepl("context_label = \"sampling_pre_gamsig\"", text, fixed = TRUE))
})

testthat::test_that("pseudo-data offset and variance reproduce information-form algebra", {
  y <- c(3, 4)
  pseudo <- disc_w_audit_pseudodata(
    E_c_invb_absgam = c(0.2, -0.1),
    E_a_invb_inv_sigma = c(0.7, -0.4),
    E_invb_inv_sigma = c(1.4, 0.8),
    E_sts = c(0.5, 1.1),
    E_inv_uts = c(2.0, 0.5)
  )
  w <- c(1.4, 0.8) * c(2.0, 0.5)
  b <- y * w - c(0.2, -0.1) * c(0.5, 1.1) * c(2.0, 0.5) - c(0.7, -0.4)

  testthat::expect_equal(pseudo$variance, 1 / w)
  testthat::expect_equal(y - pseudo$offset, b / w)
  testthat::expect_true(all(is.finite(pseudo$offset)))
  testthat::expect_true(all(pseudo$variance > 0))
})

testthat::test_that("pseudo-data guard flags destructive offsets and invalid variances", {
  qqq <- array(0, dim = c(2, 2, 2))
  qqq[, , 1] <- diag(c(0.1, 2))
  qqq[, , 2] <- diag(c(-0.1, 3))

  guard <- disc_w_audit_pseudodata_guard(
    iter = 7,
    FFF = matrix(c(1, -5000), nrow = 2),
    QQQ = qqq,
    FFF_forecast = list(matrix(c(2, 3), nrow = 1)),
    QQQ_forecast = list(array(diag(c(1, 2)), dim = c(2, 2, 1))),
    E_sts = matrix(c(0.1, 0.2), nrow = 1),
    E_sts2 = matrix(c(0.2, 0.4), nrow = 1),
    E_uts = matrix(c(1, 2), nrow = 1),
    E_inv_uts = matrix(c(10, 6000), nrow = 1),
    fff_abs_cap = 1000,
    qqq_diag_abs_cap = 10000,
    e_inv_u_abs_cap = 5000
  )

  testthat::expect_true(any(guard$quantity == "FFF" & guard$status == "cap_exceeded"))
  testthat::expect_true(any(guard$quantity == "QQQ_diag" & guard$status == "nonpositive"))
  testthat::expect_true(any(guard$quantity == "E_inv_uts" & guard$status == "cap_exceeded"))
})

testthat::test_that("pseudo-data guard passes healthy finite positive inputs", {
  qqq <- array(0, dim = c(2, 2, 2))
  qqq[, , 1] <- diag(c(0.1, 2))
  qqq[, , 2] <- diag(c(0.2, 3))

  guard <- disc_w_audit_pseudodata_guard(
    iter = 8,
    FFF = matrix(c(1, -2), nrow = 2),
    QQQ = qqq,
    E_sts = matrix(c(0.1, 0.2), nrow = 1),
    E_sts2 = matrix(c(0.2, 0.4), nrow = 1),
    E_uts = matrix(c(1, 2), nrow = 1),
    E_inv_uts = matrix(c(10, 20), nrow = 1)
  )

  testthat::expect_true(all(guard$status == "ok"))
})

testthat::test_that("keep forecast dimension table follows active segment algebra", {
  dims <- disc_w_audit_keep_dimension_table(
    p = 4,
    J = 2,
    ppx = 3,
    ranges = c(10, 4),
    num_mem = c(51, 31)
  )

  testthat::expect_equal(dims$active_sources, c(2, 1))
  testthat::expect_equal(dims$core_state_dim, c(12, 8))
  testthat::expect_equal(dims$keep_state_dim, c(15, 11))
  testthat::expect_equal(dims$forecast_series, c(2, 1))
  testthat::expect_equal(dims$forecast_member_obs_dim, c(82, 51))
  testthat::expect_equal(dims$segment_horizon, c(4, 6))
})

testthat::test_that("active forecast u_t updates index forecast columns with TT_sub", {
  runner <- testthat::test_path("..", "..", "DISC_Optimal_Synth_Ranges_W_transfer_forecast.r")
  src <- readLines(runner, warn = FALSE)
  text <- paste(src, collapse = "\n")

  testthat::expect_false(grepl("new\\.theta\\.out\\$exps\\[j,\\(T\\+1\\):\\(T\\+k_forecast\\)\\]", text))
  testthat::expect_false(grepl("new\\.theta\\.out\\$exps2\\[j,\\(T\\+1\\):\\(T\\+k_forecast\\)\\]", text))
  testthat::expect_gte(
    length(grep("new\\.theta\\.out\\$exps2?\\[j,\\(TT_sub\\+1\\):\\(TT_sub\\+k_forecast\\)\\]", src)),
    4L
  )
})
