from __future__ import annotations

import csv
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'reports' / 'he2_revised_doc_rewire_audit_20260517'


def test_revised_doc_rewire_audit_flags_renderer_and_benchmark_hold() -> None:
    subprocess.run(['python3', 'scripts/build_he2_revised_doc_rewire_audit.py'], cwd=ROOT, check=True)

    summary = json.loads((OUT / 'rewire_summary.json').read_text())
    assert summary['benchmark_table_should_be_refreshed_now'] is False
    assert summary['historical_support_scale_contract_suspect'] is False
    assert summary['recommended_next_phase'] == 'model_family_quality_audit_and_rerun_gate_review'

    rows = list(csv.DictReader((OUT / 'manuscript_asset_tracker.csv').open()))
    synth1 = next(r for r in rows if r['label'] == 'fig:synth1')
    dry = next(r for r in rows if r['label'] == 'fig:dry_quantile')
    benchmark = next(r for r in rows if r['label'] == 'tab:benchmark_crps_models')

    assert synth1['current_status'] == 'synced_to_latest_keep_output_but_output_quality_flagged'
    assert dry['action_gate'] == 'trusted_after_rerender'
    assert benchmark['current_status'] == 'frozen_non_authoritative_benchmark_source'

    families = list(csv.DictReader((OUT / 'generated_family_tracker.csv').open()))
    hist = next(r for r in families if r['generated_family'] == 'historical_support_from_current_models')
    assert hist['status'] == 'synced_with_repaired_scale_contract'
