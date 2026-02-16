"""Unit tests for plugin discovery and configuration utilities.

This test suite covers functionality for discovering installed plugins,
validating their configurations, and generating interactive questions
for the setup wizard.
"""

import json
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
        / "aida-dispatch"
        / "scripts"
    ),
)

from utils.plugins import (
    discover_installed_plugins,
    generate_plugin_checklist,
    generate_plugin_preference_questions,
    get_plugins_with_config,
    validate_plugin_config,
)
from utils.errors import ConfigurationError


class TestDiscoverInstalledPlugins(unittest.TestCase):
    """Test plugin discovery from the cache directory."""

    def setUp(self):
        """Set up temporary directory for tests."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

    def tearDown(self):
        """Clean up temporary directory."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("utils.plugins.get_home_dir")
    def test_discover_empty_dir_returns_empty_list(self, mock_home):
        """Test that an empty cache directory returns empty list."""
        mock_home.return_value = self.temp_path
        plugins = discover_installed_plugins()
        self.assertEqual(plugins, [])

    @patch("utils.plugins.get_home_dir")
    def test_valid_plugins_found(self, mock_home):
        """Test discovery of valid plugin manifests."""
        mock_home.return_value = self.temp_path

        # Create plugin cache structure
        plugin_dir = (
            self.temp_path
            / ".claude"
            / "plugins"
            / "cache"
            / "owner1"
            / "plugin1"
            / ".claude-plugin"
        )
        plugin_dir.mkdir(parents=True, exist_ok=True)

        manifest = {
            "name": "test-plugin",
            "version": "1.0.0",
            "config": {"label": "Test", "description": "Test plugin"},
            "recommendedPermissions": {"file-read": {"rules": ["Read(*)"]}},
        }

        with open(plugin_dir / "plugin.json", "w", encoding="utf-8") as f:
            json.dump(manifest, f)

        plugins = discover_installed_plugins()
        self.assertEqual(len(plugins), 1)
        self.assertEqual(plugins[0]["name"], "test-plugin")
        self.assertEqual(plugins[0]["version"], "1.0.0")
        self.assertIn("config", plugins[0])
        self.assertIn("recommendedPermissions", plugins[0])
        self.assertIn("plugin_dir", plugins[0])

    @patch("utils.plugins.get_home_dir")
    def test_invalid_json_skipped(self, mock_home):
        """Test that plugins with invalid JSON are skipped."""
        mock_home.return_value = self.temp_path

        plugin_dir = (
            self.temp_path
            / ".claude"
            / "plugins"
            / "cache"
            / "owner1"
            / "plugin1"
            / ".claude-plugin"
        )
        plugin_dir.mkdir(parents=True, exist_ok=True)

        # Write invalid JSON
        with open(plugin_dir / "plugin.json", "w", encoding="utf-8") as f:
            f.write("{invalid json")

        plugins = discover_installed_plugins()
        self.assertEqual(plugins, [])

    @patch("utils.plugins.get_home_dir")
    def test_no_plugin_json_skipped(self, mock_home):
        """Test that directories without plugin.json are skipped."""
        mock_home.return_value = self.temp_path

        # Create structure without plugin.json
        plugin_dir = (
            self.temp_path
            / ".claude"
            / "plugins"
            / "cache"
            / "owner1"
            / "plugin1"
            / ".claude-plugin"
        )
        plugin_dir.mkdir(parents=True, exist_ok=True)

        plugins = discover_installed_plugins()
        self.assertEqual(plugins, [])


class TestGetPluginsWithConfig(unittest.TestCase):
    """Test filtering plugins by config section."""

    def test_filters_correctly(self):
        """Test that only plugins with config sections are returned."""
        plugins = [
            {"name": "plugin1", "config": {"label": "Test"}},
            {"name": "plugin2", "config": {}},
            {"name": "plugin3"},
        ]

        filtered = get_plugins_with_config(plugins)
        # Empty config dict is still truthy, but filter uses truthiness
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["name"], "plugin1")

    def test_empty_list(self):
        """Test filtering an empty list."""
        filtered = get_plugins_with_config([])
        self.assertEqual(filtered, [])

    def test_no_config_section_skipped(self):
        """Test that plugins without config sections are skipped."""
        plugins = [
            {"name": "plugin1"},
            {"name": "plugin2", "config": None},
        ]

        filtered = get_plugins_with_config(plugins)
        self.assertEqual(filtered, [])


