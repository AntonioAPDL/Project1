#!/usr/bin/env Rscript

# Batch driver for generating one `forecats.png` per cutoff_date across multiple intervals.
#
# Modes:
#   - audit          : check GloFAS GRIB availability + output existence
#   - build-forecasts: build per-date forecast caches (GloFAS from GRIB; NWS from results.pkl)
#   - render         : generate per-date bundles + forecats.png using cached forecasts
#
# Usage:
#   Rscript scripts/forecats_batch.R --config <yaml> --mode <audit|build-forecasts|render>
# Optional sharding:
#   --shard-count N --shard-index i

suppressPackageStartupMessages({
  library(yaml)
  library(readr)
  library(dplyr)
  library(dataRetrieval)
})

`%||%` <- function(x, y) if (is.null(x)) y else x

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

stop_if_missing <- function(x, msg) {
  if (is.null(x) || identical(x, "")) stop(msg, call. = FALSE)
}

as_abs_path <- function(p) {
  if (is.null(p)) return(NULL)
  if (startsWith(p, "/")) return(p)
  normalizePath(file.path(getwd(), p), mustWork = FALSE)
}

ensure_dir <- function(p) dir.create(p, showWarnings = FALSE, recursive = TRUE)

run_cmd <- function(cmd, log_path = NULL) {
  cat("[CMD] ", cmd, "\n", sep = "")
  if (is.null(log_path)) {
    rc <- system(cmd)
  } else {
    rc <- system(paste(cmd, ">>", shQuote(log_path), "2>&1"))
  }
  if (!identical(rc, 0L)) stop(paste("Command failed:", cmd), call. = FALSE)
  invisible(TRUE)
}

seq_dates_inclusive <- function(start_date, end_date) {
  start_date <- as.Date(start_date)
  end_date <- as.Date(end_date)
  seq.Date(start_date, end_date, by = "day")
}

compute_cutoff_dates <- function(cfg) {
  intervals <- cfg$dates$intervals
  if (is.null(intervals) || length(intervals) == 0) stop("Missing dates.intervals in config", call. = FALSE)
  dates <- c()
  for (iv in intervals) {
    stop_if_missing(iv$start, "Missing intervals[*].start")
    stop_if_missing(iv$end, "Missing intervals[*].end")
    dates <- c(dates, seq_dates_inclusive(iv$start, iv$end))
  }
  dates <- sort(unique(as.Date(dates)))
  dates
}

apply_shard <- function(dates, shard_count, shard_index) {
  if (shard_count <= 1) return(dates)
  idx0 <- seq_along(dates) - 1L
  dates[idx0 %% shard_count == shard_index]
}

DEFAULT_FORECAST_ORIGIN_MIN <- as.Date("2019-11-05")
DEFAULT_FORECAST_ORIGIN_MAX <- as.Date("2023-01-31")
DEFAULT_FORECAST_ORIGIN_MISSING <- as.Date(c(
  "2020-03-12", "2020-03-13", "2020-03-14", "2020-03-15", "2020-03-16",
  "2020-07-29",
  "2020-11-14",
  "2022-07-14"
))

default_glofas_family_windows <- function() {
  list(
    list(
      start = "1900-01-01",
      end = "2021-05-25",
      source_id = "glofas_hist_v21_htessel_cons",
      forecast_family = "2.x",
      historical_version_label = "version_2_1"
    ),
    list(
      start = "2021-05-26",
      end = "2023-07-25",
      source_id = "glofas_hist_v31_lisflood_cons",
      forecast_family = "3.x",
      historical_version_label = "version_3_1"
    ),
    list(
      start = "2023-07-26",
      end = "2999-12-31",
      source_id = "glofas_hist_v40_lisflood_cons",
      forecast_family = "4.x",
      historical_version_label = "version_4_0"
    )
  )
}

default_nws_forecast_windows <- function() {
  list(
    list(
      start = "1900-01-01",
      end = "2021-04-19",
      forecast_version_label = "2.0",
      same_version_source_id = "nws_retro_v20",
      next_version_source_id = "nws_retro_v21"
    ),
    list(
      start = "2021-04-20",
      end = "2023-09-19",
      forecast_version_label = "2.1",
      same_version_source_id = "nws_retro_v21",
      next_version_source_id = "nws_retro_v30"
    ),
    list(
      start = "2023-09-20",
      end = "2999-12-31",
      forecast_version_label = "3.0",
      same_version_source_id = "nws_retro_v30",
      next_version_source_id = NA_character_
    )
  )
}

format_date_vec <- function(x) {
  x <- as.Date(x)
  x <- x[!is.na(x)]
  if (length(x) == 0) return("")
  paste(format(x, "%Y-%m-%d"), collapse = ", ")
}

resolve_auto_cutoff_policy <- function(policy_cfg) {
  policy_cfg <- policy_cfg %||% list()
  span_cfg <- policy_cfg$forecast_origin_span %||% list()
  nws_cfg <- policy_cfg$nws %||% list()

  missing_cfg <- policy_cfg$known_missing_origin_dates %||% DEFAULT_FORECAST_ORIGIN_MISSING
  missing_dates <- as.Date(as.character(unlist(missing_cfg)))
  missing_dates <- sort(unique(missing_dates[!is.na(missing_dates)]))

  list(
    enabled = {
      v <- policy_cfg$enabled
      if (is.null(v)) TRUE else isTRUE(v)
    },
    forecast_origin_min = as.Date(as.character(span_cfg$start %||% DEFAULT_FORECAST_ORIGIN_MIN)),
    forecast_origin_max = as.Date(as.character(span_cfg$end %||% DEFAULT_FORECAST_ORIGIN_MAX)),
    known_missing_origin_dates = missing_dates,
    glofas_family_windows = policy_cfg$glofas_family_windows %||% default_glofas_family_windows(),
    nws_forecast_windows = policy_cfg$nws_forecast_windows %||% default_nws_forecast_windows(),
    nws_primary_source_id = as.character(nws_cfg$primary_source_id %||% "nws_synth_retro_ens_mean"),
    write_nws_hybrid_diagnostic = {
      v <- nws_cfg$write_hybrid_diagnostic
      if (is.null(v)) TRUE else isTRUE(v)
    },
    use_nws_synthetic_lead_fallback = {
      v <- nws_cfg$use_synthetic_lead_fallback
      if (is.null(v)) TRUE else isTRUE(v)
    },
    fail_on_unresolved_nws_synthetic = {
      v <- nws_cfg$fail_on_unresolved_synthetic
      if (is.null(v)) TRUE else isTRUE(v)
    }
  )
}

