#!/usr/bin/env Rscript
.libPaths(c("~/R/libs", .libPaths()))
print(.libPaths())
library(dplyr)


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

n.samp <- 2000
cut <- 1
m <- 2
USE_PREV <- TRUE
SAVE <- TRUE
p0 <- 0.5
harmonics = c(1, 2, 1/6.8068493) 
# harmonics = c(30, 2, 1/6.8068493)         

# Set environment variables for Boost, Eigen, LAPACK, and BLAS
Sys.setenv("PKG_CXXFLAGS"="-I/data/muscat_data/jaguir26/libs/eigen -I/data/muscat_data/jaguir26/libs/boost/include -DEIGEN_DONT_VECTORIZE")
Sys.setenv("PKG_LIBS"="-L/data/muscat_data/jaguir26/libs/lib64 -L/data/muscat_data/jaguir26/libs/boost/lib -llapack -lblas -lboost_random -lboost_system -fopenmp")

# Update the LD_LIBRARY_PATH inside the R environment
Sys.setenv(LD_LIBRARY_PATH="/data/muscat_data/jaguir26/libs/lib64:/data/muscat_data/jaguir26/libs/boost/lib:/lib64")

# Source C++ files
Rcpp::sourceCpp("/data/muscat_data/jaguir26/project1_ucsc_phd/sampling_exal.cpp")
Rcpp::sourceCpp("/data/muscat_data/jaguir26/project1_ucsc_phd/sampling_truncnorm.cpp")
Rcpp::sourceCpp("/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_kalman_synth_NDLM.cpp")

