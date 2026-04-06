#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(ggplot2)
})

get_script_path <- function() {
  args <- commandArgs(trailingOnly = FALSE)
  file_arg <- args[grepl("^--file=", args)]
  if (length(file_arg) == 0L) {
    stop("Unable to determine script path from commandArgs().")
  }
  normalizePath(sub("^--file=", "", file_arg[1]), winslash = "/", mustWork = TRUE)
}

parse_args <- function(args, defaults) {
  out <- defaults
  for (arg in args) {
    if (!startsWith(arg, "--")) {
      next
    }
    parts <- strsplit(sub("^--", "", arg), "=", fixed = TRUE)[[1]]
    if (length(parts) != 2L) {
      stop(sprintf("Expected --key=value format, got: %s", arg))
    }
    key <- parts[1]
    value <- parts[2]
    out[[key]] <- value
  }
  out
}

discover_input_path <- function(explicit_path, candidate_paths) {
  if (!is.null(explicit_path) && nzchar(explicit_path)) {
    if (!file.exists(explicit_path)) {
      stop(sprintf("Input file does not exist: %s", explicit_path))
    }
    return(normalizePath(explicit_path, winslash = "/", mustWork = TRUE))
  }

  existing <- candidate_paths[file.exists(candidate_paths)]
  if (length(existing) == 0L) {
    stop(
      paste(
        "Could not find a retros.csv input. Checked:",
        paste(candidate_paths, collapse = "\n  - "),
        sep = "\n  - "
      )
    )
  }

  normalizePath(existing[1], winslash = "/", mustWork = TRUE)
}

read_retros_data <- function(path) {
  data <- read.csv(path, check.names = FALSE, stringsAsFactors = FALSE)
  required_cols <- c("Date", "USGS", "GloFAS", "NWS3.0")
  missing_cols <- setdiff(required_cols, names(data))
  if (length(missing_cols) > 0L) {
    stop(sprintf(
      "Input file is missing required columns: %s",
      paste(missing_cols, collapse = ", ")
    ))
  }

  data$Date <- as.Date(data$Date)
  for (col in required_cols[-1]) {
    data[[col]] <- as.numeric(data[[col]])
  }

  keep <- complete.cases(data[, required_cols])
  data <- data[keep, required_cols]
  rownames(data) <- NULL

  if (nrow(data) < 30L) {
    stop("Not enough complete observations for spectral analysis.")
  }

  data
}

calculate_w_values <- function(T) {
  m <- floor(T / 2)
  k <- seq_len(m)
  2 * pi * k / T
}

periodogram_custom <- function(w, y) {
  T <- length(y)
  m <- length(w)
  fft_values <- fft(y)
  abs(fft_values[2:(m + 1)])^2 * 2 / T
}

loglikelihood_wavelength <- function(I, y) {
  T <- length(y)
  like <- 1 - I / sum(y^2)
  like <- pmax(like, .Machine$double.eps)
  ((2 - T) / 2) * log(like)
}

detect_local_maxima <- function(values) {
  if (length(values) < 3L) {
    return(integer())
  }
  which(diff(sign(diff(values))) == -2) + 1L
}

format_period_label <- function(period_days) {
  sprintf(
    "%s d",
    format(round(period_days), trim = TRUE, big.mark = ",", scientific = FALSE)
  )
}

select_target_peaks <- function(peaks_df, target_periods) {
  available <- peaks_df
  selected_list <- vector("list", length(target_periods))

  for (i in seq_along(target_periods)) {
    target <- target_periods[i]
    if (nrow(available) == 0L) {
      stop("Ran out of local maxima while assigning target peaks.")
    }

    order_idx <- order(
      abs(available$period_days - target),
      -available$log_likelihood,
      available$period_days
    )
    pick <- available[order_idx[1], , drop = FALSE]
    pick$target_period_days <- target
    pick$target_label <- sprintf("Target %d d", round(target))
    pick$abs_error_days <- abs(pick$period_days - target)
    selected_list[[i]] <- pick

    available <- available[-order_idx[1], , drop = FALSE]
  }

  selected <- do.call(rbind, selected_list)
  rownames(selected) <- NULL
  selected[order(selected$target_period_days), ]
}

