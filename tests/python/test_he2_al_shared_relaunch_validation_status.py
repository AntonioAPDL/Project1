from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / 'scripts' / 'build_he2_al_shared_relaunch_validation_status.py'


def _load_module():
    spec = importlib.util.spec_from_file_location('he2_al_validation_status', SCRIPT)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class He2AlSharedRelaunchValidationStatusTests(unittest.TestCase):
    def test_payload_reflects_validated_univar_and_prodclone_multivar_state(self) -> None:
        module = _load_module()
        payload = module.build_payload()
        univar = payload['families']['dqlm_univar_al']
        self.assertEqual(univar['status'], 'validated')
        self.assertTrue(univar['ready_for_launch_after_validation'])
        self.assertEqual(univar['selected_rows'], 5)
        self.assertEqual(univar['smoke_runs_passed'], 8)
        self.assertEqual(univar['smoke_runs_skipped'], 3)

        for family in ('dqlm_multivar_al_keep', 'dqlm_multivar_al_drop'):
            row = payload['families'][family]
            self.assertIn(row['status'], {'prodclone_running', 'prodclone_passed', 'prodclone_failed', 'not_validated'})
            if row['status'].startswith('prodclone_'):
                prodclone = row['prodclone']
                self.assertIn(prodclone['status'], {'running', 'passed', 'failed'})
                self.assertTrue(prodclone['fit_artifact_present'])
                self.assertIsNotNone(prodclone['latest_fit_iter'])


if __name__ == '__main__':
    unittest.main()