validate_cutoff_against_local_origin_span <- function(cutoff_date, policy) {
  d <- as.Date(cutoff_date)
  if (is.na(d)) {
    stop("Invalid cutoff_date encountered while enforcing retrospective policy.", call. = FALSE)
  }

  if (d < policy$forecast_origin_min || d > policy$forecast_origin_max) {
    stop(
      sprintf(
        paste0(
          "cutoff_date=%s is outside the available shared forecast-origin span [%s, %s]. ",
          "Choose a cutoff within local cache bounds or refresh local forecast caches first."
        ),
        format(d, "%Y-%m-%d"),
        format(policy$forecast_origin_min, "%Y-%m-%d"),
        format(policy$forecast_origin_max, "%Y-%m-%d")
      ),
      call. = FALSE
    )
  }

  if (d %in% policy$known_missing_origin_dates) {
    stop(
      sprintf(
        paste0(
          "cutoff_date=%s is a known missing forecast-origin date in local shared cache. ",
          "Known missing dates: %s"
        ),
        format(d, "%Y-%m-%d"),
        format_date_vec(policy$known_missing_origin_dates)
      ),
      call. = FALSE
    )
  }
}

write_dates_file <- function(path, dates) {
  ensure_dir(dirname(path))
  writeLines(format(as.Date(dates), "%Y-%m-%d"), con = path)
}

audit_mode <- function(cfg, cutoff_dates, batch_root, shard_tag) {
  out_root <- as_abs_path(cfg$run$out_root)
  grib_root <- as_abs_path(cfg$inputs$glofas$grib_root)
  site_id <- as.character(cfg$site$usgs_site)
  run_id <- as.character(cfg$run$run_id)

  # Fast GRIB presence check: issue_date directory exists and has at least one *.grib.
  has_grib <- vapply(cutoff_dates, function(d) {
    dd <- format(as.Date(d), "%Y-%m-%d")
    dir <- file.path(grib_root, paste0("issue_date=", dd))
    if (!dir.exists(dir)) return(FALSE)
    length(list.files(dir, pattern = "\\.grib$", full.names = TRUE)) > 0
  }, logical(1))

  fig_exists <- vapply(cutoff_dates, function(d) {
    dd <- format(as.Date(d), "%Y-%m-%d")
    fig <- file.path(out_root, paste0("site=", site_id), paste0("cutoff_date=", dd), paste0("run_id=", run_id), "figures", "forecats.png")
    file.exists(fig) && file.info(fig)$size > 0
  }, logical(1))

  df <- tibble::tibble(
    cutoff_date = format(as.Date(cutoff_dates), "%Y-%m-%d"),
    has_glofas_grib = has_grib,
    figure_exists = fig_exists
  )

  audit_path <- file.path(batch_root, paste0("audit", shard_tag, ".csv"))
  readr::write_csv(df, audit_path)

  cat(sprintf("[OK] wrote %s\n", audit_path))
  cat(sprintf("Cutoffs: %d | GRIB missing: %d | figures already exist: %d\n", nrow(df), sum(!has_grib), sum(fig_exists)))
}

build_forecasts_mode <- function(cfg, cutoff_dates, batch_root, shard_tag, providers = "all") {
  logs_dir <- file.path(batch_root, "logs")
  ensure_dir(logs_dir)
  agg_scale <- cfg$processing$aggregation_scale_internal %||% "log1p_cms"

  providers <- tolower(as.character(providers %||% "all"))
  keep_glofas <- providers == "all" || grepl("(^|,)glofas(,|$)", providers)
  keep_nws <- providers == "all" || grepl("(^|,)nws(,|$)", providers)

  dates_file <- file.path(batch_root, paste0("cutoff_dates", shard_tag, ".txt"))
  write_dates_file(dates_file, cutoff_dates)

  fc_root <- file.path(batch_root, "forecast_cache")
  ensure_dir(fc_root)

  # -------------------------
  # GloFAS extraction cache
  # -------------------------
  if (keep_glofas) {
    g <- cfg$inputs$glofas
    g_out <- file.path(fc_root, "glofas")
    ensure_dir(g_out)

    cell_policy <- if (isTRUE(g$nearest_valid_cell)) "nearest_valid" else "nearest_any"
    g_cmd <- paste(
      "python3",
      shQuote(file.path(getwd(), "scripts", "forecats_extract_glofas_batch.py")),
      "--grib-root", shQuote(as_abs_path(g$grib_root)),
      "--dates-file", shQuote(dates_file),
      "--out-root", shQuote(g_out),
      "--lat", shQuote(as.character(cfg$site$lat)),
      "--lon", shQuote(as.character(cfg$site$lon)),
      "--var", shQuote(g$var %||% "dis24"),
      "--control-dtype", shQuote(g$data_types$control %||% "cf"),
      "--perturbed-dtype", shQuote(g$data_types$perturbed %||% "pf"),
      "--cell-policy", shQuote(cell_policy),
      "--shift-days", shQuote(as.character(g$shift_days %||% 1)),
      "--post-days", shQuote(as.character(cfg$dates$plot_post_days %||% 28)),
      if (isTRUE(cfg$run$overwrite)) "--overwrite" else "",
      "--verbose"
    )
    g_log <- file.path(logs_dir, paste0("build_forecasts_glofas", shard_tag, ".log"))
    run_cmd(g_cmd, log_path = g_log)
  }

  # -------------------------
  # NWS extraction cache
  # -------------------------
  if (keep_nws) {
    n <- cfg$inputs$nws
    n_out <- file.path(fc_root, "nws")
    ensure_dir(n_out)

    n_scheme <- n$weighting$scheme %||% "latest"
    exp_spec <- ""
    if (!is.null(n$weighting$exponents) && length(n$weighting$exponents) > 0) {
      parts <- c()
      for (k in names(n$weighting$exponents)) parts <- c(parts, paste0(k, "=", as.character(n$weighting$exponents[[k]])))
      exp_spec <- paste(parts, collapse = ",")
    }

    n_cmd <- paste(
      "python3",
      shQuote(file.path(getwd(), "scripts", "forecats_extract_nws_batch.py")),
      "--pkl", shQuote(as_abs_path(n$pkl_path)),
      "--dates-file", shQuote(dates_file),
      "--out-root", shQuote(n_out),
      "--post-days", shQuote(as.character(cfg$dates$plot_post_days %||% 28)),
      if (isTRUE(n$parse_issue_hour)) "--parse-issue-hour" else "",
      "--issue-lookback-days", shQuote(as.character(n$issue_lookback_days %||% 40)),
      "--weighting-scheme", shQuote(as.character(n_scheme)),
      "--alpha", shQuote(as.character(n$weighting$alpha %||% 1.0)),
      "--aggregation-scale", shQuote(as.character(agg_scale)),
      if (n_scheme == "notebook") paste("--exponents", shQuote(exp_spec)) else "",
      if (isTRUE(cfg$run$overwrite)) "--overwrite" else "",
      "--verbose"
    )
    n_log <- file.path(logs_dir, paste0("build_forecasts_nws", shard_tag, ".log"))
    run_cmd(n_cmd, log_path = n_log)
  }

  cat(sprintf("[OK] forecast_cache ready under %s\n", fc_root))
}

