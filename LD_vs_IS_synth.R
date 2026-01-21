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
# Function to check if a matrix is positive definite
is.positive.definite <- function(x) {
  eigenvalues <- eigen(x)$values
  return(all(eigenvalues > 0))
}

# Function to estimate the percentile
estimate_percentile <- function(n, percentile, dist_name, mean_norm, sd_norm, param1, param2) {
  # Define the number of cores to use
  no_cores <- detectCores() - 1
  cl <- makeCluster(no_cores)
  
  # Export the necessary variables to the cluster
  clusterExport(cl, c("n", "dist_name", "mean_norm", "sd_norm", "param1", "param2"))
  
  # Parallel computation
  sum_samples <- parLapply(cl, 1:no_cores, function(x) {
    set.seed(x)  # For reproducibility in each core
    samples_per_core <- n / no_cores
    
    # Normal distribution samples
    norm_samples <- rnorm(samples_per_core, mean = mean_norm, sd = sd_norm)
    
    # Second distribution samples
    if (dist_name == "gamma") {
      second_samples <- rgamma(samples_per_core, shape = param1, rate = param2)
    } else if (dist_name == "cauchy") {
      second_samples <- rcauchy(samples_per_core, location = param1, scale = param2)
    } else if (dist_name == "normal") {
      second_samples <- rnorm(samples_per_core, mean = param1, sd = param2)
    } else {
      stop("Unsupported distribution name")
    }
    
    # Sum of samples
    sum_samples <- norm_samples + second_samples
    return(sum_samples)
  })
  
  stopCluster(cl)
  
  # Combine the results from each core and estimate the percentile
  all_sums <- unlist(sum_samples)
  percentile_value <- quantile(all_sums, probs = percentile)
  
  return(percentile_value)
}


generateCombinedFtGt <- function(poly_order, periodicity, harmonics) {
  # Generate trend component using dlmModPoly
  trendModel <- dlmModPoly(order = poly_order)
  F_trend <- trendModel$FF
  G_trend <- trendModel$GG
  
  # Adjusted generation of seasonal F_t and G_t for specified harmonics
  alpha <- 2 * pi / periodicity
  F_seasonal <- matrix(nrow = 1, ncol = length(harmonics) * 2) # Adjust size based on harmonics
  G_seasonal <- matrix(0, nrow = length(harmonics) * 2, ncol = length(harmonics) * 2)
  
  for (i in 1:length(harmonics)) {
    harmonicIndex <- harmonics[i]
    angle <- alpha * harmonicIndex
    F_seasonal[1, (i * 2 - 1)] <- 1 # Cosine component always observed
    F_seasonal[1, i * 2] <- ifelse(harmonicIndex == periodicity / 2, NA, 0) # Sine component, NA for largest harmonic
    G_seasonal[(i * 2 - 1):(i * 2), (i * 2 - 1):(i * 2)] <- matrix(c(cos(angle), sin(angle), -sin(angle), cos(angle)), nrow = 2)
  }
  
  # Handling NA in F_seasonal to ensure correct pattern
  F_seasonal <- F_seasonal[!is.na(F_seasonal)]
  F_seasonal <- matrix(F_seasonal, nrow = 1)
  
  # Combine F_trend and F_seasonal into a single F
  F_combined <- cbind(F_trend, F_seasonal)
  
  # Combine G_trend and G_seasonal into a single G using block-diagonal structure
  G_combined <- bdiag(list(G_trend, G_seasonal))
  
  return(list(F_t = F_combined, G_t = G_combined))
}
set.seed(161) # For reproducibility

n <- 5000  # Total length of the time series
m <- 1000   # Number of observations to store
poly_order <- 2 # Polynomial trend order
harmonics <- c(1, 2, 3) # Specified harmonics for the seasonal component
periodicity <- 365 # Periodicity of the seasonal component
quantiles <- c(0.1, 0.5, 0.95)

obs_sd <- 5*1e+2
ev_sd <- 1e+1

# Run simulation for all distributions at once
#simulation_results <- simulate_DLM_q_mod(n, m, 
#                                        poly_order, harmonics, periodicity, 
#                                        qs = quantiles,
#                                        obs_sd, ev_sd)


# Save the ts_standardized_results object to a file
#saveRDS(ts_standardized_results, file = "ts_standardized_results.rds")
# Load the ts_standardized_results object from the file
ts_standardized_results <- readRDS(file = "ts_standardized_results.rds")


