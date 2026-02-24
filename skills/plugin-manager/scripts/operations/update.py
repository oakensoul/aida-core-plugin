"""Plugin Update Operations - Two-Phase API

Scans existing plugin projects against current scaffold
standards and applies non-destructive patches.

Usage (via manage.py):
    # Phase 1: Scan and report (returns JSON)
    python manage.py --get-questions \
        --context='{"operation": "update", "plugin_path": "..."}'

    # Phase 2: Apply patches (returns JSON)
    python manage.py --execute \
        --context='{"operation": "update", "plugin_path": "..."}'
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import _paths

from .constants import GENERATOR_VERSION
from .update_ops import patcher, scanner
from .update_ops.models import (
    FileCategory,
    FileStatus,
    MergeStrategy,
)

logger = logging.getLogger(__name__)


def get_questions(
    context: dict[str, Any],
) -> dict[str, Any]:
    """Phase 1: Scan plugin and return diff report with questions.

    Scans the plugin directory against current scaffold
    standards and returns a diff report along with questions
    about how to handle outdated files.

    Args:
        context: Operation context containing at minimum
            ``plugin_path`` (str)

    Returns:
        Dictionary with 'questions', 'inferred', and 'phase'
    """
    plugin_path_str = context.get("plugin_path")
    if not plugin_path_str:
        return {
            "success": False,
            "message": (
                "plugin_path is required for update operation"
            ),
        }

    plugin_path = Path(plugin_path_str).resolve()
    templates_dir = _paths.SCAFFOLD_TEMPLATES_DIR

    try:
        report = scanner.scan_plugin(
            plugin_path, templates_dir
        )
    except ValueError as exc:
        return {
            "success": False,
            "message": str(exc),
        }
    except Exception as exc:
        logger.error(
            "Scan failed: %s", exc, exc_info=True
        )
        return {
            "success": False,
            "message": f"Scan failed: {exc}",
        }

    inferred = _serialize_report(report)

    if not report.needs_update:
        return {
            "questions": [],
            "inferred": inferred,
            "phase": "get_questions",
            "message": (
                "Plugin is up to date with current standards"
            ),
        }

    questions: list[dict[str, Any]] = []

    has_outdated_boilerplate = any(
        f.category == FileCategory.BOILERPLATE
        and f.status == FileStatus.OUTDATED
        for f in report.files
    )

    if has_outdated_boilerplate:
        questions.append({
            "id": "boilerplate_strategy",
            "question": (
                "How should outdated boilerplate "
                "files be handled?"
            ),
            "type": "choice",
            "options": ["overwrite", "skip"],
            "default": "overwrite",
        })

    return {
        "questions": questions,
        "inferred": inferred,
        "phase": "get_questions",
    }


def execute(
    context: dict[str, Any],
    responses: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Phase 2: Apply approved patches to the plugin.

    Re-scans the plugin for fresh state, builds overrides
    from user responses, then applies patches.

    Args:
        context: Operation context containing at minimum
            ``plugin_path`` (str)
        responses: User responses from Phase 1 questions

    Returns:
        Result dictionary with success status and details
    """
    plugin_path_str = context.get("plugin_path")
    if not plugin_path_str:
        return {
            "success": False,
            "message": (
                "plugin_path is required for update operation"
            ),
        }

    plugin_path = Path(plugin_path_str).resolve()
    templates_dir = _paths.SCAFFOLD_TEMPLATES_DIR

    try:
        report = scanner.scan_plugin(
            plugin_path, templates_dir
        )
    except ValueError as exc:
        return {
            "success": False,
            "message": str(exc),
        }
    except Exception as exc:
        logger.error(
            "Scan failed: %s", exc, exc_info=True
        )
        return {
            "success": False,
            "message": f"Scan failed: {exc}",
        }

    if not report.needs_update:
        return {
            "success": True,
            "message": "Plugin is up to date",
            "files_created": [],
            "files_updated": [],
            "files_skipped": [],
            "manual_steps": [],
            "generator_version": GENERATOR_VERSION,
        }

    overrides = _build_overrides(report, responses)

    try:
        results = patcher.apply_patches(
            plugin_path, report, overrides
        )
    except Exception as exc:
        logger.error(
            "Patching failed: %s", exc, exc_info=True
        )
        return {
            "success": False,
            "message": f"Patching failed: {exc}",
        }

    files_created = [
        r.path for r in results if r.action == "created"
    ]
    files_updated = [
        r.path for r in results if r.action == "updated"
    ]
    files_skipped = [
        r.path for r in results if r.action == "skipped"
    ]

    backup_path = ""
    for r in results:
        if r.backup_path:
            backup_path = r.backup_path
            break

    manual_steps = _build_manual_steps(report, results)

    old_version = report.generator_version
    new_version = GENERATOR_VERSION

    return {
        "success": True,
        "message": (
            f"Updated plugin '{report.plugin_name}' "
            f"from v{old_version} to v{new_version}"
        ),
        "files_created": files_created,
        "files_updated": files_updated,
        "files_skipped": files_skipped,
        "manual_steps": manual_steps,
        "backup_path": backup_path,
        "generator_version": GENERATOR_VERSION,
    }