fetch_usgs_cache <- function(cfg, usgs_cache_path, end_date) {
  end_date <- as.Date(end_date)

  if (file.exists(usgs_cache_path) && !isTRUE(cfg$run$overwrite)) {
    cached <- tryCatch(
      readr::read_csv(usgs_cache_path, show_col_types = FALSE) %>%
        mutate(
          date = as.Date(date),
          discharge_cms = as.numeric(discharge_cms)
        ),
      error = function(e) NULL
    )

    if (!is.null(cached) && ("date" %in% names(cached)) && ("discharge_cms" %in% names(cached))) {
      max_date <- suppressWarnings(max(cached$date, na.rm = TRUE))
      if (is.finite(max_date) && !is.na(max_date) && (max_date >= end_date)) {
        return(cached)
      }

      cat(sprintf(
        "[WARN] USGS cache is stale (max_date=%s < required_end=%s); refetching.\n",
        ifelse(is.finite(max_date), format(as.Date(max_date), "%Y-%m-%d"), "NA"),
        format(end_date, "%Y-%m-%d")
      ))
    } else {
      cat("[WARN] USGS cache is unreadable/invalid; refetching.\n")
    }
  }

  ensure_dir(dirname(usgs_cache_path))
  site_id <- as.character(cfg$site$usgs_site)
  usgs_cfg <- cfg$site$usgs %||% list()
  start_usgs <- usgs_cfg$start_date %||% "1979-01-01"

  cat(sprintf("[STEP] USGS fetch (site=%s)\n", site_id))
  CFSToCMS <- 0.0283168466
  usgs <- dataRetrieval::readNWISdv(
    siteNumbers = site_id,
    parameterCd = usgs_cfg$parameterCd %||% "00060",
    statCd = usgs_cfg$statCd %||% "00003",
    startDate = start_usgs,
    endDate = format(end_date, "%Y-%m-%d")
  )
  # Expected col name for daily discharge: X_00060_00003
  if (!("X_00060_00003" %in% names(usgs))) {
    stop("Unexpected USGS column names; expected X_00060_00003 in readNWISdv output.", call. = FALSE)
  }

  out <- usgs %>%
    transmute(
      date = as.Date(Date),
      discharge_cms = as.numeric(X_00060_00003) * CFSToCMS
    )

  readr::write_csv(out, usgs_cache_path)
  cat(sprintf("[OK] wrote %s (%d rows)\n", usgs_cache_path, nrow(out)))
  out
}

build_retros_cache <- function(cfg, retros_cache_path, plot_end) {
  plot_end <- as.Date(plot_end)

  if (file.exists(retros_cache_path) && !isTRUE(cfg$run$overwrite)) {
    cached <- tryCatch(
      readr::read_csv(retros_cache_path, show_col_types = FALSE) %>%
        mutate(
          date = as.Date(date),
          discharge_cms = as.numeric(discharge_cms)
        ),
      error = function(e) NULL
    )

    has_new_schema <- !is.null(cached) &&
      all(c("date", "source_id", "source_label", "source_family", "discharge_cms") %in% names(cached))

    if (has_new_schema) {
      max_date <- suppressWarnings(max(cached$date, na.rm = TRUE))
      if (is.finite(max_date) && !is.na(max_date) && (max_date >= plot_end)) {
        return(cached)
      }

      cat(sprintf(
        "[WARN] Retros cache is stale (max_date=%s < required_end=%s); rebuilding.\n",
        ifelse(is.finite(max_date), format(as.Date(max_date), "%Y-%m-%d"), "NA"),
        format(plot_end, "%Y-%m-%d")
      ))
    } else {
      cat("[WARN] Retros cache is unreadable/invalid; rebuilding.\n")
    }
  }

  ensure_dir(dirname(retros_cache_path))
  in_path <- as_abs_path(cfg$inputs$retros$path)
  in_scale <- cfg$inputs$retros$scale %||% "log1p_cms"
  stop_if_missing(in_path, "Missing inputs.retros.path")

  retro <- readr::read_csv(in_path, show_col_types = FALSE)
  stop_if_missing(retro$Date %||% NULL, "Retros CSV must contain Date column")

  convert_scale_to_cms <- function(x, scale) {
    if (scale == "raw_cms") return(x)
    if (scale == "log1p_cms") return(exp(x) - 1)
    if (scale == "log_log1p_cms") {
      stop("log_log1p_cms is not allowed in the current workflow; use log1p_cms.", call. = FALSE)
    }
    stop(paste("Unknown scale:", scale))
  }

  mk_source_id <- function(x) {
    paste0(
      "baseline_",
      tolower(gsub("_+", "_", gsub("[^A-Za-z0-9]+", "_", x)))
    )
  }

  baseline_label <- function(col) {
    if (col == "GloFAS") return("GloFAS retrospective (baseline)")
    if (col == "NWS3.0") return("NWS retrospective v3.0 (baseline)")
    if (col == "NWS2.1") return("NWS retrospective v2.1 (baseline)")
    if (col == "NWS2.0") return("NWS retrospective v2.0 (baseline)")
    if (col == "NWS") return("NWS retrospective (baseline)")
    paste0(col, " retrospective (baseline)")
  }

  baseline_family <- function(col) {
    if (grepl("^NWS", col)) return("nwm_retrospective")
    if (grepl("^GloFAS", col, ignore.case = TRUE)) return("glofas_retrospective_baseline")
    "retrospective_baseline"
  }

  baseline_cols <- setdiff(names(retro), c("Date", "USGS"))
  if (length(baseline_cols) == 0) {
    stop("Retros CSV has no retrospective source columns (expected at least NWS/GloFAS).", call. = FALSE)
  }

  baseline_long <- dplyr::bind_rows(lapply(baseline_cols, function(col) {
    tibble::tibble(
      date = as.Date(retro$Date),
      source_id = mk_source_id(col),
      source_label = baseline_label(col),
      source_family = baseline_family(col),
      discharge_cms = convert_scale_to_cms(as.numeric(retro[[col]]), in_scale)
    )
  }))

  default_extra_sources <- list(
    list(
      source_id = "glofas_hist_v21_htessel_cons",
      source_label = "GloFAS historical v2.1 (HTESSEL-LISFLOOD, consolidated)",
      source_family = "glofas_historical",
      path = "data/glofas_historical_consolidated_point/point_series/hist_v21_htessel_cons_bigtrees.csv",
      date_col = "date",
      value_col = "discharge_cms"
    ),
    list(
      source_id = "glofas_hist_v31_lisflood_cons",
      source_label = "GloFAS historical v3.1 (LISFLOOD, consolidated)",
      source_family = "glofas_historical",
      path = "data/glofas_historical_consolidated_point/point_series/hist_v31_lisflood_cons_bigtrees.csv",
      date_col = "date",
      value_col = "discharge_cms"
    ),
    list(
      source_id = "glofas_hist_v40_lisflood_cons",
      source_label = "GloFAS historical v4.0 (LISFLOOD, consolidated)",
      source_family = "glofas_historical",
      path = "data/glofas_historical_consolidated_point/point_series/hist_v40_lisflood_cons_bigtrees.csv",
      date_col = "date",
      value_col = "discharge_cms"
    ),
    list(
      source_id = "glofas_legacy_reanalysis_v30",
      source_label = "GloFAS legacy reanalysis v3.0",
      source_family = "glofas_legacy_reanalysis",
      path = "data/glofas_legacy_global/point_series/dis_1980_2018_v3_legacy_bigtrees.csv",
      date_col = "date",
      value_col = "discharge_cms"
    ),
    list(
      source_id = "nws_retro_v20",
      source_label = "NWS retrospective v2.0",
      source_family = "nwm_retrospective",
      path = "repro/nwm_retrospective_runs/nwm_retrospective_campaign_20260218T024352Z/point_series/v20_full_daily.csv",
      date_col = "date",
      value_col = "streamflow_cms"
    ),
    list(
      source_id = "nws_retro_v21",
      source_label = "NWS retrospective v2.1",
      source_family = "nwm_retrospective",
      path = "repro/nwm_retrospective_runs/nwm_retrospective_campaign_20260218T024352Z/point_series/v21_full_daily_from_zarr.csv",
      date_col = "date",
      value_col = "streamflow_cms"
    ),
    list(
      source_id = "nws_retro_v30",
      source_label = "NWS retrospective v3.0",
      source_family = "nwm_retrospective",
      path = "repro/nwm_retrospective_runs/nwm_retrospective_campaign_20260218T024352Z/point_series/v30_full_daily_from_zarr.csv",
      date_col = "date",
      value_col = "streamflow_cms"
    ),
    list(
      source_id = "nws_synth_retro_ens_mean",
      source_label = "NWS synthetic retrospective (ensemble mean)",
      source_family = "nwm_retrospective",
      path = "data/nwm_synthetic_retrospective/point_series/nws_synthetic_retro_ensemble_mean_daily.csv",
      date_col = "date",
      value_col = "discharge_cms"
    )
  )

  configured_extra <- cfg$inputs$retros$extra_sources %||% default_extra_sources
  extras_long <- list()
  for (spec in configured_extra) {
    p <- as_abs_path(spec$path %||% "")
    if (!nzchar(p) || !file.exists(p)) next

    date_col <- spec$date_col %||% "date"
    value_col <- spec$value_col %||% "discharge_cms"
    src_id <- spec$source_id %||% mk_source_id(basename(p))
    src_label <- spec$source_label %||% src_id
    src_family <- spec$source_family %||% "historical_or_reanalysis"

    ext <- tryCatch(
      readr::read_csv(p, show_col_types = FALSE),
      error = function(e) NULL
    )
    if (is.null(ext)) {
      cat(sprintf("[WARN] Could not read extra retrospective source: %s\n", p))
      next
    }
    if (!(date_col %in% names(ext)) || !(value_col %in% names(ext))) {
      cat(sprintf("[WARN] Extra source missing required columns (%s, %s): %s\n", date_col, value_col, p))
      next
    }

    extras_long[[length(extras_long) + 1L]] <- tibble::tibble(
      date = as.Date(ext[[date_col]]),
      source_id = as.character(src_id),
      source_label = as.character(src_label),
      source_family = as.character(src_family),
      discharge_cms = as.numeric(ext[[value_col]])
    )
  }

  out <- dplyr::bind_rows(c(list(baseline_long), extras_long)) %>%
    filter(!is.na(date), !is.na(discharge_cms))

  # Keep stable row order for reproducibility.
  out <- out %>% arrange(source_id, date)

  readr::write_csv(out, retros_cache_path)
  cat(sprintf("[OK] wrote %s (%d rows)\n", retros_cache_path, nrow(out)))
  out
}

