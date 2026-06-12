from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARTICLE_ROOT = ROOT / 'Evironmetrics---REVISED-DOC-Corrected'
AUDIT_MD = ARTICLE_ROOT / 'reports' / 'manuscript_asset_review' / 'CURRENT_MODEL_OUTPUT_WIRING_AUDIT.md'


def test_benchmark_table_is_not_marked_current_model_output_wired() -> None:
    subprocess.run(
        ['python3', str(ARTICLE_ROOT / 'scripts' / 'build_article_asset_review_report.py'), '--article-root', str(ARTICLE_ROOT)],
        cwd=ROOT,
        check=True,
    )
    text = AUDIT_MD.read_text()
    assert '| `tab:benchmark_crps_models` | Table 1 | `tables/generated_tex/benchmark_crps_main_table.tex` |' in text
    assert '| No | Generated from the frozen HE2 publication manifest plus the raw-baseline rows in the five authoritative exAL-M-T1 CRPS summaries. All nine Bayesian benchmark families are promoted onto the canonical 20260510 input-bundle contract; this is the final CRPS table source for the current publication snapshot.; now auto-included into TeX |' in text
