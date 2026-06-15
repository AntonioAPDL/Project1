source(testthat::test_path("..", "..", "R", "unified", "inputs_shared_validate.R"))
source(testthat::test_path("..", "..", "R", "unified", "families", "shared_input_helpers.R"))
source(testthat::test_path("..", "..", "R", "unified", "covariate_feature_engineering.R"))

make_cov_csv <- function(path, dates, values, value_name) {
  utils::write.csv(
    data.frame(Date = as.Date(dates), value = as.numeric(values), stringsAsFactors = FALSE),
    path,
    row.names = FALSE
  )
}

test_that("engineered feature table builds squares interaction and rolling lags over stitched series", {
  td <- withr::local_tempdir()
  dates <- seq(as.Date("2022-01-01"), by = "day", length.out = 6)
  ppt_path <- file.path(td, "ppt.csv")
  soil_path <- file.path(td, "soil.csv")
  pca_path <- file.path(td, "pca.csv")

  make_cov_csv(ppt_path, dates, c(1, 2, 3, 10, 11, 12), "ppt")
  make_cov_csv(soil_path, dates, c(4, 5, 6, 20, 21, 22), "soil")
  make_cov_csv(pca_path, dates, c(100, 101, 102, 103, 104, 105), "pca")

  feat <- unified_covfeat_build_table(
    ppt_path = ppt_path,
    soil_path = soil_path,
    pca_path = pca_path,
    lag_orders = c(1L, 2L, 3L),
    include_squares = TRUE,
    include_interaction = TRUE
  )

  expect_true(all(c(
    "PPT", "SOIL", "PCA", "PPT_sq", "SOIL_sq", "PPT_x_SOIL",
    "PPT_lag1", "PPT_lag2", "PPT_lag3", "SOIL_lag1", "SOIL_lag2", "SOIL_lag3"
  ) %in% names(feat)))

  row_t1 <- feat[feat$date == as.Date("2022-01-04"), , drop = FALSE]
  row_t2 <- feat[feat$date == as.Date("2022-01-05"), , drop = FALSE]

  expect_equal(row_t1$PPT_lag1, 3)
  expect_equal(row_t1$SOIL_lag1, 6)
  expect_equal(row_t2$PPT_lag1, 10)
  expect_equal(row_t2$PPT_lag2, 3)
  expect_equal(row_t2$SOIL_lag1, 20)
  expect_equal(row_t2$SOIL_lag2, 6)
  expect_equal(row_t2$PPT_sq, 11^2)
  expect_equal(row_t2$SOIL_sq, 21^2)
  expect_equal(row_t2$PPT_x_SOIL, 11 * 21)
})

test_that("zero precipitation days remain explicit transfer-covariate values", {
  td <- withr::local_tempdir()
  dates <- seq(as.Date("2022-01-01"), by = "day", length.out = 6)
  ppt_path <- file.path(td, "ppt.csv")
  soil_path <- file.path(td, "soil.csv")
  pca_path <- file.path(td, "pca.csv")

  make_cov_csv(ppt_path, dates, c(0, 0, 5, 0, 2, 0), "ppt")
  make_cov_csv(soil_path, dates, c(4, 5, 6, 7, 8, 9), "soil")
  make_cov_csv(pca_path, dates, c(100, 101, 102, 103, 104, 105), "pca")

  feat <- unified_covfeat_build_table(
    ppt_path = ppt_path,
    soil_path = soil_path,
    pca_path = pca_path,
    lag_orders = c(1L, 2L, 3L),
    include_squares = TRUE,
    include_interaction = TRUE
  )

  expect_equal(feat$PPT, c(0, 0, 5, 0, 2, 0))
  expect_equal(feat$PPT_sq, c(0, 0, 25, 0, 4, 0))
  expect_equal(feat$PPT_x_SOIL[c(1, 2, 4, 6)], rep(0, 4))
  expect_equal(feat$PPT_lag1[2:4], c(0, 0, 5))

  feat_path <- file.path(td, "features.csv")
  utils::write.csv(feat, feat_path, row.names = FALSE)
  mats <- family_shared_build_feature_matrices(
    path = feat_path,
    history_dates = dates[1:4],
    forecast_dates = dates[5:6],
    fill_value = 0,
    scale_with_history = TRUE,
    scale_mode = "sd"
  )

  expect_equal(as.numeric(mats$history[c(1, 2, 4), "PPT"]), rep(0, 3))
  expect_equal(as.numeric(mats$forecast[2, "PPT"]), 0)
})