p0_values <- quantiles

df1 <- 0.9999
df2 <- 0.9985
dim_df <- c(2, 6)
sig_init <- 1
gam_init <- 0
tol <- 1e-4
verbose <- TRUE

# Assuming ts_standardized_results contains the "sn" observed data
ts_data_sn <- ts_standardized_results[["sn"]]$ts

par(mfrow = c(1, 1))

for (p0 in p0_values) {
  model_fit <- fit_exdqlmISVB123_LD(p0)
    
  # Plotting each model's fit along with the observed and true quantiles
  plot_quantiles_and_model_fit(model_fit)
  
  # Plotting sequence plots for gamma and sigma
  plot_sequence(model_fit)
}

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


exdqlmISVB123 <-function(y,p0,model,df,dim.df,fix.gamma=FALSE,gam.init=NA,fix.sigma=TRUE,sig.init=NA,dqlm.ind=FALSE,
                     exps0,tol=0.1,n.IS=500,n.samp=200,PriorSigma=NULL,PriorGamma=NULL,verbose=TRUE){

  # check inputs
  y = check_ts(y)
  model = check_mod(model)
  rv = check_logics(gam.init,sig.init,fix.gamma,fix.sigma,dqlm.ind)
  gam.init = rv$gam.init
  dqlm.int = rv$dqlm.ind
  fix.gamma = rv$fix.gamma

  ### Define L and U
  L = L.fn(p0); U = U.fn(p0)
  if(!is.na(gam.init)){
    if(gam.init < L | gam.init > U){
      stop(sprintf("gam.init must be between %s and %s for %s quantile",round(L,3),round(U,3),p0))
    }
  }

  ### sigma and gamma priors
  # sigma ~ IG(a_sig,b_sig)
  if(is.null(PriorSigma)){
    m_sigma = 1
    v_sigma = 10
    PriorSigma$a_sig = (m_sigma^2)/(v_sigma) + 2
    PriorSigma$b_sig = (m_sigma^3)/(v_sigma) + m_sigma
  }else{
    if(!is.list(PriorSigma) | any( is.na( match(c("a_sig", "b_sig"),names(PriorSigma)) ) )){
      stop("`PriorSigma` must be a list containing `a_sig` and `b_sig`")
      }
  }
  # gamma ~ truncated student t on L,U
  if(is.null(PriorGamma)){
    PriorGamma$m_gam = 0
    PriorGamma$s_gam = 1
    PriorGamma$df_gam = 1
   }else{
     if(!is.list(PriorGamma) | any( is.na( match(c("m_gam", "s_gam", "df_gam"),names(PriorGamma)) ) )){
       stop("`PriorGamma` must be a list containing `m_gam`,`s_gam`, and `df_gam`")
     }
   }
  PriorGammaDens<-function(gamma){ crch::dtt(gamma,location = PriorGamma$m_gam, scale = PriorGamma$s_gam, df = PriorGamma$df_gam, left = L, right = U, log = FALSE) }

  ### state-space model
  ## prior, theta ~ N(m0,C0)
  m0 = model$m0
  C0 = model$C0
  #
  TT = length(y)
  p = length(m0)
  if(!is.na(dim(model$GG)[3])){
    if(dim(model$GG)[3] != TT){stop("time-varying dimension of GG does not match length of y")}
  }
  GG = array(model$GG,c(p,p,TT)); model$GG = GG
  if(ncol(model$FF)>1){
    if(ncol(model$FF) != TT){stop("time-varying dimension of FF does not match length of y")}
  }
  FF = matrix(model$FF,p,TT); model$FF = FF
  ## discount factor blocking
  if(!methods::hasArg(dim.df)){
    if(length(df)!=1){
      stop("length of component discount factors does not match length of component dimensions")
    }
    dim.df = p
  }
  df.mat = make_df_mat(df,dim.df,p)

  ### Initialize VB
  gam0 = ifelse(!is.na(gam.init),gam.init,(L+U)/2)
  sig0 = ifelse(!is.na(sig.init),sig.init,1)
  new.gamsig.out = list(E.gam=gam0,V.gam=10,
                        E.sigma=ifelse(!is.na(sig0),sig0,m_sigma),V.sig=10,
                        E.inv.sigma=ifelse(!is.na(sig0),1/sig0,1/m_sigma),
                        E.c2.invb.absgam2.sigma = sig0*(C.fn(p0,gam0)^2)*(abs(gam0)^2)/B.fn(p0,gam0),
                        E.c.invb.absgam = C.fn(p0,gam0)*abs(gam0)/B.fn(p0,gam0),
                        E.c.a.invb.absgam = C.fn(p0,gam0)*A.fn(p0,gam0)*abs(gam0)/B.fn(p0,gam0),
                        E.a2.invb.inv.sigma = (A.fn(p0,gam0)^2)/(B.fn(p0,gam0)*sig0),
                        E.invb.inv.sigma = 1/(sig0*B.fn(p0,gam0)),
                        E.a.invb.inv.sigma = A.fn(p0,gam0)/(B.fn(p0,gam0)*sig0))
  new.sts.out = list(E.sts=rep(truncnorm::etruncnorm(a=0,b=Inf,mean=1,sd=1),TT),
                     E.sts2=rep(truncnorm::etruncnorm(a=0,b=Inf,mean=1,sd=1)^2+truncnorm::vtruncnorm(a=0,b=Inf,mean=1,sd=1),TT))
  new.uts.out = list(E.uts=rep(1/sig0,TT),
                     E.inv.uts=rep(sig0,TT))
  if(methods::hasArg(exps0)){
    if(length(exps0) != TT){ stop("exps0 must have same length as y") }
  }else{
    init.dlm = dlm_df(y,model,df,dim.df,s.priors=list(l0=1,S0=sig0),just.lik=FALSE)
    exps0 = apply(FF*t(init.dlm$m),2,sum) + stats::qnorm(p0,0,sqrt(init.dlm$s[TT]))
  }
  new.theta.out = list(exps=exps0,exps2=exps0^2)

  ### initialize convergence evaluations
  iter = 0
  conv.count = 0
  new.max = Inf
  seq.gamma = new.gamsig.out$E.gam
  seq.sigma = new.gamsig.out$E.sigma

  # function update q(st)
  update_sts<-function(exps,inv.uts,c2.invb.absgam2.sigma,c.invb.absgam,c.a.invb.absgam){
    s.sig2<-1/(1+c2.invb.absgam2.sigma*inv.uts); s.sig = sqrt(s.sig2)
    s.mu<-s.sig2*(c.invb.absgam*(y-exps)*inv.uts-c.a.invb.absgam)
    #
    E.sts = truncnorm::etruncnorm(a=rep(0,TT),b=rep(Inf,TT),mean=s.mu,sd=s.sig)
    V.sts = truncnorm::vtruncnorm(a=rep(0,TT),b=rep(Inf,TT),mean=s.mu,sd=s.sig)
    E.sts2 = s.mu^2 + s.sig2 + s.mu*s.sig*exp(stats::dnorm(-s.mu/s.sig,log = TRUE)-stats::pnorm(s.mu/s.sig,log.p = TRUE))
    return(list(sts.sig2=s.sig2,sts.mu=s.mu,
                E.sts=E.sts,E.sts2=E.sts2))
  }

  # function update q(ut)
  update_uts<-function(exps,exps2,sts,sts2,inv.sigma,a2.invb.inv.sigma,invb.inv.sigma,c.invb.absgam,c2.invb.absgam2.sigma){
    u.lambda = 0.5
    u.psi = (a2.invb.inv.sigma + 2*inv.sigma)
    u.chi = invb.inv.sigma*(y^2-2*y*exps+exps2) - 2*c.invb.absgam*sts*(y-exps) + c2.invb.absgam2.sigma*sts2
    u.chi[u.chi<=0] = 1e-3
    #
    E.uts = sapply(u.chi,function(x){sqrt(x/u.psi)*HyperbolicDist::besselRatio(sqrt(x*u.psi),u.lambda,1,Inf)})
    E.inv.uts = sapply(u.chi,function(x){sqrt(u.psi/x)*HyperbolicDist::besselRatio(sqrt(x*u.psi),u.lambda,1,Inf)-2*u.lambda/x})
    return(list(uts.lambda=u.lambda,uts.psi=u.psi,uts.chi=u.chi,E.uts=E.uts,E.inv.uts=E.inv.uts))
  }

  # function update q(theta) ffbsm
  update_theta<-function(ex.f,ex.q){
    # initialize ffbs
    m <- sm <- matrix(NA,p,TT)
    C <- sC <- array(NA,c(p,p,TT))
    standard.forecast.errors <- rep(NA,TT)
    ## forward filter
    # first iteration
    a = as.vector(GG[,,1]%*%m0)
    P = GG[,,1]%*%C0%*%t(GG[,,1])
    R = P + df.mat*P
    R = (R + t(R))/2
    f = t(FF[,1])%*%a + ex.f[1]
    q = t(FF[,1])%*%R%*%FF[,1]  + ex.q[1]
    m[,1] = a + t(R)%*%FF[,1]%*%(y[1]-f)/q[1]
    C[,,1] = R - t(R)%*%FF[,1]%*%t(FF[,1])%*%R/q[1]
    C[,,1] = (C[,,1] + t(C[,,1]))/2
    standard.forecast.errors[1] = (y[1]-f)/sqrt(q)
    # t = 2:TT
    for(t in 2:TT){
      a = as.vector(GG[,,t]%*%m[,(t-1)])
      P = GG[,,t]%*%C[,,(t-1)]%*%t(GG[,,t])
      R = P + df.mat*P
      R = (R + t(R))/2
      f = t(FF[,t])%*%a + ex.f[t]
      fB = t(FF[,t])%*%R
      q = fB%*%FF[,t] + ex.q[t]
      m[,t] = a + t(fB)%*%(y[t]-f)/q[1]
      C[,,t] = R - t(fB)%*%fB/q[1]
      C[,,t] = (C[,,t] + t(C[,,t]))/2
      standard.forecast.errors[t] = (y[t]-f)/sqrt(q)
    }
    ## backwards smoothing
    sC[,,TT] = C[,,TT]
    sm[,TT] = m[,TT]
    for(t in (TT-1):1){
      P = GG[,,(t+1)]%*%C[,,(t)]%*%t(GG[,,(t+1)])
      R = P + df.mat*P
      R = (R + t(R))/2
      svd.R = svd(R)
      inv.R = svd.R$u%*%diag(1/svd.R$d,p)%*%t(svd.R$u)
      sB = C[,,t]%*%t(GG[,,t])%*%inv.R
      sm[,t] = m[,t] + sB%*%(sm[,(t+1)]-as.vector(GG[,,(t+1)]%*%m[,(t)]))
      sC[,,t] = C[,,t] + sB%*%(sC[,,(t+1)]-R)%*%t(sB)
      sC[,,t] = (sC[,,t]+t(sC[,,t]))/2
    }
    exps =  apply(FF*sm,2,sum)
    vars = c(apply(matrix(1:TT,TT,1),1,function(x){t(FF[,x])%*%sC[,,x]%*%FF[,x]}))
    exps2 = exps^2 + vars
    return(list(exps=exps,vars=vars,exps2=exps2,standard.forecast.errors=standard.forecast.errors,sm=sm,sC=sC,fm=m,fC=C))
  }

  # function approximate q(sigma,gamma) with importance sampling
  update_gamma_sigma<-function(gamma,var.gam,sigma,var.sig,exps,exps2,sts,sts2,uts,inv.uts){
    gam.sig2 = max(var.gam,0.001)
    gam.mu = gamma
    v_sig = max(var.sig,0.001)
    m_sig = sigma
    # sampling distribution functions
    rr_gamma = function(n){
      return(crch::rtt(n, location = gam.mu, scale = sqrt(gam.sig2), df = 1, left = L+1e-3, right = U-1e-3))
    }
    dr_gamma = function(gam,log.ind=FALSE){
      return(crch::dtt(gam, location = gam.mu, scale = sqrt(gam.sig2), df = 1, left = L+1e-3, right = U-1e-3,log = log.ind))
    }
    rr_sigma = function(n){
      return(crch::rtt(n, location = m_sig, scale = sqrt(v_sig), df = 1, left = 0, right = Inf))
    }
    dr_sigma = function(sig,log.ind=FALSE){
      return(crch::dtt(sig, location = m_sig, scale = sqrt(v_sig), df = 1, left = 0, right = Inf, log = log.ind))
    }
    # variational function q(gamma,sigma) up to proportionality constant
    dq = function(sig,gam,log.ind=FALSE){
      a = A.fn(p0,gam); b = B.fn(p0,gam); c = C.fn(p0,gam);
      if(log.ind==FALSE){
        q.prior <- PriorGammaDens(gam)*(sig^(-PriorSigma$a_sig-1))*exp(-PriorSigma$b_sig/sig)
        q.lik = ((sig*b)^(-1.5*TT))*exp(-sum(uts)/sig)*
          exp( -0.5*sum( inv.uts*(y^2-2*y*exps+exps2)/sig
                         + (exps-y)*2*(inv.uts*c*abs(gam)*sts + a/sig)
                         + sig*inv.uts*(c^2)*(abs(gam)^2)*sts2
                         + 2*c*abs(gam)*sts*a
                         + (uts*a^2)/sig )/b )
        return(q.prior*q.lik)
      }else{
        log.q.prior <- log(PriorGammaDens(gam)) -(PriorSigma$a_sig+1)*log(sig)-PriorSigma$b_sig/sig
        log.q.lik = - (1.5*TT)*log(sig*b)-sum(uts)/sig -
          0.5*sum( inv.uts*(y^2-2*y*exps+exps2)/sig
                   + (exps-y)*2*(inv.uts*c*abs(gam)*sts + a/sig)
                   + sig*inv.uts*(c^2)*(abs(gam)^2)*sts2
                   + 2*c*abs(gam)*sts*a
                   + (uts*a^2)/sig )/b
        return(log.q.prior+log.q.lik)
      }
    }
    # importance sampling
    # sample sigma
    if(!fix.sigma){
      sigma.samples = rr_sigma(n.IS)
    }else{
      sigma.samples = rep(sig.init,n.IS)
    }
    # sample gamma
    if(!fix.gamma){
      gamma.samples = rr_gamma(n.IS)
    }else{
      gamma.samples = rep(gam.init,n.IS)
    }
    # compute weights
    if(fix.gamma && fix.sigma){
      weights = rep(1/n.IS,n.IS)
    }else{
      log.weights = apply(cbind(sigma.samples,gamma.samples),1,function(x){dq(x[1],x[2],log.ind=TRUE)}) -
        as.numeric(!fix.gamma)*dr_gamma(gamma.samples,log.ind=TRUE) - as.numeric(!fix.sigma)*dr_sigma(sigma.samples,log.ind = TRUE)
      max.log.weight = max(log.weights)
      log.sum.weights = max(log.weights) + log(sum(exp(log.weights-max.log.weight)))
      log.rescaled.weights = log.weights - log.sum.weights
      weights = exp(log.rescaled.weights)
    }
    # compute expectations
    E.gam = sum(gamma.samples*weights)
    V.gam = sum((gamma.samples^2)*weights) - E.gam^2
    E.sigma = sum(sigma.samples*weights)
    V.sigma = sum((sigma.samples^2)*weights) - E.sigma^2
    E.inv.sigma = sum((1/sigma.samples)*weights)
    E.c2.invb.absgam2.sigma = sum(((sigma.samples*(C.fn(p0,gamma.samples)^2)*(abs(gamma.samples)^2))/B.fn(p0,gamma.samples))*weights)
    E.c.invb.absgam = sum(((C.fn(p0,gamma.samples)*abs(gamma.samples))/B.fn(p0,gamma.samples))*weights)
    E.c.a.invb.absgam = sum(((C.fn(p0,gamma.samples)*A.fn(p0,gamma.samples)*abs(gamma.samples))/B.fn(p0,gamma.samples))*weights)
    E.a2.invb.inv.sigma = sum(((A.fn(p0,gamma.samples)^2)/(B.fn(p0,gamma.samples)*sigma.samples))*weights)
    E.invb.inv.sigma = sum((1/(B.fn(p0,gamma.samples)*sigma.samples))*weights)
    E.a.invb.inv.sigma = sum((A.fn(p0,gamma.samples)/(B.fn(p0,gamma.samples)*sigma.samples))*weights)
    E.log.inv.sigma = sum(log(1/sigma.samples)*weights)

    return(list(E.sigma=E.sigma,V.sigma=V.sigma,E.inv.sigma=E.inv.sigma,E.gam=E.gam,V.gam=V.gam,
                sigma.samples=sigma.samples,gamma.samples=gamma.samples,weights=weights,
                E.c2.invb.absgam2.sigma = E.c2.invb.absgam2.sigma, E.c.invb.absgam = E.c.invb.absgam,
                E.c.a.invb.absgam = E.c.a.invb.absgam, E.a2.invb.inv.sigma = E.a2.invb.inv.sigma,
                E.invb.inv.sigma = E.invb.inv.sigma, E.a.invb.inv.sigma = E.a.invb.inv.sigma,
                E.log.inv.sigma=E.log.inv.sigma))
  }

  tictoc::tic("run time")
  ### estimate posterior
  while( new.max > tol || conv.count < 5 || iter < 15){

    # counter
    iter = iter + 1
    if(verbose & iter%%5==0){
      cat(sprintf("ISVB iteration %s: %s", iter, Sys.time() ),"\n")
    }

    # update distributions
    cur.uts.out = new.uts.out
    cur.sts.out = new.sts.out
    cur.theta.out = new.theta.out
    cur.gamsig.out = new.gamsig.out

    # update q(st)
    new.sts.out <- update_sts(cur.theta.out$exps,cur.uts.out$E.inv.uts,
                              cur.gamsig.out$E.c2.invb.absgam2.sigma,cur.gamsig.out$E.c.invb.absgam,cur.gamsig.out$E.c.a.invb.absgam)

    # update q(ut)
    new.uts.out <- update_uts(cur.theta.out$exps,cur.theta.out$exps2,
                              new.sts.out$E.sts,new.sts.out$E.sts2,
                              cur.gamsig.out$E.inv.sigma,cur.gamsig.out$E.a2.invb.inv.sigma,cur.gamsig.out$E.invb.inv.sigma,
                              cur.gamsig.out$E.c.invb.absgam,cur.gamsig.out$E.c2.invb.absgam2.sigma)

    # update q(theta)
    new.theta.out <- update_theta(cur.gamsig.out$E.c.invb.absgam*new.sts.out$E.sts/cur.gamsig.out$E.invb.inv.sigma +
                                    cur.gamsig.out$E.a.invb.inv.sigma/(new.uts.out$E.inv.uts*cur.gamsig.out$E.invb.inv.sigma),
                                  (cur.gamsig.out$E.invb.inv.sigma*new.uts.out$E.inv.uts)^(-1) )

    # update q(gamma,sigma)
    new.gamsig.out<-update_gamma_sigma(cur.gamsig.out$E.gam,cur.gamsig.out$V.gam,
                                       cur.gamsig.out$E.sigma,cur.gamsig.out$V.sigma,
                                       new.theta.out$exps,new.theta.out$exps2,
                                       new.sts.out$E.sts,new.sts.out$E.sts2,
                                       new.uts.out$E.uts,new.uts.out$E.inv.uts)

    # save ISVB gamma and sigma estimates
    seq.gamma = c(seq.gamma,new.gamsig.out$E.gam)
    seq.sigma = c(seq.sigma,new.gamsig.out$E.sigma)

    # evaluate convergence
    # new.max = max(abs(c(cur.theta.out$exps-new.theta.out$exps)))
    new.max = sum(abs(new.gamsig.out$E.gam-cur.gamsig.out$E.gam))
    conv.count = ifelse(new.max < tol, conv.count + 1, 0)

  }
  run.time = tictoc::toc(quiet = TRUE)
  if(verbose){
    cat(sprintf("ISVB converged: %s iterations, %s seconds",iter,round(run.time$toc-run.time$tic,3)),"\n")
  }

  ### posterior samples
  # gamma and sigma
  samp.index = sample(1:n.IS,n.samp,replace=TRUE,prob=new.gamsig.out$weights)
  samp.gamma = new.gamsig.out$gamma.samples[samp.index]
  samp.sigma = new.gamsig.out$sigma.samples[samp.index]
  # uts, sts, thetas, and predicive distribution samples
  samp.uts = t(sapply(1:TT,function(t){GeneralizedHyperbolic::rgig(n.samp,chi=new.uts.out$uts.chi[t],psi=new.uts.out$uts.psi,lambda=new.uts.out$uts.lambda)}))
  samp.sts = t(sapply(1:TT,function(t){truncnorm::rtruncnorm(n.samp,a=rep(0,n.samp),b=rep(Inf,n.samp),mean=new.sts.out$sts.mu[t],sd=sqrt(new.sts.out$sts.sig2[t]))}))
  samp_theta_t = function(t){
    svd.sC = svd(new.theta.out$sC[,,t]); LL = svd.sC$u%*%diag(sqrt(svd.sC$d),p)
    new.theta.out$sm[,t] + LL%*%matrix(stats::rnorm(n.samp*p,0,1),p,n.samp)}
  samp_post_pred_t = function(t){
    brms::rasym_laplace(1,colSums(matrix(FF[,t],p,n.samp)*samp.theta[,t,])+
                    samp.sigma*C.fn(p0,samp.gamma)*abs(samp.gamma)*samp.sts[t,],samp.sigma,p.fn(p0,samp.gamma))}
  samp.theta = array(NA,c(p,TT,n.samp))
  samp.post.pred = matrix(NA,TT,n.samp)
  for(t in 1:TT){samp.theta[,t,] = samp_theta_t(t); samp.post.pred[t,] = samp_post_pred_t(t)}

  ### list results
  if(!dqlm.ind){
    retlist = list(run.time=(run.time$toc-run.time$tic),iter=iter,dqlm.ind=dqlm.ind,
                   model=model,p0=p0,df=df,dim.df=dim.df,
                   sig.init=sig.init,seq.sigma=seq.sigma,gam.init=gam.init,seq.gamma=seq.gamma,
                   samp.theta=samp.theta,samp.post.pred=samp.post.pred,
                   map.standard.forecast.errors=new.theta.out$standard.forecast.errors,
                   samp.sigma=samp.sigma,samp.gamma=samp.gamma,samp.sts=samp.sts,samp.vts=samp.uts,
                   theta.out=new.theta.out,gammasig.out=new.gamsig.out,sts.out=new.sts.out,vts.out=new.uts.out)
  }else{
    retlist = list(run.time=(run.time$toc-run.time$tic),iter=iter,dqlm.ind=dqlm.ind,
                   model=model,p0=p0,df=df,dim.df=dim.df,
                   sig.init=sig.init,seq.sigma=seq.sigma,
                   samp.theta=samp.theta,samp.post.pred=samp.post.pred,
                   map.standard.forecast.errors=new.theta.out$standard.forecast.errors,
                   samp.sigma=samp.sigma,samp.vts=samp.uts,
                   theta.out=new.theta.out,sig.out=new.gamsig.out,vts.out=new.uts.out)
  }
  # return results
  class(retlist) <- "exdqlm"
  return(retlist)
}