select_window_for_cutoff <- function(windows, cutoff_date) {
  if (is.null(windows) || length(windows) == 0) return(NULL)
  d <- as.Date(cutoff_date)
  for (w in windows) {
    s <- as.Date(as.character(w$start %||% "1900-01-01"))
    e <- as.Date(as.character(w$end %||% "2999-12-31"))
    if (is.na(s) || is.na(e)) next
    if (d >= s && d <= e) return(w)
  }
  NULL
}

select_source_for_cutoff <- function(windows, cutoff_date) {
  w <- select_window_for_cutoff(windows, cutoff_date)
  if (is.null(w)) return(NA_character_)
  src <- as.character(w$source_id %||% "")
  if (!nzchar(src)) return(NA_character_)
  src
}

apply_retros_selection_policy <- function(retros_df, cutoff_date, policy) {
  if (is.null(policy) || nrow(retros_df) == 0) return(retros_df)

  keep_ids <- as.character(unlist(policy$keep_source_ids %||% character(0)))
  keep_ids <- c(
    keep_ids,
    select_source_for_cutoff(policy$glofas_by_cutoff_windows, cutoff_date),
    select_source_for_cutoff(policy$nws_by_cutoff_windows, cutoff_date)
  )
  keep_ids <- unique(keep_ids[!is.na(keep_ids) & nzchar(keep_ids)])

  if (length(keep_ids) == 0) {
    return(retros_df[0, ])
  }
  retros_df %>% filter(source_id %in% keep_ids)
}

extract_retros_source_series <- function(retros_all, source_id, cutoff_date, role_label) {
  sid <- as.character(source_id)
  out <- retros_all %>%
    filter(source_id == sid, date <= as.Date(cutoff_date)) %>%
    arrange(date)

  if (nrow(out) == 0) {
    available <- paste(sort(unique(retros_all$source_id)), collapse = ", ")
    stop(
      sprintf(
        paste0(
          "Missing retrospective source '%s' required for %s at cutoff=%s. ",
          "Available source_id values in retros cache: %s"
        ),
        sid,
        role_label,
        format(as.Date(cutoff_date), "%Y-%m-%d"),
        available
      ),
      call. = FALSE
    )
  }
  out
}

extract_retros_source_series_optional <- function(retros_all, source_id, cutoff_date) {
  sid <- as.character(source_id %||% "")
  if (!nzchar(sid)) return(tibble::tibble(date = as.Date(character()), discharge_cms = numeric()))
  retros_all %>%
    filter(source_id == sid, date <= as.Date(cutoff_date)) %>%
    arrange(date)
}

