source(testthat::test_path('..', '..', 'R', 'unified', 'families', 'shared_input_helpers.R'))
for (f in c(
  '00_constants.R',
  '01_inputs.R',
  '02_model_spec.R',
  '03_vb_updates.R',
  '07_state_registry.R',
  '08_vb_cavi_exact.R',
  '04_elbo.R',
  '05_fitloop.R',
  '06_save_state.R'
)) {
  source(testthat::test_path('..', '..', 'R', 'unified', 'families', 'ndlm_main', f))
}

make_exact_fit_inputs <- function() {
  set.seed(42)
  Tn <- 36L
  K_nws <- 6L
  K_glofas <- 4L
  K_max <- max(K_nws, K_glofas)
  X <- matrix(rnorm(Tn * 5), nrow = Tn, ncol = 5)
  X_future <- matrix(rnorm(K_max * 5), nrow = K_max, ncol = 5)
  trend <- seq(0.1, 1.0, length.out = Tn)
  season <- sin(seq_len(Tn) / 5)
  y <- trend + 0.2 * season + rnorm(Tn, sd = 0.08)
  ret_nws <- y + 0.05 + rnorm(Tn, sd = 0.09)
  ret_glofas <- y - 0.04 + rnorm(Tn, sd = 0.10)
  fc_nws_mean <- y[Tn] + cumsum(rnorm(K_nws, 0.01, 0.07)) + 0.05
  fc_glofas_mean <- y[Tn] + cumsum(rnorm(K_glofas, 0.01, 0.08)) - 0.02
  n_members <- 3L
  nws_members <- matrix(NA_real_, nrow = K_max, ncol = n_members)
  glofas_members <- matrix(NA_real_, nrow = K_max, ncol = n_members)
  for (k in seq_len(K_nws)) nws_members[k, ] <- fc_nws_mean[k] + rnorm(n_members, sd = 0.06)
  for (k in seq_len(K_glofas)) glofas_members[k, ] <- fc_glofas_mean[k] + rnorm(n_members, sd = 0.07)
  list(
    y = y,
    retros = list(usgs = y, nws = ret_nws, glofas = ret_glofas),
    X = X,
    X_future = X_future,
    T = Tn,
    forecast = list(
      nws = fc_nws_mean,
      glofas = fc_glofas_mean,
      nws_members = nws_members,
      glofas_members = glofas_members,
      K = K_max,
      K_overlap = min(K_nws, K_glofas),
      K_max = K_max,
      K_vec = c(nws = K_nws, glofas = K_glofas),
      K_cap = K_max,
      nws_len = K_nws,
      glofas_len = K_glofas,
      forecast_dates = seq.Date(as.Date('2021-01-01'), by = 'day', length.out = K_max)
    )
  )
}

