source(testthat::test_path("..", "..", "R", "unified", "families", "ndlm_main", "00_constants.R"))
source(testthat::test_path("..", "..", "R", "unified", "families", "ndlm_main", "03_vb_updates.R"))

test_that("ndlm constants read fit-loop controls from environment", {
  old <- Sys.getenv(c(
    "NDLM_GAMSIG_MAX_ITER",
    "NDLM_GAMSIG_MIN_TOTAL_ITERS",
    "NDLM_GAMSIG_ELBO_TOL",
    "NDLM_GAMSIG_ELBO_REL_TOL",
    "NDLM_POSTERIOR_DRAWS",
    "NDLM_DF_T",
    "NDLM_DF_S1",
    "NDLM_DF_S2",
    "NDLM_DF_S67",
    "NDLM_DF_DISCREP",
    "NDLM_LAMBDA",
    "NDLM_COV_EIG_FLOOR",
    "NDLM_COV_EIG_CAP",
    "NDLM_COV_DIAG_JITTER",
    "NDLM_SIGMA_UPPER_CAP",
    "NDLM_SIGMA_UPDATE_DAMPING",
    "NDLM_LATENT_VAR_CAP_MULT",
    "NDLM_LATENT_VAR_CAP_ABS",
    "NDLM_FORECAST_IW_C_FACTOR",
    "NDLM_FORECAST_IW_EPSILON0",
    "NDLM_FORECAST_IW_DOF_OFFSET",
    "NDLM_FORECAST_IW_SCALE_MULT",
    "NDLM_FORECAST_IW_JITTER"
  ), unset = NA_character_)
  on.exit({
    for (nm in names(old)) {
      val <- old[[nm]]
      if (is.na(val)) {
        Sys.unsetenv(nm)
      } else {
        do.call(Sys.setenv, stats::setNames(list(val), nm))
      }
    }
  }, add = TRUE)

  Sys.setenv(
    NDLM_GAMSIG_MAX_ITER = "120",
    NDLM_GAMSIG_MIN_TOTAL_ITERS = "30",
    NDLM_GAMSIG_ELBO_TOL = "1e-05",
    NDLM_GAMSIG_ELBO_REL_TOL = "5e-04",
    NDLM_POSTERIOR_DRAWS = "64",
    NDLM_DF_T = "0.91",
    NDLM_DF_S1 = "0.92",
    NDLM_DF_S2 = "0.93",
    NDLM_DF_S67 = "0.94",
    NDLM_DF_DISCREP = "0.95",
    NDLM_LAMBDA = "0.96",
    NDLM_COV_EIG_FLOOR = "1e-07",
    NDLM_COV_EIG_CAP = "2e06",
    NDLM_COV_DIAG_JITTER = "1e-09",
    NDLM_SIGMA_UPPER_CAP = "7e05",
    NDLM_SIGMA_UPDATE_DAMPING = "0.65",
    NDLM_LATENT_VAR_CAP_MULT = "3210",
    NDLM_LATENT_VAR_CAP_ABS = "654321",
    NDLM_FORECAST_IW_C_FACTOR = "1.25",
    NDLM_FORECAST_IW_EPSILON0 = "42",
    NDLM_FORECAST_IW_DOF_OFFSET = "6",
    NDLM_FORECAST_IW_SCALE_MULT = "1.5",
    NDLM_FORECAST_IW_JITTER = "1e-7"
  )

  cst <- ndlm_theory_constants(seed = 777L)
  expect_equal(cst$max_iter, 120L)
  expect_equal(cst$min_total_iters, 30L)
  expect_equal(cst$convergence$elbo_tol, 1e-05)
  expect_equal(cst$convergence$elbo_rel_tol, 5e-04)
  expect_equal(cst$n_draws, 64L)
  expect_equal(cst$df_t, 0.91)
  expect_equal(cst$df_s1, 0.92)
  expect_equal(cst$df_s2, 0.93)
  expect_equal(cst$df_s67, 0.94)
  expect_equal(cst$df_discrep, 0.95)
  expect_equal(cst$lambda, 0.96)
  expect_equal(cst$stabilization$cov_eig_floor, 1e-07)
  expect_equal(cst$stabilization$cov_eig_cap, 2e06)
  expect_equal(cst$stabilization$cov_diag_jitter, 1e-09)
  expect_equal(cst$stabilization$sigma_upper_cap, 7e05)
  expect_equal(cst$stabilization$sigma_update_damping, 0.65)
  expect_equal(cst$stabilization$latent_var_cap_mult, 3210)
  expect_equal(cst$stabilization$latent_var_cap_abs, 654321)
  expect_equal(cst$forecast_iw_c_factor, 1.25)
  expect_equal(cst$forecast_iw_epsilon0, 42)
  expect_equal(cst$forecast_iw_dof_offset, 6L)
  expect_equal(cst$forecast_iw_scale_mult, 1.5)
  expect_equal(cst$forecast_iw_jitter, 1e-7)
})

test_that("ndlm convergence gate requires min iters plus abs/rel ELBO criteria", {
  expect_false(ndlm_theory_has_converged(
    iter = 20L,
    min_total_iters = 50L,
    crit_elbo = 1e-7,
    crit_elbo_rel = 1e-7,
    elbo_tol = 1e-6,
    elbo_rel_tol = 1e-4
  ))

  expect_false(ndlm_theory_has_converged(
    iter = 60L,
    min_total_iters = 50L,
    crit_elbo = 1e-3,
    crit_elbo_rel = 1e-6,
    elbo_tol = 1e-6,
    elbo_rel_tol = 1e-4
  ))

  expect_true(ndlm_theory_has_converged(
    iter = 60L,
    min_total_iters = 50L,
    crit_elbo = 5e-7,
    crit_elbo_rel = 5e-5,
    elbo_tol = 1e-6,
    elbo_rel_tol = 1e-4
  ))
})

test_that("ndlm observation-list builder preserves separate source channels and forecast export dimensions", {
  constants <- ndlm_theory_constants(seed = 777L)
  inputs <- list(
    y = c(1.1, 1.2, 1.3, 1.4),
    retros = list(
      usgs = c(1.1, 1.2, 1.3, 1.4),
      nws = c(1.0, NA, 1.5, 1.6),
      glofas = c(0.9, 1.0, NA, 1.7)
    ),
    X = matrix(seq_len(20), nrow = 4, ncol = 5),
    X_future = matrix(seq_len(15), nrow = 3, ncol = 5),
    T = 4L,
    forecast = list(
      nws = c(2.0, 2.1),
      glofas = c(1.9, 2.0, 2.1),
      K_overlap = 2L,
      K_max = 3L,
      K_vec = c(nws = 2L, glofas = 3L)
    )
  )

  out <- ndlm_theory_build_obslist_sequences(inputs = inputs, constants = constants)

  expect_equal(out$state_dim, 27L)
  expect_equal(length(out$hist_seq), 4L)
  expect_equal(vapply(out$hist_seq, `[[`, integer(1), "n_sources"), c(3L, 2L, 2L, 3L))
  expect_equal(vapply(out$future_seq, `[[`, integer(1), "n_sources"), c(2L, 2L, 1L))
  expect_equal(length(out$overlap_export_idx), 27L)
  expect_equal(length(out$tail_export_idx), 20L)
  expect_equal(length(out$future_H$usgs), 27L)
  expect_equal(which(out$future_H$usgs != 0)[1], 1L)
})
