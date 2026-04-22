"""Integration test: scan_plugins -> resolve_dependencies -> generate_report/summary.

Exercises the full pipeline with a mock plugin ecosystem on disk to verify
that the scanner, resolver, and report modules work together correctly.
"""

import json
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add marketplace-sync scripts and top-level scripts to path
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

from sync_ops.report import generate_report, generate_summary  # noqa: E402
from sync_ops.resolver import (  # noqa: E402
    DependencyEdge,
    ResolutionResult,
    build_graph,
    resolve_dependencies,
)
from sync_ops.scanner import PluginState, scan_plugins  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_ecosystem(
    tmp_dir: str,
    plugin_configs: List[Dict[str, Any]],
    marketplace_id: str = "test-marketplace",
) -> Path:
    """Build a mock plugin ecosystem on disk.

    Each plugin config dict supports:
        name (str): Plugin name.
        installed_version (str|None): Version installed on disk.
        available_version (str|None): Version in marketplace catalogue.
        dependencies (dict): Mapping of dep name -> constraint string.
        source (str): "marketplace" or "local", defaults to "marketplace".

    Returns the home_dir Path to pass to scan_plugins().
    """
    home_dir = Path(tmp_dir) / "home"
    plugins_dir = home_dir / ".claude" / "plugins"
    marketplaces_dir = plugins_dir / "marketplaces"

    # ---- installed_plugins.json ----
    installed_entries: Dict[str, list] = {}
    marketplace_manifest_plugins: List[Dict[str, str]] = []

    for cfg in plugin_configs:
        name = cfg["name"]
        installed_version = cfg.get("installed_version")
        available_version = cfg.get("available_version")
        dependencies = cfg.get("dependencies", {})
        source = cfg.get("source", "marketplace")

        # Add to marketplace manifest if it has an available version
        if available_version is not None:
            marketplace_manifest_plugins.append(
                {"name": name, "version": available_version}
            )

        # Only create installed entry if there is an installed version
        if installed_version is not None:
            if source == "marketplace":
                registry_key = f"{name}@{marketplace_id}"
            else:
                registry_key = f"{name}@local"

            # Create the plugin directory with plugin.json
            install_path = (
                plugins_dir / "installed" / name
            )
            install_path.mkdir(parents=True, exist_ok=True)
            plugin_json_dir = install_path / ".claude-plugin"
            plugin_json_dir.mkdir(parents=True, exist_ok=True)
            plugin_json = {
                "name": name,
                "version": installed_version,
                "dependencies": dependencies,
            }
            (plugin_json_dir / "plugin.json").write_text(
                json.dumps(plugin_json), encoding="utf-8"
            )

            installed_entries.setdefault(registry_key, []).append(
                {"installPath": str(install_path)}
            )

    # Write installed_plugins.json
    plugins_dir.mkdir(parents=True, exist_ok=True)
    installed_plugins_data = {"plugins": installed_entries}
    (plugins_dir / "installed_plugins.json").write_text(
        json.dumps(installed_plugins_data), encoding="utf-8"
    )

    # ---- known_marketplaces.json ----
    known = {marketplace_id: {"url": "https://test.example.com"}}
    (plugins_dir / "known_marketplaces.json").write_text(
        json.dumps(known), encoding="utf-8"
    )

    # ---- marketplace manifest ----
    mp_dir = (
        marketplaces_dir / marketplace_id / ".claude-plugin"
    )
    mp_dir.mkdir(parents=True, exist_ok=True)
    mp_manifest = {"plugins": marketplace_manifest_plugins}
    (mp_dir / "marketplace.json").write_text(
        json.dumps(mp_manifest), encoding="utf-8"
    )

    return home_dir


