###############################################################################
# Data utilities (non-semantic helpers)
# Inputs:
#   - Numeric vectors/matrices
# Outputs:
#   - Standardized values + summary stats
# Dependencies:
#   - Base R
###############################################################################

standardize_with_sd <- function(x, sd_val) {
  list(values = x / sd_val, sd = sd_val)
}

standardize_matrix_cols <- function(mat) {
  sds <- apply(mat, 2, sd)
  list(values = sweep(mat, 2, sds, FUN = "/"), sds = sds)
}
