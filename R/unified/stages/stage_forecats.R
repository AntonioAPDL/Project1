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

  pick_latest_file <- function(paths) {
    paths <- unique(normalizePath(paths[file.exists(paths)], mustWork = FALSE))
    if (length(paths) == 0L) return("")
    finfo <- file.info(paths)
    ord <- order(finfo$mtime, decreasing = TRUE, na.last = NA)
    if (length(ord) == 0L) return(paths[[1]])
    paths[[ord[[1]]]]
  }

  csv_has_finite_numeric <- function(path, min_rows = 1L, min_numeric_cols = 1L) {
    if (!file.exists(path)) return(FALSE)
    dat <- tryCatch(
      utils::read.csv(path, stringsAsFactors = FALSE, check.names = FALSE),
      error = function(e) NULL
    )
    if (!is.data.frame(dat)) return(FALSE)
    if (nrow(dat) < min_rows) return(FALSE)
    num_cols <- names(dat)[vapply(dat, is.numeric, logical(1))]
    if (length(num_cols) < min_numeric_cols) return(FALSE)
    vals <- as.matrix(dat[, num_cols, drop = FALSE])
    !any(!is.finite(vals), na.rm = TRUE)
  }

  choose_snapshot_alias_source <- function(snapshot_root, candidates, label, min_rows = 1L, min_numeric_cols = 1L) {
    candidate_paths <- normalizePath(file.path(snapshot_root, candidates), mustWork = FALSE)
    existing <- candidate_paths[file.exists(candidate_paths)]
    if (length(existing) == 0L) {
      stop(
        sprintf("forecats snapshot alias selection for %s has no existing candidates: %s", label, paste(candidates, collapse = ", ")),
        call. = FALSE
      )
    }
    for (path in existing) {
      if (csv_has_finite_numeric(path, min_rows = min_rows, min_numeric_cols = min_numeric_cols)) {
        return(path)
      }
    }
    stop(
      sprintf(
        "forecats snapshot alias selection for %s found no finite numeric CSV candidates. Checked: %s",
        label,
        paste(existing, collapse = ", ")
      ),
      call. = FALSE
    )
  }

  resolve_member_source <- function(bundle_root, kind, cfg, repo_root) {
    stopifnot(kind %in% c("nws", "glofas"))

    bundle_candidates <- if (identical(kind, "nws")) {
      c(
        "inputs/nws_members.csv",
        "inputs/nws_members_daily.csv",
        "inputs/nws_forecast.csv"
      )
    } else {
      c(
        "inputs/glofas_members.csv",
        "inputs/glofas_members_daily.csv",
        "inputs/glofas_members_forecast.csv",
        "inputs/glofas_forecast.csv"
      )
    }

    bundle_paths <- normalizePath(file.path(bundle_root, bundle_candidates), mustWork = FALSE)
    bundle_paths <- bundle_paths[file.exists(bundle_paths)]
    if (length(bundle_paths) > 0L) {
      return(bundle_paths[[1]])
    }

    site_id <- cfg$site$usgs_site
    if (is.null(site_id)) site_id <- ""
    site_id <- as.character(site_id)
    cutoff <- cfg$dates$cutoff_date
    if (is.null(cutoff)) cutoff <- ""
    cutoff <- as.character(cutoff)
    if (!nzchar(site_id) || !nzchar(cutoff)) {
      return("")
    }

    cache_glob <- if (identical(kind, "nws")) {
      file.path(
        repo_root, "data", "forecats_cache", sprintf("site=%s", site_id),
        "run_id=*", "forecast_cache", "nws", sprintf("cutoff_date=%s", cutoff), "nws_members.csv"
      )
    } else {
      file.path(
        repo_root, "data", "forecats_cache", sprintf("site=%s", site_id),
        "run_id=*", "forecast_cache", "glofas", sprintf("issue_date=%s", cutoff), "glofas_members.csv"
      )
    }

    pick_latest_file(Sys.glob(cache_glob))
  }

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

    nws_members_src <- resolve_member_source(bundle_root, kind = "nws", cfg = cfg, repo_root = repo_root)
    if (!nzchar(nws_members_src) || !file.exists(nws_members_src)) {
      stop(
        paste0(
          "forecats snapshot could not locate member-level NWS forecast CSV. ",
          "Expected bundle member CSV or data/forecats_cache/.../forecast_cache/nws/cutoff_date=<cutoff>/nws_members.csv"
        ),
        call. = FALSE
      )
    }
    glofas_members_src <- resolve_member_source(bundle_root, kind = "glofas", cfg = cfg, repo_root = repo_root)
    if (!nzchar(glofas_members_src) || !file.exists(glofas_members_src)) {
      stop(
        paste0(
          "forecats snapshot could not locate member-level GloFAS forecast CSV. ",
          "Expected bundle member CSV or data/forecats_cache/.../forecast_cache/glofas/issue_date=<cutoff>/glofas_members.csv"
        ),
        call. = FALSE
      )
    }

    copy_external <- function(src, rel, storage_scale = "raw_cms", role = "input_snapshot") {
      dst <- file.path(snapshot_root, rel)
      dir.create(dirname(dst), recursive = TRUE, showWarnings = FALSE)
      ok <- file.copy(src, dst, overwrite = TRUE)
      if (!isTRUE(ok) || !file.exists(dst)) {
        stop(sprintf("failed to copy forecats snapshot artifact: %s -> %s", src, dst), call. = FALSE)
      }
      manifest <<- unified_manifest_add_artifact(
        manifest,
        normalizePath(dst, mustWork = FALSE),
        storage_scale = storage_scale,
        role = role
      )
      normalizePath(dst, mustWork = FALSE)
    }

    copied[["inputs/nws_members.csv"]] <- copy_external(nws_members_src, "inputs/nws_members.csv", storage_scale = "raw_cms")
    copied[["inputs/glofas_members.csv"]] <- copy_external(glofas_members_src, "inputs/glofas_members.csv", storage_scale = "raw_cms")

    source_map_path <- file.path(snapshot_root, "snapshot_source_map.txt")
    writeLines(
      c(
        sprintf("mode=%s", mode),
        sprintf("bundle_root=%s", bundle_root),
        sprintf("nws_members_source=%s", nws_members_src),
        sprintf("glofas_members_source=%s", glofas_members_src)
      ),
      con = source_map_path
    )
    manifest <- unified_manifest_add_artifact(
      manifest,
      normalizePath(source_map_path, mustWork = FALSE),
      storage_scale = "text",
      role = "input_snapshot"
    )

    alias_sources <- list(
      retros = choose_snapshot_alias_source(
        snapshot_root = snapshot_root,
        candidates = c("inputs/retros_daily.csv", "retros.csv"),
        label = "retros",
        min_rows = 10L,
        min_numeric_cols = 2L
      ),
      nws_forecast = choose_snapshot_alias_source(
        snapshot_root = snapshot_root,
        candidates = c("inputs/nws_members.csv", "inputs/nws_weighted_daily.csv", "inputs/nws_forecast.csv"),
        label = "nws_forecast",
        min_rows = 10L,
        min_numeric_cols = 2L
      ),
      glofas_forecast = choose_snapshot_alias_source(
        snapshot_root = snapshot_root,
        candidates = c("inputs/glofas_members.csv"),
        label = "glofas_forecast",
        min_rows = 20L,
        min_numeric_cols = 20L
      )
    )
    unified_validate_glofas_members_csv(alias_sources$glofas_forecast, stage_name = "forecats/snapshot_alias")

    for (nm in names(alias_sources)) {
      src <- alias_sources[[nm]]
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
