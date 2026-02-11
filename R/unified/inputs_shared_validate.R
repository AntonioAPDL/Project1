# unified/inputs_shared_validate.R

unified_shared_input_paths <- function(run_root) {
  shared_root <- file.path(run_root, "inputs", "shared")
  list(
    root = shared_root,
    parameters = file.path(shared_root, "parameters", "parameters.txt"),
    retros = file.path(shared_root, "retros", "retros.csv"),
    nws = file.path(shared_root, "forecasts", "nws_forecast.csv"),
    glofas = file.path(shared_root, "forecasts", "glofas_forecast.csv"),
    covariates_dir = file.path(shared_root, "covariates")
  )
}

unified_schema_error <- function(stage_name, label, path, reason, details = character(0), hint = NULL) {
  lines <- c(
    sprintf("Stage %s: %s schema validation failed.", stage_name, label),
    sprintf("- path: %s", path),
    sprintf("- reason: %s", reason)
  )
  if (length(details) > 0L) {
    lines <- c(lines, sprintf("- %s", details))
  }
  if (!is.null(hint) && nzchar(as.character(hint))) {
    lines <- c(lines, sprintf("- hint: %s", as.character(hint)))
  }
  paste(lines, collapse = "\n")
}

unified_manifest_get_artifact_scale <- function(manifest, target_path) {
  if (is.null(manifest$artifacts) || length(manifest$artifacts) == 0L) return(NULL)
  target <- normalizePath(target_path, mustWork = FALSE)
  for (a in manifest$artifacts) {
    p <- a$path
    if (is.null(p)) next
    if (!is.character(p) || !nzchar(p)) next
    ap <- normalizePath(p, mustWork = FALSE)
    if (identical(ap, target)) {
      sc <- a$storage_scale
      if (is.character(sc) && nzchar(sc)) return(sc)
      return(NULL)
    }
  }
  NULL
}

unified_read_csv_checked <- function(path, label, stage_name) {
  out <- tryCatch(
    utils::read.csv(path, stringsAsFactors = FALSE, check.names = FALSE),
    error = function(e) e
  )
  if (inherits(out, "error")) {
    stop(
      unified_schema_error(
        stage_name = stage_name,
        label = label,
        path = path,
        reason = sprintf("unreadable CSV: %s", out$message)
      ),
      call. = FALSE
    )
  }
  if (!is.data.frame(out)) {
    stop(
      unified_schema_error(
        stage_name = stage_name,
        label = label,
        path = path,
        reason = "CSV parse did not produce a data.frame"
      ),
      call. = FALSE
    )
  }
  out
}

unified_csv_quick_validate <- function(path, label) {
  out <- tryCatch(
    utils::read.csv(path, nrows = 2L, stringsAsFactors = FALSE, check.names = FALSE),
    error = function(e) e
  )
  if (inherits(out, "error")) {
    return(sprintf("%s unreadable CSV (%s): %s", label, path, out$message))
  }
  if (!is.data.frame(out)) {
    return(sprintf("%s CSV parse did not produce a data.frame: %s", label, path))
  }
  if (ncol(out) < 2L) {
    return(sprintf("%s CSV must have at least 2 columns: %s", label, path))
  }
  if (nrow(out) < 1L) {
    return(sprintf("%s CSV must have at least 1 data row: %s", label, path))
  }
  NULL
}

