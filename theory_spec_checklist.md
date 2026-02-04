# Theory Spec Checklist (Implementation Contract)

Scope: this checklist extracts the **minimum load-bearing theory “contract items”** from the LaTeX document
`/data/muscat_data/jaguir26/exDQLM---Ensemble/main.tex` that are relevant to the **actually-used code path**
identified in `audit_used_code.md`.

Conventions:
- Time indexing: LaTeX uses `t=1..T` (historical) and `t=T+1..T+K` (forecast). C++ uses 0-based indices.
- Observation stacking: LaTeX uses `(\\tau,o)` for “time \\tau, observation o”. Code uses vector/matrix stacking.

---

## Contract Items

### T1 — Model B retrospective observation equation (baseline + discrepancy products)
- **LaTeX reference:** `main.tex:60–110` (`eq:A_obs`, `eq:B_obs`)
- **Statement (per time `t=1..T`):**
  - Baseline:  \(y_t^o \mid \alpha_t,\sigma^o,\gamma^o \sim \mathrm{exAL}_{p_0}(\tilde F_t^\top \alpha_t,\sigma^o,\gamma^o)\).
  - Retrospective product \(j\): \(z_t^j \mid \alpha_t,\delta_t^j,\sigma^j,\gamma^j \sim \mathrm{exAL}_{p_0}(\tilde F_t^\top \alpha_t + F_t^\top \delta_t^j,\sigma^j,\gamma^j)\).
- **Dimensions (theory):**
  - \(\alpha_t\in\mathbb{R}^{q+1+m}\), \(\tilde F_t\in\mathbb{R}^{q+1+m}\).
  - \(\delta_t^j\in\mathbb{R}^q\), \(F_t\in\mathbb{R}^q\).
  - Observation vector at time \(t\): \((y_t^o,z_t^1,\dots,z_t^J)\in\mathbb{R}^{J+1}\).

### T2 — Model B discrepancy evolution equation
- **LaTeX reference:** `main.tex:101–111` (`eq:B_delta`)
- **Statement (per `t=1..T`, `j=1..J`):**
  \(\delta_t^j \mid \delta_{t-1}^j \sim \mathcal{N}(G_t\delta_{t-1}^j,\;W_t^{\delta^j})\).
- **Dimensions:** \(G_t\in\mathbb{R}^{q\times q}\), \(W_t^{\delta^j}\in\mathbb{R}^{q\times q}\).

### T3 — Model C forecast-period ensemble observation + state evolution
- **LaTeX reference:** `main.tex:113–159` (`eq:C_obs`, `eq:C_state`, `eq:C_IW`)
- **Statement (forecast time `t=T+k`):**
  - State: \(\beta_t\in\mathbb{R}^{p_t}\) with \(p_t=q(1+J_f)\), transition \(\beta_t\mid\beta_{t-1},W_t\sim\mathcal{N}(M_t\beta_{t-1},W_t)\).
  - Observation (forecaster `j`, member `i`): \(y_T^{j,i}(k)\mid\beta_{T+k},\sigma^j,\gamma^j\sim \mathrm{exAL}_{p_0}(e_{T+k,j+1}^\top\beta_{T+k},\sigma^j,\gamma^j)\).
  - Evolution covariance prior: \(W_t\sim\mathrm{IW}(\nu_t,S_t)\) (as stated in the document).
- **Dimensions:** \(e_{t,\ell}\in\mathbb{R}^{p_t}\), \(M_t\in\mathbb{R}^{p_t\times p_t}\), \(W_t\in\mathbb{R}^{p_t\times p_t}\).

### T4 — exAL augmentation: Gaussian conditionals + latent priors
- **LaTeX reference:** `main.tex:162–171` (`eq:aug_y`–`eq:aug_s`)
- **Statement (per scalar datum `y_n` with linear predictor `η_n`):**
  \[
  y_n\mid \eta_n,\sigma,\gamma,v_n,s_n \sim \mathcal{N}\!\Big(\eta_n + C(p,\gamma)\sigma|\gamma|s_n + A(p)v_n,\;\sigma B(p)v_n\Big),
  \]
  with \(v_n\mid\sigma\sim\mathrm{Exp}(\text{rate}=1/\sigma)\) and \(s_n\sim\mathcal{N}^+(0,1)\).
