#' Density Function for the Extended Asymmetric Laplace (exAL) Distribution
#'
#' Computes the probability density function (PDF) for the Extended Asymmetric Laplace (exAL) distribution.
#'
#' @param x Numeric vector of quantiles.
#' @param p0 Probability level associated with the quantile parameterization. Must be in (0,1). Default is 0.5.
#' @param mu Location parameter. Default is 0.
#' @param sigma Scale parameter. Must be strictly positive. Default is 1.
#' @param gamma Skewness parameter controlling asymmetry. Default is 0.
#' @param log Logical; if TRUE, returns the log-density. Default is FALSE.
#'
#' @return A numeric vector of probability densities.
#' 
#' @details The exAL distribution extends the Asymmetric Laplace (AL) distribution by incorporating an additional skewness parameter `gamma`. 
#'          This distribution is useful for modeling heavy-tailed asymmetric data.
#'
#' @examples
#' dexal(0)
#' dexal(1, p0 = 0.75, mu = 0, sigma = 2, gamma = 1)
#' dexal(seq(-3, 3, by = 0.1), p0 = 0.3, mu = 0, sigma = 1, gamma = -0.5)
#'
#' @export
dexal <- function(x, p0 = 0.5, mu = 0, sigma = 1, gamma = 0, log = FALSE) {
  .Call('_dexal', x, p0, mu, sigma, gamma, log)
}

#' Cumulative Distribution Function (CDF) for the exAL Distribution
#'
#' Computes the cumulative probability for the Extended Asymmetric Laplace (exAL) distribution.
#'
#' @param q Numeric vector of quantiles.
#' @param p0 Probability level associated with the quantile parameterization. Must be in (0,1). Default is 0.5.
#' @param mu Location parameter. Default is 0.
#' @param sigma Scale parameter. Must be strictly positive. Default is 1.
#' @param gamma Skewness parameter controlling asymmetry. Default is 0.
#' @param lower.tail Logical; if TRUE (default), returns P(X ≤ q), otherwise P(X > q).
#' @param log.p Logical; if TRUE, returns log-probabilities. Default is FALSE.
#'
#' @return A numeric vector of cumulative probabilities.
#'
#' @examples
#' pexal(0)
#' pexal(1, p0 = 0.75, mu = 0, sigma = 2, gamma = 1)
#' pexal(seq(-3, 3, by = 0.1), p0 = 0.3, mu = 0, sigma = 1, gamma = -0.5)
#'
#' @export
pexal <- function(q, p0 = 0.5, mu = 0, sigma = 1, gamma = 0, lower.tail = TRUE, log.p = FALSE) {
  .Call('_pexal', q, p0, mu, sigma, gamma, lower.tail, log.p)
}

#' Quantile Function for the exAL Distribution
#'
#' Computes the quantile function (inverse CDF) for the Extended Asymmetric Laplace (exAL) distribution.
#'
#' @param p Numeric vector of probabilities. Must be in (0,1).
#' @param p0 Probability level associated with the quantile parameterization. Must be in (0,1). Default is 0.5.
#' @param mu Location parameter. Default is 0.
#' @param sigma Scale parameter. Must be strictly positive. Default is 1.
#' @param gamma Skewness parameter controlling asymmetry. Default is 0.
#' @param lower.tail Logical; if TRUE (default), returns the lower-tail quantile. If FALSE, returns the upper-tail quantile.
#' @param log.p Logical; if TRUE, probabilities are given in log-scale. Default is FALSE.
#'
#' @return A numeric vector of quantiles.
#'
#' @examples
#' qexal(0.5)
#' qexal(0.95, p0 = 0.75, mu = 0, sigma = 2, gamma = 1)
#' qexal(seq(0.1, 0.9, by = 0.1), p0 = 0.3, mu = 0, sigma = 1, gamma = -0.5)
#'
#' @export
qexal <- function(p, p0 = 0.5, mu = 0, sigma = 1, gamma = 0, lower.tail = TRUE, log.p = FALSE) {
  .Call('_qexal', p, p0, mu, sigma, gamma, lower.tail, log.p)
}

#' Random Sample Generation for the exAL Distribution
#'
#' Generates random numbers from the Extended Asymmetric Laplace (exAL) distribution.
#'
#' @param n Number of random values to generate. Must be a positive integer.
#' @param p0 Probability level associated with the quantile parameterization. Must be in (0,1). Default is 0.5.
#' @param mu Location parameter. Default is 0.
#' @param sigma Scale parameter. Must be strictly positive. Default is 1.
#' @param gamma Skewness parameter controlling asymmetry. Default is 0.
#'
#' @return A numeric vector of `n` random values drawn from the exAL distribution.
#'
#' @examples
#' rexal(10)
#' rexal(5, p0 = 0.75, mu = 0, sigma = 2, gamma = 1)
#' rexal(1000, p0 = 0.3, mu = 0, sigma = 1, gamma = -0.5)
#'
#' @export
rexal <- function(n, p0 = 0.5, mu = 0, sigma = 1, gamma = 0) {
  .Call('_rexal', n, p0, mu, sigma, gamma)
}