p0 <- 0.5  # Focusing on the 50th quantile
# Model components
trend.comp <- polytrendMod(poly_order)
seas.comp <- seasMod(p = periodicity, h = harmonics)
model <- combineMods(trend.comp, seas.comp)

# Model fitting
sn_model_50th <- exdqlmISVB123(y = ts_data_sn, p0 = p0, model = model,
                               df = c(df1, df2), dim.df = dim_df,
                               sig.init = sig_init, gam.init = gam_init,
                               tol = tol, verbose = verbose)

# Plotting the "sn" quantiles for visual analysis
if ("sn" %in% names(ts_standardized_results) && !is.null(ts_standardized_results[["sn"]]$qs)) {
  plot(ts_standardized_results[["sn"]]$ts, type = "l", col = "gray", main = "Skewed Normal Observational Errors", xlab = "Time", ylab = "Standardized Value")
  
  colors <- c('darkred', 'forestgreen', 'darkblue')  # Assuming the order is 95th, 50th, and 10th percentiles
  legends <- c("95th Percentile", "50th Percentile", "10th Percentile")
  
  for (i in seq_along(ts_standardized_results[["sn"]]$qs)) {
    lines(ts_standardized_results[["sn"]]$qs[[i]], col = colors[i])
  }
  
  legend("topleft", legend = legends, col = colors, lty = 1, cex = 0.8)
} else {
  print("Quantiles for 'sn' observations are not available in ts_standardized_results.")
}


