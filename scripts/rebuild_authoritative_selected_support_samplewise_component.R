#!/usr/bin/env Rscript

args <- commandArgs(trailingOnly = TRUE)

parse_args <- function(values) {
  out <- list()
  i <- 1L
  while (i <= length(values)) {
    key <- values[[i]]
    if (!startsWith(key, "--")) stop(sprintf("Unexpected argument: %s", key), call. = FALSE)
    if (i == length(values)) stop(sprintf("Missing value for argument: %s", key), call. = FALSE)
    out[[substring(key, 3L)]] <- values[[i + 1L]]
    i <- i + 2L
  }
  out
}

opt <- parse_args(args)
required <- c("source-support-dir", "fit-run-root", "output-dir")
missing <- required[!vapply(required, function(k) !is.null(opt[[k]]) && nzchar(opt[[k]]), logical(1))]
if (length(missing) > 0L) {
  stop(sprintf("Missing required args: %s", paste(missing, collapse = ", ")), call. = FALSE)
}

source_support_dir <- normalizePath(opt[["source-support-dir"]], mustWork = TRUE)
fit_run_root <- normalizePath(opt[["fit-run-root"]], mustWork = TRUE)
output_dir <- normalizePath(opt[["output-dir"]], mustWork = FALSE)
dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

required_support_files <- c(
  "authoritative_usgs_quantile_dynamics_summary.csv",
  "authoritative_usgs_quantile_dynamics_summary.rds",
  "authoritative_selected_support_lineage.csv"
)
for (name in required_support_files) {
  src <- file.path(source_support_dir, name)
  if (!file.exists(src)) stop(sprintf("Missing source support file: %s", src), call. = FALSE)
  file.copy(src, file.path(output_dir, name), overwrite = TRUE)
}

source_component_path <- file.path(source_support_dir, "authoritative_component_summary.csv")
if (!file.exists(source_component_path)) {
  stop(sprintf("Missing source component support CSV: %s", source_component_path), call. = FALSE)
}
source_component <- utils::read.csv(source_component_path, stringsAsFactors = FALSE, check.names = FALSE)
dates_df <- unique(source_component[, c("time_index", "date"), drop = FALSE])
dates_df <- dates_df[order(dates_df$time_index), , drop = FALSE]
dates <- suppressWarnings(as.Date(dates_df$date))
if (length(dates) == 0L || all(is.na(dates))) {
  stop("Unable to recover support dates from source component CSV.", call. = FALSE)
}

safe_row_quantiles <- function(mat, probs = c(0.025, 0.5, 0.975)) {
  if (!is.matrix(mat) || nrow(mat) == 0L || ncol(mat) == 0L) {
    return(matrix(NA_real_, nrow = length(probs), ncol = 0L))
  }
  out <- apply(
    mat,
    1L,
    function(v) {
      vv <- as.numeric(v)
      vv <- vv[is.finite(vv)]
      if (length(vv) == 0L) return(rep(NA_real_, length(probs)))
      stats::quantile(vv, probs = probs, na.rm = TRUE, type = 8, names = FALSE)
    }
  )
  matrix(out, nrow = length(probs), byrow = FALSE)
}

theta_array_layout <- function(arr, n_time_hint) {
  d <- dim(arr)
  if (length(d) != 3L) return(NULL)
  if (d[2L] == n_time_hint) return(list(time_dim = 2L, sample_dim = 3L))
  if (d[3L] == n_time_hint) return(list(time_dim = 3L, sample_dim = 2L))
  if (d[2L] >= d[3L]) list(time_dim = 2L, sample_dim = 3L) else list(time_dim = 3L, sample_dim = 2L)
}

component_matrix <- function(arr, component, n_time, layout) {
  if (!is.array(arr) || length(dim(arr)) != 3L || is.null(layout)) return(NULL)
  component <- as.integer(component)
  if (component < 1L || component > dim(arr)[1L]) return(NULL)
  if (layout$time_dim == 2L) {
    mat <- arr[component, seq_len(n_time), , drop = FALSE]
  } else {
    mat <- arr[component, , seq_len(n_time), drop = FALSE]
  }
  matrix(mat, nrow = n_time)
}

component_summary_row <- function(mat, dates, label, probability, component, component_contract, source_object) {
  qs <- safe_row_quantiles(mat)
  data.frame(
    date = dates,
    time_index = seq_len(length(dates)),
    quantile = label,
    probability = probability,
    component = component,
    component_contract = component_contract,
    lower_025 = as.numeric(qs[1L, ]),
    median_500 = as.numeric(qs[2L, ]),
    upper_975 = as.numeric(qs[3L, ]),
    source_object = source_object,
    stringsAsFactors = FALSE
  )
}

quantile_specs <- data.frame(
  suffix = c("5", "50", "95"),
  dir_label = c("05", "50", "95"),
  label = c("q05", "q50", "q95"),
  probability = c(0.05, 0.50, 0.95),
  stringsAsFactors = FALSE
)