test_that('ndlm exact fit returns coherent drop and keep artifacts', {
  old_env <- Sys.getenv(c(
    'NDLM_KALMAN_BACKEND',
    'NDLM_GAMSIG_MAX_ITER',
    'NDLM_GAMSIG_MIN_TOTAL_ITERS',
    'NDLM_GAMSIG_ELBO_TOL',
    'NDLM_GAMSIG_ELBO_REL_TOL',
    'NDLM_POSTERIOR_DRAWS',
    'NDLM_FORECAST_TRANSFER_MODE'
  ), unset = NA_character_)
  on.exit({
    for (nm in names(old_env)) {
      if (is.na(old_env[[nm]])) Sys.unsetenv(nm) else do.call(Sys.setenv, stats::setNames(list(old_env[[nm]]), nm))
    }
  }, add = TRUE)

  Sys.setenv(
    NDLM_KALMAN_BACKEND = 'r',
    NDLM_GAMSIG_MAX_ITER = '4',
    NDLM_GAMSIG_MIN_TOTAL_ITERS = '2',
    NDLM_GAMSIG_ELBO_TOL = '1e-5',
    NDLM_GAMSIG_ELBO_REL_TOL = '1e-4',
    NDLM_POSTERIOR_DRAWS = '8'
  )
  inputs <- make_exact_fit_inputs()

  Sys.setenv(NDLM_FORECAST_TRANSFER_MODE = 'drop')
  drop_constants <- ndlm_theory_constants(seed = 777L)
  out_drop <- ndlm_theory_fit(inputs, drop_constants)

  Sys.setenv(NDLM_FORECAST_TRANSFER_MODE = 'keep')
  keep_constants <- ndlm_theory_constants(seed = 777L)
  out_keep <- ndlm_theory_fit(inputs, keep_constants)

  expect_equal(out_drop$K_max, inputs$forecast$K_max)
  expect_equal(out_keep$K_max, inputs$forecast$K_max)
  expect_equal(nrow(out_drop$fit_diagnostics$forecast_identity), inputs$forecast$K_max)
  expect_equal(nrow(out_keep$fit_diagnostics$forecast_identity), inputs$forecast$K_max)
  expect_true(max(abs(out_drop$fit_diagnostics$forecast_identity$identity_err_glofas), na.rm = TRUE) < 1e-6)
  expect_true(max(abs(out_keep$fit_diagnostics$forecast_identity$identity_err_glofas), na.rm = TRUE) < 1e-6)
  expect_equal(out_drop$state_dim_by_lead$state_dim[[1]], 21L)
  expect_equal(out_keep$state_dim_by_lead$state_dim[[1]], 27L)
  expect_equal(length(out_drop$forecast_cov_factors), inputs$forecast$K_max)
  expect_equal(length(out_keep$forecast_cov_factors), inputs$forecast$K_max)
  expect_true(is.data.frame(out_drop$forecast_cov_diagnostics))
  expect_true(is.data.frame(out_keep$forecast_cov_diagnostics))
  expect_equal(nrow(out_drop$forecast_cov_diagnostics), inputs$forecast$K_max)
  expect_equal(nrow(out_keep$forecast_cov_diagnostics), inputs$forecast$K_max)
  expect_true(all(is.finite(out_drop$forecast_cov_diagnostics$trace_Q_anchor)))
  expect_true(all(is.finite(out_keep$forecast_cov_diagnostics$trace_Q_anchor)))
  expect_true(is.list(out_drop$state_registry))
  expect_true(is.list(out_keep$state_registry))
  expect_equal(out_drop$forecast_prior$anchor_mode, "terminal_Q_hist")
  expect_equal(out_keep$forecast_prior$anchor_mode, "terminal_Q_hist")
  expect_equal(out_drop$forecast_prior$epsilon0, inputs$T)
  expect_equal(out_keep$forecast_prior$epsilon0, inputs$T)
  expect_equal(out_drop$forecast_prior$c_factor, 1)
  expect_equal(out_keep$forecast_prior$c_factor, 1)
  expect_equal(ncol(out_drop$new_theta$forecast_mean_draws_loglog1p), inputs$forecast$K_max)
  expect_equal(ncol(out_keep$new_theta$forecast_mean_draws_loglog1p), inputs$forecast$K_max)
})

test_that('ndlm exact prior anchor uses terminal Q_T and resolves epsilon null to T', {
  old_env <- Sys.getenv(c(
    'NDLM_KALMAN_BACKEND',
    'NDLM_GAMSIG_MAX_ITER',
    'NDLM_GAMSIG_MIN_TOTAL_ITERS',
    'NDLM_POSTERIOR_DRAWS',
    'NDLM_FORECAST_TRANSFER_MODE',
    'NDLM_FORECAST_IW_C_FACTOR',
    'NDLM_FORECAST_IW_EPSILON0'
  ), unset = NA_character_)
  on.exit({
    for (nm in names(old_env)) {
      if (is.na(old_env[[nm]])) Sys.unsetenv(nm) else do.call(Sys.setenv, stats::setNames(list(old_env[[nm]]), nm))
    }
  }, add = TRUE)

  Sys.setenv(
    NDLM_KALMAN_BACKEND = 'r',
    NDLM_GAMSIG_MAX_ITER = '2',
    NDLM_GAMSIG_MIN_TOTAL_ITERS = '1',
    NDLM_POSTERIOR_DRAWS = '4',
    NDLM_FORECAST_TRANSFER_MODE = 'drop',
    NDLM_FORECAST_IW_C_FACTOR = '1'
  )
  Sys.unsetenv('NDLM_FORECAST_IW_EPSILON0')

  inputs <- make_exact_fit_inputs()
  constants <- ndlm_theory_constants(seed = 777L)
  out <- ndlm_theory_fit(inputs, constants)

  expect_equal(out$forecast_prior$epsilon0, inputs$T)
  expect_equal(out$forecast_prior$c_factor, 1)
  expect_true(all(is.finite(out$forecast_cov_diagnostics$trace_W_T_k)))
  expect_true(all(is.finite(out$forecast_cov_diagnostics$trace_S0)))

  lead1 <- out$forecast_cov_factors[[1L]]
  d1 <- lead1$state_dim[[1L]]
  expect_equal(
    lead1$trace_S0[[1L]] / (lead1$nu0[[1L]] - d1 - 1),
    lead1$trace_W_T_k[[1L]],
    tolerance = 1e-6
  )
})
