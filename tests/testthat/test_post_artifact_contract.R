source(testthat::test_path("..", "..", "R", "unified", "post_artifact_contract.R"))

create_dummy_png <- function(path) {
  grDevices::png(path, width = 200, height = 200)
  op <- graphics::par(mar = c(1, 1, 1, 1))
  on.exit({
    graphics::par(op)
    grDevices::dev.off()
  }, add = FALSE)
  graphics::plot.new()
  graphics::text(0.5, 0.5, "figure")
  invisible(TRUE)
}

write_multivar_component_diagnostics <- function(outputs_dir, contract_overrides = list()) {
  csv_names <- c(
    "multivar_trace_summary_q50.csv",
    "multivar_forecast_window_q50_summary.csv",
    "multivar_forecast_window_q50_metrics.csv",
    "multivar_transfer_state_window_q50.csv",
    "multivar_transfer_coefficients_window_q50.csv",
    "multivar_transfer_state_contract_q50.csv",
    "multivar_transfer_identity_check_q50.csv",
    "multivar_vb_usgs_location_quantiles_cutoff_window.csv",
    "multivar_vb_usgs_location_quantile_summary.csv"
  )
  for (name in csv_names) {
    write.csv(data.frame(x = 1), file.path(outputs_dir, name), row.names = FALSE)
  }

  fig_names <- c(
    "multivar_elbo_trace_q50.png",
    "multivar_sigma_traces_q50.png",
    "multivar_gamma_traces_q50.png",
    "multivar_transfer_zeta_window_q50.png",
    "multivar_transfer_coefficients_window_q50.png",
    "multivar_transfer_observation_decomposition_q50.png",
    "multivar_transfer_source_mu_window_q50.png",
    "multivar_transfer_discrepancy_identity_q50.png",
    "multivar_vb_usgs_location_quantiles_cutoff_window.png"
  )
  for (name in fig_names) {
    create_dummy_png(file.path(outputs_dir, name))
  }

  contract <- modifyList(
    list(
      transfer_mode = "keep",
      forecast_has_transfer = TRUE,
      n_forecast_rows = 30L,
      finite_zeta_forecast = 30L,
      finite_mu_without_transfer_forecast = 30L,
      max_abs_mu_decomp_error = 0,
      max_abs_identity_err_glofas = 0,
      max_abs_identity_err_nws = 0,
      tol_decomp = 1e-8,
      tol_identity = 1e-8
    ),
    contract_overrides
  )
  write.csv(as.data.frame(contract), file.path(outputs_dir, "multivar_transfer_contract_q50.csv"), row.names = FALSE)
  invisible(TRUE)
}

write_multivar_drop_component_diagnostics <- function(outputs_dir, contract_overrides = list()) {
  csv_names <- c(
    "multivar_trace_summary_q50.csv",
    "multivar_forecast_window_q50_summary.csv",
    "multivar_forecast_window_q50_metrics.csv",
    "multivar_transfer_state_window_q50.csv",
    "multivar_transfer_state_contract_q50.csv",
    "multivar_transfer_identity_check_q50.csv",
    "multivar_vb_usgs_location_quantiles_cutoff_window.csv",
    "multivar_vb_usgs_location_quantile_summary.csv"
  )
  for (name in csv_names) {
    write.csv(data.frame(x = 1), file.path(outputs_dir, name), row.names = FALSE)
  }

  fig_names <- c(
    "multivar_elbo_trace_q50.png",
    "multivar_sigma_traces_q50.png",
    "multivar_gamma_traces_q50.png",
    "multivar_transfer_zeta_window_q50.png",
    "multivar_transfer_observation_decomposition_q50.png",
    "multivar_transfer_source_mu_window_q50.png",
    "multivar_transfer_discrepancy_identity_q50.png",
    "multivar_vb_usgs_location_quantiles_cutoff_window.png"
  )
  for (name in fig_names) {
    create_dummy_png(file.path(outputs_dir, name))
  }

  contract <- modifyList(
    list(
      transfer_mode = "drop",
      forecast_has_transfer = FALSE,
      n_forecast_rows = 30L,
      finite_zeta_forecast = 30L,
      finite_mu_without_transfer_forecast = 30L,
      max_abs_mu_decomp_error = 0,
      max_abs_identity_err_glofas = 0,
      max_abs_identity_err_nws = 0,
      tol_decomp = 1e-8,
      tol_identity = 1e-8
    ),
    contract_overrides
  )
  write.csv(as.data.frame(contract), file.path(outputs_dir, "multivar_transfer_contract_q50.csv"), row.names = FALSE)
  invisible(TRUE)
}

