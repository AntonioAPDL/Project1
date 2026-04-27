source(testthat::test_path("..", "..", "R", "unified", "families", "shared_input_helpers.R"))

test_that("engineered featurecov design matrices keep engineered columns and intercept", {
  dates <- seq(as.Date("2021-01-01"), by = "1 day", length.out = 6L)
  feature_df <- data.frame(
    date = dates,
    PPT = 1:6,
    SOIL = 11:16,
    PCA = 21:26,
    PPT_sq = (1:6)^2,
    SOIL_sq = (11:16)^2,
    PPT_x_SOIL = (1:6) * (11:16),
    PPT_lag1 = c(0, 1:5),
    PPT_lag2 = c(0, 0, 1:4),
    PPT_lag3 = c(0, 0, 0, 1:3),
    SOIL_lag1 = c(0, 11:15),
    SOIL_lag2 = c(0, 0, 11:14),
    SOIL_lag3 = c(0, 0, 0, 11:13),
    stringsAsFactors = FALSE
  )
  feature_path <- tempfile(fileext = ".csv")
  on.exit(unlink(feature_path), add = TRUE)
  write.csv(feature_df, feature_path, row.names = FALSE)

  history_df <- data.frame(ppt = 1:4, soil = 11:14, Static_PCA = 21:24)
  forecast_df <- data.frame(ppt = 5:6, soil = 15:16, Static_PCA = 25:26)

  out <- family_shared_build_featurecov_design_matrices(
    history_df = history_df,
    forecast_df = forecast_df,
    history_dates = dates[1:4],
    forecast_dates = dates[5:6],
    feature_path = feature_path,
    fill_value = 0
  )

  expect_identical(out$mode, "engineered_feature_table")
  expect_equal(dim(out$X), c(4L, 13L))
  expect_equal(dim(out$X_f), c(2L, 13L))
  expect_identical(
    colnames(out$X),
    c(
      "PPT", "SOIL", "PCA", "PPT_sq", "SOIL_sq", "PPT_x_SOIL",
      "PPT_lag1", "PPT_lag2", "PPT_lag3",
      "SOIL_lag1", "SOIL_lag2", "SOIL_lag3",
      "intercept"
    )
  )
})

test_that("legacy fallback design matrices preserve old nine-column univar layout", {
  dates <- seq(as.Date("2021-01-01"), by = "1 day", length.out = 6L)
  history_df <- data.frame(
    ppt = c(10, 12, 14, 16),
    soil = c(1.1, 1.2, 1.3, 1.4),
    Static_PCA = c(0.1, 0.2, 0.3, 0.4)
  )
  forecast_df <- data.frame(
    ppt = c(18, 20),
    soil = c(1.5, 1.6),
    Static_PCA = c(0.5, 0.6)
  )

  out <- family_shared_build_featurecov_design_matrices(
    history_df = history_df,
    forecast_df = forecast_df,
    history_dates = dates[1:4],
    forecast_dates = dates[5:6],
    feature_path = "",
    fill_value = 0
  )

  expect_identical(out$mode, "legacy_precip_extension")
  expect_equal(dim(out$X), c(4L, 9L))
  expect_equal(dim(out$X_f), c(2L, 9L))
  expect_identical(
    colnames(out$X),
    c(
      "PPT", "SOIL", "PCA", "intercept",
      "PPT_lag1", "PPT_lag2", "PPT_sq", "PPT_lag1_sq", "PPT_lag2_sq"
    )
  )
})
