###############################################################################
# Data inputs and covariate assembly
# Inputs:
#   - CSVs: ELI/ONI covariates, NWS/GloFAS forecasts, PPT/soil/PCA, retros
# Outputs:
#   - Covariate matrices (X, X_f) and response matrix Y
#   - Writes data_cbind_tY_X.{rds,csv}
# Dependencies:
#   - 00_paths.R, utils_data.R
###############################################################################

# Read and process ELI_lon data
ELI_lon <- read.csv(COV_ELI_PATH)
merged_sst_data <- read.csv(COV_ONI_PATH)
ELI_lon$time <- as.Date(ELI_lon$time)
adjustment_years <- 170
ELI_lon$time <- ELI_lon$time - years(adjustment_years)
#
CFSToCMS_CONVERSION_FACTOR = 0.0283168466
# Read and process USGS data
if (nzchar(USGS_DAILY_PATH) && file.exists(USGS_DAILY_PATH)) {
  message(sprintf("Using local USGS daily truth CSV: %s", USGS_DAILY_PATH))
  San_Lorenzo_Daily_USGS_R <- family_shared_read_usgs_daily(
    USGS_DAILY_PATH,
    min_date = as.Date("1979-01-01")
  )
} else {
  data_usgs_r <- readNWISdv(siteNumbers = site_code[1], parameterCd = "00060", statCd = "00003")
  San_Lorenzo_Daily_USGS_R <- data_usgs_r %>%
    mutate(timestamp = as.Date(Date),
           data0 = log(X_00060_00003*CFSToCMS_CONVERSION_FACTOR + 1)) %>%
    filter(timestamp > as.Date("1979-01-01"))
  San_Lorenzo_Daily_USGS_R$time <- San_Lorenzo_Daily_USGS_R$timestamp
}

cutoff_date <- if (exists("CUTOFF_DATE", inherits = TRUE)) as.Date(get("CUTOFF_DATE", inherits = TRUE)) else as.Date("2022-12-25")
if (is.na(cutoff_date)) cutoff_date <- as.Date("2022-12-25")
forecast_start_date <- if (exists("FORECAST_START_DATE", inherits = TRUE)) as.Date(get("FORECAST_START_DATE", inherits = TRUE)) else (cutoff_date + 1L)
if (is.na(forecast_start_date)) forecast_start_date <- cutoff_date + 1L

select_future_window <- function(df, time_col, value_col, start_date, horizon, label) {
  idx <- which(df[[time_col]] >= start_date)
  if (!length(idx)) {
    warning(
      sprintf("%s has no rows at/after forecast start date %s; using persistence from last value", label, as.character(start_date)),
      call. = FALSE
    )
    idx <- nrow(df)
  }
  start_idx <- idx[[1]]
  n_needed <- as.integer(horizon)
  end_idx <- start_idx + n_needed - 1L
  end_obs <- min(end_idx, nrow(df))
  out <- df[start_idx:end_obs, c(time_col, value_col)]
  colnames(out) <- c("time", value_col)

  if (nrow(out) < n_needed) {
    n_pad <- n_needed - nrow(out)
    last_time <- as.Date(out$time[[nrow(out)]])
    last_val <- out[[value_col]][[nrow(out)]]
    pad_times <- seq(last_time + 1L, by = "day", length.out = n_pad)
    pad <- data.frame(time = pad_times, stringsAsFactors = FALSE)
    pad[[value_col]] <- rep(last_val, n_pad)
    out <- rbind(out, pad[, c("time", value_col)])
    warning(
      sprintf("%s forecast horizon short by %d rows; extending with persistence", label, n_pad),
      call. = FALSE
    )
  }

  out[, c(value_col, "time")]
}

###########################################################################################
####################################### Forecasts ######################################### 
###########################################################################################
nws_forecast <- read.csv(NWS_FORECAST_PATH)
if (!("target_date" %in% names(nws_forecast))) {
  if ("Date" %in% names(nws_forecast)) {
    nws_forecast$target_date <- as.Date(nws_forecast$Date)
  } else {
    stop(
      sprintf("NWS forecast file must include 'target_date' or 'Date': %s", NWS_FORECAST_PATH),
      call. = FALSE
    )
  }
} else {
  nws_forecast$target_date <- as.Date(nws_forecast$target_date)
}
nws_value_cols <- setdiff(colnames(nws_forecast), c("target_date", "Date"))
if (length(nws_value_cols) == 0L) {
  stop(sprintf("NWS forecast file has no numeric ensemble columns: %s", NWS_FORECAST_PATH), call. = FALSE)
}
nws_forecast[, nws_value_cols] <- log(nws_forecast[, nws_value_cols, drop = FALSE])
num_ens_nws <- length(nws_value_cols)

