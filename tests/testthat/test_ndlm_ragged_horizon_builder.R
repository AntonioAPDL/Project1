source(testthat::test_path("..", "..", "R", "unified", "families", "ndlm_main", "03_vb_updates.R"))

test_that("NDLM ragged horizon metadata is derived correctly for glofas extension", {
  meta <- ndlm_theory_build_ragged_horizon(
    list(K_vec = c(nws = 10L, glofas = 28L))
  )

  expect_equal(meta$K_overlap, 10L)
  expect_equal(meta$K_max, 28L)
  expect_equal(meta$K_tail, 18L)
  expect_equal(meta$extension_source, "glofas")
  expect_equal(meta$bridge_source, "nws")
  expect_equal(meta$segment_lengths[["overlap"]], 10L)
  expect_equal(meta$segment_lengths[["extension"]], 18L)
  expect_equal(length(meta$active_sources), 28L)
  expect_equal(length(meta$active_sources[[1L]]), 2L)
  expect_equal(length(meta$active_sources[[28L]]), 1L)
})

test_that("NDLM ragged horizon metadata is derived correctly for nws extension", {
  meta <- ndlm_theory_build_ragged_horizon(
    list(K_vec = c(nws = 21L, glofas = 12L))
  )

  expect_equal(meta$K_overlap, 12L)
  expect_equal(meta$K_max, 21L)
  expect_equal(meta$K_tail, 9L)
  expect_equal(meta$extension_source, "nws")
  expect_equal(meta$bridge_source, "glofas")
})

test_that("NDLM ragged horizon rejects invalid K_vec", {
  expect_error(
    ndlm_theory_build_ragged_horizon(list(K_vec = c(nws = 0L, glofas = 10L))),
    "requires positive K_vec"
  )
  expect_error(
    ndlm_theory_build_ragged_horizon(list(K_vec = c(nws = NA_integer_, glofas = 10L))),
    "requires positive K_vec"
  )
})

test_that("NDLM segment covariance supports inactive rows", {
  cov_arr <- ndlm_theory_alloc_segment_cov(k_len = 4L, w_fore = 0.1, inactive_row = 2L)
  expect_equal(dim(cov_arr), c(7L, 7L, 4L))
  expect_true(all(cov_arr[2, 2, ] < 1e-6))
  expect_true(all(cov_arr[1, 1, ] > cov_arr[2, 2, ]))
})

