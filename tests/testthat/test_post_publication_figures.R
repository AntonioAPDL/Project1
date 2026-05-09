source(testthat::test_path("..", "..", "R", "unified", "post_publication_figures.R"))

test_that("cutoff-specific shared y-limits are resolved from style", {
  style <- post_publication_load_style(
    project_root = normalizePath(testthat::test_path("..", ".."), mustWork = TRUE),
    config_path = testthat::test_path("..", "..", "config", "post_publication_figures.yaml")
  )
  expect_equal(post_publication_y_limits_for_cutoff(as.Date("2021-01-23"), style), c(0, 6))
  expect_equal(post_publication_y_limits_for_cutoff(as.Date("2021-11-12"), style), c(0, 4))
  expect_equal(post_publication_y_limits_for_cutoff(as.Date("2022-12-25"), style), c(0, 10))
})

make_quant_df <- function(model_id) {
  dates <- as.Date("2021-01-01") + 0:5
  data.frame(
    model_id = model_id,
    date = as.character(dates),
    segment = c(rep("history", 3), rep("forecast", 3)),
    observed = c(0.50, 0.55, 0.60, 0.62, 0.68, 0.70),
    q05 = c(0.30, 0.35, 0.40, 0.42, 0.45, 0.48),
    q20 = c(0.38, 0.42, 0.46, 0.49, 0.52, 0.55),
    q50 = c(0.48, 0.52, 0.58, 0.60, 0.64, 0.66),
    q80 = c(0.58, 0.62, 0.68, 0.70, 0.74, 0.77),
    q95 = c(0.66, 0.70, 0.76, 0.80, 0.84, 0.88),
    stringsAsFactors = FALSE
  )
}

make_sample_df <- function(model_id) {
  dates <- as.Date("2021-01-01") + 0:5
  draws <- 1:4
  out <- expand.grid(
    sample_index = draws,
    date = as.character(dates),
    stringsAsFactors = FALSE
  )
  out$model_id <- model_id
  out$draw_id <- sprintf("draw_%03d", out$sample_index)
  out$segment <- ifelse(as.Date(out$date) <= as.Date("2021-01-03"), "history", "forecast")
  out$value <- 0.35 + 0.05 * out$sample_index + seq_len(nrow(out)) * 0.005
  out[, c("model_id", "draw_id", "sample_index", "date", "segment", "value")]
}

write_member_adapter <- function(path, dates, prefix) {
  df <- data.frame(
    target_date = as.character(dates),
    member_001 = c(0.61, 0.64, 0.67),
    member_002 = c(0.58, 0.62, 0.66),
    stringsAsFactors = FALSE
  )
  utils::write.csv(df, path, row.names = FALSE)
}

