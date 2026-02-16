"""Agent discovery and CLAUDE.md routing generation.

Scans installed agents from project, user, and plugin sources,
reads their frontmatter metadata, and generates routing directives
in the project's CLAUDE.md file.
"""

from __future__ import annotations

import errno
import glob
import logging
import os
from pathlib import Path

from .json_utils import safe_json_load
from .paths import get_home_dir
from .files import write_file

logger = logging.getLogger(__name__)

# Try to import yaml for frontmatter parsing
try:
    import yaml

    _HAS_YAML = True
except ImportError:
    yaml = None  # type: ignore[assignment]
    _HAS_YAML = False

# Maximum file size for agent markdown files (500 KB).
_MAX_AGENT_FILE_SIZE = 500 * 1024

# Markers for managed section in CLAUDE.md
_BEGIN_MARKER = (
    "<!-- BEGIN AIDA AGENT ROUTING"
    " (auto-generated, do not edit) -->"
)
_END_MARKER = "<!-- END AIDA AGENT ROUTING -->"

# Required frontmatter fields
_REQUIRED_FIELDS = {"name", "description", "version", "tags"}

# Section header
_SECTION_HEADER = "## Available Agents"


# ── File reading ────────────────────────────────────


def _safe_read_agent_file(
    file_path: Path,
    label: str,
    resolved_root: Path | None = None,
) -> str | None:
    """Read a file with TOCTOU-safe security checks.

    Uses ``O_NOFOLLOW`` to atomically reject symlinks.
    Enforces a 500 KB size limit for agent files.
    Optionally validates path containment within a root.
    """
    if resolved_root is not None:
        try:
            file_path.resolve().relative_to(resolved_root)
        except ValueError:
            logger.warning(
                "%s path outside root: %s",
                label,
                file_path,
            )
            return None

    fd = -1
    try:
        fd = os.open(
            str(file_path), os.O_RDONLY | os.O_NOFOLLOW
        )
        st = os.fstat(fd)
        if st.st_size > _MAX_AGENT_FILE_SIZE:
            logger.warning(
                "%s too large (%d bytes): %s",
                label,
                st.st_size,
                file_path,
            )
            return None
        with os.fdopen(fd, "r", encoding="utf-8") as f:
            fd = -1  # fd now owned by file object
            return f.read()
    except OSError as exc:
        if exc.errno == errno.ELOOP:
            logger.warning(
                "Skipping symlink %s: %s",
                label,
                file_path,
            )
        elif exc.errno != errno.ENOENT:
            logger.warning(
                "Failed to read %s %s: %s",
                label,
                file_path,
                exc,
            )
        return None
    finally:
        if fd >= 0:
            os.close(fd)


# ── Frontmatter parsing ────────────────────────────


def _parse_yaml_frontmatter(content: str) -> dict | None:
    """Parse YAML frontmatter delimited by ``---``."""
    if not _HAS_YAML:
        logger.warning(
            "PyYAML not available; agent discovery disabled"
        )
        return None

    if not content.startswith("---"):
        return None

    first_nl = content.find("\n")
    if first_nl < 0:
        return None

    # Find closing --- on its own line (not inside
    # multi-line YAML values like block scalars).
    end = -1
    search_pos = first_nl
    while True:
        pos = content.find("\n---", search_pos)
        if pos < 0:
            break
        after = pos + 4  # len("\n---") == 4
        if after >= len(content) or content[after] in (
            "\n",
            "\r",
        ):
            end = pos
            break
        search_pos = after

    if end < 0:
        return None

    yaml_str = content[first_nl + 1 : end].strip()
    if not yaml_str:
        return None

    try:
        data = yaml.safe_load(yaml_str)
        if not isinstance(data, dict):
            return None
        return data
    except Exception:
        logger.warning(
            "Failed to parse YAML frontmatter",
            exc_info=True,
        )
        return None


def _ensure_list(value: object) -> list:
    """Ensure value is a list."""
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        return [value]
    return []


def _read_agent_frontmatter(
    agent_path: Path,
    resolved_root: Path | None = None,
) -> dict | None:
    """Read and validate agent frontmatter metadata.

    Returns dict with name, description, version, tags,
    skills, model — or ``None`` on failure.
    """
    content = _safe_read_agent_file(
        agent_path, "agent file", resolved_root
    )
    if content is None:
        return None

    frontmatter = _parse_yaml_frontmatter(content)
    if frontmatter is None:
        logger.warning(
            "No valid frontmatter in agent file: %s",
            agent_path,
        )
        return None

    for field in _REQUIRED_FIELDS:
        if field not in frontmatter:
            logger.warning(
                "Agent missing required field '%s': %s",
                field,
                agent_path,
            )
            return None

    return {
        "name": frontmatter["name"],
        "description": frontmatter["description"],
        "version": str(frontmatter["version"]),
        "tags": _ensure_list(frontmatter.get("tags", [])),
        "skills": _ensure_list(
            frontmatter.get("skills", [])
        ),
        "model": frontmatter.get("model"),
    }


