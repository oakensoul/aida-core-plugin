"""Unit tests for backup skill operations.

Covers: checksum dedup, metadata sidecars, git context capture,
version resolution, diff, builtin provider, retention policy,
status/analytics, custom command override, storage locations,
scope checking, config loading, and two-phase API.
"""

import sys
import hashlib
import shutil
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add scripts directories to path for imports
_project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_project_root / "scripts"))
sys.path.insert(0, str(_project_root / "skills" / "backup" / "scripts"))

# Clear cached modules to avoid cross-skill conflicts in pytest
for _mod_name in list(sys.modules):
    if _mod_name == "operations" or _mod_name.startswith("operations."):
        del sys.modules[_mod_name]
sys.modules.pop("_paths", None)

from operations.backup_ops import (  # noqa: E402
    _compute_checksum,
    _get_git_context,
    _write_metadata,
    _read_metadata,
    _repair_metadata,
    _list_backups_with_metadata,
    _resolve_version,
    _get_backup_dir,
    _format_size,
    _run_custom_command,
    _maybe_enforce_retention,
    _is_git_tracked,
    builtin_backup,
    builtin_restore,
    builtin_diff,
    builtin_list,
    builtin_clean,
    get_status,
    load_backup_config,
    should_backup,
    run_backup,
    BACKUP_SUFFIX,
    META_SUFFIX,
    TIMESTAMP_FMT,
)

_ops_snapshot = {
    k: v for k, v in sys.modules.items()
    if k == "operations" or k.startswith("operations.")
}


def _make_config(**overrides):
    """Create a test config with defaults."""
    config = {
        "enabled": True,
        "scope": "always",
        "storage": "local",
        "custom_command": "",
        "retention": {
            "max_versions": 0,
            "max_age_days": 0,
            "auto_enforce": True,
        },
    }
    for k, v in overrides.items():
        if k == "retention":
            config["retention"].update(v)
        else:
            config[k] = v
    return config


class TestChecksum(unittest.TestCase):
    """Tests for _compute_checksum."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp()).resolve()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_checksum_consistent(self):
        f = self.tmpdir / "test.txt"
        f.write_text("hello world")
        c1 = _compute_checksum(f)
        c2 = _compute_checksum(f)
        self.assertEqual(c1, c2)

    def test_checksum_changes_with_content(self):
        f = self.tmpdir / "test.txt"
        f.write_text("hello")
        c1 = _compute_checksum(f)
        f.write_text("world")
        c2 = _compute_checksum(f)
        self.assertNotEqual(c1, c2)

    def test_checksum_matches_hashlib(self):
        f = self.tmpdir / "test.txt"
        content = b"test content"
        f.write_bytes(content)
        expected = hashlib.md5(content).hexdigest()
        self.assertEqual(_compute_checksum(f), expected)


class TestGitContext(unittest.TestCase):
    """Tests for _get_git_context."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp()).resolve()
        self.test_file = self.tmpdir / "test.txt"
        self.test_file.write_text("test")

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    @patch("operations.backup_ops.subprocess.run")
    def test_git_context_included_in_result(self, mock_run):
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="abc1234\n"),
            MagicMock(returncode=0, stdout=""),
        ]
        ctx = _get_git_context(self.test_file)
        self.assertEqual(ctx["git_hash"], "abc1234")
        self.assertFalse(ctx["git_dirty"])

    @patch("operations.backup_ops.subprocess.run")
    def test_git_context_null_outside_repo(self, mock_run):
        mock_run.side_effect = FileNotFoundError("git not found")
        ctx = _get_git_context(self.test_file)
        self.assertIsNone(ctx["git_hash"])
        self.assertIsNone(ctx["git_dirty"])

    @patch("operations.backup_ops.subprocess.run")
    def test_git_context_dirty_when_changes(self, mock_run):
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="abc1234\n"),
            MagicMock(returncode=0, stdout=" M file.txt\n"),
        ]
        ctx = _get_git_context(self.test_file)
        self.assertTrue(ctx["git_dirty"])

    @patch("operations.backup_ops.subprocess.run")
    def test_git_context_graceful_on_timeout(self, mock_run):
        from subprocess import TimeoutExpired
        mock_run.side_effect = TimeoutExpired("git", 5)
        ctx = _get_git_context(self.test_file)
        self.assertIsNone(ctx["git_hash"])
        self.assertIsNone(ctx["git_dirty"])


