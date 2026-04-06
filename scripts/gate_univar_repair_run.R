#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(yaml)
})

args <- commandArgs(trailingOnly = TRUE)

parse_args <- function(args) {
  out <- list(
    run_root = "repro/runs",
    run_id = NULL,
    expected_model_id = NULL
  )
  i <- 1L
  while (i <= length(args)) {
    key <- args[[i]]
    val <- if (i < length(args)) args[[i + 1L]] else NULL
    if (identical(key, "--run-root")) out$run_root <- val
    if (identical(key, "--run-id")) out$run_id <- val
    if (identical(key, "--expected-model-id")) out$expected_model_id <- val
    i <- i + 2L
  }
  if (is.null(out$run_id) || !nzchar(out$run_id)) {
    stop("--run-id is required", call. = FALSE)
  }
  if (is.null(out$expected_model_id) || !nzchar(out$expected_model_id)) {
    stop("--expected-model-id is required", call. = FALSE)
  }
  out
}

read_manifest_stage_status <- function(path) {
  manifest <- yaml::read_yaml(path)
  stages <- manifest$stages %||% list()
  vapply(
    c("data_prep_shared", "fit", "post", "report"),
    function(nm) {
      stage <- stages[[nm]]
      if (is.list(stage) && !is.null(stage$status)) as.character(stage$status) else NA_character_
    },
    character(1)
  )
}

`%||%` <- function(x, y) if (is.null(x)) y else x

stage_status_ok <- function(stage_status) {
  allowed_optional <- c("pass", "skip")
  isTRUE(stage_status[["post"]] == "pass") &&
    isTRUE(stage_status[["data_prep_shared"]] %in% allowed_optional) &&
    isTRUE(stage_status[["fit"]] %in% allowed_optional) &&
    isTRUE(stage_status[["report"]] %in% allowed_optional)
}

compute_curve_crossing <- function(tbl) {
  req <- c("lead_day", "curve_type", "quantile", "value_log1p")
  if (!all(req %in% names(tbl))) {
    stop("forecast window quantile table missing required columns", call. = FALSE)
  }
  tbl$curve_type <- as.character(tbl$curve_type)
  tbl$quantile <- suppressWarnings(as.numeric(tbl$quantile))
  tbl$value_log1p <- suppressWarnings(as.numeric(tbl$value_log1p))
  tbl$lead_day <- suppressWarnings(as.integer(tbl$lead_day))
  tbl <- tbl[is.finite(tbl$quantile) & is.finite(tbl$value_log1p) & is.finite(tbl$lead_day), , drop = FALSE]

  split_key <- interaction(tbl$curve_type, tbl$lead_day, drop = TRUE, lex.order = TRUE)
  blocks <- split(tbl, split_key)
  out <- lapply(blocks, function(d) {
    d <- d[order(d$quantile), , drop = FALSE]
    gaps <- diff(d$value_log1p)
    has_cross <- any(gaps < -1e-10)
    data.frame(
      curve_type = d$curve_type[[1L]],
      lead_day = d$lead_day[[1L]],
      has_crossing = as.integer(has_cross),
      max_negative_gap = if (length(gaps) > 0L) min(c(0, gaps), na.rm = TRUE) else 0,
      stringsAsFactors = FALSE
    )
  })
  per_time <- do.call(rbind, out)
  summary <- aggregate(
    cbind(has_crossing, max_negative_gap) ~ curve_type,
    data = per_time,
    FUN = function(x) c(sum = sum(x), mean = mean(x), min = min(x))
  )
  data.frame(
    curve_type = summary$curve_type,
    n_horizon = as.integer(table(per_time$curve_type)[summary$curve_type]),
    n_times_with_crossing = as.integer(summary$has_crossing[, "sum"]),
    crossing_share = as.numeric(summary$has_crossing[, "mean"]),
    max_negative_gap = as.numeric(summary$max_negative_gap[, "min"]),
    stringsAsFactors = FALSE
  )
}

