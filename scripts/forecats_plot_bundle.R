#!/usr/bin/env Rscript

# Plot forecats figure from a self-contained bundle directory.
#
# Expected bundle layout:
#   <bundle_dir>/
#     meta.yaml
#     inputs/
#       usgs_daily.csv
#       retros_daily.csv
#       glofas_weighted_daily.csv
#       nws_weighted_daily.csv
#     figures/
#       forecats.png   (created)
#
# All input flows are expected to be stored in raw cms (m^3/s).

suppressPackageStartupMessages({
  library(yaml)
  library(readr)
  library(dplyr)
  library(tidyr)
  library(ggplot2)
})

parse_args <- function(argv) {
  out <- list()
  i <- 1
  while (i <= length(argv)) {
    a <- argv[[i]]
    if (startsWith(a, "--")) {
      key <- sub("^--", "", a)
      if (i == length(argv) || startsWith(argv[[i + 1]], "--")) {
        out[[key]] <- TRUE
        i <- i + 1
      } else {
        out[[key]] <- argv[[i + 1]]
        i <- i + 2
      }
    } else {
      i <- i + 1
    }
  }
  out
}

transform_flow <- function(x_cms, scale) {
  if (scale == "raw_cms") {
    return(x_cms)
  }
  if (scale == "log1p_cms") {
    # Guard against invalid values (shouldn't happen for discharge).
    out <- rep(NA_real_, length(x_cms))
    ok <- !is.na(x_cms) & (x_cms > -1)
    out[ok] <- log(x_cms[ok] + 1)
    return(out)
  }
  if (scale == "log_log1p_cms") {
    # log(log1p(x)) is only defined for log1p(x) > 0 => x > 0.
    out <- rep(NA_real_, length(x_cms))
    ok <- !is.na(x_cms) & (x_cms > 0)
    out[ok] <- log(log(x_cms[ok] + 1))
    return(out)
  }
  stop(paste("Unknown plot_scale:", scale))
}

