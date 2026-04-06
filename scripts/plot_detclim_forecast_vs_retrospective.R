#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(readr)
  library(dplyr)
  library(ggplot2)
  library(patchwork)
  library(jsonlite)
  library(scales)
})

`%||%` <- function(x, y) {
  if (is.null(x) || identical(x, "")) y else x
}

parse_args <- function(argv) {
  out <- list()
  i <- 1L
  while (i <= length(argv)) {
    arg <- argv[[i]]
    if (startsWith(arg, "--")) {
      key <- sub("^--", "", arg)
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

abs_path <- function(path) {
  if (startsWith(path, "/")) return(path)
  normalizePath(file.path(getwd(), path), mustWork = FALSE)
}

parse_kv_text <- function(path) {
  if (!file.exists(path)) {
    stop(sprintf("Missing summary file: %s", path), call. = FALSE)
  }
  lines <- readLines(path, warn = FALSE)
  lines <- lines[nzchar(lines)]
  out <- list()
  for (line in lines) {
    parts <- strsplit(line, "=", fixed = TRUE)[[1L]]
    if (length(parts) < 2L) next
    key <- trimws(parts[[1L]])
    value <- paste(parts[-1L], collapse = "=")
    out[[key]] <- value
  }
  out
}

read_realized_series <- function(path, value_col) {
  df <- readr::read_csv(path, show_col_types = FALSE)
  tibble(
    date = as.Date(df$Date),
    observed_value = as.numeric(df[[value_col]])
  ) %>%
    filter(!is.na(date), is.finite(observed_value)) %>%
    arrange(date)
}

compute_metrics <- function(df, value_col = "forecast_value") {
  err <- df[[value_col]] - df$observed_value
  rmse <- sqrt(mean(err^2, na.rm = TRUE))
  mae <- mean(abs(err), na.rm = TRUE)
  bias <- mean(err, na.rm = TRUE)
  corr <- suppressWarnings(cor(df[[value_col]], df$observed_value, use = "complete.obs"))
  list(
    n_days = nrow(df),
    rmse = rmse,
    mae = mae,
    bias = bias,
    correlation = corr
  )
}

fmt_num <- function(x, digits = 3) {
  if (!is.finite(x)) return("NA")
  formatC(x, format = "f", digits = digits)
}

stable_seed <- function(base_seed, key) {
  key_int <- sum(utf8ToInt(key))
  as.integer((base_seed + key_int) %% .Machine$integer.max)
}

read_member_forecast <- function(path, label) {
  if (!file.exists(path)) {
    stop(sprintf("Missing %s member forecast cache: %s", label, path), call. = FALSE)
  }
  df <- readr::read_csv(path, show_col_types = FALSE)
  member_cols <- names(df)[grepl("^member_", names(df))]
  if (length(member_cols) == 0L) {
    stop(sprintf("%s member forecast cache has no member columns: %s", label, path), call. = FALSE)
  }
  if ("target_date" %in% names(df)) {
    target_date <- suppressWarnings(as.Date(df$target_date))
  } else if ("target_time_utc" %in% names(df)) {
    target_date <- suppressWarnings(as.Date(sub("T.*$", "", as.character(df$target_time_utc))))
  } else {
    stop(sprintf("%s member forecast cache is missing target_date/target_time_utc: %s", label, path), call. = FALSE)
  }
  df$target_date <- target_date
  list(data = df, member_cols = member_cols, source_path = normalizePath(path, mustWork = FALSE))
}

reduce_member_values <- function(values, reduction) {
  reduction <- tolower(trimws(as.character(reduction[[1L]])))
  values <- as.numeric(values)
  values <- values[is.finite(values)]
  if (length(values) == 0L) {
    return(NA_real_)
  }
  if (identical(reduction, "mean")) {
    return(mean(values, na.rm = TRUE))
  }
  if (identical(reduction, "median")) {
    return(stats::median(values, na.rm = TRUE))
  }
  if (identical(reduction, "max")) {
    return(max(values, na.rm = TRUE))
  }
  if (identical(reduction, "q70")) {
    return(unname(stats::quantile(values, probs = 0.70, na.rm = TRUE, type = 7)))
  }
  if (identical(reduction, "q90")) {
    return(unname(stats::quantile(values, probs = 0.90, na.rm = TRUE, type = 7)))
  }
  stop(sprintf("Unsupported ensemble reduction: %s", reduction), call. = FALSE)
}

member_daily_by_date <- function(df, member_cols, cutoff_date, end_date, daily_fun, reduction) {
  cutoff_date <- as.Date(cutoff_date)
  end_date <- as.Date(end_date)
  keep <- !is.na(df$target_date) & df$target_date > cutoff_date & df$target_date <= end_date
  df <- df[keep, , drop = FALSE]
  if (nrow(df) == 0L) {
    return(data.frame(date = as.Date(character()), value = numeric(), member_count = integer(), stringsAsFactors = FALSE))
  }
  daily_fun <- match.arg(daily_fun, c("sum", "mean"))
  dates <- sort(unique(df$target_date))
  out <- data.frame(date = dates, value = NA_real_, member_count = 0L, stringsAsFactors = FALSE)
  for (i in seq_along(dates)) {
    sub_df <- df[df$target_date == dates[[i]], member_cols, drop = FALSE]
    member_mat <- as.matrix(sub_df)
    storage.mode(member_mat) <- "numeric"
    member_daily <- if (identical(daily_fun, "sum")) {
      colSums(member_mat, na.rm = TRUE)
    } else {
      colMeans(member_mat, na.rm = TRUE)
    }
    member_daily <- member_daily[is.finite(member_daily)]
    out$value[[i]] <- reduce_member_values(member_daily, reduction = reduction)
    out$member_count[[i]] <- as.integer(length(member_daily))
  }
  out
}

precip_climatology_key <- function(dates) {
  format(as.Date(dates), "%m-%d")
}

build_precip_climatology <- function(observed_df, future_dates, target) {
  target <- tolower(trimws(as.character(target[[1L]])))
  future_dates <- as.Date(future_dates)
  if (identical(target, "zero")) {
    return(data.frame(date = future_dates, climatology_value = rep(0, length(future_dates)), stringsAsFactors = FALSE))
  }
  reducer <- if (identical(target, "climatology_median")) stats::median else mean
  obs <- observed_df %>%
    transmute(date = as.Date(date), value = as.numeric(observed_value)) %>%
    filter(is.finite(value))
  obs$key <- precip_climatology_key(obs$date)
  clim_lookup <- stats::aggregate(value ~ key, data = obs, FUN = reducer, na.rm = TRUE)
  fallback_value <- reducer(obs$value, na.rm = TRUE)
  if (!is.finite(fallback_value)) {
    fallback_value <- 0
  }
  out <- data.frame(date = future_dates, key = precip_climatology_key(future_dates), stringsAsFactors = FALSE)
  out <- merge(out, clim_lookup, by = "key", all.x = TRUE, sort = FALSE)
  out$date <- future_dates
  out$value[!is.finite(out$value)] <- fallback_value
  out <- out[, c("date", "value"), drop = FALSE]
  names(out)[[2L]] <- "climatology_value"
  out
}

apply_precip_tail_blend <- function(daily_df, observed_df, start_day, end_day, target) {
  if (!is.finite(start_day) || !is.finite(end_day)) {
    daily_df$climatology_value <- NA_real_
    daily_df$pre_tail_blend_value <- daily_df$value
    daily_df$tail_blend_target <- NA_character_
    daily_df$tail_blend_start_day <- NA_integer_
    daily_df$tail_blend_end_day <- NA_integer_
    daily_df$tail_blend_forecast_weight <- 1
    daily_df$tail_blend_target_value <- NA_real_
    return(daily_df)
  }
  out <- daily_df
  clim_df <- build_precip_climatology(observed_df, out$date, target = target)
  out <- merge(out, clim_df, by = "date", all.x = TRUE, sort = FALSE)
  out <- out[order(out$date), , drop = FALSE]
  lead_day <- seq_len(nrow(out))
  forecast_weight <- rep(1, nrow(out))
  if (end_day == start_day) {
    forecast_weight[lead_day > start_day] <- 0
  } else {
    interior <- lead_day > start_day & lead_day < end_day
    forecast_weight[lead_day >= end_day] <- 0
    forecast_weight[interior] <- 1 - ((lead_day[interior] - start_day) / (end_day - start_day))
  }
  forecast_weight <- pmax(0, pmin(1, forecast_weight))
  out$pre_tail_blend_value <- out$value
  out$value <- (forecast_weight * out$pre_tail_blend_value) + ((1 - forecast_weight) * out$climatology_value)
  out$tail_blend_target <- target
  out$tail_blend_start_day <- as.integer(start_day)
  out$tail_blend_end_day <- as.integer(end_day)
  out$tail_blend_forecast_weight <- forecast_weight
  out$tail_blend_target_value <- out$climatology_value
  out
}

complete_future_dates <- function(series_df, cutoff_date, horizon_days, label) {
  future_dates <- seq(as.Date(cutoff_date) + 1L, by = "day", length.out = as.integer(horizon_days))
  merged <- merge(data.frame(date = future_dates, stringsAsFactors = FALSE), series_df, by = "date", all.x = TRUE, sort = TRUE)
  if (any(!is.finite(merged$value))) {
    missing_dates <- merged$date[!is.finite(merged$value)]
    stop(sprintf("%s is missing forecast dates. Examples: %s", label, paste(head(as.character(missing_dates), 5L), collapse = ", ")), call. = FALSE)
  }
  merged
}

infer_handoff_root <- function(source_path) {
  root <- sub("/forecast_cache/.*$", "", normalizePath(source_path, mustWork = FALSE))
  if (!dir.exists(root)) {
    stop(sprintf("Could not infer handoff root from source path: %s", source_path), call. = FALSE)
  }
  root
}

resolve_gefs_apcp_path <- function(handoff_root, cutoff_date) {
  file.path(handoff_root, "forecast_cache", "gefs", sprintf("issue_date=%s", as.character(cutoff_date)), "variable=APCP_surface", "gefs_members.csv")
}

resolve_nwm_soilsat_paths <- function(handoff_root, cutoff_date) {
  init_dir <- file.path(handoff_root, "forecast_cache", "nwm", sprintf("init_date=%s", as.character(cutoff_date)))
  paths <- c(
    short_range_land = file.path(init_dir, "product_family=short_range_land", "variable=SOILSAT_TOP_top_soil_saturation_fraction", "nwm_members.csv"),
    medium_range_land = file.path(init_dir, "product_family=medium_range_land", "variable=SOILSAT_TOP_top_soil_saturation_fraction", "nwm_members.csv"),
    long_range_land = file.path(init_dir, "product_family=long_range_land", "variable=SOILSAT_TOP_top_soil_saturation_fraction", "nwm_members.csv")
  )
  paths[file.exists(paths)]
}

build_precip_forecast_series <- function(det_root, summary, observed_df, ensemble_reduction = "stored") {
  precip_future_path <- file.path(det_root, "deterministic_precip_future.csv")
  stored <- readr::read_csv(precip_future_path, show_col_types = FALSE)
  if (identical(ensemble_reduction, "stored")) {
    cutoff_date <- as.Date(summary$cutoff_date)
    lead_day <- if ("lead_day" %in% names(stored)) {
      as.numeric(stored$lead_day)
    } else {
      as.numeric(as.Date(stored$date) - cutoff_date)
    }
    return(list(
      df = stored %>% transmute(date = as.Date(date), forecast_value = as.numeric(value), lead_day = lead_day),
      forecast_label = "Forecast used in rerun",
      reduction_label = unique(stored$reduction)[[1L]] %||% (summary$precip_reduction %||% "stored")
    ))
  }
  cutoff_date <- as.Date(summary$cutoff_date)
  horizon_days <- as.integer(summary$horizon_days %||% "28")
  handoff_root <- infer_handoff_root(as.character(stored$source_path[[1L]]))
  apcp_path <- resolve_gefs_apcp_path(handoff_root, cutoff_date)
  apcp_info <- read_member_forecast(apcp_path, "GEFS APCP")
  daily_df <- member_daily_by_date(
    df = apcp_info$data,
    member_cols = apcp_info$member_cols,
    cutoff_date = cutoff_date,
    end_date = cutoff_date + horizon_days,
    daily_fun = "sum",
    reduction = ensemble_reduction
  )
  daily_df <- complete_future_dates(daily_df, cutoff_date, horizon_days, "GEFS APCP max-ensemble precipitation")
  threshold_mm <- suppressWarnings(as.numeric(summary$precip_dry_day_threshold_mm %||% "0"))
  daily_df$raw_value <- daily_df$value
  if (is.finite(threshold_mm) && threshold_mm > 0) {
    daily_df$value[daily_df$value < threshold_mm] <- 0
  }
  blend_enabled <- identical(toupper(summary$precip_tail_blend_enabled %||% "FALSE"), "TRUE")
  if (blend_enabled) {
    start_day <- suppressWarnings(as.integer(summary$precip_tail_blend_start_day %||% NA_integer_))
    end_day <- suppressWarnings(as.integer(summary$precip_tail_blend_end_day %||% NA_integer_))
    target <- summary$precip_tail_blend_target %||% "climatology_median"
    daily_df <- apply_precip_tail_blend(daily_df, observed_df, start_day, end_day, target)
  } else {
    daily_df$climatology_value <- NA_real_
    daily_df$pre_tail_blend_value <- daily_df$value
    daily_df$tail_blend_target <- NA_character_
    daily_df$tail_blend_start_day <- NA_integer_
    daily_df$tail_blend_end_day <- NA_integer_
    daily_df$tail_blend_forecast_weight <- 1
    daily_df$tail_blend_target_value <- NA_real_
  }
  list(
    df = daily_df %>% transmute(date = as.Date(date), forecast_value = as.numeric(value), lead_day = seq_len(n())),
    forecast_label = sprintf("Max-ensemble %s summary", toupper(summary$precip_source %||% "GEFS")),
    reduction_label = ensemble_reduction
  )
}

build_soil_forecast_series <- function(det_root, summary, ensemble_reduction = "stored") {
  soil_future_path <- file.path(det_root, "deterministic_soil_future.csv")
  stored <- readr::read_csv(soil_future_path, show_col_types = FALSE)
  if (identical(ensemble_reduction, "stored")) {
    cutoff_date <- as.Date(summary$cutoff_date)
    return(list(
      df = stored %>% transmute(date = as.Date(date), forecast_value = as.numeric(value), lead_day = as.numeric(date - cutoff_date)),
      forecast_label = "Forecast used in rerun",
      reduction_label = unique(stored$reduction)[[1L]] %||% (summary$soil_reduction %||% "stored")
    ))
  }
  cutoff_date <- as.Date(summary$cutoff_date)
  horizon_days <- as.integer(summary$horizon_days %||% "28")
  handoff_root <- infer_handoff_root(as.character(stored$source_path[[1L]]))
  soilsat_paths <- resolve_nwm_soilsat_paths(handoff_root, cutoff_date)
  porosity <- suppressWarnings(as.numeric(summary$nwm_soilsat_top_porosity %||% stored$porosity[[1L]]))
  if (!is.finite(porosity) || porosity <= 0) {
    stop(sprintf("Missing or invalid NWM SOILSAT_TOP porosity for %s", det_root), call. = FALSE)
  }
  family_priority <- c(short_range_land = 1L, medium_range_land = 2L, long_range_land = 3L)
  family_rows <- list()
  for (family_name in names(soilsat_paths)) {
    info <- read_member_forecast(soilsat_paths[[family_name]], sprintf("NWM %s SOILSAT_TOP", family_name))
    daily_df <- member_daily_by_date(
      df = info$data,
      member_cols = info$member_cols,
      cutoff_date = cutoff_date,
      end_date = cutoff_date + horizon_days,
      daily_fun = "mean",
      reduction = ensemble_reduction
    )
    if (nrow(daily_df) == 0L) next
    daily_df$value <- daily_df$value * porosity
    daily_df$source_family <- family_name
    daily_df$priority <- family_priority[[family_name]]
    family_rows[[family_name]] <- daily_df
  }
  combined <- do.call(rbind, family_rows)
  combined <- combined[order(combined$date, combined$priority), , drop = FALSE]
  combined <- combined[!duplicated(combined$date), , drop = FALSE]
  combined <- complete_future_dates(combined, cutoff_date, horizon_days, "NWM SOILSAT_TOP max-ensemble soil")
  list(
    df = combined %>% transmute(date = as.Date(date), forecast_value = as.numeric(value), lead_day = as.numeric(date - cutoff_date)),
    forecast_label = sprintf("Max-ensemble %s summary", summary$soil_source %||% "NWM_SOILSAT_TOP"),
    reduction_label = ensemble_reduction
  )
}

build_metric_label <- function(metrics, unit_label, heading = NULL) {
  paste(
    c(
      if (!is.null(heading)) heading,
      sprintf("RMSE %s %s", fmt_num(metrics$rmse), unit_label),
      sprintf("MAE %s %s", fmt_num(metrics$mae), unit_label),
      sprintf("Bias %s %s", fmt_num(metrics$bias), unit_label),
      sprintf("Corr %s", fmt_num(metrics$correlation))
    ),
    sep = "\n"
  )
}

plot_theme <- function() {
  theme_minimal(base_family = "sans", base_size = 13) +
    theme(
      plot.background = element_rect(fill = "#F6F2EA", color = NA),
      panel.background = element_rect(fill = "#FCFBF7", color = NA),
      panel.grid.minor = element_blank(),
      panel.grid.major.x = element_line(color = "#E2DBCF", linewidth = 0.25),
      panel.grid.major.y = element_line(color = "#DAD1C3", linewidth = 0.3),
      axis.title = element_text(face = "bold", color = "#2D2926"),
      axis.text = element_text(color = "#3F3934"),
      plot.title = element_text(face = "bold", size = 18, color = "#1E1A17"),
      plot.subtitle = element_text(size = 11, color = "#4A433D", lineheight = 1.05),
      plot.caption = element_text(size = 9.5, color = "#5B534B", hjust = 0),
      legend.position = "top",
      legend.title = element_blank(),
      legend.text = element_text(size = 10.5),
      panel.spacing = unit(8, "pt")
    )
}

build_comparison_plot <- function(
  df,
  cutoff_date,
  variable_label,
  realized_label,
  forecast_label,
  unit_label,
  subtitle,
  out_png,
  out_pdf,
  blend_lambda = 0.5,
  blend_lambda_mode = "constant",
  blend_lambda_start = 0.8,
  blend_lambda_end = 0.2,
  noise_sd_multiplier = 0.5,
  noise_seed = 20260309L,
  floor_noisy_retrospective_at_zero = FALSE,
  zero_zero_force_prob = 0
) {
  forecast_color <- "#CC6B2C"
  realized_color <- "#2A5B84"
  blend_color <- "#4C9A2A"
  forecast_error_color <- "#D1495B"
  blend_error_color <- "#7A8E2B"

  retrospective_sd <- stats::sd(df$observed_value, na.rm = TRUE)
  if (!is.finite(retrospective_sd)) {
    retrospective_sd <- 0
  }
  noise_sd <- noise_sd_multiplier * retrospective_sd
  set.seed(noise_seed)
  noisy_retrospective <- df$observed_value + stats::rnorm(nrow(df), mean = 0, sd = noise_sd)
  if (floor_noisy_retrospective_at_zero) {
    noisy_retrospective <- pmax(noisy_retrospective, 0)
  }

  blend_lambda_mode <- tolower(trimws(as.character(blend_lambda[[1L]] %||% "constant")))
  if (identical(blend_lambda_mode, "dynamic")) {
    if (nrow(df) <= 1L) {
      lambda_values <- rep(blend_lambda_start, nrow(df))
    } else {
      lambda_values <- seq(
        from = blend_lambda_start,
        to = blend_lambda_end,
        length.out = nrow(df)
      )
    }
    blend_label <- sprintf(
      "Blend with noisy retrospective (lambda %.2f to %.2f)",
      blend_lambda_start,
      blend_lambda_end
    )
    blend_heading <- sprintf(
      "Noisy blend (lambda %.2f to %.2f)",
      blend_lambda_start,
      blend_lambda_end
    )
    caption_lambda_text <- sprintf(
      "Lambda_t decreases linearly from %.2f at the first lead to %.2f at the last lead.",
      blend_lambda_start,
      blend_lambda_end
    )
  } else {
    lambda_values <- rep(blend_lambda, nrow(df))
    blend_label <- sprintf("Blend with noisy retrospective (lambda = %.2f)", blend_lambda)
    blend_heading <- sprintf("Noisy blend (lambda = %.2f)", blend_lambda)
    caption_lambda_text <- sprintf("Lambda_t is fixed at %.2f.", blend_lambda)
  }
  df <- df %>%
    mutate(
      noisy_retrospective_value = noisy_retrospective,
      blend_lambda_value = lambda_values,
      blend_value = forecast_value * (1 - blend_lambda_value) + noisy_retrospective_value * blend_lambda_value
    )

  dry_pair_count <- 0L
  dry_pair_forced_zero_count <- 0L
  if (isTRUE(floor_noisy_retrospective_at_zero) && is.finite(zero_zero_force_prob) && zero_zero_force_prob > 0) {
    dry_pair_idx <- which(abs(df$observed_value) < 1e-12 & abs(df$forecast_value) < 1e-12)
    dry_pair_count <- length(dry_pair_idx)
    if (dry_pair_count > 0L) {
      force_zero_draw <- stats::runif(dry_pair_count) < zero_zero_force_prob
      dry_pair_forced_zero_count <- sum(force_zero_draw)
      if (dry_pair_forced_zero_count > 0L) {
        forced_idx <- dry_pair_idx[force_zero_draw]
        df$blend_value[forced_idx] <- 0
      }
    }
  }

  forecast_metrics <- compute_metrics(df, "forecast_value")
  blend_metrics <- compute_metrics(df, "blend_value")
  metric_label <- paste(
    build_metric_label(forecast_metrics, unit_label, heading = forecast_label),
    build_metric_label(blend_metrics, unit_label, heading = blend_heading),
    sep = "\n\n"
  )

  y_top <- max(c(df$forecast_value, df$observed_value, df$blend_value), na.rm = TRUE)
  label_x <- max(ceiling(max(df$lead_day, na.rm = TRUE) * 0.72), min(df$lead_day, na.rm = TRUE))

  top_panel <- ggplot(df, aes(x = lead_day)) +
    geom_ribbon(
      aes(ymin = pmin(forecast_value, observed_value), ymax = pmax(forecast_value, observed_value)),
      fill = "#D0C2A6",
      alpha = 0.18
    ) +
    geom_line(aes(y = observed_value, color = realized_label), linewidth = 1.3, lineend = "round") +
    geom_point(aes(y = observed_value, color = realized_label), size = 2.0, alpha = 0.9) +
    geom_line(aes(y = forecast_value, color = forecast_label), linewidth = 1.3, linetype = "22", lineend = "round") +
    geom_point(aes(y = forecast_value, color = forecast_label), size = 2.0, shape = 21, stroke = 0.7, fill = "white") +
    geom_line(aes(y = blend_value, color = blend_label), linewidth = 1.35, linetype = "solid", lineend = "round") +
    geom_point(aes(y = blend_value, color = blend_label), size = 2.1, shape = 24, stroke = 0.7, fill = "#F6F2EA") +
    annotate(
      "label",
      x = label_x,
      y = y_top,
      label = metric_label,
      hjust = 0,
      vjust = 1,
      linewidth = 0.25,
      fill = alpha("white", 0.9),
      color = "#2D2926",
      size = 3.5
    ) +
    scale_color_manual(
      values = setNames(
        c(realized_color, forecast_color, blend_color),
        c(realized_label, forecast_label, blend_label)
      ),
      breaks = c(realized_label, forecast_label, blend_label),
      labels = c(realized_label, forecast_label, blend_label)
    ) +
    scale_x_continuous(
      breaks = pretty_breaks(n = 8),
      minor_breaks = NULL,
      expand = expansion(mult = c(0.01, 0.03))
    ) +
    labs(
      title = sprintf("%s Forecast vs Retrospective", variable_label),
      subtitle = subtitle,
      x = NULL,
      y = unit_label
    ) +
    plot_theme()

  error_df <- bind_rows(
    df %>%
      transmute(
        lead_day = lead_day,
        error = forecast_value - observed_value,
        error_series = "Forecast error"
      ),
    df %>%
      transmute(
        lead_day = lead_day,
        error = blend_value - observed_value,
        error_series = blend_heading
      )
  )

  error_panel <- ggplot(error_df, aes(x = lead_day, y = error, color = error_series)) +
    geom_hline(yintercept = 0, color = "#615A54", linewidth = 0.35) +
    geom_line(linewidth = 1.0, lineend = "round") +
    geom_point(size = 1.9, alpha = 0.92) +
    scale_color_manual(
      values = setNames(
        c(forecast_error_color, blend_error_color),
        c("Forecast error", blend_heading)
      )
    ) +
    scale_x_continuous(
      breaks = pretty_breaks(n = 8),
      minor_breaks = NULL,
      expand = expansion(mult = c(0.01, 0.03))
    ) +
    labs(
      x = "Lead day after cutoff",
      y = paste("Error vs retrospective", unit_label),
      caption = sprintf(
        "Cutoff %s | %s is compared against the realized daily retrospective values over the same 28-day window. NoisyRetrospective_t = Retrospective_t + Normal(0, %.3f). Blend_t = Forecast_t * (1 - Lambda_t) + NoisyRetrospective_t * Lambda_t. %s%s",
        cutoff_date,
        forecast_label,
        noise_sd,
        caption_lambda_text,
        if (isTRUE(floor_noisy_retrospective_at_zero) && is.finite(zero_zero_force_prob) && zero_zero_force_prob > 0) {
          sprintf(
            " For precipitation dry coincidences (forecast = 0 and retrospective = 0), Blend_t is forced to 0 with probability %.2f.",
            zero_zero_force_prob
          )
        } else {
          ""
        }
      )
    ) +
    plot_theme()

  full_plot <- top_panel / error_panel + plot_layout(heights = c(3.4, 1.25))

  dir.create(dirname(out_png), recursive = TRUE, showWarnings = FALSE)
  ggsave(out_png, full_plot, width = 14, height = 9, dpi = 320, bg = "#F6F2EA")
  ggsave(out_pdf, full_plot, width = 14, height = 9, bg = "#F6F2EA")

  list(
    forecast = forecast_metrics,
    blend = blend_metrics,
    noise = list(
      sd_of_retrospective = retrospective_sd,
      noise_sd = noise_sd,
      noise_sd_multiplier = noise_sd_multiplier,
      floor_at_zero = floor_noisy_retrospective_at_zero,
      seed = noise_seed
    ),
    lambda = list(
      mode = blend_lambda_mode,
      constant = if (identical(blend_lambda_mode, "constant")) blend_lambda else NA_real_,
      start = if (identical(blend_lambda_mode, "dynamic")) blend_lambda_start else NA_real_,
      end = if (identical(blend_lambda_mode, "dynamic")) blend_lambda_end else NA_real_,
      realized_min = min(df$blend_lambda_value, na.rm = TRUE),
      realized_max = max(df$blend_lambda_value, na.rm = TRUE)
    ),
    zero_zero_override = list(
      enabled = isTRUE(floor_noisy_retrospective_at_zero) && is.finite(zero_zero_force_prob) && zero_zero_force_prob > 0,
      force_prob = if (isTRUE(floor_noisy_retrospective_at_zero)) zero_zero_force_prob else NA_real_,
      dry_pair_count = dry_pair_count,
      forced_zero_count = dry_pair_forced_zero_count
    )
  )
}

build_cutoff_plots <- function(
  run_root,
  out_root,
  prism_path,
  soil_path,
  ensemble_reduction = "stored",
  blend_lambda = 0.5,
  blend_lambda_mode = "constant",
  blend_lambda_start = 0.8,
  blend_lambda_end = 0.2,
  noise_sd_multiplier = 0.5,
  base_noise_seed = 20260309L,
  precip_zero_zero_force_prob = 0
) {
  det_root <- file.path(run_root, "inputs", "shared", "deterministic_climate")
  summary_path <- file.path(det_root, "deterministic_climate_summary.txt")
  precip_future_path <- file.path(det_root, "deterministic_precip_future.csv")
  soil_future_path <- file.path(det_root, "deterministic_soil_future.csv")

  summary <- parse_kv_text(summary_path)
  cutoff_date <- summary$cutoff_date %||% stop("Missing cutoff_date in deterministic climate summary", call. = FALSE)
  cutoff_date <- as.character(cutoff_date)

  precip_realized <- read_realized_series(prism_path, "PRCP_mm")
  precip_forecast <- build_precip_forecast_series(det_root, summary, precip_realized, ensemble_reduction = ensemble_reduction)
  precip_df <- precip_forecast$df %>%
    left_join(precip_realized, by = "date") %>%
    filter(is.finite(forecast_value), is.finite(observed_value)) %>%
    arrange(lead_day)

  soil_realized <- read_realized_series(soil_path, "Daily_Avg_Soil_Moisture")
  soil_forecast <- build_soil_forecast_series(det_root, summary, ensemble_reduction = ensemble_reduction)
  soil_df <- soil_forecast$df %>%
    left_join(soil_realized, by = "date") %>%
    filter(is.finite(forecast_value), is.finite(observed_value)) %>%
    arrange(lead_day)

  if (nrow(precip_df) == 0L) {
    stop(sprintf("No overlapping precipitation rows for %s", run_root), call. = FALSE)
  }
  if (nrow(soil_df) == 0L) {
    stop(sprintf("No overlapping soil rows for %s", run_root), call. = FALSE)
  }

  cutoff_out <- file.path(out_root, sprintf("cutoff_date=%s", cutoff_date))
  precip_png <- file.path(cutoff_out, "precip_forecast_vs_prism.png")
  precip_pdf <- file.path(cutoff_out, "precip_forecast_vs_prism.pdf")
  soil_png <- file.path(cutoff_out, "soil_forecast_vs_era5.png")
  soil_pdf <- file.path(cutoff_out, "soil_forecast_vs_era5.pdf")

  precip_subtitle <- sprintf(
    "Forecast summary: %s | ensemble reduction %s | dry-day threshold %s mm | tail blend %s days %s-%s | horizon %s days",
    summary$precip_source %||% "GEFS_APCP",
    precip_forecast$reduction_label,
    summary$precip_dry_day_threshold_mm %||% "0",
    summary$precip_tail_blend_target %||% "disabled",
    summary$precip_tail_blend_start_day %||% "NA",
    summary$precip_tail_blend_end_day %||% "NA",
    summary$horizon_days %||% "28"
  )
  soil_subtitle <- sprintf(
    "Forecast summary: %s | ensemble reduction %s | porosity %.3f (q10 %.3f, q90 %.3f) | horizon %s days",
    summary$soil_source %||% "NWM_SOILSAT_TOP",
    soil_forecast$reduction_label,
    as.numeric(summary$nwm_soilsat_top_porosity %||% NA_real_),
    as.numeric(summary$nwm_soilsat_top_porosity_q10 %||% NA_real_),
    as.numeric(summary$nwm_soilsat_top_porosity_q90 %||% NA_real_),
    summary$horizon_days %||% "28"
  )

  precip_metrics <- build_comparison_plot(
    df = precip_df,
    cutoff_date = cutoff_date,
    variable_label = "Precipitation",
    realized_label = "PRISM retrospective",
    forecast_label = precip_forecast$forecast_label,
    unit_label = "mm/day",
    subtitle = precip_subtitle,
    out_png = precip_png,
    out_pdf = precip_pdf,
    blend_lambda = blend_lambda,
    blend_lambda_mode = blend_lambda_mode,
    blend_lambda_start = blend_lambda_start,
    blend_lambda_end = blend_lambda_end,
    noise_sd_multiplier = noise_sd_multiplier,
    noise_seed = stable_seed(base_noise_seed, paste(cutoff_date, "precip", sep = "_")),
    floor_noisy_retrospective_at_zero = TRUE,
    zero_zero_force_prob = precip_zero_zero_force_prob
  )

  soil_metrics <- build_comparison_plot(
    df = soil_df,
    cutoff_date = cutoff_date,
    variable_label = "Soil Moisture",
    realized_label = "ERA5 soil retrospective",
    forecast_label = soil_forecast$forecast_label,
    unit_label = "m3/m3",
    subtitle = soil_subtitle,
    out_png = soil_png,
    out_pdf = soil_pdf,
    blend_lambda = blend_lambda,
    blend_lambda_mode = blend_lambda_mode,
    blend_lambda_start = blend_lambda_start,
    blend_lambda_end = blend_lambda_end,
    noise_sd_multiplier = noise_sd_multiplier,
    noise_seed = stable_seed(base_noise_seed, paste(cutoff_date, "soil", sep = "_")),
    floor_noisy_retrospective_at_zero = FALSE,
    zero_zero_force_prob = 0
  )

  summary_payload <- list(
    cutoff_date = cutoff_date,
    run_root = run_root,
    ensemble_reduction = ensemble_reduction,
    blend_lambda = blend_lambda,
    blend_lambda_mode = blend_lambda_mode,
    blend_lambda_start = blend_lambda_start,
    blend_lambda_end = blend_lambda_end,
    noise_sd_multiplier = noise_sd_multiplier,
    precip_zero_zero_force_prob = precip_zero_zero_force_prob,
    precip = c(
      list(
        png = precip_png,
        pdf = precip_pdf,
        n_days = nrow(precip_df)
      ),
      precip_metrics
    ),
    soil = c(
      list(
        png = soil_png,
        pdf = soil_pdf,
        n_days = nrow(soil_df)
      ),
      soil_metrics
    )
  )
  jsonlite::write_json(summary_payload, file.path(cutoff_out, "comparison_summary.json"), auto_unbox = TRUE, pretty = TRUE)
  summary_payload
}

main <- function() {
  args <- parse_args(commandArgs(trailingOnly = TRUE))

  repo_root <- abs_path(args$`repo-root` %||% ".")
  runs_root <- abs_path(args$`runs-root` %||% file.path(repo_root, "repro", "runs"))
  out_root <- abs_path(args$`out-root` %||% file.path(repo_root, "repro", "deterministic_covariate_forecast_vs_retrospective"))
  prism_path <- abs_path(args$`prism-path` %||% file.path(repo_root, "prism_precipitation_santa_cruz_1987_2023.csv"))
  soil_path <- abs_path(args$`soil-path` %||% file.path(repo_root, "soil_moisture_data", "soil_moisture_big_trees_daily_avg_1987_2023.csv"))
  ensemble_reduction <- tolower(trimws(args$`ensemble-reduction` %||% "stored"))
  blend_lambda <- as.numeric(args$`blend-lambda` %||% "0.5")
  blend_lambda_mode <- tolower(trimws(args$`blend-lambda-mode` %||% "constant"))
  blend_lambda_start <- as.numeric(args$`blend-lambda-start` %||% "0.8")
  blend_lambda_end <- as.numeric(args$`blend-lambda-end` %||% "0.2")
  noise_sd_multiplier <- as.numeric(args$`noise-sd-multiplier` %||% "0.5")
  precip_zero_zero_force_prob <- as.numeric(args$`precip-zero-zero-force-prob` %||% "0")
  base_noise_seed <- as.integer(args$`noise-seed` %||% "20260309")
  if (!(ensemble_reduction %in% c("stored", "mean", "median", "max", "q70", "q90"))) {
    stop("--ensemble-reduction must be one of: stored, mean, median, max, q70, q90", call. = FALSE)
  }
  if (!is.finite(blend_lambda) || blend_lambda < 0 || blend_lambda > 1) {
    stop("--blend-lambda must be a number between 0 and 1", call. = FALSE)
  }
  if (!(blend_lambda_mode %in% c("constant", "dynamic"))) {
    stop("--blend-lambda-mode must be one of: constant, dynamic", call. = FALSE)
  }
  if (!is.finite(blend_lambda_start) || blend_lambda_start < 0 || blend_lambda_start > 1) {
    stop("--blend-lambda-start must be a number between 0 and 1", call. = FALSE)
  }
  if (!is.finite(blend_lambda_end) || blend_lambda_end < 0 || blend_lambda_end > 1) {
    stop("--blend-lambda-end must be a number between 0 and 1", call. = FALSE)
  }
  if (!is.finite(noise_sd_multiplier) || noise_sd_multiplier < 0) {
    stop("--noise-sd-multiplier must be a non-negative number", call. = FALSE)
  }
  if (!is.finite(precip_zero_zero_force_prob) || precip_zero_zero_force_prob < 0 || precip_zero_zero_force_prob > 1) {
    stop("--precip-zero-zero-force-prob must be a number between 0 and 1", call. = FALSE)
  }
  if (!is.finite(base_noise_seed)) {
    stop("--noise-seed must be an integer", call. = FALSE)
  }

  run_ids <- args$`run-ids` %||% "multimodel_20210123,multimodel_20211112,multimodel_20211221,multimodel_20220511,multimodel_20221225"
  run_ids <- trimws(strsplit(run_ids, ",", fixed = TRUE)[[1L]])
  run_ids <- run_ids[nzchar(run_ids)]
  if (length(run_ids) == 0L) {
    stop("No run ids provided", call. = FALSE)
  }

  all_summaries <- lapply(run_ids, function(run_id) {
    run_root <- file.path(runs_root, run_id)
    build_cutoff_plots(
      run_root,
      out_root,
      prism_path,
      soil_path,
      ensemble_reduction = ensemble_reduction,
      blend_lambda = blend_lambda,
      blend_lambda_mode = blend_lambda_mode,
      blend_lambda_start = blend_lambda_start,
      blend_lambda_end = blend_lambda_end,
      noise_sd_multiplier = noise_sd_multiplier,
      base_noise_seed = base_noise_seed,
      precip_zero_zero_force_prob = precip_zero_zero_force_prob
    )
  })

  jsonlite::write_json(
    all_summaries,
    file.path(out_root, "all_cutoff_comparison_summaries.json"),
    auto_unbox = TRUE,
    pretty = TRUE
  )

  cat(sprintf("Wrote plots under %s\n", out_root))
}

main()