test_that("smoke post contract passes with smoke marker", {
  outputs_dir <- tempfile("post_outputs_smoke_")
  cache_dir <- tempfile("post_cache_smoke_")
  dir.create(outputs_dir, recursive = TRUE, showWarnings = FALSE)
  dir.create(cache_dir, recursive = TRUE, showWarnings = FALSE)

  writeLines("ok", con = file.path(outputs_dir, "post_smoke_marker.txt"))
  writeLines("meta", con = file.path(outputs_dir, "notes.txt"))

  artifacts <- unified_collect_post_artifacts(outputs_dir = outputs_dir, cache_dir = cache_dir)
  contract <- unified_post_contract_check(
    artifacts_df = artifacts,
    outputs_dir = outputs_dir,
    cache_dir = cache_dir,
    post_figures = FALSE,
    export_tables = FALSE
  )

  expect_true(isTRUE(contract$status))
  expect_true(isTRUE(contract$checks$smoke_marker_exists))
})

test_that("full post contract passes with figures, tables, and synthesis caches", {
  outputs_dir <- tempfile("post_outputs_full_")
  cache_dir <- tempfile("post_cache_full_")
  dir.create(outputs_dir, recursive = TRUE, showWarnings = FALSE)
  dir.create(cache_dir, recursive = TRUE, showWarnings = FALSE)
  tables_dir <- file.path(outputs_dir, "tables")
  dir.create(tables_dir, recursive = TRUE, showWarnings = FALSE)

  create_dummy_png(file.path(outputs_dir, "example.png"))

  write.csv(data.frame(x = 1), file.path(tables_dir, "gamma_summary.csv"), row.names = FALSE)
  write.csv(data.frame(x = 1), file.path(tables_dir, "sigma_summary.csv"), row.names = FALSE)
  write.csv(data.frame(x = 1), file.path(tables_dir, "covariate_effects_summary.csv"), row.names = FALSE)
  write.csv(data.frame(x = 1), file.path(tables_dir, "posterior_table_exports_manifest.csv"), row.names = FALSE)
  writeLines("readme", con = file.path(tables_dir, "posterior_table_exports_README.md"))

  saveRDS(array(1, dim = c(7, 3, 2)), file.path(cache_dir, "y_reps_f.rds"))
  saveRDS(array(1, dim = c(7, 3, 2)), file.path(cache_dir, "y_reps.rds"))
  saveRDS(array(1, dim = c(7, 3, 2)), file.path(cache_dir, "y_reps_f_new.rds"))
  saveRDS(array(1, dim = c(7, 3, 2)), file.path(cache_dir, "y_reps_new.rds"))

  artifacts <- unified_collect_post_artifacts(outputs_dir = outputs_dir, cache_dir = cache_dir)
  contract <- unified_post_contract_check(
    artifacts_df = artifacts,
    outputs_dir = outputs_dir,
    cache_dir = cache_dir,
    post_figures = TRUE,
    export_tables = TRUE
  )

  expect_true(isTRUE(contract$status))
  expect_true(isTRUE(contract$checks$has_figure))
  expect_true(isTRUE(contract$checks$synthesis_cache_files_present))
  expect_true(isTRUE(contract$checks$synthesis_core_shapes_ok))
  expect_true(isTRUE(contract$checks$table_exports_present))
})

test_that("full post contract fails fast on missing synthesis cache", {
  outputs_dir <- tempfile("post_outputs_fail_")
  cache_dir <- tempfile("post_cache_fail_")
  dir.create(outputs_dir, recursive = TRUE, showWarnings = FALSE)
  dir.create(cache_dir, recursive = TRUE, showWarnings = FALSE)
  tables_dir <- file.path(outputs_dir, "tables")
  dir.create(tables_dir, recursive = TRUE, showWarnings = FALSE)

  create_dummy_png(file.path(outputs_dir, "example.png"))

  write.csv(data.frame(x = 1), file.path(tables_dir, "gamma_summary.csv"), row.names = FALSE)
  write.csv(data.frame(x = 1), file.path(tables_dir, "sigma_summary.csv"), row.names = FALSE)
  write.csv(data.frame(x = 1), file.path(tables_dir, "covariate_effects_summary.csv"), row.names = FALSE)
  write.csv(data.frame(x = 1), file.path(tables_dir, "posterior_table_exports_manifest.csv"), row.names = FALSE)
  writeLines("readme", con = file.path(tables_dir, "posterior_table_exports_README.md"))

  saveRDS(array(1, dim = c(7, 3, 2)), file.path(cache_dir, "y_reps_f.rds"))
  # intentionally omit y_reps.rds + new caches

  contract <- unified_post_contract_check(
    artifacts_df = NULL,
    outputs_dir = outputs_dir,
    cache_dir = cache_dir,
    post_figures = TRUE,
    export_tables = TRUE
  )

  expect_false(isTRUE(contract$status))
  expect_false(isTRUE(contract$checks$synthesis_cache_files_present))
  expect_true(any(grepl("y_reps.rds", contract$missing_paths, fixed = TRUE)))
})

