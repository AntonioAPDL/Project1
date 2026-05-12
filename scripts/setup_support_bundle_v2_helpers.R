`%||%` <- function(x, y) if (is.null(x) || length(x) == 0L) y else x

suppressPackageStartupMessages({
  library(yaml)
  library(readr)
  library(dplyr)
  library(tidyr)
  library(ggplot2)
  library(patchwork)
  library(scales)
  library(tibble)
})

CFSToCMS_CONVERSION_FACTOR <- 0.028316846592

require_existing_path <- function(path, label) {
  path <- normalizePath(path, mustWork = FALSE)
  if (!file.exists(path)) {
    stop(sprintf("Missing %s: %s", label, path), call. = FALSE)
  }
  normalizePath(path, mustWork = TRUE)
}

safe_date <- function(x) {
  if (inherits(x, "Date")) return(x)
  suppressWarnings(as.Date(as.character(x)))
}

choose_date_col <- function(df, candidates = c("date", "Date", "time")) {
  hit <- candidates[candidates %in% names(df)]
  if (length(hit) == 0L) {
    stop(sprintf("Could not find a date column among: %s", paste(candidates, collapse = ", ")), call. = FALSE)
  }
  hit[[1L]]
}

choose_value_col <- function(df, candidates) {
  hit <- candidates[candidates %in% names(df)]
  if (length(hit) == 0L) {
    stop(sprintf("Could not find a value column among: %s", paste(candidates, collapse = ", ")), call. = FALSE)
  }
  hit[[1L]]
}

transform_flow <- function(x_cms, scale) {
  x <- suppressWarnings(as.numeric(x_cms))
  out <- rep(NA_real_, length(x))
  if (identical(scale, "raw_cms")) {
    return(x)
  }
  if (identical(scale, "log1p_cms")) {
    ok <- !is.na(x) & x > -1
    out[ok] <- log(x[ok] + 1)
    return(out)
  }
  if (identical(scale, "log_log1p_cms")) {
    stop("log_log1p_cms is not allowed in current support bundles; use log1p_cms.", call. = FALSE)
  }
  stop(sprintf("Unknown plot scale: %s", scale), call. = FALSE)
}

build_source_label_map <- function(meta, cutoff_date = NULL, selected_run_root = NULL) {
  label_map <- list()
  extras <- meta$config$inputs$retros$extra_sources %||% list()
  if (length(extras) > 0L) {
    for (row in extras) {
      sid <- as.character(row$source_id %||% "")
      slabel <- as.character(row$source_label %||% sid)
      if (nzchar(sid)) label_map[[sid]] <- slabel
    }
  }
  known_source_ids <- c(
    "nws_synth_retro_ens_mean",
    "nws_retro_v12",
    "nws_retro_v20",
    "nws_retro_v21",
    "nws_retro_v30",
    "nws_selected_window_retro",
    "glofas_hist_v21_htessel_cons",
    "glofas_hist_v31_lisflood_cons",
    "glofas_hist_v40_lisflood_cons",
    "glofas_legacy_reanalysis_v30",
    "glofas_synth_retro_ens_mean"
  )
  for (sid in known_source_ids) {
    resolved_label <- figure_default_retro_label(
      source_id = sid,
      meta = meta,
      cutoff_date = cutoff_date,
      selected_run_root = selected_run_root
    )
    label_map[[sid]] <- if (nzchar(as.character(resolved_label %||% ""))) resolved_label else (label_map[[sid]] %||% sid)
  }
  label_map
}

read_bundle_meta <- function(bundle_root) {
  meta_path <- file.path(bundle_root, "meta.yaml")
  require_existing_path(meta_path, "bundle meta")
  yaml::read_yaml(meta_path)
}

