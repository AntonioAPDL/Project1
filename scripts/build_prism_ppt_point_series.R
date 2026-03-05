#!/usr/bin/env Rscript

suppressWarnings(options(stringsAsFactors = FALSE))

usage <- function() {
  cat(
    paste(
      "Usage:",
      "Rscript --vanilla scripts/build_prism_ppt_point_series.R [options]",
      "",
      "Options:",
      "  --start-date YYYY-MM-DD      Start date (default: 1987-01-01)",
      "  --end-date YYYY-MM-DD        End date (default: 2023-12-31)",
      "  --lat FLOAT                  Target latitude (default: 37.0443931)",
      "  --lon FLOAT                  Target longitude (default: -122.072464)",
      "  --download-dir PATH          Working PRISM download directory",
      "                               (default: ./prism_data_work)",
      "  --resolution VALUE           PRISM resolution (default: 4km)",
      "                               Common values: 4km, 800m",
      "  --output-csv PATH            Output CSV path",
      "                               (default: ./prism_precipitation_santa_cruz_1987_2023.csv)",
      "  --keep-downloads             Keep downloaded PRISM folders (default: false)",
      "  --stop-on-unavailable        Stop gracefully at first unavailable chunk",
      "                               instead of failing the entire run (default: true)",
      "  --dry-run                    Print planned monthly requests and exit",
      "  --help                       Show this help",
      sep = "\n"
    )
  )
}

parse_args <- function(argv) {
  cfg <- list(
    start_date = as.Date("1987-01-01"),
    end_date = as.Date("2023-12-31"),
    lat = 37.0443931,
    lon = -122.072464,
    resolution = "4km",
    download_dir = file.path(getwd(), "prism_data_work"),
    output_csv = file.path(getwd(), "prism_precipitation_santa_cruz_1987_2023.csv"),
    keep_downloads = FALSE,
    stop_on_unavailable = TRUE,
    dry_run = FALSE
  )

  i <- 1L
  while (i <= length(argv)) {
    key <- argv[[i]]
    if (identical(key, "--help")) {
      usage()
      quit(status = 0L)
    } else if (identical(key, "--keep-downloads")) {
      cfg$keep_downloads <- TRUE
      i <- i + 1L
      next
    } else if (identical(key, "--dry-run")) {
      cfg$dry_run <- TRUE
      i <- i + 1L
      next
    } else if (identical(key, "--stop-on-unavailable")) {
      cfg$stop_on_unavailable <- TRUE
      i <- i + 1L
      next
    }

    if (i == length(argv)) {
      stop(sprintf("Missing value for option: %s", key), call. = FALSE)
    }
    val <- argv[[i + 1L]]

    if (identical(key, "--start-date")) {
      cfg$start_date <- as.Date(val)
    } else if (identical(key, "--end-date")) {
      cfg$end_date <- as.Date(val)
    } else if (identical(key, "--lat")) {
      cfg$lat <- as.numeric(val)
    } else if (identical(key, "--lon")) {
      cfg$lon <- as.numeric(val)
    } else if (identical(key, "--download-dir")) {
      cfg$download_dir <- val
    } else if (identical(key, "--resolution")) {
      cfg$resolution <- val
    } else if (identical(key, "--output-csv")) {
      cfg$output_csv <- val
    } else {
      stop(sprintf("Unknown option: %s", key), call. = FALSE)
    }
    i <- i + 2L
  }

  if (is.na(cfg$start_date) || is.na(cfg$end_date)) {
    stop("Invalid --start-date or --end-date. Expected YYYY-MM-DD.", call. = FALSE)
  }
  if (cfg$start_date > cfg$end_date) {
    stop("--start-date must be <= --end-date.", call. = FALSE)
  }
  if (!is.finite(cfg$lat) || cfg$lat < -90 || cfg$lat > 90) {
    stop("Invalid --lat. Expected a finite value in [-90, 90].", call. = FALSE)
  }
  if (!is.finite(cfg$lon) || cfg$lon < -180 || cfg$lon > 180) {
    stop("Invalid --lon. Expected a finite value in [-180, 180].", call. = FALSE)
  }
  if (!nzchar(cfg$resolution)) {
    stop("Invalid --resolution. Expected a non-empty string.", call. = FALSE)
  }

  cfg$download_dir <- normalizePath(cfg$download_dir, mustWork = FALSE)
  cfg$output_csv <- normalizePath(cfg$output_csv, mustWork = FALSE)
  cfg
}

require_pkg <- function(pkg) {
  if (!requireNamespace(pkg, quietly = TRUE)) {
    stop(
      sprintf("Missing required package '%s'. Install it before running this script.", pkg),
      call. = FALSE
    )
  }
}

month_sequence <- function(start_date, end_date) {
  start_month <- as.Date(format(start_date, "%Y-%m-01"))
  end_month <- as.Date(format(end_date, "%Y-%m-01"))
  seq(start_month, end_month, by = "month")
}

month_bounds <- function(month_start, start_date, end_date) {
  if (!inherits(month_start, "Date")) {
    month_start <- as.Date(month_start, origin = "1970-01-01")
  }
  next_month <- seq(month_start, by = "month", length.out = 2L)[2L]
  month_end <- next_month - 1L
  chunk_start <- max(month_start, start_date)
  chunk_end <- min(month_end, end_date)
  list(start = chunk_start, end = chunk_end)
}

folder_to_date <- function(folder_name) {
  date_str <- regmatches(folder_name, regexpr("[0-9]{8}", folder_name))
  if (length(date_str) == 0L || identical(date_str, "")) {
    return(as.Date(NA))
  }
  as.Date(date_str, format = "%Y%m%d")
}

