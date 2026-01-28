# Assets Index (Notebooks + Figures)

## Canonical notebook (source of truth)
- `repro/recovery/Environmetrics_Figures__OLDEST.ipynb`
  - Status: **working** (manual run confirmed)
  - Purpose: produce all paper figures and summaries

## Other notebook snapshots
- `repro/recovery/Environmetrics_Figures__CURRENT.ipynb`
  - Status: contaminated/modified during recovery; **not canonical**
- `repro/recovery/Environmetrics_Figures__RECOVERED_WORKING.ipynb`
  - Status: frozen copy of canonical notebook

## Figure output directories
- `Environmetrics_reproduce/`
  - **Canonical output folder going forward**
  - Produced by the canonical notebook
- `Environmetrics/`
  - Historical/legacy; may be overwritten during past runs
  - Do not treat as canonical

## Manuscript repo gold figures (historical)
- `/data/muscat_data/jaguir26/Environmetrics_paper_repo/DISC/`
  - Historical submitted-paper figures
  - Not used as primary validation going forward

## Compare artifacts
- `repro/gold_DISC_figures.sha256` (historical gold hashes)
- `repro/current_Environmetrics_reproduce.sha256` (current output hashes)
- `repro/compare_report_reproduce.txt` (last comparison report)
- `repro/VALIDATION_STATUS.md`
