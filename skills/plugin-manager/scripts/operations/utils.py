"""Shared utilities for plugin-manager operations.

Re-exports from scripts/shared/utils.py for convenient access
within the operations package.
"""

import sys
from pathlib import Path

# Add shared scripts to path
_project_root = Path(__file__).parent.parent.parent.parent.parent
_scripts_path = _project_root / "scripts"
if not (_scripts_path / "shared" / "utils.py").exists():
    raise ImportError(
        f"Cannot find shared utils at {_scripts_path}. "
        "Verify operations/utils.py is in the expected "
        "directory depth."
    )
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
