"""Unit tests for plugin-manager update patcher."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

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

from operations.update_ops.patcher import (  # noqa: E402
    _atomic_write,
    _create_backup,
    _extract_makefile_target_block,
    _merge_gitignore,
    _merge_makefile,
    _update_generator_version,
    apply_patches,
)
from operations.update_ops.parsers import (  # noqa: E402
    extract_makefile_targets,
    parse_gitignore_entries,
)
from operations.update_ops.models import (  # noqa: E402
    DiffReport,
    FileDiff,
    FileCategory,
    FileStatus,
    MergeStrategy,
    PatchResult,
)
from operations.constants import (  # noqa: E402
    GENERATOR_VERSION,
)


def _make_diff_report(
    plugin_path: str,
    files: list[FileDiff] | None = None,
) -> DiffReport:
    """Create a DiffReport for testing."""
    return DiffReport(
        plugin_path=plugin_path,
        plugin_name="test-plugin",
        language="python",
        generator_version="0.7.0",
        current_version=GENERATOR_VERSION,
        files=files or [],
    )


def _make_file_diff(
    path: str,
    status: FileStatus = FileStatus.MISSING,
    strategy: MergeStrategy = MergeStrategy.ADD,
    category: FileCategory = FileCategory.BOILERPLATE,
    expected_content: str = "expected content\n",
    actual_content: str | None = None,
    diff_summary: str = "",
) -> FileDiff:
    """Create a FileDiff for testing."""
    return FileDiff(
        path=path,
        category=category,
        status=status,
        strategy=strategy,
        expected_content=expected_content,
        actual_content=actual_content,
        diff_summary=diff_summary,
    )


class TestAtomicWrite(unittest.TestCase):
    """Test _atomic_write for safe file writes."""

    def test_writes_file_content(self):
        """Write content and read back to verify match."""
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "test.txt"
            _atomic_write(target, "hello world\n")
            self.assertEqual(
                target.read_text(), "hello world\n"
            )

    def test_creates_parent_directories(self):
        """Write to nested path and verify dirs created."""
        with tempfile.TemporaryDirectory() as tmp:
            target = (
                Path(tmp) / "a" / "b" / "c" / "deep.txt"
            )
            _atomic_write(target, "deep content\n")
            self.assertTrue(target.exists())
            self.assertEqual(
                target.read_text(), "deep content\n"
            )

    def test_overwrites_existing_file(self):
        """Write twice and verify second content wins."""
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "overwrite.txt"
            _atomic_write(target, "first\n")
            _atomic_write(target, "second\n")
            self.assertEqual(target.read_text(), "second\n")

    def test_cleans_up_tmp_on_success(self):
        """After write, verify no .tmp file remains."""
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "clean.txt"
            _atomic_write(target, "content\n")
            tmp_file = Path(str(target) + ".tmp")
            self.assertFalse(tmp_file.exists())


class TestCreateBackup(unittest.TestCase):
    """Test _create_backup for pre-patch safety copies."""

    def test_creates_backup_directory(self):
        """Backup dir should exist with timestamp format."""
        with tempfile.TemporaryDirectory() as tmp:
            plugin = Path(tmp) / "plugin"
            plugin.mkdir()
            src = plugin / "file.txt"
            src.write_text("old content\n")

            actionable = [
                _make_file_diff(
                    "file.txt",
                    status=FileStatus.OUTDATED,
                    strategy=MergeStrategy.OVERWRITE,
                )
            ]
            backup = _create_backup(plugin, actionable)

            self.assertTrue(backup.exists())
            self.assertTrue(backup.is_dir())
            # Backup lives under .aida-backup/
            self.assertEqual(
                backup.parent.name, ".aida-backup"
            )
            # Timestamp directory name: YYYYMMDD_HHMMSS
            self.assertRegex(
                backup.name, r"^\d{8}_\d{6}$"
            )

    def test_copies_existing_files(self):
        """Files on disk that will be modified appear in backup."""
        with tempfile.TemporaryDirectory() as tmp:
            plugin = Path(tmp) / "plugin"
            plugin.mkdir()
            src = plugin / "readme.txt"
            src.write_text("original readme\n")

            actionable = [
                _make_file_diff(
                    "readme.txt",
                    status=FileStatus.OUTDATED,
                    strategy=MergeStrategy.OVERWRITE,
                )
            ]
            backup = _create_backup(plugin, actionable)

            backed_up = backup / "readme.txt"
            self.assertTrue(backed_up.exists())
            self.assertEqual(
                backed_up.read_text(), "original readme\n"
            )

    def test_skips_missing_files(self):
        """MISSING files have nothing on disk to back up."""
        with tempfile.TemporaryDirectory() as tmp:
            plugin = Path(tmp) / "plugin"
            plugin.mkdir()

            actionable = [
                _make_file_diff(
                    "new_file.txt",
                    status=FileStatus.MISSING,
                    strategy=MergeStrategy.ADD,
                )
            ]
            backup = _create_backup(plugin, actionable)

            # Backup dir exists but the missing file is not
            # inside it
            self.assertTrue(backup.exists())
            self.assertFalse(
                (backup / "new_file.txt").exists()
            )

    def test_preserves_directory_structure(self):
        """Subdirectory paths are preserved in backup."""
        with tempfile.TemporaryDirectory() as tmp:
            plugin = Path(tmp) / "plugin"
            (plugin / ".claude-plugin").mkdir(parents=True)
            nested = plugin / ".claude-plugin" / "plugin.json"
            nested.write_text('{"name":"test"}\n')

            actionable = [
                _make_file_diff(
                    ".claude-plugin/plugin.json",
                    status=FileStatus.OUTDATED,
                    strategy=MergeStrategy.OVERWRITE,
                )
            ]
            backup = _create_backup(plugin, actionable)

            backed_up = (
                backup / ".claude-plugin" / "plugin.json"
            )
            self.assertTrue(backed_up.exists())
            self.assertEqual(
                backed_up.read_text(), '{"name":"test"}\n'
            )


class TestMergeGitignore(unittest.TestCase):
    """Test _merge_gitignore append-only merge logic."""

    def _run_merge(
        self,
        current: str,
        expected: str,
        status: FileStatus = FileStatus.OUTDATED,
    ) -> tuple[PatchResult, str]:
        """Run a gitignore merge and return result + file.

        Creates a temporary plugin directory, writes the
        current content to .gitignore, and invokes the merge.

        Returns:
            Tuple of (PatchResult, final file content).
        """
        with tempfile.TemporaryDirectory() as tmp:
            plugin = Path(tmp) / "plugin"
            plugin.mkdir()
            backup = plugin / ".aida-backup" / "test"
            backup.mkdir(parents=True)

            target = plugin / ".gitignore"
            if status != FileStatus.MISSING:
                target.write_text(current)
                # Copy to backup so backup_path resolves
                bk = backup / ".gitignore"
                bk.write_text(current)

            fd = _make_file_diff(
                ".gitignore",
                status=status,
                strategy=MergeStrategy.MERGE,
                category=FileCategory.COMPOSITE,
                expected_content=expected,
                actual_content=(
                    current
                    if status != FileStatus.MISSING
                    else None
                ),
            )

            result = _merge_gitignore(plugin, fd, backup)
            content = target.read_text()
        return result, content

    def test_appends_missing_entries(self):
        """Missing entries appended under update header."""
        current = "__pycache__/\n*.pyc\n"
        expected = (
            "__pycache__/\n*.pyc\n.ruff_cache/\ndist/\n"
        )
        result, content = self._run_merge(current, expected)

        self.assertEqual(result.action, "updated")
        self.assertIn(".ruff_cache/", content)
        self.assertIn("dist/", content)
        self.assertIn(
            "# Added by aida plugin update", content
        )

    def test_preserves_existing_entries(self):
        """All original entries still present after merge."""
        current = "__pycache__/\n*.pyc\nmy_custom_dir/\n"
        expected = "__pycache__/\n*.pyc\n.ruff_cache/\n"
        _, content = self._run_merge(current, expected)

        self.assertIn("__pycache__/", content)
        self.assertIn("*.pyc", content)
        self.assertIn("my_custom_dir/", content)

    def test_no_duplicates(self):
        """Already-present entries are not added again."""
        current = "__pycache__/\n*.pyc\n.ruff_cache/\n"
        expected = "__pycache__/\n*.pyc\n.ruff_cache/\n"
        result, content = self._run_merge(current, expected)

        self.assertEqual(result.action, "skipped")
        # Content should not contain the update header
        self.assertNotIn(
            "# Added by aida plugin update", content
        )

    def test_handles_empty_current(self):
        """Empty .gitignore gets all expected entries."""
        current = ""
        expected = "__pycache__/\n*.pyc\n"
        result, content = self._run_merge(current, expected)

        self.assertEqual(result.action, "updated")
        self.assertIn("__pycache__/", content)
        self.assertIn("*.pyc", content)

    def test_handles_comments_and_blanks(self):
        """Comments and blank lines are preserved."""
        current = (
            "# Python artifacts\n"
            "__pycache__/\n"
            "\n"
            "# Build output\n"
            "dist/\n"
        )
        expected = "__pycache__/\ndist/\n.ruff_cache/\n"
        _, content = self._run_merge(current, expected)

        self.assertIn("# Python artifacts", content)
        self.assertIn("# Build output", content)


class TestMergeMakefile(unittest.TestCase):
    """Test _merge_makefile conservative target merge."""

    def _run_merge(
        self,
        current: str,
        expected: str,
        status: FileStatus = FileStatus.OUTDATED,
    ) -> tuple[PatchResult, str]:
        """Run a Makefile merge and return result + file.

        Returns:
            Tuple of (PatchResult, final file content).
        """
        with tempfile.TemporaryDirectory() as tmp:
            plugin = Path(tmp) / "plugin"
            plugin.mkdir()
            backup = plugin / ".aida-backup" / "test"
            backup.mkdir(parents=True)

            target = plugin / "Makefile"
            if status != FileStatus.MISSING:
                target.write_text(current)
                bk = backup / "Makefile"
                bk.write_text(current)

            fd = _make_file_diff(
                "Makefile",
                status=status,
                strategy=MergeStrategy.MERGE,
                category=FileCategory.COMPOSITE,
                expected_content=expected,
                actual_content=(
                    current
                    if status != FileStatus.MISSING
                    else None
                ),
            )

            result = _merge_makefile(plugin, fd, backup)
            content = target.read_text()
        return result, content

    def test_appends_missing_targets(self):
        """Missing targets are appended to the Makefile."""
        current = "lint:\n\truff check .\n"
        expected = (
            "lint:\n\truff check .\n\n"
            "format:\n\truff format .\n"
        )
        result, content = self._run_merge(current, expected)

        self.assertEqual(result.action, "updated")
        self.assertIn("format:", content)
        self.assertIn("\truff format .", content)

    def test_preserves_existing_targets(self):
        """Existing custom targets are untouched."""
        current = (
            "my-custom:\n"
            "\techo custom\n\n"
            "lint:\n"
            "\truff check .\n"
        )
        expected = (
            "lint:\n"
            "\truff check .\n\n"
            "format:\n"
            "\truff format .\n"
        )
        _, content = self._run_merge(current, expected)

        self.assertIn("my-custom:", content)
        self.assertIn("\techo custom", content)

    def test_adds_phony_declaration(self):
        """Missing targets get a .PHONY line."""
        current = "lint:\n\truff check .\n"
        expected = (
            "lint:\n\truff check .\n\n"
            "test:\n\tpytest tests/\n"
        )
        _, content = self._run_merge(current, expected)

        self.assertIn(".PHONY: test", content)

    def test_preserves_tab_indentation(self):
        """Recipe lines keep tab indentation."""
        current = "lint:\n\truff check .\n"
        expected = (
            "lint:\n\truff check .\n\n"
            "clean:\n\trm -rf build/\n"
        )
        _, content = self._run_merge(current, expected)

        # Find the clean target and verify tab
        lines = content.splitlines()
        for i, line in enumerate(lines):
            if line.startswith("clean:"):
                self.assertTrue(
                    lines[i + 1].startswith("\t"),
                    "Recipe line must start with a tab",
                )
                break
        else:
            self.fail("clean: target not found in output")


class TestApplyPatches(unittest.TestCase):
    """Test apply_patches end-to-end patching flow."""

    def _setup_plugin(
        self, tmp: str
    ) -> Path:
        """Create a minimal plugin directory.

        Returns:
            Path to the plugin root directory.
        """
        plugin = Path(tmp) / "plugin"
        config_dir = plugin / ".claude-plugin"
        config_dir.mkdir(parents=True)
        config = config_dir / "aida-config.json"
        config.write_text(
            json.dumps(
                {"generator_version": "0.7.0"}, indent=2
            )
            + "\n"
        )
        return plugin

    def test_add_missing_file(self):
        """MISSING + ADD creates the file with expected content."""
        with tempfile.TemporaryDirectory() as tmp:
            plugin = self._setup_plugin(tmp)

            fd = _make_file_diff(
                "new_file.txt",
                status=FileStatus.MISSING,
                strategy=MergeStrategy.ADD,
                expected_content="brand new content\n",
            )
            report = _make_diff_report(
                str(plugin), files=[fd]
            )
            results = apply_patches(plugin, report)

            created = plugin / "new_file.txt"
            self.assertTrue(created.exists())
            self.assertEqual(
                created.read_text(), "brand new content\n"
            )

            actions = [r.action for r in results]
            self.assertIn("created", actions)

    def test_overwrite_outdated_file(self):
        """OUTDATED + OVERWRITE replaces file content."""
        with tempfile.TemporaryDirectory() as tmp:
            plugin = self._setup_plugin(tmp)
            target = plugin / "stale.txt"
            target.write_text("old stuff\n")

            fd = _make_file_diff(
                "stale.txt",
                status=FileStatus.OUTDATED,
                strategy=MergeStrategy.OVERWRITE,
                expected_content="new stuff\n",
                actual_content="old stuff\n",
            )
            report = _make_diff_report(
                str(plugin), files=[fd]
            )
            results = apply_patches(plugin, report)

            self.assertEqual(
                target.read_text(), "new stuff\n"
            )
            actions = [r.action for r in results]
            self.assertIn("updated", actions)

    def test_skip_custom_file(self):
        """CUSTOM_SKIP files are not actionable."""
        with tempfile.TemporaryDirectory() as tmp:
            plugin = self._setup_plugin(tmp)
            target = plugin / "custom.txt"
            target.write_text("my stuff\n")

            fd = _make_file_diff(
                "custom.txt",
                status=FileStatus.CUSTOM_SKIP,
                strategy=MergeStrategy.SKIP,
                actual_content="my stuff\n",
            )
            report = _make_diff_report(
                str(plugin), files=[fd]
            )
            results = apply_patches(plugin, report)

            # File unchanged
            self.assertEqual(
                target.read_text(), "my stuff\n"
            )
            # Only result is the version update
            paths = [r.path for r in results]
            self.assertNotIn("custom.txt", paths)

    def test_skip_up_to_date_file(self):
        """UP_TO_DATE files are filtered out entirely."""
        with tempfile.TemporaryDirectory() as tmp:
            plugin = self._setup_plugin(tmp)
            target = plugin / "current.txt"
            target.write_text("perfect\n")

            fd = _make_file_diff(
                "current.txt",
                status=FileStatus.UP_TO_DATE,
                strategy=MergeStrategy.SKIP,
                expected_content="perfect\n",
                actual_content="perfect\n",
            )
            report = _make_diff_report(
                str(plugin), files=[fd]
            )
            results = apply_patches(plugin, report)

            paths = [r.path for r in results]
            self.assertNotIn("current.txt", paths)

    def test_manual_review_not_modified(self):
        """MANUAL_REVIEW files are skipped without changes."""
        with tempfile.TemporaryDirectory() as tmp:
            plugin = self._setup_plugin(tmp)
            target = plugin / "complex.toml"
            target.write_text("original\n")

            fd = _make_file_diff(
                "complex.toml",
                status=FileStatus.OUTDATED,
                strategy=MergeStrategy.MANUAL_REVIEW,
                expected_content="updated\n",
                actual_content="original\n",
            )
            report = _make_diff_report(
                str(plugin), files=[fd]
            )
            results = apply_patches(plugin, report)

            # File is not modified
            self.assertEqual(
                target.read_text(), "original\n"
            )
            # Result shows skipped
            manual = [
                r
                for r in results
                if r.path == "complex.toml"
            ]
            self.assertEqual(len(manual), 1)
            self.assertEqual(manual[0].action, "skipped")

    def test_add_skips_existing_file(self):
        """ADD strategy does not overwrite existing files."""
        with tempfile.TemporaryDirectory() as tmp:
            plugin = self._setup_plugin(tmp)
            target = plugin / "exists.txt"
            target.write_text("keep me\n")

            fd = _make_file_diff(
                "exists.txt",
                status=FileStatus.MISSING,
                strategy=MergeStrategy.ADD,
                expected_content="replacement\n",
            )
            report = _make_diff_report(
                str(plugin), files=[fd]
            )
            results = apply_patches(plugin, report)

            # File content unchanged
            self.assertEqual(
                target.read_text(), "keep me\n"
            )
            add_result = [
                r
                for r in results
                if r.path == "exists.txt"
            ]
            self.assertEqual(len(add_result), 1)
            self.assertEqual(
                add_result[0].action, "skipped"
            )

    def test_user_override_to_skip(self):
        """Override dict can force SKIP on a file."""
        with tempfile.TemporaryDirectory() as tmp:
            plugin = self._setup_plugin(tmp)
            target = plugin / "override.txt"
            target.write_text("original\n")

            fd = _make_file_diff(
                "override.txt",
                status=FileStatus.OUTDATED,
                strategy=MergeStrategy.OVERWRITE,
                expected_content="new\n",
                actual_content="original\n",
            )
            report = _make_diff_report(
                str(plugin), files=[fd]
            )
            overrides = {
                "override.txt": MergeStrategy.SKIP
            }
            results = apply_patches(
                plugin, report, overrides=overrides
            )

            # File not modified
            self.assertEqual(
                target.read_text(), "original\n"
            )
            skip_result = [
                r
                for r in results
                if r.path == "override.txt"
            ]
            self.assertEqual(len(skip_result), 1)
            self.assertEqual(
                skip_result[0].action, "skipped"
            )

    def test_backup_created(self):
        """Patching OUTDATED files creates a backup dir."""
        with tempfile.TemporaryDirectory() as tmp:
            plugin = self._setup_plugin(tmp)
            target = plugin / "old.txt"
            target.write_text("before\n")

            fd = _make_file_diff(
                "old.txt",
                status=FileStatus.OUTDATED,
                strategy=MergeStrategy.OVERWRITE,
                expected_content="after\n",
                actual_content="before\n",
            )
            report = _make_diff_report(
                str(plugin), files=[fd]
            )
            apply_patches(plugin, report)

            backup_dir = plugin / ".aida-backup"
            self.assertTrue(backup_dir.exists())
            # At least one timestamped subdirectory
            subdirs = list(backup_dir.iterdir())
            self.assertGreater(len(subdirs), 0)

    def test_results_include_all_files(self):
        """Every actionable file gets a PatchResult."""
        with tempfile.TemporaryDirectory() as tmp:
            plugin = self._setup_plugin(tmp)

            # Create existing file for the OUTDATED entry
            (plugin / "b.txt").write_text("old\n")

            files = [
                _make_file_diff(
                    "a.txt",
                    status=FileStatus.MISSING,
                    strategy=MergeStrategy.ADD,
                    expected_content="a\n",
                ),
                _make_file_diff(
                    "b.txt",
                    status=FileStatus.OUTDATED,
                    strategy=MergeStrategy.OVERWRITE,
                    expected_content="b\n",
                    actual_content="old\n",
                ),
                _make_file_diff(
                    "c.txt",
                    status=FileStatus.MISSING,
                    strategy=MergeStrategy.ADD,
                    expected_content="c\n",
                ),
            ]
            report = _make_diff_report(
                str(plugin), files=files
            )
            results = apply_patches(plugin, report)

            paths = [r.path for r in results]
            self.assertIn("a.txt", paths)
            self.assertIn("b.txt", paths)
            self.assertIn("c.txt", paths)
            # Plus the version update
            self.assertIn(
                ".claude-plugin/aida-config.json", paths
            )


class TestUpdateGeneratorVersion(unittest.TestCase):
    """Test _update_generator_version config writing."""

    def test_updates_existing_aida_config(self):
        """Existing config gets its version updated."""
        with tempfile.TemporaryDirectory() as tmp:
            plugin = Path(tmp) / "plugin"
            config_dir = plugin / ".claude-plugin"
            config_dir.mkdir(parents=True)
            config = config_dir / "aida-config.json"
            config.write_text(
                json.dumps(
                    {"generator_version": "0.5.0"},
                    indent=2,
                )
                + "\n"
            )

            result = _update_generator_version(plugin)

            data = json.loads(config.read_text())
            self.assertEqual(
                data["generator_version"],
                GENERATOR_VERSION,
            )
            self.assertEqual(result.action, "updated")

    def test_creates_aida_config_if_missing(self):
        """Missing config file is created with version."""
        with tempfile.TemporaryDirectory() as tmp:
            plugin = Path(tmp) / "plugin"
            plugin.mkdir()

            result = _update_generator_version(plugin)

            config = (
                plugin
                / ".claude-plugin"
                / "aida-config.json"
            )
            self.assertTrue(config.exists())
            data = json.loads(config.read_text())
            self.assertEqual(
                data["generator_version"],
                GENERATOR_VERSION,
            )
            self.assertEqual(result.action, "updated")

    def test_preserves_other_fields(self):
        """Non-version fields survive the update."""
        with tempfile.TemporaryDirectory() as tmp:
            plugin = Path(tmp) / "plugin"
            config_dir = plugin / ".claude-plugin"
            config_dir.mkdir(parents=True)
            config = config_dir / "aida-config.json"
            original = {
                "generator_version": "0.5.0",
                "config": {"theme": "dark"},
                "permissions": ["read", "write"],
            }
            config.write_text(
                json.dumps(original, indent=2) + "\n"
            )

            _update_generator_version(plugin)

            data = json.loads(config.read_text())
            self.assertEqual(
                data["generator_version"],
                GENERATOR_VERSION,
            )
            self.assertEqual(
                data["config"], {"theme": "dark"}
            )
            self.assertEqual(
                data["permissions"], ["read", "write"]
            )


class TestParsers(unittest.TestCase):
    """Test shared parser functions."""

    def test_parse_gitignore_basic(self):
        """Should extract active entries from gitignore."""
        content = (
            "# comment\n"
            "__pycache__/\n"
            "\n"
            "*.pyc\n"
            "  dist/  \n"
        )
        entries = parse_gitignore_entries(content)
        self.assertEqual(
            entries, {"__pycache__/", "*.pyc", "dist/"}
        )

    def test_parse_gitignore_empty(self):
        """Should return empty set for empty content."""
        self.assertEqual(
            parse_gitignore_entries(""), set()
        )

    def test_parse_gitignore_only_comments(self):
        """Should return empty set for comment-only content."""
        content = "# comment\n# another\n"
        self.assertEqual(
            parse_gitignore_entries(content), set()
        )

    def test_extract_makefile_targets_basic(self):
        """Should extract target names from Makefile."""
        content = (
            ".PHONY: lint test\n\n"
            "lint:\n\truff check .\n\n"
            "test:\n\tpytest tests/\n"
        )
        targets = extract_makefile_targets(content)
        self.assertIn("lint", targets)
        self.assertIn("test", targets)

    def test_extract_makefile_targets_empty(self):
        """Should return empty set for empty content."""
        self.assertEqual(
            extract_makefile_targets(""), set()
        )

    def test_extract_makefile_targets_no_targets(self):
        """Should return empty for content without targets."""
        content = "# Just a comment\n\t@echo hi\n"
        self.assertEqual(
            extract_makefile_targets(content), set()
        )


class TestExtractMakefileTargetBlock(unittest.TestCase):
    """Test _extract_makefile_target_block edge cases."""

    def test_extracts_simple_target(self):
        """Should extract a target with recipe lines."""
        content = (
            "lint:\n"
            "\truff check .\n"
            "\n"
            "test:\n"
            "\tpytest tests/\n"
        )
        block = _extract_makefile_target_block(
            content, "lint"
        )
        self.assertIn("lint:", block)
        self.assertIn("\truff check .", block)

    def test_extracts_last_target(self):
        """Should extract the last target in the file."""
        content = (
            "lint:\n"
            "\truff check .\n"
            "\n"
            "test:\n"
            "\tpytest tests/\n"
        )
        block = _extract_makefile_target_block(
            content, "test"
        )
        self.assertIn("test:", block)
        self.assertIn("\tpytest tests/", block)

    def test_returns_empty_for_missing_target(self):
        """Should return empty string for nonexistent target."""
        content = "lint:\n\truff check .\n"
        block = _extract_makefile_target_block(
            content, "missing"
        )
        self.assertEqual(block, "")

    def test_handles_multi_line_recipe(self):
        """Should extract target with multiple recipe lines."""
        content = (
            "clean:\n"
            "\trm -rf build/\n"
            "\trm -rf dist/\n"
            "\trm -rf *.egg-info\n"
        )
        block = _extract_makefile_target_block(
            content, "clean"
        )
        self.assertIn("rm -rf build/", block)
        self.assertIn("rm -rf dist/", block)
        self.assertIn("rm -rf *.egg-info", block)

    def test_stops_at_next_target(self):
        """Should not include content from next target."""
        content = (
            "lint:\n"
            "\truff check .\n"
            "test:\n"
            "\tpytest tests/\n"
        )
        block = _extract_makefile_target_block(
            content, "lint"
        )
        self.assertIn("lint:", block)
        self.assertNotIn("test:", block)
        self.assertNotIn("pytest", block)

    def test_strips_trailing_empty_lines(self):
        """Should not include trailing blank lines."""
        content = (
            "lint:\n"
            "\truff check .\n"
            "\n"
            "\n"
            "test:\n"
            "\tpytest\n"
        )
        block = _extract_makefile_target_block(
            content, "lint"
        )
        self.assertFalse(block.endswith("\n\n"))

    def test_handles_empty_content(self):
        """Should return empty string for empty content."""
        self.assertEqual(
            _extract_makefile_target_block("", "lint"), ""
        )


class TestScannerErrorFallback(unittest.TestCase):
    """Test scanner error fallback path."""

    def test_comparison_error_marks_outdated(self):
        """File comparison error should mark as OUTDATED."""
        with tempfile.TemporaryDirectory() as tmp:
            plugin_dir = Path(tmp) / "plugin"
            plugin_dir.mkdir()

            # Create a minimal plugin
            meta_dir = plugin_dir / ".claude-plugin"
            meta_dir.mkdir()
            (meta_dir / "plugin.json").write_text(
                json.dumps({
                    "name": "test",
                    "version": "0.1.0",
                    "description": "Test plugin for testing",
                })
            )
            (meta_dir / "aida-config.json").write_text(
                json.dumps({"generator_version": "0.9.0"})
            )
            (plugin_dir / "pyproject.toml").write_text("")

            # Import scan_plugin for this test
            from operations.update_ops.scanner import (
                scan_plugin,
            )

            # Use a bogus templates dir to trigger errors
            bogus_templates = Path(tmp) / "no-templates"
            bogus_templates.mkdir()

            # scan_plugin should handle errors gracefully
            # and mark files as OUTDATED rather than crashing
            from operations.update_ops.models import (
                FileStatus as FS,
            )

            report = scan_plugin(
                plugin_dir, bogus_templates
            )
            # Templated files should be marked as OUTDATED
            # due to template rendering errors
            errored = [
                f
                for f in report.files
                if f.status == FS.OUTDATED
                and "Error" in f.diff_summary
            ]
            self.assertGreater(
                len(errored),
                0,
                "Expected at least one file marked OUTDATED "
                "due to comparison error",
            )


if __name__ == "__main__":
    unittest.main()
