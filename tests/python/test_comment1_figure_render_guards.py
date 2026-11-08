from __future__ import annotations
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class FrozenRenderGuards(unittest.TestCase):
    def test_changed_snapshot_input_fails_before_creating_output(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            mid = 'exdqlm_multivar_synth_keep'
            run = base / 'run'
            source = run / 'post/outputs/frozen-run'
            files = [source / f'{mid}_cutoff_window_{tail}' for tail in ['quantiles.csv', 'sample_subset.csv']]
            files += [run / 'post/inputs' / name for name in ['nws_post_adapter.csv', 'glofas_post_adapter.csv', 'retros_post_adapter.csv']]
            files += [run / 'post/cache' / f'{mid}__mode-keep__synth_multivar_{segment}_log1p.rds' for segment in ['hist', 'forecast']]
            for path in files:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b'frozen numerical input')
            entries = [dict(path=str(path), exists=True, sha256=hashlib.sha256(path.read_bytes()).hexdigest()) for path in files]
            files[-1].write_bytes(b'changed numerical input')
            snapshot = base / 'snapshot.json'
            snapshot.write_text(json.dumps(dict(files=entries, selected_runs=[dict(cutoff='20221225', label='exAL-M-T1', run_id='frozen-run',
                outputs_dir=str(source), artifact_run_root=str(run), model_id=mid)])))
            out = base / 'output'
            result = subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/render_comment1_publication_figures.py'),
                '--snapshot', str(snapshot), '--output-root', str(out), '--cutoffs', '20221225', '--skip-context'], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('differs from frozen snapshot', result.stderr)
            self.assertFalse(out.exists())

    def test_changed_snapshot_document_blocks_promotion_before_writes(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            snapshot = base / 'snapshot.json'
            snapshot.write_text('{}')
            old_digest = hashlib.sha256(snapshot.read_bytes()).hexdigest()
            snapshot.write_text('{"changed": true}')
            render = base / 'render'
            render.mkdir()
            (render / 'render_manifest.json').write_text(json.dumps(dict(snapshot=str(snapshot), snapshot_sha256=old_digest)))
            article = base / 'article'
            article.mkdir()
            result = subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/promote_comment1_figure_assets.py'),
                '--render-root', str(render), '--article-root', str(article)], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('snapshot content changed', result.stderr)
            self.assertEqual(list(article.iterdir()), [])


if __name__ == '__main__':
    unittest.main()
