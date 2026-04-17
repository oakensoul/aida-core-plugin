"""Panel resolution for the expert registry."""
from __future__ import annotations

_VALID_ROLES: frozenset[str] = frozenset({"core", "domain", "qa"})


def resolve_panel(
    panel_name: str | None,
    active_experts: list[dict],
    config: dict,
) -> dict:
    """Resolve a named panel (or all active experts) to a list of expert names.

    Args:
        panel_name: The panel to resolve, or None to return all active experts.
        active_experts: List of active expert dicts (each must have a "name" key).
        config: Registry config dict, expected to have a "panels" key.

    Returns:
        A dict with keys:
            - "experts": list[str] of expert names
            - "panel_found": bool
            - "warnings": list[str]
    """
    warnings: list[str] = []
    active_names = {e["name"] for e in active_experts}

    if panel_name is None:
        return {
            "experts": [e["name"] for e in active_experts],
            "panel_found": True,
            "warnings": warnings,
        }

    panels: dict = config.get("panels", {})

    if panel_name not in panels:
        warnings.append(f"Panel '{panel_name}' is not defined; falling back to all active experts.")
        return {
            "experts": [e["name"] for e in active_experts],
            "panel_found": False,
            "warnings": warnings,
        }

    panel_members: list[str] = panels[panel_name]
    resolved: list[str] = []
    for member in panel_members:
        if member in active_names:
            resolved.append(member)
        else:
            warnings.append(f"Panel member '{member}' is not in the active expert list (stale).")

    return {
        "experts": resolved,
        "panel_found": True,
        "warnings": warnings,
    }


def resolve_by_role(role: str, active_experts: list[dict]) -> dict:
    """Filter active experts by their role.

    Args:
        role: The role to filter by (must be one of core, domain, qa).
        active_experts: List of active expert dicts.

    Returns:
        A dict with keys:
            - "experts": list[str] of expert names matching the role
            - "warnings": list[str]
    """
    warnings: list[str] = []

    if role not in _VALID_ROLES:
        warnings.append(f"Unknown role '{role}'; valid roles are {sorted(_VALID_ROLES)}.")
        return {"experts": [], "warnings": warnings}

    matched: list[str] = []
    for expert in active_experts:
        expert_role = expert.get("expert-role") or expert.get("expert_role", "")
        if expert_role == role:
            matched.append(expert["name"])

    return {"experts": matched, "warnings": warnings}
