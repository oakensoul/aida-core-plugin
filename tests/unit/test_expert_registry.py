"""Tests for expert-registry registry module (config I/O)."""

import sys
import tempfile
from pathlib import Path

import yaml

# Add operations module to path
sys.path.insert(
    0,
    str(
        Path(__file__).parent.parent.parent
        / "skills"
        / "expert-registry"
        / "scripts"
    ),
)

from expert_ops.registry import load_experts_config, save_experts_config  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump(data), encoding="utf-8")


# ---------------------------------------------------------------------------
# TestConfigLoading
# ---------------------------------------------------------------------------


class TestConfigLoading:
    def test_load_global_experts_active(self):
        """Global config with active experts returns the list, source='global', empty panels."""
        with tempfile.TemporaryDirectory() as tmp:
            global_path = Path(tmp) / "global.yml"
            _write_yaml(global_path, {"experts": {"active": ["alice", "bob"]}})

            result = load_experts_config(
                global_path=global_path,
                project_path=Path(tmp) / "nonexistent.yml",
            )

        assert result["active"] == ["alice", "bob"]
        assert result["source"] == "global"
        assert result["panels"] == {}
        assert result["warnings"] == []

    def test_union_merge_global_and_project(self):
        """Both layers present merges active lists (global first, deduplicated)."""
        with tempfile.TemporaryDirectory() as tmp:
            global_path = Path(tmp) / "global.yml"
            _write_yaml(global_path, {"experts": {"active": ["alice"]}})

            project_path = Path(tmp) / "project.yml"
            _write_yaml(
                project_path,
                {
                    "experts": {
                        "active": ["charlie"],
                        "panels": {"review": ["charlie"]},
                    }
                },
            )

            result = load_experts_config(
                global_path=global_path,
                project_path=project_path,
            )

        assert result["active"] == ["alice", "charlie"]
        assert result["source"] == "merged"
        assert result["panels"] == {"review": ["charlie"]}
        assert result["warnings"] == []

    def test_union_merge_deduplicates(self):
        """Duplicate names across layers appear only once."""
        with tempfile.TemporaryDirectory() as tmp:
            global_path = Path(tmp) / "global.yml"
            _write_yaml(global_path, {"experts": {"active": ["alice", "bob"]}})

            project_path = Path(tmp) / "project.yml"
            _write_yaml(
                project_path,
                {"experts": {"active": ["bob", "charlie"]}},
            )

            result = load_experts_config(
                global_path=global_path,
                project_path=project_path,
            )

        assert result["active"] == ["alice", "bob", "charlie"]
        assert result["source"] == "merged"

    def test_empty_active_list_suppresses_global(self):
        """Explicit empty list in project opts out of global, zero experts."""
        with tempfile.TemporaryDirectory() as tmp:
            global_path = Path(tmp) / "global.yml"
            _write_yaml(global_path, {"experts": {"active": ["alice"]}})

            project_path = Path(tmp) / "project.yml"
            _write_yaml(project_path, {"experts": {"active": []}})

            result = load_experts_config(
                global_path=global_path,
                project_path=project_path,
            )

        assert result["active"] == []
        assert result["source"] == "project"

    def test_absent_experts_key_falls_through(self):
        """Project config without experts key falls to global."""
        with tempfile.TemporaryDirectory() as tmp:
            global_path = Path(tmp) / "global.yml"
            _write_yaml(global_path, {"experts": {"active": ["alice"]}})

            project_path = Path(tmp) / "project.yml"
            _write_yaml(project_path, {"other_key": "value"})

            result = load_experts_config(
                global_path=global_path,
                project_path=project_path,
            )

        assert result["active"] == ["alice"]
        assert result["source"] == "global"

    def test_both_configs_absent(self):
        """No configs returns empty active, source=None."""
        with tempfile.TemporaryDirectory() as tmp:
            result = load_experts_config(
                global_path=Path(tmp) / "no_global.yml",
                project_path=Path(tmp) / "no_project.yml",
            )

        assert result["active"] == []
        assert result["source"] is None
        assert result["warnings"] == []

    def test_malformed_yaml_skipped_with_warning(self):
        """Malformed YAML skipped, falls to global, warning added."""
        with tempfile.TemporaryDirectory() as tmp:
            global_path = Path(tmp) / "global.yml"
            _write_yaml(global_path, {"experts": {"active": ["alice"]}})

            project_path = Path(tmp) / "project.yml"
            project_path.write_text(": invalid: yaml: {{{{", encoding="utf-8")

            result = load_experts_config(
                global_path=global_path,
                project_path=project_path,
            )

        assert result["active"] == ["alice"]
        assert result["source"] == "global"
        assert len(result["warnings"]) >= 1
        assert any("malformed" in w.lower() or "yaml" in w.lower() for w in result["warnings"])

    def test_non_string_entries_filtered(self):
        """Non-string values in active skipped with warning."""
        with tempfile.TemporaryDirectory() as tmp:
            global_path = Path(tmp) / "global.yml"
            _write_yaml(
                global_path,
                {"experts": {"active": ["alice", 42, None, "bob"]}},
            )

            result = load_experts_config(
                global_path=global_path,
                project_path=Path(tmp) / "nonexistent.yml",
            )

        assert result["active"] == ["alice", "bob"]
        assert len(result["warnings"]) >= 1

    def test_panels_non_list_skipped(self):
        """Panel value not a list is skipped with warning."""
        with tempfile.TemporaryDirectory() as tmp:
            global_path = Path(tmp) / "global.yml"
            _write_yaml(
                global_path,
                {
                    "experts": {
                        "active": ["alice"],
                        "panels": {"review": "not-a-list"},
                    }
                },
            )

            result = load_experts_config(
                global_path=global_path,
                project_path=Path(tmp) / "nonexistent.yml",
            )

        assert result["panels"] == {}
        assert len(result["warnings"]) >= 1


# ---------------------------------------------------------------------------
# TestConfigWriting
# ---------------------------------------------------------------------------


class TestConfigWriting:
    def test_save_active_to_new_global(self):
        """Save to non-existent file creates it."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "subdir" / "experts.yml"

            save_experts_config(path=path, active=["alice", "bob"])

            assert path.exists()
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            assert data["experts"]["active"] == ["alice", "bob"]

    def test_save_preserves_existing_config(self):
        """Writing experts preserves other keys."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "experts.yml"
            _write_yaml(path, {"version": "1.0", "other": "value"})

            save_experts_config(path=path, active=["alice"])

            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            assert data["version"] == "1.0"
            assert data["other"] == "value"
            assert data["experts"]["active"] == ["alice"]

    def test_save_panels_to_project(self):
        """Save named panels."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "experts.yml"

            save_experts_config(
                path=path,
                active=["alice", "charlie"],
                panels={"review": ["alice"], "design": ["charlie"]},
            )

            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            assert data["experts"]["active"] == ["alice", "charlie"]
            assert data["experts"]["panels"] == {
                "review": ["alice"],
                "design": ["charlie"],
            }
