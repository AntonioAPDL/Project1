from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
os.sys.path.insert(0, str(ROOT / 'scripts'))

from build_he2_exdqlm_multivar_keep_rerun_contract import (  # noqa: E402
    DEFAULT_OUT_ROOT,
    FAMILY,
    QUARANTINED_BUILDERS,
    build_outputs,
    write_outputs,
)


class He2ExdqlmMultivarKeepRerunContractTests(unittest.TestCase):
    def test_build_outputs_freezes_five_cutoff_publication_winners(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            payload = build_outputs(out_root=Path(tmpdir))

        spec_rows = payload['spec_rows']
        self.assertEqual(len(spec_rows), 5)
        self.assertEqual({row['family'] for row in spec_rows}, {FAMILY})
        by_cutoff = {row['cutoff']: row for row in spec_rows}
        self.assertEqual(by_cutoff['20210123']['effective_epsilon_fit'], 360.0)
        self.assertEqual(by_cutoff['20211112']['effective_epsilon_fit'], 180.0)
        self.assertEqual(by_cutoff['20211221']['effective_epsilon_fit'], 1.0)
        self.assertEqual(by_cutoff['20220511']['effective_epsilon_fit'], 180.0)
        self.assertEqual(by_cutoff['20221225']['effective_epsilon_fit'], 360.0)
        self.assertEqual(by_cutoff['20221225']['discount_set'], 'set09')
        self.assertEqual(by_cutoff['20221225']['discount_set_index'], 9)
        self.assertEqual(by_cutoff['20221225']['discount_source_epsilon_label'], 'eps360cf1')
        self.assertIn('debug_v8_matrix epsilon label/value differ', by_cutoff['20221225']['epsilon_alignment_note'])
        self.assertEqual(by_cutoff['20221225']['df_s1'], 0.9998)
        self.assertEqual(by_cutoff['20221225']['df_discrep'], 0.998)
        self.assertEqual(payload['summary']['counts']['cutoffs'], ['20210123', '20211112', '20211221', '20220511', '20221225'])

    def test_write_outputs_materializes_contract_docs_and_frozen_source_configs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out_root = Path(tmpdir) / 'contract'
            payload = write_outputs(out_root=out_root)

            self.assertTrue((out_root / 'exdqlm_multivar_keep_rerun_spec_freeze.csv').exists())
            self.assertTrue((out_root / 'canonical_input_bundle_contract.csv').exists())
            self.assertTrue((out_root / 'summary.json').exists())
            self.assertTrue((out_root / 'HE2_EXDQLM_MULTIVAR_KEEP_RERUN_CONTRACT_20260516.md').exists())
            self.assertTrue((out_root / 'README.md').exists())

            launcher_text = (out_root / 'HE2_EXDQLM_MULTIVAR_KEEP_RERUN_CONTRACT_20260516.md').read_text(encoding='utf-8')
            self.assertIn('VALIDATE_ONLY', launcher_text)
            self.assertIn('20221225 nuance', launcher_text)
            for builder in QUARANTINED_BUILDERS:
                self.assertIn(builder, launcher_text)

            frozen_paths = [Path(row['frozen_resolved_config_path']) for row in payload['spec_rows']]
            self.assertEqual(len(frozen_paths), 5)
            for frozen in frozen_paths:
                self.assertTrue(frozen.exists())


if __name__ == '__main__':
    unittest.main()
