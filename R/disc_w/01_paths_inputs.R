disc_w_resolve_paths <- function() {
  paths <- list(
    parameters_path = "/data/muscat_data/jaguir26/projects/Project/Input/exAL/parameters/parameters.txt",
    cov_1_eli_path = "/data/muscat_data/jaguir26/projects/Project/Input/exAL/covariates/cov_1_ELI.csv",
    cov_2_oni_path = "/data/muscat_data/jaguir26/projects/Project/Input/exAL/covariates/cov_2_ONI.csv",
    nws_forecast_path = "/data/muscat_data/jaguir26/project1_ucsc_phd/nws_forecast.csv",
    glofas_forecast_path = "/data/muscat_data/jaguir26/project1_ucsc_phd/weighted_time_series.csv",
    prism_ppt_path = "/data/muscat_data/jaguir26/project1_ucsc_phd/prism_precipitation_santa_cruz_1987_2023.csv",
    soil_moisture_path = "/data/muscat_data/jaguir26/project1_ucsc_phd/soil_moisture_data/soil_moisture_big_trees_daily_avg_1987_2023.csv",
    pca_components_path = "/data/muscat_data/jaguir26/project1_ucsc_phd/pca.csv",
    retros_path = "/data/muscat_data/jaguir26/project1_ucsc_phd/retros_2022-12-25.csv",
    output_dir = "/data/muscat_data/jaguir26/project1_ucsc_phd"
  )

  if (isTRUE(DISC_DEBUG)) {
    for (p in unlist(paths, use.names = FALSE)) {
      disc_assert(is.character(p) && length(p) == 1, "Expected scalar character path.")
    }
  }

  paths
}
