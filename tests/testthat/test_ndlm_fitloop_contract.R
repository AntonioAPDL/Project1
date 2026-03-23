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
    "NDLM_LATENT_VAR_CAP_ABS"
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
    NDLM_LATENT_VAR_CAP_ABS = "654321"
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

test_that("ndlm historical pseudo-observations use all available source channels", {
  source_obs <- list(
    usgs = c(1, NA, 4, NA),
    nws = c(2, 3, NA, NA),
    glofas = c(4, 5, 6, NA)
  )
  sigma_by_source <- c(usgs = 1, nws = 4, glofas = 9)

  out <- ndlm_theory_build_hist_pseudo_obs(
    source_obs = source_obs,
    sigma_by_source = sigma_by_source,
    source_names = c("usgs", "nws", "glofas"),
    fallback_y = c(10, 11, 12, 13),
    fallback_var = 1e6
  )

  expect_equal(length(out$y), 4L)
  expect_equal(length(out$R_vec), 4L)
  expect_equal(as.integer(out$n_sources), c(3L, 2L, 2L, 0L))

  p1 <- 1 + 1 / 4 + 1 / 9
  expect_equal(out$R_vec[1], 1 / p1, tolerance = 1e-12)
  expect_equal(out$y[1], (1 * 1 + 2 * (1 / 4) + 4 * (1 / 9)) / p1, tolerance = 1e-12)

  p2 <- 1 / 4 + 1 / 9
  expect_equal(out$R_vec[2], 1 / p2, tolerance = 1e-12)
  expect_equal(out$y[2], (3 * (1 / 4) + 5 * (1 / 9)) / p2, tolerance = 1e-12)

  p3 <- 1 + 1 / 9
  expect_equal(out$R_vec[3], 1 / p3, tolerance = 1e-12)
  expect_equal(out$y[3], (4 * 1 + 6 * (1 / 9)) / p3, tolerance = 1e-12)

  expect_equal(out$R_vec[4], 1e6, tolerance = 1e-12)
  expect_equal(out$y[4], 13, tolerance = 1e-12)
})
