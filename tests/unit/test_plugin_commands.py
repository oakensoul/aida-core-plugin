# SPDX-FileCopyrightText: 2026 The AIDA Core Authors
# SPDX-License-Identifier: MPL-2.0

"""Unit tests for plugin-provided /aida command registration.

Covers discovery of the ``commands`` block in aida-config.json,
validation rules, reserved-name protection, and conflict handling.
"""

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# Add scripts directory to path for imports
sys.path.insert(
    0,
    str(
        Path(__file__).parent.parent.parent
        / "skills"
        / "aida"
        / "scripts"
    ),
)

from utils.errors import ConfigurationError
from utils.plugins import (
    RESERVED_COMMAND_NAMES,
    collect_plugin_commands,
    discover_installed_plugins,
    get_plugins_with_commands,
    resolve_plugin_command,
    validate_plugin_commands,
)


def make_plugin(name, commands):
    """Build a plugin dict as discover_installed_plugins returns it."""
    return {
        "name": name,
        "version": "1.0.0",
        "config": {},
        "recommendedPermissions": {},
        "commands": commands,
        "plugin_dir": f"/tmp/{name}",
    }


def command(name="prodoc", skill="prodoc", **overrides):
    """Build a valid command entry, with optional overrides."""
    entry = {
        "name": name,
        "skill": skill,
        "description": "Generate repository documentation",
        "operations": ["generate", "update"],
    }
    entry.update(overrides)
    return entry


class TestValidatePluginCommands(unittest.TestCase):
    """Validation of the commands block."""

    def test_valid_block_passes(self):
        validate_plugin_commands([command()], "prodoc-plugin")

    def test_empty_list_passes(self):
        validate_plugin_commands([], "prodoc-plugin")

    def test_non_list_rejected(self):
        with self.assertRaises(ConfigurationError):
            validate_plugin_commands({"name": "prodoc"}, "p")

    def test_non_object_entry_rejected(self):
        with self.assertRaises(ConfigurationError):
            validate_plugin_commands(["prodoc"], "p")

    def test_missing_required_field_rejected(self):
        for field in ("name", "skill", "description"):
            entry = command()
            del entry[field]
            with self.subTest(field=field):
                with self.assertRaises(ConfigurationError):
                    validate_plugin_commands([entry], "p")

    def test_non_string_field_rejected(self):
        with self.assertRaises(ConfigurationError):
            validate_plugin_commands([command(name=42)], "p")

    def test_invalid_name_shapes_rejected(self):
        for bad in ("Prodoc", "pro_doc", "1prodoc", "p", "", "pro doc", "a" * 51):
            with self.subTest(name=bad):
                with self.assertRaises(ConfigurationError):
                    validate_plugin_commands([command(name=bad)], "p")

    def test_reserved_names_rejected(self):
        for reserved in (
            "config",
            "status",
            "doctor",
            "plugin",
            "memento",
            "about",
            "expert",
            "knowledge",
            "permissions",
        ):
            with self.subTest(name=reserved):
                with self.assertRaises(ConfigurationError):
                    validate_plugin_commands(
                        [command(name=reserved)], "p"
                    )

    def test_invalid_skill_rejected(self):
        with self.assertRaises(ConfigurationError):
            validate_plugin_commands([command(skill="Bad Skill")], "p")

    def test_operations_must_be_a_list(self):
        with self.assertRaises(ConfigurationError):
            validate_plugin_commands(
                [command(operations="generate")], "p"
            )

    def test_invalid_operation_name_rejected(self):
        with self.assertRaises(ConfigurationError):
            validate_plugin_commands(
                [command(operations=["Generate"])], "p"
            )

    def test_operations_optional(self):
        entry = command()
        del entry["operations"]
        validate_plugin_commands([entry], "p")


