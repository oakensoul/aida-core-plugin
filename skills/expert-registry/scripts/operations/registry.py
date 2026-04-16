"""Expert registry config I/O operations."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

import yaml


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _read_yaml_safe(path: Path, warnings: list[str]) -> dict | None:
    """Read a YAML file safely.

    Returns the parsed dict, or None if the file is missing or malformed.
    Appends a warning message to *warnings* when the file is malformed.
    """
    if not path.exists():
        return None
    try:
        content = path.read_text(encoding="utf-8")
        data = yaml.safe_load(content)
        # safe_load returns None for an empty file
        if data is None:
            return {}
        if not isinstance(data, dict):
            warnings.append(
                f"Malformed YAML in {path}: expected a mapping at top level"
            )
            return None
        return data
    except yaml.YAMLError as exc:
        warnings.append(f"Malformed YAML in {path}: {exc}")
        return None


def _validate_active_list(raw: Any, warnings: list[str]) -> list[str]:
    """Filter *raw* to a list of strings only.

    Non-string entries are skipped and a warning is appended for each.
    """
    if not isinstance(raw, list):
        warnings.append(
            f"experts.active must be a list, got {type(raw).__name__}; ignoring"
        )
        return []
    result: list[str] = []
    for item in raw:
        if isinstance(item, str):
            result.append(item)
        else:
            warnings.append(
                f"Non-string entry in experts.active skipped: {item!r}"
            )
    return result


def _validate_panels(raw: Any, warnings: list[str]) -> dict[str, list[str]]:
    """Validate panel mapping.

    Each value must be a list; non-list values are skipped with a warning.
    """
    if not isinstance(raw, dict):
        warnings.append(
            f"experts.panels must be a mapping, got {type(raw).__name__}; ignoring"
        )
        return {}
    result: dict[str, list[str]] = {}
    for key, value in raw.items():
        if isinstance(value, list):
            result[key] = value
        else:
            warnings.append(
                f"Panel '{key}' value is not a list ({type(value).__name__}); skipping"
            )
    return result


def _atomic_write(path: Path, content: str) -> None:
    """Write *content* to *path* atomically via a temp file + fsync + rename."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        dir=path.parent,
        delete=False,
        encoding="utf-8",
        suffix=".tmp",
    ) as tmp:
        tmp.write(content)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_path = tmp.name
    try:
        os.replace(tmp_path, path)
    except OSError:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_experts_config(
    *,
    global_path: Path,
    project_path: Path,
) -> dict[str, Any]:
    """Load expert activation config using a layered strategy.

    Priority: project config > global config.

    The project config takes effect **only** when the ``experts.active`` key
    is present (even when it is an empty list).  If the key is absent the
    loader falls through to the global config.

    Returns a dict with keys:
        active   (list[str])    - names of active experts
        panels   (dict)         - named panels mapping
        source   (str | None)   - "project", "global", or None
        warnings (list[str])    - non-fatal issues encountered
    """
    warnings: list[str] = []

    def _extract(data: dict, warnings: list[str]) -> tuple[list[str], dict] | None:
        """Return (active, panels) from a parsed config dict, or None if
        the ``experts.active`` key is absent."""
        experts = data.get("experts")
        if not isinstance(experts, dict):
            return None
        if "active" not in experts:
            return None
        active = _validate_active_list(experts["active"], warnings)
        raw_panels = experts.get("panels", {})
        panels = _validate_panels(raw_panels, warnings) if raw_panels else {}
        return active, panels

    # -- project config (checked first) -----------------------------------
    project_data = _read_yaml_safe(project_path, warnings)
    if project_data is not None:
        extracted = _extract(project_data, warnings)
        if extracted is not None:
            active, panels = extracted
            return {
                "active": active,
                "panels": panels,
                "source": "project",
                "warnings": warnings,
            }

    # -- global config (fallback) -----------------------------------------
    global_data = _read_yaml_safe(global_path, warnings)
    if global_data is not None:
        extracted = _extract(global_data, warnings)
        if extracted is not None:
            active, panels = extracted
            return {
                "active": active,
                "panels": panels,
                "source": "global",
                "warnings": warnings,
            }

    # -- neither config present -------------------------------------------
    return {
        "active": [],
        "panels": {},
        "source": None,
        "warnings": warnings,
    }


def save_experts_config(
    *,
    path: Path,
    active: list[str],
    panels: dict | None = None,
) -> dict[str, Any]:
    """Write expert activation config to *path* atomically.

    Existing keys in the file are preserved; only ``experts`` is updated.

    Returns a dict with keys:
        success  (bool)
        path     (str)
    """
    # Load existing content (if any) to preserve other keys
    existing: dict = {}
    if path.exists():
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                existing = data
        except yaml.YAMLError:
            pass  # Overwrite silently if malformed

    experts_section: dict[str, Any] = {"active": active}
    if panels is not None:
        experts_section["panels"] = panels

    existing["experts"] = experts_section

    _atomic_write(path, yaml.dump(existing, default_flow_style=False, allow_unicode=True))

    return {"success": True, "path": str(path)}


# ---------------------------------------------------------------------------
# Agent filtering / resolution helpers
# ---------------------------------------------------------------------------


def filter_experts_by_role(agents: list[dict]) -> list[dict]:
    """Return only agents whose frontmatter role is 'expert'."""
    return [a for a in agents if a.get("role") == "expert"]


def resolve_active_experts(
    experts: list[dict],
    config: dict,
) -> tuple[list[dict], list[str]]:
    """Resolve the active subset of *experts* according to *config*.

    Returns:
        (active_experts, dangling_warnings)

    *dangling_warnings* lists names in config['active'] that do not match
    any expert in the provided list.
    """
    active_names: list[str] = config.get("active", [])
    expert_by_name = {e.get("name"): e for e in experts if e.get("name")}

    resolved: list[dict] = []
    dangling: list[str] = []
    for name in active_names:
        if name in expert_by_name:
            resolved.append(expert_by_name[name])
        else:
            dangling.append(f"Active expert '{name}' not found in agent list")

    return resolved, dangling
