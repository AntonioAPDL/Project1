#!/usr/bin/env python3
"""Write a durable checkpoint snapshot for the current recovery run."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.recovery_priority_lib import DEFAULT_RECOVERY_RUN_ROOT, snapshot_priority_status


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Freeze the current recovery checkpoint into a documented bundle.")
    parser.add_argument("--recovery-run-root", type=Path, default=DEFAULT_RECOVERY_RUN_ROOT)
    parser.add_argument("--out-dir", type=Path, default=None, help="Optional explicit checkpoint output directory.")
    return parser.parse_args()


def render_markdown(snapshot: dict, recovery_run_root: Path) -> str:
    lanes = snapshot["lanes"]
    return "\n".join(
        [
            "# Recovery Checkpoint",
            "",
            f"- generated_utc: `{datetime.now(timezone.utc).isoformat()}`",
            f"- recovery_run_root: `{recovery_run_root}`",
            f"- host: `{snapshot['resource']['host']}`",
            "",
            "## Lane Snapshot",
            "",
            "| lane | completed | expected | percent | note |",
            "|---|---:|---:|---:|---|",
            f"| `glofas_historical_v31` | {lanes['glofas_historical_v31']['completed']} | {lanes['glofas_historical_v31']['expected']} | {lanes['glofas_historical_v31']['percent_complete']:.1f}% | priority lane 1 |",
            f"| `glofas_operational` | {lanes['glofas_operational']['completed']} | {lanes['glofas_operational']['expected']} | {lanes['glofas_operational']['percent_complete']:.1f}% | priority lane 2 |",
            f"| `nwm_retrospective_v12` | {lanes['nwm_retrospective_v12']['completed']} | {lanes['nwm_retrospective_v12']['expected']} | {lanes['nwm_retrospective_v12']['percent_complete']:.1f}% | priority lane 3 |",
            f"| `glofas_historical_v40` | {lanes['glofas_historical_v40']['completed']} | {lanes['glofas_historical_v40']['expected']} | {lanes['glofas_historical_v40']['percent_complete']:.1f}% | priority lane 4 |",
            "",
            "## Resume Notes",
            "",
            "- Finished outputs already on disk will be reused on relaunch.",
            "- `NWM v1.2` resumes at the yearly shard level; active in-flight years would restart from the start of those years.",
            "- `GLOFAS historical` resumes from existing non-empty monthly zip shards.",
            "- `GLOFAS operational` resumes from existing non-empty per-issue GRIB outputs.",
            "",
            "## Active Targets",
            "",
            f"- tmux_sessions: `{', '.join(snapshot['target_tmux_sessions']) if snapshot['target_tmux_sessions'] else '(none)'}`",
            f"- v31_refill_pids: `{', '.join(str(pid) for pid in snapshot['target_v31_refill_pids']) if snapshot['target_v31_refill_pids'] else '(none)'}`",
            "",
            "## Resource Snapshot",
            "",
            f"- uptime: `{snapshot['resource']['uptime']}`",
            f"- memory: `{snapshot['resource']['memory']}`",
            f"- data_disk: `{snapshot['resource']['data_disk']}`",
            f"- user_processes: `{snapshot['resource']['user_processes']}`",
            "",
        ]
    ) + "\n"


def main() -> int:
    args = parse_args()
    recovery_run_root = args.recovery_run_root.expanduser().resolve()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = args.out_dir or (recovery_run_root / "status" / f"checkpoint_{timestamp}")
    out_dir.mkdir(parents=True, exist_ok=True)

    snapshot = snapshot_priority_status(recovery_run_root)
    snapshot["generated_utc"] = datetime.now(timezone.utc).isoformat()
    snapshot["recovery_run_root"] = str(recovery_run_root)

    json_path = out_dir / "checkpoint_summary.json"
    md_path = out_dir / "checkpoint_summary.md"
    sessions_path = out_dir / "target_tmux_sessions.txt"
    pids_path = out_dir / "target_v31_refill_pids.txt"

    json_path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(snapshot, recovery_run_root), encoding="utf-8")
    sessions_path.write_text("\n".join(snapshot["target_tmux_sessions"]) + ("\n" if snapshot["target_tmux_sessions"] else ""), encoding="utf-8")
    pids_path.write_text(
        "\n".join(str(pid) for pid in snapshot["target_v31_refill_pids"])
        + ("\n" if snapshot["target_v31_refill_pids"] else ""),
        encoding="utf-8",
    )

    print(json.dumps({"ok": True, "out_dir": str(out_dir), "json": str(json_path), "markdown": str(md_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
