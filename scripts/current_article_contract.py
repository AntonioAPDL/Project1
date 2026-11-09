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
publication_views = _MODULE.publication_views
publication_checks = _MODULE.publication_checks
publication_text_checks = _MODULE.publication_text_checks


def canonical_method_label(label: str) -> str:
    """Map the five reader-facing reference names to unchanged result identities."""
    return {
        'GloFAS': 'RAW-GLOFAS',
        'NWS': 'RAW-NWS',
        'Seasonal climatology': 'CLIM-SEASONAL',
        'Persistence': 'PERSISTENCE',
        'GloFAS EMOS': 'EMOS-GLOFAS',
    }.get(label, label)


TABLE_ALIASES = {
    'tab:benchmark_crps_models': 'tab:crps_all_origins',
    'tab:benchmark_crps_models_nws_horizon': 'tab:crps_all_origins',
    'tab:he3_ablation_crps': 'tab:component_comparison',
    'tab:he3_ablation_crps_nws_horizon': 'tab:component_comparison',
    'tab:he4_quantile_check_loss': 'tab:quantile_check_loss',
}


def active_table_path(article_root: Path, label: str, document: str | None = None, scope: str | None = None) -> Path:
    import json
    root = Path(article_root).resolve()
    if (root / 'PUBLICATION_PACKAGE.json').is_file():
        # The active inventory, unlike the retained evidence manifest, describes
        # what a reader actually receives. The article helper enforces its graph.
        import sys
        sys.path.insert(0, str(root / 'scripts'))
        from publication_package import submitted_asset_path
        return submitted_asset_path(root, TABLE_ALIASES.get(label, label), document=document, scope=scope)
    manifest = json.loads((root / 'MANUSCRIPT_ASSET_MANIFEST.json').read_text())
    path = (root / manifest['tables'][label]['table_tex_path']).resolve()
    if not path.is_relative_to(root) or path not in included_tex_paths(root):
        raise ValueError(f'Table is not an active manuscript dependency: {label}')
    return path


def horizon_table_rows(path: Path, horizon_days: int, *, expected_numeric_cells: int = 5) -> dict[str, list[float]]:
    """Read one explicit horizon panel without silently overwriting method rows.

    The new display contains both horizons. Archived single-panel sources remain
    readable, but a repeated row is always an error, including in old displays.
    """
    import re
    rows: dict[str, list[float]] = {}
    current: int | None = None
    text = Path(path).read_text(encoding='utf-8')
    has_panels = bool(re.search(r'%\s*horizon_days\s*=\s*\d+', text))
    for raw in text.splitlines():
        marker = re.search(r'%\s*horizon_days\s*=\s*(\d+)', raw)
        if marker:
            current = int(marker.group(1))
            continue
        if has_panels and current != horizon_days:
            continue
        line = raw.strip()
        if '&' not in line or line.startswith('%') or '\\multicolumn' in line:
            continue
        parts = [part.strip() for part in line.rstrip('\\').split('&')]
        if len(parts) != expected_numeric_cells + 1:
            continue
        def plain(cell: str) -> str:
            previous = None
            while previous != cell:
                previous = cell
                cell = re.sub(r'\\(?:textbf|textit|texttt|emph)\{([^{}]+)\}', r'\1', cell)
            return cell.replace('$', '').replace('\\,', ' ').strip()
        label = canonical_method_label(plain(parts[0]))
        if label in {'Model', 'Method', 'Model label', 'Ablation model'}:
            continue
        try:
            values = [float(plain(cell)) for cell in parts[1:]]
        except ValueError:
            continue
        if label in rows:
            raise ValueError(f'Duplicate method/horizon row: {label}/{horizon_days}')
        rows[label] = values
    if has_panels and not rows:
        raise ValueError(f'Missing horizon panel: {horizon_days}')
    return rows
