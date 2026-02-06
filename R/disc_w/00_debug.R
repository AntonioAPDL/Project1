# disc_w/00_debug.R
#
# Debug/assert utilities for the DISC Wishart/ensemble workflow.
# - `DISC_DEBUG` is defined in `DISC_Optimal_Synth_Ranges_W.r` (default: FALSE).
# - `disc_assert()` is a no-op unless `DISC_DEBUG` is TRUE.

# disc_assert(ok, msg)
# - When `DISC_DEBUG` is TRUE: stops if `ok` is not TRUE.
# - When `DISC_DEBUG` is FALSE: returns invisibly TRUE.
disc_assert <- function(ok, msg = "Assertion failed.") {
  if (!isTRUE(DISC_DEBUG)) {
    return(invisible(TRUE))
  }
  if (!isTRUE(ok)) {
    stop(msg, call. = FALSE)
  }
  invisible(TRUE)
}
