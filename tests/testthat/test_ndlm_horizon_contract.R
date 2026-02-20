source(testthat::test_path("..", "..", "R", "unified", "ndlm_post_diagnostics.R"))

make_ndlm_obj <- function(K = 10L, Tn = 120L) {
  list(
    sm = matrix(rnorm(26L * Tn), nrow = 26L, ncol = Tn),
    sC = array(diag(26L), dim = c(26L, 26L, Tn)),
    exps = matrix(rnorm(2L * Tn), nrow = 2L, ncol = Tn),
    standard_forecast_errors = matrix(rnorm(K), nrow = 1L, ncol = K),
    sm_ens = list(
      matrix(rnorm(7L * K), nrow = 7L, ncol = K),
      matrix(rnorm(7L * K), nrow = 7L, ncol = K)
    ),
    sC_ens = list(
      array(diag(7L), dim = c(7L, 7L, K)),
      array(diag(7L), dim = c(7L, 7L, K))
    )
  )
}

test_that("NDLM horizon contract uses shared min horizon rule", {
  set.seed(1)
  ndlm_obj <- make_ndlm_obj(K = 10L, Tn = 120L)
  state_obj <- list(K = 10L, K_cap = 14L, nws_len = 10L, glofas_len = 28L)

  chk <- unified_ndlm_diag_build_horizon_contract(
    ndlm_obj = ndlm_obj,
    state_obj = state_obj,
    retros_n = 120L,
    nws_n = 10L,
    glofas_n = 28L
  )

  expect_true(all(chk$status == "pass"))
  expect_equal(chk$expected_horizon[chk$figure_or_series == "ndlm_shared_forecast_horizon"], 10L)
  expect_equal(chk$actual_horizon[chk$figure_or_series == "ndlm_shared_forecast_horizon"], 10L)
})

test_that("NDLM horizon contract flags mismatched segment horizon", {
  set.seed(2)
  ndlm_obj <- make_ndlm_obj(K = 10L, Tn = 120L)
  ndlm_obj$sm_ens[[2L]] <- matrix(rnorm(7L * 8L), nrow = 7L, ncol = 8L)
  state_obj <- list(K = 10L, K_cap = 14L, nws_len = 10L, glofas_len = 28L)

  chk <- unified_ndlm_diag_build_horizon_contract(
    ndlm_obj = ndlm_obj,
    state_obj = state_obj,
    retros_n = 120L,
    nws_n = 10L,
    glofas_n = 28L
  )

  row <- chk[chk$figure_or_series == "ndlm_sm_ens_segment_horizon", , drop = FALSE]
  expect_equal(row$status[[1L]], "mismatch")
})

