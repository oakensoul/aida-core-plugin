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

from datetime import datetime, timezone
from typing import Any

# License IDs we recognize as SPDX identifiers (subset of what
# plugin-manager scaffolds). UNLICENSED is handled specially —
# proprietary all-rights-reserved files still carry the copyright
# line but skip SPDX-License-Identifier (no SPDX id for proprietary).
KNOWN_SPDX_LICENSES = frozenset({
    "MIT",
    "Apache-2.0",
    "ISC",
    "GPL-3.0",
    "AGPL-3.0",
    "MPL-2.0",
    "BSD-2-Clause",
    "BSD-3-Clause",
})

DEFAULT_COPYRIGHT_HOLDER = "The AIDA Core Authors"
DEFAULT_LICENSE_ID = "MPL-2.0"


def current_year() -> str:
    return str(datetime.now(timezone.utc).year)


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
    has_spdx_license = license_id in KNOWN_SPDX_LICENSES

    def _block(prefix: str, suffix: str) -> str:
        # REUSE-IgnoreStart
        lines = [f"{prefix}SPDX-FileCopyrightText: {year} {holder}{suffix}"]
        if has_spdx_license:
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
