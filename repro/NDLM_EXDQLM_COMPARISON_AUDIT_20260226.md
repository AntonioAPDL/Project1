# NDLM vs Multivariate exDQLM: Rigorous Comparison Audit (2026-02-26)

## Scope and parity contract
Target parity statement:
- NDLM and multivariate exDQLM should be identical except for likelihood-family consequences.
- Allowed core difference:
  - NDLM uses Gaussian likelihood with source-specific scale.
  - Multivariate exDQLM uses exAL likelihood with source/quantile-specific scale + skewness and latent augmentation.

Audit status:
- Theory-level parity is mostly strong in state-space structure.
- Implementation-level parity is not yet achieved.
- The largest non-likelihood drift is in NDLM state assimilation and objective construction.

---

## Comparison 1 (Priority): Theory vs Theory
### 1A) Core model structure checklist

| ID | Checklist item | Evidence | Expected from likelihood? | Status |
|---|---|---|---|---|
| C1-01 | Model A state transitions \(\theta,\zeta,\psi\) are structurally aligned | `NDLM---Ensemble/.../01_notation_and_model.tex:27-33`, `exDQLM---Ensemble/main.tex:65-70` | No | Match |
| C1-02 | Model B discrepancy-state construction is aligned | `01_notation_and_model.tex:52-56`, `main.tex:107-110` | No | Match |
| C1-03 | Model C forecast-state construction is aligned (state-transition side) | `01_notation_and_model.tex:67-71`, `main.tex:139-143` | No | Match |
| C1-04 | Observation family differs (Gaussian vs exAL) | `01_notation_and_model.tex:25-26,52-53,67-68`, `main.tex:63-64,107-108,139-140` | Yes | Expected difference |
| C1-05 | exDQLM includes latent augmentation \((v,s)\) | `main.tex:147-173,243-258` | Yes | Expected difference |
| C1-06 | NDLM has conjugate IG sigma in VB | `06_vb_cavi.tex:29-36` | Yes | Expected difference |
| C1-07 | exDQLM has nonconjugate joint \(q(\sigma,\gamma)\) with Laplace-Delta | `main.tex:655-683,953-1131` | Yes | Expected difference |

### 1B) Theory-level non-likelihood discrepancies

| ID | Discrepancy | Evidence | Why non-likelihood |
|---|---|---|---|
| C1-N01 | NDLM derivation includes explicit variational update \(q(\lambda)\); exDQLM derivation does not include a matching \(q(\lambda)\) block | `06_vb_cavi.tex:51-65` vs exDQLM factorization `main.tex:576-583` | Transfer coefficient treatment is an inference-spec choice, not a likelihood necessity |
| C1-N02 | NDLM doc is fully conjugate for \(W\) blocks; exDQLM doc explicitly embeds implementation notes with discount and forecast plug-in alternatives | NDLM `04_static_conditionals.tex:17-25`, exDQLM `main.tex:816-827,926-941` | \(W_t\) update policy is algorithmic design, not likelihood-required |

### 1C) Conclusion for Comparison 1
- Strong structural parity in state equations.
- Expected divergence in observation blocks and latent augmentation.
- At least two non-likelihood theory differences exist: \(\lambda\) treatment and \(W_t\) update policy.

### 1D) Step-by-step execution log (2026-02-25 PST)
Step 1 (reproducible validator pass):
- Ran `parity_with_exdqlm.py` and `validate_all.py` against:
  - NDLM derivations: `/data/muscat_data/jaguir26/NDLM---Ensemble/docs/derivations/sections`
  - exDQLM reference: `/data/muscat_data/jaguir26/exDQLM---Ensemble/main.tex`
- Artifacts written to: `repro/audit_artifacts/cmp1_theory_theory_20260225_2242/`
  - `parity_with_exdqlm.json`, `parity_with_exdqlm.md`
  - `validate_all.json`, `validate_all.md`
  - `parity_validateall.json`, `parity_validateall.md`
