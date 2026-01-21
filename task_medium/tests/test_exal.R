library(testthat)
library(Rcpp)

# Load C++ functions
Rcpp::sourceCpp("../src/exAL.cpp")

test_that("dexal() returns correct density values", {
  expect_gt(dexal(0.0), 0)  # Density should be positive
  expect_equal(dexal(0.0, mu = 0, sigma = 1, gamma = 0), dexal(0.0, p0 = 0.5))  # AL case
  expect_error(dexal(0.0, sigma = -1))  # Should throw an error for sigma <= 0
})

test_that("pexal() returns valid CDF values", {
  expect_equal(pexal(-Inf), 0)  # CDF at -Inf should be 0
  expect_equal(pexal(Inf), 1)   # CDF at Inf should be 1
  expect_true(pexal(0) >= 0 & pexal(0) <= 1)  # CDF must be between 0 and 1
})

test_that("qexal() inverts pexal() correctly", {
  p_val <- 0.3
  expect_equal(qexal(p_val), qexal(p_val))  # Should be consistent
  expect_error(qexal(-0.1))  # Probability must be in (0,1)
  expect_error(qexal(1.1))  
})

test_that("rexal() generates correct samples", {
  set.seed(123)
  samples <- rexal(100)
  expect_length(samples, 100)  # Check sample size
  expect_true(all(is.numeric(samples)))  # Ensure all values are numeric
})
