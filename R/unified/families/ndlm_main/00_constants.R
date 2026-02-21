ndlm_theory_constants <- function(seed = 777L) {
  horizon_cap <- suppressWarnings(as.integer(Sys.getenv("NDLM_FORECAST_HORIZON_CAP", "1080")))
  if (!is.finite(horizon_cap) || horizon_cap <= 0L) {
    horizon_cap <- 1080L
  }
  kalman_backend <- tolower(trimws(Sys.getenv("NDLM_KALMAN_BACKEND", "cpp")))
  if (!(kalman_backend %in% c("r", "cpp"))) {
    kalman_backend <- "cpp"
  }
  list(
    state_dim = 26L,
    active_hist_dim = 14L,
    forecast_horizon_cap = horizon_cap,
    kalman_backend = kalman_backend,
    ensemble_block_dim = 7L,
    n_iter = 16L,
    n_draws = 48L,
    seed = as.integer(seed),
    a_sigma = 2.0,
    b_sigma = 2.0,
    a_w_hist = 2.0,
    b_w_hist = 0.2,
    a_w_fore = 2.0,
    b_w_fore = 0.2,
    p0 = 0.5
  )
}
