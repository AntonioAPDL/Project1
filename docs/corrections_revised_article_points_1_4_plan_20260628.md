# Corrections/Revised-Article Points 1 And 4 Implementation Plan

Date: 2026-06-28

## Scope

This plan refines the next manuscript/corrections synchronization pass for the
two outstanding high-risk items from the recent correction cleanup list:

1. the inverse-Wishart forecast-covariance prior wording, especially the
   manuscript-facing value of the scale multiplier `c`;
2. the editor-facing explanation that the revised forecasting analysis was
   rebuilt after a retrospective/forecast-product version-matching audit.

The goal is not to relaunch any model. The goal is to make the revised article,
corrections response, manifests, validators, and workflow documentation agree
with the current executable authority.

## Current Evidence Lock

### Repository State

At the time of this plan, the workflow repository is clean on `main`. The
revised article and corrections repositories have generated HE3 ablation table
and artifact updates that still need a validation/commit pass before any broader
manuscript cleanup is considered complete.

### Point 1: Inverse-Wishart `c`

The current revised manuscript already contains the correct implementation-level
statement in the prior discussion:

- `Evironmetrics---REVISED-DOC-Corrected-2/wileyNJD-APA.tex`
  describes the forecast-window inverse-Wishart prior as
  `S_t = (nu_t - p_t - 1) c W_T`, then states that selected publication fits use
  `c = 1`.

The current authoritative selected `exAL-M-T1` rows also agree with this:

- `config/he3_exdqlm_ablation_current_authority_20260625_best_by_cutoff_long.csv`
  records `best_c_factor = 1.0` for all five selected `exAL-M-T1` cutoffs.

Important nuance: the current selected `epsilon` values are cutoff-specific, not
uniformly `365`. The current selected `exAL-M-T1` rows are:

| Cutoff | Selected source | epsilon | c_factor |
|---|---|---:|---:|
| 2021-01-23 | `c04_eps365` | 365 | 1 |
| 2021-11-12 | `c04_eps365` | 365 | 1 |
| 2021-12-21 | `he2partial20260623` | 30 | 1 |
| 2022-05-11 | `he2partial20260623` | 1 | 1 |
| 2022-12-25 | `he2partial20260623` | 1 | 1 |

Therefore, the optimal correction is **not** to add a blanket statement that
all selected fits used `epsilon = 365`, and it is not to revive the old `c =
10^2` statement. The robust correction is:

- keep `c = 1` as the selected-fit manuscript statement;
- keep `epsilon = 365` as a meaningful search/sensitivity value when relevant;
- keep final selected `epsilon` values tied to manifests and resolved configs;
- add a validation gate that fails if the revised article or corrections
  response states `c = 10^2` as the selected publication setting.

### Point 4: Version-Matched Input Bundles

The corrections response already contains a concise editor-facing disclosure:

- `Corrections---Project-1/main.tex` states that the revision re-audited
  retrospective and forecast-product archives, identified a version-matching
  inconsistency in the historical support, rebuilt affected rolling-origin
  bundles under a version-consistent contract, reran affected comparisons, and
  regenerated manuscript-facing tables and figures.

The revised manuscript already supports the same claim through its application
and rolling-origin design language:

- `wileyNJD-APA.tex` distinguishes USGS observations, retrospective products,
  forecast products, and forecast covariates;
- it states that the five cutoffs are constrained by version-consistent forecast
  archives;
- it states that fitting uses USGS and retrospective products through the
  cutoff, while forecast-window synthesis uses latest issued forecast products
  and forecast covariates staged in the same origin bundle.

The optimal correction is therefore to keep the corrections response concise,
but make the claim more auditable by tying it to the existing workflow contracts
and manifests. We should avoid overexplaining the operational data-recovery work
in the manuscript body unless it improves reader understanding.

## Plan

### Phase 0: Freeze The Current Generated-State Boundary

1. Treat the current HE3 generated changes in the revised article and
   corrections repositories as a separate pending promotion bundle.
2. Before editing prose, run a quick diff review on those generated table and
   artifact files to ensure they are only HE3 ablation refresh products.
3. Do not mix prose edits with generated table refreshes in the same commit
   unless the final diff is tiny and self-evidently coupled.

Why this is optimal: the current dirty state is generated output from a completed
ablation workflow. Mixing it with prose corrections would make it harder to
review or revert if Overleaf/GitHub synchronization is sensitive again.

### Phase 1: Add A Structured Prior-Claim Gate For Point 1

1. Extend the article-side or workflow-side validation script to parse the
   current HE2 publication manifest and verify:
   - selected multivariate forecast-covariance prior entries expose
     `forecast_cov.c_factor`;
   - all selected `exAL-M-T1` rows have `c_factor = 1.0`;
   - selected `epsilon` is permitted to vary by cutoff;
   - article/corrections prose does not state `c = 10^2` as a selected
     publication setting.
