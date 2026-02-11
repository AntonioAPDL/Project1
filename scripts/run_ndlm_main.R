#!/usr/bin/env Rscript

args <- commandArgs(trailingOnly = TRUE)
seed <- if (length(args) >= 1L) as.integer(args[[1L]]) else as.integer(Sys.getenv("DISC_BASE_SEED", "777"))
if (!is.finite(seed)) seed <- 777L

repo_root <- normalizePath(getwd(), mustWork = TRUE)
module_root <- file.path(repo_root, "R", "unified", "families", "ndlm_main")
module_files <- c(
  "00_constants.R",
  "01_inputs.R",
  "02_model_spec.R",
  "03_vb_updates.R",
  "04_elbo.R",
  "05_fitloop.R",
  "06_save_state.R",
  "zz_run.R"
)

missing <- module_files[!file.exists(file.path(module_root, module_files))]
if (length(missing) > 0L) {
  stop(sprintf("Missing NDLM theory module files: %s", paste(missing, collapse = ", ")), call. = FALSE)
}
for (f in module_files) {
  source(file.path(module_root, f), local = .GlobalEnv)
}

default_out <- file.path(repo_root, "DISC_variables_50_NDLM_synth_DISC.RData")
output_path <- Sys.getenv("UNIFIED_NDLM_RDATA_OUT", default_out)
output_path <- normalizePath(output_path, mustWork = FALSE)

summary_log <- Sys.getenv("NDLM_THEORY_SUMMARY_LOG", "")
if (!nzchar(summary_log)) {
  out_dir <- Sys.getenv("NDLM_OUT_DIR", "")
  if (nzchar(out_dir)) {
    summary_log <- file.path(out_dir, "ndlm_theory_summary.log")
  }
}

set.seed(seed)
RNGkind("Mersenne-Twister", "Inversion", "Rejection")
result <- unified_run_ndlm_main_theory(
  seed = seed,
  output_path = output_path,
  log_path = summary_log
)

cat(sprintf("ndlm_theory_complete output=%s\n", output_path))
cat(sprintf("sigma=%.8f w_hist=%.8f w_fore=%.8f\n", result$sigma, result$w_hist, result$w_fore))
