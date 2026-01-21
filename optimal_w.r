# Load required packages
if (!requireNamespace("GA", quietly = TRUE)) {
  install.packages("GA")
}
if (!requireNamespace("parallel", quietly = TRUE)) {
  install.packages("parallel")
}

library(GA)
library(parallel)

# Utility functions
p.fn <- function(p0, gam) {
  (p0 - as.numeric(gam < 0)) / exp(log.g(gam)) + as.numeric(gam < 0)
}

A.fn <- function(p0, gam) {
  temp.p <- p.fn(p0, gam)
  (1 - 2 * temp.p) / (temp.p * (1 - temp.p))
}

B.fn <- function(p0, gam) {
  temp.p <- p.fn(p0, gam)
  2 / (temp.p * (1 - temp.p))
}

C.fn <- function(p0, gam) {
  temp.p <- p.fn(p0, gam)
  (as.numeric(gam > 0) - temp.p)^(-1)
}

CheckLossFn <- function(p0, diff) {
  diff * p0 - diff * as.numeric(diff < 0)
}

# Load data
Y <- readRDS("Y.rds")
y_reps <- readRDS("y_reps.rds")
print(dim(y_reps))

n.samp <- dim(y_reps)[2]  
TT <- dim(y_reps)[3]      

# Define functions for mixture synthesis and loss calculation
mix_syth <- function(t, wt) {
  set.seed(777)
  y_reps_numeric <- as.numeric(y_reps[,,t]) 
  dim(y_reps_numeric) <- dim(y_reps[,,t])   
  wt_numeric <- as.numeric(wt)
  result <- sweep(y_reps_numeric, 1, wt_numeric, `*`)
  mix <- colSums(result)
  return(mix)
}

loss_w <- function(w, t) {
  w <- w / sum(w)  # Normalize weights
  quantiles <- c(0.05, 0.2, 0.35, 0.5, 0.65, 0.8, 0.95)
  
  # Total loss calculated across quantiles
  y_total_loss <- sum(sapply(quantiles, function(p0) {
      y_quantile <- quantile(mix_syth(t, w), p0)
      CheckLossFn(p0, y_quantile - exp(Y[1, t]))
  }))
  
  return(y_total_loss)
}

# Function to optimize weights
optimize_weights <- function(t) {
  ga_result <- ga(
    type = "real-valued",
    fitness = function(w) -loss_w(w, t),  # Minimize loss by negating
    lower = rep(0, 7),
    upper = rep(10, 7),
    popSize = 200,
    maxiter = 50,
    run = 50,
    parallel = FALSE  # Disable internal parallel processing in GA
  )
  
  optimal_w <- ga_result@solution / sum(ga_result@solution)
  minimum_loss <- -ga_result@fitnessValue
  
  list(Time_Step = t, Optimal_Weights = optimal_w, Minimum_Loss = minimum_loss)
}

# Apply optimization over time steps in parallel
time_steps <- (TT - 5000):TT
results <- mclapply(time_steps, optimize_weights, mc.cores = parallel::detectCores() - 1)
results_df <- do.call(rbind, lapply(results, as.data.frame))
print(results_df)

# Save results to file
saveRDS(results_df, file = "results_df.rds")