run_spectral_analysis <- function(values, series_id, series_label, color, analysis_period_max_days, target_periods) {
  T <- length(values)
  w <- calculate_w_values(T)
  I <- periodogram_custom(w, values)
  log_like <- loglikelihood_wavelength(I, values)
  period_days <- 2 * pi / w

  keep <- is.finite(period_days) & is.finite(log_like) & period_days <= analysis_period_max_days
  period_days <- period_days[keep]
  log_like <- log_like[keep]

  peak_idx <- detect_local_maxima(log_like)
  peaks <- data.frame(
    series_id = series_id,
    series_label = series_label,
    color = color,
    period_days = period_days[peak_idx],
    period_years = period_days[peak_idx] / 365,
    log_likelihood = log_like[peak_idx],
    stringsAsFactors = FALSE
  )

  if (nrow(peaks) == 0L) {
    stop(sprintf("No local maxima found for series %s", series_label))
  }

  peaks <- select_target_peaks(peaks, target_periods)
  peaks$rank <- seq_len(nrow(peaks))
  peaks$period_label <- format_period_label(peaks$period_days)

  curve <- data.frame(
    series_id = series_id,
    series_label = series_label,
    color = color,
    period_days = period_days,
    log_likelihood = log_like,
    stringsAsFactors = FALSE
  )
  curve <- curve[order(curve$period_days), ]
  peaks <- peaks[order(peaks$period_days), ]

  list(curve = curve, peaks = peaks)
}

save_plot_png <- function(plot_obj, path, width, height, dpi) {
  if (requireNamespace("ragg", quietly = TRUE)) {
    ragg::agg_png(
      filename = path,
      width = width,
      height = height,
      units = "in",
      res = dpi,
      scaling = 1,
      background = "white"
    )
    on.exit(grDevices::dev.off(), add = TRUE)
    print(plot_obj)
  } else {
    ggsave(
      filename = path,
      plot = plot_obj,
      width = width,
      height = height,
      units = "in",
      dpi = dpi,
      bg = "white"
    )
  }
}

