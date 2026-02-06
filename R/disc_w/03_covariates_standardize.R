# disc_w/03_covariates_standardize.R
#
# Covariate + retrospective-response construction for the Wishart/ensemble workflow.
# Extracted from `DISC_Optimal_Synth_Ranges_W.r` with the intent of *zero semantic
# change*: ordering, transformations, and standardization must remain identical.

# disc_w_build_covariates_and_retro(disc_w_paths, ranges)
# Inputs:
# - `disc_w_paths`: named list from `disc_w_resolve_paths()`.
# - `ranges`: numeric vector (length J) of forecast ranges per ensemble source.
# Output:
# - list(X, X_f, Y, TT, J) matching the original orchestrator variables.
disc_w_build_covariates_and_retro <- function(disc_w_paths, ranges) {
  #########
  ## PPT ##
  #########
  file_path <- disc_w_paths$prism_ppt_path
  ppt_data <- disc_w_read_prism_ppt(file_path)
  ppt_data$Date <- as.Date(ppt_data$Date)
  colnames(ppt_data) <- c("time", "ppt")
  X_ppt <- ppt_data[ppt_data$time <= "2022-12-25", ]

  start_date_idx <- which(ppt_data$time == "2022-12-26")
  end_date_idx <- start_date_idx + ranges[1]
  X_ppt_f <- ppt_data[start_date_idx:end_date_idx, c("ppt", "time")]

  ##########
  ## SOIL ##
  ##########
  csv_file_path <- disc_w_paths$soil_moisture_path
  soil_moisture_data <- disc_w_read_soil_moisture(csv_file_path)
  soil_moisture_data$Date <- as.Date(soil_moisture_data$Date)
  colnames(soil_moisture_data) <- c("time", "soil")
  X_soil <- soil_moisture_data[soil_moisture_data$time <= "2022-12-25", ]

  start_date_idx <- which(soil_moisture_data$time == "2022-12-26")
  end_date_idx <- start_date_idx + ranges[1]
  X_soil_f <- soil_moisture_data[start_date_idx:end_date_idx, c("soil", "time")]

  #########
  ## PCA ##
  #########
  components_file_path <- disc_w_paths$pca_components_path
  principal_components_df <- disc_w_read_pca_components(components_file_path)
  colnames(principal_components_df) <- c("time", "Static_PCA")
  X_pca <- principal_components_df[principal_components_df$time <= "2022-12-25", ]

  start_date_idx <- which(principal_components_df$time == "2022-12-26")
  end_date_idx <- start_date_idx + ranges[1]
  X_pca_f <- principal_components_df[start_date_idx:end_date_idx, c("Static_PCA", "time")]

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
  data_path <- disc_w_paths$retros_path
  streamflow_data <- disc_w_read_retro_streamflow(data_path)
  time_series_matrix <- as.matrix(streamflow_data[, c("USGS", "GloFAS", "NWS3.0")])
  timestamps <- as.Date(streamflow_data$Date)
  Y_usgs <- data.frame(time = timestamps, time_series_matrix)
  all_data <- merge(X, Y_usgs, by = "time")
  Y <- t(as.matrix(all_data[, c("USGS", "GloFAS", "NWS3.0")]))
  Y <- log(Y) # log-log, since already logged
  TT <- dim(Y)[2]
  J <- dim(Y)[1] - 1
  timestamps <- all_data[, "time"]

  # Remove constant?
  #############################
  ## Add Constant at the end ##
  #############################
  X <- cbind(all_data[, c("ppt", "soil", "Static_PCA")], rep(1, TT))
  X_f <- cbind(X_f[, -1], rep(1, ranges[1]))
  ########### Adding covariates
  X_ext <- matrix(NA_real_, ncol = 5, nrow = TT)
  X_ext[, 1] <- c(0, X[1:(TT - 1), 1])
  X_ext[, 2] <- c(0, 0, X[1:(TT - 2), 1])
  X_ext[, 3] <- X[1:(TT), 1]^2
  X_ext[, 4] <- c(0, X[1:(TT - 1), 1])^2
  X_ext[, 5] <- c(0, 0, X[1:(TT - 2), 1])^2
  ########### Standarized added covariates
  sd1 <- sd(X_ext[, 1])
  sd2 <- sd(X_ext[, 2])
  sd3 <- sd(X_ext[, 3])
  sd4 <- sd(X_ext[, 4])
  sd5 <- sd(X_ext[, 5])
  X_ext[, 1] <- X_ext[, 1]/sd1
  X_ext[, 2] <- X_ext[, 2]/sd2
  X_ext[, 3] <- X_ext[, 3]/sd3
  X_ext[, 4] <- X_ext[, 4]/sd4
  X_ext[, 5] <- X_ext[, 5]/sd5
  ###############################################
  ###############################################
  ###############################################
  ########## Adding covariates at the future
  X_ext_f <- matrix(NA_real_, ncol = 5, nrow = ranges[1])
  X_ext_f[, 1] <- c(X[TT, 1], X_f[1:(ranges[1] - 1), 1])
  X_ext_f[, 2] <- c(X[(TT - 1), 1], X[TT, 1], X_f[1:(ranges[1] - 2), 1])
  X_ext_f[, 3] <- X_f[, 1]^2
  X_ext_f[, 4] <- c(X[TT, 1], X_f[1:(ranges[1] - 1), 1])^2
  X_ext_f[, 5] <- c(X[(TT - 1), 1], X[TT, 1], X_f[1:(ranges[1] - 2), 1])^2
  #####################
  ## STANDARDIZATION ##
  #####################
  ##### Standarized original covs
  sd_ppt <- sd(X[, 1])
  sd_soil <- sd(X[, 2])
  sd_pca <- sd(X[, 3])
  X[, 1] <- X[, 1]/sd_ppt
  X[, 2] <- X[, 2]/sd_soil
  X[, 3] <- X[, 3]/sd_pca
  X <- cbind(X, X_ext)
  ###### Standarized future covs using historical sds
  X_f[, 1] <- X_f[, 1]/sd_ppt
  X_f[, 2] <- X_f[, 2]/sd_soil
  X_f[, 3] <- X_f[, 3]/sd_pca
  X_ext_f[, 1] <- X_ext_f[, 1]/sd1
  X_ext_f[, 2] <- X_ext_f[, 2]/sd2
  X_ext_f[, 3] <- X_ext_f[, 3]/sd3
  X_ext_f[, 4] <- X_ext_f[, 4]/sd4
  X_ext_f[, 5] <- X_ext_f[, 5]/sd5
  X_f <- cbind(X_f, X_ext_f)

  list(
    X = X,
    X_f = X_f,
    Y = Y,
    TT = TT,
    J = J
  )
}
