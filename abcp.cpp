#include <Rcpp.h>
#include <boost/math/distributions/normal.hpp>

// [[Rcpp::depends(BH)]]

using namespace Rcpp;

double log_g(double gam) {
    boost::math::normal_distribution<> normal_dist;
    double cdf_val = cdf(normal_dist, -std::abs(gam));
    return std::log(2) + std::log(cdf_val) + 0.5 * gam * gam;
}

double p_fn(double p0, double gam) {
    double log_g_val = log_g(gam);
    return (p0 - (gam < 0)) / std::exp(log_g_val) + (gam < 0);
}

double A_fn(double p0, double gam) {
    double temp_p = p_fn(p0, gam);
    return (1 - 2 * temp_p) / (temp_p * (1 - temp_p));
}

double B_fn(double p0, double gam) {
    double temp_p = p_fn(p0, gam);
    return 2 / (temp_p * (1 - temp_p));
}

double C_fn(double p0, double gam) {
    double temp_p = p_fn(p0, gam);
    return 1 / ((gam > 0) - temp_p);
}

// [[Rcpp::export]]
NumericVector test_functions(double p0, NumericVector gam) {
    int n = gam.size();
    NumericVector res(n * 5);

    for (int i = 0; i < n; ++i) {
        res[i] = log_g(gam[i]);
        res[n + i] = p_fn(p0, gam[i]);
        res[2 * n + i] = A_fn(p0, gam[i]);
        res[3 * n + i] = B_fn(p0, gam[i]);
        res[4 * n + i] = C_fn(p0, gam[i]);
    }

    return res;
}
