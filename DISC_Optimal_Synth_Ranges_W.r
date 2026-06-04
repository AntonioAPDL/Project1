#!/usr/bin/env Rscript
disc_libs_only <- identical(Sys.getenv("ENVIRONMETRICS_LIBS_ONLY", "0"), "1")
if (!disc_libs_only) {
  .libPaths(unique(c(.libPaths(), path.expand("~/R/libs"))))
}
print(.libPaths())

load_required_pkg <- function(pkg) {
  if (!require(pkg, character.only = TRUE, quietly = TRUE)) {
    stop(sprintf("Required package '%s' is not installed.", pkg), call. = FALSE)
  }
}

invisible(lapply(c(
  "dplyr", "parallel", "dlm", "exdqlm", "mvtnorm", "jmuOutlier", "sn",
  "Matrix", "future", "future.apply", "numDeriv", "foreach", "doParallel",
  "zoo", "expint", "nimble", "nloptr", "expm", "Rcpp", "RcppArmadillo",
  "RcppEigen", "ks", "MASS", "FNN", "lubridate"
), load_required_pkg))

DISC_DEBUG <- FALSE
source("R/disc_w/_init.R")
source("R/unified/families/exdqlm_multivar_structure.R")

n.samp <- 2000
cut <- 1
m <- 2
USE_PREV <- TRUE   
disc_use_prev_env <- Sys.getenv("DISC_USE_PREV", "")
if (nzchar(disc_use_prev_env)) {
  USE_PREV <- tolower(disc_use_prev_env) %in% c("1", "true", "yes", "y")
}

args <- commandArgs(trailingOnly = TRUE)
p0 <- as.numeric(args[1])
harmonics = c(1, 2, 1/6.8068493)   
# harmonics = c(363.5854/90, 363.5854/180, 1/6.8068493)     

Sys.setenv("PKG_CXXFLAGS"="-I/data/muscat_data/jaguir26/libs/eigen -I/data/muscat_data/jaguir26/libs/boost/include -DEIGEN_DONT_VECTORIZE")
Sys.setenv("PKG_LIBS"="-L/data/muscat_data/jaguir26/libs/lib64 -L/data/muscat_data/jaguir26/libs/boost/lib -llapack -lblas -lboost_random -lboost_system -fopenmp")
Sys.setenv(LD_LIBRARY_PATH="/data/muscat_data/jaguir26/libs/lib64:/data/muscat_data/jaguir26/libs/boost/lib:/lib64")

Rcpp::sourceCpp("/data/muscat_data/jaguir26/project1_ucsc_phd/sampling_exal.cpp")
Rcpp::sourceCpp("/data/muscat_data/jaguir26/project1_ucsc_phd/sampling_truncnorm.cpp")
Rcpp::sourceCpp("/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_kalman_synth.cpp")

disc_base_seed <- suppressWarnings(as.numeric(Sys.getenv("DISC_BASE_SEED", "777")))
if (!is.finite(disc_base_seed)) {
  disc_base_seed <- 777
}
if (exists("set_sampling_exal_seed", mode = "function")) {
  set_sampling_exal_seed(disc_base_seed)
}
if (exists("set_sampling_truncnorm_seed", mode = "function")) {
  set_sampling_truncnorm_seed(disc_base_seed)
}

disc_env_flag <- function(name, default = FALSE) {
  raw <- Sys.getenv(name, "")
  if (!nzchar(raw)) return(isTRUE(default))
  tolower(trimws(raw)) %in% c("1", "true", "yes", "y", "on")
}

disc_env_opt_flag <- function(name) {
  raw <- Sys.getenv(name, "")
  if (!nzchar(raw)) return(NA)
  tolower(trimws(raw)) %in% c("1", "true", "yes", "y", "on")
}

disc_env_choice <- function(name, choices, default) {
  raw <- tolower(trimws(Sys.getenv(name, "")))
  if (!nzchar(raw)) return(default)
  if (raw %in% choices) return(raw)
  default
}

disc_env_nonneg_int <- function(name, default = 0L) {
  out <- suppressWarnings(as.integer(Sys.getenv(name, as.character(default))))
  if (!is.finite(out) || out < 0L) return(as.integer(default))
  as.integer(out)
}

disc_env_opt_nonneg_int <- function(name) {
  raw <- Sys.getenv(name, "")
  if (!nzchar(raw)) return(NA_integer_)
  out <- suppressWarnings(as.integer(raw))
  if (!is.finite(out) || out < 0L) return(NA_integer_)
  as.integer(out)
}

disc_env_pos_num <- function(name, default) {
  out <- suppressWarnings(as.numeric(Sys.getenv(name, as.character(default))))
  if (!is.finite(out) || out <= 0) return(as.numeric(default))
  as.numeric(out)
}

disc_env_opt_pos_num <- function(name) {
  raw <- Sys.getenv(name, "")
  if (!nzchar(raw)) return(NA_real_)
  out <- suppressWarnings(as.numeric(raw))
  if (!is.finite(out) || out <= 0) return(NA_real_)
  as.numeric(out)
}

disc_env_num <- function(name, default) {
  out <- suppressWarnings(as.numeric(Sys.getenv(name, as.character(default))))
  if (!is.finite(out)) return(as.numeric(default))
  as.numeric(out)
}

disc_env_prob <- function(name, default) {
  out <- disc_env_num(name, default)
  if (!is.finite(out) || out <= 0 || out >= 1) return(as.numeric(default))
  as.numeric(out)
}

disc_env_opt_prob <- function(name) {
  out <- disc_env_opt_pos_num(name)
  if (!is.finite(out) || out >= 1) return(NA_real_)
  as.numeric(out)
}

DISC_GAMSIG_FREEZE_ITERS <- suppressWarnings(as.integer(Sys.getenv("DISC_GAMSIG_FREEZE_ITERS", "5")))
if (!is.finite(DISC_GAMSIG_FREEZE_ITERS) || DISC_GAMSIG_FREEZE_ITERS < 0L) {
  DISC_GAMSIG_FREEZE_ITERS <- 5L
}
DISC_GAMSIG_FREEZE_ITERS <- as.integer(DISC_GAMSIG_FREEZE_ITERS)
DISC_GAMSIG_MIN_UPDATE_ITERS <- disc_env_nonneg_int(
  "DISC_GAMSIG_MIN_UPDATE_ITERS",
  default = 50L
)
DISC_GAMSIG_MIN_TOTAL_ITERS <- disc_env_nonneg_int(
  "DISC_GAMSIG_MIN_TOTAL_ITERS",
  default = 50L
)
if (!is.finite(DISC_GAMSIG_MIN_TOTAL_ITERS) || DISC_GAMSIG_MIN_TOTAL_ITERS < 1L) {
  DISC_GAMSIG_MIN_TOTAL_ITERS <- 50L
}
DISC_GAMSIG_MAX_ITER <- disc_env_nonneg_int(
  "DISC_GAMSIG_MAX_ITER",
  default = 100L
)
if (!is.finite(DISC_GAMSIG_MAX_ITER) || DISC_GAMSIG_MAX_ITER < 1L) {
  DISC_GAMSIG_MAX_ITER <- 100L
}
DISC_GAMSIG_CONVERGENCE_TOL <- disc_env_pos_num(
  "DISC_GAMSIG_CONVERGENCE_TOL",
  default = 1e-6
)
DISC_GAMSIG_ELBO_TOL <- disc_env_pos_num(
  "DISC_GAMSIG_ELBO_TOL",
  default = DISC_GAMSIG_CONVERGENCE_TOL
)
DISC_GAMSIG_STATE_NORM_TOL <- disc_env_pos_num(
  "DISC_GAMSIG_STATE_NORM_TOL",
  default = 1e-6
)
DISC_GAMSIG_SIGMA_EXP_TOL <- disc_env_pos_num(
  "DISC_GAMSIG_SIGMA_EXP_TOL",
  default = 1e-6
)
DISC_GAMSIG_GAMMA_EXP_TOL <- disc_env_pos_num(
  "DISC_GAMSIG_GAMMA_EXP_TOL",
  default = 1e-6
)
DISC_GAMSIG_FREEZE_TARGET <- disc_env_choice(
  "DISC_GAMSIG_FREEZE_TARGET",
  choices = c("gamma_sigma", "states"),
  default = "gamma_sigma"
)
DISC_GAMSIG_GUARD_REFREEZE_ITERS <- disc_env_nonneg_int(
  "DISC_GAMSIG_GUARD_REFREEZE_ITERS",
  default = 10L
)
DISC_GAMSIG_INIT_MODE <- disc_env_choice(
  "DISC_GAMSIG_INIT_MODE",
  choices = c("legacy", "robust"),
  default = "robust"
)
DISC_GAMSIG_INIT_GAMMA <- disc_env_num("DISC_GAMSIG_INIT_GAMMA", 0.0)
DISC_GAMSIG_INIT_SIGMA_FLOOR <- disc_env_pos_num("DISC_GAMSIG_INIT_SIGMA_FLOOR", 1e-3)
DISC_GAMSIG_INIT_SIGMA_SCALE <- disc_env_pos_num("DISC_GAMSIG_INIT_SIGMA_SCALE", 1.0)
DISC_GAMSIG_OBJECTIVE_GUARD_ENABLED <- disc_env_flag(
  "DISC_GAMSIG_OBJECTIVE_GUARD_ENABLED",
  default = TRUE
)
DISC_GAMSIG_OBJECTIVE_GUARD_FAIL_FAST <- disc_env_flag(
  "DISC_GAMSIG_OBJECTIVE_GUARD_FAIL_FAST",
  default = FALSE
)
DISC_GAMSIG_OBJECTIVE_GUARD_LOG_FAILURES <- disc_env_flag(
  "DISC_GAMSIG_OBJECTIVE_GUARD_LOG_FAILURES",
  default = TRUE
)
DISC_GAMSIG_OBJECTIVE_GUARD_MODE <- disc_env_choice(
  "DISC_GAMSIG_OBJECTIVE_GUARD_MODE",
  choices = c("penalty", "adaptive_freeze"),
  default = "adaptive_freeze"
)
DISC_GAMSIG_OBJECTIVE_GUARD_PENALTY <- disc_env_pos_num(
  "DISC_GAMSIG_OBJECTIVE_GUARD_PENALTY",
  default = 1e12
)
DISC_GAMSIG_THETA_SIGMA_LOWER <- disc_env_num(
  "DISC_GAMSIG_THETA_SIGMA_LOWER",
  default = log(1e-4)
)
DISC_GAMSIG_THETA_SIGMA_UPPER <- disc_env_num(
  "DISC_GAMSIG_THETA_SIGMA_UPPER",
  default = log(1e3)
)
if (!is.finite(DISC_GAMSIG_THETA_SIGMA_LOWER) ||
    !is.finite(DISC_GAMSIG_THETA_SIGMA_UPPER) ||
    DISC_GAMSIG_THETA_SIGMA_LOWER >= DISC_GAMSIG_THETA_SIGMA_UPPER) {
  DISC_GAMSIG_THETA_SIGMA_LOWER <- log(1e-4)
  DISC_GAMSIG_THETA_SIGMA_UPPER <- log(1e3)
}
DISC_GAMSIG_THETA_GAMMA_LOWER <- disc_env_num(
  "DISC_GAMSIG_THETA_GAMMA_LOWER",
  default = qlogis(1e-6)
)
DISC_GAMSIG_THETA_GAMMA_UPPER <- disc_env_num(
  "DISC_GAMSIG_THETA_GAMMA_UPPER",
  default = qlogis(1 - 1e-6)
)
if (!is.finite(DISC_GAMSIG_THETA_GAMMA_LOWER) ||
    !is.finite(DISC_GAMSIG_THETA_GAMMA_UPPER) ||
    DISC_GAMSIG_THETA_GAMMA_LOWER >= DISC_GAMSIG_THETA_GAMMA_UPPER) {
  DISC_GAMSIG_THETA_GAMMA_LOWER <- qlogis(1e-6)
  DISC_GAMSIG_THETA_GAMMA_UPPER <- qlogis(1 - 1e-6)
}
DISC_GAMSIG_HESSIAN_RIDGE_INIT <- disc_env_pos_num(
  "DISC_GAMSIG_HESSIAN_RIDGE_INIT",
  default = 1e-6
)
DISC_GAMSIG_HESSIAN_RIDGE_MULTIPLIER <- disc_env_pos_num(
  "DISC_GAMSIG_HESSIAN_RIDGE_MULTIPLIER",
  default = 10
)
DISC_GAMSIG_HESSIAN_RIDGE_MAX_TRIES <- disc_env_nonneg_int(
  "DISC_GAMSIG_HESSIAN_RIDGE_MAX_TRIES",
  default = 8L
)
DISC_GAMSIG_MEDIAN_SIGMA_ONLY_FALLBACK_ENABLED <- disc_env_flag(
  "DISC_GAMSIG_MEDIAN_SIGMA_ONLY_FALLBACK_ENABLED",
  default = TRUE
)
DISC_GAMSIG_MEDIAN_SIGMA_ONLY_FALLBACK_TOL <- disc_env_pos_num(
  "DISC_GAMSIG_MEDIAN_SIGMA_ONLY_FALLBACK_TOL",
  default = 1e-8
)
DISC_GAMSIG_MEDIAN_STEP_DAMPING_ENABLED <- disc_env_flag(
  "DISC_GAMSIG_MEDIAN_STEP_DAMPING_ENABLED",
  default = TRUE
)
DISC_GAMSIG_MEDIAN_MAX_ABS_GAMMA_STEP <- disc_env_pos_num(
  "DISC_GAMSIG_MEDIAN_MAX_ABS_GAMMA_STEP",
  default = 0.25
)
DISC_GAMSIG_MEDIAN_MAX_ABS_LOG_SIGMA_STEP <- disc_env_pos_num(
  "DISC_GAMSIG_MEDIAN_MAX_ABS_LOG_SIGMA_STEP",
  default = 0.5
)
DISC_GAMSIG_MEDIAN_STATE_GUARD_ENABLED <- disc_env_flag(
  "DISC_GAMSIG_MEDIAN_STATE_GUARD_ENABLED",
  default = TRUE
)
DISC_GAMSIG_MEDIAN_STATE_NORM_MAX_RATIO <- disc_env_pos_num(
  "DISC_GAMSIG_MEDIAN_STATE_NORM_MAX_RATIO",
  default = 25
)
DISC_GAMSIG_MEDIAN_STATE_NORM_ABS_CAP <- disc_env_pos_num(
  "DISC_GAMSIG_MEDIAN_STATE_NORM_ABS_CAP",
  default = 1e8
)
DISC_GAMSIG_MEDIAN_STATE_GUARD_REFREEZE_ITERS <- disc_env_nonneg_int(
  "DISC_GAMSIG_MEDIAN_STATE_GUARD_REFREEZE_ITERS",
  default = DISC_GAMSIG_GUARD_REFREEZE_ITERS
)
DISC_GAMSIG_MEDIAN_STATE_HOLD_AFTER_GUARD_ITERS <- disc_env_nonneg_int(
  "DISC_GAMSIG_MEDIAN_STATE_HOLD_AFTER_GUARD_ITERS",
  default = 0L
)
DISC_GAMSIG_MEDIAN_STATE_BLEND_ALPHA <- disc_env_prob(
  "DISC_GAMSIG_MEDIAN_STATE_BLEND_ALPHA",
  default = 1.0
)
DISC_GAMSIG_MEDIAN_COV_BLEND_ALPHA <- disc_env_prob(
  "DISC_GAMSIG_MEDIAN_COV_BLEND_ALPHA",
  default = 1.0
)
DISC_GAMSIG_STATE_GUARD_ENABLED_OPT <- disc_env_opt_flag(
  "DISC_GAMSIG_STATE_GUARD_ENABLED"
)
DISC_GAMSIG_STATE_NORM_MAX_RATIO_OPT <- disc_env_opt_pos_num(
  "DISC_GAMSIG_STATE_NORM_MAX_RATIO"
)
DISC_GAMSIG_STATE_NORM_ABS_CAP_OPT <- disc_env_opt_pos_num(
  "DISC_GAMSIG_STATE_NORM_ABS_CAP"
)
DISC_GAMSIG_STATE_GUARD_REFREEZE_ITERS_OPT <- disc_env_opt_nonneg_int(
  "DISC_GAMSIG_STATE_GUARD_REFREEZE_ITERS"
)
DISC_GAMSIG_STATE_HOLD_AFTER_GUARD_ITERS_OPT <- disc_env_opt_nonneg_int(
  "DISC_GAMSIG_STATE_HOLD_AFTER_GUARD_ITERS"
)
DISC_GAMSIG_STATE_BLEND_ALPHA_OPT <- disc_env_opt_prob(
  "DISC_GAMSIG_STATE_BLEND_ALPHA"
)
DISC_GAMSIG_COV_BLEND_ALPHA_OPT <- disc_env_opt_prob(
  "DISC_GAMSIG_COV_BLEND_ALPHA"
)
DISC_STRICT_CONTRACTS <- disc_env_flag(
  "DISC_STRICT_CONTRACTS",
  default = TRUE
)

disc_blend_numeric_like <- function(current, candidate, alpha, label = "value") {
  disc_dim_string <- function(x) {
    dims <- dim(x)
    if (is.null(dims)) {
      return(sprintf("len=%d", length(x)))
    }
    paste(dims, collapse = "x")
  }
  if (!is.finite(alpha) || alpha >= 1) {
    return(candidate)
  }
  if (alpha <= 0) {
    return(current)
  }
  current_arr <- as.array(current)
  candidate_arr <- as.array(candidate)
  if (!identical(dim(current_arr), dim(candidate_arr))) {
    stop(
      sprintf(
        "blend dim mismatch for %s current=%s candidate=%s",
        label,
        disc_dim_string(current),
        disc_dim_string(candidate)
      ),
      call. = FALSE
    )
  }
  blended <- alpha * candidate_arr + (1 - alpha) * current_arr
  if (is.null(dim(candidate))) {
    return(as.numeric(blended))
  }
  dim(blended) <- dim(candidate)
  dimnames(blended) <- dimnames(candidate)
  blended
}

disc_blend_numeric_list <- function(current_list, candidate_list, alpha, label_prefix = "list") {
  if (!is.list(current_list) || !is.list(candidate_list)) {
    stop(sprintf("blend list mismatch for %s", label_prefix), call. = FALSE)
  }
  if (length(current_list) != length(candidate_list)) {
    stop(sprintf("blend list length mismatch for %s", label_prefix), call. = FALSE)
  }
  Map(
    function(cur_item, cand_item, idx) {
      disc_blend_numeric_like(
        cur_item,
        cand_item,
        alpha,
        sprintf("%s[[%d]]", label_prefix, as.integer(idx))
      )
    },
    current_list,
    candidate_list,
    seq_along(candidate_list)
  )
}

disc_theta_cpp_horizon_count <- function(total_len, state_rows, label) {
  horizon_count <- total_len / state_rows
  if (!is.finite(horizon_count) || abs(horizon_count - round(horizon_count)) > 1e-8) {
    stop(
      sprintf(
        "theta payload horizon mismatch for %s total_len=%d state_rows=%d ratio=%0.6f",
        label,
        as.integer(total_len),
        as.integer(state_rows),
        as.numeric(horizon_count)
      ),
      call. = FALSE
    )
  }
  as.integer(round(horizon_count))
}

disc_materialize_theta_cpp_payload <- function(
  theta_cpp,
  J,
  p,
  ppx,
  num_mem,
  context_label = "theta_cpp"
) {
  materialized <- list(
    sm = theta_cpp$sm,
    sC = theta_cpp$sC,
    fm = theta_cpp$fm,
    fC = theta_cpp$fC,
    sm_ens = vector("list", J),
    sC_ens = vector("list", J),
    fm_ens = vector("list", J),
    fC_ens = vector("list", J),
    standard_forecast_errors = theta_cpp$standard_forecast_errors,
    standard_forecast_errors_ens = vector("list", J),
    elbo.part = theta_cpp$elbo.part,
    elbo.part_ens = theta_cpp$elbo.part_ens,
    W_T = theta_cpp$W_T
  )

  for (j in seq_len(J)) {
    state_rows <- p * (J + 1) - p * (j - 1)
    r_j <- disc_theta_cpp_horizon_count(
      length(theta_cpp$sm_ens[[j]]),
      state_rows,
      sprintf("%s sm_ens[[%d]]", context_label, as.integer(j))
    )
    materialized$fm_ens[[j]] <- matrix(theta_cpp$fm_ens[[j]], nrow = state_rows)
    materialized$sm_ens[[j]] <- matrix(theta_cpp$sm_ens[[j]], nrow = state_rows)
    materialized$fC_ens[[j]] <- array(theta_cpp$fC_ens[[j]], c(state_rows, state_rows, r_j))
    materialized$sC_ens[[j]] <- array(theta_cpp$sC_ens[[j]], c(state_rows, state_rows, r_j))
    materialized$standard_forecast_errors_ens[[j]] <- matrix(
      theta_cpp$standard_forecast_errors_ens[[j]],
      nrow = cumsum(num_mem)[J - j + 1]
    )
  }

  materialized
}

DISC_W_N_SAMP <- disc_env_nonneg_int(
  "DISC_W_N_SAMP",
  default = 2000L
)
if (!is.finite(DISC_W_N_SAMP) || DISC_W_N_SAMP < 1L) {
  DISC_W_N_SAMP <- 2000L
}
n.samp <- as.integer(DISC_W_N_SAMP)
DISC_W_SAMPLING_HEARTBEAT_ENABLED <- disc_env_flag(
  "DISC_W_SAMPLING_HEARTBEAT_ENABLED",
  default = FALSE
)
DISC_W_SAMPLING_HEARTBEAT_SECONDS <- disc_env_nonneg_int(
  "DISC_W_SAMPLING_HEARTBEAT_SECONDS",
  default = 60L
)
if (!is.finite(DISC_W_SAMPLING_HEARTBEAT_SECONDS) || DISC_W_SAMPLING_HEARTBEAT_SECONDS < 1L) {
  DISC_W_SAMPLING_HEARTBEAT_SECONDS <- 60L
}
DISC_W_SAMPLING_PHASE_MARKERS_ENABLED <- disc_env_flag(
  "DISC_W_SAMPLING_PHASE_MARKERS_ENABLED",
  default = FALSE
)
DISC_W_SAMPLING_WALLTIME_SECONDS <- disc_env_nonneg_int(
  "DISC_W_SAMPLING_WALLTIME_SECONDS",
  default = 0L
)
DISC_W_SAMPLING_MEMBER_WALLTIME_SECONDS <- disc_env_nonneg_int(
  "DISC_W_SAMPLING_MEMBER_WALLTIME_SECONDS",
  default = 0L
)
DISC_W_SAMPLING_DIAG_PATH <- trimws(Sys.getenv("DISC_W_SAMPLING_DIAG_PATH", ""))
DISC_W_SAMPLING_DIAG_STDERR_ENABLED <- disc_env_flag(
  "DISC_W_SAMPLING_DIAG_STDERR_ENABLED",
  default = FALSE
)

DISC_GAMSIG_TERMINAL_SAMPLING_GUARD_MODE <- disc_env_choice(
  "DISC_GAMSIG_TERMINAL_SAMPLING_GUARD_MODE",
  choices = c("off", "fail_fast"),
  default = "off"
)
DISC_GAMSIG_TERMINAL_SAMPLING_GUARD_MIN_GUARD_COUNT <- disc_env_nonneg_int(
  "DISC_GAMSIG_TERMINAL_SAMPLING_GUARD_MIN_GUARD_COUNT",
  default = 1L
)
if (!is.finite(DISC_GAMSIG_TERMINAL_SAMPLING_GUARD_MIN_GUARD_COUNT) ||
    DISC_GAMSIG_TERMINAL_SAMPLING_GUARD_MIN_GUARD_COUNT < 1L) {
  DISC_GAMSIG_TERMINAL_SAMPLING_GUARD_MIN_GUARD_COUNT <- 1L
}
DISC_GAMSIG_TERMINAL_SAMPLING_GUARD_MAX_GUARD_LAG_ITERS <- disc_env_nonneg_int(
  "DISC_GAMSIG_TERMINAL_SAMPLING_GUARD_MAX_GUARD_LAG_ITERS",
  default = 0L
)
DISC_GAMSIG_TERMINAL_SAMPLING_GUARD_REQUIRE_FROZEN <- disc_env_flag(
  "DISC_GAMSIG_TERMINAL_SAMPLING_GUARD_REQUIRE_FROZEN",
  default = TRUE
)

disc_sampling_diag_started_at <- NULL
disc_sampling_diag_last_heartbeat <- 0
disc_sampling_diag_phase <- "idle"

disc_sampling_diag_elapsed_seconds <- function() {
  if (is.null(disc_sampling_diag_started_at)) {
    return(0)
  }
  as.numeric(difftime(Sys.time(), disc_sampling_diag_started_at, units = "secs"))
}

disc_sampling_diag_emit <- function(kind, phase, detail = "") {
  detail_text <- if (!nzchar(detail)) "-" else detail
  line <- sprintf(
    "[%s] p0=%s phase=%s elapsed=%0.3fs detail=%s\n",
    kind,
    as.character(p0),
    as.character(phase),
    disc_sampling_diag_elapsed_seconds(),
    detail_text
  )
  delivered <- FALSE
  if (nzchar(DISC_W_SAMPLING_DIAG_PATH)) {
    cat(line, file = DISC_W_SAMPLING_DIAG_PATH, append = TRUE)
    delivered <- TRUE
  }
  if (isTRUE(DISC_W_SAMPLING_DIAG_STDERR_ENABLED)) {
    cat(line, file = stderr())
    try(flush(stderr()), silent = TRUE)
    delivered <- TRUE
  }
  if (!delivered) {
    cat(line)
    flush.console()
  }
}

disc_sampling_diag_check <- function(phase = NULL, detail = "", force_heartbeat = FALSE) {
  if (is.null(disc_sampling_diag_started_at)) {
    return(invisible(NULL))
  }
  if (!is.null(phase) && nzchar(as.character(phase))) {
    disc_sampling_diag_phase <<- as.character(phase)
  }
  elapsed <- disc_sampling_diag_elapsed_seconds()
  if (is.finite(DISC_W_SAMPLING_WALLTIME_SECONDS) &&
      DISC_W_SAMPLING_WALLTIME_SECONDS > 0L &&
      elapsed > as.numeric(DISC_W_SAMPLING_WALLTIME_SECONDS)) {
    msg <- sprintf(
      "sampling walltime exceeded for p0=%s phase=%s elapsed=%0.3fs limit=%ds detail=%s",
      as.character(p0),
      as.character(disc_sampling_diag_phase),
      elapsed,
      as.integer(DISC_W_SAMPLING_WALLTIME_SECONDS),
      if (!nzchar(detail)) "-" else detail
    )
    disc_sampling_diag_emit("sampling_walltime", disc_sampling_diag_phase, detail)
    stop(msg, call. = FALSE)
  }
  if (isTRUE(DISC_W_SAMPLING_HEARTBEAT_ENABLED)) {
    should_emit <- isTRUE(force_heartbeat) ||
      (elapsed - disc_sampling_diag_last_heartbeat) >= as.numeric(DISC_W_SAMPLING_HEARTBEAT_SECONDS)
    if (should_emit) {
      disc_sampling_diag_emit("sampling_heartbeat", disc_sampling_diag_phase, detail)
      disc_sampling_diag_last_heartbeat <<- elapsed
    }
  }
  invisible(NULL)
}

disc_sampling_diag_mark <- function(phase, detail = "") {
  disc_sampling_diag_phase <<- as.character(phase)
  if (isTRUE(DISC_W_SAMPLING_PHASE_MARKERS_ENABLED)) {
    disc_sampling_diag_emit("sampling_phase", disc_sampling_diag_phase, detail)
  }
  disc_sampling_diag_check(phase = disc_sampling_diag_phase, detail = detail, force_heartbeat = TRUE)
}

disc_sampling_diag_start <- function(phase = "sampling_start", detail = "") {
  disc_sampling_diag_started_at <<- Sys.time()
  disc_sampling_diag_last_heartbeat <<- 0
  disc_sampling_diag_phase <<- as.character(phase)
  disc_sampling_diag_mark(phase, detail)
}

disc_sampling_diag_dim_summary <- function(x) {
  dims <- dim(x)
  if (is.null(dims)) {
    return(sprintf("len=%d", length(x)))
  }
  sprintf("dim=%s", paste(as.integer(dims), collapse = "x"))
}

