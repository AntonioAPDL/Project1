disc_w_build_ensembles <- function(glofas_forecast, nws_forecast) {
  ensembles <- list(glofas_forecast[, -c(1)], nws_forecast[, -c(1)])
  J <- length(ensembles)
  num_mem <- rep(NA_real_, J)
  ranges <- rep(NA_real_, J)
  for (j in 1:J) {
    num_mem[j] <- dim(ensembles[[j]])[2]
    ranges[j] <- dim(ensembles[[j]])[1]
  }

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
