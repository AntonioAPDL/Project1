#!/usr/bin/env Rscript

# Build a self-contained "forecats" input bundle from config YAML and generate the plot.
#
# Usage:
#   Rscript scripts/forecats_pipeline.R --config config/forecats_pipeline.yaml
#
# Output layout:
#   <out_root>/site=<USGS_SITE>/cutoff_date=<YYYY-MM-DD>/run_id=<RUN_ID>/
#     meta.yaml
#     inputs/*.csv
#     figures/forecats.png
#     logs/pipeline.log
#
# Notes:
# - This pipeline stores all flows in *raw cms* (m^3/s) in the bundle CSVs.
# - Forecast weighting is performed on log1p(cms) internally (per notebooks),
#   but outputs are inverted back to cms for storage.

suppressPackageStartupMessages({
  library(yaml)
  library(readr)
  library(dplyr)
  library(dataRetrieval)
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

stop_if_missing <- function(x, msg) {
  if (is.null(x) || identical(x, "")) stop(msg, call. = FALSE)
}

as_abs_path <- function(p) {
  # Resolve relative to repo root (cwd)
  if (is.null(p)) return(NULL)
  if (startsWith(p, "/")) return(p)
  normalizePath(file.path(getwd(), p), mustWork = FALSE)
}

convert_scale_to_cms <- function(x, scale) {
  if (scale == "raw_cms") return(x)
  if (scale == "log1p_cms") return(exp(x) - 1)
  stop(paste("Unknown scale:", scale))
}

ensure_dir <- function(p) dir.create(p, showWarnings = FALSE, recursive = TRUE)

fmt_num_for_id <- function(x) {
  x <- suppressWarnings(as.numeric(x))
  if (is.na(x)) return("na")
  sign <- if (x < 0) "m" else ""
  x <- abs(x)
  s <- format(x, trim = TRUE, scientific = FALSE)
  s <- gsub("\\.", "p", s)
  paste0(sign, s)
}

short_scale_for_id <- function(scale) {
  switch(
    scale,
    raw_cms = "raw",
    log1p_cms = "log1p",
    log_log1p_cms = "loglog",
    as.character(scale)
  )
}

slugify_id <- function(x) {
  # Keep file/path-safe characters only.
  gsub("[^A-Za-z0-9_.-]+", "_", x)
}

auto_run_id <- function(cfg, cutoff_date) {
  ts <- format(Sys.time(), "%Y%m%d_%H%M%S")
  scale <- short_scale_for_id(cfg$transforms$plot_scale %||% "log_log1p_cms")

  g_scheme <- cfg$inputs$glofas$weighting$scheme %||% "latest"
  g_alpha <- cfg$inputs$glofas$weighting$alpha %||% 1.0
  g_power <- cfg$inputs$glofas$weighting$power %||% -1.001
  g_tag <- if (g_scheme == "paper") paste0("a", fmt_num_for_id(g_alpha)) else if (g_scheme == "notebook") {
    paste0("pow", fmt_num_for_id(g_power))
  } else {
    g_scheme
  }

  n_scheme <- cfg$inputs$nws$weighting$scheme %||% "latest"
  n_alpha <- cfg$inputs$nws$weighting$alpha %||% 1.0
  n_tag <- if (n_scheme == "paper") paste0("a", fmt_num_for_id(n_alpha)) else {
    n_scheme
  }

  part <- function(prefix, scheme, tag) {
    if (is.null(tag) || tag == "" || tag == scheme) {
      return(paste0(prefix, "-", scheme))
    }
    paste0(prefix, "-", scheme, "-", tag)
  }

  id <- paste0(
    ts,
    "_cutoff", format(cutoff_date, "%Y-%m-%d"),
    "_", part("glofas", g_scheme, g_tag),
    "_", part("nws", n_scheme, n_tag),
    "_scale-", scale
  )
  slugify_id(id)
}

run_cmd <- function(cmd) {
  cat("[CMD] ", cmd, "\n", sep = "")
  rc <- system(cmd)
  if (!identical(rc, 0L)) stop(paste("Command failed:", cmd), call. = FALSE)
  invisible(TRUE)
}

main <- function(config_path) {
  cfg <- yaml::read_yaml(config_path)

  stop_if_missing(cfg$run$out_root, "Missing run.out_root in config")
  stop_if_missing(cfg$site$usgs_site, "Missing site.usgs_site in config")
  stop_if_missing(cfg$dates$cutoff_date, "Missing dates.cutoff_date in config")
  stop_if_missing(cfg$dates$plot_start, "Missing dates.plot_start in config")
  stop_if_missing(cfg$dates$plot_end, "Missing dates.plot_end in config")

  cutoff_date <- as.Date(cfg$dates$cutoff_date)

  run_id <- cfg$run$run_id
  if (is.null(run_id) || identical(run_id, "")) run_id <- auto_run_id(cfg, cutoff_date)
  plot_start <- as.Date(cfg$dates$plot_start)
  plot_end <- as.Date(cfg$dates$plot_end)
  forecast_start <- cutoff_date + 1

  out_root <- as_abs_path(cfg$run$out_root)
  site_id <- cfg$site$usgs_site

  bundle_dir <- file.path(
    out_root,
    paste0("site=", site_id),
    paste0("cutoff_date=", format(cutoff_date, "%Y-%m-%d")),
    paste0("run_id=", run_id)
  )

  inputs_dir <- file.path(bundle_dir, "inputs")
  figures_dir <- file.path(bundle_dir, "figures")
  logs_dir <- file.path(bundle_dir, "logs")
  cache_dir <- file.path(bundle_dir, "cache")
  ensure_dir(inputs_dir)
  ensure_dir(figures_dir)
  ensure_dir(logs_dir)
  ensure_dir(cache_dir)

  # Logging
  log_path <- file.path(logs_dir, "pipeline.log")
  con <- file(log_path, open = "wt")
  sink(con, split = TRUE)
  cat(sprintf("START: %s\n", format(Sys.time(), "%Y-%m-%d %H:%M:%S")))
  cat(sprintf("CONFIG: %s\n", normalizePath(config_path, mustWork = TRUE)))
  git_hash <- tryCatch(system("git rev-parse HEAD", intern = TRUE), error = function(e) "UNKNOWN")
  cat(sprintf("GIT_COMMIT: %s\n", git_hash))
  cat(sprintf("BUNDLE_DIR: %s\n", bundle_dir))

  overwrite <- isTRUE(cfg$run$overwrite)

  # -------------------------
  # 1) USGS daily (raw cms)
  # -------------------------
  usgs_out <- file.path(inputs_dir, "usgs_daily.csv")
  if (!file.exists(usgs_out) || overwrite) {
    cat("[STEP] USGS fetch\n")
    usgs_cfg <- cfg$site$usgs %||% list()
    start_usgs <- usgs_cfg$start_date %||% "1979-01-01"
    end_usgs <- format(plot_end, "%Y-%m-%d")
    CFSToCMS <- 0.0283168466
    usgs <- dataRetrieval::readNWISdv(
      siteNumbers = site_id,
      parameterCd = usgs_cfg$parameterCd %||% "00060",
      statCd = usgs_cfg$statCd %||% "00003",
      startDate = start_usgs,
      endDate = end_usgs
    )
    # Expected col name: X_00060_00003
    if (!("X_00060_00003" %in% names(usgs))) {
      stop("Unexpected USGS column names; expected X_00060_00003 in readNWISdv output.", call. = FALSE)
    }
    usgs_out_df <- usgs %>%
      transmute(
        date = as.Date(Date),
        discharge_cfs = as.numeric(X_00060_00003),
        discharge_cms = discharge_cfs * CFSToCMS
      )
    readr::write_csv(usgs_out_df, usgs_out)
    cat(sprintf("[OK] wrote %s (%d rows)\n", usgs_out, nrow(usgs_out_df)))
  } else {
    cat(sprintf("[SKIP] USGS exists: %s\n", usgs_out))
  }

  # -------------------------
  # 2) Retros daily (raw cms)
  # -------------------------
  retros_cfg <- cfg$inputs$retros
  stop_if_missing(retros_cfg$path, "Missing inputs.retros.path in config")
  retros_in <- as_abs_path(retros_cfg$path)
  retros_scale <- retros_cfg$scale %||% "log1p_cms"

  retros_out <- file.path(inputs_dir, "retros_daily.csv")
  if (!file.exists(retros_out) || overwrite) {
    cat("[STEP] Retros prepare\n")
    retro <- readr::read_csv(retros_in, show_col_types = FALSE)
    if (!("Date" %in% names(retro))) stop("Retros CSV missing Date column.", call. = FALSE)
    retro <- retro %>% mutate(Date = as.Date(Date)) %>% filter(Date <= cutoff_date)

    # Map legacy columns to standard names.
    if (!("USGS" %in% names(retro))) stop("Retros CSV missing USGS column.", call. = FALSE)
    if (!("GloFAS" %in% names(retro))) stop("Retros CSV missing GloFAS column.", call. = FALSE)
    nws_col <- NULL
    if ("NWS3.0" %in% names(retro)) nws_col <- "NWS3.0"
    if ("NWS" %in% names(retro)) nws_col <- "NWS"
    if (is.null(nws_col)) stop("Retros CSV missing NWS column (expected NWS3.0 or NWS).", call. = FALSE)

    out <- tibble::tibble(
      date = retro$Date,
      usgs_cms = convert_scale_to_cms(retro$USGS, retros_scale),
      glofas_cms = convert_scale_to_cms(retro$GloFAS, retros_scale),
      nws_cms = convert_scale_to_cms(retro[[nws_col]], retros_scale)
    )
    readr::write_csv(out, retros_out)
    cat(sprintf("[OK] wrote %s (%d rows)\n", retros_out, nrow(out)))
  } else {
    cat(sprintf("[SKIP] Retros exists: %s\n", retros_out))
  }

  # -------------------------
  # 3) Forecast ensembles (raw cms) + cell metadata
  # -------------------------
  forecast_start_str <- format(forecast_start, "%Y-%m-%d")
  forecast_end_str <- format(plot_end, "%Y-%m-%d")

  # 3a) GloFAS
  glofas_cfg <- cfg$inputs$glofas
  stop_if_missing(glofas_cfg$source, "Missing inputs.glofas.source in config")
  glofas_out <- file.path(inputs_dir, "glofas_weighted_daily.csv")
  glofas_cell_json <- file.path(inputs_dir, "glofas_cell.json")

  if (!file.exists(glofas_out) || overwrite) {
    if (glofas_cfg$source == "csv") {
      stop_if_missing(glofas_cfg$csv$path, "Missing inputs.glofas.csv.path in config")
      in_path <- as_abs_path(glofas_cfg$csv$path)
      in_scale <- glofas_cfg$csv$scale %||% "log1p_cms"
      df <- readr::read_csv(in_path, show_col_types = FALSE) %>%
        mutate(target_date = as.Date(target_date)) %>%
        filter(target_date >= forecast_start & target_date <= plot_end)
      # Convert all members to cms
      member_cols <- setdiff(names(df), "target_date")
      for (c in member_cols) df[[c]] <- convert_scale_to_cms(df[[c]], in_scale)
      # Rename to member_00..member_50 if needed.
      if (all(grepl("^\\d+$", member_cols))) {
        new_names <- paste0("member_", sprintf("%02d", as.integer(member_cols)))
        ren <- setNames(member_cols, new_names) # new -> old (dplyr::rename semantics)
        df <- df %>% rename(!!!ren)
      }
      readr::write_csv(df, glofas_out)
      cat(sprintf("[OK] wrote %s (%d rows)\n", glofas_out, nrow(df)))
    } else if (glofas_cfg$source == "grib") {
      grib_root <- as_abs_path(glofas_cfg$grib$grib_root)
      var <- glofas_cfg$grib$var %||% "dis24"
      control_dtype <- glofas_cfg$grib$data_types$control %||% "cf"
      pert_dtype <- glofas_cfg$grib$data_types$perturbed %||% "pf"
      scheme <- glofas_cfg$weighting$scheme %||% "latest"
      power <- glofas_cfg$weighting$power %||% -1.001
      alpha <- glofas_cfg$weighting$alpha %||% 1.0
      shift_days <- glofas_cfg$weighting$shift_days %||% 1
      lat <- cfg$site$lat
      lon <- cfg$site$lon
      stop_if_missing(grib_root, "Missing inputs.glofas.grib.grib_root")

      cache_glofas <- file.path(cache_dir, "glofas")
      ensure_dir(cache_glofas)

      cmd <- paste(
        "python3",
        shQuote(file.path(getwd(), "scripts", "forecats_build_glofas_weighted.py")),
        "--grib-root", shQuote(grib_root),
        "--cutoff-date", shQuote(format(cutoff_date, "%Y-%m-%d")),
        "--forecast-start-date", shQuote(forecast_start_str),
        "--forecast-end-date", shQuote(forecast_end_str),
        "--lat", shQuote(as.character(lat)),
        "--lon", shQuote(as.character(lon)),
        "--var", shQuote(var),
        "--control-dtype", shQuote(control_dtype),
        "--perturbed-dtype", shQuote(pert_dtype),
        "--weighting-scheme", shQuote(as.character(scheme)),
        "--power", shQuote(as.character(power)),
        "--alpha", shQuote(as.character(alpha)),
        "--shift-days", shQuote(as.character(shift_days)),
        "--cache-dir", shQuote(cache_glofas),
        "--cell-json", shQuote(glofas_cell_json),
        "--out-csv", shQuote(glofas_out),
        if (overwrite) "--overwrite" else "",
        "--verbose"
      )
      run_cmd(cmd)
    } else {
      stop(paste("Unknown inputs.glofas.source:", glofas_cfg$source), call. = FALSE)
    }
  } else {
    cat(sprintf("[SKIP] GloFAS exists: %s\n", glofas_out))
  }

  # 3b) NWS
  nws_cfg <- cfg$inputs$nws
  stop_if_missing(nws_cfg$source, "Missing inputs.nws.source in config")
  nws_out <- file.path(inputs_dir, "nws_weighted_daily.csv")

  if (!file.exists(nws_out) || overwrite) {
    if (nws_cfg$source == "csv") {
      in_path <- as_abs_path(nws_cfg$csv$path)
      in_scale <- nws_cfg$csv$scale %||% "log1p_cms"
      df <- readr::read_csv(in_path, show_col_types = FALSE) %>%
        rename(target_date = Date) %>%
        mutate(target_date = as.Date(target_date)) %>%
        filter(target_date >= forecast_start & target_date <= plot_end)

      member_cols <- setdiff(names(df), "target_date")
      for (c in member_cols) df[[c]] <- convert_scale_to_cms(df[[c]], in_scale)

      # Rename columns like Ensemble_Member_1 -> member_01
      new_names <- c()
      old_names <- c()
      for (c in member_cols) {
        m <- regmatches(c, regexpr("\\d+$", c))
        if (length(m) == 1 && m != "") {
          old_names <- c(old_names, c)
          new_names <- c(new_names, paste0("member_", sprintf("%02d", as.integer(m))))
        }
      }
      if (length(old_names) > 0) {
        ren <- setNames(old_names, new_names) # new -> old
        df <- df %>% rename(!!!ren)
      }

      readr::write_csv(df, nws_out)
      cat(sprintf("[OK] wrote %s (%d rows)\n", nws_out, nrow(df)))
    } else if (nws_cfg$source == "pickle") {
      pkl_path <- as_abs_path(nws_cfg$pickle$path)
      parse_hour <- isTRUE(nws_cfg$pickle$parse_issue_hour)
      lookback_days <- nws_cfg$pickle$issue_lookback_days %||% 40
      scheme <- nws_cfg$weighting$scheme %||% "latest"
      alpha <- nws_cfg$weighting$alpha %||% 1.0
      exps <- nws_cfg$weighting$exponents
      exp_spec <- ""
      if (!is.null(exps) && length(exps) > 0) {
        # Build "1=0,2=0.3,..." string for python.
        exp_parts <- c()
        for (k in names(exps)) exp_parts <- c(exp_parts, paste0(k, "=", as.character(exps[[k]])))
        exp_spec <- paste(exp_parts, collapse = ",")
      }
      if (scheme == "notebook" && (is.null(exps) || length(exps) == 0)) {
        stop("Missing inputs.nws.weighting.exponents (required for notebook weighting)", call. = FALSE)
      }

      cache_nws <- file.path(cache_dir, "nws")
      ensure_dir(cache_nws)

      cmd <- paste(
        "python3",
        shQuote(file.path(getwd(), "scripts", "forecats_build_nws_weighted.py")),
        "--pkl", shQuote(pkl_path),
        "--cutoff-date", shQuote(format(cutoff_date, "%Y-%m-%d")),
        "--forecast-start-date", shQuote(forecast_start_str),
        "--forecast-end-date", shQuote(forecast_end_str),
        "--weighting-scheme", shQuote(as.character(scheme)),
        "--alpha", shQuote(as.character(alpha)),
        if (scheme == "notebook") paste("--exponents", shQuote(exp_spec)) else "",
        if (parse_hour) "--parse-issue-hour" else "",
        "--issue-lookback-days", shQuote(as.character(lookback_days)),
        "--out-csv", shQuote(nws_out),
        if (overwrite) "--overwrite" else "",
        "--verbose"
      )
      run_cmd(cmd)
    } else {
      stop(paste("Unknown inputs.nws.source:", nws_cfg$source), call. = FALSE)
    }
  } else {
    cat(sprintf("[SKIP] NWS exists: %s\n", nws_out))
  }

  # -------------------------
  # 3c) Sanity checks (units/scales)
  # -------------------------
  cat("[STEP] Sanity checks (units/scales)\n")
  summarize_vec <- function(v) {
    v <- as.numeric(v)
    list(
      n = length(v),
      n_na = sum(is.na(v)),
      min = suppressWarnings(min(v, na.rm = TRUE)),
      max = suppressWarnings(max(v, na.rm = TRUE))
    )
  }

  usgs_chk <- readr::read_csv(usgs_out, show_col_types = FALSE)
  retro_chk <- readr::read_csv(retros_out, show_col_types = FALSE)

  cat(sprintf("  - Storage unit: cms (m^3/s)\n"))
  cat(sprintf("  - Weighting scale (forecasts): log1p(cms) internally; inverted to cms for storage\n"))
  cat(sprintf("  - Bias/scale correction: NONE (expected)\n"))

  # USGS range
  s <- summarize_vec(usgs_chk$discharge_cms)
  cat(sprintf("  USGS discharge_cms: n=%d, na=%d, min=%.6g, max=%.6g\n", s$n, s$n_na, s$min, s$max))

  # Retros ranges
  for (nm in c("usgs_cms", "glofas_cms", "nws_cms")) {
    if (!(nm %in% names(retro_chk))) next
    s <- summarize_vec(retro_chk[[nm]])
    cat(sprintf("  Retros %s: n=%d, na=%d, min=%.6g, max=%.6g\n", nm, s$n, s$n_na, s$min, s$max))
  }

  # USGS vs retros(USGS) overlap check (should be extremely close if both are cms)
  cmp <- usgs_chk %>%
    transmute(date = as.Date(date), usgs_nwis_cms = discharge_cms) %>%
    inner_join(
      retro_chk %>% transmute(date = as.Date(date), usgs_retros_cms = usgs_cms),
      by = "date"
    ) %>%
    filter(date <= cutoff_date)
  if (nrow(cmp) > 0) {
    diffs <- abs(cmp$usgs_nwis_cms - cmp$usgs_retros_cms)
    dmax <- suppressWarnings(max(diffs, na.rm = TRUE))
    dmed <- suppressWarnings(median(diffs, na.rm = TRUE))
    cat(sprintf("  USGS vs retros(USGS) |diff|: n=%d, median=%.6g, max=%.6g\n", nrow(cmp), dmed, dmax))
    if (is.finite(dmax) && dmax > 1e-6) {
      cat("  [WARN] USGS vs retros mismatch > 1e-6 cms. Check unit conversions / source consistency.\n")
    }
  } else {
    cat("  [WARN] No overlap rows to compare USGS vs retros.\n")
  }

  # Forecast ranges (over the stored target_date window)
  if (file.exists(glofas_out)) {
    gdf <- readr::read_csv(glofas_out, show_col_types = FALSE)
    gcols <- setdiff(names(gdf), "target_date")
    gvals <- unlist(gdf[, gcols, drop = FALSE], use.names = FALSE)
    s <- summarize_vec(gvals)
    cat(sprintf("  GloFAS forecast cms (all members): n=%d, na=%d, min=%.6g, max=%.6g\n", s$n, s$n_na, s$min, s$max))
    if (any(gvals < 0, na.rm = TRUE)) cat("  [WARN] Negative GloFAS discharge values found (unexpected).\n")
  }
  if (file.exists(nws_out)) {
    ndf <- readr::read_csv(nws_out, show_col_types = FALSE)
    ncols <- setdiff(names(ndf), "target_date")
    nvals <- unlist(ndf[, ncols, drop = FALSE], use.names = FALSE)
    s <- summarize_vec(nvals)
    cat(sprintf("  NWS forecast cms (all members): n=%d, na=%d, min=%.6g, max=%.6g\n", s$n, s$n_na, s$min, s$max))
    if (any(nvals < 0, na.rm = TRUE)) cat("  [WARN] Negative NWS discharge values found (unexpected).\n")
  }

  # -------------------------
  # 4) Write meta.yaml
  # -------------------------
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
      cutoff_date = format(cutoff_date, "%Y-%m-%d"),
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
    plot = cfg$plot,
    config = cfg
  )
  meta_path <- file.path(bundle_dir, "meta.yaml")
  writeLines(yaml::as.yaml(meta), meta_path)
  cat(sprintf("[OK] wrote %s\n", meta_path))

  # -------------------------
  # 5) Plot
  # -------------------------
  if (!isTRUE(cfg$run$no_plot)) {
    cat("[STEP] Plot\n")
    cmd <- paste(
      "Rscript",
      shQuote(file.path(getwd(), "scripts", "forecats_plot_bundle.R")),
      "--bundle-dir",
      shQuote(bundle_dir)
    )
    run_cmd(cmd)
  } else {
    cat("[SKIP] plotting disabled (run.no_plot)\n")
  }

  cat(sprintf("END: %s\n", format(Sys.time(), "%Y-%m-%d %H:%M:%S")))
  sink()
  close(con)
  message("Bundle ready: ", bundle_dir)
  invisible(bundle_dir)
}

`%||%` <- function(x, y) if (is.null(x)) y else x

if (sys.nframe() == 0) {
  argv <- commandArgs(trailingOnly = TRUE)
  args <- parse_args(argv)
  if (is.null(args$config)) {
    stop("Usage: scripts/forecats_pipeline.R --config <path>", call. = FALSE)
  }
  main(as_abs_path(args$config))
}
