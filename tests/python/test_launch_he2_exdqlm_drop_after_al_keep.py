from __future__ import annotations

import csv
import os
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
os.sys.path.insert(0, str(ROOT / "scripts"))

from launch_he2_exdqlm_drop_after_al_keep import DEFAULT_DROP_ARTIFACT_ROOT, DEFAULT_SESSION, handoff_once, matrix_dir  # noqa: E402


def write_matrix_status(artifact_root: Path, rows: list[dict[str, str]]) -> None:
    path = matrix_dir(artifact_root) / "matrix_status.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["cutoff", "epsilon", "lane", "run_id", "phase", "status", "started_at", "finished_at", "manifest_path", "latest_log_mtime", "disk_free_gb", "note"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def rows(statuses: list[str]) -> list[dict[str, str]]:
    return [
        {
            "cutoff": f"20210{idx}23",
            "epsilon": "eps365",
            "lane": "only",
            "run_id": f"run_{idx}",
            "phase": "report" if status == "pass" else "fit",
            "status": status,
            "started_at": "",
            "finished_at": "",
            "manifest_path": "",
            "latest_log_mtime": "",
            "disk_free_gb": "",
            "note": "",
        }
        for idx, status in enumerate(statuses, start=1)
    ]


class LaunchHE2ExdqlmDropAfterALKeepTests(unittest.TestCase):
    def test_defaults_point_to_promoted_q50_repair_drop_package(self) -> None:
        self.assertIn("q50repair", DEFAULT_DROP_ARTIFACT_ROOT.name)
        self.assertEqual(DEFAULT_SESSION, "he2_exal_drop_q50repair_20260602")

    def test_waits_until_keep_matrix_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            keep = Path(tmp) / "keep"
            drop = Path(tmp) / "drop"
            write_matrix_status(keep, rows(["pending", "not_started"]))
            write_matrix_status(drop, [])

            payload = handoff_once(
                keep,
                drop,
                "drop_session",
                active_count=lambda _root: 0,
                validate_drop=lambda _root: {"ok": True},
                has_session=lambda _session: False,
            )
            self.assertEqual(payload["state"], "waiting_for_keep")

    def test_refuses_when_keep_failed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            keep = Path(tmp) / "keep"
            drop = Path(tmp) / "drop"
            write_matrix_status(keep, rows(["pass", "fail"]))
            write_matrix_status(drop, [])

            payload = handoff_once(
                keep,
                drop,
                "drop_session",
                active_count=lambda _root: 0,
                validate_drop=lambda _root: {"ok": True},
                has_session=lambda _session: False,
            )
            self.assertEqual(payload["state"], "keep_failed")

    def test_dry_run_ready_only_after_passed_keep_and_validation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            keep = Path(tmp) / "keep"
            drop = Path(tmp) / "drop"
            write_matrix_status(keep, rows(["pass", "pass", "pass"]))
            write_matrix_status(drop, [])

            payload = handoff_once(
                keep,
                drop,
                "drop_session",
                dry_run=True,
                active_count=lambda _root: 0,
                validate_drop=lambda _root: {"ok": True, "returncode": 0},
                has_session=lambda _session: False,
            )
            self.assertEqual(payload["state"], "drop_launch_dry_run_ready")
            self.assertTrue(payload["drop_validation"]["ok"])

    def test_waits_for_keep_processes_even_after_passed_matrix(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            keep = Path(tmp) / "keep"
            drop = Path(tmp) / "drop"
            write_matrix_status(keep, rows(["pass", "pass"]))
            write_matrix_status(drop, [])

            payload = handoff_once(
                keep,
                drop,
                "drop_session",
                active_count=lambda root: 1 if root == keep else 0,
                validate_drop=lambda _root: {"ok": True},
                has_session=lambda _session: False,
            )
            self.assertEqual(payload["state"], "waiting_for_keep_processes_to_exit")


if __name__ == "__main__":
    unittest.main()
