from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))

from cleanup_he2_runtime_artifacts import CleanupTarget, build_plan, collect_evidence_files, collect_prune_files, parse_spec


class CleanupHe2RuntimeArtifactsTests(unittest.TestCase):
    def test_collect_prune_files_respects_suffix_and_size_threshold(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target_root = root / 'old_run'
            target_root.mkdir()
            keep = target_root / 'small.RData'
            keep.write_bytes(b'a' * 8)
            prune = target_root / 'big.RData'
            prune.write_bytes(b'b' * 64)
            wrong = target_root / 'notes.txt'
            wrong.write_text('keep', encoding='utf-8')

            files = collect_prune_files(
                CleanupTarget(path=target_root, reason='test'),
                suffixes={'.rdata'},
                min_size_bytes=32,
                protected_roots=set(),
            )
            self.assertEqual(files, [prune])

    def test_collect_evidence_files_matches_globbed_logs_and_summaries(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target_root = root / 'old_run'
            log = target_root / 'fit' / 'logs' / 'fit.log'
            log.parent.mkdir(parents=True, exist_ok=True)
            log.write_text('ok', encoding='utf-8')
            summary = target_root / 'report' / 'summary.md'
            summary.parent.mkdir(parents=True, exist_ok=True)
            summary.write_text('# summary', encoding='utf-8')

            files = collect_evidence_files(CleanupTarget(path=target_root, reason='test'), patterns=['**/fit.log', '**/summary.md'])
            self.assertEqual(files, [log.resolve(), summary.resolve()])

    def test_parse_spec_and_build_plan_handle_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            runtime_root = root / 'runtime'
            runtime_root.mkdir()
            candidate = runtime_root / 'old_run'
            candidate.mkdir()
            big = candidate / 'fit.RData'
            big.write_bytes(b'x' * 128)
            evidence = candidate / 'report' / 'summary.md'
            evidence.parent.mkdir(parents=True, exist_ok=True)
            evidence.write_text('summary', encoding='utf-8')
            protected = runtime_root / 'keep_run'
            protected.mkdir()
            config = root / 'cleanup.yaml'
            config.write_text(
                yaml.safe_dump(
                    {
                        'cleanup': {
                            'cleanup_id': 'unit_test_cleanup',
                            'runtime_root': str(runtime_root),
                            'report_root': 'repro/reports/cleanup_runs',
                            'quarantine_root': 'repro/quarantine/cleanup_runs',
                            'min_size_mb': 0.00001,
                            'prune_extensions': ['.RData'],
                            'protected_roots': [str(protected)],
                            'evidence_patterns': ['**/summary.md'],
                            'candidate_roots': [{'path': str(candidate), 'reason': 'test_candidate'}],
                        }
                    },
                    sort_keys=False,
                ),
                encoding='utf-8',
            )

            spec = parse_spec(config)
            plan = build_plan(spec)
            self.assertEqual(plan['cleanup_id'], 'unit_test_cleanup')
            self.assertEqual(plan['totals']['prune_file_count'], 1)
            self.assertGreater(plan['totals']['prune_bytes'], 0)
            self.assertEqual(plan['targets'][0]['reason'], 'test_candidate')
            self.assertEqual(len(plan['targets'][0]['evidence_files']), 1)


if __name__ == '__main__':
    unittest.main()
