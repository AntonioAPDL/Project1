#!/usr/bin/env Rscript

message("DEPRECATED entrypoint for unified workflow orchestration. Prefer: scripts/unified_run.R")

# Headless runner for Environmetrics figures (no comparisons, no nbconvert).

# -------------------------
# Config
# -------------------------
PROJECT_ROOT <- "/data/muscat_data/jaguir26/project1_ucsc_phd"
UNIFIED_RUN_ROOT <- Sys.getenv("UNIFIED_RUN_ROOT", "")
OUT_PARENT <- if (nzchar(UNIFIED_RUN_ROOT)) {
  file.path(UNIFIED_RUN_ROOT, "post", "outputs")
} else {
  file.path(PROJECT_ROOT, "Environmetrics_reproduce_script_runs")
}
RUN_ID <- Sys.getenv("RUN_ID", "")
if (RUN_ID == "") {
  RUN_ID <- format(Sys.time(), "%Y%m%d_%H%M%S")
}
OUT_DIR <- file.path(OUT_PARENT, RUN_ID)
SEED <- 777
PROFILE <- isTRUE(as.logical(Sys.getenv("PROFILE", "FALSE")))
PROFILE_DETAIL <- isTRUE(as.logical(Sys.getenv("PROFILE_DETAIL", "FALSE")))
ENV_SORT_KEEP_NA <- isTRUE(as.logical(Sys.getenv("ENV_SORT_KEEP_NA", "TRUE")))

# Deterministic settings (match notebook)
set.seed(SEED)
RNGkind("Mersenne-Twister", "Inversion", "Rounding")
options(stringsAsFactors = FALSE)

# -------------------------
# Logging
# -------------------------
log_dir <- if (nzchar(UNIFIED_RUN_ROOT)) {
  file.path(UNIFIED_RUN_ROOT, "post", "logs", RUN_ID)
} else {
  file.path(PROJECT_ROOT, "repro", "logs", "script_runs", RUN_ID)
}
dir.create(log_dir, showWarnings = FALSE, recursive = TRUE)
log_path <- file.path(log_dir, "run_log.txt")
con <- file(log_path, open = "wt")
sink(con, split = TRUE)
cat(sprintf("START: %s\n", format(Sys.time(), "%Y-%m-%d %H:%M:%S")))
git_hash <- tryCatch(system("git rev-parse HEAD", intern = TRUE), error = function(e) "UNKNOWN")
cat(sprintf("GIT_COMMIT: %s\n", git_hash))
cat(sprintf("OUT_DIR: %s\n", OUT_DIR))
cat(sprintf("SEED: %s\n", SEED))
cat(sprintf("PROFILE: %s\n", PROFILE))
cat(sprintf("PROFILE_DETAIL: %s\n", PROFILE_DETAIL))
cat(sprintf("ENV_SORT_KEEP_NA: %s\n", ENV_SORT_KEEP_NA))

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
  out_path <- redirect_path(filename)
  t0 <- Sys.time()
  on.exit({
    t1 <- Sys.time()
    log_io_timing("ggsave", out_path, t0, t1)
  }, add = TRUE)
  do.call(ggsave_original, c(list(filename = out_path, plot = plot), list(...)))
}

last_device_file <- NULL
last_device_kind <- NULL

png <- function(filename, ...) {
  out_path <- redirect_path(filename)
  last_device_file <<- out_path
  last_device_kind <<- "png"
  do.call(grDevices::png, c(list(filename = out_path), list(...)))
}

pdf <- function(file, ...) {
  out_path <- redirect_path(file)
  last_device_file <<- out_path
  last_device_kind <<- "pdf"
  do.call(grDevices::pdf, c(list(file = out_path), list(...)))
}

jpeg <- function(filename, ...) {
  out_path <- redirect_path(filename)
  last_device_file <<- out_path
  last_device_kind <<- "jpeg"
  do.call(grDevices::jpeg, c(list(filename = out_path), list(...)))
}

