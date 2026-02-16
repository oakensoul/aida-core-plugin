"""Unit tests for memento skill memento.py script.

This test suite covers the memento.py script functionality including
slug conversion, validation, frontmatter parsing, and memento operations.
"""

import sys
import subprocess
import unittest
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add scripts directory to path for imports
sys.path.insert(
    0,
    str(
        Path(__file__).parent.parent.parent
        / "skills" / "memento" / "scripts"
    ),
)

from memento import (
    to_kebab_case,
    validate_slug,
    validate_project_name,
    sanitize_git_url,
    parse_frontmatter,
    get_questions,
    execute,
    safe_json_load,
    make_memento_filename,
    parse_memento_filename,
    get_project_context,
    get_pr_context,
    get_changes_context,
    list_mementos,
    render_template,
    main,
    _atomic_write,
    _rebuild_file,
    _ensure_within_dir,
    _reset_project_context_cache,
)


MOCK_PROJECT_CTX = {
    "name": "test-project",
    "path": "/tmp/test-project",
    "repo": "",
    "branch": "",
}


class TestKebabCase(unittest.TestCase):
    """Test kebab-case conversion."""

    def test_basic_conversion(self):
        """Test basic text to kebab-case."""
        self.assertEqual(to_kebab_case("Fix Auth Bug"), "fix-auth-bug")
        self.assertEqual(to_kebab_case("Token Expiry Issue"), "token-expiry-issue")

    def test_with_special_characters(self):
        """Test conversion with special characters."""
        self.assertEqual(to_kebab_case("Fix Bug!"), "fix-bug")
        self.assertEqual(to_kebab_case("API Handler?"), "api-handler")

    def test_with_underscores(self):
        """Test conversion with underscores."""
        self.assertEqual(to_kebab_case("fix_auth_bug"), "fix-auth-bug")
        self.assertEqual(to_kebab_case("test_case_name"), "test-case-name")

    def test_with_numbers(self):
        """Test conversion with numbers."""
        self.assertEqual(to_kebab_case("Test 123"), "test-123")
        self.assertEqual(to_kebab_case("PR 456"), "pr-456")

    def test_truncation(self):
        """Test that long text is truncated to 50 chars."""
        long_text = "a" * 100
        result = to_kebab_case(long_text)
        self.assertLessEqual(len(result), 50)

    def test_empty_string(self):
        """Test conversion of empty string."""
        self.assertEqual(to_kebab_case(""), "")

    def test_multiple_spaces(self):
        """Test conversion with multiple spaces."""
        self.assertEqual(to_kebab_case("fix    auth    bug"), "fix-auth-bug")


class TestValidateSlug(unittest.TestCase):
    """Test slug validation."""

    def test_valid_slugs(self):
        """Test valid memento slugs."""
        valid_slugs = [
            "ab",  # Minimum length
            "fix-auth-bug",
            "api-migration",
            "a1-b2-c3",
            "a" * 50,  # Maximum length
        ]
        for slug in valid_slugs:
            is_valid, error = validate_slug(slug)
            self.assertTrue(
                is_valid,
                f"Slug '{slug}' should be valid: {error}",
            )
            self.assertIsNone(error)

    def test_empty_slug(self):
        """Test empty slug is rejected."""
        is_valid, error = validate_slug("")
        self.assertFalse(is_valid)
        self.assertIn("empty", error.lower())

    def test_too_short(self):
        """Test slug that is too short."""
        is_valid, error = validate_slug("a")
        self.assertFalse(is_valid)
        self.assertIn("2", error)

    def test_too_long(self):
        """Test slug that is too long."""
        is_valid, error = validate_slug("a" * 51)
        self.assertFalse(is_valid)
        self.assertIn("50", error)

    def test_starts_with_number(self):
        """Test slug starting with number is rejected."""
        is_valid, error = validate_slug("1memento")
        self.assertFalse(is_valid)
        self.assertIn("lowercase letter", error.lower())

    def test_uppercase_letters(self):
        """Test slug with uppercase letters is rejected."""
        is_valid, error = validate_slug("FixBug")
        self.assertFalse(is_valid)
        self.assertIn("lowercase", error.lower())

    def test_special_characters(self):
        """Test slug with special characters is rejected."""
        invalid_slugs = ["fix_bug", "fix.bug", "fix@bug", "fix bug"]
        for slug in invalid_slugs:
            is_valid, error = validate_slug(slug)
            self.assertFalse(is_valid, f"Slug '{slug}' should be invalid")


class TestParseFrontmatter(unittest.TestCase):
    """Test YAML frontmatter parsing."""

    def test_basic_frontmatter(self):
        """Test parsing basic frontmatter."""
        content = """---
type: memento
slug: test-memento
description: Test description
status: active
---

# Test Content

Body here."""

        frontmatter, body = parse_frontmatter(content)

        self.assertEqual(frontmatter["type"], "memento")
        self.assertEqual(frontmatter["slug"], "test-memento")
        self.assertEqual(frontmatter["description"], "Test description")
        self.assertEqual(frontmatter["status"], "active")
        self.assertIn("Test Content", body)

    def test_json_arrays_in_frontmatter(self):
        """Test parsing JSON arrays in frontmatter."""
        content = '''---
type: memento
slug: test
tags: ["auth", "bug"]
files: ["src/auth.ts", "src/token.ts"]
---

Body.'''

        frontmatter, body = parse_frontmatter(content)

        self.assertEqual(frontmatter["tags"], ["auth", "bug"])
        self.assertEqual(frontmatter["files"], ["src/auth.ts", "src/token.ts"])

    def test_no_frontmatter(self):
        """Test parsing content without frontmatter."""
        content = "# Just Content\n\nNo frontmatter here."

        frontmatter, body = parse_frontmatter(content)

        self.assertEqual(frontmatter, {})
        self.assertEqual(body, content)

    def test_empty_content(self):
        """Test parsing empty content."""
        frontmatter, body = parse_frontmatter("")

        self.assertEqual(frontmatter, {})
        self.assertEqual(body, "")


