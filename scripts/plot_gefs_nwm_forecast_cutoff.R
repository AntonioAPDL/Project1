#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(yaml)
  library(readr)
  library(dplyr)
  library(tidyr)
  library(ggplot2)
  library(scales)
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

`%||%` <- function(x, y) if (is.null(x) || identical(x, "")) y else x

stop_if_missing <- function(x, msg) {
  if (is.null(x) || identical(x, "")) stop(msg, call. = FALSE)
}

as_abs_path <- function(p) {
  if (startsWith(p, "/")) return(p)
  normalizePath(file.path(getwd(), p), mustWork = FALSE)
}

slugify <- function(x) {
  x <- gsub("[^A-Za-z0-9]+", "_", x)
  x <- gsub("_+", "_", x)
  x <- gsub("^_|_$", "", x)
  ifelse(nzchar(x), x, "na")
}

wrap_label <- function(x, width = 28) {
  vapply(
    as.character(x),
    function(xx) paste(strwrap(xx, width = width), collapse = "\n"),
    character(1)
  )
}

source_type_label <- function(source, product_family) {
  if (identical(source, "GEFS")) return("GEFS full ensemble")
  pf <- as.character(product_family)
  if (pf == "short_range_land") return("NWM short-range land")
  if (pf == "medium_range_land") return("NWM medium-range land")
  if (pf == "long_range_land") return("NWM long-range land")
  if (pf == "short_range_forcing") return("NWM short-range forcing")
  if (pf == "medium_range_forcing") return("NWM medium-range forcing")
  paste("NWM", pf)
}

source_palette <- c(
  "GEFS full ensemble" = "#C65D2E",
  "NWM short-range land" = "#2A6F97",
  "NWM medium-range land" = "#0B8F8C",
  "NWM long-range land" = "#5E8C31",
  "NWM short-range forcing" = "#7A4EAB",
  "NWM medium-range forcing" = "#355C7D"
)

custom_theme <- function() {
  theme_minimal(base_size = 13) +
    theme(
      plot.background = element_rect(fill = "#F6F3EC", color = NA),
      panel.background = element_rect(fill = "#FCFBF8", color = NA),
      panel.grid.minor = element_blank(),
      panel.grid.major.x = element_line(color = "#E2DDD2", linewidth = 0.25),
      panel.grid.major.y = element_line(color = "#D7D0C3", linewidth = 0.30),
      strip.background = element_rect(fill = "#EDE6D8", color = "#D5CAB4", linewidth = 0.4),
      strip.text = element_text(face = "bold", size = 11, color = "#2F2922", lineheight = 1.02),
      axis.title = element_text(face = "bold", color = "#2F2922"),
      axis.text = element_text(color = "#3A332B"),
      plot.title = element_text(face = "bold", size = 18, color = "#1F1A15"),
      plot.subtitle = element_text(size = 11.5, color = "#4A4237", lineheight = 1.05),
      plot.caption = element_text(size = 9.5, color = "#5A5247", hjust = 0),
      legend.position = "bottom",
      legend.title = element_text(face = "bold"),
      legend.text = element_text(size = 10),
      panel.spacing = unit(10, "pt")
    )
}

read_site <- function(path) {
  cfg <- yaml::read_yaml(path)
  site <- cfg$site %||% list()
  list(
    usgs_site = as.character(site$usgs_site %||% "11160500"),
    lat = as.numeric(site$lat %||% 37.0443931),
    lon = as.numeric(site$lon %||% -122.072464)
  )
}

read_catalogs <- function(run_dir, site_id) {
  handoff_root <- file.path(
    run_dir,
    "handoff_forecasts",
    paste0("site=", site_id),
    paste0("run_id=", basename(normalizePath(run_dir, mustWork = FALSE))),
    "catalogs"
  )
  list(
    gefs = readr::read_csv(file.path(handoff_root, "gefs_catalog.csv"), show_col_types = FALSE),
    nwm = readr::read_csv(file.path(handoff_root, "nwm_catalog.csv"), show_col_types = FALSE),
    handoff_root = dirname(handoff_root)
  )
}

read_covariate_series <- function(path, value_candidates, series_name) {
  if (!file.exists(path)) {
    stop(sprintf("Covariate file not found for %s: %s", series_name, path), call. = FALSE)
  }

  df <- readr::read_csv(path, show_col_types = FALSE)
  date_col <- intersect(c("Date", "time"), names(df))
  value_col <- intersect(value_candidates, names(df))

  if (length(date_col) == 0) {
    stop(sprintf("No Date/time column found in %s for %s", path, series_name), call. = FALSE)
  }
  if (length(value_col) == 0) {
    stop(
      sprintf(
        "No expected value column found in %s for %s. Expected one of: %s",
        path, series_name, paste(value_candidates, collapse = ", ")
      ),
      call. = FALSE
    )
  }

  tibble(
    time = as.Date(df[[date_col[[1]]]]),
    value = as.numeric(df[[value_col[[1]]]])
  ) %>%
    filter(!is.na(time), is.finite(value)) %>%
    arrange(time)
}

build_covariate_overlay <- function(path, cutoff_date, max_days, series_name, value_candidates) {
  cutoff <- as.Date(cutoff_date)
  end_date <- cutoff + ceiling(max_days)
  raw_df <- read_covariate_series(path, value_candidates = value_candidates, series_name = series_name)

  overlay_df <- raw_df %>%
    filter(time > cutoff, time <= end_date) %>%
    mutate(lead_days = as.numeric(time - cutoff))

  if (nrow(overlay_df) == 0) {
    stop(
      sprintf(
        "No covariate rows found for %s after cutoff %s in %s",
        series_name, cutoff_date, path
      ),
      call. = FALSE
    )
  }

  q05 <- quantile(overlay_df$value, probs = 0.05, na.rm = TRUE, type = 7)
  q95 <- quantile(overlay_df$value, probs = 0.95, na.rm = TRUE, type = 7)
  overlay_df %>%
    mutate(
      value_norm = dplyr::case_when(
        is.finite(q05) & is.finite(q95) & (q95 > q05) ~ pmin(pmax((value - q05) / (q95 - q05), 0), 1),
        TRUE ~ 0.5
      ),
      series_name = series_name,
      source_path = path
    )
}

build_panel_label <- function(df) {
  source_type <- if ("source_type" %in% names(df)) {
    as.character(df$source_type)
  } else {
    mapply(source_type_label, df$source, df$product_family, USE.NAMES = FALSE)
  }
  units <- ifelse(is.na(df$units) | !nzchar(df$units), "native units", df$units)
  horizon <- paste0("+", df$lead_hours_min, "h to +", df$lead_hours_max, "h")
  members <- paste0(df$member_columns, ifelse(df$member_columns == 1, " member", " members"))
  paste0(
    source_type,
    "\n",
    df$short_name, " | ", df$level_descriptor,
    "\n",
    horizon, " | ", units, " | ", members
  )
}

format_day_value <- function(hours) {
  days <- as.numeric(hours) / 24
  if (is.na(days)) return("NA")
  if (abs(days - round(days)) < 1e-8) return(sprintf("%d", as.integer(round(days))))
  if (days < 1) return(sprintf("%.2f", days))
  if (days < 10) return(sprintf("%.1f", days))
  sprintf("%.0f", days)
}

format_day_range <- function(min_hours, max_hours) {
  paste0(format_day_value(min_hours), "-", format_day_value(max_hours), " d")
}

