"""Shared extension utilities for manager skills.

Provides parameterized functions that agent-manager, skill-manager,
and plugin-manager delegate to.  Each manager defines a config dict
describing its extension type and passes it into these helpers.

Config dict keys:
    entity_label (str):  Human-readable label (e.g. "agent", "skill")
    directory (str):     Sub-directory under the base path
    file_pattern (str):  Pattern with ``{name}`` placeholder
    template (str):      Jinja2 template path for legacy create
    frontmatter_type (str | None): Expected ``type`` value in YAML
        frontmatter, or ``None`` for JSON-based extensions.
    create_subdirs (list[str]): Extra sub-dirs to create on
        ``execute_create`` (relative to the component directory).
    main_file_filter (callable | None): Predicate applied to
        ``file_entry["path"]`` to find the main file in
        ``execute_create_from_agent``.  ``None`` skips validation.
"""

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from shared.utils import (
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


# ------------------------------------------------------------------
# Discovery helpers
# ------------------------------------------------------------------


def find_extensions(
    config: Dict[str, Any],
    location: str = "all",
    plugin_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Find all extensions of a given type via frontmatter parsing.

    Walks the configured directory looking for Markdown files whose
    YAML frontmatter ``type`` matches ``config["frontmatter_type"]``.

    Note: this function is designed for frontmatter-based extensions
    (agents, skills).  Plugin-manager has its own ``find_components``
    because plugins use JSON metadata.

    Args:
        config: Extension type configuration dict.
        location: Where to search (user, project, plugin, all).
        plugin_path: Path to plugin directory.

    Returns:
        List of extension info dictionaries.
    """
    components: List[Dict[str, Any]] = []

    locations_to_search: List[str] = []
    if location == "all":
        locations_to_search = ["user", "project"]
        if plugin_path:
            locations_to_search.append("plugin")
    else:
        locations_to_search = [location]

    expected_type = config.get("frontmatter_type")

    for loc in locations_to_search:
        base_path = get_location_path(loc, plugin_path)
        search_dir = base_path / config["directory"]

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

                fm_text = content[3:end].strip()
                parsed = yaml.safe_load(fm_text)
                frontmatter: Dict[str, Any] = (
                    parsed if isinstance(parsed, dict) else {}
                )

                if frontmatter.get("type") == expected_type:
                    # Prefer parent dir name for skills
                    fallback_name = (
                        md_file.parent.name
                        if md_file.name != md_file.parent.name + ".md"
                        else md_file.stem
                    )
                    components.append(
                        {
                            "name": frontmatter.get(
                                "name", fallback_name
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
            except (IOError, UnicodeDecodeError, yaml.YAMLError):
                pass

    return components


def extension_exists(
    config: Dict[str, Any],
    name: str,
    location: str,
    plugin_path: Optional[str] = None,
    find_fn: Any = None,
) -> bool:
    """Check if an extension with the given name exists.

    Args:
        config: Extension type configuration dict.
        name: Extension name.
        location: Where to check.
        plugin_path: Path to plugin directory.
        find_fn: Custom find function (for plugin-manager).
            Defaults to ``find_extensions``.

    Returns:
        True if the extension exists.
    """
    finder = find_fn or find_extensions
    if finder is find_extensions:
        components = finder(config, location, plugin_path)
    else:
        components = finder(location, plugin_path)
    return any(c["name"] == name for c in components)


# ------------------------------------------------------------------
# Phase 1: get_questions
# ------------------------------------------------------------------


def get_extension_questions(
    config: Dict[str, Any],
    context: Dict[str, Any],
    find_fn: Any = None,
    exists_fn: Any = None,
) -> Dict[str, Any]:
    """Analyze context and return questions needing user input.

    Args:
        config: Extension type configuration dict.
        context: Operation context (operation, description, name,
            location, plugin_path).
        find_fn: Custom find function.  Defaults to
            ``find_extensions``.
        exists_fn: Custom exists function.  Defaults to
            ``extension_exists``.

    Returns:
        Dictionary with questions, inferred values, validation
        results, and optionally project_context.
    """
    operation = context.get("operation", "create")
    location = context.get("location", "user")
    plugin_path = context.get("plugin_path")
    label = config.get("entity_label", "extension")

    finder = find_fn or find_extensions
    checker = exists_fn or extension_exists

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
                        f"What should this {label} do? "
                        "(brief description)"
                    ),
                    "type": "text",
                    "required": True,
                    "help": (
                        f"Describe the purpose of this {label}"
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
                        f"What should this {label} be named?"
                    ),
                    "type": "text",
                    "required": True,
                    "help": (
                        "Must be kebab-case "
                        f"(e.g., my-{label}). "
                        f"Error: {error}"
                    ),
                    "default": (
                        inferred["name"][:50]
                        if inferred["name"]
                        else ""
                    ),
                }
            )

        # Check existence using the right finder
        if checker is extension_exists:
            already_exists = checker(
                config, inferred["name"], location, plugin_path,
                find_fn=find_fn,
            )
        else:
            already_exists = checker(
                inferred["name"], location, plugin_path
            )

        if already_exists:
            result["questions"].append(
                {
                    "id": "name",
                    "question": (
                        f"A {label} named "
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
            if finder is find_extensions:
                components = finder(
                    config, location, plugin_path
                )
            else:
                components = finder(location, plugin_path)
            result["inferred"] = {"components": components}
        elif name:
            result["inferred"] = {"name": name}
        else:
            result["questions"].append(
                {
                    "id": "name",
                    "question": (
                        f"Which {label} do you want to"
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
                        f"Which {label} do you want to"
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


def execute_extension_create(
    config: Dict[str, Any],
    name: str,
    description: str,
    version: str,
    tags: List[str],
    location: str,
    templates_dir: Path,
    plugin_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute extension creation using a Jinja2 template.

    Creates the component file from a template plus any
    subdirectories listed in ``config["create_subdirs"]``.

    Args:
        config: Extension type configuration dict.
        name: Extension name.
        description: Extension description.
        version: Initial version.
        tags: List of tags.
        location: Where to create.
        templates_dir: Path to templates directory.
        plugin_path: Path to plugin directory.

    Returns:
        Result dictionary with success status and details.
    """
    label = config.get("entity_label", "extension")
    base_path = get_location_path(location, plugin_path)
    component_dir = base_path / config["directory"]
    file_path = component_dir / config[
        "file_pattern"
    ].format(name=name)

    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Create configured subdirectories
    for subdir in config.get("create_subdirs", []):
        (file_path.parent / subdir).mkdir(exist_ok=True)

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
            config["template"],
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
            f"Created {label} '{name}' at {file_path}"
        ),
        "files_created": [str(file_path)],
        "path": str(file_path),
    }


