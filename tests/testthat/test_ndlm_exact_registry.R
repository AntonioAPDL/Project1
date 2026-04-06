source(testthat::test_path('..', '..', 'R', 'unified', 'families', 'ndlm_main', '00_constants.R'))
source(testthat::test_path('..', '..', 'R', 'unified', 'families', 'ndlm_main', '03_vb_updates.R'))
source(testthat::test_path('..', '..', 'R', 'unified', 'families', 'ndlm_main', '07_state_registry.R'))

make_registry_inputs <- function() {
  list(
    y = rep(0, 10),
    retros = list(usgs = rep(0, 10), nws = rep(0, 10), glofas = rep(0, 10)),
    X = matrix(0, nrow = 10, ncol = 5),
    X_future = matrix(0, nrow = 7, ncol = 5),
    T = 10L,
    forecast = list(
      nws = rep(0, 7),
      glofas = rep(0, 5),
      nws_members = matrix(0, nrow = 7, ncol = 3),
      glofas_members = matrix(c(rep(0, 15), rep(NA, 6)), nrow = 7, ncol = 3),
      K = 7L,
      K_overlap = 5L,
      K_max = 7L,
      K_vec = c(nws = 7L, glofas = 5L),
      K_cap = 7L,
      nws_len = 7L,
      glofas_len = 5L
    )
  )
}

test_that('ndlm exact registry encodes drop and keep state dimensions correctly', {
  inputs <- make_registry_inputs()

  Sys.setenv(NDLM_FORECAST_TRANSFER_MODE = 'drop')
  drop_constants <- ndlm_theory_constants(seed = 777L)
  drop_reg <- ndlm_exact_build_registry(inputs, drop_constants)
  expect_equal(as.integer(drop_reg$state_dim_by_lead$state_dim), c(21L, 21L, 21L, 21L, 21L, 14L, 14L))

  Sys.setenv(NDLM_FORECAST_TRANSFER_MODE = 'keep')
  keep_constants <- ndlm_theory_constants(seed = 777L)
  keep_reg <- ndlm_exact_build_registry(inputs, keep_constants)
  expect_equal(as.integer(keep_reg$state_dim_by_lead$state_dim), c(27L, 27L, 27L, 27L, 27L, 20L, 20L))
})

test_that('ndlm exact registry exposes lead-specific historical-to-forecast index vectors', {
  inputs <- make_registry_inputs()

  Sys.setenv(NDLM_FORECAST_TRANSFER_MODE = 'drop')
  drop_constants <- ndlm_theory_constants(seed = 777L)
  drop_reg <- ndlm_exact_build_registry(inputs, drop_constants)
  expect_equal(
    drop_reg$lead_specs[[1L]]$hist_to_fore_idx,
    c(drop_reg$idx_hist$theta, drop_reg$idx_hist$delta_glofas, drop_reg$idx_hist$delta_nws)
  )
  expect_equal(
    drop_reg$lead_specs[[6L]]$hist_to_fore_idx,
    c(drop_reg$idx_hist$theta, drop_reg$idx_hist$delta_nws)
  )

  Sys.setenv(NDLM_FORECAST_TRANSFER_MODE = 'keep')
  keep_constants <- ndlm_theory_constants(seed = 777L)
  keep_reg <- ndlm_exact_build_registry(inputs, keep_constants)
  expect_equal(
    keep_reg$lead_specs[[1L]]$hist_to_fore_idx,
    c(keep_reg$idx_hist$theta, keep_reg$idx_hist$transfer, keep_reg$idx_hist$delta_glofas, keep_reg$idx_hist$delta_nws)
  )
  expect_equal(
    keep_reg$lead_specs[[6L]]$hist_to_fore_idx,
    c(keep_reg$idx_hist$theta, keep_reg$idx_hist$transfer, keep_reg$idx_hist$delta_nws)
  )
})

test_that('ndlm exact registry projection vectors satisfy source identity', {
  inputs <- make_registry_inputs()
  Sys.setenv(NDLM_FORECAST_TRANSFER_MODE = 'keep')
  constants <- ndlm_theory_constants(seed = 777L)
  reg <- ndlm_exact_build_registry(inputs, constants)

  for (spec in reg$lead_specs) {
    if ('glofas' %in% spec$active_sources) {
      expect_equal(spec$h_glofas - spec$h_usgs, spec$h_delta_glofas, tolerance = 1e-12)
    }
    if ('nws' %in% spec$active_sources) {
      expect_equal(spec$h_nws - spec$h_usgs, spec$h_delta_nws, tolerance = 1e-12)
    }
  }
})
