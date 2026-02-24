"""Shared utilities for agent-manager operations.

Re-exports from scripts/shared/utils.py so that operation
modules can import via a short path.
"""

import sys
from pathlib import Path

# Path layout:
#   skills/agent-manager/scripts/operations/utils.py  <- here
#   scripts/shared/utils.py                           <- target
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
    LOCATION_PATHS,
    bump_version,
    detect_project_context,
    get_location_path,
    get_project_root,
    infer_from_description,
    parse_frontmatter,
    render_template,
    safe_json_load,
    to_kebab_case,
    validate_description,
    validate_name,
    validate_version,
)

__all__ = [
    "LOCATION_PATHS",
    "bump_version",
    "detect_project_context",
    "get_location_path",
    "get_project_root",
    "infer_from_description",
    "parse_frontmatter",
    "render_template",
    "safe_json_load",
    "to_kebab_case",
    "validate_description",
    "validate_name",
    "validate_version",
]
