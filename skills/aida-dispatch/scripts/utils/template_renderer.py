"""Template rendering utilities using Jinja2.

This module provides template rendering functionality for AIDA skill generation,
supporting both single file rendering and recursive directory rendering with
variable substitution in both file contents and filenames.
"""

import os
from pathlib import Path
from typing import Dict

from jinja2.sandbox import SandboxedEnvironment
from jinja2 import StrictUndefined, UndefinedError

from .errors import FileOperationError
from .files import read_file, write_file
from .paths import ensure_directory


# Binary file extensions to skip during rendering
BINARY_EXTENSIONS = {
    '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.ico',
    '.pdf', '.zip', '.tar', '.gz', '.bz2', '.xz',
    '.exe', '.dll', '.so', '.dylib',
    '.mp3', '.mp4', '.avi', '.mov',
    '.woff', '.woff2', '.ttf', '.otf', '.eot',
}

# Template security constants
MAX_TEMPLATE_SIZE = 1_000_000  # 1MB maximum template file size
MAX_VARIABLE_VALUE_SIZE = 10_000  # 10KB maximum per variable value
MAX_VARIABLES = 100  # Maximum number of template variables
JINJA2_EXTENSION = '.jinja2'  # Template file extension

# Reserved variable names (prevent Python attribute access)
RESERVED_VARIABLE_NAMES = {
    '__class__', '__init__', '__globals__', '__builtins__',
    'config', 'self', 'request', 'session', 'g'
}


def validate_template_variables(variables: Dict[str, str]) -> None:
    """Validate template variables for security.

    Args:
        variables: Template variables to validate

    Raises:
        ValueError: If variables contain unsafe content

    Security:
        - Prevents template injection via variable values
        - Validates variable names to prevent attribute access
        - Enforces size limits to prevent DoS
    """
    if len(variables) > MAX_VARIABLES:
        raise ValueError(
            f"Too many template variables: {len(variables)} (max {MAX_VARIABLES})"
        )

    for key, value in variables.items():
        # Validate variable name
        if not isinstance(key, str) or not key.isidentifier():
            raise ValueError(f"Invalid variable name: {key}")

        if key.startswith('_'):
            raise ValueError(
                f"Variable name cannot start with underscore: {key}"
            )

        if key.lower() in RESERVED_VARIABLE_NAMES:
            raise ValueError(f"Reserved variable name: {key}")

        # Validate variable value
        if not isinstance(value, str):
            raise ValueError(f"Variable {key} must be a string, got {type(value)}")

        if len(value) > MAX_VARIABLE_VALUE_SIZE:
            raise ValueError(
                f"Variable {key} value too long: {len(value)} bytes "
                f"(max {MAX_VARIABLE_VALUE_SIZE})"
            )

        # Check for template injection attempts
        if '{{' in value or '{%' in value or '{#' in value:
            raise ValueError(
                f"Variable {key} contains Jinja2 template syntax. "
                f"Template syntax in variables is not allowed for security reasons."
            )


def sanitize_path_component(name: str) -> str:
    """Sanitize a path component to prevent directory traversal.

    Args:
        name: Path component (filename or directory name)

    Returns:
        Sanitized path component

    Raises:
        ValueError: If path component is unsafe

    Security:
        - Prevents directory traversal via .. or /
        - Validates against null bytes
        - Rejects absolute paths
    """
    # Check for path separators
    if '/' in name or '\\' in name or os.sep in name:
        raise ValueError(
            f"Path component cannot contain separators: {name}"
        )

    # Check for parent directory references
    if name in {'.', '..'}:
        raise ValueError(f"Invalid path component: {name}")

    # Check for absolute paths
    if os.path.isabs(name):
        raise ValueError(f"Path component cannot be absolute: {name}")

    # Check for null bytes
    if '\0' in name:
        raise ValueError("Path component cannot contain null bytes")

    return name


