"""Unit tests for the project-context SKILL.md.jinja2 template.

Verifies that the rendered template produces clean markdown output
without lint violations (no 'None' literals, no consecutive blank
lines, correct conditional section handling).
"""

import sys
import unittest
from pathlib import Path

# Add shared scripts to path
_project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_project_root / "scripts"))
sys.path.insert(0, str(_project_root / "skills" / "aida" / "scripts"))

from shared.utils import render_template  # noqa: E402
from utils.template_renderer import render_template as sandbox_render  # noqa: E402

TEMPLATES_DIR = _project_root / "skills" / "aida" / "templates"
TEMPLATE_NAME = "blueprints/project-context/SKILL.md.jinja2"
TEMPLATE_PATH = TEMPLATES_DIR / TEMPLATE_NAME


def _base_vars(**overrides: str) -> dict[str, str]:
    """Return a complete set of template variables with sensible defaults.

    All values are strings, matching the contract enforced by
    validate_template_variables() in configure.py.
    """
    base: dict[str, str] = {
        "project_name": "test-project",
        "project_type": "CLI tool or utility",
        "languages": "Python",
        "vcs": "git",
        "uses_worktrees": "",
        "branching_model": "GitHub Flow",
        "has_readme": "false",
        "readme_file": "README.md",
        "readme_length": "0",
        "has_license": "false",
        "license_file": "LICENSE",
        "has_gitignore": "false",
        "has_changelog": "false",
        "changelog_files": "",
        "changelog_intent": "",
        "has_contributing": "false",
        "has_docs_directory": "false",
        "docs_directory": "docs",
        "docs_directory_intent": "README.md only",
        "has_tests": "false",
        "test_directories": "",
        "src_directories": "",
        "has_dockerfile": "false",
        "has_docker_compose": "false",
        "has_ci_cd": "false",
        "has_github_actions": "false",
        "has_gitlab_ci": "false",
        "has_package_json": "false",
        "has_requirements_txt": "false",
        "has_pyproject_toml": "false",
        "has_gemfile": "false",
        "has_go_mod": "false",
        "has_cargo_toml": "false",
        "tools": "ruff, pytest",
        "testing_framework": "pytest",
        "testing_framework_intent": "pytest",
        "testing_approach": "Unit tests",
        "issue_tracking": "",
        "project_conventions": "",
        "api_docs_intent": "",
        "github_project_config": "",
        "jira_config": "",
        "confluence_config": "",
        "uses_docker": "false",
        "docker_compose_intent": "Not configured",
        "ci_cd_intent": "Not configured",
        "uses_confluence": "false",
        "coding_standards": "",
        "code_organization": "Modular",
        "documentation_level": "Standard",
        "timestamp": "2026-01-01T00:00:00",
    }
    base.update(overrides)
    return base


def _render(**overrides: str) -> str:
    """Render the project-context template with optional overrides."""
    return render_template(TEMPLATES_DIR, TEMPLATE_NAME, _base_vars(**overrides))


class TestProjectContextTemplateAllTrue(unittest.TestCase):
    """Test rendering with all has_* flags set to 'true'."""

    def setUp(self) -> None:
        self.output = _render(
            has_readme="true",
            has_license="true",
            has_gitignore="true",
            has_changelog="true",
            changelog_files="CHANGELOG.md",
            has_contributing="true",
            has_docs_directory="true",
            has_tests="true",
            test_directories="tests",
            src_directories="src",
            has_dockerfile="true",
            has_docker_compose="true",
            has_ci_cd="true",
            has_github_actions="true",
            has_package_json="true",
            uses_docker="true",
            coding_standards="ruff",
            issue_tracking="GitHub Issues",
            project_conventions="Follow PEP 8",
            api_docs_intent="Inline docstrings",
            readme_length="1500",
        )

    def test_no_none_literal(self) -> None:
        """Output must not contain the string literal 'None' as a value."""
        # Allow 'None' inside phrases like "None detected" or "None configured"
        # but not standalone or as "N, o, n, e" (the join-over-chars bug)
        self.assertNotIn("N, o, n, e", self.output)

    def test_has_project_name(self) -> None:
        self.assertIn("test-project", self.output)

    def test_has_changelog_entry(self) -> None:
        self.assertIn("CHANGELOG.md", self.output)

    def test_has_readme_entry(self) -> None:
        self.assertIn("README.md", self.output)
        self.assertIn("1500 chars", self.output)

    def test_has_license_entry(self) -> None:
        self.assertIn("`LICENSE`", self.output)

    def test_has_contributing_entry(self) -> None:
        self.assertIn("Contributing guide", self.output)

    def test_has_docker_section(self) -> None:
        self.assertIn("Dockerfile: ✓", self.output)

    def test_has_github_actions(self) -> None:
        self.assertIn("GitHub Actions", self.output)

    def test_has_issue_tracking(self) -> None:
        self.assertIn("GitHub Issues", self.output)

    def test_has_conventions(self) -> None:
        self.assertIn("Follow PEP 8", self.output)


