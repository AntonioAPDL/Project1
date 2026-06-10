from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
import sys

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from build_he2_exdqlm_multivar_keep_authoritative_retained_matrix import build_matrix
from he2_exdqlm_keep_authoritative import load_authoritative_spec


class He2ExdqlmKeepAuthoritativeRetainedMatrixTest(unittest.TestCase):
    def test_builder_selects_exact_authoritative_winners_and_disables_cleanup(self) -> None:
        spec = load_authoritative_spec(ROOT / "docs" / "exdqlm_multivar_keep_authoritative_specs_20260601.yaml")

        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            source_matrix_dir = tmp_root / "source_matrix"
            source_configs = tmp_root / "source_configs"
            artifact_root = tmp_root / "artifact"
            source_matrix_dir.mkdir(parents=True)
            source_configs.mkdir(parents=True)

            rows = []
            for idx, winner in enumerate(spec.winners, start=1):
                cfg_path = source_configs / f"{winner.run_id}.yaml"
                cfg = {
                    "run": {
                        "run_id": winner.run_id,
                        "run_root": str(tmp_root / "old_runs"),
                        "resolved_run_root": str(tmp_root / "old_runs" / winner.run_id),
                        "resolved_config_path": str(cfg_path),
                    },
                    "models": {
                        "run_exdqlm_multivar": True,
                        "run_exdqlm_univar": False,
                        "run_ndlm_main": False,
                        "run_ndlm_univar": False,
                        "exdqlm_multivar": {"forecast_transfer_mode": "keep"},
                    },
                    "fit": {"quantiles": [0.05, 0.20, 0.35, 0.50, 0.65, 0.80, 0.95]},
                }
                cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
                rows.append(
                    {
                        "order_index": str(idx),
                        "cutoff": winner.cutoff,
                        "epsilon": winner.grid_spec_id,
                        "grid_spec_id": winner.grid_spec_id,
                        "discount_case_id": winner.discount_case_id,
                        "lane": "exdqlm_multivar_keep",
                        "run_scope": "source_grid",
                        "run_id": winner.run_id,
                        "config_path": str(cfg_path),
                        "compare_outdir": "",
                        "priority_group": "2" if winner.cutoff == "20221225" else "1",
                        "max_concurrent_class": "heavy" if winner.cutoff == "20221225" else "ordinary",
                        "active_quantiles": "05|20|35|50|65|80|95",
                    }
                )
            pd.DataFrame(rows).to_csv(source_matrix_dir / "matrix_plan.csv", index=False)

            metadata = build_matrix(
                manifest_path=spec.manifest_path,
                source_matrix_dir=source_matrix_dir,
                artifact_root=artifact_root,
                tag="unit_retained",
                ordinary_max_concurrent=5,
                pause_free_gb=1.0,
                launch_free_gb=2.0,
                heavy_free_gb=3.0,
                pause_mem_gb=4.0,
                launch_mem_gb=5.0,
                heavy_mem_gb=6.0,
                heavy_cutoff_max_concurrent=1,
                poll_seconds=7,
                gamma_sigma_max_iter=None,
                gamma_sigma_min_update_iters=None,
                state_guard_start_iter=None,
                reset_status=True,
            )

            matrix_dir = artifact_root / "control" / "publication_relaunch_matrix"
            plan = pd.read_csv(matrix_dir / "matrix_plan.csv", dtype=str)
            self.assertEqual(len(plan), 5)
            self.assertEqual(plan["cutoff"].tolist(), [winner.cutoff for winner in spec.winners])
            self.assertEqual(plan["source_grid_run_id"].tolist(), [winner.run_id for winner in spec.winners])
            self.assertTrue(all(plan["run_id"].str.endswith("_unit_retained")))
            self.assertEqual(set(plan["cleanup_rdata_after_post"].astype(str)), {"False"})
            self.assertFalse(any(plan["source_grid_run_id"] == plan["run_id"]))

            scope = (matrix_dir / "RETAINED_RDATA_SCOPE.md").read_text(encoding="utf-8")
            self.assertIn("--no-cleanup", scope)
            self.assertIn("retained `.RData` expected after post: `true`", scope)
            self.assertEqual(metadata["n_quantile_fits"], 35)
            self.assertFalse(metadata["cleanup_rdata_after_post"])

            generated_cfg = yaml.safe_load(Path(plan.iloc[0]["config_path"]).read_text(encoding="utf-8"))
            self.assertEqual(generated_cfg["run"]["run_id"], plan.iloc[0]["run_id"])
            self.assertIn("debug_he2_exdqlm_keep_authoritative_retained", generated_cfg)
            self.assertTrue(generated_cfg["debug_he2_exdqlm_keep_authoritative_retained"]["retain_rdata_intent"])


if __name__ == "__main__":
    unittest.main()
