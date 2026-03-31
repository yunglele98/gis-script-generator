"""Shared utilities for gis_codegen."""

import sys
from pathlib import Path
from types import ModuleType


def _load_toml_module() -> ModuleType | None:
    """Load tomllib (Python 3.11+) or tomli fallback."""
    try:
        import tomllib
        return tomllib
    except ImportError:
        pass
    try:
        import tomli as tomllib
        return tomllib
    except ImportError:
        return None


TOMLLIB = _load_toml_module()


def load_toml(path: Path) -> dict:
    if TOMLLIB is None:
        print(
            "[ERROR] TOML support requires Python 3.11+ or 'tomli' package.\n"
            "        Install with: pip install tomli",
            file=sys.stderr,
        )
        sys.exit(1)
    with open(path, "rb") as f:
        return TOMLLIB.load(f)
