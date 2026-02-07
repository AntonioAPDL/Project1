source(testthat::test_path("helper_unified_test_models.R"))
source(file.path("..", "..", "R", "environmetrics", "02_helpers_core.R"))

test_that("dlm_df returns s as variance path S (not loop index)", {
  y <- c(0.2, 0.4, -0.3, 1.1, -0.5)
  model <- make_toy_scalar_model(
    TT = length(y),
    gg_vals = c(1.0, 0.9, 1.1, 1.2, 0.95),
    ff_vals = rep(1, length(y)),
    m0 = 0,
    C0 = 1
  )

  out <- dlm_df(y = y, model = model, df = 0.95, dim.df = 1, s.priors = list(l0 = 1, S0 = 10), just.lik = FALSE)
  ref <- reference_dlm_df_scalar(y, model, df = 0.95, s.priors = list(l0 = 1, S0 = 10), use_buggy_index = FALSE)

  expect_true(is.numeric(out$s))
  expect_length(out$s, length(y))
  expect_equal(as.numeric(out$s), as.numeric(ref$s), tolerance = 1e-10)
  expect_false(length(out$s) == 1)
})

test_that("fit/post helper contract agrees on s = S in source files", {
  post_lines <- readLines(file.path("..", "..", "R", "environmetrics", "02_helpers_core.R"), warn = FALSE)
  fit_lines <- readLines(file.path("..", "..", "DISC_Optimal_Synth_Ranges_W.r"), warn = FALSE)

  expect_false(any(grepl("model = model, s = i", post_lines, fixed = TRUE)))
  expect_true(any(grepl("model = model, s = S", post_lines, fixed = TRUE)))

  expect_false(any(grepl("model = model, s = i", fit_lines, fixed = TRUE)))
  expect_true(any(grepl("model = model, s = S", fit_lines, fixed = TRUE)))
})
