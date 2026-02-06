#!/usr/bin/env Rscript

options(stringsAsFactors = FALSE)

draw_loop <- function(Ft, mus, sigmas, n_samp) {
  stopifnot(is.numeric(Ft))
  stopifnot(length(mus) == 8)
  stopifnot(length(sigmas) == 8)

  out <- matrix(NA_real_, nrow = n_samp, ncol = 8)
  for (i in seq_len(8)) {
    Mu <- mus[[i]]
    Sigma <- sigmas[[i]]
    out[, i] <- rnorm(
      n = n_samp,
      mean = as.numeric(t(Ft) %*% Mu),
      sd = as.numeric(sqrt(t(Ft) %*% Sigma %*% Ft))
    )
  }
  out
}

draw_batch <- function(Ft, mus, sigmas, n_samp) {
  stopifnot(is.numeric(Ft))
  stopifnot(length(mus) == 8)
  stopifnot(length(sigmas) == 8)

  means <- vapply(
    X = seq_len(8),
    FUN.VALUE = numeric(1),
    FUN = function(i) as.numeric(t(Ft) %*% mus[[i]])
  )
  sds <- vapply(
    X = seq_len(8),
    FUN.VALUE = numeric(1),
    FUN = function(i) as.numeric(sqrt(t(Ft) %*% sigmas[[i]] %*% Ft))
  )

  draws <- rnorm(
    n = n_samp * length(means),
    mean = rep(means, each = n_samp),
    sd = rep(sds, each = n_samp)
  )
  matrix(draws, nrow = n_samp, ncol = length(means))
}

RNGkind("Mersenne-Twister", "Inversion", "Rounding")
set.seed(777)

p <- 21
n_samp <- 50
Ft <- rnorm(p)

mus <- replicate(8, rnorm(p), simplify = FALSE)
sigmas <- replicate(8, {
  A <- matrix(rnorm(p * p), nrow = p)
  tcrossprod(A) + diag(p) * 1e-3
}, simplify = FALSE)

set.seed(777)
out_loop <- draw_loop(Ft, mus, sigmas, n_samp)

set.seed(777)
out_batch <- draw_batch(Ft, mus, sigmas, n_samp)

if (!identical(out_loop, out_batch)) {
  stop("RNG stability test failed: batch draw is not identical to sequential draws.")
}

cat("OK: sample_xbs_retro RNG stability test passed.\n")
