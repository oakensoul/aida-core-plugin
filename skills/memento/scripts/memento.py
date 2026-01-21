#!/usr/bin/env python3
"""Memento Management Script - Two-Phase API

This script provides a two-phase API for managing mementos - persistent context
snapshots that help Claude resume work after /clear, /compact, or in new conversations.

Phase 1: get_questions(context)
    - Analyzes context and infers memento metadata
    - Returns questions that need user input (if any)
    - Detects source (manual, from-pr, from-changes)

Phase 2: execute(operation, responses, inferred)
    - Performs the requested operation (create, read, list, update, complete, remove)
    - Uses Jinja2 templates for creation
    - Returns success/failure with details

Usage:
    # Phase 1: Get questions for create
    python memento.py --get-questions --context='{"operation": "create", "description": "..."}'

    # Phase 2: Execute create
    python memento.py --execute --context='{"operation": "create", "slug": "my-memento", ...}'

    # Direct operations (no questions)
    python memento.py --execute --context='{"operation": "list", "filter": "active"}'
    python memento.py --execute --context='{"operation": "read", "slug": "my-memento"}'

Exit codes:
    0   - Success
    1   - Error occurred
"""

import sys
import json
import argparse
import re
import subprocess
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

# Default memento storage location (relative to project root)
MEMENTOS_DIR = ".claude/mementos"
ARCHIVE_DIR = ".claude/mementos/.archive"

# Template options
TEMPLATES = {
    "work-session": "work-session.md.jinja2",
    "freeform": "freeform.md.jinja2",
}


def to_kebab_case(text: str) -> str:
    """Convert text to kebab-case for memento slugs.

    Args:
        text: Input text (description)

    Returns:
        Kebab-case string suitable for memento slugs

    Examples:
        >>> to_kebab_case("Fix auth token expiry")
        'fix-auth-token-expiry'
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
    # Truncate to reasonable length
    return text[:50]


def validate_slug(slug: str) -> Tuple[bool, Optional[str]]:
    """Validate memento slug against rules.

    Args:
        slug: Memento slug to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not slug:
        return False, "Slug cannot be empty"

    if len(slug) < 2:
        return False, "Slug must be at least 2 characters"

    if len(slug) > 50:
        return False, "Slug must be at most 50 characters"

    if not re.match(r'^[a-z][a-z0-9-]*$', slug):
        return False, "Slug must start with lowercase letter and contain only lowercase letters, numbers, and hyphens"

    return True, None


def get_project_root() -> Path:
    """Find the project root by looking for .git or .claude directory."""
    cwd = Path.cwd()

    # Walk up to find project root
    for parent in [cwd] + list(cwd.parents):
        if (parent / ".git").exists() or (parent / ".claude").exists():
            return parent

    # Default to current directory
    return cwd


def get_mementos_dir(project_root: Optional[Path] = None) -> Path:
    """Get the mementos directory path.

    Args:
        project_root: Optional project root path

    Returns:
        Path to mementos directory
    """
    root = project_root or get_project_root()
    return root / MEMENTOS_DIR


def get_archive_dir(project_root: Optional[Path] = None) -> Path:
    """Get the archive directory path.

    Args:
        project_root: Optional project root path

    Returns:
        Path to archive directory
    """
    root = project_root or get_project_root()
    return root / ARCHIVE_DIR