# Overlay the fitted model results for the 50th quantile
exdqlmPlot(y = ts_data_sn, sn_model_50th, add = TRUE, col = "orange")                               

plot.ts(sn_model_50th$seq.gamma)
plot.ts(sn_model_50th$seq.sigma)

##########################################################################################################




p0 <- 0.95  # Focusing on the 50th quantile


# Model components
trend.comp <- polytrendMod(poly_order)
seas.comp <- seasMod(p = periodicity, h = harmonics)
model <- combineMods(trend.comp, seas.comp)

# Model fitting
sn_model_95th <- exdqlmISVB123(y = ts_data_sn, p0 = p0, model = model,
                               df = c(df1, df2), dim.df = dim_df,
                               sig.init = sig_init, gam.init = gam_init,
                               tol = tol, verbose = verbose)

# Plotting the "sn" quantiles for visual analysis
if ("sn" %in% names(ts_standardized_results) && !is.null(ts_standardized_results[["sn"]]$qs)) {
  plot(ts_standardized_results[["sn"]]$ts, type = "l", col = "gray", main = "Skewed Normal Observational Errors", xlab = "Time", ylab = "Standardized Value")
  
  colors <- c('darkred', 'forestgreen', 'darkblue')  # Assuming the order is 95th, 50th, and 10th percentiles
  legends <- c("95th Percentile", "50th Percentile", "10th Percentile")
  
  for (i in seq_along(ts_standardized_results[["sn"]]$qs)) {
    lines(ts_standardized_results[["sn"]]$qs[[i]], col = colors[i])
  }
  
  legend("topleft", legend = legends, col = colors, lty = 1, cex = 0.8)
} else {
  print("Quantiles for 'sn' observations are not available in ts_standardized_results.")
}


