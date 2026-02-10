# Phase 5.1b Static Regression exAL Search (Audit Only)

Date (UTC): 2026-02-10 03:17:09
Repo: `/data/muscat_data/jaguir26/project1_ucsc_phd`
Scope: deeper static-regression audit (no code changes), per PHASE 5.1b request.

## 1) Executive Summary

1. `origin/feature/0.5.0-syntheis` is **not present** on this remote (`git ls-remote --heads origin` shows only 4 branches; none named `feature/0.5.0-syntheis`).
2. Therefore, a literal full-tree extraction of that exact ref cannot be performed from this repo state.
3. Across all available remote branches and tags, there are **no `regMod(` hits** and no direct text hits for `"exAL regression"`, `"static regression"`, or `"design matrix"` in `R/man/inst/vignettes/tools/scripts` via `git grep`.
4. Static-regression exAL VB code does exist in this repository lineage as **legacy root scripts** (not package-exported API), notably:
   - `OptimalModelSLexAL.r` (univariate exAL VB workflow)
   - `DISC_Optimal_Synth_Ranges_NDLM.r` (NDLM workflow)
   - `run_scripts_SL.py` (legacy launcher)
5. Candidate branches/tags containing those legacy scripts include:
   - `origin/main`
   - `origin/feature/export_posterior_tables`
   - tag `disc_w_refactor_v1`

## 2) Goal A — Does `origin/feature/0.5.0-syntheis` contain static regression code anywhere?

### 2.1 Ref availability check

- Attempted target ref: `origin/feature/0.5.0-syntheis`
- Result: missing (`TARGET_ARCHIVE=missing_ref:origin/feature/0.5.0-syntheis`)

Because the ref is missing, direct full-tree confirmation on that exact branch is not possible in this clone.

### 2.2 Fallback whole-tree scan (surrogate)

To preserve audit value, a full-tree archive scan was run on `origin/main`.

- Outside-`R/` files (R/Rmd/CPP/H/MD): **75 files** found.
- Broad keyword scan (`regMod|static regression|design matrix|...|VB`) produced many hits, but these are concentrated in:
  - legacy root scripts (`OptimalModelSLexAL.r`, `DISC_Optimal_Synth_Ranges_NDLM.r`)
  - notebook-linearized script (`scripts/_notebook_linearized.R`)
  - exAL distribution package material (`task_medium/*`)

### 2.3 Candidate findings outside `R/` tree

Notable paths from fallback scan:

- `OptimalModelSLexAL.r` (root; static regression/covariate matrix construction in-script)
- `DISC_Optimal_Synth_Ranges_NDLM.r` (root)
- `run_scripts_SL.py` (root launcher)
- `scripts/_notebook_linearized.R` (contains matrix/covariate reconstruction logic; appears notebook-derived)
- `task_medium/` (exAL distribution utilities; not static-regression model stage code)

Conclusion for Goal A: **cannot verify exact target branch due missing ref**; however, in reachable refs static-regression exAL logic is script-based and located outside package-style APIs.

## 3) Goal B — If missing in target branch, where does static regression code exist?

### 3.1 Required pattern search over all remote refs/tags

Searched refs:

- `origin/feature/export_posterior_tables`
- `origin/fix/notebooks-forecast-inventory`
- `origin/main`
- `origin/wrapup/2026-02-07`
- tags: `disc_w_refactor_v1`, `phase2_ok`

`git grep` results for requested patterns over `R/man/inst/vignettes/tools/scripts`:

- `regMod(`: **0 hits**
- `exAL regression`: **0 hits**
- `static regression`: **0 hits**
- `design matrix`: **0 hits**

### 3.2 Branches/tags with strongest static-regression legacy evidence

1. `origin/main`
   - Contains `OptimalModelSLexAL.r`, `DISC_Optimal_Synth_Ranges_NDLM.r`, `run_scripts_SL.py`.
   - `OptimalModelSLexAL.r` includes exAL VB flow and writes `variables_*_exAL_synth_DISC_uni.RData`.
2. `origin/feature/export_posterior_tables`
   - Same legacy scripts and outputs, plus docs (`repro/REPO_MAP.md`) referencing univariate/NDLM artifacts.
3. `disc_w_refactor_v1` (tag)
   - Contains the same script family and legacy output conventions.

Interpretation: static-regression exAL code is present, but as legacy script orchestration, not as a `regMod`-style exported API.

## 4) Recommended Next Audit Target (ONE)

Recommended next deep target: **`origin/main`**.

Reason:

1. It is present and fetchable in this remote.
2. It contains the canonical current legacy scripts used by this repo lineage.
3. It can be audited end-to-end for extraction into modular interfaces without depending on missing refs.

## 5) Phase Status Note

- Keep **Phase 4 closed**.
- `0.5.0-syntheis` replay status cannot be re-verified from this clone because that ref is not present on origin.
- No new evidence here contradicts the prior conclusion that synthesis API replay was the clean part of that line; this audit only confirms where static-regression code lives in currently reachable refs.

## 6) Command Audit (key commands executed)

```bash
git fetch --all --prune --tags
git for-each-ref --format='%(refname:short)' refs/remotes/origin | sort > /tmp/origin_refs.txt
git for-each-ref --format='%(refname:short)' refs/tags | sort > /tmp/tag_refs.txt
cat /tmp/origin_refs.txt /tmp/tag_refs.txt | sed '/^$/d' | sort -u > /tmp/search_refs.txt

git archive origin/feature/0.5.0-syntheis | tar -x -C <tmp>   # failed: missing ref

# required remote grep patterns
for p in "regMod(" "exAL regression" "static regression" "design matrix"; do
  git grep -n "$p" $(cat /tmp/origin_refs.txt) -- "R" "man" "inst" "vignettes" "tools" "scripts" 2>/dev/null | head -n 200
done

# branch/tag broad evidence
for ref in $(cat /tmp/search_refs.txt); do
  git ls-tree -r --name-only "$ref" | rg "OptimalModelSLexAL.r|DISC_Optimal_Synth_Ranges_NDLM.r|run_scripts_SL.py|regMod|static|exAL|synth"
done

# fallback whole-tree surrogate scan
git archive origin/main | tar -x -C <tmp2>
find <tmp2> -type f \( -name "*.R" -o -name "*.Rmd" -o -name "*.cpp" -o -name "*.h" -o -name "*.md" \) | rg -v '/R/'
rg -n "regMod\b|static regression|design matrix|model matrix|\bbeta\b|\bX\b|exAL\b|ALD\b|CAVI\b|LDVB\b|VB\b" <tmp2> -S
rg -n "synth|synthesis|isoreg|monotone|rearrang" <tmp2> -S
```
