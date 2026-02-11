ndlm_theory_constants <- function(seed = 777L) {
  list(
    state_dim = 26L,
    active_hist_dim = 14L,
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
