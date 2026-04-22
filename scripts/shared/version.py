"""Shared version range parsing and satisfaction checking.

Provides a thin wrapper around ``packaging.version.Version`` with support
for ``^``, ``~``, ``>=``, and ``=`` constraint operators.  Zero-major
special cases follow the npm/semver convention:

* ``^0.2.3`` → ``>=0.2.3 <0.3.0``
* ``^0.0.3`` → ``>=0.0.3 <0.0.4``
"""

import re
from typing import Optional, Tuple

from packaging.version import Version, InvalidVersion

MAX_CONSTRAINT_LENGTH = 64
VALID_CONSTRAINT_CHARS = re.compile(r'^[0-9.^~>=< ]+$')
STRICT_VERSION = re.compile(r'^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$')
PRERELEASE_VERSION = re.compile(r'^\d+\.\d+\.\d+[-+]')


def parse_version(version_str: str) -> Version:
    """Parse and validate a strict semver version string (X.Y.Z).

    Args:
        version_str: Version string to parse.

    Returns:
        A ``packaging.version.Version`` instance.

    Raises:
        ValueError: If the string is empty, too long, contains
            pre-release/build metadata, or is not strict X.Y.Z.
    """
    if not version_str:
        raise ValueError("Version string cannot be empty")

    if len(version_str) > MAX_CONSTRAINT_LENGTH:
        raise ValueError(
            f"Version string exceeds maximum length of "
            f"{MAX_CONSTRAINT_LENGTH} characters"
        )

    if PRERELEASE_VERSION.match(version_str):
        raise ValueError(
            f"Pre-release/build metadata not supported: "
            f"{version_str!r}"
        )

    if not STRICT_VERSION.match(version_str):
        raise ValueError(
            f"Version must be in strict semver format X.Y.Z: "
            f"{version_str!r}"
        )

    return Version(version_str)


class VersionRange:
    """Represents a version constraint with lower and optional upper bounds.

    Supported constraint formats:

    * ``^1.2.3`` -- caret (compatible with): ``>=1.2.3 <2.0.0``
    * ``^0.2.3`` -- zero-major caret: ``>=0.2.3 <0.3.0``
    * ``^0.0.3`` -- zero-minor caret: ``>=0.0.3 <0.0.4``
    * ``~1.2.3`` -- tilde (approximately): ``>=1.2.3 <1.3.0``
    * ``>=1.0.0`` -- greater-than-or-equal (no upper bound)
    * ``=1.2.3`` -- exact match
    * ``1.2.3`` -- bare version, treated as exact match
    """

    def __init__(self, constraint: str) -> None:
        if not constraint or not constraint.strip():
            raise ValueError("Constraint string cannot be empty")

        constraint = constraint.strip()

        if len(constraint) > MAX_CONSTRAINT_LENGTH:
            raise ValueError(
                f"Constraint string exceeds maximum length of "
                f"{MAX_CONSTRAINT_LENGTH} characters"
            )

        if not VALID_CONSTRAINT_CHARS.match(constraint):
            raise ValueError(
                f"Constraint contains invalid characters: "
                f"{constraint!r}"
            )

        self.constraint = constraint
        self.lower: Version
        self.upper: Optional[Version] = None
        self._parse(constraint)

    def _parse(self, constraint: str) -> None:
        """Expand the constraint string into lower/upper bounds."""
        if constraint.startswith('^'):
            version_str = constraint[1:].strip()
            v = parse_version(version_str)
            self.lower = v
            major, minor, patch = v.major, v.minor, v.micro
            if major != 0:
                self.upper = Version(f"{major + 1}.0.0")
            elif minor != 0:
                self.upper = Version(f"0.{minor + 1}.0")
            else:
                self.upper = Version(f"0.0.{patch + 1}")

        elif constraint.startswith('~'):
            version_str = constraint[1:].strip()
            v = parse_version(version_str)
            self.lower = v
            self.upper = Version(f"{v.major}.{v.minor + 1}.0")

        elif constraint.startswith('>='):
            version_str = constraint[2:].strip()
            v = parse_version(version_str)
            self.lower = v
            self.upper = None

        elif constraint.startswith('='):
            version_str = constraint[1:].strip()
            v = parse_version(version_str)
            self.lower = v
            self.upper = v  # exact: lower == upper

        else:
            # Bare version -- treat as exact match
            v = parse_version(constraint)
            self.lower = v
            self.upper = v

    def contains(self, version_str: str) -> bool:
        """Check whether *version_str* satisfies this range.

        Args:
            version_str: A strict semver version string.

        Returns:
            ``True`` if the version falls within the range.
        """
        v = parse_version(version_str)

        if v < self.lower:
            return False

        if self.upper is not None:
            if self.upper == self.lower:
                # Exact match
                return v == self.lower
            # Upper bound is exclusive
            if v >= self.upper:
                return False

        return True

    def __repr__(self) -> str:
        if self.upper is None:
            return f"VersionRange(>={self.lower})"
        if self.upper == self.lower:
            return f"VersionRange(={self.lower})"
        return f"VersionRange(>={self.lower}, <{self.upper})"


def satisfies(version: str, constraint: str) -> bool:
    """Convenience function: does *version* satisfy *constraint*?

    Args:
        version: A strict semver version string (X.Y.Z).
        constraint: A version constraint string.

    Returns:
        ``True`` if the version satisfies the constraint.
    """
    return VersionRange(constraint).contains(version)
