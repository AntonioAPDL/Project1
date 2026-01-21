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

// Function to regularize the matrix
arma::mat regularize(const arma::mat& matrix, double epsilon = 1e-15) {
    return matrix + epsilon * arma::eye<arma::mat>(matrix.n_rows, matrix.n_cols);
}

// Function to compute the robust SVD-based inversion
arma::mat robust_svd_inv(const arma::mat& matrix, double tolerance = 1e-20) {
    arma::mat U, V;
    arma::vec s;
    arma::svd(U, s, V, matrix);

    // Threshold small singular values and compute the inverse
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

    // Threshold small singular values and compute the inverse of the square root
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

            // Fill the block
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

std::vector<arma::cube> standard_forecast_errors_ens(J);    

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

int nrow_error = Rcpp::as<arma::mat>(y_list_ens[j-1]).col(0).n_rows;
standard_forecast_errors_ens[j-1] = arma::cube(nrow_error, 1, kkk_j, arma::fill::zeros);

}    

// arma::mat standard_forecast_errors_ens(tot_ens, k_ens[0], arma::fill::zeros);
// Rcpp::List standard_forecast_errors_ens = y_list_ens;

double elbo = 0.0;
double elbo_ens = 0.0;

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


//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////



int k_j = 0;

for (int j = J; j >= 1; --j) {

int kk = 0;
int index = J-j;

if (j == J) {
arma::mat GG_list_ens_mat = Rcpp::as<arma::mat>(GG_list_ens[index]);
a = GG_list_ens_mat * m.col(TT-1).subvec(0, p + j - 1);
P = GG_list_ens_mat * C.slice(TT-1).submat(0, 0, p + j - 1, p + j - 1) * GG_list_ens_mat.t();      
R = P % ex_df_mat_list_ens.slice(0).submat(0, 0, p + j - 1, p + j - 1) +  P % Ones_ens.submat(0, 0, p + j - 1, p + j - 1);  
} else {
//     arma::mat GG_list_ens_mat = Rcpp::as<arma::mat>(GG_list_ens[index]);
//     arma::mat sub_matrix = m_ens[index-1].subcube(0, 0, k_j-1, p + j - 1, 0, k_j-1);
//     a = GG_list_ens_mat * sub_matrix.col(0);
//     P = GG_list_ens_mat * C_ens[index-1].slice(k_j-1).submat(0, 0, p + j - 1, p + j - 1) * GG_list_ens_mat.t();  
//     R = P % ex_df_mat_list_ens.slice(1).submat(0, 0, p + j - 1, p + j - 1) +  P % Ones_ens.submat(0, 0, p + j - 1, p + j - 1);  
// }

arma::mat GG_list_ens_mat = Rcpp::as<arma::mat>(GG_list_ens[index]);
int last_slice_index = m_ens[index - 1].n_slices - 1;
arma::mat sub_matrix = m_ens[index - 1].subcube(0, 0, last_slice_index, p + j - 1, 0, last_slice_index);
a = GG_list_ens_mat * sub_matrix.col(0);
P = GG_list_ens_mat * C_ens[index - 1].slice(last_slice_index).submat(0, 0, p + j - 1, p + j - 1) * GG_list_ens_mat.t();
R = P % ex_df_mat_list_ens.slice(1).submat(0, 0, p + j - 1, p + j - 1) + P % Ones_ens.submat(0, 0, p + j - 1, p + j - 1);
}

R = (R + R.t()) / 2;  // Symmetrize the matrix
R = regularize(R);


arma::vec f_a = Rcpp::as<arma::mat>(FF_list_ens[index]).t() * a;
arma::vec sub_num_mem = num_mem.subvec(0, j-1);

arma::vec exp_f_a = repeat_vector(f_a, sub_num_mem);
f = exp_f_a + Rcpp::as<arma::mat>(ex_f_list_ens[index]).col(0);


arma::mat FF_slice = Rcpp::as<arma::mat>(FF_list_ens[index]);
arma::mat product = FF_slice.t() * R * FF_slice;
arma::mat expanded_matrix = expand_matrix(product, sub_num_mem);
q = expanded_matrix + Rcpp::as<arma::cube>(ex_q_list_ens[index]).slice(0);
q = (q + q.t()) / 2;  // Symmetrize the matrix

q_inv = robust_svd_inv(q);
q_inv_sqrt = robust_svd_inv_sqrt(q);

arma::mat expanded_FF = expand_FF(FF_slice, sub_num_mem);


arma::vec temp_vec = a + R * expanded_FF * q_inv * (Rcpp::as<arma::mat>(y_list_ens[index]).col(0) - f);
arma::mat temp_mat = R - R * expanded_FF * q_inv * expanded_FF.t() * R.t();
m_ens[index].slice(0) = temp_vec;
C_ens[index].slice(0) = temp_mat;
C_ens[index].slice(0) = (C_ens[index].slice(0) + C_ens[index].slice(0).t()) / 2;

// Compute standard forecast errors        
// Rcpp::as<arma::mat>(standard_forecast_errors_ens[index]).col(0) = q_inv_sqrt * (Rcpp::as<arma::mat>(y_list_ens[index]).col(0) - f);
standard_forecast_errors_ens[index].slice(0) = q_inv_sqrt * (Rcpp::as<arma::mat>(y_list_ens[index]).col(0) - f);



if (j < J) {
k_j = k_ens[j-1]-k_ens[j];
}else{
k_j = k_ens[j-1];
}

kk++;
while (kk < k_j) {
arma::mat GG_list_ens_mat = Rcpp::as<arma::mat>(GG_list_ens[index]);
arma::mat sub_matrix = m_ens[index].subcube(0, 0, kk-1, p + j - 1, 0, kk-1);
arma::vec a = GG_list_ens_mat * sub_matrix.col(0);

arma::mat P = GG_list_ens_mat * C_ens[index].slice(kk-1) * GG_list_ens_mat.t();
arma::mat R = P % ex_df_mat_list_ens.slice(1).submat(0, 0, p + j - 1, p + j - 1) + P % Ones_ens.submat(0, 0, p + j - 1, p + j - 1);

R = (R + R.t()) / 2;  // Symmetrize the matrix
R = regularize(R);

arma::vec f_a = Rcpp::as<arma::mat>(FF_list_ens[index]).t() * a;
arma::vec exp_f_a = repeat_vector(f_a, sub_num_mem);
arma::vec f = exp_f_a + Rcpp::as<arma::mat>(ex_f_list_ens[index]).col(kk);

arma::mat FF_slice = Rcpp::as<arma::mat>(FF_list_ens[index]);
arma::mat product = FF_slice.t() * R * FF_slice;
arma::mat expanded_matrix = expand_matrix(product, sub_num_mem);
arma::mat q = expanded_matrix + Rcpp::as<arma::cube>(ex_q_list_ens[index]).slice(kk);

q = (q + q.t()) / 2;  // Symmetrize the matrix

arma::mat q_inv = robust_svd_inv(q);
arma::mat q_inv_sqrt = robust_svd_inv_sqrt(q);

expanded_FF = expand_FF(FF_slice, sub_num_mem);
arma::vec temp_vec_ = a + R * expanded_FF * q_inv * (Rcpp::as<arma::mat>(y_list_ens[index]).col(kk) - f);
m_ens[index].slice(kk) = temp_vec_;
arma::mat temp_mat_ = R - R * expanded_FF * q_inv * expanded_FF.t() * R.t();
C_ens[index].slice(kk) = temp_mat_;
C_ens[index].slice(kk) = (C_ens[index].slice(kk) + C_ens[index].slice(kk).t()) / 2;
// Rcpp::as<arma::mat>(standard_forecast_errors_ens[index]).col(kk) = q_inv_sqrt * (Rcpp::as<arma::mat>(y_list_ens[index]).col(kk) - f);
standard_forecast_errors_ens[index].slice(kk) = q_inv_sqrt * (Rcpp::as<arma::mat>(y_list_ens[index]).col(kk) - f);
kk++;    
}

}

