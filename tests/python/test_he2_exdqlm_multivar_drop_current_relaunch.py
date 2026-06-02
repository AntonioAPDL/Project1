from __future__ import annotations

import csv
import os
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
os.sys.path.insert(0, str(ROOT / "scripts"))

from build_he2_exdqlm_multivar_drop_current_relaunch import (  # noqa: E402
    MAX_ACTIVE_QUANTILE_WORKERS,
    QUANTILE_WORKERS_PER_RUN,
    RUN_ROWS_AT_ONCE,
    TARGET_FAMILY,
    TARGET_LABEL,
    TARGET_MODEL_ID,
    TARGET_MODEL_KEY,
    build_package,
)
from he2_publication_relaunch_lib import EXPECTED_CUTOFFS  # noqa: E402
from validate_he2_exdqlm_multivar_drop_current_prelaunch import validate  # noqa: E402


def load_yaml(path: Path) -> dict:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    assert isinstance(payload, dict)
    return payload


class HE2ExdqlmMultivarDropCurrentRelaunchTests(unittest.TestCase):
    def test_builder_prepares_current_drop_package_with_two_row_queue(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            artifact_root = Path(tmp) / "drop_current"
            summary = build_package(artifact_root)

            self.assertEqual(summary["run_rows"], 5)
            self.assertEqual(summary["quantile_fits"], 35)
            self.assertEqual(summary["run_rows_at_once"], RUN_ROWS_AT_ONCE)
            self.assertEqual(summary["max_active_quantile_workers"], MAX_ACTIVE_QUANTILE_WORKERS)

            matrix_dir = Path(summary["matrix_dir"])
            with (matrix_dir / "matrix_plan.csv").open(newline="") as handle:
                plan_rows = list(csv.DictReader(handle))
            self.assertEqual([row["cutoff"] for row in plan_rows], EXPECTED_CUTOFFS)
            self.assertEqual({row["family_id"] for row in plan_rows}, {TARGET_FAMILY})
            self.assertEqual({row["manuscript_label"] for row in plan_rows}, {TARGET_LABEL})
            self.assertEqual({row["model_id"] for row in plan_rows}, {TARGET_MODEL_ID})
            self.assertEqual({row["model_key"] for row in plan_rows}, {TARGET_MODEL_KEY})
            self.assertEqual({row["likelihood_mode"] for row in plan_rows}, {"exal"})
            self.assertEqual({row["transfer_mode"] for row in plan_rows}, {"drop"})

            metadata = load_yaml(matrix_dir / "matrix_metadata.yaml")
            self.assertEqual(metadata["queue"]["ordinary_max_concurrent"], 2)
            self.assertEqual(metadata["queue"]["heavy_cutoff_max_concurrent"], 2)
            self.assertFalse(metadata["queue"]["heavy_cutoff_blocks_ordinary"])
            self.assertTrue(metadata["cleanup_rdata_after_post"])
            self.assertEqual(metadata["quantile_workers_per_run"], QUANTILE_WORKERS_PER_RUN)

            batch = load_yaml(Path(summary["generated_batch"]))
            self.assertEqual(batch["resources"]["fit_parallel_workers"], 7)
            self.assertEqual(batch["resources"]["mc_cores"], 7)
            family_patch = next(
                row for row in batch["overrides"]["row_config_patches"] if row.get("family") == TARGET_FAMILY and not row.get("cutoff")
            )
            model_patch = family_patch["config_patch"]["models"][TARGET_MODEL_KEY]
            self.assertEqual(model_patch["likelihood_mode"], "exal")
            self.assertEqual(model_patch["forecast_transfer_mode"], "drop")
            self.assertEqual(model_patch["structure"]["enabled_harmonic_indices"], [1, 2, 3])

    def test_prelaunch_validator_passes_generated_package(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            artifact_root = Path(tmp) / "drop_current"
            build_package(artifact_root)
            rec, summary = validate(artifact_root)
            self.assertEqual(summary["failures"], 0, rec.failures)
            self.assertEqual(summary["run_rows"], 5)
            self.assertEqual(summary["quantile_fits"], 35)


if __name__ == "__main__":
    unittest.main()
