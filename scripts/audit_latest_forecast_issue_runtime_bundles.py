#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BUNDLE_ROOT = (
    ROOT.parent
    / "project1_ucsc_phd_runtime"
    / "multimodel_v8_he2_publication_shared_inputs_20260510"
    / "stable_inputs"
    / "site=11160500"
)
DEFAULT_CUTOFFS = ["2021-01-23", "2021-11-12", "2021-12-21", "2022-05-11", "2022-12-25"]


@dataclass(frozen=True)
class AliasCheck:
    cutoff: str
    source: str
    alias_path: str
    canonical_path: str
    alias_sha256: str
    canonical_sha256: str
    status: str
    detail: str


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def find_bundle_dir(bundle_root: Path, cutoff: str) -> Path | None:
    root = bundle_root / f"cutoff_date={cutoff}"
    matches = sorted(root.glob("run_id=*"))
    return matches[0] if matches else None


def check_alias(bundle_dir: Path, cutoff: str, source: str, alias_rel: str, canonical_rel: str) -> AliasCheck:
    alias = bundle_dir / alias_rel
    canonical = bundle_dir / canonical_rel
    if not alias.exists() or not canonical.exists():
        return AliasCheck(
            cutoff=cutoff,
            source=source,
            alias_path=str(alias),
            canonical_path=str(canonical),
            alias_sha256="",
            canonical_sha256="",
            status="fail",
            detail="missing alias or canonical member file",
        )
    alias_sha = sha256_file(alias)
    canonical_sha = sha256_file(canonical)
    return AliasCheck(
        cutoff=cutoff,
        source=source,
        alias_path=str(alias),
        canonical_path=str(canonical),
        alias_sha256=alias_sha,
        canonical_sha256=canonical_sha,
        status="pass" if alias_sha == canonical_sha else "fail",
        detail="byte-identical" if alias_sha == canonical_sha else "sha256 mismatch",
    )


def audit(bundle_root: Path, cutoffs: Iterable[str]) -> list[AliasCheck]:
    rows: list[AliasCheck] = []
    for cutoff in cutoffs:
        bundle_dir = find_bundle_dir(bundle_root, cutoff)
        if bundle_dir is None:
            for source in ["nws", "glofas"]:
                rows.append(
                    AliasCheck(
                        cutoff=cutoff,
                        source=source,
                        alias_path=str(bundle_root / f"cutoff_date={cutoff}"),
                        canonical_path="",
                        alias_sha256="",
                        canonical_sha256="",
                        status="fail",
                        detail="missing cutoff bundle",
                    )
                )
            continue
        rows.append(check_alias(bundle_dir, cutoff, "nws", "inputs/nws_weighted_daily.csv", "inputs/nws_members.csv"))
        rows.append(check_alias(bundle_dir, cutoff, "glofas", "inputs/glofas_weighted_daily.csv", "inputs/glofas_members.csv"))
    return rows


def write_csv(path: Path, rows: list[AliasCheck]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "cutoff",
        "source",
        "alias_path",
        "canonical_path",
        "alias_sha256",
        "canonical_sha256",
        "status",
        "detail",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row.__dict__)


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit latest-only forecast bundle alias files.")
    parser.add_argument("--bundle-root", type=Path, default=DEFAULT_BUNDLE_ROOT)
    parser.add_argument("--cutoffs", nargs="*", default=DEFAULT_CUTOFFS)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "reports/latest_forecast_issue_runtime_bundle_audit")
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    rows = audit(args.bundle_root.resolve(), args.cutoffs)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(args.output_dir / "latest_forecast_issue_alias_audit.csv", rows)
    summary = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "bundle_root": str(args.bundle_root.resolve()),
        "cutoffs": list(args.cutoffs),
        "checks": len(rows),
        "failed_checks": sum(1 for row in rows if row.status != "pass"),
        "status": "pass" if all(row.status == "pass" for row in rows) else "fail",
    }
    (args.output_dir / "latest_forecast_issue_alias_audit_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
