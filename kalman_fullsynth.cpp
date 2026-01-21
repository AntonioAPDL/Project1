// Enable C++11 via this plugin (Rcpp 0.10.3 or later)
// [[Rcpp::plugins(cpp11)]]

// Dependencies for RcppArmadillo and RcppEigen
// [[Rcpp::depends(RcppArmadillo, RcppEigen)]]

#include <RcppArmadillo.h>
#include <RcppEigen.h>
#include <Eigen/Dense>
#include <vector>

using namespace Rcpp;
using Eigen::MatrixXd;  // Explicitly using MatrixXd from Eigen

// Function to compute log determinant via Cholesky decomposition
// [[Rcpp::export]]
double logDetCholesky(const Eigen::MatrixXd& matrix) {
    double epsilon = 1e-16;
    double min_eigenvalue = matrix.selfadjointView<Eigen::Lower>().eigenvalues().minCoeff();
    if (min_eigenvalue <= 0) {
        epsilon -= min_eigenvalue;
    }

    Eigen::LLT<Eigen::MatrixXd> llt(matrix + epsilon * Eigen::MatrixXd::Identity(matrix.rows(), matrix.cols()));
    Eigen::MatrixXd L = llt.matrixL();
    double logDet = 0.0;
    for (int i = 0; i < L.rows(); ++i) {
        logDet += std::log(L(i, i));
    }
    return 2 * logDet;
}

// Function to regularize the matrix
arma::mat regularize(const arma::mat& matrix, double epsilon = 1e-15) {
    return matrix + epsilon * arma::eye<arma::mat>(matrix.n_rows, matrix.n_cols);
}

// Function to compute the robust SVD-based inversion
arma::mat robust_svd_inv(const arma::mat& matrix, double tolerance = 1e-20) {
    arma::mat U, V;
    arma::vec s;
    arma::svd(U, s, V, matrix);
    arma::vec s_inv = s;
    for (size_t i = 0; i < s.n_elem; ++i) {
        if (s(i) < tolerance) {
            s_inv(i) = tolerance;
        }
        s_inv(i) = 1.0 / s_inv(i);
    }
    return V * arma::diagmat(s_inv) * U.t();
}

// Function to compute the robust SVD-based inverse of the square root
arma::mat robust_svd_inv_sqrt(const arma::mat& matrix, double tolerance = 1e-20) {
    arma::mat U, V;
    arma::vec s;
    arma::svd(U, s, V, matrix);
    arma::vec s_inv_sqrt = s;
    for (size_t i = 0; i < s.n_elem; ++i) {
        if (s(i) < tolerance) {
            s_inv_sqrt(i) = tolerance;
        }
        s_inv_sqrt(i) = 1.0 / std::sqrt(s_inv_sqrt(i));
    }
    return V * arma::diagmat(s_inv_sqrt) * U.t();
}

// Function to expand the matrix
arma::mat expand_matrix(const arma::mat& product, const arma::vec& num_mem) {
    int J = num_mem.n_elem;
    int n = arma::sum(num_mem);
    arma::mat expanded_matrix(n, n, arma::fill::zeros);
    int start_row = 0;
    for (int i = 0; i < J; ++i) {
        int ni = num_mem(i);
        int start_col = 0;
        for (int j = 0; j < J; ++j) {
            int nj = num_mem(j);
            double value = product(i, j);
            expanded_matrix.submat(start_row, start_col, start_row + ni - 1, start_col + nj - 1).fill(value);
            start_col += nj;
        }
        start_row += ni;
    }
    return expanded_matrix;
}

// Function to expand FF_ens.slice(1) according to num_mem
arma::mat expand_FF(const arma::mat& FF_slice, const arma::vec& num_mem) {
    int p = FF_slice.n_rows;
    int J = FF_slice.n_cols;
    int n = arma::sum(num_mem);
    arma::mat expanded_FF(p, n, arma::fill::zeros);
    int start_col = 0;
    for (int j = 0; j < J; ++j) {
        int nj = num_mem(j);
        arma::mat block = FF_slice.col(j) * arma::ones<arma::rowvec>(nj);
        expanded_FF.cols(start_col, start_col + nj - 1) = block;
        start_col += nj;
    }
    return expanded_FF;
}

