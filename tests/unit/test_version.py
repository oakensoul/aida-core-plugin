"""Unit tests for scripts/shared/version.py.

Comprehensive tests for VersionRange, satisfies(), and parse_version()
covering all operators, zero-major cases, whitespace handling, bare
versions, and error cases.
"""

import sys
from pathlib import Path

import pytest

# Add shared scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from shared.version import VersionRange, satisfies, parse_version


# ---------------------------------------------------------------------------
# parse_version
# ---------------------------------------------------------------------------
class TestParseVersion:
    """Tests for the parse_version() helper."""

    @pytest.mark.parametrize("version_str", [
        "0.0.1",
        "0.1.0",
        "1.0.0",
        "1.2.3",
        "10.20.30",
        "999.999.999",
    ])
    def test_valid_versions(self, version_str: str) -> None:
        v = parse_version(version_str)
        assert str(v) == version_str

    @pytest.mark.parametrize("version_str,reason", [
        ("", "empty string"),
        ("1.2", "two-part version"),
        ("1.2.3.4", "four-part version"),
        ("v1.2.3", "leading v"),
        ("abc", "non-numeric"),
        ("1.2.3-beta", "pre-release tag"),
        ("1.2.3+build", "build metadata"),
        ("1.2.3-rc.1", "pre-release with dot"),
        ("a" * 65, "exceeds max length"),
    ])
    def test_invalid_versions(self, version_str: str, reason: str) -> None:
        with pytest.raises(ValueError):
            parse_version(version_str)


# ---------------------------------------------------------------------------
# VersionRange — construction
# ---------------------------------------------------------------------------
class TestVersionRangeConstruction:
    """Tests for VersionRange constructor validation."""

    @pytest.mark.parametrize("bad_constraint", [
        "",
        "   ",
        None,
    ])
    def test_empty_or_none(self, bad_constraint) -> None:
        with pytest.raises((ValueError, TypeError)):
            VersionRange(bad_constraint)

    def test_too_long(self) -> None:
        with pytest.raises(ValueError, match="maximum length"):
            VersionRange("^" + "1" * 64)

    def test_invalid_chars(self) -> None:
        with pytest.raises(ValueError, match="invalid characters"):
            VersionRange("^1.2.3-beta")

    def test_repr_caret(self) -> None:
        r = VersionRange("^1.2.3")
        assert ">=1.2.3" in repr(r)
        assert "<2.0.0" in repr(r)

    def test_repr_exact(self) -> None:
        r = VersionRange("=1.2.3")
        assert "=1.2.3" in repr(r)

    def test_repr_gte(self) -> None:
        r = VersionRange(">=1.0.0")
        assert ">=1.0.0" in repr(r)


