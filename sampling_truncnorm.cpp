#include <boost/random.hpp>
#include <boost/random/normal_distribution.hpp>
#include <boost/random/uniform_real_distribution.hpp>
#include <boost/math/special_functions/erf.hpp>
#include <Rcpp.h>
#include <chrono>
#include <limits>
#include <omp.h>
#include <cstdint>
#include <algorithm>

// Standard normal CDF
double normal_cdf(double x) {
    return 0.5 * erfc(-x * M_SQRT1_2);
}

// Inverse CDF for the standard normal distribution
double normal_cdf_inv(double p) {
    return sqrt(2) * boost::math::erf_inv(2 * p - 1);
}

double rtruncnorm_lower_tail_robert(boost::random::mt19937& gen, double alpha) {
    const double proposal_rate = 0.5 * (alpha + std::sqrt(alpha * alpha + 4.0));
    boost::random::uniform_real_distribution<> uniform01(0.0, 1.0);

    while (true) {
        const double u1 = std::max(uniform01(gen), std::numeric_limits<double>::min());
        const double z = alpha - std::log(u1) / proposal_rate;
        const double u2 = uniform01(gen);
        const double accept_prob = std::exp(-0.5 * std::pow(z - proposal_rate, 2.0));
        if (u2 <= accept_prob) {
            return z;
        }
    }
}

// Function to sample from a lower truncated normal distribution (truncated at 0)
double rtruncnorm(boost::random::mt19937& gen, double mean, double sd) {
    if (!std::isfinite(mean) || !std::isfinite(sd) || sd <= 0.0) {
        return std::numeric_limits<double>::quiet_NaN();
    }

    double a = 0.0; // Lower bound for truncation
    double alpha = (a - mean) / sd;

    if (std::isfinite(alpha) && alpha > 5.0) {
        const double z = rtruncnorm_lower_tail_robert(gen, alpha);
        return mean + sd * z;
    }

    const double alpha_cdf = normal_cdf(alpha);
    const double upper = std::nextafter(1.0, 0.0);
    if (!std::isfinite(alpha_cdf) || alpha_cdf >= upper) {
        const double z = rtruncnorm_lower_tail_robert(gen, std::max(alpha, 0.0));
        return mean + sd * z;
    }

    boost::random::uniform_real_distribution<> uniform_dist(alpha_cdf, upper);
    double U = std::min(uniform_dist(gen), upper);
    double sample = mean + sd * normal_cdf_inv(U);

    if (!std::isfinite(sample)) {
        const double z = rtruncnorm_lower_tail_robert(gen, std::max(alpha, 0.0));
        sample = mean + sd * z;
    }

    if (sample < 0.0 && sample > -1e-12) {
        sample = 0.0;
    }

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
    for (int t = 0; t < TT; ++t) {
        if (!R_finite(sts_mu[t])) {
            Rcpp::stop("sample_truncnorm_icdf: sts_mu contains non-finite values");
        }
        if (!R_finite(sts_sig2[t]) || sts_sig2[t] <= 0.0) {
            Rcpp::stop("sample_truncnorm_icdf: sts_sig2 must be finite and strictly positive");
        }
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
                const double sample = rtruncnorm(gen, mean, sd);
                if (!std::isfinite(sample) || sample < 0.0) {
                    samples(i, t) = std::numeric_limits<double>::quiet_NaN();
                } else {
                    samples(i, t) = sample;
                }
            }
        }
    }

    for (int t = 0; t < TT; ++t) {
        for (int i = 0; i < n_samp; ++i) {
            if (!R_finite(samples(i, t)) || samples(i, t) < 0.0) {
                Rcpp::stop("sample_truncnorm_icdf: produced invalid truncated-normal draws");
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
