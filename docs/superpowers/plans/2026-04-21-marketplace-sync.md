# Marketplace Sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task.
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a marketplace-sync skill that resolves transitive plugin
dependency trees, detects version drift, and updates outdated plugins.

**Architecture:** Six modules — shared `VersionRange` in
`scripts/shared/version.py`, then four domain modules in
`skills/marketplace-sync/scripts/sync_ops/` (scanner, resolver, report,
updater), plus a `manage.py` entry point. TDD throughout: write failing
tests first, then implement.

**Tech Stack:** Python 3.8+, `packaging.version.Version`, PyYAML,
pytest with `@pytest.mark.parametrize`

**Spec:** `docs/superpowers/specs/2026-04-21-marketplace-sync-design.md`

---

## Task 1: Shared VersionRange Module

**Files:**

- Create: `scripts/shared/version.py`
- Create: `tests/unit/test_version.py`

- [ ] **Step 1: Write failing tests for VersionRange**

```python
"""Tests for shared version range module."""

import pytest
import sys
from pathlib import Path

sys.path.insert(
    0, str(Path(__file__).parent.parent.parent / "scripts")
)

from shared.version import VersionRange, satisfies, parse_version  # noqa: E402


class TestParseVersion:
    def test_valid_version(self):
        v = parse_version("1.2.3")
        assert str(v) == "1.2.3"

    def test_invalid_version_letters(self):
        with pytest.raises(ValueError, match="Invalid version"):
            parse_version("abc")

    def test_invalid_version_prerelease(self):
        with pytest.raises(ValueError, match="Pre-release"):
            parse_version("1.0.0-beta.1")

    def test_invalid_version_two_parts(self):
        with pytest.raises(ValueError, match="Invalid version"):
            parse_version("1.0")

    def test_version_too_long(self):
        with pytest.raises(ValueError, match="too long"):
            parse_version("1." + "0" * 70 + ".0")


class TestVersionRange:
    @pytest.mark.parametrize(
        "constraint,version,expected",
        [
            # Caret operator
            ("^1.2.3", "1.2.3", True),
            ("^1.2.3", "1.9.9", True),
            ("^1.2.3", "2.0.0", False),
            ("^1.2.3", "1.2.2", False),
            # Zero-major caret
            ("^0.2.3", "0.2.5", True),
            ("^0.2.3", "0.3.0", False),
            # Zero-minor caret
            ("^0.0.3", "0.0.3", True),
            ("^0.0.3", "0.0.4", False),
            # Tilde operator
            ("~1.2.3", "1.2.9", True),
            ("~1.2.3", "1.3.0", False),
            ("~0.2.3", "0.2.9", True),
            ("~0.2.3", "0.3.0", False),
            # Greater-equal operator
            (">=1.0.0", "1.0.0", True),
            (">=1.0.0", "2.5.0", True),
            (">=1.0.0", "0.9.9", False),
            # Exact operator
            ("=1.2.3", "1.2.3", True),
            ("=1.2.3", "1.2.4", False),
            # Bare version (exact match)
            ("1.2.3", "1.2.3", True),
            ("1.2.3", "1.2.4", False),
            # Whitespace tolerance
            (">= 1.0.0", "1.0.0", True),
            ("^ 1.2.3", "1.5.0", True),
        ],
    )
    def test_satisfies(self, constraint, version, expected):
        assert satisfies(version, constraint) is expected

    def test_invalid_constraint_too_long(self):
        with pytest.raises(ValueError, match="too long"):
            VersionRange("^" + "1" * 70 + ".0.0")

    def test_invalid_constraint_bad_chars(self):
        with pytest.raises(ValueError, match="Invalid characters"):
            VersionRange(">=1.0.0; rm -rf /")

    def test_invalid_constraint_empty(self):
        with pytest.raises(ValueError, match="empty"):
            VersionRange("")

    def test_invalid_constraint_operator_only(self):
        with pytest.raises(ValueError, match="Invalid version"):
            VersionRange("^")

    def test_invalid_constraint_bad_version(self):
        with pytest.raises(ValueError, match="Invalid version"):
            VersionRange(">=abc")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `~/.aida/venv/bin/pytest tests/unit/test_version.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'shared.version'`

- [ ] **Step 3: Implement version.py**

```python
"""Shared version range parsing and satisfaction checking.

Uses packaging.version.Version for correct semver comparison.
Supports ^, ~, >=, and = operators with zero-major special cases.
"""

import re
from typing import Optional, Tuple

from packaging.version import Version, InvalidVersion


MAX_CONSTRAINT_LENGTH = 64
VALID_CONSTRAINT_CHARS = re.compile(r'^[0-9.^~>=< ]+$')
STRICT_VERSION = re.compile(r'^\d+\.\d+\.\d+$')
PRERELEASE_VERSION = re.compile(r'^\d+\.\d+\.\d+[-+]')


def parse_version(version_str: str) -> Version:
    """Parse and validate a strict semver version string.

    Args:
        version_str: Version string like "1.2.3"

    Returns:
        packaging.version.Version object

    Raises:
        ValueError: If version is invalid, pre-release, or too long
    """
    if len(version_str) > MAX_CONSTRAINT_LENGTH:
        raise ValueError(f"Version string too long: {len(version_str)} chars")
    if PRERELEASE_VERSION.match(version_str):
        raise ValueError(f"Pre-release versions not supported: {version_str}")
    if not STRICT_VERSION.match(version_str):
        raise ValueError(f"Invalid version format: {version_str}")
    return Version(version_str)


class VersionRange:
    """A version constraint that can check satisfaction.

    Supports operators: ^ (compatible), ~ (patch), >= (minimum), = (exact).
    Bare versions without an operator are treated as exact match.
    """

    def __init__(self, constraint: str) -> None:
        if not constraint or not constraint.strip():
            raise ValueError("Constraint string is empty")
        if len(constraint) > MAX_CONSTRAINT_LENGTH:
            raise ValueError(
                f"Constraint string too long: {len(constraint)} chars"
            )
        if not VALID_CONSTRAINT_CHARS.match(constraint):
            raise ValueError(f"Invalid characters in constraint: {constraint}")

        self.raw = constraint.strip()
        self._lower, self._upper = self._parse(self.raw)

    def _parse(self, raw: str) -> Tuple[Version, Optional[Version]]:
        """Parse constraint into (lower_bound, upper_bound) pair."""
        if raw.startswith("^"):
            v = parse_version(raw[1:].strip())
            parts = [int(x) for x in str(v).split(".")]
            if parts[0] != 0:
                upper = Version(f"{parts[0] + 1}.0.0")
            elif parts[1] != 0:
                upper = Version(f"0.{parts[1] + 1}.0")
            else:
                upper = Version(f"0.0.{parts[2] + 1}")
            return v, upper
        elif raw.startswith("~"):
            v = parse_version(raw[1:].strip())
            parts = [int(x) for x in str(v).split(".")]
            upper = Version(f"{parts[0]}.{parts[1] + 1}.0")
            return v, upper
        elif raw.startswith(">="):
            v = parse_version(raw[2:].strip())
            return v, None
        elif raw.startswith("="):
            v = parse_version(raw[1:].strip())
            return v, v
        else:
            v = parse_version(raw)
            return v, v

    def contains(self, version_str: str) -> bool:
        """Check if a version satisfies this constraint."""
        v = parse_version(version_str)
        if v < self._lower:
            return False
        if self._upper is not None:
            if self._lower == self._upper:
                return v == self._lower
            return v < self._upper
        return True


