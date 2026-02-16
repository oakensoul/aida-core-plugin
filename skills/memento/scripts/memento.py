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

import os
import sys
import json
import argparse
import re
import subprocess
import logging
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import yaml

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
    # Truncate to reasonable length and strip trailing hyphens
    return text[:50].rstrip('-')


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
        return False, (
            "Slug must start with lowercase letter and contain"
            " only lowercase letters, numbers, and hyphens"
        )

    return True, None


def sanitize_git_url(url: str) -> str:
    """Remove embedded credentials from git remote URLs.

    Args:
        url: Raw git remote URL

    Returns:
        URL with credentials replaced by '***'
    """
    return re.sub(r'(://)[^@/]+@', r'\1***@', url)


def validate_project_name(name: str) -> Tuple[bool, Optional[str]]:
    """Validate project name for safe use in filenames.

    Args:
        name: Project name to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not name:
        return False, "Project name cannot be empty"
    if '--' in name:
        return False, (
            f"Project name '{name}' contains '--' separator; "
            "rename directory to avoid ambiguity"
        )
    if '..' in name or '/' in name or '\\' in name:
        return False, "Project name contains path traversal characters"
    if len(name) > 100:
        return False, "Project name must be at most 100 characters"
    if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9._-]*$', name):
        return False, "Project name contains invalid characters"
    return True, None


def _ensure_within_dir(path: Path, base_dir: Path) -> Path:
    """Validate that a path stays within a base directory.

    Also rejects symlinks to prevent symlink-based attacks.

    Args:
        path: Path to validate
        base_dir: Allowed base directory

    Returns:
        The resolved path

    Raises:
        ValueError: If path escapes base_dir or is a symlink
    """
    if path.is_symlink():
        raise ValueError(f"Symlink detected at {path}")
    resolved = path.resolve()
    base_resolved = base_dir.resolve()

    # Use Path.relative_to() for proper path containment validation
    # This prevents bypasses that string-based startswith() is vulnerable to
    try:
        resolved.relative_to(base_resolved)
    except ValueError:
        raise ValueError(f"Path escape detected: {resolved}")

    return resolved


def _atomic_write(path: Path, content: str) -> None:
    """Write content to a file atomically via temp-file-then-rename.

    Prevents partial writes from corrupting mementos if the process
    is interrupted mid-write.

    Args:
        path: Target file path
        content: Content to write
    """
    fd, tmp_path = tempfile.mkstemp(
        dir=str(path.parent),
        prefix=".memento-",
        suffix=".tmp",
    )
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(content)
        os.chmod(tmp_path, 0o600)
        os.replace(tmp_path, str(path))
    except BaseException:
        # BaseException: clean up temp even on KeyboardInterrupt/SystemExit
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


# Module-level cache for project context (short-lived CLI process)
_project_context_cache: Optional[Dict[str, Any]] = None


def _reset_project_context_cache() -> None:
    """Reset the project context cache. For testing only."""
    global _project_context_cache
    _project_context_cache = None


def get_project_context() -> Dict[str, Any]:
    """Detect project name, path, repository, and branch from git.

    Walks up directories looking for .git, then runs git commands
    to get remote URL and current branch. Falls back to cwd name
    if not in a git repository. Results are cached for the process
    lifetime.

    Returns:
        Dictionary with keys: name, path, repo, branch
    """
    global _project_context_cache
    if _project_context_cache is not None:
        return _project_context_cache

    cwd = Path.cwd()

    # Find git root by walking up
    git_root = None
    for parent in [cwd] + list(cwd.parents):
        if (parent / ".git").exists():
            git_root = parent
            break

    if git_root is None:
        _project_context_cache = {
            "name": cwd.name,
            "path": str(cwd),
            "repo": "",
            "branch": "",
        }
        return _project_context_cache

    # Get remote URL
    repo = ""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=str(git_root),
        )
        if result.returncode == 0:
            repo = sanitize_git_url(result.stdout.strip())
    except (subprocess.TimeoutExpired, subprocess.SubprocessError):
        pass

    # Get current branch
    branch = ""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=str(git_root),
        )
        if result.returncode == 0:
            branch = result.stdout.strip()
    except (subprocess.TimeoutExpired, subprocess.SubprocessError):
        pass

    _project_context_cache = {
        "name": git_root.name,
        "path": str(git_root),
        "repo": repo,
        "branch": branch,
    }
    return _project_context_cache


def get_user_mementos_dir() -> Path:
    """Get the user-level mementos directory path.

    Returns:
        Path to ~/.claude/memento/
    """
    return Path.home() / ".claude" / "memento"


def get_user_archive_dir() -> Path:
    """Get the user-level archive directory path.

    Returns:
        Path to ~/.claude/memento/.completed/
    """
    return get_user_mementos_dir() / ".completed"


def make_memento_filename(project_name: str, slug: str) -> str:
    """Create a namespaced memento filename.

    Args:
        project_name: Project name (e.g. "my-project")
        slug: Memento slug (e.g. "fix-auth-bug")

    Returns:
        Filename string like "my-project--fix-auth-bug.md"

    Raises:
        ValueError: If project name contains '--' or invalid chars
    """
    is_valid, error = validate_project_name(project_name)
    if not is_valid:
        raise ValueError(error)
    return f"{project_name}--{slug}.md"


def parse_memento_filename(filename: str) -> Tuple[str, str]:
    """Parse a namespaced memento filename into project and slug.

    Args:
        filename: Filename like "my-project--fix-auth-bug.md"

    Returns:
        Tuple of (project_name, slug)

    Raises:
        ValueError: If filename doesn't contain '--' separator
    """
    # Strip .md extension if present
    name = filename
    if name.endswith(".md"):
        name = name[:-3]

    idx = name.find("--")
    if idx < 0:
        raise ValueError(
            f"Filename '{filename}' does not contain '--' separator"
        )

    project_name = name[:idx]
    slug = name[idx + 2:]
    return project_name, slug


def parse_frontmatter(content: str) -> Tuple[Dict[str, Any], str]:
    """Parse YAML frontmatter from markdown content.

    Uses PyYAML's safe_load for robust parsing of all standard YAML
    including nested blocks, lists, and quoted strings.

    Args:
        content: Full markdown content

    Returns:
        Tuple of (frontmatter_dict, body_content)
    """
    if not content.startswith("---"):
        return {}, content

    end = content.find("\n---", 3)
    if end < 0:
        return {}, content

    frontmatter_text = content[3:end].strip()
    body = content[end + 4:].strip()

    try:
        parsed = yaml.safe_load(frontmatter_text)
        if not isinstance(parsed, dict):
            return {}, body
        return parsed, body
    except yaml.YAMLError:
        return {}, body


def _rebuild_file(frontmatter: Dict[str, Any], body: str) -> str:
    """Rebuild a memento file from frontmatter dict and body text.

    Args:
        frontmatter: Parsed frontmatter dictionary
        body: Markdown body content

    Returns:
        Complete file content with YAML frontmatter
    """
    fm_text = yaml.dump(
        frontmatter,
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
    ).rstrip('\n')
    return f"---\n{fm_text}\n---\n\n{body.strip()}\n"


def find_memento(
    slug: str,
    include_archive: bool = False,
    project_name: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Find a memento by slug.

    Args:
        slug: Memento slug
        include_archive: Whether to search archive directory
        project_name: Project name for filename lookup (auto-detected if None)

    Returns:
        Memento info dict or None if not found
    """
    if project_name is None:
        project_name = get_project_context()["name"]

    mementos_dir = get_user_mementos_dir()
    archive_dir = get_user_archive_dir()
    filename = make_memento_filename(project_name, slug)

    # Check active mementos.
    # Note: TOCTOU gap between check and use is accepted because
    # ~/.claude/memento/ is 0o700 (owner-only), and an attacker with
    # write access there already has full user privileges.
    memento_path = mementos_dir / filename
    if memento_path.exists():
        try:
            _ensure_within_dir(memento_path, mementos_dir)
        except ValueError:
            return None
        return {
            "slug": slug,
            "project": project_name,
            "path": str(memento_path),
            "archived": False,
        }

    # Check archive if requested
    if include_archive:
        archive_path = archive_dir / filename
        if archive_path.exists():
            try:
                _ensure_within_dir(archive_path, archive_dir)
            except ValueError:
                return None
            return {
                "slug": slug,
                "project": project_name,
                "path": str(archive_path),
                "archived": True,
            }

    return None


