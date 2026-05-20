# disc_w/02_io_loaders.R
#
# I/O-only helpers for `DISC_Optimal_Synth_Ranges_W.r`.
# These helpers load inputs using the same base functions as the original script
# (e.g., `read.csv`, `readr::read_csv`, `load`) and should not introduce any
# transformations beyond what the orchestrator already performs.

# disc_w_load_parameters(parameters_path, env)
# Reads the external parameters file and evaluates each assignment line into
# `env` (default: caller environment), matching the original script semantics.
disc_w_load_parameters <- function(parameters_path, env = parent.frame()) {
  # Check if the file exists
  if (!file.exists(parameters_path)) {
    stop("The parameters file does not exist at the specified path: ", parameters_path)
  }

  lines <- readLines(parameters_path)

  # Check if the lines variable is empty or not as expected
  if (length(lines) == 0) {
    stop("No content found in the parameters file: ", parameters_path)
  }

  # Process each line and assign variables
  for (line in lines) {
    # Remove leading and trailing whitespaces
    line <- trimws(line)

    # Skip empty lines and comments
    if (nchar(line) == 0 || grepl("^#", line)) next

    # Evaluate and assign
    eval(parse(text = line), envir = env)
  }

  invisible(NULL)
}

# disc_w_read_covariates(cov_1_eli_path, cov_2_oni_path)
# Returns a list with `ELI_lon` and `merged_sst_data` data.frames.
disc_w_read_covariates <- function(cov_1_eli_path, cov_2_oni_path) {
  list(
    ELI_lon = read.csv(cov_1_eli_path),
    merged_sst_data = read.csv(cov_2_oni_path)
  )
}

# disc_w_read_forecasts(nws_forecast_path, glofas_forecast_path)
# Returns a list with `nws_forecast` and `glofas_forecast` data.frames.
disc_w_read_forecasts <- function(nws_forecast_path, glofas_forecast_path) {
  list(
    nws_forecast = read.csv(nws_forecast_path),
    glofas_forecast = read.csv(glofas_forecast_path)
  )
}

# disc_w_read_prism_ppt(file_path)
# Reads PRISM precipitation input using `readr::read_csv` (col-types suppressed).
disc_w_read_prism_ppt <- function(file_path) {
  readr::read_csv(file_path, show_col_types = FALSE)
}

# disc_w_read_soil_moisture(csv_file_path)
# Reads soil moisture input using base `read.csv`.
disc_w_read_soil_moisture <- function(csv_file_path) {
  read.csv(csv_file_path)
}

# disc_w_read_pca_components(components_file_path)
# Reads PCA components input using `readr::read_csv` (col-types suppressed).
disc_w_read_pca_components <- function(components_file_path) {
  readr::read_csv(components_file_path, show_col_types = FALSE)
}

# disc_w_read_retro_streamflow(data_path)
# Reads retrospective streamflow input using `readr::read_csv` (col-types suppressed).
disc_w_read_retro_streamflow <- function(data_path) {
  readr::read_csv(data_path, show_col_types = FALSE)
}

# disc_w_load_rdata(file_path, env)
# Loads a `.RData` file into `env` (default: caller environment), preserving the
# original script semantics (which relied on `load()` side effects).
disc_w_load_rdata <- function(file_path, env = parent.frame()) {
  load(file_path, envir = env)
  invisible(NULL)
}

# disc_w_load_rdata_env(file_path, parent)
# Loads a `.RData` file into a dedicated environment and returns that
# environment so callers can validate object presence deterministically.
disc_w_load_rdata_env <- function(file_path, parent = emptyenv()) {
  env <- new.env(parent = parent)
  load(file_path, envir = env)
  env
}

# disc_w_require_rdata_objects(file_path, required_names)
# Loads a `.RData` file into a dedicated environment, verifies a required set of
# object names, and returns those objects as a named list.
disc_w_require_rdata_objects <- function(file_path, required_names) {
  env <- disc_w_load_rdata_env(file_path)
  loaded_names <- ls(env, all.names = TRUE)
  missing_names <- setdiff(required_names, loaded_names)
  if (length(missing_names) > 0L) {
    stop(sprintf(
      "missing required objects: %s",
      paste(missing_names, collapse = ", ")
    ), call. = FALSE)
  }
  out <- lapply(required_names, function(name) get(name, envir = env, inherits = FALSE))
  names(out) <- required_names
  out
}