series_label_from_fields <- function(source, product_family, short_name, level_descriptor, lead_hours_min, lead_hours_max) {
  source_type <- source_type_label(source, product_family)
  variable_label <- dplyr::case_when(
    short_name == "SOILW" ~ paste("SOILW", level_descriptor),
    short_name == "SOIL_M" ~ paste("SOIL_M", level_descriptor),
    short_name == "SOILSAT_TOP" ~ "SOILSAT_TOP",
    short_name == "APCP" ~ "APCP surface",
    short_name == "RAINRATE" ~ "RAINRATE forcing",
    TRUE ~ paste(short_name, level_descriptor)
  )
  paste(
    source_type,
    paste0(variable_label, " | ", format_day_range(lead_hours_min, lead_hours_max)),
    sep = "\n"
  )
}

augment_catalog <- function(catalog_df, mode) {
  if (nrow(catalog_df) == 0) {
    return(
      catalog_df %>%
        mutate(
          source_type = character(),
          series_key = character(),
          series_label = character(),
          source_order = integer(),
          variable_order = integer(),
          layer_order = double(),
          series_order = integer()
        )
    )
  }

  catalog_df %>%
    mutate(
      source_type = mapply(source_type_label, source, product_family, USE.NAMES = FALSE),
      series_key = paste(source, product_family, short_name, level_descriptor, sep = "||"),
      series_label = mapply(
        series_label_from_fields,
        source,
        product_family,
        short_name,
        level_descriptor,
        lead_hours_min,
        lead_hours_max,
        USE.NAMES = FALSE
      ),
      source_order = dplyr::case_when(
        source == "GEFS" ~ 1L,
        product_family == "short_range_land" ~ 2L,
        product_family == "short_range_forcing" ~ 2L,
        product_family == "medium_range_land" & short_name == "SOILSAT_TOP" ~ 3L,
        product_family == "medium_range_forcing" ~ 3L,
        product_family == "medium_range_land" & short_name == "SOIL_M" ~ 4L,
        product_family == "long_range_land" ~ 5L,
        TRUE ~ 9L
      ),
      variable_order = dplyr::case_when(
        mode == "soil" & short_name == "SOILW" ~ 1L,
        mode == "soil" & short_name == "SOILSAT_TOP" ~ 2L,
        mode == "soil" & short_name == "SOIL_M" ~ 3L,
        mode == "precip" & short_name == "APCP" ~ 1L,
        mode == "precip" & short_name == "RAINRATE" ~ 2L,
        TRUE ~ 9L
      ),
      layer_order = suppressWarnings(as.numeric(layer_index)),
      layer_order = ifelse(is.na(layer_order), 0, layer_order)
    ) %>%
    arrange(source_order, variable_order, layer_order, level_descriptor) %>%
    mutate(series_order = dplyr::dense_rank(series_key))
}

read_members_long <- function(catalog_row) {
  wide <- readr::read_csv(catalog_row$file_path, show_col_types = FALSE)
  member_cols <- grep("^member_", names(wide), value = TRUE)
  if (length(member_cols) == 0) {
    stop(sprintf("No member_* columns found in %s", catalog_row$file_path), call. = FALSE)
  }
  long <- wide %>%
    tidyr::pivot_longer(
      cols = all_of(member_cols),
      names_to = "member",
      values_to = "value"
    ) %>%
    mutate(
      source = catalog_row$source,
      product_family = catalog_row$product_family,
      short_name = catalog_row$short_name,
      level_descriptor = catalog_row$level_descriptor,
      layer_index = catalog_row$layer_index,
      units = catalog_row$units %||% "",
      source_type = catalog_row$source_type,
      series_key = catalog_row$series_key,
      series_label = catalog_row$series_label,
      series_order = catalog_row$series_order,
      target_time_utc = as.POSIXct(target_time_utc, tz = "UTC"),
      lead_hours = as.numeric(lead_hours),
      lead_days = lead_hours / 24
    )
  long
}

build_long_data <- function(catalog_df, mode) {
  if (nrow(catalog_df) == 0) {
    return(list(long = tibble(), catalog = tibble(), series_levels = character()))
  }

  catalog_aug <- augment_catalog(catalog_df, mode = mode)
  long_df <- bind_rows(lapply(seq_len(nrow(catalog_aug)), function(i) read_members_long(catalog_aug[i, , drop = FALSE])))
  long_df <- long_df %>% filter(is.finite(value))

  series_levels <- catalog_aug %>%
    arrange(series_order) %>%
    distinct(series_label) %>%
    pull(series_label)

  list(
    long = long_df,
    catalog = catalog_aug,
    series_levels = series_levels
  )
}

normalize_long_df <- function(long_df) {
  if (nrow(long_df) == 0) return(long_df)
  scaling <- long_df %>%
    group_by(series_key) %>%
    summarise(
      q05 = quantile(value, probs = 0.05, na.rm = TRUE, type = 7),
      q95 = quantile(value, probs = 0.95, na.rm = TRUE, type = 7),
      .groups = "drop"
    )

  long_df %>%
    left_join(scaling, by = "series_key") %>%
    mutate(
      value_norm = dplyr::case_when(
        is.finite(q05) & is.finite(q95) & (q95 > q05) ~ pmin(pmax((value - q05) / (q95 - q05), 0), 1),
        TRUE ~ 0.5
      )
    )
}

build_plot_data <- function(catalog_df, mode) {
  if (nrow(catalog_df) == 0) {
    return(list(long = tibble(), summary = tibble(), endpoints = tibble(), catalog = tibble(), series_levels = character()))
  }

  catalog_aug <- augment_catalog(catalog_df, mode = mode)
  long_df <- bind_rows(lapply(seq_len(nrow(catalog_aug)), function(i) read_members_long(catalog_aug[i, , drop = FALSE])))
  long_df <- long_df %>%
    filter(is.finite(value)) %>%
    normalize_long_df()

  summary_df <- long_df %>%
    group_by(series_key, series_label, source_type, series_order, lead_days) %>%
    summarise(
      q10 = quantile(value_norm, probs = 0.10, na.rm = TRUE, type = 7),
      mean = mean(value_norm, na.rm = TRUE),
      median = median(value_norm, na.rm = TRUE),
      q90 = quantile(value_norm, probs = 0.90, na.rm = TRUE, type = 7),
      .groups = "drop"
    )

  endpoints_df <- summary_df %>%
    group_by(series_key) %>%
    filter(lead_days == max(lead_days, na.rm = TRUE)) %>%
    slice_tail(n = 1) %>%
    ungroup()

  series_levels <- catalog_aug %>%
    arrange(series_order) %>%
    distinct(series_label) %>%
    pull(series_label)

  list(
    long = long_df,
    summary = summary_df,
    endpoints = endpoints_df,
    catalog = catalog_aug,
    series_levels = series_levels
  )
}