# ---------------------------------------------------------------------------
# satisfies — parametrized satisfaction matrix
# ---------------------------------------------------------------------------
class TestSatisfies:
    """Parametrized satisfaction tests covering all operators."""

    @pytest.mark.parametrize("version,constraint,expected", [
        # --- caret (major > 0) ---
        ("1.2.3", "^1.2.3", True),
        ("1.2.4", "^1.2.3", True),
        ("1.9.9", "^1.2.3", True),
        ("2.0.0", "^1.2.3", False),
        ("1.2.2", "^1.2.3", False),
        ("1.0.0", "^1.0.0", True),
        ("1.99.99", "^1.0.0", True),

        # --- caret zero-major (0.Y.Z where Y > 0) ---
        ("0.2.3", "^0.2.3", True),
        ("0.2.4", "^0.2.3", True),
        ("0.2.99", "^0.2.3", True),
        ("0.3.0", "^0.2.3", False),
        ("0.2.2", "^0.2.3", False),
        ("0.1.0", "^0.1.0", True),
        ("0.1.99", "^0.1.0", True),
        ("0.2.0", "^0.1.0", False),

        # --- caret zero-minor (0.0.Z) ---
        ("0.0.3", "^0.0.3", True),
        ("0.0.4", "^0.0.3", False),
        ("0.0.2", "^0.0.3", False),
        ("0.1.0", "^0.0.3", False),
        ("0.0.1", "^0.0.1", True),
        ("0.0.2", "^0.0.1", False),

        # --- tilde ---
        ("1.2.3", "~1.2.3", True),
        ("1.2.9", "~1.2.3", True),
        ("1.2.99", "~1.2.3", True),
        ("1.3.0", "~1.2.3", False),
        ("1.2.2", "~1.2.3", False),
        ("2.0.0", "~1.2.3", False),
        ("0.2.3", "~0.2.0", True),
        ("0.3.0", "~0.2.0", False),

        # --- greater-than-or-equal ---
        ("1.0.0", ">=1.0.0", True),
        ("1.0.1", ">=1.0.0", True),
        ("2.0.0", ">=1.0.0", True),
        ("99.99.99", ">=1.0.0", True),
        ("0.9.9", ">=1.0.0", False),

        # --- exact (= prefix) ---
        ("1.2.3", "=1.2.3", True),
        ("1.2.4", "=1.2.3", False),
        ("1.2.2", "=1.2.3", False),
        ("0.0.1", "=0.0.1", True),
        ("0.0.2", "=0.0.1", False),

        # --- bare version (exact match) ---
        ("1.2.3", "1.2.3", True),
        ("1.2.4", "1.2.3", False),
        ("1.2.2", "1.2.3", False),
        ("0.0.0", "0.0.0", True),
    ])
    def test_satisfaction(
        self, version: str, constraint: str, expected: bool
    ) -> None:
        assert satisfies(version, constraint) is expected, (
            f"satisfies({version!r}, {constraint!r}) should be {expected}"
        )


class TestSatisfiesWhitespace:
    """Whitespace handling in constraints."""

    @pytest.mark.parametrize("constraint", [
        " ^1.2.3",
        "^1.2.3 ",
        " ^1.2.3 ",
        "  ^1.2.3  ",
    ])
    def test_whitespace_stripped(self, constraint: str) -> None:
        assert satisfies("1.5.0", constraint) is True

    @pytest.mark.parametrize("constraint", [
        ">= 1.0.0",
        ">=  1.0.0",
        "= 1.2.3",
    ])
    def test_inner_whitespace(self, constraint: str) -> None:
        """Whitespace between operator and version is tolerated."""
        vr = VersionRange(constraint)
        assert vr.lower is not None


class TestSatisfiesErrors:
    """Error cases for satisfies()."""

    def test_invalid_version(self) -> None:
        with pytest.raises(ValueError):
            satisfies("not.a.version", "^1.0.0")

    def test_invalid_constraint(self) -> None:
        with pytest.raises(ValueError):
            satisfies("1.0.0", "invalid")

    def test_empty_version(self) -> None:
        with pytest.raises(ValueError):
            satisfies("", "^1.0.0")

    def test_empty_constraint(self) -> None:
        with pytest.raises(ValueError):
            satisfies("1.0.0", "")


# ---------------------------------------------------------------------------
# VersionRange.contains — direct usage
# ---------------------------------------------------------------------------
class TestVersionRangeContains:
    """Direct VersionRange.contains() tests."""

    def test_caret_boundary_inclusive_lower(self) -> None:
        vr = VersionRange("^1.0.0")
        assert vr.contains("1.0.0") is True

    def test_caret_boundary_exclusive_upper(self) -> None:
        vr = VersionRange("^1.0.0")
        assert vr.contains("2.0.0") is False

    def test_gte_no_upper_bound(self) -> None:
        vr = VersionRange(">=0.1.0")
        assert vr.contains("99.0.0") is True

    def test_exact_only_matches_exact(self) -> None:
        vr = VersionRange("=2.0.0")
        assert vr.contains("2.0.0") is True
        assert vr.contains("2.0.1") is False
        assert vr.contains("1.9.9") is False

    def test_tilde_upper_boundary(self) -> None:
        vr = VersionRange("~3.1.0")
        assert vr.contains("3.1.0") is True
        assert vr.contains("3.1.999") is True
        assert vr.contains("3.2.0") is False