resolve_support_window_from_selected_run <- function(selected_run_root, fallback_support_start, cutoff_date) {
  retros_path <- require_existing_path(file.path(selected_run_root, "inputs", "shared", "retros", "retros.csv"), "selected-run retros.csv")
  retros <- readr::read_csv(retros_path, show_col_types = FALSE)
  date_col <- choose_date_col(retros)
  dates <- safe_date(retros[[date_col]])
  dates <- dates[!is.na(dates)]
  if (length(dates) == 0L) {
    stop(sprintf("No valid dates found in %s", retros_path), call. = FALSE)
  }
  support_start <- min(dates)
  cutoff_use <- safe_date(cutoff_date)
  if (!is.na(fallback_support_start)) {
    fallback_use <- safe_date(fallback_support_start)
    if (!is.na(fallback_use) && fallback_use != support_start) {
      warning(sprintf("Support-start mismatch: selected-run retros starts at %s but config fallback says %s. Using selected-run window.", format(support_start), format(fallback_use)), call. = FALSE)
    }
  }
  list(support_start = support_start, support_end = cutoff_use)
}

read_usgs_history <- function(usgs_path, support_start, cutoff_date) {
  usgs <- readr::read_csv(usgs_path, show_col_types = FALSE)
  date_col <- choose_date_col(usgs)
  value_col <- choose_value_col(usgs, c("discharge_cms", "streamflow_cms", "discharge", "flow_cms"))
  out <- tibble(
    Date = safe_date(usgs[[date_col]]),
    discharge_cms = suppressWarnings(as.numeric(usgs[[value_col]]))
  ) %>%
    filter(!is.na(Date), Date >= support_start, Date <= cutoff_date)
  out
}

read_covariate_series <- function(path, support_start, cutoff_date, label, value_candidates) {
  df <- readr::read_csv(path, show_col_types = FALSE)
  date_col <- choose_date_col(df)
  value_col <- choose_value_col(df, value_candidates)
  tibble(
    Date = safe_date(df[[date_col]]),
    Variable = label,
    Value = suppressWarnings(as.numeric(df[[value_col]]))
  ) %>%
    filter(!is.na(Date), Date >= support_start, Date <= cutoff_date)
}

select_source_by_priority <- function(df_long, family_prefix, priorities, start_date, end_date) {
  rows <- df_long %>%
    filter(Date >= start_date, Date <= end_date, grepl(family_prefix, source_id)) %>%
    mutate(priority = match(source_id, priorities))
  rows$priority[is.na(rows$priority)] <- length(priorities) + 1L
  rows %>%
    arrange(Date, priority, source_id) %>%
    group_by(Date) %>%
    slice(1L) %>%
    ungroup() %>%
    select(Date, source_id, source_label, discharge_cms)
}

extract_short_window_priorities <- function(meta, cutoff_date) {
  sel <- meta$config$inputs$retros$selection_policy %||% list()
  keep_ids <- tolower(as.character(unlist(sel$keep_source_ids %||% character(0), use.names = FALSE)))
  keep_ids <- keep_ids[nzchar(keep_ids)]

  choose_window <- function(windows, cutoff_use) {
    if (!is.list(windows) || length(windows) == 0L) return(NA_character_)
    for (w in windows) {
      start <- safe_date(w$start %||% NA_character_)
      end <- safe_date(w$end %||% NA_character_)
      if (!is.na(start) && !is.na(end) && cutoff_use >= start && cutoff_use <= end) {
        return(tolower(as.character(w$source_id %||% NA_character_)))
      }
    }
    NA_character_
  }

  cutoff_use <- safe_date(cutoff_date)
  win_glofas <- choose_window(sel$glofas_by_cutoff_windows %||% list(), cutoff_use)
  win_nws <- choose_window(sel$nws_by_cutoff_windows %||% list(), cutoff_use)

  glofas_priority <- unique(c(
    win_glofas,
    keep_ids[grepl("glofas", keep_ids)],
    c("glofas_hist_v40_lisflood_cons", "glofas_hist_v31_lisflood_cons", "glofas_hist_v21_htessel_cons", "glofas_legacy_reanalysis_v30", "glofas_synth_retro_ens_mean")
  ))
  nws_priority <- unique(c(
    keep_ids[grepl("^nws", keep_ids)],
    win_nws,
    c("nws_synth_retro_ens_mean", "nws_retro_v30", "nws_retro_v21", "nws_retro_v20", "nws_retro_v12")
  ))
  list(glofas_priority = glofas_priority[!is.na(glofas_priority)], nws_priority = nws_priority[!is.na(nws_priority)])
}

