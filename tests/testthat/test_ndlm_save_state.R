source(testthat::test_path("..", "..", "R", "unified", "families", "ndlm_main", "04_elbo.R"))
source(testthat::test_path("..", "..", "R", "unified", "families", "ndlm_main", "06_save_state.R"))

test_that("ndlm compatibility output packs fit diagnostics into theory state", {
  fit_result <- list(
    samp_sigma = matrix(1, nrow = 1, ncol = 2),
    samp_theta = list(samp_theta = array(0, dim = c(3, 4, 2))),
    samp_theta_ens = list(list(samp_theta = array(0, dim = c(7, 2, 2))), list(samp_theta = array(0, dim = c(7, 1, 2)))),
    new_theta = list(
      sm = matrix(0, nrow = 3, ncol = 4),
      sC = array(0, dim = c(3, 3, 4)),
      exps = matrix(0, nrow = 2, ncol = 4),
      standard_forecast_errors = matrix(0, nrow = 1, ncol = 3),
      sm_ens = list(matrix(0, nrow = 7, ncol = 2), matrix(0, nrow = 7, ncol = 1)),
      sC_ens = list(array(0, dim = c(7, 7, 2)), array(0, dim = c(7, 7, 1)))
    ),
    seq_sigma = c(1, 0.9),
    seq_elbo = c(NA_real_, 1.23),
    delta = c(0.1, 0),
    sigma = 0.9,
    sigma_by_source = c(usgs = 0.9, nws = 1.1, glofas = 0.8),
    sigma_mean = 0.9333333,
    w_hist = 0.01,
    w_fore = 0.02,
    discount_factors = c(df_t = 0.95, df_s1 = 0.98, df_s2 = 0.98, df_s67 = 0.98, df_discrep = 0.98, lambda = 0.99),
    T = 4L,
    K = 3L,
    K_overlap = 2L,
    K_max = 3L,
    K_vec = c(nws = 2L, glofas = 3L),
    segment_lengths = c(overlap = 2L, extension = 1L),
    extension_source = "glofas",
    bridge_source = "nws",
    active_set_by_lead = data.frame(lead = 1:3, active_nws = c(1, 1, 0), active_glofas = c(1, 1, 1), active_count = c(2, 2, 1)),
    state_dim_by_lead = data.frame(lead = 1:3, state_dim = c(14, 14, 7)),
    forecast_prior = list(c_factor = 1, epsilon0 = 12, dof_offset = 4, scale_mult = 1.5, anchor_mode = "terminal_Q_hist", trace_W_T_hist = 9.5),
    forecast_cov_diagnostics = data.frame(
      lead = 1:3,
      trace_Q_anchor = c(1, 2, 3),
      stringsAsFactors = FALSE
    ),
    covariance_diagnostics = data.frame(object = "smooth_cov", n_slices = 4L),
    fit_diagnostics = list(
      y_observed = c(1, 2, 3, 4),
      y_predicted_one_step = c(1.1, 2.1, 3.1, 4.1),
      y_filtered = c(1.0, 2.0, 3.0, 4.0),
      y_smoothed = c(0.9, 1.9, 2.9, 3.9)
    ),
    K_cap = 1080L,
    nws_len = 2L,
    glofas_len = 3L
  )

  out_env <- ndlm_theory_pack_compat_outputs(fit_result)
  expect_true(exists("ndlm_main_theory_state", envir = out_env, inherits = FALSE))
  st <- get("ndlm_main_theory_state", envir = out_env, inherits = FALSE)
  expect_true(is.list(st$fit_diagnostics))
  expect_equal(as.numeric(st$fit_diagnostics$y_smoothed), c(0.9, 1.9, 2.9, 3.9))
  expect_equal(as.numeric(st$sigma_by_source[c("usgs", "nws", "glofas")]), c(0.9, 1.1, 0.8))
  expect_equal(st$forecast_prior$anchor_mode, "terminal_Q_hist")
  expect_equal(st$forecast_prior$dof_offset, 4)
  expect_equal(st$forecast_prior$scale_mult, 1.5)
  expect_true(is.data.frame(st$forecast_cov_diagnostics))
  expect_equal(as.numeric(st$forecast_cov_diagnostics$trace_Q_anchor), c(1, 2, 3))
})