objective_deltas <- function(delta, SIMS, use_covariates){

print(delta)
flush.console()

lam1 <- 1-1e-6 # Sudden correction at start of forecast period
lam2 <- 0.9 # Correction during forecast period from historical period

df_t        <- delta[1]
df_s1       <- delta[2]
df_s2       <- delta[3]
df_s67      <- delta[4]
df.discrep  <- delta[5]
df_trans      <- 0.99999999
df_covs       <- 0.99999
lambda      <- delta[6]


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
    is_correct <- all.equal(sqrt_inv_q_product, inv_q, tolerance = 1e-12)
    
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

parameters_path <- "/data/muscat_data/jaguir26/projects/Project/Input/exAL/parameters/parameters.txt"

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
#
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
    # B = C[TT-k,,] %*% t(GG[,,i]) %*% solve(R[TT-k+1,,])
    B = C[TT-k,,] %*% t(GG[,,i]) %*% chol2inv(chol(R[TT-k+1,,]))
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
  log_density <- log(density_estimates + .Machine$double.eps*100)  # Add small value to avoid log(0)
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
estimate_kl_divergence_knn_entropy <- function(sample_from_p, sample_size, k = 5) {
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
    estimated_kl_divergence <- estimate_kl_divergence_knn_entropy(sample_from_p, sample_size, k = 5)
  }
  
  # Return the estimate
  return(estimated_kl_divergence)
}
#
# Function to estimate differential entropy using KDE for univariate data
estimate_differential_entropy_kde_univariate <- function(data) {
  kde_result <- kde(data)
  estimates <- kde_result$estimate
  estimates[estimates <= 0] <- .Machine$double.eps*100 # Prevent log(0) issues
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
  estimates[estimates <= 0] <- .Machine$double.eps*100 # Prevent log(0) issues
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
concatenate_matrix_columns <- function(matrix_input) {
  # Concatenate the columns of the matrix
  concatenated_vector <- c(matrix_input)
  return(concatenated_vector)
}
#
preallocate_matrix_list <- function(column_counts, num_rows) {
  # Initialize an empty list
  matrix_list <- vector("list", length(column_counts))
  
  # Loop through the column counts and create matrices
  for (i in seq_along(column_counts)) {
    num_cols <- column_counts[i]
    matrix_list[[i]] <- matrix(NA, nrow = num_rows, ncol = num_cols)
  }
  
  return(matrix_list)
}

# Read and process ELI_lon data
ELI_lon <- read.csv("/data/muscat_data/jaguir26/projects/Project/Input/exAL/covariates/cov_1_ELI.csv")
merged_sst_data <- read.csv("/data/muscat_data/jaguir26/projects/Project/Input/exAL/covariates/cov_2_ONI.csv")
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
nws_forecast <- read.csv('/data/muscat_data/jaguir26/project1_ucsc_phd/nws_forecast.csv')
nws_forecast[,-1] <- log(nws_forecast[,-1])
num_ens_nws <- dim(nws_forecast)[2]-1

glofas_forecast <- read.csv('/data/muscat_data/jaguir26/project1_ucsc_phd/weighted_time_series.csv')
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
file_path <- "/data/muscat_data/jaguir26/project1_ucsc_phd/prism_precipitation_santa_cruz_1987_2023.csv"
ppt_data <- read_csv(file_path, show_col_types = FALSE)
ppt_data$Date <- as.Date(ppt_data$Date)
colnames(ppt_data) <- c('time','ppt')
X_ppt <- ppt_data[ppt_data$time <= '2022-12-25',]

start_date_idx <- which(ppt_data$time == '2022-12-26')
end_date_idx <- which(ppt_data$time == '2022-12-26') + ranges[1]
X_ppt_f <- ppt_data[start_date_idx:end_date_idx,c('ppt','time')]

##########
## SOIL ##
##########
csv_file_path <- "/data/muscat_data/jaguir26/project1_ucsc_phd/soil_moisture_data/soil_moisture_big_trees_daily_avg_1987_2023.csv"
soil_moisture_data <- read.csv(csv_file_path)
soil_moisture_data$Date <- as.Date(soil_moisture_data$Date)
colnames(soil_moisture_data) <- c('time','soil')
X_soil <- soil_moisture_data[soil_moisture_data$time <= '2022-12-25',]

start_date_idx <- which(soil_moisture_data$time == '2022-12-26')
end_date_idx <- which(soil_moisture_data$time == '2022-12-26') + ranges[1]
X_soil_f <- soil_moisture_data[start_date_idx:end_date_idx,c('soil','time')]

#########
## PCA ##
#########
components_file_path <- "/data/muscat_data/jaguir26/project1_ucsc_phd/pca.csv"
principal_components_df <- read_csv(components_file_path, show_col_types = FALSE)
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
data_path <- "/data/muscat_data/jaguir26/project1_ucsc_phd/retros_2022-12-25.csv"
streamflow_data <- read_csv(data_path, show_col_types = FALSE)
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
sd1  <- sd(X_ext[,1]) 
sd2  <- sd(X_ext[,2]) 
sd3  <- sd(X_ext[,3]) 
sd4  <- sd(X_ext[,4]) 
sd5  <- sd(X_ext[,5]) 
X_ext[,1] <- X_ext[,1]/sd1
X_ext[,2] <- X_ext[,2]/sd2
X_ext[,3] <- X_ext[,3]/sd3
X_ext[,4] <- X_ext[,4]/sd4 
X_ext[,5] <- X_ext[,5]/sd5
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
sd_ppt  <- sd(X[,1]) 
sd_soil <- sd(X[,2]) 
sd_pca  <- sd(X[,3]) 
X[,1] <- X[,1]/sd_ppt
X[,2] <- X[,2]/sd_soil
X[,3] <- X[,3]/sd_pca
X <- cbind(X,X_ext)
###### Standarized future covs using historical sds
X_f[,1] <- X_f[,1]/sd_ppt
X_f[,2] <- X_f[,2]/sd_soil
X_f[,3] <- X_f[,3]/sd_pca
X_ext_f[,1] <- X_ext_f[,1]/sd1
X_ext_f[,2] <- X_ext_f[,2]/sd2
X_ext_f[,3] <- X_ext_f[,3]/sd3
X_ext_f[,4] <- X_ext_f[,4]/sd4
X_ext_f[,5] <- X_ext_f[,5]/sd5
X_f <- cbind(X_f,X_ext_f)

if(use_covariates){
  ending <- "_NDLM_synth_DISC"
}else{
  ending <- "_NDLM_synth_simp"
}
#
# Model setup without covariates
m_yy <- mean(Y, na.rm = TRUE)
s_yy <- sd(Y, na.rm = TRUE)  
kk <- 0.5 * s_yy
trend.comp <- polytrendMod(1, m0 = m_yy, C0 = kk)
harm <- harmonics
seas.comp <- seasMod(p = 363.5854, h = harm, C0 = 0.5 * kk * diag(2 * length(harm)))
model <- combineMods(trend.comp, seas.comp)
p <- length(model$m0)
#
idx <- 1:TT
y <- Y[,idx]
TT_sub <- length(idx)
#
if (is.null(nrow(y))) {
  JJJ <- 1
  y <- array(y, c(JJJ, length(y)))
} else {
  JJJ <- nrow(Y)
  y <- array(y, c(JJJ, ncol(y)))
}
#
gam.init <- array(rep(0, JJJ), c(JJJ, 1))
sig.init <- array(rep(1, JJJ), c(JJJ, 1))
PriorSigma <- array(NA_real_, c(JJJ, 2))
PriorGamma <- array(NA_real_, c(JJJ, 3))
verbose <- TRUE

###########################################################################################
###########################################################################################
###########################################################################################
m0 <- c(model$m0, rep(0, p*J))
C0 <- bdiag(model$C0, 0.5 * kk * diag(p*J))
##########################################  
##########################################
df <- c(df_t, df_s1, df_s2, df_s67)
df.discrep <- rep(df,J)
dim.df <- c(1, 2, 2, 2)
k <- 10
##########################################2
##########################################
model_simp <- model
df_simp <- df
dim.df_simp <- dim.df
model_simp$GG <- array(model_simp$GG, c(p, p, TT))
model_simp$FF <- array(model_simp$FF, c(p, 1, TT))
##########################################2
##########################################
df.mat <- make_df_mat(df, dim.df, p)
df.mat.k <- make_df_mat_k(df, dim.df, p, k)

df1 <- c(df_t*lam1, df_s1, df_s2, df_s67)
df.mat_f1 <- make_df_mat(df1, dim.df, p)
df.mat.k_f1 <- make_df_mat_k(df1, dim.df, p, k)
df2 <- c(df_t*lam2, df_s1, df_s2, df_s67)
df.mat_f2 <- make_df_mat(df2, dim.df, p)
df.mat.k_f2 <- make_df_mat_k(df2, dim.df, p, k)

# df.mat_f2 <- make_df_mat(df*lam1, dim.df, p)
# df.mat.k_f2 <- make_df_mat_k(df*lam1, dim.df, p, k)
# df.mat_f2 <- make_df_mat(df*lam2, dim.df, p)
# df.mat.k_f2 <- make_df_mat_k(df*lam2, dim.df, p, k)

if (J <= 0) {
  ex.df.mat <- df.mat
  ex.df.mat.k <- df.mat.k
} else {
  extra_df.mat <- make_df_mat(df.discrep, c(rep(dim.df,J)), p*J)
  extra_df.mat.k<- make_df_mat_k(df.discrep, c(rep(dim.df,J)), p*J, k)
  
  ex.df.mat <- bdiag(df.mat, extra_df.mat)
  ex.df.mat.k <- bdiag(df.mat.k, extra_df.mat.k)

  ex.df.mat_f_T <- bdiag(df.mat_f1, extra_df.mat)
  ex.df.mat_f_T <- as.matrix(ex.df.mat_f_T)

  ex.df.mat.k_f_T <- bdiag(df.mat.k_f1, extra_df.mat.k)
  ex.df.mat.k_f_T <- as.matrix(ex.df.mat.k_f_T)

  ex.df.mat_f <- bdiag(df.mat_f2, extra_df.mat)
  ex.df.mat_f <- as.matrix(ex.df.mat_f)

  ex.df.mat.k_f <- bdiag(df.mat.k_f2, extra_df.mat.k)
  ex.df.mat.k_f <- as.matrix(ex.df.mat.k_f)

  # Get the dimensions of the input matrices
  n <- nrow(ex.df.mat_f)
  m <- ncol(ex.df.mat_f)
  DF.MAT <- array(0, dim = c(n, m, 2))
  DF.MAT[,,1] <- ex.df.mat_f_T
  DF.MAT[,,2] <- ex.df.mat_f

  DF.MAT_k <- array(0, dim = c(n, m, 2))
  DF.MAT_k[,,1] <- ex.df.mat.k_f_T
  DF.MAT_k[,,2] <- ex.df.mat.k_f

}

create_block_diag <- function(A, n) {
  if (!is.matrix(A)) stop("A must be a matrix.")
  if (!is.numeric(n) || n <= 0 || n != floor(n)) stop("n must be a positive integer.")
  block_diag_matrix <- bdiag(replicate(n, A, simplify = FALSE))
  return(as.matrix(block_diag_matrix))
}

# Discrepancies
A <- model$GG; n <- J+1;
result_GG <- create_block_diag(A, n);
GG <- array(result_GG, dim = c(dim(result_GG)[1], dim(result_GG)[1], TT))
model$GG <- GG

A <- model$FF; n <- J+1;
result_FF <- create_block_diag(A, n);
result_FF[1:p,] <- matrix(model$FF, p, J + 1)
FF <- array(result_FF, c(p*(1 + J), 1 + J, TT))
model$FF <- FF

FF <- model$FF
GG <- model$GG
model$m0 <- m0 
model$C0 <- C0 
ppx <- 0

if (use_covariates) {
  px <- dim(X)[2]
  ppx <- px + 1

  FFx <- array(0, c(dim(FF)[1] + ppx, dim(FF)[2], TT))
  FFx[1:dim(FF)[1],1:dim(FF)[2],] <- FF
  GGx <- array(0, c(dim(GG)[1] + ppx, dim(GG)[2]+ ppx, TT))
  GGx[1:dim(GG)[1],1:dim(GG)[2],] <- GG

  Fx <- rbind(rep(1, J + 1), matrix(0, nrow = px, ncol = J + 1))
  FFx[(dim(FF)[1]+1):dim(FFx)[1],,] <- Fx 

  Gx <- as.matrix(bdiag(lambda, diag(px)))
  Gx <- array(rep(Gx, TT), dim = c(ppx, ppx, TT))
  Gx[1, 2:ppx, ] <- as.matrix(t(X))
  GGx[(dim(GG)[1]+1):dim(GGx)[1],(dim(GG)[2]+1):dim(GGx)[1],] <- Gx

  model$FF <- FFx
  model$GG <- GGx

  extra_df.mat <- make_df_mat(c(df_trans,df_covs), c(1,px), ppx)
  extra_df.mat.k <- make_df_mat_k(c(df_trans,df_covs), c(1,px), ppx, k)

  ex.df.mat <- bdiag(ex.df.mat, extra_df.mat)
  ex.df.mat.k <- bdiag(ex.df.mat.k, extra_df.mat.k)

  model$m0 <- c(model$m0, rep(0, ppx))
  model$C0 <- bdiag(model$C0, 0.01 * kk * diag(ppx))
  
  FF <- model$FF
  GG <- model$GG
}


L = L.fn(p0)
U = U.fn(p0)

FF_list <- vector("list", J)
GG_list <- vector("list", J)

######################
# Without covariates for the forceasting period
for (j in 1:J) {
  jj <- J-j+1
  GG_tsc <- result_GG[1:(p*(jj+1)),1:(p*(jj+1))]
  GG_list[[j]] <- matrix(GG_tsc, nrow = p*(jj+1), ncol = p*(jj+1) )
  FF_tsc <- result_FF[1:(p*(jj+1)), 2:(jj+1)]
  FF_list[[j]] <- matrix(FF_tsc, nrow = p*(jj+1), ncol = (jj) )
}

###########################################################################################
###########################################################################################
###########################################################################################

########### For every j
for (j in 1:(J+1)) {
  if (!is.na(gam.init[j,])) {
    if (gam.init[j,] < L | gam.init[j,] > U) {
      stop(sprintf("gam.init must be between %s and %s for %s quantile", 
                    round(L, 3), round(U, 3), p0))
    }
  } 
}
###########################################################################################
########### For every j
for (j in 1:(J+1)) {
  if (is.na(PriorSigma[j,1]) || is.na(PriorSigma[j,2])) {
    m_sigma = 1
    v_sigma = 1e+10
    PriorSigma[j,1] = (m_sigma^2)/(v_sigma) + 2 
    PriorSigma[j,2] = (m_sigma^3)/(v_sigma) + m_sigma 
  }
}
###########################################################################################
########### For every j
for (j in 1:(J+1)) {
  if (is.na(PriorGamma[j,1]) || is.na(PriorGamma[j,2]) || is.na(PriorGamma[j,3])) {
    PriorGamma[j,1]  = 0
    PriorGamma[j,2]  = 1e+10
    PriorGamma[j,3] = 1
  }
}
###########################################################################################
########### For every j
gam0 = gam.init 
sig0 = sig.init 

fill_with_value <- function(matrix_list, value) {
  for (i in seq_along(matrix_list)) {
    matrix_list[[i]][] <- value
  }
  return(matrix_list)
}
preallocate_matrix_list <- function(column_counts, num_rows) {
  # Initialize an empty list
  matrix_list <- vector("list", length(column_counts))

  for (i in seq_along(column_counts)) {
    num_cols <- column_counts[i]
    matrix_list[[i]] <- matrix(NA, nrow = num_rows[i], ncol = num_cols)
  }
  return(matrix_list)
}

###########################################################################################
########### For every j 

# Gamma, Sigma
E1 <- array(NA_real_, c(J+1,1))
E1[,] <- 1
E2 <- array(NA_real_, c(J+1,1))
E2[,] <- 1
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
###########################################################################################
########### For every j

# S_t (Before Forecast)
E1 <- array(NA_real_, c(J+1,TT_sub))
E1[,] <- truncnorm::etruncnorm(a = 0, b = Inf,  mean = 1, sd = 0.1)
E2 <- array(NA_real_, c(J+1,TT_sub))
E2[,] <- E1[,]^2 
new.sts.out = list(E.sts = E1, 
                    E.sts2 = E2,
                    tot.entrop = array(0, c(J+1,1)) )
# S_t (After Forecast)
E1 <- preallocate_matrix_list(num_mem, ranges)
E2 <- preallocate_matrix_list(num_mem, ranges)
E1 <- fill_with_value(E1, 1)
E2 <- fill_with_value(E2, 1^2)

entrop_s <- preallocate_matrix_list(num_mem, rep(1,J) )
entrop_s <- fill_with_value(entrop_s, 0)

new.sts.out_f = list(E.sts = E1, 
                    E.sts2 = E2,
                    tot.entrop = entrop_s )

###########################################################################################
########### For every j

# U_t (Before Forecast)
E1 <- array(NA_real_, c(J+1,TT_sub))
E1[,] <- 1/sig0
E2 <- array(NA_real_, c(J+1,TT_sub))
E2[,] <- sig0
new.uts.out = list(E.uts = E1, 
                    E.inv.uts = E2,
                    E.log.uts = array(0, c(J+1,1)),
                    tot.entrop = array(0, c(J+1,1)) )

# U_t (After Forecast)
E1 <- preallocate_matrix_list(num_mem, ranges)
E2 <- preallocate_matrix_list(num_mem, ranges)
E1 <- fill_with_value(E1, 1/sig0)
E2 <- fill_with_value(E2, sig0)

entrop_u <- preallocate_matrix_list(num_mem, rep(1,J))
entrop_u <- fill_with_value(entrop_u, 0)

new.uts.out_f = list(E.uts = E1, 
                    E.inv.uts = E2,
                    E.log.uts = entrop_u,
                    tot.entrop = entrop_u )

###########################################################################################
# Exps
init.dlm = dlm_df(colMeans(y), model_simp, df_simp, dim.df_simp, 
                  s.priors = list(l0 = 1, S0 = mean(sig0)), 
                  just.lik = FALSE)
FF_t <- aperm(model_simp$FF, c(2, 1, 3))
multiply_matrices <- function(slice_index) {
  t(FF_t[1,,slice_index]) %*% init.dlm$m[slice_index,]
}
result_list <- lapply(1:TT_sub, multiply_matrices)
result_array <- array(unlist(result_list), dim = c(TT_sub,1))
exps0 = c(result_array) + stats::qnorm(p0, 0, sqrt(init.dlm$s[TT_sub]))
exps0 = t(replicate(J+1, exps0))

exps0 <- cbind(exps0,mean_forecast)
exps2 <- exps0^2

new.theta.out = list(exps = exps0, 
                      exps2 = exps2)

###########################################################################################
iter = 0
conv.count = 0
new.max = Inf

###########################################################################################
########### For every j
seq.gamma = new.gamsig.out$E.gam
seq.sigma = new.gamsig.out$E.sigma
###########################################################################################

update_sts<-function(y, exps,inv.uts,c2.invb.absgam2.sigma,c.invb.absgam,c.a.invb.absgam, TTT){
  s.sig2<-1/(1+c2.invb.absgam2.sigma*inv.uts); s.sig = sqrt(s.sig2)
  s.mu<-s.sig2*(c.invb.absgam*(y-exps)*inv.uts-c.a.invb.absgam)
  #
  E.sts = truncnorm::etruncnorm(a=rep(0,TTT),b=rep(Inf,TTT),mean=s.mu,sd=s.sig)
  V.sts = truncnorm::vtruncnorm(a=rep(0,TTT),b=rep(Inf,TTT),mean=s.mu,sd=s.sig)
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


###########################################################################################
update_uts<-function(y, exps,exps2,sts,sts2,inv.sigma,a2.invb.inv.sigma,invb.inv.sigma,c.invb.absgam,c2.invb.absgam2.sigma){
  u.lambda = 0.5
  u.psi = (a2.invb.inv.sigma + 2*inv.sigma)
  u.chi = invb.inv.sigma*(y^2-2*y*exps+exps2) - 2*c.invb.absgam*sts*(y-exps) + c2.invb.absgam2.sigma*sts2
  u.chi[u.chi<=0] = 1e-6
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

###########################################################################################
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

update_gamma_sigma<-function( y, nn, prior_g, prior_s, 
                              gamma,var.gam,sigma,var.sig,
                              exps,exps2,
                              sts,sts2,
                              uts,inv.uts, 
                              s_init, g_init,
                              Climate_Center,
                              ensembles_j = NULL, num_mem_j = NULL, k_forecast = NULL,
                              sts_f = NULL,sts2_f = NULL,
                              uts_f= NULL,inv.uts_f= NULL){

if(!Climate_Center){
  dq_transf <- function(theta_s,theta_g){
      sig <- exp(theta_s)
      gam <- LL+(-LL+UU)*exp(-exp(theta_g))
          a = A.fn(p0,gam); b = B.fn(p0,gam); c = C.fn(p0,gam); p.fn(p0,gam)

      # Prior
      yy <- log(PriorGammaDens(gam, prior_g)) - (prior_s[1] + 1) * log(sig) - prior_s[2]/sig

      # Likelihood
      yy <- yy - (1.5*nn)*log(sig) - (0.5*nn)*log(b)-sum(uts)/sig 
      yy <- yy - 0.5*sum( inv.uts*(y^2-2*y*exps+exps2)/sig
                      - (y-exps)*2*(inv.uts*c*abs(gam)*sts + a/sig)
                      + sig*inv.uts*(c^2)*(abs(gam)^2)*sts2
                      + 2*c*abs(gam)*sts*a
                      + (uts*a^2)/sig )/b
      
      # Jacobian
      yy <- yy + theta_s + theta_g - exp(theta_g)                   
      return(yy)
  }
}else{

  ensembles_j <- matrix(c(as.matrix(ensembles_j)),ncol = 1)
  sts_f <-  matrix(c(as.matrix(sts_f)),ncol = 1)
  sts2_f <-  matrix(c(as.matrix(sts2_f)),ncol = 1)
  uts_f <-  matrix(c(as.matrix(uts_f)),ncol = 1)
  inv.uts_f <-  matrix(c(as.matrix(inv.uts_f)),ncol = 1)

  dq_transf <- function(theta_s,theta_g){
      sig <- exp(theta_s)
      gam <- LL+(-LL+UU)*exp(-exp(theta_g))
          a = A.fn(p0,gam); b = B.fn(p0,gam); c = C.fn(p0,gam);

      # Prior
      yy <- log(PriorGammaDens(gam, prior_g)) - (prior_s[1] + 1) * log(sig) - prior_s[2]/sig

      # Likelihood
      yy <- yy - 1.5*(nn+k_forecast*num_mem_j)*log(sig) - (0.5*(nn+k_forecast*num_mem_j))*log(b)-(sum(uts)+sum(uts_f))/sig 
      # Before Forecast
      yy <- yy - 0.5*sum( inv.uts*(y^2-2*y*exps[1:nn]+exps2[1:nn])/sig
                      - (y-exps[1:nn])*2*(inv.uts*c*abs(gam)*sts + a/sig)
                      + sig*inv.uts*(c^2)*(abs(gam)^2)*sts2
                      + 2*c*abs(gam)*sts*a
                      + (uts*a^2)/sig )/b
      # After Forecast
      yy <- yy - 0.5*sum( inv.uts_f*(ensembles_j^2-2*ensembles_j*exps[(nn+1):(nn+k_forecast)]+exps2[(nn+1):(nn+k_forecast)])/sig
                      - (ensembles_j-exps[(nn+1):(nn+k_forecast)])*2*(inv.uts_f*c*abs(gam)*sts_f + a/sig)
                      + sig*inv.uts_f*(c^2)*(abs(gam)^2)*sts2_f
                      + 2*c*abs(gam)*sts_f*a
                      + (uts_f*a^2)/sig )/b
      # Jacobian
      yy <- yy + theta_s + theta_g - exp(theta_g)                   
      return(yy)
  }
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

  f.sig <- function(theta){
    sig = exp(theta[1]); 
    yy <- sig
    return(yy)
  }

  f.gam <- function(theta){
    gam = LL+(-LL+UU)*exp(-exp(theta[2]));
    yy <- gam
    return(yy)
  }

  #############################################################################################################################################
  #############################################################################################################################################

  E.sig = Expected_f(f.sig, LD_mu[1], LD_mu[2]);
  E.gam = Expected_f(f.gam, LD_mu[1], LD_mu[2]);


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

  return(list(E.sigma=E.sig,E.inv.sigma=E.inv.sigma,E.gam=E.gam,
              E.c2.invb.absgam2.sigma = E.c2.invb.absgam2.sigma, E.c.invb.absgam = E.c.invb.absgam,
              E.c.a.invb.absgam = E.c.a.invb.absgam, E.a2.invb.inv.sigma = E.a2.invb.inv.sigma,
              E.invb.inv.sigma = E.invb.inv.sigma, E.a.invb.inv.sigma = E.a.invb.inv.sigma,
              Hess.LD = LD_S,
              E.log.sig.b=E.log.sig.b, 
              E.log.sig = E.log.sig, 
              E.prior.sig.gam= E.prior.sig.gam,
              E.theta = LD_mu,
              entrop = entrop))
}

########################
T_size <- c(TT, (TT+ranges))
########################

#############################################################################################################################################
#############################################################################################################################################

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
    concatenated_matrix <- do.call(cbind, lapply(FFF_list[1:J], function(mat) mat[start_row:(start_row + row_num - 1), ]))
    concatenated_list[[J - j + 1]] <- concatenated_matrix
    start_row <- start_row + row_num
  }
  
  # Handle the last remaining rows from the first matrix
  row_num <- nrow(FFF_list[[1]]) - start_row + 1
  concatenated_list[[length(concatenated_list) + 1]] <- FFF_list[[1]][start_row:(start_row + row_num - 1), ]
  
  return(concatenated_list)
}

ensembles_forecast <- concatenate_matrices(ensembles)
ensembles_forecast <- lapply(ensembles_forecast, t)
#############################################################################################################################################
#############################################################################################################################################
########################
# Prior for variances
a_s <- 1e-6
b_s <- 1e-6

if(USE_PREV){
  file_path <- "/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_variables_50_NDLM_synth_DISC.RData"
  load(file_path)
  new.theta.out = new.theta.out_50_NDLM_synth_DISC 
}

a_update <- rep(NA_real_, 1+J)
b_update <- rep(NA_real_, 1+J)

vars <- new.theta.out$exps2-new.theta.out$exps^2
for(j in 0:J){
    if(j==0){
        a_update[j+1] <- (TT)/2 + a_s
        b_update[j+1] <- 0.5*sum((Y[j+1,]-new.theta.out$exps[j+1,1:TT])^2)+0.5*(sum(vars[j,1:TT]))+b_s
    }else{
        a_update[j+1] <- (TT+ranges[j]*num_mem[J-j+1])/2 + a_s
        b <- 0.5*sum((Y[j+1,]-new.theta.out$exps[j+1,1:TT])^2)+0.5*(sum(vars[j,1:TT]))+b_s
        b <- b + 0.5*sum((ensembles[[j]]-matrix(rep(new.theta.out$exps[j+1,(TT+1):(TT+ranges[j])],num_mem[J-j+1]), ncol = num_mem[J-j+1]))^2)
        b_update[j+1] <- b + 0.5*num_mem[J-j+1]*sum(vars[j+1,(TT+1):(TT+ranges[j])])
    }
}

sigma2 <- b_update/(a_update-1) 
seq.sigma2 <-  sigma2
D <- diag(sigma2)

d <- c()
D_ens <- vector("list", J)
for(j in 1:(J)){
    dd <- c(rep(new.gamsig.out$E.sigma[j],num_mem[j]))
    d <- c(d,dd) 
    D_ens[[J-j+1]] <- diag(d)
}
########################
dM <- 1 #Fix to one?
Ones <- matrix(1, dim(model$GG)[1], dim(model$GG)[1])
Ones_ens <- matrix(1, dim(GG_list[[1]])[1], dim(GG_list[[1]])[1])
########################
C0 <- as.matrix(model$C0)
m0 <- model$m0
ex.df.mat <- as.matrix(ex.df.mat)
ex.df.mat.k <- as.matrix(ex.df.mat.k)
########################
crit_ELBO <- 0
ELBO <- 0
seq.ndlm_elbo = ELBO
iter = 0
FLAG = TRUE
tol1 <- 1e-3
tol2 <- 1e-3
conv.check <- 0
max_iter <- 10
TOL <- 1e-4

if(USE_PREV){
  m0 <- new.theta.out$sm[,1]
  # C0 <- new.theta.out$sC[,,1]
}

# GG[(p+1):(p+J),1:p,] <- 0.01*FF[1:p,1,1]

########################
tictoc::tic("run time")
########################
# while (FLAG & iter < max_iter) {
while ( (FLAG || iter < 10) & (iter < max_iter) ) {
  update.theta <- update_theta_synth_cpp_ndlm(GG, m0, C0, 
                                      D, FF, y, ex.df.mat, ex.df.mat.k, Ones, 
                                      p, J, ppx, TT, k, dM,
                                      GG_list, FF_list,
                                      D_ens,
                                      DF.MAT, DF.MAT_k,
                                      ensembles_forecast, ranges, Ones_ens,
                                      sum(num_mem), num_mem)                         
  ######################################
  ######################################
  # cur.gamsig.out = new.gamsig.out
  cur.theta.out = new.theta.out

  ex.df.mat_f <- as.matrix(ex.df.mat_f)
  ex.df.mat.k_f <- as.matrix(ex.df.mat.k_f)
  ######################################
  ###################################### 

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

  vars <- (apply(vars_1, 3, function(x) diag(x)))
  exps2 = exps^2 + vars

  ####################################################
  ####################################################
  rs <- 0
  for (j in 1:J) {
    dims <- p*(J+1)
    r_j <- length(update.theta$sm_ens[[j]])/(dims-p*(j-1))
    rs <- r_j + rs
    fm_j <- matrix(update.theta$fm_ens[[j]], nrow = (dims-p*(j-1)))
    sm_j <- matrix(update.theta$sm_ens[[j]], nrow = (dims-p*(j-1)))
    fC_j <- array(update.theta$fC_ens[[j]], c((dims-p*(j-1)),(dims-p*(j-1)),r_j))
    sC_j <- array(update.theta$sC_ens[[j]], c((dims-p*(j-1)),(dims-p*(j-1)),r_j))

    FF_synth <- FF_list[[j]]

    FF_t <- t(FF_synth)
    exps_ens <- FF_t %*% sm_j

    compute_product_1 <- function(t) {
        sC_slice <- sC_j[,,t]
        FF_slice <- FF_synth
        result_slice <- t(FF_slice)%*%sC_slice%*%(FF_slice )
        return(result_slice)
    }

    result_list_1 <- lapply(1:r_j, compute_product_1)
    vars_1 <- simplify2array(result_list_1)

    if(j==J){
        vars_ens <- vars_1
    }else{
        vars_ens <- (apply(vars_1, 3, function(x) diag(x)))
    }   
        exps2_ens = exps_ens^2 + vars_ens

    # new.theta.out  <- update.theta 
    
    ######################
    new.theta.out$exps[2:(J-j+2),(TT+1+rs-r_j):(TT+rs)] <- exps_ens
    new.theta.out$exps2[2:(J-j+2),(TT+1+rs-r_j):(TT+rs)] <- exps2_ens
    ######################
    new.theta.out$sm_ens[[j]] <- sm_j
    new.theta.out$sC_ens[[j]] <- sC_j
    new.theta.out$fm_ens[[j]] <- fm_j
    new.theta.out$fC_ens[[j]] <- fC_j

    error_j <- matrix(update.theta$standard_forecast_errors_ens[[j]], nrow = cumsum(num_mem)[J-j+1])
    new.theta.out$standard_forecast_errors_ens[[j]] <- error_j
  }

  ######################
  new.theta.out$exps[,1:TT] <- exps
  new.theta.out$exps2[,1:TT] <- exps2
  ######################
  new.theta.out$standard_forecast_errors <- update.theta$standard_forecast_errors
  new.theta.out$sm <- update.theta$sm
  new.theta.out$sC <- update.theta$sC
  new.theta.out$fm <- update.theta$fm
  new.theta.out$fC <- update.theta$fC
  new.theta.out$elbo.part <- update.theta$elbo.part
  new.theta.out$elbo.part_ens <- update.theta$elbo.part_ens

  old.gam = seq.gamma[,dim(seq.gamma)[2]]
  new.gam = new.gamsig.out$E.gam
  seq.gamma = cbind(seq.gamma, new.gam)

  old.sig = seq.sigma[,dim(seq.sigma)[2]]
  new.sig = new.gamsig.out$E.sigma
  seq.sigma = cbind(seq.sigma, new.sig)

  conv.check <- sum(old.gam-new.gam)^2 + sum(old.sig-new.sig)^2

  ##########
  # ELBO
  ##########

  #################################################################################################### 
  elbo <- 0
  elbo <- elbo + new.theta.out$elbo.part
  #################################################################################################### 
  
  vars <- new.theta.out$exps2-new.theta.out$exps^2
  for(j in 0:J){
      if(j==0){
          a_update[j+1] <- (TT)/2 + a_s
          b_update[j+1] <- 0.5*sum((Y[j+1,]-new.theta.out$exps[j+1,1:TT])^2)+0.5*(sum(vars[j,1:TT]))+b_s
      }else{
          a_update[j+1] <- (TT+ranges[j]*num_mem[J-j+1])/2 + a_s
          b <- 0.5*sum((Y[j+1,]-new.theta.out$exps[j+1,1:TT])^2)+0.5*(sum(vars[j,1:TT]))+b_s
          b <- b + 0.5*sum((ensembles[[j]]-matrix(rep(new.theta.out$exps[j+1,(TT+1):(TT+ranges[j])],num_mem[J-j+1]), ncol = num_mem[J-j+1]))^2)
          b_update[j+1] <- b + 0.5*num_mem[J-j+1]*sum(vars[j+1,(TT+1):(TT+ranges[j])])
      }
  }

  sigma2 <- b_update/(a_update-1) 
  D <- diag(sigma2)
  seq.sigma2 <-  c(seq.sigma2,b_update/(a_update-1)) 
  
  d <- c()
  D_ens <- vector("list", J)
  for(j in 1:(J)){
      dd <- c(rep(new.gamsig.out$E.sigma[j],num_mem[j]))
      d <- c(d,dd) 
      D_ens[[J-j+1]] <- diag(d)
  }

  #################################################################################################### 
  Ts <-  TT*(J+1)+sum(ranges*num_mem)
  elbo <- elbo/Ts/( p*(J+1) + ppx)
  ####################################################################################################  
  crit_ELBO <- abs(elbo-ELBO)
  ELBO <- elbo

  if (crit_ELBO < TOL) {
    FLAG = FALSE
  }

  seq.ndlm_elbo <- c(seq.ndlm_elbo, ELBO)  
  print(c(iter, crit_ELBO, ELBO))
  flush.console()
  iter <- iter+1

}
########################

########################
run.time = tictoc::toc(quiet = TRUE)
########################
# if (verbose) {
#   cat(sprintf("VB converged: %s iterations, %s seconds", 
#               iter, round(run.time$toc - run.time$tic, 3)), "\n")
# }


###########################################################################################
update_uts<-function(y, exps,exps2,sts,sts2,inv.sigma,a2.invb.inv.sigma,invb.inv.sigma,c.invb.absgam,c2.invb.absgam2.sigma){
  u.lambda = 0.5
  u.psi = (a2.invb.inv.sigma + 2*inv.sigma)
  u.chi = invb.inv.sigma*(y^2-2*y*exps+exps2) - 2*c.invb.absgam*sts*(y-exps) + c2.invb.absgam2.sigma*sts2
  u.chi[u.chi<=0] = 1e-6
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

###########################################################################################
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

update_gamma_sigma<-function( y, nn, prior_g, prior_s, 
                              gamma,var.gam,sigma,var.sig,
                              exps,exps2,
                              sts,sts2,
                              uts,inv.uts, 
                              s_init, g_init,
                              Climate_Center,
                              ensembles_j = NULL, num_mem_j = NULL, k_forecast = NULL,
                              sts_f = NULL,sts2_f = NULL,
                              uts_f= NULL,inv.uts_f= NULL){

if(!Climate_Center){
  dq_transf <- function(theta_s,theta_g){
      sig <- exp(theta_s)
      gam <- LL+(-LL+UU)*exp(-exp(theta_g))
          a = A.fn(p0,gam); b = B.fn(p0,gam); c = C.fn(p0,gam); p.fn(p0,gam)

      # Prior
      yy <- log(PriorGammaDens(gam, prior_g)) - (prior_s[1] + 1) * log(sig) - prior_s[2]/sig

      # Likelihood
      yy <- yy - (1.5*nn)*log(sig) - (0.5*nn)*log(b)-sum(uts)/sig 
      yy <- yy - 0.5*sum( inv.uts*(y^2-2*y*exps+exps2)/sig
                      - (y-exps)*2*(inv.uts*c*abs(gam)*sts + a/sig)
                      + sig*inv.uts*(c^2)*(abs(gam)^2)*sts2
                      + 2*c*abs(gam)*sts*a
                      + (uts*a^2)/sig )/b
      
      # Jacobian
      yy <- yy + theta_s + theta_g - exp(theta_g)                   
      return(yy)
  }
}else{

  ensembles_j <- matrix(c(as.matrix(ensembles_j)),ncol = 1)
  sts_f <-  matrix(c(as.matrix(sts_f)),ncol = 1)
  sts2_f <-  matrix(c(as.matrix(sts2_f)),ncol = 1)
  uts_f <-  matrix(c(as.matrix(uts_f)),ncol = 1)
  inv.uts_f <-  matrix(c(as.matrix(inv.uts_f)),ncol = 1)

  dq_transf <- function(theta_s,theta_g){
      sig <- exp(theta_s)
      gam <- LL+(-LL+UU)*exp(-exp(theta_g))
          a = A.fn(p0,gam); b = B.fn(p0,gam); c = C.fn(p0,gam);

      # Prior
      yy <- log(PriorGammaDens(gam, prior_g)) - (prior_s[1] + 1) * log(sig) - prior_s[2]/sig

      # Likelihood
      yy <- yy - 1.5*(nn+k_forecast*num_mem_j)*log(sig) - (0.5*(nn+k_forecast*num_mem_j))*log(b)-(sum(uts)+sum(uts_f))/sig 
      # Before Forecast
      yy <- yy - 0.5*sum( inv.uts*(y^2-2*y*exps[1:nn]+exps2[1:nn])/sig
                      - (y-exps[1:nn])*2*(inv.uts*c*abs(gam)*sts + a/sig)
                      + sig*inv.uts*(c^2)*(abs(gam)^2)*sts2
                      + 2*c*abs(gam)*sts*a
                      + (uts*a^2)/sig )/b
      # After Forecast
      yy <- yy - 0.5*sum( inv.uts_f*(ensembles_j^2-2*ensembles_j*exps[(nn+1):(nn+k_forecast)]+exps2[(nn+1):(nn+k_forecast)])/sig
                      - (ensembles_j-exps[(nn+1):(nn+k_forecast)])*2*(inv.uts_f*c*abs(gam)*sts_f + a/sig)
                      + sig*inv.uts_f*(c^2)*(abs(gam)^2)*sts2_f
                      + 2*c*abs(gam)*sts_f*a
                      + (uts_f*a^2)/sig )/b
      # Jacobian
      yy <- yy + theta_s + theta_g - exp(theta_g)                   
      return(yy)
  }
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

  f.sig <- function(theta){
    sig = exp(theta[1]); 
    yy <- sig
    return(yy)
  }

  f.gam <- function(theta){
    gam = LL+(-LL+UU)*exp(-exp(theta[2]));
    yy <- gam
    return(yy)
  }

  #############################################################################################################################################
  #############################################################################################################################################

  E.sig = Expected_f(f.sig, LD_mu[1], LD_mu[2]);
  E.gam = Expected_f(f.gam, LD_mu[1], LD_mu[2]);


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

  return(list(E.sigma=E.sig,E.inv.sigma=E.inv.sigma,E.gam=E.gam,
              E.c2.invb.absgam2.sigma = E.c2.invb.absgam2.sigma, E.c.invb.absgam = E.c.invb.absgam,
              E.c.a.invb.absgam = E.c.a.invb.absgam, E.a2.invb.inv.sigma = E.a2.invb.inv.sigma,
              E.invb.inv.sigma = E.invb.inv.sigma, E.a.invb.inv.sigma = E.a.invb.inv.sigma,
              Hess.LD = LD_S,
              E.log.sig.b=E.log.sig.b, 
              E.log.sig = E.log.sig, 
              E.prior.sig.gam= E.prior.sig.gam,
              E.theta = LD_mu,
              entrop = entrop))
}

########################
T_size <- c(TT, (TT+ranges))
########################

#############################################################################################################################################
#############################################################################################################################################

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
    concatenated_matrix <- do.call(cbind, lapply(FFF_list[1:J], function(mat) mat[start_row:(start_row + row_num - 1), ]))
    concatenated_list[[J - j + 1]] <- concatenated_matrix
    start_row <- start_row + row_num
  }
  
  # Handle the last remaining rows from the first matrix
  row_num <- nrow(FFF_list[[1]]) - start_row + 1
  concatenated_list[[length(concatenated_list) + 1]] <- FFF_list[[1]][start_row:(start_row + row_num - 1), ]
  
  return(concatenated_list)
}

ensembles_forecast <- concatenate_matrices(ensembles)
ensembles_forecast <- lapply(ensembles_forecast, t)
#############################################################################################################################################
#############################################################################################################################################
########################
# Prior for variances
a_s <- 1e-6
b_s <- 1e-6

if(USE_PREV){
  file_path <- "/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_variables_50_NDLM_synth_DISC.RData"
  load(file_path)
  new.theta.out = new.theta.out_50_NDLM_synth_DISC
}

a_update <- rep(NA_real_, 1+J)
b_update <- rep(NA_real_, 1+J)

vars <- new.theta.out$exps2-new.theta.out$exps^2
for(j in 0:J){
    if(j==0){
        a_update[j+1] <- (TT)/2 + a_s
        b_update[j+1] <- 0.5*sum((Y[j+1,]-new.theta.out$exps[j+1,1:TT])^2)+0.5*(sum(vars[j,1:TT]))+b_s
    }else{
        a_update[j+1] <- (TT+ranges[j]*num_mem[J-j+1])/2 + a_s
        b <- 0.5*sum((Y[j+1,]-new.theta.out$exps[j+1,1:TT])^2)+0.5*(sum(vars[j,1:TT]))+b_s
        b <- b + 0.5*sum((ensembles[[j]]-matrix(rep(new.theta.out$exps[j+1,(TT+1):(TT+ranges[j])],num_mem[J-j+1]), ncol = num_mem[J-j+1]))^2)
        b_update[j+1] <- b + 0.5*num_mem[J-j+1]*sum(vars[j+1,(TT+1):(TT+ranges[j])])
    }
}

sigma2 <- b_update/(a_update-1) 
seq.sigma2 <-  sigma2
D <- diag(sigma2)

d <- c()
D_ens <- vector("list", J)
for(j in 1:(J)){
    dd <- c(rep(new.gamsig.out$E.sigma[j],num_mem[j]))
    d <- c(d,dd) 
    D_ens[[J-j+1]] <- diag(d)
}
########################
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
# crit_ELBO <- 0
# ELBO <- 0
# seq.ndlm_elbo = ELBO
iter = 0
FLAG = TRUE
tol1 <- 1e-3
tol2 <- 1e-3
conv.check <- 0
# max_iter <- 1000
TOL <- 1e-3

if(USE_PREV){
  m0 <- new.theta.out$sm[,1]
  C0 <- new.theta.out$sC[,,1]
}


if(SIMS){
tictoc::tic("run time")
n.samp <- 2000

########################
# if (verbose) {
#   cat(sprintf("Sampling Started", 
#               iter, round(run.time$toc - run.time$tic, 3)), "\n")
# }

########################
samp.sigma = array(NA_real_, c(J+1, n.samp))
samp.sigma <- t(matrix(rinvgamma(n.samp*length(sigma2) , shape = a_update, rate = 1/b_update),nrow=length(sigma2)))

########################
result_retro <- DISC_generate_synth_samples_retro_part(n.samp, TT, length(m0), new.theta.out$sC, new.theta.out$sm) 
########################

result_forecast <- vector("list", length(num_mem))
ks <- 0
for (j in 1:(J-1)) {
  ks <- ranges[J-j+1]-ks
  result_forecast[[j]] <- DISC_generate_synth_samples_retro_part(n.samp, ks, length(new.theta.out$sm_ens[[j]][,1]), new.theta.out$sC_ens[[j]], new.theta.out$sm_ens[[j]]) 
}
mvnorm_sampler_vectorized <- function(mu, S, n.sample) {
  p <- nrow(mu)
  T <- ncol(mu)
  samples <- array(0, dim = c(p, T, n.sample))
  for (t in 1:T) {
    samples[,t,] <- mvrnorm(n = n.sample, mu = mu[,t], Sigma = S[,,t])
  }  
  return(samples)
}
j <- J
S <- new.theta.out$sC_ens[[j]]
mu <- new.theta.out$sm_ens[[j]]
result_forecast[[j]]  <- list("samp_theta"=mvnorm_sampler_vectorized(mu, S, n.samp))
########################
########################
########################

########################
run.time = tictoc::toc(quiet = TRUE)
########################
# if (verbose) {
#   cat(sprintf("Sampling finished:  %s seconds", round(run.time$toc - run.time$tic, 3)), "\n")
# }

if (SAVE) {

save_variables <- function(var_names, filename, dir_path) {
  file_path <- file.path(dir_path, filename)
  save_cmd <- paste("save(", paste(var_names, collapse = ", "), ", file = file_path)")
  eval(parse(text = save_cmd))
  # cat("Variables saved to:", file_path, "\n")
}
result_suffix <- sprintf("%.0f", p0 * 100)
samp.sigma_name <- paste0("samp.sigma_", result_suffix, ending)

samp.theta_name <- paste0("samp.theta_", result_suffix, ending)
samp.theta_ens_name <- paste0("samp.theta_ens_", result_suffix, ending)

new.theta.out_name <- paste0("new.theta.out_", result_suffix, ending)
new.theta.out_ens_name <- paste0("new.theta_ens.out_", result_suffix, ending)

seq.sigma_name <- paste0("seq.sigma_", result_suffix, ending)
seq.elbo_name <- paste0("seq.elbo_", result_suffix, ending)

delta_name <- paste0("delta_", result_suffix, ending)

assign(delta_name, delta)
assign(samp.sigma_name, samp.sigma)
assign(samp.theta_name, result_retro)
assign(samp.theta_ens_name, result_forecast)
assign(new.theta.out_name, new.theta.out)
assign(seq.sigma_name, seq.sigma)
assign(seq.elbo_name, seq.ndlm_elbo)

vars_to_save <- c(samp.sigma_name, 
                  samp.theta_name,
                  samp.theta_ens_name,
                  new.theta.out_name,
                  seq.sigma_name, 
                  seq.elbo_name, delta_name)
# Save the variables
save_variables(vars_to_save, paste0("DISC_variables_", result_suffix, ending,".RData"), "/data/muscat_data/jaguir26/project1_ucsc_phd")
}

}


# ######################
# errors <- new.theta.out$standard_forecast_errors
# s <- 0.5*(compute_kl_divergence(t(errors))+estimate_kl_divergence(t(errors)))
# ######################

# # Function to compute JSD for a given sample matrix
# compute_jsd <- function(p_sample, gridsize = c(100, 100, 100)) {
  
#   # Step 2: Perform KDE on the sample to estimate the density of p
#   kde_p <- kde(p_sample, gridsize = gridsize)  # KDE estimation with custom grid size

#   # Step 3: Define the grid and evaluate the KDE density
#   pdf_p <- kde_p$estimate  # Estimated density of p on the grid
#   dim_p <- dim(pdf_p)
#   # cat("Dimensions of pdf_p:", dim_p, "\n")  # Print the dimensions of pdf_p

#   # Step 4: Define the distribution q (standard multivariate normal)
#   mean_q <- rep(0, 3)  # Mean vector of zeros for q
#   cov_q <- diag(3)     # Identity matrix as covariance for q

#   # Step 5: Evaluate the PDF for q on the same grid as kde_p
#   grid_points <- kde_p$eval.points  # Grid points used in kde_p

#   # Create a matrix of all grid points where the densities are evaluated
#   grid_matrix <- expand.grid(grid_points[[1]], grid_points[[2]], grid_points[[3]])

#   # Calculate the density for the standard normal on the same grid
#   pdf_q <- dmvnorm(as.matrix(grid_matrix), mean = mean_q, sigma = cov_q)
#   pdf_q <- array(pdf_q, dim = dim_p)  # Reshape to match the dimension of pdf_p
#   # cat("Dimensions of pdf_q:", dim(pdf_q), "\n")  # Print the dimensions of pdf_q

#   # Step 6: Normalize the densities
#   pdf_p <- pdf_p / sum(pdf_p)
#   pdf_q <- pdf_q / sum(pdf_q)

#   # Step 7: Function to compute the KL divergence
#   KL.divergence <- function(p, q) {
#     epsilon <- 1e-10  # Small value to prevent division by zero or log of zero
#     p <- p + epsilon
#     q <- q + epsilon
#     return(sum(p * log(p / q)))
#   }

#   # Step 8: Function to compute the Jensen-Shannon divergence
#   JSD <- function(p, q) {
#     m <- 0.5 * (p + q)
#     return(0.5 * KL.divergence(p, m) + 0.5 * KL.divergence(q, m))
#   }

#   # Step 9: Compute the Jensen-Shannon divergence
#   js_divergence <- JSD(pdf_p, pdf_q)
#   return(js_divergence)
# }

# js_divergence <- compute_jsd(t(errors), gridsize = c(100, 100, 100)


############################################################################################################
############################################################################################################
##### CRPS #################################################################################################
############################################################################################################
############################################################################################################
library(doParallel)
library(foreach)
library(abind)

# Precompute invariant matrices outside parallel loop
FF_t <- aperm(FF, c(2, 1, 3))
J1 <- J + 1

# Precompute covariance components without loops
compute_product_1 <- function(t) {
  t(FF[,,t]) %*% new.theta.out$sC[,,t] %*% FF[,,t]
}
precomputed_cov <- simplify2array(lapply(1:dim(FF)[3], compute_product_1))

# Define CRPS functions in global environment
compute_crps <- function(x) {
  cdf <- pnorm(x)
  2 * (x * (cdf - 0.5) + dnorm(x)) - 1/sqrt(pi)
}

compute_mean_crps <- function(errors, q) {
  q * vapply(errors, compute_crps, numeric(1))
}

assign("precomputed_cov", precomputed_cov, envir = .GlobalEnv)
assign("FF_t", FF_t, envir = .GlobalEnv)
assign("Y", Y, envir = .GlobalEnv)
assign("J1", J1, envir = .GlobalEnv)
assign("TT", TT, envir = .GlobalEnv)
assign("samp.sigma", samp.sigma, envir = .GlobalEnv)
assign("compute_crps", compute_crps, envir = .GlobalEnv)
assign("result_retro", result_retro, envir = .GlobalEnv)
assign("compute_mean_crps", compute_mean_crps, envir = .GlobalEnv)
assign("FF", FF, envir = .GlobalEnv)
assign("new.theta.out", new.theta.out, envir = .GlobalEnv)
                             
# # Set up parallel backend
# cl <- makeCluster(detectCores() - 5)  #
# registerDoParallel(cl)

# # Export necessary variables
# clusterExport(cl, 
#               c("precomputed_cov", "FF_t", "Y", "J1", "TT",
#                    "samp.sigma", "compute_crps", "result_retro",
#                    "compute_mean_crps", "FF", "new.theta.out")
#                ,envir = .GlobalEnv
#              )

# ############################################################################################################
# ############################################################################################################
                                                 
# foreach_opts <- list(chunkSize = ceiling(n.samp/(detectCores()*4)))
# result_list <- foreach(s = 1:n.samp, .options.foreach = foreach_opts, .packages = "abind") %dopar% {

#   # Vectorized operations
#   theta_s <- result_retro$samp_theta[,,s]
#   sig_s <- t(samp.sigma)[,s]
  
#   # Matrix multiplication using tensor operations
#   xbs_sample <- vapply(1:TT, function(t) FF_t[,,t] %*% theta_s[,t], numeric(J1))
  
#   # Predictive sampling with vectorized noise
#   y_post_sample <- xbs_sample + matrix(rnorm(J1*TT, 0, sqrt(sig_s)), nrow = J1)
  
#   D <- diag(sig_s, J1)
#   Sbs_sample <- precomputed_cov + array(D, dim = c(J1, J1, TT))
  
#   # Vectorized error standardization
#   Var_diag <- sqrt(matrix(Sbs_sample[cbind(1:J1, 1:J1, rep(1:TT, each=3))], nrow=J1))
#   errors_sample <- (Y - y_post_sample) / Var_diag
  
#   # Vectorized CRPS calculation
#   CRPS_sample <- sapply(1:J1, function(j) {
#     compute_mean_crps(errors_sample[j,], Var_diag[j,])
#   })
#   # CRPS_sample <- compute_mean_crps(t(errors_sample), t(Var_diag)) %>% t()

#   list(
#     Sbs = Sbs_sample,
#     xbs = xbs_sample,
#     y_post = y_post_sample,
#     errors = errors_sample,
#     CRPS = t(CRPS_sample)
#   )
# }
# ############################################################################################################
# ############################################################################################################

# # Function to efficiently combine results
# combine_results <- function(lst, name, expected_dim) {
#   result <- lapply(lst, `[[`, name)
#     # Check if the result should be a 4D array
#   if (length(dim(result[[1]])) == 3) {
#     return(simplify2array(result))  # Efficient array combination
#   } else if (is.matrix(result[[1]])) {
#       return(simplify2array(result))
#   } else {
#     return(unlist(result))  # Fallback for vectors
#   }
# }

# # Combine results properly
# Sbs <- combine_results(result_list, "Sbs", c(J1, J1, TT, length(result_list)))
# xbs <- combine_results(result_list, "xbs", c(J1, TT, length(result_list)))
# y_post_pred_ndlm <- combine_results(result_list, "y_post", c(J1, TT, length(result_list)))
# errors_post_pred_ndlm2 <- combine_results(result_list, "errors", c(J1, TT, length(result_list)))
# CRPS_values <- combine_results(result_list, "CRPS", c(J1, TT, length(result_list)))

# # Shutdown the parallel cluster
# stopCluster(cl)

# # Compute CRPS summaries
# crps_per_time <- apply(CRPS_values, c(1, 2), mean, na.rm = TRUE)  # Output: (3, TT)
# crps_per_sim  <- apply(CRPS_values, c(1, 3), mean, na.rm = TRUE)  # Output: (3, n.samp)
# global_crps   <- mean(CRPS_values, na.rm = TRUE)  # Overall mean
# marginal_crps <-rowMeans(crps_per_sim)
                                                 
# # END 

# print(marginal_crps[1])
# flush.console()

# return(marginal_crps[1])
return("done!")
} 


############################################################################################################
############################################################################################################

initial_delta <- c(0.999999, 0.996, 0.9975, 0.9997, 0.99, 0.99) 
# initial_delta <- c(df_t  , df_s1 , df_s2 , df_s67, df_discrep, lambda)


lower_bounds  <- c(0.9991, 0.9991, 0.9991, 0.9991, 0.9991, 0.9)
upper_bounds  <- rep(0.9999, length(initial_delta))

objective_deltas_min <- function(delta) {
  objective_deltas(delta, TRUE, TRUE)  
} 

#############################################################################################################
#############################################################################################################

opts <- list("algorithm" = "NLOPT_LN_BOBYQA",  
             "xtol_rel" = 1.0e-6,
             "maxeval" = 1000)

# result <- nloptr(x0 = initial_delta,
#                  eval_f = objective_deltas_min,  
#                  lb = lower_bounds,
#                  ub = upper_bounds,
#                  opts = opts)
# d = as.numeric(c(result$solution))
# print(result)  


d <- initial_delta
objective_deltas(d, TRUE, TRUE);

# Optimal value of objective function:  0.13349522603962 
# Optimal value of controls: 0.9979 0.9979077 0.9979 0.9979 0.9994296 0.9894808
# Optimal value of objective function:  0.133487324402348 
# Optimal value of controls: 0.9979 0.9979001 0.9979 0.9979 0.997982 0.3989718



############################################################################################################
############################################################################################################

# # Load required packages
# if (!requireNamespace("GA", quietly = TRUE)) {
#   install.packages("GA")
# }
# if (!requireNamespace("parallel", quietly = TRUE)) {
#   install.packages("parallel")
# }

# library(GA)
# library(parallel)

# # Function to optimize weights
# optimize_weights <- function() {
#   ga_result <- ga(
#     type = "real-valued",
#     fitness = function(d) -objective_deltas_min(d),  # Minimize loss by negating
#     lower = lower_bounds,
#     upper = upper_bounds,
#     popSize = 50,
#     maxiter = 200,
#     run = 20,
#     parallel = TRUE  # Disable internal parallel processing in GA
#   )
  
#   optimal_d <- ga_result@solution / sum(ga_result@solution)
#   minimum_loss <- -ga_result@fitnessValue
  
#   list(Optimal_Weights = optimal_d, Minimum_Loss = minimum_loss)
# }

# optimize_weights()
############################################################################################################
############################################################################################################

# library(nloptr)
# library(future)
# library(future.apply)

# # ================================
# #  Parallel Setup
# # ================================
# workers <- c("jaguir26@muscat.be.ucsc.edu", "jaguir26@jerez.be.ucsc.edu")
# plan(cluster, workers = workers)

# # ================================
# #  Parallelizing Function Evaluations
# # ================================
# parallel_objective <- function(X) {
#   results <- future_sapply(X, objective_deltas_min)
#   return(results)
# }

# # ================================
# #  Run Optimization with Parallel Evaluations
# # ================================
# opts <- list("algorithm" = "NLOPT_LN_BOBYQA",  
#              "xtol_rel" = 1.0e-6,
#              "maxeval" = 1000)

# result <- nloptr(
#   x0 = c(0.9995, 0.9995, 0.9995, 0.9995, 0.9995, 0.97),
#   eval_f = function(x) parallel_objective(list(x)),  # Parallel function evaluations
#   lb = c(0.9991, 0.999, 0.999, 0.999, 0.999, 0.9),
#   ub = rep(0.999999, 6),
#   opts = opts
# )

# # Print results
# print(result$solution)

############################################################################################################
# Load required packages
############################################################################################################
# library(GA)
# library(future)
# library(future.apply)

# # ===========================================
# #  Parallel Setup: Use Both Servers
# # ===========================================
# workers <- c("jaguir26@muscat.be.ucsc.edu", "jaguir26@jerez.be.ucsc.edu")

# # Set up a cluster for parallel execution
# plan(cluster, workers = workers)

# # ===========================================
# #  Parallelized Fitness Evaluation Function
# # ===========================================
# parallel_fitness <- function(d) {
#   future_sapply(d, objective_deltas_min, future.seed = TRUE)  # Ensures reproducibility
# }

# # ===========================================
# #  Genetic Algorithm Optimization
# # ===========================================
# optimize_weights <- function() {
#   ga_result <- tryCatch({
#     ga(
#       type = "real-valued",
#       fitness = function(d) -parallel_fitness(d),  # Distribute fitness evaluations
#       lower = c(0.9991, 0.999, 0.999, 0.999, 0.999, 0.9),
#       upper = rep(0.999999, 6),
#       popSize = 50,
#       maxiter = 200,
#       run = 20,
#       keepBest = TRUE,  # Retain best solutions across generations
#       parallel = FALSE  # Disable GA's built-in parallelism, use future instead
#     )
#   }, error = function(e) {
#     message("Error in GA optimization: ", e$message)
#     return(NULL)
#   })

#   if (is.null(ga_result)) {
#     return(NULL)
#   }

#   optimal_d <- ga_result@solution / sum(ga_result@solution)
#   minimum_loss <- -ga_result@fitnessValue

#   list(Optimal_Weights = optimal_d, Minimum_Loss = minimum_loss)
# }

# # ===========================================
# #  Run the Optimization
# # ===========================================
# result <- optimize_weights()

# # Print results if optimization was successful
# if (!is.null(result)) {
#   print(result)
# } else {
#   message("Optimization failed.")
# }
