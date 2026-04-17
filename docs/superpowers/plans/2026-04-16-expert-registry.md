---
type: documentation
title: "Expert Registry Implementation Plan"
---

# Expert Registry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task.
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a new `expert-registry` skill that provides layered
(global + project) activation of panel experts, role-based filtering,
and named panel composition.

**Architecture:** New skill at `skills/expert-registry/` following the
two-phase API pattern (ADR-010). Reads from existing agent discovery
(`utils/agents.py`), adds activation/panel layer on top. Config stored
in `~/.claude/aida.yml` (global) and `aida-project-context.yml`
(project). Python modules split into `registry.py` (discovery +
activation) and `panels.py` (panel resolution).

**Tech Stack:** Python 3.10+, PyYAML, existing shared utilities
(`files.py`, `agents.py`, `paths.py`), pytest

**Spec:** `docs/superpowers/specs/2026-04-16-expert-registry-design.md`

---

## File Structure

### New Files

```text
skills/expert-registry/
├── SKILL.md                              # Skill definition + command routing
├── scripts/
│   ├── _paths.py                         # Path setup for imports
│   ├── manage.py                         # Two-phase API entry point
│   └── operations/
│       ├── __init__.py                   # Package init
│       ├── registry.py                   # Expert discovery, activation, config I/O
│       └── panels.py                     # Panel resolution + composition
├── references/
│   └── schemas.md                        # Config schema documentation
└── templates/
    └── questionnaires/
        └── configure.yml                 # Questions for expert selection
tests/unit/
├── test_expert_registry.py               # Registry + activation tests
└── test_expert_panels.py                 # Panel resolution tests
```

### Modified Files

```text
.frontmatter-schema.json                  # Add expert-role to agent type
skills/aida/SKILL.md                      # Add expert routing + help text
agents/aida/knowledge/config-schema.md    # Add experts section to schema
skills/agent-manager/references/schemas.md # Add expert-role field docs
skills/plugin-manager/templates/scaffold/shared/frontmatter-schema.json.jinja2
                                          # Add expert-role to scaffold template
```

---

## Task 1: Add `expert-role` to Frontmatter Schema

**Files:**

- Modify: `.frontmatter-schema.json:61-87` (agent type block)
- Modify: `skills/agent-manager/references/schemas.md`
- Modify: `skills/plugin-manager/templates/scaffold/shared/frontmatter-schema.json.jinja2`

- [ ] **Step 1: Update `.frontmatter-schema.json`**

In the `agent` type's `then.properties` block, add `expert-role`:

```json
"expert-role": {
  "type": "string",
  "enum": ["core", "domain", "qa"],
  "description": "Panel expert role for expert-registry dispatch"
}
```

Add it after the `tags` property inside the agent `then` block.

- [ ] **Step 2: Update agent-manager schemas.md**

Read `skills/agent-manager/references/schemas.md` and add `expert-role`
to the optional fields section of the agent frontmatter schema:

```yaml
# Optional fields
model: sonnet
color: purple
expert-role: core|domain|qa    # Panel expert role for expert-registry
```

- [ ] **Step 3: Update scaffold template**

Read `skills/plugin-manager/templates/scaffold/shared/frontmatter-schema.json.jinja2`
and add the same `expert-role` property to the agent type block,
matching the exact JSON structure added in Step 1.

- [ ] **Step 4: Validate schema is valid JSON**

Run: `python -c "import json; json.load(open('.frontmatter-schema.json'))"`
Expected: No output (valid JSON)

- [ ] **Step 5: Run existing tests to confirm no regression**

Run: `~/.aida/venv/bin/pytest tests/ -v --tb=short`
Expected: All existing tests pass

- [ ] **Step 6: Commit**

```bash
git add .frontmatter-schema.json \
  skills/agent-manager/references/schemas.md \
  skills/plugin-manager/templates/scaffold/shared/frontmatter-schema.json.jinja2
git commit -m "feat(expert-registry): add expert-role to agent frontmatter schema"
```

---

## Task 2: Update Project Config Schema Documentation

**Files:**

- Modify: `agents/aida/knowledge/config-schema.md`

- [ ] **Step 1: Read the current config-schema.md**

Read `agents/aida/knowledge/config-schema.md` to find the schema
version and the end of the existing sections.

- [ ] **Step 2: Add experts section to schema docs**

Add a new section after the `plugins` section:

```yaml
experts:                          # optional
  active:                         # optional; list of expert agent names
    - security-expert             # Names must match discovered agents
    - best-practices-reviewer
  panels:                         # optional; project-only, named panels
    code-review:
      - security-expert
      - best-practices-reviewer
```

Document the semantics:

- `active` key absent: fall through to global config
- `active: []` (empty list): intentional deactivation, zero experts
- `panels` are project-only (not supported in global config)
- Panel entries filtered to active experts at resolution time

- [ ] **Step 3: Bump schema version**

Update the version field from `0.2.0` to `0.3.0`.

- [ ] **Step 4: Commit**

```bash
git add agents/aida/knowledge/config-schema.md
git commit -m "feat(expert-registry): add experts section to project config schema"
```

---

## Task 3: Create Registry Module -- Config I/O

**Files:**

