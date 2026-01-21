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
#
log.g<-function(gam){	log(2)+stats::pnorm(-abs(gam),log=T)+0.5*gam^2 }
L.fn<-function(p0){ stats::uniroot(function(gam) exp(log.g(gam))-(1-p0), c(-1000,0))$root }
U.fn<-function(p0){ stats::uniroot(function(gam) exp(log.g(gam))-p0, c(0,1000))$root }
p.fn<-function(p0,gam){ (p0-as.numeric(gam<0))/exp(log.g(gam))+as.numeric(gam<0)}
A.fn<-function(p0,gam){ temp.p = p.fn(p0,gam); return((1-2*temp.p)/(temp.p*(1-temp.p))) }
B.fn<-function(p0,gam){ temp.p = p.fn(p0,gam); return((2)/(temp.p*(1-temp.p))) }
C.fn<-function(p0,gam){ temp.p = p.fn(p0,gam); return((as.numeric(gam>0)-temp.p)^(-1)) }
#
CheckLossFn = function(p0,diff){diff*p0 - diff*as.numeric(diff<0)}
#
dlm_df = function(y, model, df, dim.df, s.priors = list(l0=1,S0=10), just.lik=FALSE){
  ### Gets the Time Series Length / Replicate number
  y = check_ts(y)
  TT = nrow(y)
  ### Gets the State Parameter dimension and Prior Distribution Parameters
  m0 = model$m0
  C0 = model$C0
  l0 = s.priors$l0
  S0 = s.priors$S0
  n = length(m0)
  ### Constructs F and G
  FF = model$FF
  GG = model$GG
  ### Variable Saving
  ### Posterior Distribution
  m = matrix(0,TT,n)
  C = array(0,c(TT,n,n))
  ### Predictive State Distribution
  a = matrix(0,TT,n)
  R = array(0,dim = c(TT,n,n))
  P = array(0,dim = c(TT,n,n))
  W = array(0,dim = c(TT,n,n))
  ### One-Step Ahead Forecast
  f = matrix(0,TT,1)
  Q = array(0,c(TT,1,1))
  inv.Q = array(0,c(TT,1,1))
  ### Regression Variables
  e = matrix(0,TT,1)
  A = array(0,c(TT,n,1))
  ### Sample Variance
  S = vector("numeric",TT)
  l = vector("numeric",TT)

  # Prior Dim Check
  m0 = matrix(m0,n,1)
  C0 = matrix(C0,n,n)
  ### Discount Factor Blocking
  df.mat = make_df_mat(df,dim.df,n)

  ### First Update
  ### One-step state forecast
  a[1,]  = GG[,,1] %*% m0
  P[1,,] = GG[,,1] %*% C0 %*% t(GG[,,1])
  W[1,,] = df.mat * P[1,,]
  R[1,,] = P[1,,] + W[1,,]
  ### One-step ahead forecast
  f[1,] = t(FF[,1]) %*% a[1,]
  Q[1,,] = as.matrix(1 + t(FF[,1]) %*% R[1,,] %*% FF[,1],1,1)
  inv.Q[1,,] = chol2inv(chol(Q[1,,]))
  ### Auxilary Variables
  e[1,]  = as.matrix(y[1,] - f[1,],1,1)
  A[1,,] = R[1,,] %*% FF[,1] %*% inv.Q[1,,]
  ### Variance update
  l[1] = l0 + 1
  S[1] = l0 * S0 / l[1] + (t(e[1,]) %*% inv.Q[1,,] %*% e[1,] / l[1])
  ### Posterior Distribution
  m[1,]  = a[1,] + as.matrix(A[1,,],n,1) %*% e[1,]
  C[1,,] = R[1,,] - as.matrix(A[1,,],n,1) %*% Q[1,,] %*% t(A[1,,])
  C[1,,] = (C[1,,] + t(C[1,,]))/2

  for(i in 2:TT){
    ### One-step state forecast
    a[i,]  = GG[,,i] %*% m[i-1,]
    P[i,,] = GG[,,i] %*% C[i-1,,] %*% t(GG[,,i])
    W[i,,] = df.mat * P[i,,]
    R[i,,] = P[i,,] + W[i,,]
    ### One-step ahead forecast
    f[i,] = t(FF[,i]) %*% a[i,]
    Q[i,,] = matrix(1 + t(FF[,i])%*% R[i,,]%*% FF[,i],1,1)
    inv.Q[i,,] = chol2inv(chol(Q[i,,]))
    ### Auxilary Variables
    e[i,]  = as.matrix(y[i,] - f[i,],1,1)
    A[i,,] = as.matrix(R[i,,] %*% FF[,i] %*% inv.Q[i,,],n,1)
    ### Variance update
    l[i] = l[i-1] + 1
    S[i] = l[i-1] * S[i-1] / l[i] + (t(e[i,]) %*% inv.Q[i,,] %*% e[i,] / l[i])
    ### Posterior Distribution
    m[i,]  = a[i,] + as.matrix(A[i,,],n,1) %*% e[i,]
    C[i,,] = R[i,,] - as.matrix(A[i,,],n,1) %*% Q[i,,] %*% t(as.matrix(A[i,,],n,1))
    C[i,,] = (C[i,,] + t(C[i,,]))/2
  }

  ### Adjust By Variance
  R[1,,] = S0 * R[1,,]
  Q[1,,]   = S0 * Q[1,,]
  C[1,,]   = S[1] * C[1,,]
  for(i in 2:TT){
    R[i,,] = S[i-1] * R[i,,]
    Q[i,,]   = S[i-1] * Q[i,,]
    C[i,,]   = S[i] * C[i,,]
  }

  # Calculate Log-Likelihood
  det.Q = log(abs(Q[1,,])) ; llik = lgamma((l0+1)/2)-lgamma(l0/2)-log(pi*l0)/2-det.Q/2-(l0+1)*log(1+t(e[1,])%*%inv.Q[1,,]%*%e[1,]/l0)/2
  for(t in 2:TT){
    det.Q = log(abs(Q[t,,]))
    llik = llik + lgamma((l[t-1]+1)/2)-lgamma(l[t-1]/2)-log(pi*l[t-1])/2-det.Q/2-(l[t-1]+1)*log(1+t(e[t,])%*%inv.Q[t,,]%*%e[t,]/l[t-1])/2
  }
  if(just.lik){
    return(list(llik = llik))
  }

  ## SMOOTHING
  ### Initializes recursive relations
  sa = matrix(0,TT,n)
  sR = array(0, dim = c(TT,n,n))
  ### Runs the recursive equations
  sa[TT,]  = m[TT,]
  sR[TT,,] = C[TT,,]
  for(k in 1:(TT-1)){
  ### Computes the Auxilary recursion Variable B
    B = C[TT-k,,] %*% t(GG[,,i]) %*% solve(R[TT-k+1,,])
    sa[TT-k,] = m[TT-k,] + B %*% (sa[TT-k+1,] - a[TT-k+1,])
    sR[TT-k,,] = C[TT-k,,] + B %*% (sR[TT-k+1,,] - R[TT-k+1,,]) %*% t(B)
  }
  ### Adjusts the variance update
  for(k in 1:TT){
    sR[TT-k,,] = S[TT] * sR[TT-k,,] / S[TT-k]
  }
  return(list(fm = m, fC = C, m = sa, C = sR,model = model, s = S, n = l))
}
#
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
check_mod = function(model){
  if(dlm::is.dlm(model)){
    model = dlmMod(model)
  }
  if(!is.vector(model$m0)){
    if(ncol(model$m0) != 1){
      stop("m0 must be a vector or a matrix with 1 column")
      }
    }
  p = length(model$m0)
  model$C0 = as.matrix(model$C0)
  if(p != dim(model$C0)[1] & p != dim(model$C0)[2]){
    stop("C0 must be a square matrix matching the dimension of m0")
    }
  if(!all.equal(model$C0, t(model$C0)) | !all(eigen(model$C0)$values >= 0)){
    stop("C0 must be a covariance matrix")
  }
  if(!is.vector(model$FF)){
    if(nrow(model$FF) != p){
      stop("FF must be a vector of length matching the dimension of m0, or a matrix with number of rows matching the dimension of m0")
    }
  }else{
    if(length(model$FF) != p){
      stop("FF must be a vector of length matching the dimension of m0, or a matrix with number of rows matching the dimension of m0")
    }
  }
  if(is.null(dim(model$GG)[3])){
    model$GG = as.matrix(model$GG)
  }else{
    if(is.na(dim(model$GG)[3])){
      model$GG = as.matrix(model$GG)
    }else{
      model$GG = as.array(model$GG)
    }
  }
  if(p != dim(model$GG)[1] & p != dim(model$GG)[2]){
    stop("GG must be a square matrix matching the dimension of m0, or an array with first two dimensions matching the dimension of m0")
  }
  model$m0 = as.matrix(model$m0)
  model$FF = as.matrix(model$FF)
  return(model)
}
#
check_logics = function(gam.init,sig.init,fix.gamma,fix.sigma,dqlm.ind){
  retval <- NULL
  retval$gam.init = gam.init
  retval$fix.gamma = fix.gamma
  retval$dqlm.ind = dqlm.ind
  if(dqlm.ind){
    if(gam.init!=0 | !fix.gamma){
      retval$gam.init <- gam.init <- 0
      retval$fix.gamma <- fix.gamma <- TRUE
    }
  }else{
    if(gam.init==0 && fix.gamma==TRUE){
      retval$dqlm.ind = TRUE
    }
  }
  if(fix.gamma & is.na(gam.init)){ stop("when fix.gamma = TRUE, gam.init must be specified") }
  if(fix.sigma & is.na(sig.init)){ stop("when fix.sigma = TRUE, sig.init must be specified") }
  return(retval)
}
#
check_ts = function(dat){
  dat = as.matrix(dat)
  if(all(dim(dat)>1)){
    stop("data must be univariate time-series")
  }
  if(dim(dat)[1]<dim(dat)[2]){
    dat = t(dat)
  }
  return(invisible(dat))
}
#
is.exdqlm = function(m){ return(inherits(m,"exdqlm")) }

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

# source("/home/jaguir26/projectsProject/Input/exAL/R_script/utilities_exDQLM.R")
#source("/home/jaguir26/projects/Project/Input/exAL/R_script/exDQLM_model1.R")

ELI_lon <- read.csv("/home/jaguir26/projects/Project/Input/exAL/covariates/cov_1_ELI.csv")
merged_sst_data <- read.csv("/home/jaguir26/projects/Project/Input/exAL/covariates/cov_2_ONI.csv")

ELI_lon$time <- as.Date(ELI_lon$time)
adjustment_years <- 170
ELI_lon$time <- ELI_lon$time - lubridate::years(adjustment_years)

t<-1

data_usgs_r <- readNWISdv(siteNumbers = site_code[t], parameterCd = "00060", statCd = "00003")
# Manipulate USGS data
San_Lorenzo_Daily_USGS_R <- data_usgs_r %>%
  mutate(timestamp = as.Date(Date),
         data0 = log(X_00060_00003 + 1)) %>%
  filter(timestamp > as.Date("1979-01-01"))
San_Lorenzo_Daily_USGS_R$time <- San_Lorenzo_Daily_USGS_R$timestamp

# Merge the datasets based on 'time' and 'Date'
merged_data <- merge(ELI_lon, merged_sst_data, by = "time")
merged_data <- merge(merged_data, San_Lorenzo_Daily_USGS_R, by = "time")
merged_data <- merged_data[,c(1:6,10)]
colnames(merged_data) <- c("time","eli","nino12","nino3","nino34","nino4","flow")
merged_data$eli_smooth <- rollmean(merged_data$eli, k = KK, align = "right", fill = NA)
merged_data$oni <- rollmean(merged_data$nino34, k = KK, align = "right", fill = NA)

# Fill the initial KK-1 values with original values
merged_data$eli_smooth[1:(KK-1)] <- merged_data$eli[1:(KK-1)]
merged_data$oni[1:(KK-1)] <- merged_data$nino34[1:(KK-1)]

merged_data$flow_log <- log(merged_data$flow+1)

# Define the standardize function
standardize <- function(x) {
  (x - mean(x, na.rm = TRUE)) / sd(x, na.rm = TRUE)
}

# Standardize the 'eli_smooth', 'oni', and 'flow_log' columns
columns_to_standardize <- c("eli_smooth", "oni", "flow_log")

merged_data[columns_to_standardize] <- lapply(merged_data[columns_to_standardize], standardize)

# Subset the data to include only the last 10 years (since 2010)
start_date <- as.Date("1979-01-01")
end_date <- max(merged_data$time)
subset_data <- subset(merged_data, time >= start_date & time <= end_date)

################################################################################
################################################################################
################################################################################
# My Example
DD <- merged_data[,c(1,8,9,10)]

# Extract columns from the merged dataframe
date <- DD$time
dates_ <- year(date)/1 + month(date)/12 + day(date)/365
value1 <- DD$flow_log
value2 <- DD$oni
value3 <- DD$eli_smooth

# Convert dates to POSIXlt object
dates_dt <- as.POSIXlt(date)
# Extract the year component
years <- dates_dt$year + 1850
# Find the indices where the year changes
year_changes <- c(1, which(diff(years) != 0) + 1)
# Indices for the first day of each year
first_day_indices <- year_changes


# Create time series for each column
# ts1_comp <- ts(value1, start = start_date, frequency = 365)
ts2_comp <- ts(value2, start = start_date, frequency = 365)
ts3_comp <- ts(value3, start = start_date, frequency = 365)


####################################################################################
####################################################################################

# Reading the CSV file
historical <- read.csv("/home/jaguir26/projects/Project/Input/ID_River/11160500/USGS_csv/historical_11160500_2019-11-25.csv")
colnames(historical) <- c('date','nws','glofas','usgs')
historical$date <- as.Date(historical$date)

# Create time series
start_year <- as.numeric(format(min(historical$date), "%Y"))
usgs_ts <- ts(historical$usgs, start = c(start_year, 1), frequency = 365)
glofas_ts <- ts(historical$glofas, start = c(start_year, 1), frequency = 365)
nws_ts <- ts(historical$nws, start = c(start_year, 1), frequency = 365)