disc_sampling_diag_numeric_summary <- function(name, x) {
  vec <- suppressWarnings(as.numeric(x))
  finite <- is.finite(vec)
  finite_n <- sum(finite)
  min_text <- if (finite_n > 0L) format(signif(min(vec[finite]), 6), scientific = TRUE, trim = TRUE) else "NA"
  max_text <- if (finite_n > 0L) format(signif(max(vec[finite]), 6), scientific = TRUE, trim = TRUE) else "NA"
  sprintf(
    "%s[%s finite=%d/%d min=%s max=%s]",
    name,
    disc_sampling_diag_dim_summary(x),
    as.integer(finite_n),
    as.integer(length(vec)),
    min_text,
    max_text
  )
}

disc_sampling_diag_require_numeric <- function(name, x, phase, detail = "", require_positive = FALSE, require_nonnegative = FALSE) {
  vec <- suppressWarnings(as.numeric(x))
  summary_text <- disc_sampling_diag_numeric_summary(name, x)
  if (!length(vec)) {
    msg <- sprintf("invalid sampler input for p0=%s phase=%s %s reason=empty %s", as.character(p0), as.character(phase), summary_text, detail)
    disc_sampling_diag_emit("sampling_invalid_input", phase, msg)
    stop(msg, call. = FALSE)
  }
  if (any(!is.finite(vec))) {
    msg <- sprintf("invalid sampler input for p0=%s phase=%s %s reason=non_finite %s", as.character(p0), as.character(phase), summary_text, detail)
    disc_sampling_diag_emit("sampling_invalid_input", phase, msg)
    stop(msg, call. = FALSE)
  }
  if (isTRUE(require_positive) && any(vec <= 0)) {
    msg <- sprintf("invalid sampler input for p0=%s phase=%s %s reason=non_positive %s", as.character(p0), as.character(phase), summary_text, detail)
    disc_sampling_diag_emit("sampling_invalid_input", phase, msg)
    stop(msg, call. = FALSE)
  }
  if (!isTRUE(require_positive) && isTRUE(require_nonnegative) && any(vec < 0)) {
    msg <- sprintf("invalid sampler input for p0=%s phase=%s %s reason=negative %s", as.character(p0), as.character(phase), summary_text, detail)
    disc_sampling_diag_emit("sampling_invalid_input", phase, msg)
    stop(msg, call. = FALSE)
  }
  invisible(summary_text)
}

disc_sampling_diag_guarded_eval <- function(phase, detail = "", timeout_seconds = 0L, code) {
  if (is.finite(timeout_seconds) && timeout_seconds > 0L) {
    setTimeLimit(cpu = Inf, elapsed = as.numeric(timeout_seconds), transient = TRUE)
    on.exit(setTimeLimit(cpu = Inf, elapsed = Inf, transient = TRUE), add = TRUE)
  }
  tryCatch(
    force(code),
    error = function(e) {
      msg <- sprintf(
        "sampling failure for p0=%s phase=%s detail=%s error=%s",
        as.character(p0),
        as.character(phase),
        if (!nzchar(detail)) "-" else detail,
        conditionMessage(e)
      )
      disc_sampling_diag_emit("sampling_error", phase, msg)
      stop(msg, call. = FALSE)
    }
  )
}

DISC_W_DF_T <- disc_env_prob("DISC_W_DF_T", 0.9999995)
DISC_W_DF_S1 <- disc_env_prob("DISC_W_DF_S1", 0.9997)
DISC_W_DF_S2 <- disc_env_prob("DISC_W_DF_S2", 0.9997)
DISC_W_DF_S67 <- disc_env_prob("DISC_W_DF_S67", 0.9997)
DISC_W_DF_DISCREP <- disc_env_prob("DISC_W_DF_DISCREP", 0.999)
DISC_W_LAMBDA <- disc_env_prob("DISC_W_LAMBDA", 0.8995)
DISC_W_DF_TRANS <- disc_env_prob("DISC_W_DF_TRANS", 0.99999999)
DISC_W_DF_COVS <- disc_env_prob("DISC_W_DF_COVS", 0.99999)
DISC_W_INITIAL_DELTA <- c(
  DISC_W_DF_T,
  DISC_W_DF_S1,
  DISC_W_DF_S2,
  DISC_W_DF_S67,
  DISC_W_DF_DISCREP,
  DISC_W_LAMBDA
)
DISC_W_LAM1 <- disc_env_prob("DISC_W_LAM1", 1 - 1e-6)
DISC_W_LAM2 <- disc_env_prob("DISC_W_LAM2", 1 - 1e-6)
DISC_W_SIMS_ENABLED <- disc_env_flag("DISC_W_SIMS_ENABLED", default = TRUE)
DISC_W_USE_COVARIATES <- disc_env_flag("DISC_W_USE_COVARIATES", default = TRUE)
DISC_W_LIKELIHOOD_MODE <- disc_env_choice("DISC_W_LIKELIHOOD_MODE", choices = c("exal", "al"), default = "exal")
DISC_W_AL_MODE <- identical(DISC_W_LIKELIHOOD_MODE, "al")
DISC_W_C_FACTOR <- disc_env_pos_num("DISC_W_C_FACTOR", 1e2)
DISC_W_FORECAST_COV_EPSILON <- disc_env_pos_num("DISC_W_FORECAST_COV_EPSILON", NA_real_)

print(c(n.samp, 444))
flush.console()