def _serialize_report(
    report: scanner.DiffReport,
) -> dict[str, Any]:
    """Serialize a DiffReport into the inferred payload.

    Args:
        report: Scan results from the scanner module

    Returns:
        Dictionary suitable for the 'inferred' response key
    """
    manual_review_files = [
        f
        for f in report.files
        if f.strategy == MergeStrategy.MANUAL_REVIEW
        and f.status
        in (FileStatus.MISSING, FileStatus.OUTDATED)
    ]

    return {
        "plugin_name": report.plugin_name,
        "plugin_path": report.plugin_path,
        "language": report.language,
        "generator_version": report.generator_version,
        "current_standard": report.current_version,
        "scan_result": {
            "summary": report.summary,
            "needs_update": report.needs_update,
            "missing_files": [
                {
                    "path": f.path,
                    "diff_summary": f.diff_summary,
                }
                for f in report.missing_files
            ],
            "outdated_files": [
                {
                    "path": f.path,
                    "diff_summary": f.diff_summary,
                    "category": f.category.value,
                }
                for f in report.outdated_files
            ],
            "up_to_date_files": [
                {"path": f.path}
                for f in report.up_to_date_files
            ],
            "custom_skip_files": [
                {"path": f.path}
                for f in report.custom_skip_files
            ],
            "manual_review_files": [
                {
                    "path": f.path,
                    "diff_summary": f.diff_summary,
                }
                for f in manual_review_files
            ],
        },
    }


def _build_overrides(
    report: scanner.DiffReport,
    responses: dict[str, Any] | None,
) -> dict[str, MergeStrategy]:
    """Build strategy overrides from user responses.

    Args:
        report: Scan results from the scanner module
        responses: User responses from Phase 1

    Returns:
        Mapping of file paths to override strategies
    """
    if not responses:
        return {}

    overrides: dict[str, MergeStrategy] = {}

    strategy_value = responses.get("boilerplate_strategy")
    if strategy_value == "skip":
        for f in report.files:
            if f.category == FileCategory.BOILERPLATE:
                overrides[f.path] = MergeStrategy.SKIP

    return overrides


def _build_manual_steps(
    report: scanner.DiffReport,
    results: list[patcher.PatchResult],
) -> list[str]:
    """Build the list of manual follow-up steps.

    Includes messages for files flagged for manual review
    in the diff report, plus standard post-update
    verification steps.

    Args:
        report: Scan results from the scanner module
        results: Patch results from the patcher

    Returns:
        List of human-readable manual step strings
    """
    steps: list[str] = []

    # Identify files that were flagged for manual review
    # by checking the strategy in the diff report
    manual_review_paths = {
        f.path
        for f in report.files
        if f.strategy == MergeStrategy.MANUAL_REVIEW
        and f.status
        in (FileStatus.MISSING, FileStatus.OUTDATED)
    }

    for r in results:
        if r.path in manual_review_paths:
            steps.append(
                f"Review {r.path}: {r.message}"
            )

    steps.extend([
        "Run `make lint` to verify the updated configuration",
        "Run `make test` to ensure nothing is broken",
        "Review changes with `git diff` before committing",
    ])

    return steps
