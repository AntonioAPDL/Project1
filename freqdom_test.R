# Load necessary libraries
if (!require(freqdom)) {
  install.packages("freqdom")
}
library(freqdom)
library(readr)

# Function to run Dynamic PCA and return the first principal component and explained variance
run_freqdom_analysis <- function(input_file, q) {
  print(paste("Running Dynamic PCA with", q, "lags..."))

  # Step 1: Load the data
  data <- read_csv(input_file)

  # Step 2: Convert data to matrix form, excluding the Date column
  data_matrix <- as.matrix(data[,-1])  # Exclude the Date column

  # Step 3: Standardize the data
  data_standardized <- scale(data_matrix)

  # Step 4: Apply Dynamic PCA using freqdom with specified number of lags and 1 component
  dpca_result <- dpca(data_standardized, q = q, Ndpc = 1)

  # Step 5: Extract the first dynamic principal component
  first_pc <- dpca_result$scores[, 1]
  
  # Step 6: Calculate explained variance
  explained_variance <- sum(dpca_result$values) / sum(diag(cov(data_standardized)))
  
  # Return both the first PC and the explained variance
  return(list(first_pc = first_pc, explained_variance = explained_variance))
}

# Run Dynamic PCA with different lags
lags <- c(1, 5, 10)

# Store results for each lag
results <- list()

# Run DPCA for each lag and store the results
for (lag in lags) {
  result <- run_freqdom_analysis("test_example_data.csv", lag)
  results[[paste("Lag", lag, sep = "_")]] <- result
}

# Plot the first principal component for each lag
par(mfrow = c(3, 1))  # Plot in a 3-row layout
for (lag in lags) {
  plot(results[[paste("Lag", lag, sep = "_")]]$first_pc, type = 'l',
       main = paste("First Principal Component (Lag", lag, ")"),
       ylab = "PC1", xlab = "Time")
}

# Print the explained variance for each lag
cat("\nExplained Variance for each Lag:\n")
for (lag in lags) {
  cat(paste("Lag", lag, ": ", results[[paste("Lag", lag, sep = "_")]]$explained_variance, "\n"))
}