def satisfies(version: str, constraint: str) -> bool:
    """Check if a version satisfies a constraint string.

    Args:
        version: Version string like "1.2.3"
        constraint: Constraint like "^1.0.0", ">=1.2.0", "=1.0.0"

    Returns:
        True if version is within the constraint range
    """
    return VersionRange(constraint).contains(version)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `~/.aida/venv/bin/pytest tests/unit/test_version.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/shared/version.py tests/unit/test_version.py
git commit -m "feat(marketplace-sync): add shared VersionRange module

Thin wrapper around packaging.version.Version supporting ^, ~, >=,
and = operators with zero-major special cases per npm/semver convention."
```

---

## Task 2: Dependency Graph Resolver

**Files:**

- Create: `skills/marketplace-sync/scripts/sync_ops/__init__.py`
- Create: `skills/marketplace-sync/scripts/sync_ops/resolver.py`
- Create: `tests/unit/test_resolver.py`

- [ ] **Step 1: Create sync_ops package**

```python
# skills/marketplace-sync/scripts/sync_ops/__init__.py
"""Marketplace sync operations package."""
```

- [ ] **Step 2: Write failing tests for resolver**

```python
"""Tests for marketplace-sync dependency graph resolver."""

import sys
from pathlib import Path

import pytest

sys.path.insert(
    0,
    str(
        Path(__file__).parent.parent.parent
        / "skills"
        / "marketplace-sync"
        / "scripts"
    ),
)
sys.path.insert(
    0, str(Path(__file__).parent.parent.parent / "scripts")
)

from sync_ops.resolver import (  # noqa: E402
    DependencyEdge,
    ResolutionResult,
    build_graph,
    resolve_dependencies,
)


def _make_plugins(plugin_map):
    """Build a list of (name, version, dependencies) tuples.

    plugin_map: dict of name -> (version, {dep: constraint})
    """
    return [
        (name, ver, deps) for name, (ver, deps) in plugin_map.items()
    ]


class TestBuildGraph:
    def test_empty_plugins(self):
        result = build_graph([])
        assert result.graph == {}
        assert result.install_order == []
        assert result.cycles == []

    def test_single_plugin_no_deps(self):
        plugins = _make_plugins({"core": ("1.0.0", {})})
        result = build_graph(plugins)
        assert result.install_order == ["core"]
        assert result.graph == {"core": []}

    def test_simple_dependency(self):
        plugins = _make_plugins({
            "core": ("1.0.0", {}),
            "eng": ("1.0.0", {"core": ">=1.0.0"}),
        })
        result = build_graph(plugins)
        assert result.install_order.index("core") < result.install_order.index("eng")
        assert len(result.graph["eng"]) == 1
        edge = result.graph["eng"][0]
        assert edge.dependency == "core"
        assert edge.satisfied is True

    def test_unsatisfied_dependency(self):
        plugins = _make_plugins({
            "core": ("0.9.0", {}),
            "eng": ("1.0.0", {"core": ">=1.0.0"}),
        })
        result = build_graph(plugins)
        edge = result.graph["eng"][0]
        assert edge.satisfied is False
        assert edge.installed == "0.9.0"

    def test_diamond_dependency(self):
        plugins = _make_plugins({
            "d": ("1.2.0", {}),
            "b": ("1.0.0", {"d": ">=1.0.0"}),
            "c": ("1.0.0", {"d": ">=1.2.0"}),
            "a": ("1.0.0", {"b": ">=1.0.0", "c": ">=1.0.0"}),
        })
        result = build_graph(plugins)
        order = result.install_order
        assert order.index("d") < order.index("b")
        assert order.index("d") < order.index("c")
        assert order.index("b") < order.index("a")
        assert order.index("c") < order.index("a")

    def test_cycle_detection_length_2(self):
        plugins = _make_plugins({
            "a": ("1.0.0", {"b": ">=1.0.0"}),
            "b": ("1.0.0", {"a": ">=1.0.0"}),
        })
        result = build_graph(plugins)
        assert len(result.cycles) > 0

    def test_cycle_detection_length_3(self):
        plugins = _make_plugins({
            "a": ("1.0.0", {"b": ">=1.0.0"}),
            "b": ("1.0.0", {"c": ">=1.0.0"}),
            "c": ("1.0.0", {"a": ">=1.0.0"}),
        })
        result = build_graph(plugins)
        assert len(result.cycles) > 0

    def test_self_dependency(self):
        plugins = _make_plugins({
            "a": ("1.0.0", {"a": ">=1.0.0"}),
        })
        result = build_graph(plugins)
        assert len(result.cycles) > 0

    def test_unresolved_dependency(self):
        plugins = _make_plugins({
            "eng": ("1.0.0", {"missing-plugin": ">=1.0.0"}),
        })
        result = build_graph(plugins)
        assert "missing-plugin" in result.unresolved

    def test_conflict_detection(self):
        plugins = _make_plugins({
            "core": ("1.5.0", {}),
            "a": ("1.0.0", {"core": ">=2.0.0"}),
            "b": ("1.0.0", {"core": "^1.0.0"}),
        })
        result = build_graph(plugins)
        # a requires core >=2.0.0, core is 1.5.0 -> unsatisfied
        a_edge = result.graph["a"][0]
        assert a_edge.satisfied is False

    def test_transitive_three_levels(self):
        plugins = _make_plugins({
            "c": ("1.0.0", {}),
            "b": ("1.0.0", {"c": ">=1.0.0"}),
            "a": ("1.0.0", {"b": ">=1.0.0"}),
        })
        result = build_graph(plugins)
        order = result.install_order
        assert order.index("c") < order.index("b") < order.index("a")


class TestResolveDependencies:
    def test_resolve_marks_satisfaction(self):
        plugins = _make_plugins({
            "core": ("1.4.0", {}),
            "eng": ("1.0.0", {"core": ">=1.0.0"}),
        })
        result = resolve_dependencies(plugins)
        assert isinstance(result, ResolutionResult)
        edge = result.graph["eng"][0]
        assert edge.satisfied is True
        assert edge.installed == "1.4.0"
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `~/.aida/venv/bin/pytest tests/unit/test_resolver.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 4: Implement resolver.py**

