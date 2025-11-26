#!/usr/bin/env python3
"""Developer mode management for AIDA Core Plugin.

This script manages the local plugin installation for development,
handling the Claude Code plugin configuration files.

Usage:
    python dev_mode.py enable   # Enable local development plugin
    python dev_mode.py disable  # Disable and remove local plugin
    python dev_mode.py status   # Show current dev mode status
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timezone

# Plugin configuration
PLUGIN_NAME = "aida-core"
MARKETPLACE_NAME = "aida"
PLUGIN_KEY = f"{PLUGIN_NAME}@{MARKETPLACE_NAME}"

# Paths
SCRIPT_DIR = Path(__file__).parent
PLUGIN_ROOT = SCRIPT_DIR.parent
CLAUDE_DIR = Path.home() / ".claude"
PLUGINS_DIR = CLAUDE_DIR / "plugins"


def get_plugin_version() -> str:
    """Get plugin version from .claude-plugin/plugin.json."""
    plugin_json = PLUGIN_ROOT / ".claude-plugin" / "plugin.json"
    if plugin_json.exists():
        try:
            data = json.loads(plugin_json.read_text())
            return data.get("version", "0.0.0")
        except (json.JSONDecodeError, IOError):
            pass
    return "0.0.0"


def ensure_marketplace_json() -> bool:
    """Ensure marketplace.json exists in .claude-plugin/ directory."""
    marketplace_json = PLUGIN_ROOT / ".claude-plugin" / "marketplace.json"
    version = get_plugin_version()

    content = {
        "name": MARKETPLACE_NAME,
        "owner": {
            "name": "oakensoul",
            "email": "github@oakensoul.com"
        },
        "description": "AIDA - Agentic Intelligence Digital Assistant plugins",
        "plugins": [
            {
                "name": PLUGIN_NAME,
                "description": "Smart configuration with auto-detection, GitHub integration, and context management",
                "version": version,
                "source": "./"
            }
        ]
    }

    try:
        marketplace_json.write_text(json.dumps(content, indent=2) + "\n")
        return True
    except IOError as e:
        print(f"Error creating marketplace.json: {e}")
        return False


def load_json(path: Path, default: dict = None) -> dict:
    """Load JSON file, returning default if not found."""
    if default is None:
        default = {}
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, IOError):
        return default


def save_json(path: Path, data: dict) -> bool:
    """Save JSON file with proper formatting."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2) + "\n")
        return True
    except IOError as e:
        print(f"Error saving {path}: {e}")
        return False


def enable_dev_mode() -> int:
    """Enable development mode for the plugin."""
    print("=== Enabling AIDA Dev Mode ===\n")

    # Ensure directories exist
    PLUGINS_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Create/update marketplace.json in .claude-plugin directory
    print("1. Creating marketplace.json in .claude-plugin directory...")
    if not ensure_marketplace_json():
        return 1
    print(f"   Created: {PLUGIN_ROOT / '.claude-plugin' / 'marketplace.json'}")

    # 2. Update known_marketplaces.json
    print("\n2. Registering local marketplace...")
    known_path = PLUGINS_DIR / "known_marketplaces.json"
    known = load_json(known_path, {})

    now = datetime.now(timezone.utc).isoformat()
    known[MARKETPLACE_NAME] = {
        "source": {
            "source": "directory",
            "path": str(PLUGIN_ROOT)
        },
        "installLocation": str(PLUGIN_ROOT),
        "lastUpdated": now
    }

    if not save_json(known_path, known):
        return 1
    print(f"   Updated: {known_path}")

    # 3. Update installed_plugins.json
    print("\n3. Registering installed plugin...")
    installed_path = PLUGINS_DIR / "installed_plugins.json"
    installed = load_json(installed_path, {"version": 1, "plugins": {}})

    if "plugins" not in installed:
        installed["plugins"] = {}

    version = get_plugin_version()
    installed["plugins"][PLUGIN_KEY] = {
        "version": version,
        "installedAt": now,
        "lastUpdated": now,
        "installPath": str(PLUGIN_ROOT),
        "isLocal": True
    }

    if not save_json(installed_path, installed):
        return 1
    print(f"   Updated: {installed_path}")

    # 4. Update settings.json to enable plugin
    print("\n4. Enabling plugin in settings...")
    settings_path = CLAUDE_DIR / "settings.json"
    settings = load_json(settings_path, {})

    if "enabledPlugins" not in settings:
        settings["enabledPlugins"] = {}

    settings["enabledPlugins"][PLUGIN_KEY] = True

    if not save_json(settings_path, settings):
        return 1
    print(f"   Updated: {settings_path}")

    print("\n=== Dev Mode Enabled ===")
    print(f"\nPlugin: {PLUGIN_KEY}")
    print(f"Version: {version}")
    print(f"Path: {PLUGIN_ROOT}")
    print("\n** Restart Claude Code for changes to take effect **")

    return 0