- Create: `skills/expert-registry/scripts/_paths.py`
- Create: `skills/expert-registry/scripts/operations/__init__.py`
- Create: `skills/expert-registry/scripts/operations/registry.py`
- Test: `tests/unit/test_expert_registry.py`

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p skills/expert-registry/scripts/operations
mkdir -p skills/expert-registry/references
mkdir -p skills/expert-registry/templates/questionnaires
```

- [ ] **Step 2: Create `_paths.py`**

```python
"""Path setup for expert-registry scripts."""

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
PLUGIN_DIR = SKILL_DIR.parent.parent

# Add shared scripts to path
sys.path.insert(0, str(PLUGIN_DIR / "scripts"))

# Add aida skill utils to path (for agents.py, files.py, paths.py)
AIDA_SCRIPTS_DIR = PLUGIN_DIR / "skills" / "aida" / "scripts"
sys.path.insert(0, str(AIDA_SCRIPTS_DIR))
```

- [ ] **Step 3: Create `operations/__init__.py`**

```python
"""Expert registry operations package."""
```

- [ ] **Step 4: Write failing tests for config loading**

Create `tests/unit/test_expert_registry.py`:

```python
"""Tests for expert-registry config loading and activation."""

import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml


class TestConfigLoading(unittest.TestCase):
    """Test YAML config reading for expert activation."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        self.global_config = self.temp_path / "global" / "aida.yml"
        self.project_config = (
            self.temp_path / "project" / ".claude"
            / "aida-project-context.yml"
        )
        self.global_config.parent.mkdir(parents=True)
        self.project_config.parent.mkdir(parents=True)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_load_global_experts_active(self):
        """Global config with active experts returns the list."""
        from operations.registry import load_experts_config

        self.global_config.write_text(yaml.dump({
            "experts": {
                "active": ["security-expert", "qa-agent"],
            }
        }))
        result = load_experts_config(
            global_path=self.global_config,
            project_path=self.project_config,
        )
        self.assertEqual(result["active"], ["security-expert", "qa-agent"])
        self.assertEqual(result["source"], "global")
        self.assertEqual(result["panels"], {})

    def test_project_overrides_global(self):
        """Project active list fully replaces global."""
        from operations.registry import load_experts_config

        self.global_config.write_text(yaml.dump({
            "experts": {"active": ["global-expert"]},
        }))
        self.project_config.write_text(yaml.dump({
            "experts": {
                "active": ["project-expert"],
                "panels": {"review": ["project-expert"]},
            },
        }))
        result = load_experts_config(
            global_path=self.global_config,
            project_path=self.project_config,
        )
        self.assertEqual(result["active"], ["project-expert"])
        self.assertEqual(result["source"], "project")
        self.assertEqual(result["panels"], {"review": ["project-expert"]})

    def test_empty_active_list_means_zero_experts(self):
        """Explicit empty list deactivates all experts."""
        from operations.registry import load_experts_config

        self.global_config.write_text(yaml.dump({
            "experts": {"active": ["global-expert"]},
        }))
        self.project_config.write_text(yaml.dump({
            "experts": {"active": []},
        }))
        result = load_experts_config(
            global_path=self.global_config,
            project_path=self.project_config,
        )
        self.assertEqual(result["active"], [])
        self.assertEqual(result["source"], "project")

    def test_absent_experts_key_falls_through(self):
        """Project config without experts key falls to global."""
        from operations.registry import load_experts_config

        self.global_config.write_text(yaml.dump({
            "experts": {"active": ["global-expert"]},
        }))
        self.project_config.write_text(yaml.dump({
            "config_complete": True,
        }))
        result = load_experts_config(
            global_path=self.global_config,
            project_path=self.project_config,
        )
        self.assertEqual(result["active"], ["global-expert"])
        self.assertEqual(result["source"], "global")

    def test_both_configs_absent(self):
        """No configs at all returns empty active list."""
        from operations.registry import load_experts_config

        result = load_experts_config(
            global_path=self.global_config,
            project_path=self.project_config,
        )
        self.assertEqual(result["active"], [])
        self.assertIsNone(result["source"])

    def test_malformed_yaml_skipped_with_warning(self):
        """Malformed YAML is skipped, not fatal."""
        from operations.registry import load_experts_config

        self.global_config.write_text("experts:\n  active:\n    - good\n")
        self.project_config.write_text(": invalid: yaml: {{{\n")
        result = load_experts_config(
            global_path=self.global_config,
            project_path=self.project_config,
        )
        self.assertEqual(result["active"], ["good"])
        self.assertEqual(result["source"], "global")
        self.assertTrue(len(result["warnings"]) > 0)

    def test_non_string_entries_filtered(self):
        """Non-string values in active list are skipped."""
        from operations.registry import load_experts_config

        self.global_config.write_text(yaml.dump({
            "experts": {"active": ["good", 123, None, "also-good"]},
        }))
        result = load_experts_config(
            global_path=self.global_config,
            project_path=self.project_config,
        )
        self.assertEqual(result["active"], ["good", "also-good"])
        self.assertTrue(len(result["warnings"]) > 0)

    def test_panels_non_list_skipped(self):
        """Panel value that is not a list is skipped."""
        from operations.registry import load_experts_config

        self.project_config.write_text(yaml.dump({
            "experts": {
                "active": ["expert-a"],
                "panels": {
                    "good-panel": ["expert-a"],
                    "bad-panel": "not-a-list",
                },
            },
        }))
        result = load_experts_config(
            global_path=self.global_config,
            project_path=self.project_config,
        )
        self.assertEqual(result["panels"], {"good-panel": ["expert-a"]})
        self.assertTrue(len(result["warnings"]) > 0)


class TestConfigWriting(unittest.TestCase):
    """Test writing expert activation config."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_save_active_to_new_global(self):
        """Save active list to global config that doesn't exist yet."""
        from operations.registry import save_experts_config

        path = self.temp_path / "aida.yml"
        result = save_experts_config(
            path=path,
            active=["expert-a", "expert-b"],
        )
        self.assertTrue(result["success"])
        data = yaml.safe_load(path.read_text())
        self.assertEqual(
            data["experts"]["active"],
            ["expert-a", "expert-b"],
        )

    def test_save_preserves_existing_config(self):
        """Writing experts section preserves other config keys."""
        from operations.registry import save_experts_config

        path = self.temp_path / "aida.yml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.dump({
            "version": "0.3.0",
            "config_complete": True,
            "preferences": {"style": "conventional"},
        }))
        result = save_experts_config(
            path=path,
            active=["expert-a"],
        )
        self.assertTrue(result["success"])
        data = yaml.safe_load(path.read_text())
        self.assertEqual(data["version"], "0.3.0")
        self.assertTrue(data["config_complete"])
        self.assertEqual(data["preferences"]["style"], "conventional")
        self.assertEqual(data["experts"]["active"], ["expert-a"])

    def test_save_panels_to_project(self):
        """Save named panels to project config."""
        from operations.registry import save_experts_config

        path = self.temp_path / "config.yml"
        result = save_experts_config(
            path=path,
            active=["expert-a", "expert-b"],
            panels={"review": ["expert-a"]},
        )
        self.assertTrue(result["success"])
        data = yaml.safe_load(path.read_text())
        self.assertEqual(
            data["experts"]["panels"]["review"],
            ["expert-a"],
        )