unified_validate_glofas_members_csv <- function(path, stage_name, min_rows = 20L, min_member_cols = 20L) {
  df <- unified_read_csv_checked(path, "glofas members forecast", stage_name)

  if (ncol(df) < 2L) {
    stop(
      unified_schema_error(
        stage_name = stage_name,
        label = "glofas members forecast",
        path = path,
        reason = sprintf("expected at least 2 columns; found %d", ncol(df)),
        hint = "Expected first date column plus member columns."
      ),
      call. = FALSE
    )
  }
  if (nrow(df) < min_rows) {
    stop(
      unified_schema_error(
        stage_name = stage_name,
        label = "glofas members forecast",
        path = path,
        reason = sprintf("expected at least %d rows; found %d", min_rows, nrow(df)),
        hint = "Do not use weighted/summary forecast files with short horizon."
      ),
      call. = FALSE
    )
  }

  member_cols <- names(df)[-1L]
  if (length(member_cols) < min_member_cols) {
    stop(
      unified_schema_error(
        stage_name = stage_name,
        label = "glofas members forecast",
        path = path,
        reason = sprintf("expected at least %d member columns; found %d", min_member_cols, length(member_cols)),
        hint = "Use member-level GloFAS forecast CSV."
      ),
      call. = FALSE
    )
  }

  member_df <- df[, member_cols, drop = FALSE]
  numeric_member_cols <- names(member_df)[vapply(member_df, is.numeric, logical(1))]
  if (length(numeric_member_cols) < min_member_cols) {
    stop(
      unified_schema_error(
        stage_name = stage_name,
        label = "glofas members forecast",
        path = path,
        reason = sprintf(
          "expected at least %d numeric member columns; found %d",
          min_member_cols, length(numeric_member_cols)
        )
      ),
      call. = FALSE
    )
  }

  num_vals <- as.matrix(member_df[, numeric_member_cols, drop = FALSE])
  bad <- !is.finite(num_vals)
  if (any(bad, na.rm = TRUE)) {
    bad_counts <- colSums(bad, na.rm = TRUE)
    bad_cols <- names(bad_counts)[bad_counts > 0L]
    row_ids <- which(rowSums(bad, na.rm = TRUE) > 0L)
    sample_rows <- head(row_ids, 5L)
    stop(
      unified_schema_error(
        stage_name = stage_name,
        label = "glofas members forecast",
        path = path,
        reason = "contains non-finite member values",
        details = c(
          sprintf("non-finite columns: %s", paste(sprintf("%s(%d)", bad_cols, bad_counts[bad_cols]), collapse = ", ")),
          sprintf("example row indices: %s", paste(sample_rows, collapse = ", "))
        )
      ),
      call. = FALSE
    )
  }

  invisible(TRUE)
}

unified_validate_weighted_time_series_csv <- function(path, stage_name, provenance = NULL) {
  df <- unified_read_csv_checked(path, "weighted_time_series", stage_name)
  numeric_cols <- names(df)[vapply(df, is.numeric, logical(1))]
  if (length(numeric_cols) == 0L) {
    stop(
      unified_schema_error(
        stage_name = stage_name,
        label = "weighted_time_series",
        path = path,
        reason = "contains no numeric columns"
      ),
      call. = FALSE
    )
  }

  num_vals <- as.matrix(df[, numeric_cols, drop = FALSE])
  bad <- !is.finite(num_vals)
  if (any(bad, na.rm = TRUE)) {
    bad_counts <- colSums(bad, na.rm = TRUE)
    bad_cols <- names(bad_counts)[bad_counts > 0L]
    row_ids <- which(rowSums(bad, na.rm = TRUE) > 0L)
    sample_rows <- head(row_ids, 5L)
    sample_cols <- unique(c(names(df)[1L], head(bad_cols, 3L)))
    sample_view <- utils::capture.output(print(df[sample_rows, sample_cols, drop = FALSE], row.names = FALSE))
    details <- c(
      sprintf("non-finite columns: %s", paste(sprintf("%s(%d)", bad_cols, bad_counts[bad_cols]), collapse = ", ")),
      sprintf("example row indices: %s", paste(sample_rows, collapse = ", ")),
      if (!is.null(provenance) && nzchar(as.character(provenance))) sprintf("provenance: %s", as.character(provenance)) else NULL,
      "example rows:",
      sample_view
    )
    stop(
      unified_schema_error(
        stage_name = stage_name,
        label = "weighted_time_series",
        path = path,
        reason = "contains non-finite numeric values",
        details = details,
        hint = "Repair weighted_time_series.csv upstream or provide member-level forecast file."
      ),
      call. = FALSE
    )
  }

  invisible(TRUE)
}

