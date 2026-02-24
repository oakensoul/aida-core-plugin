"""Unit tests for create-plugin scaffold.py main entry point."""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# Add scripts directories to path
_project_root = Path(__file__).parent.parent.parent
_scaffold_scripts = _project_root / "skills" / "create-plugin" / "scripts"
sys.path.insert(0, str(_project_root / "scripts"))
sys.path.insert(0, str(_scaffold_scripts))

import scaffold as _scaffold_mod  # noqa: E402

get_questions = _scaffold_mod.get_questions
execute = _scaffold_mod.execute


class TestGetQuestionsNoContext(unittest.TestCase):
    """Test get_questions with no context."""

    @patch.object(_scaffold_mod, "infer_git_config", return_value={"author_name": "", "author_email": ""})
    @patch.object(_scaffold_mod, "check_gh_available", return_value=False)
    def test_returns_all_questions(self, mock_gh, mock_git):
        """With empty context, all questions should be returned."""
        result = get_questions({})
        question_ids = [q["id"] for q in result["questions"]]

        self.assertIn("plugin_name", question_ids)
        self.assertIn("description", question_ids)
        self.assertIn("license", question_ids)
        self.assertIn("language", question_ids)
        self.assertIn("target_directory", question_ids)
        self.assertIn("include_agent_stub", question_ids)
        self.assertIn("include_skill_stub", question_ids)
        self.assertIn("keywords", question_ids)
        self.assertIn("author_name", question_ids)
        self.assertIn("author_email", question_ids)

    @patch.object(_scaffold_mod, "infer_git_config", return_value={"author_name": "", "author_email": ""})
    @patch.object(_scaffold_mod, "check_gh_available", return_value=False)
    def test_no_github_question_without_gh(self, mock_gh, mock_git):
        """Should not ask about GitHub repo if gh is not available."""
        result = get_questions({})
        question_ids = [q["id"] for q in result["questions"]]
        self.assertNotIn("create_github_repo", question_ids)


class TestGetQuestionsPartialContext(unittest.TestCase):
    """Test get_questions with partial context."""

    @patch.object(_scaffold_mod, "infer_git_config", return_value={"author_name": "User", "author_email": "user@test.com"})
    @patch.object(_scaffold_mod, "check_gh_available", return_value=True)
    def test_filters_answered_questions(self, mock_gh, mock_git):
        """Already-provided fields should not generate questions."""
        context = {
            "plugin_name": "my-plugin",
            "description": "A test plugin for testing",
            "license": "MIT",
            "language": "python",
        }
        result = get_questions(context)
        question_ids = [q["id"] for q in result["questions"]]

        self.assertNotIn("plugin_name", question_ids)
        self.assertNotIn("description", question_ids)
        self.assertNotIn("license", question_ids)
        self.assertNotIn("language", question_ids)
        # Should still ask for target_directory, stubs, keywords
        self.assertIn("target_directory", question_ids)
        self.assertIn("include_agent_stub", question_ids)

    @patch.object(_scaffold_mod, "infer_git_config", return_value={"author_name": "User", "author_email": "user@test.com"})
    @patch.object(_scaffold_mod, "check_gh_available", return_value=False)
    def test_infers_git_config(self, mock_gh, mock_git):
        """Should infer author info from git config."""
        result = get_questions({})
        self.assertEqual(result["inferred"]["author_name"], "User")
        self.assertEqual(result["inferred"]["author_email"], "user@test.com")

        # Should not ask for author info since it was inferred
        question_ids = [q["id"] for q in result["questions"]]
        self.assertNotIn("author_name", question_ids)
        self.assertNotIn("author_email", question_ids)

    @patch.object(_scaffold_mod, "infer_git_config", return_value={"author_name": "", "author_email": ""})
    @patch.object(_scaffold_mod, "check_gh_available", return_value=True)
    def test_github_question_with_gh(self, mock_gh, mock_git):
        """Should ask about GitHub repo if gh is available."""
        result = get_questions({})
        question_ids = [q["id"] for q in result["questions"]]
        self.assertIn("create_github_repo", question_ids)


