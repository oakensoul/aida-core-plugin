"""Integration tests for the AIDA backup skill.

Tests the full end-to-end flow via subprocess calls to backup.py,
which is how the two-phase API is used in production. Uses real
filesystem operations with temporary directories.
"""

import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

_project_root = Path(__file__).parent.parent.parent
_backup_script = (
    _project_root / "skills" / "backup" / "scripts" / "backup.py"
)


def _run_backup(context, responses=None, phase="execute"):
    """Run backup.py via subprocess and return parsed JSON output."""
    flag = f"--{phase}"
    cmd = [
        sys.executable,
        str(_backup_script),
        flag,
        "--context",
        json.dumps(context),
    ]
    if responses:
        cmd.extend(["--responses", json.dumps(responses)])

    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=30,
    )
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        raise AssertionError(
            f"Failed to parse JSON from backup.py\n"
            f"stdout: {result.stdout}\n"
            f"stderr: {result.stderr}\n"
            f"returncode: {result.returncode}"
        )


@pytest.fixture()
def backup_env(tmp_path, monkeypatch):
    """Set up a temporary backup environment.

    Overrides HOME so backup storage goes to a temp directory,
    and creates a test file to back up.
    """
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setenv("HOME", str(fake_home))

    # Create a test file outside the temp home
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    test_file = project_dir / "config.yml"
    test_file.write_text("version: 1\nname: test\n")

    # Create aida.yml with global storage pointing to temp
    claude_dir = fake_home / ".claude"
    claude_dir.mkdir(parents=True)
    backup_dir = claude_dir / ".backups"

    aida_yml = claude_dir / "aida.yml"
    aida_yml.write_text(
        "backup:\n"
        "  enabled: true\n"
        "  scope: always\n"
        "  storage: global\n"
        "  retention:\n"
        "    max_versions: 0\n"
        "    max_age_days: 0\n"
        "    auto_enforce: true\n"
    )

    return {
        "home": fake_home,
        "project_dir": project_dir,
        "test_file": test_file,
        "backup_dir": backup_dir,
        "aida_yml": aida_yml,
    }


class TestBackupSaveRestore:
    """End-to-end save and restore operations."""

    def test_save_creates_backup_and_metadata(self, backup_env):
        """Save creates a timestamped backup and .meta.json sidecar."""
        result = _run_backup({
            "operation": "save",
            "file": str(backup_env["test_file"]),
            "message": "initial backup",
        })
        assert result["success"] is True
        assert result["skipped"] is False
        assert "backup_path" in result

        backup_path = Path(result["backup_path"])
        assert backup_path.exists()
        assert backup_path.read_text() == "version: 1\nname: test\n"

        meta_path = Path(str(backup_path) + ".meta.json")
        assert meta_path.exists()
        meta = json.loads(meta_path.read_text())
        assert meta["message"] == "initial backup"
        assert "checksum" in meta
        assert "timestamp" in meta

    def test_save_dedup_skips_unchanged(self, backup_env):
        """Second save of unchanged file is skipped (checksum dedup)."""
        _run_backup({
            "operation": "save",
            "file": str(backup_env["test_file"]),
        })
        result = _run_backup({
            "operation": "save",
            "file": str(backup_env["test_file"]),
        })
        assert result["success"] is True
        assert result["skipped"] is True
        assert result["reason"] == "unchanged"

    def test_save_creates_new_version_on_change(self, backup_env):
        """Changed file creates a new backup version."""
        _run_backup({
            "operation": "save",
            "file": str(backup_env["test_file"]),
        })

        # Modify the file
        backup_env["test_file"].write_text("version: 2\nname: test\n")
        time.sleep(1)  # Ensure different timestamp

        result = _run_backup({
            "operation": "save",
            "file": str(backup_env["test_file"]),
        })
        assert result["success"] is True
        assert result["skipped"] is False

    def test_restore_recovers_previous_version(self, backup_env):
        """Restore brings back the backed-up content."""
        _run_backup({
            "operation": "save",
            "file": str(backup_env["test_file"]),
            "message": "v1",
        })

        # Modify the file
        backup_env["test_file"].write_text("version: 2\nname: changed\n")

        result = _run_backup({
            "operation": "restore",
            "file": str(backup_env["test_file"]),
            "version": "latest",
        })
        assert result["success"] is True

        restored = backup_env["test_file"].read_text()
        assert restored == "version: 1\nname: test\n"


class TestBackupDiff:
    """End-to-end diff operations."""

    def test_diff_shows_changes(self, backup_env):
        """Diff between backup and modified current file shows changes."""
        _run_backup({
            "operation": "save",
            "file": str(backup_env["test_file"]),
        })

        backup_env["test_file"].write_text("version: 2\nname: updated\n")

        result = _run_backup({
            "operation": "diff",
            "file": str(backup_env["test_file"]),
            "version1": "latest",
            "version2": "current",
        })
        assert result["success"] is True
        assert result["has_changes"] is True
        assert "-version: 1" in result["diff"]
        assert "+version: 2" in result["diff"]

    def test_diff_no_changes(self, backup_env):
        """Diff of identical content shows no changes."""
        _run_backup({
            "operation": "save",
            "file": str(backup_env["test_file"]),
        })

        result = _run_backup({
            "operation": "diff",
            "file": str(backup_env["test_file"]),
            "version1": "latest",
            "version2": "current",
        })
        assert result["success"] is True
        assert result["has_changes"] is False