################################################################################
################################################################################
################################################################################
# Define the standardize function
standardize <- function(x) {
  (x - mean(x, na.rm = TRUE)) / sd(x, na.rm = TRUE)
}

# Standardize the 'eli_smooth', 'oni', and 'flow_log' columns
columns_to_standardize <- colnames(historical)[-1]
historical_st <- historical
historical_st[columns_to_standardize] <- lapply(historical_st[columns_to_standardize], standardize)

################################################################################
################################################################################
################################################################################


# Ensure that the date columns are of Date class
merged_data$time <- as.Date(merged_data$time)
historical_st$date <- as.Date(historical_st$date)

# Merging the data frames based on the shared dates
all_ts <- merge(merged_data[, c('time', 'eli_smooth', 'oni')], historical_st, by.x = 'time', by.y = 'date', all = FALSE)


# Convert the date/time column to year + fraction of year
start_year <- as.numeric(format(min(all_ts$time), "%Y"))
end_year <- as.numeric(format(max(all_ts$time), "%Y"))
start_fraction <- as.numeric(format(min(all_ts$time), "%j")) / 365
end_fraction <- as.numeric(format(max(all_ts$time), "%j")) / 365
start_time <- start_year + start_fraction
end_time <- end_year + end_fraction

# Calculate frequency for daily data
frequency <- 365

# Create time series for each column
time_series_list <- lapply(all_ts[, -1], function(column) {
  ts(column, start = c(start_year, start_fraction * 365), end = c(end_year, end_fraction * 365), frequency = frequency)
})

# Naming the time series based on column names
names(time_series_list) <- colnames(all_ts[, -1])


################################################################################
################################################################################
################################################################################

ts2 <- time_series_list$eli_smooth
ts3 <- time_series_list$oni

ts_usgs <- time_series_list$usgs
ts_glofas <- time_series_list$glofas
ts_nws <- time_series_list$nws




dlm_df = function(y, model, df, dim.df, s.priors = list(l0=1,S0=10), just.lik=FALSE){
  
  ### Gets the Time Series Length / Replicate number
  TT = length(y)
  ### Gets the State Parameter dimension and Prior Distribution Parameters
  m0 = model$m0
  C0 = model$C0
  l0 = s.priors$l0
  S0 = s.priors$S0
  n = length(m0)
  ### Constructs F and G
  FF = model$FF
  GG = model$GG
  ### Variable Saving
  ### Posterior Distribution
  m = matrix(0,TT,n)
  C = array(0,c(TT,n,n))
  ### Predictive State Distribution
  a = matrix(0,TT,n)
  R = array(0,dim = c(TT,n,n))
  P = array(0,dim = c(TT,n,n))
  W = array(0,dim = c(TT,n,n))
  ### One-Step Ahead Forecast
  f = matrix(0,TT,1)
  Q = array(0,c(TT,1,1))
  inv.Q = array(0,c(TT,1,1))
  ### Regression Variables
  e = matrix(0,TT,1)
  A = array(0,c(TT,n,1))
  ### Sample Variance
  S = vector("numeric",TT)
  l = vector("numeric",TT)
  
  # Prior Dim Check
  m0 = matrix(m0,n,1)
  C0 = matrix(C0,n,n)
  ### Discount Factor Blocking
  df.mat = make_df_mat(df,dim.df,n)
  
  ### First Update
  ### One-step state forecast
  a[1,]  = GG[,,1] %*% m0
  P[1,,] = GG[,,1] %*% C0 %*% t(GG[,,1])
  W[1,,] = df.mat * P[1,,]
  R[1,,] = P[1,,] + W[1,,]
  ### One-step ahead forecast
  f[1,] = t(FF[,,1]) %*% a[1,]
  Q[1,,] = as.matrix(1 + t(FF[,,1]) %*% R[1,,] %*% FF[,,1],1,1)
  inv.Q[1,,] = chol2inv(chol(Q[1,,]))
  ### Auxilary Variables
  e[1,]  = as.matrix(y[1] - f[1,],1,1)
  A[1,,] = R[1,,] %*% FF[,,1] %*% inv.Q[1,,]
  ### Variance update
  l[1] = l0 + 1
  S[1] = l0 * S0 / l[1] + (t(e[1,]) %*% inv.Q[1,,] %*% e[1,] / l[1])
  ### Posterior Distribution
  m[1,]  = a[1,] + as.matrix(A[1,,],n,1) %*% e[1,]
  C[1,,] = R[1,,] - as.matrix(A[1,,],n,1) %*% Q[1,,] %*% t(A[1,,])
  C[1,,] = (C[1,,] + t(C[1,,]))/2
  
  for(i in 2:TT){
    ### One-step state forecast
    a[i,]  = GG[,,i] %*% m[i-1,]
    P[i,,] = GG[,,i] %*% C[i-1,,] %*% t(GG[,,i])
    W[i,,] = df.mat * P[i,,]
    R[i,,] = P[i,,] + W[i,,]
    ### One-step ahead forecast
    f[i,] = t(FF[,,i]) %*% a[i,]
    Q[i,,] = matrix(1 + t(FF[,,i])%*% R[i,,]%*% FF[,,i],1,1)
    inv.Q[i,,] = chol2inv(chol(Q[i,,]))
    ### Auxilary Variables
    e[i,]  = as.matrix(y[i] - f[i,],1,1)
    A[i,,] = as.matrix(R[i,,] %*% FF[,,i] %*% inv.Q[i,,],n,1)
    ### Variance update
    l[i] = l[i-1] + 1
    S[i] = l[i-1] * S[i-1] / l[i] + (t(e[i,]) %*% inv.Q[i,,] %*% e[i,] / l[i])
    ### Posterior Distribution
    m[i,]  = a[i,] + as.matrix(A[i,,],n,1) %*% e[i,]
    C[i,,] = R[i,,] - as.matrix(A[i,,],n,1) %*% Q[i,,] %*% t(as.matrix(A[i,,],n,1))
    C[i,,] = (C[i,,] + t(C[i,,]))/2
  }
  
  ### Adjust By Variance
  R[1,,] = S0 * R[1,,]
  Q[1,,]   = S0 * Q[1,,]
  C[1,,]   = S[1] * C[1,,]
  for(i in 2:TT){
    R[i,,] = S[i-1] * R[i,,]
    Q[i,,]   = S[i-1] * Q[i,,]
    C[i,,]   = S[i] * C[i,,]
  }
  
  # Calculate Log-Likelihood
  det.Q = log(abs(Q[1,,])) ; llik = lgamma((l0+1)/2)-lgamma(l0/2)-log(pi*l0)/2-det.Q/2-(l0+1)*log(1+t(e[1,])%*%inv.Q[1,,]%*%e[1,]/l0)/2
  for(t in 2:TT){
    det.Q = log(abs(Q[t,,]))
    llik = llik + lgamma((l[t-1]+1)/2)-lgamma(l[t-1]/2)-log(pi*l[t-1])/2-det.Q/2-(l[t-1]+1)*log(1+t(e[t,])%*%inv.Q[t,,]%*%e[t,]/l[t-1])/2
  }
  if(just.lik){
    return(list(llik = llik))
  }
  
  ## SMOOTHING
  ### Initializes recursive relations
  sa = matrix(0,TT,n)
  sR = array(0, dim = c(TT,n,n))
  ### Runs the recursive equations
  sa[TT,]  = m[TT,]
  sR[TT,,] = C[TT,,]
  for(k in 1:(TT-1)){
    ### Computes the Auxilary recursion Variable B
    B = C[TT-k,,] %*% t(GG[,,i]) %*% solve(R[TT-k+1,,])
    sa[TT-k,] = m[TT-k,] + B %*% (sa[TT-k+1,] - a[TT-k+1,])
    sR[TT-k,,] = C[TT-k,,] + B %*% (sR[TT-k+1,,] - R[TT-k+1,,]) %*% t(B)
  }
  ### Adjusts the variance update
  for(k in 1:TT){
    sR[TT-k,,] = S[TT] * sR[TT-k,,] / S[TT-k]
  }
  return(list(fm = m, fC = C, m = sa, C = sR,model = model, s = S, n = l))
}

###############################################################################
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

H_t_k_r <- function(GG, t, k, r){
  n <- dim(GG)[1]
  I <- diag(n)
  for (s in (t+k-r):(t+k)) {
    I <- GG[,,s] %*% I   
  }
  return(I)
}

################################################################################################################################################################
################################################################################################################################################################
################################################################################################################################################################
################################################################################################################################################################
################################################################################################################################################################
################################################################################################################################################################
################################################################################################################################################################
################################################################################################################################################################
################################################################################################################################################################
################################################################################################################################################################
################################################################################################################################################################
################################################################################################################################################################
################################################################################################################################################################
################################################################################################################################################################
################################################################################################################################################################
################################################################################################################################################################
################################################################################################################################################################
################################################################################################################################################################
Y <- rbind(t(as.matrix(ts_usgs)), t(as.matrix(ts_glofas)), t(as.matrix(ts_nws)))
TT <- dim(Y)[2]

m <- 30
seqs <- 0:(floor(TT/m)-1)
idx <- seqs*m+1
Y_batch <- Y[,idx]

df_t    <- 0.9995
df_s    <- 0.988
df_s67  <- 0.9995
m_yy <- mean(Y, na.rm = TRUE)
s_yy <- sd(Y, na.rm = TRUE)  
k <- 0.3*s_yy

trend.comp = polytrendMod(1, m0 = m_yy, C0 = k)
harm = harmonics
seas.comp = seasMod(p = 363.5854/m, h = harm , C0 = 0.5*k*diag(2*length(harm)))
model = combineMods(trend.comp, seas.comp)

y = Y_batch; p0 = 0.05; 
model = model; 


if(is.null(nrow(y))){ 
    JJJ <- 1
    y = array(y, c(JJJ,length(y)))
 }else{
    JJJ <- nrow(Y)
    y = array(y, c(JJJ,ncol(y)))
 }

df = c(df_t,df_s, df_s67); dim.df = c(1, 2*length(harm)-2, 2); 
gam.init = array(rep(0.01,JJJ), c(JJJ,1)); 
sig.init = array(rep(0.1,JJJ), c(JJJ,1));
tol = 0.001; 
n.IS = 3000; n.samp = 2000; 
PriorSigma = array(NA_real_, c(JJJ,2)); 
PriorGamma = array(NA_real_, c(JJJ,3)); 
verbose = TRUE; k = 5;

df_discrep <- rep(0.9999, JJJ-1)

  ########################
  TT = dim(y)[2] 
  J = dim(y)[1]-1 
  p = length(model$m0) 
  ########################
  m0 = c(model$m0,rep(0,J))
  # m0 = model$m0 # Erase
  C0 = bdiag(model$C0,diag(J))
  # C0 = model$C0 # Erase
  ########################
  model_simp <- model
  df_simp <- df
  dim.df_simp <- dim.df
  model_simp$GG = array(model_simp$GG, c(p, p, TT))
  model_simp$FF = array(model_simp$FF, c(p, 1, TT))
  df.mat = make_df_mat(df, dim.df, p)
  df.mat.k = make_df_mat_k(df, dim.df, p, k)
  ########################
  if(J<=0){ # Chanhe to ==0
  ex.df.mat <- df.mat
  ex.df.mat.k <- df.mat.k 
  }else{
  extra_df.mat <- make_df_mat(df_discrep,rep(1,J),J)
  extra_df.mat.k <- make_df_mat_k(df_discrep,rep(1,J),J,k)
  ex.df.mat <- bdiag(df.mat, extra_df.mat)
  ex.df.mat.k <- bdiag(df.mat.k, extra_df.mat.k)
  }

  ########################
  ########################
  GG = array( bdiag(model$GG,diag(J)), c(p+J, p+J, TT) )
  # GG = array(model$GG, c(p, p, TT) ) #Erase
  model$GG = GG
  
  F1 <- matrix(model$FF,p,J+1)
  F2 <- cbind(rep(0,J),diag(J))
  FF = array(rbind(F1,F2), c(p+J, 1+J, TT))
  # FF = array(F1, c(p, J+1, TT))#Erase
  model$FF = FF
  ########################
  ########################
  L = L.fn(p0)
  U = U.fn(p0)
  ########################
  ########### For every j
  for (j in 1:(J+1)) {
    if (!is.na(gam.init[j,])) {
      if (gam.init[j,] < L | gam.init[j,] > U) {
        stop(sprintf("gam.init must be between %s and %s for %s quantile", 
                     round(L, 3), round(U, 3), p0))
      }
    } 
  }

  ########################
  ########### For every j
  for (j in 1:(J+1)) {
    if (is.na(PriorSigma[j,1]) || is.na(PriorSigma[j,2])) {
      m_sigma = 1
      v_sigma = 1e+10
      PriorSigma[j,1] = (m_sigma^2)/(v_sigma) + 2 
      PriorSigma[j,2] = (m_sigma^3)/(v_sigma) + m_sigma 
    }
  }
  ########################
  ########### For every j
  for (j in 1:(J+1)) {
    if (is.na(PriorGamma[j,1]) || is.na(PriorGamma[j,2]) || is.na(PriorGamma[j,3])) {
      PriorGamma[j,1]  = 0
      PriorGamma[j,2]  = 1e+10
      PriorGamma[j,3] = 1
    }
  }
  
  
  ########################
  ########### For every j
  gam0 = gam.init 
  sig0 = sig.init 


  ########################
  ########### For every j 
  E1 <- array(NA_real_, c(J+1,1))
  E1[,] <- 10
  E2 <- array(NA_real_, c(J+1,1))
  E2[,] <- 10
  new.gamsig.out = list(E.gam = gam0,
                        V.gam = E1, 
                        E.sigma = sig0, 
                        V.sig = E2,
                        E.inv.sigma = 1/sig0, 
                        E.c2.invb.absgam2.sigma = sig0 * (C.fn(p0, gam0)^2) * (abs(gam0)^2)/B.fn(p0, gam0), 
                        E.c.invb.absgam = C.fn(p0, gam0) * abs(gam0)/B.fn(p0, gam0),  
                        E.c.a.invb.absgam = C.fn(p0, gam0) * A.fn(p0, gam0) * abs(gam0)/B.fn(p0, gam0), 
                        E.a2.invb.inv.sigma = (A.fn(p0,gam0)^2)/(B.fn(p0, gam0) * sig0), 
                        E.invb.inv.sigma = 1/(sig0 * B.fn(p0, gam0)), 
                        E.a.invb.inv.sigma = A.fn(p0, gam0)/(B.fn(p0, gam0) * sig0),
                        E.log.sig.b = log( sig0*B.fn(p0, gam0) ),
                        E.log.sig = log(sig0),
                        E.prior.sig.gam = array(0, c(J+1,1)),
                        entrop = array(0, c(J+1,1))  )
  
  ########################
  ########### For every j
  E1 <- array(NA_real_, c(J+1,TT))
  E1[,] <- truncnorm::etruncnorm(a = 0, b = Inf,  mean = 1, sd = 1)
  E2 <- array(NA_real_, c(J+1,TT))
  E2[,] <- truncnorm::etruncnorm(a = 0, b = Inf, mean = 1, sd = 1)^2 + truncnorm::vtruncnorm(a = 0, b = Inf,mean = 1, sd = 1)
  
  new.sts.out = list(E.sts = E1, 
                     E.sts2 = E2,
                     tot.entrop = array(0, c(J+1,1)) )
  
  ########################
  ########### For every j
  E1 <- array(NA_real_, c(J+1,TT))
  E1[,] <- 1/sig0
  E2 <- array(NA_real_, c(J+1,TT))
  E2[,] <- sig0
  new.uts.out = list(E.uts = E1, 
                     E.inv.uts = E2,
                     E.log.uts = array(0, c(J+1,1)),
                     tot.entrop = array(0, c(J+1,1)) )


  ########################
  ########### For every j
  # Initializing exps0
  init.dlm = dlm_df(colMeans(y), model_simp, df_simp, dim.df_simp, 
                    s.priors = list(l0 = 1, S0 = mean(sig0)), 
                    just.lik = FALSE)
  
  FF_t <- aperm(model_simp$FF, c(2, 1, 3))
  multiply_matrices <- function(slice_index) {
    t(FF_t[1,,slice_index]) %*% init.dlm$m[slice_index,]
  }
  result_list <- lapply(1:TT, multiply_matrices)
  result_array <- array(unlist(result_list), dim = c(TT,1))
  exps0 = c(result_array) + stats::qnorm(p0, 0, sqrt(init.dlm$s[TT]))
  exps0 = t(replicate(J+1, exps0))
            
  new.theta.out = list(exps = exps0, 
                       exps2 = (exps0)^2)
  
  ########################
  ########################
  ########################
  ########################
  iter = 0
  conv.count = 0
  new.max = Inf
  ########################
  ########### For every j
  seq.gamma = new.gamsig.out$E.gam
  seq.sigma = new.gamsig.out$E.sigma
  ########################
  
