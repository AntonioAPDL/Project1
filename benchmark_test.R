# benchmark_test.R
# This script performs a large matrix multiplication to test computation speed

# Load required library
library(microbenchmark)

# Create two large matrices (adjust the size as needed)
n <- 10000  # Size of the matrix (10000 x 10000)
A <- matrix(runif(n * n), n, n)
B <- matrix(runif(n * n), n, n)

# Run the matrix multiplication and measure the time taken
benchmark_result <- microbenchmark(
  result = A %*% B,
  times = 5  # Run 5 iterations
)

# Print the benchmark result
print(benchmark_result)

# Save the result to a file
write.csv(as.data.frame(benchmark_result), "benchmark_results.csv")