class TestProjectContextTemplateAllFalse(unittest.TestCase):
    """Test rendering with all has_* flags set to 'false'."""

    def setUp(self) -> None:
        self.output = _render()

    def test_no_none_literal_as_chars(self) -> None:
        self.assertNotIn("N, o, n, e", self.output)

    def test_conditional_sections_excluded(self) -> None:
        """Sections guarded by 'false' flags must not appear."""
        self.assertNotIn("Contributing guide", self.output)
        self.assertNotIn(".gitignore: ✓", self.output)

    def test_license_none_detected(self) -> None:
        self.assertIn("License:** None detected", self.output)

    def test_readme_not_found(self) -> None:
        self.assertIn("README:** Not found", self.output)

    def test_docker_not_used(self) -> None:
        self.assertIn("Docker:** Not used", self.output)

    def test_issue_tracking_none_configured(self) -> None:
        self.assertIn("Issue Tracking:** None configured", self.output)


class TestProjectContextTemplateWhitespace(unittest.TestCase):
    """Test markdown whitespace rules (MD012)."""

    def test_no_triple_blank_lines_all_true(self) -> None:
        output = _render(
            has_readme="true",
            has_license="true",
            has_gitignore="true",
            has_changelog="true",
            changelog_files="CHANGELOG.md",
            has_contributing="true",
            has_docs_directory="true",
            has_tests="true",
            has_ci_cd="true",
            has_github_actions="true",
            uses_docker="true",
            has_dockerfile="true",
            readme_length="500",
        )
        self.assertNotRegex(output, r"\n{4,}")

    def test_no_triple_blank_lines_all_false(self) -> None:
        output = _render()
        self.assertNotRegex(output, r"\n{4,}")

    def test_no_trailing_whitespace_lines(self) -> None:
        """Lines should not have trailing spaces (MD009)."""
        output = _render(
            has_readme="true",
            has_license="true",
            readme_length="500",
        )
        for i, line in enumerate(output.split("\n"), 1):
            # Skip empty lines
            if line.strip():
                self.assertEqual(
                    line.rstrip(),
                    line,
                    f"Line {i} has trailing whitespace: {line!r}",
                )


class TestSandboxedRenderer(unittest.TestCase):
    """Test using the production SandboxedEnvironment renderer.

    This is the actual code path used by configure.py via
    template_renderer.py, which previously lacked trim_blocks
    and lstrip_blocks settings.
    """

    def _sandbox_render(self, **overrides: str) -> str:
        return sandbox_render(TEMPLATE_PATH, _base_vars(**overrides))

    def test_no_triple_blank_lines_all_true(self) -> None:
        output = self._sandbox_render(
            has_readme="true",
            has_license="true",
            has_gitignore="true",
            has_changelog="true",
            changelog_files="CHANGELOG.md",
            has_contributing="true",
            has_docs_directory="true",
            has_tests="true",
            has_ci_cd="true",
            has_github_actions="true",
            uses_docker="true",
            has_dockerfile="true",
            readme_length="500",
            coding_standards="ruff",
            issue_tracking="GitHub Issues",
        )
        self.assertNotRegex(output, r"\n{4,}")

    def test_no_triple_blank_lines_all_false(self) -> None:
        output = self._sandbox_render()
        self.assertNotRegex(output, r"\n{4,}")

    def test_no_triple_blank_lines_mixed(self) -> None:
        """Marketplace-like project: no Docker, no tests, no docs dir."""
        output = self._sandbox_render(
            has_readme="true",
            has_license="true",
            has_gitignore="true",
            has_changelog="false",
            has_contributing="false",
            has_docs_directory="false",
            has_tests="false",
            has_dockerfile="false",
            has_docker_compose="false",
            has_ci_cd="true",
            has_github_actions="true",
            has_package_json="true",
            uses_docker="false",
            issue_tracking="GitHub Issues",
            readme_length="2500",
        )
        self.assertNotRegex(output, r"\n{4,}")

    def test_no_none_literal(self) -> None:
        output = self._sandbox_render()
        self.assertNotIn("N, o, n, e", output)

    def test_boolean_false_excluded(self) -> None:
        output = self._sandbox_render()
        self.assertNotIn(".gitignore: ✓", output)
        self.assertNotIn("Contributing guide", output)


if __name__ == "__main__":
    unittest.main()
