#!/usr/bin/env Rscript

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 1L) {
  stop("Usage: Rscript --vanilla scripts/run_exdqlm_univar.R <quantile> [seed]", call. = FALSE)
}

q <- as.numeric(args[[1L]])
if (!is.finite(q) || q <= 0 || q >= 1) {
  stop("quantile must be in (0,1)", call. = FALSE)
}

seed <- if (length(args) >= 2L) as.integer(args[[2L]]) else as.integer(Sys.getenv("DISC_BASE_SEED", "777"))
if (!is.finite(seed)) seed <- 777L

env_flag <- function(name, default = FALSE) {
  raw <- Sys.getenv(name, "")
  if (!nzchar(raw)) return(isTRUE(default))
  tolower(trimws(raw)) %in% c("1", "true", "yes", "y", "on")
}

env_choice <- function(name, choices, default) {
  raw <- tolower(trimws(Sys.getenv(name, "")))
  if (!nzchar(raw)) return(default)
  if (raw %in% choices) return(raw)
  default
}

env_nonneg_int <- function(name, default = 0L) {
  out <- suppressWarnings(as.integer(Sys.getenv(name, as.character(default))))
  if (!is.finite(out) || out < 0L) return(as.integer(default))
  as.integer(out)
}

env_num <- function(name, default) {
  out <- suppressWarnings(as.numeric(Sys.getenv(name, as.character(default))))
  if (!is.finite(out)) return(as.numeric(default))
  as.numeric(out)
}

env_pos_num <- function(name, default) {
  out <- suppressWarnings(as.numeric(Sys.getenv(name, as.character(default))))
  if (!is.finite(out) || out <= 0) return(as.numeric(default))
  as.numeric(out)
}

repo_root <- normalizePath(getwd(), mustWork = TRUE)
module_root <- file.path(repo_root, "R", "unified", "families", "exdqlm_univar")
module_files <- c(
  "00_constants.R",
  "01_inputs.R",
  "02_model_spec.R",
  "03_updates_vb_or_fitloop.R",
  "04_elbo_optional.R",
  "05_save_state.R",
  "zz_run.R"
)

missing <- module_files[!file.exists(file.path(module_root, module_files))]
if (length(missing) > 0L) {
  stop(sprintf("Missing univar theory module files: %s", paste(missing, collapse = ", ")), call. = FALSE)
}
for (f in module_files) {
  source(file.path(module_root, f), local = .GlobalEnv)
}

q_num <- as.integer(round(q * 100))
q_lab <- sprintf("%02d", q_num)
default_out <- file.path(repo_root, sprintf("variables_%s_exAL_synth_DISC_uni.RData", q_lab))
output_path <- Sys.getenv("UNIFIED_UNIV_RDATA_OUT", default_out)
output_path <- normalizePath(output_path, mustWork = FALSE)

summary_log <- Sys.getenv("UNIV_THEORY_SUMMARY_LOG", "")
if (!nzchar(summary_log)) {
  out_dir <- Sys.getenv("UNIV_OUT_DIR", "")
  if (nzchar(out_dir)) {
    summary_log <- file.path(out_dir, "univar_theory_summary.log")
  }
}

gamma_sigma_policy <- list(
  warmup_freeze_iters = env_nonneg_int("UNIV_GAMSIG_FREEZE_ITERS", 20L),
  freeze_target = env_choice("UNIV_GAMSIG_FREEZE_TARGET", choices = c("gamma_sigma", "states"), default = "gamma_sigma"),
  guard_refreeze_iters = env_nonneg_int("UNIV_GAMSIG_GUARD_REFREEZE_ITERS", 10L),
  init = list(
    mode = env_choice("UNIV_GAMSIG_INIT_MODE", choices = c("legacy", "robust"), default = "robust"),
    gamma = env_num("UNIV_GAMSIG_INIT_GAMMA", 0.0),
    sigma_floor = env_pos_num("UNIV_GAMSIG_INIT_SIGMA_FLOOR", 1e-3),
    sigma_scale = env_pos_num("UNIV_GAMSIG_INIT_SIGMA_SCALE", 1.0)
  ),
  objective_guard = list(
    enabled = env_flag("UNIV_GAMSIG_OBJECTIVE_GUARD_ENABLED", TRUE),
    fail_fast = env_flag("UNIV_GAMSIG_OBJECTIVE_GUARD_FAIL_FAST", FALSE),
    log_failures = env_flag("UNIV_GAMSIG_OBJECTIVE_GUARD_LOG_FAILURES", TRUE),
    mode = env_choice("UNIV_GAMSIG_OBJECTIVE_GUARD_MODE", choices = c("penalty", "adaptive_freeze"), default = "adaptive_freeze"),
    penalty = env_pos_num("UNIV_GAMSIG_OBJECTIVE_GUARD_PENALTY", 1e12)
  )
)

set.seed(seed)
RNGkind("Mersenne-Twister", "Inversion", "Rejection")
result <- unified_run_exdqlm_univar_theory(
  q = q,
  seed = seed,
  output_path = output_path,
  log_path = summary_log,
  gamma_sigma_policy = gamma_sigma_policy
)

cat(sprintf("univar_theory_complete quantile=%.2f output=%s\n", q, output_path))
if (!is.null(result$sigma) && !is.null(result$gamma)) {
  cat(sprintf("sigma=%.8f gamma=%.8f\n", result$sigma, result$gamma))
}
