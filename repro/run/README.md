# Environmetrics Figures Runner (Recovered Notebook)

## How to run
```bash
Rscript repro/run/Environmetrics_Figures_run.R
```

## Output directory
- Figures will be written to:
  `Environmetrics_reproduce_script/`

## Flags (edit at top of the script)
- `SKIP_UNIVARIATE`: defaults to TRUE. Keep TRUE if the univariate block is unstable.
- `OUTPUT_DIR`: change if you want a different output folder.

## What this does NOT do
- No refactor or re-organization of the repo
- No modification of the original notebook
- No automatic comparisons to gold DISC (use compare tool separately)

## Logging
- Run log: `repro/run/run_log.txt`
