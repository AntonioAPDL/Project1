# Decision gate (no-rerun-first policy)

Gate evaluation:
1. Missing diagnostics export? -> RESOLVED IN CODE (new fit-mode exports added).
2. Unexpected parity mismatch? -> No hard blocker found in discount/W_t semantics.
3. Can root cause be classified from current artifacts? -> Partially yes (diagnostic interpretation issue confirmed), calibration quality still open.

Decision:
- Do not run broad refits in this step.
- Next run should be one NDLM-only lean lane to populate new mode-separated diagnostics (`one_step`, `filtered`, `smoothed`) and assess calibration quality with the corrected diagnostic lens.
