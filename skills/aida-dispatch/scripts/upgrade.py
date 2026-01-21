#!/usr/bin/env python3
"""AIDA Upgrade Script (MVP)

Check for and upgrade to latest AIDA version.

MVP: Provides check + confirmation + instructions
Future: Full automated upgrade with rollback

Usage:
    python upgrade.py

Exit codes:
    0 - Up to date or upgrade instructions provided
    1 - Error occurred
"""

import sys
import json
from pathlib import Path
import time

def get_current_version():
    """Get current plugin version."""
    plugin_json = Path(__file__).parent.parent / ".claude-plugin" / "plugin.json"
    try:
        with open(plugin_json, 'r') as f:
            data = json.load(f)
            return data.get('version', '0.0.0')
    except Exception as e:
        print(f"Error reading version: {e}")
        return '0.0.0'

def get_latest_version():
    """Get latest version from GitHub releases (mock for MVP)."""
    # MVP: Return mock version
    # Future: Actually fetch from GitHub API
    # For now, just simulate checking

    print("Checking for updates...")

    # Simulate API call delay
    time.sleep(1)

    # Mock latest version (in reality, fetch from GitHub)
    # For MVP, we'll just return a version slightly higher to test the flow
    return "0.2.0"  # Mock version

def compare_versions(current, latest):
    """Compare version strings."""
    def parse_version(v):
        return tuple(map(int, v.split('.')))

    try:
        current_parts = parse_version(current)
        latest_parts = parse_version(latest)

        return current_parts < latest_parts
    except Exception:
        return False

def get_release_notes(version):
    """Get release notes for version (mock for MVP)."""
    # MVP: Return mock release notes
    # Future: Fetch from GitHub API

    mock_notes = f"""Changes in {version}:
• New /aida export command for sharing configurations
• Improved memory management and performance
• Bug fixes for Windows Git Bash compatibility
• Enhanced doctor diagnostics with auto-fix suggestions
• Updated documentation and examples

Full changelog: https://github.com/oakensoul/aida-core-plugin/releases/tag/v{version}
"""
    return mock_notes

def display_upgrade_instructions(current, latest):
    """Display upgrade instructions."""
    print()
    print("=" * 60)
    print("Upgrade Instructions")
    print("=" * 60)
    print()
    print("Manual upgrade steps:")
    print()
    print("1. Backup your current configuration:")
    print("   cp -r ~/.claude ~/.claude.backup")
    print()
    print("2. Remove current plugin:")
    print("   (In Claude Code) /plugin remove aida-core")
    print()
    print("3. Install new version:")
    print(f"   (In Claude Code) /plugin install aida-core@{latest}")
    print()
    print("4. Verify installation:")
    print("   /aida doctor")
    print()
    print("5. Restore settings if needed:")
    print("   (Settings should be preserved, but backup is there just in case)")
    print()
    print("Note: Fully automated upgrade is coming in a future update!")
    print()

def main():
    print("AIDA Upgrade Check")
    print("=" * 60)
    print()

    # Get current version
    current = get_current_version()
    print(f"Current version: {current}")

    # Get latest version
    latest = get_latest_version()
    print(f"Latest version: {latest}")
    print()

    # Compare versions
    if compare_versions(current, latest):
        print(f"✓ New version available: {current} → {latest}")
        print()

        # Show release notes
        notes = get_release_notes(latest)
        print(notes)

        # Ask for confirmation
        print()
        response = input("Would you like upgrade instructions? [Y/n]: ").strip().lower()

        if response in ['', 'y', 'yes']:
            display_upgrade_instructions(current, latest)
            return 0
        else:
            print("Upgrade cancelled.")
            print("Run /aida upgrade again when you're ready.")
            return 0
    else:
        print("✓ You are already on the latest version!")
        print()
        print(f"Current: {current}")
        print(f"Latest: {latest}")
        print()
        print("No upgrade needed. 🎉")
        return 0

if __name__ == "__main__":
    sys.exit(main())