unified_validate_forecast_numeric_csv <- function(path, label, stage_name, min_rows = 1L, min_numeric_cols = 1L) {
  df <- unified_read_csv_checked(path, label, stage_name)
  if (nrow(df) < min_rows) {
    stop(
      unified_schema_error(
        stage_name = stage_name,
        label = label,
        path = path,
        reason = sprintf("expected at least %d rows; found %d", min_rows, nrow(df))
      ),
      call. = FALSE
    )
  }
  numeric_cols <- names(df)[vapply(df, is.numeric, logical(1))]
  if (length(numeric_cols) < min_numeric_cols) {
    stop(
      unified_schema_error(
        stage_name = stage_name,
        label = label,
        path = path,
        reason = sprintf(
          "expected at least %d numeric columns; found %d",
          min_numeric_cols, length(numeric_cols)
        )
      ),
      call. = FALSE
    )
  }
  num_vals <- as.matrix(df[, numeric_cols, drop = FALSE])
  bad <- !is.finite(num_vals)
  if (any(bad, na.rm = TRUE)) {
    bad_counts <- colSums(bad, na.rm = TRUE)
    bad_cols <- names(bad_counts)[bad_counts > 0L]
    row_ids <- which(rowSums(bad, na.rm = TRUE) > 0L)
    sample_rows <- head(row_ids, 5L)
    stop(
      unified_schema_error(
        stage_name = stage_name,
        label = label,
        path = path,
        reason = "contains non-finite numeric values",
        details = c(
          sprintf("non-finite columns: %s", paste(sprintf("%s(%d)", bad_cols, bad_counts[bad_cols]), collapse = ", ")),
          sprintf("example row indices: %s", paste(sample_rows, collapse = ", "))
        )
      ),
      call. = FALSE
    )
  }
  invisible(TRUE)
}

