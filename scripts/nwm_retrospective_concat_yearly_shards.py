#!/usr/bin/env python3
"""Concatenate yearly NWM retrospective shard CSVs into one daily series."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List

import pandas as pd


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Concatenate yearly NWM retrospective shard CSVs.")
    p.add_argument("--input-dir", required=True, help="Directory containing yearly shard CSVs.")
    p.add_argument("--glob", default="*.csv", help="Glob pattern for shard CSVs.")
    p.add_argument("--out-csv", required=True, help="Combined output CSV path.")
    p.add_argument("--out-meta", required=True, help="Metadata JSON path.")
    p.add_argument("--version", default="", help="Optional version label for metadata.")
    p.add_argument("--expected-start", default="", help="Optional expected start date YYYY-MM-DD.")
    p.add_argument("--expected-end", default="", help="Optional expected end date YYYY-MM-DD.")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    input_dir = Path(args.input_dir).resolve()
    out_csv = Path(args.out_csv).resolve()
    out_meta = Path(args.out_meta).resolve()

    paths: List[Path] = sorted(input_dir.glob(args.glob))
    if not paths:
        raise SystemExit(f"No shard CSVs matched {args.glob!r} under {input_dir}")

    frames = []
    for path in paths:
        df = pd.read_csv(path)
        if "date" not in df.columns:
            raise SystemExit(f"Expected 'date' column in {path}")
        df["__source_path"] = str(path)
        frames.append(df)

    combined = pd.concat(frames, ignore_index=True)
    combined["date"] = pd.to_datetime(combined["date"], errors="coerce")
    combined = combined.dropna(subset=["date"]).sort_values(["date", "__source_path"], kind="mergesort")

    duplicate_dates = int(combined.duplicated(subset=["date"], keep="last").sum())
    combined = combined.drop_duplicates(subset=["date"], keep="last").copy()
    combined["date"] = combined["date"].dt.strftime("%Y-%m-%d")

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    out_meta.parent.mkdir(parents=True, exist_ok=True)
    combined.drop(columns=["__source_path"]).to_csv(out_csv, index=False)

    meta = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "input_dir": str(input_dir),
        "glob": args.glob,
        "input_file_count": len(paths),
        "input_files": [str(p) for p in paths],
        "version": args.version,
        "rows_out": int(len(combined)),
        "duplicate_dates_dropped": duplicate_dates,
        "start_date": "" if combined.empty else str(combined["date"].min()),
        "end_date": "" if combined.empty else str(combined["date"].max()),
        "expected_start": args.expected_start,
        "expected_end": args.expected_end,
        "output_csv": str(out_csv),
    }
    out_meta.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    print(f"[OK] wrote {out_csv} rows={len(combined)}")
    print(f"[OK] wrote {out_meta}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