test_that("feature matrices align and scale with history only", {
  td <- withr::local_tempdir()
  dates <- seq(as.Date("2022-01-01"), by = "day", length.out = 5)
  feat_path <- file.path(td, "features.csv")
  utils::write.csv(
    data.frame(
      date = dates,
      PPT = c(1, 2, 3, 10, 11),
      SOIL = c(4, 5, 6, 20, 21),
      PCA = c(100, 101, 102, 103, 104),
      PPT_lag1 = c(NA, 1, 2, 3, 10),
      stringsAsFactors = FALSE
    ),
    feat_path,
    row.names = FALSE
  )

  mats <- family_shared_build_feature_matrices(
    path = feat_path,
    history_dates = dates[1:3],
    forecast_dates = dates[4:5],
    fill_value = 0,
    scale_with_history = TRUE
  )

  expect_equal(colnames(mats$history), c("PPT", "SOIL", "PCA", "PPT_lag1"))
  expect_equal(dim(mats$history), c(3, 4))
  expect_equal(dim(mats$forecast), c(2, 4))

  ppt_sd <- stats::sd(c(1, 2, 3))
  expect_equal(as.numeric(mats$history[, "PPT"]), c(1, 2, 3) / ppt_sd)
  expect_equal(as.numeric(mats$forecast[, "PPT"]), c(10, 11) / ppt_sd)

  lag_sd <- stats::sd(c(1, 2), na.rm = TRUE)
  expect_equal(as.numeric(mats$forecast[, "PPT_lag1"]), c(3, 10) / lag_sd)
})

test_that("feature matrices support history-fitted zscore scaling", {
  td <- withr::local_tempdir()
  dates <- seq(as.Date("2022-01-01"), by = "day", length.out = 5)
  feat_path <- file.path(td, "features.csv")
  utils::write.csv(
    data.frame(
      date = dates,
      PPT = c(1, 2, 3, 10, 11),
      SOIL = c(4, 5, 6, 20, 21),
      stringsAsFactors = FALSE
    ),
    feat_path,
    row.names = FALSE
  )

  mats <- family_shared_build_feature_matrices(
    path = feat_path,
    history_dates = dates[1:3],
    forecast_dates = dates[4:5],
    fill_value = 0,
    scale_with_history = TRUE,
    scale_mode = "zscore"
  )

  expect_equal(mean(as.numeric(mats$history[, "PPT"])), 0, tolerance = 1e-12)
  expect_equal(stats::sd(as.numeric(mats$history[, "PPT"])), 1, tolerance = 1e-12)
  expect_equal(as.numeric(mats$forecast[, "PPT"]), (c(10, 11) - 2) / stats::sd(c(1, 2, 3)))
})

test_that("transfer design can be explicit transfer-level-only with no feature columns", {
  dates <- seq(as.Date("2022-01-01"), by = "day", length.out = 5)
  history_df <- data.frame(
    ppt = c(1, 2, 3),
    soil = c(4, 5, 6),
    Static_PCA = c(0.1, 0.2, 0.3)
  )
  forecast_df <- data.frame(
    ppt = c(10, 11),
    soil = c(20, 21),
    Static_PCA = c(0.4, 0.5)
  )

  design <- family_shared_build_featurecov_design_matrices(
    history_df = history_df,
    forecast_df = forecast_df,
    history_dates = dates[1:3],
    forecast_dates = dates[4:5],
    feature_path = "",
    feature_mode = "none",
    scaling_mode = "sd"
  )

  expect_equal(dim(design$X), c(3, 0))
  expect_equal(dim(design$X_f), c(2, 0))
  expect_equal(design$feature_names, character(0))
  diag <- family_shared_transfer_design_diagnostics(design$X, design$X_f, mode = design$mode)
  expect_equal(nrow(diag$metadata), 0)
  expect_equal(diag$condition$n_features, c(0L, 0L))
})

test_that("transfer design diagnostics write summary condition and metadata files", {
  td <- withr::local_tempdir()
  X <- cbind(
    PPT = c(1, 2, 3, 4),
    SOIL = c(0.1, 0.3, 0.2, 0.5),
    PCA = c(-1, 0.5, 1, 2)
  )
  X_f <- cbind(
    PPT = c(5, 6),
    SOIL = c(0.5, 0.6),
    PCA = c(3, 4)
  )

  diag <- family_shared_transfer_design_diagnostics(
    X = X,
    X_f = X_f,
    out_dir = td,
    mode = "unit_test"
  )

  expect_true(file.exists(file.path(td, "transfer_design_summary.csv")))
  expect_true(file.exists(file.path(td, "transfer_design_condition.csv")))
  expect_true(file.exists(file.path(td, "transfer_feature_metadata.csv")))
  expect_equal(unique(diag$summary$block), c("history", "forecast"))
  expect_equal(diag$metadata$feature_name, c("PPT", "SOIL", "PCA"))
  expect_true(is.finite(diag$condition$condition_number[diag$condition$block == "history"]))
  expect_false(diag$condition$rank_deficient[diag$condition$block == "history"])
})