test_that("multivar-only post contract accepts multivar diagnostics without synthesis cubes", {
  outputs_dir <- tempfile("post_outputs_multivar_only_")
  cache_dir <- tempfile("post_cache_multivar_only_")
  dir.create(outputs_dir, recursive = TRUE, showWarnings = FALSE)
  dir.create(cache_dir, recursive = TRUE, showWarnings = FALSE)

  create_dummy_png(file.path(outputs_dir, "multivar_fit_mu_vs_observed_loglog.png"))
  create_dummy_png(file.path(outputs_dir, "multivar_forecast_window_mu_vs_future_usgs.png"))
  create_dummy_png(file.path(outputs_dir, "multivar_elbo_trace_q50.png"))

  write.csv(data.frame(x = 1), file.path(outputs_dir, "multivar_trace_summary_q50.csv"), row.names = FALSE)
  write.csv(data.frame(x = 1), file.path(outputs_dir, "multivar_forecast_window_q50_summary.csv"), row.names = FALSE)
  write.csv(data.frame(x = 1), file.path(outputs_dir, "multivar_forecast_window_q50_metrics.csv"), row.names = FALSE)

  contract <- unified_post_contract_check(
    artifacts_df = NULL,
    outputs_dir = outputs_dir,
    cache_dir = cache_dir,
    post_figures = TRUE,
    export_tables = TRUE,
    post_smoke_fast = FALSE,
    model_run_exdqlm_multivar = TRUE,
    model_run_exdqlm_univar = FALSE,
    model_run_ndlm_main = FALSE
  )

  expect_true(isTRUE(contract$status))
  expect_true(isTRUE(contract$checks$multivar_fit_figure_present))
  expect_true(isTRUE(contract$checks$multivar_forecast_figure_present))
  expect_true(isTRUE(contract$checks$multivar_trace_figure_present))
  expect_true(isTRUE(contract$checks$multivar_summary_csv_present))
  expect_true(isTRUE(contract$checks$table_exports_present))
})

test_that("smoke-fast multivar component contract requires q50 diagnostics and keep semantics", {
  outputs_dir <- tempfile("post_outputs_multivar_components_")
  cache_dir <- tempfile("post_cache_multivar_components_")
  dir.create(outputs_dir, recursive = TRUE, showWarnings = FALSE)
  dir.create(cache_dir, recursive = TRUE, showWarnings = FALSE)

  write_multivar_component_diagnostics(outputs_dir)

  contract <- unified_post_contract_check(
    artifacts_df = NULL,
    outputs_dir = outputs_dir,
    cache_dir = cache_dir,
    post_figures = TRUE,
    export_tables = TRUE,
    post_smoke_fast = TRUE,
    multivar_component_diagnostics = TRUE,
    multivar_component_transfer_mode = "keep",
    model_run_exdqlm_multivar = TRUE,
    model_run_exdqlm_univar = FALSE,
    model_run_ndlm_main = FALSE,
    model_run_ndlm_univar = FALSE
  )

  expect_true(isTRUE(contract$status))
  expect_true(isTRUE(contract$checks$multivar_component_diagnostics_present))
  expect_true(isTRUE(contract$checks$multivar_component_transfer_contract_ok))
})

