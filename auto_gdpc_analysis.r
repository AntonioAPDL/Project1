# Load necessary libraries; install if missing
if (!require(gdpc)) {
  install.packages("gdpc")
}
library(gdpc)
if (!require(readr)) {
  install.packages("readr")
}
library(readr)
if (!require(doParallel)) {
  install.packages("doParallel")
}
library(doParallel)

# Define the specific indices to use
indices <- c("Solar Flux", "ONI", "WHWP", "GMT", "AMO", "TSA", "TNA", "SOI")

# Function to run automatic GDPC analysis with automatic lag/component selection
run_auto_gdpc_analysis <- function(input_file, output_file, ncores = 1, niter_max = 1000) {
  cat("Starting automatic GDPC analysis...\n")
  
  # Read the CSV file into R
  cat("Reading input data...\n")
  data <- tryCatch({
    read_csv(input_file, show_col_types = FALSE)
  }, error = function(e) {
    cat("Error reading file:", as.character(e), "\n")
    return(NULL)
  })
  
  if (is.null(data)) {
    stop("Failed to read the input file. Please check the path or file format.")
  }
  cat("Data loaded successfully.\n")
  
  # Check if all specified indices are present
  missing_cols <- setdiff(indices, colnames(data))
  if (length(missing_cols) > 0) {
    stop(paste("The following required columns are missing from the data:", 
               paste(missing_cols, collapse = ", ")))
  }
  
  # Subset the data to only the Date column and the selected indices
  data_subset <- data[, c("Date", indices)]
  
  # Remove rows with missing values (ensuring complete cases)
  data_subset <- data_subset[complete.cases(data_subset), ]
  
  # Convert data (excluding Date) to matrix form
  cat("Converting data to matrix form...\n")
  data_matrix <- as.matrix(data_subset[,-1])
  
  # Standardize the data (z-score normalization)
  cat("Standardizing the data...\n")
  data_standardized <- scale(data_matrix)
  
  # Remove any rows that still contain NA, infinite, or NaN values after standardization
  data_standardized <- data_standardized[apply(data_standardized, 1, function(x) all(is.finite(x))), ]
  
  # Set up parallel processing
  cat(paste("Using", ncores, "cores for parallel computations...\n"))
  cl <- makeCluster(ncores)
  registerDoParallel(cl)
  
  # Run auto.gdpc with LOO criterion
  cat("Running auto.gdpc...\n")
  gdpc_auto_result <- tryCatch({
    auto.gdpc(Z = data_standardized, crit = "LOO", normalize = 2, 
              niter_max = niter_max, ncores = ncores)
  }, error = function(e) {
    cat("Error in auto.gdpc computation:", as.character(e), "\n")
    return(NULL)
  })
  
  # Stop the parallel cluster
  stopCluster(cl)
  
  if (is.null(gdpc_auto_result)) {
    stop("Auto GDPC analysis failed. Please check the parameters or data.")
  }
  
  # Save the GDPC result as an RDS file
  cat(paste("Saving auto GDPC result to", output_file, "...\n"))
  tryCatch({
    saveRDS(gdpc_auto_result, file = output_file)
  }, error = function(e) {
    cat("Error saving the result to file:", as.character(e), "\n")
  })
  
  cat(paste("Auto GDPC analysis completed. Results saved to", output_file, "\n"))
}

# Parse command line arguments for: input file, output file, number of cores, and maximum iterations
args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 4) {
  stop("Usage: Rscript auto_gdpc_analysis.R <input_file> <output_file> <ncores> <niter_max>")
}

input_file <- args[1]
output_file <- args[2]
ncores <- as.numeric(args[3])
niter_max <- as.numeric(args[4])

# Run the automatic GDPC analysis
run_auto_gdpc_analysis(input_file, output_file, ncores, niter_max)