tiff <- function(filename, ...) {
  out_path <- redirect_path(filename)
  last_device_file <<- out_path
  last_device_kind <<- "tiff"
  do.call(grDevices::tiff, c(list(filename = out_path), list(...)))
}

svg <- function(filename, ...) {
  out_path <- redirect_path(filename)
  last_device_file <<- out_path
  last_device_kind <<- "svg"
  do.call(grDevices::svg, c(list(filename = out_path), list(...)))
}

dev_off_original <- grDevices::dev.off
dev.off <- function(...) {
  t0 <- Sys.time()
  on.exit({
    t1 <- Sys.time()
    kind <- if (!is.null(last_device_kind)) paste0(last_device_kind, ".dev.off") else "dev.off"
    log_io_timing(kind, last_device_file, t0, t1)
    last_device_file <<- NULL
    last_device_kind <<- NULL
  }, add = TRUE)
  dev_off_original(...)
}

if (!exists("saveRDS_original", inherits = FALSE)) {
  saveRDS_original <- base::saveRDS
}
saveRDS <- function(object, file = "", ...) {
  out_path <- redirect_path(file)
  t0 <- Sys.time()
  on.exit({
    t1 <- Sys.time()
    log_io_timing("saveRDS", out_path, t0, t1)
  }, add = TRUE)
  saveRDS_original(object = object, file = out_path, ...)
}

if (!exists("write.csv_original", inherits = FALSE)) {
  write.csv_original <- utils::write.csv
}
write.csv <- function(x, file = "", ...) {
  out_path <- redirect_path(file)
  t0 <- Sys.time()
  on.exit({
    t1 <- Sys.time()
    log_io_timing("write.csv", out_path, t0, t1)
  }, add = TRUE)
  write.csv_original(x = x, file = out_path, ...)
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

profile_dir <- NULL
timings_path <- NULL
io_timings_path <- NULL
if (PROFILE) {
  profile_dir <- if (nzchar(UNIFIED_RUN_ROOT)) {
    file.path(UNIFIED_RUN_ROOT, "post", "profile", RUN_ID)
  } else {
    file.path(PROJECT_ROOT, "repro", "logs", "profile", RUN_ID)
  }
  dir.create(profile_dir, showWarnings = FALSE, recursive = TRUE)
  timings_path <- file.path(profile_dir, "timings.csv")
  writeLines("section,start,end,elapsed_sec", timings_path)
  io_timings_path <- file.path(profile_dir, "io_timings.csv")
  writeLines("kind,file,start,end,elapsed_sec,file_bytes", io_timings_path)
}

log_timing <- function(section, start_time, end_time) {
  if (!PROFILE) return(invisible(NULL))
  elapsed <- as.numeric(difftime(end_time, start_time, units = "secs"))
  line <- sprintf("%s,%s,%s,%.6f", section, start_time, end_time, elapsed)
  write(line, file = timings_path, append = TRUE)
}

log_io_timing <- function(kind, file, start_time, end_time) {
  if (!PROFILE) return(invisible(NULL))
  elapsed <- as.numeric(difftime(end_time, start_time, units = "secs"))
  file_bytes <- NA_integer_
  if (!is.null(file) && !is.na(file) && nzchar(file) && file.exists(file)) {
    file_bytes <- as.integer(file.info(file)$size)
  }
  safe_file <- if (is.null(file) || is.na(file)) "" else file
  line <- sprintf("%s,%s,%s,%s,%.6f,%s", kind, safe_file, start_time, end_time, elapsed, file_bytes)
  write(line, file = io_timings_path, append = TRUE)
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
  t0 <- Sys.time()
  source(file.path(modules_dir, mod))
  t1 <- Sys.time()
  log_step(paste("END", mod))
  log_timing(mod, t0, t1)
}

cat(sprintf("END: %s\n", format(Sys.time(), "%Y-%m-%d %H:%M:%S")))

sink()
close(con)