- **Dimensions:** all scalars (per-datum augmentation).

### T5 — Mapping \((p_0,\gamma)\mapsto(p,A,B,C)\) and admissible \(\gamma\) interval
- **LaTeX reference:** `main.tex:175–181` (definitions of \(g(\gamma)\), \(p(p_0,\gamma)\), \(A(p)\), \(B(p)\), \(C(p,\gamma)\))
- **Statement:**
  \[
  g(\gamma)=2\Phi(-|\gamma|)\exp(\gamma^2/2),\quad
  p(p_0,\gamma)=\mathbf{1}(\gamma<0)+\frac{p_0-\mathbf{1}(\gamma<0)}{g(\gamma)},
  \]
  \[
  A(p)=\frac{1-2p}{p(1-p)},\quad
  B(p)=\frac{2}{p(1-p)},\quad
  C(p,\gamma)=\big(\mathbf{1}(\gamma>0)-p\big)^{-1}.
  \]
  with \(\gamma\in(L,U)\) enforced by the prior (per document text).

### T6 — Full conditional for \(v_t\): GIG parameterization
- **LaTeX reference:** `main.tex:216–235` (`eq:cond_v`)
- **Statement:**
  - Define \(r_t:=y_t-\eta_t-C(p,\gamma)\sigma|\gamma|s_t\).
  - Then \(v_t\mid\text{rest}\sim\mathrm{GIG}(\lambda=\tfrac12,\chi=r_t^2/(\sigma B),\psi=A^2/(\sigma B)+2/\sigma)\),
    under the density \(f(v)\propto v^{\lambda-1}\exp\{-\tfrac12(\chi/v+\psi v)\}\mathbf{1}(v>0)\).
- **Dimensions:** all scalars per time \(t\).

### T7 — Full conditional for \(s_t\): truncated Normal parameterization
- **LaTeX reference:** `main.tex:237–253` (`eq:cond_s_V`, `eq:cond_s_m`)
- **Statement:**
  - Let \(y_t^\circ:=y_t-\eta_t-Av_t\), \(d:=C(p,\gamma)\sigma|\gamma|\), \(R_t:=\sigma B v_t\).
  - Then \(s_t\mid\text{rest}\sim\mathcal{N}^+(m_{s,t},V_{s,t})\) with
    \(V_{s,t}=(1+d^2/R_t)^{-1}=(1+C(p,\gamma)^2\sigma\gamma^2/(Bv_t))^{-1}\),
    \(m_{s,t}=V_{s,t}\,(d\,y_t^\circ/R_t)=V_{s,t}\,(C(p,\gamma)|\gamma|\,y_t^\circ/(Bv_t))\).
- **Dimensions:** all scalars per time \(t\).

### T8 — Conditional Gaussian pseudo-observations for state-path inference (stacked form)
- **LaTeX reference:** `main.tex:255–298` (`eq:cond_state_path` + “Multiple observations per time” block)
- **Statement:**
  - For each scalar datum: \(\tilde y_{\tau,o}:=y_{\tau,o}-C_{\tau,o}\sigma_{\tau,o}|\gamma_{\tau,o}|s_{\tau,o}-A_{\tau,o}v_{\tau,o}\),
    \(R_{\tau,o}:=\sigma_{\tau,o}B_{\tau,o}v_{\tau,o}\),
    and \(\tilde y_{\tau,o}\mid x_\tau\sim\mathcal{N}(h_{\tau,o}^\top x_\tau,R_{\tau,o})\).
  - Stacked: \(\tilde{\mathbf y}_\tau\mid x_\tau\sim\mathcal{N}(H_\tau^\top x_\tau,\;R_\tau)\) with \(R_\tau=\mathrm{diag}(R_{\tau,o})\).
