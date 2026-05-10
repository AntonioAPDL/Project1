from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from scripts.he2_publication_relaunch_lib import (
    EXPECTED_CUTOFFS,
    PUBLICATION_MANIFEST_CSV,
    bundle_root,
    initialize_matrix_status,
    load_publication_manifest_rows,
    reset_campaign_state,
    selected_window_retros_by_cutoff,
)


class HE2PublicationRelaunchLibTests(unittest.TestCase):
    def test_publication_manifest_rows_cover_full_matrix(self) -> None:
        rows = load_publication_manifest_rows(PUBLICATION_MANIFEST_CSV)
        self.assertEqual(len(rows), 45)
        self.assertEqual(sorted({row['cutoff'] for row in rows}), sorted(EXPECTED_CUTOFFS))

    def test_selected_window_retros_cover_all_cutoffs(self) -> None:
        mapping = selected_window_retros_by_cutoff(PUBLICATION_MANIFEST_CSV)
        self.assertEqual(sorted(mapping.keys()), sorted(EXPECTED_CUTOFFS))
        for path in mapping.values():
            self.assertTrue(Path(path).exists())

    def test_bundle_root_suffix(self) -> None:
        root = bundle_root('/tmp/example_bundle_root', '20210123', 'bundle_r01')
        self.assertTrue(str(root).endswith('stable_inputs/site=11160500/cutoff_date=2021-01-23/run_id=bundle_r01'))

    def test_reset_campaign_state_archives_runtime_and_reinitializes_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            artifact_root = tmp_path / 'artifact_root'
            matrix_dir = artifact_root / 'control' / 'publication_relaunch_matrix'
            matrix_dir.mkdir(parents=True, exist_ok=True)
            runs_root = artifact_root / 'runs'
            reports_root = artifact_root / 'reports'
            run_id = 'multimodel_20210123_v8_he2pubgdpc1r1_ndlm_univar_keep'
            compare_outdir = reports_root / 'multimodel_20210123_v8_he2pubgdpc1r1_compare'
            (runs_root / run_id).mkdir(parents=True, exist_ok=True)
            compare_outdir.mkdir(parents=True, exist_ok=True)
            (compare_outdir / 'dummy.txt').write_text('ok\n', encoding='utf-8')

            with (matrix_dir / 'matrix_plan.csv').open('w', newline='', encoding='utf-8') as handle:
                writer = csv.DictWriter(handle, fieldnames=['run_id', 'compare_outdir'])
                writer.writeheader()
                writer.writerow({'run_id': run_id, 'compare_outdir': str(compare_outdir)})

            initialize_matrix_status(matrix_dir / 'matrix_status.csv')
            (matrix_dir / 'queue.log').write_text('old queue log\n', encoding='utf-8')
            controller_state = matrix_dir / 'controller_state'
            controller_state.mkdir(parents=True, exist_ok=True)
            (controller_state / 'controller.pid').write_text('123\n', encoding='utf-8')

            summary = reset_campaign_state(matrix_dir, artifact_root, reset_tag='reset_test')

            archive_root = matrix_dir.parent / 'restart_resets' / 'reset_test'
            self.assertEqual(summary['archive_root'], str(archive_root))
            self.assertTrue((archive_root / 'matrix_status.csv').exists())
            self.assertTrue((archive_root / 'queue.log').exists())
            self.assertTrue((archive_root / 'controller_state' / 'controller.pid').exists())
            self.assertTrue((archive_root / 'runs' / run_id).exists())
            self.assertTrue((archive_root / 'compare_outputs' / compare_outdir.name / 'dummy.txt').exists())
            self.assertFalse((runs_root / run_id).exists())
            self.assertFalse(compare_outdir.exists())
            status_lines = (matrix_dir / 'matrix_status.csv').read_text(encoding='utf-8').splitlines()
            self.assertEqual(len(status_lines), 1)
            self.assertIn('cutoff,epsilon,lane,run_id,phase,status', status_lines[0])
            self.assertEqual((matrix_dir / 'queue.log').read_text(encoding='utf-8'), '')


if __name__ == '__main__':
    unittest.main()