def execute_extension_validate(
    config: Dict[str, Any],
    name: Optional[str] = None,
    validate_all: bool = False,
    location: str = "all",
    plugin_path: Optional[str] = None,
    find_fn: Any = None,
) -> Dict[str, Any]:
    """Execute extension validation.

    Args:
        config: Extension type configuration dict.
        name: Specific extension name (or None for all).
        validate_all: Whether to validate all extensions.
        location: Where to search.
        plugin_path: Path to plugin directory.
        find_fn: Custom find function.

    Returns:
        Result dictionary with validation results.
    """
    label = config.get("entity_label", "extension")
    finder = find_fn or find_extensions

    if finder is find_extensions:
        components = finder(config, location, plugin_path)
    else:
        components = finder(location, plugin_path)

    if name and not validate_all:
        components = [
            c for c in components if c["name"] == name
        ]
        if not components:
            return {
                "success": False,
                "message": (
                    f"{label.capitalize()} '{name}' not found"
                ),
            }

    results: List[Dict[str, Any]] = []

    for component in components:
        errors: List[str] = []

        is_valid, error = validate_name(component["name"])
        if not is_valid:
            errors.append(f"Name: {error}")

        is_valid, error = validate_description(
            component.get("description", "")
        )
        if not is_valid:
            errors.append(f"Description: {error}")

        is_valid, error = validate_version(
            component.get("version", "")
        )
        if not is_valid:
            errors.append(f"Version: {error}")

        results.append(
            {
                "name": component["name"],
                "path": component["path"],
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": [],
            }
        )

    valid_count = sum(1 for r in results if r["valid"])
    invalid_count = len(results) - valid_count

    return {
        "success": True,
        "operation": "validate",
        "results": results,
        "summary": {
            "total": len(results),
            "valid": valid_count,
            "invalid": invalid_count,
        },
    }


def execute_extension_version(
    config: Dict[str, Any],
    name: str,
    bump_type: str = "patch",
    location: str = "all",
    plugin_path: Optional[str] = None,
    find_fn: Any = None,
) -> Dict[str, Any]:
    """Execute version bump for a frontmatter-based extension.

    Rewrites the ``version:`` field inside YAML frontmatter.
    Plugin-manager overrides this because it uses JSON.

    Args:
        config: Extension type configuration dict.
        name: Extension name.
        bump_type: Type of version bump (major, minor, patch).
        location: Where to search.
        plugin_path: Path to plugin directory.
        find_fn: Custom find function.

    Returns:
        Result dictionary with version update details.
    """
    label = config.get("entity_label", "extension")
    finder = find_fn or find_extensions

    if finder is find_extensions:
        components = finder(config, location, plugin_path)
    else:
        components = finder(location, plugin_path)

    component = next(
        (c for c in components if c["name"] == name), None
    )

    if not component:
        return {
            "success": False,
            "message": (
                f"{label.capitalize()} '{name}' not found"
            ),
        }

    old_version = component["version"]
    new_version = bump_version(old_version, bump_type)

    file_path = Path(component["path"])

    try:
        content = file_path.read_text(encoding="utf-8")
        new_content = re.sub(
            r"(version:\s*)[\d.]+",
            f"\\g<1>{new_version}",
            content,
            count=1,
        )
        file_path.write_text(
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
            "path": str(file_path),
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to update version: {e}",
        }


