# unified/stages/stage_data_prep_shared.R

unified_stage_data_prep_shared <- function(cfg, run_root, repo_root, manifest) {
  shared_paths <- unified_shared_input_paths(run_root)
  shared_root <- shared_paths$root
  parameters_dir <- file.path(shared_root, "parameters")
  retros_dir <- file.path(shared_root, "retros")
  forecasts_dir <- file.path(shared_root, "forecasts")
  covariates_dir <- file.path(shared_root, "covariates")

  dir.create(parameters_dir, recursive = TRUE, showWarnings = FALSE)
  dir.create(retros_dir, recursive = TRUE, showWarnings = FALSE)
  dir.create(forecasts_dir, recursive = TRUE, showWarnings = FALSE)
  dir.create(covariates_dir, recursive = TRUE, showWarnings = FALSE)

  add_shared_file <- function(src_path, dst_path, storage_scale, role = "shared_input") {
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
      normalizePath(dst_path, mustWork = FALSE),
      storage_scale = storage_scale,
      role = role
    )
    manifest$inputs[[length(manifest$inputs) + 1L]] <<- list(
      path = normalizePath(dst_path, mustWork = FALSE),
      sha256 = unified_sha256(dst_path),
      storage_scale = storage_scale
    )
  }

  snapshot_dest_rel <- cfg$inputs$forecats$snapshot$dest_rel
  if (is.null(snapshot_dest_rel) || !nzchar(snapshot_dest_rel)) {
    snapshot_dest_rel <- "inputs/shared/forecats_bundle"
  }
  snapshot_root <- file.path(run_root, snapshot_dest_rel)
  prefer_snapshot <- isTRUE(cfg$inputs$shared$prefer_forecats_snapshot)
  snapshot_retros <- file.path(snapshot_root, "retros.csv")
  snapshot_nws <- file.path(snapshot_root, "nws_forecast.csv")
  snapshot_glofas <- file.path(snapshot_root, "glofas_forecast.csv")
  snapshot_ready <- file.exists(snapshot_retros) && file.exists(snapshot_nws) && file.exists(snapshot_glofas)

  source_retros <- cfg$inputs$fit$retros_path
  source_nws <- cfg$inputs$fit$nws_forecast_path
  source_glofas <- cfg$inputs$fit$glofas_forecast_path
  source_retros_scale <- cfg$inputs$fit$retros_storage_scale
  source_nws_scale <- cfg$inputs$fit$nws_storage_scale
  source_glofas_scale <- cfg$inputs$fit$glofas_storage_scale

  if (prefer_snapshot && snapshot_ready) {
    source_retros <- snapshot_retros
    source_nws <- snapshot_nws
    source_glofas <- snapshot_glofas
    source_retros_scale <- "raw_cms"
    source_nws_scale <- "raw_cms"
    source_glofas_scale <- "raw_cms"
  }

  add_shared_file(
    cfg$inputs$fit$parameters_path,
    shared_paths$parameters,
    storage_scale = "parameters_text"
  )
  add_shared_file(
    source_retros,
    shared_paths$retros,
    storage_scale = source_retros_scale
  )
  add_shared_file(
    source_nws,
    shared_paths$nws,
    storage_scale = source_nws_scale
  )
  add_shared_file(
    source_glofas,
    shared_paths$glofas,
    storage_scale = source_glofas_scale
  )

  fit_covariates <- cfg$inputs$fit$covariates
  if (is.null(fit_covariates)) fit_covariates <- list()
  if (length(fit_covariates) > 0L) {
    for (i in seq_along(fit_covariates)) {
      entry <- fit_covariates[[i]]
      if (!is.list(entry)) next
      cov_name <- if (is.null(entry$name)) sprintf("cov%02d", i) else as.character(entry$name)
      cov_path <- if (is.null(entry$path)) "" else as.character(entry$path)
      if (!nzchar(cov_path)) next
      cov_tag <- gsub("[^A-Za-z0-9]+", "_", cov_name)
      cov_tag <- gsub("^_+|_+$", "", cov_tag)
      if (!nzchar(cov_tag)) cov_tag <- sprintf("cov%02d", i)
      add_shared_file(
        cov_path,
        file.path(covariates_dir, sprintf("cov_%02d_%s.csv", i, cov_tag)),
        storage_scale = "table_csv"
      )
    }
  } else {
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
  }

  cov_required <- list.files(covariates_dir, full.names = TRUE)
  if (length(cov_required) == 0L) cov_required <- character(0)
  unified_validate_required_shared_inputs(
    run_root = run_root,
    stage_name = "data_prep_shared",
    manifest = manifest,
    enabled_models = cfg$models,
    required_covariates = cov_required
  )

  list(manifest = manifest)
}