main <- function() {
  script_path <- get_script_path()
  repo_root <- normalizePath(file.path(dirname(script_path), ".."), winslash = "/", mustWork = TRUE)
  args <- parse_args(
    commandArgs(trailingOnly = TRUE),
    defaults = list(
      input = NULL,
      output_dir = file.path(repo_root, "exports", "spectral_retros_targets_180_365_790_20260310"),
      analysis_period_max_days = "1200",
      display_period_max_days = "1200",
      target_periods = "180,365,790"
    )
  )

  candidate_inputs <- c(
    file.path(repo_root, "repro", "runs", "multimodel_20221225", "inputs", "shared", "retros", "retros.csv"),
    file.path(repo_root, "repro", "runs", "multimodel_20220511", "inputs", "shared", "retros", "retros.csv"),
    file.path(repo_root, "repro", "runs", "multimodel_20211221", "inputs", "shared", "retros", "retros.csv"),
    file.path(repo_root, "repro", "runs", "multimodel_20211112", "inputs", "shared", "retros", "retros.csv")
  )

  input_path <- discover_input_path(args$input, candidate_inputs)
  output_dir <- normalizePath(args$output_dir, winslash = "/", mustWork = FALSE)
  analysis_period_max_days <- as.numeric(args$analysis_period_max_days)
  display_period_max_days <- as.numeric(args$display_period_max_days)
  target_periods <- as.numeric(strsplit(args$target_periods, ",", fixed = TRUE)[[1]])

  if (!is.finite(analysis_period_max_days) || analysis_period_max_days <= 0) {
    stop("--analysis_period_max_days must be a positive number.")
  }
  if (!is.finite(display_period_max_days) || display_period_max_days <= 0) {
    stop("--display_period_max_days must be a positive number.")
  }
  if (display_period_max_days > analysis_period_max_days) {
    stop("--display_period_max_days cannot exceed --analysis_period_max_days.")
  }
  if (length(target_periods) == 0L || any(!is.finite(target_periods)) || any(target_periods <= 0)) {
    stop("--target_periods must be a comma-separated list of positive numbers.")
  }
  target_periods <- unique(target_periods)
  target_periods <- sort(target_periods)

  dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

  data <- read_retros_data(input_path)
  series_specs <- data.frame(
    series_id = c("USGS", "GloFAS", "NWS3.0"),
    series_label = c("USGS observed", "GloFAS retrospective", "NWS retrospective"),
    color = c("#2F855A", "#E67E22", "#756BB1"),
    stringsAsFactors = FALSE
  )

  results <- lapply(seq_len(nrow(series_specs)), function(i) {
    spec <- series_specs[i, ]
    run_spectral_analysis(
      values = data[[spec$series_id]],
      series_id = spec$series_id,
      series_label = spec$series_label,
      color = spec$color,
      analysis_period_max_days = analysis_period_max_days,
      target_periods = target_periods
    )
  })

  curve_df <- do.call(rbind, lapply(results, `[[`, "curve"))
  peak_df <- do.call(rbind, lapply(results, `[[`, "peaks"))

  curve_df$series_label <- factor(curve_df$series_label, levels = series_specs$series_label)
  peak_df$series_label <- factor(peak_df$series_label, levels = series_specs$series_label)
  curve_plot_df <- curve_df[curve_df$period_days <= display_period_max_days, ]
  peak_plot_df <- peak_df[peak_df$period_days <= display_period_max_days, ]

  plot_obj <- ggplot(curve_plot_df, aes(x = period_days, y = log_likelihood)) +
    geom_line(aes(color = color), linewidth = 0.8, lineend = "round", show.legend = FALSE) +
    geom_point(
      data = peak_plot_df,
      fill = "#C53030",
      shape = 21,
      size = 3.0,
      stroke = 0.75,
      color = "white",
      show.legend = FALSE
    ) +
    facet_wrap(~series_label, ncol = 1, scales = "free_y") +
    scale_color_identity() +
    scale_fill_identity() +
    scale_x_continuous(
      limits = c(0, display_period_max_days),
      labels = scales::label_comma(),
      breaks = scales::breaks_pretty(n = 8),
      expand = expansion(mult = c(0.01, 0.08))
    ) +
    labs(
      title = "Observed vs Retrospective Spectral Peaks",
      subtitle = paste0(
        "San Lorenzo River (11160500), daily flow, ",
        format(min(data$Date)),
        " to ",
        format(max(data$Date)),
        ". Nearest local maxima to 180, 365, and 790 days."
      ),
      x = "Period (days)",
      y = "Log-likelihood",
      caption = paste0(
        "Input: ",
        input_path,
        "\nPeaks selected over 0-",
        format(analysis_period_max_days, trim = TRUE, big.mark = ",", scientific = FALSE),
        " days; figure shows 0-",
        format(display_period_max_days, trim = TRUE, big.mark = ",", scientific = FALSE),
        " days."
      )
    ) +
    theme_minimal(base_size = 13) +
    theme(
      plot.title = element_text(face = "bold", size = 18, color = "#1F2933"),
      plot.subtitle = element_text(size = 11.5, color = "#4A5568"),
      plot.caption = element_text(size = 9, color = "#5F6C7B", hjust = 0),
      strip.text = element_text(face = "bold", size = 13, color = "#1F2933"),
      strip.background = element_rect(fill = "#F3F0E8", color = NA),
      panel.grid.minor = element_blank(),
      panel.grid.major.x = element_line(color = "#D9DEE7", linewidth = 0.35),
      panel.grid.major.y = element_line(color = "#EEF2F7", linewidth = 0.30),
      panel.spacing = grid::unit(0.9, "lines"),
      axis.title = element_text(face = "bold", color = "#243B53"),
      axis.text = element_text(color = "#334E68"),
      plot.margin = margin(t = 14, r = 26, b = 14, l = 12)
    )

  if (requireNamespace("ggrepel", quietly = TRUE)) {
    plot_obj <- plot_obj +
      ggrepel::geom_label_repel(
        data = peak_plot_df,
        aes(label = period_label),
        seed = 20260310,
        size = 2.9,
        family = "",
        fontface = "bold",
        fill = scales::alpha("white", 0.92),
        color = "#9B2C2C",
        label.size = 0.18,
        segment.color = scales::alpha("#C53030", 0.75),
        segment.size = 0.30,
        box.padding = 0.25,
        point.padding = 0.18,
        min.segment.length = 0,
        max.overlaps = Inf,
        show.legend = FALSE
      )
  } else {
    plot_obj <- plot_obj +
      geom_label(
        data = peak_plot_df,
        aes(label = period_label),
        size = 2.8,
        fill = scales::alpha("white", 0.90),
        color = "#9B2C2C",
        label.size = 0.18,
        label.padding = grid::unit(0.10, "lines"),
        label.r = grid::unit(0.12, "lines"),
        vjust = -0.8,
        show.legend = FALSE
      )
  }

  peak_summary <- peak_df[order(peak_df$series_label, peak_df$rank), c(
    "series_id", "series_label", "rank", "period_days", "period_years",
    "log_likelihood", "period_label", "target_period_days", "target_label", "abs_error_days"
  )]
  peak_summary$in_display_window <- peak_summary$period_days <= display_period_max_days
  rownames(peak_summary) <- NULL

  png_path <- file.path(output_dir, "spectral_retros_3x1_targets_180_365_790.png")
  pdf_path <- file.path(output_dir, "spectral_retros_3x1_targets_180_365_790.pdf")
  csv_path <- file.path(output_dir, "spectral_retros_targets_180_365_790_peaks.csv")
  meta_path <- file.path(output_dir, "spectral_retros_metadata.txt")

  export_width <- 14
  export_height <- 15
  export_dpi <- 600

  save_plot_png(plot_obj, png_path, width = export_width, height = export_height, dpi = export_dpi)
  ggsave(
    pdf_path,
    plot = plot_obj,
    device = grDevices::cairo_pdf,
    width = export_width,
    height = export_height,
    units = "in",
    bg = "white"
  )
  write.csv(peak_summary, csv_path, row.names = FALSE)

  metadata <- c(
    sprintf("generated_at=%s", format(Sys.time(), tz = "UTC", usetz = TRUE)),
    sprintf("input_path=%s", input_path),
    sprintf("rows_used=%d", nrow(data)),
    sprintf("date_min=%s", format(min(data$Date))),
    sprintf("date_max=%s", format(max(data$Date))),
    sprintf(
      "analysis_period_max_days=%s",
      format(analysis_period_max_days, trim = TRUE, scientific = FALSE)
    ),
    sprintf(
      "display_period_max_days=%s",
      format(display_period_max_days, trim = TRUE, scientific = FALSE)
    ),
    sprintf(
      "target_periods=%s",
      paste(format(target_periods, trim = TRUE, scientific = FALSE), collapse = ",")
    ),
    sprintf("png=%s", png_path),
    sprintf("pdf=%s", pdf_path),
    sprintf("peaks_csv=%s", csv_path),
    sprintf("export_width_in=%d", export_width),
    sprintf("export_height_in=%d", export_height),
    sprintf("export_dpi=%d", export_dpi)
  )
  writeLines(metadata, meta_path)

  message(sprintf("Wrote figure: %s", png_path))
  message(sprintf("Wrote figure: %s", pdf_path))
  message(sprintf("Wrote peaks:  %s", csv_path))
  message(sprintf("Wrote meta:   %s", meta_path))
  print(peak_summary)
}

main()
