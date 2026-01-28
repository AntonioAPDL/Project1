# Light Modularization Plan (Design Only)

## Proposed layout (future)
```
R/environmetrics/
  00_config.R
  01_data.R
  02_models.R
  03_fit.R
  04_figures.R
  utils_plot.R
  utils_io.R
```

## Notebook section → module mapping (proposal)
- Config + globals → `00_config.R`
- Data loading, merges, standardization → `01_data.R`
- Model setup (Kalman/DLM structures, priors) → `02_models.R`
- Fitting / sampling logic → `03_fit.R`
- Plot construction and ggsave calls → `04_figures.R`

## Safe refactors (later, after equivalence proven)
- Centralized path handling (one config file)
- Shared plotting helpers (theme, save wrapper)
- Repeated data prep steps into pure functions

## Do not touch yet
- Univariate block (keep behind SKIP_UNIVARIATE)
- Any code path requiring large .RData/.rds writes
- Any logic that changes random seeds or sampling order