def execute_extension_list(
    config: Dict[str, Any],
    location: str = "all",
    plugin_path: Optional[str] = None,
    output_format: str = "table",
    find_fn: Any = None,
) -> Dict[str, Any]:
    """Execute extension listing.

    Args:
        config: Extension type configuration dict.
        location: Where to search.
        plugin_path: Path to plugin directory.
        output_format: Output format (table, json).
        find_fn: Custom find function.

    Returns:
        Result dictionary with extension list.
    """
    finder = find_fn or find_extensions

    if finder is find_extensions:
        components = finder(config, location, plugin_path)
    else:
        components = finder(location, plugin_path)

    return {
        "success": True,
        "operation": "list",
        "components": components,
        "count": len(components),
        "format": output_format,
    }


# ------------------------------------------------------------------
# Frontmatter validation
# ------------------------------------------------------------------


def validate_file_frontmatter(
    content: str,
    expected_type: str,
) -> Dict[str, Any]:
    """Validate YAML frontmatter in an extension file.

    Args:
        content: File content.
        expected_type: Expected ``type`` value (e.g. "agent",
            "skill").

    Returns:
        Dictionary with ``valid``, ``errors``, ``warnings``.
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

        if frontmatter.get("type") != expected_type:
            errors.append(
                f"Frontmatter type "
                f"'{frontmatter.get('type')}' "
                f"doesn't match expected '{expected_type}'"
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


# ------------------------------------------------------------------
# Agent output validation (Phase 3)
# ------------------------------------------------------------------


def validate_agent_output(
    agent_output: Dict[str, Any],
) -> Dict[str, Any]:
    """Validate the structure of agent-generated output.

    Used by both agent-manager and plugin-manager for Phase 3
    creation.

    Args:
        agent_output: The output from the agent.

    Returns:
        Dictionary with ``valid`` and ``errors``.
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
    if not isinstance(
        summary.get("created", []), list
    ):
        errors.append("summary.created must be a list")
    if not isinstance(
        summary.get("next_steps", []), list
    ):
        errors.append(
            "summary.next_steps must be a list"
        )

    return {"valid": len(errors) == 0, "errors": errors}


def execute_create_from_agent(
    config: Dict[str, Any],
    agent_output: Dict[str, Any],
    base_path: str,
    location: str = "user",
    plugin_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute extension creation from agent output (Phase 3).

    Args:
        config: Extension type configuration dict.
        agent_output: JSON output from the agent.
        base_path: Base path where files should be created.
        location: Location type (user, project, plugin).
        plugin_path: Path to plugin directory.

    Returns:
        Result dictionary with success status and details.
    """
    label = config.get("entity_label", "extension")
    expected_type = config.get("frontmatter_type")
    main_file_filter = config.get("main_file_filter")

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

    # Validate main files (frontmatter-based types only)
    if expected_type and main_file_filter:
        main_files = [
            f for f in files if main_file_filter(f["path"])
        ]

        validation_errors: List[str] = []
        for main_file in main_files:
            validation = validate_file_frontmatter(
                main_file["content"], expected_type
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

    # Create files
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
            f"Created {label} with"
            f" {len(created_files)} files"
        ),
        "files_created": created_files,
        "next_steps": summary.get("next_steps", []),
        "base_path": str(actual_base),
    }


# ------------------------------------------------------------------
# Main dispatcher
# ------------------------------------------------------------------


def execute_extension(
    config: Dict[str, Any],
    context: Dict[str, Any],
    responses: Dict[str, Any],
    templates_dir: Path,
    find_fn: Any = None,
    create_fn: Any = None,
    version_fn: Any = None,
) -> Dict[str, Any]:
    """Execute the requested extension operation.

    Handles two modes for create:
    1. Template-based creation (legacy): uses templates_dir
    2. Agent-based creation (new): uses agent_output

    Args:
        config: Extension type configuration dict.
        context: Operation context.
        responses: User responses to questions.
        templates_dir: Path to templates directory.
        find_fn: Custom find function for discovery.
        create_fn: Custom create function (for plugin-manager
            which has a unique create flow).
        version_fn: Custom version function (for plugin-manager
            which uses JSON).

    Returns:
        Result dictionary.
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
                config,
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

        executor = create_fn or execute_extension_create
        if executor is execute_extension_create:
            return executor(
                config,
                name,
                description,
                version,
                tags,
                location,
                templates_dir,
                plugin_path,
            )
        else:
            return executor(
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
        return execute_extension_validate(
            config,
            name,
            validate_all,
            location,
            plugin_path,
            find_fn=find_fn,
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

        executor = version_fn or execute_extension_version
        if executor is execute_extension_version:
            return executor(
                config,
                name,
                bump_type,
                location,
                plugin_path,
                find_fn=find_fn,
            )
        else:
            return executor(
                name,
                bump_type,
                location,
                plugin_path,
            )

    elif operation == "list":
        output_format = context.get("format", "table")
        return execute_extension_list(
            config,
            location,
            plugin_path,
            output_format,
            find_fn=find_fn,
        )

    else:
        return {
            "success": False,
            "message": (
                f"Unknown operation: {operation}"
            ),
        }
