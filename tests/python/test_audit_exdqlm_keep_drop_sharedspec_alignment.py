from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
os.sys.path.insert(0, str(ROOT / 'scripts'))

from audit_exdqlm_keep_drop_sharedspec_alignment import build_payload, write_outputs  # noqa: E402


class AuditExdqlmKeepDropSharedspecAlignmentTests(unittest.TestCase):
    def test_build_payload_reports_full_alignment(self) -> None:
        payload = build_payload()
        self.assertTrue(payload['all_bundle_fields_aligned'])
        self.assertTrue(payload['all_spec_fields_aligned'])
        self.assertEqual(len(payload['cutoffs']), 5)
        for row in payload['cutoffs']:
            self.assertTrue(row['bundle_alignment_passed'])
            self.assertTrue(row['spec_alignment_passed'])
            self.assertEqual(row['expected_differences']['manuscript_label']['keep'], 'exAL-M-T1')
            self.assertEqual(row['expected_differences']['manuscript_label']['drop'], 'exAL-M-T0')
            self.assertEqual(row['expected_differences']['forecast_transfer_mode']['keep'], 'keep')
            self.assertEqual(row['expected_differences']['forecast_transfer_mode']['drop'], 'drop')

    def test_write_outputs_materializes_alignment_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out_root = Path(tmpdir) / 'audit'
            payload = write_outputs.__globals__.copy()
            # Rebind output paths without mutating module globals globally.
            from audit_exdqlm_keep_drop_sharedspec_alignment import OUT_JSON, OUT_MD, OUT_ROOT  # noqa: E402

            original_root, original_json, original_md = OUT_ROOT, OUT_JSON, OUT_MD
            try:
                import audit_exdqlm_keep_drop_sharedspec_alignment as mod  # noqa: E402

                mod.OUT_ROOT = out_root
                mod.OUT_JSON = out_root / 'keep_drop_sharedspec_alignment.json'
                mod.OUT_MD = out_root / 'KEEP_DROP_SHAREDSPEC_ALIGNMENT_20260516.md'
                result = mod.write_outputs()
                self.assertTrue(mod.OUT_JSON.exists())
                self.assertTrue(mod.OUT_MD.exists())
                self.assertTrue(result['all_bundle_fields_aligned'])
                self.assertTrue(result['all_spec_fields_aligned'])
            finally:
                import audit_exdqlm_keep_drop_sharedspec_alignment as mod  # noqa: E402

                mod.OUT_ROOT = original_root
                mod.OUT_JSON = original_json
                mod.OUT_MD = original_md


if __name__ == '__main__':
    unittest.main()
