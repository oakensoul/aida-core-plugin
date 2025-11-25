#!/usr/bin/env python3
"""Claude Code Extension Management Script - Two-Phase API

This script provides a two-phase API for managing Claude Code extensions:
agents, commands, skills, and plugins.

Phase 1: get_questions(context)
    - Analyzes context and infers component metadata
    - Returns questions that need user input (if any)
    - Detects existing components, validates names

Phase 2: execute(operation, responses, inferred)
    - Performs the requested operation (create, validate, version, etc.)
    - Uses Jinja2 templates for creation
    - Returns success/failure with details

Usage:
    # Phase 1: Get questions for create
    python manage.py --get-questions --context='{"operation": "create", "type": "agent", "description": "..."}'

    # Phase 2: Execute create
    python manage.py --execute --context='{"operation": "create", "type": "agent", ...}' --responses='{}'

    # Direct operations (no questions)
    python manage.py --execute --context='{"operation": "list", "type": "agent", "location": "all"}'
    python manage.py --execute --context='{"operation": "validate", "type": "agent", "name": "my-agent"}'
    python manage.py --execute --context='{"operation": "version", "type": "agent", "name": "my-agent", "bump": "patch"}'

Exit codes:
    0   - Success
    1   - Error occurred
"""

import sys
import json
import argparse
import re
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATES_DIR = SKILL_DIR / "templates"