```python
"""Dependency graph resolver with topological sort and cycle detection.

Builds an adjacency graph from plugin dependency declarations,
detects cycles, resolves transitive dependencies, and produces
a topologically sorted install order.
"""

import re
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import sys
from pathlib import Path

# Add shared scripts to path for version module
sys.path.insert(
    0, str(Path(__file__).parent.parent.parent.parent.parent / "scripts")
)

from shared.version import satisfies  # noqa: E402

MAX_DEPENDENCY_DEPTH = 20
MAX_TOTAL_PLUGINS = 200
DEP_NAME_PATTERN = re.compile(r'^[a-z][a-z0-9-]{0,49}$')
MAX_DEPS_PER_PLUGIN = 50


@dataclass
class DependencyEdge:
    """A single dependency relationship."""
    dependent: str
    dependency: str
    constraint: str
    satisfied: bool
    installed: Optional[str]


@dataclass
class ResolutionResult:
    """Output from the dependency graph resolver."""
    graph: Dict[str, List[DependencyEdge]] = field(default_factory=dict)
    install_order: List[str] = field(default_factory=list)
    cycles: List[List[str]] = field(default_factory=list)
    conflicts: List[Tuple[str, str, str]] = field(default_factory=list)
    unresolved: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


def _validate_deps(
    name: str, deps: Dict[str, str]
) -> Tuple[Dict[str, str], List[str]]:
    """Validate dependency names and constraints, return clean deps + warnings."""
    clean = {}
    warnings = []
    if len(deps) > MAX_DEPS_PER_PLUGIN:
        warnings.append(
            f"{name}: declares {len(deps)} dependencies (max {MAX_DEPS_PER_PLUGIN}), truncating"
        )
        deps = dict(list(deps.items())[:MAX_DEPS_PER_PLUGIN])
    for dep_name, constraint in deps.items():
        if not DEP_NAME_PATTERN.match(dep_name):
            warnings.append(f"{name}: invalid dependency name '{dep_name}', skipping")
            continue
        clean[dep_name] = constraint
    return clean, warnings


def build_graph(
    plugins: List[Tuple[str, Optional[str], Dict[str, str]]]
) -> ResolutionResult:
    """Build dependency graph from plugin data.

    Args:
        plugins: List of (name, installed_version, dependencies) tuples.
                 installed_version may be None for uninstalled plugins.
                 dependencies is {dep_name: constraint_string}.

    Returns:
        ResolutionResult with graph, install order, cycles, and unresolved deps.
    """
    if len(plugins) > MAX_TOTAL_PLUGINS:
        return ResolutionResult(
            warnings=[f"Too many plugins ({len(plugins)} > {MAX_TOTAL_PLUGINS})"]
        )

    result = ResolutionResult()
    versions: Dict[str, Optional[str]] = {}
    adjacency: Dict[str, List[str]] = defaultdict(list)
    in_degree: Dict[str, int] = {}

    # Index all known plugins
    for name, version, _ in plugins:
        versions[name] = version
        in_degree.setdefault(name, 0)
        result.graph[name] = []

    # Build edges
    all_unresolved = set()
    for name, version, raw_deps in plugins:
        deps, warnings = _validate_deps(name, raw_deps)
        result.warnings.extend(warnings)

        for dep_name, constraint in deps.items():
            dep_version = versions.get(dep_name)

            if dep_name not in versions:
                all_unresolved.add(dep_name)
                satisfied = False
                installed = None
            elif dep_version is None or dep_version == "unknown":
                satisfied = False
                installed = dep_version
            else:
                try:
                    satisfied = satisfies(dep_version, constraint)
                except ValueError:
                    satisfied = False
                    result.warnings.append(
                        f"{name}: invalid constraint '{constraint}' for {dep_name}"
                    )
                installed = dep_version

            edge = DependencyEdge(
                dependent=name,
                dependency=dep_name,
                constraint=constraint,
                satisfied=satisfied,
                installed=installed,
            )
            result.graph[name].append(edge)

            if dep_name in versions:
                adjacency[dep_name].append(name)
                in_degree.setdefault(name, 0)
                in_degree[name] = in_degree.get(name, 0) + 1
                in_degree.setdefault(dep_name, 0)

    result.unresolved = sorted(all_unresolved)

    # Kahn's algorithm for topological sort + cycle detection
    queue = deque(
        [node for node in in_degree if in_degree[node] == 0]
    )
    order = []
    visited = 0

    while queue:
        node = queue.popleft()
        order.append(node)
        visited += 1
        for dependent in adjacency.get(node, []):
            in_degree[dependent] -= 1
            if in_degree[dependent] == 0:
                queue.append(dependent)

    if visited < len(in_degree):
        # Cycle detected — find the nodes involved
        cycle_nodes = [n for n in in_degree if in_degree[n] > 0]
        result.cycles.append(sorted(cycle_nodes))
        # Still provide a partial order
        result.install_order = order + sorted(cycle_nodes)
    else:
        result.install_order = order

    return result


def resolve_dependencies(
    plugins: List[Tuple[str, Optional[str], Dict[str, str]]]
) -> ResolutionResult:
    """Resolve dependencies for a set of plugins.

    Convenience wrapper around build_graph that validates inputs.

    Args:
        plugins: List of (name, installed_version, dependencies) tuples.

    Returns:
        ResolutionResult
    """
    return build_graph(plugins)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `~/.aida/venv/bin/pytest tests/unit/test_resolver.py -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add skills/marketplace-sync/scripts/sync_ops/__init__.py \
       skills/marketplace-sync/scripts/sync_ops/resolver.py \
       tests/unit/test_resolver.py
git commit -m "feat(marketplace-sync): add dependency graph resolver

