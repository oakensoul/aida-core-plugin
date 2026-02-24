"""Extension management operations for Claude Code.

Handles create, validate, version, and list operations for:
- Agents
- Skills
- Plugins

Supports three-phase orchestration:
- Phase 1: get_questions() - Gather context, infer metadata, return questions
- Phase 2: Agent generates content (handled by skill/orchestrator)
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

# Component types and their properties
COMPONENT_TYPES = {
    "agent": {
        "directory": "agents",
        "file_pattern": "{name}/{name}.md",
        "template": "agent/agent.md.jinja2",
        "has_subdirectory": True,
    },
    "skill": {
        "directory": "skills",
        "file_pattern": "{name}/SKILL.md",
        "template": "skill/SKILL.md.jinja2",
        "has_subdirectory": True,
    },
    "plugin": {
        "directory": "",  # Plugin is a directory itself
        "file_pattern": ".claude-plugin/plugin.json",
        "template": "plugin/plugin.json.jinja2",
        "has_subdirectory": True,
    },
}


def find_components(
    component_type: str,
    location: str = "all",
    plugin_path: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Find all components of a given type.

    Args:
        component_type: Type of component (agent, skill, plugin)
        location: Where to search (user, project, plugin, all)
        plugin_path: Path to plugin directory (if location is plugin)

    Returns:
        List of component info dictionaries
    """
    if component_type not in COMPONENT_TYPES:
        raise ValueError(
            f"Unknown component type: {component_type!r}. "
            f"Supported types: {', '.join(COMPONENT_TYPES)}"
        )
    config = COMPONENT_TYPES[component_type]
    components = []

    locations_to_search = []
    if location == "all":
        locations_to_search = ["user", "project"]
        if plugin_path:
            locations_to_search.append("plugin")
    else:
        locations_to_search = [location]

    for loc in locations_to_search:
        base_path = get_location_path(loc, plugin_path)
        search_dir = base_path / config["directory"] if config["directory"] else base_path

        if not search_dir.exists():
            continue

        if component_type == "plugin":
            # For plugins, look for .claude-plugin directories
            for item in search_dir.iterdir():
                if item.is_dir():
                    plugin_json = item / ".claude-plugin" / "plugin.json"
                    if plugin_json.exists():
                        try:
                            with open(plugin_json) as f:
                                data = json.load(f)
                            components.append({
                                "name": data.get("name", item.name),
                                "version": data.get("version", "0.0.0"),
                                "description": data.get("description", ""),
                                "location": loc,
                                "path": str(item),
                            })
                        except (json.JSONDecodeError, IOError):
                            pass
        else:
            # For agents, skills
            pattern = "**/*.md" if config["has_subdirectory"] else "*.md"
            for md_file in search_dir.glob(pattern):
                # Skip non-component files
                if md_file.name.startswith("_") or md_file.name == "README.md":
                    continue

                try:
                    content = md_file.read_text(encoding='utf-8')
                    # Parse frontmatter
                    if content.startswith("---"):
                        end = content.find("---", 3)
                        if end > 0:
                            frontmatter_text = content[3:end].strip()
                            # Simple YAML parsing for frontmatter
                            frontmatter = {}
                            for line in frontmatter_text.split('\n'):
                                if ':' in line and not line.strip().startswith('-'):
                                    key, value = line.split(':', 1)
                                    frontmatter[key.strip()] = value.strip().strip('"\'')

                            if frontmatter.get("type") == component_type:
                                components.append({
                                    "name": frontmatter.get("name", md_file.stem),
                                    "version": frontmatter.get("version", "0.0.0"),
                                    "description": frontmatter.get("description", ""),
                                    "location": loc,
                                    "path": str(md_file),
                                })
                except (IOError, UnicodeDecodeError):
                    pass

    return components


def component_exists(
    name: str,
    component_type: str,
    location: str,
    plugin_path: Optional[str] = None
) -> bool:
    """Check if a component with the given name already exists.

    Args:
        name: Component name
        component_type: Type of component
        location: Where to check
        plugin_path: Path to plugin directory

    Returns:
        True if component exists
    """
    components = find_components(component_type, location, plugin_path)
    return any(c["name"] == name for c in components)


