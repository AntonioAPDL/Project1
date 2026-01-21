#!/usr/bin/env Rscript
library(parallel)
library(dlm)
library(exdqlm)
library(mvtnorm)
library(jmuOutlier)
library(sn)
library(Matrix)
library(future)
library(future.apply)
library(numDeriv)
library(foreach)
library(doParallel)
library(dataRetrieval)
library(dplyr)
library(zoo)
library(tseries) 
library(tidyverse)
library(patchwork)
library(rvest)
library(expint)
library(nimble)
library(nloptr)
library(expm)
library(numDeriv)
library(Rcpp)
library(RcppArmadillo)
library(RcppEigen)
library(ks)
library(MASS)
library(FNN)
library(prism)

n.samp <- 2000 
cut <- 1
m <- 1

# Retrieve p0 from command line arguments
args <- commandArgs(trailingOnly = TRUE)
harmonics = c(1, 2, 1/6.8333333)   

Sys.setenv("PKG_CXXFLAGS"="-I/home/jaguir26/boost/include -DEIGEN_DONT_VECTORIZE")
Sys.setenv("PKG_LIBS"="-L/home/jaguir26/boost/lib -lboost_random")
Rcpp::sourceCpp("/home/jaguir26/project1_ucsc_phd/sampling_exal.cpp")
Rcpp::sourceCpp("/home/jaguir26/project1_ucsc_phd/sampling_truncnorm.cpp")
Rcpp::sourceCpp('/home/jaguir26/project1_ucsc_phd/kalman_NDLM.cpp')


objective_deltas <- function(delta, SIMS, use_covariates){

df_t    <- delta[1] 
df_s    <-  delta[2]
df_s67  <- delta[3]
# df.discrep <- delta[4]
df_trans <- delta[4]
df_covs <-  delta[5]
lambda <- delta[6]

# Function to check if a matrix is positive definite
is.positive.definite <- function(x) {
  eigenvalues <- eigen(x)$values
  return(all(eigenvalues > 0))
}

# Function to compute inverse or square root of inverse using Cholesky Decomposition
compute_cholesky <- function(q, compute_sqrt_inverse = FALSE) {
  if (!is.positive.definite(q)) {
    stop("The matrix is not positive definite.")
  }
  
  # Compute Cholesky decomposition
  chol_decomp <- chol(as.matrix(q))
  
  # Convert to Matrix class to use with chol2inv
  U <- Matrix(chol_decomp, sparse = TRUE)
  
  # Compute inverse using Cholesky decomposition
  inv_q <- chol2inv(U)
  
  if (!compute_sqrt_inverse) {
    return(list(inverse = inv_q))
  } else {
    # Compute square root of the inverse
    # The square root of the inverse in this context is the inverse of the upper triangular matrix U
    sqrt_inv_q <- solve(U)
    
    # Check if the square root of the inverse times itself results in the inverse
    sqrt_inv_q_product <- sqrt_inv_q %*% t(sqrt_inv_q)
    is_correct <- all.equal(sqrt_inv_q_product, inv_q, tolerance = 1e-10)
    
    return(list(inverse = inv_q, sqrt_inverse = sqrt_inv_q, check = is_correct))
  }
}

parameters_path <- "/home/jaguir26/projects/Project/Input/exAL/parameters/parameters.txt"

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
  eval(parse(text = line))
}

