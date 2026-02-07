# unified/stages/stage_fit.R

unified_stage_fit <- function(cfg, run_root, repo_root, manifest) {
  fit_root <- file.path(run_root, "fit")
  fit_inputs <- file.path(fit_root, "inputs")
  fit_outputs <- file.path(fit_root, "outputs")
  fit_logs <- file.path(fit_root, "logs")
  dir.create(fit_inputs, recursive = TRUE, showWarnings = FALSE)
  dir.create(fit_outputs, recursive = TRUE, showWarnings = FALSE)
  dir.create(fit_logs, recursive = TRUE, showWarnings = FALSE)

  legacy_scale <- cfg$scale_contract$legacy_fit_input_scale
  unified_assert_known_scale(legacy_scale, "scale_contract.legacy_fit_input_scale")

  parameters_copy <- file.path(fit_inputs, basename(cfg$inputs$fit$parameters_path))
  file.copy(cfg$inputs$fit$parameters_path, parameters_copy, overwrite = TRUE)

  adapted_retros <- file.path(fit_inputs, "retros_fit_adapter.csv")
  adapted_nws <- file.path(fit_inputs, "nws_fit_adapter.csv")
  adapted_glofas <- file.path(fit_inputs, "glofas_fit_adapter.csv")

  unified_adapt_csv_scale(
    input_path = cfg$inputs$fit$retros_path,
    output_path = adapted_retros,
    from_scale = cfg$inputs$fit$retros_storage_scale,
    to_scale = legacy_scale,
    positive_required = TRUE
  )
  manifest <- unified_manifest_add_scale_history(
    manifest,
    artifact = "fit_input/retros",
    from_scale = cfg$inputs$fit$retros_storage_scale,
    to_scale = legacy_scale,
    transform = sprintf("adapter_%s_to_%s", cfg$inputs$fit$retros_storage_scale, legacy_scale)
  )

  unified_adapt_csv_scale(
    input_path = cfg$inputs$fit$nws_forecast_path,
    output_path = adapted_nws,
    from_scale = cfg$inputs$fit$nws_storage_scale,
    to_scale = legacy_scale,
    positive_required = TRUE
  )
  manifest <- unified_manifest_add_scale_history(
    manifest,
    artifact = "fit_input/nws_forecast",
    from_scale = cfg$inputs$fit$nws_storage_scale,
    to_scale = legacy_scale,
    transform = sprintf("adapter_%s_to_%s", cfg$inputs$fit$nws_storage_scale, legacy_scale)
  )

  unified_adapt_csv_scale(
    input_path = cfg$inputs$fit$glofas_forecast_path,
    output_path = adapted_glofas,
    from_scale = cfg$inputs$fit$glofas_storage_scale,
    to_scale = legacy_scale,
    positive_required = TRUE
  )
  manifest <- unified_manifest_add_scale_history(
    manifest,
    artifact = "fit_input/glofas_forecast",
    from_scale = cfg$inputs$fit$glofas_storage_scale,
    to_scale = legacy_scale,
    transform = sprintf("adapter_%s_to_%s", cfg$inputs$fit$glofas_storage_scale, legacy_scale)
  )

  manifest <- unified_manifest_add_artifact(manifest, adapted_retros, storage_scale = legacy_scale)
  manifest <- unified_manifest_add_artifact(manifest, adapted_nws, storage_scale = legacy_scale)
  manifest <- unified_manifest_add_artifact(manifest, adapted_glofas, storage_scale = legacy_scale)

  env_overrides <- c(
    DISC_BASE_SEED = as.character(cfg$run$seed),
    DISC_USE_PREV = if (isTRUE(cfg$fit$warm_start$enabled)) "TRUE" else "FALSE",
    DISC_W_OUTPUT_DIR = fit_outputs,
    DISC_W_PARAMETERS_PATH = parameters_copy,
    DISC_W_RETROS_PATH = adapted_retros,
    DISC_W_NWS_PATH = adapted_nws,
    DISC_W_GLOFAS_PATH = adapted_glofas
  )

  prev <- Sys.getenv(names(env_overrides), unset = NA_character_)
  on.exit({
    for (nm in names(env_overrides)) {
      val <- prev[[nm]]
      if (is.na(val)) {
        do.call(Sys.unsetenv, list(nm))
      } else {
        do.call(Sys.setenv, setNames(list(val), nm))
      }
    }
  }, add = TRUE)
  do.call(Sys.setenv, as.list(env_overrides))

  quantiles <- as.numeric(cfg$fit$quantiles)
  for (q in quantiles) {
    q_label <- sprintf("%02d", as.integer(round(q * 100)))
    log_path <- file.path(fit_logs, sprintf("q%s.log", q_label))
    cmd_out <- system2(
      "Rscript",
      c("--vanilla", file.path("scripts", "run_DISC_Optimal_Synth_Ranges_W.R"), as.character(q), as.character(cfg$run$seed)),
      stdout = TRUE,
      stderr = TRUE
    )
    writeLines(cmd_out, log_path, useBytes = TRUE)
    status <- attr(cmd_out, "status")
    if (!is.null(status) && status != 0) {
      stop(sprintf("fit stage failed for quantile %s; see %s", q, log_path), call. = FALSE)
    }

    output_path <- file.path(fit_outputs, sprintf("DISC_variables_%d_exAL_synth_DISC.RData", as.integer(round(q * 100))))
    if (file.exists(output_path)) {
      manifest <- unified_manifest_add_artifact(manifest, output_path, storage_scale = "model_state", flow_domain = cfg$scale_contract$analysis_scale_fit_internal)
    }
  }

  list(manifest = manifest)
}
