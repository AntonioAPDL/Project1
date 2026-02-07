# disc_w/01_paths_inputs.R
#
# Centralized input/output path inventory for the DISC Wishart/ensemble workflow.
# This is intentionally minimal: it returns the same absolute paths the original
# script used, as a named list.

# disc_w_resolve_paths()
# Returns a named list of absolute input paths + `output_dir`.
# When `DISC_DEBUG` is TRUE, performs lightweight type assertions on paths.
disc_w_resolve_paths <- function() {
  env_or_default <- function(key, default) {
    val <- Sys.getenv(key, unset = "")
    if (nzchar(val)) val else default
  }

  paths <- list(
    parameters_path = env_or_default("DISC_W_PARAMETERS_PATH", "/data/muscat_data/jaguir26/projects/Project/Input/exAL/parameters/parameters.txt"),
    cov_1_eli_path = env_or_default("DISC_W_COV1_PATH", "/data/muscat_data/jaguir26/projects/Project/Input/exAL/covariates/cov_1_ELI.csv"),
    cov_2_oni_path = env_or_default("DISC_W_COV2_PATH", "/data/muscat_data/jaguir26/projects/Project/Input/exAL/covariates/cov_2_ONI.csv"),
    nws_forecast_path = env_or_default("DISC_W_NWS_PATH", "/data/muscat_data/jaguir26/project1_ucsc_phd/nws_forecast.csv"),
    glofas_forecast_path = env_or_default("DISC_W_GLOFAS_PATH", "/data/muscat_data/jaguir26/project1_ucsc_phd/weighted_time_series.csv"),
    prism_ppt_path = env_or_default("DISC_W_PRISM_PATH", "/data/muscat_data/jaguir26/project1_ucsc_phd/prism_precipitation_santa_cruz_1987_2023.csv"),
    soil_moisture_path = env_or_default("DISC_W_SOIL_PATH", "/data/muscat_data/jaguir26/project1_ucsc_phd/soil_moisture_data/soil_moisture_big_trees_daily_avg_1987_2023.csv"),
    pca_components_path = env_or_default("DISC_W_PCA_PATH", "/data/muscat_data/jaguir26/project1_ucsc_phd/pca.csv"),
    retros_path = env_or_default("DISC_W_RETROS_PATH", "/data/muscat_data/jaguir26/project1_ucsc_phd/retros_2022-12-25.csv"),
    output_dir = env_or_default("DISC_W_OUTPUT_DIR", "/data/muscat_data/jaguir26/project1_ucsc_phd")
  )

  if (isTRUE(DISC_DEBUG)) {
    for (p in unlist(paths, use.names = FALSE)) {
      disc_assert(is.character(p) && length(p) == 1, "Expected scalar character path.")
    }
  }

  paths
}
