#!/usr/bin/env python3
"""Permissions management.

Two-phase API for interactive permission setup. Scans installed
plugins for recommended permissions, presents categorized choices,
and writes the selected configuration to settings.json.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

# Reuse utilities from aida-dispatch
sys.path.insert(
    0,
    str(
        Path(__file__).parent.parent.parent
        / "aida-dispatch"
        / "scripts"
    ),
)

# Local imports (same directory)
_scripts_dir = str(Path(__file__).parent)
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)

from aggregator import (  # noqa: E402
    deduplicate_and_categorize,
    detect_conflicts,
)
from scanner import scan_plugins  # noqa: E402
from settings_manager import (  # noqa: E402
    get_settings_path,
    read_all_settings,
    write_permissions,
)

logger = logging.getLogger(__name__)

# --- Presets ---

PRESET_DEVELOPER_WORKSTATION: dict[str, str] = {
    "file-edit": "allow",
    "file-read": "allow",
    "git": "allow",
    "terminal": "allow",
    "docker": "ask",
    "mcp": "allow",
    "network": "allow",
    "dangerous": "ask",
}

PRESET_CI_SAFE: dict[str, str] = {
    "file-edit": "ask",
    "file-read": "allow",
    "git": "ask",
    "terminal": "ask",
    "docker": "deny",
    "mcp": "ask",
    "network": "ask",
    "dangerous": "deny",
}

PRESET_LOCKED_DOWN: dict[str, str] = {
    "file-edit": "ask",
    "file-read": "ask",
    "git": "ask",
    "terminal": "ask",
    "docker": "ask",
    "mcp": "ask",
    "network": "ask",
    "dangerous": "ask",
}

PRESETS: dict[str, dict[str, str]] = {
    "developer-workstation": PRESET_DEVELOPER_WORKSTATION,
    "ci-safe": PRESET_CI_SAFE,
    "locked-down": PRESET_LOCKED_DOWN,
}


def get_questions(context: dict) -> dict:
    """Phase 1: Build interactive questions for permission setup.

    Args:
        context: Context dict, may contain ``operation`` key.

    Returns:
        Dict with ``questions`` list and ``inferred`` data.
    """
    plugins = scan_plugins()
    categorized = deduplicate_and_categorize(plugins)
    current = read_all_settings()
    categories = categorized.get("categories", {})

    proposed_flat: dict[str, list[str]] = {
        "allow": [],
        "ask": [],
        "deny": [],
    }
    for cat_data in categories.values():
        suggested = cat_data.get("suggested", "ask")
        rules = cat_data.get("rules", [])
        if suggested in proposed_flat:
            proposed_flat[suggested].extend(rules)

    current_flat: dict[str, list[str]] = {
        "allow": [],
        "ask": [],
        "deny": [],
    }
    for scope_perms in current.values():
        for action in ("allow", "ask", "deny"):
            current_flat[action].extend(scope_perms.get(action, []))

    conflicts = detect_conflicts(current_flat, proposed_flat)

    questions: list[dict] = []

    questions.append(
        {
            "id": "preset",
            "type": "choice",
            "prompt": "Select a permissions preset",
            "description": (
                "Choose a preset to quickly configure "
                "permissions, or select 'custom' to configure "
                "each category individually."
            ),
            "choices": [
                {
                    "value": "developer-workstation",
                    "label": "Developer Workstation",
                    "description": (
                        "Allow most operations, ask for dangerous ones"
                    ),
                },
                {
                    "value": "ci-safe",
                    "label": "CI Safe",
                    "description": (
                        "Ask for writes, deny docker and "
                        "dangerous operations"
                    ),
                },
                {
                    "value": "locked-down",
                    "label": "Locked Down",
                    "description": "Ask for everything",
                },
                {
                    "value": "custom",
                    "label": "Custom",
                    "description": (
                        "Configure each category individually"
                    ),
                },
            ],
            "default": "developer-workstation",
        }
    )

    for cat_key, cat_data in sorted(categories.items()):
        questions.append(
            {
                "id": f"category_{cat_key}",
                "type": "choice",
                "prompt": f"Permission for: {cat_data['label']}",
                "description": cat_data["description"],
                "choices": [
                    {
                        "value": "allow",
                        "label": "Allow",
                        "description": (
                            "Automatically allow these operations"
                        ),
                    },
                    {
                        "value": "ask",
                        "label": "Ask",
                        "description": (
                            "Prompt before these operations"
                        ),
                    },
                    {
                        "value": "deny",
                        "label": "Deny",
                        "description": "Block these operations",
                    },
                ],
                "default": cat_data.get("suggested", "ask"),
                "condition": {"preset": "custom"},
                "rules": cat_data.get("rules", []),
                "sources": cat_data.get("sources", []),
            }
        )

    questions.append(
        {
            "id": "scope",
            "type": "choice",
            "prompt": "Where should permissions be saved?",
            "description": (
                "User scope applies globally, project scope "
                "applies to this project (shared), local "
                "scope applies to this project (personal)."
            ),
            "choices": [
                {
                    "value": "user",
                    "label": "User (~/.claude/settings.json)",
                    "description": "Apply to all projects",
                },
                {
                    "value": "project",
                    "label": "Project (.claude/settings.json)",
                    "description": (
                        "Apply to this project (shared with team)"
                    ),
                },
                {
                    "value": "local",
                    "label": (
                        "Local (.claude/settings.local.json)"
                    ),
                    "description": (
                        "Apply to this project (personal only)"
                    ),
                },
            ],
            "default": "user",
        }
    )

    return {
        "questions": questions,
        "inferred": {
            "categories": categories,
            "current_permissions": current,
            "conflicts": conflicts,
            "plugin_count": len(plugins),
        },
    }


def execute(context: dict, responses: dict) -> dict:
    """Phase 2: Apply permission choices to settings.

    Args:
        context: Context dict from Phase 1.
        responses: User responses keyed by question ``id``.

    Returns:
        Dict with ``success``, ``files_modified``,
        ``rules_count``, and ``message`` keys.
    """
    preset = responses.get("preset", "developer-workstation")
    scope = responses.get("scope", "user")
    categories = context.get("categories", {})

    rules: dict[str, list[str]] = {
        "allow": [],
        "ask": [],
        "deny": [],
    }

    if preset != "custom" and preset in PRESETS:
        preset_map = PRESETS[preset]
        for cat_key, cat_data in categories.items():
            action = preset_map.get(cat_key, "ask")
            cat_rules = cat_data.get("rules", [])
            rules[action].extend(cat_rules)
    else:
        for cat_key, cat_data in categories.items():
            response_key = f"category_{cat_key}"
            action = responses.get(response_key, "ask")
            if action not in ("allow", "ask", "deny"):
                action = "ask"
            cat_rules = cat_data.get("rules", [])
            rules[action].extend(cat_rules)

    for action in rules:
        rules[action] = sorted(set(rules[action]))

    rules = {k: v for k, v in rules.items() if v}

    total_rules = sum(len(v) for v in rules.values())

    try:
        success = write_permissions(
            scope=scope,
            rules=rules,
            merge_strategy="merge",
        )
    except (ValueError, OSError) as exc:
        return {
            "success": False,
            "files_modified": [],
            "rules_count": 0,
            "message": f"Failed to write permissions: {exc}",
        }

    if success:
        path = get_settings_path(scope)
        return {
            "success": True,
            "files_modified": [str(path)],
            "rules_count": total_rules,
            "message": (
                f"Wrote {total_rules} permission rules to {path}"
            ),
        }

    return {
        "success": False,
        "files_modified": [],
        "rules_count": 0,
        "message": "Failed to write permissions",
    }


def audit(context: dict) -> dict:
    """Run permissions audit without interactive setup.

    Args:
        context: Context dict (unused currently).

    Returns:
        Dict with ``coverage``, ``gaps``, ``conflicts``, and
        ``summary`` keys.
    """
    plugins = scan_plugins()
    categorized = deduplicate_and_categorize(plugins)
    current = read_all_settings()
    categories = categorized.get("categories", {})

    configured_rules: set[str] = set()
    current_flat: dict[str, list[str]] = {
        "allow": [],
        "ask": [],
        "deny": [],
    }
    for scope_perms in current.values():
        for action in ("allow", "ask", "deny"):
            scope_rules = scope_perms.get(action, [])
            current_flat[action].extend(scope_rules)
            configured_rules.update(scope_rules)

    recommended_rules: set[str] = set()
    for cat_data in categories.values():
        recommended_rules.update(cat_data.get("rules", []))

    covered = recommended_rules & configured_rules
    coverage_pct = (
        (len(covered) / len(recommended_rules) * 100)
        if recommended_rules
        else 100.0
    )

    gaps = sorted(recommended_rules - configured_rules)

    proposed_flat: dict[str, list[str]] = {
        "allow": [],
        "ask": [],
        "deny": [],
    }
    for cat_data in categories.values():
        suggested = cat_data.get("suggested", "ask")
        rules = cat_data.get("rules", [])
        if suggested in proposed_flat:
            proposed_flat[suggested].extend(rules)

    conflicts = detect_conflicts(current_flat, proposed_flat)

    return {
        "coverage": {
            "total_recommended": len(recommended_rules),
            "total_configured": len(configured_rules),
            "covered": len(covered),
            "percentage": round(coverage_pct, 1),
        },
        "gaps": gaps,
        "conflicts": conflicts,
        "summary": (
            f"{len(covered)}/{len(recommended_rules)} "
            f"recommended rules configured "
            f"({coverage_pct:.0f}% coverage). "
            f"{len(gaps)} gaps, {len(conflicts)} conflicts."
        ),
    }


def main() -> int:
    """CLI entry point for permissions management."""
    parser = argparse.ArgumentParser(
        description="Manage Claude Code permissions"
    )
    parser.add_argument(
        "--get-questions",
        action="store_true",
        help="Phase 1: get interactive questions",
    )
    parser.add_argument(
        "--execute",
        type=str,
        metavar="JSON",
        help="Phase 2: execute with responses JSON",
    )
    parser.add_argument(
        "--audit",
        action="store_true",
        help="Run permissions audit",
    )
    parser.add_argument(
        "--context",
        type=str,
        metavar="JSON",
        help="Context JSON string or file path",
    )

    args = parser.parse_args()

    context: dict = {}
    if args.context:
        context = _load_json_arg(args.context)

    if args.get_questions:
        result = get_questions(context)
        print(json.dumps(result, indent=2))
        return 0

    if args.execute:
        responses = _load_json_arg(args.execute)
        if not context:
            questions_result = get_questions({})
            context = questions_result.get("inferred", {})
        result = execute(context, responses)
        print(json.dumps(result, indent=2))
        return 0 if result.get("success") else 1

    if args.audit:
        result = audit(context)
        print(json.dumps(result, indent=2))
        return 0

    parser.print_help()
    return 1


def _load_json_arg(value: str) -> dict:
    """Load JSON from a string or file path.

    Args:
        value: JSON string or path to a JSON file.

    Returns:
        Parsed dict.
    """
    path = Path(value)
    if path.is_file():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return json.loads(value)


if __name__ == "__main__":
    sys.exit(main())
