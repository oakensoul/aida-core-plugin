"""Unit tests for scripts/shared/utils.py.

Verifies that shared utils are importable and that the extraction
from operations/utils.py didn't break any functionality.
"""

import sys
import json
import unittest
from pathlib import Path

# Add shared scripts to path
_project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_project_root / "scripts"))

from shared.utils import (  # noqa: E402
    safe_json_load,
    to_kebab_case,
    validate_name,
    validate_description,
    validate_version,
    bump_version,
    parse_frontmatter,
    render_template,
    get_project_root,
    LOCATION_PATHS,
    get_location_path,
)


class TestSharedImports(unittest.TestCase):
    """Verify all shared functions are importable."""

    def test_all_functions_importable(self):
        """All expected functions should be importable from shared.utils."""
        self.assertTrue(callable(safe_json_load))
        self.assertTrue(callable(to_kebab_case))
        self.assertTrue(callable(validate_name))
        self.assertTrue(callable(validate_description))
        self.assertTrue(callable(validate_version))
        self.assertTrue(callable(bump_version))
        self.assertTrue(callable(parse_frontmatter))
        self.assertTrue(callable(render_template))
        self.assertTrue(callable(get_project_root))
        self.assertTrue(callable(get_location_path))
        self.assertIsInstance(LOCATION_PATHS, dict)


class TestSharedKebabCase(unittest.TestCase):
    """Test kebab-case conversion from shared utils."""

    def test_basic_conversion(self):
        self.assertEqual(to_kebab_case("Hello World"), "hello-world")
        self.assertEqual(to_kebab_case("Database Migration"), "database-migration")

    def test_with_special_characters(self):
        self.assertEqual(to_kebab_case("Hello! World?"), "hello-world")

    def test_with_underscores(self):
        self.assertEqual(to_kebab_case("hello_world"), "hello-world")

    def test_empty_string(self):
        self.assertEqual(to_kebab_case(""), "")


class TestSharedValidateName(unittest.TestCase):
    """Test name validation from shared utils."""

    def test_valid_name(self):
        is_valid, error = validate_name("my-plugin")
        self.assertTrue(is_valid)
        self.assertIsNone(error)

    def test_empty_name(self):
        is_valid, error = validate_name("")
        self.assertFalse(is_valid)

    def test_too_short(self):
        is_valid, error = validate_name("a")
        self.assertFalse(is_valid)

    def test_too_long(self):
        is_valid, error = validate_name("a" * 51)
        self.assertFalse(is_valid)

    def test_invalid_characters(self):
        is_valid, error = validate_name("MyPlugin")
        self.assertFalse(is_valid)


class TestSharedValidateDescription(unittest.TestCase):
    """Test description validation from shared utils."""

    def test_valid_description(self):
        is_valid, error = validate_description("A valid description for testing")
        self.assertTrue(is_valid)
        self.assertIsNone(error)

    def test_empty_description(self):
        is_valid, error = validate_description("")
        self.assertFalse(is_valid)

    def test_too_short(self):
        is_valid, error = validate_description("Short")
        self.assertFalse(is_valid)


class TestSharedValidateVersion(unittest.TestCase):
    """Test version validation from shared utils."""

    def test_valid_version(self):
        is_valid, error = validate_version("0.1.0")
        self.assertTrue(is_valid)
        self.assertIsNone(error)

    def test_invalid_version(self):
        is_valid, error = validate_version("invalid")
        self.assertFalse(is_valid)


class TestSharedBumpVersion(unittest.TestCase):
    """Test version bumping from shared utils."""

    def test_bump_patch(self):
        self.assertEqual(bump_version("0.1.0", "patch"), "0.1.1")

    def test_bump_minor(self):
        self.assertEqual(bump_version("0.1.0", "minor"), "0.2.0")

    def test_bump_major(self):
        self.assertEqual(bump_version("0.1.0", "major"), "1.0.0")


class TestSharedSafeJsonLoad(unittest.TestCase):
    """Test safe JSON loading from shared utils."""

    def test_valid_json(self):
        result = safe_json_load('{"key": "value"}')
        self.assertEqual(result, {"key": "value"})

    def test_empty_string(self):
        result = safe_json_load("")
        self.assertEqual(result, {})

    def test_none_input(self):
        result = safe_json_load(None)
        self.assertEqual(result, {})

    def test_invalid_json(self):
        with self.assertRaises(ValueError):
            safe_json_load("{invalid}")

    def test_size_limit(self):
        large_json = json.dumps({"data": "x" * (100 * 1024 + 1)})
        with self.assertRaises(ValueError):
            safe_json_load(large_json)


class TestSharedParseFrontmatter(unittest.TestCase):
    """Test frontmatter parsing from shared utils."""

    def test_with_frontmatter(self):
        content = "---\ntype: skill\nname: test\n---\n\nBody text"
        fm, body = parse_frontmatter(content)
        self.assertEqual(fm["type"], "skill")
        self.assertEqual(fm["name"], "test")
        self.assertEqual(body, "Body text")

    def test_without_frontmatter(self):
        content = "Just body text"
        fm, body = parse_frontmatter(content)
        self.assertEqual(fm, {})
        self.assertEqual(body, "Just body text")


if __name__ == "__main__":
    unittest.main()
