"""Generator operations for plugin scaffolding.

Functions for creating directory structures, rendering templates,
and initializing git repositories for new plugin projects.
"""

import subprocess
from pathlib import Path
from typing import Any

from shared.utils import render_template


def create_directory_structure(target: Path, language: str) -> list[str]:
    """Create the directory structure for a new plugin project.

    Args:
        target: Target directory path
        language: "python" or "typescript"

    Returns:
        List of created directory paths (relative to target)
    """
    dirs = [
        ".claude-plugin",
        ".github/workflows",
        "agents",
        "skills",
        "docs",
    ]

    if language == "python":
        dirs.extend([
            "scripts",
            "tests",
        ])
    elif language == "typescript":
        dirs.extend([
            "src",
            "tests",
        ])

    created = []
    for d in dirs:
        dir_path = target / d
        dir_path.mkdir(parents=True, exist_ok=True)
        created.append(d)

    return created


def render_shared_files(
    target: Path, variables: dict[str, Any], templates_dir: Path
) -> list[str]:
    """Render language-independent template files.

    Args:
        target: Target directory path
        variables: Template variables
        templates_dir: Path to templates directory

    Returns:
        List of created file paths (relative to target)
    """
    shared_templates = {
        "shared/plugin.json.jinja2": ".claude-plugin/plugin.json",
        "shared/marketplace.json.jinja2": ".claude-plugin/marketplace.json",
        "shared/aida-config.json.jinja2": ".claude-plugin/aida-config.json",
        "shared/claude-md.jinja2": "CLAUDE.md",
        "shared/readme.md.jinja2": "README.md",
        "shared/markdownlint.json.jinja2": ".markdownlint.json",
        "shared/yamllint.yml.jinja2": ".yamllint.yml",
        "shared/frontmatter-schema.json.jinja2": ".frontmatter-schema.json",
    }

    created = []
    for template_name, output_path in shared_templates.items():
        content = render_template(templates_dir, template_name, variables)
        file_path = target / output_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)
        created.append(output_path)

    return created


def render_python_files(
    target: Path, variables: dict[str, Any], templates_dir: Path
) -> list[str]:
    """Render Python-specific template files.

    Args:
        target: Target directory path
        variables: Template variables
        templates_dir: Path to templates directory

    Returns:
        List of created file paths (relative to target)
    """
    python_templates = {
        "python/pyproject.toml.jinja2": "pyproject.toml",
        "python/python-version.jinja2": ".python-version",
        "python/conftest.py.jinja2": "tests/conftest.py",
        "python/ci.yml.jinja2": ".github/workflows/ci.yml",
    }

    created = []
    for template_name, output_path in python_templates.items():
        content = render_template(templates_dir, template_name, variables)
        file_path = target / output_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)
        created.append(output_path)

    return created


def render_typescript_files(
    target: Path, variables: dict[str, Any], templates_dir: Path
) -> list[str]:
    """Render TypeScript-specific template files.

    Args:
        target: Target directory path
        variables: Template variables
        templates_dir: Path to templates directory

    Returns:
        List of created file paths (relative to target)
    """
    ts_templates = {
        "typescript/package.json.jinja2": "package.json",
        "typescript/tsconfig.json.jinja2": "tsconfig.json",
        "typescript/eslint.config.mjs.jinja2": "eslint.config.mjs",
        "typescript/prettierrc.json.jinja2": ".prettierrc.json",
        "typescript/nvmrc.jinja2": ".nvmrc",
        "typescript/vitest.config.ts.jinja2": "vitest.config.ts",
        "typescript/index.ts.jinja2": "src/index.ts",
        "typescript/index.test.ts.jinja2": "tests/index.test.ts",
        "typescript/ci.yml.jinja2": ".github/workflows/ci.yml",
    }

    created = []
    for template_name, output_path in ts_templates.items():
        content = render_template(templates_dir, template_name, variables)
        file_path = target / output_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)
        created.append(output_path)

    return created


def render_stub_agent(
    target: Path,
    name: str,
    description: str,
    ccm_templates_dir: Path,
    timestamp: str = "",
) -> list[str]:
    """Render an agent stub using claude-code-management templates.

    Args:
        target: Target directory path
        name: Agent name (kebab-case)
        description: Agent description
        ccm_templates_dir: Path to claude-code-management templates directory
        timestamp: ISO 8601 timestamp for generated metadata

    Returns:
        List of created file paths (relative to target)
    """
    if not timestamp:
        from datetime import datetime, timezone
        timestamp = datetime.now(timezone.utc).isoformat()

    variables = {
        "name": name,
        "description": description,
        "version": "0.1.0",
        "tags": ["custom"],
        "timestamp": timestamp,
    }

    content = render_template(ccm_templates_dir, "agent/agent.md.jinja2", variables)

    agent_dir = target / "agents" / name
    agent_dir.mkdir(parents=True, exist_ok=True)

    agent_file = agent_dir / f"{name}.md"
    agent_file.write_text(content)

    # Create knowledge directory with index
    knowledge_dir = agent_dir / "knowledge"
    knowledge_dir.mkdir(parents=True, exist_ok=True)

    index_file = knowledge_dir / "index.md"
    index_file.write_text(
        f"---\ntype: reference\ntitle: {name} Knowledge Index\n---\n\n"
        f"# {name.replace('-', ' ').title()} Knowledge\n\n"
        "Add knowledge documents here.\n"
    )

    return [
        f"agents/{name}/{name}.md",
        f"agents/{name}/knowledge/index.md",
    ]


