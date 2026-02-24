#!/usr/bin/env python3
"""AIDA Upgrade Script

Check for and upgrade to latest AIDA version.

Usage:
    python upgrade.py [--json]

Flags:
    --json - Output results in JSON format (for Claude Code integration)

Exit codes:
    0 - Up to date or upgrade instructions provided
    1 - Error occurred
"""

import sys
import json
import subprocess
from pathlib import Path
from typing import Tuple, Optional, Dict, Any

def get_current_version() -> str:
    """Get current plugin version."""
    # Path: skills/aida/scripts/upgrade.py → repo root
    # parent(1)=scripts/, parent(2)=aida/, parent(3)=skills/, parent(4)=root
    plugin_json = Path(__file__).parent.parent.parent.parent / ".claude-plugin" / "plugin.json"
    try:
        with open(plugin_json, 'r') as f:
            data = json.load(f)
            return data.get('version', '0.0.0')
    except Exception as e:
        print(f"Error reading version: {e}")
        return '0.0.0'

def get_latest_version() -> Tuple[Optional[str], Optional[str]]:
    """Get latest version from GitHub releases using gh CLI.

    Returns:
        Tuple of (version, error_message). If successful, version is set and error_message is None.
        If failed, version is None and error_message describes the failure.
    """
    try:
        result = subprocess.run(
            ["gh", "api", "repos/oakensoul/aida-core-plugin/releases/latest"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode != 0:
            error = result.stderr.strip() if result.stderr else "Unknown error"
            return None, f"GitHub API error: {error}"

        data = json.loads(result.stdout)
        tag_name = data.get("tag_name", "")

        # Strip 'v' prefix if present
        version = tag_name.lstrip('v')

        if not version:
            return None, "No version found in release data"

        return version, None

    except subprocess.TimeoutExpired:
        return None, "GitHub API request timed out"
    except FileNotFoundError:
        return None, "gh CLI not installed. Install with: brew install gh"
    except json.JSONDecodeError:
        return None, "Invalid JSON response from GitHub API"
    except Exception as e:
        return None, f"Unexpected error: {e}"

def compare_versions(current: str, latest: str) -> bool:
    """Compare version strings.

    Args:
        current: Current version string (e.g., "0.7.0")
        latest: Latest version string (e.g., "0.7.1")

    Returns:
        True if current < latest, False otherwise
    """
    def parse_version(v: str) -> Tuple[int, ...]:
        return tuple(map(int, v.split('.')))

    try:
        current_parts = parse_version(current)
        latest_parts = parse_version(latest)

        return current_parts < latest_parts
    except Exception:
        return False

def get_release_notes(version: str) -> Tuple[Optional[str], Optional[str]]:
    """Get release notes for a specific version from GitHub.

    Args:
        version: Version string (e.g., "0.1.0")

    Returns:
        Tuple of (release_notes, error_message). If successful, release_notes is set.
        If failed, release_notes is None and error_message describes the failure.
    """
    try:
        # Ensure version has 'v' prefix for tag lookup
        tag = version if version.startswith('v') else f'v{version}'

        result = subprocess.run(
            ["gh", "api", f"repos/oakensoul/aida-core-plugin/releases/tags/{tag}"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode != 0:
            return None, "Release notes unavailable"

        data = json.loads(result.stdout)
        body = data.get("body", "")

        if not body:
            return f"No release notes available for {version}", None

        return body, None

    except subprocess.TimeoutExpired:
        return None, "Request timed out"
    except FileNotFoundError:
        return None, "gh CLI not installed"
    except json.JSONDecodeError:
        return None, "Invalid response from GitHub"
    except Exception as e:
        return None, f"Error: {e}"

def display_upgrade_instructions(current: str, latest: str) -> None:
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

def output_json(data: Dict[str, Any]) -> None:
    """Output result as JSON."""
    print(json.dumps(data, indent=2))

def main() -> int:
    """Main entry point for upgrade checking.

    Returns:
        0 on success, 1 on error
    """
    # Check if JSON mode is requested
    json_mode = '--json' in sys.argv

    if not json_mode:
        print("AIDA Upgrade Check")
        print("=" * 60)
        print()

    # Get current version
    current = get_current_version()

    if not json_mode:
        print(f"Current version: {current}")

    # Get latest version
    latest, error = get_latest_version()

    if error:
        if json_mode:
            output_json({
                "success": False,
                "error": error,
                "current_version": current,
                "message": "Unable to check for updates. Please check manually at: https://github.com/oakensoul/aida-core-plugin/releases"
            })
        else:
            print(f"✗ Error checking for updates: {error}")
            print()
            print("Please check manually at:")
            print("https://github.com/oakensoul/aida-core-plugin/releases")
        return 1

    if not json_mode:
        print(f"Latest version: {latest}")
        print()

    # Compare versions
    if compare_versions(current, latest):
        # New version available
        notes, notes_error = get_release_notes(latest)

        if json_mode:
            output_json({
                "success": True,
                "update_available": True,
                "current_version": current,
                "latest_version": latest,
                "release_notes": notes or "Release notes unavailable",
                "message": f"New version available: {current} → {latest}"
            })
        else:
            print(f"✓ New version available: {current} → {latest}")
            print()

            # Show release notes
            if notes:
                print("Release Notes:")
                print(notes)
            elif notes_error:
                print(f"(Release notes unavailable: {notes_error})")

            print()
            display_upgrade_instructions(current, latest)

        return 0
    else:
        # Already up to date
        if json_mode:
            output_json({
                "success": True,
                "update_available": False,
                "current_version": current,
                "latest_version": latest,
                "message": "You are already on the latest version"
            })
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
