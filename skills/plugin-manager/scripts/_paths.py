"""Path setup for plugin-manager scripts.

Configures sys.path so that operations/ and scripts/shared/
can be imported cleanly from any working directory.
"""

import sys
from pathlib import Path

# Directory layout:
#   skills/plugin-manager/scripts/_paths.py   <- this file
#   skills/plugin-manager/scripts/manage.py
#   skills/plugin-manager/templates/
#   scripts/shared/utils.py
SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = SKILL_DIR.parent.parent

TEMPLATES_DIR = SKILL_DIR / "templates"
EXTENSION_TEMPLATES_DIR = TEMPLATES_DIR / "extension"
SCAFFOLD_TEMPLATES_DIR = TEMPLATES_DIR / "scaffold"

# Shared utilities live at PROJECT_ROOT/scripts/shared/utils.py
SHARED_UTILS = PROJECT_ROOT / "scripts"
if not (SHARED_UTILS / "shared" / "utils.py").exists():
    raise ImportError(
        f"Cannot find shared utils at {SHARED_UTILS}. "
        "Verify _paths.py is at the expected directory depth."
    )

# Add to sys.path so `from shared.utils import ...` works
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(SHARED_UTILS))
