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
    to_kebab_case,
    validate_name,
    validate_description,
    validate_version,
    bump_version,
    get_location_path,
    render_template,
)

# Plugin configuration
PLUGIN_CONFIG = {
    "dir": ".claude-plugin",
    "file_pattern": "plugin.json",
    "frontmatter_type": None,  # plugins use JSON, not frontmatter
}


def find_components(
    location: str = "all",
    plugin_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Find all plugin components.

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

        # Look for .claude-plugin directories
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


def infer_from_description(
    description: str,
) -> Dict[str, Any]:
    """Infer plugin metadata from description.

    Args:
        description: User-provided description

    Returns:
        Dictionary of inferred values
    """
    inferred: Dict[str, Any] = {
        "name": to_kebab_case(description[:50]),
        "version": "0.1.0",
        "tags": ["custom"],
    }

    description_lower = description.lower()

    tag_keywords = {
        "api": ["api", "endpoint", "rest", "graphql"],
        "database": [
            "database",
            "sql",
            "query",
            "migration",
        ],
        "auth": [
            "auth",
            "login",
            "authentication",
            "security",
        ],
        "testing": ["test", "testing", "spec", "coverage"],
        "documentation": ["doc", "documentation", "readme"],
        "deployment": ["deploy", "deployment", "ci", "cd"],
        "monitoring": [
            "monitor",
            "logging",
            "metrics",
            "observability",
        ],
    }

    for tag, keywords in tag_keywords.items():
        if any(kw in description_lower for kw in keywords):
            if tag not in inferred["tags"]:
                inferred["tags"].append(tag)

    return inferred


def detect_project_context() -> Dict[str, Any]:
    """Detect project context for plugin creation.

    Returns:
        Dictionary of detected project facts
    """
    context: Dict[str, Any] = {
        "languages": [],
        "frameworks": [],
        "tools": [],
        "has_tests": False,
        "has_ci": False,
    }

    cwd = Path.cwd()

    language_indicators = {
        "python": [
            "*.py",
            "requirements.txt",
            "pyproject.toml",
            "setup.py",
            "Pipfile",
        ],
        "javascript": ["*.js", "package.json"],
        "typescript": ["*.ts", "tsconfig.json"],
        "go": ["*.go", "go.mod"],
        "rust": ["*.rs", "Cargo.toml"],
        "ruby": ["*.rb", "Gemfile"],
        "java": ["*.java", "pom.xml", "build.gradle"],
    }

    for lang, indicators in language_indicators.items():
        for indicator in indicators:
            if indicator.startswith("*"):
                if list(cwd.glob(indicator)) or list(
                    cwd.glob(f"**/{indicator}")
                ):
                    if lang not in context["languages"]:
                        context["languages"].append(lang)
                    break
            else:
                if (cwd / indicator).exists():
                    if lang not in context["languages"]:
                        context["languages"].append(lang)
                    break

    framework_files = {
        "django": ["manage.py", "settings.py"],
        "flask": ["app.py"],
        "nextjs": ["next.config.js", "next.config.ts"],
        "dbt": ["dbt_project.yml"],
        "terraform": ["*.tf"],
        "cdk": ["cdk.json"],
    }

    for framework, files in framework_files.items():
        for f in files:
            if f.startswith("*"):
                if list(cwd.glob(f)):
                    context["frameworks"].append(framework)
                    break
            elif (cwd / f).exists():
                context["frameworks"].append(framework)
                break

    package_json = cwd / "package.json"
    if package_json.exists():
        try:
            with open(package_json) as f:
                pkg = json.load(f)
                deps = {
                    **pkg.get("dependencies", {}),
                    **pkg.get("devDependencies", {}),
                }
                if "react" in deps:
                    context["frameworks"].append("react")
                if "vue" in deps:
                    context["frameworks"].append("vue")
                if "next" in deps:
                    context["frameworks"].append("nextjs")
        except (json.JSONDecodeError, IOError):
            pass

    tool_files = {
        "docker": [
            "Dockerfile",
            "docker-compose.yml",
            "docker-compose.yaml",
        ],
        "make": ["Makefile"],
        "git": [".git"],
        "pytest": ["pytest.ini", "conftest.py"],
        "jest": ["jest.config.js", "jest.config.ts"],
    }

    for tool, files in tool_files.items():
        for f in files:
            if (cwd / f).exists():
                context["tools"].append(tool)
                break

    context["has_tests"] = (
        (cwd / "tests").exists()
        or (cwd / "test").exists()
        or (cwd / "__tests__").exists()
        or bool(list(cwd.glob("**/test_*.py")))
        or bool(list(cwd.glob("**/*.test.js")))
    )

    context["has_ci"] = (
        (cwd / ".github" / "workflows").exists()
        or (cwd / ".gitlab-ci.yml").exists()
        or (cwd / ".circleci").exists()
    )

    return context


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
                        "What should this plugin do? "
                        "(brief description)"
                    ),
                    "type": "text",
                    "required": True,
                    "help": (
                        "Describe the purpose of this plugin "
                        "in 1-2 sentences"
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
                        "What should this plugin be named?"
                    ),
                    "type": "text",
                    "required": True,
                    "help": (
                        "Must be kebab-case "
                        "(e.g., my-plugin). "
                        f"Error: {error}"
                    ),
                    "default": (
                        inferred["name"][:50]
                        if inferred["name"]
                        else ""
                    ),
                }
            )

        if component_exists(
            inferred["name"], location, plugin_path
        ):
            result["questions"].append(
                {
                    "id": "name",
                    "question": (
                        f"A plugin named "
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
            components = find_components(
                location, plugin_path
            )
            result["inferred"] = {"components": components}
        elif name:
            result["inferred"] = {"name": name}
        else:
            result["questions"].append(
                {
                    "id": "name",
                    "question": (
                        "Which plugin do you want to validate?"
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
                        "Which plugin do you want to version?"
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
        "message": f"Created plugin '{name}' at {output_dir}",
        "files_created": [
            str(
                output_dir / ".claude-plugin" / "plugin.json"
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
    components = find_components(location, plugin_path)

    if name and not validate_all:
        components = [
            c for c in components if c["name"] == name
        ]
        if not components:
            return {
                "success": False,
                "message": f"Plugin '{name}' not found",
            }

    results = []
    all_valid = True

    for component in components:
        errors: List[str] = []

        # Validate name
        is_valid, error = validate_name(component["name"])
        if not is_valid:
            errors.append(f"Name: {error}")

        # Validate description
        is_valid, error = validate_description(
            component.get("description", "")
        )
        if not is_valid:
            errors.append(f"Description: {error}")

        # Validate version
        is_valid, error = validate_version(
            component.get("version", "")
        )
        if not is_valid:
            errors.append(f"Version: {error}")

        if errors:
            all_valid = False

        results.append(
            {
                "name": component["name"],
                "location": component["location"],
                "path": component["path"],
                "valid": len(errors) == 0,
                "errors": errors,
            }
        )

    valid_count = sum(1 for r in results if r["valid"])
    invalid_count = sum(1 for r in results if not r["valid"])

    return {
        "success": True,
        "all_valid": all_valid,
        "results": results,
        "summary": (
            f"Validated {len(results)} plugin(s): "
            f"{valid_count} valid, {invalid_count} invalid"
        ),
    }


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
        content = plugin_json_path.read_text(encoding="utf-8")
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
    components = find_components(location, plugin_path)

    return {
        "success": True,
        "components": components,
        "count": len(components),
        "format": output_format,
    }


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
                    f"files[{i}].path contains invalid "
                    f"characters: {path}"
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
        errors = agent_validation.get("issues", [])
        error_messages = [
            issue.get("message", str(issue))
            for issue in errors
            if isinstance(issue, dict)
            and issue.get("severity") == "error"
        ]
        if error_messages:
            return {
                "success": False,
                "message": "Agent validation failed",
                "errors": error_messages,
                "issues": errors,
            }

    files = agent_output.get("files", [])
    if not files:
        return {
            "success": False,
            "message": "No files provided by agent",
        }

    actual_base = Path(base_path).expanduser()

    # plugin.json doesn't use frontmatter validation
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
                    "message": f"Invalid path: {rel_path}",
                }

            full_path.parent.mkdir(
                parents=True, exist_ok=True
            )
            full_path.write_text(content, encoding="utf-8")
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
            f"Created plugin with "
            f"{len(created_files)} files"
        ),
        "files_created": created_files,
        "next_steps": summary.get("next_steps", []),
        "base_path": str(actual_base),
    }


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
                    get_location_path(location, plugin_path)
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
                    "Name is required for version operation"
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