class TestMetadataSidecar(unittest.TestCase):
    """Tests for metadata write/read/repair."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp()).resolve()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_metadata_written_alongside_backup(self):
        backup = self.tmpdir / "test.txt.aida-backup.20260305-143000"
        backup.write_text("content")
        meta = {
            "original_path": "/path/test.txt",
            "timestamp": "2026-03-05T14:30:00+00:00",
            "message": "test",
            "file_size": 7,
            "checksum": "abc123",
            "backup_path": str(backup),
            "git_hash": None,
            "git_dirty": None,
        }
        _write_metadata(backup, meta)
        meta_path = Path(str(backup) + META_SUFFIX)
        self.assertTrue(meta_path.exists())

    def test_metadata_contains_required_fields(self):
        backup = self.tmpdir / "test.txt.aida-backup.20260305-143000"
        backup.write_text("content")
        meta = {
            "original_path": "/test.txt",
            "timestamp": "2026-03-05T14:30:00+00:00",
            "message": "test",
            "file_size": 7,
            "checksum": "abc",
            "backup_path": str(backup),
            "git_hash": "abc1234",
            "git_dirty": False,
        }
        _write_metadata(backup, meta)
        loaded = _read_metadata(backup)
        for key in ("original_path", "timestamp", "message",
                     "file_size", "checksum", "git_hash", "git_dirty"):
            self.assertIn(key, loaded)

    def test_metadata_read_returns_dict(self):
        backup = self.tmpdir / "test.txt.aida-backup.20260305-143000"
        backup.write_text("content")
        meta = {"original_path": "/test.txt", "timestamp": "2026"}
        _write_metadata(backup, meta)
        result = _read_metadata(backup)
        self.assertIsInstance(result, dict)
        self.assertEqual(result["original_path"], "/test.txt")

    def test_metadata_repair_rebuilds_when_missing(self):
        backup = self.tmpdir / "test.txt.aida-backup.20260305-143000"
        backup.write_text("content")
        # No meta file exists
        result = _read_metadata(backup)
        self.assertIsInstance(result, dict)
        self.assertIn("checksum", result)
        # Meta file should now exist
        meta_path = Path(str(backup) + META_SUFFIX)
        self.assertTrue(meta_path.exists())

    def test_metadata_repair_rebuilds_when_corrupted(self):
        backup = self.tmpdir / "test.txt.aida-backup.20260305-143000"
        backup.write_text("content")
        meta_path = Path(str(backup) + META_SUFFIX)
        meta_path.write_text("not valid json{{{")
        result = _read_metadata(backup)
        self.assertIsInstance(result, dict)
        self.assertIn("checksum", result)

    def test_metadata_repair_recovers_fields(self):
        backup = self.tmpdir / "test.txt.aida-backup.20260305-143000"
        backup.write_text("test content")
        result = _repair_metadata(backup)
        self.assertEqual(result["file_size"], 12)
        self.assertEqual(
            result["checksum"],
            hashlib.md5(b"test content").hexdigest(),
        )
        self.assertIn("2026-03-05", result["timestamp"])

    def test_metadata_repair_sets_rebuilt_message(self):
        backup = self.tmpdir / "test.txt.aida-backup.20260305-143000"
        backup.write_text("content")
        result = _repair_metadata(backup)
        self.assertEqual(result["message"], "(metadata rebuilt)")

    def test_metadata_repair_triggered_automatically(self):
        backup = self.tmpdir / "test.txt.aida-backup.20260305-143000"
        backup.write_text("content")
        # _read_metadata should trigger repair when no meta exists
        result = _read_metadata(backup)
        self.assertIsNotNone(result)
        self.assertEqual(result["message"], "(metadata rebuilt)")


class TestVersionResolution(unittest.TestCase):
    """Tests for _resolve_version."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp()).resolve()
        self.test_file = self.tmpdir / "test.txt"
        self.test_file.write_text("current content")
        self.config = _make_config(storage="local")

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def _create_backup(self, timestamp):
        bp = self.tmpdir / f"test.txt{BACKUP_SUFFIX}.{timestamp}"
        bp.write_text(f"content at {timestamp}")
        # Parse timestamp to create unique ISO timestamp for metadata
        dt = datetime.strptime(timestamp, TIMESTAMP_FMT)
        dt = dt.replace(tzinfo=timezone.utc)
        meta = {
            "original_path": str(self.test_file),
            "timestamp": dt.isoformat(),
            "backup_path": str(bp),
            "checksum": hashlib.md5(
                f"content at {timestamp}".encode()
            ).hexdigest(),
            "file_size": bp.stat().st_size,
            "message": "",
            "git_hash": None,
            "git_dirty": None,
        }
        _write_metadata(bp, meta)
        return bp

    def test_resolve_latest_finds_newest(self):
        self._create_backup("20260301-100000")
        bp2 = self._create_backup("20260305-143000")
        result = _resolve_version(self.test_file, "latest", self.config)
        self.assertEqual(result, bp2)

    def test_resolve_current_returns_original(self):
        result = _resolve_version(
            self.test_file, "current", self.config
        )
        self.assertEqual(result, self.test_file.resolve())

    def test_resolve_timestamp_finds_exact(self):
        bp = self._create_backup("20260305-143000")
        result = _resolve_version(
            self.test_file, "20260305-143000", self.config
        )
        self.assertEqual(result, bp)

    def test_resolve_returns_none_when_not_found(self):
        result = _resolve_version(
            self.test_file, "99999999-999999", self.config
        )
        self.assertIsNone(result)

    def test_resolve_latest_no_backups(self):
        result = _resolve_version(
            self.test_file, "latest", self.config
        )
        self.assertIsNone(result)


