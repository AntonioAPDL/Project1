from pathlib import Path
import unittest

ROOT = Path('/data/muscat_data/jaguir26/project1_ucsc_phd')
TARGET = ROOT / 'R' / 'unified' / 'stages' / 'stage_data_prep_shared.R'


class DataStartUsgsFilterContractTest(unittest.TestCase):
    def test_data_start_filter_includes_usgs_as_core_input(self) -> None:
        text = TARGET.read_text(encoding='utf-8')
        self.assertIn('retros = normalizePath(shared_paths$retros, mustWork = FALSE),', text)
        self.assertIn('usgs = normalizePath(shared_paths$usgs, mustWork = FALSE)', text)


if __name__ == '__main__':
    unittest.main()
