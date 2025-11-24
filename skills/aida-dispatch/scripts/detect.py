#!/usr/bin/env python3
"""AIDA Installation Detection Script

Detects AIDA installation state and returns structured JSON output.

Usage:
    python detect.py

Output:
    JSON object with installation state:
    {
        "global_installed": true/false,
        "project_configured": true/false,
        "global_path": "~/.claude/aida.yml" or null,
        "project_path": "./.claude/aida.yml" or null,
        "project_name": "current-directory-name",
        "project_root": "/absolute/path/to/project"
    }

Exit codes:
    0 - Always succeeds (reports state)
"""

import sys
import os
import json
from pathlib import Path


def get_global_aida_yml():
    """Get path to global AIDA marker file."""
    return Path.home() / ".claude" / "aida.yml"


def get_project_aida_yml():
    """Get path to project AIDA marker file."""
    return Path.cwd() / ".claude" / "aida.yml"


def check_global_installation():
    """Check if AIDA is installed globally by checking for aida.yml marker."""
    aida_yml = get_global_aida_yml()
    return aida_yml.exists() and aida_yml.is_file()


def check_project_configuration():
    """Check if current project has AIDA configured by checking for aida.yml marker."""
    aida_yml = get_project_aida_yml()
    return aida_yml.exists() and aida_yml.is_file()


def get_project_info():
    """Get current project information."""
    cwd = Path.cwd()
    return {
        "name": cwd.name,
        "root": str(cwd.resolve())
    }


def main():
    """Detect AIDA installation state and output JSON."""
    global_installed = check_global_installation()
    project_configured = check_project_configuration()
    project_info = get_project_info()

    result = {
        "global_installed": global_installed,
        "project_configured": project_configured,
        "global_path": str(get_global_aida_yml()) if global_installed else None,
        "project_path": str(get_project_aida_yml()) if project_configured else None,
        "project_name": project_info["name"],
        "project_root": project_info["root"]
    }

    # Output JSON to stdout
    print(json.dumps(result, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