class TestDiff(unittest.TestCase):
    """Tests for builtin_diff."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp()).resolve()
        self.test_file = self.tmpdir / "test.txt"
        self.test_file.write_text("line1\nline2\nline3\n")
        self.config = _make_config(storage="local")

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def _create_backup(self, content, timestamp):
        bp = self.tmpdir / f"test.txt{BACKUP_SUFFIX}.{timestamp}"
        bp.write_text(content)
        dt = datetime.strptime(timestamp, TIMESTAMP_FMT)
        dt = dt.replace(tzinfo=timezone.utc)
        meta = {
            "original_path": str(self.test_file),
            "timestamp": dt.isoformat(),
            "backup_path": str(bp),
            "checksum": hashlib.md5(content.encode()).hexdigest(),
            "file_size": len(content),
            "message": "",
            "git_hash": None,
            "git_dirty": None,
        }
        _write_metadata(bp, meta)
        return bp

    @patch("operations.backup_ops._get_git_context")
    def test_diff_latest_vs_current(self, mock_git):
        mock_git.return_value = {"git_hash": None, "git_dirty": None}
        self._create_backup("line1\nold_line2\nline3\n", "20260305-143000")
        result = builtin_diff(
            self.test_file, self.config, "latest", "current"
        )
        self.assertTrue(result["success"])
        self.assertTrue(result["has_changes"])
        self.assertIn("-old_line2", result["diff"])
        self.assertIn("+line2", result["diff"])

    @patch("operations.backup_ops._get_git_context")
    def test_diff_two_versions(self, mock_git):
        mock_git.return_value = {"git_hash": None, "git_dirty": None}
        self._create_backup("version1\n", "20260301-100000")
        self._create_backup("version2\n", "20260305-143000")
        result = builtin_diff(
            self.test_file, self.config,
            "20260301-100000", "20260305-143000",
        )
        self.assertTrue(result["success"])
        self.assertTrue(result["has_changes"])

    @patch("operations.backup_ops._get_git_context")
    def test_diff_no_changes(self, mock_git):
        mock_git.return_value = {"git_hash": None, "git_dirty": None}
        content = "line1\nline2\nline3\n"
        self._create_backup(content, "20260305-143000")
        # Current file has same content
        result = builtin_diff(
            self.test_file, self.config, "latest", "current"
        )
        self.assertTrue(result["success"])
        self.assertFalse(result["has_changes"])

    def test_diff_version_not_found(self):
        result = builtin_diff(
            self.test_file, self.config, "99999999-999999", "current"
        )
        self.assertFalse(result["success"])
        self.assertIn("not found", result["error"])

    @patch("operations.backup_ops._get_git_context")
    def test_diff_unified_format(self, mock_git):
        mock_git.return_value = {"git_hash": None, "git_dirty": None}
        self._create_backup("old\n", "20260305-143000")
        result = builtin_diff(
            self.test_file, self.config, "latest", "current"
        )
        self.assertTrue(result["success"])
        self.assertIn("---", result["diff"])
        self.assertIn("+++", result["diff"])


class TestBuiltinProvider(unittest.TestCase):
    """Tests for builtin backup/restore/list."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp()).resolve()
        self.test_file = self.tmpdir / "test.txt"
        self.test_file.write_text("original content")
        self.config = _make_config(storage="local")

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    @patch("operations.backup_ops._get_git_context")
    def test_creates_timestamped_file(self, mock_git):
        mock_git.return_value = {"git_hash": None, "git_dirty": None}
        result = builtin_backup(self.test_file, self.config)
        self.assertTrue(result["success"])
        self.assertFalse(result["skipped"])
        bp = Path(result["backup_path"])
        self.assertTrue(bp.exists())
        self.assertIn(BACKUP_SUFFIX, bp.name)

    @patch("operations.backup_ops._get_git_context")
    def test_preserves_content(self, mock_git):
        mock_git.return_value = {"git_hash": None, "git_dirty": None}
        result = builtin_backup(self.test_file, self.config)
        bp = Path(result["backup_path"])
        self.assertEqual(bp.read_text(), "original content")

    @patch("operations.backup_ops._get_git_context")
    def test_multiple_versions(self, mock_git):
        mock_git.return_value = {"git_hash": None, "git_dirty": None}
        builtin_backup(self.test_file, self.config, "v1")
        self.test_file.write_text("modified content")
        builtin_backup(self.test_file, self.config, "v2")
        backups = _list_backups_with_metadata(self.test_file, self.config)
        self.assertGreaterEqual(len(backups), 2)

    @patch("operations.backup_ops._get_git_context")
    def test_restore_uses_latest(self, mock_git):
        mock_git.return_value = {"git_hash": None, "git_dirty": None}
        builtin_backup(self.test_file, self.config, "before change")
        self.test_file.write_text("modified")
        result = builtin_restore(self.test_file, self.config)
        self.assertTrue(result["success"])
        self.assertEqual(self.test_file.read_text(), "original content")

    @patch("operations.backup_ops._get_git_context")
    def test_restore_backs_up_current_first(self, mock_git):
        mock_git.return_value = {"git_hash": None, "git_dirty": None}
        builtin_backup(self.test_file, self.config)
        self.test_file.write_text("modified")
        builtin_restore(self.test_file, self.config)
        # Should now have at least 2 backups (original + safety)
        backups = _list_backups_with_metadata(self.test_file, self.config)
        self.assertGreaterEqual(len(backups), 2)

    def test_restore_no_backups(self):
        result = builtin_restore(self.test_file, self.config)
        self.assertFalse(result["success"])
        self.assertIn("not found", result["error"])

    @patch("operations.backup_ops._get_git_context")
    def test_list_returns_sorted(self, mock_git):
        mock_git.return_value = {"git_hash": None, "git_dirty": None}
        builtin_backup(self.test_file, self.config, "first")
        self.test_file.write_text("changed")
        builtin_backup(self.test_file, self.config, "second")
        result = builtin_list(self.test_file, self.config)
        self.assertTrue(result["success"])
        versions = result["versions"]
        self.assertGreaterEqual(len(versions), 2)
        # Newest first
        ts0 = versions[0].get("timestamp", "")
        ts1 = versions[1].get("timestamp", "")
        self.assertGreaterEqual(ts0, ts1)

    @patch("operations.backup_ops._get_git_context")
    def test_list_includes_metadata(self, mock_git):
        mock_git.return_value = {"git_hash": None, "git_dirty": None}
        builtin_backup(self.test_file, self.config, "test msg")
        result = builtin_list(self.test_file, self.config)
        v = result["versions"][0]
        self.assertIn("timestamp", v)
        self.assertIn("checksum", v)
        self.assertIn("file_size", v)

    @patch("operations.backup_ops._get_git_context")
    def test_list_all_files_with_counts(self, mock_git):
        mock_git.return_value = {"git_hash": None, "git_dirty": None}
        # Use global storage so we can scan all
        global_dir = self.tmpdir / "global_backups"
        config = _make_config(storage=str(global_dir))
        builtin_backup(self.test_file, config, "v1")
        result = builtin_list(None, config)
        self.assertTrue(result["success"])
        self.assertGreaterEqual(result["total_files"], 1)


