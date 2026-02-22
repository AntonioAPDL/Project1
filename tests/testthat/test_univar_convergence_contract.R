source(testthat::test_path("..", "..", "R", "unified", "families", "exdqlm_univar", "00_constants.R"))
source(testthat::test_path("..", "..", "R", "unified", "families", "exdqlm_univar", "03_updates_vb_or_fitloop.R"))

test_that("univar default gamma-sigma policy defines relative tolerances", {
  policy <- univar_theory_default_gamma_sigma_policy()

  expect_true(is.list(policy$convergence))
  expect_true(is.finite(policy$convergence$elbo_rel_tol))
  expect_true(is.finite(policy$convergence$state_norm_sq_rel_tol))
  expect_true(is.finite(policy$convergence$sigma_exp_rel_tol))
  expect_true(is.finite(policy$convergence$gamma_exp_rel_tol))

  expect_gt(policy$convergence$elbo_rel_tol, 0)
  expect_gt(policy$convergence$state_norm_sq_rel_tol, 0)
  expect_gt(policy$convergence$sigma_exp_rel_tol, 0)
  expect_gt(policy$convergence$gamma_exp_rel_tol, 0)
})

test_that("univar policy resolver restores invalid relative tolerances to defaults", {
  policy <- univar_theory_resolve_gamma_sigma_policy(list(
    convergence = list(
      elbo_rel_tol = NA_real_,
      state_norm_sq_rel_tol = -1,
      sigma_exp_rel_tol = 0,
      gamma_exp_rel_tol = -5
    )
  ))

  expect_equal(policy$convergence$elbo_rel_tol, 2.5e-4)
  expect_equal(policy$convergence$state_norm_sq_rel_tol, 2.5e-4)
  expect_equal(policy$convergence$sigma_exp_rel_tol, 5e-5)
  expect_equal(policy$convergence$gamma_exp_rel_tol, 5e-5)
})

test_that("metric delta convergence supports relative criteria when absolute fails", {
  # abs_delta = 0.02 exceeds abs_tol=1e-6, but rel_delta = 2e-4 passes rel_tol=2.5e-4
  out <- univar_theory_metric_delta(
    current = 100.02,
    previous = 100.00,
    abs_tol = 1e-6,
    rel_tol = 2.5e-4
  )

  expect_true(is.finite(out$abs_delta))
  expect_true(is.finite(out$rel_delta))
  expect_false(out$conv_abs)
  expect_true(out$conv_rel)
  expect_true(out$converged)
})

test_that("metric delta convergence remains true for absolute criterion and false on non-finite inputs", {
  out_abs <- univar_theory_metric_delta(
    current = 1.0000004,
    previous = 1.0000000,
    abs_tol = 1e-6,
    rel_tol = 1e-12
  )
  expect_true(out_abs$conv_abs)
  expect_true(out_abs$converged)

  out_bad <- univar_theory_metric_delta(
    current = Inf,
    previous = 1,
    abs_tol = 1e-6,
    rel_tol = 1e-6
  )
  expect_false(out_bad$converged)
  expect_false(out_bad$conv_abs)
  expect_false(out_bad$conv_rel)
})
