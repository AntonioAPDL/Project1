"""Reporting contracts from frozen small text/CSV inputs; no fits or state loads."""
import copy
import csv
from decimal import Decimal
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / 'scripts/build_no_refit_reporting_metadata.py'
spec = importlib.util.spec_from_file_location('no_refit_reporting_metadata', SCRIPT)
reporting = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reporting)
REPORT = Path(os.environ.get('NO_REFIT_REPORTING_DIR', str(
    ROOT.parent / 'article/artifacts/no_refit_revision/reporting')))


def rows(data):
    return list(csv.DictReader(io.StringIO(data.decode())))


def parse_display(text):
    if text.startswith('1-'):
        match = re.fullmatch(r'1-(?:(\d+)\\times )?10\^\{(-?\d+)\}', text)
        if not match:
            raise AssertionError(text)
        return Decimal(1) - Decimal(match[1] or '1') * Decimal(10) ** int(match[2])
    fraction = re.fullmatch(r'\\frac\{(-?\d+)\}\{(\d+)\}', text)
    return Decimal(fraction[1]) / Decimal(fraction[2]) if fraction else Decimal(text)


class ReportingMetadataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs = {p.name: p.read_bytes() for p in (REPORT / 'inputs').iterdir() if p.is_file()}
        cls.products = reporting.derived_products(cls.inputs)

    def test_selected_dimensions_and_complete_feature_identity(self):
        self.assertEqual(len(rows(self.products['configured_settings.csv'])), 45)
        self.assertEqual(len(rows(self.products['reference_settings.csv'])), 5)
        dictionary = rows(self.products['feature_state_dictionary.csv'])
        self.assertEqual([int(r['state_index']) for r in dictionary], list(range(23, 35)))
        self.assertEqual(tuple(r['actual_feature_name'] for r in dictionary), reporting.EXPECTED_FEATURES)

    def test_relabelled_values_are_exact_original_numeric_strings(self):
        originals = {(r['covariate'], r['quantile']): r for r in rows(self.inputs['covariate_effects_summary.csv'])}
        derived = rows(self.products['corrected_endpoint_summaries.csv'])
        self.assertEqual(len(derived), 27)
        for row in derived:
            original = originals[(row['original_label'], row['quantile'])]
            self.assertEqual([row['center'], row['lower'], row['upper']],
                             [original['center'], original['q2_5'], original['q97_5']])
            self.assertEqual(row['source_sha256'], reporting.digest(self.inputs['covariate_effects_summary.csv']))
            self.assertEqual(row['time_index'], '12995')

    def test_engineered_labels_correct_without_inventing_missing_summaries(self):
        derived = rows(self.products['corrected_endpoint_summaries.csv'])
        self.assertEqual({r['actual_feature_name'] for r in derived if r['original_label'] == 'Intercept'}, {'PPT_sq'})
        self.assertEqual({r['actual_feature_name'] for r in derived if r['original_label'] == 'Lag1'}, {'SOIL_sq'})
        self.assertEqual({int(r['state_index']) for r in derived}, set(range(23, 32)))
        dictionary = rows(self.products['feature_state_dictionary.csv'])
        self.assertTrue(all(r['availability_status'] == 'unavailable_not_exported' for r in dictionary[-3:]))

    def test_exact_display_roundtrips_all_reference_settings(self):
        for row in rows(self.products['reference_settings.csv']):
            for key in (*reporting.STATE_KEYS, 'epsilon_effective', 'c'):
                self.assertEqual(parse_display(row[key + '_tex']), Decimal(row[key]))
        self.assertEqual(reporting.exact_tex('0.99999999'), '1-10^{-8}')
        self.assertEqual(reporting.exact_tex('0.9988'), r'1-12\times 10^{-4}')
        self.assertEqual(reporting.exact_tex('0.97'), r'1-3\times 10^{-2}')
        with self.assertRaisesRegex(ValueError, 'Nonfinite'):
            reporting.exact_tex('NaN')

    def test_gaussian_null_default_and_univariate_applicability_separate(self):
        configured = rows(self.products['configured_settings.csv'])
        gaussian = [r for r in configured if r['family'] == 'ndlm_main']
        self.assertEqual(len(gaussian), 10)
        for row in gaussian:
            self.assertEqual(row['epsilon_configured'], 'null')
            self.assertEqual(row['epsilon_effective'], row['history_n'])
            self.assertEqual(row['epsilon_status'], 'adapter_default_historical_T')
        for row in configured:
            if row['family'].endswith('univar'):
                self.assertEqual(row['epsilon_effective'], '')
                self.assertIn('not_applicable', row['epsilon_status'])

    def test_effective_discrepancy_discounts_are_exact_products(self):
        for row in rows(self.products['configured_settings.csv']):
            for key in ('df_t', 'df_s1', 'df_s2', 'df_s67'):
                if row['df_discrep']:
                    self.assertEqual(Decimal(row['effective_discrep_' + key]),
                                     Decimal(row['df_discrep']) * Decimal(row[key]))
                else:
                    self.assertEqual(row['effective_discrep_' + key], '')

    def test_unknown_source_labels_and_reordered_features_fail(self):
        corrupted = dict(self.inputs)
        corrupted['covariate_effects_summary.csv'] = corrupted['covariate_effects_summary.csv'].replace(b'"Intercept"', b'"Unknown"')
        with self.assertRaisesRegex(ValueError, 'Unrecognized original endpoint'):
            reporting.derived_products(corrupted)
        feature_rows = rows(self.inputs['feature_metadata.csv'])
        feature_rows[0], feature_rows[1] = feature_rows[1], feature_rows[0]
        corrupted = dict(self.inputs)
        corrupted['feature_metadata.csv'] = reporting.csv_bytes(feature_rows)
        with self.assertRaisesRegex(ValueError, 'feature order'):
            reporting.derived_products(corrupted)

    def test_duplicate_selected_identities_fail(self):
        records = json.loads(self.inputs['settings_records.json'])
        records[-1] = copy.deepcopy(records[0])
        corrupted = dict(self.inputs)
        corrupted['settings_records.json'] = reporting.json_bytes(records)
        with self.assertRaisesRegex(ValueError, 'Repeated reporting'):
            reporting.derived_products(corrupted)

    def test_existing_bundle_check_is_readonly(self):
        before = {str(p.relative_to(REPORT)): reporting.digest(p.read_bytes())
                  for p in REPORT.rglob('*') if p.is_file()}
        result = subprocess.run([sys.executable, '-B', str(SCRIPT), '--output-dir', str(REPORT), '--check'],
                                text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        after = {str(p.relative_to(REPORT)): reporting.digest(p.read_bytes())
                 for p in REPORT.rglob('*') if p.is_file()}
        self.assertEqual(before, after)

    def test_portable_replay_uses_standard_library_and_frozen_inputs(self):
        with tempfile.TemporaryDirectory(prefix='no_refit_reporting_replay_') as tmp:
            destination = Path(tmp) / 'derived'
            archived_script = REPORT / 'inputs/build_no_refit_reporting_metadata.py'
            self.assertEqual(archived_script.read_bytes(), SCRIPT.read_bytes())
            result = subprocess.run([sys.executable, '-B', '-S', str(archived_script), '--inputs-dir',
                                     str(REPORT / 'inputs'), '--output-dir', str(destination)],
                                    cwd=tmp, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            for relative in json.loads((REPORT / 'reporting_manifest.json').read_text())['files']:
                self.assertEqual((destination / relative).read_bytes(), (REPORT / relative).read_bytes(), relative)

    def test_scope_and_skip_records_do_not_claim_band_reconstruction(self):
        proof = json.loads(self.inputs['source_scope_proof.json'])
        self.assertTrue(proof['all_other_source_text_identical'])
        self.assertFalse(proof['new_fits'])
        self.assertFalse(proof['numerical_band_regeneration'])
        gates = json.loads(self.products['source_gates.json'])
        self.assertEqual(gates['N11b'], 'OPTIONAL_SKIPPED_MISSING_COVARIANCE')
        self.assertTrue(gates['displayed_base_rows_unchanged'])


if __name__ == '__main__':
    unittest.main()