class TestChecksumDedup(unittest.TestCase):
    """Tests for checksum dedup on save."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp()).resolve()
        self.test_file = self.tmpdir / "test.txt"
        self.test_file.write_text("content")
        self.config = _make_config(storage="local")

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    @patch("operations.backup_ops._get_git_context")
    def test_dedup_skips_when_unchanged(self, mock_git):
        mock_git.return_value = {"git_hash": None, "git_dirty": None}
        builtin_backup(self.test_file, self.config)
        result = builtin_backup(self.test_file, self.config)
        self.assertTrue(result["success"])
        self.assertTrue(result["skipped"])
        self.assertEqual(result["reason"], "unchanged")

    @patch("operations.backup_ops._get_git_context")
    def test_dedup_saves_when_changed(self, mock_git):
        mock_git.return_value = {"git_hash": None, "git_dirty": None}
        builtin_backup(self.test_file, self.config)
        self.test_file.write_text("new content")
        result = builtin_backup(self.test_file, self.config)
        self.assertTrue(result["success"])
        self.assertFalse(result["skipped"])

    @patch("operations.backup_ops._get_git_context")
    def test_dedup_saves_first_backup(self, mock_git):
        mock_git.return_value = {"git_hash": None, "git_dirty": None}
        result = builtin_backup(self.test_file, self.config)
        self.assertTrue(result["success"])
        self.assertFalse(result["skipped"])

    @patch("operations.backup_ops._get_git_context")
    def test_dedup_works_without_metadata(self, mock_git):
        mock_git.return_value = {"git_hash": None, "git_dirty": None}
        # Create a backup file without metadata
        bp = self.tmpdir / f"test.txt{BACKUP_SUFFIX}.20260301-100000"
        bp.write_text("content")
        # Metadata gets rebuilt; dedup still works after repair
        result = builtin_backup(self.test_file, self.config)
        self.assertTrue(result["success"])
        self.assertTrue(result["skipped"])
        self.assertEqual(result["reason"], "unchanged")


class TestRetention(unittest.TestCase):
    """Tests for retention policy."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp()).resolve()
        self.test_file = self.tmpdir / "test.txt"
        self.test_file.write_text("content")

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def _create_backup_with_age(self, timestamp_str, age_days=0):
        """Create a backup with specific timestamp in metadata."""
        bp = self.tmpdir / f"test.txt{BACKUP_SUFFIX}.{timestamp_str}"
        bp.write_text(f"content-{timestamp_str}")
        ts = datetime.now(timezone.utc) - timedelta(days=age_days)
        meta = {
            "original_path": str(self.test_file),
            "timestamp": ts.isoformat(),
            "message": "",
            "file_size": bp.stat().st_size,
            "checksum": _compute_checksum(bp),
            "backup_path": str(bp),
            "git_hash": None,
            "git_dirty": None,
        }
        _write_metadata(bp, meta)
        return bp

    def test_unlimited_keeps_all(self):
        config = _make_config(
            storage="local",
            retention={"max_versions": 0, "max_age_days": 0},
        )
        result = builtin_clean(config)
        self.assertTrue(result["success"])
        self.assertEqual(result["backups_removed"], 0)
        self.assertIn("No retention policy", result.get("note", ""))

    def test_max_versions_removes_oldest(self):
        self._create_backup_with_age("20260301-100000")
        self._create_backup_with_age("20260302-100000")
        self._create_backup_with_age("20260303-100000")
        config = _make_config(
            storage="local",
            retention={"max_versions": 2, "max_age_days": 0},
        )
        # Use per-file enforcement
        _maybe_enforce_retention(self.test_file, config)
        backups = _list_backups_with_metadata(self.test_file, config)
        self.assertEqual(len(backups), 2)

    def test_max_versions_keeps_at_limit(self):
        self._create_backup_with_age("20260301-100000")
        self._create_backup_with_age("20260302-100000")
        config = _make_config(
            storage="local",
            retention={"max_versions": 2, "max_age_days": 0},
        )
        _maybe_enforce_retention(self.test_file, config)
        backups = _list_backups_with_metadata(self.test_file, config)
        self.assertEqual(len(backups), 2)

    def test_max_age_removes_old(self):
        self._create_backup_with_age("20260101-100000", age_days=60)
        self._create_backup_with_age("20260304-100000", age_days=1)
        config = _make_config(
            storage="local",
            retention={"max_versions": 0, "max_age_days": 30},
        )
        _maybe_enforce_retention(self.test_file, config)
        backups = _list_backups_with_metadata(self.test_file, config)
        self.assertEqual(len(backups), 1)

    def test_max_age_keeps_recent(self):
        self._create_backup_with_age("20260304-100000", age_days=1)
        self._create_backup_with_age("20260305-100000", age_days=0)
        config = _make_config(
            storage="local",
            retention={"max_versions": 0, "max_age_days": 30},
        )
        _maybe_enforce_retention(self.test_file, config)
        backups = _list_backups_with_metadata(self.test_file, config)
        self.assertEqual(len(backups), 2)

    def test_combined_both_enforced(self):
        self._create_backup_with_age("20260101-100000", age_days=60)
        self._create_backup_with_age("20260201-100000", age_days=30)
        self._create_backup_with_age("20260303-100000", age_days=2)
        self._create_backup_with_age("20260304-100000", age_days=1)
        config = _make_config(
            storage="local",
            retention={"max_versions": 3, "max_age_days": 15},
        )
        _maybe_enforce_retention(self.test_file, config)
        backups = _list_backups_with_metadata(self.test_file, config)
        # Should keep 2: 20260303 and 20260304
        # 20260101 removed by age, 20260201 removed by age
        self.assertEqual(len(backups), 2)

    @patch("operations.backup_ops._get_git_context")
    def test_auto_enforce_prunes_after_save(self, mock_git):
        mock_git.return_value = {"git_hash": None, "git_dirty": None}
        config = _make_config(
            storage="local",
            retention={
                "max_versions": 2,
                "max_age_days": 0,
                "auto_enforce": True,
            },
        )
        # Create 3 backups via save (changing content each time)
        for i in range(3):
            self.test_file.write_text(f"content-{i}")
            builtin_backup(self.test_file, config, f"v{i}")
        backups = _list_backups_with_metadata(self.test_file, config)
        self.assertLessEqual(len(backups), 2)

    @patch("operations.backup_ops._get_git_context")
    def test_auto_enforce_false_keeps_all(self, mock_git):
        mock_git.return_value = {"git_hash": None, "git_dirty": None}
        config = _make_config(
            storage="local",
            retention={
                "max_versions": 1,
                "max_age_days": 0,
                "auto_enforce": False,
            },
        )
        for i in range(3):
            self.test_file.write_text(f"content-{i}")
            builtin_backup(self.test_file, config, f"v{i}")
        backups = _list_backups_with_metadata(self.test_file, config)
        self.assertEqual(len(backups), 3)

    def test_clean_dry_run(self):
        self._create_backup_with_age("20260301-100000")
        self._create_backup_with_age("20260302-100000")
        self._create_backup_with_age("20260303-100000")
        config = _make_config(
            storage=str(self.tmpdir),
            retention={"max_versions": 1, "max_age_days": 0},
        )
        result = builtin_clean(config, dry_run=True)
        self.assertTrue(result["success"])
        self.assertTrue(result.get("dry_run", False))
        self.assertGreater(result["backups_removed"], 0)
        # Files should still exist (dry run)
        remaining = list(self.tmpdir.glob(f"*{BACKUP_SUFFIX}*"))
        backup_files = [
            f for f in remaining if not f.name.endswith(META_SUFFIX)
        ]
        self.assertEqual(len(backup_files), 3)

    def test_clean_no_policy(self):
        config = _make_config(
            storage=str(self.tmpdir),
            retention={"max_versions": 0, "max_age_days": 0},
        )
        result = builtin_clean(config)
        self.assertEqual(result["backups_removed"], 0)