```

- [ ] **Step 5: Run tests to verify they fail**

Run: `~/.aida/venv/bin/pytest tests/unit/test_expert_registry.py -v`
Expected: All tests FAIL with `ModuleNotFoundError` (registry.py
doesn't exist yet)

- [ ] **Step 6: Implement `registry.py` -- config loading**

Create `skills/expert-registry/scripts/operations/registry.py`:

```python
"""Expert registry -- discovery, activation, and config I/O.

Reads expert activation config from global (~/.claude/aida.yml) and
project (.claude/aida-project-context.yml) YAML files. Project config
fully replaces global when its experts.active key is present.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

_VALID_ROLES = frozenset({"core", "domain", "qa"})


@dataclass
class ExpertsConfig:
    """Loaded expert activation config."""

    active: list[str] = field(default_factory=list)
    panels: dict[str, list[str]] = field(default_factory=dict)
    source: str | None = None  # "global", "project", or None
    warnings: list[str] = field(default_factory=list)


def load_experts_config(
    *,
    global_path: Path,
    project_path: Path,
) -> dict[str, Any]:
    """Load expert activation config with layered resolution.

    Resolution order:
    1. If project config has experts.active key (even empty), use it.
    2. Otherwise fall through to global config.
    3. If neither exists, return empty active list.

    Returns dict with keys: active, panels, source, warnings.
    """
    warnings: list[str] = []

    # Try project config first
    project_data = _read_yaml_safe(project_path, warnings)
    if project_data is not None:
        experts = project_data.get("experts")
        if isinstance(experts, dict) and "active" in experts:
            active = _validate_active_list(
                experts.get("active", []), warnings
            )
            panels = _validate_panels(
                experts.get("panels", {}), warnings
            )
            return {
                "active": active,
                "panels": panels,
                "source": "project",
                "warnings": warnings,
            }

    # Fall through to global
    global_data = _read_yaml_safe(global_path, warnings)
    if global_data is not None:
        experts = global_data.get("experts")
        if isinstance(experts, dict) and "active" in experts:
            active = _validate_active_list(
                experts.get("active", []), warnings
            )
            return {
                "active": active,
                "panels": {},
                "source": "global",
                "warnings": warnings,
            }

    # Neither config has experts
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
    panels: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    """Save expert activation config to a YAML file.

    Preserves existing config keys. Uses atomic write (temp + rename)
    via write_file utility.
    """
    try:
        # Read existing config to preserve other keys
        existing: dict[str, Any] = {}
        if path.exists():
            try:
                existing = yaml.safe_load(path.read_text()) or {}
            except yaml.YAMLError:
                existing = {}

        # Build experts section
        experts_section: dict[str, Any] = {"active": active}
        if panels:
            experts_section["panels"] = panels

        existing["experts"] = experts_section

        # Atomic write
        path.parent.mkdir(parents=True, exist_ok=True)
        content = yaml.dump(
            existing,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        )
        _atomic_write(path, content)

        return {"success": True, "path": str(path)}

    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to save: {e}",
        }


def filter_experts_by_role(
    agents: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Filter discovered agents to those with valid expert-role.

    Agents with invalid expert-role values are skipped with a warning
    logged. Agents without expert-role are excluded silently.
    """
    experts = []
    for agent in agents:
        role = agent.get("expert-role") or agent.get("expert_role")
        if role is None:
            continue
        if role not in _VALID_ROLES:
            logger.warning(
                "Skipping %s: invalid expert-role '%s', "
                "expected core|domain|qa",
                agent.get("name", "unknown"),
                role,
            )
            continue
        experts.append(agent)
    return experts