make_df_mat = function(df,dim.df,n){
  if(sum(dim.df)!=n){ stop("sum of component dimensions given in dim.df does not match m0") }
  if(length(df)!=length(dim.df)){ stop("length of component discount factors does not match length of component dimensions") }
  dfs = rep(df,dim.df)
  n.dfs = length(dim.df)
  ind.dfs = c(0,sapply(1:length(dim.df),function(x){sum(dim.df[1:x])}),n)
  df.mat = matrix(0,n,n)
  for(j in 1:n.dfs){
    df.mat[(ind.dfs[j]+1):ind.dfs[(j+1)],(ind.dfs[j]+1):ind.dfs[(j+1)]] = (1-dfs[ind.dfs[(j+1)]])/dfs[ind.dfs[(j+1)]]
  }
  return(df.mat)
}
#
make_df_mat_k = function(df,dim.df,n,k){
  if(sum(dim.df)!=n){ stop("sum of component dimensions given in dim.df does not match m0") }
  if(length(df)!=length(dim.df)){ stop("length of component discount factors does not match length of component dimensions") }
  dfs = rep(df,dim.df)
  n.dfs = length(dim.df)
  ind.dfs = c(0,sapply(1:length(dim.df),function(x){sum(dim.df[1:x])}),n)
  df.mat = matrix(0,n,n)
  for(j in 1:n.dfs){
    df.mat[(ind.dfs[j]+1):ind.dfs[(j+1)],(ind.dfs[j]+1):ind.dfs[(j+1)]] = (1-dfs[ind.dfs[(j+1)]]^k)/dfs[ind.dfs[(j+1)]]^k
  }
  return(df.mat)
}
#
H_t_k_r <- function(GG, t, k, r){
  n <- dim(GG)[1]
  I <- diag(n)
  for (s in (t+k-r):(t+k)) {
    I <- GG[,,s] %*% I   
  }
  return(I)
}
#
# Function to estimate log density using KDE for univariate data
estimate_log_density_kde_univariate <- function(data, points) {
  kde_result <- kde(data)
  density_estimates <- predict(kde_result, x = points)
  log_density <- log(density_estimates + .Machine$double.eps*10)  # Add small value to avoid log(0)
  return(log_density)
}
#
# Function to estimate the expectation term for univariate data
estimate_expectation_term_univariate <- function(sample_from_p, sample_size) {
  # Generate a sample from the standard normal distribution
  sample_from_normal <- rnorm(sample_size)
  
  # Estimate log density of p at points sampled from the standard normal distribution
  log_density_estimates <- estimate_log_density_kde_univariate(sample_from_p, sample_from_normal)
  
  # Compute the Monte Carlo estimate of the expectation
  expectation_estimate <- mean(log_density_estimates)
  
  return(expectation_estimate)
}
#
# Function to estimate the KL divergence D_KL(N(0, 1) || p) for univariate data
estimate_kl_divergence_univariate_normal_to_p <- function(sample_from_p, sample_size) {
  # Estimate the expectation term
  expectation_term <- estimate_expectation_term_univariate(sample_from_p, sample_size)
  
  # Compute the KL divergence
  kl_divergence <- -0.5 * log(2 * pi) - 0.5 - expectation_term
  
  return(kl_divergence)
}
#
# Function to estimate KL divergence using k-NN with entropy package for multivariate data
estimate_kl_divergence_knn_entropy <- function(sample_from_p, sample_size, k = 200) {
  # Generate a sample from the multivariate standard normal distribution
  sample_from_normal <- matrix(rnorm(sample_size * ncol(sample_from_p)), ncol = ncol(sample_from_p))
  
  # Estimate KL divergence using entropy package's KL.div function
  kl_divergence <- KL.divergence(sample_from_p, sample_from_normal, k = k)
  
  # Return only the final estimate
  return(tail(kl_divergence, n = 1))
}
#
# Unified function to estimate KL divergence based on the input sample
estimate_kl_divergence <- function(sample, sample_size = 10000) {
  # Check if the sample is univariate or multivariate
  if (is.vector(sample) || ncol(sample) == 1) {
    # Univariate case
    if (is.vector(sample)) {
      sample_from_p <- sample
    } else {
      sample_from_p <- sample[, 1]
    }
    
    # Estimate the KL divergence using the KDE-based method
    estimated_kl_divergence <- estimate_kl_divergence_univariate_normal_to_p(sample_from_p, sample_size)
    
  } else {
    # Multivariate case
    sample_from_p <- sample
    
    # Estimate the KL divergence using the k-NN based method with entropy package
    estimated_kl_divergence <- estimate_kl_divergence_knn_entropy(sample_from_p, sample_size, k = 100)
  }
  
  # Return the estimate
  return(estimated_kl_divergence)
}
#
# Function to estimate differential entropy using KDE for univariate data
estimate_differential_entropy_kde_univariate <- function(data) {
  kde_result <- kde(data)
  estimates <- kde_result$estimate
  estimates[estimates <= 0] <- .Machine$double.eps*10 # Prevent log(0) issues
  log_estimates <- log(estimates)
  log_estimates[!is.finite(log_estimates)] <- 0 # Handle non-finite values
  entropy_estimate <- -sum(estimates * log_estimates) * diff(kde_result$eval.points)[1]
  return(entropy_estimate)
}
#
# Function to estimate differential entropy using KDE for multivariate data
estimate_differential_entropy_kde_multivariate <- function(data) {
  kde_result <- kde(data)
  estimates <- kde_result$estimate
  estimates[estimates <= 0] <- .Machine$double.eps*10  # Prevent log(0) issues
  log_estimates <- log(estimates)
  log_estimates[!is.finite(log_estimates)] <- 0 # Handle non-finite values
  entropy_estimate <- -sum(estimates * log_estimates) * prod(diff(kde_result$eval.points[[1]]))
  return(entropy_estimate)
}
#
# Function to estimate the KL divergence D_KL(p || N(0, I)) for univariate data
estimate_kl_divergence_univariate <- function(data) {
  # Estimate the differential entropy H(p)
  H_p <- estimate_differential_entropy_kde_univariate(data)
  
  # Compute the expected value of the squared norm of the vectors
  E_p_x2 <- mean(data^2)
  
  # Dimensionality is 1 for univariate data
  k <- 1
  
  # Compute the KL divergence
  kl_divergence <- -H_p + (k / 2) * log(2 * pi) + (1 / 2) * E_p_x2
  
  return(kl_divergence)
}
#
# Function to estimate the KL divergence D_KL(p || N(0, I)) for multivariate data
estimate_kl_divergence_multivariate <- function(data) {
  # Estimate the differential entropy H(p)
  H_p <- estimate_differential_entropy_kde_multivariate(data)
  
  # Dimensionality of the vectors
  k <- ncol(data)
  
  # Compute the expected value of the squared norm of the vectors
  E_p_xTx <- mean(rowSums(data^2))
  
  # Compute the KL divergence
  kl_divergence <- -H_p + (k / 2) * log(2 * pi) + (1 / 2) * E_p_xTx
  
  return(kl_divergence)
}
#
# Wrapper function for any sample
compute_kl_divergence <- function(sample) {
  # Ensure the input sample is a matrix
  sample <- as.matrix(sample)
  
  # Determine if the sample is univariate or multivariate
  if (ncol(sample) == 1) {
    kl_divergence <- estimate_kl_divergence_univariate(sample)
  } else {
    kl_divergence <- estimate_kl_divergence_multivariate(sample)
  }
  
  return(kl_divergence)
}
#