class TestStatus(unittest.TestCase):
    """Tests for status and analytics."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp()).resolve()
        self.test_file = self.tmpdir / "test.txt"
        self.test_file.write_text("content")

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def _create_backup(self, timestamp_str):
        bp = self.tmpdir / f"test.txt{BACKUP_SUFFIX}.{timestamp_str}"
        bp.write_text("content")
        dt = datetime.strptime(timestamp_str, TIMESTAMP_FMT)
        dt = dt.replace(tzinfo=timezone.utc)
        meta = {
            "original_path": str(self.test_file),
            "timestamp": dt.isoformat(),
            "message": "",
            "file_size": 7,
            "checksum": "abc",
            "backup_path": str(bp),
            "git_hash": None,
            "git_dirty": None,
        }
        _write_metadata(bp, meta)

    def test_status_returns_config(self):
        config = _make_config(storage=str(self.tmpdir))
        result = get_status(config)
        self.assertTrue(result["success"])
        self.assertIn("config", result)
        self.assertIn("enabled", result["config"])

    def test_status_counts(self):
        self._create_backup("20260305-100000")
        self._create_backup("20260305-110000")
        config = _make_config(storage=str(self.tmpdir))
        result = get_status(config)
        stats = result["stats"]
        self.assertEqual(stats["total_files_backed_up"], 1)
        self.assertEqual(stats["total_backup_versions"], 2)

    def test_status_total_size(self):
        self._create_backup("20260305-100000")
        config = _make_config(storage=str(self.tmpdir))
        result = get_status(config)
        self.assertGreater(result["stats"]["total_size_bytes"], 0)

    def test_status_timestamps(self):
        self._create_backup("20260305-100000")
        self._create_backup("20260305-140000")
        config = _make_config(storage=str(self.tmpdir))
        result = get_status(config)
        stats = result["stats"]
        self.assertIsNotNone(stats["oldest_backup"])
        self.assertIsNotNone(stats["newest_backup"])

    def test_status_per_file_breakdown(self):
        self._create_backup("20260305-100000")
        config = _make_config(storage=str(self.tmpdir))
        result = get_status(config)
        files = result["stats"]["files"]
        self.assertEqual(len(files), 1)
        self.assertIn("versions", files[0])
        self.assertIn("total_size_bytes", files[0])

    def test_status_empty_storage(self):
        empty_dir = self.tmpdir / "empty"
        empty_dir.mkdir()
        config = _make_config(storage=str(empty_dir))
        result = get_status(config)
        self.assertTrue(result["success"])
        self.assertEqual(result["stats"]["total_files_backed_up"], 0)

    def test_format_size(self):
        self.assertEqual(_format_size(0), "0 B")
        self.assertEqual(_format_size(512), "512 B")
        self.assertEqual(_format_size(1024), "1.0 KB")
        self.assertEqual(_format_size(1048576), "1.0 MB")
        self.assertEqual(_format_size(1073741824), "1.0 GB")


class TestCustomCommand(unittest.TestCase):
    """Tests for custom command override."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp()).resolve()
        self.test_file = self.tmpdir / "test.txt"
        self.test_file.write_text("content")

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    @patch("operations.backup_ops.subprocess.run")
    def test_substitution(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0, stdout="ok", stderr=""
        )
        _run_custom_command(
            "backup {file} -m '{message}'",
            self.test_file,
            "test msg",
        )
        call_args = mock_run.call_args
        cmd = call_args[0][0]
        self.assertIn(str(self.test_file), cmd)
        self.assertIn("test msg", cmd)

    @patch("operations.backup_ops.subprocess.run")
    def test_custom_used_when_configured(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0, stdout="ok", stderr=""
        )
        result = _run_custom_command("echo {file}", self.test_file, "")
        self.assertTrue(result["success"])

    @patch("operations.backup_ops.subprocess.run")
    def test_fallback_on_failure(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="error"
        )
        result = _run_custom_command("false", self.test_file, "")
        self.assertFalse(result["success"])

    @patch("operations.backup_ops.subprocess.run")
    def test_fallback_on_timeout(self, mock_run):
        from subprocess import TimeoutExpired
        mock_run.side_effect = TimeoutExpired("cmd", 30)
        result = _run_custom_command("sleep 999", self.test_file, "")
        self.assertFalse(result["success"])
        self.assertIn("timed out", result["error"])

    @patch("operations.backup_ops._get_git_context")
    @patch("operations.backup_ops.load_backup_config")
    def test_empty_custom_uses_builtin(self, mock_config, mock_git):
        mock_git.return_value = {"git_hash": None, "git_dirty": None}
        mock_config.return_value = _make_config(
            storage="local", custom_command=""
        )
        result = run_backup(self.test_file, "test")
        self.assertTrue(result["success"])