class TestValidatePluginConfig(unittest.TestCase):
    """Test plugin configuration validation."""

    def test_valid_config_passes(self):
        """Test that a valid config passes validation."""
        config = {
            "label": "Test Plugin",
            "description": "A test plugin",
            "preferences": [
                {
                    "key": "test.key",
                    "type": "boolean",
                    "label": "Test preference",
                }
            ],
        }

        # Should not raise
        validate_plugin_config(config, "test-plugin")

    def test_missing_label_raises(self):
        """Test that missing label field raises error."""
        config = {
            "description": "A test plugin",
            "preferences": [],
        }

        with self.assertRaises(ConfigurationError) as ctx:
            validate_plugin_config(config, "test-plugin")
        self.assertIn("label", str(ctx.exception))

    def test_missing_description_raises(self):
        """Test that missing description field raises error."""
        config = {
            "label": "Test Plugin",
            "preferences": [],
        }

        with self.assertRaises(ConfigurationError) as ctx:
            validate_plugin_config(config, "test-plugin")
        self.assertIn("description", str(ctx.exception))

    def test_missing_preferences_raises(self):
        """Test that missing preferences field raises error."""
        config = {
            "label": "Test Plugin",
            "description": "A test plugin",
        }

        with self.assertRaises(ConfigurationError) as ctx:
            validate_plugin_config(config, "test-plugin")
        self.assertIn("preferences", str(ctx.exception))

    def test_invalid_preference_types_raise(self):
        """Test that invalid preference types raise errors."""
        config = {
            "label": "Test Plugin",
            "description": "A test plugin",
            "preferences": [
                {
                    "key": "test.key",
                    "type": "invalid-type",
                    "label": "Test preference",
                }
            ],
        }

        with self.assertRaises(ConfigurationError) as ctx:
            validate_plugin_config(config, "test-plugin")
        self.assertIn("invalid type", str(ctx.exception))

    def test_choice_missing_options_raises(self):
        """Test that choice preference without options raises error."""
        config = {
            "label": "Test Plugin",
            "description": "A test plugin",
            "preferences": [
                {
                    "key": "test.key",
                    "type": "choice",
                    "label": "Test preference",
                }
            ],
        }

        with self.assertRaises(ConfigurationError) as ctx:
            validate_plugin_config(config, "test-plugin")
        self.assertIn("missing 'options'", str(ctx.exception))

    def test_wrong_field_types_raise(self):
        """Test that wrong field types raise errors."""
        # Non-string label
        config = {
            "label": 123,
            "description": "A test plugin",
            "preferences": [],
        }

        with self.assertRaises(ConfigurationError) as ctx:
            validate_plugin_config(config, "test-plugin")
        self.assertIn("label", str(ctx.exception))
        self.assertIn("must be a string", str(ctx.exception))

        # Non-string description
        config = {
            "label": "Test Plugin",
            "description": 123,
            "preferences": [],
        }

        with self.assertRaises(ConfigurationError) as ctx:
            validate_plugin_config(config, "test-plugin")
        self.assertIn("description", str(ctx.exception))

        # Non-list preferences
        config = {
            "label": "Test Plugin",
            "description": "A test plugin",
            "preferences": "not a list",
        }

        with self.assertRaises(ConfigurationError) as ctx:
            validate_plugin_config(config, "test-plugin")
        self.assertIn("preferences", str(ctx.exception))
        self.assertIn("must be a list", str(ctx.exception))

    def test_missing_preference_fields_raise(self):
        """Test that preferences missing required fields raise errors."""
        config = {
            "label": "Test Plugin",
            "description": "A test plugin",
            "preferences": [
                {
                    "type": "boolean",
                    "label": "Test preference",
                }
            ],
        }

        with self.assertRaises(ConfigurationError) as ctx:
            validate_plugin_config(config, "test-plugin")
        self.assertIn("missing required field: key", str(ctx.exception))

    def test_choice_options_not_list_raises(self):
        """Test that choice options must be a list."""
        config = {
            "label": "Test Plugin",
            "description": "A test plugin",
            "preferences": [
                {
                    "key": "test.key",
                    "type": "choice",
                    "label": "Test preference",
                    "options": "not a list",
                }
            ],
        }

        with self.assertRaises(ConfigurationError) as ctx:
            validate_plugin_config(config, "test-plugin")
        self.assertIn("'options' must be a list", str(ctx.exception))


class TestGeneratePluginChecklist(unittest.TestCase):
    """Test plugin checklist generation."""

    def test_no_plugins_returns_none(self):
        """Test that empty plugin list returns None."""
        result = generate_plugin_checklist([])
        self.assertIsNone(result)

    def test_single_plugin(self):
        """Test checklist generation with single plugin."""
        plugins = [
            {
                "name": "test-plugin",
                "config": {
                    "label": "Test Plugin",
                    "description": "A test plugin",
                    "preferences": [],
                },
            }
        ]

        result = generate_plugin_checklist(plugins)
        self.assertIsNotNone(result)
        self.assertEqual(result["id"], "selected_plugins")
        self.assertEqual(result["type"], "multiselect")
        self.assertEqual(len(result["options"]), 1)
        self.assertEqual(result["options"][0]["label"], "Test Plugin")
        self.assertEqual(result["options"][0]["value"], "test-plugin")
        self.assertEqual(
            result["options"][0]["description"], "A test plugin"
        )

    def test_multiple_plugins(self):
        """Test checklist generation with multiple plugins."""
        plugins = [
            {
                "name": "plugin1",
                "config": {
                    "label": "Plugin 1",
                    "description": "First plugin",
                    "preferences": [],
                },
            },
            {
                "name": "plugin2",
                "config": {
                    "label": "Plugin 2",
                    "description": "Second plugin",
                    "preferences": [],
                },
            },
        ]

        result = generate_plugin_checklist(plugins)
        self.assertIsNotNone(result)
        self.assertEqual(len(result["options"]), 2)

    def test_invalid_config_skipped(self):
        """Test that plugins with invalid config are skipped."""
        plugins = [
            {
                "name": "valid-plugin",
                "config": {
                    "label": "Valid Plugin",
                    "description": "A valid plugin",
                    "preferences": [],
                },
            },
            {
                "name": "invalid-plugin",
                "config": {
                    "label": "Invalid Plugin",
                    # Missing description
                    "preferences": [],
                },
            },
        ]

        result = generate_plugin_checklist(plugins)
        self.assertIsNotNone(result)
        self.assertEqual(len(result["options"]), 1)
        self.assertEqual(result["options"][0]["value"], "valid-plugin")


