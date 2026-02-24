"""Skill management operations for Claude Code.

Handles create, validate, version, and list operations for skills.
Skills are process definitions with execution capabilities that follow
the Agent Skills open standard (agentskills.io).

Supports three-phase orchestration:
- Phase 1: get_questions() - Gather context, infer metadata
- Phase 2: Agent generates content (handled by orchestrator)
- Phase 3: execute() with agent_output - Validate and write files
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from .utils import (
    to_kebab_case,
    validate_name,
    validate_description,
    validate_version,
    bump_version,
    get_location_path,
    render_template,
)

# Skill component configuration
SKILL_CONFIG = {
    "dir": "skills",
    "file_pattern": "{name}/SKILL.md",
    "template": "skill/SKILL.md.jinja2",
    "frontmatter_type": "skill",
}


def find_components(
    location: str = "all",
    plugin_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Find all skill components.

    Args:
        location: Where to search (user, project, plugin, all)
        plugin_path: Path to plugin directory (if location is plugin)

    Returns:
        List of skill info dictionaries
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
        search_dir = base_path / SKILL_CONFIG["dir"]

        if not search_dir.exists():
            continue

        # Skills use SKILL.md as the filename
        for md_file in search_dir.glob("**/SKILL.md"):
            # Skip non-component files
            if md_file.name.startswith("_"):
                continue

            try:
                content = md_file.read_text(encoding="utf-8")
                # Parse frontmatter
                if content.startswith("---"):
                    end = content.find("---", 3)
                    if end > 0:
                        fm_text = content[3:end].strip()
                        frontmatter: Dict[str, str] = {}
                        for line in fm_text.split("\n"):
                            if (
                                ":" in line
                                and not line.strip().startswith("-")
                            ):
                                key, value = line.split(":", 1)
                                frontmatter[key.strip()] = (
                                    value.strip().strip("\"'")
                                )

                        if frontmatter.get("type") == "skill":
                            components.append({
                                "name": frontmatter.get(
                                    "name", md_file.parent.name
                                ),
                                "version": frontmatter.get(
                                    "version", "0.0.0"
                                ),
                                "description": frontmatter.get(
                                    "description", ""
                                ),
                                "location": loc,
                                "path": str(md_file),
                            })
            except (IOError, UnicodeDecodeError):
                pass

    return components


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


def infer_from_description(description: str) -> Dict[str, Any]:
    """Infer skill metadata from description.

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

    # Infer tags from description keywords
    description_lower = description.lower()

    tag_keywords = {
        "api": ["api", "endpoint", "rest", "graphql"],
        "database": ["database", "sql", "query", "migration"],
        "auth": ["auth", "login", "authentication", "security"],
        "testing": ["test", "testing", "spec", "coverage"],
        "documentation": [
            "doc",
            "documentation",
            "readme",
        ],
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
    """Detect project context for the agent to use.

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

    # Detect languages
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

    # Detect frameworks
    framework_files = {
        "fastapi": ["main.py"],
        "django": ["manage.py", "settings.py"],
        "flask": ["app.py"],
        "react": ["package.json"],
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

    # Check package.json for JS frameworks
    package_json = cwd / "package.json"
    if package_json.exists():
        try:
            with open(package_json) as fh:
                pkg = json.load(fh)
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

    # Detect tools
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

    # Check for tests
    context["has_tests"] = (
        (cwd / "tests").exists()
        or (cwd / "test").exists()
        or (cwd / "__tests__").exists()
        or bool(list(cwd.glob("**/test_*.py")))
        or bool(list(cwd.glob("**/*.test.js")))
    )

    # Check for CI
    context["has_ci"] = (
        (cwd / ".github" / "workflows").exists()
        or (cwd / ".gitlab-ci.yml").exists()
        or (cwd / ".circleci").exists()
    )

    return context


def get_questions(context: Dict[str, Any]) -> Dict[str, Any]:
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

        # Always include project context for create operations
        result["project_context"] = detect_project_context()

        if not description:
            result["questions"].append({
                "id": "description",
                "question": (
                    "What should this skill do? "
                    "(brief description)"
                ),
                "type": "text",
                "required": True,
                "help": (
                    "Describe the purpose of this skill "
                    "in 1-2 sentences"
                ),
            })
            return result

        # Infer from description
        inferred = infer_from_description(description)
        inferred["description"] = description

        # Add base path for file creation
        inferred["base_path"] = str(
            get_location_path(location, plugin_path)
        )

        # Validate inferred name
        is_valid, error = validate_name(inferred["name"])
        if not is_valid:
            result["questions"].append({
                "id": "name",
                "question": "What should this skill be named?",
                "type": "text",
                "required": True,
                "help": (
                    "Must be kebab-case "
                    f"(e.g., my-skill). Error: {error}"
                ),
                "default": (
                    inferred["name"][:50]
                    if inferred["name"]
                    else ""
                ),
            })

        # Check if name already exists
        if component_exists(
            inferred["name"], location, plugin_path
        ):
            result["questions"].append({
                "id": "name",
                "question": (
                    f"A skill named '{inferred['name']}' "
                    "already exists. Choose a different name:"
                ),
                "type": "text",
                "required": True,
                "help": "Must be unique within the location",
            })

        result["inferred"] = inferred

    elif operation == "validate":
        name = context.get("name")
        validate_all = context.get("all", False)

        if validate_all:
            components = find_components(location, plugin_path)
            result["inferred"] = {"components": components}
        elif name:
            result["inferred"] = {"name": name}
        else:
            result["questions"].append({
                "id": "name",
                "question": (
                    "Which skill do you want to validate?"
                ),
                "type": "text",
                "required": True,
            })

    elif operation == "version":
        name = context.get("name")
        bump_type = context.get("bump", "patch")

        if not name:
            result["questions"].append({
                "id": "name",
                "question": (
                    "Which skill do you want to version?"
                ),
                "type": "text",
                "required": True,
            })

        result["inferred"] = {"name": name, "bump": bump_type}

    elif operation == "list":
        # No questions needed for list
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
    base_path = get_location_path(location, plugin_path)
    component_dir = base_path / SKILL_CONFIG["dir"]
    file_path = component_dir / SKILL_CONFIG[
        "file_pattern"
    ].format(name=name)

    # Create parent directories
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Skills get references/ and scripts/ subdirectories
    (file_path.parent / "references").mkdir(exist_ok=True)
    (file_path.parent / "scripts").mkdir(exist_ok=True)

    # Render template
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
            SKILL_CONFIG["template"],
            template_vars,
        )
        file_path.write_text(content, encoding="utf-8")
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to render template: {e}",
        }

    files_created = [str(file_path)]

    return {
        "success": True,
        "message": f"Created skill '{name}' at {file_path}",
        "files_created": files_created,
        "path": str(file_path),
    }


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
    components = find_components(location, plugin_path)

    if name and not validate_all:
        components = [c for c in components if c["name"] == name]
        if not components:
            return {
                "success": False,
                "message": f"Skill '{name}' not found",
            }

    results = []
    all_valid = True

    for component in components:
        errors = []

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

        results.append({
            "name": component["name"],
            "location": component["location"],
            "path": component["path"],
            "valid": len(errors) == 0,
            "errors": errors,
        })

    valid_count = sum(1 for r in results if r["valid"])
    invalid_count = sum(1 for r in results if not r["valid"])

    return {
        "success": True,
        "all_valid": all_valid,
        "results": results,
        "summary": (
            f"Validated {len(results)} skill(s): "
            f"{valid_count} valid, {invalid_count} invalid"
        ),
    }


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
    components = find_components(location, plugin_path)
    component = next(
        (c for c in components if c["name"] == name), None
    )

    if not component:
        return {
            "success": False,
            "message": f"Skill '{name}' not found",
        }

    old_version = component["version"]
    new_version = bump_version(old_version, bump_type)

    # Update the file
    file_path = Path(component["path"])

    try:
        content = file_path.read_text(encoding="utf-8")

        # Update YAML frontmatter version
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
    """Execute skill listing.

    Args:
        location: Where to search (user, project, plugin, all)
        plugin_path: Path to plugin directory
        output_format: Output format (table, json)

    Returns:
        Result dictionary with skill list
    """
    components = find_components(location, plugin_path)

    return {
        "success": True,
        "components": components,
        "count": len(components),
        "format": output_format,
    }


def validate_file_frontmatter(content: str) -> Dict[str, Any]:
    """Validate frontmatter in a skill file.

    Args:
        content: File content

    Returns:
        Dictionary with validation results
    """
    errors: List[str] = []
    warnings: List[str] = []

    # Check for frontmatter
    if not content.strip().startswith("---"):
        errors.append(
            "File must start with YAML frontmatter (---)"
        )
        return {
            "valid": False,
            "errors": errors,
            "warnings": warnings,
        }

    # Extract frontmatter
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

        # Check required fields
        required_fields = [
            "type",
            "name",
            "description",
            "version",
        ]
        for field in required_fields:
            if field not in frontmatter:
                errors.append(
                    f"Missing required frontmatter field: "
                    f"{field}"
                )

        # Validate type matches
        if frontmatter.get("type") != "skill":
            errors.append(
                f"Frontmatter type "
                f"'{frontmatter.get('type')}' "
                f"doesn't match expected 'skill'"
            )

        # Validate name format
        name = frontmatter.get("name", "")
        is_valid, error = validate_name(name)
        if not is_valid:
            errors.append(
                f"Invalid name in frontmatter: {error}"
            )

        # Validate version format
        version = frontmatter.get("version", "")
        is_valid, error = validate_version(version)
        if not is_valid:
            errors.append(
                f"Invalid version in frontmatter: {error}"
            )

    except yaml.YAMLError as e:
        errors.append(f"Invalid YAML in frontmatter: {e}")

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
    """Execute skill creation from agent output (Phase 3).

    Args:
        agent_output: JSON output from the agent with files
        base_path: Base path where files should be created
        location: Location type (user, project, plugin)
        plugin_path: Path to plugin directory

    Returns:
        Result dictionary with success status and details
    """
    # Validate agent output structure
    errors: List[str] = []
    required_keys = ["validation", "files", "summary"]
    for key in required_keys:
        if key not in agent_output:
            errors.append(f"Missing required key: {key}")

    if errors:
        return {
            "success": False,
            "message": "Invalid agent output structure",
            "errors": errors,
        }

    # Validate 'files' section
    files = agent_output.get("files", [])
    if not isinstance(files, list):
        return {
            "success": False,
            "message": "Invalid agent output: files must be a list",
            "errors": ["files must be a list"],
        }

    for i, file_entry in enumerate(files):
        if not isinstance(file_entry, dict):
            errors.append(f"files[{i}] must be an object")
            continue
        if "path" not in file_entry:
            errors.append(f"files[{i}].path is required")
        if "content" not in file_entry:
            errors.append(f"files[{i}].content is required")
        path = file_entry.get("path", "")
        if ".." in path or path.startswith("/"):
            errors.append(
                f"files[{i}].path contains invalid "
                f"characters: {path}"
            )

    if errors:
        return {
            "success": False,
            "message": "Invalid agent output structure",
            "errors": errors,
        }

    # Check agent's own validation
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

    if not files:
        return {
            "success": False,
            "message": "No files provided by agent",
        }

    # Determine actual base path
    actual_base = Path(base_path).expanduser()

    # Validate main skill file has proper frontmatter
    main_files = [
        f for f in files if f["path"].endswith("SKILL.md")
    ]

    validation_errors: List[str] = []
    for main_file in main_files:
        validation = validate_file_frontmatter(
            main_file["content"]
        )
        if not validation["valid"]:
            validation_errors.extend([
                f"{main_file['path']}: {err}"
                for err in validation["errors"]
            ])

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

            # Construct full path
            full_path = actual_base / rel_path
            if not str(full_path).startswith(str(actual_base)):
                return {
                    "success": False,
                    "message": f"Invalid path: {rel_path}",
                }

            # Create parent directories
            full_path.parent.mkdir(parents=True, exist_ok=True)

            # Write file
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
            f"Created skill with {len(created_files)} files"
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
    operation = context.get("operation", "create")
    location = context.get("location", "user")
    plugin_path = context.get("plugin_path")

    # Merge responses into context
    if responses:
        context.update(responses)

    if operation == "create":
        # Check if this is agent-based creation (Phase 3)
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

        # Validate before creating
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
                "message": f"Invalid description: {error}",
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