def render_stub_skill(
    target: Path,
    name: str,
    description: str,
    language: str,
    ccm_templates_dir: Path,
    timestamp: str = "",
) -> list[str]:
    """Render a skill stub using claude-code-management templates.

    Args:
        target: Target directory path
        name: Skill name (kebab-case)
        description: Skill description
        language: "python" or "typescript"
        ccm_templates_dir: Path to claude-code-management templates directory
        timestamp: ISO 8601 timestamp for generated metadata

    Returns:
        List of created file paths (relative to target)
    """
    if not timestamp:
        from datetime import datetime, timezone
        timestamp = datetime.now(timezone.utc).isoformat()

    script_extension = ".py" if language == "python" else ".ts"

    variables = {
        "name": name,
        "description": description,
        "version": "0.1.0",
        "tags": ["custom"],
        "timestamp": timestamp,
        "script_extension": script_extension,
    }

    content = render_template(ccm_templates_dir, "skill/SKILL.md.jinja2", variables)

    skill_dir = target / "skills" / name
    skill_dir.mkdir(parents=True, exist_ok=True)

    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(content)

    # Create scripts and references directories with .gitkeep
    for subdir in ("scripts", "references"):
        d = skill_dir / subdir
        d.mkdir(parents=True, exist_ok=True)
        (d / ".gitkeep").write_text("")

    return [
        f"skills/{name}/SKILL.md",
        f"skills/{name}/scripts/.gitkeep",
        f"skills/{name}/references/.gitkeep",
    ]


def assemble_gitignore(
    target: Path, language: str, templates_dir: Path
) -> str:
    """Assemble a .gitignore file from shared + language-specific blocks.

    Args:
        target: Target directory path
        language: "python" or "typescript"
        templates_dir: Path to templates directory

    Returns:
        Path to created .gitignore file (relative to target)
    """
    parts = []

    # Shared block
    shared_content = render_template(
        templates_dir, "shared/gitignore-shared.jinja2", {}
    )
    parts.append(shared_content)

    # Language-specific block
    if language == "python":
        lang_content = render_template(
            templates_dir, "python/gitignore-python.jinja2", {}
        )
    else:
        lang_content = render_template(
            templates_dir, "typescript/gitignore-node.jinja2", {}
        )
    parts.append(lang_content)

    gitignore_path = target / ".gitignore"
    gitignore_path.write_text("\n".join(parts))

    return ".gitignore"


def assemble_makefile(
    target: Path, language: str, variables: dict[str, Any], templates_dir: Path
) -> str:
    """Assemble a Makefile from header + language-specific targets.

    Args:
        target: Target directory path
        language: "python" or "typescript"
        variables: Template variables
        templates_dir: Path to templates directory

    Returns:
        Path to created Makefile (relative to target)
    """
    parts = []

    # Header with shared lint targets
    header = render_template(
        templates_dir, "shared/makefile-header.jinja2", variables
    )
    parts.append(header)

    # Language-specific targets
    if language == "python":
        lang_targets = render_template(
            templates_dir, "python/makefile-python.jinja2", variables
        )
    else:
        lang_targets = render_template(
            templates_dir, "typescript/makefile-typescript.jinja2", variables
        )
    parts.append(lang_targets)

    makefile_path = target / "Makefile"
    makefile_path.write_text("\n".join(parts))

    return "Makefile"


def initialize_git(target: Path) -> bool:
    """Initialize a git repository in the target directory.

    Args:
        target: Target directory path

    Returns:
        True if git init succeeded
    """
    try:
        result = subprocess.run(
            ["git", "init"],
            cwd=target,
            capture_output=True, text=True, timeout=10
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def create_initial_commit(target: Path) -> bool:
    """Create the initial commit in the scaffolded repository.

    Args:
        target: Target directory path

    Returns:
        True if commit succeeded
    """
    try:
        # Stage all files
        add_result = subprocess.run(
            ["git", "add", "."],
            cwd=target,
            capture_output=True, text=True, timeout=10
        )
        if add_result.returncode != 0:
            return False

        # Create initial commit
        commit_result = subprocess.run(
            ["git", "commit", "-m", "Initial scaffold from aida-core create-plugin"],
            cwd=target,
            capture_output=True, text=True, timeout=10
        )
        return commit_result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False
