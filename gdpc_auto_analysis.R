# Load necessary libraries
if (!require(gdpc)) {
  install.packages("gdpc")
}
library(gdpc)
library(readr)
library(doParallel)

# Function to run automatic GDPC analysis
run_auto_gdpc_analysis <- function(input_file, output_file, ncores = 1, niter_max = 1000) {
  print("Starting automatic GDPC analysis...")

  # Read the CSV file into R
  print("Reading input data...")
  data <- tryCatch({
    read_csv(input_file)
  }, error = function(e) {
    print(paste("Error reading file:", e))
    return(NULL)
  })

  if (is.null(data)) {
    stop("Failed to read the input file. Please check the path or file format.")
  }

  print("Data loaded successfully.")

  # Convert data to matrix form (excluding the Date column)
  print("Converting data to matrix form...")
  data_matrix <- as.matrix(data[,-1])

  # Standardize the data
  print("Standardizing the data...")
  data_standardized <- scale(data_matrix)

  # Register cores for parallel processing
  print(paste("Using", ncores, "cores for parallel computations..."))
  cl <- makeCluster(ncores)
  registerDoParallel(cl)

  # Run auto.gdpc with lag selection
  print("Running auto.gdpc...")
  gdpc_auto_result <- tryCatch({
    auto.gdpc(Z = data_standardized, crit = "LOO", normalize = 2, niter_max = niter_max, ncores = ncores)
  }, error = function(e) {
    print(paste("Error in auto.gdpc computation:", e))
    return(NULL)
  })

  stopCluster(cl)

  if (is.null(gdpc_auto_result)) {
    stop("Auto GDPC analysis failed. Please check the parameters or data.")
  }

  # Save the result
  print(paste("Saving auto GDPC result to", output_file, "..."))
  tryCatch({
    saveRDS(gdpc_auto_result, file = output_file)
  }, error = function(e) {
    print(paste("Error saving the result to file:", e))
  })

  print(paste("Auto GDPC analysis completed. Results saved to", output_file))
}

# Parse command line arguments for input file, output file, number of cores, and max iterations
args <- commandArgs(trailingOnly = TRUE)
input_file <- args[1]
output_file <- args[2]
ncores <- as.numeric(args[3])
niter_max <- as.numeric(args[4])

# Run the automatic GDPC analysis
run_auto_gdpc_analysis(input_file, output_file, ncores, niter_max)