def resolve_active_experts(
    experts: list[dict[str, Any]],
    config: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[str]]:
    """Resolve which experts are active based on config.

    Returns (active_experts, warnings) where warnings lists any
    names in config.active that were not found in discovery.
    """
    warnings: list[str] = []
    active_names = set(config.get("active", []))
    discovered_names = {e["name"] for e in experts}

    # Check for dangling references
    for name in active_names:
        if name not in discovered_names:
            warnings.append(
                f"Expert '{name}' in config but not discovered "
                f"(plugin uninstalled?)"
            )

    active = [e for e in experts if e["name"] in active_names]
    return active, warnings


# --- Private helpers ---


def _read_yaml_safe(
    path: Path, warnings: list[str]
) -> dict[str, Any] | None:
    """Read YAML file, returning None if missing or malformed."""
    if not path.exists():
        return None
    try:
        data = yaml.safe_load(path.read_text())
        if not isinstance(data, dict):
            return None
        return data
    except yaml.YAMLError as e:
        warnings.append(
            f"Malformed YAML in {path}, ignoring experts config: {e}"
        )
        return None


def _validate_active_list(
    raw: Any, warnings: list[str]
) -> list[str]:
    """Validate and filter the active list to strings only."""
    if not isinstance(raw, list):
        warnings.append(
            f"experts.active is not a list (got {type(raw).__name__}), "
            f"treating as empty"
        )
        return []
    result = []
    for item in raw:
        if isinstance(item, str):
            result.append(item)
        else:
            warnings.append(
                f"Non-string entry in experts.active skipped: "
                f"{item!r} ({type(item).__name__})"
            )
    return result


def _validate_panels(
    raw: Any, warnings: list[str]
) -> dict[str, list[str]]:
    """Validate panels dict -- each value must be a list of strings."""
    if not isinstance(raw, dict):
        return {}
    result = {}
    for name, members in raw.items():
        if not isinstance(members, list):
            warnings.append(
                f"Panel '{name}' must be a list, skipping"
            )
            continue
        valid = [m for m in members if isinstance(m, str)]
        result[str(name)] = valid
    return result


def _atomic_write(path: Path, content: str) -> None:
    """Write content atomically via temp file + rename."""
    import os

    temp_path = path.parent / f".{path.name}.tmp.{os.getpid()}"
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        temp_path.replace(path)
    finally:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except Exception:
                pass
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `~/.aida/venv/bin/pytest tests/unit/test_expert_registry.py -v`
Expected: All tests PASS

- [ ] **Step 8: Commit**

```bash
git add skills/expert-registry/scripts/ tests/unit/test_expert_registry.py
git commit -m "feat(expert-registry): add registry module with config I/O and activation"
```

---

## Task 4: Create Panels Module

**Files:**

- Create: `skills/expert-registry/scripts/operations/panels.py`
- Test: `tests/unit/test_expert_panels.py`

- [ ] **Step 1: Write failing tests for panel resolution**

Create `tests/unit/test_expert_panels.py`:

