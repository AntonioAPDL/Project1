source(file.path("..", "..", "R", "unified", "utils_scale.R"))

test_that("all declared scales convert deterministically to legacy log1p_cms", {
  x_raw <- c(1.2, 2.0, 10.0)

  expect_equal(unified_convert_scale(x_raw, "raw_cms", "log1p_cms"), log1p(x_raw), tolerance = 1e-12)
  expect_equal(unified_convert_scale(log(x_raw), "log_cms", "log1p_cms"), log1p(x_raw), tolerance = 1e-10)
  expect_equal(unified_convert_scale(log1p(x_raw), "log1p_cms", "log1p_cms"), log1p(x_raw), tolerance = 1e-12)
  expect_equal(unified_convert_scale(log(log(x_raw)), "log_log_cms", "log1p_cms"), log1p(x_raw), tolerance = 1e-10)
  expect_equal(unified_convert_scale(log(log1p(x_raw)), "log_log1p_cms", "log1p_cms"), log1p(x_raw), tolerance = 1e-10)
})

test_that("unknown scales fail fast", {
  expect_error(unified_convert_scale(c(1, 2), "bad_scale", "log1p_cms"), "from_scale")
  expect_error(unified_convert_scale(c(1, 2), "raw_cms", "bad_scale"), "to_scale")
})

test_that("scale conversions round trip for positive flows", {
  x_raw <- c(1e-6, 0.001, 0.1, 1, 10, 100)

  expect_equal(
    unified_convert_scale(unified_convert_scale(x_raw, "raw_cms", "log1p_cms"), "log1p_cms", "raw_cms"),
    x_raw,
    tolerance = 1e-12
  )
  expect_equal(
    unified_convert_scale(unified_convert_scale(x_raw, "raw_cms", "log_log1p_cms"), "log_log1p_cms", "raw_cms"),
    x_raw,
    tolerance = 1e-10
  )
  expect_equal(
    unified_convert_scale(log(log1p(x_raw)), "log_log1p_cms", "log1p_cms"),
    log1p(x_raw),
    tolerance = 1e-10
  )
})

test_that("log1p_cms handles exact-zero retrospectives but log_log1p_cms does not", {
  expect_equal(unified_convert_scale(0, "raw_cms", "log1p_cms"), 0)
  expect_error(
    unified_convert_scale(0, "raw_cms", "log_log1p_cms"),
    "Non-finite values produced"
  )
})

test_that("adapter guardrails enforce positive legacy-log input", {
  tmp_in <- tempfile(fileext = ".csv")
  tmp_out <- tempfile(fileext = ".csv")
  on.exit(unlink(c(tmp_in, tmp_out), force = TRUE), add = TRUE)

  utils::write.csv(data.frame(Date = c("d1", "d2"), v1 = c(0, 1), v2 = c(2, 3)), tmp_in, row.names = FALSE)

  expect_error(
    unified_adapt_csv_scale(tmp_in, tmp_out, from_scale = "raw_cms", to_scale = "raw_cms", positive_required = TRUE),
    "> 0"
  )
})