class TestBackupList:
    """End-to-end list operations."""

    def test_list_file_versions(self, backup_env):
        """List shows all versions of a specific file."""
        _run_backup({
            "operation": "save",
            "file": str(backup_env["test_file"]),
            "message": "first",
        })

        backup_env["test_file"].write_text("version: 2\n")
        time.sleep(1)

        _run_backup({
            "operation": "save",
            "file": str(backup_env["test_file"]),
            "message": "second",
        })

        result = _run_backup({
            "operation": "list",
            "file": str(backup_env["test_file"]),
        })
        assert result["success"] is True
        assert result["count"] == 2
        assert len(result["versions"]) == 2

    def test_list_all_files(self, backup_env):
        """List without file shows all backed-up files."""
        # Create and back up a second file
        file2 = backup_env["project_dir"] / "other.txt"
        file2.write_text("hello\n")

        _run_backup({
            "operation": "save",
            "file": str(backup_env["test_file"]),
        })
        _run_backup({
            "operation": "save",
            "file": str(file2),
        })

        result = _run_backup({"operation": "list"})
        assert result["success"] is True
        assert result["total_files"] == 2


class TestBackupStatus:
    """End-to-end status operations."""

    def test_status_with_backups(self, backup_env):
        """Status shows analytics for existing backups."""
        _run_backup({
            "operation": "save",
            "file": str(backup_env["test_file"]),
        })

        result = _run_backup({"operation": "status"})
        assert result["success"] is True
        assert "config" in result
        assert "stats" in result
        assert result["stats"]["total_files_backed_up"] == 1
        assert result["stats"]["total_backup_versions"] == 1

    def test_status_empty(self, backup_env):
        """Status with no backups shows zeros."""
        result = _run_backup({"operation": "status"})
        assert result["success"] is True
        assert result["stats"]["total_files_backed_up"] == 0


class TestBackupClean:
    """End-to-end clean operations."""

    def test_clean_no_policy(self, backup_env):
        """Clean with unlimited retention is a no-op."""
        _run_backup({
            "operation": "save",
            "file": str(backup_env["test_file"]),
        })

        result = _run_backup({
            "operation": "clean",
            "dry_run": False,
        })
        assert result["success"] is True
        assert "No retention policy" in result.get("note", "")

    def test_clean_enforces_max_versions(self, backup_env):
        """Clean removes excess versions when max_versions is set."""
        # Create 3 versions
        for i in range(3):
            backup_env["test_file"].write_text(f"version: {i}\n")
            time.sleep(1)
            _run_backup({
                "operation": "save",
                "file": str(backup_env["test_file"]),
            })

        # Set retention to 1 version
        backup_env["aida_yml"].write_text(
            "backup:\n"
            "  enabled: true\n"
            "  scope: always\n"
            "  storage: global\n"
            "  retention:\n"
            "    max_versions: 1\n"
            "    max_age_days: 0\n"
            "    auto_enforce: false\n"
        )

        result = _run_backup({
            "operation": "clean",
            "dry_run": False,
        })
        assert result["success"] is True
        assert result["backups_removed"] == 2

    def test_clean_dry_run(self, backup_env):
        """Dry run reports what would be removed without deleting."""
        for i in range(3):
            backup_env["test_file"].write_text(f"version: {i}\n")
            time.sleep(1)
            _run_backup({
                "operation": "save",
                "file": str(backup_env["test_file"]),
            })

        backup_env["aida_yml"].write_text(
            "backup:\n"
            "  enabled: true\n"
            "  scope: always\n"
            "  storage: global\n"
            "  retention:\n"
            "    max_versions: 1\n"
            "    max_age_days: 0\n"
            "    auto_enforce: false\n"
        )

        result = _run_backup({
            "operation": "clean",
            "dry_run": True,
        })
        assert result["success"] is True
        assert result["backups_removed"] == 2
        assert result["dry_run"] is True

        # Verify nothing was actually deleted
        list_result = _run_backup({
            "operation": "list",
            "file": str(backup_env["test_file"]),
        })
        assert list_result["count"] == 3


class TestBackupConfig:
    """End-to-end config operations."""

    def test_config_get_questions(self, backup_env):
        """Config get-questions returns questionnaire."""
        result = _run_backup(
            {"operation": "config"},
            phase="get-questions",
        )
        assert result["success"] is True
        assert len(result["questions"]) > 0
        ids = [q["id"] for q in result["questions"]]
        assert "backup_enabled" in ids
        assert "backup_scope" in ids

    def test_config_execute_writes_yaml(self, backup_env):
        """Config execute writes settings to aida.yml."""
        result = _run_backup(
            {"operation": "config"},
            responses={
                "backup_enabled": True,
                "backup_scope": "outside-git-only",
                "backup_storage": "global",
                "backup_retention_versions": "5",
                "backup_retention_days": "30",
                "backup_retention_auto_enforce": True,
                "backup_custom_command": "",
            },
        )
        assert result["success"] is True

        import yaml
        data = yaml.safe_load(backup_env["aida_yml"].read_text())
        assert data["backup"]["scope"] == "outside-git-only"
        assert data["backup"]["retention"]["max_versions"] == 5
        assert data["backup"]["retention"]["max_age_days"] == 30


class TestBackupDisabled:
    """Test behavior when backup is disabled."""

    def test_disabled_skips_save(self, backup_env):
        """Disabled backup skips save operations."""
        backup_env["aida_yml"].write_text(
            "backup:\n"
            "  enabled: false\n"
        )

        result = _run_backup({
            "operation": "save",
            "file": str(backup_env["test_file"]),
        })
        assert result["success"] is True
        assert result["skipped"] is True
        assert result["reason"] == "not in scope"
