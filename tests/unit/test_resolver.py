"""Tests for the marketplace-sync dependency graph resolver."""

from __future__ import annotations

import sys
from pathlib import Path

# Path setup so we can import sync_ops and shared modules
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
    0,
    str(Path(__file__).parent.parent.parent / "scripts"),
)

from sync_ops.resolver import (  # noqa: E402
    DependencyEdge,
    ResolutionResult,
    build_graph,
    resolve_dependencies,
)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _plugin(
    name: str,
    version: str | None = "1.0.0",
    deps: dict[str, str] | None = None,
) -> tuple[str, str | None, dict[str, str]]:
    """Shorthand for creating a plugin tuple."""
    return (name, version, deps or {})


# ------------------------------------------------------------------
# Basic / edge-case tests
# ------------------------------------------------------------------


class TestEmptyAndSingle:
    """Empty input and single-plugin scenarios."""

    def test_empty_plugins_list(self) -> None:
        result = build_graph([])
        assert result.install_order == []
        assert result.cycles == []
        assert result.conflicts == []
        assert result.unresolved == []
        assert result.warnings == []

    def test_single_plugin_no_deps(self) -> None:
        result = build_graph([_plugin("alpha")])
        assert result.install_order == ["alpha"]
        assert result.cycles == []
        assert result.conflicts == []
        assert result.unresolved == []

    def test_resolve_dependencies_wrapper(self) -> None:
        """resolve_dependencies delegates to build_graph."""
        result = resolve_dependencies([_plugin("beta")])
        assert isinstance(result, ResolutionResult)
        assert result.install_order == ["beta"]


# ------------------------------------------------------------------
# Simple dependency scenarios
# ------------------------------------------------------------------


class TestSimpleDependency:
    """A depends on B."""

    def test_satisfied_dependency(self) -> None:
        plugins = [
            _plugin("a", "1.0.0", {"b": ">=1.0.0"}),
            _plugin("b", "1.2.0"),
        ]
        result = build_graph(plugins)
        # b must come before a
        assert result.install_order.index("b") < result.install_order.index("a")
        assert result.cycles == []
        assert result.unresolved == []

        # Check edge exists
        edges = result.graph.get("a", [])
        assert len(edges) == 1
        edge = edges[0]
        assert edge.dependent == "a"
        assert edge.dependency == "b"
        assert edge.constraint == ">=1.0.0"
        assert edge.satisfied is True
        assert edge.installed == "1.2.0"

    def test_unsatisfied_dependency_no_version(self) -> None:
        """Dependency installed but version is None -> unsatisfied."""
        plugins = [
            _plugin("a", "1.0.0", {"b": ">=1.0.0"}),
            _plugin("b", None),
        ]
        result = build_graph(plugins)
        edges = result.graph.get("a", [])
        assert len(edges) == 1
        assert edges[0].satisfied is False
        assert ("a", "b", ">=1.0.0") in result.conflicts


# ------------------------------------------------------------------
# Diamond dependency
# ------------------------------------------------------------------


class TestDiamondDependency:
    """A->B, A->C, B->D, C->D — classic diamond."""

    def test_diamond_order(self) -> None:
        plugins = [
            _plugin("a", "1.0.0", {"b": ">=1.0.0", "c": ">=1.0.0"}),
            _plugin("b", "1.0.0", {"d": ">=1.0.0"}),
            _plugin("c", "1.0.0", {"d": ">=1.0.0"}),
            _plugin("d", "1.0.0"),
        ]
        result = build_graph(plugins)
        order = result.install_order
        assert len(order) == 4
        # d before b and c; b and c before a
        assert order.index("d") < order.index("b")
        assert order.index("d") < order.index("c")
        assert order.index("b") < order.index("a")
        assert order.index("c") < order.index("a")
        assert result.cycles == []


# ------------------------------------------------------------------
# Cycle detection
# ------------------------------------------------------------------


class TestCycleDetection:
    """Cycles of various lengths."""

    def test_cycle_length_2(self) -> None:
        plugins = [
            _plugin("x", "1.0.0", {"y": ">=1.0.0"}),
            _plugin("y", "1.0.0", {"x": ">=1.0.0"}),
        ]
        result = build_graph(plugins)
        assert len(result.cycles) > 0
        # Both nodes must appear across the detected cycles
        cycle_nodes = {n for cycle in result.cycles for n in cycle}
        assert "x" in cycle_nodes
        assert "y" in cycle_nodes
        # Nodes in cycle should NOT be in install_order
        assert "x" not in result.install_order
        assert "y" not in result.install_order

    def test_cycle_length_3(self) -> None:
        plugins = [
            _plugin("a", "1.0.0", {"b": ">=1.0.0"}),
            _plugin("b", "1.0.0", {"c": ">=1.0.0"}),
            _plugin("c", "1.0.0", {"a": ">=1.0.0"}),
        ]
        result = build_graph(plugins)
        assert len(result.cycles) > 0
        cycle_nodes = {n for cycle in result.cycles for n in cycle}
        assert {"a", "b", "c"} == cycle_nodes

    def test_self_dependency(self) -> None:
        plugins = [
            _plugin("self-ref", "1.0.0", {"self-ref": ">=1.0.0"}),
        ]
        result = build_graph(plugins)
        assert len(result.cycles) > 0
        cycle_nodes = {n for cycle in result.cycles for n in cycle}
        assert "self-ref" in cycle_nodes


