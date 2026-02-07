test_that("sampling_truncnorm deterministic with fixed base seed", {
  skip_if_not_installed("Rcpp")
  skip_if_not_installed("BH")

  Sys.setenv(
    PKG_CXXFLAGS = "-I/data/muscat_data/jaguir26/libs/eigen -I/data/muscat_data/jaguir26/libs/boost/include -DEIGEN_DONT_VECTORIZE",
    PKG_LIBS = "-L/data/muscat_data/jaguir26/libs/lib64 -L/data/muscat_data/jaguir26/libs/boost/lib -llapack -lblas -lboost_random -lboost_system -fopenmp",
    LD_LIBRARY_PATH = "/data/muscat_data/jaguir26/libs/lib64:/data/muscat_data/jaguir26/libs/boost/lib:/lib64"
  )

  Sys.setenv(
    OMP_NUM_THREADS = "1",
    OPENBLAS_NUM_THREADS = "1",
    MKL_NUM_THREADS = "1",
    VECLIB_MAXIMUM_THREADS = "1",
    NUMEXPR_NUM_THREADS = "1"
  )

  Rcpp::sourceCpp(file.path("..", "..", "sampling_truncnorm.cpp"))

  mu <- c(0.2, 0.5, 1.0)
  sig2 <- c(0.7, 1.1, 0.9)

  set_sampling_truncnorm_seed(2026)
  x1 <- sample_truncnorm_icdf(n_samp = 16, TT = length(mu), sts_mu = mu, sts_sig2 = sig2)

  set_sampling_truncnorm_seed(2026)
  x2 <- sample_truncnorm_icdf(n_samp = 16, TT = length(mu), sts_mu = mu, sts_sig2 = sig2)

  set_sampling_truncnorm_seed(2027)
  x3 <- sample_truncnorm_icdf(n_samp = 16, TT = length(mu), sts_mu = mu, sts_sig2 = sig2)

  expect_equal(x1, x2, tolerance = 0)
  expect_gt(max(abs(x1 - x3)), 0)
})

test_that("sampling_exal deterministic with fixed base seed", {
  skip_if_not_installed("Rcpp")
  skip_if_not_installed("BH")
  skip_if_not_installed("RcppArmadillo")

  Sys.setenv(
    PKG_CXXFLAGS = "-I/data/muscat_data/jaguir26/libs/eigen -I/data/muscat_data/jaguir26/libs/boost/include -DEIGEN_DONT_VECTORIZE",
    PKG_LIBS = "-L/data/muscat_data/jaguir26/libs/lib64 -L/data/muscat_data/jaguir26/libs/boost/lib -llapack -lblas -lboost_random -lboost_system -fopenmp",
    LD_LIBRARY_PATH = "/data/muscat_data/jaguir26/libs/lib64:/data/muscat_data/jaguir26/libs/boost/lib:/lib64"
  )

  Sys.setenv(
    OMP_NUM_THREADS = "1",
    OPENBLAS_NUM_THREADS = "1",
    MKL_NUM_THREADS = "1",
    VECLIB_MAXIMUM_THREADS = "1",
    NUMEXPR_NUM_THREADS = "1"
  )

  Rcpp::sourceCpp(file.path("..", "..", "sampling_exal.cpp"))

  n <- 2
  TT <- 3
  n_samp <- 12
  sC <- array(0, dim = c(n, n, TT))
  for (t in seq_len(TT)) {
    sC[, , t] <- diag(c(1.0 + t / 10, 0.7 + t / 20), nrow = n)
  }
  sm <- matrix(c(0.1, -0.2, 0.3, -0.1, 0.2, 0.5), nrow = n, ncol = TT)

  set_sampling_exal_seed(3001)
  z1 <- DISC_sample_multivariate_normal(n_samp = n_samp, TT = TT, sC = sC, sm = sm, n = n)

  set_sampling_exal_seed(3001)
  z2 <- DISC_sample_multivariate_normal(n_samp = n_samp, TT = TT, sC = sC, sm = sm, n = n)

  set_sampling_exal_seed(3002)
  z3 <- DISC_sample_multivariate_normal(n_samp = n_samp, TT = TT, sC = sC, sm = sm, n = n)

  expect_equal(z1, z2, tolerance = 0)
  expect_gt(max(abs(z1 - z3)), 0)
})