glofas_forecast <- read.csv(GLOFAS_FORECAST_PATH)
if (!("target_date" %in% names(glofas_forecast))) {
  if ("Date" %in% names(glofas_forecast)) {
    glofas_forecast$target_date <- as.Date(glofas_forecast$Date)
  } else {
    stop(
      sprintf("GLOFAS forecast file must include 'target_date' or 'Date': %s", GLOFAS_FORECAST_PATH),
      call. = FALSE
    )
  }
} else {
  glofas_forecast$target_date <- as.Date(glofas_forecast$target_date)
}
specific_date <- forecast_start_date
glofas_forecast <- glofas_forecast[glofas_forecast$target_date >= specific_date, ]
glofas_value_cols <- setdiff(colnames(glofas_forecast), c("target_date", "Date"))
if (length(glofas_value_cols) == 0L) {
  stop(sprintf("GLOFAS forecast file has no numeric ensemble columns: %s", GLOFAS_FORECAST_PATH), call. = FALSE)
}
glofas_forecast[, glofas_value_cols] <- log(glofas_forecast[, glofas_value_cols, drop = FALSE])

num_ens_glofas <- length(glofas_value_cols)

ensembles <- list(
  data.matrix(glofas_forecast[, glofas_value_cols, drop = FALSE]),
  data.matrix(nws_forecast[, nws_value_cols, drop = FALSE])
)
J <- length(ensembles)
num_mem <- rep(NA_real_, J)
ranges <- rep(NA_real_, J)
for(j in 1:J){
  num_mem[j] <- dim(ensembles[[j]])[2]
  ranges[j] <- dim(ensembles[[j]])[1]
}

row_means_list <- vector("list", J + 1)
row_means_list[[1]] <- rep(NA_real_, ranges[1])
for (j in 1:J) {
  row_means_list[[j + 1]] <- rep(NA_real_, ranges[1])
  row_means_list[[j + 1]][1:ranges[j]] <- rowMeans(ensembles[[j]])
}
mean_forecast <- do.call(rbind, row_means_list)

###########################################################################################
####################################### Covs, Retros, More ################################ 
###########################################################################################

#########
## PPT ##
#########
ppt_data <- read_csv(PPT_PATH, show_col_types = FALSE)
ppt_data$Date <- as.Date(ppt_data$Date)
colnames(ppt_data) <- c('time','ppt')
X_ppt <- ppt_data[ppt_data$time <= cutoff_date,]
X_ppt_f <- select_future_window(
  df = ppt_data,
  time_col = "time",
  value_col = "ppt",
  start_date = forecast_start_date,
  horizon = ranges[1],
  label = "PRISM precipitation"
)

##########
## SOIL ##
##########
soil_moisture_data <- read.csv(SOIL_PATH)
soil_moisture_data$Date <- as.Date(soil_moisture_data$Date)
colnames(soil_moisture_data) <- c('time','soil')
X_soil <- soil_moisture_data[soil_moisture_data$time <= cutoff_date,]
X_soil_f <- select_future_window(
  df = soil_moisture_data,
  time_col = "time",
  value_col = "soil",
  start_date = forecast_start_date,
  horizon = ranges[1],
  label = "soil moisture"
)

#########
## PCA ##
#########
principal_components_df <- read_csv(PCA_PATH, show_col_types = FALSE)
colnames(principal_components_df) <- c('time','Static_PCA')
X_pca <- principal_components_df[principal_components_df$time <= cutoff_date,]
X_pca_f <- select_future_window(
  df = principal_components_df,
  time_col = "time",
  value_col = "Static_PCA",
  start_date = forecast_start_date,
  horizon = ranges[1],
  label = "PCA covariate"
)

###########
## Merge ##
###########
X <- merge(X_ppt, X_soil, by = "time")
X <- merge(X, X_pca, by = "time")

X_f <- merge(X_ppt_f, X_soil_f, by = "time")
X_f <- merge(X_f, X_pca_f, by = "time")

#############
## Retrosp ##
#############
streamflow_data <- read_csv(RETROS_PATH, show_col_types = FALSE)
time_series_matrix <- as.matrix(streamflow_data[, c('USGS', 'GloFAS', 'NWS3.0')])
timestamps <- as.Date(streamflow_data$Date)
Y_usgs <- data.frame(time = timestamps, time_series_matrix)
all_data <- merge(X, Y_usgs, by = "time")
Y <- t(as.matrix(all_data[, c('USGS', 'GloFAS', 'NWS3.0')]))
Y <- log(Y) #log-log, since already logged
TT <- dim(Y)[2]
J <- dim(Y)[1] - 1
timestamps <- all_data[, 'time']



#############################
## Add Constant at the end ##
#############################
design <- family_shared_build_featurecov_design_matrices(
  history_df = all_data[, c("ppt", "soil", "Static_PCA"), drop = FALSE],
  forecast_df = X_f[, c("ppt", "soil", "Static_PCA"), drop = FALSE],
  history_dates = all_data[, "time"],
  forecast_dates = X_f[, "time"],
  feature_path = COVARIATE_FEATURES_PATH,
  fill_value = 0
)
X <- design$X
X_f <- design$X_f


## Build the matrix exactly as requested
data <- cbind(t(Y), X)

## Save an .rds to preserve the matrix object "as is"
saveRDS(
  object = data,
  file   = DATA_CBIND_RDS
)

## (Optional) Also write a CSV for quick inspection
## Note: CSV will coerce to a data frame for writing, but values are unchanged.
write.csv(
  x         = data,
  file      = DATA_CBIND_CSV,
  row.names = FALSE
)
