# unified/post_artifact_contract.R

unified_iso_utc <- function(x = Sys.time()) {
  format(as.POSIXct(x, tz = "UTC"), "%Y-%m-%dT%H:%M:%SZ", tz = "UTC")
}

unified_post_artifact_type <- function(path, scope = c("outputs", "cache")) {
  scope <- match.arg(scope)
  base <- basename(path)
  ext <- tolower(tools::file_ext(base))

  if (scope == "cache") {
    if (base %in% c("y_reps_f.rds", "y_reps.rds", "y_reps_f_new.rds", "y_reps_new.rds", "y_hist_uni.rds", "y_forecast_uni.rds")) {
      return("synthesis_cache")
    }
    if (ext == "rds") return("cache_rds")
    return("cache_other")
  }

  if (base == "post_smoke_marker.txt") return("smoke_marker")
  if (base %in% c("post_artifacts_manifest.csv", "post_artifacts_summary.json")) return("post_artifact_meta")

  if (ext %in% c("png", "pdf", "svg", "jpg", "jpeg", "tif", "tiff")) return("figure")

  if (base %in% c(
    "gamma_summary.csv", "sigma_summary.csv", "covariate_effects_summary.csv",
    "gamma_summary.rds", "sigma_summary.rds", "covariate_effects_summary.rds",
    "gamma_summary.tex", "sigma_summary.tex", "covariate_effects_summary.tex",
    "posterior_table_exports_manifest.csv", "posterior_table_exports_README.md"
  )) {
    return("table")
  }
  if (ext %in% c("csv", "rds", "tex", "md") && grepl("(summary|table|manifest)", base, ignore.case = TRUE)) {
    return("table")
  }

  if (ext %in% c("csv", "tsv")) return("tabular")
  if (ext %in% c("txt", "json", "yaml", "yml", "log")) return("text")
  "other"
}

unified_collect_post_artifacts <- function(outputs_dir, cache_dir = NULL) {
  collect_scope <- function(root_dir, scope) {
    if (is.null(root_dir) || !nzchar(root_dir) || !dir.exists(root_dir)) {
      return(data.frame(
        scope = character(0),
        relative_path = character(0),
        artifact_type = character(0),
        extension = character(0),
        bytes = numeric(0),
        modified_at_utc = character(0),
        abs_path = character(0),
        stringsAsFactors = FALSE
      ))
    }

    root_abs <- normalizePath(root_dir, mustWork = TRUE)
    files <- list.files(root_abs, recursive = TRUE, full.names = TRUE, all.files = FALSE, no.. = TRUE)
    files <- files[file.info(files)$isdir %in% FALSE]
    if (length(files) == 0L) {
      return(data.frame(
        scope = character(0),
        relative_path = character(0),
        artifact_type = character(0),
        extension = character(0),
        bytes = numeric(0),
        modified_at_utc = character(0),
        abs_path = character(0),
        stringsAsFactors = FALSE
      ))
    }

    prefix <- paste0(root_abs, .Platform$file.sep)
    rel <- ifelse(startsWith(files, prefix), substring(files, nchar(prefix) + 1L), basename(files))
    ext <- tolower(tools::file_ext(files))
    info <- file.info(files)
    mtime <- ifelse(is.na(info$mtime), "", unified_iso_utc(info$mtime))

    data.frame(
      scope = rep(scope, length(files)),
      relative_path = rel,
      artifact_type = vapply(files, function(p) unified_post_artifact_type(p, scope = scope), character(1)),
      extension = ext,
      bytes = as.numeric(info$size),
      modified_at_utc = mtime,
      abs_path = files,
      stringsAsFactors = FALSE
    )
  }

  out_df <- collect_scope(outputs_dir, "outputs")
  cache_df <- collect_scope(cache_dir, "cache")
  all_df <- rbind(out_df, cache_df)
  if (nrow(all_df) == 0L) {
    return(all_df)
  }
  ord <- order(all_df$scope, all_df$relative_path, method = "radix", na.last = TRUE)
  rownames(all_df) <- NULL
  all_df[ord, , drop = FALSE]
}

unified_validate_synthesis_cube_file <- function(path, context) {
  if (!file.exists(path)) {
    return(list(ok = FALSE, message = sprintf("%s missing: %s", context, path)))
  }
  obj <- tryCatch(readRDS(path), error = function(e) e)
  if (inherits(obj, "error")) {
    return(list(ok = FALSE, message = sprintf("%s unreadable (%s)", context, conditionMessage(obj))))
  }
  d <- dim(obj)
  ok <- is.numeric(obj) && !is.null(d) && length(d) == 3L && all(is.finite(d)) && all(d > 0)
  if (!ok) {
    return(list(ok = FALSE, message = sprintf("%s invalid shape; expected numeric 3D array.", context)))
  }
  list(ok = TRUE, message = "")
}

