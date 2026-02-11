univar_theory_constants <- function(q_num, seed = 777L) {
  q_num <- as.integer(q_num)
  p0 <- max(min(q_num / 100, 0.995), 0.005)

  list(
    q_num = q_num,
    q_label = sprintf("%02d", q_num),
    p0 = p0,
    state_dim = 26L,
    active_dim = 6L,
    n_iter = 12L,
    n_draws = 32L,
    seed = as.integer(seed),
    a_sigma = 2.0,
    b_sigma = 2.0,
    m_gamma = 0.0,
    s_gamma = 1.0,
    nu_gamma = 6.0
  )
}
