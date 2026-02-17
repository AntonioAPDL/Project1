# Function to concatenate matrices horizontally based on row numbers
concatenate_matrices <- function(FFF_list) {
  concatenated_list <- list()
  J <- length(FFF_list)

  if (J == 1) {
    concatenated_list[[1]] <- FFF_list[[1]]
    return(concatenated_list)
  }

  start_row <- 1
  for (j in J:2) {
    row_num <- nrow(FFF_list[[j]])
    if (is.na(row_num) || row_num <= 0L) next

    idx <- start_row:(start_row + row_num - 1L)
    concatenated_matrix <- do.call(
      cbind,
      lapply(FFF_list[1:J], function(mat) {
        out <- matrix(NA_real_, nrow = row_num, ncol = ncol(mat))
        valid <- idx[idx <= nrow(mat)]
        if (length(valid) > 0L) {
          out[seq_along(valid), ] <- mat[valid, , drop = FALSE]
        }
        out
      })
    )

    concatenated_list[[J - j + 1]] <- concatenated_matrix
    start_row <- start_row + row_num
  }

  # Handle the last remaining rows from the first matrix
  row_num <- nrow(FFF_list[[1]]) - start_row + 1L
  if (!is.na(row_num) && row_num > 0L) {
    concatenated_list[[length(concatenated_list) + 1L]] <- FFF_list[[1]][start_row:(start_row + row_num - 1L), , drop = FALSE]
  }

  return(concatenated_list)
}

ensembles_forecast <- concatenate_matrices(ensembles)
ensembles_forecast <- lapply(ensembles_forecast, t)
#############################################################################################################################################
#############################################################################################################################################
 
dM <- 1 #Fix to one?
Ones <- matrix(1, dim(model$GG)[1], dim(model$GG)[1])
Ones_ens <- matrix(1, dim(GG_list[[1]])[1], dim(GG_list[[1]])[1])
########################
C0 <- as.matrix(model$C0)
m0 <- model$m0
ex.df.mat <- as.matrix(ex.df.mat)
ex.df.mat.k <- as.matrix(ex.df.mat.k)
########################
y <- Y

crit_ELBO <- 0
ELBO <- 0
seq.elbo = ELBO
iter = 0
FLAG = TRUE
tol1 <- 1e-2
tol2 <- 1e-2
conv.check <- 0
max_iter <- 800
fast <- 0

write.csv(timestamps, TIMESTAMPS_CSV, row.names = FALSE)
# timestamps_loaded <- read.csv("/data/muscat_data/jaguir26/project1_ucsc_phd/timestamps.csv")
# timestamps_loaded$Date <- as.Date(timestamps_loaded$Date)
# head(timestamps_loaded)

###############################################################################
# Univariate block + synthesis utilities (always runs)
# Inputs:
#   - variables_*_exAL_synth_DISC_uni.RData
#   - X_f, timestamps, Y and model objects from prior modules
# Outputs:
#   - Univariate diagnostics and plots (saved in figures module)
# Dependencies:
#   - 00_paths.R, 02_helpers_core.R
###############################################################################

synthesize_samples <- function(y_reps, q_s, k = 1) {
  n.q     <- dim(y_reps)[1]
  n.samp  <- dim(y_reps)[2]
  n.times <- dim(y_reps)[3]
  stopifnot(length(q_s) == n.q, !is.unsorted(q_s))
  total_samp <- k * n.samp
  out <- matrix(NA_real_, nrow = total_samp, ncol = n.times)
  for (t_idx in seq_len(n.times)) {
      for (i in 1:total_samp) {
      u <- runif(1)
      idx <- findInterval(u, q_s)
      if((idx != 0) && (idx != n.q) ){
        q_lo <- q_s[idx]
        q_hi <- q_s[idx + 1]
        w <- (u - q_lo) / (q_hi - q_lo)
        y_lower <- quantile(y_reps[idx, , t_idx], probs = u, type = 7L, names = FALSE)
        y_upper <- quantile(y_reps[idx + 1, , t_idx], probs = u, type = 7L, names = FALSE)
        result <- (1 - w) * y_lower + w * y_upper
        out[i, t_idx] <- result
      }else{
        if(idx == 0){
          out[i, t_idx] <- quantile(y_reps[idx + 1, , t_idx], probs = u, type = 7L, names = FALSE)
        }else{
          out[i, t_idx] <- quantile(y_reps[idx, , t_idx], probs = u, type = 7L, names = FALSE)
        }
      }
    }
  }
  return(out)
}

file_path <- UNI_VAR_05
load_rdata_with_retry <- function(path, attempts = 3L, sleep_sec = 0.5, envir = parent.frame()) {
  stopifnot(is.character(path), length(path) == 1L, attempts >= 1L)
  last_err <- NULL
  for (i in seq_len(attempts)) {
    ok <- tryCatch({
      # Ensure loaded objects persist in the caller's scope (this module's run env).
      load(path, envir = envir)
      TRUE
    }, error = function(e) {
      last_err <<- e
      FALSE
    })
    if (ok) return(invisible(TRUE))
    Sys.sleep(sleep_sec)
  }
  stop(last_err)
}

quantile_label_tag <- function(label) {
  as.character(as.integer(to_quantile_label(label)))
}

load_quantile_bundle_with_alias <- function(path, target_label, source_label, suffix, attempts = 3L, sleep_sec = 0.5) {
  target_tag <- quantile_label_tag(target_label)
  source_tag <- quantile_label_tag(if (is.null(source_label) || !nzchar(as.character(source_label))) target_label else source_label)
  bundle_env <- new.env(parent = emptyenv())
  load_rdata_with_retry(path, attempts = attempts, sleep_sec = sleep_sec, envir = bundle_env)

  obj_names <- ls(bundle_env, all.names = TRUE)
  src_token <- paste0("_", source_tag, "_", suffix)
  tgt_token <- paste0("_", target_tag, "_", suffix)
  for (nm in obj_names) {
    value <- get(nm, envir = bundle_env, inherits = FALSE)
    assign(nm, value, envir = parent.frame())
    if (!identical(source_tag, target_tag)) {
      alias_name <- sub(src_token, tgt_token, nm, fixed = TRUE)
      if (!identical(alias_name, nm)) {
        assign(alias_name, value, envir = parent.frame())
      }
    }
  }
  invisible(TRUE)
}

profile_section(
  "univariate.load_vars_05",
  load_quantile_bundle_with_alias(file_path, target_label = "05", source_label = UNI_VAR_SRC_05, suffix = "exAL_synth_DISC_uni")
)



file_path <- UNI_VAR_50
profile_section(
  "univariate.load_vars_50",
  load_quantile_bundle_with_alias(file_path, target_label = "50", source_label = UNI_VAR_SRC_50, suffix = "exAL_synth_DISC_uni")
)



file_path <- UNI_VAR_95
profile_section(
  "univariate.load_vars_95",
  load_quantile_bundle_with_alias(file_path, target_label = "95", source_label = UNI_VAR_SRC_95, suffix = "exAL_synth_DISC_uni")
)



file_path <- UNI_VAR_20
profile_section(
  "univariate.load_vars_20",
  load_quantile_bundle_with_alias(file_path, target_label = "20", source_label = UNI_VAR_SRC_20, suffix = "exAL_synth_DISC_uni")
)



