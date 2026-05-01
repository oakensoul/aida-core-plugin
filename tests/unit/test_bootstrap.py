# SPDX-FileCopyrightText: 2026 The AIDA Core Authors
# SPDX-License-Identifier: MPL-2.0

"""Unit tests for scripts/shared/bootstrap.py.

Tests the AIDA managed virtual environment bootstrap including
venv creation, dependency installation, stamp file tracking,
and sys.path injection.
"""

import hashlib
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add shared scripts to path
_project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_project_root / "scripts"))

from shared.bootstrap import (  # noqa: E402
    _hash_file,
    _find_requirements_txt,
    _deps_up_to_date,
    ensure_aida_environment,
    is_aida_environment_ready,
)


class TestHashFile(unittest.TestCase):
    """Tests for _hash_file."""

    def test_returns_sha256_hex(self, tmp_path=None):
        """Hash matches expected SHA-256 for known content."""
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("jinja2>=3.1.0\n")
            f.flush()
            path = Path(f.name)

        try:
            result = _hash_file(path)
            expected = hashlib.sha256(b"jinja2>=3.1.0\n").hexdigest()
            self.assertEqual(result, expected)
        finally:
            path.unlink()

    def test_different_content_different_hash(self):
        """Different file contents produce different hashes."""
        import tempfile

        paths = []
        for content in ["aaa\n", "bbb\n"]:
            f = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False)
            f.write(content)
            f.flush()
            f.close()
            paths.append(Path(f.name))

        try:
            self.assertNotEqual(_hash_file(paths[0]), _hash_file(paths[1]))
        finally:
            for p in paths:
                p.unlink()


class TestFindRequirementsTxt(unittest.TestCase):
    """Tests for _find_requirements_txt."""

    def test_finds_requirements_in_project(self):
        """Should find requirements.txt in the plugin tree."""
        req = _find_requirements_txt()
        self.assertTrue(req.exists())
        self.assertEqual(req.name, "requirements.txt")
        # Should be in a directory that has .claude-plugin/
        self.assertTrue((req.parent / ".claude-plugin").is_dir())


class TestDepsUpToDate(unittest.TestCase):
    """Tests for _deps_up_to_date."""

    def test_false_when_no_stamp(self):
        """Returns False when stamp file doesn't exist."""
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("test\n")
            req_path = Path(f.name)

        try:
            with patch("shared.bootstrap.STAMP_FILE") as mock_stamp:
                mock_stamp.exists.return_value = False
                self.assertFalse(_deps_up_to_date(req_path))
        finally:
            req_path.unlink()

    def test_true_when_hash_matches(self):
        """Returns True when stamp hash matches requirements hash."""
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("jinja2>=3.1.0\n")
            req_path = Path(f.name)

        expected_hash = _hash_file(req_path)

        try:
            with patch("shared.bootstrap.STAMP_FILE") as mock_stamp:
                mock_stamp.exists.return_value = True
                mock_stamp.read_text.return_value = expected_hash + "\n"
                self.assertTrue(_deps_up_to_date(req_path))
        finally:
            req_path.unlink()

    def test_false_when_hash_differs(self):
        """Returns False when stamp hash doesn't match."""
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("jinja2>=3.1.0\n")
            req_path = Path(f.name)

        try:
            with patch("shared.bootstrap.STAMP_FILE") as mock_stamp:
                mock_stamp.exists.return_value = True
                mock_stamp.read_text.return_value = "stale_hash\n"
                self.assertFalse(_deps_up_to_date(req_path))
        finally:
            req_path.unlink()