def parse_frontmatter(content: str) -> Tuple[Dict[str, Any], str]:
    """Parse YAML frontmatter from markdown content.

    Args:
        content: Full markdown content

    Returns:
        Tuple of (frontmatter_dict, body_content)
    """
    frontmatter = {}
    body = content

    if content.startswith("---"):
        end = content.find("---", 3)
        if end > 0:
            frontmatter_text = content[3:end].strip()
            body = content[end + 3:].strip()

            # Simple YAML parsing for frontmatter
            current_key = None
            current_list = None

            for line in frontmatter_text.split('\n'):
                line = line.rstrip()

                # Handle list items
                if line.strip().startswith('- ') and current_key:
                    if current_list is None:
                        current_list = []
                    current_list.append(line.strip()[2:].strip().strip('"\''))
                    frontmatter[current_key] = current_list
                elif ':' in line and not line.strip().startswith('-'):
                    # Save previous list
                    current_list = None

                    key, value = line.split(':', 1)
                    current_key = key.strip()
                    value = value.strip()

                    # Handle JSON arrays/objects
                    if value.startswith('[') or value.startswith('{'):
                        try:
                            frontmatter[current_key] = json.loads(value)
                        except json.JSONDecodeError:
                            frontmatter[current_key] = value.strip('"\'')
                    elif value:
                        frontmatter[current_key] = value.strip('"\'')

    return frontmatter, body


def find_memento(slug: str, include_archive: bool = False) -> Optional[Dict[str, Any]]:
    """Find a memento by slug.

    Args:
        slug: Memento slug
        include_archive: Whether to search archive directory

    Returns:
        Memento info dict or None if not found
    """
    mementos_dir = get_mementos_dir()
    archive_dir = get_archive_dir()

    # Check active mementos
    memento_path = mementos_dir / f"{slug}.md"
    if memento_path.exists():
        return {
            "slug": slug,
            "path": str(memento_path),
            "archived": False,
        }

    # Check archive if requested
    if include_archive:
        archive_path = archive_dir / f"{slug}.md"
        if archive_path.exists():
            return {
                "slug": slug,
                "path": str(archive_path),
                "archived": True,
            }

    return None


def list_mementos(filter_status: str = "all") -> List[Dict[str, Any]]:
    """List all mementos.

    Args:
        filter_status: Filter by status (active, completed, all)

    Returns:
        List of memento info dictionaries
    """
    mementos = []
    mementos_dir = get_mementos_dir()
    archive_dir = get_archive_dir()

    # List active mementos
    if filter_status in ("active", "all") and mementos_dir.exists():
        for md_file in mementos_dir.glob("*.md"):
            try:
                content = md_file.read_text(encoding='utf-8')
                frontmatter, _ = parse_frontmatter(content)

                if frontmatter.get("type") == "memento":
                    mementos.append({
                        "slug": frontmatter.get("slug", md_file.stem),
                        "description": frontmatter.get("description", ""),
                        "status": frontmatter.get("status", "active"),
                        "created": frontmatter.get("created", ""),
                        "updated": frontmatter.get("updated", ""),
                        "source": frontmatter.get("source", "manual"),
                        "tags": frontmatter.get("tags", []),
                        "files": frontmatter.get("files", []),
                        "path": str(md_file),
                        "archived": False,
                    })
            except (IOError, UnicodeDecodeError):
                pass

    # List archived mementos
    if filter_status in ("completed", "all") and archive_dir.exists():
        for md_file in archive_dir.glob("*.md"):
            try:
                content = md_file.read_text(encoding='utf-8')
                frontmatter, _ = parse_frontmatter(content)

                if frontmatter.get("type") == "memento":
                    mementos.append({
                        "slug": frontmatter.get("slug", md_file.stem),
                        "description": frontmatter.get("description", ""),
                        "status": frontmatter.get("status", "completed"),
                        "created": frontmatter.get("created", ""),
                        "updated": frontmatter.get("updated", ""),
                        "source": frontmatter.get("source", "manual"),
                        "tags": frontmatter.get("tags", []),
                        "files": frontmatter.get("files", []),
                        "path": str(md_file),
                        "archived": True,
                    })
            except (IOError, UnicodeDecodeError):
                pass

    # Sort by updated date (most recent first)
    mementos.sort(key=lambda x: x.get("updated", ""), reverse=True)

    return mementos


