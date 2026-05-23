# exDQLM Multivariate Keep Clean All-Cutoff Near-Zero Launch

Date: 2026-05-23

Status: launch package for the clean homogeneous five-cutoff campaign.

## Scope

This package launches a fresh all-cutoff multivariate `exdqlm keep` campaign after the near-zero gamma/sigma repair.
It does not reuse or modify the 2026-05-22 promotion root or any older protected production roots.

Runtime root:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_all_cutoffs_fullhistory_nearzero_20260523`

Tracked launch files:

- `config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_all_cutoffs_fullhistory_nearzero_20260523.template.yaml`
- `config/he2_relaunch_batches/exdqlm_multivar_keep_all_cutoffs_fullhistory_nearzero_20260523.yaml`

## Locked Contract

- cutoffs: `20210123`, `20211112`, `20211221`, `20220511`, `20221225`
- quantiles: `0.05`, `0.20`, `0.35`, `0.50`, `0.65`, `0.80`, `0.95`
- history start: `1987-05-29`
- transform policy: `log1p_only`
- harmonics: indices `[1, 2, 3]`
- transfer covariates: `PPT`, `SOIL`, `PCA`, squares, interaction, and lags 1-3 for PPT/SOIL
- discounts: `df_t=0.99999`, `df_s1=df_s2=df_s67=df_discrep=0.9999`, `lambda=0.97`,
  `df_trans=df_covs=0.9999999`
- forecast Wishart prior: `epsilon=365`, `c_factor=1`
- VB maximum iterations: `100`
- gamma/sigma minimum updates: `50`
- near-zero fallback: `enabled=true`, `mode=sigma_only`, `gamma_anchor=full_candidate`
- queue shape: five cutoff rows concurrently, seven quantile workers per row, one numerical thread per worker
- cleanup: `.RData` files are temporary and removed after post finishes

## Launch Command

```bash
python3 scripts/launch_he2_bayesian_publication_relaunch.py \
  --template config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_all_cutoffs_fullhistory_nearzero_20260523.template.yaml \
  --batch-file config/he2_relaunch_batches/exdqlm_multivar_keep_all_cutoffs_fullhistory_nearzero_20260523.yaml \
  --skip-validate \
  --start-monitor \
  --monitor-out-dir reports/he2_exdqlm_multivar_keep_allcutoffs_fullhistory_nearzero_live_20260523 \
  --monitor-interval 300
```

The monitor writes:

- `reports/he2_exdqlm_multivar_keep_allcutoffs_fullhistory_nearzero_live_20260523/LIVE_STATUS.md`
- `reports/he2_exdqlm_multivar_keep_allcutoffs_fullhistory_nearzero_live_20260523/live_status_latest.csv`
- `reports/he2_exdqlm_multivar_keep_allcutoffs_fullhistory_nearzero_live_20260523/live_status_history.csv`

## Gates

The launch should be considered healthy only if every lane reaches post/report completion with:

- `gamsig_update_iters >= 50`
- pseudo-data failures `0`
- state guard events `0`
- fatal log errors `0`
- finite ELBO, sigma, gamma, and normalized state norm
- verified post-stage `.RData` cleanup
