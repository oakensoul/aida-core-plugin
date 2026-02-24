"""Plugin patcher for the update operation.

Applies approved patches to a plugin directory with backup
creation and atomic file writes.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..constants import GENERATOR_VERSION
from .models import (
    DiffReport,
    FileDiff,
    FileStatus,
    MergeStrategy,
    PatchResult,
)
from .parsers import extract_makefile_targets, parse_gitignore_entries

logger = logging.getLogger(__name__)

_AIDA_UPDATE_HEADER = "# Added by aida plugin update"


def apply_patches(
    plugin_path: Path,
    diff_report: DiffReport,
    overrides: dict[str, MergeStrategy] | None = None,
) -> list[PatchResult]:
    """Apply patches to a plugin directory.

    Processes every file in the diff report that needs action,
    creates a backup before modifications, applies the
    appropriate merge strategy, and updates the generator
    version.

    Args:
        plugin_path: Absolute path to the plugin directory
        diff_report: Scan results from the scanner module
        overrides: Optional mapping of file paths to
            strategies that override the defaults

    Returns:
        List of PatchResult for every file processed
    """
    if overrides is None:
        overrides = {}

    actionable = [
        f
        for f in diff_report.files
        if f.status in (FileStatus.MISSING, FileStatus.OUTDATED)
    ]

    if not actionable:
        logger.info("No files need patching")
        return [
            _update_generator_version(plugin_path),
        ]

    backup_path = _create_backup(plugin_path, actionable)

    results: list[PatchResult] = []
    for file_diff in actionable:
        strategy = overrides.get(
            file_diff.path, file_diff.strategy
        )
        try:
            result = _apply_strategy(
                plugin_path, file_diff, strategy, backup_path
            )
            results.append(result)
        except Exception:
            logger.error(
                "Failed to patch %s",
                file_diff.path,
                exc_info=True,
            )
            results.append(
                PatchResult(
                    path=file_diff.path,
                    action="failed",
                    message="Unexpected error during patching",
                )
            )

    results.append(_update_generator_version(plugin_path))
    return results


def _create_backup(
    plugin_path: Path,
    actionable: list[FileDiff],
) -> Path:
    """Create a backup of files that will be modified.

    Only backs up files that exist on disk; missing files
    are skipped since there is nothing to preserve.

    Args:
        plugin_path: Absolute path to the plugin directory
        actionable: Files that will be patched

    Returns:
        Path to the backup directory
    """
    timestamp = datetime.now(timezone.utc).strftime(
        "%Y%m%d_%H%M%S"
    )
    backup_path = (
        plugin_path / ".aida-backup" / timestamp
    )
    backup_path.mkdir(parents=True, exist_ok=True)

    for file_diff in actionable:
        source = plugin_path / file_diff.path
        if source.exists():
            dest = backup_path / file_diff.path
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(source), str(dest))
            logger.debug("Backed up %s", file_diff.path)

    logger.info("Backup created at %s", backup_path)
    return backup_path


def _apply_strategy(
    plugin_path: Path,
    file_diff: FileDiff,
    strategy: MergeStrategy,
    backup_path: Path,
) -> PatchResult:
    """Route a file to the appropriate strategy handler.

    Args:
        plugin_path: Absolute path to the plugin directory
        file_diff: Comparison data for the file
        strategy: Merge strategy to apply
        backup_path: Path to the backup directory

    Returns:
        PatchResult describing what was done
    """
    if strategy == MergeStrategy.SKIP:
        return _apply_skip(file_diff)
    if strategy == MergeStrategy.OVERWRITE:
        return _apply_overwrite(
            plugin_path, file_diff, backup_path
        )
    if strategy == MergeStrategy.ADD:
        return _apply_add(plugin_path, file_diff)
    if strategy == MergeStrategy.MERGE:
        return _apply_merge(
            plugin_path, file_diff, backup_path
        )
    if strategy == MergeStrategy.MANUAL_REVIEW:
        return _apply_manual_review(file_diff)

    logger.warning(
        "Unknown strategy %s for %s, skipping",
        strategy,
        file_diff.path,
    )
    return PatchResult(
        path=file_diff.path,
        action="skipped",
        message=f"Unknown strategy: {strategy.value}",
    )


def _apply_skip(file_diff: FileDiff) -> PatchResult:
    """Handle a file with SKIP strategy.

    Args:
        file_diff: Comparison data for the file

    Returns:
        PatchResult with action skipped
    """
    return PatchResult(
        path=file_diff.path,
        action="skipped",
        message=(
            "Skipped: file is managed by the plugin author"
        ),
    )


def _apply_overwrite(
    plugin_path: Path,
    file_diff: FileDiff,
    backup_path: Path,
) -> PatchResult:
    """Overwrite a file with expected content.

    Args:
        plugin_path: Absolute path to the plugin directory
        file_diff: Comparison data with expected_content
        backup_path: Path to the backup directory

    Returns:
        PatchResult with action updated
    """
    target = plugin_path / file_diff.path
    content = file_diff.expected_content or ""

    _atomic_write(target, content)

    backup_file = backup_path / file_diff.path
    backup_ref = (
        str(backup_file) if backup_file.exists() else ""
    )

    return PatchResult(
        path=file_diff.path,
        action="updated",
        message="Overwritten with current standard",
        backup_path=backup_ref,
    )


def _apply_add(
    plugin_path: Path,
    file_diff: FileDiff,
) -> PatchResult:
    """Add a file only if it does not already exist.

    Args:
        plugin_path: Absolute path to the plugin directory
        file_diff: Comparison data with expected_content

    Returns:
        PatchResult with action created or skipped
    """
    target = plugin_path / file_diff.path

    if target.exists():
        return PatchResult(
            path=file_diff.path,
            action="skipped",
            message="File already exists",
        )

    content = file_diff.expected_content or ""
    _atomic_write(target, content)

    return PatchResult(
        path=file_diff.path,
        action="created",
        message="Created from current standard",
    )


def _apply_merge(
    plugin_path: Path,
    file_diff: FileDiff,
    backup_path: Path,
) -> PatchResult:
    """Route merge to the file-specific handler.

    Args:
        plugin_path: Absolute path to the plugin directory
        file_diff: Comparison data for the file
        backup_path: Path to the backup directory

    Returns:
        PatchResult from the appropriate merge handler
    """
    if file_diff.path == ".gitignore":
        return _merge_gitignore(
            plugin_path, file_diff, backup_path
        )
    if file_diff.path == "Makefile":
        return _merge_makefile(
            plugin_path, file_diff, backup_path
        )

    logger.warning(
        "No merge handler for %s, falling back to "
        "overwrite",
        file_diff.path,
    )
    return _apply_overwrite(
        plugin_path, file_diff, backup_path
    )


def _merge_gitignore(
    plugin_path: Path,
    file_diff: FileDiff,
    backup_path: Path,
) -> PatchResult:
    """Append-only merge for .gitignore files.

    Parses both current and expected content into sets of
    active entries, then appends any missing entries under
    a clearly marked comment header.

    Args:
        plugin_path: Absolute path to the plugin directory
        file_diff: Comparison data for .gitignore
        backup_path: Path to the backup directory

    Returns:
        PatchResult describing the merge outcome
    """
    target = plugin_path / file_diff.path
    current = file_diff.actual_content or ""
    expected = file_diff.expected_content or ""

    # If file is missing on disk, write the full expected
    if file_diff.status == FileStatus.MISSING:
        _atomic_write(target, expected)
        return PatchResult(
            path=file_diff.path,
            action="created",
            message="Created .gitignore from standard",
        )

    current_entries = parse_gitignore_entries(current)
    expected_entries = parse_gitignore_entries(expected)

    missing = sorted(expected_entries - current_entries)

    if not missing:
        return PatchResult(
            path=file_diff.path,
            action="skipped",
            message="All expected entries already present",
        )

    # Preserve original content and append missing entries
    merged = current.rstrip("\n")
    merged += "\n\n" + _AIDA_UPDATE_HEADER + "\n"
    merged += "\n".join(missing) + "\n"

    _atomic_write(target, merged)

    backup_file = backup_path / file_diff.path
    backup_ref = (
        str(backup_file) if backup_file.exists() else ""
    )

    return PatchResult(
        path=file_diff.path,
        action="updated",
        message=(
            f"Added {len(missing)} entries: "
            + ", ".join(missing[:5])
            + (
                f" (and {len(missing) - 5} more)"
                if len(missing) > 5
                else ""
            )
        ),
        backup_path=backup_ref,
    )


def _merge_makefile(
    plugin_path: Path,
    file_diff: FileDiff,
    backup_path: Path,
) -> PatchResult:
    """Conservative target-addition merge for Makefiles.

    Extracts target names from both current and expected
    content, then appends full target blocks for any targets
    that are present in the expected content but missing from
    the current Makefile.

    Args:
        plugin_path: Absolute path to the plugin directory
        file_diff: Comparison data for Makefile
        backup_path: Path to the backup directory

    Returns:
        PatchResult describing the merge outcome
    """
    target = plugin_path / file_diff.path
    current = file_diff.actual_content or ""
    expected = file_diff.expected_content or ""

    # If file is missing on disk, write the full expected
    if file_diff.status == FileStatus.MISSING:
        _atomic_write(target, expected)
        return PatchResult(
            path=file_diff.path,
            action="created",
            message="Created Makefile from standard",
        )

    current_targets = extract_makefile_targets(current)
    expected_targets = extract_makefile_targets(expected)

    missing = sorted(expected_targets - current_targets)

    if not missing:
        return PatchResult(
            path=file_diff.path,
            action="skipped",
            message="All expected targets already present",
        )

    # Extract full blocks for each missing target
    blocks: list[str] = []
    added_targets: list[str] = []
    for name in missing:
        block = _extract_makefile_target_block(
            expected, name
        )
        if block:
            blocks.append(block)
            added_targets.append(name)

    if not blocks:
        return PatchResult(
            path=file_diff.path,
            action="skipped",
            message=(
                "Could not extract blocks for missing "
                "targets"
            ),
        )

    # Build .PHONY declaration only for targets we
    # actually extracted
    phony_line = ".PHONY: " + " ".join(added_targets)

    # Preserve original and append
    merged = current.rstrip("\n")
    merged += "\n\n" + _AIDA_UPDATE_HEADER + "\n"
    merged += phony_line + "\n\n"
    merged += "\n\n".join(blocks) + "\n"

    _atomic_write(target, merged)

    backup_file = backup_path / file_diff.path
    backup_ref = (
        str(backup_file) if backup_file.exists() else ""
    )

    return PatchResult(
        path=file_diff.path,
        action="updated",
        message=(
            f"Added {len(added_targets)} targets: "
            + ", ".join(added_targets[:5])
            + (
                f" (and {len(added_targets) - 5} more)"
                if len(added_targets) > 5
                else ""
            )
        ),
        backup_path=backup_ref,
    )


def _apply_manual_review(
    file_diff: FileDiff,
) -> PatchResult:
    """Handle a file that needs manual review.

    Args:
        file_diff: Comparison data for the file

    Returns:
        PatchResult with action skipped and review note
    """
    return PatchResult(
        path=file_diff.path,
        action="skipped",
        message=(
            "Needs manual review: automatic merge not "
            "supported for this file type"
        ),
    )


def _atomic_write(path: Path, content: str) -> None:
    """Write content atomically using a temporary file.

    Writes to a .tmp sibling file then uses os.replace()
    for an atomic rename. Cleans up the temporary file on
    error.

    Args:
        path: Target file path
        content: String content to write
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = Path(str(path) + ".tmp")

    try:
        tmp_path.write_text(content)
        os.replace(str(tmp_path), str(path))
    except Exception:
        # Clean up temp file on failure
        if tmp_path.exists():
            tmp_path.unlink()
        raise


