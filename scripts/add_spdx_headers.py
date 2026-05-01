#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 The AIDA Core Authors
# SPDX-License-Identifier: MPL-2.0
"""Add SPDX-FileCopyrightText/SPDX-License-Identifier headers to source files.

Idempotent: files that already contain ``SPDX-License-Identifier`` are skipped.
Operates on tracked files only (``git ls-files``) and respects a built-in
skip list for fixtures, JSON, lockfiles, generated artifacts, and
scaffolding templates (those are covered by ``.reuse/dep5`` instead).

Run from repo root::

    python3 scripts/add_spdx_headers.py        # dry-run; prints planned changes
    python3 scripts/add_spdx_headers.py --apply # actually write changes
"""

from __future__ import annotations

import argparse
import fnmatch
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

COPYRIGHT_HOLDER = "The AIDA Core Authors"
LICENSE_ID = "MPL-2.0"
YEAR = "2026"

# Substrings that indicate a header is already present.
SENTINEL = "SPDX-License-Identifier"

# fnmatch patterns evaluated against POSIX-style relative paths.
# Files matching any of these are NOT touched. dep5 covers the licensing.
SKIP_PATTERNS: tuple[str, ...] = (
    # Skip list documented in CONTRIBUTING.md#licensing
    "LICENSE",
    "AUTHORS",
    ".gitignore",
    "**/.gitignore",
    "**/.gitkeep",
    # JSON has no comment syntax
    "*.json",
    "**/*.json",
    "*.json.template",
    "**/*.json.template",
    # Test fixtures (sample-project trees simulate user repos)
    "tests/fixtures/**",
    "tests/integration/*/sample-project/**",
    # Scaffolding templates — covered by dep5 so renderers control output
    "**/*.jinja2",
    "**/*.template",
)


@dataclass(frozen=True)
class CommentStyle:
    line_prefix: str          # what each header line starts with
    line_suffix: str = ""     # what each header line ends with
    blank_line: str = ""      # blank line representation (with suffix if needed)


HASH = CommentStyle(line_prefix="# ")
HTML = CommentStyle(line_prefix="<!-- ", line_suffix=" -->")


def comment_style_for(path: Path) -> CommentStyle | None:
    """Return the comment style for a path, or None if it should be skipped.

    Caller must already have applied SKIP_PATTERNS.
    """
    name = path.name
    suffix = path.suffix.lower()

    if suffix == ".md":
        return HTML
    if suffix in {".py", ".sh", ".yml", ".yaml", ".toml"}:
        return HASH
    if suffix == ".txt" and name.startswith("requirements"):
        return HASH
    if name in {"Makefile", "Dockerfile"} or name.startswith("Makefile."):
        return HASH
    if path.as_posix().endswith(".github/CODEOWNERS"):
        return HASH
    return None


def should_skip(rel_path: str) -> bool:
    return any(fnmatch.fnmatch(rel_path, pat) for pat in SKIP_PATTERNS)


def render_header(style: CommentStyle) -> list[str]:
    # REUSE-IgnoreStart
    return [
        f"{style.line_prefix}SPDX-FileCopyrightText: {YEAR} {COPYRIGHT_HOLDER}{style.line_suffix}",
        f"{style.line_prefix}SPDX-License-Identifier: {LICENSE_ID}{style.line_suffix}",
    ]
    # REUSE-IgnoreEnd


def find_insertion_point(lines: list[str], style: CommentStyle) -> int:
    """Return the line index at which the header should be inserted.

    For HASH style, skip a leading shebang. For HTML style (markdown), skip a
    leading YAML frontmatter block delimited by ``---`` on the first line.
    """
    if not lines:
        return 0

    if style is HASH and lines[0].startswith("#!"):
        return 1

    if style is HTML and lines[0].rstrip() == "---":
        # Find the closing --- of frontmatter
        for idx in range(1, len(lines)):
            if lines[idx].rstrip() == "---":
                return idx + 1
        # Malformed frontmatter (no close): bail to top
        return 0

    return 0


def insert_header(lines: list[str], style: CommentStyle) -> list[str]:
    """Return new file lines with the SPDX header inserted at the right spot."""
    insertion = find_insertion_point(lines, style)
    header = render_header(style)

    # Build the inserted block: blank line if needed before header, then
    # header lines, then blank line before the rest of the content.
    block: list[str] = []

    needs_leading_blank = (
        insertion > 0 and lines[insertion - 1].strip() != ""
    )
    if needs_leading_blank:
        block.append("")

    block.extend(header)

    if insertion < len(lines) and lines[insertion].strip() != "":
        block.append("")

    return lines[:insertion] + block + lines[insertion:]


def already_has_header(text: str) -> bool:
    return SENTINEL in text


def tracked_files() -> list[str]:
    out = subprocess.check_output(["git", "ls-files"], text=True)
    return [line for line in out.splitlines() if line]


def process(repo_root: Path, apply: bool) -> int:
    changed: list[str] = []
    skipped_no_style: list[str] = []
    skipped_pattern: list[str] = []
    already: list[str] = []

    for rel in tracked_files():
        if should_skip(rel):
            skipped_pattern.append(rel)
            continue
        path = repo_root / rel
        if not path.is_file():
            continue
        style = comment_style_for(path)
        if style is None:
            skipped_no_style.append(rel)
            continue
        text = path.read_text(encoding="utf-8")
        if already_has_header(text):
            already.append(rel)
            continue

        # Preserve final newline status by working with split lines.
        ends_with_newline = text.endswith("\n")
        lines = text.split("\n")
        if ends_with_newline:
            # split leaves a trailing empty string for the final newline; drop it
            lines = lines[:-1]

        new_lines = insert_header(lines, style)
        new_text = "\n".join(new_lines) + ("\n" if ends_with_newline else "")

        if apply:
            path.write_text(new_text, encoding="utf-8")
        changed.append(rel)

    print(f"Files that would be updated: {len(changed)}")
    for rel in changed:
        print(f"  + {rel}")
    print(f"Already had headers: {len(already)}")
    print(f"Skipped (no comment style for type): {len(skipped_no_style)}")
    print(f"Skipped (matches skip pattern): {len(skipped_pattern)}")
    if not apply:
        print("\nDry run — re-run with --apply to write changes.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true",
                        help="actually write changes (default: dry run)")
    args = parser.parse_args()
    repo_root = Path(__file__).resolve().parent.parent
    return process(repo_root, apply=args.apply)


if __name__ == "__main__":
    sys.exit(main())