estimate_nwm_top_porosity <- function(nwm_catalog_df) {
  ref_catalog <- nwm_catalog_df %>%
    filter(product_family == "medium_range_land") %>%
    filter(
      short_name == "SOILSAT_TOP" |
        (short_name == "SOIL_M" & suppressWarnings(as.numeric(layer_index)) %in% c(0, 1))
    )

  ref_long <- build_long_data(ref_catalog, mode = "soil")$long
  if (nrow(ref_long) == 0) {
    stop("Cannot estimate NWM top-layer porosity: medium-range SOILSAT_TOP/SOIL_M reference rows missing.", call. = FALSE)
  }

  key_cols <- c("init_date", "cycle_hour", "lead_hours", "member")
  soil_sat <- ref_long %>%
    filter(short_name == "SOILSAT_TOP") %>%
    select(all_of(key_cols), soil_sat = value)
  soil_m0 <- ref_long %>%
    filter(short_name == "SOIL_M", suppressWarnings(as.numeric(layer_index)) == 0) %>%
    select(all_of(key_cols), soil_m0 = value)
  soil_m1 <- ref_long %>%
    filter(short_name == "SOIL_M", suppressWarnings(as.numeric(layer_index)) == 1) %>%
    select(all_of(key_cols), soil_m1 = value)

  ratio_df <- soil_sat %>%
    inner_join(soil_m0, by = key_cols) %>%
    inner_join(soil_m1, by = key_cols) %>%
    mutate(
      top_two_vwc = ((0.1 * soil_m0) + (0.3 * soil_m1)) / 0.4,
      porosity_est = top_two_vwc / soil_sat
    ) %>%
    filter(is.finite(porosity_est), soil_sat > 0.05)

  if (nrow(ratio_df) == 0) {
    stop("Cannot estimate NWM top-layer porosity: no valid SOILSAT_TOP/SOIL_M overlap rows.", call. = FALSE)
  }

  porosity <- median(ratio_df$porosity_est, na.rm = TRUE)
  if (!is.finite(porosity) || porosity <= 0 || porosity > 1) {
    stop(sprintf("Estimated NWM porosity is not physically plausible: %s", porosity), call. = FALSE)
  }

  list(
    porosity = porosity,
    sample_count = nrow(ratio_df),
    q10 = quantile(ratio_df$porosity_est, probs = 0.10, na.rm = TRUE, type = 7),
    q90 = quantile(ratio_df$porosity_est, probs = 0.90, na.rm = TRUE, type = 7)
  )
}

build_harmonized_covariate <- function(path, cutoff_date, max_day, series_name, value_candidates) {
  cutoff <- as.Date(cutoff_date)
  end_date <- cutoff + ceiling(max_day)
  raw_df <- read_covariate_series(path, value_candidates = value_candidates, series_name = series_name)
  out <- raw_df %>%
    filter(time > cutoff, time <= end_date) %>%
    mutate(
      day_index = as.numeric(time - cutoff),
      series_name = series_name
    ) %>%
    filter(day_index >= 1)

  if (nrow(out) == 0) {
    stop(
      sprintf("No post-cutoff covariate rows found for %s after %s in %s", series_name, cutoff_date, path),
      call. = FALSE
    )
  }
  out
}

build_harmonized_precip_data <- function(catalog_df, cutoff_date, prism_csv = NULL) {
  raw_data <- build_long_data(catalog_df, mode = "precip")
  if (nrow(raw_data$long) == 0) {
    return(list(
      daily_member = tibble(),
      summary = tibble(),
      endpoints = tibble(),
      overlay = tibble(),
      catalog = tibble(),
      series_levels = character()
    ))
  }

  daily_member <- raw_data$long %>%
    mutate(
      day_index = ceiling(lead_hours / 24),
      value_plot = dplyr::case_when(
        source == "GEFS" & short_name == "APCP" ~ value,
        source == "NWM" & short_name == "RAINRATE" ~ value * 3600,
        TRUE ~ NA_real_
      )
    ) %>%
    filter(day_index >= 1, is.finite(value_plot)) %>%
    group_by(series_key, series_label, source_type, series_order, member, day_index) %>%
    summarise(value_plot = sum(value_plot, na.rm = TRUE), .groups = "drop")

  summary_df <- daily_member %>%
    group_by(series_key, series_label, source_type, series_order, day_index) %>%
    summarise(
      member_count = n_distinct(member),
      q05 = quantile(value_plot, probs = 0.05, na.rm = TRUE, type = 7),
      mean = mean(value_plot, na.rm = TRUE),
      median = median(value_plot, na.rm = TRUE),
      q95 = quantile(value_plot, probs = 0.95, na.rm = TRUE, type = 7),
      .groups = "drop"
    )

  endpoints_df <- summary_df %>%
    group_by(series_key) %>%
    filter(day_index == max(day_index, na.rm = TRUE)) %>%
    slice_tail(n = 1) %>%
    ungroup()

  overlay_df <- tibble()
  if (!is.null(prism_csv)) {
    overlay_df <- build_harmonized_covariate(
      path = prism_csv,
      cutoff_date = cutoff_date,
      max_day = max(summary_df$day_index, na.rm = TRUE),
      series_name = "PRISM retrospective precipitation",
      value_candidates = c("PRCP_mm", "ppt")
    )
  }

  list(
    daily_member = daily_member,
    summary = summary_df,
    endpoints = endpoints_df,
    overlay = overlay_df,
    catalog = raw_data$catalog,
    series_levels = raw_data$series_levels
  )
}

build_harmonized_soil_data <- function(catalog_df, nwm_catalog_df, cutoff_date, era5_soil_csv = NULL) {
  raw_data <- build_long_data(catalog_df, mode = "soil")
  if (nrow(raw_data$long) == 0) {
    return(list(
      daily_member = tibble(),
      summary = tibble(),
      endpoints = tibble(),
      overlay = tibble(),
      catalog = tibble(),
      series_levels = character(),
      porosity_info = NULL
    ))
  }

  porosity_info <- estimate_nwm_top_porosity(nwm_catalog_df)
  catalog_plot <- raw_data$catalog %>%
    mutate(
      series_label = ifelse(
        short_name == "SOILSAT_TOP",
        sub("SOILSAT_TOP", "SOILSAT_TOP -> est. VWC", series_label, fixed = TRUE),
        series_label
      )
    )

  daily_member <- raw_data$long %>%
    mutate(
      day_index = ceiling(lead_hours / 24),
      series_label = ifelse(
        short_name == "SOILSAT_TOP",
        sub("SOILSAT_TOP", "SOILSAT_TOP -> est. VWC", series_label, fixed = TRUE),
        series_label
      ),
      value_plot = dplyr::case_when(
        source == "GEFS" & short_name == "SOILW" ~ value,
        source == "NWM" & short_name == "SOIL_M" ~ value,
        source == "NWM" & short_name == "SOILSAT_TOP" ~ value * porosity_info$porosity,
        TRUE ~ NA_real_
      )
    ) %>%
    filter(day_index >= 1, is.finite(value_plot)) %>%
    group_by(series_key, series_label, source_type, series_order, member, day_index) %>%
    summarise(value_plot = mean(value_plot, na.rm = TRUE), .groups = "drop")

  summary_df <- daily_member %>%
    group_by(series_key, series_label, source_type, series_order, day_index) %>%
    summarise(
      member_count = n_distinct(member),
      mean = mean(value_plot, na.rm = TRUE),
      .groups = "drop"
    )

  endpoints_df <- summary_df %>%
    group_by(series_key) %>%
    filter(day_index == max(day_index, na.rm = TRUE)) %>%
    slice_tail(n = 1) %>%
    ungroup()

  overlay_df <- tibble()
  if (!is.null(era5_soil_csv)) {
    overlay_df <- build_harmonized_covariate(
      path = era5_soil_csv,
      cutoff_date = cutoff_date,
      max_day = max(summary_df$day_index, na.rm = TRUE),
      series_name = "ERA5 retrospective soil moisture",
      value_candidates = c("Daily_Avg_Soil_Moisture", "soil", "average_soil_moisture")
    )
  }

  list(
    daily_member = daily_member,
    summary = summary_df,
    endpoints = endpoints_df,
    overlay = overlay_df,
    catalog = catalog_plot,
    series_levels = catalog_plot %>% arrange(series_order) %>% distinct(series_label) %>% pull(series_label),
    porosity_info = porosity_info
  )
}