//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////

// Smoothing: After Forecast  
// Rcpp::Rcout << "Debug: Smoothing after forecast" << std::endl;

k_j = k_ens[0]-k_ens[1];
sm_ens[J-1].slice(k_j-1).col(0) = m_ens[J-1].slice(k_j-1).col(0);
sC_ens[J-1].slice(k_j-1) = C_ens[J-1].slice(k_j-1) ; 

//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////

for (int j = 0; j < J; ++j) {
// for (int j = J; j >= 1; --j) {

// j =      0   1   2   3  ... J-2  J-1  
// index = J-1 J-2 J-3 J-4 ...  1   0


if (j == (J-1) )  {
k_j = k_ens[j];
}else{
k_j = k_ens[j]-k_ens[(j+1)];
}

int kk = k_j-1;
int index = J-1-j;

// ADD SMOOTH FOR T+K_2, T+K_3, ..., T+K_J

if (index < (J-1)) {

// j   =      1     2     3   ...  J-2   J-1  
// index   = J-2   J-3   J-4  ...   1    0
// Th_dims = p+J-1 p+J-2 p+J-3     p+2  p+1

arma::mat GG_list_ens_mat = Rcpp::as<arma::mat>(GG_list_ens[index+1]);
arma::mat sub_matrix = m_ens[index].subcube(0, 0, k_j-1, (p+j) - 1, 0, k_j-1);
a = GG_list_ens_mat * sub_matrix.col(0);
P = GG_list_ens_mat * C_ens[index].slice(k_j-1).submat(0, 0, (p+j) - 1, (p+j) - 1) * GG_list_ens_mat.t();  
R = P % ex_df_mat_list_ens.slice(1).submat(0, 0, (p+j) - 1, (p+j) - 1) +  P % Ones_ens.submat(0, 0, (p+j) - 1, (p+j) - 1);  

////////////////////////////////////////////////////////

R = (R + R.t()) / 2;  
arma::mat R_inv = robust_svd_inv(R);

arma::mat sB = C_ens[index].slice(k_j-1).submat(0, 0, (p+j+1) - 1, (p+j) - 1) * GG_list_ens_mat.t() * R_inv;

// sm_ens[index].col(k_j-1) = m_ens[index].col(k_j-1) + sB * (sm_ens[index+1].col(0) - a);

arma::vec m_col = m_ens[index].slice(k_j-1).col(0);
arma::vec sm_next_col = sm_ens[index+1].slice(0).col(0);
arma::vec diff = sm_next_col - a;
arma::vec result = sB * diff;
sm_ens[index].slice(k_j-1).col(0) = m_col + result;

arma::mat C_slice = C_ens[index].slice(k_j-1);
arma::mat sC_next_slice = sC_ens[index+1].slice(0);
arma::mat diff_slices = sC_next_slice - R;
arma::mat intermediate_result = sB * diff_slices;
arma::mat final_result = intermediate_result * sB.t();
sC_ens[index].slice(k_j-1) = C_slice + final_result;
sC_ens[index].slice(k_j-1) = (sC_ens[index].slice(k_j-1) + sC_ens[index].slice(k_j-1).t()) / 2;

arma::mat W_t_1 = P % ex_df_mat_list_ens.slice(1).submat(0, 0, (p+j) - 1, (p+j) - 1);
arma::svd(U, s, V, W_t_1); 
arma::mat W_inv = U * arma::diagmat(1/s) * U.t();
arma::mat CBRB = sC_ens[index].slice(k_j-1)  - sB * sC_ens[index+1].slice(0) * sB.t();

A = Eigen::Map<Eigen::MatrixXd>(W_t_1.memptr(), W_t_1.n_rows, W_t_1.n_cols);
log_det = logDetCholesky(A);
elbo_ens -= 0.5 * log_det; 

A = Eigen::Map<Eigen::MatrixXd>(CBRB.memptr(), CBRB.n_rows, CBRB.n_cols); 
log_det = logDetCholesky(A);
elbo_ens += 0.5 * log_det; 

arma::vec ee = sm_next_col - a;
arma::mat XX = sC_next_slice + P;
arma::mat intermediate1 = P * R_inv;
arma::mat intermediate2 = intermediate1 * sC_next_slice;
XX = XX - 2 * intermediate2 + ee * ee.t();

arma::mat xXX =  arma::solve(W_t_1, XX);
elbo_ens -= 0.5 * arma::accu(xXX.diag());

// a = GG_ens.slice(0) * m.col(k_j-1).subvec(0, p + j - 1);
CBRB = sC_ens[index].slice(k_j-1)  - sB*sC_next_slice*sB.t();
arma::svd(U, s, V, CBRB);
arma::mat CBRB_inv = U * arma::diagmat(1/s) * U.t();

//// CHECK THIS PART!!!!!!
// // arma::mat xx = sm_ens[index].col(k_j-1) - m_col - result; // SAME AS BELOW?
// arma::vec xx = sm_ens[index].col(k_j-1) - m_ens[index].col(k_j-1) - sB * (sm_next_col - a);
// arma::mat xxxx = CBRB_inv * (xx * xx.t());
// elbo += 0.5 * arma::accu(xxxx.diag());

arma::vec sm_col = sm_ens[index].slice(k_j-1).col(0);
arma::vec diff_sm_a = sm_next_col - a;
arma::vec intermediate_result3 = sB * diff_sm_a;
arma::vec xx = sm_col - m_col - intermediate_result3;
arma::mat outer_product = xx * xx.t();
arma::mat xxxx = CBRB_inv * outer_product;
elbo_ens += 0.5 * arma::accu(xxxx.diag());

A = Eigen::Map<Eigen::MatrixXd>(CBRB.memptr(), CBRB.n_rows, CBRB.n_cols); 
log_det = logDetCholesky(A);
elbo_ens += 0.5 * log_det; 

//////////////////////////////////////////////////////
}

kk--;
while (kk >= 0) {

arma::mat GG_list_ens_mat = Rcpp::as<arma::mat>(GG_list_ens[index]);
arma::mat sub_matrix = m_ens[index].slice(kk);

arma::vec a = GG_list_ens_mat * sub_matrix.col(0);
arma::mat C_slice = C_ens[index].slice(kk);

arma::mat P = GG_list_ens_mat * C_slice * GG_list_ens_mat.t();

arma::mat R = P % ex_df_mat_list_ens.slice(1).submat(0, 0, p + j, p + j) + P % Ones_ens.submat(0, 0, p + j, p + j);

R = (R + R.t()) / 2;  
arma::mat R_inv = robust_svd_inv(R);


// Compute sB matrix
arma::mat sB = C_slice * GG_list_ens_mat.t() * R_inv;

// Update sm_ens with intermediate results
arma::vec sm_col_ = sm_ens[index].slice(kk).col(0);
arma::vec sm_next_col_ = sm_ens[index].slice(kk+1).col(0);
arma::vec diff_sm_a_ = sm_next_col_ - a;
sm_ens[index].slice(kk).col(0) = sub_matrix.col(0) + sB * diff_sm_a_;


// Update sC_ens with intermediate results
arma::mat sC_next_slice = sC_ens[index].slice(kk+1);
arma::mat diff_slices = sC_next_slice - R;
arma::mat intermediate_result = sB * diff_slices;
sC_ens[index].slice(kk) = C_slice + intermediate_result * sB.t();
sC_ens[index].slice(kk) = (sC_ens[index].slice(kk) + sC_ens[index].slice(kk).t()) / 2;

// Calculate W_t_1 and its inverse
arma::mat W_t_1 = P % ex_df_mat_list_ens.slice(1).submat(0, 0, p + j, p + j);
arma::svd(U, s, V, W_t_1);
arma::mat W_inv = U * arma::diagmat(1/s) * U.t();

// Calculate CBRB matrix and its inverse
arma::mat CBRB = sC_ens[index].slice(kk) - sB * sC_next_slice * sB.t();
arma::svd(U, s, V, CBRB);
arma::mat CBRB_inv = U * arma::diagmat(1/s) * U.t();

// Compute log determinant for W_t_1 and update elbo
A = Eigen::Map<Eigen::MatrixXd>(W_t_1.memptr(), W_t_1.n_rows, W_t_1.n_cols);
log_det = logDetCholesky(A);
elbo_ens -= 0.5 * log_det; 

// Update XX and elbo
arma::vec ee_ = sm_next_col_ - GG_list_ens_mat * sm_col_;
arma::mat XX_ = sC_next_slice + P - 2 * sB * sC_next_slice * sB.t() + ee_ * ee_.t();
arma::mat xXX_ = W_inv * XX_;
elbo_ens -= 0.5 * arma::accu(xXX_.diag());

// // Update xx and elbo
arma::vec m_col_ = m_ens[index].slice(kk).col(0);
arma::vec xx = sm_col_ - m_col_ - sB * diff_sm_a_;
arma::mat outer_product = xx * xx.t();
arma::mat xxxx = CBRB_inv * outer_product;
elbo_ens += 0.5 * arma::accu(xxxx.diag());

// Compute log determinant for CBRB and update elbo
A = Eigen::Map<Eigen::MatrixXd>(CBRB.memptr(), CBRB.n_rows, CBRB.n_cols); 
log_det = logDetCholesky(A);
elbo_ens += 0.5 * log_det; 


kk--;    
}

}


