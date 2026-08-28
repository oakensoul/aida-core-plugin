# SPDX-FileCopyrightText: 2026 The AIDA Core Authors
# SPDX-License-Identifier: MPL-2.0

"""Plugin-provided command discovery for the /aida dispatch.

Installed plugins can register their own ``/aida <name>`` actions by
declaring a ``commands`` block in ``.claude-plugin/aida-config.json``.
This script is how the dispatch skill finds them: it lists every valid
registered command, or resolves one name to the skill that handles it.

Built-in actions always win -- a plugin cannot claim ``config``,
``doctor``, or any other reserved name.

Usage:
    python commands.py --list
    python commands.py --resolve prodoc
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from utils.plugins import (  # noqa: E402
    RESERVED_COMMAND_NAMES,
    collect_plugin_commands,
    discover_installed_plugins,
    resolve_plugin_command,
)


def list_commands() -> dict:
    """Return every valid plugin-registered command."""
    routes = collect_plugin_commands(discover_installed_plugins())
    return {
        "success": True,
        "commands": routes,
        "count": len(routes),
    }


def resolve_command(name: str) -> dict:
    """Resolve one command name to its handling skill."""
    if name in RESERVED_COMMAND_NAMES:
        return {
            "success": False,
            "found": False,
            "name": name,
            "reserved": True,
            "message": (
                f"'{name}' is a built-in /aida action, not a "
                "plugin command"
            ),
        }

    plugins = discover_installed_plugins()
    route = resolve_plugin_command(name, plugins)
    if route is None:
        available = [
            r["name"] for r in collect_plugin_commands(plugins)
        ]
        return {
            "success": False,
            "found": False,
            "name": name,
            "reserved": False,
            "available": available,
            "message": f"No installed plugin provides '{name}'",
        }

    return {
        "success": True,
        "found": True,
        "name": route["name"],
        "skill": route["skill"],
        "description": route["description"],
        "operations": route["operations"],
        "plugin": route["plugin"],
    }


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Prints JSON and returns an exit code."""
    parser = argparse.ArgumentParser(
        description="Discover plugin-provided /aida commands"
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--list",
        action="store_true",
        help="List all registered plugin commands",
    )
    mode.add_argument(
        "--resolve",
        metavar="NAME",
        help="Resolve a command name to its skill",
    )
    args = parser.parse_args(argv)

    result = (
        list_commands() if args.list else resolve_command(args.resolve)
    )
    print(json.dumps(result, indent=2))
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
