#!/usr/bin/env Rscript

message("DEPRECATED entrypoint for unified workflow orchestration. Prefer: scripts/unified_run.R")

args <- commandArgs(trailingOnly = TRUE)
seed <- if (length(args) >= 1L) as.integer(args[[1L]]) else as.integer(Sys.getenv("NDLM_SEED", Sys.getenv("DISC_BASE_SEED", "777")))
if (!is.finite(seed)) stop("seed must be integer-like.", call. = FALSE)

# Determinism / stability baseline:
# - single-threaded math + OpenMP backends
# - stable RNG
Sys.setenv(
  OMP_NUM_THREADS = Sys.getenv("OMP_NUM_THREADS", "1"),
  OPENBLAS_NUM_THREADS = Sys.getenv("OPENBLAS_NUM_THREADS", "1"),
  MKL_NUM_THREADS = Sys.getenv("MKL_NUM_THREADS", "1"),
  VECLIB_MAXIMUM_THREADS = Sys.getenv("VECLIB_MAXIMUM_THREADS", "1"),
  NUMEXPR_NUM_THREADS = Sys.getenv("NUMEXPR_NUM_THREADS", "1"),
  DISC_BASE_SEED = as.character(seed),
  NDLM_BASE_SEED = as.character(seed)
)
options(mc.cores = 1)

set.seed(seed)
RNGkind("Mersenne-Twister", "Inversion", "Rejection")

# Keep the contract: call the existing entrypoint without editing it.
if (Sys.getenv("NDLM_RPROF", "") == "1") {
  dir.create("repro/perf", recursive = TRUE, showWarnings = FALSE)
  Rprof("repro/perf/Rprof_ndlm_legacy.out")
  on.exit(Rprof(NULL), add = TRUE)
}

preflight_path <- file.path("R", "unified", "preflight.R")
if (file.exists(preflight_path)) {
  source(preflight_path)
}
source("DISC_Optimal_Synth_Ranges_NDLM.r", chdir = TRUE)
