# Load required libraries
library(fda.usc)
library(readr)

# Function to run FPCA and save the results
run_fpca_analysis <- function(input_file, output_file) {
  print("Starting FPCA analysis using fda.usc...")

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

  # Step 4: Create a functional data object
  print("Creating a functional data object...")
  tryCatch({
    # Create fdata object assuming rows are observations and columns are features
    fdata_object <- fdata(data_standardized)
    print("Functional data object created successfully.")
  }, error = function(e) {
    print(paste("Error creating fdata object:", e))
    return(NULL)
  })

  # Check if the fdata_object was created correctly
  if (!exists("fdata_object")) {
    stop("Failed to create fdata object.")
  }

  # Step 5: Apply Functional PCA
  print("Applying Functional PCA...")
  fpca_result <- tryCatch({
    fdata2pc(fdata_object, ncomp = 5)  # Select the number of components (e.g., 5)
  }, error = function(e) {
    print(paste("Error in applying FPCA:", e))
    return(NULL)
  })

  if (is.null(fpca_result)) {
    stop("FPCA analysis failed. Please check the parameters or data.")
  }

  print("FPCA analysis completed successfully.")

  # Step 6: Save the FPCA result to the output file
  print(paste("Saving FPCA result to:", output_file))
  tryCatch({
    saveRDS(fpca_result, file = output_file)
  }, error = function(e) {
    print(paste("Error saving the result to file:", e))
  })

  print("Analysis complete. FPCA result saved successfully.")
}

# Parse command line arguments for input file and output file
args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 2) {
  stop("Insufficient arguments. Provide input file and output file.")
}
input_file <- args[1]
output_file <- args[2]

# Run the analysis with the specified arguments
run_fpca_analysis(input_file, output_file)

