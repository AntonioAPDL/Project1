test_that("shared covariate helper picks value columns instead of time-like columns", {
  source("/data/muscat_data/jaguir26/project1_ucsc_phd/R/unified/families/shared_input_helpers.R", local = TRUE)

  eli_df <- data.frame(
    time = c(68300, 68301, 68302),
    ELI_lon = c(218.8, 219.3, 218.9)
  )
  oni_df <- data.frame(
    time = as.Date(c("1987-01-01", "1987-01-02", "1987-01-03")),
    nino12 = c(0.8, 0.7, 0.6),
    nino34 = c(1.0, 0.9, 0.8)
  )

  expect_equal(
    family_shared_pick_numeric_column(eli_df, preferred = family_shared_covariate_preferences("ELI")),
    eli_df$ELI_lon
  )
  expect_equal(
    family_shared_pick_numeric_column(oni_df, preferred = family_shared_covariate_preferences("ONI")),
    oni_df$nino34
  )
})

test_that("shared covariate helper aligns by date and scales by historical sd", {
  source("/data/muscat_data/jaguir26/project1_ucsc_phd/R/unified/families/shared_input_helpers.R", local = TRUE)

  cov_path <- tempfile(fileext = ".csv")
  on.exit(unlink(cov_path), add = TRUE)
  write.csv(
    data.frame(
      Date = as.Date(c("2021-01-01", "2021-01-02", "2021-01-03", "2021-01-04")),
      PRCP_mm = c(1, 2, 4, 8)
    ),
    cov_path,
    row.names = FALSE
  )

  out <- family_shared_build_covariate_series(
    path = cov_path,
    cov_name = "PPT",
    history_dates = as.Date(c("2021-01-01", "2021-01-02", "2021-01-03")),
    forecast_dates = as.Date(c("2021-01-04", "2021-01-05")),
    fill_value = 0,
    scale_with_history = TRUE
  )

  hist_sd <- stats::sd(c(1, 2, 4))
  expect_equal(out$history, c(1, 2, 4) / hist_sd)
  expect_equal(out$forecast[1], 8 / hist_sd)
  expect_equal(out$forecast[2], 8 / hist_sd)
})

test_that("shared forecast helper uses ensemble mean with requested transform", {
  source("/data/muscat_data/jaguir26/project1_ucsc_phd/R/unified/families/shared_input_helpers.R", local = TRUE)

  fc_df <- data.frame(
    target_date = as.Date(c("2021-01-01", "2021-01-02")),
    member_01 = c(1, 3),
    member_02 = c(3, 5)
  )

  expect_equal(
    family_shared_extract_forecast_mean(fc_df, label = "fc", transform = "none"),
    c(2, 4)
  )
  expect_equal(
    family_shared_extract_forecast_mean(fc_df, label = "fc", transform = "log1p"),
    rowMeans(log1p(as.matrix(fc_df[, c("member_01", "member_02")])))
  )
})
