# Stage 4 performance artifacts (local)

This folder is used by Stage 4 timing/profiling harnesses.

Tracked:
- `README.md` (this file)
- `.gitignore` (keeps generated artifacts out of git)

Generated locally (ignored):
- Timestamped run directories: `repro/perf/<ts>_p0_<p0>_seed_<seed>/`
- Profiling output: `repro/perf/Rprof.out` (when `DISC_RPROF=1`)

Run the timing harness:
```bash
bash repro/run_stage4_timing.sh 0.5 777
```
