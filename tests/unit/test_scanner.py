"""Tests for the marketplace-sync plugin scanner."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from typing import Dict, Optional

# Path setup so we can import sync_ops modules
sys.path.insert(
    0,
    str(
        Path(__file__).parent.parent.parent
        / "skills"
        / "marketplace-sync"
        / "scripts"
    ),
)
sys.path.insert(
    0,
    str(Path(__file__).parent.parent.parent / "scripts"),
)

from sync_ops.scanner import (  # noqa: E402
    _read_json_safe,
    scan_plugins,
)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _setup_ecosystem(
    tmp: Path,
    installed: Optional[Dict] = None,
    cache: Optional[Dict[str, Dict]] = None,
    marketplaces: Optional[Dict[str, Dict]] = None,
    known_marketplaces: Optional[Dict] = None,
) -> Path:
    """Build a mock plugin ecosystem under *tmp*.

    Parameters
    ----------
    tmp:
        Root directory acting as ``$HOME``.
    installed:
        Content for ``installed_plugins.json``.
    cache:
        Maps ``installPath`` (relative to *tmp*) -> ``plugin.json`` content.
        ``None`` values mean the plugin.json should not be created.
    marketplaces:
        Maps marketplace ID -> ``marketplace.json`` content.
    known_marketplaces:
        Content for ``known_marketplaces.json``.

    Returns
    -------
    Path
        The *tmp* directory (same as input, for convenience).
    """
    plugins_dir = tmp / ".claude" / "plugins"
    plugins_dir.mkdir(parents=True, exist_ok=True)

    if installed is not None:
        (plugins_dir / "installed_plugins.json").write_text(
            json.dumps(installed), encoding="utf-8"
        )

    if cache is not None:
        for rel_path, plugin_json_content in cache.items():
            plugin_dir = tmp / rel_path / ".claude-plugin"
            plugin_dir.mkdir(parents=True, exist_ok=True)
            if plugin_json_content is not None:
                (plugin_dir / "plugin.json").write_text(
                    json.dumps(plugin_json_content)
                    if isinstance(plugin_json_content, dict)
                    else str(plugin_json_content),
                    encoding="utf-8",
                )

    if known_marketplaces is not None:
        (plugins_dir / "known_marketplaces.json").write_text(
            json.dumps(known_marketplaces), encoding="utf-8"
        )

    if marketplaces is not None:
        mp_base = plugins_dir / "marketplaces"
        for mp_id, mp_content in marketplaces.items():
            mp_dir = mp_base / mp_id / ".claude-plugin"
            mp_dir.mkdir(parents=True, exist_ok=True)
            (mp_dir / "marketplace.json").write_text(
                json.dumps(mp_content), encoding="utf-8"
            )

    return tmp


# ------------------------------------------------------------------
# _read_json_safe tests
# ------------------------------------------------------------------


class TestReadJsonSafe:
    """Low-level JSON reader."""

    def test_returns_none_for_missing_file(self) -> None:
        assert _read_json_safe(Path("/nonexistent/file.json")) is None

    def test_returns_none_for_invalid_json(self) -> None:
        with tempfile.NamedTemporaryFile(
            suffix=".json", mode="w", delete=False
        ) as f:
            f.write("{not valid json!!!")
            f.flush()
            assert _read_json_safe(Path(f.name)) is None

    def test_returns_none_for_non_dict(self) -> None:
        with tempfile.NamedTemporaryFile(
            suffix=".json", mode="w", delete=False
        ) as f:
            f.write("[1, 2, 3]")
            f.flush()
            assert _read_json_safe(Path(f.name)) is None

    def test_returns_dict_for_valid_json(self) -> None:
        with tempfile.NamedTemporaryFile(
            suffix=".json", mode="w", delete=False
        ) as f:
            f.write('{"key": "value"}')
            f.flush()
            result = _read_json_safe(Path(f.name))
            assert result == {"key": "value"}


# ------------------------------------------------------------------
# Empty ecosystem
# ------------------------------------------------------------------


class TestEmptyEcosystem:
    """No installed_plugins.json or empty plugins."""

    def test_no_installed_plugins_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = scan_plugins(home_dir=Path(tmp))
            assert result == []

    def test_empty_plugins_dict(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _setup_ecosystem(
                Path(tmp),
                installed={"version": 2, "plugins": {}},
            )
            result = scan_plugins(home_dir=Path(tmp))
            assert result == []

    def test_installed_file_with_no_plugins_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _setup_ecosystem(
                Path(tmp),
                installed={"version": 2},
            )
            result = scan_plugins(home_dir=Path(tmp))
            assert result == []


# ------------------------------------------------------------------
# Single plugin, no dependencies
# ------------------------------------------------------------------


class TestSinglePluginNoDeps:
    """One installed plugin with no dependencies."""

    def test_basic_plugin(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            install_path = "plugins/my-plugin"
            _setup_ecosystem(
                tmp_path,
                installed={
                    "version": 2,
                    "plugins": {
                        "my-plugin@mp1": [
                            {
                                "scope": "user",
                                "installPath": str(
                                    tmp_path / install_path
                                ),
                                "version": "1.2.0",
                            }
                        ]
                    },
                },
                cache={
                    install_path: {
                        "name": "my-plugin",
                        "version": "1.2.0",
                    }
                },
                known_marketplaces={"mp1": {"url": "https://example.com"}},
                marketplaces={
                    "mp1": {
                        "plugins": [
                            {
                                "name": "my-plugin",
                                "version": "1.3.0",
                                "source": {"ref": "v1.3.0"},
                            }
                        ]
                    }
                },
            )
            result = scan_plugins(home_dir=tmp_path)

            assert len(result) == 1
            plugin = result[0]
            assert plugin.name == "my-plugin"
            assert plugin.installed_version == "1.2.0"
            assert plugin.available_version == "1.3.0"
            assert plugin.dependencies == {}
            assert plugin.source == "marketplace"
            assert plugin.install_path == str(tmp_path / install_path)
            assert plugin.marketplace_id == "mp1"


# ------------------------------------------------------------------
# Plugin with dependencies
# ------------------------------------------------------------------


class TestPluginWithDeps:
    """Plugins that declare dependencies."""

    def test_dependencies_populated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            install_a = "plugins/plugin-a"
            install_b = "plugins/plugin-b"
            _setup_ecosystem(
                tmp_path,
                installed={
                    "version": 2,
                    "plugins": {
                        "plugin-a@mp1": [
                            {
                                "scope": "user",
                                "installPath": str(
                                    tmp_path / install_a
                                ),
                                "version": "2.0.0",
                            }
                        ],
                        "plugin-b@mp1": [
                            {
                                "scope": "user",
                                "installPath": str(
                                    tmp_path / install_b
                                ),
                                "version": "1.0.0",
                            }
                        ],
                    },
                },
                cache={
                    install_a: {
                        "name": "plugin-a",
                        "version": "2.0.0",
                        "dependencies": {"plugin-b": ">=1.0.0"},
                    },
                    install_b: {
                        "name": "plugin-b",
                        "version": "1.0.0",
                    },
                },
                known_marketplaces={"mp1": {"url": "https://example.com"}},
                marketplaces={
                    "mp1": {
                        "plugins": [
                            {"name": "plugin-a", "version": "2.0.0"},
                            {"name": "plugin-b", "version": "1.0.0"},
                        ]
                    }
                },
            )
            result = scan_plugins(home_dir=tmp_path)

            assert len(result) == 2
            # Sorted by name
            pa = result[0]
            pb = result[1]
            assert pa.name == "plugin-a"
            assert pa.dependencies == {"plugin-b": ">=1.0.0"}
            assert pb.name == "plugin-b"
            assert pb.dependencies == {}


# ------------------------------------------------------------------
# Missing installed_plugins.json
# ------------------------------------------------------------------


class TestMissingInstalledPlugins:
    """installed_plugins.json does not exist."""

    def test_marketplace_only_plugins_still_listed(self) -> None:
        """If marketplace data exists but no installs, show available plugins."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            _setup_ecosystem(
                tmp_path,
                # No installed= argument -> no installed_plugins.json
                known_marketplaces={"mp1": {"url": "https://example.com"}},
                marketplaces={
                    "mp1": {
                        "plugins": [
                            {"name": "available-plugin", "version": "3.0.0"}
                        ]
                    }
                },
            )
            result = scan_plugins(home_dir=tmp_path)

            assert len(result) == 1
            plugin = result[0]
            assert plugin.name == "available-plugin"
            assert plugin.installed_version is None
            assert plugin.available_version == "3.0.0"
            assert plugin.source == "marketplace"
            assert plugin.install_path is None
            assert plugin.marketplace_id == "mp1"


