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
                current_authority_overlay=None,
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

    def test_builder_can_clone_current_overlay_replacements(self) -> None:
        spec = load_authoritative_spec(ROOT / "docs" / "exdqlm_multivar_keep_authoritative_specs_20260601.yaml")

        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            source_matrix_dir = tmp_root / "source_matrix"
            source_configs = tmp_root / "source_configs"
            partial_artifact = tmp_root / "partial_authority"
            partial_matrix_dir = partial_artifact / "control" / "publication_relaunch_matrix"
            partial_configs = partial_artifact / "control" / "generated_configs"
            partial_run_id = "multimodel_20211221_v8_he2partial20260623_exdqlm_multivar_keep"
            artifact_root = tmp_root / "artifact"
            source_matrix_dir.mkdir(parents=True)
            source_configs.mkdir(parents=True)
            partial_matrix_dir.mkdir(parents=True)
            partial_configs.mkdir(parents=True)

            rows = []
            for idx, winner in enumerate(spec.winners, start=1):
                cfg_path = source_configs / f"{winner.run_id}.yaml"
                cfg_path.write_text(
                    yaml.safe_dump(
                        {
                            "run": {
                                "run_id": winner.run_id,
                                "run_root": str(tmp_root / "old_runs"),
                                "resolved_run_root": str(tmp_root / "old_runs" / winner.run_id),
                                "resolved_config_path": str(cfg_path),
                            },
                            "models": {"exdqlm_multivar": {"forecast_transfer_mode": "keep"}},
                            "fit": {"quantiles": [0.05, 0.20, 0.35, 0.50, 0.65, 0.80, 0.95]},
                        },
                        sort_keys=False,
                    ),
                    encoding="utf-8",
                )
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

            partial_cfg = partial_configs / f"{partial_run_id}.yaml"
            partial_cfg.write_text(
                yaml.safe_dump(
                    {
                        "run": {
                            "run_id": partial_run_id,
                            "run_root": str(partial_artifact / "runs"),
                            "resolved_run_root": str(partial_artifact / "runs" / partial_run_id),
                            "resolved_config_path": str(partial_cfg),
                        },
                        "models": {"exdqlm_multivar": {"forecast_transfer_mode": "keep"}},
                        "fit": {"quantiles": [0.05, 0.20, 0.35, 0.50, 0.65, 0.80, 0.95]},
                    },
                    sort_keys=False,
                ),
                encoding="utf-8",
            )
            pd.DataFrame(
                [
                    {
                        "order_index": "1",
                        "cutoff": "20211221",
                        "epsilon": "he2partial20260623",
                        "lane": "exdqlm_multivar_keep",
                        "run_scope": "partial_authority",
                        "run_id": partial_run_id,
                        "config_path": str(partial_cfg),
                        "compare_outdir": "",
                        "selected_mean_crps": "0.2604466008954305",
                        "active_quantiles": "05|20|35|50|65|80|95",
                    }
                ]
            ).to_csv(partial_matrix_dir / "matrix_plan.csv", index=False)
            partial_run_root = partial_artifact / "runs" / partial_run_id
            partial_run_root.mkdir(parents=True)

            overlay_path = tmp_root / "current_overlay.yaml"
            overlay_path.write_text(
                yaml.safe_dump(
                    {
                        "replacements": [
                            {
                                "cutoff": "20211221",
                                "family": "exdqlm_multivar_keep",
                                "manuscript_label": "exAL-M-T1",
                                "run_id": partial_run_id,
                                "run_root": str(partial_run_root),
                                "campaign_lineage": "unit:clean_replay",
                                "replaced_source_run_id": "multimodel_20211221_v8_he2grid_c03_eps030_exdqlm_multivar_keep",
                            }
                        ]
                    },
                    sort_keys=False,
                ),
                encoding="utf-8",
            )

            metadata = build_matrix(
                manifest_path=spec.manifest_path,
                current_authority_overlay=overlay_path,
                source_matrix_dir=source_matrix_dir,
                artifact_root=artifact_root,
                tag="unit_current",
                ordinary_max_concurrent=2,
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
            replaced = plan.loc[plan["cutoff"].astype(str) == "20211221"].iloc[0]
            self.assertEqual(replaced["source_grid_run_id"], partial_run_id)
            self.assertEqual(replaced["grid_spec_id"], "he2partial20260623")
            self.assertEqual(replaced["authority_source"], "current_authority_overlay")
            self.assertIn("current_overlay.yaml", metadata["current_authority_overlay"])

            generated_cfg = yaml.safe_load(Path(replaced["config_path"]).read_text(encoding="utf-8"))
            debug = generated_cfg["debug_he2_exdqlm_keep_authoritative_retained"]
            self.assertEqual(debug["authority_source"], "current_authority_overlay")
            self.assertEqual(debug["authority_lineage"], "unit:clean_replay")


if __name__ == "__main__":
    unittest.main()