class TestMementoFilename(unittest.TestCase):
    """Test memento filename creation and parsing."""

    def test_make_filename(self):
        result = make_memento_filename("my-project", "fix-auth-bug")
        self.assertEqual(result, "my-project--fix-auth-bug.md")

    def test_parse_filename(self):
        project, slug = parse_memento_filename("my-project--fix-auth-bug.md")
        self.assertEqual(project, "my-project")
        self.assertEqual(slug, "fix-auth-bug")

    def test_parse_filename_without_extension(self):
        project, slug = parse_memento_filename("my-project--fix-auth-bug")
        self.assertEqual(project, "my-project")
        self.assertEqual(slug, "fix-auth-bug")

    def test_parse_filename_no_separator(self):
        with self.assertRaises(ValueError):
            parse_memento_filename("no-separator.md")

    def test_roundtrip(self):
        filename = make_memento_filename("proj", "my-slug")
        project, slug = parse_memento_filename(filename)
        self.assertEqual(project, "proj")
        self.assertEqual(slug, "my-slug")

    def test_project_name_with_hyphens(self):
        project, slug = parse_memento_filename("my-cool-project--fix-bug.md")
        self.assertEqual(project, "my-cool-project")
        self.assertEqual(slug, "fix-bug")

    def test_make_filename_rejects_double_hyphen_project(self):
        """Project names with '--' are rejected."""
        with self.assertRaises(ValueError) as cm:
            make_memento_filename("my--project", "fix-bug")
        self.assertIn("--", str(cm.exception))

    def test_make_filename_rejects_path_traversal(self):
        """Project names with '..' are rejected."""
        with self.assertRaises(ValueError) as cm:
            make_memento_filename("../evil", "fix-bug")
        self.assertIn("path traversal", str(cm.exception).lower())

    def test_make_filename_rejects_slash(self):
        """Project names with '/' are rejected."""
        with self.assertRaises(ValueError) as cm:
            make_memento_filename("foo/bar", "fix-bug")
        self.assertIn("path traversal", str(cm.exception).lower())


class TestProjectNameValidation(unittest.TestCase):
    """Test project name validation."""

    def test_valid_names(self):
        for name in ["my-project", "app123", "Cool.App", "a"]:
            is_valid, error = validate_project_name(name)
            self.assertTrue(is_valid, f"'{name}' should be valid")

    def test_empty_name(self):
        is_valid, error = validate_project_name("")
        self.assertFalse(is_valid)

    def test_double_hyphen(self):
        is_valid, error = validate_project_name("my--project")
        self.assertFalse(is_valid)
        self.assertIn("--", error)

    def test_path_traversal(self):
        is_valid, error = validate_project_name("../etc")
        self.assertFalse(is_valid)

    def test_slash(self):
        is_valid, error = validate_project_name("foo/bar")
        self.assertFalse(is_valid)

    def test_too_long(self):
        is_valid, error = validate_project_name("a" * 101)
        self.assertFalse(is_valid)
        self.assertIn("100", error)


class TestSanitizeGitUrl(unittest.TestCase):
    """Test git URL credential sanitization."""

    def test_https_with_credentials(self):
        url = "https://user:token123@github.com/org/repo.git"
        result = sanitize_git_url(url)
        self.assertEqual(result, "https://***@github.com/org/repo.git")
        self.assertNotIn("token123", result)

    def test_https_without_credentials(self):
        url = "https://github.com/org/repo.git"
        result = sanitize_git_url(url)
        self.assertEqual(result, url)

    def test_ssh_url_unchanged(self):
        url = "git@github.com:org/repo.git"
        result = sanitize_git_url(url)
        self.assertEqual(result, url)

    def test_oauth_token(self):
        url = "https://oauth2:ghp_xxxx@github.com/org/repo.git"
        result = sanitize_git_url(url)
        self.assertNotIn("ghp_xxxx", result)
        self.assertIn("***@", result)

    def test_ftp_url_sanitized(self):
        url = "ftp://user:pass@host.com/file"
        result = sanitize_git_url(url)
        self.assertNotIn("pass", result)
        self.assertIn("***@", result)

    def test_git_protocol_sanitized(self):
        url = "git://user:token@host.com/repo.git"
        result = sanitize_git_url(url)
        self.assertNotIn("token", result)
        self.assertIn("***@", result)