# Read and process ELI_lon data
ELI_lon <- read.csv("/home/jaguir26/projects/Project/Input/exAL/covariates/cov_1_ELI.csv")
merged_sst_data <- read.csv("/home/jaguir26/projects/Project/Input/exAL/covariates/cov_2_ONI.csv")
ELI_lon$time <- as.Date(ELI_lon$time)
adjustment_years <- 170
ELI_lon$time <- ELI_lon$time - years(adjustment_years)
#
# Read and process USGS data
data_usgs_r <- readNWISdv(siteNumbers = site_code[1], parameterCd = "00060", statCd = "00003")
San_Lorenzo_Daily_USGS_R <- data_usgs_r %>%
  mutate(timestamp = as.Date(Date),
         data0 = log(X_00060_00003 + 1)) %>%
  filter(timestamp > as.Date("1979-01-01"))
San_Lorenzo_Daily_USGS_R$time <- San_Lorenzo_Daily_USGS_R$timestamp
#
#
# SOIL
csv_file_path <- "/home/jaguir26/project1_ucsc_phd/climate_indices/soil_moisture_daily_avg.csv"
soil_moisture_data <- read.csv(csv_file_path)
soil_moisture_data$time <- as.Date(soil_moisture_data$time)
colnames(soil_moisture_data) <- c('time','soil')
#
# Merge datasets based on 'time'
merged_data <- merge(ELI_lon, merged_sst_data, by = "time")
merged_data <- merge(merged_data, San_Lorenzo_Daily_USGS_R, by = "time")
merged_data <- merged_data[, c(1:6, 10)]
colnames(merged_data) <- c("time", "eli", "nino12", "nino3", "nino34", "nino4", "flow")
merged_data$eli_smooth <- rollmean(merged_data$eli, k = KK, align = "right", fill = NA)
merged_data$oni <- rollmean(merged_data$nino34, k = KK, align = "right", fill = NA)
merged_data$eli_smooth[1:(KK-1)] <- merged_data$eli[1:(KK-1)]#
merged_data$oni[1:(KK-1)] <- merged_data$nino34[1:(KK-1)]
merged_data$flow_log <- log(merged_data$flow + 1)
#
# Adding soil
merged_data <- merge(merged_data, soil_moisture_data, by = "time")
#
# Standardize specified columns
standardize <- function(x) {
  (x - mean(x, na.rm = TRUE)) / sd(x, na.rm = TRUE)
}
columns_to_standardize <- c("eli_smooth", "oni", "flow_log", "soil")
merged_data[columns_to_standardize] <- lapply(merged_data[columns_to_standardize], standardize)
#
# Read streamflow data and merge with covariates
# data_path <- "/home/jaguir26/project1_ucsc_phd/combined_streamflow_data_cleaned.csv"
data_path <- "/home/jaguir26/project1_ucsc_phd/retros_2022-12-25.csv"
streamflow_data <- read_csv(data_path, show_col_types = FALSE)
timestamps <- as.Date(streamflow_data$Date)
time_series_matrix <- as.matrix(streamflow_data[, c('USGS', 'NWS3.0', 'GloFAS')])
Y_usgs <- data.frame(time = timestamps, time_series_matrix)
#
plot_data <- merge(merged_data, Y_usgs, by = "time")
ppt_data <- read.csv("PPT.csv")
ppt_data$time <- as.Date(ppt_data$time)
plot_data <- merge(plot_data, ppt_data, by = "time")
########################################################
# INDECES
file_path <- "/home/jaguir26/project1_ucsc_phd/climate_indices/combined_indices_daily_standardized.csv"
combined_indices <- read_csv(file_path, show_col_types = FALSE)
combined_indices['time']  <- as.Date(combined_indices$Date )
plot_data <- merge(plot_data, combined_indices, by = "time")
#
plot_data <- plot_data[cut:nrow(plot_data),]
# x_names <- c('ppt', 'soil','Niño 3','NAO','Niño 1+2','WHWP','GMT','ONI','PNA','NOI','WP','Niño 3.4','Solar Flux','AMO','ESPI','TSA','Niño 4','TNA','SOI')
x_names <- c( 'ppt', 
              'soil',
              'Solar Flux',
              'Niño 1+2',
              'ONI',
              'WHWP',
              'GMT',
              'NOI',
              'AMO',
              'TSA',
              'TNA',
              'SOI')
