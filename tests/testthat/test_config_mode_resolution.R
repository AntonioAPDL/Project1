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
  expect_equal(cfg$post$multivar_component_diagnostics$enabled, FALSE)
  expect_equal(cfg$post$multivar_component_diagnostics$quantile, 0.50)
  expect_equal(cfg$post$multivar_component_diagnostics$pre_days, 30L)
  expect_equal(cfg$post$multivar_component_diagnostics$fail_fast, TRUE)
  expect_equal(cfg$inputs$transfer_function_covariates$mode, "full")
  expect_equal(cfg$inputs$transfer_function_covariates$scaling, "sd")
  expect_equal(unified_resolve_transfer_feature_mode(cfg), "full")
  expect_equal(unified_resolve_transfer_feature_scaling(cfg), "sd")
  expect_equal(unified_resolve_transfer_feature_columns(cfg), c(
    "PPT", "SOIL", "PCA",
    "PPT_sq", "SOIL_sq", "PPT_x_SOIL",
    "PPT_lag1", "PPT_lag2", "PPT_lag3",
    "SOIL_lag1", "SOIL_lag2", "SOIL_lag3"
  ))
  expect_equal(cfg$fit$exdqlm_multivar$latent_ablation$mode, "free")
  expect_equal(cfg$fit$exdqlm_multivar$latent_ablation$e_inv_u_cap, 5000)
  expect_equal(cfg$fit$exdqlm_multivar$latent_ablation$e_u_cap, 1e6)
  expect_equal(cfg$fit$exdqlm_multivar$gamma_sigma$coherence_guard$enabled, TRUE)
  expect_equal(cfg$fit$exdqlm_multivar$gamma_sigma$coherence_guard$rollback_on_guard, TRUE)
  expect_equal(cfg$fit$exdqlm_multivar$gamma_sigma$coherence_guard$min_uts_psi, 1e-8)
  expect_equal(cfg$fit$exdqlm_multivar$gamma_sigma$coherence_guard$nonnegative_tol, 1e-10)
  expect_equal(cfg$fit$exdqlm_multivar$gamma_sigma$stabilization$state_norm_abs_cap_scale, "per_time")
  expect_equal(cfg$fit$exdqlm_multivar$pseudodata_guard$enabled, TRUE)
  expect_equal(cfg$fit$exdqlm_multivar$pseudodata_guard$mode, "fail")
  expect_equal(cfg$fit$exdqlm_multivar$pseudodata_guard$caps$e_inv_u_abs_cap, 5000)
  expect_equal(cfg$fit$exdqlm_multivar$pseudodata_guard$caps$e_inv_u_floor, 1e-9)
  expect_equal(cfg$fit$exdqlm_multivar$pseudodata_guard$caps$e_inv_u_floor_frac_cap, 0.25)
  expect_equal(cfg$fit$exdqlm_multivar$forecast_health$history_latent_limit, 25)
  expect_equal(cfg$fit$exdqlm_multivar$forecast_health$state_norm_sq_per_T_limit, 1e4)
  expect_equal(cfg$fit$exdqlm_multivar$forecast_health$transfer_level_limit, 25)
  expect_equal(cfg$fit$exdqlm_multivar$diagnostics$latent$enabled, TRUE)
  expect_equal(cfg$fit$exdqlm_multivar$diagnostics$latent$top_k, 20L)
  expect_equal(cfg$fit$exdqlm_multivar$diagnostics$latent$write_iteration_summary, FALSE)
  expect_equal(cfg$fit$exdqlm_multivar$diagnostics$latent$write_health_summary, TRUE)
  expect_equal(cfg$fit$exdqlm_multivar$diagnostics$latent$write_top_cells, FALSE)
  expect_equal(cfg$fit$exdqlm_multivar$legacy$post_save_objective_enabled, FALSE)
  expect_equal(cfg$fit$exdqlm_multivar$legacy$post_save_jsd_enabled, FALSE)
  expect_equal(cfg$fit$exdqlm_multivar$legacy$post_save_jsd_gridsize, 100L)
})