test_that("publication figure rewrite renders focus posterior plots with raw ensembles and predictive bands", {
  skip_if_not_installed("ggplot2")

  repo_root <- normalizePath(testthat::test_path("..", ".."), mustWork = TRUE)
  run_root <- tempfile("post_pub_run_")
  outputs_dir <- file.path(run_root, "post", "outputs", "ut_run")
  cache_dir <- file.path(run_root, "post", "cache")
  inputs_dir <- file.path(run_root, "post", "inputs")
  dir.create(outputs_dir, recursive = TRUE, showWarnings = FALSE)
  dir.create(cache_dir, recursive = TRUE, showWarnings = FALSE)
  dir.create(inputs_dir, recursive = TRUE, showWarnings = FALSE)

  model_post <- "dqlm_multivar_al_synth_keep"
  model_ndlm <- "ndlm_main_synth_keep"
  dates <- as.Date("2021-01-04") + 0:2

  quant_post_path <- file.path(outputs_dir, sprintf("%s_cutoff_window_quantiles.csv", model_post))
  sample_post_path <- file.path(outputs_dir, sprintf("%s_cutoff_window_sample_subset.csv", model_post))
  plot_post_path <- file.path(outputs_dir, sprintf("%s_cutoff_window_posterior_samples.png", model_post))
  overlay_post_path <- file.path(outputs_dir, sprintf("%s_cutoff_window_posterior_samples_with_raw_ensembles.png", model_post))
  quant_ndlm_path <- file.path(outputs_dir, sprintf("%s_cutoff_window_quantiles.csv", model_ndlm))
  plot_ndlm_path <- file.path(outputs_dir, sprintf("%s_cutoff_window_predictive_bands.png", model_ndlm))
  overlay_ndlm_path <- file.path(outputs_dir, sprintf("%s_cutoff_window_predictive_bands_with_raw_ensembles.png", model_ndlm))

  utils::write.csv(make_quant_df(model_post), quant_post_path, row.names = FALSE)
  utils::write.csv(make_sample_df(model_post), sample_post_path, row.names = FALSE)
  utils::write.csv(make_quant_df(model_ndlm)[, c("model_id", "date", "segment", "observed", "q05", "q50", "q95")], quant_ndlm_path, row.names = FALSE)

  hist_mat <- matrix(c(
    0.45, 0.50, 0.55,
    0.48, 0.53, 0.58,
    0.50, 0.55, 0.60,
    0.52, 0.57, 0.62
  ), nrow = 4, byrow = TRUE)
  fc_mat <- matrix(c(
    0.60, 0.64, 0.68,
    0.58, 0.63, 0.67,
    0.62, 0.66, 0.70,
    0.64, 0.68, 0.72
  ), nrow = 4, byrow = TRUE)
  saveRDS(hist_mat, file.path(cache_dir, sprintf("%s__mode-keep__synth_multivar_hist_log1p.rds", model_post)))
  saveRDS(fc_mat, file.path(cache_dir, sprintf("%s__mode-keep__synth_multivar_forecast_log1p.rds", model_post)))

  write_member_adapter(file.path(inputs_dir, "nws_post_adapter.csv"), dates, "nws")
  write_member_adapter(file.path(inputs_dir, "glofas_post_adapter.csv"), dates, "glofas")

  manifest <- data.frame(
    model_id = c(model_post, model_post, model_post, model_ndlm, model_ndlm),
    plot_type = c(
      "cutoff_window_posterior_samples",
      "cutoff_window_quantiles",
      "cutoff_window_sample_subset",
      "cutoff_window_predictive_bands",
      "cutoff_window_quantiles"
    ),
    path = c(plot_post_path, quant_post_path, sample_post_path, plot_ndlm_path, quant_ndlm_path),
    source_run = "ut_run",
    note = c("plot_scale=log1p_cms", "segment_quantiles_on_log1p_cms", "deterministic_sample_cap=4", "plot_scale=log1p_cms", "segment_quantiles_on_log1p_cms"),
    stringsAsFactors = FALSE
  )
  utils::write.csv(manifest, file.path(outputs_dir, "figure_manifest.csv"), row.names = FALSE)

  res <- unified_render_publication_figures(
    outputs_dir = outputs_dir,
    run_id = "ut_run",
    project_root = repo_root,
    enabled = TRUE,
    rewrite_canonical_png = TRUE,
    export_pdf = TRUE,
    fail_fast = TRUE,
    style_config_path = file.path(repo_root, "config", "post_publication_figures.yaml")
  )

  expect_true(isTRUE(res$status))
  expect_equal(res$rendered, 2L)
  expect_gte(res$rendered_outputs, 3L)
  expect_true(file.exists(plot_post_path))
  expect_true(file.exists(sub("\\.png$", ".pdf", plot_post_path)))
  expect_true(file.exists(overlay_post_path))
  expect_true(file.exists(sub("\\.png$", ".pdf", overlay_post_path)))
  expect_true(file.exists(plot_ndlm_path))
  expect_true(file.exists(sub("\\.png$", ".pdf", plot_ndlm_path)))
  expect_true(file.exists(overlay_ndlm_path))
  expect_true(file.exists(sub("\\.png$", ".pdf", overlay_ndlm_path)))
  expect_true(file.exists(file.path(outputs_dir, "publication_figure_manifest.csv")))
  expect_true(file.exists(file.path(outputs_dir, "publication_style_used.yaml")))

  updated_manifest <- utils::read.csv(file.path(outputs_dir, "figure_manifest.csv"), stringsAsFactors = FALSE, check.names = FALSE)
  expect_true(any(updated_manifest$plot_type == "cutoff_window_posterior_samples_pdf"))
  expect_true(any(updated_manifest$plot_type == "cutoff_window_posterior_samples_with_raw_ensembles"))
  expect_true(any(updated_manifest$plot_type == "cutoff_window_posterior_samples_with_raw_ensembles_pdf"))
  expect_true(any(updated_manifest$plot_type == "cutoff_window_predictive_bands_pdf"))
  expect_true(any(updated_manifest$plot_type == "cutoff_window_predictive_bands_with_raw_ensembles"))
  expect_true(any(updated_manifest$plot_type == "cutoff_window_predictive_bands_with_raw_ensembles_pdf"))
  expect_true(any(grepl("style=publication_focus_v2", updated_manifest$note[updated_manifest$plot_type == "cutoff_window_posterior_samples"], fixed = TRUE)))

  pub_manifest <- utils::read.csv(file.path(outputs_dir, "publication_figure_manifest.csv"), stringsAsFactors = FALSE, check.names = FALSE)
  expect_true(any(pub_manifest$source_plot_type == "cutoff_window_posterior_samples_focus"))
  expect_true(any(pub_manifest$source_plot_type == "cutoff_window_posterior_samples_with_raw_ensembles"))
  expect_true(any(pub_manifest$source_plot_type == "cutoff_window_predictive_bands_focus"))
  expect_true(any(pub_manifest$source_plot_type == "cutoff_window_predictive_bands_with_raw_ensembles"))
})
