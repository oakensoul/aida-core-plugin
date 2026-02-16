#!/usr/bin/env python3
"""Permission aggregator.

Deduplicates, categorizes, and detects conflicts across plugin
permission recommendations.
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

CATEGORY_METADATA: dict[str, dict[str, str]] = {
    "file-edit": {
        "label": "File Editing",
        "description": (
            "Permissions for creating, editing, and deleting files"
        ),
    },
    "file-read": {
        "label": "File Reading",
        "description": "Permissions for reading file contents",
    },
    "git": {
        "label": "Git Operations",
        "description": (
            "Permissions for git commands like commit, push, "
            "and branch management"
        ),
    },
    "terminal": {
        "label": "Terminal Commands",
        "description": (
            "Permissions for running shell commands and scripts"
        ),
    },
    "docker": {
        "label": "Docker Operations",
        "description": (
            "Permissions for Docker container and image management"
        ),
    },
    "mcp": {
        "label": "MCP Servers",
        "description": (
            "Permissions for Model Context Protocol server access"
        ),
    },
    "network": {
        "label": "Network Access",
        "description": (
            "Permissions for HTTP requests and network operations"
        ),
    },
    "dangerous": {
        "label": "Dangerous Operations",
        "description": (
            "High-risk operations like rm -rf, force push, "
            "and system modifications"
        ),
    },
}


def _parse_rule(rule: str) -> tuple[str, str]:
    """Extract tool and pattern from a permission rule.

    Args:
        rule: Rule string like ``Bash(git commit:*)``.

    Returns:
        Tuple of (tool_name, pattern) or (rule, "") if unmatched.
    """
    match = re.match(r"^(\w+)\((.+)\)$", rule)
    if match:
        return match.group(1), match.group(2)
    return rule, ""


def _wildcard_subsumes(broad: str, narrow: str) -> bool:
    """Check if a broad wildcard rule subsumes a narrower one.

    For example, ``Bash(git:*)`` subsumes ``Bash(git commit:*)``.

    Args:
        broad: The potentially broader rule.
        narrow: The potentially narrower rule.

    Returns:
        True if broad subsumes narrow.
    """
    broad_tool, broad_pat = _parse_rule(broad)
    narrow_tool, narrow_pat = _parse_rule(narrow)

    if broad_tool != narrow_tool:
        return False

    if broad_pat == "*":
        return True

    if broad_pat.endswith(":*") and narrow_pat.endswith(":*"):
        broad_cmd = broad_pat[:-2]
        narrow_cmd = narrow_pat[:-2]
        return narrow_cmd.startswith(broad_cmd)

    if broad_pat.endswith("*"):
        prefix = broad_pat[:-1]
        return narrow_pat.startswith(prefix)

    return False


def merge_rules(rules_lists: list[list[str]]) -> list[str]:
    """Union of rules with wildcard subsumption.

    If ``Bash(git:*)`` exists, ``Bash(git commit:*)`` is removed
    as redundant.

    Args:
        rules_lists: Multiple lists of rule strings to merge.

    Returns:
        Deduplicated and subsumed list of rules.
    """
    all_rules: set[str] = set()
    for rules in rules_lists:
        all_rules.update(rules)

    merged: list[str] = sorted(all_rules)

    result: list[str] = []
    for rule in merged:
        subsumed = False
        for other in merged:
            if other != rule and _wildcard_subsumes(other, rule):
                subsumed = True
                break
        if not subsumed:
            result.append(rule)

    return result


def deduplicate_and_categorize(
    plugin_permissions: list[dict],
) -> dict:
    """Merge categories across plugins and deduplicate rules.

    Args:
        plugin_permissions: List of dicts from
            ``scanner.scan_plugins()``, each with ``name`` and
            ``permissions`` keys.

    Returns:
        Dict with ``categories`` key mapping category keys to:
        ``label``, ``description``, ``rules``, ``suggested``,
        and ``sources``.
    """
    categories: dict[str, dict] = {}

    for plugin in plugin_permissions:
        plugin_name = plugin["name"]
        perms = plugin.get("permissions", {})

        for cat_key, cat_data in perms.items():
            if not isinstance(cat_data, dict):
                continue

            if cat_key not in categories:
                meta = CATEGORY_METADATA.get(
                    cat_key,
                    {
                        "label": cat_key.replace("-", " ").title(),
                        "description": (
                            f"Permissions for {cat_key}"
                        ),
                    },
                )
                categories[cat_key] = {
                    "label": meta["label"],
                    "description": meta["description"],
                    "rules": [],
                    "suggested": "ask",
                    "sources": [],
                    "_rules_lists": [],
                }

            cat = categories[cat_key]
            cat["sources"].append(plugin_name)

            rules = cat_data.get("rules", [])
            if isinstance(rules, list):
                cat["_rules_lists"].append(rules)

            suggested = cat_data.get("suggested", "ask")
            if isinstance(suggested, str):
                priority = {"allow": 0, "ask": 1, "deny": 2}
                current = priority.get(cat["suggested"], 1)
                proposed = priority.get(suggested, 1)
                if proposed < current:
                    cat["suggested"] = suggested

    for cat in categories.values():
        cat["rules"] = merge_rules(cat.pop("_rules_lists", []))
        cat["sources"] = sorted(set(cat["sources"]))

    return {"categories": categories}


def detect_conflicts(
    current_settings: dict, proposed: dict
) -> list[dict]:
    """Find rules that conflict between current and proposed.

    A conflict occurs when a rule appears in a different action
    bucket (allow vs deny) between current and proposed settings.

    Args:
        current_settings: Current permissions with allow/ask/deny.
        proposed: Proposed permissions with allow/ask/deny.

    Returns:
        List of conflict dicts with ``rule``, ``current_action``,
        ``proposed_action``, and ``category`` keys.
    """
    conflicts: list[dict] = []

    current_map: dict[str, str] = {}
    for action in ("allow", "ask", "deny"):
        for rule in current_settings.get(action, []):
            current_map[rule] = action

    proposed_map: dict[str, str] = {}
    for action in ("allow", "ask", "deny"):
        for rule in proposed.get(action, []):
            proposed_map[rule] = action

    for rule, proposed_action in proposed_map.items():
        current_action = current_map.get(rule)
        if current_action and current_action != proposed_action:
            conflicts.append(
                {
                    "rule": rule,
                    "current_action": current_action,
                    "proposed_action": proposed_action,
                    "category": _infer_category(rule),
                }
            )

    return conflicts


def _infer_category(rule: str) -> str:
    """Infer the category of a rule based on its tool/pattern.

    Args:
        rule: Permission rule string.

    Returns:
        Best-guess category key.
    """
    tool, pattern = _parse_rule(rule)

    if tool in ("Edit", "Write"):
        return "file-edit"
    if tool in ("Read", "Glob", "Grep"):
        return "file-read"
    if tool == "Bash" and pattern.startswith("git"):
        return "git"
    if tool == "Bash" and pattern.startswith("docker"):
        return "docker"
    if tool in ("mcp", "MCP"):
        return "mcp"
    return "terminal"