def disable_dev_mode() -> int:
    """Disable development mode and remove local plugin."""
    print("=== Disabling AIDA Dev Mode ===\n")

    # 1. Remove from known_marketplaces.json
    print("1. Removing local marketplace registration...")
    known_path = PLUGINS_DIR / "known_marketplaces.json"
    known = load_json(known_path, {})

    if MARKETPLACE_NAME in known:
        del known[MARKETPLACE_NAME]
        if not save_json(known_path, known):
            return 1
        print(f"   Removed marketplace: {MARKETPLACE_NAME}")
    else:
        print(f"   Marketplace not registered: {MARKETPLACE_NAME}")

    # 2. Remove from installed_plugins.json
    print("\n2. Removing installed plugin entry...")
    installed_path = PLUGINS_DIR / "installed_plugins.json"
    installed = load_json(installed_path, {"version": 1, "plugins": {}})

    if "plugins" in installed and PLUGIN_KEY in installed["plugins"]:
        del installed["plugins"][PLUGIN_KEY]
        if not save_json(installed_path, installed):
            return 1
        print(f"   Removed plugin: {PLUGIN_KEY}")
    else:
        print(f"   Plugin not installed: {PLUGIN_KEY}")

    # 3. Disable in settings.json
    print("\n3. Disabling plugin in settings...")
    settings_path = CLAUDE_DIR / "settings.json"
    settings = load_json(settings_path, {})

    if "enabledPlugins" in settings and PLUGIN_KEY in settings["enabledPlugins"]:
        del settings["enabledPlugins"][PLUGIN_KEY]
        if not save_json(settings_path, settings):
            return 1
        print(f"   Disabled plugin: {PLUGIN_KEY}")
    else:
        print(f"   Plugin not enabled: {PLUGIN_KEY}")

    # 4. Optionally remove marketplace.json from .claude-plugin directory
    marketplace_json = PLUGIN_ROOT / ".claude-plugin" / "marketplace.json"
    if marketplace_json.exists():
        print(f"\n4. Note: marketplace.json left in place at {marketplace_json}")
        print("   (Delete manually if desired)")

    print("\n=== Dev Mode Disabled ===")
    print("\n** Restart Claude Code for changes to take effect **")

    return 0


def show_status() -> int:
    """Show current dev mode status."""
    print("=== AIDA Dev Mode Status ===\n")

    # Check marketplace registration
    known_path = PLUGINS_DIR / "known_marketplaces.json"
    known = load_json(known_path, {})
    marketplace_registered = MARKETPLACE_NAME in known

    print(f"Marketplace '{MARKETPLACE_NAME}':")
    if marketplace_registered:
        mp = known[MARKETPLACE_NAME]
        print("  Registered: Yes")
        print(f"  Path: {mp.get('installLocation', 'unknown')}")
        print(f"  Last Updated: {mp.get('lastUpdated', 'unknown')}")
    else:
        print("  Registered: No")

    # Check plugin installation
    installed_path = PLUGINS_DIR / "installed_plugins.json"
    installed = load_json(installed_path, {"version": 1, "plugins": {}})
    plugin_installed = "plugins" in installed and PLUGIN_KEY in installed["plugins"]

    print(f"\nPlugin '{PLUGIN_KEY}':")
    if plugin_installed:
        pl = installed["plugins"][PLUGIN_KEY]
        print("  Installed: Yes")
        print(f"  Version: {pl.get('version', 'unknown')}")
        print(f"  Path: {pl.get('installPath', 'unknown')}")
        print(f"  Is Local: {pl.get('isLocal', False)}")
    else:
        print("  Installed: No")

    # Check if enabled
    settings_path = CLAUDE_DIR / "settings.json"
    settings = load_json(settings_path, {})
    plugin_enabled = settings.get("enabledPlugins", {}).get(PLUGIN_KEY, False)

    print(f"\nPlugin Enabled: {'Yes' if plugin_enabled else 'No'}")

    # Check marketplace.json exists in correct location
    marketplace_json = PLUGIN_ROOT / ".claude-plugin" / "marketplace.json"
    print(f"\nmarketplace.json exists: {'Yes' if marketplace_json.exists() else 'No'}")
    print(f"  Location: {marketplace_json}")

    # Overall status
    dev_mode_active = marketplace_registered and plugin_installed and plugin_enabled
    print(f"\n=== Dev Mode: {'ACTIVE' if dev_mode_active else 'INACTIVE'} ===")

    return 0


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="AIDA Core Plugin - Developer Mode Management"
    )
    parser.add_argument(
        "action",
        choices=["enable", "disable", "status"],
        help="Action to perform"
    )

    args = parser.parse_args()

    if args.action == "enable":
        return enable_dev_mode()
    elif args.action == "disable":
        return disable_dev_mode()
    elif args.action == "status":
        return show_status()

    return 1


if __name__ == "__main__":
    sys.exit(main())