class TestStorageLocation(unittest.TestCase):
    """Tests for storage location resolution."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp()).resolve()
        self.test_file = self.tmpdir / "test.txt"
        self.test_file.write_text("content")

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_global_storage_dir(self):
        config = _make_config(storage="global")
        backup_dir = _get_backup_dir(self.test_file, config)
        self.assertIn(".claude", str(backup_dir))
        self.assertIn(".backups", str(backup_dir))

    def test_global_mirrors_path(self):
        config = _make_config(storage="global")
        backup_dir = _get_backup_dir(self.test_file, config)
        # Should contain part of the original path
        self.assertIn(self.tmpdir.name, str(backup_dir))

    @patch("operations.backup_ops._get_git_context")
    def test_global_creates_dir(self, mock_git):
        mock_git.return_value = {"git_hash": None, "git_dirty": None}
        custom_dir = self.tmpdir / "custom_global"
        config = _make_config(storage=str(custom_dir))
        builtin_backup(self.test_file, config)
        self.assertTrue(custom_dir.exists())

    def test_local_storage(self):
        config = _make_config(storage="local")
        backup_dir = _get_backup_dir(self.test_file, config)
        self.assertEqual(backup_dir, self.test_file.resolve().parent)

    def test_custom_storage(self):
        custom = self.tmpdir / "my_backups"
        config = _make_config(storage=str(custom))
        backup_dir = _get_backup_dir(self.test_file, config)
        self.assertTrue(str(backup_dir).startswith(str(custom)))

    def test_custom_mirrors_path(self):
        custom = self.tmpdir / "my_backups"
        config = _make_config(storage=str(custom))
        backup_dir = _get_backup_dir(self.test_file, config)
        self.assertIn(self.tmpdir.name, str(backup_dir))


class TestScope(unittest.TestCase):
    """Tests for scope checking."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp()).resolve()
        self.test_file = self.tmpdir / "test.txt"
        self.test_file.write_text("content")

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    @patch("operations.backup_ops._is_git_tracked", return_value=True)
    def test_always_backs_up_git_tracked(self, mock_git):
        config = _make_config(scope="always")
        self.assertTrue(should_backup(self.test_file, config))

    @patch("operations.backup_ops._is_git_tracked", return_value=True)
    def test_outside_git_skips_tracked(self, mock_git):
        config = _make_config(scope="outside-git-only")
        self.assertFalse(should_backup(self.test_file, config))

    @patch("operations.backup_ops._is_git_tracked", return_value=False)
    def test_outside_git_backs_up_untracked(self, mock_git):
        config = _make_config(scope="outside-git-only")
        self.assertTrue(should_backup(self.test_file, config))

    @patch("operations.backup_ops.subprocess.run")
    def test_git_check_handles_non_repo(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1)
        self.assertFalse(_is_git_tracked(self.test_file))