- Results:
  - Parity status: `PASS`
  - Shared equation labels matched: `eq:A_theta`, `eq:A_zeta`, `eq:A_psi`, `eq:B_delta`
  - Expected likelihood-only differences confirmed: `eq:A_obs`, `eq:B_obs`, `eq:C_obs`
  - Validation summary: `7/7` checks passed (`all_passed = TRUE`)
  - Passed checks: `gaussian_likelihood_normalization`, `joint_marginal_gaussian_consistency`, `observation_variance_ig_conjugacy`, `evolution_covariance_iw_conjugacy`, `lambda_gradient_hessian`, `kalman_ffbs_vs_bruteforce`, `replicate_sufficient_statistic_assimilation`

Step 2 (manual non-likelihood discrepancy reconfirmation):
- `q(\lambda)` discrepancy reconfirmed:
  - NDLM includes explicit factor and moments: `NDLM---Ensemble/docs/derivations/sections/06_vb_cavi.tex:51-65`
  - exDQLM mean-field factorization does not include matching `q(\lambda)` block: `exDQLM---Ensemble/main.tex:576-583`
- \(W_t\) policy discrepancy reconfirmed:
  - NDLM presents conjugate IW block: `NDLM---Ensemble/docs/derivations/sections/04_static_conditionals.tex:17-25`
  - exDQLM includes explicit implementation alternatives (discounted historical \(W_t\), forecast plug-in \(W_t\)): `exDQLM---Ensemble/main.tex:816-827,926-941`

---

## Comparison 2: NDLM Theory vs NDLM Implementation (this repo)
### 2A) Checklist and findings

| ID | Checklist item | Evidence | Expected from likelihood? | Status |
|---|---|---|---|---|
| C2-01 | Source-specific sigmas are represented (USGS/NWS/GloFAS) | `03_vb_updates.R:413-422,431-438,529-559` | No | Match |
| C2-02 | State update uses all source observations through source-specific precisions | Theory `06_vb_cavi.tex:24-27,69-73`; code builds precision-weighted pseudo-observation from all sources `03_vb_updates.R:293-367`, then runs Kalman with that stream `03_vb_updates.R:511-515` | No | Match (collapsed pseudo-observation form) |
| C2-03 | Kalman observation input reflects multi-source pseudo-observations | Theory `08_computational_notes.tex:4-7`; code uses `hist_assim$y, hist_assim$R_vec` in Kalman call `03_vb_updates.R:511-515` | No | Match (with shared-loading collapse) |
| C2-04 | Variational \(q(\lambda)\) update exists | Theory `06_vb_cavi.tex:51-65`; code keeps fixed lambda from env/constants `00_constants.R:44,70`, logged in `03_vb_updates.R:575-577,614` | No | **Mismatch** |
| C2-05 | Full ELBO block decomposition exists | Theory `07_elbo.tex:12-23,56-100`; code ELBO trace remains source ll + sigma prior surrogate `03_vb_updates.R:549-559,563`, `04_elbo.R:1-5` | No | **Mismatch** |
| C2-06 | Forecast update is Gaussian state update over forecast observations | Theory `01_notation_and_model.tex:67-71`; code forecast means built by standardized source vectors + bridge + decay and covariance recursion `03_vb_updates.R:685-732` | No | **Mismatch (critical)** |
| C2-07 | Ragged-horizon bookkeeping exists | `03_vb_updates.R:32-61,792-803` | No | Match |
| C2-08 | Scale trace columns include constant model hyperparameters | `03_vb_updates.R:463-479,564-579` and diagnostics plotting of all scale columns `ndlm_post_diagnostics.R:341-357,373-401` | No | Designed behavior (not convergence signal) |
| C2-09 | `sigma_exp` duplicates USGS sigma in scale trace | `03_vb_updates.R:564-567,597-604` | No | Drift / naming ambiguity |

