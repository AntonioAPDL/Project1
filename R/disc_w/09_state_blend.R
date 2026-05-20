disc_blend_numeric_like <- function(current, candidate, alpha, label = "value") {
  disc_dim_string <- function(x) {
    dims <- dim(x)
    if (is.null(dims)) {
      return(sprintf("len=%d", length(x)))
    }
    paste(dims, collapse = "x")
  }
  if (!is.finite(alpha) || alpha >= 1) {
    return(candidate)
  }
  if (alpha <= 0) {
    return(current)
  }
  if (is.null(current) && is.null(candidate)) {
    return(NULL)
  }
  if (is.null(current)) {
    return(candidate)
  }
  if (is.null(candidate)) {
    return(current)
  }
  current_arr <- as.array(current)
  candidate_arr <- as.array(candidate)
  if (!identical(dim(current_arr), dim(candidate_arr))) {
    stop(
      sprintf(
        "blend dim mismatch for %s current=%s candidate=%s",
        label,
        disc_dim_string(current),
        disc_dim_string(candidate)
      ),
      call. = FALSE
    )
  }
  blended <- alpha * candidate_arr + (1 - alpha) * current_arr
  if (is.null(dim(candidate))) {
    return(as.numeric(blended))
  }
  dim(blended) <- dim(candidate)
  dimnames(blended) <- dimnames(candidate)
  blended
}

disc_blend_numeric_list <- function(current_list, candidate_list, alpha, label_prefix = "list") {
  if (is.null(current_list) && is.null(candidate_list)) {
    return(NULL)
  }
  if (is.null(current_list)) {
    return(candidate_list)
  }
  if (is.null(candidate_list)) {
    return(current_list)
  }
  if (!is.list(current_list) || !is.list(candidate_list)) {
    stop(sprintf("blend list mismatch for %s", label_prefix), call. = FALSE)
  }
  if (length(current_list) != length(candidate_list)) {
    stop(sprintf("blend list length mismatch for %s", label_prefix), call. = FALSE)
  }
  Map(
    function(cur_item, cand_item, idx) {
      disc_blend_numeric_like(
        cur_item,
        cand_item,
        alpha,
        sprintf("%s[[%d]]", label_prefix, as.integer(idx))
      )
    },
    current_list,
    candidate_list,
    seq_along(candidate_list)
  )
}
