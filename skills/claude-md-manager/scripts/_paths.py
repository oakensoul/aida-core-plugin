"""Path utilities for claude-md-manager scripts.

Sets up paths so that operations can import from scripts/shared/.
Also provides TEMPLATES_DIR for template rendering.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Directory layout:
#   skills/claude-md-manager/scripts/_paths.py   <- this file
#   skills/claude-md-manager/templates/           <- TEMPLATES_DIR
#   scripts/shared/utils.py                       <- shared utils

SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = SKILL_DIR.parent.parent
TEMPLATES_DIR = SKILL_DIR / "templates"

# Make shared utilities importable
_scripts_path = PROJECT_ROOT / "scripts"
if str(_scripts_path) not in sys.path:
    sys.path.insert(0, str(_scripts_path))
