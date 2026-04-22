"""Plugin scanner — reads the Claude plugin ecosystem and produces PluginState objects."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_JSON_SIZE = 1_048_576  # 1 MB

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class PluginState:
    """Unified view of a single plugin across installed and marketplace data."""

    name: str
    installed_version: Optional[str] = None
    available_version: Optional[str] = None
    dependencies: Dict[str, str] = field(default_factory=dict)
    source: str = "unknown"  # "marketplace", "local", "unknown"
    install_path: Optional[str] = None
    marketplace_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_json_safe(path: Path) -> Optional[dict]:
    """Read a JSON file, returning *None* on any error.

    Enforces a 1 MB size limit to avoid reading unexpectedly large files.
    """
    try:
        if not path.is_file():
            return None
        if path.stat().st_size > MAX_JSON_SIZE:
            return None
        text = path.read_text(encoding="utf-8")
        data = json.loads(text)
        if not isinstance(data, dict):
            return None
        return data
    except Exception:  # noqa: BLE001
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def scan_plugins(home_dir: Optional[Path] = None) -> List[PluginState]:
    """Scan the Claude plugin ecosystem and return a sorted list of PluginState.

    Parameters
    ----------
    home_dir:
        Override for ``Path.home()`` — used for test injection.

    Returns
    -------
    List[PluginState]
        Sorted by plugin name.
    """
    home = home_dir or Path.home()
    plugins_dir = home / ".claude" / "plugins"

    # ------------------------------------------------------------------
    # 1. Read installed plugins registry
    # ------------------------------------------------------------------
    installed_data = _read_json_safe(plugins_dir / "installed_plugins.json")
    installed_plugins: dict = {}
    if installed_data is not None:
        installed_plugins = installed_data.get("plugins", {})
        if not isinstance(installed_plugins, dict):
            installed_plugins = {}

    # ------------------------------------------------------------------
    # 2. Build marketplace catalogue   (marketplace_id -> {name: version})
    # ------------------------------------------------------------------
    marketplace_catalogue: Dict[str, Dict[str, str]] = {}
    marketplaces_dir = plugins_dir / "marketplaces"

    known_mp = _read_json_safe(plugins_dir / "known_marketplaces.json")
    marketplace_ids: List[str] = []
    if known_mp is not None:
        for mp_id in known_mp:
            marketplace_ids.append(mp_id)

    for mp_id in marketplace_ids:
        mp_json = _read_json_safe(
            marketplaces_dir / mp_id / ".claude-plugin" / "marketplace.json"
        )
        if mp_json is None:
            continue
        mp_plugins = mp_json.get("plugins", [])
        if not isinstance(mp_plugins, list):
            continue
        mp_versions: Dict[str, str] = {}
        for entry in mp_plugins:
            if not isinstance(entry, dict):
                continue
            pname = entry.get("name")
            pver = entry.get("version")
            if isinstance(pname, str) and isinstance(pver, str):
                mp_versions[pname] = pver
        marketplace_catalogue[mp_id] = mp_versions

    # ------------------------------------------------------------------
    # 3. Walk installed plugins and build PluginState objects
    # ------------------------------------------------------------------
    states: Dict[str, PluginState] = {}

    for registry_key, installs in installed_plugins.items():
        if not isinstance(installs, list):
            continue
        for install_entry in installs:
            if not isinstance(install_entry, dict):
                continue

            install_path_str = install_entry.get("installPath")
            if not isinstance(install_path_str, str):
                continue
            install_path = Path(install_path_str)

            # Read the plugin's own manifest
            plugin_json = _read_json_safe(
                install_path / ".claude-plugin" / "plugin.json"
            )
            if plugin_json is not None:
                name = plugin_json.get("name", registry_key.split("@")[0])
                version = plugin_json.get("version")
                if not isinstance(version, str):
                    version = "unknown"
                raw_deps = plugin_json.get("dependencies", {})
                if not isinstance(raw_deps, dict):
                    raw_deps = {}
            else:
                # Corrupt or missing plugin.json
                name = registry_key.split("@")[0]
                version = "unknown"
                raw_deps = {}

            # Determine marketplace source
            mp_id: Optional[str] = None
            source = "unknown"
            parts = registry_key.split("@", 1)
            if len(parts) == 2 and parts[1] in marketplace_catalogue:
                mp_id = parts[1]
                source = "marketplace"
            elif len(parts) == 2:
                # Has an @ but not in our known marketplaces
                source = "local"

            # Determine available version from the marketplace catalogue
            available_version: Optional[str] = None
            if mp_id and mp_id in marketplace_catalogue:
                available_version = marketplace_catalogue[mp_id].get(name)

            # If no marketplace_id yet, check all marketplaces for this plugin
            if mp_id is None:
                for cat_id, cat_versions in marketplace_catalogue.items():
                    if name in cat_versions:
                        available_version = cat_versions[name]
                        # Don't override mp_id — plugin is not installed from
                        # this marketplace
                        break

            state = PluginState(
                name=name,
                installed_version=version,
                available_version=available_version,
                dependencies=raw_deps,
                source=source,
                install_path=install_path_str,
                marketplace_id=mp_id,
            )

            # Prefer entry where plugin is actually installed from marketplace
            if name in states:
                existing = states[name]
                if (
                    existing.source != "marketplace"
                    and state.source == "marketplace"
                ):
                    states[name] = state
                # Otherwise keep the existing entry
            else:
                states[name] = state

    # ------------------------------------------------------------------
    # 4. Add marketplace-only plugins (available but not installed)
    # ------------------------------------------------------------------
    for mp_id, mp_versions in marketplace_catalogue.items():
        for pname, pver in mp_versions.items():
            if pname not in states:
                states[pname] = PluginState(
                    name=pname,
                    available_version=pver,
                    source="marketplace",
                    marketplace_id=mp_id,
                )

    # ------------------------------------------------------------------
    # 5. Return sorted by name
    # ------------------------------------------------------------------
    return sorted(states.values(), key=lambda s: s.name)