objective_deltas <- function(delta, SIMS, use_covariates){


print(c(n.samp, 444))
flush.console()

lam1 <- DISC_W_LAM1 # Sudden correction at start of forecast period
lam2 <- DISC_W_LAM2 # Correction during forecast period from historical period

df_t        <- delta[1]
df_s1       <- delta[2]
df_s2       <- delta[3]
df_s67      <- delta[4]
df.discrep  <- delta[5]
df_trans      <- DISC_W_DF_TRANS
df_covs       <- DISC_W_DF_COVS
lambda      <- delta[6]

# Function to check if a matrix is positive definite
is.positive.definite <- function(x) {
  eigenvalues <- eigen(x)$values
  return(all(eigenvalues > 0))
}

# Function to compute inverse or square root of inverse using Cholesky Decomposition
compute_cholesky <- function(q, compute_sqrt_inverse = FALSE) {
  if (!is.positive.definite(q)) {
    stop("The matrix is not positive definite.")
  }
  
  # Compute Cholesky decomposition
  chol_decomp <- chol(as.matrix(q))
  
  # Convert to Matrix class to use with chol2inv
  U <- Matrix(chol_decomp, sparse = TRUE)
  
  # Compute inverse using Cholesky decomposition
  inv_q <- chol2inv(U)
  
  if (!compute_sqrt_inverse) {
    return(list(inverse = inv_q))
  } else {
    # Compute square root of the inverse
    # The square root of the inverse in this context is the inverse of the upper triangular matrix U
    sqrt_inv_q <- solve(U)
    
    # Check if the square root of the inverse times itself results in the inverse
    sqrt_inv_q_product <- sqrt_inv_q %*% t(sqrt_inv_q)
    is_correct <- all.equal(sqrt_inv_q_product, inv_q, tolerance = 1e-12)
    
    return(list(inverse = inv_q, sqrt_inverse = sqrt_inv_q, check = is_correct))
  }
}
#
log.g<-function(gam){	log(2)+stats::pnorm(-abs(gam),log=T)+0.5*gam^2 }
L.fn<-function(p0){ stats::uniroot(function(gam) exp(log.g(gam))-(1-p0), c(-1000,0))$root }
U.fn<-function(p0){ stats::uniroot(function(gam) exp(log.g(gam))-p0, c(0,1000))$root }
p.fn<-function(p0,gam){ (p0-as.numeric(gam<0))/exp(log.g(gam))+as.numeric(gam<0)}
A.fn<-function(p0,gam){ temp.p = p.fn(p0,gam); return((1-2*temp.p)/(temp.p*(1-temp.p))) }
B.fn<-function(p0,gam){ temp.p = p.fn(p0,gam); return((2)/(temp.p*(1-temp.p))) }
C.fn<-function(p0,gam){ temp.p = p.fn(p0,gam); return((as.numeric(gam>0)-temp.p)^(-1)) }
#
CheckLossFn = function(p0,diff){diff*p0 - diff*as.numeric(diff<0)}
#
dlm_df = function(y, model, df, dim.df, s.priors = list(l0=1,S0=10), just.lik=FALSE){
  ### Gets the Time Series Length / Replicate number
  y = check_ts(y)
  TT = nrow(y)
  ### Gets the State Parameter dimension and Prior Distribution Parameters
  m0 = model$m0
  C0 = model$C0
  l0 = s.priors$l0
  S0 = s.priors$S0
  n = length(m0)
  ### Constructs F and G
  FF = model$FF
  GG = model$GG
  ### Variable Saving
  ### Posterior Distribution
  m = matrix(0,TT,n)
  C = array(0,c(TT,n,n))
  ### Predictive State Distribution
  a = matrix(0,TT,n)
  R = array(0,dim = c(TT,n,n))
  P = array(0,dim = c(TT,n,n))
  W = array(0,dim = c(TT,n,n))
  ### One-Step Ahead Forecast
  f = matrix(0,TT,1)
  Q = array(0,c(TT,1,1))
  inv.Q = array(0,c(TT,1,1))
  ### Regression Variables
  e = matrix(0,TT,1)
  A = array(0,c(TT,n,1))
  ### Sample Variance
  S = vector("numeric",TT)
  l = vector("numeric",TT)

  # Prior Dim Check
  m0 = matrix(m0,n,1)
  C0 = matrix(C0,n,n)
  ### Discount Factor Blocking
  df.mat = make_df_mat(df,dim.df,n)

  ### First Update
  ### One-step state forecast
  a[1,]  = GG[,,1] %*% m0
  P[1,,] = GG[,,1] %*% C0 %*% t(GG[,,1])
  W[1,,] = df.mat * P[1,,]
  R[1,,] = P[1,,] + W[1,,]
  ### One-step ahead forecast
  f[1,] = t(FF[,1]) %*% a[1,]
  Q[1,,] = as.matrix(1 + t(FF[,1]) %*% R[1,,] %*% FF[,1],1,1)
  inv.Q[1,,] = chol2inv(chol(Q[1,,]))
  ### Auxilary Variables
  e[1,]  = as.matrix(y[1,] - f[1,],1,1)
  A[1,,] = R[1,,] %*% FF[,1] %*% inv.Q[1,,]
  ### Variance update
  l[1] = l0 + 1
  S[1] = l0 * S0 / l[1] + (t(e[1,]) %*% inv.Q[1,,] %*% e[1,] / l[1])
  ### Posterior Distribution
  m[1,]  = a[1,] + as.matrix(A[1,,],n,1) %*% e[1,]
  C[1,,] = R[1,,] - as.matrix(A[1,,],n,1) %*% Q[1,,] %*% t(A[1,,])
  C[1,,] = (C[1,,] + t(C[1,,]))/2

  for(i in 2:TT){
    ### One-step state forecast
    a[i,]  = GG[,,i] %*% m[i-1,]
    P[i,,] = GG[,,i] %*% C[i-1,,] %*% t(GG[,,i])
    W[i,,] = df.mat * P[i,,]
    R[i,,] = P[i,,] + W[i,,]
    ### One-step ahead forecast
    f[i,] = t(FF[,i]) %*% a[i,]
    Q[i,,] = matrix(1 + t(FF[,i])%*% R[i,,]%*% FF[,i],1,1)
    inv.Q[i,,] = chol2inv(chol(Q[i,,]))
    ### Auxilary Variables
    e[i,]  = as.matrix(y[i,] - f[i,],1,1)
    A[i,,] = as.matrix(R[i,,] %*% FF[,i] %*% inv.Q[i,,],n,1)
    ### Variance update
    l[i] = l[i-1] + 1
    S[i] = l[i-1] * S[i-1] / l[i] + (t(e[i,]) %*% inv.Q[i,,] %*% e[i,] / l[i])
    ### Posterior Distribution
    m[i,]  = a[i,] + as.matrix(A[i,,],n,1) %*% e[i,]
    C[i,,] = R[i,,] - as.matrix(A[i,,],n,1) %*% Q[i,,] %*% t(as.matrix(A[i,,],n,1))
    C[i,,] = (C[i,,] + t(C[i,,]))/2
  }

  ### Adjust By Variance
  R[1,,] = S0 * R[1,,]
  Q[1,,]   = S0 * Q[1,,]
  C[1,,]   = S[1] * C[1,,]
  for(i in 2:TT){
    R[i,,] = S[i-1] * R[i,,]
    Q[i,,]   = S[i-1] * Q[i,,]
    C[i,,]   = S[i] * C[i,,]
  }

  # Calculate Log-Likelihood
  det.Q = log(abs(Q[1,,])) ; llik = lgamma((l0+1)/2)-lgamma(l0/2)-log(pi*l0)/2-det.Q/2-(l0+1)*log(1+t(e[1,])%*%inv.Q[1,,]%*%e[1,]/l0)/2
  for(t in 2:TT){
    det.Q = log(abs(Q[t,,]))
    llik = llik + lgamma((l[t-1]+1)/2)-lgamma(l[t-1]/2)-log(pi*l[t-1])/2-det.Q/2-(l[t-1]+1)*log(1+t(e[t,])%*%inv.Q[t,,]%*%e[t,]/l[t-1])/2
  }
  if(just.lik){
    return(list(llik = llik))
  }

  ## SMOOTHING
  ### Initializes recursive relations
  sa = matrix(0,TT,n)
  sR = array(0, dim = c(TT,n,n))
  ### Runs the recursive equations
  sa[TT,]  = m[TT,]
  sR[TT,,] = C[TT,,]
  for(k in 1:(TT-1)){
  ### Computes the Auxilary recursion Variable B
    B = C[TT-k,,] %*% t(GG[,,TT-k+1]) %*% solve(R[TT-k+1,,])
    sa[TT-k,] = m[TT-k,] + B %*% (sa[TT-k+1,] - a[TT-k+1,])
    sR[TT-k,,] = C[TT-k,,] + B %*% (sR[TT-k+1,,] - R[TT-k+1,,]) %*% t(B)
  }
  ### Adjusts the variance update
  for(k in 1:TT){
    sR[TT-k,,] = S[TT] * sR[TT-k,,] / S[TT-k]
  }
  return(list(fm = m, fC = C, m = sa, C = sR,model = model, s = S, n = l))
}
#
make_df_mat = function(df,dim.df,n){
  if(sum(dim.df)!=n){ stop("sum of component dimensions given in dim.df does not match m0") }
  if(length(df)!=length(dim.df)){ stop("length of component discount factors does not match length of component dimensions") }
  n.dfs = length(dim.df)
  ind.dfs = c(0,sapply(1:length(dim.df),function(x){sum(dim.df[1:x])}),n)
  df.mat = matrix(0,n,n)
  for(j in 1:n.dfs){
    if (dim.df[j] <= 0L) next
    idx <- (ind.dfs[j]+1):ind.dfs[(j+1)]
    df.mat[idx, idx] = (1-df[j])/df[j]
  }
  return(df.mat)
}
#
check_mod = function(model){
  if(dlm::is.dlm(model)){
    model = dlmMod(model)
  }
  if(!is.vector(model$m0)){
    if(ncol(model$m0) != 1){
      stop("m0 must be a vector or a matrix with 1 column")
      }
    }
  p = length(model$m0)
  model$C0 = as.matrix(model$C0)
  if(p != dim(model$C0)[1] & p != dim(model$C0)[2]){
    stop("C0 must be a square matrix matching the dimension of m0")
    }
  if(!all.equal(model$C0, t(model$C0)) | !all(eigen(model$C0)$values >= 0)){
    stop("C0 must be a covariance matrix")
  }
  if(!is.vector(model$FF)){
    if(nrow(model$FF) != p){
      stop("FF must be a vector of length matching the dimension of m0, or a matrix with number of rows matching the dimension of m0")
    }
  }else{
    if(length(model$FF) != p){
      stop("FF must be a vector of length matching the dimension of m0, or a matrix with number of rows matching the dimension of m0")
    }
  }
  if(is.null(dim(model$GG)[3])){
    model$GG = as.matrix(model$GG)
  }else{
    if(is.na(dim(model$GG)[3])){
      model$GG = as.matrix(model$GG)
    }else{
      model$GG = as.array(model$GG)
    }
  }
  if(p != dim(model$GG)[1] & p != dim(model$GG)[2]){
    stop("GG must be a square matrix matching the dimension of m0, or an array with first two dimensions matching the dimension of m0")
  }
  model$m0 = as.matrix(model$m0)
  model$FF = as.matrix(model$FF)
  return(model)
}
#
check_logics = function(gam.init,sig.init,fix.gamma,fix.sigma,dqlm.ind){
  retval <- NULL
  retval$gam.init = gam.init
  retval$fix.gamma = fix.gamma
  retval$dqlm.ind = dqlm.ind
  if(dqlm.ind){
    if(gam.init!=0 | !fix.gamma){
      retval$gam.init <- gam.init <- 0
      retval$fix.gamma <- fix.gamma <- TRUE
    }
  }else{
    if(gam.init==0 && fix.gamma==TRUE){
      retval$dqlm.ind = TRUE
    }
  }
  if(fix.gamma & is.na(gam.init)){ stop("when fix.gamma = TRUE, gam.init must be specified") }
  if(fix.sigma & is.na(sig.init)){ stop("when fix.sigma = TRUE, sig.init must be specified") }
  return(retval)
}
#
check_ts = function(dat){
  dat = as.matrix(dat)
  if(all(dim(dat)>1)){
    stop("data must be univariate time-series")
  }
  if(dim(dat)[1]<dim(dat)[2]){
    dat = t(dat)
  }
  return(invisible(dat))
}
#
is.exdqlm = function(m){ return(inherits(m,"exdqlm")) }

disc_w_paths <- disc_w_resolve_paths()
parameters_path <- disc_w_paths$parameters_path

disc_w_load_parameters(parameters_path, env = environment())
#
dlm_df = function(y, model, df, dim.df, s.priors = list(l0=1,S0=10), just.lik=FALSE){
  ### Gets the Time Series Length / Replicate number
  TT = length(y)
  ### Gets the State Parameter dimension and Prior Distribution Parameters
  m0 = model$m0
  C0 = model$C0
  l0 = s.priors$l0
  S0 = s.priors$S0
  n = length(m0)
  ### Constructs F and G
  FF = model$FF
  GG = model$GG
  ### Variable Saving
  ### Posterior Distribution
  m = matrix(0,TT,n)
  C = array(0,c(TT,n,n))
  ### Predictive State Distribution
  a = matrix(0,TT,n)
  R = array(0,dim = c(TT,n,n))
  P = array(0,dim = c(TT,n,n))
  W = array(0,dim = c(TT,n,n))
  ### One-Step Ahead Forecast
  f = matrix(0,TT,1)
  Q = array(0,c(TT,1,1))
  inv.Q = array(0,c(TT,1,1))
  ### Regression Variables
  e = matrix(0,TT,1)
  A = array(0,c(TT,n,1))
  ### Sample Variance
  S = vector("numeric",TT)
  l = vector("numeric",TT)
  
  # Prior Dim Check
  m0 = matrix(m0,n,1)
  C0 = matrix(C0,n,n)
  ### Discount Factor Blocking
  df.mat = make_df_mat(df,dim.df,n)
  
  ### First Update
  ### One-step state forecast
  a[1,]  = GG[,,1] %*% m0
  P[1,,] = GG[,,1] %*% C0 %*% t(GG[,,1])
  W[1,,] = df.mat * P[1,,]
  R[1,,] = P[1,,] + W[1,,]
  ### One-step ahead forecast
  f[1,] = t(FF[,,1]) %*% a[1,]
  Q[1,,] = as.matrix(1 + t(FF[,,1]) %*% R[1,,] %*% FF[,,1],1,1)
  inv.Q[1,,] = chol2inv(chol(Q[1,,]))
  ### Auxilary Variables
  e[1,]  = as.matrix(y[1] - f[1,],1,1)
  A[1,,] = R[1,,] %*% FF[,,1] %*% inv.Q[1,,]
  ### Variance update
  l[1] = l0 + 1
  S[1] = l0 * S0 / l[1] + (t(e[1,]) %*% inv.Q[1,,] %*% e[1,] / l[1])
  ### Posterior Distribution
  m[1,]  = a[1,] + as.matrix(A[1,,],n,1) %*% e[1,]
  C[1,,] = R[1,,] - as.matrix(A[1,,],n,1) %*% Q[1,,] %*% t(A[1,,])
  C[1,,] = (C[1,,] + t(C[1,,]))/2
  
  for(i in 2:TT){
    ### One-step state forecast
    a[i,]  = GG[,,i] %*% m[i-1,]
    P[i,,] = GG[,,i] %*% C[i-1,,] %*% t(GG[,,i])
    W[i,,] = df.mat * P[i,,]
    R[i,,] = P[i,,] + W[i,,]
    ### One-step ahead forecast
    f[i,] = t(FF[,,i]) %*% a[i,]
    Q[i,,] = matrix(1 + t(FF[,,i])%*% R[i,,]%*% FF[,,i],1,1)
    inv.Q[i,,] = chol2inv(chol(Q[i,,]))
    ### Auxilary Variables
    e[i,]  = as.matrix(y[i] - f[i,],1,1)
    A[i,,] = as.matrix(R[i,,] %*% FF[,,i] %*% inv.Q[i,,],n,1)
    ### Variance update
    l[i] = l[i-1] + 1
    S[i] = l[i-1] * S[i-1] / l[i] + (t(e[i,]) %*% inv.Q[i,,] %*% e[i,] / l[i])
    ### Posterior Distribution
    m[i,]  = a[i,] + as.matrix(A[i,,],n,1) %*% e[i,]
    C[i,,] = R[i,,] - as.matrix(A[i,,],n,1) %*% Q[i,,] %*% t(as.matrix(A[i,,],n,1))
    C[i,,] = (C[i,,] + t(C[i,,]))/2
  }
  
  ### Adjust By Variance
  R[1,,] = S0 * R[1,,]
  Q[1,,]   = S0 * Q[1,,]
  C[1,,]   = S[1] * C[1,,]
  for(i in 2:TT){
    R[i,,] = S[i-1] * R[i,,]
    Q[i,,]   = S[i-1] * Q[i,,]
    C[i,,]   = S[i] * C[i,,]
  }
  
  # Calculate Log-Likelihood
  det.Q = log(abs(Q[1,,])) ; llik = lgamma((l0+1)/2)-lgamma(l0/2)-log(pi*l0)/2-det.Q/2-(l0+1)*log(1+t(e[1,])%*%inv.Q[1,,]%*%e[1,]/l0)/2
  for(t in 2:TT){
    det.Q = log(abs(Q[t,,]))
    llik = llik + lgamma((l[t-1]+1)/2)-lgamma(l[t-1]/2)-log(pi*l[t-1])/2-det.Q/2-(l[t-1]+1)*log(1+t(e[t,])%*%inv.Q[t,,]%*%e[t,]/l[t-1])/2
  }
  if(just.lik){
    return(list(llik = llik))
  }
  
  ## SMOOTHING
  ### Initializes recursive relations
  sa = matrix(0,TT,n)
  sR = array(0, dim = c(TT,n,n))
  ### Runs the recursive equations
  sa[TT,]  = m[TT,]
  sR[TT,,] = C[TT,,]
  for(k in 1:(TT-1)){
    ### Computes the Auxilary recursion Variable B
    B = C[TT-k,,] %*% t(GG[,,TT-k+1]) %*% solve(R[TT-k+1,,])
    sa[TT-k,] = m[TT-k,] + B %*% (sa[TT-k+1,] - a[TT-k+1,])
    sR[TT-k,,] = C[TT-k,,] + B %*% (sR[TT-k+1,,] - R[TT-k+1,,]) %*% t(B)
  }
  ### Adjusts the variance update
  for(k in 1:TT){
    sR[TT-k,,] = S[TT] * sR[TT-k,,] / S[TT-k]
  }
  return(list(fm = m, fC = C, m = sa, C = sR,model = model, s = S, n = l))
}
#
make_df_mat = function(df,dim.df,n){
  if(sum(dim.df)!=n){ stop("sum of component dimensions given in dim.df does not match m0") }
  if(length(df)!=length(dim.df)){ stop("length of component discount factors does not match length of component dimensions") }
  n.dfs = length(dim.df)
  ind.dfs = c(0,sapply(1:length(dim.df),function(x){sum(dim.df[1:x])}),n)
  df.mat = matrix(0,n,n)
  for(j in 1:n.dfs){
    if (dim.df[j] <= 0L) next
    idx <- (ind.dfs[j]+1):ind.dfs[(j+1)]
    df.mat[idx, idx] = (1-df[j])/df[j]
  }
  return(df.mat)
}
#
make_df_mat_k = function(df,dim.df,n,k){
  if(sum(dim.df)!=n){ stop("sum of component dimensions given in dim.df does not match m0") }
  if(length(df)!=length(dim.df)){ stop("length of component discount factors does not match length of component dimensions") }
  n.dfs = length(dim.df)
  ind.dfs = c(0,sapply(1:length(dim.df),function(x){sum(dim.df[1:x])}),n)
  df.mat = matrix(0,n,n)
  for(j in 1:n.dfs){
    if (dim.df[j] <= 0L) next
    idx <- (ind.dfs[j]+1):ind.dfs[(j+1)]
    df.mat[idx, idx] = (1-df[j]^k)/df[j]^k
  }
  return(df.mat)
}
#
H_t_k_r <- function(GG, t, k, r){
  n <- dim(GG)[1]
  I <- diag(n)
  for (s in (t+k-r):(t+k)) {
    I <- GG[,,s] %*% I   
  }
  return(I)
}
#
# Function to estimate log density using KDE for univariate data
estimate_log_density_kde_univariate <- function(data, points) {
  kde_result <- kde(data)
  density_estimates <- predict(kde_result, x = points)
  log_density <- log(density_estimates + .Machine$double.eps*100)  # Add small value to avoid log(0)
  return(log_density)
}
#
# Function to estimate the expectation term for univariate data
estimate_expectation_term_univariate <- function(sample_from_p, sample_size) {
  # Generate a sample from the standard normal distribution
  sample_from_normal <- rnorm(sample_size)
  
  # Estimate log density of p at points sampled from the standard normal distribution
  log_density_estimates <- estimate_log_density_kde_univariate(sample_from_p, sample_from_normal)
  
  # Compute the Monte Carlo estimate of the expectation
  expectation_estimate <- mean(log_density_estimates)
  
  return(expectation_estimate)
}
#
# Function to estimate the KL divergence D_KL(N(0, 1) || p) for univariate data
estimate_kl_divergence_univariate_normal_to_p <- function(sample_from_p, sample_size) {
  # Estimate the expectation term
  expectation_term <- estimate_expectation_term_univariate(sample_from_p, sample_size)
  
  # Compute the KL divergence
  kl_divergence <- -0.5 * log(2 * pi) - 0.5 - expectation_term
  
  return(kl_divergence)
}
#
# Function to estimate KL divergence using k-NN with entropy package for multivariate data
estimate_kl_divergence_knn_entropy <- function(sample_from_p, sample_size, k = 5) {
  # Generate a sample from the multivariate standard normal distribution
  sample_from_normal <- matrix(rnorm(sample_size * ncol(sample_from_p)), ncol = ncol(sample_from_p))
  
  # Estimate KL divergence using entropy package's KL.div function
  kl_divergence <- KL.divergence(sample_from_p, sample_from_normal, k = k)
  
  # Return only the final estimate
  return(tail(kl_divergence, n = 1))
}
#
# Unified function to estimate KL divergence based on the input sample
estimate_kl_divergence <- function(sample, sample_size = 10000) {
  # Check if the sample is univariate or multivariate
  if (is.vector(sample) || ncol(sample) == 1) {
    # Univariate case
    if (is.vector(sample)) {
      sample_from_p <- sample
    } else {
      sample_from_p <- sample[, 1]
    }
    
    # Estimate the KL divergence using the KDE-based method
    estimated_kl_divergence <- estimate_kl_divergence_univariate_normal_to_p(sample_from_p, sample_size)
    
  } else {
    # Multivariate case
    sample_from_p <- sample
    
    # Estimate the KL divergence using the k-NN based method with entropy package
    estimated_kl_divergence <- estimate_kl_divergence_knn_entropy(sample_from_p, sample_size, k = 5)
  }
  
  # Return the estimate
  return(estimated_kl_divergence)
}
#
# Function to estimate differential entropy using KDE for univariate data
estimate_differential_entropy_kde_univariate <- function(data) {
  kde_result <- kde(data)
  estimates <- kde_result$estimate
  estimates[estimates <= 0] <- .Machine$double.eps*100 # Prevent log(0) issues
  log_estimates <- log(estimates)
  log_estimates[!is.finite(log_estimates)] <- 0 # Handle non-finite values
  entropy_estimate <- -sum(estimates * log_estimates) * diff(kde_result$eval.points)[1]
  return(entropy_estimate)
}
#
# Function to estimate differential entropy using KDE for multivariate data
estimate_differential_entropy_kde_multivariate <- function(data) {
  kde_result <- kde(data)
  estimates <- kde_result$estimate
  estimates[estimates <= 0] <- .Machine$double.eps*100 # Prevent log(0) issues
  log_estimates <- log(estimates)
  log_estimates[!is.finite(log_estimates)] <- 0 # Handle non-finite values
  entropy_estimate <- -sum(estimates * log_estimates) * prod(diff(kde_result$eval.points[[1]]))
  return(entropy_estimate)
}
#
# Function to estimate the KL divergence D_KL(p || N(0, I)) for univariate data
estimate_kl_divergence_univariate <- function(data) {
  # Estimate the differential entropy H(p)
  H_p <- estimate_differential_entropy_kde_univariate(data)
  
  # Compute the expected value of the squared norm of the vectors
  E_p_x2 <- mean(data^2)
  
  # Dimensionality is 1 for univariate data
  k <- 1
  
  # Compute the KL divergence
  kl_divergence <- -H_p + (k / 2) * log(2 * pi) + (1 / 2) * E_p_x2
  
  return(kl_divergence)
}
#
# Function to estimate the KL divergence D_KL(p || N(0, I)) for multivariate data
estimate_kl_divergence_multivariate <- function(data) {
  # Estimate the differential entropy H(p)
  H_p <- estimate_differential_entropy_kde_multivariate(data)
  
  # Dimensionality of the vectors
  k <- ncol(data)
  
  # Compute the expected value of the squared norm of the vectors
  E_p_xTx <- mean(rowSums(data^2))
  
  # Compute the KL divergence
  kl_divergence <- -H_p + (k / 2) * log(2 * pi) + (1 / 2) * E_p_xTx
  
  return(kl_divergence)
}
#
# Wrapper function for any sample
compute_kl_divergence <- function(sample) {
  # Ensure the input sample is a matrix
  sample <- as.matrix(sample)
  
  # Determine if the sample is univariate or multivariate
  if (ncol(sample) == 1) {
    kl_divergence <- estimate_kl_divergence_univariate(sample)
  } else {
    kl_divergence <- estimate_kl_divergence_multivariate(sample)
  }
  
  return(kl_divergence)
}
#
concatenate_matrix_columns <- function(matrix_input) {
  # Concatenate the columns of the matrix
  concatenated_vector <- c(matrix_input)
  return(concatenated_vector)
}
#
preallocate_matrix_list <- function(column_counts, num_rows) {
  # Initialize an empty list
  matrix_list <- vector("list", length(column_counts))
  
  # Loop through the column counts and create matrices
  for (i in seq_along(column_counts)) {
    num_cols <- column_counts[i]
    matrix_list[[i]] <- matrix(NA, nrow = num_rows, ncol = num_cols)
  }
  
  return(matrix_list)
}

# Read and process ELI_lon data
covariates <- disc_w_read_covariates(disc_w_paths$cov_1_eli_path, disc_w_paths$cov_2_oni_path)
ELI_lon <- covariates$ELI_lon
merged_sst_data <- covariates$merged_sst_data
ELI_lon$time <- as.Date(ELI_lon$time)
adjustment_years <- 170
ELI_lon$time <- ELI_lon$time - lubridate::years(adjustment_years)
#
CFSToCMS_CONVERSION_FACTOR = 0.0283168466
# Read and process USGS data (non-fatal if the external service is unavailable)
San_Lorenzo_Daily_USGS_R <- tryCatch({
  if (!requireNamespace("dataRetrieval", quietly = TRUE)) {
    stop("package 'dataRetrieval' is not installed")
  }
  data_usgs_r <- dataRetrieval::readNWISdv(siteNumbers = site_code[1], parameterCd = "00060", statCd = "00003")
  out <- data_usgs_r %>%
    mutate(
      timestamp = as.Date(Date),
      data0 = log(X_00060_00003 * CFSToCMS_CONVERSION_FACTOR + 1)
    ) %>%
    filter(timestamp > as.Date("1979-01-01"))
  out$time <- out$timestamp
  out
}, error = function(e) {
  warning(
    sprintf(
      "USGS readNWISdv failed (%s). Continuing fit without live USGS fetch.",
      conditionMessage(e)
    ),
    call. = FALSE
  )
  data.frame(
    timestamp = as.Date(character(0)),
    data0 = numeric(0),
    time = as.Date(character(0))
  )
})

###########################################################################################
####################################### Forecasts ######################################### 
###########################################################################################
forecasts <- disc_w_read_forecasts(disc_w_paths$nws_forecast_path, disc_w_paths$glofas_forecast_path)
nws_forecast <- forecasts$nws_forecast
# Forecast adapters now provide log1p(cms); keep that scale unchanged.
num_ens_nws <- dim(nws_forecast)[2]-1

glofas_forecast <- forecasts$glofas_forecast
glofas_forecast$target_date <- as.Date(glofas_forecast$target_date)
cutoff_date_local <- suppressWarnings(as.Date(Sys.getenv("DISC_W_CUTOFF_DATE", "2022-12-25")))
if (is.na(cutoff_date_local)) cutoff_date_local <- as.Date("2022-12-25")
specific_date <- suppressWarnings(
  as.Date(Sys.getenv("DISC_W_FORECAST_START_DATE", as.character(cutoff_date_local + 1L)))
)
if (is.na(specific_date)) specific_date <- cutoff_date_local + 1L
glofas_forecast <- glofas_forecast[glofas_forecast$target_date >= specific_date, ]
# Forecast adapters now provide log1p(cms); keep that scale unchanged.

num_ens_glofas <- dim(glofas_forecast)[2]-1

ensemble_bundle <- disc_w_build_ensembles(glofas_forecast, nws_forecast)
ensembles <- ensemble_bundle$ensembles
J <- ensemble_bundle$J
num_mem <- ensemble_bundle$num_mem
ranges <- ensemble_bundle$ranges
mean_forecast <- ensemble_bundle$mean_forecast

###########################################################################################
####################################### Covs, Retros, More ################################ 
###########################################################################################

covariate_bundle <- disc_w_build_covariates_and_retro(disc_w_paths, ranges)
X <- covariate_bundle$X
X_f <- covariate_bundle$X_f
Y <- covariate_bundle$Y
TT <- covariate_bundle$TT
J <- covariate_bundle$J

if(use_covariates){
  ending <- "_exAL_synth_DISC"
}else{
  ending <- "_exAL_synth_simp"
}
#
# Model setup without covariates
s_yy <- sd(Y, na.rm = TRUE)
m_yy <- mean(Y, na.rm = TRUE) + s_yy * qnorm(p0)
kk <- 0.5 * s_yy
structure_spec <- exdqlm_multivar_read_structure_spec_from_env(
  include_trend_keys = c("DISC_W_INCLUDE_TREND", "UNIFIED_EXDQLM_MULTIVAR_INCLUDE_TREND"),
  enabled_harmonic_keys = c("DISC_W_ENABLED_HARMONIC_INDICES", "UNIFIED_EXDQLM_MULTIVAR_ENABLED_HARMONIC_INDICES"),
  default_harmonics = harmonics
)
structure_model <- exdqlm_multivar_build_structure(
  m_yy = m_yy,
  kk = kk,
  df_t = df_t,
  df_s1 = df_s1,
  df_s2 = df_s2,
  df_s67 = df_s67,
  lam1 = lam1,
  lam2 = lam2,
  include_trend = structure_spec$include_trend,
  enabled_harmonic_indices = structure_spec$enabled_harmonic_indices,
  default_harmonics = harmonics,
  season_period = 363.5854,
  trend_c0_scale = 1.0,
  season_c0_scale = 0.5
)
harm <- structure_model$enabled_harmonics
model <- structure_model$model
p <- structure_model$p
#
idx <- 1:TT
y <- Y[,idx]
TT_sub <- length(idx)
#
if (is.null(nrow(y))) {
  JJJ <- 1
  y <- array(y, c(JJJ, length(y)))
} else {
  JJJ <- nrow(Y)
  y <- array(y, c(JJJ, ncol(y)))
}
#
gam.init <- array(rep(0, JJJ), c(JJJ, 1))
sig.init <- array(rep(1, JJJ), c(JJJ, 1))
PriorSigma <- array(NA_real_, c(JJJ, 2))
PriorGamma <- array(NA_real_, c(JJJ, 3))
verbose <- TRUE

###########################################################################################
###########################################################################################
###########################################################################################
m0 <- c(model$m0, rep(0, p*J))
C0 <- bdiag(model$C0, 0.5 * kk * diag(p*J))
##########################################  
##########################################
df <- structure_model$df
df.discrep <- df.discrep*rep(df,J)
dim.df <- structure_model$dim.df
k <- 10
##########################################2
##########################################
model_simp <- model
df_simp <- df
dim.df_simp <- dim.df
model_simp$GG <- array(model_simp$GG, c(p, p, TT))
model_simp$FF <- array(model_simp$FF, c(p, 1, TT))
##########################################2
##########################################
df.mat <- make_df_mat(df, dim.df, p)
df.mat.k <- make_df_mat_k(df, dim.df, p, k)

df1 <- structure_model$df1
df.mat_f1 <- make_df_mat(df1, dim.df, p)
df.mat.k_f1 <- make_df_mat_k(df1, dim.df, p, k)
df2 <- structure_model$df2
df.mat_f2 <- make_df_mat(df2, dim.df, p)
df.mat.k_f2 <- make_df_mat_k(df2, dim.df, p, k)

# df.mat_f2 <- make_df_mat(df*lam1, dim.df, p)
# df.mat.k_f2 <- make_df_mat_k(df*lam1, dim.df, p, k)
# df.mat_f2 <- make_df_mat(df*lam2, dim.df, p)
# df.mat.k_f2 <- make_df_mat_k(df*lam2, dim.df, p, k)

if (J <= 0) {
  ex.df.mat <- df.mat
  ex.df.mat.k <- df.mat.k
} else {
  extra_df.mat <- make_df_mat(df.discrep, c(rep(dim.df,J)), p*J)
  extra_df.mat.k<- make_df_mat_k(df.discrep, c(rep(dim.df,J)), p*J, k)
  
  ex.df.mat <- bdiag(df.mat, extra_df.mat)
  ex.df.mat.k <- bdiag(df.mat.k, extra_df.mat.k)

  ex.df.mat_f_T <- bdiag(df.mat_f1, extra_df.mat)
  ex.df.mat_f_T <- as.matrix(ex.df.mat_f_T)

  ex.df.mat.k_f_T <- bdiag(df.mat.k_f1, extra_df.mat.k)
  ex.df.mat.k_f_T <- as.matrix(ex.df.mat.k_f_T)

  ex.df.mat_f <- bdiag(df.mat_f2, extra_df.mat)
  ex.df.mat_f <- as.matrix(ex.df.mat_f)

  ex.df.mat.k_f <- bdiag(df.mat.k_f2, extra_df.mat.k)
  ex.df.mat.k_f <- as.matrix(ex.df.mat.k_f)

  # Get the dimensions of the input matrices
  n <- nrow(ex.df.mat_f)
  m <- ncol(ex.df.mat_f)
  DF.MAT <- array(0, dim = c(n, m, 2))
  DF.MAT[,,1] <- ex.df.mat_f_T
  DF.MAT[,,2] <- ex.df.mat_f

  DF.MAT_k <- array(0, dim = c(n, m, 2))
  DF.MAT_k[,,1] <- ex.df.mat.k_f_T
  DF.MAT_k[,,2] <- ex.df.mat.k_f

}

create_block_diag <- exdqlm_multivar_create_block_diag

# Discrepancies
A <- model$GG; n <- J+1;
result_GG <- create_block_diag(A, n);
GG <- array(result_GG, dim = c(dim(result_GG)[1], dim(result_GG)[1], TT))
model$GG <- GG

A <- model$FF; n <- J+1;
result_FF <- create_block_diag(A, n);
result_FF[1:p,] <- matrix(model$FF, p, J + 1)
FF <- array(result_FF, c(p*(1 + J), 1 + J, TT))
model$FF <- FF

FF <- model$FF
GG <- model$GG
model$m0 <- m0 
model$C0 <- C0 
ppx <- 0

if (use_covariates) {
  px <- dim(X)[2]
  ppx <- px + 1

  FFx <- array(0, c(dim(FF)[1] + ppx, dim(FF)[2], TT))
  FFx[1:dim(FF)[1],1:dim(FF)[2],] <- FF
  GGx <- array(0, c(dim(GG)[1] + ppx, dim(GG)[2]+ ppx, TT))
  GGx[1:dim(GG)[1],1:dim(GG)[2],] <- GG

  Fx <- rbind(rep(1, J + 1), matrix(0, nrow = px, ncol = J + 1))
  FFx[(dim(FF)[1]+1):dim(FFx)[1],,] <- Fx 

  Gx <- as.matrix(bdiag(lambda, diag(px)))
  Gx <- array(rep(Gx, TT), dim = c(ppx, ppx, TT))
  if (ppx > 1L) {
    Gx[1, 2:ppx, ] <- as.matrix(t(X))
  }
  GGx[(dim(GG)[1]+1):dim(GGx)[1],(dim(GG)[2]+1):dim(GGx)[1],] <- Gx

  model$FF <- FFx
  model$GG <- GGx

  extra_df.mat <- make_df_mat(c(df_trans,df_covs), c(1,px), ppx)
  extra_df.mat.k <- make_df_mat_k(c(df_trans,df_covs), c(1,px), ppx, k)

  ex.df.mat <- bdiag(ex.df.mat, extra_df.mat)
  ex.df.mat.k <- bdiag(ex.df.mat.k, extra_df.mat.k)

  model$m0 <- c(model$m0, rep(0, ppx))
  model$C0 <- bdiag(model$C0, 0.1 * kk * diag(ppx))
  
  FF <- model$FF
  GG <- model$GG
}


L = L.fn(p0)
U = U.fn(p0)

if (identical(DISC_GAMSIG_INIT_MODE, "robust")) {
  robust_spread <- apply(y, 1, function(v) {
    out <- suppressWarnings(stats::mad(v, center = stats::median(v, na.rm = TRUE), constant = 1.4826, na.rm = TRUE))
    if (!is.finite(out) || out <= 0) {
      out <- suppressWarnings(stats::sd(v, na.rm = TRUE))
    }
    if (!is.finite(out) || out <= 0) {
      out <- 1
    }
    out
  })
  robust_spread <- as.numeric(robust_spread)
  sigma_seed <- pmax(DISC_GAMSIG_INIT_SIGMA_FLOOR, DISC_GAMSIG_INIT_SIGMA_SCALE * robust_spread)
  gamma_seed <- if (isTRUE(DISC_W_AL_MODE)) {
    0
  } else {
    pmin(pmax(DISC_GAMSIG_INIT_GAMMA, L + 1e-6), U - 1e-6)
  }
  sig.init[, 1] <- sigma_seed
  gam.init[, 1] <- gamma_seed
  if (isTRUE(DISC_GAMSIG_OBJECTIVE_GUARD_LOG_FAILURES)) {
    cat(sprintf(
      "[gamsig_init] p0=%s mode=robust gamma_seed=%0.6f sigma_seed_min=%0.6f sigma_seed_max=%0.6f\n",
      as.character(p0),
      as.numeric(gamma_seed),
      as.numeric(min(sigma_seed, na.rm = TRUE)),
      as.numeric(max(sigma_seed, na.rm = TRUE))
    ))
    flush.console()
  }
}

FF_list <- vector("list", J)
GG_list <- vector("list", J)

######################
# Without covariates for the forceasting period
for (j in 1:J) {
  jj <- J-j+1
  GG_tsc <- result_GG[1:(p*(jj+1)),1:(p*(jj+1))]
  GG_list[[j]] <- matrix(GG_tsc, nrow = p*(jj+1), ncol = p*(jj+1) )
  FF_tsc <- result_FF[1:(p*(jj+1)), 2:(jj+1)]
  FF_list[[j]] <- matrix(FF_tsc, nrow = p*(jj+1), ncol = (jj) )
}

########### For every j
for (j in 1:(J+1)) {
  if (!is.na(gam.init[j,])) {
    if (gam.init[j,] < L | gam.init[j,] > U) {
      stop(sprintf("gam.init must be between %s and %s for %s quantile", 
                    round(L, 3), round(U, 3), p0))
    }
  } 
}
###########################################################################################
########### For every j
for (j in 1:(J+1)) {
  if (is.na(PriorSigma[j,1]) || is.na(PriorSigma[j,2])) {
    m_sigma = 1
    v_sigma = 1e+10
    PriorSigma[j,1] = (m_sigma^2)/(v_sigma) + 2 
    PriorSigma[j,2] = (m_sigma^3)/(v_sigma) + m_sigma 
  }
}
###########################################################################################
########### For every j
for (j in 1:(J+1)) {
  if (is.na(PriorGamma[j,1]) || is.na(PriorGamma[j,2]) || is.na(PriorGamma[j,3])) {
    PriorGamma[j,1]  = 0
    PriorGamma[j,2]  = 1e+10
    PriorGamma[j,3] = 1
  }
}
###########################################################################################
########### For every j
gam0 = gam.init 
sig0 = sig.init 

preallocate_matrix_list <- function(column_counts, num_rows) {
  n_list <- length(column_counts)
  if (length(num_rows) != n_list) {
    stop(sprintf(
      "preallocate_matrix_list: num_rows length (%d) must match column_counts length (%d)",
      as.integer(length(num_rows)),
      as.integer(n_list)
    ), call. = FALSE)
  }
  matrix_list <- vector("list", n_list)
  for (i in seq_along(column_counts)) {
    num_cols <- suppressWarnings(as.integer(column_counts[i]))
    num_rows_i <- suppressWarnings(as.integer(num_rows[i]))
    if (!is.finite(num_cols) || num_cols <= 0L) {
      stop(sprintf("preallocate_matrix_list: invalid num_cols at i=%d (%s)", as.integer(i), as.character(column_counts[i])), call. = FALSE)
    }
    if (!is.finite(num_rows_i) || num_rows_i <= 0L) {
      stop(sprintf("preallocate_matrix_list: invalid num_rows at i=%d (%s)", as.integer(i), as.character(num_rows[i])), call. = FALSE)
    }
    matrix_list[[i]] <- matrix(NA_real_, nrow = num_rows_i, ncol = num_cols)
  }
  matrix_list
}
fill_with_scalar <- function(matrix_list, scalar, label) {
  val <- suppressWarnings(as.numeric(scalar))
  if (length(val) != 1L || !is.finite(val)) {
    stop(sprintf("%s must be a finite scalar; got length=%d value=%s", label, as.integer(length(val)), as.character(scalar)), call. = FALSE)
  }
  for (i in seq_along(matrix_list)) {
    matrix_list[[i]][] <- val
  }
  matrix_list
}

###########################################################################################
########### For every j 

# Gamma, Sigma
E1 <- array(NA_real_, c(J+1,1))
E1[,] <- 1
E2 <- array(NA_real_, c(J+1,1))
E2[,] <- 1
new.gamsig.out = list(E.gam = gam0,
                      V.gam = E1, 
                      E.sigma = sig0, 
                      V.sig = E2,
                      E.inv.sigma = 1/sig0, 
                      E.c2.invb.absgam2.sigma = sig0 * (C.fn(p0, gam0)^2) * (abs(gam0)^2)/B.fn(p0, gam0), 
                      E.c.invb.absgam = C.fn(p0, gam0) * abs(gam0)/B.fn(p0, gam0),  
                      E.c.a.invb.absgam = C.fn(p0, gam0) * A.fn(p0, gam0) * abs(gam0)/B.fn(p0, gam0), 
                      E.a2.invb.inv.sigma = (A.fn(p0,gam0)^2)/(B.fn(p0, gam0) * sig0), 
                      E.invb.inv.sigma = 1/(sig0 * B.fn(p0, gam0)), 
                      E.a.invb.inv.sigma = A.fn(p0, gam0)/(B.fn(p0, gam0) * sig0),
                      E.log.sig.b = log( sig0*B.fn(p0, gam0) ),
                      E.log.sig = log(sig0),
                      E.prior.sig.gam = array(0, c(J+1,1)),
                      entrop = array(0, c(J+1,1))  )
###########################################################################################
########### For every j

# S_t (Before Forecast)
E1 <- array(NA_real_, c(J+1,TT_sub))
E1[,] <- truncnorm::etruncnorm(a = 0, b = Inf,  mean = 1, sd = 0.1)
E2 <- array(NA_real_, c(J+1,TT_sub))
E2[,] <- E1[,]^2 
new.sts.out = list(E.sts = E1, 
                    E.sts2 = E2,
                    tot.entrop = array(0, c(J+1,1)) )
# S_t (After Forecast)
E1 <- preallocate_matrix_list(num_mem, ranges)
E2 <- preallocate_matrix_list(num_mem, ranges)
E1 <- fill_with_scalar(E1, 1, "new.sts.out_f E.sts init")
E2 <- fill_with_scalar(E2, 1, "new.sts.out_f E.sts2 init")

entrop_s <- preallocate_matrix_list(num_mem, rep(1,J) )
entrop_s <- fill_with_scalar(entrop_s, 0, "new.sts.out_f entrop init")

new.sts.out_f = list(E.sts = E1, 
                    E.sts2 = E2,
                    tot.entrop = entrop_s )

###########################################################################################
########### For every j

# U_t (Before Forecast)
E1 <- array(NA_real_, c(J+1,TT_sub))
E1[,] <- 1/sig0
E2 <- array(NA_real_, c(J+1,TT_sub))
E2[,] <- sig0
new.uts.out = list(E.uts = E1, 
                    E.inv.uts = E2,
                    E.log.uts = array(0, c(J+1,1)),
                    tot.entrop = array(0, c(J+1,1)) )

# U_t (After Forecast)
E1 <- preallocate_matrix_list(num_mem, ranges)
E2 <- preallocate_matrix_list(num_mem, ranges)
for (jj in seq_len(J)) {
  sigma_j <- suppressWarnings(as.numeric(sig0[jj + 1, 1]))
  if (!is.finite(sigma_j) || sigma_j <= 0) {
    stop(sprintf("Invalid sigma seed for forecast ensemble j=%d: %s", as.integer(jj), as.character(sigma_j)), call. = FALSE)
  }
  E1[[jj]][] <- 1 / sigma_j
  E2[[jj]][] <- sigma_j
}

entrop_u <- preallocate_matrix_list(num_mem, rep(1,J))
entrop_u <- fill_with_scalar(entrop_u, 0, "new.uts.out_f entrop init")

new.uts.out_f = list(E.uts = E1, 
                    E.inv.uts = E2,
                    E.log.uts = entrop_u,
                    tot.entrop = entrop_u )

###########################################################################################
# Exps
init.dlm = dlm_df(colMeans(y), model_simp, df_simp, dim.df_simp, 
                  s.priors = list(l0 = 1, S0 = mean(sig0)), 
                  just.lik = FALSE)
FF_t <- aperm(model_simp$FF, c(2, 1, 3))
multiply_matrices <- function(slice_index) {
  t(FF_t[1,,slice_index]) %*% init.dlm$m[slice_index,]
}
result_list <- lapply(1:TT_sub, multiply_matrices)
result_array <- array(unlist(result_list), dim = c(TT_sub,1))
exps0 = c(result_array) + stats::qnorm(p0, 0, sqrt(init.dlm$s[TT_sub]))
exps0 = t(replicate(J+1, exps0))

exps0 <- cbind(exps0,mean_forecast)
exps2 <- exps0^2

new.theta.out = list(exps = exps0, 
                      exps2 = exps2)
###########################################################################################
iter = 0
conv.count = 0
new.max = Inf
###########################################################################################
########### For every j
seq.gamma = new.gamsig.out$E.gam
seq.sigma = new.gamsig.out$E.sigma
###########################################################################################
update_sts<-function(y, exps,inv.uts,c2.invb.absgam2.sigma,c.invb.absgam,c.a.invb.absgam, TTT){
  if (isTRUE(DISC_W_AL_MODE)) {
    z <- rep(0, TTT)
    return(list(sts.sig2=rep(1, TTT),sts.mu=z,
                E.sts=z,E.sts2=z,
                tot.entrop = 0))
  }
  inv.uts <- pmax(as.numeric(inv.uts), 1e-10)
  denom <- pmax(1 + c2.invb.absgam2.sigma * inv.uts, 1e-10)
  s.sig2<-1/denom; s.sig = sqrt(pmax(s.sig2, 1e-10))
  s.mu<-s.sig2*(c.invb.absgam*(y-exps)*inv.uts-c.a.invb.absgam)
  #
  E.sts = truncnorm::etruncnorm(a=rep(0,TTT),b=rep(Inf,TTT),mean=s.mu,sd=s.sig)
  V.sts = truncnorm::vtruncnorm(a=rep(0,TTT),b=rep(Inf,TTT),mean=s.mu,sd=s.sig)
  E.sts2 = s.mu^2 + s.sig2 + s.mu*s.sig*exp(stats::dnorm(-s.mu/s.sig,log = TRUE)-stats::pnorm(s.mu/s.sig,log.p = TRUE))
  E.sts[!is.finite(E.sts)] <- pmax(s.mu[!is.finite(E.sts)], 0)
  E.sts2[!is.finite(E.sts2)] <- pmax(E.sts[!is.finite(E.sts2)]^2 + s.sig2[!is.finite(E.sts2)], 1e-10)
  return(list(sts.sig2=s.sig2,sts.mu=s.mu,
              E.sts=E.sts,E.sts2=E.sts2,
              tot.entrop = sum(0.5*log2(2*pi*exp(1)*s.sig2) - 1 )))
}

Kprime <- function(x){
sqrt(pi/2/x) * expint_E1(2*x) * exp(x)
}

gig_entrop <- function(a,b){
nu <- 0.5
s.ab <- sqrt(a*b)
K1 <- besselK(s.ab, nu)
K2 <- besselK(s.ab, nu+1)
K3 <- besselK(s.ab, nu-1)
y <- 0.5*log(b/a) + log(2*K1) - (nu-1)*Kprime(s.ab)/K1 + s.ab/2/K1*(K2 + K3)
return(y)
}

###########################################################################################

update_uts<-function(y, exps,exps2,sts,sts2,inv.sigma,a2.invb.inv.sigma,invb.inv.sigma,c.invb.absgam,c2.invb.absgam2.sigma){
  u.lambda = 0.5
  u.psi = as.numeric(a2.invb.inv.sigma + 2*inv.sigma)
  u.chi = as.numeric(invb.inv.sigma*(y^2-2*y*exps+exps2) - 2*c.invb.absgam*sts*(y-exps) + c2.invb.absgam2.sigma*sts2)

  u.psi[!is.finite(u.psi) | u.psi <= 0] <- 1e-6
  u.chi[!is.finite(u.chi) | u.chi <= 0] <- 1e-6

  bessel_ratio_safe <- function(z, nu) {
    zz <- as.numeric(z)
    zz[!is.finite(zz) | zz <= 0] <- 1e-8
    vapply(zz, function(val) {
      out <- tryCatch(
        HyperbolicDist::besselRatio(val, nu, 1, Inf),
        error = function(e) NA_real_
      )
      if (!is.finite(out)) 1 else out
    }, FUN.VALUE = numeric(1))
  }

  s.ab <- sqrt(pmax(u.psi * u.chi, 1e-12))
  ratio <- bessel_ratio_safe(s.ab, u.lambda)

  E.uts = sqrt(u.chi/u.psi) * ratio
  E.inv.uts = sqrt(u.psi/u.chi) * ratio - 2*u.lambda/u.chi
  E.uts[!is.finite(E.uts)] <- 1e-10
  E.inv.uts[!is.finite(E.inv.uts)] <- 1e-10
  E.uts <- pmax(E.uts, 1e-10)
  E.inv.uts <- pmax(E.inv.uts, 1e-10)

  nu <- 0.5
  K1 <- besselK(s.ab, nu)
  K1[!is.finite(K1) | K1 <= 0] <- 1e-12
  kp <- Kprime(s.ab)
  kp[!is.finite(kp)] <- 0

  E.log.uts <- sum(kp/K1 - 0.5*log(u.psi/u.chi))
  if (!is.finite(E.log.uts)) E.log.uts <- 0
  tot.ent <- sum(gig_entrop(u.psi,u.chi))
  if (!is.finite(tot.ent)) tot.ent <- 0

  return(list(uts.lambda=u.lambda,
              uts.psi=u.psi,uts.chi=u.chi,
              E.uts=E.uts,E.inv.uts=E.inv.uts,
              E.log.uts=E.log.uts,
              tot.entrop=tot.ent))
}

###########################################################################################
########################
PriorGammaDens <- function(gamma, prior) {
  crch::dtt(gamma, 
            location = prior[1], 
            scale = prior[2],   
            df = prior[3], 
            left = L, right = U, 
            log = FALSE)
}

  print(c(n.samp, 222))
  flush.console()
update_gamma_sigma<-function( y, nn, prior_g, prior_s, 
                              gamma,var.gam,sigma,var.sig,
                              exps,exps2,
                              sts,sts2,
                              uts,inv.uts, 
                              s_init, g_init,
                              Climate_Center,
                              ensembles_j = NULL, num_mem_j = NULL, k_forecast = NULL,
                              sts_f = NULL,sts2_f = NULL,
                              uts_f= NULL,inv.uts_f= NULL,
                              context_label = ""){

log_guard_failure <- function(msg) {
  if (isTRUE(DISC_GAMSIG_OBJECTIVE_GUARD_LOG_FAILURES)) {
    cat(sprintf("[gamsig_guard] %s\n", msg))
    flush.console()
  }
}

log_stabilization_event <- function(msg) {
  if (isTRUE(DISC_GAMSIG_OBJECTIVE_GUARD_LOG_FAILURES)) {
    cat(sprintf("[gamsig_stabilization] %s\n", msg))
    flush.console()
  }
}

s_seed <- suppressWarnings(as.numeric(s_init)[1])
if (!is.finite(s_seed) || s_seed <= 0) {
  s_seed <- 1
}
g_seed <- suppressWarnings(as.numeric(g_init)[1])
if (!is.finite(g_seed)) {
  g_seed <- 0
}
if (isTRUE(DISC_W_AL_MODE)) {
  g_seed <- 0
}
g_seed <- pmin(pmax(g_seed, L + 1e-12), U - 1e-12)

build_mode_result <- function(theta_s_val, theta_g_val, guard = FALSE, guard_msg = "") {
  pi <- plogis(theta_g_val)
  pi <- pmin(pmax(pi, 1e-12), 1 - 1e-12)
  sig <- exp(theta_s_val)
  gam <- if (isTRUE(DISC_W_AL_MODE)) 0 else L + (U - L) * pi
  a <- A.fn(p0, gam)
  b <- B.fn(p0, gam)
  c <- C.fn(p0, gam)
  var_sig_seed <- suppressWarnings(as.numeric(var.sig)[1])
  var_gam_seed <- suppressWarnings(as.numeric(var.gam)[1])
  if (!is.finite(var_sig_seed) || var_sig_seed <= 0) var_sig_seed <- 1e-3
  if (!is.finite(var_gam_seed) || var_gam_seed <= 0) var_gam_seed <- 1e-3
  hess_seed <- diag(c(var_sig_seed, var_gam_seed), nrow = 2L)
  prior_gamma_log <- suppressWarnings(crch::dtt(
    gam, location = prior_g[1], scale = prior_g[2], df = prior_g[3], left = L, right = U, log = TRUE
  ))
  if (!is.finite(prior_gamma_log)) prior_gamma_log <- -Inf
  prior_sigma_log <- suppressWarnings(nimble::dinvgamma(sig, shape = prior_s[1], scale = prior_s[2], log = TRUE))
  if (!is.finite(prior_sigma_log)) prior_sigma_log <- -Inf
  list(
    E.sigma = sig,
    E.inv.sigma = 1 / sig,
    E.gam = gam,
    E.c2.invb.absgam2.sigma = c^2 * sig * abs(gam)^2 / b,
    E.c.invb.absgam = c * abs(gam) / b,
    E.c.a.invb.absgam = c * abs(gam) * a / b,
    E.a2.invb.inv.sigma = a^2 / (sig * b),
    E.invb.inv.sigma = 1 / (sig * b),
    E.a.invb.inv.sigma = a / (sig * b),
    Hess.LD = hess_seed,
    E.log.sig.b = log(sig * b),
    E.log.sig = log(sig),
    E.prior.sig.gam = prior_gamma_log + prior_sigma_log,
    E.theta = c(theta_s_val, theta_g_val),
    entrop = 0,
    guard_triggered = isTRUE(guard),
    guard_message = guard_msg
  )
}

build_guard_fallback <- function(theta_s_val, theta_g_val, guard_msg = "") {
  build_mode_result(theta_s_val, theta_g_val, guard = TRUE, guard_msg = guard_msg)
}

theta_sigma_lower <- as.numeric(DISC_GAMSIG_THETA_SIGMA_LOWER)
theta_sigma_upper <- as.numeric(DISC_GAMSIG_THETA_SIGMA_UPPER)
theta_gamma_lower <- as.numeric(DISC_GAMSIG_THETA_GAMMA_LOWER)
theta_gamma_upper <- as.numeric(DISC_GAMSIG_THETA_GAMMA_UPPER)

clip_theta_pair <- function(theta_s_val, theta_g_val) {
  c(
    pmin(pmax(theta_s_val, theta_sigma_lower), theta_sigma_upper),
    pmin(pmax(theta_g_val, theta_gamma_lower), theta_gamma_upper)
  )
}

use_median_sigma_only_fallback <- (!isTRUE(DISC_W_AL_MODE) &&
  isTRUE(DISC_GAMSIG_MEDIAN_SIGMA_ONLY_FALLBACK_ENABLED) &&
  is.finite(p0) &&
  abs(as.numeric(p0) - 0.5) <= as.numeric(DISC_GAMSIG_MEDIAN_SIGMA_ONLY_FALLBACK_TOL))
use_median_step_damping <- (!isTRUE(DISC_W_AL_MODE) &&
  isTRUE(DISC_GAMSIG_MEDIAN_STEP_DAMPING_ENABLED) &&
  is.finite(p0) &&
  abs(as.numeric(p0) - 0.5) <= as.numeric(DISC_GAMSIG_MEDIAN_SIGMA_ONLY_FALLBACK_TOL))

apply_median_step_damping <- function(theta_pair, reason_label) {
  if (!use_median_step_damping) {
    return(theta_pair)
  }
  theta_pair <- clip_theta_pair(theta_pair[[1L]], theta_pair[[2L]])
  cand_sigma <- exp(theta_pair[[1L]])
  cand_pi <- plogis(theta_pair[[2L]])
  cand_pi <- pmin(pmax(cand_pi, 1e-12), 1 - 1e-12)
  cand_gamma <- L + (U - L) * cand_pi
  gamma_step <- abs(cand_gamma - g_seed)
  sigma_step <- abs(log(cand_sigma) - log(s_seed))
  gamma_cap <- as.numeric(DISC_GAMSIG_MEDIAN_MAX_ABS_GAMMA_STEP)
  sigma_cap <- as.numeric(DISC_GAMSIG_MEDIAN_MAX_ABS_LOG_SIGMA_STEP)
  damped_log_sigma <- log(cand_sigma)
  if (is.finite(sigma_cap) && sigma_cap > 0) {
    damped_log_sigma <- pmin(pmax(damped_log_sigma, log(s_seed) - sigma_cap), log(s_seed) + sigma_cap)
  }
  damped_gamma <- cand_gamma
  if (is.finite(gamma_cap) && gamma_cap > 0) {
    damped_gamma <- pmin(pmax(cand_gamma, g_seed - gamma_cap), g_seed + gamma_cap)
  }
  damped_gamma <- pmin(pmax(damped_gamma, L + 1e-12), U - 1e-12)
  if (isTRUE(DISC_W_AL_MODE)) {
    damped_gamma <- 0
  }
  damped_theta_s <- damped_log_sigma
  damped_pi <- (damped_gamma - L) / (U - L)
  damped_pi <- pmin(pmax(damped_pi, 1e-12), 1 - 1e-12)
  damped_theta_g <- qlogis(damped_pi)
  damped_theta <- clip_theta_pair(damped_theta_s, damped_theta_g)
  damped_sigma <- exp(damped_theta[[1L]])
  damped_pi <- plogis(damped_theta[[2L]])
  damped_pi <- pmin(pmax(damped_pi, 1e-12), 1 - 1e-12)
  damped_gamma <- L + (U - L) * damped_pi
  gamma_step_new <- abs(damped_gamma - g_seed)
  sigma_step_new <- abs(log(damped_sigma) - log(s_seed))
  if (abs(gamma_step_new - gamma_step) < 1e-12 && abs(sigma_step_new - sigma_step) < 1e-12) {
    return(theta_pair)
  }
  log_stabilization_event(sprintf(
    "median step damping at p0=%s context=%s reason=%s gamma_step=%s->%s sigma_log_step=%s->%s",
    as.character(p0),
    context_label,
    reason_label,
    format(gamma_step, digits = 6),
    format(gamma_step_new, digits = 6),
    format(sigma_step, digits = 6),
    format(sigma_step_new, digits = 6)
  ))
  damped_theta
}

if(!Climate_Center){
  dq_transf <- function(theta_s,theta_g){
      sig <- exp(theta_s)
      pi <- plogis(theta_g)
      # Keep gamma strictly inside (L,U) to avoid evaluating A/B/C at the boundary.
      pi <- pmin(pmax(pi, 1e-12), 1 - 1e-12)
      gam <- L + (U - L) * pi
      a = A.fn(p0,gam); b = B.fn(p0,gam); c = C.fn(p0,gam); p.fn(p0,gam)
      if (isTRUE(DISC_GAMSIG_OBJECTIVE_GUARD_ENABLED)) {
        if (!is.finite(sig) || sig <= 0 || !is.finite(gam) || !is.finite(b) || b <= 0) {
          return(-Inf)
        }
      }

      # Prior
      prior_gamma_dens <- PriorGammaDens(gam, prior_g)
      if (isTRUE(DISC_GAMSIG_OBJECTIVE_GUARD_ENABLED) &&
          (!is.finite(prior_gamma_dens) || prior_gamma_dens <= 0)) {
        return(-Inf)
      }
      yy <- log(prior_gamma_dens) - (prior_s[1] + 1) * log(sig) - prior_s[2]/sig

      # Likelihood
      yy <- yy - (1.5*nn)*log(sig) - (0.5*nn)*log(b)-sum(uts)/sig 
      yy <- yy - 0.5*sum( inv.uts*(y^2-2*y*exps+exps2)/sig
                      - (y-exps)*2*(inv.uts*c*abs(gam)*sts + a/sig)
                      + sig*inv.uts*(c^2)*(abs(gam)^2)*sts2
                      + 2*c*abs(gam)*sts*a
                      + (uts*a^2)/sig )/b
      
      # Jacobian (u=log sigma, gamma=L+(U-L)*logistic(xi))
      yy <- yy + theta_s + log(U - L) + log(pi) + log1p(-pi)
      if (isTRUE(DISC_GAMSIG_OBJECTIVE_GUARD_ENABLED) && !is.finite(yy)) {
        return(-Inf)
      }
      return(yy)
  }
}else{

  ensembles_j <- matrix(c(as.matrix(ensembles_j)),ncol = 1)
  sts_f <-  matrix(c(as.matrix(sts_f)),ncol = 1)
  sts2_f <-  matrix(c(as.matrix(sts2_f)),ncol = 1)
  uts_f <-  matrix(c(as.matrix(uts_f)),ncol = 1)
  inv.uts_f <-  matrix(c(as.matrix(inv.uts_f)),ncol = 1)

  dq_transf <- function(theta_s,theta_g){
      sig <- exp(theta_s)
      pi <- plogis(theta_g)
      # Keep gamma strictly inside (L,U) to avoid evaluating A/B/C at the boundary.
      pi <- pmin(pmax(pi, 1e-12), 1 - 1e-12)
      gam <- L + (U - L) * pi
      a = A.fn(p0,gam); b = B.fn(p0,gam); c = C.fn(p0,gam);
      if (isTRUE(DISC_GAMSIG_OBJECTIVE_GUARD_ENABLED)) {
        if (!is.finite(sig) || sig <= 0 || !is.finite(gam) || !is.finite(b) || b <= 0) {
          return(-Inf)
        }
      }

      # Prior
      prior_gamma_dens <- PriorGammaDens(gam, prior_g)
      if (isTRUE(DISC_GAMSIG_OBJECTIVE_GUARD_ENABLED) &&
          (!is.finite(prior_gamma_dens) || prior_gamma_dens <= 0)) {
        return(-Inf)
      }
      yy <- log(prior_gamma_dens) - (prior_s[1] + 1) * log(sig) - prior_s[2]/sig

      # Likelihood
      yy <- yy - 1.5*(nn+k_forecast*num_mem_j)*log(sig) - (0.5*(nn+k_forecast*num_mem_j))*log(b)-(sum(uts)+sum(uts_f))/sig 
      # Before Forecast
      yy <- yy - 0.5*sum( inv.uts*(y^2-2*y*exps[1:nn]+exps2[1:nn])/sig
                      - (y-exps[1:nn])*2*(inv.uts*c*abs(gam)*sts + a/sig)
                      + sig*inv.uts*(c^2)*(abs(gam)^2)*sts2
                      + 2*c*abs(gam)*sts*a
                      + (uts*a^2)/sig )/b
      # After Forecast
      yy <- yy - 0.5*sum( inv.uts_f*(ensembles_j^2-2*ensembles_j*exps[(nn+1):(nn+k_forecast)]+exps2[(nn+1):(nn+k_forecast)])/sig
                      - (ensembles_j-exps[(nn+1):(nn+k_forecast)])*2*(inv.uts_f*c*abs(gam)*sts_f + a/sig)
                      + sig*inv.uts_f*(c^2)*(abs(gam)^2)*sts2_f
                      + 2*c*abs(gam)*sts_f*a
                      + (uts_f*a^2)/sig )/b
      # Jacobian (u=log sigma, gamma=L+(U-L)*logistic(xi))
      yy <- yy + theta_s + log(U - L) + log(pi) + log1p(-pi)
      if (isTRUE(DISC_GAMSIG_OBJECTIVE_GUARD_ENABLED) && !is.finite(yy)) {
        return(-Inf)
      }
      return(yy)
  }
}

  theta_s_init <- log(s_seed)
  pi_init <- (g_seed - L) / (U - L)
  pi_init <- pmin(pmax(pi_init, 1e-12), 1 - 1e-12)
  theta_g_init <- qlogis(pi_init)
  initial_values <- clip_theta_pair(theta_s_init, theta_g_init)

  run_sigma_only_fallback <- function(reason_label, theta_g_anchor = theta_g_init) {
    if (!use_median_sigma_only_fallback) {
      return(NULL)
    }
    theta_pair <- clip_theta_pair(theta_s_init, theta_g_anchor)
    theta_g_fixed <- theta_pair[2]
    sigma_obj <- function(theta_s_val) {
      yy <- dq_transf(theta_s_val, theta_g_fixed)
      if (!is.finite(yy)) {
        if (isTRUE(DISC_GAMSIG_OBJECTIVE_GUARD_ENABLED)) {
          return(DISC_GAMSIG_OBJECTIVE_GUARD_PENALTY)
        }
        return(Inf)
      }
      -yy
    }
    sigma_opt <- tryCatch(
      stats::optimize(sigma_obj, interval = c(theta_sigma_lower, theta_sigma_upper)),
      error = function(e) e
    )
    if (inherits(sigma_opt, "error") || !is.finite(sigma_opt$minimum)) {
      msg <- if (inherits(sigma_opt, "error")) {
        sprintf("sigma-only fallback failed after %s: %s", reason_label, conditionMessage(sigma_opt))
      } else {
        sprintf("sigma-only fallback failed after %s: invalid optimum", reason_label)
      }
      log_stabilization_event(msg)
      return(NULL)
    }
    log_stabilization_event(sprintf(
      "sigma-only fallback accepted at p0=%s context=%s after %s with theta_s=%s theta_g=%s",
      as.character(p0),
      context_label,
      reason_label,
      format(sigma_opt$minimum, digits = 16),
      format(theta_g_fixed, digits = 16)
    ))
    build_mode_result(sigma_opt$minimum, theta_g_fixed, guard = FALSE, guard_msg = reason_label)
  }

  build_ld_covariance <- function(log_hessian, label) {
    if (is.null(log_hessian) || any(!is.finite(log_hessian))) {
      return(NULL)
    }
    precision <- -(0.5 * (log_hessian + t(log_hessian)))
    if (any(!is.finite(precision))) {
      return(NULL)
    }
    ridge <- as.numeric(DISC_GAMSIG_HESSIAN_RIDGE_INIT)
    max_tries <- as.integer(DISC_GAMSIG_HESSIAN_RIDGE_MAX_TRIES)
    mult <- as.numeric(DISC_GAMSIG_HESSIAN_RIDGE_MULTIPLIER)
    if (!is.finite(mult) || mult <= 1) mult <- 10
    for (attempt in seq_len(max_tries + 1L)) {
      precision_reg <- precision + diag(ridge, nrow = nrow(precision))
      cov_candidate <- tryCatch(solve(precision_reg), error = function(e) NULL)
      if (!is.null(cov_candidate) && all(is.finite(cov_candidate))) {
        if (ridge > as.numeric(DISC_GAMSIG_HESSIAN_RIDGE_INIT)) {
          log_stabilization_event(sprintf(
            "regularized Hessian accepted at p0=%s context=%s label=%s ridge=%s",
            as.character(p0),
            context_label,
            label,
            format(ridge, scientific = TRUE, digits = 6)
          ))
        }
        return(cov_candidate)
      }
      ridge <- ridge * mult
    }
    NULL
  }

  if (isTRUE(DISC_W_AL_MODE)) {
    theta_g_fixed <- qlogis(pmin(pmax((0 - L) / (U - L), 1e-12), 1 - 1e-12))
    sigma_obj <- function(theta_s_val) {
      yy <- dq_transf(theta_s_val, theta_g_fixed)
      if (!is.finite(yy)) {
        if (isTRUE(DISC_GAMSIG_OBJECTIVE_GUARD_ENABLED)) {
          return(DISC_GAMSIG_OBJECTIVE_GUARD_PENALTY)
        }
        return(Inf)
      }
      -yy
    }
    sigma_opt <- tryCatch(
      stats::optimize(sigma_obj, interval = log(c(1e-5, 1e3))),
      error = function(e) e
    )
    if (inherits(sigma_opt, "error") || !is.finite(sigma_opt$minimum)) {
      msg <- if (inherits(sigma_opt, "error")) conditionMessage(sigma_opt) else "invalid sigma optimum"
      return(build_guard_fallback(theta_s_init, theta_g_fixed, guard_msg = msg))
    }
    return(build_mode_result(sigma_opt$minimum, theta_g_fixed, guard = FALSE, guard_msg = ""))
  }

  # Optimization step
  guard_triggered <- FALSE
  guard_message <- ""
  guard_mode <- DISC_GAMSIG_OBJECTIVE_GUARD_MODE

  mark_guard_trigger <- function(msg) {
    guard_triggered <<- TRUE
    if (!nzchar(guard_message)) {
      guard_message <<- msg
    }
  }

  objective_neg <- function(x) {
    yy <- dq_transf(x[1], x[2])
    if (!isTRUE(DISC_GAMSIG_OBJECTIVE_GUARD_ENABLED)) {
      return(-yy)
    }
    if (!is.finite(yy)) {
      msg <- sprintf(
        "non-finite dq_transf at p0=%s context=%s theta_s=%s theta_g=%s",
        as.character(p0), context_label, format(x[1], digits = 16), format(x[2], digits = 16)
      )
      if (isTRUE(DISC_GAMSIG_OBJECTIVE_GUARD_FAIL_FAST)) {
        stop(msg, call. = FALSE)
      }
      log_guard_failure(msg)
      mark_guard_trigger(msg)
      return(DISC_GAMSIG_OBJECTIVE_GUARD_PENALTY)
    }
    neg <- -yy
    if (!is.finite(neg)) {
      msg <- sprintf(
        "non-finite negative objective at p0=%s context=%s theta_s=%s theta_g=%s",
        as.character(p0), context_label, format(x[1], digits = 16), format(x[2], digits = 16)
      )
      if (isTRUE(DISC_GAMSIG_OBJECTIVE_GUARD_FAIL_FAST)) {
        stop(msg, call. = FALSE)
      }
      log_guard_failure(msg)
      mark_guard_trigger(msg)
      return(DISC_GAMSIG_OBJECTIVE_GUARD_PENALTY)
    }
    neg
  }

  optim_results <- tryCatch(
    optim(
      par = initial_values,
      fn = objective_neg, # Maximizing by minimizing the negative
      method = "L-BFGS-B", # This method allows box constraints
      lower = c(theta_sigma_lower, theta_gamma_lower),
      upper = c(theta_sigma_upper, theta_gamma_upper),
      hessian = TRUE
    ),
    error = function(e) {
      msg <- sprintf(
        "optim failure at p0=%s context=%s: %s",
        as.character(p0), context_label, conditionMessage(e)
      )
      if (isTRUE(DISC_GAMSIG_OBJECTIVE_GUARD_FAIL_FAST)) {
        stop(msg, call. = FALSE)
      }
      log_guard_failure(msg)
      mark_guard_trigger(msg)
      NULL
    }
  )

  if (is.null(optim_results)) {
    sigma_only_result <- run_sigma_only_fallback("optim failure")
    if (!is.null(sigma_only_result)) {
      return(sigma_only_result)
    }
    return(build_guard_fallback(theta_s_init, theta_g_init, guard_msg = guard_message))
  }
  optim_results$par <- clip_theta_pair(optim_results$par[[1L]], optim_results$par[[2L]])
  optim_results$par <- apply_median_step_damping(optim_results$par, reason_label = "post-optim")
  opt_obj <- tryCatch(dq_transf(optim_results$par[[1L]], optim_results$par[[2L]]), error = function(e) NA_real_)
  if (!is.finite(opt_obj)) {
    msg <- sprintf(
      "non-finite optimum after guarded multivar optimization at p0=%s context=%s",
      as.character(p0), context_label
    )
    if (nzchar(guard_message)) {
      msg <- sprintf("%s | last_guard=%s", msg, guard_message)
    }
    log_guard_failure(msg)
    sigma_only_result <- run_sigma_only_fallback("non-finite optimum")
    if (!is.null(sigma_only_result)) {
      return(sigma_only_result)
    }
    return(build_guard_fallback(theta_s_init, theta_g_init, guard_msg = msg))
  }

  log_hessian_at_optimal <- tryCatch(
    numDeriv::hessian(
      func = function(theta_vec) dq_transf(theta_vec[[1L]], theta_vec[[2L]]),
      x = optim_results$par
    ),
    error = function(e) NULL
  )
  if (is.null(log_hessian_at_optimal) || any(!is.finite(log_hessian_at_optimal))) {
    log_hessian_at_optimal <- -optim_results$hessian
  }
  LD_S <- build_ld_covariance(log_hessian_at_optimal, label = "log_hessian")
  if (is.null(LD_S)) {
    msg <- sprintf(
      "non-invertible Hessian at p0=%s context=%s",
      as.character(p0), context_label
    )
    if (isTRUE(DISC_GAMSIG_OBJECTIVE_GUARD_FAIL_FAST)) {
      stop(msg, call. = FALSE)
    }
    log_guard_failure(msg)
    sigma_only_result <- run_sigma_only_fallback("non-invertible Hessian")
    if (!is.null(sigma_only_result)) {
      return(sigma_only_result)
    }
    return(build_guard_fallback(theta_s_init, theta_g_init, guard_msg = msg))
  }

  LD_mu <- optim_results$par

  Expected_f <- function(f, theta_s, theta_g){
      x <- hessian(func = f, x = LD_mu)%*%LD_S
      e <- f(LD_mu) + 0.5*sum(diag(x))
    return(e)
  }

  f.log.sig.b <- function(theta){
    pi <- plogis(theta[2]); pi <- pmin(pmax(pi, 1e-12), 1 - 1e-12)
    sig = exp(theta[1]); gam = L + (U - L) * pi
    a = A.fn(p0,gam); b = B.fn(p0,gam); c = C.fn(p0,gam);
    yy <- log(sig*b)
    return(yy)
  }

  f.log.sig <- function(theta){
    pi <- plogis(theta[2]); pi <- pmin(pmax(pi, 1e-12), 1 - 1e-12)
    sig = exp(theta[1]); gam = L + (U - L) * pi
    a = A.fn(p0,gam); b = B.fn(p0,gam); c = C.fn(p0,gam);
    yy <- log(sig)
    return(yy)
  }

  f.prior.sig.gam <- function(theta){
    pi <- plogis(theta[2]); pi <- pmin(pmax(pi, 1e-12), 1 - 1e-12)
    sig = exp(theta[1]); gam = L + (U - L) * pi
    a = A.fn(p0,gam); b = B.fn(p0,gam); c = C.fn(p0,gam);
    yy <- crch::dtt(gam, location = prior_g[1], scale = prior_g[2], df = prior_g[3], left = L, right = U, log = TRUE)
    yy <- yy + nimble::dinvgamma(sig, shape = prior_s[1], scale =  prior_s[2], log = TRUE)
    return(yy)
  }


  f.c2.s.abs.g2.inv.b <- function(theta){
    pi <- plogis(theta[2]); pi <- pmin(pmax(pi, 1e-12), 1 - 1e-12)
    sig = exp(theta[1]); gam = L + (U - L) * pi
    a = A.fn(p0,gam); b = B.fn(p0,gam); c = C.fn(p0,gam);
    yy <- c^2*sig*abs(gam)^2/b
    return(yy)
  }

  f.inv.sig <- function(theta){
    sig = exp(theta[1])
    yy <- 1/sig
    return(yy)
  }

  f.c.abs.g.inv.b <- function(theta){
    pi <- plogis(theta[2]); pi <- pmin(pmax(pi, 1e-12), 1 - 1e-12)
    gam = L + (U - L) * pi
    b = B.fn(p0,gam); c = C.fn(p0,gam);
    yy <- c*abs(gam)/b
    return(yy)
  }

  f.c.abs.g.a.inv.b <- function(theta){
    pi <- plogis(theta[2]); pi <- pmin(pmax(pi, 1e-12), 1 - 1e-12)
    sig = exp(theta[1]); gam = L + (U - L) * pi
    a = A.fn(p0,gam); b = B.fn(p0,gam); c = C.fn(p0,gam);
    yy <- c*abs(gam)*a/b
    return(yy)
  }

  f.inv.s.inv.b <- function(theta){
    pi <- plogis(theta[2]); pi <- pmin(pmax(pi, 1e-12), 1 - 1e-12)
    sig = exp(theta[1]); gam = L + (U - L) * pi
    a = A.fn(p0,gam); b = B.fn(p0,gam); c = C.fn(p0,gam);
    yy <- 1/sig/b
    return(yy)
  }

  f.a.inv.s.inv.b <- function(theta){
    pi <- plogis(theta[2]); pi <- pmin(pmax(pi, 1e-12), 1 - 1e-12)
    sig = exp(theta[1]); gam = L + (U - L) * pi
    a = A.fn(p0,gam); b = B.fn(p0,gam); c = C.fn(p0,gam);
    yy <- a/sig/b
    return(yy)
  }

  f.a2.inv.s.inv.b <- function(theta){
    pi <- plogis(theta[2]); pi <- pmin(pmax(pi, 1e-12), 1 - 1e-12)
    sig = exp(theta[1]); gam = L + (U - L) * pi
    a = A.fn(p0,gam); b = B.fn(p0,gam); c = C.fn(p0,gam);
    yy <- a^2/sig/b
    return(yy)
  }

  f.sig <- function(theta){
    sig = exp(theta[1]); 
    yy <- sig
    return(yy)
  }

  f.gam <- function(theta){
    pi <- plogis(theta[2]); pi <- pmin(pmax(pi, 1e-12), 1 - 1e-12)
    gam = L + (U - L) * pi
    yy <- gam
    return(yy)
  }

  #############################################################################################################################################
  #############################################################################################################################################

  E.sig = Expected_f(f.sig, LD_mu[1], LD_mu[2]);
  E.gam = Expected_f(f.gam, LD_mu[1], LD_mu[2]);


  E.inv.sigma = Expected_f(f.inv.sig, LD_mu[1], LD_mu[2])
  E.c2.invb.absgam2.sigma = Expected_f(f.c2.s.abs.g2.inv.b, LD_mu[1], LD_mu[2])
  E.c.invb.absgam = Expected_f(f.c.abs.g.inv.b, LD_mu[1], LD_mu[2])
  E.c.a.invb.absgam = Expected_f(f.c.abs.g.a.inv.b, LD_mu[1], LD_mu[2])
  E.a2.invb.inv.sigma = Expected_f(f.a2.inv.s.inv.b, LD_mu[1], LD_mu[2])
  E.invb.inv.sigma = Expected_f(f.inv.s.inv.b, LD_mu[1], LD_mu[2])
  E.a.invb.inv.sigma = Expected_f(f.a.inv.s.inv.b, LD_mu[1], LD_mu[2])
  E.log.sig.b = Expected_f(f.log.sig.b, LD_mu[1], LD_mu[2])
  E.log.sig = Expected_f(f.log.sig, LD_mu[1], LD_mu[2])
  E.prior.sig.gam = Expected_f(f.prior.sig.gam, LD_mu[1], LD_mu[2])
  f.log_jac <- function(theta){
    pi <- plogis(theta[2]); pi <- pmin(pmax(pi, 1e-12), 1 - 1e-12)
    yy <- theta[1] + log(U - L) + log(pi) + log1p(-pi)
    return(yy)
  }
  E.log.jac = Expected_f(f.log_jac, LD_mu[1], LD_mu[2])

  entrop <- log(2*pi*exp(1)) + 0.5*determinant(as.matrix(LD_S), logarithm = TRUE)$modulus[1] + E.log.jac

  return(list(E.sigma=E.sig,E.inv.sigma=E.inv.sigma,E.gam=E.gam,
              E.c2.invb.absgam2.sigma = E.c2.invb.absgam2.sigma, E.c.invb.absgam = E.c.invb.absgam,
              E.c.a.invb.absgam = E.c.a.invb.absgam, E.a2.invb.inv.sigma = E.a2.invb.inv.sigma,
              E.invb.inv.sigma = E.invb.inv.sigma, E.a.invb.inv.sigma = E.a.invb.inv.sigma,
              Hess.LD = LD_S,
              E.log.sig.b=E.log.sig.b, 
              E.log.sig = E.log.sig, 
              E.prior.sig.gam= E.prior.sig.gam,
              E.theta = LD_mu,
              entrop = entrop,
              guard_triggered = FALSE,
              guard_message = ""))
}

########################
T_size <- c(TT, (TT+ranges))
########################

#############################################################################################################################################
#############################################################################################################################################

# Build horizon-segment matrices in deterministic descending-range order.
disc_w_concat_horizon_segments <- function(mat_list, label) {
  if (!is.list(mat_list) || length(mat_list) < 1L) {
    stop(sprintf("%s must be a non-empty list", label), call. = FALSE)
  }
  mats <- lapply(seq_along(mat_list), function(i) {
    m <- as.matrix(mat_list[[i]])
    storage.mode(m) <- "double"
    if (!is.matrix(m) || nrow(m) < 1L || ncol(m) < 1L) {
      stop(sprintf("%s[[%d]] must be a non-empty numeric matrix", label, as.integer(i)), call. = FALSE)
    }
    if (any(!is.finite(m))) {
      stop(sprintf("%s[[%d]] contains non-finite values", label, as.integer(i)), call. = FALSE)
    }
    m
  })
  rows <- vapply(mats, nrow, integer(1))
  if (any(diff(rows) > 0L)) {
    stop(sprintf("%s row counts must be non-increasing; got [%s]", label, paste(rows, collapse = ",")), call. = FALSE)
  }
  out <- vector("list", length(mats))
  out_i <- 1L
  for (idx in seq(from = length(mats), to = 1L, by = -1L)) {
    upper <- rows[idx]
    lower <- if (idx < length(mats)) rows[idx + 1L] else 0L
    if (upper <= lower) {
      stop(sprintf("%s has invalid segment bounds at idx=%d (lower=%d upper=%d)", label, as.integer(idx), as.integer(lower), as.integer(upper)), call. = FALSE)
    }
    segment_rows <- (lower + 1L):upper
    pieces <- lapply(seq_len(idx), function(i) mats[[i]][segment_rows, , drop = FALSE])
    out[[out_i]] <- do.call(cbind, pieces)
    out_i <- out_i + 1L
  }
  out
}
disc_w_assert_shape <- function(x, dims, label, allow_array = FALSE) {
  actual <- dim(x)
  if (is.null(actual)) {
    stop(sprintf("%s has no dim attribute", label), call. = FALSE)
  }
  if (!allow_array && length(actual) != 2L) {
    stop(sprintf("%s must be 2D; got dim length=%d", label, as.integer(length(actual))), call. = FALSE)
  }
  if (length(actual) != length(dims) || any(actual != dims)) {
    stop(sprintf(
      "%s shape mismatch: expected (%s), got (%s)",
      label,
      paste(dims, collapse = "x"),
      paste(actual, collapse = "x")
    ), call. = FALSE)
  }
}
disc_w_validate_cpp_contract <- function(
  GG,
  m0,
  C0,
  FF,
  y,
  ex.df.mat,
  ex.df.mat.k,
  GG_list,
  FF_list,
  FFF_forecast,
  QQQ_forecast,
  ensembles_forecast,
  cur.covs_list,
  num_mem,
  ranges,
  p,
  J,
  ppx,
  TT_sub,
  context_label = ""
) {
  ranges_i <- suppressWarnings(as.integer(ranges))
  num_mem_i <- suppressWarnings(as.integer(num_mem))
  if (length(ranges_i) != J || any(!is.finite(ranges_i)) || any(ranges_i <= 0L)) {
    stop(sprintf("contract %s: invalid ranges [%s]", context_label, paste(ranges, collapse = ",")), call. = FALSE)
  }
  if (length(num_mem_i) != J || any(!is.finite(num_mem_i)) || any(num_mem_i <= 0L)) {
    stop(sprintf("contract %s: invalid num_mem [%s]", context_label, paste(num_mem, collapse = ",")), call. = FALSE)
  }
  if (any(diff(ranges_i) > 0L)) {
    stop(sprintf("contract %s: ranges must be non-increasing, got [%s]", context_label, paste(ranges_i, collapse = ",")), call. = FALSE)
  }
  total_state <- as.integer(p * (J + 1) + ppx)
  disc_w_assert_shape(GG, c(total_state, total_state, as.integer(TT_sub)), sprintf("GG (%s)", context_label), allow_array = TRUE)
  disc_w_assert_shape(C0, c(total_state, total_state), sprintf("C0 (%s)", context_label))
  if (length(as.numeric(m0)) != total_state) {
    stop(sprintf("contract %s: m0 length mismatch expected=%d got=%d", context_label, total_state, as.integer(length(m0))), call. = FALSE)
  }
  disc_w_assert_shape(FF, c(total_state, as.integer(J + 1), as.integer(TT_sub)), sprintf("FF (%s)", context_label), allow_array = TRUE)
  disc_w_assert_shape(y, c(as.integer(J + 1), as.integer(TT_sub)), sprintf("y (%s)", context_label))
  disc_w_assert_shape(ex.df.mat, c(total_state, total_state), sprintf("ex.df.mat (%s)", context_label))
  disc_w_assert_shape(ex.df.mat.k, c(total_state, total_state), sprintf("ex.df.mat.k (%s)", context_label))
  if (length(GG_list) != J || length(FF_list) != J || length(FFF_forecast) != J ||
      length(QQQ_forecast) != J || length(ensembles_forecast) != J || length(cur.covs_list) != J) {
    stop(sprintf("contract %s: list-length mismatch in ensemble payloads", context_label), call. = FALSE)
  }
  ranges_per_i <- if (J > 1L) {
    ranges_i - c(ranges_i[2:J], 0L)
  } else {
    ranges_i
  }
  horizon_i <- rev(ranges_per_i)
  for (seg in seq_len(J)) {
    expected_state <- as.integer(p * (J - seg + 2L))
    expected_series <- as.integer(J - seg + 1L)
    expected_h <- as.integer(horizon_i[seg])
    expected_obs <- as.integer(sum(num_mem_i[seq_len(expected_series)]))
    GG_seg <- as.matrix(GG_list[[seg]])
    FF_seg <- as.matrix(FF_list[[seg]])
    FFF_seg <- as.matrix(FFF_forecast[[seg]])
    ens_seg <- as.matrix(ensembles_forecast[[seg]])
    QQQ_seg <- as.array(QQQ_forecast[[seg]])
    cov_seg <- as.array(cur.covs_list[[seg]])
    disc_w_assert_shape(GG_seg, c(expected_state, expected_state), sprintf("GG_list[[%d]] (%s)", as.integer(seg), context_label))
    disc_w_assert_shape(FF_seg, c(expected_state, expected_series), sprintf("FF_list[[%d]] (%s)", as.integer(seg), context_label))
    disc_w_assert_shape(FFF_seg, c(expected_obs, expected_h), sprintf("FFF_forecast[[%d]] (%s)", as.integer(seg), context_label))
    disc_w_assert_shape(ens_seg, c(expected_obs, expected_h), sprintf("ensembles_forecast[[%d]] (%s)", as.integer(seg), context_label))
    disc_w_assert_shape(QQQ_seg, c(expected_obs, expected_obs, expected_h), sprintf("QQQ_forecast[[%d]] (%s)", as.integer(seg), context_label), allow_array = TRUE)
    disc_w_assert_shape(cov_seg, c(expected_state, expected_state, expected_h), sprintf("cur.covs_list[[%d]] (%s)", as.integer(seg), context_label), allow_array = TRUE)
    if (any(!is.finite(GG_seg)) || any(!is.finite(FF_seg)) || any(!is.finite(FFF_seg)) ||
        any(!is.finite(ens_seg)) || any(!is.finite(QQQ_seg)) || any(!is.finite(cov_seg))) {
      stop(sprintf("contract %s: non-finite values in ensemble payload seg=%d", context_label, as.integer(seg)), call. = FALSE)
    }
  }
  invisible(TRUE)
}

ensembles_forecast <- disc_w_concat_horizon_segments(ensembles, "ensembles")
ensembles_forecast <- lapply(ensembles_forecast, t)
#############################################################################################################################################
#############################################################################################################################################


dM <- 1 #Fix to one?
Ones <- matrix(1, dim(model$GG)[1], dim(model$GG)[1])
Ones_ens <- matrix(1, dim(GG_list[[1]])[1], dim(GG_list[[1]])[1])
########################
C0 <- as.matrix(model$C0)
m0 <- model$m0
ex.df.mat <- as.matrix(ex.df.mat)
ex.df.mat.k <- as.matrix(ex.df.mat.k)
########################
crit_ELBO <- 0
ELBO <- 0
seq.elbo = ELBO
iter = 0
FLAG = TRUE

y <- Y

crit_ELBO <- 0
ELBO <- 0
seq.elbo = ELBO
iter = 0
FLAG = TRUE
tol1 <- 1e-3
conv.check <- 0
required_iter_floor <- suppressWarnings(as.integer(max(
  DISC_GAMSIG_MIN_TOTAL_ITERS,
  DISC_GAMSIG_FREEZE_ITERS + DISC_GAMSIG_MIN_UPDATE_ITERS
)))
if (!is.finite(required_iter_floor) || required_iter_floor < 1L) {
  required_iter_floor <- 1L
}
max_iter <- suppressWarnings(as.integer(max(DISC_GAMSIG_MAX_ITER, required_iter_floor)))
if (!is.finite(max_iter) || max_iter < 1L) {
  max_iter <- 100L
}
fast <- 0
gamsig_update_iters <- 0L
prev_state_norm_sq <- NA_real_
prev_sigma_exp <- NA_real_
prev_gamma_exp <- NA_real_
crit_state_norm_sq <- Inf
crit_sigma_exp <- Inf
crit_gamma_exp <- Inf
fmt_iter_num <- function(x, digits = 8L) {
  xx <- suppressWarnings(as.numeric(x))
  if (length(xx) < 1L) {
    return("NA")
  }
  x_val <- xx[[1L]]
  if (!is.finite(x_val)) {
    return("NA")
  }
  format(signif(x_val, digits = as.integer(digits)), trim = TRUE, scientific = FALSE)
}
fmt_iter_vec <- function(x, digits = 8L) {
  xx <- as.numeric(x)
  if (length(xx) == 0L) {
    return("[]")
  }
  vals <- vapply(xx, function(v) {
    if (!is.finite(v)) {
      return("NA")
    }
    format(signif(as.numeric(v), digits = as.integer(digits)), trim = TRUE, scientific = FALSE)
  }, FUN.VALUE = character(1))
  paste0("[", paste(vals, collapse = ","), "]")
}

disc_w_symmetrize <- function(M) {
  0.5 * (M + t(M))
}

disc_w_force_spd <- function(M, label = "matrix", eps_base = 1e-10, max_tries = 7L) {
  M <- as.matrix(M)
  storage.mode(M) <- "double"
  if (!is.matrix(M) || nrow(M) < 1L || ncol(M) < 1L || nrow(M) != ncol(M)) {
    stop(sprintf("%s must be a non-empty square matrix", label), call. = FALSE)
  }
  if (any(!is.finite(M))) {
    M[!is.finite(M)] <- 0
  }
  S <- disc_w_symmetrize(M)
  n <- nrow(S)
  jitter_seq <- c(0, eps_base * (10 ^ (0:(max_tries - 1L))))
  for (jit in jitter_seq) {
    candidate <- S + diag(jit, n)
    chol_ok <- tryCatch(chol(candidate), error = function(e) NULL)
    if (!is.null(chol_ok)) {
      return(candidate)
    }
  }
  eig <- tryCatch(eigen(S, symmetric = TRUE), error = function(e) NULL)
  if (is.null(eig) || any(!is.finite(eig$values)) || any(!is.finite(eig$vectors))) {
    stop(sprintf("%s eigen decomposition failed during SPD projection", label), call. = FALSE)
  }
  eig_floor <- max(eps_base, 1e-8 * max(1, max(abs(eig$values), na.rm = TRUE)))
  vals <- pmax(eig$values, eig_floor)
  S_psd <- eig$vectors %*% (diag(vals, nrow = length(vals)) %*% t(eig$vectors))
  S_psd <- disc_w_symmetrize(S_psd)
  chol_ok <- tryCatch(chol(S_psd), error = function(e) NULL)
  if (is.null(chol_ok)) {
    S_psd <- S_psd + diag(eig_floor, n)
    chol_ok <- tryCatch(chol(S_psd), error = function(e) NULL)
    if (is.null(chol_ok)) {
      stop(sprintf("%s could not be stabilized to SPD", label), call. = FALSE)
    }
  }
  S_psd
}

disc_w_spd_inverse <- function(M, label = "matrix") {
  S <- disc_w_force_spd(M, label = label)
  chol2inv(chol(S))
}

  print(c(n.samp, 111))
  flush.console()
if(USE_PREV){
  if(p0==0.05){
    file_path <- "/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_variables_5_exAL_synth_DISC.RData"
    disc_w_load_rdata(file_path)
    new.uts.out = new.uts.out_5_exAL_synth_DISC
    new.sts.out = new.sts.out_5_exAL_synth_DISC
    new.uts.out_f = new.uts_ens.out_5_exAL_synth_DISC
    new.sts.out_f = new.sts_ens.out_5_exAL_synth_DISC
    new.gamsig.out = new.gamsig.out_5_exAL_synth_DISC
    new.theta.out = new.theta.out_5_exAL_synth_DISC
  }else if (p0==0.2) {
    file_path <- "/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_variables_20_exAL_synth_DISC.RData"
    disc_w_load_rdata(file_path)
    new.uts.out = new.uts.out_20_exAL_synth_DISC
    new.sts.out = new.sts.out_20_exAL_synth_DISC
    new.uts.out_f = new.uts_ens.out_20_exAL_synth_DISC
    new.sts.out_f = new.sts_ens.out_20_exAL_synth_DISC
    new.gamsig.out = new.gamsig.out_20_exAL_synth_DISC
    new.theta.out = new.theta.out_20_exAL_synth_DISC
  }else if (p0==0.35) {
    file_path <- "/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_variables_35_exAL_synth_DISC.RData"
    disc_w_load_rdata(file_path)
    new.uts.out = new.uts.out_35_exAL_synth_DISC
    new.sts.out = new.sts.out_35_exAL_synth_DISC
    new.uts.out_f = new.uts_ens.out_35_exAL_synth_DISC
    new.sts.out_f = new.sts_ens.out_35_exAL_synth_DISC
    new.gamsig.out = new.gamsig.out_35_exAL_synth_DISC
    new.theta.out = new.theta.out_35_exAL_synth_DISC
  }else if (p0==0.5) {
    file_path <- "/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_variables_50_exAL_synth_DISC.RData"
    disc_w_load_rdata(file_path)
    new.uts.out = new.uts.out_50_exAL_synth_DISC
    new.sts.out = new.sts.out_50_exAL_synth_DISC
    new.uts.out_f = new.uts_ens.out_50_exAL_synth_DISC
    new.sts.out_f = new.sts_ens.out_50_exAL_synth_DISC
    new.gamsig.out = new.gamsig.out_50_exAL_synth_DISC
    new.theta.out = new.theta.out_50_exAL_synth_DISC
  }else if (p0==0.65) {
    file_path <- "/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_variables_65_exAL_synth_DISC.RData"
    disc_w_load_rdata(file_path)
    new.uts.out = new.uts.out_65_exAL_synth_DISC
    new.sts.out = new.sts.out_65_exAL_synth_DISC
    new.uts.out_f = new.uts_ens.out_65_exAL_synth_DISC
    new.sts.out_f = new.sts_ens.out_65_exAL_synth_DISC
    new.gamsig.out = new.gamsig.out_65_exAL_synth_DISC
    new.theta.out = new.theta.out_65_exAL_synth_DISC
  }else if (p0==0.8) {
    file_path <- "/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_variables_80_exAL_synth_DISC.RData"
    disc_w_load_rdata(file_path)
    new.uts.out = new.uts.out_80_exAL_synth_DISC
    new.sts.out = new.sts.out_80_exAL_synth_DISC
    new.uts.out_f = new.uts_ens.out_80_exAL_synth_DISC
    new.sts.out_f = new.sts_ens.out_80_exAL_synth_DISC
    new.gamsig.out = new.gamsig.out_80_exAL_synth_DISC
    new.theta.out = new.theta.out_80_exAL_synth_DISC
  }else if (p0==0.95) {
    file_path <- "/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_variables_95_exAL_synth_DISC.RData"
    disc_w_load_rdata(file_path)
    new.uts.out = new.uts.out_95_exAL_synth_DISC
    new.sts.out = new.sts.out_95_exAL_synth_DISC
    new.uts.out_f = new.uts_ens.out_95_exAL_synth_DISC
    new.sts.out_f = new.sts_ens.out_95_exAL_synth_DISC
    new.gamsig.out = new.gamsig.out_95_exAL_synth_DISC
    new.theta.out = new.theta.out_95_exAL_synth_DISC
  }
  m0 <- new.theta.out$sm[,1]
  # C0 <- new.theta.out$sC[,,1]
}

# Precompute dimensions and replication counts
dim_theta <- p * ((J+1):2)
ranges_per <- ranges - c(ranges[2:J], 0)
r_vec <- rev(ranges_per)

# Hyperparams for prior
c_factor <- DISC_W_C_FACTOR
epsilon <- if (is.finite(DISC_W_FORECAST_COV_EPSILON)) DISC_W_FORECAST_COV_EPSILON else TT
nu <- dim_theta + 1 + epsilon 

# Preallocate the list of 3D arrays (diagonal matrices)
new.covs_list <- mapply(function(n, r) {
  replicate(r, diag(0.0001, n), simplify = "array")
}, n = dim_theta, r = r_vec, SIMPLIFY = FALSE)

# # Example: inspect the first covariance matrix of the first period
# print(covs_list[[2]][ , , 1])
seq.eigen <- min(abs(eigen(new.covs_list[[2]][,,ranges_per[1]])$values))
# FLAG <- FALSE

########################
tictoc::tic("run time")

   print(c(n.samp))
  flush.console()
########################

gamsig_dynamic_freeze_until_iter <- as.integer(DISC_GAMSIG_FREEZE_ITERS)
if (!is.finite(gamsig_dynamic_freeze_until_iter) || gamsig_dynamic_freeze_until_iter < 0L) {
  gamsig_dynamic_freeze_until_iter <- 0L
}
median_quantile_active <- (!isTRUE(DISC_W_AL_MODE) &&
  is.finite(p0) &&
  abs(as.numeric(p0) - 0.5) < 1e-8)
generic_state_controls_present <- (
  !is.na(DISC_GAMSIG_STATE_GUARD_ENABLED_OPT) ||
  is.finite(DISC_GAMSIG_STATE_NORM_MAX_RATIO_OPT) ||
  is.finite(DISC_GAMSIG_STATE_NORM_ABS_CAP_OPT) ||
  !is.na(DISC_GAMSIG_STATE_GUARD_REFREEZE_ITERS_OPT) ||
  !is.na(DISC_GAMSIG_STATE_HOLD_AFTER_GUARD_ITERS_OPT) ||
  is.finite(DISC_GAMSIG_STATE_BLEND_ALPHA_OPT) ||
  is.finite(DISC_GAMSIG_COV_BLEND_ALPHA_OPT)
)
state_guard_enabled <- if (!is.na(DISC_GAMSIG_STATE_GUARD_ENABLED_OPT)) {
  isTRUE(DISC_GAMSIG_STATE_GUARD_ENABLED_OPT)
} else {
  median_quantile_active && isTRUE(DISC_GAMSIG_MEDIAN_STATE_GUARD_ENABLED)
}
state_norm_max_ratio <- if (is.finite(DISC_GAMSIG_STATE_NORM_MAX_RATIO_OPT)) {
  as.numeric(DISC_GAMSIG_STATE_NORM_MAX_RATIO_OPT)
} else if (median_quantile_active) {
  as.numeric(DISC_GAMSIG_MEDIAN_STATE_NORM_MAX_RATIO)
} else {
  NA_real_
}
state_norm_abs_cap <- if (is.finite(DISC_GAMSIG_STATE_NORM_ABS_CAP_OPT)) {
  as.numeric(DISC_GAMSIG_STATE_NORM_ABS_CAP_OPT)
} else if (median_quantile_active) {
  as.numeric(DISC_GAMSIG_MEDIAN_STATE_NORM_ABS_CAP)
} else {
  NA_real_
}
state_guard_refreeze_iters <- if (!is.na(DISC_GAMSIG_STATE_GUARD_REFREEZE_ITERS_OPT)) {
  as.integer(DISC_GAMSIG_STATE_GUARD_REFREEZE_ITERS_OPT)
} else if (median_quantile_active) {
  as.integer(DISC_GAMSIG_MEDIAN_STATE_GUARD_REFREEZE_ITERS)
} else {
  as.integer(DISC_GAMSIG_GUARD_REFREEZE_ITERS)
}
state_hold_after_guard_iters <- if (!is.na(DISC_GAMSIG_STATE_HOLD_AFTER_GUARD_ITERS_OPT)) {
  as.integer(DISC_GAMSIG_STATE_HOLD_AFTER_GUARD_ITERS_OPT)
} else if (median_quantile_active) {
  as.integer(DISC_GAMSIG_MEDIAN_STATE_HOLD_AFTER_GUARD_ITERS)
} else {
  0L
}
state_blend_alpha <- if (is.finite(DISC_GAMSIG_STATE_BLEND_ALPHA_OPT)) {
  as.numeric(DISC_GAMSIG_STATE_BLEND_ALPHA_OPT)
} else if (median_quantile_active) {
  as.numeric(DISC_GAMSIG_MEDIAN_STATE_BLEND_ALPHA)
} else {
  NA_real_
}
cov_blend_alpha <- if (is.finite(DISC_GAMSIG_COV_BLEND_ALPHA_OPT)) {
  as.numeric(DISC_GAMSIG_COV_BLEND_ALPHA_OPT)
} else if (median_quantile_active) {
  as.numeric(DISC_GAMSIG_MEDIAN_COV_BLEND_ALPHA)
} else {
  NA_real_
}
state_control_scope <- if (generic_state_controls_present) {
  "generic"
} else if (median_quantile_active) {
  "median_alias"
} else {
  "inactive"
}
state_log_prefix <- if (generic_state_controls_present || !median_quantile_active) "state" else "median_state"
state_hold_until_iter <- 0L
state_guard_count <- 0L
last_state_guard_iter <- NA_integer_
last_state_guard_reason <- ""
if (isTRUE(DISC_GAMSIG_OBJECTIVE_GUARD_LOG_FAILURES)) {
  cat(sprintf(
    "[gamsig_policy] p0=%s freeze_target=%s warmup_freeze_iters=%d min_update_iters=%d min_total_iters=%d max_iter=%d elbo_tol=%g state_norm_sq_tol=%g sigma_exp_tol=%g gamma_exp_tol=%g guard_mode=%s guard_refreeze_iters=%d theta_sigma_bounds=[%g,%g] theta_gamma_bounds=[%g,%g] hessian_ridge_init=%g hessian_ridge_multiplier=%g hessian_ridge_max_tries=%d state_control_scope=%s state_guard=%s state_norm_max_ratio=%g state_norm_abs_cap=%g state_guard_refreeze_iters=%d state_hold_after_guard_iters=%d state_blend_alpha=%g cov_blend_alpha=%g median_sigma_only_fallback=%s median_sigma_only_fallback_tol=%g median_step_damping=%s median_max_abs_gamma_step=%g median_max_abs_log_sigma_step=%g\n",
    as.character(p0),
    DISC_GAMSIG_FREEZE_TARGET,
    as.integer(DISC_GAMSIG_FREEZE_ITERS),
    as.integer(DISC_GAMSIG_MIN_UPDATE_ITERS),
    as.integer(DISC_GAMSIG_MIN_TOTAL_ITERS),
    as.integer(max_iter),
    as.numeric(DISC_GAMSIG_ELBO_TOL),
    as.numeric(DISC_GAMSIG_STATE_NORM_TOL),
    as.numeric(DISC_GAMSIG_SIGMA_EXP_TOL),
    as.numeric(DISC_GAMSIG_GAMMA_EXP_TOL),
    DISC_GAMSIG_OBJECTIVE_GUARD_MODE,
    as.integer(DISC_GAMSIG_GUARD_REFREEZE_ITERS),
    as.numeric(DISC_GAMSIG_THETA_SIGMA_LOWER),
    as.numeric(DISC_GAMSIG_THETA_SIGMA_UPPER),
    as.numeric(DISC_GAMSIG_THETA_GAMMA_LOWER),
    as.numeric(DISC_GAMSIG_THETA_GAMMA_UPPER),
    as.numeric(DISC_GAMSIG_HESSIAN_RIDGE_INIT),
    as.numeric(DISC_GAMSIG_HESSIAN_RIDGE_MULTIPLIER),
    as.integer(DISC_GAMSIG_HESSIAN_RIDGE_MAX_TRIES),
    state_control_scope,
    ifelse(isTRUE(state_guard_enabled), "true", "false"),
    state_norm_max_ratio,
    state_norm_abs_cap,
    as.integer(state_guard_refreeze_iters),
    as.integer(state_hold_after_guard_iters),
    state_blend_alpha,
    cov_blend_alpha,
    ifelse(isTRUE(DISC_GAMSIG_MEDIAN_SIGMA_ONLY_FALLBACK_ENABLED), "true", "false"),
    as.numeric(DISC_GAMSIG_MEDIAN_SIGMA_ONLY_FALLBACK_TOL),
    ifelse(isTRUE(DISC_GAMSIG_MEDIAN_STEP_DAMPING_ENABLED), "true", "false"),
    as.numeric(DISC_GAMSIG_MEDIAN_MAX_ABS_GAMMA_STEP),
    as.numeric(DISC_GAMSIG_MEDIAN_MAX_ABS_LOG_SIGMA_STEP)
  ))
  flush.console()
}

disc_w_theta_payload_present <- function(theta_out) {
  is.list(theta_out) &&
    !is.null(theta_out$sm) &&
    length(theta_out$sm) > 0L &&
    !is.null(dim(theta_out$sm)) &&
    !is.null(theta_out$sC) &&
    length(theta_out$sC) > 0L &&
    !is.null(dim(theta_out$sC)) &&
    !is.null(theta_out$sm_ens) &&
    is.list(theta_out$sm_ens) &&
    length(theta_out$sm_ens) == J &&
    all(vapply(theta_out$sm_ens, function(x) !is.null(x) && length(x) > 0L, logical(1)))
}

disc_w_materialize_theta_payload <- function(theta_out, context_label = "theta_seed") {
  FFF_seed <- (new.gamsig.out$E.c.invb.absgam[,] * new.sts.out$E.sts + new.gamsig.out$E.a.invb.inv.sigma[,]/new.uts.out$E.inv.uts) / new.gamsig.out$E.invb.inv.sigma[,]
  QQQ_seed <- 1/(new.gamsig.out$E.invb.inv.sigma[,] * new.uts.out$E.inv.uts)
  if (J > 0) {
    QQQ_seed <- array(apply(QQQ_seed, 2, function(col) diag(col)), dim = c(J + 1, J + 1, TT_sub))
  } else {
    QQQ_seed <- array(QQQ_seed, dim = c(J + 1, J + 1, TT_sub))
  }

  FFF_list_seed <- vector("list", J)
  QQQ_list_seed <- vector("list", J)
  for (j in seq_len(J)) {
    FFF_list_seed[[j]] <- (new.gamsig.out$E.c.invb.absgam[j,] * new.sts.out_f$E.sts[[j]] +
      new.gamsig.out$E.a.invb.inv.sigma[j,] / new.uts.out_f$E.inv.uts[[j]]) /
      new.gamsig.out$E.invb.inv.sigma[j,]
    QQQ_list_seed[[j]] <- 1/(new.gamsig.out$E.invb.inv.sigma[j,] * new.uts.out_f$E.inv.uts[[j]])
  }

  result_F_seed <- disc_w_concat_horizon_segments(FFF_list_seed, sprintf("FFF_seed %s", context_label))
  FFF_forecast_seed <- lapply(result_F_seed, t)
  result_Q_seed <- disc_w_concat_horizon_segments(QQQ_list_seed, sprintf("QQQ_seed %s", context_label))
  QQQ_forecast_seed_vec <- lapply(result_Q_seed, t)
  QQQ_forecast_seed <- vector("list", J)
  for (j in seq_len(J)) {
    n_q <- dim(QQQ_forecast_seed_vec[[j]])[1]
    m_q <- dim(QQQ_forecast_seed_vec[[j]])[2]
    arr_q <- array(0, dim = c(n_q, n_q, m_q))
    for (k_q in seq_len(m_q)) {
      arr_q[, , k_q] <- diag(QQQ_forecast_seed_vec[[j]][, k_q])
    }
    QQQ_forecast_seed[[j]] <- arr_q
  }

  if (isTRUE(DISC_STRICT_CONTRACTS)) {
    disc_w_validate_cpp_contract(
      GG = GG,
      m0 = m0,
      C0 = C0,
      FF = FF,
      y = y,
      ex.df.mat = ex.df.mat,
      ex.df.mat.k = ex.df.mat.k,
      GG_list = GG_list,
      FF_list = FF_list,
      FFF_forecast = FFF_forecast_seed,
      QQQ_forecast = QQQ_forecast_seed,
      ensembles_forecast = ensembles_forecast,
      cur.covs_list = new.covs_list,
      num_mem = num_mem,
      ranges = ranges,
      p = p,
      J = J,
      ppx = ppx,
      TT_sub = TT_sub,
      context_label = sprintf("theta_seed %s", context_label)
    )
  }

  update.theta.seed <- DISC_update_theta_synth_cpp_W(
    GG, m0, C0,
    FFF_seed, QQQ_seed,
    FF, y, ex.df.mat, ex.df.mat.k, Ones,
    p, J, ppx, TT, k, dM,
    GG_list, FF_list,
    FFF_forecast_seed, QQQ_forecast_seed,
    DF.MAT, DF.MAT_k,
    ensembles_forecast, ranges, Ones_ens,
    sum(num_mem), num_mem, new.covs_list,
    epsilon
  )

  FF_t_seed <- aperm(FF, c(2, 1, 3))
  result_list_seed <- lapply(seq_len(ncol(update.theta.seed$sm)), function(slice_index) {
    FF_t_seed[, , slice_index] %*% update.theta.seed$sm[, slice_index]
  })
  result_array_seed <- array(unlist(result_list_seed), dim = c(J + 1, 1, ncol(update.theta.seed$sm)))
  result_array_seed <- aperm(result_array_seed, c(1, 3, 2))[, , 1]
  exps_seed <- result_array_seed

  result_list_var_seed <- lapply(seq_len(dim(FF)[3]), function(t_idx) {
    FF_slice <- FF[, , t_idx]
    t(FF_slice) %*% update.theta.seed$sC[, , t_idx] %*% FF_slice
  })
  vars_1_seed <- simplify2array(result_list_var_seed)
  vars_seed <- apply(vars_1_seed, 3, function(x) diag(x))
  exps2_seed <- exps_seed^2 + vars_seed

  materialized_seed <- disc_materialize_theta_cpp_payload(
    update.theta.seed,
    J = J,
    p = p,
    ppx = ppx,
    num_mem = num_mem,
    context_label = sprintf("%s materialized", context_label)
  )
  rs_seed <- 0
  for (j in seq_len(J)) {
    r_j_seed <- ncol(materialized_seed$sm_ens[[j]])
    rs_seed <- r_j_seed + rs_seed
    FF_synth_seed <- FF_list[[j]]
    exps_ens_seed <- t(FF_synth_seed) %*% materialized_seed$sm_ens[[j]]
    vars_ens_seed_arr <- simplify2array(lapply(seq_len(r_j_seed), function(t_idx) {
      t(FF_synth_seed) %*% materialized_seed$sC_ens[[j]][, , t_idx] %*% FF_synth_seed
    }))
    if (j == J) {
      vars_ens_seed <- vars_ens_seed_arr
    } else {
      vars_ens_seed <- apply(vars_ens_seed_arr, 3, function(x) diag(x))
    }
    exps2_ens_seed <- exps_ens_seed^2 + vars_ens_seed

    theta_out$exps[2:(J - j + 2), (TT + 1 + rs_seed - r_j_seed):(TT + rs_seed)] <- exps_ens_seed
    theta_out$exps2[2:(J - j + 2), (TT + 1 + rs_seed - r_j_seed):(TT + rs_seed)] <- exps2_ens_seed
    theta_out$sm_ens[[j]] <- materialized_seed$sm_ens[[j]]
    theta_out$sC_ens[[j]] <- materialized_seed$sC_ens[[j]]
    theta_out$fm_ens[[j]] <- materialized_seed$fm_ens[[j]]
    theta_out$fC_ens[[j]] <- materialized_seed$fC_ens[[j]]
    theta_out$standard_forecast_errors_ens[[j]] <- materialized_seed$standard_forecast_errors_ens[[j]]
  }

  theta_out$exps[, 1:TT] <- exps_seed
  theta_out$exps2[, 1:TT] <- exps2_seed
  theta_out$standard_forecast_errors <- update.theta.seed$standard_forecast_errors
  theta_out$sm <- update.theta.seed$sm
  theta_out$sC <- update.theta.seed$sC
  theta_out$fm <- update.theta.seed$fm
  theta_out$fC <- update.theta.seed$fC
  theta_out$elbo.part <- update.theta.seed$elbo.part
  theta_out$elbo.part_ens <- update.theta.seed$elbo.part_ens
  theta_out$W_T <- update.theta.seed$W_T

  if (isTRUE(DISC_GAMSIG_OBJECTIVE_GUARD_LOG_FAILURES)) {
    cat(sprintf(
      "[theta_seed] p0=%s context=%s sm_dim=%s sC_dim=%s\n",
      as.character(p0),
      context_label,
      paste(dim(theta_out$sm), collapse = "x"),
      paste(dim(theta_out$sC), collapse = "x")
    ))
    flush.console()
  }

  theta_out
}

if (identical(DISC_GAMSIG_FREEZE_TARGET, "states")) {
  theta_seed_needed <- !disc_w_theta_payload_present(new.theta.out)
  if (isTRUE(DISC_GAMSIG_OBJECTIVE_GUARD_LOG_FAILURES)) {
    cat(sprintf(
      "[theta_seed_check] p0=%s needed=%s before_sm=%s before_sC=%s\n",
      as.character(p0),
      ifelse(theta_seed_needed, "true", "false"),
      ifelse(is.null(new.theta.out$sm), "NULL", paste(dim(new.theta.out$sm), collapse = "x")),
      ifelse(is.null(new.theta.out$sC), "NULL", paste(dim(new.theta.out$sC), collapse = "x"))
    ))
    flush.console()
  }
  if (theta_seed_needed) {
    new.theta.out <- disc_w_materialize_theta_payload(
      new.theta.out,
      context_label = "initial_state_freeze_seed"
    )
  }
  theta_seed_ready <- disc_w_theta_payload_present(new.theta.out)
  if (isTRUE(DISC_GAMSIG_OBJECTIVE_GUARD_LOG_FAILURES)) {
    cat(sprintf(
      "[theta_seed_check] p0=%s ready=%s after_sm=%s after_sC=%s\n",
      as.character(p0),
      ifelse(theta_seed_ready, "true", "false"),
      ifelse(is.null(new.theta.out$sm), "NULL", paste(dim(new.theta.out$sm), collapse = "x")),
      ifelse(is.null(new.theta.out$sC), "NULL", paste(dim(new.theta.out$sC), collapse = "x"))
    ))
    flush.console()
  }
  if (!theta_seed_ready) {
    stop(sprintf("state-freeze theta seed failed for p0=%s", as.character(p0)), call. = FALSE)
  }
}

  
while (isTRUE(FLAG) && iter < max_iter) {


    cur.covs_list = new.covs_list

    cur.uts.out = new.uts.out
    cur.sts.out = new.sts.out 
    cur.uts.out_f = new.uts.out_f
    cur.sts.out_f = new.sts.out_f

    cur.gamsig.out = new.gamsig.out
    cur.theta.out = new.theta.out

    ex.df.mat_f <- as.matrix(ex.df.mat_f)
    ex.df.mat.k_f <- as.matrix(ex.df.mat.k_f)

    FFF <- (new.gamsig.out$E.c.invb.absgam[,] * new.sts.out$E.sts + new.gamsig.out$E.a.invb.inv.sigma[,]/new.uts.out$E.inv.uts) / new.gamsig.out$E.invb.inv.sigma[,] 
    QQQ <- 1/(new.gamsig.out$E.invb.inv.sigma[,] * new.uts.out$E.inv.uts)
    if(J>0){
    QQQ <- array(apply(QQQ, 2, function(col) diag(col)), dim = c(J+1, J+1, TT_sub))
    }else{
        QQQ <- array(QQQ, dim = c(J+1, J+1, TT_sub))
    }


    ######################################
    ######################################


    FFF_list <- vector("list", J)
    QQQ_list <- vector("list", J)
    for (j in 1:J) {
        FFF_j <- (new.gamsig.out$E.c.invb.absgam[j,] * new.sts.out_f$E.sts[[j]] + new.gamsig.out$E.a.invb.inv.sigma[j,] / new.uts.out_f$E.inv.uts[[j]]) / new.gamsig.out$E.invb.inv.sigma[j,]
        FFF_list[[j]] <- FFF_j

        QQQ_j <- 1/(new.gamsig.out$E.invb.inv.sigma[j,] * new.uts.out_f$E.inv.uts[[j]])
        QQQ_list[[j]] <- QQQ_j
    }

    ######################################
    ######################################
    result_F <- disc_w_concat_horizon_segments(FFF_list, sprintf("FFF_list iter=%d", as.integer(iter)))
    FFF_forecast <- lapply(result_F, t)

    result_Q <- disc_w_concat_horizon_segments(QQQ_list, sprintf("QQQ_list iter=%d", as.integer(iter)))
    QQQ_forecast_VEC <- lapply(result_Q, t)
    QQQ_forecast <- vector("list", J)

    # Loop through each element in QQQ_forecast
    for (j in 1:J) {
      # Get the dimensions of the current matrix
      n <- dim(QQQ_forecast_VEC[[j]])[1]
      m <- dim(QQQ_forecast_VEC[[j]])[2]
      
      # Initialize the array
      A <- array(0, dim = c(n, n, m))
      
      # Fill the array with diagonal matrices
      for (k in 1:m) {
        A[,,k] <- diag(QQQ_forecast_VEC[[j]][,k])
      }
      
      # Store the array in the list
      QQQ_forecast[[j]] <- A
    }
  iter_candidate <- as.integer(iter + 1L)
  state_hold_now <- (state_hold_until_iter > 0L) &&
    (iter_candidate <= state_hold_until_iter)
  state_freeze_now <- (identical(DISC_GAMSIG_FREEZE_TARGET, "states") &&
    (gamsig_dynamic_freeze_until_iter > 0L) &&
    (iter_candidate <= gamsig_dynamic_freeze_until_iter)) ||
    state_hold_now

  if (state_freeze_now) {
    theta_update <- FALSE
    iter <- iter_candidate
    fast <- fast + 1
    if (isTRUE(DISC_GAMSIG_OBJECTIVE_GUARD_LOG_FAILURES)) {
      if (state_hold_now) {
        cat(sprintf(
          "[%s_hold] p0=%s iter=%d hold_until_iter=%d\n",
          state_log_prefix, as.character(p0), as.integer(iter), as.integer(state_hold_until_iter)
        ))
      } else {
        cat(sprintf(
          "[state_freeze] p0=%s iter=%d freeze_until_iter=%d\n",
          as.character(p0), as.integer(iter), as.integer(gamsig_dynamic_freeze_until_iter)
        ))
      }
      flush.console()
    }
  } else if (iter < max_iter) {
    # if ((crit_ELBO+conv.check) < tol1 || iter < 100 || fast > 0 ) {
    if (isTRUE(DISC_STRICT_CONTRACTS)) {
      disc_w_validate_cpp_contract(
        GG = GG,
        m0 = m0,
        C0 = C0,
        FF = FF,
        y = y,
        ex.df.mat = ex.df.mat,
        ex.df.mat.k = ex.df.mat.k,
        GG_list = GG_list,
        FF_list = FF_list,
        FFF_forecast = FFF_forecast,
        QQQ_forecast = QQQ_forecast,
        ensembles_forecast = ensembles_forecast,
        cur.covs_list = cur.covs_list,
        num_mem = num_mem,
        ranges = ranges,
        p = p,
        J = J,
        ppx = ppx,
        TT_sub = TT_sub,
        context_label = sprintf("p0=%s iter=%d", as.character(p0), as.integer(iter))
      )
    }
    update.theta.raw <- DISC_update_theta_synth_cpp_W( GG, m0, C0,
                                            FFF, QQQ,
                                            FF, y, ex.df.mat, ex.df.mat.k, Ones,
                                            p, J, ppx, TT, k, dM,
                                            GG_list, FF_list,
                                            FFF_forecast, QQQ_forecast,
                                            DF.MAT, DF.MAT_k,
                                            ensembles_forecast, ranges, Ones_ens,
                                            sum(num_mem), num_mem, cur.covs_list,
                                            epsilon)
    update.theta <- disc_materialize_theta_cpp_payload(
      update.theta.raw,
      J = J,
      p = p,
      ppx = ppx,
      num_mem = num_mem,
      context_label = sprintf("p0=%s iter=%d materialized", as.character(p0), as.integer(iter_candidate))
    )
    if (!state_freeze_now &&
        is.finite(state_blend_alpha) &&
        state_blend_alpha < 1) {
      blend_alpha <- as.numeric(state_blend_alpha)
      update.theta$sm <- disc_blend_numeric_like(cur.theta.out$sm, update.theta$sm, blend_alpha, "theta$sm")
      update.theta$sC <- disc_blend_numeric_like(cur.theta.out$sC, update.theta$sC, blend_alpha, "theta$sC")
      update.theta$fm <- disc_blend_numeric_like(cur.theta.out$fm, update.theta$fm, blend_alpha, "theta$fm")
      update.theta$fC <- disc_blend_numeric_like(cur.theta.out$fC, update.theta$fC, blend_alpha, "theta$fC")
      update.theta$sm_ens <- disc_blend_numeric_list(cur.theta.out$sm_ens, update.theta$sm_ens, blend_alpha, "theta$sm_ens")
      update.theta$sC_ens <- disc_blend_numeric_list(cur.theta.out$sC_ens, update.theta$sC_ens, blend_alpha, "theta$sC_ens")
      update.theta$fm_ens <- disc_blend_numeric_list(cur.theta.out$fm_ens, update.theta$fm_ens, blend_alpha, "theta$fm_ens")
      update.theta$fC_ens <- disc_blend_numeric_list(cur.theta.out$fC_ens, update.theta$fC_ens, blend_alpha, "theta$fC_ens")
      if (isTRUE(DISC_GAMSIG_OBJECTIVE_GUARD_LOG_FAILURES)) {
        cat(sprintf(
          "[%s_blend] p0=%s iter=%d alpha=%g\n",
          state_log_prefix, as.character(p0), as.integer(iter_candidate), blend_alpha
        ))
        flush.console()
      }
    }

    FF_t <- aperm(FF, c(2, 1, 3))
    multiply_matrices <- function(slice_index) {
        FF_t[,,slice_index] %*% update.theta$sm[,slice_index]
    }
    result_list <- lapply(1:ncol(update.theta$sm), multiply_matrices)
    result_array <- array(unlist(result_list), dim = c(J+1, 1, ncol(update.theta$sm)))
    result_array <- aperm(result_array, c(1, 3, 2))[,,1]
    exps <- result_array
    compute_product_1 <- function(t) {
        FF_t_slice <- FF_t[,,t]
        sC_slice <- update.theta$sC[,,t]
        FF_slice <- FF[,,t]
        result_slice <- t(FF_slice)%*%sC_slice%*%(FF_slice )
        return(result_slice)
    }
    result_list_1 <- lapply(1:dim(FF)[3], compute_product_1)
    vars_1 <- simplify2array(result_list_1)

    vars <- (apply(vars_1, 3, function(x) diag(x)))
    exps2 = exps^2 + vars

    ####################################################
    ####################################################
    rs <- 0
    for (j in 1:J) {

    r_j <- ncol(update.theta$sm_ens[[j]])
    rs <- r_j + rs
    fm_j <- update.theta$fm_ens[[j]]
    sm_j <- update.theta$sm_ens[[j]]
    fC_j <- update.theta$fC_ens[[j]]
    sC_j <- update.theta$sC_ens[[j]]

    FF_synth <- FF_list[[j]]

    FF_t <- t(FF_synth)
    exps_ens <- FF_t %*% sm_j

    compute_product_1 <- function(t) {
        sC_slice <- sC_j[,,t]
        FF_slice <- FF_synth
        result_slice <- t(FF_slice)%*%sC_slice%*%(FF_slice )
        return(result_slice)
    }

    result_list_1 <- lapply(1:r_j, compute_product_1)
    vars_1 <- simplify2array(result_list_1)

    if(j==J){
        vars_ens <- vars_1
    }else{
        vars_ens <- (apply(vars_1, 3, function(x) diag(x)))
    }
        exps2_ens = exps_ens^2 + vars_ens

    # new.theta.out  <- update.theta
    new.theta.out$exps[2:(J-j+2),(TT+1+rs-r_j):(TT+rs)] <- exps_ens
    new.theta.out$exps2[2:(J-j+2),(TT+1+rs-r_j):(TT+rs)] <- exps2_ens
    new.theta.out$sm_ens[[j]] <- sm_j
    new.theta.out$sC_ens[[j]] <- sC_j
    new.theta.out$fm_ens[[j]] <- fm_j
    new.theta.out$fC_ens[[j]] <- fC_j

    new.theta.out$standard_forecast_errors_ens[[j]] <- update.theta$standard_forecast_errors_ens[[j]]
    }

    new.theta.out$exps[,1:TT] <- exps
    new.theta.out$exps2[,1:TT] <- exps2
    new.theta.out$standard_forecast_errors <- update.theta$standard_forecast_errors
    new.theta.out$sm <- update.theta$sm
    new.theta.out$sC <- update.theta$sC
    new.theta.out$fm <- update.theta$fm
    new.theta.out$fC <- update.theta$fC

    new.theta.out$elbo.part <- update.theta$elbo.part
    new.theta.out$elbo.part_ens <- update.theta$elbo.part_ens

    new.theta.out$W_T <- update.theta$W_T
    theta_update <- TRUE
    iter <- iter + 1
    fast <- 0
  } else {
    theta_update <- FALSE
    fast <- fast + 1
  }

  ## UPDATE W
  if (!state_freeze_now) {
    ranges_rev <- rev(ranges_per)
    for(j in 1:J){
        ddd <- as.integer(dim_theta[j])
        for(t in 1:ranges_rev[j]){
            Ct <- disc_w_force_spd(
              new.theta.out$sC_ens[[j]][,,t],
              label = sprintf("sC_ens[[%d]][,,%d]", as.integer(j), as.integer(t))
            )
            mt <- as.numeric(new.theta.out$sm_ens[[j]][,t])
            GGG <- as.matrix(GG_list[[j]])
            storage.mode(GGG) <- "double"
            if((t == 1) && (j == 1)){
                Ct_1 <- disc_w_force_spd(
                  new.theta.out$sC[1:ddd,1:ddd,TT],
                  label = sprintf("sC_hist_sub[[%d]]", as.integer(j))
                )
                mt_1 <- as.numeric(new.theta.out$sm[1:ddd,TT])
            } else if (t == 1) {
                prev_h <- as.integer(ranges_rev[j-1])
                Ct_1 <- disc_w_force_spd(
                  new.theta.out$sC_ens[[j-1]][1:ddd,1:ddd,prev_h],
                  label = sprintf("sC_ens[[%d]] carry slice", as.integer(j - 1L))
                )
                mt_1 <- as.numeric(new.theta.out$sm_ens[[j-1]][1:ddd,prev_h])
            } else {
                Ct_1 <- disc_w_force_spd(
                  new.theta.out$sC_ens[[j]][,,(t-1)],
                  label = sprintf("sC_ens[[%d]][,,%d]", as.integer(j), as.integer(t - 1L))
                )
                mt_1 <- as.numeric(new.theta.out$sm_ens[[j]][,(t-1)])
            }

            GCG <- disc_w_force_spd(
              GGG %*% Ct_1 %*% t(GGG),
              label = sprintf("GCG[j=%d,t=%d]", as.integer(j), as.integer(t))
            )
            cov_t <- disc_w_force_spd(
              cur.covs_list[[j]][,,t],
              label = sprintf("cur.covs_list[[%d]][,,%d]", as.integer(j), as.integer(t))
            )
            R <- disc_w_force_spd(
              GCG + cov_t,
              label = sprintf("R[j=%d,t=%d]", as.integer(j), as.integer(t))
            )
            R_inv <- disc_w_spd_inverse(R, label = sprintf("R_inv[j=%d,t=%d]", as.integer(j), as.integer(t)))
            innovation <- mt - as.numeric(GGG %*% mt_1)
            ww <- GCG +
              tcrossprod(innovation) +
              Ct -
              2 * GCG %*% R_inv %*% Ct
            ww <- disc_w_force_spd(
              ww,
              label = sprintf("ww[j=%d,t=%d]", as.integer(j), as.integer(t))
            )
            prior_w <- disc_w_force_spd(
              new.theta.out$W_T[1:ddd,1:ddd],
              label = sprintf("W_T_sub[j=%d]", as.integer(j))
            )
            new_cov <- epsilon/(epsilon+1) * c_factor * prior_w + 1/(epsilon+1) * ww
            new.covs_list[[j]][,,t]  <- disc_w_force_spd(
              new_cov,
              label = sprintf("new.covs_list[[%d]][,,%d]", as.integer(j), as.integer(t))
            )
        }
    }
  }
  if (theta_update &&
      !state_freeze_now &&
      is.finite(cov_blend_alpha) &&
      cov_blend_alpha < 1) {
    cov_blend_alpha <- as.numeric(cov_blend_alpha)
    new.covs_list <- disc_blend_numeric_list(cur.covs_list, new.covs_list, cov_blend_alpha, "covs_list")
    if (isTRUE(DISC_GAMSIG_OBJECTIVE_GUARD_LOG_FAILURES)) {
      cat(sprintf(
        "[%s_cov_blend] p0=%s iter=%d alpha=%g\n",
        state_log_prefix, as.character(p0), as.integer(iter), cov_blend_alpha
      ))
      flush.console()
    }
  }

  gamsig_frozen_now <- identical(DISC_GAMSIG_FREEZE_TARGET, "gamma_sigma") &&
    (gamsig_dynamic_freeze_until_iter > 0L) &&
    (iter <= gamsig_dynamic_freeze_until_iter)
  if (gamsig_frozen_now && isTRUE(DISC_GAMSIG_OBJECTIVE_GUARD_LOG_FAILURES)) {
    cat(sprintf(
      "[gamsig_freeze] p0=%s iter=%d freeze_until_iter=%d\n",
      as.character(p0), as.integer(iter), as.integer(gamsig_dynamic_freeze_until_iter)
    ))
    flush.console()
  }

  ## UPDATE s and u
  for (j in 1:(J+1)) {   
      sts.dummy <- update_sts(y[j,],
                              new.theta.out$exps[j,1:TT_sub], 
                              cur.uts.out$E.inv.uts[j,], 
                              cur.gamsig.out$E.c2.invb.absgam2.sigma[j,], 
                              cur.gamsig.out$E.c.invb.absgam[j,], 
                              cur.gamsig.out$E.c.a.invb.absgam[j,], TT_sub)
      new.sts.out$E.sts[j,] <- sts.dummy$E.sts
      new.sts.out$E.sts2[j,] <- sts.dummy$E.sts2
      new.sts.out$tot.entrop[j,] <-  sts.dummy$tot.entrop
      ########################
      uts.dummy <- update_uts(y[j,],
                              new.theta.out$exps[j,1:TT_sub], 
                              new.theta.out$exps2[j,1:TT_sub], 
                              new.sts.out$E.sts[j,], 
                              new.sts.out$E.sts2[j,], 
                              cur.gamsig.out$E.inv.sigma[j,], 
                              cur.gamsig.out$E.a2.invb.inv.sigma[j,], 
                              cur.gamsig.out$E.invb.inv.sigma[j,], 
                              cur.gamsig.out$E.c.invb.absgam[j,], 
                              cur.gamsig.out$E.c2.invb.absgam2.sigma[j,]) 
      new.uts.out$E.uts[j,] <- uts.dummy$E.uts
      new.uts.out$E.inv.uts[j,] <- uts.dummy$E.inv.uts
      new.uts.out$E.log.uts[j,] <- uts.dummy$E.log.uts
      new.uts.out$tot.entrop[j,] <- uts.dummy$tot.entrop
      ########################
      if (j == 1) {
        if (!gamsig_frozen_now) {
        gamsig.dummy <- update_gamma_sigma(y[j,], 
                                            TT,
                                            PriorGamma[j,],
                                            PriorSigma[j,],
                                              cur.gamsig.out$E.gam[j,], 
                                              cur.gamsig.out$V.gam[j,], 
                                              cur.gamsig.out$E.sigma[j,], 
                                              cur.gamsig.out$V.sigma[j,], 
                                              new.theta.out$exps[j,1:TT_sub], 
                                              new.theta.out$exps2[j,1:TT_sub], 
                                              new.sts.out$E.sts[j,], 
                                              new.sts.out$E.sts2[j,], 
                                              new.uts.out$E.uts[j,], 
                                              new.uts.out$E.inv.uts[j,],
                                              cur.gamsig.out$E.sigma[j,], 
                                              cur.gamsig.out$E.gam[j,],
                                              FALSE,
                                              context_label = sprintf("vb_main iter=%d j=%d climate_center=FALSE", iter, j))    
          if (isTRUE(gamsig.dummy$guard_triggered) &&
              DISC_GAMSIG_GUARD_REFREEZE_ITERS > 0L &&
              identical(DISC_GAMSIG_FREEZE_TARGET, "gamma_sigma")) {
            old_freeze_until <- gamsig_dynamic_freeze_until_iter
            gamsig_dynamic_freeze_until_iter <- max(
              as.integer(gamsig_dynamic_freeze_until_iter),
              as.integer(iter + DISC_GAMSIG_GUARD_REFREEZE_ITERS)
            )
            gamsig_frozen_now <- TRUE
            if (isTRUE(DISC_GAMSIG_OBJECTIVE_GUARD_LOG_FAILURES)) {
              cat(sprintf(
                "[gamsig_refreeze] p0=%s iter=%d j=%d old_until=%d new_until=%d reason=%s\n",
                as.character(p0),
                as.integer(iter),
                as.integer(j),
                as.integer(old_freeze_until),
                as.integer(gamsig_dynamic_freeze_until_iter),
                ifelse(is.null(gamsig.dummy$guard_message), "", as.character(gamsig.dummy$guard_message))
              ))
              flush.console()
            }
          }
          new.gamsig.out$E.gam[j,] <- gamsig.dummy$E.gam
          new.gamsig.out$E.sigma[j,] <- gamsig.dummy$E.sigma
          new.gamsig.out$E.inv.sigma[j,] <- gamsig.dummy$E.inv.sigma
          new.gamsig.out$E.c2.invb.absgam2.sigma[j,] <- gamsig.dummy$E.c2.invb.absgam2.sigma
          new.gamsig.out$E.c.invb.absgam[j,] <- gamsig.dummy$E.c.invb.absgam
          new.gamsig.out$E.c.a.invb.absgam[j,] <- gamsig.dummy$E.c.a.invb.absgam
          new.gamsig.out$E.a2.invb.inv.sigma[j,] <- gamsig.dummy$E.a2.invb.inv.sigma
          new.gamsig.out$E.invb.inv.sigma[j,] <- gamsig.dummy$E.invb.inv.sigma
          new.gamsig.out$E.a.invb.inv.sigma[j,] <- gamsig.dummy$E.a.invb.inv.sigma
          new.gamsig.out$E.log.sig.b[j,] <- gamsig.dummy$E.log.sig.b
          new.gamsig.out$E.log.sig[j,] <- gamsig.dummy$E.log.sig
          new.gamsig.out$E.prior.sig.gam[j,] <- gamsig.dummy$E.prior.sig.gam
          new.gamsig.out$entrop[j,] <- gamsig.dummy$entrop
        }
      }else{
          k_forecast <- ranges[j-1]
          for (i in 1:num_mem[j-1]) {
              
          sts.dummy <- update_sts(
                          y = matrix(ensembles[[j-1]][,i], ncol=1), 
                          exps = matrix(new.theta.out$exps[j,(TT_sub+1):(TT_sub+k_forecast)], ncol=1), 
                          inv.uts = matrix(cur.uts.out_f$E.inv.uts[[j-1]][,i], ncol=1), 
                          c2.invb.absgam2.sigma = cur.gamsig.out$E.c2.invb.absgam2.sigma[j,], 
                          c.invb.absgam = cur.gamsig.out$E.c.invb.absgam[j,], 
                          c.a.invb.absgam = cur.gamsig.out$E.c.a.invb.absgam[j,], 
                          k_forecast)

          new.sts.out_f$E.sts[[j-1]][,i] <- sts.dummy$E.sts
          new.sts.out_f$E.sts2[[j-1]][,i] <- sts.dummy$E.sts2
          new.sts.out_f$tot.entrop[[j-1]][i] <-  sts.dummy$tot.entrop

          uts.dummy <- update_uts(
                          y = matrix(ensembles[[j-1]][,i], ncol=1),
                          exps = matrix(new.theta.out$exps[j,(T+1):(T+k_forecast)], ncol=1), 
                          exps2 = matrix(new.theta.out$exps2[j,(T+1):(T+k_forecast)], ncol=1), 
                          new.sts.out_f$E.sts[[j-1]][,i], 
                          new.sts.out_f$E.sts2[[j-1]][,i], 
                          cur.gamsig.out$E.inv.sigma[j,], 
                          cur.gamsig.out$E.a2.invb.inv.sigma[j,], 
                          cur.gamsig.out$E.invb.inv.sigma[j,], 
                          cur.gamsig.out$E.c.invb.absgam[j,], 
                          cur.gamsig.out$E.c2.invb.absgam2.sigma[j,]) 
                          
          new.uts.out_f$E.uts[[j-1]][,i] <- uts.dummy$E.uts
          new.uts.out_f$E.inv.uts[[j-1]][,i] <- uts.dummy$E.inv.uts
          new.uts.out_f$E.log.uts[[j-1]][i] <- uts.dummy$E.log.uts
          new.uts.out_f$tot.entrop[[j-1]][i] <- uts.dummy$tot.entrop
          }

      }
  }
    ## UPDATE sigma and gamma
  for (j in 2:(J+1)) {  
          if (gamsig_frozen_now) {
            next
          }
          k_forecast <- ranges[j-1]
          gamsig.dummy <- update_gamma_sigma(Y[j,], TT_sub,
                                              PriorGamma[j,],
                                              PriorSigma[j,],
                                              cur.gamsig.out$E.gam[j,], 
                                              cur.gamsig.out$V.gam[j,], 
                                              cur.gamsig.out$E.sigma[j,], 
                                              cur.gamsig.out$V.sigma[j,], 
                                              new.theta.out$exps[j,], 
                                              new.theta.out$exps2[j,], 
                                              new.sts.out$E.sts[j,], 
                                              new.sts.out$E.sts2[j,], 
                                              new.uts.out$E.uts[j,], 
                                              new.uts.out$E.inv.uts[j,],
                                              cur.gamsig.out$E.sigma[j,], 
                                              cur.gamsig.out$E.gam[j,],
                                              TRUE ,
                                              ensembles[[j-1]], 
                                              num_mem[j-1], 
                                              k_forecast,
                                              new.sts.out_f$E.sts[[j-1]],
                                              new.sts.out_f$E.sts2[[j-1]],
                                              new.uts.out_f$E.uts[[j-1]],
                                              new.uts.out_f$E.inv.uts[[j-1]],
                                              context_label = sprintf("vb_main iter=%d j=%d climate_center=TRUE", iter, j))
          if (isTRUE(gamsig.dummy$guard_triggered) &&
              DISC_GAMSIG_GUARD_REFREEZE_ITERS > 0L &&
              identical(DISC_GAMSIG_FREEZE_TARGET, "gamma_sigma")) {
            old_freeze_until <- gamsig_dynamic_freeze_until_iter
            gamsig_dynamic_freeze_until_iter <- max(
              as.integer(gamsig_dynamic_freeze_until_iter),
              as.integer(iter + DISC_GAMSIG_GUARD_REFREEZE_ITERS)
            )
            gamsig_frozen_now <- TRUE
            if (isTRUE(DISC_GAMSIG_OBJECTIVE_GUARD_LOG_FAILURES)) {
              cat(sprintf(
                "[gamsig_refreeze] p0=%s iter=%d j=%d old_until=%d new_until=%d reason=%s\n",
                as.character(p0),
                as.integer(iter),
                as.integer(j),
                as.integer(old_freeze_until),
                as.integer(gamsig_dynamic_freeze_until_iter),
                ifelse(is.null(gamsig.dummy$guard_message), "", as.character(gamsig.dummy$guard_message))
              ))
              flush.console()
            }
          }

          new.gamsig.out$E.gam[j,] <- gamsig.dummy$E.gam
          new.gamsig.out$E.sigma[j,] <- gamsig.dummy$E.sigma
          new.gamsig.out$E.inv.sigma[j,] <- gamsig.dummy$E.inv.sigma
          new.gamsig.out$E.c2.invb.absgam2.sigma[j,] <- gamsig.dummy$E.c2.invb.absgam2.sigma
          new.gamsig.out$E.c.invb.absgam[j,] <- gamsig.dummy$E.c.invb.absgam
          new.gamsig.out$E.c.a.invb.absgam[j,] <- gamsig.dummy$E.c.a.invb.absgam
          new.gamsig.out$E.a2.invb.inv.sigma[j,] <- gamsig.dummy$E.a2.invb.inv.sigma
          new.gamsig.out$E.invb.inv.sigma[j,] <- gamsig.dummy$E.invb.inv.sigma
          new.gamsig.out$E.a.invb.inv.sigma[j,] <- gamsig.dummy$E.a.invb.inv.sigma
          new.gamsig.out$E.log.sig.b[j,] <- gamsig.dummy$E.log.sig.b
          new.gamsig.out$E.log.sig[j,] <- gamsig.dummy$E.log.sig
          new.gamsig.out$E.prior.sig.gam[j,] <- gamsig.dummy$E.prior.sig.gam
          new.gamsig.out$entrop[j,] <- gamsig.dummy$entrop
  }

  if (!gamsig_frozen_now) {
    gamsig_update_iters <- as.integer(gamsig_update_iters + 1L)
  }

  old.gam <- as.numeric(seq.gamma[, dim(seq.gamma)[2], drop = TRUE])
  new.gam <- as.numeric(new.gamsig.out$E.gam)
  if (length(old.gam) != length(new.gam)) {
    stop(sprintf("gamma length drift at iter=%d: old=%d new=%d", as.integer(iter), as.integer(length(old.gam)), as.integer(length(new.gam))), call. = FALSE)
  }
  seq.gamma = cbind(seq.gamma, new.gam)

  old.sig <- as.numeric(seq.sigma[, dim(seq.sigma)[2], drop = TRUE])
  new.sig <- as.numeric(new.gamsig.out$E.sigma)
  if (length(old.sig) != length(new.sig)) {
    stop(sprintf("sigma length drift at iter=%d: old=%d new=%d", as.integer(iter), as.integer(length(old.sig)), as.integer(length(new.sig))), call. = FALSE)
  }
  seq.sigma = cbind(seq.sigma, new.sig)
  gamma_delta_vec <- as.numeric(new.gam - old.gam)
  sigma_delta_vec <- as.numeric(new.sig - old.sig)

  if (gamsig_frozen_now) {
    conv.check <- Inf
  } else {
    step_vec <- c(gamma_delta_vec, sigma_delta_vec)
    if (length(step_vec) == 0L || any(!is.finite(step_vec))) {
      conv.check <- Inf
    } else {
      conv.check <- sum(step_vec^2)
    }
  }

  ##########
  # ELBO
  ##########
  elbo <- 0

  elbo <- elbo -1/2*sum(T_size*new.gamsig.out$E.log.sig.b[,])

  elbo <- elbo -0.5*sum(new.uts.out$E.log.uts[,])-0.5*sum(unlist(new.uts.out_f$E.log.uts))
  elbo <- elbo -sum(T_size)/2*log(pi)

  elbo <- elbo -0.5*sum((new.gamsig.out$E.invb.inv.sigma[,]*new.uts.out$E.inv.uts[,])*(y[,]^2-2*y[,]*new.theta.out$exps[,1:TT_sub]+new.theta.out$exps2[,1:TT_sub]))
  ss <- 0
  for(j in 2:J){ss <- ss - 0.5* sum((new.gamsig.out$E.invb.inv.sigma[j,]*new.uts.out_f$E.inv.uts[[j-1]])*(ensembles[[j-1]]^2-2*ensembles[[j-1]]*new.theta.out$exps[j,(TT_sub+1):(TT_sub+k_forecast)]+new.theta.out$exps2[j,(TT_sub+1):(TT_sub+k_forecast)]))
  }
  elbo <- elbo + ss

  elbo <- elbo +sum((y[,]-new.theta.out$exps[,1:TT_sub])*(new.gamsig.out$E.c.invb.absgam[,]*new.sts.out$E.sts*new.uts.out$E.inv.uts[,]+new.gamsig.out$E.a.invb.inv.sigma[,]))
  ss <- 0
  for(j in 2:J){ss <- ss - 0.5* sum((ensembles[[j-1]]-new.theta.out$exps[j,(TT_sub+1):(TT_sub+k_forecast)])*(new.gamsig.out$E.c.invb.absgam[j,]*new.sts.out_f$E.sts[[j-1]]*new.uts.out_f$E.inv.uts[[j-1]]+new.gamsig.out$E.a.invb.inv.sigma[j,]))
  }
  elbo <- elbo + ss

  elbo <- elbo -0.5*sum(new.sts.out$E.sts2[,]*new.uts.out$E.inv.uts[,]*new.gamsig.out$E.c2.invb.absgam2.sigma[,])
  ss <- 0
  for(j in 2:J){ss <- ss - 0.5*sum(new.gamsig.out$E.c2.invb.absgam2.sigma[j,]*new.uts.out_f$E.sts2[[j-1]]*new.uts.out_f$E.uts[[j-1]])}
  elbo <- elbo + ss

  elbo <- elbo -sum(new.gamsig.out$E.c.a.invb.absgam[,]*new.sts.out$E.sts[,])
  ss <- 0
  for(j in 2:J){ss <- ss - sum(new.gamsig.out$E.c.a.invb.absgam[j,]*new.uts.out_f$E.sts[[j-1]])}
  elbo <- elbo + ss

  elbo <- elbo -0.5*sum(new.gamsig.out$E.a2.invb.inv.sigma[,]*new.uts.out$E.uts[,])
  ss <- 0
  for(j in 2:J){ss <- ss - 0.5*sum(new.gamsig.out$E.a2.invb.inv.sigma[j,]*new.uts.out_f$E.uts[[j-1]])}
  elbo <- elbo + ss

  elbo <- elbo -sum(T_size*new.gamsig.out$E.log.sig[,])

  elbo <- elbo -sum(new.gamsig.out$E.inv.sigma[,]*new.uts.out$E.uts[,])
  ss <- 0
  for(j in 2:J){ss <- ss - sum(new.gamsig.out$E.inv.sigma[j,]*new.uts.out_f$E.uts[[j-1]])}
  elbo <- elbo + ss

  elbo <- elbo -0.5*sum(new.sts.out$E.sts2[,])-0.5*sum(unlist(new.sts.out_f$E.sts2)) 
  elbo <- elbo +sum(new.gamsig.out$E.prior.sig.gam[,])

  elbo <- elbo +sum(new.uts.out$tot.entrop[,])+sum(unlist(new.uts.out_f$tot.entrop))
  elbo <- elbo +sum(new.sts.out$E.tot.entrop[,])+sum(unlist(new.sts.out_f$tot.entrop)) 
  elbo <- elbo +sum(new.gamsig.out$E.sig.gam.entrop[,])
  elbo <- elbo + new.theta.out$elbo.part

  ######################

  elbo <- elbo/sum(T_size)/( p*(J+1) + ppx)
  crit_ELBO <- abs(ELBO-elbo)
  ELBO <- elbo
  seq.elbo =  cbind(seq.elbo, ELBO) 
 
  seq.eigen = cbind(seq.eigen, min(abs(eigen(new.covs_list[[2]][,,ranges_per[1]])$values))) 

  print(c(iter, elbo, crit_ELBO))
  sigma_exp <- suppressWarnings(as.numeric(mean(new.sig, na.rm = TRUE)))
  gamma_exp <- suppressWarnings(as.numeric(mean(new.gam, na.rm = TRUE)))
  state_norm_sq <- suppressWarnings(as.numeric(sum(new.theta.out$sm^2, na.rm = TRUE)))
  if (!is.finite(sigma_exp)) sigma_exp <- NA_real_
  if (!is.finite(gamma_exp)) gamma_exp <- NA_real_
  if (!is.finite(state_norm_sq)) state_norm_sq <- NA_real_
  state_guard_active <- (!isTRUE(DISC_W_AL_MODE) &&
    isTRUE(state_guard_enabled))
  state_growth_ratio <- NA_real_
  if (state_guard_active &&
      theta_update &&
      !isTRUE(gamsig_frozen_now) &&
      is.finite(prev_state_norm_sq) &&
      prev_state_norm_sq > 0 &&
      is.finite(state_norm_sq)) {
    state_growth_ratio <- state_norm_sq / prev_state_norm_sq
  }
  state_guard_reason <- NULL
  if (state_guard_active && theta_update && !isTRUE(gamsig_frozen_now)) {
    if (!is.finite(state_norm_sq)) {
      state_guard_reason <- "non-finite state_norm_sq"
    } else if (is.finite(state_norm_abs_cap) && state_norm_sq > state_norm_abs_cap) {
      state_guard_reason <- sprintf(
        "state_norm_sq=%s exceeds abs_cap=%s",
        fmt_iter_num(state_norm_sq),
        fmt_iter_num(state_norm_abs_cap)
      )
    } else if (is.finite(state_growth_ratio) &&
               is.finite(state_norm_max_ratio) &&
               state_growth_ratio > state_norm_max_ratio) {
      state_guard_reason <- sprintf(
        "state_growth_ratio=%s exceeds max_ratio=%s",
        fmt_iter_num(state_growth_ratio),
        fmt_iter_num(state_norm_max_ratio)
      )
    }
  }
  if (!is.null(state_guard_reason)) {
    state_guard_count <- as.integer(state_guard_count + 1L)
    last_state_guard_iter <- as.integer(iter)
    last_state_guard_reason <- state_guard_reason
    old_freeze_until <- gamsig_dynamic_freeze_until_iter
    old_hold_until <- state_hold_until_iter
    gamsig_dynamic_freeze_until_iter <- max(
      as.integer(gamsig_dynamic_freeze_until_iter),
      as.integer(iter + state_guard_refreeze_iters)
    )
    if (state_hold_after_guard_iters > 0L) {
      state_hold_until_iter <- max(
        as.integer(state_hold_until_iter),
        as.integer(iter + state_hold_after_guard_iters)
      )
    }
    gamsig_frozen_now <- TRUE
    if (gamsig_update_iters > 0L) {
      gamsig_update_iters <- as.integer(gamsig_update_iters - 1L)
    }
    new.theta.out <- cur.theta.out
    new.sts.out <- cur.sts.out
    new.uts.out <- cur.uts.out
    new.sts.out_f <- cur.sts.out_f
    new.uts.out_f <- cur.uts.out_f
    new.gamsig.out <- cur.gamsig.out
    new.covs_list <- cur.covs_list
    if (ncol(seq.gamma) >= 1L) {
      seq.gamma[, ncol(seq.gamma)] <- old.gam
    }
    if (ncol(seq.sigma) >= 1L) {
      seq.sigma[, ncol(seq.sigma)] <- old.sig
    }
    new.gam <- old.gam
    new.sig <- old.sig
    gamma_delta_vec <- rep(0, length(old.gam))
    sigma_delta_vec <- rep(0, length(old.sig))
    elbo <- ELBO
    crit_ELBO <- Inf
    if (ncol(seq.elbo) >= 1L) {
      seq.elbo[, ncol(seq.elbo)] <- ELBO
    }
    sigma_exp <- prev_sigma_exp
    gamma_exp <- prev_gamma_exp
    state_norm_sq <- prev_state_norm_sq
    crit_sigma_exp <- Inf
    crit_gamma_exp <- Inf
    crit_state_norm_sq <- Inf
    conv.check <- Inf
    if (isTRUE(DISC_GAMSIG_OBJECTIVE_GUARD_LOG_FAILURES)) {
      cat(sprintf(
        "[gamsig_state_guard] p0=%s iter=%d old_until=%d new_until=%d old_hold_until=%d new_hold_until=%d reason=%s\n",
        as.character(p0),
        as.integer(iter),
        as.integer(old_freeze_until),
        as.integer(gamsig_dynamic_freeze_until_iter),
        as.integer(old_hold_until),
        as.integer(state_hold_until_iter),
        state_guard_reason
      ))
      flush.console()
    }
  }
  if (is.finite(prev_state_norm_sq) && is.finite(state_norm_sq)) {
    crit_state_norm_sq <- abs(state_norm_sq - prev_state_norm_sq)
  } else {
    crit_state_norm_sq <- Inf
  }
  if (is.finite(prev_sigma_exp) && is.finite(sigma_exp)) {
    crit_sigma_exp <- abs(sigma_exp - prev_sigma_exp)
  } else {
    crit_sigma_exp <- Inf
  }
  if (is.finite(prev_gamma_exp) && is.finite(gamma_exp)) {
    crit_gamma_exp <- abs(gamma_exp - prev_gamma_exp)
  } else {
    crit_gamma_exp <- Inf
  }
  prev_state_norm_sq <- state_norm_sq
  prev_sigma_exp <- sigma_exp
  prev_gamma_exp <- gamma_exp

  if (isTRUE(DISC_GAMSIG_OBJECTIVE_GUARD_LOG_FAILURES)) {
    cat(sprintf(
      "[gamsig_progress] family=exdqlm_multivar p0=%s iter=%d elbo=%s crit_elbo=%s sigma_exp=%s crit_sigma_exp=%s gamma_exp=%s crit_gamma_exp=%s sigma_exp_vec=%s gamma_exp_vec=%s sigma_delta_vec=%s gamma_delta_vec=%s state_norm_sq=%s crit_state_norm_sq=%s conv_check=%s gamsig_update_iters=%d min_update_iters=%d min_total_iters=%d frozen=%s\n",
      as.character(p0),
      as.integer(iter),
      fmt_iter_num(elbo),
      fmt_iter_num(crit_ELBO),
      fmt_iter_num(sigma_exp),
      fmt_iter_num(crit_sigma_exp),
      fmt_iter_num(gamma_exp),
      fmt_iter_num(crit_gamma_exp),
      fmt_iter_vec(new.sig),
      fmt_iter_vec(new.gam),
      fmt_iter_vec(sigma_delta_vec),
      fmt_iter_vec(gamma_delta_vec),
      fmt_iter_num(state_norm_sq),
      fmt_iter_num(crit_state_norm_sq),
      fmt_iter_num(conv.check),
      as.integer(gamsig_update_iters),
      as.integer(DISC_GAMSIG_MIN_UPDATE_ITERS),
      as.integer(DISC_GAMSIG_MIN_TOTAL_ITERS),
      ifelse(isTRUE(gamsig_frozen_now), "true", "false")
    ))
  }
  flush.console()

  if(theta_update){
    conv_elbo <- is.finite(crit_ELBO) && (crit_ELBO < DISC_GAMSIG_ELBO_TOL)
    conv_state <- is.finite(crit_state_norm_sq) && (crit_state_norm_sq < DISC_GAMSIG_STATE_NORM_TOL)
    conv_sigma <- is.finite(crit_sigma_exp) && (crit_sigma_exp < DISC_GAMSIG_SIGMA_EXP_TOL)
    conv_gamma <- is.finite(crit_gamma_exp) && (crit_gamma_exp < DISC_GAMSIG_GAMMA_EXP_TOL)
    conv_min_updates <- gamsig_update_iters >= DISC_GAMSIG_MIN_UPDATE_ITERS
    conv_min_iters <- iter >= DISC_GAMSIG_MIN_TOTAL_ITERS
    if (conv_elbo && conv_state && conv_sigma && conv_gamma && conv_min_updates && conv_min_iters) {
      FLAG = FALSE
    } else if (isTRUE(DISC_GAMSIG_OBJECTIVE_GUARD_LOG_FAILURES)) {
      cat(sprintf(
        "[gamsig_hold] p0=%s iter=%d conv_elbo=%s conv_state=%s conv_sigma=%s conv_gamma=%s conv_min_updates=%s conv_min_iters=%s updates=%d required_updates=%d required_iters=%d\n",
        as.character(p0),
        as.integer(iter),
        ifelse(conv_elbo, "true", "false"),
        ifelse(conv_state, "true", "false"),
        ifelse(conv_sigma, "true", "false"),
        ifelse(conv_gamma, "true", "false"),
        ifelse(conv_min_updates, "true", "false"),
        ifelse(conv_min_iters, "true", "false"),
        as.integer(gamsig_update_iters),
        as.integer(DISC_GAMSIG_MIN_UPDATE_ITERS),
        as.integer(DISC_GAMSIG_MIN_TOTAL_ITERS)
      ))
    }
  }



}
########################

if (gamsig_update_iters < DISC_GAMSIG_MIN_UPDATE_ITERS) {
  disc_sampling_diag_emit(
    "sampling_preflight",
    "vb_terminal",
    sprintf(
      "update_iters=%d min_update_iters=%d guard_count=%d last_guard_iter=%s",
      as.integer(gamsig_update_iters),
      as.integer(DISC_GAMSIG_MIN_UPDATE_ITERS),
      as.integer(state_guard_count),
      if (is.finite(last_state_guard_iter)) as.character(as.integer(last_state_guard_iter)) else "NA"
    )
  )
  msg <- sprintf(
    "stopped before required gamma/sigma updates: got=%d required=%d",
    as.integer(gamsig_update_iters),
    as.integer(DISC_GAMSIG_MIN_UPDATE_ITERS)
  )
  stop(msg, call. = FALSE)
}

########################
run.time = tictoc::toc(quiet = TRUE)
########################
if (verbose) {
  cat(sprintf("VB converged: %s iterations, %s seconds", 
              iter, round(run.time$toc - run.time$tic, 3)), "\n")
}

print(c(n.samp))
flush.console()

terminal_sampling_guard_is_active <- identical(
  DISC_GAMSIG_TERMINAL_SAMPLING_GUARD_MODE,
  "fail_fast"
) && isTRUE(median_quantile_active)
terminal_guard_lag_iters <- if (is.finite(last_state_guard_iter)) {
  as.integer(iter - last_state_guard_iter)
} else {
  NA_integer_
}
terminal_sampling_guard_frozen <- (
  (gamsig_dynamic_freeze_until_iter > 0L && iter <= gamsig_dynamic_freeze_until_iter) ||
  (state_hold_until_iter > 0L && iter <= state_hold_until_iter) ||
  isTRUE(gamsig_frozen_now)
)
terminal_sampling_guard_recent <- is.finite(last_state_guard_iter) &&
  as.integer(last_state_guard_iter) >= as.integer(iter)
terminal_sampling_guard_recent_enough <- is.finite(terminal_guard_lag_iters) &&
  as.integer(terminal_guard_lag_iters) <=
    as.integer(DISC_GAMSIG_TERMINAL_SAMPLING_GUARD_MAX_GUARD_LAG_ITERS)
terminal_sampling_guard_blocked <- if (isTRUE(DISC_GAMSIG_TERMINAL_SAMPLING_GUARD_REQUIRE_FROZEN)) {
  isTRUE(terminal_sampling_guard_frozen) ||
    isTRUE(terminal_sampling_guard_recent) ||
    isTRUE(terminal_sampling_guard_recent_enough)
} else {
  isTRUE(terminal_sampling_guard_recent_enough)
}
disc_sampling_diag_emit(
  "sampling_preflight",
  "vb_terminal_guard",
  sprintf(
    paste0(
      "mode=%s median=%s guard_count=%d last_guard_iter=%s lag_iters=%s ",
      "frozen=%s recent=%s recent_enough=%s blocked=%s ",
      "update_iters=%d min_update_iters=%d reason=%s"
    ),
    as.character(DISC_GAMSIG_TERMINAL_SAMPLING_GUARD_MODE),
    ifelse(isTRUE(median_quantile_active), "true", "false"),
    as.integer(state_guard_count),
    if (is.finite(last_state_guard_iter)) as.character(as.integer(last_state_guard_iter)) else "NA",
    if (is.finite(terminal_guard_lag_iters)) as.character(as.integer(terminal_guard_lag_iters)) else "NA",
    ifelse(isTRUE(terminal_sampling_guard_frozen), "true", "false"),
    ifelse(isTRUE(terminal_sampling_guard_recent), "true", "false"),
    ifelse(isTRUE(terminal_sampling_guard_recent_enough), "true", "false"),
    ifelse(isTRUE(terminal_sampling_guard_blocked), "true", "false"),
    as.integer(gamsig_update_iters),
    as.integer(DISC_GAMSIG_MIN_UPDATE_ITERS),
    if (!nzchar(last_state_guard_reason)) "-" else last_state_guard_reason
  )
)
if (terminal_sampling_guard_is_active &&
    state_guard_count >= DISC_GAMSIG_TERMINAL_SAMPLING_GUARD_MIN_GUARD_COUNT &&
    is.finite(last_state_guard_iter) &&
    isTRUE(terminal_sampling_guard_blocked)) {
  guard_msg <- sprintf(
    paste0(
      "terminal sampling guard tripped for p0=%s: guard_count=%d last_guard_iter=%d ",
      "lag_iters=%d frozen=%s recent=%s recent_enough=%s blocked=%s reason=%s"
    ),
    as.character(p0),
    as.integer(state_guard_count),
    as.integer(last_state_guard_iter),
    as.integer(terminal_guard_lag_iters),
    ifelse(isTRUE(terminal_sampling_guard_frozen), "true", "false"),
    ifelse(isTRUE(terminal_sampling_guard_recent), "true", "false"),
    ifelse(isTRUE(terminal_sampling_guard_recent_enough), "true", "false"),
    ifelse(isTRUE(terminal_sampling_guard_blocked), "true", "false"),
    if (!nzchar(last_state_guard_reason)) "-" else last_state_guard_reason
  )
  cat(sprintf("[terminal_sampling_guard] %s\n", guard_msg))
  flush.console()
  stop(guard_msg, call. = FALSE)
}


n.samp <- as.integer(DISC_W_N_SAMP)

if(SIMS){

  print(c(n.samp))
  flush.console()

tictoc::tic("run time")
########################
disc_sampling_diag_start(
  phase = "sampling_start",
  detail = sprintf("n_samp=%d vb_iter=%d", as.integer(n.samp), as.integer(iter))
)
if (verbose) {
  cat(sprintf(
    "Sampling Started: vb_iter=%d vb_seconds=%s n_samp=%d",
    as.integer(iter),
    round(run.time$toc - run.time$tic, 3),
    as.integer(n.samp)
  ), "\n")
}
disc_sampling_diag_mark("sampling_allocate", sprintf("forecast_blocks=%d", length(num_mem)))
samp.uts_ens <- vector("list", length(num_mem))
for (i in seq_along(num_mem)) {
num_cols <- num_mem[i]
samp.uts_ens[[i]] <- array(NA_real_, c(ranges[i], num_cols, n.samp) )
}

samp.sts_ens <- vector("list", length(num_mem))
for (i in seq_along(num_mem)) {
num_cols <- num_mem[i]
samp.sts_ens[[i]] <- array(NA_real_, c(ranges[i], num_cols, n.samp) )
}
########################
samp.gamma = array(NA_real_, c(J+1, n.samp))
samp.sigma = array(NA_real_, c(J+1, n.samp))
samp.uts = array(NA_real_, c(J+1, TT_sub, n.samp))
samp.sts = array(NA_real_, c(J+1, TT_sub, n.samp))
print(c(n.samp))
flush.console()
disc_sampling_diag_mark(
  "sampling_allocate_done",
  sprintf("J=%d TT_sub=%d n_samp=%d", as.integer(J + 1L), as.integer(TT_sub), as.integer(n.samp))
)

disc_sampling_diag_mark("sampling_latent_states", sprintf("j_total=%d", as.integer(J + 1L)))
for (j in 1:(J+1)) {   
    disc_sampling_diag_check("sampling_latent_states", sprintf("j=%d/%d", as.integer(j), as.integer(J + 1L)))
    sts.dummy <- update_sts(y[j,],
                            new.theta.out$exps[j,1:TT_sub], 
                            cur.uts.out$E.inv.uts[j,], 
                            cur.gamsig.out$E.c2.invb.absgam2.sigma[j,], 
                            cur.gamsig.out$E.c.invb.absgam[j,], 
                            cur.gamsig.out$E.c.a.invb.absgam[j,], TT_sub)
    new.sts.out$E.sts[j,] <- sts.dummy$E.sts
    new.sts.out$E.sts2[j,] <- sts.dummy$E.sts2
    new.sts.out$tot.entrop[j,] <-  sts.dummy$tot.entrop
    ########################
    uts.dummy <- update_uts(y[j,],
                            new.theta.out$exps[j,1:TT_sub], 
                            new.theta.out$exps2[j,1:TT_sub], 
                            new.sts.out$E.sts[j,], 
                            new.sts.out$E.sts2[j,], 
                            cur.gamsig.out$E.inv.sigma[j,], 
                            cur.gamsig.out$E.a2.invb.inv.sigma[j,], 
                            cur.gamsig.out$E.invb.inv.sigma[j,], 
                            cur.gamsig.out$E.c.invb.absgam[j,], 
                            cur.gamsig.out$E.c2.invb.absgam2.sigma[j,]) 
    new.uts.out$E.uts[j,] <- uts.dummy$E.uts
    new.uts.out$E.inv.uts[j,] <- uts.dummy$E.inv.uts
    new.uts.out$E.log.uts[j,] <- uts.dummy$E.log.uts
    new.uts.out$tot.entrop[j,] <- uts.dummy$tot.entrop
    ########################
    ########################
    ########################
    ########################
    historical_member_detail <- sprintf("j=%d/%d horizon=history TT_sub=%d", as.integer(j), as.integer(J + 1L), as.integer(TT_sub))
    uts_summary <- disc_sampling_diag_require_numeric(
      "uts.lambda",
      uts.dummy$uts.lambda,
      phase = "sampling_history_gig",
      detail = historical_member_detail
    )
    psi_summary <- disc_sampling_diag_require_numeric(
      "uts.psi",
      uts.dummy$uts.psi,
      phase = "sampling_history_gig",
      detail = historical_member_detail,
      require_positive = TRUE
    )
    chi_summary <- disc_sampling_diag_require_numeric(
      "uts.chi",
      uts.dummy$uts.chi,
      phase = "sampling_history_gig",
      detail = historical_member_detail,
      require_positive = TRUE
    )
    disc_sampling_diag_mark(
      "sampling_history_gig",
      paste(historical_member_detail, uts_summary, psi_summary, chi_summary, sep = " | ")
    )
    samp.uts[j,,] = t(disc_sampling_diag_guarded_eval(
      "sampling_history_gig",
      detail = paste(historical_member_detail, uts_summary, psi_summary, chi_summary, sep = " | "),
      timeout_seconds = DISC_W_SAMPLING_MEMBER_WALLTIME_SECONDS,
      code = sample_gig_devroye_vector(n.samp, uts.dummy$uts.lambda, uts.dummy$uts.psi, uts.dummy$uts.chi)
    ))
    disc_sampling_diag_mark("sampling_history_gig_done", historical_member_detail)
    mu_summary <- disc_sampling_diag_require_numeric(
      "sts.mu",
      sts.dummy$sts.mu,
      phase = "sampling_history_truncnorm",
      detail = historical_member_detail
    )
    sig2_summary <- disc_sampling_diag_require_numeric(
      "sts.sig2",
      sts.dummy$sts.sig2,
      phase = "sampling_history_truncnorm",
      detail = historical_member_detail,
      require_positive = TRUE
    )
    alpha_summary <- disc_sampling_diag_numeric_summary(
      "sts.alpha",
      (0 - as.numeric(sts.dummy$sts.mu)) / sqrt(as.numeric(sts.dummy$sts.sig2))
    )
    disc_sampling_diag_mark(
      "sampling_history_truncnorm",
      paste(historical_member_detail, mu_summary, sig2_summary, alpha_summary, sep = " | ")
    )
    samp.sts[j,,] = t(disc_sampling_diag_guarded_eval(
      "sampling_history_truncnorm",
      detail = paste(historical_member_detail, mu_summary, sig2_summary, alpha_summary, sep = " | "),
      timeout_seconds = DISC_W_SAMPLING_MEMBER_WALLTIME_SECONDS,
      code = sample_truncnorm_icdf(n.samp, TT_sub, sts.dummy$sts.mu, sts.dummy$sts.sig2)
    ))
    sts_draw_summary <- disc_sampling_diag_require_numeric(
      "samp.sts",
      samp.sts[j,,],
      phase = "sampling_history_truncnorm_done",
      detail = historical_member_detail
    )
    disc_sampling_diag_mark(
      "sampling_history_truncnorm_done",
      paste(historical_member_detail, sts_draw_summary, sep = " | ")
    )
    ########################
    ########################
    ########################
    ########################
    if(j==1){
        gamsig.dummy <- update_gamma_sigma(y[j,], 
                                            TT_sub,
                                            PriorGamma[j,],
                                            PriorSigma[j,],
                                            cur.gamsig.out$E.gam[j,], 
                                            cur.gamsig.out$V.gam[j,], 
                                            cur.gamsig.out$E.sigma[j,], 
                                            cur.gamsig.out$V.sigma[j,], 
                                            new.theta.out$exps[j,1:TT_sub], 
                                            new.theta.out$exps2[j,1:TT_sub], 
                                            new.sts.out$E.sts[j,], 
                                            new.sts.out$E.sts2[j,], 
                                            new.uts.out$E.uts[j,], 
                                            new.uts.out$E.inv.uts[j,],
                                            cur.gamsig.out$E.sigma[j,], 
                                            cur.gamsig.out$E.gam[j,],
                                            FALSE,
                                            context_label = sprintf("sampling j=%d climate_center=FALSE", j))    
        new.gamsig.out$E.gam[j,] <- gamsig.dummy$E.gam
        new.gamsig.out$E.sigma[j,] <- gamsig.dummy$E.sigma
        new.gamsig.out$E.inv.sigma[j,] <- gamsig.dummy$E.inv.sigma
        new.gamsig.out$E.c2.invb.absgam2.sigma[j,] <- gamsig.dummy$E.c2.invb.absgam2.sigma
        new.gamsig.out$E.c.invb.absgam[j,] <- gamsig.dummy$E.c.invb.absgam
        new.gamsig.out$E.c.a.invb.absgam[j,] <- gamsig.dummy$E.c.a.invb.absgam
        new.gamsig.out$E.a2.invb.inv.sigma[j,] <- gamsig.dummy$E.a2.invb.inv.sigma
        new.gamsig.out$E.invb.inv.sigma[j,] <- gamsig.dummy$E.invb.inv.sigma
        new.gamsig.out$E.a.invb.inv.sigma[j,] <- gamsig.dummy$E.a.invb.inv.sigma
        new.gamsig.out$E.log.sig.b[j,] <- gamsig.dummy$E.log.sig.b
        new.gamsig.out$E.log.sig[j,] <- gamsig.dummy$E.log.sig
        new.gamsig.out$E.prior.sig.gam[j,] <- gamsig.dummy$E.prior.sig.gam
        new.gamsig.out$entrop[j,] <- gamsig.dummy$entrop
        ########################
        ########################
        theta_s <- gamsig.dummy$E.theta[1]
        theta_g <- gamsig.dummy$E.theta[2]
        # Normal Aproximation
        samp.LD <- rmvnorm(n = n.samp, mean = c(theta_s, theta_g), sigma = gamsig.dummy$Hess.LD)
        if (isTRUE(DISC_W_AL_MODE)) {
          samp.gamma[j,] = rep(0, n.samp)
        } else {
          pi_gamma <- plogis(samp.LD[,2])
          pi_gamma <- pmin(pmax(pi_gamma, 1e-12), 1 - 1e-12)
          samp.gamma[j,] = L + (U - L) * pi_gamma
        }
        samp.sigma[j,] = exp(samp.LD[,1]) 
        ########################
        ########################
    }else{
        k_forecast <- ranges[j-1]
        for (i in 1:num_mem[j-1]) {
            
        member_detail <- sprintf(
          "j=%d/%d member=%d/%d",
          as.integer(j),
          as.integer(J + 1L),
          as.integer(i),
          as.integer(num_mem[j-1])
        )
        disc_sampling_diag_mark("sampling_forecast_member_update_sts", member_detail)
        sts.dummy <- disc_sampling_diag_guarded_eval(
          "sampling_forecast_member_update_sts",
          detail = member_detail,
          code = update_sts(
            y = matrix(ensembles[[j-1]][,i], ncol=1),
            exps = matrix(new.theta.out$exps[j,(TT_sub+1):(TT_sub+k_forecast)], ncol=1),
            inv.uts = matrix(cur.uts.out_f$E.inv.uts[[j-1]][,i], ncol=1),
            c2.invb.absgam2.sigma = cur.gamsig.out$E.c2.invb.absgam2.sigma[j,],
            c.invb.absgam = cur.gamsig.out$E.c.invb.absgam[j,],
            c.a.invb.absgam = cur.gamsig.out$E.c.a.invb.absgam[j,],
            k_forecast
          )
        )

        new.sts.out_f$E.sts[[j-1]][,i] <- sts.dummy$E.sts
        new.sts.out_f$E.sts2[[j-1]][,i] <- sts.dummy$E.sts2
        new.sts.out_f$tot.entrop[[j-1]][i] <-  sts.dummy$tot.entrop
        disc_sampling_diag_mark(
          "sampling_forecast_member_update_sts_done",
          paste(
            member_detail,
            disc_sampling_diag_numeric_summary("sts.mu", sts.dummy$sts.mu),
            disc_sampling_diag_numeric_summary("sts.sig2", sts.dummy$sts.sig2),
            sep = " | "
          )
        )

        disc_sampling_diag_mark("sampling_forecast_member_update_uts", member_detail)
        uts.dummy <- disc_sampling_diag_guarded_eval(
          "sampling_forecast_member_update_uts",
          detail = member_detail,
          code = update_uts(
            y = matrix(ensembles[[j-1]][,i], ncol=1),
            exps = matrix(new.theta.out$exps[j,(T+1):(T+k_forecast)], ncol=1),
            exps2 = matrix(new.theta.out$exps2[j,(T+1):(T+k_forecast)], ncol=1),
            new.sts.out_f$E.sts[[j-1]][,i],
            new.sts.out_f$E.sts2[[j-1]][,i],
            cur.gamsig.out$E.inv.sigma[j,],
            cur.gamsig.out$E.a2.invb.inv.sigma[j,],
            cur.gamsig.out$E.invb.inv.sigma[j,],
            cur.gamsig.out$E.c.invb.absgam[j,],
            cur.gamsig.out$E.c2.invb.absgam2.sigma[j,]
          )
        )

        new.uts.out_f$E.uts[[j-1]][,i] <- uts.dummy$E.uts
        new.uts.out_f$E.inv.uts[[j-1]][,i] <- uts.dummy$E.inv.uts
        new.uts.out_f$E.log.uts[[j-1]][i] <- uts.dummy$E.log.uts
        new.uts.out_f$tot.entrop[[j-1]][i] <- uts.dummy$tot.entrop
        disc_sampling_diag_mark(
          "sampling_forecast_member_update_uts_done",
          paste(
            member_detail,
            disc_sampling_diag_numeric_summary("uts.lambda", uts.dummy$uts.lambda),
            disc_sampling_diag_numeric_summary("uts.psi", uts.dummy$uts.psi),
            disc_sampling_diag_numeric_summary("uts.chi", uts.dummy$uts.chi),
            sep = " | "
          )
        )
        ########################
        ########################
        ########################
        ########################
        disc_sampling_diag_check("sampling_forecast_latent_states", member_detail)
        uts_summary <- disc_sampling_diag_require_numeric(
          "uts.lambda",
          uts.dummy$uts.lambda,
          phase = "sampling_forecast_member_gig",
          detail = member_detail
        )
        psi_summary <- disc_sampling_diag_require_numeric(
          "uts.psi",
          uts.dummy$uts.psi,
          phase = "sampling_forecast_member_gig",
          detail = member_detail,
          require_positive = TRUE
        )
        chi_summary <- disc_sampling_diag_require_numeric(
          "uts.chi",
          uts.dummy$uts.chi,
          phase = "sampling_forecast_member_gig",
          detail = member_detail,
          require_positive = TRUE
        )
        disc_sampling_diag_mark(
          "sampling_forecast_member_gig",
          paste(member_detail, uts_summary, psi_summary, chi_summary, sep = " | ")
        )
        samp.uts_ens[[j-1]][,i,]  = t(disc_sampling_diag_guarded_eval(
          "sampling_forecast_member_gig",
          detail = paste(member_detail, uts_summary, psi_summary, chi_summary, sep = " | "),
          timeout_seconds = DISC_W_SAMPLING_MEMBER_WALLTIME_SECONDS,
          code = sample_gig_devroye_vector(n.samp, uts.dummy$uts.lambda, uts.dummy$uts.psi, uts.dummy$uts.chi)
        ))
        disc_sampling_diag_mark("sampling_forecast_member_gig_done", member_detail)
        mu_summary <- disc_sampling_diag_require_numeric(
          "sts.mu",
          sts.dummy$sts.mu,
          phase = "sampling_forecast_member_truncnorm",
          detail = member_detail
        )
        sig2_summary <- disc_sampling_diag_require_numeric(
          "sts.sig2",
          sts.dummy$sts.sig2,
          phase = "sampling_forecast_member_truncnorm",
          detail = member_detail,
          require_positive = TRUE
        )
        alpha_summary <- disc_sampling_diag_numeric_summary(
          "sts.alpha",
          (0 - as.numeric(sts.dummy$sts.mu)) / sqrt(as.numeric(sts.dummy$sts.sig2))
        )
        disc_sampling_diag_mark(
          "sampling_forecast_member_truncnorm",
          paste(member_detail, mu_summary, sig2_summary, alpha_summary, sep = " | ")
        )
        samp.sts_ens[[j-1]][,i,]  = t(disc_sampling_diag_guarded_eval(
          "sampling_forecast_member_truncnorm",
          detail = paste(member_detail, mu_summary, sig2_summary, alpha_summary, sep = " | "),
          timeout_seconds = DISC_W_SAMPLING_MEMBER_WALLTIME_SECONDS,
          code = sample_truncnorm_icdf(n.samp, k_forecast, sts.dummy$sts.mu, sts.dummy$sts.sig2)
        ))
        sts_member_summary <- disc_sampling_diag_require_numeric(
          "samp.sts_member",
          samp.sts_ens[[j-1]][,i,],
          phase = "sampling_forecast_member_truncnorm_done",
          detail = member_detail
        )
        disc_sampling_diag_mark(
          "sampling_forecast_member_truncnorm_done",
          paste(member_detail, sts_member_summary, sep = " | ")
        )
        ########################
        ########################
        ########################
        ########################
        }

    }
}
disc_sampling_diag_mark("sampling_latent_states_done", sprintf("j_total=%d", as.integer(J + 1L)))

disc_sampling_diag_mark("sampling_gamma_sigma", sprintf("forecast_blocks=%d", as.integer(J)))
    for (j in 2:(J+1)) {  
        disc_sampling_diag_check("sampling_gamma_sigma", sprintf("j=%d/%d", as.integer(j), as.integer(J + 1L)))
        k_forecast <- ranges[j-1]
        gamsig.dummy <- update_gamma_sigma(Y[j,], TT_sub,
                                            PriorGamma[j,],
                                            PriorSigma[j,],
                                            cur.gamsig.out$E.gam[j,], 
                                            cur.gamsig.out$V.gam[j,], 
                                            cur.gamsig.out$E.sigma[j,], 
                                            cur.gamsig.out$V.sigma[j,], 
                                            new.theta.out$exps[j,], 
                                            new.theta.out$exps2[j,], 
                                            new.sts.out$E.sts[j,], 
                                            new.sts.out$E.sts2[j,], 
                                            new.uts.out$E.uts[j,], 
                                            new.uts.out$E.inv.uts[j,],
                                            cur.gamsig.out$E.sigma[j,], 
                                            cur.gamsig.out$E.gam[j,],
                                            TRUE ,
                                            ensembles[[j-1]], 
                                            num_mem[j-1], 
                                            k_forecast,
                                            new.sts.out_f$E.sts[[j-1]],
                                            new.sts.out_f$E.sts2[[j-1]],
                                            new.uts.out_f$E.uts[[j-1]],
                                            new.uts.out_f$E.inv.uts[[j-1]],
                                            context_label = sprintf("sampling j=%d climate_center=TRUE", j))

        new.gamsig.out$E.gam[j,] <- gamsig.dummy$E.gam
        new.gamsig.out$E.sigma[j,] <- gamsig.dummy$E.sigma
        new.gamsig.out$E.inv.sigma[j,] <- gamsig.dummy$E.inv.sigma
        new.gamsig.out$E.c2.invb.absgam2.sigma[j,] <- gamsig.dummy$E.c2.invb.absgam2.sigma
        new.gamsig.out$E.c.invb.absgam[j,] <- gamsig.dummy$E.c.invb.absgam
        new.gamsig.out$E.c.a.invb.absgam[j,] <- gamsig.dummy$E.c.a.invb.absgam
        new.gamsig.out$E.a2.invb.inv.sigma[j,] <- gamsig.dummy$E.a2.invb.inv.sigma
        new.gamsig.out$E.invb.inv.sigma[j,] <- gamsig.dummy$E.invb.inv.sigma
        new.gamsig.out$E.a.invb.inv.sigma[j,] <- gamsig.dummy$E.a.invb.inv.sigma
        new.gamsig.out$E.log.sig.b[j,] <- gamsig.dummy$E.log.sig.b
        new.gamsig.out$E.log.sig[j,] <- gamsig.dummy$E.log.sig
        new.gamsig.out$E.prior.sig.gam[j,] <- gamsig.dummy$E.prior.sig.gam
        new.gamsig.out$entrop[j,] <- gamsig.dummy$entrop
        ########################
        theta_s <- gamsig.dummy$E.theta[1]
        theta_g <- gamsig.dummy$E.theta[2]
        ########################
        ########################
        ########################
        ########################
        # Normal Aproximation
        samp.LD <- rmvnorm(n = n.samp, mean = c(theta_s, theta_g), sigma = gamsig.dummy$Hess.LD)
        if (isTRUE(DISC_W_AL_MODE)) {
          samp.gamma[j,] = rep(0, n.samp)
        } else {
          pi_gamma <- plogis(samp.LD[,2])
          pi_gamma <- pmin(pmax(pi_gamma, 1e-12), 1 - 1e-12)
          samp.gamma[j,] = L + (U - L) * pi_gamma
        }
        samp.sigma[j,] = exp(samp.LD[,1]) 
        ########################
        ########################
        ########################
        ########################
}
disc_sampling_diag_mark("sampling_gamma_sigma_done", sprintf("forecast_blocks=%d", as.integer(J)))

########################
retro_state <- disc_w_prepare_sampling_state(
  sm = new.theta.out$sm,
  sC = new.theta.out$sC,
  TT_expected = TT,
  n_expected = length(m0),
  label = sprintf("retro[p0=%s]", as.character(p0))
)
disc_sampling_diag_mark(
  "sampling_retro_synth",
  sprintf("TT=%d n=%d", as.integer(retro_state$TT), as.integer(retro_state$n))
)
result_retro <- DISC_generate_synth_samples_retro_part(
  n.samp,
  retro_state$TT,
  retro_state$n,
  retro_state$sC,
  retro_state$sm
) 
disc_sampling_diag_mark("sampling_retro_synth_done", sprintf("TT=%d n=%d", as.integer(retro_state$TT), as.integer(retro_state$n)))
########################
result_forecast <- vector("list", length(num_mem))
ks <- 0

disc_sampling_diag_mark("sampling_forecast_synth", sprintf("forecast_blocks=%d", as.integer(J - 1L)))
for (j in 1:(J-1)) {
    disc_sampling_diag_check("sampling_forecast_synth", sprintf("j=%d/%d", as.integer(j), as.integer(J - 1L)))
    ks <- ranges[J-j+1]-ks
    forecast_state <- disc_w_prepare_sampling_state(
      sm = new.theta.out$sm_ens[[j]],
      sC = new.theta.out$sC_ens[[j]],
      TT_expected = ks,
      label = sprintf("forecast[%d][p0=%s]", as.integer(j), as.character(p0))
    )
    result_forecast[[j]] <- DISC_generate_synth_samples_retro_part(
      n.samp,
      forecast_state$TT,
      forecast_state$n,
      forecast_state$sC,
      forecast_state$sm
    ) 
}
disc_sampling_diag_mark("sampling_forecast_synth_done", sprintf("forecast_blocks=%d", as.integer(J - 1L)))

mvnorm_sampler_vectorized <- function(mu, S, n.sample, progress_callback = NULL) {
  p <- nrow(mu)
  T <- ncol(mu)
  samples <- array(0, dim = c(p, T, n.sample))
  for (t in 1:T) {
    if (!is.null(progress_callback)) {
      progress_callback(t, T)
    }
    samples[,t,] <- mvrnorm(n = n.sample, mu = mu[,t], Sigma = S[,,t])
  }  
  return(samples)
}
j <- J

forecast_state <- disc_w_prepare_sampling_state(
  sm = new.theta.out$sm_ens[[j]],
  sC = new.theta.out$sC_ens[[j]],
  label = sprintf("forecast[%d][p0=%s]", as.integer(j), as.character(p0))
)
S <- forecast_state$sC
mu <- forecast_state$sm
disc_sampling_diag_mark("sampling_forecast_mvnorm", sprintf("j=%d T=%d", as.integer(j), as.integer(ncol(mu))))
result_forecast[[j]]  <- list("samp_theta"=mvnorm_sampler_vectorized(
  mu,
  S,
  n.samp,
  progress_callback = function(t, total_t) {
    disc_sampling_diag_check(
      "sampling_forecast_mvnorm",
      sprintf("j=%d t=%d/%d", as.integer(j), as.integer(t), as.integer(total_t))
    )
  }
))
disc_sampling_diag_mark("sampling_forecast_mvnorm_done", sprintf("j=%d T=%d", as.integer(j), as.integer(ncol(mu))))

print(c(n.samp))
flush.console()
disc_sampling_diag_mark("sampling_finalize", sprintf("n_samp=%d", as.integer(n.samp)))
run.time = tictoc::toc(quiet = TRUE)
########################
if (verbose) {
  cat(sprintf("Sampling finished:  %s seconds", round(run.time$toc - run.time$tic, 3)), "\n")
}

disc_w_save_state(p0 = p0, ending = ending, disc_w_paths = disc_w_paths)
}

errors <- new.theta.out$standard_forecast_errors
s <- 0.5*(compute_kl_divergence(t(errors))+estimate_kl_divergence(t(errors)))
######################

# Function to compute JSD for a given sample matrix
compute_jsd <- function(p_sample, gridsize = c(100, 100, 100)) {
  
  # Step 2: Perform KDE on the sample to estimate the density of p
  kde_p <- kde(p_sample, gridsize = gridsize)  # KDE estimation with custom grid size

  # Step 3: Define the grid and evaluate the KDE density
  pdf_p <- kde_p$estimate  # Estimated density of p on the grid
  dim_p <- dim(pdf_p)
  # cat("Dimensions of pdf_p:", dim_p, "\n")  # Print the dimensions of pdf_p

  # Step 4: Define the distribution q (standard multivariate normal)
  mean_q <- rep(0, 3)  # Mean vector of zeros for q
  cov_q <- diag(3)     # Identity matrix as covariance for q

  # Step 5: Evaluate the PDF for q on the same grid as kde_p
  grid_points <- kde_p$eval.points  # Grid points used in kde_p

  # Create a matrix of all grid points where the densities are evaluated
  grid_matrix <- expand.grid(grid_points[[1]], grid_points[[2]], grid_points[[3]])

  # Calculate the density for the standard normal on the same grid
  pdf_q <- dmvnorm(as.matrix(grid_matrix), mean = mean_q, sigma = cov_q)
  pdf_q <- array(pdf_q, dim = dim_p)  # Reshape to match the dimension of pdf_p
  # cat("Dimensions of pdf_q:", dim(pdf_q), "\n")  # Print the dimensions of pdf_q

  # Step 6: Normalize the densities
  pdf_p <- pdf_p / sum(pdf_p)
  pdf_q <- pdf_q / sum(pdf_q)

  # Step 7: Function to compute the KL divergence
  KL.divergence <- function(p, q) {
    epsilon <- 1e-10  # Small value to prevent division by zero or log of zero
    p <- p + epsilon
    q <- q + epsilon
    return(sum(p * log(p / q)))
  }

  # Step 8: Function to compute the Jensen-Shannon divergence
  JSD <- function(p, q) {
    m <- 0.5 * (p + q)
    return(0.5 * KL.divergence(p, m) + 0.5 * KL.divergence(q, m))
  }

  # Step 9: Compute the Jensen-Shannon divergence
  js_divergence <- JSD(pdf_p, pdf_q)
  return(js_divergence)
}

js_divergence <- compute_jsd(t(errors), gridsize = c(100, 100, 100))

######################
######################
######################
print(c(js_divergence, s, elbo, delta))
flush.console()

if (is.nan(s)) {
  print("Assigning Inf to NaN")
  flush.console()
  s <- Inf
}

if (is.nan(js_divergence)) {
  print("Assigning Inf to NaN")
  flush.console()
  js_divergence <- Inf
}

return(js_divergence)
######################
######################
######################
} 

