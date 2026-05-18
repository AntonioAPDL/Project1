from __future__ import annotations

import csv
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'reports' / 'he2_exal_keep_output_quality_audit_20260517'


def test_keep_output_quality_audit_marks_run_side_problem() -> None:
    subprocess.run(['python3', 'scripts/build_he2_exal_keep_output_quality_audit.py'], cwd=ROOT, check=True)

    summary = json.loads((OUT / 'summary.json').read_text())
    assert summary['representative_article_is_synced_to_runtime'] is True
    assert summary['article_staleness_is_primary_explanation'] is False
    assert summary['likely_primary_explanation'] == 'run_side_output_quality_issue'
    assert summary['all_five_cutoffs_show_severe_or_worse_issue'] is True

    rows = list(csv.DictReader((OUT / 'cutoff_quality_matrix.csv').open()))
    representative = next(r for r in rows if r['cutoff'] == '2022-12-25')
    assert float(representative['synth_mean_crps']) > 1e6
    assert representative['quality_class'] == 'extreme_run_side_issue'
