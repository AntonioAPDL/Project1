# Load necessary libraries
if (!require(gdpc)) {
  install.packages("gdpc")
}
library(gdpc)
library(readr)

# Define function to run GDPC analysis
run_gdpc_analysis <- function(input_file, output_file, k) {
  print(paste("Starting GDPC analysis with", k, "lags..."))

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

  # Apply Generalized Dynamic Principal Components (GDPC) with specified lags
  print(paste("Applying GDPC with", k, "lags..."))
  gdpc_result <- tryCatch({
    gdpc(Z = data_standardized, k = k)
  }, error = function(e) {
    print(paste("Error in GDPC computation:", e))
    return(NULL)
  })

  if (is.null(gdpc_result)) {
    stop("GDPC analysis failed. Please check the parameters or data.")
  }

  # Save the components and results
  print(paste("Saving GDPC result to", output_file, "..."))
  tryCatch({
    saveRDS(gdpc_result, file = output_file)
  }, error = function(e) {
    print(paste("Error saving the result to file:", e))
  })

  print(paste("GDPC analysis with", k, "lags completed. Results saved to", output_file))
}

# Parse command line arguments for input file, output file, and number of lags
args <- commandArgs(trailingOnly = TRUE)
input_file <- args[1]
output_file <- args[2]
k <- as.numeric(args[3])

# Run the analysis with the specified arguments
run_gdpc_analysis(input_file, output_file, k)