test_that("smoke-fast multivar component contract accepts no-transfer drop diagnostics", {
  outputs_dir <- tempfile("post_outputs_multivar_components_drop_")
  cache_dir <- tempfile("post_cache_multivar_components_drop_")
  dir.create(outputs_dir, recursive = TRUE, showWarnings = FALSE)
  dir.create(cache_dir, recursive = TRUE, showWarnings = FALSE)

  write_multivar_drop_component_diagnostics(outputs_dir)

  contract <- unified_post_contract_check(
    artifacts_df = NULL,
    outputs_dir = outputs_dir,
    cache_dir = cache_dir,
    post_figures = TRUE,
    export_tables = TRUE,
    post_smoke_fast = TRUE,
    multivar_component_diagnostics = TRUE,
    multivar_component_transfer_mode = "drop",
    model_run_exdqlm_multivar = TRUE,
    model_run_exdqlm_univar = FALSE,
    model_run_ndlm_main = FALSE,
    model_run_ndlm_univar = FALSE
  )

  expect_true(isTRUE(contract$status))
  expect_true(isTRUE(contract$checks$multivar_component_diagnostics_present))
  expect_true(isTRUE(contract$checks$multivar_component_transfer_contract_ok))
  expect_false(any(grepl("multivar_transfer_coefficients", contract$missing_paths, fixed = TRUE)))
})

test_that("smoke-fast multivar component contract fails closed on missing or dropped forecast transfer", {
  outputs_missing <- tempfile("post_outputs_multivar_components_missing_")
  cache_missing <- tempfile("post_cache_multivar_components_missing_")
  dir.create(outputs_missing, recursive = TRUE, showWarnings = FALSE)
  dir.create(cache_missing, recursive = TRUE, showWarnings = FALSE)
  create_dummy_png(file.path(outputs_missing, "multivar_elbo_trace_q50.png"))

  missing_contract <- unified_post_contract_check(
    artifacts_df = NULL,
    outputs_dir = outputs_missing,
    cache_dir = cache_missing,
    post_figures = TRUE,
    export_tables = TRUE,
    post_smoke_fast = TRUE,
    multivar_component_diagnostics = TRUE,
    multivar_component_transfer_mode = "keep",
    model_run_exdqlm_multivar = TRUE,
    model_run_exdqlm_univar = FALSE,
    model_run_ndlm_main = FALSE,
    model_run_ndlm_univar = FALSE
  )

  expect_false(isTRUE(missing_contract$status))
  expect_false(isTRUE(missing_contract$checks$multivar_component_diagnostics_present))
  expect_true(any(grepl("multivar_transfer_contract_q50.csv", missing_contract$missing_paths, fixed = TRUE)))

  nonfatal_contract <- unified_post_contract_check(
    artifacts_df = NULL,
    outputs_dir = outputs_missing,
    cache_dir = cache_missing,
    post_figures = TRUE,
    export_tables = TRUE,
    post_smoke_fast = TRUE,
    multivar_component_diagnostics = TRUE,
    multivar_component_fail_fast = FALSE,
    multivar_component_transfer_mode = "keep",
    model_run_exdqlm_multivar = TRUE,
    model_run_exdqlm_univar = FALSE,
    model_run_ndlm_main = FALSE,
    model_run_ndlm_univar = FALSE
  )

  expect_true(isTRUE(nonfatal_contract$status))
  expect_false(isTRUE(nonfatal_contract$checks$multivar_component_diagnostics_present))
  expect_true(any(grepl("multivar_component_fail_fast=false", nonfatal_contract$messages, fixed = TRUE)))

  outputs_bad <- tempfile("post_outputs_multivar_components_bad_")
  cache_bad <- tempfile("post_cache_multivar_components_bad_")
  dir.create(outputs_bad, recursive = TRUE, showWarnings = FALSE)
  dir.create(cache_bad, recursive = TRUE, showWarnings = FALSE)
  write_multivar_component_diagnostics(
    outputs_bad,
    contract_overrides = list(
      forecast_has_transfer = FALSE,
      finite_zeta_forecast = 0L,
      finite_mu_without_transfer_forecast = 0L
    )
  )

  bad_contract <- unified_post_contract_check(
    artifacts_df = NULL,
    outputs_dir = outputs_bad,
    cache_dir = cache_bad,
    post_figures = TRUE,
    export_tables = TRUE,
    post_smoke_fast = TRUE,
    multivar_component_diagnostics = TRUE,
    multivar_component_transfer_mode = "keep",
    model_run_exdqlm_multivar = TRUE,
    model_run_exdqlm_univar = FALSE,
    model_run_ndlm_main = FALSE,
    model_run_ndlm_univar = FALSE
  )

  expect_false(isTRUE(bad_contract$status))
  expect_true(isTRUE(bad_contract$checks$multivar_component_diagnostics_present))
  expect_false(isTRUE(bad_contract$checks$multivar_component_transfer_contract_ok))
  expect_true(any(grepl("forecast_has_transfer=true", bad_contract$messages, fixed = TRUE)))
})

