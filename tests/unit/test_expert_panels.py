"""Tests for skills/expert-registry/scripts/operations/panels.py"""
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "skills" / "expert-registry" / "scripts"))

# Clear cached operations modules to avoid cross-manager conflicts in pytest
for _mod_name in list(sys.modules):
    if _mod_name == "operations" or _mod_name.startswith("operations."):
        del sys.modules[_mod_name]

from operations.panels import resolve_panel, resolve_by_role  # noqa: E402


def _make_expert(name: str, role: str = "domain") -> dict[str, Any]:
    return {"name": name, "description": f"Test expert {name}", "expert-role": role}


# ---------------------------------------------------------------------------
# TestResolvePanel
# ---------------------------------------------------------------------------

class TestResolvePanel:
    def test_named_panel_found(self):
        """Named panel returns members filtered to active, panel_found=True."""
        active = [_make_expert("alice"), _make_expert("bob"), _make_expert("carol")]
        config = {"panels": {"team-a": ["alice", "bob"]}}
        result = resolve_panel("team-a", active, config)
        assert result["panel_found"] is True
        assert set(result["experts"]) == {"alice", "bob"}
        assert result["warnings"] == []

    def test_named_panel_not_defined_falls_back(self):
        """Undefined panel returns all active, panel_found=False, with warning."""
        active = [_make_expert("alice"), _make_expert("bob")]
        config = {"panels": {}}
        result = resolve_panel("unknown-panel", active, config)
        assert result["panel_found"] is False
        assert set(result["experts"]) == {"alice", "bob"}
        assert len(result["warnings"]) >= 1
        assert any("not defined" in w for w in result["warnings"])

    def test_no_panel_name_returns_all_active(self):
        """None panel_name returns all active experts, panel_found=True."""
        active = [_make_expert("alice"), _make_expert("bob")]
        config = {"panels": {}}
        result = resolve_panel(None, active, config)
        assert result["panel_found"] is True
        assert set(result["experts"]) == {"alice", "bob"}
        assert result["warnings"] == []

    def test_panel_filters_inactive_members(self):
        """Members listed in the panel but not active are excluded with a warning."""
        active = [_make_expert("alice")]
        config = {"panels": {"team-a": ["alice", "ghost"]}}
        result = resolve_panel("team-a", active, config)
        assert result["panel_found"] is True
        assert result["experts"] == ["alice"]
        assert len(result["warnings"]) >= 1
        assert any("ghost" in w for w in result["warnings"])

    def test_empty_active_returns_empty(self):
        """No active experts yields an empty expert list."""
        active: list[dict] = []
        config = {"panels": {"team-a": ["alice"]}}
        result = resolve_panel("team-a", active, config)
        assert result["panel_found"] is True
        assert result["experts"] == []


# ---------------------------------------------------------------------------
# TestResolveByRole
# ---------------------------------------------------------------------------

class TestResolveByRole:
    def test_filter_core_role(self):
        """Returns only experts with the 'core' role."""
        active = [
            _make_expert("alice", role="core"),
            _make_expert("bob", role="domain"),
            _make_expert("carol", role="core"),
        ]
        result = resolve_by_role("core", active)
        assert set(result["experts"]) == {"alice", "carol"}
        assert result["warnings"] == []

    def test_unknown_role_returns_empty_with_warning(self):
        """Unknown role returns empty list with a warning."""
        active = [_make_expert("alice", role="core")]
        result = resolve_by_role("wizard", active)
        assert result["experts"] == []
        assert len(result["warnings"]) >= 1
        assert any("wizard" in w for w in result["warnings"])

    def test_no_experts_with_role(self):
        """Valid role with no matching experts returns empty list, no warning."""
        active = [_make_expert("alice", role="domain")]
        result = resolve_by_role("qa", active)
        assert result["experts"] == []
        assert result["warnings"] == []
