source(testthat::test_path("..", "..", "R", "disc_w", "02_io_loaders.R"))

test_that("disc_w_require_rdata_objects returns required objects from dedicated env", {
  tmp <- tempfile(fileext = ".RData")
  obj_a <- list(value = 1)
  obj_b <- matrix(1:4, nrow = 2)
  save(obj_a, obj_b, file = tmp)
  on.exit(unlink(tmp), add = TRUE)

  out <- disc_w_require_rdata_objects(tmp, c("obj_a", "obj_b"))

  expect_named(out, c("obj_a", "obj_b"))
  expect_equal(out$obj_a$value, 1)
  expect_equal(out$obj_b, matrix(1:4, nrow = 2))
})

test_that("disc_w_require_rdata_objects errors clearly when names are missing", {
  tmp <- tempfile(fileext = ".RData")
  obj_a <- list(value = 1)
  save(obj_a, file = tmp)
  on.exit(unlink(tmp), add = TRUE)

  expect_error(
    disc_w_require_rdata_objects(tmp, c("obj_a", "obj_b")),
    "missing required objects: obj_b"
  )
})
