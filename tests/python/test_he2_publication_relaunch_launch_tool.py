from __future__ import annotations

import unittest
from pathlib import Path

from scripts.launch_he2_bayesian_publication_relaunch import DEFAULT_TEMPLATE, parse_args

ROOT = Path(__file__).resolve().parents[2]
ALL_CUTOFFS_TEMPLATE = ROOT / 'config' / 'he2_bayesian_publication_relaunch_exdqlm_multivar_keep_all_cutoffs_20260512.template.yaml'


class HE2PublicationRelaunchLaunchToolTests(unittest.TestCase):
    def test_parse_args_accepts_template_flag(self) -> None:
        args = parse_args(['--template', str(ALL_CUTOFFS_TEMPLATE), '--dry-run'])
        self.assertEqual(Path(args.template), ALL_CUTOFFS_TEMPLATE)
        self.assertTrue(args.dry_run)

    def test_parse_args_accepts_config_alias(self) -> None:
        args = parse_args(['--config', str(ALL_CUTOFFS_TEMPLATE), '--dry-run'])
        self.assertEqual(Path(args.template), ALL_CUTOFFS_TEMPLATE)
        self.assertTrue(args.dry_run)

    def test_parse_args_defaults_to_default_template(self) -> None:
        args = parse_args([])
        self.assertEqual(Path(args.template), DEFAULT_TEMPLATE)


if __name__ == '__main__':
    unittest.main()
