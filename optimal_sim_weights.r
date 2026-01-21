# Ensure required libraries are installed and loaded
if (!requireNamespace("GA", quietly = TRUE)) {
  install.packages("GA")
}
if (!requireNamespace("parallel", quietly = TRUE)) {
  install.packages("parallel")
}

library(GA)
library(parallel)


# y_reps_sim <- readRDS("/data/muscat_data/jaguir26/project1_ucsc_phd/y_reps_sim.rds")
y_reps_sim <- readRDS("/data/muscat_data/jaguir26/project1_ucsc_phd/y_reps_sim_synth.rds")
ps_n <- dim(y_reps_sim)[1]
y <- readRDS("/data/muscat_data/jaguir26/project1_ucsc_phd/y.rds")

TT <- dim(y)[2]
compute_crps_generic <- function(w, t) {
  set.seed(111)
  w        <- w / sum(w)
  sims_t   <- t(y_reps_sim[,t,])
  y        <- y[1, t]
  n        <- nrow(sims_t)
  selected <- sims_t[cbind(1:n, apply( matrix(runif(n), nrow = n), 1, function(x) which.max(cumsum(w) > x)))]
  
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
  
  crps_quantile_representation(y, selected)
}

optimize_weights_generic <- function(t) {
  crps_func <- function(w, t) {
    compute_crps_generic(w, t)
  }
  
  ga_result <- ga(
    type = "real-valued",
    fitness = function(w) -crps_func(w, t),  # Minimize loss by negating
    lower = rep(0, ps_n),                       # Lower bounds
    upper = rep(100000000, ps_n),                   # Upper bounds
    popSize = 100,                            # Population size
    maxiter = 1000,                          # Maximum iterations
    run = 50,                               # Convergence tolerance
    parallel = FALSE                         # Disable GA's internal parallelization
  )
  
  best_solution <- ga_result@solution[1, ]
  optimal_w <- best_solution / sum(best_solution)
  minimum_loss <- -ga_result@fitnessValue

  list(
    Time_Step = t,
    Optimal_Weights = optimal_w,
    Minimum_Loss = minimum_loss
  )
}

time_steps <- list(
  regular = 1:TT
)

results_regular <- mclapply(
  time_steps$regular,
  optimize_weights_generic,
  mc.cores = parallel::detectCores() - 1
)

all_results <- list(
  Regular = results_regular
)

saveRDS(all_results, "/data/muscat_data/jaguir26/project1_ucsc_phd/SIM_optimization_results.rds")
write.csv(do.call(rbind, results_regular), "/data/muscat_data/jaguir26/project1_ucsc_phd/SIM_results_regular.csv")
print("Results saved successfully:")
print(all_results)

