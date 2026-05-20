#!/usr/bin/env Rscript

parse_args <- function(argv) {
  out <- list()
  i <- 1L
  while (i <= length(argv)) {
    key <- argv[[i]]
    if (!startsWith(key, "--")) {
      i <- i + 1L
      next
    }
    key <- sub("^--", "", key)
    key <- gsub("-", "_", key, fixed = TRUE)
    if (i == length(argv) || startsWith(argv[[i + 1L]], "--")) {
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
  if (is.null(x) || identical(x, "") || (length(x) == 1L && is.na(x))) y else x
}

require_pkg <- function(pkg) {
  if (!requireNamespace(pkg, quietly = TRUE)) {
    stop(sprintf("Package '%s' is required.", pkg), call. = FALSE)
  }
}

write_csv_det <- function(df, path) {
  dir.create(dirname(path), recursive = TRUE, showWarnings = FALSE)
  utils::write.csv(df, path, row.names = FALSE)
}

quantile_labels <- c("q05", "q20", "q35", "q50", "q65", "q80", "q95")
quantile_suffixes <- c("5", "20", "35", "50", "65", "80", "95")
palette_quantiles <- c(
  q05 = "#9B1D20",
  q20 = "#C45D38",
  q35 = "#E38D2C",
  q50 = "#6A3D9A",
  q65 = "#2E86AB",
  q80 = "#1F9E89",
  q95 = "#006D2C"
)

component_colors <- c(
  "Observed USGS" = "#111111",
  "USGS exps" = "#7B3294",
  "USGS reconstructed" = "#1F78B4",
  "Trend contribution" = "#4D4D4D",
  "Season contribution" = "#E08214",
  "Transfer zeta" = "#B2182B",
  "Season phase state" = "#7570B3",
  "PPT beta state" = "#1B9E77"
)

resolve_covariate_path_by_name <- function(cfg, name) {
  covs <- cfg$inputs$fit$covariates
  if (!is.list(covs) || length(covs) < 1L) {
    stop("Resolved config has no fit covariates block.", call. = FALSE)
  }
  idx <- vapply(
    covs,
    function(x) identical(as.character(x$name %||% ""), name),
    logical(1)
  )
  if (!any(idx)) {
    stop(sprintf("Could not resolve covariate path for %s", name), call. = FALSE)
  }
  as.character(covs[[which(idx)[1L]]]$path)
}

prepare_context <- function(context_run_root, repo_root, cfg) {
  cutoff_date <- as.Date(cfg$dates$cutoff_date)
  if (is.na(cutoff_date)) stop("Invalid cutoff_date", call. = FALSE)
  forecast_start_date <- cutoff_date + 1L

  scale_contract <- cfg$scale_contract %||% list()
  legacy_fit_scale <- as.character(scale_contract$legacy_fit_input_scale %||% "log1p_cms")
  analysis_fit_scale <- as.character(scale_contract$analysis_scale_fit_internal %||% legacy_fit_scale)
  legacy_post_scale <- as.character(scale_contract$legacy_post_input_scale %||% legacy_fit_scale)
  analysis_post_scale <- as.character(scale_contract$analysis_scale_post_internal %||% analysis_fit_scale)

  enabled_harmonics <- cfg$models$exdqlm_multivar$structure$enabled_harmonic_indices
  if (is.null(enabled_harmonics) || length(enabled_harmonics) < 1L) enabled_harmonics <- c(1L)
  include_trend <- cfg$models$exdqlm_multivar$structure$include_trend
  if (is.null(include_trend)) include_trend <- TRUE

  Sys.setenv(
    ENV_PROJECT_ROOT = repo_root,
    UNIFIED_RUN_ROOT = context_run_root,
    UNIFIED_CUTOFF_DATE = as.character(cutoff_date),
    UNIFIED_FORECAST_START_DATE = as.character(forecast_start_date),
    ENV_RETROS_PATH = file.path(context_run_root, "fit", "inputs", "retros_fit_adapter.csv"),
    ENV_GLOFAS_FORECAST_PATH = file.path(context_run_root, "fit", "inputs", "glofas_fit_adapter.csv"),
    ENV_NWS_FORECAST_PATH = file.path(context_run_root, "fit", "inputs", "nws_fit_adapter.csv"),
    UNIFIED_USGS_DAILY_CSV = as.character(cfg$inputs$fit$usgs_cache_path),
    ENV_PPT_PATH = resolve_covariate_path_by_name(cfg, "PPT"),
    ENV_SOIL_PATH = resolve_covariate_path_by_name(cfg, "SOIL"),
    ENV_PCA_PATH = resolve_covariate_path_by_name(cfg, "PCA"),
    UNIFIED_COVARIATE_FEATURES_CSV = file.path(context_run_root, "inputs", "shared", "covariates", "covariate_features.csv"),
    DISC_W_TRANSFER_FEATURE_COLUMNS = paste(c(as.character(cfg$inputs$transfer_function_covariates$base_covariates %||% character(0)), as.character(cfg$inputs$transfer_function_covariates$engineered_terms %||% character(0))), collapse = ","),
    UNIFIED_TRANSFER_FEATURE_COLUMNS = paste(c(as.character(cfg$inputs$transfer_function_covariates$base_covariates %||% character(0)), as.character(cfg$inputs$transfer_function_covariates$engineered_terms %||% character(0))), collapse = ","),
    UNIFIED_LEGACY_FIT_INPUT_SCALE = legacy_fit_scale,
    UNIFIED_ANALYSIS_SCALE_FIT_INTERNAL = analysis_fit_scale,
    UNIFIED_LEGACY_POST_INPUT_SCALE = legacy_post_scale,
    UNIFIED_ANALYSIS_SCALE_POST_INTERNAL = analysis_post_scale,
    DISC_W_INCLUDE_TREND = if (isTRUE(include_trend)) "TRUE" else "FALSE",
    DISC_W_ENABLED_HARMONIC_INDICES = paste(as.integer(enabled_harmonics), collapse = ","),
    UNIFIED_MULTIVAR_FORECAST_TRANSFER_MODE = as.character(cfg$models$exdqlm_multivar$forecast_transfer_mode %||% "keep")
  )

  suppressPackageStartupMessages({
    library(Matrix)
    library(readr)
    library(lubridate)
    library(truncnorm)
    library(dlm)
    library(exdqlm)
  })

  source(file.path(repo_root, "R", "unified", "utils_scale.R"))
  source(file.path(repo_root, "R", "unified", "families", "shared_input_helpers.R"))
  source(file.path(repo_root, "R", "environmetrics", "00_paths.R"))
  DATA_CBIND_RDS <<- tempfile(fileext = ".rds")
  DATA_CBIND_CSV <<- tempfile(fileext = ".csv")
  source(file.path(repo_root, "R", "environmetrics", "00_constants.R"))
  source(file.path(repo_root, "R", "environmetrics", "02_helpers_core.R"))
  source(file.path(repo_root, "R", "environmetrics", "10_data_inputs.R"))
  source(file.path(repo_root, "R", "environmetrics", "20_model_setup.R"))

  ff_base <- as.numeric(model_simp$FF[seq_len(p), 1L, 1L])
  trend_dim <- if (isTRUE(include_trend)) 1L else 0L
  season_start <- trend_dim + 1L
  season_end <- p
  season_idx <- if (season_start <= season_end) seq.int(season_start, season_end) else integer(0)
  trend_idx <- if (trend_dim > 0L) seq_len(trend_dim) else integer(0)
  season_loaded_local <- season_idx[ff_base[season_idx] != 0]
  season_phase_local <- season_idx[ff_base[season_idx] == 0]
  if (length(season_loaded_local) < 1L) season_loaded_local <- integer(0)
  if (length(season_phase_local) < 1L) season_phase_local <- integer(0)

  list(
    cutoff_date = cutoff_date,
    hist_dates = as.Date(timestamps),
    observed_usgs = as.numeric(Y[1L, ]),
    TT = as.integer(TT),
    p = as.integer(p),
    J = as.integer(J),
    ppx = as.integer(ppx),
    ff_base = ff_base,
    trend_idx = trend_idx,
    season_idx = season_idx,
    season_loaded_local = season_loaded_local,
    season_phase_local = season_phase_local,
    core_hist_dim = as.integer(p * (J + 1L))
  )
}

build_state_map <- function(ctx, state_dim) {
  rows <- list()
  channel_names <- c("USGS", "GloFAS", "NWS3.0")[seq_len(ctx$J + 1L)]
  row_i <- 0L
  for (jj in seq_len(ctx$J + 1L)) {
    offset <- (jj - 1L) * ctx$p
    block_idx <- offset + seq_len(ctx$p)
    for (kk in seq_along(block_idx)) {
      idx <- block_idx[[kk]]
      role <- "other"
      ff_weight_usgs <- 0
      if (jj == 1L && kk %in% ctx$trend_idx) {
        role <- "usgs_trend"
        ff_weight_usgs <- ctx$ff_base[[kk]]
      } else if (jj == 1L && kk %in% ctx$season_loaded_local) {
        role <- "usgs_season_loaded"
        ff_weight_usgs <- ctx$ff_base[[kk]]
      } else if (jj == 1L && kk %in% ctx$season_phase_local) {
        role <- "usgs_season_phase"
        ff_weight_usgs <- ctx$ff_base[[kk]]
      } else if (jj == 2L) {
        role <- if (kk %in% ctx$trend_idx) "glofas_trend" else if (kk %in% ctx$season_loaded_local) "glofas_season_loaded" else if (kk %in% ctx$season_phase_local) "glofas_season_phase" else "glofas_other"
      } else if (jj == 3L) {
        role <- if (kk %in% ctx$trend_idx) "nws_trend" else if (kk %in% ctx$season_loaded_local) "nws_season_loaded" else if (kk %in% ctx$season_phase_local) "nws_season_phase" else "nws_other"
      }
      row_i <- row_i + 1L
      rows[[row_i]] <- data.frame(
        state_index = idx,
        block = channel_names[[jj]],
        within_block_index = kk,
        role = role,
        ff_weight_usgs = ff_weight_usgs,
        stringsAsFactors = FALSE
      )
    }
  }
  ppx_actual <- max(0L, as.integer(state_dim - ctx$core_hist_dim))
  if (ppx_actual > 0L) {
    rows[[length(rows) + 1L]] <- data.frame(
      state_index = ctx$core_hist_dim + 1L,
      block = "transfer",
      within_block_index = 1L,
      role = "transfer_zeta",
      ff_weight_usgs = 1,
      stringsAsFactors = FALSE
    )
  }
  if (ppx_actual > 1L) {
    for (kk in seq_len(ppx_actual - 1L)) {
      rows[[length(rows) + 1L]] <- data.frame(
        state_index = ctx$core_hist_dim + 1L + kk,
        block = "transfer",
        within_block_index = 1L + kk,
        role = if (kk == 1L) "transfer_beta_ppt" else sprintf("transfer_beta_%d", kk),
        ff_weight_usgs = 0,
        stringsAsFactors = FALSE
      )
    }
  }
  do.call(rbind, rows)
}

extract_quantile_state <- function(state_root, quant_label, quant_suffix, TT_hist) {
  rdata_path <- file.path(
    state_root,
    "fit", "exdqlm_multivar", "keep",
    sprintf("q=%s", sub("^q", "", quant_label)),
    "outputs",
    sprintf("DISC_variables_%s_exAL_synth_DISC.RData", quant_suffix)
  )
  env <- new.env(parent = baseenv())
  on.exit({
    rm(list = ls(env, all.names = TRUE), envir = env)
    gc(verbose = FALSE)
  }, add = TRUE)
  load(rdata_path, envir = env)
  theta_name <- sprintf("new.theta.out_%s_exAL_synth_DISC", quant_suffix)
  if (!exists(theta_name, envir = env, inherits = FALSE)) {
    stop(sprintf("Missing %s in %s", theta_name, rdata_path), call. = FALSE)
  }
  theta_obj <- get(theta_name, envir = env, inherits = FALSE)
  exps <- as.matrix(theta_obj$exps)
  sm <- as.matrix(theta_obj$sm)
  list(
    rdata_path = rdata_path,
    exps_usgs = as.numeric(exps[1L, seq_len(TT_hist)]),
    sm = sm[, seq_len(TT_hist), drop = FALSE]
  )
}

compute_quantile_components <- function(payload, ctx, q_label) {
  sm <- payload$sm
  usgs_idx <- seq_len(ctx$p)
  trend_global_idx <- usgs_idx[ctx$trend_idx]
  season_loaded_idx <- usgs_idx[ctx$season_loaded_local]
  season_phase_idx <- usgs_idx[ctx$season_phase_local]
  zeta_idx <- if (ctx$ppx > 0L) ctx$core_hist_dim + 1L else NA_integer_
  beta_idx <- if (ctx$ppx > 1L) ctx$core_hist_dim + 2L else NA_integer_

  trend_contrib <- if (length(trend_global_idx) > 0L) {
    colSums(sm[trend_global_idx, , drop = FALSE] * ctx$ff_base[ctx$trend_idx])
  } else rep(0, ctx$TT)
  season_contrib <- if (length(season_loaded_idx) > 0L) {
    colSums(sm[season_loaded_idx, , drop = FALSE] * ctx$ff_base[ctx$season_loaded_local])
  } else rep(0, ctx$TT)
  season_phase_state <- if (length(season_phase_idx) > 0L) {
    colSums(sm[season_phase_idx, , drop = FALSE])
  } else rep(0, ctx$TT)
  transfer_zeta <- if (is.finite(zeta_idx) && zeta_idx <= nrow(sm)) sm[zeta_idx, ] else rep(0, ctx$TT)
  beta_ppt <- if (is.finite(beta_idx) && beta_idx <= nrow(sm)) sm[beta_idx, ] else rep(NA_real_, ctx$TT)
  reconstructed <- trend_contrib + season_contrib + transfer_zeta
  recon_err <- payload$exps_usgs - reconstructed

  data.frame(
    date = ctx$hist_dates,
    quantile = q_label,
    observed_usgs = ctx$observed_usgs,
    exps_usgs = payload$exps_usgs,
    reconstructed_usgs = reconstructed,
    trend_contrib = trend_contrib,
    season_contrib = season_contrib,
    season_phase_state = season_phase_state,
    transfer_zeta = transfer_zeta,
    beta_ppt = beta_ppt,
    reconstruction_error = recon_err,
    stringsAsFactors = FALSE
  )
}

plot_cross_quantile_window <- function(all_df, window_n, report_dir) {
  qs <- unique(all_df$quantile)
  exps_df <- all_df[, c('date','quantile','exps_usgs')]
  names(exps_df)[3] <- 'value'
  exps_df$panel <- 'USGS exps'
  obs_df <- unique(all_df[, c('date','observed_usgs')])
  obs_df$panel <- 'USGS exps'
  obs_df$quantile <- 'Observed USGS'
  names(obs_df)[2] <- 'value'

  make_panel <- function(col, panel_name) {
    df <- all_df[, c('date','quantile', col)]
    names(df)[3] <- 'value'
    df$panel <- panel_name
    df
  }

  long_df <- rbind(
    exps_df,
    obs_df[, c('date','quantile','value','panel')],
    make_panel('trend_contrib', 'Trend contribution'),
    make_panel('season_contrib', 'Season contribution'),
    make_panel('transfer_zeta', 'Transfer zeta'),
    make_panel('beta_ppt', 'PPT beta state'),
    make_panel('season_phase_state', 'Season phase state')
  )
  long_df$panel <- factor(long_df$panel, levels = c(
    'USGS exps', 'Trend contribution', 'Season contribution', 'Transfer zeta', 'PPT beta state', 'Season phase state'
  ))

  break_str <- if (window_n >= 1500L) '4 months' else if (window_n >= 900L) '2 months' else '1 month'
  label_fmt <- if (window_n >= 1500L) '%Y-%m' else '%b %Y'

  p <- ggplot2::ggplot(long_df, ggplot2::aes(x = date, y = value, group = quantile)) +
    ggplot2::geom_line(
      data = subset(long_df, quantile == 'Observed USGS'),
      ggplot2::aes(color = quantile),
      linewidth = 1.1,
      alpha = 0.95,
      lineend = 'round'
    ) +
    ggplot2::geom_line(
      data = subset(long_df, quantile != 'Observed USGS'),
      ggplot2::aes(color = quantile),
      linewidth = 0.85,
      alpha = 0.95,
      lineend = 'round'
    ) +
    ggplot2::facet_wrap(~panel, ncol = 1L, scales = 'free_y') +
    ggplot2::scale_color_manual(values = c('Observed USGS' = '#111111', palette_quantiles)) +
    ggplot2::scale_x_date(date_breaks = break_str, date_labels = label_fmt) +
    ggplot2::labs(
      title = sprintf('Reduced-state cross-quantile audit over last %d observations', window_n),
      subtitle = 'USGS exps, trend, seasonal, transfer zeta, PPT beta, and seasonal phase across all quantiles',
      x = 'Date', y = 'Value', color = NULL
    ) +
    ggplot2::theme_minimal(base_size = 12) +
    ggplot2::theme(
      legend.position = 'bottom',
      legend.box = 'vertical',
      axis.text.x = ggplot2::element_text(angle = 45, hjust = 1),
      panel.grid.minor = ggplot2::element_blank()
    )

  ggplot2::ggsave(file.path(report_dir, sprintf('last%d_cross_quantile_state_audit.png', window_n)), p, width = 14, height = 16, dpi = 180)
  ggplot2::ggsave(file.path(report_dir, sprintf('last%d_cross_quantile_state_audit.pdf', window_n)), p, width = 14, height = 16)
}

plot_quantile_window <- function(df, q_label, window_n, report_dir) {
  level_df <- data.frame(
    date = rep(df$date, 3L),
    panel = 'USGS fit and reconstruction',
    series = factor(rep(c('Observed USGS', 'USGS exps', 'USGS reconstructed'), each = nrow(df)),
                    levels = c('Observed USGS', 'USGS exps', 'USGS reconstructed')),
    value = c(df$observed_usgs, df$exps_usgs, df$reconstructed_usgs),
    stringsAsFactors = FALSE
  )
  component_df <- data.frame(
    date = rep(df$date, 3L),
    panel = 'Observed-scale components',
    series = factor(rep(c('Trend contribution', 'Season contribution', 'Transfer zeta'), each = nrow(df)),
                    levels = c('Trend contribution', 'Season contribution', 'Transfer zeta')),
    value = c(df$trend_contrib, df$season_contrib, df$transfer_zeta),
    stringsAsFactors = FALSE
  )
  latent_df <- data.frame(
    date = rep(df$date, 2L),
    panel = 'Latent coordinates',
    series = factor(rep(c('Season phase state', 'PPT beta state'), each = nrow(df)),
                    levels = c('Season phase state', 'PPT beta state')),
    value = c(df$season_phase_state, df$beta_ppt),
    stringsAsFactors = FALSE
  )
  long_df <- rbind(level_df, component_df, latent_df)
  break_str <- if (window_n >= 1500L) '4 months' else if (window_n >= 900L) '2 months' else '1 month'
  label_fmt <- if (window_n >= 1500L) '%Y-%m' else '%b %Y'

  p <- ggplot2::ggplot(long_df, ggplot2::aes(x = date, y = value, color = series)) +
    ggplot2::geom_line(linewidth = 0.95, alpha = 0.96, na.rm = TRUE, lineend = 'round') +
    ggplot2::facet_wrap(~panel, ncol = 1L, scales = 'free_y') +
    ggplot2::scale_color_manual(values = component_colors) +
    ggplot2::scale_x_date(date_breaks = break_str, date_labels = label_fmt) +
    ggplot2::labs(
      title = sprintf('%s reduced-state identifiability audit over last %d observations', q_label, window_n),
      subtitle = 'Observed USGS, exps, reconstruction, trend, seasonal, transfer zeta, seasonal phase, and PPT beta',
      x = 'Date', y = 'Value', color = NULL
    ) +
    ggplot2::theme_minimal(base_size = 12) +
    ggplot2::theme(
      legend.position = 'bottom',
      legend.box = 'vertical',
      axis.text.x = ggplot2::element_text(angle = 45, hjust = 1),
      panel.grid.minor = ggplot2::element_blank()
    )

  ggplot2::ggsave(file.path(report_dir, sprintf('last%d_%s_state_identifiability_audit.png', window_n, q_label)), p, width = 14, height = 12, dpi = 180)
  ggplot2::ggsave(file.path(report_dir, sprintf('last%d_%s_state_identifiability_audit.pdf', window_n, q_label)), p, width = 14, height = 12)
}

main <- function() {
  require_pkg('ggplot2')
  require_pkg('yaml')

  args <- parse_args(commandArgs(trailingOnly = TRUE))
  repo_root <- normalizePath(args$repo_root %||% getwd(), mustWork = TRUE)
  context_run_root <- normalizePath(args$context_run_root %||% '', mustWork = TRUE)
  state_root <- normalizePath(args$state_root %||% '', mustWork = TRUE)
  report_dir <- normalizePath(args$report_dir %||% '', mustWork = FALSE)
  windows_raw <- as.character(args$windows %||% '2000,1000,500')
  window_sizes <- suppressWarnings(as.integer(strsplit(windows_raw, ',', fixed = TRUE)[[1L]]))
  window_sizes <- unique(window_sizes[is.finite(window_sizes) & window_sizes > 0L])
  if (!nzchar(report_dir)) stop('Provide --report-dir', call. = FALSE)
  dir.create(report_dir, recursive = TRUE, showWarnings = FALSE)

  cfg <- yaml::read_yaml(file.path(context_run_root, 'resolved_config.yaml'))
  ctx <- prepare_context(context_run_root = context_run_root, repo_root = repo_root, cfg = cfg)
  state_map <- NULL


  all_rows <- list()
  manifest_rows <- list()
  recon_rows <- list()

  first_state_dim <- NA_integer_
  for (k in seq_along(quantile_labels)) {
    q_label <- quantile_labels[[k]]
    q_suffix <- quantile_suffixes[[k]]
    message(sprintf('Loading %s', q_label))
    payload <- extract_quantile_state(state_root = state_root, quant_label = q_label, quant_suffix = q_suffix, TT_hist = ctx$TT)
    if (is.na(first_state_dim)) first_state_dim <- nrow(payload$sm)
    df_q <- compute_quantile_components(payload, ctx, q_label)
    all_rows[[length(all_rows) + 1L]] <- df_q
    manifest_rows[[length(manifest_rows) + 1L]] <- data.frame(
      quantile = q_label,
      rdata_path = payload$rdata_path,
      exps_length = length(payload$exps_usgs),
      sm_rows = nrow(payload$sm),
      sm_cols = ncol(payload$sm),
      stringsAsFactors = FALSE
    )
    recon_rows[[length(recon_rows) + 1L]] <- data.frame(
      quantile = q_label,
      rmse_exps_vs_reconstructed = sqrt(mean((df_q$exps_usgs - df_q$reconstructed_usgs)^2, na.rm = TRUE)),
      mae_exps_vs_reconstructed = mean(abs(df_q$exps_usgs - df_q$reconstructed_usgs), na.rm = TRUE),
      max_abs_exps_vs_reconstructed = max(abs(df_q$exps_usgs - df_q$reconstructed_usgs), na.rm = TRUE),
      mean_trend = mean(df_q$trend_contrib, na.rm = TRUE),
      mean_season = mean(df_q$season_contrib, na.rm = TRUE),
      mean_zeta = mean(df_q$transfer_zeta, na.rm = TRUE),
      mean_beta_ppt = mean(df_q$beta_ppt, na.rm = TRUE),
      stringsAsFactors = FALSE
    )
    invisible(gc(verbose = FALSE))
  }

  state_map <- build_state_map(ctx, state_dim = first_state_dim)
  write_csv_det(state_map, file.path(report_dir, 'state_coordinate_map.csv'))
  all_df <- do.call(rbind, all_rows)
  write_csv_det(all_df, file.path(report_dir, 'all_history_state_identifiability_full.csv'))
  write_csv_det(do.call(rbind, manifest_rows), file.path(report_dir, 'retained_state_manifest.csv'))
  write_csv_det(do.call(rbind, recon_rows), file.path(report_dir, 'reconstruction_summary.csv'))

  window_summary <- list()
  spread_summary <- list()
  for (window_n in window_sizes) {
    start_idx <- max(1L, ctx$TT - window_n + 1L)
    idx_dates <- ctx$hist_dates[seq.int(start_idx, ctx$TT)]
    window_df <- subset(all_df, date %in% idx_dates)
    plot_cross_quantile_window(window_df, length(idx_dates), report_dir)
    write_csv_det(window_df, file.path(report_dir, sprintf('last%d_state_identifiability_full.csv', length(idx_dates))))

    for (q_label in quantile_labels) {
      df_q <- subset(window_df, quantile == q_label)
      plot_quantile_window(df_q, q_label, length(idx_dates), report_dir)
    }

    wide_trend <- reshape(window_df[, c('date', 'quantile', 'trend_contrib')], idvar = 'date', timevar = 'quantile', direction = 'wide')
    wide_season <- reshape(window_df[, c('date', 'quantile', 'season_contrib')], idvar = 'date', timevar = 'quantile', direction = 'wide')
    wide_zeta <- reshape(window_df[, c('date', 'quantile', 'transfer_zeta')], idvar = 'date', timevar = 'quantile', direction = 'wide')
    wide_beta <- reshape(window_df[, c('date', 'quantile', 'beta_ppt')], idvar = 'date', timevar = 'quantile', direction = 'wide')
    spread_summary[[length(spread_summary) + 1L]] <- data.frame(
      window_n = length(idx_dates),
      start_date = as.character(min(idx_dates)),
      end_date = as.character(max(idx_dates)),
      mean_trend_range = mean(apply(wide_trend[, -1L, drop = FALSE], 1L, function(x) diff(range(x, na.rm = TRUE))), na.rm = TRUE),
      mean_season_range = mean(apply(wide_season[, -1L, drop = FALSE], 1L, function(x) diff(range(x, na.rm = TRUE))), na.rm = TRUE),
      mean_zeta_range = mean(apply(wide_zeta[, -1L, drop = FALSE], 1L, function(x) diff(range(x, na.rm = TRUE))), na.rm = TRUE),
      mean_beta_range = mean(apply(wide_beta[, -1L, drop = FALSE], 1L, function(x) diff(range(x, na.rm = TRUE))), na.rm = TRUE),
      stringsAsFactors = FALSE
    )

    window_summary[[length(window_summary) + 1L]] <- data.frame(
      window_n = length(idx_dates),
      start_date = as.character(min(idx_dates)),
      end_date = as.character(max(idx_dates)),
      stringsAsFactors = FALSE
    )
  }
  write_csv_det(do.call(rbind, window_summary), file.path(report_dir, 'window_summary.csv'))
  write_csv_det(do.call(rbind, spread_summary), file.path(report_dir, 'cross_quantile_spread_summary.csv'))

  readme <- c(
    '# Reduced exAL-M-T1 trend identifiability audit',
    '',
    sprintf('- context run root: `%s`', context_run_root),
    sprintf('- retained state root: `%s`', state_root),
    '- source objects: retained `new.theta.out_<q>_exAL_synth_DISC` from the reduced completed run seed root',
    '- model structure audited here: trend + harmonic 1 + PPT transfer only',
    '- state map is written to `state_coordinate_map.csv`',
    '- reconstruction summary compares `new.theta.out$exps[1, ]` against the reduced-state reconstruction `trend + season + zeta`',
    '',
    '## Main outputs',
    '- cross-quantile state audit plot for each requested window',
    '- per-quantile state identifiability plot for each requested window',
    '- full history CSV with trend/season/zeta/beta trajectories by quantile',
    '- state coordinate map, reconstruction summary, and cross-quantile spread summary'
  )
  writeLines(readme, con = file.path(report_dir, 'README.md'))
}

main()
