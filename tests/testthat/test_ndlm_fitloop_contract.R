source(testthat::test_path("..", "..", "R", "unified", "families", "ndlm_main", "00_constants.R"))
source(testthat::test_path("..", "..", "R", "unified", "families", "ndlm_main", "03_vb_updates.R"))

test_that("ndlm constants read fit-loop controls from environment", {
  old <- Sys.getenv(c(
    "NDLM_GAMSIG_MAX_ITER",
    "NDLM_GAMSIG_MIN_TOTAL_ITERS",
    "NDLM_GAMSIG_ELBO_TOL",
    "NDLM_GAMSIG_ELBO_REL_TOL",
    "NDLM_POSTERIOR_DRAWS"
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
    NDLM_POSTERIOR_DRAWS = "64"
  )

  cst <- ndlm_theory_constants(seed = 777L)
  expect_equal(cst$max_iter, 120L)
  expect_equal(cst$min_total_iters, 30L)
  expect_equal(cst$convergence$elbo_tol, 1e-05)
  expect_equal(cst$convergence$elbo_rel_tol, 5e-04)
  expect_equal(cst$n_draws, 64L)
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
