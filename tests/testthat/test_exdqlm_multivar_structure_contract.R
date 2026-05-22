source(testthat::test_path("..", "..", "R", "unified", "families", "exdqlm_multivar_structure.R"))

test_that("multivariate keep harmonic indices map to legacy harmonic values", {
  spec <- exdqlm_multivar_read_structure_spec(
    include_trend_raw = TRUE,
    enabled_harmonic_indices_raw = c(1L, 2L, 3L)
  )

  expect_true(spec$include_trend)
  expect_equal(spec$enabled_harmonic_indices, c(1L, 2L, 3L))
  expect_equal(spec$enabled_harmonics, c(1, 2, 1 / 6.8068493))
  expect_equal(spec$disabled_harmonic_indices, integer(0))
})

test_that("multivariate keep all/default harmonic aliases keep the same legacy basis", {
  expect_equal(
    exdqlm_multivar_read_structure_spec(enabled_harmonic_indices_raw = "all")$enabled_harmonics,
    c(1, 2, 1 / 6.8068493)
  )
  expect_equal(
    exdqlm_multivar_read_structure_spec(enabled_harmonic_indices_raw = "default")$enabled_harmonic_indices,
    c(1L, 2L, 3L)
  )
})
