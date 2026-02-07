#!/usr/bin/env Rscript

# Targeted micro-test for D2 (sampler equivalence + reproducibility).
# This script:
# - compiles both C++ implementations (reject vs icdf),
# - compares sample moments to truncated-normal theory,
# - checks reproducibility under set.seed(),
# - reports rough runtime.
#
# Usage:
#   Rscript repro/test_truncnorm_equivalence.R

suppressWarnings(suppressMessages({
  library(Rcpp)
}))

args <- commandArgs(trailingOnly = FALSE)
file_arg <- sub("^--file=", "", args[grep("^--file=", args)])
script_path <- if (length(file_arg) == 1) normalizePath(file_arg) else NA_character_
repo_root <- if (!is.na(script_path)) normalizePath(file.path(dirname(script_path), "..")) else getwd()
setwd(repo_root)

cat("Repo root:", repo_root, "\n")

# Force deterministic threading for reproducibility checks.
Sys.setenv(OMP_NUM_THREADS = "1")

cat("Compiling C++ (sampling_exal.cpp)\n")
sourceCpp("sampling_exal.cpp", rebuild = TRUE, verbose = FALSE)
stopifnot(exists("sample_truncnorm_reject", mode = "function"))

cat("Compiling C++ (sampling_truncnorm.cpp)\n")
sourceCpp("sampling_truncnorm.cpp", rebuild = TRUE, verbose = FALSE)
stopifnot(exists("sample_truncnorm_icdf", mode = "function"))
stopifnot(exists("sample_truncnorm", mode = "function")) # alias

softplus <- function(x) {
  # stable log(1+exp(x))
  log1p(exp(-abs(x))) + pmax(x, 0)
}

tn_moments_lower0 <- function(mu, sig2) {
  sd <- sqrt(sig2)
  alpha <- (0 - mu) / sd
  Z <- 1 - pnorm(alpha)
  lambda <- dnorm(alpha) / Z
  mean <- mu + sd * lambda
  var <- sig2 * (1 + alpha * lambda - lambda^2)
  list(mean = mean, var = var)
}

check_repro <- function(fn, n_samp, TT, mu, sig2, label) {
  set.seed(123)
  x1 <- fn(n_samp, TT, mu, sig2)
  set.seed(123)
  x2 <- fn(n_samp, TT, mu, sig2)
  identical_run <- isTRUE(all.equal(x1, x2, tolerance = 0))

  set.seed(124)
  x3 <- fn(n_samp, TT, mu, sig2)
  different_seed_changes <- !isTRUE(all.equal(x1, x3, tolerance = 0))

  cat(sprintf("[%s] reproducible under set.seed(): %s\n", label, identical_run))
  cat(sprintf("[%s] different seed changes draws: %s\n", label, different_seed_changes))
  invisible(list(repro = identical_run, seed_effect = different_seed_changes))
}

summarize_moments <- function(samples, mu, sig2) {
  # samples: n_samp x TT
  sm <- colMeans(samples)
  sv <- apply(samples, 2, var)
  th <- tn_moments_lower0(mu, sig2)
  err_mean <- sm - th$mean
  err_var <- sv - th$var
  list(
    sample_mean = sm,
    sample_var = sv,
    theo_mean = th$mean,
    theo_var = th$var,
    max_abs_mean_err = max(abs(err_mean)),
    max_abs_var_err = max(abs(err_var)),
    rmse_mean = sqrt(mean(err_mean^2)),
    rmse_var = sqrt(mean(err_var^2))
  )
}

run_benchmark <- function(fn, n_samp, TT, mu, sig2) {
  t <- system.time({
    x <- fn(n_samp, TT, mu, sig2)
  })
  list(time = t, x = x)
}

mu_grid <- c(-2, -1, -0.5, 0, 0.5, 1, 2)
sig2_grid <- c(0.25, 1, 4)
grid <- expand.grid(mu = mu_grid, sig2 = sig2_grid)
mu_vec <- grid$mu
sig2_vec <- grid$sig2
TT <- length(mu_vec)

cat(sprintf("Grid size TT=%d (mu x sig2)\n", TT))

cat("\n== Reproducibility checks (OMP_NUM_THREADS=1) ==\n")
check_repro(sample_truncnorm_reject, n_samp = 2000, TT = TT, mu = mu_vec, sig2 = sig2_vec, label = "reject")
check_repro(sample_truncnorm_icdf,   n_samp = 2000, TT = TT, mu = mu_vec, sig2 = sig2_vec, label = "icdf")

cat("\n== Moment checks vs truncated-normal theory ==\n")
n_samp_mom <- 20000

cat(sprintf("Sampling n_samp=%d for reject...\n", n_samp_mom))
res_reject <- run_benchmark(sample_truncnorm_reject, n_samp_mom, TT, mu_vec, sig2_vec)
m_reject <- summarize_moments(res_reject$x, mu_vec, sig2_vec)
cat(sprintf("[reject] time: %.3fs\n", res_reject$time[["elapsed"]]))
cat(sprintf("[reject] max |mean error|: %.4g; RMSE(mean): %.4g\n", m_reject$max_abs_mean_err, m_reject$rmse_mean))
cat(sprintf("[reject] max |var  error|: %.4g; RMSE(var):  %.4g\n", m_reject$max_abs_var_err, m_reject$rmse_var))

cat(sprintf("Sampling n_samp=%d for icdf...\n", n_samp_mom))
res_icdf <- run_benchmark(sample_truncnorm_icdf, n_samp_mom, TT, mu_vec, sig2_vec)
m_icdf <- summarize_moments(res_icdf$x, mu_vec, sig2_vec)
cat(sprintf("[icdf] time: %.3fs\n", res_icdf$time[["elapsed"]]))
cat(sprintf("[icdf] max |mean error|: %.4g; RMSE(mean): %.4g\n", m_icdf$max_abs_mean_err, m_icdf$rmse_mean))
cat(sprintf("[icdf] max |var  error|: %.4g; RMSE(var):  %.4g\n", m_icdf$max_abs_var_err, m_icdf$rmse_var))

cat("\n== Done ==\n")