//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////


// // Smoothing: Before Forecast  


arma::mat GG_list_ens_mat = Rcpp::as<arma::mat>(GG_list_ens[0]);
arma::mat sub_matrix = m.col(TT-1).subvec(0, p + J - 1);
a = GG_list_ens_mat * sub_matrix.col(0);
P = GG_list_ens_mat * C.slice(TT-1).submat(0, 0, p + J - 1, p + J - 1) * GG_list_ens_mat.t();  
R = P % ex_df_mat_list_ens.slice(0).submat(0, 0, (p+J) - 1, (p+J) - 1) +  P % Ones_ens.submat(0, 0, (p+J) - 1, (p+J) - 1);  

R = (R + R.t()) / 2;  
arma::mat R_inv = robust_svd_inv(R);

arma::mat sB = C.slice(TT-1).submat(0, 0, p + J + ppx - 1, p + J - 1) * GG_list_ens_mat.t() * R_inv;

arma::vec m_col =  m_ens[0].subcube(0, 0, 0, p + J - 1, 0, 0);
arma::vec sm_col =  sm_ens[0].subcube(0, 0, 0, p + J - 1, 0, 0);
arma::mat C_slice = C_ens[0].slice(0);
arma::mat sC_slice = sC_ens[0].slice(0);

sm.col(TT-1) = m.col(TT-1) + sB * (sm_col - a);
sC.slice(TT-1) = C.slice(TT-1) + sB * (sC_slice - R) * sB.t();
sC.slice(TT-1) = (sC.slice(TT-1) + sC.slice(TT-1).t()) / 2;

arma::mat W_t_1 = P % ex_df_mat_list_ens.slice(0).submat(0, 0, (p+J) - 1, (p+J) - 1);
arma::svd(U, s, V, W_t_1); 
arma::mat W_inv = U * arma::diagmat(1/s) * U.t();
arma::mat CBRB = sC.slice(TT-1) - sB * sC_slice * sB.t();

A = Eigen::Map<Eigen::MatrixXd>(W_t_1.memptr(), W_t_1.n_rows, W_t_1.n_cols);
log_det = logDetCholesky(A);
elbo_ens -= 0.5 * log_det; 

A = Eigen::Map<Eigen::MatrixXd>(CBRB.memptr(), CBRB.n_rows, CBRB.n_cols); 
log_det = logDetCholesky(A);
elbo_ens += 0.5 * log_det; 

