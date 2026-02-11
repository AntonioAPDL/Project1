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
