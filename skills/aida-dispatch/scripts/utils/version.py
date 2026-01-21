"""Python version checking utilities for AIDA.

This module provides functions to verify that the Python version meets
AIDA's requirements (Python 3.8+).
"""

import sys
from typing import Tuple

from .errors import VersionError


# Minimum required Python version
MIN_PYTHON_VERSION = (3, 8)


def get_python_version() -> Tuple[int, int, int]:
    """Get the current Python version as a tuple.

    Returns:
        Tuple of (major, minor, micro) version numbers

    Example:
        >>> get_python_version()
        (3, 11, 5)
    """
    return sys.version_info[:3]


def format_version(version: Tuple[int, ...]) -> str:
    """Format a version tuple as a string.

    Args:
        version: Version tuple (e.g., (3, 8, 0))

    Returns:
        Formatted version string (e.g., "3.8.0")

    Example:
        >>> format_version((3, 8, 0))
        '3.8.0'
    """
    return ".".join(str(v) for v in version)


def check_python_version(min_version: Tuple[int, int] = MIN_PYTHON_VERSION) -> None:
    """Verify that the Python version meets minimum requirements.

    Args:
        min_version: Minimum required Python version (major, minor)

    Raises:
        VersionError: If Python version is too old

    Example:
        >>> check_python_version()  # Raises VersionError if Python < 3.8
    """
    current_version = sys.version_info[:2]

    if current_version < min_version:
        current_full = get_python_version()
        min_full = min_version + (0,)  # Add micro version for display

        error_message = (
            f"Python {format_version(min_full)} or higher is required.\n"
            f"Current version: Python {format_version(current_full)}"
        )

        suggestion = (
            f"Please upgrade Python to version {format_version(min_full)} or higher.\n"
            f"Visit https://www.python.org/downloads/ for installation instructions."
        )

        raise VersionError(error_message, suggestion)


def is_compatible_version(min_version: Tuple[int, int] = MIN_PYTHON_VERSION) -> bool:
    """Check if the Python version is compatible (non-raising version).

    Args:
        min_version: Minimum required Python version (major, minor)

    Returns:
        True if version is compatible, False otherwise

    Example:
        >>> is_compatible_version((3, 8))
        True
    """
    current_version = sys.version_info[:2]
    return current_version >= min_version
