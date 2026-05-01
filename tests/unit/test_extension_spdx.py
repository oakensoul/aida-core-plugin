# SPDX-FileCopyrightText: 2026 The AIDA Core Authors
# SPDX-License-Identifier: MPL-2.0

"""Tests that the agent-manager scaffolding emits SPDX headers.

Verifies the leverage point of issue #73: a downstream plugin author
running the agent-manager scaffolding ends up with a reuse-compliant
agent file without having to think about SPDX headers themselves.
"""

# REUSE-IgnoreStart — assertions reference literal SPDX strings.

import json
import sys
from pathlib import Path
from unittest.mock import patch

# Reset cached operations modules so this file's agent-manager
# imports don't conflict with other test files using a different
# manager. shared.* is intentionally left intact.
for _mod_name in list(sys.modules):
    if (
        _mod_name == "operations"
        or _mod_name.startswith("operations.")
        or _mod_name == "_paths"
    ):
        del sys.modules[_mod_name]

_project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_project_root / "scripts"))
sys.path.insert(
    0, str(_project_root / "skills" / "agent-manager" / "scripts"),
)

from operations.extensions import execute_create  # noqa: E402

_TEMPLATES = _project_root / "skills" / "agent-manager" / "templates"


def _create_agent(tmp_path, **overrides):
    """Run execute_create against a tempdir and return the file content."""
    base = tmp_path / ".claude"
    with patch(
        "shared.extension_utils.get_location_path",
        return_value=base,
    ):
        result = execute_create(
            name=overrides.get("name", "test-agent"),
            description=overrides.get(
                "description", "An agent used to test SPDX emission"
            ),
            version=overrides.get("version", "0.1.0"),
            tags=overrides.get("tags", ["core"]),
            location="project",
            templates_dir=_TEMPLATES,
        )
    assert result["success"], result.get("message")
    return Path(result["path"]).read_text()


class TestAgentCreateEmitsSpdx:
    def test_emits_copyright_header_after_frontmatter(self, tmp_path):
        content = _create_agent(tmp_path)
        # Frontmatter remains the first block.
        assert content.lstrip().startswith("---")
        # Copyright appears after the closing frontmatter --- marker.
        frontmatter_end = content.find("\n---\n", 1)
        assert frontmatter_end > 0
        body = content[frontmatter_end:]
        assert "SPDX-FileCopyrightText:" in body
        assert "<!-- SPDX-FileCopyrightText:" in body

    def test_emits_license_id(self, tmp_path):
        content = _create_agent(tmp_path)
        # Default license is MPL-2.0 — matches this repo's convention
        # and is a recognized SPDX identifier.
        assert "SPDX-License-Identifier: MPL-2.0" in content

    def test_uses_html_comment_style_for_markdown(self, tmp_path):
        content = _create_agent(tmp_path)
        # Markdown wraps SPDX in HTML comments; bare `# SPDX...` would
        # render as a Markdown heading, which we never want.
        assert "<!-- SPDX-FileCopyrightText:" in content
        assert "<!-- SPDX-License-Identifier:" in content


class TestAgentCreateDetectsDownstreamPluginCopyright:
    """Leverage-point regression: agent files must not get aida-core's attribution.

    When a downstream plugin author runs agent-manager against THEIR
    plugin (`--location plugin --plugin-path /path/to/their-plugin`),
    the generated agent file should carry their plugin's copyright
    + license, derived from their `.claude-plugin/plugin.json`.
    """

    def _make_target_plugin(self, plugin_root: Path, name: str, license_id: str):
        meta = plugin_root / ".claude-plugin"
        meta.mkdir(parents=True, exist_ok=True)
        (meta / "plugin.json").write_text(
            json.dumps({"name": name, "version": "0.1.0", "license": license_id})
        )

    def _create_in_plugin(self, plugin_path: Path) -> str:
        with patch(
            "shared.extension_utils.get_location_path",
            return_value=plugin_path,
        ):
            result = execute_create(
                name="my-agent",
                description="An agent created against a downstream plugin",
                version="0.1.0",
                tags=["core"],
                location="plugin",
                templates_dir=_TEMPLATES,
                plugin_path=str(plugin_path),
            )
        assert result["success"], result.get("message")
        return Path(result["path"]).read_text()

    def test_uses_downstream_plugin_copyright_holder(self, tmp_path):
        plugin_root = tmp_path / "their-plugin"
        plugin_root.mkdir()
        self._make_target_plugin(plugin_root, "their-cool-plugin", "Apache-2.0")
        content = self._create_in_plugin(plugin_root)
        # Should pick up "The Their Cool Plugin Authors", NOT aida-core's default
        assert "The Their Cool Plugin Authors" in content
        assert "The AIDA Core Authors" not in content

    def test_uses_downstream_plugin_license(self, tmp_path):
        plugin_root = tmp_path / "their-plugin"
        plugin_root.mkdir()
        self._make_target_plugin(plugin_root, "their-cool-plugin", "Apache-2.0")
        content = self._create_in_plugin(plugin_root)
        assert "SPDX-License-Identifier: Apache-2.0" in content
        # NOT MPL-2.0 (aida-core's default)
        assert "SPDX-License-Identifier: MPL-2.0" not in content

    def test_falls_back_when_plugin_json_missing(self, tmp_path):
        # No plugin.json in the target — falls back to aida-core's default.
        plugin_root = tmp_path / "bare-target"
        plugin_root.mkdir()
        content = self._create_in_plugin(plugin_root)
        assert "The AIDA Core Authors" in content

# REUSE-IgnoreEnd
