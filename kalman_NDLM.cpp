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

// [[Rcpp::export]]
double logDetCholesky(const Eigen::MatrixXd& matrix) {
    // Base epsilon for regularization 
    double epsilon = 1e-16;

    // Estimate the smallest eigenvalue to adjust epsilon if necessary
    double min_eigenvalue = matrix.selfadjointView<Eigen::Lower>().eigenvalues().minCoeff();
    if (min_eigenvalue <= 0) {
        epsilon -= min_eigenvalue;  // Adjust epsilon to make the matrix positive definite
    }

    // Apply regularization
    Eigen::LLT<Eigen::MatrixXd> llt(matrix + epsilon * Eigen::MatrixXd::Identity(matrix.rows(), matrix.cols()));
    
    // Retrieve the lower triangular matrix L from the Cholesky decomposition
    Eigen::MatrixXd L = llt.matrixL();

    // Calculate the log determinant from the log of diagonal elements of L
    double logDet = 0.0;
    for (int i = 0; i < L.rows(); ++i) {
        logDet += std::log(L(i, i));
    }

    // log(det(A)) = 2 * sum(log(diag(L))) because det(A) = (det(L))^2
    return 2 * logDet;
}

// [[Rcpp::export]]
Rcpp::List compute_cholesky(const arma::mat& q, bool compute_sqrt_inverse = false) {
    if (!q.is_sympd()) {
        stop("The matrix is not positive definite.");
    }
    
    arma::mat U = arma::chol(q, "upper");
    arma::mat inv_q = arma::inv_sympd(q);
    
    if (!compute_sqrt_inverse) {
        return Rcpp::List::create(Named("inverse") = inv_q);
    } else {
        arma::mat sqrt_inv_q = arma::inv(arma::trimatu(U));
        arma::mat sqrt_inv_q_product = sqrt_inv_q * arma::trans(sqrt_inv_q);
        bool is_correct = arma::approx_equal(sqrt_inv_q_product, inv_q, "absdiff", 1e-20);
        
        return Rcpp::List::create(Named("inverse") = inv_q, Named("sqrt_inverse") = sqrt_inv_q, Named("check") = is_correct);
    }
}

// Function to compute matrix power for time series step ahead prediction
// [[Rcpp::export]]
arma::mat H_t_k_r(const arma::cube& GG, int t, int k, int r) {
    int n = GG.n_rows;
    arma::mat I = arma::eye<arma::mat>(n, n);
    
    for (int s = t + k - r; s <= t + k; ++s) {
        I = GG.slice(s) * I;
    }
    
    return I;
}



