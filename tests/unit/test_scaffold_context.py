"""Unit tests for create-plugin context operations."""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add scripts directories to path
_project_root = Path(__file__).parent.parent.parent
_scaffold_scripts = _project_root / "skills" / "create-plugin" / "scripts"
sys.path.insert(0, str(_project_root / "scripts"))
sys.path.insert(0, str(_scaffold_scripts))

from scaffold_ops.context import (  # noqa: E402
    infer_git_config,
    validate_target_directory,
    check_gh_available,
    resolve_default_target,
)


class TestInferGitConfig(unittest.TestCase):
    """Test git config inference."""

    @patch("scaffold_ops.context.subprocess.run")
    def test_success(self, mock_run):
        """Should return name and email from git config."""
        def side_effect(cmd, **kwargs):
            result = MagicMock()
            result.returncode = 0
            if "user.name" in cmd:
                result.stdout = "Test User\n"
            elif "user.email" in cmd:
                result.stdout = "test@example.com\n"
            return result

        mock_run.side_effect = side_effect
        config = infer_git_config()
        self.assertEqual(config["author_name"], "Test User")
        self.assertEqual(config["author_email"], "test@example.com")

    @patch("scaffold_ops.context.subprocess.run")
    def test_failure(self, mock_run):
        """Should return empty strings if git config fails."""
        mock_run.side_effect = FileNotFoundError("git not found")
        config = infer_git_config()
        self.assertEqual(config["author_name"], "")
        self.assertEqual(config["author_email"], "")

    @patch("scaffold_ops.context.subprocess.run")
    def test_partial_failure(self, mock_run):
        """Should return partial results if one config fails."""
        def side_effect(cmd, **kwargs):
            result = MagicMock()
            if "user.name" in cmd:
                result.returncode = 0
                result.stdout = "Test User\n"
            else:
                result.returncode = 1
                result.stdout = ""
            return result

        mock_run.side_effect = side_effect
        config = infer_git_config()
        self.assertEqual(config["author_name"], "Test User")
        self.assertEqual(config["author_email"], "")


class TestValidateTargetDirectory(unittest.TestCase):
    """Test target directory validation."""

    def test_new_directory(self):
        """Should accept a non-existent directory under an existing parent."""
        with tempfile.TemporaryDirectory() as tmp:
            target = os.path.join(tmp, "new-plugin")
            is_valid, error = validate_target_directory(target)
            self.assertTrue(is_valid, f"Should be valid: {error}")

    def test_existing_empty_directory(self):
        """Should accept an existing empty directory."""
        with tempfile.TemporaryDirectory() as tmp:
            target = os.path.join(tmp, "empty-dir")
            os.makedirs(target)
            is_valid, error = validate_target_directory(target)
            self.assertTrue(is_valid, f"Should be valid: {error}")

    def test_existing_non_empty_directory(self):
        """Should reject a non-empty directory."""
        with tempfile.TemporaryDirectory() as tmp:
            target = os.path.join(tmp, "non-empty")
            os.makedirs(target)
            Path(os.path.join(target, "file.txt")).write_text("content")
            is_valid, error = validate_target_directory(target)
            self.assertFalse(is_valid)
            self.assertIn("not empty", error)

    def test_existing_file(self):
        """Should reject if target is a file."""
        with tempfile.TemporaryDirectory() as tmp:
            target = os.path.join(tmp, "file.txt")
            Path(target).write_text("content")
            is_valid, error = validate_target_directory(target)
            self.assertFalse(is_valid)
            self.assertIn("existing file", error)

    def test_empty_path(self):
        """Should reject empty path."""
        is_valid, error = validate_target_directory("")
        self.assertFalse(is_valid)
        self.assertIn("empty", error)

    def test_parent_does_not_exist(self):
        """Should reject if parent directory doesn't exist."""
        is_valid, error = validate_target_directory("/nonexistent/path/plugin")
        self.assertFalse(is_valid)
        self.assertIn("Parent directory does not exist", error)

    def test_rejects_symlink(self):
        """Should reject a symlink target to prevent writing through unexpected paths."""
        with tempfile.TemporaryDirectory() as tmp:
            real_dir = os.path.join(tmp, "real-dir")
            os.makedirs(real_dir)
            link_path = os.path.join(tmp, "link-dir")
            os.symlink(real_dir, link_path)
            is_valid, error = validate_target_directory(link_path)
            self.assertFalse(is_valid)
            self.assertIn("symbolic link", error)


class TestCheckGhAvailable(unittest.TestCase):
    """Test GitHub CLI availability check."""

    @patch("scaffold_ops.context.subprocess.run")
    def test_available(self, mock_run):
        """Should return True when gh is available."""
        mock_run.return_value = MagicMock(returncode=0)
        self.assertTrue(check_gh_available())

    @patch("scaffold_ops.context.subprocess.run")
    def test_not_available(self, mock_run):
        """Should return False when gh is not installed."""
        mock_run.side_effect = FileNotFoundError("gh not found")
        self.assertFalse(check_gh_available())

    @patch("scaffold_ops.context.subprocess.run")
    def test_timeout(self, mock_run):
        """Should return False on timeout."""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired("gh", 5)
        self.assertFalse(check_gh_available())


class TestResolveDefaultTarget(unittest.TestCase):
    """Test default target directory resolution."""

    def test_resolves_to_cwd(self):
        """Should resolve to cwd/plugin_name."""
        result = resolve_default_target("my-plugin")
        expected = str(Path.cwd() / "my-plugin")
        self.assertEqual(result, expected)


if __name__ == "__main__":
    unittest.main()
