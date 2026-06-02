from __future__ import annotations

import csv
import os
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
os.sys.path.insert(0, str(ROOT / "scripts"))

from build_he2_dqlm_multivar_al_keep_from_exal_winners import (  # noqa: E402
    MAX_ACTIVE_QUANTILE_WORKERS,
    QUANTILE_WORKERS_PER_RUN,
    RUN_ROWS_AT_ONCE,
    TARGET_FAMILY,
    TARGET_LABEL,
    TARGET_MODEL_ID,
    TARGET_MODEL_KEY,
    build_package,
    target_run_id,
)
from he2_exdqlm_keep_authoritative import (  # noqa: E402
    EXPECTED_CUTOFFS,
    EXPECTED_QUANTILE_LABELS,
    EXPECTED_QUANTILES,
    load_authoritative_spec,
)
from validate_he2_dqlm_multivar_al_keep_from_exal_winners_prelaunch import validate  # noqa: E402


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    assert isinstance(payload, dict)
    return payload


class HE2DQLMMultivarALKeepFromExALWinnersTests(unittest.TestCase):
    def test_builder_clones_authoritative_winners_and_switches_likelihood_only(self) -> None:
        spec = load_authoritative_spec()
        with tempfile.TemporaryDirectory() as tmp:
            artifact_root = Path(tmp) / "al_keep_artifacts"
            metadata = build_package(spec.manifest_path, artifact_root)
            self.assertEqual(metadata["target_family"], TARGET_FAMILY)
            self.assertEqual(metadata["target_label"], TARGET_LABEL)
            self.assertEqual(metadata["target_model_id"], TARGET_MODEL_ID)
            self.assertEqual(metadata["n_run_rows"], 5)
            self.assertEqual(metadata["n_quantile_fits"], 35)
            self.assertEqual(metadata["run_rows_at_once"], RUN_ROWS_AT_ONCE)
            self.assertEqual(metadata["quantile_workers_per_run"], QUANTILE_WORKERS_PER_RUN)
            self.assertEqual(metadata["max_active_quantile_workers"], MAX_ACTIVE_QUANTILE_WORKERS)
            self.assertEqual(metadata["queue"]["ordinary_max_concurrent"], 2)
            self.assertEqual(metadata["queue"]["heavy_cutoff_max_concurrent"], 2)
            self.assertFalse(metadata["queue"]["heavy_cutoff_blocks_ordinary"])
            self.assertEqual(metadata["resources"]["fit_parallel_workers"], 7)
            self.assertEqual(metadata["resources"]["mc_cores"], 7)

            matrix_path = artifact_root / "control" / "publication_relaunch_matrix" / "matrix_plan.csv"
            with matrix_path.open(newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 5)
            self.assertEqual([row["cutoff"] for row in rows], EXPECTED_CUTOFFS)
            self.assertEqual({row["active_quantiles"] for row in rows}, {EXPECTED_QUANTILE_LABELS})
            self.assertEqual({row["family_id"] for row in rows}, {TARGET_FAMILY})
            self.assertEqual({row["model_id"] for row in rows}, {TARGET_MODEL_ID})
            self.assertEqual({row["model_key"] for row in rows}, {TARGET_MODEL_KEY})
            self.assertEqual({row["likelihood_mode"] for row in rows}, {"al"})
            self.assertEqual({row["transfer_mode"] for row in rows}, {"keep"})

            by_cutoff = spec.winner_by_cutoff()
            for row in rows:
                cutoff = row["cutoff"]
                winner = by_cutoff[cutoff]
                self.assertEqual(row["run_id"], target_run_id(cutoff, winner.grid_spec_id))
                target_cfg = load_yaml(Path(row["config_path"]))
                source_cfg = load_yaml(spec.generated_config_path(winner))

                self.assertEqual(target_cfg["models"]["exdqlm_multivar"]["likelihood_mode"], "al")
                self.assertEqual(source_cfg["models"]["exdqlm_multivar"]["likelihood_mode"], "exal")
                self.assertEqual(target_cfg["models"]["exdqlm_multivar"]["forecast_transfer_mode"], "keep")
                self.assertEqual(target_cfg["models"]["exdqlm_multivar"]["state_evolution"], source_cfg["models"]["exdqlm_multivar"]["state_evolution"])
                self.assertEqual(target_cfg["models"]["exdqlm_multivar"]["structure"], source_cfg["models"]["exdqlm_multivar"]["structure"])
                self.assertEqual(target_cfg["fit"], source_cfg["fit"])
                self.assertEqual(target_cfg["inputs"], source_cfg["inputs"])
                self.assertEqual(target_cfg["dates"], source_cfg["dates"])
                self.assertEqual(target_cfg["scale_contract"], source_cfg["scale_contract"])
                self.assertEqual(target_cfg["fit"]["quantiles"], EXPECTED_QUANTILES)
                self.assertEqual(target_cfg["fit"]["exdqlm_multivar"]["gamma_sigma"]["max_iter"], 100)
                self.assertEqual(target_cfg["debug_he2_dqlm_al_keep_from_exal_winners"]["source_run_id"], winner.run_id)
                self.assertTrue(target_cfg["debug_he2_dqlm_al_keep_from_exal_winners"]["no_launch"])

    def test_prelaunch_validator_passes_on_generated_package(self) -> None:
        spec = load_authoritative_spec()
        with tempfile.TemporaryDirectory() as tmp:
            artifact_root = Path(tmp) / "al_keep_artifacts"
            build_package(spec.manifest_path, artifact_root)
            rec, summary = validate(spec.manifest_path, artifact_root)
            self.assertEqual(summary["failures"], 0, rec.failures)
            self.assertEqual(summary["run_rows"], 5)
            self.assertEqual(summary["quantile_fits"], 35)


if __name__ == "__main__":
    unittest.main()
