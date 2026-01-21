# Load required libraries
library(fnets)
library(readr)

# Function to run FNets analysis and save the results
run_fnets_analysis <- function(input_file, output_file, q = 2, var_order = 1) {
  print("Starting FNets analysis...")

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

  # Step 4: Apply FNets analysis with specified number of factors and VAR order
  print(paste("Applying FNets with q =", q, "factors and VAR order =", var_order, "..."))
  fnets_result <- tryCatch({
    fnets(data_standardized, q = q, var.order = var_order, var.method = "lasso", do.lrpc = TRUE)
  }, error = function(e) {
    print(paste("Error in applying FNets:", e))
    return(NULL)
  })

  if (is.null(fnets_result)) {
    stop("FNets analysis failed. Please check the parameters or data.")
  }

  print("FNets analysis completed successfully.")

  # Step 5: Save the FNets result to the output file
  print(paste("Saving FNets result to:", output_file))
  tryCatch({
    saveRDS(fnets_result, file = output_file)
  }, error = function(e) {
    print(paste("Error saving the result to file:", e))
  })

  print("Analysis complete. FNets result saved successfully.")
}

# Parse command line arguments for input file, output file, and other parameters
args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 2) {
  stop("Insufficient arguments. Provide input file, output file, and optionally q (number of factors) and VAR order.")
}
input_file <- args[1]
output_file <- args[2]
q <- ifelse(length(args) >= 3, as.numeric(args[3]), 2)  # Default to 2 factors if not provided
var_order <- ifelse(length(args) >= 4, as.numeric(args[4]), 1)  # Default to VAR order 1 if not provided

# Run the analysis with the specified arguments
run_fnets_analysis(input_file, output_file, q, var_order)

