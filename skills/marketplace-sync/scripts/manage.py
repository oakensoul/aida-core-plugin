#!/usr/bin/env python3
"""Marketplace Sync Script - Two-Phase API

Entry point for marketplace dependency resolution and version drift
detection. Supports sync (report), sync --apply (update), and status.

Usage:
    python manage.py --get-questions \
        --context='{"operation": "sync"}'
    python manage.py --execute \
        --context='{"operation": "sync", "apply": true}'

Exit codes:
    0   - Success
    1   - Error occurred
"""

import argparse
import json
import sys

import _paths  # noqa: F401

from shared.utils import safe_json_load  # noqa: E402

from sync_ops.scanner import scan_plugins  # noqa: E402
from sync_ops.resolver import resolve_dependencies  # noqa: E402
from sync_ops.report import generate_report, generate_summary  # noqa: E402


def _scan_and_resolve():
    """Run scan + resolve pipeline, return (plugins, resolution)."""
    plugins = scan_plugins()
    plugin_tuples = [
        (p.name, p.installed_version, p.dependencies)
        for p in plugins
    ]
    resolution = resolve_dependencies(plugin_tuples)
    return plugins, resolution


def get_questions(context: dict) -> dict:
    """Phase 1: Scan and return report or questions."""
    operation = context.get("operation", "sync")

    if operation == "status":
        plugins, resolution = _scan_and_resolve()
        summary = generate_summary(plugins, resolution)
        return {"questions": [], "summary": summary, "success": True}

    if operation == "sync":
        apply_mode = context.get("apply", False)
        plugins, resolution = _scan_and_resolve()
        report = generate_report(plugins, resolution)

        if apply_mode:
            outdated = [
                p for p in report["plugins"] if p["status"] == "outdated"
            ]
            if not outdated:
                return {
                    "questions": [],
                    "report": report,
                    "success": True,
                    "message": "All plugins are up to date.",
                }
            return {
                "questions": [{
                    "id": "confirm",
                    "question": (
                        f"Update {len(outdated)} outdated plugin(s)?"
                    ),
                    "type": "boolean",
                    "required": True,
                }],
                "report": report,
                "success": True,
            }

        return {"questions": [], "report": report, "success": True}

    return {
        "questions": [],
        "success": False,
        "message": f"Unknown operation: {operation}",
    }


def execute(context: dict, responses: dict) -> dict:
    """Phase 2: Execute operation."""
    operation = context.get("operation", "sync")

    if operation in ("sync", "status"):
        apply_mode = context.get("apply", False)
        if not apply_mode:
            plugins, resolution = _scan_and_resolve()
            report = generate_report(plugins, resolution)
            return {"success": True, "report": report}

        confirmed = responses.get("confirm", False)
        if not confirmed:
            return {"success": True, "message": "Update cancelled."}

        return {
            "success": True,
            "message": (
                "Update capability not yet implemented. "
                "Use /plugin install to update manually."
            ),
        }

    return {
        "success": False,
        "message": f"Unknown operation: {operation}",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Marketplace Sync")
    parser.add_argument("--get-questions", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--context", type=str, default="{}")
    parser.add_argument("--responses", type=str, default="{}")

    args = parser.parse_args()

    try:
        context = safe_json_load(args.context) if args.context else {}
        responses = (
            safe_json_load(args.responses) if args.responses else {}
        )

        if args.get_questions:
            result = get_questions(context)
        elif args.execute:
            result = execute(context, responses)
        else:
            parser.print_help()
            return 1

        print(json.dumps(result, indent=2))
        return 0 if result.get("success") else 1

    except Exception as e:
        print(json.dumps({"success": False, "message": str(e)}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