- **Dimensions:** \(x_\tau\in\mathbb{R}^{p_\tau}\), \(H_\tau\in\mathbb{R}^{p_\tau\times d_\tau}\), \(R_\tau\in\mathbb{R}^{d_\tau\times d_\tau}\).

### T9 — Kalman filter recursions (predict/update moments)
- **LaTeX reference:** `main.tex:751–786` (`eq:ssm_prior_generic`–`eq:ssm_obs_generic`, `eq:kf_pred_mean`–`eq:kf_filt_cov`)
- **Statement (generic DLM):**
  \[
  a_\tau=G_\tau m_{\tau-1},\quad P_\tau=G_\tau C_{\tau-1}G_\tau^\top+W_\tau,\quad
  f_\tau=H_\tau^\top a_\tau,\quad Q_\tau=H_\tau^\top P_\tau H_\tau+R_\tau,
  \]
  \[
  K_\tau=P_\tau H_\tau Q_\tau^{-1},\quad
  m_\tau=a_\tau+K_\tau(\tilde y_\tau-f_\tau),\quad
  C_\tau=P_\tau-K_\tau Q_\tau K_\tau^\top.
  \]

### T10 — RTS smoothing recursions (smoothed moments)
- **LaTeX reference:** `main.tex:806–820` (`eq:ffbs_J`, `eq:ffbs_backward`) and `main.tex:855–861` (`eq:rts_mean`, `eq:rts_cov`)
- **Statement:**
  - Smoothing gain: \(J_\tau=C_\tau G_{\tau+1}^\top P_{\tau+1}^{-1}\).
  - RTS updates:
    \(m_\tau^\star=m_\tau+J_\tau(m_{\tau+1}^\star-a_{\tau+1})\),
    \(C_\tau^\star=C_\tau+J_\tau(C_{\tau+1}^\star-P_{\tau+1})J_\tau^\top\).

### T11 — VB pseudo-data construction from expected information-form parameters
- **LaTeX reference:** `main.tex:604–621` (`eq:vb_info_wb`), `main.tex:828–846` (`eq:vb_pseudodata_scalar`)
- **Statement:**
  - Define \(w_{\tau,o}:=\mathbb{E}_q[1/R_{\tau,o}]>0\) and \(b_{\tau,o}:=\mathbb{E}_q[\tilde y_{\tau,o}/R_{\tau,o}]\).
  - Pseudo-data: \(\bar y_{\tau,o}=b_{\tau,o}/w_{\tau,o}\), \(\bar R_{\tau,o}=1/w_{\tau,o}\),
    and assimilate \(\bar{\mathbf y}_\tau\mid x_\tau\sim\mathcal{N}(H_\tau^\top x_\tau,\bar R_\tau)\).
- **Dimensions:** same as T8/T9.

### T12 — Laplace–Delta approximation for \(q(\sigma,\gamma)\): logistic mapping + Jacobian
- **LaTeX reference:** `main.tex:987–1051` (`eq:transform_u_xi`, `eq:jacobian_u_xi`, `eq:f_tilde_def`, `eq:delta_method_2d`)
- **Statement:**
  - Transform: \(u=\log\sigma\in\mathbb{R}\), \(\gamma=L+(U-L)\pi(\xi)\) with \(\pi(\xi)=1/(1+e^{-\xi})\).
  - Jacobian: \(|\partial(\sigma,\gamma)/\partial(u,\xi)|=\sigma(U-L)\pi(\xi)(1-\pi(\xi))\).
  - Approximate \(q(u,\xi)\) by Laplace at the mode of \(\tilde f(u,\xi)=f(e^u,\gamma(\xi))+\log|J|\), and use the Delta method for required expectations.

### T13 — Priors for \((\sigma,\gamma)\) (per source)
- **LaTeX reference:** `main.tex:183–191`
- **Statement:** \(\sigma\sim\mathrm{InvGamma}(a_\sigma,b_\sigma)\) (as parameterized in the document), and \(\gamma\sim t_{(L,U)}(m_\gamma,s_\gamma;\nu_\gamma)\).

