"""Path configuration for agent-manager scripts.

Sets up paths for the skill directory, project root,
shared utilities, and templates.
"""

from pathlib import Path

# Directory layout:
#   skills/agent-manager/scripts/_paths.py  <- this file
#   skills/agent-manager/templates/         <- templates
#   scripts/shared/utils.py                 <- shared utils
SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = SKILL_DIR.parent.parent
SHARED_UTILS = PROJECT_ROOT / "scripts"
TEMPLATES_DIR = SKILL_DIR / "templates"
