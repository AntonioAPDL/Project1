from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / 'reports' / 'he2_exal_m_t1_end_to_end_audit_20221225_20260518'


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    out_dir = OUT_DIR
    manifest_path = out_dir / 'audit_manifest.json'
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {'status': {}}

    checks = {
        'scale_contract_audit': out_dir / 'scale_contract_inventory.csv',
        'pre_fit_lineage_audit': out_dir / 'prefit_history_lineage_reference_dates.csv',
        'object_semantics_decomposition': out_dir / 'object_semantics_codepath.csv',
        'historical_window_comparison_audit': ROOT / 'reports' / 'he2_exal_m_t1_hist_last200_location_review_20260518' / 'history_window_usgs_location_mean_dynamics_central_log1p.png',
        'post_stage_contract_audit': ROOT / 'reports' / 'he2_post_scale_and_usgs_quantile_audit_20221225_20260518' / 'HE2_POST_SCALE_AND_USGS_QUANTILE_AUDIT_20221225_20260518.md',
        'final_diagnosis_memo': out_dir / 'HE2_EXAL_M_T1_FINAL_DIAGNOSIS_MEMO_20260518.md',
    }

    rows: list[dict[str, object]] = []
    updated = dict(manifest.get('status', {}))
    for key, path in checks.items():
        exists = path.exists()
        prev = updated.get(key, 'pending')
        if exists and prev == 'pending':
            updated[key] = 'done'
        elif exists and prev == 'in_progress':
            updated[key] = 'done'
        rows.append({
            'workstream_key': key,
            'artifact_path': str(path),
            'artifact_exists': exists,
            'status': updated.get(key, prev),
        })

    manifest['status'] = updated
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
    write_csv(out_dir / 'workstream_status.csv', rows, ['workstream_key', 'artifact_path', 'artifact_exists', 'status'])
    (out_dir / 'status_summary.json').write_text(json.dumps({'status': updated}, indent=2) + '\n')


if __name__ == '__main__':
    main()
