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
  if (exists("post_write_csv_deterministic", inherits = TRUE)) {
    post_write_csv_deterministic(df, path, numeric_digits = 15L)
  } else {
    utils::write.csv(df, path, row.names = FALSE)
  }
}

reasonableness_checks_df <- function(fc_df) {
  obs <- fc_df$observed
  data.frame(
    metric = c(
      "n_days",
      "obs_in_q05_q95",
      "obs_in_q20_q80",
      "obs_in_q35_q65",
      "obs_above_q80",
      "obs_above_q95",
      "obs_below_q20",
      "mae_vs_model_mean",
      "mae_vs_q50",
      "signed_bias_model_mean",
      "signed_bias_q50"
    ),
    value = c(
      length(obs),
      sum(obs >= fc_df$q05 & obs <= fc_df$q95),
      sum(obs >= fc_df$q20 & obs <= fc_df$q80),
      sum(obs >= fc_df$q35 & obs <= fc_df$q65),
      sum(obs > fc_df$q80),
      sum(obs > fc_df$q95),
      sum(obs < fc_df$q20),
      mean(abs(obs - fc_df$model_mean)),
      mean(abs(obs - fc_df$q50)),
      mean(fc_df$model_mean - obs),
      mean(fc_df$q50 - obs)
    ),
    stringsAsFactors = FALSE
  )
}

build_quantile_line_df <- function(fc_df) {
  quant_cols <- c("q05", "q20", "q35", "q50", "q65", "q80", "q95")
  rows <- lapply(quant_cols, function(col) {
    data.frame(
      date = fc_df$date,
      quantile = col,
      value = fc_df[[col]],
      stringsAsFactors = FALSE
    )
  })
  out <- do.call(rbind, rows)
  out$quantile <- factor(out$quantile, levels = quant_cols)
  out
}

build_forecast_quantile_plot <- function(fc_df, style, png_path, pdf_path) {
  require_pkg("ggplot2")
  palette <- c(
    q05 = "#9B1D20",
    q20 = "#C45D38",
    q35 = "#E38D2C",
    q50 = "#6A3D9A",
    q65 = "#2E86AB",
    q80 = "#1F9E89",
    q95 = "#006D2C"
  )
  labels <- c(
    q05 = "q05",
    q20 = "q20",
    q35 = "q35",
    q50 = "q50",
    q65 = "q65",
    q80 = "q80",
    q95 = "q95"
  )
  q_lines <- build_quantile_line_df(fc_df)
  line_widths <- c(q05 = 0.70, q20 = 0.75, q35 = 0.82, q50 = 1.18, q65 = 0.82, q80 = 0.75, q95 = 0.70)
  line_types <- c(q05 = "22", q20 = "solid", q35 = "solid", q50 = "solid", q65 = "solid", q80 = "solid", q95 = "22")
  forecast_origin <- as.character(min(fc_df$date) - 1)

  p <- ggplot2::ggplot(fc_df, ggplot2::aes(x = date)) +
    ggplot2::geom_ribbon(
      ggplot2::aes(ymin = interval_low, ymax = interval_high, fill = "95% credible band"),
      alpha = 0.25,
      color = NA
    ) +
    ggplot2::geom_ribbon(
      ggplot2::aes(ymin = q20, ymax = q80, fill = "q20-q80 band"),
      alpha = 0.30,
      color = NA
    ) +
    ggplot2::geom_line(
      data = q_lines,
      mapping = ggplot2::aes(y = value, color = quantile, linewidth = quantile, linetype = quantile, group = quantile),
      alpha = 0.92,
      lineend = "round",
      show.legend = TRUE
    ) +
    ggplot2::geom_line(
      ggplot2::aes(y = model_mean, color = "model_mean"),
      linewidth = 0.95,
      linetype = "22",
      lineend = "round"
    ) +
    ggplot2::geom_line(
      ggplot2::aes(y = observed, color = "heldout_usgs"),
      linewidth = 1.00,
      lineend = "round"
    ) +
    ggplot2::geom_point(
      ggplot2::aes(y = observed),
      color = "#B22222",
      fill = "white",
      shape = 21,
      stroke = 0.55,
      size = 1.8,
      show.legend = FALSE
    ) +
    ggplot2::scale_color_manual(
      values = c(
        setNames(palette, names(palette)),
        model_mean = "#111827",
        heldout_usgs = "#B22222"
      ),
      breaks = c("heldout_usgs", "model_mean", names(labels)),
      labels = c("Held-out USGS", "Posterior mean", unname(labels))
    ) +
    ggplot2::scale_linewidth_manual(
      values = line_widths,
      breaks = names(labels),
      labels = unname(labels)
    ) +
    ggplot2::scale_linetype_manual(
      values = line_types,
      breaks = names(labels),
      labels = unname(labels)
    ) +
    ggplot2::scale_fill_manual(
      values = c(
        "95% credible band" = "#F2B6CF",
        "q20-q80 band" = "#D97AA5"
      ),
      breaks = c("95% credible band", "q20-q80 band")
    ) +
    ggplot2::scale_x_date(date_breaks = "1 week", date_labels = "%b %d") +
    ggplot2::labs(
      title = "Forecast-Window Synthesized USGS Quantiles",
      subtitle = sprintf("Representative exAL-M-T1 cutoff %s", forecast_origin),
      x = "Forecast date",
      y = post_publication_y_label(style)
    ) +
    ggplot2::guides(
      color = ggplot2::guide_legend(order = 1, nrow = 2, byrow = TRUE, override.aes = list(alpha = 1)),
      linewidth = "none",
      linetype = "none",
      fill = ggplot2::guide_legend(order = 2, nrow = 1)
    ) +
    post_publication_base_theme(style) +
    ggplot2::theme(
      legend.position = "bottom",
      legend.direction = "horizontal",
      legend.box = "vertical",
      legend.text = ggplot2::element_text(size = 10.2),
      plot.margin = ggplot2::margin(10, 10, 8, 10)
    )

  post_publication_save_plot(p, png_path = png_path, pdf_path = pdf_path, style = style)
}

