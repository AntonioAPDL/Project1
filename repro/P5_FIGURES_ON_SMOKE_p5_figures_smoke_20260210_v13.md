# P5 Figures-On Smoke Report

- Config: `config/unified_runs/smoke_p5_post_runscoped_figures.yaml`
- Run overlay: `/tmp/smoke_p5_post_runscoped_figures_p5_figures_smoke_20260210_v13.yaml`
- Run ID: `p5_figures_smoke_20260210_v13`
- Run root: `repro/runs/p5_figures_smoke_20260210_v13`

## Closure Evidence

- Manifest: `repro/runs/p5_figures_smoke_20260210_v13/run_manifest.yaml`
- `finished_at_utc`: `2026-02-11T01:01:34Z`
- Post stage log: `repro/runs/p5_figures_smoke_20260210_v13/post/logs/post_runner.log`
- Post output dir: `repro/runs/p5_figures_smoke_20260210_v13/post/outputs/p5_figures_smoke_20260210_v13`

## Run-Scoped Load Proof

- Root-load grep executed:
  - Pattern: `"/project1_ucsc_phd/(variables_|DISC_variables_)"`
  - Scope: `repro/runs/p5_figures_smoke_20260210_v13/post/logs`
  - Result: **no matches**
- `post_runner.log` explicitly records:
  - `STRICT_RUNSCOPED_POST: TRUE`
  - `RUN_ROOT: /data/muscat_data/jaguir26/project1_ucsc_phd/repro/runs/p5_figures_smoke_20260210_v13`
  - `POST_CACHE_DIR: /data/muscat_data/jaguir26/project1_ucsc_phd/repro/runs/p5_figures_smoke_20260210_v13/post/cache`
  - `DISC_W_RDATA_PATHS`, `UNIV_RDATA_PATHS`, `NDLM_RDATA_PATH` under `repro/runs/p5_figures_smoke_20260210_v13/fit/...`

## Figure Outputs

- PNG count: `2`
- Sample files:
  - `repro/runs/p5_figures_smoke_20260210_v13/post/outputs/p5_figures_smoke_20260210_v13/All_ELBOS_DISC.png`
  - `repro/runs/p5_figures_smoke_20260210_v13/post/outputs/p5_figures_smoke_20260210_v13/SMOKE_OBSERVED_SERIES_DISC.png`

