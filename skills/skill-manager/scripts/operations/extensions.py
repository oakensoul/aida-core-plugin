"""Skill management operations for Claude Code.

Handles create, validate, version, and list operations for skills.
Skills are process definitions with execution capabilities that follow
the Agent Skills open standard (agentskills.io).

Supports three-phase orchestration:
- Phase 1: get_questions() - Gather context, infer metadata
- Phase 2: Agent generates content (handled by orchestrator)
- Phase 3: execute() with agent_output - Validate and write files
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from .utils import (
    infer_from_description,  # noqa: F401  re-exported
)

from shared.extension_utils import (
    execute_create_from_agent as _execute_create_from_agent,
    execute_extension,
    execute_extension_create,
    execute_extension_list,
    execute_extension_validate,
    execute_extension_version,
    find_extensions,
    get_extension_questions,
    validate_file_frontmatter as _validate_file_frontmatter,
)

# Skill component configuration
SKILL_CONFIG: Dict[str, Any] = {
    "entity_label": "skill",
    "directory": "skills",
    "file_pattern": "{name}/SKILL.md",
    "template": "skill/SKILL.md.jinja2",
    "frontmatter_type": "skill",
    "create_subdirs": ["references", "scripts"],
    "main_file_filter": lambda p: p.endswith("SKILL.md"),
}


# ------------------------------------------------------------------
# Discovery helpers
# ------------------------------------------------------------------


def find_components(
    location: str = "all",
    plugin_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Find all skill components.

    Args:
        location: Where to search (user, project, plugin, all)
        plugin_path: Path to plugin directory (if location is
            plugin)

    Returns:
        List of skill info dictionaries
    """
    return find_extensions(
        SKILL_CONFIG, location, plugin_path
    )


def component_exists(
    name: str,
    location: str,
    plugin_path: Optional[str] = None,
) -> bool:
    """Check if a skill with the given name already exists.

    Args:
        name: Skill name
        location: Where to check
        plugin_path: Path to plugin directory

    Returns:
        True if skill exists
    """
    components = find_components(location, plugin_path)
    return any(c["name"] == name for c in components)


# ------------------------------------------------------------------
# Phase 1: get_questions
# ------------------------------------------------------------------


def get_questions(
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """Analyze context and return questions for user input (Phase 1).

    The component type is always "skill" - no type selection needed.

    Args:
        context: Operation context containing:
            - operation: create, validate, version, list
            - description: (for create) skill description
            - name: (for validate/version) skill name
            - location: user, project, plugin (default: user)
            - plugin_path: path to plugin (if location is plugin)

    Returns:
        Dictionary containing questions, inferred values,
        validation results, and project context.
    """
    return get_extension_questions(SKILL_CONFIG, context)


# ------------------------------------------------------------------
# Frontmatter validation
# ------------------------------------------------------------------


def validate_file_frontmatter(
    content: str,
) -> Dict[str, Any]:
    """Validate frontmatter in a skill file.

    Args:
        content: File content

    Returns:
        Dictionary with validation results
    """
    return _validate_file_frontmatter(content, "skill")


# ------------------------------------------------------------------
# Execution helpers (thin wrappers)
# ------------------------------------------------------------------


def execute_create(
    name: str,
    description: str,
    version: str,
    tags: List[str],
    location: str,
    templates_dir: Path,
    plugin_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute skill creation.

    Creates the skill directory with SKILL.md from template,
    plus references/ and scripts/ subdirectories.

    Args:
        name: Skill name
        description: Skill description
        version: Initial version
        tags: List of tags
        location: Where to create (user, project, plugin)
        templates_dir: Path to templates directory
        plugin_path: Path to plugin directory

    Returns:
        Result dictionary with success status and details
    """
    return execute_extension_create(
        SKILL_CONFIG,
        name,
        description,
        version,
        tags,
        location,
        templates_dir,
        plugin_path,
    )


def execute_validate(
    name: Optional[str] = None,
    validate_all: bool = False,
    location: str = "all",
    plugin_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute skill validation.

    Args:
        name: Specific skill name (or None for all)
        validate_all: Whether to validate all skills
        location: Where to search
        plugin_path: Path to plugin directory

    Returns:
        Result dictionary with validation results
    """
    return execute_extension_validate(
        SKILL_CONFIG,
        name,
        validate_all,
        location,
        plugin_path,
    )


def execute_version(
    name: str,
    bump_type: str = "patch",
    location: str = "all",
    plugin_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute version bump for a skill.

    Args:
        name: Skill name
        bump_type: Type of version bump (major, minor, patch)
        location: Where to search
        plugin_path: Path to plugin directory

    Returns:
        Result dictionary with version update details
    """
    return execute_extension_version(
        SKILL_CONFIG,
        name,
        bump_type,
        location,
        plugin_path,
    )


def execute_list(
    location: str = "all",
    plugin_path: Optional[str] = None,
    output_format: str = "table",
) -> Dict[str, Any]:
    """Execute skill listing.

    Args:
        location: Where to search (user, project, plugin, all)
        plugin_path: Path to plugin directory
        output_format: Output format (table, json)

    Returns:
        Result dictionary with skill list
    """
    return execute_extension_list(
        SKILL_CONFIG,
        location,
        plugin_path,
        output_format,
    )


def execute_create_from_agent(
    agent_output: Dict[str, Any],
    base_path: str,
    location: str = "user",
    plugin_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute skill creation from agent output (Phase 3).

    Args:
        agent_output: JSON output from the agent with files
        base_path: Base path where files should be created
        location: Location type (user, project, plugin)
        plugin_path: Path to plugin directory

    Returns:
        Result dictionary with success status and details
    """
    return _execute_create_from_agent(
        SKILL_CONFIG,
        agent_output,
        base_path,
        location,
        plugin_path,
    )


# ------------------------------------------------------------------
# Phase 2/3: execute
# ------------------------------------------------------------------


def execute(
    context: Dict[str, Any],
    responses: Dict[str, Any],
    templates_dir: Path,
) -> Dict[str, Any]:
    """Execute the requested skill operation (Phase 2/3).

    Handles two modes:
    1. Template-based creation (legacy): Uses templates_dir
    2. Agent-based creation (new): Uses agent_output

    Args:
        context: Operation context, may include:
            - agent_output: JSON from agent (Phase 3)
            - base_path: Where to create files
        responses: User responses to questions (if any)
        templates_dir: Path to templates directory

    Returns:
        Result dictionary
    """
    return execute_extension(
        SKILL_CONFIG,
        context,
        responses,
        templates_dir,
    )
