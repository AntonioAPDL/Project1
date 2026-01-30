#!/usr/bin/env Rscript

# Headless runner for Environmetrics figures (no comparisons, no nbconvert).

# -------------------------
# Config
# -------------------------
PROJECT_ROOT <- "/data/muscat_data/jaguir26/project1_ucsc_phd"
OUT_PARENT <- file.path(PROJECT_ROOT, "Environmetrics_reproduce_script_runs")
RUN_ID <- Sys.getenv("RUN_ID", "")
if (RUN_ID == "") {
  RUN_ID <- format(Sys.time(), "%Y%m%d_%H%M%S")
}
OUT_DIR <- file.path(OUT_PARENT, RUN_ID)
SEED <- 777

# Deterministic settings (match notebook)
set.seed(SEED)
RNGkind("Mersenne-Twister", "Inversion", "Rounding")
options(stringsAsFactors = FALSE)

# -------------------------
# Logging
# -------------------------
log_dir <- file.path(PROJECT_ROOT, "repro", "logs", "script_runs", RUN_ID)
dir.create(log_dir, showWarnings = FALSE, recursive = TRUE)
log_path <- file.path(log_dir, "run_log.txt")
con <- file(log_path, open = "wt")
sink(con, split = TRUE)
cat(sprintf("START: %s\n", format(Sys.time(), "%Y-%m-%d %H:%M:%S")))
git_hash <- tryCatch(system("git rev-parse HEAD", intern = TRUE), error = function(e) "UNKNOWN")
cat(sprintf("GIT_COMMIT: %s\n", git_hash))
cat(sprintf("OUT_DIR: %s\n", OUT_DIR))
cat(sprintf("SEED: %s\n", SEED))

# capture session info
session_path <- file.path(log_dir, "sessionInfo.txt")
writeLines(capture.output(sessionInfo()), session_path)

# -------------------------
# Path redirection helper (force outputs into OUT_DIR)
# -------------------------
redirect_path <- function(filename) {
  dir.create(OUT_DIR, showWarnings = FALSE, recursive = TRUE)
  if (is.null(filename)) return(filename)
  file.path(OUT_DIR, basename(filename))
}

# Clean only OUT_DIR
if (dir.exists(OUT_DIR)) {
  unlink(OUT_DIR, recursive = TRUE, force = TRUE)
}
dir.create(OUT_DIR, showWarnings = FALSE, recursive = TRUE)

# Override ggsave and graphic devices to prevent overwriting canonical outputs
if (!exists("ggsave_original", inherits = FALSE)) {
  ggsave_original <- ggplot2::ggsave
}

ggsave <- function(filename, plot = ggplot2::last_plot(), ...) {
  do.call(ggsave_original, c(list(filename = redirect_path(filename), plot = plot), list(...)))
}

png <- function(filename, ...) {
  do.call(grDevices::png, c(list(filename = redirect_path(filename)), list(...)))
}

pdf <- function(file, ...) {
  do.call(grDevices::pdf, c(list(file = redirect_path(file)), list(...)))
}

jpeg <- function(filename, ...) {
  do.call(grDevices::jpeg, c(list(filename = redirect_path(filename)), list(...)))
}

tiff <- function(filename, ...) {
  do.call(grDevices::tiff, c(list(filename = redirect_path(filename)), list(...)))
}

svg <- function(filename, ...) {
  do.call(grDevices::svg, c(list(filename = redirect_path(filename)), list(...)))
}

# -------------------------
# Execute modularized notebook export (preserve order)
# -------------------------
modules_dir <- file.path(PROJECT_ROOT, "R", "environmetrics")
modules <- c(
  "00_paths.R",
  "00_setup.R",
  "00_constants.R",
  "01_config.R",
  "02_helpers_core.R",
  "utils_data.R",
  "utils_plot.R",
  "10_data_inputs.R",
  "20_model_setup.R",
  "30_univariate_and_misc.R",
  "40_figures.R"
)

missing <- modules[!file.exists(file.path(modules_dir, modules))]
if (length(missing) > 0) {
  stop(sprintf(
    "Missing modular files in %s: %s\nRecreate modules from Environmetrics_Figures__OLDEST_linearized.R.",
    modules_dir,
    paste(missing, collapse = ", ")
  ))
}

log_step <- function(msg) {
  cat(sprintf("[%s] %s\n", format(Sys.time(), "%Y-%m-%d %H:%M:%S"), msg))
}

## Pre-check: paths and inputs (fast, no parsing)
paths_file <- file.path(modules_dir, "00_paths.R")
if (file.exists(paths_file)) {
  source(paths_file)
  check_script <- file.path(PROJECT_ROOT, "scripts", "check_inputs.R")
  if (file.exists(check_script)) {
    source(check_script)
    log_step("START check_inputs")
    check_inputs()
    log_step("END check_inputs")
  }
}

for (mod in modules) {
  log_step(paste("START", mod))
  source(file.path(modules_dir, mod))
  log_step(paste("END", mod))
}

cat(sprintf("END: %s\n", format(Sys.time(), "%Y-%m-%d %H:%M:%S")))

sink()
close(con)
