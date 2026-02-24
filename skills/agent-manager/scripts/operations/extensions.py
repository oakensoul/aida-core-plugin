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

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from .utils import (
    bump_version,
    detect_project_context,
    get_location_path,
    infer_from_description,
    render_template,
    to_kebab_case,
    validate_description,
    validate_name,
    validate_version,
)

# Agent component configuration
AGENT_CONFIG: Dict[str, Any] = {
    "directory": "agents",
    "file_pattern": "{name}/{name}.md",
    "template": "agent/agent.md.jinja2",
    "has_subdirectory": True,
    "frontmatter_type": "agent",
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
    agents: List[Dict[str, Any]] = []

    locations_to_search: List[str] = []
    if location == "all":
        locations_to_search = ["user", "project"]
        if plugin_path:
            locations_to_search.append("plugin")
    else:
        locations_to_search = [location]

    for loc in locations_to_search:
        base_path = get_location_path(loc, plugin_path)
        search_dir = base_path / AGENT_CONFIG["directory"]

        if not search_dir.exists():
            continue

        for md_file in search_dir.glob("**/*.md"):
            if (
                md_file.name.startswith("_")
                or md_file.name == "README.md"
            ):
                continue

            try:
                content = md_file.read_text(encoding="utf-8")
                if not content.startswith("---"):
                    continue

                end = content.find("---", 3)
                if end <= 0:
                    continue

                frontmatter_text = content[3:end].strip()
                frontmatter: Dict[str, str] = {}
                for line in frontmatter_text.split("\n"):
                    if (
                        ":" in line
                        and not line.strip().startswith("-")
                    ):
                        key, value = line.split(":", 1)
                        frontmatter[key.strip()] = (
                            value.strip().strip("\"'")
                        )

                if frontmatter.get("type") == "agent":
                    agents.append(
                        {
                            "name": frontmatter.get(
                                "name", md_file.stem
                            ),
                            "version": frontmatter.get(
                                "version", "0.0.0"
                            ),
                            "description": frontmatter.get(
                                "description", ""
                            ),
                            "location": loc,
                            "path": str(md_file),
                        }
                    )
            except (IOError, UnicodeDecodeError):
                pass

    return agents


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
    operation = context.get("operation", "create")
    location = context.get("location", "user")
    plugin_path = context.get("plugin_path")

    result: Dict[str, Any] = {
        "questions": [],
        "inferred": {},
        "validation": {"valid": True, "errors": []},
    }

    if operation == "create":
        description = context.get("description", "")
        result["project_context"] = detect_project_context()

        if not description:
            result["questions"].append(
                {
                    "id": "description",
                    "question": (
                        "What should this agent do? "
                        "(brief description)"
                    ),
                    "type": "text",
                    "required": True,
                    "help": (
                        "Describe the purpose of this agent"
                        " in 1-2 sentences"
                    ),
                }
            )
            return result

        inferred = infer_from_description(description)
        inferred["description"] = description
        inferred["base_path"] = str(
            get_location_path(location, plugin_path)
        )

        is_valid, error = validate_name(inferred["name"])
        if not is_valid:
            result["questions"].append(
                {
                    "id": "name",
                    "question": (
                        "What should this agent be named?"
                    ),
                    "type": "text",
                    "required": True,
                    "help": (
                        "Must be kebab-case "
                        f"(e.g., my-agent). Error: {error}"
                    ),
                    "default": (
                        inferred["name"][:50]
                        if inferred["name"]
                        else ""
                    ),
                }
            )

        if agent_exists(
            inferred["name"], location, plugin_path
        ):
            result["questions"].append(
                {
                    "id": "name",
                    "question": (
                        f"An agent named "
                        f"'{inferred['name']}' already "
                        "exists. Choose a different name:"
                    ),
                    "type": "text",
                    "required": True,
                    "help": (
                        "Must be unique within the location"
                    ),
                }
            )

        result["inferred"] = inferred

    elif operation == "validate":
        name = context.get("name")
        validate_all = context.get("all", False)

        if validate_all:
            agents = find_agents(location, plugin_path)
            result["inferred"] = {"components": agents}
        elif name:
            result["inferred"] = {"name": name}
        else:
            result["questions"].append(
                {
                    "id": "name",
                    "question": (
                        "Which agent do you want to"
                        " validate?"
                    ),
                    "type": "text",
                    "required": True,
                }
            )

    elif operation == "version":
        name = context.get("name")
        bump_type = context.get("bump", "patch")

        if not name:
            result["questions"].append(
                {
                    "id": "name",
                    "question": (
                        "Which agent do you want to"
                        " version?"
                    ),
                    "type": "text",
                    "required": True,
                }
            )

        result["inferred"] = {
            "name": name,
            "bump": bump_type,
        }

    elif operation == "list":
        result["inferred"] = {"location": location}

    return result


# ------------------------------------------------------------------
# Execution helpers
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
    base_path = get_location_path(location, plugin_path)
    component_dir = base_path / AGENT_CONFIG["directory"]
    file_path = component_dir / AGENT_CONFIG[
        "file_pattern"
    ].format(name=name)

    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Agents always get a knowledge/ subdirectory
    (file_path.parent / "knowledge").mkdir(exist_ok=True)

    template_vars = {
        "name": name,
        "description": description,
        "version": version,
        "tags": tags,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    try:
        content = render_template(
            templates_dir,
            AGENT_CONFIG["template"],
            template_vars,
        )
        file_path.write_text(content, encoding="utf-8")
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to render template: {e}",
        }

    return {
        "success": True,
        "message": (
            f"Created agent '{name}' at {file_path}"
        ),
        "files_created": [str(file_path)],
        "path": str(file_path),
    }


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
    agents = find_agents(location, plugin_path)

    if name and not validate_all:
        agents = [a for a in agents if a["name"] == name]
        if not agents:
            return {
                "success": False,
                "message": f"Agent '{name}' not found",
            }

    results: List[Dict[str, Any]] = []
    all_valid = True

    for agent in agents:
        errors: List[str] = []

        is_valid, error = validate_name(agent["name"])
        if not is_valid:
            errors.append(f"Name: {error}")

        is_valid, error = validate_description(
            agent.get("description", "")
        )
        if not is_valid:
            errors.append(f"Description: {error}")

        is_valid, error = validate_version(
            agent.get("version", "")
        )
        if not is_valid:
            errors.append(f"Version: {error}")

        if errors:
            all_valid = False

        results.append(
            {
                "name": agent["name"],
                "location": agent["location"],
                "path": agent["path"],
                "valid": len(errors) == 0,
                "errors": errors,
            }
        )

    valid_count = sum(1 for r in results if r["valid"])
    invalid_count = sum(
        1 for r in results if not r["valid"]
    )

    return {
        "success": True,
        "all_valid": all_valid,
        "results": results,
        "summary": (
            f"Validated {len(results)} agent(s): "
            f"{valid_count} valid, {invalid_count} invalid"
        ),
    }


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
    agents = find_agents(location, plugin_path)
    agent = next(
        (a for a in agents if a["name"] == name), None
    )

    if not agent:
        return {
            "success": False,
            "message": f"Agent '{name}' not found",
        }

    old_version = agent["version"]
    new_version = bump_version(old_version, bump_type)

    file_path = Path(agent["path"])

    try:
        content = file_path.read_text(encoding="utf-8")
        new_content = re.sub(
            r"(version:\s*)[\d.]+",
            f"\\g<1>{new_version}",
            content,
            count=1,
        )
        file_path.write_text(new_content, encoding="utf-8")

        return {
            "success": True,
            "message": (
                f"Updated {name} from "
                f"{old_version} to {new_version}"
            ),
            "old_version": old_version,
            "new_version": new_version,
            "path": str(file_path),
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
    """Execute agent listing.

    Args:
        location: Where to search (user, project, plugin,
            all)
        plugin_path: Path to plugin directory
        output_format: Output format (table, json)

    Returns:
        Result dictionary with agent list
    """
    agents = find_agents(location, plugin_path)

    return {
        "success": True,
        "components": agents,
        "count": len(agents),
        "format": output_format,
    }


# ------------------------------------------------------------------
# Agent output validation (Phase 3 support)
# ------------------------------------------------------------------


def validate_agent_output(
    agent_output: Dict[str, Any],
) -> Dict[str, Any]:
    """Validate the structure of agent output.

    Args:
        agent_output: The output from the agent

    Returns:
        Dictionary with validation results
    """
    errors: List[str] = []

    required_keys = ["validation", "files", "summary"]
    for key in required_keys:
        if key not in agent_output:
            errors.append(f"Missing required key: {key}")

    if errors:
        return {"valid": False, "errors": errors}

    validation = agent_output.get("validation", {})
    if "passed" not in validation:
        errors.append("validation.passed is required")
    if not isinstance(
        validation.get("issues", []), list
    ):
        errors.append("validation.issues must be a list")

    files = agent_output.get("files", [])
    if not isinstance(files, list):
        errors.append("files must be a list")
    else:
        for i, file_entry in enumerate(files):
            if not isinstance(file_entry, dict):
                errors.append(
                    f"files[{i}] must be an object"
                )
                continue
            if "path" not in file_entry:
                errors.append(
                    f"files[{i}].path is required"
                )
            if "content" not in file_entry:
                errors.append(
                    f"files[{i}].content is required"
                )
            path = file_entry.get("path", "")
            if ".." in path or path.startswith("/"):
                errors.append(
                    f"files[{i}].path contains invalid"
                    f" characters: {path}"
                )

    summary = agent_output.get("summary", {})
    if not isinstance(summary.get("created", []), list):
        errors.append("summary.created must be a list")
    if not isinstance(
        summary.get("next_steps", []), list
    ):
        errors.append(
            "summary.next_steps must be a list"
        )

    return {"valid": len(errors) == 0, "errors": errors}


def validate_file_frontmatter(
    content: str,
) -> Dict[str, Any]:
    """Validate frontmatter in an agent file.

    Args:
        content: File content

    Returns:
        Dictionary with validation results
    """
    errors: List[str] = []
    warnings: List[str] = []

    if not content.strip().startswith("---"):
        errors.append(
            "File must start with YAML frontmatter (---)"
        )
        return {
            "valid": False,
            "errors": errors,
            "warnings": warnings,
        }

    try:
        parts = content.split("---", 2)
        if len(parts) < 3:
            errors.append("Invalid frontmatter format")
            return {
                "valid": False,
                "errors": errors,
                "warnings": warnings,
            }

        frontmatter_text = parts[1].strip()
        frontmatter = yaml.safe_load(frontmatter_text)

        if not isinstance(frontmatter, dict):
            errors.append(
                "Frontmatter must be a YAML dictionary"
            )
            return {
                "valid": False,
                "errors": errors,
                "warnings": warnings,
            }

        required_fields = [
            "type",
            "name",
            "description",
            "version",
        ]
        for field in required_fields:
            if field not in frontmatter:
                errors.append(
                    "Missing required frontmatter"
                    f" field: {field}"
                )

        if frontmatter.get("type") != "agent":
            errors.append(
                f"Frontmatter type "
                f"'{frontmatter.get('type')}' "
                "doesn't match expected 'agent'"
            )

        fm_name = frontmatter.get("name", "")
        is_valid, error = validate_name(fm_name)
        if not is_valid:
            errors.append(
                f"Invalid name in frontmatter: {error}"
            )

        fm_version = frontmatter.get("version", "")
        is_valid, error = validate_version(fm_version)
        if not is_valid:
            errors.append(
                "Invalid version in frontmatter:"
                f" {error}"
            )

    except yaml.YAMLError as e:
        errors.append(
            f"Invalid YAML in frontmatter: {e}"
        )

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }


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
    structure_validation = validate_agent_output(
        agent_output
    )
    if not structure_validation["valid"]:
        return {
            "success": False,
            "message": "Invalid agent output structure",
            "errors": structure_validation["errors"],
        }

    agent_validation = agent_output.get("validation", {})
    if not agent_validation.get("passed", False):
        issues = agent_validation.get("issues", [])
        error_messages = [
            issue.get("message", str(issue))
            for issue in issues
            if isinstance(issue, dict)
            and issue.get("severity") == "error"
        ]
        if error_messages:
            return {
                "success": False,
                "message": "Agent validation failed",
                "errors": error_messages,
                "issues": issues,
            }

    files = agent_output.get("files", [])
    if not files:
        return {
            "success": False,
            "message": "No files provided by agent",
        }

    actual_base = Path(base_path).expanduser()

    # Validate main agent file has proper frontmatter
    main_files = [
        f
        for f in files
        if f["path"].endswith(".md")
        and "/knowledge/" not in f["path"]
    ]

    validation_errors: List[str] = []
    for main_file in main_files:
        validation = validate_file_frontmatter(
            main_file["content"]
        )
        if not validation["valid"]:
            validation_errors.extend(
                [
                    f"{main_file['path']}: {err}"
                    for err in validation["errors"]
                ]
            )

    if validation_errors:
        return {
            "success": False,
            "message": "File validation failed",
            "errors": validation_errors,
        }

    created_files: List[str] = []
    try:
        for file_entry in files:
            rel_path = file_entry["path"]
            content = file_entry["content"]

            full_path = actual_base / rel_path
            if not str(full_path).startswith(
                str(actual_base)
            ):
                return {
                    "success": False,
                    "message": (
                        f"Invalid path: {rel_path}"
                    ),
                }

            full_path.parent.mkdir(
                parents=True, exist_ok=True
            )
            full_path.write_text(
                content, encoding="utf-8"
            )
            created_files.append(str(full_path))

    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to create files: {e}",
            "files_created": created_files,
        }

    summary = agent_output.get("summary", {})

    return {
        "success": True,
        "message": (
            f"Created agent with"
            f" {len(created_files)} files"
        ),
        "files_created": created_files,
        "next_steps": summary.get("next_steps", []),
        "base_path": str(actual_base),
    }


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
    operation = context.get("operation", "create")
    location = context.get("location", "user")
    plugin_path = context.get("plugin_path")

    if responses:
        context.update(responses)

    if operation == "create":
        agent_output = context.get("agent_output")
        if agent_output:
            base_path = context.get("base_path")
            if not base_path:
                base_path = str(
                    get_location_path(
                        location, plugin_path
                    )
                )
            return execute_create_from_agent(
                agent_output,
                base_path,
                location,
                plugin_path,
            )

        # Legacy template-based creation
        name = context.get("name") or to_kebab_case(
            context.get("description", "")[:50]
        )
        description = context.get("description", "")
        version = context.get("version", "0.1.0")
        tags = context.get("tags", ["custom"])

        is_valid, error = validate_name(name)
        if not is_valid:
            return {
                "success": False,
                "message": f"Invalid name: {error}",
            }

        is_valid, error = validate_description(description)
        if not is_valid:
            return {
                "success": False,
                "message": (
                    f"Invalid description: {error}"
                ),
            }

        return execute_create(
            name,
            description,
            version,
            tags,
            location,
            templates_dir,
            plugin_path,
        )

    elif operation == "validate":
        name = context.get("name")
        validate_all = context.get("all", False)
        return execute_validate(
            name, validate_all, location, plugin_path
        )

    elif operation == "version":
        name = context.get("name")
        bump_type = context.get("bump", "patch")

        if not name:
            return {
                "success": False,
                "message": (
                    "Name is required for version"
                    " operation"
                ),
            }

        return execute_version(
            name, bump_type, location, plugin_path
        )

    elif operation == "list":
        output_format = context.get("format", "table")
        return execute_list(
            location, plugin_path, output_format
        )

    else:
        return {
            "success": False,
            "message": f"Unknown operation: {operation}",
        }
