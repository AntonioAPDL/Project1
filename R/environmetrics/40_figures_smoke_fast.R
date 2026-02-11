###############################################################################
# Smoke-only figures module
# Purpose:
#   - Produce a minimal figure set quickly for run-scoped post smoke validation.
#   - Reuse in-memory objects from earlier modules without touching model logic.
###############################################################################

profile_section("figures_smoke_fast.elbo_traces", {
  out_file <- file.path(OUT_DIR, "All_ELBOS_DISC.png")
  png(out_file, width = 2400, height = 1200, res = 300)
  on.exit(dev.off(), add = TRUE)

  par(mfrow = c(1, 3), mar = c(3, 3, 2, 1))

  plot_elbo <- function(x, title_txt) {
    vals <- as.numeric(x)
    if (length(vals) == 0L || all(!is.finite(vals))) {
      plot.new()
      title(main = paste0(title_txt, " (missing)"))
      return(invisible(NULL))
    }
    vals[1] <- NA_real_
    plot.ts(vals, main = title_txt, xlab = "Iteration", ylab = "ELBO", lwd = 1.5)
  }

  fetch_elbo <- function(name) {
    obj <- get0(name, ifnotfound = NULL, inherits = TRUE)
    if (is.null(obj) || !is.atomic(obj)) {
      return(numeric(0))
    }
    as.numeric(obj)
  }

  plot_elbo(fetch_elbo("seq.elbo_50_NDLM_synth_DISC"), "NDLM")
  plot_elbo(fetch_elbo("seq.elbo_50_exAL_synth_DISC"), "exAL50")
  plot_elbo(fetch_elbo("seq.elbo_95_exAL_synth_DISC"), "exAL95")
  mtext("Smoke Figure Set", side = 3, outer = TRUE, line = -2, cex = 0.9)
})

profile_section("figures_smoke_fast.observed_series", {
  out_file <- file.path(OUT_DIR, "SMOKE_OBSERVED_SERIES_DISC.png")
  png(out_file, width = 2400, height = 1200, res = 300)
  on.exit(dev.off(), add = TRUE)

  if (exists("Y", inherits = TRUE) && is.matrix(Y) && nrow(Y) >= 1L) {
    yy <- as.numeric(Y[1, ])
    idx <- which(is.finite(yy))
    if (length(idx) > 0L) {
      plot(idx, yy[idx], type = "l", col = "black", lwd = 1.5,
           xlab = "Time index", ylab = "log-flow", main = "Observed series (row 1)")
    } else {
      plot.new()
      title(main = "Observed series unavailable (no finite values)")
    }
  } else {
    plot.new()
    title(main = "Observed series unavailable (Y missing)")
  }
})
