# C++ Congruence Mismatch Table (A3)

Date: 2026-02-21

| area | expected contract | multiv status | NDLM status | mismatch | severity | fix action |
|---|---|---|---|---|---|---|
| shape guards | fail-fast matrix/cube shape and slice checks | present (comprehensive) | partial/minimal | NDLM lacked equivalent guard breadth | high | port guard utilities and apply at all external-list reads |
| covariance source | explicit covariance source with validated dimensions | `ex_q` / `ex_q_list_ens` explicit + checked | `D` / `D_ens` fixed only (no optional `V_t`) | NDLM lacked explicit expected-covariance mode | high | add optional `D_t` / `D_ens_t` mode with strict checks |
| ragged transdim smoother | rectangular gain and cross-covariance carry across dimension changes | present | present | none | low | retain and document |
| numerical stability | robust inversion and PSD regularization | present | present but less guarded at interface | interface validation weaker in NDLM | medium | add front-door contract checks |
| ELBO term structure | parallel decomposition style and explicit finite checks | present | present | missing explicit ELBO finite assertions in NDLM path | medium | add finite checks around critical ELBO blocks |
| unified backend wiring | NDLM C++ callable via unified selector | n/a | missing | unified NDLM only used R smoother | high | add `models.ndlm_main.kalman_backend: r|cpp` and wire C++ backend |
