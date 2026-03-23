// [[Rcpp::plugins(cpp11)]]
// [[Rcpp::depends(RcppArmadillo)]]

#include <RcppArmadillo.h>

using namespace Rcpp;
using namespace arma;

namespace {

struct StabilizationStats {
  int calls = 0;
  int cov_projected = 0;
  int cov_floor_clipped = 0;
  int cov_cap_clipped = 0;
  int cov_nonfinite_inputs = 0;
};

inline arma::mat symmetrize(const arma::mat& x) {
  return 0.5 * (x + x.t());
}

inline arma::mat regularize(const arma::mat& x, double eps = 1e-10) {
  return x + eps * arma::eye<arma::mat>(x.n_rows, x.n_cols);
}

inline arma::mat stabilize_covariance(
    const arma::mat& x,
    const double eig_floor,
    const double eig_cap,
    const double diag_jitter,
    StabilizationStats* stats) {
  if (stats != nullptr) {
    stats->calls += 1;
  }

  arma::mat sx = symmetrize(x);
  if (!sx.is_finite()) {
    sx.transform([](double v) { return std::isfinite(v) ? v : 0.0; });
    if (stats != nullptr) {
      stats->cov_nonfinite_inputs += 1;
    }
  }
  if (sx.n_rows != sx.n_cols || sx.n_rows == 0) {
    return arma::eye<arma::mat>(sx.n_rows, sx.n_cols) * eig_floor;
  }

  arma::vec eig_vals;
  bool eig_ok = arma::eig_sym(eig_vals, sx);
  bool needs_projection = !eig_ok || !eig_vals.is_finite();
  bool floor_hit = needs_projection;
  bool cap_hit = needs_projection;
  if (eig_ok && eig_vals.is_finite()) {
    double min_eval = eig_vals.min();
    double max_eval = eig_vals.max();
    floor_hit = (!std::isfinite(min_eval) || min_eval < eig_floor);
    cap_hit = (!std::isfinite(max_eval) || max_eval > eig_cap);
    needs_projection = floor_hit || cap_hit;
  }

  arma::mat out = sx;
  if (needs_projection) {
    if (stats != nullptr) {
      stats->cov_projected += 1;
      if (floor_hit) stats->cov_floor_clipped += 1;
      if (cap_hit) stats->cov_cap_clipped += 1;
    }
    arma::vec vals;
    arma::mat vecs;
    if (arma::eig_sym(vals, vecs, sx) && vals.is_finite() && vecs.is_finite()) {
      vals.transform([eig_floor, eig_cap](double v) {
        if (!std::isfinite(v)) return eig_floor;
        if (v < eig_floor) return eig_floor;
        if (v > eig_cap) return eig_cap;
        return v;
      });
      out = vecs * arma::diagmat(vals) * vecs.t();
    } else {
      out = arma::eye<arma::mat>(sx.n_rows, sx.n_cols) * eig_floor;
    }
  }

  arma::mat stabilized = regularize(symmetrize(out), diag_jitter);
  for (int iter = 0; iter < 3; ++iter) {
    arma::vec post_vals;
    bool post_ok = arma::eig_sym(post_vals, stabilized);
    double post_min = (post_ok && post_vals.is_finite()) ? post_vals.min() : arma::datum::nan;
    if (std::isfinite(post_min) && post_min >= eig_floor) {
      break;
    }
    double shift = eig_floor;
    if (std::isfinite(post_min)) {
      shift = eig_floor - post_min;
    }
    if (!std::isfinite(shift) || shift < 0.0) {
      shift = eig_floor;
    }
    stabilized += (shift + std::max(diag_jitter, 0.0)) * arma::eye<arma::mat>(stabilized.n_rows, stabilized.n_cols);
    if (stats != nullptr) {
      if (stats->cov_projected == 0) stats->cov_projected += 1;
      if (stats->cov_floor_clipped == 0) stats->cov_floor_clipped += 1;
    }
  }
  return stabilized;
}

inline arma::mat robust_svd_inv(const arma::mat& x, double tolerance = 1e-12) {
  arma::mat U, V;
  arma::vec s;
  if (!arma::svd(U, s, V, x)) {
    Rcpp::stop("ndlm_kalman_smoother_cpp: SVD failed during robust inverse");
  }
  arma::vec s_inv = s;
  for (arma::uword i = 0; i < s.n_elem; ++i) {
    double si = std::abs(s[i]);
    if (!std::isfinite(si) || si < tolerance) si = tolerance;
    s_inv[i] = 1.0 / si;
  }
  return V * arma::diagmat(s_inv) * U.t();
}

inline arma::mat safe_inv_with_svd(const arma::mat& x, double diag_jitter = 1e-10) {
  arma::mat sx = symmetrize(x);
  arma::mat inv_try;
  // Keep fast SPD path first, but always degrade to robust SVD inversion.
  bool ok = arma::inv_sympd(inv_try, sx);
  if (ok && inv_try.is_finite()) return inv_try;
  arma::mat reg = regularize(sx, std::max(1e-8, diag_jitter));
  ok = arma::inv_sympd(inv_try, reg);
  if (ok && inv_try.is_finite()) return inv_try;
  arma::mat inv_svd = robust_svd_inv(reg);
  if (!inv_svd.is_finite()) {
    Rcpp::stop("ndlm_kalman_smoother_cpp: robust SVD inverse produced non-finite result");
  }
  return inv_svd;
}

} // namespace

