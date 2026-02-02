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
data_usgs_r <- readNWISdv(siteNumbers = site_code[1], parameterCd = "00060", statCd = "00003")
San_Lorenzo_Daily_USGS_R <- data_usgs_r %>%
  mutate(timestamp = as.Date(Date),
         data0 = log(X_00060_00003*CFSToCMS_CONVERSION_FACTOR + 1)) %>%
  filter(timestamp > as.Date("1979-01-01"))
San_Lorenzo_Daily_USGS_R$time <- San_Lorenzo_Daily_USGS_R$timestamp

###########################################################################################
####################################### Forecasts ######################################### 
###########################################################################################
nws_forecast <- read.csv(NWS_FORECAST_PATH)
nws_forecast[,-1] <- log(nws_forecast[,-1])
num_ens_nws <- dim(nws_forecast)[2]-1

glofas_forecast <- read.csv(GLOFAS_FORECAST_PATH)
glofas_forecast$target_date <- as.Date(glofas_forecast$target_date)
specific_date <- as.Date("2022-12-26")
glofas_forecast <- glofas_forecast[glofas_forecast$target_date >= specific_date, ]
glofas_forecast[,-1] <- log(glofas_forecast[,-1])

num_ens_glofas <- dim(glofas_forecast)[2]-1

ensembles <- list(glofas_forecast[,-c(1)], nws_forecast[,-c(1)])
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
X_ppt <- ppt_data[ppt_data$time <= '2022-12-25',]

start_date_idx <- which(ppt_data$time == '2022-12-26')
end_date_idx <- which(ppt_data$time == '2022-12-26') + ranges[1]
X_ppt_f <- ppt_data[start_date_idx:end_date_idx,c('ppt','time')]

##########
## SOIL ##
##########
soil_moisture_data <- read.csv(SOIL_PATH)
soil_moisture_data$Date <- as.Date(soil_moisture_data$Date)
colnames(soil_moisture_data) <- c('time','soil')
X_soil <- soil_moisture_data[soil_moisture_data$time <= '2022-12-25',]

start_date_idx <- which(soil_moisture_data$time == '2022-12-26')
end_date_idx <- which(soil_moisture_data$time == '2022-12-26') + ranges[1]
X_soil_f <- soil_moisture_data[start_date_idx:end_date_idx,c('soil','time')]

#########
## PCA ##
#########
principal_components_df <- read_csv(PCA_PATH, show_col_types = FALSE)
colnames(principal_components_df) <- c('time','Static_PCA')
X_pca <- principal_components_df[principal_components_df$time <= '2022-12-25',]

start_date_idx <- which(principal_components_df$time == '2022-12-26')
end_date_idx <- which(principal_components_df$time == '2022-12-26') + ranges[1]
X_pca_f <- principal_components_df[start_date_idx:end_date_idx,c('Static_PCA','time')]

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
X <- cbind(all_data[,c('ppt','soil','Static_PCA')], rep(1, TT))
X_f <- cbind(X_f[,-1], rep(1, ranges[1]))
########### Adding covariates
X_ext <- matrix(NA_real_, ncol = 5, nrow = TT)

X_ext[,1] <- c(0,X[1:(TT-1),1])
X_ext[,2] <- c(0,0,X[1:(TT-2),1])
X_ext[,3] <- X[1:(TT),1]^2
X_ext[,4] <- c(0,X[1:(TT-1),1])^2
X_ext[,5] <- c(0,0,X[1:(TT-2),1])^2

########### Standarized added covariates
sds_ext <- apply(X_ext, 2, sd)
X_ext <- sweep(X_ext, 2, sds_ext, FUN = "/")
sd1 <- sds_ext[1]
sd2 <- sds_ext[2]
sd3 <- sds_ext[3]
sd4 <- sds_ext[4]
sd5 <- sds_ext[5]
###############################################
###############################################
###############################################
########## Adding covariates at the future
X_ext_f <- matrix(NA_real_, ncol = 5, nrow = ranges[1])
X_ext_f[,1] <- c(X[TT,1],X_f[1:(ranges[1]-1),1])
X_ext_f[,2] <- c(X[(TT-1),1],X[TT,1],X_f[1:(ranges[1]-2),1])
X_ext_f[,3] <- X_f[,1]^2
X_ext_f[,4] <- c(X[TT,1],X_f[1:(ranges[1]-1),1])^2
X_ext_f[,5] <- c(X[(TT-1),1],X[TT,1],X_f[1:(ranges[1]-2),1])^2
#####################
## STANDARDIZATION ##
#####################
##### Standarized original covs
sds_main <- apply(X[, 1:3, drop = FALSE], 2, sd)
X[, 1:3] <- sweep(X[, 1:3, drop = FALSE], 2, sds_main, FUN = "/")
sd_ppt <- sds_main[1]
sd_soil <- sds_main[2]
sd_pca <- sds_main[3]
X <- cbind(X,X_ext)
###### Standarized future covs using historical sds
X_f[,1] <- X_f[,1] / sd_ppt
X_f[,2] <- X_f[,2] / sd_soil
X_f[,3] <- X_f[,3] / sd_pca
X_ext_f <- sweep(X_ext_f, 2, sds_ext, FUN = "/")
X_f <- cbind(X_f,X_ext_f)


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
