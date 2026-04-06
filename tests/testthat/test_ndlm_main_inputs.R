test_that("ndlm_main loader maps log1p adapters to log_log1p internal scale", {
  source("/data/muscat_data/jaguir26/project1_ucsc_phd/R/unified/families/shared_input_helpers.R", local = TRUE)
  source("/data/muscat_data/jaguir26/project1_ucsc_phd/R/unified/families/ndlm_main/01_inputs.R", local = TRUE)

  make_cov <- function(path, dates, value_name, values) {
    write.csv(
      data.frame(Date = as.Date(dates), value = values, check.names = FALSE),
      path,
      row.names = FALSE
    )
    df <- read.csv(path, check.names = FALSE)
    names(df)[names(df) == "value"] <- value_name
    write.csv(df, path, row.names = FALSE)
  }

  tmp_dir <- tempfile("ndlm_main_inputs_")
  dir.create(tmp_dir, recursive = TRUE, showWarnings = FALSE)
  on.exit(unlink(tmp_dir, recursive = TRUE, force = TRUE), add = TRUE)

  n_hist <- 35L
  hist_dates <- seq(as.Date("2021-01-01"), by = "day", length.out = n_hist)
  forecast_dates <- seq(as.Date("2021-02-05"), by = "day", length.out = 4L)

  retros_path <- file.path(tmp_dir, "retros.csv")
  nws_path <- file.path(tmp_dir, "nws.csv")
  glofas_path <- file.path(tmp_dir, "glofas.csv")
  eli_path <- file.path(tmp_dir, "eli.csv")
  oni_path <- file.path(tmp_dir, "oni.csv")
  ppt_path <- file.path(tmp_dir, "ppt.csv")
  soil_path <- file.path(tmp_dir, "soil.csv")
  pca_path <- file.path(tmp_dir, "pca.csv")

  usgs_log1p <- seq(1.10, 2.80, length.out = n_hist)
  glofas_log1p <- seq(1.20, 2.90, length.out = n_hist)
  nws_log1p <- seq(1.30, 3.00, length.out = n_hist)
  write.csv(
    data.frame(
      Date = hist_dates,
      USGS = usgs_log1p,
      GloFAS = glofas_log1p,
      NWS3.0 = nws_log1p
    ),
    retros_path,
    row.names = FALSE
  )

  nws_members_log1p <- data.frame(
    target_date = forecast_dates,
    member_01 = c(1.10, 1.20, 1.30, 1.40),
    member_02 = c(1.30, 1.40, 1.50, 1.60)
  )
  glofas_members_log1p <- data.frame(
    target_date = forecast_dates,
    member_01 = c(1.50, 1.60, 1.70, 1.80),
    member_02 = c(1.70, 1.80, 1.90, 2.00)
  )
  write.csv(nws_members_log1p, nws_path, row.names = FALSE)
  write.csv(glofas_members_log1p, glofas_path, row.names = FALSE)

  make_cov(eli_path, hist_dates, "ELI_lon", seq(10, 44, length.out = n_hist))
  make_cov(oni_path, hist_dates, "nino34", seq(1, 4.4, length.out = n_hist))
  make_cov(ppt_path, hist_dates, "PRCP_mm", seq(2, 8.8, length.out = n_hist))
  make_cov(soil_path, hist_dates, "Daily_Avg_Soil_Moisture", seq(3, 9.8, length.out = n_hist))
  make_cov(pca_path, hist_dates, "Static_PCA", seq(4, 10.8, length.out = n_hist))

  old_env <- Sys.getenv(
    c(
      "NDLM_RETROS_CSV", "NDLM_NWS_FORECAST_CSV", "NDLM_GLOFAS_FORECAST_CSV",
      "NDLM_COV1_ELI_CSV", "NDLM_COV2_ONI_CSV", "NDLM_PPT_CSV", "NDLM_SOIL_CSV", "NDLM_PCA_CSV"
    ),
    unset = NA_character_
  )
  on.exit({
    keys <- names(old_env)
    for (k in keys) {
      val <- old_env[[k]]
      if (is.na(val)) {
        Sys.unsetenv(k)
      } else {
        Sys.setenv(structure(val, names = k))
      }
    }
  }, add = TRUE)

  Sys.setenv(
    NDLM_RETROS_CSV = retros_path,
    NDLM_NWS_FORECAST_CSV = nws_path,
    NDLM_GLOFAS_FORECAST_CSV = glofas_path,
    NDLM_COV1_ELI_CSV = eli_path,
    NDLM_COV2_ONI_CSV = oni_path,
    NDLM_PPT_CSV = ppt_path,
    NDLM_SOIL_CSV = soil_path,
    NDLM_PCA_CSV = pca_path
  )

  inputs <- ndlm_theory_load_inputs(horizon_cap = 4L)

  expect_equal(inputs$y[1], log(usgs_log1p[1]))
  expect_equal(inputs$retros$nws[1], log(nws_log1p[1]))
  expect_equal(inputs$retros$glofas[1], log(glofas_log1p[1]))
  expect_equal(
    inputs$forecast$nws[1],
    mean(log(c(nws_members_log1p$member_01[1], nws_members_log1p$member_02[1])))
  )
  expect_equal(
    inputs$forecast$glofas[1],
    mean(log(c(glofas_members_log1p$member_01[1], glofas_members_log1p$member_02[1])))
  )
  expect_equal(dim(inputs$forecast$nws_members), c(4L, 2L))
  expect_equal(dim(inputs$forecast$glofas_members), c(4L, 2L))
  expect_equal(inputs$forecast$nws_members[1, 1], log(nws_members_log1p$member_01[1]))
  expect_equal(inputs$forecast$nws_members[1, 2], log(nws_members_log1p$member_02[1]))
  expect_equal(inputs$forecast$glofas_members[4, 1], log(glofas_members_log1p$member_01[4]))
  expect_equal(inputs$forecast$glofas_members[4, 2], log(glofas_members_log1p$member_02[4]))
})
