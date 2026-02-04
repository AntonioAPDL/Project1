# Used-Code Inventory (Static Trace)

Scope: static (no execution) linkage trace for:

- R runner: `DISC_Optimal_Synth_Ranges_W.r`
- Local C++ files compiled via `Rcpp::sourceCpp(...)`

This document answers Stage A (A1–A2): what R/C++ entrypoints are actually used by the pipeline, and whether `kalman_synth.cpp` is active.

---

## A1. R → C++ linkage (no execution)

### A1.1 Sourced R files

No `source(...)` calls appear in `DISC_Optimal_Synth_Ranges_W.r` (static grep for `source(` returned none), so all helper functions appear to be defined inline in this script.

### A1.2 Compiled code brought in by the script

The script compiles/loads three C++ translation units via `Rcpp::sourceCpp`:

- `DISC_Optimal_Synth_Ranges_W.r:52` → `sampling_exal.cpp`
- `DISC_Optimal_Synth_Ranges_W.r:53` → `sampling_truncnorm.cpp`
- `DISC_Optimal_Synth_Ranges_W.r:54` → `DISC_kalman_synth.cpp`

These are the only `.cpp` paths referenced in the runner (static grep for `\\.cpp`).

**Note:** the historical exported-name collision on `sample_truncnorm(...)` has been removed. The runner now calls
`sample_truncnorm_icdf(...)` explicitly (see `discrepancy_resolution_notes.md`).

### A1.3 Exported C++ functions compiled/available

From the three compiled files (as declared by `// [[Rcpp::export]]`):

- `sampling_exal.cpp` exports: `sample_gig_devroye_vector`, `sample_truncnorm_reject`, `sample_multivariate_normal`, `samp_post_pred`, `generate_samples`, `samp_post_pred_synth`, `generate_synth_samples`, `generate_synth_samples_retro_part`, `generate_synth_samples_forecast_part`, `samp_post_pred_extended`, `generate_samples_ext`, `DISC_sample_multivariate_normal`, `DISC_generate_synth_samples_retro_part`.
- `sampling_truncnorm.cpp` exports: `sample_truncnorm_icdf` (canonical) and a backward-compatible alias `sample_truncnorm`.
- `DISC_kalman_synth.cpp` exports: `logDetCholesky`, `DISC_update_theta_synth_cpp`, `DISC_update_theta_synth_cpp_W`.

### A1.4 Exported C++ functions actually called from the runner

Static call-site search within `DISC_Optimal_Synth_Ranges_W.r` found calls to **exactly four** exported C++ functions:

1) **Kalman/VB state update**
- R call site: `DISC_Optimal_Synth_Ranges_W.r:1691`
- C++ entrypoint: `DISC_update_theta_synth_cpp_W(...)`
- C++ file: `DISC_kalman_synth.cpp:791` (`// [[Rcpp::export]]`)
- Role (per naming + args): Kalman filtering / smoothing state update with evolution covariance inputs (`W_list_ens` etc.).

2) **GIG sampling (latent v / “uts”)**
- R call sites: `DISC_Optimal_Synth_Ranges_W.r:2117`, `DISC_Optimal_Synth_Ranges_W.r:2203`
- C++ entrypoint: `sample_gig_devroye_vector(...)`
- C++ file: `sampling_exal.cpp:97`
- Role: vectorized generalized inverse Gaussian sampling (Devroye sampler).

3) **Truncated Normal sampling (latent s / “sts”)**
- R call sites: `DISC_Optimal_Synth_Ranges_W.r:2119`, `DISC_Optimal_Synth_Ranges_W.r:2205`
- C++ entrypoint: `sample_truncnorm_icdf(...)`
- C++ file: `sampling_truncnorm.cpp`
- Role: vectorized truncated-normal sampling.

4) **Gaussian sampling for trajectories (retro + forecast blocks)**
- R call sites: `DISC_Optimal_Synth_Ranges_W.r:2272`, `DISC_Optimal_Synth_Ranges_W.r:2279`
- C++ entrypoint: `DISC_generate_synth_samples_retro_part(...)`
- C++ file: `sampling_exal.cpp:401`
- Role: multivariate normal path simulation given `(sm, sC)` for retrospective/forecast blocks.

No static call sites were found in the runner for:
- `logDetCholesky`, `DISC_update_theta_synth_cpp` (in `DISC_kalman_synth.cpp`)
- `generate_samples`, `sample_multivariate_normal`, `samp_post_pred`, etc. (in `sampling_exal.cpp`)

### A1.5 Call graph (R → C++)