build_retros_long_selected <- function(bundle_root, bundle_class, support_start, plot_end, cutoff_date, selected_run_root = NULL) {
  meta <- read_bundle_meta(bundle_root)
  label_map <- build_source_label_map(meta, cutoff_date = cutoff_date, selected_run_root = selected_run_root)

  if (identical(bundle_class, "short_window_synth_bundle")) {
    path <- require_existing_path(file.path(bundle_root, "inputs", "retros_daily.csv"), "short-window retros_daily.csv")
    df <- readr::read_csv(path, show_col_types = FALSE) %>%
      transmute(
        Date = safe_date(.data[[choose_date_col(.)]]),
        source_id = tolower(as.character(source_id)),
        source_label_raw = as.character(source_label),
        discharge_cms = suppressWarnings(as.numeric(discharge_cms))
      ) %>%
      mutate(
        source_label = vapply(seq_len(n()), function(i) {
          label_map[[source_id[[i]]]] %||% source_label_raw[[i]] %||% source_id[[i]]
        }, character(1))
      ) %>%
      select(-source_label_raw) %>%
      filter(!is.na(Date), Date >= support_start, Date <= plot_end)
    pri <- extract_short_window_priorities(meta, cutoff_date)
    glofas <- select_source_by_priority(df, "glofas", pri$glofas_priority, support_start, plot_end)
    nws <- select_source_by_priority(df, "^nws", pri$nws_priority, support_start, plot_end)
    bind_rows(glofas, nws) %>% arrange(Date, source_id)
  } else if (identical(bundle_class, "histfix_long_history_bundle")) {
    path <- require_existing_path(file.path(bundle_root, "inputs", "retros_source_lineage.csv"), "histfix retros_source_lineage.csv")
    df <- readr::read_csv(path, show_col_types = FALSE) %>%
      transmute(
        Date = safe_date(.data[[choose_date_col(.)]]),
        usgs_cms = suppressWarnings(as.numeric(usgs_cms)),
        glofas_cms = suppressWarnings(as.numeric(glofas_cms)),
        glofas_source_id = tolower(as.character(glofas_source_id)),
        nws_cms = suppressWarnings(as.numeric(nws_cms)),
        nws_source_id = tolower(as.character(nws_source_id))
      ) %>%
      filter(!is.na(Date), Date >= support_start, Date <= plot_end)
    glofas <- df %>% transmute(
      Date,
      source_id = glofas_source_id,
      source_label = vapply(glofas_source_id, function(x) label_map[[x]] %||% x, character(1)),
      discharge_cms = glofas_cms
    )
    nws <- df %>% transmute(
      Date,
      source_id = nws_source_id,
      source_label = vapply(nws_source_id, function(x) label_map[[x]] %||% x, character(1)),
      discharge_cms = nws_cms
    )
    bind_rows(glofas, nws) %>% arrange(Date, source_id)
  } else {
    stop(sprintf("Unknown bundle_class: %s", bundle_class), call. = FALSE)
  }
}

build_retros_wide_for_history <- function(retros_long, cutoff_date) {
  trimmed <- retros_long %>%
    filter(Date <= cutoff_date) %>%
    mutate(Family = ifelse(grepl("^nws", source_id), "NWS", "GloFAS")) %>%
    arrange(Date, source_id) %>%
    group_by(Date, Family) %>%
    slice(1L) %>%
    ungroup() %>%
    select(Date, Family, discharge_cms) %>%
    tidyr::pivot_wider(names_from = Family, values_from = discharge_cms)
  if (!"GloFAS" %in% names(trimmed)) trimmed$GloFAS <- NA_real_
  if (!"NWS" %in% names(trimmed)) trimmed$NWS <- NA_real_
  trimmed %>% arrange(Date)
}