### 2B) Practical implication
- Historical multi-source assimilation gap is now closed in current NDLM (`hist_assim` precision-weighted collapse).
- Major theory-to-implementation gaps remain in forecast-state updating and ELBO decomposition.
- These remaining gaps are still large enough to drive instability or counterintuitive diagnostics.

### 2C) Added Kalman C++ comparisons (legacy NDLM + multiv exDQLM)
| ID | Comparison item | Evidence | Status |
|---|---|---|---|
| C2-L01 | Legacy NDLM Kalman C++ uses multivariate \((J+1)\)-output updates directly; current NDLM collapses sources to one pseudo-observation per time | Legacy NDLM C++ signature and historical update: `kalman_synth_NDLM.cpp:141-150,205-223,242-260` (also `DISC_kalman_synth_NDLM.cpp:254,329,366`); current NDLM scalar Kalman contract: `02_model_spec.R:50-57,99-104`, with collapse done in `03_vb_updates.R:293-367` | Partial parity (equivalent only under shared-loading assumption) |
| C2-L02 | Legacy NDLM Kalman C++ performs forecast filtering/smoothing over ensemble observations; current NDLM does deterministic bridge/decay + covariance recursion instead | Legacy NDLM forecast/filter-smoother blocks: `kalman_synth_NDLM.cpp:271-365,370-553,562-613`; current NDLM forecast construction: `03_vb_updates.R:685-732` | **Mismatch (critical)** |
| C2-L03 | \(W_t\) policy check versus your stated legacy design | Legacy NDLM C++ historical/forecast uses discount-style \(R=P+P\odot\text{df}\): `kalman_synth_NDLM.cpp:205,242,280,288`; current NDLM historical also uses discount-style \(W_t = \text{DF}\odot P_t\): `02_model_spec.R:92-95`; forecast covariance uses discount recursion: `03_vb_updates.R:718-732` | Match on “discount, not IW in forecast Kalman” |
| C2-L04 | Legacy NDLM C++ carries transition ELBO terms inside Kalman smoother; current NDLM does not | Legacy NDLM C++ ELBO terms and returns: `kalman_synth_NDLM.cpp:621-698,703-705`; current NDLM ELBO surrogate only: `03_vb_updates.R:549-559,563`, `04_elbo.R:1-5` | **Mismatch (major)** |
| C2-L05 | Multivariate exDQLM C++ path (the one actually used) is closer to legacy trans-dimensional Kalman architecture than current NDLM | exDQLM script compiles and calls `DISC_update_theta_synth_cpp_W`: `DISC_Optimal_Synth_Ranges_W.r:61,2094-2102`; C++ uses multi-output y and forecast \(R=P+W_t\): `DISC_kalman_synth.cpp:855-865,1065,1127,1541` | Explains NDLM vs exDQLM behavior gap beyond likelihood alone |
| C2-L06 | Legacy NDLM file-path clarification | Older NDLM script uses `kalman_synth_NDLM.cpp`: `Optimal_Synth_Ranges_NDLM.r:60,1661`; DISC legacy NDLM script uses `DISC_kalman_synth_NDLM.cpp`: `DISC_Optimal_Synth_Ranges_NDLM.r:115,1696` | Reproducibility-critical note |

---

## Comparison 3: Multivariate exDQLM Theory vs Implementation (this repo)
### 3A) Checklist and findings