Kahn's algorithm topological sort with cycle detection, transitive
resolution, and dependency name/constraint validation."
```

---

## Task 3: Plugin Scanner

**Files:**

- Create: `skills/marketplace-sync/scripts/sync_ops/scanner.py`
- Create: `tests/unit/test_scanner.py`

- [ ] **Step 1: Write failing tests for scanner**

```python
"""Tests for marketplace-sync plugin scanner."""

import json
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(
    0,
    str(
        Path(__file__).parent.parent.parent
        / "skills"
        / "marketplace-sync"
        / "scripts"
    ),
)
sys.path.insert(
    0, str(Path(__file__).parent.parent.parent / "scripts")
)

from sync_ops.scanner import scan_plugins, PluginState  # noqa: E402


def _setup_ecosystem(tmp, installed=None, cache=None, marketplaces=None):
    """Build a mock plugin ecosystem under tmp.

    installed: dict for installed_plugins.json
    cache: {marketplace: {plugin: {version: plugin_json_dict}}}
    marketplaces: {marketplace_id: marketplace_json_dict}
    """
    plugins_dir = Path(tmp) / ".claude" / "plugins"
    plugins_dir.mkdir(parents=True)

    # installed_plugins.json
    if installed is not None:
        (plugins_dir / "installed_plugins.json").write_text(
            json.dumps(installed), encoding="utf-8"
        )

    # cache
    if cache:
        for mkt, plugins in cache.items():
            for plugin_name, versions in plugins.items():
                for ver, pj in versions.items():
                    pdir = plugins_dir / "cache" / mkt / plugin_name / ver / ".claude-plugin"
                    pdir.mkdir(parents=True)
                    (pdir / "plugin.json").write_text(
                        json.dumps(pj), encoding="utf-8"
                    )

    # marketplaces
    if marketplaces:
        for mkt_id, mkt_json in marketplaces.items():
            mdir = plugins_dir / "marketplaces" / mkt_id / ".claude-plugin"
            mdir.mkdir(parents=True)
            (mdir / "marketplace.json").write_text(
                json.dumps(mkt_json), encoding="utf-8"
            )

    # known_marketplaces.json
    if marketplaces:
        known = {}
        for mkt_id in marketplaces:
            known[mkt_id] = {
                "source": {"source": "github", "repo": f"org/{mkt_id}"},
                "installLocation": str(plugins_dir / "marketplaces" / mkt_id),
            }
        (plugins_dir / "known_marketplaces.json").write_text(
            json.dumps(known), encoding="utf-8"
        )

    return Path(tmp) / ".claude"


class TestScanPlugins:
    def test_empty_ecosystem(self):
        with tempfile.TemporaryDirectory() as tmp:
            claude_dir = _setup_ecosystem(tmp, installed={"version": 2, "plugins": {}})
            result = scan_plugins(home_dir=Path(tmp))
            assert result == []

    def test_single_plugin_no_deps(self):
        with tempfile.TemporaryDirectory() as tmp:
            pj = {"name": "core", "version": "1.0.0"}
            installed = {
                "version": 2,
                "plugins": {
                    "core@mkt": [{
                        "scope": "user",
                        "installPath": str(Path(tmp) / ".claude/plugins/cache/mkt/core/1.0.0"),
                        "version": "1.0.0",
                    }]
                },
            }
            mkt = {
                "plugins": [{"name": "core", "version": "1.0.0", "source": {"ref": "v1.0.0"}}]
            }
            _setup_ecosystem(
                tmp,
                installed=installed,
                cache={"mkt": {"core": {"1.0.0": pj}}},
                marketplaces={"mkt": mkt},
            )
            result = scan_plugins(home_dir=Path(tmp))
            assert len(result) == 1
            assert result[0].name == "core"
            assert result[0].installed_version == "1.0.0"
            assert result[0].available_version == "1.0.0"
            assert result[0].dependencies == {}

    def test_plugin_with_dependencies(self):
        with tempfile.TemporaryDirectory() as tmp:
            core_pj = {"name": "core", "version": "1.4.0"}
            eng_pj = {
                "name": "eng",
                "version": "1.0.0",
                "dependencies": {"core": ">=1.0.0"},
            }
            installed = {
                "version": 2,
                "plugins": {
                    "core@mkt": [{"scope": "user", "installPath": str(Path(tmp) / ".claude/plugins/cache/mkt/core/1.4.0"), "version": "1.4.0"}],
                    "eng@mkt": [{"scope": "user", "installPath": str(Path(tmp) / ".claude/plugins/cache/mkt/eng/1.0.0"), "version": "1.0.0"}],
                },
            }
            mkt = {"plugins": [
                {"name": "core", "version": "1.4.0", "source": {"ref": "v1.4.0"}},
                {"name": "eng", "version": "1.0.0", "source": {"ref": "v1.0.0"}},
            ]}
            _setup_ecosystem(
                tmp,
                installed=installed,
                cache={"mkt": {"core": {"1.4.0": core_pj}, "eng": {"1.0.0": eng_pj}}},
                marketplaces={"mkt": mkt},
            )
            result = scan_plugins(home_dir=Path(tmp))
            eng_state = next(p for p in result if p.name == "eng")
            assert eng_state.dependencies == {"core": ">=1.0.0"}

    def test_missing_installed_plugins_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / ".claude" / "plugins").mkdir(parents=True)
            result = scan_plugins(home_dir=Path(tmp))
            assert result == []

    def test_corrupt_plugin_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            installed = {
                "version": 2,
                "plugins": {
                    "bad@mkt": [{"scope": "user", "installPath": str(Path(tmp) / ".claude/plugins/cache/mkt/bad/1.0.0"), "version": "1.0.0"}]
                },
            }
            # Create corrupt plugin.json
            plugins_dir = Path(tmp) / ".claude" / "plugins"
            plugins_dir.mkdir(parents=True)
            (plugins_dir / "installed_plugins.json").write_text(json.dumps(installed))
            pdir = plugins_dir / "cache" / "mkt" / "bad" / "1.0.0" / ".claude-plugin"
            pdir.mkdir(parents=True)
            (pdir / "plugin.json").write_text("{corrupt json", encoding="utf-8")
            # known marketplaces
            (plugins_dir / "known_marketplaces.json").write_text("{}")
            result = scan_plugins(home_dir=Path(tmp))
            assert len(result) == 1
            assert result[0].installed_version == "unknown"
            assert result[0].dependencies == {}

    def test_dependencies_field_not_dict(self):
        with tempfile.TemporaryDirectory() as tmp:
            pj = {"name": "bad", "version": "1.0.0", "dependencies": "not-a-dict"}
            installed = {
                "version": 2,
                "plugins": {
                    "bad@mkt": [{"scope": "user", "installPath": str(Path(tmp) / ".claude/plugins/cache/mkt/bad/1.0.0"), "version": "1.0.0"}]
                },
            }
            _setup_ecosystem(
                tmp,
                installed=installed,
                cache={"mkt": {"bad": {"1.0.0": pj}}},
                marketplaces={"mkt": {"plugins": [{"name": "bad", "version": "1.0.0", "source": {"ref": "v1.0.0"}}]}},
            )
            result = scan_plugins(home_dir=Path(tmp))
            assert result[0].dependencies == {}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `~/.aida/venv/bin/pytest tests/unit/test_scanner.py -v`
