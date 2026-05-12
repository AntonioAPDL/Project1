source(file.path("..", "..", "R", "disc_w", "07_sampling_contracts.R"))

test_that("disc_w_prepare_sampling_state reconstructs dropped matrix and cube dims", {
  sm_matrix <- matrix(seq_len(12), nrow = 3, ncol = 4)
  sC_cube <- array(seq_len(36), dim = c(3, 3, 4))

  out <- disc_w_prepare_sampling_state(
    sm = as.numeric(sm_matrix),
    sC = as.numeric(sC_cube),
    TT_expected = 4L,
    n_expected = 3L,
    label = "retro_test"
  )

  expect_true(is.matrix(out$sm))
  expect_equal(dim(out$sm), c(3, 4))
  expect_equal(out$sm, sm_matrix)

  expect_true(is.array(out$sC))
  expect_equal(dim(out$sC), c(3, 3, 4))
  expect_equal(out$sC, sC_cube)
  expect_equal(out$n, 3L)
  expect_equal(out$TT, 4L)
})

test_that("disc_w_prepare_sampling_state accepts already-shaped payloads", {
  sm_matrix <- matrix(runif(6), nrow = 2, ncol = 3)
  sC_cube <- array(runif(12), dim = c(2, 2, 3))

  out <- disc_w_prepare_sampling_state(
    sm = sm_matrix,
    sC = sC_cube,
    TT_expected = 3L,
    n_expected = 2L,
    label = "forecast_test"
  )

  expect_equal(out$sm, sm_matrix)
  expect_equal(out$sC, sC_cube)
})

test_that("disc_w_prepare_sampling_state rejects mismatched payload sizes", {
  expect_error(
    disc_w_prepare_sampling_state(
      sm = 1:11,
      sC = array(seq_len(36), dim = c(3, 3, 4)),
      TT_expected = 4L,
      n_expected = 3L,
      label = "bad_sm"
    ),
    "length mismatch"
  )

  expect_error(
    disc_w_prepare_sampling_state(
      sm = matrix(seq_len(12), nrow = 3, ncol = 4),
      sC = 1:35,
      TT_expected = 4L,
      n_expected = 3L,
      label = "bad_sC"
    ),
    "length mismatch"
  )
})