# ── Directory scanning ──────────────────────────────


def _find_agents_in_directory(
    base_dir: Path,
    source: str,
    resolved_root: Path | None = None,
) -> list[dict]:
    """Scan ``{base_dir}/*/*.md`` for ``{name}/{name}.md``.

    Rejects symlinked directories and files.
    """
    if not base_dir.is_dir():
        return []

    agents: list[dict] = []
    try:
        entries = sorted(base_dir.iterdir())
    except OSError:
        return []

    for subdir in entries:
        if not subdir.is_dir() or subdir.is_symlink():
            continue
        name = subdir.name
        agent_file = subdir / f"{name}.md"
        if not agent_file.exists():
            continue

        meta = _read_agent_frontmatter(
            agent_file, resolved_root
        )
        if meta is not None:
            meta["source"] = source
            meta["path"] = str(agent_file)
            agents.append(meta)

    return agents


def _read_aida_config_for_agents(
    config_path: Path,
    resolved_root: Path | None = None,
) -> dict | None:
    """Read aida-config.json for agent declarations."""
    raw = _safe_read_agent_file(
        config_path, "aida-config.json", resolved_root
    )
    if raw is None:
        return None
    try:
        data = safe_json_load(raw)
        if not isinstance(data, dict):
            return None
        return data
    except Exception:
        logger.warning(
            "Failed to parse aida-config.json: %s",
            config_path,
            exc_info=True,
        )
        return None


def _find_plugin_agents(
    plugin_root: Path,
    plugin_name: str,
    resolved_root: Path | None = None,
) -> list[dict]:
    """Find agents declared by a plugin.

    Reads ``aida-config.json`` for an ``agents`` key.  For
    each declared name, resolves to
    ``{plugin_root}/agents/{name}/{name}.md``.  Falls back
    to directory scanning if no ``agents`` key is present.
    """
    agents_dir = plugin_root / "agents"
    source = f"plugin:{plugin_name}"

    config_path = (
        plugin_root / ".claude-plugin" / "aida-config.json"
    )
    aida_config = _read_aida_config_for_agents(
        config_path, resolved_root
    )

    if aida_config is not None and "agents" in aida_config:
        declared = aida_config["agents"]
        if isinstance(declared, list):
            results: list[dict] = []
            for name in declared:
                if not isinstance(name, str):
                    continue
                agent_path = (
                    agents_dir / name / f"{name}.md"
                )
                meta = _read_agent_frontmatter(
                    agent_path, resolved_root
                )
                if meta is not None:
                    meta["source"] = source
                    meta["path"] = str(agent_path)
                    results.append(meta)
            return results

    # Fall back to directory scanning
    return _find_agents_in_directory(
        agents_dir, source, resolved_root
    )


# ── Main discovery ──────────────────────────────────


def discover_agents(
    project_root: Path | str | None = None,
) -> list[dict]:
    """Discover agents from all sources.

    Scans three sources in priority order:
    1. Project (``{project_root}/.claude/agents/``)
    2. User (``~/.claude/agents/``)
    3. Plugins (from plugin cache)

    Deduplication: first-found-wins by agent name.

    Returns list of dicts with: name, description, version,
    tags, skills, model, source, path.
    """
    if project_root is not None:
        project_root = Path(project_root)

    seen: set[str] = set()
    agents: list[dict] = []

    def _add(new_agents: list[dict]) -> None:
        for agent in new_agents:
            name = agent["name"]
            if name not in seen:
                seen.add(name)
                agents.append(agent)

    # 1. Project agents (highest priority)
    if project_root is not None:
        _add(
            _find_agents_in_directory(
                project_root / ".claude" / "agents",
                "project",
            )
        )

    # 2. User agents
    _add(
        _find_agents_in_directory(
            get_home_dir() / ".claude" / "agents",
            "user",
        )
    )

    # 3. Plugin agents (lowest priority)
    cache_root = (
        get_home_dir() / ".claude" / "plugins" / "cache"
    )
    if cache_root.is_dir():
        resolved_root = cache_root.resolve()
        pattern = str(
            cache_root / "*" / "*" / ".claude-plugin"
        )
        for meta_str in sorted(glob.glob(pattern)):
            meta_dir = Path(meta_str)
            if meta_dir.is_symlink():
                continue
            plugin_root = meta_dir.parent
            _add(
                _find_plugin_agents(
                    plugin_root,
                    plugin_root.name,
                    resolved_root,
                )
            )

    return agents