class TestNestedFrontmatter(unittest.TestCase):
    """Test nested YAML blocks in frontmatter parsing."""

    def test_project_block(self):
        content = """---
type: memento
slug: test
project:
  name: my-project
  path: /home/user/my-project
  repo: git@github.com:user/my-project.git
  branch: main
---

Body."""
        frontmatter, body = parse_frontmatter(content)
        self.assertEqual(frontmatter["project"]["name"], "my-project")
        self.assertEqual(frontmatter["project"]["path"], "/home/user/my-project")
        self.assertEqual(
            frontmatter["project"]["repo"],
            "git@github.com:user/my-project.git",
        )
        self.assertEqual(frontmatter["project"]["branch"], "main")

    def test_project_block_with_flat_fields(self):
        content = """---
type: memento
slug: test
status: active
project:
  name: my-project
  path: /tmp/proj
description: A test memento
---

Body."""
        frontmatter, body = parse_frontmatter(content)
        self.assertEqual(frontmatter["type"], "memento")
        self.assertEqual(frontmatter["slug"], "test")
        self.assertEqual(frontmatter["status"], "active")
        self.assertEqual(frontmatter["project"]["name"], "my-project")
        self.assertEqual(frontmatter["project"]["path"], "/tmp/proj")
        self.assertEqual(frontmatter["description"], "A test memento")

    def test_empty_nested_block(self):
        content = """---
type: memento
project:
slug: test
---

Body."""
        frontmatter, body = parse_frontmatter(content)
        # PyYAML parses a key with no value as None
        self.assertIsNone(frontmatter["project"])
        self.assertEqual(frontmatter["slug"], "test")

    def test_rebuild_roundtrip(self):
        """Parse frontmatter, rebuild it, parse again - should match."""
        original = {
            "type": "memento",
            "slug": "rt-test",
            "tags": ["a", "b"],
            "project": {"name": "proj", "path": "/tmp"},
        }
        body = "# Hello\n\nSome body."
        rebuilt = _rebuild_file(original, body)
        parsed, parsed_body = parse_frontmatter(rebuilt)
        self.assertEqual(parsed["type"], "memento")
        self.assertEqual(parsed["slug"], "rt-test")
        self.assertEqual(parsed["tags"], ["a", "b"])
        self.assertEqual(parsed["project"]["name"], "proj")
        self.assertIn("Hello", parsed_body)


class TestProjectContext(unittest.TestCase):
    """Test project context detection from git."""

    def setUp(self):
        _reset_project_context_cache()

    def tearDown(self):
        _reset_project_context_cache()

    @patch("memento.subprocess.run")
    def test_git_repo_with_remote_and_branch(self, mock_run):
        with patch("memento.Path.cwd") as mock_cwd:
            mock_path = MagicMock()
            mock_path.name = "my-project"
            mock_path.__str__ = lambda s: "/tmp/my-project"
            mock_git = MagicMock()
            mock_git.exists.return_value = True
            mock_path.__truediv__ = lambda s, k: (
                mock_git
                if k == ".git"
                else MagicMock(exists=MagicMock(return_value=False))
            )
            mock_path.parents = []
            mock_cwd.return_value = mock_path

            remote_result = MagicMock()
            remote_result.returncode = 0
            remote_result.stdout = "git@github.com:user/repo.git\n"

            branch_result = MagicMock()
            branch_result.returncode = 0
            branch_result.stdout = "feature-branch\n"

            mock_run.side_effect = [remote_result, branch_result]

            ctx = get_project_context()
            self.assertEqual(ctx["name"], "my-project")
            self.assertEqual(ctx["repo"], "git@github.com:user/repo.git")
            self.assertEqual(ctx["branch"], "feature-branch")

    @patch("memento.subprocess.run")
    @patch("memento.Path.cwd")
    def test_non_git_directory(self, mock_cwd, mock_run):
        mock_path = MagicMock()
        mock_path.name = "plain-dir"
        mock_path.__str__ = lambda s: "/tmp/plain-dir"
        mock_path.__truediv__ = lambda s, k: MagicMock(
            exists=MagicMock(return_value=False)
        )
        mock_path.parents = []
        mock_cwd.return_value = mock_path

        ctx = get_project_context()
        self.assertEqual(ctx["name"], "plain-dir")
        self.assertEqual(ctx["repo"], "")
        self.assertEqual(ctx["branch"], "")
        mock_run.assert_not_called()

    @patch("memento.subprocess.run")
    def test_subprocess_failure(self, mock_run):
        mock_run.side_effect = subprocess.SubprocessError("fail")
        with patch("memento.Path.cwd") as mock_cwd:
            mock_path = MagicMock()
            mock_path.name = "my-project"
            mock_path.__str__ = lambda s: "/tmp/my-project"
            mock_git = MagicMock()
            mock_git.exists.return_value = True
            mock_path.__truediv__ = lambda s, k: (
                mock_git
                if k == ".git"
                else MagicMock(exists=MagicMock(return_value=False))
            )
            mock_path.parents = []
            mock_cwd.return_value = mock_path

            ctx = get_project_context()
            self.assertEqual(ctx["name"], "my-project")
            self.assertEqual(ctx["repo"], "")
            self.assertEqual(ctx["branch"], "")


class TestListFiltering(unittest.TestCase):
    """Test list_mementos filtering by project."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.mementos_dir = Path(self.temp_dir) / "memento"
        self.archive_dir = Path(self.temp_dir) / "memento" / ".completed"
        self.mementos_dir.mkdir(parents=True)
        self.archive_dir.mkdir(parents=True)

        # Create mementos for different projects
        for project, slug in [
            ("proj-a", "task-1"),
            ("proj-a", "task-2"),
            ("proj-b", "task-3"),
        ]:
            filename = f"{project}--{slug}.md"
            content = f"""---
type: memento
slug: {slug}
description: {slug} for {project}
status: active
created: 2025-01-01T00:00:00Z
updated: 2025-01-01T00:00:00Z
source: manual
tags: []
files: []
project:
  name: {project}
---

