"""Unit tests for claude-code-management manage.py script.

This test suite covers the manage.py script functionality including
name conversion, validation, version bumping, and component operations.
"""

import sys
import unittest
import json
from pathlib import Path

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "skills" / "claude-code-management" / "scripts"))

from operations.utils import (
    to_kebab_case,
    validate_name,
    validate_description,
    validate_version,
    bump_version,
    safe_json_load,
)
from operations.extensions import infer_from_description
from manage import get_questions, execute


class TestKebabCase(unittest.TestCase):
    """Test kebab-case conversion."""

    def test_basic_conversion(self):
        """Test basic text to kebab-case."""
        self.assertEqual(to_kebab_case("Hello World"), "hello-world")
        self.assertEqual(to_kebab_case("Database Migration"), "database-migration")

    def test_with_special_characters(self):
        """Test conversion with special characters."""
        self.assertEqual(to_kebab_case("Hello! World?"), "hello-world")
        self.assertEqual(to_kebab_case("API Handler"), "api-handler")

    def test_with_underscores(self):
        """Test conversion with underscores."""
        self.assertEqual(to_kebab_case("hello_world"), "hello-world")
        self.assertEqual(to_kebab_case("test_case_name"), "test-case-name")

    def test_with_mixed_case(self):
        """Test conversion with mixed case."""
        self.assertEqual(to_kebab_case("HelloWorld"), "helloworld")
        self.assertEqual(to_kebab_case("UPPERCASE"), "uppercase")

    def test_with_numbers(self):
        """Test conversion with numbers."""
        self.assertEqual(to_kebab_case("Test 123"), "test-123")
        self.assertEqual(to_kebab_case("v2 api"), "v2-api")

    def test_with_leading_trailing_spaces(self):
        """Test conversion with leading/trailing spaces."""
        self.assertEqual(to_kebab_case("  hello world  "), "hello-world")

    def test_multiple_spaces(self):
        """Test conversion with multiple spaces."""
        self.assertEqual(to_kebab_case("hello    world"), "hello-world")

    def test_empty_string(self):
        """Test conversion of empty string."""
        self.assertEqual(to_kebab_case(""), "")


class TestValidateName(unittest.TestCase):
    """Test name validation."""

    def test_valid_names(self):
        """Test valid component names."""
        valid_names = [
            "ab",  # Minimum length
            "my-agent",
            "test-command",
            "api-handler",
            "a1-b2-c3",
            "a" * 50,  # Maximum length
        ]
        for name in valid_names:
            is_valid, error = validate_name(name)
            self.assertTrue(is_valid, f"Name '{name}' should be valid, got error: {error}")
            self.assertIsNone(error)

    def test_empty_name(self):
        """Test empty name is rejected."""
        is_valid, error = validate_name("")
        self.assertFalse(is_valid)
        self.assertIn("empty", error.lower())

    def test_too_short(self):
        """Test name that is too short."""
        is_valid, error = validate_name("a")
        self.assertFalse(is_valid)
        self.assertIn("2", error)

    def test_too_long(self):
        """Test name that is too long."""
        is_valid, error = validate_name("a" * 51)
        self.assertFalse(is_valid)
        self.assertIn("50", error)

    def test_starts_with_number(self):
        """Test name starting with number is rejected."""
        is_valid, error = validate_name("1agent")
        self.assertFalse(is_valid)
        self.assertIn("lowercase letter", error.lower())

    def test_uppercase_letters(self):
        """Test name with uppercase letters is rejected."""
        is_valid, error = validate_name("MyAgent")
        self.assertFalse(is_valid)
        self.assertIn("lowercase", error.lower())

    def test_special_characters(self):
        """Test name with special characters is rejected."""
        invalid_names = ["my_agent", "my.agent", "my@agent", "my agent"]
        for name in invalid_names:
            is_valid, error = validate_name(name)
            self.assertFalse(is_valid, f"Name '{name}' should be invalid")


class TestValidateDescription(unittest.TestCase):
    """Test description validation."""

    def test_valid_descriptions(self):
        """Test valid descriptions."""
        valid_descriptions = [
            "A" * 10,  # Minimum length
            "This is a valid description for a component.",
            "A" * 500,  # Maximum length
        ]
        for desc in valid_descriptions:
            is_valid, error = validate_description(desc)
            self.assertTrue(is_valid, f"Description should be valid, got error: {error}")
            self.assertIsNone(error)

    def test_empty_description(self):
        """Test empty description is rejected."""
        is_valid, error = validate_description("")
        self.assertFalse(is_valid)
        self.assertIn("empty", error.lower())

    def test_too_short(self):
        """Test description that is too short."""
        is_valid, error = validate_description("Too short")
        self.assertFalse(is_valid)
        self.assertIn("10", error)

    def test_too_long(self):
        """Test description that is too long."""
        is_valid, error = validate_description("A" * 501)
        self.assertFalse(is_valid)
        self.assertIn("500", error)