# Overlay the fitted model results for the 50th quantile
exdqlmPlot(y = ts_data_sn, sn_model_95th, add = TRUE, col = "orange")                               

plot.ts(sn_model_95th$seq.gamma)
plot.ts(sn_model_95th$seq.sigma)



p0 <- 0.1  # Focusing on the 50th quantile


# Model components
trend.comp <- polytrendMod(poly_order)
seas.comp <- seasMod(p = periodicity, h = harmonics)
model <- combineMods(trend.comp, seas.comp)

# Model fitting
sn_model_10th <- exdqlmISVB123(y = ts_data_sn, p0 = p0, model = model,
                               df = c(df1, df2), dim.df = dim_df,
                               sig.init = sig_init, gam.init = gam_init,
                               tol = tol, verbose = verbose)

# Plotting the "sn" quantiles for visual analysis
if ("sn" %in% names(ts_standardized_results) && !is.null(ts_standardized_results[["sn"]]$qs)) {
  plot(ts_standardized_results[["sn"]]$ts, type = "l", col = "gray", main = "Skewed Normal Observational Errors", xlab = "Time", ylab = "Standardized Value")
  
  colors <- c('darkred', 'forestgreen', 'darkblue')  # Assuming the order is 95th, 50th, and 10th percentiles
  legends <- c("95th Percentile", "50th Percentile", "10th Percentile")
  
  for (i in seq_along(ts_standardized_results[["sn"]]$qs)) {
    lines(ts_standardized_results[["sn"]]$qs[[i]], col = colors[i])
  }
  
  legend("topleft", legend = legends, col = colors, lty = 1, cex = 0.8)
} else {
  print("Quantiles for 'sn' observations are not available in ts_standardized_results.")
}


