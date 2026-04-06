#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(jsonlite)
})

`%||%` <- function(x, y) if (is.null(x) || identical(x, "") || (length(x) == 1L && is.na(x))) y else x

parse_args <- function(argv) {
  out <- list()
  i <- 1L
  while (i <= length(argv)) {
    a <- argv[[i]]
    if (startsWith(a, "--")) {
      key <- sub("^--", "", a)
      if (i == length(argv) || startsWith(argv[[i + 1L]], "--")) {
        out[[key]] <- TRUE
        i <- i + 1L
      } else {
        out[[key]] <- argv[[i + 1L]]
        i <- i + 2L
      }
    } else {
      i <- i + 1L
    }
  }
  out
}

as_abs_path <- function(p) {
  if (startsWith(p, "/")) return(p)
  normalizePath(file.path(getwd(), p), mustWork = FALSE)
}

extract_limits <- function(x) {
  vals <- suppressWarnings(as.numeric(unlist(x)))
  vals <- vals[is.finite(vals)]
  if (length(vals) != 2L) return(NULL)
  sort(vals)
}

args <- parse_args(commandArgs(trailingOnly = TRUE))
run_dir <- as_abs_path(args$`manifest-run-dir` %||% "repro/gefs_nwm_forecast_runs/gefs_nwm_forecast_manifest_20260307T023425Z")
plots_root <- file.path(run_dir, "plots")
out_json <- as_abs_path(args$`out-json` %||% file.path(plots_root, "shared_y_limits.json"))
summary_paths <- Sys.glob(file.path(plots_root, "cutoff_date=*", "plot_summary*.json"))
if (!length(summary_paths)) {
  stop(sprintf("No plot summaries found under %s", plots_root), call. = FALSE)
}

rows <- list()
for (path in summary_paths) {
  obj <- tryCatch(jsonlite::fromJSON(path, simplifyVector = FALSE), error = function(e) NULL)
  if (is.null(obj)) next
  if (!isTRUE(obj$unit_harmonized)) next
  soil_limits <- extract_limits(obj$soil_y_limits_used)
  precip_limits <- extract_limits(obj$precip_y_limits_used)
  if (is.null(soil_limits) && is.null(precip_limits)) next
  rows[[length(rows) + 1L]] <- list(
    cutoff_date = as.character(obj$cutoff_date %||% ""),
    summary_path = normalizePath(path, mustWork = FALSE),
    soil_limits = soil_limits,
    precip_limits = precip_limits
  )
}

if (!length(rows)) {
  stop("No harmonized same-unit plot summaries with y-limit metadata were found.", call. = FALSE)
}

soil_mins <- unlist(lapply(rows, function(x) if (!is.null(x$soil_limits)) x$soil_limits[[1]] else NULL))
soil_maxs <- unlist(lapply(rows, function(x) if (!is.null(x$soil_limits)) x$soil_limits[[2]] else NULL))
precip_mins <- unlist(lapply(rows, function(x) if (!is.null(x$precip_limits)) x$precip_limits[[1]] else NULL))
precip_maxs <- unlist(lapply(rows, function(x) if (!is.null(x$precip_limits)) x$precip_limits[[2]] else NULL))

payload <- list(
  created_utc = format(Sys.time(), tz = "UTC", usetz = TRUE),
  manifest_run_dir = normalizePath(run_dir, mustWork = FALSE),
  summaries_scanned = unname(vapply(rows, function(x) x$summary_path, character(1))),
  cutoff_dates = unname(vapply(rows, function(x) x$cutoff_date, character(1))),
  soil_same_units = if (length(soil_mins)) {
    list(min = min(soil_mins), max = max(soil_maxs), limits = c(min(soil_mins), max(soil_maxs)))
  } else {
    NULL
  },
  precip_same_units = if (length(precip_mins)) {
    list(min = min(precip_mins), max = max(precip_maxs), limits = c(min(precip_mins), max(precip_maxs)))
  } else {
    NULL
  }
)

dir.create(dirname(out_json), recursive = TRUE, showWarnings = FALSE)
writeLines(jsonlite::toJSON(payload, pretty = TRUE, auto_unbox = TRUE), con = out_json)
cat(jsonlite::toJSON(payload, pretty = TRUE, auto_unbox = TRUE))
cat(sprintf("\n[OK] wrote %s\n", out_json))
