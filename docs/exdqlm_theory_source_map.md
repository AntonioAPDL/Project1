# exDQLM Theory Source Map

Date: 2026-05-20

## Purpose

This document defines a source-of-truth hierarchy for the exAL / exDQLM model family used in this
repository, with a specific focus on:

- the multivariate exDQLM `keep` / `drop` forecast-transfer variants
- the joint VB update for `(sigma, gamma)`
- the Laplace-Delta approximation used for `q(sigma, gamma)`

This source map does **not** take older notes or manuscript mirrors for granted. Every source below is
classified by how it should be used in the audit:

- `primary`: can define the intended mathematical contract
- `implementation`: can define what the current code actually does
- `secondary`: useful bridge / audit note, but must be rechecked against the current implementation
- `historical`: useful context only; not authoritative without direct verification

## Audit rule

For this audit, a statement is only treated as "confirmed" if it satisfies both:

1. it appears in a primary or implementation source, and
2. it is consistent with the current active implementation path

If a source conflicts with the active implementation, it is treated as stale or historical until
reconciled.

## Current active implementation path

For the ongoing reduced multivariate `keep` runs in this repository, the active path for the theory
we care about is:

1. exAL coefficient helpers and support bounds:
   - [R/environmetrics/02_helpers_core.R](/data/muscat_data/jaguir26/project1_ucsc_phd/R/environmetrics/02_helpers_core.R:1504)
2. forecast-transfer `keep` / `drop` state construction:
   - [R/environmetrics/20_model_setup.R](/data/muscat_data/jaguir26/project1_ucsc_phd/R/environmetrics/20_model_setup.R:207)
3. joint VB update for `(sigma, gamma)` and the Laplace-Delta machinery:
   - [DISC_Optimal_Synth_Ranges_W_transfer_forecast.r](/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:1874)

Historical duplicate implementations exist, but they are not the first source of truth for the current
launched workflow.

## Source inventory

### A. Primary mathematical sources

#### A1. Canonical manuscript source
- Path:
  - [main.tex](/data/muscat_data/jaguir26/exDQLM---Ensemble/main.tex)
  - [main.pdf](/data/muscat_data/jaguir26/exDQLM---Ensemble/main.pdf)
- Classification: `primary`
- Role:
  - main mathematical definition of Models A, B, C, and C-T
  - latent augmentation
  - VB pseudo-data construction
  - Laplace-Delta transform, Jacobian, mode covariance, and delta-method expectations
- Key anchors:
  - Model A observation + transfer:
    - [main.tex:63](/data/muscat_data/jaguir26/exDQLM---Ensemble/main.tex:63)
    - [main.tex:67](/data/muscat_data/jaguir26/exDQLM---Ensemble/main.tex:67)
  - Model B retrospective discrepancy:
    - [main.tex:107](/data/muscat_data/jaguir26/exDQLM---Ensemble/main.tex:107)
    - [main.tex:109](/data/muscat_data/jaguir26/exDQLM---Ensemble/main.tex:109)
  - Model C forecast transfer omitted:
    - [main.tex:139](/data/muscat_data/jaguir26/exDQLM---Ensemble/main.tex:139)
    - [main.tex:141](/data/muscat_data/jaguir26/exDQLM---Ensemble/main.tex:141)
  - Model C-T forecast transfer retained:
    - [main.tex:161](/data/muscat_data/jaguir26/exDQLM---Ensemble/main.tex:161)
    - [main.tex:192](/data/muscat_data/jaguir26/exDQLM---Ensemble/main.tex:192)
    - [main.tex:200](/data/muscat_data/jaguir26/exDQLM---Ensemble/main.tex:200)
  - `v_t` and `s_t` conditionals:
    - [main.tex:337](/data/muscat_data/jaguir26/exDQLM---Ensemble/main.tex:337)
    - [main.tex:357](/data/muscat_data/jaguir26/exDQLM---Ensemble/main.tex:357)
    - [main.tex:359](/data/muscat_data/jaguir26/exDQLM---Ensemble/main.tex:359)
  - VB pseudo-data:
    - [main.tex:711](/data/muscat_data/jaguir26/exDQLM---Ensemble/main.tex:711)
    - [main.tex:956](/data/muscat_data/jaguir26/exDQLM---Ensemble/main.tex:956)
  - joint `q(sigma, gamma)` kernel:
    - [main.tex:735](/data/muscat_data/jaguir26/exDQLM---Ensemble/main.tex:735)
    - [main.tex:748](/data/muscat_data/jaguir26/exDQLM---Ensemble/main.tex:748)
  - Laplace-Delta transform:
    - [main.tex:1125](/data/muscat_data/jaguir26/exDQLM---Ensemble/main.tex:1125)
    - [main.tex:1139](/data/muscat_data/jaguir26/exDQLM---Ensemble/main.tex:1139)
    - [main.tex:1147](/data/muscat_data/jaguir26/exDQLM---Ensemble/main.tex:1147)
    - [main.tex:1162](/data/muscat_data/jaguir26/exDQLM---Ensemble/main.tex:1162)
    - [main.tex:1181](/data/muscat_data/jaguir26/exDQLM---Ensemble/main.tex:1181)
