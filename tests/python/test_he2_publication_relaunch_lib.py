from __future__ import annotations

import unittest
from pathlib import Path

from scripts.he2_publication_relaunch_lib import (
    EXPECTED_CUTOFFS,
    PUBLICATION_MANIFEST_CSV,
    bundle_root,
    load_publication_manifest_rows,
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


if __name__ == '__main__':
    unittest.main()