test_that("mode resolvers normalize invalid values safely", {
  cfg <- unified_config_defaults()
  cfg$models$exdqlm_univar$likelihood_mode <- "AL"
  cfg$models$exdqlm_multivar$likelihood_mode <- "bad_mode"
  cfg$models$ndlm_main$forecast_transfer_mode <- "BAD"
  cfg$models$ndlm_univar$forecast_transfer_mode <- "BAD"
  cfg$inputs$transfer_function_covariates$mode <- "BAD"
  cfg$inputs$transfer_function_covariates$scaling <- "BAD"

  expect_equal(unified_resolve_univar_likelihood_mode(cfg), "al")
  expect_equal(unified_resolve_multivar_likelihood_mode(cfg), "exal")
  expect_equal(unified_resolve_ndlm_forecast_transfer_mode(cfg), "keep")
  expect_equal(unified_resolve_ndlm_univar_forecast_transfer_mode(cfg), "keep")
  expect_equal(unified_resolve_transfer_feature_mode(cfg), "full")
  expect_equal(unified_resolve_transfer_feature_scaling(cfg), "sd")

  cfg$inputs$transfer_function_covariates$mode <- "none"
  expect_equal(unified_resolve_transfer_feature_columns(cfg), character(0))
  cfg$inputs$transfer_function_covariates$mode <- "base_only"
  cfg$inputs$transfer_function_covariates$base_covariates <- c("PPT", "SOIL")
  expect_equal(unified_resolve_transfer_feature_columns(cfg), c("PPT", "SOIL"))
})

test_that("config validation rejects invalid likelihood and ndlm transfer modes", {
  cfg <- unified_config_defaults()
  cfg$models$exdqlm_univar$likelihood_mode <- "bogus"
  cfg$models$exdqlm_multivar$likelihood_mode <- "bogus"
  cfg$models$ndlm_main$forecast_transfer_mode <- "bogus"
  cfg$models$ndlm_univar$forecast_transfer_mode <- "bogus"
  cfg$inputs$transfer_function_covariates$mode <- "bogus"
  cfg$inputs$transfer_function_covariates$scaling <- "bogus"

  errs <- unified_validate_config(cfg)

  expect_true(any(grepl("models\\.exdqlm_univar\\.likelihood_mode", errs)))
  expect_true(any(grepl("models\\.exdqlm_multivar\\.likelihood_mode", errs)))
  expect_true(any(grepl("models\\.ndlm_main\\.forecast_transfer_mode", errs)))
  expect_true(any(grepl("models\\.ndlm_univar\\.forecast_transfer_mode", errs)))
  expect_true(any(grepl("inputs\\.transfer_function_covariates\\.mode", errs)))
  expect_true(any(grepl("inputs\\.transfer_function_covariates\\.scaling", errs)))
})

test_that("transfer function covariate validation permits explicit transfer-level-only mode", {
  cfg <- unified_config_defaults()
  cfg$inputs$transfer_function_covariates <- list(
    mode = "none",
    scaling = "sd",
    base_covariates = character(0),
    engineered_terms = character(0)
  )

  expect_equal(unified_resolve_transfer_feature_columns(cfg), character(0))
  expect_false(any(grepl("transfer_function_covariates", unified_validate_config(cfg))))
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
  cfg$post$multivar_component_diagnostics$enabled <- "bad"
  cfg$post$multivar_component_diagnostics$fail_fast <- "bad"
  cfg$post$multivar_component_diagnostics$quantile <- 1
  cfg$post$multivar_component_diagnostics$pre_days <- -1L

  errs <- unified_validate_config(cfg)
  expect_true(any(grepl("fit\\.diagnostics\\.full_slice_psd", errs)))
  expect_true(any(grepl("fit\\.diagnostics\\.psd_warn_tol", errs)))
  expect_true(any(grepl("fit\\.diagnostics\\.psd_fail_tol", errs)))
  expect_true(any(grepl("post\\.crps_input_health\\.enabled", errs)))
  expect_true(any(grepl("post\\.crps_input_health\\.fail_fast", errs)))
  expect_true(any(grepl("post\\.crps_input_health\\.min_finite_share", errs)))
  expect_true(any(grepl("post\\.crps_input_health\\.max_abs", errs)))
  expect_true(any(grepl("post\\.multivar_component_diagnostics\\.enabled", errs)))
  expect_true(any(grepl("post\\.multivar_component_diagnostics\\.fail_fast", errs)))
  expect_true(any(grepl("post\\.multivar_component_diagnostics\\.quantile", errs)))
  expect_true(any(grepl("post\\.multivar_component_diagnostics\\.pre_days", errs)))
})

