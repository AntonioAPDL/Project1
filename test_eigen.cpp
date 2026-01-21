#include <RcppEigen.h>
#include <Eigen/Dense>
#include <Eigen/Cholesky>

// [[Rcpp::depends(RcppEigen)]]

using Eigen::MatrixXd;

// [[Rcpp::export]]
double logDetCholesky(const Eigen::MatrixXd& matrix) {
    // Base epsilon for regularization
    double epsilon = 1e-15;

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