test_that("univar-only post contract accepts isolated univariate diagnostics and CRPS exports", {
  outputs_dir <- tempfile("post_outputs_univar_only_")
  cache_dir <- tempfile("post_cache_univar_only_")
  dir.create(outputs_dir, recursive = TRUE, showWarnings = FALSE)
  dir.create(cache_dir, recursive = TRUE, showWarnings = FALSE)
  tables_dir <- file.path(outputs_dir, "tables")
  dir.create(tables_dir, recursive = TRUE, showWarnings = FALSE)

  create_dummy_png(file.path(outputs_dir, "univar_fit_mu_vs_observed_log1p.png"))
  create_dummy_png(file.path(outputs_dir, "univar_fit_mu_vs_observed_recent_log1p.png"))
  create_dummy_png(file.path(outputs_dir, "univar_forecast_window_mu_vs_future_usgs.png"))
  create_dummy_png(file.path(outputs_dir, "univar_forecast_window_predictive_q50_vs_future_usgs.png"))
  create_dummy_png(file.path(outputs_dir, "univar_forecast_window_univar_vs_ensembles.png"))
  create_dummy_png(file.path(outputs_dir, "univar_forecast_window_ensemble_members.png"))
  create_dummy_png(file.path(outputs_dir, "univar_forecast_window_quantiles_raw_cms.png"))
  create_dummy_png(file.path(outputs_dir, "univar_elbo_traces.png"))

  write.csv(data.frame(forecast_date = "2021-01-24", value = 1), file.path(outputs_dir, "univar_forecast_window_quantiles.csv"), row.names = FALSE)
  write.csv(data.frame(forecast_index = 1, crossing = 0), file.path(outputs_dir, "univar_forecast_quantile_crossing_per_time.csv"), row.names = FALSE)
  write.csv(data.frame(metric = "median_curve_times_with_crossing", value = 0), file.path(outputs_dir, "univar_forecast_quantile_crossing_summary.csv"), row.names = FALSE)

  write.csv(data.frame(x = 1), file.path(tables_dir, "crps_forecast_summary.csv"), row.names = FALSE)
  write.csv(data.frame(x = 1), file.path(tables_dir, "crps_forecast_per_time.csv"), row.names = FALSE)
  write.csv(data.frame(x = 1), file.path(tables_dir, "crps_input_health.csv"), row.names = FALSE)
  write.csv(data.frame(x = 1), file.path(tables_dir, "crps_input_health_per_time.csv"), row.names = FALSE)
  write.csv(data.frame(x = 1), file.path(tables_dir, "posterior_table_exports_manifest.csv"), row.names = FALSE)
  writeLines("readme", con = file.path(tables_dir, "posterior_table_exports_README.md"))

  saveRDS(array(1, dim = c(7, 3, 2)), file.path(cache_dir, "y_hist_uni.rds"))
  saveRDS(array(1, dim = c(7, 3, 2)), file.path(cache_dir, "y_forecast_uni.rds"))
  saveRDS(matrix(1, nrow = 3, ncol = 2), file.path(cache_dir, "synth_univar_hist_log1p.rds"))
  saveRDS(matrix(1, nrow = 3, ncol = 2), file.path(cache_dir, "synth_univar_forecast_log1p.rds"))

  contract <- unified_post_contract_check(
    artifacts_df = NULL,
    outputs_dir = outputs_dir,
    cache_dir = cache_dir,
    post_figures = TRUE,
    export_tables = TRUE,
    post_smoke_fast = FALSE,
    model_run_exdqlm_multivar = FALSE,
    model_run_exdqlm_univar = TRUE,
    model_run_ndlm_main = FALSE,
    model_run_ndlm_univar = FALSE
  )

  expect_true(isTRUE(contract$status))
  expect_true(isTRUE(contract$checks$univar_fit_figure_present))
  expect_true(isTRUE(contract$checks$univar_forecast_figure_present))
  expect_true(isTRUE(contract$checks$univar_trace_figure_present))
  expect_true(isTRUE(contract$checks$univar_summary_exports_present))
  expect_true(isTRUE(contract$checks$synthesis_cache_files_present))
  expect_true(isTRUE(contract$checks$synthesis_core_shapes_ok))
  expect_true(isTRUE(contract$checks$table_exports_present))
})

