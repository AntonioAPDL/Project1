source(testthat::test_path("..", "..", "R", "environmetrics", "02_helpers_core.R"))

test_that("compute_jsd_to_standard_normal supports univariate forecast-error samples", {
  skip_if_not_installed("ks")
  skip_if_not_installed("mvtnorm")

  set.seed(123)
  sample_1d <- matrix(rnorm(600), ncol = 1L)
  jsd <- compute_jsd_to_standard_normal(
    sample_1d,
    gridsize = 40L,
    context = "test.ndlm.1d"
  )

  expect_true(is.finite(jsd))
  expect_gte(jsd, 0)
})

test_that("compute_jsd_to_standard_normal supports multivariate forecast-error samples", {
  skip_if_not_installed("ks")
  skip_if_not_installed("mvtnorm")

  set.seed(456)
  sample_3d <- matrix(rnorm(2400), ncol = 3L)
  jsd <- compute_jsd_to_standard_normal(
    sample_3d,
    gridsize = c(12L, 12L, 12L),
    context = "test.exal.3d"
  )

  expect_true(is.finite(jsd))
  expect_gte(jsd, 0)
})

test_that("prepare_jsd_sample_matrix fails on malformed/non-numeric samples", {
  bad_sample <- matrix(c("a", "b", "c"), ncol = 1L)
  expect_error(
    prepare_jsd_sample_matrix(bad_sample, context = "test.bad.sample"),
    "\\[JSD_INPUT_TYPE\\]"
  )
})

test_that("compute_jsd_to_standard_normal fails with actionable error on invalid sample shape", {
  skip_if_not_installed("ks")
  skip_if_not_installed("mvtnorm")

  too_few <- matrix(c(NA_real_, NaN, Inf, 1.0), ncol = 1L)
  expect_error(
    compute_jsd_to_standard_normal(too_few, gridsize = 10L, context = "test.too_few"),
    "\\[JSD_INPUT_ROWS\\]"
  )

  high_dim <- matrix(rnorm(500), ncol = 5L)
  expect_error(
    compute_jsd_to_standard_normal(high_dim, gridsize = 10L, context = "test.high_dim"),
    "\\[JSD_DIMENSION\\]"
  )
})

test_that("compute_jsd_to_standard_normal accepts vector input and returns finite JSD", {
  skip_if_not_installed("ks")
  skip_if_not_installed("mvtnorm")

  set.seed(789)
  sample_vec <- rnorm(800)
  jsd <- compute_jsd_to_standard_normal(
    sample_vec,
    gridsize = 40L,
    context = "test.vector_input"
  )

  expect_true(is.finite(jsd))
  expect_gte(jsd, 0)
})

test_that("compute_jsd_to_standard_normal handles tied univariate samples with zero IQR", {
  skip_if_not_installed("ks")
  skip_if_not_installed("mvtnorm")

  tied_sample <- c(
    rep(0.99288822064787, 16),
    rep(0.96163822064787, 5),
    1.11415553136375,
    1.09706604607862,
    1.07831118264989,
    1.05706160616933,
    1.03331039082590,
    1.00997123760308,
    0.98622152547626
  )
  expect_equal(IQR(tied_sample), 0)
  expect_gt(stats::sd(tied_sample), 0)

  jsd <- compute_jsd_to_standard_normal(
    tied_sample,
    gridsize = 40L,
    context = "test.tied_1d"
  )

  expect_true(is.finite(jsd))
  expect_gte(jsd, 0)
})

test_that("compute_jsd_to_standard_normal handles exact constant univariate samples", {
  skip_if_not_installed("ks")
  skip_if_not_installed("mvtnorm")

  const_sample <- rep(1, 40)
  jsd <- compute_jsd_to_standard_normal(
    const_sample,
    gridsize = 30L,
    context = "test.constant_1d"
  )

  expect_true(is.finite(jsd))
  expect_gte(jsd, 0)
})

test_that("compute_jsd_to_standard_normal falls back for multivariate samples with degenerate axes", {
  skip_if_not_installed("ks")
  skip_if_not_installed("mvtnorm")

  set.seed(20260324)
  sample_3d <- cbind(
    rep(0, 120),
    rnorm(120),
    rnorm(120, sd = 0.1)
  )

  jsd <- compute_jsd_to_standard_normal(
    sample_3d,
    gridsize = c(8L, 8L, 8L),
    context = "test.degenerate_axis_3d"
  )

  expect_true(is.finite(jsd))
  expect_gte(jsd, 0)
})
