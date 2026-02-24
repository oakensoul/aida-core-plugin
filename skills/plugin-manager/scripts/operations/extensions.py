"""Plugin extension management operations.

Handles create, validate, version, and list operations for
Claude Code plugins. Plugins use JSON metadata (plugin.json)
rather than YAML frontmatter like agents and skills.

Supports two-phase orchestration:
- Phase 1: get_questions() - Gather context, return questions
- Phase 2: execute() with responses - Validate and write files
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .utils import (
    bump_version,
    get_location_path,
    render_template,
)

from shared.extension_utils import (
    execute_create_from_agent as _execute_create_from_agent,
    execute_extension,
    execute_extension_list,
    execute_extension_validate,
    get_extension_questions,
    validate_agent_output,  # noqa: F401  re-exported
)

# Plugin configuration
PLUGIN_CONFIG: Dict[str, Any] = {
    "entity_label": "plugin",
    "directory": ".claude-plugin",
    "file_pattern": "plugin.json",
    "frontmatter_type": None,  # plugins use JSON, not frontmatter
    "create_subdirs": [],
    "main_file_filter": None,  # skip frontmatter validation
}


# ------------------------------------------------------------------
# Discovery helpers (plugin-specific: JSON-based)
# ------------------------------------------------------------------


def find_components(
    location: str = "all",
    plugin_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Find all plugin components.

    Plugins use a different discovery mechanism from agents/skills:
    they look for ``.claude-plugin/plugin.json`` inside subdirectories.

    Args:
        location: Where to search (user, project, plugin, all)
        plugin_path: Path to plugin directory (if location is
            plugin)

    Returns:
        List of plugin info dictionaries
    """
    components: List[Dict[str, Any]] = []

    locations_to_search: List[str] = []
    if location == "all":
        locations_to_search = ["user", "project"]
        if plugin_path:
            locations_to_search.append("plugin")
    else:
        locations_to_search = [location]

    for loc in locations_to_search:
        base_path = get_location_path(loc, plugin_path)
        search_dir = base_path

        if not search_dir.exists():
            continue

        for item in search_dir.iterdir():
            if item.is_dir():
                plugin_json = (
                    item / ".claude-plugin" / "plugin.json"
                )
                if plugin_json.exists():
                    try:
                        with open(plugin_json) as f:
                            data = json.load(f)
                        components.append(
                            {
                                "name": data.get(
                                    "name", item.name
                                ),
                                "version": data.get(
                                    "version", "0.0.0"
                                ),
                                "description": data.get(
                                    "description", ""
                                ),
                                "location": loc,
                                "path": str(item),
                            }
                        )
                    except (json.JSONDecodeError, IOError):
                        pass

    return components


def component_exists(
    name: str,
    location: str,
    plugin_path: Optional[str] = None,
) -> bool:
    """Check if a plugin with the given name already exists.

    Args:
        name: Plugin name
        location: Where to check
        plugin_path: Path to plugin directory

    Returns:
        True if plugin exists
    """
    components = find_components(location, plugin_path)
    return any(c["name"] == name for c in components)


# ------------------------------------------------------------------
# Phase 1: get_questions
# ------------------------------------------------------------------