############################################################################################################
############################################################################################################
############# (Discrep, Mem for Trans, Cov, Trans rate, Mem for Forecast)   
# lower_bounds <- c(0.999, 0.01)   
# initial_delta <- c(0.999,0.9999)

initial_delta   <- DISC_W_INITIAL_DELTA
# initial_delta <- c(df_t  , df_s1 , df_s2 , df_s67, df.discrep, lambda)

upper_bounds <- c(rep(0.985, (length(initial_delta)-1)), 1.0e-6)   
upper_bounds <- rep(0.9999999, length(initial_delta))  

# -2416.920
# -2427.511


opts <- list("algorithm" = "NLOPT_LN_BOBYQA",  # Using a derivative-free algorithm
             "xtol_rel" = 1.0e-6,
             "maxeval" = 1000)

objective_deltas_min <- function(delta) {
  objective_deltas(delta, DISC_W_SIMS_ENABLED, DISC_W_USE_COVARIATES)  # Minimize the negative of the original function
}

# result <- nloptr(x0 = initial_delta,
#                  eval_f = objective_deltas_min,  # Objective function
#                  lb = lower_bounds,
#                  ub = upper_bounds,
#                  opts = opts)
# d = as.numeric(c(result$solution))
# print(result)                                

d <- initial_delta
objective_deltas(d, DISC_W_SIMS_ENABLED, DISC_W_USE_COVARIATES);
###########################################################################################################################
