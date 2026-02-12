#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from cleanup_policy import write_inventory


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate machine-readable inventory for repro runs")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--output-csv", type=Path, default=None)
    parser.add_argument("--output-json", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    csv_path = (args.output_csv or (repo_root / "repro" / "run_inventory.csv")).resolve()
    json_path = (args.output_json or (repo_root / "repro" / "run_inventory.json")).resolve()

    out_csv, out_json = write_inventory(repo_root=repo_root, csv_path=csv_path, json_path=json_path)
    print(f"inventory_csv={out_csv}")
    print(f"inventory_json={out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