file_path <- UNI_VAR_35
profile_section(
  "univariate.load_vars_35",
  load_quantile_bundle_with_alias(file_path, target_label = "35", source_label = UNI_VAR_SRC_35, suffix = "exAL_synth_DISC_uni")
)



file_path <- UNI_VAR_65
profile_section(
  "univariate.load_vars_65",
  load_quantile_bundle_with_alias(file_path, target_label = "65", source_label = UNI_VAR_SRC_65, suffix = "exAL_synth_DISC_uni")
)



file_path <- UNI_VAR_80
profile_section(
  "univariate.load_vars_80",
  load_quantile_bundle_with_alias(file_path, target_label = "80", source_label = UNI_VAR_SRC_80, suffix = "exAL_synth_DISC_uni")
)


n.samp_candidates <- c(
  dim(samp.theta_5_exAL_synth_DISC_uni)[3],
  dim(samp.theta_20_exAL_synth_DISC_uni)[3],
  dim(samp.theta_35_exAL_synth_DISC_uni)[3],
  dim(samp.theta_50_exAL_synth_DISC_uni)[3],
  dim(samp.theta_65_exAL_synth_DISC_uni)[3],
  dim(samp.theta_80_exAL_synth_DISC_uni)[3],
  dim(samp.theta_95_exAL_synth_DISC_uni)[3]
)
n.samp_candidates <- n.samp_candidates[is.finite(n.samp_candidates) & n.samp_candidates > 0]
n.samp <- if (length(n.samp_candidates) > 0L) {
  as.integer(min(2000L, min(n.samp_candidates)))
} else {
  2000L
}

dim(new.theta.out_50_exAL_synth_DISC_uni$exps)
TTT_temp <- dim(new.theta.out_50_exAL_synth_DISC_uni$exps)[2]
TT
diff <- TT-TTT_temp+1
length(timestamps)
diff <- 0

par(mfrow = c(1, 1), mar = c(4, 4, 2, 1), oma = c(4, 0, 0, 0))
time_cuts <- which(timestamps %in% c("2012-08-01","2016-05-01","2016-09-15","2019-08-01") )
dates_ts_usgs <- timestamps
# idx <- time_cuts[3]:time_cuts[4]
idx <- (TT-1000-diff):(TT-diff-500)
# TTT_temp <- dim(new.theta.out_50_exAL_synth_DISC_uni$exps)[2]
# idx <- (TTT_temp-200):(TTT_temp)
percentiles <- c(0.025, 0.5, 0.975)

plot(idx, (new.theta.out_50_exAL_synth_DISC_uni$exps[1,idx])*0, ylim = c(-2, 2),  type="l", lwd = 1,
        main = "Quantile Dynamics     -    2017-2019",
        xlab = " ", ylab = "log-flow", xaxt = "n")

ac <- 0.5        
lines(idx, new.theta.out_5_exAL_synth_DISC_uni$exps[1,idx], col = 'darkred', lwd = ac)
lines(idx, new.theta.out_20_exAL_synth_DISC_uni$exps[1,idx], col = 'purple', lwd = ac)
lines(idx, new.theta.out_35_exAL_synth_DISC_uni$exps[1,idx], col = 'purple', lwd = ac)
lines(idx, new.theta.out_50_exAL_synth_DISC_uni$exps[1,idx], col = 'forestgreen', lwd = ac)
lines(idx, new.theta.out_65_exAL_synth_DISC_uni$exps[1,idx], col = 'purple', lwd = ac)
lines(idx, new.theta.out_80_exAL_synth_DISC_uni$exps[1,idx], col = 'purple', lwd = ac)
lines(idx, new.theta.out_95_exAL_synth_DISC_uni$exps[1,idx], col = 'darkblue', lwd = ac)

lines(idx, Y[1,idx+diff], col = 'black', lwd = 0.1)
points(idx, Y[1,idx+diff], col = 'gray')
points(idx, Y[1,idx+diff], col = 'black', pch = 19, cex = 0.5, lwd = 0.1)

plot(ppt_data$time,ppt_data$ppt, type = 'line')
plot(principal_components_df$time,principal_components_df$Static_PCA, type = 'line')

# start_date_idx <- which(ppt_data$time == '2022-12-26')
# end_date_idx <- which(ppt_data$time == '2022-12-26') + ranges[1]
# X_ppt_f <- ppt_data[start_date_idx:end_date_idx,c('ppt','time')]

# start_date_idx <- which(principal_components_df$time == '2022-12-26')
# end_date_idx <- which(principal_components_df$time == '2022-12-26') + ranges[1]
# X_pca_f <- principal_components_df[start_date_idx:end_date_idx,c('Static_PCA','time')]

# X_ppt_pca_f <- merge(X_ppt_f, X_pca_f, by = "time")
# X_ppt_pca_soil_f <- merge(X_ppt_pca_f, soil_moisture_data, by = "time")
# X_f <- cbind(X_ppt_pca_soil_f$ppt,X_ppt_pca_soil_f$soil)

# covariates2 <- apply(X_f, 2, standardize)
# for(i in 1:dim(covariates2)[2] ){
#     covariates2[,i] <- covariates2[,i]-min(covariates2[,i])+1
# }
# covariates2 <- log(log(covariates2+1))

# plot.ts(c(X[(TT-100):(TT),1],X_f[,1]))
# plot.ts(c(covariates[(TT-100):(TT),1],covariates2[,1]))

# X_ppt_pca_soil_f$Static_PCA
# rep(1, ranges[1])

# ###########################################################################################
# ####################################### Forecasts ######################################### 
# ###########################################################################################
# nws_forecast <- read.csv('/data/muscat_data/jaguir26/project1_ucsc_phd/nws_forecast.csv')
# nws_forecast[,-1] <- log(nws_forecast[,-1])
# num_ens_nws <- dim(nws_forecast)[2]-1

# glofas_forecast <- read.csv('/data/muscat_data/jaguir26/project1_ucsc_phd/weighted_time_series.csv')
# glofas_forecast$target_date <- as.Date(glofas_forecast$target_date)
# specific_date <- as.Date("2022-12-26")
# glofas_forecast <- glofas_forecast[glofas_forecast$target_date >= specific_date, ]
# glofas_forecast[,-1] <- log(glofas_forecast[,-1])

# num_ens_glofas <- dim(glofas_forecast)[2]-1

# ensembles <- list(glofas_forecast[,-c(1)], nws_forecast[,-c(1)])
# J <- length(ensembles)
# num_mem <- rep(NA_real_, J)
# ranges <- rep(NA_real_, J)
# for(j in 1:J){
#   num_mem[j] <- dim(ensembles[[j]])[2]
#   ranges[j] <- dim(ensembles[[j]])[1]
# }

# row_means_list <- vector("list", J + 1)
# row_means_list[[1]] <- rep(NA_real_, ranges[1])
# for (j in 1:J) {
#   row_means_list[[j + 1]] <- rep(NA_real_, ranges[1])
#   row_means_list[[j + 1]][1:ranges[j]] <- rowMeans(ensembles[[j]])
# }
# mean_forecast <- do.call(rbind, row_means_list)

# ###########################################################################################
# ####################################### Covs, Retros, More ################################ 
# ###########################################################################################

