#include <RcppArmadillo.h>
#include <boost/math/special_functions/bessel.hpp>
#include <boost/random.hpp>
#include <cmath>
#include <omp.h>

// [[Rcpp::depends(RcppArmadillo)]]
// [[Rcpp::depends(BH)]]

using namespace Rcpp;
using namespace arma;

double psi(double x, double alpha, double lambda) {
    return -alpha * (cosh(x) - 1) - lambda * (exp(x) - x - 1);
}

double dpsi(double x, double alpha, double lambda) {
    return -alpha * sinh(x) - lambda * (exp(x) - 1);
}

double g(double x, double sd, double td, double f1, double f2) {
    if (x >= -sd && x <= td) {
        return 1.0;
    } else if (x > td) {
        return f1;
    } else if (x < -sd) {
        return f2;
    }
    return 0.0; // This should not happen
}

double sample_gig_devroye(double p, double a, double b) {
    double lambda = p;
    double omega = sqrt(a * b);
    double alpha = sqrt(omega * omega + lambda * lambda) - lambda;
    double t, s;

    // Find t
    double x = -psi(1.0, alpha, lambda);
    if (x >= 0.5 && x <= 2.0) {
        t = 1.0;
    } else if (x > 2.0) {
        t = sqrt(2.0 / (alpha + lambda));
    } else {
        t = log(4.0 / (alpha + 2.0 * lambda));
    }

    // Find s
    x = -psi(-1.0, alpha, lambda);
    if (x >= 0.5 && x <= 2.0) {
        s = 1.0;
    } else if (x > 2.0) {
        s = sqrt(4.0 / (alpha * cosh(1.0) + lambda));
    } else {
        s = std::min(1.0 / lambda, log(1.0 + 1.0 / alpha + sqrt(1.0 / (alpha * alpha) + 2.0 / alpha)));
    }

    double eta = -psi(t, alpha, lambda);
    double zeta = -dpsi(t, alpha, lambda);
    double theta = -psi(-s, alpha, lambda);
    double xi = dpsi(-s, alpha, lambda);

    double p_const = 1.0 / xi;
    double r = 1.0 / zeta;
    double td = t - r * eta;
    double sd = s - p_const * theta;
    double q = td + sd;

    double X, U, V, W;
    bool done = false;
    while (!done) {
        U = R::runif(0.0, 1.0);
        V = R::runif(0.0, 1.0);
        W = R::runif(0.0, 1.0);
        if (U < q / (p_const + q + r)) {
            X = -sd + q * V;
        } else if (U < (q + r) / (p_const + q + r)) {
            X = td - r * log(V);
        } else {
            X = -sd + p_const * log(V);
        }

        double f1 = exp(-eta - zeta * (X - t));
        double f2 = exp(-theta + xi * (X + s));
        if ((W * g(X, sd, td, f1, f2)) <= exp(psi(X, alpha, lambda))) {
            done = true;
        }
    }

    return exp(X) * (lambda / omega + sqrt(1.0 + (lambda / omega) * (lambda / omega))) / sqrt(a / b);
}

// [[Rcpp::export]]
Rcpp::NumericMatrix sample_gig_devroye_vector(int n_samples, double p, double a, Rcpp::NumericVector b_vec) {
    int TT = b_vec.size();
    Rcpp::NumericMatrix samples(n_samples, TT);

    #pragma omp parallel for collapse(2)
    for (int t = 0; t < TT; ++t) {
        for (int i = 0; i < n_samples; ++i) {
            samples(i, t) = sample_gig_devroye(p, a, b_vec[t]);
        }
    }

    return samples;
}