build_forecast_mean_plot <- function(fc_df, ensemble_df, style, png_path, pdf_path) {
  require_pkg("ggplot2")
  ensemble_df <- if (is.null(ensemble_df)) data.frame() else ensemble_df
  if (nrow(ensemble_df) > 0L) {
    ensemble_df <- ensemble_df[ensemble_df$date %in% fc_df$date, , drop = FALSE]
    ensemble_df$legend_label <- ifelse(ensemble_df$provider == "GloFAS", "GloFAS ensembles", "NWS ensembles")
  }

  p <- ggplot2::ggplot(fc_df, ggplot2::aes(x = date)) +
    ggplot2::geom_ribbon(
      ggplot2::aes(ymin = interval_low, ymax = interval_high, fill = "95% credible band"),
      alpha = 0.26,
      color = NA
    ) +
    ggplot2::geom_ribbon(
      ggplot2::aes(ymin = q20, ymax = q80, fill = "q20-q80 band"),
      alpha = 0.34,
      color = NA
    )

  if (nrow(ensemble_df) > 0L) {
    p <- p + ggplot2::geom_line(
      data = ensemble_df,
      mapping = ggplot2::aes(y = value, group = interaction(provider, member), color = legend_label),
      linewidth = 0.55,
      alpha = 0.20,
      lineend = "round"
    )
  }

  p <- p +
    ggplot2::geom_line(
      ggplot2::aes(y = model_mean, color = "Posterior mean"),
      linewidth = 1.15,
      lineend = "round"
    ) +
    ggplot2::geom_line(
      ggplot2::aes(y = q50, color = "Posterior median"),
      linewidth = 0.95,
      linetype = "22",
      lineend = "round"
    ) +
    ggplot2::geom_line(
      ggplot2::aes(y = observed, color = "Held-out USGS"),
      linewidth = 1.00,
      lineend = "round"
    ) +
    ggplot2::geom_point(
      ggplot2::aes(y = observed),
      color = "#B22222",
      fill = "white",
      shape = 21,
      stroke = 0.55,
      size = 1.8,
      show.legend = FALSE
    ) +
    ggplot2::scale_color_manual(
      values = c(
        "Posterior mean" = "#111827",
        "Posterior median" = "#8C2D5B",
        "Held-out USGS" = "#B22222",
        "GloFAS ensembles" = "#E67E22",
        "NWS ensembles" = "#756BB1"
      )
    ) +
    ggplot2::scale_fill_manual(
      values = c(
        "95% credible band" = "#F2B6CF",
        "q20-q80 band" = "#D97AA5"
      ),
      breaks = c("95% credible band", "q20-q80 band")
    ) +
    ggplot2::scale_x_date(date_breaks = "1 week", date_labels = "%b %d") +
    ggplot2::labs(
      title = "Forecast-Window Synthesized Mean and Bands",
      subtitle = "Held-out USGS and raw forecast ensembles overlaid",
      x = "Forecast date",
      y = post_publication_y_label(style)
    ) +
    ggplot2::guides(
      color = ggplot2::guide_legend(order = 1, nrow = 2, byrow = TRUE),
      fill = ggplot2::guide_legend(order = 2, nrow = 1)
    ) +
    post_publication_base_theme(style) +
    ggplot2::theme(
      legend.position = "bottom",
      legend.direction = "horizontal",
      legend.box = "vertical",
      legend.text = ggplot2::element_text(size = 10.2),
      plot.margin = ggplot2::margin(10, 10, 8, 10)
    )

  post_publication_save_plot(p, png_path = png_path, pdf_path = pdf_path, style = style)
}