arma::vec ee = sm_col - GG_list_ens_mat * sm.col(TT-1).subvec(0, p + J - 1);
arma::mat XX = sC_slice + GG_list_ens_mat * sC.slice(TT-1).submat(0, 0, p + J - 1, p + J - 1) * GG_list_ens_mat.t();
XX = XX - 2*(P*R_inv*sC_slice) + ee * ee.t();

arma::mat xXX =  arma::solve(W_t_1, XX);
elbo_ens -= 0.5 * arma::accu(xXX.diag());

a = GG_list_ens_mat * m.col(TT-1).subvec(0, p + J - 1);
CBRB = sC.slice(TT-1) - sB*sC_slice*sB.t();
arma::svd(U, s, V, CBRB);
arma::mat CBRB_inv = U * arma::diagmat(1/s) * U.t();

arma::vec xx = sm.col(TT-1) - m.col(TT-1) - sB * (sm_col- a);
arma::mat xxxx = CBRB_inv * (xx * xx.t());
elbo_ens += 0.5 * arma::accu(xxxx.diag());

A = Eigen::Map<Eigen::MatrixXd>(CBRB.memptr(), CBRB.n_rows, CBRB.n_cols); 
log_det = logDetCholesky(A);
elbo_ens += 0.5 * log_det; 

for (int t = TT-2; t >= 0; --t) {
a = GG.slice(t+1) * m.col(t);
P = GG.slice(t + 1)* C.slice(t) * GG.slice(t+1).t();
R = P % ex_df_mat + P % Ones; // Redundant multipication by Ones
R = (R + R.t()) / 2;  
R_inv = robust_svd_inv(R);

sB = C.slice(t) * GG.slice(t+1).t() * R_inv;
sm.col(t) = m.col(t) + sB * (sm.col(t+1) - a);
sC.slice(t) = C.slice(t) + sB * (sC.slice(t+1) - R) * sB.t();
sC.slice(t) = (sC.slice(t) + sC.slice(t).t()) / 2;

W_t_1 = ex_df_mat % P;
arma::svd(U, s, V, W_t_1); 
W_inv = U * arma::diagmat(1/s) * U.t();
CBRB = sC.slice(t) - sB * sC.slice(t+1) * sB.t();

A = Eigen::Map<Eigen::MatrixXd>(W_t_1.memptr(), W_t_1.n_rows, W_t_1.n_cols);
log_det = logDetCholesky(A);
elbo -= 0.5 * log_det; 

A = Eigen::Map<Eigen::MatrixXd>(CBRB.memptr(), CBRB.n_rows, CBRB.n_cols); 
log_det = logDetCholesky(A);
elbo += 0.5 * log_det; 

arma::vec ee = sm.col(t+1) - GG.slice(t+1) * sm.col(t);
arma::mat XX = sC.slice(t+1) + GG.slice(t+1)*sC.slice(t)*GG.slice(t+1).t();
XX = XX - 2*( P*R_inv*sC.slice(t+1)) + ee * ee.t();

arma::mat xXX =  arma::solve(W_t_1, XX);
elbo -= 0.5 * arma::accu(xXX.diag());

a = GG.slice(t+1) * m.col(t);
CBRB = sC.slice(t) - sB * sC.slice(t+1) * sB.t();
arma::svd(U, s, V, CBRB);
CBRB_inv = U * arma::diagmat(1/s) * U.t();

xx = sm.col(t) - m.col(t) - sB * (sm.col(t+1) - a);
xxxx = CBRB_inv * (xx * xx.t());
elbo += 0.5 * arma::accu(xxxx.diag());

A = Eigen::Map<Eigen::MatrixXd>(CBRB.memptr(), CBRB.n_rows, CBRB.n_cols); 
log_det = logDetCholesky(A);
elbo += 0.5 * log_det; 
}

// Smoothing at time 0
P = GG.slice(0) * C0 * GG.slice(0).t();
R = P + ex_df_mat % P;  // Variance adjustment
R = (R + R.t()) / 2;  // Ensuring symmetry
R = regularize(R);
R_inv = robust_svd_inv(R);

sB = C0 * GG.slice(0).t() * R_inv;
arma::vec sm_0 = m0 + sB * (sm.col(0) - GG.slice(0) * m0);
arma::mat sC_0 = C0 + sB * (sC.slice(0) - R) * sB.t();
sC_0 = (sC_0 + sC_0.t()) / 2;

W_t_1 = ex_df_mat % P;
arma::svd(U, s, V, W_t_1);  // Reuse U, s, V for another SVD
W_inv = U * arma::diagmat(1/s) * U.t();

ee = sm.col(0) - GG.slice(0) * sm_0;
XX = sC.slice(0) + P - 2 * sB * sC.slice(0) + ee * ee.t();
XX = W_inv * XX;
elbo -= 0.5 * arma::accu(XX.diag());

arma::mat XXX = sC_0 + (sm_0 - m0) * (sm_0 - m0).t();
XXX = arma::solve(C0, XXX);
elbo -= 0.5 * arma::accu(XXX.diag());

a = GG.slice(0) * m0;
CBRB = sC_0 - sB * sC.slice(0) * sB.t();
arma::svd(U, s, V, CBRB);
CBRB_inv = U * arma::diagmat(1/s) * U.t();
xx = sm_0 - m0 - sB * (sm.col(0) - a);
xxxx = CBRB_inv * (xx * xx.t());
elbo += 0.5 * arma::accu(xxxx.diag());

A = Eigen::Map<Eigen::MatrixXd>(CBRB.memptr(), CBRB.n_rows, CBRB.n_cols); 
log_det = logDetCholesky(A);
elbo += 0.5 * log_det; 

return List::create(Named("standard_forecast_errors") = standard_forecast_errors,
Named("sm") = sm,
Named("sC") = sC,
Named("fm") = m, 
Named("fC") = C, 
Named("elbo.part") = elbo,
Named("elbo.part_ens") = elbo_ens,
Named("standard_forecast_errors_ens") = standard_forecast_errors_ens,
Named("sm_ens") = sm_ens,
Named("sC_ens") = sC_ens,
Named("fm_ens") = m_ens, 
Named("fC_ens") = C_ens);
}



//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////