- Audit status: `confirmed as the main intended equation source`

#### A2. Project manuscript mirror
- Path:
  - [article.txt](/data/muscat_data/jaguir26/project1_ucsc_phd/article.txt)
- Classification: `primary but weaker than main.tex`
- Role:
  - local manuscript mirror with matching broad model narrative
  - useful when the current repo must be self-contained
- Key anchors:
  - exAL / DQLM framing:
    - [article.txt:68](/data/muscat_data/jaguir26/project1_ucsc_phd/article.txt:68)
    - [article.txt:70](/data/muscat_data/jaguir26/project1_ucsc_phd/article.txt:70)
  - VB algorithm steps:
    - [article.txt:729](/data/muscat_data/jaguir26/project1_ucsc_phd/article.txt:729)
    - [article.txt:735](/data/muscat_data/jaguir26/project1_ucsc_phd/article.txt:735)
  - required expectation formulas:
    - [article.txt:755](/data/muscat_data/jaguir26/project1_ucsc_phd/article.txt:755)
    - [article.txt:763](/data/muscat_data/jaguir26/project1_ucsc_phd/article.txt:763)
- Audit status: `usable, but must be checked against main.tex and current code`

### B. Current implementation sources

#### B1. exAL support and coefficient functions
- Path:
  - [R/environmetrics/02_helpers_core.R](/data/muscat_data/jaguir26/project1_ucsc_phd/R/environmetrics/02_helpers_core.R:1504)
- Classification: `implementation`
- Role:
  - defines `L_fn`, `U_fn`, `p_fn`, `A_fn`, `B_fn`, `C_fn`
- Key anchors:
  - [R/environmetrics/02_helpers_core.R:1508](/data/muscat_data/jaguir26/project1_ucsc_phd/R/environmetrics/02_helpers_core.R:1508)
  - [R/environmetrics/02_helpers_core.R:1516](/data/muscat_data/jaguir26/project1_ucsc_phd/R/environmetrics/02_helpers_core.R:1516)
  - [R/environmetrics/02_helpers_core.R:1520](/data/muscat_data/jaguir26/project1_ucsc_phd/R/environmetrics/02_helpers_core.R:1520)
  - [R/environmetrics/02_helpers_core.R:1525](/data/muscat_data/jaguir26/project1_ucsc_phd/R/environmetrics/02_helpers_core.R:1525)
  - [R/environmetrics/02_helpers_core.R:1530](/data/muscat_data/jaguir26/project1_ucsc_phd/R/environmetrics/02_helpers_core.R:1530)
- Audit status: `current code anchor`

#### B2. Current keep/drop forecast-transfer implementation
- Path:
  - [R/environmetrics/20_model_setup.R](/data/muscat_data/jaguir26/project1_ucsc_phd/R/environmetrics/20_model_setup.R:207)
- Classification: `implementation`
- Role:
  - defines whether forecast transfer coordinates are retained or dropped
  - constructs the forecast-state FF/GG objects accordingly
- Key anchors:
  - mode switch:
    - [R/environmetrics/20_model_setup.R:208](/data/muscat_data/jaguir26/project1_ucsc_phd/R/environmetrics/20_model_setup.R:208)
  - retained transfer block:
    - [R/environmetrics/20_model_setup.R:226](/data/muscat_data/jaguir26/project1_ucsc_phd/R/environmetrics/20_model_setup.R:226)
    - [R/environmetrics/20_model_setup.R:269](/data/muscat_data/jaguir26/project1_ucsc_phd/R/environmetrics/20_model_setup.R:269)
  - dropped transfer block:
    - [R/environmetrics/20_model_setup.R:271](/data/muscat_data/jaguir26/project1_ucsc_phd/R/environmetrics/20_model_setup.R:271)
- Audit status: `current code anchor`

#### B3. Current joint VB update for `(sigma, gamma)`
- Path:
  - [DISC_Optimal_Synth_Ranges_W_transfer_forecast.r](/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:1874)
- Classification: `implementation`
- Role:
  - active `update_gamma_sigma` used by the current multivariate transfer workflow
  - defines transformed objective, optimization, Hessian inversion, and Delta-method expectations
- Key anchors:
  - transform and coefficient evaluation:
    - [DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:1913](/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:1913)
    - [DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:2031](/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:2031)
  - logistic map and Jacobian:
    - [DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:2033](/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:2033)
    - [DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:2060](/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:2060)
  - optimization:
    - [DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:2265](/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:2265)
  - Laplace covariance:
    - [DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:2165](/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:2165)
    - [DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:2314](/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:2314)
  - Delta expectations:
    - [DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:2343](/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:2343)
- Audit status: `current code anchor`

### C. Secondary bridge / audit sources

#### C1. Theory checklist
- Path:
  - [theory_spec_checklist.md](/data/muscat_data/jaguir26/project1_ucsc_phd/theory_spec_checklist.md)
