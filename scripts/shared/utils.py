"""Shared utilities for AIDA Core Plugin scripts.

Common functions used across multiple skills including
claude-code-management and create-plugin.
"""

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional


def safe_json_load(json_str: str) -> dict[str, Any]:
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


def validate_name(name: str) -> tuple[bool, Optional[str]]:
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
        return False, (
            "Name must start with lowercase letter and contain only "
            "lowercase letters, numbers, and hyphens"
        )

    return True, None


def validate_description(description: str) -> tuple[bool, Optional[str]]:
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


def validate_version(version: str) -> tuple[bool, Optional[str]]:
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


def parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """Parse YAML frontmatter from markdown content.

    Args:
        content: Full markdown content

    Returns:
        Tuple of (frontmatter_dict, body_content)
    """
    frontmatter: dict[str, Any] = {}
    body = content

    if content.startswith("---"):
        end = content.find("---", 3)
        if end > 0:
            frontmatter_text = content[3:end].strip()
            body = content[end + 3:].strip()

            for line in frontmatter_text.split('\n'):
                if ':' in line and not line.strip().startswith('-'):
                    key, value = line.split(':', 1)
                    frontmatter[key.strip()] = value.strip().strip('"\'')

    return frontmatter, body


@lru_cache(maxsize=16)
def _get_jinja_env(templates_dir: str) -> Any:
    """Get or create a cached Jinja2 Environment for a templates directory.

    Args:
        templates_dir: String path to templates directory (string for hashability)

    Returns:
        Configured Jinja2 Environment
    """
    from jinja2 import Environment, FileSystemLoader

    return Environment(
        loader=FileSystemLoader(templates_dir),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )


def render_template(templates_dir: Path, template_name: str, variables: dict[str, Any]) -> str:
    """Render a Jinja2 template with variables.

    Args:
        templates_dir: Path to templates directory
        template_name: Name of template file relative to templates/
        variables: Template variables

    Returns:
        Rendered template string
    """
    try:
        import jinja2  # noqa: F401
    except ImportError:
        raise RuntimeError("Jinja2 is required. Install with: pip install jinja2")

    env = _get_jinja_env(str(templates_dir))
    template = env.get_template(template_name)
    return template.render(**variables)


def get_project_root() -> Path:
    """Find the project root by looking for .git or .claude directory."""
    cwd = Path.cwd()
    for parent in [cwd] + list(cwd.parents):
        if (parent / ".git").exists() or (parent / ".claude").exists():
            return parent
    return cwd


# Location mappings for extensions - computed at import time for backward
# compatibility (existing code references LOCATION_PATHS directly)
LOCATION_PATHS = {
    "user": Path.home() / ".claude",
    "project": Path.cwd() / ".claude",
    "plugin": None,  # Determined by context
}


def get_location_path(location: str, plugin_path: Optional[str] = None) -> Path:
    """Get the base path for a location.

    Resolves paths at call time (not import time) for user and project locations.

    Args:
        location: Location type (user, project, plugin)
        plugin_path: Path to plugin directory (required if location is plugin)

    Returns:
        Path to the location directory
    """
    if location == "plugin":
        if plugin_path:
            return Path(plugin_path)
        return Path.cwd()
    if location == "user":
        return Path.home() / ".claude"
    if location == "project":
        return Path.cwd() / ".claude"
    return Path.cwd() / ".claude"
