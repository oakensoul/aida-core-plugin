"""Tests for the marketplace-sync report generator."""

from __future__ import annotations

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


# ------------------------------------------------------------------
# generate_report tests
# ------------------------------------------------------------------


class TestGenerateReport:
    def test_empty_plugins(self) -> None:
        report = generate_report([], ResolutionResult())
        assert report["plugins"] == []
        assert report["dependency_issues"] == []
        assert report["cycles"] == []
        assert report["unresolved"] == []
        assert report["warnings"] == []
        assert "0 plugins" in report["summary"]

    def test_all_up_to_date(self) -> None:
        plugins = [
            PluginState(
                name="core",
                installed_version="1.0.0",
                available_version="1.0.0",
            ),
        ]
        result = ResolutionResult(
            graph={"core": []}, install_order=["core"]
        )
        report = generate_report(plugins, result)
        assert report["plugins"][0]["status"] == "up-to-date"
        assert "0 outdated" in report["summary"]

    def test_outdated_plugin(self) -> None:
        plugins = [
            PluginState(
                name="core",
                installed_version="1.0.0",
                available_version="2.0.0",
            ),
        ]
        result = ResolutionResult(
            graph={"core": []}, install_order=["core"]
        )
        report = generate_report(plugins, result)
        assert report["plugins"][0]["status"] == "outdated"
        assert "1 outdated" in report["summary"]

    def test_ahead_plugin(self) -> None:
        plugins = [
            PluginState(
                name="core",
                installed_version="2.0.0",
                available_version="1.0.0",
            ),
        ]
        result = ResolutionResult(
            graph={"core": []}, install_order=["core"]
        )
        report = generate_report(plugins, result)
        assert report["plugins"][0]["status"] == "ahead"

    def test_local_plugin(self) -> None:
        plugins = [
            PluginState(
                name="local-thing",
                installed_version="1.0.0",
                source="local",
            ),
        ]
        result = ResolutionResult(
            graph={"local-thing": []},
            install_order=["local-thing"],
        )
        report = generate_report(plugins, result)
        assert report["plugins"][0]["status"] == "local"

    def test_unsatisfied_dependency(self) -> None:
        plugins = [
            PluginState(
                name="core",
                installed_version="0.9.0",
                available_version="1.4.0",
            ),
            PluginState(
                name="eng",
                installed_version="1.0.0",
                available_version="1.0.0",
                dependencies={"core": ">=1.0.0"},
            ),
        ]
        edge = DependencyEdge(
            dependent="eng",
            dependency="core",
            constraint=">=1.0.0",
            satisfied=False,
            installed="0.9.0",
        )
        result = ResolutionResult(
            graph={"core": [], "eng": [edge]},
            install_order=["core", "eng"],
        )
        report = generate_report(plugins, result)
        assert len(report["dependency_issues"]) == 1
        assert report["dependency_issues"][0]["dependent"] == "eng"
        assert (
            report["dependency_issues"][0]["dependency"] == "core"
        )
        assert (
            report["dependency_issues"][0]["constraint"]
            == ">=1.0.0"
        )
        assert (
            report["dependency_issues"][0]["installed"] == "0.9.0"
        )
        assert "1 dependency issues" in report["summary"]

    def test_unknown_version(self) -> None:
        plugins = [
            PluginState(
                name="official",
                installed_version="unknown",
            ),
        ]
        result = ResolutionResult(
            graph={"official": []},
            install_order=["official"],
        )
        report = generate_report(plugins, result)
        assert report["plugins"][0]["status"] == "unknown"

    def test_none_installed_version(self) -> None:
        """Plugin with None installed version is unknown."""
        plugins = [
            PluginState(
                name="mystery",
                installed_version=None,
                available_version="1.0.0",
            ),
        ]
        result = ResolutionResult(
            graph={"mystery": []},
            install_order=["mystery"],
        )
        report = generate_report(plugins, result)
        assert report["plugins"][0]["status"] == "unknown"
        assert report["plugins"][0]["installed"] == "-"

    def test_none_available_version(self) -> None:
        """Plugin with None available version is unknown."""
        plugins = [
            PluginState(
                name="orphan",
                installed_version="1.0.0",
                available_version=None,
            ),
        ]
        result = ResolutionResult(
            graph={"orphan": []},
            install_order=["orphan"],
        )
        report = generate_report(plugins, result)
        assert report["plugins"][0]["status"] == "unknown"
        assert report["plugins"][0]["available"] == "-"

    def test_cycles_and_unresolved_passed_through(self) -> None:
        """Cycles, unresolved, and warnings from resolution appear."""
        result = ResolutionResult(
            cycles=[["a", "b"]],
            unresolved=["missing-lib"],
            warnings=["something fishy"],
        )
        report = generate_report([], result)
        assert report["cycles"] == [["a", "b"]]
        assert report["unresolved"] == ["missing-lib"]
        assert report["warnings"] == ["something fishy"]

    def test_plugin_row_fields(self) -> None:
        """Each plugin row has expected keys and values."""
        plugins = [
            PluginState(
                name="my-plugin",
                installed_version="1.2.3",
                available_version="1.2.3",
                marketplace_id="mkt-123",
            ),
        ]
        result = ResolutionResult(
            graph={"my-plugin": []},
            install_order=["my-plugin"],
        )
        report = generate_report(plugins, result)
        row = report["plugins"][0]
        assert row["name"] == "my-plugin"
        assert row["installed"] == "1.2.3"
        assert row["available"] == "1.2.3"
        assert row["status"] == "up-to-date"
        assert row["marketplace"] == "mkt-123"

    def test_marketplace_id_none_shows_dash(self) -> None:
        plugins = [
            PluginState(
                name="no-mkt",
                installed_version="1.0.0",
                available_version="1.0.0",
                marketplace_id=None,
            ),
        ]
        result = ResolutionResult(
            graph={"no-mkt": []},
            install_order=["no-mkt"],
        )
        report = generate_report(plugins, result)
        assert report["plugins"][0]["marketplace"] == "-"


