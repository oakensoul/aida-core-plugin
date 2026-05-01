# SPDX-FileCopyrightText: 2026 The AIDA Core Authors
# SPDX-License-Identifier: MPL-2.0

"""Tests that extension-manager scaffolding emits SPDX headers.

Verifies the leverage point of issue #73: a downstream plugin author
running agent-manager / skill-manager scaffolding ends up with a
reuse-compliant artifact without having to think about SPDX headers
themselves.
"""

# REUSE-IgnoreStart — assertions reference literal SPDX strings.

import sys
from pathlib import Path
from unittest.mock import patch

# Reset cached operations modules so this file's manager imports
# don't conflict with other test files using a different manager.
# shared.* is intentionally left intact.
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

_AGENT_TEMPLATES = _project_root / "skills" / "agent-manager" / "templates"
_SKILL_TEMPLATES = _project_root / "skills" / "skill-manager" / "templates"


def _create_agent(tmp_path, **overrides):
    """Run agent execute_create against a tempdir and return content."""
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
            templates_dir=_AGENT_TEMPLATES,
        )
    assert result["success"], result.get("message")
    return Path(result["path"]).read_text()


def _create_skill(tmp_path, **overrides):
    """Run skill execute_create against a tempdir and return content.

    Imports skill-manager separately because it shares the
    ``operations`` package name with agent-manager / plugin-manager
    / etc. We have to (a) drop their cached ``operations.*`` and
    ``_paths`` modules, (b) put skill-manager's scripts dir at
    sys.path[0], and (c) invalidate importlib's finder cache so
    Python doesn't reuse the previously-resolved plugin-manager
    location on import.
    """
    import importlib

    for mod_name in list(sys.modules):
        if (
            mod_name == "operations"
            or mod_name.startswith("operations.")
            or mod_name == "_paths"
        ):
            del sys.modules[mod_name]

    skill_scripts = str(
        _project_root / "skills" / "skill-manager" / "scripts"
    )
    if skill_scripts in sys.path:
        sys.path.remove(skill_scripts)
    sys.path.insert(0, skill_scripts)
    importlib.invalidate_caches()

    from operations.extensions import execute_create as skill_create

    base = tmp_path / ".claude"
    with patch(
        "shared.extension_utils.get_location_path",
        return_value=base,
    ):
        result = skill_create(
            name=overrides.get("name", "test-skill"),
            description=overrides.get(
                "description", "A skill used to test SPDX emission"
            ),
            version=overrides.get("version", "0.1.0"),
            tags=overrides.get("tags", ["core"]),
            location="project",
            templates_dir=_SKILL_TEMPLATES,
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


class TestSkillCreateEmitsSpdx:
    def test_emits_copyright_after_frontmatter(self, tmp_path):
        content = _create_skill(tmp_path)
        assert content.lstrip().startswith("---")
        frontmatter_end = content.find("\n---\n", 1)
        assert frontmatter_end > 0
        body = content[frontmatter_end:]
        assert "<!-- SPDX-FileCopyrightText:" in body

    def test_emits_default_license_id(self, tmp_path):
        content = _create_skill(tmp_path)
        assert "SPDX-License-Identifier: MPL-2.0" in content

# REUSE-IgnoreEnd
