# Test And Check Matrix

## Purpose
This matrix defines the required checks for the representative `exAL-M-T1` end-to-end audit. It is intentionally separate from the narrative audit plan so we can execute and mark checks systematically.

## Check Inventory
| ID | Workstream | Check | Method | Evidence | Pass condition |
|---|---|---|---|---|---|
| A1 | Scale contract | raw USGS scale confirmed | row inspection + source trace | raw source path + sample rows | values and transform documented |
| A2 | Scale contract | shared-bundle USGS scale confirmed | bundle file inspection | bundle path + sample rows | matches intended contract |
| A3 | Scale contract | fit response `Y` scale confirmed | object extraction | fit-stage evidence | no ambiguity remains |
| A4 | Scale contract | post cache object scales confirmed | cache inspection + code trace | cache paths + code refs | each cache has explicit scale label |
| A5 | Scale contract | exported figure/CSV scale confirmed | code trace + file comparison | output paths + code refs | plot labels and underlying objects agree |
| B1 | Pre-fit lineage | raw -> adapter -> bundle dates aligned | date diff check | comparison table | no unexplained offsets |
| B2 | Pre-fit lineage | raw -> adapter -> bundle values aligned | value spot-check | comparison table | transforms reconcile |
| B3 | Pre-fit lineage | cutoff split correct | boundary check | cutoff table | history/forecast split correct |
| B4 | Pre-fit lineage | forecast covariate lineage correct | path trace | input evidence | expected forecast adapters used |
| C1 | Semantics | `xb` extracted for reference dates | decomposition script | decomposition table | values reproducible |
| C2 | Semantics | shift term extracted | decomposition script | decomposition table | values reproducible |
| C3 | Semantics | exAL location parameter derived | decomposition script | decomposition table | formula and values agree |
| C4 | Semantics | row predictive quantiles computed | sample inspection | decomposition table | values reproducible |
| C5 | Semantics | synthesized quantiles linked to row objects | comparison check | comparison table | relationship explained |
| D1 | Historical slices | dry window diagnostic stable | figure review + summary stats | dry report | interpretable outputs produced |
| D2 | Historical slices | wet window diagnostic stable | figure review + summary stats | wet report | interpretable outputs produced |
| D3 | Historical slices | last200 diagnostic stable | figure review + summary stats | last200 report | interpretable outputs produced |
| D4 | Historical slices | central-only panels clarify middle behavior | figure review | central plots | central distortion assessed |
| E1 | Post contract | active post runner path identified | log/code trace | runner log + code refs | one active path documented |
| E2 | Post contract | no stale `log_log1p` transform remains in active path | code trace + guard outputs | guard files + code refs | no unexplained extra transform |
| E3 | Post contract | history and forecast builders compared | function trace | code refs | semantic differences explained |
| E4 | Post contract | cache reuse is not contaminating results | cache provenance audit | path and timestamp audit | no silent stale cache problem |
| F1 | Decision gate | root cause class assigned | synthesis memo | decision note | cause class selected |
| F2 | Decision gate | next action justified | decision memo | final memo | relaunch/no-relaunch rule explicit |

## Required Before Any Broader Relaunch
- A1-A5 pass
- B1-B4 pass
- C1-C5 pass
- E1-E4 pass
- F1 pass

## Nice To Have Before Broader Relaunch
- D1-D4 fully documented in manuscript-quality diagnostic form
- F2 written as a short launch/no-launch memo
