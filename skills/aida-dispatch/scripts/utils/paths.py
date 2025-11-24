"""Path resolution utilities for AIDA.

This module provides cross-platform path resolution for Claude Code and AIDA
directories, using pathlib for maximum compatibility.
"""

import os
from pathlib import Path
from typing import List, Optional, Union

from .errors import PathError


def get_home_dir() -> Path:
    """Get the user's home directory.

    Returns:
        Path to user's home directory

    Example:
        >>> get_home_dir()
        PosixPath('/Users/username')
    """
    return Path.home()


def get_claude_dir() -> Path:
    """Get the Claude Code configuration directory.

    Returns:
        Path to ~/.claude directory

    Example:
        >>> get_claude_dir()
        PosixPath('/Users/username/.claude')
    """
    return get_home_dir() / ".claude"


def get_aida_skills_dir() -> Path:
    """Get the AIDA skills directory.

    Returns:
        Path to ~/.claude/skills directory

    Example:
        >>> get_aida_skills_dir()
        PosixPath('/Users/username/.claude/skills')
    """
    return get_claude_dir() / "skills"


def get_aida_plugin_dirs() -> List[Path]:
    """Get all AIDA plugin directories.

    Searches for all directories matching ~/.claude/skills/aida-*

    Returns:
        List of paths to AIDA plugin directories

    Example:
        >>> get_aida_plugin_dirs()
        [PosixPath('/Users/username/.claude/skills/aida-core'),
         PosixPath('/Users/username/.claude/skills/aida-marketplace')]
    """
    skills_dir = get_aida_skills_dir()

    if not skills_dir.exists():
        return []

    # Find all directories starting with 'aida-'
    aida_dirs = [
        d for d in skills_dir.iterdir()
        if d.is_dir() and d.name.startswith("aida-")
    ]

    return sorted(aida_dirs)  # Sort for consistency


def ensure_directory(path: Path, permissions: int = 0o755) -> Path:
    """Create directory if it doesn't exist, with security validation.

    This function creates a directory and any necessary parent directories,
    with protection against symlink attacks and permission verification.

    Args:
        path: Directory path to create
        permissions: Unix-style permissions (default: 0o755)

    Returns:
        Path to the created/existing directory

    Raises:
        PathError: If directory creation fails, contains invalid characters,
                   is a symlink, or permissions cannot be set

    Security:
        - Validates against null bytes (path injection)
        - Rejects symlinks to prevent symlink attacks
        - Verifies permissions were actually applied

    Example:
        >>> ensure_directory(Path("~/.claude/skills"))
        PosixPath('/Users/username/.claude/skills')
    """
    # Expand user home directory if needed
    expanded_path = path.expanduser()

    # Security: Validate path doesn't contain null bytes
    if '\x00' in str(expanded_path):
        raise PathError(
            f"Invalid path contains null bytes: {path}",
            "Remove null bytes from the path."
        )

    try:
        # Security: Check for symlinks before creating
        if expanded_path.exists() and expanded_path.is_symlink():
            raise PathError(
                f"Cannot create directory: {expanded_path} is a symlink",
                "Remove the symlink or use a different path."
            )

        # Create directory and any missing parents
        expanded_path.mkdir(parents=True, exist_ok=True)

        # Set and verify permissions on Unix-like systems
        if os.name != 'nt':  # Not Windows
            # Set permissions
            expanded_path.chmod(permissions)

            # Security: Verify permissions were applied
            actual_perms = expanded_path.stat().st_mode & 0o777
            if actual_perms != permissions:
                raise PathError(
                    f"Failed to set directory permissions: {expanded_path}",
                    f"Expected {oct(permissions)}, got {oct(actual_perms)}. "
                    f"Check filesystem and parent directory permissions."
                )

        return expanded_path

    except PermissionError as e:
        raise PathError(
            f"Permission denied when creating directory: {expanded_path}",
            f"Check that you have write permissions to the parent directory.\n"
            f"You may need to run with elevated permissions or change ownership."
        ) from e

    except OSError as e:
        raise PathError(
            f"Failed to create directory: {expanded_path}",
            f"Error: {e}\n"
            f"Check that the path is valid and accessible."
        ) from e


def resolve_path(
    path: Union[str, Path],
    must_exist: bool = False,
    allowed_base: Optional[Path] = None
) -> Path:
    """Resolve a path with security validation.

    This function expands user home directories, converts to absolute paths,
    and optionally validates that the resolved path is within an allowed
    base directory to prevent path traversal attacks.

    Args:
        path: Path to resolve (string or Path object)
        must_exist: If True, raise error if path doesn't exist
        allowed_base: Optional base directory - resolved path must be under this

    Returns:
        Resolved absolute Path object

    Raises:
        PathError: If path contains invalid characters, doesn't exist when
                   required, or is outside allowed_base when provided

    Security:
        - Validates against null bytes (path injection)
        - Prevents path traversal when allowed_base is specified
        - Resolves symlinks to detect traversal attempts

    Example:
        >>> resolve_path("~/.claude")
        PosixPath('/Users/username/.claude')

        >>> # With security boundary
        >>> resolve_path("../etc/passwd", allowed_base=Path.home() / ".claude")
        PathError: Path traversal attempt detected
    """
    # Convert to Path if string
    path_obj = Path(path) if isinstance(path, str) else path

    # Security: Check for null bytes (path injection attack)
    if '\x00' in str(path_obj):
        raise PathError(
            f"Invalid path contains null bytes: {path}",
            "Remove null bytes from the path."
        )

    # Expand user home and make absolute
    resolved = path_obj.expanduser().resolve()

    # Security: Validate against allowed base if provided
    if allowed_base is not None:
        allowed_resolved = allowed_base.expanduser().resolve()
        try:
            # This will raise ValueError if resolved is not under allowed_base
            resolved.relative_to(allowed_resolved)
        except ValueError:
            raise PathError(
                f"Path traversal attempt detected: {path}",
                f"Path must be under {allowed_base}"
            )

    if must_exist and not resolved.exists():
        raise PathError(
            f"Path does not exist: {resolved}",
            f"Verify the path is correct and accessible."
        )

    return resolved


def is_subdirectory(child: Path, parent: Path) -> bool:
    """Check if child is a subdirectory of parent.

    Args:
        child: Potential child directory
        parent: Potential parent directory

    Returns:
        True if child is under parent, False otherwise

    Example:
        >>> is_subdirectory(Path("~/.claude/skills"), Path("~/.claude"))
        True
    """
    try:
        child_resolved = resolve_path(child)
        parent_resolved = resolve_path(parent)
        child_resolved.relative_to(parent_resolved)
        return True
    except (ValueError, PathError):
        return False


def get_relative_path(path: Path, base: Path) -> Optional[Path]:
    """Get relative path from base to path.

    Args:
        path: Target path
        base: Base path to calculate relative from

    Returns:
        Relative path, or None if not possible

    Example:
        >>> get_relative_path(Path("~/.claude/skills"), Path("~/.claude"))
        PosixPath('skills')
    """
    try:
        path_resolved = resolve_path(path)
        base_resolved = resolve_path(base)
        return path_resolved.relative_to(base_resolved)
    except (ValueError, PathError):
        return None