# #########
# ## PPT ##
# #########
# file_path <- "/data/muscat_data/jaguir26/project1_ucsc_phd/prism_precipitation_santa_cruz_1987_2023.csv"
# ppt_data <- read_csv(file_path, show_col_types = FALSE)
# ppt_data$Date <- as.Date(ppt_data$Date)
# colnames(ppt_data) <- c('time','ppt')
# X_ppt <- ppt_data[ppt_data$time <= '2022-12-25',]

# start_date_idx <- which(ppt_data$time == '2022-12-26')
# end_date_idx <- which(ppt_data$time == '2022-12-26') + ranges[1]
# X_ppt_f <- ppt_data[start_date_idx:end_date_idx,c('ppt','time')]

# ##########
# ## SOIL ##
# ##########
# csv_file_path <- "/data/muscat_data/jaguir26/project1_ucsc_phd/soil_moisture_data/soil_moisture_big_trees_daily_avg_1987_2023.csv"
# soil_moisture_data <- read.csv(csv_file_path)
# soil_moisture_data$Date <- as.Date(soil_moisture_data$Date)
# colnames(soil_moisture_data) <- c('time','soil')
# X_soil <- soil_moisture_data[soil_moisture_data$time <= '2022-12-25',]

# start_date_idx <- which(soil_moisture_data$time == '2022-12-26')
# end_date_idx <- which(soil_moisture_data$time == '2022-12-26') + ranges[1]
# X_soil_f <- soil_moisture_data[start_date_idx:end_date_idx,c('soil','time')]

# #########
# ## PCA ##
# #########
# components_file_path <- "/data/muscat_data/jaguir26/project1_ucsc_phd/pca.csv"
# principal_components_df <- read_csv(components_file_path, show_col_types = FALSE)
# colnames(principal_components_df) <- c('time','Static_PCA')
# X_pca <- principal_components_df[principal_components_df$time <= '2022-12-25',]

# start_date_idx <- which(principal_components_df$time == '2022-12-26')
# end_date_idx <- which(principal_components_df$time == '2022-12-26') + ranges[1]
# X_pca_f <- principal_components_df[start_date_idx:end_date_idx,c('Static_PCA','time')]

# ###########
# ## Merge ##
# ###########
# X <- merge(X_ppt, X_soil, by = "time")
# X <- merge(X, X_pca, by = "time")

# X_f <- merge(X_ppt_f, X_soil_f, by = "time")
# X_f <- merge(X_f, X_pca_f, by = "time")

# #############
# ## Retrosp ##
# #############
# data_path <- "/data/muscat_data/jaguir26/project1_ucsc_phd/retros_2022-12-25.csv"
# streamflow_data <- read_csv(data_path, show_col_types = FALSE)
# time_series_matrix <- as.matrix(streamflow_data[, c('USGS', 'GloFAS', 'NWS3.0')])
# timestamps <- as.Date(streamflow_data$Date)
# Y_usgs <- data.frame(time = timestamps, time_series_matrix)
# all_data <- merge(X, Y_usgs, by = "time")
# Y <- t(as.matrix(all_data[, c('USGS', 'GloFAS', 'NWS3.0')]))
# Y <- log(Y) #log-log, since already logged
# TT <- dim(Y)[2]
# J <- dim(Y)[1] - 1
# timestamps <- all_data[, 'time']

# #############################
# ## Add Constant at the end ##
# #############################
# X <- cbind(all_data[,c('ppt','soil','Static_PCA')], rep(1, TT))
# X_f <- cbind(X_f[,-1], rep(1, ranges[1]))

# #####################
# ## STANDARDIZATION ##
# #####################
# sd_ppt  <- sd(X[,1]) 
# sd_soil <- sd(X[,2]) 
# sd_pca  <- sd(X[,3]) 

# X[,1] <- X[,1]/sd_ppt
# X[,2] <- X[,2]/sd_soil
# X[,3] <- X[,3]/sd_pca

# X_f[,1] <- X_f[,1]/sd_ppt
# X_f[,2] <- X_f[,2]/sd_soil
# X_f[,3] <- X_f[,3]/sd_pca

a <- 30
for(i in 1:8){
plot.ts(c(X[(TT-a):TT,i],X_f[,i]))
abline(v=a, col = 'darkred')
}

sm_T95 <- matrix(new.theta.out_95_exAL_synth_DISC_uni$sm[,TT], ncol = 1)
sC_T95 <- new.theta.out_95_exAL_synth_DISC_uni$sC[,,TT]
sm_T50 <- matrix(new.theta.out_50_exAL_synth_DISC_uni$sm[,TT], ncol = 1)
sC_T50 <- new.theta.out_50_exAL_synth_DISC_uni$sC[,,TT]
sm_T5 <- matrix(new.theta.out_5_exAL_synth_DISC_uni$sm[,TT], ncol = 1)
sC_T5 <- new.theta.out_5_exAL_synth_DISC_uni$sC[,,TT]
cbind(sm_T95[8:18],sm_T50[8:18],sm_T5[8:18])

sm_T95 <- new.theta.out_95_exAL_synth_DISC_uni$sm[,] 
sm_T50 <- new.theta.out_50_exAL_synth_DISC_uni$sm[,]  
sm_T5  <- new.theta.out_5_exAL_synth_DISC_uni$sm[,]  

plot.ts(sm_T95[11,], ylim = c(-0.005,0.005) ) 
lines(sm_T50[11,])
lines(sm_T5[11,])

plot.ts(sm_T95[10,], ylim = c(0.12,0.65) )
lines(sm_T50[10,])
lines(sm_T5[10,])

plot.ts(sm_T95[9,], ylim = c(0.1,0.15) )
lines(sm_T50[9,])
lines(sm_T5[9,])


sm_T95 <- matrix(new.theta.out_95_exAL_synth_DISC_uni$sm[,TT], ncol = 1)
sC_T95 <- new.theta.out_95_exAL_synth_DISC_uni$sC[,,TT]
sm_T50 <- matrix(new.theta.out_50_exAL_synth_DISC_uni$sm[,TT], ncol = 1)
sC_T50 <- new.theta.out_50_exAL_synth_DISC_uni$sC[,,TT]
sm_T5 <- matrix(new.theta.out_5_exAL_synth_DISC_uni$sm[,TT], ncol = 1)
sC_T5 <- new.theta.out_5_exAL_synth_DISC_uni$sC[,,TT]
cbind(sm_T95[8:18],sm_T50[8:18],sm_T5[8:18])

p <- 7

print(initial_delta)

lambda2 <- initial_delta[6]
Gx <- as.matrix(bdiag(GG[1:p,1:p,TT],lambda2, diag(px)))


Gx <- array(rep(Gx, ranges[1]), dim = c(p+ppx, p+ppx, ranges[1]))

Gx[(p+1), (p+2:ppx), ] <- as.matrix(t(X_f)) * 1

print(dim(Gx))
print(c(p,ppx))
print(length(p+2:ppx))

print(dim(Gx[(p+1), (p+2:ppx), ]))
print(dim(as.matrix(t(X_f)) * 1))

