###############################################################################
# Paths (centralized)
# Inputs:
#   - None (constants only)
# Outputs:
#   - Path variables for all inputs/outputs used downstream
# Dependencies:
#   - Files must exist at these paths for a successful run
###############################################################################

PROJECT_ROOT <- "/data/muscat_data/jaguir26/project1_ucsc_phd"

# Canonical/reference output folder (do not write to directly in runs)
CANONICAL_FIG_DIR <- file.path(PROJECT_ROOT, "Environmetrics_reproduce")

# Core inputs
COV_ELI_PATH <- "/data/muscat_data/jaguir26/projects/Project/Input/exAL/covariates/cov_1_ELI.csv"
COV_ONI_PATH <- "/data/muscat_data/jaguir26/projects/Project/Input/exAL/covariates/cov_2_ONI.csv"

NWS_FORECAST_PATH <- file.path(PROJECT_ROOT, "nws_forecast.csv")
GLOFAS_FORECAST_PATH <- file.path(PROJECT_ROOT, "weighted_time_series.csv")

PPT_PATH <- file.path(PROJECT_ROOT, "prism_precipitation_santa_cruz_1987_2023.csv")
SOIL_PATH <- file.path(PROJECT_ROOT, "soil_moisture_data", "soil_moisture_big_trees_daily_avg_1987_2023.csv")
PCA_PATH <- file.path(PROJECT_ROOT, "pca.csv")
RETROS_PATH <- file.path(PROJECT_ROOT, "retros_2022-12-25.csv")

DATA_CBIND_RDS <- file.path(PROJECT_ROOT, "data_cbind_tY_X.rds")
DATA_CBIND_CSV <- file.path(PROJECT_ROOT, "data_cbind_tY_X.csv")

TIMESTAMPS_CSV <- file.path(PROJECT_ROOT, "timestamps.csv")

# Univariate outputs
UNI_VAR_05 <- file.path(PROJECT_ROOT, "variables_5_exAL_synth_DISC_uni.RData")
UNI_VAR_20 <- file.path(PROJECT_ROOT, "variables_20_exAL_synth_DISC_uni.RData")
UNI_VAR_35 <- file.path(PROJECT_ROOT, "variables_35_exAL_synth_DISC_uni.RData")
UNI_VAR_50 <- file.path(PROJECT_ROOT, "variables_50_exAL_synth_DISC_uni.RData")
UNI_VAR_65 <- file.path(PROJECT_ROOT, "variables_65_exAL_synth_DISC_uni.RData")
UNI_VAR_80 <- file.path(PROJECT_ROOT, "variables_80_exAL_synth_DISC_uni.RData")
UNI_VAR_95 <- file.path(PROJECT_ROOT, "variables_95_exAL_synth_DISC_uni.RData")
