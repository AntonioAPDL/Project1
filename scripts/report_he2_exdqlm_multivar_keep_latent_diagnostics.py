#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Iterable

import pandas as pd


DIAGNOSTIC_CSVS = [
    "latent_update_summary.csv",
    "latent_update_top_cells.csv",
    "gamsig_source_iteration_summary.csv",
    "pseudodata_iteration_summary.csv",
    "pseudodata_top_cells.csv",
    "pseudodata_guard_events.csv",
]


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Collect exDQLM multivar keep latent/gamsig/pseudodata diagnostics from targeted runs."
    )
    ap.add_argument("--root", action="append", required=True, help="Runtime/report root to scan. May be repeated.")
    ap.add_argument("--out-dir", required=True, help="Directory for concatenated CSVs and README.md.")
    return ap.parse_args()


def find_files(roots: Iterable[Path], name: str) -> list[Path]:
    out: list[Path] = []
    for root in roots:
        if root.exists():
            out.extend(sorted(root.rglob(name)))
    return out


def path_context(path: Path) -> dict[str, str]:
    parts = list(path.parts)
    run_id = ""
    if "runs" in parts:
        idx = parts.index("runs")
        if idx + 1 < len(parts):
            run_id = parts[idx + 1]
    q_label = ""
    for part in parts:
        if re.fullmatch(r"q=\d+", part):
            q_label = part
            break
    cutoff = ""
    spec = ""
    m_cutoff = re.search(r"multimodel_(\d{8})_", run_id)
    if m_cutoff:
        cutoff = m_cutoff.group(1)
    m_spec = re.search(r"_he2grid_([^_]+)_", run_id)
    if m_spec:
        spec = m_spec.group(1)
    return {
        "source_file": str(path),
        "run_id": run_id,
        "cutoff": cutoff,
        "grid_spec_id": spec,
        "q_label": q_label,
    }


