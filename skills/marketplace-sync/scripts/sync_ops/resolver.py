"""Dependency graph resolver with topological sort and cycle detection."""

from __future__ import annotations

import re
import sys
from collections import defaultdict, deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Allow importing shared.version from the top-level scripts/ directory
sys.path.insert(
    0,
    str(Path(__file__).parent.parent.parent.parent.parent / "scripts"),
)
from shared.version import satisfies  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_DEPENDENCY_DEPTH = 20
MAX_TOTAL_PLUGINS = 200
MAX_DEPS_PER_PLUGIN = 50
DEP_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9-]{0,49}$")

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class DependencyEdge:
    """A single dependency relationship between two plugins."""

    dependent: str  # plugin that requires
    dependency: str  # plugin that is required
    constraint: str  # raw constraint string
    satisfied: bool  # is installed version in range?
    installed: Optional[str]  # installed version of dependency


@dataclass
class ResolutionResult:
    """Full resolution output produced by :func:`build_graph`."""

    graph: Dict[str, List[DependencyEdge]] = field(default_factory=dict)
    install_order: List[str] = field(default_factory=list)
    cycles: List[List[str]] = field(default_factory=list)
    conflicts: List[Tuple[str, str, str]] = field(default_factory=list)
    unresolved: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_graph(
    plugins: List[Tuple[str, Optional[str], Dict[str, str]]],
) -> ResolutionResult:
    """Build a dependency graph and resolve install order.

    Parameters
    ----------
    plugins:
        List of ``(name, installed_version, dependencies)`` tuples where
        *dependencies* maps dependency plugin names to version constraint
        strings.

    Returns
    -------
    ResolutionResult
        Populated resolution result including topological install order,
        detected cycles, unresolved dependencies, conflicts, and warnings.
    """
    result = ResolutionResult()

    if len(plugins) > MAX_TOTAL_PLUGINS:
        result.warnings.append(
            f"Plugin count ({len(plugins)}) exceeds maximum"
            f" ({MAX_TOTAL_PLUGINS})"
        )

    # Index of known plugin names -> installed version
    known: Dict[str, Optional[str]] = {}
    for name, version, _deps in plugins:
        known[name] = version

    # Build adjacency list and in-degree map (for Kahn's algorithm)
    in_degree: Dict[str, int] = defaultdict(int)
    adjacency: Dict[str, List[str]] = defaultdict(list)

    # Ensure every plugin appears in the maps
    for name, _version, _deps in plugins:
        in_degree.setdefault(name, 0)

    for name, _version, deps in plugins:
        if len(deps) > MAX_DEPS_PER_PLUGIN:
            result.warnings.append(
                f"Plugin '{name}' has {len(deps)} dependencies,"
                f" exceeding maximum ({MAX_DEPS_PER_PLUGIN})"
            )

        for dep_name, constraint in deps.items():
            # Validate dependency name
            if not DEP_NAME_PATTERN.match(dep_name):
                result.warnings.append(
                    f"Skipping invalid dependency name '{dep_name}'"
                    f" in plugin '{name}'"
                )
                continue

            # Check if the dependency is a known plugin
            if dep_name not in known:
                result.unresolved.append(dep_name)
                edge = DependencyEdge(
                    dependent=name,
                    dependency=dep_name,
                    constraint=constraint,
                    satisfied=False,
                    installed=None,
                )
                result.graph.setdefault(name, []).append(edge)
                continue

            dep_version = known[dep_name]
            is_satisfied = (
                satisfies(dep_version, constraint)
                if dep_version is not None
                else False
            )

            edge = DependencyEdge(
                dependent=name,
                dependency=dep_name,
                constraint=constraint,
                satisfied=is_satisfied,
                installed=dep_version,
            )
            result.graph.setdefault(name, []).append(edge)

            # Record the edge for topological sort.
            # dep_name -> name means "dep_name must be installed before name".
            adjacency[dep_name].append(name)
            in_degree[name] = in_degree.get(name, 0) + 1

    # ------------------------------------------------------------------
    # Conflict detection: find deps with mutually incompatible constraints
    # ------------------------------------------------------------------
    dep_constraints: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
    for name, _version, deps in plugins:
        for dep_name, constraint in deps.items():
            if dep_name in known and DEP_NAME_PATTERN.match(dep_name):
                dep_constraints[dep_name].append((name, constraint))
    for dep_name, requestors in dep_constraints.items():
        if len(requestors) < 2:
            continue
        dep_version = known.get(dep_name)
        if dep_version is None:
            continue
        satisfied_by = [
            (req, c)
            for req, c in requestors
            if satisfies(dep_version, c)
        ]
        unsatisfied_by = [
            (req, c)
            for req, c in requestors
            if not satisfies(dep_version, c)
        ]
        if satisfied_by and unsatisfied_by:
            for req, c in unsatisfied_by:
                result.conflicts.append((dep_name, req, c))

    # ------------------------------------------------------------------
    # Depth enforcement — check for chains exceeding MAX_DEPENDENCY_DEPTH
    # ------------------------------------------------------------------
    for name in known:
        depth = 0
        current = name
        seen: set[str] = set()
        while True:
            deps_of_current = [
                e.dependency
                for e in result.graph.get(current, [])
                if e.dependency in known
            ]
            if not deps_of_current or current in seen:
                break
            seen.add(current)
            current = deps_of_current[0]
            depth += 1
            if depth > MAX_DEPENDENCY_DEPTH:
                result.warnings.append(
                    f"Dependency chain from '{name}' exceeds"
                    f" max depth ({MAX_DEPENDENCY_DEPTH})"
                )
                break

    # ------------------------------------------------------------------
    # Kahn's algorithm for topological sort
    # ------------------------------------------------------------------
    queue: deque[str] = deque()
    for node in in_degree:
        if in_degree[node] == 0:
            queue.append(node)

    order: List[str] = []
    while queue:
        node = queue.popleft()
        order.append(node)
        for neighbour in adjacency.get(node, []):
            in_degree[neighbour] -= 1
            if in_degree[neighbour] == 0:
                queue.append(neighbour)

    # ------------------------------------------------------------------
    # Cycle detection — nodes remaining with in-degree > 0
    # ------------------------------------------------------------------
    remaining = {n for n in in_degree if in_degree[n] > 0}
    if remaining:
        # Extract individual cycles from the remaining subgraph
        visited: set[str] = set()
        for start in remaining:
            if start in visited:
                continue
            cycle: List[str] = []
            current: Optional[str] = start
            path_set: set[str] = set()
            while current and current not in path_set:
                path_set.add(current)
                cycle.append(current)
                # Follow first remaining neighbour
                nexts = [
                    n
                    for n in adjacency.get(current, [])
                    if n in remaining
                ]
                current = nexts[0] if nexts else None
            if current and current in path_set:
                idx = cycle.index(current)
                cycle = cycle[idx:]
            result.cycles.append(cycle)
            visited.update(cycle)

    result.install_order = order
    return result


def resolve_dependencies(
    plugins: List[Tuple[str, Optional[str], Dict[str, str]]],
) -> ResolutionResult:
    """Convenience wrapper around :func:`build_graph`."""
    return build_graph(plugins)
