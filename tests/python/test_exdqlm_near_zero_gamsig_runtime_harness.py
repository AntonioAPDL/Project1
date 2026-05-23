from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

import yaml

from scripts.build_exdqlm_near_zero_gamsig_runtime_report import build_rows
from scripts.prepare_exdqlm_near_zero_gamsig_repair_runs import (
    SMOKE_CASES,
    build_smoke_package,
    mutate_config,
    q_label,
)


class ExDQLMNearZeroGamsigRuntimeHarnessTests(unittest.TestCase):
    def test_mutate_config_locks_single_lane_smoke_contract(self) -> None:
        source = {
            "run": {
                "run_id": "old",
                "run_root": "/old",
                "resolved_run_root": "/stale",
                "resolved_config_path": "/stale.yaml",
                "threads": {"mc_cores": 7},
            },
            "stages": {"post": True, "validate": True, "report": True},
            "fit": {
                "quantiles": [0.05, 0.20],
                "parallel": {"workers": 7},
                "exdqlm_multivar": {"gamma_sigma": {}},
            },
            "debug_he2_publication_relaunch": {},
        }
        cfg = mutate_config(
            source,
            artifact_root=Path("/tmp/nearzero"),
            run_id="smoke",
            quantiles=[0.35],
            workers=1,
            mc_cores=1,
            post=False,
            validate=False,
            report=False,
        )
        self.assertEqual(cfg["run"]["run_id"], "smoke")
        self.assertEqual(cfg["run"]["run_root"], "/tmp/nearzero/runs")
        self.assertNotIn("resolved_run_root", cfg["run"])
        self.assertNotIn("resolved_config_path", cfg["run"])
        self.assertEqual(cfg["run"]["threads"]["mc_cores"], 1)
        self.assertEqual(cfg["fit"]["quantiles"], [0.35])
        self.assertEqual(cfg["fit"]["parallel"]["workers"], 1)
        self.assertFalse(cfg["stages"]["post"])
        self.assertFalse(cfg["stages"]["validate"])
        self.assertFalse(cfg["stages"]["report"])
        self.assertEqual(
            cfg["fit"]["exdqlm_multivar"]["gamma_sigma"]["near_zero_fallback"],
            {"enabled": True, "mode": "sigma_only", "gamma_anchor": "full_candidate"},
        )

    def test_build_smoke_package_writes_five_isolated_configs_and_matrix(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source_dir = tmp_path / "source"
            source_dir.mkdir()
            source_cfg = {
                "run": {"run_id": "old", "run_root": "/old", "threads": {"mc_cores": 7}},
                "stages": {},
                "fit": {
                    "quantiles": [0.05, 0.20, 0.35, 0.50, 0.65, 0.80, 0.95],
                    "parallel": {"workers": 7},
                    "exdqlm_multivar": {"gamma_sigma": {}},
                },
                "debug_he2_publication_relaunch": {},
            }
            for cutoff, _, _ in SMOKE_CASES:
                path = source_dir / f"multimodel_{cutoff}_v8_he2pubgdpc1r1_exdqlm_multivar_keep.yaml"
                path.write_text(yaml.safe_dump(source_cfg), encoding="utf-8")
            payload = build_smoke_package(
                source_config_dir=source_dir,
                artifact_root=tmp_path / "artifact",
                report_dir=tmp_path / "report",
                tag="test",
            )
            self.assertEqual(payload["package"], "smoke")
            self.assertEqual(len(payload["cases"]), 5)
            matrix_path = tmp_path / "artifact" / "control" / "smoke_matrix" / "matrix_plan.csv"
            with matrix_path.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 5)
            for row in rows:
                cfg = yaml.safe_load(Path(row["config_path"]).read_text(encoding="utf-8"))
                self.assertEqual(cfg["fit"]["quantiles"], [int(row["active_quantiles"]) / 100.0])
                self.assertEqual(cfg["run"]["threads"]["mc_cores"], 1)
                self.assertFalse(cfg["stages"]["post"])

    def test_q_label_formats_canonical_lanes(self) -> None:
        self.assertEqual(q_label(0.05), "05")
        self.assertEqual(q_label(0.20), "20")
        self.assertEqual(q_label(0.95), "95")

    def test_runtime_report_accepts_verified_post_cleaned_rdata_only_when_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            artifact = tmp_path / "artifact"
            matrix = artifact / "control" / "repair_matrix"
            run_id = "repair_20210123"
            run_root = artifact / "runs" / run_id
            q_log = run_root / "fit" / "exdqlm_multivar" / "keep" / "q=20" / "logs" / "fit.log"
            q_log.parent.mkdir(parents=True)
            q_log.write_text(
                "\n".join([
                    "[gamsig_policy] near_zero_fallback_enabled=TRUE near_zero_fallback_mode=sigma_only near_zero_gamma_anchor=full_candidate",
                    "[gamsig_progress] iter=100 gamsig_update_iters=60 min_update_iters=50 elbo=-1 crit_elbo=0 sigma_exp=0.1 gamma_exp=0.2 state_norm_sq=3 near_zero_fallback_count=1",
                ])
                + "\n",
                encoding="utf-8",
            )
            run_log = tmp_path / "reports" / "run.log"
            run_log.parent.mkdir(parents=True)
            run_log.write_text(
                "Post-stage .RData cleanup: before=7 removed=7 remaining=0\n",
                encoding="utf-8",
            )
            matrix.mkdir(parents=True)
            with (matrix / "matrix_plan.csv").open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=["package", "role", "cutoff", "active_quantiles", "run_id", "run_root"],
                )
                writer.writeheader()
                writer.writerow({
                    "package": "repair",
                    "role": "failed_cutoff_row_repair",
                    "cutoff": "20210123",
                    "active_quantiles": "20",
                    "run_id": run_id,
                    "run_root": str(run_root),
                })
            with (matrix / "matrix_status.csv").open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=["run_id", "phase", "status", "returncode", "log_path"])
                writer.writeheader()
                writer.writerow({
                    "run_id": run_id,
                    "phase": "complete",
                    "status": "pass",
                    "returncode": "0",
                    "log_path": str(run_log),
                })

            strict_rows = build_rows(artifact, matrix)
            self.assertFalse(strict_rows[0]["pass_gate"])
            self.assertEqual(strict_rows[0]["rdata_contract"], "missing")

            cleanup_rows = build_rows(artifact, matrix, allow_post_cleaned_rdata=True)
            self.assertTrue(cleanup_rows[0]["pass_gate"])
            self.assertEqual(cleanup_rows[0]["rdata_contract"], "post_cleaned")
            self.assertEqual(cleanup_rows[0]["cleanup_rdata_removed"], 7)


if __name__ == "__main__":
    unittest.main()
