from __future__ import annotations

import subprocess
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from article_repository_binding import active_article_root

ROOT = Path(__file__).resolve().parents[2]
ARTICLE_ROOT = active_article_root(ROOT)
AUDIT_MD = ARTICLE_ROOT / 'reports' / 'manuscript_asset_review' / 'CURRENT_MODEL_OUTPUT_WIRING_AUDIT.md'


def test_benchmark_table_is_not_marked_current_model_output_wired() -> None:
    subprocess.run(
        ['python3', str(ARTICLE_ROOT / 'scripts' / 'build_article_asset_review_report.py'), '--article-root', str(ARTICLE_ROOT)],
        cwd=ROOT,
        check=True,
    )
    text = AUDIT_MD.read_text()
    row = next(line for line in text.splitlines() if line.startswith('| `tab:benchmark_crps_models` |'))
    cells = [cell.strip().strip('`') for cell in row.strip('|').split('|')]
    assert cells[1:3] == ['Table 1', 'tables/generated_tex/benchmark_crps_main_table.tex']
    assert 'artifacts/he2_publication_freeze/he2_bayesian_publication_manifest.csv' in cells[3]
    assert 'artifacts/five_cutoff_crps_validation_sources' in cells[3]
    assert cells[4] == 'No'
