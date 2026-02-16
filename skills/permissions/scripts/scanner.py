#!/usr/bin/env python3
"""Plugin permission scanner.

Discovers recommended permissions from installed plugins by
scanning the plugin cache directory for plugin.json manifests.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from _paths import get_home_dir

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


from rule_validation import validate_rule  # noqa: E402


def _validate_permission_rules(
    permissions: dict, plugin_name: str
) -> dict:
    """Validate and filter permission rules at scan time.

    Removes categories with invalid rules and logs warnings
    rather than propagating malformed data downstream.

    Args:
        permissions: Raw recommendedPermissions dict.
        plugin_name: Plugin name for log messages.

    Returns:
        Filtered permissions dict with only valid categories.
    """
    valid: dict = {}
    for cat_key, cat_data in permissions.items():
        if not isinstance(cat_data, dict):
            logger.warning(
                "Plugin %r category %r is not a dict; skipping",
                plugin_name,
                cat_key,
            )
            continue
        rules = cat_data.get("rules", [])
        if not isinstance(rules, list):
            logger.warning(
                "Plugin %r category %r rules is not a list; "
                "skipping",
                plugin_name,
                cat_key,
            )
            continue

        invalid_rules = []
        for rule in rules:
            ok, err = validate_rule(rule)
            if not ok:
                invalid_rules.append(
                    repr(rule) if isinstance(rule, str)
                    else repr(rule)
                )

        if invalid_rules:
            logger.warning(
                "Plugin %r category %r has invalid rules: %s; "
                "skipping category",
                plugin_name,
                cat_key,
                ", ".join(invalid_rules),
            )
            continue

        valid[cat_key] = cat_data
    return valid


def scan_plugins() -> list[dict]:
    """Collect recommendedPermissions from all installed plugins.

    Rules are validated at scan time so that malformed plugin
    data is rejected early rather than propagating downstream.

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
        validated = _validate_permission_rules(permissions, name)
        if validated:
            results.append(
                {"name": name, "permissions": validated}
            )

    return results


if __name__ == "__main__":
    plugins = scan_plugins()
    print(json.dumps(plugins, indent=2))