Body."""
            (self.mementos_dir / filename).write_text(content, encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("memento.get_user_archive_dir")
    @patch("memento.get_user_mementos_dir")
    @patch("memento.get_project_context")
    def test_list_defaults_to_current_project(
        self, mock_ctx, mock_dir, mock_archive
    ):
        mock_ctx.return_value = {
            "name": "proj-a",
            "path": "/tmp",
            "repo": "",
            "branch": "",
        }
        mock_dir.return_value = self.mementos_dir
        mock_archive.return_value = self.archive_dir

        mementos = list_mementos("active")
        self.assertEqual(len(mementos), 2)
        for m in mementos:
            self.assertEqual(m["project"], "proj-a")

    @patch("memento.get_user_archive_dir")
    @patch("memento.get_user_mementos_dir")
    def test_list_all_projects(self, mock_dir, mock_archive):
        mock_dir.return_value = self.mementos_dir
        mock_archive.return_value = self.archive_dir

        mementos = list_mementos("active", all_projects=True)
        self.assertEqual(len(mementos), 3)

    @patch("memento.get_user_archive_dir")
    @patch("memento.get_user_mementos_dir")
    def test_list_specific_project(self, mock_dir, mock_archive):
        mock_dir.return_value = self.mementos_dir
        mock_archive.return_value = self.archive_dir

        mementos = list_mementos("active", project_filter="proj-b")
        self.assertEqual(len(mementos), 1)
        self.assertEqual(mementos[0]["project"], "proj-b")


class TestGetQuestions(unittest.TestCase):
    """Test question generation."""

    def test_create_without_description(self):
        """Test create operation without description asks for it."""
        context = {"operation": "create", "source": "manual"}
        result = get_questions(context)

        self.assertTrue(len(result["questions"]) > 0)
        question_ids = [q["id"] for q in result["questions"]]
        self.assertIn("description", question_ids)

    @patch("memento.find_memento", return_value=None)
    def test_create_with_description(self, mock_find):
        """Test create operation with description infers metadata."""
        context = {
            "operation": "create",
            "source": "manual",
            "description": "Fix authentication token expiry",
        }
        result = get_questions(context)

        self.assertIn("inferred", result)
        self.assertIn("slug", result["inferred"])
        self.assertEqual(result["inferred"]["source"], "manual")

    @patch("memento.get_pr_context", return_value={})
    def test_create_from_pr_without_pr(self, mock_pr):
        """Test from-pr source when no PR exists."""
        context = {"operation": "create", "source": "from-pr"}
        result = get_questions(context)

        self.assertFalse(result["validation"]["valid"])
        self.assertIn(
            "No PR found", result["validation"]["errors"][0]
        )

    def test_list_no_questions(self):
        """Test list operation doesn't need questions."""
        context = {"operation": "list", "filter": "active"}
        result = get_questions(context)

        self.assertEqual(len(result["questions"]), 0)
        self.assertEqual(result["inferred"]["filter"], "active")

    @patch("memento.list_mementos", return_value=[])
    def test_read_without_slug(self, mock_list):
        """Test read operation without slug asks for selection."""
        context = {"operation": "read"}
        result = get_questions(context)

        self.assertIn("questions", result)

    @patch("memento.list_mementos", return_value=[])
    def test_update_without_slug(self, mock_list):
        """Test update operation without slug asks for selection."""
        context = {"operation": "update"}
        result = get_questions(context)

        self.assertIn("questions", result)

    @patch("memento.list_mementos", return_value=[])
    def test_complete_without_slug(self, mock_list):
        """Test complete operation without slug asks for selection."""
        context = {"operation": "complete"}
        result = get_questions(context)

        self.assertIn("questions", result)


class TestExecute(unittest.TestCase):
    """Test operation execution."""

    @patch("memento.get_user_archive_dir")
    @patch("memento.get_user_mementos_dir")
    @patch("memento.get_project_context", return_value=MOCK_PROJECT_CTX)
    def test_execute_list(self, mock_ctx, mock_dir, mock_archive):
        """Test list operation execution."""
        temp_dir = tempfile.mkdtemp()
        try:
            mock_dir.return_value = Path(temp_dir) / "mementos"
            mock_archive.return_value = Path(temp_dir) / "mementos" / ".completed"
            context = {
                "operation": "list",
                "filter": "active",
            }
            result = execute(context)

            self.assertTrue(result["success"])
            self.assertIn("mementos", result)
            self.assertIn("count", result)
            self.assertEqual(result["filter"], "active")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    @patch("memento.get_user_archive_dir")
    @patch("memento.get_user_mementos_dir")
    @patch("memento.get_project_context", return_value=MOCK_PROJECT_CTX)
    def test_execute_list_all(self, mock_ctx, mock_dir, mock_archive):
        """Test list all operation execution."""
        temp_dir = tempfile.mkdtemp()
        try:
            mock_dir.return_value = Path(temp_dir) / "mementos"
            mock_archive.return_value = Path(temp_dir) / "mementos" / ".completed"
            context = {
                "operation": "list",
                "filter": "all",
            }
            result = execute(context)

            self.assertTrue(result["success"])
            self.assertEqual(result["filter"], "all")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_execute_create_invalid_slug(self):
        """Test create with invalid slug fails."""
        context = {
            "operation": "create",
            "slug": "Invalid Slug!",
            "description": "Test memento for testing purposes",
        }
        result = execute(context)

        self.assertFalse(result["success"])
        self.assertIn("Invalid slug", result["message"])

    def test_execute_read_missing_slug(self):
        """Test read operation without slug fails."""
        context = {
            "operation": "read",
        }
        result = execute(context)

        self.assertFalse(result["success"])
        self.assertIn("Slug is required", result["message"])

    @patch("memento.get_user_archive_dir")
    @patch("memento.get_user_mementos_dir")
    @patch("memento.get_project_context", return_value=MOCK_PROJECT_CTX)
    def test_execute_read_not_found(self, mock_ctx, mock_dir, mock_archive):
        """Test read operation with non-existent slug."""
        temp_dir = tempfile.mkdtemp()
        try:
            mock_dir.return_value = Path(temp_dir) / "mementos"
            mock_archive.return_value = Path(temp_dir) / "mementos" / ".completed"
            context = {
                "operation": "read",
                "slug": "nonexistent-memento-12345",
            }
            result = execute(context)

            self.assertFalse(result["success"])
            self.assertIn("not found", result["message"])
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_execute_update_missing_slug(self):
        """Test update operation without slug fails."""
        context = {
            "operation": "update",
        }
        result = execute(context)

        self.assertFalse(result["success"])
        self.assertIn("Slug is required", result["message"])

    def test_execute_update_missing_section(self):
        """Test update operation without section fails."""
        context = {
            "operation": "update",
            "slug": "some-slug",
            "content": "some content",
        }
        result = execute(context)

        self.assertFalse(result["success"])
        self.assertIn("Section is required", result["message"])

    def test_execute_complete_missing_slug(self):
        """Test complete operation without slug fails."""
        context = {
            "operation": "complete",
        }
        result = execute(context)

        self.assertFalse(result["success"])
        self.assertIn("Slug is required", result["message"])

    def test_execute_remove_missing_slug(self):
        """Test remove operation without slug fails."""
        context = {
            "operation": "remove",
        }
        result = execute(context)

        self.assertFalse(result["success"])
        self.assertIn("Slug is required", result["message"])

    def test_execute_unknown_operation(self):
        """Test unknown operation fails."""
        context = {
            "operation": "unknown",
        }
        result = execute(context)

        self.assertFalse(result["success"])
        self.assertIn("Unknown operation", result["message"])