build_nws_daily_latest_target_table <- function(n_fc_root) {
  files <- sort(Sys.glob(file.path(n_fc_root, "cutoff_date=*", "nws_members.csv")))
  if (length(files) == 0) {
    return(tibble::tibble(
      date = as.Date(character()),
      issue_date = as.Date(character()),
      fallback_discharge_cms = numeric(),
      members_used = integer(),
      lead_days = integer()
    ))
  }

  rows <- list()
  warn_count <- 0L
  for (p in files) {
    issue_token <- basename(dirname(p))
    issue_str <- sub("^cutoff_date=", "", issue_token)
    issue_date <- as.Date(issue_str)
    if (is.na(issue_date)) {
      warn_count <- warn_count + 1L
      next
    }

    df <- tryCatch(
      readr::read_csv(p, show_col_types = FALSE),
      error = function(e) NULL
    )
    if (is.null(df) || !("target_date" %in% names(df))) {
      warn_count <- warn_count + 1L
      next
    }

    member_cols <- grep("^member_", names(df), value = TRUE)
    if (length(member_cols) == 0) {
      warn_count <- warn_count + 1L
      next
    }

    target_dates <- as.Date(df$target_date)
    m <- as.matrix(df[, member_cols, drop = FALSE])
    suppressWarnings(storage.mode(m) <- "double")
    finite_counts <- rowSums(is.finite(m))
    means <- rowMeans(m, na.rm = TRUE)
    means[finite_counts == 0] <- NA_real_

    rows[[length(rows) + 1L]] <- tibble::tibble(
      date = target_dates,
      issue_date = issue_date,
      fallback_discharge_cms = as.numeric(means),
      members_used = as.integer(finite_counts),
      lead_days = as.integer(target_dates - issue_date)
    ) %>%
      filter(!is.na(date), !is.na(fallback_discharge_cms), lead_days >= 1)
  }

  out <- bind_rows(rows)
  if (nrow(out) == 0) {
    return(tibble::tibble(
      date = as.Date(character()),
      issue_date = as.Date(character()),
      fallback_discharge_cms = numeric(),
      members_used = integer(),
      lead_days = integer()
    ))
  }

  latest <- out %>%
    arrange(date, issue_date) %>%
    group_by(date) %>%
    slice_tail(n = 1) %>%
    ungroup() %>%
    arrange(date)

  if (warn_count > 0L) {
    cat(sprintf("[WARN] NWS fallback builder skipped %d malformed cache files.\n", warn_count))
  }
  latest
}

prepare_auto_retrospective_for_cutoff <- function(retros_all, cutoff_date, policy, plot_start, plot_end, nws_daily_latest = NULL) {
  cutoff_date <- as.Date(cutoff_date)

  validate_cutoff_against_local_origin_span(cutoff_date, policy)

  glofas_window <- select_window_for_cutoff(policy$glofas_family_windows, cutoff_date)
  if (is.null(glofas_window)) {
    stop(
      sprintf("No GloFAS family window matched cutoff_date=%s for automatic retrospective policy.", format(cutoff_date, "%Y-%m-%d")),
      call. = FALSE
    )
  }
  glofas_source_id <- as.character(glofas_window$source_id %||% "")
  if (!nzchar(glofas_source_id)) {
    stop(
      sprintf("GloFAS automatic policy matched cutoff_date=%s but source_id is missing in configured window.", format(cutoff_date, "%Y-%m-%d")),
      call. = FALSE
    )
  }

  nws_window <- select_window_for_cutoff(policy$nws_forecast_windows, cutoff_date)
  if (is.null(nws_window)) {
    stop(
      sprintf("No NWS forecast-version window matched cutoff_date=%s for automatic retrospective policy.", format(cutoff_date, "%Y-%m-%d")),
      call. = FALSE
    )
  }

  nws_primary_source_id <- as.character(policy$nws_primary_source_id %||% "")
  if (!nzchar(nws_primary_source_id)) {
    stop("Automatic retrospective policy requires non-empty nws_primary_source_id.", call. = FALSE)
  }

  glofas_selected <- extract_retros_source_series(
    retros_all = retros_all,
    source_id = glofas_source_id,
    cutoff_date = cutoff_date,
    role_label = "selected_glofas_retrospective"
  )
  nws_primary_selected <- extract_retros_source_series(
    retros_all = retros_all,
    source_id = nws_primary_source_id,
    cutoff_date = cutoff_date,
    role_label = "selected_nws_primary_retrospective"
  )

  min_glofas <- min(glofas_selected$date, na.rm = TRUE)
  min_nws <- min(nws_primary_selected$date, na.rm = TRUE)
  shared_start <- max(min_glofas, min_nws)

  if (is.na(shared_start) || shared_start > cutoff_date) {
    stop(
      sprintf(
        paste0(
          "Computed shared retrospective window is invalid for cutoff=%s. ",
          "min_glofas=%s, min_nws=%s, shared_start=%s."
        ),
        format(cutoff_date, "%Y-%m-%d"),
        format(min_glofas, "%Y-%m-%d"),
        format(min_nws, "%Y-%m-%d"),
        ifelse(is.na(shared_start), "NA", format(shared_start, "%Y-%m-%d"))
      ),
      call. = FALSE
    )
  }

  glofas_trim <- glofas_selected %>%
    filter(date >= shared_start, date <= cutoff_date)
  nws_primary_trim <- nws_primary_selected %>%
    filter(date >= shared_start, date <= cutoff_date) %>%
    select(date, source_id, source_label, source_family, discharge_cms) %>%
    arrange(date)

  dates_full <- tibble::tibble(date = seq.Date(shared_start, cutoff_date, by = "day"))
  nws_fill <- dates_full %>%
    left_join(
      nws_primary_trim %>% transmute(date, nws_synthetic_base_value = discharge_cms),
      by = "date"
    )

  if (isTRUE(policy$use_nws_synthetic_lead_fallback) && !is.null(nws_daily_latest) && nrow(nws_daily_latest) > 0) {
    fallback_slice <- nws_daily_latest %>%
      filter(date >= shared_start, date <= cutoff_date) %>%
      transmute(
        date,
        nws_synthetic_fill_value = fallback_discharge_cms,
        nws_synthetic_fill_issue_date = issue_date,
        nws_synthetic_fill_lead_days = lead_days,
        nws_synthetic_fill_members_used = members_used
      )
    nws_fill <- nws_fill %>%
      left_join(fallback_slice, by = "date")
  } else {
    nws_fill <- nws_fill %>%
      mutate(
        nws_synthetic_fill_value = NA_real_,
        nws_synthetic_fill_issue_date = as.Date(NA),
        nws_synthetic_fill_lead_days = NA_integer_,
        nws_synthetic_fill_members_used = NA_integer_
      )
  }

  nws_fill <- nws_fill %>%
    mutate(
      selected_nws_synthetic_value = dplyr::coalesce(nws_synthetic_base_value, nws_synthetic_fill_value),
      nws_synthetic_filled_flag = is.na(nws_synthetic_base_value) & !is.na(nws_synthetic_fill_value),
      nws_synthetic_unresolved_flag = is.na(selected_nws_synthetic_value)
    )

  unresolved_dates <- nws_fill$date[nws_fill$nws_synthetic_unresolved_flag]
  if (length(unresolved_dates) > 0 && isTRUE(policy$fail_on_unresolved_nws_synthetic)) {
    stop(
      sprintf(
        paste0(
          "NWS synthetic retrospective remains unresolved after lead fallback for cutoff=%s. ",
          "Unresolved dates: %s. This indicates missing forecast origins longer than available lead horizon."
        ),
        format(cutoff_date, "%Y-%m-%d"),
        format_date_vec(unresolved_dates)
      ),
      call. = FALSE
    )
  }

  nws_primary_trim <- nws_fill %>%
    transmute(
      date = date,
      source_id = as.character(nws_primary_source_id),
      source_label = "NWS synthetic retrospective (ensemble mean, filled)",
      source_family = "nwm_retrospective",
      discharge_cms = selected_nws_synthetic_value
    )

  prep_table <- dates_full %>%
    left_join(
      glofas_trim %>% transmute(date, selected_glofas_retrospective_value = discharge_cms),
      by = "date"
    ) %>%
    left_join(
      nws_fill %>%
        transmute(
          date,
          selected_nws_synthetic_value = selected_nws_synthetic_value,
          selected_nws_synthetic_base_value = nws_synthetic_base_value,
          selected_nws_synthetic_fill_value = nws_synthetic_fill_value,
          selected_nws_synthetic_fill_issue_date = as.character(nws_synthetic_fill_issue_date),
          selected_nws_synthetic_fill_lead_days = as.integer(nws_synthetic_fill_lead_days),
          selected_nws_synthetic_filled_flag = as.logical(nws_synthetic_filled_flag),
          selected_nws_synthetic_unresolved_flag = as.logical(nws_synthetic_unresolved_flag),
          selected_nws_synthetic_fill_members_used = as.integer(nws_synthetic_fill_members_used)
        ),
      by = "date"
    ) %>%
    mutate(
      shared_window_flag = !is.na(selected_glofas_retrospective_value) & !is.na(selected_nws_synthetic_value),
      selected_glofas_source_id = glofas_source_id,
      selected_glofas_version_label = as.character(glofas_window$historical_version_label %||% NA_character_),
      selected_glofas_forecast_family = as.character(glofas_window$forecast_family %||% NA_character_),
      selected_nws_primary_source_id = nws_primary_source_id,
      selected_nws_forecast_version_label = as.character(nws_window$forecast_version_label %||% NA_character_),
      cutoff_date = format(cutoff_date, "%Y-%m-%d")
    )

  retros_selected <- bind_rows(glofas_trim, nws_primary_trim) %>%
    arrange(source_id, date)
  retros_for_plot <- retros_selected %>%
    filter(date >= as.Date(plot_start), date <= as.Date(plot_end))

  nws_same <- extract_retros_source_series_optional(
    retros_all,
    as.character(nws_window$same_version_source_id %||% ""),
    cutoff_date
  ) %>%
    filter(date >= shared_start)
  nws_next <- extract_retros_source_series_optional(
    retros_all,
    as.character(nws_window$next_version_source_id %||% ""),
    cutoff_date
  ) %>%
    filter(date >= shared_start)

  nws_hybrid_diag <- dates_full %>%
    left_join(
      nws_same %>% transmute(date, nws_same_version_value = discharge_cms),
      by = "date"
    ) %>%
    left_join(
      nws_next %>% transmute(date, nws_next_version_value = discharge_cms),
      by = "date"
    ) %>%
    left_join(
      nws_fill %>%
        transmute(
          date,
          nws_synthetic_base_value = nws_synthetic_base_value,
          nws_synthetic_filled_value = selected_nws_synthetic_value,
          nws_synthetic_fill_issue_date = as.character(nws_synthetic_fill_issue_date),
          nws_synthetic_fill_lead_days = as.integer(nws_synthetic_fill_lead_days)
        ),
      by = "date"
    ) %>%
    mutate(
      nws_hybrid_value = dplyr::coalesce(nws_same_version_value, nws_next_version_value, nws_synthetic_filled_value),
      nws_hybrid_source = dplyr::case_when(
        !is.na(nws_same_version_value) ~ "same_version_retrospective",
        !is.na(nws_next_version_value) ~ "next_version_retrospective_gap_fill",
        !is.na(nws_synthetic_filled_value) ~ "synthetic_from_latest_available_issue",
        TRUE ~ "missing"
      ),
      selected_nws_forecast_version_label = as.character(nws_window$forecast_version_label %||% NA_character_),
      selected_nws_same_version_source_id = as.character(nws_window$same_version_source_id %||% NA_character_),
      selected_nws_next_version_source_id = as.character(nws_window$next_version_source_id %||% NA_character_),
      selected_nws_primary_source_id = nws_primary_source_id,
      cutoff_date = format(cutoff_date, "%Y-%m-%d")
    )

  list(
    retros_for_plot = retros_for_plot,
    retros_selected = retros_selected,
    prep_table = prep_table,
    nws_hybrid_diagnostic = nws_hybrid_diag,
    policy_info = list(
      mode = "automatic_cutoff_policy",
      shared_start = format(shared_start, "%Y-%m-%d"),
      selected_glofas_source_id = glofas_source_id,
      selected_glofas_version_label = as.character(glofas_window$historical_version_label %||% NA_character_),
      selected_glofas_forecast_family = as.character(glofas_window$forecast_family %||% NA_character_),
      selected_nws_primary_source_id = nws_primary_source_id,
      selected_nws_forecast_version_label = as.character(nws_window$forecast_version_label %||% NA_character_),
      selected_nws_same_version_source_id = as.character(nws_window$same_version_source_id %||% NA_character_),
      selected_nws_next_version_source_id = as.character(nws_window$next_version_source_id %||% NA_character_),
      nws_synthetic_fill_count = as.integer(sum(nws_fill$nws_synthetic_filled_flag, na.rm = TRUE)),
      nws_synthetic_unresolved_count = as.integer(sum(nws_fill$nws_synthetic_unresolved_flag, na.rm = TRUE))
    )
  )
}

