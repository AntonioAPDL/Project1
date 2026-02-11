# unified/stages/stage_data_prep_shared.R

unified_stage_data_prep_shared <- function(cfg, run_root, repo_root, manifest) {
  shared_root <- file.path(run_root, "inputs", "shared")
  parameters_dir <- file.path(shared_root, "parameters")
  retros_dir <- file.path(shared_root, "retros")
  forecasts_dir <- file.path(shared_root, "forecasts")
  covariates_dir <- file.path(shared_root, "covariates")

  dir.create(parameters_dir, recursive = TRUE, showWarnings = FALSE)
  dir.create(retros_dir, recursive = TRUE, showWarnings = FALSE)
  dir.create(forecasts_dir, recursive = TRUE, showWarnings = FALSE)
  dir.create(covariates_dir, recursive = TRUE, showWarnings = FALSE)

  add_shared_file <- function(src_path, dst_path, storage_scale) {
    if (is.null(src_path) || !nzchar(src_path) || !file.exists(src_path)) {
      stop(sprintf("data_prep_shared input missing: %s", as.character(src_path)), call. = FALSE)
    }
    dir.create(dirname(dst_path), recursive = TRUE, showWarnings = FALSE)
    ok <- file.copy(src_path, dst_path, overwrite = TRUE)
    if (!isTRUE(ok) || !file.exists(dst_path)) {
      stop(sprintf("failed to copy shared input: %s -> %s", src_path, dst_path), call. = FALSE)
    }

    manifest <<- unified_manifest_add_artifact(
      manifest,
      dst_path,
      storage_scale = storage_scale
    )
    manifest$inputs[[length(manifest$inputs) + 1L]] <<- list(
      path = dst_path,
      sha256 = unified_sha256(dst_path),
      storage_scale = storage_scale
    )
  }

  add_shared_file(
    cfg$inputs$fit$parameters_path,
    file.path(parameters_dir, "parameters.txt"),
    storage_scale = "parameters_text"
  )
  add_shared_file(
    cfg$inputs$fit$retros_path,
    file.path(retros_dir, "retros.csv"),
    storage_scale = cfg$inputs$fit$retros_storage_scale
  )
  add_shared_file(
    cfg$inputs$fit$nws_forecast_path,
    file.path(forecasts_dir, "nws_forecast.csv"),
    storage_scale = cfg$inputs$fit$nws_storage_scale
  )
  add_shared_file(
    cfg$inputs$fit$glofas_forecast_path,
    file.path(forecasts_dir, "glofas_forecast.csv"),
    storage_scale = cfg$inputs$fit$glofas_storage_scale
  )

  shared_covariates <- cfg$inputs$shared_covariates
  if (is.null(shared_covariates)) {
    shared_covariates <- list()
  }
  shared_covariates <- unlist(shared_covariates, use.names = FALSE)
  if (length(shared_covariates) > 0L) {
    for (cov_path in shared_covariates) {
      cov_path <- as.character(cov_path)
      if (!nzchar(cov_path)) next
      add_shared_file(
        cov_path,
        file.path(covariates_dir, basename(cov_path)),
        storage_scale = "table_csv"
      )
    }
  }

  list(manifest = manifest)
}
