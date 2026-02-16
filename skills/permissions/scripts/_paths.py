"""Path utilities for permissions scripts."""

from __future__ import annotations

from pathlib import Path


def get_home_dir() -> Path:
    """Return the user's home directory."""
    return Path.home()
