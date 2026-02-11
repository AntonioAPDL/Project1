# P1 Forecats Snapshot Smoke Report

Date: 2026-02-11  
Config: `config/unified_runs/smoke_p1_forecats_snapshot.yaml`  
RUN_ID: `20260210_173759`  
Run root: `repro/runs/20260210_173759`

## Completion Evidence

- Manifest: `repro/runs/20260210_173759/run_manifest.yaml`
- `finished_at_utc`: `2026-02-11T01:38:04Z`
- Stages executed: `forecats`, `data_prep_shared`

## Shared Input Tree (short)

```text
inputs/shared/parameters/parameters.txt
inputs/shared/retros/retros.csv
inputs/shared/forecasts/nws_forecast.csv
inputs/shared/forecasts/glofas_forecast.csv
inputs/shared/covariates/cov_01_ELI.csv
inputs/shared/covariates/cov_02_ONI.csv
inputs/shared/forecats_bundle/meta.yaml
inputs/shared/forecats_bundle/inputs/retros_daily.csv
inputs/shared/forecats_bundle/inputs/nws_weighted_daily.csv
inputs/shared/forecats_bundle/inputs/glofas_weighted_daily.csv
inputs/shared/forecats_bundle/retros.csv
inputs/shared/forecats_bundle/nws_forecast.csv
inputs/shared/forecats_bundle/glofas_forecast.csv
```

## Manifest Excerpt (paths + hashes)

Extracted from `repro/runs/20260210_173759/run_manifest.yaml`:

```text
role=input_snapshot path=.../inputs/shared/forecats_bundle/meta.yaml sha256=c4bcf182b8e1f87bb106172cce75527125f732039e4f7dc82ab9aa0605eb7ac7
role=input_snapshot path=.../inputs/shared/forecats_bundle/inputs/retros_daily.csv sha256=91a2ca270236bf3e610ecb4c4e45bb498e7743e9399891c1d2d745e9dc2a313a
role=input_snapshot path=.../inputs/shared/forecats_bundle/inputs/nws_weighted_daily.csv sha256=08f29b520ac33d2faaf155ed63a9780f0a39c7e7f4728a01c8407fa98aa77275
role=input_snapshot path=.../inputs/shared/forecats_bundle/inputs/glofas_weighted_daily.csv sha256=4e45479c8f49994f846d19597fc1b972ef3116023cd1923c5710587008a1423c
role=shared_input path=.../inputs/shared/parameters/parameters.txt sha256=053751db21f49dc031ad655d23dc66fe54d0ceb90d83fb80cecd7d0c6ef4fb95
role=shared_input path=.../inputs/shared/retros/retros.csv sha256=91a2ca270236bf3e610ecb4c4e45bb498e7743e9399891c1d2d745e9dc2a313a
role=shared_input path=.../inputs/shared/forecasts/nws_forecast.csv sha256=08f29b520ac33d2faaf155ed63a9780f0a39c7e7f4728a01c8407fa98aa77275
role=shared_input path=.../inputs/shared/forecasts/glofas_forecast.csv sha256=4e45479c8f49994f846d19597fc1b972ef3116023cd1923c5710587008a1423c
role=shared_input path=.../inputs/shared/covariates/cov_01_ELI.csv sha256=b70f2a04d50b3d6902e916dbfeaa5bfcdabf5f60562942a0ff2e2c6e9e83bd04
role=shared_input path=.../inputs/shared/covariates/cov_02_ONI.csv sha256=7a615fa1dc9a2b5f1f55633b14be1db92eee12d67f2b67ba3c68dc5fc33338aa
```

## Notes

- Snapshot source used `inputs.forecats.mode=use_existing`.
- Canonical shared forecasts were sourced from snapshot aliases because `inputs.shared.prefer_forecats_snapshot=true`.
- No fit/post stages were run in this smoke.