c <- (1)^2
state_idx <- seq_len(p + ppx)
###############################################
sm_T <- matrix(new.theta.out_95_exAL_synth_DISC_uni$sm[state_idx,TT], ncol = 1)
sC_T <- new.theta.out_95_exAL_synth_DISC_uni$sC[state_idx, state_idx, TT]*c

FF_f <- matrix(FF[1:(p+ppx),1,1], ncol = 1)
FF_f[p+1] <- 1 
y_forecast <- array(NA_real_, dim = c(1, ranges[1]))
sm_k <- array(NA_real_, dim = c(p+ppx, 1, ranges[1]))
sm_k[,1,1] <- sm_T
y_forecast[1,1] <- sum(t(FF_f)*sm_k[,1,1])
for(k in 2:ranges[1]){
    sm_k[,1,k] <- Gx[,,k] %*% sm_k[,1,k-1]
    y_forecast[1,k] <- sum(t(FF_f)*sm_k[,1,k])
}

plot.ts(y_forecast[1,], ylim = c(-1,4), col = 'darkblue', lwd = 2)
truth_log <- log(San_Lorenzo_Daily_USGS_R$data0[San_Lorenzo_Daily_USGS_R$Date >= as.Date('2022-12-26')][1:ranges[1]])
lines(truth_log, col = 'black')
points(truth_log, col = 'black')

###############################################
sm_T <- matrix(new.theta.out_50_exAL_synth_DISC_uni$sm[state_idx,TT], ncol = 1)
sC_T <- new.theta.out_50_exAL_synth_DISC_uni$sC[state_idx, state_idx, TT]*c

FF_f <- matrix(FF[1:(p+ppx),1,1], ncol = 1)
FF_f[p+1] <- 1 
y_forecast <- array(NA_real_, dim = c(1, ranges[1]))
sm_k <- array(NA_real_, dim = c(p+ppx, 1, ranges[1]))
sm_k[,1,1] <- sm_T
y_forecast[1,1] <- sum(t(FF_f)*sm_k[,1,1])
for(k in 2:ranges[1]){
    sm_k[,1,k] <- Gx[,,k] %*% sm_k[,1,k-1]
    y_forecast[1,k] <- sum(t(FF_f)*sm_k[,1,k])
}
lines(y_forecast[1,], col = 'forestgreen', lwd = 2)


###############################################
sm_T <- matrix(new.theta.out_5_exAL_synth_DISC_uni$sm[state_idx,TT], ncol = 1)
sC_T <- new.theta.out_5_exAL_synth_DISC_uni$sC[state_idx, state_idx, TT]*c

FF_f <- matrix(FF[1:(p+ppx),1,1], ncol = 1)
FF_f[p+1] <- 1 
y_forecast <- array(NA_real_, dim = c(1, ranges[1]))
sm_k <- array(NA_real_, dim = c(p+ppx, 1, ranges[1]))
sm_k[,1,1] <- sm_T
y_forecast[1,1] <- sum(t(FF_f)*sm_k[,1,1])
for(k in 2:ranges[1]){
    sm_k[,1,k] <- Gx[,,k] %*% sm_k[,1,k-1]
    y_forecast[1,k] <- sum(t(FF_f)*sm_k[,1,k])
}
lines(y_forecast[1,], col = 'darkred', lwd = 2)


truth_log <- log(San_Lorenzo_Daily_USGS_R$data0[San_Lorenzo_Daily_USGS_R$Date >= as.Date('2022-12-26')][1:ranges[1]])
plot.ts(truth_log, col = 'black', ylim = c(-1,4))
points(truth_log, col = 'black')

###############################################
sm_T <- matrix(samp.theta_95_exAL_synth_DISC_uni[state_idx,TT,], nrow = length(state_idx))
sC_T <- new.theta.out_95_exAL_synth_DISC_uni$sC[state_idx, state_idx, TT]*c

FF_f <- matrix(FF[1:(p+ppx),1,1], ncol = 1)
FF_f[p+1] <- 1 
y_forecast <- array(NA_real_, dim = c(1, ranges[1], n.samp))

for(i in 1:n.samp){
    sm_k <- array(NA_real_, dim = c(p+ppx, 1, ranges[1]))
    sm_k[,1,1] <- sm_T[,i]
    y_forecast[1,1,i] <- sum(t(FF_f)*sm_k[,1,1])
    for(k in 2:ranges[1]){
        sm_k[,1,k] <- Gx[,,k] %*% sm_k[,1,k-1]
        y_forecast[1,k,i] <- sum(t(FF_f)*sm_k[,1,k])
    }
    lines(y_forecast[1,,i], ylim = c(-1,4), col = 'lightblue', lwd = 0.1)
}

###############################################
sm_T <- matrix(samp.theta_50_exAL_synth_DISC_uni[state_idx,TT,], nrow = length(state_idx))
sC_T <- new.theta.out_50_exAL_synth_DISC_uni$sC[state_idx, state_idx, TT]*c

FF_f <- matrix(FF[1:(p+ppx),1,1], ncol = 1)
FF_f[p+1] <- 1 
y_forecast <- array(NA_real_, dim = c(1, ranges[1], n.samp))

for(i in 1:n.samp){
    sm_k <- array(NA_real_, dim = c(p+ppx, 1, ranges[1]))
    sm_k[,1,1] <- sm_T[,i]
    y_forecast[1,1,i] <- sum(t(FF_f)*sm_k[,1,1])
    for(k in 2:ranges[1]){
        sm_k[,1,k] <- Gx[,,k] %*% sm_k[,1,k-1]
        y_forecast[1,k,i] <- sum(t(FF_f)*sm_k[,1,k])
    }
    lines(y_forecast[1,,i], col = 'lightgreen', lwd = 0.1)
}

###############################################
sm_T <- matrix(samp.theta_5_exAL_synth_DISC_uni[state_idx,TT,], nrow = length(state_idx))
sC_T <- new.theta.out_5_exAL_synth_DISC_uni$sC[state_idx, state_idx, TT]*c

FF_f <- matrix(FF[1:(p+ppx),1,1], ncol = 1)
FF_f[p+1] <- 1 
y_forecast <- array(NA_real_, dim = c(1, ranges[1], n.samp))

for(i in 1:n.samp){
    sm_k <- array(NA_real_, dim = c(p+ppx, 1, ranges[1]))
    sm_k[,1,1] <- sm_T[,i]
    y_forecast[1,1,i] <- sum(t(FF_f)*sm_k[,1,1])
    for(k in 2:ranges[1]){
        sm_k[,1,k] <- Gx[,,k] %*% sm_k[,1,k-1]
        y_forecast[1,k,i] <- sum(t(FF_f)*sm_k[,1,k])
    }
    lines(y_forecast[1,,i], col = 'red', lwd = 0.1)
}


# sm_{T+1} <- Gx_{T+1} %*% sm_T + N(0,W_{T+1}) 
# y_{T+1}  <- F_{T+1} %*% sm_{T+1} + exAL_p0(V,0,gamma) 
p <- 7

xb_forecast <- array(NA_real_,c(7,n.samp,ranges[1]))
y_forecast <- array(NA_real_,c(7,n.samp,ranges[1]))

FF_f <- matrix(FF[1:(p+ppx),1,1], ncol = 1) 
FF_f[p+1] <- 1 

