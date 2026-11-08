"""Active routing and publication guards without changing repositories or refs."""
from __future__ import annotations

import argparse
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import article_repository_binding as binding


def load_script(name):
    spec = importlib.util.spec_from_file_location('_binding_test_' + name, ROOT / 'scripts' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ArticleRepositoryBindingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.workflow = Path(self.temp.name)
        self.config = self.workflow / binding.BINDING_RELATIVE_PATH
        self.config.parent.mkdir()
        self.payload = {
            'schema_version': 1,
            'active_article_directory': 'Evironmetrics----Corrected-3',
            'expected_origin': 'https://github.com/AntonioAPDL/Evironmetrics----Corrected-3.git',
            'submitted_archive_directory': 'Evironmetrics---REVISED-DOC-Corrected-2',
            'root_override_environment': 'ENVIRONMETRICS_ARTICLE_ROOT',
        }
        self.config.write_text(json.dumps(self.payload))
        self.article = self.workflow / self.payload['active_article_directory']
        self.article.mkdir()
        self.env = patch.dict(os.environ, {}, clear=False)
        self.env.start()
        self.addCleanup(self.env.stop)
        os.environ.pop('ENVIRONMETRICS_ARTICLE_ROOT', None)

    def git_identity(self, _root, *args):
        if args == ('rev-parse', '--show-toplevel'):
            return str(self.article)
        if args == ('remote', 'get-url', '--all', 'origin'):
            return self.payload['expected_origin']
        if args == ('remote', 'get-url', '--push', '--all', 'origin'):
            return 'git@github.com:AntonioAPDL/Evironmetrics----Corrected-3.git'
        raise AssertionError(args)

    def test_deployed_binding_is_exact_approved_repository(self):
        deployed = binding.load_article_binding(ROOT)
        self.assertEqual(deployed, self.payload)

    def test_default_env_and_explicit_routing_have_defined_precedence(self):
        self.assertEqual(binding.active_article_root(self.workflow), self.article)
        os.environ['ENVIRONMETRICS_ARTICLE_ROOT'] = str(self.workflow / 'environment')
        self.assertEqual(binding.active_article_root(self.workflow), self.workflow / 'environment')
        self.assertEqual(binding.active_article_root(self.workflow, self.workflow / 'explicit'), self.workflow / 'explicit')

    def test_missing_active_checkout_never_falls_back_to_submitted_archive(self):
        self.article.rmdir()
        archive = self.workflow / self.payload['submitted_archive_directory']
        archive.mkdir()
        self.assertEqual(binding.active_article_root(self.workflow), self.article)
        with self.assertRaises(FileNotFoundError):
            binding.active_article_root(self.workflow, require_exists=True)
        with patch.object(binding, '_git_read') as git_read:
            with self.assertRaises(FileNotFoundError):
                binding.assert_article_write_target(workflow_root=self.workflow)
            git_read.assert_not_called()

    def test_invalid_binding_schema_and_child_paths_fail_closed(self):
        for value in ('../archive', '/tmp/article', '.', '..', ''):
            self.config.write_text(json.dumps({**self.payload, 'active_article_directory': value}))
            with self.subTest(value=value), self.assertRaises(ValueError):
                binding.load_article_binding(self.workflow)
        self.config.write_text(json.dumps({**self.payload, 'schema_version': 2}))
        with self.assertRaisesRegex(ValueError, 'schema'):
            binding.load_article_binding(self.workflow)

    def test_supported_remote_forms_identify_one_github_repository(self):
        expected = 'github.com/antonioapdl/evironmetrics----corrected-3'
        for value in (self.payload['expected_origin'],
                      'git@github.com:AntonioAPDL/Evironmetrics----Corrected-3.git',
                      'ssh://git@github.com/AntonioAPDL/Evironmetrics----Corrected-3.git',
                      'https://user:secret@github.com/AntonioAPDL/Evironmetrics----Corrected-3.git'):
            with self.subTest(value=value):
                self.assertEqual(binding.normalized_origin(value), expected)
        for value in ('/tmp/article', 'file:///tmp/article', 'https://example.org/owner/repo',
                      'https://github.com/owner/repo/extra', 'https://github.com/../repo'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                binding.normalized_origin(value)

    def test_guard_accepts_equivalent_fetch_and_push_origins_without_mutation(self):
        before = sorted(self.workflow.rglob('*'))
        with patch.object(binding, '_git_read', side_effect=self.git_identity) as read:
            self.assertEqual(binding.assert_article_write_target(workflow_root=self.workflow), self.article)
        self.assertEqual(read.call_count, 3)
        self.assertEqual(before, sorted(self.workflow.rglob('*')))

    def test_submitted_archive_is_rejected_even_with_override_before_git_reads(self):
        archive = self.workflow / self.payload['submitted_archive_directory']
        archive.mkdir()
        with patch.object(binding, '_git_read') as read:
            with self.assertRaisesRegex(ValueError, 'submitted article archive'):
                binding.assert_article_write_target(archive, self.workflow)
            read.assert_not_called()

    def test_workflow_git_ancestor_cannot_masquerade_as_article_repository(self):
        with patch.object(binding, '_git_read', return_value=str(self.workflow)):
            with self.assertRaisesRegex(ValueError, 'independent repository root'):
                binding.assert_article_write_target(workflow_root=self.workflow)

    def test_wrong_owner_fetch_push_or_additional_push_target_is_rejected(self):
        for key in ('fetch', 'push', 'additional_push'):
            def mismatch(root, *args):
                value = self.git_identity(root, *args)
                if key == 'fetch' and args == ('remote', 'get-url', '--all', 'origin'):
                    return 'https://github.com/SomeoneElse/Evironmetrics----Corrected-3.git'
                if key == 'push' and '--push' in args:
                    return 'git@github.com:AntonioAPDL/Evironmetrics---REVISED-DOC-Corrected-2.git'
                if key == 'additional_push' and '--push' in args:
                    return value + '\nhttps://github.com/SomeoneElse/other.git'
                return value
            with self.subTest(key=key), patch.object(binding, '_git_read', side_effect=mismatch):
                with self.assertRaisesRegex(ValueError, 'configured active repository'):
                    binding.assert_article_write_target(workflow_root=self.workflow)

    def test_remote_errors_do_not_reveal_credentials(self):
        def invalid(root, *args):
            if args == ('rev-parse', '--show-toplevel'):
                return str(self.article)
            return 'https://token:private-secret@example.org/owner/repo.git'
        with patch.object(binding, '_git_read', side_effect=invalid):
            with self.assertRaises(ValueError) as result:
                binding.assert_article_write_target(workflow_root=self.workflow)
        self.assertNotIn('private-secret', str(result.exception))

    def test_cli_defaults_and_explicit_historical_reads_do_not_require_git(self):
        with patch.object(sys, 'argv', ['binding', '--workflow-root', str(self.workflow)]), \
                patch.object(binding, '_git_read') as git_read, contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(binding.main(), 0)
            self.assertEqual(out.getvalue().strip(), str(self.article))
            git_read.assert_not_called()
        archive = self.workflow / self.payload['submitted_archive_directory']
        with patch.object(sys, 'argv', ['binding', '--workflow-root', str(self.workflow), '--article-root', str(archive)]), \
                contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(binding.main(), 0)
            self.assertEqual(out.getvalue().strip(), str(archive))

    def test_current_contract_imports_only_configured_active_parser(self):
        scripts = self.article / 'scripts'
        scripts.mkdir()
        exports = ('active_tex', 'normalized_text', 'has_concepts', 'has_label',
                   'in_order', 'cited_url', 'structure_checks', 'scientific_checks')
        (scripts / 'manuscript_text_contract.py').write_text('\n'.join(
            f'def {name}(*args, **kwargs): return "active-parser"' for name in exports))
        archive = self.workflow / self.payload['submitted_archive_directory'] / 'scripts'
        archive.mkdir(parents=True)
        (archive / 'manuscript_text_contract.py').write_text('raise RuntimeError("submitted parser must not load")')
        os.environ['ENVIRONMETRICS_ARTICLE_ROOT'] = str(self.article)
        module = load_script('current_article_contract')
        self.assertEqual(module._MODULE_PATH, scripts / 'manuscript_text_contract.py')
        for name in exports:
            self.assertEqual(getattr(module, name)(), 'active-parser')

    def test_publication_sync_checks_target_before_reading_or_writing_outputs(self):
        module = load_script('sync_he3_ablation_article_tables')
        args = argparse.Namespace(article_root=self.article)
        with patch.object(module, 'parse_args', return_value=args), \
                patch.object(module, 'assert_article_write_target', side_effect=ValueError('wrong target')) as guard, \
                patch.object(module, 'load_he3_long') as read:
            with self.assertRaisesRegex(ValueError, 'wrong target'):
                module.main()
            guard.assert_called_once_with(self.article, module.ROOT)
            read.assert_not_called()

    def test_finalizer_rejects_sealed_submitted_target_without_rewriting_configuration(self):
        module = load_script('finalize_he3_exdqlm_ablation')
        metadata = {'article_sync': {'article_root': str(self.workflow / self.payload['submitted_archive_directory'])}}
        original = json.dumps(metadata, sort_keys=True)
        with patch.object(module, 'assert_article_write_target', side_effect=ValueError('submitted archive')), \
                patch.object(module, 'run_cmd') as run:
            with self.assertRaisesRegex(ValueError, 'submitted archive'):
                module.ensure_article_sync(self.workflow, metadata, True, [])
            run.assert_not_called()
        self.assertEqual(json.dumps(metadata, sort_keys=True), original)


if __name__ == '__main__':
    unittest.main()
