# SPDX-FileCopyrightText: 2026 The AIDA Core Authors
# SPDX-License-Identifier: MPL-2.0

"""Shared helpers for plugin-manager operations.

Provides template variable construction used by both scaffold
and update operations.
"""

from datetime import datetime, timezone
from typing import Any

from shared.spdx import render_spdx_blocks, resolve_spdx_context

from .constants import GENERATOR_VERSION


def _normalize_python_version(version: str) -> str:
    """Normalize python version to X.Y format."""
    parts = version.split(".")
    if len(parts) >= 2:
        return f"{parts[0]}.{parts[1]}"
    return version


def build_template_variables(
    context: dict[str, Any],
    license_text: str,
) -> dict[str, Any]:
    """Build the standard template variables dictionary.

    Constructs the full set of Jinja2 template variables from
    a plugin context dictionary and resolved license text. Used
    by both scaffold and update operations.

    Args:
        context: Plugin context containing at minimum:
            - plugin_name: kebab-case name
            - description: plugin description
            - version: semver string
            - author_name: author name
            - author_email: author email
            - license_id: SPDX license identifier
            - language: "python" or "typescript"
        license_text: Resolved full license body text

    Returns:
        Template variables dictionary for Jinja2 rendering
    """
    plugin_name = context["plugin_name"]
    plugin_display_name = (
        plugin_name.replace("-", " ").title()
    )
    language = context.get("language", "python")
    script_extension = (
        ".py" if language == "python" else ".ts"
    )

    year = str(datetime.now(timezone.utc).year)
    timestamp = datetime.now(timezone.utc).isoformat()

    keywords_raw = context.get("keywords", "")
    if isinstance(keywords_raw, str):
        keywords = [
            k.strip()
            for k in keywords_raw.split(",")
            if k.strip()
        ]
    else:
        keywords = (
            list(keywords_raw) if keywords_raw else []
        )

    # Compute SPDX context. Default copyright holder for scaffolded
    # plugins is "The {Display Name} Authors" so the generated
    # `AUTHORS` file is the authoritative roster — file headers
    # stay stable as that file changes. Caller can override.
    spdx_context = resolve_spdx_context({
        "year": year,
        "license_id": context.get("license_id"),
        "copyright_holder": (
            context.get("copyright_holder")
            or f"The {plugin_display_name} Authors"
        ),
    })
    spdx_blocks = render_spdx_blocks(spdx_context)

    return {
        "plugin_name": plugin_name,
        "plugin_display_name": plugin_display_name,
        "description": context.get("description", ""),
        "version": context.get("version", "0.1.0"),
        "author_name": context.get("author_name", ""),
        "author_email": context.get("author_email", ""),
        "license_id": context.get("license_id", "MIT"),
        "license_text": license_text,
        "year": year,
        "copyright_holder": spdx_context["copyright_holder"],
        **spdx_blocks,
        "language": language,
        "script_extension": script_extension,
        "python_version": _normalize_python_version(
            context.get("python_version", "3.11")
        ),
        "node_version": context.get("node_version", "22"),
        "keywords": keywords,
        "repository_url": context.get(
            "repository_url", ""
        ),
        "include_agent_stub": context.get(
            "include_agent_stub", False
        ),
        "agent_stub_name": context.get(
            "agent_stub_name", plugin_name
        ),
        "agent_stub_description": context.get(
            "agent_stub_description",
            f"Agent for {plugin_display_name}",
        ),
        "include_skill_stub": context.get(
            "include_skill_stub", False
        ),
        "skill_stub_name": context.get(
            "skill_stub_name", plugin_name
        ),
        "skill_stub_description": context.get(
            "skill_stub_description",
            f"Skill for {plugin_display_name}",
        ),
        "timestamp": timestamp,
        "generator_version": GENERATOR_VERSION,
    }
