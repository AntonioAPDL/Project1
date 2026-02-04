###############################################################################
# Figures and plotting
# Inputs:
#   - Model outputs and derived objects from prior modules
# Outputs:
#   - PNG figures (redirected by runner into run output folder)
# Dependencies:
#   - ggplot2, patchwork, dplyr, tidyr, etc.
# NOTE:
#   - Many save calls use absolute canonical paths; runner redirects to OUT_DIR.
###############################################################################

png("/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics_reproduce/All_ELBOS_DISC.png", width = 6000, height = 4000, res = 600)
par(mfrow = c(1, 8), mar = c(2, 2, 2, 1), oma = c(0, 0, 3, 0))

l <- -2500
u <- -2300
a <- c(seq.elbo_50_NDLM_synth_DISC)
a[1:1]=NaN
plot.ts(a, main = "NDLM", xlab = "Iteration", ylab = "ELBO", lwd=2, ylim = c(l,u))
a <- c(seq.elbo_5_exAL_synth_DISC)
a[1:1]=NaN
plot.ts(a, main = "exAL05", xlab = "Iteration", ylab = "ELBO", lwd=2, ylim = c(l,u))
a <- c(seq.elbo_20_exAL_synth_DISC)
a[1:1]=NaN
plot.ts(a, main = "exAL20", xlab = "Iteration", ylab = "ELBO", lwd=2, ylim = c(l,u))
a <- c(seq.elbo_35_exAL_synth_DISC)
a[1:1]=NaN
plot.ts(a, main = "exAL35", xlab = "Iteration", ylab = "ELBO", lwd=2, ylim = c(l,u))
a <- c(seq.elbo_50_exAL_synth_DISC)
a[1:1]=NaN
plot.ts(a, main = "exAL50", xlab = "Iteration", ylab = "ELBO", lwd=2, ylim = c(l,u))
a <- c(seq.elbo_65_exAL_synth_DISC)
a[1:1]=NaN
plot.ts(a, main = "exAL65", xlab = "Iteration", ylab = "ELBO", lwd=2, ylim = c(l,u))
a <- c(seq.elbo_80_exAL_synth_DISC)
a[1:1]=NaN
plot.ts(a, main = "exAL80", xlab = "Iteration", ylab = "ELBO", lwd=2, ylim = c(l,u))
a <- c(seq.elbo_95_exAL_synth_DISC)
a[1:1]=NaN
plot.ts(a, main = "exAL95", xlab = "Iteration", ylab = "ELBO", lwd=2, ylim = c(l,u))
mtext("ELBO traces", side = 3, outer = TRUE, line = 0, cex = 0.8)

dev.off()


p <- 7

ks <- -diff(c(ranges,0))
xbs <- array(NA_real_, c(7,ranges[1],n.samp))
xbs_ndlm <- array(NA_real_, c(1,ranges[1],n.samp))

xb_discrep1 <- array(NA_real_ , c(7,TT,n.samp))
xb_discrep2 <- array(NA_real_ , c(7,TT,n.samp))

F_constant_disc <- FF[1:7,1,1]

idx <- c(0)
for(j in 1:(J-1)){
    idx <- 1:ks[J-j+1] + idx[length(idx)]
    for(s in 1:n.samp){
        FF_s <- FF_list[[j]]
        theta_s <- samp.theta_ens_5_exAL_synth_DISC[[j]]$samp_theta
        if(j==J){theta_s <- aperm(theta_s, c(1,3,2))}
        xb <- t(FF_s[1:p,])%*%theta_s[1:p,,s]
        xbs[1,idx,s] <- xb[1,]

        theta_s <- samp.theta_ens_20_exAL_synth_DISC[[j]]$samp_theta
        if(j==J){theta_s <- aperm(theta_s, c(1,3,2))}
        xb <- t(FF_s[1:p,])%*%theta_s[1:p,,s]
        xbs[2,idx,s] <- xb[1,]

        theta_s <- samp.theta_ens_35_exAL_synth_DISC[[j]]$samp_theta
        if(j==J){theta_s <- aperm(theta_s, c(1,3,2))}
        xb <- t(FF_s[1:p,])%*%theta_s[1:p,,s]
        xbs[3,idx,s] <- xb[1,]

        theta_s <- samp.theta_ens_50_exAL_synth_DISC[[j]]$samp_theta
        if(j==J){theta_s <- aperm(theta_s, c(1,3,2))}
        xb <- t(FF_s[1:p,])%*%theta_s[1:p,,s]
        xbs[4,idx,s] <- xb[1,]

        theta_s <- samp.theta_ens_65_exAL_synth_DISC[[j]]$samp_theta
        if(j==J){theta_s <- aperm(theta_s, c(1,3,2))}
        xb <- t(FF_s[1:p,])%*%theta_s[1:p,,s]
        xbs[5,idx,s] <- xb[1,]

        theta_s <- samp.theta_ens_80_exAL_synth_DISC[[j]]$samp_theta
        if(j==J){theta_s <- aperm(theta_s, c(1,3,2))}
        xb <- t(FF_s[1:p,])%*%theta_s[1:p,,s]
        xbs[6,idx,s] <- xb[1,]

        theta_s <- samp.theta_ens_95_exAL_synth_DISC[[j]]$samp_theta
        if(j==J){theta_s <- aperm(theta_s, c(1,3,2))}
        xb <- t(FF_s[1:p,])%*%theta_s[1:p,,s]
        xbs[7,idx,s] <- xb[1,]
        ###########################################################################
        ###########################################################################

        if(j==1){        
        theta_samp <- samp.theta_5_exAL_synth_DISC$samp_theta
        d1_s <- F_constant_disc%*%theta_samp[8:14,,s]
        d2_s <- F_constant_disc%*%theta_samp[15:21,,s]
        xb_discrep1[1,,s] <- d1_s
        xb_discrep2[1,,s] <- d2_s

        theta_samp <- samp.theta_20_exAL_synth_DISC$samp_theta
        d1_s <- F_constant_disc%*%theta_samp[8:14,,s]
        d2_s <- F_constant_disc%*%theta_samp[15:21,,s]
        xb_discrep1[2,,s] <- d1_s
        xb_discrep2[2,,s] <- d2_s

        theta_samp <- samp.theta_35_exAL_synth_DISC$samp_theta
        d1_s <- F_constant_disc%*%theta_samp[8:14,,s]
        d2_s <- F_constant_disc%*%theta_samp[15:21,,s]
        xb_discrep1[3,,s] <- d1_s
        xb_discrep2[3,,s] <- d2_s
        
        theta_samp <- samp.theta_50_exAL_synth_DISC$samp_theta
        d1_s <- F_constant_disc%*%theta_samp[8:14,,s]
        d2_s <- F_constant_disc%*%theta_samp[15:21,,s]
        xb_discrep1[4,,s] <- d1_s
        xb_discrep2[4,,s] <- d2_s

        theta_samp <- samp.theta_65_exAL_synth_DISC$samp_theta
        d1_s <- F_constant_disc%*%theta_samp[8:14,,s]
        d2_s <- F_constant_disc%*%theta_samp[15:21,,s]
        xb_discrep1[5,,s] <- d1_s
        xb_discrep2[5,,s] <- d2_s

        theta_samp <- samp.theta_80_exAL_synth_DISC$samp_theta
        d1_s <- F_constant_disc%*%theta_samp[8:14,,s]
        d2_s <- F_constant_disc%*%theta_samp[15:21,,s]
        xb_discrep1[6,,s] <- d1_s
        xb_discrep2[6,,s] <- d2_s

        theta_samp <- samp.theta_95_exAL_synth_DISC$samp_theta
        d1_s <- F_constant_disc%*%theta_samp[8:14,,s]
        d2_s <- F_constant_disc%*%theta_samp[15:21,,s]
        xb_discrep1[7,,s] <- d1_s
        xb_discrep2[7,,s] <- d2_s
        }
    }
}


prepare_quantile_data <- function(v_d) {
  if (exists("fast_prepare_quantile_data", mode = "function")) {
    return(fast_prepare_quantile_data(v_d, probs = c(0.975, 0.5, 0.025), type = 7L, na.rm = FALSE))
  }

  v_d_transposed <- aperm(v_d, c(3, 1, 2))
  q_d_transposed <- apply(v_d_transposed, 2:3, function(x) quantile(x, probs = c(0.975, 0.5, 0.025)))
  q_d <- aperm(q_d_transposed, c(2, 3, 1))
  q_d
}

q_d_discrep1_quantiles <- prepare_quantile_data(xb_discrep1)
q_d_discrep2_quantiles <- prepare_quantile_data(xb_discrep2)



eps <- 0.0

for(j in J:J){

    idx <- 1:ks[J-j+1] + idx[length(idx)]
    tt <- 1
    for(t in (idx) ){
        # print(c(0.05,t,j))
        # print(t(Ft)%*%Sigma[1:p,1:p]%*%Ft)
        Mu <- new.theta.out_5_exAL_synth_DISC$sm_ens[[j]][,tt]
        Sigma <- new.theta.out_5_exAL_synth_DISC$sC_ens[[j]][,,tt]
        Ft <- FF_list[[j]][1:p,1]
        S <- Sigma[1:p,1:p] + diag(p)*eps
        xbs_samp <- rnorm(n = n.samp, mean = t(Ft)%*%Mu[1:p], sd = sqrt(t(Ft)%*%S%*%Ft))
        xbs[1,t,] <- xbs_samp
        # print(c(0.2,t,j))
        # print(t(Ft)%*%Sigma[1:p,1:p]%*%Ft)
        Mu <- new.theta.out_20_exAL_synth_DISC$sm_ens[[j]][,tt]
        Sigma <- new.theta.out_20_exAL_synth_DISC$sC_ens[[j]][,,tt]
        Ft <- FF_list[[j]][1:p,1]
        S <- Sigma[1:p,1:p] + diag(p)*eps
        xbs_samp <- rnorm(n = n.samp, mean = t(Ft)%*%Mu[1:p], sd = sqrt(t(Ft)%*%S%*%Ft))
        xbs[2,t,] <- xbs_samp
        # print(c(0.35,t,j))
        # print(t(Ft)%*%Sigma[1:p,1:p]%*%Ft)
        Mu <- new.theta.out_35_exAL_synth_DISC$sm_ens[[j]][,tt]
        Sigma <- new.theta.out_35_exAL_synth_DISC$sC_ens[[j]][,,tt]
        Ft <- FF_list[[j]][1:p,1]
        S <- Sigma[1:p,1:p] + diag(p)*eps
        xbs_samp <- rnorm(n = n.samp, mean = t(Ft)%*%Mu[1:p], sd = sqrt(t(Ft)%*%S%*%Ft))
        xbs[3,t,] <- xbs_samp
        # print(c(0.5,t,j))
        # print(t(Ft)%*%Sigma[1:p,1:p]%*%Ft)
        Mu <- new.theta.out_50_exAL_synth_DISC$sm_ens[[j]][,tt]
        Sigma <- new.theta.out_50_exAL_synth_DISC$sC_ens[[j]][,,tt]
        Ft <- FF_list[[j]][1:p,1]
        S <- Sigma[1:p,1:p] + diag(p)*eps
        xbs_samp <- rnorm(n = n.samp, mean = t(Ft)%*%Mu[1:p], sd = sqrt(t(Ft)%*%S%*%Ft))
        xbs[4,t,] <- xbs_samp
        # print(c(0.65,t,j))
        # print(t(Ft)%*%Sigma[1:p,1:p]%*%Ft)
        Mu <- new.theta.out_65_exAL_synth_DISC$sm_ens[[j]][,tt]
        Sigma <- new.theta.out_65_exAL_synth_DISC$sC_ens[[j]][,,tt]
        Ft <- FF_list[[j]][1:p,1]
        S <- Sigma[1:p,1:p] + diag(p)*eps
        xbs_samp <- rnorm(n = n.samp, mean = t(Ft)%*%Mu[1:p], sd = sqrt(t(Ft)%*%S%*%Ft))
        xbs[5,t,] <- xbs_samp
        # print(c(0.8,t,j))
        # print(t(Ft)%*%Sigma[1:p,1:p]%*%Ft)
        Mu <- new.theta.out_80_exAL_synth_DISC$sm_ens[[j]][,tt]
        Sigma <- new.theta.out_80_exAL_synth_DISC$sC_ens[[j]][,,tt]
        Ft <- FF_list[[j]][1:p,1]
        S <- Sigma[1:p,1:p] + diag(p)*eps
        xbs_samp <- rnorm(n = n.samp, mean = t(Ft)%*%Mu[1:p], sd = sqrt(t(Ft)%*%S%*%Ft))
        xbs[6,t,] <- xbs_samp
        # print(c(0.95,t,j))
        # print(t(Ft)%*%Sigma[1:p,1:p]%*%Ft)
        Mu <- new.theta.out_95_exAL_synth_DISC$sm_ens[[j]][,tt]
        Sigma <- new.theta.out_95_exAL_synth_DISC$sC_ens[[j]][,,tt]
        Ft <- FF_list[[j]][1:p,1]
        S <- Sigma[1:p,1:p] + diag(p)*eps
        xbs_samp <- rnorm(n = n.samp, mean = t(Ft)%*%Mu[1:p], sd = sqrt(t(Ft)%*%S%*%Ft))
        xbs[7,t,] <- xbs_samp
        tt <- tt+1
    }
}


for(t in 1:ranges[1]){
    xbs[1,t,] <- sort(xbs[1,t,])
    xbs[2,t,] <- sort(xbs[2,t,])
    xbs[3,t,] <- sort(xbs[3,t,])
    xbs[4,t,] <- sort(xbs[4,t,])
    xbs[5,t,] <- sort(xbs[5,t,])
    xbs[6,t,] <- sort(xbs[6,t,])
    xbs[7,t,] <- sort(xbs[7,t,])
}


idx <- c(0)
for(j in 1:J){
    idx <- 1:ks[J-j+1] + idx[length(idx)]
    tt <- 1
    for(t in idx){
        Mu <- new.theta.out_50_NDLM_synth_DISC$sm_ens[[j]][,tt]
        Sigma <- new.theta.out_50_NDLM_synth_DISC$sC_ens[[j]][,,tt]
        Ft <- FF_list[[j]][1:p,1]
        S <- Sigma[1:p,1:p] + diag(p)*eps
        xbs_samp <- rnorm(n = n.samp, mean = t(Ft)%*%Mu[1:p], sd = sqrt(t(Ft)%*%S%*%Ft))
        xbs_ndlm[1,t,] <- xbs_samp
        
        tt <- tt+1
    }
}

set.seed(777)

# Function Definitions
inverse_cdf_AL <- function(U, mu, sigma, p) {
  ifelse(U < p, 
         mu + (sigma / (1 - p)) * log(U / p), 
         mu - (sigma / p) * log((1 - U) / (1 - p)))
}

p_fn <- function(p0, gam) {
  (p0 - as.numeric(gam < 0)) / exp(log_g(gam)) + as.numeric(gam < 0)
}

C_fn <- function(p0, gam) {
  temp_p <- p_fn(p0, gam)
  (as.numeric(gam > 0) - temp_p)^(-1)
}

# Generalized function to handle each case
generate_y_post <- function(p0, xb_matrix, gamma_sample, sigma_sample) {
  n_rows <- dim(xb_matrix)[1]
  n_cols <- dim(xb_matrix)[2]
  y_post <- matrix(NA_real_, nrow = n_rows, ncol = n_cols)
  
  for (t in 1:n_cols) {
    s_0 <- rtruncnorm(1, a=0, b=Inf, mean = 0, sd = 1)
    u <- runif(n_rows)
    y_post[,t] <- xb_matrix[,t] + sigma_sample * abs(gamma_sample) * C_fn(p0, gamma_sample) * s_0 +  
                  sigma_sample * inverse_cdf_AL(u, 0, 1, p_fn(p0, gamma_sample))
  }
  
  return(y_post)
}


# Case 1: p0 = 0.05
p0_05 <- 0.05
xb_05_f <- t(xbs[1,,])
gam_05_f <- samp.gamma_5_exAL_synth_DISC[1,]
sig_05_f <- samp.sigma_5_exAL_synth_DISC[1,]
y_post_5 <- generate_y_post(p0_05, xb_05_f, gam_05_f, sig_05_f)

# Case 2: p0 = 0.5
p0_50 <- 0.5
xb_50_f <- t(xbs[4,,])
gam_50_f <- samp.gamma_50_exAL_synth_DISC[1,]
sig_50_f <- samp.sigma_50_exAL_synth_DISC[1,]
y_post_50 <- generate_y_post(p0_50, xb_50_f, gam_50_f, sig_50_f)

# Case 3: p0 = 0.95
p0_95 <- 0.95
xb_95_f <- t(xbs[7,,])
gam_95_f <- samp.gamma_95_exAL_synth_DISC[1,]
sig_95_f <- samp.sigma_95_exAL_synth_DISC[1,]
y_post_95 <- generate_y_post(p0_95, xb_95_f, gam_95_f, sig_95_f)

# Case 4: p0 = 0.20
p0_20 <- 0.20
xb_20_f <- t(xbs[2,,])
gam_20_f <- samp.gamma_20_exAL_synth_DISC[1,]
sig_20_f <- samp.sigma_20_exAL_synth_DISC[1,]
y_post_20 <- generate_y_post(p0_20, xb_20_f, gam_20_f, sig_20_f)

# Case 5: p0 = 0.80
p0_80 <- 0.80
xb_80_f <- t(xbs[6,,])
gam_80_f <- samp.gamma_80_exAL_synth_DISC[1,]
sig_80_f <- samp.sigma_80_exAL_synth_DISC[1,]
y_post_80 <- generate_y_post(p0_80, xb_80_f, gam_80_f, sig_80_f)

# Case 6: p0 = 0.35
p0_35 <- 0.35
xb_35_f <- t(xbs[3,,])
gam_35_f <- samp.gamma_35_exAL_synth_DISC[1,]
sig_35_f <- samp.sigma_35_exAL_synth_DISC[1,]
y_post_35 <- generate_y_post(p0_35, xb_35_f, gam_35_f, sig_35_f)

# Case 7: p0 = 0.65
p0_65 <- 0.65
xb_65_f <- t(xbs[5,,])
gam_65_f <- samp.gamma_65_exAL_synth_DISC[1,]
sig_65_f <- samp.sigma_65_exAL_synth_DISC[1,]
y_post_65 <- generate_y_post(p0_65, xb_65_f, gam_65_f, sig_65_f)

n_rows_5 <- dim(xb_05_f)[1]
n_cols_5 <- dim(xb_05_f)[2]


# dim(y_post_35)

for(t in 1:ranges[1]){
    xbs[1,t,] <- sort(xbs[1,t,])
    xbs[2,t,] <- sort(xbs[2,t,])
    xbs[3,t,] <- sort(xbs[3,t,])
    xbs[4,t,] <- sort(xbs[4,t,])
    xbs[5,t,] <- sort(xbs[5,t,])
    xbs[6,t,] <- sort(xbs[6,t,])
    xbs[7,t,] <- sort(xbs[7,t,])
}

# Function to plot lines for multiple forecasts
plot_forecast_lines <- function(idx, y_post, xb_f, n_rows, truth, color_forecast = 'gray', color_baseline = 'pink') {
  for (s in 1:n_rows) {
    # Forecast lines
    lines((length(idx) + 1):(length(idx) + length(truth)), y_post[s, ], ylab = "", col = color_forecast)
    # Baseline lines
    lines((length(idx) + 1):(length(idx) + length(truth)), xb_f[s, ], ylab = "", col = color_baseline)
  }
}

# Plot for the log-transformed truth data
plot_log_truth_data <- function(idx, Y, truth, y_post_95, y_post_5, y_post_50, y_post_20, y_post_35, y_post_80, y_post_65,
                                xb_95_f, xb_05_f, xb_50_f, xb_20_f, xb_35_f, xb_80_f, xb_65_f, n_rows) {
  plot.ts(rep(0, length(idx) + 30), ylab = "", ylim = c(-1.5, 2.5))
  lines(Y[1, idx], ylab = "")
  points(Y[1, idx], ylab = "", pch = 19)
  
  # Forecast lines
  plot_forecast_lines(idx, y_post_95, xb_95_f, n_rows, truth)
  plot_forecast_lines(idx, y_post_5, xb_05_f, n_rows, truth)
  plot_forecast_lines(idx, y_post_50, xb_50_f, n_rows, truth)
  plot_forecast_lines(idx, y_post_20, xb_20_f, n_rows, truth)
  plot_forecast_lines(idx, y_post_35, xb_35_f, n_rows, truth)
  plot_forecast_lines(idx, y_post_80, xb_80_f, n_rows, truth)
  plot_forecast_lines(idx, y_post_65, xb_65_f, n_rows, truth)
  
  # Add truth points
  points((length(idx) + 1):(length(idx) + length(truth)), truth, ylab = "", col = 'darkred', pch = 19)
}

# Plot for the exp-transformed truth data
plot_exp_truth_data <- function(idx, Y, truth, y_post_95, y_post_5, y_post_50, y_post_20, y_post_35, y_post_80, y_post_65,
                                xb_95_f, xb_05_f, xb_50_f, xb_20_f, xb_35_f, xb_80_f, xb_65_f, n_rows) {
  plot.ts(rep(0, length(idx) + 30), ylab = "", ylim = c(0, 10))
  lines(exp(Y[1, idx]), ylab = "")
  points(exp(Y[1, idx]), ylab = "", pch = 19)
  
  # Forecast lines
  plot_forecast_lines(idx, exp(y_post_95), exp(xb_95_f), n_rows, truth)
  plot_forecast_lines(idx, exp(y_post_5), exp(xb_05_f), n_rows, truth)
  plot_forecast_lines(idx, exp(y_post_50), exp(xb_50_f), n_rows, truth)
  plot_forecast_lines(idx, exp(y_post_20), exp(xb_20_f), n_rows, truth)
  plot_forecast_lines(idx, exp(y_post_35), exp(xb_35_f), n_rows, truth)
  plot_forecast_lines(idx, exp(y_post_80), exp(xb_80_f), n_rows, truth)
  plot_forecast_lines(idx, exp(y_post_65), exp(xb_65_f), n_rows, truth)
  
  # Add truth points
  points((length(idx) + 1):(length(idx) + length(truth)), truth, ylab = "", col = 'darkred', pch = 19)
}

# Applying quantile computations and mean for each case
compute_quantiles_means <- function(y_post) {
  quantiles <- fast_col_quantiles_t(y_post, probs = c(0.05, 0.5, 0.95))
  mean_values <- colMeans(y_post)
  return(list(quantiles = quantiles, means = mean_values))
}

# Generate quantiles and means for each posterior
q50 <- compute_quantiles_means(y_post_50)
q5 <- compute_quantiles_means(y_post_5)
q95 <- compute_quantiles_means(y_post_95)
q20 <- compute_quantiles_means(y_post_20)
q35 <- compute_quantiles_means(y_post_35)
q65 <- compute_quantiles_means(y_post_65)
q80 <- compute_quantiles_means(y_post_80)



# Main Code Execution

# Log-transformed truth data
truth_log <- log(San_Lorenzo_Daily_USGS_R$data0[San_Lorenzo_Daily_USGS_R$Date >= as.Date('2022-12-26')][1:ranges[1]])
idx <- (TT - 30):(TT)

# Plot log-transformed data and forecast
plot_log_truth_data(idx, Y, truth_log, y_post_95, y_post_5, y_post_50, y_post_20, y_post_35, y_post_80, y_post_65,
                    xb_95_f, xb_05_f, xb_50_f, xb_20_f, xb_35_f, xb_80_f, xb_65_f, n_rows_5)

# Raw truth data
truth_raw <- San_Lorenzo_Daily_USGS_R$data0[San_Lorenzo_Daily_USGS_R$Date >= as.Date('2022-12-26')][1:ranges[1]]

# Plot exp-transformed data and forecast
plot_exp_truth_data(idx, Y, truth_raw, y_post_95, y_post_5, y_post_50, y_post_20, y_post_35, y_post_80, y_post_65,
                    xb_95_f, xb_05_f, xb_50_f, xb_20_f, xb_35_f, xb_80_f, xb_65_f, n_rows_5)



# Applying quantile computations and mean for each case
compute_quantiles_means <- function(y_post, q0) {
  quantiles <- fast_col_quantiles_t(y_post, probs = c(q0, 0.025, 0.5, 0.975))
  mean_values <- colMeans(y_post)
  return(list(quantiles = quantiles, means = mean_values))
}

# Generate quantiles and means for each posterior
q50 <- compute_quantiles_means(y_post_50,0.5)
q5 <- compute_quantiles_means(y_post_5,0.05)
q95 <- compute_quantiles_means(y_post_95,0.95)
q20 <- compute_quantiles_means(y_post_20,0.2)
q35 <- compute_quantiles_means(y_post_35,0.35)
q65 <- compute_quantiles_means(y_post_65,0.65)
q80 <- compute_quantiles_means(y_post_80,0.8)
################################################################################################################################################
n.samp <- dim(samp.theta_50_exAL_synth_DISC$samp_theta)[3]
synth_f <- matrix(NA_real_, nrow = n.samp, ncol = ranges[1])
synth_q_f <- matrix(NA_real_, nrow = n.samp, ncol = ranges[1])
k <- 10
sigma_5  <- samp.sigma_5_exAL_synth_DISC[1, ]
sigma_20 <- samp.sigma_20_exAL_synth_DISC[1, ]
sigma_35 <- samp.sigma_35_exAL_synth_DISC[1, ]
sigma_50 <- samp.sigma_50_exAL_synth_DISC[1, ]
sigma_65 <- samp.sigma_65_exAL_synth_DISC[1, ]
sigma_80 <- samp.sigma_80_exAL_synth_DISC[1, ]
sigma_95 <- samp.sigma_95_exAL_synth_DISC[1, ]

q_refs <- rbind(
  q5$quantiles[1, ],
  q50$quantiles[1, ],
  q95$quantiles[1, ],
  q20$quantiles[1, ],
  q35$quantiles[1, ],
  q80$quantiles[1, ],
  q65$quantiles[1, ]
)

profile_section("figures.synth_weights", {
  for (t in 1:ranges[1]) {
    w1 <- exp(-k * check_loss_fn(0.05, y_post_5[, t]  - q5$quantiles[1, t])  / sigma_5)
    w2 <- exp(-k * check_loss_fn(0.50, y_post_50[, t] - q50$quantiles[1, t]) / sigma_50)
    w3 <- exp(-k * check_loss_fn(0.95, y_post_95[, t] - q95$quantiles[1, t]) / sigma_95)
    w4 <- exp(-k * check_loss_fn(0.20, y_post_20[, t] - q20$quantiles[1, t]) / sigma_20)
    w5 <- exp(-k * check_loss_fn(0.35, y_post_35[, t] - q35$quantiles[1, t]) / sigma_35)
    w6 <- exp(-k * check_loss_fn(0.80, y_post_80[, t] - q80$quantiles[1, t]) / sigma_80)
    w7 <- exp(-k * check_loss_fn(0.65, y_post_65[, t] - q65$quantiles[1, t]) / sigma_65)

    W <- cbind(w1, w2, w3, w4, w5, w6, w7)
    W <- W / rowSums(W)

    q_ref <- q_refs[, t]
    synth_q_f[, t] <- rowSums(W * matrix(q_ref, nrow = n.samp, ncol = 7, byrow = TRUE))
  }
})

q_synth <- fast_col_quantiles_t(synth_q_f, probs = c(0.025, 0.5, 0.975))
m_synth <- colMeans((synth_q_f))

################################################################################################################################################

truth<- San_Lorenzo_Daily_USGS_R$data0[San_Lorenzo_Daily_USGS_R$Date>=as.Date('2022-12-26')]
truth <- log(truth[1:ranges[1]])
idx <- (TT-30):(TT)
plot.ts(rep(0, length(idx)+30), ylab="", ylim=c(-1.5,2.5))
lines((Y[1,idx]), ylab="")
points((Y[1,idx]), ylab="", pch = 19)

for(s in 1:n.samp){
    lines((length(idx)+1):(length(idx)+length(truth)),synth_f[s,], lwd = 0.1, col='gray')
} 
for(s in 1:n.samp){
    lines((length(idx)+1):(length(idx)+length(truth)),synth_q_f[s,], lwd = 0.1, col='purple')
} 

points((length(idx)+1):(length(idx)+length(truth)), (truth), ylab="", col='darkred', pch = 19)

# lines((length(idx)+1):(length(idx)+length(truth)),q95$quantiles[3,], lwd = 0.6, col='black')
lines((length(idx)+1):(length(idx)+length(truth)),q_synth[3,], lwd = 0.6, col='black')
lines((length(idx)+1):(length(idx)+length(truth)),q_synth[1,], lwd = 0.6, col='black')

################################################################################################################################################

truth<- San_Lorenzo_Daily_USGS_R$data0[San_Lorenzo_Daily_USGS_R$Date>=as.Date('2022-12-26')]
truth <- (truth[1:ranges[1]])
idx <- (TT-30):(TT)
plot.ts(rep(0, length(idx)+30), ylab="", ylim=c(0,6))
lines(exp(Y[1,idx]), ylab="")
points(exp(Y[1,idx]), ylab="", pch = 19)

for(s in 1:n.samp){
    lines((length(idx)+1):(length(idx)+length(truth)),exp(synth_f[s,]), lwd = 0.1, col='gray')
} 
for(s in 1:n.samp){
    lines((length(idx)+1):(length(idx)+length(truth)),exp(synth_q_f[s,]), lwd = 0.1, col='purple')
} 
points((length(idx)+1):(length(idx)+length(truth)),(truth), ylab="", col='darkred', pch = 19)
lines((length(idx)+1):(length(idx)+length(truth)),exp(q_synth[3,]), lwd = 0.6, col='black')
lines((length(idx)+1):(length(idx)+length(truth)),exp(q_synth[1,]), lwd = 0.6, col='black')



xbs_retro <- array(NA_real_, c(7,TT,n.samp))
xbs_ndlm_retro <- array(NA_real_, c(1,TT,n.samp))

idx <- 1:TT
for(j in 1:J){
    for(t in idx){
        ###############################################################################
        Mu <- new.theta.out_50_NDLM_synth_DISC$sm[,t]
        Sigma <- new.theta.out_50_NDLM_synth_DISC$sC[,,t]
        Ft <- FF[,1,t]
        xbs_samp <- rnorm(n = n.samp, mean = t(Ft)%*%Mu, sd = sqrt(t(Ft)%*%Sigma%*%Ft))
        xbs_ndlm_retro[1,t,] <- xbs_samp
        ###############################################################################
        ###############################################################################
        Mu <- new.theta.out_95_exAL_synth_DISC$sm[,t]
        Sigma <- new.theta.out_95_exAL_synth_DISC$sC[,,t]
        Ft <- FF[,1,t]
        xbs_samp <- rnorm(n = n.samp, mean = t(Ft)%*%Mu, sd = sqrt(t(Ft)%*%Sigma%*%Ft))
        xbs_retro[7,t,] <- xbs_samp
        ###############################################################################
        ###############################################################################
        Mu <- new.theta.out_80_exAL_synth_DISC$sm[,t]
        Sigma <- new.theta.out_80_exAL_synth_DISC$sC[,,t]
        Ft <- FF[,1,t]
        xbs_samp <- rnorm(n = n.samp, mean = t(Ft)%*%Mu, sd = sqrt(t(Ft)%*%Sigma%*%Ft))
        xbs_retro[6,t,] <- xbs_samp
        ###############################################################################
        ###############################################################################
        Mu <- new.theta.out_65_exAL_synth_DISC$sm[,t]
        Sigma <- new.theta.out_65_exAL_synth_DISC$sC[,,t]
        Ft <- FF[,1,t]
        xbs_samp <- rnorm(n = n.samp, mean = t(Ft)%*%Mu, sd = sqrt(t(Ft)%*%Sigma%*%Ft))
        xbs_retro[5,t,] <- xbs_samp
        ###############################################################################
        ###############################################################################
        Mu <- new.theta.out_50_exAL_synth_DISC$sm[,t]
        Sigma <- new.theta.out_50_exAL_synth_DISC$sC[,,t]
        Ft <- FF[,1,t]
        xbs_samp <- rnorm(n = n.samp, mean = t(Ft)%*%Mu, sd = sqrt(t(Ft)%*%Sigma%*%Ft))
        xbs_retro[4,t,] <- xbs_samp
        ###############################################################################
        ###############################################################################
        Mu <- new.theta.out_35_exAL_synth_DISC$sm[,t]
        Sigma <- new.theta.out_35_exAL_synth_DISC$sC[,,t]
        Ft <- FF[,1,t]
        xbs_samp <- rnorm(n = n.samp, mean = t(Ft)%*%Mu, sd = sqrt(t(Ft)%*%Sigma%*%Ft))
        xbs_retro[3,t,] <- xbs_samp
        ###############################################################################
        ###############################################################################
        Mu <- new.theta.out_20_exAL_synth_DISC$sm[,t]
        Sigma <- new.theta.out_20_exAL_synth_DISC$sC[,,t]
        Ft <- FF[,1,t]
        xbs_samp <- rnorm(n = n.samp, mean = t(Ft)%*%Mu, sd = sqrt(t(Ft)%*%Sigma%*%Ft))
        xbs_retro[2,t,] <- xbs_samp
        ###############################################################################
        ###############################################################################
        Mu <- new.theta.out_5_exAL_synth_DISC$sm[,t]
        Sigma <- new.theta.out_5_exAL_synth_DISC$sC[,,t]
        Ft <- FF[,1,t]
        xbs_samp <- rnorm(n = n.samp, mean = t(Ft)%*%Mu, sd = sqrt(t(Ft)%*%Sigma%*%Ft))
        xbs_retro[1,t,] <- xbs_samp
        ###############################################################################

    }
}

for(t in 1:ranges[1]){
    xbs_retro[1,t,] <- sort(xbs_retro[1,t,])
    xbs_retro[2,t,] <- sort(xbs_retro[2,t,])
    xbs_retro[3,t,] <- sort(xbs_retro[3,t,])
    xbs_retro[4,t,] <- sort(xbs_retro[4,t,])
    xbs_retro[5,t,] <- sort(xbs_retro[5,t,])
    xbs_retro[6,t,] <- sort(xbs_retro[6,t,])
    xbs_retro[7,t,] <- sort(xbs_retro[7,t,])
}

truth<- San_Lorenzo_Daily_USGS_R$data0[San_Lorenzo_Daily_USGS_R$Date>=as.Date('2022-12-26')]
# truth <- truth[1:ranges[1]]
truth <- log(truth[1:ranges[1]]+1)

FF_t <- aperm(FF, c(2, 1, 3))
multiply_matrices <- function(slice_index) {
    FF_t[,,slice_index] %*% new.theta.out_50_exAL_synth_DISC$sm[,slice_index]
}
result_list <- lapply(1:ncol(new.theta.out_50_exAL_synth_DISC$sm), multiply_matrices)
result_array <- array(unlist(result_list), dim = c(J+1, 1, ncol(new.theta.out_50_exAL_synth_DISC$sm)))
result_array <- aperm(result_array, c(1, 3, 2))[,,1]
dim( result_array )
TT

idx <- (TT-300):TT
plot.ts(Y[1,idx], col = 'gray')
points(Y[1,idx], col = 'black')
lines(new.theta.out_50_exAL_synth_DISC$exps[1,idx], col = 'green')
lines(new.theta.out_5_exAL_synth_DISC$exps[1,idx], col = 'red')
lines(new.theta.out_95_exAL_synth_DISC$exps[1,idx], col = 'blue')
# lines(new.theta.out_50_exAL_synth$exps[1,], col = 'green')
# lines(new.theta.out_50_exAL_synth$exps[1,], col = 'green')
# lines(new.theta.out_50_exAL_synth$exps[1,], col = 'green')

dates_ts_usgs <- timestamps

# Setting up the indices
iii <- 30
idx1 <- (TT-iii):(TT+ranges[2])
idx2 <- (TT-iii):(TT+ranges[1])
idx_all <- (TT-iii):(TT+ranges[1])
idx_T <- (TT-iii):TT
idx_y <- (TT-iii):TT
idx_f <- ((iii+1)+1):((iii+1)+ranges[1])

# Initialize the matrix
q_exps <- matrix(NA_real_, nrow = 7, ncol=(ranges[1]))
png("/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics_reproduce/Allth_exal_DISC.png", width = 6000, height = 4000, res = 600)
# Base plot
plot.ts((new.theta.out_95_exAL_synth_DISC$exps[2,idx_all]) * 0, ylim = c(-2.5, 2.5),
        xlab = " ", ylab = "log-flow", xaxt = "n", col = NA, lwd = 2, main = "Dynamic Quantile:  exAL")

# Adding 'Truth' points
points((1 + length(idx_y)):(length(truth) + length(idx_y)), truth, col = 'deeppink4', pch = 19, cex = 0.7, lwd = 1)

# Adding 'Observations'
lines(Y[1,idx_y], col = 'black', lwd = 1.5)
points(Y[1,idx_y], col = 'black', pch = 16, cex = 0.6)

# # Adding 95th Quantile estimation
# d1 <- new.theta.out_95_exAL_synth_DISC$sm_ens[[1]][8,]
# d2 <- new.theta.out_95_exAL_synth_DISC$sm_ens[[2]][8,]

F_constant_disc <- FF[1:7,1,1]
d1 <- F_constant_disc%*%new.theta.out_5_exAL_synth_DISC$sm_ens[[1]][8:14,]
d2 <- F_constant_disc%*%new.theta.out_5_exAL_synth_DISC$sm_ens[[2]][8:14,]
discrep <- c(d1, d2) 
estim_dqlm <- new.theta.out_5_exAL_synth_DISC$exps[2,(TT+1):(TT+ranges[1])] - discrep
q_exps[1,] <- estim_dqlm 
lines(new.theta.out_5_exAL_synth_DISC$exps[1,idx1], col = 'darkred', lwd = 2)

F_constant_disc <- FF[1:7,1,1]
d1 <- F_constant_disc%*%new.theta.out_20_exAL_synth_DISC$sm_ens[[1]][8:14,]
d2 <- F_constant_disc%*%new.theta.out_20_exAL_synth_DISC$sm_ens[[2]][8:14,]
discrep <- c(d1, d2) 
estim_dqlm <- new.theta.out_20_exAL_synth_DISC$exps[2,(TT+1):(TT+ranges[1])] - discrep
q_exps[2,] <- estim_dqlm 
lines(new.theta.out_20_exAL_synth_DISC$exps[1,idx1], col = 'purple', lwd = 2)

F_constant_disc <- FF[1:7,1,1]
d1 <- F_constant_disc%*%new.theta.out_35_exAL_synth_DISC$sm_ens[[1]][8:14,]
d2 <- F_constant_disc%*%new.theta.out_35_exAL_synth_DISC$sm_ens[[2]][8:14,]
discrep <- c(d1, d2) 
estim_dqlm <- new.theta.out_35_exAL_synth_DISC$exps[2,(TT+1):(TT+ranges[1])] - discrep
q_exps[3,] <- estim_dqlm 
lines(new.theta.out_35_exAL_synth_DISC$exps[1,idx1], col = 'purple', lwd = 2)

F_constant_disc <- FF[1:7,1,1]
d1 <- F_constant_disc%*%new.theta.out_50_exAL_synth_DISC$sm_ens[[1]][8:14,]
d2 <- F_constant_disc%*%new.theta.out_50_exAL_synth_DISC$sm_ens[[2]][8:14,]
discrep <- c(d1, d2) 
estim_dqlm <- new.theta.out_50_exAL_synth_DISC$exps[2,(TT+1):(TT+ranges[1])] - discrep
q_exps[4,] <- estim_dqlm 
lines(new.theta.out_50_exAL_synth_DISC$exps[1,idx1], col = 'darkgreen', lwd = 2)

F_constant_disc <- FF[1:7,1,1]
d1 <- F_constant_disc%*%new.theta.out_65_exAL_synth_DISC$sm_ens[[1]][8:14,]
d2 <- F_constant_disc%*%new.theta.out_65_exAL_synth_DISC$sm_ens[[2]][8:14,]
discrep <- c(d1, d2) 
estim_dqlm <- new.theta.out_65_exAL_synth_DISC$exps[2,(TT+1):(TT+ranges[1])] - discrep
q_exps[5,] <- estim_dqlm 
lines(new.theta.out_65_exAL_synth_DISC$exps[1,idx1], col = 'purple', lwd = 2)

F_constant_disc <- FF[1:7,1,1]
d1 <- F_constant_disc%*%new.theta.out_80_exAL_synth_DISC$sm_ens[[1]][8:14,]
d2 <- F_constant_disc%*%new.theta.out_80_exAL_synth_DISC$sm_ens[[2]][8:14,]
discrep <- c(d1, d2) 
estim_dqlm <- new.theta.out_80_exAL_synth_DISC$exps[2,(TT+1):(TT+ranges[1])] - discrep
q_exps[6,] <- estim_dqlm 
lines(new.theta.out_80_exAL_synth_DISC$exps[1,idx1], col = 'purple', lwd = 2)

F_constant_disc <- FF[1:7,1,1]
d1 <- F_constant_disc%*%new.theta.out_95_exAL_synth_DISC$sm_ens[[1]][8:14,]
d2 <- F_constant_disc%*%new.theta.out_95_exAL_synth_DISC$sm_ens[[2]][8:14,]
discrep <- c(d1, d2) 
estim_dqlm <- new.theta.out_95_exAL_synth_DISC$exps[2,(TT+1):(TT+ranges[1])] - discrep
q_exps[7,] <- estim_dqlm 
lines(new.theta.out_95_exAL_synth_DISC$exps[1,idx1], col = 'darkblue', lwd = 2)


# Adding quantile bands (blue) for 95th Quantile estimation
result <- fast_row_quantiles_t(xbs[6, , ], probs = c(0.025, 0.5, 0.975))
lines(idx_f, result[1,], col = 'purple', lty = 2, lwd = 1)
lines(idx_f, result[2,], col = 'purple', lwd = 1.5)
lines(idx_f, result[3,], col = 'purple', lty = 2, lwd = 1)
# Adding quantile bands (blue) for 95th Quantile estimation
result <- fast_row_quantiles_t(xbs[5, , ], probs = c(0.025, 0.5, 0.975))
lines(idx_f, result[1,], col = 'purple', lty = 2, lwd = 1)
lines(idx_f, result[2,], col = 'purple', lwd = 1.5)
lines(idx_f, result[3,], col = 'purple', lty = 2, lwd = 1)
# Adding quantile bands (blue) for 95th Quantile estimation
result <- fast_row_quantiles_t(xbs[4, , ], probs = c(0.025, 0.5, 0.975))
lines(idx_f, result[1,], col = 'green', lty = 2, lwd = 1)
lines(idx_f, result[2,], col = 'darkgreen', lwd = 1.5)
lines(idx_f, result[3,], col = 'green', lty = 2, lwd = 1)
# Adding quantile bands (blue) for 95th Quantile estimation
result <- fast_row_quantiles_t(xbs[3, , ], probs = c(0.025, 0.5, 0.975))
lines(idx_f, result[1,], col = 'purple', lty = 2, lwd = 1)
lines(idx_f, result[2,], col = 'purple', lwd = 1.5)
lines(idx_f, result[3,], col = 'purple', lty = 2, lwd = 1)
# Adding quantile bands (blue) for 95th Quantile estimation
result <- fast_row_quantiles_t(xbs[2, , ], probs = c(0.025, 0.5, 0.975))
lines(idx_f, result[1,], col = 'purple', lty = 2, lwd = 1)
lines(idx_f, result[2,], col = 'purple', lwd = 1.5)
lines(idx_f, result[3,], col = 'purple', lty = 2, lwd = 1)
# Adding quantile bands (blue) for 95th Quantile estimation
result <- fast_row_quantiles_t(xbs[1, , ], probs = c(0.025, 0.5, 0.975))
lines(idx_f, result[1,], col = 'red', lty = 2, lwd = 1)
lines(idx_f, result[2,], col = 'darkred', lwd = 1.5)
lines(idx_f, result[3,], col = 'red', lty = 2, lwd = 1)

idx <- (TT-iii):(TT)

# Adding retrospective quantile estimation (blue)
result <- fast_row_quantiles_t(xbs_retro[1, , ], probs = c(0.025, 0.5, 0.975))
lines(1:length(idx), result[1,idx], col = 'red', lty = 2, lwd = 0.5)
lines(1:length(idx), result[2,idx], col = 'darkred', lwd = 0.5)
lines(1:length(idx), result[3,idx], col = 'red', lty = 2, lwd = 0.5)

# Adding retrospective quantile estimation (blue)
result <- fast_row_quantiles_t(xbs_retro[2, , ], probs = c(0.025, 0.5, 0.975))
lines(1:length(idx), result[1,idx], col = 'purple', lty = 2, lwd = 0.5)
lines(1:length(idx), result[2,idx], col = 'purple', lwd = 0.5)
lines(1:length(idx), result[3,idx], col = 'purple', lty = 2, lwd = 0.5)

# Adding retrospective quantile estimation (blue)
result <- fast_row_quantiles_t(xbs_retro[3, , ], probs = c(0.025, 0.5, 0.975))
lines(1:length(idx), result[1,idx], col = 'purple', lty = 2, lwd = 0.5)
lines(1:length(idx), result[2,idx], col = 'purple', lwd = 0.5)
lines(1:length(idx), result[3,idx], col = 'purple', lty = 2, lwd = 0.5)

# Adding retrospective quantile estimation (blue)
result <- fast_row_quantiles_t(xbs_retro[4, , ], probs = c(0.025, 0.5, 0.975))
lines(1:length(idx), result[1,idx], col = 'green', lty = 2, lwd = 0.5)
lines(1:length(idx), result[2,idx], col = 'darkgreen', lwd = 0.5)
lines(1:length(idx), result[3,idx], col = 'green', lty = 2, lwd = 0.5)

# Adding retrospective quantile estimation (blue)
result <- fast_row_quantiles_t(xbs_retro[5, , ], probs = c(0.025, 0.5, 0.975))
lines(1:length(idx), result[1,idx], col = 'purple', lty = 2, lwd = 0.5)
lines(1:length(idx), result[2,idx], col = 'purple', lwd = 0.5)
lines(1:length(idx), result[3,idx], col = 'purple', lty = 2, lwd = 0.5)


# Adding retrospective quantile estimation (blue)
result <- fast_row_quantiles_t(xbs_retro[6, , ], probs = c(0.025, 0.5, 0.975))
lines(1:length(idx), result[1,idx], col = 'purple', lty = 2, lwd = 0.5)
lines(1:length(idx), result[2,idx], col = 'purple', lwd = 0.5)
lines(1:length(idx), result[3,idx], col = 'purple', lty = 2, lwd = 0.5)


# Adding retrospective quantile estimation (blue)
result <- fast_row_quantiles_t(xbs_retro[7, , ], probs = c(0.025, 0.5, 0.975))
lines(1:length(idx), result[1,idx], col = 'blue', lty = 2, lwd = 0.5)
lines(1:length(idx), result[2,idx], col = 'darkblue', lwd = 0.5)
lines(1:length(idx), result[3,idx], col = 'blue', lty = 2, lwd = 0.5)


# # Adding quantile bands (orange) for NDLM estimation
# sd_ndlm <- mean(sqrt(samp.sigma_50_NDLM_synth[1,]))
# result <- apply(xbs_ndlm[1,,] + sd_ndlm * qnorm(0.5), 1, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
# lines(idx_f, result[1,], col = 'orange', lty = 2, lwd = 1)
# lines(idx_f, result[2,], col = 'orange', lwd = 1.5)
# lines(idx_f, result[3,], col = 'orange', lty = 2, lwd = 1)

# # Adding NDLM estimation
# d1 <- new.theta.out_50_NDLM_synth$sm_ens[[1]][8,]
# d2 <- new.theta.out_50_NDLM_synth$sm_ens[[2]][8,]
# discrep <- c(d1, d2) 
# estim_dqlm <- new.theta.out_50_NDLM_synth$exps[2,(TT+1):(TT+ranges[1])] - discrep
# lines(idx_f, estim_dqlm + sd_ndlm * qnorm(0.5), col = "orange", lwd = 2)
# lines(new.theta.out_50_NDLM_synth$exps[1,idx1] + sd_ndlm * qnorm(0.5), col = 'orange', lwd = 2)

# # Adding retrospective NDLM estimation (orange)
# result <- apply(xbs_ndlm_retro[1,,], 1, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
# lines(1:length(idx), result[1,idx] + sd_ndlm * qnorm(0.5), col = 'orange', lty = 2, lwd = 0.5)
# lines(1:length(idx), result[2,idx] + sd_ndlm * qnorm(0.5), col = 'darkorange', lwd = 0.5)
# lines(1:length(idx), result[3,idx] + sd_ndlm * qnorm(0.5), col = 'orange', lty = 2, lwd = 0.5)

# Adding flood levels (horizontal dashed lines) with labels
lev_flood <- c(21.76, 19.5, 16.5, 14) 
flood_labels <- c("Major Flooding", "Moderate Flooding", "Minor Flooding", "Action")
log_flood_levels <- log(lev_flood + 1)
for (i in seq_along(log_flood_levels)) {
  abline(h = log_flood_levels[i], lwd = 1, lty = 2, col = "darkgray")
  text(x = par("usr")[2] + 0.05 * diff(par("usr")[1:2]), y = log_flood_levels[i], 
       labels = flood_labels[i], col = "gray", pos = 4, cex = 0.8, font = 2)
}

# Adding date labels on the x-axis
start_date <- dates_ts_usgs[(TT - iii)]  # Starting date
days_ahead <- ranges[1] + iii            # Number of days ahead
date_sequence <- seq.Date(from = start_date, by = "day", length.out = days_ahead + 1)
selected_dates <- date_sequence
num_ticks <- 13
tick_positions <- pretty(1:length(idx2), num_ticks) 
if (length(tick_positions) > num_ticks) {
    tick_positions <- tick_positions[seq(1, length(tick_positions), length.out = num_ticks)]
}
tick_labels <- format(selected_dates[match(tick_positions, 1:length(idx2))], "%Y-%m-%d")
axis(1, at = tick_positions, labels = FALSE) 
text(x = tick_positions, y = par("usr")[3] - 0.025 * diff(par("usr")[3:4]), labels = tick_labels, 
     srt = 45, adj = 1, xpd = TRUE, cex = 0.8, col = "black")

# Adding a vertical line for the forecast start date
forecast_date <- as.Date("2022-12-25")
forecast_position <- which(selected_dates == forecast_date)
abline(v = forecast_position, col = "black", lty = 1, lwd = 0.8)

# Adding the label for the forecast start date
text(x = forecast_position, y = par("usr")[4] + 0.03 * diff(par("usr")[3:4]), 
     labels = "forecast start date", col = "red", pos = 3, cex = 1.2, font = 2)

abline(h = 0)


# lines(Y[2,idx_y], col = 'gray', lwd = 1.5)
# points(Y[2,idx_y], col = 'gray', pch = 16, cex = 0.6)

# lines(Y[3,idx_y], col = 'gray', lwd = 1.5)
# points(Y[3,idx_y], col = 'gray', pch = 16, cex = 0.6)

# lines(colMeans(Y[,idx_y]), col = 'gray', lwd = 1.5)
# points(colMeans(Y[,idx_y]), col = 'gray', pch = 16, cex = 0.6)

dev.off()

# Setting up the indices
iii <- 30
idx1 <- (TT-iii):(TT+ranges[2])
idx2 <- (TT-iii):(TT+ranges[1])
idx_all <- (TT-iii):(TT+ranges[1])
idx_T <- (TT-iii):TT
idx_y <- (TT-iii):TT
idx_f <- ((iii+1)+1):((iii+1)+ranges[1])

# Initialize the matrix
q_exps <- matrix(NA_real_, nrow = 7, ncol=(ranges[1]))

png("/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics_reproduce/All3_exal_DISC.png", width = 6000, height = 4000, res = 600)
# Base plot
plot.ts((new.theta.out_95_exAL_synth_DISC$exps[2,idx_all]) * 0, ylim = c(-2.5, 2.5),
        xlab = " ", ylab = "log-flow", xaxt = "n", col = NA, lwd = 2, main = "Dynamic Quantile:  exAL")

# Adding 'Truth' points
points((1 + length(idx_y)):(length(truth) + length(idx_y)), truth, col = 'deeppink4', pch = 19, cex = 0.7, lwd = 1)

# Adding 'Observations'
lines(Y[1,idx_y], col = 'black', lwd = 1.5)
points(Y[1,idx_y], col = 'black', pch = 16, cex = 0.6)

# Adding 95th Quantile estimation
# d1 <- new.theta.out_95_exAL_synth_DISC$sm_ens[[1]][8,]
# d2 <- new.theta.out_95_exAL_synth_DISC$sm_ens[[2]][8,]
# discrep <- c(d1, d2) 

F_constant_disc <- FF[1:7,1,1]
d1 <- F_constant_disc%*%new.theta.out_5_exAL_synth_DISC$sm_ens[[1]][8:14,]
d2 <- F_constant_disc%*%new.theta.out_5_exAL_synth_DISC$sm_ens[[2]][8:14,]
discrep <- c(d1, d2) 
estim_dqlm <- new.theta.out_5_exAL_synth_DISC$exps[2,(TT+1):(TT+ranges[1])] - discrep
q_exps[1,] <- estim_dqlm 
lines(new.theta.out_5_exAL_synth_DISC$exps[1,idx1], col = 'darkred', lwd = 2)

# F_constant_disc <- FF[1:7,1,1]
# d1 <- F_constant_disc%*%new.theta.out_20_exAL_synth_DISC$sm_ens[[1]][8:14,]
# d2 <- F_constant_disc%*%new.theta.out_20_exAL_synth_DISC$sm_ens[[2]][8:14,]
# discrep <- c(d1, d2) 
# estim_dqlm <- new.theta.out_20_exAL_synth_DISC$exps[2,(TT+1):(TT+ranges[1])] - discrep
# q_exps[2,] <- estim_dqlm 
# lines(new.theta.out_20_exAL_synth_DISC$exps[1,idx1], col = 'purple', lwd = 2)

# F_constant_disc <- FF[1:7,1,1]
# d1 <- F_constant_disc%*%new.theta.out_35_exAL_synth_DISC$sm_ens[[1]][8:14,]
# d2 <- F_constant_disc%*%new.theta.out_35_exAL_synth_DISC$sm_ens[[2]][8:14,]
# discrep <- c(d1, d2) 
# estim_dqlm <- new.theta.out_35_exAL_synth_DISC$exps[2,(TT+1):(TT+ranges[1])] - discrep
# q_exps[3,] <- estim_dqlm 
# lines(new.theta.out_35_exAL_synth_DISC$exps[1,idx1], col = 'purple', lwd = 2)

F_constant_disc <- FF[1:7,1,1]
d1 <- F_constant_disc%*%new.theta.out_50_exAL_synth_DISC$sm_ens[[1]][8:14,]
d2 <- F_constant_disc%*%new.theta.out_50_exAL_synth_DISC$sm_ens[[2]][8:14,]
discrep <- c(d1, d2) 
estim_dqlm <- new.theta.out_50_exAL_synth_DISC$exps[2,(TT+1):(TT+ranges[1])] - discrep
q_exps[4,] <- estim_dqlm 
lines(new.theta.out_50_exAL_synth_DISC$exps[1,idx1], col = 'darkgreen', lwd = 2)

# F_constant_disc <- FF[1:7,1,1]
# d1 <- F_constant_disc%*%new.theta.out_65_exAL_synth_DISC$sm_ens[[1]][8:14,]
# d2 <- F_constant_disc%*%new.theta.out_65_exAL_synth_DISC$sm_ens[[2]][8:14,]
# discrep <- c(d1, d2) 
# estim_dqlm <- new.theta.out_65_exAL_synth_DISC$exps[2,(TT+1):(TT+ranges[1])] - discrep
# q_exps[5,] <- estim_dqlm 
# lines(new.theta.out_65_exAL_synth_DISC$exps[1,idx1], col = 'purple', lwd = 2)

# F_constant_disc <- FF[1:7,1,1]
# d1 <- F_constant_disc%*%new.theta.out_80_exAL_synth_DISC$sm_ens[[1]][8:14,]
# d2 <- F_constant_disc%*%new.theta.out_80_exAL_synth_DISC$sm_ens[[2]][8:14,]
# discrep <- c(d1, d2) 
# estim_dqlm <- new.theta.out_80_exAL_synth_DISC$exps[2,(TT+1):(TT+ranges[1])] - discrep
# q_exps[6,] <- estim_dqlm 
# lines(new.theta.out_80_exAL_synth_DISC$exps[1,idx1], col = 'purple', lwd = 2)

F_constant_disc <- FF[1:7,1,1]
d1 <- F_constant_disc%*%new.theta.out_95_exAL_synth_DISC$sm_ens[[1]][8:14,]
d2 <- F_constant_disc%*%new.theta.out_95_exAL_synth_DISC$sm_ens[[2]][8:14,]
discrep <- c(d1, d2) 
estim_dqlm <- new.theta.out_95_exAL_synth_DISC$exps[2,(TT+1):(TT+ranges[1])] - discrep
q_exps[7,] <- estim_dqlm 
lines(new.theta.out_95_exAL_synth_DISC$exps[1,idx1], col = 'darkblue', lwd = 2)

# Adding quantile bands (blue) for 95th Quantile estimation
result <- fast_row_quantiles_t(xbs[7, , ], probs = c(0.025, 0.5, 0.975))
lines(idx_f, result[1,], col = 'blue', lty = 2, lwd = 1)
lines(idx_f, result[2,], col = 'darkblue', lwd = 1.5)
lines(idx_f, result[3,], col = 'blue', lty = 2, lwd = 1)

# # Adding quantile bands (blue) for 95th Quantile estimation
# result <- apply(xbs[6,,], 1, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
# lines(idx_f, result[1,], col = 'purple', lty = 2, lwd = 1)
# lines(idx_f, result[2,], col = 'purple', lwd = 1.5)
# lines(idx_f, result[3,], col = 'purple', lty = 2, lwd = 1)
# # Adding quantile bands (blue) for 95th Quantile estimation
# result <- apply(xbs[5,,], 1, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
# lines(idx_f, result[1,], col = 'purple', lty = 2, lwd = 1)
# lines(idx_f, result[2,], col = 'purple', lwd = 1.5)
# lines(idx_f, result[3,], col = 'purple', lty = 2, lwd = 1)
# Adding quantile bands (blue) for 95th Quantile estimation
result <- fast_row_quantiles_t(xbs[4, , ], probs = c(0.025, 0.5, 0.975))
lines(idx_f, result[1,], col = 'green', lty = 2, lwd = 1)
lines(idx_f, result[2,], col = 'darkgreen', lwd = 1.5)
lines(idx_f, result[3,], col = 'green', lty = 2, lwd = 1)
# # Adding quantile bands (blue) for 95th Quantile estimation
# result <- apply(xbs[3,,], 1, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
# lines(idx_f, result[1,], col = 'purple', lty = 2, lwd = 1)
# lines(idx_f, result[2,], col = 'purple', lwd = 1.5)
# lines(idx_f, result[3,], col = 'purple', lty = 2, lwd = 1)
# # Adding quantile bands (blue) for 95th Quantile estimation
# result <- apply(xbs[2,,], 1, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
# lines(idx_f, result[1,], col = 'purple', lty = 2, lwd = 1)
# lines(idx_f, result[2,], col = 'purple', lwd = 1.5)
# lines(idx_f, result[3,], col = 'purple', lty = 2, lwd = 1)
# Adding quantile bands (blue) for 95th Quantile estimation
result <- fast_row_quantiles_t(xbs[1, , ], probs = c(0.025, 0.5, 0.975))
lines(idx_f, result[1,], col = 'red', lty = 2, lwd = 1)
lines(idx_f, result[2,], col = 'darkred', lwd = 1.5)
lines(idx_f, result[3,], col = 'red', lty = 2, lwd = 1)

idx <- (TT-iii):(TT)

# Adding retrospective quantile estimation (blue)
result <- fast_row_quantiles_t(xbs_retro[1, , ], probs = c(0.025, 0.5, 0.975))
lines(1:length(idx), result[1,idx], col = 'red', lty = 2, lwd = 0.5)
lines(1:length(idx), result[2,idx], col = 'darkred', lwd = 0.5)
lines(1:length(idx), result[3,idx], col = 'red', lty = 2, lwd = 0.5)

# # Adding retrospective quantile estimation (blue)
# result <- apply(xbs_retro[2,,], 1, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
# lines(1:length(idx), result[1,idx], col = 'purple', lty = 2, lwd = 0.5)
# lines(1:length(idx), result[2,idx], col = 'purple', lwd = 0.5)
# lines(1:length(idx), result[3,idx], col = 'purple', lty = 2, lwd = 0.5)

# # Adding retrospective quantile estimation (blue)
# result <- apply(xbs_retro[3,,], 1, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
# lines(1:length(idx), result[1,idx], col = 'purple', lty = 2, lwd = 0.5)
# lines(1:length(idx), result[2,idx], col = 'purple', lwd = 0.5)
# lines(1:length(idx), result[3,idx], col = 'purple', lty = 2, lwd = 0.5)

# Adding retrospective quantile estimation (blue)
result <- fast_row_quantiles_t(xbs_retro[4, , ], probs = c(0.025, 0.5, 0.975))
lines(1:length(idx), result[1,idx], col = 'green', lty = 2, lwd = 0.5)
lines(1:length(idx), result[2,idx], col = 'darkgreen', lwd = 0.5)
lines(1:length(idx), result[3,idx], col = 'green', lty = 2, lwd = 0.5)

# # Adding retrospective quantile estimation (blue)
# result <- apply(xbs_retro[5,,], 1, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
# lines(1:length(idx), result[1,idx], col = 'purple', lty = 2, lwd = 0.5)
# lines(1:length(idx), result[2,idx], col = 'purple', lwd = 0.5)
# lines(1:length(idx), result[3,idx], col = 'purple', lty = 2, lwd = 0.5)


# # Adding retrospective quantile estimation (blue)
# result <- apply(xbs_retro[6,,], 1, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
# lines(1:length(idx), result[1,idx], col = 'purple', lty = 2, lwd = 0.5)
# lines(1:length(idx), result[2,idx], col = 'purple', lwd = 0.5)
# lines(1:length(idx), result[3,idx], col = 'purple', lty = 2, lwd = 0.5)


# Adding retrospective quantile estimation (blue)
result <- fast_row_quantiles_t(xbs_retro[7, , ], probs = c(0.025, 0.5, 0.975))
lines(1:length(idx), result[1,idx], col = 'blue', lty = 2, lwd = 0.5)
lines(1:length(idx), result[2,idx], col = 'darkblue', lwd = 0.5)
lines(1:length(idx), result[3,idx], col = 'blue', lty = 2, lwd = 0.5)


# # Adding quantile bands (orange) for NDLM estimation
# sd_ndlm <- mean(sqrt(samp.sigma_50_NDLM_synth[1,]))
# result <- apply(xbs_ndlm[1,,] + sd_ndlm * qnorm(0.5), 1, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
# lines(idx_f, result[1,], col = 'orange', lty = 2, lwd = 1)
# lines(idx_f, result[2,], col = 'orange', lwd = 1.5)
# lines(idx_f, result[3,], col = 'orange', lty = 2, lwd = 1)

# # Adding NDLM estimation
# d1 <- new.theta.out_50_NDLM_synth$sm_ens[[1]][8,]
# d2 <- new.theta.out_50_NDLM_synth$sm_ens[[2]][8,]
# discrep <- c(d1, d2) 
# estim_dqlm <- new.theta.out_50_NDLM_synth$exps[2,(TT+1):(TT+ranges[1])] - discrep
# lines(idx_f, estim_dqlm + sd_ndlm * qnorm(0.5), col = "orange", lwd = 2)
# lines(new.theta.out_50_NDLM_synth$exps[1,idx1] + sd_ndlm * qnorm(0.5), col = 'orange', lwd = 2)

# # Adding retrospective NDLM estimation (orange)
# result <- apply(xbs_ndlm_retro[1,,], 1, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
# lines(1:length(idx), result[1,idx] + sd_ndlm * qnorm(0.5), col = 'orange', lty = 2, lwd = 0.5)
# lines(1:length(idx), result[2,idx] + sd_ndlm * qnorm(0.5), col = 'darkorange', lwd = 0.5)
# lines(1:length(idx), result[3,idx] + sd_ndlm * qnorm(0.5), col = 'orange', lty = 2, lwd = 0.5)

# Adding flood levels (horizontal dashed lines) with labels
lev_flood <- c(21.76, 19.5, 16.5, 14) 
flood_labels <- c("Major Flooding", "Moderate Flooding", "Minor Flooding", "Action")
log_flood_levels <- log(lev_flood + 1)
for (i in seq_along(log_flood_levels)) {
  abline(h = log_flood_levels[i], lwd = 1, lty = 2, col = "darkgray")
  text(x = par("usr")[2] + 0.05 * diff(par("usr")[1:2]), y = log_flood_levels[i], 
       labels = flood_labels[i], col = "gray", pos = 4, cex = 0.8, font = 2)
}

# Adding date labels on the x-axis
start_date <- dates_ts_usgs[(TT - iii)]  # Starting date
days_ahead <- ranges[1] + iii            # Number of days ahead
date_sequence <- seq.Date(from = start_date, by = "day", length.out = days_ahead + 1)
selected_dates <- date_sequence
num_ticks <- 13
tick_positions <- pretty(1:length(idx2), num_ticks) 
if (length(tick_positions) > num_ticks) {
    tick_positions <- tick_positions[seq(1, length(tick_positions), length.out = num_ticks)]
}
tick_labels <- format(selected_dates[match(tick_positions, 1:length(idx2))], "%Y-%m-%d")
axis(1, at = tick_positions, labels = FALSE) 
text(x = tick_positions, y = par("usr")[3] - 0.025 * diff(par("usr")[3:4]), labels = tick_labels, 
     srt = 45, adj = 1, xpd = TRUE, cex = 0.8, col = "black")

# Adding a vertical line for the forecast start date
forecast_date <- as.Date("2022-12-25")
forecast_position <- which(selected_dates == forecast_date)
abline(v = forecast_position, col = "black", lty = 1, lwd = 0.8)

# Adding the label for the forecast start date
text(x = forecast_position, y = par("usr")[4] + 0.03 * diff(par("usr")[3:4]), 
     labels = "forecast start date", col = "red", pos = 3, cex = 1.2, font = 2)

abline(h = 0)


# lines(Y[2,idx_y], col = 'gray', lwd = 1.5)
# points(Y[2,idx_y], col = 'gray', pch = 16, cex = 0.6)

# lines(Y[3,idx_y], col = 'gray', lwd = 1.5)
# points(Y[3,idx_y], col = 'gray', pch = 16, cex = 0.6)

# lines(colMeans(Y[,idx_y]), col = 'gray', lwd = 1.5)
# points(colMeans(Y[,idx_y]), col = 'gray', pch = 16, cex = 0.6)

dev.off()

# Setting up the indices
iii <- 30
idx1 <- (TT-iii):(TT+ranges[2])
idx2 <- (TT-iii):(TT+ranges[1])
idx_all <- (TT-iii):(TT+ranges[1])
idx_T <- (TT-iii):TT
idx_y <- (TT-iii):TT
idx_f <- ((iii+1)+1):((iii+1)+ranges[1])

# Initialize the matrix
# q_exps <- matrix(NA_real_, nrow = 7, ncol=(ranges[1]))

png("/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics_reproduce/Allth_ndlm_DISC.png", width = 6000, height = 4000, res = 600)
# Base plot
plot.ts((new.theta.out_95_exAL_synth_DISC$exps[2,idx_all]) * 0, ylim = c(-2.5, 2.5),
        xlab = " ", ylab = "log-flow", xaxt = "n", col = NA, lwd = 2, main = "Dynamic Quantile: NDLM")

# Adding 'Truth' points
points((1 + length(idx_y)):(length(truth) + length(idx_y)), truth, col = 'deeppink4', pch = 19, cex = 0.7, lwd = 1)

# Adding 'Observations'
lines(Y[1,idx_y], col = 'black', lwd = 1.5)
points(Y[1,idx_y], col = 'black', pch = 16, cex = 0.6)

# # Adding 95th Quantile estimation
# d1 <- new.theta.out_95_exAL_synth$sm_ens[[1]][8,]
# d2 <- new.theta.out_95_exAL_synth$sm_ens[[2]][8,]
# discrep <- c(d1, d2) 

# estim_dqlm <- new.theta.out_5_exAL_synth$exps[2,(TT+1):(TT+ranges[1])] - discrep
# q_exps[1,] <- estim_dqlm 
# lines(new.theta.out_5_exAL_synth$exps[1,idx1], col = 'darkred', lwd = 2)

# estim_dqlm <- new.theta.out_20_exAL_synth$exps[2,(TT+1):(TT+ranges[1])] - discrep
# q_exps[2,] <- estim_dqlm 
# lines(new.theta.out_20_exAL_synth$exps[1,idx1], col = 'purple', lwd = 2)

# estim_dqlm <- new.theta.out_35_exAL_synth$exps[2,(TT+1):(TT+ranges[1])] - discrep
# q_exps[3,] <- estim_dqlm 
# lines(new.theta.out_35_exAL_synth$exps[1,idx1], col = 'purple', lwd = 2)

# estim_dqlm <- new.theta.out_50_exAL_synth$exps[2,(TT+1):(TT+ranges[1])] - discrep
# q_exps[4,] <- estim_dqlm 
# lines(new.theta.out_50_exAL_synth$exps[1,idx1], col = 'darkgreen', lwd = 2)

# estim_dqlm <- new.theta.out_65_exAL_synth$exps[2,(TT+1):(TT+ranges[1])] - discrep
# q_exps[5,] <- estim_dqlm 
# lines(new.theta.out_65_exAL_synth$exps[1,idx1], col = 'purple', lwd = 2)

# estim_dqlm <- new.theta.out_80_exAL_synth$exps[2,(TT+1):(TT+ranges[1])] - discrep
# q_exps[6,] <- estim_dqlm 
# lines(new.theta.out_80_exAL_synth$exps[1,idx1], col = 'purple', lwd = 2)

# estim_dqlm <- new.theta.out_95_exAL_synth$exps[2,(TT+1):(TT+ranges[1])] - discrep
# q_exps[7,] <- estim_dqlm 
# lines(new.theta.out_95_exAL_synth$exps[1,idx1], col = 'darkblue', lwd = 2)

# # Adding quantile bands (blue) for 95th Quantile estimation
# result <- apply(xbs[7,,], 1, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
# lines(idx_f, result[1,], col = 'blue', lty = 2, lwd = 1)
# lines(idx_f, result[2,], col = 'darkblue', lwd = 1.5)
# lines(idx_f, result[3,], col = 'blue', lty = 2, lwd = 1)

# # Adding quantile bands (blue) for 95th Quantile estimation
# result <- apply(xbs[6,,], 1, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
# lines(idx_f, result[1,], col = 'purple', lty = 2, lwd = 1)
# lines(idx_f, result[2,], col = 'purple', lwd = 1.5)
# lines(idx_f, result[3,], col = 'purple', lty = 2, lwd = 1)
# # Adding quantile bands (blue) for 95th Quantile estimation
# result <- apply(xbs[5,,], 1, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
# lines(idx_f, result[1,], col = 'purple', lty = 2, lwd = 1)
# lines(idx_f, result[2,], col = 'purple', lwd = 1.5)
# lines(idx_f, result[3,], col = 'purple', lty = 2, lwd = 1)
# # Adding quantile bands (blue) for 95th Quantile estimation
# result <- apply(xbs[4,,], 1, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
# lines(idx_f, result[1,], col = 'green', lty = 2, lwd = 1)
# lines(idx_f, result[2,], col = 'darkgreen', lwd = 1.5)
# lines(idx_f, result[3,], col = 'blue', lty = 2, lwd = 1)
# # Adding quantile bands (blue) for 95th Quantile estimation
# result <- apply(xbs[3,,], 1, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
# lines(idx_f, result[1,], col = 'purple', lty = 2, lwd = 1)
# lines(idx_f, result[2,], col = 'purple', lwd = 1.5)
# lines(idx_f, result[3,], col = 'purple', lty = 2, lwd = 1)
# # Adding quantile bands (blue) for 95th Quantile estimation
# result <- apply(xbs[2,,], 1, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
# lines(idx_f, result[1,], col = 'purple', lty = 2, lwd = 1)
# lines(idx_f, result[2,], col = 'purple', lwd = 1.5)
# lines(idx_f, result[3,], col = 'purple', lty = 2, lwd = 1)
# # Adding quantile bands (blue) for 95th Quantile estimation
# result <- apply(xbs[1,,], 1, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
# lines(idx_f, result[1,], col = 'red', lty = 2, lwd = 1)
# lines(idx_f, result[2,], col = 'darkred', lwd = 1.5)
# lines(idx_f, result[3,], col = 'red', lty = 2, lwd = 1)

# # Adding retrospective quantile estimation (blue)
# result <- apply(xbs_retro[1,,], 1, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
# lines(1:length(idx), result[1,idx], col = 'red', lty = 2, lwd = 0.5)
# lines(1:length(idx), result[2,idx], col = 'darkred', lwd = 0.5)
# lines(1:length(idx), result[3,idx], col = 'red', lty = 2, lwd = 0.5)

# # Adding retrospective quantile estimation (blue)
# result <- apply(xbs_retro[2,,], 1, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
# lines(1:length(idx), result[1,idx], col = 'purple', lty = 2, lwd = 0.5)
# lines(1:length(idx), result[2,idx], col = 'purple', lwd = 0.5)
# lines(1:length(idx), result[3,idx], col = 'purple', lty = 2, lwd = 0.5)

# # Adding retrospective quantile estimation (blue)
# result <- apply(xbs_retro[3,,], 1, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
# lines(1:length(idx), result[1,idx], col = 'purple', lty = 2, lwd = 0.5)
# lines(1:length(idx), result[2,idx], col = 'purple', lwd = 0.5)
# lines(1:length(idx), result[3,idx], col = 'purple', lty = 2, lwd = 0.5)

# # Adding retrospective quantile estimation (blue)
# result <- apply(xbs_retro[4,,], 1, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
# lines(1:length(idx), result[1,idx], col = 'green', lty = 2, lwd = 0.5)
# lines(1:length(idx), result[2,idx], col = 'darkgreen', lwd = 0.5)
# lines(1:length(idx), result[3,idx], col = 'green', lty = 2, lwd = 0.5)

# # Adding retrospective quantile estimation (blue)
# result <- apply(xbs_retro[5,,], 1, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
# lines(1:length(idx), result[1,idx], col = 'purple', lty = 2, lwd = 0.5)
# lines(1:length(idx), result[2,idx], col = 'purple', lwd = 0.5)
# lines(1:length(idx), result[3,idx], col = 'purple', lty = 2, lwd = 0.5)


# # Adding retrospective quantile estimation (blue)
# result <- apply(xbs_retro[6,,], 1, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
# lines(1:length(idx), result[1,idx], col = 'purple', lty = 2, lwd = 0.5)
# lines(1:length(idx), result[2,idx], col = 'purple', lwd = 0.5)
# lines(1:length(idx), result[3,idx], col = 'purple', lty = 2, lwd = 0.5)


# # Adding retrospective quantile estimation (blue)
# result <- apply(xbs_retro[7,,], 1, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
# lines(1:length(idx), result[1,idx], col = 'blue', lty = 2, lwd = 0.5)
# lines(1:length(idx), result[2,idx], col = 'darkblue', lwd = 0.5)
# lines(1:length(idx), result[3,idx], col = 'blue', lty = 2, lwd = 0.5)


idx <- (TT-iii):(TT)


sd_ndlm <- mean(sqrt(samp.sigma_50_NDLM_synth_DISC[1,]))

d1 <- new.theta.out_50_NDLM_synth_DISC$sm_ens[[1]][8,]
d2 <- new.theta.out_50_NDLM_synth_DISC$sm_ens[[2]][8,]
discrep <- c(d1, d2) 
estim_dqlm <- new.theta.out_50_NDLM_synth_DISC$exps[2,(TT+1):(TT+ranges[1])] - discrep
lines(idx_f, estim_dqlm + sd_ndlm * qnorm(0.5), col = "orange", lwd = 2)
lines(new.theta.out_50_NDLM_synth_DISC$exps[1,idx1] + sd_ndlm * qnorm(0.5), col = 'orange', lwd = 2)

percs <- c(0.05, 0.2, 0.35, 0.5, 0.65, 0.65, 0.8, 0.95)
for (i in 1:length(percs)) {
    pp<- percs[i]
    result <- fast_row_quantiles_t(xbs_ndlm_retro[1, , ], probs = c(0.025, 0.5, 0.975))
    lines(1:length(idx), result[1,idx] + sd_ndlm * qnorm(pp), col = 'orange', lty = 2, lwd = 0.5)
    lines(1:length(idx), result[2,idx] + sd_ndlm * qnorm(pp), col = 'darkorange', lwd = 0.5)
    lines(1:length(idx), result[3,idx] + sd_ndlm * qnorm(pp), col = 'orange', lty = 2, lwd = 0.5)
    result <- fast_row_quantiles_t(xbs_ndlm[1, , ] + sd_ndlm * qnorm(pp), probs = c(0.025, 0.5, 0.975))
    lines(idx_f, result[1,], col = 'orange', lty = 2, lwd = 1)
    lines(idx_f, result[2,], col = 'orange', lwd = 1.5)
    lines(idx_f, result[3,], col = 'orange', lty = 2, lwd = 1)
}

lev_flood <- c(21.76, 19.5, 16.5, 14) 
flood_labels <- c("Major Flooding", "Moderate Flooding", "Minor Flooding", "Action")
log_flood_levels <- log(lev_flood + 1)
for (i in seq_along(log_flood_levels)) {
  abline(h = log_flood_levels[i], lwd = 1, lty = 2, col = "darkgray")
  text(x = par("usr")[2] + 0.05 * diff(par("usr")[1:2]), y = log_flood_levels[i], 
       labels = flood_labels[i], col = "gray", pos = 4, cex = 0.8, font = 2)
}

start_date <- dates_ts_usgs[(TT - iii)]  # Starting date
days_ahead <- ranges[1] + iii            # Number of days ahead
date_sequence <- seq.Date(from = start_date, by = "day", length.out = days_ahead + 1)
selected_dates <- date_sequence
num_ticks <- 13
tick_positions <- pretty(1:length(idx2), num_ticks) 
if (length(tick_positions) > num_ticks) {
    tick_positions <- tick_positions[seq(1, length(tick_positions), length.out = num_ticks)]
}
tick_labels <- format(selected_dates[match(tick_positions, 1:length(idx2))], "%Y-%m-%d")
axis(1, at = tick_positions, labels = FALSE) 
text(x = tick_positions, y = par("usr")[3] - 0.025 * diff(par("usr")[3:4]), labels = tick_labels, 
     srt = 45, adj = 1, xpd = TRUE, cex = 0.8, col = "black")

# Adding a vertical line for the forecast start date
forecast_date <- as.Date("2022-12-25")
forecast_position <- which(selected_dates == forecast_date)
abline(v = forecast_position, col = "black", lty = 1, lwd = 0.8)

# Adding the label for the forecast start date
text(x = forecast_position, y = par("usr")[4] + 0.03 * diff(par("usr")[3:4]), 
     labels = "forecast start date", col = "red", pos = 3, cex = 1.2, font = 2)

abline(h = 0)

dev.off()

# Setting up the indices
iii <- 30
idx1 <- (TT-iii):(TT+ranges[2])
idx2 <- (TT-iii):(TT+ranges[1])
idx_all <- (TT-iii):(TT+ranges[1])
idx_T <- (TT-iii):TT
idx_y <- (TT-iii):TT
idx_f <- ((iii+1)+1):((iii+1)+ranges[1])

# Initialize the matrix
# q_exps <- matrix(NA_real_, nrow = 7, ncol=(ranges[1]))

png("/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics_reproduce/All3_ndlm_DISC.png", width = 6000, height = 4000, res = 600)
# Base plot
plot.ts((new.theta.out_95_exAL_synth_DISC$exps[2,idx_all]) * 0, ylim = c(-2.5, 2.5),
        xlab = " ", ylab = "log-flow", xaxt = "n", col = NA, lwd = 2, main = "Dynamic Quantile: NDLM")

# Adding 'Truth' points
points((1 + length(idx_y)):(length(truth) + length(idx_y)), truth, col = 'deeppink4', pch = 19, cex = 0.7, lwd = 1)

# Adding 'Observations'
lines(Y[1,idx_y], col = 'black', lwd = 1.5)
points(Y[1,idx_y], col = 'black', pch = 16, cex = 0.6)

# # Adding 95th Quantile estimation
# d1 <- new.theta.out_95_exAL_synth$sm_ens[[1]][8,]
# d2 <- new.theta.out_95_exAL_synth$sm_ens[[2]][8,]
# discrep <- c(d1, d2) 

# estim_dqlm <- new.theta.out_5_exAL_synth$exps[2,(TT+1):(TT+ranges[1])] - discrep
# q_exps[1,] <- estim_dqlm 
# lines(new.theta.out_5_exAL_synth$exps[1,idx1], col = 'darkred', lwd = 2)

# estim_dqlm <- new.theta.out_20_exAL_synth$exps[2,(TT+1):(TT+ranges[1])] - discrep
# q_exps[2,] <- estim_dqlm 
# lines(new.theta.out_20_exAL_synth$exps[1,idx1], col = 'purple', lwd = 2)

# estim_dqlm <- new.theta.out_35_exAL_synth$exps[2,(TT+1):(TT+ranges[1])] - discrep
# q_exps[3,] <- estim_dqlm 
# lines(new.theta.out_35_exAL_synth$exps[1,idx1], col = 'purple', lwd = 2)

# estim_dqlm <- new.theta.out_50_exAL_synth$exps[2,(TT+1):(TT+ranges[1])] - discrep
# q_exps[4,] <- estim_dqlm 
# lines(new.theta.out_50_exAL_synth$exps[1,idx1], col = 'darkgreen', lwd = 2)

# estim_dqlm <- new.theta.out_65_exAL_synth$exps[2,(TT+1):(TT+ranges[1])] - discrep
# q_exps[5,] <- estim_dqlm 
# lines(new.theta.out_65_exAL_synth$exps[1,idx1], col = 'purple', lwd = 2)

# estim_dqlm <- new.theta.out_80_exAL_synth$exps[2,(TT+1):(TT+ranges[1])] - discrep
# q_exps[6,] <- estim_dqlm 
# lines(new.theta.out_80_exAL_synth$exps[1,idx1], col = 'purple', lwd = 2)

# estim_dqlm <- new.theta.out_95_exAL_synth$exps[2,(TT+1):(TT+ranges[1])] - discrep
# q_exps[7,] <- estim_dqlm 
# lines(new.theta.out_95_exAL_synth$exps[1,idx1], col = 'darkblue', lwd = 2)

# # Adding quantile bands (blue) for 95th Quantile estimation
# result <- apply(xbs[7,,], 1, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
# lines(idx_f, result[1,], col = 'blue', lty = 2, lwd = 1)
# lines(idx_f, result[2,], col = 'darkblue', lwd = 1.5)
# lines(idx_f, result[3,], col = 'blue', lty = 2, lwd = 1)

# # Adding quantile bands (blue) for 95th Quantile estimation
# result <- apply(xbs[6,,], 1, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
# lines(idx_f, result[1,], col = 'purple', lty = 2, lwd = 1)
# lines(idx_f, result[2,], col = 'purple', lwd = 1.5)
# lines(idx_f, result[3,], col = 'purple', lty = 2, lwd = 1)
# # Adding quantile bands (blue) for 95th Quantile estimation
# result <- apply(xbs[5,,], 1, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
# lines(idx_f, result[1,], col = 'purple', lty = 2, lwd = 1)
# lines(idx_f, result[2,], col = 'purple', lwd = 1.5)
# lines(idx_f, result[3,], col = 'purple', lty = 2, lwd = 1)
# # Adding quantile bands (blue) for 95th Quantile estimation
# result <- apply(xbs[4,,], 1, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
# lines(idx_f, result[1,], col = 'green', lty = 2, lwd = 1)
# lines(idx_f, result[2,], col = 'darkgreen', lwd = 1.5)
# lines(idx_f, result[3,], col = 'blue', lty = 2, lwd = 1)
# # Adding quantile bands (blue) for 95th Quantile estimation
# result <- apply(xbs[3,,], 1, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
# lines(idx_f, result[1,], col = 'purple', lty = 2, lwd = 1)
# lines(idx_f, result[2,], col = 'purple', lwd = 1.5)
# lines(idx_f, result[3,], col = 'purple', lty = 2, lwd = 1)
# # Adding quantile bands (blue) for 95th Quantile estimation
# result <- apply(xbs[2,,], 1, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
# lines(idx_f, result[1,], col = 'purple', lty = 2, lwd = 1)
# lines(idx_f, result[2,], col = 'purple', lwd = 1.5)
# lines(idx_f, result[3,], col = 'purple', lty = 2, lwd = 1)
# # Adding quantile bands (blue) for 95th Quantile estimation
# result <- apply(xbs[1,,], 1, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
# lines(idx_f, result[1,], col = 'red', lty = 2, lwd = 1)
# lines(idx_f, result[2,], col = 'darkred', lwd = 1.5)
# lines(idx_f, result[3,], col = 'red', lty = 2, lwd = 1)

# # Adding retrospective quantile estimation (blue)
# result <- apply(xbs_retro[1,,], 1, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
# lines(1:length(idx), result[1,idx], col = 'red', lty = 2, lwd = 0.5)
# lines(1:length(idx), result[2,idx], col = 'darkred', lwd = 0.5)
# lines(1:length(idx), result[3,idx], col = 'red', lty = 2, lwd = 0.5)

# # Adding retrospective quantile estimation (blue)
# result <- apply(xbs_retro[2,,], 1, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
# lines(1:length(idx), result[1,idx], col = 'purple', lty = 2, lwd = 0.5)
# lines(1:length(idx), result[2,idx], col = 'purple', lwd = 0.5)
# lines(1:length(idx), result[3,idx], col = 'purple', lty = 2, lwd = 0.5)

# # Adding retrospective quantile estimation (blue)
# result <- apply(xbs_retro[3,,], 1, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
# lines(1:length(idx), result[1,idx], col = 'purple', lty = 2, lwd = 0.5)
# lines(1:length(idx), result[2,idx], col = 'purple', lwd = 0.5)
# lines(1:length(idx), result[3,idx], col = 'purple', lty = 2, lwd = 0.5)

# # Adding retrospective quantile estimation (blue)
# result <- apply(xbs_retro[4,,], 1, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
# lines(1:length(idx), result[1,idx], col = 'green', lty = 2, lwd = 0.5)
# lines(1:length(idx), result[2,idx], col = 'darkgreen', lwd = 0.5)
# lines(1:length(idx), result[3,idx], col = 'green', lty = 2, lwd = 0.5)

# # Adding retrospective quantile estimation (blue)
# result <- apply(xbs_retro[5,,], 1, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
# lines(1:length(idx), result[1,idx], col = 'purple', lty = 2, lwd = 0.5)
# lines(1:length(idx), result[2,idx], col = 'purple', lwd = 0.5)
# lines(1:length(idx), result[3,idx], col = 'purple', lty = 2, lwd = 0.5)


# # Adding retrospective quantile estimation (blue)
# result <- apply(xbs_retro[6,,], 1, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
# lines(1:length(idx), result[1,idx], col = 'purple', lty = 2, lwd = 0.5)
# lines(1:length(idx), result[2,idx], col = 'purple', lwd = 0.5)
# lines(1:length(idx), result[3,idx], col = 'purple', lty = 2, lwd = 0.5)


# # Adding retrospective quantile estimation (blue)
# result <- apply(xbs_retro[7,,], 1, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
# lines(1:length(idx), result[1,idx], col = 'blue', lty = 2, lwd = 0.5)
# lines(1:length(idx), result[2,idx], col = 'darkblue', lwd = 0.5)
# lines(1:length(idx), result[3,idx], col = 'blue', lty = 2, lwd = 0.5)


idx <- (TT-iii):(TT)


sd_ndlm <- mean(sqrt(samp.sigma_50_NDLM_synth_DISC[1,]))

# d1 <- new.theta.out_50_NDLM_synth_DISC$sm_ens[[1]][8,]
# d2 <- new.theta.out_50_NDLM_synth_DISC$sm_ens[[2]][8,]
# discrep <- c(d1, d2) 


F_constant_disc <- FF[1:7,1,1]
d1 <- F_constant_disc%*%new.theta.out_50_NDLM_synth_DISC$sm_ens[[1]][8:14,]
d2 <- F_constant_disc%*%new.theta.out_50_NDLM_synth_DISC$sm_ens[[2]][8:14,]
discrep <- c(d1, d2) 

estim_dqlm <- new.theta.out_50_NDLM_synth_DISC$exps[2,(TT+1):(TT+ranges[1])] - discrep
lines(idx_f, estim_dqlm + sd_ndlm * qnorm(0.5), col = "orange", lwd = 2)
lines(new.theta.out_50_NDLM_synth_DISC$exps[1,idx1] + sd_ndlm * qnorm(0.5), col = 'orange', lwd = 2)

percs <- c(0.05, 0.5, 0.95)
for (i in 1:length(percs)) {
    pp <- percs[i]
    result <- fast_row_quantiles_t(xbs_ndlm_retro[1, , ], probs = c(0.025, 0.5, 0.975))
    lines(1:length(idx), result[1,idx] + sd_ndlm * qnorm(pp), col = 'orange', lty = 2, lwd = 0.5)
    lines(1:length(idx), result[2,idx] + sd_ndlm * qnorm(pp), col = 'darkorange', lwd = 0.5)
    lines(1:length(idx), result[3,idx] + sd_ndlm * qnorm(pp), col = 'orange', lty = 2, lwd = 0.5)
    result <- fast_row_quantiles_t(xbs_ndlm[1, , ] + sd_ndlm * qnorm(pp), probs = c(0.025, 0.5, 0.975))
    lines(idx_f, result[1,], col = 'orange', lty = 2, lwd = 1)
    lines(idx_f, result[2,], col = 'orange', lwd = 1.5)
    lines(idx_f, result[3,], col = 'orange', lty = 2, lwd = 1)
}

lev_flood <- c(21.76, 19.5, 16.5, 14) 
flood_labels <- c("Major Flooding", "Moderate Flooding", "Minor Flooding", "Action")
log_flood_levels <- log(lev_flood + 1)
for (i in seq_along(log_flood_levels)) {
  abline(h = log_flood_levels[i], lwd = 1, lty = 2, col = "darkgray")
  text(x = par("usr")[2] + 0.05 * diff(par("usr")[1:2]), y = log_flood_levels[i], 
       labels = flood_labels[i], col = "gray", pos = 4, cex = 0.8, font = 2)
}

start_date <- dates_ts_usgs[(TT - iii)]  # Starting date
days_ahead <- ranges[1] + iii            # Number of days ahead
date_sequence <- seq.Date(from = start_date, by = "day", length.out = days_ahead + 1)
selected_dates <- date_sequence
num_ticks <- 13
tick_positions <- pretty(1:length(idx2), num_ticks) 
if (length(tick_positions) > num_ticks) {
    tick_positions <- tick_positions[seq(1, length(tick_positions), length.out = num_ticks)]
}
tick_labels <- format(selected_dates[match(tick_positions, 1:length(idx2))], "%Y-%m-%d")
axis(1, at = tick_positions, labels = FALSE) 
text(x = tick_positions, y = par("usr")[3] - 0.025 * diff(par("usr")[3:4]), labels = tick_labels, 
     srt = 45, adj = 1, xpd = TRUE, cex = 0.8, col = "black")

# Adding a vertical line for the forecast start date
forecast_date <- as.Date("2022-12-25")
forecast_position <- which(selected_dates == forecast_date)
abline(v = forecast_position, col = "black", lty = 1, lwd = 0.8)

# Adding the label for the forecast start date
text(x = forecast_position, y = par("usr")[4] + 0.03 * diff(par("usr")[3:4]), 
     labels = "forecast start date", col = "red", pos = 3, cex = 1.2, font = 2)

abline(h = 0)

dev.off()

# Setting up the indices
iii <- 30
idx1 <- (TT-iii):(TT+ranges[2])
idx2 <- (TT-iii):(TT+ranges[1])
idx_all <- (TT-iii):(TT+ranges[1])
idx_T <- (TT-iii):TT
idx_y <- (TT-iii):TT
idx_f <- ((iii+1)+1):((iii+1)+ranges[1])

# Initialize the matrix
# q_exps <- matrix(NA_real_, nrow = 7, ncol=(ranges[1]))

png("/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics_reproduce/95th_exal_ndlm_DISC.png", width = 6000, height = 4000, res = 600)
# Base plot
plot.ts((new.theta.out_95_exAL_synth_DISC$exps[2,idx_all]) * 0, ylim = c(-2.5, 2.5),
        xlab = " ", ylab = "log-flow", xaxt = "n", col = NA, lwd = 2, main = "Dynamic 95th Quantile: exAL vs NDLM")

# Adding 'Truth' points
points((1 + length(idx_y)):(length(truth) + length(idx_y)), truth, col = 'deeppink4', pch = 19, cex = 0.7, lwd = 1)

# Adding 'Observations'
lines(Y[1,idx_y], col = 'black', lwd = 1.5)
points(Y[1,idx_y], col = 'black', pch = 16, cex = 0.6)

# Adding 95th Quantile estimation
# d1 <- new.theta.out_95_exAL_synth_DISC$sm_ens[[1]][8,]
# d2 <- new.theta.out_95_exAL_synth_DISC$sm_ens[[2]][8,]
# discrep <- c(d1, d2) 

F_constant_disc <- FF[1:7,1,1]
d1 <- F_constant_disc%*%new.theta.out_95_exAL_synth_DISC$sm_ens[[1]][8:14,]
d2 <- F_constant_disc%*%new.theta.out_95_exAL_synth_DISC$sm_ens[[2]][8:14,]
discrep <- c(d1, d2) 
estim_dqlm <- new.theta.out_95_exAL_synth_DISC$exps[2,(TT+1):(TT+ranges[1])] - discrep
q_exps[7,] <- estim_dqlm 
lines(new.theta.out_95_exAL_synth_DISC$exps[1,idx1], col = 'darkblue', lwd = 2)

# Adding quantile bands (blue) for 95th Quantile estimation
result <- fast_row_quantiles_t(xbs[7, , ], probs = c(0.025, 0.5, 0.975))
lines(idx_f, result[1,], col = 'blue', lty = 2, lwd = 1)
lines(idx_f, result[2,], col = 'darkblue', lwd = 1.5)
lines(idx_f, result[3,], col = 'blue', lty = 2, lwd = 1)

# Adding quantile bands (orange) for NDLM estimation
sd_ndlm <- mean(sqrt(samp.sigma_50_NDLM_synth_DISC[1,]))
result <- fast_row_quantiles_t(xbs_ndlm[1, , ] + sd_ndlm * qnorm(0.95), probs = c(0.025, 0.5, 0.975))
lines(idx_f, result[1,], col = 'orange', lty = 2, lwd = 1)
lines(idx_f, result[2,], col = 'darkorange', lwd = 1.5)
lines(idx_f, result[3,], col = 'orange', lty = 2, lwd = 1)

# # Adding NDLM estimation
# d1 <- new.theta.out_50_NDLM_synth_DISC$sm_ens[[1]][8,]
# d2 <- new.theta.out_50_NDLM_synth_DISC$sm_ens[[2]][8,]
# discrep <- c(d1, d2) 
F_constant_disc <- FF[1:7,1,1]
d1 <- F_constant_disc%*%new.theta.out_50_NDLM_synth_DISC$sm_ens[[1]][8:14,]
d2 <- F_constant_disc%*%new.theta.out_50_NDLM_synth_DISC$sm_ens[[2]][8:14,]
discrep <- c(d1, d2) 
estim_dqlm <- new.theta.out_50_NDLM_synth_DISC$exps[2,(TT+1):(TT+ranges[1])] - discrep
lines(idx_f, estim_dqlm + sd_ndlm * qnorm(0.95), col = "orange", lwd = 2)
lines(new.theta.out_50_NDLM_synth_DISC$exps[1,idx1] + sd_ndlm * qnorm(0.95), col = 'orange', lwd = 2)


idx <- (TT-iii):(TT)

# Adding retrospective quantile estimation (blue)
result <- fast_row_quantiles_t(xbs_retro[7, , ], probs = c(0.025, 0.5, 0.975))
lines(1:length(idx), result[1,idx], col = 'blue', lty = 2, lwd = 0.5)
lines(1:length(idx), result[2,idx], col = 'darkblue', lwd = 0.5)
lines(1:length(idx), result[3,idx], col = 'blue', lty = 2, lwd = 0.5)

# Adding retrospective NDLM estimation (orange)
result <- fast_row_quantiles_t(xbs_ndlm_retro[1, , ], probs = c(0.025, 0.5, 0.975))
lines(1:length(idx), result[1,idx] + sd_ndlm * qnorm(0.95), col = 'orange', lty = 2, lwd = 0.5)
lines(1:length(idx), result[2,idx] + sd_ndlm * qnorm(0.95), col = 'darkorange', lwd = 0.5)
lines(1:length(idx), result[3,idx] + sd_ndlm * qnorm(0.95), col = 'orange', lty = 2, lwd = 0.5)

# Adding flood levels (horizontal dashed lines) with labels
lev_flood <- c(21.76, 19.5, 16.5, 14) 
flood_labels <- c("Major Flooding", "Moderate Flooding", "Minor Flooding", "Action")
log_flood_levels <- log(lev_flood + 1)
for (i in seq_along(log_flood_levels)) {
  abline(h = log_flood_levels[i], lwd = 1, lty = 2, col = "darkgray")
  text(x = par("usr")[2] + 0.05 * diff(par("usr")[1:2]), y = log_flood_levels[i], 
       labels = flood_labels[i], col = "gray", pos = 4, cex = 0.8, font = 2)
}

# Adding date labels on the x-axis
start_date <- dates_ts_usgs[(TT - iii)]  # Starting date
days_ahead <- ranges[1] + iii            # Number of days ahead
date_sequence <- seq.Date(from = start_date, by = "day", length.out = days_ahead + 1)
selected_dates <- date_sequence
num_ticks <- 13
tick_positions <- pretty(1:length(idx2), num_ticks) 
if (length(tick_positions) > num_ticks) {
    tick_positions <- tick_positions[seq(1, length(tick_positions), length.out = num_ticks)]
}
tick_labels <- format(selected_dates[match(tick_positions, 1:length(idx2))], "%Y-%m-%d")
axis(1, at = tick_positions, labels = FALSE) 
text(x = tick_positions, y = par("usr")[3] - 0.025 * diff(par("usr")[3:4]), labels = tick_labels, 
     srt = 45, adj = 1, xpd = TRUE, cex = 0.8, col = "black")

# Adding a vertical line for the forecast start date
forecast_date <- as.Date("2022-12-25")
forecast_position <- which(selected_dates == forecast_date)
abline(v = forecast_position, col = "black", lty = 1, lwd = 0.8)

# Adding the label for the forecast start date
text(x = forecast_position, y = par("usr")[4] + 0.03 * diff(par("usr")[3:4]), 
     labels = "forecast start date", col = "red", pos = 3, cex = 1.2, font = 2)

abline(h = 0)


dev.off()

# Setting up the indices
iii <- 30
idx1 <- (TT-iii):(TT+ranges[2])
idx2 <- (TT-iii):(TT+ranges[1])
idx_all <- (TT-iii):(TT+ranges[1])
idx_T <- (TT-iii):TT
idx_y <- (TT-iii):TT
idx_f <- ((iii+1)+1):((iii+1)+ranges[1])

# Initialize the matrix
# q_exps <- matrix(NA_real_, nrow = 7, ncol=(ranges[1]))
#
png("/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics_reproduce/50th_exal_ndlm_DISC.png", width = 6000, height = 4000, res = 600)
# Base plot
plot.ts((new.theta.out_50_exAL_synth_DISC$exps[2,idx_all]) * 0, ylim = c(-2.5, 2.5),
        xlab = " ", ylab = "log-flow", xaxt = "n", col = NA, lwd = 2, main = "Dynamic 50th Quantile: exAL vs NDLM")

# Adding 'Truth' points
points((1 + length(idx_y)):(length(truth) + length(idx_y)), truth, col = 'deeppink4', pch = 19, cex = 0.7, lwd = 1)

# Adding 'Observations'
lines(Y[1,idx_y], col = 'black', lwd = 1.5)
points(Y[1,idx_y], col = 'black', pch = 16, cex = 0.6)

# Adding 95th Quantile estimation
# d1 <- new.theta.out_50_exAL_synth_DISC$sm_ens[[1]][8,]
# d2 <- new.theta.out_50_exAL_synth_DISC$sm_ens[[2]][8,]
# discrep <- c(d1, d2) 
F_constant_disc <- FF[1:7,1,1]
d1 <- F_constant_disc%*%new.theta.out_50_exAL_synth_DISC$sm_ens[[1]][8:14,]
d2 <- F_constant_disc%*%new.theta.out_50_exAL_synth_DISC$sm_ens[[2]][8:14,]
discrep <- c(d1, d2) 
estim_dqlm <- new.theta.out_50_exAL_synth_DISC$exps[2,(TT+1):(TT+ranges[1])] - discrep
q_exps[7,] <- estim_dqlm 
lines(new.theta.out_50_exAL_synth_DISC$exps[1,idx1], col = 'darkgreen', lwd = 2)

# Adding quantile bands (blue) for 95th Quantile estimation
result <- fast_row_quantiles_t(xbs[4, , ], probs = c(0.025, 0.5, 0.975))
lines(idx_f, result[1,], col = 'green', lty = 2, lwd = 1)
lines(idx_f, result[2,], col = 'darkgreen', lwd = 1.5)
lines(idx_f, result[3,], col = 'green', lty = 2, lwd = 1)

# Adding quantile bands (orange) for NDLM estimation
sd_ndlm <- mean(sqrt(samp.sigma_50_NDLM_synth_DISC[1,]))
result <- fast_row_quantiles_t(xbs_ndlm[1, , ] + sd_ndlm * qnorm(0.5), probs = c(0.025, 0.5, 0.975))
lines(idx_f, result[1,], col = 'orange', lty = 2, lwd = 1)
lines(idx_f, result[2,], col = 'orange', lwd = 1.5)
lines(idx_f, result[3,], col = 'orange', lty = 2, lwd = 1)

# Adding NDLM estimation
# d1 <- new.theta.out_50_NDLM_synth_DISC$sm_ens[[1]][8,]
# d2 <- new.theta.out_50_NDLM_synth_DISC$sm_ens[[2]][8,]
# discrep <- c(d1, d2) 
F_constant_disc <- FF[1:7,1,1]
d1 <- F_constant_disc%*%new.theta.out_50_NDLM_synth_DISC$sm_ens[[1]][8:14,]
d2 <- F_constant_disc%*%new.theta.out_50_NDLM_synth_DISC$sm_ens[[2]][8:14,]
discrep <- c(d1, d2) 
estim_dqlm <- new.theta.out_50_NDLM_synth_DISC$exps[2,(TT+1):(TT+ranges[1])] - discrep
lines(idx_f, estim_dqlm + sd_ndlm * qnorm(0.5), col = "orange", lwd = 2)
lines(new.theta.out_50_NDLM_synth_DISC$exps[1,idx1] + sd_ndlm * qnorm(0.5), col = 'orange', lwd = 2)


idx <- (TT-iii):(TT)

# Adding retrospective quantile estimation (blue)
result <- fast_row_quantiles_t(xbs_retro[4, , ], probs = c(0.025, 0.5, 0.975))
lines(1:length(idx), result[1,idx], col = 'green', lty = 2, lwd = 0.5)
lines(1:length(idx), result[2,idx], col = 'darkgreen', lwd = 0.5)
lines(1:length(idx), result[3,idx], col = 'green', lty = 2, lwd = 0.5)

# Adding retrospective NDLM estimation (orange)
result <- fast_row_quantiles_t(xbs_ndlm_retro[1, , ], probs = c(0.025, 0.5, 0.975))
lines(1:length(idx), result[1,idx] + sd_ndlm * qnorm(0.5), col = 'orange', lty = 2, lwd = 0.5)
lines(1:length(idx), result[2,idx] + sd_ndlm * qnorm(0.5), col = 'darkorange', lwd = 0.5)
lines(1:length(idx), result[3,idx] + sd_ndlm * qnorm(0.5), col = 'orange', lty = 2, lwd = 0.5)

# Adding flood levels (horizontal dashed lines) with labels
lev_flood <- c(21.76, 19.5, 16.5, 14) 
flood_labels <- c("Major Flooding", "Moderate Flooding", "Minor Flooding", "Action")
log_flood_levels <- log(lev_flood + 1)
for (i in seq_along(log_flood_levels)) {
  abline(h = log_flood_levels[i], lwd = 1, lty = 2, col = "darkgray")
  text(x = par("usr")[2] + 0.05 * diff(par("usr")[1:2]), y = log_flood_levels[i], 
       labels = flood_labels[i], col = "gray", pos = 4, cex = 0.8, font = 2)
}

# Adding date labels on the x-axis
start_date <- dates_ts_usgs[(TT - iii)]  # Starting date
days_ahead <- ranges[1] + iii            # Number of days ahead
date_sequence <- seq.Date(from = start_date, by = "day", length.out = days_ahead + 1)
selected_dates <- date_sequence
num_ticks <- 13
tick_positions <- pretty(1:length(idx2), num_ticks) 
if (length(tick_positions) > num_ticks) {
    tick_positions <- tick_positions[seq(1, length(tick_positions), length.out = num_ticks)]
}
tick_labels <- format(selected_dates[match(tick_positions, 1:length(idx2))], "%Y-%m-%d")
axis(1, at = tick_positions, labels = FALSE) 
text(x = tick_positions, y = par("usr")[3] - 0.025 * diff(par("usr")[3:4]), labels = tick_labels, 
     srt = 45, adj = 1, xpd = TRUE, cex = 0.8, col = "black")

# Adding a vertical line for the forecast start date
forecast_date <- as.Date("2022-12-25")
forecast_position <- which(selected_dates == forecast_date)
abline(v = forecast_position, col = "black", lty = 1, lwd = 0.8)

# Adding the label for the forecast start date
text(x = forecast_position, y = par("usr")[4] + 0.03 * diff(par("usr")[3:4]), 
     labels = "forecast start date", col = "red", pos = 3, cex = 1.2, font = 2)

abline(h = 0)
dev.off()

# Setting up the indices
iii <- 30
idx1 <- (TT-iii):(TT+ranges[2])
idx2 <- (TT-iii):(TT+ranges[1])
idx_all <- (TT-iii):(TT+ranges[1])
idx_T <- (TT-iii):TT
idx_y <- (TT-iii):TT
idx_f <- ((iii+1)+1):((iii+1)+ranges[1])

# Initialize the matrix
# q_exps <- matrix(NsA_real_, nrow = 7, ncol=(ranges[1]))

# Base plot
png("/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics_reproduce/5th_exal_ndlm_DISC.png", width = 6000, height = 4000, res = 600)
plot.ts((new.theta.out_5_exAL_synth_DISC$exps[2,idx_all]) * 0, ylim = c(-2.5, 2.5),
        xlab = " ", ylab = "log-flow", xaxt = "n", col = NA, lwd = 2, main = "Dynamic 5th Quantile: exAL vs NDLM")

# Adding 'Truth' points
points((1 + length(idx_y)):(length(truth) + length(idx_y)), truth, col = 'deeppink4', pch = 19, cex = 0.7, lwd = 1)

# Adding 'Observations'
lines(Y[1,idx_y], col = 'black', lwd = 1.5)
points(Y[1,idx_y], col = 'black', pch = 16, cex = 0.6)

# Adding 95th Quantile estimation
# d1 <- new.theta.out_5_exAL_synth_DISC$sm_ens[[1]][8,]
# d2 <- new.theta.out_5_exAL_synth_DISC$sm_ens[[2]][8,]
# discrep <- c(d1, d2) 
F_constant_disc <- FF[1:7,1,1]
d1 <- F_constant_disc%*%new.theta.out_5_exAL_synth_DISC$sm_ens[[1]][8:14,]
d2 <- F_constant_disc%*%new.theta.out_5_exAL_synth_DISC$sm_ens[[2]][8:14,]
discrep <- c(d1, d2) 
estim_dqlm <- new.theta.out_5_exAL_synth_DISC$exps[2,(TT+1):(TT+ranges[1])] - discrep
q_exps[7,] <- estim_dqlm 
lines(new.theta.out_5_exAL_synth_DISC$exps[1,idx1], col = 'darkred', lwd = 2)

# Adding quantile bands (blue) for 95th Quantile estimation
result <- fast_row_quantiles_t(xbs[1, , ], probs = c(0.025, 0.5, 0.975))
lines(idx_f, result[1,], col = 'red', lty = 2, lwd = 1)
lines(idx_f, result[2,], col = 'darkred', lwd = 1.5)
lines(idx_f, result[3,], col = 'red', lty = 2, lwd = 1)

# Adding quantile bands (orange) for NDLM estimation
sd_ndlm <- mean(sqrt(samp.sigma_50_NDLM_synth_DISC[1,]))
result <- fast_row_quantiles_t(xbs_ndlm[1, , ] + sd_ndlm * qnorm(0.05), probs = c(0.025, 0.5, 0.975))
lines(idx_f, result[1,], col = 'orange', lty = 2, lwd = 1)
lines(idx_f, result[2,], col = 'orange', lwd = 1.5)
lines(idx_f, result[3,], col = 'orange', lty = 2, lwd = 1)

# Adding NDLM estimation
d1 <- new.theta.out_50_NDLM_synth_DISC$sm_ens[[1]][8,]
d2 <- new.theta.out_50_NDLM_synth_DISC$sm_ens[[2]][8,]
discrep <- c(d1, d2) 
estim_dqlm <- new.theta.out_50_NDLM_synth_DISC$exps[2,(TT+1):(TT+ranges[1])] - discrep
q_exps[4,] <- estim_dqlm 
lines(idx_f, estim_dqlm + sd_ndlm * qnorm(0.05), col = "orange", lwd = 2)
lines(new.theta.out_50_NDLM_synth_DISC$exps[1,idx1] + sd_ndlm * qnorm(0.05), col = 'orange', lwd = 2)


idx <- (TT-iii):(TT)

# Adding retrospective quantile estimation (blue)
result <- fast_row_quantiles_t(xbs_retro[1, , ], probs = c(0.025, 0.5, 0.975))
lines(1:length(idx), result[1,idx], col = 'red', lty = 2, lwd = 0.5)
lines(1:length(idx), result[2,idx], col = 'darkred', lwd = 0.5)
lines(1:length(idx), result[3,idx], col = 'red', lty = 2, lwd = 0.5)

# Adding retrospective NDLM estimation (orange)
result <- fast_row_quantiles_t(xbs_ndlm_retro[1, , ], probs = c(0.025, 0.5, 0.975))
lines(1:length(idx), result[1,idx] + sd_ndlm * qnorm(0.05), col = 'orange', lty = 2, lwd = 0.5)
lines(1:length(idx), result[2,idx] + sd_ndlm * qnorm(0.05), col = 'darkorange', lwd = 0.5)
lines(1:length(idx), result[3,idx] + sd_ndlm * qnorm(0.05), col = 'orange', lty = 2, lwd = 0.5)

# Adding flood levels (horizontal dashed lines) with labels
lev_flood <- c(21.76, 19.5, 16.5, 14) 
flood_labels <- c("Major Flooding", "Moderate Flooding", "Minor Flooding", "Action")
log_flood_levels <- log(lev_flood + 1)
for (i in seq_along(log_flood_levels)) {
  abline(h = log_flood_levels[i], lwd = 1, lty = 2, col = "darkgray")
  text(x = par("usr")[2] + 0.05 * diff(par("usr")[1:2]), y = log_flood_levels[i], 
       labels = flood_labels[i], col = "gray", pos = 4, cex = 0.8, font = 2)
}

# Adding date labels on the x-axis
start_date <- dates_ts_usgs[(TT - iii)]  # Starting date
days_ahead <- ranges[1] + iii            # Number of days ahead
date_sequence <- seq.Date(from = start_date, by = "day", length.out = days_ahead + 1)
selected_dates <- date_sequence
num_ticks <- 13
tick_positions <- pretty(1:length(idx2), num_ticks) 
if (length(tick_positions) > num_ticks) {
    tick_positions <- tick_positions[seq(1, length(tick_positions), length.out = num_ticks)]
}
tick_labels <- format(selected_dates[match(tick_positions, 1:length(idx2))], "%Y-%m-%d")
axis(1, at = tick_positions, labels = FALSE) 
text(x = tick_positions, y = par("usr")[3] - 0.025 * diff(par("usr")[3:4]), labels = tick_labels, 
     srt = 45, adj = 1, xpd = TRUE, cex = 0.8, col = "black")

# Adding a vertical line for the forecast start date
forecast_date <- as.Date("2022-12-25")
forecast_position <- which(selected_dates == forecast_date)
abline(v = forecast_position, col = "black", lty = 1, lwd = 0.8)

# Adding the label for the forecast start date
text(x = forecast_position, y = par("usr")[4] + 0.03 * diff(par("usr")[3:4]), 
     labels = "forecast start date", col = "red", pos = 3, cex = 1.2, font = 2)

abline(h = 0)

dev.off()

p <- 7

png("/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics_reproduce/All_conv_VB_DISC.png", width = 6000, height = 4000, res = 600)
par(mfrow = c(2, 7), mar = c(2, 2, 2, 1), oma = c(0, 0, 3, 0))

colors <- c("forestgreen", "darkorange", "darkblue")

a <- 0

seq.sigma_5_exAL_synth_DISC[,1:a] = NaN
ts.plot(t(seq.sigma_5_exAL_synth_DISC), col = colors, main = "Sigma 05th", xlab = "Iteration", ylab = "Sigma", lwd = 2, ylim = c(0,0.2))

seq.sigma_20_exAL_synth_DISC[,1:a] = NaN
ts.plot(t(seq.sigma_20_exAL_synth_DISC), col = colors, main = "Sigma 20th", xlab = "Iteration", ylab = "Sigma", lwd = 2, ylim = c(0,0.2))

seq.sigma_35_exAL_synth_DISC[,1:a] = NaN
ts.plot(t(seq.sigma_35_exAL_synth_DISC), col = colors, main = "Sigma 35th", xlab = "Iteration", ylab = "Sigma", lwd = 2, ylim = c(0,0.2))

seq.sigma_50_exAL_synth_DISC[,1:a] = NaN
ts.plot(t(seq.sigma_50_exAL_synth_DISC), col = colors, main = "Sigma 50th", xlab = "Iteration", ylab = "Sigma", lwd = 2, ylim = c(0,0.2))

seq.sigma_65_exAL_synth_DISC[,1:a] = NaN
ts.plot(t(seq.sigma_65_exAL_synth_DISC), col = colors, main = "Sigma 65th", xlab = "Iteration", ylab = "Sigma", lwd = 2, ylim = c(0,0.2))

seq.sigma_80_exAL_synth_DISC[,1:a] = NaN
ts.plot(t(seq.sigma_80_exAL_synth_DISC), col = colors, main = "Sigma 80th", xlab = "Iteration", ylab = "Sigma", lwd = 2, ylim = c(0,0.2))

seq.sigma_95_exAL_synth_DISC[,1:a] = NaN
ts.plot(t(seq.sigma_95_exAL_synth_DISC), col = colors, main = "Sigma 95th", xlab = "Iteration", ylab = "Sigma", lwd = 2, ylim = c(0,0.2))

seq.gamma_5_exAL_synth_DISC[,1:a] = NaN
ts.plot(t(seq.gamma_5_exAL_synth_DISC), col = colors, main = "Gamma 05th", xlab = "Iteration", ylab = "Gamma", lwd = 2, ylim = c(-3,1))

seq.gamma_20_exAL_synth_DISC[,1:a] = NaN
ts.plot(t(seq.gamma_20_exAL_synth_DISC), col = colors, main = "Gamma 20th", xlab = "Iteration", ylab = "Gamma", lwd = 2, ylim = c(-3,1))

seq.gamma_35_exAL_synth_DISC[,1:a] = NaN
ts.plot(t(seq.gamma_35_exAL_synth_DISC), col = colors, main = "Gamma 35th", xlab = "Iteration", ylab = "Gamma", lwd = 2, ylim = c(-3,1))

seq.gamma_50_exAL_synth_DISC[,1:a] = NaN
ts.plot(t(seq.gamma_50_exAL_synth_DISC), col = colors, main = "Gamma 50th", xlab = "Iteration", ylab = "Gamma", lwd = 2, ylim = c(-3,1))

seq.gamma_65_exAL_synth_DISC[,1:a] = NaN
ts.plot(t(seq.gamma_65_exAL_synth_DISC), col = colors, main = "Gamma 65th", xlab = "Iteration", ylab = "Gamma", lwd = 2, ylim = c(-3,1))

seq.gamma_80_exAL_synth_DISC[,1:a] = NaN
ts.plot(t(seq.gamma_80_exAL_synth_DISC), col = colors, main = "Gamma 80th", xlab = "Iteration", ylab = "Sigma", lwd = 2, ylim = c(-3,1))

seq.gamma_95_exAL_synth_DISC[,1:a] = NaN
ts.plot(t(seq.gamma_95_exAL_synth_DISC), col = colors, main = "Gamma 95th", xlab = "Iteration", ylab = "Gamma", lwd = 2, ylim = c(-3,1))


# # Add a common legend to the plot
# # Placing the legend at the top of the first column (adjust `oma` and `mar` for space)
# mtext("Green - USGS, Orange - GLOFAS, Blue - NWS", side = 3, outer = TRUE, line = 0, cex = 0.8)
# par(mfrow = c(2, 4), mar = c(4, 4, 2, 1), oma = c(0, 0, 3, 0))
# # Plot each time series with the specified colors

mtext("Green - USGS, Orange - GLOFAS, Blue - NWS", side = 3, outer = TRUE, line = 0, cex = 0.8)
dev.off()
par(mfrow = c(1, 1), mar = c(5, 4, 4, 2) + 0.1, oma = c(0, 0, 0, 0))

# Define a function to calculate quantiles for each row (source) in the dataset
calculate_quantiles <- function(data, variable_name, quantile_name, source_name) {
  quantile_values <- quantile(data, probs = c(0.025, 0.5, 0.975))
  tibble(
    variable = variable_name,
    source = source_name,
    quantile = quantile_name,
    quantile_025 = quantile_values["2.5%"],
    median = quantile_values["50%"],
    quantile_975 = quantile_values["97.5%"]
  )
}

# List of datasets and their metadata
data_sets <- list(
  gamma_50_M = list(data = samp.gamma_50_exAL_synth_DISC, quantile = "50th", variable = "Gamma"),
  gamma_95_M = list(data = samp.gamma_95_exAL_synth_DISC, quantile = "95th", variable = "Gamma"),
  gamma_05_M = list(data = samp.gamma_5_exAL_synth_DISC, quantile = "05th", variable = "Gamma"),
  gamma_20_M = list(data = samp.gamma_20_exAL_synth_DISC, quantile = "20th", variable = "Gamma"),
  gamma_35_M = list(data = samp.gamma_35_exAL_synth_DISC, quantile = "35th", variable = "Gamma"),
  gamma_65_M = list(data = samp.gamma_65_exAL_synth_DISC, quantile = "65th", variable = "Gamma"),
  gamma_80_M = list(data = samp.gamma_80_exAL_synth_DISC, quantile = "80th", variable = "Gamma"),
  sigma_50_M = list(data = samp.sigma_50_exAL_synth_DISC, quantile = "50th", variable = "Sigma"),
  sigma_95_M = list(data = samp.sigma_95_exAL_synth_DISC, quantile = "95th", variable = "Sigma"),
  sigma_05_M = list(data = samp.sigma_5_exAL_synth_DISC, quantile = "05th", variable = "Sigma"),
  sigma_20_M = list(data = samp.sigma_20_exAL_synth_DISC, quantile = "20th", variable = "Sigma"),
  sigma_35_M = list(data = samp.sigma_35_exAL_synth_DISC, quantile = "35th", variable = "Sigma"),
  sigma_65_M = list(data = samp.sigma_65_exAL_synth_DISC, quantile = "65th", variable = "Sigma"),
  sigma_80_M = list(data = samp.sigma_80_exAL_synth_DISC, quantile = "80th", variable = "Sigma")
)

# Calculate quantiles for each dataset and source
all_quantiles <- bind_rows(
  lapply(data_sets, function(item) {
    bind_rows(
      calculate_quantiles(item$data[1, ], item$variable, item$quantile, "USGS"),
      calculate_quantiles(item$data[2, ], item$variable, item$quantile, "GLOFAS"),
      calculate_quantiles(item$data[3, ], item$variable, item$quantile, "NWS")
    )
  })
)

# Print the complete table of quantiles
print(all_quantiles, n = Inf)


prepare_quantile_data <- function(v_d) {
  if (exists("fast_prepare_quantile_data", mode = "function")) {
    return(fast_prepare_quantile_data(v_d, probs = c(0.975, 0.5, 0.025), type = 7L, na.rm = FALSE))
  }

  v_d_transposed <- aperm(v_d, c(3, 1, 2))
  q_d_transposed <- apply(v_d_transposed, 2:3, function(x) quantile(x, probs = c(0.975, 0.5, 0.025)))
  q_d <- aperm(q_d_transposed, c(2, 3, 1))
  q_d
}
q_d_50 <- prepare_quantile_data(samp.theta_50_exAL_synth_DISC$samp_theta)
q_d_05 <- prepare_quantile_data(samp.theta_5_exAL_synth_DISC$samp_theta)
q_d_95 <- prepare_quantile_data(samp.theta_95_exAL_synth_DISC$samp_theta)

q_d_20 <- prepare_quantile_data(samp.theta_20_exAL_synth_DISC$samp_theta)
q_d_35 <- prepare_quantile_data(samp.theta_35_exAL_synth_DISC$samp_theta)
q_d_65 <- prepare_quantile_data(samp.theta_65_exAL_synth_DISC$samp_theta)
q_d_80 <- prepare_quantile_data(samp.theta_80_exAL_synth_DISC$samp_theta)

prepare_quantile_data <- function(v_d) {
  v_d_transposed <- aperm(v_d, c(3, 1, 2))
  q_d_transposed <- apply(v_d_transposed, 2:3, function(x) quantile(x, probs = c(0.975, 0.5, 0.025)))
  q_d <- aperm(q_d_transposed, c(2, 3, 1))
  return(q_d)
}

q_d_NDLM <- prepare_quantile_data(samp.theta_50_NDLM_synth_DISC$samp_theta)

# 

time_cuts <- which(timestamps %in% c("2012-08-01","2016-05-01","2016-09-15","2019-08-01") )


png("/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics_reproduce/All_exal_ndlm_2012-2016_DISC.png", width = 6000, height = 4000, res = 600)
par(mar = c(4, 4, 2, 1) + 0.1)

idx <- time_cuts[1]:time_cuts[2]
percentiles <- c(0.025, 0.5, 0.975)
######################################################################################
######################################################################################
## Base
plot.ts(idx, (new.theta.out_50_exAL_synth_DISC$exps[1,idx])*0, ylim = c(-2, 2),  type="l", lwd = 1,
        main = "Quantile Dynamics     -    2012-2016",
        xlab = " ", ylab = "log-flow", xaxt = "n")
lines(idx, Y[1,idx], col = 'black')
points(idx, Y[1,idx], col = 'gray')
points(idx, Y[1,idx], col = 'black', pch = 19, cex = 0.5, lwd = 0.1)
######################################################################################
## 50th Quantile
########
result <- fast_row_quantiles_t(xbs_retro[4, , ], probs = percentiles)
lines(idx, result[1,idx], ylim = c(0,6),col = 'green', lty = 2, lwd=0.5)
lines(idx, result[2,idx],col = 'darkgreen', lwd=0.5)
lines(idx, result[3,idx],col = 'green', lty = 2, lwd=0.5)
######################################################################################
######################################################################################
## 5th Quantile
########
result <- fast_row_quantiles_t(xbs_retro[1, , ], probs = percentiles)
lines(idx, result[1,idx], ylim = c(0,6),col = 'red', lty = 2, lwd=0.5)
lines(idx, result[2,idx],col = 'darkred', lwd=0.5)
lines(idx, result[3,idx],col = 'red', lty = 2, lwd=0.5)
######################################################################################
######################################################################################
## 95th Quantile
########
result <- fast_row_quantiles_t(xbs_retro[7, , ], probs = percentiles)
lines(idx, result[1,idx], ylim = c(0,6),col = 'blue', lty = 2, lwd=0.5)
lines(idx, result[2,idx],col = 'darkblue', lwd=0.5)
lines(idx, result[3,idx],col = 'blue', lty = 2, lwd=0.5)
######################################################################################
######################################################################################
## NDLM
########
result <- fast_row_quantiles_t(xbs_ndlm_retro[1, , ], probs = percentiles)
lines(idx, result[1,idx], ylim = c(0,6),col = 'orange', lty = 2, lwd=0.5)
lines(idx, result[2,idx],col = 'darkorange', lwd=0.5)
lines(idx, result[3,idx],col = 'orange', lty = 2, lwd=0.5)



######################################################################################
## 80th Quantile
########
result <- fast_row_quantiles_t(xbs_retro[6, , ], probs = percentiles)
lines(idx, result[1,idx], ylim = c(0,6),col = 'purple', lty = 2, lwd=0.5)
lines(idx, result[2,idx],col = 'purple', lwd=0.5)
lines(idx, result[3,idx],col = 'purple', lty = 2, lwd=0.5)
######################################################################################
######################################################################################
## 65th Quantile
########
result <- fast_row_quantiles_t(xbs_retro[5, , ], probs = percentiles)
lines(idx, result[1,idx], ylim = c(0,6),col = 'purple', lty = 2, lwd=0.5)
lines(idx, result[2,idx],col = 'purple', lwd=0.5)
lines(idx, result[3,idx],col = 'purple', lty = 2, lwd=0.5)
######################################################################################
######################################################################################
## 35th Quantile
########
result <- fast_row_quantiles_t(xbs_retro[3, , ], probs = percentiles)
lines(idx, result[1,idx], ylim = c(0,6),col = 'purple', lty = 2, lwd=0.5)
lines(idx, result[2,idx],col = 'purple', lwd=0.5)
lines(idx, result[3,idx],col = 'purple', lty = 2, lwd=0.5)
######################################################################################
######################################################################################
## 20th Quantile
########
result <- fast_row_quantiles_t(xbs_retro[2, , ], probs = percentiles)
lines(idx, result[1,idx], ylim = c(0,6),col = 'purple', lty = 2, lwd=0.5)
lines(idx, result[2,idx],col = 'purple', lwd=0.5)
lines(idx, result[3,idx],col = 'purple', lty = 2, lwd=0.5)
######################################################################################

lev_flood <- c(21.76,19.5,16.5,14) 
abline(h=log(lev_flood+1), lwd=0.5, lty = 2)
######################################################################################
# NDLM
# sd_ndlm <- mean(sqrt(samp.sigma_50_NDLM_synth[1,]))
# estim_dqlm <- new.theta.out_50_NDLM_synth$exps[1,idx]
# lines(idx_f, estim_dqlm+sd_ndlm*qnorm(0.5), col="orange", lwd=2)
# lines(new.theta.out_50_NDLM_synth$exps[1,idx1]+sd_ndlm*qnorm(0.5), col='orange')

selected_dates <- dates_ts_usgs[idx] 
num_ticks <- 35
tick_positions <- pretty(idx, num_ticks) 
if (length(tick_positions) > num_ticks) {
    tick_positions <- tick_positions[seq(1, length(tick_positions), length.out = num_ticks)]
}
tick_labels <- format(selected_dates[match(tick_positions, idx)], "%Y-%m-%d")
axis(1, at = tick_positions, labels = FALSE) 
text(x = tick_positions, y = par("usr")[3] - 0.025 * diff(par("usr")[3:4]), labels = tick_labels, srt = 45, adj = 1, xpd = TRUE, cex = 0.8)
dev.off()

png("/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics_reproduce/All_exal_ndlm_2017-2019_DISC.png", width = 6000, height = 4000, res = 600)
par(mar = c(4, 4, 2, 1) + 0.1)

idx <- time_cuts[3]:time_cuts[4]
percentiles <- c(0.025, 0.5, 0.975)
######################################################################################
######################################################################################
## Base
plot.ts(idx, (new.theta.out_50_exAL_synth_DISC$exps[1,idx])*0, ylim = c(-2, 2),  type="l", lwd = 1,
        main = "Quantile Dynamics     -    2017-2019",
        xlab = " ", ylab = "log-flow", xaxt = "n")
lines(idx, Y[1,idx], col = 'black', lwd = 0.1)
points(idx, Y[1,idx], col = 'gray')
points(idx, Y[1,idx], col = 'black', pch = 19, cex = 0.5, lwd = 0.1)
######################################################################################
## 50th Quantile
########
result <- fast_row_quantiles_t(xbs_retro[4, , ], probs = percentiles)
lines(idx, result[1,idx], ylim = c(0,6),col = 'green', lty = 2, lwd=0.5)
lines(idx, result[2,idx],col = 'darkgreen', lwd=0.5)
lines(idx, result[3,idx],col = 'green', lty = 2, lwd=0.5)
######################################################################################
######################################################################################
## 5th Quantile
########
result <- fast_row_quantiles_t(xbs_retro[1, , ], probs = percentiles)
lines(idx, result[1,idx], ylim = c(0,6),col = 'red', lty = 2, lwd=0.5)
lines(idx, result[2,idx],col = 'darkred', lwd=0.5)
lines(idx, result[3,idx],col = 'red', lty = 2, lwd=0.5)
######################################################################################
######################################################################################
## 95th Quantile
########
result <- fast_row_quantiles_t(xbs_retro[7, , ], probs = percentiles)
lines(idx, result[1,idx], ylim = c(0,6),col = 'blue', lty = 2, lwd=0.5)
lines(idx, result[2,idx],col = 'darkblue', lwd=0.5)
lines(idx, result[3,idx],col = 'blue', lty = 2, lwd=0.5)
######################################################################################
######################################################################################
## NDLM
########
result <- fast_row_quantiles_t(xbs_ndlm_retro[1, , ], probs = percentiles)
lines(idx, result[1,idx], ylim = c(0,6),col = 'orange', lty = 2, lwd=0.5)
lines(idx, result[2,idx],col = 'darkorange', lwd=0.5)
lines(idx, result[3,idx],col = 'orange', lty = 2, lwd=0.5)



######################################################################################
## 80th Quantile
########
result <- fast_row_quantiles_t(xbs_retro[6, , ], probs = percentiles)
lines(idx, result[1,idx], ylim = c(0,6),col = 'purple', lty = 2, lwd=0.5)
lines(idx, result[2,idx],col = 'purple', lwd=0.5)
lines(idx, result[3,idx],col = 'purple', lty = 2, lwd=0.5)
######################################################################################
######################################################################################
## 65th Quantile
########
result <- fast_row_quantiles_t(xbs_retro[5, , ], probs = percentiles)
lines(idx, result[1,idx], ylim = c(0,6),col = 'purple', lty = 2, lwd=0.5)
lines(idx, result[2,idx],col = 'purple', lwd=0.5)
lines(idx, result[3,idx],col = 'purple', lty = 2, lwd=0.5)
######################################################################################
######################################################################################
## 35th Quantile
########
result <- fast_row_quantiles_t(xbs_retro[3, , ], probs = percentiles)
lines(idx, result[1,idx], ylim = c(0,6),col = 'purple', lty = 2, lwd=0.5)
lines(idx, result[2,idx],col = 'purple', lwd=0.5)
lines(idx, result[3,idx],col = 'purple', lty = 2, lwd=0.5)
######################################################################################
######################################################################################
## 20th Quantile
########
result <- fast_row_quantiles_t(xbs_retro[2, , ], probs = percentiles)
lines(idx, result[1,idx], ylim = c(0,6),col = 'purple', lty = 2, lwd=0.5)
lines(idx, result[2,idx],col = 'purple', lwd=0.5)
lines(idx, result[3,idx],col = 'purple', lty = 2, lwd=0.5)
######################################################################################

lev_flood <- c(21.76,19.5,16.5,14) 
abline(h=log(lev_flood+1), lwd=0.5, lty = 2)
######################################################################################
# NDLM
# sd_ndlm <- mean(sqrt(samp.sigma_50_NDLM_synth[1,]))
# estim_dqlm <- new.theta.out_50_NDLM_synth$exps[1,idx]
# lines(idx_f, estim_dqlm+sd_ndlm*qnorm(0.5), col="orange", lwd=2)
# lines(new.theta.out_50_NDLM_synth$exps[1,idx1]+sd_ndlm*qnorm(0.5), col='orange')

selected_dates <- dates_ts_usgs[idx] 
num_ticks <- 25
tick_positions <- pretty(idx, num_ticks) 
if (length(tick_positions) > num_ticks) {
    tick_positions <- tick_positions[seq(1, length(tick_positions), length.out = num_ticks)]
}
tick_labels <- format(selected_dates[match(tick_positions, idx)], "%Y-%m-%d")
axis(1, at = tick_positions, labels = FALSE) 
text(x = tick_positions, y = par("usr")[3] - 0.025 * diff(par("usr")[3:4]), labels = tick_labels, srt = 45, adj = 1, xpd = TRUE, cex = 0.8)

dev.off()

png("/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics_reproduce/All3_exal_ndlm_2012-2016_DISC.png", width = 6000, height = 4000, res = 600)
par(mar = c(4, 4, 2, 1) + 0.1)
par(mfrow = c(1, 1), mar = c(4, 4, 2, 1), oma = c(4, 0, 0, 0))

idx <- time_cuts[1]:time_cuts[2]
percentiles <- c(0.025, 0.5, 0.975)
######################################################################################
######################################################################################
## Base
plot.ts(idx, (new.theta.out_50_exAL_synth_DISC$exps[1,idx])*0, ylim = c(-2, 2),  type="l", lwd = 1,
        main = "Quantile Dynamics     -    2012-2016",
        xlab = " ", ylab = "log-flow", xaxt = "n")
lines(idx, Y[1,idx], col = 'black', lwd = 0.1)
points(idx, Y[1,idx], col = 'gray')
points(idx, Y[1,idx], col = 'black', pch = 19, cex = 0.5, lwd = 0.1)
######################################################################################
######################################################################################
## 50th Quantile
########
result <- fast_row_quantiles_t(xbs_retro[4, , ], probs = percentiles)
lines(idx, result[1,idx], ylim = c(0,6),col = 'green', lty = 2, lwd=0.5)
lines(idx, result[2,idx],col = 'darkgreen', lwd=0.5)
lines(idx, result[3,idx],col = 'green', lty = 2, lwd=0.5)
######################################################################################
######################################################################################
## 5th Quantile
########
result <- fast_row_quantiles_t(xbs_retro[1, , ], probs = percentiles)
lines(idx, result[1,idx], ylim = c(0,6),col = 'red', lty = 2, lwd=0.5)
lines(idx, result[2,idx],col = 'darkred', lwd=0.5)
lines(idx, result[3,idx],col = 'red', lty = 2, lwd=0.5)
######################################################################################
######################################################################################
## 95th Quantile
########
result <- fast_row_quantiles_t(xbs_retro[7, , ], probs = percentiles)
lines(idx, result[1,idx], ylim = c(0,6),col = 'blue', lty = 2, lwd=0.5)
lines(idx, result[2,idx],col = 'darkblue', lwd=0.5)
lines(idx, result[3,idx],col = 'blue', lty = 2, lwd=0.5)
######################################################################################
######################################################################################
## NDLM
########
result <- fast_row_quantiles_t(xbs_ndlm_retro[1, , ], probs = percentiles)
lines(idx, result[1,idx], ylim = c(0,6),col = 'orange', lty = 2, lwd=0.5)
lines(idx, result[2,idx],col = 'darkorange', lwd=0.5)
lines(idx, result[3,idx],col = 'orange', lty = 2, lwd=0.5)


lev_flood <- c(21.76,19.5,16.5,14) 
abline(h=log(lev_flood+1), lwd=0.5, lty = 2)
######################################################################################
# NDLM
# sd_ndlm <- mean(sqrt(samp.sigma_50_NDLM_synth[1,]))
# estim_dqlm <- new.theta.out_50_NDLM_synth$exps[1,idx]
# lines(idx_f, estim_dqlm+sd_ndlm*qnorm(0.5), col="orange", lwd=2)
# lines(new.theta.out_50_NDLM_synth$exps[1,idx1]+sd_ndlm*qnorm(0.5), col='orange')

selected_dates <- dates_ts_usgs[idx] 
num_ticks <- 35
tick_positions <- pretty(idx, num_ticks) 
if (length(tick_positions) > num_ticks) {
    tick_positions <- tick_positions[seq(1, length(tick_positions), length.out = num_ticks)]
}
tick_labels <- format(selected_dates[match(tick_positions, idx)], "%Y-%m-%d")
axis(1, at = tick_positions, labels = FALSE) 
text(x = tick_positions, y = par("usr")[3] - 0.025 * diff(par("usr")[3:4]), labels = tick_labels, srt = 45, adj = 1, xpd = TRUE, cex = 0.8)

mtext("Forest Green: 50th Quantile | Dark Red: 5th Quantile | Dark Blue: 95th Quantile | Orange: Average", side = 1, outer = TRUE, line = 2, cex = 0.8)

dev.off()


png("/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics_reproduce/All3_exal_2012-2016_DISC.png", width = 6000, height = 4000, res = 600)
par(mar = c(4, 4, 2, 1) + 0.1)
par(mfrow = c(1, 1), mar = c(4, 4, 2, 1), oma = c(4, 0, 0, 0))

idx <- time_cuts[1]:time_cuts[2]
percentiles <- c(0.025, 0.5, 0.975)
######################################################################################
######################################################################################
## Base
plot.ts(idx, (new.theta.out_50_exAL_synth_DISC$exps[1,idx])*0, ylim = c(-2, 2),  type="l", lwd = 1,
        main = "Quantile Dynamics     -    2012-2016",
        xlab = " ", ylab = "log-flow", xaxt = "n")
lines(idx, Y[1,idx], col = 'black', lwd = 0.1)
points(idx, Y[1,idx], col = 'gray')
points(idx, Y[1,idx], col = 'black', pch = 19, cex = 0.5, lwd = 0.1)
######################################################################################
######################################################################################
## 50th Quantile
########
result <- fast_row_quantiles_t(xbs_retro[4, , ], probs = percentiles)
lines(idx, result[1,idx], ylim = c(0,6),col = 'green', lty = 2, lwd=0.5)
lines(idx, result[2,idx],col = 'darkgreen', lwd=0.5)
lines(idx, result[3,idx],col = 'green', lty = 2, lwd=0.5)
######################################################################################
######################################################################################
## 5th Quantile
########
result <- fast_row_quantiles_t(xbs_retro[1, , ], probs = percentiles)
lines(idx, result[1,idx], ylim = c(0,6),col = 'red', lty = 2, lwd=0.5)
lines(idx, result[2,idx],col = 'darkred', lwd=0.5)
lines(idx, result[3,idx],col = 'red', lty = 2, lwd=0.5)
######################################################################################
######################################################################################
## 95th Quantile
########
result <- fast_row_quantiles_t(xbs_retro[7, , ], probs = percentiles)
lines(idx, result[1,idx], ylim = c(0,6),col = 'blue', lty = 2, lwd=0.5)
lines(idx, result[2,idx],col = 'darkblue', lwd=0.5)
lines(idx, result[3,idx],col = 'blue', lty = 2, lwd=0.5)
######################################################################################
######################################################################################


lev_flood <- c(21.76,19.5,16.5,14) 
abline(h=log(lev_flood+1), lwd=0.5, lty = 2)
######################################################################################
# NDLM
# sd_ndlm <- mean(sqrt(samp.sigma_50_NDLM_synth[1,]))
# estim_dqlm <- new.theta.out_50_NDLM_synth$exps[1,idx]
# lines(idx_f, estim_dqlm+sd_ndlm*qnorm(0.5), col="orange", lwd=2)
# lines(new.theta.out_50_NDLM_synth$exps[1,idx1]+sd_ndlm*qnorm(0.5), col='orange')

selected_dates <- dates_ts_usgs[idx] 
num_ticks <- 35
tick_positions <- pretty(idx, num_ticks) 
if (length(tick_positions) > num_ticks) {
    tick_positions <- tick_positions[seq(1, length(tick_positions), length.out = num_ticks)]
}
tick_labels <- format(selected_dates[match(tick_positions, idx)], "%Y-%m-%d")
axis(1, at = tick_positions, labels = FALSE) 
text(x = tick_positions, y = par("usr")[3] - 0.025 * diff(par("usr")[3:4]), labels = tick_labels, srt = 45, adj = 1, xpd = TRUE, cex = 0.8)

mtext("Forest Green: 50th Quantile | Dark Red: 5th Quantile | Dark Blue: 95th Quantile", side = 1, outer = TRUE, line = 2, cex = 0.8)

dev.off()

png("/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics_reproduce/All3_exal_ndlm_2017-2019_DISC.png", width = 6000, height = 4000, res = 600)
par(mar = c(4, 4, 2, 1) + 0.1)
par(mfrow = c(1, 1), mar = c(4, 4, 2, 1), oma = c(4, 0, 0, 0))

idx <- time_cuts[3]:time_cuts[4]
percentiles <- c(0.025, 0.5, 0.975)
######################################################################################
######################################################################################
## Base
plot.ts(idx, (new.theta.out_50_exAL_synth_DISC$exps[1,idx])*0, ylim = c(-2, 2),  type="l", lwd = 1,
        main = "Quantile Dynamics     -    2017-2019",
        xlab = " ", ylab = "log-flow", xaxt = "n")
lines(idx, Y[1,idx], col = 'black', lwd = 0.1)
points(idx, Y[1,idx], col = 'gray')
points(idx, Y[1,idx], col = 'black', pch = 19, cex = 0.5, lwd = 0.1)
######################################################################################
######################################################################################
## 50th Quantile
########
result <- fast_row_quantiles_t(xbs_retro[4, , ], probs = percentiles)
lines(idx, result[1,idx], ylim = c(0,6),col = 'green', lty = 2, lwd=0.5)
lines(idx, result[2,idx],col = 'darkgreen', lwd=0.5)
lines(idx, result[3,idx],col = 'green', lty = 2, lwd=0.5)
######################################################################################
######################################################################################
## 5th Quantile
########
result <- fast_row_quantiles_t(xbs_retro[1, , ], probs = percentiles)
lines(idx, result[1,idx], ylim = c(0,6),col = 'red', lty = 2, lwd=0.5)
lines(idx, result[2,idx],col = 'darkred', lwd=0.5)
lines(idx, result[3,idx],col = 'red', lty = 2, lwd=0.5)
######################################################################################
######################################################################################
## 95th Quantile
########
result <- fast_row_quantiles_t(xbs_retro[7, , ], probs = percentiles)
lines(idx, result[1,idx], ylim = c(0,6),col = 'blue', lty = 2, lwd=0.5)
lines(idx, result[2,idx],col = 'darkblue', lwd=0.5)
lines(idx, result[3,idx],col = 'blue', lty = 2, lwd=0.5)
######################################################################################
######################################################################################
## NDLM
########
result <- fast_row_quantiles_t(xbs_ndlm_retro[1, , ], probs = percentiles)
lines(idx, result[1,idx], ylim = c(0,6),col = 'orange', lty = 2, lwd=0.5)
lines(idx, result[2,idx],col = 'darkorange', lwd=0.5)
lines(idx, result[3,idx],col = 'orange', lty = 2, lwd=0.5)


lev_flood <- c(21.76,19.5,16.5,14) 
abline(h=log(lev_flood+1), lwd=0.5, lty = 2)
######################################################################################

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

dev.off()

# png("/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics_reproduce/All3_exal_ndlm_2017-2019_DISC.png", width = 6000, height = 4000, res = 600)
par(mar = c(4, 4, 2, 1) + 0.1)
par(mfrow = c(1, 1), mar = c(4, 4, 2, 1), oma = c(4, 0, 0, 0))

idx <- time_cuts[1]:time_cuts[2]
percentiles <- c(0.025, 0.5, 0.975)
######################################################################################
######################################################################################
## Base
plot.ts(idx, (new.theta.out_50_exAL_synth_DISC$exps[1,idx])*0, ylim = c(-2, 2),  type="l", lwd = 1,
        main = "Quantile Dynamics     -    2017-2019",
        xlab = " ", ylab = "log-flow", xaxt = "n")
lines(idx, Y[1,idx], col = 'black', lwd = 0.1)
points(idx, Y[1,idx], col = 'gray')
points(idx, Y[1,idx], col = 'black', pch = 19, cex = 0.5, lwd = 0.1)
######################################################################################
######################################################################################
## 50th Quantile
########
result <- fast_row_quantiles_t(xbs_retro[4, , ], probs = percentiles)
lines(idx, result[1,idx], ylim = c(0,6),col = 'green', lty = 2, lwd=0.5)
lines(idx, result[2,idx],col = 'darkgreen', lwd=0.5)
lines(idx, result[3,idx],col = 'green', lty = 2, lwd=0.5)
######################################################################################
######################################################################################
## 5th Quantile
########
result <- fast_row_quantiles_t(xbs_retro[1, , ], probs = percentiles)
lines(idx, result[1,idx], ylim = c(0,6),col = 'red', lty = 2, lwd=0.5)
lines(idx, result[2,idx],col = 'darkred', lwd=0.5)
lines(idx, result[3,idx],col = 'red', lty = 2, lwd=0.5)
######################################################################################
######################################################################################
## 95th Quantile
########
result <- fast_row_quantiles_t(xbs_retro[7, , ], probs = percentiles)
lines(idx, result[1,idx], ylim = c(0,6),col = 'blue', lty = 2, lwd=0.5)
lines(idx, result[2,idx],col = 'darkblue', lwd=0.5)
lines(idx, result[3,idx],col = 'blue', lty = 2, lwd=0.5)
######################################################################################
######################################################################################
## NDLM
########
result <- fast_row_quantiles_t(xbs_ndlm_retro[1, , ], probs = percentiles)
lines(idx, result[1,idx], ylim = c(0,6),col = 'orange', lty = 2, lwd=0.5)
lines(idx, result[2,idx],col = 'darkorange', lwd=0.5)
lines(idx, result[3,idx],col = 'orange', lty = 2, lwd=0.5)


lev_flood <- c(21.76,19.5,16.5,14) 
abline(h=log(lev_flood+1), lwd=0.5, lty = 2)
######################################################################################

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

# dev.off()

idx <- (TT-2000):(TT)
# yy <- new.theta.out_95_exAL_synth_DISC$standard_forecast_errors[1,idx]
yy <- Y[1,idx]
yy <- (yy-mean(yy))/sd(yy)
plot.ts(yy, ylim = c(-3,3), col = 'gray')
yy <- new.theta.out_95_exAL_synth_DISC$sm[22,idx]
yy <- (yy-mean(yy))/sd(yy)
lines(yy, col = 'blue')
yy <- new.theta.out_5_exAL_synth_DISC$sm[22,idx]
yy <- 
(yy-mean(yy))/sd(yy)
lines(yy, col = 'red')
yy <- new.theta.out_50_exAL_synth_DISC$sm[22,idx]
yy <- (yy-mean(yy))/sd(yy)
lines(yy, col = 'green')


png("/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics_reproduce/All_exal_ndlm_2018-2021_DISC.png", width = 6000, height = 4000, res = 60)
idx <- time_cuts[3]:time_cuts[4]
percentiles <- c(0.025, 0.5, 0.975)
######################################################################################
######################################################################################
## Base
plot.ts(idx, (new.theta.out_50_exAL_synth_DISC$exps[1,idx])*0, ylim = c(-2, 2),  type="l", lwd = 1,
        main = "Quantile Dynamics     -    2017-2019",
        xlab = " ", ylab = "log-flow", xaxt = "n")
lines(idx, Y[1,idx], col = 'black', lwd = 0.1)
points(idx, Y[1,idx], col = 'gray')
points(idx, Y[1,idx], col = 'black', pch = 19, cex = 0.5, lwd = 0.1)
######################################################################################
######################################################################################
## 50th Quantile
########
result <- fast_row_quantiles_t(xbs_retro[4, , ], probs = percentiles)
lines(idx, result[1,idx], ylim = c(0,6),col = 'green', lty = 2, lwd=0.5)
lines(idx, result[2,idx],col = 'darkgreen', lwd=0.5)
lines(idx, result[3,idx],col = 'green', lty = 2, lwd=0.5)
######################################################################################
######################################################################################
## 5th Quantile
########
result <- fast_row_quantiles_t(xbs_retro[1, , ], probs = percentiles)
lines(idx, result[1,idx], ylim = c(0,6),col = 'red', lty = 2, lwd=0.5)
lines(idx, result[2,idx],col = 'darkred', lwd=0.5)
lines(idx, result[3,idx],col = 'red', lty = 2, lwd=0.5)
######################################################################################
######################################################################################
## 95th Quantile
########
result <- fast_row_quantiles_t(xbs_retro[7, , ], probs = percentiles)
lines(idx, result[1,idx], ylim = c(0,6),col = 'blue', lty = 2, lwd=0.5)
lines(idx, result[2,idx],col = 'darkblue', lwd=0.5)
lines(idx, result[3,idx],col = 'blue', lty = 2, lwd=0.5)
######################################################################################
######################################################################################
## NDLM
########
result <- fast_row_quantiles_t(xbs_ndlm_retro[1, , ], probs = percentiles)
lines(idx, result[1,idx], ylim = c(0,6),col = 'orange', lty = 2, lwd=0.5)
lines(idx, result[2,idx],col = 'darkorange', lwd=0.5)
lines(idx, result[3,idx],col = 'orange', lty = 2, lwd=0.5)

######################################################################################
## 80th Quantile
########
result <- fast_row_quantiles_t(xbs_retro[6, , ], probs = percentiles)
lines(idx, result[1,idx], ylim = c(0,6),col = 'purple', lty = 2, lwd=0.5)
lines(idx, result[2,idx],col = 'purple', lwd=0.5)
lines(idx, result[3,idx],col = 'purple', lty = 2, lwd=0.5)
######################################################################################
######################################################################################
## 65th Quantile
########
result <- fast_row_quantiles_t(xbs_retro[5, , ], probs = percentiles)
lines(idx, result[1,idx], ylim = c(0,6),col = 'purple', lty = 2, lwd=0.5)
lines(idx, result[2,idx],col = 'purple', lwd=0.5)
lines(idx, result[3,idx],col = 'purple', lty = 2, lwd=0.5)
######################################################################################
######################################################################################
## 35th Quantile
########
result <- fast_row_quantiles_t(xbs_retro[3, , ], probs = percentiles)
lines(idx, result[1,idx], ylim = c(0,6),col = 'purple', lty = 2, lwd=0.5)
lines(idx, result[2,idx],col = 'purple', lwd=0.5)
lines(idx, result[3,idx],col = 'purple', lty = 2, lwd=0.5)
######################################################################################
######################################################################################
## 20th Quantile
########
result <- fast_row_quantiles_t(xbs_retro[2, , ], probs = percentiles)
lines(idx, result[1,idx], ylim = c(0,6),col = 'purple', lty = 2, lwd=0.5)
lines(idx, result[2,idx],col = 'purple', lwd=0.5)
lines(idx, result[3,idx],col = 'purple', lty = 2, lwd=0.5)
######################################################################################

lev_flood <- c(21.76,19.5,16.5,14) 
abline(h=log(lev_flood+1), lwd=0.5, lty = 2)

selected_dates <- dates_ts_usgs[idx] 
num_ticks <- 25
tick_positions <- pretty(idx, num_ticks) 
if (length(tick_positions) > num_ticks) {
    tick_positions <- tick_positions[seq(1, length(tick_positions), length.out = num_ticks)]
}
tick_labels <- format(selected_dates[match(tick_positions, idx)], "%Y-%m-%d")
axis(1, at = tick_positions, labels = FALSE) 
text(x = tick_positions, y = par("usr")[3] - 0.025 * diff(par("usr")[3:4]), labels = tick_labels, srt = 45, adj = 1, xpd = TRUE, cex = 0.8)

dev.off()

# Function to plot with quantiles and dates on x-axis
plot_quantile_component <- function(q_d_50, q_d_05, q_d_95, q_d_20, q_d_35, q_d_65, q_d_80, Y, idx, component, num_ticks,figure_names) {
  png(figure_names, width = 6000, height = 4000, res = 600)
  
  par(mar = c(4, 4, 2, 1) + 0.1)  # Ensure consistent margins in the function

  selected_dates <- dates_ts_usgs[idx]  # Retrieve dates corresponding to the indices

  num_ticks <- 27
  tick_positions <- pretty(idx, num_ticks)  # Using pretty() to generate nice breakpoints

  if (length(tick_positions) > num_ticks) {
    tick_positions <- tick_positions[seq(1, length(tick_positions), length.out = num_ticks)]
  }
  
  tick_labels <- format(selected_dates[match(tick_positions, idx)], "%Y-%m-%d")


  if (component == 1)  {
    plot(idx, 1*Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(-2.5,2.5), 
        xlab = " ", ylab = "log-flow", main = "Trend Component  -  1991-2022", xaxt = "n")
  } else if (component == 2) {
    plot(idx, 1*Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(-2.5,2.5),
        xlab = " ", ylab = "log-flow", main = "Yearly Seasonal Effect  -  1991-2022", xaxt = "n")
  } else if (component == 4) {
    plot(idx, 1*Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(-2.5,2.5), 
        xlab = " ", ylab = "log-flow", main = "6-Month Sasonal Effect  -  1991-2022", xaxt = "n")
  } else if (component == 6) {
    plot(idx, 1*Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(-2.5,2.5), 
        xlab = " ", ylab = "log-flow", main = "80-Month Sasonal Effect  -  1991-2022", xaxt = "n")
  } else if (component == 8) {
    plot(idx, Y[2, idx]-Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(-1,1), 
        xlab = " ", ylab = "log-flow", main = "Discrepancy USGS-GloFAS  -  1991-2022", xaxt = "n")
  } else if (component == 9) {
    plot(idx, Y[3, idx]-Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(-1,1), 
        xlab = " ", ylab = "log-flow", main = "Discrepancy USGS-GloFAS -  1991-2022", xaxt = "n")
  } else if (component == 10) {
    plot(idx, 0*Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(-2.5,2.5), 
        xlab = " ", ylab = "log-flow", main = "Discrepancy USGS-GloFAS  -  1991-2022", xaxt = "n")
  } else if (component == 11) {
   plot(idx, 0*Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(-0, 0.1), 
        xlab = " ", ylab = "log-flow", main = "Discrepancy USGS-GloFAS - 1991-2022", xaxt = "n")
  } else if (component == 12) {
    plot(idx, 0*Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(-0.04,0.0), 
        xlab = " ", ylab = "log-flow", main = "Discrepancy USGS-GloFAS  -  1991-2022", xaxt = "n")
  } else if (component == 13) {
    plot(idx, 0*Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(-0.05,0.05), 
        xlab = " ", ylab = "log-flow", main = "Discrepancy USGS-GloFAS -  1991-2022", xaxt = "n")
 } else if (component == 14) {
    plot(idx, 0*Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(-0.05,0.05), 
        xlab = " ", ylab = "log-flow", main = "Discrepancy USGS-GloFAS  -  1991-2022", xaxt = "n")
  } else if (component == 15) {
    plot(idx, 0*Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(-0.08,0.05), 
        xlab = " ", ylab = "log-flow", main = "Discrepancy USGS-NWS  -  1991-2022", xaxt = "n")
  } else if (component == 16) {
    plot(idx, 0*Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(-0.055,0.055), 
        xlab = " ", ylab = "log-flow", main = "Discrepancy USGS-NWS -  1991-2022", xaxt = "n")
  } else if (component == 17) {
   plot(idx, 0*Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(-0, 0.1), 
        xlab = " ", ylab = "log-flow", main = "Discrepancy USGS-NWS  -  1991-2022", xaxt = "n")
  } else if (component == 18) {
    plot(idx, 0*Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(-0.04,0.0), 
        xlab = " ", ylab = "log-flow", main = "Discrepancy USGS-NWS -  1991-2022", xaxt = "n")
  } else if (component == 19) {
    plot(idx, 0*Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(-0.05,0.05), 
        xlab = " ", ylab = "log-flow", main = "Discrepancy USGS-NWS -  1991-2022", xaxt = "n")
 } else if (component == 20) {
    plot(idx, 0*Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(-0.05,0.05), 
        xlab = " ", ylab = "log-flow", main = "Discrepancy USGS-NWS  -  1991-2022", xaxt = "n")
  } else if (component == 21) {
    plot(idx, 0*Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(-0.08,0.05), 
        xlab = " ", ylab = "log-flow", main = "Discrepancy USGS-NWS -  1991-2022", xaxt = "n")
  } else if (component == 22) {
    plot(idx, 0*Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(-2,2), 
        xlab = " ", ylab = "log-flow", main = "Cummulative Transfer   -  1991-2022", xaxt = "n")
  } else if (component == 23) {
    plot(idx, 0*Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(0,0.04), 
        xlab = " ", ylab = "log-flow", main = "PPT   -  1991-2022", xaxt = "n")
  } else if (component == 24) {
    plot(idx, 0*Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(-0.01,0.01), 
        xlab = " ", ylab = "log-flow", main = "Soil Misture   -  1991-2022", xaxt = "n")
  } else if (component == 25) {
    plot(idx, 0*Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(0,0.001), 
        xlab = " ", ylab = "log-flow", main = "GPCA Component -  1991-2022", xaxt = "n")
  } else {
    plot(idx, 0*Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(-0.04,0), 
        xlab = " ", ylab = "log-flow", main = "Const   -  1991-2022", xaxt = "n")
  
  } 


  lines(idx, q_d_50[component, idx, 2], col = "forestgreen", lwd = 1)
  lines(idx, q_d_50[component, idx, 1], col = "green", lwd = 0.5, lty = 2)
  lines(idx, q_d_50[component, idx, 3], col = "green", lwd = 0.5, lty = 2)

  lines(idx, q_d_05[component, idx, 2], col = "darkred", lwd = 1)
  lines(idx, q_d_05[component, idx, 1], col = "red", lwd = 0.5, lty = 2)
  lines(idx, q_d_05[component, idx, 3], col = "red", lwd = 0.5, lty = 2)

  lines(idx, q_d_95[component, idx, 2], col = "darkblue", lwd = 1)
  lines(idx, q_d_95[component, idx, 1], col = "blue", lwd = 0.5, lty = 2)
  lines(idx, q_d_95[component, idx, 3], col = "blue", lwd = 0.5, lty = 2)

  abline(h=0, col='black')

  axis(1, at = tick_positions, labels = FALSE) 
  text(x = tick_positions, y = par("usr")[3] - 0.05 * diff(par("usr")[3:4]),
       labels = tick_labels, srt = 45, adj = 1, xpd = TRUE, cex = 0.8)

  mtext("Forest Green: 50th Quantile | Dark Red: 5th Quantile | Dark Blue: 95th Quantile | Orange: Average", side = 1, outer = TRUE, line = 2, cex = 0.8)
  
  dev.off() 
}

par(mfrow = c(1, 1), mar = c(4, 4, 2, 1), oma = c(4, 0, 0, 0))

idx <- ceiling(TT/10):TT
components <- c(1:dim(q_d_50)[1])
figure_names <- paste0("/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics_reproduce/Component_1991_2022_", 1:length(components), ".png")

for (i in 1:length(components)) {
  par(mar = c(4, 4, 2, 1) + 0.1)  
  plot_quantile_component(q_d_50, q_d_05, q_d_95, 
                        q_d_20, q_d_35, q_d_65, q_d_80,
                        Y, idx, 
                        components[i], num_ticks = 8,figure_names[i])
}

par(mfrow = c(1, 1), mar = c(5, 4, 4, 2) + 0.1, oma = c(0, 0, 0, 0))


num_ticks <- 8
idx <- ceiling(TT/10):TT
figure_names <- paste0("/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics_reproduce/Agg_disc_1991_2022_", 1:J, ".png")

for(j in 1:J){
png(figure_names[j], width = 6000, height = 4000, res = 600)  
par(mar = c(4, 4, 2, 1) + 0.1)  # Ensure consistent margins in the function

selected_dates <- dates_ts_usgs[idx]  # Retrieve dates corresponding to the indices
num_ticks <- 27
tick_positions <- pretty(idx, num_ticks)  # Using pretty() to generate nice breakpoints

if (length(tick_positions) > num_ticks) {
tick_positions <- tick_positions[seq(1, length(tick_positions), length.out = num_ticks)]
}
tick_labels <- format(selected_dates[match(tick_positions, idx)], "%Y-%m-%d")

if(j == 1){
plot(idx, Y[2, idx]-Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(-1,1), 
xlab = " ", ylab = "log-flow", main = "Discrepancy USGS-GloFAS  -  1991-2022", xaxt = "n")
lines(idx, q_d_discrep1_quantiles[4,idx,2], col = 'forestgreen', lwd = 1)
lines(idx, q_d_discrep1_quantiles[4,idx,1], col = 'green', lwd = 1, lty = 2)
lines(idx, q_d_discrep1_quantiles[4,idx,3], col = 'green', lwd = 1, lty = 2)
lines(idx, q_d_discrep1_quantiles[1,idx,2], col = 'darkblue', lwd = 1)
lines(idx, q_d_discrep1_quantiles[1,idx,1], col = 'lightblue', lwd = 1, lty = 2)
lines(idx, q_d_discrep1_quantiles[1,idx,3], col = 'lightblue', lwd = 1, lty = 2)
lines(idx, q_d_discrep1_quantiles[7,idx,2], col = 'darkred', lwd = 1)
lines(idx, q_d_discrep1_quantiles[7,idx,1], col = 'pink', lwd = 1, lty = 2)
lines(idx, q_d_discrep1_quantiles[7,idx,3], col = 'pink', lwd = 1, lty = 2)
}else{
plot(idx, Y[3, idx]-Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(-1,1), 
xlab = " ", ylab = "log-flow", main = "Discrepancy USGS-GloFAS  -  1991-2022", xaxt = "n")
lines(idx, q_d_discrep2_quantiles[4,idx,2], col = 'forestgreen', lwd = 1)
lines(idx, q_d_discrep2_quantiles[4,idx,1], col = 'green', lwd = 1, lty = 2)
lines(idx, q_d_discrep2_quantiles[4,idx,3], col = 'green', lwd = 1, lty = 2)
lines(idx, q_d_discrep2_quantiles[1,idx,2], col = 'darkblue', lwd = 1)
lines(idx, q_d_discrep2_quantiles[1,idx,1], col = 'lightblue', lwd = 1, lty = 2)
lines(idx, q_d_discrep2_quantiles[1,idx,3], col = 'lightblue', lwd = 1, lty = 2)
lines(idx, q_d_discrep2_quantiles[7,idx,2], col = 'darkred', lwd = 1)
lines(idx, q_d_discrep2_quantiles[7,idx,1], col = 'pink', lwd = 1, lty = 2)
lines(idx, q_d_discrep2_quantiles[7,idx,3], col = 'pink', lwd = 1, lty = 2)
}

abline(h=0, col='black')

axis(1, at = tick_positions, labels = FALSE) 
text(x = tick_positions, y = par("usr")[3] - 0.05 * diff(par("usr")[3:4]),
    labels = tick_labels, srt = 45, adj = 1, xpd = TRUE, cex = 0.8)

mtext("Forest Green: 50th Quantile | Dark Red: 5th Quantile | Dark Blue: 95th Quantile | Orange: Average", side = 1, outer = TRUE, line = 2, cex = 0.8)
dev.off() 
}


# Function to plot with quantiles and dates on x-axis
plot_quantile_component <- function(q_d_50, q_d_05, q_d_95, q_d_20, q_d_35, q_d_65, q_d_80, Y, idx, component, num_ticks) {
  par(mar = c(4, 4, 2, 1) + 0.1)  # Ensure consistent margins in the function
  
  selected_dates <- dates_ts_usgs[idx]  # Retrieve dates corresponding to the indices

  num_ticks <- 27
  tick_positions <- pretty(idx, num_ticks)  # Using pretty() to generate nice breakpoints

  if (length(tick_positions) > num_ticks) {
    tick_positions <- tick_positions[seq(1, length(tick_positions), length.out = num_ticks)]
  }
  
  tick_labels <- format(selected_dates[match(tick_positions, idx)], "%Y-%m-%d")

     png("/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics_reproduce/Component_1991_2022_TRANSFER50_DISC.png", width = 6000, height = 4000, res = 600)
  
  plot(idx, 0*Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(-2,2), 
       xlab = " ", ylab = "log-flow", main = "Cummulative Transfer  -  1991-2022", xaxt = "n")
  lines(idx, q_d_50[component, idx, 2], col = "forestgreen", lwd = 1)
  lines(idx, q_d_50[component, idx, 1], col = "lightgreen", lwd = 0.5, lty = 2)
  lines(idx, q_d_50[component, idx, 3], col = "lightgreen", lwd = 0.5, lty = 2)
  abline(h=0, col='black')
  axis(1, at = tick_positions, labels = FALSE) 
  text(x = tick_positions, y = par("usr")[3] - 0.025 * diff(par("usr")[3:4]),
       labels = tick_labels, srt = 45, adj = 1, xpd = TRUE, cex = 0.8)
  mtext("Forest Green: 50th Quantile | Dark Red: 5th Quantile | Dark Blue: 95th Quantile", side = 1, outer = TRUE, line = 2, cex = 0.8)
  
  dev.off() 

   png("/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics_reproduce/Component_1991_2022_TRANSFER05_DISC.png", width = 6000, height = 4000, res = 600)
  plot(idx, 0*Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(-1.3,2.6), 
       xlab = " ", ylab = "log-flow", main = "Cummulative Transfer  -  1991-2022", xaxt = "n")
  lines(idx, q_d_05[component, idx, 2], col = "darkred", lwd = 1)
  lines(idx, q_d_05[component, idx, 1], col = "pink", lwd = 0.5, lty = 2)
  lines(idx, q_d_05[component, idx, 3], col = "pink", lwd = 0.5, lty = 2)
  abline(h=0, col='black')
  axis(1, at = tick_positions, labels = FALSE) 
  text(x = tick_positions, y = par("usr")[3] - 0.025 * diff(par("usr")[3:4]),
       labels = tick_labels, srt = 45, adj = 1, xpd = TRUE, cex = 0.8)
#   mtext("Forest Green: 50th Quantile | Dark Red: 5th Quantile | Dark Blue: 95th Quantile | Orange: Average", side = 1, outer = TRUE, line = 2, cex = 0.8)
  
  dev.off() 

png("/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics_reproduce/Component_1991_2022_TRANSFER95_DISC.png", width = 6000, height = 4000, res = 600)
  
  plot(idx, 0*Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(-1.3,2.6), 
       xlab = " ", ylab = "log-flow", main = "Cummulative Transfer  -  1991-2022", xaxt = "n")
  lines(idx, q_d_95[component, idx, 2], col = "darkblue", lwd = 1)
  lines(idx, q_d_95[component, idx, 1], col = "lightblue", lwd = 0.5, lty = 2)
  lines(idx, q_d_95[component, idx, 3], col = "lightblue", lwd = 0.5, lty = 2)
  abline(h=0, col='black')
  axis(1, at = tick_positions, labels = FALSE) 
  text(x = tick_positions, y = par("usr")[3] - 0.025 * diff(par("usr")[3:4]),
       labels = tick_labels, srt = 45, adj = 1, xpd = TRUE, cex = 0.8)
#   mtext("Forest Green: 50th Quantile | Dark Red: 5th Quantile | Dark Blue: 95th Quantile | Orange: Average", side = 1, outer = TRUE, line = 2, cex = 0.8)
  
  dev.off() 
}


  
# par(mfrow = c(1, 1), mar = c(4, 4, 2, 1), oma = c(4, 0, 0, 0))
par(mar = c(4, 4, 2, 1))

idx <- ceiling(TT/10):TT
trans_idx <- length(model$m0)-ppx+1
plot_quantile_component(q_d_50, q_d_05, q_d_95, 
                        q_d_20, q_d_35, q_d_65, q_d_80,
                        Y, idx, 
                        trans_idx, num_ticks = 8)



par(mfrow = c(1, 1), mar = c(5, 4, 4, 2) + 0.1, oma = c(0, 0, 0, 0))


# Function to plot with quantiles and dates on x-axis
plot_quantile_component <- function(q_d_50, q_d_05, q_d_95, q_d_20, q_d_35, q_d_65, q_d_80, Y, idx, component, num_ticks) {
  par(mar = c(4, 4, 2, 1) + 0.1)  # Ensure consistent margins in the function
  
  selected_dates <- dates_ts_usgs[idx]  # Retrieve dates corresponding to the indices

  num_ticks <- 35
  tick_positions <- pretty(idx, num_ticks)  # Using pretty() to generate nice breakpoints

  if (length(tick_positions) > num_ticks) {
    tick_positions <- tick_positions[seq(1, length(tick_positions), length.out = num_ticks)]
  }
  
  tick_labels <- format(selected_dates[match(tick_positions, idx)], "%Y-%m-%d")

     png("/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics_reproduce/Component_2012_2016_TRANSFER50_DISC.png", width = 6000, height = 4000, res = 600)
  
  plot(idx, 0*Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(-2,2), 
       xlab = " ", ylab = "log-flow", main = "Cummulative Transfer  -  1991-2022", xaxt = "n")
  lines(idx, q_d_50[component, idx, 2], col = "forestgreen", lwd = 1)
  lines(idx, q_d_50[component, idx, 1], col = "lightgreen", lwd = 0.5, lty = 2)
  lines(idx, q_d_50[component, idx, 3], col = "lightgreen", lwd = 0.5, lty = 2)
  abline(h=0, col='black')
  axis(1, at = tick_positions, labels = FALSE) 
  text(x = tick_positions, y = par("usr")[3] - 0.025 * diff(par("usr")[3:4]),
       labels = tick_labels, srt = 45, adj = 1, xpd = TRUE, cex = 0.8)
  mtext("Forest Green: 50th Quantile | Dark Red: 5th Quantile | Dark Blue: 95th Quantile", side = 1, outer = TRUE, line = 2, cex = 0.8)
  
  dev.off() 

     png("/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics_reproduce/Component_2012_2016_TRANSFER05_DISC.png", width = 6000, height = 4000, res = 600)
  
  plot(idx, 0*Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(-1.3,2.6), 
       xlab = " ", ylab = "log-flow", main = "Cummulative Transfer  -  1991-2022", xaxt = "n")
  lines(idx, q_d_05[component, idx, 2], col = "darkred", lwd = 1)
  lines(idx, q_d_05[component, idx, 1], col = "pink", lwd = 0.5, lty = 2)
  lines(idx, q_d_05[component, idx, 3], col = "pink", lwd = 0.5, lty = 2)
  abline(h=0, col='black')
  axis(1, at = tick_positions, labels = FALSE) 
  text(x = tick_positions, y = par("usr")[3] - 0.025 * diff(par("usr")[3:4]),
       labels = tick_labels, srt = 45, adj = 1, xpd = TRUE, cex = 0.8)
#   mtext("Forest Green: 50th Quantile | Dark Red: 5th Quantile | Dark Blue: 95th Quantile | Orange: Average", side = 1, outer = TRUE, line = 2, cex = 0.8)
  
  dev.off() 

     png("/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics_reproduce/Component_2012_2016_TRANSFER95_DISC.png", width = 6000, height = 4000, res = 600)
  
  plot(idx, 0*Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(-1.3,2.6), 
       xlab = " ", ylab = "log-flow", main = "Cummulative Transfer  -  1991-2022", xaxt = "n")
  lines(idx, q_d_95[component, idx, 2], col = "darkblue", lwd = 1)
  lines(idx, q_d_95[component, idx, 1], col = "lightblue", lwd = 0.5, lty = 2)
  lines(idx, q_d_95[component, idx, 3], col = "lightblue", lwd = 0.5, lty = 2)
  abline(h=0, col='black')
  axis(1, at = tick_positions, labels = FALSE) 
  text(x = tick_positions, y = par("usr")[3] - 0.025 * diff(par("usr")[3:4]),
       labels = tick_labels, srt = 45, adj = 1, xpd = TRUE, cex = 0.8)
#   mtext("Forest Green: 50th Quantile | Dark Red: 5th Quantile | Dark Blue: 95th Quantile | Orange: Average", side = 1, outer = TRUE, line = 2, cex = 0.8)
  
  dev.off() 
}

par(mar = c(4, 4, 2, 1))

# idx <- ceiling(TT/10):TT
idx <- time_cuts[1]:time_cuts[2]
trans_idx <- length(model$m0)-ppx+1
plot_quantile_component(q_d_50, q_d_05, q_d_95, 
                        q_d_20, q_d_35, q_d_65, q_d_80,
                        Y, idx, 
                        trans_idx, num_ticks = 11)



par(mfrow = c(1, 1), mar = c(5, 4, 4, 2) + 0.1, oma = c(0, 0, 0, 0))


# Function to plot with quantiles and dates on x-axis
plot_quantile_component <- function(q_d_50, q_d_05, q_d_95, q_d_20, q_d_35, q_d_65, q_d_80, Y, idx, component, num_ticks,figure_names) {
  png(figure_names[i], width = 6000, height = 4000, res = 600)
  
  par(mar = c(4, 4, 2, 1) + 0.1)  # Ensure consistent margins in the function
  
  selected_dates <- dates_ts_usgs[idx]  # Retrieve dates corresponding to the indices

  tick_positions <- pretty(idx, num_ticks)  # Using pretty() to generate nice breakpoints

  if (length(tick_positions) > num_ticks) {
    tick_positions <- tick_positions[seq(1, length(tick_positions), length.out = num_ticks)]
  }
  
  tick_labels <- format(selected_dates[match(tick_positions, idx)], "%Y-%m-%d")



  if (component == 1)  {
    plot(idx, 1*Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(-2.5,2.5), 
        xlab = " ", ylab = "log-flow", main = "Trend Component  -  2012-2016", xaxt = "n")
  } else if (component == 2) {
    plot(idx, 1*Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(-2.5,2.5),
        xlab = " ", ylab = "log-flow", main = "Yearly Seasonal Effect  -  2012-2016", xaxt = "n")
  } else if (component == 4) {
    plot(idx, 1*Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(-2.5,2.5), 
        xlab = " ", ylab = "log-flow", main = "6-Month Sasonal Effect  -  2012-2016", xaxt = "n")
  } else if (component == 6) {
    plot(idx, 1*Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(-2.5,2.5), 
        xlab = " ", ylab = "log-flow", main = "80-Month Sasonal Effect  -  2012-2016", xaxt = "n")
  } else if (component == 8) {
    plot(idx, Y[2, idx]-Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(-1,1), 
        xlab = " ", ylab = "log-flow", main = "Discrepancy USGS-GloFAS  -  2012-2016", xaxt = "n")
  } else if (component == 9) {
    plot(idx, Y[3, idx]-Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(-1,1), 
        xlab = " ", ylab = "log-flow", main = "Discrepancy USGS-GloFAS -  2012-2016", xaxt = "n")
  } else if (component == 10) {
    plot(idx, 0*Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(-2.5,2.5), 
        xlab = " ", ylab = "log-flow", main = "Discrepancy USGS-GloFAS  -  2012-2016", xaxt = "n")
  } else if (component == 11) {
   plot(idx, 0*Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(-0, 0.1), 
        xlab = " ", ylab = "log-flow", main = "Discrepancy USGS-GloFAS - 2012-2016", xaxt = "n")
  } else if (component == 12) {
    plot(idx, 0*Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(-0.04,0.0), 
        xlab = " ", ylab = "log-flow", main = "Discrepancy USGS-GloFAS  -  2012-2016", xaxt = "n")
  } else if (component == 13) {
    plot(idx, 0*Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(-0.05,0.05), 
        xlab = " ", ylab = "log-flow", main = "Discrepancy USGS-GloFAS -  2012-2016", xaxt = "n")
 } else if (component == 14) {
    plot(idx, 0*Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(-0.05,0.05), 
        xlab = " ", ylab = "log-flow", main = "Discrepancy USGS-GloFAS  -  2012-2016", xaxt = "n")
  } else if (component == 15) {
    plot(idx, 0*Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(-0.08,0.05), 
        xlab = " ", ylab = "log-flow", main = "Discrepancy USGS-NWS  -  2012-2016", xaxt = "n")
  } else if (component == 16) {
    plot(idx, 0*Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(-0.055,0.055), 
        xlab = " ", ylab = "log-flow", main = "Discrepancy USGS-NWS -  2012-2016", xaxt = "n")
  } else if (component == 17) {
   plot(idx, 0*Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(-0, 0.1), 
        xlab = " ", ylab = "log-flow", main = "Discrepancy USGS-NWS  -  2012-2016", xaxt = "n")
  } else if (component == 18) {
    plot(idx, 0*Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(-0.04,0.0), 
        xlab = " ", ylab = "log-flow", main = "Discrepancy USGS-NWS -  2012-2016", xaxt = "n")
  } else if (component == 19) {
    plot(idx, 0*Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(-0.05,0.05), 
        xlab = " ", ylab = "log-flow", main = "Discrepancy USGS-NWS -  2012-2016", xaxt = "n")
 } else if (component == 20) {
    plot(idx, 0*Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(-0.05,0.05), 
        xlab = " ", ylab = "log-flow", main = "Discrepancy USGS-NWS  -  2012-2016", xaxt = "n")
  } else if (component == 21) {
    plot(idx, 0*Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(-0.08,0.05), 
        xlab = " ", ylab = "log-flow", main = "Discrepancy USGS-NWS -  2012-2016", xaxt = "n")
  } else if (component == 22) {
    plot(idx, 0*Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(-1,1), 
        xlab = " ", ylab = "log-flow", main = "Cummulative Transfer   -  2012-2016", xaxt = "n")
  } else if (component == 23) {
    plot(idx, 0*Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(0,0.04), 
        xlab = " ", ylab = "log-flow", main = "PPT   -  2012-2016", xaxt = "n")
  } else if (component == 24) {
    plot(idx, 0*Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(-0.01,0.01), 
        xlab = " ", ylab = "log-flow", main = "Soil Misture   -  2012-2016", xaxt = "n")
  } else if (component == 25) {
    plot(idx, 0*Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(0,0.001), 
        xlab = " ", ylab = "log-flow", main = "GPCA Component -  2012-2016", xaxt = "n")
  } else {
    plot(idx, 0*Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(-0.04,0), 
        xlab = " ", ylab = "log-flow", main = "Const   -  2012-2016", xaxt = "n")
  } 


  

  lines(idx, q_d_50[component, idx, 2], col = "forestgreen", lwd = 1)
  lines(idx, q_d_50[component, idx, 1], col = "green", lwd = 0.5, lty = 2)
  lines(idx, q_d_50[component, idx, 3], col = "green", lwd = 0.5, lty = 2)

  lines(idx, q_d_05[component, idx, 2], col = "darkred", lwd = 1)
  lines(idx, q_d_05[component, idx, 1], col = "red", lwd = 0.5, lty = 2)
  lines(idx, q_d_05[component, idx, 3], col = "red", lwd = 0.5, lty = 2)

  lines(idx, q_d_95[component, idx, 2], col = "darkblue", lwd = 1)
  lines(idx, q_d_95[component, idx, 1], col = "blue", lwd = 0.5, lty = 2)
  lines(idx, q_d_95[component, idx, 3], col = "blue", lwd = 0.5, lty = 2)
  # lines(idx, q_d_NDLM[component, idx, 2], col = "darkorange", lwd = 1)
  # lines(idx, q_d_NDLM[component, idx, 1], col = "orange", lwd = 0.5, lty = 2)
  # lines(idx, q_d_NDLM[component, idx, 3], col = "orange", lwd = 0.5, lty = 2)


  # # Retained additional lines for future use
  # lines(idx, q_d_20[component, idx, 2], col = "gold", lwd = 1)
  # lines(idx, q_d_20[component, idx, 1], col = "gold", lwd = 0.5, lty = 2)
  # lines(idx, q_d_20[component, idx, 3], col = "gold", lwd = 0.5, lty = 2)

  # lines(idx, q_d_35[component, idx, 2], col = "purple", lwd = 1)
  # lines(idx, q_d_35[component, idx, 1], col = "purple", lwd = 0.5, lty = 2)
  # lines(idx, q_d_35[component, idx, 3], col = "purple", lwd = 0.5, lty = 2)
  
  # lines(idx, q_d_65[component, idx, 2], col = "brown", lwd = 1)
  # lines(idx, q_d_65[component, idx, 1], col = "brown", lwd = 0.5, lty = 2)
  # lines(idx, q_d_65[component, idx, 3], col = "brown", lwd = 0.5, lty = 2)

  # lines(idx, q_d_80[component, idx, 2], col = "orange", lwd = 1)
  # lines(idx, q_d_80[component, idx, 1], col = "orange", lwd = 0.5, lty = 2)
  # lines(idx, q_d_80[component, idx, 3], col = "orange", lwd = 0.5, lty = 2)

  abline(h=0, col='black')

  axis(1, at = tick_positions, labels = FALSE) 
  text(x = tick_positions, y = par("usr")[3] - 0.05 * diff(par("usr")[3:4]),
       labels = tick_labels, srt = 45, adj = 1, xpd = TRUE, cex = 0.8)

  mtext("Forest Green: 50th Quantile | Dark Red: 5th Quantile | Dark Blue: 95th Quantile | Orange: Average", side = 1, outer = TRUE, line = 2, cex = 0.8)
  dev.off() 
}

par(mfrow = c(1, 1), mar = c(4, 4, 2, 1), oma = c(4, 0, 0, 0))

# idx <- ceiling(TT/10):TT
idx <- time_cuts[1]:time_cuts[2]
components <- c(1, 2, 4, 6, 8, 9:dim(q_d_50)[1])
figure_names <- paste0("/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics_reproduce/Component_2012_2016_", 1:length(components), "_DISC.png")
for (i in 1:length(components)) {
  par(mar = c(4, 4, 2, 1) + 0.1)  
  plot_quantile_component(q_d_50, q_d_05, q_d_95, 
                        q_d_20, q_d_35, q_d_65, q_d_80,
                        Y, idx, 
                        components[i], num_ticks = 35,figure_names)
}

par(mfrow = c(1, 1), mar = c(5, 4, 4, 2) + 0.1, oma = c(0, 0, 0, 0))


num_ticks <- 8
idx <- time_cuts[1]:time_cuts[2]
figure_names <- paste0("/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics_reproduce/Agg_disc_2012_2016_", 1:J, ".png")

for(j in 1:J){
png(figure_names[j], width = 6000, height = 4000, res = 600)  
par(mar = c(4, 4, 2, 1) + 0.1)  # Ensure consistent margins in the function

selected_dates <- dates_ts_usgs[idx]  # Retrieve dates corresponding to the indices
num_ticks <- 27
tick_positions <- pretty(idx, num_ticks)  # Using pretty() to generate nice breakpoints

if (length(tick_positions) > num_ticks) {
tick_positions <- tick_positions[seq(1, length(tick_positions), length.out = num_ticks)]
}
tick_labels <- format(selected_dates[match(tick_positions, idx)], "%Y-%m-%d")

if(j == 1){
plot(idx, Y[2, idx]-Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(-1,1), 
xlab = " ", ylab = "log-flow", main = "Discrepancy USGS-GloFAS  -  1991-2022", xaxt = "n")
lines(idx, q_d_discrep1_quantiles[4,idx,2], col = 'forestgreen', lwd = 1)
lines(idx, q_d_discrep1_quantiles[4,idx,1], col = 'green', lwd = 1, lty = 2)
lines(idx, q_d_discrep1_quantiles[4,idx,3], col = 'green', lwd = 1, lty = 2)
lines(idx, q_d_discrep1_quantiles[1,idx,2], col = 'darkblue', lwd = 1)
lines(idx, q_d_discrep1_quantiles[1,idx,1], col = 'lightblue', lwd = 1, lty = 2)
lines(idx, q_d_discrep1_quantiles[1,idx,3], col = 'lightblue', lwd = 1, lty = 2)
lines(idx, q_d_discrep1_quantiles[7,idx,2], col = 'darkred', lwd = 1)
lines(idx, q_d_discrep1_quantiles[7,idx,1], col = 'pink', lwd = 1, lty = 2)
lines(idx, q_d_discrep1_quantiles[7,idx,3], col = 'pink', lwd = 1, lty = 2)
}else{
plot(idx, Y[3, idx]-Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(-1,1), 
xlab = " ", ylab = "log-flow", main = "Discrepancy USGS-GloFAS  -  1991-2022", xaxt = "n")
lines(idx, q_d_discrep2_quantiles[4,idx,2], col = 'forestgreen', lwd = 1)
lines(idx, q_d_discrep2_quantiles[4,idx,1], col = 'green', lwd = 1, lty = 2)
lines(idx, q_d_discrep2_quantiles[4,idx,3], col = 'green', lwd = 1, lty = 2)
lines(idx, q_d_discrep2_quantiles[1,idx,2], col = 'darkblue', lwd = 1)
lines(idx, q_d_discrep2_quantiles[1,idx,1], col = 'lightblue', lwd = 1, lty = 2)
lines(idx, q_d_discrep2_quantiles[1,idx,3], col = 'lightblue', lwd = 1, lty = 2)
lines(idx, q_d_discrep2_quantiles[7,idx,2], col = 'darkred', lwd = 1)
lines(idx, q_d_discrep2_quantiles[7,idx,1], col = 'pink', lwd = 1, lty = 2)
lines(idx, q_d_discrep2_quantiles[7,idx,3], col = 'pink', lwd = 1, lty = 2)
}

abline(h=0, col='black')

axis(1, at = tick_positions, labels = FALSE) 
text(x = tick_positions, y = par("usr")[3] - 0.05 * diff(par("usr")[3:4]),
    labels = tick_labels, srt = 45, adj = 1, xpd = TRUE, cex = 0.8)

mtext("Forest Green: 50th Quantile | Dark Red: 5th Quantile | Dark Blue: 95th Quantile | Orange: Average", side = 1, outer = TRUE, line = 2, cex = 0.8)
dev.off() 
}


# Function to plot with quantiles and dates on x-axis
plot_quantile_component <- function(q_d_50, q_d_05, q_d_95, q_d_20, q_d_35, q_d_65, q_d_80, Y, idx, component, num_ticks,figure_names) {
  png(figure_names[i], width = 6000, height = 4000, res = 600)
  
  par(mar = c(4, 4, 2, 1) + 0.1)  # Ensure consistent margins in the function

  
  selected_dates <- dates_ts_usgs[idx]  # Retrieve dates corresponding to the indices

  tick_positions <- pretty(idx, num_ticks)  # Using pretty() to generate nice breakpoints

  if (length(tick_positions) > num_ticks) {
    tick_positions <- tick_positions[seq(1, length(tick_positions), length.out = num_ticks)]
  }
  
  tick_labels <- format(selected_dates[match(tick_positions, idx)], "%Y-%m-%d")



  if (component == 1)  {
    plot(idx, 1*Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(-2.5,2.5), 
        xlab = " ", ylab = "log-flow", main = "Trend Component  -  2017-2019", xaxt = "n")
  } else if (component == 2) {
    plot(idx, 1*Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(-2.5,2.5),
        xlab = " ", ylab = "log-flow", main = "Yearly Seasonal Effect  -  2017-2019", xaxt = "n")
  } else if (component == 4) {
    plot(idx, 1*Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(-2.5,2.5), 
        xlab = " ", ylab = "log-flow", main = "6-Month Sasonal Effect  -  2017-2019", xaxt = "n")
  } else if (component == 6) {
    plot(idx, 1*Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(-2.5,2.5), 
        xlab = " ", ylab = "log-flow", main = "80-Month Sasonal Effect  -  2017-2019", xaxt = "n")
  } else if (component == 8) {
    plot(idx, Y[2, idx]-Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(-1,1), 
        xlab = " ", ylab = "log-flow", main = "Discrepancy USGS-GloFAS  -  2017-2019", xaxt = "n")
  } else if (component == 9) {
    plot(idx, Y[3, idx]-Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(-1,1), 
        xlab = " ", ylab = "log-flow", main = "Discrepancy USGS-GloFAS -  2017-2019", xaxt = "n")
  } else if (component == 10) {
    plot(idx, 0*Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(-2.5,2.5), 
        xlab = " ", ylab = "log-flow", main = "Discrepancy USGS-GloFAS  -  2017-2019", xaxt = "n")
  } else if (component == 11) {
   plot(idx, 0*Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(-0, 0.1), 
        xlab = " ", ylab = "log-flow", main = "Discrepancy USGS-GloFAS -  1991-2022", xaxt = "n")
  } else if (component == 12) {
    plot(idx, 0*Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(-0.04,0.0), 
        xlab = " ", ylab = "log-flow", main = "Discrepancy USGS-GloFAS  -  2017-2019", xaxt = "n")
  } else if (component == 13) {
    plot(idx, 0*Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(-0.05,0.05), 
        xlab = " ", ylab = "log-flow", main = "Discrepancy USGS-GloFAS -  2017-2019", xaxt = "n")
 } else if (component == 14) {
    plot(idx, 0*Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(-0.05,0.05), 
        xlab = " ", ylab = "log-flow", main = "Discrepancy USGS-GloFAS  -  2017-2019", xaxt = "n")
  } else if (component == 15) {
    plot(idx, 0*Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(-0.08,0.05), 
        xlab = " ", ylab = "log-flow", main = "Discrepancy USGS-NWS  -  2017-2019", xaxt = "n")
  } else if (component == 16) {
    plot(idx, 0*Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(-0.055,0.055), 
        xlab = " ", ylab = "log-flow", main = "Discrepancy USGS-NWS -  2017-2019", xaxt = "n")
  } else if (component == 17) {
   plot(idx, 0*Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(-0, 0.1), 
        xlab = " ", ylab = "log-flow", main = "Discrepancy USGS-NWS  -  2017-2019", xaxt = "n")
  } else if (component == 18) {
    plot(idx, 0*Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(-0.04,0.0), 
        xlab = " ", ylab = "log-flow", main = "Discrepancy USGS-NWS -  2017-2019", xaxt = "n")
  } else if (component == 19) {
    plot(idx, 0*Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(-0.05,0.05), 
        xlab = " ", ylab = "log-flow", main = "Discrepancy USGS-NWS -  2017-2019", xaxt = "n")
 } else if (component == 20) {
    plot(idx, 0*Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(-0.05,0.05), 
        xlab = " ", ylab = "log-flow", main = "Discrepancy USGS-NWS  -  2017-2019", xaxt = "n")
  } else if (component == 21) {
    plot(idx, 0*Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(-0.08,0.05), 
        xlab = " ", ylab = "log-flow", main = "Discrepancy USGS-NWS -  2017-2019", xaxt = "n")
  } else if (component == 22) {
    plot(idx, 0*Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(-1,1), 
        xlab = " ", ylab = "log-flow", main = "Cummulative Transfer   -  2017-2019", xaxt = "n")
  } else if (component == 23) {
    plot(idx, 0*Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(0,0.04), 
        xlab = " ", ylab = "log-flow", main = "PPT   -  2017-2019", xaxt = "n")
  } else if (component == 24) {
    plot(idx, 0*Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(-0.01,0.01), 
        xlab = " ", ylab = "log-flow", main = "Soil Misture   -  2017-2019", xaxt = "n")
  } else if (component == 25) {
    plot(idx, 0*Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(0,0.001), 
        xlab = " ", ylab = "log-flow", main = "GPCA Component -  2017-2019", xaxt = "n")
  } else {
    plot(idx, 0*Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(-0.04,0), 
        xlab = " ", ylab = "log-flow", main = "Const   -  2017-2019", xaxt = "n")

  } 


  lines(idx, q_d_50[component, idx, 2], col = "forestgreen", lwd = 1)
  lines(idx, q_d_50[component, idx, 1], col = "green", lwd = 0.5, lty = 2)
  lines(idx, q_d_50[component, idx, 3], col = "green", lwd = 0.5, lty = 2)

  lines(idx, q_d_05[component, idx, 2], col = "darkred", lwd = 1)
  lines(idx, q_d_05[component, idx, 1], col = "red", lwd = 0.5, lty = 2)
  lines(idx, q_d_05[component, idx, 3], col = "red", lwd = 0.5, lty = 2)

  lines(idx, q_d_95[component, idx, 2], col = "darkblue", lwd = 1)
  lines(idx, q_d_95[component, idx, 1], col = "blue", lwd = 0.5, lty = 2)
  lines(idx, q_d_95[component, idx, 3], col = "blue", lwd = 0.5, lty = 2)

  # lines(idx, q_d_NDLM[component, idx, 2], col = "darkorange", lwd = 1)
  # lines(idx, q_d_NDLM[component, idx, 1], col = "orange", lwd = 0.5, lty = 2)
  # lines(idx, q_d_NDLM[component, idx, 3], col = "orange", lwd = 0.5, lty = 2)


  # # Retained additional lines for future use
  # lines(idx, q_d_20[component, idx, 2], col = "gold", lwd = 1)
  # lines(idx, q_d_20[component, idx, 1], col = "gold", lwd = 0.5, lty = 2)
  # lines(idx, q_d_20[component, idx, 3], col = "gold", lwd = 0.5, lty = 2)

  # lines(idx, q_d_35[component, idx, 2], col = "purple", lwd = 1)
  # lines(idx, q_d_35[component, idx, 1], col = "purple", lwd = 0.5, lty = 2)
  # lines(idx, q_d_35[component, idx, 3], col = "purple", lwd = 0.5, lty = 2)
  
  # lines(idx, q_d_65[component, idx, 2], col = "brown", lwd = 1)
  # lines(idx, q_d_65[component, idx, 1], col = "brown", lwd = 0.5, lty = 2)
  # lines(idx, q_d_65[component, idx, 3], col = "brown", lwd = 0.5, lty = 2)

  # lines(idx, q_d_80[component, idx, 2], col = "orange", lwd = 1)
  # lines(idx, q_d_80[component, idx, 1], col = "orange", lwd = 0.5, lty = 2)
  # lines(idx, q_d_80[component, idx, 3], col = "orange", lwd = 0.5, lty = 2)

  abline(h=0, col='black')

  axis(1, at = tick_positions, labels = FALSE) 
  text(x = tick_positions, y = par("usr")[3] - 0.05 * diff(par("usr")[3:4]),
       labels = tick_labels, srt = 45, adj = 1, xpd = TRUE, cex = 0.8)

  mtext("Forest Green: 50th Quantile | Dark Red: 5th Quantile | Dark Blue: 95th Quantile | Orange: Average", side = 1, outer = TRUE, line = 2, cex = 0.8)
  
  dev.off() 
}

par(mfrow = c(1, 1), mar = c(4, 4, 2, 1), oma = c(4, 0, 0, 0))

# idx <- ceiling(TT/10):TT
idx <- time_cuts[3]:time_cuts[4]
components <- c(1:dim(q_d_50)[1])
figure_names <- paste0("/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics_reproduce/Component_2018_2020_", 1:length(components), "_DISC.png")
for (i in 1:length(components)) {
  par(mar = c(4, 4, 2, 1) + 0.1)  
  plot_quantile_component(q_d_50, q_d_05, q_d_95, 
                        q_d_20, q_d_35, q_d_65, q_d_80,
                        Y, idx, 
                        components[i], num_ticks = 25,figure_names)
}

par(mfrow = c(1, 1), mar = c(5, 4, 4, 2) + 0.1, oma = c(0, 0, 0, 0))


num_ticks <- 8
idx <- time_cuts[3]:time_cuts[4]
figure_names <- paste0("/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics_reproduce/Agg_disc_2018_2020_", 1:J, ".png")

for(j in 1:J){
png(figure_names[j], width = 6000, height = 4000, res = 600)  
par(mar = c(4, 4, 2, 1) + 0.1)  # Ensure consistent margins in the function

selected_dates <- dates_ts_usgs[idx]  # Retrieve dates corresponding to the indices
num_ticks <- 27
tick_positions <- pretty(idx, num_ticks)  # Using pretty() to generate nice breakpoints

if (length(tick_positions) > num_ticks) {
tick_positions <- tick_positions[seq(1, length(tick_positions), length.out = num_ticks)]
}
tick_labels <- format(selected_dates[match(tick_positions, idx)], "%Y-%m-%d")

if(j == 1){
plot(idx, Y[2, idx]-Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(-1,1), 
xlab = " ", ylab = "log-flow", main = "Discrepancy USGS-GloFAS  -  1991-2022", xaxt = "n")
lines(idx, q_d_discrep1_quantiles[4,idx,2], col = 'forestgreen', lwd = 1)
lines(idx, q_d_discrep1_quantiles[4,idx,1], col = 'green', lwd = 1, lty = 2)
lines(idx, q_d_discrep1_quantiles[4,idx,3], col = 'green', lwd = 1, lty = 2)
lines(idx, q_d_discrep1_quantiles[1,idx,2], col = 'darkblue', lwd = 1)
lines(idx, q_d_discrep1_quantiles[1,idx,1], col = 'lightblue', lwd = 1, lty = 2)
lines(idx, q_d_discrep1_quantiles[1,idx,3], col = 'lightblue', lwd = 1, lty = 2)
lines(idx, q_d_discrep1_quantiles[7,idx,2], col = 'darkred', lwd = 1)
lines(idx, q_d_discrep1_quantiles[7,idx,1], col = 'pink', lwd = 1, lty = 2)
lines(idx, q_d_discrep1_quantiles[7,idx,3], col = 'pink', lwd = 1, lty = 2)
}else{
plot(idx, Y[3, idx]-Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(-1,1), 
xlab = " ", ylab = "log-flow", main = "Discrepancy USGS-GloFAS  -  1991-2022", xaxt = "n")
lines(idx, q_d_discrep2_quantiles[4,idx,2], col = 'forestgreen', lwd = 1)
lines(idx, q_d_discrep2_quantiles[4,idx,1], col = 'green', lwd = 1, lty = 2)
lines(idx, q_d_discrep2_quantiles[4,idx,3], col = 'green', lwd = 1, lty = 2)
lines(idx, q_d_discrep2_quantiles[1,idx,2], col = 'darkblue', lwd = 1)
lines(idx, q_d_discrep2_quantiles[1,idx,1], col = 'lightblue', lwd = 1, lty = 2)
lines(idx, q_d_discrep2_quantiles[1,idx,3], col = 'lightblue', lwd = 1, lty = 2)
lines(idx, q_d_discrep2_quantiles[7,idx,2], col = 'darkred', lwd = 1)
lines(idx, q_d_discrep2_quantiles[7,idx,1], col = 'pink', lwd = 1, lty = 2)
lines(idx, q_d_discrep2_quantiles[7,idx,3], col = 'pink', lwd = 1, lty = 2)
}

abline(h=0, col='black')

axis(1, at = tick_positions, labels = FALSE) 
text(x = tick_positions, y = par("usr")[3] - 0.05 * diff(par("usr")[3:4]),
    labels = tick_labels, srt = 45, adj = 1, xpd = TRUE, cex = 0.8)

mtext("Forest Green: 50th Quantile | Dark Red: 5th Quantile | Dark Blue: 95th Quantile | Orange: Average", side = 1, outer = TRUE, line = 2, cex = 0.8)
dev.off() 
}


# Function to plot with quantiles and dates on x-axis
plot_quantile_component <- function(q_d_50, q_d_05, q_d_95, q_d_20, q_d_35, q_d_65, q_d_80, Y, idx, component, num_ticks) {
  par(mar = c(4, 4, 2, 1) + 0.1)  # Ensure consistent margins in the function
  
  selected_dates <- dates_ts_usgs[idx]  # Retrieve dates corresponding to the indices

  num_ticks <- 25
  tick_positions <- pretty(idx, num_ticks)  # Using pretty() to generate nice breakpoints

  if (length(tick_positions) > num_ticks) {
    tick_positions <- tick_positions[seq(1, length(tick_positions), length.out = num_ticks)]
  }
  
  tick_labels <- format(selected_dates[match(tick_positions, idx)], "%Y-%m-%d")
     png("/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics_reproduce/Component_2017_2019_TRANSFER50_DISC.png", width = 6000, height = 4000, res = 600)
  
  plot(idx, 0*Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(-2,2), 
       xlab = " ", ylab = "log-flow", main = "Cummulative Transfer  -  1991-2022", xaxt = "n")
  lines(idx, q_d_50[component, idx, 2], col = "forestgreen", lwd = 1)
  lines(idx, q_d_50[component, idx, 1], col = "lightgreen", lwd = 0.5, lty = 2)
  lines(idx, q_d_50[component, idx, 3], col = "lightgreen", lwd = 0.5, lty = 2)
  abline(h=0, col='black')
  axis(1, at = tick_positions, labels = FALSE) 
  text(x = tick_positions, y = par("usr")[3] - 0.025 * diff(par("usr")[3:4]),
       labels = tick_labels, srt = 45, adj = 1, xpd = TRUE, cex = 0.8)
  mtext("Forest Green: 50th Quantile | Dark Red: 5th Quantile | Dark Blue: 95th Quantile", side = 1, outer = TRUE, line = 2, cex = 0.8)
  
  dev.off() 

     png("/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics_reproduce/Component_22017_2019_TRANSFER05_DISC.png", width = 6000, height = 4000, res = 600)
  
  plot(idx, 0*Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(-1.3,2.6), 
       xlab = " ", ylab = "log-flow", main = "Cummulative Transfer  -  1991-2022", xaxt = "n")
  lines(idx, q_d_05[component, idx, 2], col = "darkred", lwd = 1)
  lines(idx, q_d_05[component, idx, 1], col = "pink", lwd = 0.5, lty = 2)
  lines(idx, q_d_05[component, idx, 3], col = "pink", lwd = 0.5, lty = 2)
  abline(h=0, col='black')
  axis(1, at = tick_positions, labels = FALSE) 
  text(x = tick_positions, y = par("usr")[3] - 0.025 * diff(par("usr")[3:4]),
       labels = tick_labels, srt = 45, adj = 1, xpd = TRUE, cex = 0.8)
#   mtext("Forest Green: 50th Quantile | Dark Red: 5th Quantile | Dark Blue: 95th Quantile | Orange: Average", side = 1, outer = TRUE, line = 2, cex = 0.8)
  
  dev.off() 

     png("/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics_reproduce/Component_2017_2019_TRANSFER95_DISC.png", width = 6000, height = 4000, res = 600)
  
  plot(idx, 0*Y[1, idx], type = "l", col = "gray", lwd = 2, ylim=c(-1.3,2.6), 
       xlab = " ", ylab = "log-flow", main = "Cummulative Transfer  -  1991-2022", xaxt = "n")
  lines(idx, q_d_95[component, idx, 2], col = "darkblue", lwd = 1)
  lines(idx, q_d_95[component, idx, 1], col = "lightblue", lwd = 0.5, lty = 2)
  lines(idx, q_d_95[component, idx, 3], col = "lightblue", lwd = 0.5, lty = 2)
  abline(h=0, col='black')
  axis(1, at = tick_positions, labels = FALSE) 
  text(x = tick_positions, y = par("usr")[3] - 0.025 * diff(par("usr")[3:4]),
       labels = tick_labels, srt = 45, adj = 1, xpd = TRUE, cex = 0.8)
#   mtext("Forest Green: 50th Quantile | Dark Red: 5th Quantile | Dark Blue: 95th Quantile | Orange: Average", side = 1, outer = TRUE, line = 2, cex = 0.8)
  
  dev.off() 
}

par(mar = c(4, 4, 2, 1))

# idx <- ceiling(TT/10):TT
idx <- time_cuts[3]:time_cuts[4]
trans_idx <- length(model$m0)-ppx+1
plot_quantile_component(q_d_50, q_d_05, q_d_95, 
                        q_d_20, q_d_35, q_d_65, q_d_80,
                        Y, idx, 
                        trans_idx, num_ticks = 11)



par(mfrow = c(1, 1), mar = c(5, 4, 4, 2) + 0.1, oma = c(0, 0, 0, 0))


# Load necessary libraries

# Function to compute JSD for a given sample matrix
compute_jsd <- function(p_sample, gridsize = c(100, 100, 100)) {
  
  # Step 2: Perform KDE on the sample to estimate the density of p
  kde_p <- kde(p_sample, gridsize = gridsize)  # KDE estimation with custom grid size

  # Step 3: Define the grid and evaluate the KDE density
  pdf_p <- kde_p$estimate  # Estimated density of p on the grid
  dim_p <- dim(pdf_p)
  # cat("Dimensions of pdf_p:", dim_p, "\n")  # Print the dimensions of pdf_p

  # Step 4: Define the distribution q (standard multivariate normal)
  mean_q <- rep(0, 3)  # Mean vector of zeros for q
  cov_q <- diag(3)     # Identity matrix as covariance for q

  # Step 5: Evaluate the PDF for q on the same grid as kde_p
  grid_points <- kde_p$eval.points  # Grid points used in kde_p

  # Create a matrix of all grid points where the densities are evaluated.
  # Avoid expand.grid() here: it builds a 1e6-row data.frame for gridsize=c(100,100,100),
  # which is slower and allocates more than necessary. Keep row order identical to expand.grid:
  # Var1 varies fastest, then Var2, then Var3.
  x1 <- grid_points[[1]]
  x2 <- grid_points[[2]]
  x3 <- grid_points[[3]]
  grid_matrix <- cbind(
    rep(x1, times = length(x2) * length(x3)),
    rep(rep(x2, each = length(x1)), times = length(x3)),
    rep(x3, each = length(x1) * length(x2))
  )

  # Calculate the density for the standard normal on the same grid
  pdf_q <- dmvnorm(grid_matrix, mean = mean_q, sigma = cov_q)
  pdf_q <- array(pdf_q, dim = dim_p)  # Reshape to match the dimension of pdf_p
  # cat("Dimensions of pdf_q:", dim(pdf_q), "\n")  # Print the dimensions of pdf_q

  # Step 6: Normalize the densities
  pdf_p <- pdf_p / sum(pdf_p)
  pdf_q <- pdf_q / sum(pdf_q)

  # Step 7: Function to compute the KL divergence
  KL.divergence <- function(p, q) {
    epsilon <- 1e-10  # Small value to prevent division by zero or log of zero
    p <- p + epsilon
    q <- q + epsilon
    return(sum(p * log(p / q)))
  }

  # Step 8: Function to compute the Jensen-Shannon divergence
  JSD <- function(p, q) {
    m <- 0.5 * (p + q)
    return(0.5 * KL.divergence(p, m) + 0.5 * KL.divergence(q, m))
  }

  # Step 9: Compute the Jensen-Shannon divergence
  js_divergence <- JSD(pdf_p, pdf_q)
  return(js_divergence)
}

# List of p_sample matrices
sample_list <- list(
  t(new.theta.out_50_NDLM_synth_DISC$standard_forecast_errors),
  t(new.theta.out_5_exAL_synth_DISC$standard_forecast_errors),
  t(new.theta.out_20_exAL_synth_DISC$standard_forecast_errors),
  t(new.theta.out_35_exAL_synth_DISC$standard_forecast_errors),
  t(new.theta.out_50_exAL_synth_DISC$standard_forecast_errors),
  t(new.theta.out_65_exAL_synth_DISC$standard_forecast_errors),
  t(new.theta.out_80_exAL_synth_DISC$standard_forecast_errors),
  t(new.theta.out_95_exAL_synth_DISC$standard_forecast_errors)
)

# Corresponding names for clarity in output
sample_names <- c(
  "new.theta.out_50_NDLM_synth$standard_forecast_errors",
  "new.theta.out_5_exAL_synth$standard_forecast_errors",
  "new.theta.out_20_exAL_synth$standard_forecast_errors",
  "new.theta.out_35_exAL_synth$standard_forecast_errors",
  "new.theta.out_50_exAL_synth$standard_forecast_errors",
  "new.theta.out_65_exAL_synth$standard_forecast_errors",
  "new.theta.out_80_exAL_synth$standard_forecast_errors",
  "new.theta.out_95_exAL_synth$standard_forecast_errors"
)

# Compute JSD for each sample and print the results
results <- list()

for (i in 1:length(sample_list)) {
  cat("Computing JSD for:", sample_names[i], "\n")
  js_divergence <- profile_section(
    paste0("figures.compute_jsd.", i),
    compute_jsd(sample_list[[i]], gridsize = c(100, 100, 100))
  )
  cat("Jensen-Shannon divergence for", sample_names[i], "is", js_divergence, "\n\n")
  results[[sample_names[i]]] <- js_divergence
}

# Print final results
cat("Final JSD Results:\n")
print(results)


matrix_df <- as.data.frame(X)
matrix_df <- cbind(Timestamp = timestamps, matrix_df)
write.csv(matrix_df, "factors.csv", row.names = FALSE)


# Function definitions
k_lb_tot_effect <- function(eps, lambda, tef) {
  lb <- (log(eps) - log(abs(tef))) / log(lambda)
  return(ceiling(lb))
}

# Calculate tef
p_tot <- dim(new.theta.out_20_exAL_synth_DISC$sm)[1]
reg_idx <- (p_tot - (ppx - 1) + 1):(p_tot)

# Define lambda
lambda <- 0.99

# Define epsilon values
epsilon_values <- c(0.5, 0.4, 0.3, 0.2, 0.1, 0.05, 0.01, 0.005, 0.001)

# Calculate the mean of k_lb_tot_effect for each epsilon for each tef
compute_results <- function(tef) {
  sapply(epsilon_values, function(eps) max(mean(k_lb_tot_effect(eps, lambda, tef)), 0))
}

# Calculate tef for different quantiles
retro_idx <- 1:TT
tef_5 <- rowSums(X * t(new.theta.out_5_exAL_synth_DISC$sm[reg_idx,retro_idx]))
tef_50 <- rowSums(X * t(new.theta.out_50_exAL_synth_DISC$sm[reg_idx,retro_idx]))
tef_95 <- rowSums(X * t(new.theta.out_95_exAL_synth_DISC$sm[reg_idx,retro_idx]))
tef_20 <- rowSums(X * t(new.theta.out_20_exAL_synth_DISC$sm[reg_idx,retro_idx]))

# Calculate results for each tef
results_5 <- compute_results(tef_5)
results_50 <- compute_results(tef_50)
results_95 <- compute_results(tef_95)
results_20 <- compute_results(tef_20)

# Create data frames for plotting
plot_data_5_50_95 <- data.frame(
  epsilon = rep(epsilon_values, 3),
  mean_k_lb = c(results_5, results_50, results_95),
  Quantile = factor(rep(c("5th", "50th", "95th"), each = length(epsilon_values)))
)

plot_data_20 <- data.frame(
  epsilon = epsilon_values,
  mean_k_lb = results_20,
  Quantile = "20th"
)

# Plot for 5th, 50th, and 95th quantiles
p1 <- ggplot(plot_data_5_50_95, aes(x = epsilon, y = mean_k_lb, color = Quantile)) +
  geom_line(linewidth = 1) +
  geom_point(size = 2) +
  scale_x_log10() +
  labs(title = "Total Effect Error Margin vs. Average k-step Ahead",
       x = expression(epsilon),
       y = "Average k-step Ahead to Make it Negligible") +
  theme_minimal() +
  theme(
    plot.title = element_text(hjust = 0.5, size = 14, face = "bold"),
    axis.title = element_text(size = 12),
    axis.text = element_text(size = 10),
    legend.title = element_text(size = 12),
    legend.text = element_text(size = 10)
  ) +
  scale_color_manual(values = c("darkgreen", "darkred", "darkblue"))

# Save the plot for 5th, 50th, and 95th quantiles
ggsave(filename = "/data/muscat_data/jaguir26/project1_ucsc_phd/tef_5_50_95_plot_DISC.png", plot = p1, width = 8, height = 6, dpi = 900)

# Plot for 20th quantile
p2 <- ggplot(plot_data_20, aes(x = epsilon, y = mean_k_lb, color = Quantile)) +
  geom_line(linewidth = 1) +
  geom_point(size = 2) +
  scale_x_log10() +
  labs(title = "Total Effect Error Margin vs. Average k-step Ahead",
       x = expression(epsilon),
       y = "Average k-step Ahead to Make it Negligible") +
  theme_minimal() +
  theme(
    plot.title = element_text(hjust = 0.5, size = 14, face = "bold"),
    axis.title = element_text(size = 12),
    axis.text = element_text(size = 10),
    legend.title = element_text(size = 12),
    legend.text = element_text(size = 10)
  ) +
  scale_color_manual(values = c("darkorange"))

# Save the plot for 20th quantile
ggsave(filename = "/data/muscat_data/jaguir26/project1_ucsc_phd/tef_20_plot_DISC.png", plot = p2, width = 8, height = 6, dpi = 900)


dim(samp.theta_50_exAL_synth_DISC$samp_theta)
dim(samp.sts_50_exAL_synth_DISC)
dim(samp.gamma_50_exAL_synth_DISC)
dim(samp.sigma_50_exAL_synth_DISC)

inverse_cdf_AL <- function(U, mu, sigma, p) {
  ifelse(U < p, 
         mu + (sigma / (1 - p)) * log(U / p), 
         mu - (sigma / p) * log((1 - U) / (1 - p)))
}

L_fn <- function(p0) {
  stats::uniroot(function(gam) exp(log_g(gam)) - (1 - p0), c(-1000, 0))$root
}

U_fn <- function(p0) {
  stats::uniroot(function(gam) exp(log_g(gam)) - p0, c(0, 1000))$root
}

p_fn <- function(p0, gam) {
  (p0 - as.numeric(gam < 0)) / exp(log_g(gam)) + as.numeric(gam < 0)
}

A_fn <- function(p0, gam) {
  temp_p <- p_fn(p0, gam)
  (1 - 2 * temp_p) / (temp_p * (1 - temp_p))
}

B_fn <- function(p0, gam) {
  temp_p <- p_fn(p0, gam)
  2 / (temp_p * (1 - temp_p))
}

C_fn <- function(p0, gam) {
  temp_p <- p_fn(p0, gam)
  (as.numeric(gam > 0) - temp_p)^(-1)
}


# Set index for parameters
j <- 1
# Set seed for reproducibility
set.seed(777)

# Define the inverse CDF function for the Asymmetric Laplace distribution
inverse_cdf_AL <- function(U, mu, sigma, p) {
  ifelse(U < p, 
         mu + (sigma / (1 - p)) * log(U / p), 
         mu - (sigma / p) * log((1 - U) / (1 - p)))
}

# Define auxiliary functions
p_fn <- function(p0, gam) {
  (p0 - as.numeric(gam < 0)) / exp(log_g(gam)) + as.numeric(gam < 0)
}

C_fn <- function(p0, gam) {
  temp_p <- p_fn(p0, gam)
  (as.numeric(gam > 0) - temp_p)^(-1)
}

# Define quantile levels
p0_5 <- 0.05
p0_20 <- 0.20
p0_35 <- 0.35
p0_50 <- 0.50
p0_65 <- 0.65
p0_80 <- 0.80
p0_95 <- 0.95

# Generate uniform values for inverse sampling, with dimensions [time steps x samples]
n_rows_50 <- dim(samp.theta_50_exAL_synth_DISC$samp_theta)[3]  # Samples
n_cols_50 <- dim(samp.theta_50_exAL_synth_DISC$samp_theta)[2]  # Time steps
u_values_5 <- matrix(runif(n_rows_50 * n_cols_50), ncol = n_rows_50)   # Uniform values for 5th quantile
u_values_20 <- matrix(runif(n_rows_50 * n_cols_50), ncol = n_rows_50)  # Uniform values for 20th quantile
u_values_35 <- matrix(runif(n_rows_50 * n_cols_50), ncol = n_rows_50)  # Uniform values for 35th quantile
u_values_50 <- matrix(runif(n_rows_50 * n_cols_50), ncol = n_rows_50)  # Uniform values for 50th quantile
u_values_65 <- matrix(runif(n_rows_50 * n_cols_50), ncol = n_rows_50)  # Uniform values for 65th quantile
u_values_80 <- matrix(runif(n_rows_50 * n_cols_50), ncol = n_rows_50)  # Uniform values for 80th quantile
u_values_95 <- matrix(runif(n_rows_50 * n_cols_50), ncol = n_rows_50)  # Uniform values for 95th quantile

# Function to compute posterior samples for each quantile
compute_y_post <- function(p0, samp_theta, samp_sts, samp_gamma, samp_sigma, FF, u_values) {
  # Set index for parameters
  j <- 1

  # Extract parameter arrays for computation
  th <- samp_theta$samp_theta                # [parameters x time steps x samples]
  stj <- samp_sts[j, , ]                     # [time steps x samples]
  gamj <- samp_gamma[j, ]                    # [samples]
  sigj <- samp_sigma[j, ]                    # [samples]
  p_exAL <- p_fn(p0, gamj)

  # Reshape FF to align dimensions for matrix multiplication across time steps
  TT <- dim(samp_theta$samp_theta)[2]        # Number of time steps
  FF_reshaped <- array(FF[, j, ], dim = c(dim(samp_theta$samp_theta)[1], 1, TT))

  # Compute XB by applying the matrix multiplication for each time step `t`
  result_list <- lapply(1:TT, function(t) t(FF_reshaped[,,t]) %*% th[,t,])
  XB <- do.call(rbind, result_list)          # [time steps x samples]

  # Compute `mu` using the XB result and additional parameters
  mu <- XB + sigj * abs(gamj) * C_fn(p0, gamj) * stj

  # Compute posterior samples
  inverse_cdf_AL(u_values, mu, sigj, p_exAL)
}

# Compute y_post for each quantile
y_post_5 <- compute_y_post(p0_5, samp.theta_5_exAL_synth_DISC, samp.sts_5_exAL_synth_DISC,
                           samp.gamma_5_exAL_synth_DISC, samp.sigma_5_exAL_synth_DISC, FF, u_values_5)
y_post_5 <- t(y_post_5)
y_post_20 <- compute_y_post(p0_20, samp.theta_20_exAL_synth_DISC, samp.sts_20_exAL_synth_DISC,
                            samp.gamma_20_exAL_synth_DISC, samp.sigma_20_exAL_synth_DISC, FF, u_values_20)
y_post_20 <- t(y_post_20)
y_post_35 <- compute_y_post(p0_35, samp.theta_35_exAL_synth_DISC, samp.sts_35_exAL_synth_DISC,
                            samp.gamma_35_exAL_synth_DISC, samp.sigma_35_exAL_synth_DISC, FF, u_values_35)
y_post_35 <- t(y_post_35)
y_post_50 <- compute_y_post(p0_50, samp.theta_50_exAL_synth_DISC, samp.sts_50_exAL_synth_DISC,
                            samp.gamma_50_exAL_synth_DISC, samp.sigma_50_exAL_synth_DISC, FF, u_values_50)
y_post_50 <- t(y_post_50)
y_post_65 <- compute_y_post(p0_65, samp.theta_65_exAL_synth_DISC, samp.sts_65_exAL_synth_DISC,
                            samp.gamma_65_exAL_synth_DISC, samp.sigma_65_exAL_synth_DISC, FF, u_values_65)
y_post_65 <- t(y_post_65)
y_post_80 <- compute_y_post(p0_80, samp.theta_80_exAL_synth_DISC, samp.sts_80_exAL_synth_DISC,
                            samp.gamma_80_exAL_synth_DISC, samp.sigma_80_exAL_synth_DISC, FF, u_values_80)
y_post_80 <- t(y_post_80)
y_post_95 <- compute_y_post(p0_95, samp.theta_95_exAL_synth_DISC, samp.sts_95_exAL_synth_DISC,
                            samp.gamma_95_exAL_synth_DISC, samp.sigma_95_exAL_synth_DISC, FF, u_values_95)
y_post_95 <- t(y_post_95)


exp_y_post_5 <- exp(y_post_5)
exp_y_post_20 <- exp(y_post_20)
exp_y_post_35 <- exp(y_post_35)
exp_y_post_50 <- exp(y_post_50)
exp_y_post_65 <- exp(y_post_65)
exp_y_post_80 <- exp(y_post_80)
exp_y_post_95 <- exp(y_post_95)

idx <- (TT-500):(TT)
n.samp <- dim(samp.theta_50_exAL_synth_DISC$samp_theta)[3]
plot.ts(exp(Y[1,idx]), ylim = c(0,7))
for(s in 1:n.samp){
    lines(exp_y_post_50[s,idx], lwd = 0.1, col='forestgreen')
    lines(exp_y_post_95[s,idx], lwd = 0.1, col='darkblue')
    lines(exp_y_post_5[s,idx], lwd = 0.1, col='darkred')
} 
lines(exp(Y[1,idx]))

q50 <- fast_col_quantiles_t(y_post_50, probs = c(0.5, 0.025, 0.5, 0.975))
m50 <- colMeans((y_post_50))
q5 <- fast_col_quantiles_t(y_post_5, probs = c(0.05, 0.025, 0.5, 0.975))
m5 <- colMeans((y_post_5))
q95 <- fast_col_quantiles_t(y_post_95, probs = c(0.95, 0.025, 0.5, 0.975))
m95 <- colMeans((y_post_95))
q20 <- fast_col_quantiles_t(y_post_20, probs = c(0.2, 0.025, 0.5, 0.975))
m20 <- colMeans((y_post_20))
q35 <- fast_col_quantiles_t(y_post_35, probs = c(0.35, 0.025, 0.5, 0.975))
m35 <- colMeans((y_post_35))
q65 <- fast_col_quantiles_t(y_post_65, probs = c(0.65, 0.025, 0.5, 0.975))
m65 <- colMeans((y_post_65))
q80 <- fast_col_quantiles_t(y_post_80, probs = c(0.8, 0.025, 0.5, 0.975))
m80 <- colMeans((y_post_80))

exp_q50 <- fast_col_quantiles_t(exp_y_post_50, probs = c(0.5, 0.025, 0.5, 0.975))
exp_m50 <- colMeans((exp_y_post_50))
exp_q5 <- fast_col_quantiles_t(exp_y_post_5, probs = c(0.05, 0.025, 0.5, 0.975))
exp_m5 <- colMeans((exp_y_post_5))
exp_q95 <- fast_col_quantiles_t(exp_y_post_95, probs = c(0.95, 0.025, 0.5, 0.975))
exp_m95 <- colMeans((exp_y_post_95))
exp_q20 <- fast_col_quantiles_t(exp_y_post_20, probs = c(0.2, 0.025, 0.5, 0.975))
exp_m20 <- colMeans((exp_y_post_20))
exp_q35 <- fast_col_quantiles_t(exp_y_post_35, probs = c(0.35, 0.025, 0.5, 0.975))
exp_m35 <- colMeans((exp_y_post_35))
exp_q65 <- fast_col_quantiles_t(exp_y_post_65, probs = c(0.65, 0.025, 0.5, 0.975))
exp_m65 <- colMeans((exp_y_post_65))
exp_q80 <- fast_col_quantiles_t(exp_y_post_80, probs = c(0.8, 0.025, 0.5, 0.975))
exp_m80 <- colMeans((exp_y_post_80))


# Define the time range and common y-axis limits
idx <- (TT - 500):(TT)
n.samp <- dim(samp.theta_50_exAL_synth_DISC$samp_theta)[3]
ylim_range <- c(0, 7)
output_dir <- "/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics_reproduce"

# Create a function for plotting posterior predictive samples with legends and labels (without the new.theta.out_p0_exAL_synth$exps)
plot_posterior_samples <- function(y_post, q, quantile_label, p0, color_post, color_quantile, ylim_range, idx) {
  par(mar = c(4, 4, 2, 2))  # Adjust margins
  plot(timestamps[idx], exp(Y[1, idx]), type = "l", ylim = ylim_range, 
       col = 'black', lwd = 1.5, xlab = "Date", ylab = "log(Streamflow)", 
       main = paste(quantile_label, "Qntl.: Post. Pred. Samp."))
  
  for (s in 1:n.samp) {
    lines(timestamps[idx], y_post[s, idx], lwd = 0.1, col = color_post)
  }
  
  lines(timestamps[idx], q[1, idx], lwd = 1, col = color_quantile)  # Post. Pred. Quantile
  lines(timestamps[idx], exp(Y[1, idx]), lwd = 1.5, col = 'black')  # True Obs. Streamflow
  
  # Add a legend, slightly adjusted to the left
  legend(x = "topright", inset = c(0.2, 0), legend = c("Post. Pred. Samp.", paste0(p0, "th Post. Pred. Qntl."), "log(Streamflow)"),
         col = c(color_post, color_quantile, 'black'), lwd = c(1, 1, 1.5), bty = "n")
}

# Function to save individual plots (without new.theta.out_p0_exAL_synth$exps)
save_individual_plot <- function(filename, y_post, q, quantile_label, p0, color_post, color_quantile) {
  png(filename = paste0(output_dir, filename), width = 2000, height = 1200, res = 300)
  plot_posterior_samples(y_post, q, quantile_label, p0, color_post, color_quantile, ylim_range, idx)
  dev.off()
}

# Save individual plots
save_individual_plot("plot_50th_quantile_DISC.png", exp_y_post_50, exp_q50, "50th", "50", "forestgreen", "orange")
save_individual_plot("plot_95th_quantile_DISC.png", exp_y_post_95, exp_q95, "95th", "95", "darkblue", "orange")
save_individual_plot("plot_5th_quantile_DISC.png", exp_y_post_5, exp_q5, "5th", "5", "darkred", "orange")

# Save plot with all posterior samples together (without new.theta.out_p0_exAL_synth$exps)
png(filename = paste0(output_dir, "/plot_all_quantiles_combined_DISC.png"), width = 2000, height = 1200, res = 300)
par(mar = c(4, 4, 2, 2))  # Adjust margins
plot(timestamps[idx], exp(Y[1, idx]), type = "l", ylim = ylim_range, 
     col = 'black', lwd = 1.5, xlab = "Date", ylab = "log(Streamflow)", 
     main = "Post. Pred. Samp.: 50th, 95th, and 5th Qntls.")

for (s in 1:n.samp) {
  lines(timestamps[idx], exp_y_post_50[s, idx], lwd = 0.1, col = 'forestgreen')
  lines(timestamps[idx], exp_y_post_95[s, idx], lwd = 0.1, col = 'darkblue')
  lines(timestamps[idx], exp_y_post_5[s, idx], lwd = 0.1, col = 'darkred')
}

lines(timestamps[idx], exp(Y[1, idx]), lwd = 1.5, col = 'black')  # True Obs. Streamflow
legend(x = "topright", inset = c(0.2, 0), legend = c("50th Post. Pred. Samp.", "95th Post. Pred. Samp.", "5th Post. Pred. Samp.", "log(Streamflow)"),
       col = c("forestgreen", "darkblue", "darkred", 'black'), lwd = c(1, 1, 1, 1.5), bty = "n")
dev.off()

# Save matrix plot with 3 rows (without new.theta.out_p0_exAL_synth$exps)
png(filename = paste0(output_dir, "/plot_3_row_matrix_DISC.png"), width = 2000, height = 1600, res = 300)
par(mfrow = c(3, 1), mar = c(4, 4, 2, 2))  # Set the layout to 3 rows and 1 column, adjust margins
plot_posterior_samples(exp_y_post_50, exp_q50, "50th", "50", "forestgreen", "orange", ylim_range, idx)
plot_posterior_samples(exp_y_post_95, exp_q95, "95th", "95", "darkblue", "orange", ylim_range, idx)
plot_posterior_samples(exp_y_post_5, exp_q5, "5th", "5", "darkred", "orange", ylim_range, idx)
dev.off()

# Save matrix plot with combined plot on top and 3 quantiles below (without new.theta.out_p0_exAL_synth$exps)
png(filename = paste0(output_dir, "/plot_combined_matrix_DISC.png"), width = 2000, height = 1800, res = 300)
par(mfrow = c(4, 1), mar = c(4, 4, 2, 2))  # Set the layout to 4 rows and 1 column, adjust margins
plot(timestamps[idx], exp(Y[1, idx]), type = "l", ylim = ylim_range, 
     col = 'black', lwd = 1.5, xlab = "Date", ylab = "log(Streamflow)", 
     main = "Post. Pred. Samp.: 50th, 95th, and 5th Qntls.")

for (s in 1:n.samp) {
  lines(timestamps[idx], exp_y_post_50[s, idx], lwd = 0.1, col = 'forestgreen')
  lines(timestamps[idx], exp_y_post_95[s, idx], lwd = 0.1, col = 'darkblue')
  lines(timestamps[idx], exp_y_post_5[s, idx], lwd = 0.1, col = 'darkred')
}

lines(timestamps[idx], exp(Y[1, idx]), lwd = 1.5, col = 'black')  # True Obs. Streamflow
legend(x = "topright", inset = c(0.2, 0), legend = c("50th Post. Pred. Samp.", "95th Post. Pred. Samp.", "5th Post. Pred. Samp.", "log(Streamflow)"),
       col = c("forestgreen", "darkblue", "darkred", 'black'), lwd = c(1, 1, 1, 1.5), bty = "n")

# Individual quantile plots
plot_posterior_samples(exp_y_post_50, exp_q50, "50th", "50", "forestgreen", "orange", ylim_range, idx)
plot_posterior_samples(exp_y_post_95, exp_q95, "95th", "95", "darkblue", "orange", ylim_range, idx)
plot_posterior_samples(exp_y_post_5, exp_q5, "5th", "5", "darkred", "orange", ylim_range, idx)
dev.off()

# Reset plotting parameters
par(mfrow = c(1, 1))  # Return to single plot layout


idx <- (TT-500):(TT)
n.samp <- dim(samp.theta_95_exAL_synth_DISC$samp_theta)[3]

plot.ts(exp(Y[1,idx]), ylim = c(0,7))
for(s in 1:n.samp){
    lines(exp_y_post_95[s,idx], lwd = 0.1, col='darkblue')
} 
lines(exp_q95[2,idx], lwd = 0.8, col='gray')
lines(exp_q95[3,idx], lwd = 0.8, col='gray')
lines(exp_q95[4,idx], lwd = 1, col='gray')
lines(t(exp_m95)[idx], lwd = 1, col='purple')
lines(exp(new.theta.out_95_exAL_synth_DISC$exps[1,idx]), lwd = 1.5, col='orange')
lines(exp(Y[1,idx]))



set.seed(777)
############################################################################
# Function Definitions
inverse_cdf_AL <- function(U, mu, sigma, p) {
  ifelse(U < p, 
         mu + (sigma / (1 - p)) * log(U / p), 
         mu - (sigma / p) * log((1 - U) / (1 - p)))
}
############################################################################
p_fn <- function(p0, gam) {
  (p0 - as.numeric(gam < 0)) / exp(log_g(gam)) + as.numeric(gam < 0)
}
############################################################################
C_fn <- function(p0, gam) {
  temp_p <- p_fn(p0, gam)
  (as.numeric(gam > 0) - temp_p)^(-1)
}
############################################################################
# Generalized function to handle each case
generate_y_post <- function(p0, xb_matrix, gamma_sample, sigma_sample) {
  n_rows <- dim(xb_matrix)[1]
  n_cols <- dim(xb_matrix)[2]
  y_post <- matrix(NA_real_, nrow = n_rows, ncol = n_cols)
  
  for (t in 1:n_cols) {
    s_0 <- rtruncnorm(1, a=0, b=Inf, mean = 0, sd = 1)
    u <- runif(n_rows)
    y_post[,t] <- xb_matrix[,t] + sigma_sample * abs(gamma_sample) * C_fn(p0, gamma_sample) * s_0 +  
                  sigma_sample * inverse_cdf_AL(u, 0, 1, p_fn(p0, gamma_sample))
  }

  return(y_post)
}
############################################################################
# Case 1: p0 = 0.05
p0_05 <- 0.05
xb_05_f <- t(xbs[1,,])
gam_05_f <- samp.gamma_5_exAL_synth_DISC[1,]
sig_05_f <- samp.sigma_5_exAL_synth_DISC[1,]
y_post_5_f <- (generate_y_post(p0_05, xb_05_f, gam_05_f, sig_05_f))
exp_y_post_5_f <- exp(generate_y_post(p0_05, xb_05_f, gam_05_f, sig_05_f))
# Case 2: p0 = 0.5
p0_50 <- 0.5
xb_50_f <- t(xbs[4,,])
gam_50_f <- samp.gamma_50_exAL_synth_DISC[1,]
sig_50_f <- samp.sigma_50_exAL_synth_DISC[1,]
y_post_50_f <- (generate_y_post(p0_50, xb_50_f, gam_50_f, sig_50_f))
exp_y_post_50_f <- exp(generate_y_post(p0_50, xb_50_f, gam_50_f, sig_50_f))
# Case 3: p0 = 0.95
p0_95 <- 0.95
xb_95_f <- t(xbs[7,,])
gam_95_f <- samp.gamma_95_exAL_synth_DISC[1,]
sig_95_f <- samp.sigma_95_exAL_synth_DISC[1,]
y_post_95_f <- (generate_y_post(p0_95, xb_95_f, gam_95_f, sig_95_f))
exp_y_post_95_f <- exp(generate_y_post(p0_95, xb_95_f, gam_95_f, sig_95_f))
# Case 4: p0 = 0.20
p0_20 <- 0.20
xb_20_f <- t(xbs[2,,])
gam_20_f <- samp.gamma_20_exAL_synth_DISC[1,]
sig_20_f <- samp.sigma_20_exAL_synth_DISC[1,]
y_post_20_f <- (generate_y_post(p0_20, xb_20_f, gam_20_f, sig_20_f))
exp_y_post_20_f <- exp(generate_y_post(p0_20, xb_20_f, gam_20_f, sig_20_f))
# Case 5: p0 = 0.80
p0_80 <- 0.80
xb_80_f <- t(xbs[6,,])
gam_80_f <- samp.gamma_80_exAL_synth_DISC[1,]
sig_80_f <- samp.sigma_80_exAL_synth_DISC[1,]
y_post_80_f <- (generate_y_post(p0_80, xb_80_f, gam_80_f, sig_80_f))
exp_y_post_80_f <- exp(generate_y_post(p0_80, xb_80_f, gam_80_f, sig_80_f))
# Case 6: p0 = 0.35
p0_35 <- 0.35
xb_35_f <- t(xbs[3,,])
gam_35_f <- samp.gamma_35_exAL_synth_DISC[1,]
sig_35_f <- samp.sigma_35_exAL_synth_DISC[1,]
y_post_35_f <- (generate_y_post(p0_35, xb_35_f, gam_35_f, sig_35_f))
exp_y_post_35_f <- exp(generate_y_post(p0_35, xb_35_f, gam_35_f, sig_35_f))
# Case 7: p0 = 0.65
p0_65 <- 0.65
xb_65_f <- t(xbs[5,,])
gam_65_f <- samp.gamma_65_exAL_synth_DISC[1,]
sig_65_f <- samp.sigma_65_exAL_synth_DISC[1,]
y_post_65_f <- (generate_y_post(p0_65, xb_65_f, gam_65_f, sig_65_f))
exp_y_post_65_f <- exp(generate_y_post(p0_65, xb_65_f, gam_65_f, sig_65_f))
############################################################################
n_rows_5 <- dim(xb_05_f)[1]
n_cols_5 <- dim(xb_05_f)[2]

# Initialize the y_reps array with dimensions 7 x n.samp x TT
y_reps_f <- array(NA, dim = c(7, n.samp, ranges[1]))

# Populate the array as specified
y_reps_f[1,,] <- exp_y_post_5_f[,]
y_reps_f[4,,] <- exp_y_post_50_f[,]
y_reps_f[7,,] <- exp_y_post_95_f[,]
y_reps_f[2,,] <- exp_y_post_20_f[,]
y_reps_f[3,,] <- exp_y_post_35_f[,]
y_reps_f[5,,] <- exp_y_post_80_f[,]
y_reps_f[6,,] <- exp_y_post_65_f[,]

for(t in 1:ranges[1]){
    y_reps_f[1,,t] <- sort(exp_y_post_5_f[,t])
    y_reps_f[4,,t] <- sort(exp_y_post_50_f[,t])
    y_reps_f[7,,t] <- sort(exp_y_post_95_f[,t])
    y_reps_f[2,,t] <- sort(exp_y_post_20_f[,t])
    y_reps_f[3,,t] <- sort(exp_y_post_35_f[,t])
    y_reps_f[5,,t] <- sort(exp_y_post_80_f[,t])
    y_reps_f[6,,t] <- sort(exp_y_post_65_f[,t])
}

# Save the array to your current directory
saveRDS(y_reps_f, file = "y_reps_f.rds")

print("Array y_reps_f saved as y_reps_f.rds in the current directory.")

y_reps <- array(NA, dim = c(7, n.samp, TT))

# Populate the array as specified
y_reps[1,,] <- exp_y_post_5[,]
y_reps[4,,] <- exp_y_post_50[,]
y_reps[7,,] <- exp_y_post_95[,]
y_reps[2,,] <- exp_y_post_20[,]
y_reps[3,,] <- exp_y_post_35[,]
y_reps[5,,] <- exp_y_post_80[,]
y_reps[6,,] <- exp_y_post_65[,]

for(t in 1:TT){
    y_reps[1,,t] <- sort(exp_y_post_5[,t])
    y_reps[4,,t] <- sort(exp_y_post_50[,t])
    y_reps[7,,t] <- sort(exp_y_post_95[,t])
    y_reps[2,,t] <- sort(exp_y_post_20[,t])
    y_reps[3,,t] <- sort(exp_y_post_35[,t])
    y_reps[5,,t] <- sort(exp_y_post_80[,t])
    y_reps[6,,t] <- sort(exp_y_post_65[,t])
}


# Save the array to your current directory
saveRDS(y_reps, file = "y_reps.rds")

print("Array y_reps saved as y_reps.rds in the current directory.")


synthesize_samples <- function(y_reps, q_s, n_cores = detectCores() - 1) {
  
  # Get dimensions
  n.q     <- dim(y_reps)[1]
  n.samp  <- dim(y_reps)[2]
  n.times <- dim(y_reps)[3]
  
  stopifnot(length(q_s) == n.q, !is.unsorted(q_s))
  k <- 1
  # Generate random uniform matrix
  u_mat <- matrix(runif(k*n.samp * n.times), nrow = k*n.samp, ncol = n.times)
  
  # Function to process a single time point
  process_time <- function(t_idx) {
    u_vec <- u_mat[, t_idx]  # Vector of u's for current time
    
    # Find indices
    idx <- findInterval(u_vec, q_s)
    idx[idx == 0] <- 1
    idx[idx >= n.q] <- n.q - 1
    
    # Interpolation weights
    q_lo <- q_s[idx]
    q_hi <- q_s[idx + 1]
    w <- (u_vec - q_lo) / (q_hi - q_lo)
    
    # Extract corresponding quantiles efficiently
    y_lower <- y_reps[cbind(idx, seq_len(n.samp), t_idx)]
    y_upper <- y_reps[cbind(idx + 1, seq_len(n.samp), t_idx)]
    
    # Interpolate
    result <- (1 - w) * y_lower + w * y_upper
    
    # Boundary conditions (lower)
    lower_mask <- u_vec <= q_s[1]
    if (any(lower_mask)) {
      result[lower_mask] <- quantile(y_reps[1, , t_idx], probs = u_vec[lower_mask], type = 8)
    }
    
    # Boundary conditions (upper)
    upper_mask <- u_vec >= q_s[n.q]
    if (any(upper_mask)) {
      result[upper_mask] <- quantile(y_reps[n.q, , t_idx], probs = u_vec[upper_mask], type = 8)
    }
    
    result
  }
  
  # Run parallelized over time dimension
  cl <- makeCluster(1)
  clusterExport(cl, varlist = c("u_mat", "y_reps", "q_s", "n.q", "n.samp"), envir = environment())
  out <- parSapply(cl, seq_len(n.times), process_time)
  stopCluster(cl)
  
  # Adjust dimension to [n.samp x n.times]
  if (is.vector(out)) {
    out <- matrix(out, nrow = k*n.samp, ncol = n.times)
  } else {
    out <- matrix(out, nrow = k*n.samp, ncol = n.times)
  }
  
  return(out)
}


# set.seed(777)
# y_reps_f <- readRDS("y_reps_f.rds")
# q_s    <- c(0.05, 0.2, 0.35, 0.5, 0.65, 0.8, 0.95)
# n.q     <- dim(y_reps)[1]
# n.samp  <- dim(y_reps)[2]
# n.times <- dim(y_reps)[3]
# stopifnot(length(q_s) == n.q, !is.unsorted(q_s))
# total_samp <- n.samp
# u_mat <- matrix(runif(total_samp * n.times), nrow = total_samp, ncol = n.times)
# u_vec <- u_mat[, 1]
# idx <- findInterval(u_vec, q_s)

# u_vec[4]
# q_s
# idx[4]
# n.q

# # Weights
# q_lo <- q_s[idx]
# q_hi <- q_s[idx + 1]
# w <- (u_vec - q_lo) / (q_hi - q_lo)

# # Extract quantiles
# y_lower <- y_reps[cbind(idx, (seq_len(total_samp) - 1) %% n.samp + 1, t_idx)]
# y_upper <- y_reps[cbind(idx + 1, (seq_len(total_samp) - 1) %% n.samp + 1, t_idx)]

# # Linear interpolation
# result <- (1 - w) * y_lower + w * y_upper

y_reps_f <- readRDS("y_reps_f.rds")

q_s    <- c(0.05, 0.2, 0.35, 0.5, 0.65, 0.8, 0.95)
n.q     <- length(q_s)
n.samp  <- n.samp
n.times <- ranges[1]

synth_f <- synthesize_samples(y_reps_f, q_s)
dim(synth_f)

synth_f_q <- colQuantiles(synth_f, probs = q_s, type = 8)
synth_f_q <- t(synth_f_q)
dim(synth_f_q)

# y_reps_f <- readRDS("y_reps_f.rds")

# q_s    <- c(0.05, 0.2, 0.35, 0.5, 0.65, 0.8, 0.95)
# n.q     <- length(q_s)
# n.samp  <- n.samp
# n.times <- ranges[1]

# synth_f2 <- synthesize_samples(y_reps_f, q_s)
# dim(synth_f2)

# synth_f_q2 <- colQuantiles(synth_f, probs = q_s, type = 8)
# synth_f_q2 <- t(synth_f_q)
# dim(synth_f_q2)

for (t in 1:ranges[1]) {
    synth_f[,t] <- sort(synth_f[,t])
    # synth_f2[,t] <- sort(synth_f2[,t])
}

plot.ts(rep(0,ranges[1]), ylim = c(0,10))

SL <- San_Lorenzo_Daily_USGS_R[San_Lorenzo_Daily_USGS_R$Date >= timestamps[1] , ]
SL <- SL[(TT+1):(TT+ranges[1]) , ]

for (s in 1:dim(synth_f)[1]) {
   lines(synth_f[s,], col = 'pink', lwd = 0.5)
}

points(SL$data0, lwd = 0.8)

for (i in 1:n.q) {
   lines(synth_f_q[i,], col = 'gray', lwd = 2)
}

# Adding quantile bands (blue) for 95th Quantile estimation
result <- fast_row_quantiles_t(exp(xbs[7, , ]), probs = c(0.025, 0.5, 0.975))
lines(result[1,], col = 'blue', lty = 2, lwd = 1)
lines(result[2,], col = 'darkblue', lwd = 1.5)
lines(result[3,], col = 'blue', lty = 2, lwd = 1)

# Adding quantile bands (blue) for 95th Quantile estimation
result <- fast_row_quantiles_t(exp(xbs[1, , ]), probs = c(0.025, 0.5, 0.975))
lines(result[1,], col = 'red', lty = 2, lwd = 1)
lines(result[2,], col = 'darkred', lwd = 1.5)
lines(result[3,], col = 'red', lty = 2, lwd = 1)

# Adding quantile bands (blue) for 95th Quantile estimation
result <- fast_row_quantiles_t(exp(xbs[4, , ]), probs = c(0.025, 0.5, 0.975))
lines(result[1,], col = 'green', lty = 2, lwd = 1)
lines(result[2,], col = 'forestgreen', lwd = 1.5)
lines(result[3,], col = 'green', lty = 2, lwd = 1)

# idx <- (13171-27):(13171-27+10)
# lines(exp(new.theta.out_95_exAL_synth_DISC$exps[3,idx]), col = 'lightblue', lwd = 2)
# lines(exp(new.theta.out_50_exAL_synth_DISC$exps[3,idx]), col = 'lightgreen', lwd = 2)
# lines(exp(new.theta.out_5_exAL_synth_DISC$exps[3,idx]), col = 'purple', lwd = 2)

# idx <- (13171-27):13171
# lines(exp(new.theta.out_95_exAL_synth_DISC$exps[2,idx]), col = 'lightblue', lwd = 2)
# lines(exp(new.theta.out_50_exAL_synth_DISC$exps[2,idx]), col = 'lightgreen', lwd = 2)
# lines(exp(new.theta.out_5_exAL_synth_DISC$exps[2,idx]), col = 'purple', lwd = 2)

y_reps_f_new <- array(NA_real_,c(7,n.samp,ranges[1]))

xxx <- 1
for(t in 1:ranges[1]){
    for(s in 1:n.samp){
    gamma <- samp.gamma_95_exAL_synth_DISC[1,s]*xxx
    sigma <- samp.sigma_95_exAL_synth_DISC[1,s]
    p00 <- 0.95
    mu <- xbs[7,t,s]
    y_reps_f_new[7,s,t] <- rexal(1, p00, mu, sigma, gamma)   
    
    gamma <- samp.gamma_80_exAL_synth_DISC[1,s]*xxx
    sigma <- samp.sigma_80_exAL_synth_DISC[1,s]
    p00 <- 0.80
    mu <- xbs[6,t,s]
    y_reps_f_new[6,s,t] <- rexal(1, p00, mu, sigma, gamma)   

    gamma <- samp.gamma_65_exAL_synth_DISC[1,s]*xxx
    sigma <- samp.sigma_65_exAL_synth_DISC[1,s]
    p00 <- 0.65
    mu <- xbs[5,t,s]
    y_reps_f_new[5,s,t] <- rexal(1, p00, mu, sigma, gamma)   

    gamma <- samp.gamma_50_exAL_synth_DISC[1,s]*xxx
    sigma <- samp.sigma_50_exAL_synth_DISC[1,s]
    p00 <- 0.50
    mu <- xbs[4,t,s]
    y_reps_f_new[4,s,t] <- rexal(1, p00, mu, sigma, gamma)   

    gamma <- samp.gamma_35_exAL_synth_DISC[1,s]*xxx
    sigma <- samp.sigma_35_exAL_synth_DISC[1,s]
    p00 <- 0.35
    mu <- xbs[3,t,s]
    y_reps_f_new[3,s,t] <- rexal(1, p00, mu, sigma, gamma)   

    gamma <- samp.gamma_20_exAL_synth_DISC[1,s]*xxx
    sigma <- samp.sigma_20_exAL_synth_DISC[1,s]
    p00 <- 0.20
    mu <- xbs[2,t,s]
    y_reps_f_new[2,s,t] <- rexal(1, p00, mu, sigma, gamma)   
        
    gamma <- samp.gamma_5_exAL_synth_DISC[1,s]*xxx
    sigma <- samp.sigma_5_exAL_synth_DISC[1,s]
    p00 <- 0.05
    mu <- xbs[1,t,s]
    y_reps_f_new[1,s,t] <- rexal(1, p00, mu, sigma, gamma)   
    
    
    }

}



y_reps_f_5 <- y_reps_f_new[1,,]
y_reps_f_20 <- y_reps_f_new[2,,]
y_reps_f_35 <- y_reps_f_new[3,,]
y_reps_f_50 <- y_reps_f_new[4,,]
y_reps_f_65 <- y_reps_f_new[5,,]
y_reps_f_80 <- y_reps_f_new[6,,]
y_reps_f_95 <- y_reps_f_new[7,,]
for(t in 1:ranges[1]){
    y_reps_f_5[,t] <- sort(y_reps_f_5[,t])
    y_reps_f_20[,t] <- sort(y_reps_f_20[,t])
    y_reps_f_35[,t] <- sort(y_reps_f_35[,t])
    y_reps_f_50[,t] <- sort(y_reps_f_50[,t])
    y_reps_f_65[,t] <- sort(y_reps_f_65[,t])
    y_reps_f_80[,t] <- sort(y_reps_f_80[,t])
    y_reps_f_95[,t] <- sort(y_reps_f_95[,t])
}

y_reps_f_new[1,,] <- y_reps_f_5  
y_reps_f_new[2,,] <- y_reps_f_20  
y_reps_f_new[3,,] <- y_reps_f_35  
y_reps_f_new[4,,] <- y_reps_f_50  
y_reps_f_new[5,,] <- y_reps_f_65  
y_reps_f_new[6,,] <- y_reps_f_80  
y_reps_f_new[7,,] <- y_reps_f_95 

# Save the array to your current directory
saveRDS(y_reps_f_new, file = "y_reps_f_new.rds")



y_reps_f <- readRDS("y_reps_f_new.rds")

q_s    <- c(0.05, 0.2, 0.35, 0.5, 0.65, 0.8, 0.95)
n.q     <- length(q_s)
n.samp  <- n.samp
n.times <- ranges[1]

synth_f <- synthesize_samples(exp(y_reps_f), q_s)
dim(synth_f)

synth_f_q <- colQuantiles(synth_f, probs = q_s, type = 8)
synth_f_q <- t(synth_f_q)
dim(synth_f_q)

for (t in 1:ranges[1]) {
    synth_f[,t] <- sort(synth_f[,t])
}

plot.ts(rep(0,ranges[1]), ylim = c(0,10))

SL <- San_Lorenzo_Daily_USGS_R[San_Lorenzo_Daily_USGS_R$Date >= timestamps[1] , ]
SL <- SL[(TT+1):(TT+ranges[1]) , ]

for (s in 1:dim(synth_f)[1]) {
   lines(synth_f[s,], col = 'pink', lwd = 0.5)
}

points(SL$data0, lwd = 0.8)

for (i in 1:n.q) {
   lines(synth_f_q[i,], col = 'gray', lwd = 2)
}

# Adding quantile bands (blue) for 95th Quantile estimation
result <- fast_row_quantiles_t(exp(xbs[7, , ]), probs = c(0.025, 0.5, 0.975))
lines(result[1,], col = 'blue', lty = 2, lwd = 1)
lines(result[2,], col = 'darkblue', lwd = 1.5)
lines(result[3,], col = 'blue', lty = 2, lwd = 1)

# Adding quantile bands (blue) for 95th Quantile estimation
result <- fast_row_quantiles_t(exp(xbs[1, , ]), probs = c(0.025, 0.5, 0.975))
lines(result[1,], col = 'red', lty = 2, lwd = 1)
lines(result[2,], col = 'darkred', lwd = 1.5)
lines(result[3,], col = 'red', lty = 2, lwd = 1)

# Adding quantile bands (blue) for 95th Quantile estimation
result <- fast_row_quantiles_t(exp(xbs[4, , ]), probs = c(0.025, 0.5, 0.975))
lines(result[1,], col = 'green', lty = 2, lwd = 1)
lines(result[2,], col = 'forestgreen', lwd = 1.5)
lines(result[3,], col = 'green', lty = 2, lwd = 1)

# for (s in 1:n.samp) {
#    lines(exp(xbs[4,,s]), col = 'red', lwd = 0.05)
#    lines(exp(xbs[1,,s]), col = 'lightgreen', lwd = 0.05)
#    lines(exp(xbs[7,,s]), col = 'lightblue', lwd = 0.05)
# }


# for (s in 1:n.samp) {
#    lines(exp(y_reps_f_95[s,]), col = 'gray', lwd = 0.1)
# }

result <- fast_col_quantiles_t(exp(y_reps_f_95), probs = 0.95)[1, ]
lines(result, col = 'black', lwd = 0.5)
result <- fast_col_quantiles_t(exp(y_reps_f_80), probs = 0.80)[1, ]
lines(result, col = 'black', lwd = 0.5)
result <- fast_col_quantiles_t(exp(y_reps_f_65), probs = 0.65)[1, ]
lines(result, col = 'black', lwd = 0.5)
result <- fast_col_quantiles_t(exp(y_reps_f_50), probs = 0.50)[1, ]
lines(result, col = 'black', lwd = 0.5)
result <- fast_col_quantiles_t(exp(y_reps_f_35), probs = 0.35)[1, ]
lines(result, col = 'black', lwd = 0.5)
result <- fast_col_quantiles_t(exp(y_reps_f_20), probs = 0.20)[1, ]
lines(result, col = 'black', lwd = 0.5)
result <- fast_col_quantiles_t(exp(y_reps_f_5), probs = 0.05)[1, ]
lines(result, col = 'black', lwd = 0.5)


n.samp
dim(y_reps_f)
dim(xbs)

idx_sub <- (TT-19+1):(TT)

y_reps_new <- array(NA_real_,c(7,n.samp,length(idx_sub)))

xxx <- 1
for(t in 1:length(idx_sub)){
    tt <- idx_sub[t]
    for(s in 1:n.samp){
    gamma <- samp.gamma_95_exAL_synth_DISC[1,s]*xxx
    sigma <- samp.sigma_95_exAL_synth_DISC[1,s]
    p00 <- 0.95
    mu <- xbs_retro[7,tt,s]
    y_reps_new[7,s,t] <- rexal(1, p00, mu, sigma, gamma)   
    
    gamma <- samp.gamma_80_exAL_synth_DISC[1,s]*xxx
    sigma <- samp.sigma_80_exAL_synth_DISC[1,s]
    p00 <- 0.80
    mu <- xbs_retro[6,tt,s]
    y_reps_new[6,s,t] <- rexal(1, p00, mu, sigma, gamma)   

    gamma <- samp.gamma_65_exAL_synth_DISC[1,s]*xxx
    sigma <- samp.sigma_65_exAL_synth_DISC[1,s]
    p00 <- 0.65
    mu <- xbs_retro[5,tt,s]
    y_reps_new[5,s,t] <- rexal(1, p00, mu, sigma, gamma)   

    gamma <- samp.gamma_50_exAL_synth_DISC[1,s]*xxx
    sigma <- samp.sigma_50_exAL_synth_DISC[1,s]
    p00 <- 0.50
    mu <- xbs_retro[4,tt,s]
    y_reps_new[4,s,t] <- rexal(1, p00, mu, sigma, gamma)   

    gamma <- samp.gamma_35_exAL_synth_DISC[1,s]*xxx
    sigma <- samp.sigma_35_exAL_synth_DISC[1,s]
    p00 <- 0.35
    mu <- xbs_retro[3,tt,s]
    y_reps_new[3,s,t] <- rexal(1, p00, mu, sigma, gamma)   

    gamma <- samp.gamma_20_exAL_synth_DISC[1,s]*xxx
    sigma <- samp.sigma_20_exAL_synth_DISC[1,s]
    p00 <- 0.20
    mu <- xbs_retro[2,tt,s]
    y_reps_new[2,s,t] <- rexal(1, p00, mu, sigma, gamma)   
        
    gamma <- samp.gamma_5_exAL_synth_DISC[1,s]*xxx
    sigma <- samp.sigma_5_exAL_synth_DISC[1,s]
    p00 <- 0.05
    mu <- xbs_retro[1,tt,s]
    y_reps_new[1,s,t] <- rexal(1, p00, mu, sigma, gamma)   
    }
}

y_reps_5 <- y_reps_new[1,,]
y_reps_20 <- y_reps_new[2,,]
y_reps_35 <- y_reps_new[3,,]
y_reps_50 <- y_reps_new[4,,]
y_reps_65 <- y_reps_new[5,,]
y_reps_80 <- y_reps_new[6,,]
y_reps_95 <- y_reps_new[7,,]
for(t in 1:length(idx_sub)){
    y_reps_5[,t] <- sort(y_reps_5[,t])
    y_reps_20[,t] <- sort(y_reps_20[,t])
    y_reps_35[,t] <- sort(y_reps_35[,t])
    y_reps_50[,t] <- sort(y_reps_50[,t])
    y_reps_65[,t] <- sort(y_reps_65[,t])
    y_reps_80[,t] <- sort(y_reps_80[,t])
    y_reps_95[,t] <- sort(y_reps_95[,t])
}

y_reps_new[1,,] <- y_reps_5  
y_reps_new[2,,] <- y_reps_20  
y_reps_new[3,,] <- y_reps_35  
y_reps_new[4,,] <- y_reps_50  
y_reps_new[5,,] <- y_reps_65  
y_reps_new[6,,] <- y_reps_80  
y_reps_new[7,,] <- y_reps_95 

# Save the array to your current directory
saveRDS(y_reps_new, file = "y_reps_new.rds")

y_reps <- readRDS("y_reps_new.rds")

q_s    <- c(0.05, 0.2, 0.35, 0.5, 0.65, 0.8, 0.95)
n.q     <- length(q_s)

synth <- synthesize_samples(exp(y_reps[,,]), q_s)
dim(synth)

synth_q <- colQuantiles(synth, probs = q_s, type = 8)
synth_q <- t(synth_q)
dim(synth_q)


for (t in 1:length(idx_sub)) {
    synth[,t] <- sort(synth[,t])
}

idx <- idx_sub
plot.ts(rep(0,length(idx)), ylim = c(0,10))

SL <- San_Lorenzo_Daily_USGS_R[San_Lorenzo_Daily_USGS_R$Date >= timestamps[1] , ]

for (s in 1:n.samp) {
   lines(synth[s,], col = 'pink', lwd = 0.1)
}

points(SL$data0[idx], lwd = 0.8)

for (i in 1:n.q) {
   lines(synth_q[i,], col = 'gray', lwd = 2)
}

lines(exp(new.theta.out_95_exAL_synth_DISC$exps[1,idx]), col = 'darkblue', lwd = 2)
lines(exp(new.theta.out_50_exAL_synth_DISC$exps[1,idx]), col = 'forestgreen', lwd = 2)
lines(exp(new.theta.out_5_exAL_synth_DISC$exps[1,idx]), col = 'darkred', lwd = 2)

lines(exp(new.theta.out_95_exAL_synth_DISC_uni$exps[1,idx]), col = 'lightblue', lwd = 2)
lines(exp(new.theta.out_50_exAL_synth_DISC_uni$exps[1,idx]), col = 'lightgreen', lwd = 2)
lines(exp(new.theta.out_5_exAL_synth_DISC_uni$exps[1,idx]), col = "#4a235a", lwd = 2)

p <- 7

p_uni <- dim(new.theta.out_50_exAL_synth_DISC_uni$sm)[1]
alpha <- 0.01
for(i in (p+2):p_uni){
    # plot.ts(new.theta.out_95_exAL_synth_DISC_uni$sm[i,], ylim = c(0.0,0.1))
    # lines(new.theta.out_95_exAL_synth_DISC_uni$sm[i,]+qnorm(0.975)*sqrt(new.theta.out_95_exAL_synth_DISC_uni$sC[i,i,]))
    # lines(new.theta.out_95_exAL_synth_DISC_uni$sm[i,]+qnorm(0.025)*sqrt(new.theta.out_95_exAL_synth_DISC_uni$sC[i,i,]))
    l <- new.theta.out_50_exAL_synth_DISC_uni$sm[i,1]+qnorm(alpha/2)*sqrt(new.theta.out_95_exAL_synth_DISC_uni$sC[i,i,1])
    u <- new.theta.out_50_exAL_synth_DISC_uni$sm[i,1]+qnorm(1-alpha/2)*sqrt(new.theta.out_95_exAL_synth_DISC_uni$sC[i,i,1])
    m <- new.theta.out_50_exAL_synth_DISC_uni$sm[i,1]
    print(c(l,m,u))
}

p <- 7

for(i in 2:(ppx)){
    m <- new.theta.out_50_exAL_synth_DISC$sm[p*(J+1)+i,]
    E <- qnorm(0.975)*sqrt(new.theta.out_50_exAL_synth_DISC$sC[p*(J+1)+i,p*(J+1)+i,])
    plot.ts(m, ylim=c(-0.3,0.3), col='darkgreen')
    lines(m+E, col='darkgreen')
    lines(m-E, col='darkgreen')
    m <- new.theta.out_5_exAL_synth_DISC$sm[p*(J+1)+i,]
    E <- qnorm(0.975)*sqrt(new.theta.out_5_exAL_synth_DISC$sC[p*(J+1)+i,p*(J+1)+i,])
    lines(m, ylim=c(-0.3,0.3), col='darkred')
    lines(m+E, col='red')
    lines(m-E, col='red')
    m <- new.theta.out_95_exAL_synth_DISC$sm[p*(J+1)+i,]
    E <- qnorm(0.975)*sqrt(new.theta.out_95_exAL_synth_DISC$sC[p*(J+1)+i,p*(J+1)+i,])
    lines(m, ylim=c(-0.3,0.3), col='darkblue')
    lines(m+E, col='blue')
    lines(m-E, col='blue')
    abline(h = 0, col='gray')
}

# Load libraries (run if not already loaded)

flow_data <- data.frame(Date = timestamps, Flow = Y[1,])


# Flood stage values in feet
flood_stages_ft <- c(21.76, 16.5)^3
# Convert to centimeters
flood_stages_cm <- flood_stages_ft*CFSToCMS_CONVERSION_FACTOR 
# Apply log(log(x + 1)) transformation
flood_stages_trans <- log(log(flood_stages_cm + 1))

event_dates <- as.Date(c(
  "1998-02-03",  # February 1998 Flood
  "2004-06-01",  # Levee and Floodwall Reconstruction
  "2017-02-07",  # February 2017 Flood
  "2023-01-09"  # January 2023 Flood
))

event_numbers <- as.character(1:4)
event_color <- "#D95F02" # Orange for vertical lines & labels

# Calculate y position (10% above the observed max value for clarity)
label_y <- max(flow_data$Flow, na.rm = TRUE) + 0.1 * diff(range(flow_data$Flow, na.rm = TRUE))
# Flood stage labels for annotation
flood_stage_labels <- c("Major Flooding", "Minor Flooding")

# --- Your existing plotting code with new additions ---
p <- ggplot(flow_data, aes(x = Date, y = Flow)) +
  geom_line(color = "#238b45", linewidth = 0.7, alpha = 0.92) +
  geom_vline(xintercept = event_dates, color = event_color, linetype = "dashed", linewidth = 0.5) +
  annotate(
    "text",
    x = event_dates,
    y = rep(label_y, length(event_dates)),
    label = event_numbers,
    fontface = "bold",
    color = event_color,
    size = 4,
    vjust = 0,
    hjust = 2
  ) +
  # Add flood stage horizontal lines
  geom_hline(
    yintercept = flood_stages_trans,
    linetype = c("dashed", "dashed"),
    color = c("gray", "gray"),
    linewidth = 0.8
  ) +
  # Label the flood stages at the rightmost end of the plot
  annotate(
    "text",
    x = max(flow_data$Date),
    y = flood_stages_trans,
    label = flood_stage_labels,
    hjust = 10.5,
    vjust = -0.3,
    color = c("black", "black"),
    fontface = "italic",
    size = 3.5
  ) +
  labs(
    title = "Daily Flow of San Lorenzo River at Big Trees, CA",
    subtitle = "Measurements from May 29, 1987, to December 25, 2022",
    x = "Year",
    y = expression("Water Flow (Log-Log cm^3/s)")
  ) +
  scale_x_date(date_breaks = "5 years", date_labels = "%Y") +
  theme_minimal(base_size = 14) +
  theme(
    plot.title = element_text(size = 16, face = "bold", hjust = 0.5),
    plot.subtitle = element_text(size = 13, face = "italic", hjust = 0.5),
    axis.title = element_text(face = "bold"),
    panel.grid.minor = element_blank()
  )

print(p)

ggsave(
  filename = "/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics_reproduce/usgs.png",
  plot = p,
  width = 12,
  height = 6,
  units = "in",
  dpi = 900
)


# \caption{
# Daily log-log water flow (in cm$^3$/s) of the San Lorenzo River at the Big Trees USGS station from May 29, 1987 to December 25, 2022. The green curve shows the transformed daily flow. Vertical dashed lines and numbered labels mark key flood-related events: (1) February 1998 flood; (2) levee and floodwall reconstruction (2004); (3) February 2017 flood; (4) January 2023 flood. Horizontal dashed lines indicate official flood stages for the river, with the upper line corresponding to "Major Flooding" (21.76~ft, 663~cm) and the lower line to "Minor Flooding" (16.5~ft, 503~cm), both converted and displayed on the $\log(\log(x+1))$ scale. See the main text for further discussion of each event and flood stage threshold.
# }

series_colors <- c(
  "Precipitation" = "#1b9e77",    # green
  "Soil_Moisture" = "#386cb0",    # blue
  "Climate_PC1" = "#e6550d"       # orange
)

df_covariates <- data.frame(
  Date = as.Date(timestamps),
  Precipitation = X[, 1],
  Soil_Moisture = X[, 2],
  GDPC1 = X[, 3]
)
# 1. Select only relevant columns and rename for plotting clarity
df_plot <- df_covariates
colnames(df_plot) <- c("Date", "Precipitation", "Soil_Moisture", "Climate_PC1")

# 2. Convert to long format for ggplot (avoid slow pivot_longer)
df_long <- fast_long_by_row(
  mat = df_plot[, c("Precipitation", "Soil_Moisture", "Climate_PC1")],
  row_values = df_plot$Date,
  col_values = c("Precipitation", "Soil_Moisture", "Climate_PC1"),
  row_name = "Date",
  col_name = "Variable",
  value_name = "Value"
)


# Set Variable factor order
df_long$Variable <- factor(
  df_long$Variable,
  levels = c("Precipitation", "Soil_Moisture", "Climate_PC1")
)

# Custom labels for facets
custom_labels <- c(
  Precipitation = "Precipitation",
  Soil_Moisture = "Soil Moisture",
  Climate_PC1 = "1st Principal Comp."
)

# Facet plot with custom y-axis titles via `labeller`
p_facets <- ggplot(df_long, aes(x = Date, y = Value, color = Variable)) +
  geom_line(linewidth = 0.7, alpha = 0.9) +
  scale_color_manual(values = series_colors) +
  facet_wrap(
    ~Variable, ncol = 1, scales = "free_y", strip.position = "left",
    labeller = as_labeller(custom_labels)
  ) +
  labs(
    title = "Exogeneous Data (Scaled)",
    subtitle = "at Santa Cruz Area",
    x = "Year",
    y = NULL
  ) +
  scale_x_date(date_breaks = "5 years", date_labels = "%Y") +
  theme_minimal(base_size = 14) +
  theme(
    plot.title = element_text(size = 16, face = "bold", hjust = 0.5),
    plot.subtitle = element_text(size = 13, face = "italic", hjust = 0.5),
    axis.title.x = element_text(face = "bold"),
    axis.text = element_text(size = 12),
    strip.text = element_text(face = "bold", size = 13, color = "black"),
    strip.background = element_blank(),
    legend.position = "none",
    panel.grid.minor = element_blank()
  )

print(p_facets)

ggsave(
  filename = "/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics_reproduce/precip_soilmoisture_climatePC1_faceted_labeled.png",
  plot = p_facets,
  width = 12,
  height = 8,
  units = "in",
  dpi = 900
)




df_retro <- data.frame(
  Date = as.Date(timestamps),
  GloFAS = Y[2,],
  NWS = Y[3,]
)

# Reshape to long format for ggplot (avoid slow pivot_longer)
df_retro_long <- fast_long_by_row(
  mat = df_retro[, c("GloFAS", "NWS")],
  row_values = df_retro$Date,
  col_values = c("GloFAS", "NWS"),
  row_name = "Date",
  col_name = "Source",
  value_name = "Value"
)

# Set factor order for consistent legend/order
df_retro_long$Source <- factor(
  df_retro_long$Source,
  levels = c("GloFAS", "NWS")
)

# GloFAS panel (orange)
p_glofas <- ggplot(df_retro, aes(x = Date, y = GloFAS)) +
  geom_line(color = "#E67E22", linewidth = 0.7, alpha = 0.92) +
  labs(
    title = "GloFAS Retrospective Analysis",
    x = NULL,
    y = expression("Water Flow (Log-Log cm^3/s)")
  ) +
  scale_x_date(date_breaks = "5 years", date_labels = "%Y") +
  ylim(-2, 2) +
  theme_minimal(base_size = 14) +
  theme(
    plot.title = element_text(size = 15, face = "bold", hjust = 0.5),
    axis.title.y = element_text(face = "bold"),
    axis.text = element_text(size = 12),
    panel.grid.minor = element_blank()
  )

# NWS panel (purple)
p_nws <- ggplot(df_retro, aes(x = Date, y = NWS)) +
  geom_line(color = "#756bb1", linewidth = 0.7, alpha = 0.92) +
  labs(
    title = "NWS Retrospective Analysis",
    x = "Year",
    y = expression("Water Flow (Log-Log cm^3/s)")
  ) +
  scale_x_date(date_breaks = "5 years", date_labels = "%Y") +
  ylim(-3, 2) +
  theme_minimal(base_size = 14) +
  theme(
    plot.title = element_text(size = 15, face = "bold", hjust = 0.5),
    axis.title = element_text(face = "bold"),
    axis.text = element_text(size = 12),
    panel.grid.minor = element_blank()
  )

# Combine the two plots into a 2-row figure
p_combined <- p_glofas / p_nws + plot_layout(ncol = 1)

print(p_combined)

ggsave(
  filename = "/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics_reproduce/retrospective_log_discharge_plot_faceted.png",
  plot = p_combined,
  width = 12,
  height = 8,
  units = "in",
  dpi = 900
)




# 1. Filter USGS time series for plotting window
plot_start <- as.Date("2022-12-7")
plot_end <- as.Date("2023-01-22")

df_retro_plot <- df_retro_long %>%
  filter(Date >= plot_start & Date < as.Date("2022-12-26"))


usgs_plot_df <- San_Lorenzo_Daily_USGS_R %>%
  filter(time >= plot_start & time <= plot_end) %>%
  mutate(
    obs_type = ifelse(time >= as.Date("2022-12-26"), "After", "Before"),
    value = log(log(X_00060_00003 * CFSToCMS_CONVERSION_FACTOR + 1))
  )

# 2. Get GloFAS and NWS forecast dates
forecast_start <- as.Date("2022-12-26")
glofas_dates <- seq(forecast_start, by = "1 day", length.out = ranges[1])
nws_dates    <- seq(forecast_start, by = "1 day", length.out = ranges[2])

# Set color codes
glofas_color <- "#E67E22"   # Bright orange
nws_color    <- "#756bb1"   # Purple
usgs_green   <- "#238b45"   # Dark green (for line and early points)
"#B22222"  <- "#A8E063"   # Light green (for later points)

# USGS points
usgs_before_df <- usgs_plot_df %>% filter(obs_type == "Before") %>%
  mutate(Source = "USGS")
usgs_after_df  <- usgs_plot_df %>% filter(obs_type == "After") %>%
  mutate(Source = "USGS")
glofas_before_df <- df_retro_plot %>% filter(Source == "GloFAS")
nws_before_df    <- df_retro_plot %>% filter(Source == "NWS")
y_max <- max(
  usgs_before_df$value, 
  glofas_before_df$Value, 
  nws_before_df$Value, 
  usgs_after_df$value,
  na.rm = TRUE
)


p <- ggplot() +
  annotate(
    "text",
    x = max(usgs_plot_df$time),  # or max date of your plot
    y = flood_stages_trans,
    label = flood_stage_labels,
    hjust = 10.5,     # places label just to the right of the axis
    vjust = -0.5,
    color = c("black", "black"),
    fontface = "italic",
    size = 3.5
  ) +
  annotate(
    "text",
    x = as.Date("2022-12-25"),
    y = min(usgs_plot_df$value, na.rm = TRUE) - 0.15, # a bit below min y
    label = "Dec 25",
    color = "gray40",
	    size = 3.5,
	    fontface = "bold",
	    vjust = 4,
	    hjust = -0.1 
	  ) +

  # USGS before
    # Add flood stage horizontal lines
  geom_hline(
    yintercept = flood_stages_trans,
    linetype = c("dashed", "dashed"),
    color = c("gray", "gray"),
    linewidth = 0.8
  ) +
  geom_line(
    data = usgs_before_df, 
    aes(x = time, y = value, color = Source, linetype = Source), linewidth = 0.5
  ) +
  geom_point(
    data = usgs_before_df, 
    aes(x = time, y = value, color = Source, shape = Source), size = 1.4
  ) +
  # GloFAS before
  geom_line(
    data = glofas_before_df,
    aes(x = Date, y = Value, color = Source, linetype = Source), linewidth = 0.5, alpha = 0.85
  ) +
  geom_point(
    data = glofas_before_df,
    aes(x = Date, y = Value, color = Source, shape = Source), size = 1.4, alpha = 0.85
  ) +
  # NWS before
  geom_line(
    data = nws_before_df,
    aes(x = Date, y = Value, color = Source, linetype = Source), linewidth = 0.5, alpha = 0.85
  ) +
  geom_point(
    data = nws_before_df,
    aes(x = Date, y = Value, color = Source, shape = Source), size = 1.4, alpha = 0.85
  ) +
  # GloFAS ensembles after
  geom_line(
    data = fast_long_ensembles(ensembles[[1]], glofas_dates),
    aes(x = Date, y = value, group = member),
    color = glofas_color, alpha = 0.22, linewidth = 0.5, show.legend = FALSE
  ) +
  # NWS ensembles after
  geom_line(
    data = fast_long_ensembles(ensembles[[2]], nws_dates),
    aes(x = Date, y = value, group = member),
    color = nws_color, alpha = 0.22, linewidth = 0.5, show.legend = FALSE
  ) +
  # USGS after
  geom_line(
    data = usgs_after_df,
    aes(x = time, y = value), color = "#B22222", linewidth = 0.5, linetype = "dashed", show.legend = FALSE
  ) +
  geom_point(
    data = usgs_after_df,
    aes(x = time, y = value), color = "#B22222", size = 2, show.legend = FALSE
  ) +
  scale_x_date(breaks = pretty_breaks(6), date_labels = "%b %d") +
  scale_color_manual(
    name = "Data Source",
    values = c("USGS" = usgs_green, "GloFAS" = glofas_color, "NWS" = nws_color)
  ) +
  scale_linetype_manual(
    name = "Data Source",
    values = c("USGS" = "solid", "GloFAS" = "solid", "NWS" = "solid")
  ) +
  scale_shape_manual(
    name = "Data Source",
    values = c("USGS" = 16, "GloFAS" = 16, "NWS" = 16)
  ) +
  # Vertical dashed line at forecast start
geom_vline(
  xintercept = as.numeric(as.Date("2022-12-25")), 
  color = "gray40", linetype = "dashed", linewidth = 0.5, alpha = 0.8
) +
# Vertical dashed line at 2023 flood event
geom_vline(
  xintercept = as.numeric(as.Date("2023-01-09")),
  color = "#4a235a", linetype = "dashed", linewidth = 0.5, alpha = 0.8
) +

annotate(
  "text",
  x = as.Date("2023-01-09"),
  y = min(usgs_plot_df$value, na.rm = TRUE) - 0.15,
  label = "Jan 9: Flood",
  color = "#4a235a",
  vjust = 4,
  hjust = -0.1,
  fontface = "bold",
  size = 3.5
) +

labs(
  title = "Observed and Retrospective River Flow\nwith GloFAS and NWS Forecast Ensembles",
  x = "Date (2022-2023)",
  y = expression("Water Flow (Log-Log cm^3/s)")
) +
  guides(
    color = guide_legend(override.aes = list(size = 2)),
    shape = guide_legend(override.aes = list(size = 3))
  ) +
  theme_minimal(base_size = 14) +
  theme(
    plot.title = element_text(size = 16, face = "bold", hjust = 0.5),
    plot.subtitle = element_text(size = 12, face = "italic", hjust = 0.5, margin = margin(b = 8)),
    axis.title = element_text(face = "bold"),
    legend.position = "top",
    legend.title = element_text(face = "bold"),
    panel.grid.minor = element_blank()
  )

print(p)

ggsave(
  filename = "/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics_reproduce/forecats.png",
  plot = p,
  width = 12,
  height = 6,
  units = "in",
  dpi = 900
)


  # subtitle = paste(
  #   "Forecasts initiated Dec 26, 2022 (dashed vertical line).",
  #   "\nUSGS (green), GloFAS (orange), and NWS (purple)",
  #   "\nare shown with points and thin lines before the forecast.",
  #   sep = ""
  # ),

idx <- idx_sub


# 1. Dates for fit and forecast
fit_dates <- as.Date(timestamps[idx])
forecast_dates <- seq(fit_dates[length(fit_dates)] + 1, by = "1 day", length.out = ranges[1])

# 2. Posterior samples, tidy for ggplot (long format; avoid pivot_longer)
df_post_fit <- fast_long_by_row(
  mat = synth,
  row_values = seq_len(nrow(synth)),
  col_values = fit_dates,
  row_name = "sample",
  col_name = "Date",
  value_name = "Value"
)
df_post_fit$Type <- "Fit"

df_post_forecast <- fast_long_by_row(
  mat = synth_f,
  row_values = seq_len(nrow(synth_f)),
  col_values = forecast_dates,
  row_name = "sample",
  col_name = "Date",
  value_name = "Value"
)
df_post_forecast$Type <- "Forecast"

df_post <- bind_rows(df_post_fit, df_post_forecast)

# 3. Quantile curves (avoid pivot_longer)
df_q_fit <- fast_long_by_row(
  mat = synth_q,
  row_values = seq_len(nrow(synth_q)),
  col_values = fit_dates,
  row_name = "quantile",
  col_name = "Date",
  value_name = "Value"
)
df_q_fit$Type <- "Fit"

df_q_forecast <- fast_long_by_row(
  mat = synth_f_q,
  row_values = seq_len(nrow(synth_f_q)),
  col_values = forecast_dates,
  row_name = "quantile",
  col_name = "Date",
  value_name = "Value"
)
df_q_forecast$Type <- "Forecast"

df_q <- bind_rows(df_q_fit, df_q_forecast)

# 4. Observed values for USGS
obs_df <- usgs_plot_df %>% 
  mutate(Source = "USGS", colgroup = ifelse(obs_type == "After", "After", "Before"))

p_post <- ggplot() +
  # Flood stage lines and labels
  geom_hline(
    yintercept = flood_stages_trans,
    linetype = "dashed",
    color = "gray",
    linewidth = 0.8
  ) +
    annotate(
    "text",
    x = as.Date("2022-12-25"),
    y = min(usgs_plot_df$value, na.rm = TRUE) - 0.15, # a bit below min y
    label = "Dec 25",
    color = "gray40",
    size = 3.5,
    fontface = "bold",
    vjust = 4,
    hjust = -0.1 
  ) +
  annotate(
    "text",
    x = max(obs_df$time),
    y = flood_stages_trans,
    label = flood_stage_labels,
    hjust = 10.5,
    vjust = -0.5,
    color = "black",
    fontface = "italic",
    size = 3.5
  ) +
  # Vertical lines for forecast init and flood
  geom_vline(
    xintercept = as.numeric(as.Date("2022-12-25")), 
    color = "gray40", linetype = "dashed", linewidth = 0.5, alpha = 0.8
  ) +
  geom_vline(
    xintercept = as.numeric(as.Date("2023-01-09")),
    color = "#4a235a", linetype = "dashed", linewidth = 0.5, alpha = 0.8
  ) +
  annotate(
    "text",
    x = as.Date("2023-01-09"),
    y = min(usgs_plot_df$value, na.rm = TRUE) - 0.15,
    label = "Jan 9: Flood",
    color = "#4a235a",
    vjust = 4,
    hjust = -0.1,
    fontface = "bold",
    size = 3.5
  ) +
  # Posterior samples ("spaghetti")
  geom_line(
    data = df_post, 
    aes(x = Date, y = log(Value), group = interaction(Type, sample)), 
    color = "pink", linewidth = 0.15, alpha = 0.15
  ) +
  # Posterior quantile curves (thinner black lines)
  geom_line(
    data = df_q, 
    aes(x = Date, y = log(Value), group = interaction(Type, quantile)), 
    color = "black", linewidth = 0.1
  ) +
  # USGS obs: before forecast
  geom_point(
    data = obs_df %>% filter(colgroup == "Before"), 
    aes(x = time, y = (value)), 
    color = usgs_green, size = 1.5
  ) +
  # USGS obs: after forecast (light green)
  geom_point(
    data = obs_df %>% filter(colgroup == "After"), 
    aes(x = time, y = (value)), 
    color = "#B22222", size = 2
  ) +
  geom_line(
    data = obs_df %>% filter(colgroup == "Before"),
    aes(x = time, y = (value)), color = usgs_green, linewidth = 0.5
  ) +
  geom_line(
    data = obs_df %>% filter(colgroup == "After"),
    aes(x = time, y = (value)), color = "#B22222", linewidth = 0.5, linetype = "dashed"
  ) +
  ############################
# GloFAS before (gray)
geom_line(
  data = glofas_before_df,
  aes(x = Date, y = Value, linetype = Source),
  color = "gray", linewidth = 0.5, alpha = 0.85
) +
geom_point(
  data = glofas_before_df,
  aes(x = Date, y = Value, shape = Source),
  color = "gray", size = 1.4, alpha = 0.85
) +
# NWS before (gray)
geom_line(
  data = nws_before_df,
  aes(x = Date, y = Value, linetype = Source),
  color = "gray", linewidth = 0.5, alpha = 0.85
) +
geom_point(
  data = nws_before_df,
  aes(x = Date, y = Value, shape = Source),
  color = "gray", size = 1.4, alpha = 0.85
) +
# GloFAS ensembles after (gray)
geom_line(
  data = fast_long_ensembles(ensembles[[1]], glofas_dates),
  aes(x = Date, y = value, group = member),
  color = "gray", alpha = 0.22, linewidth = 0.5, show.legend = FALSE
) +
# NWS ensembles after (gray)
geom_line(
  data = fast_long_ensembles(ensembles[[2]], nws_dates),
  aes(x = Date, y = value, group = member),
  color = "gray", alpha = 0.22, linewidth = 0.5, show.legend = FALSE
) +
  coord_cartesian(ylim = c(-1, 3.5)) +
  ############################
  scale_x_date(breaks = pretty_breaks(6), date_labels = "%b %d") +
  labs(
    title = "Posterior Predictive Samples and Quantiles\nwith USGS Observed Flow",
    x = "Date (2022-2023)",
    y = expression("Water Flow (Log-Log cm^3/s)")
  ) +
  theme_minimal(base_size = 14) +
  theme(
    plot.title = element_text(size = 16, face = "bold", hjust = 0.5),
    axis.title = element_text(face = "bold"),
    legend.position = "none",
    panel.grid.minor = element_blank()
  )

print(p_post)

ggsave(
  filename = "/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics_reproduce/posterior_samples.png",
  plot = p_post,
  width = 12,
  height = 6,
  units = "in",
  dpi = 900
)



# Dates for fit (historical) and forecast
fit_dates <- as.Date(timestamps[idx])
forecast_dates <- seq(fit_dates[length(fit_dates)] + 1, by = "1 day", length.out = ranges[1])

# 1. Posterior samples: historical (fit) and forecast (avoid pivot_longer)
df_post_fit <- fast_long_by_row(
  mat = log(synth_hist_uni),
  row_values = seq_len(nrow(synth_hist_uni)),
  col_values = fit_dates,
  row_name = "sample",
  col_name = "Date",
  value_name = "Value"
)
df_post_fit$Type <- "Fit"

df_post_forecast <- fast_long_by_row(
  mat = log(synth_f2),
  row_values = seq_len(nrow(synth_f2)),
  col_values = forecast_dates,
  row_name = "sample",
  col_name = "Date",
  value_name = "Value"
)
df_post_forecast$Type <- "Forecast"

df_post <- bind_rows(df_post_fit, df_post_forecast)

# 2. Quantile curves: historical (fit) and forecast (avoid pivot_longer)
df_q_fit <- fast_long_by_row(
  mat = log(synth_hist_uni_q),
  row_values = seq_len(nrow(synth_hist_uni_q)),
  col_values = fit_dates,
  row_name = "quantile",
  col_name = "Date",
  value_name = "Value"
)
df_q_fit$Type <- "Fit"

df_q_forecast <- fast_long_by_row(
  mat = log(synth_f2_q),
  row_values = seq_len(nrow(synth_f2_q)),
  col_values = forecast_dates,
  row_name = "quantile",
  col_name = "Date",
  value_name = "Value"
)
df_q_forecast$Type <- "Forecast"

df_q <- bind_rows(df_q_fit, df_q_forecast)

# 3. Observed values for USGS
obs_df <- usgs_plot_df %>% 
  mutate(Source = "USGS", colgroup = ifelse(obs_type == "After", "After", "Before"))

# 4. Plot (as before, no need to change this part except color for 'After' points/lines)
p_post <- ggplot() +
  # Vertical lines for forecast init and flood
  geom_vline(
    xintercept = as.numeric(as.Date("2022-12-25")), 
    color = "gray40", linetype = "dashed", linewidth = 0.5, alpha = 0.8
  ) +
  # Posterior samples
  geom_line(
    data = df_post, 
    aes(x = Date, y = Value, group = interaction(Type, sample)), 
    color = "pink", linewidth = 0.15, alpha = 0.15
  ) +
  # Posterior quantile curves
  geom_line(
    data = df_q, 
    aes(x = Date, y = Value, group = interaction(Type, quantile)), 
    color = "black", linewidth = 0.1
  ) +
  # USGS obs: before forecast
  geom_point(
    data = obs_df %>% filter(colgroup == "Before"), 
    aes(x = time, y = (value)), 
    color = usgs_green, size = 1.5
  ) +
  # USGS obs: after forecast (DARK RED)
  geom_point(
    data = obs_df %>% filter(colgroup == "After"), 
    aes(x = time, y = (value)), 
    color = "#B22222", size = 2
  ) +
  geom_line(
    data = obs_df %>% filter(colgroup == "Before"),
    aes(x = time, y = (value)), color = usgs_green, linewidth = 0.5
  ) +
  geom_line(
    data = obs_df %>% filter(colgroup == "After"),
    aes(x = time, y = (value)), color = "#B22222", linewidth = 0.5, linetype = "dashed"
  ) +
  geom_vline(
    xintercept = as.numeric(as.Date("2023-01-09")),
    color = "#4a235a", linetype = "dashed", linewidth = 0.5, alpha = 0.8
  ) +
  # Flood stage lines and labels
  geom_hline(
    yintercept = flood_stages_trans,
    linetype = "dashed",
    color = "gray",
    linewidth = 0.8
  ) +
    coord_cartesian(ylim = c(-1, 3.5)) +
  annotate(
    "text",
    x = max(obs_df$time),
    y = flood_stages_trans,
    label = flood_stage_labels,
    hjust = 10.5,
    vjust = -0.5,
    color = "black",
    fontface = "italic",
    size = 3.5
  ) +
    annotate(
    "text",
    x = as.Date("2022-12-25"),
    y = min(usgs_plot_df$value, na.rm = TRUE) - 0.15, # a bit below min y
    label = "Dec 25",
    color = "gray40",
    size = 3.5,
    fontface = "bold",
    vjust = 4,
    hjust = -0.1 
  ) +
  annotate(
    "text",
    x = as.Date("2023-01-09"),
    y = min(usgs_plot_df$value, na.rm = TRUE) - 0.15,
    label = "Jan 9: Flood",
    color = "#4a235a",
    vjust = 4,
    hjust = -0.1,
    fontface = "bold",
    size = 3.5
  ) +
  ############################
  scale_x_date(breaks = pretty_breaks(6), date_labels = "%b %d") +
  labs(
    title = "Posterior Predictive Samples and Quantiles\nwith USGS Observed Flow",
    x = "Date (2022-2023)",
    y = expression("Water Flow (Log-Log cm^3/s)")
  ) +
  theme_minimal(base_size = 14) +
  theme(
    plot.title = element_text(size = 16, face = "bold", hjust = 0.5),
    axis.title = element_text(face = "bold"),
    legend.position = "none",
    panel.grid.minor = element_blank()
  )

print(p_post)

ggsave(
  filename = "/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics_reproduce/posterior_samples_counter.png",
  plot = p_post,
  width = 12,
  height = 6,
  units = "in",
  dpi = 900
)


# -- 1. Prepare Data --
# Flood stage values in feet
flood_stages_ft <- c(21.76, 16.5)^3
# Convert to centimeters
flood_stages_cm <- flood_stages_ft*CFSToCMS_CONVERSION_FACTOR 
# Apply log(log(x + 1)) transformation
flood_stages_trans <- log(log(flood_stages_cm + 1))

idx <- time_cuts[3]:time_cuts[4]
dates <- as.Date(dates_ts_usgs[idx])         # Dates for plotting window
percentiles <- c(0.025, 0.5, 0.975)

# Helper: Extract quantile trajectory for a given quantile
get_quantile_trajectory <- function(arr, qidx, dates, idx, quantile_name) {
  mat <- arr[qidx, idx, , drop = FALSE]
  mat <- matrix(mat, nrow = length(idx), ncol = dim(arr)[3])
  qt_res <- t(fast_row_quantiles_t(mat, probs = percentiles))
  colnames(qt_res) <- c("Lower", "Median", "Upper")
  data.frame(
    Date = dates,
    Quantile = quantile_name,
    Lower = qt_res[, "Lower"],
    Median = qt_res[, "Median"],
    Upper = qt_res[, "Upper"]
  )
}

# Map quantile names to their index in the first dimension
quantiles_map <- list(
  "5th"  = 1,
  "20th" = 2,
  "35th" = 3,
  "50th" = 4,
  "65th" = 5,
  "80th" = 6,
  "95th" = 7
)

# -- 2. All quantile trajectories --
quant_df_list <- lapply(names(quantiles_map), function(qname) {
  qidx <- quantiles_map[[qname]]
  get_quantile_trajectory(xbs_retro, qidx, dates, idx, qname)
})
quant_df <- bind_rows(quant_df_list)

# -- 3. Observed USGS series --
obs_df <- data.frame(
  Date = dates,
  Value = Y[1, idx]
)

flood_lines <- data.frame(
  y = flood_stages_trans,
  Stage = paste0(lev_flood, " ft")
)

alpha_val <- 0.11
# -- 5. Plot: Publication-Ready --
p <- ggplot() +
    annotate(
    "text",
    x =  max(as.Date(dates_ts_usgs[idx])),
    y = flood_stages_trans,
    label = flood_stage_labels,
    hjust = 10.5,
    vjust = -0.5,
    color = "black",
    fontface = "italic",
    size = 3.5
  ) +
  # Flood reference lines
  geom_hline(
    data = flood_lines,
    aes(yintercept = y), linetype = "dashed", color = "gray50", linewidth = 0.6
  ) +
  # 95th quantile (blue, ribbon)
  geom_ribbon(
    data = quant_df %>% filter(Quantile == "95th"),
    aes(x = Date, ymin = Lower, ymax = Upper),
    fill = "#2171b5", alpha = alpha_val
  ) +
  geom_line(
    data = quant_df %>% filter(Quantile == "95th"),
    aes(x = Date, y = Median), color = "#2171b5", linewidth = 0.2
  ) +
  geom_line(
    data = quant_df %>% filter(Quantile == "95th"),
    aes(x = Date, y = Lower), color = "blue", linewidth = 0.05
  ) +
  geom_line(
    data = quant_df %>% filter(Quantile == "95th"),
    aes(x = Date, y = Upper), color = "blue", linewidth = 0.05
  ) +
  # 5th quantile (red, ribbon)
  geom_ribbon(
    data = quant_df %>% filter(Quantile == "5th"),
    aes(x = Date, ymin = Lower, ymax = Upper),
    fill = "#b2182b", alpha = alpha_val
  ) +
  geom_line(
    data = quant_df %>% filter(Quantile == "5th"),
    aes(x = Date, y = Median), color = "#b2182b", linewidth = 0.2
  ) +
  geom_line(
    data = quant_df %>% filter(Quantile == "5th"),
    aes(x = Date, y = Lower), color = "red", linewidth = 0.05
  ) +
  geom_line(
    data = quant_df %>% filter(Quantile == "5th"),
    aes(x = Date, y = Upper), color = "red", linewidth = 0.05
  ) +
  # 50th quantile (green, ribbon)
  geom_ribbon(
    data = quant_df %>% filter(Quantile == "50th"),
    aes(x = Date, ymin = Lower, ymax = Upper),
    fill = "#238b45", alpha = alpha_val
  ) +
  geom_line(
    data = quant_df %>% filter(Quantile == "50th"),
    aes(x = Date, y = Median), color = "#238b45", linewidth = 0.2
  ) +
  geom_line(
    data = quant_df %>% filter(Quantile == "50th"),
    aes(x = Date, y = Lower), color = "green", linewidth = 0.05
  ) +
  geom_line(
    data = quant_df %>% filter(Quantile == "50th"),
    aes(x = Date, y = Upper), color = "green", linewidth = 0.05
  ) +
  # Observed series (black, line and points)
  geom_point(
    data = obs_df, aes(x = Date, y = Value),
    color = "black", size = 0.2
  ) +
  geom_line(
    data = obs_df, aes(x = Date, y = Value),
    color = "black", linewidth = 0.1
  ) +
  labs(
    title = "Quantile Dynamics: 2017–2019",
    x = NULL,
    y = expression("Water Flow (Log-Log cm^3/s)")
  ) +
  scale_x_date(date_breaks = "6 months", date_labels = "%Y-%m") +
  coord_cartesian(ylim = c(-2, 3)) +
  theme_minimal(base_size = 14) +
  theme(
    plot.title = element_text(size = 15, face = "bold", hjust = 0.5),
    axis.title = element_text(face = "bold"),
    panel.grid.minor = element_blank()
  )

print(p)

# Save if desired
ggsave(
  filename = "/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics_reproduce/All_exal_2017-2019_DISC.png",
  plot = p, width = 12, height = 6, units = "in", dpi = 900
)



# -- 1. Prepare Data --
# Flood stage values in feet
flood_stages_ft <- c(21.76, 16.5)^3
# Convert to centimeters
flood_stages_cm <- flood_stages_ft*CFSToCMS_CONVERSION_FACTOR 
# Apply log(log(x + 1)) transformation
flood_stages_trans <- log(log(flood_stages_cm + 1))

idx <- time_cuts[1]:time_cuts[2]
dates <- as.Date(dates_ts_usgs[idx])         # Dates for plotting window
percentiles <- c(0.025, 0.5, 0.975)

# Helper: Extract quantile trajectory for a given quantile
get_quantile_trajectory <- function(arr, qidx, dates, idx, quantile_name) {
  mat <- arr[qidx, idx, , drop = FALSE]
  mat <- matrix(mat, nrow = length(idx), ncol = dim(arr)[3])
  qt_res <- t(fast_row_quantiles_t(mat, probs = percentiles))
  colnames(qt_res) <- c("Lower", "Median", "Upper")
  data.frame(
    Date = dates,
    Quantile = quantile_name,
    Lower = qt_res[, "Lower"],
    Median = qt_res[, "Median"],
    Upper = qt_res[, "Upper"]
  )
}

# Map quantile names to their index in the first dimension
quantiles_map <- list(
  "5th"  = 1,
  "20th" = 2,
  "35th" = 3,
  "50th" = 4,
  "65th" = 5,
  "80th" = 6,
  "95th" = 7
)

# -- 2. All quantile trajectories --
quant_df_list <- lapply(names(quantiles_map), function(qname) {
  qidx <- quantiles_map[[qname]]
  get_quantile_trajectory(xbs_retro, qidx, dates, idx, qname)
})
quant_df <- bind_rows(quant_df_list)

# -- 3. Observed USGS series --
obs_df <- data.frame(
  Date = dates,
  Value = Y[1, idx]
)

flood_lines <- data.frame(
  y = flood_stages_trans,
  Stage = paste0(lev_flood, " ft")
)

alpha_val <- 0.11
# -- 5. Plot: Publication-Ready --
p <- ggplot() +
    annotate(
    "text",
    x =  max(as.Date(dates_ts_usgs[idx])),
    y = flood_stages_trans,
    label = flood_stage_labels,
    hjust = 10.5,
    vjust = -0.5,
    color = "black",
    fontface = "italic",
    size = 3.5
  ) +
  # Flood reference lines
  geom_hline(
    data = flood_lines,
    aes(yintercept = y), linetype = "dashed", color = "gray50", linewidth = 0.6
  ) +
  # 95th quantile (blue, ribbon)
  geom_ribbon(
    data = quant_df %>% filter(Quantile == "95th"),
    aes(x = Date, ymin = Lower, ymax = Upper),
    fill = "#2171b5", alpha = alpha_val
  ) +
  geom_line(
    data = quant_df %>% filter(Quantile == "95th"),
    aes(x = Date, y = Median), color = "#2171b5", linewidth = 0.2
  ) +
  geom_line(
    data = quant_df %>% filter(Quantile == "95th"),
    aes(x = Date, y = Lower), color = "blue", linewidth = 0.05
  ) +
  geom_line(
    data = quant_df %>% filter(Quantile == "95th"),
    aes(x = Date, y = Upper), color = "blue", linewidth = 0.05
  ) +
  # 5th quantile (red, ribbon)
  geom_ribbon(
    data = quant_df %>% filter(Quantile == "5th"),
    aes(x = Date, ymin = Lower, ymax = Upper),
    fill = "#b2182b", alpha = alpha_val
  ) +
  geom_line(
    data = quant_df %>% filter(Quantile == "5th"),
    aes(x = Date, y = Median), color = "#b2182b", linewidth = 0.2
  ) +
  geom_line(
    data = quant_df %>% filter(Quantile == "5th"),
    aes(x = Date, y = Lower), color = "red", linewidth = 0.05
  ) +
  geom_line(
    data = quant_df %>% filter(Quantile == "5th"),
    aes(x = Date, y = Upper), color = "red", linewidth = 0.05
  ) +
  # 50th quantile (green, ribbon)
  geom_ribbon(
    data = quant_df %>% filter(Quantile == "50th"),
    aes(x = Date, ymin = Lower, ymax = Upper),
    fill = "#238b45", alpha = alpha_val
  ) +
  geom_line(
    data = quant_df %>% filter(Quantile == "50th"),
    aes(x = Date, y = Median), color = "#238b45", linewidth = 0.2
  ) +
  geom_line(
    data = quant_df %>% filter(Quantile == "50th"),
    aes(x = Date, y = Lower), color = "green", linewidth = 0.05
  ) +
  geom_line(
    data = quant_df %>% filter(Quantile == "50th"),
    aes(x = Date, y = Upper), color = "green", linewidth = 0.05
  ) +
  # Observed series (black, line and points)
  geom_point(
    data = obs_df, aes(x = Date, y = Value),
    color = "black", size = 0.2
  ) +
  geom_line(
    data = obs_df, aes(x = Date, y = Value),
    color = "black", linewidth = 0.1
  ) +
  labs(
    title = "Quantile Dynamics: 2012–2016",
    x = NULL,
    y = expression("Water Flow (Log-Log cm^3/s)")
  ) +
  scale_x_date(date_breaks = "6 months", date_labels = "%Y-%m") +
  coord_cartesian(ylim = c(-2, 3)) +
  theme_minimal(base_size = 14) +
  theme(
    plot.title = element_text(size = 15, face = "bold", hjust = 0.5),
    axis.title = element_text(face = "bold"),
    panel.grid.minor = element_blank()
  )

print(p)

# Save if desired
ggsave(
  filename = "/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics_reproduce/All_exal_2012-2016_DISC.png",
  plot = p, width = 12, height = 6, units = "in", dpi = 900
)



# -- 1. Prepare Data --
# Flood stage values in feet
flood_stages_ft <- c(21.76, 16.5)^3
# Convert to centimeters
flood_stages_cm <- flood_stages_ft*CFSToCMS_CONVERSION_FACTOR 
# Apply log(log(x + 1)) transformation
flood_stages_trans <- log(log(flood_stages_cm + 1))

idx <- time_cuts[1]:time_cuts[2]
dates <- as.Date(dates_ts_usgs[idx])         # Dates for plotting window
percentiles <- c(0.025, 0.5, 0.975)

# Helper: Extract quantile trajectory for a given quantile
get_quantile_trajectory <- function(arr, qidx, dates, idx, quantile_name) {
  mat <- arr[qidx, idx, , drop = FALSE]
  mat <- matrix(mat, nrow = length(idx), ncol = dim(arr)[3])
  qt_res <- t(fast_row_quantiles_t(mat, probs = percentiles))
  colnames(qt_res) <- c("Lower", "Median", "Upper")
  data.frame(
    Date = dates,
    Quantile = quantile_name,
    Lower = qt_res[, "Lower"],
    Median = qt_res[, "Median"],
    Upper = qt_res[, "Upper"]
  )
}

# Map quantile names to their index in the first dimension
quantiles_map <- list(
  "5th"  = 1,
  "20th" = 2,
  "35th" = 3,
  "50th" = 4,
  "65th" = 5,
  "80th" = 6,
  "95th" = 7
)

# -- 2. All quantile trajectories --
quant_df_list <- lapply(names(quantiles_map), function(qname) {
  qidx <- quantiles_map[[qname]]
  get_quantile_trajectory(xbs_retro, qidx, dates, idx, qname)
})
quant_df <- bind_rows(quant_df_list)

# -- 3. Observed USGS series --
obs_df1 <- data.frame(
  Date = dates,
  Value = Y[1, idx]
)
obs_df2 <- data.frame(
  Date = dates,
  Value = Y[2, idx]
)
obs_df3 <- data.frame(
  Date = dates,
  Value = Y[3, idx]
)
flood_lines <- data.frame(
  y = flood_stages_trans,
  Stage = paste0(lev_flood, " ft")
)

alpha_val <- 0.11
# -- 5. Plot: Publication-Ready --
p <- ggplot() +
    annotate(
    "text",
    x =  max(as.Date(dates_ts_usgs[idx])),
    y = flood_stages_trans,
    label = flood_stage_labels,
    hjust = 10.5,
    vjust = -0.5,
    color = "black",
    fontface = "italic",
    size = 3.5
  ) +
  # Flood reference lines
  geom_hline(
    data = flood_lines,
    aes(yintercept = y), linetype = "dashed", color = "gray50", linewidth = 0.6
  ) +
  # 95th quantile (blue, ribbon)
  geom_ribbon(
    data = quant_df %>% filter(Quantile == "95th"),
    aes(x = Date, ymin = Lower, ymax = Upper),
    fill = "#2171b5", alpha = alpha_val
  ) +
  geom_line(
    data = quant_df %>% filter(Quantile == "95th"),
    aes(x = Date, y = Median), color = "#2171b5", linewidth = 0.2
  ) +
  geom_line(
    data = quant_df %>% filter(Quantile == "95th"),
    aes(x = Date, y = Lower), color = "blue", linewidth = 0.05
  ) +
  geom_line(
    data = quant_df %>% filter(Quantile == "95th"),
    aes(x = Date, y = Upper), color = "blue", linewidth = 0.05
  ) +
  # 5th quantile (red, ribbon)
  geom_ribbon(
    data = quant_df %>% filter(Quantile == "5th"),
    aes(x = Date, ymin = Lower, ymax = Upper),
    fill = "#b2182b", alpha = alpha_val
  ) +
  geom_line(
    data = quant_df %>% filter(Quantile == "5th"),
    aes(x = Date, y = Median), color = "#b2182b", linewidth = 0.2
  ) +
  geom_line(
    data = quant_df %>% filter(Quantile == "5th"),
    aes(x = Date, y = Lower), color = "red", linewidth = 0.05
  ) +
  geom_line(
    data = quant_df %>% filter(Quantile == "5th"),
    aes(x = Date, y = Upper), color = "red", linewidth = 0.05
  ) +
  # 50th quantile (green, ribbon)
  geom_ribbon(
    data = quant_df %>% filter(Quantile == "50th"),
    aes(x = Date, ymin = Lower, ymax = Upper),
    fill = "#238b45", alpha = alpha_val
  ) +
  geom_line(
    data = quant_df %>% filter(Quantile == "50th"),
    aes(x = Date, y = Median), color = "#238b45", linewidth = 0.2
  ) +
  geom_line(
    data = quant_df %>% filter(Quantile == "50th"),
    aes(x = Date, y = Lower), color = "green", linewidth = 0.05
  ) +
  geom_line(
    data = quant_df %>% filter(Quantile == "50th"),
    aes(x = Date, y = Upper), color = "green", linewidth = 0.05
  ) +
  # Observed series (black, line and points)
  geom_point(
    data = obs_df1, aes(x = Date, y = Value),
    color = "black", size = 0.1
  ) +
  geom_line(
    data = obs_df1, aes(x = Date, y = Value),
    color = "black", linewidth = 0.05
  ) +
  # Observed series (black, line and points)
  geom_point(
    data = obs_df2, aes(x = Date, y = Value),
    color = "purple", size = 0.1
  ) +
  geom_line(
    data = obs_df2, aes(x = Date, y = Value),
    color = "purple", linewidth = 0.05
  ) +
  # Observed series (black, line and points)
  geom_point(
    data = obs_df3, aes(x = Date, y = Value), 
    color = "orange", size = 0.1
  ) +
  geom_line(
    data = obs_df3, aes(x = Date, y = Value),
    color = "orange", linewidth = 0.05
  ) +
  labs(
    title = "Quantile Dynamics: 2012–2016",
    x = NULL,
    y = expression("Water Flow (Log-Log cm^3/s)")
  ) +
  scale_x_date(date_breaks = "6 months", date_labels = "%Y-%m") +
  coord_cartesian(ylim = c(-3, 2)) +
  theme_minimal(base_size = 14) +
  theme(
    plot.title = element_text(size = 15, face = "bold", hjust = 0.5),
    axis.title = element_text(face = "bold"),
    panel.grid.minor = element_blank()
  )

print(p)

# # Save if desired
# ggsave(
#   filename = "/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics_reproduce/All_exal_2012-2016_DISC.png",
#   plot = p, width = 12, height = 6, units = "in", dpi = 900
# )



# -- Helper: Build tidy data for a single component --
build_quantile_df <- function(q_array, component, idx, date_vec, quantile_label) {
  # q_array: [component, time, quant] where quant 1=lower, 2=median, 3=upper
  tibble(
    Date    = as.Date(date_vec[idx]),
    Lower   = q_array[component, idx, 1],
    Median  = q_array[component, idx, 2],
    Upper   = q_array[component, idx, 3],
    Quantile = quantile_label
  )
}

# -- All quantile ribbons in one tidy dataframe --
make_component_df <- function(component, idx, date_vec,
                             q_d_50, q_d_05, q_d_95) {
  bind_rows(
    build_quantile_df(q_d_50, component, idx, date_vec, "50th"),
    build_quantile_df(q_d_05, component, idx, date_vec, "5th"),
    build_quantile_df(q_d_95, component, idx, date_vec, "95th")
  )
}

# Example: For component 1
component <- 1
comp_df <- make_component_df(component, idx, dates_ts_usgs, q_d_50, q_d_05, q_d_95)

# Observed series for this component (customize as needed per component)
obs_vec <- if (component == 1) Y[1, idx] else Y[2, idx] - Y[1, idx] # Example
obs_df <- tibble(Date = as.Date(dates_ts_usgs[idx]), Value = obs_vec)


plot_component_quantiles <- function(
    comp_df, obs_df,
    ylab = "log-flow",
    title = "Component",
    ylim = c(-2.5, 2.5),
    filename = NULL,
    time_cuts = NULL,          # pass the time_cuts vector!
    dates_ts_usgs = NULL       # pass the dates vector!
) {
  # --- 1. Shade periods setup ---
  if (is.null(time_cuts) | is.null(dates_ts_usgs)) stop("Provide time_cuts and dates_ts_usgs!")

  shade_periods <- tibble(
    xmin = as.Date(dates_ts_usgs[time_cuts[c(1, 3)]]),
    xmax = as.Date(dates_ts_usgs[time_cuts[c(2, 4)]]),
    period = c("Dry", "Rainy"),
    fill = c("#ffeead", "#c9e4f6")  # pastel yellow, pastel blue
  )

  # --- 2. Colors (as before) ---
  col_50  <- "#238b45"; band_50 <- "#b2df8a"
  col_05  <- "#b2182b"; band_05 <- "#fdbba1"
  col_95  <- "#2171b5"; band_95 <- "#a6bddb"
  obs_line <- "#222222"; obs_point <- "#222222"
  ribbon_alpha <- 0.11; lnn <- 0.4

  # --- 3. Compose plot ---
  p <- ggplot() +
    # --- Shaded regions ---
    geom_rect(
      data = shade_periods,
      aes(xmin = xmin, xmax = xmax, ymin = -Inf, ymax = Inf, fill = period),
      alpha = 0.6, inherit.aes = FALSE, show.legend = FALSE
    ) +
    scale_fill_manual(values = setNames(shade_periods$fill, shade_periods$period)) +
    # --- Bands: Light, desaturated color ---
    geom_ribbon(data = comp_df %>% filter(Quantile == "50th"),
      aes(x = Date, ymin = Lower, ymax = Upper),
      fill = band_50, alpha = ribbon_alpha) +
    geom_ribbon(data = comp_df %>% filter(Quantile == "5th"),
      aes(x = Date, ymin = Lower, ymax = Upper),
      fill = band_05, alpha = ribbon_alpha) +
    geom_ribbon(data = comp_df %>% filter(Quantile == "95th"),
      aes(x = Date, ymin = Lower, ymax = Upper),
      fill = band_95, alpha = ribbon_alpha) +
    # --- Median/Quantile lines ---
    geom_line(data = comp_df %>% filter(Quantile == "50th"),
      aes(x = Date, y = Median), color = col_50, linewidth = lnn) +
    geom_line(data = comp_df %>% filter(Quantile == "5th"),
      aes(x = Date, y = Median), color = col_05, linewidth = lnn) +
    geom_line(data = comp_df %>% filter(Quantile == "95th"),
      aes(x = Date, y = Median), color = col_95, linewidth = lnn) +
    # --- Dashed, thin quantile CI boundaries ---
    geom_line(data = comp_df %>% filter(Quantile == "50th"),
      aes(x = Date, y = Lower), color = "green", linewidth = 0.1) +
    geom_line(data = comp_df %>% filter(Quantile == "50th"),
      aes(x = Date, y = Upper), color = "green", linewidth = 0.1) +
    geom_line(data = comp_df %>% filter(Quantile == "5th"),
      aes(x = Date, y = Lower), color = "red", linewidth = 0.1) +
    geom_line(data = comp_df %>% filter(Quantile == "5th"),
      aes(x = Date, y = Upper), color = "red", linewidth = 0.1) +
    geom_line(data = comp_df %>% filter(Quantile == "95th"),
      aes(x = Date, y = Lower), color = "blue", linewidth = 0.1) +
    geom_line(data = comp_df %>% filter(Quantile == "95th"),
      aes(x = Date, y = Upper), color = "blue", linewidth = 0.1) +
    # --- Observed: Bold points + strong line for visual anchoring ---
    geom_line(data = obs_df, aes(x = Date, y = Value), color = obs_line, linewidth = 0.1) +
    geom_point(data = obs_df, aes(x = Date, y = Value), color = obs_point, size = 0.1, alpha = 0.95) +
    # --- Period text annotations ---
    annotate("text",
      x = shade_periods$xmin + (shade_periods$xmax - shade_periods$xmin) / 2,
      y = ylim[1] + 0.01 * diff(ylim),
      label = shade_periods$period,
      size = 3.4, color = "#565656", fontface = "italic"
    ) +
    # --- Axes and theme ---
    labs(title = title, x = NULL, y = ylab) +
    coord_cartesian(ylim = ylim, expand = TRUE) +
    scale_x_date(date_breaks = "24 months", date_labels = "%Y-%m") +
    theme_minimal(base_size = 15) +
    theme(
      plot.title = element_text(size = 16, face = "bold", hjust = 0.5, margin = margin(b = 8)),
      axis.title = element_text(face = "bold"),
      axis.text.x = element_text(angle = 35, hjust = 1, vjust = 1, size = 11),
      axis.text.y = element_text(size = 12),
      panel.grid.minor = element_blank(),
      panel.grid.major.x = element_line(linewidth = 0.3, color = "#e5e5e5"),
      panel.grid.major.y = element_line(linewidth = 0.4, color = "#e5e5e5"),
      plot.margin = margin(12, 12, 12, 12)
    )

  print(p)
  if (!is.null(filename)) {
    ff <- paste0("/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics_reproduce/", filename)
    ggsave(ff, plot = p, width = 12, height = 6, units = "in", dpi = 350)
  }
}


idx <- ceiling(TT/10):TT
obs_vec <- Y[1, idx]  
obs_df <- tibble(Date = as.Date(dates_ts_usgs[idx]), Value = obs_vec)

# 

# Example usage for any component
component <- 1
comp_df <- make_component_df(component, idx, dates_ts_usgs, q_d_50, q_d_05, q_d_95)
plot_component_quantiles(
  comp_df, obs_df,
  ylab = expression("Water Flow (Log-Log cm^3/s)"),
  title = "Trend Component – 1991–2022",
  ylim = c(-2, 2),
  filename = "trend_component_1991_2022.png",
  time_cuts = time_cuts,        # <-- NEW: pass this in!
  dates_ts_usgs = dates_ts_usgs # <-- NEW: pass this in!
)

# Example usage for any component
component <- 2
comp_df <- make_component_df(component, idx, dates_ts_usgs, q_d_50, q_d_05, q_d_95)
plot_component_quantiles(
  comp_df, obs_df,
  ylab = expression("Water Flow (Log-Log cm^3/s)"),
  title = "Yearly Effect – 1991–2022",
  ylim = c(-2, 2),
  filename = "yearly_component_1991_2022.png",
  time_cuts = time_cuts,        # <-- NEW: pass this in!
  dates_ts_usgs = dates_ts_usgs # <-- NEW: pass this in!
)

# Example usage for any component
component <- 4
comp_df <- make_component_df(component, idx, dates_ts_usgs, q_d_50, q_d_05, q_d_95)
plot_component_quantiles(
  comp_df, obs_df,
  ylab = expression("Water Flow (Log-Log cm^3/s)"),
  title = "Semestral Effect – 1991–2022",
  ylim = c(-2, 2),
  filename = "sem_component_1991_2022.png",
  time_cuts = time_cuts,        # <-- NEW: pass this in!
  dates_ts_usgs = dates_ts_usgs # <-- NEW: pass this in!
)

# Example usage for any component
component <- 6
comp_df <- make_component_df(component, idx, dates_ts_usgs, q_d_50, q_d_05, q_d_95)
plot_component_quantiles(
  comp_df, obs_df,
  ylab = expression("Water Flow (Log-Log cm^3/s)"),
  title = "80-month Effect – 1991–2022",
  ylim = c(-2, 2),
  filename = "80_component_1991_2022.png",
  time_cuts = time_cuts,        # <-- NEW: pass this in!
  dates_ts_usgs = dates_ts_usgs # <-- NEW: pass this in!
)


plot_component_quantiles <- function(
    comp_df, obs_df,
    ylab = "log-flow",
    title = "Component",
    ylim = c(-2.5, 2.5),
    filename = NULL
) {
  # Define custom colors (muted and colorblind-friendly)
  col_50  <- "#238b45"
  band_50 <- "#b2df8a"
  col_05  <- "#b2182b"
  band_05 <- "#fdbba1"
  col_95  <- "#2171b5"
  band_95 <- "#a6bddb"
  obs_line <- "#222222"
  obs_point <- "#222222"
  
  ribbon_alpha <- 0.11
  lnn <- 0.4
  p <- ggplot() +
    # --- Bands: Light, desaturated color ---
    geom_ribbon(
      data = comp_df %>% filter(Quantile == "50th"),
      aes(x = Date, ymin = Lower, ymax = Upper),
      fill = band_50, alpha = ribbon_alpha
    ) +
    geom_ribbon(
      data = comp_df %>% filter(Quantile == "5th"),
      aes(x = Date, ymin = Lower, ymax = Upper),
      fill = band_05, alpha = ribbon_alpha
    ) +
    geom_ribbon(
      data = comp_df %>% filter(Quantile == "95th"),
      aes(x = Date, ymin = Lower, ymax = Upper),
      fill = band_95, alpha = ribbon_alpha
    ) +

    # --- Median/Quantile lines: Strong, moderately thin ---
    geom_line(
      data = comp_df %>% filter(Quantile == "50th"),
      aes(x = Date, y = Median), color = col_50, linewidth = lnn
    ) +
    geom_line(
      data = comp_df %>% filter(Quantile == "5th"),
      aes(x = Date, y = Median), color = col_05, linewidth = lnn
    ) +
    geom_line(
      data = comp_df %>% filter(Quantile == "95th"),
      aes(x = Date, y = Median), color = col_95, linewidth = lnn
    ) +
    # --- Dashed, thin ---
    geom_line(
      data = comp_df %>% filter(Quantile == "50th"),
      aes(x = Date, y = Lower), color = "green", linewidth = 0.1
    ) +
    geom_line(
      data = comp_df %>% filter(Quantile == "50th"),
      aes(x = Date, y = Upper), color = "green", linewidth = 0.1
    ) +
    geom_line(
      data = comp_df %>% filter(Quantile == "5th"),
      aes(x = Date, y = Lower), color = "red", linewidth = 0.1
    ) +
    geom_line(
      data = comp_df %>% filter(Quantile == "5th"),
      aes(x = Date, y = Upper), color = "red", linewidth = 0.1
    ) +
    geom_line(
      data = comp_df %>% filter(Quantile == "95th"),
      aes(x = Date, y = Lower), color = "blue", linewidth = 0.1
    ) +
    geom_line(
      data = comp_df %>% filter(Quantile == "95th"),
      aes(x = Date, y = Upper), color = "blue", linewidth = 0.1
    ) +
    # --- Observed: Bold points + strong line for visual anchoring ---
    geom_line(
      data = obs_df, aes(x = Date, y = Value),
      color = obs_line, linewidth = 0.1
    ) +
    geom_point(
      data = obs_df, aes(x = Date, y = Value),
      color = obs_point, size = 0.1, alpha = 0.95
    ) +

    # --- Axes and theme ---
    labs(title = title, x = NULL, y = ylab) +
    coord_cartesian(ylim = ylim, expand = TRUE) +
    scale_x_date(date_breaks = "6 months", date_labels = "%Y-%m") +
    theme_minimal(base_size = 15) +
    theme(
      plot.title = element_text(size = 16, face = "bold", hjust = 0.5, margin = margin(b = 8)),
      axis.title = element_text(face = "bold"),
      axis.text.x = element_text(angle = 35, hjust = 1, vjust = 1, size = 11),
      axis.text.y = element_text(size = 12),
      panel.grid.minor = element_blank(),
      panel.grid.major.x = element_line(linewidth = 0.3, color = "#e5e5e5"),
      panel.grid.major.y = element_line(linewidth = 0.4, color = "#e5e5e5"),
      plot.margin = margin(12, 12, 12, 12)
    )
  
  print(p)
  if (!is.null(filename)) {
    ff <- paste0("/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics_reproduce/",filename)
    ggsave(ff, plot = p, width = 12, height = 6, units = "in", dpi = 350)
  }
}

idx <- time_cuts[1]:time_cuts[2]
obs_vec <- Y[1, idx]  
obs_df <- tibble(Date = as.Date(dates_ts_usgs[idx]), Value = obs_vec)

component <- 1
comp_df <- make_component_df(component, idx, dates_ts_usgs, q_d_50, q_d_05, q_d_95)
plot_component_quantiles(
  comp_df, obs_df,
  ylab = expression("Water Flow (Log-Log cm^3/s)"),
  title = "Trend Component – 2012–2016",
  ylim = c(-2, 2),
  filename = "trend_component_2012_2016.png"
)

component <- 2
comp_df <- make_component_df(component, idx, dates_ts_usgs, q_d_50, q_d_05, q_d_95)
plot_component_quantiles(
  comp_df, obs_df,
  ylab = expression("Water Flow (Log-Log cm^3/s)"),
  title = "Yearly Effect – 2012–2016",
  ylim = c(-2, 2),
  filename = "yearly_component_2012_2016.png"
)

component <- 4
comp_df <- make_component_df(component, idx, dates_ts_usgs, q_d_50, q_d_05, q_d_95)
plot_component_quantiles(
  comp_df, obs_df,
  ylab = expression("Water Flow (Log-Log cm^3/s)"),
  title = "Semestral Effect – 2012–2016",
  ylim = c(-2, 2),
  filename = "sem_component_2012_2016.png"
)

component <- 6
comp_df <- make_component_df(component, idx, dates_ts_usgs, q_d_50, q_d_05, q_d_95)
plot_component_quantiles(
  comp_df, obs_df,
  ylab = expression("Water Flow (Log-Log cm^3/s)"),
  title = "80-month Effect – 2012–2016",
  ylim = c(-2, 2),
  filename = "80_component_2012_2016.png"
)

idx <- time_cuts[3]:time_cuts[4]
obs_vec <- Y[1, idx]  
obs_df <- tibble(Date = as.Date(dates_ts_usgs[idx]), Value = obs_vec)

component <- 1
comp_df <- make_component_df(component, idx, dates_ts_usgs, q_d_50, q_d_05, q_d_95)
plot_component_quantiles(
  comp_df, obs_df,
  ylab = expression("Water Flow (Log-Log cm^3/s)"),
  title = "Trend Component – 2017–2019",
  ylim = c(-2, 2),
  filename = "trend_component_2017_2019.png"
)

component <- 2
comp_df <- make_component_df(component, idx, dates_ts_usgs, q_d_50, q_d_05, q_d_95)
plot_component_quantiles(
  comp_df, obs_df,
  ylab = expression("Water Flow (Log-Log cm^3/s)"),
  title = "Yearly Effect – 2017–2019",
  ylim = c(-2, 2),
  filename = "yearly_component_2017_2019.png"
)

component <- 4
comp_df <- make_component_df(component, idx, dates_ts_usgs, q_d_50, q_d_05, q_d_95)
plot_component_quantiles(
  comp_df, obs_df,
  ylab = expression("Water Flow (Log-Log cm^3/s)"),
  title = "Semestral Effect – 2017–2019",
  ylim = c(-2, 2),
  filename = "sem_component_2017_2019.png"
)

component <- 6
comp_df <- make_component_df(component, idx, dates_ts_usgs, q_d_50, q_d_05, q_d_95)
plot_component_quantiles(
  comp_df, obs_df,
  ylab = expression("Water Flow (Log-Log cm^3/s)"),
  title = "80-month Effect – 2017–2019",
  ylim = c(-2, 2),
  filename = "80_component_2017_2019.png"
)

idx <- ceiling(TT/10):TT
# Helper to tidy the quantile array
make_quantile_df <- function(q_array, idx, dates, quantiles = c("5th", "50th", "95th")) {
  # q_array: [quantile, time, quant (1=lower,2=median,3=upper)]
  stopifnot(dim(q_array)[3] == 3)
  out <- lapply(1:dim(q_array)[1], function(qi) {
    data.frame(
      Date = as.Date(dates),
      Quantile = quantiles[qi],
      Lower = q_array[qi, idx, 1],
      Median = q_array[qi, idx, 2],
      Upper = q_array[qi, idx, 3]
    )
  })
  bind_rows(out)
}

# Dates for x axis
dates <- as.Date(dates_ts_usgs[idx])

# Tidy quantile data
quantiles_labels <- c("5th", "50th", "95th")
df1 <- make_quantile_df(q_d_discrep1_quantiles, idx, dates, quantiles_labels)
df2 <- make_quantile_df(q_d_discrep2_quantiles, idx, dates, quantiles_labels)

# Observed discrepancy
obs1 <- data.frame(Date = dates, Discrepancy = Y[2, idx] - Y[1, idx])
obs2 <- data.frame(Date = dates, Discrepancy = Y[3, idx] - Y[1, idx])

make_discrepancy_plot <- function(df, obs, title, ylab = "log-flow", ylim = c(-2, 1)) {
  # Reduce number of date ticks
  n_ticks <- 16
  date_breaks <- scales::pretty_breaks(n = n_ticks)(range(obs$Date))

  # Colors
  colors <- c(
    "5th"  = "#b2182b",    # Dark red
    "50th" = "#238b45",    # Forest green
    "95th" = "#2171b5"     # Dark blue
  )
  ribbon_alpha <- 0.11

  ggplot() +
      # Observed discrepancy
    geom_line(data = obs, aes(x = Date, y = Discrepancy), color = "gray40", linewidth = 0.2) +
    geom_point(data = obs, aes(x = Date, y = Discrepancy), color = "black", size = 0.2) +
    geom_hline(yintercept = 0, color = "black", linetype = "dotted", linewidth = 0.2) +
    # Quantile ribbons (95th/5th)
    geom_ribbon(data = df %>% filter(Quantile == "5th"),
                aes(x = Date, ymin = Lower, ymax = Upper),
                fill = colors["5th"], alpha = ribbon_alpha) +
    geom_ribbon(data = df %>% filter(Quantile == "50th"),
                aes(x = Date, ymin = Lower, ymax = Upper),
                fill = colors["50th"], alpha = ribbon_alpha) +
    geom_ribbon(data = df %>% filter(Quantile == "95th"),
                aes(x = Date, ymin = Lower, ymax = Upper),
                fill = colors["95th"], alpha = ribbon_alpha) +
    # Median lines
    geom_line(data = df %>% filter(Quantile == "5th"),
              aes(x = Date, y = Median), color = colors["5th"], linewidth = 0.5) +
    geom_line(data = df %>% filter(Quantile == "50th"),
              aes(x = Date, y = Median), color = colors["50th"], linewidth = 0.5) +
    geom_line(data = df %>% filter(Quantile == "95th"),
              aes(x = Date, y = Median), color = colors["95th"], linewidth = 0.5) +
    scale_x_date(
      breaks = date_breaks,
      date_labels = "%Y-%m"
    ) +
    coord_cartesian(ylim = ylim) +
    labs(
      title = title,
      x = NULL,
      y = ylab
    ) +
    theme_minimal(base_size = 14) +
    theme(
      plot.title = element_text(size = 15, face = "bold", hjust = 0.5),
      axis.title = element_text(face = "bold"),
      axis.text.x = element_text(angle = 35, hjust = 1, vjust = 1, size = 11),
      axis.text.y = element_text(size = 12),
      panel.grid.minor = element_blank()
    )
}

# USGS-GloFAS
p1 <- make_discrepancy_plot(
  df1 %>% filter(Quantile %in% c("5th", "50th", "95th")),
  obs1,
  title = "Discrepancy USGS–GloFAS   1991–2022"
)
p1
ggsave("/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics_reproduce/Agg_disc_1991_2022_1.png", p1, width = 12, height = 6, units = "in", dpi = 900)

# USGS-NWS (if J==2)
p2 <- make_discrepancy_plot(
  df2 %>% filter(Quantile %in% c("5th", "50th", "95th")),
  obs2,
  title = "Discrepancy USGS–NWS   1991–2022"
)
p2
ggsave("/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics_reproduce/Agg_disc_1991_2022_2.png", p2, width = 12, height = 6, units = "in", dpi = 900)


idx <- time_cuts[1]:time_cuts[2]
# Helper to tidy the quantile array
make_quantile_df <- function(q_array, idx, dates, quantiles = c("5th", "50th", "95th")) {
  # q_array: [quantile, time, quant (1=lower,2=median,3=upper)]
  stopifnot(dim(q_array)[3] == 3)
  out <- lapply(1:dim(q_array)[1], function(qi) {
    data.frame(
      Date = as.Date(dates),
      Quantile = quantiles[qi],
      Lower = q_array[qi, idx, 1],
      Median = q_array[qi, idx, 2],
      Upper = q_array[qi, idx, 3]
    )
  })
  bind_rows(out)
}

# Dates for x axis
dates <- as.Date(dates_ts_usgs[idx])

# Tidy quantile data
quantiles_labels <- c("5th", "50th", "95th")
df1 <- make_quantile_df(q_d_discrep1_quantiles, idx, dates, quantiles_labels)
df2 <- make_quantile_df(q_d_discrep2_quantiles, idx, dates, quantiles_labels)

# Observed discrepancy
obs1 <- data.frame(Date = dates, Discrepancy = Y[2, idx] - Y[1, idx])
obs2 <- data.frame(Date = dates, Discrepancy = Y[3, idx] - Y[1, idx])

make_discrepancy_plot <- function(df, obs, title, ylab = "log-flow", ylim = c(-1, 1)) {
  # Reduce number of date ticks
  n_ticks <- 8
  date_breaks <- scales::pretty_breaks(n = n_ticks)(range(obs$Date))

  # Colors
  colors <- c(
    "5th"  = "#b2182b",    # Dark red
    "50th" = "#238b45",    # Forest green
    "95th" = "#2171b5"     # Dark blue
  )
  ribbon_alpha <- 0.11

  ggplot() +
      # Observed discrepancy
    geom_line(data = obs, aes(x = Date, y = Discrepancy), color = "gray40", linewidth = 0.2) +
    geom_point(data = obs, aes(x = Date, y = Discrepancy), color = "black", size = 0.2) +
    geom_hline(yintercept = 0, color = "black", linetype = "dotted", linewidth = 0.2) +
    # Quantile ribbons (95th/5th)
    geom_ribbon(data = df %>% filter(Quantile == "5th"),
                aes(x = Date, ymin = Lower, ymax = Upper),
                fill = colors["5th"], alpha = ribbon_alpha) +
    geom_ribbon(data = df %>% filter(Quantile == "50th"),
                aes(x = Date, ymin = Lower, ymax = Upper),
                fill = colors["50th"], alpha = ribbon_alpha) +
    geom_ribbon(data = df %>% filter(Quantile == "95th"),
                aes(x = Date, ymin = Lower, ymax = Upper),
                fill = colors["95th"], alpha = ribbon_alpha) +
    # Median lines
    geom_line(data = df %>% filter(Quantile == "5th"),
              aes(x = Date, y = Median), color = colors["5th"], linewidth = 0.1) +
    geom_line(data = df %>% filter(Quantile == "5th"),
              aes(x = Date, y = Lower), color = "red", linewidth = 0.051) +
    geom_line(data = df %>% filter(Quantile == "5th"),
              aes(x = Date, y = Upper), color = "red", linewidth = 0.051) +

    geom_line(data = df %>% filter(Quantile == "50th"),
              aes(x = Date, y = Median), color = colors["50th"], linewidth = 0.1) +
    geom_line(data = df %>% filter(Quantile == "50th"),
              aes(x = Date, y = Lower), color = "green", linewidth = 0.051) +
    geom_line(data = df %>% filter(Quantile == "50th"),
              aes(x = Date, y = Upper), color = "green", linewidth = 0.051) +

    geom_line(data = df %>% filter(Quantile == "95th"),
              aes(x = Date, y = Median), color = colors["95th"], linewidth = 0.1) +
    geom_line(data = df %>% filter(Quantile == "95th"),
              aes(x = Date, y = Lower), color = "blue", linewidth = 0.051) +
    geom_line(data = df %>% filter(Quantile == "95th"),
              aes(x = Date, y = Upper), color = "blue", linewidth = 0.051) +

    scale_x_date(
      breaks = date_breaks,
      date_labels = "%Y-%m"
    ) +
    coord_cartesian(ylim = ylim) +
    labs(
      title = title,
      x = NULL,
      y = ylab
    ) +
    theme_minimal(base_size = 14) +
    theme(
      plot.title = element_text(size = 15, face = "bold", hjust = 0.5),
      axis.title = element_text(face = "bold"),
      axis.text.x = element_text(angle = 35, hjust = 1, vjust = 1, size = 11),
      axis.text.y = element_text(size = 12),
      panel.grid.minor = element_blank()
    )
}

# USGS-GloFAS
p1 <- make_discrepancy_plot(
  df1 %>% filter(Quantile %in% c("5th", "50th", "95th")),
  obs1,
  title = "Discrepancy USGS–GloFAS   1991–2022",
  ylim = c(-1.5, 1)
)
p1
ggsave("/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics_reproduce/Agg_disc_2012_2016_1.png", p1, width = 12, height = 6, units = "in", dpi = 900)

# USGS-NWS (if J==2)
p2 <- make_discrepancy_plot(
  df2 %>% filter(Quantile %in% c("5th", "50th", "95th")),
  obs2,
  title = "Discrepancy USGS–NWS   1991–2022",
  ylim = c(-2.5, 1)
)
p2
ggsave("/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics_reproduce/Agg_disc_2012_2016_2.png", p2, width = 12, height = 6, units = "in", dpi = 900)


idx <- time_cuts[3]:time_cuts[4]
# Helper to tidy the quantile array
make_quantile_df <- function(q_array, idx, dates, quantiles = c("5th", "50th", "95th")) {
  # q_array: [quantile, time, quant (1=lower,2=median,3=upper)]
  stopifnot(dim(q_array)[3] == 3)
  out <- lapply(1:dim(q_array)[1], function(qi) {
    data.frame(
      Date = as.Date(dates),
      Quantile = quantiles[qi],
      Lower = q_array[qi, idx, 1],
      Median = q_array[qi, idx, 2],
      Upper = q_array[qi, idx, 3]
    )
  })
  bind_rows(out)
}

# Dates for x axis
dates <- as.Date(dates_ts_usgs[idx])

# Tidy quantile data
quantiles_labels <- c("5th", "50th", "95th")
df1 <- make_quantile_df(q_d_discrep1_quantiles, idx, dates, quantiles_labels)
df2 <- make_quantile_df(q_d_discrep2_quantiles, idx, dates, quantiles_labels)

# Observed discrepancy
obs1 <- data.frame(Date = dates, Discrepancy = Y[2, idx] - Y[1, idx])
obs2 <- data.frame(Date = dates, Discrepancy = Y[3, idx] - Y[1, idx])

make_discrepancy_plot <- function(df, obs, title, ylab = "log-flow", ylim = c(-1, 1)) {
  # Reduce number of date ticks
  n_ticks <- 8
  date_breaks <- scales::pretty_breaks(n = n_ticks)(range(obs$Date))

  # Colors
  colors <- c(
    "5th"  = "#b2182b",    # Dark red
    "50th" = "#238b45",    # Forest green
    "95th" = "#2171b5"     # Dark blue
  )
  ribbon_alpha <- 0.11

  ggplot() +
      # Observed discrepancy
    geom_line(data = obs, aes(x = Date, y = Discrepancy), color = "gray40", linewidth = 0.2) +
    geom_point(data = obs, aes(x = Date, y = Discrepancy), color = "black", size = 0.2) +
    geom_hline(yintercept = 0, color = "black", linetype = "dotted", linewidth = 0.2) +
    # Quantile ribbons (95th/5th)
    geom_ribbon(data = df %>% filter(Quantile == "5th"),
                aes(x = Date, ymin = Lower, ymax = Upper),
                fill = colors["5th"], alpha = ribbon_alpha) +
    geom_ribbon(data = df %>% filter(Quantile == "50th"),
                aes(x = Date, ymin = Lower, ymax = Upper),
                fill = colors["50th"], alpha = ribbon_alpha) +
    geom_ribbon(data = df %>% filter(Quantile == "95th"),
                aes(x = Date, ymin = Lower, ymax = Upper),
                fill = colors["95th"], alpha = ribbon_alpha) +
    # Median lines
    geom_line(data = df %>% filter(Quantile == "5th"),
              aes(x = Date, y = Median), color = colors["5th"], linewidth = 0.1) +
    geom_line(data = df %>% filter(Quantile == "5th"),
              aes(x = Date, y = Lower), color = "red", linewidth = 0.051) +
    geom_line(data = df %>% filter(Quantile == "5th"),
              aes(x = Date, y = Upper), color = "red", linewidth = 0.051) +

    geom_line(data = df %>% filter(Quantile == "50th"),
              aes(x = Date, y = Median), color = colors["50th"], linewidth = 0.1) +
    geom_line(data = df %>% filter(Quantile == "50th"),
              aes(x = Date, y = Lower), color = "green", linewidth = 0.051) +
    geom_line(data = df %>% filter(Quantile == "50th"),
              aes(x = Date, y = Upper), color = "green", linewidth = 0.051) +

    geom_line(data = df %>% filter(Quantile == "95th"),
              aes(x = Date, y = Median), color = colors["95th"], linewidth = 0.1) +
    geom_line(data = df %>% filter(Quantile == "95th"),
              aes(x = Date, y = Lower), color = "blue", linewidth = 0.051) +
    geom_line(data = df %>% filter(Quantile == "95th"),
              aes(x = Date, y = Upper), color = "blue", linewidth = 0.051) +

    scale_x_date(
      breaks = date_breaks,
      date_labels = "%Y-%m"
    ) +
    coord_cartesian(ylim = ylim) +
    labs(
      title = title,
      x = NULL,
      y = ylab
    ) +
    theme_minimal(base_size = 14) +
    theme(
      plot.title = element_text(size = 15, face = "bold", hjust = 0.5),
      axis.title = element_text(face = "bold"),
      axis.text.x = element_text(angle = 35, hjust = 1, vjust = 1, size = 11),
      axis.text.y = element_text(size = 12),
      panel.grid.minor = element_blank()
    )
}

# USGS-GloFAS
p1 <- make_discrepancy_plot(
  df1 %>% filter(Quantile %in% c("5th", "50th", "95th")),
  obs1,
  title = "Discrepancy USGS–GloFAS   1991–2022",
  ylim = c(-1.6, 0.8)
)
p1
ggsave("/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics_reproduce/Agg_disc_2017_2019_1.png", p1, width = 12, height = 6, units = "in", dpi = 900)

# USGS-NWS (if J==2)
p2 <- make_discrepancy_plot(
  df2 %>% filter(Quantile %in% c("5th", "50th", "95th")),
  obs2,
  title = "Discrepancy USGS–NWS   1991–2022",
  ylim = c(-1.6, 0.8)
)
p2
ggsave("/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics_reproduce/Agg_disc_2017_2019_2.png", p2, width = 12, height = 6, units = "in", dpi = 900)


# 

idx <- 1:TT
idx <- time_cuts[3]:time_cuts[4]
obs_vec <- Y[1, idx] * 0 
obs_df <- tibble(Date = as.Date(dates_ts_usgs[idx]), Value = obs_vec)

# component <- 23
# comp_df <- make_component_df(component, idx, dates_ts_usgs, q_d_50, q_d_05, q_d_95)
# plot_component_quantiles(
#   comp_df, obs_df,
#   ylab = expression("Water Flow (Log-Log cm^3/s)"),
#   title = "Precipitation – 2012–2016",
#   ylim = c(0, 0.5),
#   filename = "trend_component_2012_2016.png"
# )

# component <- 24
# comp_df <- make_component_df(component, idx, dates_ts_usgs, q_d_50, q_d_05, q_d_95)
# plot_component_quantiles(
#   comp_df, obs_df,
#   ylab = expression("Water Flow (Log-Log cm^3/s)"),
#   title = "Soil Moisture – 2012–2016",
#   ylim = c(0.5, 0),
#   filename = "trend_component_2012_2016.png"
# )

# component <- 25
# comp_df <- make_component_df(component, idx, dates_ts_usgs, q_d_50, q_d_05, q_d_95)
# plot_component_quantiles(
#   comp_df, obs_df,
#   ylab = expression("Water Flow (Log-Log cm^3/s)"),
#   title = "PCA – 2012–2016",
#   ylim = c(-0.005, 0),
#   filename = "trend_component_2012_2016.png"
# )

component <- 22
comp_df <- make_component_df(component, idx, dates_ts_usgs, q_d_50, q_d_05, q_d_95)
plot_component_quantiles(
  comp_df, obs_df,
  ylab = expression("Water Flow (Log-Log cm^3/s)"),
  title = "Cumm Effect – 2012–2016",
  ylim = c(-2.5, 3),
  filename = "trend_component_2012_2016.png"
)

names(new.theta.out_50_exAL_synth_DISC_uni)

# Y

# 

# for(i in 23:31){
# s5 <- samp.theta_5_exAL_synth_DISC$samp_theta[i,TT,]
# s20 <- samp.theta_20_exAL_synth_DISC$samp_theta[i,TT,]
# s35 <- samp.theta_35_exAL_synth_DISC$samp_theta[i,TT,]
# s50 <- samp.theta_50_exAL_synth_DISC$samp_theta[i,TT,]
# s65 <- samp.theta_65_exAL_synth_DISC$samp_theta[i,TT,]
# s80 <- samp.theta_80_exAL_synth_DISC$samp_theta[i,TT,]
# s95 <- samp.theta_95_exAL_synth_DISC$samp_theta[i,TT,]

# print(c(quantile(s5,0.025),mean(s5),quantile(s5,0.975)))
# print(c(quantile(s20,0.025),mean(s20),quantile(s20,0.975)))
# print(c(quantile(s35,0.025),mean(s35),quantile(s35,0.975)))
# print(c(quantile(s50,0.025),mean(s50),quantile(s50,0.975)))
# print(c(quantile(s65,0.025),mean(s65),quantile(s65,0.975)))
# print(c(quantile(s80,0.025),mean(s80),quantile(s80,0.975)))
# print(c(quantile(s95,0.025),mean(s95),quantile(s95,0.975)))


# }

# Indices and quantile labels
indices <- 23:31
sd_vec <- c(sd_ppt,sd_soil,sd_pca,1,sd1,sd2,sd3,sd4,sd5)

quantiles <- c(5, 50, 95)

# Create an empty list to store all results
all_results <- list()

ii <- 1
for(i in indices) {
  sd_fac <- sd_vec[ii]
  for(q in quantiles) {
    # Dynamically access the sample vector for this quantile/component
    samples <- (sd_fac)*get(paste0("samp.theta_", q, "_exAL_synth_DISC"))$samp_theta[i, TT, ]
    result <- data.frame(
      Component = i,
      Quantile = paste0(q, "th"),
      Lower = quantile(samples, 0.025),
      Mean = mean(samples),
      Upper = quantile(samples, 0.975)
    )
    all_results[[length(all_results) + 1]] <- result
  }
}

# Combine all into one tidy data frame
summary_df <- do.call(rbind, all_results)
print(summary_df)



synthesize_quantiles <- function(y_reps, percentiles, M = 10000) {
  # Dimensions
  n_p0 <- dim(y_reps)[1]
  n_samp <- dim(y_reps)[2]
  n_T <- dim(y_reps)[3]
  
  # Precompute grids (optimized)
  u_grid_dense <- (1:M)/(M+1)            # Dense grid for Q_init
  u_final <- (1:n_samp)/(n_samp+1)       # Probability levels for final sample
  pp <- (1:n_samp)/(n_samp+1)            # Grid for model quantiles
  
  # Output array [n_samp, n_T]
  output <- array(NA, dim = c(n_samp, n_T))
  
  for (t in 1:n_T) {
    # Step 1: Compute empirical τ-quantiles
    v <- vapply(1:n_p0, function(k) {
      quantile(y_reps[k, , t], probs = percentiles[k], type = 7, names = FALSE)
    }, numeric(1))
    
    # Step 2: Isotonic adjustment
    fit <- gpava(percentiles, v, ties = "primary")
    m_adj <- fit$x
    
    # Step 3: Distributional alignment
    adjusted_samples <- matrix(NA, nrow = n_p0, ncol = n_samp)
    for (k in 1:n_p0) {
      shift <- m_adj[k] - v[k]
      adj_vec <- y_reps[k, , t] + shift
      adjusted_samples[k, ] <- sort(adj_vec)  # Sort immediately after adjustment
    }
    
    # Step 4: Quantile function construction on a dense grid (vectorized).
    # Preserve exact behavior by evaluating approx() at the same u_grid_dense points,
    # but avoid calling approx() 10,000 times per t (one per u).
    q_dense <- vapply(
      1:n_p0,
      function(k) approx(pp, adjusted_samples[k, ], xout = u_grid_dense, rule = 2)$y,
      numeric(M)
    )
    # q_dense is [M x n_p0]; transpose to [n_p0 x M] for row-wise indexing
    q_dense <- t(q_dense)

    # Step 5: Initial synthesis (linear blend between adjacent quantile functions)
    q_init <- numeric(M)

    # Match boundary conditions from the original scalar loop
    mask_low <- u_grid_dense <= percentiles[1]
    mask_high <- u_grid_dense >= percentiles[n_p0]
    mask_mid <- !(mask_low | mask_high)

    if (any(mask_low)) {
      q_init[mask_low] <- q_dense[1, mask_low]
    }
    if (any(mask_high)) {
      q_init[mask_high] <- q_dense[n_p0, mask_high]
    }

    if (any(mask_mid)) {
      pos <- which(mask_mid)
      u_mid <- u_grid_dense[pos]
      i <- findInterval(u_mid, percentiles)
      w <- (u_mid - percentiles[i]) / (percentiles[i + 1] - percentiles[i])
      q_i <- q_dense[cbind(i, pos)]
      q_i1 <- q_dense[cbind(i + 1, pos)]
      q_init[pos] <- (1 - w) * q_i + w * q_i1
    }
    
    # Step 6: Monotone rearrangement
    q_sorted <- sort(q_init)  # Enforces global monotonicity
    
    # Step 7: Generate synthesized sample
    output[, t] <- approx(
      x = u_grid_dense, 
      y = q_sorted, 
      xout = u_final, 
      rule = 2
    )$y
  }
  
  return(output)
}

# Usage:
output_f <- synthesize_quantiles(y_reps_f, percentiles = c(0.05, 0.2, 0.35, 0.5, 0.65, 0.8, 0.95))

q_estim_output_f <- fast_col_quantiles_t(output_f, probs = c(0.05, 0.2, 0.35, 0.5, 0.65, 0.8, 0.95))
q_estim_synth_f <- fast_col_quantiles_t(log(synth_f), probs = c(0.05, 0.2, 0.35, 0.5, 0.65, 0.8, 0.95))

n_T <- dim(output_f)[2]
plot(rep(0,n_T), ylim = c(-1,3), type = 'line')
# for(s in 1:n.samp){
#     lines(output_f[s,], col = 'pink', lwd = 0.1)
# }

# for(s in 1:n.samp){
#     points(log(synth_f[s,]), col = 'lightblue', lwd = 0.1)
# }

for(i in 1:7){
    lines(q_estim_output_f[i,], col = 'black', lwd = 2, lty = 2)
    lines(q_estim_synth_f[i,], col = 'red', lwd = 2, lty = 2)
}

# Usage:
output <- synthesize_quantiles(y_reps, percentiles = c(0.05, 0.2, 0.35, 0.5, 0.65, 0.8, 0.95))

q_estim_output <- fast_col_quantiles_t(output, probs = c(0.05, 0.2, 0.35, 0.5, 0.65, 0.8, 0.95))
q_estim_synth <- fast_col_quantiles_t(log(synth), probs = c(0.05, 0.2, 0.35, 0.5, 0.65, 0.8, 0.95))

n_T <- dim(output)[2]
plot(rep(0,n_T), ylim = c(-1,3), type = 'line')
# for(s in 1:n.samp){
#     lines(output[s,], col = 'pink', lwd = 0.1)
# }

# for(s in 1:n.samp){
#     points(log(synth[s,]), col = 'lightblue', lwd = 0.1)
# }

for(i in 1:7){
    lines(q_estim_output[i,], col = 'black', lwd = 2, lty = 2)
    lines(q_estim_synth[i,], col = 'red', lwd = 2, lty = 2)
}

# q_s

idx <- idx_sub

output_f_q <- colQuantiles(output_f, probs = q_s, type = 8)
output_f_q <- t(output_f_q)

output_q <- colQuantiles(output, probs = q_s, type = 8)
output_q <- t(output_q)


# 1. Dates for fit and forecast
fit_dates <- as.Date(timestamps[idx])
forecast_dates <- seq(fit_dates[length(fit_dates)] + 1, by = "1 day", length.out = ranges[1])

# 2. Posterior samples, tidy for ggplot (long format; avoid pivot_longer)
df_post_fit <- fast_long_by_row(
  mat = output,
  row_values = seq_len(nrow(output)),
  col_values = fit_dates,
  row_name = "sample",
  col_name = "Date",
  value_name = "Value"
)
df_post_fit$Type <- "Fit"

df_post_forecast <- fast_long_by_row(
  mat = output_f,
  row_values = seq_len(nrow(output_f)),
  col_values = forecast_dates,
  row_name = "sample",
  col_name = "Date",
  value_name = "Value"
)
df_post_forecast$Type <- "Forecast"

df_post <- bind_rows(df_post_fit, df_post_forecast)

# 3. Quantile curves (avoid pivot_longer)
df_q_fit <- fast_long_by_row(
  mat = output_q,
  row_values = seq_len(nrow(output_q)),
  col_values = fit_dates,
  row_name = "quantile",
  col_name = "Date",
  value_name = "Value"
)
df_q_fit$Type <- "Fit"

df_q_forecast <- fast_long_by_row(
  mat = output_f_q,
  row_values = seq_len(nrow(output_f_q)),
  col_values = forecast_dates,
  row_name = "quantile",
  col_name = "Date",
  value_name = "Value"
)
df_q_forecast$Type <- "Forecast"

df_q <- bind_rows(df_q_fit, df_q_forecast)

# 4. Observed values for USGS
obs_df <- usgs_plot_df %>% 
  mutate(Source = "USGS", colgroup = ifelse(obs_type == "After", "After", "Before"))

p_post <- ggplot() +
  # Flood stage lines and labels
  geom_hline(
    yintercept = flood_stages_trans,
    linetype = "dashed",
    color = "gray",
    linewidth = 0.8
  ) +
    annotate(
    "text",
    x = as.Date("2022-12-25"),
    y = min(usgs_plot_df$value, na.rm = TRUE) - 0.15, # a bit below min y
    label = "Dec 25",
    color = "gray40",
    size = 3.5,
    fontface = "bold",
    vjust = 4,
    hjust = -0.1 
  ) +
  annotate(
    "text",
    x = max(obs_df$time),
    y = flood_stages_trans,
    label = flood_stage_labels,
    hjust = 10.5,
    vjust = -0.5,
    color = "black",
    fontface = "italic",
    size = 3.5
  ) +
  # Vertical lines for forecast init and flood
  geom_vline(
    xintercept = as.numeric(as.Date("2022-12-25")), 
    color = "gray40", linetype = "dashed", linewidth = 0.5, alpha = 0.8
  ) +
  geom_vline(
    xintercept = as.numeric(as.Date("2023-01-09")),
    color = "#4a235a", linetype = "dashed", linewidth = 0.5, alpha = 0.8
  ) +
  annotate(
    "text",
    x = as.Date("2023-01-09"),
    y = min(usgs_plot_df$value, na.rm = TRUE) - 0.15,
    label = "Jan 9: Flood",
    color = "#4a235a",
    vjust = 4,
    hjust = -0.1,
    fontface = "bold",
    size = 3.5
  ) +
  # Posterior samples ("spaghetti")
  geom_line(
    data = df_post, 
    aes(x = Date, y = (Value), group = interaction(Type, sample)), 
    color = "pink", linewidth = 0.15, alpha = 0.15
  ) +
  # Posterior quantile curves (thinner black lines)
  geom_line(
    data = df_q, 
    aes(x = Date, y = (Value), group = interaction(Type, quantile)), 
    color = "black", linewidth = 0.1
  ) +
  # USGS obs: before forecast
  geom_point(
    data = obs_df %>% filter(colgroup == "Before"), 
    aes(x = time, y = (value)), 
    color = usgs_green, size = 1.5
  ) +
  # USGS obs: after forecast (light green)
  geom_point(
    data = obs_df %>% filter(colgroup == "After"), 
    aes(x = time, y = (value)), 
    color = "#B22222", size = 2
  ) +
  geom_line(
    data = obs_df %>% filter(colgroup == "Before"),
    aes(x = time, y = (value)), color = usgs_green, linewidth = 0.5
  ) +
  geom_line(
    data = obs_df %>% filter(colgroup == "After"),
    aes(x = time, y = (value)), color = "#B22222", linewidth = 0.5, linetype = "dashed"
  ) +
  ############################
# GloFAS before (gray)
geom_line(
  data = glofas_before_df,
  aes(x = Date, y = Value, linetype = Source),
  color = "gray", linewidth = 0.5, alpha = 0.85
) +
geom_point(
  data = glofas_before_df,
  aes(x = Date, y = Value, shape = Source),
  color = "gray", size = 1.4, alpha = 0.85
) +
# NWS before (gray)
geom_line(
  data = nws_before_df,
  aes(x = Date, y = Value, linetype = Source),
  color = "gray", linewidth = 0.5, alpha = 0.85
) +
geom_point(
  data = nws_before_df,
  aes(x = Date, y = Value, shape = Source),
  color = "gray", size = 1.4, alpha = 0.85
) +
# GloFAS ensembles after (gray)
geom_line(
  data = fast_long_ensembles(ensembles[[1]], glofas_dates),
  aes(x = Date, y = value, group = member),
  color = "gray", alpha = 0.22, linewidth = 0.5, show.legend = FALSE
) +
# NWS ensembles after (gray)
geom_line(
  data = fast_long_ensembles(ensembles[[2]], nws_dates),
  aes(x = Date, y = value, group = member),
  color = "gray", alpha = 0.22, linewidth = 0.5, show.legend = FALSE
) +
  coord_cartesian(ylim = c(-1, 3.5)) +
  ############################
  scale_x_date(breaks = pretty_breaks(6), date_labels = "%b %d") +
  labs(
    title = "Posterior Predictive Samples and Quantiles\nwith USGS Observed Flow",
    x = "Date (2022-2023)",
    y = expression("Water Flow (Log-Log cm^3/s)")
  ) +
  theme_minimal(base_size = 14) +
  theme(
    plot.title = element_text(size = 16, face = "bold", hjust = 0.5),
    axis.title = element_text(face = "bold"),
    legend.position = "none",
    panel.grid.minor = element_blank()
  )

print(p_post)

ggsave(
  filename = "/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics_reproduce/posterior_samples_valid.png",
  plot = p_post,
  width = 12,
  height = 6,
  units = "in",
  dpi = 900
)


output_uni_f <- synthesize_quantiles(y_reps_uni, percentiles = c(0.05, 0.2, 0.35, 0.5, 0.65, 0.8, 0.95))
output_uni <- synthesize_quantiles(y_reps_hist_uni, percentiles = c(0.05, 0.2, 0.35, 0.5, 0.65, 0.8, 0.95))

idx <- idx_sub

output_f_q <- colQuantiles(output_uni_f, probs = q_s, type = 8)
output_f_q <- t(output_f_q)

output_q <- colQuantiles(output_uni, probs = q_s, type = 8)
output_q <- t(output_q)

# Dates for fit (historical) and forecast
fit_dates <- as.Date(timestamps[idx])
forecast_dates <- seq(fit_dates[length(fit_dates)] + 1, by = "1 day", length.out = ranges[1])

# 1. Posterior samples: historical (fit) and forecast (avoid pivot_longer)
df_post_fit <- fast_long_by_row(
  mat = log(synth_hist_uni),
  row_values = seq_len(nrow(synth_hist_uni)),
  col_values = fit_dates,
  row_name = "sample",
  col_name = "Date",
  value_name = "Value"
)
df_post_fit$Type <- "Fit"

df_post_forecast <- fast_long_by_row(
  mat = log(synth_f2),
  row_values = seq_len(nrow(synth_f2)),
  col_values = forecast_dates,
  row_name = "sample",
  col_name = "Date",
  value_name = "Value"
)
df_post_forecast$Type <- "Forecast"

df_post <- bind_rows(df_post_fit, df_post_forecast)

# 2. Quantile curves: historical (fit) and forecast (avoid pivot_longer)
df_q_fit <- fast_long_by_row(
  mat = log(synth_hist_uni_q),
  row_values = seq_len(nrow(synth_hist_uni_q)),
  col_values = fit_dates,
  row_name = "quantile",
  col_name = "Date",
  value_name = "Value"
)
df_q_fit$Type <- "Fit"

df_q_forecast <- fast_long_by_row(
  mat = log(synth_f2_q),
  row_values = seq_len(nrow(synth_f2_q)),
  col_values = forecast_dates,
  row_name = "quantile",
  col_name = "Date",
  value_name = "Value"
)
df_q_forecast$Type <- "Forecast"

df_q <- bind_rows(df_q_fit, df_q_forecast)

# 3. Observed values for USGS
obs_df <- usgs_plot_df %>% 
  mutate(Source = "USGS", colgroup = ifelse(obs_type == "After", "After", "Before"))

# 4. Plot (as before, no need to change this part except color for 'After' points/lines)
p_post <- ggplot() +
  # Vertical lines for forecast init and flood
  geom_vline(
    xintercept = as.numeric(as.Date("2022-12-25")), 
    color = "gray40", linetype = "dashed", linewidth = 0.5, alpha = 0.8
  ) +
  # Posterior samples
  geom_line(
    data = df_post, 
    aes(x = Date, y = Value, group = interaction(Type, sample)), 
    color = "pink", linewidth = 0.15, alpha = 0.15
  ) +
  # Posterior quantile curves
  geom_line(
    data = df_q, 
    aes(x = Date, y = Value, group = interaction(Type, quantile)), 
    color = "black", linewidth = 0.1
  ) +
  # USGS obs: before forecast
  geom_point(
    data = obs_df %>% filter(colgroup == "Before"), 
    aes(x = time, y = (value)), 
    color = usgs_green, size = 1.5
  ) +
  # USGS obs: after forecast (DARK RED)
  geom_point(
    data = obs_df %>% filter(colgroup == "After"), 
    aes(x = time, y = (value)), 
    color = "#B22222", size = 2
  ) +
  geom_line(
    data = obs_df %>% filter(colgroup == "Before"),
    aes(x = time, y = (value)), color = usgs_green, linewidth = 0.5
  ) +
  geom_line(
    data = obs_df %>% filter(colgroup == "After"),
    aes(x = time, y = (value)), color = "#B22222", linewidth = 0.5, linetype = "dashed"
  ) +
  geom_vline(
    xintercept = as.numeric(as.Date("2023-01-09")),
    color = "#4a235a", linetype = "dashed", linewidth = 0.5, alpha = 0.8
  ) +
  # Flood stage lines and labels
  geom_hline(
    yintercept = flood_stages_trans,
    linetype = "dashed",
    color = "gray",
    linewidth = 0.8
  ) +
    coord_cartesian(ylim = c(-1, 3.5)) +
  annotate(
    "text",
    x = max(obs_df$time),
    y = flood_stages_trans,
    label = flood_stage_labels,
    hjust = 10.5,
    vjust = -0.5,
    color = "black",
    fontface = "italic",
    size = 3.5
  ) +
    annotate(
    "text",
    x = as.Date("2022-12-25"),
    y = min(usgs_plot_df$value, na.rm = TRUE) - 0.15, # a bit below min y
    label = "Dec 25",
    color = "gray40",
    size = 3.5,
    fontface = "bold",
    vjust = 4,
    hjust = -0.1 
  ) +
  annotate(
    "text",
    x = as.Date("2023-01-09"),
    y = min(usgs_plot_df$value, na.rm = TRUE) - 0.15,
    label = "Jan 9: Flood",
    color = "#4a235a",
    vjust = 4,
    hjust = -0.1,
    fontface = "bold",
    size = 3.5
  ) +
  ############################
  scale_x_date(breaks = pretty_breaks(6), date_labels = "%b %d") +
  labs(
    title = "Posterior Predictive Samples and Quantiles\nwith USGS Observed Flow",
    x = "Date (2022-2023)",
    y = expression("Water Flow (Log-Log cm^3/s)")
  ) +
  theme_minimal(base_size = 14) +
  theme(
    plot.title = element_text(size = 16, face = "bold", hjust = 0.5),
    axis.title = element_text(face = "bold"),
    legend.position = "none",
    panel.grid.minor = element_blank()
  )

print(p_post)

ggsave(
  filename = "/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics_reproduce/posterior_samples_counter_valid.png",
  plot = p_post,
  width = 12,
  height = 6,
  units = "in",
  dpi = 900
)
