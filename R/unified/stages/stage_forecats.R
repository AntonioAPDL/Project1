# unified/stages/stage_forecats.R

unified_stage_forecats <- function(cfg, run_root, repo_root, manifest) {
  fore_root <- file.path(run_root, "forecats")
  dir.create(fore_root, recursive = TRUE, showWarnings = FALSE)

  mode <- cfg$inputs$forecats$mode
  bundle_root <- NULL

  snapshot_cfg <- cfg$inputs$forecats$snapshot
  if (is.null(snapshot_cfg)) snapshot_cfg <- list()
  snapshot_enabled <- snapshot_cfg$enabled
  if (is.null(snapshot_enabled)) {
    snapshot_enabled <- identical(mode, "build")
  }
  snapshot_dest_rel <- snapshot_cfg$dest_rel
  if (is.null(snapshot_dest_rel) || !nzchar(snapshot_dest_rel)) {
    snapshot_dest_rel <- "inputs/shared/forecats_bundle"
  }
  snapshot_copy_list <- snapshot_cfg$copy_list
  if (is.null(snapshot_copy_list)) snapshot_copy_list <- list()
  snapshot_copy_list <- unlist(snapshot_copy_list, use.names = FALSE)

  if (identical(mode, "use_existing")) {
    bundle <- cfg$inputs$forecats$existing_bundle_path
    if (!is.null(bundle) && nzchar(bundle) && file.exists(bundle)) {
      if (dir.exists(bundle)) {
        bundle_root <- normalizePath(bundle, mustWork = FALSE)
      } else {
        bundle_root <- normalizePath(dirname(bundle), mustWork = FALSE)
        manifest <- unified_manifest_add_artifact(
          manifest,
          normalizePath(bundle, mustWork = FALSE),
          storage_scale = "bundle",
          role = "input_snapshot"
        )
      }
    }
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

    bundle_lines <- grep("^Bundle ready:\\s*", out, value = TRUE)
    if (length(bundle_lines) > 0L) {
      bundle_root <- sub("^Bundle ready:\\s*", "", bundle_lines[[length(bundle_lines)]])
      bundle_root <- normalizePath(bundle_root, mustWork = FALSE)
    }
    if (is.null(bundle_root) || !nzchar(bundle_root) || !dir.exists(bundle_root)) {
      fallback <- cfg$inputs$forecats$existing_bundle_path
      if (!is.null(fallback) && nzchar(fallback) && dir.exists(fallback)) {
        bundle_root <- normalizePath(fallback, mustWork = FALSE)
      }
    }
  }

  if (!identical(mode, "use_existing") && !identical(mode, "build")) {
    stop(sprintf("Unsupported forecats mode: %s", mode), call. = FALSE)
  }

  if (isTRUE(snapshot_enabled)) {
    if (is.null(bundle_root) || !nzchar(bundle_root) || !dir.exists(bundle_root)) {
      stop(
        sprintf(
          "forecats snapshot enabled but bundle root could not be determined for mode=%s. Check inputs.forecats settings.",
          mode
        ),
        call. = FALSE
      )
    }

    snapshot_root <- file.path(run_root, snapshot_dest_rel)
    dir.create(snapshot_root, recursive = TRUE, showWarnings = FALSE)

    rel_files <- snapshot_copy_list
    if (length(rel_files) == 0L) {
      rel_files <- c(
        "meta.yaml",
        "inputs/retros_daily.csv",
        "inputs/nws_weighted_daily.csv",
        "inputs/glofas_weighted_daily.csv"
      )
    }

    copy_one <- function(rel) {
      src <- file.path(bundle_root, rel)
      if (!file.exists(src)) {
        stop(sprintf("forecats snapshot missing required artifact: %s", src), call. = FALSE)
      }
      dst <- file.path(snapshot_root, rel)
      dir.create(dirname(dst), recursive = TRUE, showWarnings = FALSE)
      ok <- file.copy(src, dst, overwrite = TRUE)
      if (!isTRUE(ok) || !file.exists(dst)) {
        stop(sprintf("failed to copy forecats snapshot artifact: %s -> %s", src, dst), call. = FALSE)
      }
      storage_scale <- if (grepl("\\.csv$", dst, ignore.case = TRUE)) "raw_cms" else "input_snapshot"
      manifest <<- unified_manifest_add_artifact(
        manifest,
        normalizePath(dst, mustWork = FALSE),
        storage_scale = storage_scale,
        role = "input_snapshot"
      )
      normalizePath(dst, mustWork = FALSE)
    }

    copied <- vapply(rel_files, copy_one, character(1))
    names(copied) <- rel_files

    alias_map <- list(
      retros = "inputs/retros_daily.csv",
      nws_forecast = "inputs/nws_weighted_daily.csv",
      glofas_forecast = "inputs/glofas_weighted_daily.csv"
    )
    for (nm in names(alias_map)) {
      rel <- alias_map[[nm]]
      src <- if (rel %in% names(copied)) copied[[rel]] else file.path(snapshot_root, rel)
      if (!file.exists(src)) {
        stop(sprintf("forecats snapshot alias source missing for %s: %s", nm, src), call. = FALSE)
      }
      dst <- file.path(snapshot_root, sprintf("%s.csv", nm))
      ok <- file.copy(src, dst, overwrite = TRUE)
      if (!isTRUE(ok) || !file.exists(dst)) {
        stop(sprintf("failed to create forecats snapshot alias: %s -> %s", src, dst), call. = FALSE)
      }
      manifest <- unified_manifest_add_artifact(
        manifest,
        normalizePath(dst, mustWork = FALSE),
        storage_scale = "raw_cms",
        role = "input_snapshot"
      )
    }
  }

  list(manifest = manifest)
}