def _update_generator_version(
    plugin_path: Path,
) -> PatchResult:
    """Update generator_version in aida-config.json.

    Reads the existing config, updates the version field,
    and writes back atomically. Creates the file if it does
    not exist.

    Args:
        plugin_path: Absolute path to the plugin directory

    Returns:
        PatchResult for the version update
    """
    config_path = (
        plugin_path / ".claude-plugin" / "aida-config.json"
    )

    try:
        if config_path.exists():
            data: dict[str, Any] = json.loads(
                config_path.read_text()
            )
        else:
            data = {}

        data["generator_version"] = GENERATOR_VERSION

        content = json.dumps(data, indent=2) + "\n"
        _atomic_write(config_path, content)

        return PatchResult(
            path=".claude-plugin/aida-config.json",
            action="updated",
            message=(
                f"Generator version set to "
                f"{GENERATOR_VERSION}"
            ),
        )
    except Exception:
        logger.error(
            "Failed to update generator version",
            exc_info=True,
        )
        return PatchResult(
            path=".claude-plugin/aida-config.json",
            action="failed",
            message="Could not update generator version",
        )


def _extract_makefile_target_block(
    content: str,
    target_name: str,
) -> str:
    """Extract a full target block from Makefile content.

    Finds the target definition line and collects all
    subsequent lines that are tab-indented or empty, stopping
    at the next target definition or a non-empty line that is
    not tab-indented.

    Args:
        content: Full Makefile text
        target_name: Name of the target to extract

    Returns:
        The complete target block including the definition
        line, or empty string if not found
    """
    lines = content.splitlines()
    target_pattern = re.compile(
        rf"^{re.escape(target_name)}:"
    )

    start_idx: int | None = None
    for i, line in enumerate(lines):
        if target_pattern.match(line):
            start_idx = i
            break

    if start_idx is None:
        return ""

    block_lines = [lines[start_idx]]

    for i in range(start_idx + 1, len(lines)):
        line = lines[i]
        # Empty lines are part of the block
        if not line.strip():
            block_lines.append(line)
            continue
        # Tab-indented lines are recipe lines
        if line.startswith("\t"):
            block_lines.append(line)
            continue
        # Anything else ends the block
        break

    # Strip trailing empty lines from the block
    while block_lines and not block_lines[-1].strip():
        block_lines.pop()

    return "\n".join(block_lines)