def _run_full_pipeline(
    home_dir: Path,
) -> tuple:
    """Run the full scan -> resolve -> report pipeline.

    Returns (plugins, resolution, report) tuple.
    """
    plugins = scan_plugins(home_dir=home_dir)

    # Build resolver input from scanned plugins
    resolver_input = [
        (p.name, p.installed_version, p.dependencies)
        for p in plugins
        if p.installed_version is not None
    ]

    resolution = resolve_dependencies(resolver_input)
    report = generate_report(plugins, resolution)

    return plugins, resolution, report


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestMarketplaceSyncIntegration:
    """End-to-end: mock ecosystem -> scan -> resolve -> report."""

    def test_all_up_to_date(self):
        """All plugins current — clean report with no issues."""
        with tempfile.TemporaryDirectory() as tmp:
            home_dir = _build_ecosystem(
                tmp,
                [
                    {
                        "name": "alpha-plugin",
                        "installed_version": "1.0.0",
                        "available_version": "1.0.0",
                    },
                    {
                        "name": "beta-plugin",
                        "installed_version": "2.3.0",
                        "available_version": "2.3.0",
                    },
                ],
            )

            plugins, resolution, report = _run_full_pipeline(home_dir)

            # Both plugins scanned
            assert len(plugins) == 2

            # All up to date
            for row in report["plugins"]:
                assert row["status"] == "up-to-date", (
                    f"{row['name']} should be up-to-date"
                )

            # No issues
            assert report["dependency_issues"] == []
            assert report["cycles"] == []
            assert report["unresolved"] == []

            # Summary text
            assert "0 outdated" in report["summary"]
            assert "0 dependency issues" in report["summary"]

    def test_outdated_with_unsatisfied_dep(self):
        """Core is outdated, eng requires newer core — dep issue reported."""
        with tempfile.TemporaryDirectory() as tmp:
            home_dir = _build_ecosystem(
                tmp,
                [
                    {
                        "name": "core",
                        "installed_version": "1.0.0",
                        "available_version": "2.0.0",
                    },
                    {
                        "name": "eng",
                        "installed_version": "1.0.0",
                        "available_version": "1.0.0",
                        "dependencies": {"core": "^2.0.0"},
                    },
                ],
            )

            plugins, resolution, report = _run_full_pipeline(home_dir)

            # core is outdated
            core_row = next(
                r for r in report["plugins"] if r["name"] == "core"
            )
            assert core_row["status"] == "outdated"

            # eng has unsatisfied dependency on core
            assert len(report["dependency_issues"]) >= 1
            issue = next(
                i
                for i in report["dependency_issues"]
                if i["dependent"] == "eng"
                and i["dependency"] == "core"
            )
            assert issue["constraint"] == "^2.0.0"
            assert issue["installed"] == "1.0.0"

            # Single requestor for core, so no conflict (just unsatisfied)
            # Conflicts require mutually incompatible constraints
            assert resolution.conflicts == []

    def test_transitive_three_levels(self):
        """base -> mid -> top chain — verify install order."""
        with tempfile.TemporaryDirectory() as tmp:
            home_dir = _build_ecosystem(
                tmp,
                [
                    {
                        "name": "base",
                        "installed_version": "1.0.0",
                        "available_version": "1.0.0",
                    },
                    {
                        "name": "mid",
                        "installed_version": "1.0.0",
                        "available_version": "1.0.0",
                        "dependencies": {"base": "^1.0.0"},
                    },
                    {
                        "name": "top",
                        "installed_version": "1.0.0",
                        "available_version": "1.0.0",
                        "dependencies": {"mid": "^1.0.0"},
                    },
                ],
            )

            plugins, resolution, report = _run_full_pipeline(home_dir)

            # All three plugins scanned
            assert len(plugins) == 3

            # Install order respects dependencies: base before mid before top
            order = resolution.install_order
            assert "base" in order
            assert "mid" in order
            assert "top" in order
            assert order.index("base") < order.index("mid")
            assert order.index("mid") < order.index("top")

            # No cycles or conflicts
            assert resolution.cycles == []
            assert resolution.conflicts == []

            # Clean report
            assert report["dependency_issues"] == []

    def test_mixed_deps_and_no_deps(self):
        """Some plugins have deps, some don't — all handled correctly."""
        with tempfile.TemporaryDirectory() as tmp:
            home_dir = _build_ecosystem(
                tmp,
                [
                    {
                        "name": "foundation",
                        "installed_version": "1.0.0",
                        "available_version": "1.0.0",
                    },
                    {
                        "name": "standalone",
                        "installed_version": "3.0.0",
                        "available_version": "3.0.0",
                    },
                    {
                        "name": "dependent",
                        "installed_version": "2.0.0",
                        "available_version": "2.0.0",
                        "dependencies": {"foundation": "^1.0.0"},
                    },
                ],
            )

            plugins, resolution, report = _run_full_pipeline(home_dir)

            assert len(plugins) == 3

            # foundation must come before dependent
            order = resolution.install_order
            assert order.index("foundation") < order.index(
                "dependent"
            )

            # standalone can be anywhere (no dep constraints)
            assert "standalone" in order

            # No issues
            assert resolution.conflicts == []
            assert report["dependency_issues"] == []

            # All up to date
            for row in report["plugins"]:
                assert row["status"] == "up-to-date"

    def test_diamond_dependency(self):
        """A->B, A->C, B->D, C->D — diamond resolved correctly."""
        with tempfile.TemporaryDirectory() as tmp:
            home_dir = _build_ecosystem(
                tmp,
                [
                    {
                        "name": "d-base",
                        "installed_version": "1.0.0",
                        "available_version": "1.0.0",
                    },
                    {
                        "name": "b-left",
                        "installed_version": "1.0.0",
                        "available_version": "1.0.0",
                        "dependencies": {"d-base": "^1.0.0"},
                    },
                    {
                        "name": "c-right",
                        "installed_version": "1.0.0",
                        "available_version": "1.0.0",
                        "dependencies": {"d-base": "^1.0.0"},
                    },
                    {
                        "name": "a-top",
                        "installed_version": "1.0.0",
                        "available_version": "1.0.0",
                        "dependencies": {
                            "b-left": "^1.0.0",
                            "c-right": "^1.0.0",
                        },
                    },
                ],
            )

            plugins, resolution, report = _run_full_pipeline(home_dir)

            assert len(plugins) == 4

            order = resolution.install_order

            # d-base must come before b-left and c-right
            assert order.index("d-base") < order.index("b-left")
            assert order.index("d-base") < order.index("c-right")

            # b-left and c-right must both come before a-top
            assert order.index("b-left") < order.index("a-top")
            assert order.index("c-right") < order.index("a-top")

            # No cycles or conflicts
            assert resolution.cycles == []
            assert resolution.conflicts == []

            # Clean report
            assert report["dependency_issues"] == []

    def test_empty_ecosystem(self):
        """No plugins installed — empty results."""
        with tempfile.TemporaryDirectory() as tmp:
            home_dir = _build_ecosystem(tmp, [])

            plugins, resolution, report = _run_full_pipeline(home_dir)

            assert plugins == []
            assert report["plugins"] == []
            assert report["dependency_issues"] == []
            assert report["cycles"] == []
            assert report["unresolved"] == []
            assert "0 plugins" in report["summary"]

    def test_summary_counts(self):
        """generate_summary returns correct counts for mixed statuses."""
        with tempfile.TemporaryDirectory() as tmp:
            home_dir = _build_ecosystem(
                tmp,
                [
                    {
                        "name": "up-to-date-plugin",
                        "installed_version": "1.0.0",
                        "available_version": "1.0.0",
                    },
                    {
                        "name": "outdated-plugin",
                        "installed_version": "1.0.0",
                        "available_version": "2.0.0",
                    },
                    {
                        "name": "ahead-plugin",
                        "installed_version": "3.0.0",
                        "available_version": "2.0.0",
                    },
                    {
                        "name": "local-plugin",
                        "installed_version": "1.0.0",
                        "available_version": None,
                        "source": "local",
                    },
                    {
                        "name": "dep-plugin",
                        "installed_version": "1.0.0",
                        "available_version": "1.0.0",
                        "dependencies": {
                            "outdated-plugin": "^2.0.0",
                        },
                    },
                ],
            )

            plugins = scan_plugins(home_dir=home_dir)

            # Build resolver input from installed plugins only
            resolver_input = [
                (p.name, p.installed_version, p.dependencies)
                for p in plugins
                if p.installed_version is not None
            ]
            resolution = resolve_dependencies(resolver_input)
            summary = generate_summary(plugins, resolution)

            assert summary["total"] == 5
            assert summary["outdated"] == 1
            assert summary["up_to_date"] == 2  # up-to-date + dep-plugin
            assert summary["ahead"] == 1
            assert summary["local"] == 1
            assert summary["dependency_issues"] == 1