Expected: FAIL

- [ ] **Step 3: Implement scanner.py**

```python
"""Plugin scanner — reads installed plugins, cache, and marketplaces.

Produces a unified list of PluginState objects describing the full
plugin ecosystem from the consumer's perspective.
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class PluginState:
    """Unified view of a plugin."""
    name: str
    installed_version: Optional[str] = None
    available_version: Optional[str] = None
    dependencies: Dict[str, str] = field(default_factory=dict)
    source: str = "unknown"
    install_path: Optional[str] = None
    marketplace_id: Optional[str] = None


def _read_json_safe(path: Path) -> Optional[dict]:
    """Read a JSON file, returning None on any error."""
    try:
        if not path.is_file():
            return None
        text = path.read_text(encoding="utf-8")
        if len(text) > 1_048_576:  # 1MB limit
            logger.warning("File too large, skipping: %s", path)
            return None
        return json.loads(text)
    except (json.JSONDecodeError, OSError, ValueError) as e:
        logger.warning("Failed to read %s: %s", path, e)
        return None


def _scan_marketplaces(
    plugins_dir: Path,
) -> Dict[str, Dict[str, str]]:
    """Read all marketplace manifests, return {plugin_name: {version, marketplace_id}}."""
    available: Dict[str, Dict[str, str]] = {}

    known_path = plugins_dir / "known_marketplaces.json"
    known = _read_json_safe(known_path)
    if not known or not isinstance(known, dict):
        return available

    for mkt_id in known:
        mkt_path = (
            plugins_dir / "marketplaces" / mkt_id
            / ".claude-plugin" / "marketplace.json"
        )
        mkt_data = _read_json_safe(mkt_path)
        if not mkt_data or not isinstance(mkt_data.get("plugins"), list):
            continue
        for plugin in mkt_data["plugins"]:
            name = plugin.get("name", "")
            version = plugin.get("version", "")
            if name and name not in available:
                available[name] = {
                    "version": version,
                    "marketplace_id": mkt_id,
                }

    return available


def scan_plugins(home_dir: Optional[Path] = None) -> List[PluginState]:
    """Scan the plugin ecosystem and return unified state.

    Args:
        home_dir: Override home directory (for testing).
                  Defaults to Path.home().

    Returns:
        List of PluginState objects for all discovered plugins.
    """
    if home_dir is None:
        home_dir = Path.home()

    plugins_dir = home_dir / ".claude" / "plugins"
    if not plugins_dir.is_dir():
        return []

    # Read installed plugins
    installed_path = plugins_dir / "installed_plugins.json"
    installed_data = _read_json_safe(installed_path)
    if not installed_data or not isinstance(installed_data.get("plugins"), dict):
        return []

    # Read marketplace availability
    available = _scan_marketplaces(plugins_dir)

    # Build plugin states
    states: List[PluginState] = []
    for plugin_key, entries in installed_data["plugins"].items():
        if not isinstance(entries, list) or not entries:
            continue

        entry = entries[0]  # Take first entry
        name = plugin_key.split("@")[0]
        version = entry.get("version")
        install_path = entry.get("installPath", "")
        marketplace_id = plugin_key.split("@")[1] if "@" in plugin_key else None

        # Read plugin.json from cache for dependencies
        dependencies: Dict[str, str] = {}
        if install_path:
            pj_path = Path(install_path) / ".claude-plugin" / "plugin.json"
            pj_data = _read_json_safe(pj_path)
            if pj_data:
                raw_deps = pj_data.get("dependencies", {})
                if isinstance(raw_deps, dict):
                    dependencies = raw_deps
                version = pj_data.get("version", version)
            else:
                version = "unknown"

        # Get marketplace version
        mkt_info = available.get(name, {})
        available_version = mkt_info.get("version")
        if not marketplace_id:
            marketplace_id = mkt_info.get("marketplace_id")

        source = "marketplace" if marketplace_id else "local"

        states.append(PluginState(
            name=name,
            installed_version=version,
            available_version=available_version,
            dependencies=dependencies,
            source=source,
            install_path=install_path,
            marketplace_id=marketplace_id,
        ))

    return sorted(states, key=lambda s: s.name)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `~/.aida/venv/bin/pytest tests/unit/test_scanner.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add skills/marketplace-sync/scripts/sync_ops/scanner.py \
       tests/unit/test_scanner.py
git commit -m "feat(marketplace-sync): add plugin scanner

Reads installed_plugins.json, plugin cache, and marketplace manifests
to produce a unified list of PluginState objects."
```

---

## Task 4: Report Generator

**Files:**

- Create: `skills/marketplace-sync/scripts/sync_ops/report.py`
- Create: `tests/unit/test_report.py`

- [ ] **Step 1: Write failing tests for report**

```python
"""Tests for marketplace-sync report generator."""

import sys
from pathlib import Path

import pytest

sys.path.insert(
    0,
    str(
        Path(__file__).parent.parent.parent
        / "skills"
        / "marketplace-sync"
        / "scripts"
    ),
)
sys.path.insert(
    0, str(Path(__file__).parent.parent.parent / "scripts")
)

from sync_ops.report import generate_report, generate_summary  # noqa: E402
from sync_ops.scanner import PluginState  # noqa: E402
from sync_ops.resolver import ResolutionResult, DependencyEdge  # noqa: E402


