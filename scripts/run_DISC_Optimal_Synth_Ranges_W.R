#!/usr/bin/env Rscript

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 1) {
  stop("Usage: Rscript scripts/run_DISC_Optimal_Synth_Ranges_W.R <p0> [seed]", call. = FALSE)
}

p0 <- as.numeric(args[[1]])
if (!is.finite(p0)) stop("p0 must be numeric.", call. = FALSE)

seed <- if (length(args) >= 2) as.integer(args[[2]]) else as.integer(Sys.getenv("DISC_SEED", "777"))
if (!is.finite(seed)) stop("seed must be integer-like.", call. = FALSE)

# Determinism / stability (Stage 0 baseline):
# - single-threaded math + OpenMP backends
# - stable RNG
Sys.setenv(
  OMP_NUM_THREADS = Sys.getenv("OMP_NUM_THREADS", "1"),
  OPENBLAS_NUM_THREADS = Sys.getenv("OPENBLAS_NUM_THREADS", "1"),
  MKL_NUM_THREADS = Sys.getenv("MKL_NUM_THREADS", "1"),
  VECLIB_MAXIMUM_THREADS = Sys.getenv("VECLIB_MAXIMUM_THREADS", "1"),
  NUMEXPR_NUM_THREADS = Sys.getenv("NUMEXPR_NUM_THREADS", "1"),
  DISC_BASE_SEED = as.character(seed)
)
options(mc.cores = 1)

set.seed(seed)
RNGkind("Mersenne-Twister", "Inversion", "Rejection")

# Keep the contract: call the existing entrypoint without editing it.
# `commandArgs(trailingOnly=TRUE)` inside the sourced script will see the same args.
if (Sys.getenv("DISC_RPROF", "") == "1") {
  dir.create("repro/perf", recursive = TRUE, showWarnings = FALSE)
  Rprof("repro/perf/Rprof.out")
  on.exit(Rprof(NULL), add = TRUE)
}
source("DISC_Optimal_Synth_Ranges_W.r", chdir = TRUE)