plot_forecats_bundle <- function(bundle_dir) {
  bundle_dir <- normalizePath(bundle_dir, mustWork = TRUE)
  meta_path <- file.path(bundle_dir, "meta.yaml")
  if (!file.exists(meta_path)) stop(paste("Missing meta.yaml:", meta_path))
  meta <- yaml::read_yaml(meta_path)

  inputs_dir <- file.path(bundle_dir, "inputs")
  figures_dir <- file.path(bundle_dir, "figures")
  dir.create(figures_dir, showWarnings = FALSE, recursive = TRUE)

  usgs_path <- file.path(inputs_dir, meta$paths$usgs_daily)
  retros_path <- file.path(inputs_dir, meta$paths$retros_daily)
  glofas_path <- file.path(inputs_dir, meta$paths$glofas_weighted_daily)
  nws_path <- file.path(inputs_dir, meta$paths$nws_weighted_daily)

  plot_scale <- meta$transforms$plot_scale
  cutoff_date <- as.Date(meta$dates$cutoff_date)
  forecast_start <- as.Date(meta$dates$forecast_start_date)
  plot_start <- as.Date(meta$dates$plot_start)
  plot_end <- as.Date(meta$dates$plot_end)

  # -------------------------
  # Load inputs
  # -------------------------
  usgs <- readr::read_csv(usgs_path, show_col_types = FALSE) %>%
    mutate(date = as.Date(date)) %>%
    mutate(discharge_cms = as.numeric(discharge_cms)) %>%
    filter(date >= plot_start & date <= plot_end) %>%
    mutate(
      obs_type = ifelse(date >= forecast_start, "After", "Before"),
      value = transform_flow(discharge_cms, plot_scale)
    )

  retros <- readr::read_csv(retros_path, show_col_types = FALSE) %>%
    mutate(date = as.Date(date)) %>%
    mutate(
      usgs_cms = as.numeric(usgs_cms),
      glofas_cms = as.numeric(glofas_cms),
      nws_cms = as.numeric(nws_cms)
    ) %>%
    filter(date >= plot_start & date < forecast_start)

  retros_long <- retros %>%
    select(date, glofas_cms, nws_cms) %>%
    pivot_longer(cols = c(glofas_cms, nws_cms), names_to = "Source", values_to = "cms") %>%
    mutate(
      Source = recode(Source, glofas_cms = "GloFAS", nws_cms = "NWS"),
      value = transform_flow(cms, plot_scale)
    )

  # Forecast ensembles (wide -> long)
  read_ens_long <- function(path, provider_label) {
    df <- readr::read_csv(path, show_col_types = FALSE) %>%
      mutate(target_date = as.Date(target_date)) %>%
      filter(target_date >= forecast_start & target_date <= plot_end)

    long <- df %>%
      pivot_longer(cols = -target_date, names_to = "member", values_to = "cms") %>%
      mutate(
        provider = provider_label,
        cms = as.numeric(cms),
        value = transform_flow(cms, plot_scale)
      )
    long
  }

  glofas_ens_long <- read_ens_long(glofas_path, "GloFAS")
  nws_ens_long <- read_ens_long(nws_path, "NWS")

  # -------------------------
  # Styling
  # -------------------------
  glofas_color <- "#E67E22"
  nws_color <- "#756bb1"
  usgs_color <- "#238b45"

  usgs_before <- usgs %>% filter(obs_type == "Before") %>% mutate(Source = "USGS")
  usgs_after <- usgs %>% filter(obs_type == "After") %>% mutate(Source = "USGS")

  # Optional flood thresholds (must be in discharge units, not stage).
  # Define in YAML under plot.flood_levels:
  #   - label: "Major Flooding"
  #     value: 15000
  #     unit: "cfs"   # or "cms"
  flood_levels <- meta$plot$flood_levels
  if ((is.null(flood_levels) || length(flood_levels) == 0) &&
      !is.null(meta$site$usgs_site) &&
      as.character(meta$site$usgs_site) == "11160500") {
    # Backwards-compatible defaults for this project/site so flood lines
    # always render even for older bundles/configs that predate flood_levels.
    flood_levels <- list(
      list(label = "Major Flooding", value = 15000, unit = "cfs"),
      list(label = "Minor Flooding", value = 6750, unit = "cfs")
    )
  }
  flood_df <- NULL
  if (!is.null(flood_levels) && length(flood_levels) > 0) {
    CFSToCMS <- 0.0283168466
    to_cms <- function(v, unit) {
      if (is.null(unit) || unit == "") stop("plot.flood_levels[*].unit is required (cfs or cms).")
      if (unit == "cms") return(as.numeric(v))
      if (unit == "cfs") return(as.numeric(v) * CFSToCMS)
      stop(paste("Unknown flood_levels unit:", unit))
    }
    labels <- c()
    yvals <- c()
    for (lvl in flood_levels) {
      if (is.null(lvl$label) || lvl$label == "") next
      if (is.null(lvl$value)) next
      cms <- to_cms(lvl$value, lvl$unit %||% "cfs")
      yvals <- c(yvals, transform_flow(cms, plot_scale))
      labels <- c(labels, lvl$label)
    }
    flood_df <- tibble::tibble(label = labels, y = yvals)
  }

  # -------------------------
  # Plot
  # -------------------------
  y_lab <- switch(
    plot_scale,
    raw_cms = "Water Flow (m^3/s)",
    log1p_cms = "Water Flow (log1p(m^3/s))",
    log_log1p_cms = "Water Flow (log(log1p(m^3/s)))",
    paste0("Water Flow (", plot_scale, ")")
  )

  p <- ggplot() +
    # Flood stage horizontal lines + labels (if configured)
    {if (!is.null(flood_df) && nrow(flood_df) > 0) geom_hline(
      data = flood_df,
      aes(yintercept = y),
      linetype = "dashed",
      color = "gray",
      linewidth = 0.8
    )} +
    {if (!is.null(flood_df) && nrow(flood_df) > 0) annotate(
      "text",
      x = plot_end,
      y = flood_df$y,
      label = flood_df$label,
      hjust = 1.02,
      vjust = -0.5,
      color = "black",
      fontface = "italic",
      size = 3.5
    )} +
    # Retros before (GloFAS + NWS)
    geom_line(
      data = retros_long,
      aes(x = date, y = value, color = Source, linetype = Source, group = Source),
      linewidth = 0.5,
      alpha = 0.85,
      na.rm = TRUE
    ) +
    geom_point(
      data = retros_long,
      aes(x = date, y = value, color = Source, shape = Source),
      size = 1.3,
      alpha = 0.85,
      na.rm = TRUE
    ) +
    # USGS before
    geom_line(
      data = usgs_before,
      aes(x = date, y = value, color = Source, linetype = Source),
      linewidth = 0.5,
      na.rm = TRUE
    ) +
    geom_point(
      data = usgs_before,
      aes(x = date, y = value, color = Source, shape = Source),
      size = 1.4,
      na.rm = TRUE
    ) +
    # Forecast ensembles after (thin, no legend)
    geom_line(
      data = glofas_ens_long,
      aes(x = target_date, y = value, group = member),
      color = glofas_color,
      alpha = 0.22,
      linewidth = 0.5,
      show.legend = FALSE,
      na.rm = TRUE
    ) +
    geom_line(
      data = nws_ens_long,
      aes(x = target_date, y = value, group = member),
      color = nws_color,
      alpha = 0.22,
      linewidth = 0.5,
      show.legend = FALSE,
      na.rm = TRUE
    ) +
    # USGS after (dashed)
    geom_line(
      data = usgs_after,
      aes(x = date, y = value),
      color = "#B22222",
      linewidth = 0.5,
      linetype = "dashed",
      show.legend = FALSE,
      na.rm = TRUE
    ) +
    geom_point(
      data = usgs_after,
      aes(x = date, y = value),
      color = "#B22222",
      size = 1.8,
      show.legend = FALSE,
      na.rm = TRUE
    ) +
    scale_color_manual(
      name = "Data Source",
      values = c("USGS" = usgs_color, "GloFAS" = glofas_color, "NWS" = nws_color)
    ) +
    scale_linetype_manual(
      name = "Data Source",
      values = c("USGS" = "solid", "GloFAS" = "solid", "NWS" = "solid")
    ) +
    scale_shape_manual(
      name = "Data Source",
      values = c("USGS" = 16, "GloFAS" = 16, "NWS" = 16)
    ) +
    scale_x_date(breaks = scales::pretty_breaks(6), date_labels = "%b %d") +
    labs(
      title = meta$plot$title,
      x = paste0("Date (", format(plot_start, "%Y"), "-", format(plot_end, "%Y"), ")"),
      y = y_lab
    ) +
    guides(
      color = guide_legend(override.aes = list(size = 2, shape = 16, linetype = "solid")),
      shape = "none",
      linetype = "none"
    ) +
    theme_minimal(base_size = 14) +
    theme(
      plot.title = element_text(size = 16, face = "bold", hjust = 0.5),
      axis.title = element_text(face = "bold"),
      legend.position = "top",
      legend.title = element_text(face = "bold"),
      panel.grid.minor = element_blank()
    )

  # Optional markers
  if (!is.null(meta$plot$markers) && length(meta$plot$markers) > 0) {
    for (m in meta$plot$markers) {
      d <- as.Date(m$date)
      p <- p +
        geom_vline(
          xintercept = d,
          color = m$color %||% "gray40",
          linetype = "dashed",
          linewidth = 0.5,
          alpha = 0.8
        )
      if (!is.null(m$label) && m$label != "") {
        p <- p + annotate(
          "text",
          x = d,
          y = min(usgs$value, na.rm = TRUE) - 0.15,
          label = m$label,
          color = m$color %||% "gray40",
          vjust = 4,
          hjust = -0.1,
          fontface = "bold",
          size = 3.5
        )
      }
    }
  }

  out_path <- file.path(figures_dir, "forecats.png")
  ggsave(filename = out_path, plot = p, width = 12, height = 6, units = "in", dpi = 300)
  message("Wrote: ", out_path)
  invisible(out_path)
}

`%||%` <- function(x, y) if (is.null(x)) y else x

if (sys.nframe() == 0) {
  argv <- commandArgs(trailingOnly = TRUE)
  args <- parse_args(argv)
  if (is.null(args$`bundle-dir`)) {
    stop("Usage: scripts/forecats_plot_bundle.R --bundle-dir <path>")
  }
  plot_forecats_bundle(args$`bundle-dir`)
}