apply_soil_bias_match <- function(plot_data) {
  if (nrow(plot_data$summary) == 0) {
    stop("No soil rows available for bias matching.", call. = FALSE)
  }
  if (nrow(plot_data$overlay) == 0) {
    stop("Bias-matched soil plotting requires an overlay retrospective series.", call. = FALSE)
  }

  ref_day <- min(plot_data$overlay$day_index, na.rm = TRUE)
  ref_value <- plot_data$overlay %>%
    filter(day_index == ref_day) %>%
    slice(1) %>%
    pull(value)

  offsets <- plot_data$summary %>%
    group_by(series_key, series_label, source_type, series_order) %>%
    filter(day_index == min(day_index, na.rm = TRUE)) %>%
    slice(1) %>%
    ungroup() %>%
    transmute(
      series_key,
      series_label,
      source_type,
      series_order,
      first_forecast_day = day_index,
      first_forecast_value = mean,
      bias_shift = ref_value - mean
    )

  summary_adj <- plot_data$summary %>%
    left_join(offsets %>% select(series_key, first_forecast_day, first_forecast_value, bias_shift), by = "series_key") %>%
    mutate(mean = mean + bias_shift)

  endpoints_adj <- summary_adj %>%
    group_by(series_key) %>%
    filter(day_index == max(day_index, na.rm = TRUE)) %>%
    slice_tail(n = 1) %>%
    ungroup()

  plot_data$summary <- summary_adj
  plot_data$endpoints <- endpoints_adj
  plot_data$bias_reference_day <- ref_day
  plot_data$bias_reference_value <- ref_value
  plot_data$bias_offsets <- offsets
  plot_data
}

plot_harmonized_means <- function(
  plot_data,
  title,
  subtitle,
  caption,
  out_png,
  out_pdf,
  y_label
) {
  if (nrow(plot_data$summary) == 0) {
    stop("No rows available for harmonized plot.", call. = FALSE)
  }

  series_levels <- plot_data$series_levels
  series_palette <- build_series_palette(plot_data$catalog, series_levels)
  plot_data$summary$series_label <- factor(plot_data$summary$series_label, levels = series_levels)
  plot_data$endpoints$series_label <- factor(plot_data$endpoints$series_label, levels = series_levels)

  max_day <- max(
    c(
      plot_data$summary$day_index,
      if (nrow(plot_data$overlay) > 0) plot_data$overlay$day_index else numeric()
    ),
    na.rm = TRUE
  )
  break_by <- dplyr::case_when(
    max_day <= 10 ~ 1,
    max_day <= 20 ~ 2,
    TRUE ~ 5
  )
  x_breaks <- seq(1, ceiling(max_day / break_by) * break_by, by = break_by)
  y_max <- max(
    c(
      plot_data$summary$mean,
      if (nrow(plot_data$overlay) > 0) plot_data$overlay$value else numeric()
    ),
    na.rm = TRUE
  )
  y_accuracy <- dplyr::case_when(
    y_max <= 1 ~ 0.01,
    y_max <= 10 ~ 0.1,
    TRUE ~ 1
  )

  p <- ggplot() +
    geom_line(
      data = plot_data$summary,
      aes(x = day_index, y = mean, color = series_label, group = series_key),
      linewidth = 1.35,
      lineend = "round"
    ) +
    geom_point(
      data = plot_data$endpoints,
      aes(x = day_index, y = mean, color = series_label),
      size = 2.0,
      stroke = 0,
      show.legend = FALSE
    )

  if (nrow(plot_data$overlay) > 0) {
    overlay_endpoint <- plot_data$overlay %>%
      filter(day_index == max(day_index, na.rm = TRUE)) %>%
      slice_tail(n = 1)

    p <- p +
      geom_line(
        data = plot_data$overlay,
        aes(x = day_index, y = value),
        inherit.aes = FALSE,
        color = "#FFFDF8",
        linewidth = 2.8,
        lineend = "round",
        show.legend = FALSE
      ) +
      geom_line(
        data = plot_data$overlay,
        aes(x = day_index, y = value),
        inherit.aes = FALSE,
        color = "#1B1713",
        linewidth = 1.35,
        linetype = "22",
        lineend = "round",
        show.legend = FALSE
      ) +
      geom_point(
        data = overlay_endpoint,
        aes(x = day_index, y = value),
        inherit.aes = FALSE,
        color = "#1B1713",
        fill = "#1B1713",
        size = 2.2,
        stroke = 0,
        show.legend = FALSE
      )
  }

  p <- p +
    scale_color_manual(values = series_palette, breaks = series_levels, drop = FALSE) +
    scale_x_continuous(
      breaks = x_breaks,
      labels = label_number(accuracy = 1, suffix = " d"),
      expand = expansion(mult = c(0.01, 0.02))
    ) +
    scale_y_continuous(
      labels = label_number(accuracy = y_accuracy),
      expand = expansion(mult = c(0.02, 0.05))
    ) +
    labs(
      title = title,
      subtitle = subtitle,
      x = "Forecast day after initialization",
      y = y_label,
      color = "Forecast family",
      caption = caption
    ) +
    custom_theme() +
    theme(
      legend.position = "right",
      legend.box = "vertical",
      legend.key.height = unit(16, "pt"),
      legend.text = element_text(size = 9.2)
    ) +
    guides(
      color = guide_legend(override.aes = list(alpha = 1, linewidth = 1.5))
    )

  ggsave(out_png, p, width = 16, height = 10, dpi = 320, bg = "#F6F3EC")
  ggsave(out_pdf, p, width = 16, height = 10, bg = "#F6F3EC")
  invisible(p)
}