render_mode <- function(cfg, cutoff_dates, batch_root, shard_tag) {
  out_root <- as_abs_path(cfg$run$out_root)
  site_id <- as.character(cfg$site$usgs_site)
  run_id <- as.character(cfg$run$run_id)
  pre_days <- as.integer(cfg$dates$plot_pre_days %||% 18)
  post_days <- as.integer(cfg$dates$plot_post_days %||% 28)
  auto_cutoff_policy <- resolve_auto_cutoff_policy(cfg$inputs$retros$automatic_cutoff_policy %||% NULL)

  if (isTRUE(auto_cutoff_policy$enabled)) {
    cat(
      sprintf(
        paste0(
          "[INFO] automatic cutoff retrospective policy enabled | ",
          "origin_span=[%s,%s]\n"
        ),
        format(auto_cutoff_policy$forecast_origin_min, "%Y-%m-%d"),
        format(auto_cutoff_policy$forecast_origin_max, "%Y-%m-%d")
      )
    )
    cat(
      sprintf(
        "[INFO] known missing forecast-origin dates: %s\n",
        format_date_vec(auto_cutoff_policy$known_missing_origin_dates)
      )
    )
    for (cutoff in cutoff_dates) {
      validate_cutoff_against_local_origin_span(as.Date(cutoff), auto_cutoff_policy)
    }
  } else {
    cat("[INFO] automatic cutoff retrospective policy disabled; using configured manual selection policy if provided.\n")
  }

  fc_root <- file.path(batch_root, "forecast_cache")
  g_fc_root <- file.path(fc_root, "glofas")
  n_fc_root <- file.path(fc_root, "nws")

  # Cache shared inputs once (per shard).
  max_plot_end <- max(as.Date(cutoff_dates) + post_days)
  cache_dir <- file.path(batch_root, "cache")
  ensure_dir(cache_dir)
  usgs_cache_path <- file.path(cache_dir, "usgs_daily.csv")
  retros_cache_path <- file.path(cache_dir, "retros_daily_cms.csv")

  usgs_all <- fetch_usgs_cache(cfg, usgs_cache_path, max_plot_end)
  retros_all <- build_retros_cache(cfg, retros_cache_path, max_plot_end)
  agg_scale <- cfg$processing$aggregation_scale_internal %||% "log1p_cms"
  retros_selection_policy <- cfg$inputs$retros$selection_policy %||% NULL
  nws_daily_latest <- NULL
  if (isTRUE(auto_cutoff_policy$enabled) && isTRUE(auto_cutoff_policy$use_nws_synthetic_lead_fallback)) {
    nws_daily_latest <- build_nws_daily_latest_target_table(n_fc_root)
    if (!is.null(nws_daily_latest) && nrow(nws_daily_latest) > 0) {
      cat(
        sprintf(
          paste0(
            "[INFO] NWS synthetic lead-fallback table ready | rows=%d | ",
            "coverage=[%s,%s] | max_lead_days=%d\n"
          ),
          nrow(nws_daily_latest),
          format(min(nws_daily_latest$date, na.rm = TRUE), "%Y-%m-%d"),
          format(max(nws_daily_latest$date, na.rm = TRUE), "%Y-%m-%d"),
          as.integer(max(nws_daily_latest$lead_days, na.rm = TRUE))
        )
      )
    } else {
      cat("[WARN] NWS synthetic lead-fallback is enabled but no daily forecast-cache table could be built.\n")
    }
  }

  retros_coverage <- retros_all %>%
    group_by(source_id, source_label, source_family) %>%
    summarise(
      coverage_start = min(date, na.rm = TRUE),
      coverage_end = max(date, na.rm = TRUE),
      n_points = n(),
      .groups = "drop"
    ) %>%
    arrange(source_family, source_label)
  retros_coverage_list <- lapply(seq_len(nrow(retros_coverage)), function(i) {
    row <- retros_coverage[i, ]
    list(
      source_id = as.character(row$source_id),
      source_label = as.character(row$source_label),
      source_family = as.character(row$source_family),
      coverage_start = format(as.Date(row$coverage_start), "%Y-%m-%d"),
      coverage_end = format(as.Date(row$coverage_end), "%Y-%m-%d"),
      n_points = as.integer(row$n_points)
    )
  })

  # Load plotting function without running its CLI.
  source(file.path(getwd(), "scripts", "forecats_plot_bundle.R"))

  # Manifest (shard-local to avoid contention).
  manifest_path <- file.path(batch_root, paste0("batch_manifest", shard_tag, ".csv"))
  if (!file.exists(manifest_path)) {
    readr::write_csv(tibble::tibble(
      cutoff_date = character(),
      status = character(),
      bundle_dir = character(),
      seconds = numeric(),
      note = character(),
      timestamp_utc = character()
    ), manifest_path)
  }
  append_manifest <- function(row_df) {
    # Append a single-row data.frame to an existing CSV written by readr::write_csv().
    utils::write.table(
      row_df,
      file = manifest_path,
      sep = ",",
      row.names = FALSE,
      col.names = FALSE,
      append = TRUE,
      quote = TRUE
    )
  }

  git_hash <- tryCatch(system("git rev-parse HEAD", intern = TRUE), error = function(e) "UNKNOWN")

  for (cutoff in cutoff_dates) {
    t0 <- Sys.time()
    cutoff <- as.Date(cutoff)
    cutoff_str <- format(cutoff, "%Y-%m-%d")
    plot_start <- cutoff - pre_days
    plot_end <- cutoff + post_days
    forecast_start <- cutoff + 1

    bundle_dir <- file.path(
      out_root,
      paste0("site=", site_id),
      paste0("cutoff_date=", cutoff_str),
      paste0("run_id=", run_id)
    )
    inputs_dir <- file.path(bundle_dir, "inputs")
    figures_dir <- file.path(bundle_dir, "figures")
    logs_dir <- file.path(bundle_dir, "logs")

    fig_path <- file.path(figures_dir, "forecats.png")
    if (file.exists(fig_path) && !isTRUE(cfg$run$overwrite) && file.info(fig_path)$size > 0) {
      row <- tibble::tibble(
        cutoff_date = cutoff_str,
        status = "skipped_exists",
        bundle_dir = bundle_dir,
        seconds = as.numeric(difftime(Sys.time(), t0, units = "secs")),
        note = "",
        timestamp_utc = format(as.POSIXct(Sys.time(), tz = "UTC"), "%Y-%m-%dT%H:%M:%S")
      )
      append_manifest(row)
      next
    }

    # Forecast cache inputs must exist.
    g_cache <- file.path(g_fc_root, paste0("issue_date=", cutoff_str), "glofas_members.csv")
    n_cache <- file.path(n_fc_root, paste0("cutoff_date=", cutoff_str), "nws_members.csv")
    if (!file.exists(g_cache) || !file.exists(n_cache)) {
      note <- paste0(
        if (!file.exists(g_cache)) "missing_glofas_cache " else "",
        if (!file.exists(n_cache)) "missing_nws_cache" else ""
      )
      row <- tibble::tibble(
        cutoff_date = cutoff_str,
        status = "waiting_forecast_cache",
        bundle_dir = bundle_dir,
        seconds = as.numeric(difftime(Sys.time(), t0, units = "secs")),
        note = trimws(note),
        timestamp_utc = format(as.POSIXct(Sys.time(), tz = "UTC"), "%Y-%m-%dT%H:%M:%S")
      )
      append_manifest(row)
      next
    }

    # Prepare bundle dirs.
    ensure_dir(inputs_dir)
    ensure_dir(figures_dir)
    ensure_dir(logs_dir)

    # Write window-sliced USGS and retros inputs (cms).
    usgs_out <- file.path(inputs_dir, "usgs_daily.csv")
    retros_out <- file.path(inputs_dir, "retros_daily.csv")
    retros_prep_out <- file.path(inputs_dir, "retrospective_preparation.csv")
    retros_hybrid_out <- file.path(inputs_dir, "retrospective_nws_hybrid_diagnostic.csv")

    usgs_slice <- usgs_all %>% filter(date >= plot_start & date <= plot_end)
    readr::write_csv(usgs_slice, usgs_out)

    retros_policy_info <- list(mode = "manual_selection_policy")
    if (isTRUE(auto_cutoff_policy$enabled)) {
      auto_retros <- prepare_auto_retrospective_for_cutoff(
        retros_all = retros_all,
        cutoff_date = cutoff,
        policy = auto_cutoff_policy,
        plot_start = plot_start,
        plot_end = plot_end,
        nws_daily_latest = nws_daily_latest
      )
      retros_slice <- auto_retros$retros_for_plot
      readr::write_csv(auto_retros$prep_table, retros_prep_out)
      if (isTRUE(auto_cutoff_policy$write_nws_hybrid_diagnostic)) {
        readr::write_csv(auto_retros$nws_hybrid_diagnostic, retros_hybrid_out)
      }
      retros_policy_info <- auto_retros$policy_info
    } else {
      retros_slice <- retros_all %>% filter(date >= plot_start & date <= plot_end)
      retros_slice <- apply_retros_selection_policy(retros_slice, cutoff, retros_selection_policy)
      prep_fallback <- retros_slice %>%
        group_by(date) %>%
        summarise(
          selected_glofas_retrospective_value = suppressWarnings(first(discharge_cms[grepl("glofas", source_id, ignore.case = TRUE)])),
          selected_nws_synthetic_value = suppressWarnings(first(discharge_cms[source_id == "nws_synth_retro_ens_mean"])),
          shared_window_flag = !is.na(selected_glofas_retrospective_value) & !is.na(selected_nws_synthetic_value),
          selected_glofas_source_id = NA_character_,
          selected_glofas_version_label = NA_character_,
          selected_glofas_forecast_family = NA_character_,
          selected_nws_primary_source_id = NA_character_,
          selected_nws_forecast_version_label = NA_character_,
          cutoff_date = cutoff_str,
          .groups = "drop"
        ) %>%
        arrange(date)
      readr::write_csv(prep_fallback, retros_prep_out)
    }
    readr::write_csv(retros_slice, retros_out)

    # Copy cached forecast CSVs into bundle inputs (names expected by plotter).
    file.copy(g_cache, file.path(inputs_dir, "glofas_weighted_daily.csv"), overwrite = TRUE)
    file.copy(n_cache, file.path(inputs_dir, "nws_weighted_daily.csv"), overwrite = TRUE)

    # Meta.yaml (minimal but compatible with plotter).
    meta <- list(
      run = list(
        run_id = run_id,
        created = format(Sys.time(), "%Y-%m-%d %H:%M:%S"),
        git_commit = git_hash
      ),
      processing = list(
        storage_unit = "cms",
        bias_correction = FALSE,
        scale_correction = FALSE,
        weighting_scale_internal = as.character(agg_scale)
      ),
      site = cfg$site,
      dates = list(
        cutoff_date = cutoff_str,
        forecast_start_date = format(forecast_start, "%Y-%m-%d"),
        plot_start = format(plot_start, "%Y-%m-%d"),
        plot_end = format(plot_end, "%Y-%m-%d")
      ),
      transforms = cfg$transforms,
      paths = list(
        usgs_daily = "usgs_daily.csv",
        retros_daily = "retros_daily.csv",
        retrospective_preparation = "retrospective_preparation.csv",
        retrospective_nws_hybrid_diagnostic = if (file.exists(retros_hybrid_out)) "retrospective_nws_hybrid_diagnostic.csv" else NA,
        glofas_weighted_daily = "glofas_weighted_daily.csv",
        nws_weighted_daily = "nws_weighted_daily.csv"
      ),
      plot = cfg$plot %||% list(),
      config = cfg
    )
    meta$retrospective_coverage <- retros_coverage_list
    meta$retrospective_policy <- retros_policy_info

    # Ensure cutoff marker exists.
    if (is.null(meta$plot$markers) || length(meta$plot$markers) == 0) {
      meta$plot$markers <- list(list(date = cutoff_str, label = "Cutoff", color = "gray40"))
    }

    meta_path <- file.path(bundle_dir, "meta.yaml")
    writeLines(yaml::as.yaml(meta), meta_path)

    # Plot
    status <- "success"
    note <- ""
    tryCatch(
      {
        plot_forecats_bundle(bundle_dir)
      },
      error = function(e) {
        status <<- "error"
        note <<- substr(as.character(e$message), 1, 200)
      }
    )

    row <- tibble::tibble(
      cutoff_date = cutoff_str,
      status = status,
      bundle_dir = bundle_dir,
      seconds = as.numeric(difftime(Sys.time(), t0, units = "secs")),
      note = note,
      timestamp_utc = format(as.POSIXct(Sys.time(), tz = "UTC"), "%Y-%m-%dT%H:%M:%S")
    )
    append_manifest(row)

    if (status != "success") {
      cat(sprintf("[ERR] %s: %s\n", cutoff_str, note))
    } else {
      cat(sprintf("[OK ] %s -> %s\n", cutoff_str, fig_path))
    }
  }

  cat(sprintf("[DONE] wrote manifest: %s\n", manifest_path))
}