// [[Rcpp::export]]
Rcpp::List update_theta_synth_cpp_W(arma::cube GG, 
    arma::vec m0, arma::mat C0, 
    arma::mat ex_f, arma::cube ex_q, arma::cube FF, 
    arma::mat y, arma::mat ex_df_mat, arma::mat ex_df_mat_k, 
    arma::mat Ones, int p, int J, int ppx, int TT, int k, int dM,
    Rcpp::List GG_list_ens, Rcpp::List FF_list_ens,
    Rcpp::List ex_f_list_ens, Rcpp::List ex_q_list_ens,
    arma::cube ex_df_mat_list_ens, arma::cube ex_df_mat_k_list_ens,
    Rcpp::List y_list_ens, arma::vec k_ens, arma::mat Ones_ens,
    int tot_ens, arma::vec num_mem,
    Rcpp::List W_list_ens) {

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

std::vector<arma::cube> standard_forecast_errors_ens(J);    

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

int nrow_error = Rcpp::as<arma::mat>(y_list_ens[j-1]).col(0).n_rows;
standard_forecast_errors_ens[j-1] = arma::cube(nrow_error, 1, kkk_j, arma::fill::zeros);

}    

// arma::mat standard_forecast_errors_ens(tot_ens, k_ens[0], arma::fill::zeros);
// Rcpp::List standard_forecast_errors_ens = y_list_ens;

double elbo = 0.0;
double elbo_ens = 0.0;

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

arma::mat W_T = GG.slice(TT-1) * C.slice(TT-2) * GG.slice(TT-1).t() % ex_df_mat ;

//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////



int k_j = 0;

for (int j = J; j >= 1; --j) {

int kk = 0;
int index = J-j;


if (j == J) {
arma::mat GG_list_ens_mat = Rcpp::as<arma::mat>(GG_list_ens[index]);
arma::cube W_list_ens_cube = Rcpp::as<arma::cube>(W_list_ens[index]);
arma::mat W_list_ens_mat = W_list_ens_cube.slice(0);
a = GG_list_ens_mat * m.col(TT-1).subvec(0, p + j - 1);
P = GG_list_ens_mat * C.slice(TT-1).submat(0, 0, p + j - 1, p + j - 1) * GG_list_ens_mat.t();      
// R = P % ex_df_mat_list_ens.slice(0).submat(0, 0, p + j - 1, p + j - 1) +  P % Ones_ens.submat(0, 0, p + j - 1, p + j - 1);  
R = W_list_ens_mat +  P % Ones_ens.submat(0, 0, p + j - 1, p + j - 1);  

} else {

arma::mat GG_list_ens_mat = Rcpp::as<arma::mat>(GG_list_ens[index]);
int last_slice_index = m_ens[index - 1].n_slices - 1;
arma::cube W_list_ens_cube = Rcpp::as<arma::cube>(W_list_ens[index]);
arma::mat W_list_ens_mat = W_list_ens_cube.slice(0);
arma::mat sub_matrix = m_ens[index - 1].subcube(0, 0, last_slice_index, p + j - 1, 0, last_slice_index);
a = GG_list_ens_mat * sub_matrix.col(0);
P = GG_list_ens_mat * C_ens[index - 1].slice(last_slice_index).submat(0, 0, p + j - 1, p + j - 1) * GG_list_ens_mat.t();
// R = P % ex_df_mat_list_ens.slice(0).submat(0, 0, p + j - 1, p + j - 1) +  P % Ones_ens.submat(0, 0, p + j - 1, p + j - 1);  
R = W_list_ens_mat +  P % Ones_ens.submat(0, 0, p + j - 1, p + j - 1);  

}

R = (R + R.t()) / 2;  // Symmetrize the matrix
R = regularize(R);


arma::vec f_a = Rcpp::as<arma::mat>(FF_list_ens[index]).t() * a;
arma::vec sub_num_mem = num_mem.subvec(0, j-1);

arma::vec exp_f_a = repeat_vector(f_a, sub_num_mem);
f = exp_f_a + Rcpp::as<arma::mat>(ex_f_list_ens[index]).col(0);


arma::mat FF_slice = Rcpp::as<arma::mat>(FF_list_ens[index]);
arma::mat product = FF_slice.t() * R * FF_slice;
arma::mat expanded_matrix = expand_matrix(product, sub_num_mem);
q = expanded_matrix + Rcpp::as<arma::cube>(ex_q_list_ens[index]).slice(0);
q = (q + q.t()) / 2;  // Symmetrize the matrix

q_inv = robust_svd_inv(q);
q_inv_sqrt = robust_svd_inv_sqrt(q);

arma::mat expanded_FF = expand_FF(FF_slice, sub_num_mem);


arma::vec temp_vec = a + R * expanded_FF * q_inv * (Rcpp::as<arma::mat>(y_list_ens[index]).col(0) - f);
arma::mat temp_mat = R - R * expanded_FF * q_inv * expanded_FF.t() * R.t();
m_ens[index].slice(0) = temp_vec;
C_ens[index].slice(0) = temp_mat;
C_ens[index].slice(0) = (C_ens[index].slice(0) + C_ens[index].slice(0).t()) / 2;

// Compute standard forecast errors        
// Rcpp::as<arma::mat>(standard_forecast_errors_ens[index]).col(0) = q_inv_sqrt * (Rcpp::as<arma::mat>(y_list_ens[index]).col(0) - f);
standard_forecast_errors_ens[index].slice(0) = q_inv_sqrt * (Rcpp::as<arma::mat>(y_list_ens[index]).col(0) - f);



if (j < J) {
k_j = k_ens[j-1]-k_ens[j];
}else{
k_j = k_ens[j-1];
}

kk++;
while (kk < k_j) {
arma::mat GG_list_ens_mat = Rcpp::as<arma::mat>(GG_list_ens[index]);
arma::cube W_list_ens_cube = Rcpp::as<arma::cube>(W_list_ens[index]);
arma::mat W_list_ens_mat = W_list_ens_cube.slice(kk); 
arma::mat sub_matrix = m_ens[index].subcube(0, 0, kk-1, p + j - 1, 0, kk-1);
arma::vec a = GG_list_ens_mat * sub_matrix.col(0);
arma::mat P = GG_list_ens_mat * C_ens[index].slice(kk-1) * GG_list_ens_mat.t();
// arma::mat R = P % ex_df_mat_list_ens.slice(1).submat(0, 0, p + j - 1, p + j - 1) + P % Ones_ens.submat(0, 0, p + j - 1, p + j - 1);
arma::mat R = W_list_ens_mat + P % Ones_ens.submat(0, 0, p + j - 1, p + j - 1);

R = (R + R.t()) / 2;  // Symmetrize the matrix
R = regularize(R);

arma::vec f_a = Rcpp::as<arma::mat>(FF_list_ens[index]).t() * a;
arma::vec exp_f_a = repeat_vector(f_a, sub_num_mem);
arma::vec f = exp_f_a + Rcpp::as<arma::mat>(ex_f_list_ens[index]).col(kk);

arma::mat FF_slice = Rcpp::as<arma::mat>(FF_list_ens[index]);
arma::mat product = FF_slice.t() * R * FF_slice;
arma::mat expanded_matrix = expand_matrix(product, sub_num_mem);
arma::mat q = expanded_matrix + Rcpp::as<arma::cube>(ex_q_list_ens[index]).slice(kk);

q = (q + q.t()) / 2;  // Symmetrize the matrix

arma::mat q_inv = robust_svd_inv(q);
arma::mat q_inv_sqrt = robust_svd_inv_sqrt(q);

expanded_FF = expand_FF(FF_slice, sub_num_mem);
arma::vec temp_vec_ = a + R * expanded_FF * q_inv * (Rcpp::as<arma::mat>(y_list_ens[index]).col(kk) - f);
m_ens[index].slice(kk) = temp_vec_;
arma::mat temp_mat_ = R - R * expanded_FF * q_inv * expanded_FF.t() * R.t();
C_ens[index].slice(kk) = temp_mat_;
C_ens[index].slice(kk) = (C_ens[index].slice(kk) + C_ens[index].slice(kk).t()) / 2;
// Rcpp::as<arma::mat>(standard_forecast_errors_ens[index]).col(kk) = q_inv_sqrt * (Rcpp::as<arma::mat>(y_list_ens[index]).col(kk) - f);
standard_forecast_errors_ens[index].slice(kk) = q_inv_sqrt * (Rcpp::as<arma::mat>(y_list_ens[index]).col(kk) - f);
kk++;    
}

}

