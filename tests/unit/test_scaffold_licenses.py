"""Unit tests for create-plugin license operations."""

import sys
import unittest
from pathlib import Path

# Add scripts directories to path
_project_root = Path(__file__).parent.parent.parent
_scaffold_scripts = _project_root / "skills" / "create-plugin" / "scripts"
sys.path.insert(0, str(_project_root / "scripts"))

# Import directly to avoid conflicts with ccm operations package
import importlib.util  # noqa: E402

_licenses_spec = importlib.util.spec_from_file_location(
    "scaffold_licenses",
    str(_scaffold_scripts / "operations" / "licenses.py"),
)
_licenses_mod = importlib.util.module_from_spec(_licenses_spec)
_licenses_spec.loader.exec_module(_licenses_mod)

get_license_text = _licenses_mod.get_license_text
LICENSES = _licenses_mod.LICENSES
SUPPORTED_LICENSES = _licenses_mod.SUPPORTED_LICENSES


class TestGetLicenseText(unittest.TestCase):
    """Test license text generation."""

    def test_mit_license(self):
        text = get_license_text("MIT", "2026", "Test Author")
        self.assertIn("MIT License", text)
        self.assertIn("2026", text)
        self.assertIn("Test Author", text)

    def test_apache_license(self):
        text = get_license_text("Apache-2.0", "2026", "Test Author")
        self.assertIn("Apache License", text)
        self.assertIn("2026", text)
        self.assertIn("Test Author", text)

    def test_isc_license(self):
        text = get_license_text("ISC", "2026", "Test Author")
        self.assertIn("ISC License", text)
        self.assertIn("2026", text)
        self.assertIn("Test Author", text)

    def test_gpl_license(self):
        text = get_license_text("GPL-3.0", "2026", "Test Author")
        self.assertIn("GNU GENERAL PUBLIC LICENSE", text)
        self.assertIn("2026", text)
        self.assertIn("Test Author", text)

    def test_agpl_license(self):
        text = get_license_text("AGPL-3.0", "2026", "Test Author")
        self.assertIn("GNU AFFERO GENERAL PUBLIC LICENSE", text)
        self.assertIn("2026", text)
        self.assertIn("Test Author", text)

    def test_unlicensed(self):
        text = get_license_text("UNLICENSED", "2026", "Test Author")
        self.assertIn("All rights reserved", text)
        self.assertIn("2026", text)
        self.assertIn("Test Author", text)

    def test_all_supported_licenses(self):
        """Every supported license should render without error."""
        for license_id in SUPPORTED_LICENSES:
            text = get_license_text(license_id, "2026", "Author")
            self.assertTrue(len(text) > 0, f"License {license_id} produced empty text")
            self.assertIn("2026", text)
            self.assertIn("Author", text)

    def test_year_author_substitution(self):
        """Year and author should be properly substituted."""
        text = get_license_text("MIT", "2099", "Jane Doe")
        self.assertIn("2099", text)
        self.assertIn("Jane Doe", text)
        self.assertNotIn("{year}", text)
        self.assertNotIn("{author_name}", text)

    def test_unknown_license_raises_value_error(self):
        """Unknown license IDs should raise ValueError."""
        with self.assertRaises(ValueError) as cm:
            get_license_text("UNKNOWN-LICENSE", "2026", "Author")
        self.assertIn("Unsupported license", str(cm.exception))
        self.assertIn("UNKNOWN-LICENSE", str(cm.exception))

    def test_supported_licenses_list(self):
        """SUPPORTED_LICENSES should match LICENSES dict keys."""
        self.assertEqual(set(SUPPORTED_LICENSES), set(LICENSES.keys()))

    def test_licenses_count(self):
        """Should have exactly 6 supported licenses."""
        self.assertEqual(len(SUPPORTED_LICENSES), 6)


if __name__ == "__main__":
    unittest.main()