# Precompute W_k = Gx_k %*% sC_T %*% t(Gx_k) for each quantile and forecast time k.
# This preserves exact behavior (same RNG calls/order) but avoids repeated matrix multiplications inside loops.
compute_W_list <- function(sC_T) {
  lapply(seq_len(ranges[1]), function(k) {
    G <- Gx[,,k]
    G %*% sC_T %*% t(G)
  })
}

sC_5_T  <- new.theta.out_5_exAL_synth_DISC_uni$sC[state_idx, state_idx, TT]  * c
sC_20_T <- new.theta.out_20_exAL_synth_DISC_uni$sC[state_idx, state_idx, TT] * c
sC_35_T <- new.theta.out_35_exAL_synth_DISC_uni$sC[state_idx, state_idx, TT] * c
sC_50_T <- new.theta.out_50_exAL_synth_DISC_uni$sC[state_idx, state_idx, TT] * c
sC_65_T <- new.theta.out_65_exAL_synth_DISC_uni$sC[state_idx, state_idx, TT] * c
sC_80_T <- new.theta.out_80_exAL_synth_DISC_uni$sC[state_idx, state_idx, TT] * c
sC_95_T <- new.theta.out_95_exAL_synth_DISC_uni$sC[state_idx, state_idx, TT] * c

W_list_5  <- compute_W_list(sC_5_T)
W_list_20 <- compute_W_list(sC_20_T)
W_list_35 <- compute_W_list(sC_35_T)
W_list_50 <- compute_W_list(sC_50_T)
W_list_65 <- compute_W_list(sC_65_T)
W_list_80 <- compute_W_list(sC_80_T)
W_list_95 <- compute_W_list(sC_95_T)


for(i in 1:n.samp){
    sm_k1 <- samp.theta_5_exAL_synth_DISC_uni[state_idx,TT,i]
    e <- rmvnorm(n = 1, sigma = W_list_5[[1]])
    sm_k1 <- Gx[,,1] %*% sm_k1 +t(e)
    xb_forecast[1,i,1] <- sum((FF_f)*sm_k1)
    
    sm_k2 <- samp.theta_20_exAL_synth_DISC_uni[state_idx,TT,i]
    e <- rmvnorm(n = 1, sigma = W_list_20[[1]])
    sm_k2 <- Gx[,,1] %*% sm_k2 +t(e)
    xb_forecast[2,i,1] <- sum((FF_f)*sm_k2)

    sm_k3 <- samp.theta_35_exAL_synth_DISC_uni[state_idx,TT,i]
    e <- rmvnorm(n = 1, sigma = W_list_35[[1]])
    sm_k3 <- Gx[,,1] %*% sm_k3 +t(e)
    xb_forecast[3,i,1] <- sum((FF_f)*sm_k3)
    
    sm_k4 <- samp.theta_50_exAL_synth_DISC_uni[state_idx,TT,i]
    e <- rmvnorm(n = 1, sigma = W_list_50[[1]])
    sm_k4 <- Gx[,,1] %*% sm_k4 +t(e)
    xb_forecast[4,i,1] <- sum((FF_f)*sm_k4)
    
    sm_k5 <- samp.theta_65_exAL_synth_DISC_uni[state_idx,TT,i]
    e <- rmvnorm(n = 1, sigma = W_list_65[[1]])
    sm_k5 <- Gx[,,1] %*% sm_k5 +t(e)
    xb_forecast[5,i,1] <- sum((FF_f)*sm_k5)
    
    sm_k6 <- samp.theta_80_exAL_synth_DISC_uni[state_idx,TT,i]
    e <- rmvnorm(n = 1, sigma = W_list_80[[1]])
    sm_k6 <- Gx[,,1] %*% sm_k6 +t(e)
    xb_forecast[6,i,1] <- sum((FF_f)*sm_k6)

    sm_k7 <- samp.theta_95_exAL_synth_DISC_uni[state_idx,TT,i]
    e <- rmvnorm(n = 1, sigma = W_list_95[[1]])
    sm_k7 <- Gx[,,1] %*% sm_k7 +t(e)
    xb_forecast[7,i,1] <- sum((FF_f)*sm_k7)

    # Cache per-sample params once (used for all k)
    gamma_95 <- samp.gamma_95_exAL_synth_DISC_uni[1,i]
    sigma_95 <- samp.sigma_95_exAL_synth_DISC_uni[1,i]
    gamma_80 <- samp.gamma_80_exAL_synth_DISC_uni[1,i]
    sigma_80 <- samp.sigma_80_exAL_synth_DISC_uni[1,i]
    gamma_65 <- samp.gamma_65_exAL_synth_DISC_uni[1,i]
    sigma_65 <- samp.sigma_65_exAL_synth_DISC_uni[1,i]
    gamma_50 <- samp.gamma_50_exAL_synth_DISC_uni[1,i]
    sigma_50 <- samp.sigma_50_exAL_synth_DISC_uni[1,i]
    gamma_35 <- samp.gamma_35_exAL_synth_DISC_uni[1,i]
    sigma_35 <- samp.sigma_35_exAL_synth_DISC_uni[1,i]
    gamma_20 <- samp.gamma_20_exAL_synth_DISC_uni[1,i]
    sigma_20 <- samp.sigma_20_exAL_synth_DISC_uni[1,i]
    gamma_5 <- samp.gamma_5_exAL_synth_DISC_uni[1,i]
    sigma_5 <- samp.sigma_5_exAL_synth_DISC_uni[1,i]
    
    p00 <- 0.95
    mu <- xb_forecast[7,i,1]
    y_forecast[7,i,1] <- rexal(1, p00, mu, sigma_95, gamma_95) 

    p00 <- 0.8
    mu <- xb_forecast[6,i,1]
    y_forecast[6,i,1] <- rexal(1, p00, mu, sigma_80, gamma_80) 

    p00 <- 0.65
    mu <- xb_forecast[5,i,1]
    y_forecast[5,i,1] <- rexal(1, p00, mu, sigma_65, gamma_65) 

    p00 <- 0.5
    mu <- xb_forecast[4,i,1]
    y_forecast[4,i,1] <- rexal(1, p00, mu, sigma_50, gamma_50) 

    p00 <- 0.35
    mu <- xb_forecast[3,i,1]
    y_forecast[3,i,1] <- rexal(1, p00, mu, sigma_35, gamma_35) 

    p00 <- 0.20
    mu <- xb_forecast[2,i,1]
    y_forecast[2,i,1] <- rexal(1, p00, mu, sigma_20, gamma_20) 

    p00 <- 0.05
    mu <- xb_forecast[1,i,1]
    y_forecast[1,i,1] <- rexal(1, p00, mu, sigma_5, gamma_5) 
        
    for(k in 2:ranges[1]){
        e <- rmvnorm(n = 1, sigma = W_list_5[[k]])
        sm_k1 <- Gx[,,k] %*% sm_k1 +t(e)
        xb_forecast[1,i,k] <- sum((FF_f)*sm_k1)

        e <- rmvnorm(n = 1, sigma = W_list_20[[k]])
        sm_k2 <- Gx[,,k] %*% sm_k2 +t(e)
        xb_forecast[2,i,k] <- sum((FF_f)*sm_k2)

        e <- rmvnorm(n = 1, sigma = W_list_35[[k]])
        sm_k3 <- Gx[,,k] %*% sm_k3 +t(e)
        xb_forecast[3,i,k] <- sum((FF_f)*sm_k3)

        e <- rmvnorm(n = 1, sigma = W_list_50[[k]])
        sm_k4 <- Gx[,,k] %*% sm_k4 +t(e)
        xb_forecast[4,i,k] <- sum((FF_f)*sm_k4)

        e <- rmvnorm(n = 1, sigma = W_list_65[[k]])
        sm_k5 <- Gx[,,k] %*% sm_k5 +t(e)
        xb_forecast[5,i,k] <- sum((FF_f)*sm_k5)

        e <- rmvnorm(n = 1, sigma = W_list_80[[k]])
        sm_k6 <- Gx[,,k] %*% sm_k6 +t(e)
        xb_forecast[6,i,k] <- sum((FF_f)*sm_k6)
        
        e <- rmvnorm(n = 1, sigma = W_list_95[[k]])
        sm_k7 <- Gx[,,k] %*% sm_k7 +t(e)
        xb_forecast[7,i,k] <- sum((FF_f)*sm_k7)

        p00 <- 0.95
        mu <- xb_forecast[7,i,k]
        y_forecast[7,i,k] <- rexal(1, p00, mu, sigma_95, gamma_95) 

        p00 <- 0.8
        mu <- xb_forecast[6,i,k]
        y_forecast[6,i,k] <- rexal(1, p00, mu, sigma_80, gamma_80) 

        p00 <- 0.65
        mu <- xb_forecast[5,i,k]
        y_forecast[5,i,k] <- rexal(1, p00, mu, sigma_65, gamma_65) 

        p00 <- 0.5
        mu <- xb_forecast[4,i,k]
        y_forecast[4,i,k] <- rexal(1, p00, mu, sigma_50, gamma_50) 

        p00 <- 0.35
        mu <- xb_forecast[3,i,k]
        y_forecast[3,i,k] <- rexal(1, p00, mu, sigma_35, gamma_35) 

        p00 <- 0.20
        mu <- xb_forecast[2,i,k]
        y_forecast[2,i,k] <- rexal(1, p00, mu, sigma_20, gamma_20) 

        p00 <- 0.05
        mu <- xb_forecast[1,i,k]
        y_forecast[1,i,k] <- rexal(1, p00, mu, sigma_5, gamma_5) 


    }
}

