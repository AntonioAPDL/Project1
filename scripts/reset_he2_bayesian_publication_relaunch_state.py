#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from he2_publication_relaunch_lib import reset_campaign_state

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEMPLATE = ROOT / 'config' / 'he2_bayesian_publication_relaunch_20260510.template.yaml'


def load_yaml(path: Path) -> dict:
    with path.open('r', encoding='utf-8') as handle:
        return yaml.safe_load(handle) or {}


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description='Archive stale HE2 Bayesian publication relaunch runtime state and reset matrix status for a clean restart.')
    ap.add_argument('--template', default=str(DEFAULT_TEMPLATE))
    ap.add_argument('--reset-tag', default='')
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    template_path = Path(args.template).resolve()
    template = load_yaml(template_path)
    campaign = template.get('campaign', {})
    matrix_dir = Path(campaign['matrix_dir']).resolve()
    artifact_root = Path(campaign['artifact_root']).resolve()
    summary = reset_campaign_state(matrix_dir, artifact_root, reset_tag=args.reset_tag or None)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