test_that("NDLM diagnostics bundle strict mode passes for coherent inputs", {
  skip_if_not_installed("utils")

  set.seed(3)
  td <- tempfile("ndlm_diag_ok_")
  dir.create(td, recursive = TRUE, showWarnings = FALSE)
  on.exit(unlink(td, recursive = TRUE, force = TRUE), add = TRUE)

  retros <- data.frame(Date = as.character(seq.Date(as.Date("2022-01-01"), by = "day", length.out = 120L)), USGS = rnorm(120L))
  nws <- data.frame(Date = as.character(seq.Date(as.Date("2022-05-01"), by = "day", length.out = 10L)), nws = rnorm(10L))
  glofas <- data.frame(target_date = as.character(seq.Date(as.Date("2022-05-01"), by = "day", length.out = 28L)), glofas = rnorm(28L))

  retros_path <- file.path(td, "retros.csv")
  nws_path <- file.path(td, "nws.csv")
  glofas_path <- file.path(td, "glofas.csv")
  utils::write.csv(retros, retros_path, row.names = FALSE)
  utils::write.csv(nws, nws_path, row.names = FALSE)
  utils::write.csv(glofas, glofas_path, row.names = FALSE)

  ndlm_obj <- make_ndlm_obj(K = 10L, Tn = 120L)
  ndlm_main_theory_state <- list(K = 10L, K_cap = 14L, nws_len = 10L, glofas_len = 28L)
  save(
    ndlm_obj,
    ndlm_main_theory_state,
    file = file.path(td, "ndlm.rdata")
  )

  # Match object names expected by diagnostics loader.
  rename_env <- new.env(parent = emptyenv())
  load(file.path(td, "ndlm.rdata"), envir = rename_env)
  assign("new.theta.out_50_NDLM_synth_DISC", get("ndlm_obj", envir = rename_env), envir = rename_env)
  assign("ndlm_main_theory_state", get("ndlm_main_theory_state", envir = rename_env), envir = rename_env)
  save(list = c("new.theta.out_50_NDLM_synth_DISC", "ndlm_main_theory_state"), file = file.path(td, "ndlm_bundle.rdata"), envir = rename_env)

  log_path <- file.path(td, "ndlm.log")
  writeLines(
    c(
      "[gamsig_progress] family=ndlm_main p0=NA iter=1 elbo=-10.0 crit_elbo=NA sigma_exp=1.0 gamma_exp=NA state_norm_sq=12.0 w_hist=0.1 w_fore=0.2",
      "[gamsig_progress] family=ndlm_main p0=NA iter=2 elbo=-9.5 crit_elbo=0.5 sigma_exp=0.9 gamma_exp=NA state_norm_sq=11.5 w_hist=0.1 w_fore=0.2"
    ),
    con = log_path
  )

  out <- unified_generate_ndlm_post_diagnostics(
    run_root = td,
    ndlm_rdata_path = file.path(td, "ndlm_bundle.rdata"),
    retros_csv_path = retros_path,
    nws_csv_path = nws_path,
    glofas_csv_path = glofas_path,
    fit_log_path = log_path,
    output_dir = file.path(td, "diag"),
    strict_contract = TRUE
  )

  expect_equal(out$status, "pass")
  expect_true(file.exists(file.path(td, "diag", "ndlm_plot_contract_check.csv")))
  expect_true(file.exists(file.path(td, "diag", "ndlm_fit_vs_observed_coverage.csv")))
})

test_that("NDLM diagnostics bundle strict mode fails on contract mismatch", {
  set.seed(4)
  td <- tempfile("ndlm_diag_fail_")
  dir.create(td, recursive = TRUE, showWarnings = FALSE)
  on.exit(unlink(td, recursive = TRUE, force = TRUE), add = TRUE)

  retros <- data.frame(Date = as.character(seq.Date(as.Date("2022-01-01"), by = "day", length.out = 60L)), USGS = rnorm(60L))
  nws <- data.frame(Date = as.character(seq.Date(as.Date("2022-03-01"), by = "day", length.out = 10L)), nws = rnorm(10L))
  glofas <- data.frame(target_date = as.character(seq.Date(as.Date("2022-03-01"), by = "day", length.out = 28L)), glofas = rnorm(28L))

  retros_path <- file.path(td, "retros.csv")
  nws_path <- file.path(td, "nws.csv")
  glofas_path <- file.path(td, "glofas.csv")
  utils::write.csv(retros, retros_path, row.names = FALSE)
  utils::write.csv(nws, nws_path, row.names = FALSE)
  utils::write.csv(glofas, glofas_path, row.names = FALSE)

  ndlm_obj <- make_ndlm_obj(K = 9L, Tn = 60L)
  ndlm_main_theory_state <- list(K = 10L, K_cap = 14L, nws_len = 10L, glofas_len = 28L)

  diag_env <- new.env(parent = emptyenv())
  assign("new.theta.out_50_NDLM_synth_DISC", ndlm_obj, envir = diag_env)
  assign("ndlm_main_theory_state", ndlm_main_theory_state, envir = diag_env)
  save(list = c("new.theta.out_50_NDLM_synth_DISC", "ndlm_main_theory_state"), file = file.path(td, "ndlm_bundle.rdata"), envir = diag_env)

  expect_error(
    unified_generate_ndlm_post_diagnostics(
      run_root = td,
      ndlm_rdata_path = file.path(td, "ndlm_bundle.rdata"),
      retros_csv_path = retros_path,
      nws_csv_path = nws_path,
      glofas_csv_path = glofas_path,
      fit_log_path = "",
      output_dir = file.path(td, "diag"),
      strict_contract = TRUE
    ),
    "\\[NDLM_HORIZON_CONTRACT\\]"
  )
})