unified_post_contract_check <- function(
  artifacts_df,
  outputs_dir,
  cache_dir = NULL,
  post_figures = TRUE,
  export_tables = TRUE,
  post_smoke_fast = FALSE,
  model_run_exdqlm_multivar = TRUE,
  model_run_exdqlm_univar = TRUE,
  model_run_ndlm_main = TRUE
) {
  if (is.null(artifacts_df)) {
    artifacts_df <- unified_collect_post_artifacts(outputs_dir = outputs_dir, cache_dir = cache_dir)
  }

  checks <- list()
  messages <- character(0)
  missing_paths <- character(0)

  outputs_df <- artifacts_df[artifacts_df$scope == "outputs", , drop = FALSE]
  output_basenames <- if (nrow(outputs_df) > 0L) basename(outputs_df$relative_path) else character(0)
  has_output_file <- function(name) {
    if (!nchar(name)) return(FALSE)
    any(output_basenames == name)
  }
  has_any_output_file <- function(names_vec) {
    if (length(names_vec) == 0L) return(FALSE)
    any(vapply(as.character(names_vec), has_output_file, logical(1)))
  }
  checks$outputs_nonempty <- nrow(outputs_df) > 0L
  if (!checks$outputs_nonempty) {
    messages <- c(messages, "post outputs directory has no files.")
  }

  multivar_only_mode <- isTRUE(model_run_exdqlm_multivar) &&
    !isTRUE(model_run_exdqlm_univar) &&
    !isTRUE(model_run_ndlm_main)

  if (!isTRUE(post_figures)) {
    marker_path <- file.path(outputs_dir, "post_smoke_marker.txt")
    checks$smoke_marker_exists <- file.exists(marker_path)
    if (!checks$smoke_marker_exists) {
      missing_paths <- c(missing_paths, marker_path)
      messages <- c(messages, "smoke marker missing for non-figures post mode.")
    }
  } else {
    checks$has_figure <- any(outputs_df$artifact_type == "figure")
    if (!checks$has_figure) {
      messages <- c(messages, "no figure artifacts found under post outputs.")
    }

    if (isTRUE(post_smoke_fast)) {
      # Smoke-fast figure runs are intentionally minimal and do not emit full
      # synthesis cache cubes or table-export artifacts.
      checks$synthesis_cache_files_present <- TRUE
      checks$synthesis_core_shapes_ok <- TRUE
      checks$table_exports_present <- TRUE
    } else if (multivar_only_mode) {
      # Multivariate-only post runs use the dedicated 40_figures_multivar_only
      # module. They intentionally skip full synthesis-cache cubes and
      # cross-family table exports, but must still produce core diagnostics.
      checks$synthesis_cache_files_present <- TRUE
      checks$synthesis_core_shapes_ok <- TRUE

      checks$multivar_fit_figure_present <- has_any_output_file(c(
        "multivar_fit_mu_vs_observed_loglog.png",
        "multivar_fit_mu_vs_observed_recent_loglog.png"
      ))
      if (!checks$multivar_fit_figure_present) {
        messages <- c(messages, "missing multivariate fit figure outputs.")
      }

      checks$multivar_forecast_figure_present <- has_any_output_file(c(
        "multivar_forecast_window_mu_vs_future_usgs.png",
        "multivar_forecast_window_multivar_vs_ensembles.png",
        "multivar_forecast_window_ensemble_members.png"
      ))
      if (!checks$multivar_forecast_figure_present) {
        messages <- c(messages, "missing multivariate forecast-window figure outputs.")
      }

      checks$multivar_trace_figure_present <- has_output_file("multivar_elbo_trace_q50.png")
      if (!checks$multivar_trace_figure_present) {
        messages <- c(messages, "missing multivariate ELBO trace figure output.")
      }

      required_multivar_csv <- c(
        "multivar_trace_summary_q50.csv",
        "multivar_forecast_window_q50_summary.csv",
        "multivar_forecast_window_q50_metrics.csv"
      )
      missing_multivar_csv <- required_multivar_csv[!vapply(required_multivar_csv, has_output_file, logical(1))]
      checks$multivar_summary_csv_present <- length(missing_multivar_csv) == 0L
      if (!checks$multivar_summary_csv_present) {
        missing_paths <- c(missing_paths, file.path(outputs_dir, missing_multivar_csv))
        messages <- c(messages, sprintf("missing multivariate summary exports: %s", paste(basename(missing_multivar_csv), collapse = ", ")))
      }

      # For multivar-only profiles, treat required multivar CSV diagnostics as
      # the table contract when export_tables is enabled.
      checks$table_exports_present <- TRUE
      if (isTRUE(export_tables)) {
        checks$table_exports_present <- isTRUE(checks$multivar_summary_csv_present)
      }
    } else {
      required_cache <- c("y_reps_f.rds", "y_reps.rds", "y_reps_f_new.rds", "y_reps_new.rds")
      cache_paths <- file.path(cache_dir, required_cache)
      missing_cache <- cache_paths[!file.exists(cache_paths)]
      checks$synthesis_cache_files_present <- length(missing_cache) == 0L
      if (!checks$synthesis_cache_files_present) {
        missing_paths <- c(missing_paths, missing_cache)
        messages <- c(messages, sprintf("missing synthesis cache files: %s", paste(basename(missing_cache), collapse = ", ")))
      }

      core_shape_checks <- list(
        unified_validate_synthesis_cube_file(file.path(cache_dir, "y_reps_f.rds"), "y_reps_f.rds"),
        unified_validate_synthesis_cube_file(file.path(cache_dir, "y_reps.rds"), "y_reps.rds")
      )
      core_shape_ok <- all(vapply(core_shape_checks, `[[`, logical(1), "ok"))
      checks$synthesis_core_shapes_ok <- core_shape_ok
      if (!core_shape_ok) {
        bad_msgs <- vapply(core_shape_checks[!vapply(core_shape_checks, `[[`, logical(1), "ok")], `[[`, character(1), "message")
        messages <- c(messages, bad_msgs)
      }

      if (isTRUE(export_tables)) {
        required_tables <- c(
          "gamma_summary.csv",
          "sigma_summary.csv",
          "covariate_effects_summary.csv",
          "posterior_table_exports_manifest.csv",
          "posterior_table_exports_README.md"
        )
        missing_tables <- required_tables[!vapply(required_tables, has_output_file, logical(1))]
        checks$table_exports_present <- length(missing_tables) == 0L
        if (!checks$table_exports_present) {
          missing_paths <- c(missing_paths, file.path(outputs_dir, "tables", missing_tables))
          messages <- c(messages, sprintf("missing table exports: %s", paste(basename(missing_tables), collapse = ", ")))
        }
      } else {
        checks$table_exports_present <- TRUE
      }
    }
  }

  checks_vec <- unlist(checks, use.names = TRUE)
  status <- length(checks_vec) > 0L && all(checks_vec)
  list(
    status = isTRUE(status),
    checks = checks,
    messages = unique(messages),
    missing_paths = unique(normalizePath(missing_paths, mustWork = FALSE))
  )
}