class TestConfig(unittest.TestCase):
    """Tests for config loading."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp()).resolve()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_disabled_skips(self):
        config = _make_config(enabled=False)
        f = self.tmpdir / "test.txt"
        f.write_text("content")
        self.assertFalse(should_backup(f, config))

    @patch("operations.backup_ops._read_yaml_backup_section")
    def test_defaults_when_no_config(self, mock_read):
        mock_read.return_value = None
        config = load_backup_config()
        self.assertTrue(config["enabled"])
        self.assertEqual(config["scope"], "always")
        self.assertEqual(config["storage"], "global")

    @patch("operations.backup_ops._read_yaml_backup_section")
    def test_loads_from_global(self, mock_read):
        mock_read.side_effect = [
            {"enabled": True, "scope": "outside-git-only"},
            None,
        ]
        config = load_backup_config()
        self.assertEqual(config["scope"], "outside-git-only")

    @patch("operations.backup_ops._read_yaml_backup_section")
    def test_project_overrides_global(self, mock_read):
        mock_read.side_effect = [
            {"scope": "always"},
            {"scope": "outside-git-only"},
        ]
        config = load_backup_config()
        self.assertEqual(config["scope"], "outside-git-only")

    @patch("operations.backup_ops._read_yaml_backup_section")
    def test_partial_project_override(self, mock_read):
        mock_read.side_effect = [
            {
                "scope": "always",
                "retention": {"max_versions": 10, "max_age_days": 30},
            },
            {"storage": "local"},
        ]
        config = load_backup_config()
        self.assertEqual(config["storage"], "local")
        self.assertEqual(config["scope"], "always")
        self.assertEqual(config["retention"]["max_versions"], 10)

    def test_nonexistent_file_skips(self):
        f = self.tmpdir / "does_not_exist.txt"
        config = _make_config()
        self.assertFalse(should_backup(f, config))


class TestTwoPhaseAPI(unittest.TestCase):
    """Tests for the two-phase API entry point via subprocess."""

    BACKUP_SCRIPT = str(
        Path(__file__).parent.parent.parent
        / "skills" / "backup" / "scripts" / "backup.py"
    )

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp()).resolve()
        self.test_file = self.tmpdir / "test.txt"
        self.test_file.write_text("content")

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def _run_backup_script(self, phase, context_dict):
        """Run backup.py via subprocess and parse JSON output."""
        import json as _json
        import subprocess
        ctx = _json.dumps(context_dict)
        result = subprocess.run(
            [sys.executable, self.BACKUP_SCRIPT, phase,
             "--context", ctx],
            capture_output=True, text=True, timeout=30,
        )
        # Parse last JSON object from output (skip any bootstrap output)
        output = result.stdout.strip()
        # Find the last { ... } block
        idx = output.rfind("\n{")
        if idx >= 0:
            output = output[idx + 1:]
        elif not output.startswith("{"):
            # Try to find first { if no newline prefix
            idx = output.find("{")
            if idx >= 0:
                output = output[idx:]
        return _json.loads(output)

    def test_get_questions_save(self):
        result = self._run_backup_script("--get-questions", {
            "operation": "save",
            "file": str(self.test_file),
        })
        self.assertTrue(result["success"])

    def test_get_questions_config(self):
        result = self._run_backup_script("--get-questions", {
            "operation": "config",
        })
        self.assertTrue(result["success"])
        self.assertGreater(len(result["questions"]), 0)

    def test_execute_save(self):
        result = self._run_backup_script("--execute", {
            "operation": "save",
            "file": str(self.test_file),
            "message": "test save",
        })
        self.assertTrue(result["success"])

    def test_execute_restore(self):
        # Create a backup first
        self._run_backup_script("--execute", {
            "operation": "save",
            "file": str(self.test_file),
        })
        self.test_file.write_text("modified")
        result = self._run_backup_script("--execute", {
            "operation": "restore",
            "file": str(self.test_file),
        })
        self.assertTrue(result["success"])

    def test_execute_diff(self):
        self._run_backup_script("--execute", {
            "operation": "save",
            "file": str(self.test_file),
        })
        self.test_file.write_text("changed content")
        result = self._run_backup_script("--execute", {
            "operation": "diff",
            "file": str(self.test_file),
        })
        self.assertTrue(result["success"])

    def test_execute_list(self):
        result = self._run_backup_script("--execute", {
            "operation": "list",
            "file": str(self.test_file),
        })
        self.assertTrue(result["success"])

    def test_execute_status(self):
        result = self._run_backup_script("--execute", {
            "operation": "status",
        })
        self.assertTrue(result["success"])


if __name__ == "__main__":
    unittest.main()
