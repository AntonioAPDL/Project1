# Auto-generated from Environmetrics_Figures.ipynb

#### CELL 001 ####
# Config
if (!exists("SKIP_UNIVARIATE", inherits = FALSE)) SKIP_UNIVARIATE <- FALSE
site_code <- c("11160500")


#### CELL 002 ####


#### CELL 003 ####
standardize <- function(x) {
  m <- mean(x, na.rm = TRUE)
  s <- sd(x, na.rm = TRUE)
  if (is.na(s) || s == 0) {
    return(x - m)
  }
  (x - m) / s
}


#### CELL 004 ####
.libPaths(c("~/R/libs", .libPaths()))
print(.libPaths())


# Load only what's necessary early
library(parallel)
library(dplyr)
library(tidyverse)  # Consider using only tidyverse OR individual packages



#### CELL 005 ####
#!/usr/bin/env Rscript
library(parallel)
library(dlm)
library(exdqlm)
library(mvtnorm)
library(jmuOutlier)
library(sn)
library(Matrix)
# library(future)
# library(future.apply)
library(numDeriv)
library(foreach)
library(doParallel)
library(dataRetrieval)
# library(dplyr)
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
# library(Rcpp)
library(RcppArmadillo)
library(RcppEigen)
library(ks)
library(MASS)
library(FNN)

n.samp <- 2000
cut <- 1
m <- 2
USE_PREV <- TRUE

p0 <- 0.5
harmonics = c(1, 2, 1/6.8068493)   
# harmonics = c(363.5854/90, 363.5854/180, 1/6.8068493)      

# Sys.setenv("PKG_CXXFLAGS"="-I/data/muscat_data/jaguir26/libs/eigen -I/data/muscat_data/jaguir26/libs/boost/include -DEIGEN_DONT_VECTORIZE")
# Sys.setenv("PKG_LIBS"="-L/data/muscat_data/jaguir26/libs/lib64 -L/data/muscat_data/jaguir26/libs/boost/lib -llapack -lblas -lboost_random -lboost_system -fopenmp")
# Sys.setenv(LD_LIBRARY_PATH="/data/muscat_data/jaguir26/libs/lib64:/data/muscat_data/jaguir26/libs/boost/lib:/lib64")

# Rcpp::sourceCpp("/data/muscat_data/jaguir26/project1_ucsc_phd/sampling_exal.cpp")
# Rcpp::sourceCpp("/data/muscat_data/jaguir26/project1_ucsc_phd/sampling_truncnorm.cpp")
# Rcpp::sourceCpp("/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_kalman_synth.cpp")
 


#### CELL 006 ####
Rcpp::sourceCpp("/data/muscat_data/jaguir26/project1_ucsc_phd/task_medium/src/exAL.cpp")  


#### CELL 007 ####
# initial_delta for multivariate runs
# initial_delta <- c(0.999999, 0.9952, 0.995, 0.9997, 0.9988, 0.977)
initial_delta   <- c(0.9999995, 0.9997, 0.9997, 0.9997, 0.999, 0.8995)
# initial_delta <- c(df_t  , df_s1 , df_s2 , df_s67, df_discrep, lambda)
# initial_delta_uni matches OptimalModelSLexAL.r (univariate)
initial_delta_uni <- c(0.9999995, 0.9997, 0.9997, 0.9997, 0.8995)


#### CELL 008 ####
delta <- initial_delta

SIMS <- TRUE
use_covariates <- TRUE

lam1 <- 1-1e-6 # Sudden correction at start of forecast period
lam2 <- 1-1e-6 # Correction during forecast period from historical period

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
  ### Gets the     Time Series Length / Replicate number
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
  return(list(fm = m, fC = C, m = sa, C = sR,model = model, s = i, n = l))
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
    B = C[TT-k,,] %*% t(GG[,,i]) %*% solve(R[TT-k+1,,])
    sa[TT-k,] = m[TT-k,] + B %*% (sa[TT-k+1,] - a[TT-k+1,])
    sR[TT-k,,] = C[TT-k,,] + B %*% (sR[TT-k+1,,] - R[TT-k+1,,]) %*% t(B)
  }
  ### Adjusts the variance update
  for(k in 1:TT){
    sR[TT-k,,] = S[TT] * sR[TT-k,,] / S[TT-k]
  }
  return(list(fm = m, fC = C, m = sa, C = sR,model = model, s = i, n = l))
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


#### CELL 009 ####
# Read and process ELI_lon data
ELI_lon <- read.csv(COV_1_ELI_PATH)
merged_sst_data <- read.csv(COV_2_ONI_PATH)
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


#### CELL 010 ####

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


#### CELL 011 ####
## Build the matrix exactly as requested
data <- cbind(t(Y), X)

## Save an .rds to preserve the matrix object "as is"
saveRDS(
  object = data,
  file   = "/data/muscat_data/jaguir26/project1_ucsc_phd/data_cbind_tY_X.rds"
)

## (Optional) Also write a CSV for quick inspection
## Note: CSV will coerce to a data frame for writing, but values are unchanged.
write.csv(
  x         = data,
  file      = "/data/muscat_data/jaguir26/project1_ucsc_phd/data_cbind_tY_X.csv",
  row.names = FALSE
)


#### CELL 012 ####


if(use_covariates){
  ending <- "_exAL_synth_DISC"
}else{
  ending <- "_exAL_synth_simp"
}
#
# Model setup without covariates
s_yy <- sd(Y, na.rm = TRUE)  
m_yy <- mean(Y, na.rm = TRUE) + s_yy*qnorm(p0)
kk <- 0.1 * s_yy
trend.comp <- polytrendMod(1, m0 = m_yy, C0 = kk)
harm <- harmonics
seas.comp <- seasMod(p = 363.5854, h = harm, C0 = 0.08 * kk * diag(2 * length(harm)))
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
C0 <- bdiag(model$C0, 0.1 * kk * diag(p*J))
##########################################  
##########################################
df <- c(df_t, df_s1, df_s2, df_s67)
df.discrep <- df.discrep*rep(df,J)
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


#### CELL 013 ####
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



#### CELL 014 ####

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


#### CELL 015 ####


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


#### CELL 016 ####
write.csv(timestamps, "/data/muscat_data/jaguir26/project1_ucsc_phd/timestamps.csv", row.names = FALSE)
# timestamps_loaded <- read.csv("/data/muscat_data/jaguir26/project1_ucsc_phd/timestamps.csv")
# timestamps_loaded$Date <- as.Date(timestamps_loaded$Date)
# head(timestamps_loaded)


#### CELL 017 ####
library(matrixStats)

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
        y_lower <- quantile(y_reps[idx, , t_idx], probs = u)
        y_upper <- quantile(y_reps[idx+1, , t_idx], probs = u)
        result <- (1 - w) * y_lower + w * y_upper
        out[i, t_idx] <- result
      }else{
        if(idx == 0){
          out[i, t_idx] <- quantile(y_reps[idx+1, , t_idx], probs = u)
        }else{
          out[i, t_idx] <- quantile(y_reps[idx, , t_idx], probs = u)
        }
      }
    }
  }
  return(out)
}


#### CELL 018 ####
p <- 7
file_path <- "/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_variables_50_NDLM_synth_DISC.RData"
load(file_path)


#### CELL 019 ####
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




#### CELL 020 ####
plot.ts(idx,(new.theta.out_50_NDLM_synth_DISC$sm[c(1),idx]), ylim = c(-2,2))
lines(idx,Y[1,idx], col = 'gray')
lines(new.theta.out_50_NDLM_synth_DISC$sm[22,]+(new.theta.out_50_NDLM_synth_DISC$sm[c(1),]), col = 'red')
lines(idx,new.theta.out_50_NDLM_synth_DISC$sm[22,idx]+(new.theta.out_50_NDLM_synth_DISC$sm[c(2),idx])+(new.theta.out_50_NDLM_synth_DISC$sm[c(1),idx]), col = 'blue')


#### CELL 021 ####
# ## Stochastic Matrix at Forecasting period edits

covs_list <- vector("list", J)
ranges_per <- ranges-c(ranges[2:(J)],0)
dim_theta <- p*(J:1)
for(i in 1:J){
covs_list[[i]] <- array(NA_real_,c(dim_theta[i],dim_theta[i],ranges_per[(J-i)+1]))
}



#### CELL 022 ####
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

# Example: inspect the first covariance matrix of the first period
print(covs_list[[2]][ , , 1])

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


#### CELL 023 ####
dim(new.theta.out_50_NDLM_synth_DISC$sC_ens[[1]])
dim(new.theta.out_50_NDLM_synth_DISC$sC_ens[[2]])
dim(new.theta.out_50_NDLM_synth_DISC$sm_ens[[1]])
dim(new.theta.out_50_NDLM_synth_DISC$sm_ens[[2]])


#### CELL 024 ####
file_path <- "/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_variables_5_exAL_synth_DISC.RData"
load(file_path)


#### CELL 025 ####

file_path <- "/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_variables_50_exAL_synth_DISC.RData"
load(file_path)


#### CELL 026 ####

file_path <- "/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_variables_95_exAL_synth_DISC.RData"
load(file_path)


#### CELL 027 ####

file_path <- "/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_variables_20_exAL_synth_DISC.RData"
load(file_path)


#### CELL 028 ####

file_path <- "/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_variables_35_exAL_synth_DISC.RData"
load(file_path)


#### CELL 029 ####

file_path <- "/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_variables_65_exAL_synth_DISC.RData"
load(file_path)


#### CELL 030 ####

file_path <- "/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_variables_80_exAL_synth_DISC.RData"
load(file_path)


#### CELL 031 ####

file_path <- "/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_variables_50_NDLM_synth_DISC.RData"
load(file_path)


#### CELL 032 ####
n.samp <- 2000


#### CELL 033 ####
p <- 7


#### CELL 034 ####
png("/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics/All_ELBOS_DISC.png", width = 6000, height = 4000, res = 600)
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


#### CELL 035 ####
p <- 7


#### CELL 036 ####
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


#### CELL 037 ####
prepare_quantile_data <- function(v_d) {
  v_d_transposed <- aperm(v_d, c(3, 1, 2))
  q_d_transposed <- apply(v_d_transposed, 2:3, function(x) quantile(x, probs = c(0.975, 0.5, 0.025)))
  q_d <- aperm(q_d_transposed, c(2, 3, 1))
  return(q_d)
}

q_d_discrep1_quantiles <- prepare_quantile_data(xb_discrep1)
q_d_discrep2_quantiles <- prepare_quantile_data(xb_discrep2)



#### CELL 038 ####
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


#### CELL 039 ####
for(t in 1:ranges[1]){
    xbs[1,t,] <- sort(xbs[1,t,])
    xbs[2,t,] <- sort(xbs[2,t,])
    xbs[3,t,] <- sort(xbs[3,t,])
    xbs[4,t,] <- sort(xbs[4,t,])
    xbs[5,t,] <- sort(xbs[5,t,])
    xbs[6,t,] <- sort(xbs[6,t,])
    xbs[7,t,] <- sort(xbs[7,t,])
}


#### CELL 040 ####
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


#### CELL 041 ####
library(truncnorm)
set.seed(777)

# Function Definitions
inverse_cdf_AL <- function(U, mu, sigma, p) {
  ifelse(U < p, 
         mu + (sigma / (1 - p)) * log(U / p), 
         mu - (sigma / p) * log((1 - U) / (1 - p)))
}

p.fn <- function(p0, gam) {
  (p0 - as.numeric(gam < 0)) / exp(log.g(gam)) + as.numeric(gam < 0)
}

C.fn <- function(p0, gam) {
  temp.p <- p.fn(p0, gam)
  (as.numeric(gam > 0) - temp.p)^(-1)
}