# ------------------------------------------------------------------
# Corrupt plugin.json
# ------------------------------------------------------------------


class TestCorruptPluginJson:
    """plugin.json is invalid JSON."""

    def test_corrupt_plugin_json_uses_unknown_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            install_path = "plugins/broken-plugin"

            # Create the installed_plugins.json
            plugins_dir = tmp_path / ".claude" / "plugins"
            plugins_dir.mkdir(parents=True, exist_ok=True)
            (plugins_dir / "installed_plugins.json").write_text(
                json.dumps(
                    {
                        "version": 2,
                        "plugins": {
                            "broken-plugin@mp1": [
                                {
                                    "scope": "user",
                                    "installPath": str(
                                        tmp_path / install_path
                                    ),
                                    "version": "1.0.0",
                                }
                            ]
                        },
                    }
                ),
                encoding="utf-8",
            )

            # Create a corrupt plugin.json
            plugin_json_dir = (
                tmp_path / install_path / ".claude-plugin"
            )
            plugin_json_dir.mkdir(parents=True, exist_ok=True)
            (plugin_json_dir / "plugin.json").write_text(
                "{invalid json!!!",
                encoding="utf-8",
            )

            # Marketplace data
            _setup_ecosystem(
                tmp_path,
                known_marketplaces={"mp1": {"url": "https://example.com"}},
                marketplaces={
                    "mp1": {
                        "plugins": [
                            {
                                "name": "broken-plugin",
                                "version": "1.0.0",
                            }
                        ]
                    }
                },
            )

            result = scan_plugins(home_dir=tmp_path)

            # Find the installed entry (not the marketplace-only one)
            installed = [
                p for p in result if p.install_path is not None
            ]
            assert len(installed) == 1
            plugin = installed[0]
            assert plugin.name == "broken-plugin"
            assert plugin.installed_version == "unknown"
            assert plugin.dependencies == {}


