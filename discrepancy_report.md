# Discrepancy Report (Theory ↔ Implementation)

Scope: static (no execution) audit of consistency between:
- Theory: `/data/muscat_data/jaguir26/exDQLM---Ensemble/main.tex`
- Runner: `DISC_Optimal_Synth_Ranges_W.r`
- Used C++ units: `DISC_kalman_synth.cpp`, `sampling_exal.cpp`, `sampling_truncnorm.cpp`

Used-code inventory + entrypoints are in `audit_used_code.md`. Contract items and theory→code mapping are in
`theory_spec_checklist.md` and `mapping_table.md`.

---

## Executive Summary (PASS/FAIL)

| Block | Status | Notes |
|---|---:|---|
| Measurement mapping (Model B + forecast stacking) | PASS | Block-structured `FF` matches “baseline + discrepancy” observation structure; forecast assimilation stacks ensemble members consistently (T1, T3, T8). |
| Kalman predict/update | PASS | C++ implements standard covariance-form Kalman updates with additive offset/covariance for pseudo-data (T9). |
| RTS smoothing | PASS | C++ implements standard RTS recursions for historical and forecast segments (T10). |
| exAL augmentation (A/B/C mapping + augmented Gaussian form) | PASS | `g,p,A,B,C` mapping matches LaTeX; augmented Normal structure is used consistently via expectations (T4–T5). |
| Latent updates/sampling for \(v,s\) | PASS | Parameterizations match (T6–T7); D2 collision removed and samplers are now explicit + reproducible under `set.seed()` (see D2). |
| Priors for \((\sigma,\gamma)\) | PASS | Truncated-t for \(\gamma\) and inverse-gamma kernel for \(\sigma\) match LaTeX (T13). |
| Laplace–Delta \((\sigma,\gamma)\) transform | PASS | `update_gamma_sigma` now uses the LaTeX logistic mapping + Jacobian; numerical clipping is documented (see D1/D5). |
| Evolution covariance handling \(W\) | PASS (documented) | Historical discount-factor inflation + forecast-period plug-in update are now explicitly documented in `main.tex` (see D3/D4). |

---

## Discrepancy Table

| ID | Severity | Theory ref | Code ref | Mismatch | Likely effect | Minimal fix |
|---|---|---|---|---|---|---|
| D1 | RESOLVED (was HIGH) | `main.tex:eq:transform_u_xi`, `eq:jacobian_u_xi`, `eq:f_tilde_def` | `DISC_Optimal_Synth_Ranges_W.r:update_gamma_sigma` | **Fixed:** code now uses \(\gamma=L+(U-L)\pi(\xi)\) and adds the matching \(\log|J|\) term. | Removes theory↔implementation mismatch in the Laplace objective/curvature for \(q(\sigma,\gamma)\). | Implemented in code (see `discrepancy_resolution_notes.md`). |
| D2 | RESOLVED (was HIGH) | (sampler definition implicit in augmentation; `main.tex:eq:cond_s_V`, `eq:cond_s_m`) | `sampling_exal.cpp:sample_truncnorm_reject`; `sampling_truncnorm.cpp:sample_truncnorm_icdf`; `DISC_Optimal_Synth_Ranges_W.r` call sites | **Fixed:** exported-name collision removed; runner now calls `sample_truncnorm_icdf(...)` explicitly. Both samplers seed from R’s RNG for reproducibility under `set.seed()`. | Removes silent/fragile sampler switching; improves reproducibility and auditability. | Implemented in code + micro-test `repro/test_truncnorm_equivalence.R` (see `discrepancy_resolution_notes.md`). |
| D3 | RESOLVED (documented; was MEDIUM) | `main.tex:eq:kf_pred_cov` | `DISC_Optimal_Synth_Ranges_W.r:make_df_mat`; `DISC_kalman_synth.cpp` discount inflation | **Documented:** LaTeX now states the historical discount-factor specialization for \(\bm W_\tau\) used by the implementation. | Aligns theory text with implementation (no model-code change). | Implemented as a doc note in `main.tex` near the Kalman recursions. |
| D4 | RESOLVED (documented; was MEDIUM) | `main.tex:eq:C_IW` + `eq:vb_innov_second_moment` | `DISC_Optimal_Synth_Ranges_W.r` forecast “UPDATE W” loop | **Documented:** LaTeX now states the forecast-period shrinkage plug-in update \(\widehat{\bm W}_\tau\) used in code (with mapping to `epsilon`, `c_factor`, and `ww`). | Aligns theory text with implementation (no model-code change). | Implemented as a doc note + equation `main.tex:eq:forecast_W_plugin`. |
| D5 | RESOLVED (documented) | `main.tex:eq:transform_u_xi` | `DISC_Optimal_Synth_Ranges_W.r:update_gamma_sigma` | **Updated:** removed coarse \((L,U)\) tightening (`LL/UU`). Implementation now clips \(\pi(\xi)\) slightly away from \(\{0,1\}\) to avoid evaluating \(A,B,C\) at boundary values where they diverge. | Avoids numerical blow-ups while preserving the intended open interval \(\gamma\in(L,U)\). | Documented in `main.tex` as a numerical note near the transform. |

---

## Confirmed Matches (Selected)

- **exAL mapping functions** \(g(\gamma)\), \(p(p_0,\gamma)\), \(A(p)\), \(B(p)\), \(C(p,\gamma)\) match exactly between LaTeX and code (`main.tex:175–181`; `DISC_Optimal_Synth_Ranges_W.r:114–120`).
- **\(q(v)\) / GIG parameterization** matches: `update_uts` forms \(\lambda=1/2\), \(\psi\), \(\chi\) consistent with `main.tex:eq:cond_v` and `main.tex:eq:vb_qv`/`eq:vb_chi`; sampling uses `(lambda, psi, chi)` in `sample_gig_devroye_vector`.
- **\(q(s)\) / truncated Normal parameterization** matches: `update_sts` computes \((\mu,\sigma^2)\) consistent with `main.tex:eq:cond_s_V`/`eq:cond_s_m` and `main.tex:eq:vb_kappa_rho`; `sampling_truncnorm.cpp` samples lower-truncated at 0 with variance input.
- **VB pseudo-data assimilation** matches via offset/covariance: `main.tex:eq:vb_info_wb` + `eq:vb_pseudodata_scalar` ↔ `DISC_Optimal_Synth_Ranges_W.r:1640–1646` + `DISC_kalman_synth.cpp:861–905`.
- **Kalman + RTS equations** match the generic recursions (`main.tex:eq:kf_*`, `eq:rts_*`) as implemented in `DISC_kalman_synth.cpp:851–905` and `DISC_kalman_synth.cpp:1277–1321` (historical), with analogous structure for forecast blocks.
