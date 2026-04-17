"""Integration test: discover_agents -> filter_experts_by_role -> resolve_active_experts.

Exercises the full pipeline with real agent .md files on disk to verify
that expert-role propagates through agent discovery.
"""

import sys
import tempfile
from pathlib import Path

import yaml

# Add both aida scripts (for utils.agents) and expert-registry scripts
sys.path.insert(
    0,
    str(
        Path(__file__).parent.parent.parent
        / "skills"
        / "aida"
        / "scripts"
    ),
)
sys.path.insert(
    0,
    str(
        Path(__file__).parent.parent.parent
        / "skills"
        / "expert-registry"
        / "scripts"
    ),
)

from unittest.mock import patch

from expert_ops.registry import (  # noqa: E402
    filter_experts_by_role,
    load_experts_config,
    resolve_active_experts,
    save_experts_config,
)
from utils.agents import discover_agents  # noqa: E402


def _write_agent(base: Path, name: str, frontmatter: dict) -> Path:
    """Create a {name}/{name}.md agent file under base with YAML frontmatter."""
    agent_dir = base / name
    agent_dir.mkdir(parents=True, exist_ok=True)
    agent_file = agent_dir / f"{name}.md"

    fm = yaml.dump(frontmatter, default_flow_style=False)
    agent_file.write_text(f"---\n{fm}---\n\nAgent body.\n", encoding="utf-8")
    return agent_file


class TestExpertDiscoveryIntegration:
    """End-to-end: real .md files -> discover -> filter -> resolve."""

    def test_expert_role_propagates_through_discovery(self):
        """An agent with expert-role: core is discovered and filtered correctly."""
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            agents_dir = project_root / ".claude" / "agents"

            _write_agent(
                agents_dir,
                "security-reviewer",
                {
                    "name": "security-reviewer",
                    "description": "Reviews code for security issues",
                    "version": "1.0.0",
                    "tags": ["security"],
                    "expert-role": "core",
                },
            )
            _write_agent(
                agents_dir,
                "plain-agent",
                {
                    "name": "plain-agent",
                    "description": "A non-expert agent",
                    "version": "1.0.0",
                    "tags": ["general"],
                },
            )

            agents = discover_agents(project_root=project_root)

            # Both agents discovered
            names = {a["name"] for a in agents}
            assert "security-reviewer" in names
            assert "plain-agent" in names

            # expert-role propagated for the expert
            expert = next(a for a in agents if a["name"] == "security-reviewer")
            assert expert["expert-role"] == "core"

            # filter_experts_by_role keeps only the expert
            experts = filter_experts_by_role(agents)
            assert len(experts) == 1
            assert experts[0]["name"] == "security-reviewer"

    def test_full_pipeline_discover_filter_resolve(self):
        """Full pipeline: discover -> filter -> resolve with config."""
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            agents_dir = project_root / ".claude" / "agents"

            _write_agent(
                agents_dir,
                "code-reviewer",
                {
                    "name": "code-reviewer",
                    "description": "Reviews code quality",
                    "version": "1.0.0",
                    "tags": ["review"],
                    "expert-role": "core",
                },
            )
            _write_agent(
                agents_dir,
                "db-expert",
                {
                    "name": "db-expert",
                    "description": "Database expert",
                    "version": "1.0.0",
                    "tags": ["database"],
                    "expert-role": "domain",
                },
            )

            # Create a config that activates only code-reviewer
            config_path = project_root / ".claude" / "aida-project-context.yml"
            save_experts_config(
                path=config_path,
                active=["code-reviewer"],
            )

            # Run the full pipeline
            agents = discover_agents(project_root=project_root)
            experts = filter_experts_by_role(agents)
            config = load_experts_config(
                global_path=Path(tmp) / "nonexistent.yml",
                project_path=config_path,
            )
            active, dangling = resolve_active_experts(experts, config)

            assert len(active) == 1
            assert active[0]["name"] == "code-reviewer"
            assert active[0]["expert-role"] == "core"
            assert dangling == []

    def test_invalid_expert_role_filtered_out(self):
        """Agent with invalid expert-role value is excluded by filter."""
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            agents_dir = project_root / ".claude" / "agents"

            _write_agent(
                agents_dir,
                "bad-role-agent",
                {
                    "name": "bad-role-agent",
                    "description": "Has invalid role",
                    "version": "1.0.0",
                    "tags": ["test"],
                    "expert-role": "invalid-value",
                },
            )

            agents = discover_agents(project_root=project_root)
            experts = filter_experts_by_role(agents)

            assert len(experts) == 0

    @patch("utils.agents.get_home_dir")
    def test_union_merge_through_full_pipeline(self, mock_home):
        """Global + project experts are combined via union merge."""
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp) / "project"
            agents_dir = project_root / ".claude" / "agents"

            # Fake home with no agents (isolate from real home)
            fake_home = Path(tmp) / "fakehome"
            fake_home.mkdir()
            mock_home.return_value = fake_home

            _write_agent(
                agents_dir,
                "global-expert",
                {
                    "name": "global-expert",
                    "description": "A global baseline expert",
                    "version": "1.0.0",
                    "tags": ["review"],
                    "expert-role": "core",
                },
            )
            _write_agent(
                agents_dir,
                "project-expert",
                {
                    "name": "project-expert",
                    "description": "A project-specific expert",
                    "version": "1.0.0",
                    "tags": ["domain"],
                    "expert-role": "domain",
                },
            )

            # Global config activates one, project config the other
            global_config = Path(tmp) / "global.yml"
            save_experts_config(path=global_config, active=["global-expert"])

            project_config = project_root / ".claude" / "aida-project-context.yml"
            save_experts_config(path=project_config, active=["project-expert"])

            # Full pipeline
            agents = discover_agents(project_root=project_root)
            experts = filter_experts_by_role(agents)
            config = load_experts_config(
                global_path=global_config,
                project_path=project_config,
            )
            active, dangling = resolve_active_experts(experts, config)

            names = {e["name"] for e in active}
            assert "global-expert" in names
            assert "project-expert" in names
            assert config["source"] == "merged"
            assert dangling == []

    @patch("utils.agents.get_home_dir")
    def test_discovery_skips_user_and_plugin_dirs(self, mock_home):
        """With isolated tmp home, only project agents are found."""
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp) / "project"
            agents_dir = project_root / ".claude" / "agents"

            # Fake home with no agents
            fake_home = Path(tmp) / "fakehome"
            fake_home.mkdir()
            mock_home.return_value = fake_home

            _write_agent(
                agents_dir,
                "qa-agent",
                {
                    "name": "qa-agent",
                    "description": "QA reviewer",
                    "version": "1.0.0",
                    "tags": ["qa"],
                    "expert-role": "qa",
                },
            )

            agents = discover_agents(project_root=project_root)
            experts = filter_experts_by_role(agents)

            assert len(experts) == 1
            assert experts[0]["name"] == "qa-agent"
            assert experts[0]["expert-role"] == "qa"