2. Keep the check structured where possible by reading `prior_json` from
   `artifacts/he2_publication_freeze/he2_bayesian_publication_manifest.csv`
   rather than relying only on string scans.
3. Add a small string scan only for stale prohibited wording, because the risk
   there is a manuscript prose regression.

Why this is optimal: it separates the executable prior contract from prose. The
manifest establishes what was run; the prose scan prevents accidental re-entry
of the old `c = 10^2` claim.

### Phase 2: Patch Point 1 Wording Only If The Gate Finds A Mismatch

If validation finds stale or ambiguous wording, use the following manuscript
contract:

- The general prior formula includes `c` and `epsilon`.
- The selected publication fits use `c = 1`, anchoring the forecast covariance
  to the learned pre-cutoff covariance without additional inflation.
- `epsilon` controls the effective prior strength and was varied during
  specification search; exact cutoff-specific selected values are recorded in
  manifests/resolved configs.
- `epsilon = 365` may be described as a one-year daily-data reference value only
  in search/sensitivity context.

Do not add a prose table of all cutoff-specific epsilons to the main manuscript
unless space and readability require it. The manifest is the right place for the
full hyperparameter table.

### Phase 3: Strengthen Point 4 Without Overloading The Manuscript

1. Keep the corrections response disclosure near the opening summary and HE-2
   response, because this is primarily an editor/reviewer transparency issue.
2. In the revised manuscript, keep the technical treatment inside the
   application/rolling-origin design section:
   - define retrospective products as historical discrepancy-learning inputs;
   - define forecast ensembles as post-cutoff forecast-window inputs;
   - state that retained cutoffs require version-consistent archives;
   - state that post-cutoff USGS is verification only.
3. Add or preserve manifest/document cross-references:
   - `docs/he6_out_of_sample_forecast_design_contract_20260615.md`;
   - `docs/he7_latest_forecast_issue_contract_20260615.md`;
   - article `artifacts/forecast_design/forecast_design_manifest.json`;
   - article `artifacts/latest_forecast_issue/latest_forecast_issue_manifest.json`;
   - article `artifacts/he2_publication_freeze/`.

Why this is optimal: point 4 needs transparency, but not a long detour in the
scientific manuscript. The response letter can explain why results changed; the
article should define the corrected design and provenance succinctly.

### Phase 4: Cross-Repo Validation

Run the validation in this order:

1. Workflow repo:
   - `python3 -m py_compile scripts/validate_publication_freeze.py scripts/validate_revision_cross_repo_wiring.py`
   - targeted unit tests for any new prior/prose gate
   - `python3 scripts/validate_publication_freeze.py`
   - `python3 scripts/validate_revision_cross_repo_wiring.py --check-only --strict`
2. Revised article repo:
   - `python3 -m unittest discover -s tests -v`
   - full `pdflatex`, `bibtex`, `pdflatex`, `pdflatex` sequence
3. Corrections repo:
   - `make`

Do not declare the pass complete until article and corrections generated tables
compile with the current HE3 ablation updates present.

### Phase 5: Commit Organization

Use separate commits:

1. workflow repo: validators/tests/docs only;
2. revised article repo: prose, generated tables/artifacts, tests/manifests;
3. corrections repo: response prose and synced generated table fragments.

Before pushing, verify all three repos are on `main`, clean except expected
ahead-of-origin status, and do not include `.RData`, `.rda`, `.rdata`, runtime
roots, or large uncurated support dumps.

## Concrete Checklist

- [ ] Review HE3 generated diffs in article/corrections repos and decide whether
      to commit them before prose edits.
- [ ] Add/confirm structured validation for selected `c_factor = 1.0`.
- [ ] Add/confirm stale-prose validation blocking selected-fit `c = 10^2`
      claims.
- [ ] Confirm article prior paragraph keeps `c = 1` and cutoff-specific
      `epsilon` wording.
- [ ] Confirm corrections response point 4 disclosure remains concise and
      editor-facing.
- [ ] Confirm revised manuscript rolling-origin section carries the corrected
      version-consistent design but not excessive data-recovery detail.
- [ ] Run workflow validators.
- [ ] Run revised article tests and full TeX compile.
- [ ] Run corrections `make`.
- [ ] Commit and push each repo separately after validation.

## Main Risks

1. **Overclaiming epsilon.** The current selected rows do not all use
   `epsilon = 365`; prose must not imply they do.
2. **Reviving stale `c = 10^2`.** This should be treated as a legacy/reference
   value only if mentioned at all, never as the selected setting.
3. **Mixing generated table promotion with prose edits.** Keep commits small so
   Overleaf-facing review remains manageable.
4. **Manuscript overexplanation.** The version-matching correction belongs in
   the response letter and provenance docs; the article should present the
   corrected design cleanly.