//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////

// Smoothing: After Forecast  
// Rcpp::Rcout << "Debug: Smoothing after forecast" << std::endl;

k_j = k_ens[0]-k_ens[1];
sm_ens[J-1].slice(k_j-1).col(0) = m_ens[J-1].slice(k_j-1).col(0);
sC_ens[J-1].slice(k_j-1) = C_ens[J-1].slice(k_j-1) ; 

//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////

for (int j = 0; j < J; ++j) {
// for (int j = J; j >= 1; --j) {

// j =      0   1   2   3  ... J-2  J-1  
// index = J-1 J-2 J-3 J-4 ...  1   0


if (j == (J-1) )  {
k_j = k_ens[j];
}else{
k_j = k_ens[j]-k_ens[(j+1)];
}

int kk = k_j-1;
int index = J-1-j;

// ADD SMOOTH FOR T+K_2, T+K_3, ..., T+K_J

if (index < (J-1)) {

// j   =      1     2     3   ...  J-2   J-1  
// index   = J-2   J-3   J-4  ...   1    0
// Th_dims = p+J-1 p+J-2 p+J-3     p+2  p+1

arma::mat GG_list_ens_mat = Rcpp::as<arma::mat>(GG_list_ens[index+1]);
arma::cube W_list_ens_cube = Rcpp::as<arma::mat>(W_list_ens[index+1]);
arma::mat W_list_ens_mat = W_list_ens_cube.slice(k_j);  
arma::mat sub_matrix = m_ens[index].subcube(0, 0, k_j-1, (p+j) - 1, 0, k_j-1);
a = GG_list_ens_mat * sub_matrix.col(0);
P = GG_list_ens_mat * C_ens[index].slice(k_j-1).submat(0, 0, (p+j) - 1, (p+j) - 1) * GG_list_ens_mat.t();  
// R = P % ex_df_mat_list_ens.slice(1).submat(0, 0, (p+j) - 1, (p+j) - 1) +  P % Ones_ens.submat(0, 0, (p+j) - 1, (p+j) - 1);  
R = W_list_ens_mat +  P % Ones_ens.submat(0, 0, (p+j) - 1, (p+j) - 1);  

////////////////////////////////////////////////////////

R = (R + R.t()) / 2;  
arma::mat R_inv = robust_svd_inv(R);

arma::mat sB = C_ens[index].slice(k_j-1).submat(0, 0, (p+j+1) - 1, (p+j) - 1) * GG_list_ens_mat.t() * R_inv;

// sm_ens[index].col(k_j-1) = m_ens[index].col(k_j-1) + sB * (sm_ens[index+1].col(0) - a);

arma::vec m_col = m_ens[index].slice(k_j-1).col(0);
arma::vec sm_next_col = sm_ens[index+1].slice(0).col(0);
arma::vec diff = sm_next_col - a;
arma::vec result = sB * diff;
sm_ens[index].slice(k_j-1).col(0) = m_col + result;

arma::mat C_slice = C_ens[index].slice(k_j-1);
arma::mat sC_next_slice = sC_ens[index+1].slice(0);
arma::mat diff_slices = sC_next_slice - R;
arma::mat intermediate_result = sB * diff_slices;
arma::mat final_result = intermediate_result * sB.t();
sC_ens[index].slice(k_j-1) = C_slice + final_result;
sC_ens[index].slice(k_j-1) = (sC_ens[index].slice(k_j-1) + sC_ens[index].slice(k_j-1).t()) / 2;

arma::mat W_t_1 = P % ex_df_mat_list_ens.slice(1).submat(0, 0, (p+j) - 1, (p+j) - 1);
arma::svd(U, s, V, W_t_1); 
arma::mat W_inv = U * arma::diagmat(1/s) * U.t();
arma::mat CBRB = sC_ens[index].slice(k_j-1)  - sB * sC_ens[index+1].slice(0) * sB.t();

A = Eigen::Map<Eigen::MatrixXd>(W_t_1.memptr(), W_t_1.n_rows, W_t_1.n_cols);
log_det = logDetCholesky(A);
elbo_ens -= 0.5 * log_det; 

A = Eigen::Map<Eigen::MatrixXd>(CBRB.memptr(), CBRB.n_rows, CBRB.n_cols); 
log_det = logDetCholesky(A);
elbo_ens += 0.5 * log_det; 

arma::vec ee = sm_next_col - a;
arma::mat XX = sC_next_slice + P;
arma::mat intermediate1 = P * R_inv;
arma::mat intermediate2 = intermediate1 * sC_next_slice;
XX = XX - 2 * intermediate2 + ee * ee.t();

arma::mat xXX =  arma::solve(W_t_1, XX);
elbo_ens -= 0.5 * arma::accu(xXX.diag());

// a = GG_ens.slice(0) * m.col(k_j-1).subvec(0, p + j - 1);
CBRB = sC_ens[index].slice(k_j-1)  - sB*sC_next_slice*sB.t();
arma::svd(U, s, V, CBRB);
arma::mat CBRB_inv = U * arma::diagmat(1/s) * U.t();


arma::vec sm_col = sm_ens[index].slice(k_j-1).col(0);
arma::vec diff_sm_a = sm_next_col - a;
arma::vec intermediate_result3 = sB * diff_sm_a;
arma::vec xx = sm_col - m_col - intermediate_result3;
arma::mat outer_product = xx * xx.t();
arma::mat xxxx = CBRB_inv * outer_product;
elbo_ens += 0.5 * arma::accu(xxxx.diag());

A = Eigen::Map<Eigen::MatrixXd>(CBRB.memptr(), CBRB.n_rows, CBRB.n_cols); 
log_det = logDetCholesky(A);
elbo_ens += 0.5 * log_det; 

//////////////////////////////////////////////////////
}

kk--;
while (kk >= 0) {

arma::mat GG_list_ens_mat = Rcpp::as<arma::mat>(GG_list_ens[index]);
arma::cube W_list_ens_cube = Rcpp::as<arma::mat>(W_list_ens[index]);
arma::mat W_list_ens_mat = W_list_ens_cube.slice(kk+1); 
arma::mat sub_matrix = m_ens[index].slice(kk);
arma::vec a = GG_list_ens_mat * sub_matrix.col(0);
arma::mat C_slice = C_ens[index].slice(kk);
arma::mat P = GG_list_ens_mat * C_slice * GG_list_ens_mat.t();
// arma::mat R = P % ex_df_mat_list_ens.slice(1).submat(0, 0, p + j, p + j) + P % Ones_ens.submat(0, 0, p + j, p + j);
arma::mat R = W_list_ens_mat + P % Ones_ens.submat(0, 0, p + j, p + j);

R = (R + R.t()) / 2;  
arma::mat R_inv = robust_svd_inv(R);


// Compute sB matrix
arma::mat sB = C_slice * GG_list_ens_mat.t() * R_inv;

// Update sm_ens with intermediate results
arma::vec sm_col_ = sm_ens[index].slice(kk).col(0);
arma::vec sm_next_col_ = sm_ens[index].slice(kk+1).col(0);
arma::vec diff_sm_a_ = sm_next_col_ - a;
sm_ens[index].slice(kk).col(0) = sub_matrix.col(0) + sB * diff_sm_a_;


// Update sC_ens with intermediate results
arma::mat sC_next_slice = sC_ens[index].slice(kk+1);
arma::mat diff_slices = sC_next_slice - R;
arma::mat intermediate_result = sB * diff_slices;
sC_ens[index].slice(kk) = C_slice + intermediate_result * sB.t();
sC_ens[index].slice(kk) = (sC_ens[index].slice(kk) + sC_ens[index].slice(kk).t()) / 2;

// Calculate W_t_1 and its inverse
arma::mat W_t_1 = P % ex_df_mat_list_ens.slice(1).submat(0, 0, p + j, p + j);
arma::svd(U, s, V, W_t_1);
arma::mat W_inv = U * arma::diagmat(1/s) * U.t();

// Calculate CBRB matrix and its inverse
arma::mat CBRB = sC_ens[index].slice(kk) - sB * sC_next_slice * sB.t();
arma::svd(U, s, V, CBRB);
arma::mat CBRB_inv = U * arma::diagmat(1/s) * U.t();

// Compute log determinant for W_t_1 and update elbo
A = Eigen::Map<Eigen::MatrixXd>(W_t_1.memptr(), W_t_1.n_rows, W_t_1.n_cols);
log_det = logDetCholesky(A);
elbo_ens -= 0.5 * log_det; 

// Update XX and elbo
arma::vec ee_ = sm_next_col_ - GG_list_ens_mat * sm_col_;
arma::mat XX_ = sC_next_slice + P - 2 * sB * sC_next_slice * sB.t() + ee_ * ee_.t();
arma::mat xXX_ = W_inv * XX_;
elbo_ens -= 0.5 * arma::accu(xXX_.diag());

// // Update xx and elbo
arma::vec m_col_ = m_ens[index].slice(kk).col(0);
arma::vec xx = sm_col_ - m_col_ - sB * diff_sm_a_;
arma::mat outer_product = xx * xx.t();
arma::mat xxxx = CBRB_inv * outer_product;
elbo_ens += 0.5 * arma::accu(xxxx.diag());

// Compute log determinant for CBRB and update elbo
A = Eigen::Map<Eigen::MatrixXd>(CBRB.memptr(), CBRB.n_rows, CBRB.n_cols); 
log_det = logDetCholesky(A);
elbo_ens += 0.5 * log_det; 


kk--;    
}

}


