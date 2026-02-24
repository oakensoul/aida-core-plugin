"""Path utilities for hook-manager scripts.

Sets up sys.path so that shared utilities can be imported
from the project-level scripts/shared/ directory.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Directory layout:
#   skills/hook-manager/scripts/_paths.py  (this file)
#   scripts/shared/utils.py               (shared utilities)
SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = SKILL_DIR.parent.parent

# Make shared utilities importable
_shared_scripts = PROJECT_ROOT / "scripts"
if str(_shared_scripts) not in sys.path:
    sys.path.insert(0, str(_shared_scripts))