plot_harmonized_precip_quantiles <- function(
  plot_data,
  title,
  subtitle,
  caption,
  out_png,
  out_pdf,
  y_label
) {
  if (nrow(plot_data$summary) == 0) {
    stop("No rows available for precipitation quantile plot.", call. = FALSE)
  }

  series_levels <- plot_data$series_levels
  series_palette <- build_series_palette(plot_data$catalog, series_levels)
  plot_data$summary$series_label <- factor(plot_data$summary$series_label, levels = series_levels)
  plot_data$endpoints$series_label <- factor(plot_data$endpoints$series_label, levels = series_levels)
  ensemble_df <- plot_data$summary %>%
    filter(member_count > 1) %>%
    mutate(series_label = factor(series_label, levels = series_levels))

  max_day <- max(
    c(
      plot_data$summary$day_index,
      if (nrow(plot_data$overlay) > 0) plot_data$overlay$day_index else numeric()
    ),
    na.rm = TRUE
  )
  break_by <- dplyr::case_when(
    max_day <= 10 ~ 1,
    max_day <= 20 ~ 2,
    TRUE ~ 5
  )
  x_breaks <- seq(1, ceiling(max_day / break_by) * break_by, by = break_by)
  y_max <- max(
    c(
      plot_data$summary$q95,
      plot_data$summary$mean,
      if (nrow(plot_data$overlay) > 0) plot_data$overlay$value else numeric()
    ),
    na.rm = TRUE
  )
  y_accuracy <- dplyr::case_when(
    y_max <= 1 ~ 0.01,
    y_max <= 10 ~ 0.1,
    TRUE ~ 1
  )

  p <- ggplot() +
    geom_ribbon(
      data = ensemble_df,
      aes(x = day_index, ymin = q05, ymax = q95, fill = series_label, group = series_key),
      alpha = 0.12,
      color = NA,
      show.legend = FALSE
    ) +
    geom_line(
      data = ensemble_df,
      aes(x = day_index, y = q05, color = series_label, group = series_key, linetype = "Q05 / Q95"),
      linewidth = 0.55,
      alpha = 0.75,
      lineend = "round"
    ) +
    geom_line(
      data = ensemble_df,
      aes(x = day_index, y = q95, color = series_label, group = series_key, linetype = "Q05 / Q95"),
      linewidth = 0.55,
      alpha = 0.75,
      lineend = "round"
    ) +
    geom_line(
      data = ensemble_df,
      aes(x = day_index, y = median, color = series_label, group = series_key, linetype = "Median"),
      linewidth = 0.95,
      alpha = 0.95,
      lineend = "round"
    ) +
    geom_line(
      data = plot_data$summary,
      aes(x = day_index, y = mean, color = series_label, group = series_key, linetype = "Mean"),
      linewidth = 1.35,
      lineend = "round"
    ) +
    geom_point(
      data = plot_data$endpoints,
      aes(x = day_index, y = mean, color = series_label),
      size = 2.0,
      stroke = 0,
      show.legend = FALSE
    )

  if (nrow(plot_data$overlay) > 0) {
    overlay_endpoint <- plot_data$overlay %>%
      filter(day_index == max(day_index, na.rm = TRUE)) %>%
      slice_tail(n = 1)

    p <- p +
      geom_line(
        data = plot_data$overlay,
        aes(x = day_index, y = value),
        inherit.aes = FALSE,
        color = "#FFFDF8",
        linewidth = 2.8,
        lineend = "round",
        show.legend = FALSE
      ) +
      geom_line(
        data = plot_data$overlay,
        aes(x = day_index, y = value),
        inherit.aes = FALSE,
        color = "#1B1713",
        linewidth = 1.35,
        linetype = "22",
        lineend = "round",
        show.legend = FALSE
      ) +
      geom_point(
        data = overlay_endpoint,
        aes(x = day_index, y = value),
        inherit.aes = FALSE,
        color = "#1B1713",
        fill = "#1B1713",
        size = 2.2,
        stroke = 0,
        show.legend = FALSE
      )
  }

  p <- p +
    scale_color_manual(values = series_palette, breaks = series_levels, drop = FALSE) +
    scale_fill_manual(values = series_palette, breaks = series_levels, drop = FALSE) +
    scale_linetype_manual(
      values = c(
        "Mean" = "solid",
        "Median" = "22",
        "Q05 / Q95" = "42"
      ),
      breaks = c("Mean", "Median", "Q05 / Q95")
    ) +
    scale_x_continuous(
      breaks = x_breaks,
      labels = label_number(accuracy = 1, suffix = " d"),
      expand = expansion(mult = c(0.01, 0.02))
    ) +
    scale_y_continuous(
      labels = label_number(accuracy = y_accuracy),
      expand = expansion(mult = c(0.02, 0.05))
    ) +
    labs(
      title = title,
      subtitle = subtitle,
      x = "Forecast day after initialization",
      y = y_label,
      color = "Forecast family",
      linetype = "Statistic",
      caption = caption
    ) +
    custom_theme() +
    theme(
      legend.position = "right",
      legend.box = "vertical",
      legend.key.height = unit(16, "pt"),
      legend.text = element_text(size = 9.2)
    ) +
    guides(
      color = guide_legend(order = 1, override.aes = list(alpha = 1, linewidth = 1.5, linetype = "solid")),
      linetype = guide_legend(order = 2, override.aes = list(color = "#3A332B", linewidth = c(1.5, 1.1, 0.8)))
    )

  ggsave(out_png, p, width = 16, height = 10, dpi = 320, bg = "#F6F3EC")
  ggsave(out_pdf, p, width = 16, height = 10, bg = "#F6F3EC")
  invisible(p)
}

series_shades <- function(base_color, n) {
  if (n <= 0) return(character())
  if (n == 1) return(base_color)
  ramp <- grDevices::colorRampPalette(c("#E8DFCF", base_color))(n + 2)
  rev(ramp[seq_len(n) + 1])
}

build_series_palette <- function(catalog_aug, series_levels) {
  if (nrow(catalog_aug) == 0) return(setNames(character(), character()))
  legend_df <- catalog_aug %>%
    arrange(series_order) %>%
    distinct(series_label, source_type, series_order)

  palette <- setNames(rep("#4A4237", length(series_levels)), series_levels)
  family_frames <- split(legend_df, legend_df$source_type)
  for (family_name in names(family_frames)) {
    family_df <- family_frames[[family_name]] %>% arrange(series_order)
    base_color <- source_palette[[family_name]] %||% "#4A4237"
    family_colors <- series_shades(base_color, nrow(family_df))
    palette[family_df$series_label] <- family_colors
  }
  palette
}