// Function to repeat vector
arma::vec repeat_vector(const arma::vec& input, const arma::vec& num_mem) {
    arma::vec output(arma::sum(num_mem));
    int index = 0;
    for (size_t i = 0; i < num_mem.n_elem; ++i) {
        output.subvec(index, index + num_mem(i) - 1).fill(input(i));
        index += num_mem(i);
    }
    return output;
}

// [[Rcpp::export]]
Rcpp::List update_theta_synth_cpp(arma::cube GG, 
                                  arma::vec m0, arma::mat C0, 
                                  arma::mat ex_f, arma::cube ex_q, arma::cube FF, 
                                  arma::mat y, arma::mat ex_df_mat, arma::mat ex_df_mat_k, 
                                  arma::mat Ones, int p, int J, int ppx, int TT, int k, int dM,
                                  Rcpp::List GG_list_ens, Rcpp::List FF_list_ens,
                                  Rcpp::List ex_f_list_ens, Rcpp::List ex_q_list_ens,
                                  arma::cube ex_df_mat_list_ens, arma::cube ex_df_mat_k_list_ens,
                                  Rcpp::List y_list_ens, arma::vec k_ens, arma::mat Ones_ens,
                                  int tot_ens, arma::vec num_mem) {
                                    
    // Print initial debug information
    // Rcpp::Rcout << "Debug: Entering update_theta_cpp function" << std::endl;

    // Declare matrices for use in SVD calculations
    arma::mat U, V;
    arma::vec s;

    // Variable declarations
    arma::mat m(p+J+ppx, TT, arma::fill::zeros);
    arma::cube C(p+J+ppx, p+J+ppx, TT, arma::fill::zeros);
    arma::mat sm(p+J+ppx, TT, arma::fill::zeros);
    arma::cube sC(p+J+ppx, p+J+ppx, TT, arma::fill::zeros);
    arma::mat standard_forecast_errors(J+1, TT, arma::fill::zeros);

    std::vector<arma::cube> m_ens(J);
    std::vector<arma::cube> sm_ens(J);
    std::vector<arma::cube> C_ens(J);
    std::vector<arma::cube> sC_ens(J);

    for (int j = 1; j <= J; ++j) {
        int kkk_j;
        if (j == 1) {
            kkk_j = k_ens[J-1];
        } else {
            kkk_j = k_ens[J-j] - k_ens[J-j+1];
        }
        m_ens[j-1] = arma::cube(p + J + 1 - j, 1, kkk_j, arma::fill::zeros);
        sm_ens[j-1] = arma::cube(p + J + 1 - j, 1, kkk_j, arma::fill::zeros);
        C_ens[j-1] = arma::cube(p + J + 1 - j, p + J + 1 - j, kkk_j, arma::fill::zeros);
        sC_ens[j-1] = arma::cube(p + J + 1 - j, p + J + 1 - j, kkk_j, arma::fill::zeros);
    }

    // Initialize standard_forecast_errors_ens with y_list_ens
    Rcpp::List standard_forecast_errors_ens = y_list_ens;

    double elbo = 0.0;

    // Initialize Eigen matrix from Armadillo data
    // Rcpp::Rcout << "Debug: Initializing Eigen matrix from Armadillo data" << std::endl;
    MatrixXd A = Eigen::Map<MatrixXd>(const_cast<double*>(C0.memptr()), C0.n_rows, C0.n_cols);
    double log_det = logDetCholesky(A);
    // Rcpp::Rcout << "Debug: log_det = " << log_det << std::endl;

    // Initial state and covariance propagation
    // Rcpp::Rcout << "Debug: Initial state and covariance propagation" << std::endl;
    arma::vec a = GG.slice(0) * m0;
    arma::mat P = GG.slice(0) * C0 * GG.slice(0).t();
    arma::mat R = P + ex_df_mat % P;  // Element-wise multiplication for variance adjustments
    R = (R + R.t()) / 2;
    R = regularize(R);

    // Compute initial forecast and process covariance
    // Rcpp::Rcout << "Debug: Compute initial forecast and process covariance" << std::endl;
    arma::vec f = FF.slice(0).t() * a + ex_f.col(0);
    arma::mat q = FF.slice(0).t() * R * FF.slice(0) + ex_q.slice(0);
    q = 0.5 * q + 0.5 * q.t();  // Symmetrize the matrix
    // Rcpp::Rcout << "Debug: Initial q matrix: " << q << std::endl;

    arma::mat q_inv = robust_svd_inv(q);
    arma::mat q_inv_sqrt = robust_svd_inv_sqrt(q);

    // Update the state and covariance estimates
    // Rcpp::Rcout << "Debug: Update the state and covariance estimates" << std::endl;
    m.col(0) = a + R * FF.slice(0) * q_inv * (y.col(0) - f);
    C.slice(0) = R - R * FF.slice(0) * q_inv.t() * FF.slice(0).t() * R.t();
    C.slice(0) = (C.slice(0) + C.slice(0).t()) / 2;
    // Rcpp::Rcout << "Debug: Initial m and C matrices updated" << std::endl;

    // Compute standard forecast errors
    // Rcpp::Rcout << "Debug: Compute standard forecast errors" << std::endl;
    standard_forecast_errors.col(0) = q_inv_sqrt * (y.col(0) - f);

    // Filtering: Before Forecast
    for (int t = 1; t < TT; ++t) {
        // Rcpp::Rcout << "Debug: Filtering before forecast, iteration t = " << t << std::endl;
        // State and covariance prediction using the previous time step
        a = GG.slice(t) * m.col(t-1);
        P = GG.slice(t) * C.slice(t-1) * GG.slice(t).t();  
        R = P % ex_df_mat +  P % Ones;  
        R = (R + R.t()) / 2;  // Symmetrize the matrix
        R = regularize(R);

        // Forecast and process covariance
        f = FF.slice(t).t() * a + ex_f.col(t);
        q = FF.slice(t).t() * R * FF.slice(t) + ex_q.slice(t);
        q = (q + q.t()) / 2;  // Symmetrize the matrix

        q_inv = robust_svd_inv(q);
        q_inv_sqrt = robust_svd_inv_sqrt(q);

        // Update the state and covariance estimates
        m.col(t) = a + R * FF.slice(t) * q_inv * (y.col(t) - f);
        C.slice(t) = R - R * FF.slice(t) * q_inv * FF.slice(t).t() * R.t();
        C.slice(t) = (C.slice(t) + C.slice(t).t()) / 2;

        // Compute standard forecast errors
        standard_forecast_errors.col(t) = q_inv_sqrt * (y.col(t) - f);
    }

    int k_j = 0;

    for (int j = J; j >= 1; --j) {
        int kk = 0;
        int index = J - j;

        // Filtering: After Forecast  
        if (j == J) {
            arma::mat GG_list_ens_mat = Rcpp::as<arma::mat>(GG_list_ens[index]);
            a = GG_list_ens_mat * m.col(TT-1).subvec(0, p + j - 1);
            P = GG_list_ens_mat * C.slice(TT-1).submat(0, 0, p + j - 1, p + j - 1) * GG_list_ens_mat.t();      
            R = P % ex_df_mat_list_ens.slice(0).submat(0, 0, p + j - 1, p + j - 1) +  P % Ones_ens.submat(0, 0, p + j - 1, p + j - 1);  
        } else {
            arma::mat GG_list_ens_mat = Rcpp::as<arma::mat>(GG_list_ens[index]);
            arma::mat sub_matrix = m_ens[index-1].subcube(0, 0, k_j-1, p + j - 1, 0, k_j-1);
            // a = GG_list_ens_mat * sub_matrix.col(0);
            a = GG_list_ens_mat * sub_matrix;
            P = GG_list_ens_mat * C_ens[index-1].slice(k_j-1).submat(0, 0, p + j - 1, p + j - 1) * GG_list_ens_mat.t();  
            R = P % ex_df_mat_list_ens.slice(1).submat(0, 0, p + j - 1, p + j - 1) +  P % Ones_ens.submat(0, 0, p + j - 1, p + j - 1);  
        }
        
        R = (R + R.t()) / 2;
        R = regularize(R);

        arma::vec f_a = Rcpp::as<arma::mat>(FF_list_ens[index]).t() * a;
        arma::vec exp_f_a = repeat_vector(f_a, num_mem);
        f = exp_f_a + Rcpp::as<arma::mat>(ex_f_list_ens[index]).col(kk);

        arma::mat FF_slice = Rcpp::as<arma::mat>(FF_list_ens[index]);
        arma::mat product = FF_slice.t() * R * FF_slice;
        arma::mat expanded_matrix = expand_matrix(product, num_mem);
        q = expanded_matrix + Rcpp::as<arma::cube>(ex_q_list_ens[index]).slice(kk);
        q = (q + q.t()) / 2;  // Symmetrize the matrix

        q_inv = robust_svd_inv(q);
        q_inv_sqrt = robust_svd_inv_sqrt(q);

        arma::mat expanded_FF = expand_FF(FF_slice, num_mem);
    
        m_ens[index].col(kk) = a + R * expanded_FF * q_inv * (Rcpp::as<arma::mat>(y_list_ens[index]).col(kk) - f);
        C_ens[index].slice(kk) = R - R * expanded_FF * q_inv * expanded_FF.t() * R.t();
        C_ens[index].slice(kk) = (C_ens[index].slice(kk) + C_ens[index].slice(kk).t()) / 2;

        // Compute standard forecast errors
        Rcpp::as<arma::mat>(standard_forecast_errors_ens[index]).col(kk) = q_inv_sqrt * (Rcpp::as<arma::mat>(y_list_ens[index]).col(kk) - f);

        if (j < J) {
            k_j = k_ens[index-1] - k_ens[index];
        }

        kk++;
        while (kk < k_j) {

            arma::mat GG_list_ens_mat = Rcpp::as<arma::mat>(GG_list_ens[index]);
            arma::mat sub_matrix = m_ens[index].subcube(0, 0, kk-1, p + j - 1, 0, kk-1);
            arma::vec a = GG_list_ens_mat * sub_matrix.col(0);
            
            arma::mat P = GG_list_ens_mat * C_ens[index].slice(kk-1).submat(0, 0, p + j - 1, p + j - 1) * GG_list_ens_mat.t();
            arma::mat R = P % ex_df_mat_list_ens.slice(1).submat(0, 0, p + j - 1, p + j - 1) + P % Ones_ens.submat(0, 0, p + j - 1, p + j - 1);

            // Symmetrize and regularize the matrix R
            R = (R + R.t()) / 2;
            R = regularize(R);

            arma::vec f_a = Rcpp::as<arma::mat>(FF_list_ens[index]).t() * a;
            arma::vec exp_f_a = repeat_vector(f_a, num_mem);
            arma::vec f = exp_f_a + Rcpp::as<arma::mat>(ex_f_list_ens[index]).col(kk);

            arma::mat FF_slice = Rcpp::as<arma::mat>(FF_list_ens[index]);
            arma::mat product = FF_slice.t() * R * FF_slice;
            arma::mat expanded_matrix = expand_matrix(product, num_mem);
            arma::mat q = expanded_matrix + Rcpp::as<arma::cube>(ex_q_list_ens[index]).slice(kk);
            q = (q + q.t()) / 2;  // Symmetrize the matrix

            arma::mat q_inv = robust_svd_inv(q);
            arma::mat q_inv_sqrt = robust_svd_inv_sqrt(q);

            arma::mat expanded_FF = expand_FF(FF_slice, num_mem);

            // Update the state and covariance estimates
            m_ens[index].col(kk) = a + R * expanded_FF * q_inv * (Rcpp::as<arma::mat>(y_list_ens[index]).col(kk) - f);
            C_ens[index].slice(kk) = R - R * expanded_FF * q_inv * expanded_FF.t() * R.t();
            C_ens[index].slice(kk) = (C_ens[index].slice(kk) + C_ens[index].slice(kk).t()) / 2;

            // Compute standard forecast errors
            Rcpp::as<arma::mat>(standard_forecast_errors_ens[index]).col(kk) = q_inv_sqrt * (Rcpp::as<arma::mat>(y_list_ens[index]).col(kk) - f);

            kk++;
        }

    }

    // Return the full result list
    return List::create(Named("standard_forecast_errors") = standard_forecast_errors,
                        Named("sm") = sm,
                        Named("sC") = sC,
                        Named("fm") = m, 
                        Named("fC") = C);
}