build_forecast_central_plot <- function(fc_df, ensemble_df, style, png_path, pdf_path) {
  require_pkg("ggplot2")
  ensemble_df <- if (is.null(ensemble_df)) data.frame() else ensemble_df
  if (nrow(ensemble_df) > 0L) {
    ensemble_df <- ensemble_df[ensemble_df$date %in% fc_df$date, , drop = FALSE]
    ensemble_df$legend_label <- ifelse(ensemble_df$provider == "GloFAS", "GloFAS ensembles", "NWS ensembles")
  }

  upper_target <- max(
    c(fc_df$observed, fc_df$q80, fc_df$model_mean, fc_df$q65,
      if (nrow(ensemble_df) > 0L) ensemble_df$value else NA_real_),
    na.rm = TRUE
  )
  ylim_top <- max(6, ceiling(upper_target * 1.10))

  p <- ggplot2::ggplot(fc_df, ggplot2::aes(x = date)) +
    ggplot2::geom_ribbon(
      ggplot2::aes(ymin = q20, ymax = q80, fill = "q20-q80 band"),
      alpha = 0.28,
      color = NA
    ) +
    ggplot2::geom_ribbon(
      ggplot2::aes(ymin = q35, ymax = q65, fill = "q35-q65 band"),
      alpha = 0.36,
      color = NA
    )

  if (nrow(ensemble_df) > 0L) {
    p <- p + ggplot2::geom_line(
      data = ensemble_df,
      mapping = ggplot2::aes(y = value, group = interaction(provider, member), color = legend_label),
      linewidth = 0.55,
      alpha = 0.20,
      lineend = "round"
    )
  }

  p <- p +
    ggplot2::geom_line(
      ggplot2::aes(y = model_mean, color = "Posterior mean"),
      linewidth = 1.15,
      lineend = "round"
    ) +
    ggplot2::geom_line(
      ggplot2::aes(y = q50, color = "Posterior median"),
      linewidth = 0.95,
      linetype = "22",
      lineend = "round"
    ) +
    ggplot2::geom_line(
      ggplot2::aes(y = observed, color = "Held-out USGS"),
      linewidth = 1.00,
      lineend = "round"
    ) +
    ggplot2::geom_point(
      ggplot2::aes(y = observed),
      color = "#B22222",
      fill = "white",
      shape = 21,
      stroke = 0.55,
      size = 1.8,
      show.legend = FALSE
    ) +
    ggplot2::scale_color_manual(
      values = c(
        "Posterior mean" = "#111827",
        "Posterior median" = "#8C2D5B",
        "Held-out USGS" = "#B22222",
        "GloFAS ensembles" = "#E67E22",
        "NWS ensembles" = "#756BB1"
      )
    ) +
    ggplot2::scale_fill_manual(
      values = c(
        "q20-q80 band" = "#F2B6CF",
        "q35-q65 band" = "#D97AA5"
      ),
      breaks = c("q20-q80 band", "q35-q65 band")
    ) +
    ggplot2::scale_x_date(date_breaks = "1 week", date_labels = "%b %d") +
    ggplot2::coord_cartesian(ylim = c(0, ylim_top)) +
    ggplot2::labs(
      title = "Forecast-Window Central Synthesis Check",
      subtitle = "Clipped view to inspect central predictive behavior",
      x = "Forecast date",
      y = post_publication_y_label(style)
    ) +
    ggplot2::guides(
      color = ggplot2::guide_legend(order = 1, nrow = 2, byrow = TRUE),
      fill = ggplot2::guide_legend(order = 2, nrow = 1)
    ) +
    post_publication_base_theme(style) +
    ggplot2::theme(
      legend.position = "bottom",
      legend.direction = "horizontal",
      legend.box = "vertical",
      legend.text = ggplot2::element_text(size = 10.2),
      plot.margin = ggplot2::margin(10, 10, 8, 10)
    )

  post_publication_save_plot(p, png_path = png_path, pdf_path = pdf_path, style = style)
}