class TestGenerateReport:
    def test_empty_plugins(self):
        report = generate_report([], ResolutionResult())
        assert "0 plugins" in report["summary"]

    def test_all_up_to_date(self):
        plugins = [
            PluginState(name="core", installed_version="1.0.0", available_version="1.0.0"),
        ]
        result = ResolutionResult(
            graph={"core": []}, install_order=["core"]
        )
        report = generate_report(plugins, result)
        assert report["plugins"][0]["status"] == "up-to-date"
        assert "0 outdated" in report["summary"]

    def test_outdated_plugin(self):
        plugins = [
            PluginState(name="core", installed_version="1.0.0", available_version="2.0.0"),
        ]
        result = ResolutionResult(
            graph={"core": []}, install_order=["core"]
        )
        report = generate_report(plugins, result)
        assert report["plugins"][0]["status"] == "outdated"

    def test_ahead_plugin(self):
        plugins = [
            PluginState(name="core", installed_version="2.0.0", available_version="1.0.0"),
        ]
        result = ResolutionResult(
            graph={"core": []}, install_order=["core"]
        )
        report = generate_report(plugins, result)
        assert report["plugins"][0]["status"] == "ahead"

    def test_local_plugin(self):
        plugins = [
            PluginState(name="local-thing", installed_version="1.0.0", source="local"),
        ]
        result = ResolutionResult(
            graph={"local-thing": []}, install_order=["local-thing"]
        )
        report = generate_report(plugins, result)
        assert report["plugins"][0]["status"] == "local"

    def test_unsatisfied_dependency(self):
        plugins = [
            PluginState(name="core", installed_version="0.9.0", available_version="1.4.0"),
            PluginState(
                name="eng", installed_version="1.0.0", available_version="1.0.0",
                dependencies={"core": ">=1.0.0"},
            ),
        ]
        edge = DependencyEdge(
            dependent="eng", dependency="core",
            constraint=">=1.0.0", satisfied=False, installed="0.9.0",
        )
        result = ResolutionResult(
            graph={"core": [], "eng": [edge]},
            install_order=["core", "eng"],
        )
        report = generate_report(plugins, result)
        assert len(report["dependency_issues"]) == 1
        assert report["dependency_issues"][0]["dependent"] == "eng"

    def test_unknown_version(self):
        plugins = [
            PluginState(name="official", installed_version="unknown"),
        ]
        result = ResolutionResult(
            graph={"official": []}, install_order=["official"]
        )
        report = generate_report(plugins, result)
        assert report["plugins"][0]["status"] == "unknown"


class TestGenerateSummary:
    def test_summary_counts(self):
        plugins = [
            PluginState(name="a", installed_version="1.0.0", available_version="2.0.0"),
            PluginState(name="b", installed_version="1.0.0", available_version="1.0.0"),
        ]
        result = ResolutionResult(
            graph={"a": [], "b": []}, install_order=["a", "b"]
        )
        summary = generate_summary(plugins, result)
        assert summary["total"] == 2
        assert summary["outdated"] == 1
        assert summary["up_to_date"] == 1
```

- [ ] **Step 2: Run tests, verify fail**

Run: `~/.aida/venv/bin/pytest tests/unit/test_report.py -v`
Expected: FAIL

- [ ] **Step 3: Implement report.py**

```python
"""Report generator for marketplace sync.

Produces structured report data from scan results and dependency
resolution, including plugin status table, dependency issues,
and summary counts.
"""

from typing import Any, Dict, List, Optional

from sync_ops.scanner import PluginState
from sync_ops.resolver import ResolutionResult

try:
    from packaging.version import Version
except ImportError:
    Version = None  # type: ignore[assignment, misc]


def _compare_versions(installed: str, available: str) -> str:
    """Compare two version strings, return status."""
    if not installed or installed == "unknown":
        return "unknown"
    if not available:
        return "local"
    try:
        iv = Version(installed)
        av = Version(available)
        if iv == av:
            return "up-to-date"
        elif iv < av:
            return "outdated"
        else:
            return "ahead"
    except Exception:
        return "unknown"


def generate_report(
    plugins: List[PluginState],
    resolution: ResolutionResult,
) -> Dict[str, Any]:
    """Generate a structured sync report.

    Args:
        plugins: List of PluginState from scanner
        resolution: ResolutionResult from resolver

    Returns:
        Dict with keys: plugins, dependency_issues, cycles,
        unresolved, warnings, summary
    """
    plugin_rows = []
    for p in plugins:
        if p.source == "local":
            status = "local"
        else:
            status = _compare_versions(
                p.installed_version or "", p.available_version or ""
            )
        plugin_rows.append({
            "name": p.name,
            "installed": p.installed_version or "-",
            "available": p.available_version or "-",
            "status": status,
            "marketplace": p.marketplace_id or "-",
        })

    # Collect dependency issues
    dep_issues = []
    for name, edges in resolution.graph.items():
        for edge in edges:
            if not edge.satisfied:
                dep_issues.append({
                    "dependent": edge.dependent,
                    "dependency": edge.dependency,
                    "constraint": edge.constraint,
                    "installed": edge.installed or "-",
                })

    # Summary
    outdated = sum(1 for r in plugin_rows if r["status"] == "outdated")
    up_to_date = sum(1 for r in plugin_rows if r["status"] == "up-to-date")
    summary = (
        f"{len(plugins)} plugins, {outdated} outdated, "
        f"{len(dep_issues)} dependency issues"
    )

    return {
        "plugins": plugin_rows,
        "dependency_issues": dep_issues,
        "cycles": resolution.cycles,
        "unresolved": resolution.unresolved,
        "warnings": resolution.warnings,
        "summary": summary,
    }


def generate_summary(
    plugins: List[PluginState],
    resolution: ResolutionResult,
) -> Dict[str, int]:
    """Generate quick summary counts.

    Returns:
        Dict with total, outdated, up_to_date, missing, local counts
    """
    report = generate_report(plugins, resolution)
    rows = report["plugins"]
    return {
        "total": len(rows),
        "outdated": sum(1 for r in rows if r["status"] == "outdated"),
        "up_to_date": sum(1 for r in rows if r["status"] == "up-to-date"),
        "ahead": sum(1 for r in rows if r["status"] == "ahead"),
        "local": sum(1 for r in rows if r["status"] == "local"),
        "unknown": sum(1 for r in rows if r["status"] == "unknown"),
        "dependency_issues": len(report["dependency_issues"]),
    }
```

- [ ] **Step 4: Run tests, verify pass**

Run: `~/.aida/venv/bin/pytest tests/unit/test_report.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add skills/marketplace-sync/scripts/sync_ops/report.py \
       tests/unit/test_report.py
git commit -m "feat(marketplace-sync): add report generator

Produces structured report data with plugin status table, dependency
issues, and summary counts."
```

---

## Task 5: Entry Point, SKILL.md, and Wiring

**Files:**

- Create: `skills/marketplace-sync/scripts/_paths.py`
- Create: `skills/marketplace-sync/scripts/manage.py`
- Create: `skills/marketplace-sync/SKILL.md`
- Create: `skills/marketplace-sync/references/schemas.md`
- Modify: `.claude-plugin/aida-config.json` — add to skills array

- [ ] **Step 1: Create _paths.py**

```python
"""Path setup for marketplace-sync scripts."""

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
PLUGIN_DIR = SKILL_DIR.parent.parent

