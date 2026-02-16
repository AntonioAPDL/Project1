#!/usr/bin/env Rscript
.libPaths(c("~/R/libs", .libPaths()))
print(.libPaths())
library(dplyr)

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

DISC_DEBUG <- FALSE
source("R/disc_w/_init.R")

n.samp <- 2000
print(c(n.samp))
flush.console()
cut <- 1
m <- 2
USE_PREV <- TRUE   
disc_use_prev_env <- Sys.getenv("DISC_USE_PREV", "")
if (nzchar(disc_use_prev_env)) {
  USE_PREV <- tolower(disc_use_prev_env) %in% c("1", "true", "yes", "y")
}

args <- commandArgs(trailingOnly = TRUE)
p0 <- as.numeric(args[1])
harmonics = c(1, 2, 1/6.8068493)   
# harmonics = c(363.5854/90, 363.5854/180, 1/6.8068493)     

Sys.setenv("PKG_CXXFLAGS"="-I/data/muscat_data/jaguir26/libs/eigen -I/data/muscat_data/jaguir26/libs/boost/include -DEIGEN_DONT_VECTORIZE")
Sys.setenv("PKG_LIBS"="-L/data/muscat_data/jaguir26/libs/lib64 -L/data/muscat_data/jaguir26/libs/boost/lib -llapack -lblas -lboost_random -lboost_system -fopenmp")
Sys.setenv(LD_LIBRARY_PATH="/data/muscat_data/jaguir26/libs/lib64:/data/muscat_data/jaguir26/libs/boost/lib:/lib64")

Rcpp::sourceCpp("/data/muscat_data/jaguir26/project1_ucsc_phd/sampling_exal.cpp")
Rcpp::sourceCpp("/data/muscat_data/jaguir26/project1_ucsc_phd/sampling_truncnorm.cpp")
Rcpp::sourceCpp("/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_kalman_synth.cpp")

disc_base_seed <- suppressWarnings(as.numeric(Sys.getenv("DISC_BASE_SEED", "777")))
if (!is.finite(disc_base_seed)) {
  disc_base_seed <- 777
}
if (exists("set_sampling_exal_seed", mode = "function")) {
  set_sampling_exal_seed(disc_base_seed)
}
if (exists("set_sampling_truncnorm_seed", mode = "function")) {
  set_sampling_truncnorm_seed(disc_base_seed)
}

disc_env_flag <- function(name, default = FALSE) {
  raw <- Sys.getenv(name, "")
  if (!nzchar(raw)) return(isTRUE(default))
  tolower(trimws(raw)) %in% c("1", "true", "yes", "y", "on")
}

disc_env_choice <- function(name, choices, default) {
  raw <- tolower(trimws(Sys.getenv(name, "")))
  if (!nzchar(raw)) return(default)
  if (raw %in% choices) return(raw)
  default
}

disc_env_nonneg_int <- function(name, default = 0L) {
  out <- suppressWarnings(as.integer(Sys.getenv(name, as.character(default))))
  if (!is.finite(out) || out < 0L) return(as.integer(default))
  as.integer(out)
}

disc_env_pos_num <- function(name, default) {
  out <- suppressWarnings(as.numeric(Sys.getenv(name, as.character(default))))
  if (!is.finite(out) || out <= 0) return(as.numeric(default))
  as.numeric(out)
}

disc_env_num <- function(name, default) {
  out <- suppressWarnings(as.numeric(Sys.getenv(name, as.character(default))))
  if (!is.finite(out)) return(as.numeric(default))
  as.numeric(out)
}

DISC_GAMSIG_FREEZE_ITERS <- suppressWarnings(as.integer(Sys.getenv("DISC_GAMSIG_FREEZE_ITERS", "20")))
if (!is.finite(DISC_GAMSIG_FREEZE_ITERS) || DISC_GAMSIG_FREEZE_ITERS < 0L) {
  DISC_GAMSIG_FREEZE_ITERS <- 20L
}
DISC_GAMSIG_FREEZE_ITERS <- as.integer(DISC_GAMSIG_FREEZE_ITERS)
DISC_GAMSIG_MIN_UPDATE_ITERS <- disc_env_nonneg_int(
  "DISC_GAMSIG_MIN_UPDATE_ITERS",
  default = 50L
)
DISC_GAMSIG_MIN_TOTAL_ITERS <- disc_env_nonneg_int(
  "DISC_GAMSIG_MIN_TOTAL_ITERS",
  default = 50L
)
if (!is.finite(DISC_GAMSIG_MIN_TOTAL_ITERS) || DISC_GAMSIG_MIN_TOTAL_ITERS < 1L) {
  DISC_GAMSIG_MIN_TOTAL_ITERS <- 50L
}
DISC_GAMSIG_CONVERGENCE_TOL <- disc_env_pos_num(
  "DISC_GAMSIG_CONVERGENCE_TOL",
  default = 1e-6
)
DISC_GAMSIG_ELBO_TOL <- disc_env_pos_num(
  "DISC_GAMSIG_ELBO_TOL",
  default = DISC_GAMSIG_CONVERGENCE_TOL
)
DISC_GAMSIG_STATE_NORM_TOL <- disc_env_pos_num(
  "DISC_GAMSIG_STATE_NORM_TOL",
  default = 1e-6
)
DISC_GAMSIG_SIGMA_EXP_TOL <- disc_env_pos_num(
  "DISC_GAMSIG_SIGMA_EXP_TOL",
  default = 1e-6
)
DISC_GAMSIG_GAMMA_EXP_TOL <- disc_env_pos_num(
  "DISC_GAMSIG_GAMMA_EXP_TOL",
  default = 1e-6
)
DISC_GAMSIG_FREEZE_TARGET <- disc_env_choice(
  "DISC_GAMSIG_FREEZE_TARGET",
  choices = c("gamma_sigma", "states"),
  default = "gamma_sigma"
)
DISC_GAMSIG_GUARD_REFREEZE_ITERS <- disc_env_nonneg_int(
  "DISC_GAMSIG_GUARD_REFREEZE_ITERS",
  default = 10L
)
DISC_GAMSIG_INIT_MODE <- disc_env_choice(
  "DISC_GAMSIG_INIT_MODE",
  choices = c("legacy", "robust"),
  default = "robust"
)
DISC_GAMSIG_INIT_GAMMA <- disc_env_num("DISC_GAMSIG_INIT_GAMMA", 0.0)
DISC_GAMSIG_INIT_SIGMA_FLOOR <- disc_env_pos_num("DISC_GAMSIG_INIT_SIGMA_FLOOR", 1e-3)
DISC_GAMSIG_INIT_SIGMA_SCALE <- disc_env_pos_num("DISC_GAMSIG_INIT_SIGMA_SCALE", 1.0)

DISC_GAMSIG_OBJECTIVE_GUARD_ENABLED <- disc_env_flag(
  "DISC_GAMSIG_OBJECTIVE_GUARD_ENABLED",
  default = TRUE
)
DISC_GAMSIG_OBJECTIVE_GUARD_FAIL_FAST <- disc_env_flag(
  "DISC_GAMSIG_OBJECTIVE_GUARD_FAIL_FAST",
  default = FALSE
)
DISC_GAMSIG_OBJECTIVE_GUARD_LOG_FAILURES <- disc_env_flag(
  "DISC_GAMSIG_OBJECTIVE_GUARD_LOG_FAILURES",
  default = TRUE
)
DISC_GAMSIG_OBJECTIVE_GUARD_MODE <- disc_env_choice(
  "DISC_GAMSIG_OBJECTIVE_GUARD_MODE",
  choices = c("penalty", "adaptive_freeze"),
  default = "adaptive_freeze"
)
DISC_GAMSIG_OBJECTIVE_GUARD_PENALTY <- disc_env_pos_num(
  "DISC_GAMSIG_OBJECTIVE_GUARD_PENALTY",
  default = 1e12
)
DISC_STRICT_CONTRACTS <- disc_env_flag(
  "DISC_STRICT_CONTRACTS",
  default = TRUE
)

print(c(n.samp, 444))
flush.console()


objective_deltas <- function(delta, SIMS, use_covariates){


print(c(n.samp, 444))
flush.console()

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
    B = C[TT-k,,] %*% t(GG[,,TT-k+1]) %*% solve(R[TT-k+1,,])
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

disc_w_paths <- disc_w_resolve_paths()
parameters_path <- disc_w_paths$parameters_path

disc_w_load_parameters(parameters_path, env = environment())
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
    B = C[TT-k,,] %*% t(GG[,,TT-k+1]) %*% solve(R[TT-k+1,,])
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
covariates <- disc_w_read_covariates(disc_w_paths$cov_1_eli_path, disc_w_paths$cov_2_oni_path)
ELI_lon <- covariates$ELI_lon
merged_sst_data <- covariates$merged_sst_data
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
forecasts <- disc_w_read_forecasts(disc_w_paths$nws_forecast_path, disc_w_paths$glofas_forecast_path)
nws_forecast <- forecasts$nws_forecast
nws_forecast[,-1] <- log(nws_forecast[,-1])
num_ens_nws <- dim(nws_forecast)[2]-1

glofas_forecast <- forecasts$glofas_forecast
glofas_forecast$target_date <- as.Date(glofas_forecast$target_date)
specific_date <- as.Date("2022-12-26")
glofas_forecast <- glofas_forecast[glofas_forecast$target_date >= specific_date, ]
glofas_forecast[,-1] <- log(glofas_forecast[,-1])

num_ens_glofas <- dim(glofas_forecast)[2]-1

ensemble_bundle <- disc_w_build_ensembles(glofas_forecast, nws_forecast)
ensembles <- ensemble_bundle$ensembles
J <- ensemble_bundle$J
num_mem <- ensemble_bundle$num_mem
ranges <- ensemble_bundle$ranges
mean_forecast <- ensemble_bundle$mean_forecast

###########################################################################################
####################################### Covs, Retros, More ################################ 
###########################################################################################

covariate_bundle <- disc_w_build_covariates_and_retro(disc_w_paths, ranges)
X <- covariate_bundle$X
X_f <- covariate_bundle$X_f
Y <- covariate_bundle$Y
TT <- covariate_bundle$TT
J <- covariate_bundle$J

if(use_covariates){
  ending <- "_exAL_synth_DISC"
}else{
  ending <- "_exAL_synth_simp"
}
#
# Model setup without covariates
s_yy <- sd(Y, na.rm = TRUE)  
m_yy <- mean(Y, na.rm = TRUE) + s_yy*qnorm(p0)
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
  model$C0 <- bdiag(model$C0, 0.1 * kk * diag(ppx))
  
  FF <- model$FF
  GG <- model$GG
}


L = L.fn(p0)
U = U.fn(p0)