def infer_from_description(description: str) -> Dict[str, Any]:
    """Infer component metadata from description.

    Args:
        description: User-provided description

    Returns:
        Dictionary of inferred values
    """
    inferred = {
        "name": to_kebab_case(description[:50]),  # Truncate for name
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
        "documentation": ["doc", "documentation", "readme"],
        "deployment": ["deploy", "deployment", "ci", "cd"],
        "monitoring": ["monitor", "logging", "metrics", "observability"],
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
        "python": ["*.py", "requirements.txt", "pyproject.toml", "setup.py", "Pipfile"],
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
                if list(cwd.glob(indicator)) or list(cwd.glob(f"**/{indicator}")):
                    if lang not in context["languages"]:
                        context["languages"].append(lang)
                    break
            else:
                if (cwd / indicator).exists():
                    if lang not in context["languages"]:
                        context["languages"].append(lang)
                    break

    # Detect frameworks (basic detection)
    framework_files = {
        "fastapi": ["main.py"],  # Check for FastAPI import later
        "django": ["manage.py", "settings.py"],
        "flask": ["app.py"],
        "react": ["package.json"],  # Check for react dependency
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
            with open(package_json) as f:
                pkg = json.load(f)
                deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
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
        "docker": ["Dockerfile", "docker-compose.yml", "docker-compose.yaml"],
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
        (cwd / "tests").exists() or
        (cwd / "test").exists() or
        (cwd / "__tests__").exists() or
        bool(list(cwd.glob("**/test_*.py"))) or
        bool(list(cwd.glob("**/*.test.js")))
    )

    # Check for CI
    context["has_ci"] = (
        (cwd / ".github" / "workflows").exists() or
        (cwd / ".gitlab-ci.yml").exists() or
        (cwd / ".circleci").exists()
    )

    return context


def get_questions(context: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze context and return questions that need user input (Phase 1).

    Args:
        context: Operation context containing:
            - operation: create, validate, version, update, list
            - type: agent, skill, plugin
            - description: (for create) component description
            - name: (for validate/version/update) component name
            - location: user, project, plugin (default: user)
            - plugin_path: path to plugin (if location is plugin)

    Returns:
        Dictionary containing:
            {
                "questions": [...],      # Questions needing user input
                "inferred": {...},       # Auto-detected values
                "validation": {...},     # Validation results
                "project_context": {...} # Detected project info (for create)
            }
    """
    operation = context.get("operation", "create")
    component_type = context.get("type", "agent")
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
                "question": f"What should this {component_type} do? (brief description)",
                "type": "text",
                "required": True,
                "help": "Describe the purpose of this component in 1-2 sentences",
            })
            return result

        # Infer from description
        inferred = infer_from_description(description)
        inferred["description"] = description

        # Add base path - this is the location root (e.g., ~/.claude/)
        # The agent will return relative paths like agents/{name}/{name}.md
        inferred["base_path"] = str(get_location_path(location, plugin_path))

        # Validate inferred name
        is_valid, error = validate_name(inferred["name"])
        if not is_valid:
            result["questions"].append({
                "id": "name",
                "question": f"What should this {component_type} be named?",
                "type": "text",
                "required": True,
                "help": f"Must be kebab-case (e.g., my-{component_type}). Error: {error}",
                "default": inferred["name"][:50] if inferred["name"] else "",
            })

        # Check if name already exists
        if component_exists(inferred["name"], component_type, location, plugin_path):
            result["questions"].append({
                "id": "name",
                "question": (
                    f"A {component_type} named '{inferred['name']}' already exists. "
                    "Choose a different name:"
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
            # Validate all components of this type
            components = find_components(component_type, location, plugin_path)
            result["inferred"] = {"components": components}
        elif name:
            # Validate specific component
            result["inferred"] = {"name": name}
        else:
            result["questions"].append({
                "id": "name",
                "question": f"Which {component_type} do you want to validate?",
                "type": "text",
                "required": True,
            })

    elif operation == "version":
        name = context.get("name")
        bump_type = context.get("bump", "patch")

        if not name:
            result["questions"].append({
                "id": "name",
                "question": f"Which {component_type} do you want to version?",
                "type": "text",
                "required": True,
            })

        result["inferred"] = {"name": name, "bump": bump_type}

    elif operation == "list":
        # No questions needed for list
        result["inferred"] = {"location": location}

    return result


def execute_create(
    component_type: str,
    name: str,
    description: str,
    version: str,
    tags: List[str],
    location: str,
    templates_dir: Path,
    plugin_path: Optional[str] = None
) -> Dict[str, Any]:
    """Execute component creation.

    Args:
        component_type: Type of component to create
        name: Component name
        description: Component description
        version: Initial version
        tags: List of tags
        location: Where to create (user, project, plugin)
        templates_dir: Path to templates directory
        plugin_path: Path to plugin directory

    Returns:
        Result dictionary with success status and details
    """
    if component_type not in COMPONENT_TYPES:
        return {
            "success": False,
            "message": (
                f"Unknown component type: {component_type!r}. "
                f"Supported types: {', '.join(COMPONENT_TYPES)}"
            ),
        }
    config = COMPONENT_TYPES[component_type]
    base_path = get_location_path(location, plugin_path)

    # Determine output path
    if component_type == "plugin":
        # Plugin creates its own directory structure
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
            content = render_template(templates_dir, config["template"], template_vars)
            plugin_json = output_dir / ".claude-plugin" / "plugin.json"
            plugin_json.write_text(content, encoding='utf-8')
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to render template: {e}",
            }

        # Create README
        readme_template = "plugin/README.md.jinja2"
        try:
            readme_content = render_template(templates_dir, readme_template, template_vars)
            (output_dir / "README.md").write_text(readme_content, encoding='utf-8')
        except Exception:
            # README is optional
            pass

        # Create .gitignore
        gitignore_template = "plugin/gitignore.jinja2"
        try:
            gitignore_content = render_template(templates_dir, gitignore_template, template_vars)
            (output_dir / ".gitignore").write_text(gitignore_content, encoding='utf-8')
        except Exception:
            # .gitignore is optional
            pass

        return {
            "success": True,
            "message": f"Created plugin '{name}' at {output_dir}",
            "files_created": [
                str(output_dir / ".claude-plugin" / "plugin.json"),
                str(output_dir / "README.md"),
            ],
            "path": str(output_dir),
        }

    else:
        # Agent or skill
        component_dir = base_path / config["directory"]
        file_path = component_dir / config["file_pattern"].format(name=name)

        # Create parent directories
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # For agents and skills, create knowledge/references directories
        if config["has_subdirectory"] and component_type in ["agent", "skill"]:
            if component_type == "agent":
                (file_path.parent / "knowledge").mkdir(exist_ok=True)
            elif component_type == "skill":
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
            content = render_template(templates_dir, config["template"], template_vars)
            file_path.write_text(content, encoding='utf-8')
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to render template: {e}",
            }

        files_created = [str(file_path)]

        return {
            "success": True,
            "message": f"Created {component_type} '{name}' at {file_path}",
            "files_created": files_created,
            "path": str(file_path),
        }


def execute_validate(
    component_type: str,
    name: Optional[str] = None,
    validate_all: bool = False,
    location: str = "all",
    plugin_path: Optional[str] = None
) -> Dict[str, Any]:
    """Execute component validation.

    Args:
        component_type: Type of component to validate
        name: Specific component name (or None for all)
        validate_all: Whether to validate all components
        location: Where to search
        plugin_path: Path to plugin directory

    Returns:
        Result dictionary with validation results
    """
    components = find_components(component_type, location, plugin_path)

    if name and not validate_all:
        components = [c for c in components if c["name"] == name]
        if not components:
            return {
                "success": False,
                "message": f"Component '{name}' not found",
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
        is_valid, error = validate_description(component.get("description", ""))
        if not is_valid:
            errors.append(f"Description: {error}")

        # Validate version
        is_valid, error = validate_version(component.get("version", ""))
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

    valid_count = sum(1 for r in results if r['valid'])
    invalid_count = sum(1 for r in results if not r['valid'])

    return {
        "success": True,
        "all_valid": all_valid,
        "results": results,
        "summary": (
            f"Validated {len(results)} {component_type}(s): "
            f"{valid_count} valid, {invalid_count} invalid"
        ),
    }


def execute_version(
    component_type: str,
    name: str,
    bump_type: str = "patch",
    location: str = "all",
    plugin_path: Optional[str] = None
) -> Dict[str, Any]:
    """Execute version bump.

    Args:
        component_type: Type of component
        name: Component name
        bump_type: Type of version bump (major, minor, patch)
        location: Where to search
        plugin_path: Path to plugin directory

    Returns:
        Result dictionary with version update details
    """
    components = find_components(component_type, location, plugin_path)
    component = next((c for c in components if c["name"] == name), None)

    if not component:
        return {
            "success": False,
            "message": f"Component '{name}' not found",
        }

    old_version = component["version"]
    new_version = bump_version(old_version, bump_type)

    # Update the file
    file_path = Path(component["path"])

    try:
        content = file_path.read_text(encoding='utf-8')

        if component_type == "plugin":
            # Update JSON
            data = json.loads(content)
            data["version"] = new_version
            new_content = json.dumps(data, indent=2)
        else:
            # Update YAML frontmatter
            new_content = re.sub(
                r'(version:\s*)[\d.]+',
                f'\\g<1>{new_version}',
                content,
                count=1
            )

        file_path.write_text(new_content, encoding='utf-8')

        return {
            "success": True,
            "message": f"Updated {name} from {old_version} to {new_version}",
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
    component_type: str,
    location: str = "all",
    plugin_path: Optional[str] = None,
    output_format: str = "table"
) -> Dict[str, Any]:
    """Execute component listing.

    Args:
        component_type: Type of component to list
        location: Where to search (user, project, plugin, all)
        plugin_path: Path to plugin directory
        output_format: Output format (table, json)

    Returns:
        Result dictionary with component list
    """
    components = find_components(component_type, location, plugin_path)

    return {
        "success": True,
        "components": components,
        "count": len(components),
        "format": output_format,
    }


def validate_agent_output(agent_output: Dict[str, Any]) -> Dict[str, Any]:
    """Validate the structure of agent output.

    Args:
        agent_output: The output from the agent

    Returns:
        Dictionary with validation results
    """
    errors = []

    # Check required top-level keys
    required_keys = ["validation", "files", "summary"]
    for key in required_keys:
        if key not in agent_output:
            errors.append(f"Missing required key: {key}")

    if errors:
        return {"valid": False, "errors": errors}

    # Validate 'validation' section
    validation = agent_output.get("validation", {})
    if "passed" not in validation:
        errors.append("validation.passed is required")
    if not isinstance(validation.get("issues", []), list):
        errors.append("validation.issues must be a list")

    # Validate 'files' section
    files = agent_output.get("files", [])
    if not isinstance(files, list):
        errors.append("files must be a list")
    else:
        for i, file_entry in enumerate(files):
            if not isinstance(file_entry, dict):
                errors.append(f"files[{i}] must be an object")
                continue
            if "path" not in file_entry:
                errors.append(f"files[{i}].path is required")
            if "content" not in file_entry:
                errors.append(f"files[{i}].content is required")
            # Validate path doesn't try to escape
            path = file_entry.get("path", "")
            if ".." in path or path.startswith("/"):
                errors.append(f"files[{i}].path contains invalid characters: {path}")

    # Validate 'summary' section
    summary = agent_output.get("summary", {})
    if not isinstance(summary.get("created", []), list):
        errors.append("summary.created must be a list")
    if not isinstance(summary.get("next_steps", []), list):
        errors.append("summary.next_steps must be a list")

    return {"valid": len(errors) == 0, "errors": errors}


def validate_file_frontmatter(content: str, component_type: str) -> Dict[str, Any]:
    """Validate frontmatter in a component file.

    Args:
        content: File content
        component_type: Expected component type

    Returns:
        Dictionary with validation results
    """
    errors = []
    warnings = []

    # Check for frontmatter
    if not content.strip().startswith("---"):
        errors.append("File must start with YAML frontmatter (---)")
        return {"valid": False, "errors": errors, "warnings": warnings}

    # Extract frontmatter
    try:
        parts = content.split("---", 2)
        if len(parts) < 3:
            errors.append("Invalid frontmatter format")
            return {"valid": False, "errors": errors, "warnings": warnings}

        frontmatter_text = parts[1].strip()
        frontmatter = yaml.safe_load(frontmatter_text)

        if not isinstance(frontmatter, dict):
            errors.append("Frontmatter must be a YAML dictionary")
            return {"valid": False, "errors": errors, "warnings": warnings}

        # Check required fields
        required_fields = ["type", "name", "description", "version"]
        for field in required_fields:
            if field not in frontmatter:
                errors.append(f"Missing required frontmatter field: {field}")

        # Validate type matches
        if frontmatter.get("type") != component_type:
            errors.append(
                f"Frontmatter type '{frontmatter.get('type')}' "
                f"doesn't match expected '{component_type}'"
            )

        # Validate name format
        name = frontmatter.get("name", "")
        is_valid, error = validate_name(name)
        if not is_valid:
            errors.append(f"Invalid name in frontmatter: {error}")

        # Validate version format
        version = frontmatter.get("version", "")
        is_valid, error = validate_version(version)
        if not is_valid:
            errors.append(f"Invalid version in frontmatter: {error}")

    except yaml.YAMLError as e:
        errors.append(f"Invalid YAML in frontmatter: {e}")

    return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}


def execute_create_from_agent(
    component_type: str,
    agent_output: Dict[str, Any],
    base_path: str,
    location: str = "user",
    plugin_path: Optional[str] = None
) -> Dict[str, Any]:
    """Execute component creation from agent output (Phase 3).

    Args:
        component_type: Type of component being created
        agent_output: The JSON output from the agent containing files to create
        base_path: Base path where files should be created
        location: Location type (user, project, plugin)
        plugin_path: Path to plugin directory (if location is plugin)

    Returns:
        Result dictionary with success status and details
    """
    # Validate agent output structure
    structure_validation = validate_agent_output(agent_output)
    if not structure_validation["valid"]:
        return {
            "success": False,
            "message": "Invalid agent output structure",
            "errors": structure_validation["errors"],
        }

    # Check agent's own validation
    agent_validation = agent_output.get("validation", {})
    if not agent_validation.get("passed", False):
        errors = agent_validation.get("issues", [])
        error_messages = [
            issue.get("message", str(issue))
            for issue in errors
            if isinstance(issue, dict) and issue.get("severity") == "error"
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

    # Determine actual base path
    actual_base = Path(base_path).expanduser()

    # Validate main component file has proper frontmatter
    main_file_patterns = {
        "agent": lambda f: f["path"].endswith(".md") and "/knowledge/" not in f["path"],
        "skill": lambda f: f["path"].endswith("SKILL.md"),
        "plugin": lambda f: f["path"].endswith("plugin.json"),
    }

    main_file_check = main_file_patterns.get(component_type, lambda f: False)
    main_files = [f for f in files if main_file_check(f)]

    validation_errors = []
    for main_file in main_files:
        if component_type != "plugin":  # plugin.json doesn't have frontmatter
            validation = validate_file_frontmatter(main_file["content"], component_type)
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
    created_files = []
    try:
        for file_entry in files:
            rel_path = file_entry["path"]
            content = file_entry["content"]

            # Construct full path
            full_path = actual_base / rel_path
            if not str(full_path).startswith(str(actual_base)):
                # Path traversal attempt
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
            "files_created": created_files,  # Partial success info
        }

    summary = agent_output.get("summary", {})

    return {
        "success": True,
        "message": f"Created {component_type} with {len(created_files)} files",
        "files_created": created_files,
        "next_steps": summary.get("next_steps", []),
        "base_path": str(actual_base),
    }


def execute(
    context: Dict[str, Any],
    responses: Dict[str, Any],
    templates_dir: Path
) -> Dict[str, Any]:
    """Execute the requested operation (Phase 2/3).

    This function handles two modes:
    1. Template-based creation (legacy): Uses templates_dir to render files
    2. Agent-based creation (new): Uses agent_output to write files

    Args:
        context: Operation context, may include:
            - agent_output: JSON from claude-code-expert agent (Phase 3)
            - base_path: Where to create files (required with agent_output)
        responses: User responses to questions (if any)
        templates_dir: Path to templates directory

    Returns:
        Result dictionary
    """
    operation = context.get("operation", "create")
    component_type = context.get("type", "agent")
    location = context.get("location", "user")
    plugin_path = context.get("plugin_path")

    # Merge responses into context
    if responses:
        context.update(responses)

    if operation == "create":
        # Check if this is agent-based creation (Phase 3)
        agent_output = context.get("agent_output")
        if agent_output:
            # base_path is the location root (e.g., ~/.claude/)
            # Agent returns paths relative to this (e.g., agents/{name}/{name}.md)
            base_path = context.get("base_path")
            if not base_path:
                base_path = str(get_location_path(location, plugin_path))

            return execute_create_from_agent(
                component_type, agent_output, base_path, location, plugin_path
            )

        # Legacy template-based creation
        name = context.get("name") or to_kebab_case(context.get("description", "")[:50])
        description = context.get("description", "")
        version = context.get("version", "0.1.0")
        tags = context.get("tags", ["custom"])

        # Validate before creating
        is_valid, error = validate_name(name)
        if not is_valid:
            return {"success": False, "message": f"Invalid name: {error}"}

        is_valid, error = validate_description(description)
        if not is_valid:
            return {"success": False, "message": f"Invalid description: {error}"}

        return execute_create(
            component_type, name, description, version, tags,
            location, templates_dir, plugin_path
        )

    elif operation == "validate":
        name = context.get("name")
        validate_all = context.get("all", False)
        return execute_validate(component_type, name, validate_all, location, plugin_path)

    elif operation == "version":
        name = context.get("name")
        bump_type = context.get("bump", "patch")

        if not name:
            return {"success": False, "message": "Name is required for version operation"}

        return execute_version(component_type, name, bump_type, location, plugin_path)

    elif operation == "list":
        output_format = context.get("format", "table")
        return execute_list(component_type, location, plugin_path, output_format)

    elif operation == "update":
        return {"success": False, "message": "Update operation not yet implemented"}

    else:
        return {"success": False, "message": f"Unknown operation: {operation}"}