main <- function(config_path, mode, shard_count, shard_index, providers = "all") {
  cfg <- yaml::read_yaml(config_path)

  stop_if_missing(cfg$run$out_root, "Missing run.out_root in config")
  stop_if_missing(cfg$run$cache_root, "Missing run.cache_root in config")
  stop_if_missing(cfg$run$run_id, "Missing run.run_id in config")
  stop_if_missing(cfg$site$usgs_site, "Missing site.usgs_site in config")

  cutoff_all <- compute_cutoff_dates(cfg)

  shard_count <- as.integer(shard_count)
  shard_index <- as.integer(shard_index)
  if (is.na(shard_count) || shard_count < 1) shard_count <- 1L
  if (is.na(shard_index) || shard_index < 0) shard_index <- 0L
  if (shard_index >= shard_count) stop("--shard-index must be < --shard-count", call. = FALSE)

  cutoff <- apply_shard(cutoff_all, shard_count, shard_index)

  shard_tag <- ""
  if (shard_count > 1) shard_tag <- sprintf(".shard%02dof%02d", shard_index, shard_count)

  batch_root <- file.path(
    as_abs_path(cfg$run$cache_root),
    paste0("site=", as.character(cfg$site$usgs_site)),
    paste0("run_id=", as.character(cfg$run$run_id))
  )
  ensure_dir(batch_root)

  # Keep a copy of the batch config for provenance.
  file.copy(config_path, file.path(batch_root, "batch_config.yaml"), overwrite = TRUE)

  cat(sprintf("MODE=%s | cutoffs_total=%d | shard=%d/%d => n=%d\n", mode, length(cutoff_all), shard_index, shard_count, length(cutoff)))
  cat(sprintf("BATCH_ROOT=%s\n", batch_root))

  if (mode == "audit") {
    audit_mode(cfg, cutoff, batch_root, shard_tag)
  } else if (mode == "build-forecasts") {
    build_forecasts_mode(cfg, cutoff, batch_root, shard_tag, providers = providers)
  } else if (mode == "render") {
    render_mode(cfg, cutoff, batch_root, shard_tag)
  } else {
    stop("Unknown --mode. Use audit | build-forecasts | render", call. = FALSE)
  }
}

if (sys.nframe() == 0) {
  argv <- commandArgs(trailingOnly = TRUE)
  args <- parse_args(argv)
  if (is.null(args$config) || is.null(args$mode)) {
    stop("Usage: scripts/forecats_batch.R --config <yaml> --mode <audit|build-forecasts|render>", call. = FALSE)
  }
  main(
    config_path = as_abs_path(args$config),
    mode = as.character(args$mode),
    shard_count = args$`shard-count` %||% 1,
    shard_index = args$`shard-index` %||% 0,
    providers = args$providers %||% "all"
  )
}
