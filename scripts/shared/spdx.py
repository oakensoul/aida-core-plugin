# SPDX-FileCopyrightText: 2026 The AIDA Core Authors
# SPDX-License-Identifier: MPL-2.0

"""SPDX header helpers for scaffolding-emitted artifacts.

The scaffolding tools (``plugin-manager``, ``agent-manager``, etc.)
generate hand-authored-equivalent files into downstream plugins and
into this repo. Those files should carry SPDX copyright/license
headers so they are reuse-compliant from creation. This module
computes the right values once and produces pre-formatted comment
blocks for templates to splice in.

Templates use the pre-formatted blocks (``spdx_md``, ``spdx_hash``,
``spdx_slash``) rather than building the lines themselves so that:

1. The comment style stays correct for the file type.
2. UNLICENSED / unrecognized licenses skip the
   ``SPDX-License-Identifier`` line cleanly.
3. The year, copyright holder, and license id are computed once.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Placeholders that look like a license but are NOT valid SPDX
# identifiers — for these, we still emit SPDX-FileCopyrightText
# (attribution is machine-readable) but suppress
# SPDX-License-Identifier. Everything else is passed through to the
# header verbatim, on the theory that an obscure-but-real SPDX id
# (`GPL-3.0-only`, `Unlicense`, `0BSD`, ...) should not be silently
# dropped just because we forgot to add it to an allowlist; if the
# caller mistypes, `reuse lint` will surface it loudly.
NON_SPDX_PLACEHOLDERS: frozenset[str] = frozenset({
    "UNLICENSED",
    "Proprietary",
    "PROPRIETARY",
    "None",
    "TBD",
    "TODO",
})

DEFAULT_COPYRIGHT_HOLDER = "The AIDA Core Authors"
DEFAULT_LICENSE_ID = "MPL-2.0"


def current_year() -> str:
    """Year for SPDX-FileCopyrightText headers.

    Honors ``SOURCE_DATE_EPOCH`` for reproducible builds (Nix,
    Reproducible Builds project). Otherwise uses today's UTC year.
    """
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    if epoch:
        try:
            return str(
                datetime.fromtimestamp(int(epoch), tz=timezone.utc).year
            )
        except (ValueError, OverflowError, OSError):
            pass
    return str(datetime.now(timezone.utc).year)


def has_spdx_license_id(license_id: str) -> bool:
    """Return True if ``license_id`` should be emitted in headers."""
    return bool(license_id) and license_id not in NON_SPDX_PLACEHOLDERS


def detect_spdx_from_plugin_path(
    plugin_path: str | Path | None,
) -> dict[str, str]:
    """Best-effort SPDX context derived from a target plugin's metadata.

    Reads ``<plugin_path>/.claude-plugin/plugin.json``; if present,
    derives ``copyright_holder`` from the plugin's display name
    (``"The {Display Name} Authors"``) and ``license_id`` from the
    ``license`` field. Returns only the keys it can fill — caller
    merges into a wider context.
    """
    out: dict[str, str] = {}
    if not plugin_path:
        return out
    plugin_json = Path(plugin_path) / ".claude-plugin" / "plugin.json"
    if not plugin_json.is_file():
        return out
    try:
        data = json.loads(plugin_json.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return out
    if isinstance(data, dict):
        name = data.get("name")
        if isinstance(name, str) and name:
            display = name.replace("-", " ").replace("_", " ").title()
            out["copyright_holder"] = f"The {display} Authors"
        license_id = data.get("license")
        if isinstance(license_id, str) and license_id:
            out["license_id"] = license_id
    return out


def resolve_spdx_context(context: dict[str, Any]) -> dict[str, str]:
    """Return ``{year, copyright_holder, license_id}`` for templating.

    Honors explicit context overrides first, then falls back to
    sensible defaults. Callers (plugin-manager scaffolding,
    extension creation, etc.) should pass any caller-provided
    values via ``context`` and let this fill the gaps.
    """
    license_id = context.get("license_id") or DEFAULT_LICENSE_ID
    holder = (
        context.get("copyright_holder")
        or context.get("author_name")
        or DEFAULT_COPYRIGHT_HOLDER
    )
    return {
        "year": context.get("year") or current_year(),
        "copyright_holder": holder,
        "license_id": license_id,
    }


def render_spdx_blocks(spdx: dict[str, str]) -> dict[str, str]:
    """Return pre-formatted comment blocks for the three styles.

    Each block ends with a single trailing newline so templates can
    splice it in without adding their own. For UNLICENSED (or any
    non-SPDX license id), only the copyright line is emitted — the
    license-identifier line is suppressed because there is no valid
    SPDX expression to put there.

    Block keys:
        spdx_md      ``<!-- ... -->`` style for Markdown
        spdx_hash    ``# ...`` style for Python / shell / YAML / Make
        spdx_slash   ``// ...`` style for TypeScript / JavaScript
    """
    year = spdx["year"]
    holder = spdx["copyright_holder"]
    license_id = spdx["license_id"]
    emit_license_line = has_spdx_license_id(license_id)

    def _block(prefix: str, suffix: str) -> str:
        # REUSE-IgnoreStart
        lines = [f"{prefix}SPDX-FileCopyrightText: {year} {holder}{suffix}"]
        if emit_license_line:
            lines.append(
                f"{prefix}SPDX-License-Identifier: {license_id}{suffix}"
            )
        return "\n".join(lines) + "\n"
        # REUSE-IgnoreEnd

    return {
        "spdx_md": _block("<!-- ", " -->"),
        "spdx_hash": _block("# ", ""),
        "spdx_slash": _block("// ", ""),
    }


def spdx_template_variables(context: dict[str, Any]) -> dict[str, Any]:
    """One-shot helper combining ``resolve_spdx_context`` and blocks.

    Returns a dict suitable for merging into Jinja2 template
    variables. Includes both the raw fields (``year``,
    ``copyright_holder``, ``license_id``) and the pre-formatted
    blocks (``spdx_md``, ``spdx_hash``, ``spdx_slash``).
    """
    spdx = resolve_spdx_context(context)
    return {**spdx, **render_spdx_blocks(spdx)}
