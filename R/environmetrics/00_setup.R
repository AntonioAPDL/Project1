#!/usr/bin/env Rscript

# =============================================================================
# Setup: library paths and package imports
# Inputs:
#   - None
# Outputs:
#   - Loads required packages into session
# Dependencies:
#   - R packages listed below must be installed
# =============================================================================
.libPaths(c("~/R/libs", .libPaths()))
print(.libPaths())

# Core analysis + model dependencies
library(parallel)
library(dlm)
library(exdqlm)
library(mvtnorm)
library(jmuOutlier)
library(sn)
library(Matrix)
library(numDeriv)
library(foreach)
library(doParallel)
library(dataRetrieval)
library(zoo)
library(tseries)
library(patchwork)
library(rvest)
library(expint)
library(nimble)
library(nloptr)
library(expm)
library(RcppArmadillo)
library(RcppEigen)
library(ks)
library(MASS)
library(FNN)
library(matrixStats)
library(truncnorm)
library(isotone)

# Tidyverse (explicit + meta)
library(tidyverse)
library(ggplot2)
library(dplyr)
library(tidyr)
library(scales)
library(lubridate)

# =============================================================================
# Lightweight profiling helpers (used by modules; controlled by PROFILE flag)
# =============================================================================
is_profile_enabled <- function() {
  exists("PROFILE", inherits = TRUE) && isTRUE(get("PROFILE", inherits = TRUE))
}

profile_section <- function(section, expr) {
  expr <- substitute(expr)
  if (!is_profile_enabled()) {
    return(eval(expr, envir = parent.frame()))
  }
  t0 <- Sys.time()
  on.exit({
    t1 <- Sys.time()
    if (exists("log_timing", inherits = TRUE)) {
      # Avoid commas in section labels (CSV output in runner)
      safe_section <- gsub(",", ";", section, fixed = TRUE)
      log_timing(safe_section, t0, t1)
    }
  }, add = TRUE)
  eval(expr, envir = parent.frame())
}

# =============================================================================
# Optional detailed profiling (sampling profiler via Rprof)
# - Enabled only when PROFILE_DETAIL=TRUE in the runner env.
# - Designed to wrap a few heavy blocks (do not use for many short sections).
# - Writes outputs under repro/logs/profile/<RUN_ID>/ when available.
# =============================================================================
is_profile_detail_enabled <- function() {
  exists("PROFILE_DETAIL", inherits = TRUE) && isTRUE(get("PROFILE_DETAIL", inherits = TRUE))
}

get_profile_detail_section_filter <- function() {
  if (exists("PROFILE_DETAIL_SECTION", inherits = TRUE)) {
    val <- get("PROFILE_DETAIL_SECTION", inherits = TRUE)
    if (is.character(val) && length(val) == 1L && nzchar(val)) {
      return(val)
    }
  }
  Sys.getenv("PROFILE_DETAIL_SECTION", "")
}

profile_detail_section <- function(section, expr) {
  expr <- substitute(expr)
  if (!is_profile_detail_enabled()) {
    return(eval(expr, envir = parent.frame()))
  }

  filter <- get_profile_detail_section_filter()
  if (nzchar(filter)) {
    allowed <- trimws(strsplit(filter, ",", fixed = TRUE)[[1]])
    if (!(section %in% allowed)) {
      return(eval(expr, envir = parent.frame()))
    }
  }

  profile_dir <- if (exists("profile_dir", inherits = TRUE)) get("profile_dir", inherits = TRUE) else tempdir()
  dir.create(profile_dir, showWarnings = FALSE, recursive = TRUE)
  safe <- gsub("[^A-Za-z0-9_.-]+", "_", section)
  rprof_path <- file.path(profile_dir, paste0("rprof_", safe, ".out"))
  summary_path <- file.path(profile_dir, paste0("rprof_", safe, "_summary.txt"))

  Rprof(rprof_path, interval = 0.01)
  on.exit({
    Rprof(NULL)
    summ <- tryCatch(summaryRprof(rprof_path), error = function(e) NULL)
    if (!is.null(summ)) {
      lines <- c(
        paste0("section: ", section),
        paste0("generated: ", format(Sys.time(), "%Y-%m-%d %H:%M:%S")),
        "",
        "== by.self (top 50) ==",
        capture.output(utils::head(summ$by.self, 50)),
        "",
        "== by.total (top 50) ==",
        capture.output(utils::head(summ$by.total, 50))
      )
      writeLines(lines, summary_path)
    }
  }, add = TRUE)

  eval(expr, envir = parent.frame())
}
