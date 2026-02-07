#include <boost/random.hpp>
#include <boost/random/normal_distribution.hpp>
#include <boost/random/uniform_real_distribution.hpp>
#include <boost/math/special_functions/erf.hpp>
#include <Rcpp.h>
#include <chrono>
#include <limits>
#include <omp.h>
#include <cstdint>

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

namespace {
std::uint64_t g_sampling_truncnorm_base_seed = 777ULL;

inline std::uint64_t splitmix64(std::uint64_t x) {
    x += 0x9e3779b97f4a7c15ULL;
    x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ULL;
    x = (x ^ (x >> 27)) * 0x94d049bb133111ebULL;
    return x ^ (x >> 31);
}

inline unsigned int derive_seed(std::uint64_t stream_id, std::uint64_t index_id) {
    std::uint64_t mixed = splitmix64(g_sampling_truncnorm_base_seed ^ (stream_id * 0x9e3779b97f4a7c15ULL) ^ index_id);
    return static_cast<unsigned int>(mixed & 0xffffffffULL);
}
}  // namespace

// [[Rcpp::export]]
void set_sampling_truncnorm_seed(double seed) {
    if (!R_finite(seed)) {
        Rcpp::stop("set_sampling_truncnorm_seed: seed must be finite");
    }
    if (seed < 0) {
        seed = -seed;
    }
    g_sampling_truncnorm_base_seed = static_cast<std::uint64_t>(std::llround(seed));
}

// [[Rcpp::export]]
Rcpp::NumericMatrix sample_truncnorm_icdf(int n_samp, int TT, Rcpp::NumericVector sts_mu, Rcpp::NumericVector sts_sig2) {
    if (sts_mu.size() != TT || sts_sig2.size() != TT) {
        Rcpp::stop("Length of sts_mu and sts_sig2 must be equal to TT");
    }
    Rcpp::NumericMatrix samples(n_samp, TT);

    #pragma omp parallel
    {
        int thread = omp_get_thread_num();
        boost::random::mt19937 gen(derive_seed(7001ULL, static_cast<std::uint64_t>(thread)));

        // Pre-calculate the standard deviations
        std::vector<double> std_devs(TT);
        for (int t = 0; t < TT; ++t) {
            std_devs[t] = std::sqrt(sts_sig2[t]);
        }

        #pragma omp for collapse(2) schedule(static)
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

// Backward-compatible alias (icdf sampler).
// [[Rcpp::export]]
Rcpp::NumericMatrix sample_truncnorm(int n_samp, int TT, Rcpp::NumericVector sts_mu, Rcpp::NumericVector sts_sig2) {
    return sample_truncnorm_icdf(n_samp, TT, sts_mu, sts_sig2);
}
