# SPDX-FileCopyrightText: 2026 The AIDA Core Authors
# SPDX-License-Identifier: MPL-2.0

"""Tests for shared.spdx — SPDX header helpers used by scaffolding."""

# REUSE-IgnoreStart — assertions reference literal SPDX strings.

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

_project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_project_root / "scripts"))

from shared.spdx import (  # noqa: E402
    DEFAULT_COPYRIGHT_HOLDER,
    DEFAULT_LICENSE_ID,
    NON_SPDX_PLACEHOLDERS,
    current_year,
    detect_spdx_from_plugin_path,
    has_spdx_license_id,
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

    def test_obscure_real_spdx_ids_are_not_dropped(self):
        # Identifiers like GPL-3.0-only, Unlicense, 0BSD, LGPL-3.0+
        # are valid SPDX expressions and must pass through. The
        # original allowlist would have silently dropped them.
        for license_id in (
            "GPL-3.0-only",
            "Unlicense",
            "0BSD",
            "LGPL-3.0-or-later",
            "AGPL-3.0+",
        ):
            blocks = render_spdx_blocks(self._spdx(license_id=license_id))
            self.assertIn(
                f"SPDX-License-Identifier: {license_id}",
                blocks["spdx_md"],
                f"{license_id} should be emitted, not silently dropped",
            )

    def test_placeholder_license_ids_suppress_line(self):
        # The full deny-list, not just UNLICENSED.
        for placeholder in ("Proprietary", "PROPRIETARY", "TBD", "TODO", "None"):
            blocks = render_spdx_blocks(self._spdx(license_id=placeholder))
            self.assertIn("SPDX-FileCopyrightText:", blocks["spdx_md"])
            self.assertNotIn(
                "SPDX-License-Identifier:",
                blocks["spdx_md"],
                f"{placeholder} is not a real SPDX id; line should be suppressed",
            )


class TestHasSpdxLicenseId(unittest.TestCase):
    def test_real_ids_pass_through(self):
        self.assertTrue(has_spdx_license_id("MIT"))
        self.assertTrue(has_spdx_license_id("GPL-3.0-only"))
        self.assertTrue(has_spdx_license_id("Unlicense"))

    def test_placeholders_rejected(self):
        for placeholder in NON_SPDX_PLACEHOLDERS:
            self.assertFalse(has_spdx_license_id(placeholder))

    def test_empty_rejected(self):
        self.assertFalse(has_spdx_license_id(""))


class TestCurrentYear(unittest.TestCase):
    def test_default_is_now_year(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("SOURCE_DATE_EPOCH", None)
            self.assertEqual(
                current_year(),
                str(datetime.now(timezone.utc).year),
            )

    def test_source_date_epoch_override(self):
        # Reproducible-builds convention: 1577836800 == 2020-01-01 UTC
        with patch.dict(os.environ, {"SOURCE_DATE_EPOCH": "1577836800"}):
            self.assertEqual(current_year(), "2020")

    def test_invalid_source_date_epoch_falls_back(self):
        with patch.dict(os.environ, {"SOURCE_DATE_EPOCH": "not-an-int"}):
            self.assertEqual(
                current_year(),
                str(datetime.now(timezone.utc).year),
            )


class TestDetectSpdxFromPluginPath(unittest.TestCase):
    def test_returns_empty_for_missing_path(self):
        self.assertEqual(detect_spdx_from_plugin_path(None), {})
        self.assertEqual(detect_spdx_from_plugin_path(""), {})

    def test_returns_empty_when_no_plugin_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(detect_spdx_from_plugin_path(tmp), {})

    def test_derives_holder_from_plugin_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            meta = Path(tmp) / ".claude-plugin"
            meta.mkdir()
            (meta / "plugin.json").write_text(
                json.dumps({"name": "my-cool-plugin", "version": "0.1.0"})
            )
            spdx = detect_spdx_from_plugin_path(tmp)
            self.assertEqual(spdx["copyright_holder"], "The My Cool Plugin Authors")

    def test_uses_license_field_from_plugin_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            meta = Path(tmp) / ".claude-plugin"
            meta.mkdir()
            (meta / "plugin.json").write_text(
                json.dumps({"name": "p", "license": "Apache-2.0"})
            )
            spdx = detect_spdx_from_plugin_path(tmp)
            self.assertEqual(spdx["license_id"], "Apache-2.0")

    def test_corrupt_plugin_json_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            meta = Path(tmp) / ".claude-plugin"
            meta.mkdir()
            (meta / "plugin.json").write_text("{not valid json")
            self.assertEqual(detect_spdx_from_plugin_path(tmp), {})


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
