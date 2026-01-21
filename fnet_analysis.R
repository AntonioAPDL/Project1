# Load required libraries
if (!require(fnet)) {
  install.packages("fnet")
}
library(fnet)
library(readr)

# Function to run Dynamic PCA with Factor Analysis and save the results
run_fnet_analysis <- function(input_file, output_file) {
  print("Starting Factor-Adjusted Dynamic PCA analysis...")

  # Step 1: Load the data
  print(paste("Reading data from:", input_file))
  data <- tryCatch({
    read_csv(input_file)
  }, error = function(e) {
    print(paste("Error reading file:", e))
    return(NULL)
  })

  if (is.null(data)) {
    stop("Failed to read the input file. Please check the path or file format.")
  }

  print("Data loaded successfully. Preview of the first few rows:")
  print(head(data))

  # Step 2: Convert data to matrix form, excluding the Date column
  data_matrix <- as.matrix(data[,-1])  # Exclude the Date column

  print("Data converted to matrix. Checking dimensions:")
  print(dim(data_matrix))

  # Step 3: Standardize the data
  print("Standardizing the data...")
  data_standardized <- tryCatch({
    scale(data_matrix)
  }, error = function(e) {
    print(paste("Error in standardizing data:", e))
    return(NULL)
  })

  if (is.null(data_standardized)) {
    stop("Failed to standardize the data.")
  }

  print("Data standardized successfully. Preview:")
  print(head(data_standardized))

  # Step 4: Apply Dynamic PCA with Factor Analysis using fnet
  print("Applying Factor-Adjusted Dynamic PCA...")
  factor_analysis_result <- tryCatch({
    factor.model <- fnet::factor.adjust(data_standardized, K = 1) # Adjust K based on desired factors
    factor.model
  }, error = function(e) {
    print(paste("Error in applying Factor-Adjusted Dynamic PCA:", e))
    return(NULL)
  })

  if (is.null(factor_analysis_result)) {
    stop("Factor-Adjusted Dynamic PCA failed. Please check the parameters or data.")
  }

  print("Factor-Adjusted Dynamic PCA completed successfully.")

  # Step 5: Save the factor analysis result to the output file
  print(paste("Saving factor analysis result to:", output_file))
  tryCatch({
    saveRDS(factor_analysis_result, file = output_file)
  }, error = function(e) {
    print(paste("Error saving the result to file:", e))
  })

  print("Analysis complete. Factor analysis result saved successfully.")
}

# Parse command line arguments for input file and output file
args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 2) {
  stop("Insufficient arguments. Provide input file and output file.")
}
input_file <- args[1]
output_file <- args[2]

# Run the analysis with the specified arguments
run_fnet_analysis(input_file, output_file)

