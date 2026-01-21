library(future)
library(future.apply)
library(parallel)

# Test function
test_function <- function(x) {
  Sys.sleep(1)
  paste("Task", x, "processed on", system("hostname", intern = TRUE))
}

# Define worker nodes (local and remote)
workers <- c("jaguir26@muscat.be.ucsc.edu", "localhost")  # Jerez is local

# Fix: Ensure explicit user and SSH settings
cl <- makeClusterPSOCK(
  workers,
  user = rep("jaguir26", length(workers)),  # Explicit user definition
  rshcmd = c("ssh", "-o StrictHostKeyChecking=no", "-o UserKnownHostsFile=/dev/null")
)

# Set parallel execution
plan(cluster, workers = cl)

# Run parallel tasks
results <- future_sapply(1:10, test_function)

# Stop cluster
stopCluster(cl)

# Print results
print(results)

