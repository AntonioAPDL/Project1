ndlm_theory_constants <- function(seed = 777L) {
  env_int <- function(name, default, min_val = 1L) {
    raw <- suppressWarnings(as.integer(Sys.getenv(name, as.character(default))))
    if (!is.finite(raw)) raw <- as.integer(default)
    raw <- as.integer(raw)
    if (is.finite(min_val)) raw <- max(raw, as.integer(min_val))
    raw
  }
  env_num <- function(name, default, min_val = NA_real_) {
    raw <- suppressWarnings(as.numeric(Sys.getenv(name, as.character(default))))
    if (!is.finite(raw)) raw <- as.numeric(default)
    if (is.finite(min_val)) raw <- max(raw, as.numeric(min_val))
    raw
  }
  env_prob <- function(name, default, min_val = 1e-8, max_val = 1 - 1e-8) {
    raw <- suppressWarnings(as.numeric(Sys.getenv(name, as.character(default))))
    if (!is.finite(raw)) raw <- as.numeric(default)
    raw <- max(raw, as.numeric(min_val))
    raw <- min(raw, as.numeric(max_val))
    raw
  }

  horizon_cap <- suppressWarnings(as.integer(Sys.getenv("NDLM_FORECAST_HORIZON_CAP", "1080")))
  if (!is.finite(horizon_cap) || horizon_cap <= 0L) {
    horizon_cap <- 1080L
  }
  kalman_backend <- tolower(trimws(Sys.getenv("NDLM_KALMAN_BACKEND", "cpp")))
  if (!(kalman_backend %in% c("r", "cpp"))) {
    kalman_backend <- "cpp"
  }

  max_iter <- env_int("NDLM_GAMSIG_MAX_ITER", default = 100L, min_val = 1L)
  min_total_iters <- env_int("NDLM_GAMSIG_MIN_TOTAL_ITERS", default = 50L, min_val = 1L)
  min_total_iters <- min(min_total_iters, max_iter)
  convergence_tol <- env_num("NDLM_GAMSIG_CONVERGENCE_TOL", default = 1e-6, min_val = 1e-12)
  elbo_tol <- env_num("NDLM_GAMSIG_ELBO_TOL", default = convergence_tol, min_val = 1e-12)
  elbo_rel_tol <- env_num("NDLM_GAMSIG_ELBO_REL_TOL", default = 2.5e-4, min_val = 1e-12)
  n_draws <- env_int("NDLM_POSTERIOR_DRAWS", default = 48L, min_val = 1L)
  df_t <- env_prob("NDLM_DF_T", default = 0.95)
  df_s1 <- env_prob("NDLM_DF_S1", default = 0.98)
  df_s2 <- env_prob("NDLM_DF_S2", default = 0.98)
  df_s67 <- env_prob("NDLM_DF_S67", default = 0.98)
  df_discrep <- env_prob("NDLM_DF_DISCREP", default = 0.98)
  lambda <- env_prob("NDLM_LAMBDA", default = 0.99)
  df_trans <- env_prob("NDLM_DF_TRANS", default = 0.99999999)
  df_covs <- env_prob("NDLM_DF_COVS", default = 0.99999)

  list(
    state_dim = 26L,
    active_hist_dim = 14L,
    forecast_horizon_cap = horizon_cap,
    kalman_backend = kalman_backend,
    ensemble_block_dim = 7L,
    max_iter = max_iter,
    min_total_iters = min_total_iters,
    convergence_tol = convergence_tol,
    convergence = list(
      elbo_tol = elbo_tol,
      elbo_rel_tol = elbo_rel_tol
    ),
    n_draws = n_draws,
    seed = as.integer(seed),
    a_sigma = 2.0,
    b_sigma = 2.0,
    df_t = df_t,
    df_s1 = df_s1,
    df_s2 = df_s2,
    df_s67 = df_s67,
    df_discrep = df_discrep,
    lambda = lambda,
    df_trans = df_trans,
    df_covs = df_covs,
    p0 = 0.5
  )
}