class TestExecutePythonProject(unittest.TestCase):
    """Test execute with Python toolchain."""

    @patch.object(_scaffold_mod, "initialize_git", return_value=True)
    @patch.object(_scaffold_mod, "create_initial_commit", return_value=True)
    def test_creates_full_project(self, mock_commit, mock_git):
        """Should create a complete Python plugin project."""
        with tempfile.TemporaryDirectory() as tmp:
            target = str(Path(tmp) / "test-plugin")

            context = {
                "plugin_name": "test-plugin",
                "description": "A test plugin for testing purposes",
                "license": "MIT",
                "language": "python",
                "target_directory": target,
                "author_name": "Test Author",
                "author_email": "test@example.com",
                "keywords": "test, plugin",
                "version": "0.1.0",
            }

            result = execute(context)

            self.assertTrue(result["success"], f"Execute failed: {result.get('message')}")
            self.assertEqual(result["language"], "python")
            self.assertEqual(result["path"], str(Path(target).resolve()))

            # Verify key files exist
            target_path = Path(result["path"])
            self.assertTrue((target_path / ".claude-plugin" / "plugin.json").exists())
            self.assertTrue((target_path / "CLAUDE.md").exists())
            self.assertTrue((target_path / "README.md").exists())
            self.assertTrue((target_path / "LICENSE").exists())
            self.assertTrue((target_path / "Makefile").exists())
            self.assertTrue((target_path / ".gitignore").exists())
            self.assertTrue((target_path / "pyproject.toml").exists())
            self.assertTrue((target_path / ".python-version").exists())
            self.assertTrue((target_path / "tests" / "conftest.py").exists())


class TestExecuteTypeScriptProject(unittest.TestCase):
    """Test execute with TypeScript toolchain."""

    @patch.object(_scaffold_mod, "initialize_git", return_value=True)
    @patch.object(_scaffold_mod, "create_initial_commit", return_value=True)
    def test_creates_full_project(self, mock_commit, mock_git):
        """Should create a complete TypeScript plugin project."""
        with tempfile.TemporaryDirectory() as tmp:
            target = str(Path(tmp) / "ts-plugin")

            context = {
                "plugin_name": "ts-plugin",
                "description": "A TypeScript test plugin for testing",
                "license": "Apache-2.0",
                "language": "typescript",
                "target_directory": target,
                "author_name": "Test Author",
                "author_email": "test@example.com",
                "keywords": "",
                "version": "0.1.0",
            }

            result = execute(context)

            self.assertTrue(result["success"], f"Execute failed: {result.get('message')}")
            self.assertEqual(result["language"], "typescript")

            # Verify TypeScript-specific files
            target_path = Path(result["path"])
            self.assertTrue((target_path / "package.json").exists())
            self.assertTrue((target_path / "tsconfig.json").exists())
            self.assertTrue((target_path / "eslint.config.mjs").exists())
            self.assertTrue((target_path / ".prettierrc.json").exists())
            self.assertTrue((target_path / ".nvmrc").exists())
            self.assertTrue((target_path / "vitest.config.ts").exists())


class TestExecuteWithAgentStub(unittest.TestCase):
    """Test execute with agent stub."""

    @patch.object(_scaffold_mod, "initialize_git", return_value=True)
    @patch.object(_scaffold_mod, "create_initial_commit", return_value=True)
    def test_creates_agent_stub(self, mock_commit, mock_git):
        """Should create an agent stub when requested."""
        with tempfile.TemporaryDirectory() as tmp:
            target = str(Path(tmp) / "stub-plugin")

            context = {
                "plugin_name": "stub-plugin",
                "description": "A plugin with agent stub for testing",
                "license": "MIT",
                "language": "python",
                "target_directory": target,
                "author_name": "Test",
                "author_email": "test@test.com",
                "include_agent_stub": True,
                "agent_stub_name": "my-agent",
                "agent_stub_description": "A test agent for the plugin",
            }

            result = execute(context)
            self.assertTrue(result["success"], f"Execute failed: {result.get('message')}")

            target_path = Path(result["path"])
            self.assertTrue(
                (target_path / "agents" / "my-agent" / "my-agent.md").exists()
            )


