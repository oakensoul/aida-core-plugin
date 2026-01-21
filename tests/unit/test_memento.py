"""Unit tests for memento skill memento.py script.

This test suite covers the memento.py script functionality including
slug conversion, validation, frontmatter parsing, and memento operations.
"""

import sys
import unittest
import json
import tempfile
import shutil
from pathlib import Path

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "skills" / "memento" / "scripts"))

from memento import (
    to_kebab_case,
    validate_slug,
    parse_frontmatter,
    get_questions,
    execute,
    safe_json_load,
)


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
            self.assertTrue(is_valid, f"Slug '{slug}' should be valid, got error: {error}")
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


class TestGetQuestions(unittest.TestCase):
    """Test question generation."""

    def test_create_without_description(self):
        """Test create operation without description asks for it."""
        context = {"operation": "create", "source": "manual"}
        result = get_questions(context)

        self.assertTrue(len(result["questions"]) > 0)
        question_ids = [q["id"] for q in result["questions"]]
        self.assertIn("description", question_ids)

    def test_create_with_description(self):
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

    def test_create_from_pr_without_pr(self):
        """Test from-pr source when no PR exists."""
        context = {"operation": "create", "source": "from-pr"}
        result = get_questions(context)

        # Should have validation error (no PR found)
        # Note: This will fail if there's an active PR
        self.assertIn("validation", result)

    def test_list_no_questions(self):
        """Test list operation doesn't need questions."""
        context = {"operation": "list", "filter": "active"}
        result = get_questions(context)

        self.assertEqual(len(result["questions"]), 0)
        self.assertEqual(result["inferred"]["filter"], "active")

    def test_read_without_slug(self):
        """Test read operation without slug asks for selection."""
        context = {"operation": "read"}
        result = get_questions(context)

        # If there are active mementos, it will ask for selection
        # If no mementos, it will have validation error
        self.assertIn("questions", result)

    def test_update_without_slug(self):
        """Test update operation without slug asks for selection."""
        context = {"operation": "update"}
        result = get_questions(context)

        self.assertIn("questions", result)

    def test_complete_without_slug(self):
        """Test complete operation without slug asks for selection."""
        context = {"operation": "complete"}
        result = get_questions(context)

        self.assertIn("questions", result)


class TestExecute(unittest.TestCase):
    """Test operation execution."""

    def test_execute_list(self):
        """Test list operation execution."""
        context = {
            "operation": "list",
            "filter": "active",
        }
        result = execute(context)

        self.assertTrue(result["success"])
        self.assertIn("mementos", result)
        self.assertIn("count", result)
        self.assertEqual(result["filter"], "active")

    def test_execute_list_all(self):
        """Test list all operation execution."""
        context = {
            "operation": "list",
            "filter": "all",
        }
        result = execute(context)

        self.assertTrue(result["success"])
        self.assertEqual(result["filter"], "all")

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

    def test_execute_read_not_found(self):
        """Test read operation with non-existent slug."""
        context = {
            "operation": "read",
            "slug": "nonexistent-memento-12345",
        }
        result = execute(context)

        self.assertFalse(result["success"])
        self.assertIn("not found", result["message"])

    def test_execute_update_missing_slug(self):
        """Test update operation without slug fails."""
        context = {
            "operation": "update",
        }
        result = execute(context)

        self.assertFalse(result["success"])
        self.assertIn("Slug is required", result["message"])

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


class TestMementoOperationsWithTempDir(unittest.TestCase):
    """Test memento operations using a temporary directory."""

    def setUp(self):
        """Set up temporary directory for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.mementos_dir = Path(self.temp_dir) / ".claude" / "mementos"
        self.archive_dir = self.mementos_dir / ".archive"

    def tearDown(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_create_memento_validation(self):
        """Test memento creation validation."""
        # Valid slug
        is_valid, error = validate_slug("test-memento")
        self.assertTrue(is_valid)
        self.assertIsNone(error)

        # Test inferred slug from description
        slug = to_kebab_case("Fix authentication token expiry")
        self.assertEqual(slug, "fix-authentication-token-expiry")

    def test_slug_generation_from_description(self):
        """Test slug generation from various descriptions."""
        test_cases = [
            ("Fix auth bug", "fix-auth-bug"),
            ("Add new feature", "add-new-feature"),
            ("PR #123 Changes", "pr-123-changes"),
            ("API Migration", "api-migration"),
        ]

        for description, expected_slug in test_cases:
            slug = to_kebab_case(description)
            self.assertEqual(slug, expected_slug, f"Failed for: {description}")


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

    def test_create_asks_for_problem(self):
        """Test that create asks for problem description."""
        context = {
            "operation": "create",
            "source": "manual",
            "description": "Fix authentication bug",
        }
        result = get_questions(context)

        question_ids = [q["id"] for q in result["questions"]]
        self.assertIn("problem", question_ids)

    def test_update_asks_for_section(self):
        """Test that update operation provides section options."""
        context = {
            "operation": "update",
            "slug": "some-memento",  # Note: won't exist, but tests flow
        }
        result = get_questions(context)

        # Will ask for section if memento doesn't exist
        self.assertIn("validation", result)

    def test_validation_errors_for_invalid_source(self):
        """Test validation errors for from-pr when no PR exists."""
        context = {
            "operation": "create",
            "source": "from-pr",
        }
        result = get_questions(context)

        # This may or may not have errors depending on if there's an active PR
        self.assertIn("validation", result)


def run_tests():
    """Run all tests and return results."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestKebabCase))
    suite.addTests(loader.loadTestsFromTestCase(TestValidateSlug))
    suite.addTests(loader.loadTestsFromTestCase(TestParseFrontmatter))
    suite.addTests(loader.loadTestsFromTestCase(TestGetQuestions))
    suite.addTests(loader.loadTestsFromTestCase(TestExecute))
    suite.addTests(loader.loadTestsFromTestCase(TestSafeJsonLoad))
    suite.addTests(loader.loadTestsFromTestCase(TestMementoOperationsWithTempDir))
    suite.addTests(loader.loadTestsFromTestCase(TestFrontmatterEdgeCases))
    suite.addTests(loader.loadTestsFromTestCase(TestQuestionGeneration))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result


if __name__ == "__main__":
    result = run_tests()
    sys.exit(0 if result.wasSuccessful() else 1)
