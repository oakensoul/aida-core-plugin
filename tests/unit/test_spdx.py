# SPDX-FileCopyrightText: 2026 The AIDA Core Authors
# SPDX-License-Identifier: MPL-2.0

"""Tests for shared.spdx — SPDX header helpers used by scaffolding."""

# REUSE-IgnoreStart — assertions reference literal SPDX strings.

from __future__ import annotations

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

_project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_project_root / "scripts"))

from shared.spdx import (  # noqa: E402
    DEFAULT_COPYRIGHT_HOLDER,
    DEFAULT_LICENSE_ID,
    KNOWN_SPDX_LICENSES,
    render_spdx_blocks,
    resolve_spdx_context,
    spdx_template_variables,
)


class TestResolveSpdxContext(unittest.TestCase):
    def test_defaults_when_context_empty(self):
        spdx = resolve_spdx_context({})
        self.assertEqual(spdx["copyright_holder"], DEFAULT_COPYRIGHT_HOLDER)
        self.assertEqual(spdx["license_id"], DEFAULT_LICENSE_ID)
        self.assertEqual(spdx["year"], str(datetime.now(timezone.utc).year))

    def test_explicit_overrides_win(self):
        spdx = resolve_spdx_context({
            "year": "1999",
            "copyright_holder": "Acme",
            "license_id": "Apache-2.0",
        })
        self.assertEqual(spdx, {
            "year": "1999",
            "copyright_holder": "Acme",
            "license_id": "Apache-2.0",
        })

    def test_falls_back_to_author_name_when_no_holder(self):
        spdx = resolve_spdx_context({"author_name": "Jane Doe"})
        self.assertEqual(spdx["copyright_holder"], "Jane Doe")


class TestRenderSpdxBlocks(unittest.TestCase):
    def _spdx(self, license_id="MPL-2.0"):
        return resolve_spdx_context({
            "year": "2026",
            "copyright_holder": "Acme",
            "license_id": license_id,
        })

    def test_md_block_uses_html_comments(self):
        blocks = render_spdx_blocks(self._spdx())
        self.assertIn(
            "<!-- SPDX-FileCopyrightText: 2026 Acme -->",
            blocks["spdx_md"],
        )
        self.assertIn(
            "<!-- SPDX-License-Identifier: MPL-2.0 -->",
            blocks["spdx_md"],
        )

    def test_hash_block_uses_pound_comments(self):
        blocks = render_spdx_blocks(self._spdx())
        self.assertIn("# SPDX-FileCopyrightText: 2026 Acme", blocks["spdx_hash"])
        self.assertIn("# SPDX-License-Identifier: MPL-2.0", blocks["spdx_hash"])

    def test_slash_block_uses_double_slash_comments(self):
        blocks = render_spdx_blocks(self._spdx())
        self.assertIn("// SPDX-FileCopyrightText: 2026 Acme", blocks["spdx_slash"])
        self.assertIn("// SPDX-License-Identifier: MPL-2.0", blocks["spdx_slash"])

    def test_unrecognized_license_suppresses_id_line(self):
        blocks = render_spdx_blocks(self._spdx(license_id="UNLICENSED"))
        # Copyright still emitted so attribution is machine-readable.
        self.assertIn("SPDX-FileCopyrightText: 2026 Acme", blocks["spdx_md"])
        # No SPDX-License-Identifier line because UNLICENSED isn't SPDX.
        for block_text in blocks.values():
            self.assertNotIn("SPDX-License-Identifier", block_text)

    def test_blocks_end_with_newline(self):
        blocks = render_spdx_blocks(self._spdx())
        for key, block in blocks.items():
            self.assertTrue(
                block.endswith("\n"),
                f"{key} should end with a newline so it splices cleanly",
            )

    def test_known_spdx_licenses_includes_common_set(self):
        for license_id in ("MIT", "Apache-2.0", "MPL-2.0", "GPL-3.0"):
            self.assertIn(license_id, KNOWN_SPDX_LICENSES)


class TestSpdxTemplateVariables(unittest.TestCase):
    def test_returns_raw_fields_and_blocks(self):
        out = spdx_template_variables({
            "copyright_holder": "Acme",
            "license_id": "MIT",
            "year": "2026",
        })
        self.assertEqual(out["copyright_holder"], "Acme")
        self.assertEqual(out["license_id"], "MIT")
        self.assertEqual(out["year"], "2026")
        self.assertIn("spdx_md", out)
        self.assertIn("spdx_hash", out)
        self.assertIn("spdx_slash", out)


if __name__ == "__main__":
    unittest.main()

# REUSE-IgnoreEnd