| ID | Checklist item | Evidence | Expected from likelihood? | Status |
|---|---|---|---|---|
| C3-01 | exAL latent-variable blocks \(s,u\) are implemented | `DISC_Optimal_Synth_Ranges_W.r:1226-1272` | Yes | Match |
| C3-02 | Joint \((\sigma,\gamma)\) nonconjugate update with transforms/guard appears | `DISC_Optimal_Synth_Ranges_W.r:1287-1660` | Yes | Match |
| C3-03 | Pseudo-observation construction \(FFF/QQQ\) for Gaussian state update exists | `DISC_Optimal_Synth_Ranges_W.r:2003-2033` | Yes | Match |
| C3-04 | ELBO includes broad additive components for augmented model | `DISC_Optimal_Synth_Ranges_W.r:2453-2509` and theory decomposition `main.tex:1228-1501` | Yes | Broadly aligned |
| C3-05 | Discount-based historical \(W\) and forecast plug-in \(W\) are documented deviations | Theory notes `main.tex:816-827,926-941`; code `DISC_Optimal_Synth_Ranges_W.r:2192-2217` | No | Aligned with documented implementation note |
| C3-06 | Hardcoded warm-start file paths tied to local absolute paths | `DISC_Optimal_Synth_Ranges_W.r:1867-1933` | No | Non-likelihood engineering risk |

---

## Comparison 4 (Priority): Implementation vs Implementation
### 4A) "Only likelihood should differ" checklist

| ID | Checklist item | NDLM implementation | exDQLM implementation | Explainable only by likelihood? | Status |
|---|---|---|---|---|---|
| C4-01 | Architecture parity | Modular family (`R/unified/families/ndlm_main`) | Legacy monolith via wrapper (`scripts/run_DISC_Optimal_Synth_Ranges_W.R:3`) | No | **Mismatch** |
| C4-02 | State assimilation uses all available observation channels | Uses precision-weighted collapsed pseudo-observation from USGS/NWS/GloFAS in Kalman step `03_vb_updates.R:293-367,511-515` | Uses pseudo-observation blocks from all channels `DISC_...r:2003-2103` | No | Partial mismatch (collapsed vs full multivariate) |
| C4-03 | Forecast-state update mechanism parity | Deterministic bridge/decay construction `03_vb_updates.R:592-623` | Forecast pseudo-observation + covariance updates `DISC_...r:2016-2050,2192-2217` | No | **Mismatch** |
| C4-04 | Convergence policy parity | ELBO abs/rel only `03_vb_updates.R:491-540` | ELBO + state norm + sigma + gamma + min update/iter guards `DISC_...r:2520-2573` | No | **Mismatch** |
| C4-05 | ELBO granularity parity | Reduced surrogate `03_vb_updates.R:460-474`, `04_elbo.R:1-5` | Rich blockwise augmented ELBO `DISC_...r:2453-2509` | No | **Mismatch** |
| C4-06 | Quantile handling parity | Fixed `p0 = 0.5` `00_constants.R:73`; single output filename `stage_fit.R:749` | Per-quantile runs `stage_fit.R:285-391` | No | **Mismatch** |
| C4-07 | Sigma structure per source | 3 source sigmas tracked `03_vb_updates.R:337-346,443-469` | Source-specific sigma per model/quantile `DISC_...r:2353-2418` | Partly | Partial match |

### 4B) Main conclusion for Comparison 4
Non-likelihood implementation differences are substantial and likely enough to explain why multivariate exDQLM behaves well while NDLM does not.

