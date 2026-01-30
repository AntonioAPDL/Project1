#!/usr/bin/env Rscript

# Fast existence checks only (no parsing of large files).

if (!exists("PROJECT_ROOT")) {
  source("/data/muscat_data/jaguir26/project1_ucsc_phd/R/environmetrics/00_paths.R")
}

check_inputs <- function() {
  required <- c(
    COV_ELI_PATH,
    COV_ONI_PATH,
    NWS_FORECAST_PATH,
    GLOFAS_FORECAST_PATH,
    PPT_PATH,
    SOIL_PATH,
    PCA_PATH,
    RETROS_PATH,
    UNI_VAR_05,
    UNI_VAR_20,
    UNI_VAR_35,
    UNI_VAR_50,
    UNI_VAR_65,
    UNI_VAR_80,
    UNI_VAR_95
  )
  missing <- required[!file.exists(required)]
  if (length(missing) > 0) {
    msg <- paste0("Missing required inputs:\n- ", paste(missing, collapse = "\n- "))
    stop(msg, call. = FALSE)
  }
  invisible(TRUE)
}

if (sys.nframe() == 0) {
  check_inputs()
  cat("All required inputs exist.\n")
}
