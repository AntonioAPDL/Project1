source(testthat::test_path("..", "..", "R", "unified", "config.R"))

test_that("unified config defaults include new likelihood and ndlm transfer modes", {
  cfg <- unified_config_defaults()

  expect_equal(cfg$models$exdqlm_univar$implementation_mode, "legacy_bridge")
  expect_equal(cfg$models$exdqlm_univar$likelihood_mode, "exal")
  expect_equal(cfg$models$exdqlm_multivar$likelihood_mode, "exal")
  expect_equal(cfg$models$ndlm_main$forecast_transfer_mode, "keep")
  expect_equal(cfg$models$ndlm_univar$forecast_transfer_mode, "keep")
  expect_equal(cfg$models$ndlm_univar$implementation_mode, "theory_aligned_closed_form")
  expect_equal(cfg$models$ndlm_univar$horizon_cap, 1080L)
  expect_equal(cfg$models$ndlm_main$stabilization$cov_eig_floor, 1e-8)
  expect_equal(cfg$models$ndlm_main$stabilization$cov_eig_cap, 1e8)
  expect_equal(cfg$models$ndlm_main$stabilization$sigma_update_damping, 1.0)
  expect_equal(cfg$fit$diagnostics$full_slice_psd, FALSE)
  expect_equal(cfg$fit$diagnostics$psd_warn_tol, -1e-10)
  expect_equal(cfg$fit$diagnostics$psd_fail_tol, -1e-10)
  expect_equal(cfg$post$crps_input_health$enabled, TRUE)
  expect_equal(cfg$post$crps_input_health$fail_fast, FALSE)
  expect_equal(cfg$post$crps_input_health$min_finite_share, 1)
  expect_true(is.na(cfg$post$crps_input_health$max_abs))
})

test_that("mode resolvers normalize invalid values safely", {
  cfg <- unified_config_defaults()
  cfg$models$exdqlm_univar$likelihood_mode <- "AL"
  cfg$models$exdqlm_multivar$likelihood_mode <- "bad_mode"
  cfg$models$ndlm_main$forecast_transfer_mode <- "BAD"
  cfg$models$ndlm_univar$forecast_transfer_mode <- "BAD"

  expect_equal(unified_resolve_univar_likelihood_mode(cfg), "al")
  expect_equal(unified_resolve_multivar_likelihood_mode(cfg), "exal")
  expect_equal(unified_resolve_ndlm_forecast_transfer_mode(cfg), "keep")
  expect_equal(unified_resolve_ndlm_univar_forecast_transfer_mode(cfg), "keep")
})

test_that("config validation rejects invalid likelihood and ndlm transfer modes", {
  cfg <- unified_config_defaults()
  cfg$models$exdqlm_univar$likelihood_mode <- "bogus"
  cfg$models$exdqlm_multivar$likelihood_mode <- "bogus"
  cfg$models$ndlm_main$forecast_transfer_mode <- "bogus"
  cfg$models$ndlm_univar$forecast_transfer_mode <- "bogus"

  errs <- unified_validate_config(cfg)

  expect_true(any(grepl("models\\.exdqlm_univar\\.likelihood_mode", errs)))
  expect_true(any(grepl("models\\.exdqlm_multivar\\.likelihood_mode", errs)))
  expect_true(any(grepl("models\\.ndlm_main\\.forecast_transfer_mode", errs)))
  expect_true(any(grepl("models\\.ndlm_univar\\.forecast_transfer_mode", errs)))
})

test_that("config validation rejects invalid ndlm stabilization controls", {
  cfg <- unified_config_defaults()
  cfg$models$ndlm_main$stabilization$cov_eig_floor <- -1
  cfg$models$ndlm_main$stabilization$cov_eig_cap <- 0
  cfg$models$ndlm_main$stabilization$sigma_update_damping <- 2
  cfg$models$ndlm_univar$stabilization$cov_eig_floor <- -1
  cfg$models$ndlm_univar$stabilization$cov_eig_cap <- 0

  errs <- unified_validate_config(cfg)

  expect_true(any(grepl("models\\.ndlm_main\\.stabilization\\.cov_eig_floor", errs)))
  expect_true(any(grepl("models\\.ndlm_main\\.stabilization\\.cov_eig_cap", errs)))
  expect_true(any(grepl("models\\.ndlm_main\\.stabilization\\.sigma_update_damping", errs)))
  expect_true(any(grepl("models\\.ndlm_univar\\.stabilization\\.cov_eig_floor", errs)))
  expect_true(any(grepl("models\\.ndlm_univar\\.stabilization\\.cov_eig_cap", errs)))
})

test_that("config validation rejects invalid diagnostics and crps input health controls", {
  cfg <- unified_config_defaults()
  cfg$fit$diagnostics$full_slice_psd <- "nope"
  cfg$fit$diagnostics$psd_warn_tol <- "bad"
  cfg$fit$diagnostics$psd_fail_tol <- "bad"
  cfg$post$crps_input_health$enabled <- "bad"
  cfg$post$crps_input_health$fail_fast <- "bad"
  cfg$post$crps_input_health$min_finite_share <- 2
  cfg$post$crps_input_health$max_abs <- 0

  errs <- unified_validate_config(cfg)
  expect_true(any(grepl("fit\\.diagnostics\\.full_slice_psd", errs)))
  expect_true(any(grepl("fit\\.diagnostics\\.psd_warn_tol", errs)))
  expect_true(any(grepl("fit\\.diagnostics\\.psd_fail_tol", errs)))
  expect_true(any(grepl("post\\.crps_input_health\\.enabled", errs)))
  expect_true(any(grepl("post\\.crps_input_health\\.fail_fast", errs)))
  expect_true(any(grepl("post\\.crps_input_health\\.min_finite_share", errs)))
  expect_true(any(grepl("post\\.crps_input_health\\.max_abs", errs)))
})
