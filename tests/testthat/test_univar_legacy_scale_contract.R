source(file.path("..", "..", "R", "unified", "univar_legacy_scale_contract.R"))

test_that("legacy univariate scale bridge keeps log1p inputs unchanged under log1p-only contract", {
  contract <- univar_legacy_resolve_scale_contract(
    legacy_fit_input_scale = "log1p_cms",
    analysis_scale_fit_internal = "log1p_cms",
    transform_policy = "log1p_only"
  )
  x_raw <- c(0, 0.5, 2, 10)
  x_log1p <- log1p(x_raw)

  expect_equal(
    univar_legacy_transform_flow_values_to_internal_scale(x_log1p, "fixture", contract),
    x_log1p,
    tolerance = 1e-12
  )
})

test_that("legacy univariate scale bridge converts only when an explicit compatible contract requests it", {
  contract <- univar_legacy_resolve_scale_contract(
    legacy_fit_input_scale = "raw_cms",
    analysis_scale_fit_internal = "log1p_cms",
    transform_policy = "allow_explicit_scale_conversion"
  )
  x_raw <- c(0, 0.5, 2, 10)

  expect_equal(
    univar_legacy_transform_flow_values_to_internal_scale(x_raw, "fixture", contract),
    log1p(x_raw),
    tolerance = 1e-12
  )
})

test_that("legacy univariate scale bridge preserves matrix shape", {
  contract <- univar_legacy_resolve_scale_contract(
    legacy_fit_input_scale = "log1p_cms",
    analysis_scale_fit_internal = "log1p_cms",
    transform_policy = "log1p_only"
  )
  x <- matrix(log1p(c(0, 1, 2, 3)), nrow = 2)

  out <- univar_legacy_transform_flow_values_to_internal_scale(x, "matrix_fixture", contract)

  expect_equal(dim(out), dim(x))
  expect_equal(out, x, tolerance = 1e-12)
})

test_that("legacy univariate scale bridge rejects log-log internals under log1p-only policy", {
  expect_error(
    univar_legacy_resolve_scale_contract(
      legacy_fit_input_scale = "log1p_cms",
      analysis_scale_fit_internal = "log_log1p_cms",
      transform_policy = "log1p_only"
    ),
    "forbids legacy univariate internal scale"
  )
})

test_that("legacy univariate frame conversion excludes date columns and converts numeric members", {
  contract <- univar_legacy_resolve_scale_contract(
    legacy_fit_input_scale = "raw_cms",
    analysis_scale_fit_internal = "log1p_cms",
    transform_policy = "allow_explicit_scale_conversion"
  )
  dat <- data.frame(
    target_date = as.Date("2022-12-26") + 0:1,
    m1 = c(0, 1),
    m2 = c(2, 3)
  )

  out <- univar_legacy_transform_flow_frame_cols(dat, context_label = "forecast_fixture", scale_contract = contract)

  expect_equal(out$target_date, dat$target_date)
  expect_equal(out$m1, log1p(dat$m1), tolerance = 1e-12)
  expect_equal(out$m2, log1p(dat$m2), tolerance = 1e-12)
})