if (identical(DISC_GAMSIG_INIT_MODE, "robust")) {
  robust_spread <- apply(y, 1, function(v) {
    out <- suppressWarnings(stats::mad(v, center = stats::median(v, na.rm = TRUE), constant = 1.4826, na.rm = TRUE))
    if (!is.finite(out) || out <= 0) {
      out <- suppressWarnings(stats::sd(v, na.rm = TRUE))
    }
    if (!is.finite(out) || out <= 0) {
      out <- 1
    }
    out
  })
  robust_spread <- as.numeric(robust_spread)
  sigma_seed <- pmax(DISC_GAMSIG_INIT_SIGMA_FLOOR, DISC_GAMSIG_INIT_SIGMA_SCALE * robust_spread)
  gamma_seed <- pmin(pmax(DISC_GAMSIG_INIT_GAMMA, L + 1e-6), U - 1e-6)
  sig.init[, 1] <- sigma_seed
  gam.init[, 1] <- gamma_seed
  if (isTRUE(DISC_GAMSIG_OBJECTIVE_GUARD_LOG_FAILURES)) {
    cat(sprintf(
      "[gamsig_init] p0=%s mode=robust gamma_seed=%0.6f sigma_seed_min=%0.6f sigma_seed_max=%0.6f\n",
      as.character(p0),
      as.numeric(gamma_seed),
      as.numeric(min(sigma_seed, na.rm = TRUE)),
      as.numeric(max(sigma_seed, na.rm = TRUE))
    ))
    flush.console()
  }
}

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

