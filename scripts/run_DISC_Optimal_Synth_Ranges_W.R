#!/usr/bin/env Rscript

message("DEPRECATED entrypoint for unified workflow orchestration. Prefer: scripts/unified_run.R")

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

preflight_path <- file.path("R", "unified", "preflight.R")
if (file.exists(preflight_path)) {
  source(preflight_path)
}

transfer_mode <- tolower(trimws(Sys.getenv("DISC_W_FORECAST_TRANSFER_MODE", "drop")))
if (!nzchar(transfer_mode)) transfer_mode <- "drop"
if (!(transfer_mode %in% c("drop", "keep"))) {
  warning(
    sprintf("unknown DISC_W_FORECAST_TRANSFER_MODE=%s; using drop", transfer_mode),
    call. = FALSE
  )
  transfer_mode <- "drop"
}

entrypoint <- if (identical(transfer_mode, "keep")) {
  "DISC_Optimal_Synth_Ranges_W_transfer_forecast.r"
} else {
  "DISC_Optimal_Synth_Ranges_W.r"
}
source(entrypoint, chdir = TRUE)

expected_rdata_path <- Sys.getenv("DISC_W_EXPECTED_RDATA_PATH", "")
if (nzchar(expected_rdata_path)) {
  output_info <- suppressWarnings(file.info(expected_rdata_path))
  output_size <- suppressWarnings(as.numeric(output_info$size[1L]))
  if (!file.exists(expected_rdata_path) || !is.finite(output_size) || output_size <= 0) {
    output_dir <- Sys.getenv("DISC_W_OUTPUT_DIR", "")
    candidates <- character()
    if (nzchar(output_dir) && dir.exists(output_dir)) {
      candidates <- list.files(
        output_dir,
        pattern = "^DISC_variables_.*\\.RData$",
        full.names = TRUE
      )
    }
    candidate_text <- if (length(candidates)) paste(candidates, collapse = " | ") else "<none>"
    stop(sprintf(
      "[DISC_W_EXPECTED_RDATA_MISSING] expected output not written: %s candidates=%s",
      expected_rdata_path,
      candidate_text
    ), call. = FALSE)
  }
  message(sprintf(
    "[DISC_W_EXPECTED_RDATA_OK] path=%s bytes=%d",
    expected_rdata_path,
    as.integer(output_size)
  ))
}
