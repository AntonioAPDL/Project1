# unified/stages/stage_fit.R

unified_stage_fit <- function(cfg, run_root, repo_root, manifest) {
  oldwd <- getwd()
  on.exit(setwd(oldwd), add = TRUE)
  setwd(repo_root)

  fit_root <- file.path(run_root, "fit")
  fit_inputs <- file.path(fit_root, "inputs")
  dir.create(fit_inputs, recursive = TRUE, showWarnings = FALSE)

  shared_paths <- unified_shared_input_paths(run_root)
  use_shared_inputs <- isTRUE(cfg$stages$data_prep_shared) || dir.exists(shared_paths$root)
  if (use_shared_inputs) {
    shared_validation <- unified_validate_required_shared_inputs(
      run_root = run_root,
      stage_name = "fit",
      manifest = manifest,
      enabled_models = cfg$models
    )
    source_parameters <- shared_validation$paths$parameters
    source_retros <- shared_validation$paths$retros
    source_nws <- shared_validation$paths$nws
    source_glofas <- shared_validation$paths$glofas
    source_retros_scale <- shared_validation$scales$retros
    if (is.null(source_retros_scale) || !nzchar(source_retros_scale)) {
      source_retros_scale <- cfg$inputs$fit$retros_storage_scale
    }
    source_nws_scale <- shared_validation$scales$nws
    if (is.null(source_nws_scale) || !nzchar(source_nws_scale)) {
      source_nws_scale <- cfg$inputs$fit$nws_storage_scale
    }
    source_glofas_scale <- shared_validation$scales$glofas
    if (is.null(source_glofas_scale) || !nzchar(source_glofas_scale)) {
      source_glofas_scale <- cfg$inputs$fit$glofas_storage_scale
    }
  } else {
    source_parameters <- cfg$inputs$fit$parameters_path
    source_retros <- cfg$inputs$fit$retros_path
    source_nws <- cfg$inputs$fit$nws_forecast_path
    source_glofas <- cfg$inputs$fit$glofas_forecast_path
    source_retros_scale <- cfg$inputs$fit$retros_storage_scale
    source_nws_scale <- cfg$inputs$fit$nws_storage_scale
    source_glofas_scale <- cfg$inputs$fit$glofas_storage_scale
  }

  legacy_scale <- cfg$scale_contract$legacy_fit_input_scale
  unified_assert_known_scale(legacy_scale, "scale_contract.legacy_fit_input_scale")

  parameters_copy <- file.path(fit_inputs, basename(source_parameters))
  file.copy(source_parameters, parameters_copy, overwrite = TRUE)

  adapted_retros <- file.path(fit_inputs, "retros_fit_adapter.csv")
  adapted_nws <- file.path(fit_inputs, "nws_fit_adapter.csv")
  adapted_glofas <- file.path(fit_inputs, "glofas_fit_adapter.csv")

  unified_adapt_csv_scale(
    input_path = source_retros,
    output_path = adapted_retros,
    from_scale = source_retros_scale,
    to_scale = legacy_scale,
    positive_required = TRUE
  )
  manifest <- unified_manifest_add_scale_history(
    manifest,
    artifact = "fit_input/retros",
    from_scale = source_retros_scale,
    to_scale = legacy_scale,
    transform = sprintf("adapter_%s_to_%s", source_retros_scale, legacy_scale)
  )

  unified_adapt_csv_scale(
    input_path = source_nws,
    output_path = adapted_nws,
    from_scale = source_nws_scale,
    to_scale = legacy_scale,
    positive_required = TRUE
  )
  manifest <- unified_manifest_add_scale_history(
    manifest,
    artifact = "fit_input/nws_forecast",
    from_scale = source_nws_scale,
    to_scale = legacy_scale,
    transform = sprintf("adapter_%s_to_%s", source_nws_scale, legacy_scale)
  )

  unified_adapt_csv_scale(
    input_path = source_glofas,
    output_path = adapted_glofas,
    from_scale = source_glofas_scale,
    to_scale = legacy_scale,
    positive_required = TRUE
  )
  manifest <- unified_manifest_add_scale_history(
    manifest,
    artifact = "fit_input/glofas_forecast",
    from_scale = source_glofas_scale,
    to_scale = legacy_scale,
    transform = sprintf("adapter_%s_to_%s", source_glofas_scale, legacy_scale)
  )

  manifest <- unified_manifest_add_artifact(manifest, adapted_retros, storage_scale = legacy_scale)
  manifest <- unified_manifest_add_artifact(manifest, adapted_nws, storage_scale = legacy_scale)
  manifest <- unified_manifest_add_artifact(manifest, adapted_glofas, storage_scale = legacy_scale)

  quantiles <- as.numeric(cfg$fit$quantiles)

  if (isTRUE(cfg$models$run_exdqlm_multivar)) {
    run_one_quantile <- function(q) {
      q_num <- as.integer(round(q * 100))
      q_label <- sprintf("%02d", q_num)
      q_root <- file.path(fit_root, sprintf("q=%s", q_label))
      q_outputs <- file.path(q_root, "outputs")
      q_logs <- file.path(q_root, "logs")
      dir.create(q_outputs, recursive = TRUE, showWarnings = FALSE)
      dir.create(q_logs, recursive = TRUE, showWarnings = FALSE)

      env_overrides <- c(
        DISC_BASE_SEED = as.character(cfg$run$seed),
        DISC_USE_PREV = if (isTRUE(cfg$fit$warm_start$enabled)) "TRUE" else "FALSE",
        DISC_W_OUTPUT_DIR = q_outputs,
        DISC_W_PARAMETERS_PATH = parameters_copy,
        DISC_W_RETROS_PATH = adapted_retros,
        DISC_W_NWS_PATH = adapted_nws,
        DISC_W_GLOFAS_PATH = adapted_glofas
      )
      env_kv <- sprintf("%s=%s", names(env_overrides), unname(env_overrides))

      log_path <- file.path(q_logs, "fit.log")
      cmd_out <- system2(
        "Rscript",
        c("--vanilla", file.path("scripts", "run_DISC_Optimal_Synth_Ranges_W.R"), as.character(q), as.character(cfg$run$seed)),
        stdout = TRUE,
        stderr = TRUE,
        env = env_kv
      )
      writeLines(cmd_out, log_path, useBytes = TRUE)

      output_path <- file.path(q_outputs, sprintf("DISC_variables_%d_exAL_synth_DISC.RData", q_num))
      list(
        quantile = q,
        output_path = output_path,
        log_path = log_path,
        status = attr(cmd_out, "status")
      )
    }

    workers <- suppressWarnings(as.integer(cfg$run$threads$mc_cores))
    if (!is.finite(workers) || workers < 1) workers <- 1L
    workers <- min(workers, length(quantiles))

    results <- if (workers > 1 && .Platform$OS.type != "windows") {
      parallel::mclapply(quantiles, run_one_quantile, mc.cores = workers)
    } else {
      lapply(quantiles, run_one_quantile)
    }

    for (res in results) {
      if (!is.null(res$status) && res$status != 0) {
        stop(sprintf("fit stage failed for quantile %s; see %s", res$quantile, res$log_path), call. = FALSE)
      }
      if (file.exists(res$output_path)) {
        manifest <- unified_manifest_add_artifact(
          manifest,
          res$output_path,
          storage_scale = "model_state",
          flow_domain = cfg$scale_contract$analysis_scale_fit_internal
        )
      }
    }
  }

  if (isTRUE(cfg$models$run_exdqlm_univar)) {
    univar_script <- file.path(repo_root, "OptimalModelSLexAL.r")
    if (!file.exists(univar_script)) {
      stop(sprintf("legacy univariate script not found: %s", univar_script), call. = FALSE)
    }

    for (q in quantiles) {
      q_num <- as.integer(round(q * 100))
      q_lab <- sprintf("%02d", q_num)

      q_root <- file.path(fit_root, "exdqlm_univar", sprintf("q=%s", q_lab))
      q_outputs <- file.path(q_root, "outputs")
      q_logs <- file.path(q_root, "logs")
      dir.create(q_outputs, recursive = TRUE, showWarnings = FALSE)
      dir.create(q_logs, recursive = TRUE, showWarnings = FALSE)

      output_path <- file.path(q_outputs, sprintf("variables_%s_exAL_synth_DISC_uni.RData", q_lab))
      log_path <- file.path(q_logs, "univar_legacy.log")
      env_kv <- sprintf("UNIFIED_UNIV_RDATA_OUT=%s", output_path)

      cmd_out <- system2(
        "Rscript",
        c("--vanilla", univar_script, as.character(q)),
        stdout = TRUE,
        stderr = TRUE,
        env = env_kv
      )
      writeLines(cmd_out, log_path, useBytes = TRUE)
      status <- attr(cmd_out, "status")
      if (!is.null(status) && status != 0) {
        stop(sprintf("legacy univariate fit failed for quantile %s; see %s", q, log_path), call. = FALSE)
      }
      if (!file.exists(output_path)) {
        stop(sprintf("legacy univariate output missing for quantile %s: %s", q, output_path), call. = FALSE)
      }

      manifest <- unified_manifest_add_artifact(
        manifest,
        output_path,
        storage_scale = "model_state",
        flow_domain = cfg$scale_contract$analysis_scale_fit_internal
      )
    }
  }

  if (isTRUE(cfg$models$run_ndlm_main)) {
    ndlm_script <- file.path(repo_root, "DISC_Optimal_Synth_Ranges_NDLM.r")
    if (!file.exists(ndlm_script)) {
      stop(sprintf("legacy NDLM script not found: %s", ndlm_script), call. = FALSE)
    }

    ndlm_root <- file.path(fit_root, "ndlm_main")
    ndlm_outputs <- file.path(ndlm_root, "outputs")
    ndlm_logs <- file.path(ndlm_root, "logs")
    dir.create(ndlm_outputs, recursive = TRUE, showWarnings = FALSE)
    dir.create(ndlm_logs, recursive = TRUE, showWarnings = FALSE)

    output_path <- file.path(ndlm_outputs, "DISC_variables_50_NDLM_synth_DISC.RData")
    log_path <- file.path(ndlm_logs, "ndlm_legacy.log")
    env_kv <- sprintf("UNIFIED_NDLM_RDATA_OUT=%s", output_path)

    cmd_out <- system2(
      "Rscript",
      c("--vanilla", ndlm_script),
      stdout = TRUE,
      stderr = TRUE,
      env = env_kv
    )
    writeLines(cmd_out, log_path, useBytes = TRUE)
    status <- attr(cmd_out, "status")
    if (!is.null(status) && status != 0) {
      stop(sprintf("legacy NDLM fit failed; see %s", log_path), call. = FALSE)
    }
    if (!file.exists(output_path)) {
      stop(sprintf("legacy NDLM output missing: %s", output_path), call. = FALSE)
    }

    manifest <- unified_manifest_add_artifact(
      manifest,
      output_path,
      storage_scale = "model_state",
      flow_domain = cfg$scale_contract$analysis_scale_fit_internal
    )
  }

  list(manifest = manifest)
}
