source(testthat::test_path("..", "..", "R", "environmetrics", "02_helpers_core.R"))

test_that("post_crps_quantile_approx returns zero for perfect forecast samples", {
  sample_mat <- matrix(2, nrow = 7, ncol = 5)
  obs <- rep(2, 5)

  out <- post_crps_quantile_approx(obs = obs, sample_mat = sample_mat, context = "ut.crps.zero")

  expect_equal(length(out$crps), 5L)
  expect_equal(out$crps, rep(0, 5))
  expect_equal(out$n_samples_eff, rep(7L, 5L))
  expect_equal(out$n_samples_nominal, 7L)
  expect_equal(out$method, "quantile_check_loss_sum")
  expect_equal(out$tau_rule, "k_over_m_plus_1")
})

test_that("post_crps_model_tables returns expected schemas and horizon-aligned rows", {
  set.seed(101)
  sample_mat <- matrix(rnorm(6 * 4, mean = 1.5, sd = 0.2), nrow = 6, ncol = 4)
  obs <- c(1.2, 1.4, 1.6, 1.8)
  dates <- as.Date("2022-12-26") + 0:3

  out <- post_crps_model_tables(
    model_id = "toy_model",
    model_family = "synthesis",
    model_variant = "toy_variant",
    sample_mat = sample_mat,
    obs = obs,
    forecast_dates = dates,
    cutoff_date = as.Date("2022-12-25"),
    forecast_start_date = as.Date("2022-12-26"),
    transfer_mode = "drop",
    score_scale = "log_cms_plus1",
    context = "ut.crps.tables"
  )

  expect_equal(nrow(out$per_time), 4L)
  expect_equal(nrow(out$summary), 1L)
  expect_equal(out$summary$horizon_days[[1L]], 4L)
  expect_equal(out$summary$model_id[[1L]], "toy_model")
  expect_true(all(out$per_time$model_id == "toy_model"))
  expect_true(all(out$per_time$lead_day == 1:4))
  expect_true(all(out$per_time$forecast_date == as.character(dates)))
  expect_equal(
    names(out$per_time),
    c(
      "cutoff_date", "forecast_start_date", "model_id", "model_family", "model_variant",
      "transfer_mode", "lead_day", "forecast_date", "crps", "n_samples_eff",
      "n_samples_nominal", "score_method", "tau_rule", "score_scale"
    )
  )
})

test_that("post_export_crps_tables writes suffixed table files and manifest", {
  td <- tempfile("crps_export_tables_")
  dir.create(td, recursive = TRUE, showWarnings = FALSE)

  per_time <- data.frame(
    cutoff_date = "2022-12-25",
    forecast_start_date = "2022-12-26",
    model_id = "toy_model",
    model_family = "synthesis",
    model_variant = "toy_variant",
    transfer_mode = "keep",
    lead_day = 1:2,
    forecast_date = as.character(as.Date("2022-12-26") + 0:1),
    crps = c(0.1, 0.2),
    n_samples_eff = c(10L, 10L),
    n_samples_nominal = c(10L, 10L),
    score_method = "quantile_check_loss_sum",
    tau_rule = "k_over_m_plus_1",
    score_scale = "log_cms_plus1",
    stringsAsFactors = FALSE
  )
  summary <- data.frame(
    cutoff_date = "2022-12-25",
    forecast_start_date = "2022-12-26",
    model_id = "toy_model",
    model_family = "synthesis",
    model_variant = "toy_variant",
    transfer_mode = "keep",
    horizon_days = 2L,
    n_valid = 2L,
    mean_crps = 0.15,
    median_crps = 0.15,
    sd_crps = 0.07071068,
    min_crps = 0.1,
    max_crps = 0.2,
    n_samples_nominal = 10L,
    n_samples_eff_min = 10L,
    n_samples_eff_max = 10L,
    score_method = "quantile_check_loss_sum",
    tau_rule = "k_over_m_plus_1",
    score_scale = "log_cms_plus1",
    stringsAsFactors = FALSE
  )

  out <- post_export_crps_tables(
    per_time_df = per_time,
    summary_df = summary,
    output_dir = td,
    table_formats = c("csv", "rds"),
    keep_na = TRUE,
    numeric_digits = 17L,
    file_suffix = "_keep"
  )

  expect_true(file.exists(file.path(td, "crps_forecast_per_time_keep.csv")))
  expect_true(file.exists(file.path(td, "crps_forecast_summary_keep.csv")))
  expect_true(file.exists(file.path(td, "crps_forecast_per_time_keep.rds")))
  expect_true(file.exists(file.path(td, "crps_forecast_summary_keep.rds")))
  expect_equal(
    names(out$manifest),
    c("table_name", "file_path", "nrow", "ncol", "sha256")
  )
  expect_equal(nrow(out$manifest), 4L)
  expect_true(all(nzchar(out$manifest$sha256)))
})

test_that("post_crps_synth_model_meta resolves IDs for exAL and AL families", {
  u_ex <- post_crps_synth_model_meta(family = "univar", likelihood_mode = "exal")
  u_al <- post_crps_synth_model_meta(family = "univar", likelihood_mode = "al")
  m_ex_keep <- post_crps_synth_model_meta(family = "multivar", likelihood_mode = "exal", transfer_mode = "keep")
  m_al_drop <- post_crps_synth_model_meta(family = "multivar", likelihood_mode = "al", transfer_mode = "drop")
  n_keep <- post_crps_synth_model_meta(family = "ndlm", transfer_mode = "keep")
  nu_keep <- post_crps_synth_model_meta(family = "ndlm_univar", transfer_mode = "keep")

  expect_equal(u_ex$model_id, "exdqlm_univar_synth")
  expect_equal(u_al$model_id, "dqlm_univar_al_synth")
  expect_equal(m_ex_keep$model_id, "exdqlm_multivar_synth_keep")
  expect_equal(m_al_drop$model_id, "dqlm_multivar_al_synth_drop")
  expect_equal(n_keep$model_id, "ndlm_main_synth_keep")
  expect_equal(n_keep$model_variant, "ndlm_main_keep")
  expect_equal(nu_keep$model_id, "ndlm_univar_synth_keep")
  expect_equal(nu_keep$model_variant, "ndlm_univar_keep")
})