X <- as.matrix(plot_data[, x_names])
X <- apply(X, 2, standardize)
X <- as.data.frame(X)
########################################################
# Set up Y and X matrices
Y <- t(as.matrix(plot_data[, c('USGS')]))
Y <- array(Y,c(1,length((Y))))
TT <- dim(Y)[2]
J <- dim(Y)[1] - 1
#
# X <- as.matrix(plot_data[, c('oni', 'ppt', 'soil')])
# X <- as.matrix(plot_data[, c('oni')])
timestamps <- plot_data[, 'time']
#
# Model setup without covariates
m_yy <- mean(Y, na.rm = TRUE)
s_yy <- sd(Y, na.rm = TRUE)  
kk <- 0.1 * s_yy
trend.comp <- polytrendMod(1, m0 = m_yy, C0 = kk)
harm <- harmonics
seas.comp <- seasMod(p = 363.5854, h = harm, C0 = 0.2 * kk * diag(2 * length(harm)))
model <- combineMods(trend.comp, seas.comp)
p <- length(model$m0)
#
idx <- seq(1, TT, by = m)  
y <- Y[,idx]
y <- matrix(y,nrow = 1)
TT_sub <- ncol(y)
#
if (is.null(nrow(y))) {
  JJJ <- 1
  y <- array(y, c(JJJ, length(y)))
} else {
  JJJ <- nrow(Y)
  y <- array(y, c(JJJ, ncol(y)))
}
#
n.samp <- 2000
verbose <- TRUE
#
m0 <- c(model$m0, rep(0, J))
C0 <- bdiag(model$C0, 0.2 * kk * diag(J))
#
##########################################
##########################################
#
# df_discrep <- rep(df.discrep, J)
#
df = c(df_t, df_s, df_s67); 
dim.df = c(1, 2*length(harm)-2, 2); 
k <- 10
##########################################
df.mat <- make_df_mat(df, dim.df, p)
df.mat.k <- make_df_mat_k(df, dim.df, p, k)
if (J <= 0) {
  ex.df.mat <- df.mat
  ex.df.mat.k <- df.mat.k
} else {
# #   extra_df.mat <- make_df_mat(df_discrep, rep(1, J), J)
#   extra_df.mat <- make_df_mat(c(df.discrep), c(J), J)
# #   extra_df.mat.k <- make_df_mat_k(df_discrep, rep(1, J), J, k)
#   extra_df.mat.k<- make_df_mat_k(c(df.discrep), c(J), J, k)
  ex.df.mat <- bdiag(df.mat, extra_df.mat)
  ex.df.mat.k <- bdiag(df.mat.k, extra_df.mat.k)
}
#
model_simp <- model
df_simp <- df
dim.df_simp <- dim.df
model_simp$GG <- array(model_simp$GG, c(p, p, TT))
model_simp$FF <- array(model_simp$FF, c(p, 1, TT))
model$m0 <- m0
model$C0 <- C0
if (use_covariates) {
  # Adding covariates
  px <- dim(X)[2]
  ppx <- px + 1

  F1 <- matrix(model$FF, p, J + 1)
  F2 <- cbind(rep(0, J), diag(J))
  Fx <- rbind(rep(1, J + 1), matrix(0, nrow = px, ncol = J + 1))
  FF <- array(rbind(F1, F2, Fx), c(p + J + ppx, 1 + J, TT))

  Gx <- as.matrix(bdiag(lambda, diag(px)))
  Gx <- array(rep(Gx, TT), dim = c(ppx, ppx, TT))
  Gx[1, 2:ppx, ] <- as.matrix(t(X))

  GG <- array(bdiag(model$GG, diag(J)), c(p + J, p + J, TT))
  model$GG <- GG
  GG_dim <- dim(model$GG)[1]
  new_dim <- GG_dim + ppx
  GGG <- array(0, dim = c(new_dim, new_dim, TT))
  GGG[1:GG_dim, 1:GG_dim, ] <- model$GG
  GGG[(GG_dim + 1):new_dim, (GG_dim + 1):new_dim, ] <- Gx

  model$FF <- FF
  model$GG <- GGG

  # df.covs <- rep(df_covs, ppx)
  # extra_df.mat <- make_df_mat(df.covs, rep(1, ppx), ppx)
  # extra_df.mat.k <- make_df_mat_k(df.covs, rep(1, ppx), ppx, k)

  extra_df.mat <- make_df_mat(c(df_trans,df_covs), c(1,px), ppx)
  extra_df.mat.k <- make_df_mat_k(c(df_trans,df_covs), c(1,px), ppx, k)

  ex.df.mat <- bdiag(ex.df.mat, extra_df.mat)
  ex.df.mat.k <- bdiag(ex.df.mat.k, extra_df.mat.k)

  model$m0 <- c(model$m0, rep(0, ppx))
  model$C0 <- bdiag(model$C0, 0.2 * kk * diag(ppx))

} else {
  # Without covariates
  GG <- array(bdiag(model$GG, diag(J)), c(p + J, p + J, TT))
  model$GG <- GG
  F1 <- matrix(model$FF, p, J + 1)
  F2 <- cbind(rep(0, J), diag(J))
  FF <- array(rbind(F1, F2), c(p + J, 1 + J, TT))
  model$FF <- FF
  ppx <- 0
}
#
FF <- model$FF
GG <- model$GG
#
######################## Init VB
exps <- Y
vars <- exps^2
new.sigma2_M <- array(1, c(1+J))
new.theta.out = list(exps = exps, 
                      exps2 = (exps)^2,
                      vars = 2*(exps)^2,
                      elbo.part = 0)