main <- function() {
  require_pkg("ggplot2")
  args <- parse_args(commandArgs(trailingOnly = TRUE))
  project_root <- normalizePath(getwd(), mustWork = TRUE)
  source(file.path(project_root, "R", "unified", "post_publication_figures.R"))

  run_root <- normalizePath(args$run_root %||% "", mustWork = TRUE)
  report_dir <- normalizePath(args$report_dir %||% "", mustWork = FALSE)
  if (!nzchar(report_dir)) {
    stop("Provide --report-dir", call. = FALSE)
  }
  dir.create(report_dir, recursive = TRUE, showWarnings = FALSE)

  outputs_dir <- file.path(run_root, "post", "outputs", basename(run_root))
  outputs_dir <- normalizePath(outputs_dir, mustWork = TRUE)
  quant_candidates <- Sys.glob(file.path(outputs_dir, "*_cutoff_window_quantiles.csv"))
  sample_candidates <- Sys.glob(file.path(outputs_dir, "*_cutoff_window_sample_subset.csv"))
  if (length(quant_candidates) != 1L || length(sample_candidates) != 1L) {
    stop("Expected exactly one cutoff-window quantile csv and one sample subset csv.", call. = FALSE)
  }

  quant_df <- post_publication_read_contract_csv(
    quant_candidates[[1L]],
    required_cols = c("model_id", "date", "segment", "observed", "q05", "q20", "q35", "q50", "q65", "q80", "q95"),
    context = "forecast-window review quantiles"
  )
  sample_df <- post_publication_read_contract_csv(
    sample_candidates[[1L]],
    required_cols = c("model_id", "draw_id", "sample_index", "date", "segment", "value"),
    context = "forecast-window review sample subset"
  )

  model_id <- unique(quant_df$model_id)
  if (length(model_id) != 1L) {
    stop("Expected one model_id in quantile contract.", call. = FALSE)
  }
  model_id <- model_id[[1L]]

  post_root <- post_publication_find_post_root(outputs_dir)
  cache_paths <- post_publication_resolve_posterior_cache_paths(post_root, model_id)
  style <- post_publication_load_style(project_root, file.path(project_root, "config", "post_publication_figures.yaml"))
  style$theme$legend_position <- "bottom"

  quant_focus <- post_publication_apply_exact_cache_interval(
    quant_df = quant_df,
    hist_cache_path = cache_paths$hist_cache_path,
    forecast_cache_path = cache_paths$forecast_cache_path,
    probs = c(0.025, 0.975),
    low_col = "interval_low",
    high_col = "interval_high"
  )
  quant_focus <- post_publication_apply_exact_cache_mean(
    quant_df = quant_focus,
    hist_cache_path = cache_paths$hist_cache_path,
    forecast_cache_path = cache_paths$forecast_cache_path,
    mean_col = "model_mean"
  )

  ensemble_paths <- post_publication_resolve_ensemble_input_paths(post_root)
  ensemble_frames <- list()
  if (!is.null(ensemble_paths$glofas_path) && file.exists(ensemble_paths$glofas_path)) {
    ensemble_frames[[length(ensemble_frames) + 1L]] <- post_publication_read_member_forecasts(ensemble_paths$glofas_path, "GloFAS")
  }
  if (!is.null(ensemble_paths$nws_path) && file.exists(ensemble_paths$nws_path)) {
    ensemble_frames[[length(ensemble_frames) + 1L]] <- post_publication_read_member_forecasts(ensemble_paths$nws_path, "NWS")
  }
  ensemble_df <- if (length(ensemble_frames) > 0L) do.call(rbind, ensemble_frames) else NULL

  focus_png <- file.path(report_dir, "cutoff_window_focus_log1p.png")
  focus_pdf <- sub("\\.png$", ".pdf", focus_png)
  focus_ens_png <- file.path(report_dir, "cutoff_window_focus_with_raw_ensembles_log1p.png")
  focus_ens_pdf <- sub("\\.png$", ".pdf", focus_ens_png)
  forecast_fan_png <- file.path(report_dir, "forecast_window_quantile_fan_log1p.png")
  forecast_fan_pdf <- sub("\\.png$", ".pdf", forecast_fan_png)
  forecast_mean_png <- file.path(report_dir, "forecast_window_mean_bands_and_ensembles_log1p.png")
  forecast_mean_pdf <- sub("\\.png$", ".pdf", forecast_mean_png)
  forecast_central_png <- file.path(report_dir, "forecast_window_central_reasonableness_log1p.png")
  forecast_central_pdf <- sub("\\.png$", ".pdf", forecast_central_png)

  post_publication_render_focus_posterior_plot(
    model_id = model_id,
    quant_df = quant_focus,
    sample_df = sample_df,
    png_path = focus_png,
    pdf_path = focus_pdf,
    style = style,
    source_run = basename(run_root),
    interval_low_col = "interval_low",
    interval_high_col = "interval_high",
    interval_label = "95% credible band",
    ensemble_df = NULL
  )

  post_publication_render_focus_posterior_plot(
    model_id = model_id,
    quant_df = quant_focus,
    sample_df = sample_df,
    png_path = focus_ens_png,
    pdf_path = focus_ens_pdf,
    style = style,
    source_run = basename(run_root),
    interval_low_col = "interval_low",
    interval_high_col = "interval_high",
    interval_label = "95% credible band",
    ensemble_df = ensemble_df
  )

  fc_df <- quant_focus[quant_focus$segment == "forecast", , drop = FALSE]
  fc_df$date <- as.Date(fc_df$date)
  fc_df <- fc_df[order(fc_df$date, method = "radix"), , drop = FALSE]

  build_forecast_quantile_plot(fc_df, style, forecast_fan_png, forecast_fan_pdf)
  build_forecast_mean_plot(fc_df, ensemble_df, style, forecast_mean_png, forecast_mean_pdf)
  build_forecast_central_plot(fc_df, ensemble_df, style, forecast_central_png, forecast_central_pdf)

  enriched_csv <- file.path(report_dir, "forecast_window_quantiles_with_exact_95_log1p.csv")
  write_csv_det(fc_df, enriched_csv)

  summary_df <- data.frame(
    metric = c(
      "forecast_start", "forecast_end", "n_forecast_days",
      "observed_min", "observed_max",
      "q50_min", "q50_max",
      "interval_low_min", "interval_high_max",
      "model_mean_min", "model_mean_max"
    ),
    value = c(
      as.character(min(fc_df$date)),
      as.character(max(fc_df$date)),
      as.character(nrow(fc_df)),
      sprintf("%.6f", min(fc_df$observed)),
      sprintf("%.6f", max(fc_df$observed)),
      sprintf("%.6f", min(fc_df$q50)),
      sprintf("%.6f", max(fc_df$q50)),
      sprintf("%.6f", min(fc_df$interval_low)),
      sprintf("%.6f", max(fc_df$interval_high)),
      sprintf("%.6f", min(fc_df$model_mean)),
      sprintf("%.6f", max(fc_df$model_mean))
    ),
    stringsAsFactors = FALSE
  )
  write_csv_det(summary_df, file.path(report_dir, "forecast_window_summary.csv"))
  write_csv_det(reasonableness_checks_df(fc_df), file.path(report_dir, "forecast_window_reasonableness_checks.csv"))

  md <- c(
    "# exAL-M-T1 Forecast-Window Review",
    "",
    sprintf("- run root: `%s`", run_root),
    sprintf("- outputs root: `%s`", outputs_dir),
    sprintf("- model id: `%s`", model_id),
    sprintf("- scale: `%s`", style$labels$y_scale_id %||% "log1p_cms"),
    "",
    "## Generated figures",
    "",
    sprintf("- full cutoff-window focus: `%s`", focus_png),
    sprintf("- full cutoff-window with raw ensembles: `%s`", focus_ens_png),
        sprintf("- forecast-window quantile fan: `%s`", forecast_fan_png),
        sprintf("- forecast-window mean/bands/ensembles: `%s`", forecast_mean_png),
        sprintf("- forecast-window central reasonableness: `%s`", forecast_central_png),
        "",
        "## Supporting files",
        "",
        sprintf("- enriched forecast quantiles: `%s`", enriched_csv),
        sprintf("- forecast summary: `%s`", file.path(report_dir, "forecast_window_summary.csv")),
        sprintf("- reasonableness checks: `%s`", file.path(report_dir, "forecast_window_reasonableness_checks.csv"))
  )
  writeLines(md, con = file.path(report_dir, "README.md"))

  cat(sprintf("WROTE %s\n", focus_png))
  cat(sprintf("WROTE %s\n", focus_ens_png))
  cat(sprintf("WROTE %s\n", forecast_fan_png))
  cat(sprintf("WROTE %s\n", forecast_mean_png))
  cat(sprintf("WROTE %s\n", forecast_central_png))
}

main()
