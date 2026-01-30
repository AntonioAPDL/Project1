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