extract_from_folder <- function(dl_dir, folder_name, lon, lat) {
  bil_file <- file.path(dl_dir, folder_name, paste0(folder_name, ".bil"))
  if (!file.exists(bil_file)) {
    return(NULL)
  }

  r <- raster::raster(bil_file)
  value <- raster::extract(r, matrix(c(lon, lat), ncol = 2L))
  date_val <- folder_to_date(folder_name)

  if (is.na(date_val) || is.na(value)) {
    return(NULL)
  }
  data.frame(Date = date_val, PRCP_mm = as.numeric(value))
}

main <- function() {
  cfg <- parse_args(commandArgs(trailingOnly = TRUE))

  months <- month_sequence(cfg$start_date, cfg$end_date)
  cat(sprintf("[INFO] PRISM monthly chunks to process: %d\n", length(months)))
  cat(sprintf("[INFO] Target point: lat=%.7f lon=%.6f\n", cfg$lat, cfg$lon))
  cat(sprintf("[INFO] PRISM resolution: %s\n", cfg$resolution))
  cat(sprintf("[INFO] Output CSV: %s\n", cfg$output_csv))
  cat(sprintf("[INFO] Download dir: %s\n", cfg$download_dir))
  cat(sprintf("[INFO] keep_downloads=%s\n", tolower(as.character(cfg$keep_downloads))))
  cat(sprintf("[INFO] stop_on_unavailable=%s\n", tolower(as.character(cfg$stop_on_unavailable))))

  if (isTRUE(cfg$dry_run)) {
    for (m in months) {
      bounds <- month_bounds(m, cfg$start_date, cfg$end_date)
      cat(sprintf("[DRY-RUN] %s -> %s\n", format(bounds$start), format(bounds$end)))
    }
    return(invisible(0L))
  }

  require_pkg("prism")
  require_pkg("raster")

  dir.create(cfg$download_dir, recursive = TRUE, showWarnings = FALSE)
  out_dir <- dirname(cfg$output_csv)
  dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

  prism::prism_set_dl_dir(cfg$download_dir)
  point_lon <- cfg$lon
  point_lat <- cfg$lat

  rows <- vector("list", length(months))
  row_idx <- 1L

  for (m in months) {
    bounds <- month_bounds(m, cfg$start_date, cfg$end_date)
    start_s <- format(bounds$start)
    end_s <- format(bounds$end)
    cat(sprintf("[INFO] Downloading PRISM ppt %s .. %s\n", start_s, end_s))

    dl_result <- tryCatch(
      {
        prism::get_prism_dailys(
          type = "ppt",
          resolution = cfg$resolution,
          minDate = start_s,
          maxDate = end_s,
          keepZip = FALSE
        )
        TRUE
      },
      error = function(e) {
        msg <- conditionMessage(e)
        unavailable <- grepl("available Prism data record", msg, ignore.case = TRUE, fixed = FALSE)
        if (cfg$stop_on_unavailable && unavailable) {
          cat(sprintf("[WARN] Stopping at first unavailable chunk %s .. %s\n", start_s, end_s))
          cat(sprintf("[WARN] %s\n", msg))
          return(FALSE)
        }
        stop(e)
      }
    )
    if (!isTRUE(dl_result)) {
      break
    }

    folders <- prism::prism_archive_ls()
    if (length(folders) == 0L) {
      warning(sprintf("No PRISM folders found for chunk %s .. %s", start_s, end_s))
      next
    }

    folder_dates <- as.Date(vapply(folders, folder_to_date, as.Date(NA)))
    keep <- !is.na(folder_dates) & folder_dates >= bounds$start & folder_dates <= bounds$end
    chunk_folders <- folders[keep]

    if (length(chunk_folders) == 0L) {
      warning(sprintf("No PRISM folders matched date range %s .. %s", start_s, end_s))
      next
    }

    chunk_rows <- lapply(chunk_folders, extract_from_folder, dl_dir = cfg$download_dir, lon = point_lon, lat = point_lat)
    chunk_rows <- Filter(Negate(is.null), chunk_rows)

    if (length(chunk_rows) > 0L) {
      rows[[row_idx]] <- do.call(rbind, chunk_rows)
      row_idx <- row_idx + 1L
    }

    if (!cfg$keep_downloads) {
      unlink(file.path(cfg$download_dir, chunk_folders), recursive = TRUE, force = TRUE)
    }
  }

  rows <- Filter(Negate(is.null), rows)
  if (length(rows) == 0L) {
    if (isTRUE(cfg$stop_on_unavailable)) {
      empty_out <- data.frame(
        Date = character(),
        PRCP_mm = numeric(),
        stringsAsFactors = FALSE
      )
      write.csv(empty_out, cfg$output_csv, row.names = FALSE)
      cat("[WARN] No new PRISM rows are available yet for the requested window.\n")
      cat(sprintf("[OK] wrote empty %s\n", cfg$output_csv))
      return(invisible(0L))
    }
    stop("No precipitation records were extracted.", call. = FALSE)
  }

  out <- do.call(rbind, rows)
  out <- out[!is.na(out$Date) & !is.na(out$PRCP_mm), c("Date", "PRCP_mm")]
  out <- out[order(out$Date), , drop = FALSE]
  out <- out[!duplicated(out$Date, fromLast = TRUE), , drop = FALSE]

  write.csv(out, cfg$output_csv, row.names = FALSE)

  cat(sprintf("[OK] wrote %s rows=%d\n", cfg$output_csv, nrow(out)))
  cat(sprintf("[OK] date range: %s .. %s\n", format(min(out$Date)), format(max(out$Date))))
}

main()