```
DISC_Optimal_Synth_Ranges_W.r
  ├─ sourceCpp(sampling_exal.cpp)                   [L52]
  │    ├─ sample_gig_devroye_vector(...)            [called at L2117, L2203]
  │    └─ DISC_generate_synth_samples_retro_part(...) [called at L2272, L2279]
  ├─ sourceCpp(sampling_truncnorm.cpp)              [L53]
  │    └─ sample_truncnorm_icdf(...)                [called at L2119, L2205]
  └─ sourceCpp(DISC_kalman_synth.cpp)               [L54]
       └─ DISC_update_theta_synth_cpp_W(...)        [called at L1691]
```

### A1.6 Used C++ entrypoints table

| R call site | C++ function | C++ file | Role |
|---|---|---|---|
| `DISC_Optimal_Synth_Ranges_W.r:1691` | `DISC_update_theta_synth_cpp_W` | `DISC_kalman_synth.cpp:791` | Kalman/VB state update (filter/smoother core) |
| `DISC_Optimal_Synth_Ranges_W.r:2117` | `sample_gig_devroye_vector` | `sampling_exal.cpp:97` | GIG sampling (latent `v`/`uts`) |
| `DISC_Optimal_Synth_Ranges_W.r:2119` | `sample_truncnorm_icdf` | `sampling_truncnorm.cpp` | Trunc-normal sampling (latent `s`/`sts`) |
| `DISC_Optimal_Synth_Ranges_W.r:2203` | `sample_gig_devroye_vector` | `sampling_exal.cpp:97` | GIG sampling for ensemble block |
| `DISC_Optimal_Synth_Ranges_W.r:2205` | `sample_truncnorm_icdf` | `sampling_truncnorm.cpp` | Trunc-normal sampling for ensemble block |
| `DISC_Optimal_Synth_Ranges_W.r:2272` | `DISC_generate_synth_samples_retro_part` | `sampling_exal.cpp:401` | MVN path sampling (retro) |
| `DISC_Optimal_Synth_Ranges_W.r:2279` | `DISC_generate_synth_samples_retro_part` | `sampling_exal.cpp:401` | MVN path sampling (forecast blocks) |

---

## A2. Confirm Kalman implementation location

### A2.1 Is `kalman_synth.cpp` used?

**No** (for this runner).

Evidence:
- The runner compiles `DISC_kalman_synth.cpp` (not `kalman_synth.cpp`) via `Rcpp::sourceCpp` at `DISC_Optimal_Synth_Ranges_W.r:54`.
- There are no `sourceCpp(...)`, `dyn.load(...)`, `.Call(...)`, or other explicit compilation/loading hooks referencing `kalman_synth.cpp` in the runner (static grep for `\\.cpp` yields only the three files in A1.2).

### A2.2 Where is the active Kalman core?

For this pipeline, the Kalman core is implemented in:

- `DISC_kalman_synth.cpp`, via `DISC_update_theta_synth_cpp_W(...)` (export at `DISC_kalman_synth.cpp:791`, called from `DISC_Optimal_Synth_Ranges_W.r:1691`).

---

## Unused `.cpp` files (relative to this runner)

Top-level `.cpp` files present in `/data/muscat_data/jaguir26/project1_ucsc_phd` (maxdepth 2) and whether they are used by this runner:

**Used (compiled via `sourceCpp` in the runner):**
- `sampling_exal.cpp` (`DISC_Optimal_Synth_Ranges_W.r:52`)
- `sampling_truncnorm.cpp` (`DISC_Optimal_Synth_Ranges_W.r:53`)
- `DISC_kalman_synth.cpp` (`DISC_Optimal_Synth_Ranges_W.r:54`)

**Not used by this runner (no compilation/loading reference in the script):**
- `abcp.cpp`
- `DISC_kalman_synth_NDLM.cpp`
- `gig_test.cpp`
- `kalman.cpp`
- `kalman_fullsynth.cpp`
- `kalman_NDLM.cpp`
- `kalman_sub.cpp`
- `kalman_synth.cpp`
- `kalman_synth_NDLM.cpp`
- `sampling_exal_legacy.cpp`
- `test_eigen.cpp`

Reason (static): none of these appear in `DISC_Optimal_Synth_Ranges_W.r` via `sourceCpp/dyn.load/.Call`, and the compiled translation units used by the script do not `#include` these `.cpp` files.

---

## Notes / limitations

- The runner loads many R packages (e.g., `exdqlm`, `dlm`, `nimble`, …). This Stage-A inventory is restricted to *local* compiled code explicitly loaded by `sourceCpp(...)`. If you want, we can extend Stage A to statically trace any package-level compiled symbols by inspecting package sources (if available locally) and identifying which package functions are called by the runner.
