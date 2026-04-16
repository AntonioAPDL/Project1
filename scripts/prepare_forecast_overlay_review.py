#!/usr/bin/env python3
"""Restore retrospective overlay inputs and render forecast-vs-retrospective review plots.

This workflow is meant to support the blended-forecast design review:
1. Validate the deterministic forecast handoff is complete and healthy.
2. Restore/validate the retrospective PRISM and ERA5 covariate CSVs.
3. Render exact cutoff-window comparison plots for all requested cutoffs.
4. Write a compact machine-readable summary with provenance and output paths.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import subprocess
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import yaml


@dataclass
class SeriesSpec:
    name: str
    canonical_csv: Path
    reuse_source_csv: Path
    value_column: str
    min_required_date: date


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Prepare retrospective overlays and render forecast review plots.")
    ap.add_argument(
        "--config",
        default="config/forecast_overlay_review.site11160500.yaml",
        help="Path to YAML configuration.",
    )
    ap.add_argument(
        "--force-restage",
        action="store_true",
        help="Always copy retrospective source CSVs into their canonical paths even if valid copies already exist.",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate configuration and print the planned actions without copying or plotting.",
    )
    return ap.parse_args()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"Config must be a mapping: {path}")
    return data


def parse_iso_date(raw: str) -> date:
    return pd.Timestamp(raw).date()


def validate_handoff(expected_handoff_root: Path) -> Dict[str, Any]:
    meta_path = expected_handoff_root / "handoff_meta.json"
    if not meta_path.exists():
        raise FileNotFoundError(f"handoff_meta.json not found: {meta_path}")
    meta = json.loads(meta_path.read_text())
    if not meta.get("health_pass", False):
        raise RuntimeError(f"Handoff root is not healthy yet: {expected_handoff_root}")
    return meta


def read_series_csv(path: Path, value_column: str) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    df = pd.read_csv(path)
    date_col = "Date" if "Date" in df.columns else ("time" if "time" in df.columns else None)
    if date_col is None:
        raise ValueError(f"Missing Date/time column in {path}")
    if value_column not in df.columns:
        raise ValueError(f"Missing expected value column {value_column} in {path}")
    out = df[[date_col, value_column]].copy()
    out[date_col] = pd.to_datetime(out[date_col], errors="coerce")
    out[value_column] = pd.to_numeric(out[value_column], errors="coerce")
    out = out.dropna(subset=[date_col, value_column]).sort_values(date_col)
    if out.empty:
        raise ValueError(f"No valid rows in {path}")
    out = out.drop_duplicates(subset=[date_col], keep="last")
    out = out.rename(columns={date_col: "Date"})
    return out


def validate_series(path: Path, value_column: str, min_required_date: date) -> Dict[str, Any]:
    df = read_series_csv(path, value_column=value_column)
    min_date = df["Date"].iloc[0].date()
    max_date = df["Date"].iloc[-1].date()
    if max_date < min_required_date:
        raise RuntimeError(
            f"Series {path} ends at {max_date.isoformat()}, before required {min_required_date.isoformat()}"
        )
    return {
        "path": str(path),
        "rows": int(len(df)),
        "min_date": min_date.isoformat(),
        "max_date": max_date.isoformat(),
        "value_column": value_column,
        "sha256": sha256_file(path),
    }


def maybe_stage_series(spec: SeriesSpec, force_restage: bool, dry_run: bool) -> Dict[str, Any]:
    source_meta = validate_series(spec.reuse_source_csv, spec.value_column, spec.min_required_date)
    canonical_ok = False
    canonical_meta: Dict[str, Any] | None = None
    if spec.canonical_csv.exists():
        try:
            canonical_meta = validate_series(spec.canonical_csv, spec.value_column, spec.min_required_date)
            canonical_ok = True
        except Exception:
            canonical_ok = False

    copied = False
    if force_restage or not canonical_ok:
        if not dry_run:
            spec.canonical_csv.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(spec.reuse_source_csv, spec.canonical_csv)
        copied = True

    if not dry_run:
        canonical_meta = validate_series(spec.canonical_csv, spec.value_column, spec.min_required_date)

    return {
        "name": spec.name,
        "copied": copied,
        "force_restage": force_restage,
        "dry_run": dry_run,
        "source": source_meta,
        "canonical": canonical_meta if canonical_meta is not None else {
            "path": str(spec.canonical_csv),
            "value_column": spec.value_column,
        },
    }


def run_cmd(cmd: List[str], cwd: Path, dry_run: bool) -> Dict[str, Any]:
    if dry_run:
        return {"command": cmd, "status": "planned", "returncode": None}
    proc = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            "Command failed\n"
            f"cwd={cwd}\n"
            f"cmd={' '.join(cmd)}\n"
            f"stdout=\n{proc.stdout}\n"
            f"stderr=\n{proc.stderr}"
        )
    return {
        "command": cmd,
        "status": "ran",
        "returncode": proc.returncode,
        "stdout_tail": proc.stdout.strip().splitlines()[-10:],
    }


def write_csv(path: Path, rows: List[Dict[str, Any]], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    cfg_path = Path(args.config).resolve()
    cfg = load_yaml(cfg_path)

    review_cfg = cfg["review"]
    plots_cfg = cfg["plots"]
    retro_cfg = cfg["retrospective"]

    manifest_run_dir = Path(review_cfg["manifest_run_dir"]).resolve()
    expected_handoff_root = Path(review_cfg["expected_handoff_root"]).resolve()
    site_config = Path(review_cfg["site_config"]).resolve()
    detclim_config_path = Path(review_cfg["detclim_config_path"]).resolve()
    cutoffs = [str(x) for x in review_cfg["cutoffs"]]
    max_days = int(review_cfg["max_days"])
    review_id = str(review_cfg["review_id"])
    required_end_date = max(parse_iso_date(cutoff) for cutoff in cutoffs) + timedelta(days=max_days)

    handoff_meta = validate_handoff(expected_handoff_root)

    series_specs = [
        SeriesSpec(
            name="prism",
            canonical_csv=Path(retro_cfg["prism"]["canonical_csv"]).resolve(),
            reuse_source_csv=Path(retro_cfg["prism"]["reuse_source_csv"]).resolve(),
            value_column=str(retro_cfg["prism"]["value_column"]),
            min_required_date=parse_iso_date(str(retro_cfg["prism"]["min_required_date"])),
        ),
        SeriesSpec(
            name="era5_soil",
            canonical_csv=Path(retro_cfg["era5_soil"]["canonical_csv"]).resolve(),
            reuse_source_csv=Path(retro_cfg["era5_soil"]["reuse_source_csv"]).resolve(),
            value_column=str(retro_cfg["era5_soil"]["value_column"]),
            min_required_date=parse_iso_date(str(retro_cfg["era5_soil"]["min_required_date"])),
        ),
    ]

    prep_root = manifest_run_dir / "review_prep" / review_id
    prep_root.mkdir(parents=True, exist_ok=True)

    stage_rows = []
    for spec in series_specs:
        stage_rows.append(maybe_stage_series(spec, force_restage=args.force_restage, dry_run=args.dry_run))

    status_cmd = [
        "python3",
        str(repo_root / "scripts" / "write_climate_series_status.py"),
        "--root-dir",
        str(repo_root),
        "--target-date",
        required_end_date.isoformat(),
        "--output-csv",
        str(prep_root / "climate_series_status.csv"),
    ]
    status_result = run_cmd(status_cmd, cwd=repo_root, dry_run=args.dry_run)

    plot_runs = []
    for cutoff in cutoffs:
        for style in plots_cfg["styles"]:
            cmd = [
                "Rscript",
                str(repo_root / "scripts" / "plot_gefs_nwm_forecast_cutoff.R"),
                "--manifest-run-dir",
                str(manifest_run_dir),
                "--site-config",
                str(site_config),
                "--cutoff-date",
                cutoff,
                "--detclim-config",
                str(detclim_config_path),
                "--plot-style",
                style,
                "--max-days",
                str(max_days),
                "--prism-csv",
                str(series_specs[0].canonical_csv),
                "--era5-soil-csv",
                str(series_specs[1].canonical_csv),
            ]
            if plots_cfg.get("overlay_covariates", False):
                cmd.append("--overlay-covariates")
            result = run_cmd(cmd, cwd=repo_root, dry_run=args.dry_run)
            out_root = manifest_run_dir / "plots" / f"cutoff_date={cutoff}"
            plot_runs.append(
                {
                    "cutoff": cutoff,
                    "plot_style": style,
                    "status": result["status"],
                    "command": result["command"],
                    "stdout_tail": result.get("stdout_tail", []),
                    "output_dir": str(out_root),
                }
            )

    summary = {
        "created_utc": datetime.utcnow().isoformat() + "Z",
        "config_path": str(cfg_path),
        "review_id": review_id,
        "dry_run": args.dry_run,
        "manifest_run_dir": str(manifest_run_dir),
        "expected_handoff_root": str(expected_handoff_root),
        "detclim_config_path": str(detclim_config_path),
        "handoff_health_pass": bool(handoff_meta.get("health_pass", False)),
        "cutoffs": cutoffs,
        "max_days": max_days,
        "required_review_end_date": required_end_date.isoformat(),
        "retrospective_stage": stage_rows,
        "status_csv": str(prep_root / "climate_series_status.csv"),
        "status_result": status_result,
        "plot_runs": plot_runs,
    }
    summary_path = prep_root / "forecast_overlay_review_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2))

    plot_index_rows = []
    for item in plot_runs:
        cutoff = item["cutoff"]
        style = item["plot_style"]
        out_root = Path(item["output_dir"])
        plot_index_rows.append(
            {
                "cutoff": cutoff,
                "plot_style": style,
                "output_dir": str(out_root),
                "summary_json": str(
                    out_root / (
                        "plot_summary_mean_same_units_with_covariates.json"
                        if style == "mean_only_same_units"
                        else "plot_summary_mean_same_units_bias_quantiles_with_covariates.json"
                    )
                ),
            }
        )
    write_csv(
        prep_root / "plot_index.csv",
        plot_index_rows,
        fieldnames=["cutoff", "plot_style", "output_dir", "summary_json"],
    )

    print(f"[OK] review summary: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