// [[Rcpp::export]]
Rcpp::List ndlm_kalman_smoother_cpp(
    const arma::vec& y,
    const arma::mat& H_mat,
    const arma::vec& R_vec_in,
    const arma::vec& q_diag_in,
    const Rcpp::Nullable<Rcpp::NumericMatrix>& df_mat_in,
    const arma::vec& m0,
    const arma::mat& C0,
    const double cov_eig_floor = 1e-8,
    const double cov_eig_cap = 1e8,
    const double cov_diag_jitter = 1e-10) {
  const int Tn = static_cast<int>(y.n_elem);
  if (Tn <= 0) {
    Rcpp::stop("ndlm_kalman_smoother_cpp requires non-empty y");
  }
  if (H_mat.n_rows != static_cast<arma::uword>(Tn)) {
    Rcpp::stop("ndlm_kalman_smoother_cpp: H_mat row count must match y length");
  }
  const int d = static_cast<int>(H_mat.n_cols);
  if (d <= 0) {
    Rcpp::stop("ndlm_kalman_smoother_cpp requires H_mat with at least one column");
  }
  if (m0.n_elem != static_cast<arma::uword>(d)) {
    Rcpp::stop("ndlm_kalman_smoother_cpp: m0 length must equal ncol(H_mat)");
  }
  if (C0.n_rows != static_cast<arma::uword>(d) || C0.n_cols != static_cast<arma::uword>(d)) {
    Rcpp::stop("ndlm_kalman_smoother_cpp: C0 shape must be d x d");
  }
  if (q_diag_in.n_elem != static_cast<arma::uword>(d)) {
    Rcpp::stop("ndlm_kalman_smoother_cpp: q_diag length must equal ncol(H_mat)");
  }
  if (R_vec_in.n_elem != static_cast<arma::uword>(Tn)) {
    Rcpp::stop("ndlm_kalman_smoother_cpp: R_vec length must equal y length");
  }

  arma::vec R_vec = R_vec_in;
  for (int i = 0; i < Tn; ++i) {
    if (!std::isfinite(R_vec[i]) || R_vec[i] < 1e-10) R_vec[i] = 1e-10;
  }

  arma::vec q_diag = q_diag_in;
  for (int i = 0; i < d; ++i) {
    if (!std::isfinite(q_diag[i]) || q_diag[i] < 1e-10) q_diag[i] = 1e-10;
  }
  arma::mat Q = arma::diagmat(q_diag);
  bool use_discount = false;
  arma::mat DF;
  if (df_mat_in.isNotNull()) {
    DF = Rcpp::as<arma::mat>(df_mat_in);
    if (DF.n_rows != static_cast<arma::uword>(d) || DF.n_cols != static_cast<arma::uword>(d)) {
      Rcpp::stop("ndlm_kalman_smoother_cpp: df_mat must be d x d when provided");
    }
    if (!DF.is_finite()) {
      Rcpp::stop("ndlm_kalman_smoother_cpp: df_mat must be finite");
    }
    DF = symmetrize(DF);
    DF.transform([](double v) { return (v < 0.0) ? 0.0 : v; });
    use_discount = true;
  }

  arma::mat a(d, Tn, arma::fill::zeros);
  arma::mat m(d, Tn, arma::fill::zeros);
  arma::cube Rpred(d, d, Tn, arma::fill::zeros);
  arma::cube C(d, d, Tn, arma::fill::zeros);
  arma::vec pred_mean(Tn, arma::fill::zeros);
  arma::vec pred_var(Tn, arma::fill::zeros);
  arma::vec filt_mean(Tn, arma::fill::zeros);
  arma::vec filt_var(Tn, arma::fill::zeros);

  arma::vec m_prev = m0;
  StabilizationStats stab_stats;
  arma::mat C_prev = stabilize_covariance(
    C0,
    cov_eig_floor,
    cov_eig_cap,
    cov_diag_jitter,
    &stab_stats
  );

  for (int t = 0; t < Tn; ++t) {
    arma::vec H_t = H_mat.row(static_cast<arma::uword>(t)).t();
    arma::vec a_t = m_prev;
    arma::mat P_t = stabilize_covariance(
      C_prev,
      cov_eig_floor,
      cov_eig_cap,
      cov_diag_jitter,
      &stab_stats
    );
    arma::mat R_t;
    if (use_discount) {
      arma::mat W_t = DF % P_t;
      R_t = stabilize_covariance(
        P_t + W_t + Q,
        cov_eig_floor,
        cov_eig_cap,
        cov_diag_jitter,
        &stab_stats
      );
    } else {
      R_t = stabilize_covariance(
        C_prev + Q,
        cov_eig_floor,
        cov_eig_cap,
        cov_diag_jitter,
        &stab_stats
      );
    }

    double Qy = arma::as_scalar(H_t.t() * R_t * H_t) + R_vec[static_cast<arma::uword>(t)];
    if (!std::isfinite(Qy) || Qy < 1e-10) Qy = 1e-10;

    arma::vec K = (R_t * H_t) / Qy;
    double innov = y[static_cast<arma::uword>(t)] - arma::as_scalar(H_t.t() * a_t);
    arma::vec m_t = a_t + K * innov;
    arma::mat C_t = stabilize_covariance(
      R_t - (R_t * (H_t * H_t.t()) * R_t) / Qy,
      cov_eig_floor,
      cov_eig_cap,
      cov_diag_jitter,
      &stab_stats
    );
    pred_mean[static_cast<arma::uword>(t)] = arma::dot(H_t, a_t);
    double pv = arma::as_scalar(H_t.t() * R_t * H_t) + R_vec[static_cast<arma::uword>(t)];
    if (!std::isfinite(pv) || pv < 1e-10) pv = 1e-10;
    pred_var[static_cast<arma::uword>(t)] = pv;
    filt_mean[static_cast<arma::uword>(t)] = arma::dot(H_t, m_t);
    double fv_f = arma::as_scalar(H_t.t() * C_t * H_t) + R_vec[static_cast<arma::uword>(t)];
    if (!std::isfinite(fv_f) || fv_f < 1e-10) fv_f = 1e-10;
    filt_var[static_cast<arma::uword>(t)] = fv_f;

    a.col(static_cast<arma::uword>(t)) = a_t;
    m.col(static_cast<arma::uword>(t)) = m_t;
    Rpred.slice(static_cast<arma::uword>(t)) = R_t;
    C.slice(static_cast<arma::uword>(t)) = C_t;

    m_prev = m_t;
    C_prev = C_t;
  }

  arma::mat ms = m;
  arma::cube Cs = C;
  if (Tn >= 2) {
    for (int t = Tn - 2; t >= 0; --t) {
      arma::mat R_next = stabilize_covariance(
        Rpred.slice(static_cast<arma::uword>(t + 1)),
        cov_eig_floor,
        cov_eig_cap,
        cov_diag_jitter,
        &stab_stats
      );
      arma::mat R_next_inv = safe_inv_with_svd(R_next, cov_diag_jitter);
      arma::mat J_t = C.slice(static_cast<arma::uword>(t)) * R_next_inv;
      ms.col(static_cast<arma::uword>(t)) =
        m.col(static_cast<arma::uword>(t)) +
        J_t * (ms.col(static_cast<arma::uword>(t + 1)) - a.col(static_cast<arma::uword>(t + 1)));
      arma::mat Cs_t = C.slice(static_cast<arma::uword>(t)) +
        J_t * (Cs.slice(static_cast<arma::uword>(t + 1)) - R_next) * J_t.t();
      Cs.slice(static_cast<arma::uword>(t)) = stabilize_covariance(
        Cs_t,
        cov_eig_floor,
        cov_eig_cap,
        cov_diag_jitter,
        &stab_stats
      );
    }
  }

  arma::vec smooth_mean(Tn, arma::fill::zeros);
  arma::vec smooth_var(Tn, arma::fill::zeros);
  for (int t = 0; t < Tn; ++t) {
    arma::vec H_t = H_mat.row(static_cast<arma::uword>(t)).t();
    smooth_mean[static_cast<arma::uword>(t)] = arma::dot(H_t, ms.col(static_cast<arma::uword>(t)));
    double fv = arma::as_scalar(H_t.t() * Cs.slice(static_cast<arma::uword>(t)) * H_t) + R_vec[static_cast<arma::uword>(t)];
    if (!std::isfinite(fv) || fv < 1e-10) fv = 1e-10;
    smooth_var[static_cast<arma::uword>(t)] = fv;
  }

  return Rcpp::List::create(
    Rcpp::Named("smooth_mean") = ms,
    Rcpp::Named("smooth_cov") = Cs,
    Rcpp::Named("predicted_mean") = pred_mean,
    Rcpp::Named("predicted_var") = pred_var,
    Rcpp::Named("filtered_mean") = filt_mean,
    Rcpp::Named("filtered_var") = filt_var,
    Rcpp::Named("smoothed_mean") = smooth_mean,
    Rcpp::Named("smoothed_var") = smooth_var,
    Rcpp::Named("fitted_mean") = smooth_mean,
    Rcpp::Named("fitted_var") = smooth_var,
    Rcpp::Named("stabilization") = Rcpp::List::create(
      Rcpp::Named("calls") = stab_stats.calls,
      Rcpp::Named("cov_projected") = stab_stats.cov_projected,
      Rcpp::Named("cov_floor_clipped") = stab_stats.cov_floor_clipped,
      Rcpp::Named("cov_cap_clipped") = stab_stats.cov_cap_clipped,
      Rcpp::Named("cov_nonfinite_inputs") = stab_stats.cov_nonfinite_inputs
    )
  );
}