class TestSafeJsonLoad(unittest.TestCase):
    """Test safe JSON loading."""

    def test_valid_json(self):
        """Test loading valid JSON."""
        result = safe_json_load('{"key": "value"}')
        self.assertEqual(result, {"key": "value"})

    def test_empty_string(self):
        """Test loading empty string returns empty dict."""
        result = safe_json_load("")
        self.assertEqual(result, {})

    def test_none_input(self):
        """Test loading None returns empty dict."""
        result = safe_json_load(None)
        self.assertEqual(result, {})

    def test_invalid_json(self):
        """Test invalid JSON raises ValueError."""
        with self.assertRaises(ValueError):
            safe_json_load("{invalid json}")

    def test_size_limit(self):
        """Test oversized JSON is rejected."""
        large_json = json.dumps({"data": "x" * (100 * 1024 + 1)})
        with self.assertRaises(ValueError) as cm:
            safe_json_load(large_json)
        self.assertIn("size limit", str(cm.exception).lower())


class TestFrontmatterEdgeCases(unittest.TestCase):
    """Test edge cases in frontmatter parsing."""

    def test_frontmatter_with_yaml_lists(self):
        """Test parsing YAML-style lists in frontmatter."""
        content = """---
type: memento
slug: test
tags:
  - auth
  - bug
  - urgent
---

Body."""

        frontmatter, body = parse_frontmatter(content)

        self.assertEqual(frontmatter["tags"], ["auth", "bug", "urgent"])

    def test_frontmatter_with_quoted_values(self):
        """Test parsing quoted values in frontmatter."""
        content = """---
type: memento
slug: "test-slug"
description: 'Test description with special: chars'
---

Body."""

        frontmatter, body = parse_frontmatter(content)

        self.assertEqual(frontmatter["slug"], "test-slug")
        self.assertEqual(frontmatter["description"], "Test description with special: chars")

    def test_frontmatter_with_empty_values(self):
        """Test parsing frontmatter with empty values."""
        content = """---
type: memento
slug: test
description:
tags: []
---

Body."""

        frontmatter, body = parse_frontmatter(content)

        self.assertEqual(frontmatter["type"], "memento")
        self.assertEqual(frontmatter["slug"], "test")


class TestQuestionGeneration(unittest.TestCase):
    """Test detailed question generation scenarios."""

    @patch("memento.find_memento", return_value=None)
    def test_create_asks_for_problem(self, mock_find):
        """Test that create asks for problem description."""
        context = {
            "operation": "create",
            "source": "manual",
            "description": "Fix authentication bug",
        }
        result = get_questions(context)

        question_ids = [q["id"] for q in result["questions"]]
        self.assertIn("problem", question_ids)

    @patch("memento.find_memento", return_value=None)
    def test_update_asks_for_section(self, mock_find):
        """Test that update operation provides section options."""
        context = {
            "operation": "update",
            "slug": "some-memento",  # Note: won't exist, but tests flow
        }
        result = get_questions(context)

        # Will ask for section if memento doesn't exist
        self.assertIn("validation", result)

    @patch("memento.get_pr_context", return_value={})
    def test_validation_errors_for_invalid_source(self, mock_pr):
        """Test validation errors for from-pr when no PR exists."""
        context = {
            "operation": "create",
            "source": "from-pr",
        }
        result = get_questions(context)

        self.assertFalse(result["validation"]["valid"])
        self.assertIn(
            "No PR found", result["validation"]["errors"][0]
        )