def list_mementos(
    filter_status: str = "all",
    project_filter: Optional[str] = None,
    all_projects: bool = False,
) -> List[Dict[str, Any]]:
    """List mementos, optionally filtered by project.

    Args:
        filter_status: Filter by status (active, completed, all)
        project_filter: Filter to a specific project name
        all_projects: If True, show mementos from all projects

    Returns:
        List of memento info dictionaries
    """
    mementos = []
    mementos_dir = get_user_mementos_dir()
    archive_dir = get_user_archive_dir()

    # Determine which project to filter to
    if not all_projects:
        target_project = project_filter or get_project_context()["name"]
    else:
        target_project = None

    def _scan_dir(directory: Path, archived: bool, default_status: str):
        """Scan a directory for memento files."""
        if not directory.exists():
            return
        for md_file in directory.glob("*.md"):
            # Skip symlinks
            if md_file.is_symlink():
                continue
            try:
                # Extract project from filename
                file_project, file_slug = parse_memento_filename(
                    md_file.name
                )
            except ValueError:
                continue

            # Apply project filter
            if target_project and file_project != target_project:
                continue

            try:
                content = md_file.read_text(encoding='utf-8')
                frontmatter, _ = parse_frontmatter(content)

                if frontmatter.get("type") == "memento":
                    mementos.append({
                        "slug": frontmatter.get("slug", file_slug),
                        "project": file_project,
                        "description": frontmatter.get("description", ""),
                        "status": frontmatter.get(
                            "status", default_status
                        ),
                        "created": frontmatter.get("created", ""),
                        "updated": frontmatter.get("updated", ""),
                        "source": frontmatter.get("source", "manual"),
                        "tags": frontmatter.get("tags", []),
                        "files": frontmatter.get("files", []),
                        "path": str(md_file),
                        "archived": archived,
                    })
            except (IOError, UnicodeDecodeError):
                pass

    # List active mementos
    if filter_status in ("active", "all"):
        _scan_dir(mementos_dir, archived=False, default_status="active")

    # List archived mementos
    if filter_status in ("completed", "all"):
        _scan_dir(archive_dir, archived=True, default_status="completed")

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
                    "question": (
                        f"A memento named '{inferred_slug}'"
                        " already exists."
                        " Choose a different name:"
                    ),
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
            "all_projects": context.get("all_projects", False),
            "project_filter": context.get("project_filter"),
        }

    return result


