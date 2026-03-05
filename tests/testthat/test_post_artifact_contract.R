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
