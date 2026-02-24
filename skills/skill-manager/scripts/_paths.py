"""Path configuration for skill-manager scripts.

Sets up paths so operations modules can find shared utilities
and templates regardless of how the script is invoked.
"""

from pathlib import Path

# Directory layout:
#   skills/skill-manager/scripts/_paths.py  <- this file
#   skills/skill-manager/templates/         <- templates
#   scripts/shared/utils.py                 <- shared utils

SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = SKILL_DIR.parent.parent
SHARED_UTILS = PROJECT_ROOT / "scripts"
TEMPLATES_DIR = SKILL_DIR / "templates"