def get_pr_context() -> Dict[str, Any]:
    """Get context from current PR using gh CLI.

    Returns:
        Dictionary with PR context or empty dict if no PR
    """
    try:
        result = subprocess.run(
            ["gh", "pr", "view", "--json", "title,body,files,number,url"],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            pr_data = json.loads(result.stdout)
            return {
                "pr_number": pr_data.get("number"),
                "pr_url": pr_data.get("url", ""),
                "title": pr_data.get("title", ""),
                "body": pr_data.get("body", ""),
                "files": [f.get("path", "") for f in pr_data.get("files", [])],
            }
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, json.JSONDecodeError):
        pass

    return {}


def get_changes_context() -> Dict[str, Any]:
    """Get context from current file changes using git.

    Returns:
        Dictionary with changes context
    """
    context = {
        "files": [],
        "summary": "",
    }

    try:
        # Get changed files
        result = subprocess.run(
            ["git", "diff", "--stat", "HEAD"],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            context["summary"] = result.stdout.strip()

        # Get list of changed files
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            context["files"] = [f for f in result.stdout.strip().split('\n') if f]

        # Also check untracked files
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            for line in result.stdout.strip().split('\n'):
                if line.startswith('?? '):
                    context["files"].append(line[3:])

    except (subprocess.TimeoutExpired, subprocess.SubprocessError):
        pass

    return context


def render_template(template_name: str, variables: Dict[str, Any]) -> str:
    """Render a Jinja2 template with variables.

    Args:
        template_name: Name of template file
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
            - operation: create, read, list, update, complete, remove
            - description: (for create) memento description
            - slug: (for read/update/complete/remove) memento slug
            - source: manual, from-pr, from-changes
            - filter: (for list) active, completed, all

    Returns:
        Dictionary containing:
            {
                "questions": [...],      # Questions needing user input
                "inferred": {...},       # Auto-detected values
                "validation": {...},     # Validation results
            }
    """
    operation = context.get("operation", "create")

    result = {
        "questions": [],
        "inferred": {},
        "validation": {"valid": True, "errors": []},
    }

    if operation == "create":
        source = context.get("source", "manual")
        description = context.get("description", "")

        # Infer from source
        if source == "from-pr":
            pr_context = get_pr_context()
            if pr_context:
                result["inferred"] = {
                    "slug": to_kebab_case(pr_context.get("title", "")),
                    "description": pr_context.get("title", ""),
                    "source": "from-pr",
                    "problem": pr_context.get("body", ""),
                    "files": pr_context.get("files", []),
                    "tags": ["pr", f"pr-{pr_context.get('pr_number', '')}"],
                }
            else:
                result["validation"]["valid"] = False
                result["validation"]["errors"].append("No PR found for current branch")
                return result

        elif source == "from-changes":
            changes_context = get_changes_context()
            if changes_context.get("files"):
                result["inferred"] = {
                    "slug": "",
                    "description": "",
                    "source": "from-changes",
                    "files": changes_context.get("files", []),
                    "tags": ["changes"],
                }
                # Ask for description since we can't infer it from changes
                result["questions"].append({
                    "id": "description",
                    "question": "What are you working on? (brief description)",
                    "type": "text",
                    "required": True,
                    "help": f"Found {len(changes_context['files'])} changed files",
                })
            else:
                result["validation"]["valid"] = False
                result["validation"]["errors"].append("No file changes found")
                return result

        else:  # manual
            if not description:
                result["questions"].append({
                    "id": "description",
                    "question": "What are you working on? (brief description)",
                    "type": "text",
                    "required": True,
                    "help": "Describe the task or problem you're solving",
                })
                return result

            result["inferred"] = {
                "slug": to_kebab_case(description),
                "description": description,
                "source": "manual",
                "tags": [],
            }

        # Ask for problem if not from PR
        if source != "from-pr" and not context.get("problem"):
            result["questions"].append({
                "id": "problem",
                "question": "What's the core problem you're solving?",
                "type": "text",
                "required": True,
            })

        # Check for slug conflicts
        inferred_slug = result["inferred"].get("slug", "")
        if inferred_slug:
            existing = find_memento(inferred_slug)
            if existing:
                result["questions"].append({
                    "id": "slug",
                    "question": f"A memento named '{inferred_slug}' already exists. Choose a different name:",
                    "type": "text",
                    "required": True,
                    "default": f"{inferred_slug}-2",
                })

    elif operation == "update":
        slug = context.get("slug")

        if not slug:
            # List available mementos for selection
            mementos = list_mementos("active")
            if mementos:
                result["questions"].append({
                    "id": "slug",
                    "question": "Which memento would you like to update?",
                    "type": "choice",
                    "options": [m["slug"] for m in mementos],
                    "required": True,
                })
            else:
                result["validation"]["valid"] = False
                result["validation"]["errors"].append("No active mementos found")
            return result

        # Load current memento to show sections
        memento = find_memento(slug)
        if not memento:
            result["validation"]["valid"] = False
            result["validation"]["errors"].append(f"Memento '{slug}' not found")
            return result

        # Read current content
        try:
            content = Path(memento["path"]).read_text(encoding='utf-8')
            frontmatter, body = parse_frontmatter(content)
            result["inferred"] = {
                "slug": slug,
                "description": frontmatter.get("description", ""),
                "current_content": body,
            }
        except IOError:
            pass

        # Ask which section to update
        if not context.get("section"):
            result["questions"].append({
                "id": "section",
                "question": "Which section would you like to update?",
                "type": "choice",
                "options": ["progress", "decisions", "next_step", "approach", "files"],
            })

        if not context.get("content"):
            result["questions"].append({
                "id": "content",
                "question": "What would you like to add?",
                "type": "text",
                "required": True,
            })

    elif operation == "read":
        slug = context.get("slug")
        if not slug:
            # List available mementos for selection
            mementos = list_mementos("active")
            if mementos:
                result["questions"].append({
                    "id": "slug",
                    "question": "Which memento would you like to read?",
                    "type": "choice",
                    "options": [m["slug"] for m in mementos],
                    "required": True,
                })
            else:
                result["validation"]["valid"] = False
                result["validation"]["errors"].append("No active mementos found")

    elif operation == "complete":
        slug = context.get("slug")
        if not slug:
            mementos = list_mementos("active")
            if mementos:
                result["questions"].append({
                    "id": "slug",
                    "question": "Which memento would you like to complete?",
                    "type": "choice",
                    "options": [m["slug"] for m in mementos],
                    "required": True,
                })
            else:
                result["validation"]["valid"] = False
                result["validation"]["errors"].append("No active mementos found")

    elif operation == "remove":
        slug = context.get("slug")
        if not slug:
            mementos = list_mementos("all")
            if mementos:
                result["questions"].append({
                    "id": "slug",
                    "question": "Which memento would you like to remove?",
                    "type": "choice",
                    "options": [m["slug"] for m in mementos],
                    "required": True,
                })
            else:
                result["validation"]["valid"] = False
                result["validation"]["errors"].append("No mementos found")

    elif operation == "list":
        result["inferred"] = {
            "filter": context.get("filter", "active"),
        }

    return result


def execute_create(context: Dict[str, Any]) -> Dict[str, Any]:
    """Execute memento creation.

    Args:
        context: Context with all required fields

    Returns:
        Result dictionary
    """
    slug = context.get("slug") or to_kebab_case(context.get("description", ""))
    description = context.get("description", "")
    source = context.get("source", "manual")
    template_type = context.get("template", "work-session")

    # Validate slug
    is_valid, error = validate_slug(slug)
    if not is_valid:
        return {"success": False, "message": f"Invalid slug: {error}"}

    # Check for conflicts
    existing = find_memento(slug)
    if existing:
        return {"success": False, "message": f"Memento '{slug}' already exists"}

    # Prepare template variables
    now = datetime.now(timezone.utc).isoformat()
    template_vars = {
        "slug": slug,
        "description": description,
        "status": "active",
        "created": now,
        "updated": now,
        "source": source,
        "tags": context.get("tags", []),
        "files": context.get("files", []),
        "problem": context.get("problem", ""),
        "approach": context.get("approach", ""),
        "completed": context.get("completed", ""),
        "in_progress": context.get("in_progress", ""),
        "pending": context.get("pending", ""),
        "decisions": context.get("decisions", ""),
        "files_detail": context.get("files_detail", ""),
        "next_step": context.get("next_step", ""),
        "content": context.get("content", ""),
    }

    # Render template
    template_name = TEMPLATES.get(template_type, TEMPLATES["work-session"])
    try:
        content = render_template(template_name, template_vars)
    except Exception as e:
        return {"success": False, "message": f"Failed to render template: {e}"}

    # Ensure directory exists
    mementos_dir = get_mementos_dir()
    mementos_dir.mkdir(parents=True, exist_ok=True)

    # Write memento file
    memento_path = mementos_dir / f"{slug}.md"
    try:
        memento_path.write_text(content, encoding='utf-8')
    except IOError as e:
        return {"success": False, "message": f"Failed to write memento: {e}"}

    return {
        "success": True,
        "message": f"Created memento '{slug}'",
        "path": str(memento_path),
        "slug": slug,
    }


def execute_read(context: Dict[str, Any]) -> Dict[str, Any]:
    """Execute memento read.

    Args:
        context: Context with slug

    Returns:
        Result dictionary with memento content
    """
    slug = context.get("slug")

    if not slug:
        return {"success": False, "message": "Slug is required"}

    memento = find_memento(slug, include_archive=True)
    if not memento:
        return {"success": False, "message": f"Memento '{slug}' not found"}

    try:
        content = Path(memento["path"]).read_text(encoding='utf-8')
        frontmatter, body = parse_frontmatter(content)

        return {
            "success": True,
            "slug": slug,
            "content": content,
            "body": body,
            "frontmatter": frontmatter,
            "path": memento["path"],
            "archived": memento["archived"],
        }
    except IOError as e:
        return {"success": False, "message": f"Failed to read memento: {e}"}


def execute_list(context: Dict[str, Any]) -> Dict[str, Any]:
    """Execute memento listing.

    Args:
        context: Context with filter

    Returns:
        Result dictionary with mementos list
    """
    filter_status = context.get("filter", "active")
    mementos = list_mementos(filter_status)

    return {
        "success": True,
        "mementos": mementos,
        "count": len(mementos),
        "filter": filter_status,
    }


def execute_update(context: Dict[str, Any]) -> Dict[str, Any]:
    """Execute memento update.

    Args:
        context: Context with slug, section, and content

    Returns:
        Result dictionary
    """
    slug = context.get("slug")
    section = context.get("section")
    new_content = context.get("content", "")

    if not slug:
        return {"success": False, "message": "Slug is required"}

    memento = find_memento(slug)
    if not memento:
        return {"success": False, "message": f"Memento '{slug}' not found"}

    memento_path = Path(memento["path"])

    try:
        content = memento_path.read_text(encoding='utf-8')
        frontmatter, body = parse_frontmatter(content)

        # Update the timestamp
        now = datetime.now(timezone.utc).isoformat()

        # Reconstruct frontmatter
        frontmatter["updated"] = now

        # Build new content based on section
        if section == "progress":
            # Find and update the "### In Progress" section
            body = re.sub(
                r'(### In Progress\s*\n)(.*?)(\n##|\n---|\Z)',
                f'\\g<1>{new_content}\n\\g<3>',
                body,
                flags=re.DOTALL
            )
        elif section == "decisions":
            body = re.sub(
                r'(## Key Decisions\s*\n)(.*?)(\n##|\n---|\Z)',
                f'\\g<1>{new_content}\n\\g<3>',
                body,
                flags=re.DOTALL
            )
        elif section == "next_step":
            body = re.sub(
                r'(## Next Step\s*\n)(.*?)(\n---|\Z)',
                f'\\g<1>{new_content}\n\\g<3>',
                body,
                flags=re.DOTALL
            )
        elif section == "approach":
            body = re.sub(
                r'(## Approach\s*\n)(.*?)(\n##|\n---|\Z)',
                f'\\g<1>{new_content}\n\\g<3>',
                body,
                flags=re.DOTALL
            )
        elif section == "files":
            body = re.sub(
                r'(## Files\s*\n)(.*?)(\n##|\n---|\Z)',
                f'\\g<1>{new_content}\n\\g<3>',
                body,
                flags=re.DOTALL
            )
        else:
            # Append to end if section not recognized
            body = body.rstrip() + f"\n\n## {section.title()}\n\n{new_content}\n"

        # Rebuild frontmatter string
        frontmatter_lines = ["---"]
        for key, value in frontmatter.items():
            if isinstance(value, list):
                frontmatter_lines.append(f"{key}: {json.dumps(value)}")
            else:
                frontmatter_lines.append(f"{key}: {value}")
        frontmatter_lines.append("---")

        new_file_content = '\n'.join(frontmatter_lines) + '\n\n' + body.strip() + '\n'

        memento_path.write_text(new_file_content, encoding='utf-8')

        return {
            "success": True,
            "message": f"Updated {section} section",
            "path": str(memento_path),
            "slug": slug,
        }

    except IOError as e:
        return {"success": False, "message": f"Failed to update memento: {e}"}


def execute_complete(context: Dict[str, Any]) -> Dict[str, Any]:
    """Execute memento completion (archive).

    Args:
        context: Context with slug

    Returns:
        Result dictionary
    """
    slug = context.get("slug")

    if not slug:
        return {"success": False, "message": "Slug is required"}

    memento = find_memento(slug)
    if not memento:
        return {"success": False, "message": f"Memento '{slug}' not found"}

    source_path = Path(memento["path"])
    archive_dir = get_archive_dir()

    try:
        # Update status in file
        content = source_path.read_text(encoding='utf-8')
        content = re.sub(r'status:\s*\w+', 'status: completed', content)

        # Update timestamp
        now = datetime.now(timezone.utc).isoformat()
        content = re.sub(r'updated:\s*[^\n]+', f'updated: {now}', content)

        # Ensure archive directory exists
        archive_dir.mkdir(parents=True, exist_ok=True)

        # Move to archive
        dest_path = archive_dir / f"{slug}.md"
        dest_path.write_text(content, encoding='utf-8')
        source_path.unlink()

        return {
            "success": True,
            "message": f"Completed and archived memento '{slug}'",
            "path": str(dest_path),
            "slug": slug,
        }

    except IOError as e:
        return {"success": False, "message": f"Failed to complete memento: {e}"}


def execute_remove(context: Dict[str, Any]) -> Dict[str, Any]:
    """Execute memento removal.

    Args:
        context: Context with slug

    Returns:
        Result dictionary
    """
    slug = context.get("slug")

    if not slug:
        return {"success": False, "message": "Slug is required"}

    memento = find_memento(slug, include_archive=True)
    if not memento:
        return {"success": False, "message": f"Memento '{slug}' not found"}

    try:
        Path(memento["path"]).unlink()
        return {
            "success": True,
            "message": f"Removed memento '{slug}'",
            "slug": slug,
        }
    except IOError as e:
        return {"success": False, "message": f"Failed to remove memento: {e}"}


def execute(context: Dict[str, Any], responses: Dict[str, Any] = None) -> Dict[str, Any]:
    """Execute the requested operation (Phase 2).

    Args:
        context: Operation context
        responses: User responses to questions (if any)

    Returns:
        Result dictionary
    """
    operation = context.get("operation", "create")

    # Merge responses into context
    if responses:
        context.update(responses)

    if operation == "create":
        return execute_create(context)
    elif operation == "read":
        return execute_read(context)
    elif operation == "list":
        return execute_list(context)
    elif operation == "update":
        return execute_update(context)
    elif operation == "complete":
        return execute_complete(context)
    elif operation == "remove":
        return execute_remove(context)
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
        description="Memento Management - Two-Phase API"
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
