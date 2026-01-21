#include <RcppArmadillo.h>
using namespace Rcpp;

// Declare functions to be exposed to R
RcppExport SEXP _dexal(SEXP x, SEXP p0, SEXP mu, SEXP sigma, SEXP gamma, SEXP log_) {
    return Rcpp::wrap(dexal(Rcpp::as<double>(x), Rcpp::as<double>(p0), 
                            Rcpp::as<double>(mu), Rcpp::as<double>(sigma), 
                            Rcpp::as<double>(gamma), Rcpp::as<bool>(log_)));
}

RcppExport SEXP _pexal(SEXP q, SEXP p0, SEXP mu, SEXP sigma, SEXP gamma, SEXP lower_tail, SEXP log_p) {
    return Rcpp::wrap(pexal(Rcpp::as<double>(q), Rcpp::as<double>(p0), 
                            Rcpp::as<double>(mu), Rcpp::as<double>(sigma), 
                            Rcpp::as<double>(gamma), Rcpp::as<bool>(lower_tail), 
                            Rcpp::as<bool>(log_p)));
}

RcppExport SEXP _qexal(SEXP p, SEXP p0, SEXP mu, SEXP sigma, SEXP gamma, SEXP lower_tail, SEXP log_p) {
    return Rcpp::wrap(qexal(Rcpp::as<double>(p), Rcpp::as<double>(p0), 
                            Rcpp::as<double>(mu), Rcpp::as<double>(sigma), 
                            Rcpp::as<double>(gamma), Rcpp::as<bool>(lower_tail), 
                            Rcpp::as<bool>(log_p)));
}

RcppExport SEXP _rexal(SEXP n, SEXP p0, SEXP mu, SEXP sigma, SEXP gamma) {
    return Rcpp::wrap(rexal(Rcpp::as<int>(n), Rcpp::as<double>(p0), 
                            Rcpp::as<double>(mu), Rcpp::as<double>(sigma), 
                            Rcpp::as<double>(gamma)));
}