def render_template(template_path: Path, variables: Dict[str, str]) -> str:
    """Render a single template file with variables using sandboxed Jinja2.

    Uses Jinja2 SandboxedEnvironment with StrictUndefined to ensure security
    and proper error handling.

    Args:
        template_path: Path to jinja2 template file (.jinja2 extension)
        variables: Dict of variable names to values (will be validated)

    Returns:
        str: Rendered template content

    Raises:
        FileOperationError: If template file cannot be read or exceeds size limit
        ValueError: If template contains undefined variable or invalid input

    Security:
        - Uses sandboxed Jinja2 environment to prevent code execution
        - Validates all template variables before rendering
        - Enforces template size limits
        - Autoescape disabled intentionally (markdown templates)
        - Restricted filter and function set

    Example:
        >>> variables = {"skill_name": "my-skill", "description": "My skill"}
        >>> content = render_template(Path("template.md.jinja2"), variables)
        >>> print(content)
        # My Skill
        Description: My skill
    """
    try:
        # Security: Validate template variables
        validate_template_variables(variables)

        # Read template content
        template_content = read_file(template_path, max_size=MAX_TEMPLATE_SIZE)

        # Create sandboxed environment with security settings
        env = SandboxedEnvironment(
            undefined=StrictUndefined,
            autoescape=False,  # Intentionally disabled for markdown templates
            enable_async=False,
            auto_reload=False
        )

        # Render template from string
        template = env.from_string(template_content)
        rendered = template.render(**variables)
        return rendered

    except UndefinedError as e:
        # Provide helpful error message with template path and variable name
        raise ValueError(
            f"Template rendering failed: {template_path}\n"
            f"Undefined variable: {e}\n"
            f"Available variables: {', '.join(sorted(variables.keys()))}"
        ) from e
    except FileOperationError:
        # Re-raise file operation errors as-is
        raise


def render_filename(filename: str, variables: Dict[str, str]) -> str:
    """Render a filename template with variables and sanitize result.

    Supports variable substitution in filenames, e.g., "{{skill_name}}.md"
    becomes "my-skill.md" when variables contains {"skill_name": "my-skill"}.

    Args:
        filename: Filename that may contain Jinja2 variables
        variables: Dict of variable names to values

    Returns:
        str: Rendered and sanitized filename

    Raises:
        ValueError: If filename template contains undefined variable or results
                    in unsafe path component

    Security:
        - Validates template variables before rendering
        - Sanitizes rendered filename to prevent directory traversal
        - Uses sandboxed environment

    Example:
        >>> render_filename("{{skill_name}}.md", {"skill_name": "my-skill"})
        'my-skill.md'
    """
    try:
        # Security: Validate variables first
        validate_template_variables(variables)

        # Create sandboxed environment
        env = SandboxedEnvironment(undefined=StrictUndefined)
        template = env.from_string(filename)
        rendered = template.render(**variables)

        # Security: Sanitize the rendered filename
        sanitized = sanitize_path_component(rendered)
        return sanitized

    except UndefinedError as e:
        raise ValueError(
            f"Filename template rendering failed: {filename}\n"
            f"Undefined variable: {e}\n"
            f"Available variables: {', '.join(sorted(variables.keys()))}"
        ) from e


def is_binary_file(path: Path) -> bool:
    """Check if a file is binary based on its extension.

    Args:
        path: File path to check

    Returns:
        bool: True if file has a binary extension, False otherwise

    Example:
        >>> is_binary_file(Path("image.png"))
        True
        >>> is_binary_file(Path("document.md"))
        False
    """
    return path.suffix.lower() in BINARY_EXTENSIONS


def is_template_file(path: Path) -> bool:
    """Check if a file is a Jinja2 template file.

    Template files must have .jinja2 extension (can be compound like .md.jinja2).

    Args:
        path: File path to check

    Returns:
        bool: True if file ends with .jinja2, False otherwise

    Example:
        >>> is_template_file(Path("SKILL.md.jinja2"))
        True
        >>> is_template_file(Path("image.png"))
        False
    """
    return path.suffix == '.jinja2'