test_that("config validation restricts enabled multivar component diagnostics to q50", {
  cfg <- unified_config_defaults()
  cfg$post$multivar_component_diagnostics$enabled <- TRUE
  cfg$post$multivar_component_diagnostics$quantile <- 0.65

  errs <- unified_validate_config(cfg)

  expect_true(any(grepl("currently supports quantile=0.50 only", errs, fixed = TRUE)))
})

test_that("config validation accepts and rejects exdqlm multivar runtime guard controls", {
  cfg <- unified_config_defaults()
  tmp_root <- tempfile("guard_cfg")
  dir.create(tmp_root, recursive = TRUE, showWarnings = FALSE)
  parameters_path <- file.path(tmp_root, "parameters.csv")
  retros_path <- file.path(tmp_root, "retros.csv")
  nws_path <- file.path(tmp_root, "nws.csv")
  glofas_path <- file.path(tmp_root, "glofas.csv")
  bundle_path <- file.path(tmp_root, "bundle")
  file.create(parameters_path, retros_path, nws_path, glofas_path)
  dir.create(bundle_path, recursive = TRUE, showWarnings = FALSE)
  cfg$inputs$fit$parameters_path <- parameters_path
  cfg$inputs$fit$retros_path <- retros_path
  cfg$inputs$fit$nws_forecast_path <- nws_path
  cfg$inputs$fit$glofas_forecast_path <- glofas_path
  cfg$inputs$forecats$existing_bundle_path <- bundle_path
  cfg$fit$exdqlm_multivar$latent_ablation$mode <- "cap_e_u_and_e_inv_u"
  cfg$fit$exdqlm_multivar$latent_ablation$e_inv_u_cap <- 5000
  cfg$fit$exdqlm_multivar$latent_ablation$e_u_cap <- 1e6
  cfg$fit$exdqlm_multivar$pseudodata_guard$enabled <- TRUE
  cfg$fit$exdqlm_multivar$pseudodata_guard$mode <- "fail"
  cfg$fit$exdqlm_multivar$diagnostics$latent$enabled <- TRUE
  cfg$fit$exdqlm_multivar$diagnostics$latent$report_dir <- file.path(tmp_root, "latent_diag")
  cfg$fit$exdqlm_multivar$diagnostics$latent$top_k <- 12L
  cfg$fit$exdqlm_multivar$gamma_sigma$coherence_guard$enabled <- TRUE
  cfg$fit$exdqlm_multivar$gamma_sigma$coherence_guard$rollback_on_guard <- TRUE
  cfg$fit$exdqlm_multivar$gamma_sigma$coherence_guard$min_uts_psi <- 1e-8
  cfg$fit$exdqlm_multivar$gamma_sigma$coherence_guard$nonnegative_tol <- 1e-10
  cfg$fit$exdqlm_multivar$gamma_sigma$stabilization <- list(
    state_guard_start_iter = 1000L,
    state_norm_abs_cap_scale = "per_time",
    state_guard_step_backoff_enabled = TRUE,
    state_guard_step_backoff_factor = 0.2,
    state_guard_min_step_scale = 0.05,
    state_hold_freeze_latents_enabled = TRUE,
    state_guard_hold_step_scale_enabled = TRUE,
    state_guard_min_refreeze_iters = 1L,
    state_guard_min_hold_iters = 1L,
    median_state_guard_sigma_only_enabled = TRUE,
    median_state_guard_sigma_only_after = 1L,
    median_state_guard_sigma_only_anchor = "zero"
  )

  expect_equal(unified_validate_config(cfg), character(0))

  cfg_bad <- cfg
  cfg_bad$fit$exdqlm_multivar$latent_ablation$mode <- "bogus"
  cfg_bad$fit$exdqlm_multivar$latent_ablation$e_inv_u_cap <- 0
  cfg_bad$fit$exdqlm_multivar$latent_ablation$e_u_cap <- 0
  cfg_bad$fit$exdqlm_multivar$pseudodata_guard$enabled <- "yes"
  cfg_bad$fit$exdqlm_multivar$pseudodata_guard$mode <- "panic"
  cfg_bad$fit$exdqlm_multivar$pseudodata_guard$caps$fff_abs_cap <- -1
  cfg_bad$fit$exdqlm_multivar$pseudodata_guard$caps$e_inv_u_floor <- 0
  cfg_bad$fit$exdqlm_multivar$pseudodata_guard$caps$e_inv_u_floor_frac_cap <- 2
  cfg_bad$fit$exdqlm_multivar$forecast_health$history_latent_limit <- 0
  cfg_bad$fit$exdqlm_multivar$forecast_health$state_norm_sq_per_T_limit <- 0
  cfg_bad$fit$exdqlm_multivar$forecast_health$transfer_level_limit <- 0
  cfg_bad$fit$exdqlm_multivar$diagnostics$latent$enabled <- "yes"
  cfg_bad$fit$exdqlm_multivar$diagnostics$latent$top_k <- 0L
  cfg_bad$fit$exdqlm_multivar$diagnostics$latent$write_iteration_summary <- "yes"
  cfg_bad$fit$exdqlm_multivar$diagnostics$latent$write_top_cells <- "no"
  cfg_bad$fit$exdqlm_multivar$gamma_sigma$coherence_guard$enabled <- "yes"
  cfg_bad$fit$exdqlm_multivar$gamma_sigma$coherence_guard$rollback_on_guard <- "yes"
  cfg_bad$fit$exdqlm_multivar$gamma_sigma$coherence_guard$min_uts_psi <- 0
  cfg_bad$fit$exdqlm_multivar$gamma_sigma$coherence_guard$nonnegative_tol <- -1
  cfg_bad$fit$exdqlm_multivar$gamma_sigma$stabilization$state_guard_start_iter <- -1L
  cfg_bad$fit$exdqlm_multivar$gamma_sigma$stabilization$state_norm_abs_cap_scale <- "bad"
  cfg_bad$fit$exdqlm_multivar$gamma_sigma$stabilization$state_guard_step_backoff_enabled <- "yes"
  cfg_bad$fit$exdqlm_multivar$gamma_sigma$stabilization$state_guard_step_backoff_factor <- 1
  cfg_bad$fit$exdqlm_multivar$gamma_sigma$stabilization$state_guard_min_step_scale <- 0
  cfg_bad$fit$exdqlm_multivar$gamma_sigma$stabilization$state_hold_freeze_latents_enabled <- "yes"
  cfg_bad$fit$exdqlm_multivar$gamma_sigma$stabilization$state_guard_hold_step_scale_enabled <- "yes"
  cfg_bad$fit$exdqlm_multivar$gamma_sigma$stabilization$state_guard_min_refreeze_iters <- -1L
  cfg_bad$fit$exdqlm_multivar$gamma_sigma$stabilization$state_guard_min_hold_iters <- -1L
  cfg_bad$fit$exdqlm_multivar$gamma_sigma$stabilization$median_state_guard_sigma_only_enabled <- "yes"
  cfg_bad$fit$exdqlm_multivar$gamma_sigma$stabilization$median_state_guard_sigma_only_after <- -1L
  cfg_bad$fit$exdqlm_multivar$gamma_sigma$stabilization$median_state_guard_sigma_only_anchor <- "bad"
  cfg_bad$fit$exdqlm_multivar$legacy$post_save_objective_enabled <- "yes"
  cfg_bad$fit$exdqlm_multivar$legacy$post_save_jsd_enabled <- "no"
  cfg_bad$fit$exdqlm_multivar$legacy$post_save_jsd_gridsize <- 4L

  errs <- unified_validate_config(cfg_bad)
  expect_true(any(grepl("latent_ablation\\.mode", errs)))
  expect_true(any(grepl("latent_ablation\\.e_inv_u_cap", errs)))
  expect_true(any(grepl("latent_ablation\\.e_u_cap", errs)))
  expect_true(any(grepl("pseudodata_guard\\.enabled", errs)))
  expect_true(any(grepl("pseudodata_guard\\.mode", errs)))
  expect_true(any(grepl("pseudodata_guard\\.caps\\.fff_abs_cap", errs)))
  expect_true(any(grepl("pseudodata_guard\\.caps\\.e_inv_u_floor", errs)))
  expect_true(any(grepl("pseudodata_guard\\.caps\\.e_inv_u_floor_frac_cap", errs)))
  expect_true(any(grepl("forecast_health\\.history_latent_limit", errs)))
  expect_true(any(grepl("forecast_health\\.state_norm_sq_per_T_limit", errs)))
  expect_true(any(grepl("forecast_health\\.transfer_level_limit", errs)))
  expect_true(any(grepl("diagnostics\\.latent\\.enabled", errs)))
  expect_true(any(grepl("diagnostics\\.latent\\.top_k", errs)))
  expect_true(any(grepl("diagnostics\\.latent\\.write_iteration_summary", errs)))
  expect_true(any(grepl("diagnostics\\.latent\\.write_top_cells", errs)))
  expect_true(any(grepl("coherence_guard\\.enabled", errs)))
  expect_true(any(grepl("coherence_guard\\.rollback_on_guard", errs)))
  expect_true(any(grepl("coherence_guard\\.min_uts_psi", errs)))
  expect_true(any(grepl("coherence_guard\\.nonnegative_tol", errs)))
  expect_true(any(grepl("stabilization\\.state_guard_start_iter", errs)))
  expect_true(any(grepl("stabilization\\.state_norm_abs_cap_scale", errs)))
  expect_true(any(grepl("stabilization\\.state_guard_step_backoff_enabled", errs)))
  expect_true(any(grepl("stabilization\\.state_guard_step_backoff_factor", errs)))
  expect_true(any(grepl("stabilization\\.state_guard_min_step_scale", errs)))
  expect_true(any(grepl("stabilization\\.state_hold_freeze_latents_enabled", errs)))
  expect_true(any(grepl("stabilization\\.state_guard_hold_step_scale_enabled", errs)))
  expect_true(any(grepl("stabilization\\.state_guard_min_refreeze_iters", errs)))
  expect_true(any(grepl("stabilization\\.state_guard_min_hold_iters", errs)))
  expect_true(any(grepl("stabilization\\.median_state_guard_sigma_only_enabled", errs)))
  expect_true(any(grepl("stabilization\\.median_state_guard_sigma_only_after", errs)))
  expect_true(any(grepl("stabilization\\.median_state_guard_sigma_only_anchor", errs)))
  expect_true(any(grepl("post_save_objective_enabled", errs)))
  expect_true(any(grepl("post_save_jsd_enabled", errs)))
  expect_true(any(grepl("post_save_jsd_gridsize", errs)))
})