//////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////


// // Smoothing: Before Forecast  


arma::mat GG_list_ens_mat = Rcpp::as<arma::mat>(GG_list_ens[0]);
arma::cube W_list_ens_cube = Rcpp::as<arma::mat>(W_list_ens[0]);
arma::mat W_list_ens_mat = W_list_ens_cube.slice(0);  
arma::mat sub_matrix = m.col(TT-1).subvec(0, p + J - 1);
a = GG_list_ens_mat * sub_matrix.col(0);
P = GG_list_ens_mat * C.slice(TT-1).submat(0, 0, p + J - 1, p + J - 1) * GG_list_ens_mat.t();  
// R = P % ex_df_mat_list_ens.slice(0).submat(0, 0, (p+J) - 1, (p+J) - 1) +  P % Ones_ens.submat(0, 0, (p+J) - 1, (p+J) - 1);  
R = W_list_ens_mat +  P % Ones_ens.submat(0, 0, (p+J) - 1, (p+J) - 1);  

R = (R + R.t()) / 2;  
arma::mat R_inv = robust_svd_inv(R);

arma::mat sB = C.slice(TT-1).submat(0, 0, p + J + ppx - 1, p + J - 1) * GG_list_ens_mat.t() * R_inv;

arma::vec m_col =  m_ens[0].subcube(0, 0, 0, p + J - 1, 0, 0);
arma::vec sm_col =  sm_ens[0].subcube(0, 0, 0, p + J - 1, 0, 0);
arma::mat C_slice = C_ens[0].slice(0);
arma::mat sC_slice = sC_ens[0].slice(0);

sm.col(TT-1) = m.col(TT-1) + sB * (sm_col - a);
sC.slice(TT-1) = C.slice(TT-1) + sB * (sC_slice - R) * sB.t();
sC.slice(TT-1) = (sC.slice(TT-1) + sC.slice(TT-1).t()) / 2;

arma::mat W_t_1 = P % ex_df_mat_list_ens.slice(0).submat(0, 0, (p+J) - 1, (p+J) - 1);
arma::svd(U, s, V, W_t_1); 
arma::mat W_inv = U * arma::diagmat(1/s) * U.t();
arma::mat CBRB = sC.slice(TT-1) - sB * sC_slice * sB.t();