# Add shared scripts to path
sys.path.insert(0, str(PLUGIN_DIR / "scripts"))

# Add aida skill utils to path
AIDA_SCRIPTS_DIR = PLUGIN_DIR / "skills" / "aida" / "scripts"
sys.path.insert(0, str(AIDA_SCRIPTS_DIR))
```

- [ ] **Step 2: Create manage.py**

```python
#!/usr/bin/env python3
"""Marketplace Sync Script - Two-Phase API

Entry point for marketplace dependency resolution and version drift
detection. Supports sync (report), sync --apply (update), and status.

Usage:
    python manage.py --get-questions \
        --context='{"operation": "sync"}'
    python manage.py --execute \
        --context='{"operation": "sync", "apply": true}'

Exit codes:
    0   - Success
    1   - Error occurred
"""

import argparse
import json
import sys

import _paths  # noqa: F401

from shared.utils import safe_json_load  # noqa: E402

from sync_ops.scanner import scan_plugins  # noqa: E402
from sync_ops.resolver import resolve_dependencies  # noqa: E402
from sync_ops.report import generate_report, generate_summary  # noqa: E402


def _scan_and_resolve():
    """Run scan + resolve pipeline, return (plugins, resolution)."""
    plugins = scan_plugins()
    plugin_tuples = [
        (p.name, p.installed_version, p.dependencies)
        for p in plugins
    ]
    resolution = resolve_dependencies(plugin_tuples)
    return plugins, resolution


def get_questions(context: dict) -> dict:
    """Phase 1: Scan and return report or questions."""
    operation = context.get("operation", "sync")

    if operation == "status":
        plugins, resolution = _scan_and_resolve()
        summary = generate_summary(plugins, resolution)
        return {"questions": [], "summary": summary, "success": True}

    if operation == "sync":
        apply_mode = context.get("apply", False)
        plugins, resolution = _scan_and_resolve()
        report = generate_report(plugins, resolution)

        if apply_mode:
            outdated = [
                p for p in report["plugins"] if p["status"] == "outdated"
            ]
            if not outdated:
                return {
                    "questions": [],
                    "report": report,
                    "success": True,
                    "message": "All plugins are up to date.",
                }
            return {
                "questions": [{
                    "id": "confirm",
                    "question": (
                        f"Update {len(outdated)} outdated plugin(s)?"
                    ),
                    "type": "boolean",
                    "required": True,
                }],
                "report": report,
                "success": True,
            }

        return {"questions": [], "report": report, "success": True}

    return {"questions": [], "success": False, "message": f"Unknown operation: {operation}"}