```python
"""Tests for expert panel resolution and composition."""

import unittest
from typing import Any


def _make_expert(name: str, role: str = "domain") -> dict[str, Any]:
    """Helper to create a mock expert dict."""
    return {
        "name": name,
        "description": f"Test expert {name}",
        "expert-role": role,
    }


class TestResolvePanel(unittest.TestCase):
    """Test resolve_panel function."""

    def test_named_panel_found(self):
        """Named panel returns its members filtered to active."""
        from operations.panels import resolve_panel

        active = [
            _make_expert("sec", "core"),
            _make_expert("ts", "domain"),
            _make_expert("qa", "qa"),
        ]
        config = {
            "active": ["sec", "ts", "qa"],
            "panels": {"review": ["sec", "ts"]},
        }
        result = resolve_panel("review", active, config)
        self.assertTrue(result["panel_found"])
        self.assertEqual(result["experts"], ["sec", "ts"])
        self.assertEqual(result["warnings"], [])

    def test_named_panel_not_defined_falls_back(self):
        """Undefined panel returns all active with warning."""
        from operations.panels import resolve_panel

        active = [
            _make_expert("sec", "core"),
            _make_expert("ts", "domain"),
        ]
        config = {"active": ["sec", "ts"], "panels": {}}
        result = resolve_panel("missing-panel", active, config)
        self.assertFalse(result["panel_found"])
        self.assertEqual(result["experts"], ["sec", "ts"])
        self.assertTrue(any("missing-panel" in w for w in result["warnings"]))

    def test_no_panel_name_returns_all_active(self):
        """No panel name returns all active experts."""
        from operations.panels import resolve_panel

        active = [
            _make_expert("a", "core"),
            _make_expert("b", "domain"),
        ]
        config = {"active": ["a", "b"], "panels": {}}
        result = resolve_panel(None, active, config)
        self.assertTrue(result["panel_found"])
        self.assertEqual(result["experts"], ["a", "b"])

    def test_panel_filters_inactive_members(self):
        """Panel members not in active list are excluded."""
        from operations.panels import resolve_panel

        active = [_make_expert("sec", "core")]
        config = {
            "active": ["sec"],
            "panels": {"review": ["sec", "removed-expert"]},
        }
        result = resolve_panel("review", active, config)
        self.assertTrue(result["panel_found"])
        self.assertEqual(result["experts"], ["sec"])
        self.assertTrue(
            any("removed-expert" in w for w in result["warnings"])
        )

    def test_empty_active_returns_empty(self):
        """No active experts returns empty list."""
        from operations.panels import resolve_panel

        config = {"active": [], "panels": {}}
        result = resolve_panel(None, [], config)
        self.assertTrue(result["panel_found"])
        self.assertEqual(result["experts"], [])


class TestResolveByRole(unittest.TestCase):
    """Test resolve_by_role function."""

    def test_filter_core_role(self):
        """Returns only active experts with core role."""
        from operations.panels import resolve_by_role

        active = [
            _make_expert("sec", "core"),
            _make_expert("bp", "core"),
            _make_expert("ts", "domain"),
            _make_expert("qa", "qa"),
        ]
        result = resolve_by_role("core", active)
        self.assertEqual(result["experts"], ["sec", "bp"])
        self.assertEqual(result["warnings"], [])

    def test_unknown_role_returns_empty_with_warning(self):
        """Unknown role returns empty list with warning."""
        from operations.panels import resolve_by_role

        active = [_make_expert("sec", "core")]
        result = resolve_by_role("reviewer", active)
        self.assertEqual(result["experts"], [])
        self.assertTrue(any("reviewer" in w for w in result["warnings"]))

    def test_no_experts_with_role(self):
        """Valid role but no matching experts returns empty."""
        from operations.panels import resolve_by_role

        active = [_make_expert("sec", "core")]
        result = resolve_by_role("qa", active)
        self.assertEqual(result["experts"], [])
        self.assertEqual(result["warnings"], [])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `~/.aida/venv/bin/pytest tests/unit/test_expert_panels.py -v`
Expected: All tests FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement `panels.py`**

Create `skills/expert-registry/scripts/operations/panels.py`:

```python
"""Expert panel resolution and composition.

Provides resolve_panel() and resolve_by_role() for consuming skills
to get the right set of experts for a given context.
"""

from __future__ import annotations

from typing import Any

_VALID_ROLES = frozenset({"core", "domain", "qa"})


def resolve_panel(
    panel_name: str | None,
    active_experts: list[dict[str, Any]],
    config: dict[str, Any],
) -> dict[str, Any]:
    """Resolve a panel to a list of expert names.

    Args:
        panel_name: Named panel to look up, or None for all active.
        active_experts: List of active expert dicts (from registry).
        config: Loaded experts config (with panels dict).

    Returns:
        Dict with keys: experts (list[str]), panel_found (bool),
        warnings (list[str]).
    """
    active_names = [e["name"] for e in active_experts]
    active_set = set(active_names)
    warnings: list[str] = []

    if panel_name is None:
        # No panel requested -- return all active
        return {
            "experts": active_names,
            "panel_found": True,
            "warnings": warnings,
        }

    panels = config.get("panels", {})
    if panel_name in panels:
        # Named panel found -- filter to active only
        members = panels[panel_name]
        resolved = []
        for name in members:
            if name in active_set:
                resolved.append(name)
            else:
                warnings.append(
                    f"Panel '{panel_name}' member '{name}' is not "
                    f"active or not discovered, excluded"
                )
        return {
            "experts": resolved,
            "panel_found": True,
            "warnings": warnings,
        }

    # Panel not defined -- fall back to all active
    warnings.append(
        f"Panel '{panel_name}' not defined, using all active experts"
    )
    return {
        "experts": active_names,
        "panel_found": False,
        "warnings": warnings,
    }


def resolve_by_role(
    role: str,
    active_experts: list[dict[str, Any]],
) -> dict[str, Any]:
    """Return active experts matching a given role.

    Args:
        role: One of "core", "domain", "qa".
        active_experts: List of active expert dicts.

    Returns:
        Dict with keys: experts (list[str]), warnings (list[str]).
    """
    warnings: list[str] = []

    if role not in _VALID_ROLES:
        warnings.append(
            f"Unknown expert role '{role}', expected core|domain|qa"
        )
        return {"experts": [], "warnings": warnings}

    matched = [
        e["name"]
        for e in active_experts
        if (e.get("expert-role") or e.get("expert_role")) == role
    ]
    return {"experts": matched, "warnings": warnings}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `~/.aida/venv/bin/pytest tests/unit/test_expert_panels.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add skills/expert-registry/scripts/operations/panels.py \
  tests/unit/test_expert_panels.py
git commit -m "feat(expert-registry): add panel resolution module"
```