update_sts<-function(y, exps,inv.uts,c2.invb.absgam2.sigma,c.invb.absgam,c.a.invb.absgam){
    s.sig2<-1/(1+c2.invb.absgam2.sigma*inv.uts); s.sig = sqrt(s.sig2)
    s.mu<-s.sig2*(c.invb.absgam*(y-exps)*inv.uts-c.a.invb.absgam)
    #
    E.sts = truncnorm::etruncnorm(a=rep(0,TT),b=rep(Inf,TT),mean=s.mu,sd=s.sig)
    V.sts = truncnorm::vtruncnorm(a=rep(0,TT),b=rep(Inf,TT),mean=s.mu,sd=s.sig)
    E.sts2 = s.mu^2 + s.sig2 + s.mu*s.sig*exp(stats::dnorm(-s.mu/s.sig,log = TRUE)-stats::pnorm(s.mu/s.sig,log.p = TRUE))
    return(list(sts.sig2=s.sig2,sts.mu=s.mu,
                E.sts=E.sts,E.sts2=E.sts2,
                tot.entrop = sum(0.5*log2(2*pi*exp(1)*s.sig2) - 1 )))
  }
  
Kprime <- function(x){
  sqrt(pi/2/x) * expint_E1(2*x) * exp(x)
}

gig_entrop <- function(a,b){
  nu <- 0.5
  s.ab <- sqrt(a*b)
  K1 <- besselK(s.ab, nu)
  K2 <- besselK(s.ab, nu+1)
  K3 <- besselK(s.ab, nu-1)
  y <- 0.5*log(b/a) + log(2*K1) - (nu-1)*Kprime(s.ab)/K1 + s.ab/2/K1*(K2 + K3)
  return(y)
}

  ########################
  update_uts<-function(y, exps,exps2,sts,sts2,inv.sigma,a2.invb.inv.sigma,invb.inv.sigma,c.invb.absgam,c2.invb.absgam2.sigma){
    u.lambda = 0.5
    u.psi = (a2.invb.inv.sigma + 2*inv.sigma)
    u.chi = invb.inv.sigma*(y^2-2*y*exps+exps2) - 2*c.invb.absgam*sts*(y-exps) + c2.invb.absgam2.sigma*sts2
    u.chi[u.chi<=0] = 1e-16
    #
    E.uts = sapply(u.chi,function(x){sqrt(x/u.psi)*HyperbolicDist::besselRatio(sqrt(x*u.psi),u.lambda,1,Inf)})
    E.inv.uts = sapply(u.chi,function(x){sqrt(u.psi/x)*HyperbolicDist::besselRatio(sqrt(x*u.psi),u.lambda,1,Inf)-2*u.lambda/x})

  nu <- 0.5
  s.ab <- sqrt(u.psi*u.chi)
  K1 <- besselK(s.ab, nu)

    return(list(uts.lambda=u.lambda,
                uts.psi=u.psi,uts.chi=u.chi,
                E.uts=E.uts,E.inv.uts=E.inv.uts,
                E.log.uts=sum(Kprime(s.ab)/K1-0.5*log(u.psi/u.chi)),
                tot.entrop=sum(gig_entrop(u.psi,u.chi))))
  }

    ########################
  update_theta <- function(ex.f, ex.q) {
    ##########
    m <- sm <- matrix(NA_real_, p+J, TT)   
    #m <- sm <- matrix(NA_real_, p, TT)
    C <- sC <- array(NA_real_, c(p+J, p+J, TT))
    #C <- sC <- array(NA_real_, c(p, p, TT)) 
    ##########
    standard.forecast.errors <- array(NA_real_, c(J+1,TT))
    standard.forecast.errors.k <- array(NA_real_, c(J+1,TT))
    ##########
    #
    a = as.vector(GG[, , 1] %*% m0)
    P = GG[, , 1] %*% C0 %*% t(GG[, , 1])
    R = P + ex.df.mat * P
    R = (R + t(R))/2
    #
    ##f = t(FF[, , 1]) %*% a + ex.f[, 1]*0
    ##q = t(FF[, , 1]) %*% R %*% FF[, , 1] + ex.q[,, 1]*0+diag(J+1)*0.01

    
    f = t(FF[, , 1]) %*% a + ex.f[, 1]
    q = t(FF[, , 1]) %*% R %*% FF[, , 1] + ex.q[,, 1]
    q = 0.5*q + 0.5*t(q)
    #
    # q.inv <- compute_cholesky(q, compute_sqrt_inverse = FALSE)
    # q.inv <- as.matrix(q.inv$inverse) 
    svd.q = svd(q)
    q.inv = svd.q$u%*%diag(1/svd.q$d,dim(q)[1])%*%t(svd.q$u)
    q.inv.sqrt <- compute_cholesky(q, compute_sqrt_inverse = TRUE)
    q.inv.sqrt <- as.matrix(q.inv.sqrt$sqrt_inverse)
    #
    m[, 1] = as.matrix(a + R %*% FF[, , 1] %*% q.inv %*% (y[, 1] - f))
    C[, , 1] = as.matrix(R - R %*% FF[, , 1] %*% t(q.inv) %*% t(FF[, , 1]) %*% t(R))
    C[, , 1] = (C[, , 1] + t(C[, , 1]))/2
    #
    standard.forecast.errors[, 1] = q.inv.sqrt %*% (y[, 1] - f)
    
    ##########
    ## K step ahead forecast error
    # t+k forecast
    H <- H_t_k_r(GG, t = 1, k = k, r = k)
    # f_{t+k}
    a_1k <- H %*% m0
    fk = t(FF[, , 1 + k]) %*% a_1k + ex.f[, 1 + k]
    # q_{t+k}
    Pk = H %*% C0 %*% t(H)
    R_1k = Pk + ex.df.mat.k * Pk
    qk = t(FF[, , 1 + k]) %*% R_1k %*% FF[, , 1 + k] + ex.q[,, 1 + k]
    
    qk.inv <- compute_cholesky(qk, compute_sqrt_inverse = FALSE)
    qk.inv <- as.matrix(qk.inv$inverse) 
    qk.inv.sqrt <- compute_cholesky(qk, compute_sqrt_inverse = TRUE)
    qk.inv.sqrt <- as.matrix(qk.inv.sqrt$sqrt_inverse)
    
    # e_{t+k}
    standard.forecast.errors.k[, 1] <- qk.inv.sqrt%*%(y[, 1+k] - fk)
    
    ##########
    for (t in 2:TT) {
      ######
      a = as.vector(GG[, , t] %*% m[, (t - 1)])
      P = GG[, , t] %*% C[, , (t - 1)] %*% t(GG[, , t])
      R = P + ex.df.mat * P
      R = (R + t(R))/2
      #f = t(FF[, , t]) %*% a + ex.f[, t]*0
      fB = t(FF[, , t]) %*% R
      #q = fB %*% FF[, , t] + ex.q[,, t]*0+diag(J+1)*0.01
      f = t(FF[, , t]) %*% a + ex.f[, t]
      q = t(FF[, , t]) %*% R %*% FF[, , t] + ex.q[,, t]
      #
      # q.inv <- compute_cholesky(q, compute_sqrt_inverse = FALSE)
      # q.inv <- as.matrix(q.inv$inverse) 
      svd.q = svd(q)
      q.inv = svd.q$u%*%diag(1/svd.q$d,dim(q)[1])%*%t(svd.q$u)
      q.inv.sqrt <- compute_cholesky(q, compute_sqrt_inverse = TRUE)
      q.inv.sqrt <- as.matrix(q.inv.sqrt$sqrt_inverse)
      #
      m[, t] = matrix(a + R %*% FF[, , t] %*% q.inv %*% (y[, t] - f))
      C[, , t] = matrix(R - R %*% FF[, , t] %*% q.inv %*% t(FF[, , t]) %*% t(R))
      C[, , t] = (C[, , t] + t(C[, , t]))/2
      ######
      standard.forecast.errors[, t] = q.inv.sqrt %*% (y[, t] - f)
      ######
      if((t + k) <= TT){
        # t+k forecast
        H <- H_t_k_r(GG, t = t, k = k, r = k)
        # f_{t+k}
        a_1k <- H %*% m[, (t - 1)]
        fk = t(FF[, , t + k]) %*% a_1k + ex.f[, t + k]
        # q_{t+k}
        Pk = H %*% C[, , (t - 1)] %*% t(H)
        R_1k = Pk + ex.df.mat.k * Pk
        qk = t(FF[, , t + k]) %*% R_1k %*% FF[, , t + k] + ex.q[,, t + k]
        
        qk.inv <- compute_cholesky(qk, compute_sqrt_inverse = FALSE)
        qk.inv <- as.matrix(qk.inv$inverse) 
        qk.inv.sqrt <- compute_cholesky(qk, compute_sqrt_inverse = TRUE)
        qk.inv.sqrt <- as.matrix(qk.inv.sqrt$sqrt_inverse)
        
        # e_{t+k}
        standard.forecast.errors.k[, t] <- qk.inv.sqrt %*% (y[, t+k] - fk)
      }
    }
    ##########
    ##########
    sC[, , TT] = C[, , TT]
    sm[, TT] = m[, TT]



    elbo <- 0
    elbo <- elbo +0.5*determinant(as.matrix(sC[, , TT]), logarithm = TRUE)$modulus[1]
    elbo <- elbo -0.5*determinant(as.matrix(C0), logarithm = TRUE)$modulus[1]
    ##########
    for (t in (TT - 1):1) {
      P = GG[, , (t + 1)] %*% C[, , (t)] %*% t(GG[, , (t + 1)])
      R = P + ex.df.mat * P
      R = (R + t(R))/2
      #
      # R.inv <- compute_cholesky(R, compute_sqrt_inverse = FALSE)
      # R.inv <- as.matrix(R.inv$inverse) 
      svd.R = svd(R)
      R.inv = svd.R$u%*%diag(1/svd.R$d,dim(R)[1])%*%t(svd.R$u)
      #
      sB = C[, , t] %*% t(GG[, , t+1]) %*% R.inv
      # WHY sm and not THETA -> BECAUSE ITS THE MARGINAL, NOT THE FULL POSTERIOR
      sm[, t] = m[, t] + sB %*% (sm[, (t + 1)] - as.vector(GG[, , (t + 1)] %*% m[, (t)]))
      # IS THIS RIGHT?
      sC[, , t] = as.matrix(C[, , t] + sB %*% (sC[, , (t + 1)] - R) %*% t(sB))
      sC[, , t] = (sC[, , t] + t(sC[, , t]))/2
    ##########
    # ELBO
    ########## 
    W_t_1 <- ex.df.mat * P
    svd.W = svd(W_t_1)
    W.inv = svd.W$u%*%diag(1/svd.W$d,dim(W_t_1)[1])%*%t(svd.W$u)
    CBCB <- sC[, , t+1] - sB%*%sC[, , t+1]%*%t(sB)
    elbo <- elbo -0.5*determinant(as.matrix(W_t_1), logarithm = TRUE)$modulus[1]
    elbo <- elbo +0.5*determinant(as.matrix(CBCB), logarithm = TRUE)$modulus[1]
    ee <- sm[, t+1]-GG[, , (t + 1)]%*%sm[, t]
    XX <- sC[, , t+1] + P - 2*sB%*%sC[, , t+1]+ee%*%t(ee)
    XX <- W.inv %*% XX
    elbo <- elbo -0.5*sum(diag(XX))    
    ########## 
    a = as.vector(GG[, , t+1] %*% m[, (t)])
    CBRB = sC[, , t] - sB%*%sC[, , t+1]%*%t(sB)
    svd.CBRB = svd(CBRB)
    CBRB.inv = svd.CBRB$u%*%diag(1/svd.CBRB$d,dim(CBRB)[1])%*%t(svd.CBRB$u)
    xx <- sm[, t]-m[, t]-sB%*%(sm[, t+1]-a)
    xx <- CBRB.inv%*%(xx%*%t(xx))
    elbo <- elbo +0.5*sum(diag(xx)) 
    elbo <- elbo +0.5*determinant(as.matrix(CBRB), logarithm = TRUE)$modulus[1]
    }

    ## Smoothing at time 0 
    P = GG[, , (1)] %*% C0 %*% t(GG[, , (1)])
    R = P + ex.df.mat * P
    R = (R + t(R))/2
    svd.R = svd(R)
    R.inv = svd.R$u%*%diag(1/svd.R$d,dim(R)[1])%*%t(svd.R$u)
    sB = C0 %*% t(GG[, , 1]) %*% R.inv
    sm_0 = m0 + sB %*% (sm[, (1)] - as.vector(GG[, , (1)] %*% m0))
    sC_0 = as.matrix(C0 + sB %*% (sC[, , (1)] - R) %*% t(sB))
    sC_0 = (sC_0 + t(sC_0))/2
    ##########  
    W_t_1 <- ex.df.mat * P
    svd.W = svd(W_t_1)
    W.inv = svd.W$u%*%diag(1/svd.W$d,dim(W_t_1)[1])%*%t(svd.W$u)
    ee <- sm[, 1]-GG[, , (1)]%*%sm_0
    XX <- sC[, , 1] + P - 2*sB%*%sC[, , 1]+ee%*%t(ee)
    XX <- W.inv %*% XX
    elbo <- elbo -0.5*sum(diag(XX))
    XXX <- sC_0 + (sm_0-m0)%*%t(sm_0-m0)
    XXX <- solve(C0) %*% XXX
    elbo <- elbo -0.5*sum(diag(XXX))
    ########## 
    a = as.vector(GG[, , 1] %*% m0)
    CBRB = sC_0 - sB%*%sC[, , 1]%*%t(sB)
    svd.CBRB = svd(CBRB)
    CBRB.inv = svd.CBRB$u%*%diag(1/svd.CBRB$d,dim(CBRB)[1])%*%t(svd.CBRB$u)
    xx <- sm_0-m0-sB%*%(sm[, 1]-a)
    xx <- CBRB.inv%*%(xx%*%t(xx))
    elbo <- elbo +0.5*sum(diag(xx)) 
    elbo <- elbo +0.5*determinant(as.matrix(CBRB), logarithm = TRUE)$modulus[1]

    ########## 
    FF_t <- aperm(FF, c(2, 1, 3))
    multiply_matrices <- function(slice_index) {
      FF_t[,,slice_index] %*% sm[,slice_index]
    }
    result_list <- lapply(1:ncol(sm), multiply_matrices)
    result_array <- array(unlist(result_list), dim = c(J+1, 1, ncol(sm)))
    result_array <- aperm(result_array, c(1, 3, 2))[,,1]
    ##########
    ##########
    exps <- result_array
    ##########
    compute_product_1 <- function(t) {
      FF_t_slice <- FF_t[,,t]
      sC_slice <- sC[,,t]
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
    ##########
    standard.forecast.errors.k[,(TT-(k-1)):TT] <- standard.forecast.errors[,(TT-(k-1)):TT]
    
    return(list(exps = exps, vars = vars, exps2 = exps2, 
                standard.forecast.errors = standard.forecast.errors,
                standard.forecast.errors.k = standard.forecast.errors.k,
                sm = sm, sC = sC, fm = m, fC = C,
                elbo.part = elbo))
  }

  ########################
  PriorGammaDens <- function(gamma, prior) {
    crch::dtt(gamma, 
              location = prior[1], 
              scale = prior[2],   
              df = prior[3], 
              left = L, right = U, 
              log = FALSE)
  }
  
  LL <- L+0.001
  UU <- U-0.001

  # function approximate q(sigma,gamma) with importance sampling
  update_gamma_sigma<-function(y, prior_g, prior_s, gamma,var.gam,sigma,var.sig,exps,exps2,sts,sts2,uts,inv.uts, s_init, g_init){
    #############################################################################################################################################

    dq_transf <- function(theta_s,theta_g){
        sig <- exp(theta_s)
        gam <- LL+(-LL+UU)*exp(-exp(theta_g))
            a = A.fn(p0,gam); b = B.fn(p0,gam); c = C.fn(p0,gam); p.fn(p0,gam)

        yy <- log(PriorGammaDens(gam, prior_g)) - (prior_s[1] + 1) * log(sig) - prior_s[2]/sig
        yy <- yy - (1.5*TT)*log(sig) - (0.5*TT)*log(b)-sum(uts)/sig -
                0.5*sum( inv.uts*(y^2-2*y*exps+exps2)/sig
                        + (exps-y)*2*(inv.uts*c*abs(gam)*sts + a/sig)
                        + sig*inv.uts*(c^2)*(abs(gam)^2)*sts2
                        + 2*c*abs(gam)*sts*a
                        + (uts*a^2)/sig )/b
        yy <- yy + theta_s + theta_g - exp(theta_g)                   
        return(yy)
    }

    theta_s_init <- log(s_init)
    theta_g_init <- log(log((-L+U)/(-L+g_init)))
    initial_values <- c(theta_s_init, theta_g_init)

    # Optimization step
    optim_results <- optim(par = initial_values, 
                        fn = function(x) -dq_transf(x[1], x[2]), # Maximizing by minimizing the negative
                        method = "L-BFGS-B", # This method allows box constraints
                        lower = c(-Inf, -Inf), # Transform bounds for gam to theta_g space if needed
                        upper = c(Inf, Inf),
                        hessian = TRUE)
    # Evaluate the Hessian at the optimal value
    hessian_at_optimal <- -optim_results$hessian # SINCE WE MIN -f, not MAX f
    # Take the inverse of the Hessian
    inverse_hessian <- solve(hessian_at_optimal)

    LD_mu <- optim_results$par
    LD_S <- -inverse_hessian 

    Expected_f <- function(f, theta_s, theta_g){
        x <- hessian(func = f, x = LD_mu)%*%LD_S
        e <- f(LD_mu) + 0.5*sum(diag(x))
      return(e)
    }

    f.exp.theta_g <- function(theta){
      sig = exp(theta[1]); gam = LL+(-LL+UU)*exp(-exp(theta[2]));
      a = A.fn(p0,gam); b = B.fn(p0,gam); c = C.fn(p0,gam);
      yy <- exp(theta[2])
      return(yy)
    }

    f.log.sig.b <- function(theta){
      sig = exp(theta[1]); gam = LL+(-LL+UU)*exp(-exp(theta[2]));
      a = A.fn(p0,gam); b = B.fn(p0,gam); c = C.fn(p0,gam);
      yy <- log(sig*b)
      return(yy)
    }

    f.log.sig <- function(theta){
      sig = exp(theta[1]); gam = LL+(-LL+UU)*exp(-exp(theta[2]));
      a = A.fn(p0,gam); b = B.fn(p0,gam); c = C.fn(p0,gam);
      yy <- log(sig)
      return(yy)
    }

    f.prior.sig.gam <- function(theta){
      sig = exp(theta[1]); gam = LL+(-LL+UU)*exp(-exp(theta[2]));
      a = A.fn(p0,gam); b = B.fn(p0,gam); c = C.fn(p0,gam);
      yy <- crch::dtt(gam, location = prior_g[1], scale = prior_g[2], df = prior_g[3], left = L, right = U, log = TRUE)
      yy <- yy + nimble::dinvgamma(sig, shape = prior_s[1], scale =  prior_s[2], log = TRUE)
      return(yy)
    }


    f.c2.s.abs.g2.inv.b <- function(theta){
      sig = exp(theta[1]); gam = LL+(-LL+UU)*exp(-exp(theta[2]));
      a = A.fn(p0,gam); b = B.fn(p0,gam); c = C.fn(p0,gam);
      yy <- c^2*sig*abs(gam)^2/b
      return(yy)
    }

    f.inv.sig <- function(theta){
      sig = exp(theta[1])
      yy <- 1/sig
      return(yy)
    }

    f.c.abs.g.inv.b <- function(theta){
      gam = LL+(-LL+UU)*exp(-exp(theta[2]))
      b = B.fn(p0,gam); c = C.fn(p0,gam);
      yy <- c*abs(gam)/b
      return(yy)
    }

    f.c.abs.g.a.inv.b <- function(theta){
      sig = exp(theta[1]); gam = LL+(-LL+UU)*exp(-exp(theta[2]));
      a = A.fn(p0,gam); b = B.fn(p0,gam); c = C.fn(p0,gam);
      yy <- c*abs(gam)*a/b
      return(yy)
    }

    f.inv.s.inv.b <- function(theta){
      sig = exp(theta[1]); gam = LL+(-LL+UU)*exp(-exp(theta[2]));
      a = A.fn(p0,gam); b = B.fn(p0,gam); c = C.fn(p0,gam);
      yy <- 1/sig/b
      return(yy)
    }

    f.a.inv.s.inv.b <- function(theta){
      sig = exp(theta[1]); gam = LL+(-LL+UU)*exp(-exp(theta[2]));
      a = A.fn(p0,gam); b = B.fn(p0,gam); c = C.fn(p0,gam);
      yy <- a/sig/b
      return(yy)
    }

    f.a2.inv.s.inv.b <- function(theta){
      sig = exp(theta[1]); gam = LL+(-LL+UU)*exp(-exp(theta[2]));
      a = A.fn(p0,gam); b = B.fn(p0,gam); c = C.fn(p0,gam);
      yy <- a^2/sig/b
      return(yy)
    }

    #############################################################################################################################################
    sig_opt = exp(LD_mu[1]); gam_opt = LL+(-LL+UU)*exp(-exp(LD_mu[2]));
    # compute expectations
    E.gam = gam_opt
    #V.gam = sum((gamma.samples^2)*weights) - E.gam^2
    E.sigma = sig_opt
    #V.sigma = sum((sigma.samples^2)*weights) - E.sigma^2
    E.inv.sigma = Expected_f(f.inv.sig, LD_mu[1], LD_mu[2])
    E.c2.invb.absgam2.sigma = Expected_f(f.c2.s.abs.g2.inv.b, LD_mu[1], LD_mu[2])
    E.c.invb.absgam = Expected_f(f.c.abs.g.inv.b, LD_mu[1], LD_mu[2])
    E.c.a.invb.absgam = Expected_f(f.c.abs.g.a.inv.b, LD_mu[1], LD_mu[2])
    E.a2.invb.inv.sigma = Expected_f(f.a2.inv.s.inv.b, LD_mu[1], LD_mu[2])
    E.invb.inv.sigma = Expected_f(f.inv.s.inv.b, LD_mu[1], LD_mu[2])
    E.a.invb.inv.sigma = Expected_f(f.a.inv.s.inv.b, LD_mu[1], LD_mu[2])
    E.log.sig.b = Expected_f(f.log.sig.b, LD_mu[1], LD_mu[2])
    E.log.sig = Expected_f(f.log.sig, LD_mu[1], LD_mu[2])
    E.prior.sig.gam = Expected_f(f.prior.sig.gam, LD_mu[1], LD_mu[2])
    E.exp.theta_g =  Expected_f(f.exp.theta_g, LD_mu[1], LD_mu[2])

    entrop <- log(2*pi*exp(1)) + 0.5*determinant(as.matrix(LD_S), logarithm = TRUE)$modulus[1]-(log(-LL+UU)+sum(LD_mu)-E.exp.theta_g)

    return(list(E.sigma=E.sigma,E.inv.sigma=E.inv.sigma,E.gam=E.gam,
                E.c2.invb.absgam2.sigma = E.c2.invb.absgam2.sigma, E.c.invb.absgam = E.c.invb.absgam,
                E.c.a.invb.absgam = E.c.a.invb.absgam, E.a2.invb.inv.sigma = E.a2.invb.inv.sigma,
                E.invb.inv.sigma = E.invb.inv.sigma, E.a.invb.inv.sigma = E.a.invb.inv.sigma,
                Hess.LD = LD_S,
                E.log.sig.b=E.log.sig.b, 
                E.log.sig = E.log.sig, 
                E.prior.sig.gam= E.prior.sig.gam,
                entrop = entrop))
  }


#file_path <- "/home/jaguir26/projects/notebooks/variables_05_M.RData"
#load(file_path)
#new.uts.out = new.uts.out_05_M 
#new.sts.out =  new.sts.out_05_M  
#new.gamsig.out = new.gamsig.out_05_M 
#new.theta.out = new.theta.out_05_M 
#model$m0 <- new.theta.out_05_M$sm[,1]

crit_ELBO <- 0
ELBO <- 0
seq.elbo = ELBO
iter = 0
FLAG = TRUE
tol1 <- 1e-5
tol2 <- 1e-2 
########################
  tictoc::tic("run time")
  ########################
  while (FLAG) {
   
    ##########
    cur.uts.out = new.uts.out
    cur.sts.out = new.sts.out
    cur.gamsig.out = new.gamsig.out
    cur.theta.out = new.theta.out
    
    ############# Make a function with two options dependeoing on J!!!
    for (j in 1:(J+1)) {

      ########################      
      sts.dummy <- update_sts(y[j,],
                              cur.theta.out$exps[j,], 
                              cur.uts.out$E.inv.uts[j,], 
                              cur.gamsig.out$E.c2.invb.absgam2.sigma[j,], 
                              cur.gamsig.out$E.c.invb.absgam[j,], 
                              cur.gamsig.out$E.c.a.invb.absgam[j,])
      
      new.sts.out$E.sts[j,] <- sts.dummy$E.sts
      new.sts.out$E.sts2[j,] <- sts.dummy$E.sts2
      new.sts.out$tot.entrop[j,] <-  sts.dummy$tot.entrop
      
      ########################
      uts.dummy <- update_uts(y[j,],
                              cur.theta.out$exps[j,], 
                              cur.theta.out$exps2[j,], 
                              new.sts.out$E.sts[j,], 
                              new.sts.out$E.sts2[j,], 
                              cur.gamsig.out$E.inv.sigma[j,], 
                              cur.gamsig.out$E.a2.invb.inv.sigma[j,], 
                              cur.gamsig.out$E.invb.inv.sigma[j,], 
                              cur.gamsig.out$E.c.invb.absgam[j,], 
                              cur.gamsig.out$E.c2.invb.absgam2.sigma[j,]) 
      
      
      new.uts.out$E.uts[j,] <- uts.dummy$E.uts
      new.uts.out$E.inv.uts[j,] <- uts.dummy$E.inv.uts
      new.uts.out$E.log.uts[j,] <- uts.dummy$E.log.uts
      new.uts.out$tot.entrop[j,] <- uts.dummy$tot.entrop

      ########################
     gamsig.dummy <- update_gamma_sigma(y[j,],
                                         PriorGamma[j,],
                                         PriorSigma[j,],
                                         cur.gamsig.out$E.gam[j,], 
                                         cur.gamsig.out$V.gam[j,], 
                                         cur.gamsig.out$E.sigma[j,], 
                                         cur.gamsig.out$V.sigma[j,], 
                                         cur.theta.out$exps[j,], 
                                         cur.theta.out$exps2[j,], 
                                         new.sts.out$E.sts[j,], 
                                         new.sts.out$E.sts2[j,], 
                                         new.uts.out$E.uts[j,], 
                                         new.uts.out$E.inv.uts[j,],
                                         cur.gamsig.out$E.sigma[j,], 
                                         cur.gamsig.out$E.gam[j,])    


      new.gamsig.out$E.gam[j,] <- gamsig.dummy$E.gam
      new.gamsig.out$E.sigma[j,] <- gamsig.dummy$E.sigma
      new.gamsig.out$E.inv.sigma[j,] <- gamsig.dummy$E.inv.sigma
      new.gamsig.out$E.c2.invb.absgam2.sigma[j,] <- gamsig.dummy$E.c2.invb.absgam2.sigma
      new.gamsig.out$E.c.invb.absgam[j,] <- gamsig.dummy$E.c.invb.absgam
      new.gamsig.out$E.c.a.invb.absgam[j,] <- gamsig.dummy$E.c.a.invb.absgam
      new.gamsig.out$E.a2.invb.inv.sigma[j,] <- gamsig.dummy$E.a2.invb.inv.sigma
      new.gamsig.out$E.invb.inv.sigma[j,] <- gamsig.dummy$E.invb.inv.sigma
      new.gamsig.out$E.a.invb.inv.sigma[j,] <- gamsig.dummy$E.a.invb.inv.sigma
      new.gamsig.out$E.log.sig.b[j,] <- gamsig.dummy$E.log.sig.b
      new.gamsig.out$E.log.sig[j,] <- gamsig.dummy$E.log.sig
      new.gamsig.out$E.prior.sig.gam[j,] <- gamsig.dummy$E.prior.sig.gam
      new.gamsig.out$entrop[j,] <- gamsig.dummy$entrop
      
    }
    
    ########################
    FFF <- (new.gamsig.out$E.c.invb.absgam[,] * new.sts.out$E.sts + new.gamsig.out$E.a.invb.inv.sigma[,]/new.uts.out$E.inv.uts) / new.gamsig.out$E.invb.inv.sigma[,] 
    QQQ <- 1/(new.gamsig.out$E.invb.inv.sigma[,] * new.uts.out$E.inv.uts)
    if(J>0){
    QQQ <- array(apply(QQQ, 2, function(col) diag(col)), dim = c(J+1, J+1, TT))
    }else{
     QQQ <- array(QQQ, dim = c(J+1, J+1, TT))
    }


    ##########
    if (crit_ELBO < tol1) {
      new.theta.out  <- update_theta(FFF, QQQ)
      theta_update <- TRUE
    }else{
      theta_update <- FALSE
    }
    
    
    ##########
    seq.gamma = cbind(seq.gamma, new.gamsig.out$E.gam)
    seq.sigma = cbind(seq.sigma, new.gamsig.out$E.sigma)
    
    ##########
    # ELBO
    ##########
    elbo <- 0
    elbo <- elbo -TT/2*sum(new.gamsig.out$E.log.sig.b[,])
    elbo <- elbo -0.5*sum(new.uts.out$E.log.uts[,])
    elbo <- elbo -TT*(J+1)/2*log(pi)

    elbo <- elbo -0.5*sum((new.gamsig.out$E.invb.inv.sigma[,]*new.uts.out$E.inv.uts[,])*(y[,]^2-2*y[,]*cur.theta.out$exps[,]+new.theta.out$exps2[,]))
    elbo <- elbo +sum((y[,]-new.theta.out$exps[,])*(new.gamsig.out$E.c.invb.absgam[,]*new.sts.out$E.sts*new.uts.out$E.inv.uts[,]+new.gamsig.out$E.a.invb.inv.sigma[,]))-0.5*sum(new.sts.out$E.sts2[,]*new.uts.out$E.inv.uts[,]*new.gamsig.out$E.c2.invb.absgam2.sigma[,])
    elbo <- elbo -sum(new.gamsig.out$E.c.a.invb.absgam[,]*new.sts.out$E.sts[,])-0.5*sum(new.gamsig.out$E.a2.invb.inv.sigma[,]*new.uts.out$E.uts[,])

    elbo <- elbo -TT*sum(new.gamsig.out$E.log.sig[,])-sum(new.gamsig.out$E.inv.sigma[,]*new.uts.out$E.uts[,])-0.5*sum(new.sts.out$E.sts2[,])+sum(new.gamsig.out$E.prior.sig.gam[,])
    
    elbo <- elbo +sum(new.uts.out$tot.entrop[,])+sum(new.sts.out$E.tot.entrop[,])+sum(new.gamsig.out$E.sig.gam.entrop[,])

    elbo <- elbo + new.theta.out$elbo.part
    
    elbo <- elbo/TT/(J+1)

    crit_ELBO <- abs(ELBO-elbo)
    ELBO <- elbo
    seq.elbo =  cbind(seq.elbo, ELBO) 


    print(iter)
    print(c(elbo, crit_ELBO))
    flush.console()
    iter = iter + 1
    
    if(theta_update){
      if (crit_ELBO < tol2) {
        FLAG = FALSE
      }
    }

  }
########################
run.time = tictoc::toc(quiet = TRUE)





TT <- dim(Y)[2]
interpolate_spline <- function(idx, TT, y) {
  spline_result <- spline(x = idx, y = y, xout = 1:TT)
  spline_values <- spline_result$y
  return(spline_values)
}

interpolate_linear <- function(idx, TT, y) {
  approximate_result <- approx(x = idx, y = y, xout = 1:TT)
  approximate_values <- approximate_result$y
  return(approximate_values)
}

sig0 = seq.sigma[,dim(seq.sigma)[2]]
gam0 = seq.gamma[,dim(seq.gamma)[2]]

mm <- m
seqsm <- 0:(floor(TT/mm)-1)
idxm <- seqsm*mm+1

E1.e <- t(apply(new.theta.out$exps, 1, function(row) interpolate_spline(idxm, TT, row)))
E2.e <- t(apply(new.theta.out$exps2, 1, function(row) interpolate_spline(idxm, TT, row)))
E1.s <- t(apply(new.sts.out$E.sts, 1, function(row) interpolate_spline(idxm, TT, row)))
E2.s <- t(apply(new.sts.out$E.sts2, 1, function(row) interpolate_spline(idxm, TT, row)))
E1.u <- t(apply(new.uts.out$E.uts, 1, function(row) interpolate_spline(idxm, TT, row)))
E2.u <- t(apply(new.uts.out$E.inv.uts, 1, function(row) interpolate_spline(idxm, TT, row)))

E1 = array(gam0, c(J+1,1))
E2 = new.gamsig.out$V.gam
E3 = array(sig0, c(J+1,1)) 
E4 = new.gamsig.out$V.sig
E5 = new.gamsig.out$E.inv.sigma
E6 = new.gamsig.out$E.c2.invb.absgam2.sigma
E7 = new.gamsig.out$E.c.invb.absgam 
E8 = new.gamsig.out$E.c.a.invb.absgam 
E9 = new.gamsig.out$E.a2.invb.inv.sigma
E10 = new.gamsig.out$E.invb.inv.sigma 
E11 = new.gamsig.out$E.a.invb.inv.sigma
E12 = new.gamsig.out$E.log.sig.b
E13 = new.gamsig.out$E.log.sig 

replace_negatives_with_row_mean <- function(matrix_data) {
  # Apply the function to each row
  corrected_matrix <- apply(matrix_data, 1, function(row) {
    # Identify negative or zero values
    negative_indices <- which(row <= 0.02)
    # Replace negatives with the row mean excluding negative or zero values
    if (length(negative_indices) > 0) {
      positive_values <- row[row > 0]
      row_mean <- mean(positive_values)*0.01
      row[negative_indices] <- row_mean
    }
    return(row)
  })
  return(t(corrected_matrix))
}

E2.e <- replace_negatives_with_row_mean(E2.e)
E1.s <- replace_negatives_with_row_mean(E1.s)
E2.s <- replace_negatives_with_row_mean(E2.s)
E1.u <- replace_negatives_with_row_mean(E1.u)
E2.u <- replace_negatives_with_row_mean(E2.u)

new.theta.out <- list(exps = E1.e, 
                      exps2 = E2.e, 
                      sm_0 = new.theta.out$sm[,1])

new.sts.out <- list(E.sts = E1.s, 
                    E.sts2 = E2.s,
                    tot.entrop = array(0, c(J+1,1)))

new.uts.out <- list(E.uts = E1.u, 
                    E.inv.uts = E2.u,
                    E.log.uts = array(0, c(J+1,1)),
                    tot.entrop = array(0, c(J+1,1)))

new.gamsig.out <- list(E.gam = E1,
                       V.gam = E2, 
                       E.sigma = E3, 
                       V.sig = E4,
                       E.inv.sigma = E5, 
                       E.c2.invb.absgam2.sigma = E6, 
                       E.c.invb.absgam = E7,  
                       E.c.a.invb.absgam = E8, 
                       E.a2.invb.inv.sigma = E9, 
                       E.invb.inv.sigma = E10, 
                       E.a.invb.inv.sigma = E11,
                       E.log.sig.b = E12,
                       E.log.sig = E13,
                       E.prior.sig.gam = array(0, c(J+1,1)),
                       entrop = array(0, c(J+1,1)))


print("VB initialization finished")


################################################################################################################################################################
################################################################################################################################################################
################################################################################################################################################################
################################################################################################################################################################
################################################################################################################################################################
################################################################################################################################################################
################################################################################################################################################################
################################################################################################################################################################
################################################################################################################################################################
################################################################################################################################################################
################################################################################################################################################################
################################################################################################################################################################
################################################################################################################################################################
################################################################################################################################################################
################################################################################################################################################################
################################################################################################################################################################
################################################################################################################################################################
################################################################################################################################################################
Y <- rbind(t(as.matrix(ts_usgs)), t(as.matrix(ts_glofas)), t(as.matrix(ts_nws)))
TT <- dim(Y)[2]

m <- 1
seqs <- 0:(floor(TT/m)-1)
idx <- seqs*m+1
Y_batch <- Y[,idx]

df_t    <- 0.9995
df_s    <- 0.988
df_s67  <- 0.9995
m_yy <- mean(Y, na.rm = TRUE)
s_yy <- sd(Y, na.rm = TRUE)  
k <- 0.3*s_yy

trend.comp = polytrendMod(1, m0 = m_yy, C0 = k)
harm = harmonics
seas.comp = seasMod(p = 363.5854/m, h = harm , C0 = 0.5*k*diag(2*length(harm)))
model = combineMods(trend.comp, seas.comp)

y = Y_batch; p0 = 0.05; 
model = model; 


if(is.null(nrow(y))){ 
    JJJ <- 1
    y = array(y, c(JJJ,length(y)))
 }else{
    JJJ <- nrow(Y)
    y = array(y, c(JJJ,ncol(y)))
 }

df = c(df_t,df_s, df_s67); dim.df = c(1, 2*length(harm)-2, 2); 
tol = 0.001; 
n.IS = 3000; n.samp = 2000; 
PriorSigma = array(NA_real_, c(JJJ,2)); 
PriorGamma = array(NA_real_, c(JJJ,3)); 
verbose = TRUE; k = 5;

df_discrep <- rep(0.9999, JJJ-1)

  ########################
  TT = dim(y)[2] 
  J = dim(y)[1]-1 
  p = length(model$m0) 
  ########################
  m0 = c(model$m0,rep(0,J))
  # m0 = model$m0 # Erase
  C0 = bdiag(model$C0,diag(J))
  # C0 = model$C0 # Erase
  ########################
  model_simp <- model
  df_simp <- df
  dim.df_simp <- dim.df
  model_simp$GG = array(model_simp$GG, c(p, p, TT))
  model_simp$FF = array(model_simp$FF, c(p, 1, TT))
  df.mat = make_df_mat(df, dim.df, p)
  df.mat.k = make_df_mat_k(df, dim.df, p, k)
  ########################
  if(J<=0){ # Chanhe to ==0
  ex.df.mat <- df.mat
  ex.df.mat.k <- df.mat.k 
  }else{
  extra_df.mat <- make_df_mat(df_discrep,rep(1,J),J)
  extra_df.mat.k <- make_df_mat_k(df_discrep,rep(1,J),J,k)
  ex.df.mat <- bdiag(df.mat, extra_df.mat)
  ex.df.mat.k <- bdiag(df.mat.k, extra_df.mat.k)
  }

  ########################
  ########################
  GG = array( bdiag(model$GG,diag(J)), c(p+J, p+J, TT) )
  # GG = array(model$GG, c(p, p, TT) ) #Erase
  model$GG = GG
  
  F1 <- matrix(model$FF,p,J+1)
  F2 <- cbind(rep(0,J),diag(J))
  FF = array(rbind(F1,F2), c(p+J, 1+J, TT))
  # FF = array(F1, c(p, J+1, TT))#Erase
  model$FF = FF
  ########################
  ########################
  L = L.fn(p0)
  U = U.fn(p0)
  ########################
  ########### For every j
  for (j in 1:(J+1)) {
    if (!is.na(gam.init[j,])) {
      if (gam.init[j,] < L | gam.init[j,] > U) {
        stop(sprintf("gam.init must be between %s and %s for %s quantile", 
                     round(L, 3), round(U, 3), p0))
      }
    } 
  }

  ########################
  ########### For every j
  for (j in 1:(J+1)) {
    if (is.na(PriorSigma[j,1]) || is.na(PriorSigma[j,2])) {
      m_sigma = 1
      v_sigma = 1e+10
      PriorSigma[j,1] = (m_sigma^2)/(v_sigma) + 2 
      PriorSigma[j,2] = (m_sigma^3)/(v_sigma) + m_sigma 
    }
  }
  ########################
  ########### For every j
  for (j in 1:(J+1)) {
    if (is.na(PriorGamma[j,1]) || is.na(PriorGamma[j,2]) || is.na(PriorGamma[j,3])) {
      PriorGamma[j,1]  = 0
      PriorGamma[j,2]  = 1e+10
      PriorGamma[j,3] = 1
    }
  }
  
  
  ########################
  ########### For every j
  seq.gamma = new.gamsig.out$E.gam
  seq.sigma = new.gamsig.out$E.sigma
  ########################
  
update_sts<-function(y, exps,inv.uts,c2.invb.absgam2.sigma,c.invb.absgam,c.a.invb.absgam){
    s.sig2<-1/(1+c2.invb.absgam2.sigma*inv.uts); s.sig = sqrt(s.sig2)
    s.mu<-s.sig2*(c.invb.absgam*(y-exps)*inv.uts-c.a.invb.absgam)
    #
    E.sts = truncnorm::etruncnorm(a=rep(0,TT),b=rep(Inf,TT),mean=s.mu,sd=s.sig)
    V.sts = truncnorm::vtruncnorm(a=rep(0,TT),b=rep(Inf,TT),mean=s.mu,sd=s.sig)
    E.sts2 = s.mu^2 + s.sig2 + s.mu*s.sig*exp(stats::dnorm(-s.mu/s.sig,log = TRUE)-stats::pnorm(s.mu/s.sig,log.p = TRUE))
    return(list(sts.sig2=s.sig2,sts.mu=s.mu,
                E.sts=E.sts,E.sts2=E.sts2,
                tot.entrop = sum(0.5*log2(2*pi*exp(1)*s.sig2) - 1 )))
  }
  
Kprime <- function(x){
  sqrt(pi/2/x) * expint_E1(2*x) * exp(x)
}

gig_entrop <- function(a,b){
  nu <- 0.5
  s.ab <- sqrt(a*b)
  K1 <- besselK(s.ab, nu)
  K2 <- besselK(s.ab, nu+1)
  K3 <- besselK(s.ab, nu-1)
  y <- 0.5*log(b/a) + log(2*K1) - (nu-1)*Kprime(s.ab)/K1 + s.ab/2/K1*(K2 + K3)
  return(y)
}

  ########################
  update_uts<-function(y, exps,exps2,sts,sts2,inv.sigma,a2.invb.inv.sigma,invb.inv.sigma,c.invb.absgam,c2.invb.absgam2.sigma){
    u.lambda = 0.5
    u.psi = (a2.invb.inv.sigma + 2*inv.sigma)
    u.chi = invb.inv.sigma*(y^2-2*y*exps+exps2) - 2*c.invb.absgam*sts*(y-exps) + c2.invb.absgam2.sigma*sts2
    u.chi[u.chi<=0] = 1e-16
    #
    E.uts = sapply(u.chi,function(x){sqrt(x/u.psi)*HyperbolicDist::besselRatio(sqrt(x*u.psi),u.lambda,1,Inf)})
    E.inv.uts = sapply(u.chi,function(x){sqrt(u.psi/x)*HyperbolicDist::besselRatio(sqrt(x*u.psi),u.lambda,1,Inf)-2*u.lambda/x})

  nu <- 0.5
  s.ab <- sqrt(u.psi*u.chi)
  K1 <- besselK(s.ab, nu)

    return(list(uts.lambda=u.lambda,
                uts.psi=u.psi,uts.chi=u.chi,
                E.uts=E.uts,E.inv.uts=E.inv.uts,
                E.log.uts=sum(Kprime(s.ab)/K1-0.5*log(u.psi/u.chi)),
                tot.entrop=sum(gig_entrop(u.psi,u.chi))))
  }

    ########################
  update_theta <- function(ex.f, ex.q) {
    ##########
    m <- sm <- matrix(NA_real_, p+J, TT)   
    #m <- sm <- matrix(NA_real_, p, TT)
    C <- sC <- array(NA_real_, c(p+J, p+J, TT))
    #C <- sC <- array(NA_real_, c(p, p, TT)) 
    ##########
    standard.forecast.errors <- array(NA_real_, c(J+1,TT))
    standard.forecast.errors.k <- array(NA_real_, c(J+1,TT))
    ##########
    #
    a = as.vector(GG[, , 1] %*% m0)
    P = GG[, , 1] %*% C0 %*% t(GG[, , 1])
    R = P + ex.df.mat * P
    R = (R + t(R))/2
    #
    ##f = t(FF[, , 1]) %*% a + ex.f[, 1]*0
    ##q = t(FF[, , 1]) %*% R %*% FF[, , 1] + ex.q[,, 1]*0+diag(J+1)*0.01

    
    f = t(FF[, , 1]) %*% a + ex.f[, 1]
    q = t(FF[, , 1]) %*% R %*% FF[, , 1] + ex.q[,, 1]
    q = 0.5*q + 0.5*t(q)
    #
    # q.inv <- compute_cholesky(q, compute_sqrt_inverse = FALSE)
    # q.inv <- as.matrix(q.inv$inverse) 
    svd.q = svd(q)
    q.inv = svd.q$u%*%diag(1/svd.q$d,dim(q)[1])%*%t(svd.q$u)
    q.inv.sqrt <- compute_cholesky(q, compute_sqrt_inverse = TRUE)
    q.inv.sqrt <- as.matrix(q.inv.sqrt$sqrt_inverse)
    #
    m[, 1] = as.matrix(a + R %*% FF[, , 1] %*% q.inv %*% (y[, 1] - f))
    C[, , 1] = as.matrix(R - R %*% FF[, , 1] %*% t(q.inv) %*% t(FF[, , 1]) %*% t(R))
    C[, , 1] = (C[, , 1] + t(C[, , 1]))/2
    #
    standard.forecast.errors[, 1] = q.inv.sqrt %*% (y[, 1] - f)
    
    ##########
    ## K step ahead forecast error
    # t+k forecast
    H <- H_t_k_r(GG, t = 1, k = k, r = k)
    # f_{t+k}
    a_1k <- H %*% m0
    fk = t(FF[, , 1 + k]) %*% a_1k + ex.f[, 1 + k]
    # q_{t+k}
    Pk = H %*% C0 %*% t(H)
    R_1k = Pk + ex.df.mat.k * Pk
    qk = t(FF[, , 1 + k]) %*% R_1k %*% FF[, , 1 + k] + ex.q[,, 1 + k]
    
    qk.inv <- compute_cholesky(qk, compute_sqrt_inverse = FALSE)
    qk.inv <- as.matrix(qk.inv$inverse) 
    qk.inv.sqrt <- compute_cholesky(qk, compute_sqrt_inverse = TRUE)
    qk.inv.sqrt <- as.matrix(qk.inv.sqrt$sqrt_inverse)
    
    # e_{t+k}
    standard.forecast.errors.k[, 1] <- qk.inv.sqrt%*%(y[, 1+k] - fk)
    
    ##########
    for (t in 2:TT) {
      ######
      a = as.vector(GG[, , t] %*% m[, (t - 1)])
      P = GG[, , t] %*% C[, , (t - 1)] %*% t(GG[, , t])
      R = P + ex.df.mat * P
      R = (R + t(R))/2
      #f = t(FF[, , t]) %*% a + ex.f[, t]*0
      fB = t(FF[, , t]) %*% R
      #q = fB %*% FF[, , t] + ex.q[,, t]*0+diag(J+1)*0.01
      f = t(FF[, , t]) %*% a + ex.f[, t]
      q = t(FF[, , t]) %*% R %*% FF[, , t] + ex.q[,, t]
      #
      # q.inv <- compute_cholesky(q, compute_sqrt_inverse = FALSE)
      # q.inv <- as.matrix(q.inv$inverse) 
      svd.q = svd(q)
      q.inv = svd.q$u%*%diag(1/svd.q$d,dim(q)[1])%*%t(svd.q$u)
      q.inv.sqrt <- compute_cholesky(q, compute_sqrt_inverse = TRUE)
      q.inv.sqrt <- as.matrix(q.inv.sqrt$sqrt_inverse)
      #
      m[, t] = matrix(a + R %*% FF[, , t] %*% q.inv %*% (y[, t] - f))
      C[, , t] = matrix(R - R %*% FF[, , t] %*% q.inv %*% t(FF[, , t]) %*% t(R))
      C[, , t] = (C[, , t] + t(C[, , t]))/2
      ######
      standard.forecast.errors[, t] = q.inv.sqrt %*% (y[, t] - f)
      ######
      if((t + k) <= TT){
        # t+k forecast
        H <- H_t_k_r(GG, t = t, k = k, r = k)
        # f_{t+k}
        a_1k <- H %*% m[, (t - 1)]
        fk = t(FF[, , t + k]) %*% a_1k + ex.f[, t + k]
        # q_{t+k}
        Pk = H %*% C[, , (t - 1)] %*% t(H)
        R_1k = Pk + ex.df.mat.k * Pk
        qk = t(FF[, , t + k]) %*% R_1k %*% FF[, , t + k] + ex.q[,, t + k]
        
        qk.inv <- compute_cholesky(qk, compute_sqrt_inverse = FALSE)
        qk.inv <- as.matrix(qk.inv$inverse) 
        qk.inv.sqrt <- compute_cholesky(qk, compute_sqrt_inverse = TRUE)
        qk.inv.sqrt <- as.matrix(qk.inv.sqrt$sqrt_inverse)
        
        # e_{t+k}
        standard.forecast.errors.k[, t] <- qk.inv.sqrt %*% (y[, t+k] - fk)
      }
    }
    ##########
    ##########
    sC[, , TT] = C[, , TT]
    sm[, TT] = m[, TT]



    elbo <- 0
    elbo <- elbo +0.5*determinant(as.matrix(sC[, , TT]), logarithm = TRUE)$modulus[1]
    elbo <- elbo -0.5*determinant(as.matrix(C0), logarithm = TRUE)$modulus[1]
    ##########
    for (t in (TT - 1):1) {
      P = GG[, , (t + 1)] %*% C[, , (t)] %*% t(GG[, , (t + 1)])
      R = P + ex.df.mat * P
      R = (R + t(R))/2
      #
      # R.inv <- compute_cholesky(R, compute_sqrt_inverse = FALSE)
      # R.inv <- as.matrix(R.inv$inverse) 
      svd.R = svd(R)
      R.inv = svd.R$u%*%diag(1/svd.R$d,dim(R)[1])%*%t(svd.R$u)
      #
      sB = C[, , t] %*% t(GG[, , t+1]) %*% R.inv
      # WHY sm and not THETA -> BECAUSE ITS THE MARGINAL, NOT THE FULL POSTERIOR
      sm[, t] = m[, t] + sB %*% (sm[, (t + 1)] - as.vector(GG[, , (t + 1)] %*% m[, (t)]))
      # IS THIS RIGHT?
      sC[, , t] = as.matrix(C[, , t] + sB %*% (sC[, , (t + 1)] - R) %*% t(sB))
      sC[, , t] = (sC[, , t] + t(sC[, , t]))/2
    ##########
    # ELBO
    ########## 
    W_t_1 <- ex.df.mat * P
    svd.W = svd(W_t_1)
    W.inv = svd.W$u%*%diag(1/svd.W$d,dim(W_t_1)[1])%*%t(svd.W$u)
    CBCB <- sC[, , t+1] - sB%*%sC[, , t+1]%*%t(sB)
    elbo <- elbo -0.5*determinant(as.matrix(W_t_1), logarithm = TRUE)$modulus[1]
    elbo <- elbo +0.5*determinant(as.matrix(CBCB), logarithm = TRUE)$modulus[1]
    ee <- sm[, t+1]-GG[, , (t + 1)]%*%sm[, t]
    XX <- sC[, , t+1] + P - 2*sB%*%sC[, , t+1]+ee%*%t(ee)
    XX <- W.inv %*% XX
    elbo <- elbo -0.5*sum(diag(XX))    
    ########## 
    a = as.vector(GG[, , t+1] %*% m[, (t)])
    CBRB = sC[, , t] - sB%*%sC[, , t+1]%*%t(sB)
    svd.CBRB = svd(CBRB)
    CBRB.inv = svd.CBRB$u%*%diag(1/svd.CBRB$d,dim(CBRB)[1])%*%t(svd.CBRB$u)
    xx <- sm[, t]-m[, t]-sB%*%(sm[, t+1]-a)
    xx <- CBRB.inv%*%(xx%*%t(xx))
    elbo <- elbo +0.5*sum(diag(xx)) 
    elbo <- elbo +0.5*determinant(as.matrix(CBRB), logarithm = TRUE)$modulus[1]
    }

    ## Smoothing at time 0 
    P = GG[, , (1)] %*% C0 %*% t(GG[, , (1)])
    R = P + ex.df.mat * P
    R = (R + t(R))/2
    svd.R = svd(R)
    R.inv = svd.R$u%*%diag(1/svd.R$d,dim(R)[1])%*%t(svd.R$u)
    sB = C0 %*% t(GG[, , 1]) %*% R.inv
    sm_0 = m0 + sB %*% (sm[, (1)] - as.vector(GG[, , (1)] %*% m0))
    sC_0 = as.matrix(C0 + sB %*% (sC[, , (1)] - R) %*% t(sB))
    sC_0 = (sC_0 + t(sC_0))/2
    ##########  
    W_t_1 <- ex.df.mat * P
    svd.W = svd(W_t_1)
    W.inv = svd.W$u%*%diag(1/svd.W$d,dim(W_t_1)[1])%*%t(svd.W$u)
    ee <- sm[, 1]-GG[, , (1)]%*%sm_0
    XX <- sC[, , 1] + P - 2*sB%*%sC[, , 1]+ee%*%t(ee)
    XX <- W.inv %*% XX
    elbo <- elbo -0.5*sum(diag(XX))
    XXX <- sC_0 + (sm_0-m0)%*%t(sm_0-m0)
    XXX <- solve(C0) %*% XXX
    elbo <- elbo -0.5*sum(diag(XXX))
    ########## 
    a = as.vector(GG[, , 1] %*% m0)
    CBRB = sC_0 - sB%*%sC[, , 1]%*%t(sB)
    svd.CBRB = svd(CBRB)
    CBRB.inv = svd.CBRB$u%*%diag(1/svd.CBRB$d,dim(CBRB)[1])%*%t(svd.CBRB$u)
    xx <- sm_0-m0-sB%*%(sm[, 1]-a)
    xx <- CBRB.inv%*%(xx%*%t(xx))
    elbo <- elbo +0.5*sum(diag(xx)) 
    elbo <- elbo +0.5*determinant(as.matrix(CBRB), logarithm = TRUE)$modulus[1]

    ########## 
    FF_t <- aperm(FF, c(2, 1, 3))
    multiply_matrices <- function(slice_index) {
      FF_t[,,slice_index] %*% sm[,slice_index]
    }
    result_list <- lapply(1:ncol(sm), multiply_matrices)
    result_array <- array(unlist(result_list), dim = c(J+1, 1, ncol(sm)))
    result_array <- aperm(result_array, c(1, 3, 2))[,,1]
    ##########
    ##########
    exps <- result_array
    ##########
    compute_product_1 <- function(t) {
      FF_t_slice <- FF_t[,,t]
      sC_slice <- sC[,,t]
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
    ##########
    standard.forecast.errors.k[,(TT-(k-1)):TT] <- standard.forecast.errors[,(TT-(k-1)):TT]
    
    return(list(exps = exps, vars = vars, exps2 = exps2, 
                standard.forecast.errors = standard.forecast.errors,
                standard.forecast.errors.k = standard.forecast.errors.k,
                sm = sm, sC = sC, fm = m, fC = C,
                elbo.part = elbo))
  }

  ########################
  PriorGammaDens <- function(gamma, prior) {
    crch::dtt(gamma, 
              location = prior[1], 
              scale = prior[2],   
              df = prior[3], 
              left = L, right = U, 
              log = FALSE)
  }
  
  LL <- L+0.001
  UU <- U-0.001

  # function approximate q(sigma,gamma) with importance sampling
  update_gamma_sigma<-function(y, prior_g, prior_s, gamma,var.gam,sigma,var.sig,exps,exps2,sts,sts2,uts,inv.uts, s_init, g_init){
    #############################################################################################################################################

    dq_transf <- function(theta_s,theta_g){
        sig <- exp(theta_s)
        gam <- LL+(-LL+UU)*exp(-exp(theta_g))
            a = A.fn(p0,gam); b = B.fn(p0,gam); c = C.fn(p0,gam); p.fn(p0,gam)

        yy <- log(PriorGammaDens(gam, prior_g)) - (prior_s[1] + 1) * log(sig) - prior_s[2]/sig
        yy <- yy - (1.5*TT)*log(sig) - (0.5*TT)*log(b)-sum(uts)/sig -
                0.5*sum( inv.uts*(y^2-2*y*exps+exps2)/sig
                        + (exps-y)*2*(inv.uts*c*abs(gam)*sts + a/sig)
                        + sig*inv.uts*(c^2)*(abs(gam)^2)*sts2
                        + 2*c*abs(gam)*sts*a
                        + (uts*a^2)/sig )/b
        yy <- yy + theta_s + theta_g - exp(theta_g)                   
        return(yy)
    }

    theta_s_init <- log(s_init)
    theta_g_init <- log(log((-L+U)/(-L+g_init)))
    initial_values <- c(theta_s_init, theta_g_init)

    # Optimization step
    optim_results <- optim(par = initial_values, 
                        fn = function(x) -dq_transf(x[1], x[2]), # Maximizing by minimizing the negative
                        method = "L-BFGS-B", # This method allows box constraints
                        lower = c(-Inf, -Inf), # Transform bounds for gam to theta_g space if needed
                        upper = c(Inf, Inf),
                        hessian = TRUE)
    # Evaluate the Hessian at the optimal value
    hessian_at_optimal <- -optim_results$hessian # SINCE WE MIN -f, not MAX f
    # Take the inverse of the Hessian
    inverse_hessian <- solve(hessian_at_optimal)

    LD_mu <- optim_results$par
    LD_S <- -inverse_hessian 

    Expected_f <- function(f, theta_s, theta_g){
        x <- hessian(func = f, x = LD_mu)%*%LD_S
        e <- f(LD_mu) + 0.5*sum(diag(x))
      return(e)
    }

    f.exp.theta_g <- function(theta){
      sig = exp(theta[1]); gam = LL+(-LL+UU)*exp(-exp(theta[2]));
      a = A.fn(p0,gam); b = B.fn(p0,gam); c = C.fn(p0,gam);
      yy <- exp(theta[2])
      return(yy)
    }

    f.log.sig.b <- function(theta){
      sig = exp(theta[1]); gam = LL+(-LL+UU)*exp(-exp(theta[2]));
      a = A.fn(p0,gam); b = B.fn(p0,gam); c = C.fn(p0,gam);
      yy <- log(sig*b)
      return(yy)
    }

    f.log.sig <- function(theta){
      sig = exp(theta[1]); gam = LL+(-LL+UU)*exp(-exp(theta[2]));
      a = A.fn(p0,gam); b = B.fn(p0,gam); c = C.fn(p0,gam);
      yy <- log(sig)
      return(yy)
    }

    f.prior.sig.gam <- function(theta){
      sig = exp(theta[1]); gam = LL+(-LL+UU)*exp(-exp(theta[2]));
      a = A.fn(p0,gam); b = B.fn(p0,gam); c = C.fn(p0,gam);
      yy <- crch::dtt(gam, location = prior_g[1], scale = prior_g[2], df = prior_g[3], left = L, right = U, log = TRUE)
      yy <- yy + nimble::dinvgamma(sig, shape = prior_s[1], scale =  prior_s[2], log = TRUE)
      return(yy)
    }


    f.c2.s.abs.g2.inv.b <- function(theta){
      sig = exp(theta[1]); gam = LL+(-LL+UU)*exp(-exp(theta[2]));
      a = A.fn(p0,gam); b = B.fn(p0,gam); c = C.fn(p0,gam);
      yy <- c^2*sig*abs(gam)^2/b
      return(yy)
    }

    f.inv.sig <- function(theta){
      sig = exp(theta[1])
      yy <- 1/sig
      return(yy)
    }

    f.c.abs.g.inv.b <- function(theta){
      gam = LL+(-LL+UU)*exp(-exp(theta[2]))
      b = B.fn(p0,gam); c = C.fn(p0,gam);
      yy <- c*abs(gam)/b
      return(yy)
    }

    f.c.abs.g.a.inv.b <- function(theta){
      sig = exp(theta[1]); gam = LL+(-LL+UU)*exp(-exp(theta[2]));
      a = A.fn(p0,gam); b = B.fn(p0,gam); c = C.fn(p0,gam);
      yy <- c*abs(gam)*a/b
      return(yy)
    }

    f.inv.s.inv.b <- function(theta){
      sig = exp(theta[1]); gam = LL+(-LL+UU)*exp(-exp(theta[2]));
      a = A.fn(p0,gam); b = B.fn(p0,gam); c = C.fn(p0,gam);
      yy <- 1/sig/b
      return(yy)
    }

    f.a.inv.s.inv.b <- function(theta){
      sig = exp(theta[1]); gam = LL+(-LL+UU)*exp(-exp(theta[2]));
      a = A.fn(p0,gam); b = B.fn(p0,gam); c = C.fn(p0,gam);
      yy <- a/sig/b
      return(yy)
    }

    f.a2.inv.s.inv.b <- function(theta){
      sig = exp(theta[1]); gam = LL+(-LL+UU)*exp(-exp(theta[2]));
      a = A.fn(p0,gam); b = B.fn(p0,gam); c = C.fn(p0,gam);
      yy <- a^2/sig/b
      return(yy)
    }

    #############################################################################################################################################
    sig_opt = exp(LD_mu[1]); gam_opt = LL+(-LL+UU)*exp(-exp(LD_mu[2]));
    # compute expectations
    E.gam = gam_opt
    #V.gam = sum((gamma.samples^2)*weights) - E.gam^2
    E.sigma = sig_opt
    #V.sigma = sum((sigma.samples^2)*weights) - E.sigma^2
    E.inv.sigma = Expected_f(f.inv.sig, LD_mu[1], LD_mu[2])
    E.c2.invb.absgam2.sigma = Expected_f(f.c2.s.abs.g2.inv.b, LD_mu[1], LD_mu[2])
    E.c.invb.absgam = Expected_f(f.c.abs.g.inv.b, LD_mu[1], LD_mu[2])
    E.c.a.invb.absgam = Expected_f(f.c.abs.g.a.inv.b, LD_mu[1], LD_mu[2])
    E.a2.invb.inv.sigma = Expected_f(f.a2.inv.s.inv.b, LD_mu[1], LD_mu[2])
    E.invb.inv.sigma = Expected_f(f.inv.s.inv.b, LD_mu[1], LD_mu[2])
    E.a.invb.inv.sigma = Expected_f(f.a.inv.s.inv.b, LD_mu[1], LD_mu[2])
    E.log.sig.b = Expected_f(f.log.sig.b, LD_mu[1], LD_mu[2])
    E.log.sig = Expected_f(f.log.sig, LD_mu[1], LD_mu[2])
    E.prior.sig.gam = Expected_f(f.prior.sig.gam, LD_mu[1], LD_mu[2])
    E.exp.theta_g =  Expected_f(f.exp.theta_g, LD_mu[1], LD_mu[2])

    entrop <- log(2*pi*exp(1)) + 0.5*determinant(as.matrix(LD_S), logarithm = TRUE)$modulus[1]-(log(-LL+UU)+sum(LD_mu)-E.exp.theta_g)

    return(list(E.sigma=E.sigma,E.inv.sigma=E.inv.sigma,E.gam=E.gam,
                E.c2.invb.absgam2.sigma = E.c2.invb.absgam2.sigma, E.c.invb.absgam = E.c.invb.absgam,
                E.c.a.invb.absgam = E.c.a.invb.absgam, E.a2.invb.inv.sigma = E.a2.invb.inv.sigma,
                E.invb.inv.sigma = E.invb.inv.sigma, E.a.invb.inv.sigma = E.a.invb.inv.sigma,
                Hess.LD = LD_S,
                E.log.sig.b=E.log.sig.b, 
                E.log.sig = E.log.sig, 
                E.prior.sig.gam= E.prior.sig.gam,
                entrop = entrop))
  }


#file_path <- "/home/jaguir26/projects/notebooks/variables_05_M.RData"
#load(file_path)
#new.uts.out = new.uts.out_05_M 
#new.sts.out =  new.sts.out_05_M  
#new.gamsig.out = new.gamsig.out_05_M 
#new.theta.out = new.theta.out_05_M 
#model$m0 <- new.theta.out_05_M$sm[,1]

model$m0 <- new.theta.out$sm_0


crit_ELBO <- 0
ELBO <- 0
seq.elbo = ELBO
iter = 0
FLAG = TRUE
tol1 <- 1e-5
tol2 <- 1e-2 
########################
  tictoc::tic("run time")
  ########################
  while (FLAG) {
   
    ##########
    cur.uts.out = new.uts.out
    cur.sts.out = new.sts.out
    cur.gamsig.out = new.gamsig.out
    cur.theta.out = new.theta.out
    
    ############# Make a function with two options dependeoing on J!!!
    for (j in 1:(J+1)) {

      ########################      
      sts.dummy <- update_sts(y[j,],
                              cur.theta.out$exps[j,], 
                              cur.uts.out$E.inv.uts[j,], 
                              cur.gamsig.out$E.c2.invb.absgam2.sigma[j,], 
                              cur.gamsig.out$E.c.invb.absgam[j,], 
                              cur.gamsig.out$E.c.a.invb.absgam[j,])
      
      new.sts.out$E.sts[j,] <- sts.dummy$E.sts
      new.sts.out$E.sts2[j,] <- sts.dummy$E.sts2
      new.sts.out$tot.entrop[j,] <-  sts.dummy$tot.entrop
      
      ########################
      uts.dummy <- update_uts(y[j,],
                              cur.theta.out$exps[j,], 
                              cur.theta.out$exps2[j,], 
                              new.sts.out$E.sts[j,], 
                              new.sts.out$E.sts2[j,], 
                              cur.gamsig.out$E.inv.sigma[j,], 
                              cur.gamsig.out$E.a2.invb.inv.sigma[j,], 
                              cur.gamsig.out$E.invb.inv.sigma[j,], 
                              cur.gamsig.out$E.c.invb.absgam[j,], 
                              cur.gamsig.out$E.c2.invb.absgam2.sigma[j,]) 
      
      
      new.uts.out$E.uts[j,] <- uts.dummy$E.uts
      new.uts.out$E.inv.uts[j,] <- uts.dummy$E.inv.uts
      new.uts.out$E.log.uts[j,] <- uts.dummy$E.log.uts
      new.uts.out$tot.entrop[j,] <- uts.dummy$tot.entrop

      ########################
     gamsig.dummy <- update_gamma_sigma(y[j,],
                                         PriorGamma[j,],
                                         PriorSigma[j,],
                                         cur.gamsig.out$E.gam[j,], 
                                         cur.gamsig.out$V.gam[j,], 
                                         cur.gamsig.out$E.sigma[j,], 
                                         cur.gamsig.out$V.sigma[j,], 
                                         cur.theta.out$exps[j,], 
                                         cur.theta.out$exps2[j,], 
                                         new.sts.out$E.sts[j,], 
                                         new.sts.out$E.sts2[j,], 
                                         new.uts.out$E.uts[j,], 
                                         new.uts.out$E.inv.uts[j,],
                                         cur.gamsig.out$E.sigma[j,], 
                                         cur.gamsig.out$E.gam[j,])    


      new.gamsig.out$E.gam[j,] <- gamsig.dummy$E.gam
      new.gamsig.out$E.sigma[j,] <- gamsig.dummy$E.sigma
      new.gamsig.out$E.inv.sigma[j,] <- gamsig.dummy$E.inv.sigma
      new.gamsig.out$E.c2.invb.absgam2.sigma[j,] <- gamsig.dummy$E.c2.invb.absgam2.sigma
      new.gamsig.out$E.c.invb.absgam[j,] <- gamsig.dummy$E.c.invb.absgam
      new.gamsig.out$E.c.a.invb.absgam[j,] <- gamsig.dummy$E.c.a.invb.absgam
      new.gamsig.out$E.a2.invb.inv.sigma[j,] <- gamsig.dummy$E.a2.invb.inv.sigma
      new.gamsig.out$E.invb.inv.sigma[j,] <- gamsig.dummy$E.invb.inv.sigma
      new.gamsig.out$E.a.invb.inv.sigma[j,] <- gamsig.dummy$E.a.invb.inv.sigma
      new.gamsig.out$E.log.sig.b[j,] <- gamsig.dummy$E.log.sig.b
      new.gamsig.out$E.log.sig[j,] <- gamsig.dummy$E.log.sig
      new.gamsig.out$E.prior.sig.gam[j,] <- gamsig.dummy$E.prior.sig.gam
      new.gamsig.out$entrop[j,] <- gamsig.dummy$entrop
      
    }
    
    ########################
    FFF <- (new.gamsig.out$E.c.invb.absgam[,] * new.sts.out$E.sts + new.gamsig.out$E.a.invb.inv.sigma[,]/new.uts.out$E.inv.uts) / new.gamsig.out$E.invb.inv.sigma[,] 
    QQQ <- 1/(new.gamsig.out$E.invb.inv.sigma[,] * new.uts.out$E.inv.uts)
    if(J>0){
    QQQ <- array(apply(QQQ, 2, function(col) diag(col)), dim = c(J+1, J+1, TT))
    }else{
     QQQ <- array(QQQ, dim = c(J+1, J+1, TT))
    }


    ##########
    if (crit_ELBO < tol1) {
      new.theta.out  <- update_theta(FFF, QQQ)
      theta_update <- TRUE
    }else{
      theta_update <- FALSE
    }
    
    
    ##########
    seq.gamma = cbind(seq.gamma, new.gamsig.out$E.gam)
    seq.sigma = cbind(seq.sigma, new.gamsig.out$E.sigma)
    
    ##########
    # ELBO
    ##########
    elbo <- 0
    elbo <- elbo -TT/2*sum(new.gamsig.out$E.log.sig.b[,])
    elbo <- elbo -0.5*sum(new.uts.out$E.log.uts[,])
    elbo <- elbo -TT*(J+1)/2*log(pi)

    elbo <- elbo -0.5*sum((new.gamsig.out$E.invb.inv.sigma[,]*new.uts.out$E.inv.uts[,])*(y[,]^2-2*y[,]*cur.theta.out$exps[,]+new.theta.out$exps2[,]))
    elbo <- elbo +sum((y[,]-new.theta.out$exps[,])*(new.gamsig.out$E.c.invb.absgam[,]*new.sts.out$E.sts*new.uts.out$E.inv.uts[,]+new.gamsig.out$E.a.invb.inv.sigma[,]))-0.5*sum(new.sts.out$E.sts2[,]*new.uts.out$E.inv.uts[,]*new.gamsig.out$E.c2.invb.absgam2.sigma[,])
    elbo <- elbo -sum(new.gamsig.out$E.c.a.invb.absgam[,]*new.sts.out$E.sts[,])-0.5*sum(new.gamsig.out$E.a2.invb.inv.sigma[,]*new.uts.out$E.uts[,])

    elbo <- elbo -TT*sum(new.gamsig.out$E.log.sig[,])-sum(new.gamsig.out$E.inv.sigma[,]*new.uts.out$E.uts[,])-0.5*sum(new.sts.out$E.sts2[,])+sum(new.gamsig.out$E.prior.sig.gam[,])
    
    elbo <- elbo +sum(new.uts.out$tot.entrop[,])+sum(new.sts.out$E.tot.entrop[,])+sum(new.gamsig.out$E.sig.gam.entrop[,])

    elbo <- elbo + new.theta.out$elbo.part
    
    elbo <- elbo/TT/(J+1)

    crit_ELBO <- abs(ELBO-elbo)
    ELBO <- elbo
    seq.elbo =  cbind(seq.elbo, ELBO) 


    print(iter)
    print(c(elbo, crit_ELBO))
    flush.console()
    iter = iter + 1
    
    if(theta_update){
      if (crit_ELBO < tol2) {
        FLAG = FALSE
      }
    }

  }
########################
run.time = tictoc::toc(quiet = TRUE)

########################
if (verbose) {
  cat(sprintf("ISVB converged: %s iterations, %s seconds", 
              iter, round(run.time$toc - run.time$tic, 3)), "\n")
}

########################
samp.gamma = array(NA_real_, c(J+1, n.samp))
samp.sigma = array(NA_real_, c(J+1, n.samp))
samp.uts = array(NA_real_, c(J+1, TT, n.samp))
samp.sts = array(NA_real_, c(J+1, TT, n.samp))

for (j in 1:(J+1) ) {
  
    ########################      
      sts.dummy <- update_sts(y[j,],
                              cur.theta.out$exps[j,], 
                              cur.uts.out$E.inv.uts[j,], 
                              cur.gamsig.out$E.c2.invb.absgam2.sigma[j,], 
                              cur.gamsig.out$E.c.invb.absgam[j,], 
                              cur.gamsig.out$E.c.a.invb.absgam[j,])
      
      new.sts.out$E.sts[j,] <- sts.dummy$E.sts
      new.sts.out$E.sts2[j,] <- sts.dummy$E.sts2
      
      
      ########################
      uts.dummy <- update_uts(y[j,],
                              cur.theta.out$exps[j,], 
                              cur.theta.out$exps2[j,], 
                              new.sts.out$E.sts[j,], 
                              new.sts.out$E.sts2[j,], 
                              cur.gamsig.out$E.inv.sigma[j,], 
                              cur.gamsig.out$E.a2.invb.inv.sigma[j,], 
                              cur.gamsig.out$E.invb.inv.sigma[j,], 
                              cur.gamsig.out$E.c.invb.absgam[j,], 
                              cur.gamsig.out$E.c2.invb.absgam2.sigma[j,]) 
      
      
      new.uts.out$E.uts[j,] <- uts.dummy$E.uts
      new.uts.out$E.inv.uts[j,] <- uts.dummy$E.inv.uts
      
      ########################
     gamsig.dummy <- update_gamma_sigma(y[j,],
                                         PriorGamma[j,],
                                         PriorSigma[j,],
                                         cur.gamsig.out$E.gam[j,], 
                                         cur.gamsig.out$V.gam[j,], 
                                         cur.gamsig.out$E.sigma[j,], 
                                         cur.gamsig.out$V.sigma[j,], 
                                         cur.theta.out$exps[j,], 
                                         cur.theta.out$exps2[j,], 
                                         new.sts.out$E.sts[j,], 
                                         new.sts.out$E.sts2[j,], 
                                         new.uts.out$E.uts[j,], 
                                         new.uts.out$E.inv.uts[j,],
                                         cur.gamsig.out$E.sigma[j,], 
                                         cur.gamsig.out$E.gam[j,])    


      new.gamsig.out$E.gam[j,] <- gamsig.dummy$E.gam
      new.gamsig.out$E.sigma[j,] <- gamsig.dummy$E.sigma
      new.gamsig.out$E.inv.sigma[j,] <- gamsig.dummy$E.inv.sigma
      new.gamsig.out$E.c2.invb.absgam2.sigma[j,] <- gamsig.dummy$E.c2.invb.absgam2.sigma
      new.gamsig.out$E.c.invb.absgam[j,] <- gamsig.dummy$E.c.invb.absgam
      new.gamsig.out$E.c.a.invb.absgam[j,] <- gamsig.dummy$E.c.a.invb.absgam
      new.gamsig.out$E.a2.invb.inv.sigma[j,] <- gamsig.dummy$E.a2.invb.inv.sigma
      new.gamsig.out$E.invb.inv.sigma[j,] <- gamsig.dummy$E.invb.inv.sigma
      new.gamsig.out$E.a.invb.inv.sigma[j,] <- gamsig.dummy$E.a.invb.inv.sigma

  ### posterior samples
  # gamma and sigma
  theta_s <- log(gamsig.dummy$E.sigma)
  theta_g <- log(log((-L+U)/(-L+gamsig.dummy$E.gam)))
  samp.LD <- rmvnorm(n = n.samp, mean = c(theta_s, theta_s), sigma = gamsig.dummy$Hess.LD)
  samp.gamma[j,] = LL+(-LL+UU)*exp(-exp(samp.LD[,2]))
  samp.sigma[j,] = exp(samp.LD[,1]) 
  
  ######################## Nu Sampling
  samp.uts[j,,] = t(sapply(1:TT, function(t) { GeneralizedHyperbolic::rgig(n.samp, 
                                                                          chi = uts.dummy$uts.chi[t], 
                                                                          psi = uts.dummy$uts.psi, 
                                                                          lambda = uts.dummy$uts.lambda) }))
  ######################## S Sampling
  samp.sts[j,,] = t(sapply(1:TT, function(t) {truncnorm::rtruncnorm(n.samp, 
                                                                    a = rep(0, n.samp), 
                                                                    b = rep(Inf, n.samp),
                                                                    mean = sts.dummy$sts.mu[t], 
                                                                    sd = sqrt(sts.dummy$sts.sig2[t])) }))
}    

################################################################################################
################################################################################################ Prob no need to recompute

  FFF <- (new.gamsig.out$E.c.invb.absgam[,] * new.sts.out$E.sts + new.gamsig.out$E.a.invb.inv.sigma[,]/new.uts.out$E.inv.uts) / new.gamsig.out$E.invb.inv.sigma[,] 
  QQQ <- 1/(new.gamsig.out$E.invb.inv.sigma[,] * new.uts.out$E.inv.uts)
  if(J>0){
    QQQ <- array(apply(QQQ, 2, function(col) diag(col)), dim = c(J+1, J+1, TT))
  }else{
    QQQ <- array(QQQ, dim = c(J+1, J+1, TT))
  }
  new.theta.out  <- update_theta(FFF, QQQ)

################################################################################################
################################################################################################
######################## Theta Sampling
samp_theta_t = function(t) {
  ########## 
  LL <- t(chol(as.matrix(new.theta.out$sC[, , t])))
  ##########
  new.theta.out$sm[, t] + LL %*% matrix(stats::rnorm(n.samp *  (p+J), 0, 1), p+J, n.samp)
}

#######################  
samp.theta = array(NA, c(p+J, TT, n.samp))
samp.post.pred = array(NA, c(J+1,TT, n.samp))

for (j in 1:(J+1) ) {   
  ######################## Fit  
  samp_post_pred_t = function(t,a) {
    FF_jt <- FF[, j, t] 
    samp_theta_t <- a
    xb <- colSums(FF_jt * samp_theta_t)
    brms::rasym_laplace( 1, xb + samp.sigma[j, ] * C.fn(p0, samp.gamma[j, ]) * abs(samp.gamma[j, ]) * samp.sts[j, t, ], 
                          samp.sigma[j, ], p.fn(p0, samp.gamma[j, ]))
  } 
  
  #######################
  for (t in 1:TT) {
    samp.theta[, t, ] = samp_theta_t(t)
    samp.post.pred[, t, ] = samp_post_pred_t(t, samp.theta[, t, ])
  }
  
} 

save_variables <- function(var_names, filename, dir_path) {

  file_path <- file.path(dir_path, filename)
  save_cmd <- paste("save(", paste(var_names, collapse = ", "), ", file = file_path)")
  eval(parse(text = save_cmd))
  cat("Variables saved to:", file_path, "\n")
}

samp.gamma_05_M = samp.gamma 
samp.sigma_05_M = samp.sigma
samp.uts_05_M = samp.uts
samp.sts_05_M = samp.sts 
samp.theta_05_M = samp.theta 
samp.post.pred_05_M = samp.post.pred 
new.uts.out_05_M = new.uts.out
new.sts.out_05_M = new.sts.out 
new.gamsig.out_05_M = new.gamsig.out 
new.theta.out_05_M = new.theta.out
seq.gamma_05_M = seq.gamma
seq.sigma_05_M = seq.sigma
seq.elbo_05_M =  seq.elbo


vars_to_save <- c("samp.gamma_05_M", "samp.sigma_05_M", 
                  "samp.uts_05_M", "samp.sts_05_M", 
                  "samp.theta_05_M", "samp.post.pred_05_M", 
                  "new.uts.out_05_M", "new.sts.out_05_M", 
                  "new.gamsig.out_05_M", "new.theta.out_05_M",
                  "seq.gamma_05_M", "seq.sigma_05_M", "seq.elbo_05_M")


save_variables(vars_to_save, "variables_05_M.RData", "/home/jaguir26/projects/notebooks")

