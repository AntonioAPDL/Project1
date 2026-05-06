# Publication Representative Replays

This workflow stages one isolated replay row for each publication lineage in the
current Bayesian HE2 table.

## Purpose

The goal is to move from provenance-only verification to executable replay
canaries without touching the original publication campaigns.

Each representative replay:

- uses a dedicated artifact root,
- restricts scope to one cutoff and one model family,
- preserves the publication lineage contract,
- uses the source-run runtime profile rather than assuming the current system `R`,
- and can be built, validated, and launched independently.

## Representative rows

1. `20210123 / N-M-T1`
2. `20210123 / exAL-U-T1`
3. `20210123 / exAL-M-T1`
4. `20221225 / exAL-M-T1`

## Generated bundle

- templates:
  `config/publication_replay_representatives_20260506/`
- runtime roots:
  `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_publication_replay_representatives_20260506/`
- bundle summary:
  [publication_representative_bundle.md](/data/muscat_data/jaguir26/project1_ucsc_phd/reports/publication_replay/publication_representative_bundle.md)

## Scope rules

- NDLM representative:
  `multimodel_v8_ndlm_featurecov_rerun_postfix_20260421`
- Univariate exAL representative:
  `multimodel_v8_univar_featurecov_he2_rerun_20260422`
- Multivariate exAL cf1 representative:
  `multimodel_v8_featurecov_cf1_eps_sweep_20260416`
  with only the selected publication epsilon enabled
- Exact publication override representative:
  `multimodel_v8_exalm_t1_discount_grid_exact_20260424`
  with only `set09` enabled

## Commands

Build the representative bundle templates:

```bash
python3 scripts/build_publication_replay_representative_bundle.py
```

Build and validate all four rows without launch:

```bash
python3 scripts/launch_publication_replay_representatives.py
```

Validation-only pass on already-built templates:

```bash
python3 scripts/validate_publication_replay_representatives.py
```

Launch all four detached after build+validation:

```bash
python3 scripts/launch_publication_replay_representatives.py --launch
```

This now launches each representative directly from its generated config:

- `authoritative_r440` rows use:
  `scripts/run_authoritative_r440_replay.sh`
- other rows use:
  `Rscript --vanilla scripts/unified_run.R --config ...`

Dry-run launch commands only:

```bash
python3 scripts/launch_publication_replay_representatives.py --dry-run
```

Refresh live representative status:

```bash
python3 scripts/refresh_publication_replay_representative_status.py
```

## Operational note

These replays are execution canaries. They are not yet the full publication
refresh. If they complete cleanly and reproduce the expected scores, we can
scale from these four rows to the full publication lineage.
