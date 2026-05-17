from __future__ import annotations

import json
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
REPORT_ROOT = ROOT / 'reports' / 'he2_al_shared_relaunch_plan_20260517'
REPORT_MD = REPORT_ROOT / 'HE2_AL_SHARED_RELAUNCH_PACKAGES_20260517.md'
READINESS_JSON = REPORT_ROOT / 'readiness_summary.json'
SCOPE_CSV = REPORT_ROOT / 'al_scope_matrix.csv'
TEMPLATE_KEEP = ROOT / 'config' / 'he2_bayesian_publication_relaunch_dqlm_multivar_al_keep_all_cutoffs_sharedspec_20260517.template.yaml'


class He2AlSharedRelaunchPlanTests(unittest.TestCase):
    def test_report_artifacts_exist_and_reference_all_three_families(self) -> None:
        self.assertTrue(REPORT_MD.exists())
        self.assertTrue(READINESS_JSON.exists())
        self.assertTrue(SCOPE_CSV.exists())
        text = REPORT_MD.read_text(encoding='utf-8')
        self.assertIn('dqlm_multivar_al_keep', text)
        self.assertIn('dqlm_multivar_al_drop', text)
        self.assertIn('dqlm_univar_al', text)

    def test_readiness_summary_tracks_validator_summary_paths(self) -> None:
        payload = json.loads(READINESS_JSON.read_text(encoding='utf-8'))
        self.assertEqual(payload['shared_bundle_run_id'], '20260510_publication_shared_r01')
        self.assertEqual(payload['shared_data_start'], '1987-05-29')
        self.assertIn('dqlm_multivar_al_keep', payload['families'])
        self.assertIn('dqlm_univar_al', payload['families'])
        self.assertTrue(payload['families']['dqlm_multivar_al_keep']['template_exists'])

    def test_keep_template_still_uses_canonical_shared_bundle_root(self) -> None:
        payload = yaml.safe_load(TEMPLATE_KEEP.read_text(encoding='utf-8')) or {}
        self.assertEqual(
            payload['bundles']['artifact_root'],
            '/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510',
        )
        self.assertEqual(payload['bundles']['bundle_run_id'], '20260510_publication_shared_r01')
        self.assertEqual(payload['bundles']['data_start'], '1987-05-29')


if __name__ == '__main__':
    unittest.main()
