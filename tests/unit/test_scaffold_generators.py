"""Unit tests for plugin-manager generator operations."""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add scripts directories to path
_project_root = Path(__file__).parent.parent.parent
_plugin_scripts = _project_root / "skills" / "plugin-manager" / "scripts"
sys.path.insert(0, str(_project_root / "scripts"))
sys.path.insert(0, str(_plugin_scripts))

# Clear cached operations modules to avoid cross-manager conflicts in pytest
for _mod_name in list(sys.modules):
    if _mod_name == "operations" or _mod_name.startswith("operations."):
        del sys.modules[_mod_name]

from operations.scaffold_ops.generators import (  # noqa: E402
    create_directory_structure,
    render_shared_files,
    assemble_gitignore,
    assemble_makefile,
    initialize_git,
    create_initial_commit,
)

TEMPLATES_DIR = _project_root / "skills" / "plugin-manager" / "templates" / "scaffold"


class TestCreateDirectoryStructure(unittest.TestCase):
    """Test directory structure creation."""

    def test_python_structure(self):
        """Should create Python-specific directories."""
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            created = create_directory_structure(target, "python")
            self.assertIn(".claude-plugin", created)
            self.assertIn(".github/workflows", created)
            self.assertIn("agents", created)
            self.assertIn("skills", created)
            self.assertIn("scripts", created)
            self.assertIn("tests", created)
            self.assertIn("docs", created)
            # Verify directories actually exist
            self.assertTrue((target / ".claude-plugin").is_dir())
            self.assertTrue((target / "scripts").is_dir())
            self.assertTrue((target / "tests").is_dir())
            self.assertTrue((target / ".github" / "workflows").is_dir())

    def test_typescript_structure(self):
        """Should create TypeScript-specific directories."""
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            created = create_directory_structure(target, "typescript")
            self.assertIn(".claude-plugin", created)
            self.assertIn(".github/workflows", created)
            self.assertIn("agents", created)
            self.assertIn("skills", created)
            self.assertIn("src", created)
            self.assertIn("tests", created)
            self.assertIn("docs", created)
            # Verify directories actually exist
            self.assertTrue((target / ".claude-plugin").is_dir())
            self.assertTrue((target / "src").is_dir())
            self.assertTrue((target / "tests").is_dir())
            self.assertTrue((target / ".github" / "workflows").is_dir())

    def test_python_does_not_create_src(self):
        """Python should not create src/ directory."""
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            created = create_directory_structure(target, "python")
            self.assertNotIn("src", created)

    def test_typescript_does_not_create_scripts(self):
        """TypeScript should not create scripts/ directory."""
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            created = create_directory_structure(target, "typescript")
            self.assertNotIn("scripts", created)


class TestRenderSharedFiles(unittest.TestCase):
    """Test shared file rendering."""

    def test_produces_expected_files(self):
        """Should render all shared template files."""
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            target.mkdir(exist_ok=True)

            variables = {
                "plugin_name": "test-plugin",
                "plugin_display_name": "Test Plugin",
                "description": "A test plugin for testing",
                "version": "0.1.0",
                "author_name": "Test Author",
                "author_email": "test@example.com",
                "license_id": "MIT",
                "license_text": "MIT License text here",
                "year": "2026",
                "language": "python",
                "script_extension": ".py",
                "python_version": "3.11",
                "node_version": "20",
                "keywords": ["test"],
                "repository_url": "",
                "include_agent_stub": False,
                "include_skill_stub": False,
                "timestamp": "2026-01-01T00:00:00+00:00",
                "generator_version": "0.9.0",
            }

            created = render_shared_files(target, variables, TEMPLATES_DIR)

            expected_files = [
                ".claude-plugin/plugin.json",
                ".claude-plugin/marketplace.json",
                ".claude-plugin/aida-config.json",
                "CLAUDE.md",
                "README.md",
                ".markdownlint.json",
                ".yamllint.yml",
                ".frontmatter-schema.json",
            ]

            for f in expected_files:
                self.assertIn(f, created, f"Missing file: {f}")
                self.assertTrue((target / f).exists(), f"File not created: {f}")


