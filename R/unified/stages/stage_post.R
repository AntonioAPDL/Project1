# unified/stages/stage_post.R

unified_stage_post <- function(cfg, run_root, repo_root, manifest) {
  post_root <- file.path(run_root, "post")
  post_inputs <- file.path(post_root, "inputs")
  dir.create(post_root, recursive = TRUE, showWarnings = FALSE)
  dir.create(post_inputs, recursive = TRUE, showWarnings = FALSE)

  legacy_scale <- cfg$scale_contract$legacy_post_input_scale
  unified_assert_known_scale(legacy_scale, "scale_contract.legacy_post_input_scale")

  adapted_retros <- file.path(post_inputs, "retros_post_adapter.csv")
  adapted_nws <- file.path(post_inputs, "nws_post_adapter.csv")
  adapted_glofas <- file.path(post_inputs, "glofas_post_adapter.csv")

  unified_adapt_csv_scale(
    input_path = cfg$inputs$fit$retros_path,
    output_path = adapted_retros,
    from_scale = cfg$inputs$fit$retros_storage_scale,
    to_scale = legacy_scale,
    positive_required = TRUE
  )
  manifest <- unified_manifest_add_scale_history(
    manifest,
    artifact = "post_input/retros",
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
    artifact = "post_input/nws_forecast",
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
    artifact = "post_input/glofas_forecast",
    from_scale = cfg$inputs$fit$glofas_storage_scale,
    to_scale = legacy_scale,
    transform = sprintf("adapter_%s_to_%s", cfg$inputs$fit$glofas_storage_scale, legacy_scale)
  )

  manifest <- unified_manifest_add_artifact(manifest, adapted_retros, storage_scale = legacy_scale)
  manifest <- unified_manifest_add_artifact(manifest, adapted_nws, storage_scale = legacy_scale)
  manifest <- unified_manifest_add_artifact(manifest, adapted_glofas, storage_scale = legacy_scale)

  run_id <- cfg$run$run_id
  env_overrides <- c(
    UNIFIED_RUN_ROOT = run_root,
    RUN_ID = run_id,
    PROFILE = if (isTRUE(cfg$post$profile)) "TRUE" else "FALSE",
    PROFILE_DETAIL = if (isTRUE(cfg$post$profile_detail)) "TRUE" else "FALSE",
    ENV_PROJECT_ROOT = repo_root,
    ENV_RETROS_PATH = adapted_retros,
    ENV_NWS_FORECAST_PATH = adapted_nws,
    ENV_GLOFAS_FORECAST_PATH = adapted_glofas
  )

  log_path <- file.path(post_root, "runner_console.txt")
  env_kv <- sprintf("%s=%s", names(env_overrides), unname(env_overrides))
  cmd_out <- system2(
    "Rscript",
    c("--vanilla", file.path("scripts", "run_environmetrics_figures.R")),
    stdout = TRUE,
    stderr = TRUE,
    env = env_kv
  )
  writeLines(cmd_out, log_path, useBytes = TRUE)
  status <- attr(cmd_out, "status")
  if (!is.null(status) && status != 0) {
    stop(sprintf("post stage failed; see %s", log_path), call. = FALSE)
  }

  out_dir <- file.path(run_root, "post", "outputs", run_id)
  if (dir.exists(out_dir)) {
    generated <- list.files(out_dir, full.names = TRUE)
    for (f in generated) {
      if (file.info(f)$isdir) next
      if (grepl("\\.png$", f, ignore.case = TRUE)) {
        manifest <- unified_manifest_add_artifact(manifest, f, storage_scale = "image_png", analysis_scale = "n/a")
      } else if (grepl("\\.rds$", f, ignore.case = TRUE)) {
        manifest <- unified_manifest_add_artifact(manifest, f, storage_scale = "model_state")
      }
    }
  }

  list(manifest = manifest)
}