########################
# Prior for variances
a_s <- 1e-6
b_s <- 1e-6
a_update <- rep(TT/2 + a_s, 1+J)
b_update <- 0.5*rowSums((Y-exps)^2+vars)+b_s
sigma2 <- b_update/(a_update-1) 
seq.sigma2 <-  sigma2
D <- as.matrix(sigma2)
########################
C0 <- as.matrix(model$C0)
m0 <- model$m0
ex.df.mat <- as.matrix(ex.df.mat)
ex.df.mat.k <- as.matrix(ex.df.mat.k)
########################
dM <- 1 #Fix to one?
Ones <- matrix(1, dim(model$GG)[1], dim(model$GG)[1])
crit_ELBO <- 0
ELBO <- 0
seq.elbo = ELBO
iter = 0
FLAG = TRUE
TOL <- 1e-3
seq.ndlm_elbo <- 0
tictoc::tic("run time")
while (FLAG) {  
    #################################################################################################### 
    # if (crit_ELBO < tol1) {
    update.theta <- update_theta_cpp_ndlm(GG, m0, C0, D, FF, y, ex.df.mat, ex.df.mat.k, Ones, p, J, ppx, TT, k, dM)
   
    FF_t <- aperm(FF, c(2, 1, 3))
    multiply_matrices <- function(slice_index) {
      FF_t[,,slice_index] %*% update.theta$sm[,slice_index]
    }
    result_list <- lapply(1:ncol(update.theta$sm), multiply_matrices)
    result_array <- array(unlist(result_list), dim = c(J+1, 1, ncol(update.theta$sm)))
    result_array <- aperm(result_array, c(1, 3, 2))[,,1]
    exps <- result_array

    compute_product_1 <- function(t) {
      FF_t_slice <- FF_t[,,t]
      sC_slice <- update.theta$sC[,,t]
      FF_slice <- FF[,,t]
      result_slice <- t(FF_slice)%*%sC_slice%*%(FF_slice )
      return(result_slice)
    }
    result_list_1 <- lapply(1:dim(FF)[3], compute_product_1)
    vars_1 <- simplify2array(result_list_1)

   if(J>0){
    vars <- (apply(vars_1, 3, function(x) diag(x)))
    exps2 = exps^2 + vars
    }else{
    exps2 = exps^2 + vars_1
    vars_1 <- array( vars_1, c(1,TT) )  
    exps2 <- array( exps2, c(1,TT) )  
    exps <- array( exps, c(1,TT) )    
    }
    
      new.theta.out  <- update.theta 
      new.theta.out$exps  <- exps
      new.theta.out$exps2  <- exps2
      new.theta.out$vars  <- vars

    #   theta_update <- TRUE
    # }else{
    #   theta_update <- FALSE
    # }
    #################################################################################################### 
    elbo <- 0
    elbo <- elbo + new.theta.out$elbo.part
    #################################################################################################### 
    a_update <- rep(TT/2 + a_s, 1+J)
    b_update <- 0.5*rowSums((Y-new.theta.out$exps)^2+new.theta.out$vars)+b_s
    sigma2 <- b_update/(a_update-1) 
    D <- as.matrix(sigma2)
    seq.sigma2 <-  c(seq.sigma2,b_update/(a_update-1)) 
    ####################################################################################################  
    elbo <- elbo + sum(-(TT/2+a_update)*log(b_update)+lgamma(a_update)+TT/2*digamma(a_update))  
    elbo <- elbo/TT/(J+1)
    ####################################################################################################  
    crit_ELBO <- abs(elbo-ELBO)
    ELBO <- elbo
    # if(theta_update){
    #   if (crit_ELBO < tol2) {
    #     FLAG = FALSE
    #   }
    # }

    if (crit_ELBO < TOL) {
      FLAG = FALSE
    }

    seq.ndlm_elbo <- c(seq.ndlm_elbo, ELBO)  
    print(c(crit_ELBO, ELBO))
    flush.console()
    iter <- iter+1
}

