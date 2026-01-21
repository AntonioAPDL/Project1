# Load necessary libraries
if (!require(freqdom)) {
  install.packages("freqdom")
}
library(freqdom)
library(readr)

# Function to run Dynamic PCA and save the first principal component
run_freqdom_analysis <- function(input_file, output_file, q) {
  print("Starting Dynamic PCA analysis...")

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

  # Step 4: Apply Dynamic PCA using freqdom with specified number of lags and 1 component
  print(paste("Applying Dynamic PCA with", q, "lags..."))
  dpca_result <- tryCatch({
    dpca(data_standardized, q = q, Ndpc = 1)
  }, error = function(e) {
    print(paste("Error in applying Dynamic PCA:", e))
    return(NULL)
  })

  if (is.null(dpca_result)) {
    stop("Dynamic PCA failed. Please check the parameters or data.")
  }

  print("Dynamic PCA completed successfully.")

  # Step 5: Extract the first dynamic principal component
  first_pc <- dpca_result$scores[, 1]
  print("First principal component extracted successfully. Preview:")
  print(head(first_pc))

  # Step 6: Save the first principal component to the output file
  print(paste("Saving first principal component to:", output_file))
  tryCatch({
    saveRDS(first_pc, file = output_file)
  }, error = function(e) {
    print(paste("Error saving the result to file:", e))
  })

  print("Analysis complete. First component saved successfully.")
}

# Parse command line arguments for input file, output file, and number of lags
args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 3) {
  stop("Insufficient arguments. Provide input file, output file, and number of lags.")
}
input_file <- args[1]
output_file <- args[2]
q <- as.numeric(args[3])  # Number of lags

# Run the analysis with the specified arguments
run_freqdom_analysis(input_file, output_file, q)