days_hist_uni <- 19
xb_hist_uni <- array(NA_real_,c(7,n.samp,days_hist_uni))
y_hist_uni <- array(NA_real_,c(7,n.samp,days_hist_uni))
FF_hist_uni <- matrix(FF[1:(p+ppx),1,1], ncol = 1) 
FF_hist_uni[p+1] <- 1 

for(i in 1:n.samp){
    for(t in (TT-days_hist_uni+1):TT){
        tt <- ( t -(TT-days_hist_uni+1) + 1 )
        xb_hist_uni[7,i,tt] <- sum((FF_hist_uni)*samp.theta_95_exAL_synth_DISC_uni[state_idx,t,i])
        gamma <- samp.gamma_95_exAL_synth_DISC_uni[1,i]
        sigma <- samp.sigma_95_exAL_synth_DISC_uni[1,i]
        p00 <- 0.95
        mu  <- xb_hist_uni[7,i,tt]
        y_hist_uni[7,i,tt] <- rexal(1, p00, mu, sigma, gamma)

        xb_hist_uni[6,i,tt] <- sum((FF_hist_uni)*samp.theta_80_exAL_synth_DISC_uni[state_idx,t,i])
        gamma <- samp.gamma_80_exAL_synth_DISC_uni[1,i]
        sigma <- samp.sigma_80_exAL_synth_DISC_uni[1,i]
        p00 <- 0.80
        mu  <- xb_hist_uni[6,i,tt]
        y_hist_uni[6,i,tt] <- rexal(1, p00, mu, sigma, gamma)

        xb_hist_uni[5,i,tt] <- sum((FF_hist_uni)*samp.theta_65_exAL_synth_DISC_uni[state_idx,t,i])
        gamma <- samp.gamma_65_exAL_synth_DISC_uni[1,i]
        sigma <- samp.sigma_65_exAL_synth_DISC_uni[1,i]
        p00 <- 0.65
        mu  <- xb_hist_uni[5,i,tt]
        y_hist_uni[5,i,tt] <- rexal(1, p00, mu, sigma, gamma)

        xb_hist_uni[4,i,tt] <- sum((FF_hist_uni)*samp.theta_50_exAL_synth_DISC_uni[state_idx,t,i])
        gamma <- samp.gamma_50_exAL_synth_DISC_uni[1,i]
        sigma <- samp.sigma_50_exAL_synth_DISC_uni[1,i]
        p00 <- 0.50
        mu  <- xb_hist_uni[4,i,tt]
        y_hist_uni[4,i,tt] <- rexal(1, p00, mu, sigma, gamma)

        xb_hist_uni[3,i,tt] <- sum((FF_hist_uni)*samp.theta_35_exAL_synth_DISC_uni[state_idx,t,i])
        gamma <- samp.gamma_35_exAL_synth_DISC_uni[1,i]
        sigma <- samp.sigma_35_exAL_synth_DISC_uni[1,i]
        p00 <- 0.35
        mu  <- xb_hist_uni[3,i,tt]
        y_hist_uni[3,i,tt] <- rexal(1, p00, mu, sigma, gamma)

        xb_hist_uni[2,i,tt] <- sum((FF_hist_uni)*samp.theta_20_exAL_synth_DISC_uni[state_idx,t,i])
        gamma <- samp.gamma_20_exAL_synth_DISC_uni[1,i]
        sigma <- samp.sigma_20_exAL_synth_DISC_uni[1,i]
        p00 <- 0.20
        mu  <- xb_hist_uni[2,i,tt]
        y_hist_uni[2,i,tt] <- rexal(1, p00, mu, sigma, gamma)

        xb_hist_uni[1,i,tt] <- sum((FF_hist_uni)*samp.theta_5_exAL_synth_DISC_uni[state_idx,t,i])
        gamma <- samp.gamma_5_exAL_synth_DISC_uni[1,i]
        sigma <- samp.sigma_5_exAL_synth_DISC_uni[1,i]
        p00 <- 0.05
        mu  <- xb_hist_uni[1,i,tt]
        y_hist_uni[1,i,tt] <- rexal(1, p00, mu, sigma, gamma)
    }   
}

y_reps_5 <- y_hist_uni[1,,]
y_reps_20 <- y_hist_uni[2,,]
y_reps_35 <- y_hist_uni[3,,]
y_reps_50 <- y_hist_uni[4,,]
y_reps_65 <- y_hist_uni[5,,]
y_reps_80 <- y_hist_uni[6,,]
y_reps_95 <- y_hist_uni[7,,]
for(t in 1:days_hist_uni){
    y_reps_5[,t] <- sort(y_reps_5[,t])
    y_reps_20[,t] <- sort(y_reps_20[,t])
    y_reps_35[,t] <- sort(y_reps_35[,t])
    y_reps_50[,t] <- sort(y_reps_50[,t])
    y_reps_65[,t] <- sort(y_reps_65[,t])
    y_reps_80[,t] <- sort(y_reps_80[,t])
    y_reps_95[,t] <- sort(y_reps_95[,t])
}