main <- function() {
  opts <- parse_args(args)
  run_dir <- file.path(opts$run_root, opts$run_id)
  manifest_path <- file.path(run_dir, "run_manifest.yaml")
  tables_dir <- file.path(run_dir, "post", "outputs", opts$run_id, "tables")
  quantile_path <- file.path(tables_dir, "univar_forecast_window_quantiles.csv")
  crps_summary_path <- file.path(tables_dir, "crps_forecast_summary.csv")
  crps_health_path <- file.path(tables_dir, "crps_input_health.csv")
  crossing_path <- file.path(tables_dir, "univar_forecast_quantile_crossing_summary.csv")
  plot_path <- file.path(run_dir, "post", "outputs", opts$run_id, "univar_forecast_window_quantiles_raw_cms.png")

  stage_ok <- FALSE
  model_ok <- FALSE
  health_ok <- FALSE
  files_ok <- FALSE
  synth_anchor_ok <- FALSE
  synth_empirical_ok <- FALSE
  raw_cross_share <- NA_real_

  if (!file.exists(manifest_path)) {
    cat(sprintf("RUN_ID=%s\n", opts$run_id))
    cat("G1_stages=fail missing_manifest\n")
    cat("OVERALL=fail\n")
    quit(status = 1L)
  }

  stage_status <- read_manifest_stage_status(manifest_path)
  stage_ok <- stage_status_ok(stage_status)
  cat(sprintf("RUN_ID=%s\n", opts$run_id))
  cat(sprintf(
    "G1_stages=%s data_prep_shared=%s fit=%s post=%s report=%s\n",
    if (stage_ok) "pass" else "fail",
    stage_status[["data_prep_shared"]],
    stage_status[["fit"]],
    stage_status[["post"]],
    stage_status[["report"]]
  ))

  files_ok <- all(file.exists(c(crps_summary_path, crps_health_path, quantile_path, crossing_path, plot_path)))
  cat(sprintf("G2_files=%s\n", if (files_ok) "pass" else "fail"))

  if (file.exists(crps_summary_path)) {
    crps_summary <- read.csv(crps_summary_path, stringsAsFactors = FALSE)
    model_ok <- opts$expected_model_id %in% crps_summary$model_id
    cat(sprintf("G3_model_id=%s expected=%s\n", if (model_ok) "pass" else "fail", opts$expected_model_id))
    if (model_ok) {
      row <- crps_summary[crps_summary$model_id == opts$expected_model_id, , drop = FALSE][1L, , drop = FALSE]
      cat(sprintf(
        "INFO_crps mean_crps=%0.10f median_crps=%0.10f n_valid=%s\n",
        as.numeric(row$mean_crps[[1L]]),
        as.numeric(row$median_crps[[1L]]),
        as.character(row$n_valid[[1L]])
      ))
    }
  } else {
    cat(sprintf("G3_model_id=fail expected=%s missing_crps_summary\n", opts$expected_model_id))
  }

  if (file.exists(crps_health_path)) {
    health <- read.csv(crps_health_path, stringsAsFactors = FALSE)
    fail_rows <- sum(suppressWarnings(as.numeric(health$fail_rows)), na.rm = TRUE)
    fail_rows_per_time <- if ("fail_rows_per_time" %in% names(health)) {
      sum(suppressWarnings(as.numeric(health$fail_rows_per_time)), na.rm = TRUE)
    } else {
      NA_real_
    }
    health_ok <- isTRUE(all.equal(fail_rows, 0)) && (is.na(fail_rows_per_time) || isTRUE(all.equal(fail_rows_per_time, 0)))
    cat(sprintf(
      "G4_input_health=%s fail_rows=%s fail_rows_per_time=%s\n",
      if (health_ok) "pass" else "fail",
      format(fail_rows, trim = TRUE),
      format(fail_rows_per_time, trim = TRUE)
    ))
  } else {
    cat("G4_input_health=fail missing_input_health\n")
  }

  if (file.exists(quantile_path)) {
    quant_tbl <- read.csv(quantile_path, stringsAsFactors = FALSE)
    curve_cross <- compute_curve_crossing(quant_tbl)
    raw_row <- curve_cross[curve_cross$curve_type == "raw_model", , drop = FALSE]
    raw_cross_share <- if (nrow(raw_row) > 0L) raw_row$crossing_share[[1L]] else NA_real_
    synth_anchor_row <- curve_cross[curve_cross$curve_type == "synth_anchor", , drop = FALSE]
    synth_emp_row <- curve_cross[curve_cross$curve_type == "synth_empirical", , drop = FALSE]
    synth_anchor_ok <- nrow(synth_anchor_row) == 1L && synth_anchor_row$n_times_with_crossing[[1L]] == 0L
    synth_empirical_ok <- nrow(synth_emp_row) == 1L && synth_emp_row$n_times_with_crossing[[1L]] == 0L
    cat(sprintf(
      "G5_synth_monotonicity=%s synth_anchor_crossings=%s synth_empirical_crossings=%s raw_crossing_share=%s\n",
      if (synth_anchor_ok && synth_empirical_ok) "pass" else "fail",
      if (nrow(synth_anchor_row) == 1L) as.character(synth_anchor_row$n_times_with_crossing[[1L]]) else "NA",
      if (nrow(synth_emp_row) == 1L) as.character(synth_emp_row$n_times_with_crossing[[1L]]) else "NA",
      format(raw_cross_share, digits = 6, trim = TRUE)
    ))
  } else {
    cat("G5_synth_monotonicity=fail missing_quantile_table\n")
  }

  overall <- stage_ok && files_ok && model_ok && health_ok && synth_anchor_ok && synth_empirical_ok
  cat(sprintf("OVERALL=%s\n", if (overall) "pass" else "fail"))
  quit(status = if (overall) 0L else 1L)
}

main()