- Classification: `secondary`
- Role:
  - compact contract extracted from `main.tex`
  - useful as an audit checklist
- Strength:
  - already points to the relevant manuscript equations and active code path
- Limitation:
  - must be rechecked against the current implementation every time
- Audit status: `useful and mostly aligned`

#### C2. Discrepancy resolution notes
- Path:
  - [discrepancy_resolution_notes.md](/data/muscat_data/jaguir26/project1_ucsc_phd/discrepancy_resolution_notes.md)
- Classification: `secondary`
- Role:
  - records explicit theory↔code fixes for the Laplace-Delta transform
- Strength:
  - directly names the logistic mapping and Jacobian issue
- Limitation:
  - it is a change log, not the canonical theorem statement
- Audit status: `strong supporting evidence`

#### C3. Discrepancy report
- Path:
  - [discrepancy_report.md](/data/muscat_data/jaguir26/project1_ucsc_phd/discrepancy_report.md)
- Classification: `secondary`
- Role:
  - summarizes resolved or unresolved theory/code gaps
- Audit status: `triage document only`

#### C4. Wishart workflow runbook
- Path:
  - [docs/DISC_W_WORKFLOW.md](/data/muscat_data/jaguir26/project1_ucsc_phd/docs/DISC_W_WORKFLOW.md)
- Classification: `secondary`
- Role:
  - operational map of the active Wishart / ensemble workflow
- Strength:
  - useful for implementation path discovery
- Limitation:
  - not itself a mathematical source
- Audit status: `implementation map only`

### D. Historical / non-authoritative but useful comparison sources

#### D1. Derivation audit
- Path:
  - [docs/DERIVATION_AUDIT.md](/data/muscat_data/jaguir26/project1_ucsc_phd/docs/DERIVATION_AUDIT.md)
- Classification: `historical / potentially stale`
- Why not primary:
  - it still describes a double-exponential interior map for `gamma`, which conflicts with:
    - [main.tex:1125](/data/muscat_data/jaguir26/exDQLM---Ensemble/main.tex:1125)
    - [DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:2033](/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:2033)
- Audit status: `do not trust without re-verification`

#### D2. Historical implementation prototypes
- Paths:
  - [LD_vs_IS_synth.R](/data/muscat_data/jaguir26/project1_ucsc_phd/LD_vs_IS_synth.R)
  - [Optimal_DQLM.r](/data/muscat_data/jaguir26/project1_ucsc_phd/Optimal_DQLM.r)
  - [opt_delta.r](/data/muscat_data/jaguir26/project1_ucsc_phd/opt_delta.r)
  - [opt_delta_3.r](/data/muscat_data/jaguir26/project1_ucsc_phd/opt_delta_3.r)
- Classification: `historical`
- Role:
  - useful for understanding how the sigma/gamma update evolved
- Strength:
  - exposes earlier versions of `update_gamma_sigma`
- Limitation:
  - these are not the authoritative current path for the live multivariate keep/drop runs
- Audit status: `comparison-only`

#### D3. Similar repository snapshot
- Path:
  - [project1_ucsc_phd_v8_launch_471fcfd](/data/muscat_data/jaguir26/project1_ucsc_phd_v8_launch_471fcfd)
- Classification: `historical / cross-check`
- Role:
  - contains parallel copies of the same theory and implementation files
- Audit status: `backup comparison source`

## Source precedence for the audit

Use this precedence order for all future theory checks:

1. [main.tex](/data/muscat_data/jaguir26/exDQLM---Ensemble/main.tex)
2. current implementation source files:
   - [DISC_Optimal_Synth_Ranges_W_transfer_forecast.r](/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:1874)
   - [R/environmetrics/20_model_setup.R](/data/muscat_data/jaguir26/project1_ucsc_phd/R/environmetrics/20_model_setup.R:207)
   - [R/environmetrics/02_helpers_core.R](/data/muscat_data/jaguir26/project1_ucsc_phd/R/environmetrics/02_helpers_core.R:1508)
3. [theory_spec_checklist.md](/data/muscat_data/jaguir26/project1_ucsc_phd/theory_spec_checklist.md)
4. [discrepancy_resolution_notes.md](/data/muscat_data/jaguir26/project1_ucsc_phd/discrepancy_resolution_notes.md)
5. [article.txt](/data/muscat_data/jaguir26/project1_ucsc_phd/article.txt)
6. all historical scripts and older audits

## Current conclusions from Stage 1

1. We **do** have a canonical mathematical source:
   - [main.tex](/data/muscat_data/jaguir26/exDQLM---Ensemble/main.tex)
2. We **do** have enough material to audit the current implementation rigorously.
3. `keep` vs `drop` is **not** just a post-hoc label:
   - the manuscript contains both Model C and Model C-T
   - the current code has a concrete forecast-transfer mode switch
4. Some older audit documents are stale and should not be trusted blindly.
5. The correct audit workflow is:
   - extract equations from `main.tex`
   - map them to the active current code
   - only then use the older notes as historical context
