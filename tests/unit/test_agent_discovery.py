"""Unit tests for agent discovery and CLAUDE.md routing generation.

This test suite covers agent discovery from project, user, and
plugin sources, frontmatter parsing, security checks, routing
section generation, and CLAUDE.md update logic.
"""

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# Add scripts directory to path for imports
sys.path.insert(
    0,
    str(
        Path(__file__).parent.parent.parent
        / "skills"
        / "aida-dispatch"
        / "scripts"
    ),
)

from utils.agents import (
    _BEGIN_MARKER,
    _END_MARKER,
    _SECTION_HEADER,
    _ensure_list,
    _find_agents_in_directory,
    _find_plugin_agents,
    _parse_managed_section,
    _read_agent_frontmatter,
    _safe_read_agent_file,
    discover_agents,
    generate_agent_routing_section,
    update_agent_routing,
)

# Valid agent frontmatter template
_VALID_FRONTMATTER = """\
---
type: agent
name: {name}
description: {description}
version: 0.1.0
tags:
  - core
  - test
skills:
  - skill-one
  - skill-two
model: claude-sonnet-4.5
---

# {name}

Agent body content.
"""


def _write_agent(base_dir, name, description=None):
    """Helper to create an agent file with valid frontmatter."""
    if description is None:
        description = f"Test agent {name}"
    agent_dir = base_dir / name
    agent_dir.mkdir(parents=True, exist_ok=True)
    agent_file = agent_dir / f"{name}.md"
    agent_file.write_text(
        _VALID_FRONTMATTER.format(
            name=name, description=description
        ),
        encoding="utf-8",
    )
    return agent_file