# Generalized function to handle each case
generate_y_post <- function(p0, xb_matrix, gamma_sample, sigma_sample) {
  n_rows <- dim(xb_matrix)[1]
  n_cols <- dim(xb_matrix)[2]
  y_post <- matrix(NA_real_, nrow = n_rows, ncol = n_cols)
  
  for (t in 1:n_cols) {
    s_0 <- rtruncnorm(1, a=0, b=Inf, mean = 0, sd = 1)
    u <- runif(n_rows)
    y_post[,t] <- xb_matrix[,t] + sigma_sample * abs(gamma_sample) * C.fn(p0, gamma_sample) * s_0 +  
                  sigma_sample * inverse_cdf_AL(u, 0, 1, p.fn(p0, gamma_sample))
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


#### CELL 042 ####
dim(y_post_35)


#### CELL 043 ####
for(t in 1:ranges[1]){
    xbs[1,t,] <- sort(xbs[1,t,])
    xbs[2,t,] <- sort(xbs[2,t,])
    xbs[3,t,] <- sort(xbs[3,t,])
    xbs[4,t,] <- sort(xbs[4,t,])
    xbs[5,t,] <- sort(xbs[5,t,])
    xbs[6,t,] <- sort(xbs[6,t,])
    xbs[7,t,] <- sort(xbs[7,t,])
}


#### CELL 044 ####
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
  quantiles <- apply(y_post, 2, quantile, probs = c(0.05, 0.5, 0.95))
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


#### CELL 045 ####

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


#### CELL 046 ####

# Applying quantile computations and mean for each case
compute_quantiles_means <- function(y_post, q0) {
  quantiles <- apply(y_post, 2, quantile, probs = c(q0, 0.025,0.5,0.975))
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
for(t in 1:ranges[1]){
    w <- rep(0,7)
    for(s in 1:n.samp){
        diff <- y_post_5[s,t]-q5$quantiles[1,t]
        w[1] <- exp(-k*CheckLossFn(0.05,diff)/samp.sigma_5_exAL_synth_DISC[1,s])
        diff <- y_post_50[s,t]-q50$quantiles[1,t]
        w[2] <- exp(-k*CheckLossFn(0.5,diff)/samp.sigma_50_exAL_synth_DISC[1,s])
        diff <- y_post_95[s,t]-q95$quantiles[1,t]
        w[3] <- exp(-k*CheckLossFn(0.95,diff)/samp.sigma_95_exAL_synth_DISC[1,s])
        diff <- y_post_20[s,t]-q20$quantiles[1,t]
        w[4] <- exp(-k*CheckLossFn(0.2,diff)/samp.sigma_20_exAL_synth_DISC[1,s])
        diff <- y_post_35[s,t]-q35$quantiles[1,t]
        w[5] <- exp(-k*CheckLossFn(0.35,diff)/samp.sigma_35_exAL_synth_DISC[1,s])
        diff <- y_post_80[s,t]-q80$quantiles[1,t]
        w[6] <- exp(-k*CheckLossFn(0.80,diff)/samp.sigma_80_exAL_synth_DISC[1,s])
        diff <- y_post_65[s,t]-q65$quantiles[1,t]
        w[7] <- exp(-k*CheckLossFn(0.65,diff)/samp.sigma_65_exAL_synth_DISC[1,s])
        w <- w/sum(w)
        synth_q_f[s,t] <- sum(w*c(q5$quantiles[1,t],q50$quantiles[1,t],q95$quantiles[1,t],
                                  q20$quantiles[1,t],q35$quantiles[1,t],q80$quantiles[1,t],q65$quantiles[1,t]))
    } 
}

q_synth <- apply(synth_q_f, 2, quantile, probs = c(0.025, 0.5, 0.975))
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



#### CELL 047 ####
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


#### CELL 048 ####
for(t in 1:ranges[1]){
    xbs_retro[1,t,] <- sort(xbs_retro[1,t,])
    xbs_retro[2,t,] <- sort(xbs_retro[2,t,])
    xbs_retro[3,t,] <- sort(xbs_retro[3,t,])
    xbs_retro[4,t,] <- sort(xbs_retro[4,t,])
    xbs_retro[5,t,] <- sort(xbs_retro[5,t,])
    xbs_retro[6,t,] <- sort(xbs_retro[6,t,])
    xbs_retro[7,t,] <- sort(xbs_retro[7,t,])
}


#### CELL 049 ####
truth<- San_Lorenzo_Daily_USGS_R$data0[San_Lorenzo_Daily_USGS_R$Date>=as.Date('2022-12-26')]
# truth <- truth[1:ranges[1]]
truth <- log(truth[1:ranges[1]]+1)


#### CELL 050 ####
FF_t <- aperm(FF, c(2, 1, 3))
multiply_matrices <- function(slice_index) {
    FF_t[,,slice_index] %*% new.theta.out_50_exAL_synth_DISC$sm[,slice_index]
}
result_list <- lapply(1:ncol(new.theta.out_50_exAL_synth_DISC$sm), multiply_matrices)
result_array <- array(unlist(result_list), dim = c(J+1, 1, ncol(new.theta.out_50_exAL_synth_DISC$sm)))
result_array <- aperm(result_array, c(1, 3, 2))[,,1]
dim( result_array )
TT


#### CELL 051 ####
idx <- (TT-300):TT
plot.ts(Y[1,idx], col = 'gray')
points(Y[1,idx], col = 'black')
lines(new.theta.out_50_exAL_synth_DISC$exps[1,idx], col = 'green')
lines(new.theta.out_5_exAL_synth_DISC$exps[1,idx], col = 'red')
lines(new.theta.out_95_exAL_synth_DISC$exps[1,idx], col = 'blue')
# lines(new.theta.out_50_exAL_synth$exps[1,], col = 'green')
# lines(new.theta.out_50_exAL_synth$exps[1,], col = 'green')
# lines(new.theta.out_50_exAL_synth$exps[1,], col = 'green')


#### CELL 052 ####
dates_ts_usgs <- timestamps


#### CELL 053 ####
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
png("/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics/Allth_exal_DISC.png", width = 6000, height = 4000, res = 600)
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
result <- apply(xbs[6,,], 1, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
lines(idx_f, result[1,], col = 'purple', lty = 2, lwd = 1)
lines(idx_f, result[2,], col = 'purple', lwd = 1.5)
lines(idx_f, result[3,], col = 'purple', lty = 2, lwd = 1)
# Adding quantile bands (blue) for 95th Quantile estimation
result <- apply(xbs[5,,], 1, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
lines(idx_f, result[1,], col = 'purple', lty = 2, lwd = 1)
lines(idx_f, result[2,], col = 'purple', lwd = 1.5)
lines(idx_f, result[3,], col = 'purple', lty = 2, lwd = 1)
# Adding quantile bands (blue) for 95th Quantile estimation
result <- apply(xbs[4,,], 1, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
lines(idx_f, result[1,], col = 'green', lty = 2, lwd = 1)
lines(idx_f, result[2,], col = 'darkgreen', lwd = 1.5)
lines(idx_f, result[3,], col = 'green', lty = 2, lwd = 1)
# Adding quantile bands (blue) for 95th Quantile estimation
result <- apply(xbs[3,,], 1, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
lines(idx_f, result[1,], col = 'purple', lty = 2, lwd = 1)
lines(idx_f, result[2,], col = 'purple', lwd = 1.5)
lines(idx_f, result[3,], col = 'purple', lty = 2, lwd = 1)
# Adding quantile bands (blue) for 95th Quantile estimation
result <- apply(xbs[2,,], 1, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
lines(idx_f, result[1,], col = 'purple', lty = 2, lwd = 1)
lines(idx_f, result[2,], col = 'purple', lwd = 1.5)
lines(idx_f, result[3,], col = 'purple', lty = 2, lwd = 1)
# Adding quantile bands (blue) for 95th Quantile estimation
result <- apply(xbs[1,,], 1, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
lines(idx_f, result[1,], col = 'red', lty = 2, lwd = 1)
lines(idx_f, result[2,], col = 'darkred', lwd = 1.5)
lines(idx_f, result[3,], col = 'red', lty = 2, lwd = 1)

idx <- (TT-iii):(TT)

# Adding retrospective quantile estimation (blue)
result <- apply(xbs_retro[1,,], 1, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
lines(1:length(idx), result[1,idx], col = 'red', lty = 2, lwd = 0.5)
lines(1:length(idx), result[2,idx], col = 'darkred', lwd = 0.5)
lines(1:length(idx), result[3,idx], col = 'red', lty = 2, lwd = 0.5)

# Adding retrospective quantile estimation (blue)
result <- apply(xbs_retro[2,,], 1, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
lines(1:length(idx), result[1,idx], col = 'purple', lty = 2, lwd = 0.5)
lines(1:length(idx), result[2,idx], col = 'purple', lwd = 0.5)
lines(1:length(idx), result[3,idx], col = 'purple', lty = 2, lwd = 0.5)

# Adding retrospective quantile estimation (blue)
result <- apply(xbs_retro[3,,], 1, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
lines(1:length(idx), result[1,idx], col = 'purple', lty = 2, lwd = 0.5)
lines(1:length(idx), result[2,idx], col = 'purple', lwd = 0.5)
lines(1:length(idx), result[3,idx], col = 'purple', lty = 2, lwd = 0.5)

# Adding retrospective quantile estimation (blue)
result <- apply(xbs_retro[4,,], 1, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
lines(1:length(idx), result[1,idx], col = 'green', lty = 2, lwd = 0.5)
lines(1:length(idx), result[2,idx], col = 'darkgreen', lwd = 0.5)
lines(1:length(idx), result[3,idx], col = 'green', lty = 2, lwd = 0.5)

# Adding retrospective quantile estimation (blue)
result <- apply(xbs_retro[5,,], 1, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
lines(1:length(idx), result[1,idx], col = 'purple', lty = 2, lwd = 0.5)
lines(1:length(idx), result[2,idx], col = 'purple', lwd = 0.5)
lines(1:length(idx), result[3,idx], col = 'purple', lty = 2, lwd = 0.5)


# Adding retrospective quantile estimation (blue)
result <- apply(xbs_retro[6,,], 1, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
lines(1:length(idx), result[1,idx], col = 'purple', lty = 2, lwd = 0.5)
lines(1:length(idx), result[2,idx], col = 'purple', lwd = 0.5)
lines(1:length(idx), result[3,idx], col = 'purple', lty = 2, lwd = 0.5)


# Adding retrospective quantile estimation (blue)
result <- apply(xbs_retro[7,,], 1, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
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

# Adding current-rating discharge-reference levels (horizontal dashed lines) with labels
lev_flood <- c(14895.73, 11302.95, 7402.38, 4864.84) * CFSToCMS_CONVERSION_FACTOR
flood_labels <- c("Major reference", "Moderate reference", "Minor reference", "Action reference")
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


#### CELL 054 ####
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

png("/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics/All3_exal_DISC.png", width = 6000, height = 4000, res = 600)
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
result <- apply(xbs[7,,], 1, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
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
result <- apply(xbs[4,,], 1, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
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
result <- apply(xbs[1,,], 1, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
lines(idx_f, result[1,], col = 'red', lty = 2, lwd = 1)
lines(idx_f, result[2,], col = 'darkred', lwd = 1.5)
lines(idx_f, result[3,], col = 'red', lty = 2, lwd = 1)

idx <- (TT-iii):(TT)

# Adding retrospective quantile estimation (blue)
result <- apply(xbs_retro[1,,], 1, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
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
result <- apply(xbs_retro[4,,], 1, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
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
result <- apply(xbs_retro[7,,], 1, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
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

# Adding current-rating discharge-reference levels (horizontal dashed lines) with labels
lev_flood <- c(14895.73, 11302.95, 7402.38, 4864.84) * CFSToCMS_CONVERSION_FACTOR
flood_labels <- c("Major reference", "Moderate reference", "Minor reference", "Action reference")
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


#### CELL 055 ####
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

png("/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics/Allth_ndlm_DISC.png", width = 6000, height = 4000, res = 600)
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
    result <- apply(xbs_ndlm_retro[1,,], 1, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
    lines(1:length(idx), result[1,idx] + sd_ndlm * qnorm(pp), col = 'orange', lty = 2, lwd = 0.5)
    lines(1:length(idx), result[2,idx] + sd_ndlm * qnorm(pp), col = 'darkorange', lwd = 0.5)
    lines(1:length(idx), result[3,idx] + sd_ndlm * qnorm(pp), col = 'orange', lty = 2, lwd = 0.5)
    result <- apply(xbs_ndlm[1,,] + sd_ndlm * qnorm(pp), 1, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
    lines(idx_f, result[1,], col = 'orange', lty = 2, lwd = 1)
    lines(idx_f, result[2,], col = 'orange', lwd = 1.5)
    lines(idx_f, result[3,], col = 'orange', lty = 2, lwd = 1)
}

lev_flood <- c(14895.73, 11302.95, 7402.38, 4864.84) * CFSToCMS_CONVERSION_FACTOR
flood_labels <- c("Major reference", "Moderate reference", "Minor reference", "Action reference")
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


#### CELL 056 ####
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

png("/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics/All3_ndlm_DISC.png", width = 6000, height = 4000, res = 600)
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
    result <- apply(xbs_ndlm_retro[1,,], 1, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
    lines(1:length(idx), result[1,idx] + sd_ndlm * qnorm(pp), col = 'orange', lty = 2, lwd = 0.5)
    lines(1:length(idx), result[2,idx] + sd_ndlm * qnorm(pp), col = 'darkorange', lwd = 0.5)
    lines(1:length(idx), result[3,idx] + sd_ndlm * qnorm(pp), col = 'orange', lty = 2, lwd = 0.5)
    result <- apply(xbs_ndlm[1,,] + sd_ndlm * qnorm(pp), 1, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
    lines(idx_f, result[1,], col = 'orange', lty = 2, lwd = 1)
    lines(idx_f, result[2,], col = 'orange', lwd = 1.5)
    lines(idx_f, result[3,], col = 'orange', lty = 2, lwd = 1)
}

lev_flood <- c(14895.73, 11302.95, 7402.38, 4864.84) * CFSToCMS_CONVERSION_FACTOR
flood_labels <- c("Major reference", "Moderate reference", "Minor reference", "Action reference")
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


#### CELL 057 ####
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

png("/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics/95th_exal_ndlm_DISC.png", width = 6000, height = 4000, res = 600)
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
result <- apply(xbs[7,,], 1, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
lines(idx_f, result[1,], col = 'blue', lty = 2, lwd = 1)
lines(idx_f, result[2,], col = 'darkblue', lwd = 1.5)
lines(idx_f, result[3,], col = 'blue', lty = 2, lwd = 1)

# Adding quantile bands (orange) for NDLM estimation
sd_ndlm <- mean(sqrt(samp.sigma_50_NDLM_synth_DISC[1,]))
result <- apply(xbs_ndlm[1,,] + sd_ndlm * qnorm(0.95), 1, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
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
result <- apply(xbs_retro[7,,], 1, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
lines(1:length(idx), result[1,idx], col = 'blue', lty = 2, lwd = 0.5)
lines(1:length(idx), result[2,idx], col = 'darkblue', lwd = 0.5)
lines(1:length(idx), result[3,idx], col = 'blue', lty = 2, lwd = 0.5)

# Adding retrospective NDLM estimation (orange)
result <- apply(xbs_ndlm_retro[1,,], 1, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
lines(1:length(idx), result[1,idx] + sd_ndlm * qnorm(0.95), col = 'orange', lty = 2, lwd = 0.5)
lines(1:length(idx), result[2,idx] + sd_ndlm * qnorm(0.95), col = 'darkorange', lwd = 0.5)
lines(1:length(idx), result[3,idx] + sd_ndlm * qnorm(0.95), col = 'orange', lty = 2, lwd = 0.5)

# Adding current-rating discharge-reference levels (horizontal dashed lines) with labels
lev_flood <- c(14895.73, 11302.95, 7402.38, 4864.84) * CFSToCMS_CONVERSION_FACTOR
flood_labels <- c("Major reference", "Moderate reference", "Minor reference", "Action reference")
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


#### CELL 058 ####
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
png("/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics/50th_exal_ndlm_DISC.png", width = 6000, height = 4000, res = 600)
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
result <- apply(xbs[4,,], 1, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
lines(idx_f, result[1,], col = 'green', lty = 2, lwd = 1)
lines(idx_f, result[2,], col = 'darkgreen', lwd = 1.5)
lines(idx_f, result[3,], col = 'green', lty = 2, lwd = 1)

# Adding quantile bands (orange) for NDLM estimation
sd_ndlm <- mean(sqrt(samp.sigma_50_NDLM_synth_DISC[1,]))
result <- apply(xbs_ndlm[1,,] + sd_ndlm * qnorm(0.5), 1, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
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
result <- apply(xbs_retro[4,,], 1, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
lines(1:length(idx), result[1,idx], col = 'green', lty = 2, lwd = 0.5)
lines(1:length(idx), result[2,idx], col = 'darkgreen', lwd = 0.5)
lines(1:length(idx), result[3,idx], col = 'green', lty = 2, lwd = 0.5)

# Adding retrospective NDLM estimation (orange)
result <- apply(xbs_ndlm_retro[1,,], 1, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
lines(1:length(idx), result[1,idx] + sd_ndlm * qnorm(0.5), col = 'orange', lty = 2, lwd = 0.5)
lines(1:length(idx), result[2,idx] + sd_ndlm * qnorm(0.5), col = 'darkorange', lwd = 0.5)
lines(1:length(idx), result[3,idx] + sd_ndlm * qnorm(0.5), col = 'orange', lty = 2, lwd = 0.5)

# Adding current-rating discharge-reference levels (horizontal dashed lines) with labels
lev_flood <- c(14895.73, 11302.95, 7402.38, 4864.84) * CFSToCMS_CONVERSION_FACTOR
flood_labels <- c("Major reference", "Moderate reference", "Minor reference", "Action reference")
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


#### CELL 059 ####
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
png("/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics/5th_exal_ndlm_DISC.png", width = 6000, height = 4000, res = 600)
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
result <- apply(xbs[1,,], 1, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
lines(idx_f, result[1,], col = 'red', lty = 2, lwd = 1)
lines(idx_f, result[2,], col = 'darkred', lwd = 1.5)
lines(idx_f, result[3,], col = 'red', lty = 2, lwd = 1)

# Adding quantile bands (orange) for NDLM estimation
sd_ndlm <- mean(sqrt(samp.sigma_50_NDLM_synth_DISC[1,]))
result <- apply(xbs_ndlm[1,,] + sd_ndlm * qnorm(0.05), 1, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
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
result <- apply(xbs_retro[1,,], 1, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
lines(1:length(idx), result[1,idx], col = 'red', lty = 2, lwd = 0.5)
lines(1:length(idx), result[2,idx], col = 'darkred', lwd = 0.5)
lines(1:length(idx), result[3,idx], col = 'red', lty = 2, lwd = 0.5)

# Adding retrospective NDLM estimation (orange)
result <- apply(xbs_ndlm_retro[1,,], 1, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
lines(1:length(idx), result[1,idx] + sd_ndlm * qnorm(0.05), col = 'orange', lty = 2, lwd = 0.5)
lines(1:length(idx), result[2,idx] + sd_ndlm * qnorm(0.05), col = 'darkorange', lwd = 0.5)
lines(1:length(idx), result[3,idx] + sd_ndlm * qnorm(0.05), col = 'orange', lty = 2, lwd = 0.5)

# Adding current-rating discharge-reference levels (horizontal dashed lines) with labels
lev_flood <- c(14895.73, 11302.95, 7402.38, 4864.84) * CFSToCMS_CONVERSION_FACTOR
flood_labels <- c("Major reference", "Moderate reference", "Minor reference", "Action reference")
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


#### CELL 060 ####
p <- 7


#### CELL 061 ####
# ### Break

png("/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics/All_conv_VB_DISC.png", width = 6000, height = 4000, res = 600)
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


#### CELL 062 ####
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


#### CELL 063 ####
prepare_quantile_data <- function(v_d) {
  v_d_transposed <- aperm(v_d, c(3, 1, 2))
  q_d_transposed <- apply(v_d_transposed, 2:3, function(x) quantile(x, probs = c(0.975, 0.5, 0.025)))
  q_d <- aperm(q_d_transposed, c(2, 3, 1))
  return(q_d)
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


#### CELL 064 ####
time_cuts <- which(timestamps %in% c("2012-08-01","2016-05-01","2016-09-15","2019-08-01") )


#### CELL 065 ####

png("/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics/All_exal_ndlm_2012-2016_DISC.png", width = 6000, height = 4000, res = 600)
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
result <- apply(xbs_retro[4,,], 1, function(x) quantile(x, probs = percentiles))
lines(idx, result[1,idx], ylim = c(0,6),col = 'green', lty = 2, lwd=0.5)
lines(idx, result[2,idx],col = 'darkgreen', lwd=0.5)
lines(idx, result[3,idx],col = 'green', lty = 2, lwd=0.5)
######################################################################################
######################################################################################
## 5th Quantile
########
result <- apply(xbs_retro[1,,], 1, function(x) quantile(x, probs = percentiles))
lines(idx, result[1,idx], ylim = c(0,6),col = 'red', lty = 2, lwd=0.5)
lines(idx, result[2,idx],col = 'darkred', lwd=0.5)
lines(idx, result[3,idx],col = 'red', lty = 2, lwd=0.5)
######################################################################################
######################################################################################
## 95th Quantile
########
result <- apply(xbs_retro[7,,], 1, function(x) quantile(x, probs = percentiles))
lines(idx, result[1,idx], ylim = c(0,6),col = 'blue', lty = 2, lwd=0.5)
lines(idx, result[2,idx],col = 'darkblue', lwd=0.5)
lines(idx, result[3,idx],col = 'blue', lty = 2, lwd=0.5)
######################################################################################
######################################################################################
## NDLM
########
result <- apply(xbs_ndlm_retro[1,,], 1, function(x) quantile(x, probs = percentiles))
lines(idx, result[1,idx], ylim = c(0,6),col = 'orange', lty = 2, lwd=0.5)
lines(idx, result[2,idx],col = 'darkorange', lwd=0.5)
lines(idx, result[3,idx],col = 'orange', lty = 2, lwd=0.5)



######################################################################################
## 80th Quantile
########
result <- apply(xbs_retro[6,,], 1, function(x) quantile(x, probs = percentiles))
lines(idx, result[1,idx], ylim = c(0,6),col = 'purple', lty = 2, lwd=0.5)
lines(idx, result[2,idx],col = 'purple', lwd=0.5)
lines(idx, result[3,idx],col = 'purple', lty = 2, lwd=0.5)
######################################################################################
######################################################################################
## 65th Quantile
########
result <- apply(xbs_retro[5,,], 1, function(x) quantile(x, probs = percentiles))
lines(idx, result[1,idx], ylim = c(0,6),col = 'purple', lty = 2, lwd=0.5)
lines(idx, result[2,idx],col = 'purple', lwd=0.5)
lines(idx, result[3,idx],col = 'purple', lty = 2, lwd=0.5)
######################################################################################
######################################################################################
## 35th Quantile
########
result <- apply(xbs_retro[3,,], 1, function(x) quantile(x, probs = percentiles))
lines(idx, result[1,idx], ylim = c(0,6),col = 'purple', lty = 2, lwd=0.5)
lines(idx, result[2,idx],col = 'purple', lwd=0.5)
lines(idx, result[3,idx],col = 'purple', lty = 2, lwd=0.5)
######################################################################################
######################################################################################
## 20th Quantile
########
result <- apply(xbs_retro[2,,], 1, function(x) quantile(x, probs = percentiles))
lines(idx, result[1,idx], ylim = c(0,6),col = 'purple', lty = 2, lwd=0.5)
lines(idx, result[2,idx],col = 'purple', lwd=0.5)
lines(idx, result[3,idx],col = 'purple', lty = 2, lwd=0.5)
######################################################################################

lev_flood <- c(14895.73, 11302.95, 7402.38, 4864.84) * CFSToCMS_CONVERSION_FACTOR
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


#### CELL 066 ####
png("/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics/All_exal_ndlm_2017-2019_DISC.png", width = 6000, height = 4000, res = 600)
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
result <- apply(xbs_retro[4,,], 1, function(x) quantile(x, probs = percentiles))
lines(idx, result[1,idx], ylim = c(0,6),col = 'green', lty = 2, lwd=0.5)
lines(idx, result[2,idx],col = 'darkgreen', lwd=0.5)
lines(idx, result[3,idx],col = 'green', lty = 2, lwd=0.5)
######################################################################################
######################################################################################
## 5th Quantile
########
result <- apply(xbs_retro[1,,], 1, function(x) quantile(x, probs = percentiles))
lines(idx, result[1,idx], ylim = c(0,6),col = 'red', lty = 2, lwd=0.5)
lines(idx, result[2,idx],col = 'darkred', lwd=0.5)
lines(idx, result[3,idx],col = 'red', lty = 2, lwd=0.5)
######################################################################################
######################################################################################
## 95th Quantile
########
result <- apply(xbs_retro[7,,], 1, function(x) quantile(x, probs = percentiles))
lines(idx, result[1,idx], ylim = c(0,6),col = 'blue', lty = 2, lwd=0.5)
lines(idx, result[2,idx],col = 'darkblue', lwd=0.5)
lines(idx, result[3,idx],col = 'blue', lty = 2, lwd=0.5)
######################################################################################
######################################################################################
## NDLM
########
result <- apply(xbs_ndlm_retro[1,,], 1, function(x) quantile(x, probs = percentiles))
lines(idx, result[1,idx], ylim = c(0,6),col = 'orange', lty = 2, lwd=0.5)
lines(idx, result[2,idx],col = 'darkorange', lwd=0.5)
lines(idx, result[3,idx],col = 'orange', lty = 2, lwd=0.5)



######################################################################################
## 80th Quantile
########
result <- apply(xbs_retro[6,,], 1, function(x) quantile(x, probs = percentiles))
lines(idx, result[1,idx], ylim = c(0,6),col = 'purple', lty = 2, lwd=0.5)
lines(idx, result[2,idx],col = 'purple', lwd=0.5)
lines(idx, result[3,idx],col = 'purple', lty = 2, lwd=0.5)
######################################################################################
######################################################################################
## 65th Quantile
########
result <- apply(xbs_retro[5,,], 1, function(x) quantile(x, probs = percentiles))
lines(idx, result[1,idx], ylim = c(0,6),col = 'purple', lty = 2, lwd=0.5)
lines(idx, result[2,idx],col = 'purple', lwd=0.5)
lines(idx, result[3,idx],col = 'purple', lty = 2, lwd=0.5)
######################################################################################
######################################################################################
## 35th Quantile
########
result <- apply(xbs_retro[3,,], 1, function(x) quantile(x, probs = percentiles))
lines(idx, result[1,idx], ylim = c(0,6),col = 'purple', lty = 2, lwd=0.5)
lines(idx, result[2,idx],col = 'purple', lwd=0.5)
lines(idx, result[3,idx],col = 'purple', lty = 2, lwd=0.5)
######################################################################################
######################################################################################
## 20th Quantile
########
result <- apply(xbs_retro[2,,], 1, function(x) quantile(x, probs = percentiles))
lines(idx, result[1,idx], ylim = c(0,6),col = 'purple', lty = 2, lwd=0.5)
lines(idx, result[2,idx],col = 'purple', lwd=0.5)
lines(idx, result[3,idx],col = 'purple', lty = 2, lwd=0.5)
######################################################################################

lev_flood <- c(14895.73, 11302.95, 7402.38, 4864.84) * CFSToCMS_CONVERSION_FACTOR
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


#### CELL 067 ####
png("/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics/All3_exal_ndlm_2012-2016_DISC.png", width = 6000, height = 4000, res = 600)
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
result <- apply(xbs_retro[4,,], 1, function(x) quantile(x, probs = percentiles))
lines(idx, result[1,idx], ylim = c(0,6),col = 'green', lty = 2, lwd=0.5)
lines(idx, result[2,idx],col = 'darkgreen', lwd=0.5)
lines(idx, result[3,idx],col = 'green', lty = 2, lwd=0.5)
######################################################################################
######################################################################################
## 5th Quantile
########
result <- apply(xbs_retro[1,,], 1, function(x) quantile(x, probs = percentiles))
lines(idx, result[1,idx], ylim = c(0,6),col = 'red', lty = 2, lwd=0.5)
lines(idx, result[2,idx],col = 'darkred', lwd=0.5)
lines(idx, result[3,idx],col = 'red', lty = 2, lwd=0.5)
######################################################################################
######################################################################################
## 95th Quantile
########
result <- apply(xbs_retro[7,,], 1, function(x) quantile(x, probs = percentiles))
lines(idx, result[1,idx], ylim = c(0,6),col = 'blue', lty = 2, lwd=0.5)
lines(idx, result[2,idx],col = 'darkblue', lwd=0.5)
lines(idx, result[3,idx],col = 'blue', lty = 2, lwd=0.5)
######################################################################################
######################################################################################
## NDLM
########
result <- apply(xbs_ndlm_retro[1,,], 1, function(x) quantile(x, probs = percentiles))
lines(idx, result[1,idx], ylim = c(0,6),col = 'orange', lty = 2, lwd=0.5)
lines(idx, result[2,idx],col = 'darkorange', lwd=0.5)
lines(idx, result[3,idx],col = 'orange', lty = 2, lwd=0.5)


lev_flood <- c(14895.73, 11302.95, 7402.38, 4864.84) * CFSToCMS_CONVERSION_FACTOR
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


#### CELL 068 ####

png("/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics/All3_exal_2012-2016_DISC.png", width = 6000, height = 4000, res = 600)
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
result <- apply(xbs_retro[4,,], 1, function(x) quantile(x, probs = percentiles))
lines(idx, result[1,idx], ylim = c(0,6),col = 'green', lty = 2, lwd=0.5)
lines(idx, result[2,idx],col = 'darkgreen', lwd=0.5)
lines(idx, result[3,idx],col = 'green', lty = 2, lwd=0.5)
######################################################################################
######################################################################################
## 5th Quantile
########
result <- apply(xbs_retro[1,,], 1, function(x) quantile(x, probs = percentiles))
lines(idx, result[1,idx], ylim = c(0,6),col = 'red', lty = 2, lwd=0.5)
lines(idx, result[2,idx],col = 'darkred', lwd=0.5)
lines(idx, result[3,idx],col = 'red', lty = 2, lwd=0.5)
######################################################################################
######################################################################################
## 95th Quantile
########
result <- apply(xbs_retro[7,,], 1, function(x) quantile(x, probs = percentiles))
lines(idx, result[1,idx], ylim = c(0,6),col = 'blue', lty = 2, lwd=0.5)
lines(idx, result[2,idx],col = 'darkblue', lwd=0.5)
lines(idx, result[3,idx],col = 'blue', lty = 2, lwd=0.5)
######################################################################################
######################################################################################


lev_flood <- c(14895.73, 11302.95, 7402.38, 4864.84) * CFSToCMS_CONVERSION_FACTOR
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


#### CELL 069 ####
png("/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics/All3_exal_ndlm_2017-2019_DISC.png", width = 6000, height = 4000, res = 600)
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
result <- apply(xbs_retro[4,,], 1, function(x) quantile(x, probs = percentiles))
lines(idx, result[1,idx], ylim = c(0,6),col = 'green', lty = 2, lwd=0.5)
lines(idx, result[2,idx],col = 'darkgreen', lwd=0.5)
lines(idx, result[3,idx],col = 'green', lty = 2, lwd=0.5)
######################################################################################
######################################################################################
## 5th Quantile
########
result <- apply(xbs_retro[1,,], 1, function(x) quantile(x, probs = percentiles))
lines(idx, result[1,idx], ylim = c(0,6),col = 'red', lty = 2, lwd=0.5)
lines(idx, result[2,idx],col = 'darkred', lwd=0.5)
lines(idx, result[3,idx],col = 'red', lty = 2, lwd=0.5)
######################################################################################
######################################################################################
## 95th Quantile
########
result <- apply(xbs_retro[7,,], 1, function(x) quantile(x, probs = percentiles))
lines(idx, result[1,idx], ylim = c(0,6),col = 'blue', lty = 2, lwd=0.5)
lines(idx, result[2,idx],col = 'darkblue', lwd=0.5)
lines(idx, result[3,idx],col = 'blue', lty = 2, lwd=0.5)
######################################################################################
######################################################################################
## NDLM
########
result <- apply(xbs_ndlm_retro[1,,], 1, function(x) quantile(x, probs = percentiles))
lines(idx, result[1,idx], ylim = c(0,6),col = 'orange', lty = 2, lwd=0.5)
lines(idx, result[2,idx],col = 'darkorange', lwd=0.5)
lines(idx, result[3,idx],col = 'orange', lty = 2, lwd=0.5)


lev_flood <- c(14895.73, 11302.95, 7402.38, 4864.84) * CFSToCMS_CONVERSION_FACTOR
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


#### CELL 070 ####
# png("/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics/All3_exal_ndlm_2017-2019_DISC.png", width = 6000, height = 4000, res = 600)
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
result <- apply(xbs_retro[4,,], 1, function(x) quantile(x, probs = percentiles))
lines(idx, result[1,idx], ylim = c(0,6),col = 'green', lty = 2, lwd=0.5)
lines(idx, result[2,idx],col = 'darkgreen', lwd=0.5)
lines(idx, result[3,idx],col = 'green', lty = 2, lwd=0.5)
######################################################################################
######################################################################################
## 5th Quantile
########
result <- apply(xbs_retro[1,,], 1, function(x) quantile(x, probs = percentiles))
lines(idx, result[1,idx], ylim = c(0,6),col = 'red', lty = 2, lwd=0.5)
lines(idx, result[2,idx],col = 'darkred', lwd=0.5)
lines(idx, result[3,idx],col = 'red', lty = 2, lwd=0.5)
######################################################################################
######################################################################################
## 95th Quantile
########
result <- apply(xbs_retro[7,,], 1, function(x) quantile(x, probs = percentiles))
lines(idx, result[1,idx], ylim = c(0,6),col = 'blue', lty = 2, lwd=0.5)
lines(idx, result[2,idx],col = 'darkblue', lwd=0.5)
lines(idx, result[3,idx],col = 'blue', lty = 2, lwd=0.5)
######################################################################################
######################################################################################
## NDLM
########
result <- apply(xbs_ndlm_retro[1,,], 1, function(x) quantile(x, probs = percentiles))
lines(idx, result[1,idx], ylim = c(0,6),col = 'orange', lty = 2, lwd=0.5)
lines(idx, result[2,idx],col = 'darkorange', lwd=0.5)
lines(idx, result[3,idx],col = 'orange', lty = 2, lwd=0.5)


lev_flood <- c(14895.73, 11302.95, 7402.38, 4864.84) * CFSToCMS_CONVERSION_FACTOR
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


#### CELL 071 ####
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


#### CELL 072 ####

png("/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics/All_exal_ndlm_2018-2021_DISC.png", width = 6000, height = 4000, res = 60)
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
result <- apply(xbs_retro[4,,], 1, function(x) quantile(x, probs = percentiles))
lines(idx, result[1,idx], ylim = c(0,6),col = 'green', lty = 2, lwd=0.5)
lines(idx, result[2,idx],col = 'darkgreen', lwd=0.5)
lines(idx, result[3,idx],col = 'green', lty = 2, lwd=0.5)
######################################################################################
######################################################################################
## 5th Quantile
########
result <- apply(xbs_retro[1,,], 1, function(x) quantile(x, probs = percentiles))
lines(idx, result[1,idx], ylim = c(0,6),col = 'red', lty = 2, lwd=0.5)
lines(idx, result[2,idx],col = 'darkred', lwd=0.5)
lines(idx, result[3,idx],col = 'red', lty = 2, lwd=0.5)
######################################################################################
######################################################################################
## 95th Quantile
########
result <- apply(xbs_retro[7,,], 1, function(x) quantile(x, probs = percentiles))
lines(idx, result[1,idx], ylim = c(0,6),col = 'blue', lty = 2, lwd=0.5)
lines(idx, result[2,idx],col = 'darkblue', lwd=0.5)
lines(idx, result[3,idx],col = 'blue', lty = 2, lwd=0.5)
######################################################################################
######################################################################################
## NDLM
########
result <- apply(xbs_ndlm_retro[1,,], 1, function(x) quantile(x, probs = percentiles))
lines(idx, result[1,idx], ylim = c(0,6),col = 'orange', lty = 2, lwd=0.5)
lines(idx, result[2,idx],col = 'darkorange', lwd=0.5)
lines(idx, result[3,idx],col = 'orange', lty = 2, lwd=0.5)

######################################################################################
## 80th Quantile
########
result <- apply(xbs_retro[6,,], 1, function(x) quantile(x, probs = percentiles))
lines(idx, result[1,idx], ylim = c(0,6),col = 'purple', lty = 2, lwd=0.5)
lines(idx, result[2,idx],col = 'purple', lwd=0.5)
lines(idx, result[3,idx],col = 'purple', lty = 2, lwd=0.5)
######################################################################################
######################################################################################
## 65th Quantile
########
result <- apply(xbs_retro[5,,], 1, function(x) quantile(x, probs = percentiles))
lines(idx, result[1,idx], ylim = c(0,6),col = 'purple', lty = 2, lwd=0.5)
lines(idx, result[2,idx],col = 'purple', lwd=0.5)
lines(idx, result[3,idx],col = 'purple', lty = 2, lwd=0.5)
######################################################################################
######################################################################################
## 35th Quantile
########
result <- apply(xbs_retro[3,,], 1, function(x) quantile(x, probs = percentiles))
lines(idx, result[1,idx], ylim = c(0,6),col = 'purple', lty = 2, lwd=0.5)
lines(idx, result[2,idx],col = 'purple', lwd=0.5)
lines(idx, result[3,idx],col = 'purple', lty = 2, lwd=0.5)
######################################################################################
######################################################################################
## 20th Quantile
########
result <- apply(xbs_retro[2,,], 1, function(x) quantile(x, probs = percentiles))
lines(idx, result[1,idx], ylim = c(0,6),col = 'purple', lty = 2, lwd=0.5)
lines(idx, result[2,idx],col = 'purple', lwd=0.5)
lines(idx, result[3,idx],col = 'purple', lty = 2, lwd=0.5)
######################################################################################

lev_flood <- c(14895.73, 11302.95, 7402.38, 4864.84) * CFSToCMS_CONVERSION_FACTOR
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


#### CELL 073 ####
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
figure_names <- paste0("/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics/Component_1991_2022_", 1:length(components), ".png")

for (i in 1:length(components)) {
  par(mar = c(4, 4, 2, 1) + 0.1)  
  plot_quantile_component(q_d_50, q_d_05, q_d_95, 
                        q_d_20, q_d_35, q_d_65, q_d_80,
                        Y, idx, 
                        components[i], num_ticks = 8,figure_names[i])
}

par(mfrow = c(1, 1), mar = c(5, 4, 4, 2) + 0.1, oma = c(0, 0, 0, 0))


#### CELL 074 ####
num_ticks <- 8
idx <- ceiling(TT/10):TT
figure_names <- paste0("/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics/Agg_disc_1991_2022_", 1:J, ".png")

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


#### CELL 075 ####
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

     png("/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics/Component_1991_2022_TRANSFER50_DISC.png", width = 6000, height = 4000, res = 600)
  
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

   png("/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics/Component_1991_2022_TRANSFER05_DISC.png", width = 6000, height = 4000, res = 600)
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

png("/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics/Component_1991_2022_TRANSFER95_DISC.png", width = 6000, height = 4000, res = 600)
  
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


#### CELL 076 ####
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

     png("/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics/Component_2012_2016_TRANSFER50_DISC.png", width = 6000, height = 4000, res = 600)
  
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

     png("/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics/Component_2012_2016_TRANSFER05_DISC.png", width = 6000, height = 4000, res = 600)
  
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

     png("/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics/Component_2012_2016_TRANSFER95_DISC.png", width = 6000, height = 4000, res = 600)
  
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


#### CELL 077 ####
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
figure_names <- paste0("/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics/Component_2012_2016_", 1:length(components), "_DISC.png")
for (i in 1:length(components)) {
  par(mar = c(4, 4, 2, 1) + 0.1)  
  plot_quantile_component(q_d_50, q_d_05, q_d_95, 
                        q_d_20, q_d_35, q_d_65, q_d_80,
                        Y, idx, 
                        components[i], num_ticks = 35,figure_names)
}

par(mfrow = c(1, 1), mar = c(5, 4, 4, 2) + 0.1, oma = c(0, 0, 0, 0))


#### CELL 078 ####
num_ticks <- 8
idx <- time_cuts[1]:time_cuts[2]
figure_names <- paste0("/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics/Agg_disc_2012_2016_", 1:J, ".png")

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


#### CELL 079 ####
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
figure_names <- paste0("/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics/Component_2018_2020_", 1:length(components), "_DISC.png")
for (i in 1:length(components)) {
  par(mar = c(4, 4, 2, 1) + 0.1)  
  plot_quantile_component(q_d_50, q_d_05, q_d_95, 
                        q_d_20, q_d_35, q_d_65, q_d_80,
                        Y, idx, 
                        components[i], num_ticks = 25,figure_names)
}

par(mfrow = c(1, 1), mar = c(5, 4, 4, 2) + 0.1, oma = c(0, 0, 0, 0))


#### CELL 080 ####
num_ticks <- 8
idx <- time_cuts[3]:time_cuts[4]
figure_names <- paste0("/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics/Agg_disc_2018_2020_", 1:J, ".png")

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


#### CELL 081 ####
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
     png("/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics/Component_2017_2019_TRANSFER50_DISC.png", width = 6000, height = 4000, res = 600)
  
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

     png("/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics/Component_22017_2019_TRANSFER05_DISC.png", width = 6000, height = 4000, res = 600)
  
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

     png("/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics/Component_2017_2019_TRANSFER95_DISC.png", width = 6000, height = 4000, res = 600)
  
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


#### CELL 082 ####
# Load necessary libraries
library(MASS)  # For multivariate normal distribution functions
library(ks)    # For kernel density estimation (KDE)

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

  # Create a matrix of all grid points where the densities are evaluated
  grid_matrix <- expand.grid(grid_points[[1]], grid_points[[2]], grid_points[[3]])

  # Calculate the density for the standard normal on the same grid
  pdf_q <- dmvnorm(as.matrix(grid_matrix), mean = mean_q, sigma = cov_q)
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
  js_divergence <- compute_jsd(sample_list[[i]], gridsize = c(100, 100, 100))
  cat("Jensen-Shannon divergence for", sample_names[i], "is", js_divergence, "\n\n")
  results[[sample_names[i]]] <- js_divergence
}

# Print final results
cat("Final JSD Results:\n")
print(results)


#### CELL 083 ####
matrix_df <- as.data.frame(X)
matrix_df <- cbind(Timestamp = timestamps, matrix_df)
write.csv(matrix_df, "factors.csv", row.names = FALSE)


#### CELL 084 ####

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
save_plot(filename = "/data/muscat_data/jaguir26/project1_ucsc_phd/tef_5_50_95_plot_DISC.png", plot = p1, width = 8, height = 6, dpi = 900)

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
save_plot(filename = "/data/muscat_data/jaguir26/project1_ucsc_phd/tef_20_plot_DISC.png", plot = p2, width = 8, height = 6, dpi = 900)


#### CELL 085 ####
dim(samp.theta_50_exAL_synth_DISC$samp_theta)
dim(samp.sts_50_exAL_synth_DISC)
dim(samp.gamma_50_exAL_synth_DISC)
dim(samp.sigma_50_exAL_synth_DISC)

inverse_cdf_AL <- function(U, mu, sigma, p) {
  ifelse(U < p, 
         mu + (sigma / (1 - p)) * log(U / p), 
         mu - (sigma / p) * log((1 - U) / (1 - p)))
}

L.fn<-function(p0){ stats::uniroot(function(gam) exp(log.g(gam))-(1-p0), c(-1000,0))$root }
U.fn<-function(p0){ stats::uniroot(function(gam) exp(log.g(gam))-p0, c(0,1000))$root }
p.fn<-function(p0,gam){ (p0-as.numeric(gam<0))/exp(log.g(gam))+as.numeric(gam<0)}
A.fn<-function(p0,gam){ temp.p = p.fn(p0,gam); return((1-2*temp.p)/(temp.p*(1-temp.p))) }
B.fn<-function(p0,gam){ temp.p = p.fn(p0,gam); return((2)/(temp.p*(1-temp.p))) }
C.fn<-function(p0,gam){ temp.p = p.fn(p0,gam); return((as.numeric(gam>0)-temp.p)^(-1)) }
#

# set.seed(777) 
# p0 <- 0.5
# j <- 1; 
# t <- 1; s <- 1;
# y_post <- matrix(NA_real_,nrow = dim(samp.theta_50_exAL_synth$samp_theta)[3], ncol = dim(samp.theta_50_exAL_synth$samp_theta)[2])
# for(t in 1:dim(samp.theta_50_exAL_synth$samp_theta)[2]){
#   for(s in 1:dim(samp.theta_50_exAL_synth$samp_theta)[3]){
#     y_post[s,t] <- 
#   } 
# }
# u <- runif(1)
# th_jt <- samp.theta_50_exAL_synth$samp_theta[,t,s]
# stj <- samp.sts_50_exAL_synth[j,t,s]
# gamj <- samp.gamma_50_exAL_synth[j,s]
# sigj <- samp.sigma_50_exAL_synth[j,s]
# p_exAL <- p.fn(p0, gamj)
# mu <- t(FF[,j,t])%*%(th_jt) + sigj*abs(gamj)*C.fn(p0, gamj)*stj
# inverse_cdf_AL(u, mu, sigj, p_exAL)


#### CELL 086 ####
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
p.fn <- function(p0, gam) {
  (p0 - as.numeric(gam < 0)) / exp(log.g(gam)) + as.numeric(gam < 0)
}

C.fn <- function(p0, gam) {
  temp.p <- p.fn(p0, gam)
  (as.numeric(gam > 0) - temp.p)^(-1)
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
  p_exAL <- p.fn(p0, gamj)

  # Reshape FF to align dimensions for matrix multiplication across time steps
  TT <- dim(samp_theta$samp_theta)[2]        # Number of time steps
  FF_reshaped <- array(FF[, j, ], dim = c(dim(samp_theta$samp_theta)[1], 1, TT))

  # Compute XB by applying the matrix multiplication for each time step `t`
  result_list <- lapply(1:TT, function(t) t(FF_reshaped[,,t]) %*% th[,t,])
  XB <- do.call(rbind, result_list)          # [time steps x samples]

  # Compute `mu` using the XB result and additional parameters
  mu <- XB + sigj * abs(gamj) * C.fn(p0, gamj) * stj

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


#### CELL 087 ####
exp_y_post_5 <- exp(y_post_5)
exp_y_post_20 <- exp(y_post_20)
exp_y_post_35 <- exp(y_post_35)
exp_y_post_50 <- exp(y_post_50)
exp_y_post_65 <- exp(y_post_65)
exp_y_post_80 <- exp(y_post_80)
exp_y_post_95 <- exp(y_post_95)


#### CELL 088 ####
idx <- (TT-500):(TT)
n.samp <- dim(samp.theta_50_exAL_synth_DISC$samp_theta)[3]
plot.ts(exp(Y[1,idx]), ylim = c(0,7))
for(s in 1:n.samp){
    lines(exp_y_post_50[s,idx], lwd = 0.1, col='forestgreen')
    lines(exp_y_post_95[s,idx], lwd = 0.1, col='darkblue')
    lines(exp_y_post_5[s,idx], lwd = 0.1, col='darkred')
} 
lines(exp(Y[1,idx]))


#### CELL 089 ####
q50 <- apply(y_post_50, 2, quantile, probs = c(0.5, 0.025, 0.5, 0.975))
m50 <- colMeans((y_post_50))
q5 <- apply(y_post_5, 2, quantile, probs = c(0.05, 0.025, 0.5, 0.975))
m5 <- colMeans((y_post_5))
q95 <- apply(y_post_95, 2, quantile, probs = c(0.95, 0.025, 0.5, 0.975))
m95 <- colMeans((y_post_95))
q20 <- apply(y_post_20, 2, quantile, probs = c(0.2, 0.025, 0.5, 0.975))
m20 <- colMeans((y_post_20))
q35 <- apply(y_post_35, 2, quantile, probs = c(0.35, 0.025, 0.5, 0.975))
m35 <- colMeans((y_post_35))
q65 <- apply(y_post_65, 2, quantile, probs = c(0.65, 0.025, 0.5, 0.975))
m65 <- colMeans((y_post_65))
q80 <- apply(y_post_80, 2, quantile, probs = c(0.8, 0.025, 0.5, 0.975))
m80 <- colMeans((y_post_80))

exp_q50 <- apply(exp_y_post_50, 2, quantile, probs = c(0.5, 0.025, 0.5, 0.975))
exp_m50 <- colMeans((exp_y_post_50))
exp_q5 <- apply(exp_y_post_5, 2, quantile, probs = c(0.05, 0.025, 0.5, 0.975))
exp_m5 <- colMeans((exp_y_post_5))
exp_q95 <- apply(exp_y_post_95, 2, quantile, probs = c(0.95, 0.025, 0.5, 0.975))
exp_m95 <- colMeans((exp_y_post_95))
exp_q20 <- apply(exp_y_post_20, 2, quantile, probs = c(0.2, 0.025, 0.5, 0.975))
exp_m20 <- colMeans((exp_y_post_20))
exp_q35 <- apply(exp_y_post_35, 2, quantile, probs = c(0.35, 0.025, 0.5, 0.975))
exp_m35 <- colMeans((exp_y_post_35))
exp_q65 <- apply(exp_y_post_65, 2, quantile, probs = c(0.65, 0.025, 0.5, 0.975))
exp_m65 <- colMeans((exp_y_post_65))
exp_q80 <- apply(exp_y_post_80, 2, quantile, probs = c(0.8, 0.025, 0.5, 0.975))
exp_m80 <- colMeans((exp_y_post_80))


#### CELL 090 ####
# Define the time range and common y-axis limits
idx <- (TT - 500):(TT)
n.samp <- dim(samp.theta_50_exAL_synth_DISC$samp_theta)[3]
ylim_range <- c(0, 7)
output_dir <- "/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics"

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


#### CELL 091 ####
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



#### CELL 092 ####
library(truncnorm)
set.seed(777)
############################################################################
# Function Definitions
inverse_cdf_AL <- function(U, mu, sigma, p) {
  ifelse(U < p, 
         mu + (sigma / (1 - p)) * log(U / p), 
         mu - (sigma / p) * log((1 - U) / (1 - p)))
}
############################################################################
p.fn <- function(p0, gam) {
  (p0 - as.numeric(gam < 0)) / exp(log.g(gam)) + as.numeric(gam < 0)
}
############################################################################
C.fn <- function(p0, gam) {
  temp.p <- p.fn(p0, gam)
  (as.numeric(gam > 0) - temp.p)^(-1)
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
    y_post[,t] <- xb_matrix[,t] + sigma_sample * abs(gamma_sample) * C.fn(p0, gamma_sample) * s_0 +  
                  sigma_sample * inverse_cdf_AL(u, 0, 1, p.fn(p0, gamma_sample))
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


#### CELL 093 ####
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


#### CELL 094 ####
library(matrixStats)
library(parallel)

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


#### CELL 095 ####
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


#### CELL 096 ####
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


#### CELL 097 ####
for (t in 1:ranges[1]) {
    synth_f[,t] <- sort(synth_f[,t])
    # synth_f2[,t] <- sort(synth_f2[,t])
}


#### CELL 098 ####
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
result <- apply(exp(xbs[7,,]), 1, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
lines(result[1,], col = 'blue', lty = 2, lwd = 1)
lines(result[2,], col = 'darkblue', lwd = 1.5)
lines(result[3,], col = 'blue', lty = 2, lwd = 1)

# Adding quantile bands (blue) for 95th Quantile estimation
result <- apply(exp(xbs[1,,]), 1, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
lines(result[1,], col = 'red', lty = 2, lwd = 1)
lines(result[2,], col = 'darkred', lwd = 1.5)
lines(result[3,], col = 'red', lty = 2, lwd = 1)

# Adding quantile bands (blue) for 95th Quantile estimation
result <- apply(exp(xbs[4,,]), 1, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
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


#### CELL 099 ####
# ### Break

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


#### CELL 100 ####

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



#### CELL 101 ####
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


#### CELL 102 ####
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
result <- apply(exp(xbs[7,,]), 1, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
lines(result[1,], col = 'blue', lty = 2, lwd = 1)
lines(result[2,], col = 'darkblue', lwd = 1.5)
lines(result[3,], col = 'blue', lty = 2, lwd = 1)

# Adding quantile bands (blue) for 95th Quantile estimation
result <- apply(exp(xbs[1,,]), 1, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
lines(result[1,], col = 'red', lty = 2, lwd = 1)
lines(result[2,], col = 'darkred', lwd = 1.5)
lines(result[3,], col = 'red', lty = 2, lwd = 1)

# Adding quantile bands (blue) for 95th Quantile estimation
result <- apply(exp(xbs[4,,]), 1, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
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

result <- apply(exp(y_reps_f_95), 2, function(x) quantile(x, probs = c(0.95)))
lines(result, col = 'black', lwd = 0.5)
result <- apply(exp(y_reps_f_80), 2, function(x) quantile(x, probs = c(0.80)))
lines(result, col = 'black', lwd = 0.5)
result <- apply(exp(y_reps_f_65), 2, function(x) quantile(x, probs = c(0.65)))
lines(result, col = 'black', lwd = 0.5)
result <- apply(exp(y_reps_f_50), 2, function(x) quantile(x, probs = c(0.50)))
lines(result, col = 'black', lwd = 0.5)
result <- apply(exp(y_reps_f_35), 2, function(x) quantile(x, probs = c(0.35)))
lines(result, col = 'black', lwd = 0.5)
result <- apply(exp(y_reps_f_20), 2, function(x) quantile(x, probs = c(0.20)))
lines(result, col = 'black', lwd = 0.5)
result <- apply(exp(y_reps_f_5), 2, function(x) quantile(x, probs = c(0.05)))
lines(result, col = 'black', lwd = 0.5)


n.samp
dim(y_reps_f)
dim(xbs)


#### CELL 103 ####
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


#### CELL 104 ####
y_reps <- readRDS("y_reps_new.rds")

q_s    <- c(0.05, 0.2, 0.35, 0.5, 0.65, 0.8, 0.95)
n.q     <- length(q_s)

synth <- synthesize_samples(exp(y_reps[,,]), q_s)
dim(synth)

synth_q <- colQuantiles(synth, probs = q_s, type = 8)
synth_q <- t(synth_q)
dim(synth_q)


#### CELL 105 ####
for (t in 1:length(idx_sub)) {
    synth[,t] <- sort(synth[,t])
}


#### CELL 106 ####
p <- 7


#### CELL 107 ####
p <- 7


#### CELL 108 ####
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


#### CELL 109 ####
# Load libraries (run if not already loaded)
library(ggplot2)
library(scales)
library(lubridate)


#### CELL 110 ####
# # USGS

flow_data <- data.frame(Date = timestamps, Flow = Y[1,])


#### CELL 111 ####

# Current-rating NWS stage-category discharge references in cfs
flood_stages_cfs <- c(14895.73, 7402.38)
# Convert to centimeters
flood_stages_cm <- flood_stages_cfs * CFSToCMS_CONVERSION_FACTOR
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
# Flood-reference labels for annotation
flood_stage_labels <- c("Major reference", "Minor reference")

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
  # Add current-rating discharge-reference horizontal lines
  geom_hline(
    yintercept = flood_stages_trans,
    linetype = c("dashed", "dashed"),
    color = c("gray", "gray"),
    linewidth = 0.8
  ) +
  # Label the discharge references at the rightmost end of the plot
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

save_plot(
  filename = "/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics/usgs.png",
  plot = p,
  width = 12,
  height = 6,
  units = "in",
  dpi = 900
)


# \caption{
# Daily log-log water flow (in cm$^3$/s) of the San Lorenzo River at the Big Trees USGS station from May 29, 1987 to December 25, 2022. The green curve shows the transformed daily flow. Vertical dashed lines and numbered labels mark key flood-related events: (1) February 1998 flood; (2) levee and floodwall reconstruction (2004); (3) February 2017 flood; (4) January 2023 flood. Horizontal dashed lines indicate current-rating discharge-reference levels for the river, with the upper line corresponding to the current-rating major reference and the lower line to the current-rating minor reference; both are displayed on the legacy transformed scale. See the main text for further discussion of each event and discharge-reference level.
# }


#### CELL 112 ####
# # EXO

series_colors <- c(
  "Precipitation" = "#1b9e77",    # green
  "Soil_Moisture" = "#386cb0",    # blue
  "Climate_PC1" = "#e6550d"       # orange
)


#### CELL 113 ####
df_covariates <- data.frame(
  Date = as.Date(timestamps),
  Precipitation = X[, 1],
  Soil_Moisture = X[, 2],
  GDPC1 = X[, 3]
)
# 1. Select only relevant columns and rename for plotting clarity
df_plot <- df_covariates
colnames(df_plot) <- c("Date", "Precipitation", "Soil_Moisture", "Climate_PC1")

# 2. Convert to long format for ggplot
df_long <- tidyr::pivot_longer(
  df_plot,
  cols = c("Precipitation", "Soil_Moisture", "Climate_PC1"),
  names_to = "Variable",
  values_to = "Value"
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

save_plot(
  filename = "/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics/precip_soilmoisture_climatePC1_faceted_labeled.png",
  plot = p_facets,
  width = 12,
  height = 8,
  units = "in",
  dpi = 900
)



#### CELL 114 ####
# # Retro

library(ggplot2)
library(patchwork)

df_retro <- data.frame(
  Date = as.Date(timestamps),
  GloFAS = Y[2,],
  NWS = Y[3,]
)

# Reshape to long format for ggplot
library(tidyr)
df_retro_long <- pivot_longer(
  df_retro,
  cols = c("GloFAS", "NWS"),
  names_to = "Source",
  values_to = "Value"
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

save_plot(
  filename = "/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics/retrospective_log_discharge_plot_faceted.png",
  plot = p_combined,
  width = 12,
  height = 8,
  units = "in",
  dpi = 900
)



#### CELL 115 ####
# # Forecast

library(ggplot2)
library(dplyr)
library(scales)
library(tidyr)

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


#### CELL 116 ####
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
    vjust = 4,,
    hjust = -0.1 
  ) +

  # USGS before
    # Add current-rating discharge-reference horizontal lines
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
    data = pivot_longer(
      data.frame(Date = glofas_dates, ensembles[[1]]),
      cols = -Date, names_to = "member", values_to = "value"
    ),
    aes(x = Date, y = value, group = member),
    color = glofas_color, alpha = 0.22, linewidth = 0.5, show.legend = FALSE
  ) +
  # NWS ensembles after
  geom_line(
    data = pivot_longer(
      data.frame(Date = nws_dates, ensembles[[2]]),
      cols = -Date, names_to = "member", values_to = "value"
    ),
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

save_plot(
  filename = "/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics/forecats.png",
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


#### CELL 117 ####
idx <- idx_sub


#### CELL 118 ####
library(tidyr)
library(dplyr)

# 1. Dates for fit and forecast
fit_dates <- as.Date(timestamps[idx])
forecast_dates <- seq(fit_dates[length(fit_dates)] + 1, by = "1 day", length.out = ranges[1])

# 2. Posterior samples, tidy for ggplot (long format)
df_post_fit <- as.data.frame(synth)
colnames(df_post_fit) <- as.character(fit_dates)
df_post_fit$sample <- 1:nrow(df_post_fit)
df_post_fit <- pivot_longer(df_post_fit, -sample, names_to = "Date", values_to = "Value") %>%
  mutate(Date = as.Date(Date), Type = "Fit")

df_post_forecast <- as.data.frame(synth_f)
colnames(df_post_forecast) <- as.character(forecast_dates)
df_post_forecast$sample <- 1:nrow(df_post_forecast)
df_post_forecast <- pivot_longer(df_post_forecast, -sample, names_to = "Date", values_to = "Value") %>%
  mutate(Date = as.Date(Date), Type = "Forecast")

df_post <- bind_rows(df_post_fit, df_post_forecast)

# 3. Quantile curves
df_q_fit <- as.data.frame(synth_q)
colnames(df_q_fit) <- as.character(fit_dates)
df_q_fit$quantile <- 1:nrow(df_q_fit)
df_q_fit <- pivot_longer(df_q_fit, -quantile, names_to = "Date", values_to = "Value") %>%
  mutate(Date = as.Date(Date), Type = "Fit")

df_q_forecast <- as.data.frame(synth_f_q)
colnames(df_q_forecast) <- as.character(forecast_dates)
df_q_forecast$quantile <- 1:nrow(df_q_forecast)
df_q_forecast <- pivot_longer(df_q_forecast, -quantile, names_to = "Date", values_to = "Value") %>%
  mutate(Date = as.Date(Date), Type = "Forecast")

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
  data = pivot_longer(
    data.frame(Date = glofas_dates, ensembles[[1]]),
    cols = -Date, names_to = "member", values_to = "value"
  ),
  aes(x = Date, y = value, group = member),
  color = "gray", alpha = 0.22, linewidth = 0.5, show.legend = FALSE
) +
# NWS ensembles after (gray)
geom_line(
  data = pivot_longer(
    data.frame(Date = nws_dates, ensembles[[2]]),
    cols = -Date, names_to = "member", values_to = "value"
  ),
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

save_plot(
  filename = "/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics/posterior_samples.png",
  plot = p_post,
  width = 12,
  height = 6,
  units = "in",
  dpi = 900
)


#### CELL 119 ####
# # Analysis 

library(dplyr)
library(tidyr)
library(ggplot2)

# -- 1. Prepare Data --
# Current-rating NWS stage-category discharge references in cfs
flood_stages_cfs <- c(14895.73, 7402.38)
# Convert to centimeters
flood_stages_cm <- flood_stages_cfs * CFSToCMS_CONVERSION_FACTOR
# Apply log(log(x + 1)) transformation
flood_stages_trans <- log(log(flood_stages_cm + 1))

idx <- time_cuts[3]:time_cuts[4]
dates <- as.Date(dates_ts_usgs[idx])         # Dates for plotting window
percentiles <- c(0.025, 0.5, 0.975)

# Helper: Extract quantile trajectory for a given quantile
get_quantile_trajectory <- function(arr, qidx, dates, idx, quantile_name) {
  mat <- arr[qidx, idx, , drop = FALSE]
  mat <- matrix(mat, nrow = length(idx), ncol = dim(arr)[3])
  qt_res <- t(apply(mat, 1, function(x) quantile(x, probs = percentiles)))
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
  Stage = flood_stage_labels
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
save_plot(
  filename = "/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics/All_exal_2017-2019_DISC.png",
  plot = p, width = 12, height = 6, units = "in", dpi = 900
)


#### CELL 120 ####
library(dplyr)
library(tidyr)
library(ggplot2)

# -- 1. Prepare Data --
# Current-rating NWS stage-category discharge references in cfs
flood_stages_cfs <- c(14895.73, 7402.38)
# Convert to centimeters
flood_stages_cm <- flood_stages_cfs * CFSToCMS_CONVERSION_FACTOR
# Apply log(log(x + 1)) transformation
flood_stages_trans <- log(log(flood_stages_cm + 1))

idx <- time_cuts[1]:time_cuts[2]
dates <- as.Date(dates_ts_usgs[idx])         # Dates for plotting window
percentiles <- c(0.025, 0.5, 0.975)

# Helper: Extract quantile trajectory for a given quantile
get_quantile_trajectory <- function(arr, qidx, dates, idx, quantile_name) {
  mat <- arr[qidx, idx, , drop = FALSE]
  mat <- matrix(mat, nrow = length(idx), ncol = dim(arr)[3])
  qt_res <- t(apply(mat, 1, function(x) quantile(x, probs = percentiles)))
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
  Stage = flood_stage_labels
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
save_plot(
  filename = "/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics/All_exal_2012-2016_DISC.png",
  plot = p, width = 12, height = 6, units = "in", dpi = 900
)


#### CELL 121 ####
library(dplyr)
library(tidyr)
library(ggplot2)

# -- 1. Prepare Data --
# Current-rating NWS stage-category discharge references in cfs
flood_stages_cfs <- c(14895.73, 7402.38)
# Convert to centimeters
flood_stages_cm <- flood_stages_cfs * CFSToCMS_CONVERSION_FACTOR
# Apply log(log(x + 1)) transformation
flood_stages_trans <- log(log(flood_stages_cm + 1))

idx <- time_cuts[1]:time_cuts[2]
dates <- as.Date(dates_ts_usgs[idx])         # Dates for plotting window
percentiles <- c(0.025, 0.5, 0.975)

# Helper: Extract quantile trajectory for a given quantile
get_quantile_trajectory <- function(arr, qidx, dates, idx, quantile_name) {
  mat <- arr[qidx, idx, , drop = FALSE]
  mat <- matrix(mat, nrow = length(idx), ncol = dim(arr)[3])
  qt_res <- t(apply(mat, 1, function(x) quantile(x, probs = percentiles)))
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
  Stage = flood_stage_labels
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
#   filename = "/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics/All_exal_2012-2016_DISC.png",
#   plot = p, width = 12, height = 6, units = "in", dpi = 900
# )


#### CELL 122 ####
library(ggplot2)
library(dplyr)
library(tidyr)

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


#### CELL 123 ####
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
    ff <- paste0("/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics/", filename)
    save_plot(ff, plot = p, width = 12, height = 6, units = "in", dpi = 350)
  }
}


#### CELL 124 ####
idx <- ceiling(TT/10):TT
obs_vec <- Y[1, idx]  
obs_df <- tibble(Date = as.Date(dates_ts_usgs[idx]), Value = obs_vec)


#### CELL 125 ####
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


#### CELL 126 ####
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
    ff <- paste0("/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics/",filename)
    save_plot(ff, plot = p, width = 12, height = 6, units = "in", dpi = 350)
  }
}


#### CELL 127 ####
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


#### CELL 128 ####
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


#### CELL 129 ####
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
save_plot("/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics/Agg_disc_1991_2022_1.png", p1, width = 12, height = 6, units = "in", dpi = 900)

# USGS-NWS (if J==2)
p2 <- make_discrepancy_plot(
  df2 %>% filter(Quantile %in% c("5th", "50th", "95th")),
  obs2,
  title = "Discrepancy USGS–NWS   1991–2022"
)
p2
save_plot("/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics/Agg_disc_1991_2022_2.png", p2, width = 12, height = 6, units = "in", dpi = 900)


#### CELL 130 ####
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
save_plot("/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics/Agg_disc_2012_2016_1.png", p1, width = 12, height = 6, units = "in", dpi = 900)

# USGS-NWS (if J==2)
p2 <- make_discrepancy_plot(
  df2 %>% filter(Quantile %in% c("5th", "50th", "95th")),
  obs2,
  title = "Discrepancy USGS–NWS   1991–2022",
  ylim = c(-2.5, 1)
)
p2
save_plot("/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics/Agg_disc_2012_2016_2.png", p2, width = 12, height = 6, units = "in", dpi = 900)


#### CELL 131 ####
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
save_plot("/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics/Agg_disc_2017_2019_1.png", p1, width = 12, height = 6, units = "in", dpi = 900)

# USGS-NWS (if J==2)
p2 <- make_discrepancy_plot(
  df2 %>% filter(Quantile %in% c("5th", "50th", "95th")),
  obs2,
  title = "Discrepancy USGS–NWS   1991–2022",
  ylim = c(-1.6, 0.8)
)
p2
save_plot("/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics/Agg_disc_2017_2019_2.png", p2, width = 12, height = 6, units = "in", dpi = 900)


#### CELL 132 ####
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


#### CELL 133 ####
# ### Effect Covariate effects

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


#### CELL 134 ####
# ## Valid Synthesys

library(isotone)

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
    
    # Step 4: Quantile function construction & Step 5: Initial synthesis
    q_init <- numeric(M)
    for (m in 1:M) {
      u <- u_grid_dense[m]
      
      # Find interval [τ_i, τ_{i+1}] containing u
      if (u <= percentiles[1]) {
        q_init[m] <- approx(pp, adjusted_samples[1, ], xout = u, rule = 2)$y
      } else if (u >= percentiles[n_p0]) {
        q_init[m] <- approx(pp, adjusted_samples[n_p0, ], xout = u, rule = 2)$y
      } else {
        i <- max(which(percentiles <= u))
        w <- (u - percentiles[i]) / (percentiles[i+1] - percentiles[i])
        q_i <- approx(pp, adjusted_samples[i, ], xout = u, rule = 2)$y
        q_i1 <- approx(pp, adjusted_samples[i+1, ], xout = u, rule = 2)$y
        q_init[m] <- (1 - w)*q_i + w*q_i1  # Linear blend
      }
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


#### CELL 135 ####
# Usage:
output_f <- synthesize_quantiles(y_reps_f, percentiles = c(0.05, 0.2, 0.35, 0.5, 0.65, 0.8, 0.95))


#### CELL 136 ####
q_estim_output_f <- apply(output_f, 2, function(x) quantile(x, probs = c(0.05, 0.2, 0.35, 0.5, 0.65, 0.8, 0.95) ) )
q_estim_synth_f <- apply(log(synth_f), 2, function(x) quantile(x, probs = c(0.05, 0.2, 0.35, 0.5, 0.65, 0.8, 0.95) ) )


#### CELL 137 ####
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


#### CELL 138 ####
# Usage:
output <- synthesize_quantiles(y_reps, percentiles = c(0.05, 0.2, 0.35, 0.5, 0.65, 0.8, 0.95))


#### CELL 139 ####
q_estim_output <- apply(output, 2, function(x) quantile(x, probs = c(0.05, 0.2, 0.35, 0.5, 0.65, 0.8, 0.95) ) )
q_estim_synth <- apply(log(synth), 2, function(x) quantile(x, probs = c(0.05, 0.2, 0.35, 0.5, 0.65, 0.8, 0.95) ) )


#### CELL 140 ####
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


#### CELL 141 ####
idx <- idx_sub

output_f_q <- colQuantiles(output_f, probs = q_s, type = 8)
output_f_q <- t(output_f_q)

output_q <- colQuantiles(output, probs = q_s, type = 8)
output_q <- t(output_q)


# 1. Dates for fit and forecast
fit_dates <- as.Date(timestamps[idx])
forecast_dates <- seq(fit_dates[length(fit_dates)] + 1, by = "1 day", length.out = ranges[1])

# 2. Posterior samples, tidy for ggplot (long format)
df_post_fit <- as.data.frame(output)
colnames(df_post_fit) <- as.character(fit_dates)
df_post_fit$sample <- 1:nrow(df_post_fit)
df_post_fit <- pivot_longer(df_post_fit, -sample, names_to = "Date", values_to = "Value") %>%
  mutate(Date = as.Date(Date), Type = "Fit")

df_post_forecast <- as.data.frame(output_f)
colnames(df_post_forecast) <- as.character(forecast_dates)
df_post_forecast$sample <- 1:nrow(df_post_forecast)
df_post_forecast <- pivot_longer(df_post_forecast, -sample, names_to = "Date", values_to = "Value") %>%
  mutate(Date = as.Date(Date), Type = "Forecast")

df_post <- bind_rows(df_post_fit, df_post_forecast)

# 3. Quantile curves
df_q_fit <- as.data.frame(output_q)
colnames(df_q_fit) <- as.character(fit_dates)
df_q_fit$quantile <- 1:nrow(df_q_fit)
df_q_fit <- pivot_longer(df_q_fit, -quantile, names_to = "Date", values_to = "Value") %>%
  mutate(Date = as.Date(Date), Type = "Fit")

df_q_forecast <- as.data.frame(output_f_q)
colnames(df_q_forecast) <- as.character(forecast_dates)
df_q_forecast$quantile <- 1:nrow(df_q_forecast)
df_q_forecast <- pivot_longer(df_q_forecast, -quantile, names_to = "Date", values_to = "Value") %>%
  mutate(Date = as.Date(Date), Type = "Forecast")

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
  data = pivot_longer(
    data.frame(Date = glofas_dates, ensembles[[1]]),
    cols = -Date, names_to = "member", values_to = "value"
  ),
  aes(x = Date, y = value, group = member),
  color = "gray", alpha = 0.22, linewidth = 0.5, show.legend = FALSE
) +
# NWS ensembles after (gray)
geom_line(
  data = pivot_longer(
    data.frame(Date = nws_dates, ensembles[[2]]),
    cols = -Date, names_to = "member", values_to = "value"
  ),
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

save_plot(
  filename = "/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics/posterior_samples_valid.png",
  plot = p_post,
  width = 12,
  height = 6,
  units = "in",
  dpi = 900
)


#### CELL 142 ####
# ## Univariate Aalyses (moved to end)
# ## START Univariate Aalyses

if (!SKIP_UNIVARIATE) {
  file_path <- "/data/muscat_data/jaguir26/project1_ucsc_phd/variables_5_exAL_synth_DISC_uni.RData"
  load(file_path)
}


#### CELL 143 ####
if (!SKIP_UNIVARIATE) {

  file_path <- "/data/muscat_data/jaguir26/project1_ucsc_phd/variables_50_exAL_synth_DISC_uni.RData"
  load(file_path)
}


#### CELL 144 ####
if (!SKIP_UNIVARIATE) {

  file_path <- "/data/muscat_data/jaguir26/project1_ucsc_phd/variables_95_exAL_synth_DISC_uni.RData"
  load(file_path)
}


#### CELL 145 ####
if (!SKIP_UNIVARIATE) {

  file_path <- "/data/muscat_data/jaguir26/project1_ucsc_phd/variables_20_exAL_synth_DISC_uni.RData"
  load(file_path)
}


#### CELL 146 ####
if (!SKIP_UNIVARIATE) {

  file_path <- "/data/muscat_data/jaguir26/project1_ucsc_phd/variables_35_exAL_synth_DISC_uni.RData"
  load(file_path)
}


#### CELL 147 ####
if (!SKIP_UNIVARIATE) {

  file_path <- "/data/muscat_data/jaguir26/project1_ucsc_phd/variables_65_exAL_synth_DISC_uni.RData"
  load(file_path)
}


#### CELL 148 ####
if (!SKIP_UNIVARIATE) {

  file_path <- "/data/muscat_data/jaguir26/project1_ucsc_phd/variables_80_exAL_synth_DISC_uni.RData"
  load(file_path)
}


#### CELL 149 ####
if (!SKIP_UNIVARIATE) {
  library(readr)
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
  time_series_matrix <- as.matrix(streamflow_data[, c('USGS')])
  timestamps <- as.Date(streamflow_data$Date)
  Y_usgs <- data.frame(time = timestamps, time_series_matrix)
  all_data <- merge(X, Y_usgs, by = "time")
  Y <- t(as.matrix(all_data[, c('USGS')]))
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
}


#### CELL 150 ####
if (!SKIP_UNIVARIATE) {
  n.samp <- 2000
}


#### CELL 151 ####
if (!SKIP_UNIVARIATE) {
  dim(new.theta.out_50_exAL_synth_DISC_uni$exps)
  TTT_temp <- dim(new.theta.out_50_exAL_synth_DISC_uni$exps)[2]
  TT
  diff <- TT-TTT_temp+1
  length(timestamps)
  diff <- 0
}


#### CELL 152 ####
if (!SKIP_UNIVARIATE) {
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
}


#### CELL 153 ####
if (!SKIP_UNIVARIATE) {
  plot(ppt_data$time,ppt_data$ppt, type = 'line')
  plot(principal_components_df$time,principal_components_df$Static_PCA, type = 'line')
}


#### CELL 154 ####
if (!SKIP_UNIVARIATE) {
  # Use the same covariates as the full model; do not overwrite X_f
  X_f_uni <- X_f
  covariates2 <- apply(X_f_uni, 2, standardize)
  for(i in 1:dim(covariates2)[2] ){
      covariates2[,i] <- covariates2[,i]-min(covariates2[,i])+1
  }
  covariates2 <- log(log(covariates2+1))
}


#### CELL 155 ####
if (!SKIP_UNIVARIATE) {
  # # plot.ts(c(X[(TT-100):(TT),1],X_f[,1]))
  # plot.ts(c(covariates[(TT-100):(TT),1],covariates2[,1]))
}


#### CELL 156 ####
if (!SKIP_UNIVARIATE) {
  a <- 30
  for(i in 1:8){
  plot.ts(c(X[(TT-a):TT,i],X_f[,i]))
  abline(v=a, col = 'darkred')
  }
}


#### CELL 157 ####
if (!SKIP_UNIVARIATE) {
  sm_T95 <- matrix(new.theta.out_95_exAL_synth_DISC_uni$sm[,TT], ncol = 1)
  sC_T95 <- new.theta.out_95_exAL_synth_DISC_uni$sC[,,TT]
  sm_T50 <- matrix(new.theta.out_50_exAL_synth_DISC_uni$sm[,TT], ncol = 1)
  sC_T50 <- new.theta.out_50_exAL_synth_DISC_uni$sC[,,TT]
  sm_T5 <- matrix(new.theta.out_5_exAL_synth_DISC_uni$sm[,TT], ncol = 1)
  sC_T5 <- new.theta.out_5_exAL_synth_DISC_uni$sC[,,TT]
  cbind(sm_T95[8:18],sm_T50[8:18],sm_T5[8:18])
}


#### CELL 158 ####
if (!SKIP_UNIVARIATE) {
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
}


#### CELL 159 ####
if (!SKIP_UNIVARIATE) {
  sm_T95 <- matrix(new.theta.out_95_exAL_synth_DISC_uni$sm[,TT], ncol = 1)
  sC_T95 <- new.theta.out_95_exAL_synth_DISC_uni$sC[,,TT]
  sm_T50 <- matrix(new.theta.out_50_exAL_synth_DISC_uni$sm[,TT], ncol = 1)
  sC_T50 <- new.theta.out_50_exAL_synth_DISC_uni$sC[,,TT]
  sm_T5 <- matrix(new.theta.out_5_exAL_synth_DISC_uni$sm[,TT], ncol = 1)
  sC_T5 <- new.theta.out_5_exAL_synth_DISC_uni$sC[,,TT]
  cbind(sm_T95[8:18],sm_T50[8:18],sm_T5[8:18])
}


#### CELL 160 ####
if (!SKIP_UNIVARIATE) {
  p <- 7
}


#### CELL 161 ####
if (!SKIP_UNIVARIATE) {
  if (!exists("model") || is.null(model$GG) || is.null(model$FF)) {
    stop("model$GG/FF not found; run the main model setup cells before the univariate block.")
  }
  GG <- model$GG
  FF <- model$FF
  lambda2 <- initial_delta_uni[5]

  Gx <- as.matrix(bdiag(GG[1:p,1:p,TT],lambda2, diag(px)))
  Gx <- array(rep(Gx, ranges[1]), dim = c(p+ppx, p+ppx, ranges[1]))
  Gx[(p+1), (p+2:ppx), ] <- as.matrix(t(X_f)) * 1
}


#### CELL 162 ####
if (!SKIP_UNIVARIATE) {
  c <- (1)^2
  ###############################################
  sm_T <- matrix(new.theta.out_95_exAL_synth_DISC_uni$sm[,TT], ncol = 1)
  sC_T <- new.theta.out_95_exAL_synth_DISC_uni$sC[,,TT]*c

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
  sm_T <- matrix(new.theta.out_50_exAL_synth_DISC_uni$sm[,TT], ncol = 1)
  sC_T <- new.theta.out_50_exAL_synth_DISC_uni$sC[,,TT]*c

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
  sm_T <- matrix(new.theta.out_5_exAL_synth_DISC_uni$sm[,TT], ncol = 1)
  sC_T <- new.theta.out_5_exAL_synth_DISC_uni$sC[,,TT]*c

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
}


#### CELL 163 ####
if (!SKIP_UNIVARIATE) {
  truth_log <- log(San_Lorenzo_Daily_USGS_R$data0[San_Lorenzo_Daily_USGS_R$Date >= as.Date('2022-12-26')][1:ranges[1]])
  plot.ts(truth_log, col = 'black', ylim = c(-1,4))
  points(truth_log, col = 'black')

  ###############################################
  sm_T <- samp.theta_95_exAL_synth_DISC_uni[,TT,]
  sC_T <- new.theta.out_95_exAL_synth_DISC_uni$sC[,,TT]*c

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
  sm_T <- samp.theta_50_exAL_synth_DISC_uni[,TT,]
  sC_T <- new.theta.out_50_exAL_synth_DISC_uni$sC[,,TT]*c

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
  sm_T <- samp.theta_5_exAL_synth_DISC_uni[,TT,]
  sC_T <- new.theta.out_5_exAL_synth_DISC_uni$sC[,,TT]*c

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
}


#### CELL 164 ####
if (!SKIP_UNIVARIATE) {
  # sm_{T+1} <- Gx_{T+1} %*% sm_T + N(0,W_{T+1}) 
  # y_{T+1}  <- F_{T+1} %*% sm_{T+1} + exAL_p0(V,0,gamma) 
  p <- 7
}


#### CELL 165 ####
if (!SKIP_UNIVARIATE) {
  xb_forecast <- array(NA_real_,c(7,n.samp,ranges[1]))
  y_forecast <- array(NA_real_,c(7,n.samp,ranges[1]))

  FF_f <- matrix(FF[1:(p+ppx),1,1], ncol = 1) 
  FF_f[p+1] <- 1 


  for(i in 1:n.samp){
      sm_k1 <- samp.theta_5_exAL_synth_DISC_uni[,TT,i]
      W <- Gx[,,1]%*%new.theta.out_5_exAL_synth_DISC_uni$sC[,,TT]%*%t(Gx[,,1])*c
      e <- rmvnorm(n = 1, sigma = W)
      sm_k1 <- Gx[,,1] %*% sm_k1 +t(e)
      xb_forecast[1,i,1] <- sum((FF_f)*sm_k1)
    
      sm_k2 <- samp.theta_20_exAL_synth_DISC_uni[,TT,i]
      W <- Gx[,,1]%*%new.theta.out_20_exAL_synth_DISC_uni$sC[,,TT]%*%t(Gx[,,1])*c
      e <- rmvnorm(n = 1, sigma = W)
      sm_k2 <- Gx[,,1] %*% sm_k2 +t(e)
      xb_forecast[2,i,1] <- sum((FF_f)*sm_k2)

      sm_k3 <- samp.theta_35_exAL_synth_DISC_uni[,TT,i]
      W <- Gx[,,1]%*%new.theta.out_35_exAL_synth_DISC_uni$sC[,,TT]%*%t(Gx[,,1])*c
      e <- rmvnorm(n = 1, sigma = W)
      sm_k3 <- Gx[,,1] %*% sm_k3 +t(e)
      xb_forecast[3,i,1] <- sum((FF_f)*sm_k3)
    
      sm_k4 <- samp.theta_50_exAL_synth_DISC_uni[,TT,i]
      W <- Gx[,,1]%*%new.theta.out_50_exAL_synth_DISC_uni$sC[,,TT]%*%t(Gx[,,1])*c
      e <- rmvnorm(n = 1, sigma = W)
      sm_k4 <- Gx[,,1] %*% sm_k4 +t(e)
      xb_forecast[4,i,1] <- sum((FF_f)*sm_k4)
    
      sm_k5 <- samp.theta_65_exAL_synth_DISC_uni[,TT,i]
      W <- Gx[,,1]%*%new.theta.out_65_exAL_synth_DISC_uni$sC[,,TT]%*%t(Gx[,,1])*c
      e <- rmvnorm(n = 1, sigma = W)
      sm_k5 <- Gx[,,1] %*% sm_k5 +t(e)
      xb_forecast[5,i,1] <- sum((FF_f)*sm_k5)
    
      sm_k6 <- samp.theta_80_exAL_synth_DISC_uni[,TT,i]
      W <- Gx[,,1]%*%new.theta.out_80_exAL_synth_DISC_uni$sC[,,TT]%*%t(Gx[,,1])*c
      e <- rmvnorm(n = 1, sigma = W)
      sm_k6 <- Gx[,,1] %*% sm_k6 +t(e)
      xb_forecast[6,i,1] <- sum((FF_f)*sm_k6)

      sm_k7 <- samp.theta_95_exAL_synth_DISC_uni[,TT,i]
      W <- Gx[,,1]%*%new.theta.out_95_exAL_synth_DISC_uni$sC[,,TT]%*%t(Gx[,,1])*c
      e <- rmvnorm(n = 1, sigma = W)
      sm_k7 <- Gx[,,1] %*% sm_k7 +t(e)
      xb_forecast[7,i,1] <- sum((FF_f)*sm_k7)
    
      gamma <- samp.gamma_95_exAL_synth_DISC_uni[1,i]
      sigma <- samp.sigma_95_exAL_synth_DISC_uni[1,i]
      p00 <- 0.95
      mu <- xb_forecast[7,i,1]
      y_forecast[7,i,1] <- rexal(1, p00, mu, sigma, gamma) 

      gamma <- samp.gamma_80_exAL_synth_DISC_uni[1,i]
      sigma <- samp.sigma_80_exAL_synth_DISC_uni[1,i]
      p00 <- 0.8
      mu <- xb_forecast[6,i,1]
      y_forecast[6,i,1] <- rexal(1, p00, mu, sigma, gamma) 

      gamma <- samp.gamma_65_exAL_synth_DISC_uni[1,i]
      sigma <- samp.sigma_65_exAL_synth_DISC_uni[1,i]
      p00 <- 0.65
      mu <- xb_forecast[5,i,1]
      y_forecast[5,i,1] <- rexal(1, p00, mu, sigma, gamma) 

      gamma <- samp.gamma_50_exAL_synth_DISC_uni[1,i]
      sigma <- samp.sigma_50_exAL_synth_DISC_uni[1,i]
      p00 <- 0.5
      mu <- xb_forecast[4,i,1]
      y_forecast[4,i,1] <- rexal(1, p00, mu, sigma, gamma) 

      gamma <- samp.gamma_35_exAL_synth_DISC_uni[1,i]
      sigma <- samp.sigma_35_exAL_synth_DISC_uni[1,i]
      p00 <- 0.35
      mu <- xb_forecast[3,i,1]
      y_forecast[3,i,1] <- rexal(1, p00, mu, sigma, gamma) 

      gamma <- samp.gamma_20_exAL_synth_DISC_uni[1,i]
      sigma <- samp.sigma_20_exAL_synth_DISC_uni[1,i]
      p00 <- 0.20
      mu <- xb_forecast[2,i,1]
      y_forecast[2,i,1] <- rexal(1, p00, mu, sigma, gamma) 

      gamma <- samp.gamma_5_exAL_synth_DISC_uni[1,i]
      sigma <- samp.sigma_5_exAL_synth_DISC_uni[1,i]
      p00 <- 0.05
      mu <- xb_forecast[1,i,1]
      y_forecast[1,i,1] <- rexal(1, p00, mu, sigma, gamma) 
        
      for(k in 2:ranges[1]){
          W <- Gx[,,k]%*%new.theta.out_5_exAL_synth_DISC_uni$sC[,,TT]%*%t(Gx[,,k])
          e <- rmvnorm(n = 1, sigma = W)
          sm_k1 <- Gx[,,k] %*% sm_k1 +t(e)
          xb_forecast[1,i,k] <- sum((FF_f)*sm_k1)

          W <- Gx[,,k]%*%new.theta.out_20_exAL_synth_DISC_uni$sC[,,TT]%*%t(Gx[,,k])
          e <- rmvnorm(n = 1, sigma = W)
          sm_k2 <- Gx[,,k] %*% sm_k2 +t(e)
          xb_forecast[2,i,k] <- sum((FF_f)*sm_k2)

          W <- Gx[,,k]%*%new.theta.out_35_exAL_synth_DISC_uni$sC[,,TT]%*%t(Gx[,,k])
          e <- rmvnorm(n = 1, sigma = W)
          sm_k3 <- Gx[,,k] %*% sm_k3 +t(e)
          xb_forecast[3,i,k] <- sum((FF_f)*sm_k3)

          W <- Gx[,,k]%*%new.theta.out_50_exAL_synth_DISC_uni$sC[,,TT]%*%t(Gx[,,k])
          e <- rmvnorm(n = 1, sigma = W)
          sm_k4 <- Gx[,,k] %*% sm_k4 +t(e)
          xb_forecast[4,i,k] <- sum((FF_f)*sm_k4)

          W <- Gx[,,k]%*%new.theta.out_65_exAL_synth_DISC_uni$sC[,,TT]%*%t(Gx[,,k])
          e <- rmvnorm(n = 1, sigma = W)
          sm_k5 <- Gx[,,k] %*% sm_k5 +t(e)
          xb_forecast[5,i,k] <- sum((FF_f)*sm_k5)

          W <- Gx[,,k]%*%new.theta.out_80_exAL_synth_DISC_uni$sC[,,TT]%*%t(Gx[,,k])
          e <- rmvnorm(n = 1, sigma = W)
          sm_k6 <- Gx[,,k] %*% sm_k6 +t(e)
          xb_forecast[6,i,k] <- sum((FF_f)*sm_k6)
        
          W <- Gx[,,k]%*%new.theta.out_95_exAL_synth_DISC_uni$sC[,,TT]%*%t(Gx[,,k])
          e <- rmvnorm(n = 1, sigma = W)
          sm_k7 <- Gx[,,k] %*% sm_k7 +t(e)
          xb_forecast[7,i,k] <- sum((FF_f)*sm_k7)

          gamma <- samp.gamma_95_exAL_synth_DISC_uni[1,i]
          sigma <- samp.sigma_95_exAL_synth_DISC_uni[1,i]
          p00 <- 0.95
          mu <- xb_forecast[7,i,k]
          y_forecast[7,i,k] <- rexal(1, p00, mu, sigma, gamma) 

          gamma <- samp.gamma_80_exAL_synth_DISC_uni[1,i]
          sigma <- samp.sigma_80_exAL_synth_DISC_uni[1,i]
          p00 <- 0.8
          mu <- xb_forecast[6,i,k]
          y_forecast[6,i,k] <- rexal(1, p00, mu, sigma, gamma) 

          gamma <- samp.gamma_65_exAL_synth_DISC_uni[1,i]
          sigma <- samp.sigma_65_exAL_synth_DISC_uni[1,i]
          p00 <- 0.65
          mu <- xb_forecast[5,i,k]
          y_forecast[5,i,k] <- rexal(1, p00, mu, sigma, gamma) 

          gamma <- samp.gamma_50_exAL_synth_DISC_uni[1,i]
          sigma <- samp.sigma_50_exAL_synth_DISC_uni[1,i]
          p00 <- 0.5
          mu <- xb_forecast[4,i,k]
          y_forecast[4,i,k] <- rexal(1, p00, mu, sigma, gamma) 

          gamma <- samp.gamma_35_exAL_synth_DISC_uni[1,i]
          sigma <- samp.sigma_35_exAL_synth_DISC_uni[1,i]
          p00 <- 0.35
          mu <- xb_forecast[3,i,k]
          y_forecast[3,i,k] <- rexal(1, p00, mu, sigma, gamma) 

          gamma <- samp.gamma_20_exAL_synth_DISC_uni[1,i]
          sigma <- samp.sigma_20_exAL_synth_DISC_uni[1,i]
          p00 <- 0.20
          mu <- xb_forecast[2,i,k]
          y_forecast[2,i,k] <- rexal(1, p00, mu, sigma, gamma) 

          gamma <- samp.gamma_5_exAL_synth_DISC_uni[1,i]
          sigma <- samp.sigma_5_exAL_synth_DISC_uni[1,i]
          p00 <- 0.05
          mu <- xb_forecast[1,i,k]
          y_forecast[1,i,k] <- rexal(1, p00, mu, sigma, gamma) 


      }
  }
}


#### CELL 166 ####
if (!SKIP_UNIVARIATE) {
  days_hist_uni <- 19
  xb_hist_uni <- array(NA_real_,c(7,n.samp,days_hist_uni))
  y_hist_uni <- array(NA_real_,c(7,n.samp,days_hist_uni))
  FF_hist_uni <- matrix(FF[1:(p+ppx),1,1], ncol = 1) 
  FF_hist_uni[p+1] <- 1 

  for(i in 1:n.samp){
      for(t in (TT-days_hist_uni+1):TT){
          tt <- ( t -(TT-days_hist_uni+1) + 1 )
          xb_hist_uni[7,i,tt] <- sum((FF_hist_uni)*samp.theta_95_exAL_synth_DISC_uni[,t,i])
          gamma <- samp.gamma_95_exAL_synth_DISC_uni[1,i]
          sigma <- samp.sigma_95_exAL_synth_DISC_uni[1,i]
          p00 <- 0.95
          mu  <- xb_hist_uni[7,i,tt]
          y_hist_uni[7,i,tt] <- rexal(1, p00, mu, sigma, gamma)

          xb_hist_uni[6,i,tt] <- sum((FF_hist_uni)*samp.theta_80_exAL_synth_DISC_uni[,t,i])
          gamma <- samp.gamma_80_exAL_synth_DISC_uni[1,i]
          sigma <- samp.sigma_80_exAL_synth_DISC_uni[1,i]
          p00 <- 0.80
          mu  <- xb_hist_uni[6,i,tt]
          y_hist_uni[6,i,tt] <- rexal(1, p00, mu, sigma, gamma)

          xb_hist_uni[5,i,tt] <- sum((FF_hist_uni)*samp.theta_65_exAL_synth_DISC_uni[,t,i])
          gamma <- samp.gamma_65_exAL_synth_DISC_uni[1,i]
          sigma <- samp.sigma_65_exAL_synth_DISC_uni[1,i]
          p00 <- 0.65
          mu  <- xb_hist_uni[5,i,tt]
          y_hist_uni[5,i,tt] <- rexal(1, p00, mu, sigma, gamma)

          xb_hist_uni[4,i,tt] <- sum((FF_hist_uni)*samp.theta_50_exAL_synth_DISC_uni[,t,i])
          gamma <- samp.gamma_50_exAL_synth_DISC_uni[1,i]
          sigma <- samp.sigma_50_exAL_synth_DISC_uni[1,i]
          p00 <- 0.50
          mu  <- xb_hist_uni[4,i,tt]
          y_hist_uni[4,i,tt] <- rexal(1, p00, mu, sigma, gamma)

          xb_hist_uni[3,i,tt] <- sum((FF_hist_uni)*samp.theta_35_exAL_synth_DISC_uni[,t,i])
          gamma <- samp.gamma_35_exAL_synth_DISC_uni[1,i]
          sigma <- samp.sigma_35_exAL_synth_DISC_uni[1,i]
          p00 <- 0.35
          mu  <- xb_hist_uni[3,i,tt]
          y_hist_uni[3,i,tt] <- rexal(1, p00, mu, sigma, gamma)

          xb_hist_uni[2,i,tt] <- sum((FF_hist_uni)*samp.theta_20_exAL_synth_DISC_uni[,t,i])
          gamma <- samp.gamma_20_exAL_synth_DISC_uni[1,i]
          sigma <- samp.sigma_20_exAL_synth_DISC_uni[1,i]
          p00 <- 0.20
          mu  <- xb_hist_uni[2,i,tt]
          y_hist_uni[2,i,tt] <- rexal(1, p00, mu, sigma, gamma)

          xb_hist_uni[1,i,tt] <- sum((FF_hist_uni)*samp.theta_5_exAL_synth_DISC_uni[,t,i])
          gamma <- samp.gamma_5_exAL_synth_DISC_uni[1,i]
          sigma <- samp.sigma_5_exAL_synth_DISC_uni[1,i]
          p00 <- 0.05
          mu  <- xb_hist_uni[1,i,tt]
          y_hist_uni[1,i,tt] <- rexal(1, p00, mu, sigma, gamma)
      }   
  }
}


#### CELL 167 ####
if (!SKIP_UNIVARIATE) {
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

  # Save the array to your current directory
  saveRDS(y_hist_uni, file = "y_hist_uni.rds")

  y_reps_hist_uni <- readRDS("y_hist_uni.rds")

  q_s    <- c(0.05, 0.2, 0.35, 0.5, 0.65, 0.8, 0.95)
  n.q     <- length(q_s)
  n.samp  <- n.samp
  n.times <- ranges[1]

  synth_hist_uni <- synthesize_samples(exp(y_reps_hist_uni), q_s)
  dim(synth_hist_uni)

  synth_hist_uni_q <- colQuantiles(synth_hist_uni, probs = q_s, type = 8)
  synth_hist_uni_q <- t(synth_hist_uni_q)
  dim(synth_hist_uni_q)

  for (t in 1:days_hist_uni) {
      synth_hist_uni[,t] <- sort(synth_hist_uni[,t])
  }
}


#### CELL 168 ####
if (!SKIP_UNIVARIATE) {
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

  # Save the array to your current directory
  saveRDS(y_forecast, file = "y_forecast_uni.rds")

  y_reps_uni <- readRDS("y_forecast_uni.rds")

  q_s    <- c(0.05, 0.2, 0.35, 0.5, 0.65, 0.8, 0.95)
  n.q     <- length(q_s)
  n.samp  <- n.samp
  n.times <- ranges[1]

  synth_f2 <- synthesize_samples(exp(y_reps_uni), q_s)
  dim(synth_f2)

  synth_f2_q <- colQuantiles(synth_f2, probs = q_s, type = 8)
  synth_f2_q <- t(synth_f2_q)
  dim(synth_f2_q)

  for (t in 1:ranges[1]) {
      synth_f2[,t] <- sort(synth_f2[,t])
  }
}


#### CELL 169 ####
if (!SKIP_UNIVARIATE) {
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
  result <- apply(exp(xb_forecast[7,,]), 2, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
  lines(result[1,], col = 'blue', lty = 2, lwd = 1)
  lines(result[2,], col = 'darkblue', lwd = 1.5)
  lines(result[3,], col = 'blue', lty = 2, lwd = 1)

  # Adding quantile bands (blue) for 95th Quantile estimation
  result <- apply(exp(xb_forecast[1,,]), 2, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
  lines(result[1,], col = 'red', lty = 2, lwd = 1)
  lines(result[2,], col = 'darkred', lwd = 1.5)
  lines(result[3,], col = 'red', lty = 2, lwd = 1)

  # Adding quantile bands (blue) for 95th Quantile estimation
  result <- apply(exp(xb_forecast[4,,]), 2, function(x) quantile(x, probs = c(0.025, 0.5, 0.975)))
  lines(result[1,], col = 'green', lty = 2, lwd = 1)
  lines(result[2,], col = 'forestgreen', lwd = 1.5)
  lines(result[3,], col = 'green', lty = 2, lwd = 1)


  result <- apply(exp(y_reps_f_95), 2, function(x) quantile(x, probs = c(0.95)))
  lines(result, col = 'black', lwd = 0.5)
  result <- apply(exp(y_reps_f_80), 2, function(x) quantile(x, probs = c(0.80)))
  lines(result, col = 'black', lwd = 0.5)
  result <- apply(exp(y_reps_f_65), 2, function(x) quantile(x, probs = c(0.65)))
  lines(result, col = 'black', lwd = 0.5)
  result <- apply(exp(y_reps_f_50), 2, function(x) quantile(x, probs = c(0.50)))
  lines(result, col = 'black', lwd = 0.5)
  result <- apply(exp(y_reps_f_35), 2, function(x) quantile(x, probs = c(0.35)))
  lines(result, col = 'black', lwd = 0.5)
  result <- apply(exp(y_reps_f_20), 2, function(x) quantile(x, probs = c(0.20)))
  lines(result, col = 'black', lwd = 0.5)
  result <- apply(exp(y_reps_f_5), 2, function(x) quantile(x, probs = c(0.05)))
  lines(result, col = 'black', lwd = 0.5)

  points(SL$data0, lwd = 0.8, pch = 16)
}


#### CELL 170 ####
if (!SKIP_UNIVARIATE) {
  dim(synth_hist_uni)
  dim(synth_hist_uni_q)
  dim(synth_f2_q)
  dim(synth_f2)
}


#### CELL 171 ####
# ## END Univariate Aalyses

if (!SKIP_UNIVARIATE) {
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
}


#### CELL 172 ####
if (!SKIP_UNIVARIATE) {
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
}


#### CELL 173 ####
if (!SKIP_UNIVARIATE) {
  library(tidyr)
  library(dplyr)

  # Dates for fit (historical) and forecast
  fit_dates <- as.Date(timestamps[idx])
  forecast_dates <- seq(fit_dates[length(fit_dates)] + 1, by = "1 day", length.out = ranges[1])

  # 1. Posterior samples: historical (fit) and forecast
  df_post_fit <- as.data.frame(log(synth_hist_uni))
  colnames(df_post_fit) <- as.character(fit_dates)
  df_post_fit$sample <- 1:nrow(df_post_fit)
  df_post_fit <- pivot_longer(df_post_fit, -sample, names_to = "Date", values_to = "Value") %>%
    mutate(Date = as.Date(Date), Type = "Fit")

  df_post_forecast <- as.data.frame(log(synth_f2))
  colnames(df_post_forecast) <- as.character(forecast_dates)
  df_post_forecast$sample <- 1:nrow(df_post_forecast)
  df_post_forecast <- pivot_longer(df_post_forecast, -sample, names_to = "Date", values_to = "Value") %>%
    mutate(Date = as.Date(Date), Type = "Forecast")

  df_post <- bind_rows(df_post_fit, df_post_forecast)

  # 2. Quantile curves: historical (fit) and forecast
  df_q_fit <- as.data.frame(log(synth_hist_uni_q))
  colnames(df_q_fit) <- as.character(fit_dates)
  df_q_fit$quantile <- 1:nrow(df_q_fit)
  df_q_fit <- pivot_longer(df_q_fit, -quantile, names_to = "Date", values_to = "Value") %>%
    mutate(Date = as.Date(Date), Type = "Fit")

  df_q_forecast <- as.data.frame(log(synth_f2_q))
  colnames(df_q_forecast) <- as.character(forecast_dates)
  df_q_forecast$quantile <- 1:nrow(df_q_forecast)
  df_q_forecast <- pivot_longer(df_q_forecast, -quantile, names_to = "Date", values_to = "Value") %>%
    mutate(Date = as.Date(Date), Type = "Forecast")

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

  save_plot(
    filename = "/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics/posterior_samples_counter.png",
    plot = p_post,
    width = 12,
    height = 6,
    units = "in",
    dpi = 900
  )
}


#### CELL 174 ####
if (!SKIP_UNIVARIATE) {
  names(new.theta.out_50_exAL_synth_DISC_uni)
}


#### CELL 175 ####
if (!SKIP_UNIVARIATE) {
  output_uni_f <- synthesize_quantiles(y_reps_uni, percentiles = c(0.05, 0.2, 0.35, 0.5, 0.65, 0.8, 0.95))
  output_uni <- synthesize_quantiles(y_reps_hist_uni, percentiles = c(0.05, 0.2, 0.35, 0.5, 0.65, 0.8, 0.95))
}


#### CELL 176 ####
if (!SKIP_UNIVARIATE) {
  idx <- idx_sub

  output_f_q <- colQuantiles(output_uni_f, probs = q_s, type = 8)
  output_f_q <- t(output_f_q)

  output_q <- colQuantiles(output_uni, probs = q_s, type = 8)
  output_q <- t(output_q)

  # Dates for fit (historical) and forecast
  fit_dates <- as.Date(timestamps[idx])
  forecast_dates <- seq(fit_dates[length(fit_dates)] + 1, by = "1 day", length.out = ranges[1])

  # 1. Posterior samples: historical (fit) and forecast
  df_post_fit <- as.data.frame(log(synth_hist_uni))
  colnames(df_post_fit) <- as.character(fit_dates)
  df_post_fit$sample <- 1:nrow(df_post_fit)
  df_post_fit <- pivot_longer(df_post_fit, -sample, names_to = "Date", values_to = "Value") %>%
    mutate(Date = as.Date(Date), Type = "Fit")

  df_post_forecast <- as.data.frame(log(synth_f2))
  colnames(df_post_forecast) <- as.character(forecast_dates)
  df_post_forecast$sample <- 1:nrow(df_post_forecast)
  df_post_forecast <- pivot_longer(df_post_forecast, -sample, names_to = "Date", values_to = "Value") %>%
    mutate(Date = as.Date(Date), Type = "Forecast")

  df_post <- bind_rows(df_post_fit, df_post_forecast)

  # 2. Quantile curves: historical (fit) and forecast
  df_q_fit <- as.data.frame(log(synth_hist_uni_q))
  colnames(df_q_fit) <- as.character(fit_dates)
  df_q_fit$quantile <- 1:nrow(df_q_fit)
  df_q_fit <- pivot_longer(df_q_fit, -quantile, names_to = "Date", values_to = "Value") %>%
    mutate(Date = as.Date(Date), Type = "Fit")

  df_q_forecast <- as.data.frame(log(synth_f2_q))
  colnames(df_q_forecast) <- as.character(forecast_dates)
  df_q_forecast$quantile <- 1:nrow(df_q_forecast)
  df_q_forecast <- pivot_longer(df_q_forecast, -quantile, names_to = "Date", values_to = "Value") %>%
    mutate(Date = as.Date(Date), Type = "Forecast")

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

  save_plot(
    filename = "/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics/posterior_samples_counter_valid.png",
    plot = p_post,
    width = 12,
    height = 6,
    units = "in",
    dpi = 900
  )
}


