"""Shared parsing utilities for the update operation.

Extracted from scanner.py and patcher.py to eliminate
duplication. Both modules import these functions for
gitignore and Makefile comparison/merge logic.
"""

from __future__ import annotations

import re


_MAKEFILE_TARGET_RE = re.compile(
    r"^[a-zA-Z_][a-zA-Z0-9_-]*:"
)


def parse_gitignore_entries(content: str) -> set[str]:
    """Extract meaningful entries from gitignore content.

    Strips comments, blank lines, and leading/trailing
    whitespace to produce a set of active ignore patterns.

    Args:
        content: Raw .gitignore text

    Returns:
        Set of non-empty, non-comment lines
    """
    entries: set[str] = set()
    for line in content.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            entries.add(stripped)
    return entries


def extract_makefile_targets(
    content: str,
) -> set[str]:
    """Extract target names from Makefile content.

    Matches lines that look like Makefile targets
    (``name:`` at the start of a line).

    Args:
        content: Raw Makefile text

    Returns:
        Set of target name strings (without the colon)
    """
    targets: set[str] = set()
    for line in content.splitlines():
        match = _MAKEFILE_TARGET_RE.match(line)
        if match:
            target = match.group(0).rstrip(":")
            targets.add(target)
    return targets