compute_coverage_summary <- function(retros_long) {
  retros_long %>%
    group_by(source_id, source_label) %>%
    summarise(
      coverage_start = min(Date, na.rm = TRUE),
      coverage_end = max(Date, na.rm = TRUE),
      n_points = n(),
      .groups = "drop"
    ) %>%
    arrange(source_label)
}

stage_forecats_bundle <- function(bundle_root, selected_usgs_path, retros_long, stage_dir, plot_start, plot_end, plot_scale = "log1p_cms") {
  meta <- read_bundle_meta(bundle_root)
  dir.create(file.path(stage_dir, "inputs"), recursive = TRUE, showWarnings = FALSE)

  input_map <- list(
    usgs_daily = selected_usgs_path,
    glofas_weighted_daily = require_existing_path(file.path(bundle_root, "inputs", "glofas_weighted_daily.csv"), "bundle glofas_weighted_daily.csv"),
    nws_weighted_daily = require_existing_path(file.path(bundle_root, "inputs", "nws_weighted_daily.csv"), "bundle nws_weighted_daily.csv")
  )
  for (nm in names(input_map)) {
    file.copy(input_map[[nm]], file.path(stage_dir, "inputs", paste0(nm, ".csv")), overwrite = TRUE)
  }
  readr::write_csv(
    retros_long %>% transmute(date = Date, source_id = source_id, source_label = source_label, discharge_cms = discharge_cms),
    file.path(stage_dir, "inputs", "retros_daily.csv")
  )

  meta$paths <- list(
    usgs_daily = "usgs_daily.csv",
    retros_daily = "retros_daily.csv",
    glofas_weighted_daily = "glofas_weighted_daily.csv",
    nws_weighted_daily = "nws_weighted_daily.csv"
  )
  meta$storage_scales <- list(
    usgs_daily = "raw_cms",
    retros_daily = "raw_cms",
    glofas_weighted_daily = "raw_cms",
    nws_weighted_daily = "raw_cms"
  )
  meta$transforms <- list(plot_scale = as.character(plot_scale))
  cutoff_use <- safe_date(meta$dates$cutoff_date %||% NA_character_)
  forecast_start <- safe_date(meta$dates$forecast_start_date %||% NA_character_)
  if (is.na(forecast_start) && !is.na(cutoff_use)) {
    forecast_start <- cutoff_use + 1
  }
  meta$dates$forecast_start_date <- format(forecast_start, "%Y-%m-%d")
  meta$dates$plot_start <- format(safe_date(plot_start), "%Y-%m-%d")
  meta$dates$plot_end <- format(safe_date(plot_end), "%Y-%m-%d")

  cov_tbl <- compute_coverage_summary(retros_long)
  meta$retrospective_coverage <- lapply(seq_len(nrow(cov_tbl)), function(i) {
    row <- cov_tbl[i, ]
    list(
      source_id = as.character(row$source_id),
      source_label = as.character(row$source_label),
      coverage_start = format(as.Date(row$coverage_start), "%Y-%m-%d"),
      coverage_end = format(as.Date(row$coverage_end), "%Y-%m-%d"),
      n_points = as.integer(row$n_points)
    )
  })

  yaml::write_yaml(meta, file.path(stage_dir, "meta.yaml"))
  invisible(stage_dir)
}

