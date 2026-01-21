#include <boost/random.hpp>
#include <boost/random/normal_distribution.hpp>
#include <boost/random/uniform_real_distribution.hpp>
#include <boost/math/special_functions/erf.hpp>
#include <Rcpp.h>
#include <chrono>
#include <omp.h>

// Standard normal CDF
double normal_cdf(double x) {
    return 0.5 * erfc(-x * M_SQRT1_2);
}

// Inverse CDF for the standard normal distribution
double normal_cdf_inv(double p) {
    return sqrt(2) * boost::math::erf_inv(2 * p - 1);
}

// Function to sample from a lower truncated normal distribution (truncated at 0)
double rtruncnorm(boost::random::mt19937& gen, double mean, double sd) {
    double a = 0.0; // Lower bound for truncation
    double alpha = (a - mean) / sd;
    double alpha_cdf = normal_cdf(alpha);
    
    boost::random::uniform_real_distribution<> uniform_dist(alpha_cdf, 1.0);
    double U = uniform_dist(gen);
    double sample = mean + sd * normal_cdf_inv(U);

    return sample;
}

// [[Rcpp::export]]
Rcpp::NumericMatrix sample_truncnorm(int n_samp, int TT, Rcpp::NumericVector sts_mu, Rcpp::NumericVector sts_sig2) {
    if (sts_mu.size() != TT || sts_sig2.size() != TT) {
        Rcpp::stop("Length of sts_mu and sts_sig2 must be equal to TT");
    }
    Rcpp::NumericMatrix samples(n_samp, TT);

    #pragma omp parallel
    {
        unsigned seed = std::chrono::system_clock::now().time_since_epoch().count() + omp_get_thread_num();
        boost::random::mt19937 gen(seed);

        // Pre-calculate the standard deviations
        std::vector<double> std_devs(TT);
        for (int t = 0; t < TT; ++t) {
            std_devs[t] = std::sqrt(sts_sig2[t]);
        }

        #pragma omp for collapse(2)
        for (int t = 0; t < TT; ++t) {
            for (int i = 0; i < n_samp; ++i) {
                double mean = sts_mu[t];
                double sd = std_devs[t];
                samples(i, t) = rtruncnorm(gen, mean, sd);
            }
        }
    }

    return samples;
}