# ------------------------------------------------------------------
# Unresolved dependencies
# ------------------------------------------------------------------


class TestUnresolved:
    """Dependencies not present in the plugin list."""

    def test_missing_dependency(self) -> None:
        plugins = [
            _plugin("app", "1.0.0", {"missing-lib": ">=2.0.0"}),
        ]
        result = build_graph(plugins)
        assert "missing-lib" in result.unresolved
        # app itself can still be in install order (it has no in-graph deps)
        assert "app" in result.install_order

        # Edge should still be recorded
        edges = result.graph.get("app", [])
        assert len(edges) == 1
        assert edges[0].dependency == "missing-lib"
        assert edges[0].satisfied is False
        assert edges[0].installed is None


# ------------------------------------------------------------------
# Transitive chain
# ------------------------------------------------------------------


class TestTransitiveChain:
    """Three-level chain: a -> b -> c."""

    def test_three_level_order(self) -> None:
        plugins = [
            _plugin("a", "1.0.0", {"b": ">=1.0.0"}),
            _plugin("b", "1.0.0", {"c": ">=1.0.0"}),
            _plugin("c", "1.0.0"),
        ]
        result = build_graph(plugins)
        order = result.install_order
        assert order.index("c") < order.index("b") < order.index("a")
        assert result.cycles == []


# ------------------------------------------------------------------
# Conflict detection
# ------------------------------------------------------------------


class TestConflictDetection:
    """Version constraint not satisfied should be a conflict."""

    def test_conflict_when_version_none(self) -> None:
        """A depends on B >=2.0.0 but B has no version -> conflict."""
        plugins = [
            _plugin("a", "1.0.0", {"b": ">=2.0.0"}),
            _plugin("b", None),
        ]
        result = build_graph(plugins)
        assert len(result.conflicts) == 1
        assert result.conflicts[0] == ("a", "b", ">=2.0.0")


# ------------------------------------------------------------------
# Validation / warnings
# ------------------------------------------------------------------


class TestValidation:
    """Name validation and limit warnings."""

    def test_invalid_dep_name_skipped_with_warning(self) -> None:
        plugins = [
            _plugin("good", "1.0.0", {"INVALID_NAME": ">=1.0.0"}),
        ]
        result = build_graph(plugins)
        assert len(result.warnings) == 1
        assert "INVALID_NAME" in result.warnings[0]
        # No edge should be recorded for the invalid dep
        edges = result.graph.get("good", [])
        assert len(edges) == 0

    def test_dep_name_with_uppercase_rejected(self) -> None:
        plugins = [
            _plugin("host", "1.0.0", {"BadName": ">=1.0.0"}),
        ]
        result = build_graph(plugins)
        assert any("BadName" in w for w in result.warnings)

    def test_dep_name_starting_with_digit_rejected(self) -> None:
        plugins = [
            _plugin("host", "1.0.0", {"9invalid": ">=1.0.0"}),
        ]
        result = build_graph(plugins)
        assert any("9invalid" in w for w in result.warnings)

    def test_valid_dep_name_accepted(self) -> None:
        plugins = [
            _plugin("host", "1.0.0", {"valid-dep-name": ">=1.0.0"}),
            _plugin("valid-dep-name", "1.0.0"),
        ]
        result = build_graph(plugins)
        assert result.warnings == []

    def test_too_many_deps_warning(self) -> None:
        deps = {f"dep-{i}": ">=1.0.0" for i in range(51)}
        plugins_list = [_plugin("big", "1.0.0", deps)]
        # Add all the dep plugins so they are known
        for i in range(51):
            plugins_list.append(_plugin(f"dep-{i}", "1.0.0"))
        result = build_graph(plugins_list)
        assert any("exceeding maximum" in w for w in result.warnings)

    def test_too_many_plugins_warning(self) -> None:
        plugins_list = [_plugin(f"p-{i}") for i in range(201)]
        result = build_graph(plugins_list)
        assert any("Plugin count" in w for w in result.warnings)


# ------------------------------------------------------------------
# Mixed scenarios
# ------------------------------------------------------------------


class TestMixedScenarios:
    """Combinations of valid deps, cycles, and unresolved."""

    def test_partial_cycle_with_independent(self) -> None:
        """Some plugins in a cycle, one independent."""
        plugins = [
            _plugin("independent", "1.0.0"),
            _plugin("cycler-a", "1.0.0", {"cycler-b": ">=1.0.0"}),
            _plugin("cycler-b", "1.0.0", {"cycler-a": ">=1.0.0"}),
        ]
        result = build_graph(plugins)
        # independent should be in install order
        assert "independent" in result.install_order
        # cyclers should be in cycles
        cycle_nodes = {n for cycle in result.cycles for n in cycle}
        assert "cycler-a" in cycle_nodes
        assert "cycler-b" in cycle_nodes

    def test_multiple_roots(self) -> None:
        """Two independent plugins with no deps."""
        plugins = [
            _plugin("root-a", "1.0.0"),
            _plugin("root-b", "1.0.0"),
        ]
        result = build_graph(plugins)
        assert set(result.install_order) == {"root-a", "root-b"}
        assert result.cycles == []
