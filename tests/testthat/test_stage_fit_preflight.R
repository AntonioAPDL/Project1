source(testthat::test_path("..", "..", "R", "unified", "stages", "stage_fit.R"))

make_retros_csv <- function(path, finite_n) {
  total_n <- max(40L, as.integer(finite_n) + 5L)
  usgs <- c(seq_len(as.integer(finite_n)), rep(NA_real_, total_n - as.integer(finite_n)))
  retros <- data.frame(
    Date = as.character(seq.Date(as.Date("2020-01-01"), by = "day", length.out = total_n)),
    USGS = usgs,
    GloFAS = seq_len(total_n) + 100,
    "NWS3.0" = seq_len(total_n) + 200,
    check.names = FALSE
  )
  utils::write.csv(retros, path, row.names = FALSE)
}

test_that("NDLM retros preflight counts finite observations from USGS history", {
  td <- tempfile("stage_fit_retros_count_")
  dir.create(td, recursive = TRUE, showWarnings = FALSE)
  on.exit(unlink(td, recursive = TRUE, force = TRUE), add = TRUE)

  retros_path <- file.path(td, "retros.csv")
  make_retros_csv(retros_path, finite_n = 21L)

  inspection <- unified_inspect_ndlm_retros_history(retros_path)

  expect_equal(inspection$history_column, "USGS")
  expect_equal(inspection$finite_count, 21L)
  expect_equal(inspection$total_rows, 40L)
})

test_that("NDLM retros preflight fails early on insufficient history", {
  td <- tempfile("stage_fit_retros_fail_")
  dir.create(td, recursive = TRUE, showWarnings = FALSE)
  on.exit(unlink(td, recursive = TRUE, force = TRUE), add = TRUE)

  retros_path <- file.path(td, "retros.csv")
  report_path <- file.path(td, "ndlm_retros_history_check.txt")
  make_retros_csv(retros_path, finite_n = 21L)

  expect_error(
    unified_assert_ndlm_retros_history(retros_path, min_required = 30L, report_path = report_path),
    "\\[NDLM_RETROS_HISTORY\\].*finite_count=21.*minimum_required=30"
  )
  expect_true(file.exists(report_path))
})

test_that("NDLM retros preflight passes with sufficient history", {
  td <- tempfile("stage_fit_retros_pass_")
  dir.create(td, recursive = TRUE, showWarnings = FALSE)
  on.exit(unlink(td, recursive = TRUE, force = TRUE), add = TRUE)

  retros_path <- file.path(td, "retros.csv")
  report_path <- file.path(td, "ndlm_retros_history_check.txt")
  make_retros_csv(retros_path, finite_n = 35L)

  inspection <- unified_assert_ndlm_retros_history(retros_path, min_required = 30L, report_path = report_path)

  expect_equal(inspection$history_column, "USGS")
  expect_equal(inspection$finite_count, 35L)
  expect_true(file.exists(report_path))
})
