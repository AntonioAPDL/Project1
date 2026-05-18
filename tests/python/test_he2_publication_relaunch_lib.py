from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from scripts.he2_publication_relaunch_lib import (
    EXPECTED_CUTOFFS,
    PUBLICATION_MANIFEST_CSV,
    bundle_root,
    initialize_matrix_status,
    load_publication_manifest_rows,
    load_structured_file,
    model_class,
    parse_quantile_list,
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

    def test_parse_quantile_list_accepts_numeric_fraction_percent_and_q_labels(self) -> None:
        parsed = parse_quantile_list([0.05, '5', 'q20', 'q=0.35', '0.95'])
        self.assertEqual(parsed, [0.05, 0.2, 0.35, 0.95])

    def test_model_class_mapping(self) -> None:
        self.assertEqual(model_class('ndlm_univar_keep'), 'ndlm')
        self.assertEqual(model_class('dqlm_univar_al'), 'quantile_univariate')
        self.assertEqual(model_class('exdqlm_multivar_keep'), 'quantile_multivariate')
        self.assertEqual(model_class('unknown_family'), 'unknown')

    def test_load_structured_file_supports_yaml_and_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            yaml_path = tmp_path / 'batch.yaml'
            json_path = tmp_path / 'batch.json'
            yaml_path.write_text('selection:\n  cutoffs: ["20210123"]\n', encoding='utf-8')
            json_path.write_text(json.dumps({'selection': {'families': ['ndlm_univar_keep']}}), encoding='utf-8')
            self.assertEqual(load_structured_file(yaml_path)['selection']['cutoffs'], ['20210123'])
            self.assertEqual(load_structured_file(json_path)['selection']['families'], ['ndlm_univar_keep'])

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
            self.assertGreaterEqual(len(status_lines), 1)
            self.assertIn('cutoff,epsilon,lane,run_id,phase,status', status_lines[0])
            if len(status_lines) > 1:
                self.assertIn('not_started,not_started', status_lines[1])
            self.assertEqual((matrix_dir / 'queue.log').read_text(encoding='utf-8'), '')

    def test_reset_campaign_state_can_archive_only_selected_cutoffs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            artifact_root = tmp_path / 'artifact_root'
            matrix_dir = artifact_root / 'control' / 'publication_relaunch_matrix'
            matrix_dir.mkdir(parents=True, exist_ok=True)
            runs_root = artifact_root / 'runs'
            reports_root = artifact_root / 'reports'
            run_a = 'multimodel_20210123_v8_he2pubgdpc1r1_exdqlm_multivar_keep'
            run_b = 'multimodel_20211221_v8_he2pubgdpc1r1_exdqlm_multivar_keep'
            compare_a = reports_root / 'multimodel_20210123_v8_he2pubgdpc1r1_compare'
            compare_b = reports_root / 'multimodel_20211221_v8_he2pubgdpc1r1_compare'
            for run_id in (run_a, run_b):
                run_dir = runs_root / run_id
                run_dir.mkdir(parents=True, exist_ok=True)
                (run_dir / 'run_manifest.yaml').write_text(
                    'stages:\n  report:\n    status: pass\n',
                    encoding='utf-8',
                )
            for outdir in (compare_a, compare_b):
                outdir.mkdir(parents=True, exist_ok=True)
                (outdir / 'dummy.txt').write_text('ok\n', encoding='utf-8')

            with (matrix_dir / 'matrix_plan.csv').open('w', newline='', encoding='utf-8') as handle:
                writer = csv.DictWriter(handle, fieldnames=['cutoff', 'run_id', 'compare_outdir'])
                writer.writeheader()
                writer.writerow({'cutoff': '20210123', 'run_id': run_a, 'compare_outdir': str(compare_a)})
                writer.writerow({'cutoff': '20211221', 'run_id': run_b, 'compare_outdir': str(compare_b)})

            initialize_matrix_status(matrix_dir / 'matrix_status.csv')
            (matrix_dir / 'queue.log').write_text('old queue log\n', encoding='utf-8')
            run_logs = matrix_dir / 'run_logs'
            run_logs.mkdir(parents=True, exist_ok=True)
            (run_logs / f'{run_a}.log').write_text('a\n', encoding='utf-8')
            (run_logs / f'{run_b}.log').write_text('b\n', encoding='utf-8')

            summary = reset_campaign_state(
                matrix_dir,
                artifact_root,
                reset_tag='selective_reset',
                cutoffs=['20211221'],
            )

            archive_root = matrix_dir.parent / 'restart_resets' / 'selective_reset'
            self.assertEqual(summary['selected_cutoffs'], ['20211221'])
            self.assertEqual(summary['selected_run_ids'], [run_b])
            self.assertIn(run_a, summary['preserved_run_ids'])
            self.assertTrue((archive_root / 'runs' / run_b).exists())
            self.assertTrue((archive_root / 'run_logs' / f'{run_b}.log').exists())
            self.assertTrue((archive_root / 'compare_outputs' / compare_b.name / 'dummy.txt').exists())
            self.assertTrue((runs_root / run_a).exists())
            self.assertFalse((runs_root / run_b).exists())
            self.assertTrue(compare_a.exists())
            self.assertFalse(compare_b.exists())
            self.assertTrue((run_logs / f'{run_a}.log').exists())
            self.assertFalse((run_logs / f'{run_b}.log').exists())

    def test_reset_campaign_state_raises_when_no_rows_match_selector(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            artifact_root = tmp_path / 'artifact_root'
            matrix_dir = artifact_root / 'control' / 'publication_relaunch_matrix'
            matrix_dir.mkdir(parents=True, exist_ok=True)
            with (matrix_dir / 'matrix_plan.csv').open('w', newline='', encoding='utf-8') as handle:
                writer = csv.DictWriter(handle, fieldnames=['cutoff', 'run_id', 'compare_outdir'])
                writer.writeheader()
                writer.writerow({'cutoff': '20210123', 'run_id': 'run_a', 'compare_outdir': ''})

            with self.assertRaisesRegex(ValueError, 'no matrix_plan rows matched'):
                reset_campaign_state(matrix_dir, artifact_root, cutoffs=['20211221'])


if __name__ == '__main__':
    unittest.main()
