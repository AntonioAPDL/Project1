# unified/stages/stage_forecats.R

unified_stage_forecats <- function(cfg, run_root, repo_root, manifest) {
  fore_root <- file.path(run_root, "forecats")
  dir.create(fore_root, recursive = TRUE, showWarnings = FALSE)

  mode <- cfg$inputs$forecats$mode
  if (identical(mode, "use_existing")) {
    bundle <- cfg$inputs$forecats$existing_bundle_path
    if (!is.null(bundle) && nzchar(bundle) && file.exists(bundle)) {
      manifest <- unified_manifest_add_artifact(manifest, bundle, storage_scale = "bundle")
    }
    return(list(manifest = manifest))
  }

  if (identical(mode, "build")) {
    cfg_path <- cfg$inputs$forecats$pipeline_config_path
    log_path <- file.path(fore_root, "forecats_pipeline.log")
    out <- system2(
      "Rscript",
      c("--vanilla", file.path("scripts", "forecats_pipeline.R"), "--config", cfg_path),
      stdout = TRUE,
      stderr = TRUE
    )
    writeLines(out, log_path, useBytes = TRUE)
    status <- attr(out, "status")
    if (!is.null(status) && status != 0) {
      stop(sprintf("forecats stage failed; see %s", log_path), call. = FALSE)
    }
  }

  list(manifest = manifest)
}
