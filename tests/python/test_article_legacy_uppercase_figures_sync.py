from __future__ import annotations

import csv
import unittest
from pathlib import Path


ARTICLE_ROOT = Path('/data/muscat_data/jaguir26/project1_ucsc_phd/Evironmetrics---REVISED-DOC-Corrected-2')
LOWER = ARTICLE_ROOT / 'figures'
UPPER = ARTICLE_ROOT / 'Figures'
MIRROR_MANIFEST = UPPER / 'mirror_manifest.csv'


class ArticleLegacyUppercaseFiguresSyncTest(unittest.TestCase):
    def test_uppercase_tree_matches_lowercase_tree(self) -> None:
        lower_files = sorted(str(p.relative_to(LOWER)) for p in LOWER.rglob('*') if p.is_file())
        upper_files = sorted(
            str(p.relative_to(UPPER))
            for p in UPPER.rglob('*')
            if p.is_file() and p.relative_to(UPPER) not in {Path('README.md'), Path('mirror_manifest.csv')}
        )
        self.assertEqual(lower_files, upper_files)

    def test_mirror_manifest_tracks_all_lowercase_files(self) -> None:
        with MIRROR_MANIFEST.open(newline='', encoding='utf-8') as handle:
            rows = list(csv.DictReader(handle))
        lower_files = sorted(str(p.relative_to(LOWER)) for p in LOWER.rglob('*') if p.is_file())
        manifest_files = sorted(row['relative_path'] for row in rows)
        self.assertEqual(lower_files, manifest_files)


if __name__ == '__main__':
    unittest.main()
