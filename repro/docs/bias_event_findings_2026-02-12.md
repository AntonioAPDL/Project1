# Bias Event Findings (2026-02-12 run)

## Scope

Focused event analysis was generated from:

- `repro/bias_runs/bias_20260212_171950/tables/bias_compare.csv`
- Event run output: `repro/bias_event_runs/bias_events_20260212_175338`
- Events analyzed:
  - `2021-01-23`
  - `2021-01-27`
  - `2021-11-12` (sanitized from `c2021-11-12`)
  - `2021-12-10`
  - `2021-12-17`
  - `2021-12-21`
  - `2022-05-10`
  - `2022-12-25`
- Horizons: `h=1`, `h=7`
- Plot y-range fixed to `[-30, 30]` cms.

## Main Findings

1. GloFAS has lower absolute event-day forecast bias in `15/16` event-horizon combinations.
2. NWS/NWM is smaller only at `2021-01-23`, `h=7`.
3. Largest forecast-vs-retro divergence (`|Delta|`) occurs for NWS/NWM at `2021-12-21`, `h=7`:
   - `Delta = -21.828` cms (`forecast bias` much more negative than `retro bias`).
4. The January 27, 2021 event shows a strong regime mismatch for GloFAS at `h=1`:
   - `retro bias = +10.222` vs `forecast bias = -5.627` => `Delta = -15.849`.
5. Mean absolute event-day delta is consistently larger for NWS/NWM than GloFAS:
   - `h=1`: NWS/NWM `3.617` vs GloFAS `2.426`
   - `h=7`: NWS/NWM `6.255` vs GloFAS `1.338`

## Event Highlights

### 2021-11-12

- NWS/NWM diverges strongly from retro at both horizons:
  - `h=1`: `Delta = -9.375`
  - `h=7`: `Delta = -6.608`
- GloFAS remains close to retro:
  - `h=1`: `Delta = -0.164`
  - `h=7`: `Delta = -0.264`

### 2021-12-17 and 2021-12-21 (stress period)

- NWS/NWM shows large negative forecast biases and large `|Delta|`, especially at `h=7`:
  - `2021-12-17`, `h=7`: `Delta = -12.443`
  - `2021-12-21`, `h=7`: `Delta = -21.828`
- GloFAS remains much closer to retro on the same dates:
  - `2021-12-17`, `h=7`: `Delta = -0.450`
  - `2021-12-21`, `h=7`: `Delta = -2.321`

### 2022-05-10 (quiet period)

- Both centers are relatively stable and close to retro.
- Event-day `|Delta|` stays near `0.36–0.41` cms.

### 2022-12-25

- NWS/NWM has materially larger divergence than GloFAS:
  - `h=1`: NWS/NWM `Delta = -2.964` vs GloFAS `+0.211`
  - `h=7`: NWS/NWM `Delta = -3.011` vs GloFAS `+0.204`

## Plot Locations

Per-event panel/scatter plots are in:

- `repro/bias_event_runs/bias_events_20260212_175338/plots/event_YYYY-MM-DD/`

For each event and horizon:

- `panels_all_hXX.png`
- `panels_nws_nwm_hXX.png`
- `panels_glofas_hXX.png`
- `scatter_all_hXX.png`
- `scatter_nws_nwm_hXX.png`
- `scatter_glofas_hXX.png`

## Notes

- This analysis layer is read-only over existing bias outputs and does not alter unified model stages.
- Detailed numeric tables are in:
  - `repro/bias_event_runs/bias_events_20260212_175338/tables/event_summary.json`
  - `repro/bias_event_runs/bias_events_20260212_175338/tables/event_summary.md`
  - `repro/bias_event_runs/bias_events_20260212_175338/event_report.md`