def get_questions(
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """Analyze context and return questions (Phase 1).

    Args:
        context: Operation context containing:
            - operation: create, validate, version, list
            - description: (for create) plugin description
            - name: (for validate/version) plugin name
            - location: user, project, plugin (default: user)
            - plugin_path: path to plugin (if location is plugin)

    Returns:
        Dictionary with questions, inferred values, and
        validation results
    """
    return get_extension_questions(
        PLUGIN_CONFIG,
        context,
        find_fn=find_components,
        exists_fn=component_exists,
    )


# ------------------------------------------------------------------
# Plugin-specific execution helpers
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
    """Execute plugin creation.

    Creates a plugin directory structure with .claude-plugin/,
    agents/, skills/, and metadata files.

    Args:
        name: Plugin name
        description: Plugin description
        version: Initial version
        tags: List of tags
        location: Where to create (user, project, plugin)
        templates_dir: Path to extension templates directory
        plugin_path: Path to plugin directory

    Returns:
        Result dictionary with success status and details
    """
    base_path = get_location_path(location, plugin_path)

    output_dir = base_path / name
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create subdirectories
    (output_dir / ".claude-plugin").mkdir(exist_ok=True)
    (output_dir / "agents").mkdir(exist_ok=True)
    (output_dir / "skills").mkdir(exist_ok=True)

    # Render plugin.json
    template_vars = {
        "name": name,
        "description": description,
        "version": version,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    try:
        content = render_template(
            templates_dir,
            "plugin.json.jinja2",
            template_vars,
        )
        plugin_json = (
            output_dir / ".claude-plugin" / "plugin.json"
        )
        plugin_json.write_text(content, encoding="utf-8")
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to render template: {e}",
        }

    # Create README
    try:
        readme_content = render_template(
            templates_dir,
            "README.md.jinja2",
            template_vars,
        )
        (output_dir / "README.md").write_text(
            readme_content, encoding="utf-8"
        )
    except Exception:
        pass  # README is optional

    # Create .gitignore
    try:
        gitignore_content = render_template(
            templates_dir,
            "gitignore.jinja2",
            template_vars,
        )
        (output_dir / ".gitignore").write_text(
            gitignore_content, encoding="utf-8"
        )
    except Exception:
        pass  # .gitignore is optional

    return {
        "success": True,
        "message": (
            f"Created plugin '{name}' at {output_dir}"
        ),
        "files_created": [
            str(
                output_dir
                / ".claude-plugin"
                / "plugin.json"
            ),
            str(output_dir / "README.md"),
        ],
        "path": str(output_dir),
    }


def execute_validate(
    name: Optional[str] = None,
    validate_all: bool = False,
    location: str = "all",
    plugin_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute plugin validation.

    Validates plugin.json metadata (JSON-based, not frontmatter).

    Args:
        name: Specific plugin name (or None for all)
        validate_all: Whether to validate all plugins
        location: Where to search
        plugin_path: Path to plugin directory

    Returns:
        Result dictionary with validation results
    """
    return execute_extension_validate(
        PLUGIN_CONFIG,
        name,
        validate_all,
        location,
        plugin_path,
        find_fn=find_components,
    )


def execute_version(
    name: str,
    bump_type: str = "patch",
    location: str = "all",
    plugin_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute version bump for a plugin.

    Updates the version field in plugin.json (JSON-based).

    Args:
        name: Plugin name
        bump_type: Type of version bump (major, minor, patch)
        location: Where to search
        plugin_path: Path to plugin directory

    Returns:
        Result dictionary with version update details
    """
    components = find_components(location, plugin_path)
    component = next(
        (c for c in components if c["name"] == name), None
    )

    if not component:
        return {
            "success": False,
            "message": f"Plugin '{name}' not found",
        }

    old_version = component["version"]
    new_version = bump_version(old_version, bump_type)

    # Plugin version is in plugin.json (JSON format)
    plugin_json_path = (
        Path(component["path"])
        / ".claude-plugin"
        / "plugin.json"
    )

    try:
        content = plugin_json_path.read_text(
            encoding="utf-8"
        )
        data = json.loads(content)
        data["version"] = new_version
        new_content = json.dumps(data, indent=2)
        plugin_json_path.write_text(
            new_content, encoding="utf-8"
        )

        return {
            "success": True,
            "message": (
                f"Updated {name} from "
                f"{old_version} to {new_version}"
            ),
            "old_version": old_version,
            "new_version": new_version,
            "path": str(plugin_json_path),
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to update version: {e}",
        }


def execute_list(
    location: str = "all",
    plugin_path: Optional[str] = None,
    output_format: str = "table",
) -> Dict[str, Any]:
    """Execute plugin listing.

    Args:
        location: Where to search (user, project, plugin, all)
        plugin_path: Path to plugin directory
        output_format: Output format (table, json)

    Returns:
        Result dictionary with plugin list
    """
    return execute_extension_list(
        PLUGIN_CONFIG,
        location,
        plugin_path,
        output_format,
        find_fn=find_components,
    )


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
    """Execute plugin creation from agent output (Phase 3).

    Args:
        agent_output: JSON output from the agent
        base_path: Base path where files should be created
        location: Location type (user, project, plugin)
        plugin_path: Path to plugin directory

    Returns:
        Result dictionary with success status and details
    """
    return _execute_create_from_agent(
        PLUGIN_CONFIG,
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
    """Execute the requested operation (Phase 2/3).

    Handles two modes:
    1. Template-based creation (legacy): Uses templates_dir
    2. Agent-based creation (new): Uses agent_output

    Args:
        context: Operation context
        responses: User responses to questions (if any)
        templates_dir: Path to extension templates directory

    Returns:
        Result dictionary
    """
    return execute_extension(
        PLUGIN_CONFIG,
        context,
        responses,
        templates_dir,
        find_fn=find_components,
        create_fn=execute_create,
        version_fn=execute_version,
    )
