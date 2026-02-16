"""Unit tests for permissions skill modules.

This test suite covers plugin permission scanning, aggregation,
settings management, and the two-phase permissions API.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# Add scripts directories to path for imports
sys.path.insert(
    0,
    str(
        Path(__file__).parent.parent.parent
        / "skills"
        / "permissions"
        / "scripts"
    ),
)
sys.path.insert(
    0,
    str(
        Path(__file__).parent.parent.parent
        / "skills"
        / "aida-dispatch"
        / "scripts"
    ),
)

from aggregator import (
    deduplicate_and_categorize,
    detect_conflicts,
    merge_rules,
)
from scanner import (
    get_installed_plugin_dirs,
    read_plugin_manifest,
    scan_plugins,
)
from rule_validation import validate_rules
from settings_manager import (
    get_settings_path,
    read_all_settings,
    write_permissions,
)
from permissions import audit, execute, get_questions


class TestGetInstalledPluginDirs(unittest.TestCase):
    """Test plugin directory discovery."""

    def setUp(self):
        """Set up temporary directory for tests."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

    def tearDown(self):
        """Clean up temporary directory."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("scanner.get_home_dir")
    def test_empty_cache(self, mock_home):
        """Test that empty cache returns empty list."""
        mock_home.return_value = self.temp_path
        dirs = get_installed_plugin_dirs()
        self.assertEqual(dirs, [])

    @patch("scanner.get_home_dir")
    def test_plugins_found(self, mock_home):
        """Test that plugin directories are found."""
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

        dirs = get_installed_plugin_dirs()
        self.assertEqual(len(dirs), 1)
        self.assertTrue(dirs[0].name == ".claude-plugin")

    @patch("scanner.get_home_dir")
    def test_non_dir_entries_skipped(self, mock_home):
        """Test that non-directory entries are skipped."""
        mock_home.return_value = self.temp_path

        cache_root = (
            self.temp_path / ".claude" / "plugins" / "cache" / "owner1"
        )
        cache_root.mkdir(parents=True, exist_ok=True)

        # Create a file instead of directory
        (cache_root / "plugin1").mkdir(parents=True)
        (cache_root / "plugin1" / ".claude-plugin").touch()

        dirs = get_installed_plugin_dirs()
        self.assertEqual(dirs, [])


class TestReadPluginManifest(unittest.TestCase):
    """Test plugin manifest reading."""

    def setUp(self):
        """Set up temporary directory for tests."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

    def tearDown(self):
        """Clean up temporary directory."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_valid_manifest(self):
        """Test reading a valid manifest."""
        plugin_dir = self.temp_path / ".claude-plugin"
        plugin_dir.mkdir(parents=True)

        manifest = {"name": "test-plugin", "version": "1.0.0"}
        with open(plugin_dir / "plugin.json", "w", encoding="utf-8") as f:
            json.dump(manifest, f)

        result = read_plugin_manifest(plugin_dir)
        self.assertIsNotNone(result)
        self.assertEqual(result["name"], "test-plugin")

    def test_missing_file_returns_none(self):
        """Test that missing manifest returns None."""
        plugin_dir = self.temp_path / ".claude-plugin"
        plugin_dir.mkdir(parents=True)

        result = read_plugin_manifest(plugin_dir)
        self.assertIsNone(result)

    def test_invalid_json_returns_none(self):
        """Test that invalid JSON returns None."""
        plugin_dir = self.temp_path / ".claude-plugin"
        plugin_dir.mkdir(parents=True)

        with open(plugin_dir / "plugin.json", "w", encoding="utf-8") as f:
            f.write("{invalid json")

        result = read_plugin_manifest(plugin_dir)
        self.assertIsNone(result)

    def test_large_manifest_returns_none(self):
        """Test that manifests over 1MB are rejected."""
        plugin_dir = self.temp_path / ".claude-plugin"
        plugin_dir.mkdir(parents=True)

        # Create a large manifest
        with open(plugin_dir / "plugin.json", "w", encoding="utf-8") as f:
            f.write("{" + '"x": "' + ("a" * 1024 * 1024) + '"' + "}")

        result = read_plugin_manifest(plugin_dir)
        self.assertIsNone(result)


class TestScanPlugins(unittest.TestCase):
    """Test plugin permission scanning."""

    def setUp(self):
        """Set up temporary directory for tests."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

    def tearDown(self):
        """Clean up temporary directory."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("scanner.get_home_dir")
    def test_no_plugins(self, mock_home):
        """Test scanning with no plugins."""
        mock_home.return_value = self.temp_path
        results = scan_plugins()
        self.assertEqual(results, [])

    @patch("scanner.get_home_dir")
    def test_plugins_with_permissions(self, mock_home):
        """Test scanning plugins with permissions."""
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
        plugin_dir.mkdir(parents=True)

        manifest = {
            "name": "test-plugin",
            "recommendedPermissions": {
                "file-read": {"rules": ["Read(*)"]}
            },
        }
        with open(plugin_dir / "plugin.json", "w", encoding="utf-8") as f:
            json.dump(manifest, f)

        results = scan_plugins()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "test-plugin")
        self.assertIn("permissions", results[0])

    @patch("scanner.get_home_dir")
    def test_plugins_without_permissions_skipped(self, mock_home):
        """Test that plugins without permissions are skipped."""
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
        plugin_dir.mkdir(parents=True)

        manifest = {"name": "test-plugin"}
        with open(plugin_dir / "plugin.json", "w", encoding="utf-8") as f:
            json.dump(manifest, f)

        results = scan_plugins()
        self.assertEqual(results, [])

    @patch("scanner.get_home_dir")
    def test_invalid_rules_filtered_at_scan_time(self, mock_home):
        """Test that plugins with invalid rules are skipped."""
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
        plugin_dir.mkdir(parents=True)

        manifest = {
            "name": "bad-rules-plugin",
            "recommendedPermissions": {
                "file-read": {
                    "rules": ["Read(*)"],
                    "suggested": "allow",
                },
                "dangerous": {
                    "rules": ["$(evil command)"],
                    "suggested": "deny",
                },
            },
        }
        with open(
            plugin_dir / "plugin.json", "w", encoding="utf-8"
        ) as f:
            json.dump(manifest, f)

        results = scan_plugins()
        self.assertEqual(len(results), 1)
        # Only valid category survives
        self.assertIn("file-read", results[0]["permissions"])
        self.assertNotIn("dangerous", results[0]["permissions"])

    @patch("scanner.get_home_dir")
    def test_all_categories_invalid_skips_plugin(self, mock_home):
        """Test that plugin is skipped if all categories invalid."""
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
        plugin_dir.mkdir(parents=True)

        manifest = {
            "name": "all-bad-plugin",
            "recommendedPermissions": {
                "dangerous": {
                    "rules": ["$(evil command)"],
                    "suggested": "deny",
                },
            },
        }
        with open(
            plugin_dir / "plugin.json", "w", encoding="utf-8"
        ) as f:
            json.dump(manifest, f)

        results = scan_plugins()
        self.assertEqual(results, [])


class TestMergeRules(unittest.TestCase):
    """Test rule merging and subsumption."""

    def test_basic_dedup(self):
        """Test basic deduplication of rules."""
        rules_lists = [
            ["Bash(git:*)", "Read(*.py)"],
            ["Bash(git:*)", "Write(*.txt)"],
        ]

        merged = merge_rules(rules_lists)
        self.assertEqual(len(merged), 3)
        self.assertIn("Bash(git:*)", merged)
        self.assertIn("Read(*.py)", merged)
        self.assertIn("Write(*.txt)", merged)

    def test_wildcard_subsumption(self):
        """Test that broader wildcards subsume narrower ones."""
        rules_lists = [
            ["Bash(git:*)", "Bash(git commit:*)"],
        ]

        merged = merge_rules(rules_lists)
        self.assertEqual(len(merged), 1)
        self.assertIn("Bash(git:*)", merged)
        self.assertNotIn("Bash(git commit:*)", merged)

    def test_no_subsumption_for_different_tools(self):
        """Test that subsumption only works for same tool."""
        rules_lists = [
            ["Bash(git:*)", "Read(git:*)"],
        ]

        merged = merge_rules(rules_lists)
        self.assertEqual(len(merged), 2)
        self.assertIn("Bash(git:*)", merged)
        self.assertIn("Read(git:*)", merged)

    def test_prefix_subsumption(self):
        """Test prefix-based wildcard subsumption."""
        rules_lists = [
            ["Bash(git*)", "Bash(github*)"],
        ]

        merged = merge_rules(rules_lists)
        self.assertEqual(len(merged), 1)
        self.assertIn("Bash(git*)", merged)


class TestDeduplicateAndCategorize(unittest.TestCase):
    """Test permission deduplication and categorization."""

    def test_single_plugin(self):
        """Test deduplication with single plugin."""
        plugin_permissions = [
            {
                "name": "plugin1",
                "permissions": {
                    "file-read": {
                        "rules": ["Read(*)"],
                        "suggested": "allow",
                    }
                },
            }
        ]

        result = deduplicate_and_categorize(plugin_permissions)
        self.assertIn("categories", result)
        self.assertIn("file-read", result["categories"])
        self.assertEqual(
            result["categories"]["file-read"]["rules"], ["Read(*)"]
        )
        self.assertEqual(
            result["categories"]["file-read"]["suggested"], "allow"
        )

    def test_multiple_plugins_merged(self):
        """Test merging permissions from multiple plugins."""
        plugin_permissions = [
            {
                "name": "plugin1",
                "permissions": {
                    "file-read": {
                        "rules": ["Read(*.py)"],
                        "suggested": "allow",
                    }
                },
            },
            {
                "name": "plugin2",
                "permissions": {
                    "file-read": {
                        "rules": ["Read(*.js)"],
                        "suggested": "ask",
                    }
                },
            },
        ]

        result = deduplicate_and_categorize(plugin_permissions)
        self.assertIn("file-read", result["categories"])
        self.assertEqual(len(result["categories"]["file-read"]["rules"]), 2)
        self.assertIn("plugin1", result["categories"]["file-read"]["sources"])
        self.assertIn("plugin2", result["categories"]["file-read"]["sources"])
        # Least permissive suggestion wins (ask < allow)
        self.assertEqual(
            result["categories"]["file-read"]["suggested"], "ask"
        )

    def test_unknown_categories_get_default_metadata(self):
        """Test that unknown categories get default metadata."""
        plugin_permissions = [
            {
                "name": "plugin1",
                "permissions": {
                    "custom-category": {
                        "rules": ["Custom(*)"],
                        "suggested": "ask",
                    }
                },
            }
        ]

        result = deduplicate_and_categorize(plugin_permissions)
        self.assertIn("custom-category", result["categories"])
        cat = result["categories"]["custom-category"]
        self.assertEqual(cat["label"], "Custom Category")
        self.assertIn("Permissions for custom-category", cat["description"])

    def test_least_permissive_suggestion_wins(self):
        """Test that least permissive suggestion is chosen."""
        plugin_permissions = [
            {
                "name": "plugin1",
                "permissions": {
                    "git": {"rules": ["Bash(git:*)"], "suggested": "deny"}
                },
            },
            {
                "name": "plugin2",
                "permissions": {
                    "git": {"rules": ["Bash(git:*)"], "suggested": "ask"}
                },
            },
            {
                "name": "plugin3",
                "permissions": {
                    "git": {"rules": ["Bash(git:*)"], "suggested": "allow"}
                },
            },
        ]

        result = deduplicate_and_categorize(plugin_permissions)
        # deny > ask > allow in priority, so deny wins
        self.assertEqual(result["categories"]["git"]["suggested"], "deny")

    def test_suggestion_conflict_skips_subsumption(self):
        """Test that conflicting suggestions skip subsumption."""
        plugin_permissions = [
            {
                "name": "plugin1",
                "permissions": {
                    "git": {
                        "rules": ["Bash(git:*)"],
                        "suggested": "allow",
                    }
                },
            },
            {
                "name": "plugin2",
                "permissions": {
                    "git": {
                        "rules": ["Bash(git commit:*)"],
                        "suggested": "deny",
                    }
                },
            },
        ]

        result = deduplicate_and_categorize(plugin_permissions)
        cat = result["categories"]["git"]
        # When suggestions conflict, both rules preserved
        # (no subsumption of git commit:* under git:*)
        self.assertEqual(len(cat["rules"]), 2)
        self.assertIn("Bash(git:*)", cat["rules"])
        self.assertIn("Bash(git commit:*)", cat["rules"])
        self.assertTrue(cat["suggestion_conflict"])

    def test_no_suggestion_conflict_applies_subsumption(self):
        """Test that agreeing suggestions apply subsumption."""
        plugin_permissions = [
            {
                "name": "plugin1",
                "permissions": {
                    "git": {
                        "rules": ["Bash(git:*)"],
                        "suggested": "allow",
                    }
                },
            },
            {
                "name": "plugin2",
                "permissions": {
                    "git": {
                        "rules": ["Bash(git commit:*)"],
                        "suggested": "allow",
                    }
                },
            },
        ]

        result = deduplicate_and_categorize(plugin_permissions)
        cat = result["categories"]["git"]
        # Same suggestion: subsumption applies
        self.assertEqual(cat["rules"], ["Bash(git:*)"])
        self.assertFalse(cat["suggestion_conflict"])


class TestDetectConflicts(unittest.TestCase):
    """Test permission conflict detection."""

    def test_no_conflicts(self):
        """Test that no conflicts are detected when none exist."""
        current = {"allow": ["Read(*)"], "ask": [], "deny": []}
        proposed = {"allow": ["Read(*)"], "ask": [], "deny": []}

        conflicts = detect_conflicts(current, proposed)
        self.assertEqual(conflicts, [])

    def test_allow_vs_deny_conflict_detected(self):
        """Test that allow vs deny conflicts are detected."""
        current = {"allow": ["Bash(git:*)"], "ask": [], "deny": []}
        proposed = {"allow": [], "ask": [], "deny": ["Bash(git:*)"]}

        conflicts = detect_conflicts(current, proposed)
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]["rule"], "Bash(git:*)")
        self.assertEqual(conflicts[0]["current_action"], "allow")
        self.assertEqual(conflicts[0]["proposed_action"], "deny")

    def test_same_action_no_conflict(self):
        """Test that same action doesn't create conflict."""
        current = {"allow": ["Read(*)"], "ask": [], "deny": []}
        proposed = {"allow": ["Read(*)"], "ask": [], "deny": []}

        conflicts = detect_conflicts(current, proposed)
        self.assertEqual(conflicts, [])

    def test_category_inferred(self):
        """Test that category is inferred for conflicts."""
        current = {"allow": ["Read(*)"], "ask": [], "deny": []}
        proposed = {"allow": [], "ask": ["Read(*)"], "deny": []}

        conflicts = detect_conflicts(current, proposed)
        self.assertEqual(len(conflicts), 1)
        self.assertIn("category", conflicts[0])