---

## Task 5: Create `manage.py` Entry Point

**Files:**

- Create: `skills/expert-registry/scripts/manage.py`

- [ ] **Step 1: Implement manage.py**

Create `skills/expert-registry/scripts/manage.py`:

```python
#!/usr/bin/env python3
"""Expert Registry Manager -- Two-Phase API.

Phase 1 (--get-questions): Discover experts, load activation state,
    return expert list with status and questions.
Phase 2 (--execute): Write updated activation or panel config.
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

import _paths  # noqa: F401

import yaml
from operations.registry import (
    filter_experts_by_role,
    load_experts_config,
    resolve_active_experts,
    save_experts_config,
)
from operations.panels import resolve_panel, resolve_by_role

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Default config paths
_GLOBAL_CONFIG = Path.home() / ".claude" / "aida.yml"
_PROJECT_CONFIG = Path.cwd() / ".claude" / "aida-project-context.yml"


def _safe_json_load(raw: str | None) -> dict[str, Any]:
    """Parse JSON string or return empty dict."""
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}") from e


def _discover_all_experts() -> list[dict[str, Any]]:
    """Discover agents and filter to those with expert-role."""
    try:
        from utils.agents import discover_agents

        agents = discover_agents()
    except ImportError:
        logger.warning("Agent discovery not available")
        agents = []
    return filter_experts_by_role(agents)


def get_questions(context: dict[str, Any]) -> dict[str, Any]:
    """Phase 1: Discover experts and return current state."""
    operation = context.get("operation", "list")
    global_path = Path(context.get("global_path", str(_GLOBAL_CONFIG)))
    project_path = Path(
        context.get("project_path", str(_PROJECT_CONFIG))
    )

    # Discover all experts
    experts = _discover_all_experts()

    # Load current config
    config = load_experts_config(
        global_path=global_path,
        project_path=project_path,
    )

    # Resolve which are active
    active, dangling_warnings = resolve_active_experts(experts, config)
    active_names = {e["name"] for e in active}

    # Build expert list with status
    expert_list = []
    for e in experts:
        expert_list.append({
            "name": e["name"],
            "description": e.get("description", ""),
            "expert-role": (
                e.get("expert-role") or e.get("expert_role", "")
            ),
            "source": e.get("source", "unknown"),
            "active": e["name"] in active_names,
        })

    result = {
        "success": True,
        "operation": operation,
        "experts": expert_list,
        "config": {
            "active": config["active"],
            "panels": config["panels"],
            "source": config["source"],
        },
        "warnings": config["warnings"] + dangling_warnings,
    }

    if operation == "configure":
        result["questions"] = [
            {
                "key": "selected_experts",
                "type": "multi-select",
                "label": "Select active experts",
                "options": [
                    {
                        "value": e["name"],
                        "label": (
                            f"{e['name']} "
                            f"({e.get('expert-role', '')}, "
                            f"{e.get('source', '')})"
                        ),
                        "selected": e["name"] in active_names,
                    }
                    for e in expert_list
                ],
            },
            {
                "key": "save_target",
                "type": "choice",
                "label": "Save to project or global?",
                "options": ["project", "global"],
                "default": "project",
            },
        ]

    return result


def execute(
    context: dict[str, Any],
    responses: dict[str, Any],
) -> dict[str, Any]:
    """Phase 2: Write updated config."""
    operation = context.get("operation", "configure")
    global_path = Path(context.get("global_path", str(_GLOBAL_CONFIG)))
    project_path = Path(
        context.get("project_path", str(_PROJECT_CONFIG))
    )

    if operation == "configure":
        selected = responses.get("selected_experts", [])
        target = responses.get("save_target", "project")
        path = project_path if target == "project" else global_path

        panels = None
        if target == "project":
            # Preserve existing panels
            config = load_experts_config(
                global_path=global_path,
                project_path=project_path,
            )
            panels = config.get("panels") or None

        return save_experts_config(
            path=path,
            active=selected,
            panels=panels,
        )

    elif operation == "panel-create":
        panel_name = responses.get("panel_name", "")
        members = responses.get("members", [])
        if not panel_name:
            return {
                "success": False,
                "message": "Panel name is required",
            }
        config = load_experts_config(
            global_path=global_path,
            project_path=project_path,
        )
        panels = config.get("panels", {})
        panels[panel_name] = members
        return save_experts_config(
            path=project_path,
            active=config["active"],
            panels=panels,
        )

    elif operation == "panel-remove":
        panel_name = responses.get("panel_name", "")
        config = load_experts_config(
            global_path=global_path,
            project_path=project_path,
        )
        panels = config.get("panels", {})
        panels.pop(panel_name, None)
        return save_experts_config(
            path=project_path,
            active=config["active"],
            panels=panels if panels else None,
        )

    return {"success": False, "message": f"Unknown operation: {operation}"}


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Expert Registry Manager"
    )
    parser.add_argument(
        "--get-questions",
        action="store_true",
        help="Phase 1: Discover experts and return current state",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Phase 2: Write updated config",
    )
    parser.add_argument("--context", type=str, help="JSON context")
    parser.add_argument("--responses", type=str, help="JSON responses")

    args = parser.parse_args()

    try:
        if args.get_questions:
            context = _safe_json_load(args.context)
            result = get_questions(context)
            print(json.dumps(result, indent=2))
            return 0
        elif args.execute:
            context = _safe_json_load(args.context)
            responses = _safe_json_load(args.responses)
            result = execute(context, responses)
            print(json.dumps(result, indent=2))
            return 0 if result.get("success", False) else 1
        else:
            parser.print_help()
            return 1
    except ValueError as e:
        logger.error("Validation error: %s", e)
        print(json.dumps({"success": False, "message": str(e)}))
        return 1
    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        print(json.dumps({
            "success": False,
            "message": f"Error: {e}",
            "error_type": type(e).__name__,
        }))
        return 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run full test suite**

Run: `~/.aida/venv/bin/pytest tests/ -v --tb=short`
Expected: All tests pass (existing + new)

- [ ] **Step 3: Commit**

```bash
git add skills/expert-registry/scripts/manage.py
git commit -m "feat(expert-registry): add two-phase API entry point"
```

---

## Task 6: Create SKILL.md and Reference Docs

**Files:**

- Create: `skills/expert-registry/SKILL.md`
- Create: `skills/expert-registry/references/schemas.md`

- [ ] **Step 1: Create SKILL.md**

Create `skills/expert-registry/SKILL.md`:

```markdown
---
type: skill
name: expert-registry
description: >-
  Manage expert agent activation and panel composition for
  project and global scopes. Provides list, configure, and
  panel operations for expert-based workflows like code review
  and plan grading.