class TestAtomicWrite(unittest.TestCase):
    """Test atomic file writing."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_writes_file_successfully(self):
        target = Path(self.temp_dir) / "test.md"
        _atomic_write(target, "hello world")
        self.assertEqual(target.read_text(), "hello world")

    def test_sets_restrictive_permissions(self):
        target = Path(self.temp_dir) / "test.md"
        _atomic_write(target, "secret")
        import stat
        mode = stat.S_IMODE(target.stat().st_mode)
        self.assertEqual(mode, 0o600)

    def test_no_temp_file_on_success(self):
        target = Path(self.temp_dir) / "test.md"
        _atomic_write(target, "content")
        temps = list(Path(self.temp_dir).glob(".memento-*.tmp"))
        self.assertEqual(len(temps), 0)

    def test_overwrites_existing_atomically(self):
        target = Path(self.temp_dir) / "test.md"
        target.write_text("old content")
        _atomic_write(target, "new content")
        self.assertEqual(target.read_text(), "new content")


class TestFrontmatterRoundTrip(unittest.TestCase):
    """Test that templates produce parseable frontmatter (#14)."""

    def test_work_session_template_roundtrip(self):
        """Render work-session template and verify frontmatter parses."""
        template_vars = {
            "slug": "test-roundtrip",
            "description": "Test roundtrip",
            "status": "active",
            "created": "2025-01-01T00:00:00Z",
            "updated": "2025-01-01T00:00:00Z",
            "source": "manual",
            "tags": ["test", "roundtrip"],
            "files": ["src/main.py"],
            "project_name": "my-project",
            "project_path": "/tmp/my-project",
            "project_repo": "git@github.com:user/repo.git",
            "project_branch": "main",
            "problem": "Test problem",
            "approach": "Test approach",
            "completed": "- Item one",
            "in_progress": "- Item two",
            "pending": "- Item three",
            "decisions": "- Decision one",
            "files_detail": "- src/main.py: entry point",
            "next_step": "Continue testing",
        }
        content = render_template("work-session.md.jinja2", template_vars)
        frontmatter, body = parse_frontmatter(content)

        self.assertEqual(frontmatter["type"], "memento")
        self.assertEqual(frontmatter["slug"], "test-roundtrip")
        self.assertEqual(frontmatter["status"], "active")
        self.assertEqual(frontmatter["tags"], ["test", "roundtrip"])
        self.assertEqual(frontmatter["project"]["name"], "my-project")
        self.assertEqual(
            frontmatter["project"]["repo"],
            "git@github.com:user/repo.git",
        )
        self.assertIn("Test problem", body)
        self.assertIn("Test approach", body)

    def test_freeform_template_roundtrip(self):
        """Render freeform template and verify frontmatter parses."""
        template_vars = {
            "slug": "freeform-test",
            "description": "A freeform memento",
            "status": "active",
            "created": "2025-01-01T00:00:00Z",
            "updated": "2025-01-01T00:00:00Z",
            "source": "manual",
            "tags": [],
            "files": [],
            "project_name": "proj",
            "project_path": "/tmp/proj",
            "project_repo": "",
            "project_branch": "dev",
            "content": "Free-form notes here.",
        }
        content = render_template("freeform.md.jinja2", template_vars)
        frontmatter, body = parse_frontmatter(content)

        self.assertEqual(frontmatter["type"], "memento")
        self.assertEqual(frontmatter["slug"], "freeform-test")
        self.assertEqual(frontmatter["project"]["name"], "proj")
        self.assertEqual(frontmatter["project"]["branch"], "dev")
        self.assertIn("Free-form notes here.", body)


class TestMementoLifecycle(unittest.TestCase):
    """End-to-end lifecycle: create -> read -> update -> complete (#13)."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.mementos_dir = Path(self.temp_dir) / "memento"
        self.archive_dir = self.mementos_dir / ".completed"
        self.mementos_dir.mkdir(parents=True)
        self.project_ctx = {
            "name": "lifecycle-proj",
            "path": "/tmp/lifecycle-proj",
            "repo": "git@github.com:user/lifecycle.git",
            "branch": "main",
        }

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("memento.get_user_archive_dir")
    @patch("memento.get_user_mementos_dir")
    @patch("memento.get_project_context")
    def test_full_lifecycle(self, mock_ctx, mock_dir, mock_archive):
        mock_ctx.return_value = self.project_ctx
        mock_dir.return_value = self.mementos_dir
        mock_archive.return_value = self.archive_dir

        # 1. Create
        result = execute({
            "operation": "create",
            "slug": "lifecycle-test",
            "description": "Lifecycle test memento",
            "source": "manual",
            "problem": "Testing the full lifecycle",
            "template": "work-session",
        })
        self.assertTrue(result["success"], result.get("message"))
        self.assertEqual(result["project"], "lifecycle-proj")
        created_path = Path(result["path"])
        self.assertTrue(created_path.exists())

        # 2. Read
        result = execute({
            "operation": "read",
            "slug": "lifecycle-test",
        })
        self.assertTrue(result["success"], result.get("message"))
        self.assertEqual(result["frontmatter"]["slug"], "lifecycle-test")
        self.assertEqual(result["frontmatter"]["status"], "active")
        self.assertIn("Lifecycle test memento", result["content"])

        # 3. Update
        result = execute({
            "operation": "update",
            "slug": "lifecycle-test",
            "section": "progress",
            "content": "- Implemented step one\n- Tested step one",
        })
        self.assertTrue(result["success"], result.get("message"))

        # Verify update persisted
        result = execute({
            "operation": "read",
            "slug": "lifecycle-test",
        })
        self.assertTrue(result["success"])
        self.assertIn("Implemented step one", result["body"])

        # 4. Complete
        result = execute({
            "operation": "complete",
            "slug": "lifecycle-test",
        })
        self.assertTrue(result["success"], result.get("message"))
        self.assertIn(".completed", result["path"])

        # Verify source file removed
        self.assertFalse(created_path.exists())

        # Verify archived file exists and has completed status
        archived_path = Path(result["path"])
        self.assertTrue(archived_path.exists())
        content = archived_path.read_text(encoding="utf-8")
        frontmatter, _ = parse_frontmatter(content)
        self.assertEqual(frontmatter["status"], "completed")

        # 5. Remove from archive
        result = execute({
            "operation": "remove",
            "slug": "lifecycle-test",
        })
        self.assertTrue(result["success"], result.get("message"))
        self.assertFalse(archived_path.exists())


class TestEnsureWithinDir(unittest.TestCase):
    """Test path containment validation."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.base_dir = Path(self.temp_dir) / "memento"
        self.base_dir.mkdir()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_valid_path_within_dir(self):
        child = self.base_dir / "test.md"
        child.touch()
        resolved = _ensure_within_dir(child, self.base_dir)
        self.assertEqual(resolved, child.resolve())

    def test_rejects_symlink(self):
        target = Path(self.temp_dir) / "outside.md"
        target.touch()
        link = self.base_dir / "link.md"
        link.symlink_to(target)
        with self.assertRaises(ValueError) as cm:
            _ensure_within_dir(link, self.base_dir)
        self.assertIn("Symlink", str(cm.exception))

    def test_rejects_path_escape(self):
        """Path that resolves outside base_dir is rejected."""
        outside = Path(self.temp_dir) / "outside.md"
        outside.touch()
        with self.assertRaises(ValueError):
            _ensure_within_dir(outside, self.base_dir)

    def test_base_dir_itself_is_accepted(self):
        """The base directory path itself should not be rejected."""
        resolved = _ensure_within_dir(self.base_dir, self.base_dir)
        self.assertEqual(resolved, self.base_dir.resolve())


class TestSectionReplacement(unittest.TestCase):
    """Test section replacement correctness in execute_update."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.mementos_dir = Path(self.temp_dir) / "memento"
        self.archive_dir = self.mementos_dir / ".completed"
        self.mementos_dir.mkdir(parents=True)
        self.project_ctx = {
            "name": "test-proj",
            "path": "/tmp/test-proj",
            "repo": "",
            "branch": "main",
        }

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_memento(self, mock_ctx, mock_dir, mock_archive):
        mock_ctx.return_value = self.project_ctx
        mock_dir.return_value = self.mementos_dir
        mock_archive.return_value = self.archive_dir
        result = execute({
            "operation": "create",
            "slug": "section-test",
            "description": "Section replacement test",
            "source": "manual",
            "problem": "Testing sections",
            "template": "work-session",
        })
        self.assertTrue(result["success"], result.get("message"))
        return result

    @patch("memento.get_user_archive_dir")
    @patch("memento.get_user_mementos_dir")
    @patch("memento.get_project_context")
    def test_progress_replaces_not_appends(
        self, mock_ctx, mock_dir, mock_archive
    ):
        """Old progress content is replaced, not duplicated."""
        self._create_memento(mock_ctx, mock_dir, mock_archive)

        # First update
        execute({
            "operation": "update",
            "slug": "section-test",
            "section": "progress",
            "content": "- Step one done",
        })

        # Second update should replace, not append
        execute({
            "operation": "update",
            "slug": "section-test",
            "section": "progress",
            "content": "- Step two done",
        })

        result = execute({
            "operation": "read",
            "slug": "section-test",
        })
        self.assertIn("Step two done", result["body"])
        self.assertNotIn("Step one done", result["body"])

    @patch("memento.get_user_archive_dir")
    @patch("memento.get_user_mementos_dir")
    @patch("memento.get_project_context")
    def test_decisions_update_preserves_other_sections(
        self, mock_ctx, mock_dir, mock_archive
    ):
        """Updating decisions doesn't corrupt adjacent sections."""
        self._create_memento(mock_ctx, mock_dir, mock_archive)

        execute({
            "operation": "update",
            "slug": "section-test",
            "section": "decisions",
            "content": "- Decided to use PyYAML",
        })

        result = execute({
            "operation": "read",
            "slug": "section-test",
        })
        body = result["body"]
        self.assertIn("Decided to use PyYAML", body)
        # Other sections still present
        self.assertIn("## Problem", body)
        self.assertIn("## Next Step", body)
        self.assertIn("## Files", body)

    @patch("memento.get_user_archive_dir")
    @patch("memento.get_user_mementos_dir")
    @patch("memento.get_project_context")
    def test_next_step_update(self, mock_ctx, mock_dir, mock_archive):
        """Next step section can be updated."""
        self._create_memento(mock_ctx, mock_dir, mock_archive)

        execute({
            "operation": "update",
            "slug": "section-test",
            "section": "next_step",
            "content": "Deploy to staging",
        })

        result = execute({
            "operation": "read",
            "slug": "section-test",
        })
        self.assertIn("Deploy to staging", result["body"])

    @patch("memento.get_user_archive_dir")
    @patch("memento.get_user_mementos_dir")
    @patch("memento.get_project_context")
    def test_backreference_in_content_not_interpreted(
        self, mock_ctx, mock_dir, mock_archive
    ):
        r"""Content with \1 or \g<1> is treated literally."""
        self._create_memento(mock_ctx, mock_dir, mock_archive)

        result = execute({
            "operation": "update",
            "slug": "section-test",
            "section": "progress",
            "content": r"- Used \1 backreference pattern in regex",
        })
        self.assertTrue(result["success"])

        result = execute({
            "operation": "read",
            "slug": "section-test",
        })
        self.assertIn(r"\1 backreference", result["body"])

    @patch("memento.get_user_archive_dir")
    @patch("memento.get_user_mementos_dir")
    @patch("memento.get_project_context")
    def test_unknown_section_appends(
        self, mock_ctx, mock_dir, mock_archive
    ):
        """Unknown section name appends a new section."""
        self._create_memento(mock_ctx, mock_dir, mock_archive)

        result = execute({
            "operation": "update",
            "slug": "section-test",
            "section": "custom_notes",
            "content": "My custom content",
        })
        self.assertTrue(result["success"])

        result = execute({
            "operation": "read",
            "slug": "section-test",
        })
        self.assertIn("## Custom_Notes", result["body"])
        self.assertIn("My custom content", result["body"])


class TestPrContext(unittest.TestCase):
    """Test PR context extraction."""

    @patch("memento.subprocess.run")
    def test_successful_pr(self, mock_run):
        pr_data = {
            "number": 42,
            "url": "https://github.com/org/repo/pull/42",
            "title": "Fix auth bug",
            "body": "Fixes token expiry",
            "files": [
                {"path": "src/auth.py"},
                {"path": "tests/test_auth.py"},
            ],
        }
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(pr_data)
        mock_run.return_value = mock_result

        ctx = get_pr_context()
        self.assertEqual(ctx["pr_number"], 42)
        self.assertEqual(ctx["title"], "Fix auth bug")
        self.assertEqual(
            ctx["files"],
            ["src/auth.py", "tests/test_auth.py"],
        )

    @patch("memento.subprocess.run")
    def test_no_pr(self, mock_run):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_run.return_value = mock_result

        ctx = get_pr_context()
        self.assertEqual(ctx, {})

    @patch("memento.subprocess.run")
    def test_timeout(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired("gh", 30)

        ctx = get_pr_context()
        self.assertEqual(ctx, {})


class TestChangesContext(unittest.TestCase):
    """Test git changes context extraction."""

    @patch("memento.subprocess.run")
    def test_with_changes(self, mock_run):
        diff_stat = MagicMock(
            returncode=0, stdout="2 files changed"
        )
        diff_names = MagicMock(
            returncode=0, stdout="src/main.py\nsrc/utils.py\n"
        )
        status = MagicMock(
            returncode=0, stdout="?? new_file.py\n"
        )
        mock_run.side_effect = [diff_stat, diff_names, status]

        ctx = get_changes_context()
        self.assertIn("src/main.py", ctx["files"])
        self.assertIn("src/utils.py", ctx["files"])
        self.assertIn("new_file.py", ctx["files"])
        self.assertEqual(ctx["summary"], "2 files changed")

    @patch("memento.subprocess.run")
    def test_no_changes(self, mock_run):
        empty = MagicMock(returncode=0, stdout="")
        mock_run.return_value = empty

        ctx = get_changes_context()
        self.assertEqual(ctx["files"], [])

    @patch("memento.subprocess.run")
    def test_subprocess_failure(self, mock_run):
        mock_run.side_effect = subprocess.SubprocessError("fail")

        ctx = get_changes_context()
        self.assertEqual(ctx["files"], [])
        self.assertEqual(ctx["summary"], "")


class TestDuplicateSlug(unittest.TestCase):
    """Test duplicate slug detection."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.mementos_dir = Path(self.temp_dir) / "memento"
        self.archive_dir = self.mementos_dir / ".completed"
        self.mementos_dir.mkdir(parents=True)
        self.project_ctx = {
            "name": "dup-proj",
            "path": "/tmp/dup-proj",
            "repo": "",
            "branch": "main",
        }

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("memento.get_user_archive_dir")
    @patch("memento.get_user_mementos_dir")
    @patch("memento.get_project_context")
    def test_create_duplicate_slug_fails(
        self, mock_ctx, mock_dir, mock_archive
    ):
        mock_ctx.return_value = self.project_ctx
        mock_dir.return_value = self.mementos_dir
        mock_archive.return_value = self.archive_dir

        # First create succeeds
        result = execute({
            "operation": "create",
            "slug": "dupe-test",
            "description": "First memento",
            "source": "manual",
            "problem": "Testing duplicates",
        })
        self.assertTrue(result["success"])

        # Second create with same slug fails
        result = execute({
            "operation": "create",
            "slug": "dupe-test",
            "description": "Second memento",
            "source": "manual",
            "problem": "Duplicate slug",
        })
        self.assertFalse(result["success"])
        self.assertIn("already exists", result["message"])


class TestCLI(unittest.TestCase):
    """Test CLI entry point."""

    def test_get_questions_returns_zero(self):
        with patch(
            "sys.argv",
            ["memento.py", "--get-questions",
             "--context", '{"operation": "list"}'],
        ):
            with patch("builtins.print"):
                code = main()
        self.assertEqual(code, 0)

    def test_no_args_returns_one(self):
        with patch("sys.argv", ["memento.py"]):
            with patch("builtins.print"):
                code = main()
        self.assertEqual(code, 1)

    def test_invalid_json_returns_one(self):
        with patch(
            "sys.argv",
            ["memento.py", "--execute",
             "--context", "{bad json}"],
        ):
            with patch("builtins.print"):
                code = main()
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
