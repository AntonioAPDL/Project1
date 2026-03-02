from __future__ import annotations

import copy
import datetime as dt
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd
import xarray as xr


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
import nws_operational_latest_update as updater  # noqa: E402


def _cfg_for_test() -> dict:
    cfg = copy.deepcopy(updater.DEFAULT_CONFIG)
    cfg["output"]["root_dir"] = "tmp_operational_nws/site=11160500"
    cfg["output"]["cache_alias_root"] = "tmp_operational_nws/cache_alias/nws"
    cfg["output"]["status_file_rel"] = "status/latest_run.json"
    cfg["output"]["plot_file_rel"] = "plots/nws_operational_latest.png"
    cfg["processing"]["post_days"] = 2
    cfg["observed"]["pre_days"] = 2
    cfg["ingest"]["workers"] = 1
    cfg["ingest"]["max_tasks"] = 1
    return cfg


def _write_members_csv(path: Path, dates: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        {
            "target_date": dates,
            "member_01": [1.0 for _ in dates],
            "member_02": [2.0 for _ in dates],
        }
    ).to_csv(path, index=False)


class NwsOperationalLatestUpdateTests(unittest.TestCase):
    def test_parse_nwm_key_extracts_cycle_member_lead(self) -> None:
        key = "nwm.20260301/medium_range_mem3/nwm.t12z.medium_range.channel_rt_3.f087.conus.nc"
        parsed = updater.parse_nwm_key(key)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["issue_date"], "2026-03-01")
        self.assertEqual(parsed["issue_hour"], 12)
        self.assertEqual(parsed["member"], 3)
        self.assertEqual(parsed["lead_hour"], 87)

        self.assertIsNone(updater.parse_nwm_key("bad/key"))

    def test_worker_extract_reads_value_and_deletes_temp_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            source_nc = td_path / "source.nc"
            ds = xr.Dataset(
                data_vars={"streamflow": (("feature_id",), np.array([1.0, 2.5, 4.0], dtype=np.float64))},
                coords={"feature_id": np.array([10, 20, 30], dtype=np.int64)},
            )
            ds.to_netcdf(source_nc)
            ds.close()

            created_paths: list[Path] = []

            def fake_download(url: str, timeout_connect: float, timeout_read: float):
                del url, timeout_connect, timeout_read
                out = td_path / f"download_{len(created_paths)}.nc"
                shutil.copy2(source_nc, out)
                created_paths.append(out)
                return str(out), out.stat().st_size

            payload = {
                "task": {"url": "https://example.invalid/file.nc", "key": "k"},
                "feature_index": 1,
                "retries": 1,
                "backoff_sec": 0.01,
                "timeout_connect_sec": 1,
                "timeout_read_sec": 1,
            }
            with mock.patch.object(updater, "_download_to_temp", side_effect=fake_download):
                rec = updater._worker_extract(payload)

            self.assertEqual(rec["key"], "k")
            self.assertAlmostEqual(float(rec["value"]), 2.5, places=6)
            self.assertEqual(len(created_paths), 1)
            self.assertFalse(created_paths[0].exists())

    def test_promote_successful_run_keeps_only_latest_run(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "root"
            old_run = root / "runs" / "old_run"
            old_run.mkdir(parents=True, exist_ok=True)
            (old_run / "marker.txt").write_text("old", encoding="utf-8")

            (root / "current").parent.mkdir(parents=True, exist_ok=True)
            rel_old = old_run.relative_to(root)
            (root / "current").symlink_to(rel_old)

            stage = root / "staging" / "new_run"
            stage.mkdir(parents=True, exist_ok=True)
            (stage / "marker.txt").write_text("new", encoding="utf-8")

            run_dir, old_current = updater.promote_successful_run(root, stage)
            self.assertTrue(run_dir.exists())
            self.assertEqual(run_dir.name, "new_run")
            self.assertIsNotNone(old_current)
            self.assertEqual((root / "current").resolve(), run_dir.resolve())
            self.assertFalse(old_run.exists())

    def test_run_once_rolls_back_to_previous_current_on_failure(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo_root = Path(td) / "repo"
            repo_root.mkdir(parents=True, exist_ok=True)
            cfg = _cfg_for_test()
            root_dir = repo_root / cfg["output"]["root_dir"]

            old_run = root_dir / "runs" / "old_ok"
            _write_members_csv(old_run / "forecasts" / "nws_members.csv", ["2026-03-02", "2026-03-03"])
            (root_dir / "current").parent.mkdir(parents=True, exist_ok=True)
            (root_dir / "current").symlink_to(old_run.relative_to(root_dir))

            issue = updater.IssueCycle(issue_date=dt.date(2026, 3, 1), cycle_hour=12)

            def fake_postprocess(cfg_arg, repo_arg, issue_arg, pkl_path, out_csv):
                del cfg_arg, repo_arg, issue_arg, pkl_path
                _write_members_csv(out_csv, ["2026-03-02", "2026-03-03"])
                return 0.01, ["ok"]

            with mock.patch.object(updater, "find_latest_cycle", return_value=issue), \
                mock.patch.object(
                    updater,
                    "build_tasks",
                    return_value=[updater.ExtractionTask(key="k", url="u", member=1, lead_hour=1)],
                ), \
                mock.patch.object(updater, "resolve_feature_index", return_value=(0, 1.0)), \
                mock.patch.object(
                    updater,
                    "extract_cycle_values",
                    return_value={
                        "values": {"k": 1.0},
                        "download_extract_seconds": 0.01,
                        "total_bytes": 10,
                        "avg_attempts_per_file": 1.0,
                    },
                ), \
                mock.patch.object(updater, "run_postprocess", side_effect=fake_postprocess), \
                mock.patch.object(
                    updater,
                    "fetch_usgs_recent",
                    return_value=pd.DataFrame(
                        {
                            "date": [dt.date(2026, 2, 28), dt.date(2026, 3, 1)],
                            "discharge_cms": [1.0, 2.0],
                        }
                    ),
                ), \
                mock.patch.object(updater, "build_plot", side_effect=lambda **kwargs: Path(kwargs["out_png"]).write_bytes(b"png")), \
                mock.patch.object(updater, "validate_stage_outputs", side_effect=RuntimeError("validation failed")):
                with self.assertRaises(RuntimeError):
                    updater.run_once(cfg, repo_root)

            self.assertTrue(old_run.exists())
            self.assertEqual((root_dir / "current").resolve(), old_run.resolve())
            stage_root = root_dir / "staging"
            if stage_root.exists():
                self.assertEqual(list(stage_root.iterdir()), [])

    def test_run_once_skips_when_latest_cycle_already_current(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo_root = Path(td) / "repo"
            repo_root.mkdir(parents=True, exist_ok=True)
            cfg = _cfg_for_test()
            root_dir = repo_root / cfg["output"]["root_dir"]

            issue = updater.IssueCycle(issue_date=dt.date(2026, 3, 1), cycle_hour=12)
            run_dir = root_dir / "runs" / "ok_run"
            _write_members_csv(run_dir / "forecasts" / "nws_members.csv", ["2026-03-02", "2026-03-03"])
            (root_dir / "current").parent.mkdir(parents=True, exist_ok=True)
            (root_dir / "current").symlink_to(run_dir.relative_to(root_dir))

            status_path = root_dir / cfg["output"]["status_file_rel"]
            status_path.parent.mkdir(parents=True, exist_ok=True)
            status_path.write_text(
                json.dumps(
                    {
                        "status": "success",
                        "issue_date": issue.issue_date.isoformat(),
                        "cycle_hour": issue.cycle_hour,
                    }
                ),
                encoding="utf-8",
            )

            with mock.patch.object(updater, "find_latest_cycle", return_value=issue), mock.patch.object(
                updater, "build_tasks", side_effect=AssertionError("build_tasks should not run on idempotent skip")
            ):
                out = updater.run_once(cfg, repo_root)

            self.assertEqual(out["status"], "skipped_current")
            self.assertEqual(out["issue_date"], "2026-03-01")
            self.assertEqual(out["cycle_hour"], 12)

    def test_run_once_success_replaces_old_and_publishes_alias(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo_root = Path(td) / "repo"
            repo_root.mkdir(parents=True, exist_ok=True)
            cfg = _cfg_for_test()
            root_dir = repo_root / cfg["output"]["root_dir"]

            old_run = root_dir / "runs" / "old_ok"
            _write_members_csv(old_run / "forecasts" / "nws_members.csv", ["2026-03-01", "2026-03-02"])
            (root_dir / "current").parent.mkdir(parents=True, exist_ok=True)
            (root_dir / "current").symlink_to(old_run.relative_to(root_dir))

            issue = updater.IssueCycle(issue_date=dt.date(2026, 3, 1), cycle_hour=12)

            def fake_postprocess(cfg_arg, repo_arg, issue_arg, pkl_path, out_csv):
                del cfg_arg, repo_arg, issue_arg, pkl_path
                _write_members_csv(out_csv, ["2026-03-02", "2026-03-03"])
                return 0.02, ["ok"]

            with mock.patch.object(updater, "find_latest_cycle", return_value=issue), \
                mock.patch.object(
                    updater,
                    "build_tasks",
                    return_value=[updater.ExtractionTask(key="k", url="u", member=1, lead_hour=1)],
                ), \
                mock.patch.object(updater, "resolve_feature_index", return_value=(0, 1.0)), \
                mock.patch.object(
                    updater,
                    "extract_cycle_values",
                    return_value={
                        "values": {"k": 1.0},
                        "download_extract_seconds": 0.01,
                        "total_bytes": 10,
                        "avg_attempts_per_file": 1.0,
                    },
                ), \
                mock.patch.object(updater, "run_postprocess", side_effect=fake_postprocess), \
                mock.patch.object(
                    updater,
                    "fetch_usgs_recent",
                    return_value=pd.DataFrame(
                        {
                            "date": [dt.date(2026, 2, 28), dt.date(2026, 3, 1)],
                            "discharge_cms": [1.0, 2.0],
                        }
                    ),
                ), \
                mock.patch.object(updater, "build_plot", side_effect=lambda **kwargs: Path(kwargs["out_png"]).write_bytes(b"png")):
                out = updater.run_once(cfg, repo_root)

            self.assertEqual(out["status"], "success")
            self.assertFalse(old_run.exists())
            current_dir = (root_dir / "current").resolve()
            self.assertTrue((current_dir / "forecasts" / "nws_members.csv").exists())
            self.assertTrue((current_dir / "forecasts" / "nws_weighted_daily.csv").exists())
            self.assertTrue((current_dir / "forecasts" / "nws_forecast.csv").exists())

            alias_file = (
                repo_root
                / cfg["output"]["cache_alias_root"]
                / f"cutoff_date={issue.issue_date.isoformat()}"
                / "nws_members.csv"
            )
            self.assertTrue(alias_file.exists())

            status_file = root_dir / cfg["output"]["status_file_rel"]
            self.assertTrue(status_file.exists())


if __name__ == "__main__":
    unittest.main()