class TestExecuteWithSkillStub(unittest.TestCase):
    """Test execute with skill stub."""

    @patch.object(_scaffold_mod, "initialize_git", return_value=True)
    @patch.object(_scaffold_mod, "create_initial_commit", return_value=True)
    def test_creates_skill_stub(self, mock_commit, mock_git):
        """Should create a skill stub when requested."""
        with tempfile.TemporaryDirectory() as tmp:
            target = str(Path(tmp) / "skill-plugin")

            context = {
                "plugin_name": "skill-plugin",
                "description": "A plugin with skill stub for testing",
                "license": "MIT",
                "language": "python",
                "target_directory": target,
                "author_name": "Test",
                "author_email": "test@test.com",
                "include_skill_stub": True,
                "skill_stub_name": "my-skill",
                "skill_stub_description": "A test skill for the plugin",
            }

            result = execute(context)
            self.assertTrue(result["success"], f"Execute failed: {result.get('message')}")

            target_path = Path(result["path"])
            self.assertTrue(
                (target_path / "skills" / "my-skill" / "SKILL.md").exists()
            )


class TestExecuteValidation(unittest.TestCase):
    """Test execute input validation."""

    def test_rejects_missing_name(self):
        """Should reject execution without plugin_name."""
        result = execute({})
        self.assertFalse(result["success"])
        self.assertIn("plugin_name", result["message"])

    def test_rejects_invalid_name(self):
        """Should reject plugin names that can't be auto-converted to valid kebab-case."""
        # "!!!" converts to empty string via to_kebab_case, which fails validation
        result = execute({"plugin_name": "!!!", "description": "A valid description"})
        self.assertFalse(result["success"])
        self.assertIn("invalid plugin name", result["message"].lower())

    def test_auto_converts_name_to_kebab_case(self):
        """Should auto-convert names to kebab-case before validation."""
        # "Invalid Name!" should be auto-converted to "invalid-name" which is valid
        result = execute({
            "plugin_name": "Invalid Name!",
            "description": "Short",  # Will fail on description, not name
        })
        # This fails on description (too short), proving name was accepted
        self.assertFalse(result["success"])
        self.assertIn("description", result["message"].lower())

    def test_rejects_invalid_description(self):
        """Should reject invalid descriptions."""
        result = execute({"plugin_name": "valid-name", "description": "Short"})
        self.assertFalse(result["success"])
        self.assertIn("description", result["message"].lower())

    def test_rejects_invalid_language(self):
        """Should reject unsupported languages."""
        result = execute({
            "plugin_name": "test-plugin",
            "description": "A valid description for testing",
            "language": "rust",
        })
        self.assertFalse(result["success"])
        self.assertIn("Unsupported language", result["message"])

    def test_rejects_missing_author(self):
        """Should reject execution without author_name."""
        result = execute({
            "plugin_name": "test-plugin",
            "description": "A valid description for testing",
        })
        self.assertFalse(result["success"])
        self.assertIn("author_name", result["message"])

    def test_rejects_missing_author_email(self):
        """Should reject execution without author_email."""
        result = execute({
            "plugin_name": "test-plugin",
            "description": "A valid description for testing",
            "author_name": "Test",
        })
        self.assertFalse(result["success"])
        self.assertIn("author_email", result["message"])

    def test_rejects_existing_non_empty_directory(self):
        """Should reject non-empty target directory."""
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "existing"
            target.mkdir()
            (target / "file.txt").write_text("content")

            result = execute({
                "plugin_name": "test-plugin",
                "description": "A valid description for testing",
                "target_directory": str(target),
                "author_name": "Test",
                "author_email": "test@test.com",
            })
            self.assertFalse(result["success"])
            self.assertIn("not empty", result["message"])


class TestExecuteGitInit(unittest.TestCase):
    """Test git initialization during scaffolding."""

    @patch.object(_scaffold_mod, "initialize_git", return_value=True)
    @patch.object(_scaffold_mod, "create_initial_commit", return_value=True)
    def test_git_init_creates_git_dir(self, mock_commit, mock_git):
        """Should report git initialization status."""
        with tempfile.TemporaryDirectory() as tmp:
            target = str(Path(tmp) / "git-plugin")

            context = {
                "plugin_name": "git-plugin",
                "description": "A plugin to test git init behavior",
                "license": "MIT",
                "language": "python",
                "target_directory": target,
                "author_name": "Test",
                "author_email": "test@test.com",
            }

            result = execute(context)
            self.assertTrue(result["success"])
            self.assertTrue(result["git_initialized"])
            self.assertTrue(result["git_committed"])


if __name__ == "__main__":
    unittest.main()
