# Ensure required libraries are installed and loaded
if (!requireNamespace("GA", quietly = TRUE)) {
  install.packages("GA")
}
if (!requireNamespace("parallel", quietly = TRUE)) {
  install.packages("parallel")
}

library(GA)
library(parallel)

# File paths
file_paths <- list(
  y_reps = "/data/muscat_data/jaguir26/project1_ucsc_phd/y_reps.rds",
  y_reps_f = "/data/muscat_data/jaguir26/project1_ucsc_phd/y_reps_f.rds",
  Y = "/data/muscat_data/jaguir26/project1_ucsc_phd/Y.rds",
  mean_forecast = "/data/muscat_data/jaguir26/project1_ucsc_phd/mean_forecast.rds"
)

# Load data
loaded_data <- lapply(file_paths, function(path) {
  if (file.exists(path)) {
    return(readRDS(path))
  } else {
    stop(paste("File not found:", path))
  }
})

# Assign loaded data
y_reps <- loaded_data$y_reps
y_reps_f <- loaded_data$y_reps_f
Y <- loaded_data$Y
mean_forecast <- loaded_data$mean_forecast

# Dimensions
TT <- dim(y_reps)[3]
TT_f <- dim(y_reps_f)[3]

# Generic CRPS computation function
compute_crps_generic <- function(w, t, use_forecast = FALSE) {
  set.seed(666)
  
  # Normalize weights
  w <- w / sum(w)
  
  # Select data based on the specification
  if (use_forecast) {
    sims_t <- t(y_reps_f[,,t])
    forecasts <- colMeans(exp(mean_forecast), na.rm = TRUE)
    y <- forecasts[t]
  } else {
    sims_t <- t(y_reps[,,t])
    y <- Y[1, t]
  }
  
  # Sample from rows of sims_t based on probabilities w
  n <- nrow(sims_t)
  selected <- sims_t[cbind(1:n, apply(
    matrix(runif(n), nrow = n),
    1,
    function(x) which.max(cumsum(w) > x)
  ))]
  
  # CRPS computation
  crps_quantile_representation <- function(y, sample) {
    sorted_sample <- sort(sample)
    tau_values <- seq(1 / length(sample), 1, length.out = length(sample))
    crps_value <- sum(ifelse(
      y >= sorted_sample,
      tau_values * (y - sorted_sample), 
      (1 - tau_values) * (sorted_sample - y)
    ))
    return(2 * crps_value / length(sample))
  }
  
  # Compute and return CRPS
  crps_quantile_representation(y, selected)
}

# Generic optimization function
optimize_weights_generic <- function(t, use_forecast = FALSE) {
  crps_func <- function(w, t) {
    compute_crps_generic(w, t, use_forecast)
  }
  
  ga_result <- ga(
    type = "real-valued",
    fitness = function(w) -crps_func(w, t),  # Minimize loss by negating
    lower = rep(0, 7),                       # Lower bounds
    upper = rep(10000, 7),                   # Upper bounds
    popSize = 40,                            # Population size
    maxiter = 1000,                          # Maximum iterations
    run = 100,                               # Convergence tolerance
    parallel = FALSE                         # Disable GA's internal parallelization
  )
  
  # Extract and normalize the best solution
  best_solution <- ga_result@solution[1, ]
  optimal_w <- best_solution / sum(best_solution)
  minimum_loss <- -ga_result@fitnessValue
  
  # Return results
  list(
    Time_Step = t,
    Optimal_Weights = optimal_w,
    Minimum_Loss = minimum_loss
  )
}

# Define time steps
time_steps <- list(
  regular = 1:TT,
  forecast = 1:TT_f
)

# Parallel execution for regular and forecast specifications
results_regular <- mclapply(
  time_steps$regular,
  optimize_weights_generic,
  use_forecast = FALSE,
  mc.cores = parallel::detectCores() - 1
)

results_forecast <- mclapply(
  time_steps$forecast,
  optimize_weights_generic,
  use_forecast = TRUE,
  mc.cores = parallel::detectCores() - 1
)

# Store results in a list
all_results <- list(
  Regular = results_regular,
  Forecast = results_forecast
)

# Save results to disk
saveRDS(all_results, "/data/muscat_data/jaguir26/project1_ucsc_phd/optimization_results.rds")

# Optionally save each result as a separate CSV for easier access
write.csv(do.call(rbind, results_regular), "/data/muscat_data/jaguir26/project1_ucsc_phd/results_regular.csv")
write.csv(do.call(rbind, results_forecast), "/data/muscat_data/jaguir26/project1_ucsc_phd/results_forecast.csv")

# Display results
print("Results saved successfully:")
print(all_results)

