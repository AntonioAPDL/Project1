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
