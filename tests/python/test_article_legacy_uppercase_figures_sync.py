from __future__ import annotations

import importlib.util
import tempfile
import sys
import unittest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from article_repository_binding import active_article_root

ARTICLE_ROOT = active_article_root(Path(__file__).resolve().parents[2])
sys.path.insert(0, str(ARTICLE_ROOT / "scripts"))
from refresh_cutoff_synthesis_families import mirror_figure_family_to_lowercase

SPEC = importlib.util.spec_from_file_location('figure_compatibility_sync', ARTICLE_ROOT / 'scripts/sync_legacy_uppercase_figures.py')
assert SPEC is not None and SPEC.loader is not None
SYNC = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SYNC)


class ArticleLegacyUppercaseFiguresSyncTest(unittest.TestCase):
    def test_bounded_mirror_reads_uppercase_and_preserves_unmanaged_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'Figures/manuscript').mkdir(parents=True)
            (root / 'figures/manuscript').mkdir(parents=True)
            source = root / 'Figures/manuscript/panel.png'
            source.write_bytes(b'canonical')
            (root / 'figures/manuscript/panel.png').write_bytes(b'stale')
            unmanaged = root / 'figures/manuscript/unmanaged.png'
            unmanaged.write_bytes(b'preserve')
            rows = SYNC.mirror_figures(root, ['manuscript/panel.png'])
            self.assertEqual(source.read_bytes(), b'canonical')
            self.assertEqual((root / 'figures/manuscript/panel.png').read_bytes(), b'canonical')
            self.assertEqual(unmanaged.read_bytes(), b'preserve')
            self.assertEqual(rows[0]['canonical_source'], 'Figures/manuscript/panel.png')
            self.assertEqual(rows[0]['sha256'], SYNC.sha256(source))

    def test_invalid_batch_cannot_partially_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'Figures/manuscript').mkdir(parents=True)
            (root / 'Figures/manuscript/panel.png').write_bytes(b'canonical')
            with self.assertRaises(ValueError):
                SYNC.mirror_figures(root, ['manuscript/panel.png', '../escape.png'])
            self.assertFalse((root / 'figures').exists())

    def test_symlink_target_cannot_overwrite_canonical_asset(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'Figures/manuscript').mkdir(parents=True)
            source = root / 'Figures/manuscript/panel.png'
            source.write_bytes(b'canonical')
            (root / 'figures').symlink_to(root / 'Figures', target_is_directory=True)
            with self.assertRaises(ValueError):
                SYNC.mirror_figures(root, ['manuscript/panel.png'])
            self.assertEqual(source.read_bytes(), b'canonical')

    def test_full_mirror_requires_complete_canonical_families(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'Figures/manuscript').mkdir(parents=True)
            with self.assertRaises(FileNotFoundError):
                SYNC.mirror_figures(root)
            self.assertFalse((root / 'figures').exists())

    def test_symlink_metadata_cannot_overwrite_canonical_asset(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'Figures/manuscript').mkdir(parents=True)
            (root / 'figures').mkdir()
            source = root / 'Figures/manuscript/panel.png'
            source.write_bytes(b'canonical')
            (root / 'figures/mirror_manifest.csv').symlink_to(source)
            with self.assertRaises(ValueError):
                SYNC.mirror_figures(root, ['manuscript/panel.png'])
            self.assertEqual(source.read_bytes(), b'canonical')

    def test_family_mirror_rejects_self_copy_before_writing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            canonical = root / 'Figures/multivariate_synthesis_by_cutoff'
            canonical.mkdir(parents=True)
            panel = canonical / 'panel.png'
            panel.write_bytes(b'canonical')
            with self.assertRaises(ValueError):
                mirror_figure_family_to_lowercase(article_root=root, uppercase_dir=canonical,
                                                 lowercase_dir=canonical, manifest_rows=[])
            self.assertEqual(panel.read_bytes(), b'canonical')

    def test_family_mirror_preserves_other_compatibility_assets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            canonical = root / 'Figures/multivariate_synthesis_by_cutoff'
            compatibility = root / 'figures/multivariate_synthesis_by_cutoff'
            canonical.mkdir(parents=True)
            compatibility.mkdir(parents=True)
            (canonical / 'panel.png').write_bytes(b'canonical')
            unmanaged = compatibility / 'unmanaged.png'
            unmanaged.write_bytes(b'preserve')
            rows = [{'target_path': 'Figures/multivariate_synthesis_by_cutoff/panel.png'}]
            mirror_figure_family_to_lowercase(article_root=root, uppercase_dir=canonical,
                                             lowercase_dir=compatibility, manifest_rows=rows)
            self.assertEqual((compatibility / 'panel.png').read_bytes(), b'canonical')
            self.assertEqual(unmanaged.read_bytes(), b'preserve')


if __name__ == '__main__':
    unittest.main()
