#!/usr/bin/env python3
"""AIDA Status Script

Display current AIDA configuration state.

Usage:
    python status.py

Exit codes:
    0 - Always succeeds (reports state)
"""

import sys
from pathlib import Path
import json
from typing import List

def get_claude_dir() -> Path:
    """Get ~/.claude/ directory path."""
    return Path.home() / ".claude"

def get_project_claude_dir() -> Path:
    """Get ./.claude/ directory in current working directory."""
    return Path.cwd() / ".claude"

def check_global_installation() -> bool:
    """Check if AIDA is installed globally."""
    claude_dir = get_claude_dir()
    return claude_dir.exists() and claude_dir.is_dir()

def check_project_configuration() -> bool:
    """Check if current project has AIDA configured."""
    project_claude = get_project_claude_dir()
    return project_claude.exists() and project_claude.is_dir()

def get_plugin_version() -> str:
    """Get plugin version from plugin.json."""
    # Navigate from scripts/ -> aida-core/ -> skills/ -> aida-core/ -> .claude-plugin/plugin.json
    plugin_json = Path(__file__).parent.parent.parent.parent / ".claude-plugin" / "plugin.json"
    try:
        if plugin_json.exists():
            with open(plugin_json, 'r') as f:
                data = json.load(f)
                return data.get('version', 'unknown')
    except Exception:
        pass
    return 'unknown'

def count_skills(claude_dir: Path) -> int:
    """Count active skills in a directory."""
    skills_dir = claude_dir / "skills"
    if not skills_dir.exists():
        return 0

    count = 0
    for item in skills_dir.iterdir():
        if item.is_dir() and (item / "SKILL.md").exists():
            count += 1
    return count

def list_skills(claude_dir: Path) -> List[str]:
    """List active skills in a directory."""
    skills_dir = claude_dir / "skills"
    if not skills_dir.exists():
        return []

    skills = []
    for item in skills_dir.iterdir():
        if item.is_dir() and (item / "SKILL.md").exists():
            skills.append(item.name)
    return sorted(skills)

def main() -> int:
    print("AIDA Status")
    print("=" * 40)
    print()

    # Check global installation
    global_installed = check_global_installation()
    if global_installed:
        print(f"✓ Global Installation: {get_claude_dir()}")

        # Count and list global skills
        global_skills = list_skills(get_claude_dir())
        print(f"✓ Global Skills: {len(global_skills)} loaded")
        for skill in global_skills:
            print(f"  • {skill}")
    else:
        print("✗ Global Installation: Not found")
        print("  → Run /aida config to set up AIDA globally")

    print()

    # Check project configuration
    project_configured = check_project_configuration()
    if project_configured:
        project_name = Path.cwd().name
        print(f"✓ Project Configuration: {get_project_claude_dir()}")
        print(f"✓ Project: {project_name}")

        # Count and list project skills
        project_skills = list_skills(get_project_claude_dir())
        print(f"✓ Project Skills: {len(project_skills)} loaded")
        for skill in project_skills:
            print(f"  • {skill}")
    else:
        print("✗ Project Configuration: Not found")
        if global_installed:
            print("  → Run /aida config to configure this project")
        else:
            print("  → Set up AIDA globally first")

    print()

    # Plugin version
    version = get_plugin_version()
    print(f"Plugin Version: {version}")

    print()
    print("-" * 40)

    if not global_installed:
        print("Get started: /aida config")
    elif not project_configured:
        print("Configure project: /aida config")
    else:
        print("Run /aida doctor for detailed diagnostics")
        print("Run /aida config to update settings")

    return 0

if __name__ == "__main__":
    sys.exit(main())