class TestValidateVersion(unittest.TestCase):
    """Test version validation."""

    def test_valid_versions(self):
        """Test valid semantic versions."""
        valid_versions = [
            "0.0.0",
            "0.1.0",
            "1.0.0",
            "1.2.3",
            "10.20.30",
            "99.99.99",
        ]
        for version in valid_versions:
            is_valid, error = validate_version(version)
            self.assertTrue(is_valid, f"Version '{version}' should be valid, got error: {error}")
            self.assertIsNone(error)

    def test_invalid_versions(self):
        """Test invalid version formats."""
        invalid_versions = [
            "1",
            "1.0",
            "1.0.0.0",
            "v1.0.0",
            "1.0.0-beta",
            "1.0.a",
            "a.b.c",
            "",
        ]
        for version in invalid_versions:
            is_valid, error = validate_version(version)
            self.assertFalse(is_valid, f"Version '{version}' should be invalid")
            self.assertIsNotNone(error)


class TestBumpVersion(unittest.TestCase):
    """Test version bumping."""

    def test_bump_patch(self):
        """Test patch version bump."""
        self.assertEqual(bump_version("0.1.0", "patch"), "0.1.1")
        self.assertEqual(bump_version("1.2.3", "patch"), "1.2.4")
        self.assertEqual(bump_version("0.0.9", "patch"), "0.0.10")

    def test_bump_minor(self):
        """Test minor version bump."""
        self.assertEqual(bump_version("0.1.0", "minor"), "0.2.0")
        self.assertEqual(bump_version("1.2.3", "minor"), "1.3.0")
        self.assertEqual(bump_version("0.9.5", "minor"), "0.10.0")

    def test_bump_major(self):
        """Test major version bump."""
        self.assertEqual(bump_version("0.1.0", "major"), "1.0.0")
        self.assertEqual(bump_version("1.2.3", "major"), "2.0.0")
        self.assertEqual(bump_version("9.9.9", "major"), "10.0.0")


class TestInferFromDescription(unittest.TestCase):
    """Test metadata inference from description."""

    def test_basic_inference(self):
        """Test basic inference from description."""
        result = infer_from_description("Handles database migrations")
        self.assertEqual(result["name"], "handles-database-migrations")
        self.assertEqual(result["version"], "0.1.0")
        self.assertIn("custom", result["tags"])

    def test_tag_inference_database(self):
        """Test database tag inference."""
        result = infer_from_description("Handles SQL database queries")
        self.assertIn("database", result["tags"])

    def test_tag_inference_api(self):
        """Test API tag inference."""
        result = infer_from_description("REST API endpoint handler")
        self.assertIn("api", result["tags"])

    def test_tag_inference_testing(self):
        """Test testing tag inference."""
        result = infer_from_description("Unit test runner for coverage")
        self.assertIn("testing", result["tags"])

    def test_tag_inference_auth(self):
        """Test auth tag inference."""
        result = infer_from_description("Authentication and login handler")
        self.assertIn("auth", result["tags"])

    def test_name_truncation(self):
        """Test that long descriptions are truncated for name."""
        long_desc = "A" * 100
        result = infer_from_description(long_desc)
        self.assertLessEqual(len(result["name"]), 50)


class TestGetQuestions(unittest.TestCase):
    """Test question generation."""

    def test_create_without_description(self):
        """Test create operation without description asks for it."""
        context = {"operation": "create", "type": "agent"}
        result = get_questions(context)

        self.assertTrue(len(result["questions"]) > 0)
        question_ids = [q["id"] for q in result["questions"]]
        self.assertIn("description", question_ids)

    def test_create_with_description(self):
        """Test create operation with description infers metadata."""
        context = {
            "operation": "create",
            "type": "agent",
            "description": "Handles database migrations",
        }
        result = get_questions(context)

        self.assertIn("inferred", result)
        self.assertIn("name", result["inferred"])
        self.assertEqual(result["inferred"]["version"], "0.1.0")

    def test_validate_without_name(self):
        """Test validate operation without name asks for it."""
        context = {"operation": "validate", "type": "agent"}
        result = get_questions(context)

        question_ids = [q["id"] for q in result["questions"]]
        self.assertIn("name", question_ids)

    def test_validate_with_all_flag(self):
        """Test validate --all doesn't ask for name."""
        context = {"operation": "validate", "type": "agent", "all": True}
        result = get_questions(context)

        question_ids = [q["id"] for q in result["questions"]]
        self.assertNotIn("name", question_ids)

    def test_list_no_questions(self):
        """Test list operation doesn't need questions."""
        context = {"operation": "list", "type": "agent"}
        result = get_questions(context)

        self.assertEqual(len(result["questions"]), 0)