run.time = tictoc::toc(quiet = TRUE)
if (verbose) {
  cat(sprintf("VB converged: %s iterations, %s seconds", 
              iter, round(run.time$toc - run.time$tic, 3)), "\n")
}

if(SIMS){
tictoc::tic("run time")
########################
sig.samp <- t(matrix(rinvgamma(n.samp*length(sigma2) , shape = a_update, rate = 1/b_update),nrow=length(sigma2)))
samp_theta_t = function(t) {
  LL <- t(chol(as.matrix(new.theta.out$sC[, , t])))
  return(new.theta.out$sm[, t] + LL %*% matrix(stats::rnorm(n.samp *  (p+ppx+J), 0, 1), p+ppx+J, n.samp))
}
#######################  
samp.theta = array(NA, c(p+ppx+J, TT, n.samp))
for (t in 1:TT) {
  samp.theta[, t, ] = samp_theta_t(t)
}
post_ndlm <- function(samp_theta, FF, sig.samp) {
  n_time <- dim(samp_theta)[2]
  n_sim <- dim(samp_theta)[3]
  y_post <- array(NA, dim = c( (J+1), n_time, n_sim))
  
  for (t in 1:n_time) {
    FF_t <- FF[,,t]  
    theta_t_s <- samp_theta[, t, ]
    y_post[, t, ] <- t(FF_t) %*% theta_t_s + t(sqrt(sig.samp))*matrix(rnorm((J+1)*n_sim),(J+1),n_sim)  
  }
  return(y_post)
}
samp_post_pred <- post_ndlm(samp.theta, FF, sig.samp)
########################
run.time = tictoc::toc(quiet = TRUE)
if (verbose) {
  cat(sprintf("Sampling finished:  %s seconds", round(run.time$toc - run.time$tic, 3)), "\n")
}
save_variables <- function(var_names, filename, dir_path) {
  file_path <- file.path(dir_path, filename)
  save_cmd <- paste("save(", paste(var_names, collapse = ", "), ", file = file_path)")
  eval(parse(text = save_cmd))
  cat("Variables saved to:", file_path, "\n")
}
result_suffix <- ""

if(use_covariates){
  ending <- "_NDLM_uni"
}else{
  ending <- "_NDLM_uni_simp"
}

# Define the variable names
samp.sigma_name <- paste0("samp.sigma_", result_suffix, ending)
samp.theta_name <- paste0("samp.theta_", result_suffix, ending)
samp.post.pred_name <- paste0("samp.post.pred_", result_suffix, ending)
new.theta.out_name <- paste0("new.theta.out_", result_suffix, ending)
seq.sigma_name <- paste0("seq.sigma_", result_suffix, ending)
seq.elbo_name <- paste0("seq.elbo_", result_suffix, ending)
delta_name <- paste0("delta_", result_suffix, ending)
# Create the delta variable with the result suffix
assign(delta_name, delta)
assign(samp.sigma_name, sig.samp)
assign(samp.theta_name, samp.theta)
assign(samp.post.pred_name, samp_post_pred)
assign(new.theta.out_name, new.theta.out)
assign(seq.sigma_name, seq.sigma2)
assign(seq.elbo_name, seq.ndlm_elbo)
# List of variables to save
vars_to_save <- c(samp.sigma_name, samp.theta_name, samp.post.pred_name, new.theta.out_name, seq.sigma_name, seq.elbo_name, delta_name)
# Save the variables
save_variables(vars_to_save, paste0("variables_", result_suffix, ending,".RData"), "/home/jaguir26/project1_ucsc_phd")
}


