# Univar Subset Post Failure Note

- run_id: `diag_q02_univar_only_q015099_relfix_20260222_221500`
- stage status: `fit=pass`, `post=fail`
- failure locus: `post/logs/diag_q02_univar_only_q015099_relfix_20260222_221500/run_log.txt`
- signature: `Invalid gamma: -60.8021, Allowed range: (-15.8953, 0.0652434)`

Interpretation:
- This failure is in the post-layer quantile handling contract for a 3-quantile subset (`01,50,99`), not in univariate fit execution.
- The same run produced valid univar fit artifacts for all requested subset quantiles (`q=01/q=50/q=99`).
- A full-quantile univar-only relfix lane (`01,05,10,50,90,95,99`) is used for Q-02 post-pass verification to avoid this subset-only post contract mismatch.
