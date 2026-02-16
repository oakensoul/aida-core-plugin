#!/usr/bin/env python3
"""Plugin permission scanner.

Discovers recommended permissions from installed plugins by
scanning the plugin cache directory for plugin.json manifests.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

# Reuse utilities from aida-dispatch (append to avoid shadowing stdlib)
sys.path.append(
    str(
        Path(__file__).parent.parent.parent
        / "aida-dispatch"
        / "scripts"
    ),
)
from utils import get_home_dir  # noqa: E402

logger = logging.getLogger(__name__)


def get_installed_plugin_dirs() -> list[Path]:
    """Find plugin directories in the cache.

    Scans ``~/.claude/plugins/cache/*/*/.claude-plugin/`` for
    installed plugin manifests.

    Returns:
        List of paths to ``.claude-plugin`` directories.
    """
    claude_dir = get_home_dir() / ".claude"
    cache_root = claude_dir / "plugins" / "cache"
    if not cache_root.is_dir():
        return []

    resolved_root = cache_root.resolve()
    plugin_dirs: list[Path] = []
    for manifest in cache_root.glob("*/*/.claude-plugin"):
        if not manifest.is_dir():
            continue
        # Reject symlinks to prevent following links outside cache
        if manifest.is_symlink():
            logger.warning(
                "Skipping symlink in plugin cache: %s", manifest
            )
            continue
        # Validate resolved path stays within cache root
        try:
            manifest.resolve().relative_to(resolved_root)
        except ValueError:
            logger.warning(
                "Plugin path outside cache root: %s", manifest
            )
            continue
        plugin_dirs.append(manifest)
    return sorted(plugin_dirs)


def read_plugin_manifest(plugin_dir: Path) -> dict | None:
    """Parse a plugin.json manifest safely.

    Args:
        plugin_dir: Path to a ``.claude-plugin`` directory.

    Returns:
        Parsed manifest dict, or ``None`` on error.
    """
    manifest_path = plugin_dir / "plugin.json"
    if not manifest_path.is_file():
        return None
    try:
        # Check file size before reading to prevent memory exhaustion
        if manifest_path.stat().st_size > 1024 * 1024:
            logger.warning(
                "Plugin manifest too large: %s", manifest_path
            )
            return None
        with open(manifest_path, encoding="utf-8") as f:
            content = f.read()
        return json.loads(content)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning(
            "Failed to read plugin manifest %s: %s",
            manifest_path,
            exc,
        )
        return None


def scan_plugins() -> list[dict]:
    """Collect recommendedPermissions from all installed plugins.

    Returns:
        List of dicts with ``name`` (str) and ``permissions``
        (dict) keys for each plugin that declares permissions.
    """
    results: list[dict] = []
    for plugin_dir in get_installed_plugin_dirs():
        manifest = read_plugin_manifest(plugin_dir)
        if manifest is None:
            continue

        permissions = manifest.get("recommendedPermissions")
        if not permissions or not isinstance(permissions, dict):
            continue

        name = manifest.get("name", plugin_dir.parent.name)
        results.append({"name": name, "permissions": permissions})

    return results


if __name__ == "__main__":
    plugins = scan_plugins()
    print(json.dumps(plugins, indent=2))