class TestEnsureAidaEnvironment(unittest.TestCase):
    """Tests for ensure_aida_environment."""

    @patch("shared.bootstrap._add_site_packages_to_path")
    @patch("shared.bootstrap._deps_up_to_date", return_value=True)
    @patch("shared.bootstrap._venv_python")
    @patch("shared.bootstrap._find_requirements_txt")
    def test_fast_path_when_ready(self, mock_req, mock_python, mock_up_to_date, mock_add):
        """Fast-paths when venv exists and deps are current."""
        mock_req.return_value = Path("/fake/requirements.txt")
        mock_python.return_value = MagicMock(exists=MagicMock(return_value=True))

        ensure_aida_environment()

        mock_add.assert_called_once()

    @patch("shared.bootstrap._add_site_packages_to_path")
    @patch("shared.bootstrap._install_deps")
    @patch("shared.bootstrap._create_venv")
    @patch("shared.bootstrap._deps_up_to_date", return_value=False)
    @patch("shared.bootstrap._venv_python")
    @patch("shared.bootstrap._find_requirements_txt")
    def test_creates_venv_when_missing(
        self, mock_req, mock_python, mock_up_to_date, mock_create, mock_install, mock_add
    ):
        """Creates venv and installs deps when venv is missing."""
        mock_req.return_value = Path("/fake/requirements.txt")
        mock_python.return_value = MagicMock(exists=MagicMock(return_value=False))

        ensure_aida_environment()

        mock_create.assert_called_once()
        mock_install.assert_called_once()
        mock_add.assert_called_once()

    @patch("shared.bootstrap._add_site_packages_to_path")
    @patch("shared.bootstrap._install_deps")
    @patch("shared.bootstrap._create_venv")
    @patch("shared.bootstrap._deps_up_to_date", return_value=False)
    @patch("shared.bootstrap._venv_python")
    @patch("shared.bootstrap._find_requirements_txt")
    def test_updates_deps_when_stale(
        self, mock_req, mock_python, mock_up_to_date, mock_create, mock_install, mock_add
    ):
        """Installs deps without recreating venv when stamp is stale."""
        mock_req.return_value = Path("/fake/requirements.txt")
        # venv exists but deps are stale
        mock_python.return_value = MagicMock(exists=MagicMock(return_value=True))

        ensure_aida_environment()

        mock_create.assert_not_called()
        mock_install.assert_called_once()
        mock_add.assert_called_once()


class TestIsAidaEnvironmentReady(unittest.TestCase):
    """Tests for is_aida_environment_ready."""

    @patch("shared.bootstrap._deps_up_to_date", return_value=True)
    @patch("shared.bootstrap._find_requirements_txt")
    @patch("shared.bootstrap._venv_python")
    def test_true_when_ready(self, mock_python, mock_req, mock_up_to_date):
        mock_python.return_value = MagicMock(exists=MagicMock(return_value=True))
        mock_req.return_value = Path("/fake/requirements.txt")
        self.assertTrue(is_aida_environment_ready())

    @patch("shared.bootstrap._venv_python")
    def test_false_when_no_venv(self, mock_python):
        mock_python.return_value = MagicMock(exists=MagicMock(return_value=False))
        self.assertFalse(is_aida_environment_ready())

    @patch("shared.bootstrap._find_requirements_txt", side_effect=FileNotFoundError)
    @patch("shared.bootstrap._venv_python")
    def test_false_when_no_requirements(self, mock_python, mock_req):
        mock_python.return_value = MagicMock(exists=MagicMock(return_value=True))
        self.assertFalse(is_aida_environment_ready())


class TestCreateVenv(unittest.TestCase):
    """Tests for _create_venv."""

    @patch("shared.bootstrap.subprocess.run")
    @patch("shared.bootstrap.AIDA_DIR")
    def test_calls_venv_module(self, mock_aida_dir, mock_run):
        from shared.bootstrap import _create_venv

        mock_run.return_value = MagicMock(returncode=0)

        _create_venv()

        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        self.assertIn("-m", args)
        self.assertIn("venv", args)

    @patch("shared.bootstrap.subprocess.run")
    @patch("shared.bootstrap.AIDA_DIR")
    def test_raises_on_missing_venv_module(self, mock_aida_dir, mock_run):
        from shared.bootstrap import _create_venv

        mock_run.return_value = MagicMock(
            returncode=1,
            stderr="Error: No module named ensurepip",
        )

        with self.assertRaises(RuntimeError) as ctx:
            _create_venv()
        self.assertIn("python3-venv", str(ctx.exception))

    @patch("shared.bootstrap.subprocess.run")
    @patch("shared.bootstrap.AIDA_DIR")
    def test_raises_on_generic_failure(self, mock_aida_dir, mock_run):
        from shared.bootstrap import _create_venv

        mock_run.return_value = MagicMock(
            returncode=1,
            stderr="Some other error",
        )

        with self.assertRaises(RuntimeError) as ctx:
            _create_venv()
        self.assertIn("Some other error", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