plot_usgs_png <- function(out_path, usgs_df, cutoff_date, support_start, plot_scale = "log1p_cms") {
  palette <- figure_product_palette()
  flood_df <- figure_flood_label_df(
    plot_scale = plot_scale,
    values = transform_flow(usgs_df$discharge_cms, plot_scale)
  )
  flood_style <- figure_flood_stage_style()
  flow_data <- usgs_df %>% mutate(Value = transform_flow(discharge_cms, plot_scale))
  x_label <- figure_date_label_format(flow_data$Date)
  p <- ggplot(flow_data, aes(x = Date, y = Value)) +
    geom_line(color = unname(palette[["usgs"]]), linewidth = 0.7, alpha = 0.95) +
    geom_hline(
      data = flood_df,
      aes(yintercept = y),
      linetype = flood_style$line_type,
      color = flood_style$line_color,
      linewidth = flood_style$line_width
    ) +
    annotate(
      "text",
      x = max(flow_data$Date),
      y = flood_df$label_y,
      label = flood_df$label,
      hjust = 1.02,
      vjust = 0.2,
      color = flood_style$label_color,
      fontface = flood_style$label_face,
      size = flood_style$label_size
    ) +
    labs(
      title = "Daily Flow of San Lorenzo River at Big Trees, CA",
      x = "Date",
      y = figure_flow_axis_label(plot_scale)
    ) +
    scale_x_date(labels = label_date(x_label), breaks = pretty_breaks(7), limits = c(support_start, cutoff_date)) +
    theme_manuscript_standard(base_size = 14, title_size = 16, legend_position = "none")
  ggsave(out_path, plot = p, width = 12, height = 6, units = "in", dpi = 900)
}

plot_covariates_png <- function(out_path, covariate_df, cutoff_date, support_start) {
  facet_labels <- figure_covariate_facet_labels()
  series_colors <- c(
    Precipitation = "#1b9e77",
    Soil_Moisture = "#386cb0",
    Climate_PC1 = "#e6550d"
  )
  x_label <- figure_date_label_format(covariate_df$Date)
  covariate_df <- covariate_df %>%
    mutate(
      VariableFacet = dplyr::recode(
        Variable,
        !!!facet_labels
      )
    )
  p <- ggplot(covariate_df, aes(x = Date, y = Value, color = Variable)) +
    geom_line(linewidth = 0.7, alpha = 0.92, na.rm = TRUE) +
    facet_wrap(~VariableFacet, ncol = 1, scales = "free_y", strip.position = "left", labeller = label_parsed) +
    scale_color_manual(values = series_colors) +
    labs(
      title = "Historical Covariate Inputs",
      x = "Date",
      y = NULL
    ) +
    scale_x_date(labels = label_date(x_label), breaks = pretty_breaks(7), limits = c(support_start, cutoff_date)) +
    theme_manuscript_standard(
      base_size = 14,
      title_size = 16,
      subtitle_size = 12,
      legend_position = "none",
      strip_text_size = 13
    )
  ggsave(out_path, plot = p, width = 12, height = 8, units = "in", dpi = 900)
}

plot_retrospective_png <- function(out_path, retros_wide, cutoff_date, support_start, available_start, plot_scale = "log1p_cms") {
  palette <- figure_product_palette()
  df <- retros_wide %>%
    mutate(
      GloFAS = transform_flow(GloFAS, plot_scale),
      NWS = transform_flow(NWS, plot_scale)
    )
  x_label <- figure_date_label_format(df$Date)

  p_g <- ggplot(df, aes(x = Date, y = GloFAS)) +
    geom_line(color = unname(palette[["glofas"]]), linewidth = 0.7, alpha = 0.92, na.rm = TRUE) +
    labs(
      title = "GloFAS Retrospective Product",
      x = NULL,
      y = figure_flow_axis_label(plot_scale)
    ) +
    scale_x_date(labels = label_date(x_label), breaks = pretty_breaks(7), limits = c(support_start, cutoff_date)) +
    theme_manuscript_standard(base_size = 14, title_size = 15, legend_position = "none")

  p_n <- ggplot(df, aes(x = Date, y = NWS)) +
    geom_line(color = unname(palette[["nws"]]), linewidth = 0.7, alpha = 0.92, na.rm = TRUE) +
    labs(
      title = "NWS Retrospective Product",
      x = "Date",
      y = figure_flow_axis_label(plot_scale)
    ) +
    scale_x_date(labels = label_date(x_label), breaks = pretty_breaks(7), limits = c(support_start, cutoff_date)) +
    theme_manuscript_standard(base_size = 14, title_size = 15, legend_position = "none")

  ggsave(out_path, plot = (p_g / p_n) + plot_layout(ncol = 1), width = 12, height = 8, units = "in", dpi = 900)
}
