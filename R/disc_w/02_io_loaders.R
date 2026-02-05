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

disc_w_read_covariates <- function(cov_1_eli_path, cov_2_oni_path) {
  list(
    ELI_lon = read.csv(cov_1_eli_path),
    merged_sst_data = read.csv(cov_2_oni_path)
  )
}

disc_w_read_forecasts <- function(nws_forecast_path, glofas_forecast_path) {
  list(
    nws_forecast = read.csv(nws_forecast_path),
    glofas_forecast = read.csv(glofas_forecast_path)
  )
}

disc_w_read_prism_ppt <- function(file_path) {
  read_csv(file_path, show_col_types = FALSE)
}

disc_w_read_soil_moisture <- function(csv_file_path) {
  read.csv(csv_file_path)
}

disc_w_read_pca_components <- function(components_file_path) {
  read_csv(components_file_path, show_col_types = FALSE)
}

disc_w_read_retro_streamflow <- function(data_path) {
  read_csv(data_path, show_col_types = FALSE)
}

disc_w_load_rdata <- function(file_path, env = parent.frame()) {
  load(file_path, envir = env)
  invisible(NULL)
}
