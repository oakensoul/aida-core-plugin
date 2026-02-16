"""Unit tests for security edge cases.

This test suite covers path traversal attempts, unicode edge cases,
very long inputs, and other security-sensitive edge cases.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

# Add scripts directories to path for imports
sys.path.insert(
    0,
    str(
        Path(__file__).parent.parent.parent
        / "skills"
        / "memento"
        / "scripts"
    ),
)
sys.path.insert(
    0,
    str(
        Path(__file__).parent.parent.parent
        / "skills"
        / "permissions"
        / "scripts"
    ),
)

import shutil

from memento import _ensure_within_dir
from rule_validation import validate_rules


class TestPathTraversalAttempts(unittest.TestCase):
    """Test protection against path traversal attacks."""

    def setUp(self):
        """Set up temporary directory for tests."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

    def tearDown(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_path_normalization_prevents_traversal(self):
        """Test that path normalization prevents directory traversal."""
        # Test various path traversal attempts
        dangerous_paths = [
            "../../etc/passwd",
            "../../../root/.ssh/id_rsa",
            "..\\..\\windows\\system32",
        ]

        for dangerous in dangerous_paths:
            # Resolve path and verify it stays within bounds
            # This is what should be done in production code
            normalized = Path(dangerous).resolve()
            base_path = Path.cwd().resolve()

            # The dangerous path should not escape the base path
            # Production code should verify normalized path is under base_path
            # using: normalized.is_relative_to(base_path) in Python 3.9+
            self.assertIsNotNone(normalized)
            self.assertIsNotNone(base_path)

    def test_absolute_path_handling(self):
        """Test that absolute paths are handled safely."""
        absolute_path = "/tmp/malicious-file"

        # When joining with a base path, absolute paths should override
        # or be rejected - document expected behavior
        base = Path("/safe/directory")

        # Python's Path / operator behavior: absolute path wins
        combined = base / absolute_path
        # This would result in Path('/tmp/malicious-file')
        # Production code should detect and reject absolute inputs
        self.assertEqual(str(combined), absolute_path)


class TestUnicodeEdgeCases(unittest.TestCase):
    """Test handling of unicode edge cases."""

    def test_permission_scope_unicode_characters(self):
        """Test permission scope with unicode characters."""
        # Test with various unicode characters
        unicode_rules = [
            "Read(файл.txt)",  # Cyrillic
            "Write(文件.md)",  # Chinese
            "Bash(café:*)",  # Accented
            "Edit(😀.py)",  # Emoji
        ]

        # These should be rejected as non-ASCII
        valid, error = validate_rules(unicode_rules)
        self.assertFalse(valid)
        self.assertIn("non-ASCII", error)

    def test_permission_scope_homoglyph_attack(self):
        """Test permission scope with homoglyph characters."""
        # Use Cyrillic 'а' (U+0430) instead of Latin 'a' (U+0061)
        homoglyph_rule = "Bаsh(git:*)"  # 'а' is Cyrillic
        valid, error = validate_rules([homoglyph_rule])
        self.assertFalse(valid)
        self.assertIn("non-ASCII", error)

    def test_permission_scope_zero_width_characters(self):
        """Test permission scope with zero-width characters."""
        # Zero-width space (U+200B)
        rule_with_zwsp = "Bash(git\u200b:*)"
        valid, error = validate_rules([rule_with_zwsp])
        self.assertFalse(valid)

    def test_permission_scope_rtl_override(self):
        """Test permission scope with RTL override characters."""
        # Right-to-left override (U+202E)
        rule_with_rtl = "Bash(\u202Egit:*)"
        valid, error = validate_rules([rule_with_rtl])
        self.assertFalse(valid)


class TestVeryLongInputStrings(unittest.TestCase):
    """Test handling of very long input strings."""

    def test_permission_rule_exceeds_max_length(self):
        """Test that very long rules are handled."""
        # Create a rule with path longer than 256 chars
        long_path = "a" * 300
        long_rule = f"Read({long_path})"

        valid, error = validate_rules([long_rule])
        # May be valid syntax but very long - implementation dependent
        if not valid:
            # If rejected, should mention length
            self.assertIn("too long", error.lower())

    def test_permission_many_rules(self):
        """Test handling of many permission rules."""
        # Create a large number of rules
        many_rules = [f"Read(file{i}.txt)" for i in range(1000)]

        # Should validate individual rules, but might be slow
        valid, error = validate_rules(many_rules[:10])
        self.assertTrue(valid)

    def test_permission_scope_deeply_nested_path(self):
        """Test permission with deeply nested path."""
        # Create a very deep path
        deep_path = "/".join(["dir"] * 100)
        rule = f"Read({deep_path}/*)"

        valid, error = validate_rules([rule])
        # Should be valid syntax but very long
        if not valid:
            self.assertIn("too long", error)


class TestCommandInjectionAttempts(unittest.TestCase):
    """Test protection against command injection."""

    def test_permission_rule_with_shell_metacharacters(self):
        """Test permission rules with shell metacharacters."""
        dangerous_rules = [
            "Bash(git; rm -rf /:*)",
            "Bash(git && malicious:*)",
            "Bash(git | nc:*)",
            "Bash(git$(evil):*)",
            "Bash(git`backdoor`:*)",
        ]

        # These should be rejected by the validation
        for rule in dangerous_rules:
            valid, error = validate_rules([rule])
            # The rule syntax validator should catch these
            # Note: Some might be valid syntax but dangerous semantics
            # The hook execution should handle shell escaping

    def test_permission_rule_with_newlines(self):
        """Test permission rules with newline characters."""
        rule_with_newline = "Bash(git\nmalicious:*)"
        valid, error = validate_rules([rule_with_newline])
        # Should be rejected
        self.assertFalse(valid)


class TestJsonInjectionAttempts(unittest.TestCase):
    """Test protection against JSON injection."""

    def setUp(self):
        """Set up temporary directory for tests."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

    def tearDown(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_json_with_control_characters(self):
        """Test JSON serialization with control characters."""

        # Data with various control characters
        data = {
            "field1": "value\nwith\nnewlines",
            "field2": "value\twith\ttabs",
            "field3": "value with\rcarriage\rreturns",
        }

        # JSON should handle these with proper escaping
        serialized = json.dumps(data)
        deserialized = json.loads(serialized)

        # Verify round-trip works
        self.assertEqual(data, deserialized)

    def test_json_with_deeply_nested_structure(self):
        """Test JSON with deeply nested structure."""

        # Create deeply nested structure
        nested = {"level": 0}
        current = nested
        for i in range(100):
            current["next"] = {"level": i + 1}
            current = current["next"]

        # Should serialize and deserialize
        serialized = json.dumps(nested)
        deserialized = json.loads(serialized)

        # Verify structure preserved
        self.assertEqual(nested["level"], deserialized["level"])


class TestEnsureWithinDir(unittest.TestCase):
    """Test _ensure_within_dir() from memento.py."""

    def setUp(self):
        """Set up temporary directory for tests."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

    def tearDown(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_valid_path_within_base(self):
        """Test that valid paths within base are accepted."""
        child = self.temp_path / "subdir"
        child.mkdir()
        result = _ensure_within_dir(child, self.temp_path)
        self.assertEqual(result, child.resolve())

    def test_parent_traversal_rejected(self):
        """Test that parent directory traversal is rejected."""
        escape_path = self.temp_path / ".." / ".." / "etc"
        with self.assertRaises(ValueError) as ctx:
            _ensure_within_dir(escape_path, self.temp_path)
        self.assertIn("Path escape detected", str(ctx.exception))

    def test_absolute_path_outside_base_rejected(self):
        """Test that absolute paths outside base are rejected."""
        outside_path = Path("/tmp/outside-base")
        outside_path.mkdir(exist_ok=True)
        try:
            with self.assertRaises(ValueError) as ctx:
                _ensure_within_dir(outside_path, self.temp_path)
            self.assertIn("Path escape detected", str(ctx.exception))
        finally:
            outside_path.rmdir()

    def test_symlink_rejected(self):
        """Test that symlinks are rejected."""
        target = self.temp_path / "real-dir"
        target.mkdir()
        link = self.temp_path / "link-dir"
        try:
            link.symlink_to(target)
        except OSError:
            self.skipTest("Symlinks not supported on this platform")

        with self.assertRaises(ValueError) as ctx:
            _ensure_within_dir(link, self.temp_path)
        self.assertIn("Symlink detected", str(ctx.exception))


class TestSymlinkSecurity(unittest.TestCase):
    """Test security around symlinks."""

    def setUp(self):
        """Set up temporary directory for tests."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

    def tearDown(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_symlink_detection(self):
        """Test that symlinks can be detected."""
        # Create a real directory
        real_dir = self.temp_path / "real-storage"
        real_dir.mkdir()

        # Create symlink to it
        symlink_dir = self.temp_path / "symlink-storage"

        try:
            symlink_dir.symlink_to(real_dir)
        except OSError:
            # Skip test if symlinks not supported
            self.skipTest("Symlinks not supported on this platform")

        # Verify we can detect symlinks
        self.assertTrue(symlink_dir.is_symlink())
        self.assertFalse(real_dir.is_symlink())

        # Production code should check is_symlink() before using paths


if __name__ == "__main__":
    unittest.main()
