"""Shared utilities for Claude Code management operations.

Common functions used by both extension management and CLAUDE.md operations.
Re-exports from scripts/shared/utils.py for backward compatibility.
"""

import sys
from pathlib import Path

# Add shared scripts to path
_project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(_project_root / "scripts"))

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