class TestGeneratePluginPreferenceQuestions(unittest.TestCase):
    """Test preference question generation."""

    def test_boolean_type_mapped_correctly(self):
        """Test that boolean type is mapped correctly."""
        plugins = [
            {
                "name": "test-plugin",
                "config": {
                    "preferences": [
                        {
                            "key": "feature.enabled",
                            "type": "boolean",
                            "label": "Enable feature",
                        }
                    ]
                },
            }
        ]

        questions = generate_plugin_preference_questions(
            ["test-plugin"], plugins
        )
        self.assertEqual(len(questions), 1)
        self.assertEqual(questions[0]["type"], "boolean")

    def test_choice_type_mapped_correctly(self):
        """Test that choice type is mapped correctly."""
        plugins = [
            {
                "name": "test-plugin",
                "config": {
                    "preferences": [
                        {
                            "key": "log.level",
                            "type": "choice",
                            "label": "Log level",
                            "options": ["debug", "info", "warn"],
                        }
                    ]
                },
            }
        ]

        questions = generate_plugin_preference_questions(
            ["test-plugin"], plugins
        )
        self.assertEqual(len(questions), 1)
        self.assertEqual(questions[0]["type"], "choice")
        self.assertEqual(len(questions[0]["options"]), 3)

    def test_string_type_mapped_correctly(self):
        """Test that string type is mapped to text."""
        plugins = [
            {
                "name": "test-plugin",
                "config": {
                    "preferences": [
                        {
                            "key": "api.key",
                            "type": "string",
                            "label": "API Key",
                        }
                    ]
                },
            }
        ]

        questions = generate_plugin_preference_questions(
            ["test-plugin"], plugins
        )
        self.assertEqual(len(questions), 1)
        self.assertEqual(questions[0]["type"], "text")

    def test_default_values_included(self):
        """Test that default values are included in questions."""
        plugins = [
            {
                "name": "test-plugin",
                "config": {
                    "preferences": [
                        {
                            "key": "feature.enabled",
                            "type": "boolean",
                            "label": "Enable feature",
                            "default": True,
                        }
                    ]
                },
            }
        ]

        questions = generate_plugin_preference_questions(
            ["test-plugin"], plugins
        )
        self.assertEqual(len(questions), 1)
        self.assertEqual(questions[0]["default"], True)

    def test_empty_selection_returns_empty_list(self):
        """Test that empty selection returns empty list."""
        plugins = [
            {
                "name": "test-plugin",
                "config": {
                    "preferences": [
                        {
                            "key": "test.key",
                            "type": "string",
                            "label": "Test",
                        }
                    ]
                },
            }
        ]

        questions = generate_plugin_preference_questions([], plugins)
        self.assertEqual(questions, [])

    def test_unknown_plugin_name_skipped(self):
        """Test that unknown plugin names are skipped."""
        plugins = [
            {
                "name": "test-plugin",
                "config": {
                    "preferences": [
                        {
                            "key": "test.key",
                            "type": "string",
                            "label": "Test",
                        }
                    ]
                },
            }
        ]

        questions = generate_plugin_preference_questions(
            ["unknown-plugin"], plugins
        )
        self.assertEqual(questions, [])

    def test_question_id_format(self):
        """Test that question IDs are formatted correctly."""
        plugins = [
            {
                "name": "test-plugin",
                "config": {
                    "preferences": [
                        {
                            "key": "some.dotted.key",
                            "type": "string",
                            "label": "Test",
                        }
                    ]
                },
            }
        ]

        questions = generate_plugin_preference_questions(
            ["test-plugin"], plugins
        )
        self.assertEqual(len(questions), 1)
        self.assertEqual(
            questions[0]["id"], "plugin_test-plugin_some_dotted_key"
        )

    def test_description_included_when_present(self):
        """Test that description is included when present."""
        plugins = [
            {
                "name": "test-plugin",
                "config": {
                    "preferences": [
                        {
                            "key": "test.key",
                            "type": "string",
                            "label": "Test",
                            "description": "This is a test preference",
                        }
                    ]
                },
            }
        ]

        questions = generate_plugin_preference_questions(
            ["test-plugin"], plugins
        )
        self.assertEqual(len(questions), 1)
        self.assertEqual(
            questions[0]["description"], "This is a test preference"
        )


if __name__ == "__main__":
    unittest.main()
