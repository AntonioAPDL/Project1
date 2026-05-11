source(testthat::test_path("..", "..", "R", "environmetrics", "02_helpers_core.R"))

testthat::test_that("post_requested_quantile_labels defaults to full ladder", {
  withr::local_envvar(c(UNIFIED_FIT_QUANTILE_LABELS = NA_character_))
  testthat::expect_equal(
    post_requested_quantile_labels(),
    c("05", "20", "35", "50", "65", "80", "95")
  )
})

testthat::test_that("post_requested_quantile_spec sorts and normalizes subset labels", {
  withr::local_envvar(c(UNIFIED_FIT_QUANTILE_LABELS = "95,50,05,50"))
  spec <- post_requested_quantile_spec()
  testthat::expect_equal(spec$labels, c("05", "50", "95"))
  testthat::expect_equal(spec$tags, c("5", "50", "95"))
  testthat::expect_equal(spec$probs, c(0.05, 0.50, 0.95))
})

testthat::test_that("post_requested_quantile_spec falls back on invalid env input", {
  withr::local_envvar(c(UNIFIED_FIT_QUANTILE_LABELS = "abc,def"))
  spec <- post_requested_quantile_spec()
  testthat::expect_equal(spec$labels, c("05", "20", "35", "50", "65", "80", "95"))
})