plot_forecasts <- function(
  plot_data,
  title,
  subtitle,
  caption,
  out_png,
  out_pdf,
  plot_style = "overlap_all_families",
  overlay_df = NULL
) {
  if (nrow(plot_data$long) == 0) {
    stop("No rows available for plot.", call. = FALSE)
  }

  series_levels <- plot_data$series_levels
  series_palette <- build_series_palette(plot_data$catalog, series_levels)
  plot_data$long$series_label <- factor(plot_data$long$series_label, levels = series_levels)
  plot_data$summary$series_label <- factor(plot_data$summary$series_label, levels = series_levels)
  plot_data$endpoints$series_label <- factor(plot_data$endpoints$series_label, levels = series_levels)

  max_days <- max(plot_data$long$lead_days, na.rm = TRUE)
  break_by <- dplyr::case_when(
    max_days <= 3 ~ 0.25,
    max_days <= 10 ~ 1,
    max_days <= 20 ~ 2,
    TRUE ~ 5
  )
  break_accuracy <- if (break_by < 1) 0.25 else if (break_by < 2) 0.5 else 1
  x_breaks <- seq(0, ceiling(max_days / break_by) * break_by, by = break_by)

  p <- ggplot()
  if (identical(plot_style, "overlap_all_families")) {
    p <- p +
      geom_ribbon(
        data = plot_data$summary,
        aes(x = lead_days, ymin = q10, ymax = q90, fill = series_label, group = series_key),
        alpha = 0.07,
        color = NA,
        show.legend = FALSE
      ) +
      geom_line(
        data = plot_data$long,
        aes(x = lead_days, y = value_norm, group = interaction(series_key, member), color = series_label),
        linewidth = 0.30,
        alpha = 0.08,
        show.legend = FALSE
      ) +
      geom_line(
        data = plot_data$summary,
        aes(x = lead_days, y = median, color = series_label, group = series_key),
        linewidth = 1.10,
        lineend = "round"
      ) +
      geom_point(
        data = plot_data$endpoints,
        aes(x = lead_days, y = median, color = series_label),
        size = 1.85,
        stroke = 0,
        show.legend = FALSE
      )
  } else if (identical(plot_style, "mean_only")) {
    p <- p +
      geom_line(
        data = plot_data$summary,
        aes(x = lead_days, y = mean, color = series_label, group = series_key),
        linewidth = 1.35,
        lineend = "round"
      ) +
      geom_point(
        data = plot_data$endpoints,
        aes(x = lead_days, y = mean, color = series_label),
        size = 2.0,
        stroke = 0,
        show.legend = FALSE
      )
  } else {
    stop(sprintf("Unsupported plot style: %s", plot_style), call. = FALSE)
  }

  if (!is.null(overlay_df) && nrow(overlay_df) > 0) {
    overlay_endpoint <- overlay_df %>%
      filter(lead_days == max(lead_days, na.rm = TRUE)) %>%
      slice_tail(n = 1)

    p <- p +
      geom_line(
        data = overlay_df,
        aes(x = lead_days, y = value_norm),
        inherit.aes = FALSE,
        color = "#FFFDF8",
        linewidth = 2.8,
        lineend = "round",
        show.legend = FALSE
      ) +
      geom_line(
        data = overlay_df,
        aes(x = lead_days, y = value_norm),
        inherit.aes = FALSE,
        color = "#1B1713",
        linewidth = 1.35,
        linetype = "22",
        lineend = "round",
        show.legend = FALSE
      ) +
      geom_point(
        data = overlay_endpoint,
        aes(x = lead_days, y = value_norm),
        inherit.aes = FALSE,
        color = "#1B1713",
        fill = "#1B1713",
        size = 2.2,
        stroke = 0,
        show.legend = FALSE
      )
  }

  p <- p +
    scale_color_manual(values = series_palette, breaks = series_levels, drop = FALSE) +
    scale_x_continuous(
      breaks = x_breaks,
      labels = label_number(accuracy = break_accuracy, suffix = " d"),
      expand = expansion(mult = c(0.01, 0.02))
    ) +
    scale_y_continuous(
      limits = c(0, 1),
      breaks = seq(0, 1, by = 0.2),
      labels = label_number(accuracy = 0.1)
    ) +
    labs(
      title = title,
      subtitle = subtitle,
      x = "Forecast lead from initialization (days)",
      y = "Normalized value within each source / product / layer (0-1)",
      color = "Forecast family",
      caption = caption
    ) +
    custom_theme() +
    theme(
      legend.position = "right",
      legend.box = "vertical",
      legend.key.height = unit(16, "pt"),
      legend.text = element_text(size = 9.2)
    )

  if (identical(plot_style, "overlap_all_families")) {
    p <- p +
      scale_fill_manual(values = series_palette, breaks = series_levels, drop = FALSE) +
      labs(fill = "Forecast family") +
      guides(
        color = guide_legend(override.aes = list(alpha = 1, linewidth = 1.5)),
        fill = "none"
      )
  } else {
    p <- p +
      guides(
        color = guide_legend(override.aes = list(alpha = 1, linewidth = 1.5))
      )
  }

  ggsave(out_png, p, width = 16, height = 10, dpi = 320, bg = "#F6F3EC")
  ggsave(out_pdf, p, width = 16, height = 10, bg = "#F6F3EC")
  invisible(p)
}