# ------------------------------------------------------------------
# Dependencies field is not a dict
# ------------------------------------------------------------------


class TestDependenciesNotDict:
    """dependencies field is a string instead of dict."""

    def test_string_dependencies_treated_as_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            install_path = "plugins/bad-deps"
            _setup_ecosystem(
                tmp_path,
                installed={
                    "version": 2,
                    "plugins": {
                        "bad-deps@mp1": [
                            {
                                "scope": "user",
                                "installPath": str(
                                    tmp_path / install_path
                                ),
                                "version": "1.0.0",
                            }
                        ]
                    },
                },
                cache={
                    install_path: {
                        "name": "bad-deps",
                        "version": "1.0.0",
                        "dependencies": "this-is-not-a-dict",
                    }
                },
                known_marketplaces={"mp1": {"url": "https://example.com"}},
                marketplaces={
                    "mp1": {
                        "plugins": [
                            {"name": "bad-deps", "version": "1.0.0"}
                        ]
                    }
                },
            )
            result = scan_plugins(home_dir=tmp_path)

            assert len(result) == 1
            plugin = result[0]
            assert plugin.name == "bad-deps"
            assert plugin.dependencies == {}


# ------------------------------------------------------------------
# Plugin with "unknown" version
# ------------------------------------------------------------------


