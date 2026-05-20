source(testthat::test_path("..", "..", "R", "disc_w", "09_state_blend.R"))

test_that("disc_blend_numeric_like handles NULL optional payloads", {
  mat <- matrix(1:4, nrow = 2)

  expect_null(disc_blend_numeric_like(NULL, NULL, 0.5))
  expect_equal(disc_blend_numeric_like(NULL, mat, 0.5), mat)
  expect_equal(disc_blend_numeric_like(mat, NULL, 0.5), mat)
})

test_that("disc_blend_numeric_like preserves dimension checks", {
  expect_error(
    disc_blend_numeric_like(matrix(1:4, nrow = 2), 1:3, 0.5, "theta$sm"),
    "blend dim mismatch"
  )
})

test_that("disc_blend_numeric_list handles NULL list payloads", {
  lst <- list(1:3, matrix(1:4, nrow = 2))

  expect_null(disc_blend_numeric_list(NULL, NULL, 0.5))
  expect_equal(disc_blend_numeric_list(NULL, lst, 0.5), lst)
  expect_equal(disc_blend_numeric_list(lst, NULL, 0.5), lst)
})