class TestAssembleGitignore(unittest.TestCase):
    """Test .gitignore assembly."""

    def test_python_gitignore(self):
        """Python gitignore should include Python-specific patterns."""
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            assemble_gitignore(target, "python", TEMPLATES_DIR)
            content = (target / ".gitignore").read_text()
            self.assertIn("__pycache__", content)
            self.assertIn(".DS_Store", content)
            self.assertNotIn("node_modules", content)

    def test_typescript_gitignore(self):
        """TypeScript gitignore should include Node-specific patterns."""
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            assemble_gitignore(target, "typescript", TEMPLATES_DIR)
            content = (target / ".gitignore").read_text()
            self.assertIn("node_modules", content)
            self.assertIn(".DS_Store", content)
            self.assertNotIn("__pycache__", content)

    def test_gitignore_differs_by_language(self):
        """Python and TypeScript gitignores should differ."""
        with tempfile.TemporaryDirectory() as tmp:
            py_target = Path(tmp) / "python"
            py_target.mkdir()
            ts_target = Path(tmp) / "typescript"
            ts_target.mkdir()

            assemble_gitignore(py_target, "python", TEMPLATES_DIR)
            assemble_gitignore(ts_target, "typescript", TEMPLATES_DIR)

            py_content = (py_target / ".gitignore").read_text()
            ts_content = (ts_target / ".gitignore").read_text()

            self.assertNotEqual(py_content, ts_content)


class TestAssembleMakefile(unittest.TestCase):
    """Test Makefile assembly."""

    def test_python_makefile(self):
        """Python Makefile should include ruff and pytest targets."""
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            variables = {
                "plugin_name": "test-plugin",
                "plugin_display_name": "Test Plugin",
            }
            assemble_makefile(target, "python", variables, TEMPLATES_DIR)
            content = (target / "Makefile").read_text()
            self.assertIn("ruff", content)
            self.assertIn("pytest", content)

    def test_typescript_makefile(self):
        """TypeScript Makefile should include eslint and vitest targets."""
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            variables = {
                "plugin_name": "test-plugin",
                "plugin_display_name": "Test Plugin",
            }
            assemble_makefile(target, "typescript", variables, TEMPLATES_DIR)
            content = (target / "Makefile").read_text()
            self.assertIn("lint", content)
            self.assertIn("vitest", content)

    def test_makefile_differs_by_language(self):
        """Python and TypeScript Makefiles should differ."""
        with tempfile.TemporaryDirectory() as tmp:
            py_target = Path(tmp) / "python"
            py_target.mkdir()
            ts_target = Path(tmp) / "typescript"
            ts_target.mkdir()

            variables = {
                "plugin_name": "test-plugin",
                "plugin_display_name": "Test Plugin",
            }

            assemble_makefile(py_target, "python", variables, TEMPLATES_DIR)
            assemble_makefile(ts_target, "typescript", variables, TEMPLATES_DIR)

            py_content = (py_target / "Makefile").read_text()
            ts_content = (ts_target / "Makefile").read_text()

            self.assertNotEqual(py_content, ts_content)


class TestInitializeGit(unittest.TestCase):
    """Test git initialization."""

    @patch("operations.scaffold_ops.generators.subprocess.run")
    def test_success(self, mock_run):
        """Should return True on successful git init."""
        mock_run.return_value = MagicMock(returncode=0)
        with tempfile.TemporaryDirectory() as tmp:
            result = initialize_git(Path(tmp))
            self.assertTrue(result)

    @patch("operations.scaffold_ops.generators.subprocess.run")
    def test_failure(self, mock_run):
        """Should return False when git is not available."""
        mock_run.side_effect = FileNotFoundError("git not found")
        with tempfile.TemporaryDirectory() as tmp:
            result = initialize_git(Path(tmp))
            self.assertFalse(result)


class TestCreateInitialCommit(unittest.TestCase):
    """Test initial commit creation."""

    @patch("operations.scaffold_ops.generators.subprocess.run")
    def test_success(self, mock_run):
        """Should return True when both add and commit succeed."""
        mock_run.return_value = MagicMock(returncode=0)
        result = create_initial_commit(Path("/tmp/test"))
        self.assertTrue(result)
        self.assertEqual(mock_run.call_count, 2)

    @patch("operations.scaffold_ops.generators.subprocess.run")
    def test_failure_on_add(self, mock_run):
        """Should return False when git add fails."""
        mock_run.return_value = MagicMock(returncode=1)
        result = create_initial_commit(Path("/tmp/test"))
        self.assertFalse(result)

    @patch("operations.scaffold_ops.generators.subprocess.run")
    def test_failure_on_commit(self, mock_run):
        """Should return False when git commit fails after add succeeds."""
        add_result = MagicMock(returncode=0)
        commit_result = MagicMock(returncode=1)
        mock_run.side_effect = [add_result, commit_result]
        result = create_initial_commit(Path("/tmp/test"))
        self.assertFalse(result)

    @patch("operations.scaffold_ops.generators.subprocess.run")
    def test_failure_on_file_not_found(self, mock_run):
        """Should return False when git is not available."""
        mock_run.side_effect = FileNotFoundError("git not found")
        result = create_initial_commit(Path("/tmp/test"))
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