# K STEP AHEAD ERRORS
errors <- matrix(new.theta.out$standard_forecast_errors[1,], ncol = 1)
s <- 0.5 * compute_kl_divergence(errors)
s <- s + 0.5 *  estimate_kl_divergence(new.theta.out$standard_forecast_errors[1,])

print(c(s, ELBO, delta))
flush.console()

if (is.nan(s)) {
  print("Assigning Inf to NaN")
  flush.console()
  s <- Inf
}

return(s)
}s


#s
lower_bounds <- c(0.995, 0.988, 0.995, 0.999, 0.999, 0)   
upper_bounds <- c(0.9999999, 0.9999999, 0.9999999, 0.99999999, 0.9999999, 1) 
# initial_delta <- upper_bounds * 0.9   + lower_bounds * 0.1

initial_delta <- c( 0.9999,  # Trend
                    0.9999,    # Seas year and semester
                    0.9999,  # Seas 80 month
                    0.9998, # Mem for Trans
                    0.9999,   # Cov
                    0.66)     #Trans
                    
# # Define the optimization options
# opts <- list("algorithm" = "NLOPT_GN_CRS2_LM",  # Using a derivative-free algorithm
#              "xtol_rel" = 1.0e-4,
#              "maxeval" = 1000)

# # Define the objective function for minimization
# objective_deltas_min <- function(delta) {
#   objective_deltas(delta, FALSE, TRUE)  # Minimize the negative of the original function
# }

# # Perform the optimization
# result <- nloptr(x0 = initial_delta,
#                  eval_f = objective_deltas_min,  # Objective function
#                  lb = lower_bounds,
#                  ub = upper_bounds,
#                  opts = opts)
# d = as.numeric(c(result$solution))

# print(result)


d <- initial_delta
############################################
objective_deltas(d, TRUE, TRUE);