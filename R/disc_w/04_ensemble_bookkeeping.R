# disc_w/04_ensemble_bookkeeping.R
#
# Ensemble bookkeeping for the Wishart/ensemble workflow.
# - Builds the ensemble list (per-source forecast matrix-like object).
# - Computes `J`, `num_mem`, `ranges` and `mean_forecast` exactly as in the
#   original script (no reordering or coercions).

# disc_w_build_ensembles(glofas_forecast, nws_forecast)
# Inputs:
# - forecast data.frames (as read by `read.csv`) with a date column in the first
#   position followed by numeric member columns.
# Output (list):
# - `ensembles`: list of member matrices/data.frames (date column removed)
# - `J`: number of ensemble sources
# - `num_mem`: members per source
# - `ranges`: rows per source
# - `mean_forecast`: stacked rowMeans used downstream
disc_w_build_ensembles <- function(glofas_forecast, nws_forecast) {
  raw_ensembles <- list(glofas_forecast[, -c(1)], nws_forecast[, -c(1)])
  E <- disc_w_as_ensemble(raw_ensembles, strict = DISC_DEBUG)

  ensembles <- E$data
  J <- E$J
  num_mem <- E$num_mem
  ranges <- E$ranges

  row_means_list <- vector("list", J + 1)
  row_means_list[[1]] <- rep(NA_real_, ranges[1])
  for (j in 1:J) {
    row_means_list[[j + 1]] <- rep(NA_real_, ranges[1])
    row_means_list[[j + 1]][1:ranges[j]] <- rowMeans(ensembles[[j]])
  }
  mean_forecast <- do.call(rbind, row_means_list)

  list(
    ensembles = ensembles,
    J = J,
    num_mem = num_mem,
    ranges = ranges,
    mean_forecast = mean_forecast
  )
}