# Overlay the fitted model results for the 50th quantile
exdqlmPlot(y = ts_data_sn, sn_model_10th, add = TRUE, col = "orange")                               

plot.ts(sn_model_10th$seq.gamma)
plot.ts(sn_model_10th$seq.sigma)




















# Assuming `ts_data_sn`, `quantiles`, `model` are defined and `fit_exdqlmISVB123()`, `plot_quantiles_and_model_fit()`, `plot_sequence()` functions are properly implemented
p0_values <- c(0.1, 0.5, 0.95)  # Percentiles to consider

plot_path <-  "/home/jaguir26/projects/notebooks/plots"  # Change this to the actual path where you want to save plots

for (p0 in p0_values) {
  model_fit <- exdqlmISVB123(y = ts_data_sn, p0 = p0, model = model,
                             df = c(df1, df2), dim.df = dim_df,
                             sig.init = sig_init, gam.init = gam_init,
                             tol = tol, verbose = verbose)

  # Save the plot for observational errors
  png(file = paste0(plot_path, "Observational_Errors_P", p0*100, ".png"), width = 800, height = 600)
  plot(ts_data_sn, type = "l", col = "gray", main = paste("Skewed Normal Observational Errors, P =", p0), xlab = "Time", ylab = "Standardized Value")
  lines(model_fit$fit, col = "blue")  # Assuming `model_fit$fit` contains the fitted values. Adjust according to your actual output structure.
  dev.off()

  # Save the sequence plot for gamma
  png(file = paste0(plot_path, "Gamma_Sequence_P", p0*100, ".png"), width = 800, height = 600)
  plot(model_fit$seq.gamma, type = "l", col = "red", main = paste("Gamma Sequence, P =", p0), xlab = "Iteration", ylab = "Gamma")
  dev.off()

  # Save the sequence plot for sigma
  png(file = paste0(plot_path, "Sigma_Sequence_P", p0*100, ".png"), width = 800, height = 600)
  plot(model_fit$seq.sigma, type = "l", col = "green", main = paste("Sigma Sequence, P =", p0), xlab = "Iteration", ylab = "Sigma")
  dev.off()
}
