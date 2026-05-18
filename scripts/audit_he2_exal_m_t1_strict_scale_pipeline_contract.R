#!/usr/bin/env Rscript

parse_args <- function(argv) {
  out <- list()
  i <- 1L
  while (i <= length(argv)) {
    key <- argv[[i]]
    if (!startsWith(key, '--')) {
      i <- i + 1L
      next
    }
    key <- sub('^--', '', key)
    key <- gsub('-', '_', key, fixed = TRUE)
    if (i == length(argv) || startsWith(argv[[i + 1L]], '--')) {
      out[[key]] <- TRUE
      i <- i + 1L
    } else {
      out[[key]] <- argv[[i + 1L]]
      i <- i + 2L
    }
  }
  out
}

`%||%` <- function(x, y) {
  if (is.null(x) || identical(x, '') || (length(x) == 1L && is.na(x))) y else x
}

read_csv <- function(path, ...) utils::read.csv(path, stringsAsFactors = FALSE, check.names = FALSE, ...)

max_abs_diff <- function(a, b) {
  a <- as.numeric(a)
  b <- as.numeric(b)
  keep <- is.finite(a) & is.finite(b)
  if (!any(keep)) return(NA_real_)
  max(abs(a[keep] - b[keep]))
}

compare_named_numeric_frames <- function(left, right, key_col, value_cols, transform_right = identity) {
  left[[key_col]] <- as.character(left[[key_col]])
  right[[key_col]] <- as.character(right[[key_col]])
  idx <- match(left[[key_col]], right[[key_col]])
  if (any(is.na(idx))) stop(sprintf('Failed to align on key %s', key_col), call. = FALSE)
  right <- right[idx, , drop = FALSE]
  out <- data.frame(column = value_cols, rows = nrow(left), max_abs_diff = NA_real_, stringsAsFactors = FALSE)
  for (i in seq_along(value_cols)) {
    nm <- value_cols[[i]]
    out$max_abs_diff[[i]] <- max_abs_diff(left[[nm]], transform_right(right[[nm]]))
  }
  out
}

matrix_quantiles <- function(mat, probs) {
  qs <- apply(as.matrix(mat), 2L, stats::quantile, probs = probs, na.rm = TRUE, type = 8, names = FALSE)
  matrix(qs, nrow = length(probs), byrow = FALSE)
}

write_csv <- function(df, path) {
  dir.create(dirname(path), recursive = TRUE, showWarnings = FALSE)
  utils::write.csv(df, path, row.names = FALSE)
}

