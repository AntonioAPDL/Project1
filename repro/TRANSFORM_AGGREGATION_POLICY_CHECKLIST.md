# Transform/Aggregation Policy Checklist (NWS/NWM + GloFAS)

## 1) Scope
This document defines the canonical transformation/aggregation policy for:
- Forecast preprocessing (`NWS`, `GloFAS`).
- Retrospective/historical point extraction when sub-daily data are reduced to daily.
- Synthetic NWS retrospective construction from forecast ensembles.

All raw flow units are **cms** (`m^3/s`).

## 2) Canonical Definitions
Let raw flow be `x >= 0` in cms.

Working transform `T_s(x)` depends on scale `s`:
- `raw_cms`: `T(x) = x`
- `log1p_cms`: `T(x) = log(1 + x)`
- `log_log1p_cms`: `T(x) = log(log(1 + x_safe))`, with `x_safe = max(x, eps)` for non-positive values (`eps = 1e-6 cms`)

Inverse `T_s^{-1}(y)`:
- `raw_cms`: `x = y`
- `log1p_cms`: `x = exp(y) - 1`
- `log_log1p_cms`: `x = exp(exp(y)) - 1`

### Daily aggregation rule (mandatory)
For sub-daily values `{x_t,h}` in day `t`:
1. transform each sub-daily value: `z_t,h = T_s(x_t,h)`
2. aggregate in transform space: `z_t = mean_h(z_t,h)`
3. store/report daily cms as: `x_t^* = T_s^{-1}(z_t)`

### Ensemble aggregation rule (mandatory)
For ensemble members `{x_t,h,j}` (and optional forecast weights `w_i` over contributing forecasts):
1. transform each raw value first
2. do weighted/ensemble averaging in transform space
3. invert once at the end to cms

No pipeline path should compute `T(mean(x))` when `x` are sub-daily/member values.

## 3) Synthetic NWS Retrospective Rule
Synthetic retrospective is built from `results.pkl` forecasts by:
1. selecting latest issue per `(target_date, target_hour, ensemble)`
2. optional strict one-step filter (`lead_time_h == 1`)
3. averaging in transform space
4. inverting to cms

## 4) Implementation Checklist
Status legend: `[x]=implemented`, `[ ]=pending`.

- `[x]` Shared transform utility created: `scripts/flow_scale.py`
- `[x]` Batch NWS extraction uses configurable transform-space aggregation:
  `scripts/forecats_extract_nws_batch.py`
- `[x]` Single-cutoff NWS builder uses same policy:
  `scripts/forecats_build_nws_weighted.py`
- `[x]` Single-cutoff GloFAS weighted builder uses same policy:
  `scripts/forecats_build_glofas_weighted.py`
- `[x]` Synthetic NWS retrospective supports transform-space aggregation and strict one-step mode:
  `scripts/nwm_build_synthetic_retrospective_from_results.py`
- `[x]` NWM Zarr point extraction applies transform-first daily aggregation:
  `scripts/nwm_retrospective_extract_point_zarr.py`
- `[x]` NWM v1.2 `.comp` point extraction applies transform-first daily aggregation:
  `scripts/nwm_retrospective_extract_point_v12_comp.py`
- `[x]` Batch R driver passes internal aggregation scale to NWS forecast extraction and records it in metadata:
  `scripts/forecats_batch.R`
- `[x]` Single-run R pipeline passes internal aggregation scale to forecast builders and records it in metadata:
  `scripts/forecats_pipeline.R`
- `[x]` Batch helper conversion supports `log_log1p_cms` for retrospective input decoding:
  `scripts/run_forecats_batch_all.sh`
- `[x]` Active batch configs now declare internal aggregation scale:
  `config/forecats_batch.site=11160500.default.yaml`,
  `config/forecats_batch.site=11160500.nws_reextract_only.yaml`,
  `config/forecats_batch.site=11160500.nws_multiretro_compare.yaml`

## 5) Verification Checklist (run after rebuild)
- `[ ]` Rebuild forecast caches for target run_id and confirm metadata field:
  `processing.weighting_scale_internal` equals intended scale.
- `[ ]` Rebuild synthetic NWS retrospective with chosen scale and (if requested) strict one-step.
- `[ ]` Rebuild NWM retrospective point-series daily outputs (v2.0/v2.1/v3.0/v1.2) with same aggregation scale.
- `[ ]` Confirm no NA gaps inside each stated coverage window.
- `[ ]` Regenerate figures and confirm consistent behavior (forecasts vs synthetic retrospective).

## 6) Notes
- Existing previously generated CSVs/figures may reflect older `log1p`-internal runs.
- To enforce full consistency, historical outputs should be regenerated from source using the selected scale.