// [[Rcpp::export]]
List update_theta_cpp_ndlm(const arma::cube& GG, 
                  const arma::vec& m0, const arma::mat& C0, 
                  const arma::mat& D, const arma::cube& FF, 
                  const arma::mat& y, const arma::mat& ex_df_mat, const arma::mat& ex_df_mat_k, 
                  const arma::mat& Ones, int p, int J, int ppx, int TT, int k, int dM) {
    // Declare matrices for use in SVD calculations
    arma::mat U, V;
    arma::vec s;

    // Variable declarations
    arma::mat m(p+J+ppx, TT, arma::fill::zeros);
    arma::cube C(p+J+ppx, p+J+ppx, TT, arma::fill::zeros);
    arma::mat sm(p+J+ppx, TT, arma::fill::zeros);
    arma::cube sC(p+J+ppx, p+J+ppx, TT, arma::fill::zeros);
    arma::mat standard_forecast_errors(J+1, TT, arma::fill::zeros);
    arma::mat standard_forecast_errors_k(J+1, TT, arma::fill::zeros);
    double elbo = 0.0;


    // Initialize Eigen matrix from Armadillo data
    MatrixXd A = Eigen::Map<MatrixXd>(const_cast<double*>(C0.memptr()), C0.n_rows, C0.n_cols);
    double log_det = logDetCholesky(A);

    // Initial state and covariance propagation
    arma::vec a = GG.slice(0) * m0;
    arma::mat P = GG.slice(0) * C0 * GG.slice(0).t();
    arma::mat R = P + ex_df_mat % P;  // Element-wise multiplication for variance adjustments
    R = (R + R.t()) / 2;

    // Compute initial forecast and process covariance
    arma::vec f = FF.slice(0).t() * a;
    arma::mat q = FF.slice(0).t() * R * FF.slice(0) + D;
    q = 0.5 * q + 0.5 * q.t();  // Symmetrize the matrix

    // Cholesky decomposition to compute square root inverse
    arma::svd(U, s, V, q);
    arma::mat q_inv = U * arma::diagmat(1/s) * U.t();

    Rcpp::List chol_res = compute_cholesky(q, true);
    arma::mat q_inv_sqrt = as<arma::mat>(chol_res["sqrt_inverse"]);

    // Update the state and covariance estimates
    m.col(0) = a + R * FF.slice(0) * q_inv * (y.col(0) - f);
    C.slice(0) = R - R * FF.slice(0) * q_inv.t() * FF.slice(0).t() * R.t();
    C.slice(0) = (C.slice(0) + C.slice(0).t()) / 2;

    // Compute standard forecast errors
    standard_forecast_errors.col(0) = q_inv_sqrt * (y.col(0) - f);

    // K-step ahead forecast error calculations
    arma::mat H = H_t_k_r(GG, 1, k, k);
    arma::vec a_1k = H * m0;
    arma::vec fk = FF.slice(1 + k).t() * a_1k;
    arma::mat Pk = H * C0 * H.t();
    arma::mat R_1k = Pk + ex_df_mat_k % Pk;
    arma::mat qk = FF.slice(1 + k).t() * R_1k * FF.slice(1 + k) + D;

    // Invert qk
    chol_res = compute_cholesky(qk, false);
    arma::mat qk_inv = as<arma::mat>(chol_res["inverse"]);

    chol_res = compute_cholesky(qk, true);
    arma::mat qk_inv_sqrt = as<arma::mat>(chol_res["sqrt_inverse"]);

    // Compute k-step ahead forecast errors
    standard_forecast_errors_k.col(0) = qk_inv_sqrt * (y.col(1+k) - fk);

    // Loop through remaining time steps
    for (int t = 1; t < TT; ++t) {
        // State and covariance prediction using the previous time step
        a = GG.slice(t) * m.col(t-1);
        P = GG.slice(t) * C.slice(t-1) * GG.slice(t).t();  
        R = P % ex_df_mat +  P;  
        R = (R + R.t()) / 2;  // Symmetrize the matrix

        // Forecast and process covariance
        f = FF.slice(t).t() * a;
        q = FF.slice(t).t() * R * FF.slice(t) + D;
        q = (q + q.t()) / 2;  // Symmetrize the matrix

        // Inversion of q using SVD
        arma::svd(U, s, V, q);
        arma::mat q_inv = U * arma::diagmat(1/s) * U.t();

        // Compute square root inverse via Cholesky
        q_inv_sqrt = as<arma::mat>(compute_cholesky(q, true)["sqrt_inverse"]);

        // Update the state and covariance estimates
        m.col(t) = a + R * FF.slice(t) * q_inv * (y.col(t) - f);
        C.slice(t) = R - R * FF.slice(t) * q_inv * FF.slice(t).t() * R.t();
        C.slice(t) = (C.slice(t) + C.slice(t).t()) / 2;

        // Compute standard forecast errors
        standard_forecast_errors.col(t) = q_inv_sqrt * (y.col(t) - f);

        // K-step ahead forecast error calculations
        if (t + k < TT) {
            H = H_t_k_r(GG, t, k, k);
            a_1k = H * m.col(t-1);
            fk = FF.slice(t + k).t() * a_1k;
            Pk = H * C.slice(t-1) * H.t();
            R_1k = Pk + ex_df_mat_k % Pk;
            qk = FF.slice(t + k).t() * R_1k * FF.slice(t + k) + D;

            qk_inv = as<arma::mat>(compute_cholesky(qk, false)["inverse"]);
            qk_inv_sqrt = as<arma::mat>(compute_cholesky(qk, true)["sqrt_inverse"]);

            // Compute k-step ahead forecast errors
            standard_forecast_errors_k.col(t) = qk_inv_sqrt * (y.col(t+k) - fk);
        }
    }
    // Initialize the last smoothed state and covariance from the final filter step
    sC.slice(TT-1) = C.slice(TT-1);
    sm.col(TT-1) = m.col(TT-1);

    // Initialize ELBO
    elbo = 0;

// CHANGE THIS
    elbo -= 0.5 * log_det ;

    A = Eigen::Map<Eigen::MatrixXd>(sC.slice(TT-1).memptr(), sC.slice(TT-1).n_rows, sC.slice(TT-1).n_cols);
    log_det = logDetCholesky(A);
    elbo += 0.5 * log_det; 
    // Backward loop for smoothing and ELBO calculation
    for (int t = TT-2; t >= 0; --t) {
        arma::vec a = GG.slice(t+1) * m.col(t);
        arma::mat P = GG.slice(t + 1)* C.slice(t) * GG.slice(t+1).t();
        arma::mat R = P % ex_df_mat + P; 
        R = (R + R.t()) / 2;  

        // Invert R using SVD
        arma::svd(U, s, V, R);
        arma::mat R_inv = U * arma::diagmat(1/s) * U.t();

        arma::mat sB = C.slice(t) * GG.slice(t+1).t() * R_inv;
        sm.col(t) = m.col(t) + sB * (sm.col(t+1) - a);
        sC.slice(t) = C.slice(t) + sB * (sC.slice(t+1) - R) * sB.t();
        sC.slice(t) = (sC.slice(t) + sC.slice(t).t()) / 2;

        // ELBO contribution for this step
        arma::mat W_t_1 = ex_df_mat % P;
        arma::svd(U, s, V, W_t_1); 
        arma::mat W_inv = U * arma::diagmat(1/s) * U.t();
        arma::mat CBRB = sC.slice(t) - sB * sC.slice(t+1) * sB.t();

// CHANGE THIS
        A = Eigen::Map<Eigen::MatrixXd>(W_t_1.memptr(), W_t_1.n_rows, W_t_1.n_cols);
        log_det = logDetCholesky(A);
        elbo -= 0.5 * log_det; 

        A = Eigen::Map<Eigen::MatrixXd>(CBRB.memptr(), CBRB.n_rows, CBRB.n_cols); 
        log_det = logDetCholesky(A);
        elbo += 0.5 * log_det; 

        // arma::vec ee = sm.col(t+1) - GG.slice(t+1) * sm.col(t);
        // arma::mat XX = sC.slice(t+1) + P - 2 * sB * sC.slice(t+1) + ee * ee.t();
        
        arma::vec ee = sm.col(t+1) - GG.slice(t+1) * sm.col(t);
        // CORRECT EVERYWHERE ELSE!
        arma::mat XX = sC.slice(t+1) + GG.slice(t+1)*sC.slice(t)*GG.slice(t+1).t();
        XX = XX - 2*( P*R_inv*sC.slice(t+1) ) + ee * ee.t();
        
        arma::mat xXX =  arma::solve(W_t_1, XX);
        elbo -= 0.5 * arma::accu(xXX.diag());

        a = GG.slice(t+1) * m.col(t);
        CBRB = sC.slice(t) - sB * sC.slice(t+1) * sB.t();
        arma::svd(U, s, V, CBRB);
        arma::mat CBRB_inv = U * arma::diagmat(1/s) * U.t();

        arma::vec xx = sm.col(t) - m.col(t) - sB * (sm.col(t+1) - a);
        arma::mat xxxx = CBRB_inv * (xx * xx.t());
        elbo += 0.5 * arma::accu(xxxx.diag());

// CHANGE THIS
        A = Eigen::Map<Eigen::MatrixXd>(CBRB.memptr(), CBRB.n_rows, CBRB.n_cols); 
        log_det = logDetCholesky(A);
        elbo += 0.5 * log_det; 
    }
    // Smoothing at time 0
    P = GG.slice(0) * C0 * GG.slice(0).t();
    R = P + ex_df_mat % P;  // Variance adjustment
    R = (R + R.t()) / 2;  // Ensuring symmetry

    // Invert R using SVD
    arma::svd(U, s, V, R);
    arma::mat R_inv = U * arma::diagmat(1/s) * U.t();

    arma::mat sB = C0 * GG.slice(0).t() * R_inv;
    arma::vec sm_0 = m0 + sB * (sm.col(0) - GG.slice(0) * m0);
    arma::mat sC_0 = C0 + sB * (sC.slice(0) - R) * sB.t();
    sC_0 = (sC_0 + sC_0.t()) / 2;

    // ELBO calculations for time 0
    arma::mat W_t_1 = ex_df_mat % P;
    arma::svd(U, s, V, W_t_1);  // Reuse U, s, V for another SVD
    arma::mat W_inv = U * arma::diagmat(1/s) * U.t();

    arma::vec ee = sm.col(0) - GG.slice(0) * sm_0;
    arma::mat XX = sC.slice(0) + P - 2 * sB * sC.slice(0) + ee * ee.t();
    XX = W_inv * XX;
    elbo -= 0.5 * arma::accu(XX.diag());

    arma::mat XXX = sC_0 + (sm_0 - m0) * (sm_0 - m0).t();
    XXX = arma::solve(C0, XXX);
    elbo -= 0.5 * arma::accu(XXX.diag());

    // Additional ELBO terms related to CBRB
    a = GG.slice(0) * m0;
    arma::mat CBRB = sC_0 - sB * sC.slice(0) * sB.t();
    arma::svd(U, s, V, CBRB);
    arma::mat CBRB_inv = U * arma::diagmat(1/s) * U.t();
    arma::vec xx = sm_0 - m0 - sB * (sm.col(0) - a);
    arma::mat xxxx = CBRB_inv * (xx * xx.t());
    elbo += 0.5 * arma::accu(xxxx.diag());
// CHANGE THIS
    A = Eigen::Map<Eigen::MatrixXd>(CBRB.memptr(), CBRB.n_rows, CBRB.n_cols); 
    log_det = logDetCholesky(A);
    elbo += 0.5 * log_det; 

    // Return the full result list
    return List::create(Named("standard_forecast_errors") = standard_forecast_errors,
                        Named("standard_forecast_errors_k") = standard_forecast_errors_k,
                        Named("sm") = sm,
                        Named("sC") = sC,
                        Named("fm") = m, // Filtered states
                        Named("fC") = C, // Filtered covariances
                        Named("elbo.part") = elbo);
}