preallocate_matrix_list <- function(column_counts, num_rows) {
  n_list <- length(column_counts)
  if (length(num_rows) != n_list) {
    stop(sprintf(
      "preallocate_matrix_list: num_rows length (%d) must match column_counts length (%d)",
      as.integer(length(num_rows)),
      as.integer(n_list)
    ), call. = FALSE)
  }
  matrix_list <- vector("list", n_list)
  for (i in seq_along(column_counts)) {
    num_cols <- suppressWarnings(as.integer(column_counts[i]))
    num_rows_i <- suppressWarnings(as.integer(num_rows[i]))
    if (!is.finite(num_cols) || num_cols <= 0L) {
      stop(sprintf("preallocate_matrix_list: invalid num_cols at i=%d (%s)", as.integer(i), as.character(column_counts[i])), call. = FALSE)
    }
    if (!is.finite(num_rows_i) || num_rows_i <= 0L) {
      stop(sprintf("preallocate_matrix_list: invalid num_rows at i=%d (%s)", as.integer(i), as.character(num_rows[i])), call. = FALSE)
    }
    matrix_list[[i]] <- matrix(NA_real_, nrow = num_rows_i, ncol = num_cols)
  }
  matrix_list
}
fill_with_scalar <- function(matrix_list, scalar, label) {
  val <- suppressWarnings(as.numeric(scalar))
  if (length(val) != 1L || !is.finite(val)) {
    stop(sprintf("%s must be a finite scalar; got length=%d value=%s", label, as.integer(length(val)), as.character(scalar)), call. = FALSE)
  }
  for (i in seq_along(matrix_list)) {
    matrix_list[[i]][] <- val
  }
  matrix_list
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
E1 <- fill_with_scalar(E1, 1, "new.sts.out_f E.sts init")
E2 <- fill_with_scalar(E2, 1, "new.sts.out_f E.sts2 init")

entrop_s <- preallocate_matrix_list(num_mem, rep(1,J) )
entrop_s <- fill_with_scalar(entrop_s, 0, "new.sts.out_f entrop init")

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
for (jj in seq_len(J)) {
  sigma_j <- suppressWarnings(as.numeric(sig0[jj + 1, 1]))
  if (!is.finite(sigma_j) || sigma_j <= 0) {
    stop(sprintf("Invalid sigma seed for forecast ensemble j=%d: %s", as.integer(jj), as.character(sigma_j)), call. = FALSE)
  }
  E1[[jj]][] <- 1 / sigma_j
  E2[[jj]][] <- sigma_j
}

entrop_u <- preallocate_matrix_list(num_mem, rep(1,J))
entrop_u <- fill_with_scalar(entrop_u, 0, "new.uts.out_f entrop init")

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

  print(c(n.samp, 222))
  flush.console()
update_gamma_sigma<-function( y, nn, prior_g, prior_s, 
                              gamma,var.gam,sigma,var.sig,
                              exps,exps2,
                              sts,sts2,
                              uts,inv.uts, 
                              s_init, g_init,
                              Climate_Center,
                              ensembles_j = NULL, num_mem_j = NULL, k_forecast = NULL,
                              sts_f = NULL,sts2_f = NULL,
                              uts_f= NULL,inv.uts_f= NULL,
                              context_label = ""){

log_guard_failure <- function(msg) {
  if (isTRUE(DISC_GAMSIG_OBJECTIVE_GUARD_LOG_FAILURES)) {
    cat(sprintf("[gamsig_guard] %s\n", msg))
    flush.console()
  }
}

s_seed <- suppressWarnings(as.numeric(s_init)[1])
if (!is.finite(s_seed) || s_seed <= 0) {
  s_seed <- 1
}
g_seed <- suppressWarnings(as.numeric(g_init)[1])
if (!is.finite(g_seed)) {
  g_seed <- 0
}
g_seed <- pmin(pmax(g_seed, L + 1e-12), U - 1e-12)

build_guard_fallback <- function(theta_s_val, theta_g_val, guard_msg = "") {
  pi <- plogis(theta_g_val)
  pi <- pmin(pmax(pi, 1e-12), 1 - 1e-12)
  sig <- exp(theta_s_val)
  gam <- L + (U - L) * pi
  a <- A.fn(p0, gam)
  b <- B.fn(p0, gam)
  c <- C.fn(p0, gam)
  var_sig_seed <- suppressWarnings(as.numeric(var.sig)[1])
  var_gam_seed <- suppressWarnings(as.numeric(var.gam)[1])
  if (!is.finite(var_sig_seed) || var_sig_seed <= 0) var_sig_seed <- 1e-3
  if (!is.finite(var_gam_seed) || var_gam_seed <= 0) var_gam_seed <- 1e-3
  hess_seed <- diag(c(var_sig_seed, var_gam_seed), nrow = 2L)
  prior_gamma_log <- suppressWarnings(crch::dtt(
    gam, location = prior_g[1], scale = prior_g[2], df = prior_g[3], left = L, right = U, log = TRUE
  ))
  if (!is.finite(prior_gamma_log)) prior_gamma_log <- -Inf
  prior_sigma_log <- suppressWarnings(nimble::dinvgamma(sig, shape = prior_s[1], scale = prior_s[2], log = TRUE))
  if (!is.finite(prior_sigma_log)) prior_sigma_log <- -Inf
  list(
    E.sigma = sig,
    E.inv.sigma = 1 / sig,
    E.gam = gam,
    E.c2.invb.absgam2.sigma = c^2 * sig * abs(gam)^2 / b,
    E.c.invb.absgam = c * abs(gam) / b,
    E.c.a.invb.absgam = c * abs(gam) * a / b,
    E.a2.invb.inv.sigma = a^2 / (sig * b),
    E.invb.inv.sigma = 1 / (sig * b),
    E.a.invb.inv.sigma = a / (sig * b),
    Hess.LD = hess_seed,
    E.log.sig.b = log(sig * b),
    E.log.sig = log(sig),
    E.prior.sig.gam = prior_gamma_log + prior_sigma_log,
    E.theta = c(theta_s_val, theta_g_val),
    entrop = 0,
    guard_triggered = TRUE,
    guard_message = guard_msg
  )
}

if(!Climate_Center){
  dq_transf <- function(theta_s,theta_g){
      sig <- exp(theta_s)
      pi <- plogis(theta_g)
      # Keep gamma strictly inside (L,U) to avoid evaluating A/B/C at the boundary.
      pi <- pmin(pmax(pi, 1e-12), 1 - 1e-12)
      gam <- L + (U - L) * pi
      a = A.fn(p0,gam); b = B.fn(p0,gam); c = C.fn(p0,gam); p.fn(p0,gam)
      if (isTRUE(DISC_GAMSIG_OBJECTIVE_GUARD_ENABLED)) {
        if (!is.finite(sig) || sig <= 0 || !is.finite(gam) || !is.finite(b) || b <= 0) {
          return(-Inf)
        }
      }

      # Prior
      prior_gamma_dens <- PriorGammaDens(gam, prior_g)
      if (isTRUE(DISC_GAMSIG_OBJECTIVE_GUARD_ENABLED) &&
          (!is.finite(prior_gamma_dens) || prior_gamma_dens <= 0)) {
        return(-Inf)
      }
      yy <- log(prior_gamma_dens) - (prior_s[1] + 1) * log(sig) - prior_s[2]/sig

      # Likelihood
      yy <- yy - (1.5*nn)*log(sig) - (0.5*nn)*log(b)-sum(uts)/sig 
      yy <- yy - 0.5*sum( inv.uts*(y^2-2*y*exps+exps2)/sig
                      - (y-exps)*2*(inv.uts*c*abs(gam)*sts + a/sig)
                      + sig*inv.uts*(c^2)*(abs(gam)^2)*sts2
                      + 2*c*abs(gam)*sts*a
                      + (uts*a^2)/sig )/b
      
      # Jacobian (u=log sigma, gamma=L+(U-L)*logistic(xi))
      yy <- yy + theta_s + log(U - L) + log(pi) + log1p(-pi)
      if (isTRUE(DISC_GAMSIG_OBJECTIVE_GUARD_ENABLED) && !is.finite(yy)) {
        return(-Inf)
      }
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
      pi <- plogis(theta_g)
      # Keep gamma strictly inside (L,U) to avoid evaluating A/B/C at the boundary.
      pi <- pmin(pmax(pi, 1e-12), 1 - 1e-12)
      gam <- L + (U - L) * pi
      a = A.fn(p0,gam); b = B.fn(p0,gam); c = C.fn(p0,gam);
      if (isTRUE(DISC_GAMSIG_OBJECTIVE_GUARD_ENABLED)) {
        if (!is.finite(sig) || sig <= 0 || !is.finite(gam) || !is.finite(b) || b <= 0) {
          return(-Inf)
        }
      }

      # Prior
      prior_gamma_dens <- PriorGammaDens(gam, prior_g)
      if (isTRUE(DISC_GAMSIG_OBJECTIVE_GUARD_ENABLED) &&
          (!is.finite(prior_gamma_dens) || prior_gamma_dens <= 0)) {
        return(-Inf)
      }
      yy <- log(prior_gamma_dens) - (prior_s[1] + 1) * log(sig) - prior_s[2]/sig

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
      # Jacobian (u=log sigma, gamma=L+(U-L)*logistic(xi))
      yy <- yy + theta_s + log(U - L) + log(pi) + log1p(-pi)
      if (isTRUE(DISC_GAMSIG_OBJECTIVE_GUARD_ENABLED) && !is.finite(yy)) {
        return(-Inf)
      }
      return(yy)
  }
}

  theta_s_init <- log(s_seed)
  pi_init <- (g_seed - L) / (U - L)
  pi_init <- pmin(pmax(pi_init, 1e-12), 1 - 1e-12)
  theta_g_init <- qlogis(pi_init)
  initial_values <- c(theta_s_init, theta_g_init)

  # Optimization step
  guard_triggered <- FALSE
  guard_message <- ""
  guard_mode <- DISC_GAMSIG_OBJECTIVE_GUARD_MODE

  mark_guard_trigger <- function(msg) {
    guard_triggered <<- TRUE
    if (!nzchar(guard_message)) {
      guard_message <<- msg
    }
  }

  objective_neg <- function(x) {
    yy <- dq_transf(x[1], x[2])
    if (!isTRUE(DISC_GAMSIG_OBJECTIVE_GUARD_ENABLED)) {
      return(-yy)
    }
    if (!is.finite(yy)) {
      msg <- sprintf(
        "non-finite dq_transf at p0=%s context=%s theta_s=%s theta_g=%s",
        as.character(p0), context_label, format(x[1], digits = 16), format(x[2], digits = 16)
      )
      if (isTRUE(DISC_GAMSIG_OBJECTIVE_GUARD_FAIL_FAST)) {
        stop(msg, call. = FALSE)
      }
      log_guard_failure(msg)
      mark_guard_trigger(msg)
      if (identical(guard_mode, "adaptive_freeze")) {
        return(0)
      }
      return(DISC_GAMSIG_OBJECTIVE_GUARD_PENALTY)
    }
    neg <- -yy
    if (!is.finite(neg)) {
      msg <- sprintf(
        "non-finite negative objective at p0=%s context=%s theta_s=%s theta_g=%s",
        as.character(p0), context_label, format(x[1], digits = 16), format(x[2], digits = 16)
      )
      if (isTRUE(DISC_GAMSIG_OBJECTIVE_GUARD_FAIL_FAST)) {
        stop(msg, call. = FALSE)
      }
      log_guard_failure(msg)
      mark_guard_trigger(msg)
      if (identical(guard_mode, "adaptive_freeze")) {
        return(0)
      }
      return(DISC_GAMSIG_OBJECTIVE_GUARD_PENALTY)
    }
    neg
  }

  optim_results <- optim(par = initial_values, 
                      fn = objective_neg, # Maximizing by minimizing the negative
                      method = "L-BFGS-B", # This method allows box constraints
                      lower = c(-Inf, -Inf), # Transform bounds for gam to theta_g space if needed
                      upper = c(Inf, Inf),
                      hessian = TRUE)
  if (isTRUE(guard_triggered) && identical(guard_mode, "adaptive_freeze")) {
    return(build_guard_fallback(theta_s_init, theta_g_init, guard_msg = guard_message))
  }

  # Evaluate the Hessian at the optimal value
  hessian_at_optimal <- -optim_results$hessian # SINCE WE MIN -f, not MAX f
  # Take the inverse of the Hessian
  inverse_hessian <- tryCatch(solve(hessian_at_optimal), error = function(e) NULL)
  if (is.null(inverse_hessian) || any(!is.finite(inverse_hessian))) {
    msg <- sprintf(
      "non-invertible Hessian at p0=%s context=%s",
      as.character(p0), context_label
    )
    if (isTRUE(DISC_GAMSIG_OBJECTIVE_GUARD_FAIL_FAST)) {
      stop(msg, call. = FALSE)
    }
    log_guard_failure(msg)
    return(build_guard_fallback(theta_s_init, theta_g_init, guard_msg = msg))
  }

  LD_mu <- optim_results$par
  LD_S <- -inverse_hessian

  Expected_f <- function(f, theta_s, theta_g){
      x <- hessian(func = f, x = LD_mu)%*%LD_S
      e <- f(LD_mu) + 0.5*sum(diag(x))
    return(e)
  }

  f.log.sig.b <- function(theta){
    pi <- plogis(theta[2]); pi <- pmin(pmax(pi, 1e-12), 1 - 1e-12)
    sig = exp(theta[1]); gam = L + (U - L) * pi
    a = A.fn(p0,gam); b = B.fn(p0,gam); c = C.fn(p0,gam);
    yy <- log(sig*b)
    return(yy)
  }

  f.log.sig <- function(theta){
    pi <- plogis(theta[2]); pi <- pmin(pmax(pi, 1e-12), 1 - 1e-12)
    sig = exp(theta[1]); gam = L + (U - L) * pi
    a = A.fn(p0,gam); b = B.fn(p0,gam); c = C.fn(p0,gam);
    yy <- log(sig)
    return(yy)
  }

  f.prior.sig.gam <- function(theta){
    pi <- plogis(theta[2]); pi <- pmin(pmax(pi, 1e-12), 1 - 1e-12)
    sig = exp(theta[1]); gam = L + (U - L) * pi
    a = A.fn(p0,gam); b = B.fn(p0,gam); c = C.fn(p0,gam);
    yy <- crch::dtt(gam, location = prior_g[1], scale = prior_g[2], df = prior_g[3], left = L, right = U, log = TRUE)
    yy <- yy + nimble::dinvgamma(sig, shape = prior_s[1], scale =  prior_s[2], log = TRUE)
    return(yy)
  }


  f.c2.s.abs.g2.inv.b <- function(theta){
    pi <- plogis(theta[2]); pi <- pmin(pmax(pi, 1e-12), 1 - 1e-12)
    sig = exp(theta[1]); gam = L + (U - L) * pi
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
    pi <- plogis(theta[2]); pi <- pmin(pmax(pi, 1e-12), 1 - 1e-12)
    gam = L + (U - L) * pi
    b = B.fn(p0,gam); c = C.fn(p0,gam);
    yy <- c*abs(gam)/b
    return(yy)
  }

  f.c.abs.g.a.inv.b <- function(theta){
    pi <- plogis(theta[2]); pi <- pmin(pmax(pi, 1e-12), 1 - 1e-12)
    sig = exp(theta[1]); gam = L + (U - L) * pi
    a = A.fn(p0,gam); b = B.fn(p0,gam); c = C.fn(p0,gam);
    yy <- c*abs(gam)*a/b
    return(yy)
  }

  f.inv.s.inv.b <- function(theta){
    pi <- plogis(theta[2]); pi <- pmin(pmax(pi, 1e-12), 1 - 1e-12)
    sig = exp(theta[1]); gam = L + (U - L) * pi
    a = A.fn(p0,gam); b = B.fn(p0,gam); c = C.fn(p0,gam);
    yy <- 1/sig/b
    return(yy)
  }

  f.a.inv.s.inv.b <- function(theta){
    pi <- plogis(theta[2]); pi <- pmin(pmax(pi, 1e-12), 1 - 1e-12)
    sig = exp(theta[1]); gam = L + (U - L) * pi
    a = A.fn(p0,gam); b = B.fn(p0,gam); c = C.fn(p0,gam);
    yy <- a/sig/b
    return(yy)
  }

  f.a2.inv.s.inv.b <- function(theta){
    pi <- plogis(theta[2]); pi <- pmin(pmax(pi, 1e-12), 1 - 1e-12)
    sig = exp(theta[1]); gam = L + (U - L) * pi
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
    pi <- plogis(theta[2]); pi <- pmin(pmax(pi, 1e-12), 1 - 1e-12)
    gam = L + (U - L) * pi
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
  f.log_jac <- function(theta){
    pi <- plogis(theta[2]); pi <- pmin(pmax(pi, 1e-12), 1 - 1e-12)
    yy <- theta[1] + log(U - L) + log(pi) + log1p(-pi)
    return(yy)
  }
  E.log.jac = Expected_f(f.log_jac, LD_mu[1], LD_mu[2])

  entrop <- log(2*pi*exp(1)) + 0.5*determinant(as.matrix(LD_S), logarithm = TRUE)$modulus[1] + E.log.jac

  return(list(E.sigma=E.sig,E.inv.sigma=E.inv.sigma,E.gam=E.gam,
              E.c2.invb.absgam2.sigma = E.c2.invb.absgam2.sigma, E.c.invb.absgam = E.c.invb.absgam,
              E.c.a.invb.absgam = E.c.a.invb.absgam, E.a2.invb.inv.sigma = E.a2.invb.inv.sigma,
              E.invb.inv.sigma = E.invb.inv.sigma, E.a.invb.inv.sigma = E.a.invb.inv.sigma,
              Hess.LD = LD_S,
              E.log.sig.b=E.log.sig.b, 
              E.log.sig = E.log.sig, 
              E.prior.sig.gam= E.prior.sig.gam,
              E.theta = LD_mu,
              entrop = entrop,
              guard_triggered = FALSE,
              guard_message = ""))
}

########################
T_size <- c(TT, (TT+ranges))
########################

#############################################################################################################################################
#############################################################################################################################################

# Build horizon-segment matrices in deterministic descending-range order.
disc_w_concat_horizon_segments <- function(mat_list, label) {
  if (!is.list(mat_list) || length(mat_list) < 1L) {
    stop(sprintf("%s must be a non-empty list", label), call. = FALSE)
  }
  mats <- lapply(seq_along(mat_list), function(i) {
    m <- as.matrix(mat_list[[i]])
    storage.mode(m) <- "double"
    if (!is.matrix(m) || nrow(m) < 1L || ncol(m) < 1L) {
      stop(sprintf("%s[[%d]] must be a non-empty numeric matrix", label, as.integer(i)), call. = FALSE)
    }
    if (any(!is.finite(m))) {
      stop(sprintf("%s[[%d]] contains non-finite values", label, as.integer(i)), call. = FALSE)
    }
    m
  })
  rows <- vapply(mats, nrow, integer(1))
  if (any(diff(rows) > 0L)) {
    stop(sprintf("%s row counts must be non-increasing; got [%s]", label, paste(rows, collapse = ",")), call. = FALSE)
  }
  out <- vector("list", length(mats))
  out_i <- 1L
  for (idx in seq(from = length(mats), to = 1L, by = -1L)) {
    upper <- rows[idx]
    lower <- if (idx < length(mats)) rows[idx + 1L] else 0L
    if (upper <= lower) {
      stop(sprintf("%s has invalid segment bounds at idx=%d (lower=%d upper=%d)", label, as.integer(idx), as.integer(lower), as.integer(upper)), call. = FALSE)
    }
    segment_rows <- (lower + 1L):upper
    pieces <- lapply(seq_len(idx), function(i) mats[[i]][segment_rows, , drop = FALSE])
    out[[out_i]] <- do.call(cbind, pieces)
    out_i <- out_i + 1L
  }
  out
}
disc_w_assert_shape <- function(x, dims, label, allow_array = FALSE) {
  actual <- dim(x)
  if (is.null(actual)) {
    stop(sprintf("%s has no dim attribute", label), call. = FALSE)
  }
  if (!allow_array && length(actual) != 2L) {
    stop(sprintf("%s must be 2D; got dim length=%d", label, as.integer(length(actual))), call. = FALSE)
  }
  if (length(actual) != length(dims) || any(actual != dims)) {
    stop(sprintf(
      "%s shape mismatch: expected (%s), got (%s)",
      label,
      paste(dims, collapse = "x"),
      paste(actual, collapse = "x")
    ), call. = FALSE)
  }
}
disc_w_validate_cpp_contract <- function(
  GG,
  m0,
  C0,
  FF,
  y,
  ex.df.mat,
  ex.df.mat.k,
  GG_list,
  FF_list,
  FFF_forecast,
  QQQ_forecast,
  ensembles_forecast,
  cur.covs_list,
  num_mem,
  ranges,
  p,
  J,
  ppx,
  TT_sub,
  context_label = ""
) {
  ranges_i <- suppressWarnings(as.integer(ranges))
  num_mem_i <- suppressWarnings(as.integer(num_mem))
  if (length(ranges_i) != J || any(!is.finite(ranges_i)) || any(ranges_i <= 0L)) {
    stop(sprintf("contract %s: invalid ranges [%s]", context_label, paste(ranges, collapse = ",")), call. = FALSE)
  }
  if (length(num_mem_i) != J || any(!is.finite(num_mem_i)) || any(num_mem_i <= 0L)) {
    stop(sprintf("contract %s: invalid num_mem [%s]", context_label, paste(num_mem, collapse = ",")), call. = FALSE)
  }
  if (any(diff(ranges_i) > 0L)) {
    stop(sprintf("contract %s: ranges must be non-increasing, got [%s]", context_label, paste(ranges_i, collapse = ",")), call. = FALSE)
  }
  total_state <- as.integer(p * (J + 1) + ppx)
  disc_w_assert_shape(GG, c(total_state, total_state, as.integer(TT_sub)), sprintf("GG (%s)", context_label), allow_array = TRUE)
  disc_w_assert_shape(C0, c(total_state, total_state), sprintf("C0 (%s)", context_label))
  if (length(as.numeric(m0)) != total_state) {
    stop(sprintf("contract %s: m0 length mismatch expected=%d got=%d", context_label, total_state, as.integer(length(m0))), call. = FALSE)
  }
  disc_w_assert_shape(FF, c(total_state, as.integer(J + 1), as.integer(TT_sub)), sprintf("FF (%s)", context_label), allow_array = TRUE)
  disc_w_assert_shape(y, c(as.integer(J + 1), as.integer(TT_sub)), sprintf("y (%s)", context_label))
  disc_w_assert_shape(ex.df.mat, c(total_state, total_state), sprintf("ex.df.mat (%s)", context_label))
  disc_w_assert_shape(ex.df.mat.k, c(total_state, total_state), sprintf("ex.df.mat.k (%s)", context_label))
  if (length(GG_list) != J || length(FF_list) != J || length(FFF_forecast) != J ||
      length(QQQ_forecast) != J || length(ensembles_forecast) != J || length(cur.covs_list) != J) {
    stop(sprintf("contract %s: list-length mismatch in ensemble payloads", context_label), call. = FALSE)
  }
  ranges_per_i <- if (J > 1L) {
    ranges_i - c(ranges_i[2:J], 0L)
  } else {
    ranges_i
  }
  horizon_i <- rev(ranges_per_i)
  for (seg in seq_len(J)) {
    expected_state <- as.integer(p * (J - seg + 2L))
    expected_series <- as.integer(J - seg + 1L)
    expected_h <- as.integer(horizon_i[seg])
    expected_obs <- as.integer(sum(num_mem_i[seq_len(expected_series)]))
    disc_w_assert_shape(as.matrix(GG_list[[seg]]), c(expected_state, expected_state), sprintf("GG_list[[%d]] (%s)", as.integer(seg), context_label))
    disc_w_assert_shape(as.matrix(FF_list[[seg]]), c(expected_state, expected_series), sprintf("FF_list[[%d]] (%s)", as.integer(seg), context_label))
    disc_w_assert_shape(as.matrix(FFF_forecast[[seg]]), c(expected_obs, expected_h), sprintf("FFF_forecast[[%d]] (%s)", as.integer(seg), context_label))
    disc_w_assert_shape(as.matrix(ensembles_forecast[[seg]]), c(expected_obs, expected_h), sprintf("ensembles_forecast[[%d]] (%s)", as.integer(seg), context_label))
    disc_w_assert_shape(as.array(QQQ_forecast[[seg]]), c(expected_obs, expected_obs, expected_h), sprintf("QQQ_forecast[[%d]] (%s)", as.integer(seg), context_label), allow_array = TRUE)
    disc_w_assert_shape(as.array(cur.covs_list[[seg]]), c(expected_state, expected_state, expected_h), sprintf("cur.covs_list[[%d]] (%s)", as.integer(seg), context_label), allow_array = TRUE)
  }
  invisible(TRUE)
}

ensembles_forecast <- disc_w_concat_horizon_segments(ensembles, "ensembles")
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
crit_ELBO <- 0
ELBO <- 0
seq.elbo = ELBO
iter = 0
FLAG = TRUE

y <- Y

crit_ELBO <- 0
ELBO <- 0
seq.elbo = ELBO
iter = 0
FLAG = TRUE
tol1 <- 1e-3
conv.check <- 0
max_iter <- 1000
fast <- 0
gamsig_update_iters <- 0L
prev_state_norm_sq <- NA_real_
prev_sigma_exp <- NA_real_
prev_gamma_exp <- NA_real_
crit_state_norm_sq <- Inf
crit_sigma_exp <- Inf
crit_gamma_exp <- Inf
fmt_iter_num <- function(x, digits = 8L) {
  if (!is.finite(x)) {
    return("NA")
  }
  format(signif(as.numeric(x), digits = as.integer(digits)), trim = TRUE, scientific = FALSE)
}
fmt_iter_vec <- function(x, digits = 8L) {
  xx <- as.numeric(x)
  if (length(xx) == 0L) {
    return("[]")
  }
  vals <- vapply(xx, function(v) {
    if (!is.finite(v)) {
      return("NA")
    }
    format(signif(as.numeric(v), digits = as.integer(digits)), trim = TRUE, scientific = FALSE)
  }, FUN.VALUE = character(1))
  paste0("[", paste(vals, collapse = ","), "]")
}
  print(c(n.samp, 111))
  flush.console()
if(USE_PREV){
  if(p0==0.05){
    file_path <- "/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_variables_5_exAL_synth_DISC.RData"
    disc_w_load_rdata(file_path)
    new.uts.out = new.uts.out_5_exAL_synth_DISC
    new.sts.out = new.sts.out_5_exAL_synth_DISC
    new.uts.out_f = new.uts_ens.out_5_exAL_synth_DISC
    new.sts.out_f = new.sts_ens.out_5_exAL_synth_DISC
    new.gamsig.out = new.gamsig.out_5_exAL_synth_DISC
    new.theta.out = new.theta.out_5_exAL_synth_DISC
  }else if (p0==0.2) {
    file_path <- "/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_variables_20_exAL_synth_DISC.RData"
    disc_w_load_rdata(file_path)
    new.uts.out = new.uts.out_20_exAL_synth_DISC
    new.sts.out = new.sts.out_20_exAL_synth_DISC
    new.uts.out_f = new.uts_ens.out_20_exAL_synth_DISC
    new.sts.out_f = new.sts_ens.out_20_exAL_synth_DISC
    new.gamsig.out = new.gamsig.out_20_exAL_synth_DISC
    new.theta.out = new.theta.out_20_exAL_synth_DISC
  }else if (p0==0.35) {
    file_path <- "/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_variables_35_exAL_synth_DISC.RData"
    disc_w_load_rdata(file_path)
    new.uts.out = new.uts.out_35_exAL_synth_DISC
    new.sts.out = new.sts.out_35_exAL_synth_DISC
    new.uts.out_f = new.uts_ens.out_35_exAL_synth_DISC
    new.sts.out_f = new.sts_ens.out_35_exAL_synth_DISC
    new.gamsig.out = new.gamsig.out_35_exAL_synth_DISC
    new.theta.out = new.theta.out_35_exAL_synth_DISC
  }else if (p0==0.5) {
    file_path <- "/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_variables_50_exAL_synth_DISC.RData"
    disc_w_load_rdata(file_path)
    new.uts.out = new.uts.out_50_exAL_synth_DISC
    new.sts.out = new.sts.out_50_exAL_synth_DISC
    new.uts.out_f = new.uts_ens.out_50_exAL_synth_DISC
    new.sts.out_f = new.sts_ens.out_50_exAL_synth_DISC
    new.gamsig.out = new.gamsig.out_50_exAL_synth_DISC
    new.theta.out = new.theta.out_50_exAL_synth_DISC
  }else if (p0==0.65) {
    file_path <- "/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_variables_65_exAL_synth_DISC.RData"
    disc_w_load_rdata(file_path)
    new.uts.out = new.uts.out_65_exAL_synth_DISC
    new.sts.out = new.sts.out_65_exAL_synth_DISC
    new.uts.out_f = new.uts_ens.out_65_exAL_synth_DISC
    new.sts.out_f = new.sts_ens.out_65_exAL_synth_DISC
    new.gamsig.out = new.gamsig.out_65_exAL_synth_DISC
    new.theta.out = new.theta.out_65_exAL_synth_DISC
  }else if (p0==0.8) {
    file_path <- "/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_variables_80_exAL_synth_DISC.RData"
    disc_w_load_rdata(file_path)
    new.uts.out = new.uts.out_80_exAL_synth_DISC
    new.sts.out = new.sts.out_80_exAL_synth_DISC
    new.uts.out_f = new.uts_ens.out_80_exAL_synth_DISC
    new.sts.out_f = new.sts_ens.out_80_exAL_synth_DISC
    new.gamsig.out = new.gamsig.out_80_exAL_synth_DISC
    new.theta.out = new.theta.out_80_exAL_synth_DISC
  }else if (p0==0.95) {
    file_path <- "/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_variables_95_exAL_synth_DISC.RData"
    disc_w_load_rdata(file_path)
    new.uts.out = new.uts.out_95_exAL_synth_DISC
    new.sts.out = new.sts.out_95_exAL_synth_DISC
    new.uts.out_f = new.uts_ens.out_95_exAL_synth_DISC
    new.sts.out_f = new.sts_ens.out_95_exAL_synth_DISC
    new.gamsig.out = new.gamsig.out_95_exAL_synth_DISC
    new.theta.out = new.theta.out_95_exAL_synth_DISC
  }
  m0 <- new.theta.out$sm[,1]
  # C0 <- new.theta.out$sC[,,1]
}

# Precompute dimensions and replication counts
dim_theta <- p * ((J+1):2)
ranges_per <- ranges - c(ranges[2:J], 0)
r_vec <- rev(ranges_per)

# Hyperparams for prior 
c_factor <- (10)^2
epsilon <- TT
nu <- dim_theta + 1 + epsilon 

# Preallocate the list of 3D arrays (diagonal matrices)
new.covs_list <- mapply(function(n, r) {
  replicate(r, diag(0.0001, n), simplify = "array")
}, n = dim_theta, r = r_vec, SIMPLIFY = FALSE)

# # Example: inspect the first covariance matrix of the first period
# print(covs_list[[2]][ , , 1])
seq.eigen <- min(abs(eigen(new.covs_list[[2]][,,ranges_per[1]])$values))
# FLAG <- FALSE

########################
tictoc::tic("run time")

   print(c(n.samp))
  flush.console()
########################

gamsig_dynamic_freeze_until_iter <- as.integer(DISC_GAMSIG_FREEZE_ITERS)
if (!is.finite(gamsig_dynamic_freeze_until_iter) || gamsig_dynamic_freeze_until_iter < 0L) {
  gamsig_dynamic_freeze_until_iter <- 0L
}
if (isTRUE(DISC_GAMSIG_OBJECTIVE_GUARD_LOG_FAILURES)) {
  cat(sprintf(
    "[gamsig_policy] p0=%s freeze_target=%s warmup_freeze_iters=%d min_update_iters=%d min_total_iters=%d elbo_tol=%g state_norm_sq_tol=%g sigma_exp_tol=%g gamma_exp_tol=%g guard_mode=%s guard_refreeze_iters=%d\n",
    as.character(p0),
    DISC_GAMSIG_FREEZE_TARGET,
    as.integer(DISC_GAMSIG_FREEZE_ITERS),
    as.integer(DISC_GAMSIG_MIN_UPDATE_ITERS),
    as.integer(DISC_GAMSIG_MIN_TOTAL_ITERS),
    as.numeric(DISC_GAMSIG_ELBO_TOL),
    as.numeric(DISC_GAMSIG_STATE_NORM_TOL),
    as.numeric(DISC_GAMSIG_SIGMA_EXP_TOL),
    as.numeric(DISC_GAMSIG_GAMMA_EXP_TOL),
    DISC_GAMSIG_OBJECTIVE_GUARD_MODE,
    as.integer(DISC_GAMSIG_GUARD_REFREEZE_ITERS)
  ))
  flush.console()
}

  
while (isTRUE(FLAG) && iter < max_iter) {


    cur.covs_list = new.covs_list

    cur.uts.out = new.uts.out
    cur.sts.out = new.sts.out 
    cur.uts.out_f = new.uts.out_f
    cur.sts.out_f = new.sts.out_f

    cur.gamsig.out = new.gamsig.out
    cur.theta.out = new.theta.out

    ex.df.mat_f <- as.matrix(ex.df.mat_f)
    ex.df.mat.k_f <- as.matrix(ex.df.mat.k_f)

    FFF <- (new.gamsig.out$E.c.invb.absgam[,] * new.sts.out$E.sts + new.gamsig.out$E.a.invb.inv.sigma[,]/new.uts.out$E.inv.uts) / new.gamsig.out$E.invb.inv.sigma[,] 
    QQQ <- 1/(new.gamsig.out$E.invb.inv.sigma[,] * new.uts.out$E.inv.uts)
    if(J>0){
    QQQ <- array(apply(QQQ, 2, function(col) diag(col)), dim = c(J+1, J+1, TT_sub))
    }else{
        QQQ <- array(QQQ, dim = c(J+1, J+1, TT_sub))
    }


    ######################################
    ######################################


    FFF_list <- vector("list", J)
    QQQ_list <- vector("list", J)
    for (j in 1:J) {
        FFF_j <- (new.gamsig.out$E.c.invb.absgam[j,] * new.sts.out_f$E.sts[[j]] + new.gamsig.out$E.a.invb.inv.sigma[j,] / new.uts.out_f$E.inv.uts[[j]]) / new.gamsig.out$E.invb.inv.sigma[j,]
        FFF_list[[j]] <- FFF_j

        QQQ_j <- 1/(new.gamsig.out$E.invb.inv.sigma[j,] * new.uts.out_f$E.inv.uts[[j]])
        QQQ_list[[j]] <- QQQ_j
    }

    ######################################
    ######################################
    result_F <- disc_w_concat_horizon_segments(FFF_list, sprintf("FFF_list iter=%d", as.integer(iter)))
    FFF_forecast <- lapply(result_F, t)

    result_Q <- disc_w_concat_horizon_segments(QQQ_list, sprintf("QQQ_list iter=%d", as.integer(iter)))
    QQQ_forecast_VEC <- lapply(result_Q, t)
    QQQ_forecast <- vector("list", J)

    # Loop through each element in QQQ_forecast
    for (j in 1:J) {
      # Get the dimensions of the current matrix
      n <- dim(QQQ_forecast_VEC[[j]])[1]
      m <- dim(QQQ_forecast_VEC[[j]])[2]
      
      # Initialize the array
      A <- array(0, dim = c(n, n, m))
      
      # Fill the array with diagonal matrices
      for (k in 1:m) {
        A[,,k] <- diag(QQQ_forecast_VEC[[j]][,k])
      }
      
      # Store the array in the list
      QQQ_forecast[[j]] <- A
    }
  iter_candidate <- as.integer(iter + 1L)
  state_freeze_now <- identical(DISC_GAMSIG_FREEZE_TARGET, "states") &&
    (gamsig_dynamic_freeze_until_iter > 0L) &&
    (iter_candidate <= gamsig_dynamic_freeze_until_iter)

  if (state_freeze_now) {
    theta_update <- FALSE
    iter <- iter_candidate
    fast <- fast + 1
    if (isTRUE(DISC_GAMSIG_OBJECTIVE_GUARD_LOG_FAILURES)) {
      cat(sprintf(
        "[state_freeze] p0=%s iter=%d freeze_until_iter=%d\n",
        as.character(p0), as.integer(iter), as.integer(gamsig_dynamic_freeze_until_iter)
      ))
      flush.console()
    }
  } else if (iter < max_iter) {
    # if ((crit_ELBO+conv.check) < tol1 || iter < 100 || fast > 0 ) {
    if (isTRUE(DISC_STRICT_CONTRACTS)) {
      disc_w_validate_cpp_contract(
        GG = GG,
        m0 = m0,
        C0 = C0,
        FF = FF,
        y = y,
        ex.df.mat = ex.df.mat,
        ex.df.mat.k = ex.df.mat.k,
        GG_list = GG_list,
        FF_list = FF_list,
        FFF_forecast = FFF_forecast,
        QQQ_forecast = QQQ_forecast,
        ensembles_forecast = ensembles_forecast,
        cur.covs_list = cur.covs_list,
        num_mem = num_mem,
        ranges = ranges,
        p = p,
        J = J,
        ppx = ppx,
        TT_sub = TT_sub,
        context_label = sprintf("p0=%s iter=%d", as.character(p0), as.integer(iter))
      )
    }
    update.theta <- DISC_update_theta_synth_cpp_W( GG, m0, C0,
                                            FFF, QQQ,
                                            FF, y, ex.df.mat, ex.df.mat.k, Ones,
                                            p, J, ppx, TT, k, dM,
                                            GG_list, FF_list,
                                            FFF_forecast, QQQ_forecast,
                                            DF.MAT, DF.MAT_k,
                                            ensembles_forecast, ranges, Ones_ens,
                                            sum(num_mem), num_mem, cur.covs_list)

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
    new.theta.out$exps[2:(J-j+2),(TT+1+rs-r_j):(TT+rs)] <- exps_ens
    new.theta.out$exps2[2:(J-j+2),(TT+1+rs-r_j):(TT+rs)] <- exps2_ens
    new.theta.out$sm_ens[[j]] <- sm_j
    new.theta.out$sC_ens[[j]] <- sC_j
    new.theta.out$fm_ens[[j]] <- fm_j
    new.theta.out$fC_ens[[j]] <- fC_j

    error_j <- matrix(update.theta$standard_forecast_errors_ens[[j]], nrow = cumsum(num_mem)[J-j+1])
    new.theta.out$standard_forecast_errors_ens[[j]] <- error_j
    }

    new.theta.out$exps[,1:TT] <- exps
    new.theta.out$exps2[,1:TT] <- exps2
    new.theta.out$standard_forecast_errors <- update.theta$standard_forecast_errors
    new.theta.out$sm <- update.theta$sm
    new.theta.out$sC <- update.theta$sC
    new.theta.out$fm <- update.theta$fm
    new.theta.out$fC <- update.theta$fC

    new.theta.out$elbo.part <- update.theta$elbo.part
    new.theta.out$elbo.part_ens <- update.theta$elbo.part_ens

    new.theta.out$W_T <- update.theta$W_T
    theta_update <- TRUE
    iter <- iter + 1
    fast <- 0
  } else {
    theta_update <- FALSE
    fast <- fast + 1
  }

  ## UPDATE W
  if (!state_freeze_now) {
    for(j in 1:J){
        for(t in 1:rev(ranges_per)[j]){
            Ct <- new.theta.out$sC_ens[[j]][,,t]
            mt <- new.theta.out$sm_ens[[j]][,t]
            GGG <- GG_list[[j]]
            if((j == 1) && (t == 1)){
                ddd <- dim_theta[1]
                Ct_1 <- new.theta.out$sC[1:ddd,1:ddd,TT]
                mt_1 <- new.theta.out$sm[1:ddd,TT]
            }else if ((j == 2) && (t == 1)){
                ddd <- dim_theta[j]
                Ct_1 <- new.theta.out$sC_ens[[j-1]][1:ddd,1:ddd,rev(ranges_per)[j-1]]
                mt_1 <- new.theta.out$sm_ens[[j-1]][1:ddd,rev(ranges_per)[j-1]]
            }else{
                Ct_1 <- new.theta.out$sC_ens[[j]][,,(t-1)]
                mt_1 <- new.theta.out$sm_ens[[j]][,(t-1)]
            }

            GCG <- GGG %*% Ct_1 %*% t(GGG)
            R <- GCG + cur.covs_list[[j]][,,t]
            R_inv <- solve(R)
            ww <- GCG + (mt-GGG %*% mt_1) %*% t(mt-GGG %*% mt_1) + Ct -2*GCG %*% R_inv %*% Ct
            new.covs_list[[j]][,,t]  <- epsilon/(epsilon+1)* c_factor *new.theta.out$W_T[1:ddd,1:ddd] + 1/(epsilon+1)*ww

        }
    }
  }

  gamsig_frozen_now <- identical(DISC_GAMSIG_FREEZE_TARGET, "gamma_sigma") &&
    (gamsig_dynamic_freeze_until_iter > 0L) &&
    (iter <= gamsig_dynamic_freeze_until_iter)
  if (gamsig_frozen_now && isTRUE(DISC_GAMSIG_OBJECTIVE_GUARD_LOG_FAILURES)) {
    cat(sprintf(
      "[gamsig_freeze] p0=%s iter=%d freeze_until_iter=%d\n",
      as.character(p0), as.integer(iter), as.integer(gamsig_dynamic_freeze_until_iter)
    ))
    flush.console()
  }

  ## UPDATE s and u
  for (j in 1:(J+1)) {   
      sts.dummy <- update_sts(y[j,],
                              new.theta.out$exps[j,1:TT_sub], 
                              cur.uts.out$E.inv.uts[j,], 
                              cur.gamsig.out$E.c2.invb.absgam2.sigma[j,], 
                              cur.gamsig.out$E.c.invb.absgam[j,], 
                              cur.gamsig.out$E.c.a.invb.absgam[j,], TT_sub)
      new.sts.out$E.sts[j,] <- sts.dummy$E.sts
      new.sts.out$E.sts2[j,] <- sts.dummy$E.sts2
      new.sts.out$tot.entrop[j,] <-  sts.dummy$tot.entrop
      ########################
      uts.dummy <- update_uts(y[j,],
                              new.theta.out$exps[j,1:TT_sub], 
                              new.theta.out$exps2[j,1:TT_sub], 
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
      if (j == 1) {
        if (!gamsig_frozen_now) {
        gamsig.dummy <- update_gamma_sigma(y[j,], 
                                            TT,
                                            PriorGamma[j,],
                                            PriorSigma[j,],
                                              cur.gamsig.out$E.gam[j,], 
                                              cur.gamsig.out$V.gam[j,], 
                                              cur.gamsig.out$E.sigma[j,], 
                                              cur.gamsig.out$V.sigma[j,], 
                                              new.theta.out$exps[j,1:TT_sub], 
                                              new.theta.out$exps2[j,1:TT_sub], 
                                              new.sts.out$E.sts[j,], 
                                              new.sts.out$E.sts2[j,], 
                                              new.uts.out$E.uts[j,], 
                                              new.uts.out$E.inv.uts[j,],
                                              cur.gamsig.out$E.sigma[j,], 
                                              cur.gamsig.out$E.gam[j,],
                                              FALSE,
                                              context_label = sprintf("vb_main iter=%d j=%d climate_center=FALSE", iter, j))    
          if (isTRUE(gamsig.dummy$guard_triggered) &&
              DISC_GAMSIG_GUARD_REFREEZE_ITERS > 0L &&
              identical(DISC_GAMSIG_FREEZE_TARGET, "gamma_sigma")) {
            old_freeze_until <- gamsig_dynamic_freeze_until_iter
            gamsig_dynamic_freeze_until_iter <- max(
              as.integer(gamsig_dynamic_freeze_until_iter),
              as.integer(iter + DISC_GAMSIG_GUARD_REFREEZE_ITERS)
            )
            gamsig_frozen_now <- TRUE
            if (isTRUE(DISC_GAMSIG_OBJECTIVE_GUARD_LOG_FAILURES)) {
              cat(sprintf(
                "[gamsig_refreeze] p0=%s iter=%d j=%d old_until=%d new_until=%d reason=%s\n",
                as.character(p0),
                as.integer(iter),
                as.integer(j),
                as.integer(old_freeze_until),
                as.integer(gamsig_dynamic_freeze_until_iter),
                ifelse(is.null(gamsig.dummy$guard_message), "", as.character(gamsig.dummy$guard_message))
              ))
              flush.console()
            }
          }
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
      }else{
          k_forecast <- ranges[j-1]
          for (i in 1:num_mem[j-1]) {
              
          sts.dummy <- update_sts(
                          y = matrix(ensembles[[j-1]][,i], ncol=1), 
                          exps = matrix(new.theta.out$exps[j,(TT_sub+1):(TT_sub+k_forecast)], ncol=1), 
                          inv.uts = matrix(cur.uts.out_f$E.inv.uts[[j-1]][,i], ncol=1), 
                          c2.invb.absgam2.sigma = cur.gamsig.out$E.c2.invb.absgam2.sigma[j,], 
                          c.invb.absgam = cur.gamsig.out$E.c.invb.absgam[j,], 
                          c.a.invb.absgam = cur.gamsig.out$E.c.a.invb.absgam[j,], 
                          k_forecast)

          new.sts.out_f$E.sts[[j-1]][,i] <- sts.dummy$E.sts
          new.sts.out_f$E.sts2[[j-1]][,i] <- sts.dummy$E.sts2
          new.sts.out_f$tot.entrop[[j-1]][i] <-  sts.dummy$tot.entrop

          uts.dummy <- update_uts(
                          y = matrix(ensembles[[j-1]][,i], ncol=1),
                          exps = matrix(new.theta.out$exps[j,(T+1):(T+k_forecast)], ncol=1), 
                          exps2 = matrix(new.theta.out$exps2[j,(T+1):(T+k_forecast)], ncol=1), 
                          new.sts.out_f$E.sts[[j-1]][,i], 
                          new.sts.out_f$E.sts2[[j-1]][,i], 
                          cur.gamsig.out$E.inv.sigma[j,], 
                          cur.gamsig.out$E.a2.invb.inv.sigma[j,], 
                          cur.gamsig.out$E.invb.inv.sigma[j,], 
                          cur.gamsig.out$E.c.invb.absgam[j,], 
                          cur.gamsig.out$E.c2.invb.absgam2.sigma[j,]) 
                          
          new.uts.out_f$E.uts[[j-1]][,i] <- uts.dummy$E.uts
          new.uts.out_f$E.inv.uts[[j-1]][,i] <- uts.dummy$E.inv.uts
          new.uts.out_f$E.log.uts[[j-1]][i] <- uts.dummy$E.log.uts
          new.uts.out_f$tot.entrop[[j-1]][i] <- uts.dummy$tot.entrop
          }

      }
  }
    ## UPDATE sigma and gamma
  for (j in 2:(J+1)) {  
          if (gamsig_frozen_now) {
            next
          }
          k_forecast <- ranges[j-1]
          gamsig.dummy <- update_gamma_sigma(Y[j,], TT_sub,
                                              PriorGamma[j,],
                                              PriorSigma[j,],
                                              cur.gamsig.out$E.gam[j,], 
                                              cur.gamsig.out$V.gam[j,], 
                                              cur.gamsig.out$E.sigma[j,], 
                                              cur.gamsig.out$V.sigma[j,], 
                                              new.theta.out$exps[j,], 
                                              new.theta.out$exps2[j,], 
                                              new.sts.out$E.sts[j,], 
                                              new.sts.out$E.sts2[j,], 
                                              new.uts.out$E.uts[j,], 
                                              new.uts.out$E.inv.uts[j,],
                                              cur.gamsig.out$E.sigma[j,], 
                                              cur.gamsig.out$E.gam[j,],
                                              TRUE ,
                                              ensembles[[j-1]], 
                                              num_mem[j-1], 
                                              k_forecast,
                                              new.sts.out_f$E.sts[[j-1]],
                                              new.sts.out_f$E.sts2[[j-1]],
                                              new.uts.out_f$E.uts[[j-1]],
                                              new.uts.out_f$E.inv.uts[[j-1]],
                                              context_label = sprintf("vb_main iter=%d j=%d climate_center=TRUE", iter, j))
          if (isTRUE(gamsig.dummy$guard_triggered) &&
              DISC_GAMSIG_GUARD_REFREEZE_ITERS > 0L &&
              identical(DISC_GAMSIG_FREEZE_TARGET, "gamma_sigma")) {
            old_freeze_until <- gamsig_dynamic_freeze_until_iter
            gamsig_dynamic_freeze_until_iter <- max(
              as.integer(gamsig_dynamic_freeze_until_iter),
              as.integer(iter + DISC_GAMSIG_GUARD_REFREEZE_ITERS)
            )
            gamsig_frozen_now <- TRUE
            if (isTRUE(DISC_GAMSIG_OBJECTIVE_GUARD_LOG_FAILURES)) {
              cat(sprintf(
                "[gamsig_refreeze] p0=%s iter=%d j=%d old_until=%d new_until=%d reason=%s\n",
                as.character(p0),
                as.integer(iter),
                as.integer(j),
                as.integer(old_freeze_until),
                as.integer(gamsig_dynamic_freeze_until_iter),
                ifelse(is.null(gamsig.dummy$guard_message), "", as.character(gamsig.dummy$guard_message))
              ))
              flush.console()
            }
          }

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

  if (!gamsig_frozen_now) {
    gamsig_update_iters <- as.integer(gamsig_update_iters + 1L)
  }

  old.gam <- as.numeric(seq.gamma[, dim(seq.gamma)[2], drop = TRUE])
  new.gam <- as.numeric(new.gamsig.out$E.gam)
  if (length(old.gam) != length(new.gam)) {
    stop(sprintf("gamma length drift at iter=%d: old=%d new=%d", as.integer(iter), as.integer(length(old.gam)), as.integer(length(new.gam))), call. = FALSE)
  }
  seq.gamma = cbind(seq.gamma, new.gam)

  old.sig <- as.numeric(seq.sigma[, dim(seq.sigma)[2], drop = TRUE])
  new.sig <- as.numeric(new.gamsig.out$E.sigma)
  if (length(old.sig) != length(new.sig)) {
    stop(sprintf("sigma length drift at iter=%d: old=%d new=%d", as.integer(iter), as.integer(length(old.sig)), as.integer(length(new.sig))), call. = FALSE)
  }
  seq.sigma = cbind(seq.sigma, new.sig)
  gamma_delta_vec <- as.numeric(new.gam - old.gam)
  sigma_delta_vec <- as.numeric(new.sig - old.sig)

  if (gamsig_frozen_now) {
    conv.check <- Inf
  } else {
    step_vec <- c(gamma_delta_vec, sigma_delta_vec)
    if (length(step_vec) == 0L || any(!is.finite(step_vec))) {
      conv.check <- Inf
    } else {
      conv.check <- sum(step_vec^2)
    }
  }

  ##########
  # ELBO
  ##########
  elbo <- 0

  elbo <- elbo -1/2*sum(T_size*new.gamsig.out$E.log.sig.b[,])

  elbo <- elbo -0.5*sum(new.uts.out$E.log.uts[,])-0.5*sum(unlist(new.uts.out_f$E.log.uts))
  elbo <- elbo -sum(T_size)/2*log(pi)

  elbo <- elbo -0.5*sum((new.gamsig.out$E.invb.inv.sigma[,]*new.uts.out$E.inv.uts[,])*(y[,]^2-2*y[,]*new.theta.out$exps[,1:TT_sub]+new.theta.out$exps2[,1:TT_sub]))
  ss <- 0
  for(j in 2:J){ss <- ss - 0.5* sum((new.gamsig.out$E.invb.inv.sigma[j,]*new.uts.out_f$E.inv.uts[[j-1]])*(ensembles[[j-1]]^2-2*ensembles[[j-1]]*new.theta.out$exps[j,(TT_sub+1):(TT_sub+k_forecast)]+new.theta.out$exps2[j,(TT_sub+1):(TT_sub+k_forecast)]))
  }
  elbo <- elbo + ss

  elbo <- elbo +sum((y[,]-new.theta.out$exps[,1:TT_sub])*(new.gamsig.out$E.c.invb.absgam[,]*new.sts.out$E.sts*new.uts.out$E.inv.uts[,]+new.gamsig.out$E.a.invb.inv.sigma[,]))
  ss <- 0
  for(j in 2:J){ss <- ss - 0.5* sum((ensembles[[j-1]]-new.theta.out$exps[j,(TT_sub+1):(TT_sub+k_forecast)])*(new.gamsig.out$E.c.invb.absgam[j,]*new.sts.out_f$E.sts[[j-1]]*new.uts.out_f$E.inv.uts[[j-1]]+new.gamsig.out$E.a.invb.inv.sigma[j,]))
  }
  elbo <- elbo + ss

  elbo <- elbo -0.5*sum(new.sts.out$E.sts2[,]*new.uts.out$E.inv.uts[,]*new.gamsig.out$E.c2.invb.absgam2.sigma[,])
  ss <- 0
  for(j in 2:J){ss <- ss - 0.5*sum(new.gamsig.out$E.c2.invb.absgam2.sigma[j,]*new.uts.out_f$E.sts2[[j-1]]*new.uts.out_f$E.uts[[j-1]])}
  elbo <- elbo + ss

  elbo <- elbo -sum(new.gamsig.out$E.c.a.invb.absgam[,]*new.sts.out$E.sts[,])
  ss <- 0
  for(j in 2:J){ss <- ss - sum(new.gamsig.out$E.c.a.invb.absgam[j,]*new.uts.out_f$E.sts[[j-1]])}
  elbo <- elbo + ss

  elbo <- elbo -0.5*sum(new.gamsig.out$E.a2.invb.inv.sigma[,]*new.uts.out$E.uts[,])
  ss <- 0
  for(j in 2:J){ss <- ss - 0.5*sum(new.gamsig.out$E.a2.invb.inv.sigma[j,]*new.uts.out_f$E.uts[[j-1]])}
  elbo <- elbo + ss

  elbo <- elbo -sum(T_size*new.gamsig.out$E.log.sig[,])

  elbo <- elbo -sum(new.gamsig.out$E.inv.sigma[,]*new.uts.out$E.uts[,])
  ss <- 0
  for(j in 2:J){ss <- ss - sum(new.gamsig.out$E.inv.sigma[j,]*new.uts.out_f$E.uts[[j-1]])}
  elbo <- elbo + ss

  elbo <- elbo -0.5*sum(new.sts.out$E.sts2[,])-0.5*sum(unlist(new.sts.out_f$E.sts2)) 
  elbo <- elbo +sum(new.gamsig.out$E.prior.sig.gam[,])

  elbo <- elbo +sum(new.uts.out$tot.entrop[,])+sum(unlist(new.uts.out_f$tot.entrop))
  elbo <- elbo +sum(new.sts.out$E.tot.entrop[,])+sum(unlist(new.sts.out_f$tot.entrop)) 
  elbo <- elbo +sum(new.gamsig.out$E.sig.gam.entrop[,])
  elbo <- elbo + new.theta.out$elbo.part

  ######################

  elbo <- elbo/sum(T_size)/( p*(J+1) + ppx)
  crit_ELBO <- abs(ELBO-elbo)
  ELBO <- elbo
  seq.elbo =  cbind(seq.elbo, ELBO) 
 
  seq.eigen = cbind(seq.eigen, min(abs(eigen(new.covs_list[[2]][,,ranges_per[1]])$values))) 

  print(c(iter, elbo, crit_ELBO))
  sigma_exp <- suppressWarnings(as.numeric(mean(new.sig, na.rm = TRUE)))
  gamma_exp <- suppressWarnings(as.numeric(mean(new.gam, na.rm = TRUE)))
  state_norm_sq <- suppressWarnings(as.numeric(sum(new.theta.out$sm^2, na.rm = TRUE)))
  if (!is.finite(sigma_exp)) sigma_exp <- NA_real_
  if (!is.finite(gamma_exp)) gamma_exp <- NA_real_
  if (!is.finite(state_norm_sq)) state_norm_sq <- NA_real_
  if (is.finite(prev_state_norm_sq) && is.finite(state_norm_sq)) {
    crit_state_norm_sq <- abs(state_norm_sq - prev_state_norm_sq)
  } else {
    crit_state_norm_sq <- Inf
  }
  if (is.finite(prev_sigma_exp) && is.finite(sigma_exp)) {
    crit_sigma_exp <- abs(sigma_exp - prev_sigma_exp)
  } else {
    crit_sigma_exp <- Inf
  }
  if (is.finite(prev_gamma_exp) && is.finite(gamma_exp)) {
    crit_gamma_exp <- abs(gamma_exp - prev_gamma_exp)
  } else {
    crit_gamma_exp <- Inf
  }
  prev_state_norm_sq <- state_norm_sq
  prev_sigma_exp <- sigma_exp
  prev_gamma_exp <- gamma_exp

  if (isTRUE(DISC_GAMSIG_OBJECTIVE_GUARD_LOG_FAILURES)) {
    cat(sprintf(
      "[gamsig_progress] family=exdqlm_multivar p0=%s iter=%d elbo=%s crit_elbo=%s sigma_exp=%s crit_sigma_exp=%s gamma_exp=%s crit_gamma_exp=%s sigma_exp_vec=%s gamma_exp_vec=%s sigma_delta_vec=%s gamma_delta_vec=%s state_norm_sq=%s crit_state_norm_sq=%s conv_check=%s gamsig_update_iters=%d min_update_iters=%d min_total_iters=%d frozen=%s\n",
      as.character(p0),
      as.integer(iter),
      fmt_iter_num(elbo),
      fmt_iter_num(crit_ELBO),
      fmt_iter_num(sigma_exp),
      fmt_iter_num(crit_sigma_exp),
      fmt_iter_num(gamma_exp),
      fmt_iter_num(crit_gamma_exp),
      fmt_iter_vec(new.sig),
      fmt_iter_vec(new.gam),
      fmt_iter_vec(sigma_delta_vec),
      fmt_iter_vec(gamma_delta_vec),
      fmt_iter_num(state_norm_sq),
      fmt_iter_num(crit_state_norm_sq),
      fmt_iter_num(conv.check),
      as.integer(gamsig_update_iters),
      as.integer(DISC_GAMSIG_MIN_UPDATE_ITERS),
      as.integer(DISC_GAMSIG_MIN_TOTAL_ITERS),
      ifelse(isTRUE(gamsig_frozen_now), "true", "false")
    ))
  }
  flush.console()

  if(theta_update){
    conv_elbo <- is.finite(crit_ELBO) && (crit_ELBO < DISC_GAMSIG_ELBO_TOL)
    conv_state <- is.finite(crit_state_norm_sq) && (crit_state_norm_sq < DISC_GAMSIG_STATE_NORM_TOL)
    conv_sigma <- is.finite(crit_sigma_exp) && (crit_sigma_exp < DISC_GAMSIG_SIGMA_EXP_TOL)
    conv_gamma <- is.finite(crit_gamma_exp) && (crit_gamma_exp < DISC_GAMSIG_GAMMA_EXP_TOL)
    conv_min_updates <- gamsig_update_iters >= DISC_GAMSIG_MIN_UPDATE_ITERS
    conv_min_iters <- iter >= DISC_GAMSIG_MIN_TOTAL_ITERS
    if (conv_elbo && conv_state && conv_sigma && conv_gamma && conv_min_updates && conv_min_iters) {
      FLAG = FALSE
    } else if (isTRUE(DISC_GAMSIG_OBJECTIVE_GUARD_LOG_FAILURES)) {
      cat(sprintf(
        "[gamsig_hold] p0=%s iter=%d conv_elbo=%s conv_state=%s conv_sigma=%s conv_gamma=%s conv_min_updates=%s conv_min_iters=%s updates=%d required_updates=%d required_iters=%d\n",
        as.character(p0),
        as.integer(iter),
        ifelse(conv_elbo, "true", "false"),
        ifelse(conv_state, "true", "false"),
        ifelse(conv_sigma, "true", "false"),
        ifelse(conv_gamma, "true", "false"),
        ifelse(conv_min_updates, "true", "false"),
        ifelse(conv_min_iters, "true", "false"),
        as.integer(gamsig_update_iters),
        as.integer(DISC_GAMSIG_MIN_UPDATE_ITERS),
        as.integer(DISC_GAMSIG_MIN_TOTAL_ITERS)
      ))
    }
  }



}
########################

if (gamsig_update_iters < DISC_GAMSIG_MIN_UPDATE_ITERS) {
  stop(
    sprintf(
      "stopped before required gamma/sigma updates: got=%d required=%d",
      as.integer(gamsig_update_iters),
      as.integer(DISC_GAMSIG_MIN_UPDATE_ITERS)
    ),
    call. = FALSE
  )
}

########################
run.time = tictoc::toc(quiet = TRUE)
########################
if (verbose) {
  cat(sprintf("VB converged: %s iterations, %s seconds", 
              iter, round(run.time$toc - run.time$tic, 3)), "\n")
}

print(c(n.samp))
flush.console()



n.samp <- 2000

if(SIMS){

  print(c(n.samp))
  flush.console()

tictoc::tic("run time")
########################
if (verbose) {
  cat(sprintf("Sampling Started", 
              iter, round(run.time$toc - run.time$tic, 3)), "\n")
}
samp.uts_ens <- vector("list", length(num_mem))
for (i in seq_along(num_mem)) {
num_cols <- num_mem[i]
samp.uts_ens[[i]] <- array(NA_real_, c(ranges[i], num_cols, n.samp) )
}

samp.sts_ens <- vector("list", length(num_mem))
for (i in seq_along(num_mem)) {
num_cols <- num_mem[i]
samp.sts_ens[[i]] <- array(NA_real_, c(ranges[i], num_cols, n.samp) )
}
########################
samp.gamma = array(NA_real_, c(J+1, n.samp))
samp.sigma = array(NA_real_, c(J+1, n.samp))
samp.uts = array(NA_real_, c(J+1, TT_sub, n.samp))
samp.sts = array(NA_real_, c(J+1, TT_sub, n.samp))
print(c(n.samp))
flush.console()

for (j in 1:(J+1)) {   
    sts.dummy <- update_sts(y[j,],
                            new.theta.out$exps[j,1:TT_sub], 
                            cur.uts.out$E.inv.uts[j,], 
                            cur.gamsig.out$E.c2.invb.absgam2.sigma[j,], 
                            cur.gamsig.out$E.c.invb.absgam[j,], 
                            cur.gamsig.out$E.c.a.invb.absgam[j,], TT_sub)
    new.sts.out$E.sts[j,] <- sts.dummy$E.sts
    new.sts.out$E.sts2[j,] <- sts.dummy$E.sts2
    new.sts.out$tot.entrop[j,] <-  sts.dummy$tot.entrop
    ########################
    uts.dummy <- update_uts(y[j,],
                            new.theta.out$exps[j,1:TT_sub], 
                            new.theta.out$exps2[j,1:TT_sub], 
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
    ########################
    ########################
    ########################
    # Generalized Inverse Gausian Sampling
    samp.uts[j,,] = t(sample_gig_devroye_vector(n.samp, uts.dummy$uts.lambda, uts.dummy$uts.psi, uts.dummy$uts.chi))
    # Truncated normal
    samp.sts[j,,] = t(sample_truncnorm_icdf(n.samp, TT_sub, sts.dummy$sts.mu, sts.dummy$sts.sig2) )
    ########################
    ########################
    ########################
    ########################
    if(j==1){
        gamsig.dummy <- update_gamma_sigma(y[j,], 
                                            TT_sub,
                                            PriorGamma[j,],
                                            PriorSigma[j,],
                                            cur.gamsig.out$E.gam[j,], 
                                            cur.gamsig.out$V.gam[j,], 
                                            cur.gamsig.out$E.sigma[j,], 
                                            cur.gamsig.out$V.sigma[j,], 
                                            new.theta.out$exps[j,1:TT_sub], 
                                            new.theta.out$exps2[j,1:TT_sub], 
                                            new.sts.out$E.sts[j,], 
                                            new.sts.out$E.sts2[j,], 
                                            new.uts.out$E.uts[j,], 
                                            new.uts.out$E.inv.uts[j,],
                                            cur.gamsig.out$E.sigma[j,], 
                                            cur.gamsig.out$E.gam[j,],
                                            FALSE,
                                            context_label = sprintf("sampling j=%d climate_center=FALSE", j))    
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
        ########################
        ########################
        theta_s <- gamsig.dummy$E.theta[1]
        theta_g <- gamsig.dummy$E.theta[2]
        # Normal Aproximation
        samp.LD <- rmvnorm(n = n.samp, mean = c(theta_s, theta_g), sigma = gamsig.dummy$Hess.LD)
        pi_gamma <- plogis(samp.LD[,2])
        pi_gamma <- pmin(pmax(pi_gamma, 1e-12), 1 - 1e-12)
        samp.gamma[j,] = L + (U - L) * pi_gamma
        samp.sigma[j,] = exp(samp.LD[,1]) 
        ########################
        ########################
    }else{
        k_forecast <- ranges[j-1]
        for (i in 1:num_mem[j-1]) {
            
        sts.dummy <- update_sts(
                        y = matrix(ensembles[[j-1]][,i], ncol=1), 
                        exps = matrix(new.theta.out$exps[j,(TT_sub+1):(TT_sub+k_forecast)], ncol=1), 
                        inv.uts = matrix(cur.uts.out_f$E.inv.uts[[j-1]][,i], ncol=1), 
                        c2.invb.absgam2.sigma = cur.gamsig.out$E.c2.invb.absgam2.sigma[j,], 
                        c.invb.absgam = cur.gamsig.out$E.c.invb.absgam[j,], 
                        c.a.invb.absgam = cur.gamsig.out$E.c.a.invb.absgam[j,], 
                        k_forecast)

        new.sts.out_f$E.sts[[j-1]][,i] <- sts.dummy$E.sts
        new.sts.out_f$E.sts2[[j-1]][,i] <- sts.dummy$E.sts2
        new.sts.out_f$tot.entrop[[j-1]][i] <-  sts.dummy$tot.entrop

        uts.dummy <- update_uts(
                        y = matrix(ensembles[[j-1]][,i], ncol=1),
                        exps = matrix(new.theta.out$exps[j,(T+1):(T+k_forecast)], ncol=1), 
                        exps2 = matrix(new.theta.out$exps2[j,(T+1):(T+k_forecast)], ncol=1), 
                        new.sts.out_f$E.sts[[j-1]][,i], 
                        new.sts.out_f$E.sts2[[j-1]][,i], 
                        cur.gamsig.out$E.inv.sigma[j,], 
                        cur.gamsig.out$E.a2.invb.inv.sigma[j,], 
                        cur.gamsig.out$E.invb.inv.sigma[j,], 
                        cur.gamsig.out$E.c.invb.absgam[j,], 
                        cur.gamsig.out$E.c2.invb.absgam2.sigma[j,]) 
                        
        new.uts.out_f$E.uts[[j-1]][,i] <- uts.dummy$E.uts
        new.uts.out_f$E.inv.uts[[j-1]][,i] <- uts.dummy$E.inv.uts
        new.uts.out_f$E.log.uts[[j-1]][i] <- uts.dummy$E.log.uts
        new.uts.out_f$tot.entrop[[j-1]][i] <- uts.dummy$tot.entrop
        ########################
        ########################
        ########################
        ########################
        # Generalized Inverse Gausian Sampling
        samp.uts_ens[[j-1]][,i,]  = t(sample_gig_devroye_vector(n.samp, uts.dummy$uts.lambda, uts.dummy$uts.psi, uts.dummy$uts.chi))
        # Truncated normal
        samp.sts_ens[[j-1]][,i,]  = t(sample_truncnorm_icdf(n.samp, k_forecast, sts.dummy$sts.mu, sts.dummy$sts.sig2) )
        ########################
        ########################
        ########################
        ########################
        }

    }
}

    for (j in 2:(J+1)) {  
        k_forecast <- ranges[j-1]
        gamsig.dummy <- update_gamma_sigma(Y[j,], TT_sub,
                                            PriorGamma[j,],
                                            PriorSigma[j,],
                                            cur.gamsig.out$E.gam[j,], 
                                            cur.gamsig.out$V.gam[j,], 
                                            cur.gamsig.out$E.sigma[j,], 
                                            cur.gamsig.out$V.sigma[j,], 
                                            new.theta.out$exps[j,], 
                                            new.theta.out$exps2[j,], 
                                            new.sts.out$E.sts[j,], 
                                            new.sts.out$E.sts2[j,], 
                                            new.uts.out$E.uts[j,], 
                                            new.uts.out$E.inv.uts[j,],
                                            cur.gamsig.out$E.sigma[j,], 
                                            cur.gamsig.out$E.gam[j,],
                                            TRUE ,
                                            ensembles[[j-1]], 
                                            num_mem[j-1], 
                                            k_forecast,
                                            new.sts.out_f$E.sts[[j-1]],
                                            new.sts.out_f$E.sts2[[j-1]],
                                            new.uts.out_f$E.uts[[j-1]],
                                            new.uts.out_f$E.inv.uts[[j-1]],
                                            context_label = sprintf("sampling j=%d climate_center=TRUE", j))

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
        ########################
        theta_s <- gamsig.dummy$E.theta[1]
        theta_g <- gamsig.dummy$E.theta[2]
        ########################
        ########################
        ########################
        ########################
        # Normal Aproximation
        samp.LD <- rmvnorm(n = n.samp, mean = c(theta_s, theta_g), sigma = gamsig.dummy$Hess.LD)
        pi_gamma <- plogis(samp.LD[,2])
        pi_gamma <- pmin(pmax(pi_gamma, 1e-12), 1 - 1e-12)
        samp.gamma[j,] = L + (U - L) * pi_gamma
        samp.sigma[j,] = exp(samp.LD[,1]) 
        ########################
        ########################
        ########################
        ########################
}

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

print(c(n.samp))
flush.console()
run.time = tictoc::toc(quiet = TRUE)
########################
if (verbose) {
  cat(sprintf("Sampling finished:  %s seconds", round(run.time$toc - run.time$tic, 3)), "\n")
}

########################

if (verbose) {
  cat(sprintf("Sampling finished:  %s seconds", round(run.time$toc - run.time$tic, 3)), "\n")
}

disc_w_save_state(p0 = p0, ending = ending, disc_w_paths = disc_w_paths)
}

errors <- new.theta.out$standard_forecast_errors
s <- 0.5*(compute_kl_divergence(t(errors))+estimate_kl_divergence(t(errors)))
######################

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

js_divergence <- compute_jsd(t(errors), gridsize = c(100, 100, 100))

######################
######################
######################
print(c(js_divergence, s, elbo, delta))
flush.console()

if (is.nan(s)) {
  print("Assigning Inf to NaN")
  flush.console()
  s <- Inf
}

if (is.nan(js_divergence)) {
  print("Assigning Inf to NaN")
  flush.console()
  js_divergence <- Inf
}

return(js_divergence)
######################
######################
######################
} 

############################################################################################################
############################################################################################################
############# (Discrep, Mem for Trans, Cov, Trans rate, Mem for Forecast)   
# lower_bounds <- c(0.999, 0.01)   
# initial_delta <- c(0.999,0.9999)

initial_delta   <- c(0.9999995, 0.9997, 0.9997, 0.9997, 0.999, 0.8995)
# initial_delta <- c(df_t  , df_s1 , df_s2 , df_s67, df.discrep, lambda)

upper_bounds <- c(rep(0.985, (length(initial_delta)-1)), 1.0e-6)   
upper_bounds <- rep(0.9999999, length(initial_delta))  

# -2416.920
# -2427.511


opts <- list("algorithm" = "NLOPT_LN_BOBYQA",  # Using a derivative-free algorithm
             "xtol_rel" = 1.0e-6,
             "maxeval" = 1000)

objective_deltas_min <- function(delta) {
  objective_deltas(delta, TRUE, TRUE)  # Minimize the negative of the original function
}

# result <- nloptr(x0 = initial_delta,
#                  eval_f = objective_deltas_min,  # Objective function
#                  lb = lower_bounds,
#                  ub = upper_bounds,
#                  opts = opts)
# d = as.numeric(c(result$solution))
# print(result)                                

d <- initial_delta
objective_deltas(d, TRUE, TRUE);
###########################################################################################################################
