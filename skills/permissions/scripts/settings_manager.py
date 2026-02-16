#!/usr/bin/env python3
"""Settings.json manager.

Reads and writes Claude Code permission settings across user,
project, and local scopes.
"""

from __future__ import annotations

import fcntl
import json
import logging
import os
import tempfile
from pathlib import Path

from _paths import get_home_dir

# Shared rule validation (same directory)
from rule_validation import validate_rules  # noqa: E402

logger = logging.getLogger(__name__)

MAX_SETTINGS_SIZE = 1024 * 1024  # 1MB

VALID_ACTIONS = ("allow", "ask", "deny")


def get_settings_path(scope: str) -> Path:
    """Resolve settings.json path for the given scope.

    Args:
        scope: One of ``user``, ``project``, or ``local``.

    Returns:
        Absolute path to the settings file.

    Raises:
        ValueError: If scope is not recognized.
    """
    if scope == "user":
        return get_home_dir() / ".claude" / "settings.json"
    if scope == "project":
        return Path.cwd() / ".claude" / "settings.json"
    if scope == "local":
        return Path.cwd() / ".claude" / "settings.local.json"
    msg = (
        f"Unknown scope {scope!r}. "
        "Expected 'user', 'project', or 'local'."
    )
    raise ValueError(msg)


def _read_settings_file(path: Path) -> dict:
    """Read and parse a settings.json file safely.

    Args:
        path: Path to the settings file.

    Returns:
        Parsed dict, or empty dict on error.
    """
    if not path.is_file():
        return {}
    try:
        # Check file size before reading to prevent memory exhaustion
        if path.stat().st_size > MAX_SETTINGS_SIZE:
            logger.warning("Settings file too large: %s", path)
            return {}
        with open(path, encoding="utf-8") as f:
            content = f.read()
        data = json.loads(content)
        if isinstance(data, dict):
            return data
        return {}
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to read settings %s: %s", path, exc)
        return {}


def read_all_settings() -> dict:
    """Read permissions from all settings scopes.

    Returns:
        Dict with ``user``, ``project``, and ``local`` keys,
        each containing the permissions section of the
        corresponding settings file (or empty dict).
    """
    result: dict[str, dict] = {}
    for scope in ("user", "project", "local"):
        path = get_settings_path(scope)
        data = _read_settings_file(path)
        permissions = {}
        for action in VALID_ACTIONS:
            if action in data:
                permissions[action] = data[action]
        result[scope] = permissions
    return result


def write_permissions(
    scope: str,
    rules: dict,
    merge_strategy: str = "merge",
) -> bool:
    """Write permissions to the correct settings.json.

    Args:
        scope: One of ``user``, ``project``, or ``local``.
        rules: Dict with ``allow``, ``ask``, and/or ``deny``
            keys, each mapping to a list of rule strings.
        merge_strategy: ``merge`` to add to existing rules, or
            ``replace`` to overwrite existing permissions.

    Returns:
        True on success, False on failure.

    Raises:
        ValueError: If rules contain invalid syntax.
    """
    for action in VALID_ACTIONS:
        action_rules = rules.get(action, [])
        if not isinstance(action_rules, list):
            msg = f"Rules for {action!r} must be a list"
            raise ValueError(msg)
        valid, error = validate_rules(action_rules)
        if not valid:
            raise ValueError(error)

    path = get_settings_path(scope)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Use advisory file locking to prevent concurrent writes
    lock_path = path.with_suffix(".lock")
    lock_fd = None
    try:
        lock_fd = os.open(
            str(lock_path), os.O_CREAT | os.O_WRONLY, 0o644
        )
        fcntl.flock(lock_fd, fcntl.LOCK_EX)

        # Read inside the lock to avoid TOCTOU races
        existing = _read_settings_file(path)

        if merge_strategy == "merge":
            for action in VALID_ACTIONS:
                new_rules = rules.get(action, [])
                if new_rules:
                    current = existing.get(action, [])
                    if not isinstance(current, list):
                        current = []
                    merged = sorted(set(current) | set(new_rules))
                    existing[action] = merged
        elif merge_strategy == "replace":
            for action in VALID_ACTIONS:
                if action in rules:
                    existing[action] = rules[action]
                elif action in existing:
                    del existing[action]
        else:
            msg = (
                f"Unknown merge_strategy {merge_strategy!r}. "
                "Expected 'merge' or 'replace'."
            )
            raise ValueError(msg)

        fd = None
        tmp_path = None
        try:
            fd, tmp_path = tempfile.mkstemp(
                dir=str(path.parent), suffix=".tmp"
            )
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                fd = None  # Prevent double-close
                json.dump(existing, f, indent=2)
                f.write("\n")
            Path(tmp_path).replace(path)
            tmp_path = None  # Prevent cleanup after success
        except OSError:
            return False
        finally:
            if fd is not None:
                os.close(fd)
            if tmp_path is not None:
                Path(tmp_path).unlink(missing_ok=True)
    except OSError:
        logger.warning(
            "Failed to acquire lock for %s", path, exc_info=True
        )
        return False
    finally:
        if lock_fd is not None:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            os.close(lock_fd)

    return True


if __name__ == "__main__":
    settings = read_all_settings()
    print(json.dumps(settings, indent=2))