class TestGetSettingsPath(unittest.TestCase):
    """Test settings path resolution."""

    @patch("settings_manager.get_home_dir")
    def test_user_path_correct(self, mock_home):
        """Test user scope path resolution."""
        mock_home.return_value = Path("/home/test")
        path = get_settings_path("user")
        self.assertEqual(
            path, Path("/home/test") / ".claude" / "settings.json"
        )

    @patch("settings_manager.Path.cwd")
    def test_project_path_correct(self, mock_cwd):
        """Test project scope path resolution."""
        mock_cwd.return_value = Path("/project")
        path = get_settings_path("project")
        self.assertEqual(path, Path("/project") / ".claude" / "settings.json")

    @patch("settings_manager.Path.cwd")
    def test_local_path_correct(self, mock_cwd):
        """Test local scope path resolution."""
        mock_cwd.return_value = Path("/project")
        path = get_settings_path("local")
        self.assertEqual(
            path, Path("/project") / ".claude" / "settings.local.json"
        )

    def test_invalid_scope_raises_valueerror(self):
        """Test that invalid scope raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            get_settings_path("invalid")
        self.assertIn("Unknown scope", str(ctx.exception))


class TestValidateRules(unittest.TestCase):
    """Test rule syntax validation."""

    def test_valid_rules_pass(self):
        """Test that valid rules pass validation."""
        rules = ["Bash(git:*)", "Read(*.py)", "Write(*)", "Edit(test.txt)"]
        valid, error = validate_rules(rules)
        self.assertTrue(valid)
        self.assertIsNone(error)

    def test_invalid_syntax_fails(self):
        """Test that invalid syntax fails validation."""
        rules = ["invalid-rule"]
        valid, error = validate_rules(rules)
        self.assertFalse(valid)
        self.assertIsNotNone(error)
        self.assertIn("Invalid rule syntax", error)

    def test_non_string_fails(self):
        """Test that non-string rules fail validation."""
        rules = [123]
        valid, error = validate_rules(rules)
        self.assertFalse(valid)
        self.assertIsNotNone(error)
        self.assertIn("must be a string", error)

    def test_non_ascii_rejected(self):
        """Test that non-ASCII characters are rejected."""
        # Greek omicron instead of Latin 'o' (homoglyph)
        rules = ["Bash(git c\u03bfmmit:*)"]
        valid, error = validate_rules(rules)
        self.assertFalse(valid)
        self.assertIsNotNone(error)
        self.assertIn("non-ASCII", error)

    def test_rule_too_long_rejected(self):
        """Test that rules exceeding max length are rejected."""
        rules = ["Bash(" + "a" * 500 + ":*)"]
        valid, error = validate_rules(rules)
        self.assertFalse(valid)
        self.assertIsNotNone(error)
        self.assertIn("too long", error)

    def test_error_message_includes_example(self):
        """Test that error messages include format examples."""
        rules = ["bad-rule"]
        valid, error = validate_rules(rules)
        self.assertFalse(valid)
        self.assertIn("Bash(git commit:*)", error)


class TestReadAllSettings(unittest.TestCase):
    """Test reading settings from all scopes."""

    def setUp(self):
        """Set up temporary directory for tests."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

    def tearDown(self):
        """Clean up temporary directory."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("settings_manager.get_home_dir")
    @patch("settings_manager.Path.cwd")
    def test_reads_from_all_scopes(self, mock_cwd, mock_home):
        """Test that settings are read from all scopes."""
        mock_home.return_value = self.temp_path
        mock_cwd.return_value = self.temp_path

        # Create user settings
        user_dir = self.temp_path / ".claude"
        user_dir.mkdir(parents=True)
        user_settings = {"allow": ["Read(*)"]}
        with open(user_dir / "settings.json", "w", encoding="utf-8") as f:
            json.dump(user_settings, f)

        settings = read_all_settings()
        self.assertIn("user", settings)
        self.assertIn("project", settings)
        self.assertIn("local", settings)

    @patch("settings_manager.get_home_dir")
    @patch("settings_manager.Path.cwd")
    def test_missing_files_return_empty_dict(self, mock_cwd, mock_home):
        """Test that missing settings files return empty dict."""
        mock_home.return_value = self.temp_path
        mock_cwd.return_value = self.temp_path

        settings = read_all_settings()
        self.assertEqual(settings["user"], {})
        self.assertEqual(settings["project"], {})
        self.assertEqual(settings["local"], {})


class TestWritePermissions(unittest.TestCase):
    """Test writing permissions to settings files."""

    def setUp(self):
        """Set up temporary directory for tests."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

    def tearDown(self):
        """Clean up temporary directory."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("settings_manager.get_home_dir")
    def test_merge_strategy_adds_rules(self, mock_home):
        """Test that merge strategy adds to existing rules."""
        mock_home.return_value = self.temp_path

        user_dir = self.temp_path / ".claude"
        user_dir.mkdir(parents=True)

        # Create existing settings
        existing = {"allow": ["Read(*)"]}
        with open(user_dir / "settings.json", "w", encoding="utf-8") as f:
            json.dump(existing, f)

        # Write additional rules
        new_rules = {"allow": ["Write(*)"]}
        success = write_permissions("user", new_rules, merge_strategy="merge")

        self.assertTrue(success)

        # Read back and verify
        with open(user_dir / "settings.json", encoding="utf-8") as f:
            result = json.load(f)
        self.assertIn("Read(*)", result["allow"])
        self.assertIn("Write(*)", result["allow"])

    @patch("settings_manager.get_home_dir")
    def test_replace_strategy_overwrites(self, mock_home):
        """Test that replace strategy overwrites existing rules."""
        mock_home.return_value = self.temp_path

        user_dir = self.temp_path / ".claude"
        user_dir.mkdir(parents=True)

        # Create existing settings
        existing = {"allow": ["Read(*)"], "ask": ["Write(*)"]}
        with open(user_dir / "settings.json", "w", encoding="utf-8") as f:
            json.dump(existing, f)

        # Replace rules
        new_rules = {"allow": ["Edit(*)"]}
        success = write_permissions(
            "user", new_rules, merge_strategy="replace"
        )

        self.assertTrue(success)

        # Read back and verify
        with open(user_dir / "settings.json", encoding="utf-8") as f:
            result = json.load(f)
        self.assertEqual(result["allow"], ["Edit(*)"])
        self.assertNotIn("ask", result)

    @patch("settings_manager.get_home_dir")
    def test_invalid_rules_raise_valueerror(self, mock_home):
        """Test that invalid rules raise ValueError."""
        mock_home.return_value = self.temp_path

        rules = {"allow": ["invalid-rule"]}
        with self.assertRaises(ValueError):
            write_permissions("user", rules)

    @patch("settings_manager.get_home_dir")
    def test_creates_parent_directories(self, mock_home):
        """Test that parent directories are created."""
        mock_home.return_value = self.temp_path

        rules = {"allow": ["Read(*)"]}
        success = write_permissions("user", rules)

        self.assertTrue(success)
        self.assertTrue((self.temp_path / ".claude").is_dir())


class TestPermissionsGetQuestions(unittest.TestCase):
    """Test permissions two-phase API get_questions."""

    @patch("permissions.scan_plugins")
    @patch("permissions.read_all_settings")
    def test_returns_preset_question(self, mock_read, mock_scan):
        """Test that preset question is returned."""
        mock_scan.return_value = []
        mock_read.return_value = {"user": {}, "project": {}, "local": {}}

        result = get_questions({})
        self.assertIn("questions", result)
        questions = result["questions"]

        # Find preset question
        preset_q = next(q for q in questions if q["id"] == "preset")
        self.assertEqual(preset_q["type"], "choice")
        self.assertEqual(len(preset_q["choices"]), 4)  # 3 presets + custom

    @patch("permissions.scan_plugins")
    @patch("permissions.read_all_settings")
    def test_returns_scope_question(self, mock_read, mock_scan):
        """Test that scope question is returned."""
        mock_scan.return_value = []
        mock_read.return_value = {"user": {}, "project": {}, "local": {}}

        result = get_questions({})
        questions = result["questions"]

        scope_q = next(q for q in questions if q["id"] == "scope")
        self.assertEqual(scope_q["type"], "choice")
        self.assertEqual(len(scope_q["choices"]), 3)  # user, project, local

    @patch("permissions.scan_plugins")
    @patch("permissions.read_all_settings")
    def test_returns_category_questions(self, mock_read, mock_scan):
        """Test that category questions are returned."""
        mock_scan.return_value = [
            {
                "name": "plugin1",
                "permissions": {
                    "file-read": {"rules": ["Read(*)"], "suggested": "allow"}
                },
            }
        ]
        mock_read.return_value = {"user": {}, "project": {}, "local": {}}

        result = get_questions({})
        questions = result["questions"]

        cat_q = next(
            q for q in questions if q["id"] == "category_file-read"
        )
        self.assertEqual(cat_q["type"], "choice")
        self.assertEqual(len(cat_q["choices"]), 3)  # allow, ask, deny


class TestPermissionsExecute(unittest.TestCase):
    """Test permissions two-phase API execute."""

    def setUp(self):
        """Set up temporary directory for tests."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

    def tearDown(self):
        """Clean up temporary directory."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("settings_manager.get_home_dir")
    def test_preset_applies_correctly(self, mock_home):
        """Test that preset applies permissions correctly."""
        mock_home.return_value = self.temp_path

        context = {
            "categories": {
                "file-read": {
                    "rules": ["Read(*)"],
                    "suggested": "ask",
                }
            }
        }
        responses = {
            "preset": "developer-workstation",
            "scope": "user",
        }

        result = execute(context, responses)
        self.assertTrue(result["success"])
        self.assertGreater(result["rules_count"], 0)

    @patch("settings_manager.get_home_dir")
    def test_custom_choices_work(self, mock_home):
        """Test that custom category choices work."""
        mock_home.return_value = self.temp_path

        context = {
            "categories": {
                "file-read": {
                    "rules": ["Read(*)"],
                    "suggested": "ask",
                }
            }
        }
        responses = {
            "preset": "custom",
            "scope": "user",
            "category_file-read": "deny",
        }

        result = execute(context, responses)
        self.assertTrue(result["success"])

        # Read back and verify
        user_dir = self.temp_path / ".claude"
        with open(user_dir / "settings.json", encoding="utf-8") as f:
            settings = json.load(f)
        self.assertIn("Read(*)", settings.get("deny", []))

    @patch("settings_manager.get_home_dir")
    def test_writes_to_correct_scope(self, mock_home):
        """Test that permissions are written to correct scope."""
        mock_home.return_value = self.temp_path

        context = {
            "categories": {
                "file-read": {
                    "rules": ["Read(*)"],
                    "suggested": "allow",
                }
            }
        }
        responses = {
            "preset": "developer-workstation",
            "scope": "user",
        }

        result = execute(context, responses)
        self.assertTrue(result["success"])
        self.assertTrue(
            str(self.temp_path / ".claude" / "settings.json")
            in result["files_modified"][0]
        )


class TestPermissionsAudit(unittest.TestCase):
    """Test permissions audit functionality."""

    @patch("permissions.scan_plugins")
    @patch("permissions.read_all_settings")
    def test_returns_coverage(self, mock_read, mock_scan):
        """Test that audit returns coverage information."""
        mock_scan.return_value = [
            {
                "name": "plugin1",
                "permissions": {
                    "file-read": {
                        "rules": ["Read(*)", "Grep(*)"],
                        "suggested": "allow",
                    }
                },
            }
        ]
        mock_read.return_value = {
            "user": {"allow": ["Read(*)"]},
            "project": {},
            "local": {},
        }

        result = audit({})
        self.assertIn("coverage", result)
        self.assertEqual(result["coverage"]["total_recommended"], 2)
        self.assertEqual(result["coverage"]["covered"], 1)

    @patch("permissions.scan_plugins")
    @patch("permissions.read_all_settings")
    def test_returns_gaps(self, mock_read, mock_scan):
        """Test that audit returns permission gaps."""
        mock_scan.return_value = [
            {
                "name": "plugin1",
                "permissions": {
                    "file-read": {
                        "rules": ["Read(*)", "Grep(*)"],
                        "suggested": "allow",
                    }
                },
            }
        ]
        mock_read.return_value = {
            "user": {"allow": ["Read(*)"]},
            "project": {},
            "local": {},
        }

        result = audit({})
        self.assertIn("gaps", result)
        self.assertIn("Grep(*)", result["gaps"])

    @patch("permissions.scan_plugins")
    @patch("permissions.read_all_settings")
    def test_returns_conflicts(self, mock_read, mock_scan):
        """Test that audit returns conflicts."""
        mock_scan.return_value = [
            {
                "name": "plugin1",
                "permissions": {
                    "file-read": {
                        "rules": ["Read(*)"],
                        "suggested": "allow",
                    }
                },
            }
        ]
        mock_read.return_value = {
            "user": {"deny": ["Read(*)"]},
            "project": {},
            "local": {},
        }

        result = audit({})
        self.assertIn("conflicts", result)
        self.assertGreater(len(result["conflicts"]), 0)


if __name__ == "__main__":
    unittest.main()
