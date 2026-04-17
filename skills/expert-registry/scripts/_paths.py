"""Path setup for expert-registry scripts."""

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
PLUGIN_DIR = SKILL_DIR.parent.parent

# Add shared scripts to path
sys.path.insert(0, str(PLUGIN_DIR / "scripts"))

# Add aida skill utils to path (for agents.py, files.py, paths.py)
AIDA_SCRIPTS_DIR = PLUGIN_DIR / "skills" / "aida" / "scripts"
sys.path.insert(0, str(AIDA_SCRIPTS_DIR))