# ------------------------------------------------------------------
# generate_summary tests
# ------------------------------------------------------------------


class TestGenerateSummary:
    def test_summary_counts(self) -> None:
        plugins = [
            PluginState(
                name="a",
                installed_version="1.0.0",
                available_version="2.0.0",
            ),
            PluginState(
                name="b",
                installed_version="1.0.0",
                available_version="1.0.0",
            ),
        ]
        result = ResolutionResult(
            graph={"a": [], "b": []},
            install_order=["a", "b"],
        )
        summary = generate_summary(plugins, result)
        assert summary["total"] == 2
        assert summary["outdated"] == 1
        assert summary["up_to_date"] == 1
        assert summary["ahead"] == 0
        assert summary["local"] == 0
        assert summary["unknown"] == 0
        assert summary["dependency_issues"] == 0

    def test_summary_empty(self) -> None:
        summary = generate_summary([], ResolutionResult())
        assert summary["total"] == 0
        assert summary["outdated"] == 0
        assert summary["up_to_date"] == 0
        assert summary["dependency_issues"] == 0

    def test_summary_all_statuses(self) -> None:
        """Summary counts every status type correctly."""
        plugins = [
            PluginState(
                name="outdated-one",
                installed_version="1.0.0",
                available_version="2.0.0",
            ),
            PluginState(
                name="current",
                installed_version="1.0.0",
                available_version="1.0.0",
            ),
            PluginState(
                name="ahead-one",
                installed_version="3.0.0",
                available_version="2.0.0",
            ),
            PluginState(
                name="local-one",
                installed_version="1.0.0",
                source="local",
            ),
            PluginState(
                name="mystery",
                installed_version="unknown",
            ),
        ]
        edge = DependencyEdge(
            dependent="outdated-one",
            dependency="missing",
            constraint=">=1.0.0",
            satisfied=False,
            installed=None,
        )
        result = ResolutionResult(
            graph={
                "outdated-one": [edge],
                "current": [],
                "ahead-one": [],
                "local-one": [],
                "mystery": [],
            },
            install_order=[
                "outdated-one",
                "current",
                "ahead-one",
                "local-one",
                "mystery",
            ],
        )
        summary = generate_summary(plugins, result)
        assert summary["total"] == 5
        assert summary["outdated"] == 1
        assert summary["up_to_date"] == 1
        assert summary["ahead"] == 1
        assert summary["local"] == 1
        assert summary["unknown"] == 1
        assert summary["dependency_issues"] == 1