class TestExecute(unittest.TestCase):
    """Test operation execution."""

    def test_execute_list(self):
        """Test list operation execution."""
        context = {
            "operation": "list",
            "type": "agent",
            "location": "user",
        }
        result = execute(context, {})

        self.assertTrue(result["success"])
        self.assertIn("components", result)
        self.assertIn("count", result)

    def test_execute_create_invalid_name(self):
        """Test create with invalid name fails."""
        context = {
            "operation": "create",
            "type": "agent",
            "name": "Invalid Name!",
            "description": "Test agent for testing purposes",
        }
        result = execute(context, {})

        self.assertFalse(result["success"])
        self.assertIn("Invalid name", result["message"])

    def test_execute_create_invalid_description(self):
        """Test create with invalid description fails."""
        context = {
            "operation": "create",
            "type": "agent",
            "name": "valid-name",
            "description": "Short",  # Too short
        }
        result = execute(context, {})

        self.assertFalse(result["success"])
        self.assertIn("description", result["message"].lower())

    def test_execute_version_missing_name(self):
        """Test version operation without name fails."""
        context = {
            "operation": "version",
            "type": "agent",
            "bump": "patch",
        }
        result = execute(context, {})

        self.assertFalse(result["success"])
        self.assertIn("Name is required", result["message"])

    def test_execute_unknown_operation(self):
        """Test unknown operation fails."""
        context = {
            "operation": "unknown",
            "type": "agent",
        }
        result = execute(context, {})

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


class TestCreateComponent(unittest.TestCase):
    """Test component creation in temporary directory."""

    def setUp(self):
        """Set up temporary directory for tests."""
        import tempfile
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        self.original_cwd = Path.cwd()

    def tearDown(self):
        """Clean up temporary directory."""
        import os
        import shutil
        os.chdir(self.original_cwd)
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_create_agent(self):
        """Test creating an agent with filesystem operations."""
        import os
        from unittest.mock import patch

        # Change to temp directory
        os.chdir(self.temp_path)

        # Create .git to simulate project root
        (self.temp_path / ".git").mkdir()

        context = {
            "operation": "create",
            "type": "agent",
            "name": "test-agent",
            "description": "A test agent for testing purposes",
            "version": "0.1.0",
            "tags": ["test"],
            "location": "project",
        }

        # Mock get_project_root to return our temp directory
        with patch('operations.utils.get_project_root', return_value=self.temp_path):
            result = execute(context, {})

        # Verify success
        self.assertTrue(result["success"], f"Execute failed: {result.get('message', 'unknown error')}")

        # Verify the result contains expected info
        self.assertIn("path", result)
        self.assertIn("files_created", result)

        # Verify the path indicates the agent was created
        component_path = Path(result["path"])
        self.assertEqual(component_path.name, "test-agent.md")
        self.assertIn("test-agent", str(component_path))

        # Verify at least one file was created
        self.assertGreater(len(result["files_created"]), 0)


def run_tests():
    """Run all tests and return results."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestKebabCase))
    suite.addTests(loader.loadTestsFromTestCase(TestValidateName))
    suite.addTests(loader.loadTestsFromTestCase(TestValidateDescription))
    suite.addTests(loader.loadTestsFromTestCase(TestValidateVersion))
    suite.addTests(loader.loadTestsFromTestCase(TestBumpVersion))
    suite.addTests(loader.loadTestsFromTestCase(TestInferFromDescription))
    suite.addTests(loader.loadTestsFromTestCase(TestGetQuestions))
    suite.addTests(loader.loadTestsFromTestCase(TestExecute))
    suite.addTests(loader.loadTestsFromTestCase(TestSafeJsonLoad))
    suite.addTests(loader.loadTestsFromTestCase(TestCreateComponent))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result


if __name__ == "__main__":
    result = run_tests()
    sys.exit(0 if result.wasSuccessful() else 1)