main <- function() {
  args <- parse_args(commandArgs(trailingOnly = TRUE))
  run_dir <- as_abs_path(args$`manifest-run-dir` %||% "repro/gefs_nwm_forecast_runs/gefs_nwm_forecast_manifest_20260307T023425Z")
  site_cfg <- as_abs_path(args$`site-config` %||% "config/forecats_pipeline.template.yaml")
  site <- read_site(site_cfg)
  catalogs <- read_catalogs(run_dir, site$usgs_site)
  plot_style <- as.character(args$`plot-style` %||% "overlap_all_families")
  overlay_covariates <- isTRUE(args$`overlay-covariates`)
  prism_csv <- as_abs_path(args$`prism-csv` %||% "prism_precipitation_santa_cruz_1987_2023.csv")
  era5_soil_csv <- as_abs_path(args$`era5-soil-csv` %||% "soil_moisture_data/soil_moisture_big_trees_daily_avg_1987_2023.csv")

  cutoff_date <- as.character(args$`cutoff-date` %||% max(c(catalogs$gefs$init_date, catalogs$nwm$init_date), na.rm = TRUE))
  out_root <- file.path(run_dir, "plots", paste0("cutoff_date=", cutoff_date))
  dir.create(out_root, recursive = TRUE, showWarnings = FALSE)

  gefs_cutoff <- catalogs$gefs %>% filter(init_date == cutoff_date)
  nwm_cutoff <- catalogs$nwm %>% filter(init_date == cutoff_date)
  if (nrow(gefs_cutoff) == 0 && nrow(nwm_cutoff) == 0) {
    stop(sprintf("No handoff catalog rows found for cutoff/init date %s", cutoff_date), call. = FALSE)
  }

  soil_catalog <- bind_rows(
    gefs_cutoff %>% filter(short_name == "SOILW"),
    nwm_cutoff %>% filter(short_name %in% c("SOILSAT_TOP", "SOIL_M"))
  )
  precip_catalog <- bind_rows(
    gefs_cutoff %>% filter(short_name == "APCP"),
    nwm_cutoff %>% filter(short_name == "RAINRATE")
  )

  use_same_units <- plot_style %in% c("mean_only_same_units", "mean_only_same_units_bias_quantiles")
  if (identical(plot_style, "mean_only_same_units_bias_quantiles") && !overlay_covariates) {
    stop("plot-style mean_only_same_units_bias_quantiles requires --overlay-covariates so the soil bias match can anchor to the retrospective series.", call. = FALSE)
  }
  if (use_same_units) {
    soil_data <- build_harmonized_soil_data(
      soil_catalog,
      nwm_catalog_df = catalogs$nwm,
      cutoff_date = cutoff_date,
      era5_soil_csv = if (overlay_covariates) era5_soil_csv else NULL
    )
    precip_data <- build_harmonized_precip_data(
      precip_catalog,
      cutoff_date = cutoff_date,
      prism_csv = if (overlay_covariates) prism_csv else NULL
    )
    soil_overlay <- soil_data$overlay
    precip_overlay <- precip_data$overlay
    if (identical(plot_style, "mean_only_same_units_bias_quantiles")) {
      soil_data <- apply_soil_bias_match(soil_data)
    }
  } else {
    soil_data <- build_plot_data(soil_catalog, mode = "soil")
    precip_data <- build_plot_data(precip_catalog, mode = "precip")

    soil_overlay <- NULL
    precip_overlay <- NULL
    if (overlay_covariates) {
      soil_overlay <- build_covariate_overlay(
        path = era5_soil_csv,
        cutoff_date = cutoff_date,
        max_days = max(soil_data$long$lead_days, na.rm = TRUE),
        series_name = "ERA5 retrospective soil covariate",
        value_candidates = c("Daily_Avg_Soil_Moisture", "soil", "average_soil_moisture")
      )
      precip_overlay <- build_covariate_overlay(
        path = prism_csv,
        cutoff_date = cutoff_date,
        max_days = max(precip_data$long$lead_days, na.rm = TRUE),
        series_name = "PRISM retrospective precipitation covariate",
        value_candidates = c("PRCP_mm", "ppt")
      )
    }
  }

  site_label <- sprintf("USGS %s | Big Trees / San Lorenzo (%.4f, %.4f)", site$usgs_site, site$lat, site$lon)
  if (use_same_units) {
    subtitle_lines <- c(
      sprintf("Init / cutoff date: %s", cutoff_date),
      site_label,
      "All forecast families are shown in harmonized physical units on a common forecast-day axis.",
      "Each colored line is the ensemble mean for that forecast family; deterministic products appear as their single available trajectory."
    )
    if (overlay_covariates) {
      subtitle_lines <- c(
        subtitle_lines,
        "Black dashed line is the realized retrospective covariate used in the model workflow, starting on day 1 after the cutoff."
      )
    }
    if (identical(plot_style, "mean_only_same_units_bias_quantiles")) {
      subtitle_lines <- c(
        subtitle_lines,
        "Soil lines are additively bias-matched so each forecast family starts at the first retrospective soil value.",
        "Precipitation keeps the same-unit mean trajectories and adds the 5th percentile, median, and 95th percentile for any ensemble product with more than one member."
      )
    }
    subtitle_lines <- c(
      subtitle_lines,
      sprintf(
        "NWM SOILSAT_TOP was converted from saturation fraction to estimated volumetric water content using a site-level porosity estimate of %.3f (10-90%% range %.3f to %.3f) derived from medium-range SOIL_M layers 0-1.",
        soil_data$porosity_info$porosity,
        soil_data$porosity_info$q10,
        soil_data$porosity_info$q90
      )
    )
    base_subtitle <- paste(subtitle_lines, collapse = "\n")

    soil_caption <- paste(
      "Soil series are plotted as daily mean volumetric soil moisture in m3/m3.",
      "GEFS SOILW is treated as volumetric water content, NWM SOIL_M is already volumetric water content, and NWM SOILSAT_TOP is converted to an estimated volumetric equivalent using the derived site porosity.",
      "Depths still differ by product: GEFS has 4 explicit layers, ERA5 covariate is the top soil layer, and NWM SOILSAT_TOP represents the top two NWM land layers combined.",
      if (identical(plot_style, "mean_only_same_units_bias_quantiles")) {
        sprintf(
          "Bias correction is an additive shift applied separately to each forecast family so its first plotted forecast day matches the first realized retrospective soil value on day %d.",
          soil_data$bias_reference_day
        )
      } else {
        NULL
      },
      if (overlay_covariates) {
        "Black dashed line is the ERA5 daily soil covariate used in the model workflow."
      } else {
        NULL
      },
      sep = "\n"
    )
    precip_caption <- paste(
      "Precipitation series are plotted as daily accumulated precipitation in mm/day.",
      "GEFS APCP interval accumulations were summed into forecast-day totals; NWM RAINRATE was converted from mm s^-1 to hourly mm and then summed to daily totals; PRISM is already daily precipitation in mm.",
      if (identical(plot_style, "mean_only_same_units_bias_quantiles")) {
        "Solid colored lines are the daily ensemble mean. For any ensemble precipitation product, the dashed colored line is the median and the lighter dotted colored bounds are the 5th and 95th percentiles. Deterministic precipitation products show only the mean."
      } else {
        NULL
      },
      "No long-range NWM forcing precipitation product was present in the confirmed public archive.",
      if (overlay_covariates) {
        "Black dashed line is the PRISM daily precipitation covariate used in the model workflow."
      } else {
        NULL
      },
      sep = "\n"
    )
  } else {
    subtitle_lines <- c(
      sprintf("Init / cutoff date: %s", cutoff_date),
      site_label,
      "All forecast families are overlaid on a common lead-time axis in days."
    )
    if (identical(plot_style, "overlap_all_families")) {
      subtitle_lines <- c(
        subtitle_lines,
        "Thin lines show individual members; bold lines and soft bands show the median and 10-90% spread."
      )
    } else if (identical(plot_style, "mean_only")) {
      subtitle_lines <- c(
        subtitle_lines,
        "Each line is the ensemble mean for that forecast family; deterministic products appear as their single available trajectory."
      )
    }
    if (overlay_covariates) {
      subtitle_lines <- c(
        subtitle_lines,
        "Black dashed line shows the realized retrospective covariate used in model inputs, starting the day after the cutoff."
      )
    }
    subtitle_lines <- c(
      subtitle_lines,
      "Because native units differ across sources and products, each family is normalized to its own robust 5th-95th percentile range before plotting."
    )
    base_subtitle <- paste(subtitle_lines, collapse = "\n")

    soil_caption <- paste(
      "Soil overlap includes all GEFS SOILW layers plus NWM SOILSAT_TOP and all medium-range SOIL_M layers.",
      "Horizon coverage in days: GEFS soil 0-35 d; NWM short-range soil 0.04-0.75 d; NWM medium-range soil 0.12-10 d; NWM long-range soil 1-30 d.",
      if (identical(plot_style, "overlap_all_families")) {
        "Where some NWM medium-range members end before the longest lead, summaries use the members available at that lead."
      } else {
        "For ensemble products, the plotted trajectory is the mean across all available members at each lead."
      },
      if (overlay_covariates) {
        "Black dashed line is the ERA5 daily soil covariate used in the model workflow, normalized over the realized post-cutoff window."
      } else {
        NULL
      },
      sep = "\n"
    )
    precip_caption <- paste(
      "Precipitation overlap includes GEFS APCP plus NWM RAINRATE from short- and medium-range forcing.",
      "Horizon coverage in days: GEFS APCP 0.12-35 d; NWM short-range forcing 0.04-0.75 d; NWM medium-range forcing 0.04-10 d.",
      "No long-range NWM forcing precipitation product was present in the confirmed public archive.",
      if (overlay_covariates) {
        "Black dashed line is the PRISM daily precipitation covariate used in the model workflow, normalized over the realized post-cutoff window."
      } else {
        NULL
      },
      sep = "\n"
    )
  }

  if (identical(plot_style, "overlap_all_families")) {
    soil_title <- "Overlapped Soil Forecast Families By Lead Time"
    precip_title <- "Overlapped Precipitation Forecast Families By Lead Time"
    soil_png <- file.path(out_root, "soil_forecasts.png")
    soil_pdf <- file.path(out_root, "soil_forecasts.pdf")
    precip_png <- file.path(out_root, "precip_forecasts.png")
    precip_pdf <- file.path(out_root, "precip_forecasts.pdf")
    summary_path <- file.path(out_root, "plot_summary.json")
  } else if (identical(plot_style, "mean_only")) {
    if (overlay_covariates) {
      soil_title <- "Mean Soil Forecast Families Vs ERA5 Soil Covariate"
      precip_title <- "Mean Precipitation Forecast Families Vs PRISM Precipitation"
      soil_png <- file.path(out_root, "soil_forecasts_mean_with_covariates.png")
      soil_pdf <- file.path(out_root, "soil_forecasts_mean_with_covariates.pdf")
      precip_png <- file.path(out_root, "precip_forecasts_mean_with_covariates.png")
      precip_pdf <- file.path(out_root, "precip_forecasts_mean_with_covariates.pdf")
      summary_path <- file.path(out_root, "plot_summary_mean_with_covariates.json")
    } else {
      soil_title <- "Mean Soil Forecast Families By Lead Time"
      precip_title <- "Mean Precipitation Forecast Families By Lead Time"
      soil_png <- file.path(out_root, "soil_forecasts_mean.png")
      soil_pdf <- file.path(out_root, "soil_forecasts_mean.pdf")
      precip_png <- file.path(out_root, "precip_forecasts_mean.png")
      precip_pdf <- file.path(out_root, "precip_forecasts_mean.pdf")
      summary_path <- file.path(out_root, "plot_summary_mean.json")
    }
  } else if (identical(plot_style, "mean_only_same_units")) {
    if (overlay_covariates) {
      soil_title <- "Mean Soil Forecast Families Vs ERA5 Soil Covariate In Same Units"
      precip_title <- "Mean Precipitation Forecast Families Vs PRISM In Same Units"
      soil_png <- file.path(out_root, "soil_forecasts_mean_same_units_with_covariates.png")
      soil_pdf <- file.path(out_root, "soil_forecasts_mean_same_units_with_covariates.pdf")
      precip_png <- file.path(out_root, "precip_forecasts_mean_same_units_with_covariates.png")
      precip_pdf <- file.path(out_root, "precip_forecasts_mean_same_units_with_covariates.pdf")
      summary_path <- file.path(out_root, "plot_summary_mean_same_units_with_covariates.json")
    } else {
      soil_title <- "Mean Soil Forecast Families In Same Units"
      precip_title <- "Mean Precipitation Forecast Families In Same Units"
      soil_png <- file.path(out_root, "soil_forecasts_mean_same_units.png")
      soil_pdf <- file.path(out_root, "soil_forecasts_mean_same_units.pdf")
      precip_png <- file.path(out_root, "precip_forecasts_mean_same_units.png")
      precip_pdf <- file.path(out_root, "precip_forecasts_mean_same_units.pdf")
      summary_path <- file.path(out_root, "plot_summary_mean_same_units.json")
    }
  } else if (identical(plot_style, "mean_only_same_units_bias_quantiles")) {
    soil_title <- "Bias-Matched Mean Soil Forecast Families Vs ERA5 Soil Covariate"
    precip_title <- "Mean And Ensemble Quantile Precipitation Vs PRISM In Same Units"
    if (overlay_covariates) {
      soil_png <- file.path(out_root, "soil_forecasts_mean_same_units_bias_matched_with_covariates.png")
      soil_pdf <- file.path(out_root, "soil_forecasts_mean_same_units_bias_matched_with_covariates.pdf")
      precip_png <- file.path(out_root, "precip_forecasts_mean_same_units_quantiles_with_covariates.png")
      precip_pdf <- file.path(out_root, "precip_forecasts_mean_same_units_quantiles_with_covariates.pdf")
      summary_path <- file.path(out_root, "plot_summary_mean_same_units_bias_quantiles_with_covariates.json")
    } else {
      soil_png <- file.path(out_root, "soil_forecasts_mean_same_units_bias_matched.png")
      soil_pdf <- file.path(out_root, "soil_forecasts_mean_same_units_bias_matched.pdf")
      precip_png <- file.path(out_root, "precip_forecasts_mean_same_units_quantiles.png")
      precip_pdf <- file.path(out_root, "precip_forecasts_mean_same_units_quantiles.pdf")
      summary_path <- file.path(out_root, "plot_summary_mean_same_units_bias_quantiles.json")
    }
  } else {
    stop(sprintf("Unsupported plot style: %s", plot_style), call. = FALSE)
  }

  if (use_same_units) {
    plot_harmonized_means(
      soil_data,
      title = soil_title,
      subtitle = base_subtitle,
      caption = soil_caption,
      out_png = soil_png,
      out_pdf = soil_pdf,
      y_label = "Daily mean soil moisture (m3/m3)"
    )
    if (identical(plot_style, "mean_only_same_units_bias_quantiles")) {
      plot_harmonized_precip_quantiles(
        precip_data,
        title = precip_title,
        subtitle = base_subtitle,
        caption = precip_caption,
        out_png = precip_png,
        out_pdf = precip_pdf,
        y_label = "Daily precipitation (mm)"
      )
    } else {
      plot_harmonized_means(
        precip_data,
        title = precip_title,
        subtitle = base_subtitle,
        caption = precip_caption,
        out_png = precip_png,
        out_pdf = precip_pdf,
        y_label = "Daily precipitation (mm)"
      )
    }
  } else {
    plot_forecasts(
      soil_data,
      title = soil_title,
      subtitle = base_subtitle,
      caption = soil_caption,
      out_png = soil_png,
      out_pdf = soil_pdf,
      plot_style = plot_style,
      overlay_df = soil_overlay
    )
    plot_forecasts(
      precip_data,
      title = precip_title,
      subtitle = base_subtitle,
      caption = precip_caption,
      out_png = precip_png,
      out_pdf = precip_pdf,
      plot_style = plot_style,
      overlay_df = precip_overlay
    )
  }

  summary <- list(
    run_dir = run_dir,
    cutoff_date = cutoff_date,
    site = site,
    plot_mode = plot_style,
    overlay_covariates = overlay_covariates,
    x_axis = if (use_same_units) "forecast_day_after_initialization" else "lead_days_from_initialization",
    normalization = if (use_same_units) "none; plotted in harmonized physical units" else "per-family robust 5th-95th percentile range clipped to [0, 1]",
    soil_plot_png = soil_png,
    soil_plot_pdf = soil_pdf,
    precip_plot_png = precip_png,
    precip_plot_pdf = precip_pdf,
    soil_families = length(soil_data$series_levels),
    precip_families = length(precip_data$series_levels),
    unit_harmonized = use_same_units,
    soil_units = if (use_same_units) "m3/m3" else NULL,
    precip_units = if (use_same_units) "mm per forecast day" else NULL,
    prism_csv = if (overlay_covariates) prism_csv else NULL,
    era5_soil_csv = if (overlay_covariates) era5_soil_csv else NULL,
    soil_covariate_points = if (overlay_covariates) nrow(soil_overlay) else NULL,
    precip_covariate_points = if (overlay_covariates) nrow(precip_overlay) else NULL,
    nwm_soilsat_top_porosity = if (use_same_units) soil_data$porosity_info$porosity else NULL,
    nwm_soilsat_top_porosity_q10 = if (use_same_units) soil_data$porosity_info$q10 else NULL,
    nwm_soilsat_top_porosity_q90 = if (use_same_units) soil_data$porosity_info$q90 else NULL,
    nwm_soilsat_top_porosity_samples = if (use_same_units) soil_data$porosity_info$sample_count else NULL,
    soil_bias_match_reference_day = if (identical(plot_style, "mean_only_same_units_bias_quantiles")) soil_data$bias_reference_day else NULL,
    soil_bias_match_reference_value = if (identical(plot_style, "mean_only_same_units_bias_quantiles")) soil_data$bias_reference_value else NULL,
    soil_bias_offsets = if (identical(plot_style, "mean_only_same_units_bias_quantiles")) {
      stats::setNames(as.list(soil_data$bias_offsets$bias_shift), soil_data$bias_offsets$series_label)
    } else {
      NULL
    },
    precip_quantiles_for_ensemble_only = if (identical(plot_style, "mean_only_same_units_bias_quantiles")) TRUE else NULL
  )
  writeLines(
    jsonlite::toJSON(summary, pretty = TRUE, auto_unbox = TRUE),
    con = summary_path
  )

  cat(sprintf("[OK] wrote %s\n", soil_png))
  cat(sprintf("[OK] wrote %s\n", precip_png))
}

main()