def get_output_filename(template_path: Path, variables: Dict[str, str]) -> str:
    """Get the output filename for a template file.

    Removes .jinja2 extension and renders any remaining template variables.
    For example, "{{skill_name}}.md.jinja2" becomes "my-skill.md".

    Args:
        template_path: Path to template file
        variables: Dict of variable names to values

    Returns:
        str: Output filename with .jinja2 removed and variables rendered

    Raises:
        ValueError: If filename template contains undefined variable

    Example:
        >>> get_output_filename(Path("{{skill_name}}.md.jinja2"), {"skill_name": "test"})
        'test.md'
    """
    # Remove .jinja2 extension
    filename = template_path.name
    if filename.endswith(JINJA2_EXTENSION):
        filename = filename[:-len(JINJA2_EXTENSION)]

    # Render any template variables in the filename (includes sanitization)
    return render_filename(filename, variables)


def render_skill_directory(
    template_dir: Path,
    output_dir: Path,
    variables: Dict[str, str]
) -> None:
    """Render entire skill directory from templates.

    Recursively processes a template directory, rendering all .jinja2 files
    and preserving directory structure. Template filenames can include variables.
    Binary files are skipped. Non-template files are ignored.

    Args:
        template_dir: Source template directory (e.g., templates/blueprints/skill-name/)
        output_dir: Destination directory for rendered files (e.g., ~/.claude/skills/skill-name/)
        variables: Template variables for substitution

    Raises:
        FileOperationError: If directory operations fail
        ValueError: If template rendering fails or undefined variable encountered

    Example:
        >>> template_dir = Path("templates/blueprints/personal-preferences")
        >>> output_dir = Path("~/.claude/skills/personal-preferences")
        >>> variables = {
        ...     "skill_name": "personal-preferences",
        ...     "description": "Personal coding preferences",
        ...     "coding_standards": "PEP 8"
        ... }
        >>> render_skill_directory(template_dir, output_dir, variables)
    """
    # Ensure template directory exists
    if not template_dir.exists():
        raise FileOperationError(
            f"Template directory not found: {template_dir}",
            "Verify the template directory path is correct."
        )

    if not template_dir.is_dir():
        raise FileOperationError(
            f"Template path is not a directory: {template_dir}",
            "Provide a path to a directory containing templates."
        )

    # Ensure output directory exists
    ensure_directory(output_dir)

    # Process all files recursively
    _render_directory_recursive(template_dir, output_dir, template_dir, variables)


def _render_directory_recursive(
    template_dir: Path,
    output_dir: Path,
    base_template_dir: Path,
    variables: Dict[str, str]
) -> None:
    """Recursively render directory contents with security validation.

    This is an internal helper function for render_skill_directory.

    Args:
        template_dir: Current template directory being processed
        output_dir: Current output directory
        base_template_dir: Original base template directory (for relative paths)
        variables: Template variables

    Raises:
        FileOperationError: If security violation detected (symlinks, path traversal)

    Security:
        - Rejects symlinks to prevent directory traversal attacks
        - Validates paths stay within base template directory
        - Sanitizes all rendered filenames
    """
    # Iterate through all items in the template directory
    for item in template_dir.iterdir():
        # Security: Skip symlinks to prevent directory traversal
        if item.is_symlink():
            continue

        if item.is_dir():
            # Security: Ensure directory is still within base template directory
            try:
                item.resolve().relative_to(base_template_dir.resolve())
            except ValueError:
                # Directory is outside the base - potential symlink attack
                raise FileOperationError(
                    f"Security violation: Path outside template directory: {item}",
                    "Symlinks are not allowed in template directories."
                )

            # Recursively process subdirectories
            # Render directory name (may contain variables) - already sanitized
            rendered_dirname = render_filename(item.name, variables)
            new_output_dir = output_dir / rendered_dirname
            ensure_directory(new_output_dir)

            _render_directory_recursive(item, new_output_dir, base_template_dir, variables)

        elif item.is_file():
            # Skip binary files
            if is_binary_file(item):
                continue

            # Only process template files (.jinja2)
            if not is_template_file(item):
                continue

            # Get output filename (removes .jinja2 and renders variables)
            output_filename = get_output_filename(item, variables)
            output_path = output_dir / output_filename

            try:
                # Render template content
                rendered_content = render_template(item, variables)

                # Write rendered content to output file
                write_file(output_path, rendered_content)

            except ValueError as e:
                # Add context about which file failed
                relative_path = item.relative_to(base_template_dir)
                raise ValueError(
                    f"Failed to render template: {relative_path}\n"
                    f"{str(e)}"
                ) from e