main <- function() {
  args <- parse_args(commandArgs(trailingOnly = TRUE))
  fit_run_root <- normalizePath(args$fit_run_root %||% '', mustWork = TRUE)
  post_run_root <- normalizePath(args$post_run_root %||% '', mustWork = TRUE)
  forecast_review_dir <- normalizePath(args$forecast_review_dir %||% '', mustWork = TRUE)
  location_review_dir <- normalizePath(args$location_review_dir %||% '', mustWork = TRUE)
  report_dir <- normalizePath(args$report_dir %||% '', mustWork = FALSE)
  if (!nzchar(report_dir)) stop('Provide --report-dir', call. = FALSE)
  dir.create(report_dir, recursive = TRUE, showWarnings = FALSE)

  fit_shared_dir <- file.path(fit_run_root, 'inputs', 'shared')
  fit_inputs_dir <- file.path(fit_run_root, 'fit', 'inputs')
  post_inputs_dir <- file.path(post_run_root, 'post', 'inputs')
  post_cache_dir <- file.path(post_run_root, 'post', 'cache')
  post_outputs_dir <- file.path(post_run_root, 'post', 'outputs', basename(post_run_root))

  shared_usgs <- read_csv(file.path(fit_shared_dir, 'usgs', 'usgs_daily.csv'))
  shared_retros <- read_csv(file.path(fit_shared_dir, 'retros', 'retros.csv'))
  shared_glofas <- read_csv(file.path(fit_shared_dir, 'forecasts', 'glofas_forecast.csv'))
  shared_nws <- read_csv(file.path(fit_shared_dir, 'forecasts', 'nws_forecast.csv'))

  fit_retros <- read_csv(file.path(fit_inputs_dir, 'retros_fit_adapter.csv'))
  fit_glofas <- read_csv(file.path(fit_inputs_dir, 'glofas_fit_adapter.csv'))
  fit_nws <- read_csv(file.path(fit_inputs_dir, 'nws_fit_adapter.csv'))
  post_retros <- read_csv(file.path(post_inputs_dir, 'retros_post_adapter.csv'))
  post_glofas <- read_csv(file.path(post_inputs_dir, 'glofas_post_adapter.csv'))
  post_nws <- read_csv(file.path(post_inputs_dir, 'nws_post_adapter.csv'))
  data_cbind <- read_csv(file.path(post_outputs_dir, 'data_cbind_tY_X.csv'))

  quant_path <- Sys.glob(file.path(post_outputs_dir, '*_cutoff_window_quantiles.csv'))
  sample_path <- Sys.glob(file.path(post_outputs_dir, '*_cutoff_window_sample_subset.csv'))
  if (length(quant_path) != 1L || length(sample_path) != 1L) stop('Expected one quantile csv and one sample subset csv', call. = FALSE)
  quant_df <- read_csv(quant_path[[1L]])
  sample_df <- read_csv(sample_path[[1L]])

  fc_review <- read_csv(file.path(forecast_review_dir, 'forecast_window_quantiles_with_exact_95_log1p.csv'))
  loc_review <- read_csv(file.path(location_review_dir, 'usgs_location_dynamics_log1p.csv'))

  hist_cache <- as.matrix(readRDS(file.path(post_cache_dir, 'exdqlm_multivar_synth_keep__mode-keep__synth_multivar_hist_log1p.rds')))
  fc_cache <- as.matrix(readRDS(file.path(post_cache_dir, 'exdqlm_multivar_synth_keep__mode-keep__synth_multivar_forecast_log1p.rds')))
  hist_loc <- readRDS(file.path(post_cache_dir, 'exdqlm_multivar_synth_keep__mode-keep__multivar_hist_usgs_location_summary_log1p.rds'))
  fc_loc <- readRDS(file.path(post_cache_dir, 'exdqlm_multivar_synth_keep__mode-keep__multivar_forecast_usgs_location_summary_log1p.rds'))
  exp_guard_lines <- readLines(file.path(post_cache_dir, 'exdqlm_multivar_synth_keep__mode-keep__synth_multivar_forecast_exp_guard.txt'), warn = FALSE)

  quant_probs <- c(0.05, 0.20, 0.35, 0.50, 0.65, 0.80, 0.95)
  quant_cols <- sprintf('q%02d', as.integer(round(100 * quant_probs)))

  checks <- list()

  # 1. shared retros USGS equals log1p(raw USGS)
  shared_usgs$date <- as.character(shared_usgs$date)
  shared_retros$Date <- as.character(shared_retros$Date)
  idx_usgs <- match(shared_retros$Date, shared_usgs$date)
  usgs_log1p <- log1p(as.numeric(shared_usgs$discharge_cms[idx_usgs]))
  checks[[length(checks) + 1L]] <- data.frame(
    check_id = 'shared_retros_usgs_matches_log1p_raw_usgs',
    rows_checked = length(idx_usgs),
    max_abs_diff = max_abs_diff(shared_retros$USGS, usgs_log1p),
    status = ifelse(max_abs_diff(shared_retros$USGS, usgs_log1p) <= 1e-12, 'pass', 'fail'),
    notes = 'shared retros USGS versus log1p(shared raw USGS discharge_cms)',
    stringsAsFactors = FALSE
  )

  # 2. fit adapters equal post adapters
  for (nm in c('USGS', 'GloFAS', 'NWS3.0')) {
    diff_tbl <- max_abs_diff(fit_retros[[nm]], post_retros[[nm]])
    checks[[length(checks) + 1L]] <- data.frame(
      check_id = paste0('fit_retros_matches_post_retros_', nm),
      rows_checked = nrow(fit_retros),
      max_abs_diff = diff_tbl,
      status = ifelse(diff_tbl <= 1e-12, 'pass', 'fail'),
      notes = sprintf('fit retros adapter column %s versus post retros adapter', nm),
      stringsAsFactors = FALSE
    )
  }

  for (provider in c('glofas', 'nws')) {
    fit_df <- if (provider == 'glofas') fit_glofas else fit_nws
    post_df <- if (provider == 'glofas') post_glofas else post_nws
    shared_df <- if (provider == 'glofas') shared_glofas else shared_nws
    key <- 'target_date'
    value_cols <- setdiff(intersect(names(fit_df), names(post_df)), key)
    cmp_fit_post <- compare_named_numeric_frames(fit_df, post_df, key_col = key, value_cols = value_cols)
    checks[[length(checks) + 1L]] <- data.frame(
      check_id = paste0(provider, '_fit_adapter_matches_post_adapter'),
      rows_checked = nrow(fit_df),
      max_abs_diff = max(cmp_fit_post$max_abs_diff, na.rm = TRUE),
      status = ifelse(max(cmp_fit_post$max_abs_diff, na.rm = TRUE) <= 1e-12, 'pass', 'fail'),
      notes = sprintf('%s fit adapter equals %s post adapter over all member columns', provider, provider),
      stringsAsFactors = FALSE
    )
    cmp_shared_fit <- compare_named_numeric_frames(fit_df, shared_df, key_col = key, value_cols = value_cols, transform_right = function(x) log1p(as.numeric(x)))
    checks[[length(checks) + 1L]] <- data.frame(
      check_id = paste0(provider, '_fit_adapter_matches_log1p_shared_forecast'),
      rows_checked = nrow(fit_df),
      max_abs_diff = max(cmp_shared_fit$max_abs_diff, na.rm = TRUE),
      status = ifelse(max(cmp_shared_fit$max_abs_diff, na.rm = TRUE) <= 1e-12, 'pass', 'fail'),
      notes = sprintf('%s fit adapter equals log1p(shared forecast members)', provider),
      stringsAsFactors = FALSE
    )
  }

  # 3. data_cbind response columns equal post retros
  for (nm in c('USGS', 'GloFAS', 'NWS3.0')) {
    d <- max_abs_diff(data_cbind[[nm]], post_retros[[nm]])
    checks[[length(checks) + 1L]] <- data.frame(
      check_id = paste0('data_cbind_matches_post_retros_', nm),
      rows_checked = nrow(data_cbind),
      max_abs_diff = d,
      status = ifelse(d <= 1e-12, 'pass', 'fail'),
      notes = sprintf('post output matrix column %s equals post retros adapter', nm),
      stringsAsFactors = FALSE
    )
  }

  # 4. export quantiles equal cache quantiles
  hist_rows <- quant_df[quant_df$segment == 'history', , drop = FALSE]
  fc_rows <- quant_df[quant_df$segment == 'forecast', , drop = FALSE]
  hist_q <- matrix_quantiles(hist_cache, quant_probs)
  fc_q <- matrix_quantiles(fc_cache, quant_probs)
  for (i in seq_along(quant_cols)) {
    qc <- quant_cols[[i]]
    d_hist <- max_abs_diff(hist_rows[[qc]], hist_q[i, ])
    d_fc <- max_abs_diff(fc_rows[[qc]], fc_q[i, ])
    checks[[length(checks) + 1L]] <- data.frame(
      check_id = paste0('history_quantile_csv_matches_cache_', qc),
      rows_checked = nrow(hist_rows),
      max_abs_diff = d_hist,
      status = ifelse(d_hist <= 1e-12, 'pass', 'fail'),
      notes = sprintf('history export %s equals type-8 quantile from history cache', qc),
      stringsAsFactors = FALSE
    )
    checks[[length(checks) + 1L]] <- data.frame(
      check_id = paste0('forecast_quantile_csv_matches_cache_', qc),
      rows_checked = nrow(fc_rows),
      max_abs_diff = d_fc,
      status = ifelse(d_fc <= 1e-12, 'pass', 'fail'),
      notes = sprintf('forecast export %s equals type-8 quantile from forecast cache', qc),
      stringsAsFactors = FALSE
    )
  }

  # 5. sample subset integrity
  check_subset <- function(seg_name, mat, seg_rows) {
    sub <- sample_df[sample_df$segment == seg_name, , drop = FALSE]
    date_map <- match(sub$date, as.character(seg_rows$date))
    expected <- mat[cbind(as.integer(sub$sample_index), date_map)]
    max_abs_diff(sub$value, expected)
  }
  d_hist_subset <- check_subset('history', hist_cache, hist_rows)
  d_fc_subset <- check_subset('forecast', fc_cache, fc_rows)
  checks[[length(checks) + 1L]] <- data.frame(check_id = 'history_sample_subset_matches_cache', rows_checked = nrow(sample_df[sample_df$segment == 'history', ]), max_abs_diff = d_hist_subset, status = ifelse(d_hist_subset <= 1e-12, 'pass', 'fail'), notes = 'history sample subset values equal selected cache rows', stringsAsFactors = FALSE)
  checks[[length(checks) + 1L]] <- data.frame(check_id = 'forecast_sample_subset_matches_cache', rows_checked = nrow(sample_df[sample_df$segment == 'forecast', ]), max_abs_diff = d_fc_subset, status = ifelse(d_fc_subset <= 1e-12, 'pass', 'fail'), notes = 'forecast sample subset values equal selected cache rows', stringsAsFactors = FALSE)

  # 6. review forecast export integrity
  fc_review_rows <- fc_review[fc_review$segment == 'forecast', , drop = FALSE]
  q025 <- as.numeric(matrix_quantiles(fc_cache, c(0.025))[1, ])
  q975 <- as.numeric(matrix_quantiles(fc_cache, c(0.975))[1, ])
  model_mean <- colMeans(fc_cache, na.rm = TRUE)
  for (i in seq_along(quant_cols)) {
    qc <- quant_cols[[i]]
    d <- max_abs_diff(fc_review_rows[[qc]], fc_rows[[qc]])
    checks[[length(checks) + 1L]] <- data.frame(check_id = paste0('forecast_review_quantiles_match_post_export_', qc), rows_checked = nrow(fc_review_rows), max_abs_diff = d, status = ifelse(d <= 1e-12, 'pass', 'fail'), notes = sprintf('authoritative forecast review %s matches canonical post export', qc), stringsAsFactors = FALSE)
  }
  d_low <- max_abs_diff(fc_review_rows$interval_low, q025)
  d_high <- max_abs_diff(fc_review_rows$interval_high, q975)
  d_mean <- max_abs_diff(fc_review_rows$model_mean, model_mean)
  checks[[length(checks) + 1L]] <- data.frame(check_id = 'forecast_review_interval_low_matches_cache_q025', rows_checked = nrow(fc_review_rows), max_abs_diff = d_low, status = ifelse(d_low <= 1e-12, 'pass', 'fail'), notes = 'authoritative forecast review interval_low equals cache q025', stringsAsFactors = FALSE)
  checks[[length(checks) + 1L]] <- data.frame(check_id = 'forecast_review_interval_high_matches_cache_q975', rows_checked = nrow(fc_review_rows), max_abs_diff = d_high, status = ifelse(d_high <= 1e-12, 'pass', 'fail'), notes = 'authoritative forecast review interval_high equals cache q975', stringsAsFactors = FALSE)
  checks[[length(checks) + 1L]] <- data.frame(check_id = 'forecast_review_model_mean_matches_cache_mean', rows_checked = nrow(fc_review_rows), max_abs_diff = d_mean, status = ifelse(d_mean <= 1e-12, 'pass', 'fail'), notes = 'authoritative forecast review model_mean equals cache colMeans', stringsAsFactors = FALSE)

  # 7. location review integrity
  hist_loc_rows <- loc_review[loc_review$segment == 'history', , drop = FALSE]
  fc_loc_rows <- loc_review[loc_review$segment == 'forecast', , drop = FALSE]
  q_labels <- hist_loc$q_labels
  for (i in seq_along(q_labels)) {
    ql <- q_labels[[i]]
    col_nm <- paste0('loc_', ql, '_mean')
    d_hist <- max_abs_diff(hist_loc_rows[[col_nm]], hist_loc$mean_mat[i, ])
    d_fc <- max_abs_diff(fc_loc_rows[[col_nm]], fc_loc$mean_mat[i, ])
    checks[[length(checks) + 1L]] <- data.frame(check_id = paste0('history_location_review_matches_cache_', ql), rows_checked = nrow(hist_loc_rows), max_abs_diff = d_hist, status = ifelse(d_hist <= 1e-12, 'pass', 'fail'), notes = sprintf('history location review %s mean equals location cache', ql), stringsAsFactors = FALSE)
    checks[[length(checks) + 1L]] <- data.frame(check_id = paste0('forecast_location_review_matches_cache_', ql), rows_checked = nrow(fc_loc_rows), max_abs_diff = d_fc, status = ifelse(d_fc <= 1e-12, 'pass', 'fail'), notes = sprintf('forecast location review %s mean equals location cache', ql), stringsAsFactors = FALSE)
  }
  q50_idx <- match('q50', q_labels)
  checks[[length(checks) + 1L]] <- data.frame(check_id = 'history_location_review_q50_band_matches_cache_q025', rows_checked = nrow(hist_loc_rows), max_abs_diff = max_abs_diff(hist_loc_rows$loc_q50_q025, hist_loc$q025_mat[q50_idx, ]), status = ifelse(max_abs_diff(hist_loc_rows$loc_q50_q025, hist_loc$q025_mat[q50_idx, ]) <= 1e-12, 'pass', 'fail'), notes = 'history location review q50 q025 equals location cache q025', stringsAsFactors = FALSE)
  checks[[length(checks) + 1L]] <- data.frame(check_id = 'history_location_review_q50_band_matches_cache_q500', rows_checked = nrow(hist_loc_rows), max_abs_diff = max_abs_diff(hist_loc_rows$loc_q50_q500, hist_loc$q500_mat[q50_idx, ]), status = ifelse(max_abs_diff(hist_loc_rows$loc_q50_q500, hist_loc$q500_mat[q50_idx, ]) <= 1e-12, 'pass', 'fail'), notes = 'history location review q50 q500 equals location cache q500', stringsAsFactors = FALSE)
  checks[[length(checks) + 1L]] <- data.frame(check_id = 'history_location_review_q50_band_matches_cache_q975', rows_checked = nrow(hist_loc_rows), max_abs_diff = max_abs_diff(hist_loc_rows$loc_q50_q975, hist_loc$q975_mat[q50_idx, ]), status = ifelse(max_abs_diff(hist_loc_rows$loc_q50_q975, hist_loc$q975_mat[q50_idx, ]) <= 1e-12, 'pass', 'fail'), notes = 'history location review q50 q975 equals location cache q975', stringsAsFactors = FALSE)

  # 8. exp guard
  exp_guard_text <- paste(exp_guard_lines, collapse = ' | ')
  identity_guard <- grepl('transform=identity', exp_guard_text, fixed = TRUE) && grepl('from_scale=log1p_cms', exp_guard_text, fixed = TRUE) && grepl('to_scale=log1p_cms', exp_guard_text, fixed = TRUE)
  checks[[length(checks) + 1L]] <- data.frame(check_id = 'forecast_exp_guard_records_identity_log1p_contract', rows_checked = length(exp_guard_lines), max_abs_diff = 0, status = ifelse(identity_guard, 'pass', 'fail'), notes = exp_guard_text, stringsAsFactors = FALSE)

  checks_df <- do.call(rbind, checks)
  write_csv(checks_df, file.path(report_dir, 'strict_scale_pipeline_checks.csv'))

  # inventory
  inv <- data.frame(
    artifact = c(
      'fit_retros_adapter', 'fit_glofas_adapter', 'fit_nws_adapter',
      'post_retros_adapter', 'post_glofas_adapter', 'post_nws_adapter',
      'post_data_cbind', 'post_hist_cache', 'post_fc_cache',
      'post_hist_location_cache', 'post_fc_location_cache',
      'post_quantile_csv', 'post_sample_subset_csv',
      'authoritative_forecast_review_csv', 'authoritative_location_review_csv',
      'canonical_posterior_png', 'canonical_posterior_with_ensembles_png'
    ),
    path = c(
      file.path(fit_inputs_dir, 'retros_fit_adapter.csv'),
      file.path(fit_inputs_dir, 'glofas_fit_adapter.csv'),
      file.path(fit_inputs_dir, 'nws_fit_adapter.csv'),
      file.path(post_inputs_dir, 'retros_post_adapter.csv'),
      file.path(post_inputs_dir, 'glofas_post_adapter.csv'),
      file.path(post_inputs_dir, 'nws_post_adapter.csv'),
      file.path(post_outputs_dir, 'data_cbind_tY_X.csv'),
      file.path(post_cache_dir, 'exdqlm_multivar_synth_keep__mode-keep__synth_multivar_hist_log1p.rds'),
      file.path(post_cache_dir, 'exdqlm_multivar_synth_keep__mode-keep__synth_multivar_forecast_log1p.rds'),
      file.path(post_cache_dir, 'exdqlm_multivar_synth_keep__mode-keep__multivar_hist_usgs_location_summary_log1p.rds'),
      file.path(post_cache_dir, 'exdqlm_multivar_synth_keep__mode-keep__multivar_forecast_usgs_location_summary_log1p.rds'),
      quant_path[[1L]],
      sample_path[[1L]],
      file.path(forecast_review_dir, 'forecast_window_quantiles_with_exact_95_log1p.csv'),
      file.path(location_review_dir, 'usgs_location_dynamics_log1p.csv'),
      file.path(post_outputs_dir, 'exdqlm_multivar_synth_keep_cutoff_window_posterior_samples.png'),
      file.path(post_outputs_dir, 'exdqlm_multivar_synth_keep_cutoff_window_posterior_samples_with_raw_ensembles.png')
    ),
    stringsAsFactors = FALSE
  )
  inv$exists <- file.exists(inv$path)
  write_csv(inv, file.path(report_dir, 'artifact_inventory.csv'))

  summary <- list(
    fit_run_root = fit_run_root,
    post_run_root = post_run_root,
    forecast_review_dir = forecast_review_dir,
    location_review_dir = location_review_dir,
    checks_total = nrow(checks_df),
    checks_failed = sum(checks_df$status != 'pass'),
    exp_guard_identity = identity_guard,
    data_cbind_matches_post_adapters = all(checks_df$check_id[grepl('^data_cbind_matches_post_retros_', checks_df$check_id)] %in% checks_df$check_id[checks_df$status == 'pass']),
    quantile_exports_match_caches = all(checks_df$status[grepl('quantile_csv_matches_cache', checks_df$check_id)] == 'pass'),
    sample_subset_matches_caches = all(checks_df$status[grepl('sample_subset_matches_cache', checks_df$check_id)] == 'pass'),
    review_exports_match_canonical_objects = all(checks_df$status[grepl('review_.*matches', checks_df$check_id)] == 'pass')
  )
  if (requireNamespace('jsonlite', quietly = TRUE)) {
    jsonlite::write_json(summary, file.path(report_dir, 'summary.json'), auto_unbox = TRUE, pretty = TRUE)
  } else {
    dput(summary, file = file.path(report_dir, 'summary.json'))
  }

  lines <- c(
    '# HE2 exAL-M-T1 Strict Scale Pipeline Audit 2026-05-18',
    '',
    sprintf('- fit run root: `%s`', fit_run_root),
    sprintf('- post run root: `%s`', post_run_root),
    sprintf('- authoritative forecast review dir: `%s`', forecast_review_dir),
    sprintf('- authoritative location review dir: `%s`', location_review_dir),
    '',
    '## Summary',
    '',
    sprintf('- checks total: `%d`', summary$checks_total),
    sprintf('- checks failed: `%d`', summary$checks_failed),
    sprintf('- exp guard identity on log1p contract: `%s`', if (identity_guard) 'true' else 'false'),
    sprintf('- data_cbind first three response columns match post adapters: `%s`', if (isTRUE(summary$data_cbind_matches_post_adapters)) 'true' else 'false'),
    sprintf('- canonical quantile exports match cache quantiles: `%s`', if (isTRUE(summary$quantile_exports_match_caches)) 'true' else 'false'),
    sprintf('- canonical sample-subset export matches cache samples: `%s`', if (isTRUE(summary$sample_subset_matches_caches)) 'true' else 'false'),
    sprintf('- authoritative review exports match canonical objects: `%s`', if (isTRUE(summary$review_exports_match_canonical_objects)) 'true' else 'false'),
    '',
    '## Main outputs',
    '',
    sprintf('- checks csv: `%s`', file.path(report_dir, 'strict_scale_pipeline_checks.csv')),
    sprintf('- artifact inventory: `%s`', file.path(report_dir, 'artifact_inventory.csv')),
    sprintf('- summary json: `%s`', file.path(report_dir, 'summary.json'))
  )
  writeLines(lines, con = file.path(report_dir, 'HE2_EXAL_M_T1_STRICT_SCALE_PIPELINE_AUDIT_20221225_20260518.md'))
  cat(sprintf('WROTE %s\n', file.path(report_dir, 'strict_scale_pipeline_checks.csv')))
}

main()