test_that("univar-only post contract accepts dedicated repair outputs without legacy fit/trace figures", {
  outputs_dir <- tempfile("post_outputs_univar_repair_only_")
  cache_dir <- tempfile("post_cache_univar_repair_only_")
  dir.create(outputs_dir, recursive = TRUE, showWarnings = FALSE)
  dir.create(cache_dir, recursive = TRUE, showWarnings = FALSE)
  tables_dir <- file.path(outputs_dir, "tables")
  dir.create(tables_dir, recursive = TRUE, showWarnings = FALSE)

  create_dummy_png(file.path(outputs_dir, "univar_forecast_window_quantiles_raw_cms.png"))

  write.csv(data.frame(forecast_date = "2021-01-24", value = 1), file.path(outputs_dir, "univar_forecast_window_quantiles.csv"), row.names = FALSE)
  write.csv(data.frame(forecast_index = 1, crossing = 0), file.path(outputs_dir, "univar_forecast_quantile_crossing_per_time.csv"), row.names = FALSE)
  write.csv(data.frame(metric = "median_curve_times_with_crossing", value = 0), file.path(outputs_dir, "univar_forecast_quantile_crossing_summary.csv"), row.names = FALSE)

  write.csv(data.frame(x = 1), file.path(tables_dir, "crps_forecast_summary.csv"), row.names = FALSE)
  write.csv(data.frame(x = 1), file.path(tables_dir, "crps_forecast_per_time.csv"), row.names = FALSE)
  write.csv(data.frame(x = 1), file.path(tables_dir, "crps_input_health.csv"), row.names = FALSE)
  write.csv(data.frame(x = 1), file.path(tables_dir, "crps_input_health_per_time.csv"), row.names = FALSE)
  write.csv(data.frame(x = 1), file.path(tables_dir, "posterior_table_exports_manifest.csv"), row.names = FALSE)
  writeLines("readme", con = file.path(tables_dir, "posterior_table_exports_README.md"))

  saveRDS(array(1, dim = c(3, 5, 2)), file.path(cache_dir, "y_hist_uni.rds"))
  saveRDS(array(1, dim = c(3, 5, 2)), file.path(cache_dir, "y_forecast_uni.rds"))
  saveRDS(matrix(1, nrow = 3, ncol = 2), file.path(cache_dir, "synth_univar_hist_log1p.rds"))
  saveRDS(matrix(1, nrow = 3, ncol = 2), file.path(cache_dir, "synth_univar_forecast_log1p.rds"))

  contract <- unified_post_contract_check(
    artifacts_df = NULL,
    outputs_dir = outputs_dir,
    cache_dir = cache_dir,
    post_figures = TRUE,
    export_tables = TRUE,
    post_smoke_fast = FALSE,
    model_run_exdqlm_multivar = FALSE,
    model_run_exdqlm_univar = TRUE,
    model_run_ndlm_main = FALSE,
    model_run_ndlm_univar = FALSE
  )

  expect_true(isTRUE(contract$status))
  expect_true(isTRUE(contract$checks$univar_fit_figure_present))
  expect_true(isTRUE(contract$checks$univar_forecast_figure_present))
  expect_true(isTRUE(contract$checks$univar_trace_figure_present))
  expect_true(isTRUE(contract$checks$univar_summary_exports_present))
  expect_true(isTRUE(contract$checks$table_exports_present))
})

test_that("artifact report writer creates manifest and summary files", {
  outputs_dir <- tempfile("post_outputs_report_")
  cache_dir <- tempfile("post_cache_report_")
  dir.create(outputs_dir, recursive = TRUE, showWarnings = FALSE)
  dir.create(cache_dir, recursive = TRUE, showWarnings = FALSE)
  writeLines("ok", con = file.path(outputs_dir, "post_smoke_marker.txt"))

  artifacts <- unified_collect_post_artifacts(outputs_dir = outputs_dir, cache_dir = cache_dir)
  contract <- unified_post_contract_check(
    artifacts_df = artifacts,
    outputs_dir = outputs_dir,
    cache_dir = cache_dir,
    post_figures = FALSE,
    export_tables = FALSE
  )
  reports <- unified_write_post_artifact_reports(
    artifacts_df = artifacts,
    outputs_dir = outputs_dir,
    run_id = "ut_post_artifact_contract",
    cache_dir = cache_dir,
    contract = contract
  )

  expect_true(file.exists(reports$manifest_path))
  expect_true(file.exists(reports$summary_path))
  expect_true(nrow(reports$manifest_df) >= 1L)
})