class TestCollectPluginCommands(unittest.TestCase):
    """Building the routing table."""

    def test_collects_valid_routes(self):
        routes = collect_plugin_commands(
            [make_plugin("prodoc-plugin", [command()])]
        )
        self.assertEqual(len(routes), 1)
        self.assertEqual(routes[0]["name"], "prodoc")
        self.assertEqual(routes[0]["skill"], "prodoc")
        self.assertEqual(routes[0]["plugin"], "prodoc-plugin")
        self.assertEqual(
            routes[0]["operations"], ["generate", "update"]
        )

    def test_plugins_without_commands_ignored(self):
        self.assertEqual(collect_plugin_commands([make_plugin("p", [])]), [])

    def test_invalid_block_skipped_without_breaking_others(self):
        plugins = [
            make_plugin("bad-plugin", [command(name="config")]),
            make_plugin("good-plugin", [command(name="prodoc")]),
        ]
        routes = collect_plugin_commands(plugins)
        self.assertEqual([r["name"] for r in routes], ["prodoc"])

    def test_first_plugin_wins_a_contested_name(self):
        plugins = [
            make_plugin("alpha", [command(name="docs", skill="alpha-docs")]),
            make_plugin("beta", [command(name="docs", skill="beta-docs")]),
        ]
        routes = collect_plugin_commands(plugins)
        self.assertEqual(len(routes), 1)
        self.assertEqual(routes[0]["plugin"], "alpha")

    def test_routes_sorted_by_name(self):
        plugins = [
            make_plugin("z", [command(name="zeta")]),
            make_plugin("a", [command(name="alpha")]),
        ]
        routes = collect_plugin_commands(plugins)
        self.assertEqual([r["name"] for r in routes], ["alpha", "zeta"])

    def test_operations_are_copied_not_shared(self):
        entry = command()
        routes = collect_plugin_commands([make_plugin("p", [entry])])
        routes[0]["operations"].append("mutated")
        self.assertEqual(entry["operations"], ["generate", "update"])


class TestResolvePluginCommand(unittest.TestCase):
    """Resolving one command name."""

    def setUp(self):
        self.plugins = [make_plugin("prodoc-plugin", [command()])]

    def test_resolves_a_registered_command(self):
        route = resolve_plugin_command("prodoc", self.plugins)
        self.assertIsNotNone(route)
        self.assertEqual(route["skill"], "prodoc")

    def test_unknown_command_returns_none(self):
        self.assertIsNone(
            resolve_plugin_command("nosuch", self.plugins)
        )

    def test_reserved_name_never_resolves(self):
        # Even if a plugin somehow declared it, built-ins win.
        plugins = [make_plugin("evil", [dict(command(), name="config")])]
        self.assertIsNone(resolve_plugin_command("config", plugins))

    def test_every_reserved_name_is_protected(self):
        for name in RESERVED_COMMAND_NAMES:
            with self.subTest(name=name):
                self.assertIsNone(
                    resolve_plugin_command(name, self.plugins)
                )


class TestGetPluginsWithCommands(unittest.TestCase):
    """Filtering plugins that register commands."""

    def test_filters_to_plugins_with_commands(self):
        plugins = [
            make_plugin("with", [command()]),
            make_plugin("without", []),
        ]
        result = get_plugins_with_commands(plugins)
        self.assertEqual([p["name"] for p in result], ["with"])


class TestDiscoveryReadsCommands(unittest.TestCase):
    """End-to-end read of commands from the plugin cache."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _install(self, name, aida_config):
        plugin_dir = (
            self.temp_path
            / ".claude"
            / "plugins"
            / "cache"
            / "marketplace"
            / name
            / ".claude-plugin"
        )
        plugin_dir.mkdir(parents=True)
        (plugin_dir / "plugin.json").write_text(
            json.dumps({"name": name, "version": "1.0.0"})
        )
        (plugin_dir / "aida-config.json").write_text(
            json.dumps(aida_config)
        )

    @patch("utils.plugins.get_home_dir")
    def test_commands_surface_from_aida_config(self, mock_home):
        mock_home.return_value = self.temp_path
        self._install("prodoc-plugin", {"commands": [command()]})

        plugins = discover_installed_plugins()
        self.assertEqual(len(plugins), 1)
        self.assertEqual(len(plugins[0]["commands"]), 1)

        routes = collect_plugin_commands(plugins)
        self.assertEqual(routes[0]["name"], "prodoc")

    @patch("utils.plugins.get_home_dir")
    def test_plugin_without_commands_defaults_to_empty(self, mock_home):
        mock_home.return_value = self.temp_path
        self._install("plain-plugin", {"config": {}})

        plugins = discover_installed_plugins()
        self.assertEqual(plugins[0]["commands"], [])


if __name__ == "__main__":
    unittest.main()