def read_csv_with_context(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    ctx = path_context(path)
    for key, value in reversed(list(ctx.items())):
        df.insert(0, key, value)
    return df


def collect_csvs(roots: list[Path], out_dir: Path) -> pd.DataFrame:
    manifest_rows: list[dict[str, str | int]] = []
    for name in DIAGNOSTIC_CSVS:
        files = find_files(roots, name)
        manifest_rows.append({"diagnostic_file": name, "n_files": len(files)})
        if not files:
            continue
        frames = []
        for path in files:
            try:
                frames.append(read_csv_with_context(path))
            except Exception as exc:
                manifest_rows.append({
                    "diagnostic_file": name,
                    "n_files": -1,
                    "error": f"{path}: {exc}",
                })
        if frames:
            pd.concat(frames, ignore_index=True).to_csv(out_dir / name, index=False)
    manifest = pd.DataFrame(manifest_rows)
    manifest.to_csv(out_dir / "diagnostic_file_manifest.csv", index=False)
    return manifest


def parse_sampling_logs(roots: list[Path], out_dir: Path) -> pd.DataFrame:
    files = find_files(roots, "sampling_diagnostics.log")
    rows: list[dict[str, str | float]] = []
    pattern = re.compile(r"^\[(?P<kind>[^\]]+)\]\s+p0=(?P<p0>\S+)\s+phase=(?P<phase>\S+)\s+elapsed=(?P<elapsed>[0-9.]+)s\s+detail=(?P<detail>.*)$")
    for path in files:
        ctx = path_context(path)
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            m = pattern.match(line.strip())
            if not m:
                continue
            row = dict(ctx)
            row.update(m.groupdict())
            row["elapsed"] = float(row["elapsed"])
            rows.append(row)
    out = pd.DataFrame(rows)
    if not out.empty:
        out.to_csv(out_dir / "sampling_diagnostics_events.csv", index=False)
        wall = out[out["kind"].str.contains("walltime", case=False, na=False)].copy()
        if not wall.empty:
            wall.to_csv(out_dir / "sampling_walltime_events.csv", index=False)
    return out


def write_summaries(out_dir: Path) -> dict[str, int]:
    counts: dict[str, int] = {}
    pseudo_path = out_dir / "pseudodata_iteration_summary.csv"
    if pseudo_path.exists():
        pseudo = pd.read_csv(pseudo_path)
        counts["pseudodata_iteration_rows"] = len(pseudo)
        key_cols = [c for c in ["run_id", "q_label", "p0", "iter", "context", "block", "quantity"] if c in pseudo.columns]
        if {"status", "iter"}.issubset(pseudo.columns):
            bad = pseudo[pseudo["status"].astype(str) != "ok"].copy()
            if not bad.empty:
                bad.sort_values(["run_id", "q_label", "iter"], inplace=True)
                first = bad.groupby(["run_id", "q_label"], dropna=False).head(1)
                first.to_csv(out_dir / "first_bad_pseudodata_by_lane.csv", index=False)
        if key_cols:
            extrema = pseudo.groupby([c for c in ["run_id", "q_label", "block", "quantity"] if c in pseudo.columns], dropna=False).agg(
                max_abs=("max_abs", "max") if "max_abs" in pseudo.columns else ("iter", "count"),
                last_iter=("iter", "max") if "iter" in pseudo.columns else ("quantity", "count"),
            ).reset_index()
            extrema.to_csv(out_dir / "pseudodata_extrema_by_lane.csv", index=False)

    latent_path = out_dir / "latent_update_summary.csv"
    if latent_path.exists():
        latent = pd.read_csv(latent_path)
        counts["latent_update_summary_rows"] = len(latent)
        group_cols = [c for c in ["run_id", "q_label", "block", "source_index", "source_name", "quantity"] if c in latent.columns]
        if group_cols and "max_abs" in latent.columns:
            latent.groupby(group_cols, dropna=False).agg(
                max_abs=("max_abs", "max"),
                max_value=("max", "max"),
                min_value=("min", "min"),
                last_iter=("iter", "max"),
            ).reset_index().to_csv(out_dir / "latent_extrema_by_lane_source.csv", index=False)

    gamsig_path = out_dir / "gamsig_source_iteration_summary.csv"
    if gamsig_path.exists():
        gamsig = pd.read_csv(gamsig_path)
        counts["gamsig_source_summary_rows"] = len(gamsig)
        group_cols = [c for c in ["run_id", "q_label", "source_index", "source_name"] if c in gamsig.columns]
        if group_cols:
            gamsig.groupby(group_cols, dropna=False).agg(
                max_gamma=("E_gamma", "max"),
                min_gamma=("E_gamma", "min"),
                max_sigma=("E_sigma", "max"),
                min_invb_inv_sigma=("E_invb_inv_sigma", "min"),
                guard_count=("guard_triggered", "sum"),
                last_iter=("iter", "max"),
            ).reset_index().to_csv(out_dir / "gamsig_extrema_by_lane_source.csv", index=False)
    return counts


def write_readme(out_dir: Path, roots: list[Path], manifest: pd.DataFrame, sampling: pd.DataFrame, counts: dict[str, int]) -> None:
    lines = [
        "# exDQLM Multivar Keep Latent Diagnostic Report",
        "",
        "This report concatenates default-off diagnostic artifacts from targeted q-lane runs.",
        "",
        "## Roots",
        "",
    ]
    lines.extend(f"- `{root}`" for root in roots)
    lines.extend([
        "",
        "## Collected Files",
        "",
        "| file | n_files |",
        "| --- | ---: |",
    ])
    for row in manifest.to_dict(orient="records"):
        if int(row.get("n_files", 0)) >= 0:
            lines.append(f"| `{row['diagnostic_file']}` | {int(row['n_files'])} |")
    lines.extend([
        "",
        "## Derived Tables",
        "",
    ])
    for path in sorted(out_dir.glob("*.csv")):
        lines.append(f"- `{path.name}`")
    lines.extend([
        "",
        "## Row Counts",
        "",
        "| table | rows |",
        "| --- | ---: |",
    ])
    for key, value in sorted(counts.items()):
        lines.append(f"| `{key}` | {value} |")
    if not sampling.empty:
        lines.append(f"| `sampling_diagnostics_events` | {len(sampling)} |")
    lines.extend([
        "",
        "## Interpretation Checklist",
        "",
        "1. Use `first_bad_pseudodata_by_lane.csv` to find the first hard pseudo-data failure.",
        "2. Use `latent_extrema_by_lane_source.csv` to determine whether `E[u_t]`, `E[1/u_t]`, `psi`, or `chi` moved first.",
        "3. Use `gamsig_extrema_by_lane_source.csv` to inspect source-specific gamma/sigma jumps.",
        "4. Use `pseudodata_top_cells.csv` and `latent_update_top_cells.csv` to inspect the exact source/date/member cells.",
        "5. Treat `sampling_walltime_events.csv` separately from fit-stage pseudo-data failures.",
        "",
    ])
    (out_dir / "README.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    roots = [Path(raw).expanduser().resolve() for raw in args.root]
    out_dir = Path(args.out_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = collect_csvs(roots, out_dir)
    sampling = parse_sampling_logs(roots, out_dir)
    counts = write_summaries(out_dir)
    write_readme(out_dir, roots, manifest, sampling, counts)
    print(f"out_dir={out_dir}")
    print(f"roots={len(roots)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
