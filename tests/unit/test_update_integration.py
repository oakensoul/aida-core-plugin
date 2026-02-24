"""Integration tests for plugin update end-to-end flow."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# Add scripts directories to path
_project_root = Path(__file__).parent.parent.parent
_plugin_scripts = (
    _project_root / "skills" / "plugin-manager" / "scripts"
)
sys.path.insert(0, str(_project_root / "scripts"))
sys.path.insert(0, str(_plugin_scripts))

# Clear cached operations modules to avoid cross-manager
# conflicts in pytest
for _mod_name in list(sys.modules):
    if _mod_name == "operations" or _mod_name.startswith(
        "operations."
    ):
        del sys.modules[_mod_name]

from operations import update as update_mod  # noqa: E402
from operations import scaffold as scaffold_mod  # noqa: E402
from operations.constants import (  # noqa: E402
    GENERATOR_VERSION,
)

_GIT_MOCK_PATH = (
    "operations.scaffold_ops.context.infer_git_config"
)
_GIT_MOCK_RETURN = {
    "author_name": "Test Author",
    "author_email": "test@test.com",
}
_GIT_INIT_PATH = (
    "operations.scaffold_ops.generators.initialize_git"
)
_GIT_COMMIT_PATH = (
    "operations.scaffold_ops.generators"
    ".create_initial_commit"
)


def _scaffold_plugin(
    tmp_dir: str,
    name: str = "int-test-plugin",
    language: str = "python",
) -> Path:
    """Scaffold a real plugin in a temp directory.

    Returns:
        Path to the created plugin directory.
    """
    target = str(Path(tmp_dir) / name)
    context = {
        "operation": "scaffold",
        "plugin_name": name,
        "description": (
            "A test plugin for integration testing"
        ),
        "language": language,
        "license": "MIT",
        "author_name": "Test Author",
        "author_email": "test@test.com",
        "target_directory": target,
        "include_agent_stub": False,
        "include_skill_stub": False,
        "keywords": "test",
    }
    result = scaffold_mod.execute(context)
    assert result["success"], (
        f"Scaffold failed: {result.get('message')}"
    )
    return Path(result["path"])


class TestUpdatePhase1(unittest.TestCase):
    """Tests for update_mod.get_questions (Phase 1)."""

    def test_missing_plugin_path_returns_error(self):
        """Should return error when plugin_path is missing."""
        context: dict = {"operation": "update"}
        result = update_mod.get_questions(context)
        self.assertFalse(result["success"])
        self.assertIn("plugin_path", result["message"])

    def test_invalid_plugin_returns_error(self):
        """Should return error for a non-plugin directory."""
        with tempfile.TemporaryDirectory() as tmp:
            context = {
                "operation": "update",
                "plugin_path": tmp,
            }
            result = update_mod.get_questions(context)
            self.assertFalse(result["success"])
            self.assertIn(
                "plugin.json", result["message"]
            )

    @patch(
        _GIT_COMMIT_PATH,
        return_value=True,
    )
    @patch(
        _GIT_INIT_PATH,
        return_value=True,
    )
    @patch(
        _GIT_MOCK_PATH,
        return_value=_GIT_MOCK_RETURN,
    )
    def test_up_to_date_plugin_no_questions(
        self, _mock_git, _mock_init, _mock_commit
    ):
        """Fresh scaffolded plugin should need no updates."""
        with tempfile.TemporaryDirectory() as tmp:
            plugin_dir = _scaffold_plugin(tmp)
            context = {
                "operation": "update",
                "plugin_path": str(plugin_dir),
            }
            result = update_mod.get_questions(context)

            self.assertEqual(result["questions"], [])
            self.assertFalse(
                result["inferred"]["scan_result"][
                    "needs_update"
                ]
            )

    @patch(
        _GIT_COMMIT_PATH,
        return_value=True,
    )
    @patch(
        _GIT_INIT_PATH,
        return_value=True,
    )
    @patch(
        _GIT_MOCK_PATH,
        return_value=_GIT_MOCK_RETURN,
    )
    def test_outdated_plugin_has_questions(
        self, _mock_git, _mock_init, _mock_commit
    ):
        """Outdated boilerplate should produce questions."""
        with tempfile.TemporaryDirectory() as tmp:
            plugin_dir = _scaffold_plugin(tmp)
            # Modify a boilerplate file to make it outdated
            ml_path = plugin_dir / ".markdownlint.json"
            ml_path.write_text('{"old": "config"}\n')

            context = {
                "operation": "update",
                "plugin_path": str(plugin_dir),
            }
            result = update_mod.get_questions(context)

            self.assertGreater(
                len(result["questions"]), 0
            )
            scan = result["inferred"]["scan_result"]
            self.assertTrue(scan["needs_update"])
            outdated_paths = [
                f["path"]
                for f in scan["outdated_files"]
            ]
            self.assertIn(
                ".markdownlint.json", outdated_paths
            )

    @patch(
        _GIT_COMMIT_PATH,
        return_value=True,
    )
    @patch(
        _GIT_INIT_PATH,
        return_value=True,
    )
    @patch(
        _GIT_MOCK_PATH,
        return_value=_GIT_MOCK_RETURN,
    )
    def test_missing_only_no_boilerplate_question(
        self, _mock_git, _mock_init, _mock_commit
    ):
        """Missing boilerplate should not ask boilerplate question."""
        with tempfile.TemporaryDirectory() as tmp:
            plugin_dir = _scaffold_plugin(tmp)
            # Delete (not modify) a boilerplate file
            ml_path = plugin_dir / ".markdownlint.json"
            ml_path.unlink()

            context = {
                "operation": "update",
                "plugin_path": str(plugin_dir),
            }
            result = update_mod.get_questions(context)

            scan = result["inferred"]["scan_result"]
            self.assertTrue(scan["needs_update"])
            # No boilerplate question since only
            # missing files (not outdated)
            question_ids = [
                q["id"] for q in result["questions"]
            ]
            self.assertNotIn(
                "boilerplate_strategy", question_ids
            )

    @patch(
        _GIT_COMMIT_PATH,
        return_value=True,
    )
    @patch(
        _GIT_INIT_PATH,
        return_value=True,
    )
    @patch(
        _GIT_MOCK_PATH,
        return_value=_GIT_MOCK_RETURN,
    )
    def test_inferred_contains_scan_result(
        self, _mock_git, _mock_init, _mock_commit
    ):
        """Phase 1 inferred payload has expected structure."""
        with tempfile.TemporaryDirectory() as tmp:
            plugin_dir = _scaffold_plugin(tmp)
            context = {
                "operation": "update",
                "plugin_path": str(plugin_dir),
            }
            result = update_mod.get_questions(context)

            inferred = result["inferred"]
            self.assertIn("plugin_name", inferred)
            self.assertIn("language", inferred)
            self.assertIn(
                "generator_version", inferred
            )
            self.assertIn(
                "current_standard", inferred
            )
            self.assertIn("scan_result", inferred)

            scan = inferred["scan_result"]
            self.assertIn("summary", scan)
            self.assertIn("needs_update", scan)
            self.assertIn("missing_files", scan)
            self.assertIn("outdated_files", scan)
            self.assertIn("up_to_date_files", scan)
            self.assertIn("custom_skip_files", scan)


class TestUpdatePhase2(unittest.TestCase):
    """Tests for update_mod.execute (Phase 2)."""

    @patch(
        _GIT_COMMIT_PATH,
        return_value=True,
    )
    @patch(
        _GIT_INIT_PATH,
        return_value=True,
    )
    @patch(
        _GIT_MOCK_PATH,
        return_value=_GIT_MOCK_RETURN,
    )
    def test_up_to_date_returns_no_changes(
        self, _mock_git, _mock_init, _mock_commit
    ):
        """Fresh plugin should return up-to-date result."""
        with tempfile.TemporaryDirectory() as tmp:
            plugin_dir = _scaffold_plugin(tmp)
            context = {
                "operation": "update",
                "plugin_path": str(plugin_dir),
            }
            result = update_mod.execute(context)

            self.assertTrue(result["success"])
            self.assertIn(
                "up to date", result["message"]
            )
            self.assertEqual(result["files_created"], [])
            self.assertEqual(result["files_updated"], [])

    @patch(
        _GIT_COMMIT_PATH,
        return_value=True,
    )
    @patch(
        _GIT_INIT_PATH,
        return_value=True,
    )
    @patch(
        _GIT_MOCK_PATH,
        return_value=_GIT_MOCK_RETURN,
    )
    def test_restores_deleted_boilerplate(
        self, _mock_git, _mock_init, _mock_commit
    ):
        """Deleted boilerplate file should be recreated."""
        with tempfile.TemporaryDirectory() as tmp:
            plugin_dir = _scaffold_plugin(tmp)
            ml_path = plugin_dir / ".markdownlint.json"
            ml_path.unlink()
            self.assertFalse(ml_path.exists())

            context = {
                "operation": "update",
                "plugin_path": str(plugin_dir),
            }
            result = update_mod.execute(context)

            self.assertTrue(result["success"])
            self.assertTrue(ml_path.exists())
            # Verify the restored content is valid JSON
            data = json.loads(ml_path.read_text())
            self.assertIsInstance(data, dict)

    @patch(
        _GIT_COMMIT_PATH,
        return_value=True,
    )
    @patch(
        _GIT_INIT_PATH,
        return_value=True,
    )
    @patch(
        _GIT_MOCK_PATH,
        return_value=_GIT_MOCK_RETURN,
    )
    def test_preserves_custom_claudemd(
        self, _mock_git, _mock_init, _mock_commit
    ):
        """CLAUDE.md custom content should be preserved."""
        with tempfile.TemporaryDirectory() as tmp:
            plugin_dir = _scaffold_plugin(tmp)
            claude_md = plugin_dir / "CLAUDE.md"
            custom_content = "# My Custom Instructions\n"
            claude_md.write_text(custom_content)

            # Delete a file to force an update run
            ml_path = plugin_dir / ".markdownlint.json"
            ml_path.unlink()

            context = {
                "operation": "update",
                "plugin_path": str(plugin_dir),
            }
            update_mod.execute(context)

            self.assertEqual(
                claude_md.read_text(), custom_content
            )

    @patch(
        _GIT_COMMIT_PATH,
        return_value=True,
    )
    @patch(
        _GIT_INIT_PATH,
        return_value=True,
    )
    @patch(
        _GIT_MOCK_PATH,
        return_value=_GIT_MOCK_RETURN,
    )
    def test_updates_generator_version(
        self, _mock_git, _mock_init, _mock_commit
    ):
        """Generator version should be updated after patch."""
        with tempfile.TemporaryDirectory() as tmp:
            plugin_dir = _scaffold_plugin(tmp)
            # Manually set an old generator_version
            config_path = (
                plugin_dir
                / ".claude-plugin"
                / "aida-config.json"
            )
            config = json.loads(config_path.read_text())
            config["generator_version"] = "0.1.0"
            config_path.write_text(
                json.dumps(config, indent=2) + "\n"
            )

            # Delete a file so update has work to do
            ml_path = plugin_dir / ".markdownlint.json"
            ml_path.unlink()

            context = {
                "operation": "update",
                "plugin_path": str(plugin_dir),
            }
            result = update_mod.execute(context)

            self.assertTrue(result["success"])
            self.assertEqual(
                result["generator_version"],
                GENERATOR_VERSION,
            )

            # Verify on-disk config was updated
            updated = json.loads(
                config_path.read_text()
            )
            self.assertEqual(
                updated["generator_version"],
                GENERATOR_VERSION,
            )


class TestUpdateRoundTrip(unittest.TestCase):
    """Full round-trip tests (Phase 1 -> Phase 2)."""

    @patch(
        _GIT_COMMIT_PATH,
        return_value=True,
    )
    @patch(
        _GIT_INIT_PATH,
        return_value=True,
    )
    @patch(
        _GIT_MOCK_PATH,
        return_value=_GIT_MOCK_RETURN,
    )
    def test_full_round_trip(
        self, _mock_git, _mock_init, _mock_commit
    ):
        """Phase 1 scan -> Phase 2 patch -> Phase 1 clean."""
        with tempfile.TemporaryDirectory() as tmp:
            plugin_dir = _scaffold_plugin(tmp)

            # Delete two files to simulate drift
            ml_path = plugin_dir / ".markdownlint.json"
            fs_path = (
                plugin_dir / ".frontmatter-schema.json"
            )
            ml_path.unlink()
            fs_path.unlink()

            context = {
                "operation": "update",
                "plugin_path": str(plugin_dir),
            }

            # Phase 1: scan should detect 2 missing files
            phase1 = update_mod.get_questions(context)
            scan = phase1["inferred"]["scan_result"]
            self.assertTrue(scan["needs_update"])
            missing_paths = [
                f["path"] for f in scan["missing_files"]
            ]
            self.assertIn(
                ".markdownlint.json", missing_paths
            )
            self.assertIn(
                ".frontmatter-schema.json", missing_paths
            )

            # Phase 2: apply patches with default responses
            phase2 = update_mod.execute(context, {})
            self.assertTrue(phase2["success"])
            self.assertTrue(ml_path.exists())
            self.assertTrue(fs_path.exists())

            # Phase 1 again: should be clean
            phase1_after = update_mod.get_questions(
                context
            )
            self.assertFalse(
                phase1_after["inferred"]["scan_result"][
                    "needs_update"
                ]
            )
            self.assertEqual(
                phase1_after["questions"], []
            )


class TestUpdateIdempotent(unittest.TestCase):
    """Test that updates are idempotent."""

    @patch(
        _GIT_COMMIT_PATH,
        return_value=True,
    )
    @patch(
        _GIT_INIT_PATH,
        return_value=True,
    )
    @patch(
        _GIT_MOCK_PATH,
        return_value=_GIT_MOCK_RETURN,
    )
    def test_double_update_no_changes(
        self, _mock_git, _mock_init, _mock_commit
    ):
        """Second update on same plugin reports up-to-date."""
        with tempfile.TemporaryDirectory() as tmp:
            plugin_dir = _scaffold_plugin(tmp)
            ml_path = plugin_dir / ".markdownlint.json"
            ml_path.unlink()

            context = {
                "operation": "update",
                "plugin_path": str(plugin_dir),
            }

            # First update: should make changes
            first = update_mod.execute(context)
            self.assertTrue(first["success"])
            self.assertTrue(ml_path.exists())

            # Second update: should report up-to-date
            second = update_mod.execute(context)
            self.assertTrue(second["success"])
            self.assertIn(
                "up to date", second["message"]
            )
            self.assertEqual(
                second["files_created"], []
            )
            self.assertEqual(
                second["files_updated"], []
            )


class TestUpdatePreservesContent(unittest.TestCase):
    """Test that updates preserve user-owned content."""

    @patch(
        _GIT_COMMIT_PATH,
        return_value=True,
    )
    @patch(
        _GIT_INIT_PATH,
        return_value=True,
    )
    @patch(
        _GIT_MOCK_PATH,
        return_value=_GIT_MOCK_RETURN,
    )
    def test_preserves_readme(
        self, _mock_git, _mock_init, _mock_commit
    ):
        """README.md custom content survives an update."""
        with tempfile.TemporaryDirectory() as tmp:
            plugin_dir = _scaffold_plugin(tmp)
            readme = plugin_dir / "README.md"
            custom = "# My Custom README\n\nHello world.\n"
            readme.write_text(custom)

            # Delete a file to force an update
            ml_path = plugin_dir / ".markdownlint.json"
            ml_path.unlink()

            context = {
                "operation": "update",
                "plugin_path": str(plugin_dir),
            }
            update_mod.execute(context)

            self.assertEqual(readme.read_text(), custom)

    @patch(
        _GIT_COMMIT_PATH,
        return_value=True,
    )
    @patch(
        _GIT_INIT_PATH,
        return_value=True,
    )
    @patch(
        _GIT_MOCK_PATH,
        return_value=_GIT_MOCK_RETURN,
    )
    def test_preserves_license(
        self, _mock_git, _mock_init, _mock_commit
    ):
        """LICENSE file custom content survives an update."""
        with tempfile.TemporaryDirectory() as tmp:
            plugin_dir = _scaffold_plugin(tmp)
            license_file = plugin_dir / "LICENSE"
            original = license_file.read_text()

            # Delete a file to force an update
            ml_path = plugin_dir / ".markdownlint.json"
            ml_path.unlink()

            context = {
                "operation": "update",
                "plugin_path": str(plugin_dir),
            }
            update_mod.execute(context)

            self.assertEqual(
                license_file.read_text(), original
            )


if __name__ == "__main__":
    unittest.main()
