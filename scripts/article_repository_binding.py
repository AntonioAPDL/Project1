#!/usr/bin/env python3
"""Resolve the active article independently of historical execution records.

Read-only tools may inspect an explicit historical checkout. Publication writers
must additionally call ``assert_article_write_target`` before changing files.
No repository refs or files are changed by this module.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
from urllib.parse import urlsplit


WORKFLOW_ROOT = Path(__file__).resolve().parents[1]
BINDING_RELATIVE_PATH = 'config/article_repository_binding.json'


def load_article_binding(workflow_root: Path | None = None) -> dict:
    root = (workflow_root or WORKFLOW_ROOT).resolve()
    binding = json.loads((root / BINDING_RELATIVE_PATH).read_text())
    if binding.get('schema_version') != 1:
        raise ValueError('Unsupported active article binding schema')
    directory = binding.get('active_article_directory', '')
    if not directory or Path(directory).name != directory or directory in {'.', '..'}:
        raise ValueError('Active article directory must be one explicit child directory')
    if not binding.get('expected_origin'):
        raise ValueError('Expected article origin is required')
    if not binding.get('root_override_environment'):
        raise ValueError('Article root override environment name is required')
    return binding


def active_article_root(workflow_root: Path | None = None, override: Path | str | None = None,
                        *, require_exists: bool = False) -> Path:
    root = (workflow_root or WORKFLOW_ROOT).resolve()
    binding = load_article_binding(root)
    selected = override if override is not None else os.environ.get(binding['root_override_environment'])
    path = Path(selected).expanduser() if selected else root / binding['active_article_directory']
    path = path.resolve()
    if require_exists and not path.is_dir():
        raise FileNotFoundError(f'Active article checkout is unavailable: {path}')
    return path


def normalized_origin(origin: str) -> str:
    """Match SSH/HTTPS GitHub identities without exposing embedded credentials."""
    origin = origin.strip()
    scp = re.fullmatch(r'(?:[^/@:]+@)?([^/:]+):(.+)', origin)
    if scp and '://' not in origin:
        host, path = scp.groups()
    else:
        parsed = urlsplit(origin)
        if parsed.scheme not in {'https', 'ssh'} or not parsed.hostname:
            raise ValueError('Article origin must identify a supported remote repository')
        host, path = parsed.hostname, parsed.path
    path = path.strip('/').removesuffix('.git')
    if host.lower() != 'github.com' or not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', path):
        raise ValueError('Article origin must identify a GitHub owner/repository')
    if any(part in {'.', '..'} for part in path.split('/')):
        raise ValueError('Article origin must identify a GitHub owner/repository')
    return host.lower() + '/' + path.lower()


def _git_read(root: Path, *arguments: str) -> str:
    result = subprocess.run(['git', '-C', str(root), *arguments], check=False,
                            text=True, capture_output=True)
    if result.returncode:
        raise ValueError('Cannot verify article repository identity')
    return result.stdout.strip()


def assert_article_write_target(article_root: Path | str | None = None,
                                workflow_root: Path | None = None) -> Path:
    root = (workflow_root or WORKFLOW_ROOT).resolve()
    binding = load_article_binding(root)
    article = active_article_root(root, article_root, require_exists=True)
    if article.name == binding['submitted_archive_directory']:
        raise ValueError('The submitted article archive is not an active publication write target')
    top = Path(_git_read(article, 'rev-parse', '--show-toplevel')).resolve()
    if top != article:
        raise ValueError('Article target must be an independent repository root')
    expected = normalized_origin(binding['expected_origin'])
    fetch_origins = _git_read(article, 'remote', 'get-url', '--all', 'origin').splitlines()
    push_origins = _git_read(article, 'remote', 'get-url', '--push', '--all', 'origin').splitlines()
    if not fetch_origins or not push_origins or any(
            normalized_origin(origin) != expected for origin in (*fetch_origins, *push_origins)):
        raise ValueError('Article origin differs from the configured active repository')
    return article


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workflow-root', type=Path, default=WORKFLOW_ROOT)
    parser.add_argument('--article-root', type=Path)
    parser.add_argument('--check-write-target', action='store_true')
    args = parser.parse_args()
    path = (assert_article_write_target(args.article_root, args.workflow_root)
            if args.check_write_target else active_article_root(args.workflow_root, args.article_root))
    print(path)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