class TestAgentDiscovery(unittest.TestCase):
    """Test agent discovery from various sources."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_empty_directory_returns_empty_list(self):
        """Empty agents dir returns empty list."""
        agents_dir = self.temp_path / "agents"
        agents_dir.mkdir()
        result = _find_agents_in_directory(
            agents_dir, "project"
        )
        self.assertEqual(result, [])

    def test_valid_project_agent_discovered(self):
        """Valid project agent discovered with metadata."""
        agents_dir = self.temp_path / ".claude" / "agents"
        _write_agent(agents_dir, "my-agent", "My agent desc")

        result = _find_agents_in_directory(
            agents_dir, "project"
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "my-agent")
        self.assertEqual(
            result[0]["description"], "My agent desc"
        )
        self.assertEqual(result[0]["version"], "0.1.0")
        self.assertEqual(result[0]["source"], "project")
        self.assertIn("path", result[0])

    @patch("utils.agents.get_home_dir")
    def test_valid_user_agent_discovered(self, mock_home):
        """Valid user agent discovered."""
        mock_home.return_value = self.temp_path
        user_agents = self.temp_path / ".claude" / "agents"
        _write_agent(user_agents, "user-agent")

        agents = discover_agents(project_root=None)
        names = [a["name"] for a in agents]
        self.assertIn("user-agent", names)
        user = next(
            a for a in agents if a["name"] == "user-agent"
        )
        self.assertEqual(user["source"], "user")

    @patch("utils.agents.get_home_dir")
    def test_valid_plugin_agent_via_manifest(self, mock_home):
        """Plugin agents loaded via aida-config.json."""
        mock_home.return_value = self.temp_path

        # Create plugin cache structure
        plugin_root = (
            self.temp_path
            / ".claude"
            / "plugins"
            / "cache"
            / "owner"
            / "my-plugin"
        )
        meta_dir = plugin_root / ".claude-plugin"
        meta_dir.mkdir(parents=True)

        # Write aida-config.json with agents key
        config = {"agents": ["test-agent"]}
        (meta_dir / "aida-config.json").write_text(
            json.dumps(config), encoding="utf-8"
        )

        # Create agent file
        agents_dir = plugin_root / "agents"
        _write_agent(agents_dir, "test-agent")

        result = _find_plugin_agents(
            plugin_root, "my-plugin"
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "test-agent")
        self.assertEqual(
            result[0]["source"], "plugin:my-plugin"
        )

    @patch("utils.agents.get_home_dir")
    def test_plugin_fallback_to_directory_scan(
        self, mock_home
    ):
        """Plugin falls back to dir scan without agents key."""
        mock_home.return_value = self.temp_path

        plugin_root = (
            self.temp_path
            / ".claude"
            / "plugins"
            / "cache"
            / "owner"
            / "my-plugin"
        )
        meta_dir = plugin_root / ".claude-plugin"
        meta_dir.mkdir(parents=True)

        # aida-config.json without agents key
        config = {"config": {}}
        (meta_dir / "aida-config.json").write_text(
            json.dumps(config), encoding="utf-8"
        )

        # Create agent via directory convention
        agents_dir = plugin_root / "agents"
        _write_agent(agents_dir, "fallback-agent")

        result = _find_plugin_agents(
            plugin_root, "my-plugin"
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "fallback-agent")

    def test_tags_and_skills_parsed_as_lists(self):
        """Tags and skills are parsed as lists."""
        agents_dir = self.temp_path / "agents"
        _write_agent(agents_dir, "tagged-agent")

        result = _find_agents_in_directory(
            agents_dir, "project"
        )
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0]["tags"], list)
        self.assertEqual(
            result[0]["tags"], ["core", "test"]
        )
        self.assertIsInstance(result[0]["skills"], list)
        self.assertEqual(
            result[0]["skills"],
            ["skill-one", "skill-two"],
        )

    def test_symlinked_directory_rejected(self):
        """Symlinked agent directories are rejected."""
        agents_dir = self.temp_path / "agents"
        agents_dir.mkdir()

        # Create real agent elsewhere
        real_dir = self.temp_path / "real-agents" / "sym"
        real_dir.mkdir(parents=True)
        (real_dir / "sym.md").write_text(
            _VALID_FRONTMATTER.format(
                name="sym", description="Symlinked"
            ),
            encoding="utf-8",
        )

        # Symlink into agents dir
        (agents_dir / "sym").symlink_to(real_dir)

        result = _find_agents_in_directory(
            agents_dir, "project"
        )
        self.assertEqual(result, [])

    def test_symlinked_file_rejected(self):
        """Symlinked agent files are rejected."""
        agents_dir = self.temp_path / "agents" / "sym"
        agents_dir.mkdir(parents=True)

        # Create real file elsewhere
        real_file = self.temp_path / "real-agent.md"
        real_file.write_text(
            _VALID_FRONTMATTER.format(
                name="sym", description="Symlinked file"
            ),
            encoding="utf-8",
        )

        # Symlink the file
        (agents_dir / "sym.md").symlink_to(real_file)

        result = _read_agent_frontmatter(
            agents_dir / "sym.md"
        )
        self.assertIsNone(result)

    def test_oversized_file_rejected(self):
        """Agent files over 500 KB are rejected."""
        agents_dir = self.temp_path / "agents" / "big"
        agents_dir.mkdir(parents=True)
        big_file = agents_dir / "big.md"

        # Write file over 500 KB
        content = "---\nname: big\n---\n" + (
            "x" * (500 * 1024 + 1)
        )
        big_file.write_text(content, encoding="utf-8")

        result = _read_agent_frontmatter(big_file)
        self.assertIsNone(result)

    def test_invalid_yaml_frontmatter_skipped(self):
        """Invalid YAML in frontmatter is skipped."""
        agents_dir = self.temp_path / "agents" / "bad"
        agents_dir.mkdir(parents=True)
        bad_file = agents_dir / "bad.md"
        bad_file.write_text(
            "---\n: [invalid yaml\n---\n# Bad\n",
            encoding="utf-8",
        )

        result = _read_agent_frontmatter(bad_file)
        self.assertIsNone(result)

    def test_missing_required_fields_skipped(self):
        """Agents missing required fields are skipped."""
        agents_dir = self.temp_path / "agents" / "incomplete"
        agents_dir.mkdir(parents=True)
        incomplete = agents_dir / "incomplete.md"
        # Missing 'tags' field
        incomplete.write_text(
            "---\nname: incomplete\n"
            "description: No tags\n"
            "version: 0.1.0\n"
            "---\n# Incomplete\n",
            encoding="utf-8",
        )

        result = _read_agent_frontmatter(incomplete)
        self.assertIsNone(result)

    @patch("utils.agents.get_home_dir")
    def test_dedup_project_overrides_user(self, mock_home):
        """Project agents take priority over user agents."""
        mock_home.return_value = self.temp_path

        # Create same-named agent in both locations
        project_agents = (
            self.temp_path / "project" / ".claude" / "agents"
        )
        _write_agent(
            project_agents, "shared", "From project"
        )

        user_agents = self.temp_path / ".claude" / "agents"
        _write_agent(user_agents, "shared", "From user")

        project_root = self.temp_path / "project"
        agents = discover_agents(project_root)

        shared = [
            a for a in agents if a["name"] == "shared"
        ]
        self.assertEqual(len(shared), 1)
        self.assertEqual(
            shared[0]["description"], "From project"
        )
        self.assertEqual(shared[0]["source"], "project")

    @patch("utils.agents.get_home_dir")
    def test_multiple_sources_combined(self, mock_home):
        """Agents from all sources are combined."""
        mock_home.return_value = self.temp_path

        project_root = self.temp_path / "project"
        project_agents = (
            project_root / ".claude" / "agents"
        )
        _write_agent(project_agents, "proj-agent")

        user_agents = self.temp_path / ".claude" / "agents"
        _write_agent(user_agents, "user-agent")

        agents = discover_agents(project_root)
        names = {a["name"] for a in agents}
        self.assertIn("proj-agent", names)
        self.assertIn("user-agent", names)

    @patch("utils.agents._HAS_YAML", False)
    @patch("utils.agents.get_home_dir")
    def test_graceful_degradation_without_pyyaml(
        self, mock_home
    ):
        """Returns empty list when PyYAML unavailable."""
        mock_home.return_value = self.temp_path

        agents_dir = self.temp_path / ".claude" / "agents"
        _write_agent(agents_dir, "agent-a")

        agents = discover_agents(self.temp_path)
        self.assertEqual(agents, [])

    @patch("utils.agents.get_home_dir")
    def test_plugin_invalid_aida_config_falls_back(
        self, mock_home
    ):
        """Invalid JSON in aida-config falls back to scan."""
        mock_home.return_value = self.temp_path

        plugin_root = (
            self.temp_path
            / ".claude"
            / "plugins"
            / "cache"
            / "owner"
            / "bad-json"
        )
        meta_dir = plugin_root / ".claude-plugin"
        meta_dir.mkdir(parents=True)

        (meta_dir / "aida-config.json").write_text(
            "{invalid json", encoding="utf-8"
        )

        agents_dir = plugin_root / "agents"
        _write_agent(agents_dir, "fallback-agent")

        result = _find_plugin_agents(
            plugin_root, "bad-json"
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "fallback-agent")

    @patch("utils.agents.get_home_dir")
    def test_plugin_agents_key_not_list_falls_back(
        self, mock_home
    ):
        """Non-list agents key falls back to dir scan."""
        mock_home.return_value = self.temp_path

        plugin_root = (
            self.temp_path
            / ".claude"
            / "plugins"
            / "cache"
            / "owner"
            / "bad-key"
        )
        meta_dir = plugin_root / ".claude-plugin"
        meta_dir.mkdir(parents=True)

        config = {"agents": "not-a-list"}
        (meta_dir / "aida-config.json").write_text(
            json.dumps(config), encoding="utf-8"
        )

        agents_dir = plugin_root / "agents"
        _write_agent(agents_dir, "fallback-agent")

        result = _find_plugin_agents(
            plugin_root, "bad-key"
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "fallback-agent")

    @patch("utils.agents.get_home_dir")
    def test_plugin_non_string_agent_names_skipped(
        self, mock_home
    ):
        """Non-string entries in agents list are skipped."""
        mock_home.return_value = self.temp_path

        plugin_root = (
            self.temp_path
            / ".claude"
            / "plugins"
            / "cache"
            / "owner"
            / "mixed"
        )
        meta_dir = plugin_root / ".claude-plugin"
        meta_dir.mkdir(parents=True)

        config = {"agents": ["valid", 123, None]}
        (meta_dir / "aida-config.json").write_text(
            json.dumps(config), encoding="utf-8"
        )

        agents_dir = plugin_root / "agents"
        _write_agent(agents_dir, "valid")

        result = _find_plugin_agents(
            plugin_root, "mixed"
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "valid")

    def test_single_string_tags_coerced_to_list(self):
        """Single string tag is coerced to a list."""
        agents_dir = self.temp_path / "agents" / "single"
        agents_dir.mkdir(parents=True)
        (agents_dir / "single.md").write_text(
            "---\n"
            "type: agent\n"
            "name: single\n"
            "description: Single tag agent\n"
            "version: 0.1.0\n"
            "tags: solo-tag\n"
            "skills: solo-skill\n"
            "---\n# Single\n",
            encoding="utf-8",
        )

        result = _read_agent_frontmatter(
            agents_dir / "single.md"
        )
        self.assertIsNotNone(result)
        self.assertEqual(result["tags"], ["solo-tag"])
        self.assertEqual(result["skills"], ["solo-skill"])

    def test_optional_fields_default_correctly(self):
        """Missing optional fields use defaults."""
        agents_dir = self.temp_path / "agents" / "minimal"
        agents_dir.mkdir(parents=True)
        (agents_dir / "minimal.md").write_text(
            "---\n"
            "name: minimal\n"
            "description: Minimal\n"
            "version: 0.1.0\n"
            "tags:\n"
            "  - test\n"
            "---\n# Minimal\n",
            encoding="utf-8",
        )

        result = _read_agent_frontmatter(
            agents_dir / "minimal.md"
        )
        self.assertIsNotNone(result)
        self.assertEqual(result["skills"], [])
        self.assertIsNone(result["model"])

    def test_path_outside_root_rejected(self):
        """Files outside resolved root are rejected."""
        outside = self.temp_path / "outside.md"
        outside.write_text(
            _VALID_FRONTMATTER.format(
                name="evil", description="Evil"
            ),
            encoding="utf-8",
        )

        safe_root = self.temp_path / "safe"
        safe_root.mkdir()

        result = _safe_read_agent_file(
            outside,
            "test",
            resolved_root=safe_root.resolve(),
        )
        self.assertIsNone(result)

    def test_frontmatter_delimiter_in_yaml_value(self):
        """Closing --- inside YAML value is not a delimiter."""
        agents_dir = self.temp_path / "agents" / "multi"
        agents_dir.mkdir(parents=True)
        (agents_dir / "multi.md").write_text(
            "---\n"
            "name: multi\n"
            "description: |\n"
            "  line one\n"
            "  ---extra text\n"
            "  line three\n"
            "version: 0.1.0\n"
            "tags:\n"
            "  - test\n"
            "---\n\n# Multi\n",
            encoding="utf-8",
        )

        result = _read_agent_frontmatter(
            agents_dir / "multi.md"
        )
        self.assertIsNotNone(result)
        self.assertEqual(result["name"], "multi")
        self.assertIn("---extra text", result["description"])


class TestEnsureList(unittest.TestCase):
    """Test _ensure_list helper."""

    def test_list_passthrough(self):
        self.assertEqual(_ensure_list([1, 2]), [1, 2])

    def test_string_to_list(self):
        self.assertEqual(_ensure_list("val"), ["val"])

    def test_none_to_empty(self):
        self.assertEqual(_ensure_list(None), [])

    def test_int_to_empty(self):
        self.assertEqual(_ensure_list(123), [])

    def test_empty_list_passthrough(self):
        self.assertEqual(_ensure_list([]), [])


class TestRoutingGeneration(unittest.TestCase):
    """Test agent routing section generation."""

    def test_empty_list_returns_empty_string(self):
        """Empty agent list produces empty string."""
        result = generate_agent_routing_section([])
        self.assertEqual(result, "")

    def test_section_has_correct_markers(self):
        """Section contains begin and end markers."""
        agents = [
            {
                "name": "test",
                "description": "Test agent",
            }
        ]
        result = generate_agent_routing_section(agents)
        self.assertIn(_BEGIN_MARKER, result)
        self.assertIn(_END_MARKER, result)
        self.assertIn(_SECTION_HEADER, result)

    def test_agent_descriptions_included(self):
        """Agent names and descriptions are included."""
        agents = [
            {
                "name": "alpha",
                "description": "Alpha agent",
            },
            {
                "name": "beta",
                "description": "Beta agent",
            },
        ]
        result = generate_agent_routing_section(agents)
        self.assertIn("**alpha**", result)
        self.assertIn("Alpha agent", result)
        self.assertIn("**beta**", result)
        self.assertIn("Beta agent", result)

    def test_agent_teams_guidance_included(self):
        """Agent Teams guidance section is included."""
        agents = [
            {
                "name": "test",
                "description": "Test",
            }
        ]
        result = generate_agent_routing_section(agents)
        self.assertIn("### Using Agent Teams", result)
        self.assertIn("team lead", result)


class TestClaudeMdUpdate(unittest.TestCase):
    """Test CLAUDE.md update logic."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _sample_agents(self, count=2):
        """Return sample agent dicts."""
        agents = []
        for i in range(count):
            agents.append(
                {
                    "name": f"agent-{i}",
                    "description": f"Agent {i} desc",
                    "version": "0.1.0",
                    "tags": ["test"],
                    "skills": [],
                    "model": None,
                    "source": "project",
                    "path": f"/fake/agent-{i}.md",
                }
            )
        return agents

    def test_creates_new_claude_md(self):
        """Creates CLAUDE.md when missing."""
        result = update_agent_routing(
            project_root=self.temp_path,
            agents=self._sample_agents(1),
        )
        self.assertTrue(result["success"])
        self.assertEqual(result["agents_count"], 1)

        md = (self.temp_path / "CLAUDE.md").read_text(
            encoding="utf-8"
        )
        self.assertIn(_BEGIN_MARKER, md)
        self.assertIn(_END_MARKER, md)
        self.assertIn("agent-0", md)

    def test_appends_to_existing(self):
        """Appends routing to existing CLAUDE.md."""
        claude_md = self.temp_path / "CLAUDE.md"
        claude_md.write_text(
            "# My Project\n\nExisting content.\n",
            encoding="utf-8",
        )

        result = update_agent_routing(
            project_root=self.temp_path,
            agents=self._sample_agents(1),
        )
        self.assertTrue(result["success"])

        md = claude_md.read_text(encoding="utf-8")
        self.assertIn("# My Project", md)
        self.assertIn("Existing content.", md)
        self.assertIn(_BEGIN_MARKER, md)

    def test_replaces_existing_section(self):
        """Replaces existing managed section idempotently."""
        claude_md = self.temp_path / "CLAUDE.md"
        agents_v1 = self._sample_agents(1)
        agents_v2 = [
            {
                "name": "new-agent",
                "description": "New agent desc",
                "version": "0.2.0",
                "tags": ["new"],
                "skills": [],
                "model": None,
                "source": "project",
                "path": "/fake/new-agent.md",
            }
        ]

        # First write
        update_agent_routing(
            project_root=self.temp_path,
            agents=agents_v1,
        )
        # Second write with different agents
        update_agent_routing(
            project_root=self.temp_path,
            agents=agents_v2,
        )

        md = claude_md.read_text(encoding="utf-8")
        self.assertIn("new-agent", md)
        self.assertNotIn("agent-0", md)
        # Only one set of markers
        self.assertEqual(md.count(_BEGIN_MARKER), 1)
        self.assertEqual(md.count(_END_MARKER), 1)

    def test_preserves_manual_content(self):
        """Content outside markers is preserved."""
        claude_md = self.temp_path / "CLAUDE.md"
        claude_md.write_text(
            "# Header\n\nManual content above.\n",
            encoding="utf-8",
        )

        update_agent_routing(
            project_root=self.temp_path,
            agents=self._sample_agents(1),
        )

        md = claude_md.read_text(encoding="utf-8")
        self.assertIn("# Header", md)
        self.assertIn("Manual content above.", md)
        self.assertIn(_BEGIN_MARKER, md)

        # Add content after markers manually
        md += "\n## Footer\n\nManual content below.\n"
        claude_md.write_text(md, encoding="utf-8")

        # Re-run update
        update_agent_routing(
            project_root=self.temp_path,
            agents=self._sample_agents(1),
        )

        md = claude_md.read_text(encoding="utf-8")
        self.assertIn("# Header", md)
        self.assertIn("Manual content above.", md)
        self.assertIn("## Footer", md)
        self.assertIn("Manual content below.", md)

    def test_no_duplication_on_rerun(self):
        """Re-running does not duplicate sections."""
        agents = self._sample_agents(2)
        update_agent_routing(
            project_root=self.temp_path, agents=agents
        )
        update_agent_routing(
            project_root=self.temp_path, agents=agents
        )

        md = (self.temp_path / "CLAUDE.md").read_text(
            encoding="utf-8"
        )
        self.assertEqual(md.count(_BEGIN_MARKER), 1)
        self.assertEqual(md.count(_END_MARKER), 1)
        self.assertEqual(md.count("agent-0"), 1)
        self.assertEqual(md.count("agent-1"), 1)

    def test_removed_agents_cleaned_up(self):
        """Agents removed from sources are cleaned up."""
        update_agent_routing(
            project_root=self.temp_path,
            agents=self._sample_agents(2),
        )

        md = (self.temp_path / "CLAUDE.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("agent-0", md)
        self.assertIn("agent-1", md)

        # Re-run with fewer agents
        update_agent_routing(
            project_root=self.temp_path,
            agents=self._sample_agents(1),
        )

        md = (self.temp_path / "CLAUDE.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("agent-0", md)
        self.assertNotIn("agent-1", md)

    def test_no_agents_no_changes(self):
        """No agents and no existing section = no changes."""
        result = update_agent_routing(
            project_root=self.temp_path, agents=[]
        )
        self.assertTrue(result["success"])
        self.assertIsNone(result["path"])
        self.assertFalse(
            (self.temp_path / "CLAUDE.md").exists()
        )

    def test_removed_all_agents_cleans_section(self):
        """Removing all agents removes the section."""
        claude_md = self.temp_path / "CLAUDE.md"
        claude_md.write_text(
            "# Header\n\nContent.\n",
            encoding="utf-8",
        )

        # Add agents
        update_agent_routing(
            project_root=self.temp_path,
            agents=self._sample_agents(1),
        )
        md = claude_md.read_text(encoding="utf-8")
        self.assertIn(_BEGIN_MARKER, md)

        # Remove all agents
        update_agent_routing(
            project_root=self.temp_path, agents=[]
        )
        md = claude_md.read_text(encoding="utf-8")
        self.assertNotIn(_BEGIN_MARKER, md)
        self.assertIn("# Header", md)
        self.assertIn("Content.", md)


class TestParseManagedSection(unittest.TestCase):
    """Test _parse_managed_section helper."""

    def test_no_markers_returns_none_managed(self):
        """Content without markers returns None managed."""
        content = "# Title\n\nSome content.\n"
        before, managed, after = _parse_managed_section(
            content
        )
        self.assertEqual(before, content)
        self.assertIsNone(managed)
        self.assertEqual(after, "")

    def test_markers_split_correctly(self):
        """Content with markers splits correctly."""
        content = (
            "# Title\n\n"
            f"{_SECTION_HEADER}\n\n"
            f"{_BEGIN_MARKER}\nRouting\n{_END_MARKER}\n\n"
            "## Footer\n"
        )
        before, managed, after = _parse_managed_section(
            content
        )
        self.assertEqual(before, "# Title\n\n")
        self.assertIsNotNone(managed)
        self.assertIn(_BEGIN_MARKER, managed)
        self.assertIn(_END_MARKER, managed)
        self.assertIn("## Footer", after)


if __name__ == "__main__":
    unittest.main()
