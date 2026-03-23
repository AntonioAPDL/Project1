source(testthat::test_path("..", "..", "R", "unified", "config.R"))

test_that("unified config defaults include new likelihood and ndlm transfer modes", {
  cfg <- unified_config_defaults()

  expect_equal(cfg$models$exdqlm_univar$likelihood_mode, "exal")
  expect_equal(cfg$models$exdqlm_multivar$likelihood_mode, "exal")
  expect_equal(cfg$models$ndlm_main$forecast_transfer_mode, "keep")
  expect_equal(cfg$models$ndlm_univar$forecast_transfer_mode, "keep")
  expect_equal(cfg$models$ndlm_univar$implementation_mode, "theory_aligned_closed_form")
  expect_equal(cfg$models$ndlm_univar$horizon_cap, 1080L)
  expect_equal(cfg$models$ndlm_main$stabilization$cov_eig_floor, 1e-8)
  expect_equal(cfg$models$ndlm_main$stabilization$cov_eig_cap, 1e8)
  expect_equal(cfg$models$ndlm_main$stabilization$sigma_update_damping, 1.0)
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