unified_validate_required_shared_inputs <- function(
  run_root,
  stage_name,
  manifest = NULL,
  enabled_models = list(run_exdqlm_multivar = TRUE, run_exdqlm_univar = FALSE, run_ndlm_main = FALSE),
  required_covariates = character(0)
) {
  paths <- unified_shared_input_paths(run_root)

  families <- character(0)
  if (isTRUE(enabled_models$run_exdqlm_multivar)) families <- c(families, "exdqlm_multivar")
  if (isTRUE(enabled_models$run_exdqlm_univar)) families <- c(families, "exdqlm_univar")
  if (isTRUE(enabled_models$run_ndlm_main)) families <- c(families, "ndlm_main")
  if (length(families) == 0L) families <- "shared_bundle_only"

  errs <- character(0)
  add_err <- function(msg) errs <<- c(errs, msg)

  must_files <- c(parameters = paths$parameters, retros = paths$retros, nws = paths$nws, glofas = paths$glofas)
  for (nm in names(must_files)) {
    p <- must_files[[nm]]
    if (!file.exists(p)) {
      add_err(sprintf("missing required shared %s file: %s", nm, p))
      next
    }
    if (isTRUE(file.info(p)$size <= 0)) {
      add_err(sprintf("empty shared %s file: %s", nm, p))
      next
    }
    if (file.access(p, mode = 4L) != 0L) {
      add_err(sprintf("unreadable shared %s file: %s", nm, p))
      next
    }
  }

  for (nm in c("retros", "nws", "glofas")) {
    p <- must_files[[nm]]
    if (file.exists(p) && isTRUE(file.info(p)$size > 0) && file.access(p, mode = 4L) == 0L) {
      csv_err <- unified_csv_quick_validate(p, sprintf("shared %s", nm))
      if (!is.null(csv_err)) add_err(csv_err)
    }
  }

  if ((isTRUE(enabled_models$run_exdqlm_univar) || isTRUE(enabled_models$run_ndlm_main)) &&
      file.exists(paths$retros) &&
      isTRUE(file.info(paths$retros)$size > 0) &&
      file.access(paths$retros, mode = 4L) == 0L) {
    retros_df <- tryCatch(
      unified_read_csv_checked(paths$retros, "retros", stage_name),
      error = function(e) e
    )
    if (inherits(retros_df, "error")) {
      add_err(conditionMessage(retros_df))
    } else {
      required_cols <- c("USGS", "GloFAS", "NWS3.0")
      missing_cols <- setdiff(required_cols, names(retros_df))
      if (length(missing_cols) > 0L) {
        add_err(
          unified_schema_error(
            stage_name = stage_name,
            label = "retros",
            path = paths$retros,
            reason = sprintf("missing legacy-required columns: %s", paste(missing_cols, collapse = ", ")),
            hint = "Use retros input schema compatible with legacy univariate/NDLM scripts (USGS, GloFAS, NWS3.0)."
          )
        )
      }
    }
  }

  if (file.exists(paths$glofas) && isTRUE(file.info(paths$glofas)$size > 0) && file.access(paths$glofas, mode = 4L) == 0L) {
    glofas_err <- tryCatch(
      {
        unified_validate_glofas_members_csv(paths$glofas, stage_name = stage_name)
        NULL
      },
      error = function(e) conditionMessage(e)
    )
    if (!is.null(glofas_err)) add_err(glofas_err)

    glofas_base <- tolower(basename(paths$glofas))
    if (grepl("weighted_time_series\\.csv$", glofas_base)) {
      weighted_err <- tryCatch(
        {
          unified_validate_weighted_time_series_csv(
            paths$glofas,
            stage_name = stage_name,
            provenance = "shared forecast source selected as weighted_time_series.csv"
          )
          NULL
        },
        error = function(e) conditionMessage(e)
      )
      if (!is.null(weighted_err)) add_err(weighted_err)
    }
  }

  if (file.exists(paths$nws) && isTRUE(file.info(paths$nws)$size > 0) && file.access(paths$nws, mode = 4L) == 0L) {
    nws_err <- tryCatch(
      {
        unified_validate_forecast_numeric_csv(
          paths$nws,
          label = "nws forecast",
          stage_name = stage_name,
          min_rows = 10L,
          min_numeric_cols = 2L
        )
        NULL
      },
      error = function(e) conditionMessage(e)
    )
    if (!is.null(nws_err)) add_err(nws_err)
  }

  if (length(required_covariates) > 0L) {
    for (cov_path in required_covariates) {
      cov_path <- as.character(cov_path)
      if (!nzchar(cov_path)) next
      if (!file.exists(cov_path)) {
        add_err(sprintf("missing required shared covariate: %s", cov_path))
        next
      }
      if (isTRUE(file.info(cov_path)$size <= 0)) {
        add_err(sprintf("empty required shared covariate: %s", cov_path))
      }
      if (file.access(cov_path, mode = 4L) != 0L) {
        add_err(sprintf("unreadable required shared covariate: %s", cov_path))
      }
    }
  }

  if (length(errs) > 0L) {
    stop(
      paste(
        c(
          sprintf("Stage %s: shared input validation failed for families [%s].", stage_name, paste(families, collapse = ", ")),
          paste0("- ", errs)
        ),
        collapse = "\n"
      ),
      call. = FALSE
    )
  }

  scales <- list(
    retros = unified_manifest_get_artifact_scale(manifest, paths$retros),
    nws = unified_manifest_get_artifact_scale(manifest, paths$nws),
    glofas = unified_manifest_get_artifact_scale(manifest, paths$glofas)
  )

  list(paths = paths, scales = scales, families = families)
}
