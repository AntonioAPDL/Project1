from __future__ import annotations

import importlib
import os
from pathlib import Path
from typing import Any, Dict, Iterable

import yaml


def _resolve_path(value: str | Path | None, base: Path) -> Path | None:
    if value is None:
        return None
    p = Path(value).expanduser()
    if not p.is_absolute():
        p = (base / p).resolve()
    return p


def load_paths(config_path: str | Path | None = None) -> Dict[str, Any]:
    """Load path configuration and resolve to absolute Paths."""
    if config_path is None:
        repo_root = Path.cwd()
        config_path = Path(
            os.environ.get("PROJECT1_UCSC_CONFIG", repo_root / "config" / "paths.yaml")
        )
    config_path = Path(config_path).expanduser().resolve()
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    raw = yaml.safe_load(config_path.read_text()) or {}

    raw_repo = raw.get("repo_root")
    if raw_repo:
        repo_root = Path(raw_repo)
        if not repo_root.is_absolute():
            repo_root = (config_path.parent / repo_root).resolve()
    else:
        repo_root = config_path.parent.parent.resolve()

    data_root = _resolve_path(raw.get("data_root", "."), repo_root)
    output_root = _resolve_path(raw.get("output_root", "outputs"), repo_root)
    logs_root = _resolve_path(raw.get("logs_root", "logs"), repo_root)

    extra_roots_raw = raw.get("extra_data_roots", []) or []
    extra_roots = [_resolve_path(p, repo_root) for p in extra_roots_raw]

    return {
        "config_path": config_path,
        "raw": raw,
        "repo_root": repo_root,
        "data_root": data_root,
        "output_root": output_root,
        "logs_root": logs_root,
        "extra_data_roots": extra_roots,
    }


def ensure_dirs(*paths: Iterable[str | Path | None]) -> None:
    for path in paths:
        if path is None:
            continue
        Path(path).mkdir(parents=True, exist_ok=True)


def is_fast_mode(default: bool = True) -> bool:
    value = os.environ.get("FAST_MODE")
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def optional_import(module_name: str):
    try:
        return importlib.import_module(module_name)
    except Exception as exc:  # pragma: no cover - runtime helper
        print(f"[WARN] optional import failed: {module_name}: {exc}")
        return None