// [[Rcpp::export]]
List update_theta_cpp_ndlm_exactV(const arma::cube& GG, 
                  const arma::vec& m0, const arma::mat& C0, const arma::cube& FF, 
                  const arma::mat& y, const arma::mat& ex_df_mat, const arma::mat& ex_df_mat_k, 
                  const arma::mat& Ones, int p, int J, int ppx, int TT, int k, int dM,
                  const arma::vec& nu0, const arma::vec& S0) {
    // Declare matrices for use in SVD calculations
    arma::mat U, V;
    arma::vec s;

    arma::vec nu_t = nu0;  // Initialize posterior degrees of freedom
    arma::vec S_t = S0;    // Initialize posterior scale
    arma::mat V_obs_inv_diag(J+1, TT, arma::fill::zeros);  // Store inverse diagonal values of V
    arma::vec V_diag = S_t / (nu_t);  // Posterior mean of diagonal elements
    arma::mat V_obs = arma::diagmat(V_diag);  // Diagonal covariance matrix

    // Variable declarations
    arma::mat m(p+J+ppx, TT, arma::fill::zeros);
    arma::cube C(p+J+ppx, p+J+ppx, TT, arma::fill::zeros);
    arma::mat sm(p+J+ppx, TT, arma::fill::zeros);
    arma::cube sC(p+J+ppx, p+J+ppx, TT, arma::fill::zeros);
    arma::mat standard_forecast_errors(J+1, TT, arma::fill::zeros);
    arma::mat standard_forecast_errors_k(J+1, TT, arma::fill::zeros);
    double elbo = 0.0;

    // Initialize Eigen matrix from Armadillo data
    MatrixXd A = Eigen::Map<MatrixXd>(const_cast<double*>(C0.memptr()), C0.n_rows, C0.n_cols);
    double log_det = logDetCholesky(A);

    // Initial state and covariance propagation
    arma::vec a = GG.slice(0) * m0;
    arma::mat P = GG.slice(0) * C0 * GG.slice(0).t();
    arma::mat R = P + ex_df_mat % P;  // Element-wise multiplication for variance adjustments
    R = (R + R.t()) / 2;
    // Compute initial forecast and process covariance
    arma::vec f = FF.slice(0).t() * a;
    arma::mat q = FF.slice(0).t() * R * FF.slice(0) + V_obs;
    q = 0.5 * q + 0.5 * q.t();  // Symmetrize the matrix
    // Cholesky decomposition to compute square root inverse
    arma::svd(U, s, V, q);
    arma::mat q_inv = U * arma::diagmat(1/s) * U.t();
    Rcpp::List chol_res = compute_cholesky(q, true);
    arma::mat q_inv_sqrt = as<arma::mat>(chol_res["sqrt_inverse"]);

    // Update the state and covariance estimates
    m.col(0) = a + R * FF.slice(0) * q_inv * (y.col(0) - f);
    C.slice(0) = R - R * FF.slice(0) * q_inv.t() * FF.slice(0).t() * R.t();
    C.slice(0) = (C.slice(0) + C.slice(0).t()) / 2;

    // Compute standard forecast errors
    standard_forecast_errors.col(0) = q_inv_sqrt * (y.col(0) - f);
    // K-step ahead forecast error calculations
    arma::mat H = H_t_k_r(GG, 1, k, k);
    arma::vec a_1k = H * m0;
    arma::vec fk = FF.slice(1 + k).t() * a_1k;
    arma::mat Pk = H * C0 * H.t();
    arma::mat R_1k = Pk + ex_df_mat_k % Pk;
    arma::mat qk = FF.slice(1 + k).t() * R_1k * FF.slice(1 + k) + V_obs;  // Include updated V
    // Invert qk
    chol_res = compute_cholesky(qk, false);
    arma::mat qk_inv = as<arma::mat>(chol_res["inverse"]);

    chol_res = compute_cholesky(qk, true);
    arma::mat qk_inv_sqrt = as<arma::mat>(chol_res["sqrt_inverse"]);

    // Compute k-step ahead forecast errors
    standard_forecast_errors_k.col(0) = qk_inv_sqrt * (y.col(1+k) - fk);
    // Loop through remaining time steps
    for (int t = 1; t < TT; ++t) {
        // State and covariance prediction using the previous time step
        a = GG.slice(t) * m.col(t-1);
        P = GG.slice(t) * C.slice(t-1) * GG.slice(t).t();  
        R = P % ex_df_mat +  P;  
        R = (R + R.t()) / 2;  // Symmetrize the matrix

        // Predictive observation covariance (using updated V)
        V_diag = S_t / nu_t ;  // Posterior mean of diagonal elements
        V_obs = arma::diagmat(V_diag);  // Diagonal covariance matrix

        // Forecast and process covariance
        f = FF.slice(t).t() * a;
        // q = FF.slice(t).t() * R * FF.slice(t) + D;
        q = FF.slice(t).t() * R * FF.slice(t) + V_obs;  // Observation covariance
        q = (q + q.t()) / 2;  // Symmetrize the matrix

        // Inversion of q using SVD
        arma::svd(U, s, V, q);
        arma::mat q_inv = U * arma::diagmat(1/s) * U.t();

        // Compute square root inverse via Cholesky
        q_inv_sqrt = as<arma::mat>(compute_cholesky(q, true)["sqrt_inverse"]);

        // Update the state and covariance estimates
        arma::vec e = y.col(t) - f;  // Innovation
        m.col(t) = a + R * FF.slice(t) * q_inv * (e);
        C.slice(t) = R - R * FF.slice(t) * q_inv * FF.slice(t).t() * R.t();
        C.slice(t) = (C.slice(t) + C.slice(t).t()) / 2;

        // Compute standard forecast errors
        standard_forecast_errors.col(t) = q_inv_sqrt * (e);

        // K-step ahead forecast error calculations
        if (t + k < TT) {
            H = H_t_k_r(GG, t, k, k);
            a_1k = H * m.col(t-1);
            fk = FF.slice(t + k).t() * a_1k;
            Pk = H * C.slice(t-1) * H.t();
            R_1k = Pk + ex_df_mat_k % Pk;
            qk = FF.slice(t + k).t() * R_1k * FF.slice(t + k) + V_obs;

            qk_inv = as<arma::mat>(compute_cholesky(qk, false)["inverse"]);
            qk_inv_sqrt = as<arma::mat>(compute_cholesky(qk, true)["sqrt_inverse"]);

            // Compute k-step ahead forecast errors
            standard_forecast_errors_k.col(t) = qk_inv_sqrt * (y.col(t+k) - fk);
        }

        // Update nu_t and S_t for V
        arma::vec q_diag = q.diag();  // Diagonal of Q_t
        nu_t += 1;                  // Update degrees of freedom
        S_t +=  S_t/nu_t*(arma::square(e) / q_diag-1);  // Update scale
    }
    // Initialize the last smoothed state and covariance from the final filter step
    sC.slice(TT-1) = C.slice(TT-1);
    sm.col(TT-1) = m.col(TT-1);
    // Initialize ELBO
    elbo = 0;

// CHANGE THIS
    elbo -= 0.5 * log_det ;
    A = Eigen::Map<Eigen::MatrixXd>(sC.slice(TT-1).memptr(), sC.slice(TT-1).n_rows, sC.slice(TT-1).n_cols);
    log_det = logDetCholesky(A);
    elbo += 0.5 * log_det; 
    // Backward loop for smoothing and ELBO calculation
    for (int t = TT-2; t >= 0; --t) {
        // Rcpp::Rcout << t << std::endl;
        arma::vec a = GG.slice(t+1) * m.col(t);
        arma::mat P = GG.slice(t + 1)* C.slice(t) * GG.slice(t+1).t();
        arma::mat R = P % ex_df_mat + P; 
        R = (R + R.t()) / 2;  

        // Invert R using SVD
        arma::svd(U, s, V, R);
        arma::mat R_inv = U * arma::diagmat(1/s) * U.t();

        arma::mat sB = C.slice(t) * GG.slice(t+1).t() * R_inv;
        sm.col(t) = m.col(t) + sB * (sm.col(t+1) - a);
        sC.slice(t) = C.slice(t) + sB * (sC.slice(t+1) - R) * sB.t();
        sC.slice(t) = (sC.slice(t) + sC.slice(t).t()) / 2;

    }
    // Rcpp::Rcout << "Debug1" << std::endl;
    // Smoothing at time 0
    P = GG.slice(0) * C0 * GG.slice(0).t();
    R = P + ex_df_mat % P;  // Variance adjustment
    R = (R + R.t()) / 2;  // Ensuring symmetry
    // Rcpp::Rcout << "Debug2" << std::endl;
    // Invert R using SVD
    arma::svd(U, s, V, R);
    arma::mat R_inv = U * arma::diagmat(1/s) * U.t();

    arma::mat sB = C0 * GG.slice(0).t() * R_inv;
    arma::vec sm_0 = m0 + sB * (sm.col(0) - GG.slice(0) * m0);
    arma::mat sC_0 = C0 + sB * (sC.slice(0) - R) * sB.t();
    sC_0 = (sC_0 + sC_0.t()) / 2;

    // Return the full result list
    return List::create(Named("standard_forecast_errors") = standard_forecast_errors,
                        Named("standard_forecast_errors_k") = standard_forecast_errors_k,
                        Named("sm") = sm,
                        Named("sC") = sC,
                        Named("fm") = m, // Filtered states
                        Named("fC") = C, // Filtered covariances
                        Named("elbo.part") = elbo,
                        Named("nu_t") = nu_t,   // Posterior degrees of freedom for each diagonal element
                        Named("S_t") = S_t      // Posterior scales for each diagonal element
    );
}
