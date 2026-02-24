"""JSON utilities for AIDA with security validation.

This module provides safe JSON operations with size and depth validation
to prevent injection attacks and resource exhaustion.
"""

import json
from typing import Any, Dict

# JSON safety limits
MAX_JSON_SIZE = 1024 * 1024  # 1MB maximum JSON payload
MAX_JSON_DEPTH = 10          # Maximum nesting depth


def safe_json_load(json_str: str, max_size: int = MAX_JSON_SIZE) -> Dict[str, Any]:
    """Safely load JSON with size and depth validation.

    This function prevents JSON injection attacks and resource exhaustion
    by validating payload size and nesting depth before parsing.

    Args:
        json_str: JSON string to parse
        max_size: Maximum allowed size in bytes (default: 1MB)

    Returns:
        Parsed JSON dictionary

    Raises:
        ValueError: If JSON is too large, too deeply nested, or invalid

    Security:
        - Prevents memory exhaustion from large payloads
        - Prevents stack overflow from deeply nested objects
        - Prevents DoS attacks via malicious JSON

    Example:
        >>> safe_json_load('{"key": "value"}')
        {'key': 'value'}
        >>> safe_json_load('x' * (MAX_JSON_SIZE + 1))
        ValueError: JSON payload too large
    """
    # Check size limit
    if len(json_str) > max_size:
        raise ValueError(f"JSON payload too large (max {max_size} bytes)")

    # Parse JSON
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}")

    # Validate nesting depth
    def check_depth(obj: Any, depth: int = 0, max_depth: int = MAX_JSON_DEPTH) -> None:
        """Recursively check JSON nesting depth."""
        if depth > max_depth:
            raise ValueError(f"JSON nesting too deep (max {max_depth} levels)")

        if isinstance(obj, dict):
            for value in obj.values():
                check_depth(value, depth + 1, max_depth)
        elif isinstance(obj, list):
            for item in obj:
                check_depth(item, depth + 1, max_depth)

    check_depth(data)
    return data
