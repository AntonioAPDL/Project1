#!/usr/bin/env Rscript

options(stringsAsFactors = FALSE)

stopifnot(
  getRversion() >= "3.0.0"
)

build_xb_loop <- function(F_s, theta_arr) {
  stopifnot(is.numeric(F_s))
  stopifnot(is.array(theta_arr))
  stopifnot(length(dim(theta_arr)) == 3)
  stopifnot(dim(theta_arr)[1] == length(F_s))

  n_samp <- dim(theta_arr)[3]
  seg_len <- dim(theta_arr)[2]

  out <- vapply(
    X = seq_len(n_samp),
    FUN.VALUE = numeric(seg_len),
    FUN = function(s) {
      as.vector(crossprod(F_s, theta_arr[, , s, drop = TRUE]))
    }
  )
  # vapply returns seg_len x n_samp matrix
  out
}

build_xb_vec <- function(F_s, theta_arr) {
  stopifnot(is.numeric(F_s))
  stopifnot(is.array(theta_arr))
  stopifnot(length(dim(theta_arr)) == 3)
  stopifnot(dim(theta_arr)[1] == length(F_s))

  n_samp <- dim(theta_arr)[3]
  seg_len <- dim(theta_arr)[2]
  p <- length(F_s)

  theta_mat <- matrix(theta_arr, nrow = p)
  xb_vec <- as.vector(crossprod(F_s, theta_mat))
  xb_mat <- matrix(xb_vec, nrow = seg_len, ncol = n_samp)
  xb_mat
}

build_discrep_loop <- function(F_const, theta_arr, rows) {
  stopifnot(is.numeric(F_const))
  stopifnot(is.array(theta_arr))
  stopifnot(length(dim(theta_arr)) == 3)
  stopifnot(length(rows) == length(F_const))

  n_samp <- dim(theta_arr)[3]
  tt <- dim(theta_arr)[2]

  out <- vapply(
    X = seq_len(n_samp),
    FUN.VALUE = numeric(tt),
    FUN = function(s) {
      as.vector(crossprod(F_const, theta_arr[rows, , s, drop = TRUE]))
    }
  )
  out
}

build_discrep_vec <- function(F_const, theta_arr, rows) {
  stopifnot(is.numeric(F_const))
  stopifnot(is.array(theta_arr))
  stopifnot(length(dim(theta_arr)) == 3)
  stopifnot(length(rows) == length(F_const))

  n_samp <- dim(theta_arr)[3]
  tt <- dim(theta_arr)[2]

  theta_mat <- matrix(theta_arr[rows, , ], nrow = length(rows))
  d_vec <- as.vector(crossprod(F_const, theta_mat))
  d_mat <- matrix(d_vec, nrow = tt, ncol = n_samp)
  d_mat
}

set.seed(123)
p <- 7
seg_len <- 11
n_samp <- 13

F_s <- rnorm(p)
theta_arr <- array(rnorm(p * seg_len * n_samp), dim = c(p, seg_len, n_samp))

xb_loop <- build_xb_loop(F_s, theta_arr)
xb_vec <- build_xb_vec(F_s, theta_arr)

max_abs <- max(abs(xb_loop - xb_vec))
if (max_abs > 1e-12) {
  stop(sprintf("build_xb vectorization mismatch (max abs diff %.3e).", max_abs))
}

# Simulate the "j==J" shape that is later aperm'd into p x seg_len x n_samp
theta_raw_jJ <- aperm(theta_arr, c(1, 3, 2)) # p x n_samp x seg_len
theta_norm_jJ <- aperm(theta_raw_jJ, c(1, 3, 2))

if (!identical(theta_norm_jJ, theta_arr)) {
  stop("aperm normalization sanity check failed.")
}

# Discrepancy: theta is 21 x TT x n_samp; we test rows 8:14 and 15:21
tt <- 17
theta_disc <- array(rnorm(21 * tt * n_samp), dim = c(21, tt, n_samp))
F_const <- rnorm(p)

d1_loop <- build_discrep_loop(F_const, theta_disc, 8:14)
d1_vec <- build_discrep_vec(F_const, theta_disc, 8:14)
max_abs <- max(abs(d1_loop - d1_vec))
if (max_abs > 1e-12) {
  stop(sprintf("discrepancy d1 vectorization mismatch (max abs diff %.3e).", max_abs))
}

d2_loop <- build_discrep_loop(F_const, theta_disc, 15:21)
d2_vec <- build_discrep_vec(F_const, theta_disc, 15:21)
max_abs <- max(abs(d2_loop - d2_vec))
if (max_abs > 1e-12) {
  stop(sprintf("discrepancy d2 vectorization mismatch (max abs diff %.3e).", max_abs))
}

cat("OK: build_xbs_discrep vectorization equivalence tests passed.\n")