unified_write_post_artifact_reports <- function(
  artifacts_df,
  outputs_dir,
  run_id = "",
  cache_dir = NULL,
  contract = NULL,
  manifest_path = NULL,
  summary_path = NULL
) {
  if (is.null(manifest_path) || !nzchar(manifest_path)) {
    manifest_path <- file.path(outputs_dir, "post_artifacts_manifest.csv")
  }
  if (is.null(summary_path) || !nzchar(summary_path)) {
    summary_path <- file.path(outputs_dir, "post_artifacts_summary.json")
  }

  dir.create(dirname(manifest_path), recursive = TRUE, showWarnings = FALSE)
  dir.create(dirname(summary_path), recursive = TRUE, showWarnings = FALSE)

  if (is.null(artifacts_df)) {
    artifacts_df <- unified_collect_post_artifacts(outputs_dir = outputs_dir, cache_dir = cache_dir)
  }

  manifest_df <- artifacts_df[, c("scope", "relative_path", "artifact_type", "extension", "bytes", "modified_at_utc"), drop = FALSE]
  utils::write.csv(manifest_df, file = manifest_path, row.names = FALSE)

  counts <- if (nrow(manifest_df) == 0L) {
    data.frame(scope = character(0), artifact_type = character(0), count = integer(0), stringsAsFactors = FALSE)
  } else {
    as.data.frame(table(manifest_df$scope, manifest_df$artifact_type), stringsAsFactors = FALSE)
  }
  names(counts) <- c("scope", "artifact_type", "count")

  summary <- list(
    run_id = as.character(run_id),
    generated_at_utc = unified_iso_utc(),
    outputs_dir = normalizePath(outputs_dir, mustWork = FALSE),
    cache_dir = normalizePath(cache_dir, mustWork = FALSE),
    total_artifact_files = nrow(manifest_df),
    counts = counts,
    contract = contract
  )

  if (requireNamespace("jsonlite", quietly = TRUE)) {
    jsonlite::write_json(summary, path = summary_path, auto_unbox = TRUE, pretty = TRUE)
  } else {
    lines <- c(
      "{",
      sprintf("  \"run_id\": \"%s\",", as.character(run_id)),
      sprintf("  \"generated_at_utc\": \"%s\",", unified_iso_utc()),
      sprintf("  \"total_artifact_files\": %d", as.integer(nrow(manifest_df))),
      "}"
    )
    writeLines(lines, con = summary_path, useBytes = TRUE)
  }

  list(
    manifest_path = manifest_path,
    summary_path = summary_path,
    manifest_df = manifest_df
  )
}
