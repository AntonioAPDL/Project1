#!/usr/bin/env Rscript

# Headless runner for recovered Environmetrics figures notebook
# Usage:
#   Rscript repro/run/Environmetrics_Figures_run.R

args <- commandArgs(trailingOnly = FALSE)
file_flag <- "--file="
script_path <- sub(file_flag, "", args[grep(file_flag, args)])
if (length(script_path) == 0 || script_path == "") {
  script_path <- "repro/run/Environmetrics_Figures_run.R"
}
script_dir <- dirname(normalizePath(script_path))
PROJECT_ROOT <- normalizePath(file.path(script_dir, "../.."))
setwd(PROJECT_ROOT)

# -------------------------
# Config
# -------------------------
SKIP_UNIVARIATE <- TRUE
OUTPUT_DIR <- file.path(PROJECT_ROOT, "Environmetrics_reproduce_script")
GOLD_DISC_SHA <- file.path(PROJECT_ROOT, "repro", "gold_DISC_figures.sha256")

set.seed(123)

# -------------------------
# Logging
# -------------------------
log_path <- file.path(PROJECT_ROOT, "repro", "run", "run_log.txt")
con <- file(log_path, open = "wt")
sink(con, split = TRUE)
cat(sprintf("START: %s\n", format(Sys.time(), "%Y-%m-%d %H:%M:%S")))
cat(sprintf("OUTPUT_DIR: %s\n", OUTPUT_DIR))
cat(sprintf("SKIP_UNIVARIATE: %s\n", SKIP_UNIVARIATE))

# Redirect ggsave to OUTPUT_DIR without changing filenames
if (!exists("ggsave_original", inherits = FALSE)) {
  ggsave_original <- ggplot2::ggsave
}

ggsave <- function(filename, plot = ggplot2::last_plot(), ...) {
  dir.create(OUTPUT_DIR, showWarnings = FALSE, recursive = TRUE)
  if (!is.null(filename)) {
    filename <- file.path(OUTPUT_DIR, basename(filename))
  }
  ggsave_original(filename = filename, plot = plot, ...)
}

# -------------------------
# Execute extracted notebook script
# -------------------------
extracted <- file.path(PROJECT_ROOT, "repro", "extracted", "Environmetrics_Figures__RECOVERED_WORKING.r")
if (!file.exists(extracted)) {
  stop(sprintf("Extracted script not found: %s", extracted))
}
source(extracted)

cat(sprintf("END: %s\n", format(Sys.time(), "%Y-%m-%d %H:%M:%S")))

sink()
close(con)
