"""Shared utilities for CLAUDE.md management operations.

Re-exports from scripts/shared/utils.py so that operation modules
can use ``from .utils import ...`` without knowing the project
layout.
"""

import sys
from pathlib import Path

# Ensure shared scripts are on sys.path
_project_root = Path(__file__).parent.parent.parent.parent.parent
_scripts_path = _project_root / "scripts"
if not (_scripts_path / "shared" / "utils.py").exists():
    raise ImportError(
        f"Cannot find shared utils at {_scripts_path}. "
        "Verify operations/utils.py is in the expected "
        "directory depth."
    )
if str(_scripts_path) not in sys.path:
    sys.path.insert(0, str(_scripts_path))

from shared.utils import (  # noqa: E402, F401
    safe_json_load,
    to_kebab_case,
    validate_name,
    validate_description,
    validate_version,
    bump_version,
    parse_frontmatter,
    render_template,
    get_project_root,
    LOCATION_PATHS,
    get_location_path,
)

__all__ = [
    "safe_json_load",
    "to_kebab_case",
    "validate_name",
    "validate_description",
    "validate_version",
    "bump_version",
    "parse_frontmatter",
    "render_template",
    "get_project_root",
    "LOCATION_PATHS",
    "get_location_path",
]
