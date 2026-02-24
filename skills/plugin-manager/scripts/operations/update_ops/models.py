"""Data models for the plugin update operation.

Defines enums for file categories, merge strategies, and
statuses, plus dataclasses for file diffs, diff reports,
and patch results.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class FileCategory(Enum):
    """Classification of files managed by the scaffolder."""

    CUSTOM = "custom"
    BOILERPLATE = "boilerplate"
    COMPOSITE = "composite"
    CI_WORKFLOW = "ci_workflow"
    DEPENDENCY_CONFIG = "dependency_config"
    TEST_SCAFFOLD = "test_scaffold"
    METADATA = "metadata"


class MergeStrategy(Enum):
    """How to handle a file during update."""

    SKIP = "skip"
    OVERWRITE = "overwrite"
    MERGE = "merge"
    ADD = "add"
    MANUAL_REVIEW = "manual_review"


class FileStatus(Enum):
    """Status of a file compared to current standards."""

    MISSING = "missing"
    OUTDATED = "outdated"
    UP_TO_DATE = "up_to_date"
    CUSTOM_SKIP = "custom_skip"


@dataclass
class FileDiff:
    """Comparison result for a single file.

    Attributes:
        path: Relative path from plugin root
        category: File classification
        status: Comparison result
        strategy: Recommended merge strategy
        expected_content: What the template would produce
        actual_content: What currently exists on disk
        diff_summary: Human-readable description of changes
    """

    path: str
    category: FileCategory
    status: FileStatus
    strategy: MergeStrategy
    expected_content: str | None = None
    actual_content: str | None = None
    diff_summary: str = ""


@dataclass
class DiffReport:
    """Full scan report for a plugin.

    Attributes:
        plugin_path: Absolute path to the plugin
        plugin_name: Plugin name from plugin.json
        language: Detected language ("python" or "typescript")
        generator_version: Version the plugin was created with
        current_version: Current standard version
        files: List of file comparisons
    """

    plugin_path: str
    plugin_name: str
    language: str
    generator_version: str
    current_version: str
    files: list[FileDiff] = field(default_factory=list)

    @property
    def missing_files(self) -> list[FileDiff]:
        """Files present in standards but absent from plugin."""
        return [
            f
            for f in self.files
            if f.status == FileStatus.MISSING
        ]

    @property
    def outdated_files(self) -> list[FileDiff]:
        """Files that exist but differ from current standards."""
        return [
            f
            for f in self.files
            if f.status == FileStatus.OUTDATED
        ]

    @property
    def up_to_date_files(self) -> list[FileDiff]:
        """Files that match current standards."""
        return [
            f
            for f in self.files
            if f.status == FileStatus.UP_TO_DATE
        ]

    @property
    def custom_skip_files(self) -> list[FileDiff]:
        """Files classified as custom content (never modified)."""
        return [
            f
            for f in self.files
            if f.status == FileStatus.CUSTOM_SKIP
        ]

    @property
    def summary(self) -> dict[str, int]:
        """Count of files by status."""
        return {
            "missing": len(self.missing_files),
            "outdated": len(self.outdated_files),
            "up_to_date": len(self.up_to_date_files),
            "custom_skip": len(self.custom_skip_files),
            "total": len(self.files),
        }

    @property
    def needs_update(self) -> bool:
        """Whether any files need attention."""
        return bool(
            self.missing_files or self.outdated_files
        )


@dataclass
class PatchResult:
    """Result of patching a single file.

    Attributes:
        path: Relative path from plugin root
        action: What was done
        message: Human-readable description
        backup_path: Path to backup if created
    """

    path: str
    action: str  # "created", "updated", "skipped", "failed"
    message: str
    backup_path: str = ""
