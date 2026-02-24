"""Agent management operations for Claude Code.

Handles create, validate, version, and list operations
for agent (subagent) definitions. Agents are Markdown files
with YAML frontmatter stored under ``agents/{name}/{name}.md``
with an accompanying ``knowledge/`` subdirectory.

Supports three-phase orchestration:
- Phase 1: get_questions() -- gather context, infer metadata
- Phase 2: Agent generates content (handled by orchestrator)
- Phase 3: execute() with agent_output -- validate and write
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from .utils import (
    infer_from_description,  # noqa: F401  re-exported for tests
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
    validate_agent_output,  # noqa: F401  re-exported
    validate_file_frontmatter as _validate_file_frontmatter,
)

# Agent component configuration
AGENT_CONFIG: Dict[str, Any] = {
    "entity_label": "agent",
    "directory": "agents",
    "file_pattern": "{name}/{name}.md",
    "template": "agent/agent.md.jinja2",
    "frontmatter_type": "agent",
    "create_subdirs": ["knowledge"],
    "main_file_filter": lambda p: (
        p.endswith(".md") and "/knowledge/" not in p
    ),
}


# ------------------------------------------------------------------
# Discovery helpers
# ------------------------------------------------------------------


def find_agents(
    location: str = "all",
    plugin_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Find all agent definitions.

    Args:
        location: Where to search (user, project, plugin, all)
        plugin_path: Path to plugin directory (if location
            is plugin)

    Returns:
        List of agent info dictionaries
    """
    return find_extensions(
        AGENT_CONFIG, location, plugin_path
    )


def agent_exists(
    name: str,
    location: str,
    plugin_path: Optional[str] = None,
) -> bool:
    """Check if an agent with the given name already exists.

    Args:
        name: Agent name
        location: Where to check
        plugin_path: Path to plugin directory

    Returns:
        True if agent exists
    """
    agents = find_agents(location, plugin_path)
    return any(a["name"] == name for a in agents)


# ------------------------------------------------------------------
# Phase 1: get_questions
# ------------------------------------------------------------------


def get_questions(
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """Analyze context and return questions needing user input.

    Args:
        context: Operation context containing:
            - operation: create, validate, version, list
            - description: (for create) agent description
            - name: (for validate/version) agent name
            - location: user, project, plugin (default: user)
            - plugin_path: path to plugin (if location is
              plugin)

    Returns:
        Dictionary containing questions, inferred values,
        validation results, and project_context (for create).
    """
    return get_extension_questions(AGENT_CONFIG, context)


# ------------------------------------------------------------------
# Frontmatter validation
# ------------------------------------------------------------------


def validate_file_frontmatter(
    content: str,
) -> Dict[str, Any]:
    """Validate frontmatter in an agent file.

    Args:
        content: File content

    Returns:
        Dictionary with validation results
    """
    return _validate_file_frontmatter(content, "agent")


# ------------------------------------------------------------------
# Agent output validation (Phase 3 support)
# ------------------------------------------------------------------

# validate_agent_output is imported from shared and
# re-exported directly (see imports above).


def execute_create_from_agent(
    agent_output: Dict[str, Any],
    base_path: str,
    location: str = "user",
    plugin_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute agent creation from agent output (Phase 3).

    Args:
        agent_output: JSON output from the agent containing
            files to create
        base_path: Base path where files should be created
        location: Location type (user, project, plugin)
        plugin_path: Path to plugin directory

    Returns:
        Result dictionary with success status and details
    """
    return _execute_create_from_agent(
        AGENT_CONFIG,
        agent_output,
        base_path,
        location,
        plugin_path,
    )


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
    """Execute agent creation using a Jinja2 template.

    Args:
        name: Agent name
        description: Agent description
        version: Initial version
        tags: List of tags
        location: Where to create (user, project, plugin)
        templates_dir: Path to templates directory
        plugin_path: Path to plugin directory

    Returns:
        Result dictionary with success status and details
    """
    return execute_extension_create(
        AGENT_CONFIG,
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
    """Execute agent validation.

    Args:
        name: Specific agent name (or None for all)
        validate_all: Whether to validate all agents
        location: Where to search
        plugin_path: Path to plugin directory

    Returns:
        Result dictionary with validation results
    """
    return execute_extension_validate(
        AGENT_CONFIG,
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
    """Execute version bump for an agent.

    Args:
        name: Agent name
        bump_type: Type of version bump (major, minor, patch)
        location: Where to search
        plugin_path: Path to plugin directory

    Returns:
        Result dictionary with version update details
    """
    return execute_extension_version(
        AGENT_CONFIG,
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
    """Execute agent listing.

    Args:
        location: Where to search (user, project, plugin,
            all)
        plugin_path: Path to plugin directory
        output_format: Output format (table, json)

    Returns:
        Result dictionary with agent list
    """
    return execute_extension_list(
        AGENT_CONFIG,
        location,
        plugin_path,
        output_format,
    )


# ------------------------------------------------------------------
# Phase 2/3: execute
# ------------------------------------------------------------------


def execute(
    context: Dict[str, Any],
    responses: Dict[str, Any],
    templates_dir: Path,
) -> Dict[str, Any]:
    """Execute the requested agent operation.

    Handles two modes for create:
    1. Template-based creation (legacy): uses templates_dir
    2. Agent-based creation (new): uses agent_output

    Args:
        context: Operation context
        responses: User responses to questions (if any)
        templates_dir: Path to templates directory

    Returns:
        Result dictionary
    """
    return execute_extension(
        AGENT_CONFIG,
        context,
        responses,
        templates_dir,
    )
