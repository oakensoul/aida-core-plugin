"""Report generator for marketplace sync.

Produces structured report data from scan results and dependency
resolution, including plugin status table, dependency issues,
and summary counts.
"""

from __future__ import annotations

from typing import Any, Dict, List

from sync_ops.resolver import ResolutionResult
from sync_ops.scanner import PluginState

try:
    from packaging.version import Version
except ImportError:
    Version = None  # type: ignore[assignment, misc]


def _compare_versions(installed: str, available: str) -> str:
    """Compare two version strings, return status."""
    if not installed or installed == "unknown":
        return "unknown"
    if not available:
        return "unknown"
    try:
        iv = Version(installed)
        av = Version(available)
        if iv == av:
            return "up-to-date"
        elif iv < av:
            return "outdated"
        else:
            return "ahead"
    except Exception:
        return "unknown"


def generate_report(
    plugins: List[PluginState],
    resolution: ResolutionResult,
) -> Dict[str, Any]:
    """Generate a structured sync report.

    Args:
        plugins: List of PluginState from scanner.
        resolution: ResolutionResult from resolver.

    Returns:
        Dict with keys: plugins, dependency_issues, cycles,
        unresolved, warnings, summary.
    """
    plugin_rows = []
    for p in plugins:
        if p.source == "local":
            status = "local"
        else:
            status = _compare_versions(
                p.installed_version or "",
                p.available_version or "",
            )
        plugin_rows.append(
            {
                "name": p.name,
                "installed": p.installed_version or "-",
                "available": p.available_version or "-",
                "status": status,
                "marketplace": p.marketplace_id or "-",
            }
        )

    # Collect dependency issues
    dep_issues = []
    for _name, edges in resolution.graph.items():
        for edge in edges:
            if not edge.satisfied:
                dep_issues.append(
                    {
                        "dependent": edge.dependent,
                        "dependency": edge.dependency,
                        "constraint": edge.constraint,
                        "installed": edge.installed or "-",
                    }
                )

    # Summary
    outdated = sum(
        1 for r in plugin_rows if r["status"] == "outdated"
    )
    summary = (
        f"{len(plugins)} plugins, {outdated} outdated, "
        f"{len(dep_issues)} dependency issues"
    )

    return {
        "plugins": plugin_rows,
        "dependency_issues": dep_issues,
        "cycles": resolution.cycles,
        "unresolved": resolution.unresolved,
        "warnings": resolution.warnings,
        "summary": summary,
    }


def generate_summary(
    plugins: List[PluginState],
    resolution: ResolutionResult,
) -> Dict[str, int]:
    """Generate quick summary counts.

    Returns:
        Dict with total, outdated, up_to_date, ahead, local,
        unknown, dependency_issues counts.
    """
    report = generate_report(plugins, resolution)
    rows = report["plugins"]
    return {
        "total": len(rows),
        "outdated": sum(
            1 for r in rows if r["status"] == "outdated"
        ),
        "up_to_date": sum(
            1 for r in rows if r["status"] == "up-to-date"
        ),
        "ahead": sum(1 for r in rows if r["status"] == "ahead"),
        "local": sum(1 for r in rows if r["status"] == "local"),
        "unknown": sum(
            1 for r in rows if r["status"] == "unknown"
        ),
        "dependency_issues": len(report["dependency_issues"]),
    }
