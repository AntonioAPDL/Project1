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
          usgs_cms = as.numeric(usgs_cms),
          glofas_cms = as.numeric(glofas_cms),
          nws_cms = as.numeric(nws_cms)
        ),
      error = function(e) NULL
    )

    if (!is.null(cached) && ("date" %in% names(cached))) {
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

  nws_col <- NULL
  if ("NWS3.0" %in% names(retro)) nws_col <- "NWS3.0"
  if ("NWS" %in% names(retro)) nws_col <- "NWS"
  if (is.null(nws_col)) stop("Retros CSV missing NWS column (expected NWS3.0 or NWS).", call. = FALSE)

  convert_scale_to_cms <- function(x, scale) {
    if (scale == "raw_cms") return(x)
    if (scale == "log1p_cms") return(exp(x) - 1)
    stop(paste("Unknown scale:", scale))
  }

  out <- tibble::tibble(
    date = as.Date(retro$Date),
    usgs_cms = convert_scale_to_cms(retro$USGS, in_scale),
    glofas_cms = convert_scale_to_cms(retro$GloFAS, in_scale),
    nws_cms = convert_scale_to_cms(retro[[nws_col]], in_scale)
  ) %>% filter(date <= as.Date(plot_end))

  readr::write_csv(out, retros_cache_path)
  cat(sprintf("[OK] wrote %s (%d rows)\n", retros_cache_path, nrow(out)))
  out
}

render_mode <- function(cfg, cutoff_dates, batch_root, shard_tag) {
  out_root <- as_abs_path(cfg$run$out_root)
  site_id <- as.character(cfg$site$usgs_site)
  run_id <- as.character(cfg$run$run_id)
  pre_days <- as.integer(cfg$dates$plot_pre_days %||% 18)
  post_days <- as.integer(cfg$dates$plot_post_days %||% 28)

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

    usgs_slice <- usgs_all %>% filter(date >= plot_start & date <= plot_end)
    readr::write_csv(usgs_slice, usgs_out)

    retros_slice <- retros_all %>% filter(date >= plot_start & date <= plot_end)
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
        weighting_scale_internal = "log1p_cms"
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
        glofas_weighted_daily = "glofas_weighted_daily.csv",
        nws_weighted_daily = "nws_weighted_daily.csv"
      ),
      plot = cfg$plot %||% list(),
      config = cfg
    )

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
