#include <Rcpp.h>
#include <RcppEigen.h>
#include <random>
#include <cmath>

// [[Rcpp::depends(RcppEigen)]]
using namespace Rcpp;
using namespace std;
using Eigen::Map;
using Eigen::MatrixXd;

// Function to perform Nu Sampling
// [[Rcpp::export]]
NumericMatrix nu_sampling(int n_samp, NumericVector uts_chi, double uts_psi, double uts_lambda, int TT) {
  NumericMatrix samp_uts(TT, n_samp);
  std::random_device rd;
  std::mt19937 gen(rd());
  for (int t = 0; t < TT; t++) {
    for (int i = 0; i < n_samp; i++) {
      std::gamma_distribution<> d(uts_lambda, uts_psi / uts_chi[t]);
      samp_uts(t, i) = d(gen);
    }
  }
  return samp_uts;
}

// Function to perform S Sampling
// [[Rcpp::export]]
NumericMatrix s_sampling(int n_samp, NumericVector sts_mu, NumericVector sts_sig2, int TT) {
  NumericMatrix samp_sts(TT, n_samp);
  std::random_device rd;
  std::mt19937 gen(rd());
  for (int t = 0; t < TT; t++) {
    for (int i = 0; i < n_samp; i++) {
      std::normal_distribution<> d(sts_mu[t], std::sqrt(sts_sig2[t]));
      double samp = d(gen);
      samp_sts(t, i) = std::max(samp, 0.0);  // Ensure truncation at 0
    }
  }
  return samp_sts;
}

// Function to perform Theta Sampling for a single time point
// [[Rcpp::export]]
NumericMatrix samp_theta_t(NumericMatrix sC, NumericMatrix sm, int t, int n_samp, int pJ) {
  Map<MatrixXd> LL(Map<MatrixXd>(sC.begin(), sC.nrow(), sC.ncol()).transpose());
  NumericMatrix theta(pJ, n_samp);
  std::random_device rd;
  std::mt19937 gen(rd());
  for (int i = 0; i < n_samp; i++) {
    NumericVector rnorm = rnorm(pJ);
    for (int j = 0; j < pJ; j++) {
      double sum = 0;
      for (int k = 0; k < pJ; k++) {
        sum += LL(j, k) * rnorm[k];
      }
      theta(j, i) = sm(j, t) + sum;
    }
  }
  return theta;
}

// Function to vectorize Theta Sampling for all time points
// [[Rcpp::export]]
List samp_theta_all(NumericMatrix sC, NumericMatrix sm, int TT, int n_samp, int pJ) {
  List theta_all(TT);
  for (int t = 0; t < TT; t++) {
    theta_all[t] = samp_theta_t(sC, sm, t, n_samp, pJ);
  }
  return theta_all;
}

// Function to perform posterior predictive sampling
// [[Rcpp::export]]
NumericMatrix samp_post_pred_all(int j, List samp_theta, NumericVector FF, NumericMatrix samp_sigma, NumericMatrix samp_gamma, NumericMatrix samp_sts, int n_samp, int TT) {
  NumericMatrix post_pred(TT, n_samp);
  for (int t = 0; t < TT; t++) {
    NumericMatrix theta = samp_theta[t];
    for (int i = 0; i < n_samp; i++) {
      double xb = 0;
      for (int k = 0; k < theta.nrow(); k++) {
        xb += FF[k + j * FF.size() / (TT * theta.nrow()) + t * FF.size() / TT] * theta(k, i);
      }
      double value = xb + samp_sigma(j, i) * std::abs(samp_gamma(j, i)) * samp_sts(j, t, i);
      post_pred(t, i) = value;  // This line can be adjusted as needed
    }
  }
  return post_pred;
}