rebuild_one_quantile <- function(spec) {
  rdata_path <- file.path(
    fit_run_root,
    "fit", "exdqlm_multivar", "keep",
    sprintf("q=%s", spec$dir_label),
    "outputs",
    sprintf("DISC_variables_%s_exAL_synth_DISC.RData", spec$suffix)
  )
  if (!file.exists(rdata_path)) stop(sprintf("Missing retained RData: %s", rdata_path), call. = FALSE)
  message(sprintf("[load] %s", rdata_path))
  e <- new.env(parent = emptyenv())
  load(rdata_path, envir = e)
  obj_name <- sprintf("samp.theta_%s_exAL_synth_DISC", spec$suffix)
  if (!exists(obj_name, envir = e, inherits = FALSE)) {
    stop(sprintf("Missing `%s` in %s", obj_name, rdata_path), call. = FALSE)
  }
  obj <- get(obj_name, envir = e, inherits = FALSE)
  arr <- if (is.list(obj) && is.array(obj$samp_theta)) obj$samp_theta else if (is.array(obj)) obj else NULL
  if (is.null(arr)) stop(sprintf("`%s` is not a recognized posterior theta sample object.", obj_name), call. = FALSE)
  n_time <- length(dates)
  layout <- theta_array_layout(arr, n_time)
  if (is.null(layout)) stop(sprintf("Unable to infer theta sample layout for %s", obj_name), call. = FALSE)
  n_component <- min(7L, dim(arr)[1L])
  source_object <- obj_name
  rows <- vector("list", n_component + 3L)
  for (component in seq_len(n_component)) {
    rows[[component]] <- component_summary_row(
      mat = component_matrix(arr, component, n_time, layout),
      dates = dates,
      label = spec$label,
      probability = spec$probability,
      component = component,
      component_contract = "raw_state_component",
      source_object = source_object
    )
  }
  trend_mat <- component_matrix(arr, 1L, n_time, layout)
  component6_mat <- component_matrix(arr, 6L, n_time, layout)
  rows[[n_component + 1L]] <- component_summary_row(
    mat = trend_mat + component6_mat,
    dates = dates,
    label = spec$label,
    probability = spec$probability,
    component = 6L,
    component_contract = "component_6_plus_trend_component_1_samplewise",
    source_object = source_object
  )
  rows[[n_component + 2L]] <- component_summary_row(
    mat = component6_mat - trend_mat,
    dates = dates,
    label = spec$label,
    probability = spec$probability,
    component = 6L,
    component_contract = "component_6_minus_trend_component_1_samplewise",
    source_object = source_object
  )
  legacy <- component_summary_row(
    mat = component6_mat,
    dates = dates,
    label = spec$label,
    probability = spec$probability,
    component = 6L,
    component_contract = "component_6_shifted_by_posterior_mean_trend_component_1",
    source_object = source_object
  )
  trend_shift <- rowMeans(trend_mat, na.rm = TRUE)
  legacy$lower_025 <- legacy$lower_025 + trend_shift
  legacy$median_500 <- legacy$median_500 + trend_shift
  legacy$upper_975 <- legacy$upper_975 + trend_shift
  rows[[n_component + 3L]] <- legacy
  rm(e, obj, arr, trend_mat, component6_mat)
  invisible(gc())
  do.call(rbind, rows)
}

component_rows <- lapply(seq_len(nrow(quantile_specs)), function(i) rebuild_one_quantile(quantile_specs[i, , drop = FALSE]))
component_summary <- do.call(rbind, component_rows)
component_csv <- file.path(output_dir, "authoritative_component_summary.csv")
component_rds <- file.path(output_dir, "authoritative_component_summary.rds")
utils::write.csv(component_summary, component_csv, row.names = FALSE)
saveRDS(component_summary, component_rds)

manifest_src <- file.path(source_support_dir, "authoritative_selected_support_manifest.json")
manifest_out <- file.path(output_dir, "authoritative_selected_support_manifest.json")
if (file.exists(manifest_src) && requireNamespace("jsonlite", quietly = TRUE)) {
  manifest <- jsonlite::read_json(manifest_src, simplifyVector = FALSE)
  manifest$component_rows <- nrow(component_summary)
  manifest$component_contracts <- sort(unique(component_summary$component_contract))
  manifest$component_rebuild <- list(
    rebuilt_at_utc = format(Sys.time(), "%Y-%m-%dT%H:%M:%SZ", tz = "UTC"),
    source_support_dir = source_support_dir,
    fit_run_root = fit_run_root,
    contracts_added = c(
      "component_6_plus_trend_component_1_samplewise",
      "component_6_minus_trend_component_1_samplewise"
    )
  )
  jsonlite::write_json(manifest, manifest_out, auto_unbox = TRUE, pretty = TRUE)
} else if (file.exists(manifest_src)) {
  file.copy(manifest_src, manifest_out, overwrite = TRUE)
} else {
  writeLines("{\"artifact_family\":\"authoritative_selected_model_support\"}", manifest_out)
}

status <- data.frame(
  artifact = c(
    "authoritative_usgs_quantile_dynamics_summary",
    "authoritative_component_summary",
    "authoritative_selected_support_manifest"
  ),
  status = "pass",
  rows = c(
    nrow(utils::read.csv(file.path(output_dir, "authoritative_usgs_quantile_dynamics_summary.csv"))),
    nrow(component_summary),
    1L
  ),
  path = c(
    file.path(output_dir, "authoritative_usgs_quantile_dynamics_summary.csv"),
    component_csv,
    manifest_out
  ),
  detail = c(
    "copied from source selected-support root",
    "rebuilt from retained RData with samplewise component-6-plus/minus-trend contracts",
    "copied and updated with component rebuild metadata"
  ),
  stringsAsFactors = FALSE
)
utils::write.csv(status, file.path(output_dir, "authoritative_selected_support_status.csv"), row.names = FALSE)

message(sprintf("[ok] wrote rebuilt selected support to %s", output_dir))
