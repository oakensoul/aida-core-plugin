# SPDX-FileCopyrightText: 2026 The AIDA Core Authors
# SPDX-License-Identifier: MPL-2.0

"""Split/merge helpers for the project-context YAML files.

The project context lives in two files under `.claude/`:

- `aida-project-context.yml` — committed; project-level facts (vcs.type,
  languages, tools, preferences, etc.). Should be identical across every
  contributor's working copy.
- `aida-project-context.local.yml` — gitignored; user/environment overlay
  (project_root, vcs.remote_url, last_updated, config_complete).

Consumers should always read via `load_project_context()`, which merges
both files (local overrides project). Writers should always go through
`write_project_context()`, which splits a merged dict and writes both
files atomically.

Legacy single-file projects (everything in `aida-project-context.yml`)
read transparently through `load_project_context()`; the next call to
`write_project_context()` migrates them by emitting both files.
"""

from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import yaml

from .errors import ConfigurationError, FileOperationError
from .files import read_file, write_yaml

PROJECT_CONTEXT_FILE = "aida-project-context.yml"
PROJECT_CONTEXT_LOCAL_FILE = "aida-project-context.local.yml"

# Top-level keys that belong in the gitignored .local overlay.
_LOCAL_TOP_LEVEL_KEYS = frozenset(
    {"project_root", "last_updated", "config_complete"}
)

# Nested keys that belong in .local. Keyed by parent → child name.
# Per issue #65, only `vcs.remote_url` is user-specific; the rest of vcs
# (type, has_vcs, uses_worktrees, is_github, is_gitlab) is project-level.
_LOCAL_NESTED_KEYS: Dict[str, frozenset] = {
    "vcs": frozenset({"remote_url"}),
}


def split_context(merged: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Split a merged context dict into (project, local) components.

    Project-level keys go to the committed file; user-specific keys
    (paths, remote URLs, timestamps) go to the gitignored .local file.

    Empty parent dicts that result from extracting all their children
    are dropped so `local` doesn't carry stub `vcs: {}` entries.
    """
    project: Dict[str, Any] = {}
    local: Dict[str, Any] = {}

    for key, value in merged.items():
        if key in _LOCAL_TOP_LEVEL_KEYS:
            local[key] = value
            continue

        nested_local_keys = _LOCAL_NESTED_KEYS.get(key)
        if nested_local_keys and isinstance(value, dict):
            project_subset = {
                k: v for k, v in value.items() if k not in nested_local_keys
            }
            local_subset = {
                k: v for k, v in value.items() if k in nested_local_keys
            }
            if project_subset:
                project[key] = project_subset
            if local_subset:
                local[key] = local_subset
            continue

        project[key] = value

    return project, local


def merge_context(
    project: Dict[str, Any], local: Dict[str, Any]
) -> Dict[str, Any]:
    """Merge a project + local pair into a single dict.

    Local values override project values at the leaf level. Nested dicts
    are merged shallowly (one level deep, matching the split semantics).
    """
    merged: Dict[str, Any] = {}
    for key, value in project.items():
        merged[key] = dict(value) if isinstance(value, dict) else value

    for key, value in local.items():
        if (
            key in merged
            and isinstance(merged[key], dict)
            and isinstance(value, dict)
        ):
            merged[key].update(value)
        else:
            merged[key] = value

    return merged


def _read_yaml_if_exists(path: Path) -> Optional[Dict[str, Any]]:
    """Load a YAML mapping from path, returning None if the file is absent.

    Raises ConfigurationError on parse failure or if the document is not
    a mapping.
    """
    if not path.exists():
        return None
    try:
        text = read_file(path)
    except FileOperationError:
        raise
    try:
        data = yaml.safe_load(text) or {}
    except yaml.YAMLError as e:
        raise ConfigurationError(
            f"Cannot parse {path.name}: {e}",
            f"Fix the YAML syntax in {path}, or delete the file and rerun"
            " /aida config to regenerate it.",
        ) from e
    if not isinstance(data, dict):
        raise ConfigurationError(
            f"{path.name} is not a YAML mapping (got {type(data).__name__})",
            f"Expected a top-level mapping in {path}.",
        )
    return data


def load_project_context(project_root: Path) -> Dict[str, Any]:
    """Load the merged project context from `.claude/`.

    Reads `aida-project-context.yml` and (if present) overlays
    `aida-project-context.local.yml`. Returns an empty dict if neither
    file exists.

    Legacy single-file projects (no `.local.yml`) still work — the
    committed file is returned as-is; the split happens on the next
    write.
    """
    claude_dir = project_root / ".claude"
    project = _read_yaml_if_exists(claude_dir / PROJECT_CONTEXT_FILE) or {}
    local = _read_yaml_if_exists(claude_dir / PROJECT_CONTEXT_LOCAL_FILE) or {}
    return merge_context(project, local)


def write_project_context(
    project_root: Path, merged: Dict[str, Any]
) -> Tuple[Path, Path]:
    """Split `merged` and write the project + local files atomically.

    Returns (project_path, local_path). Both files are written even if
    one of the components is empty — an empty `.local` file is fine and
    keeps the gitignore expectation stable.
    """
    claude_dir = project_root / ".claude"
    project_path = claude_dir / PROJECT_CONTEXT_FILE
    local_path = claude_dir / PROJECT_CONTEXT_LOCAL_FILE

    project, local = split_context(merged)
    write_yaml(project_path, project)
    write_yaml(local_path, local)
    return project_path, local_path


_GITIGNORE_BLOCK_HEADER = "# AIDA project context (user-specific overlay)"


def ensure_gitignore_entry(project_root: Path) -> bool:
    """Append the AIDA local-overlay block to `.gitignore` if missing.

    Returns True if the gitignore was modified, False if it was already
    up-to-date or `.gitignore` does not exist (we don't create one — that
    decision belongs to the project, not /aida config).

    The entry is anchored to the `.claude/` path so it doesn't conflict
    with similarly-named files elsewhere in the tree.
    """
    gitignore_path = project_root / ".gitignore"
    if not gitignore_path.exists():
        return False

    entry = f".claude/{PROJECT_CONTEXT_LOCAL_FILE}"
    try:
        current = read_file(gitignore_path)
    except FileOperationError:
        return False

    # Idempotency: skip if the entry is already present in any non-comment line.
    for line in current.splitlines():
        if line.strip() == entry:
            return False

    block = f"\n{_GITIGNORE_BLOCK_HEADER}\n{entry}\n"
    if not current.endswith("\n") and current:
        block = "\n" + block
    new_content = current + block

    from .files import write_file as _write_file

    _write_file(gitignore_path, new_content, create_parents=False)
    return True
