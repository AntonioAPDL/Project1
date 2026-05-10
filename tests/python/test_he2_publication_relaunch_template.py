from __future__ import annotations

import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / 'config' / 'he2_bayesian_publication_relaunch_20260510.template.yaml'


class HE2PublicationRelaunchTemplateTests(unittest.TestCase):
    def test_template_exists_and_has_five_cutoffs(self) -> None:
        self.assertTrue(TEMPLATE.exists())
        payload = yaml.safe_load(TEMPLATE.read_text(encoding='utf-8')) or {}
        self.assertEqual(len(payload['campaign']['cutoffs']), 5)
        self.assertEqual(len(payload['bundles']['cutoffs']), 5)
        self.assertEqual(payload['campaign']['campaign_spec_id'], 'he2pubgdpc1r1')
        self.assertEqual(payload['validation']['fit_smoke_family'], 'ndlm_univar_keep')
        self.assertEqual(payload['validation']['fit_smoke_cutoff'], '20210123')


if __name__ == '__main__':
    unittest.main()