### 4C) Step-by-step verification log (2026-02-25 PST)
Note: C4-S2 reflects the pre-fix snapshot before `hist_assim` was introduced; current historical assimilation status is superseded by Comparison 2 (C2-02/C2-03).
| Step | Check | Evidence | Result |
|---|---|---|---|
| C4-S1 | Architecture parity | NDLM uses modular theory runner path in `R/unified/stages/stage_fit.R:720-723`; multivariate exDQLM run path still calls wrapper `scripts/run_DISC_Optimal_Synth_Ranges_W.R` from `R/unified/stages/stage_fit.R:376`, which sources legacy monolith at `scripts/run_DISC_Optimal_Synth_Ranges_W.R:44` | Confirmed mismatch |
| C4-S2 | Historical state assimilation parity | NDLM Kalman smoother call uses `y = inputs$y` with `R_vec` built from USGS sigma only: `R/unified/families/ndlm_main/03_vb_updates.R:420-423`; multivariate exDQLM builds source-wise pseudo-observations and variances (`FFF`, `QQQ`): `DISC_Optimal_Synth_Ranges_W.r:2003-2004,2019-2023` | Confirmed mismatch (critical) |
| C4-S3 | Forecast-state update parity | NDLM forecast state mean is deterministic bridge/decay construction: `R/unified/families/ndlm_main/03_vb_updates.R:595-623`; multivariate exDQLM performs forecast covariance/state updates with iterative \(W\) update: `DISC_Optimal_Synth_Ranges_W.r:2192-2217` | Confirmed mismatch |
| C4-S4 | Convergence policy parity | NDLM convergence gate is ELBO absolute+relative only: `R/unified/families/ndlm_main/03_vb_updates.R:293-307,529-536`; multivariate exDQLM requires ELBO + state + sigma + gamma + min-update/min-iter criteria: `DISC_Optimal_Synth_Ranges_W.r:2566-2572` | Confirmed mismatch |
| C4-S5 | ELBO granularity parity | NDLM objective is reduced source likelihood + sigma prior surrogate: `R/unified/families/ndlm_main/03_vb_updates.R:460-474` and `R/unified/families/ndlm_main/04_elbo.R:1-5`; multivariate exDQLM ELBO includes broad augmented terms: `DISC_Optimal_Synth_Ranges_W.r:2455-2502` | Confirmed mismatch |
| C4-S6 | Quantile handling parity | NDLM constants fix `p0 = 0.5`: `R/unified/families/ndlm_main/00_constants.R:73`, and NDLM output path is fixed at `DISC_variables_50...`: `R/unified/stages/stage_fit.R:749`; multivariate exDQLM runs per-quantile loop: `R/unified/stages/stage_fit.R:285-391` | Confirmed mismatch |
| C4-S7 | Sigma structure parity | NDLM tracks source-specific sigmas (`usgs`, `nws`, `glofas`): `R/unified/families/ndlm_main/03_vb_updates.R:337-346,443-469`; multivariate exDQLM updates source-wise sigma/gamma under each quantile run: `DISC_Optimal_Synth_Ranges_W.r:2302-2314,2406-2418` with quantile argument from wrapper `scripts/run_DISC_Optimal_Synth_Ranges_W.R:10` | Partial match (structure differs as expected by likelihood) |

---

## Rigorous action checklist (execution order)
1. Unify state assimilation contract:
   - NDLM must build multi-source observation list (USGS/NWS/GloFAS) for historical fit and use source-specific \(E[1/\sigma_j^2]\) in Kalman updates.
   - Acceptance: NDLM state-update code path includes all sources and passes contract tests with per-source ablation checks.
2. Align ELBO instrumentation:
   - Implement blockwise ELBO terms in NDLM (at minimum: likelihood, transition, priors, state entropy, sigma entropy).
   - Acceptance: ELBO block CSV and monotonicity diagnostics comparable to exDQLM logs.
3. Decide \(\lambda\) policy explicitly:
   - Either implement \(q(\lambda)\) in NDLM code or fix \(\lambda\) in both derivation and implementation docs.
   - Acceptance: no ambiguity between derivation and code for \(\lambda\).
4. Normalize convergence criteria across models:
   - Add state/sigma (and if present gamma) convergence guards to NDLM or intentionally simplify both with rationale.
   - Acceptance: documented, shared stop policy schema in `stage_fit.R`.
5. Clean scale traces semantics:
   - Separate dynamic parameter traces from static hyperparameter traces.
   - Acceptance: sigma plots contain sigma-only series unless user explicitly requests hyperparameter traces.
6. Remove brittle warm-start dependencies in multivariate exDQLM:
   - Replace hardcoded absolute RData paths with configurable run-relative paths.
   - Acceptance: warm start works in arbitrary run roots without path edits.

---

## Bottom line
- The likelihood difference alone does not explain current NDLM vs multivariate exDQLM behavior.
- The dominant non-likelihood divergence is NDLM’s current state-update/ELBO implementation gap relative to both theory and exDQLM implementation patterns.
