"""Load the standalone article's shared, pure LaTeX contract utilities."""
from __future__ import annotations

import importlib.util
from pathlib import Path

_MODULE_PATH = Path(__file__).resolve().parents[1] / 'Evironmetrics---REVISED-DOC-Corrected-2/scripts/manuscript_text_contract.py'
_SPEC = importlib.util.spec_from_file_location('_current_article_text_contract', _MODULE_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError(f'Cannot load article text contract: {_MODULE_PATH}')
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
active_tex = _MODULE.active_tex
normalized_text = _MODULE.normalized_text
has_concepts = _MODULE.has_concepts
has_label = _MODULE.has_label
in_order = _MODULE.in_order
cited_url = _MODULE.cited_url
structure_checks = _MODULE.structure_checks

scientific_checks = _MODULE.scientific_checks