y_hist_uni[1,,] <- y_reps_5  
y_hist_uni[2,,] <- y_reps_20  
y_hist_uni[3,,] <- y_reps_35  
y_hist_uni[4,,] <- y_reps_50  
y_hist_uni[5,,] <- y_reps_65  
y_hist_uni[6,,] <- y_reps_80  
y_hist_uni[7,,] <- y_reps_95 

# Save in run-scoped cache
saveRDS(y_hist_uni, file = post_cache_path("y_hist_uni.rds"))

y_reps_hist_uni <- y_hist_uni

q_s    <- c(0.05, 0.2, 0.35, 0.5, 0.65, 0.8, 0.95)
n.q     <- length(q_s)
n.samp  <- n.samp
n.times <- ranges[1]

synth_hist_uni <- profile_section("univariate.synthesize_hist", synthesize_samples(exp(y_reps_hist_uni), q_s))
dim(synth_hist_uni)

synth_hist_uni_q <- colQuantiles(synth_hist_uni, probs = q_s, type = 8)
synth_hist_uni_q <- t(synth_hist_uni_q)
dim(synth_hist_uni_q)

for (t in 1:days_hist_uni) {
    synth_hist_uni[,t] <- sort(synth_hist_uni[,t])
}

y_reps_f_5 <- y_forecast[1,,]
y_reps_f_20 <- y_forecast[2,,]
y_reps_f_35 <- y_forecast[3,,]
y_reps_f_50 <- y_forecast[4,,]
y_reps_f_65 <- y_forecast[5,,]
y_reps_f_80 <- y_forecast[6,,]
y_reps_f_95 <- y_forecast[7,,]
for(t in 1:ranges[1]){
    y_reps_f_5[,t] <- sort(y_reps_f_5[,t])
    y_reps_f_20[,t] <- sort(y_reps_f_20[,t])
    y_reps_f_35[,t] <- sort(y_reps_f_35[,t])
    y_reps_f_50[,t] <- sort(y_reps_f_50[,t])
    y_reps_f_65[,t] <- sort(y_reps_f_65[,t])
    y_reps_f_80[,t] <- sort(y_reps_f_80[,t])
    y_reps_f_95[,t] <- sort(y_reps_f_95[,t])
}

y_forecast[1,,] <- y_reps_f_5  
y_forecast[2,,] <- y_reps_f_20  
y_forecast[3,,] <- y_reps_f_35  
y_forecast[4,,] <- y_reps_f_50  
y_forecast[5,,] <- y_reps_f_65  
y_forecast[6,,] <- y_reps_f_80  
y_forecast[7,,] <- y_reps_f_95 

# Save in run-scoped cache
saveRDS(y_forecast, file = post_cache_path("y_forecast_uni.rds"))

y_reps_uni <- y_forecast

q_s    <- c(0.05, 0.2, 0.35, 0.5, 0.65, 0.8, 0.95)
n.q     <- length(q_s)
n.samp  <- n.samp
n.times <- ranges[1]

synth_f2 <- profile_section("univariate.synthesize_forecast", synthesize_samples(exp(y_reps_uni), q_s))
dim(synth_f2)

synth_f2_q <- colQuantiles(synth_f2, probs = q_s, type = 8)
synth_f2_q <- t(synth_f2_q)
dim(synth_f2_q)

for (t in 1:ranges[1]) {
    synth_f2[,t] <- sort(synth_f2[,t])
}

plot.ts(rep(0,ranges[1]), ylim = c(0,12))

SL <- San_Lorenzo_Daily_USGS_R[San_Lorenzo_Daily_USGS_R$Date >= timestamps[1] , ]
SL <- SL[(TT+1):(TT+ranges[1]) , ]

for (s in 1:dim(synth_f2)[1]) {
   lines(synth_f2[s,], col = 'pink', lwd = 0.5)
}

points(SL$data0, lwd = 0.8)

for (i in 1:n.q) {
   lines(synth_f2_q[i,], col = 'gray', lwd = 2)
}

# Adding quantile bands (blue) for 95th Quantile estimation
result <- fast_col_quantiles_t(exp(xb_forecast[7, , ]), probs = c(0.025, 0.5, 0.975))
lines(result[1,], col = 'blue', lty = 2, lwd = 1)
lines(result[2,], col = 'darkblue', lwd = 1.5)
lines(result[3,], col = 'blue', lty = 2, lwd = 1)

# Adding quantile bands (blue) for 95th Quantile estimation
result <- fast_col_quantiles_t(exp(xb_forecast[1, , ]), probs = c(0.025, 0.5, 0.975))
lines(result[1,], col = 'red', lty = 2, lwd = 1)
lines(result[2,], col = 'darkred', lwd = 1.5)
lines(result[3,], col = 'red', lty = 2, lwd = 1)

# Adding quantile bands (blue) for 95th Quantile estimation
result <- fast_col_quantiles_t(exp(xb_forecast[4, , ]), probs = c(0.025, 0.5, 0.975))
lines(result[1,], col = 'green', lty = 2, lwd = 1)
lines(result[2,], col = 'forestgreen', lwd = 1.5)
lines(result[3,], col = 'green', lty = 2, lwd = 1)


result <- fast_col_quantiles_t(exp(y_reps_f_95), probs = 0.95)
lines(as.numeric(result), col = 'black', lwd = 0.5)
result <- fast_col_quantiles_t(exp(y_reps_f_80), probs = 0.80)
lines(as.numeric(result), col = 'black', lwd = 0.5)
result <- fast_col_quantiles_t(exp(y_reps_f_65), probs = 0.65)
lines(as.numeric(result), col = 'black', lwd = 0.5)
result <- fast_col_quantiles_t(exp(y_reps_f_50), probs = 0.50)
lines(as.numeric(result), col = 'black', lwd = 0.5)
result <- fast_col_quantiles_t(exp(y_reps_f_35), probs = 0.35)
lines(as.numeric(result), col = 'black', lwd = 0.5)
result <- fast_col_quantiles_t(exp(y_reps_f_20), probs = 0.20)
lines(as.numeric(result), col = 'black', lwd = 0.5)
result <- fast_col_quantiles_t(exp(y_reps_f_5), probs = 0.05)
lines(as.numeric(result), col = 'black', lwd = 0.5)

points(SL$data0, lwd = 0.8, pch = 16)

dim(synth_hist_uni)
dim(synth_hist_uni_q)
dim(synth_f2_q)
dim(synth_f2)


p <- 7
file_path <- NDLM_VAR_50
profile_section("univariate.load_disc_vars_ndlm_50", load_rdata_with_retry(file_path))

par(mfrow = c(1, 1), mar = c(4, 4, 2, 1), oma = c(4, 0, 0, 0))
time_cuts <- which(timestamps %in% c("2012-08-01","2016-05-01","2016-09-15","2019-08-01") )
dates_ts_usgs <- timestamps
idx <- time_cuts[3]:time_cuts[4]
percentiles <- c(0.025, 0.5, 0.975)

plot.ts(idx, (new.theta.out_50_NDLM_synth_DISC$exps[1,idx])*0, ylim = c(-2, 2),  type="l", lwd = 1,
        main = "Quantile Dynamics     -    2017-2019",
        xlab = " ", ylab = "log-flow", xaxt = "n")
