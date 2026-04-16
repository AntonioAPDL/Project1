source(testthat::test_path("..", "..", "R", "unified", "deterministic_climate_blend.R"))

test_that("detclim reduction parser accepts quantile shorthand", {
  spec <- detclim_parse_reduction_spec("q85")
  expect_identical(spec$method, "quantile")
  expect_equal(spec$quantile, 0.85)
  expect_identical(spec$label, "q85")
})

test_that("detclim reduction computes requested ensemble summary", {
  vals <- c(1, 2, 3, 4, 5)
  expect_equal(detclim_reduce_values(vals, "mean"), mean(vals))
  expect_equal(detclim_reduce_values(vals, "median"), stats::median(vals))
  expect_equal(detclim_reduce_values(vals, "max"), max(vals))
  expect_equal(
    detclim_reduce_values(vals, "q85"),
    as.numeric(stats::quantile(vals, probs = 0.85, type = 7))
  )
})

test_that("detclim noise is deterministic and precip floor clamps negatives", {
  noisy_a <- detclim_apply_noise(
    values = c(0, 1, 2),
    noise_sd = 15,
    noise_seed = 20260415L,
    floor_at_zero = TRUE,
    label = "precip|2022-12-25|gefs_apcp"
  )
  noisy_b <- detclim_apply_noise(
    values = c(0, 1, 2),
    noise_sd = 15,
    noise_seed = 20260415L,
    floor_at_zero = TRUE,
    label = "precip|2022-12-25|gefs_apcp"
  )

  expect_equal(noisy_a$seed, noisy_b$seed)
  expect_equal(noisy_a$noise, noisy_b$noise)
  expect_equal(noisy_a$value, noisy_b$value)
  expect_true(all(noisy_a$value >= 0))
})

test_that("detclim future composition matches convex observed-forecast blend", {
  observed_df <- data.frame(
    date = as.Date(c("2022-01-02", "2022-01-03")),
    value = c(10, 20)
  )
  forecast_df <- data.frame(
    date = as.Date(c("2022-01-02", "2022-01-03")),
    value = c(100, 200)
  )

  out <- detclim_compose_future_series(
    observed_df = observed_df,
    forecast_df = forecast_df,
    observed_weight = 0.9,
    noise_sd = 0,
    noise_seed = 20260415L,
    floor_at_zero = FALSE,
    label = "soil|2022-01-01|gefs_soilw_0_0.1m"
  )

  expect_equal(out$noise, c(0, 0))
  expect_equal(out$noisy_forecast_value, c(100, 200))
  expect_equal(out$blended_value, c(0.9 * 10 + 0.1 * 100, 0.9 * 20 + 0.1 * 200))
  expect_true(length(unique(out$noise_seed_effective)) == 1L)
})

test_that("detclim series config normalization keeps user-specified blend defaults", {
  cfg <- list(
    precip = list(
      source = "gefs_apcp",
      reduction = "q85",
      noisy_blend = list(enabled = TRUE, noise_sd = 15, noise_seed = 123L, floor_at_zero = TRUE),
      observed_blend = list(enabled = TRUE, observed_weight = 0.9)
    ),
    soil = list(
      source = "gefs_soilw_0_0.1m",
      reduction = "q85",
      noisy_blend = list(enabled = TRUE, noise_sd = 0.01, noise_seed = 456L, floor_at_zero = FALSE),
      observed_blend = list(enabled = TRUE, observed_weight = 0.9)
    )
  )

  precip_cfg <- detclim_normalize_series_cfg(cfg, "precip")
  soil_cfg <- detclim_normalize_series_cfg(cfg, "soil")

  expect_identical(precip_cfg$source, "gefs_apcp")
  expect_identical(soil_cfg$source, "gefs_soilw_0_0.1m")
  expect_identical(precip_cfg$reduction, "q85")
  expect_identical(soil_cfg$reduction, "q85")
  expect_true(precip_cfg$noisy_blend$enabled)
  expect_true(soil_cfg$observed_blend$enabled)
  expect_equal(soil_cfg$noisy_blend$noise_sd, 0.01)
})
