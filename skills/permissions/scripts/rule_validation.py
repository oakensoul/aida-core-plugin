#!/usr/bin/env python3
"""Shared permission rule validation.

Centralizes rule syntax validation used by both scanner.py
(at scan time) and settings_manager.py (at write time).
"""

from __future__ import annotations

import re

# Only allow safe ASCII characters inside rule patterns.
# This prevents Unicode homoglyph confusion and shell
# metacharacter injection.
RULE_PATTERN = re.compile(
    r"^[A-Za-z]\w*\([A-Za-z0-9_.*:/ -]+\)$"
)

MAX_RULE_LENGTH = 500


def validate_rule(rule: str) -> tuple[bool, str | None]:
    """Validate a single permission rule string.

    Args:
        rule: Permission rule string to validate.

    Returns:
        Tuple of (is_valid, error_message).
    """
    if not isinstance(rule, str):
        return False, f"Rule must be a string, got {type(rule)}"
    if len(rule) > MAX_RULE_LENGTH:
        return False, (
            f"Rule too long ({len(rule)} chars, "
            f"max {MAX_RULE_LENGTH}): {rule[:50]!r}..."
        )
    if not rule.isascii():
        return False, (
            f"Rule contains non-ASCII characters: {rule[:50]!r}. "
            "Only ASCII characters are allowed in permission rules"
        )
    if not RULE_PATTERN.match(rule):
        return False, (
            f"Invalid rule syntax: {rule!r}. "
            "Expected format: Tool(command:args) "
            "with alphanumeric chars, spaces, "
            "dots, stars, colons, slashes, and dashes. "
            "Examples: 'Bash(git commit:*)' or 'Read(src/*.py)'"
        )
    return True, None


def validate_rules(rules: list[str]) -> tuple[bool, str | None]:
    """Validate a list of permission rule strings.

    Args:
        rules: List of permission rule strings to validate.

    Returns:
        Tuple of (is_valid, error_message).
    """
    for rule in rules:
        valid, error = validate_rule(rule)
        if not valid:
            return False, error
    return True, None