def execute_create(context: Dict[str, Any]) -> Dict[str, Any]:
    """Execute memento creation.

    Args:
        context: Context with all required fields

    Returns:
        Result dictionary
    """
    slug = context.get("slug") or to_kebab_case(
        context.get("description", "")
    )
    description = context.get("description", "")
    source = context.get("source", "manual")
    template_type = context.get("template", "work-session")

    # Centralized validation in execute() only fires when slug is
    # already in the context dict. When we generate it here from
    # the description, we must validate explicitly.
    is_valid, error = validate_slug(slug)
    if not is_valid:
        return {"success": False, "message": f"Invalid slug: {error}"}

    # Get project context
    project_ctx = get_project_context()
    project_name = project_ctx["name"]

    # Check for conflicts
    existing = find_memento(slug, project_name=project_name)
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
        "project_name": project_ctx["name"],
        "project_path": project_ctx["path"],
        "project_repo": project_ctx["repo"],
        "project_branch": project_ctx["branch"],
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

    # Ensure directory exists with restrictive permissions
    mementos_dir = get_user_mementos_dir()
    mementos_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(str(mementos_dir), 0o700)

    # Write memento file atomically
    filename = make_memento_filename(project_name, slug)
    memento_path = mementos_dir / filename
    try:
        _ensure_within_dir(memento_path, mementos_dir)
    except ValueError as e:
        return {"success": False, "message": f"Path validation failed: {e}"}
    try:
        _atomic_write(memento_path, content)
    except IOError as e:
        return {"success": False, "message": f"Failed to write memento: {e}"}

    return {
        "success": True,
        "message": f"Created memento '{slug}'",
        "path": str(memento_path),
        "slug": slug,
        "project": project_name,
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
        context: Context with filter, project_filter, all_projects

    Returns:
        Result dictionary with mementos list
    """
    filter_status = context.get("filter", "active")
    all_projects = context.get("all_projects", False)
    project_filter = context.get("project_filter")

    mementos = list_mementos(
        filter_status,
        project_filter=project_filter,
        all_projects=all_projects,
    )

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

    if not section:
        return {"success": False, "message": "Section is required for update"}

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

        # Build new content based on section.
        # Note: section headings are coupled to work-session template
        # structure. Freeform mementos fall through to the else branch.
        # Lambda replacements prevent regex backreference injection
        # from user content containing \1 or \g<1>.
        section_patterns = {
            "progress": r'(### In Progress[ \t]*\n)(.*?)(\n##|\n---|\Z)',
            "decisions": r'(## Key Decisions[ \t]*\n)(.*?)(\n##|\n---|\Z)',
            "next_step": r'(## Next Step[ \t]*\n)(.*?)(\n---|\Z)',
            "approach": r'(## Approach[ \t]*\n)(.*?)(\n##|\n---|\Z)',
            "files": r'(## Files[ \t]*\n)(.*?)(\n##|\n---|\Z)',
        }

        pattern = section_patterns.get(section)
        if pattern:
            new_body = re.sub(
                pattern,
                lambda m: m.group(1) + new_content + '\n' + m.group(3),
                body,
                flags=re.DOTALL,
            )
            if new_body != body:
                body = new_body
            else:
                # Section heading not found (e.g. freeform template);
                # fall through to append
                body = (
                    body.rstrip()
                    + f"\n\n## {section.title()}\n\n"
                    + new_content + "\n"
                )
        else:
            # Section name not recognized; append new section
            body = (
                body.rstrip()
                + f"\n\n## {section.title()}\n\n"
                + new_content + "\n"
            )

        _atomic_write(memento_path, _rebuild_file(frontmatter, body))

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

    project_name = get_project_context()["name"]
    memento = find_memento(slug, project_name=project_name)
    if not memento:
        return {"success": False, "message": f"Memento '{slug}' not found"}

    source_path = Path(memento["path"])
    archive_dir = get_user_archive_dir()

    try:
        # Parse and update frontmatter structurally
        raw_content = source_path.read_text(encoding='utf-8')
        frontmatter, body = parse_frontmatter(raw_content)

        frontmatter["status"] = "completed"
        now = datetime.now(timezone.utc).isoformat()
        frontmatter["updated"] = now

        content = _rebuild_file(frontmatter, body)

        # Ensure archive directory exists
        archive_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(str(archive_dir), 0o700)

        # Move to archive (preserve namespaced filename).
        # This is intentionally write-then-unlink rather than a single
        # atomic rename, because we need to update frontmatter status.
        # Failure between write and unlink produces duplication (safe),
        # not data loss.
        filename = make_memento_filename(project_name, slug)
        dest_path = archive_dir / filename
        try:
            _ensure_within_dir(dest_path, archive_dir)
        except ValueError as e:
            return {
                "success": False,
                "message": f"Path validation failed: {e}",
            }
        _atomic_write(dest_path, content)
        source_path.unlink()

        return {
            "success": True,
            "message": f"Completed and archived memento '{slug}'",
            "path": str(dest_path),
            "slug": slug,
            "project": project_name,
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


def execute(
    context: Dict[str, Any],
    responses: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Execute the requested operation (Phase 2).

    Args:
        context: Operation context (not mutated)
        responses: User responses to questions (if any)

    Returns:
        Result dictionary
    """
    # Merge responses into a new dict to avoid mutating the caller's context
    context = {**context, **(responses or {})}
    operation = context.get("operation", "create")

    # Centralized slug validation for all operations
    slug = context.get("slug")
    if slug and operation in (
        "create", "read", "update", "complete", "remove"
    ):
        is_valid, error = validate_slug(slug)
        if not is_valid:
            return {"success": False, "message": f"Invalid slug: {error}"}

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


def safe_json_load(json_str: Optional[str]) -> Dict[str, Any]:
    """Safely load JSON string with size limits.

    Args:
        json_str: JSON string to parse (None returns empty dict)

    Returns:
        Parsed dictionary

    Raises:
        ValueError: If JSON is invalid or exceeds limits
    """
    if not json_str:
        return {}

    # Size limit: 100KB for mementos
    # Note: This is lower than the general 1MB limit in json_utils.py because
    # mementos are session snapshots that should remain lightweight. Config
    # files may legitimately be larger, so the general limit is higher.
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

    except (KeyboardInterrupt, SystemExit):
        raise
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
