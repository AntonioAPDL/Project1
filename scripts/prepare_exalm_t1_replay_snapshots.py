#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import shutil
from pathlib import Path


USGS_RECENT_RUNS_ROOT = Path(
    "/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/"
    "multimodel_v8_quantile_featurecov_ndlm_discount_probe_20260422/runs"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare frozen shared-input snapshots for exAL-M-T1 post replays."
    )
    parser.add_argument(
        "--manifest",
        default="repro/manifests/exalm_t1_authoritative_runs_20260505.csv",
        help="CSV manifest listing authoritative source runs.",
    )
    parser.add_argument(
        "--out-root",
        default="repro/frozen_shared_inputs/exalm_t1_authoritative_20260505",
        help="Directory where frozen shared-input snapshots will be written.",
    )
    return parser.parse_args()


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def copy_tree(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def main() -> None:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    manifest_path = (repo_root / args.manifest).resolve()
    out_root = (repo_root / args.out_root).resolve()
    out_root.mkdir(parents=True, exist_ok=True)

    rows = load_rows(manifest_path)
    if not rows:
        raise SystemExit(f"No rows found in manifest: {manifest_path}")

    for row in rows:
        cutoff = row["cutoff_date"]
        compact = cutoff.replace("-", "")
        source_run_dir = Path(row["source_run_root"]).resolve() / row["source_run_id"]
        source_shared = source_run_dir / "inputs" / "shared"
        if not source_shared.is_dir():
            raise SystemExit(f"Missing authoritative shared-input tree: {source_shared}")

        recent_run = (
            USGS_RECENT_RUNS_ROOT
            / f"multimodel_{compact}_v8_quantile_featurecov_ndlm_discount_probe_v1_exdqlm_multivar_keep"
        )
        usgs_src = recent_run / "inputs" / "shared" / "usgs" / "usgs_daily.csv"
        if not usgs_src.exists():
            raise SystemExit(f"Missing cutoff-matched USGS daily snapshot: {usgs_src}")

        snapshot_root = out_root / f"cutoff_date={cutoff}"
        copy_tree(source_shared, snapshot_root)
        (snapshot_root / "inputs").mkdir(parents=True, exist_ok=True)
        shutil.copy2(usgs_src, snapshot_root / "inputs" / "usgs_daily.csv")

        meta = {
            "cutoff_date": cutoff,
            "source_run_id": row["source_run_id"],
            "source_run_root": row["source_run_root"],
            "source_shared_root": str(source_shared),
            "usgs_daily_source": str(usgs_src),
            "expected_mean_crps": float(row["expected_mean_crps"]),
            "compare_bundle": row["compare_bundle"],
        }
        (snapshot_root / "snapshot_source_map.json").write_text(
            json.dumps(meta, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(snapshot_root)


if __name__ == "__main__":
    main()
