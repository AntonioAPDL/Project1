# Load necessary libraries
if (!require(freqdom)) {
  install.packages("freqdom")
}
library(freqdom)
library(readr)

# Function to run Dynamic PCA and save the result
run_dpca_analysis <- function(data_matrix, q, output_file) {
  print(paste("Running DPCA with", q, "lags..."))

  # Apply DPCA with specified number of lags
  dpca_result <- dpca(data_matrix, q = q, Ndpc = 1)

  # Save the explained variance
  explained_variance <- dpca.var(dpca_result$spec.density)[1]
  print(paste("Explained Variance for Lag", q, ":", explained_variance))

  # Save the first dynamic principal component
  first_pc <- dpca_result$scores[, 1]
  print(paste("First principal component for Lag", q, "extracted."))

  # Save results to file
  saveRDS(list(dpca_result = dpca_result, explained_variance = explained_variance, first_pc = first_pc), file = output_file)
  print(paste("Results for Lag", q, "saved to", output_file))
}

# Main Script
args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 2) {
  stop("Please provide the lag value and output file name.")
}

# Parse command-line arguments
lag <- as.numeric(args[1])
output_file <- args[2]

# Load the data, excluding the Date column
print("Loading data...")
data <- read_csv("/data/muscat_data/jaguir26/project1_ucsc_phd/climate_indices/combined_indices_daily.csv")

# Convert data to matrix form (excluding the Date column)
data_matrix <- as.matrix(data[,-1])
print("Data successfully loaded and converted to matrix.")

# Standardize the data
data_standardized <- scale(data_matrix)
print("Data standardized.")

# Run DPCA with the specified lag
run_dpca_analysis(data_standardized, lag, output_file)

