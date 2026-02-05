disc_assert <- function(ok, msg = "Assertion failed.") {
  if (!isTRUE(DISC_DEBUG)) {
    return(invisible(TRUE))
  }
  if (!isTRUE(ok)) {
    stop(msg, call. = FALSE)
  }
  invisible(TRUE)
}