A = Eigen::Map<Eigen::MatrixXd>(W_t_1.memptr(), W_t_1.n_rows, W_t_1.n_cols);
log_det = logDetCholesky(A);
elbo_ens -= 0.5 * log_det; 

A = Eigen::Map<Eigen::MatrixXd>(CBRB.memptr(), CBRB.n_rows, CBRB.n_cols); 
log_det = logDetCholesky(A);
elbo_ens += 0.5 * log_det; 

arma::vec ee = sm_col - GG_list_ens_mat * sm.col(TT-1).subvec(0, p + J - 1);
arma::mat XX = sC_slice + GG_list_ens_mat * sC.slice(TT-1).submat(0, 0, p + J - 1, p + J - 1) * GG_list_ens_mat.t();
XX = XX - 2*(P*R_inv*sC_slice) + ee * ee.t();

arma::mat xXX =  arma::solve(W_t_1, XX);
elbo_ens -= 0.5 * arma::accu(xXX.diag());

a = GG_list_ens_mat * m.col(TT-1).subvec(0, p + J - 1);
CBRB = sC.slice(TT-1) - sB*sC_slice*sB.t();
arma::svd(U, s, V, CBRB);
arma::mat CBRB_inv = U * arma::diagmat(1/s) * U.t();

arma::vec xx = sm.col(TT-1) - m.col(TT-1) - sB * (sm_col- a);
arma::mat xxxx = CBRB_inv * (xx * xx.t());
elbo_ens += 0.5 * arma::accu(xxxx.diag());

A = Eigen::Map<Eigen::MatrixXd>(CBRB.memptr(), CBRB.n_rows, CBRB.n_cols); 
log_det = logDetCholesky(A);
elbo_ens += 0.5 * log_det; 

for (int t = TT-2; t >= 0; --t) {
a = GG.slice(t+1) * m.col(t);
P = GG.slice(t + 1)* C.slice(t) * GG.slice(t+1).t();
R = P % ex_df_mat + P % Ones; // Redundant multipication by Ones
R = (R + R.t()) / 2;  
R_inv = robust_svd_inv(R);

sB = C.slice(t) * GG.slice(t+1).t() * R_inv;
sm.col(t) = m.col(t) + sB * (sm.col(t+1) - a);
sC.slice(t) = C.slice(t) + sB * (sC.slice(t+1) - R) * sB.t();
sC.slice(t) = (sC.slice(t) + sC.slice(t).t()) / 2;

W_t_1 = ex_df_mat % P;
arma::svd(U, s, V, W_t_1); 
W_inv = U * arma::diagmat(1/s) * U.t();
CBRB = sC.slice(t) - sB * sC.slice(t+1) * sB.t();

A = Eigen::Map<Eigen::MatrixXd>(W_t_1.memptr(), W_t_1.n_rows, W_t_1.n_cols);
log_det = logDetCholesky(A);
elbo -= 0.5 * log_det; 

A = Eigen::Map<Eigen::MatrixXd>(CBRB.memptr(), CBRB.n_rows, CBRB.n_cols); 
log_det = logDetCholesky(A);
elbo += 0.5 * log_det; 

arma::vec ee = sm.col(t+1) - GG.slice(t+1) * sm.col(t);
arma::mat XX = sC.slice(t+1) + GG.slice(t+1)*sC.slice(t)*GG.slice(t+1).t();
XX = XX - 2*( P*R_inv*sC.slice(t+1)) + ee * ee.t();

arma::mat xXX =  arma::solve(W_t_1, XX);
elbo -= 0.5 * arma::accu(xXX.diag());

a = GG.slice(t+1) * m.col(t);
CBRB = sC.slice(t) - sB * sC.slice(t+1) * sB.t();
arma::svd(U, s, V, CBRB);
CBRB_inv = U * arma::diagmat(1/s) * U.t();

xx = sm.col(t) - m.col(t) - sB * (sm.col(t+1) - a);
xxxx = CBRB_inv * (xx * xx.t());
elbo += 0.5 * arma::accu(xxxx.diag());

A = Eigen::Map<Eigen::MatrixXd>(CBRB.memptr(), CBRB.n_rows, CBRB.n_cols); 
log_det = logDetCholesky(A);
elbo += 0.5 * log_det; 
}

// Smoothing at time 0
P = GG.slice(0) * C0 * GG.slice(0).t();
R = P + ex_df_mat % P;  // Variance adjustment
R = (R + R.t()) / 2;  // Ensuring symmetry
R = regularize(R);
R_inv = robust_svd_inv(R);

sB = C0 * GG.slice(0).t() * R_inv;
arma::vec sm_0 = m0 + sB * (sm.col(0) - GG.slice(0) * m0);
arma::mat sC_0 = C0 + sB * (sC.slice(0) - R) * sB.t();
sC_0 = (sC_0 + sC_0.t()) / 2;

W_t_1 = ex_df_mat % P;
arma::svd(U, s, V, W_t_1);  // Reuse U, s, V for another SVD
W_inv = U * arma::diagmat(1/s) * U.t();

ee = sm.col(0) - GG.slice(0) * sm_0;
XX = sC.slice(0) + P - 2 * sB * sC.slice(0) + ee * ee.t();
XX = W_inv * XX;
elbo -= 0.5 * arma::accu(XX.diag());

arma::mat XXX = sC_0 + (sm_0 - m0) * (sm_0 - m0).t();
XXX = arma::solve(C0, XXX);
elbo -= 0.5 * arma::accu(XXX.diag());

a = GG.slice(0) * m0;
CBRB = sC_0 - sB * sC.slice(0) * sB.t();
arma::svd(U, s, V, CBRB);
CBRB_inv = U * arma::diagmat(1/s) * U.t();
xx = sm_0 - m0 - sB * (sm.col(0) - a);
xxxx = CBRB_inv * (xx * xx.t());
elbo += 0.5 * arma::accu(xxxx.diag());

A = Eigen::Map<Eigen::MatrixXd>(CBRB.memptr(), CBRB.n_rows, CBRB.n_cols); 
log_det = logDetCholesky(A);
elbo += 0.5 * log_det; 

return List::create(Named("standard_forecast_errors") = standard_forecast_errors,
Named("sm") = sm,
Named("sC") = sC,
Named("fm") = m, 
Named("fC") = C, 
Named("elbo.part") = elbo,
Named("elbo.part_ens") = elbo_ens,
Named("standard_forecast_errors_ens") = standard_forecast_errors_ens,
Named("sm_ens") = sm_ens,
Named("sC_ens") = sC_ens,
Named("fm_ens") = m_ens, 
Named("fC_ens") = C_ens, 
Named("W_T") = W_T);
}