# ── Routing generation ──────────────────────────────


def generate_agent_routing_section(
    agents: list[dict],
) -> str:
    """Generate markdown routing section for agents.

    Returns markdown with HTML comment markers, or empty
    string if no agents provided.
    """
    if not agents:
        return ""

    lines = [
        _SECTION_HEADER,
        "",
        _BEGIN_MARKER,
        "",
        "### Agent Routing Directives",
        "",
        (
            "When working on this project, consult"
            " these specialized agents"
        ),
        (
            "for domain expertise before making"
            " decisions in their areas:"
        ),
        "",
    ]

    for agent in agents:
        desc = agent.get("description", "")
        lines.append(f"- **{agent['name']}**: {desc}")
        lines.append("")

    lines.extend(
        [
            "### Using Agent Teams",
            "",
            (
                "When orchestrating complex tasks with"
                " Agent Teams, the team lead"
            ),
            (
                "should consult relevant agents for"
                " domain expertise before"
            ),
            (
                "delegating implementation. Teammates"
                " encountering domain-specific"
            ),
            (
                "decisions should either consult the"
                " agent directly or flag it"
            ),
            "back to the lead.",
            "",
            _END_MARKER,
        ]
    )

    return "\n".join(lines)


def _parse_managed_section(
    content: str,
) -> tuple[str, str | None, str]:
    """Split CLAUDE.md around managed markers.

    Returns (before, managed, after).  ``managed`` is
    ``None`` if no markers are found.
    """
    begin_idx = content.find(_BEGIN_MARKER)
    if begin_idx < 0:
        return content, None, ""

    end_idx = content.find(_END_MARKER, begin_idx)
    if end_idx < 0:
        return content, None, ""

    after_end = end_idx + len(_END_MARKER)

    # Look for section header before begin marker
    search_area = content[:begin_idx]
    header_idx = search_area.rfind(_SECTION_HEADER)
    section_start = (
        header_idx if header_idx >= 0 else begin_idx
    )

    before = content[:section_start]
    managed = content[section_start:after_end]
    after = content[after_end:]

    return before, managed, after


def _assemble_content(
    before: str, middle: str, after: str
) -> str:
    """Join sections with proper spacing."""
    parts = []
    b = before.rstrip("\n")
    a = after.lstrip("\n")

    if b:
        parts.append(b)
    if middle:
        parts.append(middle)
    if a:
        parts.append(a)

    result = "\n\n".join(parts)
    if result and not result.endswith("\n"):
        result += "\n"
    return result if result else ""


def update_agent_routing(
    project_root: Path | str | None = None,
    agents: list[dict] | None = None,
) -> dict:
    """Update CLAUDE.md with agent routing directives.

    Discovers agents if not provided, then creates or
    updates the managed routing section using marker-based
    idempotent replacement.

    Returns dict with success, message, agents_count, path.
    """
    if project_root is None:
        project_root = Path.cwd()
    else:
        project_root = Path(project_root)

    if agents is None:
        agents = discover_agents(project_root)

    claude_md_path = project_root / "CLAUDE.md"

    # Read existing content
    if claude_md_path.exists():
        try:
            content = claude_md_path.read_text(
                encoding="utf-8"
            )
        except OSError as exc:
            return {
                "success": False,
                "message": f"Failed to read CLAUDE.md: {exc}",
                "agents_count": 0,
                "path": None,
            }
    else:
        content = ""

    routing = generate_agent_routing_section(agents)
    before, managed, after = _parse_managed_section(content)

    if managed is not None:
        # Replace existing section
        new_content = _assemble_content(
            before, routing, after
        )
    elif routing:
        # Append new section
        new_content = _assemble_content(content, routing, "")
    else:
        return {
            "success": True,
            "message": "No agents found; no changes needed",
            "agents_count": 0,
            "path": None,
        }

    try:
        write_file(claude_md_path, new_content)
    except OSError as exc:
        return {
            "success": False,
            "message": (
                f"Failed to write CLAUDE.md: {exc}"
            ),
            "agents_count": 0,
            "path": None,
        }

    count = len(agents)
    if count:
        msg = (
            f"Updated CLAUDE.md with {count}"
            f" agent routing directive"
            f"{'s' if count != 1 else ''}"
        )
    else:
        msg = "Removed agent routing section from CLAUDE.md"

    return {
        "success": True,
        "message": msg,
        "agents_count": count,
        "path": str(claude_md_path),
    }