lines(idx, Y[1,idx], col = 'black', lwd = 0.1)
points(idx, Y[1,idx], col = 'gray')
points(idx, Y[1,idx], col = 'black', pch = 19, cex = 0.5, lwd = 0.1)

# lines(idx, Y[2,idx], col = 'black', lwd = 0.1)
# points(idx, Y[2,idx], col = 'gray')
# points(idx, Y[2,idx], col = 'black', pch = 19, cex = 0.5, lwd = 0.1)

# lines(idx, Y[3,idx], col = 'black', lwd = 0.1)
# points(idx, Y[3,idx], col = 'gray')
# points(idx, Y[3,idx], col = 'black', pch = 19, cex = 0.5, lwd = 0.1)

result <- new.theta.out_50_NDLM_synth_DISC$exps[1,idx]
lines(idx, result, col = 'pink', lwd=2)

result <- new.theta.out_50_NDLM_synth_DISC$sm[1,idx]
lines(idx, result, col = 'blue', lwd=2)

result <- new.theta.out_50_NDLM_synth_DISC$sm[2,idx]
lines(idx, result, col = 'green', lwd=2)

result <- new.theta.out_50_NDLM_synth_DISC$sm[6,idx]
lines(idx, result, col = 'orange', lwd=2)

selected_dates <- dates_ts_usgs[idx] 
num_ticks <- 25
tick_positions <- pretty(idx, num_ticks) 
if (length(tick_positions) > num_ticks) {
    tick_positions <- tick_positions[seq(1, length(tick_positions), length.out = num_ticks)]
}
tick_labels <- format(selected_dates[match(tick_positions, idx)], "%Y-%m-%d")
axis(1, at = tick_positions, labels = FALSE) 
text(x = tick_positions, y = par("usr")[3] - 0.025 * diff(par("usr")[3:4]), labels = tick_labels, srt = 45, adj = 1, xpd = TRUE, cex = 0.8)
  mtext("Forest Green: 50th Quantile | Dark Red: 5th Quantile | Dark Blue: 95th Quantile | Orange: Average", side = 1, outer = TRUE, line = 2, cex = 0.8)

plot.ts(t(new.theta.out_50_NDLM_synth_DISC$sm[22:26,]))




plot.ts(idx,(new.theta.out_50_NDLM_synth_DISC$sm[c(1),idx]), ylim = c(-2,2))
lines(idx,Y[1,idx], col = 'gray')
lines(new.theta.out_50_NDLM_synth_DISC$sm[22,]+(new.theta.out_50_NDLM_synth_DISC$sm[c(1),]), col = 'red')
lines(idx,new.theta.out_50_NDLM_synth_DISC$sm[22,idx]+(new.theta.out_50_NDLM_synth_DISC$sm[c(2),idx])+(new.theta.out_50_NDLM_synth_DISC$sm[c(1),idx]), col = 'blue')

invisible(try({
  covs_list <- vector("list", J)
  ranges_per <- ranges-c(ranges[2:(J)],0)
  dim_theta <- p*(J:1)
  for(i in 1:J){
    covs_list[[i]] <- array(NA_real_,c(dim_theta[i],dim_theta[i],ranges_per[(J-i)+1]))
  }

  # Precompute dimensions and replication counts
  dim_theta <- p * (J:1)
  ranges_per <- ranges - c(ranges[2:J], 0)
  r_vec <- rev(ranges_per)

  # Hyperparams for prior
  epsilon <- 1
  nu <- dim_theta + 1 + epsilon

  # Preallocate the list of 3D arrays (diagonal matrices)
  covs_list <- mapply(function(n, r) {
    replicate(r, diag(0.01, n), simplify = "array")
  }, n = dim_theta, r = r_vec, SIMPLIFY = FALSE)

  # Example: inspect the first covariance matrix of the first period.
  # replicate(..., simplify="array") may return 2D when r == 1.
  cov2 <- covs_list[[2]]
  if (length(dim(cov2)) == 3L) {
    print(cov2[, , 1, drop = FALSE])
  } else {
    print(cov2)
  }

  GG_T <- (GG[,,TT])
  #### This Requires to define the prior inside the kalman filtering!
  sC_T <- new.theta.out_50_NDLM_synth_DISC$sC[,,TT]
  ####
  W_T <- ex.df.mat * GG_T%*%sC_T%*%t(GG_T)

  S_list <- mapply(function(n, factor) {
    # Extract the top-left submatrix of W_T of size n x n
    subW <- W_T[1:n, 1:n]
    # Multiply by factor: (nu - n - 1)
    subW * factor
  }, n = dim_theta, factor = nu - dim_theta - 1, SIMPLIFY = FALSE)

  # Check the result for the first element:
  print(S_list[[2]])

  dim(new.theta.out_50_NDLM_synth_DISC$sC_ens[[1]])
  dim(new.theta.out_50_NDLM_synth_DISC$sC_ens[[2]])
  dim(new.theta.out_50_NDLM_synth_DISC$sm_ens[[1]])
  dim(new.theta.out_50_NDLM_synth_DISC$sm_ens[[2]])
}, silent = TRUE))

file_path <- DISC_W_VAR_05
profile_section(
  "univariate.load_disc_vars_exal_05",
  load_quantile_bundle_with_alias(file_path, target_label = "05", source_label = DISC_W_VAR_SRC_05, suffix = "exAL_synth_DISC")
)



file_path <- DISC_W_VAR_50
profile_section(
  "univariate.load_disc_vars_exal_50",
  load_quantile_bundle_with_alias(file_path, target_label = "50", source_label = DISC_W_VAR_SRC_50, suffix = "exAL_synth_DISC")
)



file_path <- DISC_W_VAR_95
profile_section(
  "univariate.load_disc_vars_exal_95",
  load_quantile_bundle_with_alias(file_path, target_label = "95", source_label = DISC_W_VAR_SRC_95, suffix = "exAL_synth_DISC")
)



file_path <- DISC_W_VAR_20
profile_section(
  "univariate.load_disc_vars_exal_20",
  load_quantile_bundle_with_alias(file_path, target_label = "20", source_label = DISC_W_VAR_SRC_20, suffix = "exAL_synth_DISC")
)



file_path <- DISC_W_VAR_35
profile_section(
  "univariate.load_disc_vars_exal_35",
  load_quantile_bundle_with_alias(file_path, target_label = "35", source_label = DISC_W_VAR_SRC_35, suffix = "exAL_synth_DISC")
)



file_path <- DISC_W_VAR_65
profile_section(
  "univariate.load_disc_vars_exal_65",
  load_quantile_bundle_with_alias(file_path, target_label = "65", source_label = DISC_W_VAR_SRC_65, suffix = "exAL_synth_DISC")
)



file_path <- DISC_W_VAR_80
profile_section(
  "univariate.load_disc_vars_exal_80",
  load_quantile_bundle_with_alias(file_path, target_label = "80", source_label = DISC_W_VAR_SRC_80, suffix = "exAL_synth_DISC")
)



file_path <- NDLM_VAR_50
profile_section("univariate.load_disc_vars_ndlm_50_repeat", load_rdata_with_retry(file_path))


n.samp <- 2000

p <- 7
