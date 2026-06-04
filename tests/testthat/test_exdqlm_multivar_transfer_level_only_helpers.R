source(testthat::test_path("..", "..", "R", "environmetrics", "02_helpers_core.R"))

test_that("discount matrix helpers skip zero-sized transfer covariate blocks", {
  mat <- make_df_mat(c(0.97, 0.99), c(1L, 0L), 1L)
  mat_k <- make_df_mat_k(c(0.97, 0.99), c(1L, 0L), 1L, 3L)

  expect_equal(dim(mat), c(1L, 1L))
  expect_equal(dim(mat_k), c(1L, 1L))
  expect_equal(as.numeric(mat[1, 1]), (1 - 0.97) / 0.97)
  expect_equal(as.numeric(mat_k[1, 1]), (1 - 0.97^3) / 0.97^3)
})

test_that("legacy DISC entrypoints guard transfer-level-only indexing", {
  project_root <- testthat::test_path("..", "..")
  drop_text <- readLines(file.path(project_root, "DISC_Optimal_Synth_Ranges_W.r"), warn = FALSE)
  keep_text <- readLines(file.path(project_root, "DISC_Optimal_Synth_Ranges_W_transfer_forecast.r"), warn = FALSE)

  expect_true(any(grepl("if \\(ppx > 1L\\)", drop_text)))
  expect_true(any(grepl("if \\(ppx > 1L\\)", keep_text)))
  expect_true(any(grepl("dim.df[j] <= 0L", drop_text, fixed = TRUE)))
  expect_true(any(grepl("dim.df[j] <= 0L", keep_text, fixed = TRUE)))
})