class TestUnknownVersion:
    """plugin.json exists but version field is missing or non-string."""

    def test_missing_version_field(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            install_path = "plugins/no-version"
            _setup_ecosystem(
                tmp_path,
                installed={
                    "version": 2,
                    "plugins": {
                        "no-version@mp1": [
                            {
                                "scope": "user",
                                "installPath": str(
                                    tmp_path / install_path
                                ),
                                "version": "1.0.0",
                            }
                        ]
                    },
                },
                cache={
                    install_path: {
                        "name": "no-version",
                        # no "version" key
                    }
                },
                known_marketplaces={"mp1": {"url": "https://example.com"}},
                marketplaces={
                    "mp1": {
                        "plugins": [
                            {"name": "no-version", "version": "2.0.0"}
                        ]
                    }
                },
            )
            result = scan_plugins(home_dir=tmp_path)

            assert len(result) == 1
            plugin = result[0]
            assert plugin.name == "no-version"
            assert plugin.installed_version == "unknown"
            assert plugin.available_version == "2.0.0"

    def test_version_is_integer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            install_path = "plugins/int-version"
            _setup_ecosystem(
                tmp_path,
                installed={
                    "version": 2,
                    "plugins": {
                        "int-version@local": [
                            {
                                "scope": "user",
                                "installPath": str(
                                    tmp_path / install_path
                                ),
                                "version": "1.0.0",
                            }
                        ]
                    },
                },
                cache={
                    install_path: {
                        "name": "int-version",
                        "version": 42,
                    }
                },
            )
            result = scan_plugins(home_dir=tmp_path)

            assert len(result) == 1
            plugin = result[0]
            assert plugin.installed_version == "unknown"


# ------------------------------------------------------------------
# Sorting
# ------------------------------------------------------------------


class TestSorting:
    """Results are sorted by plugin name."""

    def test_output_sorted_by_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            _setup_ecosystem(
                tmp_path,
                installed={
                    "version": 2,
                    "plugins": {
                        "zebra@mp1": [
                            {
                                "scope": "user",
                                "installPath": str(
                                    tmp_path / "plugins/zebra"
                                ),
                                "version": "1.0.0",
                            }
                        ],
                        "alpha@mp1": [
                            {
                                "scope": "user",
                                "installPath": str(
                                    tmp_path / "plugins/alpha"
                                ),
                                "version": "1.0.0",
                            }
                        ],
                        "middle@mp1": [
                            {
                                "scope": "user",
                                "installPath": str(
                                    tmp_path / "plugins/middle"
                                ),
                                "version": "1.0.0",
                            }
                        ],
                    },
                },
                cache={
                    "plugins/zebra": {
                        "name": "zebra",
                        "version": "1.0.0",
                    },
                    "plugins/alpha": {
                        "name": "alpha",
                        "version": "1.0.0",
                    },
                    "plugins/middle": {
                        "name": "middle",
                        "version": "1.0.0",
                    },
                },
                known_marketplaces={"mp1": {"url": "https://example.com"}},
                marketplaces={
                    "mp1": {
                        "plugins": [
                            {"name": "zebra", "version": "1.0.0"},
                            {"name": "alpha", "version": "1.0.0"},
                            {"name": "middle", "version": "1.0.0"},
                        ]
                    }
                },
            )
            result = scan_plugins(home_dir=tmp_path)

            names = [p.name for p in result]
            assert names == ["alpha", "middle", "zebra"]


# ------------------------------------------------------------------
# Multi-marketplace preference
# ------------------------------------------------------------------


class TestMultiMarketplace:
    """Prefer marketplace where plugin is currently installed."""

    def test_prefers_installed_marketplace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            install_path = "plugins/shared-plugin"
            _setup_ecosystem(
                tmp_path,
                installed={
                    "version": 2,
                    "plugins": {
                        "shared-plugin@mp-a": [
                            {
                                "scope": "user",
                                "installPath": str(
                                    tmp_path / install_path
                                ),
                                "version": "1.0.0",
                            }
                        ]
                    },
                },
                cache={
                    install_path: {
                        "name": "shared-plugin",
                        "version": "1.0.0",
                    }
                },
                known_marketplaces={
                    "mp-a": {"url": "https://a.example.com"},
                    "mp-b": {"url": "https://b.example.com"},
                },
                marketplaces={
                    "mp-a": {
                        "plugins": [
                            {"name": "shared-plugin", "version": "1.1.0"}
                        ]
                    },
                    "mp-b": {
                        "plugins": [
                            {"name": "shared-plugin", "version": "2.0.0"}
                        ]
                    },
                },
            )
            result = scan_plugins(home_dir=tmp_path)

            assert len(result) == 1
            plugin = result[0]
            assert plugin.marketplace_id == "mp-a"
            assert plugin.available_version == "1.1.0"
            assert plugin.source == "marketplace"
