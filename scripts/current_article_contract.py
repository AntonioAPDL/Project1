"""Load the standalone article's shared, pure LaTeX contract utilities."""
from __future__ import annotations

import importlib.util
from pathlib import Path

from article_repository_binding import active_article_root

_MODULE_PATH = active_article_root() / 'scripts/manuscript_text_contract.py'
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
included_tex_paths = _MODULE.included_tex_paths
manuscript_with_includes = _MODULE.manuscript_with_includes


def canonical_method_label(label: str) -> str:
    """Map the five reader-facing reference names to unchanged result identities."""
    return {
        'GloFAS': 'RAW-GLOFAS',
        'NWS': 'RAW-NWS',
        'Seasonal climatology': 'CLIM-SEASONAL',
        'Persistence': 'PERSISTENCE',
        'GloFAS EMOS': 'EMOS-GLOFAS',
    }.get(label, label)


def active_table_path(article_root: Path, label: str) -> Path:
    import json
    root = Path(article_root).resolve()
    manifest = json.loads((root / 'MANUSCRIPT_ASSET_MANIFEST.json').read_text())
    path = (root / manifest['tables'][label]['table_tex_path']).resolve()
    if not path.is_relative_to(root) or path not in included_tex_paths(root):
        raise ValueError(f'Table is not an active manuscript dependency: {label}')
    return path
