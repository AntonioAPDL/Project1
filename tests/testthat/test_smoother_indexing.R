source(testthat::test_path("helper_unified_test_models.R"))
source(file.path("..", "..", "R", "environmetrics", "02_helpers_core.R"))

test_that("dlm_df smoothing uses time-indexed GG in recursion", {
  y <- c(0.5, -0.1, 0.9, -0.7, 0.3, 0.8)
  model <- make_toy_scalar_model(
    TT = length(y),
    gg_vals = c(1.0, 0.75, 1.6, 0.9, 1.35, 0.8),
    ff_vals = c(1, 1, 1, 1, 1, 1),
    m0 = 0,
    C0 = 2
  )

  out <- dlm_df(y = y, model = model, df = 0.9, dim.df = 1, s.priors = list(l0 = 1, S0 = 10), just.lik = FALSE)
  ref_fixed <- reference_dlm_df_scalar(y, model, df = 0.9, s.priors = list(l0 = 1, S0 = 10), use_buggy_index = FALSE)
  ref_buggy <- reference_dlm_df_scalar(y, model, df = 0.9, s.priors = list(l0 = 1, S0 = 10), use_buggy_index = TRUE)

  expect_equal(as.numeric(out$m), as.numeric(ref_fixed$m), tolerance = 1e-10)
  expect_equal(as.numeric(out$C), as.numeric(ref_fixed$C), tolerance = 1e-10)

  # This assertion fails under the old buggy implementation where GG[,,i] was
  # reused in the smoothing loop.
  expect_gt(max(abs(as.numeric(out$m) - as.numeric(ref_buggy$m))), 1e-8)
})