# Component types and their properties
COMPONENT_TYPES = {
    "agent": {
        "directory": "agents",
        "file_pattern": "{name}/{name}.md",
        "template": "agent/agent.md.jinja2",
        "has_subdirectory": True,
    },
    "command": {
        "directory": "commands",
        "file_pattern": "{name}.md",
        "template": "command/command.md.jinja2",
        "has_subdirectory": False,
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

# Location mappings
LOCATION_PATHS = {
    "user": Path.home() / ".claude",
    "project": Path.cwd() / ".claude",
    "plugin": None,  # Determined by context
}


def to_kebab_case(text: str) -> str:
    """Convert text to kebab-case for component names.

    Args:
        text: Input text (description or name)

    Returns:
        Kebab-case string suitable for component names

    Examples:
        >>> to_kebab_case("Database Migration Handler")
        'database-migration-handler'
        >>> to_kebab_case("handles API requests")
        'handles-api-requests'
    """
    # Remove special characters except spaces and hyphens
    text = re.sub(r'[^\w\s-]', '', text)
    # Replace spaces and underscores with hyphens
    text = re.sub(r'[\s_]+', '-', text)
    # Convert to lowercase
    text = text.lower()
    # Remove leading/trailing hyphens
    text = text.strip('-')
    # Collapse multiple hyphens
    text = re.sub(r'-+', '-', text)
    return text


def validate_name(name: str) -> Tuple[bool, Optional[str]]:
    """Validate component name against schema rules.

    Args:
        name: Component name to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not name:
        return False, "Name cannot be empty"

    if len(name) < 2:
        return False, "Name must be at least 2 characters"

    if len(name) > 50:
        return False, "Name must be at most 50 characters"

    if not re.match(r'^[a-z][a-z0-9-]*$', name):
        return False, "Name must start with lowercase letter and contain only lowercase letters, numbers, and hyphens"

    return True, None


def validate_description(description: str) -> Tuple[bool, Optional[str]]:
    """Validate component description against schema rules.

    Args:
        description: Component description to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not description:
        return False, "Description cannot be empty"

    if len(description) < 10:
        return False, "Description must be at least 10 characters"

    if len(description) > 500:
        return False, "Description must be at most 500 characters"

    return True, None


def validate_version(version: str) -> Tuple[bool, Optional[str]]:
    """Validate semantic version string.

    Args:
        version: Version string to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not re.match(r'^\d+\.\d+\.\d+$', version):
        return False, "Version must be in format X.Y.Z (e.g., 0.1.0)"

    return True, None


def bump_version(version: str, bump_type: str) -> str:
    """Bump semantic version.

    Args:
        version: Current version string (X.Y.Z)
        bump_type: Type of bump (major, minor, patch)

    Returns:
        New version string
    """
    parts = [int(p) for p in version.split('.')]
    major, minor, patch = parts[0], parts[1], parts[2]

    if bump_type == "major":
        major += 1
        minor = 0
        patch = 0
    elif bump_type == "minor":
        minor += 1
        patch = 0
    elif bump_type == "patch":
        patch += 1

    return f"{major}.{minor}.{patch}"


def get_location_path(location: str, plugin_path: Optional[str] = None) -> Path:
    """Get the base path for a location.

    Args:
        location: Location type (user, project, plugin)
        plugin_path: Path to plugin directory (required if location is plugin)

    Returns:
        Path to the location directory
    """
    if location == "plugin":
        if plugin_path:
            return Path(plugin_path)
        # Default to current directory for plugin context
        return Path.cwd()
    return LOCATION_PATHS.get(location, Path.cwd() / ".claude")


def find_components(
    component_type: str,
    location: str = "all",
    plugin_path: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Find all components of a given type.

    Args:
        component_type: Type of component (agent, command, skill, plugin)
        location: Where to search (user, project, plugin, all)
        plugin_path: Path to plugin directory (if location is plugin)

    Returns:
        List of component info dictionaries
    """
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
            # For agents, commands, skills
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


def component_exists(name: str, component_type: str, location: str, plugin_path: Optional[str] = None) -> bool:
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


def render_template(template_name: str, variables: Dict[str, Any]) -> str:
    """Render a Jinja2 template with variables.

    Args:
        template_name: Name of template file relative to templates/
        variables: Template variables

    Returns:
        Rendered template string
    """
    try:
        from jinja2 import Environment, FileSystemLoader, select_autoescape
    except ImportError:
        raise RuntimeError("Jinja2 is required. Install with: pip install jinja2")

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(['html', 'xml']),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    template = env.get_template(template_name)
    return template.render(**variables)


def get_questions(context: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze context and return questions that need user input (Phase 1).

    Args:
        context: Operation context containing:
            - operation: create, validate, version, update, list
            - type: agent, command, skill, plugin
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
            }
    """
    operation = context.get("operation", "create")
    component_type = context.get("type", "agent")
    location = context.get("location", "user")
    plugin_path = context.get("plugin_path")

    result = {
        "questions": [],
        "inferred": {},
        "validation": {"valid": True, "errors": []},
    }

    if operation == "create":
        description = context.get("description", "")

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
                "question": f"A {component_type} named '{inferred['name']}' already exists. Choose a different name:",
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
        plugin_path: Path to plugin directory

    Returns:
        Result dictionary with success status and details
    """
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
        (output_dir / "commands").mkdir(exist_ok=True)
        (output_dir / "skills").mkdir(exist_ok=True)

        # Render plugin.json
        template_vars = {
            "name": name,
            "description": description,
            "version": version,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        try:
            content = render_template(config["template"], template_vars)
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
            readme_content = render_template(readme_template, template_vars)
            (output_dir / "README.md").write_text(readme_content, encoding='utf-8')
        except Exception:
            # README is optional
            pass

        # Create .gitignore
        gitignore_template = "plugin/gitignore.jinja2"
        try:
            gitignore_content = render_template(gitignore_template, template_vars)
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
        # Agent, command, or skill
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
            content = render_template(config["template"], template_vars)
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

    return {
        "success": True,
        "all_valid": all_valid,
        "results": results,
        "summary": f"Validated {len(results)} {component_type}(s): {sum(1 for r in results if r['valid'])} valid, {sum(1 for r in results if not r['valid'])} invalid",
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


def execute(context: Dict[str, Any], responses: Dict[str, Any] = None) -> Dict[str, Any]:
    """Execute the requested operation (Phase 2).

    Args:
        context: Operation context
        responses: User responses to questions (if any)

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

        return execute_create(component_type, name, description, version, tags, location, plugin_path)

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
        # TODO: Implement update operation
        return {"success": False, "message": "Update operation not yet implemented"}

    else:
        return {"success": False, "message": f"Unknown operation: {operation}"}


def safe_json_load(json_str: str) -> Dict[str, Any]:
    """Safely load JSON string with size limits.

    Args:
        json_str: JSON string to parse

    Returns:
        Parsed dictionary

    Raises:
        ValueError: If JSON is invalid or exceeds limits
    """
    if not json_str:
        return {}

    # Size limit: 100KB
    if len(json_str) > 100 * 1024:
        raise ValueError("JSON input exceeds size limit (100KB)")

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}")


def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Claude Code Extension Management - Two-Phase API"
    )

    parser.add_argument(
        "--get-questions",
        action="store_true",
        help="Phase 1: Analyze context and return questions (outputs JSON)"
    )

    parser.add_argument(
        "--execute",
        action="store_true",
        help="Phase 2: Execute operation with provided context/responses (outputs JSON)"
    )

    parser.add_argument(
        "--context",
        type=str,
        help="JSON string containing operation context"
    )

    parser.add_argument(
        "--responses",
        type=str,
        help="JSON string containing user responses for Phase 2"
    )

    args = parser.parse_args()

    try:
        # Phase 1: Get Questions
        if args.get_questions:
            context = safe_json_load(args.context) if args.context else {}
            result = get_questions(context)
            print(json.dumps(result, indent=2))
            return 0

        # Phase 2: Execute
        elif args.execute:
            context = safe_json_load(args.context) if args.context else {}
            responses = safe_json_load(args.responses) if args.responses else {}

            result = execute(context, responses)
            print(json.dumps(result, indent=2))

            return 0 if result.get("success", False) else 1

        else:
            parser.print_help()
            return 1

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        print(json.dumps({
            "success": False,
            "message": f"Validation error: {e}"
        }))
        return 1

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        print(json.dumps({
            "success": False,
            "message": f"Error: {e}",
            "error_type": type(e).__name__
        }))
        return 1


if __name__ == "__main__":
    sys.exit(main())
