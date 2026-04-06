#!/usr/bin/env python3
"""Initialize a run-scoped external recovery layout for site 11160500.

This helper does not download data. It creates a resumable runtime directory
tree, records repo/git context, inventories known surviving artifacts, and
writes a shell env file that later commands can source.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

try:
    import yaml
except Exception as exc:  # pragma: no cover
    yaml = None
    YAML_IMPORT_ERROR = exc
else:
    YAML_IMPORT_ERROR = None


DEFAULT_CONFIG = "config/recovery_site11160500.yaml"
FAMILY_SUBDIRS = [
    "manifests",
    "logs",
    "outputs",
    "smoke",
    "health_checks",
    "audits",
    "provenance",
]
GLOBAL_SUBDIRS = ["commands", "logs", "manifests", "provenance", "status"]


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Initialize a run-scoped external recovery layout.")
    parser.add_argument("--config", default=DEFAULT_CONFIG, help="Recovery YAML config path.")
    parser.add_argument("--run-id", default="", help="Optional fixed run id.")
    parser.add_argument("--runtime-root", default="", help="Optional override for runtime root.")
    parser.add_argument(
        "--reuse-existing",
        action="store_true",
        help="Reuse an existing run directory instead of failing if it already exists.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the planned run root and artifact inventory without creating anything.",
    )
    return parser.parse_args()


def load_config(path: Path) -> Dict[str, Any]:
    if yaml is None:  # pragma: no cover
        raise RuntimeError(f"PyYAML import failed: {YAML_IMPORT_ERROR}")
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise SystemExit(f"Expected mapping at config root: {path}")
    return payload


def run_git(repo_root: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return ""
    return (proc.stdout or "").strip()


def git_context(repo_root: Path) -> Dict[str, Any]:
    status = run_git(repo_root, "status", "--short", "--branch")
    dirty = bool(run_git(repo_root, "status", "--porcelain"))
    return {
        "branch": run_git(repo_root, "rev-parse", "--abbrev-ref", "HEAD"),
        "commit": run_git(repo_root, "rev-parse", "HEAD"),
        "status_short": status,
        "dirty": dirty,
    }


def env_key(name: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "_", name.upper()).strip("_")


def inventory_rows(items: Iterable[Dict[str, Any]]) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    for item in items:
        path = Path(str(item.get("path", ""))).expanduser()
        exists = path.exists()
        is_dir = path.is_dir() if exists else False
        size_bytes = path.stat().st_size if exists and path.is_file() else 0
        rows.append(
            {
                "id": str(item.get("id", "")),
                "family": str(item.get("family", "")),
                "role": str(item.get("role", "")),
                "path": str(path),
                "exists": "YES" if exists else "NO",
                "is_dir": "YES" if is_dir else "NO",
                "size_bytes": str(size_bytes),
                "notes": str(item.get("notes", "")),
            }
        )
    return rows


def write_csv(path: Path, rows: List[Dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = ["id", "family", "role", "path", "exists", "is_dir", "size_bytes", "notes"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def write_env(path: Path, run_root: Path, family_roots: Dict[str, Path], config_path: Path) -> None:
    lines = [
        "#!/usr/bin/env bash",
        f'export RECOVERY_CONFIG_PATH="{config_path}"',
        f'export RECOVERY_RUN_ROOT="{run_root}"',
        f'export RECOVERY_COMMAND_DIR="{run_root / "commands"}"',
        f'export RECOVERY_LOG_DIR="{run_root / "logs"}"',
        f'export RECOVERY_MANIFEST_DIR="{run_root / "manifests"}"',
        f'export RECOVERY_STATUS_DIR="{run_root / "status"}"',
        f'export RECOVERY_PROVENANCE_DIR="{run_root / "provenance"}"',
    ]
    for family_id, family_root in sorted(family_roots.items()):
        key = env_key(f"RECOVERY_FAMILY_{family_id}_ROOT")
        lines.append(f'export {key}="{family_root}"')
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    config_path = Path(args.config).resolve()
    cfg = load_config(config_path)

    site = cfg.get("site") or {}
    runtime = cfg.get("runtime") or {}
    families = list(cfg.get("families") or [])
    bootstrap = list(cfg.get("bootstrap_artifacts") or [])

    site_id = str(site.get("usgs_site", "11160500"))
    runtime_root = Path(args.runtime_root or runtime.get("root") or "").expanduser().resolve()
    if not str(runtime_root):
        raise SystemExit("Runtime root is required via config.runtime.root or --runtime-root.")
    campaign_slug = str(runtime.get("campaign_slug", "data_recovery"))
    run_prefix = str(runtime.get("run_prefix", f"site{site_id}_recovery"))
    run_id = args.run_id or f"{run_prefix}_{now_utc()}"
    run_root = runtime_root / campaign_slug / f"site={site_id}" / f"recovery_run={run_id}"

    family_roots = {
        str(family.get("id")): run_root / f"family={family.get('id')}"
        for family in families
        if family.get("id")
    }

    inventory = inventory_rows(bootstrap)

    if args.dry_run:
        payload = {
            "config_path": str(config_path),
            "run_root": str(run_root),
            "family_roots": {k: str(v) for k, v in family_roots.items()},
            "bootstrap_inventory": inventory,
        }
        print(json.dumps(payload, indent=2))
        return 0

    if run_root.exists() and any(run_root.iterdir()) and not args.reuse_existing:
        raise SystemExit(
            f"Run root already exists and is non-empty: {run_root}\n"
            "Use --reuse-existing to refresh manifests in place or choose a different --run-id."
        )

    for subdir in GLOBAL_SUBDIRS:
        (run_root / subdir).mkdir(parents=True, exist_ok=True)
    for family_root in family_roots.values():
        for subdir in FAMILY_SUBDIRS:
            (family_root / subdir).mkdir(parents=True, exist_ok=True)

    bootstrap_csv = run_root / "provenance" / "bootstrap_artifacts_inventory.csv"
    write_csv(bootstrap_csv, inventory)

    env_path = run_root / "commands" / "paths.sh"
    write_env(env_path, run_root, family_roots, config_path)

    manifest = {
        "run_id": run_id,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "config_path": str(config_path),
        "project_root": str(repo_root),
        "run_root": str(run_root),
        "site": {
            "usgs_site": site_id,
            "name": str(site.get("name", "")),
            "lat": float(site.get("lat", 37.0443931)),
            "lon": float(site.get("lon", -122.072464)),
        },
        "git": git_context(repo_root),
        "source_docs": list(cfg.get("source_docs") or []),
        "source_scripts": list(cfg.get("source_scripts") or []),
        "family_roots": {k: str(v) for k, v in family_roots.items()},
        "bootstrap_artifacts_csv": str(bootstrap_csv),
    }
    manifest_path = run_root / "manifests" / "run_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    readme_path = run_root / "status" / "README.txt"
    readme_path.write_text(
        "\n".join(
            [
                f"Recovery run: {run_id}",
                f"Run root: {run_root}",
                f"Bootstrap artifact inventory: {bootstrap_csv}",
                f"Environment file: {env_path}",
                "",
                "This run root is metadata-only until family workflows are executed.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"[OK] initialized recovery run: {run_root}")
    print(f"[OK] wrote {manifest_path}")
    print(f"[OK] wrote {bootstrap_csv}")
    print(f"[OK] wrote {env_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