def execute(context: dict, responses: dict) -> dict:
    """Phase 2: Execute operation."""
    operation = context.get("operation", "sync")

    if operation in ("sync", "status"):
        apply_mode = context.get("apply", False)
        if not apply_mode:
            # Report-only: just return the scan results
            plugins, resolution = _scan_and_resolve()
            report = generate_report(plugins, resolution)
            return {"success": True, "report": report}

        confirmed = responses.get("confirm", False)
        if not confirmed:
            return {"success": True, "message": "Update cancelled."}

        # TODO: implement updater in future task
        return {
            "success": True,
            "message": "Update capability not yet implemented. Use /plugin install to update manually.",
        }

    return {"success": False, "message": f"Unknown operation: {operation}"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Marketplace Sync")
    parser.add_argument("--get-questions", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--context", type=str, default="{}")
    parser.add_argument("--responses", type=str, default="{}")

    args = parser.parse_args()

    try:
        context = safe_json_load(args.context) if args.context else {}
        responses = safe_json_load(args.responses) if args.responses else {}

        if args.get_questions:
            result = get_questions(context)
        elif args.execute:
            result = execute(context, responses)
        else:
            parser.print_help()
            return 1

        print(json.dumps(result, indent=2))
        return 0 if result.get("success") else 1

    except Exception as e:
        print(json.dumps({"success": False, "message": str(e)}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 3: Create SKILL.md**

Write the full SKILL.md with frontmatter and activation/usage docs
following the pattern from expert-registry/SKILL.md.

- [ ] **Step 4: Create references/schemas.md**

Document the `plugin.json` dependencies schema, PluginState, and
ResolutionResult data model.

- [ ] **Step 5: Register skill in aida-config.json**

Add `"marketplace-sync"` to the `skills` array in
`.claude-plugin/aida-config.json`.

- [ ] **Step 6: Run full test suite**

Run: `~/.aida/venv/bin/pytest tests/ -v`
Expected: All existing + new tests PASS

- [ ] **Step 7: Commit**

```bash
git add skills/marketplace-sync/ .claude-plugin/aida-config.json
git commit -m "feat(marketplace-sync): add skill entry point and SKILL.md

Two-phase API with sync (report), sync --apply (update), and status
operations. Registered in aida-config.json."
```

---

## Task 6: Integration Tests

**Files:**

- Create: `tests/integration/test_marketplace_sync_integration.py`

- [ ] **Step 1: Write integration tests**

```python
"""Integration tests for marketplace-sync full pipeline."""

import json
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(
    0,
    str(
        Path(__file__).parent.parent.parent
        / "skills"
        / "marketplace-sync"
        / "scripts"
    ),
)
sys.path.insert(
    0, str(Path(__file__).parent.parent.parent / "scripts")
)

from sync_ops.scanner import scan_plugins  # noqa: E402
from sync_ops.resolver import resolve_dependencies  # noqa: E402
from sync_ops.report import generate_report, generate_summary  # noqa: E402


def _build_ecosystem(tmp, plugins_config):
    """Build a full mock ecosystem.

    plugins_config: list of dicts with keys:
        name, version, deps (dict), available_version, marketplace
    """
    plugins_dir = Path(tmp) / ".claude" / "plugins"
    plugins_dir.mkdir(parents=True)

    installed_plugins = {"version": 2, "plugins": {}}
    marketplace_plugins = []

    for p in plugins_config:
        name = p["name"]
        version = p["version"]
        mkt = p.get("marketplace", "test-mkt")
        deps = p.get("deps", {})
        avail = p.get("available_version", version)
        key = f"{name}@{mkt}"
        install_path = str(
            plugins_dir / "cache" / mkt / name / version
        )

        installed_plugins["plugins"][key] = [{
            "scope": "user",
            "installPath": install_path,
            "version": version,
        }]

        # Write plugin.json to cache
        pj = {"name": name, "version": version}
        if deps:
            pj["dependencies"] = deps
        pdir = Path(install_path) / ".claude-plugin"
        pdir.mkdir(parents=True)
        (pdir / "plugin.json").write_text(
            json.dumps(pj), encoding="utf-8"
        )

        marketplace_plugins.append({
            "name": name,
            "version": avail,
            "source": {"ref": f"v{avail}"},
        })

    (plugins_dir / "installed_plugins.json").write_text(
        json.dumps(installed_plugins), encoding="utf-8"
    )

    mkt_dir = plugins_dir / "marketplaces" / "test-mkt" / ".claude-plugin"
    mkt_dir.mkdir(parents=True)
    (mkt_dir / "marketplace.json").write_text(
        json.dumps({"plugins": marketplace_plugins}), encoding="utf-8"
    )
    (plugins_dir / "known_marketplaces.json").write_text(
        json.dumps({"test-mkt": {
            "source": {"source": "github", "repo": "org/test-mkt"},
            "installLocation": str(plugins_dir / "marketplaces" / "test-mkt"),
        }}), encoding="utf-8"
    )

    return Path(tmp)


class TestFullPipeline:
    def test_all_up_to_date(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = _build_ecosystem(tmp, [
                {"name": "core", "version": "1.0.0"},
                {"name": "eng", "version": "1.0.0", "deps": {"core": ">=1.0.0"}},
            ])
            plugins = scan_plugins(home_dir=home)
            tuples = [(p.name, p.installed_version, p.dependencies) for p in plugins]
            resolution = resolve_dependencies(tuples)
            report = generate_report(plugins, resolution)
            assert all(p["status"] == "up-to-date" for p in report["plugins"])

    def test_outdated_with_unsatisfied_dep(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = _build_ecosystem(tmp, [
                {"name": "core", "version": "1.0.0", "available_version": "2.0.0"},
                {"name": "eng", "version": "1.0.0", "deps": {"core": ">=2.0.0"}},
            ])
            plugins = scan_plugins(home_dir=home)
            tuples = [(p.name, p.installed_version, p.dependencies) for p in plugins]
            resolution = resolve_dependencies(tuples)
            report = generate_report(plugins, resolution)
            core_row = next(r for r in report["plugins"] if r["name"] == "core")
            assert core_row["status"] == "outdated"
            assert len(report["dependency_issues"]) == 1

    def test_transitive_three_levels(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = _build_ecosystem(tmp, [
                {"name": "base", "version": "1.0.0"},
                {"name": "mid", "version": "1.0.0", "deps": {"base": ">=1.0.0"}},
                {"name": "top", "version": "1.0.0", "deps": {"mid": ">=1.0.0"}},
            ])
            plugins = scan_plugins(home_dir=home)
            tuples = [(p.name, p.installed_version, p.dependencies) for p in plugins]
            resolution = resolve_dependencies(tuples)
            order = resolution.install_order
            assert order.index("base") < order.index("mid") < order.index("top")

    def test_mixed_deps_and_no_deps(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = _build_ecosystem(tmp, [
                {"name": "core", "version": "1.0.0"},
                {"name": "standalone", "version": "1.0.0"},
                {"name": "eng", "version": "1.0.0", "deps": {"core": ">=1.0.0"}},
            ])
            plugins = scan_plugins(home_dir=home)
            tuples = [(p.name, p.installed_version, p.dependencies) for p in plugins]
            resolution = resolve_dependencies(tuples)
            assert len(resolution.install_order) == 3
            summary = generate_summary(plugins, resolution)
            assert summary["total"] == 3
            assert summary["up_to_date"] == 3
```

- [ ] **Step 2: Run integration tests**

Run: `~/.aida/venv/bin/pytest tests/integration/test_marketplace_sync_integration.py -v`
Expected: All PASS

- [ ] **Step 3: Run full suite**

Run: `~/.aida/venv/bin/pytest tests/ -v`
Expected: All PASS (existing + new)

- [ ] **Step 4: Commit**

```bash
git add tests/integration/test_marketplace_sync_integration.py
git commit -m "test(marketplace-sync): add integration tests

Full pipeline tests covering transitive deps, mixed ecosystems,
outdated plugins, and unsatisfied dependencies."
```

---

## Task 7: AIDA Routing and Plugin Registration

**Files:**

- Modify: `skills/aida/SKILL.md` — add marketplace command routing
- Modify: `.claude-plugin/plugin.json` — bump version
- Modify: `CHANGELOG.md` — add entry

- [ ] **Step 1: Add marketplace routing to AIDA SKILL.md**

Add after the Expert Registry routing section:

```markdown
### Marketplace Commands

For `marketplace` commands:

- **Invoke the `marketplace-sync` skill** to handle these operations
- Pass the full command arguments to the skill
- The skill handles sync (report), sync --apply (update), and status

**Process:**

1. Parse the command to extract:
   - Operation: `sync`, `status`
   - Flags: `--apply`, `--offline`

2. Invoke `marketplace-sync` skill with the parsed context

**Examples:**

\`\`\`text
/aida marketplace sync            -> marketplace-sync skill
/aida marketplace sync --apply    -> marketplace-sync skill
/aida marketplace status          -> marketplace-sync skill
\`\`\`
```

- [ ] **Step 2: Add to help text in AIDA SKILL.md**

Add under Extension Management in the help block:

```markdown
### Marketplace
- `/aida marketplace sync` - Report plugin versions and dependency status
- `/aida marketplace sync --apply` - Update outdated plugins
- `/aida marketplace status` - Quick summary of plugin drift
```

- [ ] **Step 3: Bump version in plugin.json**

Update version from `1.4.0` to `1.5.0` in
`.claude-plugin/plugin.json`.

- [ ] **Step 4: Add CHANGELOG entry**

Add `## [1.5.0]` entry to `CHANGELOG.md` with marketplace-sync
feature description.

- [ ] **Step 5: Run linters**

Run: `make lint`
Expected: Clean

- [ ] **Step 6: Run full test suite**

Run: `make test`
Expected: All PASS

- [ ] **Step 7: Commit**

```bash
git add skills/aida/SKILL.md .claude-plugin/plugin.json CHANGELOG.md
git commit -m "feat(marketplace-sync): add AIDA routing and bump to v1.5.0

Wire /aida marketplace commands into AIDA dispatcher. Add help text
and changelog entry."
```