version: 0.1.0
tags:
  - core
  - management
  - experts
  - panels
---

# Expert Registry

Manage which expert agents are active for panel dispatch and how
they are organized into named panels.

## Activation

This skill activates when:

- User invokes `/aida expert [list|configure|panels|panel]`
- A consuming skill needs to resolve an expert panel

## Operations

### Command Routing

Parse the command to determine:

1. **Operation**: `list`, `configure`, `panels`, `panel create`,
   `panel remove`
2. **Arguments**: panel name (for create/remove)

### List (`/aida expert list`)

Show all discovered experts with plugin source, role, activation
status, and config source.

```bash
python {base_directory}/scripts/manage.py \
  --get-questions \
  --context='{"operation": "list"}'
```

Present the returned expert list as a formatted table:

```text
Expert Registry -- Project: {project_name}

Plugin: {plugin_name} ({source})
  Name                    Role     Status      Source
  ─────────────────────── ──────── ─────────── ────────
  {name}                  {role}   [{status}]  {source}
```

### Configure (`/aida expert configure`)

Interactive expert selection.

#### Phase 1: Gather State

```bash
python {base_directory}/scripts/manage.py \
  --get-questions \
  --context='{"operation": "configure"}'
```

Present the numbered expert list with current activation status.
User toggles by number or role shortcut (e.g., "all core",
"none domain").

#### Phase 2: Save Config

```bash
python {base_directory}/scripts/manage.py \
  --execute \
  --context='{"operation": "configure"}' \
  --responses='{"selected_experts": [...], "save_target": "project"}'
```

### Panels (`/aida expert panels`)

Show named panels and their composition. Use the Phase 1 list
response and format the panels section, flagging stale entries.

### Panel Create (`/aida expert panel create <name>`)

#### Phase 1: Show active experts for selection

```bash
python {base_directory}/scripts/manage.py \
  --get-questions \
  --context='{"operation": "panel-create"}'
```

If no active experts, report:
"No active experts. Run /aida expert configure first."

#### Phase 2: Save panel

```bash
python {base_directory}/scripts/manage.py \
  --execute \
  --context='{"operation": "panel-create"}' \
  --responses='{"panel_name": "...", "members": [...]}'
```

### Panel Remove (`/aida expert panel remove <name>`)

```bash
python {base_directory}/scripts/manage.py \
  --execute \
  --context='{"operation": "panel-remove"}' \
  --responses='{"panel_name": "..."}'
```

```text
```

- [ ] **Step 2: Create references/schemas.md**

Create `skills/expert-registry/references/schemas.md`:

```markdown
---
type: reference
title: Expert Registry Schemas
description: >-
  Configuration schemas for expert activation and panel
  composition in global and project config files.
---

# Expert Registry Schemas

## Agent Frontmatter

Agents declare panel eligibility via the `expert-role` field:

```yaml
---
type: agent
name: security-expert
description: Security review expert
version: 1.0.0
tags:
  - security
expert-role: core
---
```

Valid values: `core`, `domain`, `qa`

## Global Config (`~/.claude/aida.yml`)

```yaml
experts:
  active:
    - security-expert
    - best-practices-reviewer
```

## Project Config (`aida-project-context.yml`)

```yaml
experts:
  active:
    - security-expert
    - best-practices-reviewer
    - nestjs-expert
  panels:
    code-review:
      - security-expert
      - best-practices-reviewer
    plan-grading:
      - security-expert
      - best-practices-reviewer
      - nestjs-expert
