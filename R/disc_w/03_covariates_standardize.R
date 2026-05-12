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
  cutoff_date <- suppressWarnings(as.Date(Sys.getenv("DISC_W_CUTOFF_DATE", "2022-12-25")))
  if (is.na(cutoff_date)) cutoff_date <- as.Date("2022-12-25")
  forecast_start_date <- suppressWarnings(as.Date(Sys.getenv("DISC_W_FORECAST_START_DATE", as.character(cutoff_date + 1))))
  if (is.na(forecast_start_date)) forecast_start_date <- cutoff_date + 1

  select_future_window <- function(df, time_col, value_col, start_date, horizon, label) {
    n_needed <- as.integer(horizon)
    if (!is.finite(n_needed) || n_needed < 1L) {
      stop(sprintf("%s has invalid forecast horizon: %s", label, as.character(horizon)), call. = FALSE)
    }

    idx <- which(df[[time_col]] >= start_date)
    if (!length(idx)) {
      warning(
        sprintf(
          "%s has no rows at/after forecast start date %s; using persistence from last available value",
          label,
          as.character(start_date)
        ),
        call. = FALSE
      )
      last_idx <- nrow(df)
      last_time <- as.Date(df[[time_col]][[last_idx]])
      last_val <- df[[value_col]][[last_idx]]
      out <- data.frame(
        time = seq(last_time + 1, by = "day", length.out = n_needed),
        stringsAsFactors = FALSE
      )
      out[[value_col]] <- rep(last_val, n_needed)
      return(out[, c(value_col, "time"), drop = FALSE])
    }

    start_idx <- idx[[1]]
    end_idx <- start_idx + n_needed - 1L
    end_obs <- min(end_idx, nrow(df))
    out <- df[start_idx:end_obs, c(time_col, value_col)]
    colnames(out) <- c("time", value_col)

    if (nrow(out) < n_needed) {
      n_pad <- n_needed - nrow(out)
      last_time <- as.Date(out$time[[nrow(out)]])
      last_val <- out[[value_col]][[nrow(out)]]
      pad <- data.frame(
        time = seq(last_time + 1, by = "day", length.out = n_pad),
        stringsAsFactors = FALSE
      )
      pad[[value_col]] <- rep(last_val, n_pad)
      out <- rbind(out[, c("time", value_col), drop = FALSE], pad[, c("time", value_col), drop = FALSE])
      warning(
        sprintf(
          "%s forecast covariate horizon is short by %d rows; extending with persistence",
          label,
          n_pad
        ),
        call. = FALSE
      )
    }

    out[, c(value_col, "time"), drop = FALSE]
  }

  #########
  ## PPT ##
  #########
  file_path <- disc_w_paths$prism_ppt_path
  ppt_data <- disc_w_read_prism_ppt(file_path)
  ppt_data$Date <- as.Date(ppt_data$Date)
  colnames(ppt_data) <- c("time", "ppt")
  X_ppt <- ppt_data[ppt_data$time <= cutoff_date, ]
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
  csv_file_path <- disc_w_paths$soil_moisture_path
  soil_moisture_data <- disc_w_read_soil_moisture(csv_file_path)
  soil_moisture_data$Date <- as.Date(soil_moisture_data$Date)
  colnames(soil_moisture_data) <- c("time", "soil")
  X_soil <- soil_moisture_data[soil_moisture_data$time <= cutoff_date, ]
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
  components_file_path <- disc_w_paths$pca_components_path
  principal_components_df <- disc_w_read_pca_components(components_file_path)
  principal_components_df$time <- as.Date(principal_components_df$time)
  colnames(principal_components_df) <- c("time", "Static_PCA")
  X_pca <- principal_components_df[principal_components_df$time <= cutoff_date, ]
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
  data_path <- disc_w_paths$retros_path
  streamflow_data <- disc_w_read_retro_streamflow(data_path)
  time_series_matrix <- as.matrix(streamflow_data[, c("USGS", "GloFAS", "NWS3.0")])
  timestamps <- as.Date(streamflow_data$Date)
  Y_usgs <- data.frame(time = timestamps, time_series_matrix)
  all_data <- merge(X, Y_usgs, by = "time")
  Y <- t(as.matrix(all_data[, c("USGS", "GloFAS", "NWS3.0")]))
  # The shared retrospective contract is already log1p(cms); keep it on that
  # scale and do not apply a second log transform.
  TT <- dim(Y)[2]
  J <- dim(Y)[1] - 1
  timestamps <- all_data[, "time"]

  feature_ready <- nzchar(Sys.getenv("UNIFIED_COVARIATE_FEATURES_CSV", "")) &&
    file.exists(Sys.getenv("UNIFIED_COVARIATE_FEATURES_CSV", ""))

  if (feature_ready) {
    feature_bundle <- family_shared_build_feature_matrices(
      path = Sys.getenv("UNIFIED_COVARIATE_FEATURES_CSV", ""),
      history_dates = all_data[, "time"],
      forecast_dates = X_f[, "time"],
      fill_value = 0,
      scale_with_history = TRUE
    )
    X <- cbind(data.matrix(feature_bundle$history), rep(1, TT))
    X_f <- cbind(data.matrix(feature_bundle$forecast), rep(1, ranges[1]))
  } else {
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
    sd_ppt <- sd(X[, 1])
    sd_soil <- sd(X[, 2])
    sd_pca <- sd(X[, 3])
    X[, 1] <- X[, 1]/sd_ppt
    X[, 2] <- X[, 2]/sd_soil
    X[, 3] <- X[, 3]/sd_pca
    X <- cbind(X, X_ext)
    X_f[, 1] <- X_f[, 1]/sd_ppt
    X_f[, 2] <- X_f[, 2]/sd_soil
    X_f[, 3] <- X_f[, 3]/sd_pca
    X_ext_f[, 1] <- X_ext_f[, 1]/sd1
    X_ext_f[, 2] <- X_ext_f[, 2]/sd2
    X_ext_f[, 3] <- X_ext_f[, 3]/sd3
    X_ext_f[, 4] <- X_ext_f[, 4]/sd4
    X_ext_f[, 5] <- X_ext_f[, 5]/sd5
    X_f <- cbind(X_f, X_ext_f)
  }

  list(
    X = X,
    X_f = X_f,
    Y = Y,
    TT = TT,
    J = J
  )
}
