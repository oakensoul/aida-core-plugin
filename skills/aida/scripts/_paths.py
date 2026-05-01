# SPDX-FileCopyrightText: 2026 The AIDA Core Authors
# SPDX-License-Identifier: MPL-2.0

"""Path configuration for aida scripts.

Sets up sys.path so that shared utilities can be imported
from the project-level scripts/shared/ directory.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Directory layout:
#   skills/aida/scripts/_paths.py      <- this file
#   skills/aida/templates/             <- templates
#   scripts/shared/utils.py            <- shared utils
SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = SKILL_DIR.parent.parent
TEMPLATES_DIR = SKILL_DIR / "templates"

# Make local operations and shared utilities importable
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
_shared_scripts = PROJECT_ROOT / "scripts"
if str(_shared_scripts) not in sys.path:
    sys.path.insert(0, str(_shared_scripts))

from shared.bootstrap import ensure_aida_environment  # noqa: E402
ensure_aida_environment()