```

## Semantics

- `active` absent: fall through to next config layer
- `active: []`: intentional deactivation (zero experts)
- `panels`: project-only, not supported in global config
- Panel members filtered to active experts at resolution time
- Dangling names (not discovered) logged as warnings

```text
```

- [ ] **Step 3: Create empty questionnaire template**

Create `skills/expert-registry/templates/questionnaires/configure.yml`:

```yaml
# Expert selection questionnaire
# Used by manage.py Phase 1 to structure the configure flow
title: "Expert Configuration"
description: "Select which experts are active for panel dispatch"
sections:
  - key: expert_selection
    label: "Active Experts"
    type: multi-select
    dynamic: true  # Options populated from discovery at runtime
  - key: save_target
    label: "Save Location"
    type: choice
    options:
      - value: project
        label: "Project (aida-project-context.yml)"
      - value: global
        label: "Global (~/.claude/aida.yml)"
    default: project
```

- [ ] **Step 4: Run linting**

Run: `~/.aida/venv/bin/ruff check skills/expert-registry/`
Expected: No errors

- [ ] **Step 5: Commit**

```bash
git add skills/expert-registry/SKILL.md \
  skills/expert-registry/references/schemas.md \
  skills/expert-registry/templates/questionnaires/configure.yml
git commit -m "feat(expert-registry): add SKILL.md and reference docs"
```

---

## Task 7: Update AIDA Dispatcher

**Files:**

- Modify: `skills/aida/SKILL.md`

- [ ] **Step 1: Read current SKILL.md routing sections**

Read `skills/aida/SKILL.md` to find where agent/skill/plugin/hook
routing is defined and the Help Text section.

- [ ] **Step 2: Add expert routing**

Add a new routing section alongside the existing management command
routing. Find the section that routes agent/skill/plugin/hook commands
and add:

```markdown
### Expert Registry Commands

For `expert` commands:

- **Invoke the `expert-registry` skill** to handle operations
- Pass the full command arguments to the skill
- The skill handles list, configure, panels, and panel operations

**Process:**

1. Parse the command to extract:
   - Operation: `list`, `configure`, `panels`, `panel create`,
     `panel remove`
   - Arguments: panel name (for create/remove)

2. Invoke `expert-registry` skill with the parsed context

**Examples:**

```text
/aida expert list                  → expert-registry skill
/aida expert configure             → expert-registry skill
/aida expert panels                → expert-registry skill
/aida expert panel create review   → expert-registry skill
/aida expert panel remove review   → expert-registry skill
```

```text
```

- [ ] **Step 3: Add help text entry**

In the Help Text section, add under "Extension Management" (after
the hook line):

```markdown
### Expert Registry
- `/aida expert list` - List available experts and activation status
- `/aida expert configure` - Select active experts (project or global)
- `/aida expert panels` - Show named panel compositions
- `/aida expert panel create <name>` - Create a named expert panel
- `/aida expert panel remove <name>` - Remove a named panel
```

- [ ] **Step 4: Commit**

```bash
git add skills/aida/SKILL.md
git commit -m "feat(expert-registry): add expert routing to AIDA dispatcher"
```

---

## Task 8: Add Configure Flow Nudge

**Files:**

- Modify: `skills/aida/scripts/configure.py`

- [ ] **Step 1: Read configure.py to find post-config completion point**

Read `skills/aida/scripts/configure.py` and find where
`config_complete` is set to `True` or where the configuration
flow completes successfully.

- [ ] **Step 2: Add expert configuration nudge**

After project configuration completes, add a check: if any
discovered agents have `expert-role` set and the project config
has no `experts` section, print a nudge message.

Add after the project config write succeeds:

```python
# Nudge user toward expert configuration if experts available
try:
    from utils.agents import discover_agents
    agents = discover_agents()
    has_experts = any(
        a.get("expert-role") or a.get("expert_role")
        for a in agents
    )
    project_config = yaml.safe_load(
        config_path.read_text()
    ) or {}
    has_expert_config = "experts" in project_config.get(
        "experts", {}
    ) if "experts" in project_config else False

    if has_experts and not has_expert_config:
        print(
            "\nExpert agents detected from installed plugins.\n"
            "Run `/aida expert configure` to select which "
            "experts are active for this project."
        )
except Exception:
    pass  # Non-critical, don't break config flow
```

- [ ] **Step 3: Commit**

```bash
git add skills/aida/scripts/configure.py
git commit -m "feat(expert-registry): add expert config nudge after project setup"
```

---

## Task 9: Run Full Test Suite and Lint

**Files:** None (verification only)

- [ ] **Step 1: Run all tests**

Run: `~/.aida/venv/bin/pytest tests/ -v --tb=short`
Expected: All tests pass

- [ ] **Step 2: Run linting**

Run: `make lint`
Expected: No errors from ruff, yamllint, or markdownlint

- [ ] **Step 3: Fix any lint issues found**

If lint finds issues, fix them in the appropriate files.

- [ ] **Step 4: Run tests again after fixes**

Run: `~/.aida/venv/bin/pytest tests/ -v --tb=short`
Expected: All tests pass

- [ ] **Step 5: Final commit if fixes were needed**

```bash
git add -u
git commit -m "fix(expert-registry): resolve lint issues"
```
